"""Tests for energytools.raumdaten.service -- the read-only query API (part 03, section 3)."""

from __future__ import annotations

import json

import pytest

from energytools.common.errors import (
    DatasetNotFoundError,
    ExportError,
    UnknownClimateStationError,
    UnknownLanguageError,
    UnknownParameterError,
    UnknownRoomUseError,
    UnknownValueKindError,
)


class TestReleases:
    def test_list_releases(self, service) -> None:
        releases = service.list_releases()
        assert releases[0]["id"] == "V221"
        assert set(releases[0]) == {
            "id",
            "edition",
            "publication_date",
            "checksum_sha256",
            "supersedes",
        }

    def test_get_release_latest_and_missing(self, service) -> None:
        release = service.get_release("latest")
        assert release["id"] == "V221"
        assert release["changelog"][0]["version"] == "V221"
        with pytest.raises(DatasetNotFoundError):
            service.get_release("V222")


class TestRoomUses:
    def test_list_room_uses_localized(self, service) -> None:
        uses = service.list_room_uses("V221", "fr")
        assert uses[0] == {"nutzid": 1, "code": "1.01", "category": 1, "name": "Habitat collectif"}
        with pytest.raises(UnknownLanguageError):
            service.list_room_uses("V221", "en")

    def test_get_room_use_by_code(self, service) -> None:
        data = service.get_room_use("V221", "3.01")
        assert data["nutzid"] == 5
        assert data["name"]["de"] == "Einzel-, Gruppenbüro"
        with pytest.raises(UnknownRoomUseError):
            service.get_room_use("V221", 99)

    def test_get_room_use_profile(self, service) -> None:
        profile = service.get_room_use_profile("V221", 1, "zielwert")
        assert profile["room_use"]["code"] == "1.01"
        assert len(profile["parameters"]) == 193  # one entry per Datenblatt row
        uop = next(p for p in profile["parameters"] if p["id"] == "Uop")
        assert uop["label"] == "U-Wert opake Bauteile"
        assert uop["values"]["zielwert"]["value"] == 0.1
        with pytest.raises(UnknownValueKindError):
            service.get_room_use_profile("V221", 1, "optimal")


class TestParameters:
    def test_list_parameters(self, service) -> None:
        parameters = service.list_parameters("V221")
        assert len(parameters) == 193
        # the catalog preserves the Datenblatt rows 4..196 one-to-one (the
        # first entries are the sheet header row and the Raum section)
        assert [p["id"] for p in parameters][:3] == ["Symbol", "qo", "norm-lufttemperatur-k-hlerauslegung"]
        assert parameters[0]["unit"] == "-"

    def test_get_parameter(self, service) -> None:
        parameter = service.get_parameter("V221", "1.1.3.3")
        assert parameter["symbol"] == "pA"
        assert parameter["category"] == "Geräte und Prozessanlagen"
        with pytest.raises(UnknownParameterError):
            service.get_parameter("V221", "9.9.9")


class TestCompare:
    def test_compare_room_use_profiles(self, service) -> None:
        diff = service.compare_room_use_profiles("V221", "1.01", "1.02")
        assert diff["a"] == 1 and diff["b"] == 2
        assert not diff["identical"]
        changed = {entry["parameter_id"]: entry for entry in diff["changed"]}
        assert "1.1.2.9" in changed  # Personenfläche differs between Wohnen MFH and EFH
        assert changed["1.1.2.9"]["diffs"]["standard"] == [35, 50]
        assert "1.1.2.7" not in changed  # Jahresgleichzeitigkeit is equal for both


class TestClimate:
    def test_list_climate_stations(self, service) -> None:
        stations = service.list_climate_stations("V221")
        assert stations[0]["name"] == "Adelboden"
        assert len(stations) == 40

    def test_get_climate_station(self, service) -> None:
        station = service.get_climate_station("V221", 1)
        assert station["winter_design"]["t_a"] == {"value": -10.2, "unit": "°C"}
        assert station["hdd"]["unit"] == "K·d"
        assert len(station["monthly"]["t_aussen"]["values"]) == 12
        with pytest.raises(UnknownClimateStationError):
            service.get_climate_station("V221", 41)


class TestProfilesAndTables:
    def test_list_profiles(self, service) -> None:
        data = service.list_profiles("V221")
        assert len(data["hourly"]) == 6
        assert len(data["hourly"][0]["values"]) == 24
        assert len(data["monthly"]) == 360  # 40 stations x 9 monthly series
        assert len(data["weekly"]) == 0

    def test_get_full_load_hours(self, service) -> None:
        data = service.get_full_load_hours("V221", 1, "2-stufig", "prSIA 2024-C1:2024")
        assert data["hours"] == 7540.0
        assert data["unit"] == "h/a"
        with pytest.raises(UnknownRoomUseError):
            service.get_full_load_hours("V221", 99, "2-stufig", "prSIA 2024-C1:2024")

    def test_get_qhc(self, service) -> None:
        data = service.get_qhc("V221", 4, 1)
        assert data["qhc"]["value"] == pytest.approx(5.657977024881182)
        assert data["qhc"]["unit"] == "kWh/m2"

    def test_get_sia3801(self, service) -> None:
        data = service.get_sia3801("V221", 1, "de+qc")
        assert data["values"]["Qh"]["unit"] == "kWh/m2a"


class TestValidateAndExport:
    def test_validate(self, service) -> None:
        report = service.validate("V221")
        assert report["release_id"] == "V221"
        assert report["valid"] is True
        assert report["errors"] == []
        # the workbook's matrix/row inconsistencies are reported as warnings
        # (e.g. profile values for kinds the Datenblatt row does not carry)
        assert len(report["warnings"]) == 107
        with pytest.raises(DatasetNotFoundError):
            service.validate("V999")

    def test_export_json_scoped(self, service, tmp_path) -> None:
        target = tmp_path / "out.json"
        result = service.export("V221", "json", "climate", str(target))
        assert result["format"] == "json" and result["scope"] == "climate"
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert set(payload) == {"schema_version", "release", "climate"}
        assert (
            result["checksum"] == service.export("V221", "json", "climate", str(target))["checksum"]
        )

    def test_export_unsupported_format(self, service, tmp_path) -> None:
        with pytest.raises(ExportError, match="not available"):
            service.export("V221", "xlsx", "all", str(tmp_path / "out.xlsx"))
