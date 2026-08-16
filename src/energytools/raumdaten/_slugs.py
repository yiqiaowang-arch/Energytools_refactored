"""Slug tables and helpers for the Raumdaten attribute accessors.

Shared by :mod:`energytools.raumdaten.accessors` (runtime) and
``tools/generate_accessors.py`` (code generation) — no dependency on the
generated module, so the generator can import this without a cycle.
"""

from __future__ import annotations

import re

__all__ = [
    "PARAMETER_ALIASES",
    "ROOM_USE_SLUGS",
    "parameter_slug",
    "slugify_label",
]

# ---------------------------------------------------------------------------
# Room-use slugs (curated English; stable across dataset releases)
# ---------------------------------------------------------------------------
ROOM_USE_SLUGS: dict[str, str] = {
    "1.01": "residential_mfh",
    "1.02": "residential_sfh",
    "2.01": "hotel_room",
    "2.02": "lobby_reception",
    "3.01": "group_office",
    "3.02": "open_plan_office",
    "3.03": "meeting_room",
    "3.04": "reception_hall",
    "4.01": "classroom",
    "4.02": "teacher_room",
    "4.03": "library",
    "4.04": "lecture_hall",
    "4.05": "specialist_classroom",
    "5.01": "grocery_shop",
    "5.02": "specialty_shop",
    "5.03": "furniture_store",
    "6.01": "restaurant",
    "6.02": "cafeteria",
    "6.03": "restaurant_kitchen",
    "6.04": "cafeteria_kitchen",
    "7.01": "auditorium",
    "7.02": "multi_purpose_hall",
    "7.03": "exhibition_hall",
    "8.01": "patient_room",
    "8.02": "ward_room",
    "8.03": "treatment_room",
    "9.01": "production_heavy",
    "9.02": "production_fine",
    "9.03": "laboratory",
    "10.01": "storage_hall",
    "11.01": "gymnasium",
    "11.02": "fitness_room",
    "11.03": "swimming_hall",
    "12.01": "circulation_area",
    "12.02": "circulation_24h",
    "12.03": "staircase",
    "12.04": "utility_room",
    "12.05": "kitchenette",
    "12.06": "wc_bath_shower",
    "12.07": "wc",
    "12.08": "locker_shower",
    "12.09": "parking_garage",
    "12.10": "laundry_room",
    "12.11": "cold_room",
    "12.12": "server_room",
}

# ---------------------------------------------------------------------------
# Parameter aliases (curated English slugs for the commonly asked parameters)
# ---------------------------------------------------------------------------
PARAMETER_ALIASES: dict[str, str] = {
    "1.1.1.2": "thermal_envelope_area",
    "1.1.2.9": "personnel_area",
    "1.1.2.8": "full_load_hours_year",
    "1.1.2.10": "activity_level",
    "1.1.2.11": "clothing_insulation",
    "1.1.3.3": "equipment_power",
    "1.1.3.4": "process_power",
    "1.1.3.6": "equipment_heat_gain",
    "1.1.3.5": "off_hours_power",
    "1.1.4.1": "illuminance",
    "1.1.4.2": "reference_illuminance",
    "1.1.4.4": "work_plane_height",
    "1.1.4.6": "lamp_efficacy",
    "1.1.4.9": "lighting_control_factor",
    "1.1.4.12": "lighting_full_load_hours",
    "1.1.4.13": "lighting_electricity",
    "1.1.5.1": "fresh_air_per_person",
    "1.1.5.2": "hygienic_airflow",
    "1.1.5.3": "process_airflow",
    "1.1.5.4": "infiltration_airflow",
    "1.1.5.5": "air_quality_class",
    "1.1.5.6": "heat_recovery_temp_eff",
    "1.1.5.7": "heat_recovery_annual_eff",
    "1.1.5.8": "volume_flow_full_load_hours",
    "1.1.6.4": "cooling_required",
    "1.1.7.3": "heating_design_temp",
    "1.1.8.1": "reference_unit",
    "1.1.8.2": "domestic_hot_water_per_unit",
    "1.1.8.3": "units_per_person",
    "1.1.8.4": "domestic_hot_water_per_person",
    "1.1.8.5": "water_to_hot_water_ratio",
    "1.1.8.6": "water_per_person",
}


def slugify_label(text: str) -> str:
    """ASCII slug from a (German) label: ``"Norm Aussentemperatur"`` -> ``norm_aussentemperatur``."""
    t = text.strip().lower()
    t = t.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return t or "param"


def parameter_slug(parameter_id: str, symbol: str, label_de: str) -> str:
    """Stable slug for a parameter: alias -> sanitized symbol -> slugified label."""
    if parameter_id in PARAMETER_ALIASES:
        return PARAMETER_ALIASES[parameter_id]
    sym = (symbol or "").strip()
    if sym and sym != "Symbol":
        s = re.sub(r"[^A-Za-z0-9]+", "_", sym).strip("_")
        if s:
            return s
    return slugify_label(label_de or parameter_id)
