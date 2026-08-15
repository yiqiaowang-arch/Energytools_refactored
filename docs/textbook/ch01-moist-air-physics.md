# Chapter 1 — Moist-Air Physics: Glück Polynomials and the 8 UDFs

> Code source: `.analysis/vba/gebaeude/FeuchteLuft_Formeln.bas` (module `FeuchteLuft_Formeln`)
> Call sites: `Klimadaten!Q5:Q65`, `Berechnung LU` temperature-interval rows (columns E, N, O, P, Y, AA, AB, AE, AJ, AM, AN, AQ, AS, AV, BK, BL, BM, BO, BQ, BT, BV, etc.; see Chapter 4)

This chapter presents all of Gebäude-Tool's moist-air state-variable formulas: saturation vapour pressure (Glück polynomial), humidity ratio, enthalpy, relative humidity, dew point, enthalpy-inverted temperature, and the empirical wet-bulb temperature approximation. For each formula it gives the derivation, units, assumptions, range of validity, and the call sites in the workbook (cell provenance).

## 1.1 Module Overview: the 8 UDFs

`FeuchteLuft_Formeln.bas` defines 8 usable `Public Function`s (the 9th, `TaupunktA`, is commented out in its entirety — dead code, but `Berechnung LU` still references it; see §1.8):

| # | UDF | Signature (units in comments) | Return | Referenced by workbook formulas? |
|---|---|---|---|---|
| 1 | `Saettigungsdruck` | `(T)` T[°C] | Saturation pressure [mbar] | No (dead code; the polynomial is inlined in other functions) |
| 2 | `AbsFeuchte` | `(T, rF, p)` T[°C], rF[%], p[mbar] | Humidity ratio [g/kg] | **Yes**: `Klimadaten!Q5:Q65`, `Berechnung LU!AA{n}, BL{n}` |
| 3 | `EnthalpieA` | `(T, x, p)` T[°C], x[g/kg], p[mbar] | Enthalpy [kJ/kg] | **Yes**: used extensively in `Berechnung LU` (columns N, O, Y, AB, AE, AJ, AM, AS, AV, BM, BQ) |
| 4 | `EnthalpieR` | `(T, rF, p)` T[°C], rF[%], p[mbar] | Enthalpy [kJ/kg] | No (dead code) |
| 5 | `TaupunktR` | `(T, rF, p)` | Dew point [°C] | No (dead code) |
| 6 | `RelFeuchte` | `(T, x, p)` T[°C], x[g/kg], p[mbar] | Relative humidity [–] (the formula returns a decimal) | **Yes**: `Berechnung LU!E{n}, BK{n}, BO{n}, BV{n}` |
| 7 | `TemperaturH` | `(h, xein)` h[kJ/kg], x[g/kg] | Temperature [°C] | **Yes**: `Berechnung LU!AN{n}` |
| 8 | `Feuchtkugel` | `(Tein, rFein)` T[°C], rF[%] | Wet-bulb temperature [°C] | No (dead code) |
| (9) | `TaupunktA` (commented out) | `(x, p)` x[g/kg], p[mbar] | Dew point [°C] | Referenced but `#NAME?` (see §1.8) |

**Module-level constants** (redefined identically inside every function):

| Symbol | Value | Unit | Meaning |
|---|---|---|---|
| `cpl` | 1.006 | kJ/(kg·K) | Specific heat of dry air (atmospheric pressure) |
| `cpw` | 1.86 | kJ/(kg·K) | Specific heat of water vapour (atmospheric pressure) |
| `r0` | 2501.6 | kJ/kg | Latent heat of vaporisation of water at 0 °C |
| 622 | – | – | Molar-mass ratio water/dry air × 1000 (0.622×1000; see derivation in §1.3) |
| 611 | Pa | – | Triple-point pressure of water (611 Pa ≈ 6.11 mbar) |

## 1.2 Formula 1 — Saturation Vapour Pressure (Glück Polynomial)

**Mathematical form** (Glück polynomial, piecewise):

$$
p_s(T) = \frac{611}{100}\cdot\exp\!\big(a_0 + a_1 T + a_2 T^2 + a_3 T^3 + a_4 T^4\big) \quad[\mathrm{mbar}],\quad T \text{ in }[°C]
$$

