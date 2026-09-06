from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from .persistenz import Datenbank
from .orchestrierung import Orchestrator
from .modelle import *
from .register import Vertragsregister, Vertragseintrag, Schemaregister
from .sicherheit import Sicherheitsdienst
from .entscheidungsintelligenz import Entscheidungsintelligenz, Entscheidungsgrundlage
from pathlib import Path
from .produktionsbetrieb import Produktionsbetrieb
from . import __version__

app=FastAPI(title='Fabrik-Betriebssystem', version=__version__)
betrieb=Produktionsbetrieb(); db=betrieb.db; orchestrator=Orchestrator(db)
vertraege=Vertragsregister(); vertraege.registrieren(Vertragseintrag('zustandsuebergang','1.0.0','zustandsuebergang','1.0.0','ZUSTANDSUEBERGANG'))
schemata=Schemaregister(Path(__file__).resolve().parent.parent / 'schemas')
sicherheit=Sicherheitsdienst(orchestrator.befugnis)

class EntitaetAnlegen(ModellBasis):
    entitaetskennung:str; entitaetstyp:Entitaetstyp; zustand:Zustand=Zustand.INITIAL; zustandsversion:int=0; organisationskennung:str|None=None; fabrikkennung:str|None=None; projektkennung:str|None=None

class Entscheidungsanfrage(ModellBasis):
    grundlage: dict

@app.get('/gesundheit')
def gesundheit(): return {'erfolg':True,'daten':betrieb.betriebspruefer.gesundheit()}

@app.get('/bereitschaft')
def bereitschaft():
    daten = betrieb.readiness_auswerten()
    if not daten['betriebsbereit']:
        raise HTTPException(503, 'DIENST_NICHT_BEREIT')
    return {'erfolg': True, 'daten': daten}

@app.get('/vertraege/{kennung}/{version}')
def vertrag_lesen(kennung: str, version: str):
    try: return {'erfolg': True, 'daten': vertraege.auflosen(kennung,version).__dict__}
    except FabrikFehler as e: raise HTTPException(409,e.code)

@app.get('/schemata/{kennung}/{version}')
def schema_lesen(kennung: str, version: str):
    try: return {'erfolg': True, 'daten': schemata.laden(kennung,version)}
    except FabrikFehler as e: raise HTTPException(404,e.code)

@app.post('/entscheidungen/pruefen')
def entscheidung_pruefen(x: Entscheidungsanfrage):
    try:
        g=Entscheidungsgrundlage(**x.grundlage)
        d=Entscheidungsintelligenz().entscheiden(g)
        return {'erfolg':True,'daten':d.__dict__}
    except Exception as e: raise HTTPException(422,str(e))

@app.post('/entitaeten',status_code=201)
def entitaet_anlegen(x:EntitaetAnlegen):
    try:
        db.entitaet_anlegen(x.entitaetskennung,getattr(x.entitaetstyp, 'value', x.entitaetstyp),getattr(x.zustand, 'value', x.zustand),x.zustandsversion,x.organisationskennung,x.fabrikkennung,x.projektkennung)
        return {'erfolg':True,'daten':x.model_dump()}
    except Exception as e: raise HTTPException(409,str(e))

@app.get('/entitaeten/{kennung}')
def entitaet_lesen(kennung:str):
    e=db.entitaet_lesen(kennung)
    if not e: raise HTTPException(404,'ENTITAET_NICHT_GEFUNDEN')
    return {'erfolg':True,'daten':{'entitaetskennung':e.kennung,'entitaetstyp':e.typ,'zustand':e.zustand,'zustandsversion':e.zustandsversion}}

@app.post('/uebergaenge/ausfuehren')
def uebergang_ausfuehren(c:Uebergangskontext, rolle:Rolle=Rolle.BENUTZER):
    try: return {'erfolg':True,'daten':orchestrator.transition(c,rolle)}
    except FabrikFehler as e: raise HTTPException(409,e.code)

