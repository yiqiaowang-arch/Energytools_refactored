# 第 5 章 产热（Erzeugung）与 Resultate 汇总

> 核心区域：`Nutzungsgrad!A1:G41`（产热器目录）、`Erzeugung!A1:Q37`（三组产热 + 电力产热）、`Resultate!A1:U71`（Energieträger 矩阵与加权指标）
> 上游：`Gebäude!Q35:W35`（房间需求 Rechenwert）、`Lüftung!Q23:T23`（AHU 空气处理需求 Total）

## 5.1 章节定位

本章覆盖从"房间+空气处理需求"到"按 Energieträger 的最终能量（Endenergie）"的转换：① 需求分配（Deckungsgrad）；② 损失加成（Speicher-/Verteilverluste）；③ 产热效率（Nutzungsgrad，标准值或项目值）；④ 按 Energieträger 汇总（Resultate 表）；⑤ 加权指标（NEGF/PEne/THGE）。

## 5.2 Nutzungsgrad 目录（产热器目录）

`Nutzungsgrad!B3:G8`（Kälte KE01–KE06）、`B11:G26`（Wärme WE01–WE16）、`B29:G41`（WW W01–W13）：

| 列 | 内容 |
|---|---|
| B | 代号（KE01…KE06 / WE01…WE16 / W01…W13） |
| C | 名称（如 "Kompaktkältemaschine 7°C"、"Wärmepumpe Grundwasser 35°C"） |
| E | **Nutzungsgrad**（效率/COP 标准值） |
| F | Energieträger（Elektrizität、Heizöl EL、Erdgas、Holz、Holzschnitzel、Pellets、Fernwärme、Sonne） |
| G | Hilfsenergie（%——当前版本未参与计算，仅信息） |

**代表性标准值**：Kälte：KE01=3、KE02=4、KE03=4、KE04=7.5、KE05/KE06=15（直接冷源，EER 高）；Wärme：WE01/WE02=0.8（油/气冷凝）、WE03=0.6（Stückholz）、WE04/WE05=0.7（Hackschnitzel/Pellets）、WE06=0.98（Fernwärme）、WE07=0.93、WE08=1（Elektro direkt）、WE09=0.5（WKK thermisch）、WE11–WE16=3.0/2.2/4.3/3.1/4.3/3.1（热泵 35/50 °C × 空气/地源/水源）；WW：W01/W02=0.75、W03=0.55、W04=0.6、W05=0.65、W06/W07=1、W08=0.65、W11=2.2、W12=2.4、W13=1.9。

**单元格出处**：`Nutzungsgrad!E3:E8、E11:E26、E29:E41`；F 列同域；标签经 `Begriffe!F244/F251/F242`。

## 5.3 Erzeugung 布局

三组同构产热块（每组：1 个标题行 + 1 个表头行 + 3 台产热器行 + Total 行）：

| 组 | 行 | 需求来源（功率 L / 能量 M） |
|---|---|---|
| Kälteerzeugung | 7–10 | `Gebäude!Q$35`（Raumkühlung）+ `Lüftung!Q$23`（Luftkühlung 功率）；能量用 `Gebäude!R$35` + `Lüftung!R$23` |
| Wärmeerzeugung | 16–19 | `Gebäude!T$35`（Raumheizung）+ `Lüftung!S$23`（Lufterwärmung 功率）；能量用 `Gebäude!U$35` + `Lüftung!T$23` |
| Warmwassererzeugung | 25–28 | 功率：`Gebäude!V$35×4.186/3.6×50/L$29/1000`；能量：`Gebäude!W$35` |

每台产热器行（以 Kälte 行 7 为例）的列结构：

| 列 | 内容 | 公式 |
|---|---|---|
| A | 代号（自动） | `=IF(B7<>"",INDEX(Nutzungsgrad!$B$3:$C$8,MATCH(Erzeugung!B7,Nutzungsgrad!$C$3:$C$8,0),1),"")` |
| B/C | 产热器名称（下拉，C 为镜像） | 输入 |
| D | Nutzungsgrad 标准值（自动） | `=IF(B7<>"",VLOOKUP($B7,Nutzungsgrad!$C$3:$G$8,3,FALSE),0)` |
| E | Nutzungsgrad 项目值（可覆盖 D） | 输入 |
| F/G | Deckungsgrad 功率/能量 | 输入（%，组内合计 = 100 %） |
| H/I | Speicher-/Verteilverluste 标准/项目 | 输入（%） |
| J/K | 损失项目值（可覆盖 H） | 输入 |
| L/M | **需求（含损失）** 功率/能量 | `=(Gebäude!Q$35+Lüftung!Q$23)*F7%*(100+IF($J7<>"",$J7,$H7))%` |
| N/O | Volllaststunden | `=IF(L7=0,0,M7*1000/L7)` |
| P/Q | **Endenergie** 功率/能量 | `=IF(D7=0,0,$L7/IF($E7<>"",$E7,$D7))` / 同构 M |
| R | Energieträger（自动） | `=IF(D7=0,"",VLOOKUP($B7,Nutzungsgrad!$C$3:$G$8,4,FALSE))` |

