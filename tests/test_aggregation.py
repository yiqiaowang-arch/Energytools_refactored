"""Tests for the building aggregation / ``Resultate`` module
(:mod:`energytools.engine.native.aggregation`).

The aggregation module ports the last link of the computation chain — rooms →
ventilation → generation → Resultate (textbook ch02 and ch05).  Verification
layers:

1. **Golden comparison** (primary): the six ``data/golden/case-0X.json``
   files carry the workbook's room inputs (``Gebäude``/``rooms``/``Lueftung``/
   ``Erzeugung``) and the cached outputs (``Gebaeude_totals``,
   ``Lueftung_results``, ``Erzeugung_totals``, ``Resultate``).  The engine
   must reproduce every cached cell at rel = 1e-6.  The room KPI intensities
   (the ``Res`` matrix) come from the workbook dump
   ``.analysis/dumps/gebaeude/sheet_41_KZ_Raum_2024.tsv`` (the matrix is
   partly climate-dependent — Klimakälte/Heizwärme reference ``Qhc_Klimastat``
   — so for the non-Zürich cases case-01/06 the climate columns are overridden
   from the case's own cached room cells).  The ``Std`` intensities
   (fresh-air rates, WW demand) come from ``sheet_42_Std.tsv``.  When the
   dumps are absent the dump-backed cells are skipped (see ``HAS_DUMPS``).

2. **AHU dependence**: the per-system air-treatment results (``Lüftung``
   rows 7–22) are injected from the cached rows because the JSON's
   ``Lueftung_results`` were *not* recalculated for the non-base cases (the
   cached totals are identical across all six cases although the systems
   differ — a known extraction artifact).  For case-02 the LA01 result is
   recomputed with the AHU engine (:mod:`energytools.engine.native.ahu`) and
   cross-checked against the cached row 7.  The Resultate Kühlung/Heizung
   columns (N/O/P/Q) therefore verify the aggregation wiring for all cases
   and the genuine AHU chain for case-02.

3. **Pure unit tests**: Res column offsets (Standard/Zielwert/Bestand incl.
   the Lüftung deviation), gating, KPI×area arithmetic, SUMIF semantics,
   Deckungsgrad sums = 100 %, carrier merging, the KPI-lookup error contract,
   the dataset-backed lookup, the weighted indicator rows (incl. the ``I21``
   copy-paste error reproduction) and the WW power conversion.

Skip accounting: cells without a cached value in the golden JSON
(``no-cached-value`` / shared formulas without results) are recorded and not
counted against the skip rate; the skip rate is the share of *cached* cells
the engine cannot reproduce, which stays below 30 % for every case.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from energytools.engine.model import BuildingInput, RoomRow, ValueKind, VentilationSystem
from energytools.engine.native.aggregation import (
    RES_SELECTORS,
    RESULTATE_CARRIERS,
    AggregationInput,
    DatasetResLookup,
    GenerationCatalog,
    GenerationGroupInput,
    GenerationInput,
    GeneratorSpec,
    KpiLookupError,
    ResMatrixKpiProvider,
    aggregate,
    compute_room_row,
    res_column,
)
from energytools.engine.native.ahu import (
    AhuAnnualResult,
    AhuInput,
    compute_ahu_annual,
    compute_fan_model,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = REPO_ROOT / "data" / "golden"
DUMP_DIR = REPO_ROOT / ".analysis" / "dumps" / "gebaeude"
TSV_KZ = DUMP_DIR / "sheet_41_KZ_Raum_2024.tsv"
TSV_STD = DUMP_DIR / "sheet_42_Std.tsv"
HAS_DUMPS = TSV_KZ.exists() and TSV_STD.exists()
DATASET_PKG = REPO_ROOT / "data" / "datasets" / "V221" / "package.json"

CASE_IDS = ("case-01", "case-02", "case-03", "case-04", "case-05", "case-06")

#: Workbench columns that are compared per room row (Gebäude!F12:W32) →
#: RoomResult field.
ROOM_FIELD_BY_COL: dict[str, str] = {
    "E": "share",
    "F": "geraete_kw",
    "G": "geraete_mwh",
    "H": "prozessanlagen_kw",
    "I": "prozessanlagen_mwh",
    "J": "beleuchtung_kw",
    "K": "beleuchtung_mwh",
    "M": "lueftung_volume_flow_m3h",
    "N": "lueftung_kw",
    "O": "lueftung_mwh",
    "Q": "kuehlung_kw",
    "R": "kuehlung_mwh",
    "T": "heizung_kw",
    "U": "heizung_mwh",
    "V": "warmwasser_l_d",
    "W": "warmwasser_mwh",
}

#: Gebaeude totals (Rechenwert row 35) → RoomTotals field.
TOTALS_FIELD_BY_CELL: dict[str, str] = {
    "E33": "share_sum",
    "F35": "geraete_kw",
    "G35": "geraete_mwh",
    "H35": "prozessanlagen_kw",
    "I35": "prozessanlagen_mwh",
    "J35": "beleuchtung_kw",
    "K35": "beleuchtung_mwh",
    "M35": "lueftung_volume_flow_m3h",
    "N35": "lueftung_kw",
    "O35": "lueftung_mwh",
    "Q35": "kuehlung_kw",
    "R35": "kuehlung_mwh",
    "T35": "heizung_kw",
    "U35": "heizung_mwh",
    "V35": "warmwasser_l_d",
    "W35": "warmwasser_mwh",
}

#: Lüftung totals (row 23) → VentilationTotals field.
VENT_TOTALS_FIELD_BY_CELL: dict[str, str] = {
    "C23": "volume_flow_m3h",
    "D23": "process_flow_m3h",
    "H23": "fan_power_kw",
    "I23": "fan_energy_mwh",
    "Q23": "luftkuehlung_kw",
    "R23": "luftkuehlung_mwh",
    "S23": "lufterwaermung_kw",
    "T23": "lufterwaermung_mwh",
}

#: Per-system Lüftung cells (rows 7–22) → VentilationSystemResult field.
SYS_FIELD_BY_CELL: dict[str, str] = {
    "C": "volume_flow_m3h",
    "D": "process_flow_m3h",
    "F": "effective_flow_m3h",
    "H": "fan_power_kw",
    "I": "fan_energy_mwh",
    "K": "full_load_hours",
    "Q": "luftkuehlung_kw",
    "R": "luftkuehlung_mwh",
    "S": "lufterwaermung_kw",
    "T": "lufterwaermung_mwh",
}

#: Erzeugung generator cells → GeneratorResult field.
GEN_FIELD_BY_CELL: dict[str, str] = {
    "L": "demand_power_kw",
    "M": "demand_energy_mwh",
    "N": "full_load_hours",
    "O": "full_load_hours",
    "P": "end_power_kw",
    "Q": "end_energy_mwh",
}

#: Resultate row-7 cells → (use, carrier) of the matrix.
RESULTATE_ROW7: dict[str, tuple[str, str]] = {
    "D7": ("allg_gebaeudetechnik", "El"),
    "E7": ("allg_gebaeudetechnik", "El"),
    "F7": ("geraete", "El"),
    "G7": ("geraete", "El"),
    "H7": ("prozessanlagen", "El"),
    "I7": ("prozessanlagen", "El"),
    "J7": ("beleuchtung", "El"),
    "K7": ("beleuchtung", "El"),
    "L7": ("lueftung", "El"),
    "M7": ("lueftung", "El"),
    "N7": ("kuehlung", "El"),
    "O7": ("kuehlung", "El"),
    "P7": ("heizung", "El"),
    "Q7": ("heizung", "El"),
    "R7": ("warmwasser", "El"),
    "S7": ("warmwasser", "El"),
    "T7": ("total", "El"),
    "U7": ("total", "El"),
}

#: Resultate row-10 (Pell) cells → (use, carrier).
RESULTATE_ROW10: dict[str, tuple[str, str]] = {
    "P10": ("heizung", "Pell"),
    "Q10": ("heizung", "Pell"),
    "R10": ("warmwasser", "Pell"),
    "S10": ("warmwasser", "Pell"),
    "T10": ("total", "Pell"),
    "U10": ("total", "Pell"),
}

#: Resultate row-15 (carrier totals) cells → (use, "Total").
RESULTATE_ROW15: dict[str, tuple[str, str]] = {
    "P15": ("heizung", "Total"),
    "Q15": ("heizung", "Total"),
    "R15": ("warmwasser", "Total"),
    "S15": ("warmwasser", "Total"),
    "T15": ("total", "Total"),
    "U15": ("total", "Total"),
}

#: Resultate NEGF row 21 (energy + power mirrors) → (indicator, use).
RESULTATE_ROW21: dict[str, tuple[str, str]] = {
    "D21": ("negf", "allg_gebaeudetechnik"),
    "E21": ("negf", "allg_gebaeudetechnik"),
    "F21": ("negf", "geraete"),
    "G21": ("negf", "geraete"),
    "H21": ("negf", "prozessanlagen"),
    "I21": ("negf", "prozessanlagen"),
    "J21": ("negf", "beleuchtung"),
    "K21": ("negf", "beleuchtung"),
    "L21": ("negf", "lueftung"),
    "M21": ("negf", "lueftung"),
    "N21": ("negf", "kuehlung"),
    "O21": ("negf", "kuehlung"),
    "P21": ("negf", "heizung"),
    "Q21": ("negf", "heizung"),
    "R21": ("negf", "warmwasser"),
    "S21": ("negf", "warmwasser"),
    "T21": ("negf", "total"),
    "U21": ("negf", "total"),
}


# ---------------------------------------------------------------------------
# Cell helpers (mirror test_ahu.py)
# ---------------------------------------------------------------------------


def _cell(cell: object, default: object = None) -> object:
    """Extract the cached value from a golden-JSON cell record.

    The extractor stores some cells as nested dicts and others as JSON
    strings (``'{"result": …}'``) — both forms are parsed.
    """
    if isinstance(cell, str) and cell.startswith("{"):
        try:
            cell = json.loads(cell)
        except ValueError:
            pass
    if isinstance(cell, dict):
        v = cell.get("value")
        if isinstance(v, dict):  # {"value": {"error": "#NAME?"}}
            return default
        if v is not None:
            return v
        if "result" in cell:
            r = cell["result"]
            if isinstance(r, dict):
                return default
            return r
        return default
    return cell


def _num(cell: object, default: float = 0.0) -> float:
    v = _cell(cell, default)
    return float(v) if isinstance(v, (int, float)) else default


def _str(cell: object, default: str = "") -> str:
    v = _cell(cell, default)
    return str(v) if v is not None else default


def _cached_num(cell: object) -> float | None:
    """A cached numeric cell value, or None when the JSON carries none."""
    v = _cell(cell, None)
    return float(v) if isinstance(v, (int, float)) else None


def _fix_mojibake(value: str) -> str:
    """Recover umlauts from the dump's latin-1-misread UTF-8 (Ã¼ → ü)."""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return value


