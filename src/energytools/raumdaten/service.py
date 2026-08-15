"""energytools.raumdaten.service -- read-only semantic query API (API reference part 03, section 3).

:class:`RaumdatenService` is the **read-only semantic query API** over the
canonical dataset (assessment 6.1).  One service instance = one
:class:`DatasetStore` + one :class:`VersionResolver`.  All methods take
``release_id`` explicitly (never "whatever is loaded") and return domain
objects or JSON-ready dicts; none exposes Excel addresses.  This class is the
single dependency of the FastAPI datasets router and the MCP data tools.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import energytools
from energytools.common.errors import ExportError
from energytools.common.language import Language, TrilingualText
from energytools.common.valuekind import ValueKind
from energytools.common.versioning import VersionResolver
from energytools.raumdaten.compare import compare_profiles
from energytools.raumdaten.dataset import DatasetStore
from energytools.raumdaten.model import Dataset

__all__ = ["RaumdatenService"]

_SIA3801_VARIANTS = ("de", "en", "de+qc", "en+qc")
_EXPORT_FORMATS = ("json", "csv", "xlsx", "pdf")
_EXPORT_SCOPES = ("room-uses", "profiles", "climate", "full-load-hours", "qhc", "all")


def _climate_version_from_manifest(dataset_dir: str, release_id: str) -> str | None:
    """Read the climate data version from an installed package manifest (cheap metadata read)."""
    try:
        data = json.loads(
            (Path(dataset_dir) / release_id / "package.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None
    climate = data.get("climate")
    if isinstance(climate, dict):
        return climate.get("version")
    return None


class RaumdatenService:
    """Read-only semantic query API over the canonical dataset.

    Args:
        store: The dataset store (defaults to the configured dataset directory).
        resolver: The version resolver (defaults to one built from the installed
            releases of ``store``; ``"latest"`` is resolved against it).
    """

    def __init__(
        self, store: DatasetStore | None = None, resolver: VersionResolver | None = None
    ) -> None:
        self.store = store or DatasetStore()
        if resolver is None:
            releases = self.store.list()
            resolver = VersionResolver(
                datasets={release.id: release for release in releases},
                models={},
                implementation_version=energytools.__version__,
                climate_versions={
                    release.id: version
                    for release in releases
                    if (
                        version := _climate_version_from_manifest(
                            self.store.dataset_dir, release.id
                        )
                    )
                },
            )
        self.resolver = resolver

    # -- helpers ------------------------------------------------------------

    def _dataset(self, release_id: str) -> Dataset:
        return self.store.get(release_id)

    @staticmethod
    def _language(language: Language | str) -> Language:
        return language if isinstance(language, Language) else Language.parse(language)

    @staticmethod
    def _value_kind(value_kind: ValueKind | str | None) -> ValueKind | None:
        if value_kind is None:
            return None
        return value_kind if isinstance(value_kind, ValueKind) else ValueKind.parse(value_kind)

    @staticmethod
    def _localized(text: TrilingualText, language: Language) -> str:
        return text.get(language)

    # -- releases -----------------------------------------------------------

    def list_releases(self) -> list[dict]:
        """List dataset releases (id, edition, date, checksum, supersedes), newest first."""
        return [
            {
                "id": release.id,
                "edition": release.edition,
                "publication_date": release.publication_date.isoformat(),
                "checksum_sha256": release.checksum_sha256,
                "supersedes": release.supersedes,
            }
            for release in self.resolver.list_datasets()
        ]

    def get_release(self, release_id: str) -> dict:
        """Full release metadata incl. changelog (alias ``"latest"`` allowed).

        Raises:
            DatasetNotFoundError: unknown release id.
        """
        release = self.resolver.resolve_dataset(release_id)
        return {
            "id": release.id,
            "edition": release.edition,
            "publication_date": release.publication_date.isoformat(),
            "checksum_sha256": release.checksum_sha256,
            "source_workbook": release.source_workbook,
            "extraction_tool_version": release.extraction_tool_version,
            "supersedes": release.supersedes,
            "changelog": [
                {
                    "version": entry.version,
                    "date": entry.date.isoformat(),
                    "change": entry.change,
                    "migration": entry.migration,
                }
                for entry in release.changelog
            ],
        }

    # -- room uses ----------------------------------------------------------

    def list_room_uses(self, release_id: str, language: Language | str = Language.DE) -> list[dict]:
        """The room uses with id, code, category and localized name (dropdown/selector data).

        Raises:
            DatasetNotFoundError, UnknownLanguageError.
        """
        lang = self._language(language)
        dataset = self._dataset(release_id)
        return [
            {
                "nutzid": room_use.nutzid,
                "code": room_use.code,
                "category": room_use.category,
                "name": room_use.name.get(lang),
            }
            for room_use in dataset.room_uses()
        ]

    def get_room_use(self, release_id: str, room_use_id: int | str) -> dict:
        """One room use (all languages).

        Raises:
            DatasetNotFoundError, UnknownRoomUseError.
        """
        dataset = self._dataset(release_id)
        return dataset.room_use(room_use_id).as_dict()

    def get_room_use_profile(
        self,
        release_id: str,
        room_use_id: int | str,
        value_kind: ValueKind | str | None = None,
    ) -> dict:
        """The full data-sheet content of one room use: all parameters per kind.

        Raises:
            DatasetNotFoundError, UnknownRoomUseError, UnknownValueKindError.
        """
        dataset = self._dataset(release_id)
        room_use = dataset.room_use(room_use_id)
        profile = dataset.profile(room_use.nutzid)
        kind = self._value_kind(value_kind)
        return profile.as_dict(kind=kind)

    # -- parameters ---------------------------------------------------------

    def list_parameters(
        self, release_id: str, language: Language | str = Language.DE
    ) -> list[dict]:
        """The parameter catalog (clause ids, labels, symbols, units, types, categories, flags).

        Raises:
            DatasetNotFoundError, UnknownLanguageError.
        """
        lang = self._language(language)
        dataset = self._dataset(release_id)
        return [
            {
                "id": parameter.id,
                "label": parameter.label.get(lang),
                "symbol": parameter.symbol,
                "unit": parameter.unit.symbol,
                "data_type": parameter.data_type,
                "category": parameter.category,
                "value_kinds": sorted(kind.value for kind in parameter.value_kinds),
                "export_flag": parameter.export_flag,
                "display_flag": parameter.display_flag,
                "internal_heat_flag": parameter.internal_heat_flag,
                "qhc_flag": parameter.qhc_flag,
            }
            for parameter in dataset.parameters()
        ]

    def get_parameter(self, release_id: str, parameter_id: str) -> dict:
        """One parameter incl. applicable value kinds and flags.

        Raises:
            DatasetNotFoundError, UnknownParameterError.
        """
        dataset = self._dataset(release_id)
        return dataset.parameter(parameter_id).as_dict()

    # -- comparison ---------------------------------------------------------

    def compare_room_use_profiles(self, release_id: str, a: int | str, b: int | str) -> dict:
        """Compare two room-use profiles: per-parameter diffs across all value kinds.

        Raises:
            DatasetNotFoundError, UnknownRoomUseError.
        """
        dataset = self._dataset(release_id)
        profile_a = dataset.profile(dataset.room_use(a).nutzid)
        profile_b = dataset.profile(dataset.room_use(b).nutzid)
        return compare_profiles(profile_a, profile_b).as_dict()

    # -- climate ------------------------------------------------------------

    def list_climate_stations(
        self, release_id: str, language: Language | str = Language.DE
    ) -> list[dict]:
        """The stations with ids and names.

        Raises:
            DatasetNotFoundError, UnknownLanguageError.
        """
        lang = self._language(language)
        dataset = self._dataset(release_id)
        return [
            {"id": station.id, "name": station.name.get(lang)}
            for station in dataset.climate().stations
        ]

    def get_climate_station(self, release_id: str, station_id: int | str) -> dict:
        """Full station data (winter/summer design, monthly values, bins, HDD).

        Raises:
            DatasetNotFoundError, UnknownClimateStationError.
        """
        dataset = self._dataset(release_id)
        station = dataset.climate().station(station_id)
        return station.as_dict()

    # -- profiles -----------------------------------------------------------

    def list_profiles(self, release_id: str) -> dict:
        """Hourly/monthly/weekly profile sets.

        Raises:
            DatasetNotFoundError.
        """
        dataset = self._dataset(release_id)
        return {
            "hourly": [profile.as_dict() for profile in dataset.hourly_profiles],
            "monthly": [profile.as_dict() for profile in dataset.monthly_profiles],
            "weekly": [profile.as_dict() for profile in dataset.weekly_profiles],
        }

    # -- tables -------------------------------------------------------------

    def get_full_load_hours(
        self, release_id: str, room_use_id: int | str, regulation: str, standard_version: str
    ) -> dict:
        """Ventilation full-load hours for one use x regulation x standard version.

        Raises:
            DatasetNotFoundError, UnknownRoomUseError, TableLookupError.
        """
        dataset = self._dataset(release_id)
        room_use = dataset.room_use(room_use_id)
        hours = dataset.full_load_hours().hours(room_use.nutzid, regulation, standard_version)
        return {
            "room_use_id": room_use.nutzid,
            "regulation": regulation,
            "standard_version": standard_version,
            "hours": hours,
            "unit": "h/a",
            "provenance": _provenance_dict(dataset.full_load_hours().provenance),
        }

    def get_qhc(
        self,
        release_id: str,
        room_use_id: int | str,
        station_id: int | str,
        value_kind: ValueKind | str = ValueKind.STANDARD,
    ) -> dict:
        """Annual cooling energy Qhc for one use x station x kind.

        Raises:
            DatasetNotFoundError, UnknownRoomUseError, UnknownClimateStationError,
            UnknownValueKindError, TableLookupError.
        """
        dataset = self._dataset(release_id)
        room_use = dataset.room_use(room_use_id)
        kind = self._value_kind(value_kind) or ValueKind.STANDARD
        try:
            station_id_int = int(station_id)
        except (TypeError, ValueError):
            from energytools.common.errors import UnknownClimateStationError

            raise UnknownClimateStationError(station_id, release_id) from None
        qhc = dataset.qhc().qhc(room_use.nutzid, station_id_int, kind)
        return {
            "room_use_id": room_use.nutzid,
            "station_id": station_id_int,
            "kind": kind.value,
            "qhc": qhc.as_dict(),
            "provenance": _provenance_dict(dataset.qhc().provenance),
        }

    def get_sia3801(self, release_id: str, room_use_id: int | str, variant: str = "de") -> dict:
        """SIA 380/1 result (incl. Qc variant) of one room use.

        Raises:
            DatasetNotFoundError, UnknownRoomUseError, TableLookupError (no
            result for the requested variant).
        """
        dataset = self._dataset(release_id)
        room_use = dataset.room_use(room_use_id)
        results = dataset.sia3801_results(variant)
        result = next((r for r in results if r.room_use_id == room_use.nutzid), None)
        if result is None:
            from energytools.common.errors import TableLookupError

            raise TableLookupError(
                f"no SIA 380/1 result for room use {room_use.nutzid} / variant '{variant}' "
                f"in release '{release_id}'"
            )
        return {
            "room_use_id": result.room_use_id,
            "station_id": result.station_id,
            "kind": result.kind.value,
            "variant": result.variant,
            "values": {key: quantity.as_dict() for key, quantity in result.values.items()},
            "provenance": _provenance_dict(result.provenance),
        }

    # -- validation & export ------------------------------------------------

    def validate(self, release_id: str) -> dict:
        """Validation report of a release (schema + value rules).

        Raises:
            DatasetNotFoundError.
        """
        dataset = self._dataset(release_id)
        report = dataset.validate()
        return {
            "release_id": release_id,
            "valid": report.valid,
            "errors": list(report.errors),
            "warnings": list(report.warnings),
        }

    def export(self, release_id: str, fmt: str, scope: str, target: str) -> dict:
        """Bulk export of a release.

        ``fmt="json"`` is fully supported (the canonical package, scoped);
        ``csv``/``xlsx``/``pdf`` raise :class:`ExportError` until the export
        layer (part 05) lands.

        Raises:
            DatasetNotFoundError, ExportError.
        """
        dataset = self._dataset(release_id)
        if fmt not in _EXPORT_FORMATS:
            raise ExportError(
                f"unsupported export format '{fmt}' (expected one of {', '.join(_EXPORT_FORMATS)})",
                {"format": fmt},
            )
        if scope not in _EXPORT_SCOPES:
            raise ExportError(
                f"unsupported export scope '{scope}' (expected one of {', '.join(_EXPORT_SCOPES)})",
                {"scope": scope},
            )
        if fmt != "json":
            raise ExportError(
                f"export format '{fmt}' is not available yet: the export layer "
                f"(energytools.export, part 05) is not implemented",
                {"format": fmt, "target": target},
            )
        payload = _scoped_package(dataset, scope)
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        target_path = Path(target)
        target_path.write_text(content, encoding="utf-8")
        return {
            "release_id": release_id,
            "format": fmt,
            "scope": scope,
            "target": str(target_path),
            "bytes": len(content.encode("utf-8")),
            "checksum": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }


def _provenance_dict(provenance: Any) -> dict | None:
    if provenance is None:
        return None
    return provenance.as_dict()


def _scoped_package(dataset: Dataset, scope: str) -> dict:
    """The canonical package dict, restricted to one export scope."""
    package = dataset.to_package_dict()
    if scope == "all":
        return package
    keys = {
        "room-uses": ("room_uses",),
        "profiles": ("profiles", "hourly_profiles", "monthly_profiles", "weekly_profiles"),
        "climate": ("climate",),
        "full-load-hours": ("full_load_hours",),
        "qhc": ("qhc",),
    }[scope]
    return {
        "schema_version": package["schema_version"],
        "release": package["release"],
        **{key: package[key] for key in keys},
    }
