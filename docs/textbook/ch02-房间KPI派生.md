# 第 2 章 房间 KPI 派生（Gebäude 表与 KZ_Raum_2024 矩阵）

> 核心区域：`KZ_Raum_2024`（KPI 矩阵，命名区域 `Res` = `KZ_Raum_2024!$B$7:$AV$51`）、`Gebäude!A10:W39`（房间输入与汇总）、`Gebäude!A43:L62`（Allg. Gebäudetechnik）
> 依赖：`Std!B6:I50`（通风/热水参数）、`Qhc_Klimastat!D7:O51`（冷热负荷强度）、`Begriffe!F13:F57`（房间用途名）

## 2.1 章节定位

本章回答一个问题：**用户在选择房间用途并输入 NGF 之后，各分项功率（kW）与年能量（MWh）是如何从 SIA 2024 的房间特征值（Kennzahlen）派生的**。派生链分三层：

1. **KPI 矩阵层**（`KZ_Raum_2024`）：45 个房间用途 ×（能量 kWh/m² + 功率 W/m²）×（Standard/Zielwert/Bestand）的二维数值表，其中 Klimakälte/Heizwärme 两列是气候相关的公式（引用 `Qhc_Klimastat`）。
2. **查表层**（`Gebäude!F12:W32`）：`VLOOKUP($B{n}, Res, 列号, FALSE)` 按房间用途名精确匹配，乘以 NGF/1000 得到 kW 与 MWh。
3. **汇总层**（`Gebäude!D33:W39`）：Total 行 33 → Rechenwert 行 35（可被外部值覆盖）→ 单位面积指标（除以 EBF）。

## 2.2 KPI 矩阵布局（KZ_Raum_2024）

**行**：7–51 = 45 个房间用途（A 列 = SIA 代码 1.1…12.12；B 列 = 用途名，即 `Res` 的查键；AA 列另有一组内部代码 1.01…12.12 与 45 个名称副本，供 `Leistung` 块使用）。
**列**（以 B 为 `Res` 第 1 列计）：

| Res 列号 | 工作表列 | 内容 | 单位 |
|---|---|---|---|
| 1 | B | 房间用途名（查键） | – |
| 2–8 | C–I | 能量 Standard：Geräte、Prozessanlagen、Beleuchtung、Lüftung、Klimakälte*、Heizwärme*、Warmwasser | kWh/m² |
| 9 | J | （空） | |
| 10–16 | K–Q | 能量 Zielwert（同上 7 项） | kWh/m² |
| 17 | R | （空） | |
| 18–24 | S–Y | 能量 Bestand（同上 7 项） | kWh/m² |
| 25–26 | Z–AA | 内部代码（1.01…12.12）与名称副本 | – |
| 27–33 | AB–AH | 功率 Standard：Geräte、Prozessanlagen、Beleuchtung、Lüftung、Klimakälte*、Heizwärme* | W/m² |
| 34–40 | AI–AO | 功率 Zielwert（同上 6 项） | W/m² |
| 41–47 | AP–AV | 功率 Bestand（同上 6 项） | W/m² |

\* Klimakälte 与 Heizwärme 两列（能量与功率共 12 列）**不是静态值**，而是公式：`=Qhc_Klimastat!<D…O>{行}`。例如 `KZ_Raum_2024!G7: =Qhc_Klimastat!E7`（Einzelbüro 行：`G11 = Qhc_Klimastat!E11 = 14.43 kWh/m²` Klimakälte Standard；`AG11 = Qhc_Klimastat!D11 = 43.66 W/m²` Klimakälte 功率 Standard）。其余 5 类（Geräte/Prozess/Beleuchtung/Lüftung/Warmwasser）为**固化数值**（Raumdatenblätter 出版时的快照）。

