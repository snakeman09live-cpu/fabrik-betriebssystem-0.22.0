from __future__ import annotations
from enum import Enum
from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class Zustand(str, Enum):
    INITIAL="INITIAL"; VORBEREITUNG="VORBEREITUNG"; BEREIT="BEREIT"; WARTEND="WARTEND"; AKTIV="AKTIV"; PAUSIERT="PAUSIERT"; BLOCKIERT="BLOCKIERT"; FEHLERBEHANDLUNG="FEHLERBEHANDLUNG"; WIEDERHERSTELLUNG="WIEDERHERSTELLUNG"; ABSCHLUSSBEARBEITUNG="ABSCHLUSSBEARBEITUNG"; ABGESCHLOSSEN="ABGESCHLOSSEN"; FEHLGESCHLAGEN="FEHLGESCHLAGEN"; ABGEBROCHEN="ABGEBROCHEN"; ZURUECKGESETZT="ZURUECKGESETZT"; ABGELAUFEN="ABGELAUFEN"; ABGELOEST="ABGELOEST"; AUSSER_BETRIEB="AUSSER_BETRIEB"

class Aktion(str, Enum):
    ERSTELLEN="ERSTELLEN"; VORBEREITEN="VORBEREITEN"; STARTEN="STARTEN"; EINREIHEN="EINREIHEN"; WARTEN="WARTEN"; FORTSETZEN="FORTSETZEN"; PAUSIEREN="PAUSIEREN"; ABBRECHEN="ABBRECHEN"; WIEDERHOLUNGSVERSUCH="WIEDERHOLUNGSVERSUCH"; NEUAUSFUEHRUNG="NEUAUSFUEHRUNG"; NEUPLANUNG="NEUPLANUNG"; WIEDERHERSTELLEN="WIEDERHERSTELLEN"; ZURUECKSETZEN="ZURUECKSETZEN"; ABSCHLIESSEN="ABSCHLIESSEN"; FEHLSCHLAGEN="FEHLSCHLAGEN"; HOEHERSTUFEN="HOEHERSTUFEN"; BEREITSTELLEN="BEREITSTELLEN"; AKTIVIEREN="AKTIVIEREN"; ABLAUFEN_LASSEN="ABLAUFEN_LASSEN"; ABLOESEN="ABLOESEN"; AUSSER_BETRIEB_NEHMEN="AUSSER_BETRIEB_NEHMEN"

class Entitaetstyp(str, Enum):
    AUSFUEHRUNGSLAUF="AUSFUEHRUNGSLAUF"; AUFGABE="AUFGABE"; BAUVORGANG="BAUVORGANG"; BEREITSTELLUNG="BEREITSTELLUNG"; ARTEFAKT="ARTEFAKT"; GENEHMIGUNG="GENEHMIGUNG"; BETRIEBSSTOERUNG="BETRIEBSSTOERUNG"; PROJEKT="PROJEKT"; FABRIK="FABRIK"; AUSFUEHRUNGSEINHEIT="AUSFUEHRUNGSEINHEIT"; RESSOURCE="RESSOURCE"

class Fachbereich(str, Enum):
    BENUTZER="BENUTZER"; PROJEKT="PROJEKT"; FABRIK="FABRIK"; STEUERUNG="STEUERUNG"; BETRIEB="BETRIEB"; SICHERHEIT="SICHERHEIT"; KOSTEN="KOSTEN"; QUALITAET="QUALITAET"; BEREITSTELLUNG="BEREITSTELLUNG"; WIEDERHERSTELLUNG="WIEDERHERSTELLUNG"; REGELKONFORMITAET="REGELKONFORMITAET"; RISIKO="RISIKO"

class Umgebung(str, Enum):
    SIMULATION="SIMULATION"; ENTWICKLUNG="ENTWICKLUNG"; BEREITSTELLUNGSVORSTUFE="BEREITSTELLUNGSVORSTUFE"; PRODUKTION="PRODUKTION"

class Zustaendigkeitsbereich(str, Enum):
    GESAMT="GESAMT"; ORGANISATION="ORGANISATION"; FABRIK="FABRIK"; PROJEKT="PROJEKT"; RESSOURCE="RESSOURCE"; AUSFUEHRUNGSLAUF="AUSFUEHRUNGSLAUF"; AUFGABE="AUFGABE"

class Risikostufe(str, Enum):
    KEIN_RISIKO="KEIN_RISIKO"; NIEDRIG="NIEDRIG"; MITTEL="MITTEL"; HOCH="HOCH"; KRITISCH="KRITISCH"

class Entscheidung(str, Enum):
    ZULASSEN="ZULASSEN"; MIT_BEDINGUNGEN_ZULASSEN="MIT_BEDINGUNGEN_ZULASSEN"; ABLEHNEN="ABLEHNEN"; ESKALIEREN="ESKALIEREN"

