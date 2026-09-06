from fabrik_betriebssystem.entscheidungsintelligenz import Entscheidungsgrundlage, Entscheidungsintelligenz
from fabrik_betriebssystem.modelle import Entscheidung, Risikostufe

def test_entscheidungsintelligenz_allows_without_hidden_priority():
    a = Entscheidungsintelligenz().entscheiden(Entscheidungsgrundlage(
        befugnis_gueltig=True, richtlinienkonform=True, risiko=Risikostufe.NIEDRIG,
        risiko_grenze=Risikostufe.HOCH, sicherheit_ok=True, budget_ok=True,
        qualitaet_ok=True, voraussetzungen_erfuellt=True))
    assert a.entscheidung == Entscheidung.ZULASSEN

def test_entscheidungsintelligenz_escalates_on_missing_authority():
    a = Entscheidungsintelligenz().entscheiden(Entscheidungsgrundlage(
        befugnis_gueltig=False, richtlinienkonform=True))
    assert a.entscheidung == Entscheidung.ESKALIEREN

def test_entscheidungsintelligenz_uses_conditions():
    a = Entscheidungsintelligenz().entscheiden(Entscheidungsgrundlage(
        befugnis_gueltig=True, richtlinienkonform=True, budget_ok=False))
    assert a.entscheidung == Entscheidung.MIT_BEDINGUNGEN_ZULASSEN
    assert 'BUDGET_PRUEFEN' in a.bedingungen
