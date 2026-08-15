# Textbook Ch. 1–6 Formulas vs. Workbook Dumps — Cross-Verification Report

- Object under review: chapters 1–6 (ch01–ch06) of `Energytools_refactored-wt-计算模型教科书式文档-基于-analysis提取/docs/`
- Reference baseline: extraction artifacts of the main repository `Energytools_refactored/.analysis`
  - Cell-by-cell dumps: `.analysis/dumps/gebaeude/sheet_*.tsv`, `.analysis/dumps/raumdaten/sheet_14843_Volll_Lüft.tsv`
  - VBA sources: `.analysis/vba/gebaeude/FeuchteLuft_Formeln.bas`, `Fallunterscheidung.bas`
- Review method: machine verification (`verify/run-checks.js`, **672 assertions** in total) + manual spot checks. Numeric comparisons use a relative tolerance of ≤0.2 % (the chapters' rounding precision); encoding garbles in the dumps (e.g. `ZÃ¼rich`→`Zürich`) are treated as UTF-8 double-encoding artifacts; trailing values such as `6512.000000000001` are treated as Excel floating-point noise.
- Result summary: **668 passed / 3 failed / 1 warning** (the warning concerns the precision of a formula-citation wording; semantics identical)

| Chapter | Items (formula entries) | Result |
|---|---|---|
| Ch. 1 Moist-air physics (Glück polynomials & 8 UDFs) | 8 UDFs + call-site summary | **2 failed** (numerical checks of 1.5, 1.7); the rest passed |
| Ch. 2 Room KPI derivation | Formulas 1–6 + matrix/data flow | all passed |
| Ch. 3 Ventilation full-load hours | Formulas 1–3 + data table | passed (1 warning: the `I8` formula citation omits the sheet prefix) |
| Ch. 4 AHU temperature-bin method | Formulas 1–10 + 14 quirks | all passed (3 wording-simplification suggestions) |
| Ch. 5 Heat generation & Resultate aggregation | Formulas 1–6 + catalog/matrix | all passed |
| Ch. 6 Climate data | Formulas 1–3 + Qhc | all passed |

---

## 1. Failed items (3, all in Chapter 1 — the textbook text must be corrected)

### ❌ 1. Ch. 1 §1.7 — Erroneous check value of the dew-point power-law fit (T=0)
Textbook text (pre-correction, Chinese original): `T=0: p_s=2.8858·1.098^8.02≈6.02 mbar (true value 6.11, deviation 1.5 %)` (translated from the original Chinese)
Actual computation: `2.8858 × 1.098^8.02 = 6.1080 mbar` (deviation from the true value 6.11/6.112 is only **−0.03 % to −0.07 %**, not 1.5 %).
**Correction proposal**: change to `≈6.11 mbar (deviation <0.1 %)`.

### ❌ 2. Ch. 1 §1.7 — Erroneous check value of the dew-point power-law fit (T=20)
Textbook text (pre-correction, Chinese original): `T=20: ≈24.9 mbar (true value 23.4, deviation 6 %)` (translated from the original Chinese)
Actual computation: `2.8858 × 1.298^8.02 = 23.374 mbar` (deviation from the true value 23.39 is only **−0.07 %**, not 6 %).
**Correction proposal**: change to `≈23.4 mbar (deviation <0.1 %)`; also note that the conclusion "less accurate than the Glück polynomial" does not hold at the two points 0/20 °C (the two are of equal accuracy there); use −20 °C (power law 1.218 vs. true value ≈1.254 mbar, deviation ≈−2.9 %, which supports the conclusion) or −30 °C as the check point instead.

### ❌ 3. Ch. 1 §1.5 / §1.10 — the `TemperaturH` numeric example's inputs do not match the check formula
Textbook text (1.5): `example n=121: TemperaturH(12.2406, 8.19…) → 21.27 °C`;
(1.10): `AN121 = TemperaturH(AP121, AO121) = 21.27 °C: enthalpy 12.24 kJ/kg, humidity ratio ~8.19 g/kg inverted ✓ (T=(12.24−8.19×2.5016)/(1.006+1.86×0.00819)≈21.3)` (translated from the original Chinese).
Measured in the dump (cached values):
- `Berechnung LU!AP121 = 21.39789189189189` (= `BM121`, the supply-air setpoint enthalpy), **not 12.2406**;
- `Berechnung LU!AO121 = 0` (temperature-controlled branch `X121`, humidity ratio 0 in the −25 °C bin), **not 8.19**;
- `AN121 = TemperaturH(21.3979, 0) = 21.3979/1.006 = 21.2703 °C` ✓ (the result 21.27 is correct);
- recomputed with the textbook's check formula: `(12.24−8.19×2.5016)/(1.006+1.86×0.00819) = −8.08 °C ≠ 21.27 °C` (12.2406 is in fact the MIL enthalpy of `N121`, unrelated to AN's input `AP121`).
**Correction proposal**: change the example to `TemperaturH(AP121, AO121) = TemperaturH(21.3979, 0) → 21.27 °C` (or cite another row and state its inputs).

