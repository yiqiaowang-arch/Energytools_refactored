# Part 04 — API Reference: `energytools.gebaeude` (Calculation Engine)

**Document set 02** · Target-state design specification · Back to [index](README.md) ·
Inventory: [01-package-inventory.md](01-package-inventory.md) · Foundation:
[02-common-foundation.md](02-common-foundation.md) · Data:
[03-raumdaten-service.md](03-raumdaten-service.md)

The Gebäude calculation engine: deterministic early-design energy model (assessment §2: building
inputs → room KPI aggregation → AHU temperature-bin psychrometric calculation → generation →
resultate). This part covers the building model (§1), the psychrometric physics port (§2), the
AHU bin engine (§3), the orchestration engine (§4), the **Excel and native backends** (§5) and
the resultate aggregation (§6).

---

## 1. `energytools.gebaeude.model`

### 1.1 `EnergyCarrier`

`class EnergyCarrier(enum.Enum)`

- **Purpose:** The Energieträger of the `Resultate` table (assessment §2.1: El, HEL, Erdgas, …).
- **Members:** `ELECTRICITY = "el"`, `HEATING_OIL = "hel"`, `NATURAL_GAS = "erdgas"`,
  `WOOD = "holz"`, `DISTRICT_HEATING = "fernwaerme"`, `DISTRICT_COOLING = "fernkaelte"`,
  `SOLAR = "solar"`, `OTHER = "andere"`.
- **Inputs:** — (enum members; `parse` takes `value: str`).
- **Outputs:** the enum member; `parse` returns `EnergyCarrier`.
- **Methods:**
  - **`parse(value: str) -> EnergyCarrier`** — accepts German workbook labels
    (`"Elektrizität"`, `"HEL"`, `"Erdgas"`) and the codes above. **Raises:** `ValueError`.
- **Example:**
  ```python
  EnergyCarrier.parse("Elektrizität") is EnergyCarrier.ELECTRICITY
  ```

### 1.2 `EndUse`

`class EndUse(enum.Enum)`

- **Purpose:** End-use categories of the `Resultate` table (assessment §2.1): Allg.
  Gebäudetechnik, Geräte, Prozessanlagen, Beleuchtung, Lüftung, Kühlung, Heizung, Warmwasser.
- **Members:** `ALLGEMEINE_GEBAEUDETECHNIK = "allg_gebaeudetechnik"`, `GERAETE = "geraete"`,
  `PROZESSANLAGEN = "prozessanlagen"`, `BELEUCHTUNG = "beleuchtung"`, `LUEFTUNG = "lueftung"`,
  `KUEHLUNG = "kuehlung"`, `HEIZUNG = "heizung"`, `WARMWASSER = "warmwasser"`.
- **Inputs:** — (enum members; `parse` takes `value: str`).
- **Outputs:** the enum member; `parse` returns `EndUse`.
- **Methods:**
  - **`parse(value: str) -> EndUse`** — accepts German labels and the codes above.
    **Raises:** `ValueError`.
- **Example:**
  ```python
  EndUse.parse("Kühlung") is EndUse.KUEHLUNG
  ```

### 1.3 `RoomRow`

`@dataclass(frozen=True) class RoomRow`

- **Purpose:** One building room row of the `Gebäude` sheet (assessment §2.1: room use, EBF
  flag, NGF, share, per-use power/energy for Geräte/Prozessanlagen/Beleuchtung/Lüftung,
  Raumkühlung/Heizung flags, Warmwasser).
- **Inputs (constructor):** `name: str` (row label), `room_use_id: int | str` (nutzid or SIA
  code), `ebf: bool` (counts toward EBF), `ngf: Quantity` (m²), `share: float | None = None`
  (share of the total NGF), `geraete: Quantity | None`, `prozessanlagen: Quantity | None`,
  `beleuchtung: Quantity | None`, `lueftung_system: str | None` (LA id, e.g. `"LA03"`),
  `lueftung_volume_flow: Quantity | None` (m³/h), `gekuehlt: bool = False`,
  `beheizt: bool = True`, `warmwasser: bool = False`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; derived values are returned by its methods).
- **Methods:**
  - **`effective_area() -> Quantity`** — `share × ngf` when share is set, else `ngf`.
- **Raises:** `ValueError` for negative areas or unknown flags.
- **Example:**
  ```python
  RoomRow(name="Büro 1", room_use_id="1.01", ebf=True, ngf=Quantity(1200.0, "m2"),
          geraete=Quantity(8.0, "W/m2"), lueftung_system="LA03",
          lueftung_volume_flow=Quantity(4000.0, "m3/h"))
  ```

### 1.4 `VentilationSystem`

`@dataclass(frozen=True) class VentilationSystem`

- **Purpose:** One of the **16 ventilation systems LA01–LA16** of the `Lüftung` sheet
  (assessment §2.1): volume flows (Standard/Prozess/Projekt), SFP, fan power, regulation,
  full-load hours, WRG %, setpoints and humidity setpoints.