- Over ice ($T \le 0$): $a = (−4.909965\!\times\!10^{-4},\; 8.183197\!\times\!10^{-2},\; −5.552967\!\times\!10^{-4},\; −2.228376\!\times\!10^{-5},\; −6.211808\!\times\!10^{-7})$
- Over water ($T > 0$): $a = (−1.91275\!\times\!10^{-4},\; 7.258\!\times\!10^{-2},\; −2.939\!\times\!10^{-4},\; 9.841\!\times\!10^{-7},\; −1.92\!\times\!10^{-9})$

**Workbook implementation** (verbatim VBA, inlined in three functions; excerpt from `Saettigungsdruck`):

```vba
If T <= 0 Then
    ps = 611 * Exp(-4.909965 * 10 ^ -4 + 8.183197 * 10 ^ -2 * T - 5.552967 * 10 ^ -4 * T ^ 2 _
        - 2.228376 * 10 ^ -5 * T ^ 3 - 6.211808 * 10 ^ -7 * T ^ 4) / 100
ElseIf T > 0 Then
    ps = 611 * Exp(-1.91275 * 10 ^ -4 + 7.258 * 10 ^ -2 * T - 2.939 * 10 ^ -4 * T ^ 2 _
        + 9.841 * 10 ^ -7 * T ^ 3 - 1.92 * 10 ^ -9 * T ^ 4) / 100
End If
```

**Units**: `T` [°C]; returns `ps` [mbar] (611 [Pa] ÷ 100 = 6.11 [mbar], i.e. the triple-point pressure 611 Pa converted to mbar).

**Derivation**: the saturation vapour pressure is the integral result of the Clausius–Clapeyron equation $d\ln p_s/dT = r/(R_w T^2)$, whose exact solution must be tabulated (e.g. IAPWS-IF97). The Glück polynomial is a least-squares quartic fit of the IAPWS/VDI tabulated data over −20…+60 °C (ice branch −60…0 °C), given in the form $\ln p_s = \sum a_i T^i$, so that the error is < 0.1 %. 611 Pa is the triple-point pressure of water (at 0.01 °C), which keeps the two branches continuous around $T=0$ (the constant terms of the two branches at T=0, −4.9×10⁻⁴ and −1.9×10⁻⁴, are nearly equal; the jump is on the order of 0.03 %).

**Assumptions**: ① moist air is an ideal-gas mixture; ② the saturation pressure depends only on temperature (the Poynting correction of the total pressure on $p_s$ is neglected — acceptable for low-pressure HVAC applications); ③ the polynomial coefficients follow Glück's fit (workbook comment "nach Glück"), deviating from VDI 4670 or ASHRAE values within engineering accuracy.

**Range of validity**: $-25 \ldots +35$ °C (the range actually used by Gebäude-Tool; at lower temperatures the ice-branch polynomial may diverge — do not extrapolate); pressure 850–1030 mbar (Swiss station pressure range).

**Cell provenance**: function `FeuchteLuft_Formeln.Saettigungsdruck`; the polynomial is copied inline into `AbsFeuchte`, `RelFeuchte`, `EnthalpieR`; `Klimadaten!Q5:Q65` and the humidity-ratio columns of `Berechnung LU` use it indirectly through these functions. **No** workbook formula calls `Saettigungsdruck()` directly (the polynomial appears only via the inlined path).

## 1.3 Formula 2 — Humidity Ratio (Absolute Humidity) `AbsFeuchte`

**Mathematical form**:

$$
x = \frac{622\,\varphi\, p_s(T)}{p - \varphi\, p_s(T)} \quad [\mathrm{g/kg}]
$$

Here $\varphi$ is passed as a decimal (0–1) (as actually used at the call sites; the VBA comment says `rF [%]`; see §1.9).

**Workbook implementation**:

```vba
'Glück polynomial → ps [mbar]
AbsFeuchte = (rF * 622 * ps) / (p - rF * ps)      ' [g/kg]
```

Call example: `Klimadaten!Q20: =AbsFeuchte(M20,N20,$F$44)` (T=−10 °C, φ=0.8817, p=948.2 mbar → 1.5015 g/kg).

**Units**: `T` [°C], `φ` [–], `p`, `ps` [mbar]; returns `x` [g/kg].

**Derivation**: from Dalton's law of partial pressures and the ideal-gas law, the water-vapour partial pressure is $p_v = \varphi p_s$; the dry-air partial pressure is $p_{da} = p - p_v$; the mass ratio:

