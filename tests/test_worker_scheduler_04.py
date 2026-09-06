from datetime import datetime, timezone, timedelta
import time
from fabrik_betriebssystem.worker import Arbeitswarteschlange, Arbeiter
from fabrik_betriebssystem.scheduler import Ablaufplaner

def test_scheduler_und_arbeiter():
    q=Arbeitswarteschlange(); p=Ablaufplaner(q); seen=[]
    p.planen('v1', datetime.now(timezone.utc)-timedelta(seconds=1))
    assert p.faellige_einreihen()==['v1']
    a=Arbeiter(q, seen.append); a.starten();
    for _ in range(20):
        if seen==['v1']: break
        time.sleep(0.01)
    a.stoppen()
    assert seen==['v1']
