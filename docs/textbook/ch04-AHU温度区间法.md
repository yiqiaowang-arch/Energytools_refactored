# Chapter 4 — AHU Temperature-Bin Method (Berechnung LU)

> Core region: `Berechnung LU!A1:DA328` (328 rows × 108 columns, 13 466 formula cells — the physical engine of the whole workbook)
> Upstream: `Lüftung!A32:Z32` (current system template row), `Klimadaten!F44/N/O/Q` (air pressure, bin humidity, bin hours), `Std!Q:V` (full-load hours)
> Downstream: `Lüftung!Q32:Z32` (result write-back), `Lüftung!I32/K32`, `Erzeugung` (cooling/heating demand)
> Analysis basis: full dump of `sheet_61_Berechnung LU.tsv` (in this work tree, `docs/analysis_Berechnung_LU.md` is the column-by-column analysis draft)

## 4.1 Section Scope and Engine Architecture

`Berechnung LU` is the only "physical" calculation engine in Gebäude-Tool: it performs the year-round psychrometric calculation for **one** air-handling unit (AHU) using the **temperature-bin method**. Key points:

1. **One instance, one system**: `Berechnung LU!A6 = Lüftung!A32` carries only the "current system" (example = LA01). The loop over the 16 systems (LA01…LA16) is implemented by the macro `Lüftung_Resultate` (`Lüftung_Resultate.bas`): copy `Lüftung!A7:Z7` to `A32:Z32` → recalculate this sheet → copy the corresponding values of result row 7 and template row 32 back into the system row (`A7`, `G32`, `I32`, `O32:X32`) → repeat 16 times.
2. **Two-block structure**: the IST block (rows 121–181, 61 bins, inputs from column E) and the SOLL block (rows 189–249, inputs from column F) have identical structure; **in this file the SOLL block is dormant** (climate cells are 0, the air-pressure reference is `#REF!`, `K82/M82/P82/R82 = 0`), so all results come from the IST block. The SOLL block is the "target state" reference (column F inputs are unfilled in the example building).
3. **Bin climate data**: 61 outdoor temperature bins t_A = −25…+35 °C (one 1 K step per bin); each bin gives annual hours, relative humidity and moisture content (see Chapter 6).
4. **State chain**: AUL (outdoor) → frost-protection preheating → WRG (heat recovery) → MIL (mixing/fresh air) → cooling-coil chain (A/C/D1/D2) → heating/humidification (E/F/G) → ZUL soll/ist → room/exhaust air → enthalpy difference → hourly energy × bin hours → annual energy.

## 4.2 Layout Map (Rows)

| Row | Role | Key cells |
|---|---|---|
| 3–5 | System-row headers (C air volume, F fan, K supply-air control, P–Y five treatment-stage powers/energies) | Units row 5 |
| 6 | **System input row (current system)** | `A6=Lüftung!A32`…`O6` (see §4.3) |
| 7 | **Result row** | `H7=C259/1000`, `P7=D254`, `Q7=C254/1000`…`Y7` (see §4.12) |
| 8 | Control-mode index | `I8 = IF(I6=Begriffe!F205,1,IF(I6=Begriffe!F206,2,IF(I6=Begriffe!F207,3,FALSE)))` |
| 11–25 | Ventilation-technical inputs (IST = column E / SOLL = column F): area, ceiling height, filters, fans, staged air volumes | see §4.3 |
| 26–33 | Seasonal air volume, WRG/KRG, frost protection | `E28` (WRG η=0.8), `E33` (frost-protection threshold) |
| 34–38 | Fresh-air ratio (E34/E35=1), control reference (E36), fresh-air source | see §4.5 |
| 39–51 | Heating/cooling coils, dehumidification, humidification | `E39/E42/E47/E49` existence flags, `E45/E46` cooling-coil water temperature, `E48/E50` humidity band |
| 52–55 | Room humidity load, air-volume control mode | `E52=0` |
| 56–70 | **Operating schedule** (IST) + plausibility checks | `I58:I60` (50/15/15 h/week), `M58:M60` (shares), `K68/K69` (full-load hours), `K70/M70` |
| 71–85 | SOLL operating schedule (dormant) | `K82/M82 = 0` |
| 86–91 | **Temperature curves IST** (t_ZUL, t_Raum piecewise-linear f(t_A)) | `B88:D91` breakpoints, `I88:J90` slopes |
| 92–97 | Temperature curves SOLL | `B94:D97` |
| 100–108 | Motor efficiency-class lookup (IE5…Eff3 × power band) | `C108/E108/H108/J108` (η) |
| 109–115 | Filter pressure drop, shaft power/motor power, frost-protection power | `B110:B114`, `F113` |
| 117–120 | IST block headers (state-point naming) | `A117` AUL, `F117` AUL nWRG, `N117/T117` MIL, `Z117` cooling coil, `AH/AK` D1/D2, `AN` E, `AQ` F, `AT` G, `AW` Fall-, `BB..BH` Fall 1–4, `BJ` soll, `BN` ist, `BR` Raum |
| **121–181** | **IST temperature-bin calculation** (61 bins, t_A = −25…+35 °C) | see §4.4–4.11 column map |
| 182–183 | **IST summary**: energy sums (`CE182…CM182, CT182`) and power maxima (`BZ183…CD183`) | see §4.12 |
| 184 | Documentation row (legacy LUET/LUEAB formula text, a `#NAME?` risk source) | `A184/D184` |
| 185–250 | SOLL bin block (dormant) + SOLL sum (row 250) | all 0 |
| 251–253 | "Energiebedarf pro Aussentemp." header and chart lookup values | `H253:J253` |
| **254–260** | **Annual result rows** (kWh / kW) | `C254:C259`, `D254:D259`, row 260 Total |
| 262–263 | Humidification water / condensate amounts (L/a, CHF/a) | `C262/D262`, `C263/D263` |
| 264–266 | "Daten für HG/KG" chart headers | labels `Begriffe!F152:F158` |
| 267–327 | Per-bin chart data (kW curves, kWh curves, t_ZUL, rF_ZUL) | `B:D` power, `I:N` energy, `O/P` states |
| 328 | Chart totals | `I328:N328` |