$$
x = \frac{m_v}{m_{da}} = \frac{p_v M_v}{p_{da} M_{da}} = \frac{M_v}{M_{da}}\cdot\frac{\varphi p_s}{p-\varphi p_s} = 0.622\cdot\frac{\varphi p_s}{p-\varphi p_s}\ [\mathrm{kg/kg}]
$$

where $M_v/M_{da} = 18.015/28.966 = 0.622$. Multiplying by 1000 gives g/kg: $x = 622\,\varphi p_s/(p-\varphi p_s)$.

**Assumptions**: ideal gas; molar mass of water vapour 18.015 g/mol, of dry air 28.966 g/mol; the effect of air dissolved in water is neglected.

**Range of validity**: $\varphi\in[0,1)$ (as $\varphi\to 1$, $x\to x_s$, the saturation value); $p > \varphi p_s$ always holds (normal atmospheric conditions); temperature range as above. Note: if $\varphi$ is mistakenly passed as a percentage (e.g. 88), the result is inflated by a factor of 100 — in the workbook, the `Klimadaten!N` column and the `Berechnung LU` call sites all pass a decimal.

**Cell provenance**: defined in `FeuchteLuft_Formeln.bas`; call sites: `Klimadaten!Q5:Q65` (61 temperature intervals), `Berechnung LU!AA{n}` (`=IF($E$36=$D$36,MIN(AbsFeuchte(Z{n},100%,$N$19),R{n}),MIN(AbsFeuchte(Z{n},100%,$N$19),X{n}))`, where `100%`=1, i.e. the saturation humidity ratio, and taking the min yields the dew-point limiting), `Berechnung LU!BL{n}` (`=AbsFeuchte(BJ{n},BK{n},$N$19)`). Note that in `AA{n}` `100%` is passed as the decimal 1, confirming the calling convention again.

## 1.4 Formula 3 — Enthalpy of Moist Air `EnthalpieA`

**Mathematical form**:

$$
h = c_{pl}\,T + \frac{x}{1000}\big(r_0 + c_{pw}\,T\big) \quad [\mathrm{kJ/kg}]
$$

**Workbook implementation**:

```vba
EnthalpieA = cpl * T + x / 1000 * (r0 + cpw * T)   ' x [g/kg]
```

**Units**: `T` [°C], `x` [g/kg] (internally ÷1000 converts to kg/kg), `p` [mbar] (**unused**; kept only for a signature consistent with `EnthalpieR`); returns `h` [kJ/kg].

**Derivation**: with 0 °C dry air and 0 °C liquid water as the enthalpy datum (HVAC convention; reference state 0 °C, 0 kJ/kg):

$$
h = \underbrace{c_{pl}T}_{\text{sensible heat of dry air}} + \underbrace{\frac{x}{1000}\big(\underbrace{r_0}_{\text{latent heat at 0 °C}} + \underbrace{c_{pw}T}_{\text{sensible heat of water vapour}}\big)}_{\text{enthalpy of water vapour}}
$$

i.e. $h = c_{pl}T + x_{kg}(r_0 + c_{pw}T)$. Above 0 °C: $r_0 + c_{pw}T$ is the enthalpy of water vapour at T (latent + sensible heat); below 0 °C the sublimation heat of ice is about 2834 kJ/kg, which this formula approximates with 2501.6 (the error grows as the temperature drops; see range of validity).

**Assumptions**: ① the specific heats are constant, $c_{pl}=1.006$, $c_{pw}=1.86$ kJ/(kg·K) (variation < 1 % over 0–60 °C); ② the latent heat of vaporisation takes its 0 °C value $r_0=2501.6$ kJ/kg (ideal-gas approximation for water vapour; the actual $r$ decreases roughly linearly with temperature by about −2.4 kJ/(kg·K), giving an error ≤ 4 % over 0–40 °C); ③ reference state 0 °C.

**Range of validity**: HVAC conditions −20…+60 °C; humidity ratio 0–30 g/kg; below 0 °C recommended only as an engineering approximation (differences of the ice phase transition are neglected).

