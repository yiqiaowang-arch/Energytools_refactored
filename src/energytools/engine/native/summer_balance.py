"""Summer design-day heat balance (``Profile!`` Wärmebilanz-Sommertag block).

The workbook's cooling-design day: a 24-hour balance of a room on the
August design day (``Aug_Auslegung``), reproducing the ``Wärmebilanz -
Sommertag - Standard`` block of the ``Profile`` sheet row by row:

    C  persons        = Personen-Wärmeeintrag  × occupancy curve
    D  devices        = Geräte × device curve
    E  process        = Prozessanlagen × device curve
    F  lighting       = Beleuchtung × lighting curve
    J  solar          = radiation × 0.9 × g_effective × Glasflächenzahl
    K  air volume     = hygienic flow × ventilation stage curve (IDA mode)
    L  bypass         = open while |ΔT| < 2 K
    M  supply temp    = fixed value, else bypass → outdoor, else room + ΔT·(1−k)
    N  infiltration   = infiltration flow (m³/(h·m²))
    O  ventilation    = (K·(M−W) + N·X) · 0.32        (sensible exchange)
    P  transmission   = U·A/NGF × ΔT
    Q  balance        = −(C+D+E+F+J+O+P)              (with process)
    R  balance        = −(C+D+F+J+O+P)                (without process)
    U  cooling power  = min(0, R) × 1                  (Klimakälte, W/m²)
    V  outdoor temp   = August design-day temperature
    W  room temp      = Raumtemperatur setpoint
    X  ΔT             = V − W

All inputs are dataset values (room-type parameters, the room's editable
schedules, the station's design days); nothing is hardcoded except the
workbook's own constants (0.9 reduction, 200 W/m² shading threshold,
0.32 air constant, 2 K bypass band, IDA stage selection).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SummerBalanceRow:
    """One hour of the 24 h design-day balance (W/m², °C)."""

    hour: int
    persons: float  # C
    devices: float  # D
    process: float  # E
    lighting: float  # F
    solar: float  # J
    air_volume: float  # K (m³/(h·m²))
    bypass: int  # L (1 = open)
    supply_temp: float  # M (°C)
    infiltration: float  # N (m³/(h·m²))
    ventilation: float  # O (sensible exchange, W/m²)
    transmission: float  # P (W/m²)
    balance_with_process: float  # Q (W/m²)
    balance_without_process: float  # R (W/m²)
    cooling_power: float  # U (W/m²)
    outdoor_temp: float  # V (°C)
    room_temp: float  # W (°C)
    delta_temp: float  # X (K)

    def as_dict(self) -> dict:
        """JSON-ready row."""
        return {
            "hour": self.hour,
            "persons": self.persons,
            "devices": self.devices,
            "process": self.process,
            "lighting": self.lighting,
            "solar": self.solar,
            "air_volume": self.air_volume,
            "bypass": self.bypass,
            "supply_temp": self.supply_temp,
            "infiltration": self.infiltration,
            "ventilation": self.ventilation,
            "transmission": self.transmission,
            "balance_with_process": self.balance_with_process,
            "balance_without_process": self.balance_without_process,
            "cooling_power": self.cooling_power,
            "outdoor_temp": self.outdoor_temp,
            "room_temp": self.room_temp,
            "delta_temp": self.delta_temp,
        }


def summer_balance_24h(
    *,
    person_wm2: float,
    device_wm2: float,
    process_wm2: float,
    lighting_wm2: float,
    g_value: float,
    g_total: float,
    glasflaechenzahl: float,
    room_temp: float,
    air_volume: float,
    infiltration: float,
    supply_temp: float | None,
    supply_coeff: float,
    transmission_coeff: float,
    occupancy: tuple[float, ...],
    device_curve: tuple[float, ...],
    lighting_curve: tuple[float, ...],
    ventilation_curve: tuple[float, ...],
    radiation: tuple[float, ...],
    outdoor_temp: tuple[float, ...],
    reduction_factor: float = 0.9,
    shading_threshold: float = 200.0,
    air_constant: float = 0.32,
    bypass_band: float = 2.0,
) -> tuple[SummerBalanceRow, ...]:
    """The 24 h Wärmebilanz-Sommertag calculation (Standard, without node
    iteration — the workbook's X column is the instantaneous ΔT).

    All curves are 24 values; ``ventilation_curve`` is the curve of the
    IDA-selected regulation stage (einstufig/zweistufig/stufenlos).
    """
    rows = []
    for hour in range(24):
        persons = person_wm2 * occupancy[hour]
        devices = device_wm2 * device_curve[hour]
        process = process_wm2 * device_curve[hour]
        lighting = lighting_wm2 * lighting_curve[hour]
        g_effective = g_value if radiation[hour] <= shading_threshold else g_total
        solar = radiation[hour] * reduction_factor * g_effective * glasflaechenzahl
        volume = air_volume * ventilation_curve[hour]
        outdoor = outdoor_temp[hour]
        room = room_temp
        delta = outdoor - room
        # The workbook's bypass closes only when the room is warmer than the
        # outdoor air by 2 K or more (X >= 2); negative deltas stay open.
        bypass = 0 if delta >= bypass_band else 1
        if supply_temp is not None:
            zuluft = supply_temp
        else:
            zuluft = outdoor if bypass == 1 else room + delta * (1.0 - supply_coeff)
        sensible = (volume * (zuluft - room) + infiltration * delta) * air_constant
        transmission = transmission_coeff * delta
        balance_with = -(persons + devices + process + lighting + solar + sensible + transmission)
        balance_without = -(persons + devices + lighting + solar + sensible + transmission)
        cooling = min(0.0, balance_with)
        rows.append(
            SummerBalanceRow(
                hour=hour,
                persons=persons,
                devices=devices,
                process=process,
                lighting=lighting,
                solar=solar,
                air_volume=volume,
                bypass=bypass,
                supply_temp=zuluft,
                infiltration=infiltration,
                ventilation=sensible,
                transmission=transmission,
                balance_with_process=balance_with,
                balance_without_process=balance_without,
                cooling_power=cooling,
                outdoor_temp=outdoor,
                room_temp=room,
                delta_temp=delta,
            )
        )
    return tuple(rows)


def cooling_power_kw(rows: tuple[SummerBalanceRow, ...], ngf_m2: float) -> float:
    """The maximum hourly cooling power of the design day (kW).

    The workbook's Klimakälteleistungsbedarf is the maximum of the hourly
    cooling power ``U`` × NGF (``Qhc_Klimastat`` D/H/L columns).  ``U`` is
    ``min(0, Q)``, so the peak cooling hour is the most negative one.
    """
    return max(-row.cooling_power for row in rows) * ngf_m2 / 1000.0