## 4.3 Input Block (Rows 6, 11–55, 56–70, 86–115)

**Row 6 (from `Lüftung` template row 32)**:

| Cell | Value (example LA01) | Meaning |
|---|---|---|
| `A6` | LA01 | System name (=`Lüftung!A32`) |
| `B6` | Einzel-, Gruppenbüro | Usage (Std lookup key) |
| `C6/D6/E6` | 8578.6 / 0 / 0 m³/h | Air volume Standard/Prozess/Projekt (=`Lüftung!C32:E32`) |
| `F6` | 0.8 W/(m³/h) | SFP (=`Lüftung!G32`) |
| `G6` | 6.863 kW | Total fan power (=`Lüftung!H32`) |
| `I6` | einstufig | Control mode (=`Lüftung!J32`) |
| `J6` | =K68 → 3900 h | Full-load hours (air-volume basis) |
| `K6` | 80 % | WRG efficiency (=`Lüftung!L32`) |
| `L6/M6` | 20 / 21 °C | Supply-air set temperature summer (Kühlfall)/winter (Heizfall) |
| `N6/O6` | 0 / 0 % r.F. | Supply-air set humidity summer/winter |

**Key inputs, rows 11–55** (IST = column E): `E11` conditioned area 500 m², `E12` ceiling height 3 m, `E13` "Mischluft" (supply-air type; alternative: Quellluft), `E14/E15` filters ("0 keinen", look up the pressure drop in table M28:M44), `E16 = G6/2` (ZUL fan power), `E17` "IE5 - gefaked" (motor efficiency class), `E18:E20` three staged air volumes (100/67/33 %, per the `I6` control mode), `E21:E25` ABL analogous, `E26` summer-mode start temperature 0, `E27` summer air-volume increment 0, `E28 = K6%` (WRG thermal efficiency 0.8), `E29` 0 (moisture recovery), `E30/E31` "ja" (bypass/KRG), `E32` 0 (frost-protection type: 0 = off, or `I32` electric on/off / `I33` electric variable), `E33` 0 (frost-protection threshold temperature), `E34/E35` 1/1 (**fresh-air ratio min/max** — the example is 100 % fresh air, no return-air mixing), `E36` "Temperatur" (control reference; D36 empty → the enthalpy-control branch is not active), `E39` "ja" (heating coil), `E40` −13 °C (heating design temperature), `E42` "ja" (cooling coil), `E43` 35 °C (cooling design temperature), `E45/E46` 6/12 °C (cooling coil VL (Vorlauf)/RL (Rücklauf)), `E47` "ja" (dehumidification), `E48 = IF(OR(N6="",N6=0),1,N6%)` → 1 (maximum allowed rF in summer), `E49` "Adiabatisch Bef." (humidification type), `E50 = IF(O6="",0,O6%)` → 0 (minimum allowed rF in winter), `E51` 10 °C (chilled-water temperature), `E52` 0 (room moisture load), `E54` "Benutzerdefiniert" (air-volume control mode; VLOOKUP `I39:J47` gives the time factor).

**Rows 56–70, operating schedule and plausibility**: `I58 = 5*MIN(24, HOUR(C58-B58)+…)` → 50 h/week (Stufe 1, Monday–Friday 08–18); `I59/I60` → 15/15 h; `L58 = SUM(I58:K58)*VLOOKUP($E$54,$I$39:$J$47,2,FALSE)` (factor 1); `L61` = 80 h/week; `M58 = L58/L61` → 0.625 (stage-1 time share). `K68/K69` (Std lookup, see Chapter 3), `K70 = E7*K68/8760` → 3819.2 m³/h (year-weighted average air volume), `M70 = G6*K69/K68` → 6.863 kW (year-weighted average fan power).

**Rows 86–91, temperature curves** (IST): breakpoints (t_A, t_ZUL, t_Raum): (−15, 21, 22), (22, 20, 24), (24, 20, 25), (30, 20, 25); slopes `I88 = (C89-C88)/(B89-B88)` = −0.0270 K/K (t_ZUL segment 1), `J88 = (D89-D88)/(B89-B88)` = 0.0541 (t_Raum segment 1), `I89 = 0`, `J89 = 0.5`, `I90/J90 = 0`.

**Rows 100–108, motor efficiency classes**: power bands `N10:R10` (≤1.1, 1.1–2.2, 2.2–11, 11–110, >110 kW); IE5=1/1/1/1/1 ("gefaked"), IE4=0.872/0.895/0.933/0.963/0.967, IE3=0.85/0.87/0.9/0.94/0.96, IE2=0.82/0.84/0.88/0.93/0.95, IE1=0.73/0.78/0.84/0.91/0.94, Eff3=0.69/0.74/0.81/0.9/0.93. `B102 = IF(E$16<1.1,N11,IF(E$16<2.2,O11,IF(E$16<11,P11,IF(E$16<110,Q11,R11))))`; `C102 = IF(E$17=A102,B102,0)` (take the row of the efficiency class selected by E17); `C108 = MAX(C102:C107)` → η_ZUL,IST = 1 (IE5 row) ✓.

**Rows 109–115**: `B110 = LOOKUP(E14,M28:M44,N28:N44)+LOOKUP(E15,M28:M44,N28:N44)` → 0 Pa (filter pressure-drop table M27:O44: 0/95/105/125/150/160/180/198/215/233/250/268/285 Pa ↔ "0 keinen"/F5/F6/F7/F8/F9/G1/G2/G3/G4/H10/H11/H12/H13/H14/U15/U16); `B113 = K82/3600*B112/(1000*0.75)` (Pw); `B114 = B113/(0.98*H108)` (Pm); `F113 = ABS(K70*N20*N23*(E40-E33)/3600)` → 15.96 kW (frost-protection heating power = ṁ·cp·ΔT, ΔT = E40−E33 = −13 K).

## 4.4 Formula 1 — Bin Hours (Operating-Hour Conversion)

**Mathematical form**: annual operating hours of bin k (temperature t_A = k °C, k = −25…35):

$$
B_k = \frac{O_{k+30}}{8760}\cdot t_{VL,V} \quad[\mathrm{h/a}]
$$

