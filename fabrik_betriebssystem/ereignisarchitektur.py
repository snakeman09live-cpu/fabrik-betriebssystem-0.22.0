from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import uuid
from typing import Any, Callable

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from .modelle import Ereignis
from .persistenz import Basis, Datenbank


def jetzt() -> datetime:
    return datetime.now(timezone.utc)


class PersistiertesEreignis(Basis):
    __tablename__ = "persistierte_ereignisse"
    ereigniskennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    ereignisart: Mapped[str] = mapped_column(String(120), nullable=False)
    entitaetskennung: Mapped[str] = mapped_column(String(255), nullable=False)
    vorgangskennung: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nutzlast: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    zusammenhangskennung: Mapped[str] = mapped_column(String(255), nullable=False)
    ablaufverfolgungskennung: Mapped[str] = mapped_column(String(255), nullable=False)
    sequenznummer: Mapped[int] = mapped_column(Integer, nullable=False)


class Konsumentenstand(Basis):
    __tablename__ = "konsumentenstaende"
    konsumentenkennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    sequenznummer: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Zustellversuch(Basis):
    __tablename__ = "ereignis_zustellversuche"
    ereigniskennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    konsumentenkennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    versuche: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    letzter_fehler: Mapped[str | None] = mapped_column(Text, nullable=True)
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("ereigniskennung", "konsumentenkennung"),)


@dataclass(frozen=True)
class PersistiertesEreignisErgebnis:
    ereignis: Ereignis
    neu: bool


