"""Shared test helpers for the engine milestone tests.

Room names and workbook terms stay German on purpose (Büro, Sitzungszimmer,
Gebäude, Lüftung, Erzeugung) — the domain terms the engine is ported from.
"""

from __future__ import annotations

import datetime

from energytools.engine.model import (
    BuildingInput,
    GenerationSystem,
    RoomRow,
    VentilationSystem,
)


def make_building_input(**overrides: object) -> BuildingInput:
    """A valid example building input (Zürich-MeteoSchweiz, station 40).

    Room 1: Büro with Geräte/Beleuchtung and an LA03 Lüftung reference.
    Room 2: Sitzungszimmer with a 50 % share of its NGF.
    """
    rooms = (
        RoomRow(
            name="Büro 1",
            room_use_id="1.01",
            ebf=True,
            ngf=1200.0,
            geraete=8.0,
            beleuchtung=10.0,
            lueftung_system="LA03",
            lueftung_volume_flow=4000.0,
            gekuehlt=True,
        ),
        RoomRow(
            name="Sitzungszimmer",
            room_use_id=2,
            ebf=True,
            ngf=300.0,
            share=0.5,
            geraete=5.0,
        ),
    )
    ventilation = (
        VentilationSystem(
            id="LA03",
            room_use="1.01",
            regulation="2-stufig",
            volume_flow_standard=4000.0,
            sfp=1.8,
            fan_power=7.5,
            full_load_hours=3900.0,
            wrg=0.7,
        ),
    )
    generation = (
        GenerationSystem(
            id="KE1",
            kind="cooling",
            catalog_code="KE01",
            coverage=1.0,
            losses=0.05,
            nominal_power=120.0,
        ),
    )
    data: dict[str, object] = {
        "name": "Beispiel",
        "author": "Max Muster",
        "date": datetime.date(2025, 1, 15),
        "climate_station_id": 40,
        "rooms": rooms,
        "ventilation": ventilation,
        "generation": generation,
    }
    data.update(overrides)
    return BuildingInput(**data)  # type: ignore[arg-type]