where $O_{k+30}$ = `Klimadaten!O5:O65` (bin hours, see Chapter 6) and $t_{VL,V}$ = `Berechnung LU!K68` (full-load hours on an air-volume basis, see Chapter 3).

**Workbook implementation** (`Berechnung LU!B121`, t_A = −25 °C): `=Klimadaten!O5/8760*$K$68` (bin k ↔ Klimadaten row k+30).

**Units**: h/a. **Property**: $\sum_k B_k = t_{VL,V}$ (=3900 h in the example) — SIA full-load hours are "spread back" over the temperature bins as the annual operating time of each stage; this is also the connecting point between the "temperature-bin method" and the "full-load-hour method".

**Verification**: k = −10 (row 136): `B136 = 6/8760×3900 = 2.671 h` ✓; k = 22 (row 168): `59.6575 h` ✓.

**Assumptions**: ① the bin-hour distribution is independent of the system's operating periods (operation does not change the shape of the bin distribution, only compresses the total duration); ② the bin temperature is taken as the lower bound of the bin.

**Scope**: all 61 rows of the IST block; the SOLL block (rows 189–249) is isomorphic but dormant.

**Cell origins**: `Berechnung LU!B121:B181`; climate source `Klimadaten!O5:O65`; `K68`.

## 4.5 Formula 2 — Outdoor State and Frost-Protection Preheating

**Mathematical form**: outdoor state (moisture content $x_A$, relative humidity at room temperature $\varphi_R$):

$$
x_A = \text{Klimadaten!Q}_{k+30}\ [\mathrm{g/kg}],\qquad
\varphi_R = \min\!\big(1,\ \varphi(t_{Raum}, x_A, p)\big)
$$

Frost-protection preheating (only when $t_A \le t_{VS}$, i.e. `A{n}<=$E$33`):

$$
t_{VS} = t_A + \frac{P_{VS}\cdot 3600}{\dot V_{Jahr}\,\rho\, c_{pl}} \quad[\mathrm{°C}]
$$

**Workbook implementation**: `C{n} = Klimadaten!Q{k+30}`; `E{n} = MIN(100%,RelFeuchte(BR{n},C{n},$N$19))`; `G{n} = IF(A{n}<=$E$33,(IF($E$32=$I$32,DB{n},IF($E$32=$I$33,DC{n},0))*3600)/($K$70*$N$20*$N$23)+A{n},A{n})`; `DB{n} = IF(A{n}<=$E$33,$F$113,0)` (on/off type); `DC{n} = IF(A{n}<=$E$33,ABS($K$70*$N$20*$N$23*MIN(ABS(A{n}-$E$33),ABS($E$40-$E$33))/3600),0)` (variable type).

**Units**: g/kg; –; °C.

**Derivation**: $\varphi_R$ uses `RelFeuchte` (Chapter 1, formula 5) to back-calculate the relative humidity of the outdoor moisture content at room temperature (`BR`, from the temperature curve) — i.e. the simplified model "room humidity follows the outdoor moisture content" (when there is no independent moisture source). Frost-protection power `F113 = ṁ·cp·(t_design−t_boundary)/3600` (kW); preheating temperature rise = P/(ṁ·cp).

**Assumptions**: in the example `E32=0` (frost protection off) and `E33=0`, so `G{n} = A{n}` (no preheating); the room humidity band [E50, E48] = [0, 1] (not constraining).

**Scope**: all 61 bins; the frost-protection branch activates only when t_A ≤ E33.

**Cell origins**: `Berechnung LU!C121:C181, E121:E181, G121:G181, DB121:DB181, DC121:DC181`, `F113`.

## 4.6 Formula 3 — Heat Recovery WRG (Fixed and Modulated Efficiency)

**Mathematical form**: let the exhaust-air (Abluft) temperature be $t_{AB}$ (=`BU`, = room temperature, +2 K for Quellluft), the outdoor temperature $t_A$, and the WRG nominal efficiency $\eta_0$ (=`E28`=0.8):

$$
t_{WRG,0} = t_A + \eta_0(t_{AB}-t_A);\qquad
t_{WRG,reg} = t_A + \varepsilon(t_{AB}-t_A),\quad
\varepsilon = \max\!\Big(\frac{t_{ist}-t_A}{t_{AB}-t_A},\ 0\Big)
$$

where $t_{ist} = \min(t_{WRG,0},\ t_{ZUL,soll})$ (no over-recovery — full bypass in summer gives $\varepsilon=0$).

**Workbook implementation**:
- `I{n} = $E$28*(BU{n}-A{n})+A{n}` (fixed efficiency);
- `J{n} = IF(F{n}=0,MIN(I{n},BJ{n}),I{n})` (limiting; `F{n} = IF(H{n}<=0,IF(BU{n}<A{n},1,0),0)` is the summer cooling flag);
- `K{n} = IF($E$30=$S$20,$E$28,MAX(IF(AND($E$31=$S$20,F{n}=1),0,IF(A{n}=BU{n},0,(J{n}-A{n})/(BU{n}-A{n}))),0))` (**modulated efficiency**; E30="ja" bypass present → use the ratio formula);
- `L{n} = IF($E$30=$S$21,K{n}*(BU{n}-A{n})+A{n},I{n})` (supply-side temperature after the bypass);
- `M{n} = IF($E$28=0,C{n},(K{n}/$E$28*$E$29)*(BW{n}-C{n})+C{n})` (moisture recovery, E29=0 → M = x_A).

**Units**: °C; ε [–].

**Derivation**: inverse solution of the efficiency definition $\varepsilon = (t_{nach}-t_{vor})/(t_{quelle}-t_{vor})$; bypass modulation reduces ε from the nominal value to the value that just reaches the supply-air set temperature, and in summer (outdoor ≥ setpoint) it is 0 (full bypass). **Verification** (row 168, t_A=22 °C, t_AB=24 °C, t_ZUL,soll=20 °C): `I168 = 22+0.8×(24−22) = 23.6` ✓; `J168 = MIN(23.6, 20) = 20`; `K168 = (20−22)/(24−22) = −1 → MAX(…,0) = 0` (full bypass) ✓; `L168 = 22` ✓.

**Assumptions**: the efficiency is linear in the temperature difference (no degradation at freezing/condensation); KRG (E31) is present and ε is forced to 0 in summer; moisture recovery is proportional to ε (scaled by E29).