- **Inputs (constructor):** `id: str` (`"LA01"`…`"LA16"`), `room_use: str | None` (served use),
  `volume_flow_standard: Quantity | None` (m³/h), `volume_flow_prozess: Quantity | None`,
  `volume_flow_projekt: Quantity | None`, `sfp: Quantity | None` (W/(m³/s) or W/(m³/h) — unit
  explicit), `fan_power: Quantity | None` (kW), `regulation: str | None`
  (`"1-stufig" | "2-stufig" | "stufenlos"`), `full_load_hours: Quantity | None` (h/a),
  `wrg: float | None` (0–1 recovery ratio), `kuehlfall_t: Quantity | None` (°C setpoint),
  `heizfall_t: Quantity | None`, `humidity_setpoints: dict[str, Quantity] | None`
  (e.g. `{"x_soll": …, "rh_soll": …}`).
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; derived values are returned by its methods).
- **Methods:**
  - **`effective_volume_flow() -> Quantity`** — Projekt → Prozess → Standard priority.
- **Raises:** `ValueError` if `wrg` outside 0–1.
- **Example:**
  ```python
  VentilationSystem(id="LA03", regulation="2-stufig",
                    volume_flow_standard=Quantity(4000.0, "m3/h"),
                    sfp=Quantity(1.8, "W/(m3/h)"), wrg=0.7,
                    kuehlfall_t=Quantity(26.0, "°C"), heizfall_t=Quantity(21.0, "°C"))
  ```

### 1.5 `GenerationSystem`

`@dataclass(frozen=True) class GenerationSystem`

- **Purpose:** One generator of the `Erzeugung` sheet (assessment §2.1: 3 Kälteerzeuger + 3
  Wärmeerzeuger + 3 Warmwassererzeuger): catalog code, Nutzungsgrad, Deckungsgrad,
  Speicher-/Verteilverluste, and computed Leistung/Energie/Endenergie per Energieträger.
- **Inputs (constructor):** `id: str` (e.g. `"KE1"`), `kind: str` (`"cooling" | "heating" |
  "ww"`), `catalog_code: str` (e.g. `"KE01"` — resolved via `GenerationCatalog`),
  `coverage: float` (Deckungsgrad 0–1), `losses: float` (Speicher-/Verteilverluste 0–1),
  `nominal_power: Quantity | None = None` (kW).
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; no methods).
- **Raises:** `ValueError` if `coverage`/`losses` outside 0–1.
- **Example:**
  ```python
  GenerationSystem(id="KE1", kind="cooling", catalog_code="KE01",
                   coverage=1.0, losses=0.05, nominal_power=Quantity(120.0, "kW"))
  ```

### 1.6 `BuildingProject`

`@dataclass(frozen=True) class BuildingProject`

- **Purpose:** The complete, validated calculation input: project header (as in
  `Gebäude!B1:J2`), climate station, value kind, room rows, ventilation systems, generation
  systems. Exactly the request body of `POST /calculations` (assessment §6.2).
- **Inputs (constructor):** `name: str`, `author: str | None = None`, `date: date | None =
  None`, `climate_station_id: int` (1–40), `value_kind: ValueKind = ValueKind.STANDARD`,
  `rooms: tuple[RoomRow, ...]`, `ventilation: tuple[VentilationSystem, ...] = ()`,
  `generation: tuple[GenerationSystem, ...] = ()`, `note: str | None = None`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; derived values are returned by its methods).
- **Methods:**
  - **`validate(dataset: Dataset, catalog: GenerationCatalog) -> ValidationReport`** —
    domain validation: room uses exist, areas positive, systems reference known LAs, catalog
    codes exist, at least one room. **Raises:** — (report, not exception).
  - **`total_ngf() -> Quantity`** — sum of effective areas.
- **Raises:** constructor: `ValueError` on empty `name` or empty `rooms`.
- **Example:**
  ```python
  project = BuildingProject(name="Beispiel", author="Max Muster",
                            climate_station_id=40, value_kind=ValueKind.STANDARD,
                            rooms=(room_office, room_meeting),
                            ventilation=(la03,), generation=(ke1, we1))
  report = project.validate(ds, catalog)
  ```

### 1.7 `GenerationCatalog`

`@dataclass(frozen=True) class GenerationCatalog`

- **Purpose:** The generator catalog (assessment §2.1, `Nutzungsgrad` sheet): KE01–KE06
  (cooling, EER 3–15), WE01+ (heating, η 0.6–0.8), WW types; each entry carries Energieträger
  and Hilfsenergie %.
- **Inputs (constructor):** `entries: Mapping[str, CatalogEntry]` (`CatalogEntry` =
  `{code, kind, name: TrilingualText, efficiency: float, energy_carrier: EnergyCarrier,
  auxiliary_energy_pct: float, provenance}`).
- **Attributes:** `entries`.
- **Outputs:** — (value object; lookup results are returned by its methods).
- **Methods:**
  - **`generator(code: str) -> CatalogEntry`** — **Raises:** `KeyError`-derived
    `CalculationInputError` with the offending code.
  - **`codes(kind: str | None = None) -> tuple[str, ...]`** — all codes, optionally filtered.
