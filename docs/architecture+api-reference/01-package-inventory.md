# Part 01 — Package / Module / Symbol Inventory

**Document set 02** · Target-state design specification · Back to [index](README.md)

This part is the **map**: the complete package/module tree and, for every module, the table of
public symbols with their kind, a one-line purpose and the pointer to the full API entry in
parts 02–07. Every row in these tables has a full API reference entry (purpose / inputs /
outputs / exceptions / example) at the linked location — this is verified in
[08-completeness-check.md](08-completeness-check.md).

## 1. Package tree

```text
energytools/                        [02-common-foundation.md, 05-versioning-export.md]
├── common/                         → 02
│   ├── errors.py
│   ├── versioning.py
│   ├── units.py
│   ├── language.py
│   ├── valuekind.py
│   └── provenance.py
├── raumdaten/                      → 03
│   ├── model.py
│   ├── dataset.py
│   ├── service.py
│   └── compare.py
├── gebaeude/                       → 04
│   ├── model.py
│   ├── physics.py
│   ├── ahu.py
│   ├── engine.py
│   ├── resultate.py
│   └── backends/ {base, excel, native}
├── export/                         → 05
│   ├── base.py
│   ├── json_exporter.py
│   ├── csv_exporter.py
│   ├── xlsx_exporter.py
│   └── pdf_exporter.py
├── api/                            → 06
│   ├── app.py
│   ├── settings.py
│   ├── deps.py
│   ├── schemas.py
│   └── routers/ {datasets, calculations, versions}
├── mcp/                            → 07
│   ├── server.py
│   └── tools.py
└── cli/                            → 05
    └── main.py
```

## 2. Module symbol tables