**Scope**: applies in both winter and summer; the example (E30="ja") takes the modulated branch, while E30="nein" uses the fixed η0.

**Cell origins**: `Berechnung LU!F121:F181, H121:H181, I121:I181, J121:J181, K121:K181, L121:L181, M121:M181`, `BU121:BU181` (exhaust-air temperature), `BW121:BW181` (exhaust-air moisture content).

## 4.7 Formula 4 — Mixed Air MIL (Fresh-Air Ratio and Bypass)

**Mathematical form** (enthalpy-control branch; the temperature-control branch is active when E36≠D36, see §4.10): fresh-air ratio $\gamma_{min}=\text{E34}$, $\gamma_{max}=\text{E35}$ (both 1 in the example):

$$
h_{MIL} = \gamma\, h_{nWRG} + (1-\gamma)\, h_{AB};\qquad
u = 1 - \frac{h_{soll}-h_{AB}}{h_{nWRG}-h_{AB}};\qquad
t_{MIL} = t_{nWRG}(1-u)+t_{AB}\,u
$$

(u = return-air share that brings $h_{MIL}$ to the target $h_{soll}$; in the example γ=1 → u=0, MIL = pure fresh air.)

**Workbook implementation**: `N{n} = EnthalpieA(L{n},M{n},$N$19)*$E$35+(1-$E$35)*EnthalpieA(BU{n},BW{n},$N$19)` (enthalpy, γ_max); `O{n}` analogous with γ_min; `P{n} = 1-IF(EnthalpieA(L{n},M{n},$N$19)=S{n},$E$35,(S{n}-EnthalpieA(BU{n},BW{n},$N$19))/((EnthalpieA(L{n},M{n},$N$19)-EnthalpieA(BU{n},BW{n},$N$19))))`; `Q{n} = L{n}*(1-P{n})+BU{n}*P{n}`; `R{n} = M{n}*(1-P{n})+BW{n}*P{n}`; `S{n} = MIN(MAX(N{n},BM{n}),O{n})` (target enthalpy = h_ZUL,soll, clamped to [h_MIL,min, h_MIL,max]); the temperature-control branch is analogous: `T{n} = MIN(L*E35+BU*(1-E35))` (MIN with a single argument is a no-op), `U{n}`, `V{n} = 1-IF(L{n}=W{n},$E$35,(W{n}-BU{n})/(L{n}-BU{n}))`, `W{n} = MIN(MAX(T{n},BJ{n}),U{n})`, `X{n} = M{n}*(1-$V{n})+BW{n}*$V{n}`, `Y{n} = EnthalpieA(W{n},X{n},$N$19)`.

**Units**: kJ/kg; °C; g/kg.

**Derivation**: mixing law (energy and mass conservation): $h = \sum w_i h_i$, $t = \sum w_i t_i$, $x = \sum w_i x_i$; the return-air share u is solved from the target enthalpy.

**Assumptions**: in the example γ_min=γ_max=1 (no return air); the enthalpy-control branch (P/Q/R) feeds downstream only when `$E$36=$D$36`, while the temperature-control branch (V/W/X/Y) is always computed and is used by the Fall detector AW (E36="Temperatur").

**Scope**: all bins; for return-air systems (γ<1), P/V give the return-air share.

**Cell origins**: `Berechnung LU!N121:Y181`.

## 4.8 Formula 5 — Cooling Coil and Linear Cooling Curve (A/C/D1/D2)

**Mathematical form**: the cooling-coil surface temperature is approximated by the mean water temperature $t_{LK} = \mathrm{AVERAGE}(E45:F46)$ = 9 °C (VL 6 / RL 12 °C); the coil outlet is the saturated state $(t_{LK}, x_s(t_{LK}))$, but with moisture content not lower than the supply setpoint $x_{soll}$:

**Workbook implementation**:
- `Z{n} = AVERAGE($E$45:$F$46)` (=9); `AA{n} = IF($E$36=$D$36,MIN(AbsFeuchte(Z{n},100%,$N$19),R{n}),MIN(AbsFeuchte(Z{n},100%,$N$19),X{n}))` (coil-dew-point moisture content, clamped by min); `AB{n} = EnthalpieA(Z{n},AA{n},$N$19)`;
- **Linear cooling curve** (straight line through the coil point and the MIL point in the (t, x) plane): `AF{n} = AVERAGE($E$45:$E$46)` (=9, intercept temperature); `AG{n} = IF($E$36=$D$36,IF(AA{n}=R{n},1E+23,(Q{n}-AF{n})/(R{n}-AA{n})),IF(AA{n}=X{n},1E+23,(W{n}-AF{n})/(X{n}-AA{n})))` (slope dt/dx);
- **D1** (dehumidification endpoint, cooled to $x_{soll}$): `AH{n} = IF($E$36=$D$36,MAX(IF(R{n}>BL{n},AF{n}+(AG{n}*(BL{n}-AA{n})),Q{n}),Z{n}),…)`; `AI{n} = IF(AH{n}=Z{n},AA{n},BL{n})`; `AJ{n} = EnthalpieA(AH{n},AI{n},$N$19)`;
- **D2** (cooled to supply temperature): `AK{n} = IF($E$36=$D$36,MAX(MIN(Q{n},BJ{n}),Z{n}),MAX(MIN(W{n},BJ{n}),Z{n}))`; `AL{n} = IF(Z{n}=AK{n},AA{n},(BJ{n}-AF{n})/AG{n}+AA{n})` (interpolate along the curve); `AM{n} = EnthalpieA(AK{n},AL{n},$N$19)`.

**Units**: °C; g/kg; kJ/kg; slope °C/(g/kg).

**Derivation**: the saturated line at the coil outlet $x_s(T)$ uses the Glück polynomial (Chapter 1); the "linear cooling curve" approximates the coil process line as a straight line in the (t,x) plane (coil point ↔ MIL point), used to find "the temperature for a given x" and "the x for a given temperature" — the classic approach for simplified coil models (a linearization approximating a constant wet-bulb / constant-enthalpy process).