- **Raises:** —.
- **Example:**
  ```python
  catalog.generator("KE01").efficiency        # 3.0
  catalog.generator("KE99")                    # → CalculationInputError
  ```

### 1.8 `WeightingFactors`

`@dataclass(frozen=True) class WeightingFactors`

- **Purpose:** The weighting factors of the `Resultate` sheet (assessment §2.1: NEGF, PEne,
  THGE per Energieträger).
- **Inputs (constructor):** `negf: Mapping[EnergyCarrier, float]`, `pene: Mapping[EnergyCarrier,
  float]`, `thge: Mapping[EnergyCarrier, float]`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:** `factors.negf[EnergyCarrier.ELECTRICITY]  # e.g. 2.0`

### 1.9 `Resultate`

`@dataclass class Resultate`

- **Purpose:** Final energy per Energieträger × end use plus totals and weighted sums — the
  digital `Resultate` table (assessment §2.1).
- **Inputs (constructor):** `project: BuildingProject`, `cells: Mapping[tuple[EnergyCarrier,
  EndUse], Quantity]`, `weighting: WeightingFactors | None = None`.
- **Attributes:** `project`, `cells`, `weighting`.
- **Outputs:** — (value object; table views are returned by its methods).
- **Methods:**
  - **`totals(carrier: EnergyCarrier | None = None) -> Quantity | dict[EnergyCarrier, Quantity]`**
    — column/row totals. **Raises:** —.
  - **`weighted(factor: str) -> dict[EnergyCarrier, float]`** — `"negf" | "pene" | "thge"`
    weighted sums. **Raises:** `ValueError` on unknown factor name.
  - **`as_dict() -> dict`** — JSON-ready table.
- **Raises:** —.
- **Example:**
  ```python
  resultate.totals(EnergyCarrier.ELECTRICITY)     # Quantity(…, 'kWh/a')
  resultate.weighted("pene")
  ```

### 1.10 `ValidationReport`

`@dataclass(frozen=True) class ValidationReport`

- **Purpose:** Structured validation outcome: hard errors (invalid) and warnings (suspicious
  but acceptable). Used by input validation and dataset validation alike.
- **Inputs (constructor):** `errors: tuple[str, ...] = ()`, `warnings: tuple[str, ...] = ()`.
- **Attributes:** `errors`, `warnings`; `valid` property (`not errors`); `as_dict()`.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:**
  ```python
  report = project.validate(ds, catalog)
  if not report.valid:
      raise CalculationInputError("invalid project", {"errors": list(report.errors)})
  ```

---

## 2. `energytools.gebaeude.physics`

Direct port of the psychrometric UDFs observed in `FeuchteLuft_Formeln.bas` (assessment §2.2:
"Glück" saturation-pressure polynomials, constants 611, 2501.6, 1.006, 1.86, 2.8858, 8.02). All
functions are pure, documented with the VBA source, and verified against VBA values over the
full bin range (−25 … +34 °C) in the regression harness (assessment §7.4/7.5).

### 2.1 Physics constants

`CP_AIR = 1.006` (kJ/(kg·K), dry air — VBA `cpl`), `CP_WATER_VAPOUR = 1.86` (kJ/(kg·K),
water vapour — VBA `cpw`), `CP_WATER = 4.19` (kJ/(kg·K), liquid water — `cw`,
`Berechnung LU!N22`), `HEAT_OF_VAPORIZATION = 2501.6` (kJ/kg at 0 °C — VBA `r0`),
`HEAT_OF_VAPORIZATION_100 = 2256` (kJ/kg at 100 °C — `r100`, `Berechnung LU!N25`),
`AIR_DENSITY = 1.15` (kg/m³ — `ρ`, `Berechnung LU!N23`), `MOLAR_MASS_RATIO = 622`
(g/kg scale factor, 0.622 × 1000 — used in all psychrometric formulas), `PS_0 = 611`
(Pa reference of the Glück polynomial), `DEW_POINT_P = 2.8858`, `DEW_POINT_N = 8.02`,
`DEW_POINT_K = 1.098` (dew-point inversion constants).

- **Purpose:** The magic constants of the workbook model, named and unit-annotated so the
  port can be reviewed against the VBA. Value grounding: textbook ch01 §1.1 (UDF module
  constants) and ch04 §4.16-3 / `analysis_Berechnung_LU.md` §8 (`Berechnung LU!N19:N25`
  AHU constants).
- **Inputs:** —.
- **Outputs:** `float` constants.
- **Raises:** —.
- **Example:**
  ```python
  from energytools.gebaeude import physics
  physics.HEAT_OF_VAPORIZATION      # 2501.6
  ```

### 2.2 `saturation_pressure_glueck`

`def saturation_pressure_glueck(t: float) -> float`

- **Purpose:** Saturation vapour pressure after Glück in **mbar** — the piecewise polynomial
  with the split at `t = 0` (VBA `Saettigungsdruck`; the VBA `Else` branch returning
  `"Fehler"` is unreachable in VBA and becomes an exception here).
