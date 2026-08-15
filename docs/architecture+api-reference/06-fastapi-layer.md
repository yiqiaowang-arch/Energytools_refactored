# Part 06 — API Reference: FastAPI Layer (`energytools.api`)

**Document set 02** · Target-state design specification · Back to [index](README.md) ·
Inventory: [01-package-inventory.md](01-package-inventory.md) · Foundation:
[02-common-foundation.md](02-common-foundation.md) · Data:
[03-raumdaten-service.md](03-raumdaten-service.md) · Engine:
[04-gebaeude-engine.md](04-gebaeude-engine.md)

The stable domain API (assessment §6, OpenAPI 3 + JSON Schema) as a FastAPI application. The
layer is **thin**: endpoints delegate to `RaumdatenService` / `CalculationEngine` / export
facades; all domain exceptions map to HTTP errors via one exception handler. Domain concepts
only — **no cell addresses** (assessment §5.3 rule 1).

---

## 1. Settings

`class Settings(pydantic.BaseSettings)`

- **Purpose:** Runtime settings of the API process: where datasets/models live, which backend
  is used, request limits, CORS and docs flags. Loaded from environment (`ENERGYTOOLS_*`) and
  `.env`.
- **Inputs (constructor):** environment/config only; fields:
  `dataset_dir: str = "data/datasets"`, `model_dir: str = "data/models"`,
  `backend: str = "native"` (`"native" | "excel"`), `excel_workbook: str | None = None`
  (copy of the Gebaeude workbook for the Excel backend), `result_store_dir: str | None =
  None`, `max_rooms: int = 100`, `max_ventilation_systems: int = 16`,
  `cors_origins: list[str] = []`, `docs_enabled: bool = True`, `api_prefix: str = ""`.
- **Attributes:** all fields (pydantic).
- **Outputs:** —.
- **Raises:** `ValidationError` (pydantic) on invalid environment values.
- **Example:**
  ```python
  from energytools.api.settings import Settings
  settings = Settings(dataset_dir="data/datasets", backend="native")
  ```

## 2. `create_app`

`def create_app(service: RaumdatenService | None = None, engine: CalculationEngine | None =
None, store: CalculationStore | None = None, settings: Settings | None = None) -> FastAPI`

- **Purpose:** Application factory: builds the FastAPI app with the three routers, wires
  dependency injection (defaults created from `settings`), registers the global exception
  handler (domain exceptions → HTTP error responses with `details`) and the OpenAPI schema
  (`/openapi.json`, `/docs`).
- **Inputs:** `service` (data service; default: created from `settings.dataset_dir`),
  `engine` (calculation engine; default: created with `settings.backend`),
  `store` (result store; default: `CalculationStore(settings.result_store_dir)`),
  `settings`.
- **Outputs:** configured `FastAPI` instance (not started).
- **Raises:** —.
- **Example:**
  ```python
  from energytools.api.app import create_app
  app = create_app()                      # defaults from environment
  # uvicorn energytools.api.app:create_app --factory
  ```

## 3. Datasets router

`datasets_router: APIRouter` (prefix `/datasets`, tags `["datasets"]`) — endpoints delegate to
`RaumdatenService`. All error responses follow `{"detail": …, "details": {…}}`; `release_id`
path params accept aliases (`latest`).

### 3.1 `GET /datasets`

- **Purpose:** List dataset releases (id, edition, date, checksum, supersedes).
- **Inputs:** —.
- **Outputs:** `200` → `list[DatasetReleaseOut]` (newest first).
- **Raises:** HTTP —.
- **Example:**
  ```console
  $ curl http://127.0.0.1:8000/datasets
  [{"id": "V221", "edition": "SIA 2024", "publication_date": "2024-11-17", …}]
  ```

### 3.2 `GET /datasets/{release_id}`

- **Purpose:** Full release metadata incl. changelog.
- **Inputs:** `release_id: str` (path).
- **Outputs:** `200` → `DatasetReleaseOut` (with `changelog`).
- **Raises:** HTTP `404` `DatasetNotFoundError`.
- **Example:** `curl http://127.0.0.1:8000/datasets/latest`

### 3.3 `GET /datasets/{release_id}/room-uses`

- **Purpose:** The 45 room uses, localized.
- **Inputs:** `release_id` (path), `language: str = "de"` (query).
- **Outputs:** `200` → `list[RoomUseOut]`.
- **Raises:** HTTP `404` `DatasetNotFoundError`; `422` `UnknownLanguageError`.
- **Example:** `curl "http://127.0.0.1:8000/datasets/V221/room-uses?language=fr"`