**验证示例**（Einzel-, Gruppenbüro，行 11，Standard）：C11=32.01（Geräte 能量）、E11=13.446（Beleuchtung）、F11=4.443（Lüftung）、G11=14.430（Klimakälte，气候相关）、H11=10.762（Heizwärme）、I11=2.595（Warmwasser）；AC11=11（Geräte 功率）、AF11=1.139（Lüftung 功率）、AH11=19.823（Heizwärme 功率）。

## 2.3 公式 1 — Res 列选择器（Wertebereich 切换）

**数学形式**：用户选择值域（`Gebäude!B5`：Standard/Zielwert/Bestand，与 `Begriffe!F76/F77` 比较），把基础列号 $c_0$ 平移得到目标列 $c$：

$$
c = \begin{cases} c_0 & \text{Standard}\\ c_0 + 7\ (功率) \text{ 或 } c_0 + 8\ (能量) & \text{Zielwert}\\ c_0 + 14\ (功率) \text{ 或 } c_0 + 16\ (能量) & \text{Bestand}\end{cases}
$$

**工作簿实现**（`Gebäude!F9`，功率列的代表）：

```
=IF($B5=Begriffe!$F76, F8, IF($B5=Begriffe!$F77, F8+7, F8+14))
```

（`Gebäude!G9` 能量列为 `+8/+16`；`B5` 为值域选择单元格，`F76/F77` 为三语词典中 "Standard"/"Zielwert" 的标签。）

**单位**：–（列号）。

**推导**：矩阵三块（Standard 能量 C–I、Zielwert 能量 K–Q、Bestand 能量 S–Y；功率块 AC–AH/AJ–AO/AQ–AV）在 `Res` 中按固定间隔排列：能量块间隔 8 列（C→K→S 因块间有空列 J/R），功率块间隔 7 列（AC→AJ→AQ）。选择器把「值域」这一用户输入翻译成 VLOOKUP 的列参数。

**假设**：矩阵列布局固定；`B5` 只能取词典中的三种标签之一。

**适用范围**：`Gebäude!F9:W9` 全部 14 个列选择器。**已知偏差**：Lüftung 两列（N9/O9）的偏移为 +6/+12 与 +7/+14，与矩阵实际布局（应为 +7/+14、+8/+16）不一致 → Zielwert/Bestand 值域下 Lüftung 功率/能量将查得 Beleuchtung/Prozessanlagen 列（见 README 0.7-3）。Standard 值域已验证正确。

**单元格出处**：`Gebäude!F9,G9,H9,I9,J9,K9,N9,O9,Q9,R9,T9,U9,W9`；基础列号存于 `Gebäude!F8:W8`（F8=28, G8=2, H8=29, I8=3, J8=30, K8=4, N8=31, O8=5, Q8=32, R8=6, T8=33, U8=7, V8=8, W8=8）。

## 2.4 公式 2 — 房间行功率/能量派生（核心查表式）

**数学形式**：对房间行 n（12≤n≤32）、用途名 $B_n$、NGF $A_n$（`D{n}`）：

$$
P_{n,use} = k_{use}(B_n)\cdot\frac{A_n}{1000}\ [\mathrm{kW}],\qquad E_{n,use} = k_{use}(B_n)\cdot\frac{A_n}{1000}\ [\mathrm{MWh}]
$$

其中 $k_{use}$ 为对应用途 × 值域的 W/m²（功率）或 kWh/m²（能量）特征值（`Res` 查得）。

**工作簿实现**（`Gebäude!F12`，Geräte 功率）：

```
=IF($B12="",0, VLOOKUP($B12,Res,F$9,FALSE))*$D12/1000
```

同类公式遍布 `Gebäude!F12:W32`，列对应关系：

