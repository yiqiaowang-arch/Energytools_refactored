# Part 02 — API Reference: `energytools.common` (Foundation)

**Document set 02** · Target-state design specification · Back to [index](README.md) ·
Inventory: [01-package-inventory.md](01-package-inventory.md)

Cross-cutting foundation shared by every layer: the exception hierarchy (§1), versioning
primitives (§2), units (§3), languages (§4), value kinds (§5) and provenance (§6).

---

## 1. `energytools.common.errors`

All exceptions derive from `EnergyToolsError`. The hierarchy is flat by design: every subclass is
raised in exactly one layer, so callers can catch either the precise type or the base type.

### 1.1 `EnergyToolsError`

`class EnergyToolsError(Exception)`

- **Purpose:** Base class of the whole library exception hierarchy. Carries an optional
  `details: dict | None` payload for structured error reporting (used by the FastAPI and MCP
  layers to build error responses without string parsing).
- **Inputs:** `message: str` (human-readable, English), `details: dict | None = None`
  (structured context, e.g. offending value, symbol id, release id).
- **Outputs:** Standard exception; `str(e)` = message; `e.details` = details dict.
- **Raises:** — (raised by subclasses).
- **Example:**
  ```python
  from energytools.common.errors import EnergyToolsError
  try:
      ...
  except EnergyToolsError as e:
      print(e.details)          # structured context
  ```

### 1.2 `DatasetNotFoundError`

`class DatasetNotFoundError(EnergyToolsError)`

- **Purpose:** Raised when a requested dataset release does not exist in the store (unknown
  `release_id`, uninstalled release).
- **Inputs:** `release_id: str` (as passed by the caller), `details=None`.
- **Outputs:** Exception with message `"Dataset release '<id>' not found"`.
- **Raises:** — (raised by `DatasetStore.get`, `RaumdatenService` methods, dataset endpoints).
- **Example:**
  ```python
  from energytools.common.errors import DatasetNotFoundError
  service.get_release("V222")   # → DatasetNotFoundError: Dataset release 'V222' not found
  ```

### 1.3 `DatasetValidationError`

`class DatasetValidationError(EnergyToolsError)`

- **Purpose:** Raised when a dataset or an input payload fails schema or domain-value validation
  (JSON Schema validation of the package, value rules such as `12.1` vs `12.10` code sanity,
  percentage ranges, missing required columns).
- **Inputs:** `message: str`, `details: dict | None = None` (recommended: `{"errors": [...]}`
  list of validation messages, optionally per path).
- **Outputs:** Exception; `e.details["errors"]` carries the per-item messages.
- **Raises:** — (raised by `DatasetExtractor`, `Dataset.validate`, `service.validate`,
  `POST /datasets/{release}/validate`).
- **Example:**
  ```python
  report = service.validate("V221")      # → ValidationReport with errors
  if report.has_errors:
      raise DatasetValidationError("release V221 invalid", {"errors": report.errors})
  ```

### 1.4 `UnknownRoomUseError`

`class UnknownRoomUseError(EnergyToolsError)`

- **Purpose:** Raised when a room-use identifier (numeric `nutzid` 1–45 or SIA code like
  `"1.01"`) does not exist in the release.
- **Inputs:** `room_use_id: str | int`, `release_id: str`, `details=None`.
- **Outputs:** Exception with message `"Room use '<id>' not found in release '<release>'"`.
- **Raises:** — (raised by `Dataset.room_use`, `RaumdatenService.get_room_use`,
  `get_room_use_profile`).
- **Example:**
  ```python
  service.get_room_use("V221", 99)   # → UnknownRoomUseError
  ```

### 1.5 `UnknownParameterError`

`class UnknownParameterError(EnergyToolsError)`

- **Purpose:** Raised when a parameter id (SIA clause id, e.g. `"1.1.2.7"`, or documented slug)
  is not part of the parameter catalog.
- **Inputs:** `parameter_id: str`, `release_id: str`, `details=None`.
- **Outputs:** Exception with message `"Parameter '<id>' not found in release '<release>'"`.
- **Raises:** — (raised by `Dataset.parameter`, `RaumdatenService.get_parameter`).
- **Example:**
  ```python
  service.get_parameter("V221", "9.9.9")   # → UnknownParameterError
  ```

