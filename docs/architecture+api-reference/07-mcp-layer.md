# API Reference — MCP Service Layer

**Module:** `energytools.mcp` (planned) · **Doc set 02 (API Reference)** · Back to
[index](README.md) · Data: [03-raumdaten-service.md](03-raumdaten-service.md) · Engine:
[04-gebaeude-engine.md](04-gebaeude-engine.md) · HTTP API:
[06-fastapi-layer.md](06-fastapi-layer.md)

The MCP (Model Context Protocol) adapter exposes the same stable service/engine operations as
**tools** for LLM clients: "thin MCP server exposing only the stable API operations — no cell
access, no memorized values" (assessment §7.7). Tools mirror the API operations 1:1, return
structured JSON (never markdown tables), and report errors as structured objects
`{"error": {"code", "message", "details"}}` — never raised across the MCP boundary.

> ⚙ **Status: planned.** `energytools.mcp` is **not yet implemented** in this milestone —
> there is nothing to import or run yet. The tool contract below is the design; every
> underlying operation is already available in Python (parts [03](03-raumdaten-service.md) /
> [04](04-gebaeude-engine.md)).

---

## In this page

- [How to run the server (planned)](#how-to-run-the-server-planned)
- [Tool reference](#tool-reference)
- [What to import for a new project](#what-to-import-for-a-new-project)

---

<a id="1-create_mcp_server"></a>
<a id="2-run_mcp_server"></a>
<a id="3-tool_registry"></a>
## How to run the server (planned)

Once implemented, the server runs as a standalone MCP process (stdio by default, SSE when
configured):

```console
# planned
$ energytools mcp --host 127.0.0.1 --port 8001
```

```python
# planned
from energytools.mcp.server import create_mcp_server

mcp = create_mcp_server()          # registers all tools from TOOL_REGISTRY
```

`TOOL_REGISTRY` maps tool name → `ToolSpec(name, description, input_schema, handler)`; the
nine tools below. Tools operate **only** on the stable service/engine operations — no cell
access, no workbook paths, no memorized dataset values — and every result embeds
`release_id`/`result_id` and versions where applicable, so LLM clients never need to guess.

---

<a id="4-mcp-tools"></a>
## Tool reference

| Tool | Delegates to | Input | Output |
|---|---|---|---|
| `list_room_uses` | `RaumdatenService.list_room_uses` | `release_id`, `language="de"` | `{release_id, room_uses: [{nutzid, code, category, name}]}` |
| `get_room_use_profile` | `RaumdatenService.get_room_use_profile` | `release_id`, `room_use_id`, `value_kind=None` | `{room_use, parameters: [{id, label, symbol, unit, values}]}` |
| `compare_room_use_profiles` | `RaumdatenService.compare_room_use_profiles` | `release_id`, `a`, `b` | `{a, b, identical, changed[], added[], removed[]}` |
| `list_climate_stations` | `RaumdatenService.list_climate_stations` | `release_id`, `language="de"` | `{release_id, stations: [{id, name}]}` |
| `get_versions` | `VersionResolver.current` + releases | — | `{dataset, model, implementation, climate, releases}` |
| `validate_building_input` | `Engine.validate_input` | `CalculateRequest`-shaped payload | `{valid, errors, warnings}` |
| `calculate_building` | `Engine.calculate` | `CalculateRequest`-shaped payload | `CalculateResponse` (resultId, versions, results, …) |
| `explain_calculation_result` | `Engine.explain` | `result_id` | `{result_id, steps: [{id, kind, label, inputs, formula, outputs, provenance}]}` |
| `export_dataset` | `RaumdatenService.export` | `release_id`, `fmt`, `scope`, `language` | `{release_id, format, scope, checksum_sha256, …}` |

Example call shape (planned):

```json
{"tool": "compare_room_use_profiles",
 "input": {"release_id": "V221", "a": "1.01", "b": "1.02"},
 "result": {"a": 1, "b": 2, "identical": false,
            "changed": [{"parameter_id": "1.1.1.2", "label": "Thermische Gebäudehüllfläche",
                          "symbol": "Ath", "unit": "m2",
                          "diffs": {"standard": [26.47058823529412, 38.23529411764706]}}],
            "added": [], "removed": []}}
```

Error codes map 1:1 from the domain exceptions of part [02](02-common-foundation.md):
`dataset_not_found`, `unknown_room_use`, `unknown_language`, `unknown_value_kind`,
`model_version_mismatch`, `calculation_input_error`, `calculation_error`, `backend_error`,
`export_error`, `validation_error`.

---

## What to import for a new project

Nothing to import yet — the MCP layer is **planned**. Today you call the same operations
directly in Python:

```python
from energytools.raumdaten import RaumdatenService
from energytools.engine import Engine

svc = RaumdatenService()                     # what the data tools will delegate to
engine = Engine()                            # what the calculation tools will delegate to

svc.list_room_uses("V221")                   # → list_room_uses tool
engine.calculate(building_input, "V221", "1.0.0")   # → calculate_building tool
```

When `energytools.mcp` lands, the tool contract above maps 1:1 to these methods.
