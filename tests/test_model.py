"""Tests for energytools.raumdaten.model -- the canonical dataset model (part 03, section 1)."""

from __future__ import annotations

import pytest

from energytools.common.errors import (
    TableLookupError,
    UnknownClimateStationError,
    UnknownParameterError,
    UnknownRoomUseError,
)
from energytools.common.language import TrilingualText
from energytools.common.units import Quantity
from energytools.common.valuekind import ValueKind
from energytools.common.versioning import DatasetRelease
from energytools.raumdaten.model import (
    ClimateData,
    ClimateStation,
    Dataset,
    FullLoadHoursTable,
    HourlyProfile,
    MonthlyProfile,
    Parameter,
    ParameterValue,
    QhcTable,
    RoomUse,
    RoomUseProfile,
    TemperatureBin,
    WeeklyProfile,
    normalize_room_use_code,
)

RELEASE = DatasetRelease(
    id="V221",
    edition="SIA 2024",
    publication_date=__import__("datetime").date(2024, 11, 17),
    checksum_sha256="ab" * 32,
    source_workbook="2024_Raumdatenblätter_dfi_V221.xlsm",
    extraction_tool_version="0.1.0",
)


def _room_use(nutzid: int = 1, code: str = "1.01", category: int = 1) -> RoomUse:
    return RoomUse(
        nutzid=nutzid,
        code=code,
        category=category,
        name=TrilingualText(de=f"Name {nutzid}", fr=f"Nom {nutzid}", it=f"Nome {nutzid}"),
    )


def _parameter(
    parameter_id: str = "1.1.2.7", unit: str = "%", kinds=None, data_type: str = "number"
) -> Parameter:
    return Parameter(
        id=parameter_id,
        label=TrilingualText(de="Jahresgleichzeitigkeit"),
        symbol="fP",
        unit=unit,
        data_type=data_type,
        category="Personen",
        value_kinds=frozenset(kinds or {ValueKind.STANDARD, ValueKind.ZIELWERT, ValueKind.BESTAND}),
    )


class TestRoomUse:
    def test_constructor_validation(self) -> None:
        with pytest.raises(ValueError):
            RoomUse(nutzid=0, code="1.01", category=1, name=TrilingualText(de="x"))
        with pytest.raises(ValueError):
            RoomUse(nutzid=1, code="", category=1, name=TrilingualText(de="x"))
        with pytest.raises(ValueError):
            RoomUse(nutzid=46, code="1.01", category=1, name=TrilingualText(de="x"))

    def test_as_dict(self) -> None:
        data = _room_use().as_dict()
        assert data["nutzid"] == 1 and data["code"] == "1.01" and data["name"]["fr"] == "Nom 1"


class TestParameterAndValue:
    def test_parameter_validation(self) -> None:
        with pytest.raises(ValueError):
            Parameter(
                id="",
                label=TrilingualText(de="x"),
                symbol="s",
                unit="-",
                data_type="number",
                category="Raum",
                value_kinds=frozenset(),
            )
        with pytest.raises(ValueError):
            _parameter(data_type="unknown")

    def test_parameter_parses_unit(self) -> None:
        assert _parameter(unit="W/m2").unit.symbol == "W/m2"

    def test_parameter_value_quantity(self) -> None:
        value = ParameterValue(parameter_id="1.1.2.7", kind=ValueKind.STANDARD, value=0.7, unit="%")
        assert value.quantity == Quantity(0.7, "%")
        assert value.as_dict() == {"value": 0.7, "unit": "%", "provenance": None}

    def test_parameter_value_parses_kind(self) -> None:
        value = ParameterValue(parameter_id="x", kind="zielwert", value=1, unit="-")
        assert value.kind is ValueKind.ZIELWERT


class TestProfiles:
    def test_hourly_profile_length(self) -> None:
        with pytest.raises(ValueError):
            HourlyProfile(id="p", profile_type="person", values=(0.0,) * 23)
        with pytest.raises(ValueError):
            HourlyProfile(id="p", profile_type="nope", values=(0.0,) * 24)
        assert len(HourlyProfile(id="p", profile_type="person", values=(0.0,) * 24).values) == 24

    def test_monthly_and_weekly_lengths(self) -> None:
        with pytest.raises(ValueError):
            MonthlyProfile(id="m", values=(1.0,) * 11, unit="°C")
        with pytest.raises(ValueError):
            WeeklyProfile(id="w", values=(1.0,) * 6)

    def test_temperature_bin(self) -> None:
        with pytest.raises(ValueError):
            TemperatureBin(lower=5.0, upper=-5.0, hours=1.0)
        with pytest.raises(ValueError):
            TemperatureBin(lower=-5.0, upper=5.0, hours=-1.0)


