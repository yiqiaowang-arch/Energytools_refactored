"""energytools.common.validation -- structured validation outcome.

``ValidationReport`` is defined in part 04 section 1.10 of the API reference and
is used by input validation and dataset validation alike.  It lives here (common)
so that ``energytools.raumdaten`` (part 03) can use it without depending on the
not-yet-implemented ``energytools.gebaeude`` package; the gebaeude layer will
re-export it from its own ``model`` module for API compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["ValidationReport"]


@dataclass(frozen=True)
class ValidationReport:
    """Structured validation outcome: hard errors (invalid) and warnings (suspicious).

    Args:
        errors: Hard validation errors; a non-empty list means ``valid is False``.
        warnings: Suspicious but acceptable findings.
    """

    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def valid(self) -> bool:
        """``True`` when there are no errors."""
        return not self.errors

    def as_dict(self) -> dict:
        """JSON-ready dict ``{"valid": ..., "errors": [...], "warnings": [...]}``."""
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }
