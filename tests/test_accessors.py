"""Tests for the attribute-style (dot-syntax) accessors."""

from __future__ import annotations

import pytest

from energytools.raumdaten import load_dataset
from energytools.raumdaten.accessors import (
    PARAMETER_ALIASES,
    ROOM_USE_SLUGS,
    ParameterAccessor,
    ParameterCatalog,
    RoomUseCatalog,
    parameter_slug,
    slugify_label,
)

pytestmark = pytest.mark.usefixtures("dataset")


def test_room_use_slug_access(dataset):
    group_office = dataset.room_uses.group_office
    assert group_office.code == "3.01"
    assert group_office.name.de == "Einzel-, Gruppenbüro"
    assert dataset.room_uses.classroom.code == "4.01"
    assert dataset.room_uses.residential_mfh.code == "1.01"
    assert dataset.room_uses.server_room.code == "12.12"


def test_room_use_catalog_getitem_and_iteration(dataset):
    cat = dataset.room_uses
    assert cat["3.01"] is cat.group_office
    assert cat["group_office"] is cat.group_office
    assert cat[5].code == "3.01"
    assert len(cat) == 45
    assert len(list(cat)) == 45
    with pytest.raises(KeyError):
        cat["99.99"]


def test_room_use_catalog_callable_compat(dataset):
    # Old API: ds.room_uses() still returns the tuple.
    assert len(dataset.room_uses()) == 45
    assert dataset.room_uses()[0].code == "1.01"


def test_room_use_catalog_typo_message(dataset):
    with pytest.raises(AttributeError, match="group_office"):
        dataset.room_uses.group_offce


def test_parameter_slug_access(dataset):
    prof = dataset.profile(dataset.room_uses.group_office.nutzid)
    acc = prof.personnel_area
    assert isinstance(acc, ParameterAccessor)
    assert acc.standard.value == 14
    assert acc.standard.unit.symbol == "m2"
    # symbol-derived slug works too
    assert prof.Uw.zielwert.value == 0.8
    # value kinds as properties
    assert acc.standard is not None
    with pytest.raises(AttributeError):
        _ = prof.personnel_area.nonexistent_kind


def test_parameter_catalog_access(dataset):
    p = dataset.parameters.personnel_area
    assert p.id == "1.1.2.9"
    assert dataset.parameters["1.1.2.9"] is p
    assert dataset.parameters["personnel_area"] is p
    assert len(dataset.parameters) == 193
    assert len(list(dataset.parameters)) == 193
    # callable compat
    assert len(dataset.parameters()) == 193
    with pytest.raises(KeyError):
        dataset.parameters["1.1.99.99"]


def test_dot_notation_three_user_questions(dataset):
    """The three canonical user questions, dot-syntax only."""
    # 1. group-office personnel area
    prof = dataset.profile(dataset.room_uses.group_office.nutzid)
    persons_per_m2 = 1.0 / prof.personnel_area.standard.value
    assert persons_per_m2 == pytest.approx(1 / 14)
    # 2. classroom exists with its own profile
    classroom = dataset.room_uses.classroom
    assert dataset.profile(classroom.nutzid).room_use.code == "4.01"
    # 3. parameters are reachable without ids
    assert dataset.parameters.fresh_air_per_person.id == "1.1.5.1"


def test_generated_properties_exist_in_dir(dataset):
    names = {name for name in dir(dataset.room_uses) if not name.startswith("_")}
    assert "group_office" in names
    assert "classroom" in names
    assert len(names) >= 45
    pnames = {name for name in dir(dataset.parameters) if not name.startswith("_")}
    assert "personnel_area" in pnames
    assert len(pnames) >= 180  # 193 params minus a few reserved-name/illegal slugs


def test_slug_tables_are_complete():
    assert len(ROOM_USE_SLUGS) == 45
    assert len(PARAMETER_ALIASES) >= 30
    assert set(ROOM_USE_SLUGS.values()) == set(ROOM_USE_SLUGS.values())  # unique
    assert len(set(ROOM_USE_SLUGS.values())) == 45


def test_slugify_label():
    assert slugify_label("Norm Aussentemperatur") == "norm_aussentemperatur"
    assert slugify_label("Wärmedämmwert der Bekleidung") == "waermedaemmwert_der_bekleidung"
    assert slugify_label("Personenfläche") == "personenflaeche"


def test_parameter_slug_priority():
    # alias wins over symbol
    assert parameter_slug("1.1.2.9", "AP,NGF", "Personenfläche") == "personnel_area"
    # symbol fallback
    assert parameter_slug("x.y.z", "Uw", "U-Wert Fenster") == "Uw"
    # label fallback
    assert parameter_slug("x.y.z", "", "Norm Aussentemperatur") == "norm_aussentemperatur"
