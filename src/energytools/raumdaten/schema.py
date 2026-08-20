"""energytools.raumdaten.schema -- JSON Schema of the canonical dataset package.

Single source of truth for the package format (``package.json``): the loader
validates against it, the extractor writes it next to every package it produces
and the bundled sample fixture carries a copy.

The schema is JSON Schema draft 2020-12.  Row maps use ``"nutzid|regulation|
standard_version"`` / ``"nutzid|station_id|kind"`` string keys (the ``|``
separator cannot occur in regulation, standard-version or value-kind strings).
"""

from __future__ import annotations

__all__ = ["PACKAGE_SCHEMA", "SCHEMA_VERSION"]

SCHEMA_VERSION = "1.0"

_quantity = {
    "type": "object",
    "properties": {
        "value": {"type": ["number", "string", "boolean", "null"]},
        "unit": {"type": "string"},
        "provenance": {"$ref": "#/$defs/provenance"},
    },
    "required": ["value", "unit"],
    "additionalProperties": False,
}

_trilingual = {
    "type": "object",
    "properties": {"de": {"type": "string"}, "fr": {"type": "string"}, "it": {"type": "string"}},
    "required": ["de", "fr", "it"],
    "additionalProperties": False,
}

_source_ref = {
    "type": "object",
    "properties": {
        "workbook": {"type": "string"},
        "sheet": {"type": "string"},
        "range": {"type": ["string", "null"]},
        "formula": {"type": ["string", "null"]},
        "cached_value": {"type": ["number", "string", "null"]},
        "extraction_hash": {"type": ["string", "null"]},
    },
    "required": ["workbook", "sheet"],
    "additionalProperties": False,
}

_provenance = {
    "type": ["object", "null"],
    "properties": {
        "sources": {"type": "array", "items": _source_ref},
        "note": {"type": ["string", "null"]},
    },
    "additionalProperties": False,
}

_changelog_entry = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "date": {"type": "string", "format": "date"},
        "change": {"type": "string"},
        "migration": {"type": ["string", "null"]},
    },
    "required": ["version", "date", "change"],
    "additionalProperties": False,
}

_release = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "edition": {"type": "string"},
        "publication_date": {"type": "string", "format": "date"},
        "checksum_sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
        "source_workbook": {"type": "string"},
        "extraction_tool_version": {"type": "string"},
        "supersedes": {"type": ["string", "null"]},
        "changelog": {"type": "array", "items": _changelog_entry},
    },
    "required": [
        "id",
        "edition",
        "publication_date",
        "checksum_sha256",
        "source_workbook",
        "extraction_tool_version",
    ],
    "additionalProperties": False,
}

_room_use = {
    "type": "object",
    "properties": {
        "nutzid": {"type": "integer", "minimum": 1, "maximum": 45},
        "code": {"type": "string", "minLength": 1},
        "category": {"type": "integer", "minimum": 1, "maximum": 12},
        "name": _trilingual,
        "sia_clause": {"type": ["string", "null"]},
    },
    "required": ["nutzid", "code", "category", "name"],
    "additionalProperties": False,
}

_parameter = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "label": _trilingual,
        "symbol": {"type": "string"},
        "unit": {"type": "string"},
        "data_type": {"enum": ["number", "enum", "text", "bool"]},
        "category": {"type": "string"},
        "value_kinds": {"type": "array", "items": {"enum": ["standard", "zielwert", "bestand"]}},
        "export_flag": {"type": "boolean"},
        "display_flag": {"type": "boolean"},
        "internal_heat_flag": {"type": "boolean"},
        "qhc_flag": {"type": "boolean"},
        "provenance": _provenance,
    },
    "required": ["id", "label", "symbol", "unit", "data_type", "category", "value_kinds"],
    "additionalProperties": False,
}

_profile = {
    "type": "object",
    "properties": {
        "nutzid": {"type": "integer", "minimum": 1, "maximum": 45},
        "values": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": _quantity,
            },
        },
    },
    "required": ["nutzid", "values"],
    "additionalProperties": False,
}

_hourly_profile = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "profile_type": {"enum": ["person", "device", "lighting", "ventilation"]},
        "values": {"type": "array", "items": {"type": "number"}, "minItems": 24, "maxItems": 24},
        "unit": {"type": "string"},
        "provenance": _provenance,
    },
    "required": ["id", "profile_type", "values", "unit"],
    "additionalProperties": False,
}

_monthly_profile = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "values": {"type": "array", "items": {"type": "number"}, "minItems": 12, "maxItems": 12},
        "unit": {"type": "string"},
        "provenance": _provenance,
    },
    "required": ["id", "values", "unit"],
    "additionalProperties": False,
}

_weekly_profile = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "values": {"type": "array", "items": {"type": "number"}, "minItems": 7, "maxItems": 7},
        "unit": {"type": "string"},
        "provenance": _provenance,
    },
    "required": ["id", "values", "unit"],
    "additionalProperties": False,
}

