# Chapter 2 — Room KPI Derivation (Gebäude Sheet and the KZ_Raum_2024 Matrix)

> Core area: `KZ_Raum_2024` (KPI matrix, named range `Res` = `KZ_Raum_2024!$B$7:$AV$51`), `Gebäude!A10:W39` (room inputs and totals), `Gebäude!A43:L62` (Allg. Gebäudetechnik)
> Dependencies: `Std!B6:I50` (ventilation/hot-water parameters), `Qhc_Klimastat!D7:O51` (heating/cooling load intensities), `Begriffe!F13:F57` (room-use names)

## 2.1 Chapter Positioning

This chapter answers one question: **after the user selects a room use and enters the NGF, how are the individual power values (kW) and annual energies (MWh) derived from the SIA 2024 room characteristic values (Kennzahlen)**. The derivation chain has three layers:

1. **KPI matrix layer** (`KZ_Raum_2024`): a two-dimensional numeric table of 45 room uses × (energy kWh/m² + power W/m²) × (Standard/Zielwert/Bestand), in which the Klimakälte/Heizwärme columns are climate-dependent formulas (referencing `Qhc_Klimastat`).
2. **Lookup layer** (`Gebäude!F12:W32`): `VLOOKUP($B{n}, Res, 列号, FALSE)` exact-matches on the room-use name, then multiplies by NGF/1000 to obtain kW and MWh.
3. **Totals layer** (`Gebäude!D33:W39`): Total row 33 → Rechenwert row 35 (overridable by external values) → per-area indicators (divided by EBF).

## 2.2 KPI Matrix Layout (KZ_Raum_2024)

**Rows**: 7–51 = 45 room uses (column A = SIA codes 1.1…12.12; column B = use names, i.e. the `Res` lookup keys; column AA additionally holds a set of internal codes 1.01…12.12 and 45 name copies, used by the `Leistung` block).
**Columns** (counting B as `Res` column 1):

| Res column | Sheet column | Content | Unit |
|---|---|---|---|
| 1 | B | Room-use name (lookup key) | – |
| 2–8 | C–I | Energy Standard: Geräte, Prozessanlagen, Beleuchtung, Lüftung, Klimakälte*, Heizwärme*, Warmwasser | kWh/m² |
| 9 | J | (empty) | |
| 10–16 | K–Q | Energy Zielwert (same 7 items) | kWh/m² |
| 17 | R | (empty) | |
| 18–24 | S–Y | Energy Bestand (same 7 items) | kWh/m² |
| 25–26 | Z–AA | Internal codes (1.01…12.12) and name copies | – |
| 27–33 | AB–AH | Power Standard: Geräte, Prozessanlagen, Beleuchtung, Lüftung, Klimakälte*, Heizwärme* | W/m² |
| 34–40 | AI–AO | Power Zielwert (same 6 items) | W/m² |
| 41–47 | AP–AV | Power Bestand (same 6 items) | W/m² |

\* The Klimakälte and Heizwärme columns (12 columns in total across energy and power) are **not static values** but formulas: `=Qhc_Klimastat!<D…O>{行}`. For example `KZ_Raum_2024!G7: =Qhc_Klimastat!E7` (Einzelbüro row: `G11 = Qhc_Klimastat!E11 = 14.43 kWh/m²` Klimakälte Standard; `AG11 = Qhc_Klimastat!D11 = 43.66 W/m²` Klimakälte power Standard). The remaining 5 categories (Geräte/Prozess/Beleuchtung/Lüftung/Warmwasser) are **hard-coded values** (a snapshot from the publication of the Raumdatenblätter).

**Verification example** (Einzel-, Gruppenbüro, row 11, Standard): C11=32.01 (Geräte energy), E11=13.446 (Beleuchtung), F11=4.443 (Lüftung), G11=14.430 (Klimakälte, climate-dependent), H11=10.762 (Heizwärme), I11=2.595 (Warmwasser); AC11=11 (Geräte power), AF11=1.139 (Lüftung power), AH11=19.823 (Heizwärme power).

## 2.3 Formula 1 — Res Column Selector (Wertebereich switching)

**Mathematical form**: the user selects a value range (`Gebäude!B5`: Standard/Zielwert/Bestand, compared against `Begriffe!F76/F77`), and the base column number $c_0$ is shifted to obtain the target column $c$:

$$
c = \begin{cases} c_0 & \text{Standard}\\ c_0 + 7\ (功率) \text{ 或 } c_0 + 8\ (能量) & \text{Zielwert}\\ c_0 + 14\ (功率) \text{ 或 } c_0 + 16\ (能量) & \text{Bestand}\end{cases}
$$

**Workbook implementation** (`Gebäude!F9`, representative of the power columns):

