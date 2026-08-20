"""Tests for the engine input model: enums with German labels, value objects,
``BuildingInput`` validation, versions and the validation report."""

from __future__ import annotations

import json
from datetime import date

import pytest
from helpers import make_building_input

from energytools.engine.errors import UnknownValueKindError
from energytools.engine.model import (
    BuildingInput,
    EndUse,
    EnergyCarrier,
    GenerationSystem,
    ModelRelease,
    RoomRow,
    ValidationReport,
    ValueKind,
    VentilationSystem,
    VersionInfo,
)

# ---------------------------------------------------------------------------
# Enums: German workbook labels (德语源术语) + codes
# ---------------------------------------------------------------------------


def test_energy_carrier_parse_german_labels() -> None:
    assert EnergyCarrier.parse("Elektrizität") is EnergyCarrier.ELECTRICITY
    assert EnergyCarrier.parse("HEL") is EnergyCarrier.HEATING_OIL
    assert EnergyCarrier.parse("Erdgas") is EnergyCarrier.NATURAL_GAS
    assert EnergyCarrier.parse("Holz") is EnergyCarrier.WOOD
    assert EnergyCarrier.parse("Fernwärme") is EnergyCarrier.DISTRICT_HEATING
    assert EnergyCarrier.parse("fernkaelte") is EnergyCarrier.DISTRICT_COOLING
    assert EnergyCarrier.parse("el") is EnergyCarrier.ELECTRICITY
    assert EnergyCarrier.parse("erdgas") is EnergyCarrier.NATURAL_GAS
    with pytest.raises(ValueError):
        EnergyCarrier.parse("diesel")


def test_end_use_parse_german_labels() -> None:
    assert EndUse.parse("Kühlung") is EndUse.KUEHLUNG
    assert EndUse.parse("Geräte") is EndUse.GERAETE
    assert EndUse.parse("Lüftung") is EndUse.LUEFTUNG
    assert EndUse.parse("Heizung") is EndUse.HEIZUNG
    assert EndUse.parse("Warmwasser") is EndUse.WARMWASSER
    assert EndUse.parse("Beleuchtung") is EndUse.BELEUCHTUNG
    assert EndUse.parse("Allg. Gebäudetechnik") is EndUse.ALLGEMEINE_GEBAEUDETECHNIK
    assert EndUse.parse("lueftung") is EndUse.LUEFTUNG
    with pytest.raises(ValueError):
        EndUse.parse("Schwimmbad")


def test_value_kind_parse() -> None:
    assert ValueKind.parse("standard") is ValueKind.STANDARD
    assert ValueKind.parse("Zielwert") is ValueKind.ZIELWERT
    assert ValueKind.parse("BESTAND") is ValueKind.BESTAND
    assert ValueKind.parse("target") is ValueKind.ZIELWERT
    assert ValueKind.parse("existing") is ValueKind.BESTAND
    with pytest.raises(UnknownValueKindError):
        ValueKind.parse("optimal")


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


def test_room_row_effective_area() -> None:
    room = RoomRow(name="Büro 1", room_use_id="1.01", ebf=True, ngf=1200.0, share=0.5)
    assert room.effective_area() == pytest.approx(600.0)
    whole = RoomRow(name="Büro 2", room_use_id=3, ebf=True, ngf=100.0)
    assert whole.effective_area() == pytest.approx(100.0)


def test_room_row_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        RoomRow(name="x", room_use_id=1, ebf=True, ngf=-1.0)
    with pytest.raises(ValueError):
        RoomRow(name="x", room_use_id=1, ebf=True, ngf=10.0, geraete=-2.0)
    with pytest.raises(ValueError):
        RoomRow(name="x", room_use_id=1, ebf=True, ngf=10.0, share=-0.1)
    with pytest.raises(ValueError):
        RoomRow(name="x", room_use_id=1, ebf="yes", ngf=10.0)
    with pytest.raises(ValueError):
        RoomRow(name="  ", room_use_id=1, ebf=True, ngf=10.0)


def test_ventilation_effective_flow_priority() -> None:
    system = VentilationSystem(
        id="LA03",
        volume_flow_standard=1000.0,
        volume_flow_prozess=2000.0,
        volume_flow_projekt=3000.0,
    )
    assert system.effective_volume_flow() == pytest.approx(3000.0)
    two = VentilationSystem(id="LA04", volume_flow_standard=1000.0, volume_flow_prozess=2000.0)
    assert two.effective_volume_flow() == pytest.approx(2000.0)
    one = VentilationSystem(id="LA05", volume_flow_standard=500.0)
    assert one.effective_volume_flow() == pytest.approx(500.0)
    assert VentilationSystem(id="LA06").effective_volume_flow() is None


def test_ventilation_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        VentilationSystem(id="LA03", wrg=1.2)
    with pytest.raises(ValueError):
        VentilationSystem(id="LA03", wrg=-0.1)
    with pytest.raises(ValueError):
        VentilationSystem(id="LA03", regulation="kontinuierlich")
    with pytest.raises(ValueError):
        VentilationSystem(id="LA03", volume_flow_standard=-5.0)
    with pytest.raises(ValueError):
        VentilationSystem(id="LA03", humidity_setpoints={"x_soll": "hoch"})


def test_generation_system_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        GenerationSystem(id="KE1", kind="cooling", catalog_code="KE01", coverage=1.2, losses=0.05)
    with pytest.raises(ValueError):
        GenerationSystem(id="KE1", kind="cooling", catalog_code="KE01", coverage=1.0, losses=-0.05)
    with pytest.raises(ValueError):
        GenerationSystem(id="KE1", kind="dampf", catalog_code="KE01", coverage=1.0, losses=0.05)


