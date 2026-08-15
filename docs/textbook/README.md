# Gebäude-Tool（SIA 2024）计算模型教科书

> 完整计算教科书 · 基于 `.analysis` 提取物编写
>
> 对象：`data/raw/2024_Gebaeude-Tool_dfi_V221.xlsm`（13 个工作表，≈51 300 个非空单元格，≈16 900 个公式单元格）
> 姊妹数据集：`2024_Raumdatenblätter_dfi_V221.xlsm`（房间数据源，45 种房间用途）
>
> 语言约定：正文以中文撰写；专业术语保留德语原文（首次出现附中文与英文）；公式引用原样保留 Excel/VBA 语法。

---

## 0.1 文档地图

| 章节 | 文件 | 内容 |
|---|---|---|
| 导读（本文件） | `README.md` | 工具定位、数据来源、单元格引用约定、计算流程总览、工作表清单、单位制、已知怪癖 |
| 第 1 章 | `ch01-湿空气物理-Glück多项式与UDF.md` | 湿空气物理：Glück 饱和压力多项式、焓/含湿量/相对湿度/露点等 8 个 UDF 的推导、单位、假设、适用范围与全部调用点 |
| 第 2 章 | `ch02-房间KPI派生.md` | 房间 KPI 派生：`KZ_Raum_2024` 矩阵、`Res` 命名区域、`Gebäude` 房间行 VLOOKUP 链、EBF/GF/面积加权、Allg. Gebäudetechnik |
| 第 3 章 | `ch03-通风全负荷小时.md` | 通风全负荷小时：`Std` 表（Raumdaten `Volll_Lüft` 副本）、按 Regelung 选取的机制、AHU 引擎中的使用 |
| 第 4 章 | `ch04-AHU温度区间法.md` | AHU 温度区间法（`Berechnung LU`）：气象区间（bin）焓湿链、风机三档 P∝V^2.5、WRG/KRG、四种控制工况（Fall 1–4）、能耗汇总 |
| 第 5 章 | `ch05-产热与Resultate汇总.md` | 产热与 Resultate 汇总：`Nutzungsgrad` 目录、`Erzeugung` 三组产热器、Endenergie/Energieträger 分配、`Resultate` 加权（NEGF/PEne/THGE） |
| 第 6 章 | `ch06-气候数据.md` | 气候数据：`Klimadaten` 40 站点、气压（气压高度公式）、HDD、设计温度、温度区间小时数与湿度序列、`Qhc_Klimastat` |
| 附录 A | `analysis_Berechnung_LU.md` | `Berechnung LU` 全表逐列分析底稿（第 4 章的推导依据；含行 168 完整数值示例） |

## 0.2 数据来源与可复现性

本教科书的一切公式、常量与单元格引用均取自以下 `.analysis` 提取物（工作簿 OOXML 解包 + VBA 源码提取 + 逐单元格转储）：

- 逐单元格转储（地址 / 公式 / 缓存结果）：`.analysis/dumps/gebaeude/sheet_*.tsv`
- 工作表清单与行列统计：`.analysis/dumps/gebaeude/sheets.json`
- 命名区域：`.analysis/dumps/gebaeude/definedNames.json`
- VBA 源码（UDF 与宏）：`.analysis/vba/gebaeude/*.bas`、`*.cls`
- 解包 OOXML：`.analysis/unpacked/gebaeude/`
- 源文件哈希可复现：`data/raw/2024_Gebaeude-Tool_dfi_V221.xlsm`（897 991 字节）

> ⚠️ 转储中的 `R:` 值为该文件保存时的**缓存计算结果**（例如示例建筑 = Zürich-MeteoSchweiz 站、Standard 值域）；本文中的数值示例均标注其输入前提。

## 0.3 单元格引用约定

- 本教科书使用德语工作表原名（文件内存储名，不随语言切换改名）：
  `Gebäude`、`Lüftung`、`Erzeugung`、`Resultate`、`Nutzungsgrad`、`Berechnung LU`、
  `Klimadaten`、`KZ_Raum_2024`、`Qhc_Klimastat`、`Std`、`Begriffe`、`Anleitung`、`Lizenzieren`。
- 单元格记号：`工作表!列行`，如 `Gebäude!F12`；范围如 `KZ_Raum_2024!$B$7:$AV$51`。
- 公式原文用等宽字体（`` ` ``）引用，例如 `` `VLOOKUP($B12,Res,F$9,FALSE)` ``；其中 `Res` 为命名区域。
- **行变量约定**：凡公式沿行重复，用行号 `n` 表示一般行，并给出一个具体示例行（如 `n=121`）。
  例如 `Berechnung LU` 的温度区间行写作 `X{n}`（IST 块 `n=121…181`、SOLL 块 `n=189…249`，t_A = −25…+35 °C）。
- 跨表引用（外部链接）按转储记号 `[3]` 等标注（见 0.7 节）。

## 0.4 计算流程总览

```
项目输入 (Gebäude!B2..J2, Klimastation via Gebäude!D2)
        │
        ▼