```
=IF($B5=Begriffe!$F76, F8, IF($B5=Begriffe!$F77, F8+7, F8+14))
```

(`Gebäude!G9` uses `+8/+16` for the energy columns; `B5` is the value-range selection cell, and `F76/F77` are the labels for "Standard"/"Zielwert" in the trilingual dictionary.)

**Unit**: – (column number).

**Derivation**: the matrix's three blocks (Standard energy C–I, Zielwert energy K–Q, Bestand energy S–Y; power blocks AC–AH/AJ–AO/AQ–AV) are arranged in `Res` at fixed intervals: energy blocks are 8 columns apart (C→K→S because of the empty columns J/R between blocks), power blocks are 7 columns apart (AC→AJ→AQ). The selector translates this user input — the value range — into the VLOOKUP column argument.

**Assumptions**: the matrix column layout is fixed; `B5` can only take one of the three dictionary labels.

**Scope**: all 14 column selectors in `Gebäude!F9:W9`. **Known deviation**: the Lüftung columns (N9/O9) use offsets +6/+12 and +7/+14, inconsistent with the actual matrix layout (which should be +7/+14, +8/+16) → under Zielwert/Bestand, the Lüftung power/energy lookups hit the Beleuchtung/Prozessanlagen columns (see README §0.7-3). The Standard value range has been verified correct.

**Cell provenance**: `Gebäude!F9,G9,H9,I9,J9,K9,N9,O9,Q9,R9,T9,U9,W9`; the base column numbers are stored in `Gebäude!F8:W8` (F8=28, G8=2, H8=29, I8=3, J8=30, K8=4, N8=31, O8=5, Q8=32, R8=6, T8=33, U8=7, V8=8, W8=8).

## 2.4 Formula 2 — Room-Row Power/Energy Derivation (the core lookup formula)

**Mathematical form**: for room row n (12≤n≤32), use name $B_n$, NGF $A_n$ (`D{n}`):

$$
P_{n,use} = k_{use}(B_n)\cdot\frac{A_n}{1000}\ [\mathrm{kW}],\qquad E_{n,use} = k_{use}(B_n)\cdot\frac{A_n}{1000}\ [\mathrm{MWh}]
$$

where $k_{use}$ is the characteristic W/m² (power) or kWh/m² (energy) value for the corresponding use × value range (looked up in `Res`).

**Workbook implementation** (`Gebäude!F12`, Geräte power):

```
=IF($B12="",0, VLOOKUP($B12,Res,F$9,FALSE))*$D12/1000
```

The same formula pattern covers `Gebäude!F12:W32`; the column mapping is:

| Target | Formula column | Res column (Standard) | Meaning | Output unit |
|---|---|---|---|---|
| F | `VLOOKUP($B12,Res,F$9,FALSE)` | AC (28) | Geräte power | kW |
| G | `…,G$9,…` | C (2) | Geräte energy | MWh |
| H | `…,H$9,…` | AD (29) | Prozessanlagen power | kW |
| I | `…,I$9,…` | D (3) | Prozessanlagen energy | MWh |
| J | `…,J$9,…` | AE (30) | Beleuchtung power | kW |
| K | `…,K$9,…` | E (4) | Beleuchtung energy | MWh |
| N | `…,N$9,…` (with `IF(L12=FALSE,0,…)` added) | AF (31) | Lüftung power | kW |
| O | `…,O$9,…` (with `IF(L12=FALSE,0,…)` added) | F (5) | Lüftung energy | MWh |
| Q | `…,Q$9,…` (with `IF(P12=FALSE,0,…)` added) | AG (32) | Raumkühlung power | kW |
| R | `…,R$9,…` (with `IF(P12=FALSE,0,…)` added) | G (6) | Raumkühlung energy | MWh |
| T | `…,T$9,…` (with `IF(S12=FALSE,0,…)` added) | AH (33) | Raumheizung power | kW |
| U | `…,U$9,…` (with `IF(S12=FALSE,0,…)` added) | H (7) | Raumheizung energy | MWh |
| W | `…,W$9,…` | I (8) | Warmwasser energy | MWh |

**Unit derivation**: $k$ [W/m²]×$A$ [m²] = [W]; ÷1000 → [kW]. The energy version is analogous: kWh/m²×m² = kWh; ÷1000 → MWh. **1 kWh = 0.001 MWh**.

**Assumptions**: ① `VLOOKUP`'s 4th argument FALSE (exact match) — the room-use name must exactly match column B of `Res` (guaranteed by the data-validation dropdown); ② empty-use rows (B empty) output 0; ③ power scales linearly with NGF (an early-design-phase assumption, no simultaneity reduction); ④ energies are annual values.

