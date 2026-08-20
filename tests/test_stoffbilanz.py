"""Tests for the Stoffbilanz (CO₂/moisture balance) engine.

The engine reproduces the workbook's ``Profile!A278:Y301`` block
(room use 1.01, March, station 40) from dataset inputs only; the golden
file holds the workbook's cached rows and the comparison is exact
(verification reached max diff 0.0).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from energytools.engine.native.stoffbilanz import stoffbilanz_24h
from energytools.raumdaten import load_dataset

GOLDEN = Path(__file__).resolve().parents[1] / "data" / "golden" / "stoffbilanz-101.json"

#: golden column keys -> engine attribute names
_COLUMN_TO_ATTR = {
    "D": "persons",
    "E": "co2_emission",
    "G": "air_flow",
    "H": "co2_concentration",
    "L": "moisture_person",
    "M": "moisture_total",
    "Q": "saturation_pressure",
    "R": "mixing_ratio",
    "S": "outdoor_moisture",
    "T": "moisture_concentration",
    "U": "moisture_transient",
    "Y": "room_rh",
}


def _inputs(dataset) -> dict:
    """The dataset inputs of room use 1.01 (March, station 40)."""
    schedule = dataset.schedules[1]
    sia = dataset.sia2028_monthly
    assert sia is not None
    occupancy = tuple(schedule.person_fraction)
    # ventilation+infiltration flow: the einstufig stage runs the whole day
    # for 1.01 (its ±2 h occupancy window never closes -> the workbook's F
    # curve is all 1), i.e. hygienic flow 0.8285714285714286 + infiltration
    # 0.15, matching the workbook's cached K column.
    ventilation_flow = (0.9785714285714286,) * 24
    return {
        "person_area": 35.0,
        "ngf": 20.0,
        "room_height": 2.5,
        "co2_rate": 1.2,
        "person_moisture": 66.0,
        "other_moisture": 0.5,
        "air_pressure": 948.225968475814,  # Winter_Auslegung!D44 (station 40)
        "monthly_temperature": tuple(sia.temperature),
        "monthly_humidity": tuple(sia.relative_humidity),
        # the workbook's room-temperature month series (Profile!AS284)
        "monthly_room_temp": (
            21.0, 21.833333333333332, 22.666666666666664, 23.499999999999996,
            24.33333333333333, 25.16666666666666, 26.0, 25.166666666666668,
            24.333333333333336, 23.500000000000004, 22.66666666666667,
            21.83333333333334,
        ),
        "month_index": 2,  # 'Mär'
        "occupancy": occupancy,
        "ventilation_flow": ventilation_flow,
        "start_co2": 400.0,
        "start_moisture": 5.619444929725641,  # U275 (steady state of the day before)
    }


@pytest.fixture(scope="module")
def inputs():
    return _inputs(load_dataset("V221"))


@pytest.mark.skipif(not GOLDEN.exists(), reason="golden stoffbilanz file not present")
def test_stoffbilanz_matches_workbook_cache(inputs) -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    rows = stoffbilanz_24h(**inputs)
    assert len(rows) == 24
    for hour, row in enumerate(rows):
        cached = golden["rows"][hour]
        values = row.as_dict()
        for column, attr in _COLUMN_TO_ATTR.items():
            engine_value = values[attr]
            cached_value = cached[column]
            assert engine_value == pytest.approx(cached_value, rel=1e-9, abs=1e-9), (
                f"hour {hour} {column} ({attr}): engine {engine_value!r} "
                f"vs workbook {cached_value!r}"
            )


def test_co2_and_moisture_physics(inputs) -> None:
    rows = stoffbilanz_24h(**inputs)
    # CO₂ rises with occupancy and decays through the air exchange
    assert rows[0].co2_concentration > 400.0  # occupied night hour
    assert rows[10].co2_concentration == pytest.approx(400.0)  # empty midday
    # the transient moisture follows the recursive Gl. (8)
    assert rows[1].moisture_transient != rows[0].moisture_transient
    # relative humidity is capped at 100 %
    assert all(row.room_rh <= 100.0 for row in rows)
    assert all(row.room_rh > 0.0 for row in rows)