- **Inputs:** `t: float` — temperature in °C.
- **Outputs:** `float` — saturation pressure in mbar.
- **Raises:** `PsychrometricError` if `t` is NaN (the VBA "Fehler" case).
- **Example:**
  ```python
  ps = saturation_pressure_glueck(20.0)     # ≈ 23.37 mbar
  ```

### 2.3 `absolute_humidity`

`def absolute_humidity(t: float, rh: float, p: float) -> float`

- **Purpose:** Absolute humidity in **g/kg** from temperature, relative humidity and pressure —
  VBA `AbsFeuchte`: `x = (rh * 622 * ps) / (p - rh * ps)`. **Unit convention:** the workbook
  call sites pass φ as a **fraction (0–1)** (e.g. `Klimadaten!Q20 = AbsFeuchte(-10, 0.8817, p)`;
  textbook ch01 §1.3/§1.9); this API accepts `rh` in **% (0–100)** and converts internally so
  the VBA formula above uses `rh/100`.
- **Inputs:** `t` (°C), `rh` (%, 0–100), `p` (mbar, > 0).
- **Outputs:** `float` — g/kg.
- **Raises:** `PsychrometricError` for `rh` outside 0–100, `p <= 0`, or when `p - rh*ps <= 0`.
- **Example:**
  ```python
  absolute_humidity(20.0, 50.0, 1013.0)     # ≈ 7.28 g/kg
  ```

### 2.4 `relative_humidity`

`def relative_humidity(t: float, x: float, p: float) -> float`

- **Purpose:** Relative humidity in % from temperature, absolute humidity and pressure — VBA
  `RelFeuchte`: `rh = (x * p) / (ps * (622 + x))`. **Unit convention:** the workbook function
  returns a **fraction (0–1)** and call sites combine it with `MIN(1, …)` saturation clamps
  (textbook ch01 §1.6); this API returns **% (0–100)**.
- **Inputs:** `t` (°C), `x` (g/kg, ≥ 0), `p` (mbar, > 0).
- **Outputs:** `float` — %.
- **Raises:** `PsychrometricError` for `x < 0` or `p <= 0`.
- **Example:**
  ```python
  relative_humidity(20.0, 7.28, 1013.0)     # ≈ 50.0 %
  ```

### 2.5 `enthalpy_from_rel_humidity`

`def enthalpy_from_rel_humidity(t: float, rh: float, p: float) -> float`

- **Purpose:** Enthalpy in **kJ/kg** from T/rF/p — VBA `EnthalpieR`, which computes `x` in kg/kg
  first: `h = cpl*T + x*(r0 + cpw*T)`. **Reference-only:** no stored formula calls
  `EnthalpieR` (dead code — textbook ch01 §1.9; the VBA `rF*100`/`p*100` double conversion is
  only self-consistent for fractional `rF`), ported for completeness.
- **Inputs:** `t` (°C), `rh` (%, 0–100), `p` (mbar, > 0).
- **Outputs:** `float` — kJ/kg.
- **Raises:** `PsychrometricError` (same domain rules as `absolute_humidity`).
- **Example:**
  ```python
  enthalpy_from_rel_humidity(20.0, 50.0, 1013.0)    # ≈ 38.5 kJ/kg
  ```

### 2.6 `enthalpy_from_absolute_humidity`

`def enthalpy_from_absolute_humidity(t: float, x: float, p: float) -> float`

- **Purpose:** Enthalpy in **kJ/kg** from T/x/p — VBA `EnthalpieA` (the UDF actually referenced
  by stored formulas in the Gebäude-Tool): `h = cpl*T + (x/1000)*(r0 + cpw*T)`. `p` is unused
  in the formula but kept for signature symmetry with the VBA.
- **Inputs:** `t` (°C), `x` (g/kg, ≥ 0), `p` (mbar — accepted, unused).
- **Outputs:** `float` — kJ/kg.
- **Raises:** `PsychrometricError` for `x < 0`.
- **Example:**
  ```python
  enthalpy_from_absolute_humidity(20.0, 7.28, 1013.0)
  ```

### 2.7 `dew_point`

`def dew_point(t: float, rh: float, p: float) -> float`

- **Purpose:** Dew-point temperature in °C from T/rF/p — VBA `TaupunktR`: computes `x`, then
  inverts the saturation pressure: `t_dp = ((pst/2.8858)^(1/8.02) - 1.098) * 100` with
  `pst = p / (0.622*1000/x + 1)`. **Reference-only:** no stored formula calls `TaupunktR`
  (dead code — textbook ch01 §1.7); the dew-point power-law fit deviates from the Glück
  polynomial (≈6 % at 20 °C) and is not used by the engine.
- **Inputs:** `t` (°C), `rh` (%, 0–100), `p` (mbar, > 0).
- **Outputs:** `float` — °C.
- **Raises:** `PsychrometricError` (domain rules of `absolute_humidity`; also when `x == 0`).
- **Example:**
  ```python
  dew_point(20.0, 50.0, 1013.0)             # ≈ 9.3 °C
  ```

### 2.8 `dew_point_from_absolute_humidity`

`def dew_point_from_absolute_humidity(x: float, p: float) -> float`

