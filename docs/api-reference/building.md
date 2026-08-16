# energytools.building

The object-oriented user-facing domain layer: buildings, rooms, room
types, climate, editable schedules and lazy loads.  This is the API the
end user works with — the dataset (``energytools.raumdaten``) and the
engine (``energytools.engine``) stay underneath and are used through it:

```python
ds      = load_dataset("V221")
zurich  = Climate.from_dataset(ds, 40)
shop    = RoomType.from_dataset(ds, "5.02")

b = Building(name="Mein Haus", climate=zurich, standard="standard")
b.add_room(Room("Laden", type=shop, area=200, ebf=True))
b.room("Laden").schedules.occupancy[18] *= 0.8   # editable per room
b.add_generation(Generation("WE02", coverage=1.0, losses=0.1))

print(b.area)                    # Area(ngf=..., ebf=..., gf=...)
print(b.load.heating.annually)   # {room: MWh}
print(b.load.electricity.hourly) # 8760 h x rooms
```

::: energytools.building
    options:
      members_order: source
