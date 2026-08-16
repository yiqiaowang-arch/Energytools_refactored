# energytools.engine

The deterministic calculation engine: inputs, results, backends and the
explain trace.

```python
from energytools.engine import Engine, BuildingInput, RoomRow
project = BuildingInput(name="My building", rooms=(RoomRow(name="A", room_use_id=5, ebf=True, ngf=1000.0),))
result = Engine().calculate(project, "V221", "1.0.0")
```

::: energytools.engine
