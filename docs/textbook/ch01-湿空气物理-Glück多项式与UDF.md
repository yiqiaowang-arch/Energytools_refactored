# 第 1 章 湿空气物理：Glück 多项式与 8 个 UDF

> 代码出处：`.analysis/vba/gebaeude/FeuchteLuft_Formeln.bas`（模块 `FeuchteLuft_Formeln`）
> 调用点：`Klimadaten!Q5:Q65`、`Berechnung LU` 温度区间行（列 E、N、O、P、Y、AA、AB、AE、AJ、AM、AN、AQ、AS、AV、BK、BL、BM、BO、BQ、BT、BV 等，见第 4 章）

本章给出 Gebäude-Tool 全部湿空气状态量公式：饱和水蒸气分压（Glück 多项式）、含湿量、焓、相对湿度、露点、焓反解温度、湿球温度的经验近似。每条公式给出推导、单位、假设、适用范围与工作簿中的调用点（单元格出处）。

## 1.1 模块总览：8 个 UDF

`FeuchteLuft_Formeln.bas` 共定义 8 个可用的 `Public Function`（第 9 个 `TaupunktA` 被整段注释，属死代码但 `Berechnung LU` 仍引用它，见 1.8 节）：

| # | UDF | 签名（注释中的单位） | 返回 | 工作簿公式是否引用 |
|---|---|---|---|---|
| 1 | `Saettigungsdruck` | `(T)` T[°C] | 饱和压力 [mbar] | 否（死代码；多项式被其他函数内联复制） |
| 2 | `AbsFeuchte` | `(T, rF, p)` T[°C], rF[%], p[mbar] | 含湿量 [g/kg] | **是**：`Klimadaten!Q5:Q65`、`Berechnung LU!AA{n}、BL{n}` |
| 3 | `EnthalpieA` | `(T, x, p)` T[°C], x[g/kg], p[mbar] | 焓 [kJ/kg] | **是**：`Berechnung LU` 大量使用（列 N、O、Y、AB、AE、AJ、AM、AS、AV、BM、BQ） |
| 4 | `EnthalpieR` | `(T, rF, p)` T[°C], rF[%], p[mbar] | 焓 [kJ/kg] | 否（死代码） |
| 5 | `TaupunktR` | `(T, rF, p)` | 露点 [°C] | 否（死代码） |
| 6 | `RelFeuchte` | `(T, x, p)` T[°C], x[g/kg], p[mbar] | 相对湿度 [–]（公式返回小数） | **是**：`Berechnung LU!E{n}、BK{n}、BO{n}、BV{n}` |
| 7 | `TemperaturH` | `(h, xein)` h[kJ/kg], x[g/kg] | 温度 [°C] | **是**：`Berechnung LU!AN{n}` |
| 8 | `Feuchtkugel` | `(Tein, rFein)` T[°C], rF[%] | 湿球温度 [°C] | 否（死代码） |
| (9) | `TaupunktA`（注释掉） | `(x, p)` x[g/kg], p[mbar] | 露点 [°C] | 被引用但 `#NAME?`（见 1.8 节） |

**模块级常量**（所有函数内部重复定义，取值一致）：

| 符号 | 值 | 单位 | 含义 |
|---|---|---|---|
| `cpl` | 1.006 | kJ/(kg·K) | 干空气比热（常压） |
| `cpw` | 1.86 | kJ/(kg·K) | 水蒸气比热（常压） |
| `r0` | 2501.6 | kJ/kg | 0 °C 时水的汽化潜热 |
| 622 | – | – | 水/干空气摩尔质量比 × 1000（0.622×1000，见 1.3 节推导） |
| 611 | Pa | – | 水的三相点压力（611 Pa ≈ 6.11 mbar） |

## 1.2 公式 1 — 饱和水蒸气分压（Glück 多项式）

**数学形式**（Glück 多项式，分段）：

$$
p_s(T) = \frac{611}{100}\cdot\exp\!\big(a_0 + a_1 T + a_2 T^2 + a_3 T^3 + a_4 T^4\big) \quad[\mathrm{mbar}],\quad T \text{ in }[°C]
$$

