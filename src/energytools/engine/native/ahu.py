"""AHU temperature-bin method — pure-Python port of the ``Berechnung LU`` engine.

This module ports the physical engine of the workbook sheet ``Berechnung LU``
(``2024_Gebaeude-Tool_dfi_V221.xlsm``) — the year-round psychrometric
calculation of **one** air-handling unit (AHU) with the **temperature-bin
method**. It is the native companion of
:mod:`energytools.engine.native.psychrometrics` (the port of
``FeuchteLuft_Formeln.bas``) and reuses its functions verbatim.

Authoritative documentation: ``docs/textbook/ch04-ahu-temperature-bin-method.md``
(formulas 1–10), ``docs/textbook/analysis_Berechnung_LU.md`` (column-by-column
analysis with the worked example row 168), and the cached-value dump
``.analysis/dumps/gebaeude/sheet_61_Berechnung LU.tsv`` (the oracle used by
``tests/test_ahu.py``).

Method
------
For each outdoor-temperature bin ``t_A = −25…+35 °C`` (61 bins, 1 K step,
``Klimadaten!O5:O65``) the engine computes the annual operating hours

    B_k = O_{k+30} / 8760 · t_VL,V            [h/a]          (Formula 1)

and then walks the state chain (Formula 2–7): outdoor air (AUL, moisture
content ``x_A = Klimadaten!Q``) → frost-protection preheating → WRG heat
recovery (fixed or bypass-modulated efficiency) → mixed air MIL (fresh-air
ratio E34/E35) → cooling coil with the linear cooling curve (A/C/D1/D2) →
case determination Fall 1–4 → supply-air setpoint/IST state → room/exhaust-air
state. The per-bin treatment loads (Formula 8, enthalpy differences
``BZ…CD``) are converted into annual energies (Formula 8, ``CE…CM/CT`` in
MWh) and aggregated into the annual result rows 254–260 (Formula 9). The fan
model (Formula 10) applies the affinity law ``P ∝ V^2.5`` over the staged air
volumes with the motor-efficiency lookup.

Units (all consistent with the psychrometrics module and the workbook):
temperature °C, humidity ratio x g/kg, relative humidity φ decimal 0–1,
pressure p mbar, enthalpy h kJ/kg, air volume m³/h, power kW, energy MWh
(per bin) and kWh (annual), water L/a.

Key workbook conventions reproduced faithfully (see ch04 §4.14):
- the energy sums start at row 122 (t_A = −24 °C), excluding the t_A = −25 °C
  bin from the annual sums (the bin has 0 hours in all golden cases);
- the heating-power maximum ``CC183`` starts at row 133 (t_A = −13 °C);
- the case detector ``AW`` and the cooling enthalpy ``BZ`` compare with the
  S/Q/R branch when ``E36 = C36`` (``"Temperatur"``), while the state columns
  and the dehumidification/heating columns use the W/X branch when
  ``E36 != D36`` (D36 empty) — a deliberate workbook asymmetry;
- ``MIN()`` with a single argument (column T) is a no-op;
- the density ρ = 1.15 kg/m³ and the mass flow are year-round constants.

Cell origins of the major groups: input rows 6/11–55 (column E = IST),
``Berechnung LU!B121:DC181`` (bin block), rows 182/183 (sums/maxima), rows
254–260 (annual results), rows 86–91 (temperature curves), rows 100–115
(efficiency classes, filter/frost-protection), ``Klimadaten!O5:O65/Q5:Q65/F44``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from energytools.engine.native.psychrometrics import (
    absolute_humidity,
    enthalpy_from_absolute_humidity,
    relative_humidity,
    temperature_from_enthalpy,
)

__all__ = [
    "AhuAnnualResult",
    "AhuBinResult",
    "AhuInput",
    "FanModelResult",
    "compute_ahu_annual",
    "compute_ahu_bins",
    "compute_bin_hours",
    "compute_fan_model",
]

# ---------------------------------------------------------------------------
# Module constants (verbatim from the workbook "Grundlagen" block, M17:O25)
# ---------------------------------------------------------------------------

#: Specific heat of dry air in kJ/(kg·K) — ``Berechnung LU!N20`` (cpl).
CP_AIR = 1.006
#: Specific heat of water vapour in kJ/(kg·K) — ``N21`` (cpw).
CP_WATER_VAPOUR = 1.86
#: Specific heat of liquid water in kJ/(kg·K) — ``N22`` (cw).
CP_WATER = 4.19
#: Air density in kg/m³ — ``N23`` (ρ).
AIR_DENSITY = 1.15
#: Latent heat of vaporisation at 0 °C in kJ/kg — ``N24`` (r0).
HEAT_OF_VAPORIZATION = 2501.6
#: Latent heat of vaporisation at 100 °C in kJ/kg — ``N25`` (r100).
HEAT_OF_VAPORIZATION_100 = 2256.0
#: Quellluft exhaust-air surcharge in K — ``N18``.
QUELLLUFT_DELTA_T = 2.0

#: Hours per year (8760).
HOURS_PER_YEAR = 8760.0
#: Seconds per hour.
SECONDS_PER_HOUR = 3600.0
#: kJ per MWh (1 MWh = 3.6e6 kJ).
KJ_PER_MWH = 3.6e6

#: Number of temperature bins (−25…+35 °C, 1 K steps).
N_BINS = 61
#: Lowest bin temperature in °C.
T_MIN_BIN = -25.0

#: Label strings of the workbook (column S, rows 10–24).
_LBL_QUELLLUFT = "Quellluft"
_LBL_KEINE = "keine"
_LBL_ADIABAT = "Adiabatisch Bef."
_LBL_NEIN = "nein"
_LBL_JA = "ja"

#: Motor efficiency classes (rows 11–16 of the efficiency table): class label →
#: (η for power bands ≤1.1, 1.1–2.2, 2.2–11, 11–110, >110 kW).
MOTOR_EFFICIENCY_CLASSES: dict[str, tuple[float, float, float, float, float]] = {
    "IE5 - gefaked": (1.0, 1.0, 1.0, 1.0, 1.0),
    "IE4 (> 2016)": (0.872, 0.895, 0.933, 0.963, 0.967),
    "IE3 (< 2016)": (0.85, 0.87, 0.9, 0.94, 0.96),
    "IE2 (< 2012)": (0.82, 0.84, 0.88, 0.93, 0.95),
    "IE1 (< 2008)": (0.73, 0.78, 0.84, 0.91, 0.94),
    "Eff3 (<1999)": (0.69, 0.74, 0.81, 0.9, 0.93),
}
#: Power-band boundaries in kW (N10:R10).
_MOTOR_BANDS = (1.1, 2.2, 11.0, 110.0)

#: Full-load hours for the example usage "Einzel-, Gruppenbüro" from the Std
#: table (``Std!Q10:V10``): (volumenstrom, elektrisch) per regulation mode —
#: einstufig / zweistufig / stufenlos. Used only as a fallback default for
#: ``AhuInput.full_load_hours_electricity`` when the caller does not supply it
#: (see ch03 — the Std lookup is a separate module in the port).
STD_FULL_LOAD_HOURS: dict[str, tuple[float, float]] = {
    "einstufig": (3900.0, 3900.0),
    "zweistufig": (3290.0, 2740.0),
    "stufenlos": (2160.0, 1780.0),
}


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AhuInput:
    """All inputs of the AHU temperature-bin calculation.

    The fields mirror the IST input block of ``Berechnung LU`` (row 6 +
    column E of rows 11–55) plus the climate data (``Klimadaten``) and the
    temperature curves / efficiency constants (rows 86–115). Defaults match
    the example system LA01 (Zürich-MeteoSchweiz). All values are in SI units
    as documented in the module docstring; strings keep the workbook's German
    labels verbatim (``"einstufig"``, ``"Temperatur"``, ``"ja"``, …).
    """

    # -- system (Berechnung LU row 6 / Lüftung template row 32) -------------
    system_name: str = "LA01"
    usage: str = "Einzel-, Gruppenbüro"
    volume_flow: float = 8578.57142857143  #: C6/E7 [m³/h] (Rechenwert)
    sfp: float = 0.8  #: F6 [W/(m³/h)]
    fan_power_total: float = 6.862857142857144  #: G6 [kW]
    regulation: str = "einstufig"  #: I6 — einstufig / zweistufig / stufenlos
    full_load_hours: float = 3900.0  #: K68 [h/a] (air-volume basis, Std lookup)
    full_load_hours_electricity: float | None = None  #: K69 [h/a], default = K68
    wrg_efficiency: float = 0.8  #: K6% = E28 [–]
    t_supply_summer: float = 20.0  #: L6 [°C] (Kühlfall)
    t_supply_winter: float = 21.0  #: M6 [°C] (Heizfall)
    rh_supply_summer: float = 0.0  #: N6 [%]
    rh_supply_winter: float = 0.0  #: O6 [%]

    # -- climate (Klimadaten) ------------------------------------------------
    pressure: float = 948.225968475814  #: N19 = Klimadaten!F44 [mbar]
    bin_hours: tuple[float, ...] = field(
        default_factory=lambda: (0.0,) * N_BINS
    )  #: 61 × [h/a] (Klimadaten!O5:O65, t = −25…+35)
    bin_humidity_ratio: tuple[float, ...] = field(
        default_factory=lambda: (0.0,) * N_BINS
    )  #: 61 × x_A [g/kg] (Klimadaten!Q5:Q65)

    # -- IST block (column E, rows 11–55) ------------------------------------
    air_supply_type: str = "Mischluft"  #: E13 (alternative "Quellluft")
    fan_power_zul_stage1: float | None = None  #: E16 [kW], default = G6/2
    fan_power_abl_stage1: float | None = None  #: E21 [kW], default = E16
    motor_class: str = "IE5 - gefaked"  #: E17
    motor_class_abl: str | None = None  #: E22, default = E17
    summer_start_temp: float = 0.0  #: E26 [°C] (Sommerbetrieb ab t_A)
    summer_dv: float = 0.0  #: E27 [m³/h] (Volumenstromerhöhung)
    moisture_recovery: float = 0.0  #: E29 [–] (Feuchte-WRG Faktor)
    bypass: bool = True  #: E30 == "ja" (Bypass für Regulierung KRG/WRG)
    krg: bool = True  #: E31 == "ja" (Kälterückgewinnung)
    frost_protection: str = "off"  #: E32 — "off" | "elektrisch (ein/aus)" | "elektrisch (variabel)"
    frost_threshold: float = 0.0  #: E33 [°C] (Grenztemperatur Vereisungsschutz)
    fresh_air_min: float = 1.0  #: E34 [–] (Frischluftanteil minimal)
    fresh_air_max: float = 1.0  #: E35 [–] (Frischluftanteil maximal)
    control_reference: str = "Temperatur"  #: E36 (Umluftregulierung anhand von)
    enthalpy_control: bool = False  #: E36 == D36 (True → R/Q branch; example: False)
    case_detector_s_based: bool = True  #: E36 == C36 (True → S branch in AW/BZ; example: True)
    heating_coil: bool = True  #: E39 == "ja"
    heating_design_temp: float = -13.0  #: E40 [°C]
    cooling_coil: bool = True  #: E42 == "ja"
    cooling_design_temp: float = 35.0  #: E43 [°C]
    coil_vl: float = 6.0  #: E45 [°C] (LK-Register Vorlauf)
    coil_rl: float = 12.0  #: E46 [°C] (LK-Register Rücklauf)
    dehumidification: bool = True  #: E47 == "ja"
    rh_max: float = 1.0  #: E48 [–] (max. zulässige r.F. Sommer)
    humidification_type: str = "Adiabatisch Bef."  #: E49 ("keine"/"Adiabatisch Bef."/sonst = Dampf)
    rh_min: float = 0.0  #: E50 [–] (min. zulässige r.F. Winter)
    chilled_water_temp: float = 10.0  #: E51 [°C] (Kaltwassertemperatur)
    room_moisture_load: float = 0.0  #: E52 → I20 [g/kg Zuluft-Erhöhung]
    control_mode: str = "Benutzerdefiniert"  #: E54 (Regelungsart Volumenstrom)

    # -- operating schedule (rows 56–70) -------------------------------------
    weekly_hours: tuple[float, float, float] = (50.0, 15.0, 15.0)  #: I58..I60 [h/week]
    weekly_hours_total: float = 80.0  #: L61 [h/week]
    #: Summer air volume P70 [m³/h] for the dV branch (default = K70).
    summer_volume_flow: float | None = None

    # -- temperature curves (rows 86–91, IST) --------------------------------
    curve_ta: tuple[float, float, float, float] = (-15.0, 22.0, 24.0, 30.0)  #: B88..B91
    curve_t_zul: tuple[float, float, float, float] | None = None  #: C88..C91 (default from M6/L6)
    curve_t_raum: tuple[float, float, float, float] = (22.0, 24.0, 25.0, 25.0)  #: D88..D91

    def __post_init__(self) -> None:
        if len(self.bin_hours) != N_BINS or len(self.bin_humidity_ratio) != N_BINS:
            raise ValueError(
                f"bin_hours/bin_humidity_ratio must have length {N_BINS} "
                f"(t_A = −25…+35 °C), got {len(self.bin_hours)}/{len(self.bin_humidity_ratio)}"
            )

    @property
    def k69(self) -> float:
        """K69 (electricity full-load hours); defaults to K68."""
        if self.full_load_hours_electricity is not None:
            return self.full_load_hours_electricity
        return self.full_load_hours

    @property
    def t_zul_curve(self) -> tuple[float, float, float, float]:
        """Supply-air set temperatures C88..C91 (override M6/L6)."""
        if self.curve_t_zul is not None:
            return self.curve_t_zul
        t = self.curve_ta
        t_summer = self.t_supply_summer
        t_winter = self.t_supply_winter
        return (
            t_winter if t_winter != 0 else t[0],
            t_summer if t_summer != 0 else t[1],
            t_summer if t_summer != 0 else t[2],
            t_summer if t_summer != 0 else t[3],
        )


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AhuBinResult:
    """Result of one temperature bin (IST block row 121 + k, t_A = k − 25 °C).

    The fields carry both the treatment energies (MWh per bin) and the
    intermediate psychrometric states used for the cache-value comparison
    against the workbook dump (``tests/test_ahu.py``).
    """

    t_outdoor: float  #: A [°C]
    hours: float  #: B [h/a]
    x_aul: float  #: C [g/kg]
    rh_aul_room: float  #: E [–]
    t_after_frost: float  #: G [°C]
    t_after_wrg_fixed: float  #: I [°C]
    t_after_wrg_limited: float  #: J [°C]
    wrg_epsilon: float  #: K [–] (modulated efficiency)
    t_after_wrg: float  #: L [°C]
    x_after_wrg: float  #: M [g/kg]
    h_mil_max: float  #: N [kJ/kg] (γ_max)
    h_mil_min: float  #: O [kJ/kg] (γ_min)
    h_mil_target: float  #: S [kJ/kg]
    t_mil: float  #: Q [°C] (enthalpy branch)
    x_mil: float  #: R [g/kg]
    t_mil_temp: float  #: W [°C] (temperature branch)
    x_mil_temp: float  #: X [g/kg]
    h_mil_temp: float  #: Y [kJ/kg]
    coil_t: float  #: Z [°C]
    coil_x: float  #: AA [g/kg]
    coil_h: float  #: AB [kJ/kg]
    slope: float  #: AG [°C/(g/kg)]
    t_d1: float  #: AH [°C]
    x_d1: float  #: AI [g/kg]
    h_d1: float  #: AJ [kJ/kg]
    t_d2: float  #: AK [°C]
    x_d2: float  #: AL [g/kg]
    h_d2: float  #: AM [kJ/kg]
    h_point_g: float  #: AV [kJ/kg]
    fall: int  #: AW (1–4)
    t_supply_soll: float  #: BJ [°C]
    x_supply_soll: float  #: BL [g/kg]
    h_supply_soll: float  #: BM [kJ/kg]
    t_supply_ist: float  #: BN [°C]
    x_supply_ist: float  #: BP [g/kg]
    h_supply_ist: float  #: BQ [kJ/kg]
    t_room: float  #: BR [°C]
    rh_room: float  #: BS [–]
    x_room: float  #: BT [g/kg]
    t_exhaust: float  #: BU [°C]
    x_exhaust: float  #: BW [g/kg]
    dh_cooling: float  #: BZ [kJ/kg]
    dh_dehum_cooling: float  #: CA [kJ/kg]
    dh_dehum_heating: float  #: CB [kJ/kg]
    dh_heating: float  #: CC [kJ/kg]
    dh_humidification: float  #: CD [kJ/kg]
    energy_cooling_mwh: float  #: CJ [MWh]
    energy_heating_mwh: float  #: CK [MWh]
    energy_dehum_cooling_mwh: float  #: CE [MWh]
    energy_dehum_heating_mwh: float  #: CF [MWh]
    energy_humidification_mwh: float  #: CM [MWh]
    energy_fan_mwh: float  #: CT [MWh]
    water_humidification_l: float  #: CH [L]
    water_condensate_l: float  #: CL [L]


@dataclass(frozen=True)
class FanModelResult:
    """Fan model (Formula 10): staged powers, motor efficiencies, annual power."""

    volume_stages: tuple[float, float, float]  #: E18..E20 (ZUL) [m³/h]
    volume_abl_stages: tuple[float, float, float]  #: E23..E25 (ABL) [m³/h]
    power_stages: tuple[float, float, float]  #: I14..I16 (ZUL) [kW]
    power_abl_stages: tuple[float, float, float]  #: I17..I19 (ABL) [kW]
    motor_eta_zul: float  #: C108 [–]
    motor_eta_abl: float  #: E108 [–]
    stage_shares: tuple[float, float, float]  #: M58..M60 [–]
    power_weighted_total: float  #: M67 [kW] (should equal fan_power_total)
    volume_weighted_annual: float  #: K70 [m³/h]
    power_weighted_annual: float  #: M70 [kW]


@dataclass(frozen=True)
class AhuAnnualResult:
    """Annual result rows 254–260 (and the water rows 262/263) of the workbook.

    Field names keep the German row labels (Luftkühlung / Lufterwärmung /
    Erwärmung Bef. / Entfeuchtung Kühlung / Entfeuchtung Erwärmung /
    Ventilator / Total); each pair is (energy kWh, power kW).
    """

    luftkuehlung_kwh: float  #: C254
    luftkuehlung_kw: float  #: D254
    lufterwaermung_kwh: float  #: C255
    lufterwaermung_kw: float  #: D255
    erwaermung_befeuchtung_kwh: float  #: C256
    erwaermung_befeuchtung_kw: float  #: D256
    entfeuchtung_kuehlung_kwh: float  #: C257
    entfeuchtung_kuehlung_kw: float  #: D257
    entfeuchtung_erwaermung_kwh: float  #: C258
    entfeuchtung_erwaermung_kw: float  #: D258
    ventilator_kwh: float  #: C259
    ventilator_kw: float  #: D259
    total_kwh: float  #: C260
    total_kw: float  #: D260
    befeuchtungswasser_l: float  #: C262 [L/a]
    kondensat_l: float  #: C263 [L/a]
    #: Derived quantities (verification support).
    k70: float  #: K70 [m³/h]
    m70: float  #: M70 [kW]
    fan: FanModelResult


# ---------------------------------------------------------------------------
# Formula 1 — bin hours
# ---------------------------------------------------------------------------


def compute_bin_hours(climate_hours: Sequence[float], full_load_hours: float) -> tuple[float, ...]:
    """Annual operating hours per bin (Formula 1): B = O/8760 · K68.

    Args:
        climate_hours: 61 annual bin hours from ``Klimadaten!O5:O65`` [h/a].
        full_load_hours: full-load hours on an air-volume basis K68 [h/a].

    Returns:
        61 operating hours [h/a] summing to ``full_load_hours``.
    """
    if len(climate_hours) != N_BINS:
        raise ValueError(f"climate_hours must have length {N_BINS}")
    return tuple(float(h) / HOURS_PER_YEAR * full_load_hours for h in climate_hours)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _round_excel(x: float, digits: int) -> float:
    """Excel ROUND (half away from zero), used by the case detector AW."""
    factor = 10.0**digits
    if x >= 0:
        return math.floor(x * factor + 0.5) / factor
    return math.ceil(x * factor - 0.5) / factor


def _gt(a: float, b: float) -> bool:
    """Strict ``>`` with a 1-ulp-scale tolerance for workbook state points.

    The workbook compares algebraically identical states (e.g. the MIL and the
    supply-setpoint humidity content, ``X`` vs ``BL``, are both equal to the
    outdoor content in the dry case) with exact Excel arithmetic. The Python
    port re-derives both values through the psychrometric functions, whose
    1-ulp rounding (Excel's ``EXP`` vs the C library ``exp``) can flip an
    exact comparison at the vertical-cooling-curve guard (``AG = 1E+23``,
    ch04 §4.14-6) and turn a no-op branch into a huge value. A relative
    tolerance of 1e-9 swallows that floating-point noise while leaving
    genuinely distinct states untouched.
    """
    return a - b > 1e-9 * max(abs(a), abs(b), 1.0)


def _eq(a: float, b: float) -> bool:
    """Workbook-style equality of state points (see :func:`_gt`)."""
    return not _gt(a, b) and not _gt(b, a)


def _motor_efficiency(motor_class: str, power: float) -> float:
    """Look up the motor efficiency by class and rated power (rows 100–108)."""
    bands = MOTOR_EFFICIENCY_CLASSES.get(motor_class)
    if bands is None:
        return 1.0
    for band, limit in enumerate(_MOTOR_BANDS):
        if power < limit:
            return bands[band]
    return bands[-1]


def _t_curve(t_a: float, ta: tuple, tzul: tuple, traum: tuple) -> tuple[float, float]:
    """Piecewise-linear interpolation of the temperature curve (columns BJ/BR).

    Returns (t_ZUL, t_Raum) for the given outdoor temperature. Mirrors the
    workbook formula exactly (first segment anchored at the second breakpoint
    with the first slope — including the extrapolation below B89).
    """
    (b1, b2, b3, b4), (c1, c2, c3, c4), (d1, d2, d3, d4) = ta, tzul, traum
    i1 = (c2 - c1) / (b2 - b1) if b2 != b1 else 0.0
    i2 = (c3 - c2) / (b3 - b2) if b3 != b2 else 0.0
    i3 = (c4 - c3) / (b4 - b3) if b4 != b3 else 0.0
    j1 = (d2 - d1) / (b2 - b1) if b2 != b1 else 0.0
    j2 = (d3 - d2) / (b3 - b2) if b3 != b2 else 0.0
    j3 = (d4 - d3) / (b4 - b3) if b4 != b3 else 0.0
    if t_a <= b2:
        t_zul = c2 - (b2 - t_a) * i1
        t_raum = d2 - (b2 - t_a) * j1
    elif t_a <= b3:
        t_zul = c3 - (b3 - t_a) * i2
        t_raum = d3 - (b3 - t_a) * j2
    else:
        t_zul = c4 - (b4 - t_a) * i3
        t_raum = d4 - (b4 - t_a) * j3
    return t_zul, t_raum


def _fall1_tzul(heiz: int, bef: int, t_soll: float, t_mil: float) -> float:
    """VBA ``Fall1Tzul`` — supply-air IST temperature, Fall 1 (heating)."""
    if heiz == 1:  # heating coil present → setpoint reached
        return t_soll
    return t_mil


def _fall1_xzul(heiz: int, bef: int, x_soll: float, x_mil: float) -> float:
    """VBA ``Fall1xzul`` — supply-air IST humidity, Fall 1."""
    if heiz == 1 and bef == 1:
        return x_soll
    return x_mil


def _fall2_tzul(heiz: int, kuhl: int, t_soll: float, t_mil: float, t_a: float) -> float:
    """VBA ``Fall2Tzul`` — supply-air IST temperature, Fall 2 (dehumidify)."""
    if heiz == 1 and kuhl == 1:
        if t_a > t_soll and t_a < t_mil:
            return t_a
        if t_a > t_soll and t_a > t_mil:
            return t_soll
        if t_soll < t_a:
            return t_a
        return t_soll
    if heiz == 1:  # and kuhl == 0
        return max(t_soll, t_mil)
    if kuhl == 1:  # and heiz == 0
        if t_soll > t_mil:
            return t_mil
        if t_soll > t_a:
            return t_soll
        return t_a
    return t_mil


def _fall2_xzul(heiz: int, kuhl: int, x_soll: float, x_mil: float, x_a: float) -> float:
    """VBA ``Fall2xzul`` — supply-air IST humidity, Fall 2."""
    if heiz == 1 and kuhl == 1:
        return min(x_a, x_mil)
    if heiz == 1:
        return x_mil
    if kuhl == 1:
        return min(x_a, x_mil)
    return x_mil


# ---------------------------------------------------------------------------
# Per-bin state chain
# ---------------------------------------------------------------------------


def _compute_bin(
    inp: AhuInput,
    k: int,
    hours: float,
    x_aul: float,
    p: float,
    k70: float,
    m70: float,
    i20: float,
    f113: float,
) -> AhuBinResult:
    """One temperature bin of the IST block (row 121 + k)."""
    t_a = T_MIN_BIN + k

    # --- Formula 1: bin hours ------------------------------------------------
    b = hours / HOURS_PER_YEAR * inp.full_load_hours

    # --- temperature curve: supply-air setpoint + room temperature (F. 7) ----
    bj, br = _t_curve(t_a, inp.curve_ta, inp.t_zul_curve, inp.curve_t_raum)

    # --- outdoor state (Formula 2) -------------------------------------------
    # E = MIN(100%, RelFeuchte(BR, C, p)); room rF inherits the outdoor moisture.
    rh_aul_room = min(1.0, relative_humidity(br, x_aul, p))

    # --- frost-protection preheating (Formula 2, only when t_A <= E33) -------
    if t_a <= inp.frost_threshold and inp.frost_protection != "off":
        if inp.frost_protection == "elektrisch (ein/aus)":
            p_vs = f113
        else:  # "elektrisch (variabel)"
            p_vs = abs(
                k70
                * CP_AIR
                * AIR_DENSITY
                * min(
                    abs(t_a - inp.frost_threshold),
                    abs(inp.heating_design_temp - inp.frost_threshold),
                )
                / SECONDS_PER_HOUR
            )
        t_after_frost = p_vs * SECONDS_PER_HOUR / (k70 * CP_AIR * AIR_DENSITY) + t_a
    else:
        t_after_frost = t_a

    # --- room/exhaust-air state (Formula 7) ----------------------------------
    # BS = clamp(E, E50, E48); BT = x(BR, BS); BU = BR (+2 K Quellluft); BW = BT + I20
    bs = min(max(rh_aul_room, inp.rh_min), inp.rh_max)
    bt = absolute_humidity(br, bs, p)
    if inp.air_supply_type == _LBL_QUELLLUFT:
        bu = br + QUELLLUFT_DELTA_T  # (i21 == 0 branch of BU)
    else:
        bu = br
    bw = bt + i20

    # --- supply-air setpoint (Formula 7) -------------------------------------
    # BK = MIN(1, RelFeuchte(BJ, BT, p)); BL = x(BJ, BK); BM = h(BJ, BL)
    bk = min(1.0, relative_humidity(bj, bt, p))
    bl = absolute_humidity(bj, bk, p)
    bm = enthalpy_from_absolute_humidity(bj, bl, p)

    # --- WRG heat recovery (Formula 3) ---------------------------------------
    # F = IF(H<=0, IF(BU<A,1,0),0), H = BJ - A (summer cooling flag)
    h_col = bj - t_a
    f = 1 if (h_col <= 0 and bu < t_a) else 0
    i_wrg = inp.wrg_efficiency * (bu - t_a) + t_a
    j_wrg = min(i_wrg, bj) if f == 0 else i_wrg
    if not inp.bypass:
        k_eps = inp.wrg_efficiency
    elif (not inp.krg) and f == 1:
        # Summer cooling flag F=1 and no cooling recovery (KRG absent) → full bypass.
        # (With KRG present the WRG actively recovers cooling, ε stays at η0.)
        k_eps = 0.0
    elif t_a == bu:
        k_eps = 0.0
    else:
        k_eps = max((j_wrg - t_a) / (bu - t_a), 0.0)
    l_wrg = k_eps * (bu - t_a) + t_a if inp.bypass else i_wrg
    if inp.wrg_efficiency == 0.0:
        m_wrg = x_aul
    else:
        m_wrg = (k_eps / inp.wrg_efficiency * inp.moisture_recovery) * (bw - x_aul) + x_aul

    # --- mixed air MIL (Formula 4) -------------------------------------------
    h_lm = enthalpy_from_absolute_humidity(l_wrg, m_wrg, p)
    h_buw = enthalpy_from_absolute_humidity(bu, bw, p)
    n_mil = h_lm * inp.fresh_air_max + (1 - inp.fresh_air_max) * h_buw
    o_mil = h_lm * inp.fresh_air_min + (1 - inp.fresh_air_min) * h_buw
    # T (single-argument MIN is a no-op, workbook quirk §4.14-4); U as usual.
    t_mil_enc = l_wrg * inp.fresh_air_max + bu * (1 - inp.fresh_air_max)
    u_mil = l_wrg * inp.fresh_air_min + bu * (1 - inp.fresh_air_min)
    # Target enthalpy S = MIN(MAX(N, BM), O); return-air share P brings h to S.
    s_mil = min(max(n_mil, bm), o_mil)
    if h_lm == s_mil:
        p_share = 1.0 - inp.fresh_air_max
    else:
        p_share = 1.0 - (s_mil - h_buw) / (h_lm - h_buw)
    q_mil = l_wrg * (1 - p_share) + bu * p_share
    r_mil = m_wrg * (1 - p_share) + bw * p_share
    # Temperature-control branch: W = MIN(MAX(T, BJ), U); share V brings t to W.
    w_mil = min(max(t_mil_enc, bj), u_mil)
    if l_wrg == w_mil:
        v_share = 1.0 - inp.fresh_air_max
    else:
        v_share = 1.0 - (w_mil - bu) / (l_wrg - bu)
    x_mil = m_wrg * (1 - v_share) + bw * v_share
    y_mil = enthalpy_from_absolute_humidity(w_mil, x_mil, p)

    # --- cooling coil and linear cooling curve (Formula 5) -------------------
    z = (inp.coil_vl + inp.coil_rl) / 2.0  # AVERAGE(E45:F46) = 9 °C
    if inp.enthalpy_control:
        aa = min(absolute_humidity(z, 1.0, p), r_mil)
    else:
        aa = min(absolute_humidity(z, 1.0, p), x_mil)
    ab = enthalpy_from_absolute_humidity(z, aa, p)
    af = (inp.coil_vl + inp.coil_rl) / 2.0  # AVERAGE(E45:E46), curve offset
    if inp.enthalpy_control:
        ag = 1e23 if aa == r_mil else (q_mil - af) / (r_mil - aa)
    else:
        ag = 1e23 if aa == x_mil else (w_mil - af) / (x_mil - aa)
    if inp.enthalpy_control:
        ah = max(af + ag * (bl - aa) if _gt(r_mil, bl) else q_mil, z)
    else:
        ah = max(af + ag * (bl - aa) if _gt(x_mil, bl) else w_mil, z)
    ai = aa if ah == z else bl
    aj = enthalpy_from_absolute_humidity(ah, ai, p)
    if inp.enthalpy_control:
        ak = max(min(q_mil, bj), z)
    else:
        ak = max(min(w_mil, bj), z)
    al = aa if z == ak else (bj - af) / ag + aa
    am = enthalpy_from_absolute_humidity(ak, al, p)

    # --- point E/G (heating-coil reference, Formula 8 CC/CD) -----------------
    # AO = MIL humidity (R or X); AP = BM (target enthalpy); AN = T(AP, AO).
    ao = r_mil if inp.enthalpy_control else x_mil
    ap = bm
    _an = temperature_from_enthalpy(ap, ao)  # AN (informational)

    # --- case determination (Formula 6) --------------------------------------
    if inp.case_detector_s_based:
        fall = (
            1
            if (
                _round_excel(bm, 4) >= _round_excel(s_mil, 4)
                and _round_excel(bl, 4) >= _round_excel(r_mil, 4)
                and _round_excel(bj, 4) >= _round_excel(q_mil, 4)
            )
            else 2
            if _round_excel(bl, 4) < _round_excel(aa, 4)
            else 3
            if _round_excel(bj, 4) >= _round_excel(ah, 4)
            else 4
        )
    else:
        fall = (
            1
            if (
                _round_excel(bm, 4) >= _round_excel(y_mil, 4)
                and _round_excel(bl, 4) >= _round_excel(x_mil, 4)
                and _round_excel(bj, 4) >= _round_excel(w_mil, 4)
            )
            else 2
            if _round_excel(bl, 4) < _round_excel(aa, 4)
            else 3
            if _round_excel(bj, 4) >= _round_excel(ah, 4)
            else 4
        )

    # --- equipment-availability flags -----------------------------------------
    ax = 1 if inp.heating_coil else 0
    ay = 1 if inp.humidification_type != _LBL_KEINE else 0
    az = 1 if inp.cooling_coil else 0
    ba = 1 if (inp.dehumidification and az == 1) else 0

    # --- supply-air IST state per case (BB..BI → BN/BP) ----------------------
    mil_t = x_mil if not inp.enthalpy_control else r_mil
    mil_tt = w_mil if not inp.enthalpy_control else q_mil
    bb = _fall1_tzul(ax, ay, bj, mil_tt) if fall == 1 else 0.0
    bc = _fall1_xzul(ax, ay, bl, mil_t) if fall == 1 else 0.0
    bd = _fall2_tzul(ax, az, bj, mil_tt, z) if fall == 2 else 0.0
    be = _fall2_xzul(ax, az, bl, mil_t, aa) if fall == 2 else 0.0
    if fall == 3:
        if ba == 1 and ax == 1:
            bf = bj
        elif az == 1:
            bf = min(bj, bj if ax == 1 else mil_tt)
        elif ax == 1 and bj > mil_tt:
            bf = bj
        else:
            bf = mil_tt
        if ba == 1 and ax == 1:
            bg = bl
        elif az == 1:
            bg = min(al, mil_t)
        else:
            bg = mil_t
    else:
        bf = 0.0
        bg = 0.0
    if fall == 4:
        bh = bj if az == 1 else mil_tt
        if ay == 0:
            bi = al if az == 1 else mil_t
        else:
            bi = bl
    else:
        bh = 0.0
        bi = 0.0
    bn = bb + bd + bf + bh
    bp = bc + be + bg + bi
    bq = enthalpy_from_absolute_humidity(bn, bp, p)

    # --- point G (AT = BN, AU = AO) and its enthalpy AV -----------------------
    at_g = bn
    au_g = ao
    av = enthalpy_from_absolute_humidity(at_g, au_g, p)

    # --- enthalpy differences (Formula 8) -------------------------------------
    if inp.case_detector_s_based:
        bz = max(az * (s_mil - am) if az == 1 and fall in (2, 3, 4) else 0.0, 0.0)
    else:
        bz = max(az * (y_mil - am) if az == 1 and fall in (2, 3, 4) else 0.0, 0.0)
    if inp.enthalpy_control:
        if ba == 1:
            if fall == 3:
                ca = am - aj
            elif fall == 2:
                ca = 0.0 if _eq(bp, r_mil) else s_mil - ab - bz
            else:
                ca = 0.0
        else:
            ca = 0.0
        ca = max(ca, 0.0)
        if ba == 1 and ax == 1:
            if fall == 3:
                cb = bq - aj
            elif fall == 2:
                cb = 0.0 if _eq(r_mil, bp) else bq - ab
            else:
                cb = 0.0
        else:
            cb = 0.0
        cb = max(cb, 0.0)
        cc = 0.0 if f == 1 else (av - s_mil if ax == 1 and fall == 1 else 0.0)
    else:
        if ba == 1:
            if fall == 3:
                ca = am - aj
            elif fall == 2:
                ca = 0.0 if _eq(bp, x_mil) else y_mil - ab - bz
            else:
                ca = 0.0
        else:
            ca = 0.0
        ca = max(ca, 0.0)
        if ba == 1 and ax == 1:
            if fall == 3:
                cb = bq - aj
            elif fall == 2:
                cb = 0.0 if _eq(x_mil, bp) else bq - ab
            else:
                cb = 0.0
        else:
            cb = 0.0
        cb = max(cb, 0.0)
        cc = 0.0 if f == 1 else (av - y_mil if ax == 1 and fall == 1 else 0.0)
    cd = bq - av if ay == 1 and b > 0 and fall in (1, 4) else 0.0

    # --- energies (Formula 8, MWh per bin) ------------------------------------
    # dV summer branch: IF(OR(AND(A>=E26,E27>0),AND(A>=E26,E27<0)), P70, K70).
    use_summer_flow = (t_a >= inp.summer_start_temp and inp.summer_dv > 0) or (
        t_a >= inp.summer_start_temp and inp.summer_dv < 0
    )
    flow = (
        (inp.summer_volume_flow if inp.summer_volume_flow is not None else k70)
        if use_summer_flow
        else k70
    )
    m_flow = flow * AIR_DENSITY  # kg/h
    ce = m_flow * b * ca / KJ_PER_MWH if inp.cooling_coil else 0.0
    cf = m_flow * b * cb / KJ_PER_MWH if inp.heating_coil else 0.0
    cg = m_flow * b * cd / KJ_PER_MWH
    ch = max(0.0, (bp - mil_t) * b * flow * AIR_DENSITY / 1000.0)
    ci = (
        ch * CP_WATER * (100.0 - inp.chilled_water_temp) + HEAT_OF_VAPORIZATION_100 * ch
    ) / 3600000.0
    cj = m_flow * b * bz / KJ_PER_MWH if inp.cooling_coil else 0.0
    ck = m_flow * b * cc / KJ_PER_MWH if inp.heating_coil else 0.0
    cl = max(0.0, -(bp - mil_t) * b * flow * AIR_DENSITY / 1000.0)
    if inp.humidification_type == _LBL_KEINE:
        cm = 0.0
    elif inp.humidification_type == _LBL_ADIABAT:
        cm = cg
    else:  # steam ("Dampfbef.")
        cm = ci
    ct = b * m70 / 1000.0

    return AhuBinResult(
        t_outdoor=t_a,
        hours=b,
        x_aul=x_aul,
        rh_aul_room=rh_aul_room,
        t_after_frost=t_after_frost,
        t_after_wrg_fixed=i_wrg,
        t_after_wrg_limited=j_wrg,
        wrg_epsilon=k_eps,
        t_after_wrg=l_wrg,
        x_after_wrg=m_wrg,
        h_mil_max=n_mil,
        h_mil_min=o_mil,
        h_mil_target=s_mil,
        t_mil=q_mil,
        x_mil=r_mil,
        t_mil_temp=w_mil,
        x_mil_temp=x_mil,
        h_mil_temp=y_mil,
        coil_t=z,
        coil_x=aa,
        coil_h=ab,
        slope=ag,
        t_d1=ah,
        x_d1=ai,
        h_d1=aj,
        t_d2=ak,
        x_d2=al,
        h_d2=am,
        h_point_g=av,
        fall=fall,
        t_supply_soll=bj,
        x_supply_soll=bl,
        h_supply_soll=bm,
        t_supply_ist=bn,
        x_supply_ist=bp,
        h_supply_ist=bq,
        t_room=br,
        rh_room=bs,
        x_room=bt,
        t_exhaust=bu,
        x_exhaust=bw,
        dh_cooling=bz,
        dh_dehum_cooling=ca,
        dh_dehum_heating=cb,
        dh_heating=cc,
        dh_humidification=cd,
        energy_cooling_mwh=cj,
        energy_heating_mwh=ck,
        energy_dehum_cooling_mwh=ce,
        energy_dehum_heating_mwh=cf,
        energy_humidification_mwh=cm,
        energy_fan_mwh=ct,
        water_humidification_l=ch,
        water_condensate_l=cl,
    )


# ---------------------------------------------------------------------------
# Fan model (Formula 10)
# ---------------------------------------------------------------------------


def compute_fan_model(inp: AhuInput) -> FanModelResult:
    """Staged fan powers, motor efficiencies and annual average power (F. 10).

    The affinity law P = P_nom·(V_stufe/V_max)^2.5 (exponent 2.5, workbook
    convention) applies to the staged air volumes; the motor efficiency comes
    from the class × power-band lookup. ``power_weighted_total`` (M67) is the
    time-weighted sum of the stage powers including motor efficiencies and
    should equal ``fan_power_total`` (G6) for single-stage systems; the annual
    average power ``M70 = G6·K69/K68`` uses the total fan power directly
    (workbook convention, ch04 §4.12/§4.13).
    """
    e18 = inp.volume_flow
    if inp.regulation == "einstufig":
        e19, e20 = e18, e18
    elif inp.regulation == "zweistufig":
        e19, e20 = e18 * 0.67, e18 * 0.67
    else:  # stufenlos
        e19, e20 = e18 * 0.67, e18 * 0.33
    v_max = max(e18, e19, e20)
    e16 = (
        inp.fan_power_zul_stage1
        if inp.fan_power_zul_stage1 is not None
        else inp.fan_power_total / 2.0
    )
    e21 = inp.fan_power_abl_stage1 if inp.fan_power_abl_stage1 is not None else e16

    def _stage_power(p_nom: float, v: float) -> float:
        if v >= v_max or v_max == 0:
            return p_nom
        return p_nom * (v / v_max) ** 2.5

    p_zul = (_stage_power(e16, e18), _stage_power(e16, e19), _stage_power(e16, e20))
    p_abl = (_stage_power(e21, e18), _stage_power(e21, e19), _stage_power(e21, e20))
    eta_zul = _motor_efficiency(inp.motor_class, e16)
    eta_abl = _motor_efficiency(
        inp.motor_class_abl if inp.motor_class_abl is not None else inp.motor_class, e21
    )
    total = inp.weekly_hours_total
    if total > 0:
        shares: tuple[float, float, float] = (
            inp.weekly_hours[0] / total,
            inp.weekly_hours[1] / total,
            inp.weekly_hours[2] / total,
        )
    else:
        shares = (0.0, 0.0, 0.0)
    m67 = sum((p_zul[i] / eta_zul + p_abl[i] / eta_abl) * shares[i] for i in range(3))
    k70 = inp.volume_flow * inp.full_load_hours / HOURS_PER_YEAR
    m70 = inp.fan_power_total * inp.k69 / inp.full_load_hours
    return FanModelResult(
        volume_stages=(e18, e19, e20),
        volume_abl_stages=(e18, e19, e20),
        power_stages=p_zul,
        power_abl_stages=p_abl,
        motor_eta_zul=eta_zul,
        motor_eta_abl=eta_abl,
        stage_shares=shares,
        power_weighted_total=m67,
        volume_weighted_annual=k70,
        power_weighted_annual=m70,
    )


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


def compute_ahu_bins(inp: AhuInput) -> tuple[AhuBinResult, ...]:
    """Run the per-bin state chain for all 61 temperature bins (Formula 1–8).

    Args:
        inp: the AHU inputs.

    Returns:
        61 :class:`AhuBinResult` in t_A = −25…+35 °C order.
    """
    fan = compute_fan_model(inp)
    k70 = fan.volume_weighted_annual
    m70 = fan.power_weighted_annual
    # I20 = Feuchtelast: 0 for E52 = 0, else (E52·1000)/(3600·(K70/3600)·ρ) g/kg.
    if inp.room_moisture_load == 0.0:
        i20 = 0.0
    else:
        i20 = (inp.room_moisture_load * 1000.0) / (3600.0 * (k70 / 3600.0) * AIR_DENSITY)
    # F113 = frost-protection heating power (Formula 2), kW.
    f113 = abs(
        k70
        * CP_AIR
        * AIR_DENSITY
        * (inp.heating_design_temp - inp.frost_threshold)
        / SECONDS_PER_HOUR
    )
    bins = tuple(
        _compute_bin(
            inp,
            k,
            float(hours),
            float(x_aul),
            inp.pressure,
            k70,
            m70,
            i20,
            f113,
        )
        for k, (hours, x_aul) in enumerate(zip(inp.bin_hours, inp.bin_humidity_ratio))
    )
    return bins


def compute_ahu_annual(inp: AhuInput) -> AhuAnnualResult:
    """Annual summary (Formula 9): rows 182/183 → rows 254–260 and 262/263.

    The energy sums follow the workbook convention ``SUM(Cx122:Cx181)``, i.e.
    they exclude the t_A = −25 °C bin (row 121) — reproduced exactly (the bin
    has 0 hours in all golden cases). The power maxima follow rows
    ``BZ/CA/CB/CD 121:181`` and ``CC 133:181`` (t_A = −13 °C and above).
    """
    bins = compute_ahu_bins(inp)
    fan = compute_fan_model(inp)
    e18 = inp.volume_flow

    # Energy sums: rows 122..181 (index 1..60, t_A = −24…+35).
    s = bins[1:]
    cj182 = sum(r.energy_cooling_mwh for r in s)
    ck182 = sum(r.energy_heating_mwh for r in s)
    ce182 = sum(r.energy_dehum_cooling_mwh for r in s)
    cf182 = sum(r.energy_dehum_heating_mwh for r in s)
    cm182 = sum(r.energy_humidification_mwh for r in s)
    ct182 = sum(r.energy_fan_mwh for r in s)
    ch182 = sum(r.water_humidification_l for r in s)
    cl182 = sum(r.water_condensate_l for r in s)

    # Power maxima: full range 121..181 except CC from row 133 (t_A = −13 °C).
    factor = e18 * AIR_DENSITY / SECONDS_PER_HOUR
    bz183 = max(r.dh_cooling for r in bins) * factor
    ca183 = max(r.dh_dehum_cooling for r in bins) * factor
    cb183 = max(r.dh_dehum_heating for r in bins) * factor
    cc183 = max(r.dh_heating for r in bins[12:]) * factor  # rows 133..181
    cd183 = max(r.dh_humidification for r in bins) * factor

    c254 = cj182 * 1000.0
    c255 = ck182 * 1000.0
    c256 = cm182 * 1000.0
    c257 = ce182 * 1000.0
    c258 = cf182 * 1000.0
    c259 = ct182 * 1000.0
    d259 = inp.fan_power_total

    return AhuAnnualResult(
        luftkuehlung_kwh=c254,
        luftkuehlung_kw=bz183,
        lufterwaermung_kwh=c255,
        lufterwaermung_kw=cc183,
        erwaermung_befeuchtung_kwh=c256,
        erwaermung_befeuchtung_kw=cd183,
        entfeuchtung_kuehlung_kwh=c257,
        entfeuchtung_kuehlung_kw=ca183,
        entfeuchtung_erwaermung_kwh=c258,
        entfeuchtung_erwaermung_kw=cb183,
        ventilator_kwh=c259,
        ventilator_kw=d259,
        total_kwh=c254 + c255 + c256 + c257 + c258 + c259,
        total_kw=bz183 + cc183 + cd183 + ca183 + cb183 + d259,
        befeuchtungswasser_l=ch182,
        kondensat_l=cl182,
        k70=fan.volume_weighted_annual,
        m70=fan.power_weighted_annual,
        fan=fan,
    )
