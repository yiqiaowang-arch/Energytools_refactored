# Quickstart

`energytools` replaces the SIA 2024 Excel tools (Raumdatenblätter and
Gebäude-Tool) with a Python package: the **dataset** holds every table of
the workbooks as JSON, the **engine** reproduces the calculations exactly
(verified against the workbook's own cached values), and the **building
domain layer** gives you an object-oriented way to model and evaluate a
building.

## 1. Install and load the library

```bash
pip install energytools            # the package
pixi run -e dev python              # or: the repo's dev environment
```

```python
from energytools.raumdaten import load_dataset

ds = load_dataset("V221")          # the SIA 2024 dataset release
```

The dataset is the frozen library: 45 room-use **types** (SIA 2024
Raumnutzungen), 193 parameters, 40 climate stations, per-room-use
schedules, Qhc matrices, design days and category tables — everything the
workbooks contain, extracted once and checksum-verified.

## 2. Model your building (the object API)

```python
from energytools.building import Building, Climate, Room, RoomType

zurich = Climate.from_dataset(ds, 40)          # Zürich-MeteoSchweiz
shop   = RoomType.from_dataset(ds, "5.02")     # Fachgeschäft
flat   = RoomType.from_dataset(ds, "1.01")     # Wohnen MFH
garage = RoomType.from_dataset(ds, "12.09")    # Parkhaus

b = Building(name="Mein Haus", climate=zurich, standard="standard")
b.add_room(Room("Laden",  type=shop,   area=200, ebf=True))
b.add_room(Room("Schlaf", type=flat,   area=200))
b.add_room(Room("Wohnen", type=flat,   area=100))
b.add_room(Room("Bad",    type=flat,   area=30))
b.add_room(Room("Küche",  type=flat,   area=20))
b.add_room(Room("Garage", type=garage, area=50, ebf=False, heated=False))
```

Every intensity (persons per m², device/lighting power, hot water, ...)
comes from the room's **type**; the room only needs its name, type, area
and the envelope flags (`ebf` = heated envelope, `heated`, `conditioned`).

## 3. Adjust the schedules (per room, editable)

```python
b.room("Laden").schedules.occupancy[18] *= 0.8   # shop closes later
b.room("Bad").schedules.occupancy[7] = 1.0        # morning shower peak
```

Each room owns a copy of its type's default curves (occupancy / device /
lighting, each with 24 h, 7-day and 12-month axes) — editing a room never
touches the library.

## 4. Ventilation on the room, generation on the building (or the room)

```python
from energytools.building import Generation, Ventilation

b.room("Laden").ventilation = Ventilation(
    volume_flow=725.0, sfp=0.8, full_load_hours=6260.0, wrg=0.8
)
b.add_generation(Generation("WE02", coverage=1.0, losses=0.1))  # gas boiler
b.add_generation(Generation("W13",  coverage=1.0, losses=0.4))  # electric WW
b.room("Bad").add_generation(Generation("WE08", coverage=1.0))  # electric heater
```

Room-level generators cover the room's own demand first; the remaining
demand flows into the building-level groups.

## 5. Lazy results — areas, annual loads, hourly series

```python
print(b.area)                    # Area(ngf=600, ebf=550, gf=605)
print(b.load.heating.annually)   # {room: MWh/a}
print(b.load.electricity.hourly) # 8760 h series per room
print(b.load.totals)             # final end energy per carrier
```

`b.load` is computed on first access and invalidated automatically when
rooms, schedules, ventilation or generation change. The hourly series
distribute the verified annual values by the room's own schedules, so
`sum(hourly) == annually` by construction.

## 6. Design-day balances (the workbook's heat/air-quality blocks)

```python
rows = b.design_day(room)   # 24 h summer heat balance (August design day)
air  = b.air_quality(room)  # 24 h CO₂/moisture balance (March)
```

Both reproduce the workbook's `Wärmebilanz-Sommertag` and `Stoffbilanz`
blocks exactly (verified against the workbook's cached values), with all
inputs assembled from the dataset.

## 7. What lies underneath

- `energytools.raumdaten` — the dataset service (load, extract, validate).
- `energytools.engine` — `Engine` + backends; `NativeBackend` runs the
  real calculation chain (psychrometrics → AHU temperature-bin → building
  aggregation → generation catalogue → Resultate).
- The engine-level API (`BuildingInput`/`RoomRow`) still exists for
  headless use; the object API above compiles to it internally.

See also: [API Reference (auto)](api-reference/index.md),
[Excel equivalence](excel-equivalence.md).
