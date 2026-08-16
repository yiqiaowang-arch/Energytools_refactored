"""Tests for the native psychrometric port (``FeuchteLuft_Formeln.bas``).

Three layers:

1. **Cache-value comparison** (the primary oracle): hardcoded (input, cached
   value) pairs extracted from the workbook dumps ``.analysis/dumps/gebaeude``
   — ``Klimadaten!Q5:Q65`` (``AbsFeuchte``, 61 rows) and the ``Berechnung LU``
   interval rows 121/168/200/230/249 (``RelFeuchte`` → E, ``AbsFeuchte`` →
   BL/BW, ``EnthalpieA`` → N/BM/BQ, ``TemperaturH`` → AN). Each cached value
   was produced by Excel from the cached input cells, so the port must
   reproduce it to ``rel=1e-9``. The constants make the tests run without
   ``.analysis`` (CI-safe).
2. **Live re-check**: when ``.analysis/dumps`` is present, re-read the same
   sheets at runtime and re-verify a 5-point sample (skipped otherwise).
3. **Pure unit tests**: monotonicity, anchors, algebraic inverses, dew-point
   consistency, wet-bulb sanity and the ``PsychrometricError`` domain rules.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from energytools.common.errors import PsychrometricError
from energytools.engine.native import (
    absolute_humidity,
    dew_point,
    dew_point_from_absolute_humidity,
    enthalpy_from_absolute_humidity,
    enthalpy_from_rel_humidity,
    relative_humidity,
    saturation_pressure_glueck,
    temperature_from_enthalpy,
    wet_bulb_temperature,
)

# ---------------------------------------------------------------------------
# Shared cached workbook constants
# ---------------------------------------------------------------------------

#: Total air pressure of the Klimadaten sheet — ``Klimadaten!F44`` (mbar).
P_KLIMADATEN = 948.225968475814
#: Total air pressure of the Berechnung LU template — ``Berechnung LU!N19``
#: (mbar, = ``Klimadaten!F44``).
P_LU = 948.225968475814

# ---------------------------------------------------------------------------
# Cache comparison constants — Klimadaten!Q5:Q65 = AbsFeuchte(M{n}, N{n}, F44)
# ---------------------------------------------------------------------------
# Each row: (row, T [°C] from M{n}, φ [decimal] from N{n}, cached x [g/kg] from Q{n}).

ABSFEUCHTE_KLIMADATEN = [
    (5, -25.0, 0.0, 0.0),
    (6, -24.0, 0.0, 0.0),
    (7, -23.0, 0.0, 0.0),
    (8, -22.0, 0.0, 0.0),
    (9, -21.0, 0.0, 0.0),
    (10, -20.0, 0.0, 0.0),
    (11, -19.0, 0.0, 0.0),
    (12, -18.0, 0.0, 0.0),
    (13, -17.0, 0.0, 0.0),
    (14, -16.0, 0.0, 0.0),
    (15, -15.0, 0.0, 0.0),
    (16, -14.0, 0.0, 0.0),
    (17, -13.0, 0.0, 0.0),
    (18, -12.0, 0.0, 0.0),
    (19, -11.0, 0.0, 0.0),
    (20, -10.0, 0.8816666666666667, 1.501516346575252),
    (21, -9.0, 0.8835555555555555, 1.6443161150095276),
    (22, -8.0, 0.84875, 1.7250087090245703),
    (23, -7.0, 0.8305882352941176, 1.8427124559848516),
    (24, -6.0, 0.7846666666666667, 1.899063744632537),
    (25, -5.0, 0.8068421052631579, 2.129588221769916),
    (26, -4.0, 0.7892857142857143, 2.270167880624591),
    (27, -3.0, 0.830703125, 2.6026589843261188),
    (28, -2.0, 0.8668333333333333, 2.9561836544515754),
    (29, -1.0, 0.8758375634517767, 3.2480380336969135),
    (30, 0.0, 0.8677108433734939, 3.49554885575434),
    (31, 1.0, 0.8396686746987951, 3.6380720602590477),
    (32, 2.0, 0.828005249343832, 3.855569564859213),
    (33, 3.0, 0.8207538802660754, 4.10518316732949),
    (34, 4.0, 0.8144444444444444, 4.373310291319655),
    (35, 5.0, 0.7811940298507463, 4.499803421613228),
    (36, 6.0, 0.8118705035971223, 5.016895900091342),
    (37, 7.0, 0.7690147783251231, 5.091548178378688),
    (38, 8.0, 0.7768452380952381, 5.510833399227258),
    (39, 9.0, 0.7694690265486726, 5.844490980424946),
    (40, 10.0, 0.7767610062893081, 6.315056628208842),
    (41, 11.0, 0.7757608695652174, 6.746744327431421),
    (42, 12.0, 0.7328660436137072, 6.810595211012464),
    (43, 13.0, 0.7693714285714286, 7.645338174169924),
    (44, 14.0, 0.7502116402116402, 7.960905180402722),
    (45, 15.0, 0.7438484848484849, 8.426811370048695),
    (46, 16.0, 0.7515384615384616, 9.08751007667435),
    (47, 17.0, 0.7313972602739726, 9.430311668588425),
    (48, 18.0, 0.6918305084745762, 9.502784356511844),
    (49, 19.0, 0.6673109243697479, 9.762800605394874),
    (50, 20.0, 0.5925, 9.216475765386784),
    (51, 21.0, 0.5826027397260274, 9.645893861910121),
    (52, 22.0, 0.5698507462686567, 10.036723173953218),
    (53, 23.0, 0.5582456140350878, 10.455194597031547),
    (54, 24.0, 0.5083495145631067, 10.106875028410924),
    (55, 25.0, 0.5043478260869565, 10.654876344186441),
    (56, 26.0, 0.47234042553191485, 10.588087791667846),
    (57, 27.0, 0.44275862068965516, 10.526445754832219),
    (58, 28.0, 0.4008333333333334, 10.096823845730837),
    (59, 29.0, 0.39642857142857146, 10.590957931484501),
    (60, 30.0, 0.385625, 10.918959306969693),
    (61, 31.0, 0.365, 10.943572231900754),
    (62, 32.0, 0.295, 9.33754639888188),
    (63, 33.0, 0.25, 8.358750343870948),
    (64, 34.0, 0.0, 0.0),
    (65, 35.0, 0.0, 0.0),
]

# ---------------------------------------------------------------------------
# Cache comparison constants — Berechnung LU interval rows (121/168/200/230/249)
# ---------------------------------------------------------------------------
# RelFeuchte via E{n} = MIN(100%, RelFeuchte(BR{n}, C{n}, $N$19)) — the MIN
# clamp is a no-op for these (all < 1), so the cached value is the raw
# RelFeuchte result. Rows with x = 0 (E121/E200/E249) verify the boundary.
# Each row: (address, T [°C] from BR{n}, x [g/kg] from C{n}, cached φ [decimal]).

RELFEUCHTE_BERECHNUNG_LU = [
    ("E121", 21.45945945945946, 0.0, 0.0),
    ("E168", 24.0, 10.036723173953218, 0.5048770905933516),
    ("E200", 24.0, 0.0, 0.0),
    ("E230", 24.0, 8.340541125484249, 0.4206830551960779),
    ("E249", 26.0, 0.0, 0.0),
]

# AbsFeuchte via BL{n} = AbsFeuchte(BJ{n}, BK{n}, $N$19).
# Each row: (address, T [°C] from BJ{n}, φ [decimal] from BK{n}, cached x [g/kg]).

ABSFEUCHTE_BL_BERECHNUNG_LU = [
    ("BL121", 21.27027027027027, 0.0, 0.0),
    ("BL168", 20.0, 0.6443939116511824, 10.03672317395322),
    ("BL200", 22.0, 0.011286920260116094, 0.195700066854932),
    ("BL230", 22.0, 0.47482160987801486, 8.340541125484247),
    ("BL249", 22.0, 0.012716069586535643, 0.2204883842791794),
]

# AbsFeuchte via BW{n} = BT{n} + I20/J20, where I20 = J20 = 0, so
# BW{n} = BT{n} = AbsFeuchte(BR{n}, BS{n}, $N$19).
# Each row: (address, T [°C] from BR{n}, φ [decimal] from BS{n}, cached x [g/kg]).

ABSFEUCHTE_BW_BERECHNUNG_LU = [
    ("BW168", 24.0, 0.5048770905933516, 10.036723173953218),
    ("BW200", 24.0, 0.01, 0.195700066854932),
    ("BW230", 24.0, 0.4206830551960779, 8.340541125484249),
    ("BW249", 26.0, 0.01, 0.2204883842791794),
]

# EnthalpieA via N{n} = EnthalpieA(L{n}, M{n}, p)·E35 + (1−E35)·EnthalpieA(BU{n}, BW{n}, p)
# with E35 = F35 = 1, so the cached value is exactly EnthalpieA(L{n}, M{n}, p).
# Each row: (address, T [°C] from L{n}, x [g/kg] from M{n}, cached h [kJ/kg]).

ENTHALPIEA_N_BERECHNUNG_LU = [
    ("N121", 12.167567567567566, 0.0, 12.240572972972972),
    ("N168", 22.0, 10.036723173953218, 47.65056940423954),
    ("N200", 10.7, 0.0, 10.764199999999999),
    ("N230", 21.2, 8.340541125484249, 42.52078189717149),
    ("N249", 29.15, 0.0, 29.3249),
]

# EnthalpieA via BM{n} = EnthalpieA(BJ{n}, BL{n}, $N$19).
# Each row: (address, T [°C] from BJ{n}, x [g/kg] from BL{n}, cached h [kJ/kg]).

ENTHALPIEA_BM_BERECHNUNG_LU = [
    ("BM121", 21.27027027027027, 0.0, 21.39789189189189),
    ("BM168", 20.0, 10.03672317395322, 45.601232794032434),
    ("BM200", 22.0, 0.195700066854932, 22.629571333980003),
    ("BM230", 22.0, 8.340541125484247, 43.33799262236621),
    ("BM249", 22.0, 0.2204883842791794, 22.6925961267975),
]

# EnthalpieA via BQ{n} = EnthalpieA(BN{n}, BP{n}, $N$19).
# Each row: (address, T [°C] from BN{n}, x [g/kg] from BP{n}, cached h [kJ/kg]).

ENTHALPIEA_BQ_BERECHNUNG_LU = [
    ("BQ121", 21.27027027027027, 0.0, 21.39789189189189),
    ("BQ168", 20.0, 10.03672317395322, 45.601232794032434),
    ("BQ200", 22.0, 0.0, 22.132),
    ("BQ230", 22.0, 8.340541125484249, 43.337992622366215),
    ("BQ249", 22.0, 0.0, 22.132),
]

# TemperaturH via AN{n} = TemperaturH(AP{n}, AO{n}).
# Each row: (address, h [kJ/kg] from AP{n}, x [g/kg] from AO{n}, cached T [°C]).

TEMPERATURH_BERECHNUNG_LU = [
    ("AN121", 21.39789189189189, 0.0, 21.27027027027027),
    ("AN168", 45.601232794032434, 10.036723173953218, 20.0),
    ("AN200", 22.629571333980003, 0.0, 22.494603711709743),
    ("AN230", 43.33799262236621, 8.340541125484249, 22.0),
    ("AN249", 22.6925961267975, 0.0, 22.557252611130718),
]


# ---------------------------------------------------------------------------
# Cache comparison tests (constants only — CI-safe, no .analysis dependency)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "t", "rh", "cached"),
    ABSFEUCHTE_KLIMADATEN,
    ids=[f"Q{row}" for row, *_ in ABSFEUCHTE_KLIMADATEN],
)
def test_absfeuchte_matches_klimadaten_cache(row: int, t: float, rh: float, cached: float) -> None:
    """``Klimadaten!Q{row} = AbsFeuchte(M, N, $F$44)`` against the cached value."""
    assert absolute_humidity(t, rh, P_KLIMADATEN) == pytest.approx(cached, rel=1e-9)


@pytest.mark.parametrize(
    ("address", "t", "x", "cached"),
    RELFEUCHTE_BERECHNUNG_LU,
    ids=[addr for addr, *_ in RELFEUCHTE_BERECHNUNG_LU],
)
def test_relfeuchte_matches_berechnung_lu_cache(
    address: str, t: float, x: float, cached: float
) -> None:
    """``Berechnung LU!{address}`` (VBA ``RelFeuchte``) against the cached value."""
    assert relative_humidity(t, x, P_LU) == pytest.approx(cached, rel=1e-9)


@pytest.mark.parametrize(
    ("address", "t", "rh", "cached"),
    ABSFEUCHTE_BL_BERECHNUNG_LU,
    ids=[addr for addr, *_ in ABSFEUCHTE_BL_BERECHNUNG_LU],
)
def test_absfeuchte_bl_matches_berechnung_lu_cache(
    address: str, t: float, rh: float, cached: float
) -> None:
    """``Berechnung LU!{address}`` (VBA ``AbsFeuchte``) against the cached value."""
    assert absolute_humidity(t, rh, P_LU) == pytest.approx(cached, rel=1e-9)


@pytest.mark.parametrize(
    ("address", "t", "rh", "cached"),
    ABSFEUCHTE_BW_BERECHNUNG_LU,
    ids=[addr for addr, *_ in ABSFEUCHTE_BW_BERECHNUNG_LU],
)
def test_absfeuchte_bw_matches_berechnung_lu_cache(
    address: str, t: float, rh: float, cached: float
) -> None:
    """``Berechnung LU!{address}`` (VBA ``AbsFeuchte`` via BT + I20/J20 = 0)."""
    assert absolute_humidity(t, rh, P_LU) == pytest.approx(cached, rel=1e-9)


@pytest.mark.parametrize(
    ("address", "t", "x", "cached"),
    ENTHALPIEA_N_BERECHNUNG_LU,
    ids=[addr for addr, *_ in ENTHALPIEA_N_BERECHNUNG_LU],
)
def test_enthalpiea_n_matches_berechnung_lu_cache(
    address: str, t: float, x: float, cached: float
) -> None:
    """``Berechnung LU!{address}`` (VBA ``EnthalpieA``, E35 = 1) against cache."""
    assert enthalpy_from_absolute_humidity(t, x, P_LU) == pytest.approx(cached, rel=1e-9)


@pytest.mark.parametrize(
    ("address", "t", "x", "cached"),
    ENTHALPIEA_BM_BERECHNUNG_LU,
    ids=[addr for addr, *_ in ENTHALPIEA_BM_BERECHNUNG_LU],
)
def test_enthalpiea_bm_matches_berechnung_lu_cache(
    address: str, t: float, x: float, cached: float
) -> None:
    """``Berechnung LU!{address}`` (VBA ``EnthalpieA``) against the cached value."""
    assert enthalpy_from_absolute_humidity(t, x, P_LU) == pytest.approx(cached, rel=1e-9)


@pytest.mark.parametrize(
    ("address", "t", "x", "cached"),
    ENTHALPIEA_BQ_BERECHNUNG_LU,
    ids=[addr for addr, *_ in ENTHALPIEA_BQ_BERECHNUNG_LU],
)
def test_enthalpiea_bq_matches_berechnung_lu_cache(
    address: str, t: float, x: float, cached: float
) -> None:
    """``Berechnung LU!{address}`` (VBA ``EnthalpieA``) against the cached value."""
    assert enthalpy_from_absolute_humidity(t, x, P_LU) == pytest.approx(cached, rel=1e-9)


@pytest.mark.parametrize(
    ("address", "h", "x", "cached"),
    TEMPERATURH_BERECHNUNG_LU,
    ids=[addr for addr, *_ in TEMPERATURH_BERECHNUNG_LU],
)
def test_temperaturh_matches_berechnung_lu_cache(
    address: str, h: float, x: float, cached: float
) -> None:
    """``Berechnung LU!{address}`` (VBA ``TemperaturH``) against the cached value."""
    assert temperature_from_enthalpy(h, x) == pytest.approx(cached, rel=1e-9)


# ---------------------------------------------------------------------------
# Live re-check against .analysis/dumps (skipped when the dumps are absent)
# ---------------------------------------------------------------------------

_DUMP_DIR = Path(__file__).resolve().parents[1] / ".analysis" / "dumps" / "gebaeude"
_HAS_DUMPS = (_DUMP_DIR / "sheet_62_Klimadaten.tsv").exists() and (
    _DUMP_DIR / "sheet_61_Berechnung LU.tsv"
).exists()


def _parse_tsv_values(path: Path) -> dict[str, float]:
    """Parse a workbook dump TSV (``地址\\t值`` or ``地址\\tF:…\\tR:…``) into cells.

    No third-party libraries: each line is split on tabs; a cell's cached value
    is the ``R:`` payload of a formula row or the plain value of a value row.
    Error payloads (``R:{"error": …}``) are dropped (not floatable).
    """
    cells: dict[str, float] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        value: str | None = None
        if len(parts) == 2:
            value = parts[1]
        elif len(parts) >= 3:
            for part in parts[1:]:
                if part.startswith("R:"):
                    value = part[2:]
                    break
        if value is None or value == "" or value.startswith("{"):
            continue
        try:
            cells[parts[0]] = float(value)
        except ValueError:
            continue
    return cells


@pytest.mark.skipif(not _HAS_DUMPS, reason=".analysis/dumps not present")
def test_live_recheck_against_dumps() -> None:
    """Re-read the dumps at runtime and re-verify a 5-point sample per sheet."""
    klima = _parse_tsv_values(_DUMP_DIR / "sheet_62_Klimadaten.tsv")
    ber = _parse_tsv_values(_DUMP_DIR / "sheet_61_Berechnung LU.tsv")

    f44 = klima["F44"]
    n19 = ber["N19"]
    assert f44 == pytest.approx(P_KLIMADATEN, rel=1e-12)
    assert n19 == pytest.approx(P_LU, rel=1e-12)

    # Klimadaten sample: rows 20, 30, 40, 50, 60 → AbsFeuchte(M, N, F44).
    for row in (20, 30, 40, 50, 60):
        t = klima[f"M{row}"]
        rh = klima[f"N{row}"]
        cached = klima[f"Q{row}"]
        assert absolute_humidity(t, rh, f44) == pytest.approx(cached, rel=1e-9)

    # Berechnung LU sample: E168 (RelFeuchte), BL230 (AbsFeuchte),
    # N168 (EnthalpieA), BW200 (AbsFeuchte), AN230 (TemperaturH).
    assert relative_humidity(ber["BR168"], ber["C168"], n19) == pytest.approx(ber["E168"], rel=1e-9)
    assert absolute_humidity(ber["BJ230"], ber["BK230"], n19) == pytest.approx(
        ber["BL230"], rel=1e-9
    )
    assert enthalpy_from_absolute_humidity(ber["L168"], ber["M168"], n19) == pytest.approx(
        ber["N168"], rel=1e-9
    )
    assert absolute_humidity(ber["BR200"], ber["BS200"], n19) == pytest.approx(
        ber["BW200"], rel=1e-9
    )
    assert temperature_from_enthalpy(ber["AP230"], ber["AO230"]) == pytest.approx(
        ber["AN230"], rel=1e-9
    )


# ---------------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------------


def test_saturation_pressure_monotonic_increasing() -> None:
    """The Glück polynomial is strictly increasing over −25…+35 °C."""
    temps = [t / 10.0 for t in range(-250, 351)]
    values = [saturation_pressure_glueck(t) for t in temps]
    assert all(b > a for a, b in itertools.pairwise(values))


def test_saturation_pressure_anchors() -> None:
    """Glück anchors: p_s(0) ≈ 6.1088 and p_s(20) ≈ 23.369 mbar (magnitude).

    The verbatim VBA selects the **ice branch** for ``T <= 0``, so at exactly
    0 °C the port returns 6.1070 mbar (the water branch would give 6.1088);
    both agree with the textbook's triple-point anchor (≈6.11 mbar) within
    0.03 %.
    """
    assert saturation_pressure_glueck(0.0) == pytest.approx(6.1088, abs=0.01)
    assert saturation_pressure_glueck(20.0) == pytest.approx(23.369, abs=0.01)
    # Verbatim VBA arithmetic (bit-exact port): ice branch at 0 °C.
    assert saturation_pressure_glueck(0.0) == pytest.approx(6.107000747756432, rel=1e-12)
    assert saturation_pressure_glueck(20.0) == pytest.approx(23.3673815296201, rel=1e-12)


def test_saturation_pressure_split_at_zero() -> None:
    """The ice/water split sits at T = 0 with the documented ≈0.03 % jump.

    The two Glück branches are nearly — but not exactly — continuous at 0 °C:
    the ice branch (selected for ``T <= 0``) gives 6.1070 mbar, the water
    branch 6.1088 mbar (textbook ch01 §1.2: "the jump is on the order of
    0.03 %"). The verbatim VBA keeps the piecewise split, so the port does too.
    """
    just_below = saturation_pressure_glueck(-1e-6)
    just_above = saturation_pressure_glueck(1e-6)
    assert just_below == pytest.approx(6.107000248008546, rel=1e-9)
    assert just_above == pytest.approx(6.108831864892487, rel=1e-9)
    jump = (just_above - just_below) / just_below
    assert 1e-4 <= jump <= 1e-3  # ≈ 0.03 % (3e-4) by design


def test_enthalpy_monotonic_in_humidity() -> None:
    """On the h–x diagram, at constant T the enthalpy grows with x."""
    t = 20.0
    xs = [0.0, 5.0, 10.0, 15.0, 20.0, 30.0]
    hs = [enthalpy_from_absolute_humidity(t, x, 1013.0) for x in xs]
    assert all(b > a for a, b in itertools.pairwise(hs))


def test_absolute_humidity_monotonic_in_relative_humidity() -> None:
    """At constant T and p the humidity ratio grows with φ."""
    t, p = 20.0, 1013.0
    xs = [absolute_humidity(t, rh, p) for rh in (0.0, 0.2, 0.4, 0.6, 0.8, 0.99)]
    assert all(b > a for a, b in itertools.pairwise(xs))


def test_relative_absolute_humidity_are_algebraic_inverses() -> None:
    """φ = RelFeuchte(x) inverts x = AbsFeuchte(φ) exactly (same p_s model)."""
    for t, x in ((20.0, 7.28), (0.0, 3.0), (-10.0, 1.5), (30.0, 20.0)):
        p = 1013.0
        rh = relative_humidity(t, x, p)
        assert absolute_humidity(t, rh, p) == pytest.approx(x, rel=1e-12)


def test_temperature_enthalpy_roundtrip() -> None:
    """TemperaturH inverts EnthalpieA: T(h(T, x), x) == T."""
    for t, x in ((20.0, 7.28), (0.0, 3.0), (-10.0, 1.5), (35.0, 20.0)):
        h = enthalpy_from_absolute_humidity(t, x, 1013.0)
        assert temperature_from_enthalpy(h, x) == pytest.approx(t, rel=1e-12)


def test_dew_point_inverse_consistency() -> None:
    """At the dew point the air is saturated: x(t_dp, 100 %) ≈ x(t, φ).

    The dew point inverts the power-law fit p_s = 2.8858·(T/100 + 1.098)^8.02,
    which deviates from the Glück polynomial the port uses elsewhere; the two
    models agree within ≈0.2 % above 0 °C and drift to ≈12 % below −10 °C, so
    the round trip is asserted with a matching tolerance (textbook ch01 §1.7).
    """
    for t, rh in ((20.0, 0.5), (10.0, 0.8), (0.0, 0.6), (30.0, 0.3)):
        p = 1013.0
        x = absolute_humidity(t, rh, p)
        t_dp = dew_point(t, rh, p)
        assert absolute_humidity(t_dp, 1.0, p) == pytest.approx(x, rel=0.15)
    # Tighter check in the range where the fit is accurate (T >= 10 °C).
    for t, rh in ((20.0, 0.5), (10.0, 0.8), (30.0, 0.3)):
        p = 1013.0
        x = absolute_humidity(t, rh, p)
        t_dp = dew_point(t, rh, p)
        assert absolute_humidity(t_dp, 1.0, p) == pytest.approx(x, rel=0.01)


def test_dew_point_saturated_air_equals_dry_bulb() -> None:
    """φ = 100 % ⇒ dew point ≈ dry-bulb temperature (0…30 °C)."""
    for t in (0.0, 10.0, 20.0, 30.0):
        assert dew_point(t, 1.0, 1013.0) == pytest.approx(t, abs=0.1)


def test_dew_point_from_absolute_humidity_consistency() -> None:
    """TaupunktA (x, p) agrees with TaupunktR at φ = 100 %."""
    for t in (0.0, 10.0, 20.0, 30.0):
        x = absolute_humidity(t, 1.0, 1013.0)
        assert dew_point_from_absolute_humidity(x, 1013.0) == pytest.approx(
            dew_point(t, 1.0, 1013.0), rel=1e-12
        )


def test_wet_bulb_relative_humidity_relations() -> None:
    """Feuchtkugel sanity: wet bulb ≤ dry bulb, saturated ≈ dry bulb."""
    # At 100 % rh the wet bulb equals the dry bulb (within the fit).
    assert wet_bulb_temperature(20.0, 100.0) == pytest.approx(20.0, abs=0.1)
    assert wet_bulb_temperature(20.0, 100.0) == pytest.approx(19.931, rel=1e-12)
    # Wet bulb never exceeds the dry bulb at 20 °C.
    for rh in (0.0, 25.0, 50.0, 75.0, 100.0):
        assert wet_bulb_temperature(20.0, rh) <= 20.0
    # Lower humidity ⇒ lower wet bulb.
    assert wet_bulb_temperature(20.0, 90.0) > wet_bulb_temperature(20.0, 10.0)
    # Below-zero branch: FK < 0 → FK·0.8 + 0.5.
    assert wet_bulb_temperature(-10.0, 50.0) == pytest.approx(-8.6032, rel=1e-12)
    assert wet_bulb_temperature(20.0, 50.0) == pytest.approx(14.031, rel=1e-12)


# ---------------------------------------------------------------------------
# Domain errors — the VBA "Fehler"/Excel-error cases become PsychrometricError
# ---------------------------------------------------------------------------


def test_saturation_pressure_nan_raises() -> None:
    with pytest.raises(PsychrometricError):
        saturation_pressure_glueck(float("nan"))


def test_absolute_humidity_domain_errors() -> None:
    for t, rh, p in (
        (20.0, 1.5, 1013.0),  # rh > 1 (percent passed by mistake)
        (20.0, -0.1, 1013.0),  # rh < 0
        (20.0, 0.5, 0.0),  # p == 0
        (20.0, 0.5, -10.0),  # p < 0
        (20.0, 1.0, 5.0),  # p - rh*ps <= 0 (supersaturated)
    ):
        with pytest.raises(PsychrometricError):
            absolute_humidity(t, rh, p)


def test_relative_humidity_domain_errors() -> None:
    for t, x, p in ((20.0, -1.0, 1013.0), (20.0, 5.0, 0.0)):
        with pytest.raises(PsychrometricError):
            relative_humidity(t, x, p)


def test_enthalpy_domain_errors() -> None:
    with pytest.raises(PsychrometricError):
        enthalpy_from_absolute_humidity(20.0, -1.0, 1013.0)
    with pytest.raises(PsychrometricError):
        enthalpy_from_rel_humidity(20.0, 1.5, 1013.0)


def test_dew_point_domain_errors() -> None:
    with pytest.raises(PsychrometricError):
        dew_point(20.0, 0.0, 1013.0)  # x == 0 → VBA division by zero
    with pytest.raises(PsychrometricError):
        dew_point_from_absolute_humidity(0.0, 1013.0)
    with pytest.raises(PsychrometricError):
        dew_point_from_absolute_humidity(5.0, 0.0)
    with pytest.raises(PsychrometricError):
        dew_point_from_absolute_humidity(-1.0, 1013.0)


def test_temperature_from_enthalpy_domain_errors() -> None:
    with pytest.raises(PsychrometricError):
        temperature_from_enthalpy(20.0, -1.0)


def test_wet_bulb_domain_errors() -> None:
    for rh in (-1.0, 101.0):
        with pytest.raises(PsychrometricError):
            wet_bulb_temperature(20.0, rh)


def test_error_details_carry_function_and_args() -> None:
    """PsychrometricError carries structured details for the API layer."""
    with pytest.raises(PsychrometricError) as exc_info:
        absolute_humidity(20.0, 1.5, 1013.0)
    details = exc_info.value.details
    assert details is not None
    assert details["function"] == "AbsFeuchte"
    assert details["args"] == {"t": 20.0, "rh": 1.5, "p": 1013.0}
