"""energytools.engine.native — pure-Python (native) port of the workbook model.

The native backend runtime of the calculation engine (doc part 04 §5.3): pure
Python implementations of the workbook formulas, verified against the Excel
oracle. Currently ships the psychrometric port of ``FeuchteLuft_Formeln.bas``
(:mod:`energytools.engine.native.psychrometrics`); the AHU temperature-bin
engine (``Berechnung LU``) arrives in a later milestone.

Example:
    from energytools.engine.native.psychrometrics import absolute_humidity

    x = absolute_humidity(20.0, 0.5, 1013.0)   # ≈ 7.28 g/kg
"""

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
    "absolute_humidity",
    "dew_point",
    "dew_point_from_absolute_humidity",
    "enthalpy_from_absolute_humidity",
    "enthalpy_from_rel_humidity",
    "relative_humidity",
    "saturation_pressure_glueck",
    "temperature_from_enthalpy",
    "wet_bulb_temperature",
]
