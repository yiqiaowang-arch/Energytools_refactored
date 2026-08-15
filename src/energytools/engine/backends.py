"""Pluggable calculation backends (doc part 04 §5).

The ``EngineBase`` contract (§5.1, there named ``CalculationBackend``) and
the deterministic structural ``StubBackend``. The real backends —
``ExcelBackend`` (reference runtime over workbook copies, §5.2) and
``NativeBackend`` (ported pure-Python runtime, §5.3) — plug into the same
contract in later milestones.

German source terms are kept verbatim (Gebäude, Lüftung, Erzeugung,
Resultate, Energieträger, Volllaststunden, FeuchteLuft, ...).
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import energytools
from energytools.engine.model import (
    BuildingInput,
    EnergyCarrier,
    RoomRow,
    ValidationReport,
    VentilationSystem,
    VersionInfo,
)
from energytools.engine.result import CalculationTrace, Results, TraceStep

__all__ = ["EngineBase", "StubBackend"]

#: Source workbook of the Gebaeude-Tool, referenced by the trace provenance.
WORKBOOK = "2024_Gebaeude-Tool_dfi_V221.xlsm"


class EngineBase(ABC):
    """The backend contract (doc part 04 §5.1, ``CalculationBackend``).

    A backend executes one *validated* calculation and reports its identity;
    the engine treats all backends uniformly. ``name`` is e.g. ``"excel"`` /
    ``"native"`` / ``"stub"``, ``version`` the backend implementation version.

    Attributes:
        name: Backend name.
        version: Backend version.
    """

    name: str = "abstract"
    version: str = ""

    @abstractmethod
    def calculate(self, input_: BuildingInput, dataset: str, model_release: str) -> Results:
        """Run one validated calculation and return its results.

        Args:
            input_: The validated building input.
            dataset: Dataset release id (e.g. ``"V221"``).
            model_release: Model release id (e.g. ``"1.0.0"``).

        Returns:
            Results with per-room/per-system/per-carrier values, totals,
            intermediates, assumptions, warnings and the explain trace.

        Raises:
            BackendError: backend failure (subclasses).
            ModelVersionMismatchError: version conflict detected by the backend.
            CalculationError: internal inconsistency.
        """

    @abstractmethod
    def validate(self, input_: BuildingInput, dataset: str) -> ValidationReport:
        """Backend capability validation.

        Args:
            input_: The building input.
            dataset: Dataset release id.

        Returns:
            ValidationReport — e.g. for the future ExcelBackend: whether all
            inputs are mappable to workbook ranges.
        """


class StubBackend(EngineBase):
    """Deterministic structural stub backend (``name`` = ``"stub"``).

    Computes no physics (the FeuchteLuft_Formeln.bas psychrometrics and the
    AHU temperature-bin engine of ``Berechnung LU`` arrive with the native
    backend): it aggregates structural values only — per-room effective areas
    and installed electric power, per-system effective volume flows, and
    building totals — so that the engine I/O contract, backend pluggability
    and the explain trace can be exercised without Excel or the ported model.
    All energy values are placeholders; ``assumptions``/``warnings`` state
    this explicitly.
    """

    name = "stub"

    def __init__(self, implementation_version: str | None = None) -> None:
        """Args:
        implementation_version: Overrides the library version in
            ``Results.backend`` (defaults to ``energytools.__version__``).
        """
        self.version = implementation_version or energytools.__version__

    def validate(self, input_: BuildingInput, dataset: str) -> ValidationReport:
        """Structural validation plus a stub capability warning.

        The workbook-range capability check of the future ExcelBackend is
        explicitly not performed.
        """
        report = input_.validate()
        warnings = report.warnings + (
            "stub backend: structural validation only; no workbook-range "
            "capability check (ExcelBackend arrives in a later milestone)",
        )
        return ValidationReport(errors=report.errors, warnings=warnings)

    def calculate(self, input_: BuildingInput, dataset: str, model_release: str) -> Results:
        """Run the structural stub calculation and build the full ``Results``.

        The ``versions`` quadruple built here is provisional (climate
        ``"unknown"``); the engine replaces it with the resolved versions
        after the call.
        """
        report = input_.validate()
        result_id = str(uuid.uuid4())

        per_room = {room.name: self._room_kpis(room) for room in input_.rooms}
        per_system = {
            system.id: self._system_kpis(system) for system in input_.ventilation
        }
        installed_electric_kw = sum(
            kpis["installed_electric_kw"] for kpis in per_room.values()
        ) + sum(kpis.get("fan_power_kw") or 0.0 for kpis in per_system.values())

        totals = {
            "ngf_m2": round(input_.total_ngf(), 6),
            "ebf_m2": round(input_.total_ebf_area(), 6),
            "rooms": len(input_.rooms),
            "ventilation_systems": len(input_.ventilation),
            "installed_electric_kw": round(installed_electric_kw, 6),
        }
        per_carrier = {
            EnergyCarrier.ELECTRICITY.value: round(installed_electric_kw, 6)
        }

        assumptions = (
            "Stub backend: structural aggregation only — no psychrometric "
            "calculation (FeuchteLuft_Formeln.bas) and no AHU temperature-bin "
            "engine (Berechnung LU).",
            "Energieträger 'el' (Elektrizität) carries installed electric "
            "power in kW, not Endenergie in kWh/a.",
            "Volllaststunden are not applied; per_system values are "
            "design-point values of the Lüftung sheet.",
        )
        warnings = report.warnings + (
            "stub backend: energy values are placeholders (structural values only).",
        )
        intermediates: dict[str, Any] = {
            "sources": {
                "rooms": "Gebäude",
                "ventilation": "Lüftung",
                "generation": "Erzeugung",
                "catalog": "Nutzungsgrad",
                "resultate": "Resultate",
                "workbook": WORKBOOK,
            }
        }

        trace = CalculationTrace(
            result_id=result_id,
            steps=(
                TraceStep(
                    id="validate",
                    kind="validation",
                    label="Input validation (Gebäude sheet)",
                    inputs={
                        "climate_station_id": input_.climate_station_id,
                        "rooms": len(input_.rooms),
                        "value_kind": input_.value_kind.value,
                    },
                    outputs={
                        "valid": report.valid,
                        "errors": list(report.errors),
                        "warnings": list(report.warnings),
                    },
                    provenance={"workbook": WORKBOOK, "sheet": "Gebäude"},
                ),
                TraceStep(
                    id="rooms",
                    kind="kpi",
                    label="Room KPIs (Raum-KPIs)",
                    inputs={"rooms": [room.name for room in input_.rooms]},
                    outputs=per_room,
                    formula="share × NGF; P × A / 1000 (stub structural KPIs)",
                    provenance={"workbook": WORKBOOK, "sheet": "Gebäude"},
                ),
                TraceStep(
                    id="ventilation",
                    kind="kpi",
                    label="Lüftung systems",
                    inputs={"systems": [system.id for system in input_.ventilation]},
                    outputs=per_system,
                    formula="Projekt → Prozess → Standard flow priority",
                    provenance={"workbook": WORKBOOK, "sheet": "Lüftung"},
                ),
                TraceStep(
                    id="generation",
                    kind="kpi",
                    label="Erzeugung systems",
                    inputs={
                        "systems": [system.id for system in input_.generation],
                        "catalog": "Nutzungsgrad",
                    },
                    outputs={"systems": len(input_.generation)},
                    provenance={"workbook": WORKBOOK, "sheet": "Erzeugung"},
                ),
                TraceStep(
                    id="totals",
                    kind="aggregation",
                    label="Building totals (Summen)",
                    inputs={"rooms": len(input_.rooms)},
                    outputs=totals,
                    provenance={"workbook": WORKBOOK, "sheet": "Gebäude"},
                ),
                TraceStep(
                    id="resultate",
                    kind="aggregation",
                    label="Resultate per Energieträger",
                    inputs={"carriers": sorted(per_carrier)},
                    outputs=per_carrier,
                    provenance={"workbook": WORKBOOK, "sheet": "Resultate"},
                ),
            ),
        )

        return Results(
            result_id=result_id,
            versions=VersionInfo(
                dataset=dataset,
                model=model_release,
                implementation=self.version,
                climate="unknown",
            ),
            inputs_hash=input_.inputs_hash(),
            input_=input_,
            backend=f"{self.name}@{self.version}",
            per_room=per_room,
            per_system=per_system,
            per_carrier=per_carrier,
            totals=totals,
            intermediates=intermediates,
            assumptions=assumptions,
            warnings=warnings,
            overridden_values=(),
            computed_at=datetime.now(timezone.utc),
            trace=trace,
        )

    @staticmethod
    def _room_kpis(room: RoomRow) -> dict[str, Any]:
        area = room.effective_area()
        geraete_kw = (room.geraete or 0.0) * area / 1000.0
        prozessanlagen_kw = (room.prozessanlagen or 0.0) * area / 1000.0
        beleuchtung_kw = (room.beleuchtung or 0.0) * area / 1000.0
        return {
            "room_use_id": room.room_use_id,
            "ebf": room.ebf,
            "ngf_m2": round(room.ngf, 6),
            "effective_area_m2": round(area, 6),
            "geraete_kw": round(geraete_kw, 6),
            "prozessanlagen_kw": round(prozessanlagen_kw, 6),
            "beleuchtung_kw": round(beleuchtung_kw, 6),
            "installed_electric_kw": round(
                geraete_kw + prozessanlagen_kw + beleuchtung_kw, 6
            ),
            "gekuehlt": room.gekuehlt,
            "beheizt": room.beheizt,
            "warmwasser": room.warmwasser,
        }

    @staticmethod
    def _system_kpis(system: VentilationSystem) -> dict[str, Any]:
        return {
            "room_use": system.room_use,
            "effective_volume_flow_m3h": system.effective_volume_flow(),
            "sfp_w_per_m3h": system.sfp,
            "fan_power_kw": system.fan_power,
            "regulation": system.regulation,
            "full_load_hours": system.full_load_hours,
            "wrg": system.wrg,
        }
