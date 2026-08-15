# Docs Inventory

Index of all documentation in this repository. Every planned or existing document is listed here;
the completeness of each document set is verified against this inventory (see
[architecture+api-reference/08-completeness-check.md](architecture+api-reference/08-completeness-check.md)).

Legend — Status: `done` (written, content complete), `draft` (written, not yet reviewed), `planned`
(agreed but not yet written), `stale` (written but outdated).

## Document set 01 — Grounded assessment (findings + proposals)

| # | Document | Status | Content |
|---|----------|--------|---------|
| 01 | [01-workbook-assessment.md](01-workbook-assessment.md) | done | Grounded architectural assessment of the two source workbooks (`2024_Raumdatenblätter_dfi_V221.xlsm`, `2024_Gebaeude-Tool_dfi_V221.xlsm`): sheet inventories, data model findings, automation inventory, dependency analysis, proposed component separation, initial API boundary, staged PoC plan, risks. |

## Document set 02 — OOP library architecture & API reference

Target-state specification of the refactored Python OOP library (`energytools`), grounded in
document 01 and the `.analysis/` artifacts (VBA source, per-sheet dumps, defined names).

| # | Document | Status | Content |
|---|----------|--------|---------|
| 02a | [architecture+api-reference/README.md](architecture+api-reference/README.md) | done | Index of the document set: scope, status, conventions, symbol-entry template, package layout, layer diagram, reading order. |
| 02b | [architecture+api-reference/01-package-inventory.md](architecture+api-reference/01-package-inventory.md) | done | Full package/module inventory with per-module symbol tables (symbol, kind, one-line purpose, reference to the API entry), plus the VBA → Python symbol mapping. |
| 02c | [architecture+api-reference/02-common-foundation.md](architecture+api-reference/02-common-foundation.md) | done | API reference of `energytools.common`: exception hierarchy, versioning primitives, units, language, value kinds, provenance. |
| 02d | [architecture+api-reference/03-raumdaten-service.md](architecture+api-reference/03-raumdaten-service.md) | done | API reference of `energytools.raumdaten`: canonical dataset model, dataset loading, `RaumdatenService` query API, profile comparison. |
| 02e | [architecture+api-reference/04-gebaeude-engine.md](architecture+api-reference/04-gebaeude-engine.md) | done | API reference of `energytools.gebaeude`: building model, psychrometric physics, AHU bin engine, calculation engine, Excel (reference) and native backends, resultate aggregation. |
| 02f | [architecture+api-reference/05-versioning-export.md](architecture+api-reference/05-versioning-export.md) | done | API reference of version resolution/release management (`VersionResolver`), the `energytools.export` layer (JSON/CSV/XLSX/PDF) and the `energytools.cli` entry points. |
| 02g | [architecture+api-reference/06-fastapi-layer.md](architecture+api-reference/06-fastapi-layer.md) | done | API reference of the FastAPI layer: `create_app`, routers, endpoints (purpose, request, response, HTTP exceptions, examples), schemas, settings. |
| 02h | [architecture+api-reference/07-mcp-layer.md](architecture+api-reference/07-mcp-layer.md) | done | API reference of the MCP layer: server factory, tool registry, each tool with purpose, inputs, outputs, exceptions, examples. |
| 02i | [architecture+api-reference/08-completeness-check.md](architecture+api-reference/08-completeness-check.md) | done | Completeness verification: required coverage areas × document map, inventory ↔ API-entry cross-check, VBA symbol coverage, open gaps and next actions. |

## Document set 03 — Calculation model (textbook style)

Textbook-style documentation of the calculation model extracted from `.analysis/` (formulas,
physics, sheet semantics) of `2024_Gebaeude-Tool_dfi_V221.xlsm`. Written in English with German
domain terms kept verbatim; the intro is [textbook/README.md](textbook/README.md).

