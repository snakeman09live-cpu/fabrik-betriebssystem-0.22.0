from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib, json, uuid
from .modelle import *

class FabrikFehler(Exception):
    def __init__(self, code: str, message: str, **details):
        super().__init__(message); self.code=code; self.message=message; self.details=details

@dataclass(frozen=True)
class Uebergangseintrag:
    uebergang: Uebergang

class Uebergangsregister:
    def __init__(self): self._werte: dict[str, Uebergang] = {}
    def registrieren(self, u: Uebergang):
        def wert(x): return x.value if hasattr(x, "value") else x
        for alt in self._werte.values():
            if (wert(alt.entitaetstyp), wert(alt.ausgangszustand), wert(alt.aktion), alt.fachbereich, alt.umgebung, alt.zustaendigkeitsbereich) == (wert(u.entitaetstyp), wert(u.ausgangszustand), wert(u.aktion), u.fachbereich, u.umgebung, u.zustaendigkeitsbereich) and alt.zielzustand != u.zielzustand:
                raise FabrikFehler("UEBERGANGSKONFLIKT","Widersprüchliche Übergänge sind nicht zulässig.")
        self._werte[u.uebergangskennung]=u
    def aufloesen(self, c: Uebergangskontext) -> Uebergang:
        treffer=[]; jetzt_zeit=datetime.now(timezone.utc)
        for u in self._werte.values():
            if u.entitaetstyp!=c.entitaet.entitaetstyp or u.ausgangszustand!=Zustand(c.lebenszyklus.zustand) or u.aktion!=Aktion(c.vorgang.aktion): continue
            if u.fachbereich is not None and u.fachbereich != c.anwendbarkeit.fachbereich: continue
            if u.umgebung is not None and u.umgebung != c.anwendbarkeit.umgebung: continue
            if u.zustaendigkeitsbereich is not None and u.zustaendigkeitsbereich != c.anwendbarkeit.zustaendigkeitsbereich: continue
            if u.gueltig_ab and jetzt_zeit < u.gueltig_ab: continue
            if u.gueltig_bis and jetzt_zeit >= u.gueltig_bis: continue
            treffer.append(u)
        if not treffer: raise FabrikFehler("KEIN_ANWENDBARER_UEBERGANG","Für Kontext und Aktion wurde kein Übergang gefunden.")
        ziele={x.zielzustand for x in treffer}
        if len(ziele)!=1: raise FabrikFehler("MEHRDEUTIGER_UEBERGANG","Mehrere widersprüchliche Übergänge sind anwendbar.")
        return treffer[0]

class Kontextpruefer:
    def pruefen(self,c: Uebergangskontext):
        if not c.kontextkennung or not c.kontextversion: raise FabrikFehler("KONTEXT_UNGUELTIG","Kontextkennung und Kontextversion sind erforderlich.")
        if c.nebenlaeufigkeit.erwartete_zustandsversion is not None and c.nebenlaeufigkeit.erwartete_zustandsversion<0: raise FabrikFehler("NEBENLAEUFIGKEIT_UNGUELTIG","Ungültige erwartete Zustandsversion.")
        if c.steuerung.richtlinie and (not c.steuerung.richtlinie.richtlinienkennung or not c.steuerung.richtlinie.richtlinienversion): raise FabrikFehler("RICHTLINIE_UNGUELTIG","Richtlinienbezug unvollständig.")
        if c.steuerung.delegation and ((c.steuerung.delegation.delegationskennung is None) != (c.steuerung.delegation.delegationsversion is None)): raise FabrikFehler("DELEGATION_UNGUELTIG","Delegationskennung und Delegationsversion müssen gemeinsam angegeben werden.")
        if c.steuerung.genehmigung and c.steuerung.genehmigung.genehmigungszustand=="NICHT_ERFORDERLICH" and c.steuerung.genehmigung.genehmigungskennung is not None: raise FabrikFehler("GENEHMIGUNG_UNGUELTIG","Eine nicht erforderliche Genehmigung darf keine Kennung tragen.")
        for ident in (c.kontextkennung,c.entitaet.entitaetskennung,c.vorgang.anfragekennung,c.herkunft.zusammenhangskennung,c.herkunft.ablaufverfolgungskennung):
            if not ident.strip(): raise FabrikFehler("KONTEXT_UNGUELTIG","Kennungen dürfen nicht leer sein.")
        return True