┌───────────────────────────── Gebäude 表 ─────────────────────────────┐
│ 21 个房间行 (12..32)：Raumnutzung 下拉 (Begriffe!F13:F57)             │
│   → A 列反查 SIA 代码 (INDEX/MATCH Begriffe!B13:F57)                 │
│   → EBF 标志 (C)、NGF (D)、Anteil (E)                                │
│   → 各用途 Leistung/Energie (F..K)  ← VLOOKUP(B, Res, 列号) × NGF/1000│
│   → Lüftung 系统 (L)、Volumenstr. (M) ← VLOOKUP(B, Std!B:H)          │
│   → Raumkühlung (P..R)、Raumheizung (S..U) ← VLOOKUP(B, Res) × NGF/1000│
│   → Warmwasser Bedarf (V) ← VLOOKUP(B, Std!B:I)；Energie (W) ← Res   │
│   → Total 行 33 → Rechenwert 行 35 (可被 "Werte aus anderen Quellen"│
│     行 34 覆盖) → GF/EBF 行 37..39                                    │
│   → Allg. Gebäudetechnik 行 47..57 (AG01..AG10, Minergie-Strommodell)│
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────────── Lüftung 表 ──────────────────────────────┐
│ 16 个系统行 (LA01..LA16, 7..22)                                       │
│   C: Volumenstr. Standard ← SUMIF(Gebäude!L12:L32, 系统, M12:M32)    │
│   F: Rechenwert = C 或 E(Projekt)；H: 风机功率 = F×SFP/1000           │
│   J: Regelung (einstufig/zweistufig/stufenlos)                        │
│   K: Vollast. = ROUND(I×1000/H, -1)（由 AHU 结果反推）                │
│   Q..Z: 空气冷却/加热/加湿/除湿 Leistung+Energie ← Berechnung LU 结果 │
│   Total 行 23                                                        │
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────── Berechnung LU 表（物理引擎）────────────────┐
│ 行 6：单系统输入（= Lüftung!32 模板行，宏复制到 7..22）               │
│ 行 7：Resultate（风机电能 H7、各处理段功率/能量 P7..Y7）              │
│ 行 11..55：IST/SOLL 输入（面积、层高、过滤器、风机效率级、WRG/KRG、  │
│            冷却/加热/加湿/除湿设定、运行时间表、温度曲线）            │
│ 行 63..67：分档运行时间加权风机功率与平均风量                        │
│ 行 68..70：SIA 全负荷小时 (Std!Q:V 按 Regelung) 与合理性检验         │
│ 行 100..114：电机效率级 (IE5..Eff3 × 功率带) 与过滤器压降            │
│ 行 121..181：IST 温度区间焓湿计算（61 区间 −25…+35 °C，逐区间：      │
│    AUL → 防冻 → nWRG → MIL(焓/温) → 冷盘管链 A/C/D1/D2 → Fall 1..4 →│
│    Zuluft soll/ist、Raum；每小时功率 × 区间小时数 = 区间能量）        │
│ 行 189..249：SOLL 区间块（休眠）；行 182/183：年度能量和/功率最大    │
│ 行 254..260：年度能量汇总（kWh/kW；行 7 的 MWh 等价 Q7..Y7、H7）     │
│ 行 261+：经济性（电价、运行成本）                                    │
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────────── Erzeugung 表 ────────────────────────────┐
│ Kälte (行 7..10)：需求 ← Gebäude!Q/R35 + Lüftung!Q/R23               │
│ Wärme (行 16..19)：需求 ← Gebäude!T/U35 + Lüftung!S/T23              │
│ WW   (行 25..28)：需求 ← Gebäude!V/W35（V×4.186/3.6×50/L29/1000）    │
│ 每台：Deckungsgrad F/G%、Speicher-/Verteilverluste H/J%              │
│   L/M = 需求×Deckungsgrad×(100+Verluste)%                            │
│   N = M×1000/L（Volllaststunden）；P/Q = L/M÷Nutzungsgrad(项目或标准) │
│   R = Energieträger ← VLOOKUP Nutzungsgrad 目录                      │
│ Elektrizitätserzeugung (行 34..37)：PV/WKK 装机与效率                  │
└──────────────┬────────────────────────────────────────────────────────┘
               ▼
