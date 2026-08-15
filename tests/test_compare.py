"""Tests for energytools.raumdaten.compare -- profile comparison (part 03, section 4)."""

from __future__ import annotations

import pytest

from energytools.common.language import TrilingualText
from energytools.common.valuekind import ValueKind
from energytools.raumdaten.compare import compare_profiles
from energytools.raumdaten.model import Parameter, ParameterValue, RoomUse, RoomUseProfile

KINDS = {ValueKind.STANDARD, ValueKind.ZIELWERT, ValueKind.BESTAND}

CATALOG = {
    "1.1.2.7": Parameter(
        id="1.1.2.7",
        label=TrilingualText(de="Jahresgleichzeitigkeit"),
        symbol="fP",
        unit="-",
        data_type="number",
        category="Personen",
        value_kinds=frozenset(KINDS),
    ),
    "1.1.7.6": Parameter(
        id="1.1.7.6",
        label=TrilingualText(de="Norm-Heizlast"),
        symbol="FHL",
        unit="W/m2",
        data_type="number",
        category="Raumheizung",
        value_kinds=frozenset(KINDS),
    ),
}
OTHER_CATALOG = dict(CATALOG)
OTHER_CATALOG["9.9.9"] = Parameter(
    id="9.9.9",
    label=TrilingualText(de="X"),
    symbol="X",
    unit="-",
    data_type="number",
    category="Raum",
    value_kinds=frozenset({ValueKind.STANDARD}),
)


def _profile(nutzid: int, values: dict) -> RoomUseProfile:
    room_use = RoomUse(
        nutzid=nutzid,
        code=f"{nutzid}.01",
        category=1,
        name=TrilingualText(de=f"Name {nutzid}"),
    )
    return RoomUseProfile(room_use=room_use, values=values, parameter_catalog=CATALOG)


def _value(parameter_id: str, kind: ValueKind, value) -> ParameterValue:
    return ParameterValue(parameter_id=parameter_id, kind=kind, value=value, unit="-")


def _values(parameter_id: str, standard=None, zielwert=None, bestand=None) -> dict:
    result = {}
    if standard is not None:
        result[ValueKind.STANDARD] = _value(parameter_id, ValueKind.STANDARD, standard)
    if zielwert is not None:
        result[ValueKind.ZIELWERT] = _value(parameter_id, ValueKind.ZIELWERT, zielwert)
    if bestand is not None:
        result[ValueKind.BESTAND] = _value(parameter_id, ValueKind.BESTAND, bestand)
    return result


class TestCompareProfiles:
    def test_identical_profiles(self) -> None:
        a = _profile(1, {"1.1.2.7": _values("1.1.2.7", 0.7, 0.6, 0.8)})
        b = _profile(2, {"1.1.2.7": _values("1.1.2.7", 0.7, 0.6, 0.8)})
        diff = compare_profiles(a, b)
        assert diff.identical
        assert diff.changed == () and diff.added == () and diff.removed == ()
        assert diff.as_dict()["identical"] is True

    def test_changed_values_per_kind(self) -> None:
        a = _profile(1, {"1.1.7.6": _values("1.1.7.6", 15.5, 11.59, 53.89)})
        b = _profile(2, {"1.1.7.6": _values("1.1.7.6", 19.7, 11.59, 60.0)})
        diff = compare_profiles(a, b)
        assert not diff.identical
        assert len(diff.changed) == 1
        changed = diff.changed[0]
        assert changed.parameter_id == "1.1.7.6"
        assert changed.diffs == {"standard": (15.5, 19.7), "bestand": (53.89, 60.0)}
        assert changed.as_dict()["diffs"]["standard"] == [15.5, 19.7]

    def test_added_and_removed_parameters(self) -> None:
        a = _profile(1, {"1.1.2.7": _values("1.1.2.7", 0.7)})
        b = _profile(2, {"1.1.7.6": _values("1.1.7.6", 15.5)})
        diff = compare_profiles(a, b)
        assert diff.removed == ("1.1.2.7",)
        assert diff.added == ("1.1.7.6",)
        assert not diff.identical

    def test_kind_present_on_one_side_only(self) -> None:
        a = _profile(1, {"1.1.7.6": _values("1.1.7.6", standard=15.5)})
        b = _profile(2, {"1.1.7.6": _values("1.1.7.6", standard=15.5, zielwert=10.0)})
        diff = compare_profiles(a, b)
        assert diff.changed[0].diffs == {"zielwert": (None, 10.0)}

    def test_different_releases_rejected(self) -> None:
        a = _profile(1, {})
        b = RoomUseProfile(
            room_use=a.room_use,
            values={},
            parameter_catalog=OTHER_CATALOG,
        )
        with pytest.raises(ValueError, match="different releases"):
            compare_profiles(a, b)

    def test_as_dict_shape(self) -> None:
        a = _profile(1, {"1.1.7.6": _values("1.1.7.6", 15.5)})
        b = _profile(2, {"1.1.7.6": _values("1.1.7.6", 19.7)})
        data = compare_profiles(a, b).as_dict()
        assert data["a"] == 1 and data["b"] == 2
        assert data["changed"][0]["diffs"]["standard"] == [15.5, 19.7]
        assert data["added"] == [] and data["removed"] == []
