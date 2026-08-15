# Gebäude-Tool (SIA 2024) Calculation Model Textbook

> Complete calculation textbook · written from the `.analysis` extracts
>
> Subject: `data/raw/2024_Gebaeude-Tool_dfi_V221.xlsm` (13 worksheets, ≈51 300 non-empty cells, ≈16 900 formula cells)
> Companion dataset: `2024_Raumdatenblätter_dfi_V221.xlsm` (room data source, 45 room use types)
>
> Language convention: the body text is written in Chinese; technical terms keep the German original (with Chinese and English glosses at first occurrence); formula references retain the Excel/VBA syntax verbatim.

---

## 0.1 Document Map

| Section | File | Content |
|---|---|---|
| Introduction (this file) | `README.md` | Tool positioning, data sources, cell-reference conventions, calculation-flow overview, worksheet list, unit system, known quirks |
| Chapter 1 | `ch01-湿空气物理-Glück多项式与UDF.md` | Moist-air physics: derivation, units, assumptions, scope of validity and all call sites of the 8 UDFs — Glück saturation-pressure polynomial, enthalpy/humidity ratio/relative humidity/dew point, etc. |
| Chapter 2 | `ch02-房间KPI派生.md` | Room KPI derivation: `KZ_Raum_2024` matrix, `Res` named range, `Gebäude` room-row VLOOKUP chain, EBF/GF (energy reference area / floor area) weighting, Allg. Gebäudetechnik |
| Chapter 3 | `ch03-通风全负荷小时.md` | Ventilation full-load hours: `Std` table (copy of Raumdaten `Volll_Lüft`), mechanism of selection by Regelung (control mode), use in the AHU engine |
| Chapter 4 | `ch04-AHU温度区间法.md` | AHU temperature-bin method (`Berechnung LU`): meteorological bin h-x chain, three fan stages P∝V^2.5, WRG/KRG (heat/cold recovery), four control cases (Fall 1–4), energy summary |
| Chapter 5 | `ch05-产热与Resultate汇总.md` | Heat generation and Resultate summary: `Nutzungsgrad` catalogue, the three heat-generator groups in `Erzeugung`, Endenergie/Energieträger allocation, `Resultate` weighting (NEGF/PEne/THGE) |
| Chapter 6 | `ch06-气候数据.md` | Climate data: `Klimadaten` 40 stations, air pressure (barometric-height formula), HDD, design temperatures, temperature-bin hours and humidity sequences, `Qhc_Klimastat` |
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
- Cell notation: `工作表!列行` (worksheet!column-row), e.g. `Gebäude!F12`; ranges e.g. `KZ_Raum_2024!$B$7:$AV$51`.
- Formula originals are quoted in a monospace font (`` ` ``), e.g. `` `VLOOKUP($B12,Res,F$9,FALSE)` ``; `Res` is the named range.
- **Row-variable convention**: whenever a formula repeats along rows, the row number `n` denotes a generic row, and a concrete example row is given (e.g. `n=121`).
   For example, the temperature-bin rows of `Berechnung LU` are written as `X{n}` (IST (actual) block `n=121…181`, SOLL (target) block `n=189…249`, t_A = −25…+35 °C).
- Cross-workbook references (external links) are marked with the dump notation `[3]` etc. (see Section 0.7).

## 0.4 Calculation-Flow Overview

```
项目输入 (Gebäude!B2..J2, Klimastation via Gebäude!D2)
        │
        ▼
┌───────────────────────────── Gebäude 表 ─────────────────────────────┐
│ 21 个房间行 (12..32)：Raumnutzung 下拉 (Begriffe!F13:F57)             │
│   → A 列反查 SIA 代码 (INDEX/MATCH Begriffe!B13:F57)                 │
│   → EBF 标志 (C)、NGF (D)、Anteil (E)                                │
│   → 各用途 Leistung/Energie (F..K)  ← VLOOKUP(B, Res, 列号) × NGF/1000│
│   → Lüftung 系统 (L)、Volumenstr. (M) ← VLOOKUP(B, Std!B:H)          │
│   → Raumkühlung (P..R)、Raumheizung (S..U) ← VLOOKUP(B, Res) × NGF/1000│
│   → Warmwasser Bedarf (V) ← VLOOKUP(B, Std!B:I)；Energie (W) ← Res   │
│   → Total 行 33 → Rechenwert 行 35 (可被 "Werte aus anderen Quellen"│
│     行 34 覆盖) → GF/EBF 行 37..39                                    │
│   → Allg. Gebäudetechnik 行 47..57 (AG01..AG10, Minergie-Strommodell)│
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────────── Lüftung 表 ──────────────────────────────┐
│ 16 个系统行 (LA01..LA16, 7..22)                                       │
│   C: Volumenstr. Standard ← SUMIF(Gebäude!L12:L32, 系统, M12:M32)    │
│   F: Rechenwert = C 或 E(Projekt)；H: 风机功率 = F×SFP/1000           │
│   J: Regelung (einstufig/zweistufig/stufenlos)                        │
│   K: Vollast. = ROUND(I×1000/H, -1)（由 AHU 结果反推）                │
│   Q..Z: 空气冷却/加热/加湿/除湿 Leistung+Energie ← Berechnung LU 结果 │
│   Total 行 23                                                        │
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────── Berechnung LU 表（物理引擎）────────────────┐
│ 行 6：单系统输入（= Lüftung!32 模板行，宏复制到 7..22）               │
│ 行 7：Resultate（风机电能 H7、各处理段功率/能量 P7..Y7）              │
│ 行 11..55：IST/SOLL 输入（面积、层高、过滤器、风机效率级、WRG/KRG、  │
│            冷却/加热/加湿/除湿设定、运行时间表、温度曲线）            │
│ 行 63..67：分档运行时间加权风机功率与平均风量                        │
│ 行 68..70：SIA 全负荷小时 (Std!Q:V 按 Regelung) 与合理性检验         │
│ 行 100..114：电机效率级 (IE5..Eff3 × 功率带) 与过滤器压降            │
│ 行 121..181：IST 温度区间焓湿计算（61 区间 −25…+35 °C，逐区间：      │
│    AUL → 防冻 → nWRG → MIL(焓/温) → 冷盘管链 A/C/D1/D2 → Fall 1..4 →│
│    Zuluft soll/ist、Raum；每小时功率 × 区间小时数 = 区间能量）        │
│ 行 189..249：SOLL 区间块（休眠）；行 182/183：年度能量和/功率最大    │
│ 行 254..260：年度能量汇总（kWh/kW；行 7 的 MWh 等价 Q7..Y7、H7）     │
│ 行 261+：经济性（电价、运行成本）                                    │
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────────── Erzeugung 表 ────────────────────────────┐
│ Kälte (行 7..10)：需求 ← Gebäude!Q/R35 + Lüftung!Q/R23               │
│ Wärme (行 16..19)：需求 ← Gebäude!T/U35 + Lüftung!S/T23              │
│ WW   (行 25..28)：需求 ← Gebäude!V/W35（V×4.186/3.6×50/L29/1000）    │
│ 每台：Deckungsgrad F/G%、Speicher-/Verteilverluste H/J%              │
│   L/M = 需求×Deckungsgrad×(100+Verluste)%                            │
│   N = M×1000/L（Volllaststunden）；P/Q = L/M÷Nutzungsgrad(项目或标准) │
│   R = Energieträger ← VLOOKUP Nutzungsgrad 目录                      │
│ Elektrizitätserzeugung (行 34..37)：PV/WKK 装机与效率                  │
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────────── Resultate 表 ────────────────────────────┐
│ Energieträger × 用途矩阵 (行 7..15)：El/HEL/Gas/Pell/HSch/StH/Bio/FW │
│   Geräte/Prozess/Beleuchtung ← Gebäude 行 35                          │
│   Lüftung ← Lüftung!H23/I23；Kühlung/Heizung/WW ← Erzeugung SUMIF     │
│ 加权行 21/22/25：NEGF (W)、PEne (X)、THGE (Y) 权重 SUMPRODUCT         │
│ 能量平衡行 28..59：kWh/m²、kg/m² 单位面积指标                         │
└──────────────────────────────────────────────────────────────────────┘
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
12. **Other `Berechnung LU` quirks**: the energy sum starts at row 122 (excluding the −25 °C bin), the `CC183` power maximum starts at row 133 (−10 °C), the SOLL block (rows 189–249) is dormant (climate cells 0, air pressure `#REF!`), `T{n}=MIN(单参)` is a no-op, columns AD/AE are draft columns (`AD=n−122`, AE has no downstream), the energy-price cells are empty → costs are always 0, and column `BU` contains a `#REF!` dead branch (triggered only when Quellluft and I21≠0). See Chapter 4, §4.14.
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
