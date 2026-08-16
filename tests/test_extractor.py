"""Tests for energytools.raumdaten.dataset.DatasetExtractor -- the stage-0 pipeline (part 03, section 2.3).

The extractor is exercised against a small synthetic workbook that mirrors the
documented V221 layout (Eingabedaten master matrix, Begriffe Ziffern + names,
Datenblatt parameter rows, Profile hour rows, Winter_Auslegung / Monatswerte
climate blocks, Volll_Lüft, Qhc_Klimastat, Fläche-E/GEPAMOD, SIA 380-1).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from energytools.common.errors import DatasetValidationError
from energytools.raumdaten.dataset import DatasetExtractor, load_dataset

openpyxl = pytest.importorskip("openpyxl")


def _write_synthetic_workbook(path: Path) -> None:
    """Write a minimal workbook following the documented V221 sheet layout."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # --- Eingabedaten: master matrix (row 6 names, row 7 kinds, row 8 units, rows 9+ values) ---
    ws = wb.create_sheet("Eingabedaten")
    ws["A9"], ws["C9"] = "1.01", "Wohnen MFH"
    ws["A10"], ws["C10"] = "1.02", "Wohnen EFH"
    ws["D6"], ws["D7"], ws["D8"] = "Raumlänge", None, "m"
    ws["D9"], ws["D10"] = 4.0, 4.0
    ws["L6"], ws["L7"], ws["L8"] = "Wärmedurchgangskoeffizient", "Standard", "W/(m²K)"
    ws["M7"], ws["N7"] = "Zielwert", "Bestand"
    ws["M8"], ws["N8"] = "W/(m²K)", "W/(m²K)"
    ws["L9"], ws["M9"], ws["N9"] = 1.0, 0.8, 1.5
    ws["L10"], ws["M10"], ws["N10"] = 1.0, 0.8, 1.5

    # --- Begriffe: parameter Ziffern (rows 25+) and room-use names (rows 134+) ---
    ws = wb.create_sheet("Begriffe")
    ws["B25"], ws["C25"] = "1.1.1.6", "Wärmedurchgangskoeffizient"
    ws["B134"], ws["C134"], ws["D134"], ws["E134"] = (
        "1.1",
        "Wohnen MFH",
        "Habitat collectif",
        "Abitazione plurifamiliare",
    )
    ws["B135"], ws["C135"], ws["D135"], ws["E135"] = (
        "1.2",
        "Wohnen EFH",
        "Habitat individuel",
        "Abitazione monofamiliare",
    )

    # --- Datenblatt: parameter rows 4-5, selected nutzid in C1 ---
    ws = wb.create_sheet("Datenblatt")
    ws["C1"] = 1
    ws["A4"] = "Raum"
    ws["C4"], ws["I4"], ws["J4"] = "Raumlänge", "lR", "m"
    ws["M4"], ws["P4"], ws["Q4"], ws["R4"] = 4.0, 0, 1, 0
    ws["C5"], ws["I5"], ws["J5"] = "Wärmedurchgangskoeffizient", "U", "W/(m2K)"
    ws["M5"], ws["N5"], ws["O5"] = 1.0, 0.8, 1.5

    # --- Profile: hour rows 63-86 (person column B) ---
    ws = wb.create_sheet("Profile")
    ws["B1"] = "Wohnen MFH"
    for hour in range(1, 25):
        ws.cell(row=62 + hour, column=2, value=1.0)

    # --- Winter_Auslegung: stations in rows 5-6 (A name, E HDD, F/G/H temps, J radiation) ---
    ws = wb.create_sheet("Winter_Auslegung")
    ws["A5"], ws["E5"], ws["F5"], ws["G5"], ws["H5"], ws["J5"] = (
        "Adelboden",
        4670,
        -10.2,
        -15.9,
        -10.2,
        73,
    )
    ws["A6"], ws["E6"], ws["F6"], ws["G6"], ws["H6"], ws["J6"] = (
        "Aigle",
        3152,
        -5.5,
        -12.9,
        -5.5,
        73,
    )

    # --- Monatswerte: 11-row blocks per station (rows 1 and 12) ---
    ws = wb.create_sheet("Monatswerte")
    for block, name in ((1, "Adelboden"), (12, "Aigle")):
        ws.cell(row=block, column=1, value=name)
        for month in range(12):
            ws.cell(row=block + 1, column=12 + month, value=float(month))
        ws.cell(row=block + 2, column=12, value=150.0)  # radiation horizontal, Jan

    # --- Volll_Lüft: rows 7-8 (A code, D 1-stufig, F 2-stufig, J stufenlos) ---
    ws = wb.create_sheet("Volll_Lüft")
    ws["A7"], ws["D7"], ws["F7"], ws["J7"] = "1.01", 8760, 7540, 5750
    ws["A8"], ws["D8"], ws["F8"], ws["J8"] = "1.02", 8760, 7540, 5750

    # --- Qhc_Klimastat: station blocks at D3/P3, E/I/M annual cooling kWh/m2 ---
    ws = wb.create_sheet("Qhc_Klimastat")
    ws["D3"], ws["P3"] = "Adelboden", "Aigle"
    ws["A7"], ws["E7"], ws["I7"], ws["M7"] = "1.01", 0.0, 0.0, 0.0
    ws["A8"], ws["E8"], ws["I8"], ws["M8"] = "1.02", 27.16, 15.55, 123.2
    # D/F/G columns of the block carry the three further metrics per kind
    ws["D7"], ws["D8"] = 15.5, 20.0  # cooling power W/m2 (Adelboden Standard)
    ws["F7"], ws["F8"] = 30.0, 42.5  # Norm-Heizlast W/m2
    ws["G7"], ws["G8"] = 90.0, 140.0  # annual heating kWh/m2

    # --- Aug_Auslegung: empty design-day matrix (no station blocks) ---
    wb.create_sheet("Aug_Auslegung")

    # --- Fläche-E / GEPAMOD ---
    ws = wb.create_sheet("Fläche-E")
    ws["D1"], ws["E1"] = "I", "I.1"
    ws["D2"], ws["E2"] = "Wohnen MFH", "Wohnen MFH"
    ws["A3"], ws["B3"], ws["C3"], ws["D3"], ws["E3"] = "1.01", "Wohnen MFH", "%", 85, 85
    ws["A4"], ws["B4"], ws["C4"] = "1.02", "Wohnen EFH", "%"
    ws = wb.create_sheet("GEPAMOD")
    ws["D1"], ws["E1"] = "I.1", "I.2"
    ws["D2"], ws["E2"] = "Wohnen MFH", "Hotel"

    # --- SIA 380-1: station B68 + Qh per kind (P134/P166/P196), 4 variant sheets ---
    ws = wb.create_sheet("Eigene Nutzung")
    ws["G1"] = 1  # selected station index (Adelboden)
    for sheet_name in ("SIA 380-1", "SIA 380-1_Qc", "SIA 380-1_EN", "SIA 380-1_Qc_EN"):
        ws = wb.create_sheet(sheet_name)
        ws["B68"] = "Zürich-MeteoSchweiz"  # unknown station -> falls back to the first station
        ws["P134"], ws["P166"], ws["P196"] = 14.85, 10.3, 103.48

    wb.save(path)