---

## 2. Warning (1 — precision of a formula-citation wording)

### ⚠️ Ch. 3 §3.4 — the `Berechnung LU!I8` formula citation omits the same-sheet prefix
Chapter citation: `=IF(I6=Begriffe!F205,1,IF(I6=Begriffe!F206,2,IF(I6=Begriffe!F207,3,FALSE)))`
Dump text: `IF(I6=Begriffe!F205,1,IF('Berechnung LU'!I6=Begriffe!F206,2,IF('Berechnung LU'!I6=Begriffe!F207,3,FALSE)))`
(the workbook itself writes the 1st condition without a prefix and the 2nd/3rd with one — an inconsistent same-sheet citation style; semantics and results are fully identical, `I8=1` ✓).
**Correction proposal**: complete the `'Berechnung LU'!` prefix per the dump, or note "same-sheet citations omit the prefix".

---

## 3. Item-by-item verification results per chapter

### Ch. 1 Moist-air physics: Glück polynomials & 8 UDFs

| Item | Result | Source verification | Numerical-example verification |
|---|---|---|---|
| 1.1 Module overview | ✅ | All 8 `Public Function`s exist; `TaupunktA` is commented out as a whole block in `FeuchteLuft_Formeln.bas` lines 90–99 ✓; the module constants cpl=1.006, cpw=1.86, r0=2501.6, 611, 622 match the VBA verbatim ✓ | – |
| 1.2 Formula 1 saturation pressure (Glück polynomial) | ✅ | The ice/water two coefficient sets (−4.909965e-4, 8.183197e-2, …, −1.92e-9) match VBA's three inlined segments ✓; no workbook formula calls `Saettigungsdruck(` directly (dead code) ✓ | T=0 two-segment jump recomputed = +0.030 % (chapter 0.03 %) ✓ |
| 1.3 Formula 2 humidity ratio `AbsFeuchte` | ✅ | Call sites `Klimadaten!Q5:Q65`, `Berechnung LU!AA{n}` (incl. `100%` passed as decimal 1), `BL{n}` — formula shapes identical ✓ | `Q20 = AbsFeuchte(M20,N20,$F$44) = 1.501516` (chapter 1.5015) ✓; recomputed with full-precision Glück = 1.50152 ✓; `N20` cached 0.8816667 (chapter 0.8817 is display rounding) |
| 1.4 Formula 3 enthalpy `EnthalpieA` | ✅ | The 11 call columns (N/O/Y/AB/AE/AJ/AM/AS/AV/BM/BQ) have identical formula shapes cell by cell ✓ | `N121 = 12.240573` (chapter 12.2406) ✓ |
| 1.5 Formula 4 temperature from enthalpy `TemperaturH` | ❌ | Call site `AN{n}=TemperaturH(AP{n},AO{n})` ✓; VBA source identical ✓ | **example inputs wrong** (see failed item 3): actual `AP121=21.3979`, `AO121=0`; result 21.27 ✓ |
| 1.6 Formula 5 relative humidity `RelFeuchte` | ✅ | The 4 call sites (E/BK/BO/BV) are identical, incl. the `MIN(100%,…)`/`MIN(1,…)` saturation clamps ✓ | – |
| 1.7 Formula 6 dew point (`TaupunktR`/`TaupunktA`) | ❌ | `AQ121=TaupunktA(AR121,$N$19)` → cached `#NAME?` ✓; cascading `AS121` → `#VALUE!` ✓ (dead reference chain confirmed); `TaupunktR` has no formula calls ✓ | **power-law check value errors** (see failed items 1, 2) |
| 1.8 Formula 7 wet bulb `Feuchtkugel` | ✅ | VBA source (−5.809 + 0.058·φ + 0.697·T + 0.003·φ·T; sub-zero ×0.8+0.5) identical ✓; a full-sheet formula search finds no calls (dead code) ✓ | – |
| 1.9 Formula 8 enthalpy `EnthalpieR` | ✅ | VBA source `x = 0.622*(rF*100*ps)/(p*100−rF*100*ps)` confirms the ×100/÷100 redundancy and the misleading `rF [%]` comment ✓; no calls ✓ | – |
| 1.10 Call-site summary & consistency check | ✅ (except item 1.5) | The 5-UDF call-site table matches the dumps one by one ✓ | `Q20=1.5015` ✓, `N121=12.2406` ✓, `AN121=21.27` ✓ (input wording — see failed item 3) |