- **Purpose:** Dew-point temperature in °C from absolute humidity and pressure — VBA
  `TaupunktA`. **Reference-only:** the function is **commented out** in the Gebaeude VBA
  module, but `Berechnung LU!AQ{n}` still calls it → cached `#NAME?` cascading to `AS{n}`
  `#VALUE!`; the AQ/AS column chain does not participate in any result (textbook ch01
  §1.7/§1.10, ch04 §4.14-1). Ported for completeness; a fix would invert the Glück
  polynomial instead.
- **Inputs:** `x` (g/kg, > 0), `p` (mbar, > 0).
- **Outputs:** `float` — °C.
- **Raises:** `PsychrometricError` for `x <= 0` or `p <= 0`.
- **Example:**
  ```python
  dew_point_from_absolute_humidity(7.28, 1013.0)   # ≈ 9.3 °C
  ```

### 2.9 `temperature_from_enthalpy`

`def temperature_from_enthalpy(h: float, x: float) -> float`

- **Purpose:** Temperature in °C from enthalpy and absolute humidity — VBA `TemperaturH`:
  `t = (h - x*r0) / (cpl + cpw*x)` with `x` in kg/kg internally.
- **Inputs:** `h` (kJ/kg), `x` (g/kg, ≥ 0).
- **Outputs:** `float` — °C.
- **Raises:** `PsychrometricError` for `x < 0` or a denominator of zero.
- **Example:**
  ```python
  temperature_from_enthalpy(38.5, 7.28)     # ≈ 20.0 °C
  ```

### 2.10 `wet_bulb_temperature`

`def wet_bulb_temperature(t: float, rh: float) -> float`

- **Purpose:** Empirical wet-bulb temperature in °C — VBA `Feuchtkugel`
  (`FK = -5.809 + 0.058*rh + 0.697*t + 0.003*rh*t`, below 0 °C corrected to `FK*0.8 + 0.5`).
  **Reference-only**: the function is not referenced by any stored formula (dead code —
  textbook ch01 §1.8); it is ported for completeness and marked accordingly.
- **Inputs:** `t` (°C), `rh` (%, 0–100).
- **Outputs:** `float` — °C.
- **Raises:** `PsychrometricError` for `rh` outside 0–100.
- **Example:**
  ```python
  wet_bulb_temperature(20.0, 50.0)          # ≈ 13.7 °C
  ```

---

## 3. `energytools.gebaeude.ahu`

The AHU temperature-bin engine — the port of `Berechnung LU` (assessment §2.2: ≈13,500 formula
cells; a single row-32 template driven per system; fans, WRG/KRG, recirculation, heating/cooling
coils, dehumidification, humidification, IST/SOLL comparison, results in rows 254–260). It is a
**pure function of the inputs**; the Excel backend exists only to produce the same numbers via
the original workbook during the port phase.

### 3.1 `AhuInput`

`@dataclass(frozen=True) class AhuInput`

- **Purpose:** All inputs of one AHU calculation — the row-32 template as data (no cells).
- **Inputs (constructor):** `system: VentilationSystem`, `served_area: Quantity` (m²),
  `room_use: RoomUse | None = None`, `climate_station: ClimateStation`,
  `value_kind: ValueKind`, `bin_temperatures: tuple[float, ...]` (bin centres, from
  `Klimadaten`), `bin_hours: tuple[float, ...]` (annual hours per bin),
  `supply_setpoint: Quantity` (°C), `return_setpoint: Quantity` (°C), `recirculation_ratio:
  float = 0.0`, `air_pressure: Quantity = Quantity(1013.0, "mbar")`.
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; validation results are returned by its methods).
- **Methods:**
  - **`validate() -> ValidationReport`** — bins/hours length match, positive areas.
- **Raises:** constructor: `ValueError` on mismatched bin arrays.
- **Example:**
  ```python
  AhuInput(system=la03, served_area=Quantity(1200.0, "m2"), climate_station=zurich,
           value_kind=ValueKind.STANDARD, bin_temperatures=(-25.0, …, 34.0),
           bin_hours=(0.0, …, 120.0), supply_setpoint=Quantity(21.0, "°C"),
           return_setpoint=Quantity(24.0, "°C"))
  ```

### 3.2 `AhuBinResult`

`@dataclass(frozen=True) class AhuBinResult`

- **Purpose:** Per-temperature-bin result of the psychrometric loop: one row of the
  `Berechnung LU` template for one outdoor bin.
- **Inputs (constructor):** `bin_index: int`, `t_a: float` (°C), `hours: float` (h/a),
  `x_a: float` (g/kg), `h_a: float` (kJ/kg), `t_mil: float` (°C, mixed air), `x_mil: float`,
  `t_zul_ist: float` (°C, supply IST after case selection), `x_zul_ist: float` (g/kg),
  `case: str` (`"fall1_heizen_befeuchten" | "fall2_entfeuchten_heizen" |
  "fall3_kuehlen_entfeuchten" | "fall4_kuehlen_befeuchten"` — the `Fallunterscheidung`
  classification of the workbook's `AW{n}` detector, **live code** per textbook ch04 §4.9:
  Fall 1 heat+humidify, Fall 2 dehumidify+heat, Fall 3 cool (±reheat), Fall 4 cool+humidify),
  `fan_power: float` (kW), `heating_power: float` (kW), `cooling_power: float` (kW),
  `humidification_power: float` (kW), `dehumidification_power: float` (kW),
  `energy: dict[str, float]` (kWh per function).
