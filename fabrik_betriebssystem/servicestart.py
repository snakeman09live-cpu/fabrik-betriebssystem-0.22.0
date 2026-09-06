from __future__ import annotations
import os
from .produktionsbetrieb import Produktionsbetrieb, BetriebsKonfiguration
from .orchestrierung import Orchestrator


def betriebsdienst() -> Produktionsbetrieb:
    return Produktionsbetrieb(BetriebsKonfiguration())


def start_api() -> None:
    import uvicorn
    uvicorn.run("fabrik_betriebssystem.api:app", host=os.getenv("FABRIK_API_HOST", "0.0.0.0"), port=int(os.getenv("FABRIK_API_PORT", "8000")))


def start_worker() -> None:
    betrieb = betriebsdienst()
    from .worker import Worker
    worker = Worker(betrieb.db)
    worker.ausfuehren()


def start_scheduler() -> None:
    betrieb = betriebsdienst()
    from .scheduler import Scheduler
    scheduler = Scheduler(betrieb.db)
    scheduler.ausfuehren()
