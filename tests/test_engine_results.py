"""Tests for the engine result objects: ``Results`` (assumptions / warnings /
versions / traceId), the trace, and the JSON round trip."""

from __future__ import annotations

import json

import pytest

import energytools
from energytools.engine.backends import StubBackend
from energytools.engine.model import BuildingInput
from energytools.engine.result import CalculationTrace, Results, TraceStep


def make_result(project: BuildingInput) -> Results:
    return StubBackend().calculate(project, "V221", "1.0.0")


def test_results_carries_contract_fields(project: BuildingInput) -> None:
    result = make_result(project)
    assert result.result_id
    assert result.trace_id == result.result_id
    assert result.versions.dataset == "V221"
    assert result.versions.model == "1.0.0"
    assert result.versions.implementation == energytools.__version__
    assert result.versions.climate == "unknown"  # replaced by the engine
    assert result.inputs_hash == project.inputs_hash()
    assert result.backend.startswith("stub@")
    assert result.assumptions
    assert result.warnings
    assert result.overridden_values == ()
    assert result.computed_at.tzinfo is not None


def test_results_structural_values(project: BuildingInput) -> None:
    result = make_result(project)
    assert result.per_room["Büro 1"]["effective_area_m2"] == pytest.approx(1200.0)
    assert result.per_room["Sitzungszimmer"]["effective_area_m2"] == pytest.approx(150.0)
    assert result.per_room["Büro 1"]["installed_electric_kw"] == pytest.approx(21.6)
    assert result.per_system["LA03"]["effective_volume_flow_m3h"] == pytest.approx(4000.0)
    assert result.per_carrier["el"] == pytest.approx(29.85)
    assert result.totals["ngf_m2"] == pytest.approx(1350.0)
    assert result.totals["ebf_m2"] == pytest.approx(1350.0)
    assert result.totals["rooms"] == 2


def test_results_as_dict_is_json_ready(project: BuildingInput) -> None:
    result = make_result(project)
    data = json.loads(json.dumps(result.as_dict()))
    assert data["result_id"] == result.result_id
    assert data["versions"] == result.versions.as_dict()
    assert data["backend"] == result.backend
    assert data["computed_at"] == result.computed_at.isoformat()
    assert data["trace"]["result_id"] == result.result_id
    assert data["trace"]["steps"][-1]["id"] == "resultate"
    assert data["input"]["name"] == "Beispiel"


def test_results_from_dict_roundtrip(project: BuildingInput) -> None:
    result = make_result(project)
    assert Results.from_dict(result.as_dict()) == result


def test_trace_access(project: BuildingInput) -> None:
    result = make_result(project)
    assert result.trace is not None
    assert result.trace.result_id == result.result_id
    assert [step.id for step in result.trace.steps] == [
        "validate",
        "rooms",
        "ventilation",
        "generation",
        "totals",
        "resultate",
    ]
    step = result.trace.step("rooms")
    assert step.kind == "kpi"
    assert step.outputs["Büro 1"]["installed_electric_kw"] > 0
    with pytest.raises(KeyError):
        result.trace.step("does-not-exist")


def test_trace_roundtrip(project: BuildingInput) -> None:
    result = make_result(project)
    assert result.trace is not None
    restored = CalculationTrace.from_dict(result.trace.as_dict())
    assert restored == result.trace
    assert restored.step("resultate").id == "resultate"


def test_trace_step_as_dict() -> None:
    step = TraceStep(
        id="rooms",
        kind="kpi",
        label="Raum-KPIs",
        inputs={"rooms": ["Büro 1"]},
        formula="share × NGF",
        outputs={"Büro 1": {"effective_area_m2": 1200.0}},
        provenance={"workbook": "2024_Gebaeude-Tool_dfi_V221.xlsm", "sheet": "Gebäude"},
    )
    data = step.as_dict()
    assert data["id"] == "rooms"
    assert data["provenance"]["sheet"] == "Gebäude"
    assert json.loads(json.dumps(data)) == data
