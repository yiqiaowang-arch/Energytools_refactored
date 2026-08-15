# Document-Tree Merge & Cross-Consistency Report

**Document-Tree Merge & Cross-Consistency Report** · 2026-08-20 · branch
`文档树合并与交叉一致性核对-把四个工作区的产出-`

Scope: merge the outputs of **four parallel workstreams** into one final documentation tree and
cross-check symbol-level consistency between the architecture/API-reference set, the
calculation-model textbook, and part 08's completeness verification. This report lists what was
merged, what was verified consistent, what was inconsistent and how it was fixed, the
verification actually executed, and the remaining open problems.

---

## 1. Inputs (four workstreams + main repository)

| Workstream (branch) | Output | Merged into |
|---|---|---|
| `架构与api参考文档-编写完整的oop库架构文档` | `docs/01-workbook-assessment.md`, `docs/README.md`, `docs/architecture+api-reference/` (README + parts 01–08) | `docs/` (assessment + inventory + architecture set) |
| `计算模型教科书式文档-基于-analysis提取` | `docs/README.md`, `ch01–ch06`, `analysis_Berechnung_LU.md` | `docs/textbook/` (intro README renamed into the folder) |
| `多安装方式打包脚手架-编写pyproject-t` | `README.md`, `pyproject.toml`, `pixi.toml`, `pixi.lock`, `src/`, `tests/`, `docs/installation.md` | repo root + `docs/installation.md` |
| `文档构建与readthedocs发布管线-搭建m` | `mkdocs.yml` (scaffold nav) | `mkdocs.yml` (nav rewired to the real tree) |
| Main repo `Energytools_refactored` | `docs/01-workbook-assessment.md` (identical copy), `data/raw/*.xlsm`, `.analysis/`, `.gitignore` | `docs/01-workbook-assessment.md`, `.gitignore` baseline; `data/`/`.analysis/` stay in the main repo (not copied) |

**Conflict resolution:** both the main repo and the ARCH worktree carry
`docs/01-workbook-assessment.md` — hashes are identical (SHA-256
`E67C9DE9ACB087F4D256D137BE674730CDBFE0A18047E17AFB7569060EF5D096`), one copy is kept. The two
`docs/README.md` files (English docs inventory vs. Chinese textbook intro) both had to exist at
`docs/` — the textbook intro moved to `docs/textbook/README.md`, the merged inventory stays at
`docs/README.md`.

## 2. Final tree (merge-ready package)

```text
<repo root>
├── README.md · .gitignore · .python-version          (packaging scaffold; site/ added to gitignore)
├── pyproject.toml · pixi.toml · pixi.lock            (scaffold; docs extra unified on MkDocs)
├── src/energytools/ · tests/                         (scaffold placeholder package + smoke tests)
├── mkdocs.yml                                        (nav rewired to the real docs tree)
├── requirements.txt · .readthedocs.yaml              (new: MkDocs build pipeline)
└── docs/
    ├── README.md                                     (merged docs inventory, sets 01–04)
    ├── 01-workbook-assessment.md                     (set 01, unchanged)
    ├── architecture+api-reference/                   (set 02, consistency fixes applied)
    │   ├── README.md · 01-package-inventory.md · 02-common-foundation.md
    │   ├── 03-raumdaten-service.md · 04-gebaeude-engine.md · 05-versioning-export.md
    │   ├── 06-fastapi-layer.md · 07-mcp-layer.md · 08-completeness-check.md
    ├── textbook/                                     (set 03)
    │   ├── README.md · ch01-…ch06-*.md · analysis_Berechnung_LU.md
    ├── installation.md                               (set 04a)
    └── deployment/readthedocs.md                     (set 04b, new)
```

## 3. Cross-check method

1. Read all four workstreams' documents completely (ARCH set 01–08, textbook README + ch01–ch06,
   scaffold README/installation/pyproject/pixi, mkdocs.yml).
2. Extracted the authoritative symbol inventory (part 01 §2: 107 rows + 16 methods + 20 endpoints
   + 13 schemas + 3 deps + 9 tools = 163 entries) and the workbook ground truth (textbook
   chapters: 8 UDFs + call-site table, 45 room uses, 16 AHU systems LA01–16, 40 climate stations,
   Std table, Fall 1–4, Resultate weighting).
3. Compared (a) inventory ↔ API entries (part 08 §2.2 counts), (b) inventory ↔ textbook symbols
   and constants, (c) textbook ↔ part 08 cross-references, (d) docs inventory status (set 03),
   (e) mkdocs nav ↔ actual files, (f) scaffold toolchain ↔ docs pipeline.

## 4. Verified-consistent (no change needed)

* **Counts:** 107 inventory rows, 163 API entries; part 02 = 28 entries, part 03 = 38 entries
  (22 class/function + 16 service methods), part 04 = 35, part 05 = 12 entries / 14 blocks,
  part 06 = 38 (Settings, create_app, 20 endpoints, 13 schemas, 3 deps), part 07 = 12
  (3 server/registry + 9 tools). All five-field entry checks pass.
