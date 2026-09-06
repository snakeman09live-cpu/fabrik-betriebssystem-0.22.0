from __future__ import annotations
from dataclasses import dataclass, field
from queue import Queue, Empty
from threading import Event, Thread
from typing import Callable

@dataclass
class Arbeitswarteschlange:
    _warteschlange: Queue = field(default_factory=Queue)
    def einreihen(self, kennung: str) -> None:
        self._warteschlange.put(kennung)
    def entnehmen(self, timeout: float = 0.2):
        try:
            return self._warteschlange.get(timeout=timeout)
        except Empty:
            return None
    def erledigt(self):
        self._warteschlange.task_done()

class Arbeiter:
    def __init__(self, warteschlange: Arbeitswarteschlange, handler: Callable[[str], None]):
        self.warteschlange = warteschlange
        self.handler = handler
        self._stop = Event()
        self._thread: Thread | None = None

    def starten(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._arbeiten, name='fabrik-arbeiter', daemon=True)
        self._thread.start()

    def _arbeiten(self):
        while not self._stop.is_set():
            kennung = self.warteschlange.entnehmen()
            if kennung is None:
                continue
            try:
                self.handler(kennung)
            finally:
                self.warteschlange.erledigt()

    def stoppen(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
