"""energytools.raumdaten.model -- canonical Raumdaten dataset model (API reference part 03, section 1).

The canonical, versioned, machine-readable dataset (assessment 5.1) as an OOP
model: every table of the canonical package plus the release metadata.  German
source terms (``nutzid``, ``Datenblatt``, ``Raumklima``, ``Volll_Lüft``, ...)
are preserved as documented in the workbook assessment.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from energytools.common.errors import (
    TableLookupError,
    UnknownClimateStationError,
    UnknownParameterError,
    UnknownRoomUseError,
)
from energytools.common.language import TrilingualText
from energytools.common.provenance import Provenance
from energytools.common.units import Quantity, Unit
from energytools.common.validation import ValidationReport
from energytools.common.valuekind import ValueKind
from energytools.common.versioning import DatasetRelease
from energytools.raumdaten._generated import ParameterProperties
from energytools.raumdaten.accessors import (
    ParameterAccessor,
    ParameterCatalog,
    RoomUseCatalog,
    parameter_slug,
)

__all__ = [
    "AreaTable",
    "BuildingCategoryMapping",
    "CategoryTable",
    "ClimateData",
    "ClimateStation",
    "Dataset",
    "FullLoadHoursTable",
    "HourlyProfile",
    "MonthlyProfile",
    "Parameter",
    "ParameterValue",
    "QhcTable",
    "RoomUse",
    "RoomUseProfile",
    "Sia3801Coefficients",
    "Sia3801Result",
    "TemperatureBin",
    "WeeklyProfile",
]

_DATA_TYPES = ("number", "enum", "text", "bool")
_SIA3801_VARIANTS = ("de", "en", "de+qc", "en+qc")
_HOURLY_PROFILE_TYPES = ("person", "device", "lighting", "ventilation")
_CODE_RE = re.compile(r"^\d{1,2}\.\d{2}$")
_CODE_QUIRK_RE = re.compile(r"^(\d+)\.(\d)$")

# The workbook contains the code "12.1" instead of "12.10" for nutzid 45
# (Wasch- und Trockenraum) -- assessment 1.2, quality quirk 12.1.  Loaders and
# the extractor normalize it; single-digit fractions are zero-padded.
CODE_QUIRK_NORMALIZED = "12.10"


def normalize_room_use_code(code: str) -> str:
    """Normalize a SIA room-use code (``"12.1"`` -> ``"12.10"``, quality quirk 12.1)."""
    match = _CODE_QUIRK_RE.match(code.strip())
    if match:
        return f"{match.group(1)}.{match.group(2)}0"
    return code.strip()


# ---------------------------------------------------------------------------
# JSON (de)serialization helpers
# ---------------------------------------------------------------------------


def _text_dict(text: TrilingualText | None) -> dict[str, str] | None:
    return None if text is None else text.as_dict()


def _provenance_dict(provenance: Provenance | None) -> dict | None:
    return None if provenance is None else provenance.as_dict()


def _quantity_dict(quantity: Quantity | None) -> dict | None:
    return None if quantity is None else quantity.as_dict()


# ---------------------------------------------------------------------------
# Support value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemperatureBin:
    """One temperature bin (bin edges + hours), from ``Klimadaten`` "Anzahl Stunden Tac".

    Args:
        lower: Lower bin edge in degrees Celsius.
        upper: Upper bin edge in degrees Celsius.
        hours: Annual hours the outdoor temperature falls into this bin.

    Raises:
        ValueError: if ``lower > upper`` or ``hours`` is negative.
    """

    lower: float
    upper: float
    hours: float

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError(f"temperature bin lower edge {self.lower} > upper edge {self.upper}")
        if self.hours < 0:
            raise ValueError(f"temperature bin hours must be >= 0, got {self.hours}")

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {"lower": self.lower, "upper": self.upper, "hours": self.hours}


# ---------------------------------------------------------------------------
# Core value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoomUse:
    """One of the 45 standard room uses (assessment 1.2: ``Eingabedaten`` rows 9-53).

    Carries the numeric ``nutzid`` (1-45, the workbook's selector value for
    ``Datenblatt!C1``), the SIA code (e.g. ``"1.01"``), the category
    (1 Wohnen ... 12 Nebenräume) and trilingual names.

    Raises:
        ValueError: if ``nutzid`` is outside 1-45, ``code`` is empty, or
            ``category`` is outside 1-12.
    """

    nutzid: int
    code: str
    category: int
    name: TrilingualText
    sia_clause: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.nutzid, int) or not 1 <= self.nutzid <= 45:
            raise ValueError(f"nutzid must be an int in 1..45, got {self.nutzid!r}")
        if not self.code or not isinstance(self.code, str):
            raise ValueError(f"room use code must be a non-empty string, got {self.code!r}")
        if not isinstance(self.category, int) or not 1 <= self.category <= 12:
            raise ValueError(f"category must be an int in 1..12, got {self.category!r}")

    def as_dict(self) -> dict:
        """JSON-ready dict ``{nutzid, code, category, name, sia_clause}``."""
        return {
            "nutzid": self.nutzid,
            "code": self.code,
            "category": self.category,
            "name": _text_dict(self.name),
            "sia_clause": self.sia_clause,
        }


@dataclass(frozen=True)
class Parameter:
    """One of the 193 data-sheet parameters (assessment 1.2, ``Datenblatt`` rows 4-196).

    The stable id is the SIA clause number (e.g. ``"1.1.2.7"``
    Jahresgleichzeitigkeit) or a documented slug; carries trilingual label,
    symbol, unit, data type, category, applicable value kinds and the observed
    P/Q/R/S export/display flags.

    Raises:
        ValueError: on an empty ``id`` or an unknown ``data_type``.
    """

    id: str
    label: TrilingualText
    symbol: str
    unit: Unit
    data_type: str
    category: str
    value_kinds: frozenset[ValueKind]
    export_flag: bool = True
    display_flag: bool = True
    internal_heat_flag: bool = False
    qhc_flag: bool = False
    provenance: Provenance | None = None

    def __init__(
        self,
        id: str,
        label: TrilingualText,
        symbol: str,
        unit: Unit | str,
        data_type: str,
        category: str,
        value_kinds: frozenset[ValueKind],
        export_flag: bool = True,
        display_flag: bool = True,
        internal_heat_flag: bool = False,
        qhc_flag: bool = False,
        provenance: Provenance | None = None,
    ) -> None:
        """See the class docstring; ``unit`` accepts a symbol string (parsed via :class:`Unit`)."""
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "unit", unit if isinstance(unit, Unit) else Unit(unit))
        object.__setattr__(self, "data_type", data_type)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "value_kinds", frozenset(value_kinds))
        object.__setattr__(self, "export_flag", export_flag)
        object.__setattr__(self, "display_flag", display_flag)
        object.__setattr__(self, "internal_heat_flag", internal_heat_flag)
        object.__setattr__(self, "qhc_flag", qhc_flag)
        object.__setattr__(self, "provenance", provenance)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("parameter id must not be empty")
        if self.data_type not in _DATA_TYPES:
            raise ValueError(
                f"unknown data_type '{self.data_type}' (expected one of {', '.join(_DATA_TYPES)})"
            )

    def as_dict(self) -> dict:
        """JSON-ready parameter dict (all fields)."""
        return {
            "id": self.id,
            "label": _text_dict(self.label),
            "symbol": self.symbol,
            "unit": self.unit.symbol,
            "data_type": self.data_type,
            "category": self.category,
            "value_kinds": sorted(kind.value for kind in self.value_kinds),
            "export_flag": self.export_flag,
            "display_flag": self.display_flag,
            "internal_heat_flag": self.internal_heat_flag,
            "qhc_flag": self.qhc_flag,
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class ParameterValue:
    """One value of one parameter in one value kind, with unit and provenance.

    Replaces the workbook's raw cell triple (columns M/N/O of ``Datenblatt``)
    by a typed object.  ``UnknownParameterError`` is not raised here (no catalog
    access); ``UnitError`` on an invalid unit string.

    Attributes:
        quantity: property -> :class:`Quantity` ``(value, unit)``.
    """

    parameter_id: str
    kind: ValueKind
    value: float | int | str | bool | None
    unit: Unit
    provenance: Provenance | None = None

    def __init__(
        self,
        parameter_id: str,
        kind: ValueKind | str,
        value: float | str | bool | None,
        unit: Unit | str,
        provenance: Provenance | None = None,
    ) -> None:
        """See the class docstring; ``kind``/``unit`` accept string forms (parsed)."""
        object.__setattr__(self, "parameter_id", parameter_id)
        object.__setattr__(
            self, "kind", kind if isinstance(kind, ValueKind) else ValueKind.parse(kind)
        )
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "unit", unit if isinstance(unit, Unit) else Unit(unit))
        object.__setattr__(self, "provenance", provenance)

    @property
    def quantity(self) -> Quantity:
        """This value as a typed :class:`Quantity` (``None`` for non-numeric values)."""
        value = self.value if isinstance(self.value, (int, float)) else None
        return Quantity(value, self.unit)

    def as_dict(self) -> dict:
        """JSON-ready dict ``{value, unit, provenance}``."""
        return {
            "value": self.value,
            "unit": self.unit.symbol,
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass
class RoomUseProfile(ParameterProperties):
    """The full parameter-value set of one room use, for all value kinds.

    The digital equivalent of the rendered ``Datenblatt`` sheet for ``nutzid``.
    Immutable after construction by convention; built by :class:`Dataset`.

    Supports attribute access to parameter values::

        profile.personnel_area.standard.value   # 14 m2 for 3.01
        profile.Uw.zielwert.value               # window U-value, Zielwert

    Args:
        room_use: The room use this profile belongs to.
        values: Parameter id -> value kind -> value.
        parameter_catalog: The release parameter catalog (sheet order).
        release_id: Optional release id used in lookup error messages.

    Raises:
        ValueError: on an inconsistent catalog (unknown parameter ids).
    """

    room_use: RoomUse
    values: Mapping[str, Mapping[ValueKind, ParameterValue]]
    parameter_catalog: Mapping[str, Parameter]
    release_id: str = ""

    def __post_init__(self) -> None:
        for parameter_id in self.values:
            if parameter_id not in self.parameter_catalog:
                raise ValueError(
                    f"profile of room use {self.room_use.nutzid} references unknown parameter "
                    f"'{parameter_id}'"
                )

    def _parameter_by_slug(self, slug: str) -> ParameterAccessor:
        """Resolve a generated parameter property to its value accessor."""
        parameter = self.parameter_catalog.get(slug)
        if parameter is None:
            # slug may be an alias or a symbol-derived slug; build the map lazily.
            by_slug = {
                parameter_slug(p.id, p.symbol, p.label.de if p.label else ""): p
                for p in self.parameter_catalog.values()
            }
            parameter = by_slug.get(slug)
        if parameter is None:
            raise AttributeError(f"no parameter named {slug!r} in this profile")
        values = self.values.get(parameter.id, {})
        label = parameter.label.de if parameter.label else parameter.id
        return ParameterAccessor(parameter.id, values, label)

    def value(self, parameter_id: str, kind: ValueKind = ValueKind.STANDARD) -> ParameterValue:
        """Look up one value.

        Raises:
            UnknownParameterError: for an unknown ``parameter_id``.
            UnknownValueKindError: for an invalid ``kind``.
        """
        parameter = self.parameter_catalog.get(parameter_id)
        if parameter is None:
            raise UnknownParameterError(parameter_id, self.release_id)
        kind = kind if isinstance(kind, ValueKind) else ValueKind.parse(kind)
        value = self.values.get(parameter_id, {}).get(kind)
        if value is None:
            # KeyError-free: a kind that is not applicable (or not stored) yields
            # a value object with value=None instead of an exception.
            return ParameterValue(parameter_id, kind, None, parameter.unit)
        return value

    def parameters(self) -> list[Parameter]:
        """Catalog entries in sheet order."""
        return list(self.parameter_catalog.values())

    def to_frame(self, kind: ValueKind = ValueKind.STANDARD) -> Any:
        """Rows = parameters (id, label, symbol, unit, value) for one kind.

        Requires ``pandas`` (the ``data`` extra).
        """
        # Lazily imported: pandas is part of the 'data' extra.
        import pandas as pd  # type: ignore[import-untyped]

        kind = kind if isinstance(kind, ValueKind) else ValueKind.parse(kind)
        rows = [
            {
                "id": parameter.id,
                "label": parameter.label.de,
                "symbol": parameter.symbol,
                "unit": parameter.unit.symbol,
                "value": self.value(parameter.id, kind).value,
            }
            for parameter in self.parameters()
        ]
        return pd.DataFrame(rows, columns=["id", "label", "symbol", "unit", "value"])

    def as_dict(self, kind: ValueKind | None = None) -> dict:
        """JSON-ready dict; ``kind=None`` includes all value kinds.

        Shape: ``{room_use: ..., parameters: [{id, label, symbol, unit,
        category, values: {standard: {value, unit, provenance}, ...}}]}``.
        """
        if kind is not None and not isinstance(kind, ValueKind):
            kind = ValueKind.parse(kind)
        parameters = []
        for parameter in self.parameters():
            entry: dict[str, Any] = {
                "id": parameter.id,
                "label": parameter.label.de,
                "symbol": parameter.symbol,
                "unit": parameter.unit.symbol,
                "category": parameter.category,
            }
            kinds = (
                [kind]
                if kind is not None
                else sorted(
                    (k for k in ValueKind if k in parameter.value_kinds), key=lambda k: k.value
                )
            )
            values = {}
            for value_kind in kinds:
                value = self.values.get(parameter.id, {}).get(value_kind)
                if value is not None:
                    values[value_kind.value] = value.as_dict()
            entry["values"] = values
            parameters.append(entry)
        return {"room_use": self.room_use.as_dict(), "parameters": parameters}


@dataclass(frozen=True)
class HourlyProfile:
    """One 24 h profile (person / device / lighting / ventilation loads).

    The observed ``Profile`` sheet rows 58-86 (assessment 1.2).  Hour index 0-23.

    Raises:
        ValueError: if ``len(values) != 24`` or ``profile_type`` is unknown.
    """

    id: str
    profile_type: str
    values: tuple[float, ...]
    unit: Unit
    provenance: Provenance | None = None

    def __init__(
        self,
        id: str,
        profile_type: str,
        values: tuple[float, ...],
        unit: Unit | str = "%",
        provenance: Provenance | None = None,
    ) -> None:
        """See the class docstring; ``unit`` accepts a symbol string (parsed via :class:`Unit`)."""
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "profile_type", profile_type)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "unit", unit if isinstance(unit, Unit) else Unit(unit))
        object.__setattr__(self, "provenance", provenance)
        self.__post_init__()

    def __post_init__(self) -> None:
        if self.profile_type not in _HOURLY_PROFILE_TYPES:
            raise ValueError(
                f"unknown profile_type '{self.profile_type}' "
                f"(expected one of {', '.join(_HOURLY_PROFILE_TYPES)})"
            )
        if len(self.values) != 24:
            raise ValueError(
                f"hourly profile '{self.id}' must have 24 values, got {len(self.values)}"
            )

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "id": self.id,
            "profile_type": self.profile_type,
            "values": list(self.values),
            "unit": self.unit.symbol,
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class MonthlyProfile:
    """Twelve monthly values (climate or load), as in ``Monatswerte`` rows.

    Raises:
        ValueError: if ``len(values) != 12``.
    """

    id: str
    values: tuple[float, ...]
    unit: Unit
    provenance: Provenance | None = None

    def __init__(
        self,
        id: str,
        values: tuple[float, ...],
        unit: Unit | str,
        provenance: Provenance | None = None,
    ) -> None:
        """See the class docstring; ``unit`` accepts a symbol string (parsed via :class:`Unit`)."""
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "unit", unit if isinstance(unit, Unit) else Unit(unit))
        object.__setattr__(self, "provenance", provenance)
        self.__post_init__()

    def __post_init__(self) -> None:
        if len(self.values) != 12:
            raise ValueError(
                f"monthly profile '{self.id}' must have 12 values, got {len(self.values)}"
            )

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "id": self.id,
            "values": list(self.values),
            "unit": self.unit.symbol,
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class WeeklyProfile:
    """Seven-day weekly profile (observed ``Eingabedaten`` weekly profile section).

    Raises:
        ValueError: if ``len(values) != 7``.
    """

    id: str
    values: tuple[float, ...]
    unit: Unit
    provenance: Provenance | None = None

    def __init__(
        self,
        id: str,
        values: tuple[float, ...],
        unit: Unit | str = "%",
        provenance: Provenance | None = None,
    ) -> None:
        """See the class docstring; ``unit`` accepts a symbol string (parsed via :class:`Unit`)."""
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "unit", unit if isinstance(unit, Unit) else Unit(unit))
        object.__setattr__(self, "provenance", provenance)
        self.__post_init__()

    def __post_init__(self) -> None:
        if len(self.values) != 7:
            raise ValueError(
                f"weekly profile '{self.id}' must have 7 values, got {len(self.values)}"
            )

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "id": self.id,
            "values": list(self.values),
            "unit": self.unit.symbol,
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class RoomUseSchedule:
    """Per-room-use time schedules from the ``Eingabedaten`` matrix (rows 9-53).

    One entry per room use (nutzid).  The workbook stores the daily person
    fraction (``Personenprofil (Nutzungstag)``, ``Eingabedaten!DP9:EM53``),
    the daily device fraction (``Geräteprofil (Nutzungstag)``,
    ``Eingabedaten!EN9:FK53``), the weekly fraction (``Wochenprofil``,
    ``Eingabedaten!HS9:HY53``, day 1 = Saturday), and two monthly variants
    (``Jahresprofil`` ``FM9:FX53`` and ``Monatsprofil (bisher)``
    ``HC9:HN53``, 12 months each).  Empty matrix cells mean zero occupation
    (the workbook leaves them blank).

    ``rest_days_per_week`` is the literal ``Ruhetage pro Woche`` column
    (``FY9:FY53``); ``working_days_per_year`` and ``annual_simultaneity`` are
    derived from the workbook formulas (``Nutzungstage pro Jahr`` =
    ``365 - 52 * rest_days`` and ``Jahresgleichzeitigkeit (berechnet)`` =
    mean of the 12 ``Monatsprofil (bisher)`` values), so packages carry them
    without depending on the workbook's cached formula results.

    Raises:
        ValueError: on wrong profile lengths or a negative fraction.
    """

    room_use_id: int
    person_fraction: tuple[float, ...]  # 24 h, 0..1
    device_fraction: tuple[float, ...]  # 24 h, 0..1
    weekly_fraction: tuple[float, ...]  # 7 days, day 1 = Saturday
    monthly_fraction: tuple[float, ...]  # 12 months (Jahresprofil)
    monthly_previous_fraction: tuple[float, ...]  # 12 months (Monatsprofil bisher)
    rest_days_per_week: float
    working_days_per_year: float | None = None
    annual_simultaneity: float | None = None
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        for name, values, expected in (
            ("person_fraction", self.person_fraction, 24),
            ("device_fraction", self.device_fraction, 24),
            ("weekly_fraction", self.weekly_fraction, 7),
            ("monthly_fraction", self.monthly_fraction, 12),
            ("monthly_previous_fraction", self.monthly_previous_fraction, 12),
        ):
            if len(values) != expected:
                raise ValueError(
                    f"room use {self.room_use_id}: {name} must have {expected} values, "
                    f"got {len(values)}"
                )
        for name, values in (
            ("person_fraction", self.person_fraction),
            ("device_fraction", self.device_fraction),
            ("weekly_fraction", self.weekly_fraction),
            ("monthly_fraction", self.monthly_fraction),
            ("monthly_previous_fraction", self.monthly_previous_fraction),
        ):
            if any(value < 0 for value in values):
                raise ValueError(f"room use {self.room_use_id}: {name} must not be negative")
        if not 0 <= self.rest_days_per_week <= 7:
            raise ValueError(
                f"room use {self.room_use_id}: rest_days_per_week {self.rest_days_per_week} "
                f"outside 0..7"
            )

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "room_use_id": self.room_use_id,
            "person_fraction": list(self.person_fraction),
            "device_fraction": list(self.device_fraction),
            "weekly_fraction": list(self.weekly_fraction),
            "monthly_fraction": list(self.monthly_fraction),
            "monthly_previous_fraction": list(self.monthly_previous_fraction),
            "rest_days_per_week": self.rest_days_per_week,
            "working_days_per_year": self.working_days_per_year,
            "annual_simultaneity": self.annual_simultaneity,
            "provenance": _provenance_dict(self.provenance),
        }


def _schedule_from_dict(data: dict) -> RoomUseSchedule:
    """Rebuild a :class:`RoomUseSchedule` from its package dict."""
    return RoomUseSchedule(
        room_use_id=int(data["room_use_id"]),
        person_fraction=tuple(float(value) for value in data["person_fraction"]),
        device_fraction=tuple(float(value) for value in data["device_fraction"]),
        weekly_fraction=tuple(float(value) for value in data["weekly_fraction"]),
        monthly_fraction=tuple(float(value) for value in data["monthly_fraction"]),
        monthly_previous_fraction=tuple(
            float(value) for value in data["monthly_previous_fraction"]
        ),
        rest_days_per_week=float(data["rest_days_per_week"]),
        working_days_per_year=(
            None
            if data.get("working_days_per_year") is None
            else float(data["working_days_per_year"])
        ),
        annual_simultaneity=(
            None if data.get("annual_simultaneity") is None else float(data["annual_simultaneity"])
        ),
        provenance=_provenance_from_dict(data.get("provenance")),
    )


@dataclass(frozen=True)
class RoomUseInputs:
    """Per-room-use input columns of the ``Eingabedaten`` matrix without catalog labels.

    The parameter matrix (columns D..DN) is captured through the catalog
    label matching of the profile extractor; the columns below carry design
    inputs whose row-6 labels do not match a catalog parameter, so they were
    silently dropped before the proofread audit.  All values are the literal
    workbook cells (``K9:IE53``); ``None`` where the cell is blank.

    The SIA 380/1 system-requirement block (``Qh,li0`` / ``dQh,li`` /
    ``Hüllzahl`` / ``Qh,lim``, columns HZ..IE) is included here because the
    catalog parameters ``QH,li0`` / ``DQH,li`` exist but carry no values
    (label mismatch), and ``Hüllzahl`` / ``Qh,lim`` are not in the catalog.
    """

    room_use_id: int
    fensteranteil: float | None = None  # K: Fensteranteil, Bruttofassade %
    solar_reduction_factor: float | None = None  # Y
    shading_radiation_threshold: float | None = None  # Z: W/m2
    klimatisierung: bool | None = None  # AF: 'x' markers
    klimatisierung_kategorie: str | None = None  # AG
    schallschutz_key: float | None = None  # AK (0/1/2)
    schallschutz_geraete_db: float | None = None  # AL: dB
    schallschutz_nutzung_db: float | None = None  # AM: dB
    sensible_waerme_kuehlfall: float | None = None  # AT: W
    sensible_waerme_heizfall: float | None = None  # AU: W
    k0_korrektur: float | None = None  # BM
    praesenzart: str | None = None  # BO: DP/NP
    ida_kategorie: str | None = None  # BW: IDA class
    aussenluft_volumenstrom: float | None = None  # CB: m3/(h m2)
    cooling_necessity: str | None = None  # CX: nicht notwendig/erwünscht/notwendig
    tagesprofil_typ: str | None = None  # DO
    monatsprofil_typ: str | None = None  # HB: Arbeit/Schule
    qh_li0: float | None = None  # HZ: Heizwärmebedarf Basiswert SIA 380/1
    dqh_li: float | None = None  # IA: Steigungsfaktor
    huellzahl: float | None = None  # ID
    qh_lim: float | None = None  # IE: = HZ + IA * ID
    provenance: Provenance | None = None

    def as_dict(self) -> dict:
        """JSON-ready dict (``None`` fields are omitted)."""
        result = {"room_use_id": self.room_use_id}
        for name in (
            "fensteranteil",
            "solar_reduction_factor",
            "shading_radiation_threshold",
            "klimatisierung",
            "klimatisierung_kategorie",
            "schallschutz_key",
            "schallschutz_geraete_db",
            "schallschutz_nutzung_db",
            "sensible_waerme_kuehlfall",
            "sensible_waerme_heizfall",
            "k0_korrektur",
            "praesenzart",
            "ida_kategorie",
            "aussenluft_volumenstrom",
            "cooling_necessity",
            "tagesprofil_typ",
            "monatsprofil_typ",
            "qh_li0",
            "dqh_li",
            "huellzahl",
            "qh_lim",
        ):
            value = getattr(self, name)
            if value is not None:
                result[name] = value
        result["provenance"] = _provenance_dict(self.provenance)
        return result


def _inputs_from_dict(data: dict) -> RoomUseInputs:
    """Rebuild a :class:`RoomUseInputs` from its package dict."""
    return RoomUseInputs(
        room_use_id=int(data["room_use_id"]),
        **{name: data.get(name) for name in (
            "fensteranteil",
            "solar_reduction_factor",
            "shading_radiation_threshold",
            "klimatisierung",
            "klimatisierung_kategorie",
            "schallschutz_key",
            "schallschutz_geraete_db",
            "schallschutz_nutzung_db",
            "sensible_waerme_kuehlfall",
            "sensible_waerme_heizfall",
            "k0_korrektur",
            "praesenzart",
            "ida_kategorie",
            "aussenluft_volumenstrom",
            "cooling_necessity",
            "tagesprofil_typ",
            "monatsprofil_typ",
            "qh_li0",
            "dqh_li",
            "huellzahl",
            "qh_lim",
        )},
        provenance=_provenance_from_dict(data.get("provenance")),
    )


@dataclass(frozen=True)
class DesignDaySeries:
    """One 96-hour summer design-day series (``Aug_Auslegung`` matrix block).

    The workbook carries two blocks per station — June (rows 4-99) and
    August (rows 100-195) — of 96 hourly values each (4 x 24 h) for the
    outdoor temperature (0.1 °C resolution), relative humidity (%) and
    global radiation (W/m²).  This is the only intact summer-design source
    (the Datenblatt Kühlerauslegung cells are #REF! errors in the workbook).

    Raises:
        ValueError: if any series does not have 96 values.
    """

    month: int  # 6 or 8
    temperature: tuple[float, ...]  # 96 h, °C
    relative_humidity: tuple[float, ...]  # 96 h, %
    radiation: tuple[float, ...]  # 96 h, W/m²
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if self.month not in (6, 8):
            raise ValueError(f"design day month must be 6 or 8, got {self.month}")
        for name, values in (
            ("temperature", self.temperature),
            ("relative_humidity", self.relative_humidity),
            ("radiation", self.radiation),
        ):
            if len(values) != 96:
                raise ValueError(
                    f"design day {self.month}: {name} must have 96 values, got {len(values)}"
                )

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "month": self.month,
            "temperature": list(self.temperature),
            "relative_humidity": list(self.relative_humidity),
            "radiation": list(self.radiation),
            "provenance": _provenance_dict(self.provenance),
        }


def _design_day_from_dict(data: dict) -> DesignDaySeries:
    """Rebuild a :class:`DesignDaySeries` from its package dict."""
    return DesignDaySeries(
        month=int(data["month"]),
        temperature=tuple(float(value) for value in data["temperature"]),
        relative_humidity=tuple(float(value) for value in data["relative_humidity"]),
        radiation=tuple(float(value) for value in data["radiation"]),
        provenance=_provenance_from_dict(data.get("provenance")),
    )


@dataclass(frozen=True)
class ClimateStation:
    """One of the 40 climate stations (assessment 1.2).

    Winter design values (``Winter_Auslegung!H5:H44``), summer design values
    (``Aug_Auslegung``), monthly values (``Monatswerte``), heating degree days
    and temperature-bin hours (``Klimadaten`` in the Gebaeude-Tool).

    The Gebaeude-Tool's ``Klimadaten`` block additionally carries the
    per-temperature-bin hours (``bin_hours``, the ``temperature_bins`` hours
    summed over the 61 bins of −25…+35 °C), the absolute-humidity ratio per
    bin (``bin_humidity_ratio``, g/kg, ``AbsFeuchte`` of the workbook) and the
    station air pressure (``winter_design["pressure"]``, mbar) — the inputs of
    the AHU temperature-bin engine (:mod:`energytools.engine.native.ahu`).
    Packages without them leave the fields ``None``.

    Raises:
        ValueError: on an empty ``name``, an ``id`` outside 1-40, or a
            ``bin_humidity_ratio`` whose length differs from
            ``temperature_bins``.
    """

    id: int
    name: TrilingualText
    winter_design: dict[str, Quantity]
    summer_design: dict[str, Quantity]
    monthly: dict[str, MonthlyProfile]
    temperature_bins: tuple[TemperatureBin, ...] | None = None
    bin_humidity_ratio: tuple[float, ...] | None = None
    hdd: Quantity | None = None
    canton: str | None = None
    wind_direction: str | None = None
    trub_wind_direction: str | None = None
    design_days: tuple[DesignDaySeries, ...] = ()
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or not 1 <= self.id <= 40:
            raise ValueError(f"station id must be an int in 1..40, got {self.id!r}")
        if not self.name.de:
            raise ValueError(f"station {self.id} name must not be empty")
        if self.bin_humidity_ratio is not None:
            if any(value < 0 for value in self.bin_humidity_ratio):
                raise ValueError(f"station {self.id}: bin_humidity_ratio must not be negative")
            if self.temperature_bins is not None and len(self.bin_humidity_ratio) != len(
                self.temperature_bins
            ):
                raise ValueError(
                    f"station {self.id}: bin_humidity_ratio length "
                    f"{len(self.bin_humidity_ratio)} differs from temperature_bins "
                    f"length {len(self.temperature_bins)}"
                )

    def as_dict(self) -> dict:
        """JSON-ready station dict."""
        return {
            "id": self.id,
            "name": _text_dict(self.name),
            "winter_design": {key: _quantity_dict(q) for key, q in self.winter_design.items()},
            "summer_design": {key: _quantity_dict(q) for key, q in self.summer_design.items()},
            "monthly": {key: profile.as_dict() for key, profile in self.monthly.items()},
            "temperature_bins": (
                None
                if self.temperature_bins is None
                else [bin_.as_dict() for bin_ in self.temperature_bins]
            ),
            "bin_humidity_ratio": (
                None if self.bin_humidity_ratio is None else list(self.bin_humidity_ratio)
            ),
            "hdd": _quantity_dict(self.hdd),
            "canton": self.canton,
            "wind_direction": self.wind_direction,
            "trub_wind_direction": self.trub_wind_direction,
            "design_days": [day.as_dict() for day in self.design_days],
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class ClimateData:
    """The immutable collection of all stations of a release, with a version tag.

    The version tag implements the assessment's climate-version requirement
    (8.6); ``station()`` lookup results are returned by its methods.
    """

    version: str
    stations: tuple[ClimateStation, ...]
    source: str | None = None

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("climate version must not be empty")
        station_ids = [station.id for station in self.stations]
        if len(set(station_ids)) != len(station_ids):
            raise ValueError("duplicate climate station ids in release")

    def station(self, station_id: int | str) -> ClimateStation:
        """Look up a station by id.

        Raises:
            UnknownClimateStationError: for an unknown id.
        """
        try:
            station_id_int = int(station_id)
        except (TypeError, ValueError):
            raise UnknownClimateStationError(station_id, self.version) from None
        for station in self.stations:
            if station.id == station_id_int:
                return station
        raise UnknownClimateStationError(station_id, self.version)

    def ids(self) -> tuple[int, ...]:
        """Station ids in order."""
        return tuple(station.id for station in self.stations)

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "version": self.version,
            "source": self.source,
            "stations": [station.as_dict() for station in self.stations],
        }


@dataclass(frozen=True)
class FullLoadHoursTable:
    """Ventilation full-load hours per room use x regulation type x standard version.

    The versioned ``Volll_Lüft`` table (assessment 1.2, 5.1); the version axis
    is the model for the whole dataset's evolution.

    Queries default to the release's **final** standard version: when
    ``standard_version`` is omitted, :meth:`hours` resolves
    ``default_standard_version`` (falling back to the single installed version
    for packages that predate the field).

    Args:
        rows: ``(nutzid, regulation, standard_version)`` -> hours.
        electrical: ``(nutzid, regulation, standard_version)`` -> electrical
            full-load hours (``Volllaststunden elektrische Energie``, columns
            E/I/Q of the sheet).
        stage_hours: ``(nutzid, regulation, stage, standard_version)`` ->
            operating hours of one volume-flow stage (``Betriebsstunden
            Volumenstrom``, columns G/H for 2-stufig, K..P for stufenlos).
        standard_versions: Installed standard versions (e.g. ``"prSIA 2024-C1:2024"``).
        regulations: Regulation types (e.g. ``{"1-stufig", "2-stufig", "stufenlos"}``).
        default_standard_version: The default (final/latest) standard version
            used when :meth:`hours` is called without one; ``None`` falls back
            to the single installed version, else an explicit version is
            required.
        provenance: Optional provenance.
        room_use_ids: Optional set of valid nutzids (passed by :class:`Dataset`);
            enables ``UnknownRoomUseError`` in :meth:`hours`.
    """

    rows: Mapping[tuple[int, str, str], float]
    standard_versions: frozenset[str]
    regulations: frozenset[str]
    electrical: Mapping[tuple[int, str, str], float] = field(default_factory=dict)
    stage_hours: Mapping[tuple[int, str, float, str], float] = field(default_factory=dict)
    default_standard_version: str | None = None
    provenance: Provenance | None = None
    room_use_ids: frozenset[int] | None = field(default=None, repr=False, compare=False)
    release_id: str = field(default="?", repr=False, compare=False)

    def hours(
        self, room_use_id: int, regulation: str, standard_version: str | None = None
    ) -> float:
        """Look up full-load hours.

        ``standard_version=None`` resolves to the default (final/latest)
        standard version: ``default_standard_version`` when set, otherwise the
        single installed version; when neither applies an explicit
        ``standard_version`` is required.

        Raises:
            UnknownRoomUseError: for an unknown ``room_use_id`` (validated
                against the release when the table is part of a :class:`Dataset`).
            TableLookupError: when no standard version can be resolved or the
                combination is absent (a KeyError-compatible
                :class:`EnergyToolsError`).
        """
        if self.room_use_ids is not None and room_use_id not in self.room_use_ids:
            raise UnknownRoomUseError(room_use_id, self.release_id)
        if standard_version is None:
            standard_version = self.default_standard_version
            if standard_version is None and len(self.standard_versions) == 1:
                standard_version = next(iter(self.standard_versions))
            if standard_version is None:
                raise TableLookupError(
                    f"no standard version given and the full-load-hours table of release "
                    f"'{self.release_id}' has no default standard version "
                    f"(installed: {sorted(self.standard_versions)}); "
                    f"pass standard_version explicitly"
                )
        try:
            return self.rows[(room_use_id, regulation, standard_version)]
        except KeyError:
            raise TableLookupError(
                f"{room_use_id!r} / {regulation!r} / {standard_version!r} not found "
                f"in the full-load-hours table of release '{self.release_id}'"
            ) from None

    def as_dict(self) -> dict:
        """JSON-ready dict (rows keyed ``"nutzid|regulation|standard_version"``)."""
        result = {
            "standard_versions": sorted(self.standard_versions),
            "regulations": sorted(self.regulations),
            "default_standard_version": self.default_standard_version,
            "rows": {
                f"{nutzid}|{regulation}|{standard_version}": hours
                for (nutzid, regulation, standard_version), hours in self.rows.items()
            },
            "provenance": _provenance_dict(self.provenance),
        }
        if self.electrical:
            result["electrical"] = {
                f"{nutzid}|{regulation}|{standard_version}": hours
                for (nutzid, regulation, standard_version), hours in self.electrical.items()
            }
        if self.stage_hours:
            result["stage_hours"] = {
                f"{nutzid}|{regulation}|{stage}|{standard_version}": hours
                for (nutzid, regulation, stage, standard_version), hours in self.stage_hours.items()
            }
        return result


@dataclass(frozen=True)
class BuildingCategoryMapping:
    """One row of the SIA 2024 <-> SIA 380/1 building-category mapping (``GEPAMOD``).

    Gebaeudekategorien I...X.
    """

    sia3801_category: str
    room_use_codes: frozenset[str]
    name: TrilingualText | None = None
    provenance: Provenance | None = None

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "sia3801_category": self.sia3801_category,
            "room_use_codes": sorted(self.room_use_codes),
            "name": _text_dict(self.name),
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class AreaTable:
    """One building-category area table (``Fläche-E`` / ``-L`` / ``-ZW`` / ``-Best`` sheets).

    Per category, the area per room use.  The sheet suffix encodes the value
    kind; the model carries it explicitly.
    """

    kind: ValueKind
    rows: Mapping[str, Mapping[str, Quantity]]
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", ValueKind.parse(self.kind))

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "kind": self.kind.value,
            "rows": {
                category: {code: _quantity_dict(q) for code, q in codes.items()}
                for category, codes in self.rows.items()
            },
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class CategoryTable:
    """One per-category reference table (batch C: ``Fläche-E/-ZW/-Best/-L`` + ``GEPAMOD``).

    The SIA 2024 workbook carries, next to the area-% matrix, a family of
    per-building-category reference tables: the "SIA 2024 Standardwerte"
    energy/design-parameter blocks (one per sheet variant: Standard /
    Zielwert / Bestand / Leistung), the "SIA 380/1 Tabelle 27" block, the
    harmonized standard values, SIA 2040, the Minergie weighted / electric
    energy blocks, the Strommodell block, the SIA 380/1 vs SIA 2024
    comparison rows (WW demand, ventilation, person gains, person area, room
    temperature) and the GEPAMOD subcategory / EBF / end-energy tables.

    ``rows`` maps ``(category_code, metric_label)`` to a value; ``metric_label``
    is the workbook's row label (unit column, design parameter name, standard
    version tag, ...), falling back to ``"rowN"`` when a row has values but no
    label.  Duplicate labels within one table are disambiguated with a
    ``" (row N)"`` suffix.  Category codes are taken from the block's row-1
    header and are **not** required to match the building-category mappings
    (the GEPAMOD columns use the SIA 380/1 subcategory codes ``I.1 ... X``).

    Args:
        kind: Table family id, e.g. ``"energy_standard"``, ``"sia3801_tab27"``,
            ``"harmonized"``, ``"sia2040"``, ``"weighted_energy"``,
            ``"electric_energy"``, ``"minergie"``, ``"strommodell"``,
            ``"ww_demand"``, ``"ventilation_flow"``, ``"person_gain"``,
            ``"person_area"``, ``"room_temperature"``, ``"gepamod_end_energy"``,
            ``"gepamod_ebf"``, ``"gepamod_subcategory"``.
        variant: Sheet/value variant: ``"standard" | "zielwert" | "bestand" |
            "power" | "reference"``.
        rows: ``(category_code, metric_label)`` -> value.
        unit: Table-level unit; ``"-"`` when the rows carry mixed units (each
            :class:`Quantity` still carries its own unit).
        provenance: Optional provenance.
    """

    kind: str
    rows: Mapping[tuple[str, str], Quantity]
    variant: str = "reference"
    unit: str = "-"
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not self.kind:
            raise ValueError("category table kind must not be empty")
        if not self.variant:
            raise ValueError("category table variant must not be empty")
        if self.unit is None:
            object.__setattr__(self, "unit", "-")

    def metric(self, metric_label: str, category_code: str | None = None) -> Quantity:
        """Look up one value by metric label (optionally restricted to one category).

        Raises:
            KeyError-compatible :class:`TableLookupError` when the combination
                is absent.
        """
        for (category, metric), quantity in self.rows.items():
            if metric == metric_label and (category_code is None or category == category_code):
                return quantity
        raise TableLookupError(
            f"category-table '{self.kind}' has no value for metric "
            f"{metric_label!r}" + (f" / category {category_code!r}" if category_code else "")
        )

    def as_dict(self) -> dict:
        """JSON-ready dict (rows keyed ``category -> metric -> quantity``)."""
        nested: dict[str, dict[str, dict]] = {}
        for (category, metric), quantity in self.rows.items():
            nested.setdefault(category, {})[metric] = _quantity_dict(quantity)
        return {
            "kind": self.kind,
            "variant": self.variant,
            "unit": self.unit,
            "rows": nested,
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class Sia3801Coefficients:
    """Per-category SIA 380/1 coefficients.

    From the ``SIA 380-1`` / ``_Qc`` / ``_EN`` / ``_Qc_EN`` sheets -- the four
    sheets are one calculation with a variant axis (assessment 8.9).

    Raises:
        ValueError: on an unknown ``variant``.
    """

    variant: str
    category: str
    coefficients: dict[str, Quantity]
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if self.variant not in _SIA3801_VARIANTS:
            raise ValueError(
                f"unknown SIA 380/1 variant '{self.variant}' "
                f"(expected one of {', '.join(_SIA3801_VARIANTS)})"
            )

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "variant": self.variant,
            "category": self.category,
            "coefficients": {key: _quantity_dict(q) for key, q in self.coefficients.items()},
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class Sia3801Result:
    """SIA 380/1 heating-demand result of one room use.

    ``Qh`` and related values incl. the cooling variant ``Qc``, computed for a
    station and value kind.
    """

    room_use_id: int
    station_id: int
    kind: ValueKind
    variant: str
    values: dict[str, Quantity]
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", ValueKind.parse(self.kind))

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "room_use_id": self.room_use_id,
            "station_id": self.station_id,
            "kind": self.kind.value,
            "variant": self.variant,
            "values": {key: _quantity_dict(q) for key, q in self.values.items()},
            "provenance": _provenance_dict(self.provenance),
        }


@dataclass(frozen=True)
class QhcTable:
    """Per-station room-heating/cooling results (``Qhc_Klimastat``, 40 stations x 45 uses).

    Each station block carries four metrics per value kind:
    ``Klimakälteleistungsbedarf`` (cooling power, W/m²), ``Jährlicher
    Klimakältebedarf`` (annual cooling energy, kWh/m²a — the ``rows``
    table), ``Norm-Heizlast`` (heating design load, W/m²) and ``Jährlicher
    Heizwärmebedarf`` (annual heating energy, kWh/m²a).

    Args:
        rows: ``(nutzid, station_id, kind)`` -> annual cooling energy.
        cooling_power: ``(nutzid, station_id, kind)`` -> cooling power W/m².
        heating_load: ``(nutzid, station_id, kind)`` -> heating design load W/m².
        heating_energy: ``(nutzid, station_id, kind)`` -> annual heating kWh/m²a.
        provenance: Optional provenance.
        room_use_ids: Optional id set (passed by :class:`Dataset`);
            enables ``UnknownRoomUseError``.
        station_ids: Optional id set (passed by :class:`Dataset`);
            enables ``UnknownClimateStationError``.
    """

    rows: Mapping[tuple[int, int, ValueKind], Quantity]
    cooling_power: Mapping[tuple[int, int, ValueKind], Quantity] = field(default_factory=dict)
    heating_load: Mapping[tuple[int, int, ValueKind], Quantity] = field(default_factory=dict)
    heating_energy: Mapping[tuple[int, int, ValueKind], Quantity] = field(default_factory=dict)
    provenance: Provenance | None = None
    room_use_ids: frozenset[int] | None = field(default=None, repr=False, compare=False)
    station_ids: frozenset[int] | None = field(default=None, repr=False, compare=False)
    release_id: str = field(default="?", repr=False, compare=False)

    _METRICS = {
        "cooling_energy": "rows",
        "cooling_power": "cooling_power",
        "heating_load": "heating_load",
        "heating_energy": "heating_energy",
    }

    def metric(self, name: str, room_use_id: int, station_id: int, kind: ValueKind = ValueKind.STANDARD) -> Quantity:
        """Look up one of the four per-station metrics.

        ``name`` is one of ``"cooling_energy" | "cooling_power" |
        "heating_load" | "heating_energy"``.

        Raises:
            ValueError: for an unknown metric name.
            UnknownRoomUseError / UnknownClimateStationError: for unknown ids.
            TableLookupError: when the combination is absent (KeyError-compatible).
        """
        attribute = self._METRICS.get(name)
        if attribute is None:
            raise ValueError(
                f"unknown Qhc metric {name!r} (expected one of {', '.join(self._METRICS)})"
            )
        kind = kind if isinstance(kind, ValueKind) else ValueKind.parse(kind)
        if self.room_use_ids is not None and room_use_id not in self.room_use_ids:
            raise UnknownRoomUseError(room_use_id, self.release_id)
        if self.station_ids is not None and station_id not in self.station_ids:
            raise UnknownClimateStationError(station_id, self.release_id)
        table = getattr(self, attribute)
        try:
            return table[(room_use_id, station_id, kind)]
        except KeyError:
            raise TableLookupError(
                f"Qhc {name} for room use {room_use_id!r} / station {station_id!r} / "
                f"kind {kind.value!r} not found in release '{self.release_id}'"
            ) from None

    def qhc(
        self,
        room_use_id: int,
        station_id: int,
        kind: ValueKind = ValueKind.STANDARD,
    ) -> Quantity:
        """Look up the annual cooling energy.

        Raises:
            UnknownRoomUseError / UnknownClimateStationError: for unknown ids
                (validated against the release when part of a :class:`Dataset`).
            TableLookupError: when the combination is absent (KeyError-compatible).
        """
        kind = kind if isinstance(kind, ValueKind) else ValueKind.parse(kind)
        if self.room_use_ids is not None and room_use_id not in self.room_use_ids:
            raise UnknownRoomUseError(room_use_id, self.release_id)
        if self.station_ids is not None and station_id not in self.station_ids:
            raise UnknownClimateStationError(station_id, self.release_id)
        try:
            return self.rows[(room_use_id, station_id, kind)]
        except KeyError:
            raise TableLookupError(
                f"Qhc for room use {room_use_id!r} / station {station_id!r} / "
                f"kind {kind.value!r} not found in release '{self.release_id}'"
            ) from None

    @staticmethod
    def _rows_keyed(rows: Mapping[tuple[int, int, ValueKind], Quantity]) -> dict:
        return {
            f"{nutzid}|{station_id}|{kind.value}": _quantity_dict(q)
            for (nutzid, station_id, kind), q in rows.items()
        }

    def as_dict(self) -> dict:
        """JSON-ready dict (rows keyed ``"nutzid|station_id|kind"``)."""
        result = {"rows": self._rows_keyed(self.rows)}
        for key in ("cooling_power", "heating_load", "heating_energy"):
            table = getattr(self, key)
            if table:
                result[key] = self._rows_keyed(table)
        result["provenance"] = _provenance_dict(self.provenance)
        return result


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


@dataclass(frozen=True, init=False, eq=False)
class Dataset:
    """One immutable dataset release: every table of the canonical package.

    This is the **only** way the calculation engine consumes Raumdaten
    (assessment 5.3 rule 2).  Immutable after construction; all data access
    happens through its methods.

    The constructor accepts the documented input names (``release``,
    ``room_uses``, ``parameters``, ``profiles``, ..., ``mappings``, ...).
    Tables whose name also exists as an accessor method (``room_uses``,
    ``parameters``, ``climate``, ``full_load_hours``, ``qhc``, ``mappings``,
    ``area_tables``, ``sia3801_coefficients``, ``category_tables``) are stored
    under private attributes and read exclusively through the accessor methods
    -- the accessors are the attribute API.

    Raises:
        ValueError: on inconsistent content (e.g. profile count != room-use
            count, unknown references in tables, invalid variants).
    """

    release: DatasetRelease
    profiles: Mapping[int, RoomUseProfile]
    schedules: Mapping[int, RoomUseSchedule]
    inputs: Mapping[int, RoomUseInputs]
    hourly_profiles: tuple[HourlyProfile, ...]
    monthly_profiles: tuple[MonthlyProfile, ...]
    weekly_profiles: tuple[WeeklyProfile, ...]
    sia3801: tuple[Sia3801Result, ...]

    # Private storage for tables that also exist as accessor methods (see the
    # class docstring); assigned in __init__ via object.__setattr__.
    _room_uses: tuple[RoomUse, ...] = field(init=False, repr=False, compare=False)
    _parameters: tuple[Parameter, ...] = field(init=False, repr=False, compare=False)
    _climate: ClimateData = field(init=False, repr=False, compare=False)
    _full_load_hours: FullLoadHoursTable = field(init=False, repr=False, compare=False)
    _qhc: QhcTable = field(init=False, repr=False, compare=False)
    _mappings: tuple[BuildingCategoryMapping, ...] = field(init=False, repr=False, compare=False)
    _area_tables: tuple[AreaTable, ...] = field(init=False, repr=False, compare=False)
    _sia3801_coefficients: tuple[Sia3801Coefficients, ...] = field(
        init=False, repr=False, compare=False
    )
    _category_tables: tuple[CategoryTable, ...] = field(init=False, repr=False, compare=False)
    _catalog: dict[str, Parameter] = field(init=False, repr=False, compare=False)
    _room_use_by_nutzid: dict[int, RoomUse] = field(init=False, repr=False, compare=False)
    _room_use_by_code: dict[str, RoomUse] = field(init=False, repr=False, compare=False)
    _stations: set[int] = field(init=False, repr=False, compare=False)
    _room_use_catalog: "RoomUseCatalog" = field(init=False, repr=False, compare=False)
    _parameter_catalog: "ParameterCatalog" = field(init=False, repr=False, compare=False)

    def __init__(
        self,
        release: DatasetRelease,
        room_uses: tuple[RoomUse, ...],
        parameters: tuple[Parameter, ...],
        profiles: Mapping[int, RoomUseProfile],
        schedules: Mapping[int, RoomUseSchedule] | None = None,
        inputs: Mapping[int, RoomUseInputs] | None = None,
        hourly_profiles: tuple[HourlyProfile, ...] = (),
        monthly_profiles: tuple[MonthlyProfile, ...] = (),
        weekly_profiles: tuple[WeeklyProfile, ...] = (),
        climate: ClimateData | None = None,
        full_load_hours: FullLoadHoursTable | None = None,
        qhc: QhcTable | None = None,
        sia3801: tuple[Sia3801Result, ...] = (),
        mappings: tuple[BuildingCategoryMapping, ...] = (),
        area_tables: tuple[AreaTable, ...] = (),
        sia3801_coefficients: tuple[Sia3801Coefficients, ...] = (),
        category_tables: tuple[CategoryTable, ...] = (),
    ) -> None:
        """See the class docstring; ``release``, ``room_uses``, ``parameters`` and
        ``profiles`` are required, the remaining tables default to empty."""
        object.__setattr__(self, "release", release)
        object.__setattr__(self, "_room_uses", tuple(room_uses))
        object.__setattr__(self, "_parameters", tuple(parameters))
        object.__setattr__(self, "profiles", profiles)
        object.__setattr__(self, "schedules", dict(schedules or {}))
        object.__setattr__(self, "inputs", dict(inputs or {}))
        object.__setattr__(self, "hourly_profiles", tuple(hourly_profiles))
        object.__setattr__(self, "monthly_profiles", tuple(monthly_profiles))
        object.__setattr__(self, "weekly_profiles", tuple(weekly_profiles))
        object.__setattr__(self, "_climate", climate or ClimateData(version="", stations=()))
        object.__setattr__(self, "_full_load_hours", full_load_hours)
        object.__setattr__(self, "_qhc", qhc)
        object.__setattr__(self, "sia3801", tuple(sia3801))
        object.__setattr__(self, "_mappings", tuple(mappings))
        object.__setattr__(self, "_area_tables", tuple(area_tables))
        object.__setattr__(self, "_sia3801_coefficients", tuple(sia3801_coefficients))
        object.__setattr__(self, "_category_tables", tuple(category_tables))
        self.__post_init__()

    def __post_init__(self) -> None:
        errors, _ = self._collect_issues()
        if errors:
            raise ValueError("inconsistent dataset content:\n  " + "\n  ".join(errors))
        catalog = {parameter.id: parameter for parameter in self._parameters}
        room_use_by_nutzid = {room_use.nutzid: room_use for room_use in self._room_uses}
        room_use_by_code = {room_use.code: room_use for room_use in self._room_uses}
        stations = {station.id for station in self._climate.stations}
        object.__setattr__(self, "_catalog", catalog)
        object.__setattr__(self, "_room_use_by_nutzid", room_use_by_nutzid)
        object.__setattr__(self, "_room_use_by_code", room_use_by_code)
        object.__setattr__(self, "_stations", stations)
        # Attribute-access catalogs (generated @property mixins; also callable
        # for backwards compatibility with ds.room_uses() / ds.parameters()).
        object.__setattr__(
            self,
            "_room_use_catalog",
            RoomUseCatalog(list(self._room_uses)),
        )
        object.__setattr__(
            self,
            "_parameter_catalog",
            ParameterCatalog(list(self._parameters)),
        )
        # Re-bind lookup tables so the Unknown* errors carry this release id and
        # validate against the release.
        object.__setattr__(
            self,
            "_full_load_hours",
            FullLoadHoursTable(
                rows=self._full_load_hours.rows,
                standard_versions=self._full_load_hours.standard_versions,
                regulations=self._full_load_hours.regulations,
                default_standard_version=self._full_load_hours.default_standard_version,
                provenance=self._full_load_hours.provenance,
                room_use_ids=frozenset(room_use_by_nutzid),
                release_id=self.release.id,
            ),
        )
        object.__setattr__(
            self,
            "_qhc",
            QhcTable(
                rows=self._qhc.rows,
                cooling_power=self._qhc.cooling_power,
                heating_load=self._qhc.heating_load,
                heating_energy=self._qhc.heating_energy,
                provenance=self._qhc.provenance,
                room_use_ids=frozenset(room_use_by_nutzid),
                station_ids=frozenset(stations),
                release_id=self.release.id,
            ),
        )
        for profile in self.profiles.values():
            object.__setattr__(profile, "release_id", self.release.id)
            object.__setattr__(profile, "parameter_catalog", catalog)

    def __eq__(self, other: object) -> bool:
        """Content equality across every table of the package."""
        if not isinstance(other, Dataset):
            return NotImplemented
        return self._content_key() == other._content_key()

    def _content_key(self) -> tuple:
        return (
            self.release,
            self._room_uses,
            self._parameters,
            self.profiles,
            self.hourly_profiles,
            self.monthly_profiles,
            self.weekly_profiles,
            self._climate,
            self._full_load_hours,
            self._qhc,
            self.sia3801,
            self._mappings,
            self._area_tables,
            self._sia3801_coefficients,
            self._category_tables,
        )

    def __repr__(self) -> str:
        return (
            f"Dataset(release_id={self.release.id!r}, room_uses={len(self._room_uses)}, "
            f"parameters={len(self._parameters)}, profiles={len(self.profiles)}, "
            f"climate_stations={len(self._climate.stations)})"
        )

    @property
    def release_id(self) -> str:
        """Release id (``release.id``)."""
        return self.release.id

    # -- lookups ------------------------------------------------------------

    def room_use(self, room_use_id: int | str) -> RoomUse:
        """Look up a room use by nutzid or SIA code.

        Raises:
            UnknownRoomUseError: for an unknown id.
        """
        if isinstance(room_use_id, int):
            room_use = self._room_use_by_nutzid.get(room_use_id)
        else:
            room_use = self._room_use_by_code.get(normalize_room_use_code(room_use_id))
        if room_use is None:
            raise UnknownRoomUseError(room_use_id, self.release.id)
        return room_use

    @property
    def room_uses(self) -> "RoomUseCatalog":
        """All 45 room uses with attribute access: ``ds.room_uses.group_office``.

        Also callable for compatibility: ``ds.room_uses()`` returns the tuple.
        """
        return self._room_use_catalog

    def parameter(self, parameter_id: str) -> Parameter:
        """Look up one catalog parameter.

        Raises:
            UnknownParameterError: for an unknown id.
        """
        parameter = self._catalog.get(parameter_id)
        if parameter is None:
            raise UnknownParameterError(parameter_id, self.release.id)
        return parameter

    @property
    def parameters(self) -> "ParameterCatalog":
        """The parameter catalog with attribute access: ``ds.parameters.personnel_area``.

        Also callable for compatibility: ``ds.parameters()`` returns the tuple.
        """
        return self._parameter_catalog

    def profile(self, room_use_id: int, kind: ValueKind | None = None) -> RoomUseProfile:
        """The full profile of one room use (all value kinds).

        ``kind`` is accepted and validated for API compatibility with the
        specification; the returned profile always carries all value kinds.

        Raises:
            UnknownRoomUseError: for an unknown ``room_use_id``.
            UnknownValueKindError: for an invalid ``kind``.
        """
        if kind is not None and not isinstance(kind, ValueKind):
            ValueKind.parse(kind)
        profile = self.profiles.get(room_use_id)
        if profile is None:
            raise UnknownRoomUseError(room_use_id, self.release.id)
        return profile

    def climate(self) -> ClimateData:
        """The climate data of the release."""
        return self._climate

    def full_load_hours(self) -> FullLoadHoursTable:
        """The ventilation full-load-hours table of the release."""
        return self._full_load_hours

    def qhc(self) -> QhcTable:
        """The annual cooling-energy table of the release."""
        return self._qhc

    def sia3801_results(self, variant: str | None = None) -> tuple[Sia3801Result, ...]:
        """SIA 380/1 results, optionally filtered by variant (``"de" | "en" | "de+qc" | "en+qc"``)."""
        if variant is None:
            return self.sia3801
        return tuple(result for result in self.sia3801 if result.variant == variant)

    def mappings(self) -> tuple[BuildingCategoryMapping, ...]:
        """The SIA 2024 <-> SIA 380/1 category mappings of the release."""
        return self._mappings

    def area_tables(self) -> tuple[AreaTable, ...]:
        """The building-category area tables of the release."""
        return self._area_tables

    def sia3801_coefficients(self) -> tuple[Sia3801Coefficients, ...]:
        """The per-category SIA 380/1 coefficients of the release."""
        return self._sia3801_coefficients

    def category_tables(self) -> tuple[CategoryTable, ...]:
        """The per-category reference tables of the release (batch C)."""
        return self._category_tables

    # -- validation ---------------------------------------------------------

    def validate(self) -> ValidationReport:
        """Schema + domain-value validation (see :class:`ValidationReport`).

        Errors are reported, not raised.
        """
        errors, warnings = self._collect_issues()
        return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))

    def _collect_issues(self) -> tuple[list[str], list[str]]:
        """Hard errors and warnings over the whole release content."""
        errors: list[str] = []
        warnings: list[str] = []

        if not isinstance(self.release, DatasetRelease):
            errors.append("release metadata missing or invalid")
        if not self._parameters:
            errors.append("parameter catalog is empty")
        if not self._room_uses:
            errors.append("room-use list is empty")

        nutzids = [room_use.nutzid for room_use in self._room_uses]
        if len(set(nutzids)) != len(nutzids):
            errors.append("duplicate room-use nutzids")
        codes = [room_use.code for room_use in self._room_uses]
        if len(set(codes)) != len(codes):
            errors.append("duplicate room-use codes")
        for room_use in self._room_uses:
            if not _CODE_RE.match(room_use.code):
                warnings.append(
                    f"room use {room_use.nutzid}: code '{room_use.code}' is not canonical "
                    f"(expected NN.NN)"
                )

        parameter_ids = [parameter.id for parameter in self._parameters]
        if len(set(parameter_ids)) != len(parameter_ids):
            errors.append("duplicate parameter ids")

        profile_nutzids = set(self.profiles)
        if profile_nutzids != set(nutzids):
            missing = sorted(set(nutzids) - profile_nutzids)
            extra = sorted(profile_nutzids - set(nutzids))
            errors.append(f"profiles do not match room uses (missing: {missing}, extra: {extra})")
        catalog = {parameter.id: parameter for parameter in self._parameters}
        for nutzid, profile in self.profiles.items():
            if profile.room_use.nutzid != nutzid:
                errors.append(f"profile key {nutzid} does not match its room use")
            if profile.parameter_catalog != catalog:
                errors.append(f"profile {nutzid} uses a different parameter catalog")
            for parameter_id, by_kind in profile.values.items():
                parameter = catalog.get(parameter_id)
                if parameter is None:
                    errors.append(f"profile {nutzid} references unknown parameter '{parameter_id}'")
                    continue
                for kind, value in by_kind.items():
                    if not parameter.value_kinds or kind not in parameter.value_kinds:
                        warnings.append(
                            f"profile {nutzid}: parameter '{parameter_id}' has a value for "
                            f"non-applicable kind '{kind.value}'"
                        )
                    if (
                        parameter.unit.dimension == "dimensionless"
                        and parameter.unit.symbol == "%"
                        and isinstance(value.value, (int, float))
                        and not 0.0 <= value.value <= 100.0
                    ):
                        warnings.append(
                            f"profile {nutzid}: parameter '{parameter_id}' value {value.value} "
                            f"outside 0..100 %"
                        )

        for parameter in self._parameters:
            if not parameter.value_kinds:
                warnings.append(f"parameter '{parameter.id}' has no applicable value kinds")

        station_ids = [station.id for station in self._climate.stations]
        if len(set(station_ids)) != len(station_ids):
            errors.append("duplicate climate station ids")
        for station in self._climate.stations:
            if not station.name.de:
                errors.append(f"station {station.id} has an empty name")
            for key, monthly in station.monthly.items():
                if len(monthly.values) != 12:
                    errors.append(f"station {station.id}: monthly profile '{key}' has wrong length")
            if station.temperature_bins:
                for bin_ in station.temperature_bins:
                    if bin_.lower > bin_.upper or bin_.hours < 0:
                        errors.append(f"station {station.id}: invalid temperature bin {bin_}")

        if self._full_load_hours:
            for (nutzid, regulation, standard_version), hours in self._full_load_hours.rows.items():
                if nutzid not in set(nutzids):
                    errors.append(f"full-load hours reference unknown room use {nutzid}")
                if hours < 0:
                    errors.append(
                        f"full-load hours for {nutzid}/{regulation}/{standard_version} are negative"
                    )
            unknown_versions = self._full_load_hours.standard_versions - {
                v for (_, _, v) in self._full_load_hours.rows
            }
            if unknown_versions:
                warnings.append(f"standard versions without rows: {sorted(unknown_versions)}")

        if self._qhc:
            for nutzid, station_id, kind in self._qhc.rows:
                if nutzid not in set(nutzids):
                    errors.append(f"Qhc references unknown room use {nutzid}")
                if station_id not in set(station_ids):
                    errors.append(f"Qhc references unknown climate station {station_id}")

        for schedule_id in self.schedules:
            if schedule_id not in set(nutzids):
                errors.append(f"room-use schedule references unknown room use {schedule_id}")
        for inputs_id in self.inputs:
            if inputs_id not in set(nutzids):
                errors.append(f"room-use inputs reference unknown room use {inputs_id}")

        known_codes = set(codes)
        for mapping in self._mappings:
            unknown_codes = mapping.room_use_codes - known_codes
            if unknown_codes:
                errors.append(
                    f"mapping '{mapping.sia3801_category}' references unknown room-use codes: "
                    f"{sorted(unknown_codes)}"
                )

        category_ids = {mapping.sia3801_category for mapping in self._mappings}
        for table in self._area_tables:
            for category, codes_by_category in table.rows.items():
                if category_ids and category not in category_ids:
                    errors.append(
                        f"area table '{table.kind.value}' references unknown category '{category}'"
                    )
                unknown_area_codes = set(codes_by_category) - known_codes
                if unknown_area_codes:
                    errors.append(
                        f"area table '{table.kind.value}' references unknown room-use codes: "
                        f"{sorted(unknown_area_codes)}"
                    )

        for coefficients in self._sia3801_coefficients:
            if coefficients.category and coefficients.category not in category_ids:
                errors.append(
                    f"coefficients '{coefficients.variant}' reference unknown category "
                    f"'{coefficients.category}'"
                )

        for result in self.sia3801:
            if result.room_use_id not in set(nutzids):
                errors.append(f"SIA 380/1 result references unknown room use {result.room_use_id}")
            if result.station_id not in set(station_ids):
                errors.append(
                    f"SIA 380/1 result references unknown climate station {result.station_id}"
                )
            if result.variant not in ("de", "en", "de+qc", "en+qc"):
                errors.append(f"SIA 380/1 result has unknown variant '{result.variant}'")

        return errors, warnings

    # -- serialization ------------------------------------------------------

    def to_package_dict(self) -> dict:
        """JSON-ready package dict (the canonical package file content)."""
        return {
            "schema_version": "1.0",
            "release": _release_dict(self.release),
            "room_uses": [room_use.as_dict() for room_use in self._room_uses],
            "parameters": [parameter.as_dict() for parameter in self._parameters],
            "profiles": [
                {
                    "nutzid": nutzid,
                    "values": {
                        parameter_id: {
                            kind.value: value.as_dict() for kind, value in by_kind.items()
                        }
                        for parameter_id, by_kind in profile.values.items()
                    },
                }
                for nutzid, profile in sorted(self.profiles.items())
            ],
            "room_use_schedules": [
                self.schedules[nutzid].as_dict() for nutzid in sorted(self.schedules)
            ],
            "room_use_inputs": [self.inputs[nutzid].as_dict() for nutzid in sorted(self.inputs)],
            "hourly_profiles": [profile.as_dict() for profile in self.hourly_profiles],
            "monthly_profiles": [profile.as_dict() for profile in self.monthly_profiles],
            "weekly_profiles": [profile.as_dict() for profile in self.weekly_profiles],
            "climate": self._climate.as_dict(),
            "full_load_hours": self._full_load_hours.as_dict(),
            "qhc": self._qhc.as_dict(),
            "sia3801": [result.as_dict() for result in self.sia3801],
            "mappings": [mapping.as_dict() for mapping in self._mappings],
            "area_tables": [table.as_dict() for table in self._area_tables],
            "sia3801_coefficients": [
                coefficients.as_dict() for coefficients in self._sia3801_coefficients
            ],
            "category_tables": [table.as_dict() for table in self._category_tables],
        }

    @classmethod
    def from_package_dict(cls, data: dict) -> Dataset:
        """Build a :class:`Dataset` from a package dict (the loader's core).

        Applies the documented data-quality normalization (code ``12.1`` ->
        ``12.10``, quality quirk 12.1).
        """
        room_uses = tuple(_room_use_from_dict(item) for item in data["room_uses"])
        parameters = tuple(_parameter_from_dict(item) for item in data["parameters"])
        catalog = {parameter.id: parameter for parameter in parameters}

        profiles = {}
        for item in data["profiles"]:
            nutzid = int(item["nutzid"])
            values = {
                parameter_id: {
                    ValueKind.parse(kind): ParameterValue(
                        parameter_id=parameter_id,
                        kind=ValueKind.parse(kind),
                        value=value_data.get("value"),
                        unit=value_data.get("unit", "-"),
                        provenance=_provenance_from_dict(value_data.get("provenance")),
                    )
                    for kind, value_data in by_kind.items()
                }
                for parameter_id, by_kind in item["values"].items()
            }
            room_use = next(ru for ru in room_uses if ru.nutzid == nutzid)
            profiles[nutzid] = RoomUseProfile(
                room_use=room_use,
                values=values,
                parameter_catalog=catalog,
            )

        stations = tuple(
            _station_from_dict(item, index)
            for index, item in enumerate(data["climate"]["stations"], start=1)
        )
        climate = ClimateData(
            version=data["climate"]["version"],
            stations=stations,
            source=data["climate"].get("source"),
        )

        flh_data = data["full_load_hours"]
        flh_versions = frozenset(flh_data["standard_versions"])
        # Absent key -> fall back to the single installed version (final-version
        # semantics for packages that predate the field); a present key (even
        # null) is honored as-is so as_dict/from_package_dict round-trips
        # preserve the table exactly.
        flh_default = flh_data.get("default_standard_version")
        if flh_default is None and "default_standard_version" not in flh_data and len(flh_versions) == 1:
            flh_default = next(iter(flh_versions))
        full_load_hours = FullLoadHoursTable(
            rows={
                (int(nutzid), regulation, standard_version): float(value)
                for key, value in flh_data["rows"].items()
                for nutzid, regulation, standard_version in [_parse_row_key(key, 3)]
            },
            electrical={
                (int(nutzid), regulation, standard_version): float(value)
                for key, value in flh_data.get("electrical", {}).items()
                for nutzid, regulation, standard_version in [_parse_row_key(key, 3)]
            },
            stage_hours={
                (int(nutzid), regulation, float(stage), standard_version): float(value)
                for key, value in flh_data.get("stage_hours", {}).items()
                for nutzid, regulation, stage, standard_version in [_parse_row_key(key, 4)]
            },
            standard_versions=flh_versions,
            regulations=frozenset(flh_data["regulations"]),
            default_standard_version=flh_default,
            provenance=_provenance_from_dict(flh_data.get("provenance")),
        )

        qhc_data = data["qhc"]
        qhc = QhcTable(
            rows={
                _parse_qhc_key(key): Quantity(
                    value.get("value"),
                    value.get("unit", "-"),
                )
                for key, value in qhc_data["rows"].items()
            },
            cooling_power={
                _parse_qhc_key(key): Quantity(
                    value.get("value"),
                    value.get("unit", "-"),
                )
                for key, value in qhc_data.get("cooling_power", {}).items()
            },
            heating_load={
                _parse_qhc_key(key): Quantity(
                    value.get("value"),
                    value.get("unit", "-"),
                )
                for key, value in qhc_data.get("heating_load", {}).items()
            },
            heating_energy={
                _parse_qhc_key(key): Quantity(
                    value.get("value"),
                    value.get("unit", "-"),
                )
                for key, value in qhc_data.get("heating_energy", {}).items()
            },
            provenance=_provenance_from_dict(qhc_data.get("provenance")),
        )

        return cls(
            release=_release_from_dict(data["release"]),
            room_uses=room_uses,
            parameters=parameters,
            profiles=profiles,
            schedules={
                int(item["room_use_id"]): _schedule_from_dict(item)
                for item in data.get("room_use_schedules", [])
            },
            inputs={
                int(item["room_use_id"]): _inputs_from_dict(item)
                for item in data.get("room_use_inputs", [])
            },
            hourly_profiles=tuple(
                HourlyProfile(
                    id=item["id"],
                    profile_type=item["profile_type"],
                    values=tuple(float(v) for v in item["values"]),
                    unit=item.get("unit", "%"),
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data["hourly_profiles"]
            ),
            monthly_profiles=tuple(
                MonthlyProfile(
                    id=item["id"],
                    values=tuple(float(v) for v in item["values"]),
                    unit=item["unit"],
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data["monthly_profiles"]
            ),
            weekly_profiles=tuple(
                WeeklyProfile(
                    id=item["id"],
                    values=tuple(float(v) for v in item["values"]),
                    unit=item.get("unit", "%"),
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data["weekly_profiles"]
            ),
            climate=climate,
            full_load_hours=full_load_hours,
            qhc=qhc,
            sia3801=tuple(
                Sia3801Result(
                    room_use_id=item["room_use_id"],
                    station_id=item["station_id"],
                    kind=item["kind"],
                    variant=item["variant"],
                    values={
                        key: Quantity(value.get("value"), value.get("unit", "-"))
                        for key, value in item["values"].items()
                    },
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data["sia3801"]
            ),
            mappings=tuple(
                BuildingCategoryMapping(
                    sia3801_category=item["sia3801_category"],
                    room_use_codes=frozenset(item["room_use_codes"]),
                    name=_text_from_dict(item.get("name")),
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data["mappings"]
            ),
            area_tables=tuple(
                AreaTable(
                    kind=item["kind"],
                    rows={
                        category: {
                            code: Quantity(value.get("value"), value.get("unit", "-"))
                            for code, value in codes.items()
                        }
                        for category, codes in item["rows"].items()
                    },
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data["area_tables"]
            ),
            sia3801_coefficients=tuple(
                Sia3801Coefficients(
                    variant=item["variant"],
                    category=item["category"],
                    coefficients={
                        key: Quantity(value.get("value"), value.get("unit", "-"))
                        for key, value in item["coefficients"].items()
                    },
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data["sia3801_coefficients"]
            ),
            category_tables=tuple(
                CategoryTable(
                    kind=item["kind"],
                    variant=item.get("variant", "reference"),
                    unit=item.get("unit", "-"),
                    rows={
                        (category, metric): Quantity(
                            value.get("value"), value.get("unit", "-")
                        )
                        for category, metrics in item.get("rows", {}).items()
                        for metric, value in metrics.items()
                    },
                    provenance=_provenance_from_dict(item.get("provenance")),
                )
                for item in data.get("category_tables", [])
            ),
        )


# ---------------------------------------------------------------------------
# Package-dict parsing helpers
# ---------------------------------------------------------------------------


def _parse_row_key(key: str, parts: int) -> tuple:
    """Parse ``"1|1-stufig|prSIA 2024-C1:2024"`` style row keys."""
    pieces = key.split("|")
    if len(pieces) != parts:
        raise ValueError(f"malformed row key '{key}' (expected {parts} '|'-separated parts)")
    return tuple(pieces)


def _parse_qhc_key(key: str) -> tuple[int, int, ValueKind]:
    nutzid, station_id, kind = _parse_row_key(key, 3)
    return int(nutzid), int(station_id), ValueKind.parse(kind)


def _release_dict(release: DatasetRelease) -> dict:
    return {
        "id": release.id,
        "edition": release.edition,
        "publication_date": release.publication_date.isoformat(),
        "checksum_sha256": release.checksum_sha256,
        "source_workbook": release.source_workbook,
        "extraction_tool_version": release.extraction_tool_version,
        "supersedes": release.supersedes,
        "changelog": [
            {
                "version": entry.version,
                "date": entry.date.isoformat(),
                "change": entry.change,
                "migration": entry.migration,
            }
            for entry in release.changelog
        ],
    }


def _release_from_dict(data: dict) -> DatasetRelease:
    from energytools.common.versioning import ChangelogEntry

    return DatasetRelease(
        id=data["id"],
        edition=data["edition"],
        publication_date=date.fromisoformat(data["publication_date"]),
        checksum_sha256=data["checksum_sha256"],
        source_workbook=data["source_workbook"],
        extraction_tool_version=data["extraction_tool_version"],
        supersedes=data.get("supersedes"),
        changelog=tuple(
            ChangelogEntry(
                version=entry["version"],
                date=date.fromisoformat(entry["date"]),
                change=entry["change"],
                migration=entry.get("migration"),
            )
            for entry in data.get("changelog", [])
        ),
    )


def _text_from_dict(data: dict | None) -> TrilingualText | None:
    if data is None:
        return None
    return TrilingualText(de=data.get("de", ""), fr=data.get("fr", ""), it=data.get("it", ""))


def _provenance_from_dict(data: dict | None) -> Provenance | None:
    if data is None:
        return None
    from energytools.common.provenance import SourceRef

    return Provenance(
        sources=tuple(
            SourceRef(
                workbook=source["workbook"],
                sheet=source["sheet"],
                range=source.get("range"),
                formula=source.get("formula"),
                cached_value=source.get("cached_value"),
                extraction_hash=source.get("extraction_hash"),
            )
            for source in data.get("sources", [])
        ),
        note=data.get("note"),
    )


def _room_use_from_dict(data: dict) -> RoomUse:
    return RoomUse(
        nutzid=int(data["nutzid"]),
        code=normalize_room_use_code(data["code"]),
        category=int(data["category"]),
        name=_text_from_dict(data["name"]) or TrilingualText(),
        sia_clause=data.get("sia_clause"),
    )


def _parameter_from_dict(data: dict) -> Parameter:
    return Parameter(
        id=data["id"],
        label=_text_from_dict(data["label"]) or TrilingualText(),
        symbol=data.get("symbol", ""),
        unit=data.get("unit", "-"),
        data_type=data.get("data_type", "number"),
        category=data.get("category", ""),
        value_kinds=frozenset(ValueKind.parse(kind) for kind in data.get("value_kinds", [])),
        export_flag=bool(data.get("export_flag", True)),
        display_flag=bool(data.get("display_flag", True)),
        internal_heat_flag=bool(data.get("internal_heat_flag", False)),
        qhc_flag=bool(data.get("qhc_flag", False)),
        provenance=_provenance_from_dict(data.get("provenance")),
    )


def _station_from_dict(data: dict, index: int) -> ClimateStation:
    monthly = {
        key: MonthlyProfile(
            id=profile.get("id", key),
            values=tuple(float(v) for v in profile["values"]),
            unit=profile.get("unit", "-"),
            provenance=_provenance_from_dict(profile.get("provenance")),
        )
        for key, profile in data.get("monthly", {}).items()
    }
    bins = data.get("temperature_bins")
    return ClimateStation(
        id=int(data["id"]),
        name=_text_from_dict(data["name"]) or TrilingualText(),
        winter_design={
            key: Quantity(value.get("value"), value.get("unit", "-"))
            for key, value in data.get("winter_design", {}).items()
        },
        summer_design={
            key: Quantity(value.get("value"), value.get("unit", "-"))
            for key, value in data.get("summer_design", {}).items()
        },
        monthly=monthly,
        temperature_bins=(
            None
            if bins is None
            else tuple(
                TemperatureBin(lower=bin_["lower"], upper=bin_["upper"], hours=bin_["hours"])
                for bin_ in bins
            )
        ),
        hdd=(
            None
            if data.get("hdd") is None
            else Quantity(data["hdd"].get("value"), data["hdd"].get("unit", "-"))
        ),
        bin_humidity_ratio=(
            None
            if data.get("bin_humidity_ratio") is None
            else tuple(float(value) for value in data["bin_humidity_ratio"])
        ),
        canton=data.get("canton"),
        wind_direction=data.get("wind_direction"),
        trub_wind_direction=data.get("trub_wind_direction"),
        design_days=tuple(
            _design_day_from_dict(item) for item in data.get("design_days", [])
        ),
        provenance=_provenance_from_dict(data.get("provenance")),
    )