- **Attributes:** all constructor fields; `as_dict()`.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:** `bin = result.bins[30]; bin.case, bin.heating_power`

### 3.3 `AhuResult`

`@dataclass(frozen=True) class AhuResult`

- **Purpose:** Aggregated result of one AHU over all bins: annual energies (rows 254–260 of
  `Berechnung LU`) plus the full bin trace for explanation.
- **Inputs (constructor):** `system_id: str`, `input: AhuInput`, `bins: tuple[AhuBinResult,
  ...]`, `annual: dict[str, Quantity]` (e.g. `{"heating": …, "cooling": …,
  "humidification": …, "fans": …, "total_electric": …}` in kWh/a),
  `full_load_hours: Quantity | None` (h/a), `provenance: Provenance | None = None`.
- **Attributes:** all constructor fields; `as_dict()`.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:** `ahu_result.annual["cooling"].format()  # '12 400.00 kWh/a'`

### 3.4 `calculate_ahu`

`def calculate_ahu(input: AhuInput) -> AhuResult`

- **Purpose:** Runs the temperature-bin psychrometric calculation for one AHU: for each bin —
  outdoor state from climate, mixed-air state, **Fall 1–4 case selection** (the live
  `Fallunterscheidung` logic — workbook `Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul`, textbook
  ch04 §4.9; bin state machine per ch04 §4.16-2), fan power (P ∝ V^2.5, stage-dependent),
  coil/heater/humidifier models with WRG/KRG — then aggregates annual energies (rows 254–260).
  Deterministic: same inputs → bit-identical outputs.
- **Inputs:** `input: AhuInput` (see 3.1).
- **Outputs:** `AhuResult`.
- **Raises:** `PsychrometricError` (out-of-domain state, e.g. humidity > saturation in a bin),
  `CalculationError` for internal inconsistency (e.g. negative annual energy).
- **Example:**
  ```python
  result = calculate_ahu(AhuInput(system=la03, …))
  print(result.annual["heating"])
  ```

### 3.5 `FanModel`

`@dataclass(frozen=True) class FanModel`

- **Purpose:** Stage-dependent fan power model of the workbook: fan power scales with
  `(V/V_ref)^2.5` between stages (observed "Leistung" column of `Berechnung LU`).
- **Inputs (constructor):** `reference_power: Quantity` (kW at reference flow),
  `reference_flow: Quantity` (m³/h), `stages: tuple[float, ...] = (0.33, 0.66, 1.0)`
  (relative flows per stage).
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; power results are returned by its methods).
- **Methods:**
  - **`fan_power(volume_flow: Quantity, stage: int = -1) -> Quantity`** — power at the given
    flow (or at the given stage index). **Raises:** `ValueError` for out-of-range stage.
- **Raises:** —.
- **Example:**
  ```python
  FanModel(reference_power=Quantity(7.5, "kW"), reference_flow=Quantity(4000.0, "m3/h"))
      .fan_power(Quantity(2000.0, "m3/h"))      # 7.5 * (0.5)^2.5 ≈ 1.33 kW
  ```

### 3.6 `HeatRecoveryModel`

`@dataclass(frozen=True) class HeatRecoveryModel`

- **Purpose:** WRG/KRG recovery: temperature efficiency model for the recovery wheel/plate
  used in `Berechnung LU` (wrga = recovery ratio of `VentilationSystem`).
- **Inputs (constructor):** `efficiency: float` (0–1), `frost_protection: bool = True`
  (recovery limited above the frost threshold).
- **Attributes:** all constructor fields.
- **Outputs:** — (value object; temperature results are returned by its methods).
- **Methods:**
  - **`recovery_temperature(t_exhaust: float, t_outdoor: float) -> float`** — pre-heated
    outdoor temperature after recovery, °C. **Raises:** `PsychrometricError` on invalid
    efficiency.
- **Raises:** —.
- **Example:**
  ```python
  HeatRecoveryModel(0.7).recovery_temperature(22.0, -10.0)   # ≈ 12.4 °C
  ```

---

## 4. `energytools.gebaeude.engine`

### 4.1 `CalculationEngine`

`class CalculationEngine`

- **Purpose:** The orchestration facade of the calculation service (assessment §6.2): validate
  input → calculate over a chosen backend → explain; stores results for reproducibility.
  Backend-agnostic: `ExcelBackend` (reference) and `NativeBackend` (ported) are interchangeable
  behind it, and the engine records which backend produced a result.
- **Inputs (constructor):** `store: CalculationStore | None = None`,
  `resolver: VersionResolver | None = None`, `default_backend: CalculationBackend | None =
  None`.
