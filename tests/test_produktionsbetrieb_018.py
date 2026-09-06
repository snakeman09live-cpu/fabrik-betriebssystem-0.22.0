from fabrik_betriebssystem.produktionsbetrieb import (
    BetriebsKonfiguration, LokalerNachrichtenbroker, Produktionsbetrieb
)


def test_lokaler_broker_erhaelt_und_entnimmt_nachrichten():
    b = LokalerNachrichtenbroker()
    kennung = b.senden("aufgaben", {"wert": 1})
    assert kennung == "nachricht-1"
    assert b.konsumieren("aufgaben") == [{"nachrichtenkennung": "nachricht-1", "nutzlast": {"wert": 1}}]
    assert b.konsumieren("aufgaben") == []


def test_produktionsbetrieb_readiness_gegen_sqlite(tmp_path):
    cfg = BetriebsKonfiguration(datenbank_url=f"sqlite+pysqlite:///{tmp_path/'test.db'}", umgebung="ENTWICKLUNG", instanzkennung="test")
    p = Produktionsbetrieb(cfg)
    r = p.readiness_auswerten()
    assert r["betriebsbereit"] is True
    assert r["datenbank"] is True
    assert r["nachrichten"] is True
    assert r["instanzkennung"] == "test"


def test_produktionsbetrieb_lehnt_ungueltige_umgebung_ab():
    cfg = BetriebsKonfiguration(umgebung="UNBEKANNT")
    try:
        Produktionsbetrieb(cfg)
        assert False
    except Exception as exc:
        assert getattr(exc, "code", None) == "UMGEBUNG_UNGUELTIG"
