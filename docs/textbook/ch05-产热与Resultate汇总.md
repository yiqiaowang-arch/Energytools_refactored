# Chapter 5 — Heat Generation (Erzeugung) and Resultate Summary

> Core area: `Nutzungsgrad!A1:G41` (generator catalogue), `Erzeugung!A1:Q37` (three generation groups + electrical generation), `Resultate!A1:U71` (Energieträger matrix and weighted indicators)
> Upstream: `Gebäude!Q35:W35` (room demand Rechenwert (calculated value)), `Lüftung!Q23:T23` (AHU air-treatment demand Total)

## 5.1 Chapter Positioning

This chapter covers the conversion from "room + air-treatment demand" to "final energy (Endenergie) by Energieträger": ① demand allocation (Deckungsgrad); ② loss markup (Speicher-/Verteilverluste); ③ generation efficiency (Nutzungsgrad, standard or project value); ④ aggregation by Energieträger (Resultate sheet); ⑤ weighted indicators (NEGF/PEne/THGE).

## 5.2 Nutzungsgrad Catalogue (Generator Catalogue)

`Nutzungsgrad!B3:G8` (Kälte KE01–KE06), `B11:G26` (Wärme WE01–WE16), `B29:G41` (WW W01–W13):

| Column | Content |
|---|---|
| B | Code (KE01…KE06 / WE01…WE16 / W01…W13) |
| C | Name (e.g. "Kompaktkältemaschine 7°C", "Wärmepumpe Grundwasser 35°C") |
| E | **Nutzungsgrad** (efficiency/COP standard value) |
| F | Energieträger (Elektrizität, Heizöl EL, Erdgas, Holz, Holzschnitzel, Pellets, Fernwärme, Sonne) |
| G | Hilfsenergie (% — not used in calculations in the current version; informational only) |

**Representative standard values**: Kälte: KE01=3, KE02=4, KE03=4, KE04=7.5, KE05/KE06=15 (direct cold source, high EER); Wärme: WE01/WE02=0.8 (oil/gas condensing), WE03=0.6 (Stückholz), WE04/WE05=0.7 (Hackschnitzel/Pellets), WE06=0.98 (Fernwärme), WE07=0.93, WE08=1 (Elektro direkt), WE09=0.5 (WKK thermisch), WE11–WE16=3.0/2.2/4.3/3.1/4.3/3.1 (heat pumps 35/50 °C × air/ground/water source); WW: W01/W02=0.75, W03=0.55, W04=0.6, W05=0.65, W06/W07=1, W08=0.65, W11=2.2, W12=2.4, W13=1.9.

**Cell sources**: `Nutzungsgrad!E3:E8、E11:E26、E29:E41`; F column same range; labels via `Begriffe!F244/F251/F242`.

## 5.3 Erzeugung Layout

Three isomorphic generation blocks (each block: 1 title row + 1 header row + 3 generator rows + a Total row):

| Group | Rows | Demand source (power L / energy M) |
|---|---|---|
| Kälteerzeugung | 7–10 | `Gebäude!Q$35` (Raumkühlung) + `Lüftung!Q$23` (Luftkühlung power); energy uses `Gebäude!R$35` + `Lüftung!R$23` |
| Wärmeerzeugung | 16–19 | `Gebäude!T$35` (Raumheizung) + `Lüftung!S$23` (Lufterwärmung power); energy uses `Gebäude!U$35` + `Lüftung!T$23` |
| Warmwassererzeugung | 25–28 | Power: `Gebäude!V$35×4.186/3.6×50/L$29/1000`; energy: `Gebäude!W$35` |

Column structure of each generator row (using Kälte row 7 as an example):

| Column | Content | Formula |
|---|---|---|
| A | Code (automatic) | `=IF(B7<>"",INDEX(Nutzungsgrad!$B$3:$C$8,MATCH(Erzeugung!B7,Nutzungsgrad!$C$3:$C$8,0),1),"")` |
| B/C | Generator name (dropdown; C is a mirror) | Input |
| D | Nutzungsgrad standard value (automatic) | `=IF(B7<>"",VLOOKUP($B7,Nutzungsgrad!$C$3:$G$8,3,FALSE),0)` |
| E | Nutzungsgrad project value (overrides D) | Input |
| F/G | Deckungsgrad power/energy | Input (%, group total = 100 %) |
| H/I | Speicher-/Verteilverluste standard/project | Input (%) |
| J/K | Loss project value (overrides H) | Input |
| L/M | **Demand (incl. losses)** power/energy | `=(Gebäude!Q$35+Lüftung!Q$23)*F7%*(100+IF($J7<>"",$J7,$H7))%` |
| N/O | Volllaststunden | `=IF(L7=0,0,M7*1000/L7)` |
| P/Q | **Endenergie** power/energy | `=IF(D7=0,0,$L7/IF($E7<>"",$E7,$D7))` / isomorphic M |
| R | Energieträger (automatic) | `=IF(D7=0,"",VLOOKUP($B7,Nutzungsgrad!$C$3:$G$8,4,FALSE))` |

