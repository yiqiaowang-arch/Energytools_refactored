"""Backfill the V221 dataset package with the Gebaeude-Tool KPI/climate data.

One-shot data migration (run from the repo root):

    pixi run -e dev python verify/backfill_v221_kpi.py

The Raumdaten ``data/datasets/V221/package.json`` carries only a subset of the
KPI matrix (the ``Res`` matrix / ``KZ_Raum_2024``): e.g. the Geräte power
``1.1.3.3`` and the hygienic fresh air ``1.1.5.2``.  The native engine backend
(:mod:`energytools.engine.native.backend`) consumes the full ``Res`` matrix,
the ``Std`` intensities and the ``Klimadaten`` station data through the
dataset, so this script backfills them from the read-only workbook dumps in
``.analysis/dumps/gebaeude/``:

- **KPI matrix** (``sheet_41_KZ_Raum_2024.tsv``): the 7 energy + 6 power
  columns of ``Res!B7:AV51`` for all three value kinds → the parameter ids of
  ``_RES_COL_ENERGY_PARAM`` / ``_RES_COL_POWER_PARAM`` (ch02 §2.2/§2.4).
  The Klimakälte/Heizwärme columns (``1.1.6.7``/``1.1.7.9``/``1.1.6.5``/
  ``FV,i``) reference ``Qhc_Klimastat`` and are **station-dependent**: the
  dump carries the cached values of the workbook's selected station
  (Zürich-MeteoSchweiz, ``Gebäude!D2 = 40``), so the package stores the
  Zürich default.  The engine backend records this as a known gap (a warning
  when the building's station is not 40).
- **Std intensities** (``sheet_42_Std.tsv``): the process fresh air
  ``1.1.5.3`` (Standard only; empty workbook cells → 0.0).  The hygienic
  fresh air ``1.1.5.2`` and the WW demand (``1.1.8.4``/``1.1.2.9``) are
  already derivable from the package and are verified, not written.
- **Klimadaten** (``sheet_62_Klimadaten.tsv``): per station — the 61
  temperature-bin hours (``temperature_bins``), the per-bin absolute-humidity
  ratio in g/kg (``bin_humidity_ratio``, computed with
  :func:`absolute_humidity` like the workbook's ``AbsFeuchte`` column) and the
  station air pressure in mbar (``winter_design["pressure"]``, the height
  formula ``E4:E43``).  These are the inputs of the AHU temperature-bin
  engine (:mod:`energytools.engine.native.ahu`).

The ``release.checksum_sha256`` is recomputed with the loader's own
``_content_checksum`` so the package still passes the loader's checksum
verification.  ``.analysis/`` is read-only; the script only reads it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from energytools.engine.native.aggregation import (
    _RES_COL_ENERGY_PARAM,
    _RES_COL_POWER_PARAM,
    _energy_block_kind,
    _power_block_kind,
)
from energytools.engine.native.psychrometrics import absolute_humidity
from energytools.raumdaten.dataset import _content_checksum

PACKAGE = REPO_ROOT / "data" / "datasets" / "V221" / "package.json"
DUMPS = REPO_ROOT / ".analysis" / "dumps" / "gebaeude"
TSV_KZ = DUMPS / "sheet_41_KZ_Raum_2024.tsv"
TSV_STD = DUMPS / "sheet_42_Std.tsv"
TSV_KLIMADATEN = DUMPS / "sheet_62_Klimadaten.tsv"

N_BINS = 61
T_MIN_BIN = -25.0

#: Klimadaten sheet: station id -> (hours column, humidity column).  The
#: column assignment is a workbook constant (row 1/2 of the sheet) and is the
#: same mapping the golden-JSON loader uses (``tests/test_ahu.py``
#: ``STATION_COLS``).  Keys are the raumdaten station names (proper UTF-8).
STATION_COLS: dict[str, tuple[str, str]] = {
    "Adelboden": ("T", "S"),
    "Aigle": ("V", "U"),
    "Altdorf": ("X", "W"),
    "Basel-Binningen": ("Z", "Y"),
    "Bern-Liebefeld": ("AB", "AA"),
    "Buchs-Aarau": ("AD", "AC"),
    "La Chaux-de-Fonds": ("AF", "AE"),
    "Chur": ("AH", "AG"),
    "Davos": ("AJ", "AI"),
    "Disentis": ("AL", "AK"),
    "Engelberg": ("AN", "AM"),
    "La Frétaz": ("AP", "AO"),
    "Glarus": ("AR", "AQ"),
    "Grand-St-Bernard": ("AT", "AS"),
    "Güttingen": ("AV", "AU"),
    "Genève-Cointrin": ("AX", "AW"),
    "Interlaken": ("AZ", "AY"),
    "Zürich-Kloten": ("BB", "BA"),
    "Lugano": ("BD", "BC"),
    "Luzern": ("BF", "BE"),
    "Magadino": ("BH", "BG"),
    "Montana": ("BJ", "BI"),
    "Neuchâtel": ("BL", "BK"),
    "Locarno-Monti": ("BN", "BM"),
    "Payerne": ("BP", "BO"),
    "Piotta": ("BR", "BQ"),
    "Pully": ("BT", "BS"),
    "Robbia": ("BV", "BU"),
    "Rünenberg": ("BX", "BW"),
    "Samedan": ("BZ", "BY"),
    "San Bernardino": ("CB", "CA"),
    "Scuol": ("CD", "CC"),
    "Schaffhausen": ("CF", "CE"),
    "Sion": ("CH", "CG"),
    "Zürich-MeteoSchweiz": ("CJ", "CI"),
    "St. Gallen": ("CL", "CK"),
    "Ulrichen": ("CN", "CM"),
    "Vaduz": ("CP", "CO"),
    "Wynau": ("CR", "CQ"),
    "Zermatt": ("CT", "CS"),
}

#: Res columns that reference ``Qhc_Klimastat`` (station-dependent).
CLIMATE_RES_COLS = frozenset({6, 7, 14, 15, 22, 23, 32, 33, 39, 40, 46, 47})


def _dump_cells(path: Path) -> dict[tuple[str, int], float]:
    """Cell address -> numeric cached value of a workbook dump TSV."""
    cells: dict[tuple[str, int], float] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        match = re.match(r"^([A-Z]+)(\d+)$", parts[0])
        if not match:
            continue
        value: float | None = None
        for part in parts[1:]:
            if part.startswith("R:"):
                try:
                    value = float(part[2:])
                except ValueError:
                    pass
                break
        if value is None and len(parts) == 2:
            try:
                value = float(parts[1])
            except ValueError:
                pass
        if value is not None:
            cells[(match.group(1), int(match.group(2)))] = value
    return cells


def _kz_kpi_values(cells: dict[tuple[str, int], float]) -> dict[int, dict[str, dict[str, float]]]:
    """KZ matrix -> nutzid -> parameter id -> value kind -> value.

    KZ matrix rows 7..51 correspond to nutzid 1..45 (row = nutzid + 6); the
    Res column number of a cell equals its sheet column minus one (the
    workbook's own ``Res`` named range ``KZ_Raum_2024!B7:AV51``).
    """
    result: dict[int, dict[str, dict[str, float]]] = {}
    for (col, row), value in cells.items():
        if not 7 <= row <= 51:
            continue
        res_col = _excel_col_index(col) - 1
        if 2 <= res_col <= 8 or 10 <= res_col <= 16 or 18 <= res_col <= 24:
            value_kind, offset = _energy_block_kind(res_col)
            param = _RES_COL_ENERGY_PARAM[offset]
        elif 28 <= res_col <= 33 or 35 <= res_col <= 40 or 42 <= res_col <= 47:
            value_kind, offset = _power_block_kind(res_col)
            param = _RES_COL_POWER_PARAM[offset]
        else:
            continue
        nutzid = row - 6
        result.setdefault(nutzid, {}).setdefault(param, {})[value_kind] = value
    return result


def _std_process_air(cells: dict[tuple[str, int], float]) -> dict[int, float]:
    """Std table -> nutzid -> process fresh air ``Std!E`` (0.0 when empty).

    Std rows 6..50 correspond to nutzid 1..45 (row = nutzid + 5); an empty
    ``E`` cell reads as 0 (the workbook's VLOOKUP over an empty cell).
    """
    result: dict[int, float] = {}
    for nutzid in range(1, 46):
        result[nutzid] = cells.get(("E", nutzid + 5), 0.0)
    return result


def _excel_col_index(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def main() -> None:
    if not (TSV_KZ.exists() and TSV_STD.exists() and TSV_KLIMADATEN.exists()):
        raise SystemExit(
            f"workbook dumps not present under {DUMPS} — cannot backfill"
        )

    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    catalog = {parameter["id"]: parameter for parameter in package["parameters"]}
    profiles = {profile["nutzid"]: profile for profile in package["profiles"]}

    # ------------------------------------------------------------------ KPI
    kz_cells = _dump_cells(TSV_KZ)
    kpi = _kz_kpi_values(kz_cells)
    added: dict[str, int] = {}
    overwritten: list[tuple[int, str, str, float, float]] = []
    for nutzid in range(1, 46):
        values = profiles[nutzid]["values"]
        for param_id, by_kind in kpi.get(nutzid, {}).items():
            unit = catalog[param_id]["unit"]
            for kind, value in by_kind.items():
                entry = values.setdefault(param_id, {})
                existing = entry.get(kind)
                if existing is not None and abs(float(existing["value"]) - value) > 1e-9:
                    # Known workbook quirk: the Res matrix Bestand
                    # Prozessanlagen-power column (AR) references the
                    # Prozessanlagen *energy* column (Resultate Bestand!T) —
                    # the package's extraction carries the true power column
                    # (P).  The golden caches follow the workbook, so the
                    # matrix values win (documented in the module docstring).
                    overwritten.append((nutzid, param_id, kind, float(existing["value"]), value))
                    entry[kind] = {"value": value, "unit": unit, "provenance": None}
                    continue
                if existing is None:
                    entry[kind] = {"value": value, "unit": unit, "provenance": None}
                    added[param_id] = added.get(param_id, 0) + 1

    # ------------------------------------------------------------------ Std
    std_cells = _dump_cells(TSV_STD)
    process = _std_process_air(std_cells)
    unit = catalog["1.1.5.3"]["unit"]
    added_std = 0
    for nutzid, value in process.items():
        values = profiles[nutzid]["values"]
        entry = values.setdefault("1.1.5.3", {})
        existing = entry.get("standard")
        if existing is not None and abs(float(existing["value"]) - value) > 1e-9:
            raise SystemExit(
                f"process-air conflict: nutzid {nutzid}: "
                f"package {existing['value']!r} vs Std {value!r}"
            )
        if existing is None:
            entry["standard"] = {"value": value, "unit": unit, "provenance": None}
            added_std += 1

    # ------------------------------------------------------------ Klimadaten
    kd_cells = _dump_cells(TSV_KLIMADATEN)
    stations = {station["id"]: station for station in package["climate"]["stations"]}
    climate_added = 0
    for station_id, station in sorted(stations.items()):
        # station ids 1..40 == Klimadaten sheet rows 4..43
        sheet_row = station_id + 3
        name = station["name"]["de"]
        try:
            hours_col, humidity_col = STATION_COLS[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise SystemExit(
                f"station {station_id} {name!r}: no Klimadaten column pair"
            ) from exc
        hours = [kd_cells.get((hours_col, r), 0.0) for r in range(5, 5 + N_BINS)]
        rh = [kd_cells.get((humidity_col, r), 0.0) for r in range(5, 5 + N_BINS)]
        pressure = kd_cells.get(("E", sheet_row))
        if pressure is None:
            raise SystemExit(f"station {station_id} {name!r}: no pressure (E{sheet_row})")
        x_aul = tuple(
            absolute_humidity(T_MIN_BIN + k, rh[k], pressure) for k in range(N_BINS)
        )
        station["temperature_bins"] = [
            {"lower": round(T_MIN_BIN + k - 0.5, 6), "upper": round(T_MIN_BIN + k + 0.5, 6), "hours": hours[k]}
            for k in range(N_BINS)
        ]
        station["bin_humidity_ratio"] = list(x_aul)
        station["winter_design"]["pressure"] = {"value": pressure, "unit": "mbar"}
        climate_added += 1

    # ------------------------------------------------------------- checksum
    package["release"]["checksum_sha256"] = _content_checksum(package)
    PACKAGE.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("backfilled KPI values:", added)
    print(
        "  of which climate-dependent (Zürich default): "
        f"1.1.6.7={added.get('1.1.6.7', 0)} 1.1.7.9={added.get('1.1.7.9', 0)} "
        f"1.1.6.5={added.get('1.1.6.5', 0)} FV,i={added.get('FV,i', 0)}"
    )
    print("overwritten (KZ-matrix Bestand-Prozess-power quirk):", len(overwritten))
    for item in overwritten:
        print("  ", item)
    print("backfilled process-air values (1.1.5.3 standard):", added_std)
    print("backfilled climate stations (bins/pressure/humidity):", climate_added)
    print("new checksum:", package["release"]["checksum_sha256"])
    print(f"wrote {PACKAGE}")


if __name__ == "__main__":
    main()