┌───────────────────────────── Resultate 表 ────────────────────────────┐
│ Energieträger × 用途矩阵 (行 7..15)：El/HEL/Gas/Pell/HSch/StH/Bio/FW │
│   Geräte/Prozess/Beleuchtung ← Gebäude 行 35                          │
│   Lüftung ← Lüftung!H23/I23；Kühlung/Heizung/WW ← Erzeugung SUMIF     │
│ 加权行 21/22/25：NEGF (W)、PEne (X)、THGE (Y) 权重 SUMPRODUCT         │
│ 能量平衡行 28..59：kWh/m²、kg/m² 单位面积指标                         │
└──────────────────────────────────────────────────────────────────────┘
```

依赖方向：`Gebäude` → `Lüftung`/`Berechnung LU` → `Erzeugung` → `Resultate`；
数据表：`Klimadaten`（气候）、`Std`（全负荷小时与通风/热水参数）、`KZ_Raum_2024`（KPI 矩阵，即命名区域 `Res`）、`Qhc_Klimastat`（冷热负荷强度）、`Nutzungsgrad`（产热器目录）、`Begriffe`（三语词典/标签）。

## 0.5 工作表清单（Gebäude-Tool V221）

| 工作表 | 可见性 | 行×列 | 公式单元 | 角色 |
|---|---|---|---|---|
| Lizenzieren | veryHidden | 2:40 | 0 | 旧许可 UI（V221 已停用） |
| Anleitung | visible | 1:30 | 26 | 三语说明；建筑工作表增删宏 |
| Begriffe | veryHidden | 1:301 | 295 | 三语词典；45 个房间用途名（下拉源 `B13:F57`）；标签 F 列 |
| **Gebäude** | visible | 1:87 | 555 | 建筑输入表：21 房间行 + Total/Rechenwert + GF/EBF + Allg. Gebäudetechnik |
| **Lüftung** | visible | 1:32 | 135 | 16 个通风系统（LA01–LA16），风机/冷却/加热/加湿/除湿结果 |
| **Erzeugung** | visible | 1:37 | 159 | 3 组产热（Kälte/Wärme/WW）+ 电力产热（PV/WKK） |
| **Resultate** | visible | 1:71 | 248 | Energieträger×用途 Endenergie 表 + NEGF/PEne/THGE 加权 + 单位面积指标 |
| Nutzungsgrad | veryHidden | 2:41 | 85 | 产热器目录（KE01–06、WE01–16、W01–13）：Nutzungsgrad、Energieträger、Hilfsenergie |
| **Berechnung LU** | veryHidden | 1:328 | 13 466 | AHU 物理引擎：温度区间焓湿法（核心） |
| **Klimadaten** | veryHidden | 1:65 | 485 | 40 站点：设计温度、HDD、气压、温度区间小时数、湿度序列 |
| KZ_Raum_2024 | veryHidden | 2:51 | 631 | 房间 KPI 矩阵（命名区域 `Res` = `$B$7:$AV$51`） |
| Qhc_Klimastat | veryHidden | 1:51 | 727 | 40 站点 × 45 房间用途冷/热负荷强度（Raumdaten 副本） |
| Std | veryHidden | 1:50 | 119 | Raumdaten `Volll_Lüft` 副本 + 通风/热水参数（来源注释 `Std!L2`） |

## 0.6 单位制与命名惯例

- 能量：`MWh`（工作表内部）/ `kWh/m²`（单位面积指标）；功率：`kW`；风量：`m³/h`。
- 湿空气：温度 `T [°C]`；含湿量 `x [g/kg]`（UDF 内部 `EnthalpieA` 以 g/kg 计，换算 `/1000`）；相对湿度 `rF [%]`（UDF 调用处多用 0–1 小数，见第 1 章 1.9 节）；气压 `p [mbar]`；焓 `h [kJ/kg]`。
- 物性常量（`Berechnung LU!N19:N25`）：`p`（站点气压）、`cpl=1.006 kJ/kgK`、`cpw=1.86 kJ/kgK`、`cw=4.19 kJ/kgK`、`ρ=1.15 kg/m³`、`r0=2501.6 kJ/kg (0°C)`、`r100=2256 kJ/kg (100°C)`。
- 德语量符号：`t_A` 室外温度、`t_ZUL` 送风温度、`t_Raum` 房间温度、`x` 含湿量、`φ/rF` 相对湿度、`h` 焓、`η_WRG` 热回收效率、`SFP` 比风机功率 `[W/(m³/h)]`。

## 0.7 已知怪癖与注意点（观察所得，非评价）

1. **`TaupunktA` UDF 已注释掉**（`FeuchteLuft_Formeln.bas` 行 90–99），但 `Berechnung LU` 列 AQ/AS 仍调用它 → 缓存结果 `#NAME?` / `#VALUE!`。该列链（ZUL 露点控制）在当前版本**不参与**结果（列 AS 的下游未使用）。
2. **相对湿度单位不一致**：`Klimadaten` 表头标 `[%]`，但数值为 0–1 小数（如 0.88）；UDF `AbsFeuchte/RelFeuchte` 期望 0–1 小数，`EnthalpieR` 注释称 `%` 但其算式对小数才自洽（见 1.9 节）。
3. **`Gebäude!N9/O9`（Lüftung 的 Res 列选择器）对 Zielwert/Bestand 值域的偏移量疑似偏小**（+6/+12 与 +7/+14）：Zielwert 将查得 `AL`（Beleuchtung 功率）而非 `AM`（Lüftung 功率），Bestand 将查得 `AR`/`T` 而非 `AT`/`V`。Standard 值域正确（已用缓存值验证）。移植时需按矩阵列定义修正或保留原行为。
4. **数据陈旧风险**：`Std`、`Qhc_Klimastat`、`KZ_Raum_2024` 为 Raumdatenblätter 的静态副本/手工数据；外部链接 `[3]` 指向 `SIA2024_Raumdatenblätter_dfi_V221_20241117.xlsm`（与发行文件名不一致），`[1]`（Lüftung_20201113.xlsm）与 `[4]`（Arealbewertungstool）链接已断/仅缓存。
5. **单位面积指标的分母**：`Gebäude!D39`（EBF）只汇总 `C12:C32 = TRUE`（EBF 标志）的房间面积，且乘以 `(100+D37)%`（Anteil Konstruktionsfläche，默认 10%）。
6. **`Std!N` 列（Ventilatorregelung Standard）与 `Gebäude`/`Lüftung` 的 J 列（Regelung）**是两套独立输入：`Std` 提供各用途的标准调节方式（数据属性），`Lüftung!J7` 是项目对该系统的实际调节方式（决定 `Berechnung LU` 的档位与全负荷小时）。
7. **四舍五入为规范**：`ROUND(I×1000/H, -1)`（Lüftung!K7）与 `ROUND(H7*1000/G6,-1)`（Berechnung LU!J7）把全负荷小时取整到 10 h——这是发布值的一部分，移植时必须保留。
8. **保护口令可恢复**（`lockStructure` 等，口令见 VBA 源码）——属商业包装而非加密安全。
9. **`KZ_Raum_2024` 行 3 的序号列（B3=1, C3=2, …）与 A 列 SIA 代码（1.1…12.12）、AA 列内部代码（1.01…12.12）并存**；`Res` 的查键是 B 列房间用途名（德语）。
10. **`Fallunterscheidung.bas`（Fall1Tzul/Fall1xzul/Fall2Tzul/Fall2xzul）被 `Berechnung LU!BB:BE` 列实际引用**（早期评估误判为死代码；全表检索证实 61×2 个区间行调用它们，`#NAME?` 仅出现在 `TaupunktA`）。该模块为**活代码**，移植时需一并实现。
11. **`Lüftung!U32:Z32` 接线错位**：`U32←'Berechnung LU'!V7`（实为 Entfeuchtung Kühlung）、`W32←X7`（Entf. Erwärmung）、`Y32←T7`（Erwärmung Befeuchtung）——即"Befeuchtung / Entf. Kühlung / Entf. Erwärmung"三对列的表头与实际取值整体错一对，`Resultate!C37/C38` 沿同一错位链取值。示例建筑三对值均 ≈0 未暴露；移植时必须按 `Berechnung LU` 行 254–258 的语义重新接线（第 4 章 4.14-8）。
12. **`Berechnung LU` 其他怪癖**：能量和从行 122 起（排除 −25 °C 区间）、`CC183` 功率最大从行 133 起（−10 °C）、SOLL 块（行 189–249）休眠（气候单元格 0、气压 `#REF!`）、`T{n}=MIN(单参)` 无操作、AD/AE 草稿列（`AD=n−122`，AE 无下游）、能源价格单元格空 → 成本恒 0、`BU` 列含 `#REF!` 死分支（Quellluft 且 I21≠0 时才会触发）。详见第 4 章 4.14。
13. **`Resultate` 加权行两处复制粘贴错误**：`I21`（NEGF·Prozessanlagen）误用 THGE 权重列 Y（= 2.923，与 `I25` 相同）；`G22/F22`（PEne·Geräte）重复 E 列（Allg. Gebäudetechnik，146.99 MWh / 22.57 kWh/m²）。两者已用缓存值证实（第 5 章 5.10）。

## 0.8 如何阅读每条公式

每章公式条目统一采用如下结构：

> **公式 n — 名称**
> - 数学形式（符号式）
> - 工作簿实现（Excel 原文 + 单元格）
> - 单位
> - 推导（从物理定义出发）
> - 假设（常量、简化、规范取整）
> - 适用范围（输入域、边界、失效条件）
> - 单元格出处（一级引用链）

数值示例均以转储缓存值为准，并注明输入前提（站点、值域、系统）。
