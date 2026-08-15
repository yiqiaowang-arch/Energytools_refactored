"""Pytest fixtures for the engine milestone tests."""

from __future__ import annotations

import pytest

from energytools.engine.model import BuildingInput

from helpers import make_building_input


@pytest.fixture
def project() -> BuildingInput:
    """A valid example building input."""
    return make_building_input()
