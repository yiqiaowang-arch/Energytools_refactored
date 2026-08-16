# API Reference — Raumdaten Data Service

**Module:** `energytools.raumdaten` · **Doc set 02 (API Reference)** · Back to [index](README.md) ·
Foundation: [02-common-foundation.md](02-common-foundation.md) · Engine:
[04-gebaeude-engine.md](04-gebaeude-engine.md)

The Raumdaten data service gives you read-only access to the **canonical, versioned SIA 2024
dataset** (the digital replacement of `2024_Raumdatenblätter_dfi_V221.xlsm`): 45 room uses,
193 data-sheet parameters, per-use profiles in three value kinds, 40 climate stations, and the
full-load-hours / Qhc / SIA 380-1 tables. Everything you do with the data — load a release,
query room uses, read a profile, compare two profiles, list climate stations — goes through two
entry points: [`load_dataset`](#functions) and [`RaumdatenService`](#classes).

> **Which parts do you need?** For a typical project you only need the **user-facing** symbols
> marked ✅: `load_dataset`, `Dataset`, `RaumdatenService`, `RoomUse`, `RoomUseProfile`, and the
> `compare_profiles` helper. The ⚙ symbols (`DatasetExtractor`, `DatasetStore`, schema) are for
> dataset *authoring* and advanced use — skip them.

---

## In this page

- [Quickstart](#quickstart) — load V221 and run the three most common queries
- [Classes](#classes) — `Dataset`, `RaumdatenService`, data classes
- [Functions](#functions) — `load_dataset`, `compare_profiles`
- [Internal / advanced](#internal-advanced) — extraction, store, schema
- [What to import for a new project](#what-to-import-for-a-new-project)

---

## Quickstart

### 1. Install

```bash
# pixi (recommended, contributors)
pixi install

# or plain pip (Python >= 3.11)
pip install -e .
```

The Raumdaten loader needs the `data` extra (`jsonschema` + `pandas`):

```bash
pixi run -e dev python -c "import jsonschema"   # dev env ships it
pip install "energytools[data]"
```

### 2. Load the V221 release

```python
from energytools.raumdaten import load_dataset

dataset = load_dataset("V221")          # reads ./data/datasets by default
print(dataset)
# Dataset(release_id='V221', room_uses=45, parameters=193, profiles=45, climate_stations=40)
```

`load_dataset` looks in the directory configured by the `ENERGYTOOLS_DATASET_DIR` environment
variable, falling back to `./data/datasets` relative to the current working directory. You can
point it anywhere explicitly:

```python
dataset = load_dataset("V221", path="/srv/energytools/data/datasets")
```

### 3. Query with `RaumdatenService`

`RaumdatenService` is the semantic, read-only query API. It takes the `release_id` explicitly on
every call — nothing is "implicitly loaded".

```python
from energytools.raumdaten import RaumdatenService

svc = RaumdatenService()

# Which room uses does the release define?
svc.list_room_uses("V221")
# [{'nutzid': 1, 'code': '1.01', 'category': 1, 'name': 'Wohnen MFH'},
#  {'nutzid': 2, 'code': '1.02', 'category': 1, 'name': 'Wohnen EFH'},
#  {'nutzid': 3, 'code': '2.01', 'category': 2, 'name': 'Hotelzimmer'}, ...]

# The full data sheet of one room use (SIA code or nutzid)
profile = svc.get_room_use_profile("V221", "1.01")
print(profile["room_use"]["name"]["de"])    # 'Wohnen MFH'
print(len(profile["parameters"]))           # 193

# Compare two room uses
diff = svc.compare_room_use_profiles("V221", "1.01", "1.02")
print(diff["identical"])                    # False
print(len(diff["changed"]))                 # 10
print(diff["changed"][0])
# {'parameter_id': '1.1.1.2', 'label': 'Thermische Gebäudehüllfläche', 'symbol': 'Ath',
#  'unit': 'm2', 'diffs': {'standard': [26.47058823529412, 38.23529411764706]}}
```

### 4. Working with the loaded `Dataset` directly

```python
ru = dataset.room_use("1.01")               # or dataset.room_use(1) by nutzid
print(ru.nutzid, ru.code, ru.category, ru.name.get("fr"))
# 1 1.01 1 Habitat collectif

profile = dataset.profile(1)                # RoomUseProfile for nutzid 1
pv = profile.value("1.1.1.2")               # ParameterValue, standard kind
print(pv.value, pv.unit.symbol)             # 26.47058823529412 m2
print(profile.value("Uop", "zielwert").value)   # 0.1  (value kind by name)

stations = dataset.climate().stations
print(len(stations), stations[0].name.de)   # 40 Adelboden
```

---

<a id="1-energytoolsraumdatenmodel"></a>
## Classes

<a id="116-dataset"></a>
<a id="dataset--user-facing"></a>
### `Dataset` ✅ (user-facing)

`@dataclass(frozen=True) class Dataset` — one **immutable dataset release**: every table of the
canonical package (room uses, parameters, profiles, climate, full-load hours, Qhc, SIA 380-1,
mappings, area tables). Built by [`load_dataset`](#load_dataset); this is the **only** way the
calculation engine consumes Raumdaten.

**Methods:**

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `room_use` | `(room_use_id: int \| str) -> RoomUse` | `RoomUse` | Look up by nutzid (1–45) or SIA code (`"1.01"`). |
| `room_uses` | `() -> tuple[RoomUse, ...]` | `tuple[RoomUse, ...]` | All 45 room uses in sheet order. |
| `parameter` | `(parameter_id: str) -> Parameter` | `Parameter` | One catalog parameter (clause id or slug). |
| `parameters` | `() -> tuple[Parameter, ...]` | `tuple[Parameter, ...]` | All 193 catalog parameters in sheet order. |
| `profile` | `(room_use_id: int, kind: ValueKind \| None = None) -> RoomUseProfile` | `RoomUseProfile` | Full profile of one room use (all value kinds). |
| `climate` | `() -> ClimateData` | `ClimateData` | The release climate data (40 stations). |
| `full_load_hours` | `() -> FullLoadHoursTable` | `FullLoadHoursTable` | Ventilation full-load-hours table. |
| `qhc` | `() -> QhcTable` | `QhcTable` | Annual cooling-energy table. |
| `sia3801_results` | `(variant: str \| None = None) -> tuple[Sia3801Result, ...]` | `tuple[Sia3801Result, ...]` | SIA 380-1 results, optionally filtered by variant. |
| `mappings` | `() -> tuple[BuildingCategoryMapping, ...]` | `tuple[BuildingCategoryMapping, ...]` | SIA 2024 ↔ SIA 380-1 category mappings. |
| `area_tables` | `() -> tuple[AreaTable, ...]` | `tuple[AreaTable, ...]` | Building-category area tables. |
| `sia3801_coefficients` | `() -> tuple[Sia3801Coefficients, ...]` | `tuple[Sia3801Coefficients, ...]` | Per-category SIA 380-1 coefficients. |
| `validate` | `() -> ValidationReport` | `ValidationReport` | Schema + domain-value validation (reports, never raises). |
| `to_package_dict` | `() -> dict` | `dict` | The canonical package as a JSON-ready dict. |
| `from_package_dict` | `(data: dict) -> Dataset` *(classmethod)* | `Dataset` | Build a `Dataset` from a package dict. |
| `release_id` | *(property)* | `str` | The release id, e.g. `"V221"`. |

```python
report = dataset.validate()
print(report.valid, len(report.warnings))   # True 107
```

**Raises:** `UnknownRoomUseError`, `UnknownParameterError`, `UnknownValueKindError` on bad
lookups; `ValueError` at construction on inconsistent content (see
[02-common-foundation.md](02-common-foundation.md) for the exception classes).

---

<a id="3-energytoolsraumdatenservice"></a>
<a id="31-raumdatenservice"></a>
<a id="32-methods"></a>
### `RaumdatenService` ✅ (user-facing)

`class RaumdatenService` — the **read-only semantic query API** over the canonical dataset.
One instance = one `DatasetStore` + one `VersionResolver`; all methods take `release_id`
explicitly and return JSON-ready dicts. This is the single dependency of the FastAPI datasets
router and the MCP data tools (parts [06](06-fastapi-layer.md) / [07](07-mcp-layer.md)).

**Methods:**

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `list_releases` | `() -> list[dict]` | `list[dict]` | Installed releases, newest first (id, edition, date, checksum, supersedes). |
| `get_release` | `(release_id: str) -> dict` | `dict` | Full release metadata incl. changelog (`"latest"` allowed). |
| `list_room_uses` | `(release_id, language=Language.DE) -> list[dict]` | `list[dict]` | Room uses as `{nutzid, code, category, name}` — dropdown/selector data. |
| `get_room_use` | `(release_id, room_use_id) -> dict` | `dict` | One room use, all languages. |
| `get_room_use_profile` | `(release_id, room_use_id, value_kind=None) -> dict` | `dict` | The full data sheet: all parameters per kind. |
| `list_parameters` | `(release_id, language=Language.DE) -> list[dict]` | `list[dict]` | The parameter catalog (ids, labels, symbols, units, flags). |
| `get_parameter` | `(release_id, parameter_id) -> dict` | `dict` | One parameter incl. value kinds and flags. |
| `compare_room_use_profiles` | `(release_id, a, b) -> dict` | `dict` | Diff two profiles (a, b as nutzid or SIA code). |
| `list_climate_stations` | `(release_id, language=Language.DE) -> list[dict]` | `list[dict]` | The 40 stations as `{id, name}`. |
| `get_climate_station` | `(release_id, station_id) -> dict` | `dict` | Full station data (design values, monthly, bins, HDD). |
| `list_profiles` | `(release_id) -> dict` | `dict` | `{"hourly": [...], "monthly": [...], "weekly": [...]}` profile sets. |
| `get_full_load_hours` | `(release_id, room_use_id, regulation, standard_version=None) -> dict` | `dict` | Full-load hours; `None` resolves the release default standard version. |
| `get_qhc` | `(release_id, room_use_id, station_id, value_kind=ValueKind.STANDARD) -> dict` | `dict` | Annual cooling energy Qhc for one use × station × kind. |
| `get_sia3801` | `(release_id, room_use_id, variant="de") -> dict` | `dict` | SIA 380-1 result (incl. `"de+qc"` cooling variant). |
| `validate` | `(release_id) -> dict` | `dict` | `{"release_id", "valid", "errors", "warnings"}` report. |
| `export` | `(release_id, fmt, scope, target) -> dict` | `dict` | Bulk export — **JSON only** for now; `csv/xlsx/pdf` raise `ExportError` (see [05](05-versioning-export.md)). |

```python
svc = RaumdatenService()
svc.list_climate_stations("V221")[:2]
# [{'id': 1, 'name': 'Adelboden'}, {'id': 2, 'name': 'Aigle'}]

svc.get_full_load_hours("V221", 1, "1-stufig")
# {'room_use_id': 1, 'regulation': '1-stufig', 'standard_version': 'prSIA 2024-C1:2024',
#  'default_standard_version': 'prSIA 2024-C1:2024', 'hours': 8760.0, 'unit': 'h/a', ...}

svc.get_qhc("V221", 1, 1)
# {'room_use_id': 1, 'station_id': 1, 'kind': 'standard',
#  'qhc': {'value': 0.0, 'unit': 'kWh/m2'}, ...}
```

**Raises:** `DatasetNotFoundError`, `UnknownRoomUseError`, `UnknownParameterError`,
`UnknownClimateStationError`, `UnknownLanguageError`, `UnknownValueKindError`,
`TableLookupError`, `ExportError` — all from `energytools.common.errors` (part
[02](02-common-foundation.md)).

---

### Data classes ✅ (user-facing, read-only)

These are immutable value objects you receive from `Dataset` / `RaumdatenService` — you rarely
construct them yourself.

<a id="11-roomuse"></a>
#### `RoomUse` ✅

`@dataclass(frozen=True) class RoomUse` — one of the **45 standard room uses**.

| Field | Type | Meaning |
|---|---|---|
| `nutzid` | `int` | Numeric id 1–45 (the workbook selector value). |
| `code` | `str` | SIA code, e.g. `"1.01"` (normalized, `"12.1"` → `"12.10"`). |
| `category` | `int` | Building category 1–12 (1 Wohnen … 12 Nebenräume). |
| `name` | `TrilingualText` | DE/FR/IT names. |
| `sia_clause` | `str \| None` | Optional SIA clause identifier. |

```python
ru = dataset.room_use("1.01")
ru.as_dict()   # {'nutzid': 1, 'code': '1.01', 'category': 1,
               #  'name': {'de': 'Wohnen MFH', 'fr': 'Habitat collectif', 'it': 'Abitazione plurifamiliare'}, ...}
```

<a id="12-parameter"></a>
#### `Parameter` ✅

`@dataclass(frozen=True) class Parameter` — one of the **193 data-sheet parameters**; the
stable id is the SIA clause number (e.g. `"1.1.2.7"` Jahresgleichzeitigkeit) or a documented
slug.

| Field | Type | Meaning |
|---|---|---|
| `id` | `str` | SIA clause id or slug (the stable key). |
| `label` | `TrilingualText` | Trilingual label. |
| `symbol` | `str` | Parameter symbol, e.g. `"fP"`. |
| `unit` | `Unit` | Unit of measure (part [02](02-common-foundation.md)). |
| `data_type` | `str` | `"number" \| "enum" \| "text" \| "bool"`. |
| `category` | `str` | Sheet section, e.g. `"Personen"`, `"Lüftung"`. |
| `value_kinds` | `frozenset[ValueKind]` | Applicable value kinds. |
| `export_flag` / `display_flag` / `internal_heat_flag` / `qhc_flag` | `bool` | Workbook export/display flags. |
| `provenance` | `Provenance \| None` | Source reference (part [02](02-common-foundation.md)). |

```python
p = dataset.parameter("1.1.2.7")
print(p.symbol, p.unit.symbol, p.category)      # fP - Personen
```

<a id="13-parametervalue"></a>
#### `ParameterValue` ✅

`@dataclass(frozen=True) class ParameterValue` — one value of one parameter in one value kind,
with unit and provenance. The `quantity` property returns a typed `Quantity`.

```python
pv = profile.value("Uop")                       # standard kind
print(pv.value, pv.unit.symbol)                 # 0.17 W/(m2xK)
print(pv.quantity)                              # Quantity(value=0.17, unit=Unit(...))
```

<a id="14-roomuseprofile"></a>
#### `RoomUseProfile` ✅

`@dataclass class RoomUseProfile` — the full parameter-value set of one room use for **all
value kinds**; the digital equivalent of the rendered data sheet.

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `value` | `(parameter_id, kind=ValueKind.STANDARD) -> ParameterValue` | `ParameterValue` | One value; a non-applicable kind yields `value=None` instead of raising. |
| `parameters` | `() -> list[Parameter]` | `list[Parameter]` | Catalog entries in sheet order. |
| `to_frame` | `(kind=ValueKind.STANDARD) -> pandas.DataFrame` | `DataFrame` | Rows = parameters for one kind (needs the `data` extra). |
| `as_dict` | `(kind=None) -> dict` | `dict` | JSON-ready; `kind=None` includes all kinds. |

```python
prof = dataset.profile(1)
prof.value("1.1.1.2").value                    # 26.47058823529412  (standard)
prof.value("Uop", "zielwert").value            # 0.1
df = prof.to_frame()                           # 193 rows x 5 columns
```

<a id="18-climatestation"></a>
#### `ClimateStation` ✅

`@dataclass(frozen=True) class ClimateStation` — one of the **40 climate stations**:
winter/summer design values (`Quantity` per key), monthly profiles, temperature bins and HDD.

```python
st = dataset.climate().station(1)
print(st.name.de, st.hdd)                      # Adelboden 4670.0 K·d
print(list(st.winter_design))                  # ['t_a', 't_heating', 't_ventilation', 'radiation']
```

<a id="15-hourlyprofile"></a>
<a id="16-monthlyprofile"></a>
<a id="17-weeklyprofile"></a>
<a id="19-climatedata"></a>
<a id="110-fullloadhourstable"></a>
<a id="111-buildingcategorymapping"></a>
<a id="112-areatable"></a>
<a id="113-sia3801coefficients"></a>
<a id="114-sia3801result"></a>
<a id="115-qhctable"></a>
#### Other model classes ✅ (field tables)

| Class | Purpose | Key fields |
|---|---|---|
| `ClimateData` | All stations of a release + version tag | `version`, `stations`, `station(id)`, `ids()`, `as_dict()` |
| `FullLoadHoursTable` | Ventilation full-load hours per use × regulation × standard version | `hours(room_use_id, regulation, standard_version=None)`, `standard_versions`, `regulations`, `default_standard_version` |
| `QhcTable` | Annual cooling energy per use × station × kind | `qhc(room_use_id, station_id, kind=STANDARD)`, `rows` |
| `Sia3801Result` | SIA 380-1 heating-demand result of one room use | `room_use_id`, `station_id`, `kind`, `variant`, `values` (`{"Qh": Quantity}`) |
| `Sia3801Coefficients` | Per-category SIA 380-1 coefficients | `variant` (`de/en/de+qc/en+qc`), `category`, `coefficients` |
| `BuildingCategoryMapping` | SIA 2024 ↔ SIA 380-1 category mapping | `sia3801_category`, `room_use_codes`, `name` |
| `AreaTable` | Building-category area table | `kind` (`ValueKind`), `rows` (category → code → `Quantity`) |
| `HourlyProfile` | One 24 h load profile | `id`, `profile_type` (person/device/lighting/ventilation), `values` (24), `unit` |
| `MonthlyProfile` | Twelve monthly values | `id`, `values` (12), `unit` |
| `WeeklyProfile` | Seven-day profile | `id`, `values` (7), `unit` |
| `TemperatureBin` | One bin of `Klimadaten` "Anzahl Stunden Tac" | `lower`, `upper`, `hours` |

```python
flh = dataset.full_load_hours()
print(sorted(flh.standard_versions))           # ['prSIA 2024-C1:2024']
print(flh.hours(1, "1-stufig"))                # 8760.0  (default standard version)
print(dataset.qhc().qhc(1, 1))                 # 0.0 kWh/m2
```

---

<a id="2-energytoolsraumdatendataset"></a>
## Functions

<a id="21-load_dataset"></a>
<a id="load_dataset"></a>
### `load_dataset` ✅ (user-facing)

`def load_dataset(release_id: str, path: str | None = None) -> Dataset`

Load a dataset release from disk (JSON package + JSON Schema) as a frozen `Dataset`. Results
are cached process-wide: subsequent calls with the same `release_id` and directory return the
identical object.

**Two usages:**

```python
# 1) release_id only — configured dataset dir (ENERGYTOOLS_DATASET_DIR or ./data/datasets)
dataset = load_dataset("V221")

# 2) explicit directory
dataset = load_dataset("V221", path="/srv/energytools/data/datasets")
```

**Raises:** `DatasetNotFoundError` (release not installed); `DatasetValidationError` (package
fails schema/checksum/content validation — a corrupt package is never half-loaded).

<a id="4-energytoolsraumdatencompare"></a>
<a id="41-compare_profiles"></a>
<a id="42-profilediff"></a>
### `compare_profiles` ✅ (user-facing)

`def compare_profiles(a: RoomUseProfile, b: RoomUseProfile) -> ProfileDiff`

Compare two room-use profiles **of the same release** across all value kinds. Returns a
`ProfileDiff` (fields `a_id`, `b_id`, `changed: tuple[ParameterDiff, ...]`, `added`, `removed`,
`identical`), JSON-ready via `as_dict()`.

```python
from energytools.raumdaten import compare_profiles

diff = compare_profiles(dataset.profile(1), dataset.profile(2))
print(diff.identical, len(diff.changed))       # False 10
print(diff.changed[0].as_dict())
# {'parameter_id': '1.1.1.2', 'label': 'Thermische Gebäudehüllfläche', 'symbol': 'Ath',
#  'unit': 'm2', 'diffs': {'standard': [26.47058823529412, 38.23529411764706]}}
```

**Raises:** `ValueError` when the profiles belong to different releases (checked via their
parameter catalogs). `ParameterDiff` carries `parameter_id`, `label`, `symbol`, `unit`,
`diffs` (kind → `(value_a, value_b)`).

---

## Internal / advanced

These symbols power dataset **authoring and infrastructure**. You do not need them to *use* the
data — they are documented for maintainers and advanced users.

<a id="22-datasetstore"></a>
### `DatasetStore` ⚙ (internal)

`class DatasetStore` — process-wide registry of loaded releases. Enforces "one frozen `Dataset`
per release id" and answers existence queries without touching disk.

| Method | Signature | Returns |
|---|---|---|
| `get` | `(release_id) -> Dataset` | Load-on-demand, cached. |
| `list` | `() -> list[DatasetRelease]` | Installed releases (from package manifests), newest first. |
| `register` | `(dataset) -> None` | Pre-register an in-memory dataset (tests, custom packages). |
| `refresh` | `() -> None` | Drop the cache and re-scan. |

<a id="23-datasetextractor"></a>
### `DatasetExtractor` ⚙ (internal — extraction/authoring use)

`class DatasetExtractor` — the stage-0 pipeline that reads a **copy** of the source workbook
`2024_Raumdatenblätter_dfi_V221.xlsm` deterministically (values + formulas + cached results),
checksums it, validates the result against the package JSON Schema and writes the canonical
JSON package + manifest.

```python
from energytools.raumdaten import DatasetExtractor

extractor = DatasetExtractor(
    workbook_path="data/raw/2024_Raumdatenblätter_dfi_V221.xlsm",
    output_dir="data/datasets",
    release_id="V221",
    extraction_tool_version="0.1.0",
)
release = extractor.extract()      # DatasetRelease of the written package
```

**Raises:** `FileNotFoundError` (constructor, workbook copy missing); `DatasetValidationError`
(unexpected sheet layout, missing tables, unknown value kinds).

### Package schema ⚙ (internal)

`energytools.raumdaten.schema` exports `PACKAGE_SCHEMA` (JSON Schema draft 2020-12, the single
source of truth for the `package.json` format) and `SCHEMA_VERSION = "1.0"`. The loader
validates against it; the extractor writes a copy next to every package it produces.

<a id="computepackagechecksum--internal--moved-to-the-deprecated-energytoolsdataset"></a>
### `compute_package_checksum` ⚙ (internal — moved to the deprecated `energytools.dataset`)

`def compute_package_checksum(package: Mapping[str, Any]) -> str`

The SHA-256 of the canonical package content **with the declared `release.checksum_sha256`
field excluded** (self-referential exclusion, the same trick git uses), so a package can
truthfully declare its own checksum.

> **Note:** this helper currently lives in the **deprecated** `energytools.dataset` package
> (`from energytools.dataset import compute_package_checksum`), not in
> `energytools.raumdaten`. It is on the roadmap to move into `energytools.raumdaten.dataset`
> alongside the canonical loader. See the *doc–code deviations* list in the index
> [README.md](README.md#doccode-deviation-list).

---

## What to import for a new project

```python
# Data access — everything a typical project needs
from energytools.raumdaten import (
    load_dataset,          # Dataset  <- load a release
    RaumdatenService,      # read-only query API (list/get/compare/validate/export)
    compare_profiles,      # pure profile diff (advanced)
    RoomUse,               # value objects you receive from the API
    RoomUseProfile,
    ClimateStation,
)

# Value kinds and languages for arguments (de/fr/it, standard/zielwert/bestand)
from energytools.common.valuekind import ValueKind
from energytools.common.language import Language

# Errors to catch
from energytools.common.errors import (
    EnergyToolsError,          # catch-all
    DatasetNotFoundError,      # unknown release
    UnknownRoomUseError,       # unknown nutzid / SIA code
    UnknownValueKindError,     # bad value kind
)
```

Typical flow: `load_dataset("V221")` → `RaumdatenService()` → `list_room_uses` /
`get_room_use_profile` / `compare_room_use_profiles` → pass the loaded `Dataset` to the
calculation engine (part [04](04-gebaeude-engine.md)).
