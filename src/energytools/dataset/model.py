"""Data models of the ``energytools.dataset`` data service.

Implements the canonical, versioned Raumdaten dataset (docs/architecture+api-reference/
03-raumdaten-service.md §1) as immutable value objects: :class:`RoomUse` (one of the
45 standard room uses), :class:`Parameter` (one of the data-sheet parameters, keyed by
SIA clause id), :class:`ParameterValue`, :class:`RoomUseProfile` (one room use × all
value kinds), :class:`ClimateStation` and the release container :class:`Dataset`.

Conventions follow :mod:`energytools.engine.model`: plain frozen dataclasses (no
pydantic), strict constructors that raise ``ValueError`` on invalid input,
``as_dict()`` for JSON serialization, and the workbook's German vocabulary kept
verbatim (``Standard``/``Zielwert``/``Bestand`` value kinds, ``Datenblatt`` sheet,
SIA clause ids). Units and quantities come from :mod:`energytools.common.units`,
labels from :mod:`energytools.common.language`, value kinds from
:mod:`energytools.common.valuekind` and release metadata from
:mod:`energytools.common.versioning`.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from energytools.common.errors import (
    ExportError,
    UnknownClimateStationError,
    UnknownParameterError,
    UnknownRoomUseError,
)
from energytools.common.language import TrilingualText
from energytools.common.provenance import Provenance
from energytools.common.units import Quantity, Unit
from energytools.common.valuekind import ValueKind
from energytools.common.versioning import DatasetRelease

if TYPE_CHECKING:
    from energytools.dataset.compare import ProfileDiff

__all__ = [
    "ClimateStation",
    "Dataset",
    "Parameter",
    "ParameterValue",
    "RoomUse",
    "RoomUseProfile",
    "ValidationReport",
    "compute_package_checksum",
]

#: Allowed ``Parameter.data_type`` values (the workbook's cell types).
_DATA_TYPES = ("number", "enum", "text", "bool")

#: SIA room-use code pattern, e.g. ``"1.01"`` or ``"12.10"``.
_SIA_CODE_RE = re.compile(r"^\d{1,2}(\.\d{1,2})?$")

#: Canonical value-kind order = workbook column order (M/N/O of ``Datenblatt``).
_VALUE_KIND_ORDER = tuple(ValueKind)  # STANDARD, ZIELWERT, BESTAND


def _value_kind_names(value_kinds: frozenset[ValueKind]) -> list[str]:
    """Serialize value kinds in workbook column order (Standard, Zielwert, Bestand)."""
    return [kind.value for kind in _VALUE_KIND_ORDER if kind in value_kinds]


def compute_package_checksum(package: Mapping[str, Any]) -> str:
    """SHA-256 (hex) of the canonical package content.

    The declared ``release.checksum_sha256`` field is excluded from the hashed
    content (self-referential exclusion, the same trick git uses): a package
    can therefore truthfully declare its own checksum, and any modification of
    the payload — but not of the checksum field itself — is detected by
    :meth:`Dataset.validate`.

    Args:
        package: The package dict (the :meth:`Dataset.as_dict` shape).

    Returns:
        The 64-character hex digest.
    """
    copy_ = copy.deepcopy(dict(package))
    release = copy_.get("release")
    if isinstance(release, dict):
        release.pop("checksum_sha256", None)
    canonical = json.dumps(
        copy_, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RoomUse:
    """One of the 45 standard room uses (``Eingabedaten`` rows 9–53 of the workbook).

    Carries the numeric ``nutzid`` (1–45 — the workbook's selector value for
    ``Datenblatt!C1``), the SIA code (e.g. ``"1.01"``), the category
    (1 Wohnen … 12 Nebenräume) and the trilingual name.

    Args:
        nutzid: Numeric room-use id, 1–45.
        code: SIA code, e.g. ``"1.01"``.
        category: Room-use category, 1–12.
        name: Trilingual name (DE/FR/IT).
        sia_clause: SIA clause identifier, e.g. ``"1.1.1"``.

    Raises:
        ValueError: If ``nutzid`` is outside 1–45 or ``code`` is empty.
    """

    nutzid: int
    code: str
    category: int
    name: TrilingualText
    sia_clause: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.nutzid, bool) or not isinstance(self.nutzid, int):
            raise ValueError(f"nutzid must be an int (1–45), got {self.nutzid!r}")
        if not 1 <= self.nutzid <= 45:
            raise ValueError(f"nutzid {self.nutzid} outside 1–45")
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("room-use code must not be empty")
        if isinstance(self.category, bool) or not isinstance(self.category, int):
            raise ValueError(f"category must be an int (1–12), got {self.category!r}")
        if not 1 <= self.category <= 12:
            raise ValueError(f"category {self.category} outside 1–12")
        if not isinstance(self.name, TrilingualText):
            raise ValueError("name must be a TrilingualText")
        object.__setattr__(self, "code", self.code.strip())

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation."""
        return {
            "nutzid": self.nutzid,
            "code": self.code,
            "category": self.category,
            "name": self.name.as_dict(),
            "sia_clause": self.sia_clause,
        }


