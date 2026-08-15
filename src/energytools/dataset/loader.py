"""Loading of Raumdaten dataset packages for ``energytools.dataset``.

A dataset package is a JSON document with the canonical shape produced by
:meth:`~energytools.dataset.model.Dataset.as_dict` (a ``release`` metadata
object plus the ``room_uses``, ``parameters``, ``profiles`` and
``climate_stations`` tables). :func:`load_dataset` loads one explicit file and
raises on a corrupt/foreign package — it is never half-loaded
(docs/architecture+api-reference/03-raumdaten-service.md §2.1).
:func:`load_datasets` discovers all ``*.json`` files of a directory in the
style of ``VersionResolver.from_installed`` (sorted, invalid files skipped and
recorded, never crashing); missing directories yield an empty collection.

The release metadata reuses :class:`~energytools.common.versioning.DatasetRelease`
from ``energytools.common.versioning``. Package integrity is tracked via
:func:`compute_package_checksum`: the SHA-256 of the canonical package content
with the declared checksum field excluded (self-referential exclusion, the same
trick git uses), so a package can truthfully declare its own checksum.
"""

from __future__ import annotations

import builtins
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from energytools.common.errors import DatasetNotFoundError, UnitError, UnknownValueKindError
from energytools.common.language import TrilingualText
from energytools.common.provenance import Provenance, SourceRef
from energytools.common.units import Quantity
from energytools.common.valuekind import ValueKind
from energytools.common.versioning import ChangelogEntry, DatasetRelease
from energytools.dataset.errors import DatasetError, LoadError, NotFoundError, ValidationError
from energytools.dataset.model import (
    ClimateStation,
    Dataset,
    Parameter,
    ParameterValue,
    RoomUse,
    RoomUseProfile,
    compute_package_checksum,
)

__all__ = [
    "DatasetCollection",
    "SkippedFile",
    "compute_package_checksum",
    "load_dataset",
    "load_datasets",
    "parse_dataset",
]


# ---------------------------------------------------------------------------
# Low-level parsers (collect problems instead of raising)
# ---------------------------------------------------------------------------


def _parse_trilingual(raw: Any, problems: list[str], context: str) -> TrilingualText | None:
    """Parse a name/label as ``{"de": ..., "fr": ..., "it": ...}`` or a bare string."""
    if isinstance(raw, str):
        return TrilingualText(de=raw)
    if isinstance(raw, dict):
        return TrilingualText(
            de=str(raw.get("de", "")),
            fr=str(raw.get("fr", "")),
            it=str(raw.get("it", "")),
        )
    problems.append(f"{context}: missing or invalid name/label (expected object or string)")
    return None


def _parse_provenance(raw: Any, problems: list[str], context: str) -> Provenance | None:
    """Parse an optional provenance object; ``None`` when absent."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        problems.append(f"{context}: provenance must be an object")
        return None
    note = raw.get("note") if isinstance(raw.get("note"), str) else None
    sources: list[SourceRef] = []
    raw_sources = raw.get("sources", [])
    if not isinstance(raw_sources, list):
        problems.append(f"{context}: provenance.sources must be a list")
        return None
    for index, source_raw in enumerate(raw_sources):
        source_context = f"{context}.sources[{index}]"
        if not isinstance(source_raw, dict):
            problems.append(f"{source_context}: must be an object")
            continue
        try:
            sources.append(
                SourceRef(
                    workbook=str(source_raw.get("workbook", "")),
                    sheet=str(source_raw.get("sheet", "")),
                    range=source_raw.get("range"),
                    formula=source_raw.get("formula"),
                    cached_value=source_raw.get("cached_value"),
                    extraction_hash=source_raw.get("extraction_hash"),
                )
            )
        except ValueError as exc:
            problems.append(f"{source_context}: {exc}")
    return Provenance(sources=tuple(sources), note=note)


def _parse_quantity(raw: Any, problems: list[str], context: str) -> Quantity | None:
    """Parse a ``{"value": ..., "unit": ...}`` quantity."""
    if not isinstance(raw, dict):
        problems.append(f"{context}: quantity must be an object")
        return None
    unit_raw = raw.get("unit")
    if not isinstance(unit_raw, str) or not unit_raw.strip():
        problems.append(f"{context}: missing required field 'unit'")
        return None
    try:
        return Quantity(raw.get("value"), unit_raw)
    except UnitError as exc:
        problems.append(f"{context}: {exc}")
        return None


def _parse_quantity_map(raw: Any, problems: list[str], context: str) -> dict[str, Quantity]:
    """Parse a mapping of quantity objects (design values, monthly values)."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        problems.append(f"{context}: must be an object")
        return {}
    result: dict[str, Quantity] = {}
    for key, quantity_raw in raw.items():
        quantity = _parse_quantity(quantity_raw, problems, f"{context}.{key}")
        if quantity is not None:
            result[str(key)] = quantity
    return result


