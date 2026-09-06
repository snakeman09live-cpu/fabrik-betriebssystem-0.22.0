from datetime import datetime, timezone, timedelta
from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.outbox import AusgabepufferDienst
from fabrik_betriebssystem.produktionsbetrieb import BetriebsKonfiguration
from fabrik_betriebssystem.anwendung import anwendung_erstellen
from fabrik_betriebssystem.orchestrierung import Orchestrator
from fabrik_betriebssystem.modelle import *


def test_outbox_ist_leer_bis_nachrichten_versendet_werden(tmp_path):
    db = Datenbank(f"sqlite+pysqlite:///{tmp_path/'a.db'}")
    db.outbox_anfuegen('n1', 'ZUSTAND_AKTIV', {'x': 1})
    dienst = AusgabepufferDienst(db)
    assert len(dienst.noch_nicht_versendet()) == 1
    class Versand:
        def __init__(self): self.werte=[]
        def senden(self, kanal, nutzlast): self.werte.append((kanal,nutzlast)); return 'ok'
    v=Versand()
    assert dienst.versenden(v) == 1
    assert dienst.noch_nicht_versendet() == []
    assert v.werte[0][0] == 'ZUSTAND_AKTIV'


def test_outbox_doppelte_kennung_ist_idempotent(tmp_path):
    db = Datenbank(f"sqlite+pysqlite:///{tmp_path/'b.db'}")
    db.outbox_anfuegen('n1', 'A', {'x': 1})
    db.outbox_anfuegen('n1', 'A', {'x': 2})
    offene = db.outbox_lesen()
    assert len(offene) == 1 and offene[0].nutzlast == {'x': 1}


def test_anwendung_ist_zentral_konstruiert(tmp_path):
    cfg = BetriebsKonfiguration(datenbank_url=f"sqlite+pysqlite:///{tmp_path/'c.db'}")
    anwendung = anwendung_erstellen(cfg)
    assert anwendung.betrieb.db is not None
    assert anwendung.orchestrator.db is anwendung.betrieb.db
    assert anwendung.ausgabepuffer.db is anwendung.betrieb.db


def _setup_transition(tmp_path):
    db = Datenbank(f"sqlite+pysqlite:///{tmp_path/'d.db'}")
    o = Orchestrator(db)
    o.uebergaenge.registrieren(Uebergang(
        uebergangskennung='u1', uebergangsversion='1.0.0',
        entitaetstyp=Entitaetstyp.AUSFUEHRUNGSLAUF,
        ausgangszustand=Zustand.BEREIT, aktion=Aktion.STARTEN,
        zielzustand=Zustand.AKTIV, fachbereich=Fachbereich.BETRIEB,
        umgebung=Umgebung.ENTWICKLUNG,
        zustaendigkeitsbereich=Zustaendigkeitsbereich.AUSFUEHRUNGSLAUF))
    o.befugnis.registrieren(Befugnis(
        befugniskennung='b1', identitaetskennung='u1', rolle=Rolle.BENUTZER,
        fachbereich=Fachbereich.BETRIEB,
        zustaendigkeitsbereich=Zustaendigkeitsbereich.AUSFUEHRUNGSLAUF,
        aktionen=[Aktion.STARTEN], risikogrenze=Risikostufe.NIEDRIG,
        gueltig_ab=datetime.now(timezone.utc)-timedelta(days=1)))
    o.richtlinie.registrieren(Richtlinie(richtlinienkennung='r1', richtlinienversion='1.0.0', regeln=[]))
    db.entitaet_anlegen('lauf1','AUSFUEHRUNGSLAUF','BEREIT',0)
    c=Uebergangskontext(
        kontextkennung='k1',kontextversion='1.0.0',
        entitaet={'entitaetstyp':'AUSFUEHRUNGSLAUF','entitaetskennung':'lauf1'},
        lebenszyklus={'zustand':'BEREIT','zustandsversion':0},
        vorgang={'aktion':'STARTEN','beantragt_durch':'u1','anfragekennung':'a1'},
        anwendbarkeit={'fachbereich':'BETRIEB','umgebung':'ENTWICKLUNG','zustaendigkeitsbereich':'AUSFUEHRUNGSLAUF'},
        steuerung={'risiko':'NIEDRIG','richtlinie':{'richtlinienkennung':'r1','richtlinienversion':'1.0.0'},'genehmigung':{'genehmigungszustand':'NICHT_ERFORDERLICH'}},
        ausfuehrung={},nebenlaeufigkeit={'erwartete_zustandsversion':0,'idempotenzkennung':'i1'},
        zeitbezug={'beobachtet_am':datetime.now(timezone.utc),'gueltig_ab':datetime.now(timezone.utc)},
        herkunft={'quelle':'BENUTZER','zusammenhangskennung':'z1','ablaufverfolgungskennung':'t1'})
    return db,o,c


def test_zustandswechsel_erzeugt_transaktionale_outbox(tmp_path):
    db,o,c=_setup_transition(tmp_path)
    result=o.transition(c,Rolle.BENUTZER)
    assert result['zielzustand']=='AKTIV'
    offene=db.outbox_lesen()
    assert len(offene)==1
    assert offene[0].kanal=='ZUSTAND_AKTIV'