## 5.4 公式 1 — 需求分配与损失加成

**数学形式**（对第 i 台产热器，Kälte 组示例）：

$$
\dot Q_{L,i} = \dot Q_{Bedarf}\cdot\frac{d_{P,i}}{100}\cdot\Big(1+\frac{v_i}{100}\Big) \quad[\mathrm{kW}],\qquad
Q_{M,i} = Q_{Bedarf}\cdot\frac{d_{E,i}}{100}\cdot\Big(1+\frac{v_i}{100}\Big) \quad[\mathrm{MWh}]
$$

其中 $d_{P,i}$、$d_{E,i}$ 为功率/能量 Deckungsgrad（%），$v_i = \text{IF}(J_i\neq"", J_i, H_i)$ 为损失率（%）。

**工作簿实现**（`Erzeugung!L7`）：

```
=(Gebäude!Q$35+Lüftung!Q$23)*F7%*(100+IF($J7<>"",$J7,$H7))%
```

**单位**：kW / MWh（能量列 M7 同构，源为 `Gebäude!R$35+Lüftung!R$23`）。

**推导**：把总需求按各产热器的承担份额拆分，并把管网/储罐损失折算到产热器出口（需求 + 损失 = 产热器供给）。损失以百分比加乘（非加性）处理。

**验证**（示例建筑，Kälte 组）：`L7 = (167.138+36.433)×0.6×1.1 = 134.36 kW` ✓（F7=60 %，H7=10 %）；`M7 = (61.207+2.113)×0.8×1.1 = 55.72 MWh` ✓；`L8 = 223.928×0.4×1.1 = 89.57`、`M8×1.1 = 13.93` ✓（组 Total L10=223.93 = 需求合计 203.57×1.1 ✓）。

**假设**：损失与负荷线性成比例（与负荷率无关）；Deckungsgrad 功率与能量可分别设定；项目损失值 J 优先于标准 H。

**适用范围**：Kälte（L7:M9）、Wärme（L16:M18）同构；WW 组功率源不同（见公式 2）。空行（无产热器）输出 0。

**单元格出处**：`Erzeugung!L7:M9`、`L16:M18`；需求源 `Gebäude!Q35/R35、T35/U35`、`Lüftung!Q23/R23、S23/T23`。

## 5.5 公式 2 — Warmwasser 功率需求（水量→功率换算）

**数学形式**：

$$
\dot Q_{WW} = V_{WW}\,[\mathrm{l/d}]\cdot\frac{4.186}{3.6}\cdot 50\,[\mathrm{K}]\cdot\frac{1}{t_{Aufh}}\cdot\frac{1}{1000} \quad[\mathrm{kW}]
$$

其中 $V_{WW}$ = `Gebäude!V35`（日需水量 l/d，第 2 章公式 4），$t_{Aufh}$ = `Erzeugung!L29` = 6（Aufheizzeit h/d），4.186 kJ/(kg·K) 为水的比热，3.6 为 kJ→Wh 换算，50 K 为冷水→热水温升。

**工作簿实现**（`Erzeugung!L25`）：

```
=Gebäude!V$35*4.186/3.6*50/L$29/1000*F25%*(100+IF($J25<>"",$J25,$H25))%
```

**单位推导**：$V\times c_w\times\Delta T$ = kJ/d；÷3.6 → Wh/d；×50 K 已含；÷$t_{Aufh}$ (h/d) → W；÷1000 → kW。合并：$835.7\times(4.186/3.6)\times50/6/1000 = 8.098$ kW（总）；×0.3×1.4 = 3.40 kW（W13 份额）✓ 缓存 3.4011。

**假设**：温升恒为 50 K；日需水量在 Aufheizzeit 内均匀加热（储罐蓄热）；水密度 1 kg/l。

**单元格出处**：`Erzeugung!L25:L27`（能量列 `M25: =（Gebäude!W$35×G25%）×(100+IF($J25<>"",$J25,$H25))%`，直接以 MWh 计）；`Erzeugung!L29/M29`（6 h/d）。

## 5.6 公式 3 — Volllaststunden 与 Endenergie

**数学形式**：

