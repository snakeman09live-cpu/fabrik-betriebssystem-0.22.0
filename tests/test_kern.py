from datetime import datetime, timezone, timedelta
from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.orchestrierung import Orchestrator
from fabrik_betriebssystem.modelle import *
from fabrik_betriebssystem.kern import Uebergangsregister, FabrikFehler


def kontext(aktion=Aktion.STARTEN,version=0):
    return Uebergangskontext(
        kontextkennung='k1',kontextversion='1.0.0',
        entitaet={'entitaetstyp':'AUSFUEHRUNGSLAUF','entitaetskennung':'lauf1'},
        lebenszyklus={'zustand':'BEREIT','zustandsversion':version},
        vorgang={'aktion':aktion,'beantragt_durch':'u1','anfragekennung':'a1'},
        anwendbarkeit={'fachbereich':'BETRIEB','umgebung':'ENTWICKLUNG','zustaendigkeitsbereich':'AUSFUEHRUNGSLAUF'},
        steuerung={'risiko':'NIEDRIG','richtlinie':{'richtlinienkennung':'r1','richtlinienversion':'1.0.0'},'genehmigung':{'genehmigungszustand':'NICHT_ERFORDERLICH'}},
        ausfuehrung={},nebenlaeufigkeit={'erwartete_zustandsversion':version,'idempotenzkennung':'i1'},
        zeitbezug={'beobachtet_am':datetime.now(timezone.utc),'gueltig_ab':datetime.now(timezone.utc)},
        herkunft={'quelle':'BENUTZER','zusammenhangskennung':'z1','ablaufverfolgungskennung':'t1'})

def setup():
    db=Datenbank('sqlite+pysqlite:///:memory:')
    o=Orchestrator(db)
    o.uebergaenge.registrieren(Uebergang(uebergangskennung='u1',uebergangsversion='1.0.0',entitaetstyp=Entitaetstyp.AUSFUEHRUNGSLAUF,ausgangszustand=Zustand.BEREIT,aktion=Aktion.STARTEN,zielzustand=Zustand.AKTIV,fachbereich=Fachbereich.BETRIEB,umgebung=Umgebung.ENTWICKLUNG,zustaendigkeitsbereich=Zustaendigkeitsbereich.AUSFUEHRUNGSLAUF))
    o.befugnis.registrieren(Befugnis(befugniskennung='b1',identitaetskennung='u1',rolle=Rolle.BENUTZER,fachbereich=Fachbereich.BETRIEB,zustaendigkeitsbereich=Zustaendigkeitsbereich.AUSFUEHRUNGSLAUF,aktionen=[Aktion.STARTEN],risikogrenze=Risikostufe.NIEDRIG,gueltig_ab=datetime.now(timezone.utc)-timedelta(days=1)))
    o.richtlinie.registrieren(Richtlinie(richtlinienkennung='r1',richtlinienversion='1.0.0',regeln=[]))
    db.entitaet_anlegen('lauf1','AUSFUEHRUNGSLAUF','BEREIT',0)
    return db,o

def test_transition():
    db,o=setup(); res=o.transition(kontext(),Rolle.BENUTZER); assert res['zielzustand']=='AKTIV'; assert res['zustandsversion']==1

def test_version_conflict():
    db,o=setup(); c=kontext(); db.zustand_aktualisieren('lauf1',0,'AKTIV')
    try: o.transition(c,Rolle.BENUTZER); assert False
    except FabrikFehler as e: assert e.code=='ZUSTAND_NICHT_AKTUELL'

def test_transition_conflict_registry():
    reg=Uebergangsregister(); common=dict(uebergangskennung='a',uebergangsversion='1.0.0',entitaetstyp=Entitaetstyp.AUSFUEHRUNGSLAUF,ausgangszustand=Zustand.BEREIT,aktion=Aktion.STARTEN,fachbereich=Fachbereich.BETRIEB,umgebung=Umgebung.ENTWICKLUNG,zustaendigkeitsbereich=Zustaendigkeitsbereich.AUSFUEHRUNGSLAUF)
    reg.registrieren(Uebergang(zielzustand=Zustand.AKTIV,**common));
    try: common2={**common, 'uebergangskennung':'b', 'uebergangsversion':'1.0.1'}; reg.registrieren(Uebergang(zielzustand=Zustand.PAUSIERT, **common2)); assert False
    except FabrikFehler as e: assert e.code=='UEBERGANGSKONFLIKT'


def test_idempotency_returns_same_result():
    db,o=setup(); c=kontext(); first=o.transition(c,Rolle.BENUTZER); second=o.transition(c,Rolle.BENUTZER); assert first==second

def test_missing_authority_is_rejected():
    db,o=setup(); c=kontext(); c.vorgang.beantragt_durch='u2'
    try: o.transition(c,Rolle.BENUTZER); assert False
    except FabrikFehler as e: assert e.code=='BEFUGNIS_FEHLT'

def test_non_overridable_deny():
    db,o=setup(); o.richtlinie.registrieren(Richtlinie(richtlinienkennung='r1',richtlinienversion='1.1.0',regeln=[Richtlinienregel(regelkennung='deny',aktion=Aktion.STARTEN,fachbereich=Fachbereich.BETRIEB,umgebung=Umgebung.ENTWICKLUNG,risikogrenze=Risikostufe.KRITISCH,wirkung=Entscheidung.ABLEHNEN,nicht_ueberschreibbar=True)]))
    c=kontext(); c.steuerung.richtlinie.richtlinienversion='1.1.0'
    try: o.transition(c,Rolle.BENUTZER); assert False
    except FabrikFehler as e: assert e.code=='ABLEHNEN'

def test_atomic_persistence_failure_does_not_change_state():
    db, _ = setup()
    try:
        db.zustandswechsel_mit_nachweis_und_ereignis('lauf1', 99, 'AKTIV',
            {'kennung':'n1','vorgang':'a1','entitaet':'lauf1','inhalt':{}},
            {'kennung':'e1','art':'ZUSTAND_AKTIV','entitaet':'lauf1','vorgang':'a1','inhalt':{}})
        assert False
    except ValueError as e:
        assert str(e) == 'VERSIONSKONFLIKT'
    e = db.entitaet_lesen('lauf1')
    assert e.zustand == 'BEREIT' and e.zustandsversion == 0
