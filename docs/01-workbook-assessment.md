# Grounded Architectural Assessment — SIA 2024 Excel Tools

**Scope:** `data/raw/2024_Raumdatenblätter_dfi_V221.xlsm` and `data/raw/2024_Gebaeude-Tool_dfi_V221.xlsm`

**Method:** Both `.xlsm` packages were copied and unpacked as OOXML ZIP archives; every sheet was
dumped cell-by-cell (address, value, formula, cached result); both `vbaProject.bin` files were
extracted to VBA source; external-link, protection, ActiveX, chart, comment and Power Query parts
were inspected. **No source file was modified.** Analysis artifacts live under `.analysis/`
(workbook copies, per-sheet TSV dumps, extracted VBA, extracted Power Query mashup).

This document strictly separates **Findings** (observed in the files) from **Proposals**
(architectural recommendations).

---

## 1. Workbook 1 — SIA 2024 Raumdatenblätter (findings)

*2,455,973 bytes, 25 worksheets, ≈132,000 non-empty cells, ≈48,100 formula cells.*

**Purpose (as stated in the workbook):** display and print the room data sheets
("Raumdatenblätter") according to SIA 2024; the data sheet values are standardized assumptions
for room uses to be used in energy and building-services calculations. The workbook is a
*versioned professional dataset with an embedded calculation engine*, not a project tool.

### 1.1 Sheet inventory

| Sheet (name in file) | State | Role (observed) |
|---|---|---|
| Lizenzieren | veryHidden | License/activation UI (legacy, logic disabled in V221) |
| Anleitung | visible | Trilingual instructions, language selector |
| Begriffe | veryHidden | **Trilingual dictionary** (DE/FR/IT), SIA clause numbers, sheet names, UI labels; `G1` = language index (1/2/3) |
| Eingabedaten | visible | **Master data matrix**: 45 room uses (rows 9–53) × ~200 parameter columns; per parameter triples *Standard / Zielwert / Bestand*; 24 h person & device profiles; 12 monthly values; weekly profile; comments; SIA 380/1 system requirements |
| Profile | veryHidden | Hourly profiles (rows 58–86), **annual ventilation full-load-hour engine** (rows 605–976, 365 days × regulation variants) |
| Monatswerte | veryHidden | Monthly climate values per station (air temperature etc.) |
| Winter_Auslegung | veryHidden | Winter design conditions per station (temp, radiation, wind, humidity) |
| Aug_Auslegung | veryHidden | Summer design conditions per station (incl. Power Query import area) |
| Datenblatt | visible | **Rendered per-room-use data sheet** (rows 4–196 = 193 parameters), driven by `nutzid` (C1) and `klimastat` (G1) |
| Eigene Nutzung | visible | Copy of Datenblatt for a user-defined room use (same structure) |
| Resultate Standard / Zielwert / Bestand | visible | 45-row × ~70-column exported result tables (macro-generated) |
| KZ_Raum_2024 | veryHidden | Room-use key figures ("Energiekennzahlen" kWh/m² + "Leistungskennzahlen" W/m²) per room use × value kind |
| Fläche-E / -L / -ZW / -Best | veryHidden | Building-category area tables (Gebäudekategorien I…X) |
| GEPAMOD | veryHidden | SIA 2024 ↔ SIA 380/1 building-category mapping |
| Volll_Lüft | veryHidden | Ventilation full-load hours per room use, regulation type and **standard version** (SIA 2024:2015 / prSIA 2024:2021 / prSIA 2024-C1:2024) |
| SIA 380-1 (+ `_Qc`, `_EN`, `_Qc_EN`) | veryHidden | Per-room-use **SIA 380/1 heating-demand calculation** (German/English × with/without cooling variant) |
| Qhc_Klimastat | veryHidden | Annual cooling energy (Qhc) per room use × climate station × value kind |

### 1.2 Data model (observed, de facto)

* **Room uses:** exactly **45** standard room uses, codes `1.01 … 12.12` (categories 1 Wohnen …
  12 Nebenräume; names trilingual via `Begriffe`). Data-quality quirk observed: code `12.1`
  instead of `12.10` (Wasch- und Trockenraum).