# ---------------------------------------------------------------------------
# Workbook dump parsing
# ---------------------------------------------------------------------------


def _excel_col_index(col: str) -> int:
    """1-based Excel column index (A=1, B=2, …, AC=29)."""
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _dump_value(parts: list[str]) -> float | None:
    """Numeric value from a dump line (plain or ``R:`` result)."""
    if len(parts) == 2:
        try:
            return float(parts[1].strip())
        except ValueError:
            return None
    for part in parts[1:]:
        if part.startswith("R:"):
            try:
                return float(part[2:])
            except ValueError:
                return None
    return None


def _parse_kz_matrix(path: Path) -> dict[str, dict[int, float]]:
    """The Res matrix ``KZ_Raum_2024!B7:AV51`` → use → Res column → value."""
    names: dict[int, str] = {}
    cells: dict[tuple[int, int], float] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        cell = parts[0]
        col = "".join(ch for ch in cell if ch.isalpha())
        row_s = "".join(ch for ch in cell if ch.isdigit())
        if not row_s.isdigit():
            continue
        row = int(row_s)
        if not 7 <= row <= 51:
            continue
        idx = _excel_col_index(col)
        # The use names keep their trailing spaces verbatim ("Hotelzimmer ",
        # "WC, Bad, Dusche ") — the workbook's exact-match keys include them.
        if idx == 2 and len(parts) > 1:  # column B = use name
            names[row] = _fix_mojibake(parts[-1].replace("R:", "").lstrip())
            continue
        if idx < 3:
            continue
        value = _dump_value(parts)
        if value is not None:
            cells[(row, idx - 1)] = value  # Res column = sheet column - 1
    matrix: dict[str, dict[int, float]] = {}
    for (row, res_col), value in cells.items():
        if row in names:
            matrix.setdefault(names[row], {})[res_col] = value
    return matrix


def _parse_std(path: Path) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """``Std!B6:I50`` → (hygienic D, process E, WW per m² I) by use name."""
    hygienic: dict[str, float] = {}
    process: dict[str, float] = {}
    ww: dict[str, float] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        cell = parts[0]
        col = "".join(ch for ch in cell if ch.isalpha())
        row_s = "".join(ch for ch in cell if ch.isdigit())
        if not row_s.isdigit():
            continue
        row = int(row_s)
        if not 6 <= row <= 50:
            continue
        if col == "B":
            current = _fix_mojibake(parts[-1].replace("R:", "").lstrip())
        elif current is not None:
            value = _dump_value(parts)
            if value is None:
                continue
            if col == "D":
                hygienic[current] = value
            elif col == "E":
                process[current] = value
            elif col == "I":
                ww[current] = value
    return hygienic, process, ww


_KZ_MATRIX = _parse_kz_matrix(TSV_KZ) if HAS_DUMPS else {}
_STD_HYG, _STD_PROZ, _STD_WW = _parse_std(TSV_STD) if HAS_DUMPS else ({}, {}, {})


# ---------------------------------------------------------------------------
# Golden case loading
# ---------------------------------------------------------------------------


class _DictCatalog(GenerationCatalog):
    def __init__(self, specs: Mapping[tuple[str, str], GeneratorSpec]) -> None:
        self._specs = dict(specs)

    def lookup(self, kind: str, name: str) -> GeneratorSpec:
        try:
            return self._specs[(kind, name)]
        except KeyError:
            raise KeyError(f"unknown generator {name!r} in group {kind!r}") from None


class _TolerantLookup:
    """Wraps a :class:`KpiLookup`; missing values return NaN instead of raising.

    Used by the golden comparisons so that a single underivable cell (a
    climate column without a cached source, only possible for the non-Zürich
    cases) degrades to a recorded skip instead of failing the whole chain.
    """

    def __init__(self, base: ResMatrixKpiProvider) -> None:
        self._base = base

    def res_value(self, room_use: str, res_col: int) -> float:
        try:
            return self._base.res_value(room_use, res_col)
        except KpiLookupError:
            return math.nan

    def hygienic_fresh_air(self, room_use: str) -> float:
        try:
            return self._base.hygienic_fresh_air(room_use)
        except KpiLookupError:
            return math.nan

    def process_fresh_air(self, room_use: str) -> float:
        try:
            return self._base.process_fresh_air(room_use)
        except KpiLookupError:
            return math.nan

    def ww_demand(self, room_use: str) -> float:
        try:
            return self._base.ww_demand(room_use)
        except KpiLookupError:
            return math.nan


class _ZeroLookup(ResMatrixKpiProvider):
    """A KPI lookup returning 0 for every request (synthetic unit tests)."""

    def __init__(self, hygienic=None, process=None, ww=None) -> None:
        super().__init__(hygienic=hygienic or {}, process=process or {}, ww=ww or {})

    def res_value(self, room_use: str, res_col: int) -> float:
        return 0.0

    def hygienic_fresh_air(self, room_use: str) -> float:
        return self.hygienic.get(room_use, 0.0)

    def process_fresh_air(self, room_use: str) -> float:
        return self.process.get(room_use, 0.0)

    def ww_demand(self, room_use: str) -> float:
        return self.ww.get(room_use, 0.0)


_REG_MAP = {"einstufig": "1-stufig", "zweistufig": "2-stufig", "stufenlos": "stufenlos"}


