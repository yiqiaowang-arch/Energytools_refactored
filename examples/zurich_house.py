"""Zürich three-storey house — a fully annotated real-calculation example.

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

from energytools.engine import Engine, NativeBackend
from energytools.engine.model import (
    BuildingInput,
    GenerationSystem,
    RoomRow,
    ValueKind,
    VentilationSystem,
)
from energytools.raumdaten import load_dataset

# ---------------------------------------------------------------------------
# 1. Dataset — one frozen release, everything below comes from it
# ---------------------------------------------------------------------------
ds = load_dataset("V221")

# ---------------------------------------------------------------------------
# 2. Rooms — your 600 m², mapped onto SIA 2024 room uses
# ---------------------------------------------------------------------------
# Each RoomRow needs: the SIA 2024 room-use code, the net floor area (ngf)
# and whether the room is part of the heated envelope (ebf).  All other
# intensities are looked up from the dataset, not typed in.
rooms = (
    # commercial part (ground floor)
    RoomRow(
        name="Laden (Fachgeschäft)",
        room_use_id="5.02",
        ebf=True,          # heated
        ngf=200.0,         # m² — your 200 m² commercial
        lueftung_system="LA01",
        gekuehlt=False,
        beheizt=True,
    ),
    # residential part (upper floors), split into your rooms; SIA 2024
    # uses one Wohnen MFH profile for all of them
    RoomRow(name="Schlafzimmer", room_use_id="1.01", ebf=True, ngf=200.0, beheizt=True),
    RoomRow(name="Wohnzimmer", room_use_id="1.01", ebf=True, ngf=100.0, beheizt=True),
    RoomRow(name="Bad", room_use_id="1.01", ebf=True, ngf=30.0, beheizt=True),
    RoomRow(name="Küche", room_use_id="1.01", ebf=True, ngf=20.0, beheizt=True),
    # garage — SIA 2024 has no private-garage use; Parkhaus 12.09 is the
    # closest; unheated, no persons
    RoomRow(name="Garage", room_use_id="12.09", ebf=False, ngf=50.0, beheizt=False),
)

# ---------------------------------------------------------------------------
# 3. Where the room numbers come from (dataset lookups)
# ---------------------------------------------------------------------------
def show_room_data() -> None:
    for code in ("5.02", "1.01", "12.09"):
        ru = ds.room_use(code)
        p = ds.profile(ru.nutzid)
        s = ds.schedules[ru.nutzid]
        vals = {
            pid: {k.value: v.value for k, v in byk.items()}
            for pid, byk in p.values.items()
            if pid
            in (
                "1.1.2.9",  # Personenfläche (m²/Person) → occupancy density
                "1.1.3.3",  # Geräte (W/m²) → device power
                "1.1.4.1",  # Beleuchtungsstärke (lx) → lighting level
                "1.1.8.4",  # Warmwasser (l/Person·d) → WW demand
            )
        }
        print(f"  {code} {ru.name.de}:")
        for pid, byk in vals.items():
            print(f"    parameter {pid}: {byk}")
        print(
            f"    schedule person 24h: {[round(x, 2) for x in s.person_fraction]}"
        )
        print(
            f"    schedule weekly (Sat first): {[round(x, 2) for x in s.weekly_fraction]}"
            f"  rest days: {s.rest_days_per_week}"
        )

print("=== where the intensities come from ===")
show_room_data()

# ---------------------------------------------------------------------------
# 4. Ventilation — one system for the shop; the residential part is
#    naturally ventilated (no system).  Sized from the dataset itself:
#    hygienic fresh air 5.02 = 3.625 m³/(h·m²)  ->  200 m² -> 725 m³/h,
#    fan power = 725 × SFP 0.8 W/(m³/h) = 0.58 kW,
#    full-load hours from the Volll_Lüft table (5.02, 1-stufig = 6260 h/a).
# ---------------------------------------------------------------------------
ventilation = (
    VentilationSystem(
        id="LA01",
        room_use="5.02",
        volume_flow_standard=725.0,   # m³/h = 200 m² × 1.1.5.2 (3.625)
        sfp=0.8,                      # W/(m³/h) — SFP value
        fan_power=0.58,               # kW = 725 × 0.8 / 1000
        regulation="1-stufig",
        full_load_hours=6260.0,       # h/a — Volll_Lüft 5.02 1-stufig
        wrg=0.8,                      # heat recovery efficiency
        kuehlfall_t=20.0,             # supply temp cooling case
        heizfall_t=21.0,              # supply temp heating case
    ),
)

# ---------------------------------------------------------------------------
# 5. Generation — gas boiler for heating, electric for hot water
# ---------------------------------------------------------------------------
generation = (
    GenerationSystem(id="WE1", kind="heating", catalog_code="WE02", coverage=1.0, losses=0.1),
    GenerationSystem(id="WW1", kind="ww", catalog_code="W13", coverage=1.0, losses=0.4),
)

# ---------------------------------------------------------------------------
# 6. Calculate — NativeBackend consumes the real dataset (station 40 Zürich)
# ---------------------------------------------------------------------------
building = BuildingInput(
    name="Zürich Dreifamilienhaus (600 m²)",
    rooms=rooms,
    ventilation=ventilation,
    generation=generation,
    value_kind=ValueKind.STANDARD,
    climate_station_id=40,  # Zürich-MeteoSchweiz
)

result = Engine().calculate(
    building, "V221", "1.0.0", backend=NativeBackend()
)

print("\n=== result ===")
for key, value in result.totals.items():
    print(f"  {key:32s} {value:12.3f}")
print("  per carrier:", {k: round(v, 2) for k, v in result.per_carrier.items()})
print("  trace:", [step.id for step in result.trace.steps])

# ---------------------------------------------------------------------------
# 7. Climate the engine used (station 40 = Zürich-MeteoSchweiz)
# ---------------------------------------------------------------------------
station = ds.climate().station(40)
print("\n=== climate (station 40) ===")
print(f"  {station.name.de}, canton {station.canton}, "
      f"elevation {station.winter_design['elevation'].value} m")
print(f"  winter design: t_a = {station.winter_design['t_a'].value} °C, "
      f"HDD = {station.hdd.value} K·d")
print(f"  summer design days: "
      f"{[(d.month, len(d.temperature)) for d in station.design_days]}")
print(f"  AHU bins: {len(station.temperature_bins)} temperature bins, "
      f"{len(station.bin_humidity_ratio)} humidity ratios")