### 3.4 `GET /datasets/{release_id}/room-uses/{room_use_id}`

- **Purpose:** One room use, all languages.
- **Inputs:** `release_id`, `room_use_id` (path; nutzid or SIA code).
- **Outputs:** `200` → `RoomUseOut`.
- **Raises:** HTTP `404` `DatasetNotFoundError` / `UnknownRoomUseError`.
- **Example:** `curl http://127.0.0.1:8000/datasets/V221/room-uses/1.01`

### 3.5 `GET /datasets/{release_id}/room-uses/{room_use_id}/profile`

- **Purpose:** Full data-sheet content (assessment §6.1 `get_room_use_profile`).
- **Inputs:** `release_id`, `room_use_id` (path), `value_kind: str | None = None` (query).
- **Outputs:** `200` → `RoomUseProfileOut` (parameters with values per kind, units,
  provenance).
- **Raises:** HTTP `404` dataset/room-use; `422` `UnknownValueKindError`.
- **Example:**
  ```console
  $ curl "http://127.0.0.1:8000/datasets/V221/room-uses/1/profile?value_kind=zielwert"
  ```

### 3.6 `GET /datasets/{release_id}/room-uses/{a}/compare/{b}`

- **Purpose:** Compare two room-use profiles (all kinds).
- **Inputs:** `release_id`, `a`, `b` (path).
- **Outputs:** `200` → `CompareOut`.
- **Raises:** HTTP `404` dataset/room-use.
- **Example:** `curl http://127.0.0.1:8000/datasets/V221/room-uses/1.01/compare/1.02`

### 3.7 `GET /datasets/{release_id}/parameters`

- **Purpose:** Parameter catalog, localized.
- **Inputs:** `release_id` (path), `language: str = "de"` (query).
- **Outputs:** `200` → `list[ParameterOut]`.
- **Raises:** HTTP `404` `DatasetNotFoundError`; `422` `UnknownLanguageError`.
- **Example:** `curl http://127.0.0.1:8000/datasets/V221/parameters`

### 3.8 `GET /datasets/{release_id}/parameters/{parameter_id}`

- **Purpose:** One parameter.
- **Inputs:** `release_id`, `parameter_id` (path; clause id or slug).
- **Outputs:** `200` → `ParameterOut`.
- **Raises:** HTTP `404` `UnknownParameterError`.
- **Example:** `curl http://127.0.0.1:8000/datasets/V221/parameters/1.1.2.7`

### 3.9 `GET /datasets/{release_id}/climate-stations`

- **Purpose:** The 40 stations (id, name).
- **Inputs:** `release_id` (path), `language: str = "de"` (query).
- **Outputs:** `200` → `list[ClimateStationOut]`.
- **Raises:** HTTP `404` `DatasetNotFoundError`.
- **Example:** `curl http://127.0.0.1:8000/datasets/V221/climate-stations`

### 3.10 `GET /datasets/{release_id}/climate-stations/{station_id}`

- **Purpose:** Full station data.
- **Inputs:** `release_id`, `station_id` (path).
- **Outputs:** `200` → `ClimateStationOut` (design values, monthly, bins).
- **Raises:** HTTP `404` `UnknownClimateStationError`.
- **Example:** `curl http://127.0.0.1:8000/datasets/V221/climate-stations/40`

### 3.11 `GET /datasets/{release_id}/profiles`

- **Purpose:** Hourly/monthly/weekly profile sets.
- **Inputs:** `release_id` (path).
- **Outputs:** `200` → `{"hourly": […], "monthly": […], "weekly": […]}`.
- **Raises:** HTTP `404` `DatasetNotFoundError`.
- **Example:** `curl http://127.0.0.1:8000/datasets/V221/profiles`

### 3.12 `GET /datasets/{release_id}/full-load-hours`

- **Purpose:** Ventilation full-load hours (all uses × regulations × standard versions) —
  the versioned `Volll_Lüft` table.
- **Inputs:** `release_id` (path), optional filters `room_use_id`, `regulation`,
  `standard_version` (query).
- **Outputs:** `200` → list of `{room_use_id, regulation, standard_version, hours, unit,
  provenance}`.
