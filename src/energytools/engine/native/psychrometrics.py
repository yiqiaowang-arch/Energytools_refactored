"""Moist-air psychrometric functions — pure-Python port of the workbook UDFs.

This module is the ``native`` port of ``FeuchteLuft_Formeln.bas`` (the
``FeuchteLuft_Formeln`` module of ``2024_Gebaeude-Tool_dfi_V221.xlsm``), i.e.
the psychrometric layer of the target-state API reference
``docs/architecture+api-reference/04-gebaeude-engine.md`` §2 (there named
``energytools.gebaeude.physics``). Every function mirrors one VBA ``Public
Function`` verbatim — Glück saturation-pressure polynomials (ice/water
branches), the module constants (``cpl = 1.006``, ``cpw = 1.86``,
``r0 = 2501.6``, ``611``, ``622``), and the empirical formulas — and is
verified against the workbook's cached values (``.analysis/dumps``) in
``tests/test_psychrometrics.py``.

Unit conventions (authoritative, from the VBA source comments and the
textbook ``docs/textbook/ch01-moist-air-physics.md`` §1.3/§1.11):

- ``t`` temperature in °C;
- ``x`` humidity ratio in **g/kg**;
- ``p`` total air pressure in **mbar**;
- ``h`` enthalpy in **kJ/kg**;
- ``rh`` relative humidity as a **decimal fraction 0–1** for every function
  except :func:`wet_bulb_temperature`, which works in **% (0–100)** exactly
  like the VBA ``Feuchtkugel`` (its one percent/decimal inconsistency is kept
  as-is on purpose — see the textbook §1.8).

The workbook itself passes φ as a decimal (e.g. ``Klimadaten!Q20 =
AbsFeuchte(M20, N20, $F$44)`` with ``N20 = 0.88167``) and the VBA formulas are
only self-consistent for decimal φ (textbook §1.9), so the decimal convention
is the port's default here — a deliberate deviation from the design document
§2.3–§2.7, which had specified % for the not-yet-built API.

Domain errors (the cases in which the VBA returned the string ``"Fehler"``
or an Excel error) raise :class:`energytools.common.errors.PsychrometricError`
with structured ``details``; they are never returned as values.
"""

from __future__ import annotations

import math

from energytools.common.errors import PsychrometricError

__all__ = [
    "absolute_humidity",
    "dew_point",
    "dew_point_from_absolute_humidity",
    "enthalpy_from_absolute_humidity",
    "enthalpy_from_rel_humidity",
    "relative_humidity",
    "saturation_pressure_glueck",
    "temperature_from_enthalpy",
    "wet_bulb_temperature",
]

# -- Module constants (verbatim from FeuchteLuft_Formeln.bas) ---------------
#: Specific heat of dry air in kJ/(kg·K) — VBA ``cpl``.
CP_AIR = 1.006
#: Specific heat of water vapour in kJ/(kg·K) — VBA ``cpw``.
CP_WATER_VAPOUR = 1.86
#: Specific heat of liquid water in kJ/(kg·K) — workbook ``cw`` (``Berechnung LU!N22``),
#: not used by the psychrometric UDFs (doc part 04 §2.1).
CP_WATER = 4.19
#: Latent heat of vaporisation of water at 0 °C in kJ/kg — VBA ``r0``.
HEAT_OF_VAPORIZATION = 2501.6
#: Latent heat of vaporisation at 100 °C in kJ/kg — workbook ``r100`` (``Berechnung LU!N25``),
#: not used by the psychrometric UDFs (doc part 04 §2.1).
HEAT_OF_VAPORIZATION_100 = 2256.0
#: Air density in kg/m³ — workbook ``ρ`` (``Berechnung LU!N23``), not used by the
#: psychrometric UDFs (doc part 04 §2.1).
AIR_DENSITY = 1.15
#: Molar-mass ratio water/dry air × 1000 (0.622 × 1000) — the g/kg scale factor.
MOLAR_MASS_RATIO = 622
#: Triple-point pressure of water in Pa, the reference of the Glück polynomial — VBA ``611``.
PS_0 = 611
#: Dew-point power-law fit constants (VBA ``TaupunktR``): p_s(T) = DEW_POINT_P ·
#: (T/100 + DEW_POINT_K) ** DEW_POINT_N.
DEW_POINT_P = 2.8858
DEW_POINT_N = 8.02
DEW_POINT_K = 1.098

#: Glück polynomial coefficients over ice (T <= 0), a0..a4 (VBA ``Saettigungsdruck``).
_GLUECK_ICE = (
    -4.909965e-4,
    8.183197e-2,
    -5.552967e-4,
    -2.228376e-5,
    -6.211808e-7,
)
#: Glück polynomial coefficients over water (T > 0), a0..a4 (VBA ``Saettigungsdruck``).
_GLUECK_WATER = (
    -1.91275e-4,
    7.258e-2,
    -2.939e-4,
    9.841e-7,
    -1.92e-9,
)


