"""energytools.building — the object-oriented user-facing domain layer.

The user thinks in buildings, rooms, room types and climate — not in input
records.  This package provides that language on top of the verified
dataset (``energytools.raumdaten``) and the verified engine
(``energytools.engine``), which stay untouched:

    ds      = load_dataset("V221")
    zurich  = Climate.from_dataset(ds, 40)
    shop    = RoomType.from_dataset(ds, "5.02")

    b = Building(name="Mein Haus", climate=zurich, standard="standard")
    b.add_room(Room("Laden", type=shop, area=200, ebf=True))
    b.room("Laden").schedules.occupancy[18] *= 0.8   # editable per room
    b.add_generation(Generation("WE02", coverage=1.0, losses=0.1))

    print(b.area)                  # Area(ngf=600, ebf=550, gf=605)
    print(b.load.heating.annually) # {room: MWh}
    print(b.load.electricity.hourly)  # 8760 x rooms

``Building.load`` is lazy: computed on first access and invalidated
automatically when rooms, schedules, ventilation or generation change.
"""

from energytools.building.building import Area, Building
from energytools.building.climate import Climate
from energytools.building.generation import Generation
from energytools.building.load import Load, LoadCategory
from energytools.building.room import Room
from energytools.building.roomtype import RoomType
from energytools.building.schedules import Schedule, Schedules
from energytools.building.ventilation import Ventilation

__all__ = [
    "Area",
    "Building",
    "Climate",
    "Generation",
    "Load",
    "LoadCategory",
    "Room",
    "RoomType",
    "Schedule",
    "Schedules",
    "Ventilation",
]