**Scope**: rows `Gebäude!12:32` (21 room rows). Lüftung (N/O) is counted only when `L{n}≠FALSE` (a ventilation system is selected); Raumkühlung (Q/R) only when `P{n}=TRUE` (gekühlt); Raumheizung (T/U) only when `S{n}=TRUE` (beheizt) — implemented via `IF(flag=FALSE,0,…)`.

**Cell provenance**: `Gebäude!F12:W32` (21 rows × 14 columns); lookup-key column `B12:B32`; NGF column `D12:D32`; flag columns `C12:C32` (EBF), `L12:L32` (system), `P12:P32` (gekühlt), `S12:S32` (beheizt).

## 2.5 Formula 3 — Ventilation Volume Flow (including process air)

**Mathematical form**:

$$
\dot V_n = \big(q_{hyg}(B_n) + q_{proz}(B_n)\big)\cdot A_n \quad[\mathrm{m^3/h}]
$$

where $q_{hyg}$ and $q_{proz}$ are the hygienic (hygienebedingt) and process (prozessbedingt) fresh-air rates per unit area, taken from the `Std!D/E` columns.

**Workbook implementation** (`Gebäude!M12`):

```
=IF($B12="",0, VLOOKUP($B12,Std!$B$6:$H$50,M$8,0))*$D12
 +IF($B12="",0, VLOOKUP($B12,Std!$B$6:$H$50,4,0))*$D12
```

`M8=3` → `Std!D` (hygienic fresh air in m³/(h·m²)); the 4th column → `Std!E` (process fresh air). The `L{n}` column selects the system (LA01…LA16 or "-").

**Unit**: [m³/(h·m²)]×[m²] = [m³/h].

**Verification example**: `Gebäude!M12 = 2.07143×2500 + 0×2500 = 5178.6 m³/h` (Einzelbüro: `Std!D10=2.0714`). Parkhaus special case: `Lüftung!D12 = Gebäude!D21*Std!E47 = 670×2 = 1340 m³/h` (Parkhaus has no hygienic fresh air, D47=0, E47=2 process fresh air).

**Assumptions**: hygienic fresh air follows the SIA 2024 standard values (`Std` table, 29 m³/h·P version, see Chapter 3); process fresh air appears only for uses where `Std!E` is non-zero (Küche, Produktion, Labor, Schwimmhalle, Parkhaus, etc.).

**Cell provenance**: `Gebäude!M12:M32`; `Std!D6:D50`, `Std!E6:E50`; `Lüftung!D12` (Parkhaus override example).

## 2.6 Formula 4 — Warmwasser Daily Demand

**Mathematical form**:

$$
V_{WW,n} = q_{WW}(B_n)\cdot A_n \quad[\mathrm{l/d}]
$$

$q_{WW}$ is the `Std!I` column (Warmwasserbedarf pro m², = `Std!H` (l/(d·P)) ÷ `Std!C` (m²/P)).

**Workbook implementation** (`Gebäude!V12`):

```
=IF($B12="",0, VLOOKUP($B12,Std!$B$6:$I$50,$V$8,0))*$D12
```

`V8=8` → `Std!I` column (the 8th column of the lookup range `$B$6:$I$50` = I, i.e. "Warmwasserbedarf pro m²"; `Std!I6 = H6/C6` is a derived formula).

**Unit**: l/d. **Verification**: `V12 = 0.21429×2500 = 535.7 l/d` (Einzelbüro `I10 = 3/14 = 0.21429`). This value feeds the WW power conversion in Chapter 5 (×4.186/3.6×50 K).

**Cell provenance**: `Gebäude!V12:V32`; `Std!H6:H50` (l/(d·P)), `Std!I6:I50` (l/(d·m²)), `Std!C6:C50` (m²/P).

## 2.7 Formula 5 — Totals: Total, Rechenwert, GF, EBF

**Total row 33** (`Gebäude!D33:W33`): `=SUM(D12:D32)` etc., summing column by column. **Rechenwert row 35** (`Gebäude!D35:W35`): `=IF(D34<>"",D34,D33)` — if row 34 ("Werte aus anderen Quellen") contains a value it is used, otherwise the Total is taken. This is the interface that lets the user override the room totals with external calculations.

**Geschossfläche (GF)** (`Gebäude!D38`):

$$
A_{GF} = A_{EBF,rec}\cdot\Big(1+\frac{k_{Konstr}}{100}\Big),\qquad k_{Konstr} = \text{Gebäude!D37} \text{（Anteil Konstruktionsfläche，默认 10 %）}
$$

Implementation: `=D35*(100+D37)%`.

**Energiebezugsfläche (EBF)** (`Gebäude!D39`):

$$
A_{EBF} = \Big(\sum_{n:\,C_n=TRUE} D_n\Big)\cdot\Big(1+\frac{k_{Konstr}}{100}\Big)
$$

