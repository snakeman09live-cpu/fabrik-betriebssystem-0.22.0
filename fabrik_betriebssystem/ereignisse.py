from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from threading import RLock
from typing import Callable
from .modelle import Ereignis

@dataclass
class Ereignisbus:
    _abonenten: dict[str, list[Callable[[Ereignis], None]]] = field(default_factory=lambda: defaultdict(list))
    _verlauf: list[Ereignis] = field(default_factory=list)
    _kennungen: set[str] = field(default_factory=set)
    _sperre: RLock = field(default_factory=RLock)

    def abonnieren(self, ereignisart: str, empfaenger: Callable[[Ereignis], None]) -> None:
        with self._sperre:
            self._abonenten[ereignisart].append(empfaenger)

    def veroeffentlichen(self, ereignis: Ereignis) -> bool:
        with self._sperre:
            if ereignis.ereigniskennung in self._kennungen:
                return False
            self._kennungen.add(ereignis.ereigniskennung)
            self._verlauf.append(ereignis)
            empfaenger = list(self._abonenten.get(ereignis.ereignisart, ()))
            empfaenger += list(self._abonenten.get("*", ()))
        for fn in empfaenger:
            fn(ereignis)
        return True

    def verlauf(self) -> list[Ereignis]:
        with self._sperre:
            return list(self._verlauf)
