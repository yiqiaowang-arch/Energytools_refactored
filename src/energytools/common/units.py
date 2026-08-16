"""Units and quantities of the energytools library.

Units are parsed from the workbook's rich-text unit cells during extraction
(normalized from e.g. ``W/m²`` to ``W/m2``); unknown symbols raise
:class:`~energytools.common.errors.UnitError`. Conversion is supported within
the same physical dimension (:class:`Unit.convert_to`), and
:class:`Quantity` pairs a typed value with a unit for the domain model.

See docs/architecture+api-reference/02-common-foundation.md §3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from energytools.common.errors import UnitError

__all__ = ["Unit", "Quantity", "register_unit"]

#: Registry of known unit symbols: normalized symbol ->
#: (dimension, factor to SI base, offset from SI base, default SI hint).
#: ``value_si = (value + offset) * factor``.
_UNIT_REGISTRY: dict[str, tuple[str, float, float, str | None]] = {
    # dimensionless
    "-": ("dimensionless", 1.0, 0.0, None),
    "1": ("dimensionless", 1.0, 0.0, None),
    # percent (relative-humidity and share cells of the workbook)
    "%": ("percent", 1.0, 0.0, None),
    # temperature
    "K": ("temperature", 1.0, 0.0, None),
    "°C": ("temperature", 1.0, 273.15, "K"),
    # pressure
    "Pa": ("pressure", 1.0, 0.0, None),
    "hPa": ("pressure", 100.0, 0.0, "Pa"),
    "kPa": ("pressure", 1000.0, 0.0, "Pa"),
    "mbar": ("pressure", 100.0, 0.0, "Pa"),
    "bar": ("pressure", 100_000.0, 0.0, "Pa"),
    # energy
    "J": ("energy", 1.0, 0.0, None),
    "kJ": ("energy", 1000.0, 0.0, "J"),
    "MJ": ("energy", 1_000_000.0, 0.0, "J"),
    "Wh": ("energy", 3600.0, 0.0, "J"),
    "kWh": ("energy", 3_600_000.0, 0.0, "J"),
    "MWh": ("energy", 3_600_000_000.0, 0.0, "J"),
    # power
    "W": ("power", 1.0, 0.0, None),
    "kW": ("power", 1000.0, 0.0, "W"),
    "MW": ("power", 1_000_000.0, 0.0, "W"),
    # power per area
    "W/m2": ("power_per_area", 1.0, 0.0, "W·m⁻²"),
    "kW/m2": ("power_per_area", 1000.0, 0.0, "W·m⁻²"),
    "MW/m2": ("power_per_area", 1_000_000.0, 0.0, "W·m⁻²"),
    "W/cm2": ("power_per_area", 10_000.0, 0.0, "W·m⁻²"),
    # energy per area
    "Wh/m2": ("energy_per_area", 3600.0, 0.0, "J·m⁻²"),
    "kWh/m2": ("energy_per_area", 3_600_000.0, 0.0, "J·m⁻²"),
    "MWh/m2": ("energy_per_area", 3_600_000_000.0, 0.0, "J·m⁻²"),
    "J/m2": ("energy_per_area", 1.0, 0.0, None),
    "kJ/m2": ("energy_per_area", 1000.0, 0.0, "J·m⁻²"),
    "MJ/m2": ("energy_per_area", 1_000_000.0, 0.0, "J·m⁻²"),
    # area
    "m2": ("area", 1.0, 0.0, None),
    "cm2": ("area", 1e-4, 0.0, "m²"),
    "mm2": ("area", 1e-6, 0.0, "m²"),
    # length
    "m": ("length", 1.0, 0.0, None),
    "cm": ("length", 1e-2, 0.0, "m"),
    "mm": ("length", 1e-3, 0.0, "m"),
    "km": ("length", 1000.0, 0.0, "m"),
    # volume
    "m3": ("volume", 1.0, 0.0, None),
    "l": ("volume", 1e-3, 0.0, "m³"),
    "ml": ("volume", 1e-6, 0.0, "m³"),
    # volume flow
    "m3/h": ("volume_flow", 1.0, 0.0, None),
    "l/h": ("volume_flow", 1e-3, 0.0, "m³·h⁻¹"),
    "l/s": ("volume_flow", 3.6, 0.0, "m³·h⁻¹"),
    "m3/s": ("volume_flow", 3600.0, 0.0, "m³·h⁻¹"),
    # metabolic / clothing units (SIA 2024 data sheet: Aktivitätsgrad "met",
    # Wärmedämmwert "clo")
    "met": ("metabolic_equivalent", 1.0, 0.0, None),
    "clo": ("clothing_insulation", 1.0, 0.0, None),
    # mass
    "kg": ("mass", 1.0, 0.0, None),
    "g": ("mass", 1e-3, 0.0, "kg"),
    "t": ("mass", 1000.0, 0.0, "kg"),
    # mass fraction (absolute-humidity style ratios)
    "g/kg": ("mass_fraction", 1e-3, 0.0, "kg·kg⁻¹"),
    "kg/kg": ("mass_fraction", 1.0, 0.0, None),
    # time
    "s": ("time", 1.0, 0.0, None),
    "min": ("time", 60.0, 0.0, "s"),
    "h": ("time", 3600.0, 0.0, "s"),
    "d": ("time", 86_400.0, 0.0, "s"),
    "ppm": ("dimensionless", 1e-06, 0.0, None),
    "ppb": ("dimensionless", 1e-09, 0.0, None),
    "C": ("temperature", 1.0, 273.15, None),
    "ha": ("area", 10000.0, 0.0, None),
    "L": ("volume", 0.001, 0.0, None),
    "a": ("time", 31536000.0, 0.0, None),
    "Jahr": ("time", 31536000.0, 0.0, None),
    "Hz": ("frequency", 1.0, 0.0, None),
    "h-1": ("frequency", 0.0002777777777777778, 0.0, None),
    "1/h": ("frequency", 0.0002777777777777778, 0.0, None),
    "m/s": ("velocity", 1.0, 0.0, None),
    "km/h": ("velocity", 0.2777777777777778, 0.0, None),
    "kg/m3": ("density", 1.0, 0.0, None),
    "N": ("force", 1.0, 0.0, None),
    "kN": ("force", 1000.0, 0.0, None),
    "MPa": ("pressure", 1000000.0, 0.0, None),
    "GJ": ("energy", 1000000000.0, 0.0, None),
    "GWh": ("energy", 3600000000000.0, 0.0, None),
    "Wh/m2a": ("energy_per_area_time", 0.00011415525114155251, 0.0, None),
    "kWh/m2a": ("energy_per_area_time", 0.1141552511415525, 0.0, None),
    "MWh/m2a": ("energy_per_area_time", 114.15525114155251, 0.0, None),
    "kJ/m2a": ("energy_per_area_time", 3.1709791983764585e-05, 0.0, None),
    "J/kg": ("energy_per_mass", 1.0, 0.0, None),
    "kJ/kg": ("energy_per_mass", 1000.0, 0.0, None),
    "Wh/kg": ("energy_per_mass", 3600.0, 0.0, None),
    "J/kgK": ("energy_per_mass_temperature", 1.0, 0.0, None),
    "kJ/kgK": ("energy_per_mass_temperature", 1000.0, 0.0, None),
    "Wh/kgK": ("energy_per_mass_temperature", 3600.0, 0.0, None),
    "W/m3": ("power_per_volume", 1.0, 0.0, None),
    "kW/m3": ("power_per_volume", 1000.0, 0.0, None),
    "W/m2K": ("power_per_area_temperature", 1.0, 0.0, None),
    "kW/m2K": ("power_per_area_temperature", 1000.0, 0.0, None),
    "W/(m2K)": ("power_per_area_temperature", 1.0, 0.0, None),
    "W/m2xK": ("power_per_area_temperature", 1.0, 0.0, None),
    "W/(m2xK)": ("power_per_area_temperature", 1.0, 0.0, None),
    "m2K/W": ("area_temperature_per_power", 1.0, 0.0, None),
    "W/K": ("power_per_temperature", 1.0, 0.0, None),
    "kW/K": ("power_per_temperature", 1000.0, 0.0, None),
    "mg/m3": ("mass_per_volume", 1e-06, 0.0, None),
    "g/m3": ("mass_per_volume", 1e-03, 0.0, None),
    "Kd": ("degree_days", 86400.0, 0.0, None),
    "K·d": ("degree_days", 86400.0, 0.0, None),
    "°C·d": ("degree_days", 86400.0, 0.0, None),
    "°Cd": ("degree_days", 86400.0, 0.0, None),
    "lm": ("luminous_flux", 1.0, 0.0, None),
    "lx": ("illuminance", 1.0, 0.0, None),
    "V": ("voltage", 1.0, 0.0, None),
    "A": ("current", 1.0, 0.0, None),
    "dB": ("level", 1.0, 0.0, None),
    "m3/hm2": ("volumetric_flow_per_area", 0.0002777777777777778, 0.0, None),
    "l/sm2": ("volumetric_flow_per_area", 0.001, 0.0, None),
    "GJ/m2": ("energy_per_area", 1000000000.0, 0.0, None),
    "m3/m2h": ("volumetric_flow_per_area", 0.0002777777777777778, 0.0, None),
    "m3/(m2xh)": ("volumetric_flow_per_area", 0.0002777777777777778, 0.0, None),
    "g/(hm2)": ("mass_flow_per_area", 2.7777777777777776e-07, 0.0, None),
    "g/(hxm2)": ("mass_flow_per_area", 2.7777777777777776e-07, 0.0, None),
    "Wh/(m2K)": ("energy_per_area_temperature", 3600.0, 0.0, None),
    "Wh/(m2xK)": ("energy_per_area_temperature", 3600.0, 0.0, None),
    "MJ/(m2K)": ("energy_per_area_temperature", 1000000.0, 0.0, None),
    "MJ/(m2*K)": ("energy_per_area_temperature", 1000000.0, 0.0, None),
    "m2/P": ("area_per_person", 1.0, 0.0, None),
    # per-person power/energy of the per-category reference tables
    # (``Fläche-E`` "Wärmeabgabe pro Person" W/P, "Warmwasser pro Person"
    # kWh/P) and the per-person air flow of the SIA 380/1 Tab. 27 comparison
    # rows (``m3/(Ph)`` = m3 per person-hour); "1000m2" is the GEPAMOD EBF
    # column unit (energy reference area in 1000 m2, workbook cell ``EBF!C5``).
    "W/P": ("power_per_person", 1.0, 0.0, "W·P⁻¹"),
    "kWh/P": ("energy_per_person", 3_600_000.0, 0.0, "kWh·P⁻¹"),
    "m3/(Ph)": ("volume_flow_per_person", 1.0, 0.0, "m³·P⁻¹·h⁻¹"),
    "1000m2": ("area", 1000.0, 0.0, None),
    "l/d": ("volume_per_time", 1.1574074074074074e-08, 0.0, None),
    "W/(m3/h)": ("power_per_volumetric_flow", 3600.0, 0.0, None),
    "W/(m3xh)": ("power_per_volumetric_flow", 3600.0, 0.0, None),
    "m3/d": ("volumetric_flow", 1.1574074074074073e-05, 0.0, None),
    "Wh/m2d": ("energy_per_area_time", 0.041666666666666664, 0.0, None),
    "kWh/m2d": ("energy_per_area_time", 41.666666666666664, 0.0, None),
}

#: Superscript characters the workbook's rich-text cells use for exponents.
_SUPERSCRIPT_MAP = str.maketrans(
    {
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
        "⁻": "-",
    }
)


def _normalize_symbol(symbol: str) -> str:
    """Normalize a unit symbol for registry lookup.

    Strips whitespace, translates superscript digits and the Unicode minus,
    and replaces the Unicode division/other dashes with ASCII forms so that
    rich-text workbook cells (``W/m²``, ``kWh/m²``) resolve to the registry
    entries (``W/m2``, ``kWh/m2``).
    """
    return (
        symbol.strip()
        .translate(_SUPERSCRIPT_MAP)
        .replace("−", "-")
        .replace("–", "-")
        .replace("×", "x")
        .replace(" ", "")
        .replace("\u00a0", "")
    )


def register_unit(
    symbol: str,
    dimension: str,
    factor: float = 1.0,
    offset: float = 0.0,
    si_hint: str | None = None,
) -> None:
    """Register a custom unit symbol (e.g. for a private dataset package).

    The symbol is normalized before registration; units of the same dimension
    are convertible via :meth:`Unit.convert_to`.

    Args:
        symbol: The display symbol, e.g. ``"W/m2"`` or ``"kWh/m2"``.
        dimension: Physical dimension id; units sharing an id are convertible.
        factor: Multiplication factor to the SI base (relative to the dimension).
        offset: Additive offset to SI (non-zero only for temperature scales).
        si_hint: Optional SI rendering hint (e.g. ``"W·m⁻²"``).
    """
    _UNIT_REGISTRY[_normalize_symbol(symbol)] = (dimension, float(factor), float(offset), si_hint)


@dataclass(frozen=True)
class Unit:
    """A unit of measure with a display symbol, an SI hint and conversion metadata.

    Symbols are normalized on construction (e.g. ``W/m²`` becomes ``W/m2``)
    and looked up in the unit registry; unknown symbols raise
    :class:`UnitError`. Conversion is only defined within the same physical
    dimension.

    Args:
        symbol: Unit symbol, e.g. ``"W/m2"``, ``"kWh"``, ``"mbar"``, ``"%"``,
            ``"-"``.
        si_hint: Optional SI display hint, e.g. ``"W·m⁻²"``; inferred from
            the registry when omitted.
        dimension: Optional physical dimension (e.g. ``"power_per_area"``);
            inferred from the registry when omitted.

    Raises:
        UnitError: If the symbol is not in the unit registry.
    """

    symbol: str
    si_hint: str | None = None
    dimension: str | None = None
    _factor: float = field(default=1.0, init=False, repr=False)
    _offset: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        normalized = _normalize_symbol(self.symbol)
        entry = _UNIT_REGISTRY.get(normalized)
        if entry is None:
            raise UnitError(
                f"unknown unit symbol '{self.symbol}'",
                {"symbol": self.symbol},
            )
        registry_dimension, factor, offset, registry_hint = entry
        object.__setattr__(self, "symbol", normalized)
        if self.si_hint is None:
            object.__setattr__(self, "si_hint", registry_hint)
        if self.dimension is None:
            object.__setattr__(self, "dimension", registry_dimension)
        object.__setattr__(self, "_factor", factor)
        object.__setattr__(self, "_offset", offset)

    def convert_to(self, value: float, target: "Unit") -> float:
        """Convert ``value`` expressed in this unit to ``target``.

        Args:
            value: Numeric value in this unit.
            target: Target unit.

        Returns:
            The converted value.

        Raises:
            UnitError: If the dimensions differ or conversion metadata is
                missing.
        """
        if self.dimension != target.dimension:
            raise UnitError(
                f"cannot convert '{self.symbol}' ({self.dimension}) to "
                f"'{target.symbol}' ({target.dimension})",
                {"from": self.symbol, "to": target.symbol},
            )
        value_si = (value + self._offset) * self._factor
        return value_si / target._factor - target._offset

    def __str__(self) -> str:
        """Return the (normalized) unit symbol."""
        return self.symbol


@dataclass(frozen=True)
class Quantity:
    """A typed value paired with a unit.

    Used across the domain model for parameter values, results and profile
    values. Conversion-safe and format-safe; the API serializes it as
    ``{"value": ..., "unit": ...}``.

    Args:
        value: The numeric value (``None`` marks a missing value).
        unit: A :class:`Unit` or a unit symbol parsed via :class:`Unit`.

    Raises:
        UnitError: If ``unit`` is a string that is not a known unit symbol.
    """

    value: float | int | None
    unit: Unit

    def __init__(self, value: float | int | None, unit: Unit | str) -> None:
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit if isinstance(unit, Unit) else Unit(unit))

    def to(self, unit: Unit | str) -> "Quantity":
        """Return a copy of this quantity converted to ``unit``.

        Args:
            unit: Target :class:`Unit` or unit symbol.

        Returns:
            A new :class:`Quantity` with the converted value.

        Raises:
            UnitError: If the units have different dimensions or the target
                symbol is unknown.
        """
        target = unit if isinstance(unit, Unit) else Unit(unit)
        if self.value is None:
            return Quantity(None, target)
        return Quantity(self.unit.convert_to(float(self.value), target), target)

    def format(self, precision: int = 2) -> str:
        """Format the quantity as ``"<value> <unit>"``.

        A missing value (``None``) is rendered as ``"-"``. Values are rounded
        half-up on the decimal representation (``0.045`` → ``"0.05"``) so
        workbook-style tables are reproducible.

        Args:
            precision: Number of decimals for the value.

        Returns:
            The formatted string, e.g. ``"12.34 W/m2"``.
        """
        if self.value is None:
            return "-"
        try:
            rounded = Decimal(str(self.value)).quantize(
                Decimal(1).scaleb(-precision),
                rounding=ROUND_HALF_UP,
            )
        except InvalidOperation:
            # Extremely large magnitudes exceed the decimal context precision;
            # fall back to plain float formatting rather than raising.
            return f"{self.value:.{precision}f} {self.unit.symbol}"
        return f"{rounded} {self.unit.symbol}"

    def as_dict(self) -> dict[str, Any]:
        """Return the API serialization ``{"value": ..., "unit": ...}``."""
        return {"value": self.value, "unit": self.unit.symbol}
