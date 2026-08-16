"""energytools.raumdaten.compare -- profile comparison (API reference part 03, section 4).

Pure comparison of two room-use profiles across all value kinds; used by
:meth:`RaumdatenService.compare_room_use_profiles` and the MCP tool.  Replaces
manual diffing of the workbook result sheets.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from energytools.raumdaten.model import RoomUseProfile

__all__ = ["ParameterDiff", "ProfileDiff", "compare_profiles"]


@dataclass(frozen=True)
class ParameterDiff:
    """Per-parameter difference: which kinds differ and by how much.

    ``diffs`` maps value-kind name -> ``(value_a, value_b)``; either value may
    be ``None`` when the kind is only present on one side.
    """

    parameter_id: str
    label: str
    symbol: str
    unit: str
    diffs: dict[str, tuple] = field(default_factory=dict)

    def as_dict(self) -> dict:
        """JSON-ready dict."""
        return {
            "parameter_id": self.parameter_id,
            "label": self.label,
            "symbol": self.symbol,
            "unit": self.unit,
            "diffs": {kind: list(values) for kind, values in self.diffs.items()},
        }


@dataclass(frozen=True)
class ProfileDiff:
    """Structured comparison result of two room-use profiles.

    Args:
        a_id: The first compared room use (nutzid).
        b_id: The second compared room use (nutzid).
        changed: Parameters with at least one differing value.
        added: Parameter ids only present in ``b``.
        removed: Parameter ids only present in ``a``.
        identical: ``True`` when nothing changed/added/removed.
    """

    a_id: int
    b_id: int
    changed: tuple[ParameterDiff, ...] = field(default_factory=tuple)
    added: tuple[str, ...] = field(default_factory=tuple)
    removed: tuple[str, ...] = field(default_factory=tuple)
    identical: bool = True

    def as_dict(self) -> dict:
        """JSON-ready dict (used by the service)."""
        return {
            "a": self.a_id,
            "b": self.b_id,
            "changed": [diff.as_dict() for diff in self.changed],
            "added": list(self.added),
            "removed": list(self.removed),
            "identical": self.identical,
        }


def compare_profiles(a: RoomUseProfile, b: RoomUseProfile) -> ProfileDiff:
    """Compare two room-use profiles across all value kinds.

    Args:
        a: First room-use profile.
        b: Second room-use profile.

    Raises:
        ValueError: if the profiles belong to different releases (checked via
            their parameter catalogs).
    """
    if a.parameter_catalog != b.parameter_catalog:
        raise ValueError("profiles belong to different releases (parameter catalogs differ)")

    a_ids = set(a.values)
    b_ids = set(b.values)
    added = tuple(sorted(b_ids - a_ids))
    removed = tuple(sorted(a_ids - b_ids))

    changed: list[ParameterDiff] = []
    for parameter_id in sorted(a_ids & b_ids):
        parameter = a.parameter_catalog[parameter_id]
        by_kind_a = a.values[parameter_id]
        by_kind_b = b.values[parameter_id]
        kind_names = sorted(set(by_kind_a) | set(by_kind_b), key=lambda k: k.value)
        diffs: dict[str, tuple] = {}
        for kind in kind_names:
            value_a = by_kind_a.get(kind)
            value_b = by_kind_b.get(kind)
            if value_a is None or value_b is None:
                if value_a is not value_b:
                    diffs[kind.value] = (
                        None if value_a is None else value_a.value,
                        None if value_b is None else value_b.value,
                    )
                continue
            if value_a.value != value_b.value:
                diffs[kind.value] = (value_a.value, value_b.value)
        if diffs:
            changed.append(
                ParameterDiff(
                    parameter_id=parameter_id,
                    label=parameter.label.de,
                    symbol=parameter.symbol,
                    unit=parameter.unit.symbol,
                    diffs=diffs,
                )
            )

    identical = not changed and not added and not removed
    return ProfileDiff(
        a_id=a.room_use.nutzid,
        b_id=b.room_use.nutzid,
        changed=tuple(changed),
        added=added,
        removed=removed,
        identical=identical,
    )
