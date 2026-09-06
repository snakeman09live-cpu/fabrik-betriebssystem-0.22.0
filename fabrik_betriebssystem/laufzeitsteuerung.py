from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

from .ereignisarchitektur import PersistenterEreignisdienst, PersistenterEreigniskonsument
from .verteilte_laufzeit import PersistenterAblaufplaner, VerteilteWarteschlange, AufgabenNachricht
from .kern import FabrikFehler


@dataclass
class Laufzeitzustand:
    laufende_lauefe: set[str] = field(default_factory=set)
    abgeschlossene_lauefe: set[str] = field(default_factory=set)
    letzte_sequenz: int = 0
    verarbeitete_ereignisse: int = 0


class KanonischeLaufzeit:
    """Zentrale 0.7-Laufzeit: Ereignisstrom, Aufgabenbroker, Ablaufplaner und Wiederanlauf."""

    def __init__(
        self,
        db,
        ereignisse: PersistenterEreignisdienst,
        warteschlange: VerteilteWarteschlange,
        ablaufplaner: PersistenterAblaufplaner,
    ) -> None:
        self.db = db
        self.ereignisse = ereignisse
        self.warteschlange = warteschlange
        self.ablaufplaner = ablaufplaner
        self.zustand = Laufzeitzustand()
        self._aufgabenbehandlung: dict[str, Callable[[AufgabenNachricht], None]] = {}
        self._lauf_ereignisbehandlung: dict[str, Callable[[object], None]] = {}
        self._konsument = PersistenterEreigniskonsument(
            ereignisse, "KANONISCHE_LAUFZEIT", self._ereignis_behandeln
        )

    def aufgabenhandler_registrieren(self, aufgabenkennung: str, handler: Callable[[AufgabenNachricht], None]) -> None:
        if not aufgabenkennung:
            raise FabrikFehler("AUFGABENKENNUNG_FEHLT", "Aufgabenkennung fehlt.")
        self._aufgabenbehandlung[aufgabenkennung] = handler

    def laufereignishandler_registrieren(self, ereignisart: str, handler: Callable[[object], None]) -> None:
        if not ereignisart:
            raise FabrikFehler("EREIGNISART_FEHLT", "Ereignisart fehlt.")
        self._lauf_ereignisbehandlung[ereignisart] = handler

    def _ereignis_behandeln(self, ereignis) -> None:
        self.zustand.letzte_sequenz = ereignis.sequenznummer or self.zustand.letzte_sequenz
        self.zustand.verarbeitete_ereignisse += 1
        if ereignis.ereignisart in {"AUSFUEHRUNGSLAUF_GESTARTET", "VORGANG_GESTARTET"}:
            self.zustand.laufende_lauefe.add(ereignis.entitaetskennung)
        elif ereignis.ereignisart in {"AUSFUEHRUNGSLAUF_ABGESCHLOSSEN", "VORGANG_ABGESCHLOSSEN"}:
            self.zustand.laufende_lauefe.discard(ereignis.entitaetskennung)
            self.zustand.abgeschlossene_lauefe.add(ereignis.entitaetskennung)
        handler = self._lauf_ereignisbehandlung.get(ereignis.ereignisart)
        if handler:
            handler(ereignis)

    def ereignisse_nachholen(self, limit: int = 100) -> int:
        return self._konsument.nachholen(limit)

    def faellige_aufgaben_einreihen(self, jetztzeitpunkt=None) -> list[str]:
        return self.ablaufplaner.faellige_einreihen(jetztzeitpunkt)

    def aufgabe_ausfuehren(self, arbeiterkennung: str) -> str | None:
        from .verteilte_laufzeit import VerteilterArbeiter

        def handler(nachricht: AufgabenNachricht) -> None:
            handler = self._aufgabenbehandlung.get(nachricht.aufgabenkennung)
            if handler is None:
                raise FabrikFehler(
                    "AUFGABENHANDLER_FEHLT",
                    f"Kein Laufzeit-Handler für {nachricht.aufgabenkennung} registriert.",
                )
            handler(nachricht)

        return VerteilterArbeiter(self.warteschlange, handler, kennung=arbeiterkennung).einmal()

    def runde(self, arbeiterkennung: str = "laufzeit-arbeiter", jetztzeitpunkt=None, ereignislimit: int = 100) -> dict:
        faellig = self.faellige_aufgaben_einreihen(jetztzeitpunkt)
        aufgabe = self.aufgabe_ausfuehren(arbeiterkennung)
        nachgeholt = self.ereignisse_nachholen(ereignislimit)
        return {"faellig": faellig, "aufgabe": aufgabe, "ereignisse": nachgeholt}

    def wiederanlauf(self, ereignislimit: int = 1000) -> dict:
        """Rekonstruiert den flüchtigen Laufzeitstatus aus dem persistenten Ereignisstrom."""
        self.zustand = Laufzeitzustand()
        anzahl = self.ereignisse_nachholen(ereignislimit)
        return {
            "nachgeholt": anzahl,
            "letzte_sequenz": self.zustand.letzte_sequenz,
            "laufende_lauefe": sorted(self.zustand.laufende_lauefe),
            "abgeschlossene_lauefe": sorted(self.zustand.abgeschlossene_lauefe),
        }