class Befugnisdienst:
    _rang = {Risikostufe.KEIN_RISIKO:0,Risikostufe.NIEDRIG:1,Risikostufe.MITTEL:2,Risikostufe.HOCH:3,Risikostufe.KRITISCH:4}
    def __init__(self): self.befugnisse=[]; self.delegationen=[]
    def registrieren(self,b): self.befugnisse.append(b)
    def delegieren(self,d): self.delegationen.append(d)
    def pruefen(self, identitaet, rolle, c):
        now=datetime.now(timezone.utc); aktion=Aktion(c.vorgang.aktion); risiko=Risikostufe(c.steuerung.risiko or Risikostufe.KEIN_RISIKO)
        kandidat=[b for b in self.befugnisse if b.identitaetskennung==identitaet and b.rolle==rolle and aktion in b.aktionen and self._rang[b.risikogrenze]>=self._rang[risiko] and b.gueltig_ab<=now and (b.gueltig_bis is None or now<b.gueltig_bis) and (b.fachbereich==c.anwendbarkeit.fachbereich or b.fachbereich==Fachbereich.BENUTZER) and b.zustaendigkeitsbereich in (c.anwendbarkeit.zustaendigkeitsbereich,Zustaendigkeitsbereich.GESAMT)]
        if kandidat: return kandidat[0]
        for d in self.delegationen:
            if not d.aktiv or d.empfaenger!=identitaet or d.rolle!=rolle or aktion not in d.aktionen: continue
            if d.gueltig_ab>now or (d.gueltig_bis and now>=d.gueltig_bis): continue
            if self._rang[d.risikogrenze] < self._rang[risiko]: continue
            if d.fachbereich!=c.anwendbarkeit.fachbereich and d.fachbereich!=Fachbereich.BENUTZER: continue
            return Befugnis(befugniskennung=f"delegiert:{d.delegationskennung}",identitaetskennung=identitaet,rolle=rolle,fachbereich=d.fachbereich,zustaendigkeitsbereich=d.zustaendigkeitsbereich,aktionen=d.aktionen,risikogrenze=d.risikogrenze,gueltig_ab=d.gueltig_ab,gueltig_bis=d.gueltig_bis,delegationskennung=d.delegationskennung)
        raise FabrikFehler("BEFUGNIS_FEHLT","Keine gültige Befugnis gefunden.")

class Richtliniendienst:
    def __init__(self): self.richtlinien={}
    def registrieren(self,r): self.richtlinien[(r.richtlinienkennung,r.richtlinienversion)]=r
    def bewerten(self,c):
        if not c.steuerung.richtlinie: return []
        key=(c.steuerung.richtlinie.richtlinienkennung,c.steuerung.richtlinie.richtlinienversion); r=self.richtlinien.get(key)
        if not r or not r.aktiv: raise FabrikFehler("RICHTLINIE_UNGUELTIG","Richtlinie fehlt oder ist nicht aktiv.")
        aktive=[]; risiko=Risikostufe(c.steuerung.risiko or Risikostufe.KEIN_RISIKO)
        for regel in r.regeln:
            if regel.aktion!=Aktion(c.vorgang.aktion): continue
            if regel.fachbereich and regel.fachbereich!=c.anwendbarkeit.fachbereich: continue
            if regel.umgebung and regel.umgebung!=c.anwendbarkeit.umgebung: continue
            aktive.append(regel)
        return aktive

class Entscheidungsdienst:
    def entscheiden(self,c,befugnis,regeln):
        verbote=[r for r in regeln if r.wirkung==Entscheidung.ABLEHNEN and r.nicht_ueberschreibbar]
        if verbote: return Entscheidungsresultat(entscheidungskennung=str(uuid.uuid4()),entscheidung=Entscheidung.ABLEHNEN,entscheidungsbefugnis=befugnis.befugniskennung,begruendung="Nicht überschreibbare Richtlinie untersagt die Aktion.")
        widersprueche=[r for r in regeln if r.wirkung==Entscheidung.ABLEHNEN]
        bedingungen=[r.begruendung for r in regeln if r.wirkung==Entscheidung.MIT_BEDINGUNGEN_ZULASSEN]
        if widersprueche: return Entscheidungsresultat(entscheidungskennung=str(uuid.uuid4()),entscheidung=Entscheidung.ESKALIEREN,entscheidungsbefugnis=befugnis.befugniskennung,begruendung="Widersprüchliche Richtlinienwirkung konnte nicht eindeutig aufgelöst werden.")
        if bedingungen: return Entscheidungsresultat(entscheidungskennung=str(uuid.uuid4()),entscheidung=Entscheidung.MIT_BEDINGUNGEN_ZULASSEN,entscheidungsbefugnis=befugnis.befugniskennung,begruendung="Zulassung ist an Richtlinienbedingungen gebunden.",bedingungen=bedingungen)
        return Entscheidungsresultat(entscheidungskennung=str(uuid.uuid4()),entscheidung=Entscheidung.ZULASSEN,entscheidungsbefugnis=befugnis.befugniskennung,begruendung="Befugnis und Richtlinienprüfung erlauben die Aktion.")

def fingerabdruck(obj:object)->str:
    raw=json.dumps(obj,default=lambda x:x.value if hasattr(x,'value') else x.isoformat() if hasattr(x,'isoformat') else x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()
