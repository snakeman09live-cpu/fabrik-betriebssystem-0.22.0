from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Any
import uuid
from .modelle import Zustand, Aktion
from .aufgaben import Aufgabengraph, Ausfuehrungsaufgabe
from .kern import FabrikFehler
from .nachrichten import Ereignisbus, Nachricht

@dataclass
class Ausfuehrungslauf:
    laufkennung: str
    planversion: str
    zustand: Zustand = Zustand.INITIAL
    zustandsversion: int = 0
    aufgaben: dict[str, Ausfuehrungsaufgabe] = field(default_factory=dict)
    ergebnisse: list[Any] = field(default_factory=list)

class Ausfuehrungslaufdienst:
    def __init__(self, ereignisbus: Ereignisbus, persist=None):
        self.ereignisbus = ereignisbus
        self.persist = persist
        self._laeufe: dict[str, Ausfuehrungslauf] = {}

    def erstellen(self, planversion: str, aufgaben: list[Ausfuehrungsaufgabe]) -> Ausfuehrungslauf:
        graph = Aufgabengraph(aufgaben)
        if not aufgaben:
            raise FabrikFehler("AUFGABEN_FEHLEN", "Ein Ausführungslauf benötigt mindestens eine Aufgabe.")
        lauf = Ausfuehrungslauf(str(uuid.uuid4()), planversion, aufgaben={x.aufgabenkennung: x for x in aufgaben})
        graph  # validiert Zyklus/Referenzen
        self._laeufe[lauf.laufkennung] = lauf
        if self.persist:
            self.persist(lauf)
        self.ereignisbus.veroeffentlichen("AUSFUEHRUNGSLAUF_ERSTELLT", lauf.laufkennung,
                                          {"planversion": planversion})
        return lauf

    def ausfuehren(self, laufkennung: str) -> Ausfuehrungslauf:
        lauf = self._laeufe.get(laufkennung)
        if lauf is None:
            raise FabrikFehler("AUSFUEHRUNGSLAUF_NICHT_GEFUNDEN", "Ausführungslauf wurde nicht gefunden.")
        if lauf.zustand in {Zustand.ABGESCHLOSSEN, Zustand.ABGELOEST, Zustand.AUSSER_BETRIEB}:
            return lauf
        graph = Aufgabengraph(list(lauf.aufgaben.values()))
        lauf.zustand = Zustand.AKTIV
        lauf.zustandsversion += 1
        self.ereignisbus.veroeffentlichen("AUSFUEHRUNGSLAUF_GESTARTET", lauf.laufkennung, {})
        try:
            while True:
                bereit = graph.bereite_aufgaben()
                if not bereit:
                    break
                for aufgabe in bereit:
                    if aufgabe.handler is None:
                        raise FabrikFehler("AUFGABENHANDLER_FEHLT", f"Für {aufgabe.aufgabenkennung} fehlt die Ausführung.")
                    self.ereignisbus.veroeffentlichen("AUFGABE_GESTARTET", lauf.laufkennung,
                                                      {"aufgabenkennung": aufgabe.aufgabenkennung})
                    aufgabe.ergebnis = aufgabe.handler()
                    aufgabe.abgeschlossen = True
                    if self.persist:
                        self.persist(lauf)
                    lauf.ergebnisse.append(aufgabe.ergebnis)
                    self.ereignisbus.veroeffentlichen("AUFGABE_ABGESCHLOSSEN", lauf.laufkennung,
                                                      {"aufgabenkennung": aufgabe.aufgabenkennung})
            if not all(x.abgeschlossen for x in lauf.aufgaben.values()):
                lauf.zustand = Zustand.BLOCKIERT
            else:
                lauf.zustand = Zustand.ABGESCHLOSSEN
            lauf.zustandsversion += 1
            self.ereignisbus.veroeffentlichen("AUSFUEHRUNGSLAUF_ABGESCHLOSSEN", lauf.laufkennung,
                                              {"zustand": lauf.zustand.value, "zustandsversion": lauf.zustandsversion})
            if self.persist:
                self.persist(lauf)
            return lauf
        except FabrikFehler:
            lauf.zustand = Zustand.FEHLGESCHLAGEN
            lauf.zustandsversion += 1
            if self.persist:
                self.persist(lauf)
            self.ereignisbus.veroeffentlichen("AUSFUEHRUNGSLAUF_FEHLGESCHLAGEN", lauf.laufkennung, {})
            raise

    def lesen(self, laufkennung: str) -> Ausfuehrungslauf:
        if laufkennung not in self._laeufe:
            raise FabrikFehler("AUSFUEHRUNGSLAUF_NICHT_GEFUNDEN", "Ausführungslauf wurde nicht gefunden.")
        return self._laeufe[laufkennung]

    def alle(self) -> list[Ausfuehrungslauf]:
        return list(self._laeufe.values())
