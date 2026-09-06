from dataclasses import dataclass
from .modelle import Risikostufe

@dataclass(frozen=True)
class Messung:
    messungskennung: str
    messart: str
    wert: float
    grenze: float

class Ueberwachungsdienst:
    def anomalie(self, messung: Messung) -> bool:
        return messung.wert > messung.grenze

    def bewerten(self, messung: Messung) -> dict:
        return {"messungskennung": messung.messungskennung, "anomalie": self.anomalie(messung), "wert": messung.wert, "grenze": messung.grenze}
