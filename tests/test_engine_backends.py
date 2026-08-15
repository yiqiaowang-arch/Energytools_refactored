"""Tests for the backend contract: ``EngineBase`` abstraction and the
``StubBackend`` implementation."""

from __future__ import annotations

import uuid

import pytest

import energytools
from energytools.engine.backends import EngineBase, StubBackend
from energytools.engine.model import BuildingInput, ValidationReport

from helpers import make_building_input


def test_engine_base_is_abstract() -> None:
    with pytest.raises(TypeError):
        EngineBase()  # type: ignore[abstract]


def test_engine_base_partial_implementation_still_abstract() -> None:
    class Partial(EngineBase):
        name = "partial"

        def validate(self, input_: BuildingInput, dataset: str) -> ValidationReport:
            return ValidationReport()

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_stub_backend_identity() -> None:
    backend = StubBackend()
    assert backend.name == "stub"
    assert backend.version == energytools.__version__
    assert isinstance(backend, EngineBase)


def test_stub_backend_validate() -> None:
    backend = StubBackend()
    report = backend.validate(make_building_input(), "V221")
    assert report.valid
    assert any("stub" in warning for warning in report.warnings)
    invalid = make_building_input(climate_station_id=99)
    assert not backend.validate(invalid, "V221").valid


def test_stub_backend_calculate_returns_results(project: BuildingInput) -> None:
    backend = StubBackend()
    result = backend.calculate(project, "V221", "1.0.0")
    assert uuid.UUID(result.result_id)
    assert result.backend == f"stub@{backend.version}"
    assert result.per_room
    assert result.per_system
    assert result.totals["rooms"] == 2
    assert result.trace is not None
    assert result.trace.result_id == result.result_id


def test_stub_backend_is_deterministic(project: BuildingInput) -> None:
    backend = StubBackend()
    first = backend.calculate(project, "V221", "1.0.0")
    second = backend.calculate(project, "V221", "1.0.0")
    assert first.result_id != second.result_id
    assert first.per_room == second.per_room
    assert first.per_system == second.per_system
    assert first.per_carrier == second.per_carrier
    assert first.totals == second.totals
    assert first.assumptions == second.assumptions
    assert first.inputs_hash == second.inputs_hash
