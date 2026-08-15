# Structural Analysis of the Sheet "Berechnung LU" (Gebäude-Tool, SIA 2024)

Analysis source: `Energytools_refactored/.analysis/dumps/gebaeude/sheet_61_Berechnung LU.tsv`
(15,416 rows, 328 rows × 108 columns A…DD, of which columns A…DC are occupied; 13,466 formula cells).

**Purpose of the sheet:** Annual energy-demand calculation of an air-handling unit (AHU) using the
temperature-bin method with psychrometric states
(enthalpy / absolute humidity / relative humidity). The sheet computes **one** system
(here LA01); the parameters come from the sheet `Lüftung` (row 32), the
results go back to `Lüftung` (e.g. `'Berechnung LU'!H7`).

> **Corrections to the task specifications:**
> 1. Rows 7–22 are **not** 16 system result rows (LA01…LA16). Only row 6
>    (input) and row 7 (results) contain the data of the one system LA01
>    (`A6 = Lüftung!A32` → LA01). Rows 8–22 are headings and the input
>    block. The "copy-template row 32" lies in the sheet `Lüftung` (LA01 parameter row),
>    not here; here row 32 is `Vereisungsschutz`.
> 2. `$E$34`/`$E$35` are **not** WRG efficiencies, but **min./max. fresh-air fraction**
>    of the recirculation control (both = 1, i.e. 100 % fresh air, no recirculation). The
>    WRG efficiencies are in `$E$28` (0.8) and `$F$28` (0.65).
> 3. The sheet contains **two parallel temperature-bin blocks**: IST (rows 121–183,
>    inputs from column E) and SOLL (rows 189–250, inputs from column F). The
>    SOLL block is inactive in this workbook (climate-data cells = 0, `#REF!` print
>    reference), so it delivers 0 everywhere.

---

## 1. Layout Map (Rows)

| Rows | Role | Key cells |
|---|---|---|
| 1 | Title | `A1 "Berechnung LU"` |
| 3–5 | Table header of the system row | `C3 Volumenstrom`, `F3 Zu- und Abluft-Ventilator`, `K3 Zuluftkonditionierung`, `P3 Luftkühlung`, `R3 Lufterwärmung`, `T3 Befeuchtung Erwärmung`, `V3 Entfeuchtung Kühlung`, `X3 Entfeuchtung Erwärmung`; units row 5 (m³/h, W/(m³/h), kW, MWh, h/a, %, °C, % r.F.) |
| 6 | **System input row LA01** | `A6=Lüftung!A32` (LA01), `B6` Nutzung, `C6` Volumenstrom 8578.57 m³/h, `D6` Prozess 0, `E6` Projekt 0, `F6` SFP 0.8 W/(m³/h), `G6` Leistung 6.863 kW, `I6` Regelung "einstufig", `J6=F:K68` (3900), `K6` WRG 80 %, `L6` 20 °C (Sommer), `M6` 21 °C (Winter), `N6`/`O6` 0 % r.F. |
| 7 | **Result row** | `E7` Volumenstrom (E6||C6), `H7=C259/1000` Ventilator-MWh, `J7` Volllaststunden, `P7=D254`, `Q7=C254/1000`, `R7=D255`, `S7=C255/1000`, `T7=D256`, `U7=C256/1000`, `V7=D257`, `W7=C257/1000`, `X7=D258`, `Y7=C258/1000` |
| 8 | Ventistufe (fan stage) | `H8 "Ventistufe"`, `I8 = IF(I6=Begriffe!F205,1,IF(I6=Begriffe!F206,2,IF(I6=Begriffe!F207,3,FALSE)))` → 1 (einstufig) |
| 9–10 | Section headings "Eingabe / Grundlagen / Beschriftung", "IST-Zustand / SOLL-Zustand" | `G10 "L01"`, `N10–R10` power ranges of the efficiency classes (bis 1.1 kW … ab 110 kW), `S10 "Quellluft"` |
| 11–25 | **Input block Lüftungstechnik** (IST=column E, SOLL=column F) | Luftwechsel 11–13, Filter 14–15, ZUL-Ventilator 16–20, ABL-Ventilator 21–25 (details §2) |
| 26–27 | Saisonaler Volumenstrom (seasonal volume flow) | `E26` Sommerbetrieb ab t_A (0), `E27` Volumenstromerhöhung dV (0) |
| 28–33 | WRG/KRG | `E28=K6%` 0.8 (thermal WRG), `E29` 0 (Feuchte-WRG), `E30 "ja"` (Bypass), `E31 "ja"` (Kälterückgewinnung), `E32` 0 + `I32 "elektrisch (ein/aus)"`, `E33` 0 (Grenztemp. Vereisungsschutz), `I33 "elektrisch (variabel)"` |
| 34–38 | Umluft / Frischluftquelle (recirculation / fresh-air source) | `E34` 1 (Frischluftanteil min.), `E35` 1 (max.), `E36 "Temperatur"` (Regulierungsbasis), `D36` empty, `E37/E38 "Aussenluft"` |
| 39–46 | Heizregister / Kälteregister (heating coil / cooling coil) | `E39 "ja"` (Heizregister), `E40` −13 °C (design), `E41` empty (installed capacity); `E42 "ja"` (Kühlung), `E43` 35 °C / `F43` 30 °C (design), `E44` empty; `E45` 6 / `E46` 12 (LK VL/RL °C); `I39:I47` VLOOKUP table Regelungsarten (Zeitsteuerung 1.0 … VAV 0.55) |
| 47–51 | Entfeuchtung / Befeuchtung (dehumidification / humidification) | `E47 "ja"` (Entfeuchtung), `E48=IF(OR(N6="",N6=0),1,N6%)` → 1 (max. r.F.), `E49 "Adiabatisch Bef."` (type), `E50=IF(O6="",0,O6%)` → 0 (min. r.F.), `E51` 10 (Kaltwassertemperatur °C) |
| 52–55 | Raumlast / Nutzungszone (room load / usage zone) | `E52` 0 (Feuchtelast), `E54 "Benutzerdefiniert"` (Regelungsart), `E55` 0 |
| 56–69 | **Operating hours IST** | `B58:C61` time windows, `I58:I60` h/week per stage (50/15/15), `L58:L60` with VLOOKUP factor, `L61` 80 h, `M58:M60` shares (0.625/0.1875/0.1875); Stufen-Volumenströme/-Leistungen `J64:J66`, `K64:K66`, `L64:L66`, `M64:M66`, `K67`/`M67` sums |
| 70 | Plausibilitätstest IST | `K70=E7*K68/8760` (3819.2 m³/h), `M70=G6*K69/K68` (6.863 kW), `P70=K70`, `R70=M70` |
| 71–85 | **Operating hours SOLL + Plausibilitätstest SOLL** | analogous to column F; `K82=SUM(K79:K81)` (0), `M82=SUM(M79:M81)-B114` (0), `P82`, `R82` |
| 86–91 | **Temperature curve IST** (ZUL and room temperature f(t_A)) | `B88:B91` t_A (−15/22/24/30), `C88:C91` t_ZUL (21/20/20/20), `D88:D91` t_Raum (22/24/25/25); slopes `I88:I90`, `J88:J90` |
| 92–97 | **Temperature curve SOLL** | `B94:B97`, `C94:C97` (22/22/22/22), `D94:D97` (24/24/26/26); `I94:I96`, `J94:J96` |
| 100–108 | Fan power by efficiency class | Effizienz-Lookup per class × power range; `C108=MAX(C102:C107)` (1), `E108` (1), `H108` (0.85), `J108` (0.85) |
| 109–115 | Filter stages / Pw / Pm / Vereisungsschutz (frost protection) | `B110/B111` filter pressure drop (Pa), `B112` difference, `B113=Pw`, `B114=Pm`, `F113` Vereisungsschutz power (15.96 kW) |
| 117–120 | Header of the IST class block | column labels + units (detailed in §3) |
| 121–181 | **IST temperature-bin calculation** (61 classes, t_A = −25…+35 °C) | formula pattern §3/§4 |
| 182–183 | **IST sums** | row 182: energy sums `CE182…CM182`, `CT182`, `CW182`; row 183: power maxima `BZ183…CD183` |
| 184 | Documentation row (VBA formula text LUET/LUEAB, `#NAME?`-relevant) | `A184`/`D184` as text |
| 185–188 | Header of the SOLL class block | like 117–120, states over 3 columns (T, x, h) |
| 189–249 | **SOLL temperature-bin calculation** (inactive: B/C/D = 0, `#REF!` print) | same structure, inputs from column F, target curve from rows 94–97 |
| 250 | SOLL sums | `CE250…CM250`, `CT250` (all 0) |
| 251–253 | Header "Energieverbrauch IST/SOLL", chart lookups | `H253:J253` (t_ABL, r_F, x_Raum) |
| 254–263 | **Final result rows** (§6) | Luftkühlung, Lufterwärmung, Erwärmung Bef., Entfeuchtung (Kühlung/Erwärmung), Luftumwälzung (Ventilator), Total, Wasser Bef., Entfeuchtung-Wasser |
| 264–266 | Header "Daten für HG/KG", chart | `H265:N265` Begriffe!F152:F158 |
| 267–327 | **Chart data per class** (kW and kWh) | `B/C` heating power, `D/E` cooling power, `I:N` kWh per stage, `O` t_ZUL, `P` rF_ZUL |
| 328 | Chart totals | `I328:N328` sums |

