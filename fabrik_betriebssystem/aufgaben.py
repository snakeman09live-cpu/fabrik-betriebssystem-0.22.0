from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
from .modelle import Aktion
from .kern import FabrikFehler

@dataclass
class Ausfuehrungsaufgabe:
    aufgabenkennung: str
    aktion: Aktion
    vorgaenger: list[str] = field(default_factory=list)
    handler: Callable[[], object] | None = None
    ergebnis: object | None = None
    abgeschlossen: bool = False

class Aufgabengraph:
    def __init__(self, aufgaben: list[Ausfuehrungsaufgabe]):
        self.aufgaben = {a.aufgabenkennung: a for a in aufgaben}
        self._pruefe_zyklen()

    def _pruefe_zyklen(self) -> None:
        besucht, stapel = set(), set()
        def dfs(name: str):
            if name in stapel:
                raise FabrikFehler("AUFGABENZYKLUS", "Aufgabengraph enthält einen Zyklus.")
            if name in besucht:
                return
            stapel.add(name)
            for vor in self.aufgaben[name].vorgaenger:
                if vor not in self.aufgaben:
                    raise FabrikFehler("AUFGABENABHAENGIGKEIT_FEHLT", f"Abhängigkeit {vor} fehlt.")
                dfs(vor)
            stapel.remove(name); besucht.add(name)
        for name in self.aufgaben:
            dfs(name)

    def bereite_aufgaben(self) -> list[Ausfuehrungsaufgabe]:
        return [a for a in self.aufgaben.values() if not a.abgeschlossen and all(self.aufgaben[p].abgeschlossen for p in a.vorgaenger)]

    def ausfuehren(self) -> list[object]:
        ergebnisse=[]
        while True:
            bereit=self.bereite_aufgaben()
            if not bereit:
                offen=[a.aufgabenkennung for a in self.aufgaben.values() if not a.abgeschlossen]
                if offen:
                    raise FabrikFehler("AUFGABENBLOCKIERT", "Nicht alle Aufgaben konnten ausgeführt werden.", offene=offen)
                return ergebnisse
            for aufgabe in bereit:
                if aufgabe.handler is None:
                    raise FabrikFehler("AUFGABENHANDLER_FEHLT", f"Für {aufgabe.aufgabenkennung} fehlt die Ausführung.")
                aufgabe.ergebnis=aufgabe.handler()
                aufgabe.abgeschlossen=True
                ergebnisse.append(aufgabe.ergebnis)
