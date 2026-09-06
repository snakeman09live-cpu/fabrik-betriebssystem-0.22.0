from __future__ import annotations
from dataclasses import dataclass
from .produktionsbetrieb import Produktionsbetrieb, BetriebsKonfiguration
from .orchestrierung import Orchestrator
from .governance import GovernanceDienst
from .sicherheit import Sicherheitsdienst
from .register import Vertragsregister, Schemaregister
from .vertragsdienst import Vertragsdienst
from .outbox import AusgabepufferDienst
from .normalisierung import schema_synchronisieren
from .verteilte_sicherheit import InboxDienst, TransaktionalerAusgabepuffer
from pathlib import Path

@dataclass
class FabrikAnwendung:
    betrieb: Produktionsbetrieb
    orchestrator: Orchestrator
    governance: GovernanceDienst
    sicherheit: Sicherheitsdienst
    vertraege: Vertragsregister
    schemata: Schemaregister
    ausgabepuffer: AusgabepufferDienst
    inbox: InboxDienst
    transaktionaler_ausgabepuffer: TransaktionalerAusgabepuffer

def anwendung_erstellen(konfiguration: BetriebsKonfiguration | None = None) -> FabrikAnwendung:
    betrieb = Produktionsbetrieb(konfiguration)
    orchestrator = Orchestrator(betrieb.db)
    governance = GovernanceDienst(orchestrator.befugnis, orchestrator.richtlinie)
    sicherheit = Sicherheitsdienst(orchestrator.befugnis)
    vertraege = Vertragsregister()
    schemata = Schemaregister(Path(__file__).resolve().parent.parent / 'schemas')
    schema_synchronisieren(betrieb.db)
    ausgabepuffer = AusgabepufferDienst(betrieb.db)
    return FabrikAnwendung(betrieb, orchestrator, governance, sicherheit, vertraege, schemata, ausgabepuffer, InboxDienst(betrieb.db), TransaktionalerAusgabepuffer(betrieb.db))