* **Parameters:** the Datenblatt contains **193 parameter rows**, grouped into sections
  (Raum, Bauphysik, Raumklima, Schallschutz, Personen, Geräte/Prozessanlagen, Beleuchtung,
  Lüftung, Kühlung, Feuchte, Heizlast, Warmwasser). Each parameter has: label (trilingual via
  `Begriffe!F<row>`), **symbol** (rich text with sub/superscripts, e.g. A_NGF), **unit**
  (rich text), and up to three value kinds (**Standard / Zielwert / Bestand**, columns M/N/O).
  Flag columns P/Q/R mark export-to-results, display, and internal-heat relevance.
* **Terminology source:** `Begriffe` rows carry **SIA clause identifiers** ("Ziffern", e.g.
  `1.1.1.4`, `1.1.2.10`) — a ready-made stable identifier scheme for parameters, plus DE/FR/IT
  labels (some Italian cells contain unfinished/red-marked translations).
* **Climate data:** **40 climate stations** with winter design values (`Winter_Auslegung!H5:H44`),
  summer design values (`Aug_Auslegung`), monthly values (`Monatswerte`) and Qhc results
  (`Qhc_Klimastat`, 40 stations × 12 months).
* **Value provenance (observed formulas):** raw values are looked up with `INDEX/MATCH` from
  `Eingabedaten` (with `MATCH` on the parameter-name row); derived values are computed with
  simple arithmetic, `ROUND(…,-1)`, `SUMPRODUCT` and `SUMIF` (e.g. annual full-load hours
  `t_P = t_P,d · d_P · f_P`, annual ventilation full-load hours from 365 daily rows);
  design temperatures come from the climate sheets per selected station.
* **Formula palette (Raumdaten):** only `AVERAGE, IF, INDEX, MAX, MIN, ROUND, SUM, SUMIF,
  SUMPRODUCT` — no UDFs referenced by stored formulas (the bundled `FeuchteLuft_Formeln.bas`
  is **not referenced** here).

### 1.3 Automation (observed)

* VBA modules: license UI (`basLizenzieren`, `tblLizenzieren` — **all license checks commented
  out in V221**; stale license cells remain), language switching (`Sprachänderungen`,
  `tblBegriffe.Worksheet_Change` renames sheets and re-exports on language change),
  **export macros** (`Res_Export` 45 room uses, `Volll_Lüft_Export`, `Qhc_Export`
  40 stations × 45 uses), data-sheet **PDF/print export** (45 files), protection helpers.
* **No `Workbook_Open`/`BeforeClose` handlers are active** (all commented out) — no auto-run
  macros, no license enforcement on open.
* ActiveX controls: 7 on Lizenzieren (license UI), 1 on Anleitung (language combo), 4 form
  controls on Datenblatt (PDF/print buttons), 4 on Profile, 5 on Eigene Nutzung.
* Charts: 145 embedded chart parts (per-room-use charts on Datenblatt area).
* **Power Query (Get & Transform): one query `AIGSommer`** in `customXml/item1.xml`
  (DataMashup). Extracted M source: reads `C:\Program Files (x86)\SIA\SIATEC316\Stammdaten\
  AIGSommer.dat` (tab-separated, 45 columns, codepage 1252) — a **machine-specific external
  import** of "AIG Sommer" (Annahmen für Ingenieurgrundlagen) data, last refreshed 2020-10-10.
* External link: **1 link to the predecessor module**
  `SIA2024_Modul-Raum_2012-05-21.xlsm` (OneDrive path; cached values present, used for legacy
  continuity).
* Named ranges: **186 defined names**, mostly SIA 380-1 sheet parameters (`AE, AP, bGF, EBF,
  Qh, …`), plus `nutzid`, `klimastat`, `Res`; several **broken** (`QhmitWB = #REF!`).
* Protection: workbook structure SHA-512 (`lockStructure`), 12 sheets with SHA-512 password
  hashes, 4 sheets passwordless. **The passwords are recoverable from the VBA source**:
  structure `"AWOUZTRf"`, sheets `"$iA2024"` — protection is commercial packaging, not
  cryptographic security.

---

## 2. Workbook 2 — SIA 2024 Gebäude-Tool (findings)

*897,991 bytes, 13 worksheets, ≈51,300 non-empty cells, ≈16,900 formula cells.*

