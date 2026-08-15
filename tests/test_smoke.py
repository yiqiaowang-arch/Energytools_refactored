"""Smoke tests for the energytools packaging scaffold.

These tests only verify that the placeholder distribution installs and
imports correctly — the real test suite arrives with the implementation.
"""

from __future__ import annotations

import pytest

import energytools
from energytools.cli import main


def test_version_metadata() -> None:
    assert energytools.__version__ == "0.1.0"
    assert energytools.get_version() == "0.1.0"


def test_cli_version_flag() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0


def test_cli_runs_without_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "usage:" in out
