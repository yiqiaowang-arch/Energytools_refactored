"""Tests for the JSON/CSV export of ``energytools.dataset``.

Covers ``Dataset.to_json`` (round-trip fidelity, file writing,
determinism) and ``Dataset.to_csv`` (all four scopes: room-uses,
parameters, profiles, climate; unknown scope errors; file writing).
Excel (xlsx) export is a documented TODO of a later milestone.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from energytools.common.errors import ExportError
from energytools.common.valuekind import ValueKind
from energytools.dataset import load_dataset, parse_dataset

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "dataset_sample"
SAMPLE = FIXTURE_DIR / "V221.json"


def _parse_csv(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


# ---------------------------------------------------------------------------
# to_json
# ---------------------------------------------------------------------------


def test_to_json_round_trip_preserves_package() -> None:
    ds = load_dataset(SAMPLE)
    reloaded = parse_dataset(json.loads(ds.to_json()), source="roundtrip.json")
    # The exported package is the normalized canonical form; the declared
    # checksum is recomputed for it, so only the checksum field may differ.
    expected = ds.as_dict()
    actual = reloaded.as_dict()
    assert actual["room_uses"] == expected["room_uses"]
    assert actual["parameters"] == expected["parameters"]
    assert actual["profiles"] == expected["profiles"]
    assert actual["climate_stations"] == expected["climate_stations"]
    for key in ("id", "edition", "publication_date", "source_workbook", "changelog"):
        assert actual["release"][key] == expected["release"][key]
    # The exported package is self-consistent: it validates cleanly.
    report = reloaded.validate()
    assert report.valid
    assert report.warnings == ()


def test_to_json_writes_target(tmp_path: Path) -> None:
    ds = load_dataset(SAMPLE)
    target = tmp_path / "out.json"
    text = ds.to_json(target)
    assert target.read_text(encoding="utf-8") == text
    reloaded = load_dataset(target)
    assert reloaded.release_id == "V221"
    assert reloaded.validate().valid


def test_to_json_is_deterministic() -> None:
    ds = load_dataset(SAMPLE)
    assert ds.to_json() == ds.to_json()


def test_to_json_preserves_umlauts() -> None:
    text = load_dataset(SAMPLE).to_json()
    assert "Zürich-MeteoSchweiz" in text
    assert "Jahresgleichzeitigkeit" in text


# ---------------------------------------------------------------------------
# to_csv
# ---------------------------------------------------------------------------


def test_to_csv_room_uses() -> None:
    rows = _parse_csv(load_dataset(SAMPLE).to_csv("room-uses"))
    assert rows[0] == [
        "nutzid", "code", "category", "name_de", "name_fr", "name_it", "sia_clause",
    ]
    assert len(rows) == 1 + 3  # header + 3 room uses
    assert rows[1][:3] == ["1", "1.01", "1"]
    assert rows[1][3] == "Wohnen MFH"
    assert rows[1][4] == "Habitation CMI"
    assert rows[3][:3] == ["3", "3.01", "3"]


def test_to_csv_parameters() -> None:
    rows = _parse_csv(load_dataset(SAMPLE).to_csv("parameters"))
    assert len(rows) == 1 + 6  # header + 6 parameters
    header = rows[0]
    assert header[0] == "id" and header[5] == "unit" and header[7] == "category"
    assert header[8] == "value_kinds"
    assert rows[1][0] == "1.1.2.7"
    assert rows[1][5] == "%"
    assert rows[1][7] == "Raumklima"
    assert rows[1][8] == "standard;zielwert;bestand"
    assert rows[5][0] == "5.1.1.1"
    assert rows[5][8] == "standard"  # Standard-only parameter
    assert rows[6][0] == "1.3.1.1"
    assert rows[6][8] == "standard;bestand"


def test_to_csv_profiles() -> None:
    rows = _parse_csv(load_dataset(SAMPLE).to_csv("profiles"))
    assert rows[0] == [
        "room_use_id", "room_use_code", "parameter_id", "kind", "value", "unit",
    ]
    # 3 profiles × (4 params × 3 kinds + 5.1.1.1 × 1 kind + 1.3.1.1 × 2 kinds).
    assert len(rows) == 1 + 3 * (4 * 3 + 1 + 2)
    kinds = {row[3] for row in rows[1:]}
    assert kinds == {"standard", "zielwert", "bestand"}
    assert ["1", "1.01", "1.1.2.7", "standard", "0.7", "%"] in rows
    assert ["1", "1.01", "5.1.1.1", "standard", "30.0", "m3/h"] in rows
    assert ["3", "3.01", "1.3.1.1", "bestand", "Leuchtstoff", "-"] in rows


def test_to_csv_climate() -> None:
    rows = _parse_csv(load_dataset(SAMPLE).to_csv("climate"))
    assert rows[0] == [
        "station_id", "name_de", "name_fr", "name_it", "section", "key", "value", "unit",
    ]
    station_ids = {row[0] for row in rows[1:]}
    assert station_ids == {"1", "40"}
    zurich = [row for row in rows[1:] if row[1] == "Zürich-MeteoSchweiz"]
    assert len(zurich) == 4  # 2 winter + 1 summer + 1 monthly
    assert ["40", "Zürich-MeteoSchweiz", "Zurich-MétéoSuisse", "Zurigo-MeteoSvizzera",
            "winter_design", "t_a", "-8.0", "°C"] in rows


def test_to_csv_unknown_scope_raises_export_error() -> None:
    with pytest.raises(ExportError) as exc_info:
        load_dataset(SAMPLE).to_csv("bogus-scope")
    assert exc_info.value.details["scope"] == "bogus-scope"


def test_to_csv_writes_target(tmp_path: Path) -> None:
    ds = load_dataset(SAMPLE)
    target = tmp_path / "room-uses.csv"
    text = ds.to_csv("room-uses", target)
    assert target.read_text(encoding="utf-8") == text


# ---------------------------------------------------------------------------
# pandas helper (optional dependency)
# ---------------------------------------------------------------------------


def test_profile_to_frame_requires_pandas() -> None:
    pandas = pytest.importorskip("pandas")
    ds = load_dataset(SAMPLE)
    frame = ds.get_room_use_profile(1).to_frame(ValueKind.STANDARD)
    assert list(frame.columns) == ["id", "label", "symbol", "unit", "value"]
    assert len(frame) == 6
    row = frame[frame["id"] == "1.1.2.7"].iloc[0]
    assert row["symbol"] == "g"
    assert row["value"] == 0.7
    assert pandas is not None  # silence unused-import linters