@dataclass(frozen=True)
class Parameter:
    """One data-sheet parameter (``Datenblatt`` rows 4–196 of the workbook).

    The stable id is the SIA clause number (e.g. ``"1.1.2.7"``
    Jahresgleichzeitigkeit) or a documented slug. Carries the trilingual label,
    symbol, unit, data type, category, the applicable value kinds and the
    observed export/display flags (workbook columns P–S).

    Args:
        id: Clause id or slug, e.g. ``"1.1.2.7"``.
        label: Trilingual label.
        symbol: Normalized symbol, e.g. ``"A_NGF"``.
        unit: A :class:`Unit` or a unit symbol parsed via :class:`Unit`.
        data_type: One of ``"number"``, ``"enum"``, ``"text"``, ``"bool"``.
        category: Parameter category, e.g. ``"Raum"``, ``"Lüftung"``.
        value_kinds: Value kinds the parameter is applicable to.
        export_flag: Workbook column P ("1" = export to results).
        display_flag: Workbook column Q.
        internal_heat_flag: Workbook column R.
        qhc_flag: Workbook column S.
        provenance: Optional provenance of the catalog entry.

    Raises:
        ValueError: If ``id`` is empty or ``data_type`` is unknown.
        UnitError: If ``unit`` is a string with an unknown unit symbol.
    """

    id: str
    label: TrilingualText
    symbol: str
    unit: Unit | str
    data_type: str
    category: str
    value_kinds: frozenset[ValueKind]
    export_flag: bool = True
    display_flag: bool = True
    internal_heat_flag: bool = False
    qhc_flag: bool = False
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("parameter id must not be empty")
        if self.data_type not in _DATA_TYPES:
            raise ValueError(
                f"parameter {self.id!r}: unknown data_type {self.data_type!r} "
                f"(expected one of {', '.join(_DATA_TYPES)})"
            )
        if not isinstance(self.label, TrilingualText):
            raise ValueError(f"parameter {self.id!r}: label must be a TrilingualText")
        if isinstance(self.unit, str):
            object.__setattr__(self, "unit", Unit(self.unit))
        if not isinstance(self.unit, Unit):
            raise ValueError(f"parameter {self.id!r}: unit must be a Unit or a unit string")
        object.__setattr__(self, "value_kinds", frozenset(self.value_kinds))
        object.__setattr__(self, "id", self.id.strip())

    @property
    def unit_symbol(self) -> str:
        """The normalized unit symbol, e.g. ``"W/m2"``."""
        unit = self.unit
        return unit.symbol if isinstance(unit, Unit) else Unit(unit).symbol

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation."""
        data: dict[str, Any] = {
            "id": self.id,
            "label": self.label.as_dict(),
            "symbol": self.symbol,
            "unit": self.unit_symbol,
            "data_type": self.data_type,
            "category": self.category,
            "value_kinds": _value_kind_names(self.value_kinds),
            "export_flag": self.export_flag,
            "display_flag": self.display_flag,
            "internal_heat_flag": self.internal_heat_flag,
            "qhc_flag": self.qhc_flag,
        }
        if self.provenance is not None:
            data["provenance"] = self.provenance.as_dict()
        return data


@dataclass(frozen=True)
class ParameterValue:
    """One value of one parameter in one value kind, with unit and provenance.

    Replaces the workbook's raw cell triple (columns M/N/O of ``Datenblatt``)
    by a typed object. ``value`` may be numeric, a string (enum/text
    parameters), a bool or ``None`` (missing/not-applicable).

    Args:
        parameter_id: The parameter id this value belongs to.
        kind: The :class:`ValueKind`.
        value: The value (``None`` marks a missing value).
        unit: A :class:`Unit` or a unit symbol.
        provenance: Optional provenance of the cell.

    Raises:
        UnitError: If ``unit`` is a string with an unknown unit symbol.
    """

    parameter_id: str
    kind: ValueKind
    value: float | int | str | bool | None
    unit: Unit | str
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ValueKind):
            raise ValueError(f"kind must be a ValueKind, got {self.kind!r}")
        if isinstance(self.unit, str):
            object.__setattr__(self, "unit", Unit(self.unit))
        if not isinstance(self.unit, Unit):
            raise ValueError("unit must be a Unit or a unit string")

    @property
    def unit_symbol(self) -> str:
        """The normalized unit symbol, e.g. ``"%"``."""
        unit = self.unit
        return unit.symbol if isinstance(unit, Unit) else Unit(unit).symbol

    @property
    def quantity(self) -> Quantity:
        """The value paired with its unit as a :class:`Quantity`.

        Only meaningful for numeric values: a string/bool value is not
        quantifiable and yields ``value=None`` (the raw value stays
        accessible via :attr:`value`).
        """
        if self.value is None or isinstance(self.value, (int, float)):
            return Quantity(self.value, self.unit)
        return Quantity(None, self.unit)

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready ``{"value": ..., "unit": ...}`` (+ ``provenance`` when set)."""
        data: dict[str, Any] = {"value": self.value, "unit": self.unit_symbol}
        if self.provenance is not None:
            data["provenance"] = self.provenance.as_dict()
        return data