**Cell provenance**: defined in `FeuchteLuft_Formeln.bas`; call sites (all in `Berechnung LU`, interval rows n=33…253, example n=121):
- `N{n}` / `O{n}`: `=EnthalpieA(L{n},M{n},$N$19)*$E$35+(1-$E$35)*EnthalpieA(BU{n},BW{n},$N$19)` (MIL enthalpy, winter/summer WRG efficiencies E35/E34)
- `Y{n}`: `=EnthalpieA(W{n},X{n},$N$19)` (enthalpy of the state after the KRG)
- `AB{n}`: `=EnthalpieA(Z{n},AA{n},$N$19)`; `AE{n}`: `=EnthalpieA(AC{n},AD{n},$N$19)`
- `AJ{n}`, `AM{n}`: enthalpy after the coils; `AV{n}`: `=EnthalpieA(AT{n},AU{n},$N$19)`
- `AS{n}`: `=EnthalpieA(AQ{n},AR{n},$N$19)` (cascades to `#VALUE!` because column AQ's `TaupunktA` errors; not part of any result)
- `BM{n}`, `BQ{n}`: `=EnthalpieA(BJ{n},BL{n},$N$19)`, `=EnthalpieA(BN{n},BP{n},$N$19)`

## 1.5 Formula 4 — Enthalpy-Inverted Temperature `TemperaturH`

**Mathematical form** (inverse of Formula 3):

$$
T = \frac{h - \dfrac{x}{1000}\,r_0}{c_{pl} + \dfrac{x}{1000}\,c_{pw}} \quad [°C]
$$

**Workbook implementation**:

```vba
x = xein / 1000            ' g/kg → kg/kg
TemperaturH = (h - x * r0) / (cpl + cpw * x)
```

**Units**: `h` [kJ/kg], `xein` [g/kg]; returns [°C].

**Derivation**: solving $h = c_{pl}T + x_{kg}(r_0 + c_{pw}T)$ for $T$: $h - x_{kg}r_0 = T(c_{pl} + x_{kg}c_{pw})$, i.e. the formula above. Geometrically this is the intersection of the isoenthalpy line in the $h$–$x$ diagram (slope $1/(c_{pl}+x c_{pw})$) with the temperature axis.

**Assumptions**: same as `EnthalpieA` (constant specific heat, constant latent heat).

**Range of validity**: enthalpy values corresponding to −20…+60 °C; humidity ratio 0–30 g/kg; when `h < x·r0/1000` it returns a negative temperature (physically impossible; the call sites should already guarantee this via upstream states).

**Cell provenance**: `Berechnung LU!AN{n}`: `=TemperaturH(AP{n},AO{n})` (temperature after the heating section E, inverted from enthalpy AP and humidity ratio AO); example n=121: `TemperaturH(12.2406, 8.19…) → 21.27 °C`.

## 1.6 Formula 5 — Relative Humidity `RelFeuchte`

**Mathematical form**:

$$
\varphi = \frac{x\,p}{p_s(T)\,(622 + x)} \quad [–]
$$

**Workbook implementation**:

```vba
'Glück polynomial → ps [mbar]
RelFeuchte = (x * p) / (ps * (622 + x))
```

**Units**: `x` [g/kg], `p`, `ps` [mbar]; returns a decimal (0–1). Note: at the `Berechnung LU` call sites the value is clamped with `MIN(100%, …)`/`MIN(1, …)`, confirming the return value is a decimal.

**Derivation**: inverting Formula 2: $x(622+x)^{-1} = \varphi p_s/p \Rightarrow \varphi = xp/\big(p_s(622+x)\big)$. This is the algebraic inverse of $x = 622\varphi p_s/(p-\varphi p_s)$.

**Assumptions**: same as Formula 2.

**Range of validity**: $\varphi\in[0,1]$; the call sites usually combine it with `MIN` as a saturation clamp (`MIN(1, RelFeuchte(...))`) to avoid supersaturated (fog) states.

**Cell provenance**: `Berechnung LU!E{n}`: `=MIN(100%,RelFeuchte(BR{n},C{n},$N$19))` (relative humidity of the outdoor air for interval n; BR = outdoor enthalpy/humidity state); `BK{n}`: `=MIN(1,RelFeuchte(BJ{n},BT{n},$N$19))`; `BO{n}`: `=MIN(1,RelFeuchte(BN{n},BP{n},$N$19))`; `BV{n}`: `=RelFeuchte(BU{n},BW{n},$N$19)` (Abluft state).

## 1.7 Formula 6 — Dew Point `TaupunktR` (and Dead Code `TaupunktA`)

**Mathematical form**: first compute the humidity ratio (Formula 2), then the dew-point partial pressure and dew-point temperature:

$$
p_{st} = \frac{p}{\dfrac{0.622\cdot1000}{x}+1} = \frac{p\,x}{622+x} \quad[\mathrm{mbar}]
$$

$$
T_d = \Big(\big(p_{st}/2.8858\big)^{1/8.02} - 1.098\Big)\cdot 100 \quad[°C]
$$

**Workbook implementation**:

```vba
x = AbsFeuchte(T, rF, p)
pst = p / (0.622 * 1000 / x + 1)
TaupunktR = ((pst / 2.8858) ^ (1 / 8.02) - 1.098) * 100
```

**Units**: `pst` [mbar], `x` [g/kg]; returns [°C].

**Derivation**: ① Dew-point partial pressure: the dew-point temperature is defined as the temperature at which air with humidity ratio x cools to saturation ($\varphi=1$), hence $p_{st} = p_v = \varphi p_s$; inverting Formula 2 gives $p_v = xp/(622+x)$ (consistent with the formula above; note $0.622\cdot1000/x$ is $622/x$). ② Dew-point temperature: a **different empirical saturation-pressure fit** is used (not the Glück polynomial):

$$
p_s(T) = 2.8858\,(T/100 + 1.098)^{8.02} \quad[\mathrm{mbar}]
$$

Its inverse is the formula above. Check: $T=0$: $p_s=2.8858\cdot1.098^{8.02}\approx6.02$ mbar (true value 6.11, deviation 1.5 %); $T=20$: ≈24.9 mbar (true value 23.4, deviation 6 %). Within the HVAC dew-point range (−20…+30 °C) this fit is an engineering approximation, less accurate than the Glück polynomial, and it is inconsistent with the other functions in the module (two $p_s$ models coexist).

**Assumptions**: ideal gas; $p_s$ uses the power-law fit above; humidity ratio in g/kg.

**Range of validity**: dew point −20…+30 °C; $p_{st} > 0$ (x>0). **Note**: the function exists only in `TaupunktR` (dead code) and the commented-out `TaupunktA`.

**Cell provenance**: `TaupunktA` is referenced by `Berechnung LU!AQ{n}`: `=TaupunktA(AR{n},$N$19)`, but the function has been commented out of the VBA → the cached result is `#NAME?`, and `AS{n}: =EnthalpieA(AQ{n},AR{n},$N$19)` cascades to `#VALUE!`. In the current version the AQ/AS columns take **no part** in any result aggregation (detailed in Chapter 4, §4.10).

## 1.8 Formula 7 — Wet-Bulb Temperature `Feuchtkugel` (Dead Code)

**Mathematical form** (empirical):

$$
T_{wb} = -5.809 + 0.058\,\varphi[\%] + 0.697\,T + 0.003\,\varphi[\%]\,T
$$

When $T_{wb}<0$: $T_{wb} \leftarrow 0.8\,T_{wb} + 0.5$ (ice-surface wet-bulb correction).

**Workbook implementation**:

```vba
FK = -5.809 + 0.058 * rFein + 0.697 * Tein + 0.003 * rFein * Tein
If FK < 0 Then Feuchtkugel = FK * 0.8 + 0.5 Else Feuchtkugel = FK
```

**Units**: `Tein` [°C], `rFein` [%] (this function works in percent, unlike the other functions in the module!); returns [°C].

**Derivation**: no thermodynamic derivation — the wet-bulb temperature $T_{wb}$ is the temperature at the intersection of the isoenthalpy line and the $\varphi=100\%$ curve in the $h$–$x$ diagram; this formula is a bilinear regression fit (predictors T and φ[%]), common in simplified engineering software. In the negative-temperature range, multiplying by 0.8 and adding 0.5 is an empirical correction for the ice-surface wet bulb (icing conditions).

**Assumptions**: ambient pressure; fit domain unknown (typically 0–40 °C, 20–100 %).

**Range of validity**: for HVAC approximation; **no workbook formula calls it** (confirmed by a full-sheet formula search); it is legacy code.

**Cell provenance**: none (dead code).

## 1.9 Formula 8 — Enthalpy (Directly from Relative Humidity) `EnthalpieR` (Dead Code)

**Mathematical form**: first compute the humidity ratio via Formula 2, then the enthalpy via Formula 3:

$$
x = 0.622\,\frac{\varphi p_s}{p - \varphi p_s};\qquad h = c_{pl}T + x\big(r_0 + c_{pw}T\big)
$$

**Workbook implementation** (note its double-conversion formulation):

```vba
x = 0.622 * (rF * 100 * ps) / (p * 100 - rF * 100 * ps)
EnthalpieR = cpl * T + x * (r0 + cpw * T)
```

**Unit analysis**: the comment says `rF [%]`, but in the formula `rF*100` and `p*100` appear together and cancel exactly: $x = 0.622\,\varphi p_s/(p-\varphi p_s)$. If rF is passed as a percentage (e.g. 50), then $x = 0.622\cdot50 p_s/(p - 50p_s)$; the denominator `p − 50·ps` is still positive at low temperatures — at 0 °C, p=950, 50×6.1=305 ≪ 950 is still acceptable — but numerically the result is wrongly inflated by a factor of 100 (x should be 0.5 times the saturation humidity ratio, not 50 times). **The function is self-consistent only when rF is passed as a decimal (0–1)** — consistent with the calling convention of `AbsFeuchte`. This is coding redundancy (the ×100/÷100 is not cancelled) and the comment is misleading.

**Cell provenance**: none (dead code; a full-sheet formula search finds no `EnthalpieR(` calls).

## 1.10 Call-Site Summary and Consistency Check

| UDF | Calling cells (all) | Purpose |
|---|---|---|
| `AbsFeuchte` | `Klimadaten!Q5:Q65`; `Berechnung LU!AA{n}`, `BL{n}` | Interval humidity ratio; saturation/dew-point limiting |
| `EnthalpieA` | `Berechnung LU!N{n}, O{n}, Y{n}, AB{n}, AE{n}, AJ{n}, AM{n}, AS{n}, AV{n}, BM{n}, BQ{n}` | Enthalpy at the individual state points (MIL, after KRG, after coils, Abluft, etc.) |
| `RelFeuchte` | `Berechnung LU!E{n}, BK{n}, BO{n}, BV{n}` | Outdoor/exhaust relative humidity (with MIN saturation clamp) |
| `TemperaturH` | `Berechnung LU!AN{n}` | Inverted temperature after heating |
| `TaupunktA` | `Berechnung LU!AQ{n}` (**commented out, reports #NAME?**) | Dew point (non-functional) |

**Consistency-check findings** (verified item by item against the dumped cached values):
- `Klimadaten!Q20 = AbsFeuchte(−10, 0.8817, 948.2) = 1.5015 g/kg`: with the Glück polynomial $p_s(-10°C)\approx2.60$ mbar, $622×0.8817×2.60/(948.2−0.8817×2.60) = 1.505$ ✓ (cached 1.5015, difference 0.2 %, from the accuracy of the $p_s$ polynomial).
- `Berechnung LU!N121 = EnthalpieA(L121,M121,p)·E35 + (1−E35)·EnthalpieA(BU121,BW121,p) = 12.2406 kJ/kg`: a weighted average of the MIL enthalpy (WRG efficiency E35); see Chapter 4.
- `AN121 = TemperaturH(AP121, AO121) = 21.27 °C`: inverted from enthalpy 12.24 kJ/kg and humidity ratio ~8.19 g/kg ✓ ($T=(12.24-8.19×2.5016)/(1.006+1.86×0.00819)\approx21.3$).

## 1.11 Porting and Testing Recommendations

1. **Canonical UDFs**: `EnthalpieA`, `AbsFeuchte`, `RelFeuchte`, `TemperaturH` are the canonical implementations; when porting, use the verbatim VBA as the oracle; the `Saettigungsdruck` polynomial should be extracted into a single function for internal reuse (the original workbook inlines it, duplicating code).
2. **Keep the parameter-unit conventions**: `x` is always g/kg; `φ` is always a decimal; `p` is always mbar; **do not** copy the percent/decimal confusion of `EnthalpieR` and `Feuchtkugel` (the former is self-consistent with decimals and has a wrong comment; the latter works in percent).
3. **Glück polynomial boundaries**: use the ice branch only for T≤0; intervals beyond −25…+35 °C have 0 hours in Klimadaten and never enter the calculation, but ported code should keep the piecewise logic.
4. **Dead-code handling**: `EnthalpieR`, `TaupunktR`, `Feuchtkugel`, `TaupunktA` take part in no results; if `TaupunktA` needs to be fixed, invert the Glück polynomial instead, or iterate `TemperaturH` together with the saturation humidity ratio.
