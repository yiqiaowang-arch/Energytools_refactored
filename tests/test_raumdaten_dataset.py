"""Tests for energytools.raumdaten.dataset -- loading and the store (part 03, section 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from energytools.common.errors import DatasetNotFoundError, DatasetValidationError
from energytools.raumdaten.dataset import DatasetStore, load_dataset


class TestLoadDataset:
    def test_load_sample_release(self, dataset) -> None:
        assert dataset.release_id == "V221"
        assert len(dataset.room_uses()) == 6
        assert len(dataset.parameters()) == 11
        assert len(dataset.climate().stations) == 2
        assert dataset.validate().valid

    def test_identical_frozen_object_is_cached(self, datasets_dir: Path) -> None:
        first = load_dataset("V221", path=str(datasets_dir))
        second = load_dataset("V221", path=str(datasets_dir))
        assert first is second

    def test_missing_release_raises(self, datasets_dir: Path) -> None:
        with pytest.raises(DatasetNotFoundError):
            load_dataset("V999", path=str(datasets_dir))

    def test_invalid_release_id_rejected(self, datasets_dir: Path) -> None:
        with pytest.raises(DatasetValidationError):
            load_dataset("../../etc", path=str(datasets_dir))

    def test_checksum_mismatch_rejected(self, datasets_dir: Path, tmp_path: Path) -> None:
        package = json.loads((datasets_dir / "V221" / "package.json").read_text(encoding="utf-8"))
        package["release"]["checksum_sha256"] = "ff" * 32
        (tmp_path / "V221").mkdir(parents=True)
        (tmp_path / "V221" / "package.json").write_text(json.dumps(package), encoding="utf-8")
        (tmp_path / "V221" / "schema.json").write_text(
            (datasets_dir / "V221" / "schema.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        with pytest.raises(DatasetValidationError, match="checksum"):
            load_dataset("V221", path=str(tmp_path))

    def test_schema_violation_rejected(self, datasets_dir: Path, tmp_path: Path) -> None:
        package = json.loads((datasets_dir / "V221" / "package.json").read_text(encoding="utf-8"))
        del package["parameters"]  # required property -> schema violation
        (tmp_path / "V221").mkdir(parents=True)
        (tmp_path / "V221" / "package.json").write_text(json.dumps(package), encoding="utf-8")
        with pytest.raises(DatasetValidationError, match="schema"):
            load_dataset("V221", path=str(tmp_path))

    def test_invalid_json_rejected(self, datasets_dir: Path, tmp_path: Path) -> None:
        (tmp_path / "V221").mkdir(parents=True)
        (tmp_path / "V221" / "package.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(DatasetValidationError, match="not valid JSON"):
            load_dataset("V221", path=str(tmp_path))

    def test_checksum_of_fixture_is_verifiable(self, datasets_dir: Path) -> None:
        from energytools.raumdaten.dataset import _content_checksum

        package = json.loads((datasets_dir / "V221" / "package.json").read_text(encoding="utf-8"))
        assert _content_checksum(package) == package["release"]["checksum_sha256"]


class TestDatasetStore:
    def test_list_and_get(self, datasets_dir: Path) -> None:
        store = DatasetStore(str(datasets_dir))
        assert [release.id for release in store.list()] == ["V221"]
        assert store.get("V221").release_id == "V221"

    def test_list_empty_for_missing_dir(self, tmp_path: Path) -> None:
        assert DatasetStore(str(tmp_path / "nope")).list() == []

    def test_register_and_duplicate_content(self, datasets_dir: Path, dataset) -> None:
        store = DatasetStore(str(datasets_dir))
        store.register(dataset)  # identical content -> no error
        with pytest.raises(ValueError, match="different content"):
            store.register(_tampered(dataset, store))

    def test_refresh_drops_cache(self, datasets_dir: Path, tmp_path: Path) -> None:
        store = DatasetStore(str(datasets_dir))
        first = store.get("V221")
        store.refresh()
        second = store.get("V221")
        assert first is not second  # re-loaded after refresh


def _tampered(dataset, store):
    """A copy of the sample dataset with one value changed."""
    from energytools.common.valuekind import ValueKind
    from energytools.raumdaten.model import Dataset, ParameterValue, RoomUseProfile

    profile = dataset.profiles[1]
    values = dict(profile.values)
    by_kind = dict(values["1.1.2.7"])
    by_kind[ValueKind.STANDARD] = ParameterValue("1.1.2.7", ValueKind.STANDARD, 0.99, "%")
    values["1.1.2.7"] = by_kind
    tampered_profile = RoomUseProfile(
        room_use=profile.room_use, values=values, parameter_catalog=profile.parameter_catalog
    )
    profiles = dict(dataset.profiles)
    profiles[1] = tampered_profile
    return Dataset(
        release=dataset.release,
        room_uses=dataset._room_uses,
        parameters=dataset._parameters,
        profiles=profiles,
        hourly_profiles=dataset.hourly_profiles,
        monthly_profiles=dataset.monthly_profiles,
        weekly_profiles=dataset.weekly_profiles,
        climate=dataset._climate,
        full_load_hours=dataset._full_load_hours,
        qhc=dataset._qhc,
        sia3801=dataset.sia3801,
        mappings=dataset._mappings,
        area_tables=dataset._area_tables,
        sia3801_coefficients=dataset._sia3801_coefficients,
    )