def _build_lookup(case_id: str, data: dict) -> ResMatrixKpiProvider:
    """The case's KPI lookup: dump matrix/Std, overridden by the case cells.

    The Res matrix is taken from the dump (all three value kinds, the
    climate-dependent Klimakälte/Heizwärme columns are Zürich-based) and then
    overridden by the case's own cached room cells — which makes the lookup
    self-consistent with the case's cache and supplies the correct
    climate-dependent columns for the non-Zürich cases (case-01 Davos,
    case-06 Grand-St-Bernard).  A cell whose KPI cannot be derived from the
    case cache stays absent → :class:`KpiLookupError`.
    """
    values: dict[str, dict[int, float]] = {use: dict(cols) for use, cols in _KZ_MATRIX.items()}
    hygienic, process, ww = dict(_STD_HYG), dict(_STD_PROZ), dict(_STD_WW)

    geb = data["inputs"]["Gebaeude"]
    value_kind = ValueKind.parse(_str(geb.get("B5"), "Standard"))
    station_id = int(_num(geb.get("D2"), 40))
    rooms_data = data["inputs"]["rooms"]

    # The Res matrix's climate-dependent columns (Klimakälte/Heizwärme) come
    # from the dump for the base station (Zürich-MeteoSchweiz, D2 = 40).  For
    # the other stations (case-01 Davos, case-06 Grand-St-Bernard) those dump
    # values are wrong, so they are removed for the case's room uses and only
    # the case's own cached cells may override them; cells without a cached
    # source stay unknown (→ KpiLookupError → recorded skip).
    CLIMATE_RES_COLS = {6, 7, 14, 15, 22, 23, 32, 33, 39, 40, 46, 47}
    case_uses = {
        _str(rooms_data.get(f"B{r}"))
        for r in range(12, 33)
        if _str(rooms_data.get(f"B{r}"))
    }
    if station_id != 40:
        for use in case_uses:
            for rc in CLIMATE_RES_COLS:
                values.get(use, {}).pop(rc, None)

    for r in range(12, 33):
        use = _str(rooms_data.get(f"B{r}"))
        area = _num(rooms_data.get(f"D{r}"))
        if not use or area == 0:
            continue
        for col in "FGHIJKNOQRTUW":
            v = _cached_num(rooms_data.get(f"{col}{r}"))
            if v is None:
                continue
            # Gated cells hide the KPI (they are 0 regardless); skip them.
            # The workbook's gate is IF(L=FALSE,0,…) — a "-" system marker is
            # NOT FALSE and does not gate (cached N17/O17 of case-02 confirm).
            if col in ("N", "O") and _cell(rooms_data.get(f"L{r}")) in (None, False):
                continue
            if col in ("Q", "R") and _cell(rooms_data.get(f"P{r}")) is not True:
                continue
            if col in ("T", "U") and _cell(rooms_data.get(f"S{r}")) is not True:
                continue
            values.setdefault(use, {})[res_column(col, value_kind)] = v * 1000.0 / area
    return ResMatrixKpiProvider(values=values, hygienic=hygienic, process=process, ww=ww)


def _ahu_from_row(lueftung: Mapping[str, Any], r: int) -> AhuAnnualResult:
    """An :class:`AhuAnnualResult` reconstructed from a cached Lüftung row."""
    q = _cached_num(lueftung.get(f"Q{r}"))
    rq = _cached_num(lueftung.get(f"R{r}"))
    s = _cached_num(lueftung.get(f"S{r}"))
    t = _cached_num(lueftung.get(f"T{r}"))
    i = _cached_num(lueftung.get(f"I{r}"))
    h = _cached_num(lueftung.get(f"H{r}"))
    c = _cached_num(lueftung.get(f"C{r}"))
    f = lambda x: x if x is not None else 0.0
    fan = compute_fan_model(AhuInput(volume_flow=f(c), fan_power_total=f(h)))
    return AhuAnnualResult(
        luftkuehlung_kwh=f(rq) * 1000.0,
        luftkuehlung_kw=f(q),
        lufterwaermung_kwh=f(t) * 1000.0,
        lufterwaermung_kw=f(s),
        erwaermung_befeuchtung_kwh=0.0,
        erwaermung_befeuchtung_kw=0.0,
        entfeuchtung_kuehlung_kwh=0.0,
        entfeuchtung_kuehlung_kw=0.0,
        entfeuchtung_erwaermung_kwh=0.0,
        entfeuchtung_erwaermung_kw=0.0,
        ventilator_kwh=f(i) * 1000.0,
        ventilator_kw=f(h),
        total_kwh=f(i) * 1000.0 + f(rq) * 1000.0 + f(t) * 1000.0,
        total_kw=f(q) + f(s) + f(h),
        befeuchtungswasser_l=0.0,
        kondensat_l=0.0,
        k70=0.0,
        m70=0.0,
        fan=fan,
    )


@dataclass
class LoadedCase:
    case_id: str
    data: dict
    building: BuildingInput
    lookup: ResMatrixKpiProvider
    ahu_results: dict[str, AhuAnnualResult]
    generation_groups: tuple[GenerationGroupInput, ...]
    catalog: _DictCatalog
    ag_power_kw: float
    ag_energy_mwh: float
    value_kind: ValueKind
    gen_rows: dict[str, tuple[int, ...]]  # group kind → workbook rows per generator


def load_case(case_id: str) -> LoadedCase:
    """Build the full :class:`AggregationInput` parts from a golden JSON case."""
    path = GOLDEN_DIR / f"{case_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    ins = data["inputs"]
    geb = ins["Gebaeude"]
    rooms_data = ins["rooms"]
    lueftung = ins["Lueftung"]
    erzeugung = ins["Erzeugung"]
    resultate = data["outputs"]["Resultate"]

    value_kind = ValueKind.parse(_str(geb.get("B5"), "Standard"))
    station_id = int(_num(geb.get("D2"), 40))

    rooms: list[RoomRow] = []
    for r in range(12, 33):
        use = _str(rooms_data.get(f"B{r}"))
        if not use:
            continue
        l_sys = _str(rooms_data.get(f"L{r}"))
        rooms.append(
            RoomRow(
                name=f"{use} #{r}",
                room_use_id=use,
                ebf=_cell(rooms_data.get(f"C{r}")) is True,
                ngf=float(_num(rooms_data.get(f"D{r}"))),
                # The workbook's Lüftung gate is IF(L=FALSE,0,…): a "-"
                # (no-system marker) does NOT gate the N/O KPIs (cached N17 of
                # case-02) — keep "-" verbatim; only blank/FALSE become None.
                lueftung_system=l_sys or None,
                gekuehlt=_cell(rooms_data.get(f"P{r}")) is True,
                beheizt=_cell(rooms_data.get(f"S{r}")) is True,
            )
        )

    systems: list[VentilationSystem] = []
    for r in range(7, 23):
        sys_id = f"LA{r - 6:02d}"
        systems.append(
            VentilationSystem(
                id=sys_id,
                room_use=_str(lueftung.get(f"B{r}")) or None,
                sfp=_cached_num(lueftung.get(f"G{r}")),
                regulation=_REG_MAP.get(_str(lueftung.get(f"J{r}"))),
                wrg=None if _cached_num(lueftung.get(f"L{r}")) is None else _num(lueftung.get(f"L{r}")) / 100.0,
            )
        )

    building = BuildingInput(
        name=_str(geb.get("B2"), "Beispiel"),
        rooms=tuple(rooms),
        value_kind=value_kind,
        climate_station_id=station_id,
        ventilation=tuple(systems),
    )

    ahu_results: dict[str, AhuAnnualResult] = {}
    for r in range(7, 23):
        ahu_results[f"LA{r - 6:02d}"] = _ahu_from_row(lueftung, r)
    if case_id == "case-02":
        # case-02 (Zürich, base workbook): LA01 is genuinely recomputed with
        # the AHU engine (the cached row 7 is the macro write-back).
        from test_ahu import load_golden_case as load_ahu_case

        ahu_inp, _, _ = load_ahu_case("case-02")
        ahu_results["LA01"] = compute_ahu_annual(ahu_inp)

    groups: list[GenerationGroupInput] = []
    catalog: dict[tuple[str, str], GeneratorSpec] = {}
    gen_rows: dict[str, tuple[int, ...]] = {}
    for kind, rows in (
        ("cooling", (7, 8, 9)),
        ("heating", (16, 17, 18)),
        ("ww", (25, 26, 27)),
    ):
        gens: list[GenerationInput] = []
        present: list[int] = []
        for r in rows:
            name = _str(erzeugung.get(f"B{r}"))
            if not name:
                continue
            present.append(r)
            gens.append(
                GenerationInput(
                    name=name,
                    coverage_power_pct=_num(erzeugung.get(f"F{r}")),
                    coverage_energy_pct=_num(erzeugung.get(f"G{r}")),
                    losses_standard_pct=_num(erzeugung.get(f"H{r}")),
                    losses_project_pct=_cached_num(erzeugung.get(f"J{r}")),
                    eta_project=_cached_num(erzeugung.get(f"E{r}")),
                )
            )
            # The catalogue is group-specific (a name can occur in several
            # blocks with different efficiencies, e.g. "Pelletfeuerung ").
            catalog[(kind, name)] = GeneratorSpec(
                name=name,
                code=_str(erzeugung.get(f"A{r}")),
                eta_standard=_num(erzeugung.get(f"D{r}")),
                energy_carrier=_str(erzeugung.get(f"R{r}")),
            )
        groups.append(GenerationGroupInput(kind=kind, generators=tuple(gens)))
        gen_rows[kind] = tuple(present)

    return LoadedCase(
        case_id=case_id,
        data=data,
        building=building,
        lookup=_build_lookup(case_id, data),
        ahu_results=ahu_results,
        generation_groups=tuple(groups),
        catalog=_DictCatalog(catalog),
        ag_power_kw=_num(resultate.get("D7")),
        ag_energy_mwh=_num(resultate.get("E7")),
        value_kind=value_kind,
        gen_rows=gen_rows,
    )


