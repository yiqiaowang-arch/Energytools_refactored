# Gebäude-Tool (SIA 2024) Calculation Model Textbook

> Complete calculation textbook · written from the `.analysis` extracts
>
> Subject: `data/raw/2024_Gebaeude-Tool_dfi_V221.xlsm` (13 worksheets, ≈51 300 non-empty cells, ≈16 900 formula cells)
> Companion dataset: `2024_Raumdatenblätter_dfi_V221.xlsm` (room data source, 45 room use types)
>
> Language convention: the body text is written in English; technical terms keep the German original (with English glosses at first occurrence); formula references retain the Excel/VBA syntax verbatim.

---

## 0.1 Document Map

| Section | File | Content |
|---|---|---|
| Introduction (this file) | `README.md` | Tool positioning, data sources, cell-reference conventions, calculation-flow overview, worksheet list, unit system, known quirks |
| Chapter 1 | `ch01-moist-air-physics.md` | Moist-air physics: derivation, units, assumptions, scope of validity and all call sites of the 8 UDFs — Glück saturation-pressure polynomial, enthalpy/humidity ratio/relative humidity/dew point, etc. |
| Chapter 2 | `ch02-room-kpi-derivation.md` | Room KPI derivation: `KZ_Raum_2024` matrix, `Res` named range, `Gebäude` room-row VLOOKUP chain, EBF/GF (energy reference area / floor area) weighting, Allg. Gebäudetechnik |
| Chapter 3 | `ch03-ventilation-full-load-hours.md` | Ventilation full-load hours: `Std` table (copy of Raumdaten `Volll_Lüft`), mechanism of selection by Regelung (control mode), use in the AHU engine |
| Chapter 4 | `ch04-ahu-temperature-bin-method.md` | AHU temperature-bin method (`Berechnung LU`): meteorological bin h-x chain, three fan stages P∝V^2.5, WRG/KRG (heat/cold recovery), four control cases (Fall 1–4), energy summary |
| Chapter 5 | `ch05-heat-generation-resultate.md` | Heat generation and Resultate summary: `Nutzungsgrad` catalogue, the three heat-generator groups in `Erzeugung`, Endenergie/Energieträger allocation, `Resultate` weighting (NEGF/PEne/THGE) |
| Chapter 6 | `ch06-climate-data.md` | Climate data: `Klimadaten` 40 stations, air pressure (barometric-height formula), HDD, design temperatures, temperature-bin hours and humidity sequences, `Qhc_Klimastat` |
| Appendix A | `analysis_Berechnung_LU.md` | Column-by-column analysis worksheet of the entire `Berechnung LU` table (basis for the Chapter 4 derivations; includes a complete numerical example for row 168) |

## 0.2 Data Sources and Reproducibility

All formulas, constants and cell references in this textbook are taken from the following `.analysis` extracts (workbook OOXML unpacking + VBA source extraction + per-cell dump):

- Per-cell dump (address / formula / cached result): `.analysis/dumps/gebaeude/sheet_*.tsv`
- Worksheet list and row/column statistics: `.analysis/dumps/gebaeude/sheets.json`
- Named ranges: `.analysis/dumps/gebaeude/definedNames.json`
- VBA source (UDFs and macros): `.analysis/vba/gebaeude/*.bas`, `*.cls`
- Unpacked OOXML: `.analysis/unpacked/gebaeude/`
- Reproducible source-file hash: `data/raw/2024_Gebaeude-Tool_dfi_V221.xlsm` (897 991 bytes)

> ⚠️ The `R:` values in the dumps are the **cached calculation results** from the time the file was saved (e.g. the example building = Zürich-MeteoSchweiz station, Standard value range); every numerical example in this text states its input premises.

## 0.3 Cell-Reference Conventions

- This textbook uses the original German worksheet names (the names stored in the file; they do not change with the UI language):
  `Gebäude`, `Lüftung`, `Erzeugung`, `Resultate`, `Nutzungsgrad`, `Berechnung LU`,
  `Klimadaten`, `KZ_Raum_2024`, `Qhc_Klimastat`, `Std`, `Begriffe`, `Anleitung`, `Lizenzieren`.