- 冰面（$T \le 0$）：$a = (−4.909965\!\times\!10^{-4},\; 8.183197\!\times\!10^{-2},\; −5.552967\!\times\!10^{-4},\; −2.228376\!\times\!10^{-5},\; −6.211808\!\times\!10^{-7})$
- 水面（$T > 0$）：$a = (−1.91275\!\times\!10^{-4},\; 7.258\!\times\!10^{-2},\; −2.939\!\times\!10^{-4},\; 9.841\!\times\!10^{-7},\; −1.92\!\times\!10^{-9})$

**工作簿实现**（VBA 原文，三个函数内联重复，节选 `Saettigungsdruck`）：

```vba
If T <= 0 Then
    ps = 611 * Exp(-4.909965 * 10 ^ -4 + 8.183197 * 10 ^ -2 * T - 5.552967 * 10 ^ -4 * T ^ 2 _
        - 2.228376 * 10 ^ -5 * T ^ 3 - 6.211808 * 10 ^ -7 * T ^ 4) / 100
ElseIf T > 0 Then
    ps = 611 * Exp(-1.91275 * 10 ^ -4 + 7.258 * 10 ^ -2 * T - 2.939 * 10 ^ -4 * T ^ 2 _
        + 9.841 * 10 ^ -7 * T ^ 3 - 1.92 * 10 ^ -9 * T ^ 4) / 100
End If
```

**单位**：`T` [°C]；返回 `ps` [mbar]（611 [Pa] ÷ 100 = 6.11 [mbar]，即三相点压力 611 Pa 换算为 mbar）。

**推导**：饱和水蒸气分压是克劳修斯–克拉佩龙方程 $d\ln p_s/dT = r/(R_w T^2)$ 的积分结果，其精确解需查表（如 IAPWS-IF97）。Glück 多项式是把 IAPWS/VDI 表格数据在 −20…+60 °C（冰面段 −60…0 °C）区间上做四次多项式最小二乘拟合，以 $\ln p_s = \sum a_i T^i$ 形式给出，使误差 < 0.1 %。611 Pa 为水的三相点压力（0.01 °C 时），保证 $T=0$ 附近两段连续（两段在 T=0 的常数项 −4.9×10⁻⁴ 与 −1.9×10⁻⁴ 近似相等，跳变量级 0.03 %）。

**假设**：① 湿空气为理想气体混合物；② 饱和分压仅依赖温度（忽略总压对 $p_s$ 的 Poynting 修正——低压暖通应用可接受）；③ 多项式系数按 Glück 拟合值（工作簿注释"nach Glück"），与 VDI 4670 或 ASHRAE 数值偏差在工程精度内。

**适用范围**：$-25 \ldots +35$ °C（Gebäude-Tool 实际使用区间；冰面段公式在更低温度下多项式可能发散，勿外推）；压力 850–1030 mbar（瑞士站点气压范围）。

**单元格出处**：函数 `FeuchteLuft_Formeln.Saettigungsdruck`；多项式以内联形式复制于 `AbsFeuchte`、`RelFeuchte`、`EnthalpieR`；`Klimadaten!Q5:Q65` 与 `Berechnung LU` 的含湿量列均经由这些函数间接使用。工作簿公式中**无**直接调用 `Saettigungsdruck()` 的单元格（多项式只以内联路径出现）。

## 1.3 公式 2 — 含湿量（绝对湿度）`AbsFeuchte`

**数学形式**：

$$
x = \frac{622\,\varphi\, p_s(T)}{p - \varphi\, p_s(T)} \quad [\mathrm{g/kg}]
$$

其中 $\varphi$ 以小数（0–1）传入（调用处实际用法；VBA 注释写 `rF [%]`，见 1.9 节）。

**工作簿实现**：

```vba
'Glück 多项式 → ps [mbar]
AbsFeuchte = (rF * 622 * ps) / (p - rF * ps)      ' [g/kg]
```

调用示例：`Klimadaten!Q20: =AbsFeuchte(M20,N20,$F$44)`（T=−10 °C，φ=0.8817，p=948.2 mbar → 1.5015 g/kg）。

**单位**：`T` [°C]，`φ` [–]，`p`、`ps` [mbar]；返回 `x` [g/kg]。

**推导**：由道尔顿分压定律与理想气体状态方程，水蒸气分压 $p_v = \varphi p_s$；干空气分压 $p_{da} = p - p_v$；质量比：