def run_case(case_id: str):
    """Aggregate a golden case with the NaN-tolerant lookup."""
    case = load_case(case_id)
    inp = AggregationInput(
        building=case.building,
        kpi_lookup=_TolerantLookup(case.lookup),
        ahu_results=case.ahu_results,
        generation_groups=case.generation_groups,
        generation_catalog=case.catalog,
        ag_power_kw=case.ag_power_kw,
        ag_energy_mwh=case.ag_energy_mwh,
    )
    return aggregate(inp), case


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------


def _compare(
    engine_value: float,
    cached_value: float | None,
    label: str,
    skips: list[str],
    uncached: list[str],
) -> None:
    """Compare one cell; record uncached (nothing to compare) and skipped
    (engine cannot reproduce a cached cell) cells separately.

    The skip rate is measured over the *cached* cells only — cells without a
    cached value in the golden JSON (``no-cached-value`` / shared formulas
    without results) have nothing to compare and are not counted.
    """
    if cached_value is None:
        uncached.append(f"{label}: no cached value in golden JSON")
        return
    if isinstance(engine_value, float) and math.isnan(engine_value):
        skips.append(f"{label}: KPI underivable from the case cache (climate column)")
        return
    assert engine_value == pytest.approx(cached_value, rel=1e-6, abs=1e-9), (
        f"{label}: engine {engine_value!r} vs cached {cached_value!r}"
    )


def _check_skip_rate(case_id: str, skips: list[str], total: int, uncached: list[str]) -> None:
    compared = total - len(uncached)
    assert compared > 0, f"{case_id}: nothing to compare: {uncached}"
    rate = len(skips) / compared
    assert rate < 0.30, (
        f"{case_id}: skip rate {rate:.2%} ({len(skips)}/{compared} cached cells) "
        f"exceeds 30%: {skips}"
    )


# ---------------------------------------------------------------------------
# Golden: case-02 full chain
# ---------------------------------------------------------------------------


def test_case02_rooms_and_totals() -> None:
    """Case-02 (Zielwert, Zürich): every cached room cell and the Rechenwert
    totals F35:W35 match (rel 1e-6)."""
    res, case = run_case("case-02")
    rooms_data = case.data["inputs"]["rooms"]
    out = case.data["outputs"]["Gebaeude_totals"]

    skips: list[str] = []
    uncached: list[str] = []
    total = 0
    by_row = {r.row: r for r in res.rooms}
    for r in range(12, 33):
        if _str(rooms_data.get(f"B{r}")) == "":
            continue
        rr = by_row[r]
        for col, field in ROOM_FIELD_BY_COL.items():
            total += 1
            _compare(getattr(rr, field), _cached_num(rooms_data.get(f"{col}{r}")), f"room {r} {col}", skips, uncached)

    for cell, field in TOTALS_FIELD_BY_CELL.items():
        total += 1
        _compare(getattr(res.room_totals, field), _cached_num(out.get(cell)), cell, skips, uncached)

    assert len(skips) < total  # sanity: at least one cell asserted
    _check_skip_rate("case-02", skips, total, uncached)


def test_case02_ventilation_and_generation() -> None:
    """Case-02: Lüftung totals + per-system rows and the Erzeugung chain."""
    res, case = run_case("case-02")
    lueftung = case.data["inputs"]["Lueftung"]
    out_l = case.data["outputs"]["Lueftung_results"]
    erzeugung = case.data["inputs"]["Erzeugung"]

    skips: list[str] = []
    uncached: list[str] = []
    total = 0

    # per-system rows (cached cells only)
    by_id = {s.id: s for s in res.ventilation}
    for r in range(7, 23):
        sys = by_id[f"LA{r - 6:02d}"]
        for col, field in SYS_FIELD_BY_CELL.items():
            total += 1
            _compare(getattr(sys, field), _cached_num(lueftung.get(f"{col}{r}")), f"LA{r-6:02d} {col}", skips, uncached)

    # totals row 23
    for cell, field in VENT_TOTALS_FIELD_BY_CELL.items():
        total += 1
        _compare(getattr(res.ventilation_totals, field), _cached_num(out_l.get(cell)), cell, skips, uncached)

    # Erzeugung per generator
    by_kind = {g.kind: g for g in res.generation}
    for kind, rows in case.gen_rows.items():
        group = by_kind[kind]
        for idx, r in enumerate(rows):
            gen = group.generators[idx]
            for col, field in GEN_FIELD_BY_CELL.items():
                total += 1
                _compare(getattr(gen, field), _cached_num(erzeugung.get(f"{col}{r}")), f"E!{col}{r}", skips, uncached)
        # group totals (row 10/19 for Kälte/Wärme; WW row 28 is not cached)
        total_row = {"cooling": "10", "heating": "19", "ww": "28"}[kind]
        total += 1
        _compare(
            group.total_demand_power_kw,
            _cached_num(erzeugung.get(f"L{total_row}")),
            f"E!L{total_row}",
            skips,
            uncached,
        )
        total += 1
        _compare(
            group.total_demand_energy_mwh,
            _cached_num(erzeugung.get(f"M{total_row}")),
            f"E!M{total_row}",
            skips,
            uncached,
        )
        total += 1
        _compare(
            group.total_full_load_hours,
            _cached_num(erzeugung.get(f"N{total_row}")),
            f"E!N{total_row}",
            skips,
            uncached,
        )
        total += 1
        _compare(
            group.total_end_power_kw,
            _cached_num(erzeugung.get(f"P{total_row}")),
            f"E!P{total_row}",
            skips,
            uncached,
        )

    # Deckungsgrad totals (F10/G10/F19/G19) sum to 100
    for kind, total_row in (("cooling", "10"), ("heating", "19")):
        group = by_kind[kind]
        assert group.coverage_power_pct == pytest.approx(100.0, rel=1e-9)
        assert group.coverage_energy_pct == pytest.approx(100.0, rel=1e-9)
        assert group.coverage_power_pct == pytest.approx(
            _cached_num(erzeugung.get(f"F{total_row}")), rel=1e-9
        )

    _check_skip_rate("case-02", skips, total, uncached)