class Konfliktart(str, Enum):
    BEFUGNISKONFLIKT="BEFUGNISKONFLIKT"; RICHTLINIENKONFLIKT="RICHTLINIENKONFLIKT"; ENTSCHEIDUNGSKONFLIKT="ENTSCHEIDUNGSKONFLIKT"; GENEHMIGUNGSKONFLIKT="GENEHMIGUNGSKONFLIKT"; ZUSTANDSKONFLIKT="ZUSTANDSKONFLIKT"; RESSOURCENKONFLIKT="RESSOURCENKONFLIKT"; ZEITKONFLIKT="ZEITKONFLIKT"; VERSIONSKONFLIKT="VERSIONSKONFLIKT"; ZUSTAENDIGKEITSKONFLIKT="ZUSTAENDIGKEITSKONFLIKT"; BEDINGUNGSKONFLIKT="BEDINGUNGSKONFLIKT"

class Quelle(str, Enum):
    BENUTZER="BENUTZER"; SCHNITTSTELLE="SCHNITTSTELLE"; ARBEITSABLAUF="ARBEITSABLAUF"; SYSTEM="SYSTEM"; BETREIBER="BETREIBER"; ABLAUFPLANER="ABLAUFPLANER"; WIEDERHERSTELLUNG="WIEDERHERSTELLUNG"

class Identitaetsart(str, Enum):
    BENUTZER="BENUTZER"; DIENST="DIENST"; ARBEITSABLAUF="ARBEITSABLAUF"; SYSTEM="SYSTEM"; AUSFUEHRUNGSEINHEIT="AUSFUEHRUNGSEINHEIT"; BETREIBER="BETREIBER"

class Rolle(str, Enum):
    BENUTZER="BENUTZER"; PROJEKTVERANTWORTLICHER="PROJEKTVERANTWORTLICHER"; FABRIKVERANTWORTLICHER="FABRIKVERANTWORTLICHER"; STEUERUNGSVERANTWORTLICHER="STEUERUNGSVERANTWORTLICHER"; BETREIBER="BETREIBER"

class Fehlerklasse(str, Enum):
    ANFRAGE="ANFRAGE"; AUTHENTIFIZIERUNG="AUTHENTIFIZIERUNG"; BERECHTIGUNG="BERECHTIGUNG"; VERTRAG="VERTRAG"; SCHEMA="SCHEMA"; VALIDIERUNG="VALIDIERUNG"; ANWENDBARKEIT="ANWENDBARKEIT"; BEFUGNIS="BEFUGNIS"; RICHTLINIE="RICHTLINIE"; GENEHMIGUNG="GENEHMIGUNG"; KONFLIKT="KONFLIKT"; VERSIONSKONFLIKT="VERSIONSKONFLIKT"; NEBENLAEUFIGKEIT="NEBENLAEUFIGKEIT"; IDEMPOTENZ="IDEMPOTENZ"; RESSOURCE="RESSOURCE"; AUSFUEHRUNG="AUSFUEHRUNG"; ABHAENGIGKEIT="ABHAENGIGKEIT"; INTERN="INTERN"

def jetzt() -> datetime:
    return datetime.now(timezone.utc)