- Cell notation: `Sheet!ColumnRow` (worksheet!column-row), e.g. `Gebäude!F12`; ranges e.g. `KZ_Raum_2024!$B$7:$AV$51`.
- Formula originals are quoted in a monospace font (`` ` ``), e.g. `` `VLOOKUP($B12,Res,F$9,FALSE)` ``; `Res` is the named range.
- **Row-variable convention**: whenever a formula repeats along rows, the row number `n` denotes a generic row, and a concrete example row is given (e.g. `n=121`).
   For example, the temperature-bin rows of `Berechnung LU` are written as `X{n}` (IST (actual) block `n=121…181`, SOLL (target) block `n=189…249`, t_A = −25…+35 °C).
- Cross-workbook references (external links) are marked with the dump notation `[3]` etc. (see Section 0.7).

## 0.4 Calculation-Flow Overview

```
Project input (Gebäude!B2..J2, climate station via Gebäude!D2)
        │
        ▼
┌──────────────────────────── Gebäude sheet ─────────────────────────────┐
│ 21 room rows (12..32): Raumnutzung dropdown (Begriffe!F13:F57)         │
│   → column A reverse-lookup SIA code (INDEX/MATCH Begriffe!B13:F57)    │
│   → EBF flag (C), NGF (D), Anteil (E)                                  │
│   → per-use Leistung/Energie (F..K) ← VLOOKUP(B, Res, <col>) × NGF/1000│
│   → Lüftung system (L), Volumenstr. (M) ← VLOOKUP(B, Std!B:H)          │
│   → Raumkühlung (P..R), Raumheizung (S..U) ← VLOOKUP(B, Res) × NGF/1000│
│   → Warmwasser demand (V) ← VLOOKUP(B, Std!B:I); energy (W) ← Res      │
│   → Total row 33 → Rechenwert row 35 (overridable by "Werte aus anderen│
│     Quellen" row 34) → GF/EBF rows 37..39                              │
│   → Allg. Gebäudetechnik rows 47..57 (AG01..AG10, Minergie-Strommodell)│
└──────────────┬─────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────── Lüftung sheet ───────────────────────────────────────────┐
│ 16 system rows (LA01..LA16, 7..22)                                                                  │
│   C: Volumenstr. Standard ← SUMIF(Gebäude!L12:L32, system, M12:M32)                                 │
│   F: Rechenwert = C or E (project); H: fan power = F×SFP/1000                                       │
│   J: Regelung (einstufig/zweistufig/stufenlos)                                                      │
│   K: Vollast. = ROUND(I×1000/H, -1) (back-calculated from the AHU result)                           │
│   Q..Z: air cooling/heating/humidification/dehumidification Leistung+Energie ← Berechnung LU results│
│   Total row 23                                                                                      │
└──────────────┬──────────────────────────────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────── Berechnung LU sheet (physics engine) ───────────────────────────┐
│ row 6: single-system input (= Lüftung!32 template row, macro-copied to 7..22)              │
│ row 7: Resultate (fan electrical energy H7, per-section power/energy P7..Y7)               │
│ rows 11..55: IST/SOLL inputs (areas, ceiling heights, filters, fan efficiency              │
│             classes, WRG/KRG, cooling/heating/humidification/dehumidification              │
│             setpoints, operating schedules, temperature curves)                            │
│ rows 63..67: stage runtime-weighted fan power and average air volume                       │
│ rows 68..70: SIA full-load hours (Std!Q:V by Regelung) and plausibility check              │
│ rows 100..114: motor efficiency classes (IE5..Eff3 × power bands) and filter pressure drops│
│ rows 121..181: IST temperature-bin h-x calculation (61 bins −25…+35 °C, per bin:           │
│    AUL → frost protection → nWRG → MIL (enthalpy/temperature) → cooling-coil               │
│    chain A/C/D1/D2 → Fall 1..4 → Zuluft soll/ist, Raum; per-bin power × bin                │
│    hours = bin energy)                                                                     │
│ rows 189..249: SOLL bin block (dormant); rows 182/183: annual energy sum / power max       │
│ rows 254..260: annual energy summary (kWh/kW; row-7 MWh equivalents Q7..Y7, H7)            │
│ row 261+: economics (energy prices, operating costs)                                       │
└──────────────┬─────────────────────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────── Erzeugung sheet ───────────────────────────────┐
│ Kälte (rows 7..10): demand ← Gebäude!Q/R35 + Lüftung!Q/R23                    │
│ Wärme (rows 16..19): demand ← Gebäude!T/U35 + Lüftung!S/T23                   │
│ WW   (rows 25..28): demand ← Gebäude!V/W35 (V×4.186/3.6×50/L29/1000)          │
│ per unit: Deckungsgrad F/G%, Speicher-/Verteilverluste H/J%                   │
│   L/M = demand×Deckungsgrad×(100+losses)%                                     │
│   N = M×1000/L (Volllaststunden); P/Q = L/M÷Nutzungsgrad (project or standard)│
│   R = Energieträger ← VLOOKUP Nutzungsgrad catalogue                          │
│ Elektrizitätserzeugung (rows 34..37): PV/WKK installed capacity and efficiency│
└──────────────┬────────────────────────────────────────────────────────────────┘
               ▼
┌──────────────────────────── Resultate sheet ────────────────────────────┐
│ Energieträger × use matrix (rows 7..15): El/HEL/Gas/Pell/HSch/StH/Bio/FW│
│   Geräte/Prozess/Beleuchtung ← Gebäude row 35                           │
│   Lüftung ← Lüftung!H23/I23; Kühlung/Heizung/WW ← Erzeugung SUMIF       │
│ weighted rows 21/22/25: NEGF (W), PEne (X), THGE (Y) weights SUMPRODUCT │
│ energy-balance rows 28..59: kWh/m², kg/m² per-floor-area indicators     │
└─────────────────────────────────────────────────────────────────────────┘
```

Dependency direction: `Gebäude` → `Lüftung`/`Berechnung LU` → `Erzeugung` → `Resultate`;
Data tables: `Klimadaten` (climate), `Std` (full-load hours and ventilation/hot-water parameters), `KZ_Raum_2024` (KPI matrix, i.e. the named range `Res`), `Qhc_Klimastat` (cooling/heating load intensities), `Nutzungsgrad` (heat-generator catalogue), `Begriffe` (trilingual dictionary/labels).

## 0.5 Worksheet List (Gebäude-Tool V221)

| Worksheet | Visibility | Rows×Cols | Formula cells | Role |
|---|---|---|---|---|
| Lizenzieren | veryHidden | 2:40 | 0 | Legacy licensing UI (deactivated in V221) |
| Anleitung | visible | 1:30 | 26 | Trilingual instructions; macro for adding/removing building worksheets |
| Begriffe | veryHidden | 1:301 | 295 | Trilingual dictionary; 45 room-use names (dropdown source `B13:F57`); label column F |
| **Gebäude** | visible | 1:87 | 555 | Building input sheet: 21 room rows + Total/Rechenwert + GF/EBF + Allg. Gebäudetechnik |
| **Lüftung** | visible | 1:32 | 135 | 16 ventilation systems (LA01–LA16); fan/cooling/heating/humidification/dehumidification results |
| **Erzeugung** | visible | 1:37 | 159 | 3 heat-generation groups (Kälte/Wärme/WW) + electricity generation (PV/WKK) |
| **Resultate** | visible | 1:71 | 248 | Energieträger × use Endenergie table + NEGF/PEne/THGE weighting + per-area indicators |
| Nutzungsgrad | veryHidden | 2:41 | 85 | Heat-generator catalogue (KE01–06, WE01–16, W01–13): Nutzungsgrad, Energieträger, Hilfsenergie |
| **Berechnung LU** | veryHidden | 1:328 | 13 466 | AHU physics engine: temperature-bin h-x method (core) |
| **Klimadaten** | veryHidden | 1:65 | 485 | 40 stations: design temperatures, HDD, air pressure, temperature-bin hours, humidity sequences |
| KZ_Raum_2024 | veryHidden | 2:51 | 631 | Room KPI matrix (named range `Res` = `$B$7:$AV$51`) |
| Qhc_Klimastat | veryHidden | 1:51 | 727 | Cooling/heating load intensities for 40 stations × 45 room uses (Raumdaten copy) |
| Std | veryHidden | 1:50 | 119 | Copy of Raumdaten `Volll_Lüft` + ventilation/hot-water parameters (source note `Std!L2`) |

## 0.6 Unit System and Naming Conventions

- Energy: `MWh` (internal to the worksheets) / `kWh/m²` (per-area indicators); power: `kW`; airflow: `m³/h`.
- Moist air: temperature `T [°C]`; humidity ratio `x [g/kg]` (internally the UDF `EnthalpieA` works in g/kg, converted by `/1000`); relative humidity `rF [%]` (mostly used as a 0–1 fraction at UDF call sites, see Chapter 1, §1.9); air pressure `p [mbar]`; enthalpy `h [kJ/kg]`.
- Physical constants (`Berechnung LU!N19:N25`): `p` (station air pressure), `cpl=1.006 kJ/kgK`, `cpw=1.86 kJ/kgK`, `cw=4.19 kJ/kgK`, `ρ=1.15 kg/m³`, `r0=2501.6 kJ/kg (0°C)`, `r100=2256 kJ/kg (100°C)`.
- German quantity symbols: `t_A` outdoor temperature, `t_ZUL` supply-air temperature, `t_Raum` room temperature, `x` humidity ratio, `φ/rF` relative humidity, `h` enthalpy, `η_WRG` heat-recovery efficiency, `SFP` specific fan power `[W/(m³/h)]`.

## 0.7 Known Quirks and Caveats (Observations, Not Judgments)

1. **The `TaupunktA` UDF is commented out** (`FeuchteLuft_Formeln.bas`, lines 90–99), yet `Berechnung LU` columns AQ/AS still call it → cached results `#NAME?` / `#VALUE!`. This column chain (ZUL dew-point control) **does not participate** in the results in the current version (the downstream of column AS is unused).
2. **Inconsistent relative-humidity units**: the `Klimadaten` header states `[%]`, but the values are 0–1 fractions (e.g. 0.88); the UDFs `AbsFeuchte/RelFeuchte` expect 0–1 fractions, and `EnthalpieR`'s comment claims `%`, although its formula is only self-consistent for fractions (see §1.9).
3. **The offsets of `Gebäude!N9/O9` (the Res column selector for Lüftung) for the Zielwert/Bestand (target/existing) value ranges appear too small** (+6/+12 vs. +7/+14): Zielwert looks up `AL` (Beleuchtung power) instead of `AM` (Lüftung power), and Bestand looks up `AR`/`T` instead of `AT`/`V`. The Standard range is correct (verified against cached values). When porting, correct the offsets according to the matrix column definitions or preserve the original behavior.
4. **Risk of stale data**: `Std`, `Qhc_Klimastat`, and `KZ_Raum_2024` are static copies / manual data from the Raumdatenblätter; external link `[3]` points to `SIA2024_Raumdatenblätter_dfi_V221_20241117.xlsm` (which does not match the release file name), and links `[1]` (Lüftung_20201113.xlsm) and `[4]` (Arealbewertungstool) are broken / cached-only.
5. **Denominator of the per-area indicators**: `Gebäude!D39` (EBF) only sums the areas of rooms with `C12:C32 = TRUE` (EBF flag) and multiplies by `(100+D37)%` (Anteil Konstruktionsfläche, default 10%).
6. **Column `Std!N` (Ventilatorregelung Standard) and the J columns (Regelung) of `Gebäude`/`Lüftung`** are two independent sets of inputs: `Std` provides the standard control mode per use (a data attribute), while `Lüftung!J7` is the project's actual control mode for that system (it determines the stages and the full-load hours in `Berechnung LU`).
7. **Rounding is normative**: `ROUND(I×1000/H, -1)` (Lüftung!K7) and `ROUND(H7*1000/G6,-1)` (Berechnung LU!J7) round the full-load hours to the nearest 10 h — this is part of the published values and must be preserved when porting.
8. **Protection passwords are recoverable** (`lockStructure` etc.; the passwords are in the VBA source) — commercial packaging rather than cryptographic security.
9. **In `KZ_Raum_2024`, row 3's index columns (B3=1, C3=2, …) coexist with the SIA codes in column A (1.1…12.12) and the internal codes in column AA (1.01…12.12)**; the lookup key of `Res` is the room-use name in column B (German).
10. **`Fallunterscheidung.bas` (Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul) is actually referenced by columns `Berechnung LU!BB:BE`** (an earlier assessment misjudged it as dead code; a full-table search confirmed that 61×2 bin rows call them, and `#NAME?` occurs only for `TaupunktA`). This module is **live code** and must be implemented as well when porting.
11. **`Lüftung!U32:Z32` is mis-wired**: `U32←'Berechnung LU'!V7` (actually Entfeuchtung Kühlung), `W32←X7` (Entf. Erwärmung), `Y32←T7` (Erwärmung Befeuchtung) — i.e. the headers and the actual values of the three column pairs "Befeuchtung / Entf. Kühlung / Entf. Erwärmung" are shifted by one pair as a whole, and `Resultate!C37/C38` read their values along the same mis-wired chain. In the example building all three pair values are ≈0, so this was not exposed; when porting, re-wire according to the semantics of `Berechnung LU` rows 254–258 (Chapter 4, §4.14-8).
12. **Other `Berechnung LU` quirks**: the energy sum starts at row 122 (excluding the −25 °C bin), the `CC183` power maximum starts at row 133 (−10 °C), the SOLL block (rows 189–249) is dormant (climate cells 0, air pressure `#REF!`), `T{n}=MIN(single-argument)` is a no-op, columns AD/AE are draft columns (`AD=n−122`, AE has no downstream), the energy-price cells are empty → costs are always 0, and column `BU` contains a `#REF!` dead branch (triggered only when Quellluft and I21≠0). See Chapter 4, §4.14.
13. **Two copy-paste errors in the `Resultate` weighting rows**: `I21` (NEGF·Prozessanlagen) mistakenly uses the THGE weight column Y (= 2.923, same as `I25`); `G22/F22` (PEne·Geräte) duplicates column E (Allg. Gebäudetechnik, 146.99 MWh / 22.57 kWh/m²). Both were confirmed with cached values (Chapter 5, §5.10).

## 0.8 How to Read Each Formula

Formula entries in every chapter uniformly follow the structure below:

> **Formula n — Name**
> - Mathematical form (symbolic)
> - Workbook implementation (Excel original + cell)
> - Units
> - Derivation (starting from the physical definition)
> - Assumptions (constants, simplifications, normative rounding)
> - Scope of validity (input domain, boundaries, failure conditions)
> - Cell provenance (first-level reference chain)

Numerical examples are based on the cached dump values and state their input premises (station, value range, system).