class TestRoomUseProfile:
    def _profile(self) -> RoomUseProfile:
        catalog = {"1.1.2.7": _parameter()}
        values = {
            "1.1.2.7": {
                ValueKind.STANDARD: ParameterValue("1.1.2.7", ValueKind.STANDARD, 0.7, "%"),
                ValueKind.ZIELWERT: ParameterValue("1.1.2.7", ValueKind.ZIELWERT, 0.6, "%"),
            }
        }
        return RoomUseProfile(room_use=_room_use(), values=values, parameter_catalog=catalog)

    def test_value_lookup_and_missing_kind(self) -> None:
        profile = self._profile()
        assert profile.value("1.1.2.7", ValueKind.ZIELWERT).value == 0.6
        missing = profile.value(
            "1.1.2.7", ValueKind.BESTAND
        )  # not stored -> None value, no KeyError
        assert missing.value is None
        assert missing.unit.symbol == "%"

    def test_value_unknown_parameter(self) -> None:
        with pytest.raises(UnknownParameterError):
            self._profile().value("9.9.9")

    def test_inconsistent_catalog_rejected(self) -> None:
        with pytest.raises(ValueError):
            RoomUseProfile(
                room_use=_room_use(),
                values={"unknown-id": {}},
                parameter_catalog={"1.1.2.7": _parameter()},
            )

    def test_parameters_in_sheet_order(self) -> None:
        profile = self._profile()
        assert [p.id for p in profile.parameters()] == ["1.1.2.7"]

    def test_as_dict_shape(self) -> None:
        data = self._profile().as_dict(kind=ValueKind.STANDARD)
        assert data["room_use"]["code"] == "1.01"
        parameter = data["parameters"][0]
        assert parameter["id"] == "1.1.2.7"
        assert parameter["values"]["standard"]["value"] == 0.7
        assert "zielwert" not in parameter["values"]

    def test_to_frame(self) -> None:
        pytest.importorskip("pandas")
        frame = self._profile().to_frame(ValueKind.STANDARD)
        assert list(frame.columns) == ["id", "label", "symbol", "unit", "value"]
        assert frame.iloc[0]["value"] == 0.7


class TestClimate:
    def _station(self, station_id: int = 1) -> ClimateStation:
        return ClimateStation(
            id=station_id,
            name=TrilingualText(de="Adelboden"),
            winter_design={"t_a": Quantity(-10.2, "°C")},
            summer_design={},
            monthly={"t_aussen": MonthlyProfile(id="t_aussen", values=(1.0,) * 12, unit="°C")},
            hdd=Quantity(4670.0, "K·d"),
        )

    def test_station_validation(self) -> None:
        with pytest.raises(ValueError):
            ClimateStation(
                id=0, name=TrilingualText(de="x"), winter_design={}, summer_design={}, monthly={}
            )
        with pytest.raises(ValueError):
            ClimateStation(
                id=1, name=TrilingualText(de=""), winter_design={}, summer_design={}, monthly={}
            )

    def test_climate_data_lookup(self) -> None:
        climate = ClimateData(
            version="meteoschweiz-2024", stations=(self._station(1), self._station(2))
        )
        assert climate.ids() == (1, 2)
        assert climate.station("2").name.de == "Adelboden"
        with pytest.raises(UnknownClimateStationError):
            climate.station(40)
        with pytest.raises(ValueError):
            ClimateData(version="v", stations=(self._station(1), self._station(1)))


class TestLookupTables:
    def test_full_load_hours(self) -> None:
        table = FullLoadHoursTable(
            rows={(1, "2-stufig", "prSIA 2024-C1:2024"): 7540.0},
            standard_versions=frozenset({"prSIA 2024-C1:2024"}),
            regulations=frozenset({"1-stufig", "2-stufig", "stufenlos"}),
            room_use_ids=frozenset({1, 2}),
            release_id="V221",
        )
        assert table.hours(1, "2-stufig", "prSIA 2024-C1:2024") == 7540.0
        with pytest.raises(UnknownRoomUseError):
            table.hours(99, "2-stufig", "prSIA 2024-C1:2024")
        with pytest.raises(TableLookupError):
            table.hours(1, "stufenlos", "prSIA 2024-C1:2024")
        with pytest.raises(KeyError):  # TableLookupError is KeyError-compatible
            table.hours(1, "1-stufig", "prSIA 2024-C1:2024")

    def test_qhc_table(self) -> None:
        table = QhcTable(
            rows={(1, 40, ValueKind.STANDARD): Quantity(12.4, "kWh/m2")},
            room_use_ids=frozenset({1}),
            station_ids=frozenset({40}),
            release_id="V221",
        )
        assert table.qhc(1, 40).value == 12.4
        with pytest.raises(UnknownRoomUseError):
            table.qhc(2, 40)
        with pytest.raises(UnknownClimateStationError):
            table.qhc(1, 41)
        with pytest.raises(TableLookupError):
            table.qhc(1, 40, ValueKind.ZIELWERT)


