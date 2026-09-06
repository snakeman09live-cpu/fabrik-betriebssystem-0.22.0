from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable

@dataclass(frozen=True)
class Pruefergebnis:
    pruefungskennung: str
    ergebnis: str
    begruendung: str
    nachweise: tuple[str, ...] = ()

@dataclass(frozen=True)
class Verifikationsergebnis:
    verifikationskennung: str
    ergebnis: str
    pruefungen: tuple[str, ...]
    nachweise: tuple[str, ...] = ()

class Qualitaetsdienst:
    def __init__(self):
        self._pruefungen: dict[str, Pruefergebnis] = {}
        self._verifikationen: dict[str, Verifikationsergebnis] = {}

    def pruefung_registrieren(self, ergebnis: Pruefergebnis) -> None:
        self._pruefungen[ergebnis.pruefungskennung] = ergebnis

    def verifikation_durchfuehren(self, kennung: str, erforderliche_pruefungen: Iterable[str]) -> Verifikationsergebnis:
        ids = tuple(erforderliche_pruefungen)
        fehlend = [x for x in ids if x not in self._pruefungen]
        nicht_bestanden = [x for x in ids if x in self._pruefungen and self._pruefungen[x].ergebnis != "BESTANDEN"]
        if fehlend or nicht_bestanden:
            ergebnis = "VERIFIKATION_FEHLGESCHLAGEN"
        else:
            ergebnis = "VERIFIZIERT"
        result = Verifikationsergebnis(kennung, ergebnis, ids)
        self._verifikationen[kennung] = result
        return result