- **Raises:** HTTP `404` `DatasetNotFoundError`; `422` invalid filter values.
- **Example:**
  ```console
  $ curl "http://127.0.0.1:8000/datasets/V221/full-load-hours?standard_version=prSIA%202024-C1:2024"
  ```

### 3.13 `GET /datasets/{release_id}/qhc`

- **Purpose:** Qhc matrix rows (use × station × kind).
- **Inputs:** `release_id` (path), optional filters `room_use_id`, `station_id`, `value_kind`
  (query).
- **Outputs:** `200` → list of `{room_use_id, station_id, kind, qhc: {value, unit}}`.
- **Raises:** HTTP `404` `DatasetNotFoundError`.
- **Example:** `curl "http://127.0.0.1:8000/datasets/V221/qhc?station_id=40"`

### 3.14 `GET /datasets/{release_id}/exports.{fmt}`

- **Purpose:** Bulk export of the release (assessment §6.1).
- **Inputs:** `release_id` (path), `fmt` (path: `json | csv | xlsx | pdf`), `scope: str =
  "all"` (query), `language: str = "de"` (query).
- **Outputs:** `200` → file response (`Content-Disposition: attachment`); for `pdf` one file
  (`merged=true`) or a zip.
- **Raises:** HTTP `404` `DatasetNotFoundError`; `400` `ExportError` (unsupported
  format/scope).
- **Example:** `curl -o V221.xlsx http://127.0.0.1:8000/datasets/V221/exports.xlsx`

### 3.15 `POST /datasets/{release_id}/validate`

- **Purpose:** Validation report of the release (schema + value rules).
- **Inputs:** `release_id` (path).
- **Outputs:** `200` → `{"release_id", "valid", "errors": [...], "warnings": [...]}`.
- **Raises:** HTTP `404` `DatasetNotFoundError`.
- **Example:**
  ```console
  $ curl -X POST http://127.0.0.1:8000/datasets/V221/validate
  {"release_id": "V221", "valid": true, "errors": [], "warnings": ["code 12.1 normalized to 12.10"]}
  ```

## 4. Calculations router

`calculations_router: APIRouter` (prefix `/calculations`, tags `["calculations"]`) — delegates
to `CalculationEngine`; request/response per assessment §6.2.

### 4.1 `POST /calculations/validate`

- **Purpose:** Validate a building input without calculating.
- **Inputs (body):** `CalculateRequest` (datasetRelease, modelRelease, project{…}, rooms[…],
  ventilation[…], generation[…], climateStation, valueKind).
- **Outputs:** `200` → `{"valid": bool, "errors": [...], "warnings": [...]}`.
- **Raises:** HTTP `404` `DatasetNotFoundError` (unknown release/model);
  `422` schema/domain validation errors of the request body itself.
- **Example:**
  ```console
  $ curl -X POST http://127.0.0.1:8000/calculations/validate -H "Content-Type: application/json" \
      -d '{"datasetRelease": "V221", "modelRelease": "1.0.0", "project": {"name": "Beispiel",
           "climateStationId": 40, "valueKind": "standard", "rooms": [{"name": "Büro 1",
           "roomUseId": "1.01", "ebf": true, "ngf": 1200.0}]}}'
  ```

### 4.2 `POST /calculations`

- **Purpose:** Run a calculation (assessment §6.2 `calculate_building`).
- **Inputs (body):** `CalculateRequest` as in 4.1.
- **Outputs:** `201` → `CalculateResponse` (resultId, versions, inputsHash, assumptions,
  warnings, overriddenValues, results{perRoom, perSystem, perEnergietraeger, totals},
  intermediates{ahuBins, fullLoadHours, qhc}, units).
- **Raises:** HTTP `404` dataset/model; `409` `ModelVersionMismatchError`;
  `422` `CalculationInputError` (hard validation errors); `500` `CalculationError` /
  `BackendError` (with `details`).
- **Example:**
  ```console
  $ curl -X POST http://127.0.0.1:8000/calculations -H "Content-Type: application/json" \
      -d @building.json
  {"resultId": "9f2c…", "versions": {"dataset": "V221", "model": "1.0.0", …}, …}
  ```

### 4.3 `GET /calculations/{result_id}`

- **Purpose:** Retrieve a stored calculation (reproducibility).
- **Inputs:** `result_id` (path).
- **Outputs:** `200` → `CalculateResponse`.
- **Raises:** HTTP `404` unknown `result_id` (`CalculationError` mapped).
- **Example:** `curl http://127.0.0.1:8000/calculations/9f2c…`

