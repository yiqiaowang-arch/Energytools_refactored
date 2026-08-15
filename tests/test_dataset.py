"""Tests for the ``energytools.dataset`` data service.

Covers loading (single file and directory discovery with corrupt-file
skipping), the query API, profile comparison, validation and the model
constructors. Fixtures live in ``tests/fixtures/dataset_sample/``: a small
sample of the Raumdaten workbook (3 of the 45 standard room uses — 1.01
Wohnen MFH, 1.02 Wohnen EFH, 3.01 Einzel-, Gruppenbüro — a few of the 193
data-sheet parameters, the three value kinds Standard/Zielwert/Bestand,
trilingual labels and 2 of the 40 climate stations) plus deliberately corrupt
packages for the loader tests. Room-use names and values are illustrative
samples.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from energytools.common.errors import (
    DatasetNotFoundError,
    EnergyToolsError,
    UnknownClimateStationError,
    UnknownParameterError,
    UnknownRoomUseError,
)
from energytools.common.language import Language, TrilingualText
from energytools.common.units import Unit, UnitError
from energytools.common.valuekind import ValueKind
from energytools.dataset import (
    ClimateStation,
    Dataset,
    DatasetCollection,
    DatasetError,
    LoadError,
    NotFoundError,
    Parameter,
    ParameterValue,
    RoomUse,
    RoomUseProfile,
    ValidationError,
    compare_profiles,
    compute_package_checksum,
    load_dataset,
    load_datasets,
    parse_dataset,
)
from energytools.dataset.errors import (
    DatasetNotFoundError as DatasetNotFoundErrorAlias,
)
from energytools.dataset.errors import (
    DatasetValidationError,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "dataset_sample"
SAMPLE = FIXTURE_DIR / "V221.json"


def _load_sample() -> Dataset:
    """Load the valid sample fixture."""
    return load_dataset(SAMPLE)


def _sample_package() -> dict:
    """The sample fixture as a package dict (independent copy)."""
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_load_dataset_from_sample_fixture() -> None:
    ds = _load_sample()
    assert ds.release_id == "V221"
    assert ds.release.edition == "SIA 2024"
    assert ds.release.publication_date == date(2024, 11, 17)
    assert ds.release.source_workbook == "2024_Raumdatenblätter_dfi_V221.xlsm"
    assert len(ds.release.changelog) == 1
    assert len(ds.list_room_uses()) == 3
    assert len(ds.list_parameters()) == 6
    assert len(ds.profiles) == 3
    assert len(ds.list_climate_stations()) == 2
    # The loader computed the package content checksum and it matches the
    # declared one (the checksum field itself is excluded from the hash).
    assert ds.content_checksum_sha256 == ds.release.checksum_sha256


def test_load_dataset_missing_file_raises_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(NotFoundError) as exc_info:
        load_dataset(missing)
    # Hooked under the common.errors tree: also a DatasetNotFoundError.
    assert isinstance(exc_info.value, DatasetNotFoundError)
    assert "not found" in str(exc_info.value)


def test_load_dataset_directory_path_raises_load_error() -> None:
    with pytest.raises(LoadError):
        load_dataset(FIXTURE_DIR)


def test_load_dataset_invalid_json_raises_validation_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        load_dataset(FIXTURE_DIR / "not-json.json")
    assert isinstance(exc_info.value, DatasetValidationError)
    assert "not valid JSON" in str(exc_info.value)
    assert exc_info.value.details["errors"]


def test_load_dataset_non_object_package_raises() -> None:
    with pytest.raises(ValidationError, match="JSON object"):
        load_dataset(FIXTURE_DIR / "not-a-package.json")


def test_load_dataset_missing_required_field_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        load_dataset(FIXTURE_DIR / "incomplete.json")
    errors = exc_info.value.details["errors"]
    assert any("missing required field 'unit'" in error for error in errors)


def test_load_dataset_unknown_value_kind_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        load_dataset(FIXTURE_DIR / "unknown-value-kind.json")
    assert any("unknown value kind 'bogus'" in error for error in exc_info.value.details["errors"])


def test_load_dataset_duplicate_ids_raises() -> None:
    with pytest.raises(ValidationError) as exc_info:
        load_dataset(FIXTURE_DIR / "duplicate-ids.json")
    assert any("duplicate parameter" in error for error in exc_info.value.details["errors"])


def test_load_datasets_directory_discovery_skips_invalid_files() -> None:
    collection = load_datasets(FIXTURE_DIR)
    assert isinstance(collection, DatasetCollection)
    assert [dataset.release_id for dataset in collection.datasets] == ["V221"]
    # The five corrupt packages are skipped and recorded, never crash.
    assert len(collection.skipped) == 5
    reasons = " ".join(skipped.reason for skipped in collection.skipped)
    assert "not valid JSON" in reasons
    assert "unknown value kind" in reasons
    assert "duplicate parameter" in reasons
    # The collection answers existence queries without touching disk.
    assert collection.get("V221").release_id == "V221"
    with pytest.raises(DatasetNotFoundError):
        collection.get("V999")


def test_load_datasets_missing_directory_yields_empty(tmp_path: Path) -> None:
    collection = load_datasets(tmp_path / "definitely-not-here")
    assert collection.datasets == ()
    assert collection.skipped == ()


def test_load_datasets_list_newest_first(tmp_path: Path) -> None:
    package = _sample_package()
    package["release"]["id"] = "V222"
    package["release"]["publication_date"] = "2025-03-02"
    package["release"]["checksum_sha256"] = compute_package_checksum(package)
    (tmp_path / "V222.json").write_text(json.dumps(package), encoding="utf-8")
    shutil.copy(SAMPLE, tmp_path / "V221.json")
    collection = load_datasets(tmp_path)
    assert [dataset.release_id for dataset in collection.list()] == ["V222", "V221"]
    assert [release.id for release in collection.releases()] == ["V222", "V221"]


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------


def test_list_room_uses_sheet_order_and_trilingual() -> None:
    ds = _load_sample()
    room_uses = ds.list_room_uses()
    assert [room_use.nutzid for room_use in room_uses] == [1, 2, 3]
    assert [room_use.code for room_use in room_uses] == ["1.01", "1.02", "3.01"]
    assert room_uses[0].name.get("de") == "Wohnen MFH"
    assert room_uses[0].name.get(Language.FR) == "Habitation CMI"
    assert room_uses[2].name.get("it") == "Ufficio singolo, di gruppo"


def test_room_use_lookup_by_id_and_code() -> None:
    ds = _load_sample()
    assert ds.room_use(2).code == "1.02"
    assert ds.room_use("3.01").nutzid == 3
    with pytest.raises(UnknownRoomUseError):
        ds.room_use(99)
    with pytest.raises(UnknownRoomUseError):
        ds.room_use("9.99")


def test_list_parameters_sheet_order() -> None:
    ds = _load_sample()
    parameter_ids = [parameter.id for parameter in ds.list_parameters()]
    assert parameter_ids == [
        "1.1.2.7", "1.1.2.1", "1.2.1.1", "1.2.2.1", "5.1.1.1", "1.3.1.1",
    ]
    first = ds.list_parameters()[0]
    assert first.symbol == "g"
    assert first.unit.symbol == "%"
    assert first.value_kinds == frozenset(ValueKind)


def test_get_parameter_by_clause_id() -> None:
    ds = _load_sample()
    parameter = ds.get_parameter("1.1.2.7")
    assert parameter.data_type == "number"
    assert parameter.category == "Raumklima"
    assert parameter.label.de == "Jahresgleichzeitigkeit"
    assert ds.parameter("5.1.1.1").value_kinds == frozenset({ValueKind.STANDARD})
    with pytest.raises(UnknownParameterError):
        ds.get_parameter("9.9.9.9")


def test_get_room_use_profile_values() -> None:
    ds = _load_sample()
    profile = ds.get_room_use_profile(1)
    assert profile.room_use.code == "1.01"
    assert profile.value("1.1.2.7", ValueKind.STANDARD).value == 0.7
    assert profile.value("1.1.2.7", ValueKind.ZIELWERT).value == 0.6
    assert profile.value("1.1.2.7", ValueKind.BESTAND).value == 0.8
    assert profile.value("1.3.1.1").value == "LED"
    assert len(profile.parameters()) == 6
    # Doc part 03 §1.16 also exposes ``profile(...)``.
    assert ds.profile(1) is profile


def test_get_room_use_profile_by_code() -> None:
    ds = _load_sample()
    profile = ds.get_room_use_profile("3.01")
    assert profile.room_use.nutzid == 3
    assert profile.value("1.1.2.7").value == 0.8
    with pytest.raises(UnknownRoomUseError):
        ds.get_room_use_profile(99)


def test_profile_value_kind_not_applicable_returns_none() -> None:
    ds = _load_sample()
    profile = ds.get_room_use_profile(1)
    # 5.1.1.1 (Lüftungsvolumenstrom) is Standard-only; a missing kind is
    # answered with a ``value=None`` ParameterValue, never a KeyError.
    missing = profile.value("5.1.1.1", ValueKind.BESTAND)
    assert missing.value is None
    assert missing.unit.symbol == "m3/h"


def test_profile_value_unknown_parameter_raises() -> None:
    ds = _load_sample()
    with pytest.raises(UnknownParameterError):
        ds.get_room_use_profile(1).value("does-not-exist")


def test_list_climate_stations_and_lookup() -> None:
    ds = _load_sample()
    stations = ds.list_climate_stations()
    assert [station.id for station in stations] == [1, 40]
    assert ds.climate_station(40).name.de == "Zürich-MeteoSchweiz"
    # Empty Italian label falls back to German (TrilingualText behaviour).
    assert ds.climate_station(1).name.get("it") == "Basel-Binningen"
    assert ds.climate_station(1).winter_design["t_a"].value == -8.0
    with pytest.raises(UnknownClimateStationError):
        ds.climate_station(7)


def test_get_release_info() -> None:
    ds = _load_sample()
    info = ds.get_release_info()
    assert info["id"] == "V221"
    assert info["publication_date"] == "2024-11-17"
    assert info["room_use_count"] == 3
    assert info["parameter_count"] == 6
    assert info["profile_count"] == 3
    assert info["climate_station_count"] == 2
    assert info["content_checksum_sha256"] == info["checksum_sha256"]
    assert info["changelog"][0]["version"] == "V221"


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------


def test_compare_room_use_profiles_structured_diff() -> None:
    ds = _load_sample()
    diff = ds.compare_room_use_profiles(1, 3)
    assert diff.a_id == 1
    assert diff.b_id == 3
    assert not diff.identical
    assert diff.added == () and diff.removed == ()
    by_id = {entry.parameter_id: entry for entry in diff.changed}
    assert "1.1.2.7" in by_id
    entry = by_id["1.1.2.7"]
    assert entry.symbol == "g"
    assert entry.unit == "%"
    assert entry.diffs["standard"] == (0.7, 0.8)
    assert entry.diffs["zielwert"] == (0.6, 0.7)
    assert entry.diffs["bestand"] == (0.8, 0.9)


def test_compare_profiles_function() -> None:
    ds = _load_sample()
    diff = compare_profiles(ds.get_room_use_profile(1), ds.get_room_use_profile(2))
    by_id = {entry.parameter_id: entry for entry in diff.changed}
    # 1.1.2.7 differs in Zielwert only (0.6 vs 0.65).
    assert by_id["1.1.2.7"].diffs == {"zielwert": (0.6, 0.65)}
    # 1.1.2.1 is identical for all kinds and therefore not in ``changed``.
    assert "1.1.2.1" not in by_id


def test_compare_identical_profiles() -> None:
    ds = _load_sample()
    diff = ds.compare_room_use_profiles(1, 1)
    assert diff.identical
    assert diff.changed == ()
    assert diff.as_dict()["identical"] is True


def test_compare_profiles_as_dict_is_json_ready() -> None:
    ds = _load_sample()
    data = ds.compare_room_use_profiles(1, 3).as_dict()
    assert data["a_id"] == 1 and data["b_id"] == 3
    first = data["changed"][0]
    assert "parameter_id" in first and "diffs" in first and "label" in first
    assert json.dumps(data)  # serializable without custom encoders


def test_compare_different_releases_raises() -> None:
    ds = _load_sample()
    catalog_a = {parameter.id: parameter for parameter in ds.list_parameters()}
    catalog_b = {
        parameter.id: parameter for parameter in ds.list_parameters()[:1]
    }
    profile_a = RoomUseProfile(
        room_use=ds.room_use(1), values={}, parameter_catalog=catalog_a
    )
    profile_b = RoomUseProfile(
        room_use=ds.room_use(1), values={}, parameter_catalog=catalog_b
    )
    with pytest.raises(ValueError, match="different releases"):
        compare_profiles(profile_a, profile_b)


def test_compare_unknown_room_use_raises() -> None:
    ds = _load_sample()
    with pytest.raises(UnknownRoomUseError):
        ds.compare_room_use_profiles(1, 99)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_valid_sample() -> None:
    report = _load_sample().validate()
    assert report.valid
    assert report.errors == ()
    assert report.warnings == ()


def test_validate_duplicate_parameter_ids() -> None:
    package = _sample_package()
    package["parameters"].append(dict(package["parameters"][0]))
    report = parse_dataset(package, source="dup.json").validate()
    assert not report.valid
    assert any("duplicate parameter id" in error for error in report.errors)


def test_validate_duplicate_room_uses() -> None:
    package = _sample_package()
    package["room_uses"].append(dict(package["room_uses"][0]))
    report = parse_dataset(package, source="dup.json").validate()
    assert any("duplicate room use nutzid" in error for error in report.errors)


def test_validate_value_kind_not_applicable() -> None:
    package = _sample_package()
    # 5.1.1.1 is Standard-only; a Bestand value in the profile is invalid.
    package["profiles"][0]["values"]["5.1.1.1"]["bestand"] = {"value": 30.0, "unit": "m3/h"}
    report = parse_dataset(package, source="kind.json").validate()
    assert not report.valid
    assert any("'bestand' is not applicable" in error for error in report.errors)


def test_validate_parameter_without_value_kinds() -> None:
    package = _sample_package()
    package["parameters"][0]["value_kinds"] = []
    report = parse_dataset(package, source="kinds.json").validate()
    assert any("no applicable value kind" in error for error in report.errors)


def test_validate_missing_profile_for_room_use() -> None:
    package = _sample_package()
    package["profiles"] = [p for p in package["profiles"] if p["room_use_id"] != 3]
    report = parse_dataset(package, source="noprofile.json").validate()
    assert not report.valid
    assert any("no profile" in error for error in report.errors)


def test_validate_malformed_checksum_is_error() -> None:
    package = _sample_package()
    package["release"]["checksum_sha256"] = "not-a-checksum"
    report = parse_dataset(package, source="badsum.json").validate()
    assert not report.valid
    assert any("64-char hex" in error for error in report.errors)


def test_validate_checksum_mismatch_is_warning() -> None:
    package = _sample_package()
    package["parameters"][0]["symbol"] = "g_mod"
    report = parse_dataset(package, source="tampered.json").validate()
    assert report.valid
    assert any("checksum_sha256 does not match" in warning for warning in report.warnings)


def test_validate_empty_catalog() -> None:
    package = _sample_package()
    package["room_uses"] = []
    package["profiles"] = []
    report = parse_dataset(package, source="empty.json").validate()
    assert not report.valid
    assert any("no room uses" in error for error in report.errors)


def test_validate_report_as_dict() -> None:
    report = _load_sample().validate()
    assert report.as_dict() == {"valid": True, "errors": [], "warnings": []}


# ---------------------------------------------------------------------------
# Model constructors
# ---------------------------------------------------------------------------


def test_room_use_constructor_validation() -> None:
    name = TrilingualText(de="Wohnen MFH")
    room_use = RoomUse(nutzid=1, code="1.01", category=1, name=name)
    assert room_use.nutzid == 1
    with pytest.raises(ValueError, match="1–45"):
        RoomUse(nutzid=0, code="1.01", category=1, name=name)
    with pytest.raises(ValueError, match="1–45"):
        RoomUse(nutzid=46, code="1.01", category=1, name=name)
    with pytest.raises(ValueError, match="must not be empty"):
        RoomUse(nutzid=1, code="", category=1, name=name)


def test_parameter_constructor_validation() -> None:
    label = TrilingualText(de="Jahresgleichzeitigkeit")
    Parameter(
        id="1.1.2.7", label=label, symbol="g", unit="%", data_type="number",
        category="Raumklima", value_kinds=frozenset(ValueKind),
    )
    with pytest.raises(ValueError, match="must not be empty"):
        Parameter(
            id="", label=label, symbol="g", unit="%", data_type="number",
            category="Raumklima", value_kinds=frozenset(ValueKind),
        )
    with pytest.raises(ValueError, match="data_type"):
        Parameter(
            id="1.1.2.7", label=label, symbol="g", unit="%", data_type="bogus",
            category="Raumklima", value_kinds=frozenset(ValueKind),
        )
    with pytest.raises(UnitError):
        Parameter(
            id="1.1.2.7", label=label, symbol="g", unit="no-such-unit",
            data_type="number", category="Raumklima", value_kinds=frozenset(ValueKind),
        )


def test_parameter_unit_normalized_from_rich_text() -> None:
    parameter = Parameter(
        id="1.1.2.1", label=TrilingualText(de="Innentemperatur"), symbol="T_i",
        unit="W/m²", data_type="number", category="Raum",
        value_kinds=frozenset(ValueKind),
    )
    assert isinstance(parameter.unit, Unit)
    assert parameter.unit.symbol == "W/m2"  # superscript normalized


def test_climate_station_constructor_validation() -> None:
    name = TrilingualText(de="Zürich-MeteoSchweiz")
    ClimateStation(id=40, name=name, winter_design={}, summer_design={}, monthly={})
    with pytest.raises(ValueError, match="1–40"):
        ClimateStation(id=41, name=name, winter_design={}, summer_design={}, monthly={})
    with pytest.raises(ValueError, match="must not be empty"):
        ClimateStation(
            id=1, name=TrilingualText(), winter_design={}, summer_design={}, monthly={}
        )


def test_parameter_value_quantity_property() -> None:
    pv = ParameterValue(
        parameter_id="1.1.2.7", kind=ValueKind.STANDARD, value=0.7, unit="%"
    )
    assert pv.quantity.value == 0.7
    assert pv.quantity.unit.symbol == "%"


def test_dataset_constructor_rejects_unknown_profile_room_use() -> None:
    from energytools.common.versioning import DatasetRelease

    release = DatasetRelease(
        id="V221", edition="SIA 2024", publication_date=date(2024, 11, 17),
        checksum_sha256="0" * 64,
        source_workbook="2024_Raumdatenblätter_dfi_V221.xlsm",
        extraction_tool_version="0.1.0",
    )
    room_use = RoomUse(nutzid=1, code="1.01", category=1, name=TrilingualText(de="x"))
    parameter = Parameter(
        id="1.1.2.7", label=TrilingualText(de="x"), symbol="g", unit="%",
        data_type="number", category="Raum", value_kinds=frozenset(ValueKind),
    )
    catalog = {"1.1.2.7": parameter}
    with pytest.raises(ValueError, match="no matching room use"):
        Dataset(
            release=release,
            room_uses=(room_use,),
            parameters=(parameter,),
            profiles={99: RoomUseProfile(room_use=room_use, values={}, parameter_catalog=catalog)},
            climate_stations=(),
        )


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_error_hierarchy_hooks_into_common_tree() -> None:
    from energytools.dataset.errors import LoadError, ValidationError

    assert issubclass(DatasetError, EnergyToolsError)
    assert issubclass(NotFoundError, DatasetError)
    assert issubclass(NotFoundError, DatasetNotFoundErrorAlias)  # common DatasetNotFoundError
    assert issubclass(ValidationError, DatasetError)
    assert issubclass(ValidationError, DatasetValidationError)  # common DatasetValidationError
    assert issubclass(LoadError, DatasetError)