**Purpose (as stated in the workbook):** estimation of **power and energy demand of buildings
in an early planning phase** ("Abschätzung des Leistungs- und Energiebedarfs von Gebäuden in
einer frühen Planungsphase") using SIA 2024 room-use assumptions. The workbook is a
**deterministic calculation model** (sizing + annual energy) over project inputs.

### 2.1 Sheet inventory

| Sheet | State | Role (observed) |
|---|---|---|
| Lizenzieren | veryHidden | License UI (legacy, disabled) |
| Anleitung | veryHidden/visible | Trilingual instructions; add/remove building sheets; explicitly points to the Raumdatenblätter tool at www.energytools.ch |
| Begriffe | veryHidden | Trilingual dictionary incl. the **45 room-use names** (`B13:F57` with codes) used as dropdown source |
| Gebäude | visible | **Building input table**: project, climate station (index → name), 21 room rows (room use, EBF flag, NGF, share) with per-use power/energy for Geräte, Prozessanlagen, Beleuchtung, Lüftung (system LAxx, volume flow), Raumkühlung (gekühlt flag), Raumheizung (beheizt flag), Warmwasser; totals; "Allg. Gebäudetechnik" inputs; Wertebereich selector (Standard/Zielwert/Bestand) |
| Lüftung | visible | **16 ventilation systems** (LA01–LA16): volume flow (Standard/Prozess/Projekt), SFP, fan power, regulation, full-load hours, WRG %, Kühlfall/Heizfall setpoints, humidity setpoints, air cooling/heating/humidification power+energy |
| Erzeugung | visible | **Generation systems**: 3 Kälteerzeuger + 3 Wärmeerzeuger + 3 Warmwassererzeuger with Nutzungsgrad, Deckungsgrad, Speicher-/Verteilverluste, Leistung/Energie, Endenergie per Energieträger |
| Resultate | visible | **Final energy table** per Energieträger (El, HEL, Erdgas, …) × end-use (Allg. Gebäudetechnik, Geräte, Prozessanlagen, Beleuchtung, Lüftung, Kühlung, Heizung, Warmwasser), plus weighting factors (NEGF, PEne, THGE) |
| Nutzungsgrad | veryHidden | Catalog of generation systems: KE01–KE06 (cooling, EER 3–15), WE01+ (heating, η 0.6–0.8), WW types, each with Energieträger and Hilfsenergie % |
| Berechnung LU | veryHidden | **Core AHU calculation sheet** (≈13,500 formula cells): a single air-handling-unit template (row 32) driven per system; **temperature-bin psychrometric method** over outdoor bins (−25 … +34 °C) with per-station bin hours; fans, WRG/KRG, recirculation, heating/cooling coils, dehumidification, humidification, IST/SOLL comparison, energy prices, results in rows 254–260 |
| Klimadaten | veryHidden | 40 stations × design temperatures, heating degree days, **hours per temperature bin** ("Anzahl Stunden Tac"), humidity series |
| KZ_Raum_2024 | veryHidden | Local room KPI matrix (45 × 46) — see dependency section |
| Qhc_Klimastat | veryHidden | Local copy of the Raumdaten Qhc matrix (40 stations) |
| Std | veryHidden | Copy of ventilation full-load-hour data; header comment: *"Quelle: SIA2024_Raumdatenblätter > tblVoll_Lüft"* |

### 2.2 Calculation flow (observed)

`Gebäude` room rows → `VLOOKUP` against **`Res`** (`KZ_Raum_2024!$B$7:$AV$51`, local KPI matrix)
for per-use W/m² and kWh/m² values → area-weighted room totals → `Lüftung` systems (volume flow
aggregated per system via `SUMIF`, energies pasted from `Berechnung LU` by macro) → `Erzeugung`
(distributes Kühlung/Heizung/WW demands over generators, computes Endenergie via
Nutzungsgrad/Deckungsgrad/Verluste) → `Resultate` (per Energieträger totals with NEGF/PEne/THGE
weighting). `Berechnung LU` is the only "physical" engine: psychrometric UDFs, bin-hour climate
data, stage-dependent fan power (P ∝ V^2.5), coil/heater/humidifier models.

* **Formula palette (Gebäude-Tool):** `ABS, AVERAGE, IF, IFERROR, INDEX, LOOKUP, MATCH, MAX,
  MIN, ROUND, SUM, SUMIF, SUMPRODUCT` plus **VBA UDFs** `AbsFeuchte, EnthalpieA, RelFeuchte,
  TaupunktA, TemperaturH` (moist-air physics, "Glück" saturation-pressure polynomials).
* **Unused/dead VBA observed:** `Fallunterscheidung.bas` (`Fall1Tzul/Fall1xzul/Fall2Tzul/
  Fall2xzul`) and `EnthalpieR/Saettigungsdruck/Feuchtkugel/TaupunktR` are defined but **not
  referenced by any stored formula**.
* Automation: license UI (disabled), language switch, **add/remove building sheets** macro
  (copies a veryHidden template sheet `tblLeer`), `Lüftung_Resultate` copy macro
  (row 32 → system rows), protection helpers. No active `Workbook_Open`.
* Named ranges: only **19**, several broken (`EtaWW = [1]Grundlagendaten!#REF!`,
  `Nein = #REF!`, `Parallel = #REF!`, `_xleta.INDEX = #NAME?`).
* Protection: structure SHA-512 + **all 13 sheets** SHA-512 (same known passwords).

---

## 3. Dependency relationship between the two workbooks (findings)

The Gebäude-Tool **depends on the Raumdatenblätter dataset in three ways of very different
robustness**:

1. **Live external links (fragile):** the Gebäude-Tool contains 4 external links:
   - `[3]` → `SIA2024_Raumdatenblätter_dfi_V221_20241117.xlsm` — **the Raumdatenblätter** under
     a date-suffixed name that does **not** match the distributed file name
     (`2024_Raumdatenblätter_dfi_V221.xlsm`). Used for: room-use codes/names
     (`[3]Eingabedaten!A9:C53` in `KZ_Raum_2024`), climate station names
     (`[3]Winter_Auslegung!A5…` in `Qhc_Klimastat`), and `nutzid` names
     (`[3]Datenblatt!C1`, `[2]Datenblatt!C1`).
   - `[2]` → `SIA2024_Modul-Raum_2012-05-21.xlsm` (predecessor module, also linked by the
     Raumdatenblätter itself).
   - `[1]` → `Lüftung_20201113.xlsm` (ventilation "Summenhäufigkeit" reference; its only named
     range `EtaWW` is `#REF!` — **broken**).
   - `[4]` → `Arealbewertungstool_V10_ungeschützt_Richtwerte_mme.xls` (reference energy values;
     `SMA_Faktor = [4]Referenz-Energie!H34`).
   All targets are absolute OneDrive / `C:\Users\Lemonadmin\…` paths — **machine-dependent**.
2. **Copied-at-authoring-time data (stale-prone):** the KPI values in `KZ_Raum_2024`
   (columns C–Y, AC–AV) are a mixture of hard-coded numbers and formulas to the **local**
   `Qhc_Klimastat` copy; `Qhc_Klimastat` and `Std` are full copies of Raumdaten exports
   (documented by the `Std!L2` provenance comment). Nothing refreshes them automatically.
3. **Conceptual dependency:** the tool's room-use names/assumptions come from the SIA 2024
   Raumdaten; the Anleitung sheet instructs users to obtain the Raumdatenblätter tool
   separately at www.energytools.ch.

**Consequence:** today the Gebäude-Tool maintains an **opaque, partially stale, partially
broken copy** of the Raumdaten dataset (exactly the problem the target architecture must
eliminate), while a thin live link keeps the room-use *list* and station *names* consistent.

---

## 4. Excel mechanism inventory (findings, consolidated)

| Mechanism | Raumdatenblätter | Gebäude-Tool |
|---|---|---|
| Worksheets | 25 (8 visible, 17 veryHidden) | 13 (4 visible, 9 veryHidden) |
| Formula cells | ≈48,100 | ≈16,900 |
| Named ranges | 186 (many; several `#REF!`) | 19 (several `#REF!`/`#NAME?`) |
| VBA (vbaProject.bin) | 34 modules, license logic **disabled**, export/print/language macros, no auto-run | 21 modules, license logic **disabled**, AHU copy macro, sheet add/remove, psychrometric UDFs, no auto-run |
| VBA UDFs used by formulas | none | `AbsFeuchte, EnthalpieA, RelFeuchte, TaupunktA, TemperaturH` |
| Power Query | **1 query** (`AIGSommer` ← SIATEC316 `.dat` file, machine path) | none |
| External links | 1 (predecessor module, cached) | 4 (2× Raumdaten variants, 1 broken Lüftung ref, 1 Arealbewertungstool) |
| Workbook protection | SHA-512 `lockStructure` (pw known) | SHA-512 `lockStructure` (pw known) |
| Sheet protection | 12 sheets SHA-512 + 4 passwordless (pw known) | 13 sheets SHA-512 (pw known) |
| ActiveX / form controls | 8 ActiveX + 14 form-control parts | 8 ActiveX + 107 form-control parts (105 on Gebäude) |
| Charts | 145 chart parts | 7 chart parts |
| Data validation | sparse; several `#REF!` lists | sparse; several `#REF!` lists |
| Comments / threaded comments | 14 legacy + threaded | 2 legacy + threaded |
| calcChain | present (cached results embedded) | present |
| Pivot tables | none | none |
| Query tables / connections | AIGSommer query table | none |

---

## 5. Proposed canonical domain model and component separation (proposal)

### 5.1 Canonical Raumdaten dataset (versioned, machine-readable)

A single published dataset package (JSON Schema-validated, released like software):

* **`room_use`** — stable id (numeric `nutzid` 1–45 **plus** the SIA code `1.01…12.12`),
  category (1 Wohnen … 12 Nebenräume), DE/FR/IT names, SIA clause references.
* **`parameter`** — stable parameter id derived from the **SIA clause number** (e.g.
  `1.1.2.7` Jahresgleichzeitigkeit) or a documented slug; trilingual label, LaTeX/Unicode
  symbol, unit (as structured text + SI hint), data type (number/enum/text/bool), category,
  applicable value kinds (Standard/Zielwert/Bestand), display/export flags, applicability
  conditions (observed as P/Q/R flags and conditional formulas).
* **`room_use_profile`** — parameter values per room use × value kind, including derived
  values with **formula provenance** (the workbook's calculation rules recorded as metadata,
  not re-derived by hand).
* **`hourly_profile` / `monthly_profile` / `weekly_profile`** — person/device/lighting/vent
  load profiles (24 h, 12 months, 7 days), each tagged with profile type.
* **`ventilation_full_load_hours`** — per room use × regulation type × **standard version**
  (2015/2021/2024-C1) — this table already documents its own provenance; the version axis is a
  model for how the whole dataset should evolve.
* **`climate_station`** (40 stations) — winter/summer design values, monthly values,
  temperature-bin hour counts, HDD, air pressure; versioned as **external dataset** (SIA/partner
  source; note the AIGSommer Power Query and the Lüftung Summenhäufigkeit link).
* **`building_category_mapping`** (GEPAMOD/Fläche-*) and **`sia3801_coefficients`** —
  category mappings and per-category limit/basis values used by the SIA 380/1 sheets.
* **`release`/`changelog`** — dataset release id (V221), SIA publication edition (SIA 2024),
  corrigenda list, extraction hash of the source workbook, extraction tool version.

### 5.2 Gebäude calculation model definition

A versioned, declarative **model definition** (not code): inputs schema, calculation graph
(room KPIs → building aggregation → AHU bin calculation → generation → resultate), constants
and catalogs (Nutzungsgrad, SFP classes, motor efficiency classes IE1–IE5, filter classes,
price tables, weighting factors NEGF/PEne/THGE). Each node declares its inputs, formula
(reference to Excel cell/range initially), unit, and output. This is what makes
**traceability and reference testing** possible: every result carries the model version and
the input values that produced it.

### 5.3 Component separation (proposal)

```text
Excel source workbooks (authoring/reference)
        │  (extraction pipeline, on copies, checksummed)
        ▼
[1] Raumdaten dataset package (versioned JSON + JSON Schema)   ← canonical, single source of truth
[2] Gebäude calculation model definition (versioned JSON)      ← declarative, references dataset ids
        │
        ▼
[3] Versioned data service (read-only, semantic query API)     ← list/get/compare room uses, parameters, profiles, climate
[4] Deterministic calculation runtime                           ← validate/calculate/explain
        │    initial runtime: Excel adapter (reference implementation)
        │    later runtime: ported code, verified case-by-case against Excel
        ▼
[5] Stable domain API (OpenAPI + JSON Schema)
        ├── Web / engineering / BIM integrations
        ├── Python / Grasshopper SDK (OpenAPI client)
        └── MCP adapter (later, thin, on top of [5] only)
```

**Rules:** Excel cells/addresses never cross boundary [5]; the dataset package is the only way
the calculation model consumes Raumdaten; the Gebäude-Tool's local copies (`KZ_Raum_2024`,
`Qhc_Klimastat`, `Std`) are replaced by service lookups; Excel remains an authoring/export
format, not an API.

