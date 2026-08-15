# Chapter 6 — Climate Data (Klimadaten and Qhc_Klimastat)

> Core areas: `Klimadaten!A1:Q65` (40-station metadata + selected-station bin data), `Klimadaten!S1:CT65` (40 stations × bin hours/humidity), `Qhc_Klimastat!A1:O51` (selected-station cooling/heating load intensities), `Qhc_Klimastat!P3:SA51` (40-station snapshot)
> Consumers: `Gebäude!D2` (station selection) → `Berechnung LU!N19` (air pressure), `KZ_Raum_2024` (Qhc references)

## 6.1 Chapter Placement

The AHU temperature-bin method (Chapter 4) needs the **bin hours**, **relative humidity** and **air pressure** for each outdoor temperature bin; the room cooling/heating load characteristic values (Chapter 2) need the climate-dependent Klimakälte/Heizwärme intensities. This chapter presents the structure, formulas and provenance of these two blocks of climate data. There are 40 Swiss climate stations in total (MeteoSchweiz series).

## 6.2 Klimadaten Layout

**Station metadata block** (`Klimadaten!B4:J43`, 40 stations):

| Column | Content | Unit | Formula |
|---|---|---|---|
| B | Station name | – | Static (lookup key) |
| C | Canton (Kanton) | – | Static |
| D | Altitude | m ü.M. | Static |
| E | Air pressure | mbar | `=1013.25*(1-(0.0065*D4)/288.15)^5.255` (standard-atmosphere formula) |
| F | Selected-station air pressure | mbar | `=IF(B4=$N$1,E4,0)` (non-zero only for the selected station) |
| G | Heizgradtage (heating degree days, HDD) | K·d | Static |
| H | Selected-station HDD | K·d | `=IF(B4=$N$1,G4,0)` |
| I | Design temperature Heizung (winter) | °C | Static |
| J | Design temperature Lüftung (winter) | °C | Static |

**Selected station**: `Klimadaten!N1: =INDEX(B4:B43,Gebäude!D2,0)` (station name); `Gebäude!D2` is the user-entered station index (example = 40 → Zürich-MeteoSchweiz).

**Bin block** (`Klimadaten!L5:Q65`, 61 rows = temperature −25…+35 °C in 1 K steps):

| Column | Content | Unit | Formula |
|---|---|---|---|
| L | Bin-table row number | – | 5…65 (= row number) |
| M | Bin temperature T | °C | −25…+35 |
| N | Selected-station relative humidity φ | – (header says [%], actually a 0–1 fraction) | `=INDEX($S$1:$CT$65, L5, MATCH($N$2, $S$2:$CT$2, 0))` |
| O | Selected-station bin hours | h | `=INDEX($S$1:$CT$65, L5, MATCH($O$2, $S$2:$CT$2, 0))` |
| P | Cumulative bin hours | h | `=O5+P4` (from P5; P65 = 8760) |
| Q | Selected-station moisture content | g/kg | `=AbsFeuchte(M5,N5,$F$44)` (Chapter 1, Formula 2) |

**All-station bin matrix** (`Klimadaten!S1:CT65`): S/T, U/V, …, CS/CT = two columns per station (relative humidity φ, bin hours), rows 5–65 correspond to −25…+35 °C; rows 1–4 hold station name/title/subtitle/units. The matrix is **static data** (from the "Summenhäufigkeit" hourly distribution published by SIA/MeteoSchweiz).

**Selected-station air pressure and HDD** (`Klimadaten!F44/H44`): `=SUM(F4:F43)`, `=SUM(H4:H43)` — since only the selected station is non-zero in columns F/H, the sum equals the selected station's value. `F44` is referenced by `Berechnung LU!N19: =Klimadaten!F44` as the whole-engine air-pressure constant (example 948.226 mbar).

## 6.3 Formula 1 — Station Air Pressure (standard-atmosphere height formula)

**Mathematical form**:

$$
p(h) = p_0\left(1 - \frac{\Gamma h}{T_0}\right)^{g/(R\Gamma)} = 1013.25\left(1-\frac{0.0065\,h}{288.15}\right)^{5.255} \quad[\mathrm{mbar}]
$$

**Workbook implementation** (`Klimadaten!E4`): `=1013.25*(1-(0.0065*D4)/288.15)^5.255`

