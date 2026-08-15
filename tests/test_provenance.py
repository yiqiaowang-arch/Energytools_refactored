"""Tests for energytools.common.provenance.

Covers the ``SourceRef`` source reference (range/formula requirement and
serialization) and the ``Provenance`` collection with its free-text note.
"""

from __future__ import annotations

import pytest

from energytools.common.provenance import Provenance, SourceRef


def _source_ref(**overrides: object) -> SourceRef:
    kwargs: dict[str, object] = {
        "workbook": "2024_Raumdatenblätter_dfi_V221.xlsm",
        "sheet": "Datenblatt",
        "range": "O2",
        **overrides,
    }
    return SourceRef(**kwargs)  # type: ignore[arg-type]


def test_source_ref_fields() -> None:
    ref = _source_ref(
        formula="INDEX(Eingabedaten!A9:A53,nutzid)",
        cached_value="1.01",
        extraction_hash="abc123",
    )
    assert ref.workbook == "2024_Raumdatenblätter_dfi_V221.xlsm"
    assert ref.sheet == "Datenblatt"
    assert ref.range == "O2"
    assert ref.formula == "INDEX(Eingabedaten!A9:A53,nutzid)"
    assert ref.cached_value == "1.01"
    assert ref.extraction_hash == "abc123"


def test_source_ref_requires_range_or_formula() -> None:
    # Range alone is fine, formula alone is fine, both is fine.
    assert _source_ref(range="M11").range == "M11"
    assert _source_ref(range=None, formula="SUM(A1:A2)").formula == "SUM(A1:A2)"
    assert _source_ref(range="A9:C53", formula="INDEX(...)").range == "A9:C53"
    with pytest.raises(ValueError, match="range.*formula"):
        _source_ref(range=None, formula=None)


def test_source_ref_cached_value_number() -> None:
    ref = _source_ref(cached_value=12.5)
    assert ref.cached_value == 12.5


def test_source_ref_as_dict() -> None:
    ref = _source_ref(formula="INDEX(Eingabedaten!A9:A53,nutzid)", cached_value="1.01")
    assert ref.as_dict() == {
        "workbook": "2024_Raumdatenblätter_dfi_V221.xlsm",
        "sheet": "Datenblatt",
        "range": "O2",
        "formula": "INDEX(Eingabedaten!A9:A53,nutzid)",
        "cached_value": "1.01",
        "extraction_hash": None,
    }


def test_source_ref_frozen() -> None:
    ref = _source_ref()
    with pytest.raises(AttributeError):
        ref.sheet = "Profile"  # type: ignore[misc]


def test_provenance_defaults() -> None:
    provenance = Provenance()
    assert provenance.sources == ()
    assert provenance.note is None


def test_provenance_fields() -> None:
    source = _source_ref(sheet="Profile", range="O611:AB611")
    provenance = Provenance(
        sources=(source,),
        note="Annual ventilation full-load hours, 365-day engine, prSIA 2024-C1",
    )
    assert provenance.sources == (source,)
    assert provenance.note.startswith("Annual ventilation full-load hours")


def test_provenance_as_dict() -> None:
    source = _source_ref(sheet="Profile", range="O611:AB611")
    provenance = Provenance(sources=(source,), note="derived")
    assert provenance.as_dict() == {
        "sources": [source.as_dict()],
        "note": "derived",
    }


def test_provenance_frozen() -> None:
    provenance = Provenance()
    with pytest.raises(AttributeError):
        provenance.note = "nope"  # type: ignore[misc]
