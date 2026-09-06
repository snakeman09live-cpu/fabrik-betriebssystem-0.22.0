from __future__ import annotations
from dataclasses import dataclass
from .kern import FabrikFehler

@dataclass(frozen=True)
class Vertragsreferenz:
    vertragskennung: str
    vertragsversion: str
    schemakennung: str
    schemaversion: str

class Vertragsdienst:
    def __init__(self) -> None:
        self._vertraege: dict[tuple[str, str], Vertragsreferenz] = {}

    def registrieren(self, vertrag: Vertragsreferenz) -> None:
        key = (vertrag.vertragskennung, vertrag.vertragsversion)
        vorhanden = self._vertraege.get(key)
        if vorhanden is not None and vorhanden != vertrag:
            raise FabrikFehler("VERTRAGSKONFLIKT", "Veröffentlichte Vertragsversion ist unveränderlich.")
        self._vertraege[key] = vertrag

    def aufloesen(self, kennung: str, version: str) -> Vertragsreferenz:
        vertrag = self._vertraege.get((kennung, version))
        if vertrag is None:
            raise FabrikFehler("VERTRAG_VERSION_UNGUELTIG", "Vertrag oder Version ist nicht registriert.")
        return vertrag

    def alle(self) -> list[Vertragsreferenz]:
        return sorted(self._vertraege.values(), key=lambda x: (x.vertragskennung, x.vertragsversion))
