"""Tests for energytools.common.versioning.

Covers the immutable release value objects (``DatasetRelease``,
``ModelRelease``, ``VersionInfo``, ``ChangelogEntry``) and the
``VersionResolver`` (id/``"latest"`` resolution, listing, ``current()`` and
manifest-based ``from_installed``).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from energytools.common.errors import DatasetNotFoundError
from energytools.common.versioning import (
    ChangelogEntry,
    DatasetRelease,
    ModelRelease,
    VersionInfo,
    VersionResolver,
    _parse_date,
)


def _release(
    release_id: str = "V221",
    publication_date: date = date(2024, 11, 17),
    **overrides: object,
) -> DatasetRelease:
    kwargs: dict[str, object] = {
        "id": release_id,
        "edition": "SIA 2024",
        "publication_date": publication_date,
        "checksum_sha256": "ab12" * 16,
        "source_workbook": "2024_Raumdatenblätter_dfi_V221.xlsm",
        "extraction_tool_version": "0.1.0",
        **overrides,
    }
    return DatasetRelease(**kwargs)  # type: ignore[arg-type]


def _model(
    model_id: str = "1.0.0",
    publication_date: date = date(2025, 4, 20),
    **overrides: object,
) -> ModelRelease:
    kwargs: dict[str, object] = {
        "id": model_id,
        "compatible_dataset_releases": frozenset({"V221"}),
        "compatible_climate_versions": frozenset({"meteoschweiz-2024"}),
        "publication_date": publication_date,
        **overrides,
    }
    return ModelRelease(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


def test_dataset_release_fields_and_frozen() -> None:
    entry = ChangelogEntry(version="V221", date=date(2024, 11, 17), change="initial")
    release = _release(changelog=(entry,))
    assert release.id == "V221"
    assert release.edition == "SIA 2024"
    assert release.publication_date == date(2024, 11, 17)
    assert release.checksum_sha256 == "ab12" * 16
    assert release.source_workbook == "2024_Raumdatenblätter_dfi_V221.xlsm"
    assert release.extraction_tool_version == "0.1.0"
    assert release.supersedes is None
    assert release.changelog == (entry,)
    with pytest.raises(AttributeError):
        release.id = "V222"  # type: ignore[misc]


def test_dataset_release_supersedes_and_empty_changelog() -> None:
    release = _release("V222", supersedes="V221")
    assert release.supersedes == "V221"
    assert release.changelog == ()


def test_dataset_release_empty_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="id must not be empty"):
        _release("")


def test_dataset_release_equality_and_ordering_on_id() -> None:
    assert _release("V221") == _release("V221")
    assert _release("V221") != _release("V222")
    assert _release("V221") < _release("V222")
    assert sorted([_release("V222"), _release("V221")]) == [_release("V221"), _release("V222")]


def test_dataset_release_comparison_with_foreign_type_raises() -> None:
    with pytest.raises(TypeError):
        _release("V221") < "V222"  # type: ignore[operator]


def test_changelog_entry_fields_and_defaults() -> None:
    entry = ChangelogEntry(
        version="V221",
        date=date(2024, 11, 17),
        change="prSIA 2024-C1 values; Qhc extended to 40 stations",
        migration="Qhc table layout extended by 12 columns per station block",
    )
    assert entry.version == "V221"
    assert entry.date == date(2024, 11, 17)
    assert entry.change.startswith("prSIA 2024-C1")
    assert entry.migration is not None
    assert ChangelogEntry("V221", date(2024, 11, 17), "change").migration is None
    assert ChangelogEntry("V221", date(2024, 11, 17), "change") == ChangelogEntry(
        "V221", date(2024, 11, 17), "change"
    )


@pytest.mark.parametrize(
    "model_id",
    [
        "1.0.0",
        "0.1.0",
        "2.1.0-alpha.1",
        "2.1.0-alpha.1+build.5",
        "1.0.0+20241117",
        "10.20.30",
    ],
)
def test_model_release_accepts_valid_semantic_versions(model_id: str) -> None:
    assert _model(model_id).id == model_id


@pytest.mark.parametrize(
    "model_id",
    ["1.0", "1", "1.0.0.0", "abc", "V221", "1.0.0-", "1..0", "1.0.0 alpha"],
)
def test_model_release_rejects_malformed_semantic_versions(model_id: str) -> None:
    with pytest.raises(ValueError, match="semantic version"):
        _model(model_id)


def test_model_release_requires_non_empty_compatibility_sets() -> None:
    with pytest.raises(ValueError, match="compatible_dataset_releases"):
        _model(compatible_dataset_releases=frozenset())
    with pytest.raises(ValueError, match="compatible_climate_versions"):
        _model(compatible_climate_versions=frozenset())


def test_model_release_fields() -> None:
    model = _model(
        changelog=(ChangelogEntry("1.0.0", date(2025, 4, 20), "initial model"),),
    )
    assert model.id == "1.0.0"
    assert model.compatible_dataset_releases == frozenset({"V221"})
    assert model.compatible_climate_versions == frozenset({"meteoschweiz-2024"})
    assert model.publication_date == date(2025, 4, 20)
    assert model.changelog[0].version == "1.0.0"
    with pytest.raises(AttributeError):
        model.id = "2.0.0"  # type: ignore[misc]


def test_version_info_fields_and_as_dict() -> None:
    info = VersionInfo(
        dataset="V221", model="1.0.0", implementation="0.1.0", climate="meteoschweiz-2024"
    )
    assert info.dataset == "V221"
    assert info.model == "1.0.0"
    assert info.implementation == "0.1.0"
    assert info.climate == "meteoschweiz-2024"
    assert info.as_dict() == {
        "dataset": "V221",
        "model": "1.0.0",
        "implementation": "0.1.0",
        "climate": "meteoschweiz-2024",
    }
    assert info == VersionInfo("V221", "1.0.0", "0.1.0", "meteoschweiz-2024")


# ---------------------------------------------------------------------------
# VersionResolver
# ---------------------------------------------------------------------------


def _resolver() -> VersionResolver:
    v221 = _release("V221", date(2024, 11, 17))
    v222 = _release("V222", date(2025, 3, 2), supersedes="V221")
    model = _model("1.0.0", date(2025, 4, 20))
    return VersionResolver(
        datasets={"V221": v221, "V222": v222},
        models={"1.0.0": model},
        implementation_version="0.1.0",
    )


def test_resolve_dataset_by_id_and_latest() -> None:
    resolver = _resolver()
    assert resolver.resolve_dataset("V221").id == "V221"
    # "latest" resolves by publication date, not by id.
    assert resolver.resolve_dataset("latest").id == "V222"
    assert resolver.resolve_dataset("V222") is resolver.datasets["V222"]


def test_resolve_dataset_unknown_raises() -> None:
    with pytest.raises(DatasetNotFoundError) as exc_info:
        _resolver().resolve_dataset("V199")
    assert str(exc_info.value) == "Dataset release 'V199' not found"


def test_resolve_dataset_latest_with_empty_store_raises() -> None:
    resolver = VersionResolver(datasets={}, models={})
    with pytest.raises(DatasetNotFoundError):
        resolver.resolve_dataset("latest")


def test_resolve_model_by_id_and_latest() -> None:
    resolver = _resolver()
    assert resolver.resolve_model("1.0.0").id == "1.0.0"
    assert resolver.resolve_model("latest").id == "1.0.0"


def test_resolve_model_unknown_raises_reused_dataset_error() -> None:
    with pytest.raises(DatasetNotFoundError) as exc_info:
        _resolver().resolve_model("9.9.9")
    assert str(exc_info.value) == "Dataset release '9.9.9' not found"


def test_list_datasets_and_models_newest_first() -> None:
    resolver = _resolver()
    assert [release.id for release in resolver.list_datasets()] == ["V222", "V221"]
    assert [model.id for model in resolver.list_models()] == ["1.0.0"]


def test_list_sorts_by_publication_date_with_id_tie_break() -> None:
    older = _release("A01", date(2025, 1, 1))
    newer = _release("B01", date(2025, 1, 1))
    resolver = VersionResolver(datasets={"A01": older, "B01": newer}, models={})
    assert [release.id for release in resolver.list_datasets()] == ["B01", "A01"]


def test_current_returns_version_quadruple() -> None:
    info = _resolver().current()
    assert info == VersionInfo("V222", "1.0.0", "0.1.0", "meteoschweiz-2024")


def test_current_climate_is_newest_across_models() -> None:
    resolver = VersionResolver(
        datasets={},
        models={
            "1.0.0": _model(
                "1.0.0",
                date(2025, 1, 1),
                compatible_climate_versions=frozenset({"meteoschweiz-2023"}),
            ),
            "1.1.0": _model(
                "1.1.0",
                date(2025, 6, 1),
                compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
            ),
        },
    )
    info = resolver.current()
    assert info.dataset == ""
    assert info.model == "1.1.0"
    assert info.climate == "meteoschweiz-2024"


def test_current_empty_resolver() -> None:
    resolver = VersionResolver(datasets={}, models={})
    assert resolver.current() == VersionInfo("", "", "", "")


def test_current_implementation_none_becomes_empty() -> None:
    resolver = VersionResolver(datasets={}, models={}, implementation_version=None)
    assert resolver.current().implementation == ""


def test_resolver_mapping_attributes_are_copied() -> None:
    datasets = {"V221": _release()}
    resolver = VersionResolver(datasets=datasets, models={})
    datasets["V999"] = _release("V999")
    assert "V999" not in resolver.datasets


# ---------------------------------------------------------------------------
# from_installed (manifest files)
# ---------------------------------------------------------------------------


def _write_manifest(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_from_installed_parses_dataset_and_model_manifests(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets"
    model_dir = tmp_path / "models"
    dataset_dir.mkdir()
    model_dir.mkdir()
    _write_manifest(
        dataset_dir / "V221.json",
        {
            "id": "V221",
            "edition": "SIA 2024",
            "publication_date": "2024-11-17",
            "checksum_sha256": "ab12" * 16,
            "source_workbook": "2024_Raumdatenblätter_dfi_V221.xlsm",
            "extraction_tool_version": "0.1.0",
            "changelog": [
                {"version": "V221", "date": "2024-11-17", "change": "initial", "migration": None},
            ],
        },
    )
    _write_manifest(
        model_dir / "1.0.0.json",
        {
            "id": "1.0.0",
            "compatible_dataset_releases": ["V221"],
            "compatible_climate_versions": ["meteoschweiz-2024"],
            "publication_date": "2025-04-20",
        },
    )
    resolver = VersionResolver.from_installed(
        dataset_dir, model_dir, implementation_version="0.2.0"
    )
    release = resolver.resolve_dataset("V221")
    assert release.edition == "SIA 2024"
    assert release.publication_date == date(2024, 11, 17)
    assert release.changelog == (ChangelogEntry("V221", date(2024, 11, 17), "initial", None),)
    model = resolver.resolve_model("1.0.0")
    assert model.compatible_dataset_releases == frozenset({"V221"})
    assert model.compatible_climate_versions == frozenset({"meteoschweiz-2024"})
    assert resolver.current().implementation == "0.2.0"


def test_from_installed_uses_filename_stem_as_id(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir()
    _write_manifest(
        dataset_dir / "V221.json",
        {
            "edition": "SIA 2024",
            "publication_date": "2024-11-17",
            "checksum_sha256": "ab12" * 16,
            "source_workbook": "2024_Raumdatenblätter_dfi_V221.xlsm",
            "extraction_tool_version": "0.1.0",
        },
    )
    resolver = VersionResolver.from_installed(dataset_dir, tmp_path / "models")
    assert resolver.resolve_dataset("V221").id == "V221"


def test_from_installed_skips_invalid_and_unreadable_files(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets"
    dataset_dir.mkdir()
    _write_manifest(dataset_dir / "bad.json", {"edition": "no id, no date"})
    # A file with invalid JSON content (not produced by json.dumps).
    (dataset_dir / "not-json.json").write_text("not json", encoding="utf-8")
    _write_manifest(dataset_dir / "not-object.json", [1, 2, 3])
    _write_manifest(dataset_dir / "bad-date.json", {"publication_date": 12345})
    resolver = VersionResolver.from_installed(dataset_dir, tmp_path / "models")
    assert resolver.datasets == {}


def test_from_installed_missing_directories_yield_empty_resolver(tmp_path: Path) -> None:
    resolver = VersionResolver.from_installed(
        tmp_path / "nope-datasets",
        tmp_path / "nope-models",
    )
    assert resolver.datasets == {}
    assert resolver.models == {}
    assert resolver.current() == VersionInfo("", "", "", "")


def test_from_installed_skips_model_with_bad_semver_or_missing_keys(tmp_path: Path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    _write_manifest(model_dir / "bad.json", {"id": "not-semver", "publication_date": "2025-04-20"})
    _write_manifest(model_dir / "empty.json", {"id": "1.0.0", "publication_date": "2025-04-20"})
    resolver = VersionResolver.from_installed(tmp_path / "datasets", model_dir)
    assert resolver.models == {}


def test_from_installed_accepts_bare_string_compatibility_sets(tmp_path: Path) -> None:
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    _write_manifest(
        model_dir / "1.0.0.json",
        {
            "id": "1.0.0",
            "compatible_dataset_releases": "V221",
            "compatible_climate_versions": "meteoschweiz-2024",
            "publication_date": "2025-04-20",
        },
    )
    resolver = VersionResolver.from_installed(tmp_path / "datasets", model_dir)
    model = resolver.resolve_model("1.0.0")
    assert model.compatible_dataset_releases == frozenset({"V221"})
    assert model.compatible_climate_versions == frozenset({"meteoschweiz-2024"})


def test_parse_date_accepts_date_instances_and_iso_strings() -> None:
    assert _parse_date(date(2024, 11, 17)) == date(2024, 11, 17)
    assert _parse_date("2024-11-17") == date(2024, 11, 17)
    with pytest.raises(ValueError, match="invalid date value"):
        _parse_date(12345)