**Verification** (row 168): `AA168 = MIN(x_sat(9)=7.617, x_MIL=10.037) = 7.617`; `AG168 = (22−9)/(10.037−7.617) = 5.372 °C/(g/kg)` ✓; `AK168 = MAX(MIN(22,20),9) = 20`; `AL168 = (20−9)/5.372+7.617 = 9.664` ✓; `AM168 = h(20, 9.664) = 44.66 kJ/kg` ✓.

**Assumptions**: the coil outlet is always saturated (no bypass leakage); the mean water temperature of 9 °C represents the coil surface; the supply-air set temperature BJ is the lower bound.

**Scope**: all bins; core states for the dehumidification (Fall 2/3) and cooling (Fall 3/4) cases.

**Cell origins**: `Berechnung LU!Z121:AM181`; `AD{n}` is a temporary column feeding only `AE{n}` (`AD = n-122`, `AE = EnthalpieA(AC,AD)` — AE is not referenced downstream; it is a legacy/draft column, see §4.14-5).

## 4.9 Formula 6 — Case Determination (Fall 1–4) and Supply-Air IST State

**Mathematical form** (`AW{n}`, temperature-control branch; comparisons use ROUND(·,4) to guard against floating point):

1. **Fall 1 heating + humidification**: $h_{soll}\ge h_{MIL}$ and $x_{soll}\ge x_{MIL}$ and $t_{soll}\ge t_{MIL}$;
2. **Fall 2 dehumidification + heating**: $x_{MIL} < x_{Register}$ (must first be cooled to the coil dew point);
3. **Fall 3 cooling (± dehumidification reheat)**: $t_{soll}\ge t_{D1}$ (after cooling, no reheat needed, or reheat only up to the setpoint);
4. **Fall 4 cooling + humidification**: otherwise (overcooling makes humidification necessary).

**Workbook implementation** (`AW{n}` temperature-control branch):

```
=IF($E$36=$C$36,IF(AND(ROUND(BM{n},4)>=ROUND(S{n},4),ROUND(BL{n},4)>=ROUND(R{n},4),ROUND(BJ{n},4)>=ROUND(Q{n},4)),1,
   IF(ROUND(BL{n},4)<ROUND(AA{n},4),2,IF(ROUND(BJ{n},4)>=ROUND(AH{n},4),3,4))),
   IF(AND(ROUND(BM{n},4)>=ROUND(Y{n},4),ROUND(BL{n},4)>=ROUND(X{n},4),ROUND(BJ{n},4)>=ROUND(W{n},4)),1,
   IF(ROUND(BL{n},4)<ROUND(AA{n},4),2,IF(ROUND(BJ{n},4)>=ROUND(AH{n},4),3,4))))
```

**Supply air IST** (`BB..BI` columns, temperature/moisture content for the four cases; `BB`/`BC` call the VBA UDFs `Fall1Tzul/Fall1xzul`, `BD`/`BE` call `Fall2Tzul/Fall2xzul` (`Fallunterscheidung.bas`), `BF`/`BG`/`BH`/`BI` are inline IFs):

```
BN{n} = BB{n}+BD{n}+BF{n}+BH{n}      ' t_ZUL,ist [°C]
BP{n} = BC{n}+BE{n}+BG{n}+BI{n}      ' x_ZUL,ist [g/kg]
BQ{n} = EnthalpieA(BN{n},BP{n},$N$19) ' h_ZUL,ist
```

**Units**: –; °C; g/kg; kJ/kg.

**Derivation**: the four cases cover all positional relations of the supply-air setpoint relative to the MIL point in the h–x diagram (heating + humidification / dehumidification + heating / cooling ± reheat / cooling + humidification); the t/x of each case is given by combining the available-equipment flags (`AX` heating, `AY` humidification, `AZ` cooling, `BA` dehumidification) with the state points (Q/R enthalpy-controlled MIL, W/X temperature-controlled MIL, Z/AA coil, AH/AI D1, BJ/BL setpoints).

**Verification** (row 168, t_A=22 °C): `AW168 = 4` (summer cooling case) ✓; `BN168 = BH168 = 20 °C`, `BP168 = BI168 = 10.037 g/kg` (Fall 4 humidified to setpoint x) ✓; `BQ168 = 45.60 kJ/kg`.

**Assumptions**: when equipment is missing, the output of the corresponding case is gated by the flags (e.g. no heating coil → AX=0 → Fall 1 outputs nothing); multiple cases never output simultaneously for the same bin (AW is single-valued).

**Scope**: all bins; this is the IST side of the "IST vs SOLL comparison" (§4.10).

**Cell origins**: `Berechnung LU!AW121:AW181, AX121:BA181, BB121:BI181, BN121:BQ181`; UDF source `Fallunterscheidung.bas` (`Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul` — columns BB–BE call them by name, so they are **live code** (an earlier assessment misjudged them as dead code); `#NAME?` appears only in AQ/AS (`TaupunktA`), which proves that the four UDFs of BB–BE are available in the VBA binary and are resolved by the formula engine).

## 4.10 Formula 7 — Supply-Air Setpoint (SOLL) and Room/Exhaust-Air State

**Supply-air setpoint** (piecewise-linear interpolation of the temperature curve, `BJ{n}`):

$$
t_{ZUL,soll} = \begin{cases} t_{ZUL,1} - (t_{A,1}-t_A)\, m_{t,1} & t_A \le t_{A,1}\\ t_{ZUL,2} - (t_{A,2}-t_A)\, m_{t,2} & t_A \le t_{A,2}\\ t_{ZUL,3} - (t_{A,3}-t_A)\, m_{t,3} & \text{sonst}\end{cases}
$$

Implementation: `BJ{n} = IF($DA{n}<=$B$89,$C$89-($B$89-$DA{n})*$I$88,IF($DA{n}<=$B$90,$C$90-($B$90-$DA{n})*$I$89,$C$91-($B$91-$DA{n})*$I$90))` (`DA{n} = A{n}` = t_A). Supply-air setpoint moisture content: `BK{n} = MIN(1,RelFeuchte(BJ{n},BT{n},$N$19))`, `BL{n} = AbsFeuchte(BJ{n},BK{n},$N$19)` (i.e. the setpoint humidity is the moisture content at room-temperature relative humidity, drifting with the outdoor moisture content), `BM{n} = EnthalpieA(BJ{n},BL{n},$N$19)`.

