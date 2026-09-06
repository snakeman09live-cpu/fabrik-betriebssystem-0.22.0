from fastapi.testclient import TestClient
from fabrik_betriebssystem.api import app

def test_health_endpoint():
    client=TestClient(app)
    r=client.get('/gesundheit')
    assert r.status_code==200
    assert r.json()['erfolg'] is True
