"""Room — one room of a building (an *instance* of a RoomType).

A room owns editable copies of the type's default schedules, optionally a
ventilation system and optionally its own generators (room-level Erzeugung,
e.g. a bathroom electric heater or a room air conditioner).  Rooms are
mutable; changing anything invalidates the building's lazy load.
"""

from __future__ import annotations

from typing import Callable

from energytools.building.generation import Generation
from energytools.building.roomtype import RoomType
from energytools.building.schedules import Schedules
from energytools.building.ventilation import Ventilation


class Room:
    """One room.

    Args:
        name: Room name (unique within the building).
        type: The :class:`RoomType` (SIA 2024 room use).
        area: Net floor area (m²).
        ebf: Part of the heated envelope (Energiebezugsfläche), default True.
        heated: Heated (Raumheizung), default True.
        conditioned: Mechanically cooled (Raumkühlung), default False.
        warm_water: Hot-water demand (Warmwasser), default False.
    """

    def __init__(
        self,
        name: str,
        type: RoomType,
        area: float,
        ebf: bool = True,
        heated: bool = True,
        conditioned: bool = False,
        warm_water: bool = False,
        _on_change: Callable[[], None] | None = None,
    ) -> None:
        if not name.strip():
            raise ValueError("room name must not be empty")
        if area < 0:
            raise ValueError(f"negative area {area}")
        self.name = name
        self.type = type
        self.area = area
        self.ebf = ebf
        self.heated = heated
        self.conditioned = conditioned
        self.warm_water = warm_water
        self.schedules = type.default_schedules()
        self.ventilation: Ventilation | None = None
        self._generations: list[Generation] = []
        self._on_change = _on_change

    # -- generation ---------------------------------------------------------

    @property
    def generations(self) -> tuple[Generation, ...]:
        """The room-level generators (room-level Erzeugung)."""
        return tuple(self._generations)

    def add_generation(self, generation: Generation) -> None:
        """Attach a generator that covers part of this room's demand."""
        self._generations.append(generation)
        self._changed()

    # -- internals ----------------------------------------------------------

    def _changed(self) -> None:
        if self._on_change is not None:
            self._on_change()

    def __repr__(self) -> str:
        return f"Room({self.name!r}, {self.type.code}, {self.area} m²)"
