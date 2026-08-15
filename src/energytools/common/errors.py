"""Exception hierarchy of the energytools library.

Every exception derives from :class:`EnergyToolsError`. The hierarchy is flat
by design: each subclass is raised in exactly one layer, so callers can catch
either the precise type or the base type. All messages are human-readable
English; structured context travels in the ``details`` payload, which the
FastAPI and MCP layers use to build error responses without string parsing.

Workbook terms (e.g. ``Raumdaten``, ``Zielwert``, ``Bestand``) appear in this
module only where they are part of the documented domain vocabulary of the
source workbooks (see docs/architecture+api-reference/02-common-foundation.md
§1).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "EnergyToolsError",
    "DatasetNotFoundError",
    "DatasetValidationError",
    "UnknownRoomUseError",
    "UnknownParameterError",
    "UnknownClimateStationError",
    "UnknownLanguageError",
    "UnknownValueKindError",
    "CalculationInputError",
    "CalculationError",
    "ModelVersionMismatchError",
    "BackendError",
    "ExcelBackendError",
    "ExportError",
    "UnitError",
    "PsychrometricError",
]


class EnergyToolsError(Exception):
    """Base class of the whole library exception hierarchy.

    Carries an optional ``details`` payload (a plain dict) for structured
    error reporting. ``str(e)`` returns the human-readable message and
    ``e.details`` the structured context.

    Args:
        message: Human-readable error message (English).
        details: Optional structured context (offending value, symbol id,
            release id, ...). Defaults to ``None``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class DatasetNotFoundError(EnergyToolsError):
    """Raised when a requested dataset release does not exist in the store.

    Covers unknown ``release_id`` values and uninstalled releases. Raised by
    ``DatasetStore.get``, ``RaumdatenService`` methods and the dataset
    endpoints.

    Args:
        release_id: The release id as passed by the caller.
        details: Optional structured context.
    """

    def __init__(self, release_id: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"Dataset release '{release_id}' not found", details)


class DatasetValidationError(EnergyToolsError):
    """Raised when a dataset or an input payload fails validation.

    Covers JSON Schema validation of the package, domain value rules (such as
    the ``12.1`` vs ``12.10`` code sanity check, percentage ranges, missing
    required columns). The recommended ``details`` payload is
    ``{"errors": [...]}`` with one message per failing item or path.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g. ``{"errors": [...]}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class UnknownRoomUseError(EnergyToolsError):
    """Raised when a room-use identifier is not part of the release.

    The identifier may be the numeric ``nutzid`` (1-45) or an SIA code such as
    ``"1.01"``.

    Args:
        room_use_id: The offending room-use identifier.
        release_id: The release that was queried.
        details: Optional structured context.
    """

    def __init__(
        self, room_use_id: str | int, release_id: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(f"Room use '{room_use_id}' not found in release '{release_id}'", details)


class UnknownParameterError(EnergyToolsError):
    """Raised when a parameter id is not part of the parameter catalog.

    Parameter ids are SIA clause ids (e.g. ``"1.1.2.7"``) or documented slugs.

    Args:
        parameter_id: The offending parameter id.
        release_id: The release that was queried.
        details: Optional structured context.
    """

    def __init__(
        self, parameter_id: str, release_id: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(f"Parameter '{parameter_id}' not found in release '{release_id}'", details)


class UnknownClimateStationError(EnergyToolsError):
    """Raised when a climate-station id (1-40) is not present in the release.

    Args:
        station_id: The offending station id.
        release_id: The release that was queried.
        details: Optional structured context.
    """

    def __init__(
        self, station_id: int | str, release_id: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            f"Climate station '{station_id}' not found in release '{release_id}'", details
        )


class UnknownLanguageError(EnergyToolsError):
    """Raised when a language other than ``de``, ``fr`` or ``it`` is requested.

    Args:
        language: The offending language value.
        details: Optional structured context.
    """

    def __init__(self, language: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"Unknown language '{language}' (expected de, fr or it)", details)


class UnknownValueKindError(EnergyToolsError):
    """Raised when a value kind other than ``standard``, ``zielwert`` or ``bestand`` is requested.

    ``zielwert`` and ``bestand`` are the workbook's German value-kind terms and
    are part of the documented API vocabulary.

    Args:
        value_kind: The offending value-kind value.
        details: Optional structured context.
    """

    def __init__(self, value_kind: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            f"Unknown value kind '{value_kind}' (expected standard, zielwert or bestand)",
            details,
        )


class CalculationInputError(EnergyToolsError):
    """Raised when a building input is structurally or semantically invalid.

    Covers unknown room uses, negative areas, systems referencing a
    nonexistent catalog code, missing climate stations and version mismatches
    between the requested dataset and the model. The recommended ``details``
    payload is ``{"errors": [...]}``.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g. ``{"errors": [...]}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class CalculationError(EnergyToolsError):
    """Raised when a calculation fails at runtime after validation.

    Covers backend failures not attributable to Excel, numeric failures,
    missing intermediates and internal inconsistencies.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g. ``{"step": ..., "system": ...}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class ModelVersionMismatchError(EnergyToolsError):
    """Raised when the versions a calculation combines are incompatible.

    Covers dataset releases not supported by the model release, climate
    versions newer or older than the model expects, and native backend
    versions that cannot reproduce the model release.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g.
            ``{"dataset": ..., "model": ..., "climate": ...}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class BackendError(EnergyToolsError):
    """Base class for calculation-backend failures.

    Raised directly when a backend cannot produce a result for reasons other
    than Excel COM (workbook copy missing, recalculation timeout, an
    unclassified native-backend runtime error).

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g.
            ``{"backend": ..., "workbook": ...}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class ExcelBackendError(BackendError):
    """Excel-COM-specific backend failure.

    Covers Excel not being installed, COM automation denied, unexpected
    workbook-copy protection, non-deterministic recalculation and cached-value
    mismatches. Raised by the ``ExcelBackend`` only.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g.
            ``{"workbook": path, "cell": address}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class ExportError(EnergyToolsError):
    """Raised when an export fails.

    Covers unsupported formats, unwritable targets, missing data for the
    requested scope and PDF rendering failures.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g.
            ``{"format": ..., "target": ...}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class UnitError(EnergyToolsError):
    """Raised for invalid units, unknown unit symbols or impossible conversions.

    For example converting ``kWh`` to ``m2`` (different physical dimensions).

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g. ``{"from": ..., "to": ...}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)


class PsychrometricError(EnergyToolsError):
    """Raised by psychrometric functions on out-of-domain inputs.

    Covers relative humidity outside 0-100 %, negative absolute humidity and
    pressures <= 0. These are the cases in which the workbook's VBA code
    returned the string ``"Fehler"``.

    Args:
        message: Human-readable error message.
        details: Optional structured context, e.g.
            ``{"function": ..., "args": {...}}``.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, details)
