"""Provenance tracking of the energytools library.

:class:`SourceRef` records where a value or formula came from in the source
workbook; :class:`Provenance` collects source references plus a free-text
note for one domain value or derived result. Traceability is kept without
exposing cell addresses through the API (addresses are metadata, not API —
assessment §5.3 rule 1).

See docs/architecture+api-reference/02-common-foundation.md §6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["Provenance", "SourceRef"]


@dataclass(frozen=True)
class SourceRef:
    """One grounded source reference in the source workbook.

    Args:
        workbook: Source workbook file name, e.g.
            ``"2024_Raumdatenblätter_dfi_V221.xlsm"``.
        sheet: Exact sheet name as stored, e.g. ``"tblEingabedaten"``.
        range: Cell range, e.g. ``"M11"`` or ``"A9:C53"``.
        formula: Extracted formula text, e.g.
            ``INDEX(Eingabedaten!C9:C53,nutzid)``.
        cached_value: The value Excel cached for the cell.
        extraction_hash: Package fingerprint of the extraction.

    Raises:
        ValueError: If neither ``range`` nor ``formula`` is set.
    """

    workbook: str
    sheet: str
    range: str | None = None
    formula: str | None = None
    cached_value: str | float | None = None
    extraction_hash: str | None = None

    def __post_init__(self) -> None:
        if self.range is None and self.formula is None:
            raise ValueError("SourceRef requires at least one of 'range' or 'formula'")

    def as_dict(self) -> dict[str, Any]:
        """Return the reference as a plain dict (API metadata shape)."""
        return {
            "workbook": self.workbook,
            "sheet": self.sheet,
            "range": self.range,
            "formula": self.formula,
            "cached_value": self.cached_value,
            "extraction_hash": self.extraction_hash,
        }


@dataclass(frozen=True)
class Provenance:
    """Collection of source references plus a note for one value or result.

    Args:
        sources: The :class:`SourceRef` entries backing the value.
        note: Optional free-text note (English; workbook terms where
            applicable).
    """

    sources: tuple[SourceRef, ...] = ()
    note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return the provenance as a plain dict."""
        return {
            "sources": [source.as_dict() for source in self.sources],
            "note": self.note,
        }
