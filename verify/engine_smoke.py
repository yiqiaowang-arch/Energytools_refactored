"""End-to-end smoke of the public engine API (doc part 04 §4/§5 example flows)."""

from __future__ import annotations

import json

from energytools.engine import (
    CalculationEngine,
    EnergyCarrier,
    Engine,
    Results,
    RoomRow,
    StubBackend,
    ValidationReport,
)
from energytools.engine.model import BuildingInput, VentilationSystem

room_office = RoomRow(
    name="Büro 1",
    room_use_id="1.01",
    ebf=True,
    ngf=1200.0,
    geraete=8.0,
    beleuchtung=10.0,
    lueftung_system="LA03",
    lueftung_volume_flow=4000.0,
    gekuehlt=True,
)
la03 = VentilationSystem(
    id="LA03",
    regulation="2-stufig",
    volume_flow_standard=4000.0,
    sfp=1.8,
    fan_power=7.5,
    wrg=0.7,
)
project = BuildingInput(
    name="Beispiel",
    author="Max Muster",
    climate_station_id=40,
    rooms=(room_office,),
    ventilation=(la03,),
)

assert EnergyCarrier.parse("Elektrizität") is EnergyCarrier.ELECTRICITY

engine: Engine = CalculationEngine()
report: ValidationReport = engine.validate_input(project, "V221", "1.0.0")
assert report.valid, report.errors

result: Results = engine.calculate(project, "V221", "1.0.0", backend=StubBackend())
trace = engine.explain(result.trace_id)
assert trace.result_id == result.result_id
assert [s.id for s in trace.steps][-1] == "resultate"

payload = json.dumps(result.as_dict())  # JSON-ready API response
assert '"versions"' in payload and '"assumptions"' in payload
assert result.versions.dataset == "V221"
print(
    "OK —",
    result.result_id,
    "| carriers:",
    sorted(result.per_carrier),
    "| steps:",
    len(trace.steps),
)