| 目标 | 公式列 | Res 列（Standard） | 含义 | 输出单位 |
|---|---|---|---|---|
| F | `VLOOKUP($B12,Res,F$9,FALSE)` | AC (28) | Geräte 功率 | kW |
| G | `…,G$9,…` | C (2) | Geräte 能量 | MWh |
| H | `…,H$9,…` | AD (29) | Prozessanlagen 功率 | kW |
| I | `…,I$9,…` | D (3) | Prozessanlagen 能量 | MWh |
| J | `…,J$9,…` | AE (30) | Beleuchtung 功率 | kW |
| K | `…,K$9,…` | E (4) | Beleuchtung 能量 | MWh |
| N | `…,N$9,…`（叠加 `IF(L12=FALSE,0,…)`） | AF (31) | Lüftung 功率 | kW |
| O | `…,O$9,…`（叠加 `IF(L12=FALSE,0,…)`） | F (5) | Lüftung 能量 | MWh |
| Q | `…,Q$9,…`（叠加 `IF(P12=FALSE,0,…)`） | AG (32) | Raumkühlung 功率 | kW |
| R | `…,R$9,…`（叠加 `IF(P12=FALSE,0,…)`） | G (6) | Raumkühlung 能量 | MWh |
| T | `…,T$9,…`（叠加 `IF(S12=FALSE,0,…)`） | AH (33) | Raumheizung 功率 | kW |
| U | `…,U$9,…`（叠加 `IF(S12=FALSE,0,…)`） | H (7) | Raumheizung 能量 | MWh |
| W | `…,W$9,…` | I (8) | Warmwasser 能量 | MWh |

**单位推导**：$k$ [W/m²]×$A$ [m²] = [W]；÷1000 → [kW]。能量同构：kWh/m²×m² = kWh；÷1000 → MWh。**1 kWh = 0.001 MWh**。

**假设**：① `VLOOKUP` 第 4 参数 FALSE（精确匹配），房间用途名必须与 `Res` B 列完全一致（数据验证下拉保证）；② 空用途行（B 为空）输出 0；③ 功率按 NGF 线性外推（早期规划阶段假设，无同时性折减）；④ 能量为年值。

**适用范围**：`Gebäude!12:32` 行（21 个房间行）。Lüftung（N/O）仅在 `L{n}≠FALSE`（选择了通风系统）时计入；Raumkühlung（Q/R）仅在 `P{n}=TRUE`（gekühlt）时计入；Raumheizung（T/U）仅在 `S{n}=TRUE`（beheizt）时计入——用 `IF(flag=FALSE,0,…)` 实现。

**单元格出处**：`Gebäude!F12:W32`（21 行 × 14 列）；查键列 `B12:B32`；NGF 列 `D12:D32`；标志列 `C12:C32`（EBF）、`L12:L32`（系统）、`P12:P32`（gekühlt）、`S12:S32`（beheizt）。

## 2.5 公式 3 — 通风体积流量（含过程风量）

**数学形式**：

$$
\dot V_n = \big(q_{hyg}(B_n) + q_{proz}(B_n)\big)\cdot A_n \quad[\mathrm{m^3/h}]
$$

其中 $q_{hyg}$、$q_{proz}$ 分别为卫生（hygienebedingt）与过程（prozessbedingt）单位面积新风量，来自 `Std!D/E` 列。

**工作簿实现**（`Gebäude!M12`）：

```
=IF($B12="",0, VLOOKUP($B12,Std!$B$6:$H$50,M$8,0))*$D12
 +IF($B12="",0, VLOOKUP($B12,Std!$B$6:$H$50,4,0))*$D12
```

`M8=3` → `Std!D`（卫生新风 m³/(h·m²)）；第 4 列 → `Std!E`（过程新风）。`L{n}` 列选择系统（LA01…LA16 或 "-"）。

**单位**：[m³/(h·m²)]×[m²] = [m³/h]。

**验证示例**：`Gebäude!M12 = 2.07143×2500 + 0×2500 = 5178.6 m³/h`（Einzelbüro：`Std!D10=2.0714`）。Parkhaus 特例：`Lüftung!D12 = Gebäude!D21*Std!E47 = 670×2 = 1340 m³/h`（Parkhaus 无卫生新风，D47=0，E47=2 过程新风）。