@dataclass(frozen=True)
class RoomUseProfile:
    """The full parameter-value set of one room use, for all value kinds.

    The digital equivalent of the rendered ``Datenblatt`` sheet for one
    ``nutzid``. Immutable after construction; built by the loader / by
    :class:`Dataset`.

    Args:
        room_use: The :class:`RoomUse` this profile belongs to.
        values: Parameter id → value kind → :class:`ParameterValue`.
        parameter_catalog: Parameter id → :class:`Parameter` (the release
            catalog; order defines "sheet order").
        release_id: Release id (e.g. ``"V221"``), used for error messages.

    Raises:
        ValueError: If ``values`` references a parameter that is not in
            ``parameter_catalog`` (inconsistent catalog).
    """

    room_use: RoomUse
    values: Mapping[str, Mapping[ValueKind, ParameterValue]]
    parameter_catalog: Mapping[str, Parameter]
    release_id: str | None = None

    def __post_init__(self) -> None:
        catalog = dict(self.parameter_catalog)
        values: dict[str, dict[ValueKind, ParameterValue]] = {}
        for parameter_id, kinds in self.values.items():
            if parameter_id not in catalog:
                raise ValueError(
                    f"profile of room use {self.room_use.nutzid!r}: values reference "
                    f"unknown parameter {parameter_id!r}"
                )
            values[parameter_id] = dict(kinds)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "parameter_catalog", catalog)

    # -- data access ---------------------------------------------------------

    def value(
        self, parameter_id: str, kind: ValueKind = ValueKind.STANDARD
    ) -> ParameterValue:
        """Look up one parameter value.

        Args:
            parameter_id: Parameter (clause) id.
            kind: The value kind; defaults to ``STANDARD``.

        Returns:
            The stored :class:`ParameterValue`, or a ``value=None``
            :class:`ParameterValue` when the kind is not applicable / not
            recorded for the parameter.

        Raises:
            UnknownParameterError: If ``parameter_id`` is not part of the
                catalog.
        """
        if parameter_id not in self.parameter_catalog:
            raise UnknownParameterError(parameter_id, self.release_id or "")
        kinds = self.values.get(parameter_id)
        if kinds is None:
            kinds = {}
        stored = kinds.get(kind)
        if stored is not None:
            return stored
        return ParameterValue(
            parameter_id=parameter_id,
            kind=kind,
            value=None,
            unit=self.parameter_catalog[parameter_id].unit,
        )

    def parameters(self) -> list[Parameter]:
        """Catalog entries in sheet order."""
        return list(self.parameter_catalog.values())

    def to_frame(self, kind: ValueKind = ValueKind.STANDARD):
        """One pandas DataFrame row per parameter (id, label, symbol, unit, value).

        Requires the optional ``pandas`` dependency (the ``data`` extra).

        Args:
            kind: The value kind to materialize.

        Returns:
            A ``pandas.DataFrame`` with columns ``id``, ``label``, ``symbol``,
            ``unit``, ``value``.

        Raises:
            ImportError: If ``pandas`` is not installed.
        """
        try:
            import pandas as pd  # type: ignore[import-not-found, import-untyped]
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "RoomUseProfile.to_frame requires pandas; install the 'data' extra "
                "('pip install -e .[data]' or add pandas to the environment)"
            ) from exc
        rows = [
            {
                "id": parameter.id,
                "label": parameter.label.de,
                "symbol": parameter.symbol,
                "unit": parameter.unit_symbol,
                "value": self.value(parameter.id, kind).value,
            }
            for parameter in self.parameters()
        ]
        return pd.DataFrame(rows, columns=["id", "label", "symbol", "unit", "value"])

    def as_dict(self, kind: ValueKind | None = None) -> dict[str, Any]:
        """JSON-ready representation; ``kind=None`` includes all value kinds."""
        values: dict[str, Any] = {}
        for parameter_id, kinds in self.values.items():
            selected = {
                key.value: pv.as_dict()
                for key, pv in kinds.items()
                if kind is None or key is kind
            }
            values[parameter_id] = selected
        return {"room_use": self.room_use.as_dict(), "values": values}


