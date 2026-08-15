"""Smoke tests for the energytools distribution root.

These tests verify that the package installs and imports correctly and that
the documented root API (``__version__`` and ``get_version()``) works.
"""

from __future__ import annotations

import pytest

import energytools
from energytools.cli import main
from energytools.common.versioning import VersionInfo


def test_version_metadata() -> None:
    assert energytools.__version__ == "0.1.0"


def test_get_version_returns_version_info() -> None:
    version = energytools.get_version()
    assert isinstance(version, VersionInfo)
    # The library version is always reported; the dataset/model/climate axes
    # depend on the installed manifests of the checkout.
    assert version.implementation == energytools.__version__
    assert set(version.as_dict()) == {"dataset", "model", "implementation", "climate"}


def test_cli_version_flag() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0


def test_cli_runs_without_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "usage:" in out