**Units**: h [m], p [mbar].

**Derivation**: the dry-adiabatic pressure–height formula of the International Standard Atmosphere (ISA): sea-level pressure $p_0=1013.25$ mbar, sea-level temperature $T_0=288.15$ K (15 °C), temperature lapse rate $\Gamma=0.0065$ K/m, exponent $g/(R\Gamma)=9.80665/(287.05\times0.0065)=5.255$. **Verification**: Zürich-MeteoSchweiz (`Klimadaten!B43`, D43=556 m ü.M.): `E43 = 1013.25(1-0.0065×556/288.15)^5.255 = 948.226 mbar`, in exact agreement with `F44 = SUM(F4:F43) = 948.226` ✓ (the selected station's air pressure is its E-column value; only the selected station is non-zero in `F4:F43`).

**Assumptions**: standard atmosphere (not the actual annual-mean air pressure); a single station represents the entire building location.

**Applicability**: Swiss stations at altitudes of 200–3400 m (Grand-St-Bernard 2472 m: $p\approx 750$ mbar); the error remains < 1 % even for high-altitude stations.

**Cell provenance**: `Klimadaten!E4:E43`, `F4:F43`, `F44`; consumer `Berechnung LU!N19`.

## 6.4 Formula 2 — Bin Hours and Cumulative Frequency

**Mathematical form**: $O_{T}$ = the number of hours in the average year in which the outdoor temperature falls into bin $[T-0.5, T+0.5)$ °C; $P_T = \sum_{t\le T} O_t$ (cumulative hours).

**Workbook implementation**: `Klimadaten!O5: =INDEX($S$1:$CT$65, L5, MATCH($O$2, $S$2:$CT$2, 0))`; `P6: =O6+P5`.

**Units**: h (annual total P65 = 8760 ✓, verified for the example station).

**Derivation**: the bin hours count the hourly weather year (8760 h) into bins by dry-bulb temperature (the basis of the temperature-bin method, see Chapter 4, §4.2); cumulative column P serves "hours below a given temperature" lookups (e.g. design-condition checks).

**Assumptions**: 1 K bins; zero hours below −25 °C and above +35 °C (Swiss climate); the bin temperature takes the bin's lower bound (column M values −25…+35 correspond one-to-one with row numbers 5…65 in column L).

**Applicability**: the 40 standard stations; intended for energy calculations (not extreme design).

**Cell provenance**: `Klimadaten!O5:O65`, `P5:P65`; consumer `Berechnung LU` bin rows (Chapter 4).

## 6.5 Formula 3 — Bin Relative Humidity and Moisture Content

**Mathematical form**: $\varphi_T$ = the mean relative humidity (as a fraction) for bin temperature T; $x_T = 622\,\varphi_T p_s(T)/(p - \varphi_T p_s(T))$ (Chapter 1, Formula 2).

**Workbook implementation**: `Klimadaten!N5: =INDEX($S$1:$CT$65, L5, MATCH($N$2, $S$2:$CT$2, 0))`; `Q5: =AbsFeuchte(M5,N5,$F$44)`.

**Verification** (example station, T=−10 °C): `N20=0.8817`, `Q20=1.5015 g/kg`; T=20 °C: `N50=0.5925`, `Q50=9.2165 g/kg` ✓.

**Units**: φ [–] (the header `[%]` is misleading, see README §0.7-2); x [g/kg].

**Assumptions**: the bin humidity is the mean (arithmetic average) humidity, combined with temperature as a "design-day" state pair; the joint distribution of humidity and temperature is not considered (the humidity distribution belonging to a bin temperature is compressed to its mean).

**Applicability**: the standard simplification for AHU annual energy calculations (SIA practice).

**Cell provenance**: `Klimadaten!N5:N65`, `Q5:Q65`; consumer `Berechnung LU` columns BR/C (outdoor enthalpy–humidity state).

## 6.6 Qhc_Klimastat: Room Cooling/Heating Load Intensity Matrix

**Structure**:
- `Qhc_Klimastat!A7:B51`: room-use codes and names (external link `[3]Eingabedaten!A9:C53`, i.e. the room list of the Raumdatenblätter — note the offset: row 7 corresponds to code 1.01, while `Res` row 7 corresponds to 1.1);
- `C7:C51`: row numbers 1…45;
- `P3:SA3`: 40 stations × 12-column blocks = station names (external link `[3]Winter_Auslegung!A5:A44`); `P7:SA51`: a 12-column numeric snapshot per station, block layout: Standard (Kühlung P, Kühlung E, Heizung P, Heizung E), Zielwert (same 4 columns), Bestand (same 4 columns);
- `G3: =MATCH(D3,P3:SA3,0)`: the starting column of the selected station's block (example = 469 → column RP, Zürich-MeteoSchweiz);
- **Selected-station block** (`D7:O51`): `D7: =INDEX($P$7:$SA$51,$C7,$G$3-1+D$2)` (D2=1…12 is the offset within the block) — i.e. the 40-station snapshot is sliced by the selected station into 12 columns × 45 rows.

| Selected-station column | Content | Unit | Referenced by `Res` |
|---|---|---|---|
| D/E | Kühlung Leistung/Energie Standard | W/m² / kWh/m² | `KZ_Raum_2024!AC{row}/G{row}` |
| F/G | Heizung Leistung/Energie Standard | W/m² / kWh/m² | `KZ_Raum_2024!AH{row}/H{row}` |
| H/I | Kühlung Zielwert | W/m² / kWh/m² | `AN/O` |
| J/K | Heizung Zielwert | W/m² / kWh/m² | `AO/P` |
| L/M | Kühlung Bestand | W/m² / kWh/m² | `AU/W` |
| N/O | Heizung Bestand | W/m² / kWh/m² | `AV/X` |

**Verification** (Einzel-, Gruppenbüro, row 11): `Qhc!D11=43.656 W/m²` (=`KZ_Raum_2024!AG11` cached 43.656 ✓), `Qhc!E11=14.430 kWh/m²` (=`G11` ✓), `Qhc!F11=19.823 W/m²` (=`AH11` ✓).

**Data source**: the Qhc matrix is a copy of the Raumdatenblätter's `Qhc_Export` (annual cooling/heating energy and design power for 40 stations × 45 room uses × 12 months × 3 value ranges). Its annual-value formula (on the Raumdaten side) sums the monthly $Q_{hc}$ and takes the design condition for power; in the Gebäude-Tool it is used as a **static snapshot** (external link `[3]` only provides the station names and the room-use list; the data itself is not refreshed automatically — README §0.7-4).

**Cell provenance**: `Qhc_Klimastat!D7:O51` (slice), `G3` (station match), `P7:SA51` (snapshot); consumer `KZ_Raum_2024!C7:I51, AC7:AV51` (12 reference columns).

## 6.7 Complete Climate-Data Reference Chain

```
Gebäude!D2 (station index) ──► Klimadaten!N1 (station name) ──► Gebäude!D3 display
                    ├─► Klimadaten!F44 (air pressure) ──► Berechnung LU!N19
                    ├─► Klimadaten!N/O/Q (bin φ, h, x) ──► Berechnung LU bin rows
                    ├─► Klimadaten!I/J (design temperatures) ──► (unused by Erzeugung/Resultate; used on the Raumdaten side)
                    └─► Qhc_Klimastat!G3 (station block) ──► D7:O51 ──► KZ_Raum_2024 (Res) ──► Gebäude!Q..U
```

## 6.8 Porting Key Points

1. The bin hours and humidity should be kept as a **versioned external dataset** (published by SIA/MeteoSchweiz), separate from the calculation model; inside Gebäude-Tool they are pasted data without a version stamp (Raumdaten `Aug_Auslegung` has the precedent of importing `AIGSommer.dat` via Power Query).
2. "Column-name matching" of the `MATCH($N$2,$S$2:$CT$2,0)` kind can be retained as a data-validation aid; after porting, a structured key (station × quantity × bin) is recommended instead.
3. The "selected-station sum" trick for air pressure and HDD (F44 = SUM(F4:F43)) should be expressed directly as a station attribute when porting.
4. The 12-column block layout of the Qhc snapshot (4 quantities × 3 value ranges) corresponds one-to-one with `Res`'s reference columns; keeping the station axis when porting eliminates the `G3` slice formula.
5. The inconsistency between the header unit `[%]` and the actual 0–1 fraction, and the slight deviation of `F44` from the standard-atmosphere formula, should be handled explicitly in the data-validation rules.