### 1.6 `UnknownClimateStationError`

`class UnknownClimateStationError(EnergyToolsError)`

- **Purpose:** Raised when a climate-station id (1–40) is not present in the release.
- **Inputs:** `station_id: int | str`, `release_id: str`, `details=None`.
- **Outputs:** Exception with message `"Climate station '<id>' not found in release '<release>'"`.
- **Raises:** — (raised by `ClimateData.station`, `RaumdatenService.get_climate_station`).
- **Example:**
  ```python
  service.get_climate_station("V221", 41)   # → UnknownClimateStationError (only 40 stations)
  ```

### 1.7 `UnknownLanguageError`

`class UnknownLanguageError(EnergyToolsError)`

- **Purpose:** Raised when a language other than `de`, `fr`, `it` is requested.
- **Inputs:** `language: str`, `details=None`.
- **Outputs:** Exception with message `"Unknown language '<lang>' (expected de, fr or it)"`.
- **Raises:** — (raised by `TrilingualText.get`, service/API methods with a `language` argument).
- **Example:**
  ```python
  text.get("en")   # → UnknownLanguageError
  ```

### 1.8 `UnknownValueKindError`

`class UnknownValueKindError(EnergyToolsError)`

- **Purpose:** Raised when a value kind other than `standard`, `zielwert`, `bestand` is requested.
- **Inputs:** `value_kind: str`, `details=None`.
- **Outputs:** Exception with message `"Unknown value kind '<kind>' (expected standard, zielwert or bestand)"`.
- **Raises:** — (raised by `ValueKind.parse`, service/API methods with a `value_kind` argument).
- **Example:**
  ```python
  service.get_room_use_profile("V221", 5, value_kind="optimal")   # → UnknownValueKindError
  ```

### 1.9 `CalculationInputError`

`class CalculationInputError(EnergyToolsError)`

- **Purpose:** Raised when a building input (`BuildingProject`) is structurally or semantically
  invalid (unknown room use, negative area, system referencing a nonexistent catalog code,
  missing climate station, version mismatch between requested dataset and model).
- **Inputs:** `message: str`, `details: dict | None = None` (recommended `{"errors": [...]}`).
- **Outputs:** Exception; details carry the validation messages.
- **Raises:** — (raised by `BuildingProject.validate` consumers, `CalculationEngine.validate_input`
  for hard errors, `POST /calculations/validate`).
- **Example:**
  ```python
  engine.validate_input(project, dataset, model)   # → ValidationReport
  # hard failures are raised instead:
  engine.calculate(project, dataset=wrong_release, ...)  # → ModelVersionMismatchError (see 1.11)
  ```

### 1.10 `CalculationError`

`class CalculationError(EnergyToolsError)`

- **Purpose:** Raised when a calculation fails at runtime after validation (backend failure not
  attributable to Excel, numeric failure, missing intermediate, internal inconsistency).
- **Inputs:** `message: str`, `details: dict | None = None`.
- **Outputs:** Exception; details may carry `{"step": ..., "system": ...}` context.
- **Raises:** — (raised by `CalculationEngine.calculate` and backends).
- **Example:**
  ```python
  except CalculationError as e:
      print(e.details.get("step"))   # e.g. "ahu:LA03"
  ```

### 1.11 `ModelVersionMismatchError`

`class ModelVersionMismatchError(EnergyToolsError)`

- **Purpose:** Raised when the versions a calculation combines are incompatible: dataset release
  not supported by the model release, climate version newer/older than the model expects, or a
  native backend version that cannot reproduce the model release.
- **Inputs:** `message: str`, `details: dict | None = None`
  (recommended `{"dataset": ..., "model": ..., "climate": ...}`).
- **Outputs:** Exception; details carry the conflicting versions.
- **Raises:** — (raised by `CalculationEngine.calculate`, `ExcelBackend`/`NativeBackend`).
- **Example:**
  ```python
  engine.calculate(project, dataset_2024, model_release="1.0.0")
  # model 1.0.0 declares compatibility with dataset V221 only → ModelVersionMismatchError
  ```

### 1.12 `BackendError`