| # | Document | Status | Content |
|---|----------|--------|---------|
| 03a | [textbook/README.md](textbook/README.md) | done | Intro: tool positioning, data sources, cell-reference conventions, calculation-flow overview, sheet inventory, unit system, known quirks (0.7), formula-entry format. |
| 03b | [textbook/ch01-湿空气物理-Glück多项式与UDF.md](textbook/ch01-湿空气物理-Glück多项式与UDF.md) | done | Chapter 1 — Moist-Air Physics: Glück saturation-pressure polynomials, the 8 UDFs (derivation, units, assumptions, validity, every call site). ↔ `gebaeude.physics` (part 04 §2). |
| 03c | [textbook/ch02-房间KPI派生.md](textbook/ch02-房间KPI派生.md) | done | Chapter 2 — Room KPI Derivation: `KZ_Raum_2024` matrix (`Res`), `Gebäude` room-row VLOOKUP chains, EBF/GF/area weighting, Allg. Gebäudetechnik. ↔ `raumdaten.model` / `RoomUseProfile`. |
| 03d | [textbook/ch03-通风全负荷小时.md](textbook/ch03-通风全负荷小时.md) | done | Chapter 3 — Ventilation Full-Load Hours: `Std` table (copy of Raumdaten `Volll_Lüft`), regulation-based selection, use in the AHU engine. ↔ `FullLoadHoursTable`. |
| 03e | [textbook/ch04-AHU温度区间法.md](textbook/ch04-AHU温度区间法.md) | done | Chapter 4 — AHU Temperature-Bin Method (`Berechnung LU`): climate bins, psychrometric chain, fan stages P∝V^2.5, WRG/KRG, Fall 1–4 control cases, energy aggregation, quirks (4.14). ↔ `gebaeude.ahu` (part 04 §3). |
| 03f | [textbook/ch05-产热与Resultate汇总.md](textbook/ch05-产热与Resultate汇总.md) | done | Chapter 5 — Heat Generation and Resultate Summary: `Nutzungsgrad` catalog, `Erzeugung` generator groups, Endenergie/Energieträger allocation, NEGF/PEne/THGE weighting (incl. two documented copy-paste errors). ↔ `gebaeude.model` / `ResultateAggregator`. |
| 03g | [textbook/ch06-气候数据.md](textbook/ch06-气候数据.md) | done | Chapter 6 — Climate Data: `Klimadaten` 40 stations, pressure altitude formula, HDD, design temperatures, bin hours/humidity, `Qhc_Klimastat`. ↔ `ClimateStation` / `ClimateData` / `QhcTable`. |
| 03h | [textbook/analysis_Berechnung_LU.md](textbook/analysis_Berechnung_LU.md) | done | Appendix A: column-by-column analysis draft of `Berechnung LU` (basis of ch04; incl. full numeric example of row 168). |

## Document set 04 — Installation & documentation pipeline

| # | Document | Status | Content |
|---|----------|--------|---------|
| 04a | [installation.md](installation.md) | done | Multi-toolchain install guide (pixi / uv / conda / pip) for the `energytools` package scaffold. |
| 04b | [deployment/readthedocs.md](deployment/readthedocs.md) | done | Documentation build pipeline: local MkDocs build/serve, ReadTheDocs integration (`requirements.txt`, `.readthedocs.yaml`), nav structure. |
| 04c | `mkdocs.yml` (repo root) | done | MkDocs + Material site configuration (nav covers sets 01–04). |

## Repository conventions

* All documents are Markdown (UTF-8). All document sets (01–04) are written in English;
  German/SIA domain terms are kept in their original form (e.g. `Nutzungsgrad`,
  `Volllaststunden`, `Endenergie`).
* Source artifacts referenced by documents live under `.analysis/` (extracted VBA, sheet dumps,
  defined names, unpacked OOXML) and `data/raw/` (the unmodified workbooks) in the main
  repository; the merged documentation tree does not copy them.
* Findings (observed) and proposals (target state) are kept separate; document set 02 is a
  **target-state design specification** and is explicitly labelled as such. Document set 03 is
  the authoritative description of the **current workbook behaviour** (observed).
* Build the site with `mkdocs serve` / `mkdocs build` (see
  [deployment/readthedocs.md](deployment/readthedocs.md)).
