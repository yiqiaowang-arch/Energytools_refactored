"""energytools.engine — calculation engine input/output models and pluggable backends.

Implements the calculation engine of the target-state API reference
``docs/architecture+api-reference/04-gebaeude-engine.md`` §4/§5 (there named
``energytools.gebaeude.engine`` / ``backends``), with the milestone names
``BuildingInput`` / ``Results`` / ``EngineBase`` and a structural
``StubBackend``. German source terms of the workbook are kept verbatim
(Gebäude, Lüftung, Erzeugung, Resultate, Energieträger, Nutzungsgrad, ...).

Example:
    from energytools.engine import Engine, StubBackend

    engine = Engine()
    result = engine.calculate(project, "V221", "1.0.0", backend=StubBackend())
    trace = engine.explain(result.trace_id)
"""

from energytools.engine.backends import EngineBase, StubBackend
from energytools.engine.engine import DEFAULT_MODEL, CalculationEngine, Engine
from energytools.engine.errors import (
    BackendError,
    CalculationError,
    CalculationInputError,
    EnergyToolsError,
    ModelVersionMismatchError,
    UnknownValueKindError,
)
from energytools.engine.model import (
    BuildingInput,
    EndUse,
    EnergyCarrier,
    GenerationSystem,
    ModelRelease,
    RoomRow,
    ValidationReport,
    ValueKind,
    VentilationSystem,
    VersionInfo,
)
from energytools.engine.native.backend import NativeBackend
from energytools.engine.result import CalculationTrace, Results, TraceStep
from energytools.engine.store import CalculationStore

__all__ = [
    "DEFAULT_MODEL",
    "BackendError",
    "BuildingInput",
    "CalculationEngine",
    "CalculationError",
    "CalculationInputError",
    "CalculationStore",
    "CalculationTrace",
    "EndUse",
    "EnergyCarrier",
    "EnergyToolsError",
    "Engine",
    "EngineBase",
    "GenerationSystem",
    "ModelRelease",
    "ModelVersionMismatchError",
    "NativeBackend",
    "Results",
    "RoomRow",
    "StubBackend",
    "TraceStep",
    "UnknownValueKindError",
    "ValidationReport",
    "ValueKind",
    "VentilationSystem",
    "VersionInfo",
]