@dataclass(frozen=True)
class ClimateStation:
    """One of the 40 climate stations (``Winter_Auslegung`` / ``Aug_Auslegung`` /
    ``Monatswerte`` sheets and ``Klimadaten`` in the Gebaeude-Tool).

    Carries winter/summer design values, monthly values and heating degree
    days as quantities.

    Args:
        id: Station id, 1–40.
        name: Trilingual station name, e.g. ``"Zürich-MeteoSchweiz"``.
        winter_design: Winter design quantities, e.g. ``{"t_a": Quantity(-8.0, "°C")}``.
        summer_design: Summer design quantities.
        monthly: Monthly values as quantities (simplified in this milestone;
            full 12-value :class:`MonthlyProfile` objects are a follow-up).
        hdd: Heating degree days (``None`` when not provided).
        provenance: Optional provenance.

    Raises:
        ValueError: If ``id`` is outside 1–40 or ``name`` is empty.
    """

    id: int
    name: TrilingualText
    winter_design: Mapping[str, Quantity]
    summer_design: Mapping[str, Quantity]
    monthly: Mapping[str, Quantity]
    hdd: Quantity | None = None
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int):
            raise ValueError(f"station id must be an int (1–40), got {self.id!r}")
        if not 1 <= self.id <= 40:
            raise ValueError(f"station id {self.id} outside 1–40")
        if not isinstance(self.name, TrilingualText) or not self.name.de.strip():
            raise ValueError("station name must not be empty")
        object.__setattr__(self, "winter_design", dict(self.winter_design))
        object.__setattr__(self, "summer_design", dict(self.summer_design))
        object.__setattr__(self, "monthly", dict(self.monthly))

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation."""
        return {
            "id": self.id,
            "name": self.name.as_dict(),
            "winter_design": {key: q.as_dict() for key, q in self.winter_design.items()},
            "summer_design": {key: q.as_dict() for key, q in self.summer_design.items()},
            "monthly": {key: q.as_dict() for key, q in self.monthly.items()},
            "hdd": self.hdd.as_dict() if self.hdd is not None else None,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Structured validation outcome of a :class:`Dataset`.

    Hard errors (``valid`` is ``False`` when any is present) and warnings
    (suspicious but acceptable). Same shape as the engine's report; the
    library-wide canonical type is planned for ``energytools.common``.
    """

    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """``True`` when there are no hard errors."""
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation."""
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Dataset:
    """One immutable dataset release: the canonical package plus release metadata.

    This is the data service's central object: a release id, the room-use
    catalog, the parameter catalog, the per-room-use profiles and the climate
    stations, plus the read-only query API (:meth:`list_room_uses`,
    :meth:`get_room_use_profile`, :meth:`compare_room_use_profiles`, ...),
    :meth:`validate` and the exports (:meth:`to_json`, :meth:`to_csv`).

    Args:
        release: Release metadata (:class:`DatasetRelease`).
        room_uses: Room uses in sheet order (nutzid order).
        parameters: Parameters in sheet order (``Datenblatt`` row order).
        profiles: Room use (by nutzid) → :class:`RoomUseProfile`.
        climate_stations: Climate stations.
        content_checksum_sha256: SHA-256 of the canonical package content,
            computed by the loader (checksum field excluded); ``None`` when
            the dataset was built in memory.

    Raises:
        ValueError: If a profile references a room use that is not in
            ``room_uses`` (inconsistent content).
    """

    release: DatasetRelease
    room_uses: tuple[RoomUse, ...]
    parameters: tuple[Parameter, ...]
    profiles: Mapping[int, RoomUseProfile]
    climate_stations: tuple[ClimateStation, ...]
    content_checksum_sha256: str | None = None

    def __post_init__(self) -> None:
        room_uses = tuple(self.room_uses)
        parameters = tuple(self.parameters)
        climate_stations = tuple(self.climate_stations)
        profiles = dict(self.profiles)
        object.__setattr__(self, "room_uses", room_uses)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "climate_stations", climate_stations)
        object.__setattr__(self, "profiles", profiles)
        known_nutzid = {room_use.nutzid for room_use in room_uses}
        for nutzid in profiles:
            if nutzid not in known_nutzid:
                raise ValueError(
                    f"profile for room use {nutzid!r} has no matching room use"
                )

    @property
    def release_id(self) -> str:
        """The release id, e.g. ``"V221"``."""
        return self.release.id

    # -- query API -----------------------------------------------------------

    def list_room_uses(self) -> list[RoomUse]:
        """All room uses in sheet order (nutzid 1–45)."""
        return list(self.room_uses)

    def room_use(self, room_use_id: int | str) -> RoomUse:
        """One room use by nutzid or SIA code.

        Raises:
            UnknownRoomUseError: If the id is not part of the release.
        """
        if isinstance(room_use_id, bool):
            raise UnknownRoomUseError(room_use_id, self.release.id)
        if isinstance(room_use_id, int):
            for room_use in self.room_uses:
                if room_use.nutzid == room_use_id:
                    return room_use
        elif isinstance(room_use_id, str):
            for room_use in self.room_uses:
                if room_use.code == room_use_id.strip():
                    return room_use
        raise UnknownRoomUseError(room_use_id, self.release.id)

    def get_room_use_profile(self, room_use_id: int | str) -> RoomUseProfile:
        """The full data-sheet profile of one room use.

        Raises:
            UnknownRoomUseError: If the id is not part of the release.
        """
        room_use = self.room_use(room_use_id)
        profile = self.profiles.get(room_use.nutzid)
        if profile is None:
            raise UnknownRoomUseError(room_use_id, self.release.id)
        return profile

    #: Alias for :meth:`get_room_use_profile` (doc part 03 §1.16 ``profile``).
    profile = get_room_use_profile

    def list_parameters(self) -> list[Parameter]:
        """The parameter catalog in sheet order (``Datenblatt`` rows)."""
        return list(self.parameters)

    def parameter(self, parameter_id: str) -> Parameter:
        """One parameter by clause id.

        Raises:
            UnknownParameterError: If the id is not part of the catalog.
        """
        for parameter in self.parameters:
            if parameter.id == parameter_id:
                return parameter
        raise UnknownParameterError(parameter_id, self.release.id)

    def get_parameter(self, clause_id: str) -> Parameter:
        """Alias of :meth:`parameter` (query-API name)."""
        return self.parameter(clause_id)

    def compare_room_use_profiles(self, a: int | str, b: int | str) -> ProfileDiff:
        """Compare two room-use profiles across all value kinds.

        Args:
            a: First room use (nutzid or SIA code).
            b: Second room use (nutzid or SIA code).

        Returns:
            A :class:`ProfileDiff` (structured: value kind, parameter,
            old/new values).

        Raises:
            UnknownRoomUseError: If either id is not part of the release.
            ValueError: If the profiles belong to different releases.
        """
        from energytools.dataset.compare import compare_profiles

        return compare_profiles(
            self.get_room_use_profile(a), self.get_room_use_profile(b)
        )

    def list_climate_stations(self) -> list[ClimateStation]:
        """All climate stations in id order."""
        return sorted(self.climate_stations, key=lambda station: station.id)

    def climate_station(self, station_id: int | str) -> ClimateStation:
        """One climate station by id.

        Raises:
            UnknownClimateStationError: If the id is not part of the release.
        """
        if isinstance(station_id, bool):
            raise UnknownClimateStationError(station_id, self.release.id)
        for station in self.climate_stations:
            if station.id == station_id:
                return station
            if isinstance(station_id, str) and station.name.de == station_id:
                return station
        raise UnknownClimateStationError(station_id, self.release.id)

    def get_release_info(self) -> dict[str, Any]:
        """Release metadata incl. checksums and table sizes (JSON-ready)."""
        release = self.release
        return {
            "id": release.id,
            "edition": release.edition,
            "publication_date": release.publication_date.isoformat(),
            "source_workbook": release.source_workbook,
            "extraction_tool_version": release.extraction_tool_version,
            "checksum_sha256": release.checksum_sha256,
            "content_checksum_sha256": self.content_checksum_sha256,
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
            "room_use_count": len(self.room_uses),
            "parameter_count": len(self.parameters),
            "profile_count": len(self.profiles),
            "climate_station_count": len(self.climate_stations),
        }

    # -- validation ----------------------------------------------------------

    def validate(self) -> ValidationReport:
        """Domain validation of the loaded release: report, not exception.

        Checks: duplicate room-use / parameter / station ids, room uses
        without a profile, empty parameter labels or symbols, parameters
        without applicable value kinds, profile values for a value kind the
        parameter does not support, value-unit mismatches, and release
        checksum format / integrity. Structural problems (missing fields,
        unknown unit symbols, unknown value-kind names in the file) are
        reported by the loader as :class:`ValidationError` with the same
        message vocabulary.

        Returns:
            A :class:`ValidationReport` with hard errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not self.room_uses:
            errors.append("package contains no room uses (expected the 45 standard room uses)")
        if not self.parameters:
            errors.append("package contains no parameters (expected the data-sheet catalog)")
        if not self.climate_stations:
            warnings.append("package contains no climate stations (expected 40 stations)")

        release = self.release
        if not _is_sha256_hex(release.checksum_sha256):
            errors.append(
                f"release checksum_sha256 is not a 64-char hex string "
                f"(got {release.checksum_sha256!r})"
            )
        elif (
            self.content_checksum_sha256 is not None
            and self.content_checksum_sha256.lower() != release.checksum_sha256.lower()
        ):
            warnings.append(
                f"release checksum_sha256 does not match the package content "
                f"(declared {release.checksum_sha256[:12]}…, computed "
                f"{self.content_checksum_sha256[:12]}…)"
            )

        seen_nutzid: set[int] = set()
        seen_code: set[str] = set()
        for room_use in self.room_uses:
            if room_use.nutzid in seen_nutzid:
                errors.append(f"duplicate room use nutzid {room_use.nutzid}")
            seen_nutzid.add(room_use.nutzid)
            if room_use.code in seen_code:
                errors.append(f"duplicate room use code {room_use.code!r}")
            seen_code.add(room_use.code)
            if not _matches_sia_code(room_use.code):
                warnings.append(f"room use {room_use.nutzid}: code {room_use.code!r} "
                                "does not match the SIA code pattern")

        seen_parameter: set[str] = set()
        for parameter in self.parameters:
            if parameter.id in seen_parameter:
                errors.append(f"duplicate parameter id {parameter.id!r}")
            seen_parameter.add(parameter.id)
            if not (parameter.label.de or parameter.label.fr or parameter.label.it):
                errors.append(f"parameter {parameter.id!r}: missing label (required)")
            if not parameter.symbol.strip():
                errors.append(f"parameter {parameter.id!r}: missing symbol (required)")
            if not parameter.value_kinds:
                errors.append(
                    f"parameter {parameter.id!r}: no applicable value kind "
                    "(expected at least one of Standard, Zielwert, Bestand)"
                )
            if not parameter.category.strip():
                warnings.append(f"parameter {parameter.id!r}: missing category")

        parameter_by_id = {parameter.id: parameter for parameter in self.parameters}
        for room_use in self.room_uses:
            profile = self.profiles.get(room_use.nutzid)
            if profile is None:
                errors.append(f"room use {room_use.nutzid} ({room_use.code}): no profile")
                continue
            for parameter_id, kinds in profile.values.items():
                catalog_parameter = parameter_by_id.get(parameter_id)
                if catalog_parameter is None:
                    # Unreachable via the public constructors; defensive.
                    errors.append(
                        f"profile of room use {room_use.nutzid}: unknown parameter "
                        f"{parameter_id!r}"
                    )
                    continue
                for kind, pv in kinds.items():
                    if kind not in catalog_parameter.value_kinds:
                        errors.append(
                            f"profile of room use {room_use.nutzid}, parameter "
                            f"{parameter_id!r}: value kind {kind.value!r} is not "
                            f"applicable to this parameter"
                        )
                    if pv.unit_symbol != catalog_parameter.unit_symbol:
                        warnings.append(
                            f"profile of room use {room_use.nutzid}, parameter "
                            f"{parameter_id!r}, kind {kind.value!r}: unit "
                            f"{pv.unit_symbol!r} differs from parameter unit "
                            f"{catalog_parameter.unit_symbol!r}"
                        )

        seen_station: set[int] = set()
        for station in self.climate_stations:
            if station.id in seen_station:
                errors.append(f"duplicate climate station id {station.id}")
            seen_station.add(station.id)

        return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))

    # -- export --------------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        """The canonical package dict (the shape the loader accepts back)."""
        return {
            "release": {
                "id": self.release.id,
                "edition": self.release.edition,
                "publication_date": self.release.publication_date.isoformat(),
                "checksum_sha256": self.release.checksum_sha256,
                "source_workbook": self.release.source_workbook,
                "extraction_tool_version": self.release.extraction_tool_version,
                "supersedes": self.release.supersedes,
                "changelog": [
                    {
                        "version": entry.version,
                        "date": entry.date.isoformat(),
                        "change": entry.change,
                        "migration": entry.migration,
                    }
                    for entry in self.release.changelog
                ],
            },
            "room_uses": [room_use.as_dict() for room_use in self.room_uses],
            "parameters": [parameter.as_dict() for parameter in self.parameters],
            "profiles": [
                {
                    "room_use_id": nutzid,
                    "values": {
                        parameter_id: {
                            kind.value: pv.as_dict() for kind, pv in kinds.items()
                        }
                        for parameter_id, kinds in profile.values.items()
                    },
                }
                for nutzid, profile in sorted(self.profiles.items())
            ],
            "climate_stations": [
                station.as_dict() for station in self.climate_stations
            ],
        }

    def to_json(self, target: str | Path | None = None) -> str:
        """Serialize the dataset as a JSON package string (optionally written out).

        The declared ``release.checksum_sha256`` is recomputed over the
        exported (canonical) content, so the exported package validates
        cleanly when loaded back (the checksum field itself is excluded from
        the hash).

        Args:
            target: Optional file path to write the package to.

        Returns:
            The JSON package text (indented, UTF-8 with umlauts preserved).

        Raises:
            OSError: If ``target`` cannot be written.
        """
        package = self.as_dict()
        package["release"]["checksum_sha256"] = compute_package_checksum(package)
        text = json.dumps(package, indent=2, ensure_ascii=False)
        if target is not None:
            Path(target).write_text(text, encoding="utf-8")
        return text

    def to_csv(self, scope: str, target: str | Path | None = None) -> str:
        """Export one table of the dataset as CSV.

        Args:
            scope: One of ``"room-uses"``, ``"parameters"``, ``"profiles"``,
                ``"climate"``.
            target: Optional file path to write the CSV to.

        Returns:
            The CSV text (UTF-8, ``\\n`` line terminator).

        Raises:
            ExportError: For an unsupported scope.
            OSError: If ``target`` cannot be written.

        Note:
            Excel (xlsx) export is a TODO for a later milestone
            (``energytools.export``, see docs/architecture+api-reference/05-export.md).
        """
        header, rows = _csv_table(self, scope)
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(header)
        writer.writerows([_csv_cell(cell) for cell in row] for row in rows)
        text = buffer.getvalue()
        if target is not None:
            Path(target).write_text(text, encoding="utf-8")
        return text


