"""Compare the AHU engine against the golden Excel caches.

CLI: prints a per-case × result-row (254–260) table of engine value vs cached
value vs relative error, so the port can be reviewed at a glance.

Usage:
    pixi run -e dev python verify/compare_ahu.py [case-01 case-02 ...]
    (default: all six golden cases)

The golden JSON caches only a subset of rows 254–260 (the ExcelJS extraction
dropped the shared-formula results; see verify/extract-golden.js). Cells
without a cached value are printed as ``-``. For case-02 the missing cells
are filled from the workbook dump ``.analysis/dumps/gebaeude/sheet_61_Berechnung
LU.tsv`` (same station and inputs).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tests"))

from test_ahu import ANNUAL_CELLS, load_golden_case

from energytools.engine.native.ahu import compute_ahu_annual

CASES = ["case-01", "case-02", "case-03", "case-04", "case-05", "case-06"]


def _rel(a: float, b: float) -> str:
    if a == b:
        return "0"
    if b == 0:
        return "-" if abs(a) < 1e-9 else "inf"
    return f"{abs(a - b) / abs(b):.2e}"


def main(argv: list[str]) -> int:
    cases = [c for c in argv if c in CASES] or CASES
    # per-case cached values from the JSON + the TSV fallback for case-02
    from test_ahu import TSV, _cached_annual, _parse_tsv_values

    tsv = _parse_tsv_values(TSV) if TSV.exists() else {}

    for case in cases:
        inp, data, station = load_golden_case(case)
        res = compute_ahu_annual(inp)
        out = data["outputs"]["BerechnungLU"]
        print(f"== {case}  (station: {station}) ==")
        print(f"   {'row':<5}{'engine':>16}{'cached':>16}{'rel.err':>10}")
        for cell, attr in ANNUAL_CELLS:
            engine = getattr(res, attr)
            cached = _cached_annual(out, cell)
            if cached is None and case == "case-02":
                cached = tsv.get(cell)
            if cached is None:
                print(f"   {cell:<5}{engine:>16.8g}{'-':>16}{'-':>10}   (no cache)")
                continue
            print(f"   {cell:<5}{engine:>16.8g}{cached:>16.8g}{_rel(engine, cached):>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