`class BackendError(EnergyToolsError)`

- **Purpose:** Base class for calculation-backend failures; raised directly when a backend cannot
  produce a result for reasons other than Excel COM (e.g. workbook copy missing, recalculation
  timed out, native backend raised an unclassified runtime error).
- **Inputs:** `message: str`, `details: dict | None = None`.
- **Outputs:** Exception; details may carry `{"backend": ..., "workbook": ...}`.
- **Raises:** — (raised by backends).
- **Example:**
  ```python
  except BackendError as e:
      logger.error("backend %s failed: %s", e.details.get("backend"), e)
  ```

### 1.13 `ExcelBackendError`

`class ExcelBackendError(BackendError)`

- **Purpose:** Excel-COM-specific backend failure: Excel not installed, COM automation denied,
  workbook copy protection unexpected, recalculation non-deterministic, cached-value mismatch.
- **Inputs:** `message: str`, `details: dict | None = None`.
- **Outputs:** Exception; details may carry `{"workbook": path, "cell": address}`.
- **Raises:** — (raised by `ExcelBackend` only).
- **Example:**
  ```python
  backend = ExcelBackend(path)
  try:
      backend.calculate(project, dataset, model)
  except ExcelBackendError as e:
      print("Excel runtime unavailable:", e)
  ```

### 1.14 `ExportError`

`class ExportError(EnergyToolsError)`

- **Purpose:** Raised when an export fails: unsupported format, unwritable target, missing data
  for the requested scope, PDF rendering failure.
- **Inputs:** `message: str`, `details: dict | None = None`.
- **Outputs:** Exception; details may carry `{"format": ..., "target": ...}`.
- **Raises:** — (raised by all exporters and `export_dataset`/`export_calculation`).
- **Example:**
  ```python
  export_dataset(service, "V221", fmt="docx", target=out)   # → ExportError (unsupported format)
  ```

### 1.15 `UnitError`

`class UnitError(EnergyToolsError)`

- **Purpose:** Raised for invalid units, unknown unit symbols, or impossible conversions
  (e.g. converting `kWh` to `m²`).
- **Inputs:** `message: str`, `details: dict | None = None`.
- **Outputs:** Exception; details may carry `{"from": ..., "to": ...}`.
- **Raises:** — (raised by `Unit`, `Quantity.to`).
- **Example:**
  ```python
  Quantity(1.0, Unit("kWh")).to(Unit("m2"))   # → UnitError
  ```

### 1.16 `PsychrometricError`

`class PsychrometricError(EnergyToolsError)`

- **Purpose:** Raised by psychrometric functions on out-of-domain inputs (e.g. relative humidity
  outside 0–100 %, negative absolute humidity, pressure ≤ 0), where the VBA code returned the
  string `"Fehler"`.
- **Inputs:** `message: str`, `details: dict | None = None` (recommended `{"function": ..., "args": {...}}`).
- **Outputs:** Exception; details identify the failing function and arguments.
- **Raises:** — (raised by `gebaeude.physics` functions, see part 04 §2).
- **Example:**
  ```python
  absolute_humidity(20.0, 150.0, 1013.0)   # → PsychrometricError (rh > 100)
  ```

---

## 2. `energytools.common.versioning`

Versioning is the backbone of the library (assessment §5.1: "released like software"). Every
result, export and API response references concrete releases; nothing resolves "latest"
silently at calculation time.

### 2.1 `DatasetRelease`

`@dataclass(frozen=True) class DatasetRelease`

- **Purpose:** Immutable metadata of one Raumdaten dataset package. Identifies a release by its
  human id (`"V221"` — the workbook version convention), the SIA edition it implements, the
  publication date, content checksum and extraction fingerprint.
- **Inputs (constructor):** `id: str` (e.g. `"V221"`), `edition: str` (e.g. `"SIA 2024"`),
  `publication_date: date`, `checksum_sha256: str` (of the package file), `source_workbook: str`
  (e.g. `"2024_Raumdatenblätter_dfi_V221.xlsm"`), `extraction_tool_version: str`,
  `changelog: tuple[ChangelogEntry, ...] = ()`, `supersedes: str | None = None`.
