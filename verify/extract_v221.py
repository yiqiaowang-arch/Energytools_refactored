"""Verify the full V221 extraction point-by-point against the reference cell dumps.

The reference dumps (``.analysis/dumps/raumdaten`` in the main repository
checkout, produced by the exceljs-based ``.analysis/tools/dump.js``) contain
one TSV per sheet: ``CELLREF<TAB>VALUE`` for literal cells and
``CELLREF<TAB>F:<formula><TAB>R:<cached result>`` for formula cells.  Cells
that do not exist in the workbook XML (exceljs "ghost" cells reported as
``{"formula": ...}`` JSON lines) are ignored; rich-text cells are reduced to
their concatenated plain text.

Checks (all must pass, mismatches abort with exit code 1):
  * counts: 45 room uses, 193 parameters, 40 climate stations, 135 full-load
    hour rows, 5400 Qhc rows, 6 hourly profiles, 360 monthly profiles
  * JSON Schema validation of the package (``PACKAGE_SCHEMA``) and the
    loader's content validation (``Dataset.validate``)
  * room uses: codes + DE/FR/IT names vs Eingabedaten A9:C53 / Begriffe
  * parameters: labels/symbols/units per row 4..196 vs Datenblatt, and
    Standard/Zielwert/Bestand presence (M/N/O cells)
  * climate: winter design + HDD vs Winter_Auslegung; monthly values vs
    Monatswerte blocks
  * profiles: full 45-nutzid sample of selected parameters vs Eingabedaten
  * full-load hours vs Volll_Lüft; Qhc sample vs Qhc_Klimastat; hourly
    profiles vs Profile; area tables vs Fläche-E; SIA 380/1 vs the variant
    sheets

Usage:
    python verify/extract_v221.py [--package-dir data/datasets/V221] [--dumps DIR]

Environment override: ``RAUMDATEN_DUMPS_DIR``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from energytools.common.valuekind import ValueKind  # noqa: E402
from energytools.raumdaten.dataset import _safe_unit, load_dataset  # noqa: E402
from energytools.raumdaten.model import normalize_room_use_code  # noqa: E402

DEFAULT_DUMPS = (
    r"C:\Users\wangy\Documents\GitHub\Energytools_refactored\.analysis\dumps\raumdaten"
)

# dump file name per sheet (exceljs sheet ids of the Raumdaten workbook)
DUMP_FILES = {
    "Eingabedaten": "sheet_14809_Eingabedaten.tsv",
    "Begriffe": "sheet_14829_Begriffe.tsv",
    "Datenblatt": "sheet_14786_Datenblatt.tsv",
    "Monatswerte": "sheet_14838_Monatswerte.tsv",
    "Winter_Auslegung": "sheet_14839_Winter_Auslegung.tsv",
    "Profile": "sheet_14814_Profile.tsv",
    "Volll_Lüft": "sheet_14843_Volll_Lüft.tsv",
    "Qhc_Klimastat": "sheet_14853_Qhc_Klimastat.tsv",
    "Fläche-E": "sheet_14835_Fläche-E.tsv",
    "SIA 380-1": "sheet_14822_SIA 380-1.tsv",
    "SIA 380-1_EN": "sheet_14847_SIA 380-1_EN.tsv",
    "SIA 380-1_Qc": "sheet_14842_SIA 380-1_Qc.tsv",
    "SIA 380-1_Qc_EN": "sheet_14848_SIA 380-1_Qc_EN.tsv",
}

# fixed sample of matrix columns -> (parameter label, sub-kind suffix or None)
PROFILE_SAMPLES = [
    ("Raumlänge", "D", None),
    ("U-Wert Fenster", "L", None),
    ("U-Wert opake Bauteile", "O", None),
    ("Elektrische Leistung der Geräte", "AY", None),
    ("Raumtemperatur-Auslegungswert", "AB", "C"),  # Kühlfall column
    ("Raumtemperatur-Auslegungswert", "AC", "H"),  # Heizfall column
    ("Nutzungstage pro Jahr", "FZ", None),
    ("Ruhetage pro Woche", "FY", None),
    ("Jahresgleichzeitigkeit", "GE", None),
    ("Personenfläche", "AP", None),
]

SIA3801_SHEETS = {
    "de": "SIA 380-1",
    "en": "SIA 380-1_EN",
    "de+qc": "SIA 380-1_Qc",
    "en+qc": "SIA 380-1_Qc_EN",
}

_failures: list[str] = []


def fail(message: str) -> None:
    _failures.append(message)
    print(f"FAIL: {message}")


def _num_equal(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def parse_dump(path: Path) -> dict[str, str]:
    """Parse a dump TSV -> {ref: value}; ghost cells are skipped."""
    dump: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        ref, payload = parts[0], parts[1]
        if payload.startswith("{"):
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if "richText" in obj:
                dump[ref] = "".join(run.get("text", "") for run in obj["richText"])
            continue  # ghost cell (formula/result object for an empty cell)
        if payload.startswith("F:"):
            result = parts[2][2:] if len(parts) > 2 and parts[2].startswith("R:") else ""
            dump[ref] = "F:" + result
        else:
            dump[ref] = payload
    return dump


def check_value(dump: dict[str, str], ref: str, expected, where: str) -> None:
    raw = dump.get(ref)
    if raw is None:
        fail(f"{where}: dump has no cell {ref}")
        return
    if raw.startswith("F:"):
        raw = raw[2:]
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            if _num_equal(float(expected), float(raw)):
                return
        except ValueError:
            pass
        fail(f"{where}: {ref} numeric mismatch: package={expected!r} dump={raw!r}")
        return
    if isinstance(expected, str):
        if expected.strip() == raw.strip():
            return
        if normalize_room_use_code(expected.strip()) == normalize_room_use_code(raw.strip()):
            return
        fail(f"{where}: {ref} string mismatch: package={expected!r} dump={raw!r}")
        return
    fail(f"{where}: {ref} value type mismatch: package={expected!r} dump={raw!r}")


def check_unit(dump: dict[str, str], ref: str, expected_symbol: str, where: str) -> None:
    raw = dump.get(ref)
    if raw is None:
        if expected_symbol == "-":
            return  # no unit cell in the sheet -> the extractor's "-"
        fail(f"{where}: dump has no unit cell {ref}")
        return
    if raw.startswith("F:"):
        raw = raw[2:]
    from energytools.common.errors import UnitError
    from energytools.common.units import Unit

    try:
        normalized = Unit(raw).symbol
    except UnitError:
        if expected_symbol == "-":
            return
        fail(f"{where}: {ref} unit mismatch: package={expected_symbol!r} dump={raw!r} "
             f"(not a known unit)")
        return
    if normalized != expected_symbol:
        fail(f"{where}: {ref} unit mismatch: package={expected_symbol!r} dump={raw!r} "
             f"(normalized {normalized!r})")


def _present_in_dump(raw: str | None) -> bool:
    """Whether a dump cell carries a real value (not an error/empty)."""
    if raw is None:
        return False
    if raw.startswith("F:"):
        raw = raw[2:]
    if not raw.strip() or raw.startswith("{"):
        return False
    return True


def check_monthly(dump: dict[str, str], station_id: int, name: str, station_monthly,
                  where: str) -> None:
    """Compare a station's monthly profiles against its Monatswerte block."""
    # station i data lives in block i+1 (row 1 + 11*i); the air-temperature
    # row is the block row + 1, radiation_horizontal at +2, ... +9.
    block_row = 1 + 11 * station_id
    labels = ("t_aussen", "radiation_horizontal", "radiation_east", "radiation_south",
              "radiation_west", "radiation_north", "precipitation", "mixing_ratio",
              "absolute_humidity")
    for offset, key in enumerate(labels, start=1):
        if key not in station_monthly:
            fail(f"{where}: station {station_id} {name!r} missing monthly '{key}'")
            continue
        for month in range(12):
            ref = f"{chr(76 + month)}{block_row + offset}"  # L..W columns
            check_value(dump, ref, station_monthly[key].values[month],
                        f"{where} monthly[{key}]")