class TestDatasetExtractor:
    def test_missing_workbook_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            DatasetExtractor(
                str(tmp_path / "nope.xlsm"),
                str(tmp_path / "out"),
                extraction_tool_version="test",
            )

    def test_extract_writes_loadable_package(self, tmp_path: Path) -> None:
        workbook = tmp_path / "Raumdaten_copy.xlsm"
        _write_synthetic_workbook(workbook)
        out_dir = tmp_path / "out"

        extractor = DatasetExtractor(
            str(workbook), str(out_dir), release_id="V221", extraction_tool_version="0.1.0-test"
        )
        release = extractor.extract()
        assert release.id == "V221"
        assert len(release.checksum_sha256) == 64
        assert (out_dir / "V221" / "package.json").is_file()
        assert (out_dir / "V221" / "schema.json").is_file()

        dataset = load_dataset("V221", path=str(out_dir))
        report = dataset.validate()
        assert report.valid, report.errors
        assert len(dataset.room_uses()) == 2
        assert dataset.room_use("1.01").name.get("fr") == "Habitat collectif"
        assert dataset.room_use("1.02").name.get("it") == "Abitazione monofamiliare"
        # profiles from the Eingabedaten matrix
        assert dataset.profile(1).value("1.1.1.6", "standard").value == 1.0
        assert dataset.profile(1).value("1.1.1.6", "zielwert").value == 0.8
        # climate + tables
        assert len(dataset.climate().stations) == 2
        assert dataset.climate().station(1).hdd.value == 4670.0
        assert dataset.full_load_hours().hours(1, "2-stufig", "prSIA 2024-C1:2024") == 7540.0
        assert dataset.qhc().qhc(2, 1).value == 27.16  # E8 = annual cooling of 1.02 at Adelboden
        assert dataset.qhc().qhc(1, 1).value == 0.0
        assert len(dataset.hourly_profiles) == 8
        assert len(dataset.sia3801_results()) == 12

    def test_missing_required_sheet_raises(self, tmp_path: Path) -> None:
        workbook = tmp_path / "broken.xlsm"
        wb = openpyxl.Workbook()
        wb.save(workbook)  # no sheets at all
        extractor = DatasetExtractor(
            str(workbook), str(tmp_path / "out"), extraction_tool_version="test"
        )
        with pytest.raises(DatasetValidationError, match="sheet layout"):
            extractor.extract()
