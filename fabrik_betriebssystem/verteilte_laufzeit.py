from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Callable
import json
import uuid
from sqlalchemy import String, Integer, DateTime, Text, select, Index
from sqlalchemy.orm import Mapped, mapped_column
from .persistenz import Basis, Datenbank


def jetzt() -> datetime:
    return datetime.now(timezone.utc)


class AufgabenNachricht(Basis):
    __tablename__ = "aufgaben_nachrichten"
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    laufkennung: Mapped[str] = mapped_column(String(255), nullable=False)
    aufgabenkennung: Mapped[str] = mapped_column(String(255), nullable=False)
    nutzlast: Mapped[str] = mapped_column(Text, default="{}")
    zustand: Mapped[str] = mapped_column(String(40), default="BEREIT", nullable=False)
    versuche: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    naechster_versuch_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=jetzt, nullable=False)
    sperrfrist_bis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arbeiterkennung: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fehler: Mapped[str | None] = mapped_column(Text, nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=jetzt, nullable=False)
    geaendert_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=jetzt, nullable=False)

Index("ix_aufgaben_nachrichten_bereit", AufgabenNachricht.zustand, AufgabenNachricht.naechster_versuch_am)


class GeplanterNachricht(Basis):
    __tablename__ = "geplante_nachrichten"
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    ausfuehrungszeitpunkt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nachrichtenkennung: Mapped[str] = mapped_column(String(255), nullable=False)
    zustand: Mapped[str] = mapped_column(String(40), default="GEPLANT", nullable=False)


class Ereignisspeicher(Basis):
    __tablename__ = "ereignisspeicher"
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    ereignisart: Mapped[str] = mapped_column(String(120), nullable=False)
    entitaet: Mapped[str] = mapped_column(String(255), nullable=False)
    vorgang: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inhalt: Mapped[str] = mapped_column(Text, default="{}")
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=jetzt, nullable=False)
    sequenznummer: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ToterBrief(Basis):
    __tablename__ = "tote_briefe"
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    nachrichtenkennung: Mapped[str] = mapped_column(String(255), nullable=False)
    grund: Mapped[str] = mapped_column(String(255), nullable=False)
    nutzlast: Mapped[str] = mapped_column(Text, default="{}")
    archiviert_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=jetzt, nullable=False)


@dataclass
class VerteilteWarteschlange:
    db: Datenbank
    maximale_versuche: int = 5
    sichtbarkeit_sekunden: int = 30
    basis_wiederholungssekunden: int = 1

    def einreihen(self, laufkennung: str, aufgabenkennung: str, nutzlast: dict | None = None, kennung: str | None = None) -> str:
        kennung = kennung or str(uuid.uuid4())
        with self.db.session() as s:
            vorhandener = s.get(AufgabenNachricht, kennung)
            if vorhandener:
                return kennung
            s.add(AufgabenNachricht(
                kennung=kennung,
                laufkennung=laufkennung,
                aufgabenkennung=aufgabenkennung,
                nutzlast=json.dumps(nutzlast or {}, ensure_ascii=False, default=str),
            ))
            s.commit()
        return kennung

    def beanspruchen(self, arbeiterkennung: str, jetztzeitpunkt: datetime | None = None) -> AufgabenNachricht | None:
        jetztzeitpunkt = jetztzeitpunkt or jetzt()
        with self.db.session() as s:
            stmt = (
                select(AufgabenNachricht)
                .where(
                    AufgabenNachricht.zustand == "BEREIT",
                    AufgabenNachricht.naechster_versuch_am <= jetztzeitpunkt,
                )
                .order_by(AufgabenNachricht.naechster_versuch_am, AufgabenNachricht.erstellt_am)
                .limit(1)
                .with_for_update()
            )
            nachricht = s.scalar(stmt)
            if nachricht is None:
                return None
            nachricht.zustand = "IN_BEARBEITUNG"
            nachricht.arbeiterkennung = arbeiterkennung
            nachricht.sperrfrist_bis = jetztzeitpunkt + timedelta(seconds=self.sichtbarkeit_sekunden)
            nachricht.versuche += 1
            nachricht.geaendert_am = jetztzeitpunkt
            s.commit()
            return nachricht

    def bestaetigen(self, kennung: str) -> None:
        with self.db.session() as s:
            n = s.get(AufgabenNachricht, kennung)
            if n is None:
                return
            n.zustand = "ERLEDIGT"
            n.sperrfrist_bis = None
            n.geaendert_am = jetzt()
            s.commit()

    def erneut_einreihen(self, kennung: str, fehler: str, jetztzeitpunkt: datetime | None = None) -> str:
        jetztzeitpunkt = jetztzeitpunkt or jetzt()
        with self.db.session() as s:
            n = s.get(AufgabenNachricht, kennung)
            if n is None:
                raise ValueError("NACHRICHT_NICHT_GEFUNDEN")
            if n.versuche >= self.maximale_versuche:
                n.zustand = "TOTE_POST"
                n.fehler = fehler
                n.sperrfrist_bis = None
                s.add(ToterBrief(kennung=str(uuid.uuid4()), nachrichtenkennung=n.kennung, grund=fehler, nutzlast=n.nutzlast))
            else:
                wartezeit = self.basis_wiederholungssekunden * (2 ** max(0, n.versuche - 1))
                n.zustand = "BEREIT"
                n.fehler = fehler
                n.sperrfrist_bis = None
                n.naechster_versuch_am = jetztzeitpunkt + timedelta(seconds=wartezeit)
            n.geaendert_am = jetztzeitpunkt
            s.commit()
            return n.zustand

    def abgelaufene_sperren_freigeben(self, jetztzeitpunkt: datetime | None = None) -> int:
        jetztzeitpunkt = jetztzeitpunkt or jetzt()
        with self.db.session() as s:
            rows = s.scalars(select(AufgabenNachricht).where(
                AufgabenNachricht.zustand == "IN_BEARBEITUNG",
                AufgabenNachricht.sperrfrist_bis.is_not(None),
                AufgabenNachricht.sperrfrist_bis < jetztzeitpunkt,
            )).all()
            for n in rows:
                n.zustand = "BEREIT"
                n.arbeiterkennung = None
                n.sperrfrist_bis = None
                n.naechster_versuch_am = jetztzeitpunkt
                n.geaendert_am = jetztzeitpunkt
            s.commit()
            return len(rows)

    def tote_briefe(self) -> list[ToterBrief]:
        with self.db.session() as s:
            return list(s.scalars(select(ToterBrief).order_by(ToterBrief.archiviert_am)).all())