def _saturation_pressure_glueck(t: float) -> float:
    """Saturation vapour pressure after Glück in mbar (internal helper).

    Mirrors the piecewise polynomial inlined in ``Saettigungsdruck``,
    ``AbsFeuchte``, ``RelFeuchte`` and ``EnthalpieR`` of
    ``FeuchteLuft_Formeln.bas``: ice branch for ``t <= 0``, water branch for
    ``t > 0``. The VBA ``Else`` branch (returning ``"Fehler"``) is reachable
    only for non-comparable inputs such as NaN and becomes an exception here.
    """
    if t <= 0:
        a0, a1, a2, a3, a4 = _GLUECK_ICE
        poly = a0 + a1 * t + a2 * t**2 + a3 * t**3 + a4 * t**4
    elif t > 0:
        a0, a1, a2, a3, a4 = _GLUECK_WATER
        poly = a0 + a1 * t + a2 * t**2 + a3 * t**3 + a4 * t**4
    else:  # NaN (or other non-comparable): the VBA "Fehler" branch
        raise PsychrometricError(
            "saturation_pressure_glueck: temperature must be a finite number",
            details={"function": "Saettigungsdruck", "args": {"t": t}},
        )
    return PS_0 * math.exp(poly) / 100


def saturation_pressure_glueck(t: float) -> float:
    """Saturation vapour pressure after Glück in mbar (VBA ``Saettigungsdruck``).

    p_s(T) = 611 / 100 · exp(a0 + a1·T + a2·T² + a3·T³ + a4·T⁴) [mbar], with the
    ice-branch coefficients for ``t <= 0`` and the water-branch coefficients
    for ``t > 0`` (textbook ch01 §1.2). The piecewise split at 0 °C and every
    coefficient are verbatim from ``FeuchteLuft_Formeln.bas``.

    Args:
        t: Temperature in °C.

    Returns:
        Saturation vapour pressure in mbar.

    Raises:
        PsychrometricError: if ``t`` is NaN (the VBA ``"Fehler"`` case).

    Example:
        >>> saturation_pressure_glueck(20.0)
        23.3673...
    """
    return _saturation_pressure_glueck(t)


def absolute_humidity(t: float, rh: float, p: float) -> float:
    """Absolute humidity in g/kg from T/φ/p (VBA ``AbsFeuchte``).

    x = (φ · 622 · p_s(T)) / (p − φ · p_s(T)) [g/kg], derived from Dalton's law
    with the molar-mass ratio 0.622 (textbook ch01 §1.3). ``rh`` is a decimal
    fraction 0–1, matching the workbook call sites (e.g. ``Klimadaten!Q20 =
    AbsFeuchte(M20, N20, $F$44)`` with φ = 0.88167).

    Args:
        t: Temperature in °C.
        rh: Relative humidity as a decimal fraction in [0, 1].
        p: Total air pressure in mbar (> 0).

    Returns:
        Absolute humidity in g/kg.

    Raises:
        PsychrometricError: if ``rh`` is outside [0, 1], ``p <= 0``, or the
            denominator ``p − rh·p_s`` is non-positive (saturated or
            supersaturated state) — the VBA ``"Fehler"``/error cases.

    Example:
        >>> absolute_humidity(20.0, 0.5, 1013.0)
        7.2577...
    """
    if not 0 <= rh <= 1:
        raise PsychrometricError(
            "absolute_humidity: relative humidity must be a decimal fraction in [0, 1]",
            details={"function": "AbsFeuchte", "args": {"t": t, "rh": rh, "p": p}},
        )
    if p <= 0:
        raise PsychrometricError(
            "absolute_humidity: pressure must be positive",
            details={"function": "AbsFeuchte", "args": {"t": t, "rh": rh, "p": p}},
        )
    ps = _saturation_pressure_glueck(t)
    if p - rh * ps <= 0:
        raise PsychrometricError(
            "absolute_humidity: p - rh*ps <= 0 (saturated or supersaturated state)",
            details={"function": "AbsFeuchte", "args": {"t": t, "rh": rh, "p": p}},
        )
    return (rh * MOLAR_MASS_RATIO * ps) / (p - rh * ps)


