from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
import hashlib

from sqlalchemy import Boolean, DateTime, Integer, String, Text, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from .persistenz import Basis, Datenbank


def jetzt() -> datetime:
    return datetime.now(timezone.utc)


def utc(datum: datetime) -> datetime:
    if datum.tzinfo is None:
        return datum.replace(tzinfo=timezone.utc)
    return datum.astimezone(timezone.utc)


class AusgabepufferLease(Basis):
    __tablename__ = "ausgabepuffer_leases"
    nachrichtenkennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    besitzer: Mapped[str] = mapped_column(String(255), nullable=False)
    lease_bis: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Eingangsverarbeitung(Basis):
    __tablename__ = "eingangsverarbeitungen"
    nachrichtenkennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    konsumentenkennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    begonnen_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    abgeschlossen_am: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fehler: Mapped[str | None] = mapped_column(Text, nullable=True)


@dataclass(frozen=True)
class AusgabepufferAuftrag:
    nachrichtenkennung: str
    kanal: str
    nutzlast: dict[str, Any]
    lease_bis: datetime


class TransaktionalerAusgabepuffer:
    """Outbox mit Datenbank-Lease. Mehrere Zusteller können sicher parallel arbeiten."""

    def __init__(self, db: Datenbank, lease_sekunden: int = 30):
        self.db = db
        self.lease_sekunden = lease_sekunden

    def _lease_erwerben(self, s, kennung: str, besitzer: str, now: datetime, ende: datetime) -> bool:
        """Erwirbt den Lease einer Nachricht atomar.

        Gibt False zurück, wenn ein anderer Zusteller den Lease hält oder ein
        paralleler Zusteller zwischen Lesen und Schreiben schneller war.

        Ob ein Lease abgelaufen ist, wird in Python entschieden, weil SQLite
        keine Zeitzone speichert und ein SQL-seitiger Zeitvergleich zwischen
        SQLite und PostgreSQL unterschiedlich ausfiele. Geschrieben wird per
        Compare-and-Set auf den gelesenen Werten, damit sich zwei Zusteller
        nicht gegenseitig den Lease überschreiben.
        """
        lease = s.get(AusgabepufferLease, kennung)
        if lease is None:
            try:
                with s.begin_nested():
                    s.execute(insert(AusgabepufferLease).values(
                        nachrichtenkennung=kennung, besitzer=besitzer, lease_bis=ende))
                return True
            except IntegrityError:
                return False
        if utc(lease.lease_bis) > now and lease.besitzer != besitzer:
            return False
        alter_besitzer, altes_ende = lease.besitzer, lease.lease_bis
        s.expunge(lease)
        getroffen = s.execute(update(AusgabepufferLease)
                              .where(AusgabepufferLease.nachrichtenkennung == kennung,
                                     AusgabepufferLease.besitzer == alter_besitzer,
                                     AusgabepufferLease.lease_bis == altes_ende)
                              .values(besitzer=besitzer, lease_bis=ende))
        return getroffen.rowcount == 1

    def uebernehmen(self, besitzer: str, limit: int = 100) -> list[AusgabepufferAuftrag]:
        import json
        from .persistenz import Ausgabepufferdaten
        now = jetzt()
        ende = datetime.fromtimestamp(now.timestamp() + self.lease_sekunden, tz=timezone.utc)
        result: list[AusgabepufferAuftrag] = []
        with self.db.session() as s:
            offene = s.scalars(select(Ausgabepufferdaten).where(Ausgabepufferdaten.bestaetigt.is_(False)).order_by(Ausgabepufferdaten.erstellt_am).limit(limit * 2)).all()
            for row in offene:
                if not self._lease_erwerben(s, row.kennung, besitzer, now, ende):
                    continue
                result.append(AusgabepufferAuftrag(row.kennung, row.kanal, json.loads(row.nutzlast), ende))
                if len(result) >= limit:
                    break
            s.commit()
        return result

    def bestaetigen(self, besitzer: str, nachrichtenkennung: str) -> bool:
        from .persistenz import Ausgabepufferdaten
        with self.db.session() as s:
            row = s.get(Ausgabepufferdaten, nachrichtenkennung)
            lease = s.get(AusgabepufferLease, nachrichtenkennung)
            if row is None or row.bestaetigt or lease is None or lease.besitzer != besitzer:
                return False
            row.bestaetigt = True
            row.bestaetigt_am = jetzt()
            s.delete(lease)
            s.commit()
            return True

    def freigeben(self, besitzer: str, nachrichtenkennung: str) -> bool:
        with self.db.session() as s:
            lease = s.get(AusgabepufferLease, nachrichtenkennung)
            if lease is None or lease.besitzer != besitzer:
                return False
            s.delete(lease)
            s.commit()
            return True


class InboxDienst:
    """Dedup-/Inbox-Schutz: ein Konsument verarbeitet dieselbe Nachricht höchstens logisch einmal."""

    def __init__(self, db: Datenbank):
        self.db = db

    @staticmethod
    def schluessel(nachrichtenkennung: str, konsumentenkennung: str) -> tuple[str, str]:
        return (nachrichtenkennung, konsumentenkennung)

    def uebernehmen(self, nachrichtenkennung: str, konsumentenkennung: str) -> bool:
        with self.db.session() as s:
            row = s.get(Eingangsverarbeitung, self.schluessel(nachrichtenkennung, konsumentenkennung))
            if row is not None and row.status == "ABGESCHLOSSEN":
                return False
            if row is None:
                s.add(Eingangsverarbeitung(
                    nachrichtenkennung=nachrichtenkennung,
                    konsumentenkennung=konsumentenkennung,
                    status="IN_BEARBEITUNG",
                    begonnen_am=jetzt(),
                ))
            else:
                row.status = "IN_BEARBEITUNG"
                row.begonnen_am = jetzt()
                row.abgeschlossen_am = None
                row.fehler = None
            s.commit()
            return True

    def abschliessen(self, nachrichtenkennung: str, konsumentenkennung: str) -> None:
        with self.db.session() as s:
            row = s.get(Eingangsverarbeitung, self.schluessel(nachrichtenkennung, konsumentenkennung))
            if row:
                row.status = "ABGESCHLOSSEN"
                row.abgeschlossen_am = jetzt()
                row.fehler = None
                s.commit()

    def fehlschlagen(self, nachrichtenkennung: str, konsumentenkennung: str, fehler: str) -> None:
        with self.db.session() as s:
            row = s.get(Eingangsverarbeitung, self.schluessel(nachrichtenkennung, konsumentenkennung))
            if row:
                row.status = "FEHLGESCHLAGEN"
                row.fehler = fehler[:4000]
                s.commit()


class Signaturdienst:
    """Einfacher Inhaltsfingerabdruck für Integritätsnachweise; keine Kryptografie-/Identitätsverwaltung."""
    @staticmethod
    def fingerabdruck(nutzlast: dict[str, Any]) -> str:
        import json
        raw = json.dumps(nutzlast, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()
