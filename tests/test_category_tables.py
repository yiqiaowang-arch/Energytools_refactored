"""Tests for the per-category reference tables (batch C: ``CategoryTable``).

Covers the model round-trips (:class:`CategoryTable` and its place in
:class:`~energytools.raumdaten.model.Dataset`) plus the real-package content
extracted from the Fläche family sheets and GEPAMOD: the 22-category
per-category blocks, the SIA 380/1 Tab. 27 room temperature of category I
(= 20 °C) and the GEPAMOD EBF table.
"""

from __future__ import annotations

from datetime import date

import pytest

from energytools.common.errors import TableLookupError
from energytools.common.language import TrilingualText
from energytools.common.units import Quantity
from energytools.common.valuekind import ValueKind
from energytools.common.versioning import DatasetRelease
from energytools.raumdaten.model import (
    CategoryTable,
    ClimateData,
    ClimateStation,
    Dataset,
    FullLoadHoursTable,
    Parameter,
    QhcTable,
    RoomUse,
    RoomUseProfile,
)

RELEASE = DatasetRelease(
    id="V221",
    edition="SIA 2024",
    publication_date=date(2024, 11, 17),
    checksum_sha256="ab" * 32,
    source_workbook="2024_Raumdatenblätter_dfi_V221.xlsm",
    extraction_tool_version="0.1.0",
)

#: The 22 SIA 2024 base-block category codes (row 1 of the Fläche sheets).
CATEGORIES_22 = (
    "I", "I.1", "I.2", "II", "III", "IV", "IV.1", "IV.2", "V", "V.1",
    "V.2", "V.3", "VI", "VII", "VIII", "VIII.1", "VIII.2", "IX", "X",
    "XI", "XII", "XIII",
)


def _category_table() -> CategoryTable:
    """A small table: 2 metrics x 3 categories (unit ``kWh/m2``)."""
    return CategoryTable(
        kind="energy_standard",
        variant="standard",
        rows={
            ("I", "Geräte"): Quantity(14.688, "kWh/m2"),
            ("I.1", "Geräte"): Quantity(14.688, "kWh/m2"),
            ("I", "Beleuchtung"): Quantity(2.153, "kWh/m2"),
        },
        unit="kWh/m2",
    )


def _minimal_dataset(category_tables=()) -> Dataset:
    room_uses = (
        RoomUse(nutzid=1, code="1.01", category=1, name=TrilingualText(de="Wohnen MFH")),
        RoomUse(nutzid=2, code="1.02", category=1, name=TrilingualText(de="Wohnen EFH")),
    )
    parameters = (
        Parameter(
            id="1.1.2.7",
            label=TrilingualText(de="Jahresgleichzeitigkeit"),
            symbol="fP",
            unit="%",
            data_type="number",
            category="Personen",
            value_kinds=frozenset({ValueKind.STANDARD, ValueKind.ZIELWERT, ValueKind.BESTAND}),
        ),
    )
    catalog = {parameter.id: parameter for parameter in parameters}
    profiles = {
        nutzid: RoomUseProfile(
            room_use=room_use, values={}, parameter_catalog=catalog
        )
        for nutzid, room_use in enumerate(room_uses, start=1)
    }
    station = ClimateStation(
        id=1,
        name=TrilingualText(de="Adelboden"),
        winter_design={},
        summer_design={},
        monthly={},
    )
    return Dataset(
        release=RELEASE,
        room_uses=room_uses,
        parameters=parameters,
        profiles=profiles,
        hourly_profiles=(),
        monthly_profiles=(),
        weekly_profiles=(),
        climate=ClimateData(version="meteoschweiz-2024", stations=(station,)),
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
        category_tables=category_tables,
    )


