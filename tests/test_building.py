"""Tests for the object-oriented domain layer (energytools.building)."""

from __future__ import annotations

import pytest

from energytools.building import (
    Building,
    Climate,
    Generation,
    Room,
    RoomType,
    Schedule,
    Schedules,
    Ventilation,
)
from energytools.raumdaten import load_dataset


@pytest.fixture(scope="module")
def dataset():
    return load_dataset("V221")


@pytest.fixture(scope="module")
def building(dataset) -> Building:
    b = Building(
        name="Mein Haus",
        climate=Climate.from_dataset(dataset, 40),
        standard="standard",
    )
    b.add_room(Room("Laden", type=RoomType.from_dataset(dataset, "5.02"), area=200, ebf=True))
    b.add_room(Room("Schlaf", type=RoomType.from_dataset(dataset, "1.01"), area=200))
    b.add_room(Room("Garage", type=RoomType.from_dataset(dataset, "12.09"), area=50, ebf=False, heated=False))
    b.room("Laden").ventilation = Ventilation(volume_flow=725.0, sfp=0.8, full_load_hours=6260.0)
    b.add_generation(Generation("WE02", coverage=1.0, losses=0.1))
    b.add_generation(Generation("W13", coverage=1.0, losses=0.4))
    return b


class TestSchedules:
    def test_schedule_indexing(self) -> None:
        schedule = Schedule([1.0] * 24, [1.0] * 7, [1.0] * 12)
        assert schedule[4] == 1.0
        schedule[4] = 0.5
        assert schedule[4] == 0.5
        assert len(schedule) == 24

    def test_schedule_validation(self) -> None:
        with pytest.raises(ValueError, match="24"):
            Schedule([1.0] * 23, [1.0] * 7, [1.0] * 12)

    def test_yearly_distribution_sums_to_one(self) -> None:
        schedule = Schedule([1.0] * 24, [1.0] * 7, [1.0] * 12)
        distribution = schedule.yearly_distribution()
        assert len(distribution) == 8760
        assert sum(distribution) == pytest.approx(1.0)
        # night hours of a day profile are zero
        night_only = Schedule(
            [0.0 if h < 8 or h >= 18 else 1.0 for h in range(24)], [1.0] * 7, [1.0] * 12
        )
        assert sum(night_only.yearly_distribution()) == pytest.approx(1.0)
        assert night_only.yearly_distribution()[0] == 0.0
        assert night_only.yearly_distribution()[12] > 0.0


class TestRoomTypeAndClimate:
    def test_from_dataset(self, dataset) -> None:
        shop = RoomType.from_dataset(dataset, "5.02")
        assert shop.code == "5.02"
        assert shop.nutzid == 15
        assert shop.parameter("1.1.2.9") == 8.0  # Personenfläche m²/Person
        assert shop.parameter("1.1.3.3", "zielwert") == 1.0
        assert shop.parameter("1.1.8.4") == 1.5

    def test_parameter_missing_returns_none(self, dataset) -> None:
        garage = RoomType.from_dataset(dataset, "12.09")
        assert garage.parameter("1.1.2.9") is None

    def test_climate(self, dataset) -> None:
        zurich = Climate.from_dataset(dataset, 40)
        assert zurich.name == "Zürich-MeteoSchweiz"
        assert len(zurich.monthly_temperature()) == 12
        assert len(zurich.design_days()) == 2

    def test_default_schedules_are_copies(self, dataset) -> None:
        shop = RoomType.from_dataset(dataset, "5.02")
        first = shop.default_schedules()
        second = shop.default_schedules()
        assert first.occupancy[10] == 0.4  # 5.02 day profile at 10:00
        first.occupancy[10] = 0.0
        assert second.occupancy[10] == 0.4  # the copy is untouched