## 5.4 Formula 1 — Demand Allocation and Loss Markup

**Mathematical form** (for generator i, Kälte group example):

$$
\dot Q_{L,i} = \dot Q_{Bedarf}\cdot\frac{d_{P,i}}{100}\cdot\Big(1+\frac{v_i}{100}\Big) \quad[\mathrm{kW}],\qquad
Q_{M,i} = Q_{Bedarf}\cdot\frac{d_{E,i}}{100}\cdot\Big(1+\frac{v_i}{100}\Big) \quad[\mathrm{MWh}]
$$

where $d_{P,i}$, $d_{E,i}$ are the power/energy Deckungsgrad (%), and $v_i = \text{IF}(J_i\neq"", J_i, H_i)$ is the loss rate (%).

**Workbook implementation** (`Erzeugung!L7`):

```
=(Gebäude!Q$35+Lüftung!Q$23)*F7%*(100+IF($J7<>"",$J7,$H7))%
```

**Units**: kW / MWh (energy column M7 is isomorphic; source is `Gebäude!R$35+Lüftung!R$23`).

**Derivation**: The total demand is split among the generators according to their assigned shares, and the network/storage-tank losses are added back at the generator outlet (demand + losses = generator output). Losses are applied as a multiplicative percentage (not additively).

**Verification** (example building, Kälte group): `L7 = (167.138+36.433)×0.6×1.1 = 134.36 kW` ✓ (F7=60 %, H7=10 %); `M7 = (61.207+2.113)×0.8×1.1 = 55.72 MWh` ✓; `L8 = 223.928×0.4×1.1 = 89.57`, `M8×1.1 = 13.93` ✓ (group Total L10=223.93 = total demand 203.57×1.1 ✓).

**Assumptions**: Losses are linearly proportional to load (independent of load factor); Deckungsgrad power and energy can be set separately; the project loss value J takes precedence over the standard H.

**Applicability**: Kälte (L7:M9) and Wärme (L16:M18) are isomorphic; the WW group has a different power source (see Formula 2). Empty rows (no generator) output 0.

**Cell sources**: `Erzeugung!L7:M9`, `L16:M18`; demand sources `Gebäude!Q35/R35、T35/U35`, `Lüftung!Q23/R23、S23/T23`.

## 5.5 Formula 2 — Warmwasser Power Demand (Water Volume → Power Conversion)

**Mathematical form**:

$$
\dot Q_{WW} = V_{WW}\,[\mathrm{l/d}]\cdot\frac{4.186}{3.6}\cdot 50\,[\mathrm{K}]\cdot\frac{1}{t_{Aufh}}\cdot\frac{1}{1000} \quad[\mathrm{kW}]
$$

where $V_{WW}$ = `Gebäude!V35` (daily water demand l/d, Chapter 2, Formula 4), $t_{Aufh}$ = `Erzeugung!L29` = 6 (Aufheizzeit h/d), 4.186 kJ/(kg·K) is the specific heat of water, 3.6 is the kJ→Wh conversion, and 50 K is the cold-water→hot-water temperature rise.

**Workbook implementation** (`Erzeugung!L25`):

```
=Gebäude!V$35*4.186/3.6*50/L$29/1000*F25%*(100+IF($J25<>"",$J25,$H25))%
```

**Unit derivation**: $V\times c_w\times\Delta T$ = kJ/d; ÷3.6 → Wh/d; ×50 K already included; ÷$t_{Aufh}$ (h/d) → W; ÷1000 → kW. Combined: $835.7\times(4.186/3.6)\times50/6/1000 = 8.098$ kW (total); ×0.3×1.4 = 3.40 kW (W13 share) ✓ cached 3.4011.

**Assumptions**: Temperature rise is constant at 50 K; the daily water demand is heated uniformly within the Aufheizzeit (tank heat storage); water density 1 kg/l.

**Cell sources**: `Erzeugung!L25:L27` (energy column `M25: =（Gebäude!W$35×G25%）×(100+IF($J25<>"",$J25,$H25))%`, expressed directly in MWh); `Erzeugung!L29/M29` (6 h/d).

## 5.6 Formula 3 — Volllaststunden and Endenergie

**Mathematical form**:

