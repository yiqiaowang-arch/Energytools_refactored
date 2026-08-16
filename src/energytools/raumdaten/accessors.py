"""Attribute-style accessors for the Raumdaten dataset.

The workbook keys (room-use codes like ``"3.01"``, parameter ids like
``"1.1.2.9"``) stay in the data model, but everyday users should not have to
remember them: this module provides attribute access with full IDE support.

The concrete ``@property`` accessors are **generated** from the dataset by
``tools/generate_accessors.py`` into :mod:`energytools.raumdaten._generated`
(committed), so typing ``ds.room_uses.`` or ``profile.`` shows the complete
list in the IDE and every accessor carries a docstring with the German name:

    ds.room_uses.group_office          # RoomUse (3.01 Einzel-, Gruppenbüro)
    profile.personnel_area             # ParameterAccessor (1.1.2.9 Personenfläche)
    profile.personnel_area.standard    # ParameterValue(value=14, unit=m2)
    profile.personnel_area.standard.value

Slug sources, in priority order:

* room uses: curated English slugs (stable, human-readable);
* parameters: curated English alias slugs for the commonly asked parameters,
  falling back to the workbook symbol (sanitized) and then to a slugified
  German label.
"""

from __future__ import annotations

from typing import Any, Iterator

from energytools.common.errors import UnknownRoomUseError
from energytools.common.valuekind import ValueKind
from energytools.raumdaten._generated import ParameterProperties, RoomUseProperties
from energytools.raumdaten._slugs import (
    PARAMETER_ALIASES,
    ROOM_USE_SLUGS,
    parameter_slug,
    slugify_label,
)

__all__ = [
    "ROOM_USE_SLUGS",
    "PARAMETER_ALIASES",
    "RoomUseCatalog",
    "ParameterCatalog",
    "ParameterAccessor",
    "slugify_label",
    "parameter_slug",
]

_SLUG_TO_CODE: dict[str, str] = {v: k for k, v in ROOM_USE_SLUGS.items()}
_ALIAS_TO_PARAM: dict[str, str] = {v: k for k, v in PARAMETER_ALIASES.items()}


# ---------------------------------------------------------------------------
# Catalogs (attribute access via generated static @property mixins)
# ---------------------------------------------------------------------------
class RoomUseCatalog(RoomUseProperties):
    """Attribute access to the 45 standard room uses (generated ``@property``s).

    ``ds.room_uses.group_office`` == ``ds.room_use("3.01")``.
    Also supports ``ds.room_uses["3.01"]``, ``ds.room_uses["group_office"]``,
    ``ds.room_uses[5]`` and iteration.
    """

    def __init__(self, room_uses: list[Any]) -> None:
        self._by_nutzid: dict[int, Any] = {ru.nutzid: ru for ru in room_uses}
        self._by_code: dict[str, Any] = {ru.code: ru for ru in room_uses}
        self._by_slug: dict[str, Any] = {}
        for ru in room_uses:
            slug = ROOM_USE_SLUGS.get(ru.code)
            if slug:
                self._by_slug[slug] = ru

    def _room_use_by_slug(self, slug: str) -> Any:
        try:
            return self._by_slug[slug]
        except KeyError:
            raise AttributeError(
                f"no room use named {slug!r}; try a code ('3.01'), another slug, "
                f"or ds.room_uses['group_office']"
            ) from None

    def __getattr__(self, name: str) -> Any:
        # Fallback for typos with a helpful message; real accessors come from
        # the generated mixin (static @property), so IDE autocompletion works.
        raise AttributeError(
            f"no room use named {name!r}; available slugs include: "
            f"{', '.join(sorted(self._by_slug)[:12])}, …"
        )

    def __call__(self) -> tuple[Any, ...]:
        """Compatibility: ``ds.room_uses()`` returns the tuple of room uses."""
        return tuple(self._by_nutzid.values())

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            try:
                return self._by_nutzid[key]
            except KeyError:
                raise UnknownRoomUseError(key) from None
        if key in self._by_code:
            return self._by_code[key]
        if key in _SLUG_TO_CODE:
            return self._by_code[_SLUG_TO_CODE[key]]
        raise KeyError(f"unknown room use {key!r} (try a code like '3.01', a slug like 'group_office', or a nutzid)")

    def __iter__(self) -> Iterator[Any]:
        return iter(self._by_nutzid.values())

    def __len__(self) -> int:
        return len(self._by_nutzid)

    def __repr__(self) -> str:
        items = ", ".join(f"{slug}={ru.code} {ru.name.de}" for slug, ru in list(self._by_slug.items())[:6])
        return f"RoomUseCatalog({len(self)} room uses; {items}, …)"