class TestDataset:
    def _dataset(self) -> Dataset:
        room_uses = (_room_use(1, "1.01"), _room_use(2, "1.02", category=1))
        parameters = (_parameter(),)
        catalog = {p.id: p for p in parameters}
        profile_1 = RoomUseProfile(
            room_use=room_uses[0],
            values={
                "1.1.2.7": {
                    ValueKind.STANDARD: ParameterValue("1.1.2.7", ValueKind.STANDARD, 0.7, "%")
                }
            },
            parameter_catalog=catalog,
        )
        profile_2 = RoomUseProfile(
            room_use=room_uses[1],
            values={
                "1.1.2.7": {
                    ValueKind.STANDARD: ParameterValue("1.1.2.7", ValueKind.STANDARD, 0.8, "%")
                }
            },
            parameter_catalog=catalog,
        )
        station = ClimateStation(
            id=1,
            name=TrilingualText(de="Adelboden"),
            winter_design={},
            summer_design={},
            monthly={},
        )
        climate = ClimateData(version="meteoschweiz-2024", stations=(station,))
        return Dataset(
            release=RELEASE,
            room_uses=room_uses,
            parameters=parameters,
            profiles={1: profile_1, 2: profile_2},
            hourly_profiles=(),
            monthly_profiles=(),
            weekly_profiles=(),
            climate=climate,
            full_load_hours=FullLoadHoursTable(
                rows={},
                standard_versions=frozenset({"prSIA 2024-C1:2024"}),
                regulations=frozenset({"1-stufig"}),
            ),
            qhc=QhcTable(rows={}),
            sia3801=(),
            mappings=(),
            area_tables=(),
            sia3801_coefficients=(),
        )

    def test_lookups(self) -> None:
        dataset = self._dataset()
        assert dataset.release_id == "V221"
        assert dataset.room_use(1).code == "1.01"
        assert dataset.room_use("1.02").nutzid == 2
        assert len(dataset.room_uses()) == 2
        assert dataset.parameter("1.1.2.7").symbol == "fP"
        assert dataset.profile(1).value("1.1.2.7").value == 0.7
        with pytest.raises(UnknownRoomUseError):
            dataset.room_use(99)
        with pytest.raises(UnknownParameterError):
            dataset.parameter("9.9.9")
        assert dataset.climate().ids() == (1,)
        assert dataset.sia3801_results() == ()

    def test_code_quirk_normalization(self) -> None:
        assert normalize_room_use_code("12.1") == "12.10"
        assert normalize_room_use_code(" 1.01 ") == "1.01"

    def test_room_use_lookup_normalizes_quirk(self) -> None:
        """The documented quality quirk: code '12.1' is looked up as '12.10'."""
        dataset = self._dataset()
        quirk_use = RoomUse(
            nutzid=45, code="12.10", category=12, name=TrilingualText(de="Wasch- und Trockenraum")
        )
        profiles = dict(dataset.profiles)
        profiles[45] = RoomUseProfile(
            room_use=quirk_use,
            values={},
            parameter_catalog={p.id: p for p in dataset._parameters},
        )
        with_quirk = Dataset(
            release=RELEASE,
            room_uses=tuple(dataset._room_uses) + (quirk_use,),
            parameters=dataset._parameters,
            profiles=profiles,
            hourly_profiles=(),
            monthly_profiles=(),
            weekly_profiles=(),
            climate=dataset._climate,
            full_load_hours=dataset._full_load_hours,
            qhc=dataset._qhc,
            sia3801=(),
            mappings=(),
            area_tables=(),
            sia3801_coefficients=(),
        )
        assert with_quirk.room_use("12.10") is quirk_use
        assert with_quirk.room_use("12.1") is quirk_use  # normalized before lookup

    def test_inconsistent_profile_count_rejected(self) -> None:
        dataset = self._dataset()
        with pytest.raises(ValueError):
            Dataset(
                release=RELEASE,
                room_uses=dataset._room_uses,
                parameters=dataset._parameters,
                profiles={1: dataset.profiles[1]},  # missing profile for nutzid 2
                hourly_profiles=(),
                monthly_profiles=(),
                weekly_profiles=(),
                climate=dataset._climate,
                full_load_hours=dataset._full_load_hours,
                qhc=dataset._qhc,
                sia3801=(),
                mappings=(),
                area_tables=(),
                sia3801_coefficients=(),
            )

    def test_validate_reports_not_raises(self) -> None:
        report = self._dataset().validate()
        assert report.valid

    def test_roundtrip_package_dict(self) -> None:
        dataset = self._dataset()
        rebuilt = Dataset.from_package_dict(dataset.to_package_dict())
        assert rebuilt == dataset

    def test_equality_detects_content_change(self) -> None:
        dataset = self._dataset()
        other = self._dataset()
        assert dataset == other
        different = Dataset(
            release=RELEASE,
            room_uses=dataset._room_uses,
            parameters=dataset._parameters,
            profiles=dataset.profiles,
            hourly_profiles=(HourlyProfile(id="x", profile_type="person", values=(0.0,) * 24),),
            monthly_profiles=(),
            weekly_profiles=(),
            climate=dataset._climate,
            full_load_hours=dataset._full_load_hours,
            qhc=dataset._qhc,
            sia3801=(),
            mappings=(),
            area_tables=(),
            sia3801_coefficients=(),
        )
        assert dataset != different
