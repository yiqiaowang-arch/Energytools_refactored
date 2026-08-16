"""RoomType — a SIA 2024 room-use *class* (the "type" of a room).

A :class:`RoomType` is the immutable library entry of one of the 45 SIA
2024 room uses: its parameters (person density, device/lighting power,
hot-water demand, ...), its default schedules and its KPI intensities.
Rooms are *instances* of a type and copy the defaults so they can be
edited without touching the library.

The German parameter labels of the workbook are kept (Standard / Zielwert
/ Bestand); ``standard`` selects the value kind of a building.
"""

from __future__ import annotations

from typing import Any

from energytools.building.schedules import Schedules


class RoomType:
    """One SIA 2024 room-use class (``Raumnutzung``), read-only.

    Args:
        code: SIA code (``"5.02"``).
        name: German name (``"Fachgeschäft"``).
        nutzid: Dataset row id (1-45).
        dataset: The dataset release this type belongs to (used for the
            calculation; the type is only meaningful together with it).
    """

    def __init__(self, code: str, name: str, nutzid: int, dataset: Any) -> None:
        self.code = code
        self.name = name
        self.nutzid = nutzid
        self._dataset = dataset

    # -- factory ------------------------------------------------------------

    @classmethod
    def from_dataset(cls, dataset: Any, room_use: str | int) -> RoomType:
        """Look up a type by SIA code (``"5.02"``) or nutzid (``15``)."""
        room = dataset.room_use(room_use)
        return cls(code=room.code, name=room.name.de, nutzid=room.nutzid, dataset=dataset)

    # -- parameter access ---------------------------------------------------

    def parameter(self, parameter_id: str, kind: str = "standard") -> float | None:
        """One parameter value (e.g. ``1.1.2.9`` Personenfläche), or ``None``.

        ``None`` covers parameters that do not apply to this room use (no
        persons, no hot water, ...); an unknown parameter id raises.
        """
        profile = self._dataset.profile(self.nutzid)
        try:
            value = profile.value(parameter_id, kind)
        except (KeyError, TypeError, ValueError):
            return None
        return value.value if value is not None else None

    def default_schedules(self) -> Schedules:
        """The default schedules of this type (editable copy per room)."""
        schedule = self._dataset.schedules[self.nutzid]
        return Schedules(
            occupancy_hourly=list(schedule.person_fraction),
            occupancy_weekly=list(schedule.weekly_fraction),
            occupancy_monthly=list(schedule.monthly_fraction),
            device_hourly=list(schedule.device_fraction),
            device_weekly=list(schedule.weekly_fraction),
            device_monthly=list(schedule.monthly_fraction),
            lighting_hourly=list(schedule.person_fraction),
            lighting_weekly=list(schedule.weekly_fraction),
            lighting_monthly=list(schedule.monthly_fraction),
        )

    def __repr__(self) -> str:
        return f"RoomType({self.code} {self.name})"
