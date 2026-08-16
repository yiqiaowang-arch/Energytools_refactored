"""Building — the house itself: rooms, climate, standard, lazy loads.

The :class:`Building` is the root of the object model.  It owns its rooms
and its building-level generators, knows its climate and standard value
kind, and provides ``area`` and the lazy :attr:`load` (recomputed
automatically when anything changes — rooms, schedules, ventilation or
generation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from energytools.building.climate import Climate
from energytools.building.generation import Generation
from energytools.building.load import Load, LoadCategory
from energytools.building.room import Room
from energytools.building.schedules import Schedule

_STANDARD_KINDS = {"standard": "standard", "zielwert": "zielwert", "bestand": "bestand"}
_CATALOG_KIND = {"KE": "cooling", "WE": "heating", "W": "ww"}


@dataclass(frozen=True)
class Area:
    """The areas of the building (m²)."""

    ngf: float  #: Net floor area (NGF)
    ebf: float  #: Heated envelope area (EBF)
    gf: float  #: Gross floor area (GF)

    def __repr__(self) -> str:
        return f"Area(ngf={self.ngf:.0f}, ebf={self.ebf:.0f}, gf={self.gf:.0f})"


class Building:
    """A building.

    Args:
        name: Building name.
        climate: The :class:`Climate` of the location.
        standard: Value kind of the SIA 2024 tables — ``"standard"``
            (default), ``"zielwert"`` or ``"bestand"``.
        dataset: The dataset release; taken from the climate when omitted.
    """

    def __init__(
        self,
        name: str,
        climate: Climate,
        standard: str = "standard",
        dataset: Any = None,
    ) -> None:
        if not name.strip():
            raise ValueError("building name must not be empty")
        if standard not in _STANDARD_KINDS:
            raise ValueError(
                f"unknown standard {standard!r} (expected standard, zielwert or bestand)"
            )
        self.name = name
        self.climate = climate
        self.standard = standard
        self._dataset = dataset if dataset is not None else climate._dataset
        self._rooms: list[Room] = []
        self._generations: list[Generation] = []
        self._load: Load | None = None
        self._fingerprint: tuple[Any, ...] | None = None

    # -- rooms --------------------------------------------------------------

    def add_room(self, room: Room) -> None:
        """Add a room; its changes invalidate the lazy load."""
        if any(existing.name == room.name for existing in self._rooms):
            raise ValueError(f"duplicate room name {room.name!r}")
        room._on_change = self._invalidate
        self._rooms.append(room)
        self._invalidate()

    def room(self, name: str) -> Room:
        """The room of the given name.

        Raises:
            KeyError: for an unknown room name.
        """
        for room in self._rooms:
            if room.name == name:
                return room
        raise KeyError(f"no room named {name!r}")

    @property
    def rooms(self) -> tuple[Room, ...]:
        """The rooms in insertion order."""
        return tuple(self._rooms)

    # -- generation ---------------------------------------------------------

    def add_generation(self, generation: Generation) -> None:
        """Add a building-level generator."""
        self._generations.append(generation)
        self._invalidate()

    @property
    def generations(self) -> tuple[Generation, ...]:
        """The building-level generators."""
        return tuple(self._generations)

    # -- areas --------------------------------------------------------------

    @property
    def area(self) -> Area:
        """The areas of the building (m²): NGF, EBF, GF."""
        ngf = sum(room.area for room in self._rooms)
        ebf = sum(room.area for room in self._rooms if room.ebf)
        return Area(ngf=ngf, ebf=ebf, gf=ebf * 1.1)

    # -- lazy load ----------------------------------------------------------

    @property
    def load(self) -> Load:
        """The calculation result, computed lazily and cached.

        Any change to rooms, schedules, ventilation or generation
        invalidates the cache; the next access recomputes.
        """
        fingerprint = self._schedules_fingerprint()
        if self._load is None or fingerprint != self._fingerprint:
            self._load = self._compute_load()
            self._fingerprint = fingerprint
        return self._load

    def _invalidate(self) -> None:
        self._load = None
        self._fingerprint = None

    def _schedules_fingerprint(self) -> tuple[Any, ...]:
        def axis(schedule: Schedule) -> tuple[Any, ...]:
            return (tuple(schedule.hourly), tuple(schedule.weekly), tuple(schedule.monthly))

        return tuple(
            (room.name, axis(room.schedules.occupancy), axis(room.schedules.device),
             axis(room.schedules.lighting), room.area, room.ebf)
            for room in self._rooms
        )

    # -- calculation --------------------------------------------------------

    def _compile(self) -> Any:
        """Compile the object graph into the engine's BuildingInput."""
        from energytools.engine.model import (
            BuildingInput,
            GenerationSystem,
            RoomRow,
            ValueKind,
            VentilationSystem,
        )

        rooms = []
        ventilation = []
        la_counter = 0
        for room in self._rooms:
            generations = tuple(
                GenerationSystem(
                    id=f"{room.name}-{generation.catalog_code}",
                    kind=generation.kind or _catalog_kind(generation.catalog_code),
                    catalog_code=generation.catalog_code,
                    coverage=generation.coverage,
                    losses=generation.losses,
                )
                for generation in room._generations
            )
            system_id = None
            if room.ventilation is not None:
                la_counter += 1
                system_id = f"LA{la_counter:02d}"
            rooms.append(
                RoomRow(
                    name=room.name,
                    room_use_id=room.type.code,
                    ebf=room.ebf,
                    ngf=room.area,
                    lueftung_system=system_id,
                    lueftung_volume_flow=(
                        room.ventilation.volume_flow if room.ventilation is not None else None
                    ),
                    gekuehlt=room.conditioned,
                    beheizt=room.heated,
                    warmwasser=room.warm_water,
                    generations=generations,
                )
            )
            if room.ventilation is not None:
                ventilation.append(
                    VentilationSystem(
                        id=system_id,
                        room_use=room.type.code,
                        volume_flow_standard=room.ventilation.volume_flow,
                        sfp=room.ventilation.sfp,
                        fan_power=room.ventilation.fan_power,
                        regulation=room.ventilation.regulation,
                        full_load_hours=room.ventilation.full_load_hours,
                        wrg=room.ventilation.wrg,
                        kuehlfall_t=room.ventilation.kuehlfall_t,
                        heizfall_t=room.ventilation.heizfall_t,
                    )
                )
        generation = tuple(
            GenerationSystem(
                id=f"{self.name}-{generation.catalog_code}",
                kind=generation.kind or _catalog_kind(generation.catalog_code),
                catalog_code=generation.catalog_code,
                coverage=generation.coverage,
                losses=generation.losses,
            )
            for generation in self._generations
        )
        return BuildingInput(
            name=self.name,
            rooms=tuple(rooms),
            climate_station_id=self.climate.station_id,
            value_kind=ValueKind.parse(self.standard),
            ventilation=tuple(ventilation),
            generation=generation,
        )

    def _compute_load(self) -> Load:
        from energytools.engine import Engine, NativeBackend

        building_input = self._compile()
        results = Engine().calculate(
            building_input,
            self._dataset.release.id,
            "1.0.0",
            backend=NativeBackend(dataset_dir=self._dataset_dir()),
        )
        per_room = results.per_room
        by_name = {room.name: room for room in self._rooms}

        heating = LoadCategory(
            "heating",
            {name: row["heizung_mwh"] for name, row in per_room.items()},
            {
                name: _hourly_series(
                    row["heizung_mwh"],
                    by_name[name].schedules.occupancy,
                    temperature_weight=self.climate.monthly_temperature(),
                    heating=True,
                )
                for name, row in per_room.items()
            },
        )
        cooling = LoadCategory(
            "cooling",
            {name: row["kuehlung_mwh"] for name, row in per_room.items()},
            {
                name: _hourly_series(
                    row["kuehlung_mwh"],
                    by_name[name].schedules.occupancy,
                    temperature_weight=self.climate.monthly_temperature(),
                    heating=False,
                )
                for name, row in per_room.items()
            },
        )
        ww = LoadCategory(
            "ww",
            {name: row["warmwasser_mwh"] for name, row in per_room.items()},
            {
                name: _hourly_series(
                    row["warmwasser_mwh"],
                    by_name[name].schedules.occupancy,
                )
                for name, row in per_room.items()
            },
        )
        electricity = LoadCategory(
            "electricity",
            {
                name: row["geraete_mwh"] + row["beleuchtung_mwh"] + row["lueftung_mwh"]
                for name, row in per_room.items()
            },
            {
                name: _combined_hourly(
                    geraete=row["geraete_mwh"],
                    beleuchtung=row["beleuchtung_mwh"],
                    lueftung=row["lueftung_mwh"],
                    occupancy=by_name[name].schedules.occupancy,
                    lighting=by_name[name].schedules.lighting,
                )
                for name, row in per_room.items()
            },
        )
        return Load(
            heating=heating,
            cooling=cooling,
            ww=ww,
            electricity=electricity,
            totals=results.per_carrier,
            end_energy={
                "heating": results.totals["heizung_endenergie_mwh"],
                "cooling": results.totals["kuehlung_endenergie_mwh"],
                "ww": results.totals["warmwasser_endenergie_mwh"],
            },
        )

    def _dataset_dir(self) -> str:
        import os

        from energytools.raumdaten.dataset import default_dataset_dir

        return os.environ.get("ENERGYTOOLS_DATASET_DIR", default_dataset_dir())