def relative_humidity(t: float, x: float, p: float) -> float:
    """Relative humidity as a decimal fraction from T/x/p (VBA ``RelFeuchte``).

    φ = (x · p) / (p_s(T) · (622 + x)) [–], the algebraic inverse of
    ``AbsFeuchte`` (textbook ch01 §1.6). Returns a decimal fraction; the
    workbook combines the call sites with ``MIN(100%, …)``/``MIN(1, …)``
    saturation clamps, which this function does **not** apply (VBA-verbatim:
    supersaturated states return φ > 1).

    Args:
        t: Temperature in °C.
        x: Absolute humidity in g/kg (≥ 0).
        p: Total air pressure in mbar (> 0).

    Returns:
        Relative humidity as a decimal fraction in [0, …] (may exceed 1).

    Raises:
        PsychrometricError: if ``x < 0`` or ``p <= 0``.

    Example:
        >>> relative_humidity(20.0, 7.26, 1013.0)
        0.5001...
    """
    if x < 0:
        raise PsychrometricError(
            "relative_humidity: absolute humidity must be >= 0",
            details={"function": "RelFeuchte", "args": {"t": t, "x": x, "p": p}},
        )
    if p <= 0:
        raise PsychrometricError(
            "relative_humidity: pressure must be positive",
            details={"function": "RelFeuchte", "args": {"t": t, "x": x, "p": p}},
        )
    ps = _saturation_pressure_glueck(t)
    return (x * p) / (ps * (MOLAR_MASS_RATIO + x))


def enthalpy_from_rel_humidity(t: float, rh: float, p: float) -> float:
    """Enthalpy in kJ/kg from T/φ/p (VBA ``EnthalpieR``).

    Computes x in kg/kg first — x = 0.622 · (φ·p_s) / (p − φ·p_s) — then
    h = cpl·T + x·(r0 + cpw·T) (textbook ch01 §1.9). ``rh`` is a decimal
    fraction 0–1: the VBA ``rF*100``/``p*100`` double conversion cancels and is
    only self-consistent for decimal ``rF``. **Reference-only** — no stored
    formula calls ``EnthalpieR`` (dead code), ported for completeness.

    Args:
        t: Temperature in °C.
        rh: Relative humidity as a decimal fraction in [0, 1].
        p: Total air pressure in mbar (> 0).

    Returns:
        Enthalpy in kJ/kg.

    Raises:
        PsychrometricError: same domain rules as :func:`absolute_humidity`.

    Example:
        >>> enthalpy_from_rel_humidity(20.0, 0.5, 1013.0)
        38.5...
    """
    x_kg = absolute_humidity(t, rh, p) / 1000.0
    return CP_AIR * t + x_kg * (HEAT_OF_VAPORIZATION + CP_WATER_VAPOUR * t)


def enthalpy_from_absolute_humidity(t: float, x: float, p: float) -> float:
    """Enthalpy in kJ/kg from T/x/p (VBA ``EnthalpieA``).

    h = cpl·T + (x/1000)·(r0 + cpw·T) [kJ/kg] with the 0 °C reference state
    (textbook ch01 §1.4). ``p`` is accepted for signature symmetry with the VBA
    but is **unused** by the formula.

    Args:
        t: Temperature in °C.
        x: Absolute humidity in g/kg (≥ 0).
        p: Total air pressure in mbar (accepted, unused).

    Returns:
        Enthalpy in kJ/kg.

    Raises:
        PsychrometricError: if ``x < 0``.

    Example:
        >>> enthalpy_from_absolute_humidity(20.0, 7.28, 1013.0)
        38.6024...
    """
    if x < 0:
        raise PsychrometricError(
            "enthalpy_from_absolute_humidity: absolute humidity must be >= 0",
            details={"function": "EnthalpieA", "args": {"t": t, "x": x, "p": p}},
        )
    return CP_AIR * t + x / 1000.0 * (HEAT_OF_VAPORIZATION + CP_WATER_VAPOUR * t)


def dew_point(t: float, rh: float, p: float) -> float:
    """Dew-point temperature in °C from T/φ/p (VBA ``TaupunktR``).

    Computes x = ``AbsFeuchte(T, φ, p)``, the dew-point vapour pressure
    p_st = p / (622/x + 1) [mbar], then inverts the power-law fit
    T_d = ((p_st / 2.8858)^(1/8.02) − 1.098) · 100 (textbook ch01 §1.7).
    **Reference-only** — no stored formula calls ``TaupunktR`` (dead code);
    the power-law fit deviates from the Glück polynomial (≈6 % at 20 °C).

    Args:
        t: Temperature in °C.
        rh: Relative humidity as a decimal fraction in [0, 1].
        p: Total air pressure in mbar (> 0).

    Returns:
        Dew-point temperature in °C.

    Raises:
        PsychrometricError: domain rules of :func:`absolute_humidity`; also
            when the resulting humidity ratio is 0 (the VBA division-by-zero).

    Example:
        >>> dew_point(20.0, 0.5, 1013.0)
        9.2488...
    """
    x = absolute_humidity(t, rh, p)
    if x <= 0:
        raise PsychrometricError(
            "dew_point: humidity ratio must be > 0",
            details={"function": "TaupunktR", "args": {"t": t, "rh": rh, "p": p}},
        )
    pst = p / (0.622 * 1000 / x + 1)
    return ((pst / DEW_POINT_P) ** (1 / DEW_POINT_N) - DEW_POINT_K) * 100