---

## 2. Input Block (Rows 1–32) – Complete List of the Input-Carrying Cells

Values for the example system LA01 (IST = column E, SOLL = column F).

### Row 6 – System (from `Lüftung` row 32)
| Cell | Formula / Value | Meaning |
|---|---|---|
| A6 | `F:Lüftung!A32` → LA01 | Anlagenname |
| B6 | `F:Lüftung!B32` → "Einzel-, Gruppenbüro" | Nutzung (für Std-Lookup) |
| C6 | `F:Lüftung!C32` → 8578.571… | Standard-Volumenstrom m³/h |
| D6 | `F:Lüftung!D32` → 0 | Prozess-Volumenstrom |
| E6 | `F:Lüftung!E32` → 0 | Projekt-Volumenstrom |
| F6 | `F:Lüftung!G32` → 0.8 | SFP W/(m³/h) |
| G6 | `F:Lüftung!H32` → 6.862857 | Ventilatorleistung total (Zu+ABL) kW |
| I6 | `F:Lüftung!J32` → "einstufig" | Regelung |
| J6 | `F:K68` → 3900 | Volllaststunden (h/a) |
| K6 | `F:Lüftung!L32` → 80 | WRG % |
| L6 | `F:Lüftung!M32` → 20 | Zuluft-Solltemperatur Sommer °C |
| M6 | `F:Lüftung!N32` → 21 | Zuluft-Solltemperatur Winter °C |
| N6 | `F:Lüftung!O32` → 0 | Feuchtesoll Sommer % r.F. |
| O6 | `F:Lüftung!P32` → 0 | Feuchtesoll Winter % r.F. |

### Row 7 – Results (see §6; here already the links)
`E7=IF(OR(E6="",E6=0),C6,E6)` (8578.57); `H7=C259/1000`; `J7=ROUND(IF(G6=0,0,H7*1000/G6),-1)`; `P7…Y7` see §6.

### Rows 11–25 – Lüftungstechnik (IST E / SOLL F)
| Cell | Value | Meaning |
|---|---|---|
| E11/F11 | 500 / 2 | Klimatisierte Fläche (m²) |
| E12/F12 | 3 / 3 | Raumhöhe (m) |
| E13/F13 | "Mischluft" | Art der Lufteinbringung (Alternative "Quellluft" = S10) |
| E14/F14 | "0 keinen" | Vorfilterklasse (LOOKUP against M28:M44) |
| E15/F15 | "0 keinen" | Nachfilterklasse |
| E16 | `F:G6/2` → 3.4314 | ZUL-Ventilatorleistung Stufe 1 (kW) |
| F16 | 0 | SOLL-ZUL-Leistung |
| E17 | "IE5 - gefaked" | ZUL-Motoreffizienzklasse (IST) |
| F17 | "IE3 (< 2016)" | SOLL |
| E18 | `F:E7` → 8578.57 | ZUL Stufe 1 Volumenstrom (m³/h) |
| F18 | 0 | SOLL |
| E19 | `F:IF(OR(I6="einstufig",I6="1 vitesse",I6="1 velocità"),E18,E18*0.67)` | ZUL stage 2 (einstufig → =E18, otherwise 67 %) |
| E20 | `F:IF(OR(I6="einstufig",…),E18,IF(OR(I6="zweistufig",…),E18*0.67,E18*0.33))` | ZUL stage 3 (33 % for stufenlos) |
| E21 | `F:E16` | ABL-Leistung Stufe 1 |
| E22 | `F:E17` | ABL-Motorklasse |
| E23/E24/E25 | `F:E18`/`F:E19`/`F:E20` | ABL Stufen-Volumenströme |
| I14…I16 | see §5.1 | ZUL-Stufenleistungen (Ventilatorgesetz) |
| I17…I19 | analogous to E21/E23..E25 | ABL-Stufenleistungen |
| I20 | `F:IF(E52=0,0,(E52*1000)/(3600*(K70/3600)*N23))` → 0 | Feuchtelast (g/kg Zuluft-Erhöhung) |
| J20 | analogous to F52/K82 | SOLL |

### Rows 26–33 – Saisonaler Volumenstrom, WRG/KRG
| Cell | Value | Meaning |
|---|---|---|
| E26/F26 | 0 / 0 | "Sommerbetrieb ab einer Aussentemperatur von" (°C) |
| E27/F27 | 0 / 0 | Volumenstromerhöhung dV (m³/h) in summer operation |
| E28 | `F:K6%` → 0.8 | WRG-Wirkungsgrad thermisch (IST) |
| F28 | 0.65 | WRG-Wirkungsgrad SOLL |
| E29/F29 | 0 / 0 | Feuchterückgewinnung (Faktor) |
| E30/F30 | "ja" | Bypass für Regulierung KRG/WRG |
| E31/F31 | "ja" | Kälterückgewinnung (KRG) |
| E32/F32 | 0 / 0 | Vereisungsschutz (0 = off; options "elektrisch (ein/aus)"=I32, "elektrisch (variabel)"=I33) |
| E33/F33 | 0 / 0 | Grenztemperatur Vereisungsschutz (°C) |

### Rows 34–38 – Umluft / Frischluftquelle
| Cell | Value | Meaning |
|---|---|---|
| E34/F34 | 1 / 1 | **Frischluftanteil minimal** (Umluftregulierung f(t_ZUL)) |
| E35/F35 | 1 / 1 | **Frischluftanteil maximal** |
| E36/F36 | "Temperatur" | Umluftregulierung anhand von (alternative: D36, empty here) |
| E37/F37 | "Aussenluft" | Frischluftquelle (alternative "Vorkonditionierte Luft von LXX") |
| E38/F38 | "Aussenluft" | Art der vorkonditionierten Luft |

### Rows 39–51 – Register, Entfeuchtung, Befeuchtung
| Cell | Value | Meaning |
|---|---|---|
| E39/F39 | "ja" | Heizregister installiert |
| E40 | −13 | Leistungsberechnung Heizung bei °C (Auslegungs-Aussentemp.) |
| F40 | `#N/A` (error) | SOLL-Auslegungstemperatur (empty dependency) |
| E41/F41 | empty | Installierte Heizleistung (kW) |
| E42/F42 | "ja" | Kühlung installiert |
| E43/F43 | 35 / 30 | Leistungsberechnung Kühlung bei °C |
| E44/F44 | empty | Installierte Kühlleistung |
| E45/F45 | 6 / 6 | LK-Register Vorlauf °C |
| E46/F46 | 12 / 12 | LK-Register Rücklauf °C |
| E47/F47 | "ja" / "nein" | Entfeuchtung installiert |
| E48 | `F:IF(OR(N6="",N6=0),1,N6%)` → 1 | Max. zulässige rel. Raumfeuchte / Zuluftfeuchte Sommer |
| F48 | 0.99 | SOLL |
| E49/F49 | "Adiabatisch Bef." / "keine" | Art der Befeuchtung (S16="keine", S17="Adiabatisch Bef.") |
| E50 | `F:IF(O6="",0,O6%)` → 0 | Min. zulässige r.F. Winter |
| F50 | 0.01 | SOLL |
| E51/F51 | 10 / 10 | Kaltwassertemperatur (°C) – for Dampfbefeuchter-Energie |

### Rows 52–55
| Cell | Value | Meaning |
|---|---|---|
| E52/F52 | 0 / 0 | Feuchtigkeitslast im Raum (g/h?) |
| E54/F54 | "Benutzerdefiniert" | Regelungsart Volumenstrom (VLOOKUP against I39:J47) |

### Rows 56–70 – Operating Hours & Plausibility (IST)
- Time windows: `B58:C58` = 08:00–18:00 (stage 1), `B62:C62` = 11:00–14:00 (stage 2), `B66:C66` = 14:00–17:00 (stage 3); Sat/Sun empty.
- `I58 = 5*MIN(24,HOUR(C58-B58)+MINUTE(C58-B58)/60+HOUR(C59-B59)+…+HOUR(C61-B61)+…)` → 50 h (5 × 10 h). Correspondingly I59 → 15, I60 → 15.
- `L58 = SUM(I58:K58)*VLOOKUP($E$54,$I$39:$J$47,2,FALSE)` → 50 (factor "Benutzerdefiniert" = 1). `L61 = SUM(L58:L60)` → 80 h/week.
- `M58 = L58/L$61` → 0.625 (share of stage 1); M59/M60 = 0.1875.
- Stage values: `J64=E18`, `K64=J64*M58` (weighted volume flow), `L64=(I14/C108+I17/E108)` (sum ZUL+ABL power/η), `M64=L64*M58`; analogous rows 65/66; `K67=SUM(K64:K66)` → 8578.57 (=E18, consistency test), `M67=SUM(M64:M66)` → 6.863 (=G6).
- `K68 = IF($I$8=1,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),1),IF($I$8=2,…,3),IF($I$8=3,…,5),FALSE))` → **3900** (Volllaststunden Volumenstrom, SIA 2024)
- `K69 = …(Indexspalte 2/4/6)…` → **3900** (Volllaststunden Elektrizität)
- `K70 = E7*K68/8760` → 3819.23 m³/h (annual-average volume flow)
- `M70 = G6*K69/K68` → 6.863 kW (annual-average fan power)
- `P70 = K70`, `R70 = M70` (for the dV summer logic)