### 2.1 `energytools/__init__.py` — distribution root → [05 §1](05-versioning-export.md#1-distribution-root)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `__version__` | str constant | PEP 440 version of the installed library | [05 §1.1](05-versioning-export.md#11-__version__) |
| `get_version()` | function | Structured `VersionInfo` of the installed library | [05 §1.2](05-versioning-export.md#12-get_version) |

### 2.2 `energytools.common.errors` — exception hierarchy → [02 §1](02-common-foundation.md#1-energytoolscommonerrors)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `EnergyToolsError` | class (Exception) | Base of all library exceptions | [02 §1.1](02-common-foundation.md#11-energytoolserror) |
| `DatasetNotFoundError` | class | Requested dataset release does not exist | [02 §1.2](02-common-foundation.md#12-datasetnotfounderror) |
| `DatasetValidationError` | class | Dataset/input violates schema or value rules | [02 §1.3](02-common-foundation.md#13-datasetvalidationerror) |
| `UnknownRoomUseError` | class | Room-use id not found in the dataset | [02 §1.4](02-common-foundation.md#14-unknownroomuseerror) |
| `UnknownParameterError` | class | Parameter id not found | [02 §1.5](02-common-foundation.md#15-unknownparametererror) |
| `UnknownClimateStationError` | class | Climate station id not found | [02 §1.6](02-common-foundation.md#16-unknownclimatestationerror) |
| `UnknownLanguageError` | class | Language not in {de, fr, it} | [02 §1.7](02-common-foundation.md#17-unknownlanguageerror) |
| `UnknownValueKindError` | class | Value kind not in {standard, zielwert, bestand} | [02 §1.8](02-common-foundation.md#18-unknownvaluekinderror) |
| `CalculationInputError` | class | Building input invalid (schema or domain rules) | [02 §1.9](02-common-foundation.md#19-calculationinputerror) |
| `CalculationError` | class | Calculation failed at runtime | [02 §1.10](02-common-foundation.md#110-calculationerror) |
| `ModelVersionMismatchError` | class | Dataset/model/climate versions incompatible | [02 §1.11](02-common-foundation.md#111-modelversionmismatcherror) |
| `BackendError` | class | Calculation backend failed | [02 §1.12](02-common-foundation.md#112-backenderror) |
| `ExcelBackendError` | class | Excel-COM-specific backend failure | [02 §1.13](02-common-foundation.md#113-excelbackenderror) |
| `ExportError` | class | Export failed (format, target, data) | [02 §1.14](02-common-foundation.md#114-exporterror) |
| `UnitError` | class | Invalid unit or unit conversion | [02 §1.15](02-common-foundation.md#115-uniterror) |
| `PsychrometricError` | class | Out-of-domain psychrometric input | [02 §1.16](02-common-foundation.md#116-psychrometricerror) |

### 2.3 `energytools.common.versioning` — version primitives → [02 §2](02-common-foundation.md#2-energytoolscommonversioning)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `DatasetRelease` | class (dataclass) | Immutable release metadata of a Raumdaten dataset package | [02 §2.1](02-common-foundation.md#21-datasetrelease) |
| `ModelRelease` | class (dataclass) | Immutable release metadata of the Gebäude model definition | [02 §2.2](02-common-foundation.md#22-modelrelease) |
| `VersionInfo` | class (dataclass) | Version quadruple dataset/model/implementation/climate | [02 §2.3](02-common-foundation.md#23-versioninfo) |
| `ChangelogEntry` | class (dataclass) | One changelog row (version, date, change, migration) | [02 §2.4](02-common-foundation.md#24-changelogentry) |
| `VersionResolver` | class | Resolves release ids/aliases to concrete releases | [02 §2.5](02-common-foundation.md#25-versionresolver) |

### 2.4 `energytools.common.units` — units → [02 §3](02-common-foundation.md#3-energytoolscommonunits)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `Unit` | class | Unit of measure (symbol, SI hint, category, convertible) | [02 §3.1](02-common-foundation.md#31-unit) |
| `Quantity` | class (dataclass) | Typed value + unit with conversion and formatting | [02 §3.2](02-common-foundation.md#32-quantity) |

### 2.5 `energytools.common.language` — languages → [02 §4](02-common-foundation.md#4-energytoolscommonlanguage)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `Language` | class (enum) | DE / FR / IT | [02 §4.1](02-common-foundation.md#41-language) |
| `TrilingualText` | class (dataclass) | de/fr/it label triple with language lookup | [02 §4.2](02-common-foundation.md#42-trilingualtext) |

### 2.6 `energytools.common.valuekind` — value kinds → [02 §5](02-common-foundation.md#5-energytoolscommonvaluekind)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `ValueKind` | class (enum) | STANDARD / ZIELWERT / BESTAND | [02 §5.1](02-common-foundation.md#51-valuekind) |

### 2.7 `energytools.common.provenance` — provenance → [02 §6](02-common-foundation.md#6-energytoolscommonprovenance)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `SourceRef` | class (dataclass) | One grounded source reference (workbook sheet/cell/formula) | [02 §6.1](02-common-foundation.md#61-sourceref) |
| `Provenance` | class (dataclass) | Collection of source references + note | [02 §6.2](02-common-foundation.md#62-provenance) |

### 2.8 `energytools.raumdaten.model` — canonical dataset model → [03 §1](03-raumdaten-service.md#1-energytoolsraumdatenmodel)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `RoomUse` | class (dataclass) | One of the 45 room uses (nutzid, SIA code, category, names) | [03 §1.1](03-raumdaten-service.md#11-roomuse) |
| `Parameter` | class (dataclass) | One of the 193 data-sheet parameters (SIA clause id, label, symbol, unit) | [03 §1.2](03-raumdaten-service.md#12-parameter) |
| `ParameterValue` | class (dataclass) | Value + unit + provenance for one parameter × value kind | [03 §1.3](03-raumdaten-service.md#13-parametervalue) |
| `RoomUseProfile` | class | Full parameter-value set of one room use (all kinds) | [03 §1.4](03-raumdaten-service.md#14-roomuseprofile) |
| `HourlyProfile` | class (dataclass) | 24 h person/device/lighting/vent profile | [03 §1.5](03-raumdaten-service.md#15-hourlyprofile) |
| `MonthlyProfile` | class (dataclass) | 12 monthly climate/profile values | [03 §1.6](03-raumdaten-service.md#16-monthlyprofile) |
| `WeeklyProfile` | class (dataclass) | 7-day weekly profile | [03 §1.7](03-raumdaten-service.md#17-weeklyprofile) |
| `ClimateStation` | class (dataclass) | One of the 40 stations (design values, monthly values) | [03 §1.8](03-raumdaten-service.md#18-climatestation) |
| `ClimateData` | class | Collection of stations with lookup | [03 §1.9](03-raumdaten-service.md#19-climatedata) |
| `FullLoadHoursTable` | class | Ventilation full-load hours per use × regulation × standard version | [03 §1.10](03-raumdaten-service.md#110-fullloadhourstable) |
| `BuildingCategoryMapping` | class (dataclass) | SIA 2024 ↔ SIA 380/1 category mapping (GEPAMOD) | [03 §1.11](03-raumdaten-service.md#111-buildingcategorymapping) |
| `AreaTable` | class (dataclass) | Building-category area table (Fläche-E/L/ZW/Best) | [03 §1.12](03-raumdaten-service.md#112-areatable) |
| `Sia3801Coefficients` | class (dataclass) | Per-category SIA 380/1 coefficients | [03 §1.13](03-raumdaten-service.md#113-sia3801coefficients) |
| `Sia3801Result` | class (dataclass) | SIA 380/1 heating-demand result of one room use | [03 §1.14](03-raumdaten-service.md#114-sia3801result) |
| `QhcTable` | class | Annual cooling energy per use × station × kind | [03 §1.15](03-raumdaten-service.md#115-qhctable) |
| `Dataset` | class | One immutable dataset release: all tables + manifest | [03 §1.16](03-raumdaten-service.md#116-dataset) |

### 2.9 `energytools.raumdaten.dataset` — loading and extraction → [03 §2](03-raumdaten-service.md#2-energytoolsraumdatendataset)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `load_dataset(release_id, path=None)` | function | Load a dataset release from disk (cached) | [03 §2.1](03-raumdaten-service.md#21-load_dataset) |
| `DatasetStore` | class | Registry of loaded releases | [03 §2.2](03-raumdaten-service.md#22-datasetstore) |
| `DatasetExtractor` | class | Stage-0 extraction pipeline from workbook copies | [03 §2.3](03-raumdaten-service.md#23-datasetextractor) |

### 2.10 `energytools.raumdaten.service` — data service → [03 §3](03-raumdaten-service.md#3-energytoolsraumdatenservice)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `RaumdatenService` | class | Read-only semantic query API over datasets | [03 §3.1](03-raumdaten-service.md#31-raumdatenservice) |

Methods of `RaumdatenService` (entries at [03 §3.2–3.17](03-raumdaten-service.md#32-methods)):

`list_releases`, `get_release`, `list_room_uses`, `get_room_use`, `get_room_use_profile`,
`list_parameters`, `get_parameter`, `compare_room_use_profiles`, `list_climate_stations`,
`get_climate_station`, `list_profiles`, `get_full_load_hours`, `get_qhc`, `get_sia3801`,
`validate`, `export`.

### 2.11 `energytools.raumdaten.compare` — profile comparison → [03 §4](03-raumdaten-service.md#4-energytoolsraumdatencompare)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `compare_profiles(a, b)` | function | Diff two room-use profiles (all kinds) | [03 §4.1](03-raumdaten-service.md#41-compare_profiles) |
| `ProfileDiff` | class (dataclass) | Structured comparison result | [03 §4.2](03-raumdaten-service.md#42-profilediff) |

### 2.12 `energytools.gebaeude.model` — building model → [04 §1](04-gebaeude-engine.md#1-energytoolsgebaeudemodel)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `EnergyCarrier` | class (enum) | Energieträger (Elektrizität, HEL, Erdgas, …) | [04 §1.1](04-gebaeude-engine.md#11-energycarrier) |
| `EndUse` | class (enum) | End-use categories of the Resultate table | [04 §1.2](04-gebaeude-engine.md#12-enduse) |
| `RoomRow` | class (dataclass) | One building room row (use, EBF flag, NGF, share, systems) | [04 §1.3](04-gebaeude-engine.md#13-roomrow) |
| `VentilationSystem` | class (dataclass) | One of 16 AHU systems LA01–LA16 | [04 §1.4](04-gebaeude-engine.md#14-ventilationsystem) |
| `GenerationSystem` | class (dataclass) | One generator (cooling/heating/WW) with catalog code | [04 §1.5](04-gebaeude-engine.md#15-generationsystem) |
| `BuildingProject` | class (dataclass) | Complete calculation input (project + rooms + systems) | [04 §1.6](04-gebaeude-engine.md#16-buildingproject) |
| `GenerationCatalog` | class | Generator catalog (Nutzungsgrad sheet) | [04 §1.7](04-gebaeude-engine.md#17-generationcatalog) |
| `WeightingFactors` | class (dataclass) | NEGF / PEne / THGE weighting per carrier | [04 §1.8](04-gebaeude-engine.md#18-weightingfactors) |
| `Resultate` | class | Final energy per carrier × end use + totals | [04 §1.9](04-gebaeude-engine.md#19-resultate) |
| `ValidationReport` | class (dataclass) | Errors + warnings of input validation | [04 §1.10](04-gebaeude-engine.md#110-validationreport) |

### 2.13 `energytools.gebaeude.physics` — psychrometrics → [04 §2](04-gebaeude-engine.md#2-energytoolsgebaeudephysics)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `CP_AIR`, `CP_WATER_VAPOUR`, `CP_WATER`, `HEAT_OF_VAPORIZATION`, `HEAT_OF_VAPORIZATION_100`, `AIR_DENSITY`, `MOLAR_MASS_RATIO`, `PS_0`, `DEW_POINT_P`, `DEW_POINT_N`, `DEW_POINT_K` | float constants | Physics constants of the Glück model + AHU air/water constants (cpl, cpw, cw, r0, r100, ρ, 622, 611, dew-point fit — textbook ch01 §1.1, ch04 §4.16-3) | [04 §2.1](04-gebaeude-engine.md#21-physics-constants) |
| `saturation_pressure_glueck(t)` | function | Saturation pressure after Glück (mbar) ← `Saettigungsdruck` (dead in workbook; extracted for reuse) | [04 §2.2](04-gebaeude-engine.md#22-saturation_pressure_glueck) |
| `absolute_humidity(t, rh, p)` | function | Absolute humidity (g/kg) ← `AbsFeuchte` | [04 §2.3](04-gebaeude-engine.md#23-absolute_humidity) |
| `relative_humidity(t, x, p)` | function | Relative humidity (%) ← `RelFeuchte` | [04 §2.4](04-gebaeude-engine.md#24-relative_humidity) |
| `enthalpy_from_rel_humidity(t, rh, p)` | function | Enthalpy (kJ/kg) from T/rF ← `EnthalpieR` (dead in workbook; reference-only) | [04 §2.5](04-gebaeude-engine.md#25-enthalpy_from_rel_humidity) |
| `enthalpy_from_absolute_humidity(t, x, p)` | function | Enthalpy (kJ/kg) from T/x ← `EnthalpieA` | [04 §2.6](04-gebaeude-engine.md#26-enthalpy_from_absolute_humidity) |
| `dew_point(t, rh, p)` | function | Dew point (°C) from T/rF ← `TaupunktR` (dead in workbook; reference-only) | [04 §2.7](04-gebaeude-engine.md#27-dew_point) |
| `dew_point_from_absolute_humidity(x, p)` | function | Dew point (°C) from x ← `TaupunktA` (commented out in VBA, referenced by `Berechnung LU!AQ` → `#NAME?`; reference-only) | [04 §2.8](04-gebaeude-engine.md#28-dew_point_from_absolute_humidity) |
| `temperature_from_enthalpy(h, x)` | function | Temperature (°C) from enthalpy ← `TemperaturH` | [04 §2.9](04-gebaeude-engine.md#29-temperature_from_enthalpy) |
| `wet_bulb_temperature(t, rh)` | function | Wet-bulb temperature (°C) ← `Feuchtkugel` (dead in workbook; reference-only) | [04 §2.10](04-gebaeude-engine.md#210-wet_bulb_temperature) |

### 2.14 `energytools.gebaeude.ahu` — AHU bin engine → [04 §3](04-gebaeude-engine.md#3-energytoolsgebaeudeahu)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `AhuInput` | class (dataclass) | All inputs of one AHU calculation (row-32 template) | [04 §3.1](04-gebaeude-engine.md#31-ahuinput) |
| `AhuBinResult` | class (dataclass) | Per-temperature-bin result of the psychrometric loop (incl. `case` = Fall 1–4 classification) | [04 §3.2](04-gebaeude-engine.md#32-ahubinresult) |
| `AhuResult` | class (dataclass) | Aggregated result of one AHU over all bins | [04 §3.3](04-gebaeude-engine.md#33-ahuresult) |
| `calculate_ahu(input)` | function | Runs the temperature-bin psychrometric calculation (Fall 1–4 case selection) | [04 §3.4](04-gebaeude-engine.md#34-calculate_ahu) |
| `FanModel` | class | Stage-dependent fan power (P ∝ V^2.5) | [04 §3.5](04-gebaeude-engine.md#35-fanmodel) |
| `HeatRecoveryModel` | class | WRG/KRG recovery temperature model | [04 §3.6](04-gebaeude-engine.md#36-heatrecoverymodel) |

### 2.15 `energytools.gebaeude.engine` — calculation engine → [04 §4](04-gebaeude-engine.md#4-energytoolsgebaeudeengine)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `CalculationEngine` | class | Orchestrates validate → calculate → explain over a backend | [04 §4.1](04-gebaeude-engine.md#41-calculationengine) |
| `CalculationResult` | class (dataclass) | Full result incl. versions, inputs hash, intermediates | [04 §4.2](04-gebaeude-engine.md#42-calculationresult) |
| `CalculationTrace` | class | Step-by-step explainable trace of a calculation | [04 §4.3](04-gebaeude-engine.md#43-calculationtrace) |
| `CalculationStore` | class | Persistence of results by `result_id` | [04 §4.4](04-gebaeude-engine.md#44-calculationstore) |

### 2.16 `energytools.gebaeude.backends` — calculation backends → [04 §5](04-gebaeude-engine.md#5-energytoolsgebaeudebackends)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `CalculationBackend` | class (ABC) | Backend contract (validate + calculate + identity) | [04 §5.1](04-gebaeude-engine.md#51-calculationbackend) |
| `ExcelBackend` | class | **Excel backend**: reference runtime over workbook copies (COM) | [04 §5.2](04-gebaeude-engine.md#52-excelbackend) |
| `NativeBackend` | class | **Native backend**: pure-Python ported runtime | [04 §5.3](04-gebaeude-engine.md#53-nativebackend) |

### 2.17 `energytools.gebaeude.resultate` — resultate aggregation → [04 §6](04-gebaeude-engine.md#6-energytoolsgebaeuderesultate)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `ResultateAggregator` | class | Aggregates AHU + generation results into `Resultate` | [04 §6.1](04-gebaeude-engine.md#61-resultateaggregator) |
| `weight_resultate(resultate, factors)` | function | Applies NEGF/PEne/THGE weighting | [04 §6.2](04-gebaeude-engine.md#62-weight_resultate) |

### 2.18 `energytools.export` — export layer → [05 §3](05-versioning-export.md#3-energytoolsexport)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `Exporter` | class (ABC) | Export contract (format, target, options) | [05 §3.1](05-versioning-export.md#31-exporter) |
| `JsonExporter` | class | Dataset/result → JSON (schema-annotated) | [05 §3.2](05-versioning-export.md#32-jsonexporter) |
| `CsvExporter` | class | Tabular views → CSV | [05 §3.3](05-versioning-export.md#33-csvexporter) |
| `XlsxExporter` | class | Dataset/result → XLSX workbook | [05 §3.4](05-versioning-export.md#34-xlsxexporter) |
| `PdfExporter` | class | Data-sheet PDFs (replaces `DatenblattSpeichern`) | [05 §3.5](05-versioning-export.md#35-pdfexporter) |
| `export_dataset(...)` | function | Convenience export of a dataset release | [05 §3.6](05-versioning-export.md#36-export_dataset) |
| `export_calculation(...)` | function | Convenience export of a calculation result | [05 §3.7](05-versioning-export.md#37-export_calculation) |

### 2.19 `energytools.cli` — command line → [05 §4](05-versioning-export.md#4-energytoolscli)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `main(argv=None)` | function | CLI dispatcher (`versions`, `export`, `serve`, `mcp`) | [05 §4.1](05-versioning-export.md#41-main) |
| `versions_cmd(args)` | function | Prints version info | [05 §4.2](05-versioning-export.md#42-versions_cmd) |
| `export_cmd(args)` | function | Exports dataset/result to a file | [05 §4.3](05-versioning-export.md#43-export_cmd) |

### 2.20 `energytools.api` — FastAPI layer → [06](06-fastapi-layer.md)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `Settings` | class | Runtime settings (dataset dir, backend, limits) | [06 §1](06-fastapi-layer.md#1-settings) |
| `create_app(service, engine, store, settings)` | function | FastAPI application factory | [06 §2](06-fastapi-layer.md#2-create_app) |
| `datasets_router` | router | Data-service endpoints | [06 §3](06-fastapi-layer.md#3-datasets-router) |
| `calculations_router` | router | Calculation endpoints | [06 §4](06-fastapi-layer.md#4-calculations-router) |
| `versions_router` | router | Version endpoints | [06 §5](06-fastapi-layer.md#5-versions-router) |
| Pydantic schemas | classes | Request/response models (see [06 §6](06-fastapi-layer.md#6-schemas)) | [06 §6](06-fastapi-layer.md#6-schemas) |

### 2.21 `energytools.mcp` — MCP layer → [07](07-mcp-layer.md)

| Symbol | Kind | Purpose | API entry |
|---|---|---|---|
| `create_mcp_server(service, engine)` | function | Builds the MCP server with all tools | [07 §1](07-mcp-layer.md#1-create_mcp_server) |
| `run_mcp_server(service, engine, host, port)` | function | Runs the MCP server (stdio/SSE) | [07 §2](07-mcp-layer.md#2-run_mcp_server) |
| `TOOL_REGISTRY` | dict | Tool name → implementation map | [07 §3](07-mcp-layer.md#3-tool_registry) |
| MCP tools | functions | 9 tools (see [07 §4](07-mcp-layer.md#4-mcp-tools)) | [07 §4](07-mcp-layer.md#4-mcp-tools) |

## 3. VBA → Python symbol mapping (grounding)

Every functional VBA module of both workbooks is mapped below. `→` marks the Python equivalent;
`not ported` marks deliberate exclusions (dead code, license UI, protection, print UI).

### 3.1 Raumdatenblätter (`raumdaten.xlsm`, 34 modules)

| VBA module / symbol | Observed role | Python mapping |
|---|---|---|
| `FeuchteLuft_Formeln` (`AbsFeuchte`, `EnthalpieA`, `RelFeuchte`, `TaupunktA`, `TemperaturH`, `EnthalpieR`, `Saettigungsdruck`, `TaupunktR`, `Feuchtkugel`) | Moist-air physics UDFs (not referenced by stored formulas in this workbook — assessment §1.2; the Gebaeude-Tool call analysis is in textbook ch01 §1.10) | `gebaeude.physics` (shared module: normative ports of the live UDFs, reference-only ports of the dead ones — see §2.13/part 04 §2) |
| `ErstelleResultate` (`Res_Export`, `Volll_Lüft_Export`, `Qhc_Export`) | Export of 45 room uses / 40 stations × 45 uses into result sheets | `raumdaten.service.RaumdatenService.export` + `export.XlsxExporter` (semantic export; no cell copying) |
| `Datenblatt_Handle` (`DatenblattSpeichern`, `DatenblattDruck`, `Zellen_Ausblenden_Datenblatt`, `Zellen_Einblenden_Datenblatt`) | Data-sheet PDF/print UI | `export.PdfExporter` (PDF part); print/scroll UI **not ported** |
| `Sprachänderungen` (`SprachWechsel`, `Blattnamen`, `IndexC342`, `KopfzeileBasteln`) | Language switching, sheet renaming, rich-text symbols | `common.language` + `RaumdatenService` language-aware output; sheet renaming **not ported** (no sheet names in the model) |
| `Workmode` (`Workmodus`, `Modus_unliz`, `Modus_liz`, `BlattSchutzaufheben`, `BlattSchutzSetzen`) | Protection/visibility toggles | **not ported** (Excel authoring context; assessment §8.10) |
| `basLizenzieren` / `tblLizenzieren` (incl. `SetzenAufhebenStrukturArbeitsmappe`, `EinblendenAusblendenArbeitsblätter`, `ZurücksetzenAnfangszustand`) | License UI (logic disabled in V221) | **not ported** |
| `tblBegriffe` (Worksheet_Change) | Trilingual dictionary, re-export on language change | `common.language.TrilingualText`, `raumdaten.model` labels |
| `tblDatenblatt` / `tblDatenblatt2` (CommandButton handlers) | PDF/print buttons | `export.PdfExporter` |
| `tblEingabedaten`, `tblProfile`, `tblMonats`, `tblWinterAusl`, `tblAug`, `tblVolll_Lüft`, `tblKZ_Raum_2024`, `tblFlächeE/E1/E2/L/ZW/Best`, `tblGEPAMOD`, `tblSIA3801–3804`, `tblQhc`, `tblRes_Std/Zw/Best`, `tblAnleitung` | Sheet classes (no active handlers beyond above) | Data contents → `raumdaten.model` tables (see part 03 §1); `tblSIA3801*` → `Sia3801Coefficients`/`Sia3801Result` with variant axis (DE/EN × ±Qc) |
| `Modul1` (`Makro2`), `Modul2` (`Makro1`) | Recorded button-layout macros | **not ported** |
| `DieseArbeitsmappe` | Workbook events (all commented out) | **not ported** |

### 3.2 Gebäude-Tool (`gebaeude.xlsm`, 21 modules)

| VBA module / symbol | Observed role | Python mapping |
|---|---|---|
| `FeuchteLuft_Formeln` (`AbsFeuchte`, `EnthalpieA`, `RelFeuchte`, `TemperaturH` — referenced by stored formulas) | Psychrometric UDFs used by `Berechnung LU` (call-site analysis: textbook ch01 §1.10) | `gebaeude.physics` (exact port, verified against VBA values — assessment §7.5) |
| `FeuchteLuft_Formeln` (`EnthalpieR`, `Saettigungsdruck`, `Feuchtkugel`, `TaupunktR` — not referenced; `TaupunktA` — commented out in VBA) | Dead code / commented out (textbook ch01 §1.7–§1.9) | `saturation_pressure_glueck` extracted for reuse; `enthalpy_from_rel_humidity`, `dew_point`, `dew_point_from_absolute_humidity`, `wet_bulb_temperature` ported **reference-only** (part 04 §2.5/2.7/2.8/2.10) |
| `Fallunterscheidung` (`Fall1Tzul`, `Fall1xzul`, `Fall2Tzul`, `Fall2xzul`) | **Live code**: case selection for Zuluft IST values, referenced by `Berechnung LU!BB:BE` (61×2 interval rows — textbook README §0.7-10, ch04 §4.9; early assessment misjudged it as dead) | Ported as the **Fall 1–4 case selection inside `ahu.calculate_ahu`** (`AhuBinResult.case`, part 04 §3.2/§3.4); must be verified against the Excel oracle (`Berechnung LU` rows 254–260) |
| `Lüftung_Resultate` (`Lüftung_Resultate`) | Copies AHU row-32 result into per-system rows | `ahu.calculate_ahu` + `engine.CalculationEngine` (no copy/paste; mind the documented `Lüftung!U32:Z32` wiring shift — textbook ch04 §4.14-8) |
| `Blatthinzufügen` (`Hinzufügen`, `Entfernen`) | Add/remove building sheets | `BuildingProject.rooms` as data (no sheets) — **not ported** as UI |
| `Bearbeitungsmodus` (`Schutz`) | Protection toggles | **not ported** |
| `Sprachänderungen` | Language handling | `common.language` |
| `basLizenzieren` / `tblLizenzieren` | License UI (disabled) | **not ported** |
| `tblGebaeude` (Worksheet_Change, commented out) | Auto recalc on station change | `engine.CalculationEngine` recalculates on demand |
| `tblBerechnungLU`, `tblErzeugung`, `tblKlimadaten`, `tblLueftung`, `tblNutzungsgrad`, `tblQhc`, `tblRaum`, `tblResultate`, `tblStd`, `tblBegriffe`, `tblAnleitung` | Sheet classes (no active handlers) | Contents → `gebaeude.model` (rooms, systems, catalog, climate) and `raumdaten` lookups |
| `DieseArbeitsmappe` | Workbook events (all commented out) | **not ported** |

### 3.3 Sheet contents → model tables

| Workbook sheet(s) | Model target |
|---|---|
| `Eingabedaten`, `Datenblatt`, `Begriffe` (labels), `KZ_Raum_2024` | `raumdaten.model`: `RoomUse`, `Parameter`, `RoomUseProfile`, `ParameterValue` |
| `Profile` (hourly rows 58–86, annual rows 605–976) | `HourlyProfile`, `WeeklyProfile`, `FullLoadHoursTable` |
| `Monatswerte`, `Winter_Auslegung`, `Aug_Auslegung`, `Klimadaten` | `ClimateStation` / `ClimateData` (40 stations; bin hours for the AHU engine) |
| `Volll_Lüft`, `Std` | `FullLoadHoursTable` (standard-version axis, provenance comment `Std!L2`) |
| `Qhc_Klimastat` | `QhcTable` |
| `Fläche-*`, `GEPAMOD` | `AreaTable`, `BuildingCategoryMapping` |
| `SIA 380-1` + `_Qc`, `_EN`, `_Qc_EN` | `Sia3801Coefficients`, `Sia3801Result` (variant axis: language × cooling) |
| `Gebäude` | `BuildingProject`, `RoomRow` |
| `Lüftung` (+ row 32 template) | `VentilationSystem`, `AhuInput` |
| `Nutzungsgrad` | `GenerationCatalog` (KE01–KE06, WE01+, WW types) |
| `Erzeugung` | `GenerationSystem` |
| `Resultate` | `Resultate` (carriers × end uses, NEGF/PEne/THGE weighting) |