from .governance import GovernanceDienst
from .kern import FabrikFehler
from pydantic import Field

governance = GovernanceDienst(orchestrator.befugnis, orchestrator.richtlinie)
# Die Governance-Tabellen werden nach Laden der Governance-Modelle angelegt.
from .persistenz import Basis as _Basis
_Basis.metadata.create_all(db.engine)

class Genehmigungsanfrage(ModellBasis):
    vorgangskennung: str = Field(min_length=1)
    aktion: Aktion
    beantragt_durch: str = Field(min_length=1)
    grund: str = ""

class Genehmigungsaktion(ModellBasis):
    durch: str = Field(min_length=1)
    grund: str = ""

class Delegationsanfrage(Delegation):
    pass

class Genehmigungspruefanfrage(ModellBasis):
    genehmigungskennung: str
    vorgangskennung: str
    aktion: Aktion

@app.post('/genehmigungen', status_code=201)
def genehmigung_anfordern(x: Genehmigungsanfrage):
    try:
        g = governance.genehmigung_beantragen(x.vorgangskennung, x.aktion, x.beantragt_durch, x.grund)
        db.genehmigung_speichern(g)
        return {'erfolg': True, 'daten': g.__dict__}
    except FabrikFehler as e:
        raise HTTPException(422, e.code)

@app.get('/genehmigungen/{kennung}')
def genehmigung_lesen(kennung: str):
    g = governance.genehmigungen.get(kennung)
    if g is None:
        row = db.genehmigung_lesen(kennung)
        if row is None:
            raise HTTPException(404, 'GENEHMIGUNG_NICHT_GEFUNDEN')
        return {'erfolg': True, 'daten': {
            'genehmigungskennung': row.kennung,
            'vorgangskennung': row.vorgang,
            'aktion': row.aktion,
            'beantragt_durch': row.beantragt_durch,
            'genehmigt_durch': row.genehmigt_durch,
            'zustand': row.zustand,
            'gueltig_ab': row.gueltig_ab,
            'gueltig_bis': row.gueltig_bis,
            'grund': row.grund,
        }}
    return {'erfolg': True, 'daten': g.__dict__}

@app.post('/genehmigungen/{kennung}/genehmigen')
def genehmigung_genehmigen(kennung: str, x: Genehmigungsaktion):
    try:
        g = governance.genehmigen(kennung, x.durch)
        db.genehmigung_speichern(g)
        return {'erfolg': True, 'daten': g.__dict__}
    except FabrikFehler as e:
        raise HTTPException(409, e.code)

@app.post('/genehmigungen/{kennung}/ablehnen')
def genehmigung_ablehnen(kennung: str, x: Genehmigungsaktion):
    try:
        g = governance.ablehnen(kennung, x.durch, x.grund)
        db.genehmigung_speichern(g)
        return {'erfolg': True, 'daten': g.__dict__}
    except FabrikFehler as e:
        raise HTTPException(409, e.code)

@app.post('/genehmigungen/pruefen')
def genehmigung_pruefen(x: Genehmigungspruefanfrage):
    try:
        g = governance.genehmigung_pruefen(x.genehmigungskennung, x.vorgangskennung, x.aktion)
        return {'erfolg': True, 'daten': g.__dict__}
    except FabrikFehler as e:
        raise HTTPException(409, e.code)

@app.post('/delegationen', status_code=201)
def delegation_anlegen(x: Delegationsanfrage):
    try:
        governance.delegation_registrieren(x)
        db.delegation_speichern(x)
        return {'erfolg': True, 'daten': x.model_dump()}
    except FabrikFehler as e:
        raise HTTPException(409, e.code)
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get('/ausgabepuffer/gesundheit')
def ausgabepuffer_gesundheit():
    offene = len(betrieb.betriebspruefer.db.outbox_lesen(1000))
    return {'erfolg': True, 'daten': {'offene_nachrichten': offene}}