$$
t_{VL,i} = \frac{Q_{M,i}\,[\mathrm{MWh}]\cdot1000}{\dot Q_{L,i}\,[\mathrm{kW}]} \quad[\mathrm{h}],\qquad
P_{End,i} = \frac{\dot Q_{L,i}}{\eta_i},\quad Q_{End,i} = \frac{Q_{M,i}}{\eta_i}
$$

Efficiency $\eta_i = \text{IF}(E_i\neq"", E_i, D_i)$ (project value takes precedence over the catalogue standard value).

**Workbook implementation**: `Erzeugung!N7: =IF(L7=0,0,M7*1000/L7)`; `P7: =IF(D7=0,0,$L7/IF($E7<>"",$E7,$D7))`; `Q7: =IF(D7=0,0,$M7/IF($E7<>"",$E7,$D7))`.

**Units**: h; kW; MWh. **Verification**: `N7 = 55.72×1000/134.36 = 414.7 h` ✓; `P7 = 134.36/12 = 11.196` (E7=12 project COP) ✓; `Q7 = 55.72/12 = 4.644` ✓.

**Derivation**: Endenergie = generator outlet energy ÷ efficiency (for heat pumps/chillers, η is the COP and Endenergie is electricity); full-load hours = energy/power (same convention as Chapter 3).

**Assumptions**: Efficiency is a constant annual value (no part-load curve); output is 0 when η=0 or D=0 (empty row).

**Applicability**: all rows of the three generation groups (7–9, 16–18, 25–27); the N column of the Total rows (10/19/28) is `=M10*1000/L10` (no IF guard — division by zero would occur if L=0; not triggered in the example building since L>0).

**Cell sources**: `Erzeugung!N7:Q9`, `N16:Q18`, `N25:Q27`; Total rows such as `N10:Q10`.

## 5.7 Formula 4 — Elektrizitätserzeugung (Electrical Generation, PV/WKK)

`Erzeugung!A31:Q37`: PV-Anlage (EE01) and WKK-Biogas (EE02) inputs: D/E columns installed power (elektr./therm. kW), G/H efficiency (elektr./therm.), J/K system efficiency (Standard/Projekt), L/M full-load hours, O–Q PV orientation (Orient./Azimut/Faktor). Example: EE01 PV 30 kW, η=0.21, O=8°, Azimut=−45°, Faktor=0.83; EE02 WKK 5 kW/16 kW, η=0.27/0.51, t_VL=3500 h. This block is an **input area** (no downstream formula consumes its values — in the current version Resultate does not offset self-generated electricity; it is a reserved feature).

**Cell sources**: `Erzeugung!A31:Q37`.

## 5.8 Resultate Layout

**Matrix** (`Resultate!A7:U15`): rows 7–14 = 8 Energieträger (El, HEL, Gas, Pell, HSch, StH, Bio, FW); columns D–U = 9 uses × (Leistung/Energie):

| Column | Use | Source |
|---|---|---|
| D/E | Allg. Gebäudetechnik | `Gebäude!L58/I58` |
| F/G | Geräte | `Gebäude!F35/G35` |
| H/I | Prozessanlagen | `Gebäude!H35/I35` |
| J/K | Beleuchtung | `Gebäude!J35/K35` |
| L/M | Lüftung | `Lüftung!H23/I23` (fans) |
| N/O | Kühlung | `Erzeugung!P10` / `=SUMIF(Erzeugung!$R$7:$R$9,$B7,Erzeugung!$Q$7:$Q$9)` |
| P/Q | Heizung | `=SUMIF(Erzeugung!$R$16:$R$18,$B7,Erzeugung!$P$16:$P$18)` (and Q) |
| R/S | Warmwasser | `=SUMIF(Erzeugung!$R$25:$R$27,$B7,Erzeugung!$P$25:$P$27)` (and Q) |
| T/U | Total | `=SUM(D7,F7,H7,J7,L7,N7,P7,R7)` / `=E7+G7+I7+K7+M7+O7+Q7+S7` |

**Weighted indicators** (`Resultate!A18:U25`): weight columns `W7:Y17` (one row per Energieträger):

| Row | Indicator | Weight column | Formula |
|---|---|---|---|
| 21 | EP_CH (Nationale Energie-Kennzahl) | W (NEGF) | Energy: `=SUMPRODUCT(E$7:E$17*W7:W17)`; per floor area: `=E21*1000/Gebäude!$D$39` |
| 22 | EP_Pnr (Primärenergie nicht erneuerbar) | X (PEne) | Isomorphic (note: the power columns such as D22/F22 are actually mirrors of `=E22*1000/$D$39`; power weighting is not computed independently) |
| 25 | EP_GHG (Treibhausgasemissionen) | Y (THGE) | `=SUMPRODUCT(E$7:E$17*$Y7:$Y17)`; THGE weight unit kg/kWh |

