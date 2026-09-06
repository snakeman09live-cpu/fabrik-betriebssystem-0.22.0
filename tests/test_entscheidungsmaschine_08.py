from datetime import datetime, timezone
from fabrik_betriebssystem.entscheidungsmaschine import Entscheidungsmaschine, Bewertungsgrundlage
from fabrik_betriebssystem.modelle import Befugnis, Rolle, Fachbereich, Zustaendigkeitsbereich, Risikostufe, Aktion, Entscheidung

def befugnis(risiko=Risikostufe.HOCH):
    return Befugnis(
        befugniskennung='b1', identitaetskennung='u1', rolle=Rolle.BENUTZER,
        fachbereich=Fachbereich.BENUTZER, zustaendigkeitsbereich=Zustaendigkeitsbereich.GESAMT,
        aktionen=[Aktion.STARTEN], risikogrenze=risiko,
        gueltig_ab=datetime.now(timezone.utc)
    )

def test_fehlende_befugnis_eskaliert_vor_normaler_zulassung():
    d=Entscheidungsmaschine().entscheiden(befugnis=None,bewertung=Bewertungsgrundlage())
    assert d.entscheidung == Entscheidung.ESKALIEREN

def test_kosten_und_kapazitaet_werden_als_bedingungen_behandelt():
    d=Entscheidungsmaschine().entscheiden(
        befugnis=befugnis(),
        bewertung=Bewertungsgrundlage(budget_verfuegbar=False, kapazitaet_verfuegbar=False),
    )
    assert d.entscheidung == Entscheidung.MIT_BEDINGUNGEN_ZULASSEN
    assert set(d.bedingungen) >= {'BUDGET_PRUEFEN','KAPAZITAET_PRUEFEN'}

def test_nicht_ueberschreibbare_richtlinienablehnung_wird_ablehnung():
    from fabrik_betriebssystem.modelle import Richtlinienregel
    regel=Richtlinienregel(
        regelkennung='r1', aktion=Aktion.STARTEN,
        wirkung=Entscheidung.ABLEHNEN, nicht_ueberschreibbar=True
    )
    d=Entscheidungsmaschine().entscheiden(befugnis=befugnis(),bewertung=Bewertungsgrundlage(),regeln=[regel])
    assert d.entscheidung == Entscheidung.ABLEHNEN

def test_risiko_oberhalb_der_befugnis_eskaliert():
    d=Entscheidungsmaschine().entscheiden(
        befugnis=befugnis(Risikostufe.MITTEL),
        bewertung=Bewertungsgrundlage(risiko=Risikostufe.HOCH),
    )
    assert d.entscheidung == Entscheidung.ESKALIEREN