### Rows 71–85 – Operating Hours & Plausibility (SOLL)
Analogous to column F; `K82 = SUM(K79:K81)` → 0, `M82 = SUM(M79:M81)-B114` → 0, `P82`, `R82`. These 0 values make the entire SOLL class block zero on the energy side.

### Rows 86–97 – Temperature Curves
- IST: `C88=IF(M6=0,B88,M6)` → 21 °C (t_ZUL at −15 °C), `C89..C91=IF(L6=0,B89,L6)` → 20 °C (t_ZUL at 22/24/30 °C). Room: D88=22, D89=24, D90=25, D91=25.
- Slopes IST: `I88=IFERROR((C89-C88)/(B89-B88),0)` → −0.0270; `I89=0`, `I90=0`; `J88=0.0541`, `J89=0.5`, `J90=0`.
- SOLL: `C94..C97=22`, `D94=24`, `D95=24`, `D96=26`, `D97=26`; slopes I94..I96, J94..J96.

### Rows 100–108 – Efficiency-Class Lookup (fan power)
- Power ranges: `N10:R10` = "bis 1.1 kW", "1.1-2.2", "2.2-11", "11-110", "ab 110 kW".
- Class values (rows 11–16): IE5: 1/1/1/1/1 ("gefaked"); IE4: 0.872/0.895/0.933/0.963/0.967; IE3: 0.85/0.87/0.9/0.94/0.96; IE2: 0.82/0.84/0.88/0.93/0.95; IE1: 0.73/0.78/0.84/0.91/0.94; Eff3: 0.69/0.74/0.81/0.9/0.93.
- `B102 = IF(E$16<1.1,N11,IF(E$16<2.2,O11,IF(E$16<11,P11,IF(E$16<110,Q11,R11))))`; `C102 = IF(E$17=A102,B102,0)`; `C108 = MAX(C102:C107)` → **1** (IST-ZUL-η); `E108` → **1** (IST-ABL-η); `H108` → **0.85** (SOLL-ZUL-η, IE3); `J108` → **0.85** (SOLL-ABL-η).

### Rows 109–115 – Filter & Shaft/Motor Power
- `B110 = LOOKUP(E14,M28:M44,N28:N44)+LOOKUP(E15,M28:M44,N28:N44)` → 0 Pa (filter-class pressure-drop table M27:O44: target 0/95/105/125/150/160/180/… Pa for classes 0…F9/G1…H14/U15/U16).
- `B112 = B110-B111` → 0; `B113 = K82/3600*B112/(1000*0.75)` → 0 (Pw, shaft power; η_Filter=0.75); `B114 = B113/(0.98*H108)` → 0 (Pm, motor power).
- `F113 = ABS(K70*N20*N23*(E40-E33)/3600)` → **15.956 kW** (Vereisungsschutz heating power = ṁ·cp·ΔT).

### Further Constants ("Grundlagen", Columns M–R, Rows 17–25)
| Cell | Value | Unit | Meaning |
|---|---|---|---|
| N18 | 2 | K | Quellluft: exhaust air warmer than room air (+2 K) |
| N19 | `F:Klimadaten!F44` → **948.226** | mbar | Luftdruck (site altitude) |
| N20 | 1.006 | kJ/kgK | cpl (Wärmekapazität Luft) |
| N21 | 1.86 | kJ/kgK | cpw (Wasserdampf) |
| N22 | 4.19 | kJ/kgK | cw (Wasser) |
| N23 | **1.15** | kg/m³ | Dichte Luft |
| N24 | 2501.6 | kJ/kg | r0 (Verdampfungswärme bei 0 °C) |
| N25 | 2256 | kJ/kg | r100 (Verdampfungswärme bei 100 °C) |
| I29/J29 | 185 | Rp./m³ | Wasserpreis (existing/optimized) |
| I26:I28, J26:J28 | empty | Rp./kWh | Energiepreise Elektrizität/Wärme/Kälte (not filled → costs 0) |

### Label Strings (Column S)
`S10 "Quellluft"`, `S16 "keine"`, `S17 "Adiabatisch Bef."`, `S20 "nein"`, `S21 "ja"`, `S23 "vorhanden"`, `S24 "nicht vorhanden"`.

---

## 3. Column Map of the Temperature-Bin Block (IST, Rows 121–181; SOLL Analogous 189–249)

Formula pattern with class index `n` (n = 121…181 resp. 189…249; t_A = −25…+35 °C in 1-K steps). `$E$…` references are IST inputs, `$F$…` SOLL inputs; in the SOLL block additionally `#REF!` in place of `$N$19` and `$K$82/$P$82/$M$82/$R$82` instead of `$K$70/$P$70/$M$70/$R$70`, as well as target curve `$B$95/$C$95/$I$94` instead of `$B$89/$C$89/$I$88`. State names according to header row 117/119.

**Worked example (row 168, t_A = 22 °C, IST) – complete values in §3.1.**

