# energytools.raumdaten

The Raumdaten data service: the canonical, versioned SIA 2024 room-use
dataset with attribute-style (dot-syntax) access.

```python
from energytools.raumdaten import load_dataset
ds = load_dataset("V221", path="data/datasets")
ds.room_uses.group_office
ds.profile(ds.room_uses.group_office.nutzid).personnel_area.standard.value
```

::: energytools.raumdaten