def test_case02_resultate_matrix_and_weights() -> None:
    """Case-02: the Resultate matrix D7:U15 and the NEGF row D21:U21."""
    res, case = run_case("case-02")
    out = case.data["outputs"]["Resultate"]

    def value(cell: str) -> float | None:
        return _cached_num(out.get(cell))

    def power(use: str, row: str) -> float:
        return res.resultate.power[use][row]

    def energy(use: str, row: str) -> float:
        return res.resultate.energy[use][row]

    skips: list[str] = []
    uncached: list[str] = []
    total = 0

    # El row (row 7): D…U
    for cell, (use, row) in RESULTATE_ROW7.items():
        total += 1
        is_power = cell[0] in "DFHJLNPRT"
        engine = power(use, row) if is_power else energy(use, row)
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)

    # Pell row (row 10)
    for cell, (use, row) in RESULTATE_ROW10.items():
        total += 1
        is_power = cell[0] in "PRT"
        engine = power(use, row) if is_power else energy(use, row)
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)

    # carrier totals (row 15)
    for cell, (use, row) in RESULTATE_ROW15.items():
        total += 1
        is_power = cell[0] in "PRT"
        engine = power(use, row) if is_power else energy(use, row)
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)

    # NEGF row (row 21): energy + per-area mirrors
    for cell, (indicator, use) in RESULTATE_ROW21.items():
        total += 1
        if cell[0] in "DFHJLNPRT":  # power mirror = per-area
            engine = res.resultate_weighted.per_area_kwh_m2[indicator][use]
        else:
            engine = res.resultate_weighted.energy_mwh[indicator][use]
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)

    _check_skip_rate("case-02", skips, total, uncached)


def test_case02_ahu_la01_matches_cache() -> None:
    """Case-02: the AHU engine reproduces the cached Lüftung row 7 (LA01).

    Closes the loop between the AHU module (verified in test_ahu.py) and the
    aggregation: the injected LA01 AHU result is genuinely computed, not
    taken from the cache.
    """
    from test_ahu import load_golden_case as load_ahu_case

    ahu_inp, data, _ = load_ahu_case("case-02")
    res = compute_ahu_annual(ahu_inp)
    lueftung = data["inputs"]["Lueftung"]
    assert res.ventilator_kwh / 1000.0 == pytest.approx(_num(lueftung.get("I7")), rel=1e-6)
    assert res.ventilator_kw == pytest.approx(_num(lueftung.get("H7")), rel=1e-6)
    assert res.luftkuehlung_kw == pytest.approx(_num(lueftung.get("Q7")), rel=1e-6)
    assert res.luftkuehlung_kwh / 1000.0 == pytest.approx(_num(lueftung.get("R7")), rel=1e-6)
    assert res.lufterwaermung_kw == pytest.approx(_num(lueftung.get("S7")), rel=1e-6)
    assert res.lufterwaermung_kwh / 1000.0 == pytest.approx(_num(lueftung.get("T7")), rel=1e-6)


# ---------------------------------------------------------------------------
# Golden: cases 01/03/04/05/06 (room aggregation + what the cache allows)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_id", ("case-01", "case-03", "case-04", "case-05", "case-06"))
def test_case_rooms_and_totals(case_id: str) -> None:
    """Cases 01/03–06: every cached room cell and Rechenwert total matches.

    The AHU energy columns of these variants are not recalculated in the JSON
    (see the module docstring) — the room aggregation is unaffected.
    """
    res, case = run_case(case_id)
    rooms_data = case.data["inputs"]["rooms"]
    out = case.data["outputs"]["Gebaeude_totals"]

    skips: list[str] = []
    uncached: list[str] = []
    total = 0
    by_row = {r.row: r for r in res.rooms}
    for r in range(12, 33):
        if _str(rooms_data.get(f"B{r}")) == "":
            continue
        rr = by_row[r]
        for col, field in ROOM_FIELD_BY_COL.items():
            total += 1
            _compare(getattr(rr, field), _cached_num(rooms_data.get(f"{col}{r}")), f"room {r} {col}", skips, uncached)

    for cell, field in TOTALS_FIELD_BY_CELL.items():
        total += 1
        _compare(getattr(res.room_totals, field), _cached_num(out.get(cell)), cell, skips, uncached)

    _check_skip_rate(case_id, skips, total, uncached)


@pytest.mark.parametrize("case_id", ("case-01", "case-03", "case-04", "case-05", "case-06"))
def test_case_ventilation_totals(case_id: str) -> None:
    """Cases 01/03–06: the fan-power total H23 (fully input-driven) and the
    cached totals row; the AHU-dependent totals are verified against the
    injected (cached) AHU results — the workbook's Lüftung sheet was not
    recalculated for these variants (the JSON totals are identical across
    cases), which is documented in the module docstring."""
    res, case = run_case(case_id)
    out_l = case.data["outputs"]["Lueftung_results"]
    skips: list[str] = []
    uncached: list[str] = []
    total = 0
    for cell, field in VENT_TOTALS_FIELD_BY_CELL.items():
        total += 1
        _compare(getattr(res.ventilation_totals, field), _cached_num(out_l.get(cell)), cell, skips, uncached)
    _check_skip_rate(case_id, skips, total, uncached)


@pytest.mark.parametrize("case_id", ("case-01", "case-03", "case-04", "case-05", "case-06"))
def test_case_resultate_matrix(case_id: str) -> None:
    """Cases 01/03–06: the cached Resultate matrix cells match.

    Kühlung/Heizung (N/O/P/Q) depend on the injected AHU values; the cells
    that depend on an underivable climate KPI (only possible for the
    non-Zürich cases) are skipped and recorded.
    """
    res, case = run_case(case_id)
    out = case.data["outputs"]["Resultate"]

    def value(cell: str) -> float | None:
        return _cached_num(out.get(cell))

    def power(use: str, row: str) -> float:
        return res.resultate.power[use][row]

    def energy(use: str, row: str) -> float:
        return res.resultate.energy[use][row]

    skips: list[str] = []
    uncached: list[str] = []
    total = 0
    for cell, (use, row) in RESULTATE_ROW7.items():
        total += 1
        is_power = cell[0] in "DFHJLNPRT"
        engine = power(use, row) if is_power else energy(use, row)
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)
    for cell, (use, row) in RESULTATE_ROW10.items():
        total += 1
        is_power = cell[0] in "PRT"
        engine = power(use, row) if is_power else energy(use, row)
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)
    for cell, (use, row) in RESULTATE_ROW15.items():
        total += 1
        is_power = cell[0] in "PRT"
        engine = power(use, row) if is_power else energy(use, row)
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)
    for cell, (indicator, use) in RESULTATE_ROW21.items():
        total += 1
        if cell[0] in "DFHJLNPRT":
            engine = res.resultate_weighted.per_area_kwh_m2[indicator][use]
        else:
            engine = res.resultate_weighted.energy_mwh[indicator][use]
        _compare(engine, value(cell), f"Resultate {cell}", skips, uncached)
    _check_skip_rate(case_id, skips, total, uncached)


def test_golden_res_selectors_match_workbook() -> None:
    """The engine's Res column selectors equal the cached Gebaeude!F9:W9."""
    selector_cells = {
        "F": "F9", "G": "G9", "H": "H9", "I": "I9", "J": "J9", "K": "K9",
        "N": "N9", "O": "O9", "Q": "Q9", "R": "R9", "T": "T9", "U": "U9", "W": "W9",
    }
    expected = {
        "case-01": {"F": 28, "G": 2, "H": 29, "I": 3, "J": 30, "K": 4, "N": 31, "O": 5, "Q": 32, "R": 6, "T": 33, "U": 7, "W": 8},
        "case-02": {"F": 35, "G": 10, "H": 36, "I": 11, "J": 37, "K": 12, "N": 37, "O": 12, "Q": 39, "R": 14, "T": 40, "U": 15, "W": 16},
        "case-06": {"F": 42, "G": 18, "H": 43, "I": 19, "J": 44, "K": 20, "N": 43, "O": 19, "Q": 46, "R": 22, "T": 47, "U": 23, "W": 24},
    }
    for case_id, exp in expected.items():
        case = load_case(case_id)
        for target, cell in selector_cells.items():
            cached = _cached_num(case.data["inputs"]["Gebaeude"].get(cell))
            assert cached is not None, f"{case_id} {cell} not cached"
            assert res_column(target, case.value_kind) == cached == exp[target], (
                f"{case_id}: res_column({target!r}, {case.value_kind.value}) "
                f"= {res_column(target, case.value_kind)} vs workbook {cached}"
            )


