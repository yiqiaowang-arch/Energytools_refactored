"""Tests for energytools.common -- the cross-cutting foundation (part 02)."""

from __future__ import annotations

from datetime import date

import pytest

from energytools.common.errors import (
    DatasetNotFoundError,
    EnergyToolsError,
    TableLookupError,
    UnitError,
    UnknownLanguageError,
    UnknownRoomUseError,
    UnknownValueKindError,
)
from energytools.common.language import Language, TrilingualText
from energytools.common.provenance import Provenance, SourceRef
from energytools.common.units import Quantity, Unit, register_unit
from energytools.common.validation import ValidationReport
from energytools.common.valuekind import ValueKind
from energytools.common.versioning import (
    ChangelogEntry,
    DatasetRelease,
    ModelRelease,
    VersionResolver,
)


class TestErrors:
    def test_base_error_carries_details(self) -> None:
        error = EnergyToolsError("boom", {"step": 3})
        assert str(error) == "boom"
        assert error.details == {"step": 3}

    def test_dataset_not_found_message(self) -> None:
        assert str(DatasetNotFoundError("V222")) == "Dataset release 'V222' not found"

    def test_unknown_room_use_message(self) -> None:
        error = UnknownRoomUseError(99, "V221")
        assert str(error) == "Room use '99' not found in release 'V221'"

    def test_table_lookup_error_is_key_error_compatible(self) -> None:
        error = TableLookupError("combo missing")
        assert isinstance(error, EnergyToolsError)
        assert isinstance(error, KeyError)
        assert str(error) == "combo missing"


class TestLanguage:
    def test_parse_indices_and_codes(self) -> None:
        assert Language.parse("1") is Language.DE
        assert Language.parse("FR") is Language.FR
        assert Language.parse("it") is Language.IT

    def test_parse_unknown(self) -> None:
        with pytest.raises(UnknownLanguageError):
            Language.parse("en")

    def test_get_falls_back_to_german(self) -> None:
        text = TrilingualText(de="Wohnen MFH", fr="Habitat collectif")
        assert text.get("fr") == "Habitat collectif"
        assert text.get("it") == "Wohnen MFH"  # empty Italian -> German fallback

    def test_as_dict(self) -> None:
        assert TrilingualText(de="a", fr="b", it="c").as_dict() == {"de": "a", "fr": "b", "it": "c"}


class TestValueKind:
    def test_parse(self) -> None:
        assert ValueKind.parse("Zielwert") is ValueKind.ZIELWERT
        assert ValueKind.parse("target") is ValueKind.ZIELWERT
        assert ValueKind.parse("existing") is ValueKind.BESTAND

    def test_parse_unknown(self) -> None:
        with pytest.raises(UnknownValueKindError):
            ValueKind.parse("optimal")


class TestUnits:
    def test_known_symbol_and_conversion(self) -> None:
        w_per_m2 = Unit("W/m2")
        kw_per_m2 = Unit("kW/m2")
        assert w_per_m2.convert_to(1000.0, kw_per_m2) == pytest.approx(1.0)

    def test_normalizes_workbook_spellings(self) -> None:
        assert Unit("W/(m²K)").symbol == "W/(m2K)"
        assert Unit("kWh/m²").symbol == "kWh/m2"
        assert Unit("W/m2 × K").symbol == "W/m2xK"

    def test_unknown_symbol_raises(self) -> None:
        with pytest.raises(UnitError):
            Unit("not-a-unit")

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(UnitError):
            Unit("kWh").convert_to(1.0, Unit("m2"))

    def test_temperature_conversion(self) -> None:
        assert Unit("°C").convert_to(0.0, Unit("K")) == pytest.approx(273.15)

    def test_register_custom_unit(self) -> None:
        register_unit("myunit", "custom_dim")
        assert Unit("myunit").dimension == "custom_dim"

    def test_quantity(self) -> None:
        q = Quantity(50.0, "kWh/m2")
        assert q.to("MWh/m2").format() == "0.05 MWh/m2"
        assert q.as_dict() == {"value": 50.0, "unit": "kWh/m2"}
        assert Quantity(None, "kWh/m2").format() == "-"


class TestProvenance:
    def test_source_ref_requires_range_or_formula(self) -> None:
        with pytest.raises(ValueError):
            SourceRef(workbook="w.xlsm", sheet="Datenblatt")

    def test_provenance_dict(self) -> None:
        ref = SourceRef(workbook="w.xlsm", sheet="Datenblatt", range="M11")
        provenance = Provenance(sources=(ref,), note="note")
        assert provenance.as_dict()["note"] == "note"
        assert provenance.as_dict()["sources"][0]["range"] == "M11"


class TestVersioning:
    def _release(
        self, release_id: str = "V221", publication_date: date = date(2024, 11, 17)
    ) -> DatasetRelease:
        return DatasetRelease(
            id=release_id,
            edition="SIA 2024",
            publication_date=publication_date,
            checksum_sha256="ab" * 32,
            source_workbook="2024_Raumdatenblätter_dfi_V221.xlsm",
            extraction_tool_version="0.1.0",
            changelog=(
                ChangelogEntry(version=release_id, date=publication_date, change="release"),
            ),
        )

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            DatasetRelease(
                id="",
                edition="SIA 2024",
                publication_date=date(2024, 11, 17),
                checksum_sha256="ab" * 32,
                source_workbook="w",
                extraction_tool_version="0.1.0",
            )

    def test_model_release_semver(self) -> None:
        with pytest.raises(ValueError):
            ModelRelease(
                id="not-semver",
                compatible_dataset_releases=frozenset({"V221"}),
                compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
                publication_date=date(2025, 4, 20),
            )

    def test_resolver_latest_and_errors(self) -> None:
        older = self._release("V220", date(2023, 1, 1))
        newer = self._release("V221", date(2024, 11, 17))
        resolver = VersionResolver(datasets={"V220": older, "V221": newer})
        assert resolver.resolve_dataset("latest") is newer
        assert resolver.list_datasets() == [newer, older]
        with pytest.raises(DatasetNotFoundError):
            resolver.resolve_dataset("V199")

    def test_current_version_info(self) -> None:
        resolver = VersionResolver(
            datasets={"V221": self._release()},
            models={
                "1.0.0": ModelRelease(
                    id="1.0.0",
                    compatible_dataset_releases=frozenset({"V221"}),
                    compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
                    publication_date=date(2025, 4, 20),
                )
            },
            implementation_version="0.1.0",
            climate_versions={"V221": "meteoschweiz-2024"},
        )
        info = resolver.current()
        assert info.as_dict() == {
            "dataset": "V221",
            "model": "1.0.0",
            "implementation": "0.1.0",
            "climate": "meteoschweiz-2024",
        }


class TestValidationReport:
    def test_valid_and_as_dict(self) -> None:
        report = ValidationReport(errors=("e1",), warnings=("w1",))
        assert not report.valid
        assert report.as_dict() == {"valid": False, "errors": ["e1"], "warnings": ["w1"]}
        assert ValidationReport().valid
