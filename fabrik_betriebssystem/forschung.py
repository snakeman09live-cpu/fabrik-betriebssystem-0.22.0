from dataclasses import dataclass

@dataclass(frozen=True)
class Simulation:
    simulationskennung: str
    szenariokennung: str
    parameter: dict

class Simulationsdienst:
    def ausfuehren(self, simulation: Simulation, laufzeit_basis: float) -> dict:
        faktor=float(simulation.parameter.get("laufzeitfaktor", 1.0))
        return {"simulationskennung": simulation.simulationskennung, "szenariokennung": simulation.szenariokennung, "prognostizierte_laufzeit": laufzeit_basis*faktor, "ist_simulation": True}
