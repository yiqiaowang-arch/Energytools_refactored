"""energytools.engine.native — pure-Python (native) port of the workbook model.

The native backend runtime of the calculation engine (doc part 04 §5.3): pure
Python implementations of the workbook formulas, verified against the Excel
oracle. Ships the psychrometric port of ``FeuchteLuft_Formeln.bas``
(:mod:`energytools.engine.native.psychrometrics`), the AHU temperature-bin
engine of the sheet ``Berechnung LU`` (:mod:`energytools.engine.native.ahu`)
and the building aggregation / ``Resultate`` summary
(:mod:`energytools.engine.native.aggregation`).

Example:
    from energytools.engine.native.ahu import AhuInput, compute_ahu_annual

    result = compute_ahu_annual(AhuInput())
"""

from energytools.engine.native.aggregation import (
    DEFAULT_WEIGHTS,
    NUTZUNGSGRAD_CATALOG,
    RES_SELECTORS,
    RESULTATE_CARRIERS,
    AggregationInput,
    AggregationResult,
    DatasetResLookup,
    GenerationCatalog,
    GenerationGroupInput,
    GenerationGroupResult,
    GenerationInput,
    GeneratorResult,
    GeneratorSpec,
    KpiLookup,
    KpiLookupError,
    NutzungsgradCatalog,
    ResMatrixKpiProvider,
    RoomResult,
    RoomTotals,
    VentilationSystemResult,
    VentilationTotals,
    WeightTable,
    aggregate,
    compute_room_row,
    res_column,
)
from energytools.engine.native.ahu import (
    AhuAnnualResult,
    AhuBinResult,
    AhuInput,
    FanModelResult,
    compute_ahu_annual,
    compute_ahu_bins,
    compute_bin_hours,
    compute_fan_model,
)
from energytools.engine.native.backend import NativeBackend
from energytools.engine.native.psychrometrics import (
    absolute_humidity,
    dew_point,
    dew_point_from_absolute_humidity,
    enthalpy_from_absolute_humidity,
    enthalpy_from_rel_humidity,
    relative_humidity,
    saturation_pressure_glueck,
    temperature_from_enthalpy,
    wet_bulb_temperature,
)

__all__ = [
    "DEFAULT_WEIGHTS",
    "NUTZUNGSGRAD_CATALOG",
    "RESULTATE_CARRIERS",
    "RES_SELECTORS",
    "AggregationInput",
    "AggregationResult",
    "AhuAnnualResult",
    "AhuBinResult",
    "AhuInput",
    "DatasetResLookup",
    "FanModelResult",
    "GenerationCatalog",
    "GenerationGroupInput",
    "GenerationGroupResult",
    "GenerationInput",
    "GeneratorResult",
    "GeneratorSpec",
    "KpiLookup",
    "KpiLookupError",
    "NativeBackend",
    "NutzungsgradCatalog",
    "ResMatrixKpiProvider",
    "RoomResult",
    "RoomTotals",
    "VentilationSystemResult",
    "VentilationTotals",
    "WeightTable",
    "absolute_humidity",
    "aggregate",
    "compute_ahu_annual",
    "compute_ahu_bins",
    "compute_bin_hours",
    "compute_fan_model",
    "compute_room_row",
    "dew_point",
    "dew_point_from_absolute_humidity",
    "enthalpy_from_absolute_humidity",
    "enthalpy_from_rel_humidity",
    "relative_humidity",
    "res_column",
    "saturation_pressure_glueck",
    "temperature_from_enthalpy",
    "wet_bulb_temperature",
]