**Room/exhaust air**: `BR{n}` (room temperature, interpolated with the `J` slopes of the same temperature curve); `BS{n} = IF(E{n}<$E$50,$E$50,IF(E{n}>$E$48,$E$48,E{n}))` (room rF clamped to [E50, E48]); `BT{n} = AbsFeuchte(BR{n},BS{n},$N$19)` (room moisture content); `BU{n}` (exhaust-air temperature = room temperature, +2 K for Quellluft; the `I21` temperature-difference input branch contains a dead `#REF!` reference); `BW{n} = BT{n}+$I$20` (exhaust-air moisture content = room + moisture load); `BV{n} = RelFeuchte(BU{n},BW{n},$N$19)`.

**Units**: °C; g/kg; kJ/kg; –.

**Assumptions**: the exhaust-air state = the room state (perfect mixing); the room humidity band [E50,E48] is [0,1] in the example (not constraining); no independent room moisture source (E52=0 → I20=0).

**Cell origins**: `Berechnung LU!BJ121:BM181, BR121:BW181`; temperature-curve breakpoints `B88:D91` and slopes `I88:J90`.

## 4.11 Formula 8 — Enthalpy Difference and Energy (Per-Bin MWh)

**Enthalpy-difference columns** (kJ/kg; treatment load between the supply-air setpoint and IST, grouped by case):

| Column | Meaning | Formula (temperature-control branch) |
|---|---|---|
| `BZ` | Cooling (MIL→D2, Fall 2/3/4) | `MAX(IF(AZ=1,IF(OR(AW=3,AW=4,AW=2),Y-AM,0),0),0)` |
| `CA` | Dehumidification cooling (D2→D1 or topped up to coil enthalpy, Fall 2/3) | `MAX(IF(BA=1,IF(AW=3,AM-AJ,IF(AW=2,(IF(BP=R,0,S-AB-BZ)),0)),0),0)` |
| `CB` | Dehumidification reheat (Fall 2/3) | `MAX(IF(AND(BA=1,AX=1),IF(AW=3,BQ-AJ,IF(AW=2,IF(R=BP,0,BQ-AB),0)),0),0)` |
| `CC` | Heating (MIL→G, Fall 1) | `IF(F=1,0,IF(AX=1,IF(AW=1,AV-Y,0),0))` |
| `CD` | Humidification heating (G→ZUL ist, Fall 1/4) | `IF(AND(AY=1,B>0),IF(OR(AW=1,AW=4),BQ-AV,0),0)` |

`BX = BZ+CA` (total cooling enthalpy difference), `BY = CB+CC+CD` (total heating enthalpy difference).

**Energy columns** (MWh per bin; mass flow = `K70`×`N23` kg/h):

| Column | Meaning | Formula |
|---|---|---|
| `CJ` | Cooling energy | `IF($E$42=$S$21,IF(OR(AND(A>=$E$26,$E$27>0),AND(A>=$E$26,$E$27<0)),$P$70*B*$N$23*(BZ)/3.6/1000000,$K$70*B*$N$23*(BZ)/3.6/1000000),0)` |
| `CE` | Dehumidification cooling energy | Analogous ×(CA) |
| `CK` | Heating energy | Analogous ×(CC) |
| `CF` | Dehumidification reheat energy | Analogous ×(CB) |
| `CG` | Humidification heating energy (adiabatic humidification) | Analogous ×(CD) (no E42 gating) |
| `CM` | Humidification energy (selected by humidification type) | `IF($E$49=$S$16,0,IF($E$49=$S$17,CG,CI))` |
| `CT` | Fan energy | `IF(OR(AND(A>=$E$26,$E$27>0),AND(A>=$E$26,$E$27<0)),B*($R$70/1000),B*($M$70)/1000)` |
| `CW` | Bin total energy | `SUM(CK,CJ,CE,CF,CM,CT)` |

**Water-quantity columns**: `CH` (humidification water, L) = `MAX(0,(BP−R)·B·K70·N23/1000)`; `CI` (steam humidification energy, MWh) = `(CH*$N$22*(100-$E$51)+$N$25*CH)/3600000` (water heated from E51=10 °C to 100 °C and vaporized, r100=2256); `CL` (condensate amount) = analogous with a negative sign.

**Unit derivation**: energy = mass flow [kg/h] × hours [h] × enthalpy difference [kJ/kg] = kJ; ÷3.6e6 → MWh (1 MWh = 3.6e6 kJ). Fan: kW × h ÷ 1000 → MWh. Water: Δx [g/kg] × kg/h × h ÷ 1000 → kg = L.

**Verification** (row 168, t_A=22 °C): `CJ168 = 3819.23×59.6575×1.15×2.9945/3.6e6 = 0.21795 MWh` ✓ (BZ168 = S−AM = 47.65−44.66 = 2.9945); `CT168 = 59.6575×6.8629/1000 = 0.40942 MWh` ✓.

**Assumptions**: the air mass flow is based on the year-weighted average air volume `K70` (the summer dV branch uses `P70`; no difference in the example since E27=0); density is a constant 1.15 kg/m³; humidification/dehumidification water is computed linearly from the moisture-content difference.

**Cell origins**: `Berechnung LU!BZ121:CD181` (enthalpy difference), `CE121:CM181`, `CT121:CT181`, `CH121:CH181`, `CI121:CI181`, `CL121:CL181`, `CW121:CW181`.

## 4.12 Formula 9 — Annual Summary (Rows 182/183 → Rows 254–260 → Row 7 → Lüftung)

**Energy sums** (row 182, MWh):

```
CJ182 = SUM(CJ122:CJ181)      CK182 = SUM(CK122:CK181)
CE182 = SUM(CE122:CE181)      CF182 = SUM(CF122:CF181)
CM182 = SUM(CM122:CM181)      CT182 = SUM(CT122:CT181)
CH182 = SUM(CH122:CH181)      CL182 = SUM(CL122:CL181)
```

**Power maxima** (row 183, kW; MAX enthalpy difference × design air volume E18 × ρ / 3600):

