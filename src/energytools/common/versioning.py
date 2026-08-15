"""Versioning primitives of the energytools library.

Versioning is the backbone of the library: every result, export and API
response references concrete releases, and nothing resolves "latest" silently
at calculation time (assessment §5.1 "released like software"). This module
provides the immutable release value objects (:class:`DatasetRelease`,
:class:`ModelRelease`, :class:`VersionInfo`, :class:`ChangelogEntry`) and the
resolver (:class:`VersionResolver`) that maps user-facing ids and aliases to
concrete releases.

See docs/architecture+api-reference/02-common-foundation.md §2.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from energytools.common.errors import DatasetNotFoundError

__all__ = [
    "DatasetRelease",
    "ModelRelease",
    "VersionInfo",
    "ChangelogEntry",
    "VersionResolver",
]

# Semantic version (https://semver.org): MAJOR.MINOR.PATCH with optional
# pre-release and build metadata. The workbook-derived dataset ids ("V221")
# are *not* semantic and therefore never accepted for models.
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


@dataclass(frozen=True)
class ChangelogEntry:
    """One changelog row of a release.

    Describes what changed between releases and whether the change is a
    breaking migration.

    Args:
        version: The release version this row belongs to (e.g. ``"V221"``).
        date: Date of the change.
        change: What changed (English; workbook terms where applicable).
        migration: Description of the required data migration, if any.
    """

    version: str
    date: date
    change: str
    migration: str | None = None


@dataclass(frozen=True)
class DatasetRelease:
    """Immutable metadata of one Raumdaten dataset package.

    Identifies a release by its human id (``"V221"`` — the workbook version
    convention), the SIA edition it implements, the publication date, the
    content checksum and the extraction fingerprint. ``is_latest`` is computed
    by the resolver, never stored.

    Args:
        id: Human release id, e.g. ``"V221"``.
        edition: SIA edition the release implements, e.g. ``"SIA 2024"``.
        publication_date: Publication date of the package.
        checksum_sha256: SHA-256 checksum of the package file.
        source_workbook: Source workbook file name, e.g.
            ``"2024_Raumdatenblätter_dfi_V221.xlsm"``.
        extraction_tool_version: Version of the extraction tool that produced
            the package.
        changelog: Changelog rows of this release.
        supersedes: Id of the release this one supersedes, if any.

    Raises:
        ValueError: If ``id`` is empty.
    """

    id: str
    edition: str
    publication_date: date
    checksum_sha256: str
    source_workbook: str
    extraction_tool_version: str
    changelog: tuple[ChangelogEntry, ...] = ()
    supersedes: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("DatasetRelease id must not be empty")

    def __lt__(self, other: object) -> bool:
        """Order releases by their id (used to break publication-date ties)."""
        if not isinstance(other, DatasetRelease):
            return NotImplemented
        return self.id < other.id


@dataclass(frozen=True)
class ModelRelease:
    """Immutable metadata of the declarative Gebaeude model definition.

    Declares the dataset releases the model is compatible with, the climate
    data versions it accepts, and a changelog.

    Args:
        id: Semantic version, e.g. ``"1.0.0"``.
        compatible_dataset_releases: Dataset release ids the model supports,
            e.g. ``frozenset({"V221"})``.
        compatible_climate_versions: Climate data versions the model accepts,
            e.g. ``frozenset({"meteoschweiz-2024"})``.
        publication_date: Publication date of the model.
        changelog: Changelog rows of this release.

    Raises:
        ValueError: If ``id`` is not a valid semantic version or either
            compatibility set is empty.
    """

    id: str
    compatible_dataset_releases: frozenset[str]
    compatible_climate_versions: frozenset[str]
    publication_date: date
    changelog: tuple[ChangelogEntry, ...] = ()

    def __post_init__(self) -> None:
        if not _SEMVER_RE.match(self.id):
            raise ValueError(f"ModelRelease id must be a semantic version, got {self.id!r}")
        if not self.compatible_dataset_releases:
            raise ValueError("ModelRelease compatible_dataset_releases must not be empty")
        if not self.compatible_climate_versions:
            raise ValueError("ModelRelease compatible_climate_versions must not be empty")


@dataclass(frozen=True)
class VersionInfo:
    """The version quadruple every calculation result carries.

    ``dataset``, ``model``, ``implementation`` and ``climate`` make results
    reproducible and comparable; the FastAPI ``/versions`` response uses the
    same shape.

    Args:
        dataset: Dataset release id (e.g. ``"V221"``).
        model: Model release id (e.g. ``"1.0.0"``).
        implementation: Library version (PEP 440), e.g. ``"0.1.0"``.
        climate: Climate data version, e.g. ``"meteoschweiz-2024"``.
    """

    dataset: str
    model: str
    implementation: str
    climate: str

    def as_dict(self) -> dict[str, str]:
        """Return the quadruple as a plain dict (API serialization shape)."""
        return {
            "dataset": self.dataset,
            "model": self.model,
            "implementation": self.implementation,
            "climate": self.climate,
        }


def _parse_date(value: Any) -> date:
    """Parse a date from a ``date`` or an ISO ``"YYYY-MM-DD"`` string."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"invalid date value {value!r}")


