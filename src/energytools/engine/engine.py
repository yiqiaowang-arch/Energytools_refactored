"""The orchestration facade of the calculation service (doc part 04 §4.1).

``Engine`` (alias ``CalculationEngine``) validates input → calculates over a
pluggable backend → explains, and stores results for reproducibility. The
backends (``ExcelBackend`` reference / ``NativeBackend`` ported / ``StubBackend``)
are interchangeable behind the ``EngineBase`` contract, and the engine
records which backend produced a result.
"""

from __future__ import annotations

import dataclasses
from datetime import date

import energytools
from energytools.engine.backends import EngineBase, StubBackend
from energytools.engine.errors import (
    BackendError,
    CalculationError,
    CalculationInputError,
    EnergyToolsError,
    ModelVersionMismatchError,
)
from energytools.engine.model import BuildingInput, ModelRelease, ValidationReport, VersionInfo
from energytools.engine.result import CalculationTrace, Results
from energytools.engine.store import CalculationStore

__all__ = ["DEFAULT_MODEL", "CalculationEngine", "Engine"]

#: The model release installed with this milestone: model 1.0.0 is compatible
#: with the V221 dataset release and the MeteoSchweiz 2024 climate data.
DEFAULT_MODEL = ModelRelease(
    id="1.0.0",
    compatible_dataset_releases=frozenset({"V221"}),
    compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
    publication_date=date(2025, 4, 20),
)


class Engine:
    """Orchestration facade: validate → calculate → explain (doc part 04 §4.1).

    Args:
        store: Result store (in-memory by default).
        default_backend: Backend used when ``calculate`` gets none
            (``StubBackend`` by default — the only backend of this milestone).
        models: Installed model releases by id (``DEFAULT_MODEL`` by default).
        implementation_version: Library version recorded in ``VersionInfo``
            (``energytools.__version__`` by default).
    """

    def __init__(
        self,
        store: CalculationStore | None = None,
        default_backend: EngineBase | None = None,
        models: dict[str, ModelRelease] | None = None,
        implementation_version: str | None = None,
    ) -> None:
        self.store = store or CalculationStore()
        self.default_backend = default_backend
        self.models: dict[str, ModelRelease] = (
            dict(models) if models else {DEFAULT_MODEL.id: DEFAULT_MODEL}
        )
        self.implementation_version = implementation_version or energytools.__version__

    # -- version resolution -------------------------------------------------

    def _resolve_model(self, model_release: str) -> ModelRelease:
        """Resolve a model id (``"latest"`` = newest publication date).

        Raises:
            ModelVersionMismatchError: unknown model release.
        """
        if model_release == "latest":
            candidates = sorted(self.models.values(), key=lambda model: model.publication_date)
            if not candidates:
                raise ModelVersionMismatchError(
                    "no model releases installed", {"model": model_release}
                )
            return candidates[-1]
        model = self.models.get(model_release)
        if model is None:
            raise ModelVersionMismatchError(
                f"unknown model release {model_release!r} (installed: {sorted(self.models)})",
                {"model": model_release},
            )
        return model

    def _resolve_versions(self, dataset: str, model_release: str) -> VersionInfo:
        """Resolve the concrete version quadruple; never called silently.

        Raises:
            ModelVersionMismatchError: unknown model or incompatible dataset.
        """
        model = self._resolve_model(model_release)
        if dataset not in model.compatible_dataset_releases:
            raise ModelVersionMismatchError(
                f"dataset release {dataset!r} is not compatible with model "
                f"{model.id!r} (compatible: {sorted(model.compatible_dataset_releases)})",
                {
                    "dataset": dataset,
                    "model": model.id,
                    "compatible_dataset_releases": sorted(model.compatible_dataset_releases),
                },
            )
        climate = (
            min(model.compatible_climate_versions)
            if model.compatible_climate_versions
            else "unknown"
        )
        return VersionInfo(
            dataset=dataset,
            model=model.id,
            implementation=self.implementation_version,
            climate=climate,
        )

    def _version_errors(self, dataset: str, model_release: str) -> tuple[str, ...]:
        try:
            self._resolve_versions(dataset, model_release)
        except ModelVersionMismatchError as exc:
            return (str(exc),)
        return ()

    # -- public API ---------------------------------------------------------

    def validate_input(self, input_: BuildingInput, dataset: str, model_release: str) -> ValidationReport:
        """Structural + domain validation and version compatibility.

        Never raises — hard problems are returned in the report.

        Args:
            input_: The building input.
            dataset: Dataset release id (e.g. ``"V221"``).
            model_release: Model release id (e.g. ``"1.0.0"``, ``"latest"``).

        Returns:
            ValidationReport (errors + warnings).
        """
        report = input_.validate()
        return ValidationReport(
            errors=report.errors + self._version_errors(dataset, model_release),
            warnings=report.warnings,
        )

    def calculate(
        self,
        input_: BuildingInput,
        dataset: str,
        model_release: str,
        backend: EngineBase | None = None,
        result_id: str | None = None,
    ) -> Results:
        """Validate first, then run the backend and store the result.

        Args:
            input_: The building input.
            dataset: Dataset release id.
            model_release: Model release id.
            backend: Backend to use (defaults to ``default_backend`` or a
                fresh ``StubBackend``).
            result_id: Optional explicit result id (a UUID is generated
                otherwise).

        Returns:
            The stored Results (``versions`` resolved by the engine).

        Raises:
            ModelVersionMismatchError: unknown model or incompatible dataset.
            CalculationInputError: hard input validation errors.
            BackendError: backend failure.
            CalculationError: runtime failure after validation.
        """
        versions = self._resolve_versions(dataset, model_release)
        report = input_.validate()
        if not report.valid:
            raise CalculationInputError(
                "invalid building input",
                {"errors": list(report.errors), "warnings": list(report.warnings)},
            )
        backend = backend or self.default_backend or StubBackend()
        capability = backend.validate(input_, dataset)
        if not capability.valid:
            raise CalculationInputError(
                f"backend {backend.name!r} rejected the input",
                {"errors": list(capability.errors)},
            )
        try:
            result = backend.calculate(input_, dataset, versions.model)
        except EnergyToolsError:
            raise
        except Exception as exc:
            raise BackendError(
                f"backend {backend.name!r} failed: {exc}", {"backend": backend.name}
            ) from exc
        # The engine resolves versions and ids; the backend's provisional
        # values are replaced so every stored result carries the resolved ones.
        result = dataclasses.replace(result, versions=versions)
        if result_id is not None:
            trace = result.trace
            if trace is not None:
                trace = dataclasses.replace(trace, result_id=result_id)
            result = dataclasses.replace(result, result_id=result_id, trace=trace)
        self.store.save(result)
        return result

    def explain(self, result_id: str) -> CalculationTrace:
        """The stored trace of a result (``GET /calculations/{id}/explain``).

        Raises:
            CalculationError: unknown result id or result without a trace.
        """
        result = self.get_result(result_id)
        if result.trace is None:
            raise CalculationError(
                f"result {result_id!r} has no trace", {"result_id": result_id}
            )
        return result.trace

    def get_result(self, result_id: str) -> Results:
        """The stored result (``GET /calculations/{result_id}``).

        Raises:
            CalculationError: unknown result id.
        """
        return self.store.get(result_id)


#: Doc-name alias (doc part 04 §4.1 calls the facade ``CalculationEngine``).
CalculationEngine: type[Engine] = Engine
