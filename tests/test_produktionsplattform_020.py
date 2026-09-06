from fabrik_betriebssystem.broker import Auftrag, SpeicherBroker
from fabrik_betriebssystem.gesundheit import Gesundheitsdienst, Pruefergebnis
from fabrik_betriebssystem.beobachtbarkeit import Metriken


def test_broker_lease_und_bestaetigung():
    b = SpeicherBroker(); a = Auftrag('a-1', {'x': 1}, lease_sekunden=10)
    b.einreihen(a)
    assert b.uebernehmen('w-1', jetzt=100) == a
    assert not b.bestaetigen('w-2', 'a-1')
    assert b.bestaetigen('w-1', 'a-1')
    assert b.uebernehmen('w-2', jetzt=101) is None


def test_broker_lease_ablauf_ermoeglicht_wiederuebernahme():
    b = SpeicherBroker(); a = Auftrag('a-2', {}, lease_sekunden=5)
    b.einreihen(a)
    assert b.uebernehmen('w-1', jetzt=100) == a
    assert b.uebernehmen('w-2', jetzt=101) is None
    assert b.uebernehmen('w-2', jetzt=106) == a


def test_gesundheit_und_bereitschaft():
    g = Gesundheitsdienst()
    g.registrieren('db', lambda: Pruefergebnis('db', True))
    assert g.pruefen()['gesund'] is True
    assert g.bereitschaft()['bereit'] is True


def test_metriken():
    m = Metriken(); p=m.erfassen('antwortzeit', 12.5)
    assert p.name == 'antwortzeit'
    assert m.letzte('antwortzeit').wert == 12.5