| Column | Formula (pattern) | Physical quantity | Unit | State point |
|---|---|---|---|---|
| A | `22` (literal) | Aussentemperatur t_A | °C | Aussenluft (AUL) |
| B | `Klimadaten!O{n+30}/8760*$K$68` | Stunden je Klasse (Betriebszeit) | h/a | – |
| C | `Klimadaten!Q{n+30}` | Absolute Feuchte AUL | g/kg | AUL |
| D | `Klimadaten!N{n+30}` | Rel. Feuchte AUL (nur Anzeige, wird nirgends referenziert!) | % | AUL |
| E | `MIN(100%,RelFeuchte(BR{n},C{n},$N$19))` | r.F. der AUL bei Raumtemperatur | % | Raum/AUL |
| F | `IF(H{n}<=0,IF(BU{n}<A{n},1,0),0)` | Sommer-Kühlfall-Flag (KRG-relevant) | 0/1 | – |
| G | `IF(A{n}<=$E$33,(IF($E$32=$I$32,DB{n},IF($E$32=$I$33,DC{n},0))*3600)/($K$70*$N$20*$N$23)+A{n},A{n})` | t_A nach Vereisungsschutz-Vorheizung | °C | AUL nach VS |
| H | `-(A{n}-BJ{n})` | ΔT = t_ZUL-Soll − t_A | K | – |
| I | `$E$28*(BU{n}-A{n})+A{n}` | t nach WRG (feste Effektivität, ohne Regulierung) | °C | AUL nWRG |
| J | `IF(F{n}=0,MIN(I{n},BJ{n}),I{n})` | t nach WRG, begrenzt auf t_ZUL-Soll | °C | AUL nWRG |
| K | `IF($E$30=$S$20,$E$28,MAX(IF(AND($E$31=$S$20,F{n}=1),0,IF(A{n}=BU{n},0,(J{n}-A{n})/(BU{n}-A{n}))),0))` | **regulierter WRG-Wirkungsgrad** ε = (t_ist−t_A)/(t_ABL−t_A) | – | WRG |
| L | `IF($E$30=$S$21,K{n}*(BU{n}-A{n})+A{n},I{n})` | t nach WRG mit Bypass-Regulierung | °C | AUL nWRG |
| M | `IF($E$28=0,C{n},(K{n}/$E$28*$E$29)*(BW{n}-C{n})+C{n})` | x nach WRG (Feuchte-WRG skaliert mit ε) | g/kg | AUL nWRG |
| N | `EnthalpieA(L{n},M{n},$N$19)*$E$35+(1-$E$35)*EnthalpieA(BU{n},BW{n},$N$19)` | **MIL-Enthalpie (enthalpiegeregelt), max. Frischluftanteil** | kJ/kg | MIL |
| O | `EnthalpieA(L{n},M{n},$N$19)*$E$34+(1-$E$34)*EnthalpieA(BU{n},BW{n},$N$19)` | MIL-Enthalpie, min. Frischluftanteil | kJ/kg | MIL |
| P | `1-IF(EnthalpieA(L{n},M{n},$N$19)=S{n},$E$35,(S{n}-EnthalpieA(BU{n},BW{n},$N$19))/((EnthalpieA(L{n},M{n},$N$19)-EnthalpieA(BU{n},BW{n},$N$19))))` | Umluft-Anteil (Enthalpieziel S) | – | MIL |
| Q | `L{n}*(1-P{n})+BU{n}*P{n}` | t MIL (enthalpiegeregelt) | °C | MIL |
| R | `(M{n}*(1-P{n})+BW{n}*P{n})` | x MIL (enthalpiegeregelt) | g/kg | MIL |
| S | `MIN(MAX(N{n},BM{n}),O{n})` | MIL-Enthalpie, begrenzt auf [h_ZUL-Soll, h_max] | kJ/kg | MIL |
| T | `MIN((L{n}*($E$35)+BU{n}*(1-$E$35)))` | t MIL (temp.geregelt, max. Frischluft; MIN() ist No-op) | °C | MIL |
| U | `(L{n}*($E$34)+BU{n}*(1-$E$34))` | t MIL (temp.geregelt, min. Frischluft) | °C | MIL |
| V | `1-IF(L{n}=W{n},$E$35,(W{n}-BU{n})/(L{n}-BU{n}))` | Umluft-Anteil (Temp-Ziel W) | – | MIL |
| W | `MIN(MAX(T{n},BJ{n}),U{n})` | t MIL (temp.geregelt), begrenzt auf t_ZUL-Soll | °C | MIL |
| X | `(M{n}*(1-$V{n})+BW{n}*$V{n})` | x MIL (temp.geregelt) | g/kg | MIL |
| Y | `EnthalpieA(W{n},X{n},$N$19)` | MIL-Enthalpie (temp.geregelt) | kJ/kg | MIL |
| Z | `AVERAGE($E$45:$F$46)` → 9 | **Taupunkt Kälteregister (A):** mean chilled-water temperature (VL/RL) | °C | Kälteregister (A) |
| AA | `IF($E$36=$D$36,MIN(AbsFeuchte(Z{n},100%,$N$19),R{n}),MIN(AbsFeuchte(Z{n},100%,$N$19),X{n}))` | Sättigungsfeuchte am Register, begrenzt auf MIL-x | g/kg | Kälteregister (A) |
| AB | `EnthalpieA(Z{n},AA{n},$N$19)` | Enthalpie am Registeraustritt (A) | kJ/kg | (A) |
| AC | `AVERAGE($E$45:$E$46)` → 9 | Register-Temperatur für lineare Kühlkurve | °C | Kälteregister (C) |
| AD | `n-122` (literal, −1 … 59) | Scratch/Parameter-Spalte (nur für AE, sonst ungenutzt) | g/kg | – |
| AE | `EnthalpieA(AC{n},AD{n},$N$19)` | Enthalpie auf Hilfskurve (nicht weiter referenziert) | kJ/kg | – |
| AF | `AVERAGE($E$45:$E$46)` → 9 | Offset a der linearen Kühlkurve | °C | (C) |
| AG | `IF($E$36=$D$36,IF(AA{n}=R{n},1E+23,(Q{n}-AF{n})/(R{n}-AA{n})),IF(AA{n}=X{n},1E+23,(W{n}-AF{n})/(X{n}-AA{n})))` | Steigung b der linearen Kühlkurve (dt/dx) | °C/(g/kg) | (C) |
| AH | `IF($E$36=$D$36,MAX(IF(R{n}>BL{n},AF{n}+(AG{n}*(BL{n}-AA{n})),Q{n}),Z{n}),MAX(IF(X{n}>BL{n},AF{n}+(AG{n}*(BL{n}-AA{n})),W{n}),Z{n}))` | **t nach Kühlregister D1** (lineare Kühlkurve bis x_ZUL-Soll) | °C | D1 |
| AI | `IF(AH{n}=Z{n},AA{n},BL{n})` | x nach D1 | g/kg | D1 |
| AJ | `EnthalpieA(AH{n},AI{n},$N$19)` | h nach D1 | kJ/kg | D1 |
| AK | `IF($E$36=$D$36,MAX(MIN(Q{n},BJ{n}),Z{n}),MAX(MIN(W{n},BJ{n}),Z{n}))` | **t nach Kühlregister D2** (MIL begrenzt auf t_ZUL-Soll, min. Registertemp.) | °C | D2 |
| AL | `IF(Z{n}=AK{n},AA{n},(BJ{n}-AF{n})/AG{n}+AA{n})` | x nach D2 (entlang linearer Kühlkurve) | g/kg | D2 |
| AM | `EnthalpieA(AK{n},AL{n},$N$19)` | h nach D2 | kJ/kg | D2 |
| AN | `TemperaturH(AP{n},AO{n})` | t für "Erwärmung vor Befeuchtung" (E): Temperatur bei Zielenthalpie und MIL-x | °C | (E) |
| AO | `IF($E$36=$D$36,R{n},X{n})` | x für Punkt E (= MIL-x) | g/kg | (E) |
| AP | `BM{n}` | Zielenthalpie für Punkt E (= h_ZUL-Soll) | kJ/kg | (E) |
| AQ | `TaupunktA(AR{n},$N$19)` → **#NAME?** | Taupunkttemperatur ZUL bei Entfeuchtung (F) – UDF broken/commented out | °C | (F) |
| AR | `BL{n}` | x_ZUL-Soll (input for F) | g/kg | (F) |
| AS | `EnthalpieA(AQ{n},AR{n},$N$19)` → **#VALUE!** | h at F (error propagated) | kJ/kg | (F) |
| AT | `BN{n}` | t für "Erwärmung ohne Befeuchtung" (G) = t_ZUL-IST | °C | (G) |
| AU | `IF($E$36=$D$36,R{n},X{n})` | x für G (= MIL-x) | g/kg | (G) |
| AV | `EnthalpieA(AT{n},AU{n},$N$19)` | h bei G | kJ/kg | (G) |
| AW | `IF($E$36=$C$36,IF(AND(ROUND(BM{n},4)>=ROUND(S{n},4),ROUND(BL{n},4)>=ROUND(R{n},4),ROUND(BJ{n},4)>=ROUND(Q{n},4)),1,IF(ROUND(BL{n},4)<ROUND(AA{n},4),2,IF(ROUND(BJ{n},4)>=ROUND(AH{n},4),3,4))),IF(AND(ROUND(BM{n},4)>=ROUND(Y{n},4),ROUND(BL{n},4)>=ROUND(X{n},4),ROUND(BJ{n},4)>=ROUND(W{n},4)),1,IF(ROUND(BL{n},4)<ROUND(AA{n},4),2,IF(ROUND(BJ{n},4)>=ROUND(AH{n},4),3,4))))` | **Fall-Unterscheidung 1–4** (see §5.4) | 1–4 | – |
| AX | `IF($E$39=$S$21,1,0)` | Flag Heizregister vorhanden | 0/1 | – |
| AY | `IF($E$49=$S$16,0,1)` | Flag Befeuchtung vorhanden | 0/1 | – |
| AZ | `IF($E$42=$S$21,1,0)` | Flag Kühlung vorhanden | 0/1 | – |
| BA | `IF(AND($E$47=$S$21,AZ{n}=1),1,0)` | Flag Entfeuchtung vorhanden (Kühlung + Entfeuchtung installiert) | 0/1 | – |
| BB | `IF($E$36=$D$36,IF(AW{n}=1,Fall1Tzul(AX{n},AY{n},BJ{n},Q{n}),0),IF(AW{n}=1,Fall1Tzul(AX{n},AY{n},BJ{n},W{n}),0))` | t_ZUL Fall 1 (VBA-UDF Fall1Tzul) | °C | Zuluft Fall 1 |
| BC | `…Fall1xzul(AX,AY,BL,R)…` | x_ZUL Fall 1 | g/kg | Zuluft Fall 1 |
| BD | `…Fall2Tzul(AX,AZ,BJ,Q,Z)…` | t_ZUL Fall 2 | °C | Zuluft Fall 2 |
| BE | `…Fall2xzul(AX,AZ,BL,R,AA)…` | x_ZUL Fall 2 | g/kg | Zuluft Fall 2 |
| BF | `IF($E$36=$D$36,IF(AW{n}=3,IF(AND(BA{n}=1,AX{n}=1),BJ{n},IF(AZ{n}=1,MIN(BJ{n},IF(AX{n}=1,BJ{n},Q{n})),IF(AND(AX{n}=1,BJ{n}>Q{n}),BJ{n},Q{n}))),0),…)` | t_ZUL Fall 3 | °C | Zuluft Fall 3 |
| BG | `…IF(AW=3,IF(AND(BA,AX),BL,IF(AZ,MIN(AL,R),R))…)` | x_ZUL Fall 3 | g/kg | Zuluft Fall 3 |
| BH | `IF($E$36=$D$36,IF(AW{n}=4,IF(AZ{n}=1,BJ{n},Q{n}),0),…)` | t_ZUL Fall 4 | °C | Zuluft Fall 4 |
| BI | `IF($E$36=$D$36,IF(AND(AW{n}=4,AY{n}=0),IF(AZ{n}=1,AI{n},R{n}),IF(AND(AW{n}=4,AY{n}=1),BL{n},0)),…)` | x_ZUL Fall 4 | g/kg | Zuluft Fall 4 |
| BJ | `IF($DA{n}<=$B$89,$C$89-($B$89-$DA{n})*$I$88,IF($DA{n}<=$B$90,$C$90-($B$90-$DA{n})*$I$89,$C$91-($B$91-$DA{n})*$I$90))` | **t_ZUL-Soll** (piecewise linear temperature curve) | °C | Zuluft soll |
| BK | `MIN(1,RelFeuchte(BJ{n},BT{n},$N$19))` | rF_ZUL-Soll | % | Zuluft soll |
| BL | `AbsFeuchte(BJ{n},BK{n},$N$19)` | **x_ZUL-Soll** | g/kg | Zuluft soll |
| BM | `EnthalpieA(BJ{n},BL{n},$N$19)` | **h_ZUL-Soll** | kJ/kg | Zuluft soll |
| BN | `BB{n}+BD{n}+BF{n}+BH{n}` | **t_ZUL-IST** (sum of the case contributions) | °C | Zuluft ist |
| BO | `MIN(1,RelFeuchte(BN{n},BP{n},$N$19))` | rF_ZUL-IST | % | Zuluft ist |
| BP | `BC{n}+BE{n}+BG{n}+BI{n}` | **x_ZUL-IST** | g/kg | Zuluft ist |
| BQ | `EnthalpieA(BN{n},BP{n},$N$19)` | **h_ZUL-IST** | kJ/kg | Zuluft ist |
| BR | `IF($DA{n}<=$B$89,$D$89-($B$89-$DA{n})*$J$88,IF($DA{n}<=$B$90,$D$90-($B$90-$DA{n})*$J$89,$D$91-($B$91-$DA{n})*$J$90))` | **t_Raum** (aus Raumkurve) | °C | Raum |
| BS | `IF(E{n}<$E$50,$E$50,IF(E{n}>$E$48,$E$48,E{n}))` | rF_Raum, begrenzt auf [min,max]-Sollband | % | Raum |
| BT | `AbsFeuchte(BR{n},BS{n},$N$19)` | x_Raum | g/kg | Raum |
| BU | `IF($I$21=0,IF(E$13=$S$10,BR{n}+$N$18,BR{n}),IF(E$13=$S$10,BR{n}+$N$18+#REF!,BR{n}+$I$21))` | **t_Abluft** (= t_Raum, bei Quellluft +2 K; + Feuchtelast-Zuschlag I21) | °C | Abluft |
| BV | `RelFeuchte(BU{n},BW{n},$N$19)` | rF_Abluft | % | Abluft |
| BW | `BT{n}+$I$20` | **x_Abluft** (= x_Raum + Feuchtelast) | g/kg | Abluft |
| BX | `SUM(BZ{n}:CA{n})` | Kühl-Enthalpiedifferenz total | kJ/kg | – |
| BY | `SUM(CB{n}:CD{n})` | Heiz-Enthalpiedifferenz total | kJ/kg | – |
| BZ | `IF($E$36=$C$36,MAX(IF(AZ{n}=1,IF(OR(AW{n}=3,AW{n}=4,AW{n}=2),S{n}-AM{n},0),0),0),MAX(IF(AZ{n}=1,IF(OR(AW{n}=3,AW{n}=4,AW{n}=2),Y{n}-AM{n},0),0),0))` | **Kühlung** (MIL→D2), Fälle 2/3/4 | kJ/kg | Kühlen |
| CA | `IF($E$36=$D$36,MAX(IF(BA{n}=1,IF(AW{n}=3,AM{n}-AJ{n},IF(AW{n}=2,(IF(BP{n}=R{n},0,S{n}-AB{n}-BZ{n})),0)),0),0),…)` | **Entfeuchtung-Kühlung** (D2→D1 bzw. Rest bis AB) | kJ/kg | Kühlen Entf. |
| CB | `IF($E$36=$D$36,MAX(IF(AND(BA{n}=1,AX{n}=1),IF(AW{n}=3,BQ{n}-AJ{n},IF(AW{n}=2,IF(R{n}=BP{n},0,BQ{n}-AB{n}),0)),0),0),…)` | **Entfeuchtung-Erwärmung** (Nachheizen) | kJ/kg | Heizen Entf. |
| CC | `IF(F{n}=1,0,IF($E$36=$D$36,IF(AX{n}=1,IF(AW{n}=1,AV{n}-S{n},0),0),IF(AX{n}=1,IF(AW{n}=1,AV{n}-Y{n},0),0)))` | **Heizen** (MIL→G), Fall 1 | kJ/kg | Heizen |
| CD | `IF(AND(AY{n}=1,B{n}>0),IF(OR(AW{n}=1,AW{n}=4),BQ{n}-AV{n},0),0)` | **Befeuchtung-Erwärmung** (G→ZUL-IST), Fälle 1/4 | kJ/kg | Heizen Bef. |
| CE | `IF($E$42=$S$21,IF(OR(AND(A{n}>=$E$26,$E$27>0),AND(A{n}>=$E$26,$E$27<0)),$P$70*B{n}*$N$23*(CA{n})/3.6/1000000,$K$70*B{n}*$N$23*(CA{n})/3.6/1000000),0)` | **Entfeuchtung-Kühlenergie** je Klasse | MWh | – |
| CF | analogous to CB | **Entfeuchtung-Heizenergie** | MWh | – |
| CG | `IF(OR(AND(A{n}>=$E$26,$E$27>0),AND(A{n}>=$E$26,$E$27<0)),$P$70*B{n}*$N$23*(CD{n})/3.6/1000000,$K$70*B{n}*$N$23*(CD{n})/3.6/1000000)` | **Befeuchtung-Heizenergie** (adiabatisch) | MWh | – |
| CH | `IF($E$36=$D$36,IF(OR(…),MAX(0,(BP{n}-R{n})*B{n}*$P$70*$N$23/1000),MAX(0,(BP{n}-R{n})*B{n}*$K$70*$N$23/1000)),IF(OR(…),MAX(0,(BP{n}-X{n})*B{n}*$P$70*$N$23/1000),MAX(0,(BP{n}-X{n})*B{n}*$K$70*$N$23/1000)))` | **Befeuchtungswasser** | Liter | – |
| CI | `(CH{n}*$N$22*(100-$E$51)+$N$25*CH{n})/3600000` | **Dampfbefeuchter-Energie** (Wasser von E51 auf 100 °C + Verdampfung) | MWh | – |
| CJ | `IF($E$42=$S$21,IF(OR(…),$P$70*B{n}*$N$23*(BZ{n})/3.6/1000000,$K$70*B{n}*$N$23*(BZ{n})/3.6/1000000),0)` | **Kühlenergie** (Luftkühlung) | MWh | – |
| CK | analogous to CC | **Heizenergie** (Lufterwärmung) | MWh | – |
| CL | `IF($E$36=$D$36,IF(OR(…),MAX(0,-(BP{n}-R{n})*B{n}*$P$70*$N$23/1000),MAX(0,-(BP{n}-R{n})*B{n}*$K$70*$N$23/1000)),IF(OR(…),MAX(0,-(BP{n}-X{n})*B{n}*$P$70*$N$23/1000),MAX(0,-(BP{n}-X{n})*B{n}*$K$70*$N$23/1000)))` | **Entfeuchtungswasser** (Kondensat) | Liter | – |
| CM | `IF($E$49=$S$16,0,IF($E$49=$S$17,CG{n},CI{n}))` | **Befeuchtungs-Energie final** (adiabatisch → CG, otherwise → CI) | MWh | – |
| CN | `IF(E{n}>0,BK{n},222)` | rF_ZUL-Soll (Diagramm-Guard 222) | % | Anzeige |
| CO | `IF(E{n}>0,BO{n},222)` | rF_ZUL-IST | % | Anzeige |
| CP | `IF($E$36=$D$36,IF(B{n}>0,Q{n},222),IF(B{n}>0,W{n},222))` | t MIL min | °C | Anzeige |
| CQ | `IF($E$36=$D$36,IF(B{n}>0,Q{n},-222),IF(B{n}>0,W{n},-222))` | t MIL max | °C | Anzeige |
| CR | `IF(B{n}>0,BY{n},-222)` | Heiz-Enthalpie (Anzeige) | kJ/kg | Auslegung |
| CS | `IF(B{n}>0,BX{n},-222)` | Kühl-Enthalpie (Anzeige) | kJ/kg | Auslegung |
| CT | `IF(OR(AND(A{n}>=$E$26,$E$27>0),AND(A{n}>=$E$26,$E$27<0)),B{n}*($R$70/1000),B{n}*($M$70)/1000)` | **Ventilator-Energie** | MWh | – |
| CU | `IF(B{n}>0,BJ{n},222)` | t_ZUL-Soll (Diagramm) | °C | Anzeige |
| CV | `IF(B{n}>0,BJ{n},-222)` | t_ZUL-Soll (Diagramm) | °C | Anzeige |
| CW | `SUM(CK{n},CJ{n},CE{n},CF{n},CM{n},CT{n})` | Gesamt-Energie je Klasse | MWh | Diagramm |
| CX | `-CL{n}` | Entfeuchtungswasser (positive) | Liter | Diagramm |
| CY | `IF(I{n}=0,CY{n+1},BJ{n})` | t_ZUL-Soll "letzter gültiger Wert" | °C | Diagramm |
| CZ | `IF(I{n}=0,CZ{n+1},BN{n})` | t_ZUL-IST "letzter gültiger Wert" | °C | Diagramm |
| DA | `n-146` (literal, −25…35) | Aussentemperatur (Duplikat von A, Lookup-Schlüssel) | °C | – |
| DB | `IF(A{n}<=$E$33,$F$113,0)` | VS-Leistung "ein/aus" | kW | Vereisungsschutz |
| DC | `IF(A{n}<=$E$33,ABS($K$70*$N$20*$N$23*MIN(ABS(A{n}-$E$33),ABS($E$40-$E$33))/3600),0)` | VS-Leistung "variabel" | kW | Vereisungsschutz |

