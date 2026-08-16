"""energytools.dataset — the Raumdaten data service (deprecated alias).

.. deprecated:: 0.2.0
   Use :mod:`energytools.raumdaten` instead. This package was the first-wave
   implementation of the Raumdaten data service (docs/architecture+
   api-reference/03-raumdaten-service.md). The canonical package is now
   ``energytools.raumdaten`` with the full model (incl. hourly/monthly/weekly
   profiles, full-load-hours/Qhc/SIA 380-1 tables), the extraction pipeline
   (``DatasetExtractor``), the release-scoped ``RaumdatenService`` and the
   JSON-Schema-validated loader. This alias keeps the first-wave public
   surface importable for backward compatibility; new code must import from
   ``energytools.raumdaten``.

Example (new code):
    from energytools.raumdaten import load_dataset, RaumdatenService
"""

import warnings as _warnings

from energytools.dataset.compare import ParameterDiff, ProfileDiff, compare_profiles
from energytools.dataset.errors import (
    DatasetError,
    DatasetNotFoundError,
    DatasetValidationError,
    ExportError,
    LoadError,
    NotFoundError,
    UnitError,
    UnknownClimateStationError,
    UnknownLanguageError,
    UnknownParameterError,
    UnknownRoomUseError,
    UnknownValueKindError,
    ValidationError,
)
from energytools.dataset.loader import (
    DatasetCollection,
    SkippedFile,
    compute_package_checksum,
    load_dataset,
    load_datasets,
    parse_dataset,
)
from energytools.dataset.model import (
    ClimateStation,
    Dataset,
    Parameter,
    ParameterValue,
    RoomUse,
    RoomUseProfile,
    ValidationReport,
)

__all__ = [
    "ClimateStation",
    "Dataset",
    "DatasetCollection",
    "DatasetError",
    "DatasetNotFoundError",
    "DatasetValidationError",
    "ExportError",
    "LoadError",
    "NotFoundError",
    "Parameter",
    "ParameterDiff",
    "ParameterValue",
    "ProfileDiff",
    "RoomUse",
    "RoomUseProfile",
    "SkippedFile",
    "UnitError",
    "UnknownClimateStationError",
    "UnknownLanguageError",
    "UnknownParameterError",
    "UnknownRoomUseError",
    "UnknownValueKindError",
    "ValidationError",
    "ValidationReport",
    "compare_profiles",
    "compute_package_checksum",
    "load_dataset",
    "load_datasets",
    "parse_dataset",
]

_warnings.warn(
    "energytools.dataset is deprecated; use energytools.raumdaten instead "
    "(the canonical Raumdaten data-service package).",
    DeprecationWarning,
    stacklevel=2,
)
