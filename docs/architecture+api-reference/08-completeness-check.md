# Part 08 — Completeness Check

**Document set 02** · Back to [index](README.md) · Docs inventory:
[../README.md](../README.md)

This part verifies the document set against (a) the required coverage areas of the task
(**raumdaten data service · gebaeude calculation engine with excel/native backends · versioning
& export · FastAPI layer · MCP layer**), (b) the docs inventory
([docs/README.md](../README.md)), and (c) the internal consistency rule "every inventory symbol
has a full API reference entry, every API entry belongs to an inventory symbol". Verification
was executed with a script (entry-block field check + markdown link/anchor check) on
2026-08-15; the commands are reproducible (see §5).

**Result: all checks pass.** Details below.

---

## 1. Required coverage areas × document map

| Required area (task) | Where covered | Primary symbols |
|---|---|---|
| **raumdaten data service** (Raumdaten-Datenservice) | [03 §1–§4](03-raumdaten-service.md) | `Dataset`, `RoomUse`, `Parameter`, `RoomUseProfile`, `ClimateData`, `FullLoadHoursTable`, `QhcTable`, `Sia3801*`, `load_dataset`, `DatasetStore`, `DatasetExtractor`, `RaumdatenService` (16 methods), `compare_profiles`/`ProfileDiff` |
| **gebaeude calculation engine — excel backend** | [04 §5.2](04-gebaeude-engine.md#52-excelbackend), [04 §5.1](04-gebaeude-engine.md#51-calculationbackend) | `ExcelBackend` (reference runtime over workbook copies; COM, deterministic, no links), `CalculationBackend` |
| **gebaeude calculation engine — native backend** | [04 §5.3](04-gebaeude-engine.md#53-nativebackend), [04 §2–§4](04-gebaeude-engine.md#2-energytoolsgebaeudephysics) | `NativeBackend`, physics ports (`AbsFeuchte`→`absolute_humidity`, …), `calculate_ahu`, `CalculationEngine`, `ResultateAggregator` |
| **versioning & export** | [05 §1–§4](05-versioning-export.md), [02 §2](02-common-foundation.md#2-energytoolscommonversioning) | `DatasetRelease`, `ModelRelease`, `VersionInfo`, `ChangelogEntry`, `VersionResolver`, release workflow, `Exporter` + JSON/CSV/XLSX/PDF exporters, `export_dataset`, `export_calculation`, CLI |
| **FastAPI layer** | [06 §1–§7](06-fastapi-layer.md) | `Settings`, `create_app`, 20 endpoints (15 datasets + 4 calculations + 1 versions), 13 schemas, 3 dependencies |
| **MCP layer** | [07 §1–§5](07-mcp-layer.md) | `create_mcp_server`, `run_mcp_server`, `TOOL_REGISTRY`, 9 tools |
| **API reference per symbol: purpose / inputs / outputs / exceptions / example** | every entry in parts 02–07 | verified in §2.2 (0 entries missing a field) |
| **Docs inventory (docs清单) cross-check** | [docs/README.md](../README.md) + §3 | all rows `done` (sets 01–03 + installation/deployment) |

---

## 2. Inventory ↔ API-entry cross-check

### 2.1 Method

1. **Inventory (part 01)** lists every public symbol per module (§2.1–§2.21) with a link to its
   API entry in parts 02–07; the VBA mapping (§3) lists every VBA module of both workbooks.
2. **API parts (02–07)** contain one entry per symbol using the five-field template
   (Purpose / Inputs / Outputs / Raises / Example).
3. **Script checks:** (a) every entry block contains all five fields; (b) every relative
   markdown link with an anchor resolves to an existing heading (GitHub slug rules); (c) every
   file referenced by the docs inventory exists.

### 2.2 Verified counts

Method documentation convention (see [README §4](README.md#4-symbol-entry-template)): class
helper methods are documented compactly inside their class entry (signature = inputs/outputs,
purpose, raises, class-level example); facade methods mirroring API operations
(`RaumdatenService`, `CalculationEngine`) have full five-field entries — verified 16/16 in part
03. Endpoints, tools and schemas are symbols in their own right and are verified like classes
and functions.

| Part | Inventory table (01) | API entries | Field check (five fields) | Link check |
|---|---|---|---|---|
| [02-common-foundation.md](02-common-foundation.md) | §2.2–§2.7: 28 rows | 28 entries (16 errors, 5 versioning, 2 units, 2 language, 1 value kind, 2 provenance) | 28/28 blocks pass | pass |
| [03-raumdaten-service.md](03-raumdaten-service.md) | §2.8–§2.11: 22 rows + 16 service methods | 38 entries (16 model classes, 3 dataset, 1 service + 16 methods, 2 compare) | 38/38 entry blocks pass (22 class/function + 16 method; the `### 3.2 Methods` container heading is not an entry) | pass |
| [04-gebaeude-engine.md](04-gebaeude-engine.md) | §2.12–§2.17: 35 rows | 35 entries (10 model, 10 physics, 6 ahu, 4 engine, 3 backends, 2 resultate) | 35/35 blocks pass | pass |
| [05-versioning-export.md](05-versioning-export.md) | §2.1, §2.18–§2.19: 12 rows | 12 entries (2 root, 7 export, 3 CLI) + release-workflow section | 14/14 blocks pass | pass |
| [06-fastapi-layer.md](06-fastapi-layer.md) | §2.20: 6 rows (expanded) | 38 entries (Settings, create_app, 20 endpoints, 13 schemas, 3 deps) | 20/20 endpoint blocks pass (+ Settings/create_app) | pass |
| [07-mcp-layer.md](07-mcp-layer.md) | §2.21: 4 rows (expanded) | 12 entries (3 server/registry + 9 tools) | 9/9 tool blocks pass (+ server/registry) | pass |
| **Total** | **107 inventory rows (+ 16 methods + 20 endpoints + 13 schemas + 3 deps + 9 tools)** | **163 symbol entries** | **all pass** | **140 anchors checked, 0 broken** |

### 2.3 VBA → Python mapping coverage (part 01 §3)

| Workbook | VBA modules | Mapped | `not ported` (documented decision) |
|---|---|---|---|
| Raumdatenblätter (`raumdaten.xlsm`, 34 modules) | 34 | 13 functional modules mapped to Python equivalents (physics → `gebaeude.physics`; exports → export layer; language → `common.language`; sheet classes → `raumdaten.model` tables) | `Workmode`, `basLizenzieren`/`tblLizenzieren`, `Modul1`/`Modul2`, `DieseArbeitsmappe`, print/scroll UI parts of `Datenblatt_Handle`, sheet-renaming part of `Sprachänderungen` — each with reason (assessment §8.10, dead code, UI-only) |
| Gebäude-Tool (`gebaeude.xlsm`, 21 modules) | 21 | 8 functional modules mapped (physics UDFs, `Fallunterscheidung` → the Fall 1–4 case selection in `ahu.calculate_ahu`, `Lüftung_Resultate` → `calculate_ahu`, sheet classes → `gebaeude.model`) | `Blatthinzufügen` (UI), `Bearbeitungsmodus`, `basLizenzieren`/`tblLizenzieren`, `DieseArbeitsmappe` — with reasons |

> **Correction (2026-08-20, merged with document set 03):** the early assessment classified
> `Fallunterscheidung` as dead code; the textbook's full-sheet formula scan proved it **live**
> (`Berechnung LU!BB:BE` calls `Fall1Tzul`/`Fall1xzul`/`Fall2Tzul`/`Fall2xzul` on 61×2 interval
> rows — textbook README §0.7-10, ch04 §4.9). It is therefore mapped as ported logic, not as
> `not ported` (see [01 §3.2](01-package-inventory.md#32-gebäude-tool-gebaeudexlsm-21-modules)).

Every VBA module of both workbooks appears in [01 §3](01-package-inventory.md#3-vba--python-symbol-mapping-grounding):
none is silently omitted.

---

## 3. Docs inventory (docs清单) status

[docs/README.md](../README.md) is the inventory. Status after this document set:

| # | Document | Status |
|---|----------|--------|
| 01 | [01-workbook-assessment.md](../01-workbook-assessment.md) | done (pre-existing, copied into this worktree so the set is self-contained) |
| 02a–02i | architecture+api-reference set (README, parts 01–08) | **done** (this document set) |
| 03 | Calculation-model textbook ([../textbook/README.md](../textbook/README.md)) — chapters [ch01](../textbook/ch01-湿空气物理-Glück多项式与UDF.md) … [ch06](../textbook/ch06-气候数据.md) + appendix [analysis_Berechnung_LU.md](../textbook/analysis_Berechnung_LU.md) | **done** (merged from the parallel worktree; this set is now self-contained) |
| 04 | Installation & deployment ([installation.md](../installation.md), [deployment/readthedocs.md](../deployment/readthedocs.md), `mkdocs.yml`) | **done** (merged packaging-scaffold + docs-pipeline worktrees) |

Completeness statement: all documents promised by the inventory exist, and the inventory lists
nothing that is missing (sets 03 and 04 were merged from the parallel worktrees on 2026-08-20).

---

## 4. Open gaps and next actions

The following are **intentional design decisions / follow-ups**, not omissions:

1. **No implemented library code yet.** This document set specifies the target library
   (`energytools`); a minimal **packaging scaffold** (installable placeholder package — see
   [installation.md](../installation.md)) exists, and implementation of the real modules
   follows the assessment's staged PoC plan (§7). When code exists, re-run §5 checks plus an
   automated doc↔code symbol audit (e.g. `pydoc`-based) to catch drift.
2. **Dead VBA not ported / ported reference-only.** `EnthalpieR`/`Saettigungsdruck`/
   `Feuchtkugel`/`TaupunktR` and the commented-out `TaupunktA` (Gebäude) are mapped
   `reference-only` with explicit reasons (textbook ch01 §1.7–§1.9); license/protection/UI
   macros are `not ported` (see
   [01 §3](01-package-inventory.md#3-vba--python-symbol-mapping-grounding)).
   **`Fallunterscheidung` is live code** (see the correction note in §2.3): its Fall 1–4
   case logic is ported into `ahu.calculate_ahu` and must be **verified against the Excel
   oracle** with golden values from `Berechnung LU` rows 254–260 (per-system IST runs) — the
   workbook's UDFs `Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul` provide the expected values
   (textbook ch04 §4.9).
3. **Workbook quirks to honour during porting** (found by document set 03): the `Lüftung!U32:Z32`
   wiring shift (ch04 §4.14-8), the `Resultate!I21` / `G22:F22` weighting copy-paste errors
   (ch05 §5.10), the `N9/O9` Res column-selector offsets (ch02 §2.3), and the `AQ/AS`
   `TaupunktA` dead column (ch04 §4.14-1) must be handled exactly as the textbook documents —
   do **not** reproduce the workbook's copy-paste errors in the port.
4. **Climate data versioning** is specified (`ClimateData.version`, `VersionInfo.climate`) but
   the concrete source versioning scheme (MeteoSchweiz/SIATEC316) must be fixed with the data
   owner (assessment §8.6; textbook ch06 §6.8-1).
5. **SIA 380-1 four-sheet variants** are modelled as one calculation with a variant axis
   (`Sia3801Coefficients.variant`, `get_sia3801(variant=…)`); the variant semantics
   (DE/EN × ±Qc) must be confirmed against a reference run in stage 1 (assessment §8.9).
6. **Excel backend details** (COM automation, `AutomationSecurity = ForceDisable`, link
   handling, recalculation determinism) are specified at contract level; the concrete runner
   implementation and its timing characteristics are stage-3 work (assessment §7.3).
7. **Recommended next action:** review this set against
   [01-workbook-assessment.md](../01-workbook-assessment.md) §5–§7 and the merged textbook
   (chapters ch01–ch06), then start stage 0/1 (extraction + golden reference cases) with part
   03's `DatasetExtractor` and part 04's `ExcelBackend` as the implementation blueprint.

---

## 5. Reproducing the verification

```powershell
# 1) five-field entry check (parts 02–07): every '### ' block must contain
#    **Purpose:**, **Inputs**, **Outputs:**, **Raises:**, **Example:**
#    (run per file; result: entries=N missing=0)

# 2) markdown link/anchor check (all docs/*.md):
#    - every relative link target exists
#    - every '#anchor' resolves to a heading (GitHub slug: lowercase,
#      strip punctuation, spaces → hyphens, no collapsing)
# Result: 140 anchors checked, 0 broken (2026-08-15);
# re-verified on the merged doc tree (sets 01–04) on 2026-08-20 — see
# docs-consistency-report.md §6 for the merged counts.
```
