"""energytools.raumdaten -- the Raumdaten data service (API reference part 03).

The canonical, versioned, machine-readable dataset (assessment 5.1): the OOP
model (``model``), loading/extraction (``dataset``), the semantic read-only
query API (``service``) and profile comparison (``compare``).  All exceptions
come from ``energytools.common.errors``.
"""

from __future__ import annotations

from energytools.raumdaten.compare import ParameterDiff, ProfileDiff, compare_profiles
from energytools.raumdaten.dataset import DatasetExtractor, DatasetStore, load_dataset
from energytools.raumdaten.model import (
    AreaTable,
    BuildingCategoryMapping,
    ClimateData,
    ClimateStation,
    Dataset,
    FullLoadHoursTable,
    HourlyProfile,
    MonthlyProfile,
    Parameter,
    ParameterValue,
    QhcTable,
    RoomUse,
    RoomUseProfile,
    Sia3801Coefficients,
    Sia3801Result,
    TemperatureBin,
    WeeklyProfile,
)
from energytools.raumdaten.service import RaumdatenService

__all__ = [
    "AreaTable",
    "BuildingCategoryMapping",
    "ClimateData",
    "ClimateStation",
    "Dataset",
    "DatasetExtractor",
    "DatasetStore",
    "FullLoadHoursTable",
    "HourlyProfile",
    "MonthlyProfile",
    "Parameter",
    "ParameterDiff",
    "ParameterValue",
    "ProfileDiff",
    "QhcTable",
    "RaumdatenService",
    "RoomUse",
    "RoomUseProfile",
    "Sia3801Coefficients",
    "Sia3801Result",
    "TemperatureBin",
    "WeeklyProfile",
    "compare_profiles",
    "load_dataset",
]
