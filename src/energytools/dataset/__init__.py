"""energytools.dataset — the Raumdaten data service.

The canonical, versioned, machine-readable Raumdaten dataset
(docs/architecture+api-reference/03-raumdaten-service.md, there named
``energytools.raumdaten``) as a data service package: immutable data models
(:mod:`energytools.dataset.model`), loading from JSON packages with single-file
and directory discovery (:mod:`energytools.dataset.loader`), profile comparison
(:mod:`energytools.dataset.compare`), validation and JSON/CSV export.

The three value kinds keep their German workbook names (Standard, Zielwert,
Bestand); labels are trilingual (DE/FR/IT) via
:class:`~energytools.common.language.TrilingualText`.

Example:
    from energytools.dataset import load_dataset

    ds = load_dataset("tests/fixtures/dataset_sample/V221.json")
    ds.list_room_uses()                      # RoomUse objects in sheet order
    profile = ds.get_room_use_profile("1.01")
    diff = ds.compare_room_use_profiles(1, 3)
"""

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
