from fastapi.testclient import TestClient
from fabrik_betriebssystem.api import app


def test_http_end_to_end_health_and_entity(tmp_path, monkeypatch):
    client = TestClient(app)
    h = client.get('/gesundheit')
    assert h.status_code == 200
    assert h.json()['erfolg'] is True

    entity_id = f'e2e-019-{id(client)}'
    e = client.post('/entitaeten', json={
        'entitaetskennung': entity_id,
        'entitaetstyp': 'AUSFUEHRUNGSLAUF',
        'zustand': 'INITIAL',
        'zustandsversion': 0,
    })
    assert e.status_code == 201

    r = client.get(f'/entitaeten/{entity_id}')
    assert r.status_code == 200
    assert r.json()['daten']['zustand'] == 'INITIAL'
