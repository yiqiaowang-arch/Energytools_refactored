# API Reference — Calculation Engine

**Module:** `energytools.engine` · **Doc set 02 (API Reference)** · Back to [index](README.md) ·
Foundation: [02-common-foundation.md](02-common-foundation.md) · Data:
[03-raumdaten-service.md](03-raumdaten-service.md)

The calculation engine is the digital replacement of the `2024_Gebaeude-Tool_dfi_V221.xlsm`
workbook: you build a `BuildingInput` (rooms, ventilation systems, generation systems, climate
station), hand it to [`Engine.calculate`](#engine--calculationengine), and read a fully
versioned, explainable `Results` object. The physical core (psychrometrics, the AHU
temperature-bin method, building aggregation) lives in `energytools.engine.native` and is
available directly to advanced users.

> **Which parts do you need?** For a typical project: `Engine` (or its alias
> `CalculationEngine`), `BuildingInput`, `RoomRow`, `VentilationSystem`, `Results`, and the
> `ValueKind` enum. That is the ✅ section below. The ⚙ symbols (`EngineBase`, `StubBackend`,
> `CalculationStore`, `engine.native.*`) are for backend development and low-level physics.

---

## In this page

- [Quickstart](#quickstart) — build an input, calculate, read results
- [Classes](#classes) — `Engine`, `BuildingInput`, `Results`, backends
- [Functions and constants](#functions-and-constants) — `DEFAULT_MODEL`
- [Native module (advanced)](#native-module-advanced) — psychrometrics, AHU, aggregation
- [What to import for a new project](#what-to-import-for-a-new-project)

---

## Quickstart

### 1. Install

```bash
# pixi (recommended, contributors)
pixi install

# or plain pip (Python >= 3.11)
pip install -e .
```

The engine itself needs no extras. The dataset it calculates against comes from part
[03](03-raumdaten-service.md) (the `data` extra covers the loader).

### 2. Build the input

`BuildingInput` is the validated, immutable calculation request. Rooms reference the 45
standard room uses by **nutzid (1–45) or SIA code** (`"3.01"`); ventilation systems use the
workbook's `LA01`–`LA16` ids; the climate station is 1–40. The real-field names follow the
workbook sheets: `ebf`/`ngf` (Gebäude C/D), `lueftung_system` (L), `gekuehlt`/`beheizt`
(P/S), `wrg`/`kuehlfall_t`/`heizfall_t` (Lüftung L/M/N), `catalog_code`/`coverage`/`losses`
(Erzeugung A/F/H).

```python
from datetime import date
from energytools.engine import (
    BuildingInput, RoomRow, VentilationSystem, GenerationSystem,
)

project = BuildingInput(
    name="Beispiel",
    author="Max Muster",
    date=date(2025, 1, 15),
    climate_station_id=40,                      # Zürich-MeteoSchweiz
    value_kind="zielwert",                      # Standard | Zielwert | Bestand
    rooms=(
        RoomRow(name="Büro 1", room_use_id="3.01", ebf=True, ngf=1200.0,
                lueftung_system="LA03", gekuehlt=True, beheizt=True),
        RoomRow(name="Sitzungszimmer", room_use_id="3.03", ebf=True, ngf=300.0,
                share=0.5, beheizt=True),
    ),
    ventilation=(
        VentilationSystem(id="LA03", room_use="3.01", regulation="2-stufig",
                          volume_flow_standard=4000.0, sfp=1.8,
                          fan_power=7.5, full_load_hours=3290.0, wrg=0.7,
                          kuehlfall_t=20.0, heizfall_t=21.0),
    ),
    generation=(
        GenerationSystem(id="WE2", kind="heating", catalog_code="WE02",
                         coverage=0.5, losses=0.1, nominal_power=60.0),
        GenerationSystem(id="W2", kind="ww", catalog_code="W13",
                         coverage=1.0, losses=0.4),
    ),
)

print(project.validate().valid)     # True — hard errors are reported, not raised
print(project.total_ngf())          # 1350.0  (m²)
```

### 3. Calculate

```python
from energytools.engine import Engine, NativeBackend

engine = Engine()                                   # in-memory result store
result = engine.calculate(project, "V221", "1.0.0",
                          backend=NativeBackend())  # real physics, real dataset
```

`calculate` validates the input first, then runs the backend and **stores** the result. The
default backend is `StubBackend` (deterministic structural aggregation — energy placeholders,
no physics); pass `NativeBackend()` for the real calculation: psychrometrics, the AHU
temperature-bin engine (``Berechnung LU``), the building aggregation and the `Resultate`
summary over the V221 dataset. (The reference `ExcelBackend` arrives in a later milestone.)

```python
result = engine.calculate(project, "V221", "1.0.0")  # default: StubBackend
```

### 4. Read the results

```python
print(result.totals)
# {'ngf_m2': 1500.0, 'ebf_m2': 1650.0, 'rooms': 2, 'ventilation_systems': 1,
#  'geraete_mwh': 22.644, 'fan_energy_mwh': 24.675, 'endenergie_total_mwh': 64.675, ...}

print(result.per_carrier)            # {'el': 51.883, 'erdgas': 12.792}  (MWh/a, real energies)
print(result.backend)                # 'native@0.1.0'
print(result.versions.as_dict())
# {'dataset': 'V221', 'model': '1.0.0', 'implementation': '0.1.0', 'climate': 'meteoschweiz-2024'}
print(result.assumptions[0])         # documents the native-engine defaults
```

> The workbook's `ngf_m2` total is the **raw** NGF sum (Gebäude!D35 = SUM(D12:D32)); the
> model helper `project.total_ngf()` applies `share` (the effective area). The aggregation
> reproduces the workbook. Values above are the actual output of this Quickstart input.

Every result is reproducible and explainable:

```python
trace = engine.explain(result.trace_id)             # trace_id == result_id
print([step.id for step in trace.steps])
# ['validate', 'rooms', 'ventilation', 'generation', 'totals', 'resultate']

again = engine.get_result(result.result_id)         # stored results are reloadable
assert again == result
```

---

<a id="1-energytoolsgebaeudemodel"></a>
<a id="11-energycarrier"></a>
<a id="12-enduse"></a>
<a id="17-generationcatalog"></a>
<a id="18-weightingfactors"></a>
<a id="19-resultate"></a>
## Classes

<a id="4-energytoolsgebaeudeengine"></a>
<a id="41-calculationengine"></a>
<a id="engine--calculationengine"></a>
### `Engine` / `CalculationEngine` ✅ (user-facing)

`class Engine` — the orchestration facade: **validate → calculate → explain → retrieve**.
`CalculationEngine` is a type alias for `Engine` (kept for the API-reference name); use either.

**Methods:**

| Method | Signature | Returns | One-liner |
|---|---|---|---|
| `validate_input` | `(input_: BuildingInput, dataset: str, model_release: str) -> ValidationReport` | `ValidationReport` | Structural + domain validation and version compatibility; never raises. |
| `calculate` | `(input_, dataset, model_release, backend=None, result_id=None) -> Results` | `Results` | Validate, run the backend, store the result, return it. |
| `explain` | `(result_id: str) -> CalculationTrace` | `CalculationTrace` | The stored step-by-step trace of a result. |
| `get_result` | `(result_id: str) -> Results` | `Results` | The stored result. |

**Raises:** `ModelVersionMismatchError` (unknown model / incompatible dataset),
`CalculationInputError` (hard validation errors), `BackendError` / `CalculationError`
(runtime failures). All engine exceptions come from `energytools.engine.errors` — see
[02-common-foundation.md](02-common-foundation.md) for the exception classes.

```python
engine = Engine()
report = engine.validate_input(project, "V221", "1.0.0")
print(report.valid)                  # True
```

The engine resolves versions explicitly — `"latest"` is never resolved silently inside a
calculation; the concrete ids are recorded in `Results.versions`:

```python
engine.calculate(project, "V221", "latest")      # resolves to the newest installed model
engine.calculate(project, "V222", "1.0.0")       # → ModelVersionMismatchError
```

<a id="16-buildingproject"></a>
### `BuildingInput` ✅ (user-facing)

`@dataclass(frozen=True) class BuildingInput` — the complete, validated calculation request.
Construct it directly; `validate()` reports problems instead of raising.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | `str` | **yes** | Project name. |
| `rooms` | `tuple[RoomRow, ...]` | **yes** | At least one room. |
| `author` | `str \| None` | no | Author name. |
| `date` | `date \| None` | no | Project date. |
| `climate_station_id` | `int` | no (default `1`) | Climate station 1–40. |
| `value_kind` | `ValueKind` | no (default `STANDARD`) | `standard` / `zielwert` / `bestand`. |
| `ventilation` | `tuple[VentilationSystem, ...]` | no | AHU systems `LA01`–`LA16`. |
| `generation` | `tuple[GenerationSystem, ...]` | no | Generators (cooling/heating/ww). |
| `note` | `str \| None` | no | Free-text note. |

**Methods:** `validate() -> ValidationReport` (climate station 1–40, room uses known, LA ids
`LA01`–`LA16`, no duplicate system ids), `total_ngf() -> float` (m²), `total_ebf_area() ->
float` (m²), `canonical_json() -> str`, `inputs_hash() -> str` (SHA-256 of the canonical
input), `as_dict()` / `from_dict()`.

<a id="13-roomrow"></a>
### `RoomRow` ✅ (user-facing)

`@dataclass(frozen=True) class RoomRow` — one building room row.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | `str` | **yes** | Room label. |
| `room_use_id` | `int \| str` | **yes** | nutzid (1–45) or SIA code (`"1.01"`). |
| `ebf` | `bool` | **yes** | Counts toward the energy reference area (EBF). |
| `ngf` | `float` | **yes** | Net floor area (m²). |
| `share` | `float \| None` | no | Share of the total NGF (0–1). |
| `geraete` / `prozessanlagen` / `beleuchtung` | `float \| None` | no | Power densities (W/m²). |
| `lueftung_system` | `str \| None` | no | LA id of the served AHU system. |
| `lueftung_volume_flow` | `float \| None` | no | Volume flow (m³/h). |
| `gekuehlt` / `beheizt` / `warmwasser` | `bool` | no | Demand flags. |

```python
room = RoomRow(name="Büro 1", room_use_id="1.01", ebf=True, ngf=1200.0,
               geraete=8.0, lueftung_system="LA03")
print(room.effective_area())          # 1200.0  (share × ngf, or ngf)
```

<a id="14-ventilationsystem"></a>
### `VentilationSystem` ✅ (user-facing)

`@dataclass(frozen=True) class VentilationSystem` — one of the 16 workbook systems `LA01`–`LA16`.

| Field | Type | Meaning |
|---|---|---|
| `id` | `str` | System id, `"LA01"`…`"LA16"` (required). |
| `room_use` | `str \| None` | Served room use (SIA code). |
| `volume_flow_standard` / `volume_flow_prozess` / `volume_flow_projekt` | `float \| None` | Volume flows (m³/h). |
| `sfp` | `float \| None` | Specific fan power (W/(m³/h)). |
| `fan_power` | `float \| None` | Fan power (kW). |
| `regulation` | `str \| None` | `"1-stufig" \| "2-stufig" \| "stufenlos"`. |
| `full_load_hours` | `float \| None` | Full-load hours (h/a). |
| `wrg` | `float \| None` | WRG recovery ratio 0–1. |
| `kuehlfall_t` / `heizfall_t` | `float \| None` | Kühlfall/Heizfall setpoints (°C). |
| `humidity_setpoints` | `dict[str, float] \| None` | Humidity setpoints. |

```python
sys = VentilationSystem(id="LA03", regulation="2-stufig", volume_flow_standard=4000.0,
                        sfp=1.8, wrg=0.7)
print(sys.effective_volume_flow())    # 4000.0  (Projekt → Prozess → Standard priority)
```

<a id="15-generationsystem"></a>
### `GenerationSystem` ✅ (user-facing)

`@dataclass(frozen=True) class GenerationSystem` — one generator of the `Erzeugung` sheet.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | `str` | **yes** | Generator id (e.g. `"KE1"`). |
| `kind` | `str` | **yes** | `"cooling" \| "heating" \| "ww"`. |
| `catalog_code` | `str` | **yes** | `Nutzungsgrad` catalog code (KE/WE/WW pattern). |
| `coverage` | `float` | **yes** | Deckungsgrad 0–1. |
| `losses` | `float` | **yes** | Speicher-/Verteilverluste 0–1. |
| `nominal_power` | `float \| None` | no | Nominal power (kW). |

<a id="42-calculationresult"></a>
### `Results` ✅ (user-facing)

`@dataclass(frozen=True) class Results` — the complete, reproducible outcome of one
calculation. `as_dict()` is JSON-ready (the `POST /calculations` response shape).

| Attribute | Type | Meaning |
|---|---|---|
| `result_id` | `str` | Stable id of the stored result. |
| `versions` | `VersionInfo` | dataset / model / implementation / climate quadruple. |
| `inputs_hash` | `str` | SHA-256 of the canonical input JSON. |
| `input_` | `BuildingInput` | The input that produced this result. |
| `backend` | `str` | Backend identity, e.g. `"stub@0.1.0"`. |
| `per_room` | `dict[str, Any]` | Per-room KPIs keyed by room name. |
| `per_system` | `dict[str, Any]` | Per-system values keyed by LA id. |
| `per_carrier` | `dict[str, float]` | Totals per Energieträger. |
| `totals` | `dict[str, float]` | Building totals (ngf, ebf, rooms, …). |
| `intermediates` | `dict[str, Any]` | Intermediate values (stub: data sources). |
| `assumptions` | `tuple[str, ...]` | Documented assumptions of the run. |
| `warnings` | `tuple[str, ...]` | Warnings (e.g. placeholder values). |
| `overridden_values` | `tuple[dict, ...]` | Values overridden vs. the catalog. |
| `computed_at` | `datetime` | UTC timestamp. |
| `trace` | `CalculationTrace \| None` | The explain trace. |
| `trace_id` | *(property)* | Alias of `result_id` — pass it to `Engine.explain`. |

```python
print(result.per_room["Büro 1"])
# {'room_use_id': '1.01', 'ebf': True, 'ngf_m2': 1200.0, 'effective_area_m2': 1200.0,
#  'geraete_kw': 9.6, 'beleuchtung_kw': 12.0, 'installed_electric_kw': 21.6, ...}
```

<a id="43-calculationtrace"></a>
### `CalculationTrace` ✅ (user-facing)

`@dataclass(frozen=True) class CalculationTrace` — the step-by-step trace of one calculation
(the `GET /calculations/{id}/explain` payload). `steps` is a tuple of `TraceStep`
(`id`, `kind`, `label`, `inputs`, `formula`, `outputs`, `provenance`); `step(step_id)`
returns one step (raises `KeyError` for unknown ids).

<a id="110-validationreport"></a>
### `ValidationReport` ✅ (user-facing)

`@dataclass(frozen=True) class ValidationReport` — hard errors (invalid) and warnings
(suspicious but acceptable). `valid` is `True` when there are no errors; `as_dict()` is
JSON-ready.

<a id="5-energytoolsgebaeudebackends"></a>
<a id="51-calculationbackend"></a>
### `EngineBase` ⚙ (internal — writing custom backends)

`class EngineBase(ABC)` — the backend contract. A backend executes one **validated**
calculation and reports its identity (`name`, `version`). Implement `calculate` and `validate`
to plug a custom backend into `Engine`.

```python
from energytools.engine import EngineBase, Results, ValidationReport

class MyBackend(EngineBase):
    name = "my-backend"
    version = "0.1.0"

    def validate(self, input_, dataset):        # capability check
        return ValidationReport()

    def calculate(self, input_, dataset, model_release) -> Results:
        ...  # must return a full Results with a trace
```

<a id="52-excelbackend"></a>
<a id="53-nativebackend"></a>
### `StubBackend` ⚙ (internal — default, structural only)

`class StubBackend(EngineBase)` — the deterministic structural backend (`name = "stub"`).
It computes **no physics**: it aggregates per-room effective areas and installed electric
power, per-system effective volume flows and building totals so the engine I/O contract and
the explain trace can be exercised without the model. Energy values are placeholders —
stated explicitly in `assumptions`/`warnings`.

### `NativeBackend` ⚙ (internal — the real pure-Python runtime)

`class NativeBackend(EngineBase)` — the real calculation backend (`name = "native"`). It
plugs the verified native model — psychrometrics, the AHU temperature-bin engine
(`Berechnung LU`), the building aggregation and the `Resultate` summary — into the engine
and consumes the **real V221 dataset**: the room KPI intensities come from the dataset
profiles (the `Res` matrix), each ventilation system drives one `AhuInput` with the station
climate (temperature-bin hours, humidity, pressure) from `ds.climate` and the full-load
hours from the `Volll_Lüft` table, and the generators resolve through the built-in
`Nutzungsgrad` catalogue. Construct it with `NativeBackend()` (dataset dir defaults to
`data/datasets`) and pass it to `Engine.calculate(..., backend=...)`.

<a id="44-calculationstore"></a>
### `CalculationStore` ⚙ (internal)

`class CalculationStore` — persistence of results by `result_id`. In-memory when `directory`
is `None`; otherwise every result is also written as `<result_id>.json` so a fresh process can
reload it. Methods: `save(result)`, `get(result_id)`, `list(limit=100)`.

```python
from energytools.engine import CalculationStore, Engine

store = CalculationStore(directory=".tmp/results")
engine = Engine(store=store)
```

---

## Functions and constants

### `DEFAULT_MODEL` ✅ (user-facing)

`DEFAULT_MODEL: ModelRelease` — the model release installed with this milestone: model
`1.0.0`, compatible with the `V221` dataset release and the `meteoschweiz-2024` climate data.
This is what `Engine()` uses when you do not pass `models`.

```python
from energytools.engine import DEFAULT_MODEL
print(DEFAULT_MODEL.id)                     # 1.0.0
print(sorted(DEFAULT_MODEL.compatible_dataset_releases))   # ['V221']
```

There is currently no `example_building()` helper in the public API; the Quickstart above is
the canonical minimal example (the tests use the same shape via `tests/helpers.py`).

---

<a id="2-energytoolsgebaeudephysics"></a>
## Native module (advanced)

`energytools.engine.native` is the pure-Python port of the workbook's physical model — the
runtime of the `NativeBackend`. These are **low-level physics / computation primitives**,
usually called by the engine internally; advanced users can call them directly. All functions
are verified against the Excel-oracle golden files in `data/golden/`.

<a id="21-physics-constants"></a>
<a id="22-saturation_pressure_glueck"></a>
<a id="23-absolute_humidity"></a>
<a id="24-relative_humidity"></a>
<a id="25-enthalpy_from_rel_humidity"></a>
<a id="26-enthalpy_from_absolute_humidity"></a>
<a id="27-dew_point"></a>
<a id="28-dew_point_from_absolute_humidity"></a>
<a id="29-temperature_from_enthalpy"></a>
<a id="210-wet_bulb_temperature"></a>
<a id="psychrometrics--moist-air-functions-advanced"></a>
### `psychrometrics` — moist-air functions (advanced)

Port of `FeuchteLuft_Formeln.bas`. Unit conventions: `t` in °C, `x` in g/kg, `p` in mbar,
`h` in kJ/kg, relative humidity as a **decimal fraction 0–1** (except `wet_bulb_temperature`,
which takes % 0–100 exactly like the VBA).

| Function | Signature | Returns | One-liner |
|---|---|---|---|
| `saturation_pressure_glueck` | `(t: float) -> float` | `float` | Saturation vapour pressure after Glück in mbar. |
| `absolute_humidity` | `(t, rh, p) -> float` | `float` | Absolute humidity in g/kg (VBA `AbsFeuchte`). |
| `relative_humidity` | `(t, x, p) -> float` | `float` | Relative humidity as a decimal fraction (VBA `RelFeuchte`). |
| `enthalpy_from_rel_humidity` | `(t, rh, p) -> float` | `float` | Enthalpy in kJ/kg (VBA `EnthalpieR`, reference-only). |
| `enthalpy_from_absolute_humidity` | `(t, x, p) -> float` | `float` | Enthalpy in kJ/kg (VBA `EnthalpieA`). |
| `dew_point` | `(t, rh, p) -> float` | `float` | Dew-point temperature in °C (VBA `TaupunktR`, reference-only). |
| `dew_point_from_absolute_humidity` | `(x, p) -> float` | `float` | Dew point from x/p (VBA `TaupunktA`, reference-only). |
| `temperature_from_enthalpy` | `(h, x) -> float` | `float` | Temperature in °C from enthalpy (VBA `TemperaturH`). |
| `wet_bulb_temperature` | `(t, rh) -> float` | `float` | Wet-bulb temperature in °C (VBA `Feuchtkugel`, reference-only; rh in %). |

Module constants: `CP_AIR = 1.006`, `CP_WATER_VAPOUR = 1.86`, `CP_WATER = 4.19`,
`HEAT_OF_VAPORIZATION = 2501.6`, `HEAT_OF_VAPORIZATION_100 = 2256.0`, `AIR_DENSITY = 1.15`,
`MOLAR_MASS_RATIO = 622`, `PS_0 = 611`, `DEW_POINT_P = 2.8858`, `DEW_POINT_N = 8.02`,
`DEW_POINT_K = 1.098`.

```python
from energytools.engine.native import psychrometrics as ps

ps.saturation_pressure_glueck(20.0)          # 23.3673815296201   mbar
ps.absolute_humidity(20.0, 0.5, 1013.0)      # 7.2577022751807725 g/kg
ps.enthalpy_from_absolute_humidity(20.0, 7.28, 1013.0)   # 38.602464 kJ/kg
```

**Raises:** `PsychrometricError` (from `energytools.common.errors`) on out-of-domain inputs —
the cases where the VBA returned `"Fehler"` (rh outside 0–1, p ≤ 0, x < 0, NaN).

<a id="3-energytoolsgebaeudeahu"></a>
<a id="31-ahuinput"></a>
<a id="32-ahubinresult"></a>
<a id="33-ahuresult"></a>
<a id="34-calculate_ahu"></a>
<a id="35-fanmodel"></a>
<a id="36-heatrecoverymodel"></a>
### `ahu` — AHU temperature-bin engine (advanced)

Port of the `Berechnung LU` sheet: the year-round psychrometric calculation of **one**
air-handling unit with the temperature-bin method (61 bins, t_A = −25…+35 °C).

| Symbol | Kind | Purpose |
|---|---|---|
| `AhuInput` | `@dataclass(frozen=True)` | All inputs of one AHU calculation (system, climate bins, IST block, temperature curves). Defaults match the workbook example LA01 (Zürich-MeteoSchweiz). |
| `compute_ahu_annual` | `(inp: AhuInput) -> AhuAnnualResult` | Annual summary (rows 254–260): `luftkuehlung_kwh`, `lufterwaermung_kwh`, `ventilator_kwh`, `total_kwh`, power maxima, water. |
| `compute_ahu_bins` | `(inp) -> tuple[AhuBinResult, ...]` | The 61 per-bin state results. |
| `compute_bin_hours` | `(climate_hours, full_load_hours) -> tuple[float, ...]` | Formula 1: annual operating hours per bin. |
| `compute_fan_model` | `(inp) -> FanModelResult` | Formula 10: staged fan powers, motor efficiencies, annual average power. |
| `AhuBinResult` | `@dataclass(frozen=True)` | One bin: psychrometric states, Fall 1–4 case, per-bin treatment energies (MWh). |
| `AhuAnnualResult` | `@dataclass(frozen=True)` | Annual energies (kWh) and powers (kW) + `fan` model. |
| `FanModelResult` | `@dataclass(frozen=True)` | Fan stages, motor efficiencies, annual power. |

```python
from energytools.engine.native.ahu import AhuInput, compute_ahu_annual

annual = compute_ahu_annual(AhuInput())          # default LA01 example
print(round(annual.total_kwh, 1))                # depends on supplied bin hours
print(round(annual.ventilator_kwh, 1))
```

Note: `AhuInput()` defaults to zero bin hours (safe no-op). Feed the station's
`bin_hours`/`bin_humidity_ratio` (from the dataset climate block or the golden files) to get
real annual energies; the golden case-02 (Zürich-MeteoSchweiz) reproduces the workbook totals
`total_kwh ≈ 32301.6`, `ventilator_kwh ≈ 26765.1`, `lufterwaermung_kwh ≈ 3786.3` at rel 1e-6.

<a id="6-energytoolsgebaeuderesultate"></a>
<a id="61-resultateaggregator"></a>
<a id="62-weight_resultate"></a>
### `aggregation` — building aggregation and `Resultate` summary (advanced)

Port of the room-KPI derivation (`Gebäude!F12:W32`), the ventilation/generation aggregation
and the final-energy matrix by Energieträger (`Resultate!D7:U15`).

| Symbol | Kind | Purpose |
|---|---|---|
| `aggregate` | `(inp: AggregationInput) -> AggregationResult` | Run the full chain: rooms → ventilation → generation → Resultate. |
| `compute_room_row` | `(room, value_kind, lookup, total_ngf, row_index) -> RoomResult` | One room row from the KPI lookup. |
| `res_column` | `(target, value_kind) -> int` | Res matrix column for a target column and value kind. |
| `AggregationInput` | `@dataclass(frozen=True)` | Everything the aggregation needs beyond `BuildingInput` (KPI lookup, AHU results, generation groups, weights). |
| `AggregationResult` | `@dataclass(frozen=True)` | Rooms, totals, ventilation, generation, Resultate matrix + weighted indicators. |
| `KpiLookup` | `class` | The room-KPI interface (`Res` matrix + `Std` table); implement or use `ResMatrixKpiProvider` / `DatasetResLookup`. |
| `ResMatrixKpiProvider` | `@dataclass(frozen=True)` | Dict-backed `KpiLookup` implementation. |
| `DatasetResLookup` | `class` | Dataset-backed `KpiLookup` over a V221 package (full `Res` matrix + `Std` intensities). |
| `GenerationCatalog` | `class` | The `Nutzungsgrad` catalogue lookup (by group kind + name). |
| `NutzungsgradCatalog` / `NUTZUNGSGRAD_CATALOG` | `class` / `const` | The built-in catalogue (KE01–06, WE01–16, W01–13 with η and Energieträger, from `Nutzungsgrad!C3:G42`). |
| `RESULTATE_CARRIERS` / `RESULTATE_USES` / `RES_SELECTORS` / `DEFAULT_WEIGHTS` | constants | Workbook matrix conventions (carrier rows, use columns, Res column selectors, NEGF/PEne/THGE weights). |

```python
from energytools.engine.native import aggregation
print(aggregation.RESULTATE_CARRIERS)
# ('El', 'HEL', 'Gas', 'Pell', 'HSch', 'StH', 'Bio', 'FW')
```

**Raises:** `KpiLookupError` (a `KeyError`) when the KPI lookup cannot provide a needed
value; `KeyError` when a generator name is absent from the catalogue.

---

## What to import for a new project

```python
# The engine — everything a typical project needs
from energytools.engine import (
    Engine,                # or CalculationEngine (alias)
    BuildingInput,         # the calculation request
    RoomRow,
    VentilationSystem,
    GenerationSystem,
    NativeBackend,         # the real (native) calculation backend
    Results,               # what calculate() returns
    CalculationTrace,      # explain() payload
    ValueKind,             # standard / zielwert / bestand
)

# The dataset it calculates against (part 03)
from energytools.raumdaten import load_dataset

# Errors to catch
from energytools.engine.errors import (
    EnergyToolsError,            # engine error base (note: engine-specific hierarchy)
    CalculationInputError,       # invalid building input
    ModelVersionMismatchError,   # incompatible dataset/model versions
    CalculationError,            # runtime failure / unknown result id
)
```

Typical flow: `load_dataset("V221")` (part [03](03-raumdaten-service.md)) → build a
`BuildingInput` → `Engine().calculate(project, "V221", "1.0.0")` → read `Results.totals` /
`per_carrier` / `versions` → keep `result_id` for `explain` / `get_result`.