* **Domain constants between sets:** 45 room uses, 16 ventilation systems LA01–LA16,
  40 climate stations, NEGF/PEne/THGE weighting, `Std` table semantics (`t_VL,V` / `t_VL,E`),
  fan law P ∝ V^2.5, `ROUND(…,-1)` rounding, three regulation modes
  (einstufig/zweistufig/stufenlos), WRG/KRG recovery, `SFP` fan power.
* **Versioning:** dataset release `V221` / model `1.0.0` / implementation PEP 440 / climate —
  consistent across sets 02 and 03.
* **VBA mapping:** 34 Raumdaten + 21 Gebäude modules all present in part 01 §3 (no silent
  omissions).

## 5. Inconsistencies found and fixed

| # | Issue | Location(s) fixed | Fix |
|---|---|---|---|
| F1 | **`Fallunterscheidung` mislabelled as dead code.** The ARCH set (README §6, 01 §3.2, 08 §2.3/§4.2) marked it `not ported (dead)`; the textbook's full-sheet formula scan proved it **live** (`Berechnung LU!BB:BE` calls `Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul` on 61×2 bin rows — textbook README §0.7-10, ch04 §4.9). | `README.md`, `01-package-inventory.md`, `08-completeness-check.md` | Reclassified as live code ported as the **Fall 1–4 case selection** in `ahu.calculate_ahu` / `AhuBinResult.case`; correction note added in 08 §2.3; 08 §4.2 now demands oracle verification of the ported case logic (golden values from rows 254–260). |
| F2 | **`TaupunktA` listed twice** in 01 §3.2 (both "referenced" and "not referenced"), and 04 §2.8 claimed it was "referenced in the Raumdaten workbook". | `01-package-inventory.md`, `04-gebaeude-engine.md` | Per textbook ch01 §1.7/§1.10: referenced by `Berechnung LU!AQ{n}` but **commented out in the VBA module** → `#NAME?`, column chain unused. Removed the duplicate, corrected the workbook claim, marked the function reference-only. |
| F3 | **`calculate_ahu` signature mismatch**: inventory 01 §2.14 said `calculate_ahu(input, climate)`, part 04 §3.4 defines `calculate_ahu(input: AhuInput)`. | `01-package-inventory.md` | Inventory row fixed to `calculate_ahu(input)`. |
| F4 | **AHU case semantics: 3 values vs. 4 falls.** Part 04 §3.2 `AhuBinResult.case` allowed `"heizen_befeuchten" | "kuehlen_entfeuchten" | "free"`; the workbook and textbook ch04 §4.9 define **Fall 1–4** (heat+humidify / dehumidify+heat / cool±reheat / cool+humidify). | `04-gebaeude-engine.md` | `case` redefined as the four Fall values `fall1_heizen_befeuchten … fall4_kuehlen_befeuchten`, citing the live `Fallunterscheidung` detector `AW{n}`; `calculate_ahu` purpose updated. |
| F5 | **Physics constant list incomplete vs. textbook.** Part 04 §2.1 named 9 constants; the workbook model also uses `cw = 4.19` (liquid water), `ρ = 1.15` (air density), `r100 = 2256` (100 °C), `622` (molar-mass ratio) — textbook ch01 §1.1, ch04 §4.16-3, appendix §8. | `04-gebaeude-engine.md`, `01-package-inventory.md` | Added `CP_WATER`, `AIR_DENSITY`, `HEAT_OF_VAPORIZATION_100`, `MOLAR_MASS_RATIO` to the constants entry (values + workbook grounding). |
| F6 | **Relative-humidity unit convention.** Part 04 §2.3/§2.4 implied `rh` in % while the VBA formula text matched the workbook's **fractional (0–1)** call convention (textbook ch01 §1.3/§1.6/§1.9). | `04-gebaeude-engine.md` | Documented both sides: workbook call sites pass fractions; the Python API takes % (0–100) and converts internally; `RelFeuchte` returns a fraction in the workbook, % in the API. |
| F7 | **Dead-UDF status inconsistent.** README §6 claimed only 5 referenced UDFs are ported, while 01 §2.13/04 §2 presented `enthalpy_from_rel_humidity`, `dew_point`, `dew_point_from_absolute_humidity` as ordinary ports. | `01-package-inventory.md`, `04-gebaeude-engine.md`, `README.md` | Marked `EnthalpieR`/`TaupunktR`/`TaupunktA`/`Feuchtkugel`-derived functions **reference-only** with textbook citations (ch01 §1.7–§1.9); `saturation_pressure_glueck` noted as extracted for reuse. |
| F8 | **Part-03 block count wrong in 08 §2.2**: "39/39 blocks (23 class/function + 16 method)" vs. 38 actual entries (22 + 16; the `### 3.2 Methods` container is not an entry). | `08-completeness-check.md` | Corrected to "38/38 entry blocks pass (22 class/function + 16 method; the `### 3.2 Methods` container heading is not an entry)". |
| F9 | **Docs inventory status stale**: set 03 (textbook) marked `planned (parallel worktree)` in docs/README.md and 08 §3. | `docs/README.md` (rewritten), `08-completeness-check.md` | Set 03 marked `done` with per-chapter links; new set 04 (installation + deployment) added; completeness statement updated. |
| F10 | **mkdocs.yml nav pointed at non-existent files** (`index.md`, `architecture/*`, `computation/*`, `api/*` — none exist in any workstream). | `mkdocs.yml` | Nav rewired to the actual tree (assessment, architecture set 02, textbook set 03, installation, deployment); verified every nav path exists. |
| F11 | **Missing build-pipeline files**: `mkdocs.yml` references `requirements.txt` and `.readthedocs.yaml`, neither existed anywhere. | new `requirements.txt`, `.readthedocs.yaml`, `docs/deployment/readthedocs.md` | Created MkDocs/ReadTheDocs pipeline config and a deployment doc (set 04b); `site/` added to `.gitignore`. |
| F12 | **Toolchain conflict: Sphinx vs. MkDocs.** The scaffold's `docs` extra (pyproject.toml), pixi `docs` feature and installation.md promised a Sphinx toolchain; the docs-pipeline workstream standardized on MkDocs + Material. | `pyproject.toml`, `pixi.toml`, `docs/installation.md` | Unified on `mkdocs` + `mkdocs-material` in the extra, the pixi feature and the docs (extras table + pixi environments table + links to the new deployment doc). |
| F13 | **Leftover process artifact in a deliverable**: the appendix `analysis_Berechnung_LU.md` ended with a `## Worker report` section (analysis log, not documentation). | `docs/textbook/analysis_Berechnung_LU.md` | Removed the worker-report section; preserved the open questions by pointing to the corresponding textbook sections (ch01 §1.7, ch04 §4.12/§4.14, README §0.7) in a short creation note. |

