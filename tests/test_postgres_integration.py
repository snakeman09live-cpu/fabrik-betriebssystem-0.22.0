"""Integrationsprüfung gegen einen echten PostgreSQL-Server.

Die Prüfungen überspringen sich, solange `FABRIK_TEST_POSTGRES_URL` nicht
gesetzt ist. Damit bleibt die lokale Referenzsuite ohne externe Dienste
lauffähig, während die CI gegen einen echten Server prüft.

Hintergrund: die übrigen Tests verdrahten SQLite fest. SQLite serialisiert
Schreibzugriffe global, wodurch Nebenläufigkeitsfehler unentdeckt bleiben, die
auf PostgreSQL auftreten.
"""
from __future__ import annotations

import json
import os
import threading
import uuid

import pytest

from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.verteilte_sicherheit import (
    InboxDienst,
    TransaktionalerAusgabepuffer,
)

URL = os.environ.get("FABRIK_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not URL, reason="FABRIK_TEST_POSTGRES_URL nicht gesetzt; kein echter PostgreSQL-Server verfügbar"
)


@pytest.fixture(scope="module")
def db() -> Datenbank:
    return Datenbank(URL)


@pytest.fixture
def kennung() -> str:
    """Eigene Kennung pro Prüfung, da alle Prüfungen dieselbe Datenbank teilen."""
    return f"t-{uuid.uuid4()}"


def test_datenbank_ist_wirklich_postgresql(db):
    assert db.engine.dialect.name == "postgresql"


def test_entitaet_anlegen_und_lesen(db, kennung):
    db.entitaet_anlegen(kennung, "PROJEKT", "INITIAL")
    e = db.entitaet_lesen(kennung)
    assert e is not None
    assert e.typ == "PROJEKT"
    assert e.zustandsversion == 0


def test_entitaet_doppelt_anlegen_wird_abgewiesen(db, kennung):
    db.entitaet_anlegen(kennung, "PROJEKT", "INITIAL")
    with pytest.raises(ValueError, match="ENTITAET_BEREITS_VORHANDEN"):
        db.entitaet_anlegen(kennung, "PROJEKT", "INITIAL")


def test_zustandsversion_schuetzt_vor_verlorenem_schreibzugriff(db, kennung):
    db.entitaet_anlegen(kennung, "PROJEKT", "INITIAL")
    db.zustand_aktualisieren(kennung, 0, "AKTIV")
    assert db.entitaet_lesen(kennung).zustandsversion == 1
    with pytest.raises(ValueError, match="VERSIONSKONFLIKT"):
        db.zustand_aktualisieren(kennung, 0, "GESPERRT")


def _zustandswechsel(db, kennung, idempotenzschluessel=None, fingerabdruck="fp"):
    nachricht = f"m-{uuid.uuid4()}"
    idempotenz = None
    if idempotenzschluessel is not None:
        idempotenz = (idempotenzschluessel, fingerabdruck, json.dumps({"zustandsversion": 1}))
    return db.zustandswechsel_mit_nachweis_und_ereignis(
        kennung,
        0,
        "AKTIV",
        {"kennung": f"n-{uuid.uuid4()}", "vorgang": "start", "entitaet": kennung, "inhalt": {"a": 1}},
        {"kennung": nachricht, "art": "ZUSTAND_GEAENDERT", "entitaet": kennung, "inhalt": {"b": 2}},
        idempotenz=idempotenz,
    )


def test_zustandswechsel_schreibt_nachweis_ereignis_und_ausgabepuffer(db, kennung):
    db.entitaet_anlegen(kennung, "PROJEKT", "INITIAL")
    ergebnis = _zustandswechsel(db, kennung)
    assert ergebnis == {"zustandsversion": 1}
    assert db.entitaet_lesen(kennung).zustand == "AKTIV"
    offen = [n for n in db.outbox_lesen(limit=1000) if n.nutzlast.get("entitaet") == kennung]
    assert len(offen) == 1
    assert offen[0].kanal == "ZUSTAND_GEAENDERT"


def test_idempotenzschluessel_liefert_gespeichertes_ergebnis(db, kennung):
    db.entitaet_anlegen(kennung, "PROJEKT", "INITIAL")
    schluessel = f"i-{uuid.uuid4()}"
    assert _zustandswechsel(db, kennung, schluessel) == {"zustandsversion": 1}
    # Zweiter Aufruf: die Entität steht auf Version 1, der Idempotenzschlüssel
    # muss das gespeicherte Ergebnis zurückgeben statt erneut zu wechseln.
    assert db.idempotenz_lesen(schluessel, "fp") == {"zustandsversion": 1}
    assert db.entitaet_lesen(kennung).zustandsversion == 1


