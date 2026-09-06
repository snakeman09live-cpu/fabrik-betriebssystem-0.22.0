from __future__ import annotations
from dataclasses import dataclass, field
from .modelle import Entscheidung, Risikostufe

_RISIKO_RANG = {Risikostufe.KEIN_RISIKO: 0, Risikostufe.NIEDRIG: 1, Risikostufe.MITTEL: 2, Risikostufe.HOCH: 3, Risikostufe.KRITISCH: 4}

@dataclass(frozen=True)
class Entscheidungsgrundlage:
    befugnis_gueltig: bool
    richtlinienkonform: bool
    genehmigung_erforderlich: bool = False
    genehmigung_gueltig: bool = True
    sicherheit_ok: bool = True
    budget_ok: bool = True
    qualitaet_ok: bool = True
    voraussetzungen_erfuellt: bool = True
    risiko: Risikostufe = Risikostufe.KEIN_RISIKO
    risiko_grenze: Risikostufe = Risikostufe.KRITISCH
    nicht_ueberschreibbare_ablehnung: bool = False
    bedingungen: tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class Entscheidungsanalyse:
    entscheidung: Entscheidung
    begruendung: str
    bedingungen: tuple[str, ...] = ()

class Entscheidungsintelligenz:
    """Verbindliche Entscheidungslogik ohne Rollen- oder Regelpriorität."""
    def entscheiden(self, g: Entscheidungsgrundlage) -> Entscheidungsanalyse:
        if g.nicht_ueberschreibbare_ablehnung:
            return Entscheidungsanalyse(Entscheidung.ABLEHNEN, "Eine nicht überschreibbare Nebenbedingung untersagt die Handlung.")
        if not g.befugnis_gueltig:
            return Entscheidungsanalyse(Entscheidung.ESKALIEREN, "Keine ausreichende Entscheidungsbefugnis nachgewiesen.")
        if _RISIKO_RANG[g.risiko] > _RISIKO_RANG[g.risiko_grenze]:
            return Entscheidungsanalyse(Entscheidung.ESKALIEREN, "Das Risiko überschreitet die zulässige Befugnisgrenze.")
        if not g.sicherheit_ok:
            return Entscheidungsanalyse(Entscheidung.ESKALIEREN, "Sicherheitsanforderungen sind nicht erfüllt.")
        if not g.qualitaet_ok or not g.voraussetzungen_erfuellt:
            return Entscheidungsanalyse(Entscheidung.ESKALIEREN, "Erforderliche Qualitäts- oder Voraussetzungenachweise fehlen.")
        if not g.richtlinienkonform:
            return Entscheidungsanalyse(Entscheidung.ABLEHNEN, "Die Handlung ist nicht richtlinienkonform.")
        bedingungen = list(g.bedingungen)
        if g.genehmigung_erforderlich and not g.genehmigung_gueltig:
            bedingungen.append("ERFORDERLICHE_GENEHMIGUNG")
        if not g.budget_ok:
            bedingungen.append("BUDGET_PRUEFEN")
        if bedingungen:
            return Entscheidungsanalyse(Entscheidung.MIT_BEDINGUNGEN_ZULASSEN, "Die Handlung ist nur unter expliziten Bedingungen zulässig.", tuple(conditions_unique(bedingungen)))
        return Entscheidungsanalyse(Entscheidung.ZULASSEN, "Alle bekannten verbindlichen Voraussetzungen sind erfüllt.")

def conditions_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
