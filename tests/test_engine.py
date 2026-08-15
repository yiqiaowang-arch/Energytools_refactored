"""Tests for the engine facade: validation, version compatibility, backend
pluggability, result storage and explanation."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

import energytools
from energytools.engine import Engine, StubBackend
from energytools.engine.errors import (
    BackendError,
    CalculationError,
    CalculationInputError,
    ModelVersionMismatchError,
)
from energytools.engine.model import BuildingInput, ValidationReport, VersionInfo
from energytools.engine.result import Results
from energytools.engine.store import CalculationStore

from helpers import make_building_input


def _make_temp_directory() -> str:
    """A scratch directory for the on-disk store tests.

    Lives in the repo root (gitignored as ``energytools-store-*/``): the DSH
    file sandbox denies writes to the OS temp area, while pytest's tmp_path
    machinery trips the sandbox's directory scans/removals. Created with a
    bare ``mkdir``: ``tempfile.mkdtemp`` passes mode 0o700, which Python
    3.13 on Windows maps to a restrictive ACL that blocks file creation.
    """
    base = Path.cwd()
    for _ in range(100):
        candidate = base / f"energytools-store-{uuid.uuid4().hex[:8]}"
        try:
            candidate.mkdir()
            return str(candidate)
        except FileExistsError:
            continue
    raise RuntimeError("could not create a scratch directory")


class EchoBackend(StubBackend):
    """A minimal custom backend proving pluggability behind ``EngineBase``."""

    name = "echo"

    def __init__(self) -> None:
        self.version = "2.0"

    def calculate(self, input_: BuildingInput, dataset: str, model_release: str) -> Results:
        return Results(
            result_id="echo-1",
            versions=VersionInfo(dataset, model_release, self.version, "unknown"),
            inputs_hash=input_.inputs_hash(),
            input_=input_,
            backend=f"{self.name}@{self.version}",
            totals={"rooms": len(input_.rooms), "ngf_m2": input_.total_ngf()},
        )


class ExplodingBackend(StubBackend):
    """A backend that fails at runtime, to test the ``BackendError`` wrap."""

    name = "boom"

    def __init__(self) -> None:
        self.version = "1.0"

    def calculate(self, input_: BuildingInput, dataset: str, model_release: str) -> Results:
        raise RuntimeError("kaputt")


def test_validate_input_report(project: BuildingInput) -> None:
    engine = Engine()
    assert engine.validate_input(project, "V221", "1.0.0").valid
    assert engine.validate_input(project, "V221", "latest").valid
    report = engine.validate_input(project, "V199", "1.0.0")
    assert not report.valid
    assert any("compatible" in error for error in report.errors)
    report2 = engine.validate_input(project, "V221", "9.9.9")
    assert not report2.valid
    assert any("unknown model" in error for error in report2.errors)


def test_calculate_happy_path(project: BuildingInput) -> None:
    engine = Engine()
    result = engine.calculate(project, "V221", "1.0.0")
    assert result.versions.dataset == "V221"
    assert result.versions.model == "1.0.0"
    assert result.versions.implementation == energytools.__version__
    assert result.versions.climate == "meteoschweiz-2024"
    assert result.backend.startswith("stub@")
    assert result.trace_id == result.result_id
    # Stored and retrievable.
    assert engine.get_result(result.result_id) is result
    trace = engine.explain(result.result_id)
    assert trace.result_id == result.result_id
    assert trace.steps[-1].id == "resultate"


def test_calculate_resolves_latest_model(project: BuildingInput) -> None:
    result = Engine().calculate(project, "V221", "latest")
    assert result.versions.model == "1.0.0"


def test_calculate_unknown_model_raises(project: BuildingInput) -> None:
    engine = Engine()
    with pytest.raises(ModelVersionMismatchError) as exc_info:
        engine.calculate(project, "V221", "9.9.9")
    assert exc_info.value.details["model"] == "9.9.9"


def test_calculate_incompatible_dataset_raises(project: BuildingInput) -> None:
    engine = Engine()
    with pytest.raises(ModelVersionMismatchError) as exc_info:
        engine.calculate(project, "V199", "1.0.0")
    assert exc_info.value.details["dataset"] == "V199"


def test_calculate_invalid_input_raises(project: BuildingInput) -> None:
    engine = Engine()
    bad = make_building_input(climate_station_id=99)
    with pytest.raises(CalculationInputError) as exc_info:
        engine.calculate(bad, "V221", "1.0.0")
    assert any("climate_station_id" in error for error in exc_info.value.details["errors"])


def test_calculate_explicit_result_id(project: BuildingInput) -> None:
    engine = Engine()
    result = engine.calculate(project, "V221", "1.0.0", result_id="abc-123")
    assert result.result_id == "abc-123"
    assert engine.get_result("abc-123").result_id == "abc-123"
    assert engine.explain("abc-123").result_id == "abc-123"


def test_get_result_and_explain_unknown(project: BuildingInput) -> None:
    engine = Engine()
    with pytest.raises(CalculationError):
        engine.get_result("does-not-exist")
    with pytest.raises(CalculationError):
        engine.explain("does-not-exist")


def test_pluggable_backend(project: BuildingInput) -> None:
    engine = Engine(default_backend=EchoBackend())
    result = engine.calculate(project, "V221", "1.0.0")
    assert result.backend == "echo@2.0"
    assert result.totals["rooms"] == 2
    assert result.totals["ngf_m2"] == pytest.approx(1350.0)
    # The engine still resolves the versions of the result.
    assert result.versions.model == "1.0.0"
    assert result.versions.climate == "meteoschweiz-2024"
    assert engine.get_result(result.result_id).backend == "echo@2.0"


def test_backend_failure_wrapped(project: BuildingInput) -> None:
    engine = Engine()
    with pytest.raises(BackendError) as exc_info:
        engine.calculate(project, "V221", "1.0.0", backend=ExplodingBackend())
    assert exc_info.value.details["backend"] == "boom"


def test_store_memory_list_newest_first(project: BuildingInput) -> None:
    engine = Engine()
    first = engine.calculate(project, "V221", "1.0.0")
    second = engine.calculate(project, "V221", "1.0.0")
    assert engine.store.list() == [second.result_id, first.result_id]
    assert engine.store.list(limit=1) == [second.result_id]


def test_store_directory_roundtrip(project: BuildingInput) -> None:
    # Note: uses tempfile instead of pytest's tmp_path fixture — the DSH file
    # sandbox denies the tmpdir plugin's directory scans/removals.
    directory = _make_temp_directory()
    try:
        backend = StubBackend()
        result = backend.calculate(project, "V221", "1.0.0")
        store = CalculationStore(directory=directory)
        store.save(result)
        assert store.get(result.result_id) == result
        assert store.list() == [result.result_id]
        # A fresh store (new process) reloads from disk.
        fresh = CalculationStore(directory=directory)
        assert fresh.get(result.result_id) == result
        assert fresh.list() == [result.result_id]
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_store_directory_unknown_id() -> None:
    directory = _make_temp_directory()
    try:
        store = CalculationStore(directory=directory)
        with pytest.raises(CalculationError):
            store.get("nope")
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_store_rejects_unsafe_result_id(project: BuildingInput) -> None:
    directory = _make_temp_directory()
    try:
        store = CalculationStore(directory=directory)
        result = StubBackend().calculate(project, "V221", "1.0.0")
        unsafe = Results(
            result_id="../evil",
            versions=result.versions,
            inputs_hash=result.inputs_hash,
            input_=result.input_,
            backend=result.backend,
        )
        with pytest.raises(ValueError):
            store.save(unsafe)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_backend_validate_rejection_is_input_error(project: BuildingInput) -> None:
    class RejectingBackend(StubBackend):
        name = "reject"

        def __init__(self) -> None:
            self.version = "1.0"

        def validate(self, input_: BuildingInput, dataset: str) -> ValidationReport:
            return ValidationReport(errors=("not mappable to workbook ranges",))

    engine = Engine()
    with pytest.raises(CalculationInputError) as exc_info:
        engine.calculate(project, "V221", "1.0.0", backend=RejectingBackend())
    assert "rejected" in str(exc_info.value)
