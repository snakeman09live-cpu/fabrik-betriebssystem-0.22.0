from datetime import datetime, timezone, timedelta
from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.verteilte_laufzeit import VerteilteWarteschlange, VerteilterArbeiter, PersistenterAblaufplaner, AufgabenNachricht


def make_db():
    return Datenbank('sqlite+pysqlite:///:memory:')


def test_persistente_warteschlange_wiederaufnahme_nach_absturz():
    db = make_db(); q = VerteilteWarteschlange(db, sichtbarkeit_sekunden=0)
    kennung = q.einreihen('lauf-1', 'aufgabe-1')
    beansprucht = q.beanspruchen('arbeiter-a')
    assert beansprucht.kennung == kennung
    assert q.abgelaufene_sperren_freigeben() == 1
    wieder = q.beanspruchen('arbeiter-b')
    assert wieder.kennung == kennung
    assert wieder.versuche == 2


def test_wiederholungsversuche_und_tote_post():
    db = make_db(); q = VerteilteWarteschlange(db, maximale_versuche=2, basis_wiederholungssekunden=0, sichtbarkeit_sekunden=0)
    kennung = q.einreihen('lauf-1', 'aufgabe-1')
    assert q.beanspruchen('a')
    assert q.erneut_einreihen(kennung, 'fehler') == 'BEREIT'
    assert q.beanspruchen('a')
    assert q.erneut_einreihen(kennung, 'dauerfehler') == 'TOTE_POST'
    assert len(q.tote_briefe()) == 1


def test_idempotentes_einreihen():
    db = make_db(); q = VerteilteWarteschlange(db)
    kennung = 'nachricht-1'
    assert q.einreihen('lauf', 'aufgabe', kennung=kennung) == kennung
    assert q.einreihen('lauf', 'aufgabe', kennung=kennung) == kennung
    with db.session() as s:
        assert len(s.scalars(__import__('sqlalchemy').select(AufgabenNachricht)).all()) == 1


def test_persistenter_ablaufplaner():
    db = make_db(); q = VerteilteWarteschlange(db); p = PersistenterAblaufplaner(db, q)
    msg = q.einreihen('lauf', 'a1')
    p.planen(msg, datetime.now(timezone.utc) - timedelta(seconds=1))
    assert p.faellige_einreihen() == [msg]
