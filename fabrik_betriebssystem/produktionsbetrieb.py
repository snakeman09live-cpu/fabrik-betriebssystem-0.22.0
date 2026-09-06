from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from typing import Callable, Protocol, Any
from sqlalchemy import text

from .persistenz import Datenbank
from .kern import FabrikFehler


def jetzt() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BetriebsKonfiguration:
    datenbank_url: str = os.getenv("FABRIK_DATENBANK_URL", "sqlite+pysqlite:///./fabrik.db")
    umgebung: str = os.getenv("FABRIK_UMGEBUNG", "ENTWICKLUNG")
    instanzkennung: str = os.getenv("FABRIK_INSTANZKENNUNG", "lokal")
    maximale_wiederholungen: int = int(os.getenv("FABRIK_MAXIMALE_WIEDERHOLUNGEN", "5"))

    def validieren(self) -> None:
        if self.umgebung not in {"SIMULATION", "ENTWICKLUNG", "BEREITSTELLUNGSVORSTUFE", "PRODUKTION"}:
            raise FabrikFehler("UMGEBUNG_UNGUELTIG", "Unbekannte Betriebsumgebung.")
        if self.maximale_wiederholungen < 1:
            raise FabrikFehler("WIEDERHOLUNGSGRENZE_UNGUELTIG", "Die Wiederholungsgrenze muss mindestens 1 sein.")


class Nachrichtenbroker(Protocol):
    def senden(self, kanal: str, nutzlast: dict[str, Any]) -> str: ...
    def konsumieren(self, kanal: str, limit: int = 100) -> list[dict[str, Any]]: ...


class LokalerNachrichtenbroker:
    """Deterministischer Referenzbroker. Redis kann später über dasselbe Protokoll angeschlossen werden."""
    def __init__(self) -> None:
        self._kanaele: dict[str, list[dict[str, Any]]] = {}
        self._zaehler = 0

    def senden(self, kanal: str, nutzlast: dict[str, Any]) -> str:
        self._zaehler += 1
        kennung = f"nachricht-{self._zaehler}"
        self._kanaele.setdefault(kanal, []).append({"nachrichtenkennung": kennung, "nutzlast": nutzlast})
        return kennung

    def konsumieren(self, kanal: str, limit: int = 100) -> list[dict[str, Any]]:
        werte = self._kanaele.setdefault(kanal, [])
        ausgabe, self._kanaele[kanal] = werte[:limit], werte[limit:]
        return ausgabe


class RedisNachrichtenbroker:
    """Optionale Redis-Implementierung. Redis wird nur bei tatsächlicher Nutzung importiert."""
    def __init__(self, url: str) -> None:
        try:
            from redis import Redis
        except ImportError as exc:
            raise FabrikFehler("REDIS_ABHAENGIGKEIT_FEHLT", "Für den Redis-Broker fehlt das Python-Paket redis.") from exc
        self._redis = Redis.from_url(url, decode_responses=True)

    def senden(self, kanal: str, nutzlast: dict[str, Any]) -> str:
        import json
        from uuid import uuid4
        kennung = str(uuid4())
        self._redis.rpush(kanal, json.dumps({"nachrichtenkennung": kennung, "nutzlast": nutzlast}, ensure_ascii=False, default=str))
        return kennung

    def konsumieren(self, kanal: str, limit: int = 100) -> list[dict[str, Any]]:
        import json
        werte = self._redis.lrange(kanal, 0, limit - 1)
        if werte:
            self._redis.ltrim(kanal, len(werte), -1)
        return [json.loads(x) for x in werte]


@dataclass(frozen=True)
class Bereitschaft:
    betriebsbereit: bool
    datenbank: bool
    nachrichten: bool
    umgebung: str
    instanzkennung: str
    zeitpunkt: datetime


class Betriebspruefer:
    def __init__(self, db: Datenbank, broker: Nachrichtenbroker, konfiguration: BetriebsKonfiguration):
        self.db = db
        self.broker = broker
        self.konfiguration = konfiguration

    def gesundheit(self) -> dict[str, Any]:
        datenbank_ok = False
        try:
            with self.db.session() as s:
                s.execute(text("SELECT 1"))
            datenbank_ok = True
        except Exception:
            datenbank_ok = False
        return {
            "dienst": "bereit" if datenbank_ok else "eingeschraenkt",
            "datenbank": datenbank_ok,
            "nachrichten": True,
            "umgebung": self.konfiguration.umgebung,
            "instanzkennung": self.konfiguration.instanzkennung,
            "zeitpunkt": jetzt().isoformat(),
        }

    def bereitschaft(self) -> Bereitschaft:
        g = self.gesundheit()
        return Bereitschaft(bool(g["datenbank"] and g["nachrichten"]), bool(g["datenbank"]), bool(g["nachrichten"]), self.konfiguration.umgebung, self.konfiguration.instanzkennung, jetzt())


class Produktionsbetrieb:
    """Composition Root für einen reproduzierbaren Laufzeitverbund."""
    def __init__(self, konfiguration: BetriebsKonfiguration | None = None, broker: Nachrichtenbroker | None = None):
        self.konfiguration = konfiguration or BetriebsKonfiguration()
        self.konfiguration.validieren()
        self.db = Datenbank(self.konfiguration.datenbank_url)
        self.broker = broker or LokalerNachrichtenbroker()
        self.betriebspruefer = Betriebspruefer(self.db, self.broker, self.konfiguration)

    def readiness_auswerten(self) -> dict[str, Any]:
        b = self.betriebspruefer.bereitschaft()
        return {
            "betriebsbereit": b.betriebsbereit,
            "datenbank": b.datenbank,
            "nachrichten": b.nachrichten,
            "umgebung": b.umgebung,
            "instanzkennung": b.instanzkennung,
            "zeitpunkt": b.zeitpunkt.isoformat(),
        }