$$
x = \frac{m_v}{m_{da}} = \frac{p_v M_v}{p_{da} M_{da}} = \frac{M_v}{M_{da}}\cdot\frac{\varphi p_s}{p-\varphi p_s} = 0.622\cdot\frac{\varphi p_s}{p-\varphi p_s}\ [\mathrm{kg/kg}]
$$

式中 $M_v/M_{da} = 18.015/28.966 = 0.622$。乘以 1000 即得 g/kg：$x = 622\,\varphi p_s/(p-\varphi p_s)$。

**假设**：理想气体；水蒸气摩尔质量 18.015 g/mol，干空气 28.966 g/mol；忽略溶解空气于水的影响。

**适用范围**：$\varphi\in[0,1)$（$\varphi\to 1$ 时 $x\to x_s$ 饱和值）；$p > \varphi p_s$ 恒成立（正常大气条件）；温度区间同上。注意：若以百分数（如 88）误传 $\varphi$，结果将放大 100 倍——工作簿内 `Klimadaten!N` 列与 `Berechnung LU` 调用处均传小数。

**单元格出处**：定义于 `FeuchteLuft_Formeln.bas`；调用点：`Klimadaten!Q5:Q65`（61 个温度区间）、`Berechnung LU!AA{n}`（`=IF($E$36=$D$36,MIN(AbsFeuchte(Z{n},100%,$N$19),R{n}),MIN(AbsFeuchte(Z{n},100%,$N$19),X{n}))`，其中 `100%`=1 即饱和含湿量，取 min 得露点限幅）、`Berechnung LU!BL{n}`（`=AbsFeuchte(BJ{n},BK{n},$N$19)`）。注意 `AA{n}` 中 `100%` 以小数 1 传入，再次印证调用约定。

## 1.4 公式 3 — 湿空气焓 `EnthalpieA`

**数学形式**：

$$
h = c_{pl}\,T + \frac{x}{1000}\big(r_0 + c_{pw}\,T\big) \quad [\mathrm{kJ/kg}]
$$

**工作簿实现**：

```vba
EnthalpieA = cpl * T + x / 1000 * (r0 + cpw * T)   ' x [g/kg]
```

**单位**：`T` [°C]，`x` [g/kg]（内部 ÷1000 转 kg/kg），`p` [mbar]（**未使用**，仅为与 `EnthalpieR` 一致的签名而保留）；返回 `h` [kJ/kg]。

**推导**：以 0 °C 干空气与 0 °C 液态水为焓基准（暖通惯例，参考态 0 °C、0 kJ/kg）：

$$
h = \underbrace{c_{pl}T}_{\text{干空气显热}} + \underbrace{\frac{x}{1000}\big(\underbrace{r_0}_{\text{0 °C 汽化潜热}} + \underbrace{c_{pw}T}_{\text{水蒸气显热}}\big)}_{\text{水蒸气焓}}
$$

即 $h = c_{pl}T + x_{kg}(r_0 + c_{pw}T)$。对 0 °C 以上：$r_0 + c_{pw}T$ 为水蒸气在 T 时的焓（潜热 + 显热）；0 °C 以下时冰的升华热约 2834 kJ/kg，本式以 2501.6 近似（误差随温度降低增大，见适用范围）。

**假设**：① 比热 $c_{pl}=1.006$、$c_{pw}=1.86$ kJ/(kg·K) 取常值（0–60 °C 内变化 < 1 %）；② 汽化潜热取 0 °C 值 $r_0=2501.6$ kJ/kg（水蒸气理想气体近似，实际 $r$ 随温度线性减小约 −2.4 kJ/(kg·K)，在 0–40 °C 误差 ≤ 4 %）；③ 参考态 0 °C。

**适用范围**：暖通工况 −20…+60 °C；含湿量 0–30 g/kg；0 °C 以下建议仅作工程近似（忽略冰相变差异）。

