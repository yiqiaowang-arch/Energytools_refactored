# OOP Library Architecture & API Reference — `energytools`

**Document set:** 02 of the [docs inventory](../README.md) · **Status:** target-state design
specification · **Grounded in:** [01-workbook-assessment.md](../01-workbook-assessment.md) and the
`.analysis/` artifacts (extracted VBA, per-sheet TSV dumps, defined names) · **Scope:** the
refactored Python OOP library that replaces the two SIA 2024 Excel tools
(`2024_Raumdatenblätter_dfi_V221.xlsm`, `2024_Gebaeude-Tool_dfi_V221.xlsm`).

> **What this is.** A complete architecture and API reference for the target library: the
> package/module/class/function inventory (part 01) and, for **every public symbol**, an API
> reference entry with **purpose, inputs, outputs, exceptions and a usage example** (parts 02–07).
> Part 08 verifies completeness against the docs inventory and the required coverage areas.
>
> **What this is not.** Implemented code or a changelog of the current state. The library does not
> exist in this repository yet; this specification is the blueprint the implementation (and the
> staged PoC plan of the assessment, §7) must follow. Where a symbol maps to observed Excel/VBA
> behaviour, the grounding is cited (e.g. `← VBA: AbsFeuchte`).

---

## 1. Reading order

| # | Part | Content |
|---|------|---------|
| 1 | [01-package-inventory.md](01-package-inventory.md) | Package tree, per-module symbol tables, VBA → Python mapping. Start here for orientation. |
| 2 | [02-common-foundation.md](02-common-foundation.md) | Cross-cutting foundation: errors, versioning, units, language, value kinds, provenance. |
| 3 | [03-raumdaten-service.md](03-raumdaten-service.md) | `energytools.raumdaten` — the Raumdaten data service (canonical dataset, queries, compare). |
| 4 | [04-gebaeude-engine.md](04-gebaeude-engine.md) | `energytools.gebaeude` — the Gebäude calculation engine (model, physics, AHU, engine, **Excel and native backends**, resultate). |
| 5 | [05-versioning-export.md](05-versioning-export.md) | Version resolution, release management, the export layer (JSON/CSV/XLSX/PDF) and the CLI. |
| 6 | [06-fastapi-layer.md](06-fastapi-layer.md) | FastAPI application, routers and endpoints, schemas, settings. |
| 7 | [07-mcp-layer.md](07-mcp-layer.md) | MCP server, tool registry and per-tool reference. |
| 8 | [08-completeness-check.md](08-completeness-check.md) | Completeness verification against the docs inventory and the required coverage areas. |

## 2. Architectural context

The target architecture follows the component separation proposed in the assessment (§5.3):
Excel stays an **authoring/reference format**, never an API; the canonical dataset package and a
declarative model definition are the single sources of truth; a deterministic calculation runtime
runs behind a stable domain API; an MCP adapter is a thin layer on top of that API.

```text
Excel source workbooks (authoring/reference)
        │  (extraction pipeline, on copies, checksummed)          ← DatasetExtractor
        ▼
[1] Raumdaten dataset package (versioned JSON + JSON Schema)       ← energytools.raumdaten.model / dataset
[2] Gebäude calculation model definition (versioned JSON)          ← energytools.gebaeude.model
        │
        ▼
[3] Versioned data service (read-only, semantic query API)         ← RaumdatenService
[4] Deterministic calculation runtime                              ← CalculationEngine
        │    initial runtime: Excel backend (reference impl.)      ← gebaeude.backends.excel.ExcelBackend
        │    later runtime:   native backend (ported, verified)    ← gebaeude.backends.native.NativeBackend
        ▼
[5] Stable domain API (OpenAPI 3 + JSON Schema)
        ├── FastAPI layer                                          ← energytools.api
        ├── CLI                                                     ← energytools.cli
        └── MCP adapter (thin, on top of [5] only)                 ← energytools.mcp
```

**Invariants (from assessment §5.3, binding for every symbol below):**

1. Excel cell/range addresses never cross the API boundary; the Excel backend keeps ranges internal.
2. The calculation model consumes Raumdaten **only** through `Dataset` objects (replacing the
   fragile external links and stale copies `KZ_Raum_2024`, `Qhc_Klimastat`, `Std`).
3. Every public result carries version information (dataset, model, implementation, climate) and
   provenance; nothing is "just a number".
4. The Gebaeude-Tool's local copies are replaced by service lookups; nothing refreshes copies.

## 3. Package layout (single source of truth)

