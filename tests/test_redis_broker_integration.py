"""Integrationsprüfung des Redis-Brokers gegen einen echten Redis-Server.

Die Prüfungen überspringen sich, solange `FABRIK_TEST_REDIS_URL` nicht gesetzt
ist. `RedisBroker` war bis dahin ohne jede Testabdeckung; der `SpeicherBroker`
dient hier als Verhaltensmaßstab, weil beide dasselbe Protokoll erfüllen.
"""
from __future__ import annotations

import os
import uuid

import pytest

from fabrik_betriebssystem.broker import Auftrag, RedisBroker, SpeicherBroker

URL = os.environ.get("FABRIK_TEST_REDIS_URL")

pytestmark = pytest.mark.skipif(
    not URL, reason="FABRIK_TEST_REDIS_URL nicht gesetzt; kein echter Redis-Server verfügbar"
)


@pytest.fixture
def broker() -> RedisBroker:
    """Frischer Broker je Prüfung.

    `RedisBroker` benutzt feste Schlüsselnamen, deshalb werden die Schlüssel
    vor jeder Prüfung geleert.
    """
    b = RedisBroker(URL)
    b.client.delete("fabrik:auftraege", "fabrik:in_bearbeitung")
    for key in b.client.scan_iter("fabrik:lease:*"):
        b.client.delete(key)
    return b


@pytest.fixture
def auftrag() -> Auftrag:
    return Auftrag(f"a-{uuid.uuid4()}", {"aktion": "pruefen"}, lease_sekunden=60)


def test_verbindung_steht(broker):
    assert broker.client.ping() is True


def test_leere_warteschlange_liefert_keinen_auftrag(broker):
    assert broker.uebernehmen("w1") is None


def test_eingereihter_auftrag_wird_uebernommen(broker, auftrag):
    broker.einreihen(auftrag)
    uebernommen = broker.uebernehmen("w1")
    assert uebernommen is not None
    assert uebernommen.auftragskennung == auftrag.auftragskennung
    assert uebernommen.inhalt == {"aktion": "pruefen"}


def test_uebernommener_auftrag_liegt_nicht_mehr_in_der_warteschlange(broker, auftrag):
    broker.einreihen(auftrag)
    broker.uebernehmen("w1")
    assert broker.client.llen("fabrik:auftraege") == 0
    assert broker.client.llen("fabrik:in_bearbeitung") == 1


def test_bestaetigung_durch_fremden_kunden_wird_abgewiesen(broker, auftrag):
    broker.einreihen(auftrag)
    broker.uebernehmen("w1")
    assert broker.bestaetigen("w2", auftrag.auftragskennung) is False
    # Der Auftrag bleibt in Bearbeitung und der Lease beim rechtmäßigen Besitzer.
    assert broker.client.llen("fabrik:in_bearbeitung") == 1
    assert broker.client.hget(f"fabrik:lease:{auftrag.auftragskennung}", "kunde") == "w1"


def test_bestaetigung_durch_besitzer_entfernt_den_auftrag(broker, auftrag):
    broker.einreihen(auftrag)
    broker.uebernehmen("w1")
    assert broker.bestaetigen("w1", auftrag.auftragskennung) is True
    assert broker.client.llen("fabrik:in_bearbeitung") == 0
    assert broker.client.exists(f"fabrik:lease:{auftrag.auftragskennung}") == 0


def test_bestaetigung_ohne_lease_wird_abgewiesen(broker, auftrag):
    broker.einreihen(auftrag)
    assert broker.bestaetigen("w1", auftrag.auftragskennung) is False


def test_zurueckstellen_macht_den_auftrag_erneut_uebernehmbar(broker, auftrag):
    """Regressionsprüfung: Zurückstellen darf den Auftrag nicht verwerfen.

    `zurueckstellen` delegierte an `bestaetigen` und löschte den Auftrag damit
    aus `fabrik:in_bearbeitung`, ohne ihn zurück in die Warteschlange zu legen –
    ein zurückgestellter Auftrag war verloren.
    """
    broker.einreihen(auftrag)
    assert broker.uebernehmen("w1") is not None
    assert broker.zurueckstellen("w1", auftrag.auftragskennung) is True

    erneut = broker.uebernehmen("w2")
    assert erneut is not None, "zurückgestellter Auftrag ist verloren gegangen"
    assert erneut.auftragskennung == auftrag.auftragskennung
    assert broker.client.llen("fabrik:in_bearbeitung") == 1


def test_zurueckstellen_durch_fremden_kunden_wird_abgewiesen(broker, auftrag):
    broker.einreihen(auftrag)
    broker.uebernehmen("w1")
    assert broker.zurueckstellen("w2", auftrag.auftragskennung) is False
    assert broker.client.hget(f"fabrik:lease:{auftrag.auftragskennung}", "kunde") == "w1"


def test_zurueckstellen_gibt_den_lease_frei(broker, auftrag):
    broker.einreihen(auftrag)
    broker.uebernehmen("w1")
    broker.zurueckstellen("w1", auftrag.auftragskennung)
    assert broker.client.exists(f"fabrik:lease:{auftrag.auftragskennung}") == 0


def test_redisbroker_verhaelt_sich_wie_der_speicherbroker(broker, auftrag):
    """Beide Broker erfüllen dasselbe Protokoll und müssen sich gleich verhalten."""
    speicher = SpeicherBroker()

    for b in (speicher, broker):
        b.einreihen(auftrag)
        assert b.uebernehmen("w1").auftragskennung == auftrag.auftragskennung
        assert b.bestaetigen("w2", auftrag.auftragskennung) is False
        assert b.zurueckstellen("w2", auftrag.auftragskennung) is False
        assert b.zurueckstellen("w1", auftrag.auftragskennung) is True
        assert b.uebernehmen("w2").auftragskennung == auftrag.auftragskennung
        assert b.bestaetigen("w2", auftrag.auftragskennung) is True
        assert b.uebernehmen("w3") is None
