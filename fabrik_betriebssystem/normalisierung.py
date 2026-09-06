from __future__ import annotations
from pathlib import Path

from .persistenz import Basis, Datenbank
from .verteilte_sicherheit import AusgabepufferLease, Eingangsverarbeitung


def schema_synchronisieren(db: Datenbank) -> None:
    """Erzeugt die zusätzlichen verteilten Konsistenzobjekte idempotent."""
    Basis.metadata.create_all(db.engine, tables=[AusgabepufferLease.__table__, Eingangsverarbeitung.__table__])
