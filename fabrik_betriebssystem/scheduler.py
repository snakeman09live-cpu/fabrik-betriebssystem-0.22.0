from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from .worker import Arbeitswarteschlange

@dataclass(order=True)
class GeplanterVorgang:
    ausfuehrungszeitpunkt: datetime
    vorgangskennung: str = field(compare=False)

class Ablaufplaner:
    def __init__(self, warteschlange: Arbeitswarteschlange):
        self.warteschlange = warteschlange
        self._plaene: list[GeplanterVorgang] = []

    def planen(self, vorgangskennung: str, ausfuehrungszeitpunkt: datetime | None = None):
        zeitpunkt = ausfuehrungszeitpunkt or datetime.now(timezone.utc)
        self._plaene.append(GeplanterVorgang(zeitpunkt, vorgangskennung))
        self._plaene.sort()
        return vorgangskennung

    def faellige_einreihen(self, jetzt: datetime | None = None) -> list[str]:
        zeitpunkt = jetzt or datetime.now(timezone.utc)
        faellig = [x for x in self._plaene if x.ausfuehrungszeitpunkt <= zeitpunkt]
        self._plaene = [x for x in self._plaene if x.ausfuehrungszeitpunkt > zeitpunkt]
        for x in faellig:
            self.warteschlange.einreihen(x.vorgangskennung)
        return [x.vorgangskennung for x in faellig]