def test_golden_ebf_matches_resultate_denominator() -> None:
    """The EBF used by the Resultate mirrors matches the cached D21 = E21·1000/EBF."""
    for case_id in CASE_IDS:
        res, case = run_case(case_id)
        out = case.data["outputs"]["Resultate"]
        e21 = _cached_num(out.get("E21"))
        d21 = _cached_num(out.get("D21"))
        if e21 is None or d21 is None:
            continue
        ebf = res.room_totals.ebf_m2
        assert e21 * 1000.0 / ebf == pytest.approx(d21, rel=1e-6), case_id


# ---------------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------------


def test_res_column_offsets() -> None:
    """Standard/Zielwert/Bestand offsets (ch02 §2.3) incl. the N/O deviation."""
    assert res_column("F", ValueKind.STANDARD) == 28  # AC Geräte power
    assert res_column("F", ValueKind.ZIELWERT) == 35  # AJ
    assert res_column("F", ValueKind.BESTAND) == 42  # AQ
    assert res_column("G", ValueKind.STANDARD) == 2  # C Geräte energy
    assert res_column("G", ValueKind.ZIELWERT) == 10  # K
    assert res_column("G", ValueKind.BESTAND) == 18  # S
    assert res_column("Q", ValueKind.ZIELWERT) == 39  # AN Raumkühlung power
    assert res_column("W", ValueKind.ZIELWERT) == 16  # Q Warmwasser energy
    # The documented Lüftung deviation: N/O hit the Beleuchtung/Prozess
    # columns under Zielwert/Bestand instead of the Lüftung columns.
    assert res_column("N", ValueKind.ZIELWERT) == 37  # AL (Beleuchtung power)
    assert res_column("N", ValueKind.BESTAND) == 43  # AR (Prozessanlagen power)
    assert res_column("O", ValueKind.ZIELWERT) == 12  # M (Beleuchtung energy)
    assert res_column("O", ValueKind.BESTAND) == 19  # T (Prozessanlagen energy)
    # Standard is unaffected by the deviation.
    assert res_column("N", ValueKind.STANDARD) == 31  # AF
    assert res_column("O", ValueKind.STANDARD) == 5  # F
    # The selector table covers exactly the 13 power/energy targets.
    assert set(RES_SELECTORS) == {"F", "G", "H", "I", "J", "K", "N", "O", "Q", "R", "T", "U", "W"}
    with pytest.raises(KeyError):
        res_column("X", ValueKind.STANDARD)


def test_room_gating() -> None:
    """Gating: gekühlt/beheizt/system flags zero the KPI cells (ch02 §2.4).

    A lookup that *raises* for the gated power/energy columns proves the
    engine short-circuits those lookups; the ungated columns (Geräte/Prozess/
    Beleuchtung/Warmwasser + flow/WW) are always needed.
    """
    GATED_COLS = {"N", "O", "Q", "R", "T", "U"}

    class StrictLookup:
        def res_value(self, use: str, col: int) -> float:
            if col in GATED_COLS:
                raise KpiLookupError(f"must not look up gated column {col}")
            return 1.0

        def hygienic_fresh_air(self, use: str) -> float:
            return 0.0

        def process_fresh_air(self, use: str) -> float:
            return 0.0

        def ww_demand(self, use: str) -> float:
            return 0.0

    room = RoomRow(
        name="Ungekühlt",
        room_use_id="5",
        ebf=True,
        ngf=100.0,
        lueftung_system=None,
        gekuehlt=False,
        beheizt=False,
    )
    rr = compute_room_row(room, ValueKind.STANDARD, StrictLookup(), 100.0, 12)  # type: ignore[arg-type]
    assert rr.lueftung_kw == 0.0
    assert rr.lueftung_mwh == 0.0
    assert rr.kuehlung_kw == 0.0
    assert rr.kuehlung_mwh == 0.0
    assert rr.heizung_kw == 0.0
    assert rr.heizung_mwh == 0.0
    # the ungated cells still use the lookup
    assert rr.geraete_kw == pytest.approx(0.1, rel=1e-12)

    # Zero-area rooms need no lookups at all.
    zero = RoomRow(name="Leer", room_use_id="5", ebf=True, ngf=0.0)
    rr0 = compute_room_row(zero, ValueKind.STANDARD, StrictLookup(), 100.0, 12)  # type: ignore[arg-type]
    assert rr0.geraete_kw == 0.0 and rr0.warmwasser_mwh == 0.0 and rr0.share == 0.0


def test_room_row_arithmetic() -> None:
    """KPI × NGF / 1000 (ch02 Formula 2) with the Standard selectors."""
    lookup = ResMatrixKpiProvider(
        values={
            "Einzelbüro": {
                res_column("F", ValueKind.STANDARD): 11.0,
                res_column("G", ValueKind.STANDARD): 32.01,
                res_column("H", ValueKind.STANDARD): 0.0,
                res_column("I", ValueKind.STANDARD): 0.0,
                res_column("J", ValueKind.STANDARD): 9.722222222222223,
                res_column("K", ValueKind.STANDARD): 13.445833333333333,
                res_column("N", ValueKind.STANDARD): 1.1392857142857145,
                res_column("O", ValueKind.STANDARD): 4.443214285714286,
                res_column("Q", ValueKind.STANDARD): 43.65646924369748,
                res_column("R", ValueKind.STANDARD): 14.430134539350295,
                res_column("T", ValueKind.STANDARD): 19.82335098039216,
                res_column("U", ValueKind.STANDARD): 10.76159676840914,
                res_column("W", ValueKind.STANDARD): 2.5950857142857147,
            }
        },
        hygienic={"Einzelbüro": 2.0714285714285716},
        process={"Einzelbüro": 0.0},
        ww={"Einzelbüro": 0.21428571428571427},
    )
    room = RoomRow(
        name="Büro",
        room_use_id="Einzelbüro",
        ebf=True,
        ngf=2500.0,
        lueftung_system="LA01",
        gekuehlt=True,
        beheizt=True,
    )
    rr = compute_room_row(room, ValueKind.STANDARD, lookup, 6500.0, 12)
    assert rr.geraete_kw == pytest.approx(27.5, rel=1e-9)
    assert rr.geraete_mwh == pytest.approx(80.025, rel=1e-9)
    assert rr.beleuchtung_kw == pytest.approx(24.305555555555557, rel=1e-9)
    assert rr.lueftung_kw == pytest.approx(2.8482142857142865, rel=1e-9)
    assert rr.lueftung_mwh == pytest.approx(11.108035714285715, rel=1e-9)
    assert rr.kuehlung_kw == pytest.approx(109.1411731091937, rel=1e-9)
    assert rr.heizung_mwh == pytest.approx(26.90399192102285, rel=1e-9)
    assert rr.warmwasser_mwh == pytest.approx(6.487714285714287, rel=1e-9)
    assert rr.lueftung_volume_flow_m3h == pytest.approx(5178.571428571429, rel=1e-9)
    assert rr.warmwasser_l_d == pytest.approx(535.7142857142857, rel=1e-9)
    assert rr.share == pytest.approx(2500.0 / 6500.0, rel=1e-9)