_room_use_schedule = {
    "type": "object",
    "properties": {
        "room_use_id": {"type": "integer", "minimum": 1},
        "person_fraction": {
            "type": "array",
            "items": {"type": "number", "minimum": 0, "maximum": 1},
            "minItems": 24,
            "maxItems": 24,
        },
        "device_fraction": {
            "type": "array",
            "items": {"type": "number", "minimum": 0, "maximum": 1},
            "minItems": 24,
            "maxItems": 24,
        },
        "weekly_fraction": {
            "type": "array",
            "items": {"type": "number", "minimum": 0, "maximum": 1},
            "minItems": 7,
            "maxItems": 7,
        },
        "monthly_fraction": {
            "type": "array",
            "items": {"type": "number", "minimum": 0, "maximum": 1},
            "minItems": 12,
            "maxItems": 12,
        },
        "monthly_previous_fraction": {
            "type": "array",
            "items": {"type": "number", "minimum": 0, "maximum": 1},
            "minItems": 12,
            "maxItems": 12,
        },
        "rest_days_per_week": {"type": "number", "minimum": 0, "maximum": 7},
        "working_days_per_year": {"type": ["number", "null"], "minimum": 0},
        "annual_simultaneity": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "provenance": _provenance,
    },
    "required": [
        "room_use_id",
        "person_fraction",
        "device_fraction",
        "weekly_fraction",
        "monthly_fraction",
        "monthly_previous_fraction",
        "rest_days_per_week",
    ],
    "additionalProperties": False,
}

_room_use_inputs = {
    "type": "object",
    "properties": {
        "room_use_id": {"type": "integer", "minimum": 1},
        "fensteranteil": {"type": "number"},
        "solar_reduction_factor": {"type": "number"},
        "shading_radiation_threshold": {"type": "number"},
        "klimatisierung": {"type": "boolean"},
        "klimatisierung_kategorie": {"type": "string"},
        "schallschutz_key": {"type": "number"},
        "schallschutz_geraete_db": {"type": "number"},
        "schallschutz_nutzung_db": {"type": "number"},
        "sensible_waerme_kuehlfall": {"type": "number"},
        "sensible_waerme_heizfall": {"type": "number"},
        "k0_korrektur": {"type": "number"},
        "praesenzart": {"type": "string"},
        "ida_kategorie": {"type": "string"},
        "aussenluft_volumenstrom": {"type": "number"},
        "cooling_necessity": {"type": "string"},
        "tagesprofil_typ": {"type": "string"},
        "monatsprofil_typ": {"type": "string"},
        "qh_li0": {"type": "number"},
        "dqh_li": {"type": "number"},
        "huellzahl": {"type": "number"},
        "qh_lim": {"type": "number"},
        "provenance": _provenance,
    },
    "required": ["room_use_id"],
    "additionalProperties": False,
}

_temperature_bin = {    "type": "object",
    "properties": {
        "lower": {"type": "number"},
        "upper": {"type": "number"},
        "hours": {"type": "number", "minimum": 0},
    },
    "required": ["lower", "upper", "hours"],
    "additionalProperties": False,
}

_design_day_series = {
    "type": "object",
    "properties": {
        "month": {"enum": [6, 8]},
        "temperature": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 96,
            "maxItems": 96,
        },
        "relative_humidity": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 96,
            "maxItems": 96,
        },
        "radiation": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 96,
            "maxItems": 96,
        },
        "provenance": _provenance,
    },
    "required": ["month", "temperature", "relative_humidity", "radiation"],
    "additionalProperties": False,
}

_climate_station = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "minimum": 1, "maximum": 40},
        "name": _trilingual,
        "winter_design": {"type": "object", "additionalProperties": _quantity},
        "summer_design": {"type": "object", "additionalProperties": _quantity},
        "monthly": {"type": "object", "additionalProperties": _monthly_profile},
        "temperature_bins": {
            "type": ["array", "null"],
            "items": _temperature_bin,
        },
        "bin_humidity_ratio": {
            "type": ["array", "null"],
            "items": {"type": "number", "minimum": 0},
            "minItems": 1,
        },
        "hdd": _quantity,
        "canton": {"type": ["string", "null"]},
        "wind_direction": {"type": ["string", "null"]},
        "trub_wind_direction": {"type": ["string", "null"]},
        "design_days": {"type": "array", "items": _design_day_series},
        "provenance": _provenance,
    },
    "required": ["id", "name", "winter_design", "summer_design", "monthly"],
    "additionalProperties": False,
}

_climate = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "minLength": 1},
        "source": {"type": ["string", "null"]},
        "stations": {"type": "array", "items": _climate_station, "minItems": 1},
    },
    "required": ["version", "stations"],
    "additionalProperties": False,
}

_full_load_hours = {
    "type": "object",
    "properties": {
        "standard_versions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "regulations": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        # Default (final/latest) standard version; optional so packages that
        # predate the field stay valid (their single version is used instead).
        "default_standard_version": {"type": "string"},
        "rows": {"type": "object", "additionalProperties": {"type": "number", "minimum": 0}},
        "electrical": {
            "type": "object",
            "additionalProperties": {"type": "number", "minimum": 0},
        },
        "stage_hours": {
            "type": "object",
            "additionalProperties": {"type": "number", "minimum": 0},
        },
        "provenance": _provenance,
    },
    "required": ["standard_versions", "regulations", "rows"],
    "additionalProperties": False,
}

