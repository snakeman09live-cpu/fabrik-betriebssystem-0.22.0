from datetime import datetime, timezone, timedelta
from fabrik_betriebssystem.ausfuehrungslauf import Ausfuehrungslaufdienst
from fabrik_betriebssystem.aufgaben import Ausfuehrungsaufgabe
from fabrik_betriebssystem.modelle import Aktion, Zustand
from fabrik_betriebssystem.nachrichten import Ereignisbus
from fabrik_betriebssystem.vertragsdienst import Vertragsdienst, Vertragsreferenz
from fabrik_betriebssystem.kern import FabrikFehler


def test_ereignisbus_korreliert_und_sequenziert():
    bus = Ereignisbus(); gesehen=[]
    bus.abonnieren(gesehen.append, {"AUSFUEHRUNG_GESTARTET"})
    a = bus.veroeffentlichen("AUSFUEHRUNG_GESTARTET", "l1", {}, zusammenhangskennung="z1", ablaufverfolgungskennung="t1")
    bus.veroeffentlichen("ANDERES", "l1", {}, zusammenhangskennung="z1", ablaufverfolgungskennung="t1")
    assert a.sequenznummer == 1 and gesehen == [a] and bus.seit(1)[0].ereignisart == "ANDERES"


def test_ausfuehrungslauf_fuehrt_abhaengigkeiten_aus():
    bus = Ereignisbus(); d = Ausfuehrungslaufdienst(bus); reihenfolge=[]
    a = Ausfuehrungsaufgabe("a", Aktion.STARTEN, handler=lambda: reihenfolge.append("a") or 1)
    b = Ausfuehrungsaufgabe("b", Aktion.STARTEN, vorgaenger=["a"], handler=lambda: reihenfolge.append("b") or 2)
    lauf=d.erstellen("1.0.0", [a,b]); d.ausfuehren(lauf.laufkennung)
    assert reihenfolge == ["a","b"] and lauf.zustand == Zustand.ABGESCHLOSSEN


def test_ausfuehrungslauf_fehlender_handler_scheitert():
    d=Ausfuehrungslaufdienst(Ereignisbus()); lauf=d.erstellen("1.0.0", [Ausfuehrungsaufgabe("a", Aktion.STARTEN)])
    try: d.ausfuehren(lauf.laufkennung); assert False
    except FabrikFehler as e: assert e.code == "AUFGABENHANDLER_FEHLT" and lauf.zustand == Zustand.FEHLGESCHLAGEN


def test_vertragsdienst_bindet_exakte_version():
    d=Vertragsdienst(); v=Vertragsreferenz("zustand","1.0.0","zustand","1.0.0"); d.registrieren(v)
    assert d.aufloesen("zustand","1.0.0") == v
    try: d.aufloesen("zustand","2.0.0"); assert False
    except FabrikFehler as e: assert e.code == "VERTRAG_VERSION_UNGUELTIG"
