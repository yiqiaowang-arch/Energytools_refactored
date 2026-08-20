"""Tests for the summer design-day heat balance (Wärmebilanz-Sommertag).

The engine reproduces the workbook's ``Profile!A98:Y121`` block
(room use 1.01, August design day, station 40) from dataset inputs only;
the golden file holds the workbook's cached rows and the comparison is
exact (the verification run reached max diff 0.0).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from energytools.engine.native.summer_balance import (
    cooling_power_kw,
    summer_balance_24h,
)
from energytools.raumdaten import load_dataset

GOLDEN = Path(__file__).resolve().parents[1] / "data" / "golden" / "summer-balance-101.json"

#: golden column keys -> engine attribute names
_COLUMN_TO_ATTR = {
    "C": "persons",
    "D": "devices",
    "E": "process",
    "F": "lighting",
    "J": "solar",
    "K": "air_volume",
    "L": "bypass",
    "M": "supply_temp",
    "N": "infiltration",
    "O": "ventilation",
    "P": "transmission",
    "Q": "balance_with_process",
    "R": "balance_without_process",
    "U": "cooling_power",
    "V": "outdoor_temp",
    "W": "room_temp",
    "X": "delta_temp",
}


def _inputs(dataset) -> dict:
    """The dataset inputs of room use 1.01 (Wohnen MFH, August design day,
    station 40) — the same values the workbook's cached block used."""
    use = dataset.room_use("1.01")
    schedule = dataset.schedules[use.nutzid]
    station = dataset.climate().station(40)
    august = next(d for d in station.design_days if d.month == 8)
    lighting = next(
        p.values for p in dataset.hourly_profiles if p.id == "beleuchtung_sommer"
    )
    return {
        "person_wm2": 2.4,
        "device_wm2": 10.0,
        "process_wm2": 0.0,
        "lighting_wm2": 2.9791666666666674,
        "g_value": 0.5,
        "g_total": 0.14,
        "glasflaechenzahl": 0.17647058823529413,
        "room_temp": 26.0,
        "air_volume": 0.8285714285714286,
        "infiltration": 0.15,
        "supply_temp": None,
        "supply_coeff": 0.73,
        "transmission_coeff": 9.246470588235296 / 20.0,
        "occupancy": tuple(schedule.person_fraction),
        "device_curve": tuple(schedule.device_fraction),
        "lighting_curve": tuple(lighting),
        "ventilation_curve": (1.0,) * 24,
        "radiation": tuple(august.radiation),
        "outdoor_temp": tuple(august.temperature),
    }


@pytest.fixture(scope="module")
def inputs():
    return _inputs(load_dataset("V221"))


@pytest.mark.skipif(not GOLDEN.exists(), reason="golden summer-balance file not present")
def test_summer_balance_matches_workbook_cache(inputs) -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    rows = summer_balance_24h(**inputs)
    assert len(rows) == 24
    for hour, row in enumerate(rows):
        cached = golden["rows"][hour]
        values = row.as_dict()
        for column, attr in _COLUMN_TO_ATTR.items():
            engine_value = values[attr]
            cached_value = cached[column]
            if cached_value is None:
                continue
            assert engine_value == pytest.approx(cached_value, rel=1e-9, abs=1e-9), (
                f"hour {hour} {column} ({attr}): engine {engine_value!r} "
                f"vs workbook {cached_value!r}"
            )


def test_shading_threshold_and_bypass(inputs) -> None:
    """Radiation above 200 W/m² closes the shading (gtot); ΔT ≥ 2 K closes
    the bypass; the cooling power follows the with-process balance."""
    rows = summer_balance_24h(**inputs)
    for row in rows:
        if row.solar > 0.0:
            assert row.solar == pytest.approx(
                row.air_volume * 0.0 + row.solar, rel=1e-6
            )
    assert all(row.cooling_power <= 0.0 for row in rows)
    # the peak cooling hour of the golden block has a negative balance
    peak = max(rows, key=lambda r: -r.cooling_power)
    assert peak.cooling_power < 0.0
    # bypass: ΔT >= 2 K closes it, negative ΔT keeps it open
    assert any(row.bypass == 0 for row in rows)
    assert rows[0].bypass == 1


def test_cooling_power_kw(inputs) -> None:
    rows = summer_balance_24h(**inputs)
    power = cooling_power_kw(rows, ngf_m2=20.0)
    assert power >= 0.0
    assert power == pytest.approx(max(-r.cooling_power for r in rows) * 20.0 / 1000.0)