```text
energytools/                        distribution root (pyproject: name = "energytools")
├── __init__.py                     __version__, get_version()
├── common/                         cross-cutting foundation
│   ├── errors.py                   EnergyToolsError hierarchy (all exceptions)
│   ├── versioning.py               DatasetRelease, ModelRelease, VersionInfo, ChangelogEntry, VersionResolver
│   ├── units.py                    Unit, Quantity
│   ├── language.py                 Language (DE/FR/IT), TrilingualText
│   ├── valuekind.py                ValueKind (Standard/Zielwert/Bestand)
│   └── provenance.py               SourceRef, Provenance
├── raumdaten/                      data service (dataset + queries)
│   ├── model.py                    RoomUse, Parameter, RoomUseProfile, ClimateStation, profiles, FullLoadHoursTable, QhcTable, Sia3801*, Dataset, …
│   ├── dataset.py                  load_dataset, DatasetStore, DatasetExtractor
│   ├── service.py                  RaumdatenService (semantic query API)
│   └── compare.py                  compare_profiles, ProfileDiff
├── gebaeude/                       calculation engine
│   ├── model.py                    BuildingProject, RoomRow, VentilationSystem, GenerationSystem, Resultate, catalogs, ValidationReport
│   ├── physics.py                  psychrometric functions (Glück polynomials) + constants
│   ├── ahu.py                      AhuInput, calculate_ahu, AhuResult, FanModel, HeatRecoveryModel
│   ├── engine.py                   CalculationEngine, CalculationResult, CalculationTrace, CalculationStore
│   ├── resultate.py                ResultateAggregator, weight_resultate
│   └── backends/
│       ├── base.py                 CalculationBackend (ABC)
│       ├── excel.py                ExcelBackend (reference runtime, Excel COM)
│       └── native.py               NativeBackend (ported, pure Python)
├── export/                         export layer
│   ├── base.py                     Exporter (ABC), registry helpers
│   ├── json_exporter.py            JsonExporter
│   ├── csv_exporter.py             CsvExporter
│   ├── xlsx_exporter.py            XlsxExporter
│   └── pdf_exporter.py             PdfExporter (data-sheet PDFs)
├── api/                            FastAPI layer
│   ├── app.py                      create_app
│   ├── settings.py                 Settings
│   ├── deps.py                     get_service, get_engine, get_store
│   ├── schemas.py                  Pydantic request/response models
│   └── routers/
│       ├── datasets.py             datasets_router (data service endpoints)
│       ├── calculations.py         calculations_router (calculation endpoints)
│       └── versions.py             versions_router (version endpoints)
├── mcp/                            MCP layer
│   ├── server.py                   create_mcp_server, run_mcp_server
│   └── tools.py                    tool implementations and registry
└── cli/
    └── main.py                     entry points: versions, export, serve, mcp
```

## 4. Symbol entry template

Every public symbol is documented in parts 02–07 using this template (compact form for small
symbols, full form for classes and complex functions):

```text
### `fully.qualified.symbol`
`signature`                            ← Python signature (params with types, return type)
- **Purpose:**  …
- **Inputs:**   … (parameters, types, constraints, defaults)
- **Outputs:**  … (return value(s), types, side effects)
- **Raises:**   … (exceptions and the conditions that trigger them; "—" if none)
- **Example:**  …
```

Class entries additionally list **Attributes** and **Methods**. Methods are documented compactly
within their class entry: signature (which states **inputs** and **outputs**), a purpose
sentence, and explicit **raises**; usage is demonstrated by the class-level example. The methods
of the service/engine facades (`RaumdatenService`, `CalculationEngine`) that mirror API
operations additionally receive full five-field nested entries. Enums/constants use a reduced
but complete form (purpose, members/values, example).

## 5. Naming and versioning conventions

* **Case/orthography:** German domain terms are kept verbatim as symbol suffixes where they are
  part of the domain vocabulary (`FullLoadHours`, `QhcTable`, `Sia3801Result`, `Resultate`), while
  Python identifiers use English. Sheet/table names referenced from the workbooks keep their exact
  spelling in comments and provenance (`tblVolll_Lüft`, `Berechnung LU`).
* **Release identifiers:** dataset releases use the workbook convention (`V221`), model releases
  are semantic (`1.0.0`), implementation versions follow PEP 440; climate data carries its own
  source version (see `VersionInfo`).
* **Value kinds:** `standard | zielwert | bestand` are mapped to `ValueKind.STANDARD | ZIELWERT |
  BESTAND` (assessment §1.2).
* **Languages:** `de | fr | it` map to `Language.DE | FR | IT`; `TrilingualText` is the carrier.

## 6. Scope decisions (explicitly out of scope)

* Excel **protection/licensing UI** (VBA `basLizenzieren`, `tblLizenzieren`, `Workmode`) — the
  digital service must not replicate the disabled license-gating logic (assessment §8.10); the
  protection helpers stay in the Excel authoring context and are **not ported** (mapped as
  `not ported` in part 01).
* Excel **print/PDF/export macros as UI** (`DatenblattSpeichern`, `DatenblattDruck`,
  `Blatthinzufügen`/`Entfernen`, `Sprachänderungen`) — replaced by the export layer and the
  language-aware model; the macros are mapped to their functional equivalents.
* Dead VBA (`EnthalpieR`, `Saettigungsdruck`, `Feuchtkugel`, `TaupunktR`, and the
  commented-out `TaupunktA` in Gebaeude) — mapped as `not ported (dead code, assessment §2.2)`
  or `reference-only`; only the functions actually referenced by stored formulas are normative
  ports (`AbsFeuchte`, `EnthalpieA`, `RelFeuchte`, `TemperaturH`; `TaupunktA` is referenced by
  `Berechnung LU!AQ` but commented out in the VBA module → `#NAME?`, and its column chain does
  not participate in results — textbook ch01 §1.7/§1.10). **`Fallunterscheidung` is *live*
  code** (referenced by `Berechnung LU!BB:BE`, 61×2 interval rows — textbook README §0.7-10 and
  ch04 §4.9; the early assessment misjudged it as dead): its case logic is ported as the
  Fall 1–4 selection inside `ahu.calculate_ahu` / `AhuBinResult.case`.
