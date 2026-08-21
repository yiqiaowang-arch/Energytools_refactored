# Excel equivalence

Every table and calculation of the SIA 2024 workbooks (Raumdatenblätter
and Gebäude-Tool, version V221) is either **extracted into the dataset**,
**reproduced by the engine**, or **derivable from extracted data** — this
matrix maps each workbook sheet/block to its Python counterpart and its
verification status.

## Input tables → dataset

| Workbook sheet / block | Dataset table | Verification |
|---|---|---|
| `Eingabedaten` room-use list (rows 9-53) | `ds.room_uses` (45 uses) | extracted, count-checked |
| `Eingabedaten` parameter matrix (D..DN) | `ds.profile(nutzid)` (193 parameters × Standard/Zielwert/Bestand) | extracted |
| `Eingabedaten` schedules (DP9:HY53) | `ds.schedules` (person/device 24 h, week, 2×12-month, rest days) | extracted; simultaneity matches workbook cache |
| `Eingabedaten` input columns (K..IE) | `ds.inputs` (Fensteranteil, Schallschutz, IDA, SIA 380/1 requirements, ...) | extracted |
| `Begriffe` / `Datenblatt` | parameter catalog, labels, units | extracted |
| `Volll_Lüft` | `ds.full_load_hours` (+ electrical, stage hours) | extracted |
| `Qhc_Klimastat` | `ds.qhc` (4 metrics × 40 stations × 45 uses) | extracted |
| `Monatswerte` / `Winter_Auslegung` / `Aug_Auslegung` | `ds.climate` (monthly, winter design, 96 h design days) | extracted |
| `KZ_Raum_2024` + `Std` | KPI matrix in `ds.profile` (backfilled) | checksum-verified |
| `Fläche-E/-ZW/-Best/-L`, `GEPAMOD` | `ds.category_tables` (60 tables, 19 kinds) | extracted |
| `SIA 380-1` family | `ds.sia3801_results` + `ds.sia3801_coefficients` | extracted |
| `Profile!AS278:BD284` | `ds.sia2028_monthly` (SIA 2028 monthly reference) | extracted |

## Calculations → engine functions

| Workbook calculation | Python | Verification |
|---|---|---|
| FeuchteLuft_Formeln.bas (psychrometrics) | `engine.native.psychrometrics` | golden rel ≤ 1e-16 |
| `Berechnung LU` (AHU temperature-bin) | `engine.native.ahu.compute_ahu_annual` | golden, LA01 row exact (rel ≤ 1e-6) |
| Gebäude/Resultate aggregation | `engine.native.aggregation.aggregate` | case-02 rows rel ≤ 1e-6 |
| Erzeugung + Nutzungsgrad | `NutzungsgradCatalog` + generation groups | case-02 |
| `Wärmebilanz - Sommertag` (24 h) | `summer_balance.summer_balance_24h` | **cache-exact (max diff 0.0)** |
| `Stoffbilanz - Arbeitstag` (24 h) | `stoffbilanz.stoffbilanz_24h` | **cache-exact (max diff 0.0)** |
| Jahresprofil / Wochenprofil | `Schedule.yearly_distribution` (8760 h) | sums to annual |

## User-facing domain layer

| Excel concept | Python |
|---|---|
| Gebäude (building) | `building.Building` |
| Raum (room) | `building.Room` |
| Raumnutzung (room-use class) | `building.RoomType` |
| Klimastation | `building.Climate` |
| Tagesprofile | `Room.schedules.occupancy/device/lighting` |
| Lüftung / Erzeugung | `Room.ventilation`, `Room.add_generation`, `Building.add_generation` |
| Resultate | `Building.load` (per-kind annual + hourly, per-carrier totals) |

## Known approximations (documented, not silent)

- The Norm-Lüftungswärmeverlust ``FV,i`` has no per-station matrix and
  carries the Zürich (station 40) default; the backend warns for other
  stations.  (The Klimakälte/Heizwärme KPI ``1.1.6.5``/``1.1.6.7``/
  ``1.1.7.9`` are read from the per-station Qhc_Klimastat matrices, so
  non-Zürich buildings get their station's values.)
- The fan full-load hours on an electricity basis default to the
  air-volume values (K69 ≈ K68).
- The hourly load series distribute the verified annual values by the
  room schedules (temperature-weighted months for heating/cooling); they
  are not a separate physical simulation.
- `Allg. Gebäudetechnik` (AG01-AG10) is 0; construction factor 10 % and
  Aufheizzeit 6 h/d are the aggregation defaults.