### Ch. 2 Room KPI derivation

| Item | Result | Source verification | Numerical-example verification |
|---|---|---|---|
| 2.2 KPI matrix layout | ✅ | 12 climate-column reference formulas such as `KZ_Raum_2024!G7=Qhc_Klimastat!E7`, `AG7=Qhc_Klimastat!D7` ✓; column A holds SIA codes 1.1…12.12, column AA internal codes 1.01…12.12 (`A51/AA51=12.12`) ✓ | row 11 (Einzel-, Gruppenbüro): all 9 values correct: C11=32.01, E11=13.4458, F11=4.4432, G11=14.4301, H11=10.7616, I11=2.5951, AC11=11, AF11=1.1393, AG11=43.6565, AH11=19.8234 ✓ |
| Formula 1 Res column selector | ✅ | `F9`/`G9` formulas verbatim-identical to the chapter text (+7/+14, +8/+16) ✓; `F8:W8` — all 14 base column numbers (28/2/29/3/30/4/31/5/32/6/33/7/8/8) ✓ | **known N9/O9 deviation confirmed**: `N9=+6/+12`, `O9=+7/+14` (inconsistent with the matrix layout; wrong columns looked up under Zielwert/Bestand) ✓ |
| Formula 2 room-row power/energy derivation | ✅ | `F12=IF($B12="",0,VLOOKUP($B12,Res,F$9,FALSE))*$D12/1000` identical to the source ✓; the 14-column VLOOKUP structure and the Lüftung/gekühlt/beheizt gating `IF(flag=FALSE,0,…)` are present ✓ | `F12=27.5 kW` (cached) ✓ |
| Formula 3 ventilation volume flow | ✅ | `M12` formula identical to the source (two-segment VLOOKUP over Std!D + Std!E) ✓ | `M12=5178.57` (2.07143×2500) ✓; Parkhaus special case `Lüftung!D12=Gebäude!D21×Std!E47=670×2=1340` ✓ |
| Formula 4 Warmwasser daily demand | ✅ | `V12` formula identical; `V8=8`→Std!I; `Std!I6=H6/C6` derived ✓ | `V12=535.714` (0.21429×2500) ✓; `Std!I10=3/14=0.214286` ✓ |
| Formula 5 Total/Rechenwert/GF/EBF | ✅ | `D38=D35*(100+D37)%`, `D39=SUMIF(C12:C32,TRUE,D12:D32)*(100+D37)%` identical to the source ✓ | GF=7249, EBF=6512 (cached 6512.000000000001, floating-point tail); `G39=19.9149` (129.6861×1000/6512) ✓ |
| Formula 6 Allg. Gebäudetechnik | ✅ | `E47` (intensity tier looked up in `$B$69:$F$85`), `I47=E47*G47/1000`, `L47` (energy÷full-load hours), `I58/L58=SUM(I47:I57)/SUM(L47:L57)`, `I62/L62` per unit area ✓ | `I58=54.6442 MWh`, `L58=55.8229 kW` ✓ |
| 2.9 Data-flow check | ✅ | Consistent with the `Resultate!F7/G7`, `Erzeugung!L7/L16/L25` chains ✓ | F35/G35=45.57/129.6861, J35/K35=41.3754/59.9020, Q35/R35=167.138/61.207, T35=103.3221 (chapter 103.32 rounded), U35=68.8339, V35=835.714, W35=10.1214 ✓ |