def dew_point_from_absolute_humidity(x: float, p: float) -> float:
    """Dew-point temperature in °C from x/p (VBA ``TaupunktA``).

    p_st = p / (622/x + 1); T_d = ((p_st / 2.8858)^(1/8.02) − 1.098) · 100.
    **Reference-only**: ``TaupunktA`` is commented out in the VBA module, but
    ``Berechnung LU!AQ{n}`` still calls it → cached ``#NAME?`` cascading to
    ``AS{n}`` ``#VALUE!``; the AQ/AS chain takes part in no result (textbook
    ch01 §1.7/§1.10). Ported for completeness.

    Args:
        x: Absolute humidity in g/kg (> 0).
        p: Total air pressure in mbar (> 0).

    Returns:
        Dew-point temperature in °C.

    Raises:
        PsychrometricError: if ``x <= 0`` or ``p <= 0``.

    Example:
        >>> dew_point_from_absolute_humidity(7.28, 1013.0)
        9.29...
    """
    if x <= 0:
        raise PsychrometricError(
            "dew_point_from_absolute_humidity: humidity ratio must be > 0",
            details={"function": "TaupunktA", "args": {"x": x, "p": p}},
        )
    if p <= 0:
        raise PsychrometricError(
            "dew_point_from_absolute_humidity: pressure must be positive",
            details={"function": "TaupunktA", "args": {"x": x, "p": p}},
        )
    pst = p / (0.622 * 1000 / x + 1)
    return ((pst / DEW_POINT_P) ** (1 / DEW_POINT_N) - DEW_POINT_K) * 100


def temperature_from_enthalpy(h: float, x: float) -> float:
    """Temperature in °C from enthalpy and humidity ratio (VBA ``TemperaturH``).

    The algebraic inverse of :func:`enthalpy_from_absolute_humidity`:
    T = (h − (x/1000)·r0) / (cpl + (x/1000)·cpw) (textbook ch01 §1.5).

    Args:
        h: Enthalpy in kJ/kg.
        x: Absolute humidity in g/kg (≥ 0).

    Returns:
        Temperature in °C.

    Raises:
        PsychrometricError: if ``x < 0`` or the denominator is zero.

    Example:
        >>> temperature_from_enthalpy(38.60, 7.28)
        20.0...
    """
    if x < 0:
        raise PsychrometricError(
            "temperature_from_enthalpy: absolute humidity must be >= 0",
            details={"function": "TemperaturH", "args": {"h": h, "x": x}},
        )
    x_kg = x / 1000.0
    denominator = CP_AIR + CP_WATER_VAPOUR * x_kg
    if denominator == 0:
        raise PsychrometricError(
            "temperature_from_enthalpy: denominator cpl + cpw*x is zero",
            details={"function": "TemperaturH", "args": {"h": h, "x": x}},
        )
    return (h - x_kg * HEAT_OF_VAPORIZATION) / denominator


def wet_bulb_temperature(t: float, rh: float) -> float:
    """Empirical wet-bulb temperature in °C (VBA ``Feuchtkugel``).

    FK = −5.809 + 0.058·rh[%] + 0.697·t + 0.003·rh[%]·t; below 0 °C corrected
    to FK·0.8 + 0.5 (ice-surface wet-bulb correction). **Unit note:** this
    function works in **percent** (0–100) exactly like the VBA ``Feuchtkugel``
    — the module's one percent/decimal inconsistency, kept as-is (textbook ch01
    §1.8). **Reference-only** — no stored formula calls it (dead code).

    Args:
        t: Dry-bulb temperature in °C.
        rh: Relative humidity in % (0–100).

    Returns:
        Wet-bulb temperature in °C.

    Raises:
        PsychrometricError: if ``rh`` is outside [0, 100].

    Example:
        >>> wet_bulb_temperature(20.0, 50.0)
        14.031
    """
    if not 0 <= rh <= 100:
        raise PsychrometricError(
            "wet_bulb_temperature: relative humidity must be in % within [0, 100]",
            details={"function": "Feuchtkugel", "args": {"t": t, "rh": rh}},
        )
    fk = -5.809 + 0.058 * rh + 0.697 * t + 0.003 * rh * t
    if fk < 0:
        return fk * 0.8 + 0.5
    return fk