### 4.4 `GET /calculations/{result_id}/explain`

- **Purpose:** Explain a stored calculation (trace steps, formulas, data sources —
  assessment §6.2 `explain_calculation_result`).
- **Inputs:** `result_id` (path).
- **Outputs:** `200` → `ExplainResponse` (steps with id, kind, label, inputs, formula,
  outputs, provenance).
- **Raises:** HTTP `404` unknown `result_id`.
- **Example:** `curl http://127.0.0.1:8000/calculations/9f2c…/explain`

## 5. Versions router

### 5.1 `GET /versions`

- **Purpose:** Publication/dataset/model/implementation/climate versions (assessment §6.2).
- **Inputs:** —.
- **Outputs:** `200` → `VersionsOut` (`{"dataset": …, "model": …, "implementation": …,
  "climate": …, "releases": […]}`).
- **Raises:** HTTP —.
- **Example:**
  ```console
  $ curl http://127.0.0.1:8000/versions
  {"dataset": "V221", "model": "1.0.0", "implementation": "0.1.0",
   "climate": "meteoschweiz-2024", "releases": [{"id": "V221", …}]}
  ```

## 6. Schemas

Pydantic models (all JSON-Schema-exportable via `model_json_schema()`); fields mirror the
domain objects of parts 03–04. Every schema is a **class** with the usual pydantic behaviour.

| Schema | Purpose | Key fields | Raises |
|---|---|---|---|
| `DatasetReleaseOut` | Release metadata | id, edition, publication_date, checksum_sha256, supersedes, changelog | `ValidationError` |
| `RoomUseOut` | Room use | nutzid, code, category, name{de,fr,it} | `ValidationError` |
| `ParameterOut` | Parameter | id, label, symbol, unit, data_type, category, flags | `ValidationError` |
| `RoomUseProfileOut` | Data sheet | room_use, parameters[{id, label, symbol, unit, values{kind: {value, unit, provenance}}}] | `ValidationError` |
| `ClimateStationOut` | Station | id, name, winter_design, summer_design, monthly, bins, hdd | `ValidationError` |
| `ProfileOut` | Profiles | id, profile_type, values, unit | `ValidationError` |
| `CompareOut` | Profile diff | a_id, b_id, identical, changed[], added[], removed[] | `ValidationError` |
| `ValidationReportOut` | Report | valid, errors[], warnings[] | `ValidationError` |
| `CalculateRequest` | Calculation input | datasetRelease, modelRelease, project, rooms[], ventilation[], generation[], climateStationId, valueKind | `ValidationError` |
| `CalculateResponse` | Calculation output | resultId, versions, inputsHash, assumptions, warnings, overriddenValues, results, intermediates, units | `ValidationError` |
| `ExplainResponse` | Trace | resultId, steps[{id, kind, label, inputs, formula, outputs, provenance}] | `ValidationError` |
| `VersionsOut` | Versions | dataset, model, implementation, climate, releases[] | `ValidationError` |
| `ErrorOut` | Error body | detail, details | `ValidationError` |

- **Purpose:** Typed request/response contracts; generated OpenAPI/JSON Schema is the public
  contract of the API (assessment §6).
- **Inputs:** constructor keyword arguments per field; unknown fields rejected.
- **Outputs:** validated pydantic instances; `.model_dump_json()` for responses.
- **Raises:** `pydantic.ValidationError` (→ HTTP 422 by FastAPI).
- **Example:**
  ```python
  from energytools.api.schemas import CalculateRequest
  req = CalculateRequest.model_validate(payload)
  ```

## 7. Dependencies

| Symbol | Kind | Purpose |
|---|---|---|
| `get_service(request) -> RaumdatenService` | FastAPI dependency | Yields the app-wide `RaumdatenService` (from `app.state`). |
| `get_engine(request) -> CalculationEngine` | FastAPI dependency | Yields the app-wide `CalculationEngine`. |
| `get_store(request) -> CalculationStore` | FastAPI dependency | Yields the app-wide `CalculationStore`. |

- **Purpose:** Single wiring point so routers never construct services; enables test
  overrides (`app.dependency_overrides`).
- **Inputs:** `request: Request`.
- **Outputs:** the singleton instances.
- **Raises:** —.
- **Example:**
  ```python
  app.dependency_overrides[get_service] = lambda: test_service
  ```
