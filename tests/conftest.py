"""Shared pytest fixtures for the energytools test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from energytools.engine.model import BuildingInput

from helpers import make_building_input

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DATASETS_DIR = REPO_ROOT / "data" / "datasets"


@pytest.fixture
def project() -> BuildingInput:
    """A valid example building input (engine milestone)."""
    return make_building_input()


@pytest.fixture(scope="session")
def datasets_dir() -> Path:
    """The repository's installed dataset packages (sample fixture releases)."""
    return DATASETS_DIR


@pytest.fixture(scope="session")
def dataset(datasets_dir: Path):
    """The loaded sample fixture release ``V221``."""
    from energytools.raumdaten.dataset import load_dataset

    return load_dataset("V221", path=str(datasets_dir))


@pytest.fixture(scope="session")
def service(datasets_dir: Path):
    """A :class:`RaumdatenService` over the sample fixture releases."""
    from energytools.raumdaten.dataset import DatasetStore
    from energytools.raumdaten.service import RaumdatenService

    return RaumdatenService(store=DatasetStore(str(datasets_dir)))
