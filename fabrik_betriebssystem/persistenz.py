from __future__ import annotations
from datetime import datetime, timezone
import json
from sqlalchemy import create_engine, String, Integer, DateTime, Text, Boolean, select, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Basis(DeclarativeBase):
    pass

class Entitaetsdatensatz(Basis):
    __tablename__ = 'entitaeten'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    typ: Mapped[str] = mapped_column(String(80))
    zustand: Mapped[str] = mapped_column(String(80))
    zustandsversion: Mapped[int] = mapped_column(Integer, default=0)
    organisationskennung: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fabrikkennung: Mapped[str | None] = mapped_column(String(255), nullable=True)
    projektkennung: Mapped[str | None] = mapped_column(String(255), nullable=True)

class Idempotenzdatensatz(Basis):
    __tablename__ = 'idempotenz'
    idempotenzkennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    vorgangsfingerabdruck: Mapped[str] = mapped_column(String(128))
    ergebnis: Mapped[str] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('idempotenzkennung', 'vorgangsfingerabdruck'),)

class Nachweisdaten(Basis):
    __tablename__ = 'nachweise'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    vorgang: Mapped[str] = mapped_column(String(255))
    entitaet: Mapped[str] = mapped_column(String(255))
    inhalt: Mapped[str] = mapped_column(Text)
    erzeugt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Ereignisdaten(Basis):
    __tablename__ = 'ereignisse'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    art: Mapped[str] = mapped_column(String(120))
    entitaet: Mapped[str] = mapped_column(String(255))
    vorgang: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inhalt: Mapped[str] = mapped_column(Text)
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sequenznummer: Mapped[int] = mapped_column(Integer, default=0)

class Vertragsdatensatz(Basis):
    __tablename__ = 'vertraege'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[str] = mapped_column(String(32))
    schemakennung: Mapped[str] = mapped_column(String(255))
    schemaversion: Mapped[str] = mapped_column(String(32))
    art: Mapped[str] = mapped_column(String(120))
    zustand: Mapped[str] = mapped_column(String(80), default='AKTIV')
    gueltig_ab: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gueltig_bis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fingerabdruck: Mapped[str] = mapped_column(String(128))
    daten: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('kennung', 'version'),)

class Uebergangsdatensatz(Basis):
    __tablename__ = 'uebergaenge'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[str] = mapped_column(String(32))
    entitaetstyp: Mapped[str] = mapped_column(String(80))
    ausgangszustand: Mapped[str] = mapped_column(String(80))
    aktion: Mapped[str] = mapped_column(String(120))
    zielzustand: Mapped[str] = mapped_column(String(80))
    fachbereich: Mapped[str | None] = mapped_column(String(80), nullable=True)
    umgebung: Mapped[str | None] = mapped_column(String(80), nullable=True)
    zustaendigkeitsbereich: Mapped[str | None] = mapped_column(String(80), nullable=True)
    daten: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('kennung', 'version'),)

class Entscheidungsdatensatz(Basis):
    __tablename__ = 'entscheidungen'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[str] = mapped_column(String(32), default='1.0.0')
    entscheidung: Mapped[str] = mapped_column(String(80))
    befugnis: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vorgang: Mapped[str | None] = mapped_column(String(255), nullable=True)
    begruendung: Mapped[str] = mapped_column(Text)
    bedingungen: Mapped[str] = mapped_column(Text, default='[]')
    richtlinienversionen: Mapped[str] = mapped_column(Text, default='[]')
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Ausgabepufferdaten(Basis):
    __tablename__ = 'ausgabepuffer'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    kanal: Mapped[str] = mapped_column(String(255))
    nutzlast: Mapped[str] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    bestaetigt: Mapped[bool] = mapped_column(Boolean, default=False)
    bestaetigt_am: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index('ix_ausgabepuffer_offen', 'bestaetigt', 'erstellt_am'),)


