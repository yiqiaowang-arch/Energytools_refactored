"""Exception hierarchy of the calculation engine.

The target-state design places the library-wide exception hierarchy in
``energytools.common.errors`` (docs/architecture+api-reference/02-common-foundation.md
§1). This milestone implements the subset the engine needs here, with the same
names, messages and ``details`` payloads; when ``energytools.common`` lands,
this module re-exports from there instead of defining its own classes.

The hierarchy is flat by design: every subclass is raised in exactly one
layer, so callers can catch either the precise type or the base type.
"""

from __future__ import annotations

from typing import Any


class EnergyToolsError(Exception):
    """Base class of the whole library exception hierarchy.

    Carries an optional structured ``details`` payload used by the FastAPI/MCP
    layers to build error responses without string parsing.

    Args:
        message: Human-readable message (English).
        details: Structured context (offending value, release id, ...).
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details: dict[str, Any] = details or {}


class CalculationInputError(EnergyToolsError):
    """A building input (``BuildingInput``) is structurally or semantically invalid.

    Raised by ``Engine.calculate`` for hard validation errors (unknown room
    use, negative area, unknown Lüftung system, missing climate station, ...).
    ``details["errors"]`` carries the per-item validation messages.
    """


class CalculationError(EnergyToolsError):
    """A calculation fails at runtime after validation.

    Backend failure not attributable to the backend itself, numeric failure,
    missing intermediate, internal inconsistency, or unknown ``result_id``
    lookups in the store. ``details`` may carry ``{"step": ..., "system": ...}``
    context.
    """


class ModelVersionMismatchError(EnergyToolsError):
    """The versions a calculation combines are incompatible.

    Dataset release not supported by the model release, or an unknown model
    release id. ``details`` may carry ``{"dataset": ..., "model": ...,
    "compatible_dataset_releases": [...]}``.
    """


class BackendError(EnergyToolsError):
    """A calculation backend cannot produce a result.

    Base class for backend failures; ``details`` may carry
    ``{"backend": ..., "workbook": ...}``.
    """


class UnknownValueKindError(EnergyToolsError):
    """A value kind other than standard, zielwert or bestand was requested.

    Raised by ``ValueKind.parse`` (doc part 02 §1.8).
    """