Implementation: `=SUMIF(C12:C32,TRUE,D12:D32)*(100+D37)%`. **Key point**: EBF only sums the areas of rooms whose EBF flag is TRUE (e.g. Parkhaus C21=FALSE is excluded), then multiplies by the construction-area factor.

**Per-area indicators** (`Gebäude!F39:W39`; row 38 has the same structure): `=F35*1000/$D$39` (kW→W, divided by EBF m² → W/m²); energy: `=G35*1000/$D$39` (MWh→kWh, ÷EBF → kWh/m²). **Verification**: `G39 = 129.6861×1000/6512 = 19.9149 kWh/m²` (consistent with `Resultate!G21`).

**Cell provenance**: `Gebäude!D33:W33` (Total), `D34:W34` (external values), `D35:W35` (Rechenwert), `D37` (k_Konstr=10), `D38` (GF), `D39` (EBF), `F38:W39` (per-area indicators).

## 2.8 Formula 6 — Allg. Gebäudetechnik (AG01–AG10)

**Structure** (`Gebäude!A43:L58`): 10 building-services categories (Notlicht, Beschattung manuell/automatisch, Gebäudeautomation, Einbruchmeldeanlage, Kleinstverbraucher, Zentrale Parkuhr, Zutrittskontrolle, Aufzug, plus an empty AG10 row). Three input forms:

**(a) By area intensity** (kWh/m², e.g. AG01 Notlicht): `Gebäude!E47: =IF(B47="",0,VLOOKUP(B47,$B$69:$F$85,C47+2,0))` (looks up the `$B$69:$F$85` catalogue by intensity tier C47=1/2/3 → tief/mittel/hoch); energy `I47: =E47*G47/1000` (G47 = area, default `=D$35`); power `L47: =IF(B47="",0, I47*1000/IF(OR(K47="",K47=0),J47,K47))` (energy ÷ full-load hours; J47 is taken from catalogue column 6, K47 permits a project override).

**(b) By unit count** (kWh/Stk, e.g. AG07 Parkuhr): `E54=1752` (kWh/Stk), `H54=1` (Stk), `I54: =E54*H54/1000`.

**(c) Catalogue table** (`Gebäude!B66:G85`): source note "Minergie Strommodell, Bericht Stefan Gasser 2018"; one row per category: columns D/E/F = kWh/m² (or kWh/Stk) values for intensity tiers 1/2/3, column G = full-load hours (e.g. Notlicht 8760, Beschattung 200/300 h, Aufzug 500 h).

**Totals** (`Gebäude!I58/L58`): `=SUM(I47:I57)` (energy MWh), `=SUM(L47:L57)` (power kW); per-area indicators `I62/L62: =I58*1000/$D$39`. **Verification**: `I58 = 54.6442 MWh` → `Resultate!E7 = Gebäude!I58`.

**Cell provenance**: `Gebäude!A43:L58`, `B66:G85` (catalogue), `I62/L62` (indicators).

## 2.9 Data-Flow Verification (handoff to Chapter 5)

| Quantity | Formula chain | Value (example building) |
|---|---|---|
| Geräte power/energy | `Gebäude!F35/G35` → `Resultate!F7/G7` | 45.57 kW / 129.69 MWh |
| Beleuchtung | `Gebäude!J35/K35` → `Resultate!J7/K7` | 41.38 kW / 59.90 MWh |
| Raumkühlung | `Gebäude!Q35/R35` → `Erzeugung!L7` chain, `Resultate!N7` | 167.14 kW / 61.21 MWh |
| Raumheizung | `Gebäude!T35/U35` → `Erzeugung!L16` chain, `Resultate!P7` | 103.32 kW / 68.83 MWh |
| Warmwasser | `Gebäude!V35/W35` → `Erzeugung!L25` chain | 835.71 l/d / 10.12 MWh |
| Allg. Gebäudetechnik | `Gebäude!I58/L58` → `Resultate!E7/D7` | 54.64 MWh / 55.82 kW |

## 2.10 Porting Key Points

1. In a port, the `Res` matrix should be expressed as a structured dataset (room_use × value_kind × {W/m², kWh/m²}), preserving the Klimakälte/Heizwärme dependence on the climate station (Qhc) — they are **functions**, not constants.
2. The VLOOKUP exact match can be replaced by a key-value lookup; use the German names from `Begriffe!B13:F57` as the room-use keys (or the SIA codes 1.1…12.12, but matrix column B stores the names).
3. Keep the gating semantics of `IF(flag=FALSE,0,…)` (Lüftung system, gekühlt, beheizt) and the `IF(空行,0)` guard.
4. Keep the N9/O9 column selectors as-is or fix them according to the matrix definition (see the deviation note in §2.3); the EBF SUMIF and the construction-area factor (10 %) are normative values.