class Ausfuehrungslaufdaten(Basis):
    __tablename__ = 'ausfuehrungslaeufe'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    planversion: Mapped[str] = mapped_column(String(32))
    zustand: Mapped[str] = mapped_column(String(80))
    zustandsversion: Mapped[int] = mapped_column(Integer, default=0)
    daten: Mapped[str] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Aufgabendaten(Basis):
    __tablename__ = 'aufgaben'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    laufkennung: Mapped[str] = mapped_column(String(255))
    aktion: Mapped[str] = mapped_column(String(120))
    vorgaenger: Mapped[str] = mapped_column(Text, default='[]')
    zustand: Mapped[str] = mapped_column(String(80), default='INITIAL')
    daten: Mapped[str] = mapped_column(Text, default='{}')

class Datenbank:
    def __init__(self, url: str = 'sqlite+pysqlite:///./fabrik.db'):
        self.engine = create_engine(url, future=True)
        Basis.metadata.create_all(self.engine)

    def session(self) -> Session:
        return Session(self.engine, expire_on_commit=False)

    def entitaet_anlegen(self, kennung, typ, zustand, zustandsversion=0, organisation=None, fabrik=None, projekt=None):
        with self.session() as s:
            if s.get(Entitaetsdatensatz, kennung):
                raise ValueError('ENTITAET_BEREITS_VORHANDEN')
            s.add(Entitaetsdatensatz(kennung=kennung, typ=typ, zustand=zustand, zustandsversion=zustandsversion,
                                     organisationskennung=organisation, fabrikkennung=fabrik, projektkennung=projekt))
            s.commit()

    def entitaet_lesen(self, kennung):
        with self.session() as s:
            return s.get(Entitaetsdatensatz, kennung)

    def vertragsversion_speichern(self, daten: dict):
        with self.session() as s:
            key = (daten['vertragskennung'], daten['vertragsversion'])
            stmt = select(Vertragsdatensatz).where(Vertragsdatensatz.kennung == key[0], Vertragsdatensatz.version == key[1])
            if s.scalar(stmt):
                raise ValueError('VERTRAG_BEREITS_VORHANDEN')
            s.add(Vertragsdatensatz(kennung=key[0], version=key[1], schemakennung=daten['schemakennung'],
                                    schemaversion=daten['schemaversion'], art=daten['vertragsart'],
                                    zustand=daten.get('zustand', 'AKTIV'), gueltig_ab=daten.get('gueltig_ab'),
                                    gueltig_bis=daten.get('gueltig_bis'), fingerabdruck=daten['fingerabdruck'],
                                    daten=json.dumps(daten.get('daten', {}), ensure_ascii=False)))
            s.commit()

    def vertrag_lesen(self, kennung, version):
        with self.session() as s:
            return s.scalar(select(Vertragsdatensatz).where(Vertragsdatensatz.kennung == kennung, Vertragsdatensatz.version == version))

    def uebergang_speichern(self, daten: dict):
        with self.session() as s:
            if s.get(Uebergangsdatensatz, daten['uebergangskennung']):
                raise ValueError('UEBERGANG_BEREITS_VORHANDEN')
            s.add(Uebergangsdatensatz(kennung=daten['uebergangskennung'], version=daten['uebergangsversion'],
                                      entitaetstyp=daten['entitaetstyp'], ausgangszustand=daten['ausgangszustand'],
                                      aktion=daten['aktion'], zielzustand=daten['zielzustand'],
                                      fachbereich=daten.get('fachbereich'), umgebung=daten.get('umgebung'),
                                      zustaendigkeitsbereich=daten.get('zustaendigkeitsbereich'),
                                      daten=json.dumps(daten.get('daten', {}), ensure_ascii=False)))
            s.commit()

    def zustand_aktualisieren(self, kennung, erwartete_version, zustand):
        with self.session() as s:
            e = s.get(Entitaetsdatensatz, kennung)
            if not e:
                raise ValueError('ENTITAET_NICHT_GEFUNDEN')
            if e.zustandsversion != erwartete_version:
                raise ValueError('VERSIONSKONFLIKT')
            e.zustand = zustand
            e.zustandsversion += 1
            s.commit()
            return e

    def idempotenz_lesen(self, key, fingerprint):
        with self.session() as s:
            row = s.get(Idempotenzdatensatz, key)
            if row is None:
                return None
            if row.vorgangsfingerabdruck != fingerprint:
                raise ValueError('IDEMPOTENZKONFLIKT')
            return json.loads(row.ergebnis)

    def zustandswechsel_mit_nachweis_und_ereignis(self, kennung, erwartete_version, zustand, nachweis, ereignis, idempotenz=None):
        with self.session() as s:
            e = s.get(Entitaetsdatensatz, kennung)
            if not e:
                raise ValueError('ENTITAET_NICHT_GEFUNDEN')
            if e.zustandsversion != erwartete_version:
                raise ValueError('VERSIONSKONFLIKT')
            if idempotenz:
                key, fingerprint, result = idempotenz
                existing = s.get(Idempotenzdatensatz, key)
                if existing:
                    if existing.vorgangsfingerabdruck != fingerprint:
                        raise ValueError('IDEMPOTENZKONFLIKT')
                    return json.loads(existing.ergebnis)
            neue_version = e.zustandsversion + 1
            e.zustand = zustand
            e.zustandsversion = neue_version
            s.add(Nachweisdaten(kennung=nachweis['kennung'], vorgang=nachweis['vorgang'], entitaet=nachweis['entitaet'], inhalt=json.dumps(nachweis['inhalt'], ensure_ascii=False)))
            s.add(Ereignisdaten(kennung=ereignis['kennung'], art=ereignis['art'], entitaet=ereignis['entitaet'], vorgang=ereignis.get('vorgang'), inhalt=json.dumps(ereignis['inhalt'], ensure_ascii=False), sequenznummer=neue_version))
            outbox_kennung = ereignis.get('nachrichtenkennung') or ereignis['kennung']
            s.add(Ausgabepufferdaten(kennung=outbox_kennung, kanal=ereignis['art'], nutzlast=json.dumps(ereignis, ensure_ascii=False, default=str)))
            if idempotenz:
                key, fingerprint, result = idempotenz
                s.add(Idempotenzdatensatz(idempotenzkennung=key, vorgangsfingerabdruck=fingerprint, ergebnis=result))
            s.commit()
            return json.loads(idempotenz[2]) if idempotenz else {'zustandsversion': neue_version}

    def outbox_anfuegen(self, kennung: str, kanal: str, nutzlast: dict) -> None:
        with self.session() as s:
            if s.get(Ausgabepufferdaten, kennung) is not None:
                return
            s.add(Ausgabepufferdaten(kennung=kennung, kanal=kanal, nutzlast=json.dumps(nutzlast, ensure_ascii=False, default=str)))
            s.commit()

    def outbox_lesen(self, limit: int = 100):
        with self.session() as s:
            rows = s.scalars(select(Ausgabepufferdaten).where(Ausgabepufferdaten.bestaetigt == False).order_by(Ausgabepufferdaten.erstellt_am).limit(limit)).all()
            from .outbox import AusgehendeNachricht
            return [AusgehendeNachricht(r.kennung, r.kanal, json.loads(r.nutzlast)) for r in rows]

    def outbox_bestaetigen(self, kennung: str) -> bool:
        with self.session() as s:
            row = s.get(Ausgabepufferdaten, kennung)
            if row is None or row.bestaetigt:
                return False
            row.bestaetigt = True
            row.bestaetigt_am = datetime.now(timezone.utc)
            s.commit()
            return True

    def entscheidung_speichern(self, entscheidung, vorgangskennung=None):
        with self.session() as s:
            s.add(Entscheidungsdatensatz(
                kennung=entscheidung.entscheidungskennung,
                entscheidung=entscheidung.entscheidung.value if hasattr(entscheidung.entscheidung, 'value') else entscheidung.entscheidung,
                befugnis=entscheidung.entscheidungsbefugnis,
                vorgang=vorgangskennung,
                begruendung=entscheidung.begruendung,
                bedingungen=json.dumps(entscheidung.bedingungen, ensure_ascii=False),
                richtlinienversionen=json.dumps(entscheidung.richtlinienversionen, ensure_ascii=False),
            ))
            s.commit()

    def entscheidung_lesen(self, kennung):
        with self.session() as s:
            return s.get(Entscheidungsdatensatz, kennung)

    def lauf_speichern(self, lauf):
        with self.session() as s:
            daten = {'aufgaben': list(lauf.aufgaben), 'ergebnisse': lauf.ergebnisse}
            row = s.get(Ausfuehrungslaufdaten, lauf.laufkennung)
            if row is None:
                s.add(Ausfuehrungslaufdaten(kennung=lauf.laufkennung, planversion=lauf.planversion, zustand=lauf.zustand.value,
                                            zustandsversion=lauf.zustandsversion, daten=json.dumps(daten, ensure_ascii=False)))
            else:
                row.planversion = lauf.planversion
                row.zustand = lauf.zustand.value
                row.zustandsversion = lauf.zustandsversion
                row.daten = json.dumps(daten, ensure_ascii=False)
            for a in lauf.aufgaben.values():
                ad = s.get(Aufgabendaten, a.aufgabenkennung)
                payload = {'ergebnis': a.ergebnis}
                if ad is None:
                    s.add(Aufgabendaten(kennung=a.aufgabenkennung, laufkennung=lauf.laufkennung, aktion=a.aktion.value,
                                        vorgaenger=json.dumps(a.vorgaenger), zustand='ABGESCHLOSSEN' if a.abgeschlossen else 'BEREIT',
                                        daten=json.dumps(payload, ensure_ascii=False, default=str)))
                else:
                    ad.zustand = 'ABGESCHLOSSEN' if a.abgeschlossen else 'BEREIT'
                    ad.daten = json.dumps(payload, ensure_ascii=False, default=str)
            s.commit()

    def lauf_lesen(self, kennung):
        with self.session() as s:
            return s.get(Ausfuehrungslaufdaten, kennung)