def verify(package_dir: Path, dumps_dir: Path) -> int:
    dataset = load_dataset("V221", path=str(package_dir))
    package_file = package_dir / "V221" / "package.json"
    package = json.loads(package_file.read_text(encoding="utf-8"))

    # -- schema + content validation -------------------------------------
    from energytools.raumdaten.schema import PACKAGE_SCHEMA

    import jsonschema

    jsonschema.Draft202012Validator(PACKAGE_SCHEMA).validate(package)
    report = dataset.validate()
    if not report.valid:
        fail("Dataset.validate: " + "; ".join(report.errors))
    print(f"package: {package_file} ({package_file.stat().st_size} bytes)")
    print("schema validation: OK; dataset.validate: OK")

    # -- counts -----------------------------------------------------------
    room_uses = dataset.room_uses()
    parameters = dataset.parameters()
    stations = dataset.climate().stations
    flh = dataset.full_load_hours()
    qhc = dataset.qhc()
    monthly_count = sum(len(station.monthly) for station in stations)
    expected_counts = {
        "room_uses": (len(room_uses), 45),
        "parameters": (len(parameters), 193),
        "climate stations": (len(stations), 40),
        "full-load-hours rows": (len(flh.rows), 135),
        "qhc rows": (len(qhc.rows), 5400),
        "hourly profiles": (len(dataset.hourly_profiles), 6),
        "monthly profiles": (monthly_count, 360),
        "profiles (room uses)": (len(dataset.profiles), 45),
    }
    for label, (actual, expected) in expected_counts.items():
        if actual != expected:
            fail(f"count {label}: {actual} != {expected}")
        else:
            print(f"count {label}: {actual} OK")

    dumps = {sheet: parse_dump(dumps_dir / filename) for sheet, filename in DUMP_FILES.items()}

    # -- room uses --------------------------------------------------------
    for nutzid, room_use in enumerate(room_uses, start=1):
        row = 8 + nutzid
        where = f"room_use[{nutzid}]"
        check_value(dumps["Eingabedaten"], f"A{row}", room_use.code, where)
        check_value(dumps["Eingabedaten"], f"C{row}", room_use.name.de, where)
        begriffe_row = 133 + nutzid
        check_value(dumps["Begriffe"], f"C{begriffe_row}", room_use.name.de, where)
        check_value(dumps["Begriffe"], f"D{begriffe_row}", room_use.name.fr, where)
        check_value(dumps["Begriffe"], f"E{begriffe_row}", room_use.name.it, where)
    print("room uses: 45 codes + trilingual names OK")

    # -- parameters -------------------------------------------------------
    rows_seen: list[int] = []
    for parameter in parameters:
        src = parameter.provenance.sources[0] if parameter.provenance else None
        if src is None or src.sheet != "Datenblatt":
            fail(f"parameter {parameter.id}: missing Datenblatt provenance")
            continue
        row = int(re.match(r"A(\d+):", src.range).group(1))
        rows_seen.append(row)
        where = f"parameter[{row}] {parameter.id}"
        label_cell = dumps["Datenblatt"].get(f"C{row}")
        if parameter.label.de:
            if label_cell is None:
                # synthesized label of a sub-case row ("<parent> (<designator>)")
                parent = _previous_label(dumps["Datenblatt"], row)
                if not parameter.label.de.startswith(parent + " ("):
                    fail(f"{where}: synthesized label {parameter.label.de!r} "
                         f"does not extend parent {parent!r}")
            else:
                check_value(dumps["Datenblatt"], f"C{row}", parameter.label.de, where)
        elif label_cell is not None:
            fail(f"{where}: package label empty but dump C{row}={label_cell!r}")
        if parameter.symbol:
            check_value(dumps["Datenblatt"], f"I{row}", parameter.symbol, where)
        check_unit(dumps["Datenblatt"], f"J{row}", parameter.unit.symbol, where)
        # Standard/Zielwert/Bestand presence must match the M/N/O cells; the
        # extractor defaults to {standard} when the row has no value cells.
        present_kinds = {
            kind
            for kind, column in ((ValueKind.STANDARD, "M"), (ValueKind.ZIELWERT, "N"),
                                 (ValueKind.BESTAND, "O"))
            if _present_in_dump(dumps["Datenblatt"].get(f"{column}{row}"))
        }
        expected_kinds = present_kinds or {ValueKind.STANDARD}
        if set(parameter.value_kinds) != expected_kinds:
            fail(f"{where}: value kinds mismatch: package={sorted(k.value for k in parameter.value_kinds)} "
                 f"dump={sorted(k.value for k in expected_kinds)}")
    if sorted(rows_seen) != list(range(4, 197)):
        fail(f"parameter rows: {sorted(set(rows_seen))} != 4..196")
    else:
        print("parameters: 193 rows 4..196 (labels/symbols/units/value kinds) OK")

    # -- climate ----------------------------------------------------------
    for station in stations:
        row = 4 + station.id
        where = f"station[{station.id}]"
        check_value(dumps["Winter_Auslegung"], f"A{row}", station.name.de, where)
        if station.hdd is not None:
            check_value(dumps["Winter_Auslegung"], f"E{row}", station.hdd.value, where)
        for key, column in (("t_heating", "F"), ("t_ventilation", "G"),
                            ("t_a", "H"), ("radiation", "J")):
            quantity = station.winter_design.get(key)
            if quantity is not None:
                check_value(dumps["Winter_Auslegung"], f"{column}{row}", quantity.value, where)
        check_monthly(dumps["Monatswerte"], station.id, station.name.de, station.monthly, where)
    print("climate: 40 stations (winter design, HDD, monthly) OK")

    # -- profiles (sample) ------------------------------------------------
    for label, column, sub_kind in PROFILE_SAMPLES:
        parameter = _find_parameter(dataset, label, sub_kind)
        if parameter is None:
            fail(f"profile sample: parameter {label!r} (sub {sub_kind}) not found")
            continue
        for nutzid in range(1, 46):
            value = dataset.profile(nutzid).value(parameter.id, ValueKind.STANDARD).value
            if value is not None:
                check_value(dumps["Eingabedaten"], f"{column}{8 + nutzid}", value,
                            f"profile {label}[{nutzid}]")
    print("profiles: sample matrix columns x 45 nutzids OK")

    # -- full-load hours --------------------------------------------------
    for nutzid in range(1, 46):
        row = 6 + nutzid
        where = f"flh[{nutzid}]"
        for regulation, column in (("1-stufig", "D"), ("2-stufig", "F"), ("stufenlos", "J")):
            check_value(dumps["Volll_Lüft"], f"{column}{row}",
                        flh.hours(nutzid, regulation, "prSIA 2024-C1:2024"), where)
    print("full-load hours: 135 rows OK")

    # -- qhc (sample: all 40 stations x 3 nutzids x 3 kinds) --------------
    qhc_checked = 0
    for station in stations:
        station_start = 4 + 12 * (station.id - 1)
        for nutzid in (1, 22, 45):
            for kind, offset in ((ValueKind.STANDARD, 0), (ValueKind.ZIELWERT, 4),
                                 (ValueKind.BESTAND, 8)):
                column = station_start + offset + 1
                ref = f"{_col_letters(column)}{6 + nutzid}"
                check_value(dumps["Qhc_Klimastat"], ref,
                            qhc.qhc(nutzid, station.id, kind).value,
                            f"qhc[{nutzid},{station.id},{kind.value}]")
                qhc_checked += 1
    print(f"qhc: {qhc_checked} sample cells OK")

    # -- hourly profiles --------------------------------------------------
    profile_columns = {"personen_werktag": "B", "geraete_werktag": "D",
                       "geraete_freier_tag": "E", "lueftung_einstufig": "F",
                       "lueftung_zweistufig": "G", "lueftung_stufenlos": "I"}
    for profile in dataset.hourly_profiles:
        column = profile_columns[profile.id]
        for hour in range(24):
            check_value(dumps["Profile"], f"{column}{63 + hour}", profile.values[hour],
                        f"hourly {profile.id}[{hour}]")
    print("hourly profiles: 6 x 24 values OK")

    # -- area tables ------------------------------------------------------
    area = dataset.area_tables()[0]
    area_cells = 0
    for category, codes in area.rows.items():
        column = _category_column(category)
        if column is None:
            fail(f"area table: category {category!r} not mapped to a column")
            continue
        for code, quantity in codes.items():
            room_use = dataset.room_use(code)
            check_value(dumps["Fläche-E"], f"{column}{2 + room_use.nutzid}",
                        quantity.value, f"area[{category},{code}]")
            area_cells += 1
    print(f"area tables: {area_cells} cells OK")

    # -- SIA 380/1 --------------------------------------------------------
    for result in dataset.sia3801_results():
        sheet = SIA3801_SHEETS[result.variant]
        row = {ValueKind.STANDARD: 134, ValueKind.ZIELWERT: 166, ValueKind.BESTAND: 196}[result.kind]
        check_value(dumps[sheet], f"P{row}", result.values["Qh"].value,
                    f"sia3801[{result.variant},{result.kind.value}]")
    station_name = dumps["SIA 380-1"].get("B68", "")
    print(f"sia3801: {len(dataset.sia3801_results())} results OK (station B68={station_name!r})")

    if _failures:
        print(f"\n{len(_failures)} MISMATCH(ES)")
        return 1
    print("\nAll point-by-point checks passed.")
    return 0


