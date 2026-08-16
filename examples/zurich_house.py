"""Zürich three-storey house — the object-oriented way.

Building: 600 m² over three storeys in Zürich (climate station 40 =
Zürich-MeteoSchweiz, the dataset default).

Space breakdown (from the owner's room list):
    200 m²  ground floor  — commercial: Fachgeschäft (5.02)
    400 m²  upper floors  — residential: 200 m² bedrooms + 100 m² living
                            room + 30 m² bathroom + 20 m² kitchen
                            (all Wohnen MFH 1.01) and 50 m² garage
                            (Parkhaus 12.09)

Every number the engine uses is annotated with its data source below.
Run:  pixi run -e dev python examples/zurich_house.py
"""

from __future__ import annotations

from energytools.building import (
    Building,
    Climate,
    Generation,
    Room,
    RoomType,
    Ventilation,
)
from energytools.raumdaten import load_dataset

# ---------------------------------------------------------------------------
# 1. The library: dataset release -> room-type classes + climate class
# ---------------------------------------------------------------------------
# 45 SIA 2024 room uses are the *classes*; 40 climate stations are the
# *climate classes*.  The library itself is immutable — buildings and rooms
# copy from it and may diverge.
ds = load_dataset("V221")
shop = RoomType.from_dataset(ds, "5.02")   # Fachgeschäft
flat = RoomType.from_dataset(ds, "1.01")   # Wohnen MFH
garage = RoomType.from_dataset(ds, "12.09")  # Parkhaus
zurich = Climate.from_dataset(ds, 40)      # Zürich-MeteoSchweiz

# Where the type parameters come from (dataset lookups, annotated):
#   5.02: 1.1.2.9 Personenfläche 8 m²/Person · 1.1.3.3 Geräte 2 W/m² ·
#         1.1.4.1 Beleuchtung 300 lx · 1.1.8.4 Warmwasser 1.5 l/(P·d) ·
#         hygienic fresh air 1.1.5.2 = 3.625 m³/(h·m²)
#   1.01: 35 m²/Person · 10 W/m² · 150 lx · 35 l/(P·d)
#   12.09: 1 W/m² · no persons, no hot water, no fresh air

# ---------------------------------------------------------------------------
# 2. The building and its rooms (your 600 m², mapped onto SIA 2024 uses)
# ---------------------------------------------------------------------------
b = Building(name="Mein Haus", climate=zurich, standard="standard")  # standard|zielwert|bestand
b.add_room(Room("Laden", type=shop, area=200, ebf=True))             # 商业 200
b.add_room(Room("Schlaf", type=flat, area=200))                      # 客房 200
b.add_room(Room("Wohnen", type=flat, area=100))                      # 起居 100
b.add_room(Room("Bad", type=flat, area=30))                          # 卫浴 30
b.add_room(Room("Küche", type=flat, area=20))                        # 厨房 20
b.add_room(Room("Garage", type=garage, area=50, ebf=False, heated=False))  # 车库 50

# ---------------------------------------------------------------------------
# 3. Editable schedules — per room, copied from the type (dataset defaults)
# ---------------------------------------------------------------------------
# 5.02 weekday curve: closed at 18:00 -> the shop stays open a bit longer
b.room("Laden").schedules.occupancy[18] *= 0.8
# 1.01 curve: everyone is home at night -> the bathroom is used at 07:00
b.room("Bad").schedules.occupancy[7] = 1.0

# ---------------------------------------------------------------------------
# 4. Ventilation on the room, generation on the building (and rooms)
# ---------------------------------------------------------------------------
# Shop ventilation sized from the dataset: 200 m² × 3.625 m³/(h·m²) = 725 m³/h,
# fan 725 × SFP 0.8 = 0.58 kW, full-load hours 6260 h/a (Volll_Lüft 5.02).
b.room("Laden").ventilation = Ventilation(
    volume_flow=725.0, sfp=0.8, full_load_hours=6260.0, wrg=0.8
)
# Building-level generation: gas boiler (WE02) + electric hot water (W13)
b.add_generation(Generation("WE02", coverage=1.0, losses=0.1))
b.add_generation(Generation("W13", coverage=1.0, losses=0.4))
# Room-level generation example: the bathroom heats itself electrically
# (WE08 "Elektro direkt", η = 1.0), so its heating never reaches the boiler.
b.room("Bad").add_generation(Generation("WE08", coverage=1.0, losses=0.0))

# ---------------------------------------------------------------------------
# 5. Lazy results — computed on first access, invalidated automatically
# ---------------------------------------------------------------------------
print(f"=== {b.name} ({zurich}) ===")
print(f"area:  {b.area}")

load = b.load
print("\n--- annual loads (MWh/a) ---")
for kind in ("heating", "cooling", "ww", "electricity"):
    category = getattr(load, kind)
    print(f"{kind:12s} {category.total:8.2f}  " + ", ".join(
        f"{room}: {value:.2f}" for room, value in category.annually.items()
    ))

print("\n--- hourly (8760 h, kW) ---")
schlaf_heating = load.heating.hourly["Schlaf"]
print(f"Schlaf heating: 8760 values, sum = {sum(schlaf_heating):.2f} MWh "
      f"(== annually {load.heating.annually['Schlaf']:.2f})")
print(f"Schlaf heating Jan 1 00:00..05:00: "
      f"{[round(v, 3) for v in schlaf_heating[:6]]}")

print("\n--- final end energy per carrier (MWh/a) ---")
print({carrier: round(value, 2) for carrier, value in load.totals.items()})
print("end energy per kind:", {k: round(v, 2) for k, v in load.end_energy.items()})

# Lazy invalidation: edit a schedule, the next access recomputes the
# hourly distribution (the annual KPI totals stay — schedules decide *when*
# the verified annual demand occurs, not its size).
b.room("Laden").schedules.occupancy[19] = 0.0  # close at 19:00 now
laden_elec_before = load.electricity.hourly["Laden"]
laden_elec_after = b.load.electricity.hourly["Laden"]
print("\n--- after closing the shop at 19:00 ---")
print(f"Laden electricity at 19:00: {laden_elec_before[19]:.4f} kW "
      f"-> {laden_elec_after[19]:.4f} kW (recomputed on access)")
