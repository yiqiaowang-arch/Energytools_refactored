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

    # -- design-day balances (Wärmebilanz / Stoffbilanz) --------------------

    def design_day(self, room: Room, month: int = 8) -> Any:
        """The 24 h summer design-day heat balance of a room.

        Reproduces the workbook's ``Wärmebilanz - Sommertag`` block
        (:func:`energytools.engine.native.summer_balance.summer_balance_24h`)
        from the dataset: the room's type parameters (persons/devices/
        process/lighting gains, g/gtot, Glasflächenzahl, Raumtemperatur,
        hygienic fresh air, infiltration, WRG temperature change), the
        room's editable schedules and the station's August design day.

        Args:
            room: The room.
            month: Design-day month (6 or 8; 8 = the workbook's cooling
                design day).
        """
        from energytools.engine.native.summer_balance import summer_balance_24h

        inputs = self._balance_inputs(room)
        station = self.climate._dataset.climate().station(self.climate.station_id)
        design = next(d for d in station.design_days if d.month == month)
        lighting = next(
            p.values for p in self._dataset.hourly_profiles if p.id == "beleuchtung_sommer"
        )
        # the ventilation stage curve follows the 1.1.5.5 control mode
        # (IDA-C3 -> einstufig, IDA-C4 -> zweistufig, else stufenlos)
        mode = self._balance_inputs(room).get("ventilation_mode") or "einstufig"
        stage_curve = {
            "einstufig": "lueftung_einstufig",
            "zweistufig": "lueftung_zweistufig",
            "stufenlos": "lueftung_stufenlos",
        }[mode]
        ventilation_curve = next(
            p.values for p in self._dataset.hourly_profiles if p.id == stage_curve
        )
        return summer_balance_24h(
            person_wm2=inputs["person_wm2"],
            device_wm2=inputs["device_wm2"],
            process_wm2=inputs["process_wm2"],
            lighting_wm2=inputs["lighting_wm2"],
            g_value=inputs["g_value"],
            g_total=inputs["g_total"],
            glasflaechenzahl=inputs["glasflaechenzahl"],
            room_temp=inputs["room_temp"],
            air_volume=inputs["air_volume"],
            infiltration=inputs["infiltration"],
            supply_temp=None,
            supply_coeff=inputs["supply_coeff"],
            transmission_coeff=inputs["transmission_coeff"],
            occupancy=tuple(room.schedules.occupancy),
            device_curve=tuple(room.schedules.device),
            lighting_curve=tuple(lighting),
            ventilation_curve=tuple(ventilation_curve),
            radiation=tuple(design.radiation),
            outdoor_temp=tuple(design.temperature),
        )

    def air_quality(self, room: Room, month: int = 2) -> Any:
        """The 24 h CO₂/moisture balance of a room (Stoffbilanz-Arbeitstag).

        Reproduces the workbook's ``Stoffbilanz`` block
        (:func:`energytools.engine.native.stoffbilanz.stoffbilanz_24h`) from
        the dataset: the room's type parameters (person area, NGF, room
        height, CO₂ rate, moisture sources), the SIA 2028 monthly reference
        and the ventilation flow of the design-day balance.

        Args:
            room: The room.
            month: SIA 2028 month index 0-11 (2 = March, the workbook's
                current month cell).
        """
        from energytools.engine.native.stoffbilanz import stoffbilanz_24h

        inputs = self._balance_inputs(room)
        sia = self._dataset.sia2028_monthly
        if sia is None:
            raise ValueError("dataset has no SIA 2028 monthly reference")
        flow = [
            row.air_volume + row.infiltration for row in self.design_day(room)
        ]
        return stoffbilanz_24h(
            person_area=inputs["person_area"],
            ngf=inputs["ngf"],
            room_height=inputs["room_height"],
            co2_rate=inputs["co2_rate"],
            person_moisture=inputs["person_moisture"],
            other_moisture=inputs["other_moisture"],
            air_pressure=inputs["air_pressure"],
            monthly_temperature=tuple(sia.temperature),
            monthly_humidity=tuple(sia.relative_humidity),
            monthly_room_temp=tuple(sia.room_temperature),
            month_index=month,
            occupancy=tuple(room.schedules.occupancy),
            ventilation_flow=tuple(flow),
            start_co2=inputs["start_co2"],
            start_moisture=inputs["start_moisture"],
        )

    def _balance_inputs(self, room: Room) -> dict:
        """The dataset parameter values behind the design-day balances.

        The mapping mirrors the workbook's Datenblatt cell chain: gains per
        m² from the type parameters, the Glasflächenzahl from Glasanteil /
        Abminderungsfaktor × hR/dR and the transmission coefficient from
        the U-values and the window fraction (Datenblatt M95/M173).  All
        parameters are read in the building's value kind
        (standard/zielwert/bestand), like the workbook's M/N/O columns.
        """
        type_ = room.type
        kind = self.standard
        p = type_.parameter

        def pv(pid: str) -> float | None:
            """Value of the kind, falling back to Standard like the workbook's
            N = M cell references (e.g. N133 = M133)."""
            return p(pid, kind) if p(pid, kind) is not None else p(pid, "standard")

        inputs = self._dataset.inputs[type_.nutzid]
        person_area = pv("1.1.2.9") or 0.0
        ngf = room.area
        return {
            "person_wm2": (
                (inputs.sensible_waerme_kuehlfall or 0.0) / person_area
                if person_area else 0.0
            ),
            "device_wm2": pv("1.1.3.6") or 0.0,
            "process_wm2": 0.0,
            "lighting_wm2": pv("1.1.4.10") or 0.0,
            "g_value": pv("g") or 0.0,
            "g_total": pv("gtot") or 0.0,
            "glasflaechenzahl": (pv("1.1.1.3") or 0.0) / 100.0 / 0.85
            * (p("hR") or 0.0) / (p("dR") or 1.0),
            "room_temp": pv("1.1.1.12.C") or 26.0,
            "air_volume": pv("1.1.5.2") or 0.0,
            "infiltration": pv("1.1.5.4") or 0.0,
            # The Bestand block reads the WRG temperature change from the
            # Bestand matrix (M196 = O139); an absent Bestand value is 0,
            # not a Standard fallback (the workbook has no N = M style
            # reference here).
            "supply_coeff": (
                pv("1.1.5.6") if self.standard != "bestand" else (p("1.1.5.6", "bestand") or 0.0)
            ),
            "ventilation_mode": self._ventilation_mode(p, kind),
            "transmission_coeff": self._transmission_coeff(type_, p, ngf, kind),
            "person_area": person_area,
            "ngf": ngf,
            "room_height": pv("hR") or 2.5,
            "co2_rate": 1.2,
            "person_moisture": 66.0,
            "other_moisture": pv("1.1.2.15") or 0.0,
            "air_pressure": self._air_pressure(),
            "start_co2": 400.0,
            "start_moisture": 5.619444929725641,
        }

    def _air_pressure(self) -> float:
        """The station's winter-design air pressure (hPa)."""
        pressure = self.climate.winter_design().get("pressure")
        return float(pressure.value) if pressure is not None else 950.0

    @staticmethod
    def _ventilation_mode(p, kind: str) -> str:
        """The ventilation control mode of the value kind (``1.1.5.5``):
        IDA-C3 -> einstufig, IDA-C4 -> zweistufig, else stufenlos."""
        mode = p("1.1.5.5", kind)
        if mode == "IDA-C3":
            return "einstufig"
        if mode == "IDA-C4":
            return "zweistufig"
        return "stufenlos"

    @staticmethod
    def _transmission_coeff(type_, p, ngf: float, kind: str = "standard") -> float:
        """(A − gf·NGF/0.75)·Uop + gf·NGF/0.75·Uw, ×1.1 cold bridges, /NGF.

        The U-values are read in the value kind (the workbook's N173 uses
        the Zielwert U-values, e.g. Uop 0.1 / Uw 0.8 for 1.01); values the
        kind does not carry fall back to Standard like the N = M columns.
        """
        pv = lambda pid: p(pid, kind) if p(pid, kind) is not None else p(pid, "standard")
        hull = pv("1.1.1.2") or 0.0
        u_op = pv("Uop") or 0.0
        u_w = pv("Uw") or 0.0
        glas = (pv("1.1.1.3") or 0.0) / 100.0 / 0.85 * (pv("hR") or 0.0) / (pv("dR") or 1.0)
        window_area = glas * ngf / 0.75
        return ((hull - window_area) * u_op + window_area * u_w) * 1.1 / ngf


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
        (beleuchtung, lighting),        (lueftung, occupancy),
    ):
        hourly = _hourly_series(annual, schedule)
        for index in range(8760):
            series[index] += hourly[index]
    return series
