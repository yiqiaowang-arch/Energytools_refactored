"""Tests for energytools.common.units.

Covers the unit registry and symbol normalization (``Unit``) plus the typed
value+unit pair (``Quantity``): construction, conversion within a dimension,
dimension-mismatch errors and serialization.
"""

from __future__ import annotations

import math

import pytest

from energytools.common.errors import UnitError
from energytools.common.units import Quantity, Unit

# ---------------------------------------------------------------------------
# Unit construction and registry
# ---------------------------------------------------------------------------


def test_unit_attributes_and_str() -> None:
    unit = Unit("W/m2")
    assert unit.symbol == "W/m2"
    assert unit.dimension == "power_per_area"
    assert unit.si_hint == "W·m⁻²"
    assert str(unit) == "W/m2"


def test_unit_normalizes_rich_text_symbols() -> None:
    assert Unit("W/m²").symbol == "W/m2"
    assert Unit("kWh/m²").symbol == "kWh/m2"
    assert Unit(" W/m2 ").symbol == "W/m2"
    assert Unit("m²").symbol == "m2"
    assert Unit("m³/h").symbol == "m3/h"
    assert Unit("W/m²") == Unit("W/m2")


def test_unit_accepts_workbook_symbols() -> None:
    for symbol in ("W/m2", "kWh", "mbar", "%", "-", "°C", "g/kg", "m3/h", "l"):
        assert Unit(symbol).symbol == symbol


def test_unit_unknown_symbol_raises_unit_error() -> None:
    with pytest.raises(UnitError) as exc_info:
        Unit("not-a-unit")
    assert "unknown unit symbol" in str(exc_info.value)
    assert exc_info.value.details == {"symbol": "not-a-unit"}


def test_unit_explicit_si_hint_and_dimension_override() -> None:
    unit = Unit("kW/m2", si_hint="custom hint", dimension="custom_dim")
    assert unit.si_hint == "custom hint"
    assert unit.dimension == "custom_dim"


def test_unit_without_registry_hint() -> None:
    assert Unit("kWh").si_hint == "J"
    assert Unit("-").si_hint is None


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def test_convert_within_dimension() -> None:
    w_per_m2 = Unit("W/m2")
    kw_per_m2 = Unit("kW/m2")
    assert w_per_m2.convert_to(1000.0, kw_per_m2) == 1.0
    assert kw_per_m2.convert_to(1.0, w_per_m2) == 1000.0


def test_convert_energy_example() -> None:
    assert Unit("kWh").convert_to(1.0, Unit("Wh")) == 1000.0
    assert Unit("MWh").convert_to(1.0, Unit("kWh")) == 1000.0


def test_convert_temperature_with_offset() -> None:
    assert Unit("°C").convert_to(20.0, Unit("K")) == pytest.approx(293.15)
    assert Unit("K").convert_to(293.15, Unit("°C")) == pytest.approx(20.0)


def test_convert_pressure() -> None:
    assert Unit("mbar").convert_to(1013.25, Unit("hPa")) == pytest.approx(1013.25)
    assert Unit("bar").convert_to(1.0, Unit("Pa")) == pytest.approx(100_000.0)


def test_convert_dimension_mismatch_raises() -> None:
    with pytest.raises(UnitError) as exc_info:
        Unit("kWh").convert_to(1.0, Unit("m2"))
    assert "cannot convert" in str(exc_info.value)
    assert exc_info.value.details == {"from": "kWh", "to": "m2"}


def test_convert_percent_only_within_percent() -> None:
    assert Unit("%").convert_to(50.0, Unit("%")) == 50.0
    with pytest.raises(UnitError):
        Unit("%").convert_to(50.0, Unit("-"))


# ---------------------------------------------------------------------------
# Quantity
# ---------------------------------------------------------------------------


def test_quantity_accepts_unit_and_string() -> None:
    assert Quantity(45.0, Unit("kWh/m2")).unit.symbol == "kWh/m2"
    assert Quantity(45.0, "kWh/m2").unit.symbol == "kWh/m2"


def test_quantity_invalid_unit_string_raises() -> None:
    with pytest.raises(UnitError):
        Quantity(45.0, "not-a-unit")


def test_quantity_to_converts_copy() -> None:
    q = Quantity(45.0, "kWh/m2")
    converted = q.to(Unit("MWh/m2"))
    assert isinstance(converted, Quantity)
    assert converted.value == pytest.approx(0.045)
    assert converted.unit.symbol == "MWh/m2"
    # The original quantity is untouched.
    assert q.value == 45.0
    assert q.unit.symbol == "kWh/m2"


def test_quantity_to_with_string_target() -> None:
    assert Quantity(1000.0, "W/m2").to("kW/m2").value == 1.0


def test_quantity_to_none_value_keeps_none() -> None:
    q = Quantity(None, "kWh/m2")
    converted = q.to("MWh/m2")
    assert converted.value is None
    assert converted.unit.symbol == "MWh/m2"


def test_quantity_to_dimension_mismatch_raises() -> None:
    with pytest.raises(UnitError):
        Quantity(1.0, "kWh").to("m2")


def test_quantity_format() -> None:
    assert Quantity(45.0, "kWh/m2").format() == "45.00 kWh/m2"
    assert Quantity(12.3456, "W/m2").format(4) == "12.3456 W/m2"
    assert Quantity(12.3456, "W/m2").format() == "12.35 W/m2"
    assert Quantity(None, "kWh").format() == "-"


def test_quantity_as_dict() -> None:
    assert Quantity(45.0, "kWh/m2").as_dict() == {"value": 45.0, "unit": "kWh/m2"}
    assert Quantity(None, "kWh").as_dict() == {"value": None, "unit": "kWh"}


def test_quantity_frozen() -> None:
    q = Quantity(1.0, "kWh")
    with pytest.raises(AttributeError):
        q.value = 2.0  # type: ignore[misc]


def test_documented_examples() -> None:
    w_per_m2 = Unit("W/m2")
    kw_per_m2 = Unit("kW/m2")
    assert w_per_m2.convert_to(1000.0, kw_per_m2) == 1.0
    with pytest.raises(UnitError):
        Unit("not-a-unit")

    q = Quantity(45.0, "kWh/m2")
    assert q.to(Unit("MWh/m2")).format() == "0.05 MWh/m2"
    assert q.as_dict() == {"value": 45.0, "unit": "kWh/m2"}


def test_quantity_to_with_none_value_and_float_value_types() -> None:
    assert math.isclose(Quantity(2, "kWh").to("Wh").value or 0.0, 2000.0)


def test_quantity_format_extreme_magnitude_falls_back() -> None:
    # Values whose decimal representation exceeds the context precision must
    # still format without raising.
    formatted = Quantity(1e30, "kWh").format()
    assert formatted.endswith(" kWh")
