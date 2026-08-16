"""Load — the lazy per-kind calculation result of a building.

``Building.load`` returns a :class:`Load` with one :class:`LoadCategory`
per kind — heating, cooling, ww, electricity — each carrying the annual
table (room → MWh) and the 8760-hour series per room.  The 8760 series is
the verified annual value distributed by the room's own schedules
(occupancy/device/lighting × week × month, temperature-weighted for
heating/cooling), so ``sum(hourly) == annually`` by construction.
"""

from __future__ import annotations

from typing import Mapping


class LoadCategory:
    """One load kind of the building.

    Args:
        name: ``"heating" | "cooling" | "ww" | "electricity"``.
        annually: Room name -> annual demand (MWh).
        hourly: Room name -> 8760 hourly values (kW).
    """

    def __init__(
        self,
        name: str,
        annually: Mapping[str, float],
        hourly: Mapping[str, list[float]],
    ) -> None:
        self.name = name
        self.annually = dict(annually)
        self.hourly = {room: list(values) for room, values in hourly.items()}

    @property
    def total(self) -> float:
        """The annual building total of this kind (MWh)."""
        return sum(self.annually.values())

    def __repr__(self) -> str:
        return f"LoadCategory({self.name}, {self.total:.3f} MWh/a)"


class Load:
    """The lazy calculation result of a building.

    ``heating`` / ``cooling`` / ``ww`` / ``electricity`` are
    :class:`LoadCategory` objects; ``totals`` is the final end energy per
    carrier (MWh) after the generation systems.
    """

    def __init__(
        self,
        heating: LoadCategory,
        cooling: LoadCategory,
        ww: LoadCategory,
        electricity: LoadCategory,
        totals: Mapping[str, float],
        end_energy: Mapping[str, float],
    ) -> None:
        self.heating = heating
        self.cooling = cooling
        self.ww = ww
        self.electricity = electricity
        self.totals = dict(totals)
        self.end_energy = dict(end_energy)

    @property
    def annually(self) -> dict[str, float]:
        """The annual building totals per kind (MWh)."""
        return {
            "heating": self.heating.total,
            "cooling": self.cooling.total,
            "ww": self.ww.total,
            "electricity": self.electricity.total,
        }

    def __repr__(self) -> str:
        return f"Load(heating={self.heating.total:.1f}, cooling={self.cooling.total:.1f}, ww={self.ww.total:.1f}, electricity={self.electricity.total:.1f} MWh/a)"