class TestCategoryTable:
    def test_construction_and_validation(self) -> None:
        with pytest.raises(ValueError):
            CategoryTable(kind="", rows={})
        with pytest.raises(ValueError):
            CategoryTable(kind="energy_standard", variant="", rows={})
        table = CategoryTable(kind="energy_standard", variant="standard", rows={})
        assert table.unit == "-"

    def test_as_dict_round_trip(self) -> None:
        table = _category_table()
        data = table.as_dict()
        assert data["kind"] == "energy_standard"
        assert data["variant"] == "standard"
        assert data["unit"] == "kWh/m2"
        assert data["rows"]["I"]["Geräte"] == {"value": 14.688, "unit": "kWh/m2"}

    def test_metric_lookup(self) -> None:
        table = _category_table()
        assert table.metric("Geräte", "I").value == 14.688
        assert table.metric("Geräte").value == 14.688
        with pytest.raises(TableLookupError):
            table.metric("Heizung", "I")

    def test_dataset_round_trip(self) -> None:
        table = _category_table()
        dataset = _minimal_dataset((table,))
        assert dataset.category_tables() == (table,)
        rebuilt = Dataset.from_package_dict(dataset.to_package_dict())
        assert rebuilt == dataset
        assert rebuilt.category_tables() == (table,)

    def test_dataset_validate_accepts_arbitrary_category_codes(self) -> None:
        # category codes of the reference tables are not validated against the
        # building-category mappings (the GEPAMOD columns use SIA 380/1
        # subcategory codes such as "I.1" / "II")
        dataset = _minimal_dataset(
            (
                CategoryTable(
                    kind="gepamod_end_energy",
                    variant="reference",
                    rows={("II", "Endenergie / Beleuchtung"): Quantity(2.0, "kWh/m2")},
                ),
            )
        )
        report = dataset.validate()
        assert report.valid, report.errors

    def test_package_dict_without_category_tables_loads(self) -> None:
        # packages that predate batch C have no "category_tables" key
        package = _minimal_dataset().to_package_dict()
        del package["category_tables"]
        reloaded = Dataset.from_package_dict(package)
        assert reloaded.category_tables() == ()


class TestRealPackage:
    """Assertions against the extracted V221 package (``data/datasets``)."""

    def test_all_expected_kinds_present(self, dataset) -> None:
        kinds = {table.kind for table in dataset.category_tables()}
        assert kinds == {
            "energy_standard",
            "energy_zielwert",
            "energy_bestand",
            "energy_power",
            "sia3801_tab27",
            "harmonized",
            "sia2040",
            "weighted_energy",
            "electric_energy",
            "minergie",
            "strommodell",
            "ww_demand",
            "ventilation_flow",
            "person_gain",
            "person_area",
            "room_temperature",
            "gepamod_end_energy",
            "gepamod_ebf",
            "gepamod_subcategory",
        }

    def test_energy_blocks_cover_22_categories(self, dataset) -> None:
        # the per-category blocks exist per sheet variant; the "SIA 2024
        # Standardwerte" block of Fläche-E covers the full 22-category row-1
        # header of the shared 45-row (room-use) matrix, 21 metric rows here
        variants = {table.variant for table in dataset.category_tables() if table.kind == "energy_standard"}
        assert variants == {"standard"}
        for kind in ("energy_standard", "energy_zielwert", "energy_bestand", "energy_power"):
            tables = [t for t in dataset.category_tables() if t.kind == kind]
            assert tables, kind
            categories = {category for t in tables for category, _ in t.rows}
            assert categories == set(CATEGORIES_22), kind
        # the base area-% matrix of Fläche-E carries the same 22 categories
        # (45 room-use rows of the sheet; only codes with a non-zero share
        # appear in the extracted table)
        area = dataset.area_tables()[0]
        assert set(area.rows) == set(CATEGORIES_22)

    def test_sia3801_tab27_raumtemperatur_category_I(self, dataset) -> None:
        table = next(
            t for t in dataset.category_tables()
            if t.kind == "sia3801_tab27" and t.variant == "standard"
        )
        quantity = table.rows[("I", "Raumtemperatur")]
        assert quantity.value == 20
        assert quantity.unit.symbol == "°C"

    def test_gepamod_ebf_exists(self, dataset) -> None:
        ebf = next(t for t in dataset.category_tables() if t.kind == "gepamod_ebf")
        quantity = ebf.rows[("I.1", "EBF")]
        assert quantity.value == 314363
        assert quantity.unit.symbol == "1000m2"

    def test_harmonized_raumtemperatur(self, dataset) -> None:
        table = next(
            t for t in dataset.category_tables()
            if t.kind == "harmonized" and t.variant == "standard"
        )
        assert table.rows[("I", "Raumtemperatur")].value == 22

    def test_comparison_tables_present_per_sheet(self, dataset) -> None:
        for kind in ("ww_demand", "person_gain", "person_area", "room_temperature"):
            tables = [t for t in dataset.category_tables() if t.kind == kind]
            assert len(tables) == 4, kind
        # ventilation flows split into the per-area (m3/m2h) and per-person
        # (m3/(Ph)) tables -> 8 tables in total
        ventilation = [t for t in dataset.category_tables() if t.kind == "ventilation_flow"]
        assert len(ventilation) == 8
        assert {t.unit for t in ventilation} == {"m3/m2h", "m3/(Ph)"}