**假设**：卫生新风为 SIA 2024 标准值（`Std` 表，29 m³/h·P 版本，见第 3 章）；过程新风仅在 `Std!E` 非零的用途出现（Küche、Produktion、Labor、Schwimmhalle、Parkhaus 等）。

**单元格出处**：`Gebäude!M12:M32`；`Std!D6:D50`、`Std!E6:E50`；`Lüftung!D12`（Parkhaus 覆盖示例）。

## 2.6 公式 4 — Warmwasser 日需求量

**数学形式**：

$$
V_{WW,n} = q_{WW}(B_n)\cdot A_n \quad[\mathrm{l/d}]
$$

$q_{WW}$ 为 `Std!I` 列（Warmwasserbedarf pro m²，= `Std!H`（l/(d·P)）÷ `Std!C`（m²/P））。

**工作簿实现**（`Gebäude!V12`）：

```
=IF($B12="",0, VLOOKUP($B12,Std!$B$6:$I$50,$V$8,0))*$D12
```

`V8=8` → `Std!I` 列（查表范围 `$B$6:$I$50` 的第 8 列 = I，即"Warmwasserbedarf pro m²"，`Std!I6 = H6/C6` 为派生公式）。

**单位**：l/d。**验证**：`V12 = 0.21429×2500 = 535.7 l/d`（Einzelbüro `I10 = 3/14 = 0.21429`）。该值进入第 5 章的 WW 功率换算（×4.186/3.6×50 K）。

**单元格出处**：`Gebäude!V12:V32`；`Std!H6:H50`（l/(d·P)）、`Std!I6:I50`（l/(d·m²)）、`Std!C6:C50`（m²/P）。

## 2.7 公式 5 — 汇总：Total、Rechenwert、GF、EBF

**Total 行 33**（`Gebäude!D33:W33`）：`=SUM(D12:D32)` 等，逐列求和。**Rechenwert 行 35**（`Gebäude!D35:W35`）：`=IF(D34<>"",D34,D33)`——若行 34（"Werte aus anderen Quellen"）填写了值则用之，否则取 Total。这是让用户用外部计算覆盖房间汇总的接口。

**Geschossfläche（GF）**（`Gebäude!D38`）：

$$
A_{GF} = A_{EBF,rec}\cdot\Big(1+\frac{k_{Konstr}}{100}\Big),\qquad k_{Konstr} = \text{Gebäude!D37} \text{（Anteil Konstruktionsfläche，默认 10 %）}
$$

实现：`=D35*(100+D37)%`。

**Energiebezugsfläche（EBF）**（`Gebäude!D39`）：

$$
A_{EBF} = \Big(\sum_{n:\,C_n=TRUE} D_n\Big)\cdot\Big(1+\frac{k_{Konstr}}{100}\Big)
$$

实现：`=SUMIF(C12:C32,TRUE,D12:D32)*(100+D37)%`。**要点**：EBF 只汇总 EBF 标志为 TRUE 的房间面积（如 Parkhaus C21=FALSE 不计入），再乘构造面积系数。

**单位面积指标**（`Gebäude!F39:W39`，行 38 同上结构）：`=F35*1000/$D$39`（kW→W，除以 EBF m² → W/m²）；能量：`=G35*1000/$D$39`（MWh→kWh，÷EBF → kWh/m²）。**验证**：`G39 = 129.6861×1000/6512 = 19.9149 kWh/m²`（与 `Resultate!G21` 一致）。

**单元格出处**：`Gebäude!D33:W33`（Total）、`D34:W34`（外部值）、`D35:W35`（Rechenwert）、`D37`（k_Konstr=10）、`D38`（GF）、`D39`（EBF）、`F38:W39`（单位面积指标）。

## 2.8 公式 6 — Allg. Gebäudetechnik（AG01–AG10）

