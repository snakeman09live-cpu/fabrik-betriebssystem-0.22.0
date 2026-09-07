from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any

@dataclass(frozen=True)
class Auftrag:
    auftragskennung: str
    inhalt: dict[str, Any]
    lease_sekunden: int = 30

class Auftragsbroker(Protocol):
    def einreihen(self, auftrag: Auftrag) -> None: ...
    def uebernehmen(self, kunde: str, jetzt: float | None = None) -> Auftrag | None: ...
    def bestaetigen(self, kunde: str, auftragskennung: str) -> bool: ...
    def zurueckstellen(self, kunde: str, auftragskennung: str) -> bool: ...

class SpeicherBroker:
    def __init__(self):
        self._warteschlange: list[Auftrag] = []
        self._leases: dict[str, tuple[str, float]] = {}
    def einreihen(self, auftrag: Auftrag) -> None:
        if any(a.auftragskennung == auftrag.auftragskennung for a in self._warteschlange): return
        self._warteschlange.append(auftrag)
    def uebernehmen(self, kunde: str, jetzt: float | None = None) -> Auftrag | None:
        import time
        jetzt = time.time() if jetzt is None else jetzt
        for a in list(self._warteschlange):
            lease = self._leases.get(a.auftragskennung)
            if lease is None or lease[1] <= jetzt:
                self._leases[a.auftragskennung] = (kunde, jetzt + a.lease_sekunden)
                return a
        return None
    def bestaetigen(self, kunde: str, auftragskennung: str) -> bool:
        lease = self._leases.get(auftragskennung)
        if lease is None or lease[0] != kunde: return False
        self._leases.pop(auftragskennung, None)
        self._warteschlange = [a for a in self._warteschlange if a.auftragskennung != auftragskennung]
        return True
    def zurueckstellen(self, kunde: str, auftragskennung: str) -> bool:
        lease = self._leases.get(auftragskennung)
        if lease is None or lease[0] != kunde: return False
        self._leases.pop(auftragskennung, None)
        return True

class RedisBroker:
    def __init__(self, url: str):
        try:
            import redis
        except ImportError as exc: raise RuntimeError('REDIS_BIBLIOTHEK_FEHLT') from exc
        self.client = redis.Redis.from_url(url, decode_responses=True)
    def einreihen(self, auftrag: Auftrag) -> None:
        import json
        self.client.rpush('fabrik:auftraege', json.dumps({'auftragskennung':auftrag.auftragskennung,'inhalt':auftrag.inhalt,'lease_sekunden':auftrag.lease_sekunden}))
    def uebernehmen(self, kunde: str, jetzt: float | None = None) -> Auftrag | None:
        import json
        werte = self.client.blmove('fabrik:auftraege','fabrik:in_bearbeitung','LEFT','RIGHT',timeout=1)
        if not werte: return None
        d=json.loads(werte); self.client.hset(f"fabrik:lease:{d['auftragskennung']}",mapping={'kunde':kunde,'ablauf':(jetzt or __import__('time').time())+d['lease_sekunden'],'inhalt':json.dumps(d)})
        return Auftrag(**d)
    def bestaetigen(self, kunde: str, auftragskennung: str) -> bool:
        key=f'fabrik:lease:{auftragskennung}'; lease=self.client.hgetall(key)
        if not lease or lease.get('kunde')!=kunde: return False
        self.client.delete(key); self.client.lrem('fabrik:in_bearbeitung',0,lease['inhalt']); return True
    def zurueckstellen(self, kunde: str, auftragskennung: str) -> bool:
        # Nicht an bestaetigen() delegieren: Zurueckstellen muss den Auftrag
        # erneut uebernehmbar machen, nicht verwerfen.
        key=f'fabrik:lease:{auftragskennung}'; lease=self.client.hgetall(key)
        if not lease or lease.get('kunde')!=kunde: return False
        inhalt=lease['inhalt']
        pipe=self.client.pipeline()
        pipe.lrem('fabrik:in_bearbeitung',0,inhalt)
        pipe.lpush('fabrik:auftraege',inhalt)
        pipe.delete(key)
        pipe.execute()
        return True