class ModellBasis(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

class Entitaet(ModellBasis):
    entitaetstyp: Entitaetstyp
    entitaetskennung: str = Field(min_length=1, max_length=255)
    organisationskennung: str | None = None
    fabrikkennung: str | None = None
    projektkennung: str | None = None

class Lebenszyklus(ModellBasis):
    zustand: Zustand
    zustandsversion: int = Field(ge=0)

class Vorgang(ModellBasis):
    aktion: Aktion
    beantragt_durch: str = Field(min_length=1)
    anfragekennung: str = Field(min_length=1)

class Anwendbarkeit(ModellBasis):
    fachbereich: Fachbereich | None = None
    umgebung: Umgebung | None = None
    zustaendigkeitsbereich: Zustaendigkeitsbereich | None = None

class Richtlinienbezug(ModellBasis):
    richtlinienkennung: str
    richtlinienversion: str

class Genehmigungsbezug(ModellBasis):
    genehmigungskennung: str | None = None
    genehmigungszustand: str

class Delegationsbezug(ModellBasis):
    delegationskennung: str | None = None
    delegationsversion: int | None = Field(default=None, ge=1)

class Steuerung(ModellBasis):
    risiko: Risikostufe | None = None
    richtlinie: Richtlinienbezug | None = None
    genehmigung: Genehmigungsbezug | None = None
    delegation: Delegationsbezug | None = None

class Ausfuehrung(ModellBasis):
    faehigkeiten: list[str] = Field(default_factory=list)
    benoetigte_ressourcen: list[str] = Field(default_factory=list)
    ressourcenverfuegbarkeit: str | None = None

class Nebenlaeufigkeit(ModellBasis):
    erwartete_zustandsversion: int | None = Field(default=None, ge=0)
    idempotenzkennung: str | None = None

class Zeitbezug(ModellBasis):
    beobachtet_am: datetime
    gueltig_ab: datetime

class Herkunft(ModellBasis):
    quelle: Quelle
    zusammenhangskennung: str
    ablaufverfolgungskennung: str

class Uebergangskontext(ModellBasis):
    kontextkennung: str
    kontextversion: str
    entitaet: Entitaet
    lebenszyklus: Lebenszyklus
    vorgang: Vorgang
    anwendbarkeit: Anwendbarkeit
    steuerung: Steuerung
    ausfuehrung: Ausfuehrung
    nebenlaeufigkeit: Nebenlaeufigkeit
    zeitbezug: Zeitbezug
    herkunft: Herkunft

class Befugnis(ModellBasis):
    befugniskennung: str
    identitaetskennung: str
    rolle: Rolle
    fachbereich: Fachbereich
    zustaendigkeitsbereich: Zustaendigkeitsbereich
    aktionen: list[Aktion]
    risikogrenze: Risikostufe
    gueltig_ab: datetime
    gueltig_bis: datetime | None = None
    delegationskennung: str | None = None

class Richtlinienregel(ModellBasis):
    regelkennung: str
    aktion: Aktion
    fachbereich: Fachbereich | None = None
    umgebung: Umgebung | None = None
    risikogrenze: Risikostufe | None = None
    wirkung: Entscheidung
    nicht_ueberschreibbar: bool = False
    begruendung: str = ""

class Richtlinie(ModellBasis):
    richtlinienkennung: str
    richtlinienversion: str
    regeln: list[Richtlinienregel]
    aktiv: bool = True

class Delegation(ModellBasis):
    delegationskennung: str
    delegationsversion: int = Field(ge=1)
    delegiert_durch: str
    empfaenger: str
    rolle: Rolle
    fachbereich: Fachbereich
    zustaendigkeitsbereich: Zustaendigkeitsbereich
    aktionen: list[Aktion]
    risikogrenze: Risikostufe
    umgebungen: list[Umgebung] = Field(default_factory=list)
    gueltig_ab: datetime
    gueltig_bis: datetime | None = None
    aktiv: bool = True

class Entscheidungsinput(ModellBasis):
    kontext: Uebergangskontext
    befund: dict[str, Any] = Field(default_factory=dict)
    empfehlungen: list[dict[str, Any]] = Field(default_factory=list)
    nachweise: list[str] = Field(default_factory=list)

class Entscheidungsresultat(ModellBasis):
    entscheidungskennung: str
    entscheidung: Entscheidung
    entscheidungsbefugnis: str | None = None
    begruendung: str
    bedingungen: list[str] = Field(default_factory=list)
    konfliktkennungen: list[str] = Field(default_factory=list)
    richtlinienversionen: list[str] = Field(default_factory=list)

class Uebergang(ModellBasis):
    uebergangskennung: str
    uebergangsversion: str
    entitaetstyp: Entitaetstyp
    ausgangszustand: Zustand
    aktion: Aktion
    zielzustand: Zustand
    fachbereich: Fachbereich | None = None
    umgebung: Umgebung | None = None
    zustaendigkeitsbereich: Zustaendigkeitsbereich | None = None
    gueltig_ab: datetime | None = None
    gueltig_bis: datetime | None = None

class Nachweis(ModellBasis):
    nachweiskennung: str
    nachweisart: str
    vorgangskennung: str
    entitaetskennung: str
    vertragskennung: str | None = None
    vertragsversion: str | None = None
    schemakennung: str | None = None
    schemaversion: str | None = None
    entscheidungskennung: str | None = None
    uebergangskennung: str | None = None
    vorheriger_zustand: Zustand | None = None
    neuer_zustand: Zustand | None = None
    vorherige_zustandsversion: int | None = None
    neue_zustandsversion: int | None = None
    inhaltsfingerabdruck: str
    erzeugt_am: datetime = Field(default_factory=jetzt)

class Ereignis(ModellBasis):
    ereigniskennung: str
    ereignisart: str
    entitaetskennung: str
    vorgangskennung: str | None = None
    vorheriger_zustand: Zustand | None = None
    neuer_zustand: Zustand | None = None
    vorherige_zustandsversion: int | None = None
    neue_zustandsversion: int | None = None
    zeitpunkt: datetime = Field(default_factory=jetzt)
    zusammenhangskennung: str
    ablaufverfolgungskennung: str
    sequenznummer: int | None = None

class Fehler(ModellBasis):
    fehlerkennung: str
    fehlerklasse: Fehlerklasse
    meldung: str
    wiederholbar: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
