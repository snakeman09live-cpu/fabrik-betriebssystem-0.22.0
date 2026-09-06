from __future__ import annotations
from .ausfuehrungslauf import Ausfuehrungslaufdienst, Ausfuehrungslauf

class PersistenterAusfuehrungslaufdienst(Ausfuehrungslaufdienst):
    def __init__(self, ereignisbus, db):
        super().__init__(ereignisbus)
        self.db = db

    def erstellen(self, planversion, aufgaben):
        lauf = super().erstellen(planversion, aufgaben)
        self.db.lauf_speichern(lauf)
        return lauf

    def ausfuehren(self, laufkennung):
        lauf = super().ausfuehren(laufkennung)
        self.db.lauf_speichern(lauf)
        return lauf
