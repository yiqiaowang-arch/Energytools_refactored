# Strukturanalyse des Blatts „Berechnung LU" (Gebäude-Tool, SIA 2024)

Analyse-Quelle: `Energytools_refactored/.analysis/dumps/gebaeude/sheet_61_Berechnung LU.tsv`
(15.416 Zeilen, 328 Zeilen × 108 Spalten A…DD, davon Spalten A…DC belegt; 13.466 Formelzellen).

**Zweck des Blatts:** Jährliche Energiebedarfs-Berechnung einer Lüftungsanlage (AHU) nach
Temperaturklassen-Verfahren („temperature-bin") mit psychrometrischen Zuständen
(Enthalpie / absolute Feuchte / relative Feuchte). Das Blatt rechnet **eine** Anlage
(hier LA01) durch; die Parameter kommen aus dem Blatt `Lüftung` (Zeile 32), die
Ergebnisse gehen an `Lüftung` zurück (z. B. `'Berechnung LU'!H7`).

> **Korrekturen zu den Vorgaben im Auftrag:**
> 1. Zeilen 7–22 sind **keine** 16 Anlagen-Ergebniszeilen (LA01…LA16). Nur Zeile 6
>    (Eingabe) und Zeile 7 (Resultate) enthalten die Daten der einen Anlage LA01
>    (`A6 = Lüftung!A32` → LA01). Zeilen 8–22 sind Überschriften und der Eingabe-
>    block. Die „Kopie-Template-Zeile 32" liegt im Blatt `Lüftung` (LA01-Parameterzeile),
>    nicht hier; hier ist Zeile 32 `Vereisungsschutz`.
> 2. `$E$34`/`$E$35` sind **nicht** WRG-Wirkungsgrade, sondern **min./max. Frischluftanteil**
>    der Umluftregulierung (beide = 1, d. h. 100 % Frischluft, keine Umluft). Die
>    WRG-Wirkungsgrade stehen in `$E$28` (0.8) und `$F$28` (0.65).
> 3. Das Blatt enthält **zwei parallele Temperaturklassen-Blöcke**: IST (Zeilen 121–183,
>    Eingaben aus Spalte E) und SOLL (Zeilen 189–250, Eingaben aus Spalte F). Der
>    SOLL-Block ist in dieser Arbeitsmappe inaktiv (Klimadaten-Zellen = 0, `#REF!`-Druck-
>    referenz), liefert also überall 0.

---

## 1. Layout-Karte (Zeilen)

| Zeilen | Rolle | Schlüsselzellen |
|---|---|---|
| 1 | Titel | `A1 "Berechnung LU"` |
| 3–5 | Tabellenkopf der Systemzeile | `C3 Volumenstrom`, `F3 Zu- und Abluft-Ventilator`, `K3 Zuluftkonditionierung`, `P3 Luftkühlung`, `R3 Lufterwärmung`, `T3 Befeuchtung Erwärmung`, `V3 Entfeuchtung Kühlung`, `X3 Entfeuchtung Erwärmung`; Einheiten Zeile 5 (m³/h, W/(m³/h), kW, MWh, h/a, %, °C, % r.F.) |
| 6 | **System-Eingabezeile LA01** | `A6=Lüftung!A32` (LA01), `B6` Nutzung, `C6` Volumenstrom 8578.57 m³/h, `D6` Prozess 0, `E6` Projekt 0, `F6` SFP 0.8 W/(m³/h), `G6` Leistung 6.863 kW, `I6` Regelung „einstufig", `J6=F:K68` (3900), `K6` WRG 80 %, `L6` 20 °C (Sommer), `M6` 21 °C (Winter), `N6`/`O6` 0 % r.F. |
| 7 | **Ergebniszeile** | `E7` Volumenstrom (E6||C6), `H7=C259/1000` Ventilator-MWh, `J7` Volllaststunden, `P7=D254`, `Q7=C254/1000`, `R7=D255`, `S7=C255/1000`, `T7=D256`, `U7=C256/1000`, `V7=D257`, `W7=C257/1000`, `X7=D258`, `Y7=C258/1000` |
| 8 | Ventistufe | `H8 "Ventistufe"`, `I8 = IF(I6=Begriffe!F205,1,IF(I6=Begriffe!F206,2,IF(I6=Begriffe!F207,3,FALSE)))` → 1 (einstufig) |
| 9–10 | Abschnittsüberschriften „Eingabe / Grundlagen / Beschriftung", „IST-Zustand / SOLL-Zustand" | `G10 "L01"`, `N10–R10` Leistungsbereiche der Effizienzklassen (bis 1.1 kW … ab 110 kW), `S10 "Quellluft"` |
| 11–25 | **Eingabeblock Lüftungstechnik** (IST=Spalte E, SOLL=Spalte F) | Luftwechsel 11–13, Filter 14–15, ZUL-Ventilator 16–20, ABL-Ventilator 21–25 (Details §2) |
| 26–27 | Saisonaler Volumenstrom | `E26` Sommerbetrieb ab t_A (0), `E27` Volumenstromerhöhung dV (0) |
| 28–33 | WRG/KRG | `E28=K6%` 0.8 (therm. WRG), `E29` 0 (Feuchte-WRG), `E30 "ja"` (Bypass), `E31 "ja"` (Kälterückgewinnung), `E32` 0 + `I32 "elektrisch (ein/aus)"`, `E33` 0 (Grenztemp. Vereisungsschutz), `I33 "elektrisch (variabel)"` |
| 34–38 | Umluft / Frischluftquelle | `E34` 1 (Frischluftanteil min.), `E35` 1 (max.), `E36 "Temperatur"` (Regulierungsbasis), `D36` leer, `E37/E38 "Aussenluft"` |
| 39–46 | Heizregister / Kälteregister | `E39 "ja"` (Heizregister), `E40` −13 °C (Auslegung), `E41` leer (Install. Leistung); `E42 "ja"` (Kühlung), `E43` 35 °C / `F43` 30 °C (Auslegung), `E44` leer; `E45` 6 / `E46` 12 (LK VL/RL °C); `I39:I47` VLOOKUP-Tabelle Regelungsarten (Zeitsteuerung 1.0 … VAV 0.55) |
| 47–51 | Entfeuchtung / Befeuchtung | `E47 "ja"` (Entfeuchtung), `E48=IF(OR(N6="",N6=0),1,N6%)` → 1 (max. r.F.), `E49 "Adiabatisch Bef."` (Art), `E50=IF(O6="",0,O6%)` → 0 (min. r.F.), `E51` 10 (Kaltwassertemperatur °C) |
| 52–55 | Raumlast / Nutzungszone | `E52` 0 (Feuchtelast), `E54 "Benutzerdefiniert"` (Regelungsart), `E55` 0 |
| 56–69 | **Betriebszeiten IST** | `B58:C61` Zeitfenster, `I58:I60` h/Woche je Stufe (50/15/15), `L58:L60` mit VLOOKUP-Faktor, `L61` 80 h, `M58:M60` Anteile (0.625/0.1875/0.1875); Stufen-Volumenströme/-Leistungen `J64:J66`, `K64:K66`, `L64:L66`, `M64:M66`, `K67`/`M67` Summen |
| 70 | Plausibilitätstest IST | `K70=E7*K68/8760` (3819.2 m³/h), `M70=G6*K69/K68` (6.863 kW), `P70=K70`, `R70=M70` |
| 71–85 | **Betriebszeiten SOLL + Plausibilitätstest SOLL** | analog mit Spalte F; `K82=SUM(K79:K81)` (0), `M82=SUM(M79:M81)-B114` (0), `P82`, `R82` |
| 86–91 | **Temperaturkurve IST** (ZUL- und Raumtemperatur f(t_A)) | `B88:B91` t_A (−15/22/24/30), `C88:C91` t_ZUL (21/20/20/20), `D88:D91` t_Raum (22/24/25/25); Steigungen `I88:I90`, `J88:J90` |
| 92–97 | **Temperaturkurve SOLL** | `B94:B97`, `C94:C97` (22/22/22/22), `D94:D97` (24/24/26/26); `I94:I96`, `J94:J96` |
| 100–108 | Ventilatorleistung anhand Effizienzklasse | Effizienz-Lookup je Klasse × Leistungsbereich; `C108=MAX(C102:C107)` (1), `E108` (1), `H108` (0.85), `J108` (0.85) |
| 109–115 | Filterstufen / Pw / Pm / Vereisungsschutz | `B110/B111` Filterdruck (Pa), `B112` Differenz, `B113=Pw`, `B114=Pm`, `F113` Vereisungsschutz-Leistung (15.96 kW) |
| 117–120 | Kopf des IST-Klassenblocks | Spaltenbeschriftungen + Einheiten (detailliert §3) |
| 121–181 | **IST-Temperaturklassen-Berechnung** (61 Klassen, t_A = −25…+35 °C) | Formelmuster §3/§4 |
| 182–183 | **IST-Summen** | Zeile 182: Energiesummen `CE182…CM182`, `CT182`, `CW182`; Zeile 183: Leistungsmaxima `BZ183…CD183` |
| 184 | Doku-Zeile (VBA-Formeltext LUET/LUEAB, `#NAME?`-relevant) | `A184`/`D184` als Text |
| 185–188 | Kopf des SOLL-Klassenblocks | wie 117–120, Zustände über 3 Spalten (T, x, h) |
| 189–249 | **SOLL-Temperaturklassen-Berechnung** (inaktiv: B/C/D = 0, `#REF!`-Druck) | gleiche Struktur, Eingaben aus Spalte F, Soll-Kurve aus Zeilen 94–97 |
| 250 | SOLL-Summen | `CE250…CM250`, `CT250` (alle 0) |
| 251–253 | Kopf „Energieverbrauch IST/SOLL", Diagramm-Lookups | `H253:J253` (t_ABL, r_F, x_Raum) |
| 254–263 | **Endergebniszeilen** (§6) | Luftkühlung, Lufterwärmung, Erwärmung Bef., Entfeuchtung (Kühlung/Erwärmung), Luftumwälzung (Ventilator), Total, Wasser Bef., Entfeuchtung-Wasser |
| 264–266 | Kopf „Daten für HG/KG", Diagramm | `H265:N265` Begriffe!F152:F158 |
| 267–327 | **Diagrammdaten je Klasse** (kW und kWh) | `B/C` Heizleistung, `D/E` Kühlleistung, `I:N` kWh je Stufe, `O` t_ZUL, `P` rF_ZUL |
| 328 | Diagramm-Totale | `I328:N328` Summen |

---

## 2. Eingabeblock (Zeilen 1–32) – vollständige Liste der eingabeführenden Zellen

Werte für die Beispielanlage LA01 (IST = Spalte E, SOLL = Spalte F).

### Zeile 6 – System (aus `Lüftung`-Zeile 32)
| Zelle | Formel / Wert | Bedeutung |
|---|---|---|
| A6 | `F:Lüftung!A32` → LA01 | Anlagenname |
| B6 | `F:Lüftung!B32` → „Einzel-, Gruppenbüro" | Nutzung (für Std-Lookup) |
| C6 | `F:Lüftung!C32` → 8578.571… | Standard-Volumenstrom m³/h |
| D6 | `F:Lüftung!D32` → 0 | Prozess-Volumenstrom |
| E6 | `F:Lüftung!E32` → 0 | Projekt-Volumenstrom |
| F6 | `F:Lüftung!G32` → 0.8 | SFP W/(m³/h) |
| G6 | `F:Lüftung!H32` → 6.862857 | Ventilatorleistung total (Zu+ABL) kW |
| I6 | `F:Lüftung!J32` → „einstufig" | Regelung |
| J6 | `F:K68` → 3900 | Volllaststunden (h/a) |
| K6 | `F:Lüftung!L32` → 80 | WRG % |
| L6 | `F:Lüftung!M32` → 20 | Zuluft-Solltemperatur Sommer °C |
| M6 | `F:Lüftung!N32` → 21 | Zuluft-Solltemperatur Winter °C |
| N6 | `F:Lüftung!O32` → 0 | Feuchtesoll Sommer % r.F. |
| O6 | `F:Lüftung!P32` → 0 | Feuchtesoll Winter % r.F. |

### Zeile 7 – Resultate (s. §6; hier schon die Verknüpfungen)
`E7=IF(OR(E6="",E6=0),C6,E6)` (8578.57); `H7=C259/1000`; `J7=ROUND(IF(G6=0,0,H7*1000/G6),-1)`; `P7…Y7` s. §6.

### Zeilen 11–25 – Lüftungstechnik (IST E / SOLL F)
| Zelle | Wert | Bedeutung |
|---|---|---|
| E11/F11 | 500 / 2 | Klimatisierte Fläche (m²) |
| E12/F12 | 3 / 3 | Raumhöhe (m) |
| E13/F13 | „Mischluft" | Art der Lufteinbringung (Alternative „Quellluft" = S10) |
| E14/F14 | „0 keinen" | Vorfilterklasse (LOOKUP gegen M28:M44) |
| E15/F15 | „0 keinen" | Nachfilterklasse |
| E16 | `F:G6/2` → 3.4314 | ZUL-Ventilatorleistung Stufe 1 (kW) |
| F16 | 0 | SOLL-ZUL-Leistung |
| E17 | „IE5 - gefaked" | ZUL-Motoreffizienzklasse (IST) |
| F17 | „IE3 (< 2016)" | SOLL |
| E18 | `F:E7` → 8578.57 | ZUL Stufe 1 Volumenstrom (m³/h) |
| F18 | 0 | SOLL |
| E19 | `F:IF(OR(I6="einstufig",I6="1 vitesse",I6="1 velocità"),E18,E18*0.67)` | ZUL Stufe 2 (einstufig → =E18, sonst 67 %) |
| E20 | `F:IF(OR(I6="einstufig",…),E18,IF(OR(I6="zweistufig",…),E18*0.67,E18*0.33))` | ZUL Stufe 3 (33 % bei stufenlos) |
| E21 | `F:E16` | ABL-Leistung Stufe 1 |
| E22 | `F:E17` | ABL-Motorklasse |
| E23/E24/E25 | `F:E18`/`F:E19`/`F:E20` | ABL Stufen-Volumenströme |
| I14…I16 | s. §5.1 | ZUL-Stufenleistungen (Ventilatorgesetz) |
| I17…I19 | analog mit E21/E23..E25 | ABL-Stufenleistungen |
| I20 | `F:IF(E52=0,0,(E52*1000)/(3600*(K70/3600)*N23))` → 0 | Feuchtelast (g/kg Zuluft-Erhöhung) |
| J20 | analog mit F52/K82 | SOLL |

