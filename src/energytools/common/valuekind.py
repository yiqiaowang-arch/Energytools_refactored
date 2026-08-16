"""Value kinds of the Raumdaten dataset.

The three value kinds of the dataset (assessment §1.2, columns M/N/O of the
``Datenblatt`` sheet) are Standard, Zielwert and Bestand. The German terms
``zielwert`` and ``bestand`` are kept as the canonical API values because
they are the workbook's own column vocabulary.

See docs/architecture+api-reference/02-common-foundation.md §5.
"""

from __future__ import annotations

import enum

from energytools.common.errors import UnknownValueKindError

__all__ = ["ValueKind"]


class ValueKind(enum.Enum):
    """The three value kinds of the Raumdaten dataset.

    Members:

    - ``STANDARD`` — standard values (``"standard"``)
    - ``ZIELWERT`` — target values (``"zielwert"``; workbook column M)
    - ``BESTAND`` — existing-stock values (``"bestand"``; workbook column O)
    """

    STANDARD = "standard"
    ZIELWERT = "zielwert"
    BESTAND = "bestand"

    @classmethod
    def parse(cls, value: str) -> ValueKind:
        """Parse a value kind from its canonical name or an alias.

        Case-insensitive; accepts ``"standard"``, ``"zielwert"``,
        ``"bestand"`` and the English aliases ``"target"`` and
        ``"existing"``.

        Args:
            value: The value-kind name.

        Returns:
            The corresponding :class:`ValueKind` member.

        Raises:
            UnknownValueKindError: If ``value`` is not a known value kind.
        """
        if isinstance(value, ValueKind):
            return value
        lowered = str(value).strip().lower()
        # English aliases for the workbook's Zielwert/Bestand columns.
        alias_map = {"target": cls.ZIELWERT, "existing": cls.BESTAND}
        if lowered in alias_map:
            return alias_map[lowered]
        try:
            return cls(lowered)
        except ValueError:
            raise UnknownValueKindError(str(value)) from None