_qhc = {
    "type": "object",
    "properties": {
        "rows": {"type": "object", "additionalProperties": _quantity},
        "cooling_power": {"type": "object", "additionalProperties": _quantity},
        "heating_load": {"type": "object", "additionalProperties": _quantity},
        "heating_energy": {"type": "object", "additionalProperties": _quantity},
        "provenance": _provenance,
    },
    "required": ["rows"],
    "additionalProperties": False,
}

_sia3801_result = {
    "type": "object",
    "properties": {
        "room_use_id": {"type": "integer"},
        "station_id": {"type": "integer"},
        "kind": {"enum": ["standard", "zielwert", "bestand"]},
        "variant": {"enum": ["de", "en", "de+qc", "en+qc"]},
        "values": {"type": "object", "additionalProperties": _quantity},
        "provenance": _provenance,
    },
    "required": ["room_use_id", "station_id", "kind", "variant", "values"],
    "additionalProperties": False,
}

_mapping = {
    "type": "object",
    "properties": {
        "sia3801_category": {"type": "string"},
        "room_use_codes": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "name": {"anyOf": [_trilingual, {"type": "null"}]},
        "provenance": _provenance,
    },
    "required": ["sia3801_category", "room_use_codes"],
    "additionalProperties": False,
}

_area_table = {
    "type": "object",
    "properties": {
        "kind": {"enum": ["standard", "zielwert", "bestand"]},
        "rows": {
            "type": "object",
            "additionalProperties": {"type": "object", "additionalProperties": _quantity},
        },
        "provenance": _provenance,
    },
    "required": ["kind", "rows"],
    "additionalProperties": False,
}

_coefficients = {
    "type": "object",
    "properties": {
        "variant": {"enum": ["de", "en", "de+qc", "en+qc"]},
        "category": {"type": "string"},
        "coefficients": {"type": "object", "additionalProperties": _quantity},
        "provenance": _provenance,
    },
    "required": ["variant", "category", "coefficients"],
    "additionalProperties": False,
}

_category_table = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "minLength": 1},
        "variant": {"type": "string", "minLength": 1},
        "unit": {"type": "string"},
        "rows": {
            "type": "object",
            "additionalProperties": {"type": "object", "additionalProperties": _quantity},
        },
        "provenance": _provenance,
    },
    "required": ["kind", "variant", "unit", "rows"],
    "additionalProperties": False,
}

PACKAGE_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://energytools.refactored.ch/schemas/raumdaten-package-1.0.schema.json",
    "title": "energytools Raumdaten dataset package",
    "description": (
        "Canonical JSON package of one Raumdaten dataset release (V221 ...): release "
        "metadata plus every table of the canonical dataset.  Row maps use '|'-separated "
        "string keys ('nutzid|regulation|standard_version', 'nutzid|station_id|kind')."
    ),
    "type": "object",
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "source_checksum_sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
        "release": _release,
        "room_uses": {"type": "array", "items": _room_use, "minItems": 1},
        "parameters": {"type": "array", "items": _parameter, "minItems": 1},
        "profiles": {"type": "array", "items": _profile, "minItems": 1},
        "room_use_schedules": {"type": "array", "items": _room_use_schedule},
        "room_use_inputs": {"type": "array", "items": _room_use_inputs},
        "sia2028_monthly": {
            "type": ["object", "null"],
            "properties": {
                "temperature": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 12,
                    "maxItems": 12,
                },
                "relative_humidity": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 12,
                    "maxItems": 12,
                },
                "provenance": _provenance,
            },
            "required": ["temperature", "relative_humidity"],
            "additionalProperties": False,
        },
        "hourly_profiles": {"type": "array", "items": _hourly_profile},
        "monthly_profiles": {"type": "array", "items": _monthly_profile},
        "weekly_profiles": {"type": "array", "items": _weekly_profile},
        "climate": _climate,
        "full_load_hours": _full_load_hours,
        "qhc": _qhc,
        "sia3801": {"type": "array", "items": _sia3801_result},
        "mappings": {"type": "array", "items": _mapping},
        "area_tables": {"type": "array", "items": _area_table},
        "sia3801_coefficients": {"type": "array", "items": _coefficients},
        "category_tables": {"type": "array", "items": _category_table},
    },
    "required": [
        "schema_version",
        "release",
        "room_uses",
        "parameters",
        "profiles",
        "hourly_profiles",
        "monthly_profiles",
        "weekly_profiles",
        "climate",
        "full_load_hours",
        "qhc",
        "sia3801",
        "mappings",
        "area_tables",
        "sia3801_coefficients",
    ],
    "additionalProperties": False,
    "$defs": {
        "provenance": _provenance,
        "quantity": _quantity,
        "trilingual": _trilingual,
    },
}