### Zeilen 26–33 – saisonaler Volumenstrom, WRG/KRG
| Zelle | Wert | Bedeutung |
|---|---|---|
| E26/F26 | 0 / 0 | „Sommerbetrieb ab einer Aussentemperatur von" (°C) |
| E27/F27 | 0 / 0 | Volumenstromerhöhung dV (m³/h) im Sommerbetrieb |
| E28 | `F:K6%` → 0.8 | WRG-Wirkungsgrad thermisch (IST) |
| F28 | 0.65 | WRG-Wirkungsgrad SOLL |
| E29/F29 | 0 / 0 | Feuchterückgewinnung (Faktor) |
| E30/F30 | „ja" | Bypass für Regulierung KRG/WRG |
| E31/F31 | „ja" | Kälterückgewinnung (KRG) |
| E32/F32 | 0 / 0 | Vereisungsschutz (0 = aus; Optionen „elektrisch (ein/aus)"=I32, „elektrisch (variabel)"=I33) |
| E33/F33 | 0 / 0 | Grenztemperatur Vereisungsschutz (°C) |

### Zeilen 34–38 – Umluft / Frischluftquelle
| Zelle | Wert | Bedeutung |
|---|---|---|
| E34/F34 | 1 / 1 | **Frischluftanteil minimal** (Umluftregulierung f(t_ZUL)) |
| E35/F35 | 1 / 1 | **Frischluftanteil maximal** |
| E36/F36 | „Temperatur" | Umluftregulierung anhand von (Alternative: D36, hier leer) |
| E37/F37 | „Aussenluft" | Frischluftquelle (Alternative „Vorkonditionierte Luft von LXX") |
| E38/F38 | „Aussenluft" | Art der vorkonditionierten Luft |