- **Attributes:** `store`, `resolver`, `default_backend`.
- **Outputs:** — (service object; results are returned by its methods).
- **Methods:**
  - **`validate_input(project: BuildingProject, dataset: Dataset, model_release: ModelRelease |
    str) -> ValidationReport`** — structural + domain validation (project, rooms, systems,
    station, generation) **and** version compatibility. **Raises:** — (report).
  - **`calculate(project: BuildingProject, dataset: Dataset, model_release: ModelRelease | str,
    backend: CalculationBackend | None = None, result_id: str | None = None) ->
    CalculationResult`** — validates first, then runs the backend, stores the result.
    **Raises:** `ModelVersionMismatchError`, `CalculationInputError` (hard errors),
    `BackendError`, `CalculationError`.
  - **`explain(result_id: str) -> CalculationTrace`** — the stored trace. **Raises:**
    `KeyError`-derived `CalculationError` for unknown `result_id`.
  - **`get_result(result_id: str) -> CalculationResult`** — stored result. **Raises:**
    `CalculationError` for unknown id.
- **Raises:** constructor: —.
- **Example:**
  ```python
  engine = CalculationEngine()
  report = engine.validate_input(project, ds, "1.0.0")
  result = engine.calculate(project, ds, "1.0.0", backend=NativeBackend())
  trace = engine.explain(result.result_id)
  ```

### 4.2 `CalculationResult`

`@dataclass(frozen=True) class CalculationResult`

- **Purpose:** The complete, reproducible outcome of one calculation (assessment §6.2 response):
  versions, inputs hash, assumptions, warnings, overridden values, results per room/system/
  carrier, totals and intermediates.
- **Inputs (constructor):** `result_id: str` (UUID), `versions: VersionInfo`, `inputs_hash:
  str` (SHA-256 of the canonical input JSON), `project: BuildingProject`, `backend: str`
  (backend name + version), `per_room: Mapping[str, dict]`, `per_system: Mapping[str,
  AhuResult]`, `per_carrier: Resultate`, `totals: dict[str, Quantity]`,
  `intermediates: dict[str, object]` (e.g. `{"ahu_bins": …, "full_load_hours": …,
  "qhc": …}`), `assumptions: tuple[str, ...]`, `warnings: tuple[str, ...]`,
  `overridden_values: tuple[dict, ...]`, `computed_at: datetime`, `trace: CalculationTrace |
  None = None`.
- **Attributes:** all constructor fields; `as_dict()` → JSON-ready.
- **Outputs:** — (value object).
- **Raises:** —.
- **Example:**
  ```python
  result.versions.as_dict()          # {'dataset': 'V221', 'model': '1.0.0', …}
  result.totals["endenergie_el"]
  ```

### 4.3 `CalculationTrace`

`class CalculationTrace`

- **Purpose:** Step-by-step explainable trace: the calculation graph nodes (room KPI
  derivation → building aggregation → AHU bins → generation → resultate) with their inputs,
  formula reference and outputs — the payload of `GET /calculations/{id}/explain`
  (assessment §6.2).
- **Inputs (constructor):** `result_id: str`, `steps: tuple[TraceStep, ...]`
  (`TraceStep` = `{id, kind, label, inputs: dict, formula: str | None, outputs: dict,
  provenance: Provenance | None}`).
- **Attributes:** `result_id`, `steps`.
- **Outputs:** — (value object; step access via its methods).
- **Methods:**
  - **`steps() -> tuple[TraceStep, ...]`** — ordered steps.
  - **`step(step_id: str) -> TraceStep`** — **Raises:** `KeyError`.
- **Raises:** —.
- **Example:**
  ```python
  for s in trace.steps():
      print(s.label, s.outputs)
  ```

### 4.4 `CalculationStore`

`class CalculationStore`

- **Purpose:** Persistence of calculation results by `result_id` (in-memory or on-disk),
  enabling `GET /calculations/{result_id}` and reproducibility (assessment §6.2).
- **Inputs (constructor):** `directory: str | None = None` (None = in-memory).
- **Attributes:** `directory`.
- **Outputs:** — (store object; persistence results via its methods).
- **Methods:**
  - **`save(result: CalculationResult) -> None`** — **Raises:** `OSError` on write failure.
  - **`get(result_id: str) -> CalculationResult`** — **Raises:** `CalculationError` (unknown
    id).
  - **`list(limit: int = 100) -> list[str]`** — newest-first result ids.
- **Raises:** —.
- **Example:**
  ```python
  store.save(result); store.get(result.result_id)
  ```

---

## 5. `energytools.gebaeude.backends`

### 5.1 `CalculationBackend`

`class CalculationBackend(abc.ABC)`

- **Purpose:** The backend contract. A backend executes one validated calculation and reports
  its identity; the engine treats all backends uniformly (assessment §5.3 [4]).
- **Inputs (constructor):** — (abstract).
- **Attributes:** `name: str` (e.g. `"excel"` / `"native"`), `version: str`.
- **Outputs:** — (backend object; calculation results are returned by its methods).
- **Methods (abstract):**
  - **`calculate(project: BuildingProject, dataset: Dataset, model_release: ModelRelease) ->
    CalculationResult`** — full calculation (per-room, per-system, per-carrier, totals,
    intermediates, trace). **Raises:** `BackendError` subclasses, `ModelVersionMismatchError`.
  - **`validate(project: BuildingProject, dataset: Dataset) -> ValidationReport`** — backend
    capability validation (e.g. Excel: all inputs mappable to workbook ranges).
