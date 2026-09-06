from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

@dataclass(frozen=True)
class Pruefergebnis:
    name: str
    gesund: bool
    details: str = ''

class Gesundheitsdienst:
    def __init__(self): self._pruefer: dict[str, Callable[[], Pruefergebnis]] = {}
    def registrieren(self, name: str, pruefer: Callable[[], Pruefergebnis]) -> None: self._pruefer[name]=pruefer
    def pruefen(self) -> dict:
        ergebnisse=[]
        for name,p in self._pruefer.items():
            try: ergebnisse.append(p())
            except Exception as exc: ergebnisse.append(Pruefergebnis(name,False,str(exc)))
        return {'zeitpunkt':datetime.now(timezone.utc).isoformat(),'gesund':all(x.gesund for x in ergebnisse),'pruefungen':[x.__dict__ for x in ergebnisse]}
    def bereitschaft(self) -> dict:
        daten=self.pruefen(); return {'bereit': daten['gesund'], **daten}