**结构**（`Gebäude!A43:L58`）：10 类建筑设备（Notlicht、Beschattung manuell/automatisch、Gebäudeautomation、Einbruchmeldeanlage、Kleinstverbraucher、Zentrale Parkuhr、Zutrittskontrolle、Aufzug、AG10 空行）。三类输入形态：

**(a) 按面积强度**（kWh/m²，如 AG01 Notlicht）：`Gebäude!E47: =IF(B47="",0,VLOOKUP(B47,$B$69:$F$85,C47+2,0))`（按强度档 C47=1/2/3 → tief/mittel/hoch 查 `$B$69:$F$85` 目录表）；能量 `I47: =E47*G47/1000`（G47=面积，默认 `=D$35`）；功率 `L47: =IF(B47="",0, I47*1000/IF(OR(K47="",K47=0),J47,K47))`（能量÷全负荷小时，J47 从目录第 6 列查得，K47 可项目覆盖）。

**(b) 按件数**（kWh/Stk，如 AG07 Parkuhr）：`E54=1752`（kWh/Stk）、`H54=1`（Stk）、`I54: =E54*H54/1000`。

**(c) 目录表**（`Gebäude!B66:G85`）：来源注释"Minergie Strommodell, Bericht Stefan Gasser 2018"；每类一行：D/E/F 列 = 强度档 1/2/3 的 kWh/m²（或 kWh/Stk）值，G 列 = 全负荷小时（如 Notlicht 8760、Beschattung 200/300 h、Aufzug 500 h）。

**汇总**（`Gebäude!I58/L58`）：`=SUM(I47:I57)`（能量 MWh）、`=SUM(L47:L57)`（功率 kW）；单位面积指标 `I62/L62: =I58*1000/$D$39`。**验证**：`I58 = 54.6442 MWh` → `Resultate!E7 = Gebäude!I58`。

**单元格出处**：`Gebäude!A43:L58`、`B66:G85`（目录）、`I62/L62`（指标）。

## 2.9 数据流校验（与第 5 章衔接）

| 量 | 公式链 | 数值（示例建筑） |
|---|---|---|
| Geräte 功率/能量 | `Gebäude!F35/G35` → `Resultate!F7/G7` | 45.57 kW / 129.69 MWh |
| Beleuchtung | `Gebäude!J35/K35` → `Resultate!J7/K7` | 41.38 kW / 59.90 MWh |
| Raumkühlung | `Gebäude!Q35/R35` → `Erzeugung!L7` 链、`Resultate!N7` | 167.14 kW / 61.21 MWh |
| Raumheizung | `Gebäude!T35/U35` → `Erzeugung!L16` 链、`Resultate!P7` | 103.32 kW / 68.83 MWh |
| Warmwasser | `Gebäude!V35/W35` → `Erzeugung!L25` 链 | 835.71 l/d / 10.12 MWh |
| Allg. Gebäudetechnik | `Gebäude!I58/L58` → `Resultate!E7/D7` | 54.64 MWh / 55.82 kW |

## 2.10 移植要点

1. `Res` 矩阵在移植中应表达为结构化数据集（room_use × value_kind × {W/m², kWh/m²}），并保留 Klimakälte/Heizwärme 对气候站点（Qhc）的依赖——它们是**函数**而非常量。
2. VLOOKUP 精确匹配可替换为键值查表；房间用途键用 `Begriffe!B13:F57` 的德语名（或 SIA 代码 1.1…12.12，但矩阵 B 列存的是名称）。
3. 保留 `IF(flag=FALSE,0,…)` 的门控语义（Lüftung 系统、gekühlt、beheizt）与 `IF(空行,0)` 的守卫。
4. 保留 N9/O9 的列选择器原样或按矩阵定义修正（见 2.3 节偏差说明）；EBF 的 SUMIF 与构造面积系数（10 %）为规范数值。