**Example weights**: El: NEGF=2, PEne=2.69, THGE=0.139; HEL: 1/1.22/0.298; Gas: 1/1.06/0.228; Pell: 0.7/0.2/0.034; HSch: 0.7/0.06/0.022; StH: 0.7/0.05/0.022; Bio: 1/0.31/0.132; FW: 0.6/0.55/0.1.

**Per-floor-area energy balance** (`Resultate!A28:C59`): C31: `=Gebäude!R35*1000/Gebäude!D39` (Raumkühlung kWh/m²), C32: `=Lüftung!R23*1000/Gebäude!D39` (Luftkühlung), C33/C34 (Raumheizung/Lufterwärmung), C35 (WW), C37/C38 (humidification/dehumidification: `=Lüftung!V23/X23*1000/…`), C40–C47 (electrical uses, sourced from matrix rows E7/G7/I7/K7/M7/O7/Q7/S7), C52–C59 (PEne indicator rows), C64–C71 (THGE indicator rows). **Verification**: `C31 = 61.207×1000/6512 = 9.399 kWh/m²` ✓.

**Cell sources**: `Resultate!A7:U15`, `W7:Y17` (weights), `D21:U25` (weighted), `B30:C59` (energy balance), `B50:C71` (WW/PEne/THGE per-floor-area block).

## 5.9 Formula 5 — SUMIF Aggregation by Energieträger

**Mathematical form** (for Energieträger $e$, use $u$):

$$
Q_{End}(e,u) = \sum_{i\in \text{Erzeugung 组}(u)} Q_{End,i}\cdot\mathbb{1}[R_i = e]
$$

**Workbook implementation** (`Resultate!O7`, Kühlung energy):

```
=SUMIF(Erzeugung!$R$7:$R$9,$B7,Erzeugung!$Q$7:$Q$9)
```

**Units**: MWh (the power column is isomorphic, taking the P column → kW).

**Derivation**: Each generator's Energieträger in Erzeugung is filled automatically from the catalogue (column R); Resultate sums the generators within the same use group by Energieträger name — i.e. the "total per fuel".

**Verification** (example building): El row (B7="Elektrizität"): `O7 = 8.126` (KE02/KE06 electricity), `Q7 = 11.820` (WE15 electricity), `S7 = 2.624` (W13 electricity) ✓; Pell row (B10): `Q10 = 23.218` (WE05), `S10 = 4.360` (W05) ✓; `U7 = 320.316 MWh` (El total energy) ✓.

**Assumptions**: The Energieträger names are exactly identical between the `Nutzungsgrad` catalogue and `Resultate!B7:B14` (both are produced by the `Begriffe` dictionary).

**Applicability**: `Resultate!N7:S14` (6 use columns × 8 rows); the T/U Total columns use an explicit SUM (including the directly referenced Gebäude/Lüftung columns).

**Cell sources**: `Resultate!N7:S14`; match keys `Erzeugung!R7:R9、R16:R18、R25:R27`; catalogue `Nutzungsgrad!F3:F8、F11:F26、F29:F41`.

## 5.10 Formula 6 — Weighted Energy and Per-Floor-Area Indicators

**Mathematical form**:

$$
EP_{CH,u} = \sum_e k_{NEGF,e}\cdot E_{End}(e,u) \quad[\mathrm{MWh}],\qquad
ep_{CH,u} = EP_{CH,u}\cdot\frac{1000}{A_{EBF}} \quad[\mathrm{kWh/m^2}]
$$

**Workbook implementation** (`Resultate!E21`, `D21`):

```
=SUMPRODUCT(E$7:E$17*W7:W17)
=D21*1000/Gebäude!$D$39     ' 注意：D21 指向 E21 的 1/1000 镜像（见下）
```

**Units**: MWh; kWh/m².

**Derivation**: The weight factors (NEGF unweighted, PEne primary-energy factor, THGE greenhouse-gas coefficient kg CO₂-eq/kWh) are multiplied element-wise with the energy of each Energieträger and summed; dividing by the EBF yields the per-floor-area indicator. **Note**: the workbook implements the power columns (D21, F21…) as `=E21*1000/Gebäude!$D$39`, where `E21` is the MWh-weighted value, `×1000` divided by the EBF — i.e. the power column is actually a duplicate display of the "energy indicator" (weighted power is not defined separately); `D21` caches 16.78 = E21×1000/6512 ✓. Similarly for the PEne row (D22/F22… all mirror `E22*1000/$D$39`) and the THGE row (`D25: =E25*1000/$D$39`).

