from __future__ import annotations
from dataclasses import dataclass
import time

@dataclass(frozen=True)
class Messpunkt:
    name: str
    wert: float
    zeitpunkt: float

class Metriken:
    def __init__(self): self._werte: list[Messpunkt]=[]
    def erfassen(self,name: str, wert: float) -> Messpunkt:
        m=Messpunkt(name,wert,time.time()); self._werte.append(m); return m
    def letzte(self,name: str) -> Messpunkt|None:
        for m in reversed(self._werte):
            if m.name==name: return m
        return None