**单元格出处**：定义于 `FeuchteLuft_Formeln.bas`；调用点（全部在 `Berechnung LU`，行号 n=33…253 区间行，示例 n=121）：
- `N{n}` / `O{n}`：`=EnthalpieA(L{n},M{n},$N$19)*$E$35+(1-$E$35)*EnthalpieA(BU{n},BW{n},$N$19)`（MIL 焓，冬季/夏季 WRG 效率 E35/E34）
- `Y{n}`：`=EnthalpieA(W{n},X{n},$N$19)`（KRG 后状态焓）
- `AB{n}`：`=EnthalpieA(Z{n},AA{n},$N$19)`；`AE{n}`：`=EnthalpieA(AC{n},AD{n},$N$19)`
- `AJ{n}`、`AM{n}`：盘管后焓；`AV{n}`：`=EnthalpieA(AT{n},AU{n},$N$19)`
- `AS{n}`：`=EnthalpieA(AQ{n},AR{n},$N$19)`（因 AQ 列 `TaupunktA` 报错而级联 `#VALUE!`，未参与结果）
- `BM{n}`、`BQ{n}`：`=EnthalpieA(BJ{n},BL{n},$N$19)`、`=EnthalpieA(BN{n},BP{n},$N$19)`

## 1.5 公式 4 — 焓反解温度 `TemperaturH`

**数学形式**（公式 3 的逆）：

$$
T = \frac{h - \dfrac{x}{1000}\,r_0}{c_{pl} + \dfrac{x}{1000}\,c_{pw}} \quad [°C]
$$

**工作簿实现**：

```vba
x = xein / 1000            ' g/kg → kg/kg
TemperaturH = (h - x * r0) / (cpl + cpw * x)
```

**单位**：`h` [kJ/kg]，`xein` [g/kg]；返回 [°C]。

**推导**：由 $h = c_{pl}T + x_{kg}(r_0 + c_{pw}T)$ 解出 $T$：$h - x_{kg}r_0 = T(c_{pl} + x_{kg}c_{pw})$，即上式。几何上这是 $h$–$x$ 图中等焓线（斜率 $1/(c_{pl}+x c_{pw})$）与温度轴的交点。

**假设**：与 `EnthalpieA` 相同（常比热、常潜热）。

**适用范围**：焓值对应 −20…+60 °C 区间；含湿量 0–30 g/kg；当 `h < x·r0/1000` 时返回负温度（物理上不存在，调用处应已由上游状态保证）。

**单元格出处**：`Berechnung LU!AN{n}`：`=TemperaturH(AP{n},AO{n})`（加热段 E 后的温度，由焓 AP 与含湿量 AO 反解）；示例 n=121：`TemperaturH(12.2406, 8.19…) → 21.27 °C`。

## 1.6 公式 5 — 相对湿度 `RelFeuchte`

**数学形式**：

$$
\varphi = \frac{x\,p}{p_s(T)\,(622 + x)} \quad [–]
$$

**工作簿实现**：

```vba
'Glück 多项式 → ps [mbar]
RelFeuchte = (x * p) / (ps * (622 + x))
```

**单位**：`x` [g/kg]，`p`、`ps` [mbar]；返回小数（0–1）。注意：`Berechnung LU` 调用处以 `MIN(100%, …)`/`MIN(1, …)` 限幅，说明返回值按小数计。

**推导**：由公式 2 反解：$x(622+x)^{-1} = \varphi p_s/p \Rightarrow \varphi = xp/\big(p_s(622+x)\big)$。这是 $x = 622\varphi p_s/(p-\varphi p_s)$ 的代数逆。

**假设**：同公式 2。

**适用范围**：$\varphi\in[0,1]$；调用处通常与 `MIN` 组合作为饱和限幅（`MIN(1, RelFeuchte(...))`），避免过饱和（雾）态。

**单元格出处**：`Berechnung LU!E{n}`：`=MIN(100%,RelFeuchte(BR{n},C{n},$N$19))`（区间 n 的室外空气相对湿度，BR=室外焓湿状态）；`BK{n}`：`=MIN(1,RelFeuchte(BJ{n},BT{n},$N$19))`；`BO{n}`：`=MIN(1,RelFeuchte(BN{n},BP{n},$N$19))`；`BV{n}`：`=RelFeuchte(BU{n},BW{n},$N$19)`（Abluft 状态）。

## 1.7 公式 6 — 露点 `TaupunktR`（及死代码 `TaupunktA`）

**数学形式**：先求含湿量（公式 2），再求露点分压与露点温度：