**Verification**: `E21 = 54.644×2 = 109.288` (El row W7=2, the other rows are 0) ✓; `G21 = 129.686×2 = 259.372` ✓; `U21 = 620.80 MWh`. **Note two suspected copy-paste errors (confirmed via the cached values)**:
- `Resultate!I21` (NEGF row · Prozessanlagen) has the formula `=SUMPRODUCT(I$7:I$17*Y7:Y17)` — it uses the **THGE weight column Y** instead of the NEGF column W (its value 2.923 equals the THGE row `I25`); by design it should be `SUMPRODUCT(I7:I17*W7:W17) = 21.03×2 = 42.06 MWh`.
- `Resultate!G22` (PEne row · Geräte) has the formula `=SUMPRODUCT(E$7:E$17*$X7:$X17)` — it **repeats column E (Allg. Gebäudetechnik)** instead of column G; `F22` (its power mirror) is correspondingly wrong as well (146.99 MWh / 22.57 kWh/m², should be 129.686×2.69 ≈ 348.9 MWh).

**Assumptions**: The weight factors are the current NEGF/PEne/THGE values of Swiss national energy legislation (at the time of release); the EBF denominator uses `Gebäude!D39` (including the construction-area factor).

**Applicability**: `Resultate!D21:U25`; the weight columns W/X/Y can be edited by the user.

**Cell sources**: `Resultate!E21、G21、I21、K21、M21、O21、Q21、S21、U21` (NEGF); `E22…U22` (PEne); `E25…U25` (THGE); weights `W7:Y17`; denominator `Gebäude!D39`.

## 5.11 Verification Matrix (Example Building, El Row, Units MWh/kW)

| Use | Energy (cached) | Power (cached) | Formula source |
|---|---|---|---|
| Allg. Gebäudetechnik | 54.6442 | 55.8229 | `Resultate!E7/D7 ← Gebäude!I58/L58` |
| Geräte | 129.6861 | 45.57 | `G7/F7 ← Gebäude!G35/F35` |
| Prozessanlagen | 21.03 | 3 | `I7/H7 ← Gebäude!I35/H35` |
| Beleuchtung | 59.9020 | 41.3754 | `K7/J7 ← Gebäude!K35/J35` |
| Lüftung (fans) | 32.4834 | 9.2079 | `M7/L7 ← Lüftung!I23/H23` |
| Kühlung | 8.1262 | 33.5893 | `O7/N7 ← Erzeugung!Q/P10` |
| Heizung | 11.8202 | 17.7691 | `Q7/P7 ← SUMIF WE 组` |
| Warmwasser | 2.6239 | 1.2597 | `S7/R7 ← SUMIF W 组` |
| **Total** | **320.3159** | **207.5942** | `U7/T7` |

**Energy-conservation check**: demand side (Gebäude+Luft+Warmwasser, before losses) 129.686+21.03+59.902+32.483+(61.207+2.113)+(68.834+5.042)+10.121 ≈ 390.4 MWh; the Endenergie side, after conversion by η, totals 347.89 MWh by Energieträger (`U15`) — the difference stems from the net effect of generation efficiency (COP>1 makes electricity consumption lower than demand) and the loss markup (>1). Both accounting conventions are traceable within the sheet.

## 5.12 Porting Notes

1. The three generation blocks are isomorphic → port to a single "generator" model (kind: cooling/heating/ww × {name, eta_standard, eta_project, coverage_P, coverage_E, losses_standard, losses_project, energy_carrier}), with group-level validation: Deckungsgrad power/energy each 100 % (`Erzeugung!F10/G10: =SUM(F7:F9)` etc.).
2. The constants of the WW power conversion (4.186/3.6×50/L29/1000) should be parameterized (ΔT=50 K, Aufheizzeit=6 h/d).
3. The SUMPRODUCT weighting in Resultate is a "column (use) × row (Energieträger)" matrix multiplication — port it as a dot product; the power-column mirrors (D21=F21=…) are display redundancy and can be dropped.
4. The weight factors (NEGF/PEne/THGE) are versioned external data (Swiss energy law / EnDK) and should be maintained separately from the model.
5. Keep the IF guards (D=0 → 0) and the Total-row summation convention; note the potential division-by-zero risk of the Total-row N column (`M10*1000/L10`) without a guard.
6. **Fix the two copy-paste errors in the `Resultate` weighted rows** (§5.10): `I21` (NEGF·Prozessanlagen) wrongly uses the Y weight column; `G22/F22` (PEne·Geräte) repeats column E. Rewrite by column definition when porting.
