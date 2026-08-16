# API Reference — Overview

**Doc set 02 (API Reference)** · The user-facing API reference of the `energytools` library:
what to import, which classes and functions exist, and minimal runnable examples — in the
style of [compas.dev](https://compas.dev/compas/latest/api/index.html).

This library reimplements the two SIA 2024 Excel tools
(`2024_Raumdatenblätter_dfi_V221.xlsm`, `2024_Gebaeude-Tool_dfi_V221.xlsm`) as a layered
Python package. You use it in three steps: **load the dataset** (part
[03](03-raumdaten-service.md)), **run a calculation** (part [04](04-gebaeude-engine.md)), and
read **versions / exports** (part [05](05-versioning-export.md)); the shared foundation
(units, languages, value kinds, errors) is part [02](02-common-foundation.md).

---

## Module navigation

| Part | Module | Content | User-facing core |
|---|---|---|---|
| [02](02-common-foundation.md) | `energytools.common` | Errors, versioning, units, language, value kinds, provenance, validation | `get_version`, `VersionResolver`, `Quantity`, `Unit`, `TrilingualText`, `ValueKind`, exceptions |
| [03](03-raumdaten-service.md) | `energytools.raumdaten` | Canonical dataset: loading, queries, compare | `load_dataset`, `Dataset`, `RaumdatenService`, `RoomUse`, `RoomUseProfile` |
| [04](04-gebaeude-engine.md) | `energytools.engine` | Calculation engine: input model, engine, results, native physics | `Engine`, `BuildingInput`, `RoomRow`, `VentilationSystem`, `Results` |
| [05](05-versioning-export.md) | `energytools` (root) + export | Release lifecycle, CLI, export | `get_version`, `energytools --version`, `RaumdatenService.export` (JSON) |
| [06](06-fastapi-layer.md) | `energytools.api` *(planned)* | FastAPI HTTP layer | — |
| [07](07-mcp-layer.md) | `energytools.mcp` *(planned)* | MCP server/tools | — |

---

## Symbol statistics (public API surface)

Counted from the `__all__` exports of the implemented packages (`energytools` 0.1.0).

| Package | ✅ User-facing | ⚙ Internal/advanced | Total exported |
|---|---|---|---|
| `energytools` (root) | 2 (`__version__`, `get_version`) | — | 2 |
| `energytools.common` | 28 (errors 17, versioning 5, units 2, language 2, valuekind 1, validation 1) | 3 (`register_unit`, `SourceRef`, `Provenance`) | 31 |
| `energytools.raumdaten` | 22 (model classes, `Dataset`, `RaumdatenService`, `load_dataset`, `compare_profiles`, diff classes) | 2 (`DatasetExtractor`, `DatasetStore`) | 24 |
| `energytools.engine` | 21 (engine + input/result model + enums + `DEFAULT_MODEL` + errors¹) | 4 (`EngineBase`, `StubBackend`, `CalculationStore`, `TraceStep`) | 25 |
| `energytools.engine.native` | — (advanced) | 40 (psychrometrics, ahu, aggregation) | 40 |
| `energytools.dataset` | — (deprecated) | 29 (first-wave alias, emits `DeprecationWarning`) | 29 |

¹ Engine errors are user-facing for `try/except` but form the engine's **own** hierarchy —
see the deviation list below.

<a id="4-symbol-entry-template"></a>
## How to read the parts

Every part follows the same structure (compas-style):

1. **Quickstart** — install + a minimal runnable example (3–10 lines) with expected output.
2. **Classes** — each class with signature, one-sentence purpose, a **methods table**
   (signature → return → one-liner) and a 1-line example. User-facing classes come first.
3. **Functions** — standalone functions with signature + example.
4. **Internal/advanced** — ⚙ symbols (extraction, store, schema, low-level physics).
5. **What to import for a new project** — exact import blocks for the typical use case.

Markers: ✅ = user-facing (use freely); ⚙ = internal/advanced (skip unless you need it).

---

## Doc–code deviation list

Verified against the implemented code (`energytools` 0.1.0, `pixi run -e dev`). Items where
the documentation had to describe reality rather than the earlier design spec:

1. **`energytools.gebaeude` does not exist.** The calculation engine is implemented as
   `energytools.engine` (input model, `Engine`, `Results`, `engine.native.*`). Part
   [04](04-gebaeude-engine.md) documents the implemented names.
2. **`energytools.export`, `energytools.api`, `energytools.mcp` are not implemented.**
   Parts [05 § Export](05-versioning-export.md#export), [06](06-fastapi-layer.md) and
   [07](07-mcp-layer.md) mark them **planned**. What works today: JSON export via
   `RaumdatenService.export`, and the CLI `--version` only.
3. **`get_version()` reports empty dataset/model axes in a source checkout.** The root
   resolver reads flat `*.json` release manifests from `data/datasets/` and `data/models/`,
   but the shipped canonical package lives in `data/datasets/V221/package.json`
   (subdirectory). `RaumdatenService` scans `*/package.json` and resolves the same releases
   correctly — prefer it for data access (see
   [02 § Quickstart](02-common-foundation.md#quickstart)).
4. **Engine exceptions are a separate hierarchy.** `energytools.engine.errors` defines its
   own `EnergyToolsError` base and subclasses; they are **not** subclasses of
   `energytools.common.errors.EnergyToolsError`. Catch engine errors from
   `energytools.engine.errors`, library-wide errors from `energytools.common.errors`
   (see [04 § Classes](04-gebaeude-engine.md#engine--calculationengine) and the deviation
   note there).
5. **`compute_package_checksum` lives in the deprecated `energytools.dataset` package**, not
   in `energytools.raumdaten` (see [03 § Internal/advanced](03-raumdaten-service.md#computepackagechecksum--internal--moved-to-the-deprecated-energytoolsdataset)).
6. **`Dataset.to_json` / `to_csv` do not exist.** The `Dataset` serialization API is
   `to_package_dict()` / `from_package_dict()`; JSON export goes through
   `RaumdatenService.export(fmt="json", ...)` (see [03 § Classes](03-raumdaten-service.md#dataset--user-facing)).
7. **`example_building()` does not exist.** Part [04](04-gebaeude-engine.md) documents the
   canonical minimal example inline; the tests use the same shape via `tests/helpers.py`.
8. **`psychrometrics` unit conventions.** Relative humidity is a **decimal fraction 0–1** for
   every function except `wet_bulb_temperature` (percent 0–100, VBA-verbatim) — a deliberate
   deviation from the earlier design spec (see [04 § Native](04-gebaeude-engine.md#psychrometrics--moist-air-functions-advanced)).
9. **Part [01](01-package-inventory.md) is a target-state inventory** written against the
   pre-refactor names (`energytools.gebaeude`, `energytools.export`, …). It is kept as
   historical/reference documentation; the implemented symbols are the ones documented in
   parts 02–05 and verified by the tests.

---

## Quick links

- **Start here:** [03 — Raumdaten Data Service](03-raumdaten-service.md) (load data) →
  [04 — Calculation Engine](04-gebaeude-engine.md) (calculate) → [02 — Common
  Foundation](02-common-foundation.md) (units/languages/errors).
- **Versions & CLI:** [05](05-versioning-export.md).
- **Service layers (planned):** [06 FastAPI](06-fastapi-layer.md), [07 MCP](07-mcp-layer.md).
- **Completeness verification** against the docs inventory: [08](08-completeness-check.md).