def _parse_release(
    raw: Any, fallback_id: str, problems: list[str]
) -> DatasetRelease | None:
    """Parse the release metadata into a common :class:`DatasetRelease`."""
    context = "release"
    if not isinstance(raw, dict):
        problems.append(f"{context}: must be a JSON object")
        return None
    release_id = raw.get("id")
    if not isinstance(release_id, str) or not release_id.strip():
        release_id = fallback_id
    raw_date = raw.get("publication_date")
    if not isinstance(raw_date, str):
        problems.append(f"{context}: missing required field 'publication_date'")
        return None
    try:
        publication_date = date.fromisoformat(raw_date)
    except ValueError:
        problems.append(f"{context}: publication_date must be an ISO date string")
        return None
    changelog: list[ChangelogEntry] = []
    for index, entry_raw in enumerate(raw.get("changelog", [])):
        entry_context = f"{context}.changelog[{index}]"
        if not isinstance(entry_raw, dict):
            problems.append(f"{entry_context}: must be an object")
            continue
        try:
            changelog.append(
                ChangelogEntry(
                    version=str(entry_raw["version"]),
                    date=date.fromisoformat(entry_raw["date"]),
                    change=str(entry_raw["change"]),
                    migration=entry_raw.get("migration"),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            problems.append(f"{entry_context}: invalid changelog entry ({exc})")
    try:
        return DatasetRelease(
            id=release_id,
            edition=raw["edition"],
            publication_date=publication_date,
            checksum_sha256=raw["checksum_sha256"],
            source_workbook=raw["source_workbook"],
            extraction_tool_version=raw["extraction_tool_version"],
            changelog=tuple(changelog),
            supersedes=raw.get("supersedes"),
        )
    except KeyError as exc:
        problems.append(f"{context}: missing required field {exc.args[0]!r}")
        return None
    except ValueError as exc:
        problems.append(f"{context}: {exc}")
        return None


def _parse_room_use(raw: Any, problems: list[str], index: int) -> RoomUse | None:
    """Parse one room use; ``None`` and a problem message on failure."""
    context = f"room_uses[{index}]"
    if not isinstance(raw, dict):
        problems.append(f"{context}: must be a JSON object")
        return None
    name = _parse_trilingual(raw.get("name"), problems, context)
    if name is None:
        return None
    sia_clause = raw.get("sia_clause")
    if sia_clause is not None and not isinstance(sia_clause, str):
        problems.append(f"{context}: sia_clause must be a string")
        return None
    try:
        return RoomUse(
            nutzid=raw["nutzid"],
            code=raw["code"],
            category=raw["category"],
            name=name,
            sia_clause=sia_clause,
        )
    except KeyError as exc:
        problems.append(f"{context}: missing required field {exc.args[0]!r}")
        return None
    except ValueError as exc:
        problems.append(f"{context}: {exc}")
        return None


def _parse_parameter(raw: Any, problems: list[str], index: int) -> Parameter | None:
    """Parse one parameter; ``None`` and a problem message on failure."""
    context = f"parameters[{index}]"
    if not isinstance(raw, dict):
        problems.append(f"{context}: must be a JSON object")
        return None
    label = _parse_trilingual(raw.get("label"), problems, context)
    if label is None:
        return None
    value_kinds_raw = raw.get("value_kinds")
    if not isinstance(value_kinds_raw, list):
        problems.append(f"{context}: missing or invalid required field 'value_kinds'")
        return None
    value_kinds: set[ValueKind] = set()
    for kind_name in value_kinds_raw:
        try:
            value_kinds.add(ValueKind.parse(kind_name))
        except UnknownValueKindError:
            problems.append(f"{context}: unknown value kind {kind_name!r}")
            return None
    provenance = _parse_provenance(raw.get("provenance"), problems, context)
    try:
        return Parameter(
            id=raw["id"],
            label=label,
            symbol=raw["symbol"],
            unit=raw["unit"],
            data_type=raw["data_type"],
            category=raw["category"],
            value_kinds=frozenset(value_kinds),
            export_flag=raw.get("export_flag", True),
            display_flag=raw.get("display_flag", True),
            internal_heat_flag=raw.get("internal_heat_flag", False),
            qhc_flag=raw.get("qhc_flag", False),
            provenance=provenance,
        )
    except KeyError as exc:
        problems.append(f"{context}: missing required field {exc.args[0]!r}")
        return None
    except (UnitError, ValueError) as exc:
        problems.append(f"{context}: {exc}")
        return None


def _parse_parameter_value(
    raw: Any,
    parameter_id: str,
    kind: ValueKind,
    problems: list[str],
    context: str,
) -> ParameterValue | None:
    """Parse one ``{"value": ..., "unit": ...}`` parameter value."""
    if not isinstance(raw, dict):
        problems.append(f"{context}: value must be an object")
        return None
    unit_raw = raw.get("unit")
    if not isinstance(unit_raw, str) or not unit_raw.strip():
        problems.append(f"{context}: missing required field 'unit'")
        return None
    value = raw.get("value")
    if value is not None and not isinstance(value, (bool, int, float, str)):
        problems.append(
            f"{context}: unsupported value type {type(value).__name__} "
            "(expected number, string, bool or null)"
        )
        return None
    provenance = _parse_provenance(raw.get("provenance"), problems, context)
    try:
        return ParameterValue(
            parameter_id=parameter_id,
            kind=kind,
            value=value,
            unit=unit_raw,
            provenance=provenance,
        )
    except UnitError as exc:
        problems.append(f"{context}: {exc}")
        return None


def _parse_profile(
    raw: Any,
    room_uses_by_nutzid: dict[int, RoomUse],
    catalog: dict[str, Parameter],
    release_id: str,
    problems: list[str],
    index: int,
) -> tuple[int, RoomUseProfile] | None:
    """Parse one room-use profile; ``None`` and a problem message on failure."""
    context = f"profiles[{index}]"
    if not isinstance(raw, dict):
        problems.append(f"{context}: must be a JSON object")
        return None
    nutzid = raw.get("room_use_id")
    if isinstance(nutzid, bool) or not isinstance(nutzid, int):
        problems.append(f"{context}: room_use_id must be an int")
        return None
    room_use = room_uses_by_nutzid.get(nutzid)
    if room_use is None:
        problems.append(f"{context}: unknown room_use_id {nutzid!r}")
        return None
    values_raw = raw.get("values")
    if not isinstance(values_raw, dict):
        problems.append(f"{context}: missing required field 'values'")
        return None
    values: dict[str, dict[ValueKind, ParameterValue]] = {}
    for parameter_id, kinds_raw in values_raw.items():
        if parameter_id not in catalog:
            problems.append(f"{context}: values reference unknown parameter {parameter_id!r}")
            continue
        if not isinstance(kinds_raw, dict):
            problems.append(f"{context}: values[{parameter_id!r}] must be an object")
            continue
        kinds: dict[ValueKind, ParameterValue] = {}
        for kind_name, value_raw in kinds_raw.items():
            try:
                kind = ValueKind.parse(kind_name)
            except UnknownValueKindError:
                problems.append(
                    f"{context}: parameter {parameter_id!r}: unknown value kind {kind_name!r}"
                )
                continue
            value_context = (
                f"{context}: parameter {parameter_id!r}, kind {kind_name!r}"
            )
            parameter_value = _parse_parameter_value(
                value_raw, parameter_id, kind, problems, value_context
            )
            if parameter_value is not None:
                kinds[kind] = parameter_value
        values[parameter_id] = kinds
    try:
        profile = RoomUseProfile(
            room_use=room_use,
            values=values,
            parameter_catalog=catalog,
            release_id=release_id,
        )
    except ValueError as exc:
        problems.append(f"{context}: {exc}")
        return None
    return nutzid, profile


def _parse_climate_station(raw: Any, problems: list[str], index: int) -> ClimateStation | None:
    """Parse one climate station; ``None`` and a problem message on failure."""
    context = f"climate_stations[{index}]"
    if not isinstance(raw, dict):
        problems.append(f"{context}: must be a JSON object")
        return None
    name = _parse_trilingual(raw.get("name"), problems, context)
    if name is None:
        return None
    winter_design = _parse_quantity_map(
        raw.get("winter_design"), problems, f"{context}.winter_design"
    )
    summer_design = _parse_quantity_map(
        raw.get("summer_design"), problems, f"{context}.summer_design"
    )
    monthly = _parse_quantity_map(raw.get("monthly"), problems, f"{context}.monthly")
    hdd = _parse_quantity(raw.get("hdd"), problems, f"{context}.hdd") if raw.get("hdd") is not None else None
    provenance = _parse_provenance(raw.get("provenance"), problems, context)
    try:
        return ClimateStation(
            id=raw["id"],
            name=name,
            winter_design=winter_design,
            summer_design=summer_design,
            monthly=monthly,
            hdd=hdd,
            provenance=provenance,
        )
    except KeyError as exc:
        problems.append(f"{context}: missing required field {exc.args[0]!r}")
        return None
    except ValueError as exc:
        problems.append(f"{context}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def parse_dataset(
    package: dict[str, Any],
    source: str = "<memory>",
    content_checksum: str | None = None,
) -> Dataset:
    """Build a :class:`Dataset` from a parsed package dict.

    Raises :class:`ValidationError` (a :class:`DatasetValidationError`) with
    all structural problems when the package is corrupt/foreign — a package is
    never half-loaded. Domain checks (duplicate ids, ...) are *not* run here;
    call :meth:`Dataset.validate` or use :func:`load_dataset`.

    Args:
        package: The parsed package dict (the :meth:`Dataset.as_dict` shape).
        source: Human-readable source name for error messages.
        content_checksum: Precomputed content checksum (see
            :func:`compute_package_checksum`); computed here when omitted.

    Returns:
        The parsed :class:`Dataset`.

    Raises:
        ValidationError: If the package is structurally invalid.
    """
    problems: list[str] = []
    if not isinstance(package, dict):
        raise ValidationError(
            f"dataset package '{source}' must be a JSON object",
            {"source": source, "errors": ["package root must be a JSON object"]},
        )
    fallback_id = Path(source).stem
    release = _parse_release(package.get("release"), fallback_id, problems)
    release_id = release.id if release is not None else fallback_id

    room_uses: list[RoomUse] = []
    for index, raw in enumerate(package.get("room_uses", [])):
        room_use = _parse_room_use(raw, problems, index)
        if room_use is not None:
            room_uses.append(room_use)
    room_uses_by_nutzid = {room_use.nutzid: room_use for room_use in room_uses}

    parameters: list[Parameter] = []
    for index, raw in enumerate(package.get("parameters", [])):
        parameter = _parse_parameter(raw, problems, index)
        if parameter is not None:
            parameters.append(parameter)
    catalog = {parameter.id: parameter for parameter in parameters}

    profiles: dict[int, RoomUseProfile] = {}
    for index, raw in enumerate(package.get("profiles", [])):
        parsed = _parse_profile(
            raw, room_uses_by_nutzid, catalog, release_id, problems, index
        )
        if parsed is not None:
            nutzid, profile = parsed
            profiles[nutzid] = profile

    stations: list[ClimateStation] = []
    for index, raw in enumerate(package.get("climate_stations", [])):
        station = _parse_climate_station(raw, problems, index)
        if station is not None:
            stations.append(station)

    if problems:
        raise ValidationError(
            f"dataset package '{source}' failed validation: {'; '.join(problems)}",
            {"source": source, "errors": problems},
        )

    if content_checksum is None:
        content_checksum = compute_package_checksum(package)
    return Dataset(
        release=release,  # type: ignore[arg-type]  # release is not None when problems is empty
        room_uses=tuple(room_uses),
        parameters=tuple(parameters),
        profiles=profiles,
        climate_stations=tuple(stations),
        content_checksum_sha256=content_checksum,
    )


def load_dataset(path: str | Path) -> Dataset:
    """Load one dataset package file into a validated :class:`Dataset`.

    The package is structurally parsed and domain-validated; a corrupt or
    foreign package raises instead of being half-loaded
    (docs/architecture+api-reference/03-raumdaten-service.md §2.1).

    Args:
        path: Path to a ``*.json`` dataset package.

    Returns:
        The loaded :class:`Dataset` (frozen; its ``content_checksum_sha256``
        reflects the file content).

    Raises:
        NotFoundError: If the file does not exist (also a
            :class:`DatasetNotFoundError`).
        LoadError: If the file cannot be read.
        ValidationError: If the package is not valid JSON or fails structural
            or domain validation (also a :class:`DatasetValidationError`).
    """
    package_path = Path(path)
    if not package_path.exists():
        raise NotFoundError(str(package_path))
    if package_path.is_dir():
        raise LoadError(
            f"'{package_path}' is a directory; use load_datasets() for directory discovery",
            {"path": str(package_path)},
        )
    try:
        package = json.loads(package_path.read_bytes())
    except UnicodeDecodeError as exc:
        raise ValidationError(
            f"dataset file '{package_path}' is not valid UTF-8",
            {"path": str(package_path), "errors": [str(exc)]},
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"dataset file '{package_path}' is not valid JSON",
            {
                "path": str(package_path),
                "errors": [f"line {exc.lineno}, column {exc.colno}: {exc.msg}"],
            },
        ) from exc
    except OSError as exc:
        raise LoadError(
            f"cannot read dataset file '{package_path}': {exc}",
            {"path": str(package_path)},
        ) from exc

    dataset = parse_dataset(
        package,
        source=package_path.name,
        content_checksum=compute_package_checksum(package) if isinstance(package, dict) else None,
    )
    report = dataset.validate()
    if not report.valid:
        raise ValidationError(
            f"dataset file '{package_path}' failed validation: "
            f"{'; '.join(report.errors)}",
            {"path": str(package_path), "errors": list(report.errors)},
        )
    return dataset


@dataclass(frozen=True)
class SkippedFile:
    """One file that directory discovery could not load.

    Args:
        path: The file path.
        reason: Human-readable reason (the loader error message).
    """

    path: str
    reason: str


@dataclass(frozen=True)
class DatasetCollection:
    """The result of :func:`load_datasets`: loaded datasets + skipped files.

    Args:
        datasets: The successfully loaded datasets (discovery order, i.e.
            sorted by file name).
        skipped: The files that were skipped, with reasons.
    """

    datasets: tuple[Dataset, ...]
    skipped: tuple[SkippedFile, ...] = ()

    def list(self) -> list[Dataset]:
        """All loaded datasets, newest first (publication date desc, id desc)."""
        return sorted(
            self.datasets,
            key=lambda dataset: (dataset.release.publication_date, dataset.release.id),
            reverse=True,
        )

    def releases(self) -> builtins.list[DatasetRelease]:
        """Release metadata of all loaded datasets, newest first."""
        return [dataset.release for dataset in self.list()]

    def get(self, release_id: str) -> Dataset:
        """One dataset by release id.

        Raises:
            DatasetNotFoundError: If the release id is not loaded.
        """
        for dataset in self.datasets:
            if dataset.release.id == release_id:
                return dataset
        raise DatasetNotFoundError(release_id)


def load_datasets(directory: str | Path) -> DatasetCollection:
    """Discover all dataset packages of a directory (``VersionResolver.from_installed`` style).

    Every ``*.json`` file in the directory (sorted by name) is loaded via
    :func:`load_dataset`; invalid files are skipped and recorded in
    :attr:`DatasetCollection.skipped` instead of crashing the discovery.
    Missing or non-directory paths yield an empty collection (matching the
    ``from_installed`` behaviour of ``energytools.common.versioning``).

    Args:
        directory: The dataset package directory.

    Returns:
        A :class:`DatasetCollection` with the loaded datasets and the skipped
        files.
    """
    directory_path = Path(directory)
    if not directory_path.is_dir():
        return DatasetCollection(datasets=())
    datasets: list[Dataset] = []
    skipped: list[SkippedFile] = []
    for path in sorted(directory_path.glob("*.json")):
        try:
            datasets.append(load_dataset(path))
        except DatasetError as exc:
            skipped.append(SkippedFile(path=str(path), reason=str(exc)))
    return DatasetCollection(datasets=tuple(datasets), skipped=tuple(skipped))
