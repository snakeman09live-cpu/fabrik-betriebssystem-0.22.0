from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable
from .modelle import Entscheidung, Risikostufe, Uebergangskontext, Befugnis, Richtlinienregel
from .kern import FabrikFehler

_RISIKO_RANG = {
    Risikostufe.KEIN_RISIKO: 0,
    Risikostufe.NIEDRIG: 1,
    Risikostufe.MITTEL: 2,
    Risikostufe.HOCH: 3,
    Risikostufe.KRITISCH: 4,
}

@dataclass(frozen=True)
class Bewertungsgrundlage:
    risiko: Risikostufe = Risikostufe.KEIN_RISIKO
    risikogrenze: Risikostufe = Risikostufe.KRITISCH
    sicherheit_erfuellt: bool = True
    qualitaet_erfuellt: bool = True
    budget_verfuegbar: bool = True
    kapazitaet_verfuegbar: bool = True
    voraussetzungen_erfuellt: bool = True
    genehmigung_erforderlich: bool = False
    genehmigung_erteilt: bool = False
    bedingungen: tuple[str, ...] = field(default_factory=tuple)
    nicht_ueberschreibbare_ablehnung: bool = False
    widerspruechliche_entscheidungen: bool = False

@dataclass(frozen=True)
class Entscheidungspruefung:
    entscheidung: Entscheidung
    gruende: tuple[str, ...] = ()
    bedingungen: tuple[str, ...] = ()

class Entscheidungsmaschine:
    """Einheitliche Entscheidungslogik. Keine Rollen-, Regel- oder Zeitpriorität."""

    def entscheiden(self, *, befugnis: Befugnis | None, bewertung: Bewertungsgrundlage,
                    regeln: Iterable[Richtlinienregel] = ()) -> Entscheidungspruefung:
        regeln = tuple(regeln)
        aktive_denies = [r for r in regeln if r.wirkung == Entscheidung.ABLEHNEN]
        aktive_bedingungen = [r for r in regeln if r.wirkung == Entscheidung.MIT_BEDINGUNGEN_ZULASSEN]

        if befugnis is None:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("ENTSCHEIDUNGSBEFUGNIS_FEHLT",))
        if bewertung.widerspruechliche_entscheidungen:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("ENTSCHEIDUNGSKONFLIKT",))
        if bewertung.nicht_ueberschreibbare_ablehnung or any(r.nicht_ueberschreibbar for r in aktive_denies):
            return Entscheidungspruefung(Entscheidung.ABLEHNEN, ("NICHT_UEBERSCHREIBBARE_RICHTLINIE",))
        if _RISIKO_RANG[bewertung.risiko] > _RISIKO_RANG[befugnis.risikogrenze]:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("RISIKOGRENZE_UEBERSCHRITTEN",))
        if _RISIKO_RANG[bewertung.risiko] > _RISIKO_RANG[bewertung.risikogrenze]:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("BEWERTUNGSRISIKOGRENZE_UEBERSCHRITTEN",))
        if not bewertung.sicherheit_erfuellt:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("SICHERHEIT_NICHT_ERFUELLT",))
        if not bewertung.qualitaet_erfuellt:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("QUALITAET_NICHT_ERFUELLT",))
        if not bewertung.voraussetzungen_erfuellt:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("VORAUSSETZUNGEN_NICHT_ERFUELLT",))
        if aktive_denies:
            return Entscheidungspruefung(Entscheidung.ESKALIEREN, ("RICHTLINIENKONFLIKT",))

        bedingungen = list(bewertung.bedingungen)
        if aktive_bedingungen:
            bedingungen.extend(r.begruendung or r.regelkennung for r in aktive_bedingungen)
        if not bewertung.budget_verfuegbar:
            bedingungen.append("BUDGET_PRUEFEN")
        if not bewertung.kapazitaet_verfuegbar:
            bedingungen.append("KAPAZITAET_PRUEFEN")
        if bewertung.genehmigung_erforderlich and not bewertung.genehmigung_erteilt:
            bedingungen.append("GENEHMIGUNG_ERFORDERLICH")
        dedup = tuple(dict.fromkeys(bedingungen))
        if dedup:
            return Entscheidungspruefung(Entscheidung.MIT_BEDINGUNGEN_ZULASSEN, ("BEDINGUNGEN_ERFUELLEN",), dedup)
        return Entscheidungspruefung(Entscheidung.ZULASSEN, ("VERBINDLICHE_VORAUSSETZUNGEN_ERFUELLT",))

class Entscheidungsdienst08:
    def __init__(self, befugnisdienst, richtliniendienst):
        self.befugnisdienst = befugnisdienst
        self.richtliniendienst = richtliniendienst
        self.maschine = Entscheidungsmaschine()

    def pruefen(self, kontext: Uebergangskontext, rolle, bewertung: Bewertungsgrundlage) -> tuple[Befugnis, Entscheidungspruefung, list[Richtlinienregel]]:
        befugnis = self.befugnisdienst.pruefen(kontext.vorgang.beantragt_durch, rolle, kontext)
        regeln = self.richtliniendienst.bewerten(kontext)
        pruefung = self.maschine.entscheiden(befugnis=befugnis, bewertung=bewertung, regeln=regeln)
        return befugnis, pruefung, regeln
