from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from .modelle import Entscheidung, Aktion, Rolle, Fachbereich, Zustaendigkeitsbereich, Umgebung, Risikostufe, Delegation, Richtlinie
from .kern import FabrikFehler, Befugnisdienst, Richtliniendienst

_RANG = {Risikostufe.KEIN_RISIKO:0,Risikostufe.NIEDRIG:1,Risikostufe.MITTEL:2,Risikostufe.HOCH:3,Risikostufe.KRITISCH:4}

@dataclass(frozen=True)
class Genehmigung:
    genehmigungskennung: str
    vorgangskennung: str
    aktion: Aktion
    beantragt_durch: str
    genehmigt_durch: str | None
    zustand: str
    gueltig_ab: datetime
    gueltig_bis: datetime | None = None
    grund: str = ""

class GovernanceDienst:
    """Persistenzunabhängiger Governance-Dienst; Persistenz wird optional über Adapter angebunden."""
    def __init__(self, befugnisdienst: Befugnisdienst, richtliniendienst: Richtliniendienst):
        self.befugnisdienst = befugnisdienst
        self.richtliniendienst = richtliniendienst
        self.genehmigungen: dict[str, Genehmigung] = {}
        self.delegationen: dict[str, Delegation] = {}

    def delegation_registrieren(self, d: Delegation) -> None:
        if d.delegiert_durch == d.empfaenger:
            raise FabrikFehler("SELBSTDELEGATION_VERBOTEN", "SELBSTDELEGATION_VERBOTEN: Eine Delegation an sich selbst ist nicht zulässig.")
        if d.gueltig_bis is not None and d.gueltig_bis <= d.gueltig_ab:
            raise FabrikFehler("DELEGATION_GUELTIGKEIT_UNGUELTIG", "Delegationszeitraum ist ungültig.")
        self.delegationen[d.delegationskennung] = d
        self.befugnisdienst.delegieren(d)

    def genehmigung_beantragen(self, vorgang: str, aktion: Aktion, beantragt_durch: str, grund: str = "") -> Genehmigung:
        g = Genehmigung(str(uuid.uuid4()), vorgang, Aktion(aktion), beantragt_durch, None, "ANGEFORDERT", datetime.now(timezone.utc), None, grund)
        self.genehmigungen[g.genehmigungskennung] = g
        return g

    def genehmigen(self, kennung: str, durch: str, unabhaengig_von: str | None = None) -> Genehmigung:
        g = self.genehmigungen.get(kennung)
        if not g:
            raise FabrikFehler("GENEHMIGUNG_NICHT_GEFUNDEN", "Genehmigung wurde nicht gefunden.")
        if g.zustand != "ANGEFORDERT":
            raise FabrikFehler("GENEHMIGUNG_ZUSTAND_UNGUELTIG", "Genehmigung ist in diesem Zustand nicht genehmigbar.")
        if durch == g.beantragt_durch:
            raise FabrikFehler("SELBSTGENEHMIGUNG_VERBOTEN", "SELBSTGENEHMIGUNG_VERBOTEN: Antragsteller und Genehmiger müssen getrennt sein.")
        if unabhaengig_von is not None and durch == unabhaengig_von:
            raise FabrikFehler("GENEHMIGUNG_ABHAENGIGKEIT_UNGUELTIG", "Genehmiger ist nicht unabhängig.")
        g = Genehmigung(g.genehmigungskennung,g.vorgangskennung,g.aktion,g.beantragt_durch,durch,"GENEHMIGT",g.gueltig_ab,g.gueltig_bis,g.grund)
        self.genehmigungen[kennung] = g
        return g

    def ablehnen(self, kennung: str, durch: str, grund: str) -> Genehmigung:
        g = self.genehmigungen.get(kennung)
        if not g:
            raise FabrikFehler("GENEHMIGUNG_NICHT_GEFUNDEN", "Genehmigung wurde nicht gefunden.")
        if durch == g.beantragt_durch:
            raise FabrikFehler("SELBSTGENEHMIGUNG_VERBOTEN", "Antragsteller darf den eigenen Antrag nicht ablehnen.")
        g = Genehmigung(g.genehmigungskennung,g.vorgangskennung,g.aktion,g.beantragt_durch,durch,"ABGELEHNT",g.gueltig_ab,g.gueltig_bis,grund)
        self.genehmigungen[kennung] = g
        return g

    def genehmigung_pruefen(self, kennung: str, vorgang: str, aktion: Aktion) -> Genehmigung:
        g = self.genehmigungen.get(kennung)
        if not g:
            raise FabrikFehler("GENEHMIGUNG_NICHT_GEFUNDEN", "Genehmigung wurde nicht gefunden.")
        now = datetime.now(timezone.utc)
        if g.vorgangskennung != vorgang or g.aktion != aktion:
            raise FabrikFehler("GENEHMIGUNG_KONTEXT_UNGUELTIG", "GENEHMIGUNG_KONTEXT_UNGUELTIG: Genehmigung passt nicht zum Vorgang.")
        if g.zustand != "GENEHMIGT":
            raise FabrikFehler("GENEHMIGUNG_FEHLT", "Erforderliche Genehmigung wurde nicht erteilt.")
        if now < g.gueltig_ab or (g.gueltig_bis and now >= g.gueltig_bis):
            raise FabrikFehler("GENEHMIGUNG_ABGELAUFEN", "Genehmigung ist nicht mehr gültig.")
        return g