**Klimadaten assignment:** class t_A = k °C → Klimadaten row `k+30` (t_A = −25 → row 5; 22 → row 52; 35 → row 65). Columns: **O** = hours/a, **Q** = absolute humidity (g/kg), **N** = relative humidity (%), **F44** = Luftdruck (mbar, for N19).

### 3.1 Complete Worked Example: Row 168 (t_A = 22 °C)
| Cell | Value | Cell | Value |
|---|---|---|---|
| A168 | 22 | AM168 | 44.6561 kJ/kg |
| B168 | 59.6575 h | AN168 | 20 °C |
| C168 | 10.0367 g/kg | AO168 | 10.0367 g/kg |
| E168 | 0.5049 (=50.5 %) | AP168 | 45.6012 kJ/kg |
| F168 | 0 | AQ168 | #NAME? |
| G168 | 22 | AR168 | 10.0367 g/kg |
| H168 | −2 K | AS168 | #VALUE! |
| I168 | 23.6 °C | AT168 | 20 °C |
| J168 | 20 °C | AU168 | 10.0367 g/kg |
| K168 | 0 (Bypass) | AV168 | 45.6012 kJ/kg |
| L168 | 22 °C | AW168 | **4** (cooling & humidifying) |
| M168 | 10.0367 g/kg | AX168 | 1 |
| N168 | 47.6506 kJ/kg | AY168 | 1 |
| O168 | 47.6506 kJ/kg | AZ168 | 1 |
| P168 | 0 | BA168 | 1 |
| Q168 | 22 °C | BB168 | 0 |
| R168 | 10.0367 g/kg | BC168 | 0 |
| S168 | 47.6506 kJ/kg | BD168 | 0 |
| T168 | 22 °C | BE168 | 0 |
| U168 | 22 °C | BF168 | 0 |
| V168 | 0 | BG168 | 0 |
| W168 | 22 °C | BH168 | 20 °C |
| X168 | 10.0367 g/kg | BI168 | 10.0367 g/kg |
| Y168 | 47.6506 kJ/kg | BJ168 | 20 °C |
| Z168 | 9 °C | BK168 | 0.6444 (64.4 %) |
| AA168 | 7.6169 g/kg | BL168 | 10.0367 g/kg |
| AB168 | 28.2360 kJ/kg | BM168 | 45.6012 kJ/kg |
| AC168 | 9 °C | BN168 | 20 °C |
| AD168 | 46 (Scratch) | BO168 | 0.6444 |
| AE168 | 124.8976 kJ/kg | BP168 | 10.0367 g/kg |
| AF168 | 9 °C | BQ168 | 45.6012 kJ/kg |
| AG168 | 5.3724 °C/(g/kg) | BR168 | 24 °C |
| AH168 | 22 °C | BS168 | 0.5049 |
| AI168 | 10.0367 g/kg | BT168 | 10.0367 g/kg |
| AJ168 | 47.6506 kJ/kg | BU168 | 24 °C |
| AK168 | 20 °C | BV168 | 0.5049 |
| AL168 | 9.6644 g/kg | BW168 | 10.0367 g/kg |
| BX168 | 2.9945 kJ/kg | CJ168 | 0.21795 MWh |
| BY168 | 7.1e-15 kJ/kg | CK168 | 0 MWh |
| BZ168 | 2.9945 kJ/kg | CM168 | 5.17e-16 MWh |
| CA168 | 0 | CN168 | 0.6444 |
| CB168 | 0 | CP168 | 22 °C |
| CC168 | 0 | CT168 | 0.40942 MWh |
| CD168 | 7.1e-15 kJ/kg | CU168 | 20 °C |
| CE168 | 0 MWh | CW168 | 0.62737 MWh |
| CF168 | 0 MWh | CY168 | 20 °C |
| CG168 | 5.17e-16 MWh | CZ168 | 20 °C |
| CH168 | 4.65e-13 Liter | DA168 | 22 °C |
| CI168 | 3.40e-16 MWh | DB168 | 0 |
| | | DC168 | 0 |

