"""Tests for per-room-use time schedules (RoomUseSchedule, ``room_use_schedules``)."""

from __future__ import annotations

import pytest

from energytools.common.provenance import Provenance
from energytools.raumdaten.model import Dataset, RoomUseSchedule, _schedule_from_dict


def _schedule(**overrides) -> RoomUseSchedule:
    values = {
        "room_use_id": 2,
        "person_fraction": (1.0,) * 24,
        "device_fraction": (0.1,) * 24,
        "weekly_fraction": (1.0,) * 7,
        "monthly_fraction": (0.8,) * 12,
        "monthly_previous_fraction": (0.6,) * 12,
        "rest_days_per_week": 0.0,
        "working_days_per_year": 365.0,
        "annual_simultaneity": 0.6,
    }
    values.update(overrides)
    return RoomUseSchedule(**values)


class TestRoomUseScheduleValidation:
    def test_accepts_full_schedule(self) -> None:
        schedule = _schedule()
        assert len(schedule.person_fraction) == 24
        assert len(schedule.device_fraction) == 24
        assert len(schedule.weekly_fraction) == 7
        assert len(schedule.monthly_fraction) == 12
        assert len(schedule.monthly_previous_fraction) == 12

    @pytest.mark.parametrize(
        "field,values",
        [
            ("person_fraction", (1.0,) * 23),
            ("device_fraction", (0.1,) * 25),
            ("weekly_fraction", (1.0,) * 6),
            ("monthly_fraction", (0.8,) * 11),
            ("monthly_previous_fraction", (0.6,) * 13),
        ],
    )
    def test_wrong_length_rejected(self, field: str, values: tuple[float, ...]) -> None:
        with pytest.raises(ValueError, match="must have"):
            _schedule(**{field: values})

    def test_negative_fraction_rejected(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            _schedule(person_fraction=(-0.1, *([1.0] * 23)))

    def test_rest_days_out_of_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="rest_days_per_week"):
            _schedule(rest_days_per_week=8.0)


class TestScheduleSerialization:
    def test_round_trip(self) -> None:
        schedule = _schedule(provenance=Provenance(sources=(), note="test"))
        rebuilt = _schedule_from_dict(schedule.as_dict())
        assert rebuilt == schedule

    def test_none_derived_values_round_trip(self) -> None:
        schedule = _schedule(working_days_per_year=None, annual_simultaneity=None)
        rebuilt = _schedule_from_dict(schedule.as_dict())
        assert rebuilt.working_days_per_year is None
        assert rebuilt.annual_simultaneity is None


class TestDatasetSchedules:
    def test_schedules_mapping_round_trip(self, dataset: Dataset) -> None:
        package = dataset.to_package_dict()
        assert "room_use_schedules" in package
        reloaded = Dataset.from_package_dict(package)
        assert reloaded.schedules == dataset.schedules

    def test_schedules_reference_known_room_uses(self, dataset: Dataset) -> None:
        nutzids = {room_use.nutzid for room_use in dataset.room_uses()}
        for schedule in dataset.schedules.values():
            assert schedule.room_use_id in nutzids

    def test_real_package_has_all_45_schedules(self, dataset: Dataset) -> None:
        assert len(dataset.schedules) == 45
        assert set(dataset.schedules) == {room_use.nutzid for room_use in dataset.room_uses()}

    def test_classroom_daily_profile(self, dataset: Dataset) -> None:
        """1.02 classroom: persons present overnight until 06:00, midday break, evening."""
        schedule = dataset.schedules[2]
        assert schedule.person_fraction[:6] == (1.0,) * 6
        assert schedule.person_fraction[8:12] == (0.0, 0.0, 0.0, 0.0)
        assert 0.0 < schedule.device_fraction[6] < 1.0
        assert len(schedule.weekly_fraction) == 7
        assert len(schedule.monthly_fraction) == 12
        assert len(schedule.monthly_previous_fraction) == 12

    def test_annual_simultaneity_matches_workbook(self, dataset: Dataset) -> None:
        """Jahresgleichzeitigkeit (berechnet) = mean of Monatsprofil (bisher)."""
        schedule = dataset.schedules[2]
        expected = sum(schedule.monthly_previous_fraction) / 12.0
        assert schedule.annual_simultaneity == pytest.approx(expected)
        # The workbook's cached value for the selected profile was 0.783333...
        assert 0.7 < schedule.annual_simultaneity < 0.9