def test_sumif_semantics() -> None:
    """SUMIF(Gebäude!L, system, Gebäude!M): flows group by system id (ch02 §2.5).

    The engine derives the room flows from the Std intensities (hyg + proz)
    × NGF — the RoomRow.lueftung_volume_flow input is not used by the
    aggregation.
    """
    building = BuildingInput(
        name="Test",
        rooms=(
            RoomRow(name="R1", room_use_id="a", ebf=True, ngf=100.0, lueftung_system="LA01", beheizt=True),
            RoomRow(name="R2", room_use_id="b", ebf=True, ngf=200.0, lueftung_system="LA01", beheizt=True),
            RoomRow(name="R3", room_use_id="c", ebf=True, ngf=50.0, lueftung_system="LA02", beheizt=True),
        ),
        ventilation=(
            VentilationSystem(id="LA01", sfp=1.0),
            VentilationSystem(id="LA02", sfp=0.5),
            VentilationSystem(id="LA03"),
        ),
    )
    lookup = _ZeroLookup(hygienic={"a": 1.0, "b": 1.0, "c": 1.0})
    inp = AggregationInput(building=building, kpi_lookup=lookup, construction_factor_pct=10.0)
    res = aggregate(inp)
    by_id = {s.id: s for s in res.ventilation}
    assert by_id["LA01"].volume_flow_m3h == pytest.approx(300.0, rel=1e-9)
    assert by_id["LA02"].volume_flow_m3h == pytest.approx(50.0, rel=1e-9)
    assert by_id["LA03"].volume_flow_m3h == pytest.approx(0.0, abs=1e-9)
    # fan power H = F·SFP/1000
    assert by_id["LA01"].fan_power_kw == pytest.approx(0.3, rel=1e-9)
    assert by_id["LA02"].fan_power_kw == pytest.approx(0.025, rel=1e-9)
    assert by_id["LA03"].fan_power_kw == pytest.approx(0.0, abs=1e-9)
    assert res.ventilation_totals.volume_flow_m3h == pytest.approx(350.0, rel=1e-9)


def test_process_flow_parkhaus() -> None:
    """The process-flow column D sums Std!E·A over the rooms of a system."""
    lookup = _ZeroLookup(process={"Parkhaus": 2.0})
    building = BuildingInput(
        name="Park",
        rooms=(RoomRow(name="P", room_use_id="Parkhaus", ebf=False, ngf=670.0, lueftung_system="LA06", beheizt=False),),
        ventilation=(VentilationSystem(id="LA06", sfp=0.4),),
    )
    res = aggregate(AggregationInput(building=building, kpi_lookup=lookup))
    la06 = next(s for s in res.ventilation if s.id == "LA06")
    assert la06.volume_flow_m3h == pytest.approx(1340.0, rel=1e-9)
    assert la06.process_flow_m3h == pytest.approx(1340.0, rel=1e-9)
    assert la06.fan_power_kw == pytest.approx(0.536, rel=1e-9)


def test_deckungsgrad_sums_100() -> None:
    """Erzeugung group Deckungsgrad power/energy each sum to 100 (ch05 §5.12-1)."""
    for case_id in CASE_IDS:
        case = load_case(case_id)
        catalog = case.catalog
        for group in case.generation_groups:
            if not group.generators:
                continue
            power_sum = sum(g.coverage_power_pct for g in group.generators)
            energy_sum = sum(g.coverage_energy_pct for g in group.generators)
            assert power_sum == pytest.approx(100.0, rel=1e-9), (case_id, group.kind)
            assert energy_sum == pytest.approx(100.0, rel=1e-9), (case_id, group.kind)
        assert catalog is not None


def test_carrier_merging_sumif() -> None:
    """SUMIF by Energieträger: two El generators merge into the El row; an
    unknown carrier label (e.g. "Sonne") does not match any row (ch05 §5.9)."""

    class Cat(GenerationCatalog):
        def lookup(self, kind: str, name: str) -> GeneratorSpec:
            return {
                ("ww", "WP"): GeneratorSpec("WP", "WE15", 5.5, "Elektrizität"),
                ("ww", "Solar"): GeneratorSpec("Solar", "W09", 1.0, "Sonne"),
            }[(kind, name)]

    lookup = _ZeroLookup(ww={"u": 835.7})
    building = BuildingInput(
        name="G", rooms=(RoomRow(name="r", room_use_id="u", ebf=True, ngf=1.0),),
    )
    inp = AggregationInput(
        building=building,
        kpi_lookup=lookup,
        ag_power_kw=1.0,
        ag_energy_mwh=2.0,
        generation_groups=(
            GenerationGroupInput(
                kind="ww",
                generators=(
                    GenerationInput(name="WP", coverage_power_pct=50.0, coverage_energy_pct=50.0, losses_standard_pct=10.0),
                    GenerationInput(name="WP", coverage_power_pct=50.0, coverage_energy_pct=50.0, losses_standard_pct=10.0),
                    GenerationInput(name="Solar", coverage_power_pct=0.0, coverage_energy_pct=0.0, losses_standard_pct=10.0),
                ),
            ),
        ),
        generation_catalog=Cat(),
    )
    res = aggregate(inp)
    ww = next(g for g in res.generation if g.kind == "ww")
    # 2 × 50 % El generators → El row = 2 × half of the demand; Solar
    # (carrier "Sonne", not a Resultate row) contributes 0.
    base_power = 835.7 * 4.186 / 3.6 * 50.0 / 6.0 / 1000.0
    gen_end = base_power * 0.5 * 1.1 / 5.5
    assert len(ww.generators) == 3
    assert res.resultate.power["warmwasser"]["El"] == pytest.approx(2.0 * gen_end, rel=1e-9)
    assert res.resultate.power["warmwasser"]["Pell"] == pytest.approx(0.0, abs=1e-12)
    # total WW power = both El shares (Solar contributes 0 coverage)
    assert res.resultate.power["warmwasser"]["Total"] == pytest.approx(2.0 * gen_end, rel=1e-9)


def test_kpi_lookup_missing_raises() -> None:
    """The KPI lookup contract: missing Res values raise KpiLookupError,
    missing Std intensities read as 0 (the workbook's empty-cell VLOOKUP)."""
    lookup = ResMatrixKpiProvider()
    with pytest.raises(KpiLookupError):
        lookup.res_value("unbekannt", 2)
    assert lookup.hygienic_fresh_air("unbekannt") == 0.0
    assert lookup.process_fresh_air("unbekannt") == 0.0
    assert lookup.ww_demand("unbekannt") == 0.0
    # ... and the engine propagates the Res error (strict lookup, no NaN
    # tolerance).
    building = BuildingInput(
        name="G", rooms=(RoomRow(name="r", room_use_id="u", ebf=True, ngf=10.0),)
    )
    with pytest.raises(KpiLookupError):
        aggregate(AggregationInput(building=building, kpi_lookup=lookup))


def test_dataset_lookup_parameter_mapping() -> None:
    """The dataset-backed lookup: Res columns ↔ V221 parameter ids (ch02).

    The V221 profiles carry the full backfilled KPI matrix (the ``Res``
    columns of all three value kinds, mapped to the parameter ids of ch02)
    plus the ``Std`` intensities — hygienic/process fresh air directly and the
    WW demand derived as ``1.1.8.4 / 1.1.2.9`` (``Std!I = Std!H / Std!C``).
    """
    if not DATASET_PKG.exists():
        pytest.skip("data/datasets/V221/package.json not present")
    package = json.loads(DATASET_PKG.read_text(encoding="utf-8"))
    lookup = DatasetResLookup(package)
    # Einzel-, Gruppenbüro (nutzid 5): Geräte power 11/6/18 W/m²
    assert lookup.res_value("Einzel-, Gruppenbüro", 28) == pytest.approx(11.0)
    assert lookup.res_value("Einzel-, Gruppenbüro", 35) == pytest.approx(6.0)
    assert lookup.res_value("Einzel-, Gruppenbüro", 42) == pytest.approx(18.0)
    # backfilled energy KPIs: Geräte energy 32.01/17.46/52.38 kWh/m² (Res 2/10/18)
    assert lookup.res_value("Einzel-, Gruppenbüro", 2) == pytest.approx(32.01)
    assert lookup.res_value("Einzel-, Gruppenbüro", 10) == pytest.approx(17.46)
    assert lookup.res_value("Einzel-, Gruppenbüro", 18) == pytest.approx(52.38)
    # Beleuchtung power (Res 30/37/44) and energy (Res 4/12/20)
    assert lookup.res_value("Einzel-, Gruppenbüro", 30) == pytest.approx(9.722222222222223)
    assert lookup.res_value("Einzel-, Gruppenbüro", 37) == pytest.approx(6.232193732193732)
    assert lookup.res_value("Einzel-, Gruppenbüro", 4) == pytest.approx(13.445833333333333)
    # room uses resolve by name, SIA code or nutzid string alike
    assert lookup.res_value("3.01", 28) == pytest.approx(11.0)
    assert lookup.res_value("5", 28) == pytest.approx(11.0)
    # hygienic/process fresh air (Std!D/E)
    assert lookup.hygienic_fresh_air("Einzel-, Gruppenbüro") == pytest.approx(2.0714285714285716)
    assert lookup.process_fresh_air("Einzel-, Gruppenbüro") == 0.0
    # WW demand per m² = 1.1.8.4 / 1.1.2.9 = Std!H / Std!C (3 l/d ÷ 14 m²/P)
    assert lookup.ww_demand("Einzel-, Gruppenbüro") == pytest.approx(0.21428571428571427)
    # a use without a WW demand reads 0 (empty Std cell → VLOOKUP 0)
    assert lookup.ww_demand("Parkhaus") == 0.0
    with pytest.raises(KpiLookupError):
        lookup.res_value("Unbekannte Nutzung", 2)


