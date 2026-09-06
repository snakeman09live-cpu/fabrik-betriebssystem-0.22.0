from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.ereignisarchitektur import PersistenterEreignisdienst
from fabrik_betriebssystem.verteilte_laufzeit import VerteilteWarteschlange, PersistenterAblaufplaner
from fabrik_betriebssystem.laufzeitsteuerung import KanonischeLaufzeit
from fabrik_betriebssystem.modelle import Ereignis
from datetime import datetime, timezone, timedelta


def db():
    return Datenbank("sqlite+pysqlite:///:memory:")


def test_runde_verarbeitet_planer_warteschlange_und_ereignisse():
    d = db(); e = PersistenterEreignisdienst(d); q = VerteilteWarteschlange(d); p = PersistenterAblaufplaner(d, q)
    r = KanonischeLaufzeit(d, e, q, p)
    gesehen = []
    r.aufgabenhandler_registrieren("a1", lambda n: gesehen.append(n.aufgabenkennung))
    msg = q.einreihen("lauf-1", "a1")
    p.planen(msg, datetime.now(timezone.utc) - timedelta(seconds=1))
    e.veroeffentlichen(Ereignis(ereigniskennung="e1", ereignisart="AUSFUEHRUNGSLAUF_GESTARTET", entitaetskennung="lauf-1", zusammenhangskennung="z1", ablaufverfolgungskennung="t1"))
    out = r.runde()
    assert out["aufgabe"] == "ERLEDIGT"
    assert gesehen == ["a1"]
    assert out["ereignisse"] == 1
    assert "lauf-1" in r.zustand.laufende_lauefe


def test_wiederanlauf_rekonstruiert_laufstatus_aus_ereignissen():
    d = db(); e = PersistenterEreignisdienst(d); q = VerteilteWarteschlange(d); p = PersistenterAblaufplaner(d, q)
    e.veroeffentlichen(Ereignis(ereigniskennung="e1", ereignisart="AUSFUEHRUNGSLAUF_GESTARTET", entitaetskennung="lauf-2", zusammenhangskennung="z2", ablaufverfolgungskennung="t2"))
    e.veroeffentlichen(Ereignis(ereigniskennung="e2", ereignisart="AUSFUEHRUNGSLAUF_ABGESCHLOSSEN", entitaetskennung="lauf-3", zusammenhangskennung="z3", ablaufverfolgungskennung="t3"))
    r = KanonischeLaufzeit(d, e, q, p)
    out = r.wiederanlauf()
    assert out["nachgeholt"] == 2
    assert out["laufende_lauefe"] == ["lauf-2"]
    assert out["abgeschlossene_lauefe"] == ["lauf-3"]


def test_fehlender_aufgabenhandler_und_meldung_bleibt_wiederholbar():
    d = db(); e = PersistenterEreignisdienst(d); q = VerteilteWarteschlange(d, maximale_versuche=2, basis_wiederholungssekunden=0, sichtbarkeit_sekunden=0); p = PersistenterAblaufplaner(d, q)
    r = KanonischeLaufzeit(d, e, q, p)
    msg = q.einreihen("lauf-4", "unbekannt")
    p.planen(msg, datetime.now(timezone.utc) - timedelta(seconds=1))
    assert r.aufgabe_ausfuehren("arbeiter-a") == "FEHLER"
    assert r.aufgabe_ausfuehren("arbeiter-b") == "FEHLER"
    from sqlalchemy import select
    from fabrik_betriebssystem.verteilte_laufzeit import AufgabenNachricht
    with d.session() as s:
        n = s.get(AufgabenNachricht, msg)
        assert n.zustand == "TOTE_POST"