def _catalog_kind(code: str) -> str:
    for prefix, kind in _CATALOG_KIND.items():
        if code.startswith(prefix):
            return kind
    raise ValueError(f"cannot infer the kind of catalogue code {code!r} (use KE/WE/W...)")


def _temperature_weight(monthly_temperature: tuple[float, ...], heating: bool) -> list[float]:
    """Monthly heating/cooling weights from the station's monthly temperatures."""
    if heating:
        return [max(0.0, 15.0 - temperature) for temperature in monthly_temperature]
    return [max(0.0, temperature - 18.0) for temperature in monthly_temperature]


def _hourly_series(
    annual_mwh: float,
    schedule: Schedule,
    temperature_weight: tuple[float, ...] | None = None,
    heating: bool = True,
) -> list[float]:
    """Distribute the annual MWh over 8760 h using the room's schedule.

    ``hour * week * month`` with the monthly axis weighted by the station
    temperature for heating/cooling; normalized so the sum equals the
    annual value.
    """
    hours = 8760
    distribution = schedule.yearly_distribution()
    if temperature_weight is not None:
        weights = _temperature_weight(temperature_weight, heating)
        monthly = schedule.monthly
        base = [0.0] * hours
        day_of_year = 0
        for month, days in enumerate((31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)):
            for day in range(days):
                weekday = day_of_year % 7
                for hour in range(24):
                    base[day_of_year * 24 + hour] = (
                        schedule.hourly[hour]
                        * schedule.weekly[weekday]
                        * monthly[month]
                        * weights[month]
                    )
                day_of_year += 1
        total = sum(base)
        distribution = [value / total if total > 0 else 0.0 for value in base]
    return [value * annual_mwh for value in distribution]


def _combined_hourly(
    geraete: float,
    beleuchtung: float,
    lueftung: float,
    occupancy: Schedule,
    lighting: Schedule,
) -> list[float]:
    """Electricity: device + lighting + fan loads on their own schedules."""
    series = [0.0] * 8760
    for annual, schedule in (
        (geraete, occupancy),
        (beleuchtung, lighting),
        (lueftung, occupancy),
    ):
        hourly = _hourly_series(annual, schedule)
        for index in range(8760):
            series[index] += hourly[index]
    return series