```
BZ183 = MAX(BZ$121:BZ$181)*$E$18*$N$23/3600      ' cooling power
CA183 = MAX(CA$121:CA$181)*$E$18*$N$23/3600      ' dehumidification cooling power
CB183 = MAX(CB$121:CB$181)*$E$18*$N$23/3600      ' dehumidification reheat power
CC183 = MAX(CC$133:CC$181)*$E$18*$N$23/3600      ' heating power (note: starts at row 133!)
CD183 = MAX(CD$121:CD$181)*$E$18*$N$23/3600      ' humidification heating power
```

**Annual result rows** (rows 254–260, kWh/kW):

| Row | Segment | Energy | Power |
|---|---|---|---|
| 254 | Luftkühlung | `C254 = IFERROR(CJ182*1000,0)` → 1750.16 kWh | `D254 = BZ183` → 25.78 kW |
| 255 | Lufterwärmung | `C255 = IFERROR(CK182*1000,0)` → 3786.30 kWh | `D255 = CC183` → 16.15 kW |
| 256 | Erwärmung Bef. | `C256 = IFERROR(CM182*1000,0)` ≈ 0 | `D256 = CD183` ≈ 0 |
| 257 | Entfeuchtung Kühlung | `C257 = IFERROR(CE182*1000,0)` → 0 | `D257 = CA183` → 0 |
| 258 | Entfeuchtung Erwärmung | `C258 = IFERROR(CF182*1000,0)` → 0 | `D258 = CB183` → 0 |
| 259 | Ventilator | `C259 = IFERROR(CT182*1000,0)` → 26765.14 kWh | `D259 = G6` → 6.863 kW |
| 260 | Total | `C260 = SUM(C254:C259)` → 32301.60 kWh | `D260 = SUM(D254:D259)` → 48.80 kW |

**Row 7 (MWh/kW results)**: `H7 = C259/1000` (fan electrical energy 26.765 MWh), `P7 = D254`, `Q7 = C254/1000`, `R7 = D255`, `S7 = C255/1000`, `T7 = D256`, `U7 = C256/1000`, `V7 = D257`, `W7 = C257/1000`, `X7 = D258`, `Y7 = C258/1000`; `J7 = ROUND(IF(G6=0,0,H7*1000/G6),-1)` (full-load-hour check = 3900).

**Write-back to Lüftung** (template row 32): `Lüftung!Q32 ← 'Berechnung LU'!P7` (Luftkühlung power), `R32 ← Q7` (energy), `S32 ← R7`, `T32 ← S7`, `I32 ← H7` (fan energy), `K32 ← J7` (full-load hours); **note the misalignment**: `Lüftung!U32 ← V7` (dehumidification cooling power, but the header says "Befeuchtung"), `V32 ← W7`, `W32 ← X7`, `X32 ← Y7`, `Y32 ← T7` (humidification heating power, header says "Entf. Erwärmung"), `Z32 ← U7` — i.e. the wiring of the six columns U…Z on the `Lüftung` sheet is **shifted by one pair relative to the headers** (see §4.14-8; in the example building all three pairs are 0, so no visible difference results).

**Cell origins**: rows `Berechnung LU!182–183`, `254–260`, `7`; `Lüftung!Q32:Z32, I32, K32`.

## 4.13 Formula 10 — Fan Model (Stages, Affinity Laws, Efficiency, Energy Consumption)

**Staged air volumes** (`E18:E20`, `E23:E25`):

$$
\dot V_1 = \dot V_{nom},\qquad \dot V_2 = \dot V_{nom}\cdot\begin{cases}1 & \text{einstufig}\\ 0.67 & \text{sonst}\end{cases},\qquad \dot V_3 = \dot V_{nom}\cdot\begin{cases}1 & \text{einstufig}\\ 0.67 & \text{zweistufig}\\ 0.33 & \text{stufenlos}\end{cases}
$$

Implementation: `E19 = IF(OR(I6="einstufig",I6="1 vitesse",I6="1 velocità"),E18,E18*0.67)`; `E20 = IF(OR(I6="einstufig",…),E18,IF(OR(I6="zweistufig",…),E18*0.67,E18*0.33))` (compatible with labels in three languages).

**Staged power (fan affinity laws, exponent 2.5)** (`I14:I16` ZUL, `I17:I19` ABL):

$$
P_{stufe} = P_{nom}\cdot\Big(\frac{\dot V_{stufe}}{\dot V_{max}}\Big)^{2.5},\quad P_{nom} = \frac{G6}{2}\ (\text{ZUL}),\ \text{ABL same}
$$

Implementation (`I14`): `=IF(E18<MAX(E19:E20),IF(ISERROR(E16*(E18^2.5)/(E19^2.5)),0,E16*(E18^2.5)/(MAX(E18:E20)^2.5)),E16)`.

**Operating-time weighting** (rows 64–67): `J64 = E18`, `K64 = J64*M58` (weighted air volume), `L64 = (I14/C108+I17/E108)` (power including motor efficiency η), `M64 = L64*M58`; `K67 = SUM(K64:K66)` (= E18 consistency check), `M67 = SUM(M64:M66)` (= G6 ✓); `M70 = G6*K69/K68` (year-weighted average power).

**Annual fan energy**: `CT{n} = B{n}*M70/1000` (MWh); `C259 = CT182*1000` (kWh); `H7 = C259/1000` (MWh).

**Units**: m³/h; kW; MWh.

**Derivation**: fan affinity laws: $P \propto \dot V^3$ (constant density, constant speed and constant efficiency). An exponent of 3 assumes constant efficiency; in reality the motor + drive efficiency falls with load, so engineering practice often takes 2.5–2.8 as a compromise (this tool uses **2.5**, annotated in VBA/header conventions). Motor efficiency comes from the efficiency-class × power-band lookup (`C108` etc.).

**Verification**: `M67 = 6.863 = G6` ✓; `CT168 = 0.40942 MWh` ✓; `CT182 = 26.765 MWh` → `H7 = 26.765` ✓ (consistent with `Lüftung!I7`).

**Assumptions**: the efficiency-class lookup is selected by rated power E16; within a stage, power and air volume are constant; the ISERROR guard prevents division by zero for zero air volume.

**Cell origins**: `Berechnung LU!E16:E25, I14:I19, J64:M67, K68:K70, M70, CT121:CT181, C259, H7`.