class TestBuilding:
    def test_area(self, building) -> None:
        area = building.area
        assert area.ngf == pytest.approx(450.0)  # 200 + 200 + 50
        assert area.ebf == pytest.approx(400.0)  # garage not ebf
        assert area.gf == pytest.approx(440.0)

    def test_room_lookup(self, building) -> None:
        assert building.room("Laden").type.code == "5.02"
        with pytest.raises(KeyError):
            building.room("nope")

    def test_duplicate_room_rejected(self, building) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            building.add_room(Room("Laden", type=building.room("Laden").type, area=1))

    def test_annual_loads(self, building) -> None:
        load = building.load
        assert load.heating.annually["Schlaf"] > 0.0
        assert load.heating.annually["Garage"] == 0.0
        assert load.electricity.annually["Laden"] > 0.0
        assert load.totals["erdgas"] > 0.0

    def test_hourly_sums_match_annual(self, building) -> None:
        load = building.load
        for kind in ("heating", "ww", "electricity"):
            category = getattr(load, kind)
            for room, annual in category.annually.items():
                assert sum(category.hourly[room]) == pytest.approx(annual, rel=1e-9), (
                    f"{kind}/{room}: hourly sum {sum(category.hourly[room])} != annual {annual}"
                )

    def test_hourly_series_length(self, building) -> None:
        series = building.load.heating.hourly["Schlaf"]
        assert len(series) == 8760

    def test_lazy_invalidation_on_schedule_change(self, building) -> None:
        load = building.load
        before = load.heating.hourly["Schlaf"][12]
        building.room("Schlaf").schedules.occupancy[12] = 0.0
        after = building.load.heating.hourly["Schlaf"][12]
        assert before > 0.0
        assert after == 0.0

    def test_lazy_invalidation_on_generation(self, building) -> None:
        before = building.load.totals["erdgas"]
        building.room("Schlaf").add_generation(Generation("WE08", coverage=1.0, losses=0.0))
        after = building.load.totals["erdgas"]
        assert after < before

    def test_standard_kinds(self, dataset) -> None:
        b = Building(
            name="Zielwert",
            climate=Climate.from_dataset(dataset, 40),
            standard="zielwert",
        )
        b.add_room(Room("Laden", type=RoomType.from_dataset(dataset, "5.02"), area=100))
        assert b.load.electricity.annually["Laden"] > 0.0
        with pytest.raises(ValueError, match="standard"):
            Building(name="x", climate=Climate.from_dataset(dataset, 40), standard="nope")

    def test_schedules_editable_per_room(self, building) -> None:
        schedules: Schedules = building.room("Laden").schedules
        assert isinstance(schedules.occupancy, Schedule)
        original = schedules.occupancy[10]
        schedules.occupancy[10] = original * 2.0
        assert schedules.occupancy[10] == original * 2.0
        # the other room keeps the type default (1.01 day profile at 10:00)
        assert building.room("Schlaf").schedules.occupancy[10] == 0.0  # type: ignore[attr-defined]


class TestDesignDayBalances:
    def _fresh_building(self, dataset) -> Building:
        building = Building(
            name="Balance",
            climate=Climate.from_dataset(dataset, 40),
            standard="standard",
        )
        building.add_room(Room("Schlaf", type=RoomType.from_dataset(dataset, "1.01"), area=20))
        return building

    def test_design_day(self, dataset) -> None:
        building = self._fresh_building(dataset)
        rows = building.design_day(building.room("Schlaf"))
        assert len(rows) == 24
        # hour 0 of the August design day: night, occupied (2.4 W/m² persons)
        assert rows[0].persons == pytest.approx(2.4)
        assert rows[0].solar == 0.0
        # peak cooling in the afternoon
        peak = max(rows, key=lambda r: -r.cooling_power)
        assert peak.cooling_power < 0.0
        assert peak.hour in range(11, 18)

    def test_air_quality(self, dataset) -> None:
        building = self._fresh_building(dataset)
        rows = building.air_quality(building.room("Schlaf"), month=2)
        assert len(rows) == 24
        # the golden values of room use 1.01 at 20 m² (verified vs the cache)
        assert rows[0].co2_concentration == pytest.approx(626.9731917520139, rel=1e-9)
        assert rows[0].room_rh == pytest.approx(35.45786495353908, rel=1e-9)
        assert rows[0].persons == pytest.approx(20.0 / 35.0)
