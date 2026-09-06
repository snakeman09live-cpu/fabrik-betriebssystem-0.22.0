from datetime import datetime, timezone
from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.modelle import Zustand, Aktion
from fabrik_betriebssystem.aufgaben import Ausfuehrungsaufgabe
from fabrik_betriebssystem.nachrichten import Ereignisbus
from fabrik_betriebssystem.ausfuehrungslauf import Ausfuehrungslaufdienst


def test_vertrag_und_uebergang_persistent():
    db = Datenbank('sqlite+pysqlite:///:memory:')
    db.vertragsversion_speichern({'vertragskennung':'v','vertragsversion':'1.0.0','schemakennung':'v','schemaversion':'1.0.0','vertragsart':'TEST','fingerabdruck':'x','daten':{}})
    assert db.vertrag_lesen('v','1.0.0').version == '1.0.0'
    db.uebergang_speichern({'uebergangskennung':'u','uebergangsversion':'1.0.0','entitaetstyp':'AUSFUEHRUNGSLAUF','ausgangszustand':'BEREIT','aktion':'STARTEN','zielzustand':'AKTIV','daten':{}})


def test_lauf_persistent_waehrend_ausfuehrung():
    db = Datenbank('sqlite+pysqlite:///:memory:')
    bus = Ereignisbus(); d = Ausfuehrungslaufdienst(bus, persist=db.lauf_speichern)
    lauf = d.erstellen('1.0.0', [Ausfuehrungsaufgabe('a', Aktion.STARTEN, handler=lambda: 42)])
    d.ausfuehren(lauf.laufkennung)
    gespeich = db.lauf_lesen(lauf.laufkennung)
    assert gespeich is not None
    assert gespeich.zustand == Zustand.ABGESCHLOSSEN.value
