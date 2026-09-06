from dataclasses import dataclass
from datetime import datetime, timezone
from .modelle import Risikostufe

@dataclass(frozen=True)
class Ressourcenbestand:
    ressourcenkennung: str
    kapazitaet_gesamt: float
    kapazitaet_verfuegbar: float
    kosten_pro_einheit: float = 0.0

@dataclass(frozen=True)
class Budget:
    budgetkennung: str
    grenze: float
    verbrauch: float = 0.0
    reserviert: float = 0.0

    @property
    def verfuegbar(self) -> float:
        return self.grenze - self.verbrauch - self.reserviert

class KostenDienst:
    def schaetzen(self, menge: float, kosten_pro_einheit: float) -> dict:
        erwartet = menge * kosten_pro_einheit
        return {"mindestkosten": erwartet, "erwartete_kosten": erwartet, "hoechstkosten": erwartet}

    def budget_pruefen(self, budget: Budget, schaetzung: dict) -> str:
        if schaetzung["erwartete_kosten"] <= budget.verfuegbar:
            return "ZULAESSIG"
        return "BLOCKIERT"