Verification: `CT168 = B168*M70/1000 = 59.6575×6.8629/1000 = 0.4094` ✓;
`CJ168 = K70×B168×N23×BZ168/3.6e6 = 3819.23×59.6575×1.15×2.9945/3.6e6 = 0.2179` ✓.

---

## 4. Driving Data (Klimadaten Link) and Hour Scaling

- Class n (t_A = k °C): `B{n} = Klimadaten!O{k+30}/8760*$K$68` – annual hours of the class, scaled to the full-load hours of the system (K68). Σ B over all classes = K68 = 3900 h.
- `C{n} = Klimadaten!Q{k+30}` (x_AUL g/kg), `D{n} = Klimadaten!N{k+30}` (rF_AUL %, display only), `N19 = Klimadaten!F44` (Luftdruck mbar).
- Energy per class = **B × ṁ × Δh** with ṁ = K70 × N23 (m³/h × kg/m³ = kg/h) and conversion `…/3.6/1000000` (kJ → MWh; 1 MWh = 3.6e6 kJ). Example CE/CJ/CF/CK/CG:
  `K70*B168*N23*(BZ168)/3.6/1000000` → MWh.
- Fan: `CT{n} = B{n}*M70/1000` (h × kW / 1000 → MWh).
- Water: `CH{n} = (BP{n}-R{n})*B{n}*K70*N23/1000` (g/kg × h × kg/h / 1000 → liters); `CL{n}` analogous with negative sign (Kondensat).
- The dV summer logic selects between summer and annual-average volume flow via `IF(OR(AND(A>=$E$26,$E$27>0),AND(A>=$E$26,$E$27<0)),$P$70,$K$70)`; since E27 = 0 and P70 = K70, it is ineffective here.

---

## 5. Physics of the Model

### 5.1 Fan Power (Gebläsegesetz with Exponent 2.5)
ZUL-Stufenleistungen (row n = 14,15,16; analogous ABL 17,18,19 with E21/E23:E25):
```
I14 = IF(E18<MAX(E19:E20),IF(ISERROR(E16*(E18^2.5)/(E19^2.5)),0,E16*(E18^2.5)/(MAX(E18:E20)^2.5)),E16)
I15 = IF(E19<MAX(E18,E20),IF(ISERROR(E16*(E19^2.5)/(E20^2.5)),0,E16*(E19^2.5)/(MAX(E18:E20)^2.5)),E16)
I16 = IF(E20<MAX(E18:E19),IF(ISERROR(E16*(E20^2.5)/(E20^2.5)),0,E16*(E20^2.5)/(MAX(E18:E20)^2.5)),E16)
```
- Nennleistung E16 = G6/2 (half of total power for ZUL; ABL E21 = E16).
- Stufen-Volumenströme: stage 1 = E7 (100 %), stage 2 = 67 %, stage 3 = 33 % (only for "stufenlos"; "einstufig" → all stages = 100 %).
- **P_Stufe = P_Nenn × (V_Stufe/V_max)^2.5** (Affinitätsgesetz with exponent 2.5 instead of 3 – compromise for motor efficiency; ISERROR guard against V=0).
- Sum with motor efficiency: `L64 = (I14/C108 + I17/E108)` etc. (C108/E108 = η from efficiency-class lookup). Annual fan electricity: `CT182 = Σ CT122:CT181`, `C259 = CT182*1000` kWh, `H7 = C259/1000` MWh.

### 5.2 WRG (Heat Recovery)
- Fixed efficiency `$E$28` (0.8). State after WRG: `I{n} = E28*(BU-A)+A` (temperature) and `M{n} = C + (K/E28*E29)*(BW-C)` (humidity; E29 = 0 → no Feuchte-WRG).
- **Regulated efficiency** (bypass): `K{n} = MAX((J{n}-A{n})/(BU{n}-A{n}),0)` with `J{n} = MIN(I{n},BJ{n})` – ε is reduced so that t after WRG does not exceed the Zuluft-Solltemperatur (summer → ε = 0, full bypass). Special case: KRG present (E31="ja") and summer flag F=1 → 0. If no bypass (E30="nein"): K = E28 fixed.
- t after WRG with bypass: `L{n} = K{n}*(BU-A)+A` (if E30="ja"), otherwise `I{n}`.