$$
t_{VL,i} = \frac{Q_{M,i}\,[\mathrm{MWh}]\cdot1000}{\dot Q_{L,i}\,[\mathrm{kW}]} \quad[\mathrm{h}],\qquad
P_{End,i} = \frac{\dot Q_{L,i}}{\eta_i},\quad Q_{End,i} = \frac{Q_{M,i}}{\eta_i}
$$

效率 $\eta_i = \text{IF}(E_i\neq"", E_i, D_i)$（项目值优先于目录标准值）。

**工作簿实现**：`Erzeugung!N7: =IF(L7=0,0,M7*1000/L7)`；`P7: =IF(D7=0,0,$L7/IF($E7<>"",$E7,$D7))`；`Q7: =IF(D7=0,0,$M7/IF($E7<>"",$E7,$D7))`。

**单位**：h；kW；MWh。**验证**：`N7 = 55.72×1000/134.36 = 414.7 h` ✓；`P7 = 134.36/12 = 11.196`（E7=12 项目 COP）✓；`Q7 = 55.72/12 = 4.644` ✓。

**推导**：Endenergie = 产热器出口能量 ÷ 效率（对热泵/制冷机，η 即 COP，Endenergie 为电）；全负荷小时 = 能量/功率（与第 3 章同一口径）。

**假设**：效率取年恒值（无部分负荷曲线）；η=0 或 D=0（空行）时输出 0。

**适用范围**：三组产热全部行（7–9、16–18、25–27）；Total 行（10/19/28）的 N 列 `=M10*1000/L10`（无 IF 守卫，L=0 时会有除零——示例建筑 L>0 未触发）。

**单元格出处**：`Erzeugung!N7:Q9`、`N16:Q18`、`N25:Q27`；`N10:Q10` 等 Total 行。

## 5.7 公式 4 — Elektrizitätserzeugung（电力产热，PV/WKK）

`Erzeugung!A31:Q37`：PV-Anlage（EE01）与 WKK-Biogas（EE02）输入：D/E 列装机功率（elektr./therm. kW）、G/H 效率（elektr./therm.）、J/K 系统效率（Standard/Projekt）、L/M 全负荷小时、O–Q PV 朝向（Orient./Azimut/Faktor）。示例：EE01 PV 30 kW、η=0.21、O=8°、Azimut=−45°、Faktor=0.83；EE02 WKK 5 kW/16 kW、η=0.27/0.51、t_VL=3500 h。该块为**输入区**（无下游公式消费其值——当前版本 Resultate 不抵扣自产电；属预留功能）。

**单元格出处**：`Erzeugung!A31:Q37`。

## 5.8 Resultate 布局

**矩阵**（`Resultate!A7:U15`）：行 7–14 = 8 个 Energieträger（El、HEL、Gas、Pell、HSch、StH、Bio、FW）；列 D–U = 9 个用途 ×（Leistung/Energie）：

| 列 | 用途 | 来源 |
|---|---|---|
| D/E | Allg. Gebäudetechnik | `Gebäude!L58/I58` |
| F/G | Geräte | `Gebäude!F35/G35` |
| H/I | Prozessanlagen | `Gebäude!H35/I35` |
| J/K | Beleuchtung | `Gebäude!J35/K35` |
| L/M | Lüftung | `Lüftung!H23/I23`（风机） |
| N/O | Kühlung | `Erzeugung!P10` / `=SUMIF(Erzeugung!$R$7:$R$9,$B7,Erzeugung!$Q$7:$Q$9)` |
| P/Q | Heizung | `=SUMIF(Erzeugung!$R$16:$R$18,$B7,Erzeugung!$P$16:$P$18)`（及 Q） |
| R/S | Warmwasser | `=SUMIF(Erzeugung!$R$25:$R$27,$B7,Erzeugung!$P$25:$P$27)`（及 Q） |
| T/U | Total | `=SUM(D7,F7,H7,J7,L7,N7,P7,R7)` / `=E7+G7+I7+K7+M7+O7+Q7+S7` |

**加权指标**（`Resultate!A18:U25`）：权重列 `W7:Y17`（每 Energieträger 一行）：

| 行 | 指标 | 权重列 | 公式 |
|---|---|---|---|
| 21 | EP_CH（Nationale Energie-Kennzahl） | W（NEGF） | 能量：`=SUMPRODUCT(E$7:E$17*W7:W17)`；单位面积：`=E21*1000/Gebäude!$D$39` |
| 22 | EP_Pnr（Primärenergie nicht erneuerbar） | X（PEne） | 同构（注意：列 D22/F22 等功率列实为 `=E22*1000/$D$39` 的镜像，功率加权未独立计算） |
| 25 | EP_GHG（Treibhausgasemissionen） | Y（THGE） | `=SUMPRODUCT(E$7:E$17*$Y7:$Y17)`；THGE 权重单位 kg/kWh |