class ParameterCatalog(ParameterProperties):
    """Attribute access to the parameter catalog (generated ``@property``s).

    ``ds.parameters.personnel_area`` -> :class:`Parameter` (``1.1.2.9``).
    """

    def __init__(self, parameters: list[Any]) -> None:
        self._by_id: dict[str, Any] = {p.id: p for p in parameters}
        self._by_slug: dict[str, Any] = {
            parameter_slug(p.id, p.symbol, p.label.de if p.label else ""): p
            for p in parameters
        }
        self._accessor_by_slug: dict[str, ParameterAccessor] = {}

    def _parameter_by_slug(self, slug: str) -> Any:
        try:
            return self._by_slug[slug]
        except KeyError:
            raise AttributeError(
                f"no parameter named {slug!r}; use ds.parameters['1.1.2.9'] or one of: "
                f"{', '.join(sorted(self._by_slug)[:12])}, …"
            ) from None

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(
            f"no parameter named {name!r}; available slugs include: "
            f"{', '.join(sorted(self._by_slug)[:12])}, …"
        )

    def __call__(self) -> list[Any]:
        """Compatibility: ``ds.parameters()`` returns the list of parameters."""
        return list(self._by_id.values())

    def __getitem__(self, key: str) -> Any:
        if key in self._by_id:
            return self._by_id[key]
        if key in _ALIAS_TO_PARAM:
            return self._by_id[_ALIAS_TO_PARAM[key]]
        raise KeyError(f"unknown parameter {key!r} (try an id like '1.1.2.9' or a slug)")

    def __iter__(self) -> Iterator[Any]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"ParameterCatalog({len(self)} parameters)"


class ParameterAccessor:
    """Value accessor: ``profile.personnel_area.standard.value``.

    ``standard`` / ``zielwert`` / ``bestand`` are real ``@property``s
    returning the :class:`ParameterValue`; ``.value`` / ``.unit`` forward to
    the standard value for convenience.
    """

    def __init__(self, parameter_id: str, values: dict[ValueKind, Any], label: str | None = None) -> None:
        self._id = parameter_id
        self._values = values
        self._label = label or parameter_id

    @property
    def standard(self) -> Any:
        return self._kind(ValueKind.STANDARD)

    @property
    def zielwert(self) -> Any:
        return self._kind(ValueKind.ZIELWERT)

    @property
    def bestand(self) -> Any:
        return self._kind(ValueKind.BESTAND)

    def _kind(self, vk: ValueKind) -> Any:
        try:
            return self._values[vk]
        except KeyError:
            raise AttributeError(
                f"{self._label}: no {vk.value} value in this profile "
                f"(available: {', '.join(k.value for k in self._values)})"
            ) from None

    @property
    def value(self) -> Any:
        """The standard value (or the only available value)."""
        if ValueKind.STANDARD in self._values:
            return self._values[ValueKind.STANDARD].value
        return next(iter(self._values.values())).value

    @property
    def unit(self) -> Any:
        if ValueKind.STANDARD in self._values:
            return self._values[ValueKind.STANDARD].unit
        return next(iter(self._values.values())).unit

    def __repr__(self) -> str:
        parts = ", ".join(f"{k.value}={v.value} {v.unit.symbol}" for k, v in self._values.items())
        return f"ParameterAccessor({self._label}: {parts})"