- **Attributes:** all constructor fields; `is_latest` is computed by the resolver, not stored.
- **Outputs:** — (value object; equality/ordering on `id`).
- **Raises:** `ValueError` on empty `id`.
- **Example:**
  ```python
  from energytools.common.versioning import DatasetRelease
  rel = DatasetRelease(id="V221", edition="SIA 2024", publication_date=date(2024, 11, 17),
                       checksum_sha256="ab12…", source_workbook="2024_Raumdatenblätter_dfi_V221.xlsm",
                       extraction_tool_version="0.1.0")
  ```

### 2.2 `ModelRelease`

`@dataclass(frozen=True) class ModelRelease`

- **Purpose:** Immutable metadata of the declarative Gebäude model definition (assessment §5.2):
  version, the dataset releases it is compatible with, the climate data versions it accepts, and
  a changelog.
- **Inputs (constructor):** `id: str` (semantic, e.g. `"1.0.0"`), `compatible_dataset_releases:
  frozenset[str]` (e.g. `{"V221"}`), `compatible_climate_versions: frozenset[str]`,
  `publication_date: date`, `changelog: tuple[ChangelogEntry, ...] = ()`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` on malformed semantic version or empty compatibility sets.
- **Example:**
  ```python
  ModelRelease(id="1.0.0", compatible_dataset_releases=frozenset({"V221"}),
               compatible_climate_versions=frozenset({"meteoschweiz-2024"}),
               publication_date=date(2025, 4, 20))
  ```

### 2.3 `VersionInfo`

`@dataclass(frozen=True) class VersionInfo`

- **Purpose:** The version quadruple every calculation result and every `/versions` response
  carries: dataset release, model release, implementation (library) version and climate data
  version. This makes results reproducible and comparable (assessment §6.2).
- **Inputs (constructor):** `dataset: str`, `model: str`, `implementation: str` (PEP 440),
  `climate: str`.
- **Attributes:** all four fields; `as_dict()` returns `{"dataset": …, "model": …,
  "implementation": …, "climate": …}`.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:**
  ```python
  VersionInfo(dataset="V221", model="1.0.0", implementation="0.1.0", climate="meteoschweiz-2024")
  ```

### 2.4 `ChangelogEntry`

`@dataclass(frozen=True) class ChangelogEntry`

- **Purpose:** One changelog row of a release: what changed between releases and whether the
  change is a breaking migration.
- **Inputs (constructor):** `version: str`, `date: date`, `change: str`, `migration: str | None = None`
  (description of required data migration, if any).
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:**
  ```python
  ChangelogEntry(version="V221", date=date(2024, 11, 17),
                 change="prSIA 2024-C1 values; Qhc extended to 40 stations",
                 migration="Qhc table layout extended by 12 columns per station block")
  ```

### 2.5 `VersionResolver`

`class VersionResolver`

- **Purpose:** Resolves user-facing release ids and aliases (`"latest"`, `"V221"`) to concrete
  `DatasetRelease` / `ModelRelease` objects. Central place for "what is installed" and "what is
  current"; used by `RaumdatenService`, `CalculationEngine`, the FastAPI and MCP layers and the
  CLI. Never resolves silently inside a calculation — the resolved ids are recorded in
  `VersionInfo`.
- **Inputs (constructor):** `datasets: Mapping[str, DatasetRelease]`,
  `models: Mapping[str, ModelRelease]`, `implementation_version: str | None = None`.
- **Attributes:** `datasets`, `models`.
- **Outputs:** — (service object; results are returned by its methods).
- **Methods:**
  - **`resolve_dataset(release_id: str) -> DatasetRelease`** — resolves `release_id`; accepts
    `"latest"` (highest `publication_date`). **Raises:** `DatasetNotFoundError` on unknown id.
  - **`resolve_model(model_id: str) -> ModelRelease`** — same for models; `"latest"` supported.
    **Raises:** `DatasetNotFoundError` (reused) on unknown id.
  - **`list_datasets() -> list[DatasetRelease]`** — all installed releases, newest first.
  - **`list_models() -> list[ModelRelease]`** — all installed models, newest first.
  - **`current() -> VersionInfo`** — `VersionInfo` of latest dataset, latest model, library
    version and latest installed climate version.
- **Raises:** constructor: —; methods as noted.
- **Example:**
  ```python
  from energytools.common.versioning import VersionResolver, DatasetRelease, ModelRelease
  resolver = VersionResolver(
      datasets={"V221": rel_v221},
      models={"1.0.0": model_100},
      implementation_version="0.1.0",
  )
  current = resolver.current()              # VersionInfo(dataset="V221", model="1.0.0", …)
  assert resolver.resolve_dataset("latest") is rel_v221
  resolver.resolve_dataset("V199")          # → DatasetNotFoundError
  ```

---

## 3. `energytools.common.units`

### 3.1 `Unit`

`class Unit`

- **Purpose:** A unit of measure with a display symbol, an SI hint and conversion metadata.
  Units are parsed from the workbook's rich-text unit cells during extraction (normalized from
  e.g. `W/m²`); unknown symbols raise `UnitError`. Provides conversion within the same physical
  dimension.
- **Inputs (constructor):** `symbol: str` (e.g. `"W/m2"`, `"kWh"`, `"mbar"`, `"%"`, `"-"`),
  `si_hint: str | None = None` (e.g. `"W·m⁻²"`), `dimension: str | None = None`
  (e.g. `"power_per_area"`; inferred from the unit registry when omitted).
- **Attributes:** `symbol`, `si_hint`, `dimension`.
- **Outputs:** — (value object; conversion results are returned by its methods).
- **Methods:**
  - **`convert_to(value: float, target: Unit) -> float`** — converts `value` in this unit to
    `target`. **Raises:** `UnitError` when dimensions differ or conversion factors are unknown.
  - **`__str__()`** — the symbol.
- **Raises:** `UnitError` on unknown symbol (constructor).
- **Example:**
  ```python
  from energytools.common.units import Unit
  w_per_m2 = Unit("W/m2")
  kw_per_m2 = Unit("kW/m2")
  assert w_per_m2.convert_to(1000.0, kw_per_m2) == 1.0
  Unit("not-a-unit")          # → UnitError
  ```

### 3.2 `Quantity`

`@dataclass(frozen=True) class Quantity`

- **Purpose:** Typed value + unit pair used across the domain model (parameter values, results,
  profile values). Conversion-safe and format-safe; the API serializes it as
  `{"value": …, "unit": …}`.
- **Inputs (constructor):** `value: float | int | None`, `unit: Unit | str`
  (str is parsed via `Unit`).
- **Attributes:** `value`, `unit`.
- **Outputs:** — (value object; converted/formatted values are returned by its methods).
- **Methods:**
  - **`to(unit: Unit | str) -> Quantity`** — converted copy. **Raises:** `UnitError`.
  - **`format(precision: int = 2) -> str`** — e.g. `"12.34 W/m2"`. **Raises:** —.
  - **`as_dict() -> dict`** — `{"value": …, "unit": "…"}`. **Raises:** —.
- **Raises:** constructor: `UnitError` on invalid unit string.
- **Example:**
  ```python
  from energytools.common.units import Quantity, Unit
  q = Quantity(45.0, "kWh/m2")
  q.to(Unit("MWh/m2")).format()      # "0.05 MWh/m2"
  q.as_dict()                        # {'value': 45.0, 'unit': 'kWh/m2'}
  ```

---

## 4. `energytools.common.language`

### 4.1 `Language`

`class Language(enum.Enum)`

- **Purpose:** The three workbook languages (assessment §1.2: `Begriffe!G1` = 1/2/3).
- **Members:** `DE = "de"`, `FR = "fr"`, `IT = "it"`.
- **Inputs:** — (enum members; `parse` takes `value: str`).
- **Outputs:** the enum member; `parse` returns `Language`.
- **Methods:**
  - **`parse(value: str) -> Language`** — accepts `"de"/"fr"/"it"` (case-insensitive) and
    `"1"/"2"/"3"` (workbook indices). **Raises:** `UnknownLanguageError`.
- **Example:**
  ```python
  from energytools.common.language import Language
  Language.parse("1") is Language.DE    # workbook index 1 = German
  Language.parse("fr") is Language.FR
  Language.parse("en")                   # → UnknownLanguageError
  ```

### 4.2 `TrilingualText`

`@dataclass(frozen=True) class TrilingualText`

- **Purpose:** A DE/FR/IT label triple (names, parameter labels, sheet titles). Normalizes the
  workbook's rich-text cells to plain structured strings during extraction.
- **Inputs (constructor):** `de: str = ""`, `fr: str = ""`, `it: str = ""`.
- **Attributes:** `de`, `fr`, `it`; `as_dict()` → `{"de": …, "fr": …, "it": …}`.
- **Outputs:** — (value object; labels are returned by `get`/`as_dict`).
- **Methods:**
  - **`get(language: Language | str) -> str`** — label in the requested language; falls back to
    `de` when the requested field is empty (observed: unfinished Italian cells). **Raises:**
    `UnknownLanguageError` on invalid language input.
- **Raises:** —.
- **Example:**
  ```python
  from energytools.common.language import TrilingualText, Language
  name = TrilingualText(de="Wohnen MFH", fr="Habitation CMI", it="Abitazione CMI")
  name.get(Language.FR)                 # 'Habitation CMI'
  name.get("it")                        # 'Abitazione CMI'
  ```

---

## 5. `energytools.common.valuekind`

### 5.1 `ValueKind`

`class ValueKind(enum.Enum)`

- **Purpose:** The three value kinds of the Raumdaten dataset (assessment §1.2, columns M/N/O of
  `Datenblatt`): Standard, Zielwert, Bestand.
- **Members:** `STANDARD = "standard"`, `ZIELWERT = "zielwert"`, `BESTAND = "bestand"`.
- **Inputs:** — (enum members; `parse` takes `value: str`).
- **Outputs:** the enum member; `parse` returns `ValueKind`.
- **Methods:**
  - **`parse(value: str) -> ValueKind`** — case-insensitive; accepts `"standard"`,
    `"zielwert"`, `"bestand"` (also `"target"`/`"existing"` aliases). **Raises:**
    `UnknownValueKindError`.
- **Example:**
  ```python
  from energytools.common.valuekind import ValueKind
  ValueKind.parse("Zielwert") is ValueKind.ZIELWERT
  ValueKind.parse("optimal")           # → UnknownValueKindError
  ```

---

## 6. `energytools.common.provenance`

### 6.1 `SourceRef`

`@dataclass(frozen=True) class SourceRef`

- **Purpose:** One grounded source reference: where a value or formula came from in the source
  workbook. Keeps traceability without exposing addresses through the API (addresses are
  metadata, not API — assessment §5.3 rule 1).
- **Inputs (constructor):** `workbook: str` (e.g. `"2024_Raumdatenblätter_dfi_V221.xlsm"`),
  `sheet: str` (exact sheet name as stored, e.g. `"tblEingabedaten"`), `range: str | None`
  (e.g. `"M11"` or `"A9:C53"`), `formula: str | None` (extracted formula text, e.g.
  `INDEX(Eingabedaten!C9:C53,nutzid)`), `cached_value: str | float | None` (the value Excel
  cached), `extraction_hash: str | None` (package fingerprint).
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; serializes via `as_dict()`).
- **Raises:** `ValueError` if neither `range` nor `formula` is set.
- **Example:**
  ```python
  SourceRef(workbook="2024_Raumdatenblätter_dfi_V221.xlsm", sheet="Datenblatt",
            range="O2", formula="INDEX(Eingabedaten!A9:A53,nutzid)", cached_value="1.01")
  ```

### 6.2 `Provenance`

`@dataclass(frozen=True) class Provenance`

- **Purpose:** Collection of `SourceRef`s plus a free-text note for one domain value or derived
  result. Every `ParameterValue`, derived profile value and calculation intermediate may carry
  one; the API surfaces it in `assumptions[]`/`overriddenValues[]` (assessment §6.2).
- **Inputs (constructor):** `sources: tuple[SourceRef, ...] = ()`, `note: str | None = None`.
- **Attributes:** `sources`, `note`.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:**
  ```python
  Provenance(sources=(SourceRef(workbook=…, sheet="Profile", range="O611:AB611"),),
             note="Annual ventilation full-load hours, 365-day engine, prSIA 2024-C1")
  ```