$$
p_{st} = \frac{p}{\dfrac{0.622\cdot1000}{x}+1} = \frac{p\,x}{622+x} \quad[\mathrm{mbar}]
$$

$$
T_d = \Big(\big(p_{st}/2.8858\big)^{1/8.02} - 1.098\Big)\cdot 100 \quad[°C]
$$

**工作簿实现**：

```vba
x = AbsFeuchte(T, rF, p)
pst = p / (0.622 * 1000 / x + 1)
TaupunktR = ((pst / 2.8858) ^ (1 / 8.02) - 1.098) * 100
```

**单位**：`pst` [mbar]，`x` [g/kg]；返回 [°C]。

**推导**：① 露点分压：露点温度定义为含湿量 x 的空气冷却到饱和（$\varphi=1$）时的温度，故 $p_{st} = p_v = \varphi p_s$；由公式 2 反解 $p_v = xp/(622+x)$（与上式一致，注意 $0.622\cdot1000/x$ 即 $622/x$）。② 露点温度：采用**另一组饱和压力经验拟合**（非 Glück 多项式）：

$$
p_s(T) = 2.8858\,(T/100 + 1.098)^{8.02} \quad[\mathrm{mbar}]
$$

其逆即上式。校核：$T=0$：$p_s=2.8858\cdot1.098^{8.02}\approx6.02$ mbar（真值 6.11，偏差 1.5 %）；$T=20$：≈24.9 mbar（真值 23.4，偏差 6 %）。该拟合在暖通露点范围（−20…+30 °C）内为工程近似，精度低于 Glück 多项式，且与模块内其他函数不自洽（两种 $p_s$ 模型并存）。

**假设**：理想气体；$p_s$ 采用上述幂律拟合；含湿量以 g/kg 计。

**适用范围**：露点 −20…+30 °C；$p_{st} > 0$（x>0）。**注意**：函数仅存在于 `TaupunktR`（死代码）与注释掉的 `TaupunktA` 中。

**单元格出处**：`TaupunktA` 被 `Berechnung LU!AQ{n}` 引用：`=TaupunktA(AR{n},$N$19)`，但该函数已从 VBA 注释掉 → 缓存结果 `#NAME?`，级联 `AS{n}: =EnthalpieA(AQ{n},AR{n},$N$19)` 为 `#VALUE!`。当前版本中 AQ/AS 列**不参与**任何结果汇总（第 4 章 4.10 节详述）。

## 1.8 公式 7 — 湿球温度 `Feuchtkugel`（死代码）

**数学形式**（经验式）：

$$
T_{wb} = -5.809 + 0.058\,\varphi[\%] + 0.697\,T + 0.003\,\varphi[\%]\,T
$$

当 $T_{wb}<0$ 时：$T_{wb} \leftarrow 0.8\,T_{wb} + 0.5$（冰面湿球修正）。

**工作簿实现**：

```vba
FK = -5.809 + 0.058 * rFein + 0.697 * Tein + 0.003 * rFein * Tein
If FK < 0 Then Feuchtkugel = FK * 0.8 + 0.5 Else Feuchtkugel = FK
```

**单位**：`Tein` [°C]，`rFein` [%]（此函数以百分数计，与模块其他函数不同！）；返回 [°C]。

**推导**：无热力学推导——湿球温度 $T_{wb}$ 是 $h$–$x$ 图上等焓线与 $\varphi=100\%$ 曲线的交点温度；本式为双线性回归拟合（自变量 T 与 φ[%]），常见于简化工程软件。负温段乘以 0.8 并加 0.5 是对冰面湿球（结冰工况）的经验修正。

**假设**：常压环境；拟合域未知（典型 0–40 °C、20–100 %）。

**适用范围**：暖通近似用；**工作簿中无任何公式调用**（已通过全表公式检索确认），属遗留代码。

**单元格出处**：无（死代码）。

## 1.9 公式 8 — 焓（由相对湿度直接计算）`EnthalpieR`（死代码）

**数学形式**：先由公式 2 求含湿量再按公式 3 求焓：

$$
x = 0.622\,\frac{\varphi p_s}{p - \varphi p_s};\qquad h = c_{pl}T + x\big(r_0 + c_{pw}T\big)
$$

