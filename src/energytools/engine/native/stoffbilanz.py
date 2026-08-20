"""Stoffbilanz — the workbook's 24 h CO₂ and moisture balance (``Profile!``).

Reproduces the ``Stoffbilanz - Arbeitstag`` block (rows 278-301) of the
``Profile`` sheet: a one-hour-box air-quality model on the working day.

CO₂ (columns C-H):
    persons      = occupancy × NGF / Personenfläche
    emission     = persons × 20 × CO₂-rate (l/h) × 1000        [cm³/h]
    air flow     = (ventilation + infiltration) × NGF          [m³/h]
    concentration= C₀ + emission/flow × (1 − e^(−flow/volume)) [ppm]

Moisture (columns L-Y):
    person       = 66 g/(P·h) × persons
    total        = person + other sources (g/(h·m²)) × NGF
    saturation   = Magnus saturation pressure of the SIA 2028 month
    mixing ratio = RH% × 622 × p_sat / (p_air − RH% × p_sat)   [g/kg]
    outdoor conc = mixing ratio × 1.1                          [g/m³]
    Gl. (9)      = S + total/flow × (1 − e^(−flow/volume))     [g/m³]
    Gl. (8)      = (S₀ − total/flow)·e^(−flow/volume)
                   + total/flow + S·(1 − e^(−flow/volume))     [g/m³]

The month axis (the workbook's ``O273`` cell) and the SIA 2028 monthly
outdoor values come from the dataset; the room temperature per month is
the ``Profile!AS284`` series.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class StoffbilanzRow:
    """One hour of the 24 h material balance."""

    hour: int
    persons: float  # D
    co2_emission: float  # E (cm³/h)
    air_flow: float  # G (m³/h)
    co2_concentration: float  # H/I (ppm, Gl. 9/8)
    moisture_person: float  # L (g/h)
    moisture_total: float  # M (g/h)
    saturation_pressure: float  # Q (Pa)
    mixing_ratio: float  # R (g/kg)
    outdoor_moisture: float  # S (g/m³)
    moisture_concentration: float  # T (g/m³, Gl. 9)
    moisture_transient: float  # U (g/m³, Gl. 8)
    room_rh: float  # Y (%)

    def as_dict(self) -> dict:
        """JSON-ready row."""
        return {
            "hour": self.hour,
            "persons": self.persons,
            "co2_emission": self.co2_emission,
            "air_flow": self.air_flow,
            "co2_concentration": self.co2_concentration,
            "moisture_person": self.moisture_person,
            "moisture_total": self.moisture_total,
            "saturation_pressure": self.saturation_pressure,
            "mixing_ratio": self.mixing_ratio,
            "outdoor_moisture": self.outdoor_moisture,
            "moisture_concentration": self.moisture_concentration,
            "moisture_transient": self.moisture_transient,
            "room_rh": self.room_rh,
        }


def _magnus_hpa(temperature: float) -> float:
    """Magnus saturation pressure in hPa — the workbook's Q/X column
    formula ``610.5·exp(...)/100``."""
    if temperature >= 0.0:
        return 610.5 * math.exp(17.269 * temperature / (237.3 + temperature)) / 100.0
    return 610.5 * math.exp(21.875 * temperature / (265.5 + temperature)) / 100.0


def stoffbilanz_24h(
    *,
    person_area: float,
    ngf: float,
    room_height: float,
    co2_rate: float = 1.2,
    person_moisture: float = 66.0,
    other_moisture: float = 0.5,
    air_pressure: float,
    monthly_temperature: tuple[float, ...],
    monthly_humidity: tuple[float, ...],
    monthly_room_temp: tuple[float, ...],
    month_index: int,
    occupancy: tuple[float, ...],
    ventilation_flow: tuple[float, ...],  # m³/(h·m²), ventilation + infiltration
    start_co2: float = 400.0,
    start_moisture: float | None = None,
) -> tuple[StoffbilanzRow, ...]:
    """The 24 h Stoffbilanz-Arbeitstag calculation.

    All curves are 24 values; the month axis selects the SIA 2028 outdoor
    and room-temperature values (the workbook's ``O273`` month cell).
    ``start_moisture`` seeds the transient Gl. (8) series (the workbook's
    ``U275`` cell, the steady state of the previous day).
    """
    if not 0 <= month_index <= 11:
        raise ValueError(f"month_index {month_index} outside 0-11")
    volume = ngf * room_height
    month_temp = monthly_temperature[month_index]
    month_rh = monthly_humidity[month_index]
    month_room = monthly_room_temp[month_index]

    saturation_outdoor = _magnus_hpa(month_temp)
    saturation_room = _magnus_hpa(month_room)
    mixing = (
        month_rh / 100.0 * 622.0 * saturation_outdoor
        / (air_pressure - month_rh / 100.0 * saturation_outdoor)
    )
    outdoor_conc = mixing * 1.1
    room_rh_factor = saturation_room / 100.0

    rows = []
    moisture_prev = start_moisture if start_moisture is not None else outdoor_conc
    # The V column ("Gl. (8) t+24 h") is the same recursive transient seeded
    # with the U series' final hour (the workbook: V275 = U301), i.e. the
    # transient of the day that already ran.
    u_series: list[float] = []
    for hour in range(24):
        flow = ventilation_flow[hour] * ngf
        if flow > 0.0:
            decay = math.exp(-flow / volume)
            persons = occupancy[hour] * ngf / person_area
            moisture_total = person_moisture * persons + other_moisture * ngf
            moisture_prev = (
                (moisture_prev - moisture_total / flow) * decay
                + moisture_total / flow
                + outdoor_conc * (1.0 - decay)
            )
        u_series.append(moisture_prev)
    steady = u_series[-1]

    steady_prev = steady
    moisture_prev = start_moisture if start_moisture is not None else outdoor_conc
    for hour in range(24):
        persons = occupancy[hour] * ngf / person_area
        co2_emission = persons * 20.0 * co2_rate * 1000.0
        flow = ventilation_flow[hour] * ngf
        if flow > 0.0:
            decay = math.exp(-flow / volume)
            co2_conc = start_co2 + co2_emission / flow * (1.0 - decay)
        else:
            decay = 1.0
            co2_conc = start_co2
        moisture_person = person_moisture * persons
        moisture_total = moisture_person + other_moisture * ngf
        if flow > 0.0:
            moisture_conc = outdoor_conc + moisture_total / flow * (1.0 - decay)
            # Gl. (8) is a recursive transient: this hour's value depends on
            # the previous hour's (the workbook's U column; U275 seeds it).
            moisture_transient = (
                (moisture_prev - moisture_total / flow) * decay
                + moisture_total / flow
                + outdoor_conc * (1.0 - decay)
            )
            moisture_prev = moisture_transient
            # Gl. (8) t+24 h: the same recursion seeded with the converged
            # loop value (the workbook's V column; Y uses it).
            steady_transient = (
                (steady_prev - moisture_total / flow) * decay
                + moisture_total / flow
                + outdoor_conc * (1.0 - decay)
            )
            steady_prev = steady_transient
        else:
            moisture_conc = outdoor_conc
            moisture_transient = moisture_prev
            steady_transient = steady_prev
        # relative humidity from the t+24 h series:
        # (V/1.1·p)/(p_sat/100·(622+V/1.1)), capped at 100 %
        ratio = steady_transient / 1.1
        room_rh = min(
            100.0,
            ratio * air_pressure / (room_rh_factor * (622.0 + ratio)),
        )
        rows.append(
            StoffbilanzRow(
                hour=hour,
                persons=persons,
                co2_emission=co2_emission,
                air_flow=flow,
                co2_concentration=co2_conc,
                moisture_person=moisture_person,
                moisture_total=moisture_total,
                saturation_pressure=saturation_outdoor,
                mixing_ratio=mixing,
                outdoor_moisture=outdoor_conc,
                moisture_concentration=moisture_conc,
                moisture_transient=moisture_transient,
                room_rh=room_rh,
            )
        )
    return tuple(rows)