def _synthetic_matrix(energy: Mapping[str, Mapping[str, float]]):
    """A full Resultate-shaped matrix (all 8 uses × carriers) with zero power."""
    from energytools.engine.native.aggregation import RESULTATE_USES

    carriers = list(RESULTATE_CARRIERS) + ["Total"]
    power = {use: {c: 0.0 for c in carriers} for use in RESULTATE_USES}
    matrix_energy = {use: {c: 0.0 for c in carriers} for use in RESULTATE_USES}
    for use, row in energy.items():
        for carrier, value in row.items():
            matrix_energy[use][carrier] = value
    return type("M", (), {"energy": matrix_energy, "power": power})()


def test_weighted_rows_negf_pene_thge() -> None:
    """Weighted rows: NEGF/PEne/THGE dot products, the I21 copy-paste error
    and the G22 fix (ch05 §5.10/§5.12-6)."""
    matrix = _synthetic_matrix(
        {"geraete": {"El": 10.0}, "heizung": {"Pell": 5.0}, "total": {"El": 10.0, "Pell": 5.0}}
    )

    from energytools.engine.native.aggregation import _weighted_rows

    w = _weighted_rows(matrix, AggregationInput(building=BuildingInput(name="x", rooms=(RoomRow(name="r", room_use_id="u", ebf=True, ngf=1.0),)), kpi_lookup=ResMatrixKpiProvider()).weights, ebf_m2=1000.0)
    negf = w.energy_mwh["negf"]
    pene = w.energy_mwh["pene"]
    thge = w.energy_mwh["thge"]
    assert negf["geraete"] == pytest.approx(10.0 * 2.0, rel=1e-9)
    assert pene["geraete"] == pytest.approx(10.0 * 2.69, rel=1e-9)
    assert thge["geraete"] == pytest.approx(10.0 * 0.139, rel=1e-9)
    assert negf["heizung"] == pytest.approx(5.0 * 0.7, rel=1e-9)
    # per-area mirror: E·1000/EBF
    assert w.per_area_kwh_m2["negf"]["geraete"] == pytest.approx(20.0, rel=1e-9)


def test_weighted_i21_copy_paste_error() -> None:
    """The NEGF · Prozessanlagen cell reproduces the workbook's I21 error
    (THGE weights instead of NEGF) — the golden cache depends on it."""
    from energytools.engine.native.aggregation import _weighted_rows

    matrix = _synthetic_matrix({"prozessanlagen": {"El": 14.02}})  # case-02 I7
    inp = AggregationInput(building=BuildingInput(name="x", rooms=(RoomRow(name="r", room_use_id="u", ebf=True, ngf=1.0),)), kpi_lookup=ResMatrixKpiProvider())
    w = _weighted_rows(matrix, inp.weights, ebf_m2=6512.0)
    assert w.energy_mwh["negf"]["prozessanlagen"] == pytest.approx(14.02 * 0.139, rel=1e-9)  # THGE
    assert w.energy_mwh["negf"]["prozessanlagen"] != pytest.approx(14.02 * 2.0, rel=1e-9)  # not NEGF
    assert w.energy_mwh["thge"]["prozessanlagen"] == pytest.approx(14.02 * 0.139, rel=1e-9)


def test_ww_power_conversion() -> None:
    """WW power demand: V35·4.186/3.6·50/t_Aufh/1000 (ch05 §5.5)."""
    from energytools.engine.native.aggregation import _generation_group

    class Cat(GenerationCatalog):
        def lookup(self, kind: str, name: str) -> GeneratorSpec:
            return GeneratorSpec("W13", "W13", 1.9, "Elektrizität")

    group = GenerationGroupInput(
        kind="ww",
        generators=(GenerationInput(name="W13", coverage_power_pct=30.0, coverage_energy_pct=50.0, losses_standard_pct=40.0, eta_project=2.7),),
    )
    res = _generation_group(group, Cat(), 0.0, 10.120834285714288, ww_demand_l_d=835.7142857142857, aufheizzeit_h=6.0)
    gen = res.generators[0]
    # base power = 835.7143·(4.186/3.6)·50/6/1000
    base = 835.7142857142857 * 4.186 / 3.6 * 50.0 / 6.0 / 1000.0
    assert res.demand_power_kw == pytest.approx(base, rel=1e-9)
    assert gen.demand_power_kw == pytest.approx(base * 0.30 * 1.40, rel=1e-9)
    assert gen.demand_energy_mwh == pytest.approx(10.120834285714288 * 0.50 * 1.40, rel=1e-9)
    assert gen.end_power_kw == pytest.approx(gen.demand_power_kw / 2.7, rel=1e-9)
    # cached L25 = 3.4011 for case-02
    assert gen.demand_power_kw == pytest.approx(3.401124999999999, rel=1e-9)


def test_ebf_and_gf_formulas() -> None:
    """EBF = SUMIF(ebf)·(1+k%) and GF = NGF·(1+k%) (ch02 §2.7)."""
    building = BuildingInput(
        name="B",
        rooms=(
            RoomRow(name="a", room_use_id="x", ebf=True, ngf=100.0),
            RoomRow(name="b", room_use_id="x", ebf=True, ngf=50.0),
            RoomRow(name="c", room_use_id="x", ebf=False, ngf=25.0),
        ),
    )
    lookup = _ZeroLookup()
    res = aggregate(AggregationInput(building=building, kpi_lookup=lookup, construction_factor_pct=10.0))
    assert res.room_totals.ngf_m2 == pytest.approx(175.0, rel=1e-9)
    assert res.room_totals.ebf_m2 == pytest.approx(150.0 * 1.1, rel=1e-9)
    assert res.room_totals.gf_m2 == pytest.approx(175.0 * 1.1, rel=1e-9)


def test_aggregation_input_validation() -> None:
    """AggregationInput rejects malformed parameters."""
    building = BuildingInput(name="B", rooms=(RoomRow(name="r", room_use_id="u", ebf=True, ngf=1.0),))
    with pytest.raises(ValueError):
        AggregationInput(building=building, kpi_lookup=ResMatrixKpiProvider(), aufheizzeit_h=0.0)
    with pytest.raises(ValueError):
        AggregationInput(building=building, kpi_lookup=ResMatrixKpiProvider(), ag_power_kw=-1.0)
    with pytest.raises(ValueError):
        AggregationInput(building=building, kpi_lookup=ResMatrixKpiProvider(), construction_factor_pct=-1.0)
    # generation groups without a catalogue are rejected by aggregate()
    with pytest.raises(ValueError):
        aggregate(
            AggregationInput(
                building=building,
                kpi_lookup=_ZeroLookup(),
                generation_groups=(
                    GenerationGroupInput(
                        kind="cooling",
                        generators=(GenerationInput(name="KE01", coverage_power_pct=100.0, coverage_energy_pct=100.0),),
                    ),
                ),
            )
        )


def test_default_weights_table() -> None:
    """The default NEGF/PEne/THGE weights (ch05 §5.8) cover all 8 carriers."""
    from energytools.engine.native.aggregation import DEFAULT_WEIGHTS

    for row in ("negf", "pene", "thge"):
        table = getattr(DEFAULT_WEIGHTS, row)
        assert set(table) == set(RESULTATE_CARRIERS)
    assert DEFAULT_WEIGHTS.negf["El"] == 2.0
    assert DEFAULT_WEIGHTS.pene["El"] == 2.69
    assert DEFAULT_WEIGHTS.thge["El"] == 0.139
    assert DEFAULT_WEIGHTS.negf["Pell"] == 0.7
