"""Exception hierarchy of the ``energytools.dataset`` data service.

Every exception derives — directly or transitively — from
:class:`energytools.common.errors.EnergyToolsError`, the library-wide root
(docs/architecture+api-reference/02-common-foundation.md §1), so callers can
catch either the precise type or the base type.

The release- and lookup-level errors the service raises
(``DatasetNotFoundError``, ``UnknownRoomUseError``, ...) are already defined in
:mod:`energytools.common.errors` and are re-exported here unchanged, so that
``from energytools.dataset.errors import ...`` covers the whole layer. This
module additionally defines the dataset-layer base class
(:class:`DatasetError`) and the file-level errors of the loader
(:class:`NotFoundError`, :class:`LoadError`, :class:`ValidationError`).
:class:`ValidationError` is also a :class:`DatasetValidationError`, matching
the documented contract that ``load_dataset`` raises a validation error for a
corrupt/foreign package (docs/architecture+api-reference/03-raumdaten-service.md
§2.1); :class:`NotFoundError` is also a :class:`DatasetNotFoundError`.
"""

from __future__ import annotations

from typing import Any

from energytools.common.errors import (
    DatasetNotFoundError,
    DatasetValidationError,
    EnergyToolsError,
    ExportError,
    UnitError,
    UnknownClimateStationError,
    UnknownLanguageError,
    UnknownParameterError,
    UnknownRoomUseError,
    UnknownValueKindError,
)

__all__ = [
    "DatasetError",
    "DatasetNotFoundError",
    "DatasetValidationError",
    "EnergyToolsError",
    "ExportError",
    "LoadError",
    "NotFoundError",
    "UnitError",
    "UnknownClimateStationError",
    "UnknownLanguageError",
    "UnknownParameterError",
    "UnknownRoomUseError",
    "UnknownValueKindError",
    "ValidationError",
]


class DatasetError(EnergyToolsError):
    """Base class of the ``energytools.dataset`` layer.

    Subclasses :class:`~energytools.common.errors.EnergyToolsError` — the
    library-wide exception root — which hooks the dataset hierarchy into the
    common exception tree. Raised directly only for layer-level failures that
    no more specific class covers.

    Args:
        message: Human-readable error message (English).
        details: Optional structured context, e.g. ``{"path": ..., "errors": [...]}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class NotFoundError(DatasetError, DatasetNotFoundError):
    """A dataset file or directory does not exist on disk.

    Raised by :func:`energytools.dataset.loader.load_dataset` when the given
    path is missing. Also an :class:`DatasetNotFoundError` so release-level
    callers can catch either type.

    Args:
        name: The offending path or resource name.
        details: Optional structured context.
    """

    def __init__(self, name: str, details: dict[str, Any] | None = None) -> None:
        DatasetError.__init__(self, f"Dataset '{name}' not found", details)


class LoadError(DatasetError):
    """A dataset file could not be read from disk.

    Covers I/O failures that are not "file missing" (permission errors,
    unreadable content). Content problems (invalid JSON, missing fields,
    unknown value kinds) are reported as :class:`ValidationError` instead.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g. ``{"path": ...}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class ValidationError(DatasetError, DatasetValidationError):
    """A dataset package fails structural validation.

    Raised by :func:`energytools.dataset.loader.load_dataset` for a single
    explicit file — a corrupt/foreign package is never half-loaded
    (docs/architecture+api-reference/03-raumdaten-service.md §2.1). Also a
    :class:`DatasetValidationError`; the recommended ``details`` payload is
    ``{"errors": [...]}`` with one message per failing item.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g. ``{"errors": [...], "path": ...}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        DatasetError.__init__(self, message, details)