def test_gleicher_idempotenzschluessel_mit_anderem_fingerabdruck_kollidiert(db, kennung):
    db.entitaet_anlegen(kennung, "PROJEKT", "INITIAL")
    schluessel = f"i-{uuid.uuid4()}"
    _zustandswechsel(db, kennung, schluessel)
    with pytest.raises(ValueError, match="IDEMPOTENZKONFLIKT"):
        db.idempotenz_lesen(schluessel, "anderer-fingerabdruck")


def test_inbox_dedupliziert_gegen_echte_datenbank(db):
    nachricht, konsument = f"n-{uuid.uuid4()}", f"k-{uuid.uuid4()}"
    inbox = InboxDienst(db)
    assert inbox.uebernehmen(nachricht, konsument) is True
    inbox.abschliessen(nachricht, konsument)
    assert inbox.uebernehmen(nachricht, konsument) is False


def test_inbox_trennt_konsumenten(db):
    nachricht = f"n-{uuid.uuid4()}"
    inbox = InboxDienst(db)
    assert inbox.uebernehmen(nachricht, "konsument-a") is True
    inbox.abschliessen(nachricht, "konsument-a")
    # Ein zweiter Konsument muss dieselbe Nachricht noch verarbeiten dürfen.
    assert inbox.uebernehmen(nachricht, "konsument-b") is True


def test_ausgabepuffer_lease_gilt_exklusiv(db):
    nachricht = f"n-{uuid.uuid4()}"
    db.outbox_anfuegen(nachricht, "A", {"x": 1})
    dienst = TransaktionalerAusgabepuffer(db, lease_sekunden=60)
    uebernommen = [a for a in dienst.uebernehmen("w1", limit=1000) if a.nachrichtenkennung == nachricht]
    assert len(uebernommen) == 1
    fremd = [a for a in dienst.uebernehmen("w2", limit=1000) if a.nachrichtenkennung == nachricht]
    assert fremd == []
    assert dienst.bestaetigen("w2", nachricht) is False
    assert dienst.bestaetigen("w1", nachricht) is True


def test_ausgabepuffer_lease_wird_nach_ablauf_neu_uebernommen(db):
    import time

    nachricht = f"n-{uuid.uuid4()}"
    db.outbox_anfuegen(nachricht, "A", {"x": 1})
    dienst = TransaktionalerAusgabepuffer(db, lease_sekunden=1)
    assert any(a.nachrichtenkennung == nachricht for a in dienst.uebernehmen("w1", limit=1000))
    time.sleep(1.05)
    assert any(a.nachrichtenkennung == nachricht for a in dienst.uebernehmen("w2", limit=1000))


def test_lease_bleibt_bei_echt_paralleler_uebernahme_exklusiv():
    """Kernzusage von 0.22.0: mehrere Zusteller dürfen parallel arbeiten.

    SQLite serialisiert Schreibzugriffe und kann das nicht widerlegen. Hier
    laufen zwei Zusteller auf getrennten PostgreSQL-Verbindungen gleichzeitig
    gegen dieselbe Nachricht. Erwartung: genau einer erhält sie, der andere
    geht leer aus, und keiner bricht mit einer Datenbankausnahme ab.
    """
    nachricht = f"n-{uuid.uuid4()}"
    Datenbank(URL).outbox_anfuegen(nachricht, "A", {"x": 1})

    treffer: list[str] = []
    fehler: list[BaseException] = []
    schranke = threading.Barrier(2)
    sperre = threading.Lock()

    def zusteller(name: str) -> None:
        # Eigene Datenbank-Instanz je Thread: getrennte Verbindung, keine
        # gemeinsame Session.
        eigene = Datenbank(URL)
        dienst = TransaktionalerAusgabepuffer(eigene, lease_sekunden=60)
        try:
            schranke.wait(timeout=30)
            auftraege = dienst.uebernehmen(name, limit=1000)
            if any(a.nachrichtenkennung == nachricht for a in auftraege):
                with sperre:
                    treffer.append(name)
        except BaseException as exc:  # noqa: BLE001 - Fehler soll die Prüfung sichtbar machen
            with sperre:
                fehler.append(exc)

    threads = [threading.Thread(target=zusteller, args=(f"w{i}",)) for i in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert fehler == [], f"Zusteller brach mit Ausnahme ab: {fehler!r}"
    assert len(treffer) == 1, f"Nachricht wurde {len(treffer)}-mal übernommen: {treffer}"