### Ch. 3 Ventilation full-load hours

| Item | Result | Source verification | Numerical-example verification |
|---|---|---|---|
| 3.2 Std table layout | ✅ | `Std!L2` comment "Quelle: SIA2024_Raumdatenblätter > tblVoll_Lüft", `L3` "prSIA 2024-C1:2024 (29 m³/h pro Person)" ✓; columns O/P are **static snapshots** (the source table's select-by-column-N logic lives in Raumdaten `Volll_Lüft` columns AJ/AK, confirmed by `AJ11=IF(AI11="einstufig",$E11,…)`) | `Std!Q10..V10 = 3900/3900/3290/2740/2160/1780` ✓; `Volll_Lüft` row 11 (Einzel-, Gruppenbüro) D/E/F/I/J/Q = 3900/3900/3290/2740/2160/1780 ✓; R11/S11 ratio formulas `F11/D11`, `J11/D11` ✓ (note: `Volll_Lüft` column A stores internal code 3.01; the SIA code 1.03 is in the source `Eingabedaten`; the chapter's "row 1.03" refers to the same row) |
| Formula 1 full-load-hours definition & conversion | ✅ | `K68`/`K69` formulas verbatim-identical to the chapter text (INDEX/MATCH over `Std!$Q$6:$V$50`, columns 1/3/5 and 2/4/6 selected by I8) ✓ | `K68=3900`, `K69=3900` (einstufig) ✓ |
| Formula 2 lookup by Regelung | ✅ (1 warning) | The `I8` mapping formula exists (see warning: prefix wording) ✓; `I6='Lüftung'!J32` → einstufig ✓ | `K68/K69=3900` ✓ |
| Formula 3 fan annual electrical energy & closed loop | ✅ | `H7=C259/1000`, `J7=ROUND(IF(G6=0,0,H7*1000/G6),-1)`, `Lüftung!K7=IF(H7=0,0,ROUND(I7*1000/H7,-1))`, `Lüftung!H7=F7*G7/1000` identical to the source ✓ | `H7=26.76514 MWh`, `J7=3900` (26.765×1000/6.8629=3900.0) ✓; `Lüftung!K7=3900` ✓ |
| 3.6 usage chain | ✅ | `K70=E7*K68/8760`, `M70=G6*K69/K68`, `I20=IF(E52=0,0,(E52*1000)/(3600*(K70/3600)*N23))` identical to the source ✓ | `K70=3819.227` (chapter 3819.2) ✓, `M70=6.862857` ✓, `I20=0` ✓; Kühlraum (Std row 49) Q..V all 0 ✓ |

### Ch. 4 AHU temperature-bin method