@dataclass
class PersistenterAblaufplaner:
    db: Datenbank
    warteschlange: VerteilteWarteschlange

    def planen(self, nachrichtenkennung: str, ausfuehrungszeitpunkt: datetime, planungskennung: str | None = None) -> str:
        planungskennung = planungskennung or str(uuid.uuid4())
        with self.db.session() as s:
            s.add(GeplanterNachricht(
                kennung=planungskennung,
                ausfuehrungszeitpunkt=ausfuehrungszeitpunkt,
                nachrichtenkennung=nachrichtenkennung,
            ))
            s.commit()
        return planungskennung

    def faellige_einreihen(self, jetztzeitpunkt: datetime | None = None) -> list[str]:
        jetztzeitpunkt = jetztzeitpunkt or jetzt()
        with self.db.session() as s:
            rows = s.scalars(select(GeplanterNachricht).where(
                GeplanterNachricht.zustand == "GEPLANT",
                GeplanterNachricht.ausfuehrungszeitpunkt <= jetztzeitpunkt,
            )).all()
            ids = []
            for row in rows:
                row.zustand = "EINGEREIHT"
                ids.append(row.nachrichtenkennung)
            s.commit()
        for kennung in ids:
            # Die eigentliche Nachricht muss bereits existieren; hier wird nur ihr Zustand aktiviert.
            with self.db.session() as s:
                n = s.get(AufgabenNachricht, kennung)
                if n and n.zustand == "BEREIT":
                    n.naechster_versuch_am = jetztzeitpunkt
                    s.commit()
        return ids


class VerteilterArbeiter:
    def __init__(self, warteschlange: VerteilteWarteschlange, handler: Callable[[AufgabenNachricht], None], kennung: str | None = None):
        self.warteschlange = warteschlange
        self.handler = handler
        self.arbeiterkennung = kennung or str(uuid.uuid4())

    def einmal(self) -> str | None:
        self.warteschlange.abgelaufene_sperren_freigeben()
        n = self.warteschlange.beanspruchen(self.arbeiterkennung)
        if n is None:
            return None
        try:
            self.handler(n)
        except Exception as exc:
            self.warteschlange.erneut_einreihen(n.kennung, f"{type(exc).__name__}: {exc}")
            return "FEHLER"
        self.warteschlange.bestaetigen(n.kennung)
        return "ERLEDIGT"