### Zeilen 39–51 – Register, Entfeuchtung, Befeuchtung
| Zelle | Wert | Bedeutung |
|---|---|---|
| E39/F39 | „ja" | Heizregister installiert |
| E40 | −13 | Leistungsberechnung Heizung bei °C (Auslegungs-Aussentemp.) |
| F40 | `#N/A` (Fehler) | SOLL-Auslegungstemperatur (leere Abhängigkeit) |
| E41/F41 | leer | Installierte Heizleistung (kW) |
| E42/F42 | „ja" | Kühlung installiert |
| E43/F43 | 35 / 30 | Leistungsberechnung Kühlung bei °C |
| E44/F44 | leer | Installierte Kühlleistung |
| E45/F45 | 6 / 6 | LK-Register Vorlauf °C |
| E46/F46 | 12 / 12 | LK-Register Rücklauf °C |
| E47/F47 | „ja" / „nein" | Entfeuchtung installiert |
| E48 | `F:IF(OR(N6="",N6=0),1,N6%)` → 1 | Max. zulässige rel. Raumfeuchte / Zuluftfeuchte Sommer |
| F48 | 0.99 | SOLL |
| E49/F49 | „Adiabatisch Bef." / „keine" | Art der Befeuchtung (S16=„keine", S17=„Adiabatisch Bef.") |
| E50 | `F:IF(O6="",0,O6%)` → 0 | Min. zulässige r.F. Winter |
| F50 | 0.01 | SOLL |
| E51/F51 | 10 / 10 | Kaltwassertemperatur (°C) – für Dampfbefeuchter-Energie |

### Zeilen 52–55
| Zelle | Wert | Bedeutung |
|---|---|---|
| E52/F52 | 0 / 0 | Feuchtigkeitslast im Raum (g/h?) |
| E54/F54 | „Benutzerdefiniert" | Regelungsart Volumenstrom (VLOOKUP gegen I39:J47) |

