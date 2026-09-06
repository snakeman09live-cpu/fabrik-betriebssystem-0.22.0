from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import pytest
from fabrik_betriebssystem.governance import GovernanceDienst
from fabrik_betriebssystem.kern import Befugnisdienst, Richtliniendienst, FabrikFehler
from fabrik_betriebssystem.modelle import Aktion, Rolle, Fachbereich, Zustaendigkeitsbereich, Umgebung, Risikostufe, Delegation, Uebergangskontext
from fabrik_betriebssystem.api import app, governance, db


def test_genehmigung_vier_augen():
    g = GovernanceDienst(Befugnisdienst(), Richtliniendienst())
    antrag = g.genehmigung_beantragen('vorgang-1', Aktion.STARTEN, 'alice')
    with pytest.raises(FabrikFehler, match='SELBSTGENEHMIGUNG_VERBOTEN'):
        g.genehmigen(antrag.genehmigungskennung, 'alice')
    erledigt = g.genehmigen(antrag.genehmigungskennung, 'bob')
    assert erledigt.zustand == 'GENEHMIGT'


def test_genehmigung_kontextgebunden():
    g = GovernanceDienst(Befugnisdienst(), Richtliniendienst())
    antrag = g.genehmigung_beantragen('vorgang-1', Aktion.STARTEN, 'alice')
    g.genehmigen(antrag.genehmigungskennung, 'bob')
    with pytest.raises(FabrikFehler, match='GENEHMIGUNG_KONTEXT_UNGUELTIG'):
        g.genehmigung_pruefen(antrag.genehmigungskennung, 'vorgang-2', Aktion.STARTEN)


def test_delegation_zeitraum_und_selbstdelegation():
    g = GovernanceDienst(Befugnisdienst(), Richtliniendienst())
    basis = dict(delegationskennung='d-1', delegationsversion=1, delegiert_durch='owner', empfaenger='agent',
        rolle=Rolle.PROJEKTVERANTWORTLICHER, fachbereich=Fachbereich.PROJEKT,
        zustaendigkeitsbereich=Zustaendigkeitsbereich.PROJEKT, aktionen=[Aktion.PAUSIEREN],
        risikogrenze=Risikostufe.NIEDRIG, umgebungen=[Umgebung.PRODUKTION], gueltig_ab=datetime.now(timezone.utc))
    d = Delegation(**basis)
    g.delegation_registrieren(d)
    assert d.delegationskennung in g.delegationen
    with pytest.raises(FabrikFehler, match='SELBSTDELEGATION_VERBOTEN'):
        g.delegation_registrieren(Delegation(**{**basis, 'delegationskennung':'d-2', 'empfaenger':'owner'}))


def test_genehmigungs_api():
    client = TestClient(app)
    r = client.post('/genehmigungen', json={'vorgangskennung':'v-api-1','aktion':'STARTEN','beantragt_durch':'alice','grund':'freigabe'})
    assert r.status_code == 201
    kennung = r.json()['daten']['genehmigungskennung']
    r = client.post(f'/genehmigungen/{kennung}/genehmigen', json={'durch':'bob'})
    assert r.status_code == 200
    assert r.json()['daten']['zustand'] == 'GENEHMIGT'
    r = client.post('/genehmigungen/pruefen', json={'genehmigungskennung':kennung,'vorgangskennung':'v-api-1','aktion':'STARTEN'})
    assert r.status_code == 200