# ---------------------------------------------------------------------------
# CSV table writers
# ---------------------------------------------------------------------------

_CSV_SCOPES = ("room-uses", "parameters", "profiles", "climate")


def _csv_cell(value: Any) -> str:
    """Render one CSV cell (``None`` → empty string, bools as true/false)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _csv_table(dataset: Dataset, scope: str) -> tuple[list[str], list[list[Any]]]:
    """Build the header and rows of one CSV scope."""
    rows: list[list[Any]]
    if scope == "room-uses":
        header = ["nutzid", "code", "category", "name_de", "name_fr", "name_it", "sia_clause"]
        rows = [
            [
                room_use.nutzid,
                room_use.code,
                room_use.category,
                room_use.name.de,
                room_use.name.fr,
                room_use.name.it,
                room_use.sia_clause,
            ]
            for room_use in dataset.list_room_uses()
        ]
    elif scope == "parameters":
        header = [
            "id", "label_de", "label_fr", "label_it", "symbol", "unit", "data_type",
            "category", "value_kinds", "export_flag", "display_flag",
            "internal_heat_flag", "qhc_flag",
        ]
        rows = [
            [
                parameter.id,
                parameter.label.de,
                parameter.label.fr,
                parameter.label.it,
                parameter.symbol,
                parameter.unit_symbol,
                parameter.data_type,
                parameter.category,
                ";".join(_value_kind_names(parameter.value_kinds)),
                parameter.export_flag,
                parameter.display_flag,
                parameter.internal_heat_flag,
                parameter.qhc_flag,
            ]
            for parameter in dataset.list_parameters()
        ]
    elif scope == "profiles":
        header = ["room_use_id", "room_use_code", "parameter_id", "kind", "value", "unit"]
        rows = []
        for room_use in dataset.list_room_uses():
            profile = dataset.profiles.get(room_use.nutzid)
            if profile is None:
                continue
            for parameter_id, kinds in profile.values.items():
                for kind, pv in kinds.items():
                    rows.append(
                        [
                            room_use.nutzid,
                            room_use.code,
                            parameter_id,
                            kind.value,
                            pv.value,
                            pv.unit_symbol,
                        ]
                    )
    elif scope == "climate":
        header = [
            "station_id", "name_de", "name_fr", "name_it", "section", "key",
            "value", "unit",
        ]
        rows = []
        for station in dataset.list_climate_stations():
            for section in ("winter_design", "summer_design", "monthly"):
                for key, quantity in getattr(station, section).items():
                    rows.append(
                        [
                            station.id,
                            station.name.de,
                            station.name.fr,
                            station.name.it,
                            section,
                            key,
                            quantity.value,
                            quantity.unit.symbol,
                        ]
                    )
            if station.hdd is not None:
                rows.append(
                    [
                        station.id,
                        station.name.de,
                        station.name.fr,
                        station.name.it,
                        "hdd",
                        "hdd",
                        station.hdd.value,
                        station.hdd.unit.symbol,
                    ]
                )
    else:
        raise ExportError(
            f"unsupported CSV scope {scope!r} (expected one of {', '.join(_CSV_SCOPES)})",
            {"scope": scope, "supported": list(_CSV_SCOPES)},
        )
    return header, rows


def _is_sha256_hex(value: str) -> bool:
    """``True`` when ``value`` is a 64-character hex string (SHA-256 digest)."""
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _matches_sia_code(code: str) -> bool:
    """``True`` when ``code`` matches the SIA room-use code pattern (e.g. "1.01")."""
    return _SIA_CODE_RE.fullmatch(code) is not None
