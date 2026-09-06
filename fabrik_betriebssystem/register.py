from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from .kern import FabrikFehler

@dataclass(frozen=True)
class Vertragseintrag:
    vertragskennung: str
    vertragsversion: str
    schemakennung: str
    schemaversion: str
    vertragsart: str
    zustand: str = "AKTIV"

class Vertragsregister:
    def __init__(self):
        self._werte: dict[tuple[str, str], Vertragseintrag] = {}

    def registrieren(self, eintrag: Vertragseintrag) -> None:
        key = (eintrag.vertragskennung, eintrag.vertragsversion)
        if key in self._werte and self._werte[key] != eintrag:
            raise FabrikFehler("VERTRAGSKONFLIKT", "Eine veröffentlichte Vertragsversion darf nicht verändert werden.")
        self._werte[key] = eintrag

    def aufloesen(self, kennung: str, version: str) -> Vertragseintrag:
        eintrag = self._werte.get((kennung, version))
        if eintrag is None:
            raise FabrikFehler("VERTRAG_VERSION_UNGUELTIG", "Vertrag oder Vertragsversion ist nicht registriert.")
        if eintrag.zustand != "AKTIV":
            raise FabrikFehler("VERTRAG_NICHT_AKTIV", "Vertrag ist nicht aktiv.")
        return eintrag

class Schemaregister:
    def __init__(self, schema_verzeichnis: str | Path):
        self.verzeichnis = Path(schema_verzeichnis)
        self.verzeichnis.mkdir(parents=True, exist_ok=True)

    def laden(self, schemakennung: str, schemaversion: str) -> dict:
        pfad = self.verzeichnis / f"{schemakennung.lower()}-{schemaversion}.json"
        if not pfad.exists():
            raise FabrikFehler("SCHEMA_NICHT_GEFUNDEN", "Schema ist nicht registriert.", pfad=str(pfad))
        try:
            return json.loads(pfad.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise FabrikFehler("SCHEMA_UNGUELTIG", "Schema ist kein gültiges JSON.") from exc