---

## 6. Initial API boundary (proposal)

Exposed as **OpenAPI 3 + JSON Schema**, domain concepts only.

### 6.1 Data service (Raumdaten)

```
GET  /datasets                         → list dataset releases (V221, …) with edition, date, checksum
GET  /datasets/{release}/room-uses     → list_room_uses (id, code, category, names de/fr/it)
GET  /datasets/{release}/room-uses/{id}→ get_room_use_profile (all parameters, values per kind, units, provenance)
GET  /datasets/{release}/parameters    → parameter catalog (clause ids, labels, units, types, categories)
GET  /datasets/{release}/room-uses/{a}/compare/{b} → compare_room_use_profiles (diff, value kinds)
GET  /datasets/{release}/climate-stations
GET  /datasets/{release}/profiles      → hourly/monthly/weekly profiles
GET  /datasets/{release}/exports.{json|csv|xlsx}  → bulk export
POST /datasets/{release}/validate      → validation report (schema + value rules)
```

### 6.2 Calculation service (Gebäude-Tool)

```
POST /calculations/validate            → validate_building_input  (project, rooms, systems, station, generation)
POST /calculations                     → calculate_building
     request:  { datasetRelease, modelRelease, project{…}, rooms[{roomUse, area, flags, system}],
                 ventilation[{…}], generation[{…}], climateStation, valueKind (standard|zielwert|bestand) }
     response: { resultId, modelVersion, datasetVersion, climateVersion, assumptions[], warnings[],
                 overriddenValues[], inputsHash, results { perRoom, perSystem, perEnergietraeger,
                 totals }, intermediates { ahuBins, fullLoadHours, qhc }, units }
GET  /calculations/{resultId}          → retrieve stored calculation (reproducibility)
GET  /calculations/{resultId}/explain  → explain_calculation_result (trace steps, formulas, data sources)
GET  /versions                          → publication, dataset, model, implementation, climate versions
```

