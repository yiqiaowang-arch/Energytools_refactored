"""Domain model of the calculation engine: input, validation, versions.

Mirrors the target-state API reference
``docs/architecture+api-reference/04-gebaeude-engine.md`` §1 (building model,
there named ``BuildingProject`` and friends) and §2.2/§2.3 of the common
foundation (``ModelRelease``/``VersionInfo``, doc part 02). The German source
terminology of the workbook is kept verbatim — ``Gebäude``, ``Lüftung``,
``Erzeugung``, ``Resultate``, ``Nutzungsgrad``, Energieträger, Deckungsgrad,
Speicher-/Verteilverluste, Volllaststunden — so the port can be reviewed
against the VBA and the workbook sheets.

Units: areas in m², power densities in W/m², volume flows in m³/h, powers in
kW (the workbook's display units); the real ``energytools.common.units``
``Quantity`` replaces the plain floats in a later milestone.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from energytools.common.versioning import ModelRelease, VersionInfo
from energytools.engine.errors import UnknownValueKindError

_SIA_CODE_RE = re.compile(r"^\d{1,2}(\.\d{1,2})?$")
_LA_ID_RE = re.compile(r"^LA(0[1-9]|1[0-6])$")
_CATALOG_CODE_RE = re.compile(r"^(KE|WE|WW)\d{2,3}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([-+.][0-9A-Za-z.-]+)?$")

__all__ = [
    "BuildingInput",
    "EndUse",
    "EnergyCarrier",
    "GenerationSystem",
    "ModelRelease",
    "RoomRow",
    "ValidationReport",
    "ValueKind",
    "VentilationSystem",
    "VersionInfo",
]


class EnergyCarrier(Enum):
    """The Energieträger of the ``Resultate`` table (doc part 04 §1.1).

    Members are the workbook codes (``"el"``, ``"hel"``, ``"erdgas"``, ...);
    ``parse`` additionally accepts the German workbook labels (``"Elektrizität"``,
    ``"HEL"``, ``"Erdgas"``, ...).
    """

    ELECTRICITY = "el"
    HEATING_OIL = "hel"
    NATURAL_GAS = "erdgas"
    WOOD = "holz"
    DISTRICT_HEATING = "fernwaerme"
    DISTRICT_COOLING = "fernkaelte"
    SOLAR = "solar"
    OTHER = "andere"

    @classmethod
    def parse(cls, value: str) -> EnergyCarrier:
        """Parse a code or a German workbook label.

        Accepts the codes above (``"el"``, ``"hel"``, ...) and labels such as
        ``"Elektrizität"``, ``"HEL"``, ``"Erdgas"`` (case-insensitive, umlaut
        and transliterated forms).

        Raises:
            ValueError: for unknown values.
        """
        key = value.strip().casefold()
        try:
            return cls(key)
        except ValueError:
            pass
        try:
            return _ENERGY_CARRIER_GERMAN_LABELS[key]
        except KeyError as exc:
            raise ValueError(f"unknown Energieträger {value!r}") from exc


#: German workbook labels → member (module level: single-underscore names are
#: treated as enum members on Python 3.13+ and must not live in the class body).
_ENERGY_CARRIER_GERMAN_LABELS: dict[str, EnergyCarrier] = {
    "elektrizität": EnergyCarrier.ELECTRICITY,
    "elektrizitaet": EnergyCarrier.ELECTRICITY,
    "strom": EnergyCarrier.ELECTRICITY,
    "hel": EnergyCarrier.HEATING_OIL,
    "heizöl": EnergyCarrier.HEATING_OIL,
    "heizoel": EnergyCarrier.HEATING_OIL,
    "erdgas": EnergyCarrier.NATURAL_GAS,
    "holz": EnergyCarrier.WOOD,
    "fernwärme": EnergyCarrier.DISTRICT_HEATING,
    "fernwaerme": EnergyCarrier.DISTRICT_HEATING,
    "fernkälte": EnergyCarrier.DISTRICT_COOLING,
    "fernkaelte": EnergyCarrier.DISTRICT_COOLING,
    "solar": EnergyCarrier.SOLAR,
    "andere": EnergyCarrier.OTHER,
    "übrige": EnergyCarrier.OTHER,
    "uebrige": EnergyCarrier.OTHER,
}


class EndUse(Enum):
    """End-use categories of the ``Resultate`` table (doc part 04 §1.2).

    Allg. Gebäudetechnik, Geräte, Prozessanlagen, Beleuchtung, Lüftung,
    Kühlung, Heizung, Warmwasser.
    """

    ALLGEMEINE_GEBAEUDETECHNIK = "allg_gebaeudetechnik"
    GERAETE = "geraete"
    PROZESSANLAGEN = "prozessanlagen"
    BELEUCHTUNG = "beleuchtung"
    LUEFTUNG = "lueftung"
    KUEHLUNG = "kuehlung"
    HEIZUNG = "heizung"
    WARMWASSER = "warmwasser"

    @classmethod
    def parse(cls, value: str) -> EndUse:
        """Parse a code or a German workbook label (e.g. ``"Kühlung"``).

        Raises:
            ValueError: for unknown values.
        """
        key = value.strip().casefold()
        try:
            return cls(key)
        except ValueError:
            pass
        try:
            return _END_USE_GERMAN_LABELS[key]
        except KeyError as exc:
            raise ValueError(f"unknown Endenergieverbraucher {value!r}") from exc


#: German workbook labels → member (see note at ``_ENERGY_CARRIER_GERMAN_LABELS``).
_END_USE_GERMAN_LABELS: dict[str, EndUse] = {
    "allg. gebäudetechnik": EndUse.ALLGEMEINE_GEBAEUDETECHNIK,
    "allg. gebaeudetechnik": EndUse.ALLGEMEINE_GEBAEUDETECHNIK,
    "gebäudetechnik": EndUse.ALLGEMEINE_GEBAEUDETECHNIK,
    "geräte": EndUse.GERAETE,
    "geraete": EndUse.GERAETE,
    "prozessanlagen": EndUse.PROZESSANLAGEN,
    "beleuchtung": EndUse.BELEUCHTUNG,
    "lüftung": EndUse.LUEFTUNG,
    "lueftung": EndUse.LUEFTUNG,
    "kühlung": EndUse.KUEHLUNG,
    "kuehlung": EndUse.KUEHLUNG,
    "heizung": EndUse.HEIZUNG,
    "warmwasser": EndUse.WARMWASSER,
}


class ValueKind(Enum):
    """The three value kinds of the Raumdaten dataset (doc part 02 §5.1).

    Standard, Zielwert, Bestand — the M/N/O columns of the workbook's
    ``Datenblatt`` sheet.
    """

    STANDARD = "standard"
    ZIELWERT = "zielwert"
    BESTAND = "bestand"

    @classmethod
    def parse(cls, value: str) -> ValueKind:
        """Parse a value kind, case-insensitively.

        Accepts ``"standard"``, ``"zielwert"``, ``"bestand"`` and the aliases
        ``"target"`` / ``"existing"``.

        Raises:
            UnknownValueKindError: for anything else.
        """
        key = value.strip().casefold()
        try:
            return cls(key)
        except ValueError:
            pass
        aliases = {"target": cls.ZIELWERT, "existing": cls.BESTAND}
        if key in aliases:
            return aliases[key]
        raise UnknownValueKindError(
            f"unknown value kind {value!r} (expected standard, zielwert or bestand)"
        )


@dataclass(frozen=True)
class RoomRow:
    """One building room row of the ``Gebäude`` sheet (doc part 04 §1.3).

    Room use (nutzid or SIA code), EBF flag, NGF, share, per-use power
    densities for Geräte/Prozessanlagen/Beleuchtung, Lüftung system
    reference, and the Raumkühlung/Heizung/Warmwasser flags.
    """

    name: str
    room_use_id: int | str
    ebf: bool
    ngf: float
    share: float | None = None
    geraete: float | None = None
    prozessanlagen: float | None = None
    beleuchtung: float | None = None
    lueftung_system: str | None = None
    lueftung_volume_flow: float | None = None
    gekuehlt: bool = False
    beheizt: bool = True
    warmwasser: bool = False
    generations: tuple[GenerationSystem, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("room name must not be empty")
        for flag, value in (
            ("ebf", self.ebf),
            ("gekuehlt", self.gekuehlt),
            ("beheizt", self.beheizt),
            ("warmwasser", self.warmwasser),
        ):
            if not isinstance(value, bool):
                raise ValueError(f"room {self.name!r}: flag {flag!r} must be a bool")
        if self.ngf < 0:
            raise ValueError(f"room {self.name!r}: negative NGF {self.ngf}")
        if self.share is not None and self.share < 0:
            raise ValueError(f"room {self.name!r}: negative share {self.share}")
        for label, value in (
            ("geraete", self.geraete),
            ("prozessanlagen", self.prozessanlagen),
            ("beleuchtung", self.beleuchtung),
        ):
            if value is not None and value < 0:
                raise ValueError(f"room {self.name!r}: negative {label} {value}")
        if self.lueftung_volume_flow is not None and self.lueftung_volume_flow < 0:
            raise ValueError(
                f"room {self.name!r}: negative lueftung_volume_flow {self.lueftung_volume_flow}"
            )
        object.__setattr__(self, "generations", tuple(self.generations))

    def effective_area(self) -> float:
        """The area that counts: ``share × ngf`` when a share is set, else ``ngf`` (m²)."""
        if self.share is None:
            return self.ngf
        return self.share * self.ngf

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation (m², W/m², m³/h)."""
        return {
            "name": self.name,
            "room_use_id": self.room_use_id,
            "ebf": self.ebf,
            "ngf": self.ngf,
            "share": self.share,
            "geraete": self.geraete,
            "prozessanlagen": self.prozessanlagen,
            "beleuchtung": self.beleuchtung,
            "lueftung_system": self.lueftung_system,
            "lueftung_volume_flow": self.lueftung_volume_flow,
            "gekuehlt": self.gekuehlt,
            "beheizt": self.beheizt,
            "warmwasser": self.warmwasser,
            "generations": [generation.as_dict() for generation in self.generations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoomRow:
        """Reconstruct from :meth:`as_dict` output."""
        generations = tuple(
            GenerationSystem.from_dict(item) for item in data.get("generations", [])
        )
        return cls(**{key: value for key, value in data.items() if key != "generations"}, generations=generations)


@dataclass(frozen=True)
class VentilationSystem:
    """One of the 16 ventilation systems LA01–LA16 of the ``Lüftung`` sheet (doc part 04 §1.4).

    Volume flows (Standard/Prozess/Projekt), SFP, fan power, regulation,
    full-load hours (Volllaststunden), WRG recovery ratio, and the
    Kühlfall/Heizfall setpoints.
    """

    id: str
    room_use: str | None = None
    volume_flow_standard: float | None = None
    volume_flow_prozess: float | None = None
    volume_flow_projekt: float | None = None
    sfp: float | None = None
    fan_power: float | None = None
    regulation: str | None = None
    full_load_hours: float | None = None
    wrg: float | None = None
    kuehlfall_t: float | None = None
    heizfall_t: float | None = None
    humidity_setpoints: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("ventilation system id must not be empty")
        if self.wrg is not None and not 0 <= self.wrg <= 1:
            raise ValueError(
                f"system {self.id!r}: WRG recovery ratio {self.wrg} outside 0–1"
            )
        if self.regulation is not None and self.regulation not in (
            "1-stufig",
            "2-stufig",
            "stufenlos",
        ):
            raise ValueError(
                f"system {self.id!r}: unknown Regelung {self.regulation!r} "
                "(expected 1-stufig, 2-stufig or stufenlos)"
            )
        for label, value in (
            ("volume_flow_standard", self.volume_flow_standard),
            ("volume_flow_prozess", self.volume_flow_prozess),
            ("volume_flow_projekt", self.volume_flow_projekt),
            ("sfp", self.sfp),
            ("fan_power", self.fan_power),
            ("full_load_hours", self.full_load_hours),
        ):
            if value is not None and value < 0:
                raise ValueError(f"system {self.id!r}: negative {label} {value}")
        if self.humidity_setpoints is not None:
            setpoints = dict(self.humidity_setpoints)
            for key, value in setpoints.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(
                        f"system {self.id!r}: humidity setpoint {key!r} must be numeric"
                    )
            object.__setattr__(self, "humidity_setpoints", setpoints)

    def effective_volume_flow(self) -> float | None:
        """The flow that applies: Projekt → Prozess → Standard priority (m³/h)."""
        for value in (
            self.volume_flow_projekt,
            self.volume_flow_prozess,
            self.volume_flow_standard,
        ):
            if value is not None:
                return value
        return None

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation (m³/h, W/(m³/h), kW, h/a)."""
        return {
            "id": self.id,
            "room_use": self.room_use,
            "volume_flow_standard": self.volume_flow_standard,
            "volume_flow_prozess": self.volume_flow_prozess,
            "volume_flow_projekt": self.volume_flow_projekt,
            "sfp": self.sfp,
            "fan_power": self.fan_power,
            "regulation": self.regulation,
            "full_load_hours": self.full_load_hours,
            "wrg": self.wrg,
            "kuehlfall_t": self.kuehlfall_t,
            "heizfall_t": self.heizfall_t,
            "humidity_setpoints": dict(self.humidity_setpoints)
            if self.humidity_setpoints is not None
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VentilationSystem:
        """Reconstruct from :meth:`as_dict` output."""
        return cls(**data)


@dataclass(frozen=True)
class GenerationSystem:
    """One generator of the ``Erzeugung`` sheet (doc part 04 §1.5).

    The workbook distinguishes 3 Kälteerzeuger + 3 Wärmeerzeuger + 3
    Warmwassererzeuger; each carries a catalog code (resolved via the
    ``Nutzungsgrad`` catalog in a later milestone), Deckungsgrad,
    Speicher-/Verteilverluste and a nominal power.
    """

    id: str
    kind: str
    catalog_code: str
    coverage: float
    losses: float
    nominal_power: float | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("generation system id must not be empty")
        if self.kind not in ("cooling", "heating", "ww"):
            raise ValueError(
                f"system {self.id!r}: unknown kind {self.kind!r} "
                "(expected cooling, heating or ww)"
            )
        if not self.catalog_code.strip():
            raise ValueError(f"system {self.id!r}: catalog_code must not be empty")
        if not 0 <= self.coverage <= 1:
            raise ValueError(
                f"system {self.id!r}: Deckungsgrad {self.coverage} outside 0–1"
            )
        if not 0 <= self.losses <= 1:
            raise ValueError(
                f"system {self.id!r}: Speicher-/Verteilverluste {self.losses} outside 0–1"
            )
        if self.nominal_power is not None and self.nominal_power < 0:
            raise ValueError(f"system {self.id!r}: negative nominal_power {self.nominal_power}")

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation (kW)."""
        return {
            "id": self.id,
            "kind": self.kind,
            "catalog_code": self.catalog_code,
            "coverage": self.coverage,
            "losses": self.losses,
            "nominal_power": self.nominal_power,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationSystem:
        """Reconstruct from :meth:`as_dict` output."""
        return cls(**data)


@dataclass(frozen=True)
class ValidationReport:
    """Structured validation outcome (doc part 04 §1.10).

    Hard errors (invalid) and warnings (suspicious but acceptable). Used by
    input validation and backend capability validation alike.
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
class BuildingInput:
    """The complete, validated calculation input (doc part 04 §1.6, ``BuildingProject``).

    Project header, climate station, value kind, room rows, ventilation
    systems and generation systems — the request body of ``POST /calculations``.
    """

    name: str
    rooms: tuple[RoomRow, ...]
    author: str | None = None
    date: date | None = None
    climate_station_id: int = 1
    value_kind: ValueKind = ValueKind.STANDARD
    ventilation: tuple[VentilationSystem, ...] = ()
    generation: tuple[GenerationSystem, ...] = ()
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("building input name must not be empty")
        rooms = tuple(self.rooms)
        if not rooms:
            raise ValueError("building input must contain at least one room")
        object.__setattr__(self, "rooms", rooms)
        object.__setattr__(self, "ventilation", tuple(self.ventilation))
        object.__setattr__(self, "generation", tuple(self.generation))
        if isinstance(self.value_kind, str):
            object.__setattr__(self, "value_kind", ValueKind.parse(self.value_kind))
        if isinstance(self.climate_station_id, bool) or not isinstance(
            self.climate_station_id, int
        ):
            raise ValueError("climate_station_id must be an int (1–40)")

    # -- validation ---------------------------------------------------------

    def validate(self) -> ValidationReport:
        """Domain validation: report, not exception.

        Checks: climate station 1–40, room uses known (nutzid 1–45 or SIA
        code), ventilation systems in LA01–LA16, no duplicate system ids,
        rooms referencing known Lüftung systems. The GenerationCatalog
        lookup (catalog codes KE/WE/WW) arrives with the dataset milestone;
        non-matching codes are reported as warnings here.

        Returns:
            ValidationReport with hard errors and warnings.
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not 1 <= self.climate_station_id <= 40:
            errors.append(f"climate_station_id {self.climate_station_id} outside 1–40")

        seen_room_names: set[str] = set()
        for room in self.rooms:
            if room.name in seen_room_names:
                warnings.append(f"duplicate room name {room.name!r}")
            seen_room_names.add(room.name)
            if not self._room_use_known(room.room_use_id):
                errors.append(
                    f"room {room.name!r}: unknown room use {room.room_use_id!r} "
                    "(expected nutzid 1–45 or SIA code like '1.01')"
                )
            if room.share is not None and room.share > 1:
                warnings.append(f"room {room.name!r}: share {room.share} > 1 (suspicious)")

        seen_la: set[str] = set()
        for system in self.ventilation:
            if not _LA_ID_RE.fullmatch(system.id):
                errors.append(f"ventilation system id {system.id!r} not in LA01–LA16")
            if system.id in seen_la:
                errors.append(f"duplicate ventilation system id {system.id!r}")
            seen_la.add(system.id)

        defined_la = {system.id for system in self.ventilation}
        for room in self.rooms:
            if room.lueftung_system is None:
                continue
            if not _LA_ID_RE.fullmatch(room.lueftung_system):
                errors.append(
                    f"room {room.name!r}: Lüftung system {room.lueftung_system!r} "
                    "not in LA01–LA16"
                )
            elif room.lueftung_system not in defined_la:
                warnings.append(
                    f"room {room.name!r}: Lüftung system {room.lueftung_system!r} "
                    "not defined in ventilation"
                )

        seen_generation: set[str] = set()
        for system in self.generation:
            if system.id in seen_generation:
                warnings.append(f"duplicate generation system id {system.id!r}")
            seen_generation.add(system.id)
            if not _CATALOG_CODE_RE.fullmatch(system.catalog_code):
                warnings.append(
                    f"generation system {system.id!r}: catalog code "
                    f"{system.catalog_code!r} does not match the KE/WE/WW pattern "
                    "(catalog lookup not available in this milestone)"
                )

        return ValidationReport(errors=tuple(errors), warnings=tuple(warnings))

    @staticmethod
    def _room_use_known(room_use_id: int | str) -> bool:
        if isinstance(room_use_id, bool):
            return False
        if isinstance(room_use_id, int):
            return 1 <= room_use_id <= 45
        if isinstance(room_use_id, str):
            return bool(_SIA_CODE_RE.fullmatch(room_use_id.strip()))
        return False

    # -- derived values -----------------------------------------------------

    def total_ngf(self) -> float:
        """Sum of the effective room areas (m²)."""
        return sum(room.effective_area() for room in self.rooms)

    def total_ebf_area(self) -> float:
        """Sum of the effective areas of rooms counted toward the EBF (m²)."""
        return sum(room.effective_area() for room in self.rooms if room.ebf)

    # -- serialization ------------------------------------------------------

    def canonical_json(self) -> str:
        """Deterministic JSON of the input (sorted keys, no whitespace, ASCII).

        Basis of the ``inputs_hash``: identical inputs produce identical
        strings on every platform.
        """
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def inputs_hash(self) -> str:
        """SHA-256 of the canonical input JSON (hex)."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation."""
        return {
            "name": self.name,
            "author": self.author,
            "date": self.date.isoformat() if self.date is not None else None,
            "climate_station_id": self.climate_station_id,
            "value_kind": self.value_kind.value,
            "rooms": [room.as_dict() for room in self.rooms],
            "ventilation": [system.as_dict() for system in self.ventilation],
            "generation": [system.as_dict() for system in self.generation],
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuildingInput:
        """Reconstruct from :meth:`as_dict` output."""
        return cls(
            name=data["name"],
            author=data.get("author"),
            date=date.fromisoformat(data["date"]) if data.get("date") else None,
            climate_station_id=data["climate_station_id"],
            value_kind=ValueKind.parse(data["value_kind"]),
            rooms=tuple(RoomRow.from_dict(room) for room in data["rooms"]),
            ventilation=tuple(
                VentilationSystem.from_dict(system) for system in data["ventilation"]
            ),
            generation=tuple(
                GenerationSystem.from_dict(system) for system in data["generation"]
            ),
            note=data.get("note"),
        )