## 6. Verification executed (on the merged tree)

| Check | Result |
|---|---|
| Markdown link/anchor check (all `docs/*.md`; GitHub slug rules; file existence + `#anchor` resolution) | **21 files, 414 headings, 227 links, 0 broken** |
| Five-field entry check (parts 02–07: every `###`/`####` entry block contains Purpose / Inputs / Outputs / Raises / Example) | 28 + 38 + 35 + 14 + 20 + 9 = **144 entry blocks, 0 field issues** (the `### 3.2 Methods` container excluded as non-entry) |
| mkdocs.yml nav ↔ files | all **21 nav paths exist** |
| Assessment copy dedup | main-repo vs. worktree `01-workbook-assessment.md` identical (SHA-256 match) |
| Leftover-marker grep (`Worker report`, TODO/FIXME/XXX/TBD…) | clean (3 benign word matches) |

Notes: `mkdocs build` was not executed in this session (no MkDocs runtime available in the
sandbox); the static nav/link checks above cover the failure modes `mkdocs build` would report
for this tree. The textbook's `.analysis/`-relative references (VBA/TSV dumps) resolve only in
the main repository, which owns `.analysis/` and `data/raw/` — the merged package deliberately
does not copy them.

## 7. Merge-ready package — how to merge

The workspace root **is** the merge-ready package. To merge into the main repository
(`Energytools_refactored`):

1. Copy the tree (or merge the branch): `README.md`, `.gitignore`, `.python-version`,
   `pyproject.toml`, `pixi.toml`, `pixi.lock`, `requirements.txt`, `.readthedocs.yaml`,
   `mkdocs.yml`, `src/`, `tests/`, `docs/`.
2. No conflicts expected: the only overlapping file, `docs/01-workbook-assessment.md`, is
   byte-identical to the main repo's copy; `data/` and `.analysis/` stay untouched.
3. After merge, run `pip install -r requirements.txt && mkdocs build` (or
   `pixi install -e docs`) to verify the site builds, then push to trigger the ReadTheDocs
   build (`.readthedocs.yaml`).

## 8. Open problems / next actions

1. **Spec-only, no implementation yet.** The library does not exist beyond the scaffold; when
   the real modules land, re-run the doc↔code symbol audit (08 §4.1).
2. **Fall 1–4 golden values.** The ported case logic (`ahu.calculate_ahu`) must be verified
   against the Excel oracle using `Berechnung LU` rows 254–260 (08 §4.2) — the textbook
   provides the mechanism (ch04 §4.9) but no per-system oracle values were extracted yet.
3. **Workbook quirks to honour, not reproduce** (08 §4.3): `Lüftung!U32:Z32` wiring shift
   (ch04 §4.14-8), `Resultate!I21`/`G22:F22` weighting copy-paste errors (ch05 §5.10),
   `N9/O9` selector offsets (ch02 §2.3), `AQ/AS` dead column (ch04 §4.14-1).
4. **Climate-data versioning** and **SIA 380-1 variant semantics** still need data-owner
   confirmation (08 §4.4/§4.5).
5. `pixi.lock` was solved for the scaffold's four platforms; re-run `pixi install` once the
   `docs` feature changed (mkdocs replaces sphinx) to refresh the lockfile.
6. `mkdocs.yml` `repo_url`/`site_url` are placeholders — replace before first public build.