**工作簿实现**（注意其双重换算写法）：

```vba
x = 0.622 * (rF * 100 * ps) / (p * 100 - rF * 100 * ps)
EnthalpieR = cpl * T + x * (r0 + cpw * T)
```

**单位推导**：注释称 `rF [%]`，但公式中 `rF*100` 与 `p*100` 同时出现、恰好抵消：$x = 0.622\,\varphi p_s/(p-\varphi p_s)$。若 rF 以百分数传入（如 50），则 $x = 0.622\cdot50 p_s/(p - 50p_s)$，分母 `p − 50·ps` 在低温时仍为正但在 0 °C、p=950 时 50×6.1=305 ≪ 950 尚可，但数值上错误放大 100 倍（x 应为 0.5 倍饱和含湿量而非 50 倍）。**只有当 rF 以小数（0–1）传入时该函数才自洽**——与 `AbsFeuchte` 的调用约定一致。属编码冗余（×100/÷100 未约简）且注释误导。

**单元格出处**：无（死代码；全表公式检索无 `EnthalpieR(` 调用）。

## 1.10 调用点汇总与一致性核查

| UDF | 调用单元格（全部） | 用途 |
|---|---|---|
| `AbsFeuchte` | `Klimadaten!Q5:Q65`；`Berechnung LU!AA{n}`、`BL{n}` | 区间含湿量；饱和/露点限幅 |
| `EnthalpieA` | `Berechnung LU!N{n}、O{n}、Y{n}、AB{n}、AE{n}、AJ{n}、AM{n}、AS{n}、AV{n}、BM{n}、BQ{n}` | 各状态点焓（MIL、KRG 后、盘管后、Abluft 等） |
| `RelFeuchte` | `Berechnung LU!E{n}、BK{n}、BO{n}、BV{n}` | 室外/排风相对湿度（含 MIN 饱和限幅） |
| `TemperaturH` | `Berechnung LU!AN{n}` | 加热后温度反解 |
| `TaupunktA` | `Berechnung LU!AQ{n}`（**已注释，报 #NAME?**） | 露点（失效） |

**一致性核查结论**（基于转储缓存值逐项验证）：
- `Klimadaten!Q20 = AbsFeuchte(−10, 0.8817, 948.2) = 1.5015 g/kg`：以 Glück 多项式 $p_s(-10°C)\approx2.60$ mbar 代入 $622×0.8817×2.60/(948.2−0.8817×2.60) = 1.505$ ✓（缓存 1.5015，差 0.2 %，来自 $p_s$ 多项式精度）。
- `Berechnung LU!N121 = EnthalpieA(L121,M121,p)·E35 + (1−E35)·EnthalpieA(BU121,BW121,p) = 12.2406 kJ/kg`：为 MIL 焓的加权平均（WRG 效率 E35），见第 4 章。
- `AN121 = TemperaturH(AP121, AO121) = 21.27 °C`：焓 12.24 kJ/kg、含湿量 ~8.19 g/kg 反解 ✓（$T=(12.24-8.19×2.5016)/(1.006+1.86×0.00819)\approx21.3$）。

## 1.11 移植与测试建议

1. **规范 UDF**：`EnthalpieA`、`AbsFeuchte`、`RelFeuchte`、`TemperaturH` 为规范实现，移植时以 VBA 原文为 oracle；`Saettigungsdruck` 多项式应提取为单一函数供内部复用（原工作簿为内联复制，存在重复代码）。
2. **保留参数单位约定**：`x` 一律 g/kg；`φ` 一律小数；`p` 一律 mbar；`EnthalpieR` 与 `Feuchtkugel` 的百分数/小数混乱**不要**照搬（前者按小数自洽、注释错误；后者按百分数）。
3. **Glück 多项式边界**：冰面段仅在 T≤0 使用；超出 −25…+35 °C 的区间在 Klimadaten 中小时数为 0，不会进入计算，但移植代码应保留分段逻辑。
4. **死代码处理**：`EnthalpieR`、`TaupunktR`、`Feuchtkugel`、`TaupunktA` 不参与任何结果；`TaupunktA` 若需修复，应改用 Glück 多项式反解或 `TemperaturH` 配合饱和含湿量迭代。
