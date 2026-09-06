from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from .modelle import Rolle, Risikostufe, Uebergangskontext
from .kern import FabrikFehler, Befugnisdienst

@dataclass(frozen=True)
class Sicherheitspruefung:
    identitaetskennung: str
    rolle: Rolle
    befugniskennung: str
    geprueft_am: datetime

class Sicherheitsdienst:
    def __init__(self, befugnisdienst: Befugnisdienst):
        self.befugnisdienst = befugnisdienst

    def pruefen(self, c: Uebergangskontext, rolle: Rolle) -> Sicherheitspruefung:
        if not c.vorgang.beantragt_durch.strip():
            raise FabrikFehler("IDENTITAET_FEHLT", "Beantragende Identität fehlt.")
        befugnis = self.befugnisdienst.pruefen(c.vorgang.beantragt_durch, rolle, c)
        return Sicherheitspruefung(c.vorgang.beantragt_durch, rolle, befugnis.befugniskennung, datetime.now(timezone.utc))
