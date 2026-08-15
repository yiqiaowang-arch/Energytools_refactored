"""Tests for energytools.common.valuekind.

Covers the ``ValueKind`` enum (standard / zielwert / bestand) with its
case-insensitive parsing and the English aliases ``target`` / ``existing``.
"""

from __future__ import annotations

import pytest

from energytools.common.errors import UnknownValueKindError
from energytools.common.valuekind import ValueKind


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("standard", ValueKind.STANDARD),
        ("Standard", ValueKind.STANDARD),
        ("STANDARD", ValueKind.STANDARD),
        ("zielwert", ValueKind.ZIELWERT),
        ("Zielwert", ValueKind.ZIELWERT),
        ("ZIELWERT", ValueKind.ZIELWERT),
        ("bestand", ValueKind.BESTAND),
        ("Bestand", ValueKind.BESTAND),
        ("BESTAND", ValueKind.BESTAND),
        ("target", ValueKind.ZIELWERT),
        ("Target", ValueKind.ZIELWERT),
        ("existing", ValueKind.BESTAND),
        ("Existing", ValueKind.BESTAND),
        (" standard ", ValueKind.STANDARD),
    ],
)
def test_value_kind_parse(value: str, expected: ValueKind) -> None:
    assert ValueKind.parse(value) is expected


def test_value_kind_parse_accepts_members() -> None:
    assert ValueKind.parse(ValueKind.STANDARD) is ValueKind.STANDARD


@pytest.mark.parametrize("value", ["optimal", "standard2", "soll", "ist", ""])
def test_value_kind_parse_unknown_raises(value: str) -> None:
    with pytest.raises(UnknownValueKindError) as exc_info:
        ValueKind.parse(value)
    assert str(exc_info.value) == (
        f"Unknown value kind '{value}' (expected standard, zielwert or bestand)"
    )


def test_value_kind_members_and_values() -> None:
    assert ValueKind.STANDARD.value == "standard"
    assert ValueKind.ZIELWERT.value == "zielwert"
    assert ValueKind.BESTAND.value == "bestand"
    assert {kind.value for kind in ValueKind} == {"standard", "zielwert", "bestand"}