### 5.3 Mixed Air (Recirculation Damper)
- MIL enthalpy (enthalpy control): `N{n} = h(L,M)*E35 + (1-E35)*h(BU,BW)`; `O{n}` analogous with E34. With E34=E35=1 → MIL = pure outside air after WRG.
- **Umluft-Anteil** (Enthalpieziel S): `P{n} = 1 - (S - h(BU,BW))/(h(L,M) - h(BU,BW))`; `Q{n} = L*(1-P)+BU*P`, `R{n} = M*(1-P)+BW*P`.
- Limitation: `S{n} = MIN(MAX(N,BM),O)` – MIL enthalpy not below h_ZUL-Soll.
- Temperature control analogous via T/U/V/W/X/Y (V share, W limited to t_ZUL-Soll BJ).
- Exhaust-air state = room state: `BU = BR` (t_Raum from room curve; Quellluft +2 K), `BW = BT + I20` (x_Raum + Feuchtelast), with rF_Raum `BS` limited to [E50, E48] (humidity target band; here [0, 1] = unlimited).

### 5.4 Cooling Coil (Entfeuchtung), Linear Cooling Curve, Cases 1–4
- Coil state (A): `Z = AVERAGE(E45:F46)` = 9 °C (mean chilled-water temperature), `AA = MIN(x_sat(9°C,100%), MIL-x)` (saturation humidity, limited to MIL), `AB = h(9,AA)`.
- Linear cooling curve through (AF=9 °C, AA) and MIL (Q,R resp. W,X): slope `AG = (t_MIL - 9)/(x_MIL - AA)`; target temperature `AH = MAX(AF+AG*(x_ZUL-Soll - AA), 9)` (D1: cooling until x_ZUL-Soll is reached).
- D2: `AK = MAX(MIN(t_MIL, t_ZUL-Soll), 9)`, `AL = (t_ZUL-Soll - 9)/AG + AA` (state after cooling coil at target temperature), `AM = h(AK,AL)`.
- **Case detector** `AW` (with ROUND(…,4) comparisons against rounding errors):
  - Case 1 (heating & humidifying): h_ZUL-Soll ≥ h_MIL, x_ZUL-Soll ≥ x_MIL, t_ZUL-Soll ≥ t_MIL.
  - Case 2 (dehumidifying & heating): x_ZUL-Soll < x_Register (must be dehumidified).
  - Case 3 (cooling & possibly dehumidify-heating): t_ZUL-Soll ≥ t_D1 (only cooling, no reheat needed).
  - Case 4 (cooling & humidifying): otherwise (too dry after cooling → humidify).
- ZUL-IST from the UDFs `Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul` (BB–BE) resp. inline IFs (BF–BI): `BN = BB+BD+BF+BH`, `BP = BC+BE+BG+BI`.
- **Enthalpy differences (kJ/kg):**
  - `BZ` (cooling) = S − AM resp. Y − AM (MIL → D2), cases 2/3/4.
  - `CA` (dehum./cooling) = AM − AJ (D2→D1, case 3) resp. S − AB − BZ (case 2: remainder after dehumidification).
  - `CB` (dehum./heating) = BQ − AJ (case 3) resp. BQ − AB (case 2) – reheat to t_ZUL.
  - `CC` (heating) = AV − S (case 1: MIL → G), if F=1 (summer) = 0.
  - `CD` (heating hum.) = BQ − AV (cases 1/4: G → ZUL-IST, adiabatic humidification).
  - `BX = BZ+CA`, `BY = CB+CC+CD`.

### 5.5 Energies (MWh per Class) and Water
- Cooling: `CJ = K70·B·N23·BZ/3.6e6`; dehum.-cooling: `CE = …·CA/3.6e6`; heating: `CK = …·CC/3.6e6`; dehum.-heating: `CF = …·CB/3.6e6`; hum.-heating (adiabatic): `CG = …·CD/3.6e6`.
- Steam humidification: `CI = (CH·N22·(100−E51) + N25·CH)/3.6e6` (heat water from E51=10 °C to 100 °C + evaporate with r100=2256).
- Final humidification energy: `CM = CG` (adiabatic, E49=S17) resp. `CI` (otherwise).
- Humidification water: `CH = MAX(0,(x_ZUL-IST − x_MIL)·B·K70·N23/1000)` liters; condensate `CL = −MAX(0,(x_MIL − x_ZUL-IST)·…)` liters, `CX = −CL`.
- Fan: `CT = B·M70/1000` MWh.
- Total per class: `CW = CK+CJ+CE+CF+CM+CT`.

