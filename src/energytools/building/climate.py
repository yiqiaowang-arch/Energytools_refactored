"""Climate — the climate *class* of a location.

A :class:`Climate` is the library entry of one of the 40 SIA 2024 climate
stations: winter/summer design conditions, monthly values, the 61-bin
temperature distribution of the AHU engine and the summer design days.
"""

from __future__ import annotations

from typing import Any


class Climate:
    """One climate station (``Klimastation``), read-only.

    Args:
        station_id: 1-40 (40 = Zürich-MeteoSchweiz, the dataset default).
        name: Station name.
        dataset: The dataset release this climate belongs to.
    """

    def __init__(self, station_id: int, name: str, dataset: Any) -> None:
        self.station_id = station_id
        self.name = name
        self._dataset = dataset

    @classmethod
    def from_dataset(cls, dataset: Any, station_id: int) -> "Climate":
        """Look up a station by id (1-40)."""
        station = dataset.climate().station(station_id)
        return cls(station_id=station.id, name=station.name.de, dataset=dataset)

    # -- design conditions --------------------------------------------------

    def winter_design(self) -> dict[str, Any]:
        """The winter design values of the station (Quantities)."""
        return self._dataset.climate().station(self.station_id).winter_design

    def design_days(self) -> tuple[Any, ...]:
        """The 96-hour summer design days (June/August)."""
        return self._dataset.climate().station(self.station_id).design_days

    def monthly_temperature(self) -> tuple[float, ...]:
        """The 12 monthly outdoor temperatures (°C)."""
        station = self._dataset.climate().station(self.station_id)
        profile = station.monthly.get("t_aussen")
        return profile.values if profile is not None else (10.0,) * 12

    def __repr__(self) -> str:
        return f"Climate({self.station_id} {self.name})"
