from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.verteilte_sicherheit import InboxDienst, TransaktionalerAusgabepuffer


def test_inbox_dedupliziert_abgeschlossene_nachrichten(tmp_path):
    db = Datenbank(f"sqlite+pysqlite:///{tmp_path/'inbox.db'}")
    inbox = InboxDienst(db)
    assert inbox.uebernehmen('n1', 'k1') is True
    inbox.abschliessen('n1', 'k1')
    assert inbox.uebernehmen('n1', 'k1') is False


def test_outbox_lease_verhindert_parallele_doppeluebernahme(tmp_path):
    db = Datenbank(f"sqlite+pysqlite:///{tmp_path/'outbox.db'}")
    db.outbox_anfuegen('n1', 'A', {'x': 1})
    dienst = TransaktionalerAusgabepuffer(db, lease_sekunden=60)
    assert len(dienst.uebernehmen('w1')) == 1
    assert dienst.uebernehmen('w2') == []
    assert dienst.bestaetigen('w2', 'n1') is False
    assert dienst.bestaetigen('w1', 'n1') is True
    assert dienst.uebernehmen('w2') == []


def test_outbox_lease_kann_nach_ablauf_neu_uebernommen_werden(tmp_path):
    db = Datenbank(f"sqlite+pysqlite:///{tmp_path/'lease.db'}")
    db.outbox_anfuegen('n1', 'A', {'x': 1})
    dienst = TransaktionalerAusgabepuffer(db, lease_sekunden=1)
    assert len(dienst.uebernehmen('w1')) == 1
    import time
    time.sleep(1.05)
    assert len(dienst.uebernehmen('w2')) == 1