- **Raises:** —.
- **Example:**
  ```python
  backend: CalculationBackend = NativeBackend() if use_native else ExcelBackend(path)
  ```

### 5.2 `ExcelBackend`

`class ExcelBackend(CalculationBackend)`

- **Purpose:** **Excel backend — the reference runtime** (assessment §7.3): executes the
  original Gebäude-Tool workbook on a **copy** via Excel COM to produce the oracle values. Inputs
  are mapped API-side to workbook cells; outputs are read back from result ranges; **no cell
  address ever crosses the API** (assessment §5.3 rule 1). Deterministic configuration: links
  not updated, `Application.Calculation` fixed, `AutomationSecurity = ForceDisable`,
  no save.
- **Inputs (constructor):** `workbook_path: str` (path to a copy of
  `2024_Gebaeude-Tool_dfi_V221.xlsm`), `excel_app: object | None = None` (injected COM
  application for tests), `timeout_s: float = 120.0`.
- **Attributes:** `name = "excel"`, `version` (from the workbook + runner version),
  `workbook_path`.
- **Outputs:** — (backend object; calculation results are returned by its methods).
- **Methods:**
  - **`calculate(project, dataset, model_release) -> CalculationResult`** — recalculates the
    workbook copy and reads results. **Raises:** `ExcelBackendError` (Excel missing/denied,
    recalc failure, non-deterministic results, cached-value mismatch),
    `ModelVersionMismatchError`.
  - **`close() -> None`** — releases the COM application deterministically.
  - **`__enter__() / __exit__(...)`** — context manager wrapping open/close.
- **Raises:** constructor: `FileNotFoundError` if the copy is missing.
- **Example:**
  ```python
  with ExcelBackend("data/raw/_copies/Gebaeude_V221.xlsm") as backend:
      result = engine.calculate(project, ds, "1.0.0", backend=backend)
  # Excel process guaranteed released even on failure
  ```

### 5.3 `NativeBackend`

`class NativeBackend(CalculationBackend)`

- **Purpose:** **Native backend — the ported runtime** (assessment §7.5/7.6): pure-Python
  execution of the model (physics + AHU + generation + resultate). Verified module-by-module
  against the Excel oracle within defined tolerances (exact for pure arithmetic; ≤1e-9 relative
  for transcendental physics; normative `ROUND(…,-1)` rules applied where the workbook defines
  them). No Excel required.
- **Inputs (constructor):** `tolerances: dict[str, float] | None = None` (per-result-kind
  tolerances for the self-check against stored reference cases), `self_check: bool = True`.
- **Attributes:** `name = "native"`, `version` (library version).
- **Outputs:** — (backend object; calculation results are returned by its methods).
- **Methods:**
  - **`calculate(project, dataset, model_release) -> CalculationResult`** — runs
    `calculate_ahu` per system, aggregates via `ResultateAggregator`, builds the trace.
    **Raises:** `CalculationError`, `PsychrometricError` (wrapped), `ModelVersionMismatchError`.
- **Raises:** —.
- **Example:**
  ```python
  result = engine.calculate(project, ds, "1.0.0", backend=NativeBackend())
  ```

---

## 6. `energytools.gebaeude.resultate`

### 6.1 `ResultateAggregator`

`class ResultateAggregator`

- **Purpose:** Aggregates room KPIs, AHU results and generation results into the `Resultate`
  table (per Energieträger × end use, with losses and Deckungsgrad applied — the `Erzeugung` →
  `Resultate` flow of assessment §2.2).
- **Inputs (constructor):** `catalog: GenerationCatalog`, `weighting: WeightingFactors | None
  = None`.
- **Attributes:** `catalog`, `weighting`.
- **Outputs:** — (service object; aggregation results are returned by its methods).
- **Methods:**
  - **`aggregate(project: BuildingProject, ahu_results: Mapping[str, AhuResult], dataset:
    Dataset) -> Resultate`** — full aggregation incl. per-generator Endenergie and carrier
    totals. **Raises:** `CalculationError` for unknown catalog codes or inconsistent units.
- **Raises:** —.
- **Example:**
  ```python
  agg = ResultateAggregator(catalog, factors)
  resultate = agg.aggregate(project, ahu_results, ds)
  ```

### 6.2 `weight_resultate`

`def weight_resultate(resultate: Resultate, factors: WeightingFactors) -> dict[str, dict]`

- **Purpose:** Applies the NEGF/PEne/THGE weighting factors to the resultate table (assessment
  §2.1 weighting columns).
- **Inputs:** `resultate: Resultate`, `factors: WeightingFactors`.
- **Outputs:** `{"negf": {carrier: value}, "pene": …, "thge": …}` (also aggregated totals).
- **Raises:** `CalculationError` if a carrier of the resultate is missing from `factors`.
- **Example:**
  ```python
  weighted = weight_resultate(resultate, factors)
  weighted["pene"]["el"]
  ```