## 4.14 Known Quirks and Risks (Observed)

1. **Dead `TaupunktA` reference**: `AQ{n} = TaupunktA(AR{n},$N$19)` → `#NAME?`, cascading to `AS{n}` → `#VALUE!` (122 bins × 2 blocks). Columns AQ/AS ("ZUL Taupunkt bei Entfeuchtung (F)") do not feed any result — but they should be removed or fixed during a port (using the Chapter 1 Glück inverse).
2. **Energy sums start at row 122**: `SUM(CE122:CE181)` etc. exclude t_A = −25 °C (row 121) from the annual sum (that bin has 0 hours, so no practical effect); the power maximum `CC183 = MAX(CC$133:CC$181)` starts at −10 °C (likewise no practical effect because CC is constantly 0 in the low bins, but the convention is inconsistent).
3. **Dormant SOLL block**: columns B/C/D are literally 0, the pressure reference is `#REF!`, `K82/M82/P82/R82=0` → all SOLL energies are 0; activating the SOLL inputs would require fixing the `#REF!` and backfilling the climate data.
4. **`T{n} = MIN(single-argument)`** is a no-op (intermediate value of temperature-controlled mixing) — a formula leftover.
5. **Columns `AD/AE` are draft columns**: AD = the consecutive integers of row number − 122 (−1…59), referenced only by AE, which in turn has no downstream — suspected debugging/charting residue; `AD181=59` makes `AE181 = h(9, 59 g/kg) = 157.6 kJ/kg` (59 g/kg at 9 °C is a supersaturated state, physically unreachable).
6. **Chart guard values**: columns `CN…CV` use 222/−222 to "kick" the curves of bins without hours out of the charts; `AG` uses 1E+23 to prevent vertical cooling curves.
7. **Empty energy prices**: `I26:I28`, `J26:J28` are unfilled → the costs `F254:F259` are all 0; only the water price 185 Rp./m³ (I29/J29) is effective.
8. **Misaligned `Lüftung` U…Z wiring**: `Lüftung!U32:Z32 ← 'Berechnung LU'!V7/W7/X7/Y7/T7/U7` is shifted by one pair relative to the `Lüftung` headers (Befeuchtung / Entf. Kühlung / Entf. Erwärmung); `Resultate!C37/C38` ("Erwärmung Befeuchtung"←`Lüftung!V23`, "Kühlung Entfeuchtung"←`Lüftung!X23`) take values along the same misalignment chain. In the example building all three pairs are ≈0, so it was never exposed; when porting, rewire according to the semantics of rows 254–258 of Berechnung LU.
9. **The operating schedule does not feed energy directly**: `L58:L61` (80 h/week) is used only for stage weighting (M58:M60); the annual hours come from K68 (Std full-load hours) — two time concepts coexist.
10. **`E41/E44` (installed coil power) are empty**: only the existence checks and design temperatures take part in the calculation; annual energy does not need installed power.
11. **Documentation row `A184/D184`** contains legacy formula text (the references of `LUET/LUEAB` to `Auswertung!T6` etc.) — historical residue and one of the `#NAME?` risk sources (not active in this file).
12. **Constant air mass flow**: all enthalpy-difference energies are computed with `K70` (year-weighted average air volume), not corrected for temperature/density within a bin; the density 1.15 kg/m³ is a year-round constant.
13. **The exhaust-air-temperature branch in column `BU` contains `#REF!`**: `IF(E13=$S$10,BR+$N$18+#REF!,BR+$I$21)` — the bad branch is only evaluated when "Quellluft and I21≠0" both hold; the current inputs (Mischluft, I21=0) do not trigger it.
14. **`#N/A` in `J11`/`F40`**: caused by the SOLL state formulas and the empty SOLL design temperatures; it does not affect the IST results.

## 4.15 Computation-Chain Overview (For Review)

```
t_A (Klimadaten!M) ─► B = O/8760·K68 (bin operating hours)
AUL: x_A=C, φ_R=E ─► frost protection G (off) ─► WRG: I/J/K/L/M (ε modulated, summer bypass ε=0)
MIL: N..Y (γ=1 pure fresh air) ─► cooling coil: Z..AM (A/C/D1/D2 + linear cooling curve)
Fall determination: AW (1 heating+humidification / 2 dehumidification+heating / 3 cooling±reheat / 4 cooling+humidification)
ZUL soll: BJ..BM (temperature curve + humidity drift); ZUL ist: BN..BQ (BB..BI by case)
enthalpy difference: BZ(cooling) CA(dehumidification cooling) CB(dehumidification reheat) CC(heating) CD(humidification heating)
energy: CJ/CE/CK/CF/CG/CM/CT = B·ṁ·Δh/3.6e6 (fan CT = B·M70/1000)
summary: row 182 sum (MWh) → row 183 max (kW) → rows 254..259 (kWh/kW) → row 7 (MWh) → Lüftung
```

## 4.16 Porting Notes

1. The bin method is inherently a vectorizable computation of 61 rows × state columns — port it as a per-bin loop or array operation; every bin is independent (no cross-bin state), so it is naturally parallelizable.
2. The state-column naming (AUL/nWRG/MIL/A/C/D1/D2/E/F/G/ZUL soll/ist/Raum/ABL) should be modeled as an explicit state machine; the four cases Fall 1–4 are output via the `AW` detector plus the equipment-availability flags (AX/AY/AZ/BA).
3. Constants: cpl/cpw/cw/ρ/r0/r100, 3600, 8760, 3.6e6, K70/M70, temperature-curve breakpoints, efficiency-class table, filter pressure-drop table — all should go into the model configuration.
4. Preserve the normative behavior: fan exponent 2.5; `ROUND(·,-1)`; min/MAX clamping of the WRG modulated efficiency ε; `ROUND(·,4)` against floating point; IFERROR/ISERROR guards.
5. Fix list (when porting): AQ/AS dead columns, Lüftung U…Z misalignment, CC183/sum-start convention, SOLL-block #REF!, AD/AE draft columns, price placeholders.
6. The single-instance engine's "macro loop 16 times" should be replaced by a functional call over the 16 systems (inputs = the 16-row parameter set of Lüftung!A32:Z32).