class PersistenterEreignisdienst:
    """Dauerhafter Ereignisspeicher mit Konsumentenständen und Nachholverarbeitung."""

    def __init__(self, db: Datenbank):
        self.db = db

    @staticmethod
    def _to_dict(ereignis: Ereignis) -> dict[str, Any]:
        return ereignis.model_dump(mode="json")

    @staticmethod
    def _aus_datensatz(row: PersistiertesEreignis) -> Ereignis:
        daten = json.loads(row.nutzlast)
        return Ereignis(
            ereigniskennung=row.ereigniskennung,
            ereignisart=row.ereignisart,
            entitaetskennung=row.entitaetskennung,
            vorgangskennung=row.vorgangskennung,
            vorheriger_zustand=daten.get("vorheriger_zustand"),
            neuer_zustand=daten.get("neuer_zustand"),
            vorherige_zustandsversion=daten.get("vorherige_zustandsversion"),
            neue_zustandsversion=daten.get("neue_zustandsversion"),
            zeitpunkt=row.zeitpunkt,
            zusammenhangskennung=row.zusammenhangskennung,
            ablaufverfolgungskennung=row.ablaufverfolgungskennung,
            sequenznummer=row.sequenznummer,
        )

    def veroeffentlichen(self, ereignis: Ereignis) -> PersistiertesEreignisErgebnis:
        with self.db.session() as s:
            vorhanden = s.get(PersistiertesEreignis, ereignis.ereigniskennung)
            if vorhanden:
                return PersistiertesEreignisErgebnis(self._aus_datensatz(vorhanden), False)
            letzter = s.scalar(select(PersistiertesEreignis.sequenznummer).order_by(PersistiertesEreignis.sequenznummer.desc()).limit(1)) or 0
            sequenz = letzter + 1
            payload = self._to_dict(ereignis)
            payload.pop("sequenznummer", None)
            row = PersistiertesEreignis(
                ereigniskennung=ereignis.ereigniskennung,
                ereignisart=ereignis.ereignisart,
                entitaetskennung=ereignis.entitaetskennung,
                vorgangskennung=ereignis.vorgangskennung,
                nutzlast=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                zeitpunkt=ereignis.zeitpunkt,
                zusammenhangskennung=ereignis.zusammenhangskennung,
                ablaufverfolgungskennung=ereignis.ablaufverfolgungskennung,
                sequenznummer=sequenz,
            )
            s.add(row)
            s.commit()
            stored = self._aus_datensatz(row)
            return PersistiertesEreignisErgebnis(stored, True)

    def seit(self, sequenznummer: int = 0, limit: int = 1000) -> list[Ereignis]:
        with self.db.session() as s:
            rows = s.scalars(
                select(PersistiertesEreignis)
                .where(PersistiertesEreignis.sequenznummer > sequenznummer)
                .order_by(PersistiertesEreignis.sequenznummer)
                .limit(limit)
            ).all()
            return [self._aus_datensatz(row) for row in rows]

    def alle(self) -> list[Ereignis]:
        return self.seit(0, 1_000_000)

    def konsumentenstand(self, konsumentenkennung: str) -> int:
        with self.db.session() as s:
            row = s.get(Konsumentenstand, konsumentenkennung)
            return row.sequenznummer if row else 0

    def _stand_setzen(self, s, konsumentenkennung: str, sequenznummer: int) -> None:
        row = s.get(Konsumentenstand, konsumentenkennung)
        if row is None:
            s.add(Konsumentenstand(konsumentenkennung=konsumentenkennung, sequenznummer=sequenznummer, aktualisiert_am=jetzt()))
        else:
            row.sequenznummer = sequenznummer
            row.aktualisiert_am = jetzt()

    def verarbeiten(self, konsumentenkennung: str, handler: Callable[[Ereignis], None], limit: int = 100) -> int:
        """Verarbeitet Ereignisse ab dem gespeicherten Offset. Offset wird erst nach Handler-Erfolg fortgeschrieben."""
        verarbeitete = 0
        stand = self.konsumentenstand(konsumentenkennung)
        for ereignis in self.seit(stand, limit):
            self._zustellversuch_starten(konsumentenkennung, ereignis.ereigniskennung)
            try:
                handler(ereignis)
            except Exception as exc:
                self._zustellversuch_fehlgeschlagen(konsumentenkennung, ereignis.ereigniskennung, str(exc))
                raise
            self._zustellversuch_erfolgreich(konsumentenkennung, ereignis.ereigniskennung)
            with self.db.session() as s:
                self._stand_setzen(s, konsumentenkennung, ereignis.sequenznummer or stand)
                s.commit()
            stand = ereignis.sequenznummer or stand
            verarbeitete += 1
        return verarbeitete

    def _zustellversuch_starten(self, konsumentenkennung: str, ereigniskennung: str) -> None:
        with self.db.session() as s:
            key = (ereigniskennung, konsumentenkennung)
            row = s.get(Zustellversuch, key)
            if row is None:
                s.add(Zustellversuch(ereigniskennung=ereigniskennung, konsumentenkennung=konsumentenkennung, versuche=1, aktualisiert_am=jetzt()))
            else:
                row.versuche += 1
                row.aktualisiert_am = jetzt()
            s.commit()

    def _zustellversuch_fehlgeschlagen(self, konsumentenkennung: str, ereigniskennung: str, fehler: str) -> None:
        with self.db.session() as s:
            row = s.get(Zustellversuch, (ereigniskennung, konsumentenkennung))
            if row:
                row.letzter_fehler = fehler
                row.aktualisiert_am = jetzt()
                s.commit()

    def _zustellversuch_erfolgreich(self, konsumentenkennung: str, ereigniskennung: str) -> None:
        # Der Zustellversuch bleibt als Nachweis erhalten; kein Löschen.
        with self.db.session() as s:
            row = s.get(Zustellversuch, (ereigniskennung, konsumentenkennung))
            if row:
                row.letzter_fehler = None
                row.aktualisiert_am = jetzt()
                s.commit()


class PersistenterEreigniskonsument:
    def __init__(self, dienst: PersistenterEreignisdienst, konsumentenkennung: str, handler: Callable[[Ereignis], None]):
        self.dienst = dienst
        self.konsumentenkennung = konsumentenkennung
        self.handler = handler

    def nachholen(self, limit: int = 100) -> int:
        return self.dienst.verarbeiten(self.konsumentenkennung, self.handler, limit)