def _read_release_json(path: Path) -> dict[str, Any] | None:
    """Read one release manifest file; return ``None`` when it is unusable."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _release_from_json(path: Path, kind: str) -> Any | None:
    """Build a release value object from a JSON manifest file, or ``None``."""
    raw = _read_release_json(path)
    if raw is None:
        return None
    data = dict(raw)
    data.setdefault("id", path.stem)
    try:
        data["publication_date"] = _parse_date(data["publication_date"])
        changelog = data.get("changelog", ())
        data["changelog"] = tuple(
            ChangelogEntry(
                version=str(entry["version"]),
                date=_parse_date(entry["date"]),
                change=str(entry["change"]),
                migration=entry.get("migration"),
            )
            for entry in changelog
        )
        if kind == "dataset":
            return DatasetRelease(**data)
        # Accept a bare string as a single-element compatibility set (a
        # hand-written manifest may pass "V221" instead of ["V221"]).
        data["compatible_dataset_releases"] = frozenset(
            {data["compatible_dataset_releases"]}
            if isinstance(data["compatible_dataset_releases"], str)
            else data["compatible_dataset_releases"]
        )
        data["compatible_climate_versions"] = frozenset(
            {data["compatible_climate_versions"]}
            if isinstance(data["compatible_climate_versions"], str)
            else data["compatible_climate_versions"]
        )
        return ModelRelease(**data)
    except (KeyError, TypeError, ValueError):
        return None


def _newest_first(items: list[Any]) -> list[Any]:
    """Sort releases by publication date descending, id descending as tie-break."""
    return sorted(items, key=lambda r: (r.publication_date, r.id), reverse=True)


def _latest(items: Mapping[str, Any], not_found_id: str) -> Any:
    """Return the release with the highest publication date (id as tie-break)."""
    if not items:
        raise DatasetNotFoundError(not_found_id)
    return max(items.values(), key=lambda r: (r.publication_date, r.id))


class VersionResolver:
    """Resolves user-facing release ids and aliases to concrete releases.

    Central place for "what is installed" and "what is current"; used by
    ``RaumdatenService``, ``CalculationEngine``, the FastAPI and MCP layers
    and the CLI. ``"latest"`` resolves by publication date and is meant for
    read/display purposes only — a calculation records the resolved concrete
    ids in its :class:`VersionInfo`.

    Args:
        datasets: Installed dataset releases keyed by id.
        models: Installed model releases keyed by id.
        implementation_version: Library version (PEP 440) reported by
            :meth:`current`, if any.
        climate_versions: Optional mapping of dataset release id to the
            climate-data version it was produced with (used to fill the
            ``climate`` axis of :class:`VersionInfo`).
    """

    def __init__(
        self,
        datasets: Mapping[str, DatasetRelease] | None = None,
        models: Mapping[str, ModelRelease] | None = None,
        implementation_version: str | None = None,
        climate_versions: dict[str, str] | None = None,
    ) -> None:
        self.datasets: Mapping[str, DatasetRelease] = dict(datasets or {})
        self.models: Mapping[str, ModelRelease] = dict(models or {})
        self.implementation_version = implementation_version
        self.climate_versions: dict[str, str] = climate_versions or {}

    @classmethod
    def from_installed(
        cls,
        dataset_dir: str | Path,
        model_dir: str | Path,
        implementation_version: str | None = None,
    ) -> "VersionResolver":
        """Build a resolver from release manifest files on disk.

        Each ``*.json`` file in ``dataset_dir`` / ``model_dir`` is parsed as
        one release manifest. The manifest keys mirror the constructor
        arguments; ``publication_date`` is an ISO ``"YYYY-MM-DD"`` string and
        ``changelog`` is a list of changelog rows. When the ``id`` key is
        missing, the file name stem is used. Unreadable or invalid files are
        skipped. Missing directories yield empty mappings.

        Args:
            dataset_dir: Directory with dataset release manifests.
            model_dir: Directory with model release manifests.
            implementation_version: Library version (PEP 440), if any.
        """
        datasets: dict[str, DatasetRelease] = {}
        models: dict[str, ModelRelease] = {}
        dataset_path = Path(dataset_dir)
        model_path = Path(model_dir)
        if dataset_path.is_dir():
            for path in sorted(dataset_path.glob("*.json")):
                release = _release_from_json(path, "dataset")
                if release is not None:
                    datasets[release.id] = release
        if model_path.is_dir():
            for path in sorted(model_path.glob("*.json")):
                release = _release_from_json(path, "model")
                if release is not None:
                    models[release.id] = release
        return cls(datasets, models, implementation_version)

    def resolve_dataset(self, release_id: str) -> DatasetRelease:
        """Resolve a dataset release id or the ``"latest"`` alias.

        Args:
            release_id: Release id (e.g. ``"V221"``) or ``"latest"``.

        Returns:
            The concrete :class:`DatasetRelease`.

        Raises:
            DatasetNotFoundError: If the id is unknown or no dataset is
                installed.
        """
        if release_id == "latest":
            return _latest(self.datasets, release_id)
        try:
            return self.datasets[release_id]
        except KeyError:
            raise DatasetNotFoundError(release_id) from None

    def resolve_model(self, model_id: str) -> ModelRelease:
        """Resolve a model release id or the ``"latest"`` alias.

        Args:
            model_id: Model id (e.g. ``"1.0.0"``) or ``"latest"``.

        Returns:
            The concrete :class:`ModelRelease`.

        Raises:
            DatasetNotFoundError: If the id is unknown or no model is
                installed (the dataset exception is reused by design).
        """
        if model_id == "latest":
            return _latest(self.models, model_id)
        try:
            return self.models[model_id]
        except KeyError:
            raise DatasetNotFoundError(model_id) from None

    def list_datasets(self) -> list[DatasetRelease]:
        """Return all installed dataset releases, newest first."""
        return _newest_first(list(self.datasets.values()))

    def list_models(self) -> list[ModelRelease]:
        """Return all installed model releases, newest first."""
        return _newest_first(list(self.models.values()))

    def current(self) -> VersionInfo:
        """Return the version quadruple of the current installation.

        ``dataset`` and ``model`` are the ids of the newest installed release
        (``""`` when nothing is installed); ``implementation`` is the library
        version passed to the constructor (``""`` when ``None``); ``climate``
        is the newest climate version declared by any installed model
        (``""`` when no model declares one).

        Returns:
            A :class:`VersionInfo` with the resolved ids.
        """
        dataset = ""
        if self.datasets:
            dataset = _latest(self.datasets, "latest").id
        model = ""
        climate_versions: set[str] = set()
        if self.models:
            latest_model = _latest(self.models, "latest")
            model = latest_model.id
            for release in self.models.values():
                climate_versions.update(release.compatible_climate_versions)
        climate = max(climate_versions) if climate_versions else ""
        implementation = self.implementation_version or ""
        return VersionInfo(
            dataset=dataset,
            model=model,
            implementation=implementation,
            climate=climate,
        )