**示例权重**：El：NEGF=2、PEne=2.69、THGE=0.139；HEL：1/1.22/0.298；Gas：1/1.06/0.228；Pell：0.7/0.2/0.034；HSch：0.7/0.06/0.022；StH：0.7/0.05/0.022；Bio：1/0.31/0.132；FW：0.6/0.55/0.1。

**单位面积能量平衡**（`Resultate!A28:C59`）：C31: `=Gebäude!R35*1000/Gebäude!D39`（Raumkühlung kWh/m²）、C32: `=Lüftung!R23*1000/Gebäude!D39`（Luftkühlung）、C33/C34（Raumheizung/Lufterwärmung）、C35（WW）、C37/C38（加湿/除湿：`=Lüftung!V23/X23*1000/…`）、C40–C47（电力用途，源为矩阵 E7/G7/I7/K7/M7/O7/Q7/S7 行）、C52–C59（PEne 指标行）、C64–C71（THGE 指标行）。**验证**：`C31 = 61.207×1000/6512 = 9.399 kWh/m²` ✓。

**单元格出处**：`Resultate!A7:U15`、`W7:Y17`（权重）、`D21:U25`（加权）、`B30:C59`（能量平衡）、`B50:C71`（WW/PEne/THGE 单位面积块）。

## 5.9 公式 5 — SUMIF 按 Energieträger 汇总

**数学形式**（对 Energieträger $e$、用途 $u$）：

$$
Q_{End}(e,u) = \sum_{i\in \text{Erzeugung 组}(u)} Q_{End,i}\cdot\mathbb{1}[R_i = e]
$$

**工作簿实现**（`Resultate!O7`，Kühlung 能量）：

```
=SUMIF(Erzeugung!$R$7:$R$9,$B7,Erzeugung!$Q$7:$Q$9)
```

**单位**：MWh（功率列同构取 P 列 → kW）。

**推导**：Erzeugung 每台产热器的 Energieträger 由目录自动填入（R 列），Resultate 按 Energieträger 名称把同一用途组内的产热器求和——即"每种燃料的总量"。

**验证**（示例建筑）：El 行（B7="Elektrizität"）：`O7 = 8.126`（KE02/KE06 电）、`Q7 = 11.820`（WE15 电）、`S7 = 2.624`（W13 电）✓；Pell 行（B10）：`Q10 = 23.218`（WE05）、`S10 = 4.360`（W05）✓；`U7 = 320.316 MWh`（El 总能量）✓。

**假设**：Energieträger 名称在 `Nutzungsgrad` 目录与 `Resultate!B7:B14` 之间完全一致（均由 `Begriffe` 词典产生）。

**适用范围**：`Resultate!N7:S14`（6 个用途列 × 8 行）；T/U 列 Total 用显式 SUM（含 Gebäude/Lüftung 直接引用列）。

**单元格出处**：`Resultate!N7:S14`；匹配键 `Erzeugung!R7:R9、R16:R18、R25:R27`；目录 `Nutzungsgrad!F3:F8、F11:F26、F29:F41`。

## 5.10 公式 6 — 加权能量与单位面积指标

**数学形式**：

$$
EP_{CH,u} = \sum_e k_{NEGF,e}\cdot E_{End}(e,u) \quad[\mathrm{MWh}],\qquad
ep_{CH,u} = EP_{CH,u}\cdot\frac{1000}{A_{EBF}} \quad[\mathrm{kWh/m^2}]
$$

**工作簿实现**（`Resultate!E21`、`D21`）：

```
=SUMPRODUCT(E$7:E$17*W7:W17)
=D21*1000/Gebäude!$D$39     ' 注意：D21 指向 E21 的 1/1000 镜像（见下）
```

**单位**：MWh；kWh/m²。

**推导**：权重因子（NEGF 无权重、PEne 一次能源系数、THGE 温室气体系数 kg CO₂-eq/kWh）与各 Energieträger 的能量逐项相乘求和；再除以 EBF 得单位面积指标。**注意**：工作簿把功率列（D21、F21…）实现为 `=E21*1000/Gebäude!$D$39`，其中 `E21` 为 MWh 加权值，`×1000` 后除以 EBF——即功率列实为"能量指标"的重复显示（加权功率未独立定义），`D21` 缓存 16.78 = E21×1000/6512 ✓。同理 PEne 行（D22/F22… 均镜像 `E22*1000/$D$39`）与 THGE 行（`D25: =E25*1000/$D$39`）。

