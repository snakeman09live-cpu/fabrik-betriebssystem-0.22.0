from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Any
import uuid

@dataclass(frozen=True)
class Nachricht:
    nachrichtenkennung: str
    nachrichtenart: str
    ereignisart: str
    entitaetskennung: str
    vorgangskennung: str | None
    zusammenhangskennung: str
    ablaufverfolgungskennung: str
    daten: dict[str, Any]
    erzeugt_am: datetime
    sequenznummer: int

class Ereignisbus:
    def __init__(self) -> None:
        self._abonenten: list[tuple[Callable[[Nachricht], None], set[str] | None]] = []
        self._nachrichten: list[Nachricht] = []
        self._sequenz = 0

    def abonnieren(self, handler: Callable[[Nachricht], None], ereignisarten: set[str] | None = None) -> None:
        self._abonenten.append((handler, ereignisarten))

    def veroeffentlichen(self, ereignisart: str, entitaetskennung: str, daten: dict[str, Any], vorgangskennung: str | None = None,
                         zusammenhangskennung: str | None = None, ablaufverfolgungskennung: str | None = None) -> Nachricht:
        self._sequenz += 1
        n = Nachricht(str(uuid.uuid4()), 'EREIGNIS', ereignisart, entitaetskennung, vorgangskennung,
                      zusammenhangskennung or str(uuid.uuid4()), ablaufverfolgungskennung or str(uuid.uuid4()), daten,
                      datetime.now(timezone.utc), self._sequenz)
        self._nachrichten.append(n)
        for handler, filterarten in tuple(self._abonenten):
            if filterarten is None or ereignisart in filterarten:
                handler(n)
        return n

    def alle(self) -> list[Nachricht]:
        return list(self._nachrichten)

    def seit(self, sequenznummer: int) -> list[Nachricht]:
        return [x for x in self._nachrichten if x.sequenznummer > sequenznummer]
