from datetime import datetime, timezone, timedelta
from .persistenz import Datenbank
from .orchestrierung import Orchestrator
from .modelle import *


def beispiel() -> dict:
    db = Datenbank('sqlite+pysqlite:///:memory:')
    o = Orchestrator(db)
    o.uebergaenge.registrieren(Uebergang(
        uebergangskennung='start-ausfuehrung-1', uebergangsversion='1.0.0',
        entitaetstyp=Entitaetstyp.AUSFUEHRUNGSLAUF,
        ausgangszustand=Zustand.BEREIT, aktion=Aktion.STARTEN,
        zielzustand=Zustand.AKTIV, fachbereich=Fachbereich.BETRIEB,
        umgebung=Umgebung.ENTWICKLUNG,
        zustaendigkeitsbereich=Zustaendigkeitsbereich.AUSFUEHRUNGSLAUF))
    o.befugnis.registrieren(Befugnis(
        befugniskennung='befugnis-demo', identitaetskennung='benutzer-demo',
        rolle=Rolle.BENUTZER, fachbereich=Fachbereich.BETRIEB,
        zustaendigkeitsbereich=Zustaendigkeitsbereich.AUSFUEHRUNGSLAUF,
        aktionen=[Aktion.STARTEN], risikogrenze=Risikostufe.NIEDRIG,
        gueltig_ab=datetime.now(timezone.utc)-timedelta(minutes=1)))
    o.richtlinie.registrieren(Richtlinie(
        richtlinienkennung='richtlinie-demo', richtlinienversion='1.0.0', regeln=[]))
    db.entitaet_anlegen('lauf-demo','AUSFUEHRUNGSLAUF','BEREIT',0)
    c=Uebergangskontext(
        kontextkennung='kontext-demo',kontextversion='1.0.0',
        entitaet={'entitaetstyp':'AUSFUEHRUNGSLAUF','entitaetskennung':'lauf-demo'},
        lebenszyklus={'zustand':'BEREIT','zustandsversion':0},
        vorgang={'aktion':'STARTEN','beantragt_durch':'benutzer-demo','anfragekennung':'anfrage-demo'},
        anwendbarkeit={'fachbereich':'BETRIEB','umgebung':'ENTWICKLUNG','zustaendigkeitsbereich':'AUSFUEHRUNGSLAUF'},
        steuerung={'risiko':'NIEDRIG','richtlinie':{'richtlinienkennung':'richtlinie-demo','richtlinienversion':'1.0.0'},'genehmigung':{'genehmigungszustand':'NICHT_ERFORDERLICH'}},
        ausfuehrung={},nebenlaeufigkeit={'erwartete_zustandsversion':0,'idempotenzkennung':'idem-demo'},
        zeitbezug={'beobachtet_am':datetime.now(timezone.utc),'gueltig_ab':datetime.now(timezone.utc)},
        herkunft={'quelle':'BENUTZER','zusammenhangskennung':'zusammenhang-demo','ablaufverfolgungskennung':'spur-demo'})
    return o.transition(c,Rolle.BENUTZER)

if __name__ == '__main__':
    print(beispiel())