Explicitly **not exposed**: `write_cell/read_cell` or any address-based operation; the Excel
adapter (later) keeps ranges internal.

---

## 7. Staged proof-of-concept plan (proposal)

1. **Extraction & golden dump (stage 0):** deterministic extraction of the full cell graph
   (values + formulas + cached results) from both workbooks; checksum both files; build the
   **canonical Raumdaten JSON** from `Eingabedaten`/`Begriffe`/`Datenblatt`/`Profile`/
   `Volll_Lüft`/climate sheets; publish release metadata.
2. **Reference cases (stage 1):** define a small corpus (e.g. the shipped example building at
   Zürich station, value kind Standard, plus 3–5 variations) and a **reference runner** that
   executes the Excel model on copies (Excel COM with `AutomationSecurity = ForceDisable`,
   links not updated, `Application.Calculation` deterministic, no save) and records inputs,
   all intermediates and outputs. This is the test oracle.
3. **Data service (stage 2):** read-only API over the canonical dataset (JSON Schema
   validation, exports JSON/CSV/Excel, semantic queries, compare endpoint). Verified against
   stage-0 dump by cross-checking a random sample of parameters per room use.
4. **Calculation service v1 — Excel runtime (stage 3):** wrap the existing Gebäude-Tool behind
   the calculation API via the reference runner; map API inputs ↔ workbook inputs and
   workbook outputs ↔ API results; every response carries versions + trace id.
