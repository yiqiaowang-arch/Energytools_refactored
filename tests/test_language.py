"""Tests for energytools.common.language.

Covers the ``Language`` enum (codes and workbook indices 1/2/3) and the
``TrilingualText`` DE/FR/IT label triple with German fallback.
"""

from __future__ import annotations

import pytest

from energytools.common.errors import UnknownLanguageError
from energytools.common.language import Language, TrilingualText


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("de", Language.DE),
        ("DE", Language.DE),
        ("De", Language.DE),
        ("fr", Language.FR),
        ("FR", Language.FR),
        ("it", Language.IT),
        ("IT", Language.IT),
        ("1", Language.DE),
        ("2", Language.FR),
        ("3", Language.IT),
        (" de ", Language.DE),
    ],
)
def test_language_parse_accepts_codes_and_indices(value: str, expected: Language) -> None:
    assert Language.parse(value) is expected


def test_language_parse_accepts_members() -> None:
    assert Language.parse(Language.FR) is Language.FR


@pytest.mark.parametrize("value", ["en", "0", "4", "deu", ""])
def test_language_parse_unknown_raises(value: str) -> None:
    with pytest.raises(UnknownLanguageError) as exc_info:
        Language.parse(value)
    assert str(exc_info.value) == f"Unknown language '{value}' (expected de, fr or it)"


def test_language_members_and_values() -> None:
    assert Language.DE.value == "de"
    assert Language.FR.value == "fr"
    assert Language.IT.value == "it"
    assert {language.value for language in Language} == {"de", "fr", "it"}


def test_trilingual_text_fields_and_as_dict() -> None:
    name = TrilingualText(de="Wohnen MFH", fr="Habitation CMI", it="Abitazione CMI")
    assert name.de == "Wohnen MFH"
    assert name.fr == "Habitation CMI"
    assert name.it == "Abitazione CMI"
    assert name.as_dict() == {"de": "Wohnen MFH", "fr": "Habitation CMI", "it": "Abitazione CMI"}


def test_trilingual_text_defaults_to_empty() -> None:
    text = TrilingualText()
    assert text.as_dict() == {"de": "", "fr": "", "it": ""}


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        (Language.DE, "Wohnen MFH"),
        (Language.FR, "Habitation CMI"),
        (Language.IT, "Abitazione CMI"),
        ("de", "Wohnen MFH"),
        ("fr", "Habitation CMI"),
        ("it", "Abitazione CMI"),
        ("2", "Habitation CMI"),
    ],
)
def test_trilingual_text_get(language: Language | str, expected: str) -> None:
    name = TrilingualText(de="Wohnen MFH", fr="Habitation CMI", it="Abitazione CMI")
    assert name.get(language) == expected


def test_trilingual_text_get_falls_back_to_german_when_empty() -> None:
    text = TrilingualText(de="Büro", fr="Bureau")
    assert text.get("it") == "Büro"
    assert text.get(Language.IT) == "Büro"
    text = TrilingualText(de="Büro")
    assert text.get("fr") == "Büro"


def test_trilingual_text_get_all_empty_returns_empty_string() -> None:
    assert TrilingualText().get("de") == ""


def test_trilingual_text_get_unknown_language_raises() -> None:
    text = TrilingualText(de="Büro", fr="Bureau")
    with pytest.raises(UnknownLanguageError):
        text.get("en")


def test_trilingual_text_frozen() -> None:
    text = TrilingualText(de="Büro")
    with pytest.raises(AttributeError):
        text.de = "Wohnen"  # type: ignore[misc]
