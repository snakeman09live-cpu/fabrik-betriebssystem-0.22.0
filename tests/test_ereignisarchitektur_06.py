from fabrik_betriebssystem.persistenz import Datenbank
from fabrik_betriebssystem.ereignisarchitektur import PersistenterEreignisdienst, PersistenterEreigniskonsument
from fabrik_betriebssystem.modelle import Ereignis


def ereignis(kennung: str, art: str) -> Ereignis:
    return Ereignis(
        ereigniskennung=kennung,
        ereignisart=art,
        entitaetskennung="e1",
        zusammenhangskennung="z1",
        ablaufverfolgungskennung="t1",
    )


def make_db():
    return Datenbank("sqlite+pysqlite:///:memory:")


def test_ereignisse_persistent_und_sequenziert():
    db = make_db()
    dienst = PersistenterEreignisdienst(db)
    a = dienst.veroeffentlichen(ereignis("a", "A")).ereignis
    b = dienst.veroeffentlichen(ereignis("b", "B")).ereignis
    assert (a.sequenznummer, b.sequenznummer) == (1, 2)
    assert [x.ereigniskennung for x in dienst.seit(1)] == ["b"]


def test_doppeltes_ereignis_erzeugt_keine_zweite_sequenz():
    db = make_db(); dienst = PersistenterEreignisdienst(db)
    a = ereignis("a", "A")
    first = dienst.veroeffentlichen(a)
    second = dienst.veroeffentlichen(a)
    assert first.neu is True and second.neu is False
    assert len(dienst.alle()) == 1


def test_konsument_offset_und_nachholen_nach_neustart():
    db = make_db(); dienst = PersistenterEreignisdienst(db)
    dienst.veroeffentlichen(ereignis("a", "A"))
    dienst.veroeffentlichen(ereignis("b", "B"))
    gesehen = []
    konsument = PersistenterEreigniskonsument(dienst, "k1", gesehen.append)
    assert konsument.nachholen() == 2
    assert dienst.konsumentenstand("k1") == 2
    assert konsument.nachholen() == 0
    assert [e.ereigniskennung for e in gesehen] == ["a", "b"]


def test_fehlgeschlagener_handler_fortschreibung_erst_nach_erfolg():
    db = make_db(); dienst = PersistenterEreignisdienst(db)
    dienst.veroeffentlichen(ereignis("a", "A"))
    versuche = {"zahl": 0}

    def handler(e):
        versuche["zahl"] += 1
        if versuche["zahl"] == 1:
            raise RuntimeError("temporär")

    konsument = PersistenterEreigniskonsument(dienst, "k1", handler)
    try:
        konsument.nachholen()
        assert False
    except RuntimeError:
        pass
    assert dienst.konsumentenstand("k1") == 0
    assert konsument.nachholen() == 1
    assert dienst.konsumentenstand("k1") == 1