def _previous_label(dump: dict[str, str], row: int) -> str:
    """Nearest preceding Datenblatt C label (the extractor's parent label)."""
    for r in range(row - 1, 3, -1):
        raw = dump.get(f"C{r}")
        if raw is None:
            continue
        if raw.startswith("F:"):
            raw = raw[2:]
        raw = raw.strip()
        if raw and raw != "berechnet!":  # computed-marker row: not a parent label
            return raw
    return ""


def _find_parameter(dataset, label: str, sub_kind: str | None):
    candidates = [
        p for p in dataset.parameters()
        if p.label.de.strip() == label
        or (p.label.de.strip().startswith(label + " (") and p.label.de.strip().endswith(")"))
    ]
    if not candidates:
        return None
    if sub_kind is None:
        for p in candidates:
            if not p.id.endswith((".C", ".H")) and not re.search(r",[CH]$", p.symbol):
                return p
        return candidates[0]
    for p in candidates:
        if p.id.endswith("." + sub_kind):
            return p
    return candidates[0]


def _col_letters(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _category_column(category: str) -> str | None:
    """Fläche-E first-block column letter for a category code (D..Y)."""
    return {
        "I": "D", "I.1": "E", "I.2": "F", "II": "G", "III": "H", "IV": "I",
        "IV.1": "J", "IV.2": "K", "V": "L", "V.1": "M", "V.2": "N", "V.3": "O",
        "VI": "P", "VII": "Q", "VIII": "R", "VIII.1": "S", "VIII.2": "T",
        "IX": "U", "X": "V", "XI": "W", "XII": "X", "XIII": "Y",
    }.get(category)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", default="data/datasets")
    parser.add_argument("--dumps", default=os.environ.get("RAUMDATEN_DUMPS_DIR", DEFAULT_DUMPS))
    args = parser.parse_args()
    return verify(Path(args.package_dir), Path(args.dumps))


if __name__ == "__main__":
    sys.exit(main())
