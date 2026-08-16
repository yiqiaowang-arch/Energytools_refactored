# API Reference — Common Foundation

**Module:** `energytools.common` · **Doc set 02 (API Reference)** · Back to [index](README.md) ·
Data service: [03-raumdaten-service.md](03-raumdaten-service.md) · Engine:
[04-gebaeude-engine.md](04-gebaeude-engine.md)

The cross-cutting foundation shared by every layer of the library: the **exception hierarchy**
(what to catch), **versioning** (what release am I on), **units and quantities** (typed
values), **languages** (DE/FR/IT labels), **value kinds** (standard / zielwert / bestand),
**provenance** (where a value came from) and **validation reports**. You will use most of this
implicitly — the value objects come back from the data service and the engine — but the
versioning, units, language and exception pieces are worth importing directly.

> **Which parts do you need?** For a typical project: `VersionInfo`, `ValueKind`, `Language`,
> `Quantity`, and the exceptions. The ⚙ symbols (`SourceRef`, `Provenance`, `register_unit`)
> are for advanced/audit use.

---

## In this page

- [Quickstart](#quickstart) — versions, quantities, languages, value kinds
- [Exceptions](#exceptions) — the hierarchy and when to catch what
- [Classes](#classes) — `VersionInfo`, `VersionResolver`, `TrilingualText`, `Quantity`, `Unit`, `ValueKind`, `Language`, `ValidationReport`
- [What to import for a new project](#what-to-import-for-a-new-project)

---

## Quickstart

### Versions

```python
from energytools import get_version

info = get_version()            # structured version quadruple of the installation
print(info.as_dict())
# {'dataset': '', 'model': '', 'implementation': '0.1.0', 'climate': ''}
```

`get_version()` reads the newest installed dataset/model release per axis. In a source
checkout with the canonical package layout the dataset/model axes are currently empty — see
the layout note below. With release manifests installed they resolve to the concrete ids
(e.g. `dataset: 'V221'`, `model: '1.0.0'`, `climate: 'meteoschweiz-2024'`).

> **Layout note (source checkout).** `get_version()` and `VersionResolver.from_installed`
> read **flat `*.json` release manifests** from `data/datasets/` and `data/models/`. The
> canonical dataset package shipped with this repository lives in the subdirectory
> `data/datasets/V221/package.json`, so in this checkout `get_version()` reports empty
> dataset/model axes. The `RaumdatenService` (part [03](03-raumdaten-service.md)) scans
> `*/package.json` and resolves the same releases correctly — prefer it for data access.

Resolve ids and aliases explicitly with `VersionResolver`:

```python
from energytools.common.versioning import VersionResolver, DatasetRelease, ModelRelease
from datetime import date

resolver = VersionResolver(
    datasets={
        "V221": DatasetRelease(id="V221", edition="SIA 2024",
                               publication_date=date(2024, 11, 17),
                               checksum_sha256="0" * 64,
                               source_workbook="…V221.xlsm",
                               extraction_tool_version="0.1.0"),
    },
    models={
        "1.0.0": ModelRelease(id="1.0.0",
                              compatible_dataset_releases=frozenset({"V221"}),
                              compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
                              publication_date=date(2025, 4, 20)),
    },
    implementation_version="0.1.0",
)
release = resolver.resolve_dataset("V221")     # or "latest"
print(release.id, release.edition)             # V221 SIA 2024
```

### Typed values with units

```python
from energytools.common.units import Quantity, Unit

q = Quantity(3600.0, "kWh")
print(q.to("MWh"))                  # 3.6 MWh  (Quantity(value=3.6, unit=MWh))
print(q.to("MWh").format(2))        # '3.60 MWh'
print(q.as_dict())                  # {'value': 3600.0, 'unit': 'kWh'}

Unit("W/m2").convert_to(1000.0, Unit("kW/m2"))   # 1.0
Quantity(1.0, "kWh").to("m2")       # → UnitError (different dimensions)
```

### Trilingual labels

```python
from energytools.common.language import Language, TrilingualText

name = TrilingualText(de="Wohnen MFH", fr="Habitat collectif", it="Abitazione plurifamiliare")
print(name.get(Language.FR))        # 'Habitat collectif'
print(name.get("it"))               # 'Abitazione plurifamiliare'
print(name.get("de"))               # 'Wohnen MFH'  (fallback for empty fields)
```

### Value kinds

```python
from energytools.common.valuekind import ValueKind

print(ValueKind.parse("zielwert"))      # ValueKind.ZIELWERT
print(ValueKind.parse("target"))        # ValueKind.ZIELWERT  (English alias)
print(ValueKind.parse("optimal"))       # → UnknownValueKindError
```

### Catching errors

```python
from energytools.common.errors import EnergyToolsError, DatasetNotFoundError

try:
    svc.get_release("V199")             # unknown release
except DatasetNotFoundError as e:
    print(e)                            # Dataset release 'V199' not found
    print(e.details)                    # structured context (or None)
except EnergyToolsError as e:           # catch-all for library errors
    ...
```

---

<a id="1-energytoolscommonerrors"></a>
<a id="11-energytoolserror"></a>
<a id="12-datasetnotfounderror"></a>
<a id="13-datasetvalidationerror"></a>
<a id="14-unknownroomuseerror"></a>
<a id="15-unknownparametererror"></a>
<a id="16-unknownclimatestationerror"></a>
<a id="17-unknownlanguageerror"></a>
<a id="18-unknownvaluekinderror"></a>
<a id="19-calculationinputerror"></a>
<a id="110-calculationerror"></a>
<a id="111-modelversionmismatcherror"></a>
<a id="112-backenderror"></a>
<a id="113-excelbackenderror"></a>
<a id="114-exporterror"></a>
<a id="115-uniterror"></a>
<a id="116-psychrometricerror"></a>
## Exceptions

All exceptions derive from `EnergyToolsError(Exception)` and carry an optional structured
`details: dict | None` payload (`str(e)` is the human-readable message, `e.details` the
structured context). The hierarchy is **flat by design**: each subclass is raised in exactly
one layer, so you can catch either the precise type or the base type.

| Exception | Raised when | Raised by | Typical handling |
|---|---|---|---|
| `EnergyToolsError` | *(base)* | everything | Catch-all for library errors. |
| `DatasetNotFoundError` | A dataset release is unknown/uninstalled | `DatasetStore.get`, `RaumdatenService`, resolver | Show "release not found". |
| `DatasetValidationError` | A package/input fails schema or value rules | loader, `Dataset.validate` consumers | Report validation errors. |
| `UnknownRoomUseError` | Room-use id not in the release | `Dataset.room_use`, service methods | Show "unknown room use". |
| `UnknownParameterError` | Parameter id not in the catalog | `Dataset.parameter`, service methods | Show "unknown parameter". |
| `UnknownClimateStationError` | Station id (1–40) not in the release | `ClimateData.station`, service methods | Show "unknown station". |
| `UnknownLanguageError` | Language not de/fr/it | `Language.parse`, `TrilingualText.get`, service methods | Show "unknown language". |
| `UnknownValueKindError` | Value kind not standard/zielwert/bestand | `ValueKind.parse`, service methods | Show "unknown value kind". |
| `CalculationInputError` | Building input structurally/semantically invalid | `Engine.calculate` (hard validation errors) | Report validation errors. |
| `CalculationError` | Calculation fails at runtime after validation | `Engine.calculate`, `Engine.explain`/`get_result` | Show "calculation failed". |
| `ModelVersionMismatchError` | Dataset/model/climate versions incompatible | `Engine.calculate` | Suggest a compatible release. |
| `BackendError` | Backend cannot produce a result | backends | Show "backend unavailable". |
| `ExcelBackendError` | Excel-COM-specific failure | Excel backend only | Show "Excel unavailable". |
| `ExportError` | Export fails (format, target, data) | `RaumdatenService.export`, export layer | Show "export failed". |
| `UnitError` | Invalid unit, unknown symbol, impossible conversion | `Unit`, `Quantity.to` | Show unit error. |
| `PsychrometricError` | Out-of-domain psychrometric input | `engine.native.psychrometrics` | Show "invalid input". |
| `TableLookupError` | Workbook-derived table lookup misses a key | `FullLoadHoursTable.hours`, `QhcTable.qhc` | Show "value not found in table". |

```python
try:
    dataset = load_dataset("V221")
except DatasetNotFoundError:
    print("install the release first")
except DatasetValidationError as e:
    print("corrupt package:", e.details.get("errors"))
```

---

## Classes

<a id="2-energytoolscommonversioning"></a>
<a id="23-versioninfo"></a>
### `VersionInfo` ✅ (user-facing)

`@dataclass(frozen=True) class VersionInfo` — the version quadruple every calculation result
and every `/versions` response carries: `dataset`, `model`, `implementation`, `climate`.
`as_dict()` returns the four axes as a plain dict.

```python
from energytools.common.versioning import VersionInfo
v = VersionInfo(dataset="V221", model="1.0.0", implementation="0.1.0", climate="meteoschweiz-2024")
print(v.as_dict())
# {'dataset': 'V221', 'model': '1.0.0', 'implementation': '0.1.0', 'climate': 'meteoschweiz-2024'}
```

<a id="25-versionresolver"></a>
### `VersionResolver` ✅ (user-facing)

`class VersionResolver` — the central place for "what is installed" and "what is current".
Maps user-facing ids and the `"latest"` alias to concrete releases; **never resolves
silently inside a calculation** — the concrete ids are recorded in `VersionInfo`.

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `from_installed` | `(dataset_dir, model_dir, implementation_version=None) -> VersionResolver` *(classmethod)* | `VersionResolver` | Build from release manifest files on disk. |
| `resolve_dataset` | `(release_id: str) -> DatasetRelease` | `DatasetRelease` | Resolve an id or `"latest"` (newest publication date). |
| `resolve_model` | `(model_id: str) -> ModelRelease` | `ModelRelease` | Same for models. |
| `list_datasets` | `() -> list[DatasetRelease]` | `list[DatasetRelease]` | Installed datasets, newest first. |
| `list_models` | `() -> list[ModelRelease]` | `list[ModelRelease]` | Installed models, newest first. |
| `current` | `() -> VersionInfo` | `VersionInfo` | Quadruple of the newest dataset/model/climate + implementation version. |

**Raises:** `DatasetNotFoundError` for unknown ids (also reused for unknown models).

```python
resolver = VersionResolver(
    datasets={"V221": rel_v221},
    models={"1.0.0": model_100},
    implementation_version="0.1.0",
)
print(resolver.current())                 # VersionInfo(dataset='V221', model='1.0.0', ...)
print(resolver.resolve_dataset("latest").id)
```

<a id="21-datasetrelease"></a>
<a id="22-modelrelease"></a>
<a id="24-changelogentry"></a>
### `DatasetRelease` / `ModelRelease` ✅ (user-facing)

Immutable release metadata value objects (fields are also constructor arguments).

| Class | Key fields |
|---|---|
| `DatasetRelease` | `id` (`"V221"`), `edition` (`"SIA 2024"`), `publication_date: date`, `checksum_sha256`, `source_workbook`, `extraction_tool_version`, `changelog`, `supersedes` |
| `ModelRelease` | `id` (semver, `"1.0.0"`), `compatible_dataset_releases: frozenset[str]`, `compatible_climate_versions: frozenset[str]`, `publication_date`, `changelog` |
| `ChangelogEntry` | `version`, `date`, `change`, `migration: str \| None` |

```python
from datetime import date
from energytools.common.versioning import DatasetRelease, ModelRelease

rel = DatasetRelease(id="V221", edition="SIA 2024", publication_date=date(2024, 11, 17),
                     checksum_sha256="0" * 64, source_workbook="…V221.xlsm",
                     extraction_tool_version="0.1.0")
model = ModelRelease(id="1.0.0",
                     compatible_dataset_releases=frozenset({"V221"}),
                     compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
                     publication_date=date(2025, 4, 20))
```

**Raises:** `ValueError` on an empty dataset id, a non-semver model id, or empty
compatibility sets.

<a id="3-energytoolscommonunits"></a>
<a id="32-quantity"></a>
### `Quantity` ✅ (user-facing)

`@dataclass(frozen=True) class Quantity` — a typed value paired with a unit. Used across the
domain model for parameter values, results and profile values; serialized as
`{"value": …, "unit": …}`.

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `to` | `(unit: Unit \| str) -> Quantity` | `Quantity` | A converted copy. |
| `format` | `(precision: int = 2) -> str` | `str` | `"12.34 W/m2"` (missing values render `"-"`). |
| `as_dict` | `() -> dict` | `dict` | `{"value": …, "unit": "…"}`. |

**Raises:** `UnitError` on conversion across dimensions or an unknown unit symbol.

```python
q = Quantity(45.0, "kWh/m2")
q.to("MWh/m2").format(2)          # '0.05 MWh/m2'
q.as_dict()                       # {'value': 45.0, 'unit': 'kWh/m2'}
```

<a id="31-unit"></a>
### `Unit` ✅ (user-facing)

`@dataclass(frozen=True) class Unit` — a unit of measure with a display symbol (normalized,
e.g. `W/m²` → `W/m2`), an SI hint and conversion metadata. Conversion is only defined within
the same physical dimension.

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `convert_to` | `(value: float, target: Unit) -> float` | `float` | Convert a numeric value to the target unit. |

```python
Unit("W/m2").convert_to(1000.0, Unit("kW/m2"))   # 1.0
Unit("kWh").convert_to(3600.0, Unit("Wh"))       # 3600.0
Unit("not-a-unit")                               # → UnitError
```

`register_unit(symbol, dimension, factor=1.0, offset=0.0, si_hint=None)` ⚙ registers a custom
unit symbol (e.g. for a private dataset package) — advanced use.

<a id="4-energytoolscommonlanguage"></a>
<a id="42-trilingualtext"></a>
### `TrilingualText` ✅ (user-facing)

`@dataclass(frozen=True) class TrilingualText` — a DE/FR/IT label triple (names, parameter
labels, sheet titles).

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `get` | `(language: Language \| str) -> str` | `str` | Label in the requested language; falls back to German for empty fields. |
| `as_dict` | `() -> dict` | `dict` | `{"de": …, "fr": …, "it": …}`. |

```python
name.get(Language.IT)             # 'Abitazione plurifamiliare'
name.get("fr")                    # 'Habitat collectif'
name.get("en")                    # → UnknownLanguageError
```

<a id="41-language"></a>
### `Language` ✅ (user-facing)

`class Language(enum.Enum)` — members `DE = "de"`, `FR = "fr"`, `IT = "it"`.
`parse(value)` accepts the codes (case-insensitive) and the workbook indices `"1"/"2"/"3"`;
raises `UnknownLanguageError` otherwise.

<a id="5-energytoolscommonvaluekind"></a>
<a id="51-valuekind"></a>
### `ValueKind` ✅ (user-facing)

`class ValueKind(enum.Enum)` — members `STANDARD = "standard"`, `ZIELWERT = "zielwert"`,
`BESTAND = "bestand"` (the workbook's M/N/O columns). `parse(value)` is case-insensitive and
accepts the English aliases `"target"` / `"existing"`; raises `UnknownValueKindError`.

### `ValidationReport` ✅ (user-facing)

`@dataclass(frozen=True) class ValidationReport` — structured validation outcome: hard
`errors` (a non-empty list means `valid is False`) and `warnings` (suspicious but acceptable).
`as_dict()` → `{"valid", "errors", "warnings"}`. Returned by `Dataset.validate`,
`BuildingInput.validate`, `Engine.validate_input`.

<a id="6-energytoolscommonprovenance"></a>
<a id="61-sourceref"></a>
<a id="62-provenance"></a>
### `SourceRef` / `Provenance` ⚙ (internal/advanced)

Provenance keeps traceability without exposing cell addresses through the API.

| Class | Purpose |
|---|---|
| `SourceRef` | One grounded source reference: `workbook`, `sheet`, `range`, `formula`, `cached_value`, `extraction_hash`. Requires at least `range` or `formula`. |
| `Provenance` | Collection of `SourceRef`s plus a free-text `note` for one value or derived result. |

```python
from energytools.common.provenance import Provenance, SourceRef

provenance = Provenance(
    sources=(SourceRef(workbook="2024_Raumdatenblätter_dfi_V221.xlsm",
                       sheet="Datenblatt", range="A56:S56"),),
    note="Parameter values of the Datenblatt sheet",
)
```

These ride along on `ParameterValue`, `Parameter`, `ClimateStation` and calculation
intermediates — you mostly *read* them, e.g. `parameter.provenance.as_dict()`.

---

## What to import for a new project

```python
# Versions
from energytools import get_version                                   # VersionInfo
from energytools.common.versioning import VersionResolver, VersionInfo

# Typed values
from energytools.common.units import Quantity, Unit

# Languages and value kinds for API arguments
from energytools.common.language import Language, TrilingualText
from energytools.common.valuekind import ValueKind

# Errors to catch
from energytools.common.errors import (
    EnergyToolsError,            # catch-all
    DatasetNotFoundError,        # unknown release
    UnknownRoomUseError,         # unknown room use
    UnknownValueKindError,       # bad value kind
    UnitError,                   # bad unit/conversion
    ExportError,                 # export failures
)

# Validation outcome
from energytools.common.validation import ValidationReport
```

Typical flow: `get_version()` for the installation state → service/engine methods that accept
`ValueKind` / `Language` arguments → read the returned `Quantity` / `TrilingualText` values.