### Zeilen 56–70 – Betriebszeiten & Plausibilität (IST)
- Zeitfenster: `B58:C58` = 08:00–18:00 (Stufe 1), `B62:C62` = 11:00–14:00 (Stufe 2), `B66:C66` = 14:00–17:00 (Stufe 3); Sa/So leer.
- `I58 = 5*MIN(24,HOUR(C58-B58)+MINUTE(C58-B58)/60+HOUR(C59-B59)+…+HOUR(C61-B61)+…)` → 50 h (5 × 10 h). Entsprechend I59 → 15, I60 → 15.
- `L58 = SUM(I58:K58)*VLOOKUP($E$54,$I$39:$J$47,2,FALSE)` → 50 (Faktor „Benutzerdefiniert" = 1). `L61 = SUM(L58:L60)` → 80 h/Woche.
- `M58 = L58/L$61` → 0.625 (Anteil Stufe 1); M59/M60 = 0.1875.
- Stufenwerte: `J64=E18`, `K64=J64*M58` (gewichteter Volumenstrom), `L64=(I14/C108+I17/E108)` (Summe ZUL+ABL-Leistung/η), `M64=L64*M58`; analog Zeilen 65/66; `K67=SUM(K64:K66)` → 8578.57 (=E18, Konsistenztest), `M67=SUM(M64:M66)` → 6.863 (=G6).
- `K68 = IF($I$8=1,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),1),IF($I$8=2,…,3),IF($I$8=3,…,5),FALSE))` → **3900** (Volllaststunden Volumenstrom, SIA 2024)
- `K69 = …(Indexspalte 2/4/6)…` → **3900** (Volllaststunden Elektrizität)
- `K70 = E7*K68/8760` → 3819.23 m³/h (Jahresmittel-Volumenstrom)
- `M70 = G6*K69/K68` → 6.863 kW (Jahresmittel-Ventilatorleistung)
- `P70 = K70`, `R70 = M70` (für die dV-Sommerlogik)

### Zeilen 71–85 – Betriebszeiten & Plausibilität (SOLL)
Analog mit Spalte F; `K82 = SUM(K79:K81)` → 0, `M82 = SUM(M79:M81)-B114` → 0, `P82`, `R82`. Diese 0-Werte machen den gesamten SOLL-Klassenblock energieseitig zu 0.

### Zeilen 86–97 – Temperaturkurven
- IST: `C88=IF(M6=0,B88,M6)` → 21 °C (t_ZUL bei −15 °C), `C89..C91=IF(L6=0,B89,L6)` → 20 °C (t_ZUL bei 22/24/30 °C). Raum: D88=22, D89=24, D90=25, D91=25.
- Steigungen IST: `I88=IFERROR((C89-C88)/(B89-B88),0)` → −0.0270; `I89=0`, `I90=0`; `J88=0.0541`, `J89=0.5`, `J90=0`.
- SOLL: `C94..C97=22`, `D94=24`, `D95=24`, `D96=26`, `D97=26`; Steigungen I94..I96, J94..J96.

### Zeilen 100–108 – Effizienzklassen-Lookup (Ventilatorleistung)
- Leistungsbereiche: `N10:R10` = „bis 1.1 kW", „1.1-2.2", „2.2-11", „11-110", „ab 110 kW".
- Klassenwerte (Zeilen 11–16): IE5: 1/1/1/1/1 („gefaked"); IE4: 0.872/0.895/0.933/0.963/0.967; IE3: 0.85/0.87/0.9/0.94/0.96; IE2: 0.82/0.84/0.88/0.93/0.95; IE1: 0.73/0.78/0.84/0.91/0.94; Eff3: 0.69/0.74/0.81/0.9/0.93.
- `B102 = IF(E$16<1.1,N11,IF(E$16<2.2,O11,IF(E$16<11,P11,IF(E$16<110,Q11,R11))))`; `C102 = IF(E$17=A102,B102,0)`; `C108 = MAX(C102:C107)` → **1** (IST-ZUL-η); `E108` → **1** (IST-ABL-η); `H108` → **0.85** (SOLL-ZUL-η, IE3); `J108` → **0.85** (SOLL-ABL-η).

### Zeilen 109–115 – Filter & Wellen-/Motorleistung
- `B110 = LOOKUP(E14,M28:M44,N28:N44)+LOOKUP(E15,M28:M44,N28:N44)` → 0 Pa (Filterklassen-Druckverlust-Tabelle M27:O44: Soll 0/95/105/125/150/160/180/… Pa für Klassen 0…F9/G1…H14/U15/U16).
- `B112 = B110-B111` → 0; `B113 = K82/3600*B112/(1000*0.75)` → 0 (Pw, Wellenleistung; η_Filter=0.75); `B114 = B113/(0.98*H108)` → 0 (Pm, Motorleistung).
- `F113 = ABS(K70*N20*N23*(E40-E33)/3600)` → **15.956 kW** (Vereisungsschutz-Heizleistung = ṁ·cp·ΔT).

### Weitere Konstanten („Grundlagen", Spalten M–R, Zeilen 17–25)
| Zelle | Wert | Einheit | Bedeutung |
|---|---|---|---|
| N18 | 2 | K | Quellluft: Abluft wärmer als Raumluft (+2 K) |
| N19 | `F:Klimadaten!F44` → **948.226** | mbar | Luftdruck (Standorthöhe) |
| N20 | 1.006 | kJ/kgK | cpl (Wärmekapazität Luft) |
| N21 | 1.86 | kJ/kgK | cpw (Wasserdampf) |
| N22 | 4.19 | kJ/kgK | cw (Wasser) |
| N23 | **1.15** | kg/m³ | Dichte Luft |
| N24 | 2501.6 | kJ/kg | r0 (Verdampfungswärme bei 0 °C) |
| N25 | 2256 | kJ/kg | r100 (Verdampfungswärme bei 100 °C) |
| I29/J29 | 185 | Rp./m³ | Wasserpreis (Bestehend/Optimiert) |
| I26:I28, J26:J28 | leer | Rp./kWh | Energiepreise Elektrizität/Wärme/Kälte (nicht befüllt → Kosten 0) |

### Beschriftungs-Zeichenketten (Spalte S)
`S10 "Quellluft"`, `S16 "keine"`, `S17 "Adiabatisch Bef."`, `S20 "nein"`, `S21 "ja"`, `S23 "vorhanden"`, `S24 "nicht vorhanden"`.

---

## 3. Spaltenkarte des Temperaturklassen-Blocks (IST, Zeilen 121–181; SOLL analog 189–249)

Formelmuster mit Klassenindex `n` (n = 121…181 bzw. 189…249; t_A = −25…+35 °C in 1-K-Schritten). `$E$…`-Bezüge sind IST-Eingaben, `$F$…` SOLL-Eingaben; im SOLL-Block zusätzlich `#REF!` an Stelle von `$N$19` und `$K$82/$P$82/$M$82/$R$82` statt `$K$70/$P$70/$M$70/$R$70` sowie Soll-Kurve `$B$95/$C$95/$I$94` statt `$B$89/$C$89/$I$88`. Zustandsbezeichnungen nach Kopfzeile 117/119.

**Arbeitsbeispiel (Zeile 168, t_A = 22 °C, IST) – vollständige Werte in §3.1.**

| Spalte | Formel (Muster) | Physikalische Größe | Einheit | Zustandspunkt |
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
| Z | `AVERAGE($E$45:$F$46)` → 9 | **Taupunkt Kälteregister (A):** mittlere Kaltwasser-Temperatur (VL/RL) | °C | Kälteregister (A) |
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
| AN | `TemperaturH(AP{n},AO{n})` | t für „Erwärmung vor Befeuchtung" (E): Temperatur bei Zielenthalpie und MIL-x | °C | (E) |
| AO | `IF($E$36=$D$36,R{n},X{n})` | x für Punkt E (= MIL-x) | g/kg | (E) |
| AP | `BM{n}` | Zielenthalpie für Punkt E (= h_ZUL-Soll) | kJ/kg | (E) |
| AQ | `TaupunktA(AR{n},$N$19)` → **#NAME?** | Taupunkttemperatur ZUL bei Entfeuchtung (F) – UDF defekt/auskommentiert | °C | (F) |
| AR | `BL{n}` | x_ZUL-Soll (Eingang für F) | g/kg | (F) |
| AS | `EnthalpieA(AQ{n},AR{n},$N$19)` → **#VALUE!** | h bei F (Fehler fortgepflanzt) | kJ/kg | (F) |
| AT | `BN{n}` | t für „Erwärmung ohne Befeuchtung" (G) = t_ZUL-IST | °C | (G) |
| AU | `IF($E$36=$D$36,R{n},X{n})` | x für G (= MIL-x) | g/kg | (G) |
| AV | `EnthalpieA(AT{n},AU{n},$N$19)` | h bei G | kJ/kg | (G) |
| AW | `IF($E$36=$C$36,IF(AND(ROUND(BM{n},4)>=ROUND(S{n},4),ROUND(BL{n},4)>=ROUND(R{n},4),ROUND(BJ{n},4)>=ROUND(Q{n},4)),1,IF(ROUND(BL{n},4)<ROUND(AA{n},4),2,IF(ROUND(BJ{n},4)>=ROUND(AH{n},4),3,4))),IF(AND(ROUND(BM{n},4)>=ROUND(Y{n},4),ROUND(BL{n},4)>=ROUND(X{n},4),ROUND(BJ{n},4)>=ROUND(W{n},4)),1,IF(ROUND(BL{n},4)<ROUND(AA{n},4),2,IF(ROUND(BJ{n},4)>=ROUND(AH{n},4),3,4))))` | **Fall-Unterscheidung 1–4** (s. §5.4) | 1–4 | – |
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
| BJ | `IF($DA{n}<=$B$89,$C$89-($B$89-$DA{n})*$I$88,IF($DA{n}<=$B$90,$C$90-($B$90-$DA{n})*$I$89,$C$91-($B$91-$DA{n})*$I$90))` | **t_ZUL-Soll** (stückweise lineare Temperaturkurve) | °C | Zuluft soll |
| BK | `MIN(1,RelFeuchte(BJ{n},BT{n},$N$19))` | rF_ZUL-Soll | % | Zuluft soll |
| BL | `AbsFeuchte(BJ{n},BK{n},$N$19)` | **x_ZUL-Soll** | g/kg | Zuluft soll |
| BM | `EnthalpieA(BJ{n},BL{n},$N$19)` | **h_ZUL-Soll** | kJ/kg | Zuluft soll |
| BN | `BB{n}+BD{n}+BF{n}+BH{n}` | **t_ZUL-IST** (Summe der Fallbeiträge) | °C | Zuluft ist |
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
| CF | analog mit CB | **Entfeuchtung-Heizenergie** | MWh | – |
| CG | `IF(OR(AND(A{n}>=$E$26,$E$27>0),AND(A{n}>=$E$26,$E$27<0)),$P$70*B{n}*$N$23*(CD{n})/3.6/1000000,$K$70*B{n}*$N$23*(CD{n})/3.6/1000000)` | **Befeuchtung-Heizenergie** (adiabatisch) | MWh | – |
| CH | `IF($E$36=$D$36,IF(OR(…),MAX(0,(BP{n}-R{n})*B{n}*$P$70*$N$23/1000),MAX(0,(BP{n}-R{n})*B{n}*$K$70*$N$23/1000)),IF(OR(…),MAX(0,(BP{n}-X{n})*B{n}*$P$70*$N$23/1000),MAX(0,(BP{n}-X{n})*B{n}*$K$70*$N$23/1000)))` | **Befeuchtungswasser** | Liter | – |
| CI | `(CH{n}*$N$22*(100-$E$51)+$N$25*CH{n})/3600000` | **Dampfbefeuchter-Energie** (Wasser von E51 auf 100 °C + Verdampfung) | MWh | – |
| CJ | `IF($E$42=$S$21,IF(OR(…),$P$70*B{n}*$N$23*(BZ{n})/3.6/1000000,$K$70*B{n}*$N$23*(BZ{n})/3.6/1000000),0)` | **Kühlenergie** (Luftkühlung) | MWh | – |
| CK | analog mit CC | **Heizenergie** (Lufterwärmung) | MWh | – |
| CL | `IF($E$36=$D$36,IF(OR(…),MAX(0,-(BP{n}-R{n})*B{n}*$P$70*$N$23/1000),MAX(0,-(BP{n}-R{n})*B{n}*$K$70*$N$23/1000)),IF(OR(…),MAX(0,-(BP{n}-X{n})*B{n}*$P$70*$N$23/1000),MAX(0,-(BP{n}-X{n})*B{n}*$K$70*$N$23/1000)))` | **Entfeuchtungswasser** (Kondensat) | Liter | – |
| CM | `IF($E$49=$S$16,0,IF($E$49=$S$17,CG{n},CI{n}))` | **Befeuchtungs-Energie final** (adiabatisch → CG, sonst → CI) | MWh | – |
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
| CX | `-CL{n}` | Entfeuchtungswasser (positiv) | Liter | Diagramm |
| CY | `IF(I{n}=0,CY{n+1},BJ{n})` | t_ZUL-Soll „letzter gültiger Wert" | °C | Diagramm |
| CZ | `IF(I{n}=0,CZ{n+1},BN{n})` | t_ZUL-IST „letzter gültiger Wert" | °C | Diagramm |
| DA | `n-146` (literal, −25…35) | Aussentemperatur (Duplikat von A, Lookup-Schlüssel) | °C | – |
| DB | `IF(A{n}<=$E$33,$F$113,0)` | VS-Leistung „ein/aus" | kW | Vereisungsschutz |
| DC | `IF(A{n}<=$E$33,ABS($K$70*$N$20*$N$23*MIN(ABS(A{n}-$E$33),ABS($E$40-$E$33))/3600),0)` | VS-Leistung „variabel" | kW | Vereisungsschutz |

**Klimadaten-Zuordnung:** Klasse t_A = k °C → Klimadaten-Zeile `k+30` (t_A = −25 → Zeile 5; 22 → Zeile 52; 35 → Zeile 65). Spalten: **O** = Stunden/a, **Q** = absolute Feuchte (g/kg), **N** = relative Feuchte (%), **F44** = Luftdruck (mbar, für N19).

### 3.1 Vollständiges Arbeitsbeispiel: Zeile 168 (t_A = 22 °C)
| Zelle | Wert | Zelle | Wert |
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
| L168 | 22 °C | AW168 | **4** (Kühlen & Befeuchten) |
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

Verifikation: `CT168 = B168*M70/1000 = 59.6575×6.8629/1000 = 0.4094` ✓;
`CJ168 = K70×B168×N23×BZ168/3.6e6 = 3819.23×59.6575×1.15×2.9945/3.6e6 = 0.2179` ✓.

---

## 4. Antriebsdaten (Klimadaten-Verknüpfung) und Stunden-Skalierung

- Klasse n (t_A = k °C): `B{n} = Klimadaten!O{k+30}/8760*$K$68` – Jahresstunden der Klasse, skaliert auf die Volllaststunden der Anlage (K68). Σ B über alle Klassen = K68 = 3900 h.
- `C{n} = Klimadaten!Q{k+30}` (x_AUL g/kg), `D{n} = Klimadaten!N{k+30}` (rF_AUL %, nur Anzeige), `N19 = Klimadaten!F44` (Luftdruck mbar).
- Energie je Klasse = **B × ṁ × Δh** mit ṁ = K70 × N23 (m³/h × kg/m³ = kg/h) und Umrechnung `…/3.6/1000000` (kJ → MWh; 1 MWh = 3.6e6 kJ). Beispiel CE/CJ/CF/CK/CG:
  `K70*B168*N23*(BZ168)/3.6/1000000` → MWh.
- Ventilator: `CT{n} = B{n}*M70/1000` (h × kW / 1000 → MWh).
- Wasser: `CH{n} = (BP{n}-R{n})*B{n}*K70*N23/1000` (g/kg × h × kg/h / 1000 → Liter); `CL{n}` analog mit negativem Vorzeichen (Kondensat).
- Die dV-Sommerlogik wählt per `IF(OR(AND(A>=$E$26,$E$27>0),AND(A>=$E$26,$E$27<0)),$P$70,$K$70)` zwischen Sommer- und Jahresmittel-Volumenstrom; da E27 = 0 und P70 = K70, ist sie hier wirkungslos.

---

## 5. Physik des Modells

### 5.1 Ventilatorleistung (Gebläsegesetz mit Exponent 2.5)
ZUL-Stufenleistungen (Zeile n = 14,15,16; analog ABL 17,18,19 mit E21/E23:E25):
```
I14 = IF(E18<MAX(E19:E20),IF(ISERROR(E16*(E18^2.5)/(E19^2.5)),0,E16*(E18^2.5)/(MAX(E18:E20)^2.5)),E16)
I15 = IF(E19<MAX(E18,E20),IF(ISERROR(E16*(E19^2.5)/(E20^2.5)),0,E16*(E19^2.5)/(MAX(E18:E20)^2.5)),E16)
I16 = IF(E20<MAX(E18:E19),IF(ISERROR(E16*(E20^2.5)/(E20^2.5)),0,E16*(E20^2.5)/(MAX(E18:E20)^2.5)),E16)
```
- Nennleistung E16 = G6/2 (halbe Gesamtleistung für ZUL; ABL E21 = E16).
- Stufen-Volumenströme: Stufe 1 = E7 (100 %), Stufe 2 = 67 %, Stufe 3 = 33 % (nur bei „stufenlos"; „einstufig" → alle Stufen = 100 %).
- **P_Stufe = P_Nenn × (V_Stufe/V_max)^2.5** (Affinitätsgesetz mit Exponent 2.5 statt 3 – Kompromiss für Motorwirkungsgrad; ISERROR-Guard gegen V=0).
- Summe mit Motorwirkungsgrad: `L64 = (I14/C108 + I17/E108)` usw. (C108/E108 = η aus Effizienzklassen-Lookup). Jahres-Ventilatorstrom: `CT182 = Σ CT122:CT181`, `C259 = CT182*1000` kWh, `H7 = C259/1000` MWh.

### 5.2 WRG (Wärmerückgewinnung)
- Fester Wirkungsgrad `$E$28` (0.8). Zustand nach WRG: `I{n} = E28*(BU-A)+A` (Temperatur) und `M{n} = C + (K/E28*E29)*(BW-C)` (Feuchte; E29 = 0 → keine Feuchte-WRG).
- **Regulierter Wirkungsgrad** (Bypass): `K{n} = MAX((J{n}-A{n})/(BU{n}-A{n}),0)` mit `J{n} = MIN(I{n},BJ{n})` – ε wird so reduziert, dass t nach WRG die Zuluft-Solltemperatur nicht überschreitet (Sommer → ε = 0, voller Bypass). Sonderfall: KRG vorhanden (E31=„ja") und Sommer-Flag F=1 → 0. Wenn kein Bypass (E30=„nein"): K = E28 fest.
- t nach WRG mit Bypass: `L{n} = K{n}*(BU-A)+A` (bei E30=„ja"), sonst `I{n}`.

### 5.3 Mischluft (Umluftklappe)
- MIL-Enthalpie (Enthalpie-Regelung): `N{n} = h(L,M)*E35 + (1-E35)*h(BU,BW)`; `O{n}` analog mit E34. Mit E34=E35=1 → MIL = reine Außenluft nach WRG.
- **Umluft-Anteil** (Enthalpieziel S): `P{n} = 1 - (S - h(BU,BW))/(h(L,M) - h(BU,BW))`; `Q{n} = L*(1-P)+BU*P`, `R{n} = M*(1-P)+BW*P`.
- Begrenzung: `S{n} = MIN(MAX(N,BM),O)` – MIL-Enthalpie nicht unter h_ZUL-Soll.
- Temperatur-Regelung analog über T/U/V/W/X/Y (V-Anteil, W begrenzt auf t_ZUL-Soll BJ).
- Abluftzustand = Raumzustand: `BU = BR` (t_Raum aus Raumkurve; Quellluft +2 K), `BW = BT + I20` (x_Raum + Feuchtelast), mit rF_Raum `BS` auf [E50, E48] begrenzt (Feuchte-Sollband; hier [0, 1] = unbegrenzt).

### 5.4 Kälteregister (Entfeuchtung), lineare Kühlkurve, Fälle 1–4
- Register-Zustand (A): `Z = AVERAGE(E45:F46)` = 9 °C (mittlere Kaltwassertemperatur), `AA = MIN(x_sat(9°C,100%), MIL-x)` (Sättigungsfeuchte, begrenzt auf MIL), `AB = h(9,AA)`.
- Lineare Kühlkurve durch (AF=9 °C, AA) und MIL (Q,R bzw. W,X): Steigung `AG = (t_MIL - 9)/(x_MIL - AA)`; Zieltemperatur `AH = MAX(AF+AG*(x_ZUL-Soll - AA), 9)` (D1: Kühlen bis x_ZUL-Soll erreicht).
- D2: `AK = MAX(MIN(t_MIL, t_ZUL-Soll), 9)`, `AL = (t_ZUL-Soll - 9)/AG + AA` (Zustand nach Kühlregister bei Solltemperatur), `AM = h(AK,AL)`.
- **Fall-Detektor** `AW` (mit ROUND(…,4)-Vergleichen gegen Rundungsfehler):
  - Fall 1 (Heizen & Befeuchten): h_ZUL-Soll ≥ h_MIL, x_ZUL-Soll ≥ x_MIL, t_ZUL-Soll ≥ t_MIL.
  - Fall 2 (Entfeuchten & Heizen): x_ZUL-Soll < x_Register (Muss entfeuchtet werden).
  - Fall 3 (Kühlen & ggf. Entfeuchten-Heizen): t_ZUL-Soll ≥ t_D1 (nur Kühlen, kein Nachheizen nötig).
  - Fall 4 (Kühlen & Befeuchten): sonst (nach Kühlung zu trocken → befeuchten).
- ZUL-IST aus UDFs `Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul` (BB–BE) bzw. Inline-IFs (BF–BI): `BN = BB+BD+BF+BH`, `BP = BC+BE+BG+BI`.
- **Enthalpiedifferenzen (kJ/kg):**
  - `BZ` (Kühlen) = S − AM bzw. Y − AM (MIL → D2), Fälle 2/3/4.
  - `CA` (Entf./Kühlen) = AM − AJ (D2→D1, Fall 3) bzw. S − AB − BZ (Fall 2: Rest nach Entfeuchtung).
  - `CB` (Entf./Heizen) = BQ − AJ (Fall 3) bzw. BQ − AB (Fall 2) – Nachheizen auf t_ZUL.
  - `CC` (Heizen) = AV − S (Fall 1: MIL → G), bei F=1 (Sommer) = 0.
  - `CD` (Heizen Bef.) = BQ − AV (Fall 1/4: G → ZUL-IST, adiabate Befeuchtung).
  - `BX = BZ+CA`, `BY = CB+CC+CD`.

### 5.5 Energien (MWh je Klasse) und Wasser
- Kühlen: `CJ = K70·B·N23·BZ/3.6e6`; Entf.-Kühlen: `CE = …·CA/3.6e6`; Heizen: `CK = …·CC/3.6e6`; Entf.-Heizen: `CF = …·CB/3.6e6`; Bef.-Heizen (adiabatisch): `CG = …·CD/3.6e6`.
- Dampfbefeuchtung: `CI = (CH·N22·(100−E51) + N25·CH)/3.6e6` (Wasser von E51=10 °C auf 100 °C erhitzen + Verdampfen mit r100=2256).
- Finale Befeuchtungsenergie: `CM = CG` (adiabatisch, E49=S17) bzw. `CI` (sonst).
- Befeuchtungswasser: `CH = MAX(0,(x_ZUL-IST − x_MIL)·B·K70·N23/1000)` Liter; Kondensat `CL = −MAX(0,(x_MIL − x_ZUL-IST)·…)` Liter, `CX = −CL`.
- Ventilator: `CT = B·M70/1000` MWh.
- Gesamt je Klasse: `CW = CK+CJ+CE+CF+CM+CT`.

### 5.6 IST vs. SOLL Steuerlogik
- Der Vergleich `$E$36=$D$36` („Temperatur" vs. leer) schaltet zwischen enthalpiegeregelter (Zweig 2, aktiv) und temperaturgeregelter Mischluftberechnung. Da D36 leer ist, ist immer Zweig 2 aktiv (X-basiert).
- `$E$36=$C$36` im Fall-Detektor AW wählt S-basierte (aktiv) vs. Y-basierte Vergleiche.
- Der SOLL-Block (189–249) bildet dieselbe Logik mit `$F$`-Eingaben und Soll-Temperaturkurve ab, ist aber in dieser Datei inaktiv (B/C/D = 0, #REF!, K82… = 0).

### 5.7 Summation in die Ergebniszeilen
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
und dann: `C254 = CJ182*1000` (kWh), `D254 = BZ183` (kW), …, `C259 = CT182*1000`, `D259 = G6`; Zeile 7: `Q7 = C254/1000` (MWh), `P7 = D254`, … `H7 = C259/1000` (MWh). SOLL analog über Zeile 250 (alle 0).

---

## 6. Ergebniszeilen (254–328)

| Zelle | Formel | Ergebnis | Bedeutung |
|---|---|---|---|
| A254 | Luftkühlung | – | Abschnittstitel |
| C254 | `IFERROR(CJ182*1000,0)` | 1750.16 kWh | **Jahres-Kühlenergie** (Nutzenergie) |
| D254 | `BZ183` | 25.78 kW | Kühlleistung (max.) |
| E254 | `IFERROR(CJ250*1000,0)` | 0 | SOLL-Kühlenergie |
| F254 | `IFERROR(E254*J28/100,0)` | 0 | Kühlkosten CHF/a (Preis J28 leer) |
| A255 | Lufterwärmung | – | |
| C255 | `IFERROR(CK182*1000,0)` | 3786.30 kWh | **Jahres-Heizenergie** |
| D255 | `CC183` | 16.15 kW | Heizleistung (max.) |
| E255/F255 | analog (CK250 / J27) | 0 | SOLL/Kosten |
| A256 | Erwärmung Bef. | – | |
| C256 | `IFERROR(CM182*1000,0)` | −3.25e-12 kWh | **Jahres-Befeuchtungs-Heizenergie** (≈0) |
| D256 | `CD183` | 3.9e-14 kW | Leistung (≈0) |
| A257 | Entfeuchtung (Kühlung Entf.) | | |
| C257 | `IFERROR(CE182*1000,0)` | 0 | **Jahres-Entfeuchtungskühlenergie** |
| D257 | `CA183` | 0 | Leistung |
| B258 | Erwärmung Entf. | | |
| C258 | `IFERROR(CF182*1000,0)` | 0 | **Jahres-Entfeuchtungsheizenergie** |
| D258 | `CB183` | 0 | Leistung |
| A259 | Luftumwälzung / Ventilator | | |
| C259 | `IFERROR(CT182*1000,0)` | 26765.14 kWh | **Jahres-Ventilatorstrom** |
| D259 | `G6` | 6.863 kW | Ventilatorleistung |
| E259/F259 | analog (CT250 / J26) | 0 | SOLL/Kosten |
| A260 | Total | | |
| C260 | `SUM(C254:C259)` | 32301.60 kWh | Gesamt-Nutzenergie |
| D260 | `SUM(D254:D259)` | 48.80 kW | Gesamtleistung |
| E260/F260 | Summen | 0 | |
| A262 | Wasser Bef. | | |
| C262 | `IFERROR(CH182,0)` | ~1e-11 Liter/a | Befeuchtungswasser |
| D262 | `IFERROR(C262/1000*I29/100,0)` | ~0 | Wasserkosten (185 Rp./m³) |
| A263 | Entfeuchtung | | |
| C263 | `IFERROR(CL182,0)` | ~9e-12 Liter/a | Kondensat |
| H253 | `LOOKUP(B88,$DA$122:$DA$181,$BU$122:$BU$181)` | 22 °C | t_Abluft bei t_A=−15 (Diagramm) |
| I253 | `LOOKUP(B88,$DA$122:$DA$181,$BS$122:$BS$181)` | 0 | rF_Raum bei −15 °C |
| J253 | `AbsFeuchte(D88,I253,$N$19)` | 0.196 g/kg | x_Raum bei −15 °C |
| H254:J262 | LOOKUPs gegen DA/BU bzw. DA/BS (SOLL-Kurven 190:249 ab H259) | – | Diagramm-Stützpunkte |
| A264–A265 | „Daten für HG/KG" / „Tab" | – | Abschnittstitel |
| H265:N265 | `Begriffe!F152:F158` | Aussentemperatur, Luftförderung, Lufterwärmung, Erwärmung Befeuchtung, Luftkühlung, Kühlung Entfeuchtung, Erwärmung Entfeuchtung | Diagramm-Legende |
| **267–327** (je Klasse k = −25…35) | | | |
| B | `IFERROR((CK{k+30}+CF{k+30})*1000/Klimadaten!O{k+30},0)` | 0 | Heizleistung IST kW (Energie/Stunden – geteilt durch Klimadaten-Stunden, nicht B!) |
| C | analog mit CK189+CF189 | 0 | Heizleistung SOLL |
| D | `IFERROR((CE+CJ)*1000/O,0)` | 0 | Kühlleistung IST |
| E | analog (CE189+CJ189) | 0 | Kühlleistung SOLL |
| H | `=A` | – | t_A |
| I | `CT*1000` | – | Ventilator kWh |
| J | `CK*1000` | – | Heizen kWh |
| K | `CM*1000` | – | Bef.-Heizen kWh |
| L | `CJ*1000` | – | Kühlen kWh |
| M | `CE*1000` | – | Entf.-Kühlen kWh |
| N | `CF*1000` | – | Entf.-Heizen kWh |
| O | `BN` | – | t_ZUL-IST °C |
| P | `BO*100` | – | rF_ZUL-IST % |
| H328 | Total | | |
| I328 | `SUM(I267:I327)` | 26765.14 kWh | Ventilator |
| J328 | `SUM(J267:J327)` | 3786.30 kWh | Heizen |
| K328 | `SUM(K267:K327)` | ≈0 | Bef.-Heizen |
| L328 | `SUM(L267:L327)` | 1750.16 kWh | Kühlen |
| M328 | `SUM(M267:M327)` | 0 | Entf.-Kühlen |
| N328 | `SUM(N267:N327)` | 0 | Entf.-Heizen |

### Geforderte Schlüsseladressen
- **(a) Jahres-Endenergien je Behandlungsstufe (entsprechen Lüftung!Q32…Z32):** `C254` (Luftkühlung, kWh), `C255` (Lufterwärmung), `C256` (Erwärmung Befeuchtung), `C257` (Entfeuchtung Kühlung), `C258` (Entfeuchtung Erwärmung), `C259` (Ventilator). MWh-Äquivalente in Zeile 7: `Q7=C254/1000`, `S7=C255/1000`, `U7=C256/1000`, `W7=C257/1000`, `Y7=C258/1000`, `H7=C259/1000`. Leistungen: `D254…D258` (bzw. `P7,R7,T7,V7,X7`). Die exakte Spaltenzuordnung von Lüftung!Q32…Z32 muss am Lüftung-Dump verifiziert werden.
- **(b) Ventilator-Energiezelle:** `C259` (kWh) bzw. `H7` (MWh); Leistung `G6`/`D259`; Jahresmittel `M70`.
- **(c) Volllaststunden-Zelle:** `K68` (3900 h, aus `Std!$Q$6:$V$50` per MATCH auf `B6`); `K69` (Elektrizität, 3900); berechnete Kontrolle `J7 = ROUND(IF(G6=0,0,H7*1000/G6),-1)`; `J6 = K68`.

---

## 7. Fehler / tote Zellen

| Zelle(n) | Fehler | Ursache / Bedeutung |
|---|---|---|
| `AQ121…AQ249` (122 Zellen, beide Blöcke) | `#NAME?` | `TaupunktA(x,p)`-UDF ist definiert aber auskommentiert/nicht registriert → Zellwert ist Fehler. |
| `AS121…AS249` (122 Zellen) | `#VALUE!` | `EnthalpieA(AQ,AR,$N$19)` mit Fehler-Eingang AQ → fortgepflanzt. |
| `J11` | `#N/A` | SOLL-Statusformel: OR-Ausdruck enthält `F40<0` mit F40=#N/A → #N/A. |
| `F40` | `#N/A` | SOLL-Auslegungstemperatur (leere Formelabhängigkeit, cached error). |
| SOLL-Block N/O/P/V/Z/AA/AB/… | `#REF!`-Teilausdrücke | `EnthalpieA(L,M,#REF!)` – die SOLL-Kopien verloren den `$N$19`-Druckbezug (Ergebnisse trotzdem rechnerisch korrekt, weil #REF!-Argumente nur in den toten Enthalpie-Zwischenzellen stehen; die R:-Werte zeigen plausible Zahlen, da der Cached-Wert offenbar mit gültigem Druck berechnet wurde – Achtung: Formeltext ≠ berechneter Wert). |

Keine `#DIV/0!` im aktuellen Stand (durch ISERROR/IFERROR/IF-Guards abgefangen; siehe §8).

---

## 8. Annahmen & Eigenheiten

**Konstanten:** cpl = 1.006 (N20), cpw = 1.86 (N21), cw = 4.19 (N22), ρ = 1.15 kg/m³ (N23), r0 = 2501.6 (N24), r100 = 2256 (N25), Luftdruck 948.2 mbar (N19 aus Klimadaten!F44), Quellluft-Zuschlag 2 K (N18), 3600 s/h (3.6e6 kJ/MWh), 8760 h/a, Kaltwassertemperatur 10 °C (E51).

**Eigenheiten / Quirks:**
1. **Gebläsegesetz mit Exponent 2.5** (statt 3) in I14:I19.
2. **Summen beginnen bei Zeile 122** – die Klasse −25 °C (Zeile 121) ist von allen Energiesummen (`CE182…CT182`, `CE250…CT250`) ausgeschlossen (B121=0, daher hier ohne Auswirkung).
3. **`CC183 = MAX(CC$133:CC$181)…`** – Heizleistungsmaximum ab Zeile 133 (−10 °C), nicht ab 121.
4. **`T{n} = MIN(…einfaches Argument…)`** – MIN() ohne zweites Argument ist ein No-op (Temperaturregelungs-Zwischenwert).
5. **AD-Spalte** ist eine literal fortlaufende Scratch-Spalte (−1…59) nur für AE (das seinerseits nirgends referenziert wird) – vermutlich Altlast/Diagrammhilfe.
6. **D-Spalte (rF_AUL aus Klimadaten!N)** wird von keiner Formel referenziert (nur Anzeige); die effektive Raum-rF wird in E über `RelFeuchte(BR, C, p)` neu berechnet.
7. **222/−222-Guards** in CN…CV für Diagramme (Ausblendung bei B=0 oder E=0); `1E+23` in AG gegen senkrechte Kühlkurve.
8. **ROUND(…,4)-Vergleiche** im Fall-Detektor AW gegen Gleitkomma-Artefakte.
9. **Energiepreise** (I26:I28, J26:J28) sind leer → alle Kosten (F254:F259) = 0; nur Wasserpreis 185 Rp./m³ (I29/J29) belegt.
10. **Betriebszeiten-Block** (L58:L61, 80 h/Woche) geht nicht direkt in die Energie-Summen ein – die Jahresstunden kommen aus `K68` (Std-Lookup 3900 h); die Stufen-Anteile M58:M60 fließen nur in die gewichteten Stufenleistungen/-ströme (K64:M67) und die Plausibilitätswerte.
11. **Diagramm-Leistungen** (B267:D327) dividieren durch `Klimadaten!O{k+30}` (Klimastunden), nicht durch die skalierten Betriebsstunden B – die „kW"-Kurven sind also bezogen auf reale Jahresstunden.
12. **SOLL-Block inaktiv:** Klimadaten-Zellen literal 0, `#REF!`-Druck, K82/M82/P82/R82 = 0 → alle SOLL-Energien 0; Befeuchtungstyp SOLL „keine" (F49) und Entfeuchtung „nein" (F47) deaktivieren die entsprechenden Terme zusätzlich.
13. **UDF-Abhängigkeiten:** `EnthalpieA`, `AbsFeuchte`, `RelFeuchte`, `TemperaturH`, `Fall1Tzul`, `Fall1xzul`, `Fall2Tzul`, `Fall2xzul`, `LUET`, `LUEAB` (Doku in A184/D184); `TaupunktA` defekt (#NAME?).
14. **`E41`/`E44` (installierte Registerleistungen)** sind leer – nur Status-Checks (I11) und Design-Temperaturen (E40/E43) sind belegt; die Jahresrechnung benötigt sie nicht.
15. **Frischluftanteil E34/E35 = 1** → keine Umluftmischung (MIL = Außenluft nach WRG); die Umluft-Anteile P/V ergeben 0.
16. **WRG-Bypass** (E30=„ja") macht den regulierten Wirkungsgrad K wirksam; im Sommer (t_A ≥ t_ZUL) fällt K auf 0 (voller Bypass), im Winter bleibt K = E28 = 0.8.
17. **Raum-/Abluftmodell:** Abluft = Raumzustand aus Temperaturkurve + Klima-rF, begrenzt auf das Feuchte-Sollband [E50, E48] – d. h. die Abluft „erbt" die Außenfeuchte, was bei N6=O6=0 (Band [0,1]) zu identischen x_Raum = x_AUL führt.
18. **Feuchtelast I20/J20** = 0 (E52=0) → Abluft-x = Raum-x.
19. Das Blatt rechnet **eine Anlage pro Instanz**; die 16er-Struktur (LA01…LA16) entsteht über Makro-Kopien der Lüftung-Zeile 32, nicht über Zeilen 7–22 hier.

---

## Zusammenfassung der Rechenkette (Kurzform für das Kapitel)

t_A (Klimadaten) → Stunden B = O/8760·K68 → AUL-Zustand (C, E) → WRG (I, K, L, M) → MIL (N…Y, Umluftklappe) → Kälteregister A/C + lineare Kühlkurve (Z…AM) → Fall 1–4 (AW) → ZUL-IST (BN, BP) → Enthalpiedifferenzen (BZ…CD) → Energien (CE…CM, CT) → Summen (Zeile 182) → kWh-Ergebnisse (C254…C259) → Zeile 7 (P7…Y7, H7) → Lüftung.

---

*Hinweis zur Erstellung (2026-08-20, Merge der Dokumentbäume):* die Analyse basiert auf
`sheet_61_Berechnung LU.tsv` (vollständig gelesen in Chunks) mit numerischer Gegenrechnung
(CT168, CJ168, K168, K121, CJ182→C254→Q7, C259→H7, J7, K70/M70, I88/J88), Konsistenz ΣB = K68 und
der Klimadaten-Zuordnung t_A+30. Offene Detailfragen sind in Kapitel 4 des Lehrbuchs
(README §0.7 und ch04 §4.14) überführt: Lüftung!Q32…Z32-Zuordnung (ch04 §4.12/4.14-8),
`TaupunktA`-Defekt (ch01 §1.7), Summenstart Zeile 122 / CC183 ab Zeile 133 (ch04 §4.14-2), SOLL-
Block-Schlafzustand (ch04 §4.14-3).