| Item | Result | Source verification | Numerical-example verification |
|---|---|---|---|
| 4.3 input block | ✅ | C6=8578.57, D6/E6=0, F6=0.8, G6=6.8629, K6=80, L6/M6=20/21, N6/O6=0/0, E11=500, E12=3, E16=G6/2, E17="IE5 - gefaked", E18=E7, E19/E20 tier formulas (trilingual labels) identical to the source, E28=0.8, E30/E31="ja", E32/E33=0, E34/E35=1, E36="Temperatur", E39..E52 coil flags and setpoints identical, S20/S21 comparison labels ✓ | motor efficiency tier `C108=MAX(C102:C107)=1` (IE5 row), `B102` power-band lookup ✓; filter `B110=0 Pa` ✓; freeze protection `F113=15.9556 kW` (chapter 15.96) ✓; temperature-curve breakpoints (B88:D91) and slopes (I88:J90) — all 8 values correct (−0.0270/0.0541/0/0.5/0) ✓; I58/I59/I60=50/15/15, L58=50, L61=80, M58=0.625 ✓ |
| Formula 1 bin hours | ✅ | `B121=Klimadaten!O5/8760*$K$68` identical to the source ✓ | B121=0 (−25 °C), B136=2.67123 (O20=6: 6/8760×3900), B168=59.65753 (O52=134: 134/8760×3900) ✓ |
| Formula 2 outdoor state & freeze protection | ✅ | `C{n}=Klimadaten!Q{k+30}`, `E{n}=MIN(100%,RelFeuchte(BR,C,$N$19))`, `G/DB/DC` three-branch freeze-protection formulas ✓ | row 168 state chain: C168=10.0367, E168=0.504877 ✓ |
| Formula 3 heat recovery WRG | ✅ | Five-column formulas I/J/K/L/M identical to the source (incl. `F168` summer flag, ε adjustment `MAX(…,0)`) ✓ | row 168: I168=23.6 (22+0.8×(24−22)), J168=20 (MIN), K168=0 (full bypass), L168=22, M168=10.0367 (humidity recovery E29=0 → x_A) ✓; BU168=24, BW168=10.0367 ✓ |
| Formula 4 mixed air MIL | ✅ | N..Y formulas identical to the source (incl. confirmation that `T168=MIN(single-param)` is a no-op) ✓ | row 168: N168=O168=S168=47.6506, P168=0, Q168=22, R168=X168=10.0367, T168=U168=W168=22, V168=0, Y168=47.6506 ✓ |
| Formula 5 cooling coil & linear cooling curve | ✅ | Z/AA/AB/AF/AG/AH/AI/AJ/AK/AL/AM formulas identical to the source (incl. the `1E+23` vertical-curve guard) ✓ | row 168: Z168=AF168=9, AA168=7.617, AG168=5.372, AK168=20, AL168=9.664, AM168=44.66 ✓ |
| Formula 6 case determination Fall 1–4 | ✅ | `AW168` formula identical to the source (ROUND(·,4) guards against floating point; enthalpy/temperature dual branch) ✓; `BB..BE` call `Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul` (`Fallunterscheidung.bas`, confirmed **live code**; #NAME? only in AQ/AS) ✓; BN/BP/BQ formulas ✓ | AW168=4 (summer cooling), BN168=20, BP168=10.0367 (chapter 10.037), BQ168=45.6012 (chapter 45.60) ✓ |
| Formula 7 supply-air setpoints & room/extract air | ✅ | BJ/BK/BL/BM and BR/BS/BT/BU/BW/BV formulas identical to the source (piecewise interpolation on the temperature curve, humidity drift, BS clamping, BW=BT+I20) ✓ | BJ168=20, BL168=10.0367, BM168=45.6012, BR168=24, BS168=0.5049, BT168=10.0367, BV168 formula ✓ |
| Formula 8 enthalpy difference & energy | ✅ (3 wording-simplification suggestions) | BZ/CA/CB/CD enthalpy-difference formulas identical to the source; BX/BY are actually `SUM(BZ168:CA168)`/`SUM(CB168:CD168)` (the chapter writes BZ+CA, CB+CC+CD — semantically equivalent, **citation update suggested**); CC168/CH168 actually contain `IF($E$36=$D$36,…)` enthalpy/temperature dispatch and the summer dV (P70) branch (the chapter cites only the temperature-controlled K70 branch — **completion suggested**); CJ/CE/CK/CF/CG/CM/CT/CH/CI/CL/CW formulas ✓ | row 168: CJ168=0.21795 (3819.23×59.6575×1.15×2.9945/3.6e6, BZ=S−AM=47.65−44.66=2.9945) ✓, CT168=0.40942 (59.6575×6.8629/1000) ✓ |
| Formula 9 annual aggregation | ✅ | Row 182: eight `SUM(…122:…181)`; row 183: four `MAX(…)×$E$18*$N$23/3600` (confirmed by `CC183`'s scope starting at row 133); rows 254–260: `IFERROR(…*1000,0)`; row-7 mapping (H7=C259/1000, P7=D254, Q7=C254/1000, …); `Lüftung!Q32:Z32` write-back wiring confirmed cell by cell (**incl. the shifts U32←V7, V32←W7, W32←X7, X32←Y7, Y32←T7, Z32←U7**) ✓ | C254=1750.16/D254=25.78, C255=3786.30/D255=16.15, C256..C258≈0, C259=26765.14/D259=6.8629, C260=32301.60/D260=48.80 ✓; `Resultate!C37/C38` (Erwärmung Befeuchtung←`Lüftung!V23`, Kühlung Entfeuchtung←`Lüftung!X23`) = 0 chain ✓ |
| Formula 10 fan model | ✅ | E19/E20/I14 (P∝V^2.5) formulas identical to the source; J64:M67 runtime weighting; M70 ✓ | `M67=6.862857=G6` (consistency) ✓; CT168/CT182 re-checked ✓ |
| 4.14 known quirks (14 items) | ✅ | All verifiable items confirmed: ① AQ/AS erroneous chain; ② summation starts at row 122, `CC183` starts at 133; ③ SOLL dormant (K82/M82/P82/R82=0, B189=0); ⑤ AD181=59, AE181=157.6 (supersaturation draft columns); ⑥ CN/CV columns 222/−222 chart guards; ⑦ energy prices empty → F254=0; ⑧ Lüftung U..Z shifts; ⑨ timetables only used for tier weighting; ⑩ E41/E44 empty; ⑪ A184/D184 contain LUET/LUEAB documentation formulas; ⑬ BU121 contains a `#REF!` dead branch (not triggered by current inputs); ⑭ J11/F40=`#N/A` | – |

### Ch. 5 Heat generation & Resultate aggregation

| Item | Result | Source verification | Numerical-example verification |
|---|---|---|---|
| 5.2 Nutzungsgrad catalog | ✅ | Columns B/C/E/F/G layout identical; all 39 standard values in column E match the dumps (KE01–06=3/4/4/7.5/15/15; WE01–09=0.8/0.8/0.6/0.7/0.7/0.98/0.93/1/0.5; WE10 empty; WE11–16=3/2.2/4.3/3.1/4.3/3.1; W01–13=0.75/0.75/0.55/0.6/0.65/1/1/0.65/empty/0.5/2.2/2.4/1.9) ✓ | name spot checks (KE01, WE01, WE11, WE15) identical ✓ |
| Formula 1 demand allocation & loss markup | ✅ | `L7=(Gebäude!Q$35+Lüftung!Q$23)*F7%*(100+IF($J7<>"",$J7,$H7))%` identical to the source; three demand sources (Kälte Q/R, Wärme T/U, WW V/W) ✓ | L7=134.357 (chapter 134.36), M7=55.7223, L8=89.571, M8=13.9306, L10=223.928 (203.571×1.1) ✓; F7/G7/H7=60/80/10 ✓ |
| Formula 2 WW power demand | ✅ | `L25=Gebäude!V$35*4.186/3.6*50/L$29/1000*F25%*(100+…)%` identical to the source; `M25=(Gebäude!W$35*G25%)×(100+…)%` ✓ | `L25=3.401125` (835.7×(4.186/3.6)×50/6/1000×0.3×1.4; chapter 3.4011) ✓; L29=6 h/d, F25=30, H25=40 ✓ |
| Formula 3 Volllaststunden & Endenergie | ✅ | `N7=IF(L7=0,0,M7*1000/L7)`, `P7/Q7=IF(D7=0,0,$L7/IF($E7<>"",$E7,$D7))` identical to the source; Total row `N10=M10*1000/L10` (no division-by-zero guard) confirmed ✓ | N7=414.733 (chapter 414.7), P7=11.1964 (134.36/12), Q7=4.64353 (55.72/12) ✓; E7=12 (project COP), D7=15 (KE06 standard) ✓ |
| Formula 4 Elektrizitätserzeugung | ✅ | EE01/EE02 input areas fully identical (30 kW/0.21/8°/−45°/0.83; 5/16 kW, 0.27/0.51, 3500 h) ✓; no downstream consumption (reserved feature) ✓ | – |
| 5.8 Resultate matrix | ✅ | 8-row × 9-end-use layout; all source formulas in columns D..U identical (D7/E7←Gebäude L58/I58, F/G←F35/G35, L/M←Lüftung H23/I23, N7←Erzeugung!P10, O/P/Q/R/S←SUMIF, T/U explicit SUM) ✓ | all 16 cached values in the El row identical (E7=54.6442, G7=129.6861, K7=59.9020, M7=32.4834, N7=33.5893, O7=8.1262, P7=17.7691, Q7=11.8202, R7=1.2597, S7=2.6239, T7=207.594, U7=320.316) ✓ |
| Formula 5 SUMIF aggregation by Energieträger | ✅ | The five SUMIF formulas O7/P7/Q7/R7/S7 identical to the source ✓ | Q10=23.218 (Pell Heizung), S10=4.360, U15=347.894 (chapter 347.89) ✓ |
| Formula 6 weighted energy & per-unit-area indicators | ✅ | `E21=SUMPRODUCT(E$7:E$17*W7:W17)`, `D21=E21*1000/Gebäude!$D$39` identical to the source; all 24 weighting values in columns W/X/Y identical (El 2/2.69/0.139 … FW 0.6/0.55/0.1) ✓ | E21=109.2884, G21=259.3722, U21=620.80, D21=16.7826 (chapter 16.78) ✓ |
| 5.10 two copy-paste errors | ✅ (confirmed) | `I21=SUMPRODUCT(I$7:I$17*Y7:Y17)` (wrongly uses THGE weighting column Y), `G22=F22=E22` chain `=SUMPRODUCT(E$7:E$17*$X7:$X17)` (duplicates column E) ✓ | I21=2.92317=I25 (proves column Y is used); G22=146.993 (should be 129.686×2.69≈348.9), F22=22.5726 ✓ |
| 5.8 per-unit-area energy balance | ✅ | C31/C32/C33/C34/C35/C37/C38 formulas identical ✓ | C31=9.3992 (61.207×1000/6512, chapter 9.399) ✓; C37/C38=0 ✓ |

### Ch. 6 Climate data

| Item | Result | Source verification | Numerical-example verification |
|---|---|---|---|
| 6.2 Klimadaten layout | ✅ | `N1=INDEX(B4:B43,Gebäude!D2,0)` → Zürich-MeteoSchweiz (Gebäude!D2=40) ✓; N2/O2 key-name formulas (`N1&N3`) ✓; S4 header `[%]` inconsistent with the actual 0–1 fractions (README 0.7-2) confirmed ✓ | – |
| Formula 1 station air pressure (standard-atmosphere altitude formula) | ✅ | `E4=1013.25*(1-(0.0065*D4)/288.15)^5.255` identical to the source; `F44=SUM(F4:F43)`, `H44=SUM(H4:H43)` selected-station summation trick ✓; `Berechnung LU!N19=Klimadaten!F44` ✓ | E43=948.226 (D43=556, Zürich) ✓; F44=948.226 ✓; H44=3440 (HDD); Grand-St-Bernard (D16=2472): E16=749.494 ≈750 mbar ✓; first station Adelboden (D4=1320): E4=864.428 ✓ |
| Formula 2 bin hours & cumulative | ✅ | `O5=INDEX($S$1:$CT$65,L5,MATCH($O$2,$S$2:$CT$2,0))`, `P6=O6+P5` identical to the source ✓ | P65=8760 ✓; O5=0 (−25 °C), O20=6 (−10 °C), O52=134 (22 °C), O65=0 (+35 °C) ✓ |
| Formula 3 bin humidity & humidity ratio | ✅ | `N5`/`Q5=AbsFeuchte(M5,N5,$F$44)` identical to the source ✓ | N20=0.881667 (chapter 0.8817 rounded), Q20=1.50152 (chapter 1.5015), N50=0.5925, Q50=9.21648 (chapter 9.2165) ✓ |
| 6.6 Qhc_Klimastat | ✅ | `G3=MATCH(D3,P3:SA3,0)=469`; `D7=INDEX($P$7:$SA$51,$C7,$G$3-1+D$2)` slice formula identical to the source; `P3=[3]Winter_Auslegung!A5` (external link [3]) ✓; `A7=[3]Eingabedaten!A9=1.01`, `B7=[3]Eingabedaten!C9=Wohnen MFH` ✓; `KZ_Raum_2024!G11/AG11/AH11 = Qhc!E11/D11/F11` reference formulas ✓ | D11=43.6565 (=KZ!AG11), E11=14.4301 (=KZ!G11), F11=19.8234 (=KZ!AH11) ✓ (chapter 43.656/14.430/19.823) |

---

## 4. Summary of correction proposals

**Substantive errors (3 — the main text must be corrected):**
1. Ch. 1 §1.7: `p_s(0°C)=6.02 mbar` → should be **6.108 mbar**; deviation 1.5 % → ≈0.03 %.
2. Ch. 1 §1.7: `p_s(20°C)=24.9 mbar` → should be **23.374 mbar**; deviation 6 % → ≈0.07 %. Also suggested: move the "less accurate than Glück" check points to −20/−30 °C (there the power-law deviation is ~3 %, which supports the conclusion).
3. Ch. 1 §1.5/§1.10: change the `TemperaturH` example inputs to `(21.3979, 0)` (or cite another row), delete/correct `(12.2406, 8.19…)` and the check formula (it yields −8.1 °C).

**Wording precision (citation updates suggested; conclusions unaffected):**
4. Ch. 3 §3.4: complete the `I8` formula with the `'Berechnung LU'!` prefix per the dump.
5. Ch. 4 §4.11: `BX=SUM(BZ:CA)`, `BY=SUM(CB:CD)` (not the `+` form); add notes on the complete `CC`/`CH` formulas incl. the enthalpy/temperature dispatch and the summer P70 branch.
6. Ch. 3 §3.2: note that Std columns O/P are static snapshots (the "select by column N" mechanism lives in the Raumdaten source table), and that `Volll_Lüft` column A stores internal codes (3.01) while the SIA code 1.03 comes from `Eingabedaten`.
7. Ch. 1 §1.3 / Ch. 6 §6.5: note that `N20=0.8817` is the display rounding of the cached 0.881666….
8. Ch. 5 §5.2: optionally add W09 (empty)/W10 (0.5) to make the catalog table more complete.

**Workbook-internal issues also confirmed during the review (already faithfully recorded in the textbook; no change needed):**
- `Lüftung!U..Z` header shifts, `Resultate!I21/G22` copy-paste errors, `TaupunktA` dead references (#NAME?/#VALUE!), `Gebäude!N9/O9` column-selector offset deviations, the dormant SOLL block, `CC183` scope, the BU-column `#REF!` dead branch, J11/F40 `#N/A`, etc. — all consistent with the dump caches; the textbook descriptions are accurate.

---

## 5. Reproduction method

- Verification script: `verify/run-checks.js` (Node ≥ 18, no third-party dependencies; reads the main repository's `.analysis/dumps` and `.analysis/vba`)
- Assertion details: `verify/results.json` (672 entries, each with PASS/FAIL/WARN and the dump's measured value)
- Run: `node verify/run-checks.js` → 668 PASS / 3 FAIL / 1 WARN
- Tolerance notes: numeric assertions use a default relative tolerance of 0.2 % (matching the chapters' rounding); formula assertions are compared exactly after whitespace normalization; error cells (#NAME?/#VALUE!/#N/A) are identified via the dump's JSON `error` objects.
