from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Any
import json

class Nachrichtenversand(Protocol):
    def senden(self, kanal: str, nutzlast: dict[str, Any]) -> str: ...

@dataclass(frozen=True)
class AusgehendeNachricht:
    nachrichtenkennung: str
    kanal: str
    nutzlast: dict[str, Any]

class AusgabepufferDienst:
    """Transaktionales Outbox-Muster: fachliche Änderung und Nachricht werden gemeinsam gespeichert."""
    def __init__(self, db):
        self.db = db

    def noch_nicht_versendet(self, limit: int = 100) -> list[AusgehendeNachricht]:
        return self.db.outbox_lesen(limit)

    def versenden(self, versand: Nachrichtenversand, limit: int = 100) -> int:
        anzahl = 0
        for nachricht in self.db.outbox_lesen(limit):
            versand.senden(nachricht.kanal, nachricht.nutzlast)
            if self.db.outbox_bestaetigen(nachricht.nachrichtenkennung):
                anzahl += 1
        return anzahl
