"""Result objects of the calculation engine: ``Results`` and the explain trace.

Mirrors the target-state API reference
``docs/architecture+api-reference/04-gebaeude-engine.md`` §4.2/§4.3
(``CalculationResult`` / ``CalculationTrace``). The German source terms of
the workbook are kept verbatim (Resultate, Endenergie, Energieträger, ...).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from energytools.engine.model import BuildingInput, VersionInfo

__all__ = ["CalculationTrace", "Results", "TraceStep"]


@dataclass(frozen=True)
class TraceStep:
    """One node of the calculation graph (doc part 04 §4.3, ``TraceStep``).

    Room KPI derivation → building aggregation → AHU bins → generation →
    resultate, each with its inputs, formula reference and outputs.
    """

    id: str
    kind: str
    label: str
    inputs: dict[str, Any] = field(default_factory=dict)
    formula: str | None = None
    outputs: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation."""
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "inputs": dict(self.inputs),
            "formula": self.formula,
            "outputs": dict(self.outputs),
            "provenance": dict(self.provenance) if self.provenance is not None else None,
        }


@dataclass(frozen=True)
class CalculationTrace:
    """Step-by-step explainable trace of one calculation (doc part 04 §4.3).

    The payload of ``GET /calculations/{id}/explain``. Note: the doc lists a
    ``steps()`` method alongside the ``steps`` attribute; a dataclass field
    and a method cannot share a name, so ``steps`` is the attribute and
    :meth:`step` provides indexed access.
    """

    result_id: str
    steps: tuple[TraceStep, ...] = ()

    def step(self, step_id: str) -> TraceStep:
        """The step with the given id.

        Raises:
            KeyError: for unknown step ids.
        """
        for step in self.steps:
            if step.id == step_id:
                return step
        raise KeyError(step_id)

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation."""
        return {
            "result_id": self.result_id,
            "steps": [step.as_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalculationTrace:
        """Reconstruct from :meth:`as_dict` output."""
        return cls(
            result_id=data["result_id"],
            steps=tuple(TraceStep(**step) for step in data["steps"]),
        )


@dataclass(frozen=True)
class Results:
    """The complete, reproducible outcome of one calculation (doc part 04 §4.2).

    Versions, inputs hash, assumptions, warnings, overridden values, results
    per room/system/carrier, totals and intermediates, plus the explain
    trace. ``as_dict()`` is JSON-ready (``POST /calculations`` response).
    """

    result_id: str
    versions: VersionInfo
    inputs_hash: str
    input_: BuildingInput
    backend: str
    per_room: dict[str, Any] = field(default_factory=dict)
    per_system: dict[str, Any] = field(default_factory=dict)
    per_carrier: dict[str, float] = field(default_factory=dict)
    totals: dict[str, float] = field(default_factory=dict)
    intermediates: dict[str, Any] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    overridden_values: tuple[dict[str, Any], ...] = ()
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace: CalculationTrace | None = None

    @property
    def trace_id(self) -> str:
        """Alias for :attr:`result_id` — the id passed to ``Engine.explain``.

        This is the ``traceId`` of the milestone contract: the same id that
        fetches the stored result also fetches its trace.
        """
        return self.result_id

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation (datetimes as ISO 8601, tuples as lists)."""
        return {
            "result_id": self.result_id,
            "versions": self.versions.as_dict(),
            "inputs_hash": self.inputs_hash,
            "input": self.input_.as_dict(),
            "backend": self.backend,
            "per_room": {key: dict(value) for key, value in self.per_room.items()},
            "per_system": {key: dict(value) for key, value in self.per_system.items()},
            "per_carrier": dict(self.per_carrier),
            "totals": dict(self.totals),
            "intermediates": dict(self.intermediates),
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
            "overridden_values": [dict(value) for value in self.overridden_values],
            "computed_at": self.computed_at.isoformat(),
            "trace": self.trace.as_dict() if self.trace is not None else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Results:
        """Reconstruct from :meth:`as_dict` output."""
        return cls(
            result_id=data["result_id"],
            versions=VersionInfo(**data["versions"]),
            inputs_hash=data["inputs_hash"],
            input_=BuildingInput.from_dict(data["input"]),
            backend=data["backend"],
            per_room={key: dict(value) for key, value in data["per_room"].items()},
            per_system={key: dict(value) for key, value in data["per_system"].items()},
            per_carrier=dict(data["per_carrier"]),
            totals=dict(data["totals"]),
            intermediates=dict(data["intermediates"]),
            assumptions=tuple(data["assumptions"]),
            warnings=tuple(data["warnings"]),
            overridden_values=tuple(dict(value) for value in data["overridden_values"]),
            computed_at=datetime.fromisoformat(
                data["computed_at"].replace("Z", "+00:00")  # noqa: FURB162 - ISO-8601 Zulu -> offset
            ),
            trace=CalculationTrace.from_dict(data["trace"])
            if data.get("trace") is not None
            else None,
        )
