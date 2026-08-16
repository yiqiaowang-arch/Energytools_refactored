"""Languages and trilingual labels of the energytools library.

The three workbook languages (assessment §1.2: ``Begriffe!G1`` = 1/2/3) are
modelled by :class:`Language`; :class:`TrilingualText` carries DE/FR/IT label
triples and normalizes the workbook's rich-text cells to plain structured
strings during extraction.

See docs/architecture+api-reference/02-common-foundation.md §4.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from energytools.common.errors import UnknownLanguageError

__all__ = ["Language", "TrilingualText"]


class Language(enum.Enum):
    """The three workbook languages (DE, FR, IT).

    Members:

    - ``DE`` — German (``"de"``)
    - ``FR`` — French (``"fr"``)
    - ``IT`` — Italian (``"it"``)
    """

    DE = "de"
    FR = "fr"
    IT = "it"

    @classmethod
    def parse(cls, value: str) -> Language:
        """Parse a language from its code or the workbook index.

        Accepts ``"de"``/``"fr"``/``"it"`` (case-insensitive) and the
        workbook's numeric indices ``"1"``/``"2"``/``"3"``.

        Args:
            value: The language code or workbook index.

        Returns:
            The corresponding :class:`Language` member.

        Raises:
            UnknownLanguageError: If ``value`` is not a known language.
        """
        if isinstance(value, Language):
            return value
        lowered = str(value).strip().lower()
        # Workbook indices as stored in the ``Begriffe`` sheet (G1 = 1/2/3).
        index_map = {"1": cls.DE, "2": cls.FR, "3": cls.IT}
        if lowered in index_map:
            return index_map[lowered]
        try:
            return cls(lowered)
        except ValueError:
            raise UnknownLanguageError(str(value)) from None


@dataclass(frozen=True)
class TrilingualText:
    """A DE/FR/IT label triple (names, parameter labels, sheet titles).

    Args:
        de: German label.
        fr: French label.
        it: Italian label.
    """

    de: str = ""
    fr: str = ""
    it: str = ""

    def get(self, language: Language | str) -> str:
        """Return the label in the requested language.

        Falls back to the German label when the requested field is empty
        (observed for unfinished Italian cells in the workbook).

        Args:
            language: A :class:`Language` member, language code or workbook
                index.

        Returns:
            The label in the requested language (or German as fallback).

        Raises:
            UnknownLanguageError: If the language is not one of de/fr/it.
        """
        resolved = language if isinstance(language, Language) else Language.parse(language)
        label = getattr(self, resolved.value)
        if label:
            return label
        return self.de

    def as_dict(self) -> dict[str, str]:
        """Return the label triple as ``{"de": ..., "fr": ..., "it": ...}``."""
        return {"de": self.de, "fr": self.fr, "it": self.it}
