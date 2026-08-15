# Part 03 — API Reference: `energytools.raumdaten` (Data Service)

**Document set 02** · Target-state design specification · Back to [index](README.md) ·
Inventory: [01-package-inventory.md](01-package-inventory.md) · Foundation:
[02-common-foundation.md](02-common-foundation.md)

The Raumdaten data service: the canonical, versioned, machine-readable dataset (assessment §5.1)
as an OOP model (§1), loading/extraction (§2), the semantic read-only query API `RaumdatenService`
(§3) and profile comparison (§4). All exceptions come from `energytools.common.errors`.

---

## 1. `energytools.raumdaten.model`

### 1.1 `RoomUse`

`@dataclass(frozen=True) class RoomUse`

- **Purpose:** One of the **45 standard room uses** (assessment §1.2: `Eingabedaten` rows 9–53).
  Carries the numeric `nutzid` (1–45, the workbook's selector value for `Datenblatt!C1`), the SIA
  code (e.g. `"1.01"`), the category (1 Wohnen … 12 Nebenräume) and trilingual names.
- **Inputs (constructor):** `nutzid: int` (1–45), `code: str` (SIA code, e.g. `"1.01"`),
  `category: int` (1–12), `name: TrilingualText`, `sia_clause: str | None = None`
  (SIA clause identifier, e.g. `"1.1.1"`).
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` if `nutzid` outside 1–45 or `code` empty.
- **Example:**
  ```python
  RoomUse(nutzid=1, code="1.01", category=1,
          name=TrilingualText(de="Wohnen MFH", fr="Habitation CMI", it="Abitazione CMI"))
  ```

### 1.2 `Parameter`

`@dataclass(frozen=True) class Parameter`

- **Purpose:** One of the **193 data-sheet parameters** (assessment §1.2, `Datenblatt` rows
  4–196). The stable id is the **SIA clause number** (e.g. `"1.1.2.7"` Jahresgleichzeitigkeit)
  or a documented slug; carries trilingual label, symbol, unit, data type, category, applicable
  value kinds and the observed P/Q/R/S export/display flags.
- **Inputs (constructor):** `id: str` (clause id or slug), `label: TrilingualText`,
  `symbol: str` (normalized from rich text, e.g. `"A_NGF"`), `unit: Unit | str`,
  `data_type: str` (`"number" | "enum" | "text" | "bool"`), `category: str` (e.g. `"Raum"`,
  `"Lüftung"`), `value_kinds: frozenset[ValueKind]` (e.g. all three), `export_flag: bool =
  True` (column P, "1" = export to results), `display_flag: bool = True` (column Q),
  `internal_heat_flag: bool = False` (column R), `qhc_flag: bool = False` (column S),
  `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` on empty `id` or unknown `data_type`.
- **Example:**
  ```python
  Parameter(id="1.1.2.7", label=TrilingualText(de="Jahresgleichzeitigkeit", fr="…", it="…"),
            symbol="g", unit="%", data_type="number", category="Raumklima",
            value_kinds=frozenset(ValueKind))
  ```

### 1.3 `ParameterValue`

`@dataclass(frozen=True) class ParameterValue`

- **Purpose:** One value of one parameter in one value kind, with unit and provenance. Replaces
  the workbook's raw cell triple (columns M/N/O) by a typed object.
- **Inputs (constructor):** `parameter_id: str`, `kind: ValueKind`, `value: float | int | str |
  bool | None`, `unit: Unit | str`, `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields; `quantity` property → `Quantity(value, unit)`.
- **Outputs:** — (value object).
- **Raises:** `UnknownParameterError` is not raised here (no catalog access); `UnitError` on
  invalid unit string.
- **Example:**
  ```python
  ParameterValue(parameter_id="1.1.2.7", kind=ValueKind.STANDARD, value=0.7, unit="%")
  ```

### 1.4 `RoomUseProfile`

`@dataclass class RoomUseProfile`

- **Purpose:** The full parameter-value set of one room use, for all value kinds — the digital
  equivalent of the rendered `Datenblatt` sheet for `nutzid`. Immutable after construction;
  built by `Dataset`.
- **Inputs (constructor):** `room_use: RoomUse`, `values: Mapping[str, Mapping[ValueKind,
  ParameterValue]]` (parameter id → kind → value), `parameter_catalog: Mapping[str, Parameter]`.
- **Attributes:** `room_use`, `values`, `parameter_catalog`.
- **Outputs:** — (value object; data access via its methods).
- **Methods:**
  - **`value(parameter_id: str, kind: ValueKind = ValueKind.STANDARD) -> ParameterValue`** —
    lookup. **Raises:** `UnknownParameterError` for unknown `parameter_id`;
    `KeyError`-free: returns `ParameterValue(…, value=None)` for a kind not applicable.
  - **`parameters() -> list[Parameter]`** — catalog entries in sheet order.
  - **`to_frame(kind: ValueKind) -> pandas.DataFrame`** — rows = parameters (id, label, symbol,
    unit, value) for one kind. **Raises:** —.
  - **`as_dict(kind: ValueKind | None = None) -> dict`** — JSON-ready; `None` = all kinds.
- **Raises:** constructor: `ValueError` on inconsistent catalog.
- **Example:**
  ```python
  profile = dataset.profile(1)
  pv = profile.value("1.1.2.7", ValueKind.ZIELWERT)
  print(pv.value, pv.unit.symbol)          # e.g. 0.6 %
  profile.to_frame(ValueKind.STANDARD)
  ```

### 1.5 `HourlyProfile`

`@dataclass(frozen=True) class HourlyProfile`

- **Purpose:** One 24 h profile (person / device / lighting / ventilation loads) — the observed
  `Profile` sheet rows 58–86 (assessment §1.2). Hour index 0–23.
- **Inputs (constructor):** `id: str` (e.g. `"personen_werktag"`), `profile_type: str`
  (`"person" | "device" | "lighting" | "ventilation"`), `values: tuple[float, ...]` (length 24),
  `unit: Unit | str = "%"`, `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` if `len(values) != 24`.
- **Example:**
  ```python
  HourlyProfile(id="licht_buero", profile_type="lighting",
                values=(0.0, 0.0, …, 1.0, 0.5, …), unit="%")
  ```

### 1.6 `MonthlyProfile`

`@dataclass(frozen=True) class MonthlyProfile`

- **Purpose:** Twelve monthly values (climate or load), as in `Monatswerte` rows and the
  monthly profile columns of `Eingabedaten`.
- **Inputs (constructor):** `id: str`, `values: tuple[float, ...]` (length 12),
  `unit: Unit | str`, `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` if `len(values) != 12`.
- **Example:** `MonthlyProfile(id="t_aussen", values=(…), unit="°C")`

### 1.7 `WeeklyProfile`

`@dataclass(frozen=True) class WeeklyProfile`

- **Purpose:** Seven-day weekly profile (observed `Eingabedaten` weekly profile section).
- **Inputs (constructor):** `id: str`, `values: tuple[float, ...]` (length 7),
  `unit: Unit | str = "%"`, `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` if `len(values) != 7`.
- **Example:** `WeeklyProfile(id="woche_buero", values=(0.2, 0.2, …, 0.1), unit="%")`

### 1.8 `ClimateStation`

`@dataclass(frozen=True) class ClimateStation`

- **Purpose:** One of the **40 climate stations** (assessment §1.2): winter design values
  (`Winter_Auslegung!H5:H44`), summer design values (`Aug_Auslegung`), monthly values
  (`Monatswerte`), heating degree days and temperature-bin hours (`Klimadaten` in the
  Gebäude-Tool).
- **Inputs (constructor):** `id: int` (1–40), `name: TrilingualText`,
  `winter_design: dict[str, Quantity]` (e.g. `{"t_a": …, "radiation": …, "wind": …}`),
  `summer_design: dict[str, Quantity]`, `monthly: dict[str, MonthlyProfile]`,
  `temperature_bins: tuple[TemperatureBin, …] | None = None` (bin edges + hours, from
  `Klimadaten` "Anzahl Stunden Tac"), `hdd: Quantity | None = None`,
  `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` on empty `name`.
- **Example:**
  ```python
  ClimateStation(id=40, name=TrilingualText(de="Zürich-MeteoSchweiz", fr="…", it="…"),
                 winter_design={"t_a": Quantity(-8.0, "°C"), …}, monthly={…})
  ```

### 1.9 `ClimateData`

`@dataclass(frozen=True) class ClimateData`

- **Purpose:** The immutable collection of all stations of a release, with a version tag (the
  assessment's climate-version requirement, §8.6).
- **Inputs (constructor):** `version: str` (e.g. `"meteoschweiz-2024"`),
  `stations: tuple[ClimateStation, ...]`, `source: str | None = None`.
- **Attributes:** `version`, `stations`, `source`.
- **Outputs:** — (value object; lookup results are returned by its methods).
- **Methods:**
  - **`station(station_id: int | str) -> ClimateStation`** — lookup by id. **Raises:**
    `UnknownClimateStationError`.
  - **`ids() -> tuple[int, ...]`** — station ids in order.
- **Raises:** —.
- **Example:** `dataset.climate().station(40).name.get("de")  # 'Zürich-MeteoSchweiz'`

### 1.10 `FullLoadHoursTable`

`@dataclass(frozen=True) class FullLoadHoursTable`

- **Purpose:** Ventilation full-load hours per room use × regulation type × **standard version**
  (SIA 2024:2015 / prSIA 2024:2021 / prSIA 2024-C1:2024) — the versioned `Volll_Lüft` table
  (assessment §1.2, §5.1). The version axis is the model for the whole dataset's evolution.
- **Inputs (constructor):** `rows: Mapping[tuple[int, str, str], float]` (key = (nutzid,
  regulation, standard_version)), `standard_versions: frozenset[str]`, `regulations:
  frozenset[str]` (e.g. `{"1-stufig", "2-stufig", "stufenlos"}`), `provenance: Provenance | None
  = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; lookup results are returned by its methods).
- **Methods:**
  - **`hours(room_use_id: int, regulation: str, standard_version: str) -> float`** — lookup.
    **Raises:** `KeyError` → wrapped as `EnergyToolsError` subclass `KeyError`-compatible
    message; `UnknownRoomUseError` for unknown `room_use_id` (validated against the release).
- **Raises:** —.
- **Example:**
  ```python
  t = dataset.full_load_hours()
  t.hours(1, "2-stufig", "prSIA 2024-C1:2024")    # e.g. 2850.0 h/a
  ```

### 1.11 `BuildingCategoryMapping`

`@dataclass(frozen=True) class BuildingCategoryMapping`

- **Purpose:** One row of the SIA 2024 ↔ SIA 380/1 building-category mapping (`GEPAMOD` sheet,
  Gebaeudekategorien I…X).
- **Inputs (constructor):** `sia3801_category: str` (e.g. `"I"`), `room_use_codes:
  frozenset[str]`, `name: TrilingualText | None = None`, `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:** `BuildingCategoryMapping(sia3801_category="I", room_use_codes=frozenset({"1.01"}))`

### 1.12 `AreaTable`

`@dataclass(frozen=True) class AreaTable`

- **Purpose:** One building-category area table (`Fläche-E` / `-L` / `-ZW` / `-Best` sheets): per
  category, the area per room use. The sheet suffix encodes the value kind; the model carries it
  explicitly.
- **Inputs (constructor):** `kind: ValueKind`, `rows: Mapping[str, Mapping[str, Quantity]]`
  (category → room-use code → area), `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:** `AreaTable(kind=ValueKind.STANDARD, rows={"I": {"1.01": Quantity(1200.0, "m2")}})`

### 1.13 `Sia3801Coefficients`

`@dataclass(frozen=True) class Sia3801Coefficients`

- **Purpose:** Per-category SIA 380/1 coefficients (from `SIA 380-1` / `_Qc` / `_EN` / `_Qc_EN`
  sheets — the four sheets are **one calculation with a variant axis**, assessment §8.9).
- **Inputs (constructor):** `variant: str` (`"de" | "en" | "de+qc" | "en+qc"`), `category: str`,
  `coefficients: dict[str, Quantity]` (e.g. `{"U_E3": …, "U_E4": …, "U_DAFbeheizt": …, "tau0": …
  }` — named ranges observed in the workbook), `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** `ValueError` on unknown `variant`.
- **Example:**
  ```python
  Sia3801Coefficients(variant="de", category="I",
                      coefficients={"tau0": Quantity(60.0, "h"), "U_E3": Quantity(0.20, "W/m2K")})
  ```

### 1.14 `Sia3801Result`

`@dataclass(frozen=True) class Sia3801Result`

- **Purpose:** SIA 380/1 heating-demand result of one room use (Qh and related values incl. the
  cooling variant Qc), computed for a station and value kind.
- **Inputs (constructor):** `room_use_id: int`, `station_id: int`, `kind: ValueKind`,
  `variant: str`, `values: dict[str, Quantity]` (e.g. `{"Qh": …, "Qc": …}`),
  `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:** `Sia3801Result(room_use_id=1, station_id=40, kind=ValueKind.STANDARD,
  variant="de", values={"Qh": Quantity(38.0, "kWh/m2a")})`

### 1.15 `QhcTable`

`@dataclass(frozen=True) class QhcTable`

- **Purpose:** Annual cooling energy Qhc per room use × climate station × value kind — the
  `Qhc_Klimastat` matrix (40 stations × 45 uses; assessment §1.2).
- **Inputs (constructor):** `rows: Mapping[tuple[int, int, ValueKind], Quantity]` (key =
  (nutzid, station_id, kind)), `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; lookup results are returned by its methods).
- **Methods:**
  - **`qhc(room_use_id: int, station_id: int, kind: ValueKind = ValueKind.STANDARD) ->
    Quantity`** — lookup. **Raises:** `UnknownRoomUseError` / `UnknownClimateStationError` for
    unknown ids (validated against the release); `KeyError` when the combination is absent.
- **Raises:** —.
- **Example:**
  ```python
  dataset.qhc().qhc(1, 40, ValueKind.STANDARD)   # e.g. 12.4 kWh/m2a
  ```

### 1.16 `Dataset`

`@dataclass(frozen=True) class Dataset`

- **Purpose:** One immutable dataset release: every table of the canonical package plus the
  release metadata. This is the **only** way the calculation engine consumes Raumdaten
  (assessment §5.3 rule 2).
- **Inputs (constructor):** `release: DatasetRelease`, `room_uses: tuple[RoomUse, ...]`,
  `parameters: tuple[Parameter, ...]`, `profiles: Mapping[int, RoomUseProfile]` (by nutzid),
  `hourly_profiles: tuple[HourlyProfile, ...]`, `monthly_profiles: tuple[MonthlyProfile, ...]`,
  `weekly_profiles: tuple[WeeklyProfile, ...]`, `climate: ClimateData`,
  `full_load_hours: FullLoadHoursTable`, `qhc: QhcTable`,
  `sia3801: tuple[Sia3801Result, ...]`, `mappings: tuple[BuildingCategoryMapping, ...]`,
  `area_tables: tuple[AreaTable, ...]`, `sia3801_coefficients: tuple[Sia3801Coefficients, ...]`.
- **Attributes:** all constructor fields; `release_id` property.
- **Outputs:** — (value object; data access via its methods).
- **Methods:**
  - **`room_use(room_use_id: int | str) -> RoomUse`** — by nutzid or SIA code. **Raises:**
    `UnknownRoomUseError`.
  - **`room_uses() -> tuple[RoomUse, ...]`** — in sheet order (nutzid 1–45).
  - **`parameter(parameter_id: str) -> Parameter`** — **Raises:** `UnknownParameterError`.
  - **`parameters() -> tuple[Parameter, ...]`** — in sheet order (Datenblatt rows).
  - **`profile(room_use_id: int, kind: ValueKind | None = None) -> RoomUseProfile`** —
    **Raises:** `UnknownRoomUseError`.
  - **`climate() -> ClimateData`**, **`full_load_hours() -> FullLoadHoursTable`**,
    **`qhc() -> QhcTable`**, **`sia3801_results(variant: str | None = None) ->
    tuple[Sia3801Result, ...]`**, **`mappings() -> tuple[BuildingCategoryMapping, ...]`** —
    accessors.
  - **`validate() -> ValidationReport`** — schema + domain-value validation (see
    `ValidationReport` in part 04 §1.10). **Raises:** — (errors are reported, not raised).
- **Raises:** constructor: `ValueError` on inconsistent content (e.g. profile count ≠ 45).
- **Example:**
  ```python
  ds = load_dataset("V221")
  ds.room_use("12.10")          # nutzid 45, code '12.10' (quality quirk 12.1 → normalized)
  ds.profile(1).value("1.1.2.7")
  ```

---

## 2. `energytools.raumdaten.dataset`

### 2.1 `load_dataset`

`def load_dataset(release_id: str, path: str | None = None) -> Dataset`

- **Purpose:** Loads a dataset release from disk (JSON package + JSON Schema) into a `Dataset`.
  Results are cached in the process-wide `DatasetStore`; subsequent calls with the same
  `release_id` return the identical frozen object.
- **Inputs:** `release_id: str` (e.g. `"V221"`), `path: str | None = None` (directory of the
  package; defaults to the configured dataset directory).
- **Outputs:** `Dataset` (frozen, fully validated on load).
- **Raises:** `DatasetNotFoundError` (release not installed), `DatasetValidationError`
  (package fails schema validation — a corrupt/foreign package is never half-loaded).
- **Example:**
  ```python
  from energytools.raumdaten.dataset import load_dataset
  ds = load_dataset("V221", path="data/datasets")
  print(ds.release_id, len(ds.room_uses()))      # V221 45
  ```

### 2.2 `DatasetStore`

`class DatasetStore`

- **Purpose:** Process-wide registry of loaded releases. Enforces the invariant "one frozen
  `Dataset` per release id" and answers existence queries without touching disk.
- **Inputs (constructor):** `dataset_dir: str | None = None` (root of installed packages).
- **Attributes:** `dataset_dir`.
- **Outputs:** — (service object; results are returned by its methods).
- **Methods:**
  - **`get(release_id: str) -> Dataset`** — load-on-demand (via `load_dataset`), cached.
    **Raises:** `DatasetNotFoundError`.
  - **`list() -> list[DatasetRelease]`** — installed releases (from package manifests),
    newest first. **Raises:** —.
  - **`register(dataset: Dataset) -> None`** — pre-registers an in-memory dataset (tests,
    custom packages). **Raises:** `ValueError` on duplicate id with different content.
  - **`refresh() -> None`** — drops the cache and re-scans the dataset directory.
- **Raises:** constructor: —.
- **Example:**
  ```python
  store = DatasetStore("data/datasets")
  store.list()                # [DatasetRelease(id='V221', …)]
  ds = store.get("V221")
  ```

### 2.3 `DatasetExtractor`

`class DatasetExtractor`

- **Purpose:** Stage-0 extraction pipeline (assessment §7.1): reads a **copy** of the source
  workbook deterministically (cell graph: values + formulas + cached results), checksums it,
  validates against the package JSON Schema and writes the canonical JSON package + manifest.
  No cell is written, no macro runs, no link is followed.
- **Inputs (constructor):** `workbook_path: str` (path to a **copy** of
  `2024_Raumdatenblätter_dfi_V221.xlsm`), `output_dir: str`,
  `release_id: str = "V221"`, `extraction_tool_version: str`.
- **Attributes:** `workbook_path`, `output_dir`, `release_id`.
- **Outputs:** — (pipeline object; the extraction result is returned by `extract`).
- **Methods:**
  - **`extract() -> DatasetRelease`** — runs the pipeline and returns the release metadata of
    the written package. **Raises:** `DatasetValidationError` (unexpected sheet layout,
    missing required tables, unknown value kinds); `OSError` (unreadable copy).
- **Raises:** constructor: `FileNotFoundError` when the copy does not exist.
- **Example:**
  ```python
  from energytools.raumdaten.dataset import DatasetExtractor
  rel = DatasetExtractor("data/raw/_copies/Raumdaten_V221.xlsm", "data/datasets").extract()
  print(rel.checksum_sha256)
  ```

---

## 3. `energytools.raumdaten.service`

### 3.1 `RaumdatenService`

`class RaumdatenService`

- **Purpose:** The **read-only semantic query API** over the canonical dataset (assessment §6.1).
  One service instance = one `DatasetStore` + one `VersionResolver`. All methods take
  `release_id` explicitly (never "whatever is loaded") and return domain objects or
  JSON-ready dicts; none exposes Excel addresses. This class is the single dependency of the
  FastAPI datasets router and the MCP data tools.
- **Inputs (constructor):** `store: DatasetStore | None = None`,
  `resolver: VersionResolver | None = None` (defaults are created from the dataset directory).
- **Attributes:** `store`, `resolver`.
- **Outputs:** — (service instance; all data access via its methods).
- **Raises:** constructor: —.
- **Example:**
  ```python
  from energytools.raumdaten.service import RaumdatenService
  from energytools.raumdaten.dataset import DatasetStore
  service = RaumdatenService(store=DatasetStore("data/datasets"))
  service.list_room_uses("V221", "de")[:2]
  ```

### 3.2 Methods

Every method below raises `DatasetNotFoundError` for an unknown `release_id` and uses the
`Unknown*` errors for unknown ids (see part 02). `language`/`value_kind` arguments accept
`Language`/`ValueKind` or their string forms and raise `UnknownLanguageError` /
`UnknownValueKindError` on invalid input.

#### `list_releases() -> list[dict]`

- **Purpose:** List dataset releases (id, edition, date, checksum, supersedes) — the `GET
  /datasets` endpoint payload.
- **Inputs:** —.
- **Outputs:** List of JSON-ready release dicts, newest first.
- **Raises:** —.
- **Example:** `service.list_releases()[0]["id"]  # 'V221'`

#### `get_release(release_id: str) -> dict`

- **Purpose:** Full release metadata incl. changelog.
- **Inputs:** `release_id: str` (alias `"latest"` allowed).
- **Outputs:** Release dict incl. `changelog`.
- **Raises:** `DatasetNotFoundError`.
- **Example:** `service.get_release("latest")`

#### `list_room_uses(release_id: str, language: Language | str = Language.DE) -> list[dict]`

- **Purpose:** The 45 room uses with id, code, category and localized name — dropdown/selector
  data (replaces the workbook's external-link list, assessment §3).
- **Inputs:** `release_id`, `language` (label language).
- **Outputs:** `[{nutzid, code, category, name}, …]` in sheet order.
- **Raises:** `DatasetNotFoundError`, `UnknownLanguageError`.
- **Example:** `service.list_room_uses("V221", "fr")`

#### `get_room_use(release_id: str, room_use_id: int | str) -> dict`

- **Purpose:** One room use (all languages).
- **Inputs:** `release_id`, `room_use_id` (nutzid or SIA code).
- **Outputs:** `{nutzid, code, category, name: {de, fr, it}, sia_clause}`.
- **Raises:** `DatasetNotFoundError`, `UnknownRoomUseError`.
- **Example:** `service.get_room_use("V221", "1.01")`

#### `get_room_use_profile(release_id: str, room_use_id: int | str, value_kind: ValueKind | str | None = None) -> dict`

- **Purpose:** The full data-sheet content of one room use (assessment §6.1
  `get_room_use_profile`): all parameters with values per kind, units and provenance.
- **Inputs:** `release_id`, `room_use_id`, `value_kind` (None = all three kinds).
- **Outputs:** `{room_use: …, parameters: [{id, label, symbol, unit, category, values:
  {standard: {value, unit, provenance}, …}}]}`.
- **Raises:** `DatasetNotFoundError`, `UnknownRoomUseError`, `UnknownValueKindError`.
- **Example:**
  ```python
  prof = service.get_room_use_profile("V221", 1, "zielwert")
  prof["parameters"][0]["values"]["zielwert"]["value"]
  ```

#### `list_parameters(release_id: str, language: Language | str = Language.DE) -> list[dict]`

- **Purpose:** The parameter catalog (clause ids, labels, symbols, units, types, categories,
  flags).
- **Inputs:** `release_id`, `language`.
- **Outputs:** List of parameter dicts in sheet order.
- **Raises:** `DatasetNotFoundError`, `UnknownLanguageError`.
- **Example:** `[p["id"] for p in service.list_parameters("V221")]`

#### `get_parameter(release_id: str, parameter_id: str) -> dict`

- **Purpose:** One parameter incl. applicable value kinds and flags.
- **Inputs:** `release_id`, `parameter_id`.
- **Outputs:** Parameter dict.
- **Raises:** `DatasetNotFoundError`, `UnknownParameterError`.
- **Example:** `service.get_parameter("V221", "1.1.2.7")`

#### `compare_room_use_profiles(release_id: str, a: int | str, b: int | str) -> dict`

- **Purpose:** Compare two room-use profiles (assessment §6.1 `compare_room_use_profiles`):
  per-parameter diffs across all value kinds.
- **Inputs:** `release_id`, `a`, `b` (nutzid or SIA code).
- **Outputs:** JSON-ready `ProfileDiff` dict (see §4.2).
- **Raises:** `DatasetNotFoundError`, `UnknownRoomUseError`.
- **Example:** `service.compare_room_use_profiles("V221", "1.01", "1.02")`

#### `list_climate_stations(release_id: str, language: Language | str = Language.DE) -> list[dict]`

- **Purpose:** The 40 stations with ids and names.
- **Inputs:** `release_id`, `language`.
- **Outputs:** `[{id, name}, …]`.
- **Raises:** `DatasetNotFoundError`, `UnknownLanguageError`.
- **Example:** `service.list_climate_stations("V221")[39]["name"]  # 'Zürich-MeteoSchweiz'`

#### `get_climate_station(release_id: str, station_id: int | str) -> dict`

- **Purpose:** Full station data (winter/summer design, monthly values, bins, HDD).
- **Inputs:** `release_id`, `station_id`.
- **Outputs:** Station dict with `Quantity`-style values.
- **Raises:** `DatasetNotFoundError`, `UnknownClimateStationError`.
- **Example:** `service.get_climate_station("V221", 40)`

#### `list_profiles(release_id: str) -> dict`

- **Purpose:** Hourly/monthly/weekly profile sets (assessment §6.1 `GET /profiles`).
- **Inputs:** `release_id`.
- **Outputs:** `{hourly: […], monthly: […], weekly: […]}`.
- **Raises:** `DatasetNotFoundError`.
- **Example:** `service.list_profiles("V221")["hourly"][0]`

#### `get_full_load_hours(release_id: str, room_use_id: int | str, regulation: str, standard_version: str) -> dict`

- **Purpose:** Ventilation full-load hours for one use × regulation × standard version.
- **Inputs:** `release_id`, `room_use_id`, `regulation` (`"1-stufig" | "2-stufig" |
  "stufenlos"`), `standard_version` (`"SIA 2024:2015" | "prSIA 2024:2021" |
  "prSIA 2024-C1:2024"`).
- **Outputs:** `{room_use_id, regulation, standard_version, hours: float, unit: "h/a",
  provenance}`.
- **Raises:** `DatasetNotFoundError`, `UnknownRoomUseError`.
- **Example:** `service.get_full_load_hours("V221", 1, "2-stufig", "prSIA 2024-C1:2024")`

#### `get_qhc(release_id: str, room_use_id: int | str, station_id: int | str, value_kind: ValueKind | str = ValueKind.STANDARD) -> dict`

- **Purpose:** Annual cooling energy Qhc for one use × station × kind.
- **Inputs:** `release_id`, `room_use_id`, `station_id`, `value_kind`.
- **Outputs:** `{room_use_id, station_id, kind, qhc: {value, unit}, provenance}`.
- **Raises:** `DatasetNotFoundError`, `UnknownRoomUseError`, `UnknownClimateStationError`,
  `UnknownValueKindError`.
- **Example:** `service.get_qhc("V221", 1, 40)`

#### `get_sia3801(release_id: str, room_use_id: int | str, variant: str = "de") -> dict`

- **Purpose:** SIA 380/1 result (incl. Qc variant) of one room use.
- **Inputs:** `release_id`, `room_use_id`, `variant` (`"de" | "en" | "de+qc" | "en+qc"`).
- **Outputs:** Result dict with values and provenance.
- **Raises:** `DatasetNotFoundError`, `UnknownRoomUseError`.
- **Example:** `service.get_sia3801("V221", 1, "de+qc")`

#### `validate(release_id: str) -> dict`

- **Purpose:** Validation report of a release (schema + value rules; assessment §6.1
  `POST /datasets/{release}/validate`).
- **Inputs:** `release_id`.
- **Outputs:** `{release_id, valid: bool, errors: [...], warnings: [...]}`.
- **Raises:** `DatasetNotFoundError`.
- **Example:** `service.validate("V221")["valid"]  # True`

#### `export(release_id: str, fmt: str, scope: str, target: str) -> dict`

- **Purpose:** Bulk export of a release (assessment §6.1 `GET /exports.{json|csv|xlsx}`);
  delegates to the export layer (part 05 §3).
- **Inputs:** `release_id`, `fmt` (`"json" | "csv" | "xlsx" | "pdf"`), `scope` (e.g.
  `"room-uses" | "profiles" | "climate" | "full-load-hours" | "qhc" | "all"`), `target` (file
  path).
- **Outputs:** `{release_id, format, scope, target, bytes, checksum}`.
- **Raises:** `DatasetNotFoundError`, `ExportError`.
- **Example:** `service.export("V221", "xlsx", "all", "out/V221.xlsx")`

---

## 4. `energytools.raumdaten.compare`

### 4.1 `compare_profiles`

`def compare_profiles(a: RoomUseProfile, b: RoomUseProfile) -> ProfileDiff`

- **Purpose:** Pure comparison of two room-use profiles across all value kinds; used by
  `RaumdatenService.compare_room_use_profiles` and the MCP tool. Replaces manual diffing of the
  workbook result sheets.
- **Inputs:** `a`, `b` (profiles of the same release).
- **Outputs:** `ProfileDiff` (see below).
- **Raises:** `ValueError` if the profiles belong to different releases (checked via parameter
  catalogs).
- **Example:**
  ```python
  from energytools.raumdaten.compare import compare_profiles
  diff = compare_profiles(ds.profile(1), ds.profile(2))
  ```

### 4.2 `ProfileDiff`

`@dataclass(frozen=True) class ProfileDiff`

- **Purpose:** Structured comparison result: which parameters changed/added/removed and the
  per-kind value differences.
- **Inputs (constructor):** `a_id: int`, `b_id: int`, `changed: tuple[ParameterDiff, ...]`,
  `added: tuple[str, ...]` (parameter ids), `removed: tuple[str, ...]`, `identical: bool`.
  (`ParameterDiff` is a small dataclass `{parameter_id, label, symbol, unit, diffs:
  {kind: (value_a, value_b)}}`.)
- **Attributes:** all constructor fields; `as_dict()` → JSON-ready (used by the service).
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:**
  ```python
  diff.as_dict()["changed"][0]["diffs"]["standard"]   # (0.7, 0.6)
  ```
