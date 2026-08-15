# Part 07 — API Reference: MCP Layer (`energytools.mcp`)

**Document set 02** · Target-state design specification · Back to [index](README.md) ·
Inventory: [01-package-inventory.md](01-package-inventory.md) · Data:
[03-raumdaten-service.md](03-raumdaten-service.md) · Engine:
[04-gebaeude-engine.md](04-gebaeude-engine.md) · HTTP API:
[06-fastapi-layer.md](06-fastapi-layer.md)

The MCP adapter (assessment §7.7: "thin MCP server exposing only the stable API operations …
no cell access, no memorized values"). It is a **client of the same service/engine objects** the
FastAPI layer uses — the tools below mirror the API operations 1:1 and return structured JSON.
Every tool input/output is validated through the same schemas.

---

## 1. `create_mcp_server`

`def create_mcp_server(service: RaumdatenService | None = None, engine: CalculationEngine |
None = None) -> FastMCP`

- **Purpose:** Builds the MCP server: registers all tools from `TOOL_REGISTRY` with their JSON
  Schema input contracts and returns the `FastMCP` instance (stdio transport by default; SSE
  when configured).
- **Inputs:** `service` (default: from `Settings`), `engine` (default: from `Settings`).
- **Outputs:** configured `FastMCP` server instance.
- **Raises:** —.
- **Example:**
  ```python
  from energytools.mcp.server import create_mcp_server
  mcp = create_mcp_server()
  # run via the MCP CLI/stdio or mcp.run()
  ```

## 2. `run_mcp_server`

`def run_mcp_server(service: RaumdatenService | None = None, engine: CalculationEngine | None
= None, host: str = "127.0.0.1", port: int = 8001) -> None`

- **Purpose:** Runs the MCP server as a standalone process (used by the CLI `energytools mcp`
  and deployment scripts): SSE transport on `host:port` with a health endpoint.
- **Inputs:** `service`, `engine`, `host`, `port`.
- **Outputs:** blocks until terminated.
- **Raises:** `OSError` on port conflicts.
- **Example:**
  ```console
  $ energytools mcp --host 127.0.0.1 --port 8001
  ```

## 3. `TOOL_REGISTRY`

`TOOL_REGISTRY: dict[str, ToolSpec]`

- **Purpose:** Tool name → `ToolSpec(name, description, input_schema, handler)` map; the single
  registration point (tools are added here, `create_mcp_server` only registers).
- **Inputs:** —.
- **Outputs:** `dict` with the nine keys of §4.
- **Raises:** —.
- **Example:**
  ```python
  from energytools.mcp.tools import TOOL_REGISTRY
  assert set(TOOL_REGISTRY) == {"list_room_uses", "get_room_use_profile",
      "compare_room_use_profiles", "list_climate_stations", "get_versions",
      "validate_building_input", "calculate_building", "explain_calculation_result",
      "export_dataset"}
  ```

## 4. MCP tools

All tools return structured JSON (dicts), never markdown tables; errors are returned as
structured error objects `{"error": {"code": …, "message": …, "details": {…}}}` (never raised
across the MCP boundary). Tool names follow the assessment §7.7 operations.

### 4.1 `list_room_uses`

`list_room_uses(release_id: str, language: str = "de") -> dict`

- **Purpose:** The 45 room uses with id, code, category and localized name.
- **Inputs:** `release_id` (e.g. `"V221"`), `language` (`de|fr|it`).
- **Outputs:** `{"release_id": …, "room_uses": [{nutzid, code, category, name}, …]}`.
- **Raises:** error object `dataset_not_found`, `unknown_language`.
- **Example:**
  ```json
  {"tool": "list_room_uses", "input": {"release_id": "V221", "language": "fr"},
   "result": {"release_id": "V221", "room_uses": [{"nutzid": 1, "code": "1.01",
   "category": 1, "name": "Habitation CMI"}]}}
  ```

### 4.2 `get_room_use_profile`

`get_room_use_profile(release_id: str, room_use_id: str | int, value_kind: str | None = None)
-> dict`

- **Purpose:** Full data sheet of one room use (all or one value kind).
- **Inputs:** `release_id`, `room_use_id` (nutzid or SIA code), `value_kind` (`standard |
  zielwert | bestand`, optional).
- **Outputs:** `{"room_use": …, "parameters": [{id, label, symbol, unit, values{…}}]}`.
- **Raises:** error object `dataset_not_found`, `unknown_room_use`, `unknown_value_kind`.
- **Example:**
  ```json
  {"tool": "get_room_use_profile",
   "input": {"release_id": "V221", "room_use_id": 1, "value_kind": "zielwert"}}
  ```

### 4.3 `compare_room_use_profiles`

`compare_room_use_profiles(release_id: str, a: str | int, b: str | int) -> dict`

- **Purpose:** Diff two room-use profiles.
- **Inputs:** `release_id`, `a`, `b`.
- **Outputs:** `{"a": …, "b": …, "identical": bool, "changed": […], "added": […],
  "removed": […]}`.
- **Raises:** error object `dataset_not_found`, `unknown_room_use`.
- **Example:** `{"tool": "compare_room_use_profiles", "input": {"release_id": "V221",
  "a": "1.01", "b": "1.02"}}`

### 4.4 `list_climate_stations`

`list_climate_stations(release_id: str, language: str = "de") -> dict`

- **Purpose:** The 40 climate stations.
- **Inputs:** `release_id`, `language`.
- **Outputs:** `{"release_id": …, "stations": [{id, name}, …]}`.
- **Raises:** error object `dataset_not_found`, `unknown_language`.
- **Example:** `{"tool": "list_climate_stations", "input": {"release_id": "V221"}}`

### 4.5 `get_versions`

`get_versions() -> dict`

- **Purpose:** Publication/dataset/model/implementation/climate versions.
- **Inputs:** —.
- **Outputs:** `{"dataset": …, "model": …, "implementation": …, "climate": …,
  "releases": […]}`.
- **Raises:** error object —.
- **Example:** `{"tool": "get_versions", "input": {}, "result": {"dataset": "V221", …}}`

### 4.6 `validate_building_input`

`validate_building_input(input: dict) -> dict`

- **Purpose:** Validate a building input without calculating (schema + domain rules).
- **Inputs:** `input` — the `CalculateRequest`-shaped payload
  (`datasetRelease`, `modelRelease`, `project`, `rooms`, `ventilation`, `generation`,
  `climateStationId`, `valueKind`).
- **Outputs:** `{"valid": bool, "errors": [...], "warnings": [...]}`.
- **Raises:** error object `dataset_not_found`, `validation_error` (malformed payload).
- **Example:** `{"tool": "validate_building_input", "input": {"input": {"datasetRelease":
  "V221", "modelRelease": "1.0.0", "project": {"name": "Beispiel",
  "climateStationId": 40, "valueKind": "standard", "rooms": […]}}}}`

### 4.7 `calculate_building`

`calculate_building(input: dict) -> dict`

- **Purpose:** Run a calculation (assessment §7.7 `calculate_building`).
- **Inputs:** `input` — `CalculateRequest`-shaped payload (as 4.6).
- **Outputs:** `CalculateResponse` (resultId, versions, inputsHash, assumptions, warnings,
  overriddenValues, results, intermediates, units).
- **Raises:** error object `dataset_not_found`, `model_version_mismatch`,
  `calculation_input_error`, `calculation_error`, `backend_error`.
- **Example:** `{"tool": "calculate_building", "input": {"input": {…building.json…}}}`

### 4.8 `explain_calculation_result`

`explain_calculation_result(result_id: str) -> dict`

- **Purpose:** Explain a stored calculation (trace steps).
- **Inputs:** `result_id` (from `calculate_building`).
- **Outputs:** `{"result_id": …, "steps": [{id, kind, label, inputs, formula, outputs,
  provenance}]}`.
- **Raises:** error object `calculation_error` (unknown result id).
- **Example:** `{"tool": "explain_calculation_result", "input": {"result_id": "9f2c…"}}`

### 4.9 `export_dataset`

`export_dataset(release_id: str, fmt: str, scope: str = "all", language: str = "de") -> dict`

- **Purpose:** Export a dataset release; returns the artifact as base64 plus metadata (or a
  target path when the server runs with a writable export directory).
- **Inputs:** `release_id`, `fmt` (`json|csv|xlsx|pdf`), `scope`, `language`.
- **Outputs:** `{"release_id": …, "format": …, "scope": …, "bytes_b64": …, "checksum_sha256":
  …, "versions": …}`.
- **Raises:** error object `dataset_not_found`, `export_error`.
- **Example:** `{"tool": "export_dataset", "input": {"release_id": "V221", "fmt": "xlsx",
  "scope": "qhc"}}`

---

## 5. Invariants (assessment §7.7)

* Tools operate **only** on the stable service/engine operations — no cell access, no workbook
  paths, no memorized dataset values.
* Every tool result embeds `release_id`/`result_id` and versions where applicable; LLM clients
  never need to guess versions.
* Errors are structured (`code`/`message`/`details`), mapped 1:1 from the domain exceptions of
  part 02, so clients can branch on `code`.
* `calculate_building` and `validate_building_input` share the exact payload schema of
  `POST /calculations` (part 06 §4), keeping the MCP and HTTP surfaces consistent.
