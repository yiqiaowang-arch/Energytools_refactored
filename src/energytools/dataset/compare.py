"""Profile comparison of the ``energytools.dataset`` data service.

Pure comparison of two :class:`~energytools.dataset.model.RoomUseProfile`
objects across all value kinds (docs/architecture+api-reference/03-raumdaten-service.md
§4): :func:`compare_profiles` returns a :class:`ProfileDiff` describing which
parameters changed/added/removed and the per-value-kind old/new values.
Replaces manual diffing of the workbook result sheets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from energytools.common.language import TrilingualText
from energytools.common.valuekind import ValueKind
from energytools.dataset.model import RoomUseProfile

__all__ = ["ParameterDiff", "ProfileDiff", "compare_profiles"]


def _same_value(a: Any, b: Any) -> bool:
    """Value equality used by comparison (type-sensitive, ``None``-safe).

    ``None`` equals ``None``; otherwise values must have the same type and be
    equal, so that ``True`` never equals ``1`` and ``1`` never equals ``1.0``.
    """
    if a is None or b is None:
        return a is b
    return type(a) is type(b) and a == b


@dataclass(frozen=True)
class ParameterDiff:
    """The per-parameter part of a profile comparison.

    Args:
        parameter_id: The parameter (clause) id.
        label: Trilingual label of the parameter.
        symbol: Parameter symbol.
        unit: Normalized unit symbol.
        diffs: Value kind name (``"standard"``, ``"zielwert"``, ``"bestand"``)
            → ``(value_a, value_b)``; a missing side is ``None``.
    """

    parameter_id: str
    label: TrilingualText
    symbol: str
    unit: str
    diffs: dict[str, tuple[Any, Any]]

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation (``diffs`` values stay tuples, as in the doc)."""
        return {
            "parameter_id": self.parameter_id,
            "label": self.label.as_dict(),
            "symbol": self.symbol,
            "unit": self.unit,
            "diffs": {kind: (a, b) for kind, (a, b) in self.diffs.items()},
        }


@dataclass(frozen=True)
class ProfileDiff:
    """Structured comparison of two room-use profiles.

    Args:
        a_id: nutzid of the first profile.
        b_id: nutzid of the second profile.
        changed: Per-parameter differences (parameters present in both).
        added: Parameter ids present in ``b`` but not in ``a``.
        removed: Parameter ids present in ``a`` but not in ``b``.
        identical: ``True`` when nothing changed/added/removed.
    """

    a_id: int
    b_id: int
    changed: tuple[ParameterDiff, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]
    identical: bool

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready representation (used by the service layer)."""
        return {
            "a_id": self.a_id,
            "b_id": self.b_id,
            "identical": self.identical,
            "changed": [diff.as_dict() for diff in self.changed],
            "added": list(self.added),
            "removed": list(self.removed),
        }


def compare_profiles(a: RoomUseProfile, b: RoomUseProfile) -> ProfileDiff:
    """Compare two room-use profiles across all value kinds.

    Args:
        a: First profile (the reference side).
        b: Second profile.

    Returns:
        A :class:`ProfileDiff` with per-parameter, per-kind old/new values.

    Raises:
        ValueError: If the profiles belong to different releases (checked via
            their parameter catalogs).
    """
    if a.parameter_catalog != b.parameter_catalog:
        raise ValueError(
            "cannot compare profiles of different releases "
            "(parameter catalogs differ)"
        )

    a_ids = set(a.values)
    b_ids = set(b.values)
    added = sorted(b_ids - a_ids)
    removed = sorted(a_ids - b_ids)

    changed: list[ParameterDiff] = []
    for parameter_id in sorted(a_ids & b_ids):
        parameter = a.parameter_catalog[parameter_id]
        kinds_a = a.values[parameter_id]
        kinds_b = b.values[parameter_id]
        diffs: dict[str, tuple[Any, Any]] = {}
        for kind in sorted(set(kinds_a) | set(kinds_b), key=_kind_order):
            value_a = kinds_a.get(kind)
            value_b = kinds_b.get(kind)
            a_value = value_a.value if value_a is not None else None
            b_value = value_b.value if value_b is not None else None
            if not _same_value(a_value, b_value):
                diffs[kind.value] = (a_value, b_value)
        if diffs:
            changed.append(
                ParameterDiff(
                    parameter_id=parameter_id,
                    label=parameter.label,
                    symbol=parameter.symbol,
                    unit=parameter.unit_symbol,
                    diffs=diffs,
                )
            )

    return ProfileDiff(
        a_id=a.room_use.nutzid,
        b_id=b.room_use.nutzid,
        changed=tuple(changed),
        added=tuple(added),
        removed=tuple(removed),
        identical=not changed and not added and not removed,
    )


def _kind_order(kind: ValueKind) -> int:
    """Workbook column order (Standard, Zielwert, Bestand) for stable diffs."""
    return (ValueKind.STANDARD, ValueKind.ZIELWERT, ValueKind.BESTAND).index(kind)
