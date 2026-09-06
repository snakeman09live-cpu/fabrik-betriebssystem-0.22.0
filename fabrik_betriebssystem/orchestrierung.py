from __future__ import annotations
from dataclasses import dataclass, field
from .modelle import *
from .kern import FabrikFehler, Uebergangsregister, Kontextpruefer, Befugnisdienst, Richtliniendienst, Entscheidungsdienst, fingerabdruck
from .persistenz import Datenbank
from .nachrichten import Ereignisbus
from .vertragsdienst import Vertragsdienst, Vertragsreferenz
from .entscheidungsmaschine import Entscheidungsdienst08, Bewertungsgrundlage
from .ausfuehrungslauf import Ausfuehrungslaufdienst
import uuid

@dataclass
class Aufgabe:
    aufgabenkennung:str
    vorgang:str
    entitaetskennung:str
    aktion:Aktion
    abhaengigkeiten:list[str]=field(default_factory=list)
    abgeschlossen:bool=False

class Orchestrator:
    def __init__(self, db:Datenbank):
        self.db=db; self.ereignisbus=Ereignisbus(); self.vertraege=Vertragsdienst(); self.uebergaenge=Uebergangsregister(); self.kontext=Kontextpruefer(); self.befugnis=Befugnisdienst(); self.richtlinie=Richtliniendienst(); self.entscheidung=Entscheidungsdienst(); self.entscheidung08=Entscheidungsdienst08(self.befugnis, self.richtlinie); self.ausfuehrungslaeufe=Ausfuehrungslaufdienst(self.ereignisbus, persist=self.db.lauf_speichern)
    def transition(self,c:Uebergangskontext,rolle:Rolle):
        self.kontext.pruefen(c)
        u=self.uebergaenge.aufloesen(c)
        key=c.nebenlaeufigkeit.idempotenzkennung
        fp=fingerabdruck(c.model_dump())
        if key:
            try:
                alt=self.db.idempotenz_lesen(key,fp)
            except ValueError as exc:
                raise FabrikFehler(str(exc), 'Idempotenzkonflikt.') from exc
            if alt: return alt
        aktuelles=self.db.entitaet_lesen(c.entitaet.entitaetskennung)
        if not aktuelles: raise FabrikFehler('ENTITAET_NICHT_GEFUNDEN','Entität wurde nicht gefunden.')
        if aktuelles.zustand!=(c.lebenszyklus.zustand.value if hasattr(c.lebenszyklus.zustand, 'value') else c.lebenszyklus.zustand): raise FabrikFehler('ZUSTAND_NICHT_AKTUELL','Kontextzustand stimmt nicht mit Persistenz überein.')
        if c.nebenlaeufigkeit.erwartete_zustandsversion is not None and aktuelles.zustandsversion!=c.nebenlaeufigkeit.erwartete_zustandsversion:
            raise FabrikFehler('VERSIONSKONFLIKT','Zustandsversion ist nicht mehr aktuell.')
        bewertung=Bewertungsgrundlage(
            risiko=Risikostufe(c.steuerung.risiko or Risikostufe.KEIN_RISIKO),
            risikogrenze=Risikostufe.KRITISCH,
            sicherheit_erfuellt=True,
            qualitaet_erfuellt=True,
            budget_verfuegbar=True,
            kapazitaet_verfuegbar=True,
            voraussetzungen_erfuellt=True,
            genehmigung_erforderlich=bool(c.steuerung.genehmigung and c.steuerung.genehmigung.genehmigungszustand != 'NICHT_ERFORDERLICH'),
            genehmigung_erteilt=bool(c.steuerung.genehmigung and c.steuerung.genehmigung.genehmigungszustand == 'GENEHMIGT'),
        )
        b, d08, regeln=self.entscheidung08.pruefen(c,rolle,bewertung)
        d=Entscheidungsresultat(
            entscheidungskennung=str(uuid.uuid4()),
            entscheidung=d08.entscheidung,
            entscheidungsbefugnis=b.befugniskennung,
            begruendung='; '.join(d08.gruende),
            bedingungen=list(d08.bedingungen),
            richtlinienversionen=[c.steuerung.richtlinie.richtlinienversion] if c.steuerung.richtlinie else [],
        )
        self.db.entscheidung_speichern(d, c.vorgang.anfragekennung)
        if d.entscheidung in (Entscheidung.ABLEHNEN,Entscheidung.ESKALIEREN): raise FabrikFehler(d.entscheidung.value if hasattr(d.entscheidung, 'value') else d.entscheidung,d.begruendung,entscheidungskennung=d.entscheidungskennung)
        if d.entscheidung==Entscheidung.MIT_BEDINGUNGEN_ZULASSEN and d.bedingungen: raise FabrikFehler('BEDINGUNGEN_NICHT_ERFUELLT','Die Zulassungsbedingungen sind vor Ausführung zu erfüllen.',bedingungen=d.bedingungen,entscheidungskennung=d.entscheidungskennung)
        zielzustand = u.zielzustand.value if hasattr(u.zielzustand, 'value') else u.zielzustand
        naechste_version = aktuelles.zustandsversion + 1
        result={'entscheidungskennung':d.entscheidungskennung,'entscheidung':(d.entscheidung.value if hasattr(d.entscheidung, 'value') else d.entscheidung),'uebergangskennung':u.uebergangskennung,'zielzustand':zielzustand,'zustandsversion':naechste_version}
        nachweis={'kennung':str(uuid.uuid4()),'vorgang':c.vorgang.anfragekennung,'entitaet':c.entitaet.entitaetskennung,'inhalt':result}
        ereignis={'kennung':str(uuid.uuid4()),'art':f'ZUSTAND_{zielzustand}','entitaet':c.entitaet.entitaetskennung,'vorgang':c.vorgang.anfragekennung,'inhalt':result}
        try:
            gespeichertes=self.db.zustandswechsel_mit_nachweis_und_ereignis(
                c.entitaet.entitaetskennung, c.lebenszyklus.zustandsversion, zielzustand,
                nachweis, ereignis,
                (key, fp, __import__('json').dumps(result, ensure_ascii=False)) if key else None
            )
        except ValueError as exc:
            code=str(exc)
            raise FabrikFehler(code, 'Zustandsänderung konnte nicht atomar gespeichert werden.') from exc
        self.ereignisbus.veroeffentlichen(
            f"ZUSTAND_{zielzustand}",
            c.entitaet.entitaetskennung,
            result,
            vorgangskennung=c.vorgang.anfragekennung,
            zusammenhangskennung=c.herkunft.zusammenhangskennung,
            ablaufverfolgungskennung=c.herkunft.ablaufverfolgungskennung,
        )
        if isinstance(gespeichertes, dict):
            return gespeichertes
        return result