class GovernanceGenehmigungsdatensatz(Basis):
    __tablename__ = 'genehmigungen'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    vorgang: Mapped[str] = mapped_column(String(255))
    aktion: Mapped[str] = mapped_column(String(120))
    beantragt_durch: Mapped[str] = mapped_column(String(255))
    genehmigt_durch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zustand: Mapped[str] = mapped_column(String(80))
    gueltig_ab: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    gueltig_bis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grund: Mapped[str] = mapped_column(Text, default='')

class GovernanceDelegationsdatensatz(Basis):
    __tablename__ = 'delegationen'
    kennung: Mapped[str] = mapped_column(String(255), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    daten: Mapped[str] = mapped_column(Text)


def _genehmigung_speichern(self, g):
    with self.session() as s:
        row = s.get(GovernanceGenehmigungsdatensatz, g.genehmigungskennung)
        payload = dict(g.__dict__)
        if row is None:
            s.add(GovernanceGenehmigungsdatensatz(kennung=g.genehmigungskennung, vorgang=g.vorgangskennung, aktion=g.aktion.value,
                beantragt_durch=g.beantragt_durch, genehmigt_durch=g.genehmigt_durch, zustand=g.zustand,
                gueltig_ab=g.gueltig_ab, gueltig_bis=g.gueltig_bis, grund=g.grund))
        else:
            row.genehmigt_durch=g.genehmigt_durch; row.zustand=g.zustand; row.gueltig_bis=g.gueltig_bis; row.grund=g.grund
        s.commit()
Datenbank.genehmigung_speichern = _genehmigung_speichern

def _genehmigung_lesen(self, kennung):
    with self.session() as s:
        return s.get(GovernanceGenehmigungsdatensatz, kennung)
Datenbank.genehmigung_lesen = _genehmigung_lesen

def _delegation_speichern(self, d):
    with self.session() as s:
        row = s.get(GovernanceDelegationsdatensatz, d.delegationskennung)
        if row is not None:
            raise ValueError('DELEGATION_BEREITS_VORHANDEN')
        s.add(GovernanceDelegationsdatensatz(kennung=d.delegationskennung, version=d.delegationsversion,
            daten=json.dumps(d.model_dump() if hasattr(d, 'model_dump') else d.__dict__, ensure_ascii=False, default=str)))
        s.commit()
Datenbank.delegation_speichern = _delegation_speichern