5. **Regression harness (stage 4):** run the same inputs through v1 (Excel) and every future
   implementation; compare final and selected intermediate values within defined tolerances
   (proposal: exact for pure arithmetic on same doubles; ≤1e-9 relative for transcendental
   physics; explicit rounding rules where `ROUND(…,-1)` is normative).
6. **Gradual port (stage 5):** replace modules one at a time — order by risk/benefit:
   (a) room KPI derivation (pure lookup/arithmetic), (b) psychrometric UDFs (pure functions,
   direct port with unit tests against VBA values), (c) AHU bin calculation (largest, keep
   Excel as oracle), (d) generation/resultate aggregation; each stage ships behind the same API.
7. **LLM adapter (stage 6, later):** thin MCP server exposing only the stable API operations
   (`list_room_uses`, `get_room_use_profile`, `calculate_building`, `explain_calculation_result`,
   `get_versions`) with tools that return structured JSON; no cell access, no memorized values.

---

## 8. Technical uncertainties and risks to test before finalizing the stack

1. **Excel fidelity of extracted formulas:** cached values in the files were produced by Excel;
   any re-implementation must reproduce Excel semantics for `INDEX/MATCH`, `VLOOKUP` (sorted vs
   exact), `SUMPRODUCT`, `ROUND(…,-1)` (banker's vs arithmetic), floating-point order, and
   locale-dependent argument separators. **Test:** compare extraction against a fresh Excel
   recalculation on copies (COM), and freeze a golden dump.
2. **External-link breakage:** all 4 Gebäude-Tool links point to machine-specific absolute
   paths and one target name differs from the distributed file name; cached values hide the
   breakage until recalculation. **Test:** how much of the model depends on live links vs
   cached copies; plan the canonical dataset as the replacement before touching the runtime.
3. **Excel-as-runtime constraints:** COM automation needs a licensed Excel on a Windows host,
   must not trigger the (currently disabled) license macros, must disable link updates, and
   recalculates the whole workbook each call (performance). **Test:** headless recalculation
   stability, timing for one building, and determinism across runs.
4. **UDF porting:** the psychrometric functions use "Glück" polynomials with magic constants
   (611, 2501.6, 1.006, 1.86, 2.8858, 8.02, …) and an empirical wet-bulb formula; the workbook
   itself contains **unused variant UDFs** (which constants are normative?). **Test:** port +
   assert against VBA results over the full bin range.
5. **Normative rounding:** `ROUND(…,-1)` on annual full-load hours and `IF(OR(...))` guards
   are part of the published values; tolerance definitions must distinguish normative rounding
   from float noise. **Test:** sensitivity of results to rounding rules.
6. **Climate data provenance:** bin-hour counts, design values and the AIGSommer import have
   external, versioned sources (SIATEC316, MeteoSchweiz) and machine-specific paths; the
   dataset must record climate version + source, and the service must accept climate-data
   versions explicitly.
7. **Trilingual content quality:** labels are rich text (sub/superscript symbols), some
   Italian cells are unfinished (red-marked placeholders) and sheet names are **renamed at
   runtime per language** — extraction must normalize rich text to structured symbol/unit
   fields and must not key anything by sheet name.
8. **Data quality landmines (observed):** code `12.1` instead of `12.10`; `#REF!` named ranges
   (`QhmitWB`, `EtaWW`, `Nein`, `Parallel`); broken validation lists; dead VBA modules; stale
   license cells; two different Raumdaten link targets (`…V221_20241117.xlsm` vs
   `…V221.xlsm`) that may be different releases — the dataset release id must be pinned
   explicitly, and a diff between the linked variant and the shipped file should be performed
   in stage 1.
9. **SIA 380-1 sheet variants:** four parallel sheets (DE/EN × with/without Qc) duplicate the
   same logic with small differences; the canonical model must treat them as variants of one
   calculation, not four datasets.
10. **Licensing/legal packaging:** protection is present but its passwords are embedded in VBA;
    the digital service must not replicate the (disabled) license-gating logic, but the SIA
    content licensing terms for the dataset/API must be clarified with the rights holder
    (SIA Zurich / dfi) before public exposure.

---

## 9. Findings vs proposals — one-line summary

* **Findings:** Raumdatenblätter = versioned trilingual dataset (45 room uses, 193 parameters,
  3 value kinds, 40 climate stations) with a small arithmetic engine and export/print macros;
  Gebäude-Tool = deterministic early-design energy model (21-room building → 16 AHUs → 9
  generators → resultate) with a temperature-bin psychrometric core; the tool depends on the
  Raumdaten via one fragile live link, several stale copies and one broken reference; both
  files contain dead code, broken ranges and known protection passwords, and neither executes
  macros automatically.
* **Proposals:** extract the dataset into a versioned JSON package with clause-number
  parameter ids; declare the Gebäude model as a versioned graph over that dataset; expose a
  domain API (data + calculation) behind OpenAPI/JSON Schema; keep Excel as reference runtime
  first, then port module-by-module against golden reference cases with explicit tolerances;
  add an MCP adapter only later, on top of the stable API.