# ---------------------------------------------------------------------------
# BuildingInput construction and validation
# ---------------------------------------------------------------------------


def test_building_input_constructor_guards() -> None:
    room = RoomRow(name="r", room_use_id=1, ebf=True, ngf=10.0)
    with pytest.raises(ValueError):
        BuildingInput(name="", rooms=(room,))
    with pytest.raises(ValueError):
        BuildingInput(name="Projekt", rooms=())


def test_building_input_value_kind_coercion() -> None:
    room = RoomRow(name="r", room_use_id=1, ebf=True, ngf=10.0)
    input_ = BuildingInput(name="x", rooms=(room,), value_kind="Zielwert")
    assert input_.value_kind is ValueKind.ZIELWERT
    with pytest.raises(UnknownValueKindError):
        BuildingInput(name="x", rooms=(room,), value_kind="optimal")


def test_validate_ok(project: BuildingInput) -> None:
    report = project.validate()
    assert report.valid
    assert report.errors == ()


def test_validate_climate_station_bounds() -> None:
    for bad in (0, 41):
        report = make_building_input(climate_station_id=bad).validate()
        assert not report.valid
        assert any("climate_station_id" in error for error in report.errors)


def test_validate_room_use_ids() -> None:
    for bad_use in ("9.9.9", "abc", True, 46, 0):
        bad = make_building_input(
            rooms=(RoomRow(name="R", room_use_id=bad_use, ebf=True, ngf=10.0),)  # type: ignore[arg-type]
        )
        assert not bad.validate().valid
    good = make_building_input(
        rooms=(RoomRow(name="R", room_use_id=45, ebf=True, ngf=10.0),)
    )
    assert good.validate().valid


def test_validate_ventilation_ids() -> None:
    bad = make_building_input(ventilation=(VentilationSystem(id="LA99", wrg=0.5),))
    report = bad.validate()
    assert any("LA01" in error for error in report.errors)
    duplicate = make_building_input(
        ventilation=(
            VentilationSystem(id="LA03"),
            VentilationSystem(id="LA03"),
        )
    )
    assert any("duplicate" in error for error in duplicate.validate().errors)


def test_validate_room_lueftung_reference(project: BuildingInput) -> None:
    # Defined LA03 -> no error, no warning.
    assert project.validate().valid
    # Undefined but well-formed LA04 -> warning, still valid.
    undefined = make_building_input(
        rooms=(RoomRow(name="Büro 1", room_use_id="1.01", ebf=True, ngf=1200.0, lueftung_system="LA04"),)
    )
    report = undefined.validate()
    assert report.valid
    assert any("LA04" in warning and "not defined" in warning for warning in report.warnings)
    # Malformed id -> hard error.
    malformed = make_building_input(
        rooms=(RoomRow(name="Büro 1", room_use_id="1.01", ebf=True, ngf=1200.0, lueftung_system="X99"),)
    )
    assert not malformed.validate().valid


def test_validate_warnings() -> None:
    suspicious = make_building_input(
        rooms=(RoomRow(name="Büro 1", room_use_id="1.01", ebf=True, ngf=1200.0, share=1.5),)
    )
    report = suspicious.validate()
    assert report.valid
    assert any("share" in warning for warning in report.warnings)


def test_total_ngf_and_ebf(project: BuildingInput) -> None:
    assert project.total_ngf() == pytest.approx(1350.0)
    assert project.total_ebf_area() == pytest.approx(1350.0)
    mixed = make_building_input(
        rooms=(
            RoomRow(name="A", room_use_id=1, ebf=False, ngf=500.0),
            RoomRow(name="B", room_use_id=2, ebf=True, ngf=100.0),
        )
    )
    assert mixed.total_ngf() == pytest.approx(600.0)
    assert mixed.total_ebf_area() == pytest.approx(100.0)


def test_inputs_hash_deterministic(project: BuildingInput) -> None:
    first = project.inputs_hash()
    assert first == project.inputs_hash()
    assert len(first) == 64
    other = make_building_input(name="Anderes Projekt")
    assert other.inputs_hash() != first


def test_building_input_json_roundtrip(project: BuildingInput) -> None:
    data = json.loads(json.dumps(project.as_dict()))
    restored = BuildingInput.from_dict(data)
    assert restored == project
    assert restored.inputs_hash() == project.inputs_hash()


# ---------------------------------------------------------------------------
# Versions and reports
# ---------------------------------------------------------------------------


def test_model_release_guards() -> None:
    ModelRelease(
        id="1.0.0",
        compatible_dataset_releases=frozenset({"V221"}),
        compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
        publication_date=date(2025, 4, 20),
    )
    with pytest.raises(ValueError):
        ModelRelease(
            id="not-semver",
            compatible_dataset_releases=frozenset({"V221"}),
            compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
            publication_date=date(2025, 4, 20),
        )
    with pytest.raises(ValueError):
        ModelRelease(
            id="1.0.0",
            compatible_dataset_releases=frozenset(),
            compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
            publication_date=date(2025, 4, 20),
        )


def test_version_info_as_dict() -> None:
    info = VersionInfo(
        dataset="V221", model="1.0.0", implementation="0.1.0", climate="meteoschweiz-2024"
    )
    assert info.as_dict() == {
        "dataset": "V221",
        "model": "1.0.0",
        "implementation": "0.1.0",
        "climate": "meteoschweiz-2024",
    }


def test_validation_report() -> None:
    report = ValidationReport(errors=("a",), warnings=("w",))
    assert not report.valid
    assert ValidationReport().valid
    assert report.as_dict() == {"valid": False, "errors": ["a"], "warnings": ["w"]}