**验证**：`E21 = 54.644×2 = 109.288`（El 行 W7=2，其余行为 0）✓；`G21 = 129.686×2 = 259.372` ✓；`U21 = 620.80 MWh`。**注意两处疑似复制粘贴错误（已用缓存值证实）**：
- `Resultate!I21`（NEGF 行 · Prozessanlagen）公式为 `=SUMPRODUCT(I$7:I$17*Y7:Y17)`——用了 **THGE 权重列 Y** 而非 NEGF 列 W（其值 2.923 与 THGE 行 `I25` 相同）；按设计应为 `SUMPRODUCT(I7:I17*W7:W17) = 21.03×2 = 42.06 MWh`。
- `Resultate!G22`（PEne 行 · Geräte）公式为 `=SUMPRODUCT(E$7:E$17*$X7:$X17)`——**重复了 E 列（Allg. Gebäudetechnik）** 而非 G 列；`F22`（其功率镜像）随之同样错误（146.99 MWh / 22.57 kWh/m²，应为 129.686×2.69 ≈ 348.9 MWh）。

**假设**：权重因子为瑞士国家能源法中 NEGF/PEne/THGE 的当前值（发布时点）；EBF 分母取 `Gebäude!D39`（含构造面积系数）。

**适用范围**：`Resultate!D21:U25`；权重列 W/X/Y 可被用户编辑。

**单元格出处**：`Resultate!E21、G21、I21、K21、M21、O21、Q21、S21、U21`（NEGF）；`E22…U22`（PEne）；`E25…U25`（THGE）；权重 `W7:Y17`；分母 `Gebäude!D39`。

## 5.11 校验矩阵（示例建筑，El 行，单位 MWh/kW）

| 用途 | 能量（缓存） | 功率（缓存） | 公式出处 |
|---|---|---|---|
| Allg. Gebäudetechnik | 54.6442 | 55.8229 | `Resultate!E7/D7 ← Gebäude!I58/L58` |
| Geräte | 129.6861 | 45.57 | `G7/F7 ← Gebäude!G35/F35` |
| Prozessanlagen | 21.03 | 3 | `I7/H7 ← Gebäude!I35/H35` |
| Beleuchtung | 59.9020 | 41.3754 | `K7/J7 ← Gebäude!K35/J35` |
| Lüftung（风机） | 32.4834 | 9.2079 | `M7/L7 ← Lüftung!I23/H23` |
| Kühlung | 8.1262 | 33.5893 | `O7/N7 ← Erzeugung!Q/P10` |
| Heizung | 11.8202 | 17.7691 | `Q7/P7 ← SUMIF WE 组` |
| Warmwasser | 2.6239 | 1.2597 | `S7/R7 ← SUMIF W 组` |
| **Total** | **320.3159** | **207.5942** | `U7/T7` |

**能量守恒校验**：需求侧（Gebäude+Luft+Warmwasser 损耗前）129.686+21.03+59.902+32.483+(61.207+2.113)+(68.834+5.042)+10.121 ≈ 390.4 MWh；Endenergie 侧经 η 折算后按 Energieträger 合计 347.89 MWh（`U15`）——差额来自产热效率（COP>1 使电耗低于需求）与损失加成（>1）的净效应。两类口径均在表内可追踪。

## 5.12 移植要点

1. 三组产热块同构 → 移植为单一"generator"模型（kind: cooling/heating/ww × {name, eta_standard, eta_project, coverage_P, coverage_E, losses_standard, losses_project, energy_carrier}），组级校验：Deckungsgrad 功率/能量各 100 %（`Erzeugung!F10/G10: =SUM(F7:F9)` 等）。
2. WW 功率换算（4.186/3.6×50/L29/1000）的常量应参数化（ΔT=50 K、Aufheizzeit=6 h/d）。
3. Resultate 的 SUMPRODUCT 加权是"列（用途）× 行（Energieträger）"矩阵乘法——移植为点积即可；功率列镜像（D21=F21=…）是显示冗余，可弃。
4. 权重因子（NEGF/PEne/THGE）为版本化外部数据（瑞士能源法/EnDK），应与模型分开维护。
5. 保留 IF 守卫（D=0 → 0）与 Total 行的求和口径；注意 Total 行 N 列（`M10*1000/L10`）无除零守卫的潜在风险。
6. **修复 `Resultate` 加权行两处复制粘贴错误**（5.10 节）：`I21`（NEGF·Prozessanlagen）误用 Y 权重列；`G22/F22`（PEne·Geräte）重复 E 列。移植时按列定义重写。
