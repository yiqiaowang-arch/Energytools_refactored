"""Tests for the native backend (:mod:`energytools.engine.native.backend`).

The native backend plugs the verified native model (psychrometrics, the AHU
temperature-bin engine, the building aggregation) into the
:class:`~energytools.engine.backends.EngineBase` contract and consumes the
real V221 dataset.  Verification layers:

1. **End-to-end** (primary): ``NativeBackend().calculate(...)`` over a real
   :class:`BuildingInput` (2 rooms 3.01/3.02, LA01, WE02) returns a complete
   ``Results`` with non-zero energy values, resolved versions and the explain
   trace steps validate → rooms → ventilation → ahu → generation → resultate.

2. **Golden comparison** (case-02, Zielwert/Zürich): the backend is fed the
   case-02 room rows 12/13 (Einzel-, Gruppenbüro 2500 m² + Grossraumbüro
   1000 m²) and the LA01 system; the per-room values must equal the cached
   room cells F12..W12 / F13..W13 and the per-system LA01 values the cached
   Lüftung row 7 (rel 1e-6) — the AHU engine's cache match is exact because
   the inputs (volume flow, fan power, regulation, full-load hours, WRG,
   Kühlfall/Heizfall setpoints, Zürich climate bins/humidity/pressure) are
   identical.

3. **Engine entry**: ``Engine().calculate(..., backend=NativeBackend())``
   validates and stores the result like any other backend.

4. **validate**: capability validation reports a missing dataset release as a
   hard error and the station-dependent KPI-column warning for non-Zürich
   stations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import energytools
from energytools.engine import Engine, NativeBackend
from energytools.engine.backends import EngineBase
from energytools.engine.model import (
    BuildingInput,
    GenerationSystem,
    RoomRow,
    ValidationReport,
    ValueKind,
    VentilationSystem,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "data" / "datasets"
GOLDEN = REPO_ROOT / "data" / "golden" / "case-02.json"
DATASET_PKG = DATASET_DIR / "V221" / "package.json"

#: The case-02 LA01 system inputs (Lüftung row 7) — the native AHU must
#: reproduce the cached row 7 exactly.
LA01 = {
    "id": "LA01",
    "room_use": "Einzel-, Gruppenbüro",
    "volume_flow_standard": 8578.57142857143,
    "sfp": 0.8,
    "fan_power": 6.862857142857144,
    "regulation": "1-stufig",
    "full_load_hours": 3900.0,
    "wrg": 0.8,
    "kuehlfall_t": 20.0,
    "heizfall_t": 21.0,
}


def _cell(cell: object, default: object = None) -> object:
    """Cached value of a golden-JSON cell record (nested dict or JSON string)."""
    if isinstance(cell, str) and cell.startswith("{"):
        try:
            cell = json.loads(cell)
        except ValueError:
            pass
    if isinstance(cell, dict):
        v = cell.get("value")
        if isinstance(v, dict):
            return default
        if v is not None:
            return v
        if "result" in cell:
            r = cell["result"]
            return default if isinstance(r, dict) else r
        return default
    return cell


def _num(cell: object, default: float = 0.0) -> float:
    v = _cell(cell, default)
    return float(v) if isinstance(v, (int, float)) else default


def _str(cell: object, default: str = "") -> str:
    v = _cell(cell, default)
    return str(v) if v is not None else default


def make_two_room_building(**overrides: object) -> BuildingInput:
    """The task example: rooms 3.01/3.02 + LA01 + WE02 (Zielwert, Zürich)."""
    data: dict[str, object] = {
        "name": "Beispiel 2R",
        "rooms": (
            RoomRow(
                name="Einzel-, Gruppenbüro",
                room_use_id="3.01",
                ebf=True,
                ngf=2500.0,
                lueftung_system="LA01",
                gekuehlt=True,
                beheizt=True,
            ),
            RoomRow(
                name="Grossraumbüro",
                room_use_id="3.02",
                ebf=True,
                ngf=1000.0,
                lueftung_system="LA01",
                gekuehlt=True,
                beheizt=True,
            ),
        ),
        "ventilation": (VentilationSystem(**LA01),),
        "generation": (
            GenerationSystem(
                id="WE2", kind="heating", catalog_code="WE02", coverage=1.0, losses=0.1
            ),
        ),
        "value_kind": ValueKind.ZIELWERT,
        "climate_station_id": 40,
    }
    data.update(overrides)
    return BuildingInput(**data)  # type: ignore[arg-type]


def make_case02_rooms_building() -> BuildingInput:
    """The case-02 room rows 12/13 with the case-02 LA01 system."""
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    rooms_data = data["inputs"]["rooms"]
    rooms = []
    for r in (12, 13):
        use = _str(rooms_data.get(f"B{r}"))
        rooms.append(
            RoomRow(
                name=f"{use} #{r}",
                room_use_id=use,
                ebf=_cell(rooms_data.get(f"C{r}")) is True,
                ngf=float(_num(rooms_data.get(f"D{r}"))),
                lueftung_system=_str(rooms_data.get(f"L{r}")) or None,
                gekuehlt=_cell(rooms_data.get(f"P{r}")) is True,
                beheizt=_cell(rooms_data.get(f"S{r}")) is True,
            )
        )
    return BuildingInput(
        name="case-02 subset",
        rooms=tuple(rooms),
        value_kind=ValueKind.ZIELWERT,
        climate_station_id=40,
        ventilation=(VentilationSystem(**LA01),),
    )


def _cached_room(data: dict, row: int) -> dict[str, float | None]:
    """case-02 cached room cells (F..W) → value."""
    rooms_data = data["inputs"]["rooms"]
    return {
        col: (
            _num(rooms_data.get(f"{col}{row}"))
            if _cell(rooms_data.get(f"{col}{row}")) is not None
            else None
        )
        for col in "FGHIJKNOQRTUVW"
    }


# ---------------------------------------------------------------------------
# Backend contract
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_native_backend_identity() -> None:
    backend = NativeBackend(dataset_dir=str(DATASET_DIR))
    assert backend.name == "native"
    assert backend.version == energytools.__version__
    assert isinstance(backend, EngineBase)


@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_native_backend_validate() -> None:
    backend = NativeBackend(dataset_dir=str(DATASET_DIR))
    report = backend.validate(make_two_room_building(), "V221")
    assert isinstance(report, ValidationReport)
    assert report.valid
    # non-Zürich stations warn about the station-dependent KPI columns
    davos = make_two_room_building(climate_station_id=8)
    report_davos = backend.validate(davos, "V221")
    assert report_davos.valid
    assert any("Klimakälte/Heizwärme" in w for w in report_davos.warnings)
    # a missing release is a hard error
    assert not backend.validate(make_two_room_building(), "V999").valid


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_calculate_two_rooms_end_to_end() -> None:
    """The task example runs end-to-end with real, non-zero energy values."""
    backend = NativeBackend(dataset_dir=str(DATASET_DIR))
    result = backend.calculate(make_two_room_building(), "V221", "1.0.0")

    assert result.backend == f"native@{backend.version}"
    assert result.versions.dataset == "V221"
    assert result.versions.model == "1.0.0"
    assert result.versions.climate == "unknown"  # engine replaces it later
    assert result.inputs_hash == make_two_room_building().inputs_hash()

    # real energy values (not stub placeholders)
    assert result.totals["geraete_mwh"] == pytest.approx(72.75, rel=1e-9)
    assert result.totals["fan_energy_mwh"] == pytest.approx(26.765142857142862, rel=1e-9)
    assert result.totals["heizung_endenergie_mwh"] > 0.0
    assert result.totals["endenergie_total_mwh"] == pytest.approx(
        result.totals["geraete_mwh"]
        + result.totals["beleuchtung_mwh"]
        + result.totals["fan_energy_mwh"]
        + result.totals["heizung_endenergie_mwh"],
        rel=1e-9,
    )
    assert result.per_carrier["erdgas"] == pytest.approx(
        result.totals["heizung_endenergie_mwh"], rel=1e-6
    )
    assert result.per_carrier["el"] > 0.0

    # per-room / per-system values present
    assert set(result.per_room) == {"Einzel-, Gruppenbüro", "Grossraumbüro"}
    assert set(result.per_system) == {"LA01"}

    # trace steps
    assert result.trace is not None
    assert [step.id for step in result.trace.steps] == [
        "validate",
        "rooms",
        "ventilation",
        "ahu",
        "generation",
        "resultate",
    ]

    # assumptions document the dataset defaults
    assert any("Nutzungsgrad" in a for a in result.assumptions)
    assert any("Klimakälte/Heizwärme" in a for a in result.assumptions)


@pytest.mark.skipif(not GOLDEN.exists(), reason="golden case-02 not present")
@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_rooms_match_case02_cached_rows() -> None:
    """The room aggregation reproduces the case-02 cached room rows 12/13.

    Same room uses, areas, flags and value kind → the dataset KPI
    intensities × NGF must equal the workbook cache (rel 1e-6).
    """
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    building = make_case02_rooms_building()
    backend = NativeBackend(dataset_dir=str(DATASET_DIR))
    result = backend.calculate(building, "V221", "1.0.0")

    by_name = dict(result.per_room)  # room name -> RoomResult dict
    for row, room_name in ((12, building.rooms[0].name), (13, building.rooms[1].name)):
        cached = _cached_room(data, row)
        room = by_name[room_name]
        for col, value in cached.items():
            field = {
                "F": "geraete_kw",
                "G": "geraete_mwh",
                "H": "prozessanlagen_kw",
                "I": "prozessanlagen_mwh",
                "J": "beleuchtung_kw",
                "K": "beleuchtung_mwh",
                "N": "lueftung_kw",
                "O": "lueftung_mwh",
                "Q": "kuehlung_kw",
                "R": "kuehlung_mwh",
                "T": "heizung_kw",
                "U": "heizung_mwh",
                "V": "warmwasser_l_d",
                "W": "warmwasser_mwh",
            }[col]
            if value is None:
                continue
            assert room[field] == pytest.approx(value, rel=1e-6), (
                f"room {row} {col} ({field}): engine {room[field]!r} vs cached {value!r}"
            )


@pytest.mark.skipif(not GOLDEN.exists(), reason="golden case-02 not present")
@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_ahu_matches_case02_cache() -> None:
    """LA01 with the case-02 inputs reproduces the cached Lüftung row 7.

    The AHU temperature-bin engine is exact (rel 1e-6): the same volume flow,
    fan power, regulation, full-load hours, WRG, setpoints and Zürich climate
    (bins/humidity/pressure from the dataset) as the workbook cache.
    """
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    lueftung = data["inputs"]["Lueftung"]
    building = make_case02_rooms_building()
    backend = NativeBackend(dataset_dir=str(DATASET_DIR))
    result = backend.calculate(building, "V221", "1.0.0")

    system = result.per_system["LA01"]
    for col, field in (
        ("H", "fan_power_kw"),
        ("I", "fan_energy_mwh"),
        ("Q", "luftkuehlung_kw"),
        ("R", "luftkuehlung_mwh"),
        ("S", "lufterwaermung_kw"),
        ("T", "lufterwaermung_mwh"),
        ("K", "full_load_hours"),
    ):
        cached = _num(lueftung.get(f"{col}7"))
        assert system[field] == pytest.approx(cached, rel=1e-6), (
            f"Lüftung {col}7 ({field}): engine {system[field]!r} vs cached {cached!r}"
        )


@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_engine_entry_with_native_backend() -> None:
    """``Engine().calculate(..., backend=NativeBackend())`` — the engine path.

    The engine validates, resolves the versions (replacing the backend's
    provisional ``climate="unknown"``) and stores the result.
    """
    engine = Engine()
    result = engine.calculate(
        make_two_room_building(),
        "V221",
        "1.0.0",
        backend=NativeBackend(dataset_dir=str(DATASET_DIR)),
    )
    assert result.backend.startswith("native@")
    assert result.versions.climate == "meteoschweiz-2024"
    assert result.versions.model == "1.0.0"
    assert result.totals["endenergie_total_mwh"] > 0.0
    # the stored result is reloadable and explainable
    assert engine.get_result(result.result_id) == result
    assert engine.explain(result.result_id).step("ahu").id == "ahu"


@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_full_generation_groups() -> None:
    """Cooling + heating + WW generators flow into the Resultate matrix."""
    building = make_two_room_building(
        generation=(
            GenerationSystem(id="KE1", kind="cooling", catalog_code="KE06", coverage=1.0, losses=0.1),
            GenerationSystem(id="WE1", kind="heating", catalog_code="WE15", coverage=0.5, losses=0.1),
            GenerationSystem(id="WE2", kind="heating", catalog_code="WE05", coverage=0.5, losses=0.1),
            GenerationSystem(id="W1", kind="ww", catalog_code="W13", coverage=1.0, losses=0.4),
        ),
    )
    result = NativeBackend(dataset_dir=str(DATASET_DIR)).calculate(building, "V221", "1.0.0")
    # cooling end energy lands on El (KE06), WW on El (W13)
    assert result.per_carrier["el"] > result.totals["fan_energy_mwh"]
    assert result.totals["kuehlung_endenergie_mwh"] > 0.0
    assert result.totals["warmwasser_endenergie_mwh"] > 0.0
    # the Resultate matrix carries the heating carriers (El + Pell)
    energy = result.intermediates["resultate"]["energy"]
    assert energy["heizung"]["El"] > 0.0
    assert energy["heizung"]["Pell"] > 0.0


@pytest.mark.skipif(not DATASET_PKG.exists(), reason="V221 package not present")
def test_station_kpi_from_qhc() -> None:
    """A non-Zürich building reads the Klimakälte/Heizwärme KPI from the
    Qhc_Klimastat matrices of its station instead of the station-40 cache."""
    backend = NativeBackend(dataset_dir=str(DATASET_DIR))
    zurich = backend.calculate(make_two_room_building(climate_station_id=40), "V221", "1.0.0")
    davos = backend.calculate(make_two_room_building(climate_station_id=8), "V221", "1.0.0")
    # the stations differ (Qhc_Klimastat: station 8 Zielwert heating 7.47 vs
    # station 40 9.81 kWh/m2 for 3.01) — the engine follows the matrix
    assert davos.totals["heizung_mwh"] != zurich.totals["heizung_mwh"]
    # Davos Zielwert cooling energy of 3.01 is 0 in the matrix
    assert davos.per_room["Einzel-, Gruppenbüro"]["kuehlung_mwh"] == 0.0
    # the per-room heating equals the qhc heating_energy matrix of station 8
    from energytools.raumdaten import load_dataset
    from energytools.raumdaten.model import ValueKind

    ds = load_dataset("V221", path=str(DATASET_DIR))
    nutzid = ds.room_use("3.01").nutzid
    expected = (
        ds.qhc().metric("heating_energy", nutzid, 8, ValueKind.ZIELWERT).value
        * 2500.0
        / 1000.0
    )
    assert davos.per_room["Einzel-, Gruppenbüro"]["heizung_mwh"] == pytest.approx(expected, rel=1e-9)
    # the warning documents the remaining station-40 default (FV,i)
    assert any("FV,i" in w for w in davos.warnings)