### 5.6 IST vs. SOLL Control Logic
- The comparison `$E$36=$D$36` ("Temperatur" vs. empty) switches between enthalpy-controlled (branch 2, active) and temperature-controlled mixed-air calculation. Since D36 is empty, branch 2 is always active (X-based).
- `$E$36=$C$36` in the case detector AW selects S-based (active) vs. Y-based comparisons.
- The SOLL block (189–249) mirrors the same logic with `$F$` inputs and the target temperature curve, but is inactive in this file (B/C/D = 0, #REF!, K82… = 0).

### 5.7 Summation into the Result Rows
```
CJ182 = SUM(CJ122:CJ181)          CK182 = SUM(CK122:CK181)
CE182 = SUM(CE122:CE181)          CF182 = SUM(CF122:CF181)
CM182 = SUM(CM122:CM181)          CT182 = SUM(CT122:CT181)
CH182 = SUM(CH122:CH181)          CL182 = SUM(CL122:CL181)
BZ183 = MAX(BZ$121:BZ$181)*$E$18*$N$23/3600    (kW, Leistungsmax.)
CA183 = MAX(CA$121:CA$181)*$E$18*$N$23/3600
CB183 = MAX(CB$121:CB$181)*$E$18*$N$23/3600
CC183 = MAX(CC$133:CC$181)*$E$18*$N$23/3600    (Achtung: ab Zeile 133!)
CD183 = MAX(CD$121:CD$181)*$E$18*$N$23/3600
```
and then: `C254 = CJ182*1000` (kWh), `D254 = BZ183` (kW), …, `C259 = CT182*1000`, `D259 = G6`; row 7: `Q7 = C254/1000` (MWh), `P7 = D254`, … `H7 = C259/1000` (MWh). SOLL analogous via row 250 (all 0).

---

## 6. Result Rows (254–328)

| Cell | Formula | Result | Meaning |
|---|---|---|---|
| A254 | Luftkühlung | – | Section title |
| C254 | `IFERROR(CJ182*1000,0)` | 1750.16 kWh | **Annual cooling energy** (useful energy) |
| D254 | `BZ183` | 25.78 kW | Cooling power (max.) |
| E254 | `IFERROR(CJ250*1000,0)` | 0 | SOLL cooling energy |
| F254 | `IFERROR(E254*J28/100,0)` | 0 | Cooling costs CHF/a (price J28 empty) |
| A255 | Lufterwärmung | – | |
| C255 | `IFERROR(CK182*1000,0)` | 3786.30 kWh | **Annual heating energy** |
| D255 | `CC183` | 16.15 kW | Heating power (max.) |
| E255/F255 | analogous (CK250 / J27) | 0 | SOLL/costs |
| A256 | Erwärmung Bef. | – | |
| C256 | `IFERROR(CM182*1000,0)` | −3.25e-12 kWh | **Annual humidification heating energy** (≈0) |
| D256 | `CD183` | 3.9e-14 kW | Power (≈0) |
| A257 | Entfeuchtung (Kühlung Entf.) | | |
| C257 | `IFERROR(CE182*1000,0)` | 0 | **Annual dehumidification cooling energy** |
| D257 | `CA183` | 0 | Power |
| B258 | Erwärmung Entf. | | |
| C258 | `IFERROR(CF182*1000,0)` | 0 | **Annual dehumidification heating energy** |
| D258 | `CB183` | 0 | Power |
| A259 | Luftumwälzung / Ventilator | | |
| C259 | `IFERROR(CT182*1000,0)` | 26765.14 kWh | **Annual fan electricity** |
| D259 | `G6` | 6.863 kW | Fan power |
| E259/F259 | analogous (CT250 / J26) | 0 | SOLL/costs |
| A260 | Total | | |
| C260 | `SUM(C254:C259)` | 32301.60 kWh | Total useful energy |
| D260 | `SUM(D254:D259)` | 48.80 kW | Total power |
| E260/F260 | Sums | 0 | |
| A262 | Wasser Bef. | | |
| C262 | `IFERROR(CH182,0)` | ~1e-11 liters/a | Befeuchtungswasser |
| D262 | `IFERROR(C262/1000*I29/100,0)` | ~0 | Water costs (185 Rp./m³) |
| A263 | Entfeuchtung | | |
| C263 | `IFERROR(CL182,0)` | ~9e-12 liters/a | Kondensat |
| H253 | `LOOKUP(B88,$DA$122:$DA$181,$BU$122:$BU$181)` | 22 °C | t_Abluft at t_A=−15 (chart) |
| I253 | `LOOKUP(B88,$DA$122:$DA$181,$BS$122:$BS$181)` | 0 | rF_Raum at −15 °C |
| J253 | `AbsFeuchte(D88,I253,$N$19)` | 0.196 g/kg | x_Raum at −15 °C |
| H254:J262 | LOOKUPs against DA/BU resp. DA/BS (SOLL curves 190:249 from H259) | – | Chart support points |
| A264–A265 | "Daten für HG/KG" / "Tab" | – | Section title |
| H265:N265 | `Begriffe!F152:F158` | Aussentemperatur, Luftförderung, Lufterwärmung, Erwärmung Befeuchtung, Luftkühlung, Kühlung Entfeuchtung, Erwärmung Entfeuchtung | Chart legend |
| **267–327** (per class k = −25…35) | | | |
| B | `IFERROR((CK{k+30}+CF{k+30})*1000/Klimadaten!O{k+30},0)` | 0 | Heating power IST kW (energy/hours – divided by Klimadaten hours, not B!) |
| C | analogous to CK189+CF189 | 0 | Heating power SOLL |
| D | `IFERROR((CE+CJ)*1000/O,0)` | 0 | Cooling power IST |
| E | analogous (CE189+CJ189) | 0 | Cooling power SOLL |
| H | `=A` | – | t_A |
| I | `CT*1000` | – | Fan kWh |
| J | `CK*1000` | – | Heating kWh |
| K | `CM*1000` | – | Hum.-heating kWh |
| L | `CJ*1000` | – | Cooling kWh |
| M | `CE*1000` | – | Dehum.-cooling kWh |
| N | `CF*1000` | – | Dehum.-heating kWh |
| O | `BN` | – | t_ZUL-IST °C |
| P | `BO*100` | – | rF_ZUL-IST % |
| H328 | Total | | |
| I328 | `SUM(I267:I327)` | 26765.14 kWh | Fan |
| J328 | `SUM(J267:J327)` | 3786.30 kWh | Heating |
| K328 | `SUM(K267:K327)` | ≈0 | Hum.-heating |
| L328 | `SUM(L267:L327)` | 1750.16 kWh | Cooling |
| M328 | `SUM(M267:M327)` | 0 | Dehum.-cooling |
| N328 | `SUM(N267:N327)` | 0 | Dehum.-heating |

### Required Key Addresses
- **(a) Annual final energies per treatment stage (correspond to Lüftung!Q32…Z32):** `C254` (Luftkühlung, kWh), `C255` (Lufterwärmung), `C256` (Erwärmung Befeuchtung), `C257` (Entfeuchtung Kühlung), `C258` (Entfeuchtung Erwärmung), `C259` (Ventilator). MWh equivalents in row 7: `Q7=C254/1000`, `S7=C255/1000`, `U7=C256/1000`, `W7=C257/1000`, `Y7=C258/1000`, `H7=C259/1000`. Powers: `D254…D258` (resp. `P7,R7,T7,V7,X7`). The exact column assignment of Lüftung!Q32…Z32 must be verified on the Lüftung dump.
- **(b) Fan energy cell:** `C259` (kWh) resp. `H7` (MWh); power `G6`/`D259`; annual average `M70`.
- **(c) Full-load hours cell:** `K68` (3900 h, from `Std!$Q$6:$V$50` via MATCH on `B6`); `K69` (Elektrizität, 3900); computed check `J7 = ROUND(IF(G6=0,0,H7*1000/G6),-1)`; `J6 = K68`.

---

## 7. Errors / Dead Cells

| Cell(s) | Error | Cause / Meaning |
|---|---|---|
| `AQ121…AQ249` (122 cells, both blocks) | `#NAME?` | `TaupunktA(x,p)` UDF is defined but commented out/not registered → cell value is an error. |
| `AS121…AS249` (122 cells) | `#VALUE!` | `EnthalpieA(AQ,AR,$N$19)` with error input AQ → propagated. |
| `J11` | `#N/A` | SOLL status formula: OR expression contains `F40<0` with F40=#N/A → #N/A. |
| `F40` | `#N/A` | SOLL design temperature (empty formula dependency, cached error). |
| SOLL block N/O/P/V/Z/AA/AB/… | `#REF!` subexpressions | `EnthalpieA(L,M,#REF!)` – the SOLL copies lost the `$N$19` pressure reference (results nevertheless arithmetically correct, because the #REF! arguments only stand in the dead enthalpy intermediate cells; the R: values show plausible numbers since the cached value was apparently computed with a valid pressure – caution: formula text ≠ computed value). |

No `#DIV/0!` in the current state (caught by ISERROR/IFERROR/IF guards; see §8).

---

## 8. Assumptions & Quirks

**Constants:** cpl = 1.006 (N20), cpw = 1.86 (N21), cw = 4.19 (N22), ρ = 1.15 kg/m³ (N23), r0 = 2501.6 (N24), r100 = 2256 (N25), Luftdruck 948.2 mbar (N19 from Klimadaten!F44), Quellluft surcharge 2 K (N18), 3600 s/h (3.6e6 kJ/MWh), 8760 h/a, Kaltwassertemperatur 10 °C (E51).

**Peculiarities / Quirks:**
1. **Gebläsegesetz with exponent 2.5** (instead of 3) in I14:I19.
2. **Sums start at row 122** – the class −25 °C (row 121) is excluded from all energy sums (`CE182…CT182`, `CE250…CT250`) (B121=0, therefore without effect here).
3. **`CC183 = MAX(CC$133:CC$181)…`** – heating power maximum from row 133 (−10 °C), not from 121.
4. **`T{n} = MIN(…einfaches Argument…)`** – MIN() without a second argument is a no-op (temperature-control intermediate value).
5. **AD column** is a literal running scratch column (−1…59) only for AE (which itself is nowhere referenced) – presumably legacy/chart aid.
6. **D column (rF_AUL from Klimadaten!N)** is referenced by no formula (display only); the effective room rF is recomputed in E via `RelFeuchte(BR, C, p)`.
7. **222/−222 guards** in CN…CV for charts (hiding when B=0 or E=0); `1E+23` in AG against a vertical cooling curve.
8. **ROUND(…,4) comparisons** in the case detector AW against floating-point artifacts.
9. **Energy prices** (I26:I28, J26:J28) are empty → all costs (F254:F259) = 0; only water price 185 Rp./m³ (I29/J29) filled.
10. **Operating-hours block** (L58:L61, 80 h/week) does not enter the energy sums directly – the annual hours come from `K68` (Std lookup 3900 h); the stage shares M58:M60 flow only into the weighted stage powers/flows (K64:M67) and the plausibility values.
11. **Chart powers** (B267:D327) divide by `Klimadaten!O{k+30}` (Klima hours), not by the scaled operating hours B – the "kW" curves are thus related to real annual hours.
12. **SOLL block inactive:** Klimadaten cells literally 0, `#REF!` print, K82/M82/P82/R82 = 0 → all SOLL energies 0; SOLL humidification type "keine" (F49) and dehumidification "nein" (F47) additionally deactivate the corresponding terms.
13. **UDF dependencies:** `EnthalpieA`, `AbsFeuchte`, `RelFeuchte`, `TemperaturH`, `Fall1Tzul`, `Fall1xzul`, `Fall2Tzul`, `Fall2xzul`, `LUET`, `LUEAB` (documentation in A184/D184); `TaupunktA` defective (#NAME?).
14. **`E41`/`E44` (installed coil capacities)** are empty – only status checks (I11) and design temperatures (E40/E43) are filled; the annual calculation does not need them.
15. **Fresh-air fraction E34/E35 = 1** → no recirculation mixing (MIL = outside air after WRG); the recirculation shares P/V result in 0.
16. **WRG bypass** (E30="ja") makes the regulated efficiency K effective; in summer (t_A ≥ t_ZUL) K falls to 0 (full bypass), in winter K remains E28 = 0.8.
17. **Room/exhaust-air model:** exhaust air = room state from temperature curve + climate rF, limited to the humidity target band [E50, E48] – i.e. the exhaust air "inherits" the outside humidity, which with N6=O6=0 (band [0,1]) leads to identical x_Raum = x_AUL.
18. **Feuchtelast I20/J20** = 0 (E52=0) → exhaust-air x = room x.
19. The sheet computes **one system per instance**; the 16-fold structure (LA01…LA16) arises via macro copies of the Lüftung row 32, not via rows 7–22 here.

---

## Summary of the Calculation Chain (Short Form for the Chapter)

t_A (Klimadaten) → hours B = O/8760·K68 → AUL state (C, E) → WRG (I, K, L, M) → MIL (N…Y, recirculation damper) → cooling coil A/C + linear cooling curve (Z…AM) → cases 1–4 (AW) → ZUL-IST (BN, BP) → enthalpy differences (BZ…CD) → energies (CE…CM, CT) → sums (row 182) → kWh results (C254…C259) → row 7 (P7…Y7, H7) → Lüftung.

---

*Note on creation (2026-08-20, merge of the document trees):* the analysis is based on
`sheet_61_Berechnung LU.tsv` (read completely in chunks) with numerical cross-check
(CT168, CJ168, K168, K121, CJ182→C254→Q7, C259→H7, J7, K70/M70, I88/J88), consistency ΣB = K68 and
the Klimadaten assignment t_A+30. Open detail questions are transferred into Chapter 4 of the textbook
(README §0.7 and ch04 §4.14): Lüftung!Q32…Z32 assignment (ch04 §4.12/4.14-8),
`TaupunktA` defect (ch01 §1.7), sum start row 122 / CC183 from row 133 (ch04 §4.14-2), SOLL-
block sleep state (ch04 §4.14-3).
