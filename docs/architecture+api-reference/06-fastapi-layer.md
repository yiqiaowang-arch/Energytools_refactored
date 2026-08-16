# API Reference — FastAPI Service Layer

**Module:** `energytools.api` (planned) · **Doc set 02 (API Reference)** · Back to
[index](README.md) · Data: [03-raumdaten-service.md](03-raumdaten-service.md) · Engine:
[04-gebaeude-engine.md](04-gebaeude-engine.md) · MCP: [07-mcp-layer.md](07-mcp-layer.md)

The HTTP API exposes the same `RaumdatenService` / `Engine` operations as REST endpoints
(OpenAPI 3 + JSON Schema). The layer is **thin**: endpoints delegate to the service/engine
facades, all domain exceptions map to HTTP errors via one exception handler, and **no cell
addresses** cross the boundary (assessment §5.3 rule 1).

> ⚙ **Status: planned.** `energytools.api` is **not yet implemented** in this milestone — there
> is nothing to import or run yet. The endpoint contract below is the design the FastAPI
> layer will implement; the underlying operations are already available in Python
> (parts [03](03-raumdaten-service.md) / [04](04-gebaeude-engine.md)).

---

## In this page

- [How to run the service (planned)](#how-to-run-the-service-planned)
- [Endpoint reference](#endpoint-reference)
- [What to import for a new project](#what-to-import-for-a-new-project)

---

<a id="1-settings"></a>
<a id="2-create_app"></a>
## How to run the service (planned)

Once implemented, the service runs as a standard FastAPI app (the `api` extra provides
fastapi/uvicorn):

```bash
pip install "energytools[api]"
```

```python
# energytools.api.app:create_app --factory   (planned)
from energytools.api.app import create_app

app = create_app()                    # builds service/engine/store from settings
```

```console
# planned
$ uvicorn energytools.api.app:create_app --factory --port 8000
$ curl http://127.0.0.1:8000/openapi.json   # OpenAPI schema
$ curl http://127.0.0.1:8000/docs           # Swagger UI
```

Runtime settings (environment `ENERGYTOOLS_*` / `.env`): `dataset_dir` (`"data/datasets"`),
`model_dir`, `backend` (`"native"`/`"excel"`), `excel_workbook`, `result_store_dir`,
`max_rooms`, `max_ventilation_systems`, `cors_origins`, `docs_enabled`, `api_prefix`.

---

## Endpoint reference

All endpoints delegate to the Python API documented in parts [03](03-raumdaten-service.md) /
[04](04-gebaeude-engine.md); error responses follow `{"detail": …, "details": {…}}` and
`release_id` path params accept the `latest` alias.

<a id="3-datasets-router"></a>
### Datasets router — `GET /datasets`

| Method & path | Delegates to | Output | Errors |
|---|---|---|---|
| `GET /datasets` | `list_releases` | release list, newest first | — |
| `GET /datasets/{release_id}` | `get_release` | release metadata + changelog | 404 |
| `GET /datasets/{release_id}/room-uses` | `list_room_uses` | localized room uses | 404, 422 |
| `GET /datasets/{release_id}/room-uses/{room_use_id}` | `get_room_use` | one room use | 404 |
| `GET /datasets/{release_id}/room-uses/{room_use_id}/profile` | `get_room_use_profile` | full data sheet | 404, 422 |
| `GET /datasets/{release_id}/room-uses/{a}/compare/{b}` | `compare_room_use_profiles` | profile diff | 404 |
| `GET /datasets/{release_id}/parameters` | `list_parameters` | parameter catalog | 404, 422 |
| `GET /datasets/{release_id}/parameters/{parameter_id}` | `get_parameter` | one parameter | 404 |
| `GET /datasets/{release_id}/climate-stations` | `list_climate_stations` | station list | 404 |
| `GET /datasets/{release_id}/climate-stations/{station_id}` | `get_climate_station` | full station | 404 |
| `GET /datasets/{release_id}/profiles` | `list_profiles` | hourly/monthly/weekly | 404 |
| `GET /datasets/{release_id}/full-load-hours` | `get_full_load_hours` (filters) | full-load-hours rows | 404, 422 |
| `GET /datasets/{release_id}/qhc` | `get_qhc` (filters) | Qhc matrix rows | 404 |
| `GET /datasets/{release_id}/exports.{fmt}` | `export` | file download (json today) | 404, 400 |
| `POST /datasets/{release_id}/validate` | `validate` | `{release_id, valid, errors, warnings}` | 404 |

Example:

```console
$ curl http://127.0.0.1:8000/datasets/V221/room-uses
[{"nutzid": 1, "code": "1.01", "category": 1, "name": "Wohnen MFH"}, ...]
```

<a id="4-calculations-router"></a>
### Calculations router — `POST /calculations`

| Method & path | Delegates to | Output | Errors |
|---|---|---|---|
| `POST /calculations/validate` | `Engine.validate_input` | `{valid, errors, warnings}` | 404, 422 |
| `POST /calculations` | `Engine.calculate` | `CalculateResponse` (resultId, versions, results, trace) | 404, 409, 422, 500 |
| `GET /calculations/{result_id}` | `Engine.get_result` | stored `CalculateResponse` | 404 |
| `GET /calculations/{result_id}/explain` | `Engine.explain` | trace steps | 404 |

Request body (`CalculateRequest`): `datasetRelease`, `modelRelease`, `project{name,
climateStationId, valueKind, ...}`, `rooms[]`, `ventilation[]`, `generation[]`.

```console
$ curl -X POST http://127.0.0.1:8000/calculations -H "Content-Type: application/json" \
    -d @building.json
{"resultId": "9f2c…", "versions": {"dataset": "V221", "model": "1.0.0", …}, …}
```

<a id="5-versions-router"></a>
### Versions router — `GET /versions`

| Method & path | Delegates to | Output | Errors |
|---|---|---|---|
| `GET /versions` | `VersionResolver.current` + releases | `{dataset, model, implementation, climate, releases}` | — |

```console
$ curl http://127.0.0.1:8000/versions
{"dataset": "V221", "model": "1.0.0", "implementation": "0.1.0",
 "climate": "meteoschweiz-2024", "releases": [{"id": "V221", …}]}
```

<a id="6-schemas"></a>
### Schemas & dependencies (planned)

Pydantic schemas mirror the domain objects of parts [03](03-raumdaten-service.md) /
[04](04-gebaeude-engine.md) (`DatasetReleaseOut`, `RoomUseOut`, `ParameterOut`,
`RoomUseProfileOut`, `ClimateStationOut`, `CompareOut`, `ValidationReportOut`,
`CalculateRequest`, `CalculateResponse`, `ExplainResponse`, `VersionsOut`, `ErrorOut`).
FastAPI dependencies (`get_service`, `get_engine`, `get_store`) wire the app-wide singletons
and support test overrides.

---

## What to import for a new project

Nothing to import yet — the FastAPI layer is **planned**. Today you call the same operations
directly in Python:

```python
from energytools.raumdaten import RaumdatenService
from energytools.engine import Engine

svc = RaumdatenService()                     # what GET /datasets/... will delegate to
engine = Engine()                            # what POST /calculations will delegate to

profiles = svc.get_room_use_profile("V221", "1.01")
result = engine.calculate(building_input, "V221", "1.0.0")
```

When `energytools.api` lands, the endpoint contract above maps 1:1 to these methods.
