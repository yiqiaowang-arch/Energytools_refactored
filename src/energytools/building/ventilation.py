"""Ventilation — one ventilation system (Lüftung) attached to a room."""

from __future__ import annotations


class Ventilation:
    """One ventilation system of a room (natural ventilation = none).

    Args:
        volume_flow: Standard volume flow (m³/h).
        sfp: Specific fan power (W/(m³/h)).
        fan_power: Fan motor power (kW) — derived from ``volume_flow * sfp``
            when omitted.
        regulation: ``"1-stufig" | "2-stufig" | "stufenlos"``.
        full_load_hours: Annual full-load hours (h/a).
        wrg: Heat-recovery efficiency 0-1.
        kuehlfall_t: Supply-air setpoint, cooling case (°C).
        heizfall_t: Supply-air setpoint, heating case (°C).
    """

    def __init__(
        self,
        volume_flow: float,
        sfp: float = 0.8,
        fan_power: float | None = None,
        regulation: str = "1-stufig",
        full_load_hours: float = 3000.0,
        wrg: float = 0.8,
        kuehlfall_t: float = 20.0,
        heizfall_t: float = 21.0,
    ) -> None:
        if volume_flow < 0:
            raise ValueError(f"negative volume flow {volume_flow}")
        if not 0.0 <= wrg <= 1.0:
            raise ValueError(f"WRG {wrg} outside 0-1")
        if regulation not in ("1-stufig", "2-stufig", "stufenlos"):
            raise ValueError(f"unknown Regelung {regulation!r}")
        self.volume_flow = volume_flow
        self.sfp = sfp
        self.fan_power = fan_power if fan_power is not None else volume_flow * sfp / 1000.0
        self.regulation = regulation
        self.full_load_hours = full_load_hours
        self.wrg = wrg
        self.kuehlfall_t = kuehlfall_t
        self.heizfall_t = heizfall_t

    def __repr__(self) -> str:
        return (
            f"Ventilation({self.volume_flow} m3/h, {self.fan_power:.2f} kW fan, "
            f"{self.full_load_hours} h/a)"
        )
