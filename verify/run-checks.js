// 对拍复核 harness: textbook chapters (6) vs .analysis cell dumps (main repo)
// Usage: node verify/run-checks.js
'use strict';
const fs = require('fs');
const path = require('path');

const MAIN = 'C:/Users/wangy/Documents/GitHub/Energytools_refactored/.analysis/dumps';
const GEB = path.join(MAIN, 'gebaeude');
const RAUM = path.join(MAIN, 'raumdaten');

// ---------- dump loading ----------
const cache = {};
function loadSheet(name, file) {
  if (cache[name]) return cache[name];
  const map = new Map();
  const txt = fs.readFileSync(file, 'utf8');
  for (const line of txt.split(/\r?\n/)) {
    if (!line) continue;
    const tab = line.indexOf('\t');
    if (tab <= 0) continue;
    const addr = line.slice(0, tab);
    const rest = line.slice(tab + 1);
    const entry = { addr, raw: rest, f: null, r: null, v: null };
    if (rest.startsWith('F:')) {
      const m = rest.match(/^F:(.*?)(?:\tR:(.*))?$/s);
      if (m) { entry.f = m[1]; if (m[2] !== undefined) entry.r = m[2]; }
    } else if (rest.startsWith('{')) {
      try {
        const j = JSON.parse(rest);
        if (typeof j.formula === 'string') entry.f = j.formula;
        if (j.result !== undefined) entry.r = String(j.result);
        if (j.error) entry.r = JSON.stringify({ error: j.error });
      } catch (e) { entry.v = rest; }
    } else {
      entry.v = rest;
    }
    map.set(addr, entry);
  }
  cache[name] = map;
  return map;
}
const sheets = {
  Nutzungsgrad: () => loadSheet('Nutzungsgrad', path.join(GEB, 'sheet_15_Nutzungsgrad.tsv')),
  Gebaeude: () => loadSheet('Gebaeude', path.join(GEB, 'sheet_40_Gebäude.tsv')),
  KZ: () => loadSheet('KZ', path.join(GEB, 'sheet_41_KZ_Raum_2024.tsv')),
  Std: () => loadSheet('Std', path.join(GEB, 'sheet_42_Std.tsv')),
  Lueftung: () => loadSheet('Lueftung', path.join(GEB, 'sheet_56_Lüftung.tsv')),
  Erzeugung: () => loadSheet('Erzeugung', path.join(GEB, 'sheet_57_Erzeugung.tsv')),
  Resultate: () => loadSheet('Resultate', path.join(GEB, 'sheet_58_Resultate.tsv')),
  BLU: () => loadSheet('BLU', path.join(GEB, 'sheet_61_Berechnung LU.tsv')),
  Klima: () => loadSheet('Klima', path.join(GEB, 'sheet_62_Klimadaten.tsv')),
  Qhc: () => loadSheet('Qhc', path.join(GEB, 'sheet_64_Qhc_Klimastat.tsv')),
  Volll: () => loadSheet('Volll', path.join(RAUM, 'sheet_14843_Volll_Lüft.tsv')),
};

// ---------- helpers ----------
function cell(sheet, addr) {
  const m = sheets[sheet]();
  const e = m.get(addr);
  if (!e) return null;
  return e;
}
function numVal(sheet, addr) {
  const e = cell(sheet, addr);
  if (!e) return NaN;
  const s = (e.r !== null && e.r !== undefined) ? e.r : e.v;
  if (s === null || s === undefined) return NaN;
  if (/^\{/.test(String(s))) return NaN; // error object
  const n = parseFloat(String(s));
  return n;
}
function strVal(sheet, addr) {
  const e = cell(sheet, addr);
  if (!e) return null;
  const s = (e.r !== null && e.r !== undefined) ? e.r : e.v;
  if (s === null || s === undefined) return null;
  let t = String(s);
  if (t.startsWith('"') && t.endsWith('"') && t.length >= 2) t = t.slice(1, -1);
  return t;
}
function formulaVal(sheet, addr) {
  const e = cell(sheet, addr);
  if (!e) return null;
  return e.f;
}
function norm(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/^\s*=/, '').replace(/\s+/g, '');
}
const MOJI = [['Ã¼', 'ü'], ['Ã¤', 'ä'], ['Ã¶', 'ö'], ['Ã©', 'é'], ['Ã¨', 'è'], ['Ã¢', 'â'],
  ['Ã', 'Ã'], ['Â°', '°'], ['Â', ' ']];
function deMoji(s) {
  if (!s) return s;
  for (const [a, b] of MOJI) s = s.split(a).join(b);
  return s;
}
const TOL_REL = 2e-3; // 0.2% for chapter-rounded numbers

// ---------- result collection ----------
const results = [];
// severity: 'fail' (substantive) | 'warn' (quote precision / harmless simplification)
function check(id, chapter, ok, detail, severity) {
  results.push({ id, chapter, ok: !!ok, detail, severity: ok ? 'pass' : (severity || 'fail') });
}
function num(sheet, addr, expected, id, chapter, note, tol) {
  const got = numVal(sheet, addr);
  const t = tol !== undefined ? tol : Math.max(1e-9, Math.abs(expected) * TOL_REL);
  const ok = isFinite(got) && Math.abs(got - expected) <= t;
  check(id, chapter, ok, `${sheet}!${addr} = ${got} (expect ≈${expected}${note ? '; ' + note : ''})`);
  return ok;
}
function str(sheet, addr, expected, id, chapter, note, fuzzy) {
  const got = strVal(sheet, addr);
  const ok = got === expected || (fuzzy && deMoji(got) === deMoji(expected));
  check(id, chapter, ok, `${sheet}!${addr} = ${JSON.stringify(got)} (expect ${JSON.stringify(expected)}${note ? '; ' + note : ''})`);
  return ok;
}
function fmt(sheet, addr, expected, id, chapter, note, sev) {
  const got = formulaVal(sheet, addr);
  const ok = got !== null && norm(got) === norm(expected);
  check(id, chapter, ok, `${sheet}!${addr} formula ${ok ? 'MATCHES' : '≠'} (dump: ${got ? norm(got) : 'NONE'} / expect: ${norm(expected)}${note ? '; ' + note : ''})`, sev);
  return ok;
}
function fmtContains(sheet, addr, token, id, chapter, note, sev) {
  const got = formulaVal(sheet, addr);
  const ok = got !== null && norm(got).includes(norm(token));
  check(id, chapter, ok, `${sheet}!${addr} formula ${ok ? 'contains' : 'MISSING'} ${JSON.stringify(token)} (dump: ${got || 'NONE'}${note ? '; ' + note : ''})`, sev);
  return ok;
}
function exists(sheet, addr, id, chapter, note) {
  const e = cell(sheet, addr);
  check(id, chapter, !!e, `${sheet}!${addr} ${e ? 'exists' : 'MISSING'}${note ? '; ' + note : ''}`);
  return !!e;
}
function errVal(sheet, addr, expectedErr, id, chapter, note) {
  const e = cell(sheet, addr);
  const s = e ? String(e.r !== null && e.r !== undefined ? e.r : (e.v || '')) : '';
  const ok = s.includes(expectedErr);
  check(id, chapter, ok, `${sheet}!${addr} = ${JSON.stringify(s)} (expect error ${expectedErr}${note ? '; ' + note : ''})`);
  return ok;
}

// ---------- chapter 1 ----------
const ch1 = 'ch01';
{
  // 1.1 module constants (from VBA source)
  const vba = fs.readFileSync(path.join(MAIN, '../vba/gebaeude/FeuchteLuft_Formeln.bas'), 'utf8');
  const vbaFlat = vba.replace(/\s+/g, '');
  const vbaChecks = [
    ['cpl = 1.006', 'cpl = 1.006'],
    ['cpw = 1.86', 'cpw = 1.86'],
    ['r0 = 2501.6', 'r0 = 2501.6'],
    ['Glück ice coeff -4.909965', '-4.909965'],
    ['Glück ice coeff 8.183197', '8.183197'],
    ['Glück ice coeff -5.552967', '-5.552967'],
    ['Glück ice coeff -2.228376', '-2.228376'],
    ['Glück ice coeff -6.211808', '-6.211808'],
    ['Glück water coeff -1.91275', '-1.91275'],
    ['Glück water coeff 7.258', '7.258'],
    ['Glück water coeff -2.939', '-2.939'],
    ['Glück water coeff 9.841', '9.841'],
    ['Glück water coeff -1.92', '-1.92'],
    ['611 factor', '611 * Exp'],
    ['AbsFeuchte body', 'AbsFeuchte = (rF * 622 * ps) / (p - rF * ps)'],
    ['EnthalpieA body', 'EnthalpieA = cpl * T + x / 1000 * (r0 + cpw * T)'],
    ['RelFeuchte body', 'RelFeuchte = (x * p) / (ps * (622 + x))'],
    ['TemperaturH body', 'TemperaturH = (h - x * r0) / (cpl + cpw * x)'],
    ['TaupunktR pst', 'pst = p / (0.622 * 1000 / x + 1)'],
    ['TaupunktR Td', '((pst / 2.8858) ^ (1 / 8.02) - 1.098) * 100'],
    ['EnthalpieR body', 'x = 0.622 * (rF * 100 * ps) / (p * 100 - rF * 100 * ps)'],
    ['Feuchtkugel body', 'FK = -5.809 + 0.058 * rFein + 0.697 * Tein + 0.003 * rFein * Tein'],
    ['Feuchtkugel ice branch', 'Feuchtkugel = FK * 0.8 + 0.5'],
  ];
  for (const [label, token] of vbaChecks) {
    check('1.1-const-' + label.replace(/[^a-z0-9]/gi, ''), ch1, vbaFlat.includes(token.replace(/\s+/g, '')), `FeuchteLuft_Formeln.bas ${okW(vbaFlat.includes(token.replace(/\s+/g, '')))} ${JSON.stringify(token)}`);
  }
  function okW(b) { return b ? 'contains' : 'MISSING'; }
  // TaupunktA commented out
  const commented = /'Public Function TaupunktA/.test(vba) && !/^\s*Public Function TaupunktA\b/m.test(vba);
  check('1.1-TaupunktA-commented', ch1, commented, 'TaupunktA 整段注释状态确认');

  // 1.2 Saettigungsdruck polynomial checks: ps(-10) & consistency at T=0
  function psGlueck(T) {
    let a;
    if (T <= 0) a = [-4.909965e-4, 8.183197e-2, -5.552967e-4, -2.228376e-5, -6.211808e-7];
    else a = [-1.91275e-4, 7.258e-2, -2.939e-4, 9.841e-7, -1.92e-9];
    return 611 * Math.exp(a[0] + a[1] * T + a[2] * T * T + a[3] * T * T * T + a[4] * T * T * T * T) / 100;
  }
  const ps0 = psGlueck(0); // ice side
  const ps0w = psGlueck(1e-9 > 0 ? 0.001 : 0.001); // water side at T>0
  const jump = (ps0w - ps0) / ps0;
  check('1.2-ps0-jump', ch1, Math.abs(jump) < 0.002, `T=0 两段跳变 = ${(jump * 100).toFixed(4)}% (章节声称 0.03%)`);
  // 1.3 call point numeric: Klimadaten!Q20
  num('Klima', 'Q20', 1.5015, '1.3-Q20', ch1, 'AbsFeuchte(−10, 0.8817, 948.2)');
  str('Klima', 'M20', '-10', '1.3-M20', ch1, 'T=−10 °C');
  const n20 = numVal('Klima', 'N20');
  check('1.3-N20', ch1, Math.abs(n20 - 0.8817) < 1e-3, `Klima!N20 = ${n20} (章节 0.8817; 缓存 0.881666…=0.8817 取整)`);
  // formula of Q20
  fmt('Klima', 'Q20', 'AbsFeuchte(M20,N20,$F$44)', '1.3-Q20-formula', ch1, '调用示例公式');
  // AbsFeuchte recompute with full precision
  const x20 = (0.8816666666666667 * 622 * psGlueck(-10)) / (948.225968475814 - 0.8816666666666667 * psGlueck(-10));
  check('1.3-Q20-recompute', ch1, Math.abs(x20 - 1.501516346575252) < 1e-9, `重算 AbsFeuchte(−10, 0.8817, 948.226) = ${x20} (缓存 1.50152)`);

  // 1.4 EnthalpieA call points (formula shapes at row 121)
  fmt('BLU', 'N121', 'EnthalpieA(L121,M121,$N$19)*$E$35+(1-$E$35)*EnthalpieA(BU121,BW121,$N$19)', '1.4-N121-f', ch1, 'MIL 焓加权');
  fmt('BLU', 'Y121', 'EnthalpieA(W121,X121,$N$19)', '1.4-Y121-f', ch1, 'KRG 后焓');
  fmt('BLU', 'AB121', 'EnthalpieA(Z121,AA121,$N$19)', '1.4-AB121-f', ch1);
  fmt('BLU', 'AE121', 'EnthalpieA(AC121,AD121,$N$19)', '1.4-AE121-f', ch1);
  fmtContains('BLU', 'AJ121', 'EnthalpieA(', '1.4-AJ121-f', ch1, '盘管后焓');
  fmtContains('BLU', 'AM121', 'EnthalpieA(', '1.4-AM121-f', ch1);
  fmt('BLU', 'AS121', 'EnthalpieA(AQ121,AR121,$N$19)', '1.4-AS121-f', ch1, '级联 #VALUE!');
  fmtContains('BLU', 'AV121', 'EnthalpieA(', '1.4-AV121-f', ch1);
  fmt('BLU', 'BM121', 'EnthalpieA(BJ121,BL121,$N$19)', '1.4-BM121-f', ch1);
  fmt('BLU', 'BQ121', 'EnthalpieA(BN121,BP121,$N$19)', '1.4-BQ121-f', ch1);
  num('BLU', 'N121', 12.2406, '1.4-N121-v', ch1, 'MIL 焓 12.2406 kJ/kg');

  // 1.5 TemperaturH
  fmt('BLU', 'AN121', 'TemperaturH(AP121,AO121)', '1.5-AN121-f', ch1);
  num('BLU', 'AN121', 21.27, '1.5-AN121-v', ch1, 'TemperaturH(AP121=21.3979, AO121=0) → 21.27 °C', 0.01);
  num('BLU', 'AP121', 21.3979, '1.5-AP121-v', ch1, 'AP=BM=21.398', 1e-3);

  // 1.6 RelFeuchte call points
  fmt('BLU', 'E121', 'MIN(100%,RelFeuchte(BR121,C121,$N$19))', '1.6-E121-f', ch1);
  fmt('BLU', 'BK121', 'MIN(1,RelFeuchte(BJ121,BT121,$N$19))', '1.6-BK121-f', ch1);
  fmt('BLU', 'BO121', 'MIN(1,RelFeuchte(BN121,BP121,$N$19))', '1.6-BO121-f', ch1);
  fmt('BLU', 'BV121', 'RelFeuchte(BU121,BW121,$N$19)', '1.6-BV121-f', ch1);

  // 1.7 Taupunkt: power-law calibration claims
  const fit0 = 2.8858 * Math.pow(1.098, 8.02);
  const fit20 = 2.8858 * Math.pow(1.298, 8.02);
  check('1.7-fit-T0', ch1, Math.abs(fit0 - 6.108) < 0.01, `幂律拟合 p_s(0°C) = ${fit0.toFixed(3)} mbar (章节称 ≈6.11；Glück 真值 6.11；2025 修正)`);
  check('1.7-fit-T20', ch1, Math.abs(fit20 - 23.374) < 0.01, `幂律拟合 p_s(20°C) = ${fit20.toFixed(3)} mbar (章节称 ≈23.4；Glück 真值 23.4；2025 修正)`);
  // TaupunktA call
  fmt('BLU', 'AQ121', 'TaupunktA(AR121,$N$19)', '1.7-AQ121-f', ch1);
  errVal('BLU', 'AQ121', '#NAME?', '1.7-AQ121-err', ch1, 'TaupunktA 已注释');
  errVal('BLU', 'AS121', '#VALUE!', '1.7-AS121-err', ch1, '级联错误');

  // 1.8 Feuchtkugel: no workbook call — grep check
  const allBLU = fs.readFileSync(path.join(GEB, 'sheet_61_Berechnung LU.tsv'), 'utf8');
  const allKlima = fs.readFileSync(path.join(GEB, 'sheet_62_Klimadaten.tsv'), 'utf8');
  check('1.8-Feuchtkugel-dead', ch1, !/Feuchtkugel\(/.test(allBLU + allKlima), '工作簿公式无 Feuchtkugel( 调用');
  check('1.9-EnthalpieR-dead', ch1, !/EnthalpieR\(/.test(allBLU + allKlima), '工作簿公式无 EnthalpieR( 调用');
  check('1.7-TaupunktR-dead', ch1, !/TaupunktR\(/.test(allBLU + allKlima), '工作簿公式无 TaupunktR( 调用');
  check('1.2-Saettigungsdruck-dead', ch1, !/Saettigungsdruck\(/.test(allBLU + allKlima), '工作簿公式无 Saettigungsdruck( 调用');
}

// ---------- chapter 2 ----------
const ch2 = 'ch02';
{
  // 2.3 formula 1 — column selectors
  fmt('Gebaeude', 'F9', 'IF($B5=Begriffe!$F76,F8,IF($B5=Begriffe!$F77,F8+7,F8+14))', '2.3-F9', ch2);
  fmt('Gebaeude', 'G9', 'IF($B5=Begriffe!$F76,G8,IF($B5=Begriffe!$F77,G8+8,G8+16))', '2.3-G9', ch2);
  fmt('Gebaeude', 'N9', 'IF(B5=Begriffe!F76,N8,IF(B5=Begriffe!F77,N8+6,N8+12))', '2.3-N9', ch2, 'Lüftung 功率偏移 +6/+12（已知偏差）');
  fmt('Gebaeude', 'O9', 'IF(B5=Begriffe!F76,O8,IF(B5=Begriffe!F77,O8+7,O8+14))', '2.3-O9', ch2, 'Lüftung 能量偏移 +7/+14（已知偏差）');
  const base = { F8: 28, G8: 2, H8: 29, I8: 3, J8: 30, K8: 4, N8: 31, O8: 5, Q8: 32, R8: 6, T8: 33, U8: 7, V8: 8, W8: 8 };
  for (const [a, v] of Object.entries(base)) {
    num('Gebaeude', a, v, '2.3-base-' + a, ch2, '基础列号', 1e-9);
  }
  // 2.4 formula 2 — room row derivation
  fmt('Gebaeude', 'F12', 'IF($B12="",0,VLOOKUP($B12,Res,F$9,FALSE))*$D12/1000', '2.4-F12', ch2);
  // column mapping: F..W
  const colMap = { F: 28, G: 2, H: 29, I: 3, J: 30, K: 4, N: 31, O: 5, Q: 32, R: 6, T: 33, U: 7, W: 8 };
  for (const [c, resCol] of Object.entries(colMap)) {
    const cellAddr = c + '12';
    const f = formulaVal('Gebaeude', cellAddr);
    const ok = f && norm(f).includes('VLOOKUP($B12,Res,' + c + '$9,FALSE)');
    check('2.4-' + cellAddr, ch2, ok, `${cellAddr} VLOOKUP 列 ${c}$9 (dump: ${f || 'NONE'})`);
  }
  num('Gebaeude', 'F12', 27.5, '2.4-F12-v', ch2, 'Geräte 功率 kW (缓存)', 0.01);
  // gates
  for (const c of ['N', 'O', 'Q', 'R', 'T', 'U']) {
    const f = formulaVal('Gebaeude', c + '12');
    check('2.4-gate-' + c, ch2, f && norm(f).includes('IF(L12=FALSE,0,') || (c === 'Q' || c === 'R' || c === 'T' || c === 'U') && f && (norm(f).includes('IF(P12=FALSE,0,') || norm(f).includes('IF(S12=FALSE,0,')), `${c}12 门控公式 (dump: ${f || 'NONE'})`);
  }
  // 2.5 formula 3 — volume flow
  fmt('Gebaeude', 'M12', 'IF($B12="",0,VLOOKUP($B12,Std!$B$6:$H$50,M$8,0))*$D12+IF($B12="",0,VLOOKUP($B12,Std!$B$6:$H$50,4,0))*$D12', '2.5-M12', ch2);
  num('Gebaeude', 'M12', 5178.571428571429, '2.5-M12-v', ch2, '2.07143×2500 + 0×2500', 1e-6);
  num('Std', 'D10', 2.0714285714285716, '2.5-StdD10', ch2, 'Std!D10 卫生新风');
  num('Lueftung', 'D12', 1340, '2.5-LueftD12', ch2, 'Parkhaus: Gebäude!D21×Std!E47 = 670×2', 1e-9);
  // 2.6 formula 4 — WW demand
  fmt('Gebaeude', 'V12', 'IF($B12="",0,VLOOKUP($B12,Std!$B$6:$I$50,$V$8,0))*$D12', '2.6-V12', ch2);
  num('Gebaeude', 'V12', 535.7142857142857, '2.6-V12-v', ch2, '0.21429×2500', 1e-6);
  num('Std', 'I10', 0.21428571428571427, '2.6-StdI10', ch2, 'I10 = H10/C10 = 3/14');
  fmt('Std', 'I10', 'H10/C10', '2.6-StdI10-f', ch2);
  // 2.7 formula 5 — totals
  num('Gebaeude', 'D38', 7249, '2.7-D38', ch2, 'GF = D35×(100+D37)%', 0.01);
  num('Gebaeude', 'D39', 6512, '2.7-D39', ch2, 'EBF = SUMIF(TRUE)×(100+D37)%', 0.01);
  fmt('Gebaeude', 'D38', 'D35*(100+D37)%', '2.7-D38-f', ch2);
  fmt('Gebaeude', 'D39', 'SUMIF(C12:C32,TRUE,D12:D32)*(100+D37)%', '2.7-D39-f', ch2);
  num('Gebaeude', 'D37', 10, '2.7-D37', ch2, 'Anteil Konstruktionsfläche');
  num('Gebaeude', 'G39', 19.9149, '2.7-G39', ch2, '129.6861×1000/6512', 0.001);
  fmt('Gebaeude', 'G39', 'G35*1000/$D$39', '2.7-G39-f', ch2);
  // 2.8 formula 6 — Allg. Gebäudetechnik
  fmtContains('Gebaeude', 'E47', 'VLOOKUP(B47,$B$69:$F$85,C47+2,0)', '2.8-E47', ch2, 'AG01 按强度档查目录');
  fmtContains('Gebaeude', 'I47', 'E47*G47/1000', '2.8-I47', ch2);
  fmtContains('Gebaeude', 'L47', 'I47*1000/', '2.8-L47', ch2, '能量÷全负荷小时');
  num('Gebaeude', 'I58', 54.6442, '2.8-I58', ch2, 'AG 能量 Total MWh', 1e-4);
  num('Gebaeude', 'L58', 55.8229, '2.8-L58', ch2, 'AG 功率 Total kW', 1e-3);
  fmt('Gebaeude', 'I58', 'SUM(I47:I57)', '2.8-I58-f', ch2);
  fmt('Gebaeude', 'L58', 'SUM(L47:L57)', '2.8-L58-f', ch2);
  fmtContains('Gebaeude', 'I62', 'I58*1000/$D$39', '2.8-I62', ch2);
  fmtContains('Gebaeude', 'L62', 'L58*1000/$D$39', '2.8-L62', ch2);
  // 2.2 KPI matrix
  fmt('KZ', 'G7', 'Qhc_Klimastat!E7', '2.2-G7-f', ch2, 'Klimakälte 能量为公式');
  fmt('KZ', 'AG7', 'Qhc_Klimastat!D7', '2.2-AG7-f', ch2);
  const kz11 = { C11: 32.01, E11: 13.4458, F11: 4.443214, G11: 14.4301, H11: 10.7616, I11: 2.595086, AC11: 11, AF11: 1.139286, AG11: 43.6565, AH11: 19.82335 };
  for (const [a, v] of Object.entries(kz11)) {
    num('KZ', a, v, '2.2-kz-' + a, ch2, 'Einzel-, Gruppenbüro 行 11', 2e-3);
  }
  num('Qhc', 'D11', 43.6565, '2.2-qhc-D11', ch2, 'Qhc!D11 = KZ!AG11');
  num('Qhc', 'E11', 14.4301, '2.2-qhc-E11', ch2, 'Qhc!E11 = KZ!G11');
  num('Qhc', 'F11', 19.82335, '2.2-qhc-F11', ch2, 'Qhc!F11 = KZ!AH11');
  // 2.9 data flow
  const flow = { F35: 45.57, G35: 129.6861, J35: 41.3754, K35: 59.9020, Q35: 167.138, R35: 61.207, T35: 103.32, U35: 68.834, V35: 835.7143, W35: 10.1214 };
  for (const [a, v] of Object.entries(flow)) {
    num('Gebaeude', a, v, '2.9-' + a, ch2, 'Rechenwert');
  }
}

// ---------- chapter 3 ----------
const ch3 = 'ch03';
{
  // 3.2 Std table
  const std = { Q10: 3900, R10: 3900, S10: 3290, T10: 2740, U10: 2160, V10: 1780 };
  for (const [a, v] of Object.entries(std)) {
    num('Std', a, v, '3.2-' + a, ch3, 'Einzel-, Gruppenbüro');
  }
  // Volll_Lüft row 11 (code 3.01 / 1.03)
  const volll = { D11: 3900, E11: 3900, F11: 3290, I11: 2740, J11: 2160, Q11: 1780 };
  for (const [a, v] of Object.entries(volll)) {
    num('Volll', a, v, '3.2-volll-' + a, ch3, 'Volll_Lüft 行 1.03');
  }
  str('Std', 'L2', 'Quelle: SIA2024_Raumdatenblätter > tblVoll_Lüft', '3.1-L2', ch3, '来源注释', true);
  const l3 = strVal('Std', 'L3') || '';
  check('3.1-L3', ch3, l3.includes('prSIA 2024-C1:2024') && l3.includes('29'), `Std!L3 = ${JSON.stringify(l3)} (应含 prSIA 2024-C1:2024, 29 m³/h)`);
  // 3.4 formula 2
  fmt('BLU', 'K68', "IF($I$8=1,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),1),IF($I$8=2,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),3),IF($I$8=3,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),5),FALSE)))", '3.4-K68', ch3);
  fmt('BLU', 'K69', "IF($I$8=1,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),2),IF($I$8=2,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),4),IF($I$8=3,INDEX(Std!$Q$6:$V$50,MATCH('Berechnung LU'!$B$6,Std!$B$6:$B$50,0),6),FALSE)))", '3.4-K69', ch3);
  num('BLU', 'K68', 3900, '3.4-K68-v', ch3);
  num('BLU', 'K69', 3900, '3.4-K69-v', ch3);
  fmt('BLU', 'I8', "IF('Berechnung LU'!I6=Begriffe!F205,1,IF('Berechnung LU'!I6=Begriffe!F206,2,IF('Berechnung LU'!I6=Begriffe!F207,3,FALSE)))", '3.4-I8', ch3, '章节引用省略了同表前缀，语义一致', 'warn');  num('BLU', 'I8', 1, '3.4-I8-v', ch3, 'einstufig → 1');
  fmt('BLU', 'I6', "Lüftung!J32", '3.4-I6', ch3);
  str('BLU', 'I6', 'einstufig', '3.4-I6-v', ch3, '当前系统 Regelung', false);
  // 3.5 formula 3
  fmt('BLU', 'H7', 'C259/1000', '3.5-H7', ch3);
  fmt('BLU', 'J7', 'ROUND(IF(G6=0,0,H7*1000/G6),-1)', '3.5-J7', ch3);
  num('BLU', 'H7', 26.7651, '3.5-H7-v', ch3, '风机电能 MWh', 1e-3);
  num('BLU', 'J7', 3900, '3.5-J7-v', ch3, '反推全负荷小时');
  fmt('Lueftung', 'K7', 'IF(H7=0,0,ROUND(I7*1000/H7,-1))', '3.5-LueftK7', ch3);
  fmt('Lueftung', 'H7', 'F7*G7/1000', '3.5-LueftH7', ch3);
  num('Lueftung', 'K7', 3900, '3.5-LueftK7-v', ch3);
  // 3.6 use chain
  fmt('BLU', 'K70', 'E7*K68/8760', '3.6-K70', ch3);
  fmt('BLU', 'M70', 'G6*K69/K68', '3.6-M70', ch3);
  num('BLU', 'K70', 3819.227, '3.6-K70-v', ch3, '年加权平均风量', 1e-3);
  num('BLU', 'M70', 6.862857, '3.6-M70-v', ch3, '年加权平均风机功率', 1e-3);
  fmtContains('BLU', 'I20', 'E52*1000)/(3600*(K70/3600)*N23)', '3.6-I20', ch3, 'Feuchtelast 用 K70');
}

// ---------- chapter 4 ----------
const ch4 = 'ch04';
{
  // constants
  const consts = { N19: 948.226, N20: 1.006, N21: 1.86, N22: 4.19, N23: 1.15, N24: 2501.6, N25: 2256 };
  for (const [a, v] of Object.entries(consts)) {
    num('BLU', a, v, '4.0-' + a, ch4, '物性常量', v > 100 ? 1e-2 : 1e-6);
  }
  fmt('BLU', 'N19', 'Klimadaten!F44', '4.0-N19-f', ch4);
  // 4.4 formula 1
  fmt('BLU', 'B121', 'Klimadaten!O5/8760*$K$68', '4.4-B121', ch4);
  num('BLU', 'B121', 0, '4.4-B121-v', ch4, '−25 °C 区间小时数 0');
  num('BLU', 'B136', 2.67123, '4.4-B136', ch4, '6/8760×3900', 1e-3);
  num('BLU', 'B168', 59.65753, '4.4-B168', ch4, '134/8760×3900', 1e-3);
  num('Klima', 'O20', 6, '4.4-O20', ch4, 'Klimadaten!O20 区间小时数');
  num('Klima', 'O52', 134, '4.4-O52', ch4, 'Klimadaten!O52 区间小时数');
  // 4.5 formula 2
  fmt('BLU', 'C121', 'Klimadaten!Q5', '4.5-C121', ch4, 'x_A = Klimadaten!Q{k+30}');
  fmt('BLU', 'E121', 'MIN(100%,RelFeuchte(BR121,C121,$N$19))', '4.5-E121', ch4);
  fmtContains('BLU', 'G121', 'IF(A121<=$E$33', '4.5-G121', ch4, '防冻预热分支');
  fmtContains('BLU', 'DB121', 'IF(A121<=$E$33,$F$113,0)', '4.5-DB121', ch4, '开关式防冻');
  fmtContains('BLU', 'DC121', 'IF(A121<=$E$33,ABS($K$70*$N$20*$N$23*', '4.5-DC121', ch4, '可变式防冻');
  num('BLU', 'F113', 15.9556, '4.5-F113', ch4, '防冻加热功率 kW', 1e-3);
  // 4.6 formula 3 WRG
  fmt('BLU', 'I168', '$E$28*(BU168-A168)+A168', '4.6-I168-f', ch4);
  num('BLU', 'I168', 23.6, '4.6-I168', ch4, '22+0.8×(24−22)', 1e-6);
  fmtContains('BLU', 'J168', 'IF(F168=0,MIN(I168,BJ168),I168)', '4.6-J168-f', ch4);
  num('BLU', 'J168', 20, '4.6-J168', ch4, 'MIN(23.6, 20)');
  fmtContains('BLU', 'K168', 'MAX(IF(AND($E$31=$S$20,F168=1),0,IF(A168=BU168,0,(J168-A168)/(BU168-A168))),0)', '4.6-K168-f', ch4, '调节效率');
  num('BLU', 'K168', 0, '4.6-K168', ch4, '夏季全旁通 ε=0');
  num('BLU', 'L168', 22, '4.6-L168', ch4, '旁通后送风侧温度');
  fmtContains('BLU', 'M168', '$E$28=0,C168', '4.6-M168-f', ch4, '湿度回收 E29=0 → x_A');
  fmt('BLU', 'F168', 'IF(H168<=0,IF(BU168<A168,1,0),0)', '4.6-F168-f', ch4, '夏季冷却标志');
  num('BLU', 'BU168', 24, '4.6-BU168', ch4, '排风温度 = 室温 24 °C');
  num('BLU', 'BW168', 10.03672, '4.6-BW168', ch4, '排风含湿量 = BT+I20', 1e-3);
  // 4.7 formula 4 MIL
  fmt('BLU', 'N168', 'EnthalpieA(L168,M168,$N$19)*$E$35+(1-$E$35)*EnthalpieA(BU168,BW168,$N$19)', '4.7-N168-f', ch4);
  fmtContains('BLU', 'O168', '$E$34', '4.7-O168-f', ch4, 'γ_min');
  fmtContains('BLU', 'P168', '1-IF(EnthalpieA(L168,M168,$N$19)=S168', '4.7-P168-f', ch4, '回风份额');
  fmtContains('BLU', 'Q168', 'L168*(1-P168)+BU168*P168', '4.7-Q168-f', ch4);
  fmtContains('BLU', 'R168', 'M168*(1-P168)+BW168*P168', '4.7-R168-f', ch4);
  fmtContains('BLU', 'S168', 'MIN(MAX(N168,BM168),O168)', '4.7-S168-f', ch4, '目标焓');
  fmtContains('BLU', 'T168', 'MIN(', '4.7-T168-f', ch4, 'MIN 单参 no-op');
  fmtContains('BLU', 'V168', '1-IF(L168=W168', '4.7-V168-f', ch4);
  fmtContains('BLU', 'W168', 'MIN(MAX(T168,BJ168),U168)', '4.7-W168-f', ch4);
  fmtContains('BLU', 'X168', 'M168*(1-$V168)+BW168*$V168', '4.7-X168-f', ch4);
  fmt('BLU', 'Y168', 'EnthalpieA(W168,X168,$N$19)', '4.7-Y168-f', ch4);
  // 4.8 formula 5 coil
  fmt('BLU', 'Z168', 'AVERAGE($E$45:$F$46)', '4.8-Z168-f', ch4);
  num('BLU', 'Z168', 9, '4.8-Z168', ch4, '盘管表面温度');
  fmt('BLU', 'AA168', 'IF($E$36=$D$36,MIN(AbsFeuchte(Z168,100%,$N$19),R168),MIN(AbsFeuchte(Z168,100%,$N$19),X168))', '4.8-AA168-f', ch4);
  num('BLU', 'AA168', 7.617, '4.8-AA168', ch4, 'x_sat(9°C)', 2e-3);
  fmt('BLU', 'AF168', 'AVERAGE($E$45:$E$46)', '4.8-AF168-f', ch4);
  num('BLU', 'AF168', 9, '4.8-AF168', ch4);
  fmtContains('BLU', 'AG168', '(Q168-AF168)/(R168-AA168)', '4.8-AG168-f', ch4, '线性冷却曲线斜率');
  num('BLU', 'AG168', 5.372, '4.8-AG168', ch4, '(22−9)/(10.037−7.617)', 3e-3);
  fmtContains('BLU', 'AH168', 'MAX(IF(R168>BL168,AF168+(AG168*(BL168-AA168)),Q168),Z168)', '4.8-AH168-f', ch4, 'D1');
  fmtContains('BLU', 'AK168', 'MAX(MIN(W168,BJ168),Z168)', '4.8-AK168-f', ch4, 'D2 (温度控分支)');
  num('BLU', 'AK168', 20, '4.8-AK168', ch4, 'MAX(MIN(22,20),9)');
  fmtContains('BLU', 'AL168', '(BJ168-AF168)/AG168+AA168', '4.8-AL168-f', ch4, '沿曲线插值');
  num('BLU', 'AL168', 9.664, '4.8-AL168', ch4, '(20−9)/5.372+7.617', 3e-3);
  num('BLU', 'AM168', 44.66, '4.8-AM168', ch4, 'h(20, 9.664)', 0.02);
  // 4.9 formula 6 Fall
  fmtContains('BLU', 'AW168', 'IF($E$36=$C$36,IF(AND(ROUND(BM168,4)>=ROUND(S168,4),ROUND(BL168,4)>=ROUND(R168,4),ROUND(BJ168,4)>=ROUND(Q168,4)),1,IF(ROUND(BL168,4)<ROUND(AA168,4),2,IF(ROUND(BJ168,4)>=ROUND(AH168,4),3,4)))', '4.9-AW168-f', ch4);
  num('BLU', 'AW168', 4, '4.9-AW168', ch4, '夏季冷却工况');
  fmtContains('BLU', 'BB168', 'Fall1Tzul(AX168,AY168,BJ168', '4.9-BB168-f', ch4, 'Fall1 活代码');
  fmtContains('BLU', 'BD168', 'Fall2Tzul(AX168', '4.9-BD168-f', ch4, 'Fall2 活代码');
  fmtContains('BLU', 'BC168', 'Fall1xzul(', '4.9-BC168-f', ch4);
  fmtContains('BLU', 'BE168', 'Fall2xzul(', '4.9-BE168-f', ch4);
  fmt('BLU', 'BN168', 'BB168+BD168+BF168+BH168', '4.9-BN168-f', ch4);
  fmt('BLU', 'BP168', 'BC168+BE168+BG168+BI168', '4.9-BP168-f', ch4);
  fmt('BLU', 'BQ168', 'EnthalpieA(BN168,BP168,$N$19)', '4.9-BQ168-f', ch4);
  num('BLU', 'BN168', 20, '4.9-BN168', ch4, 't_ZUL,ist');
  num('BLU', 'BP168', 10.0367, '4.9-BP168', ch4, 'x_ZUL,ist (Fall 4 加湿到设定)', 1e-3);
  num('BLU', 'BQ168', 45.6012, '4.9-BQ168', ch4, 'h_ZUL,ist', 1e-3);
  num('BLU', 'BH168', 20, '4.9-BH168', ch4);
  num('BLU', 'BI168', 10.0367, '4.9-BI168', ch4, 1e-3);
  // 4.10 formula 7 setpoints
  fmt('BLU', 'BJ168', 'IF($DA168<=$B$89,$C$89-($B$89-$DA168)*$I$88,IF($DA168<=$B$90,$C$90-($B$90-$DA168)*$I$89,$C$91-($B$91-$DA168)*$I$90))', '4.10-BJ168-f', ch4);
  num('BLU', 'BJ168', 20, '4.10-BJ168', ch4, 't_ZUL,soll');
  fmt('BLU', 'BK168', 'MIN(1,RelFeuchte(BJ168,BT168,$N$19))', '4.10-BK168-f', ch4);
  fmt('BLU', 'BL168', 'AbsFeuchte(BJ168,BK168,$N$19)', '4.10-BL168-f', ch4);
  fmt('BLU', 'BM168', 'EnthalpieA(BJ168,BL168,$N$19)', '4.10-BM168-f', ch4);
  num('BLU', 'BL168', 10.0367, '4.10-BL168', ch4, 1e-3);
  num('BLU', 'BM168', 45.6012, '4.10-BM168', ch4, 1e-3);
  fmtContains('BLU', 'BS168', 'IF(E168<$E$50,$E$50,IF(E168>$E$48,$E$48,E168))', '4.10-BS168-f', ch4, '室温 rF 限幅');
  fmtContains('BLU', 'BT168', 'AbsFeuchte(BR168,BS168,$N$19)', '4.10-BT168-f', ch4);
  fmt('BLU', 'BV168', 'RelFeuchte(BU168,BW168,$N$19)', '4.10-BV168-f', ch4);
  // temperature curve breakpoints
  const curve = { B88: -15, C88: 21, D88: 22, B89: 22, C89: 20, D89: 24, B90: 24, C90: 20, D90: 25, B91: 30, C91: 20, D91: 25, I88: -0.0270, J88: 0.0541, I89: 0, J89: 0.5, I90: 0, J90: 0 };
  for (const [a, v] of Object.entries(curve)) {
    num('BLU', a, v, '4.10-curve-' + a, ch4, '温度曲线折点/斜率', 3e-3);
  }
  // 4.11 formula 8 enthalpy diff & energy
  fmtContains('BLU', 'BZ168', 'MAX(IF(AZ168=1,IF(OR(AW168=3,AW168=4,AW168=2),Y168-AM168,0),0),0)', '4.11-BZ168-f', ch4, '冷却焓差');
  fmtContains('BLU', 'CA168', 'IF(AW168=3,AM168-AJ168', '4.11-CA168-f', ch4, '除湿冷却');
  fmtContains('BLU', 'CB168', 'IF(AW168=3,BQ168-AJ168', '4.11-CB168-f', ch4, '除湿再热');
  // CC168: chapter presents 温度控分支 only; actual formula has IF($E$36=$D$36,...) dispatcher with both branches
  fmtContains('BLU', 'CC168', 'IF(F168=1,0,IF($E$36=$D$36,IF(AX168=1,IF(AW168=1,AV168-S168,0),0),IF(AX168=1,IF(AW168=1,AV168-Y168,0),0)))', '4.11-CC168-f', ch4, '章节仅引温度控分支；实际含焓/温控分派', 'warn');
  fmtContains('BLU', 'CD168', 'IF(AND(AY168=1,B168>0),IF(OR(AW168=1,AW168=4),BQ168-AV168,0),0)', '4.11-CD168-f', ch4, '加湿加热');
  fmt('BLU', 'BX168', 'SUM(BZ168:CA168)', '4.11-BX168-f', ch4, '章节写 BZ+CA；实际用 SUM，语义等价', 'warn');
  fmt('BLU', 'BY168', 'SUM(CB168:CD168)', '4.11-BY168-f', ch4, '章节写 CB+CC+CD；实际用 SUM，语义等价', 'warn');
  fmtContains('BLU', 'CJ168', '$K$70*B168*$N$23*(BZ168)/3.6/1000000', '4.11-CJ168-f', ch4, '冷却能量');
  num('BLU', 'CJ168', 0.21795, '4.11-CJ168', ch4, '3819.23×59.6575×1.15×2.9945/3.6e6', 1e-4);
  fmtContains('BLU', 'CT168', 'B168*($M$70)/1000', '4.11-CT168-f', ch4, '风机能量');
  num('BLU', 'CT168', 0.40942, '4.11-CT168', ch4, '59.6575×6.8629/1000', 2e-4);
  // CH168: chapter shows 温度控 K70 形式; actual has 焓/温控 × 夏季 dV (P70) 分派
  fmtContains('BLU', 'CH168', 'MAX(0,(BP168-R168)*B168*$K$70*$N$23/1000)', '4.11-CH168-f', ch4, '章节仅引 K70 温度控分支；实际含 P70 夏季分支', 'warn');
  fmtContains('BLU', 'CI168', '(CH168*$N$22*(100-$E$51)+$N$25*CH168)/3600000', '4.11-CI168-f', ch4, '蒸汽加湿能量');
  fmtContains('BLU', 'CM168', 'IF($E$49=$S$16,0,IF($E$49=$S$17,CG168,CI168))', '4.11-CM168-f', ch4, '按加湿方式');
  fmt('BLU', 'CW168', 'SUM(CK168,CJ168,CE168,CF168,CM168,CT168)', '4.11-CW168-f', ch4, '区间总能量');
  // 4.12 formula 9 summaries
  for (const c of ['CJ', 'CK', 'CE', 'CF', 'CM', 'CT', 'CH', 'CL']) {
    const f = formulaVal('BLU', c + '182');
    const ok = f && norm(f) === 'SUM(' + c + '122:' + c + '181)';
    check('4.12-sum-' + c, ch4, ok, `${c}182 = ${f || 'NONE'} (expect SUM(${c}122:${c}181))`);
  }
  for (const c of ['BZ', 'CA', 'CB', 'CD']) {
    const f = formulaVal('BLU', c + '183');
    const range = c === 'CC' ? 'CC$133:CC$181' : c + '$121:' + c + '$181';
    const ok = f && norm(f).includes('MAX(' + range + ')*$E$18*$N$23/3600');
    check('4.12-max-' + c, ch4, ok, `${c}183 = ${f || 'NONE'} (expect MAX(${range})×E18×N23/3600)`);
  }
  const res254 = { C254: 1750.16, D254: 25.7809, C255: 3786.30, D255: 16.1535, C256: 0, D256: 0, C257: 0, D257: 0, C258: 0, D258: 0, C259: 26765.14, D259: 6.862857, C260: 32301.60, D260: 48.7972 };
  for (const [a, v] of Object.entries(res254)) {
    num('BLU', a, v, '4.12-' + a, ch4, '年度结果行', a.startsWith('D') ? 5e-3 : 0.02);
  }
  fmt('BLU', 'C254', 'IFERROR(CJ182*1000,0)', '4.12-C254-f', ch4);
  fmt('BLU', 'D254', 'BZ183', '4.12-D254-f', ch4);
  fmt('BLU', 'D259', 'G6', '4.12-D259-f', ch4);
  fmt('BLU', 'C260', 'SUM(C254:C259)', '4.12-C260-f', ch4);
  // row 7
  const row7 = { P7: 'D254', Q7: 'C254/1000', R7: 'D255', S7: 'C255/1000', T7: 'D256', U7: 'C256/1000', V7: 'D257', W7: 'C257/1000', X7: 'D258', Y7: 'C258/1000' };
  for (const [a, expr] of Object.entries(row7)) {
    fmt('BLU', a, expr, '4.12-row7-' + a, ch4);
  }
  num('BLU', 'P7', 25.7809, '4.12-P7', ch4, 5e-3);
  num('BLU', 'Q7', 1.75016, '4.12-Q7', ch4, 1e-4);
  num('BLU', 'S7', 3.78630, '4.12-S7', ch4, 1e-4);
  // Lüftung wiring
  const wiring = { U32: 'V7', V32: 'W7', W32: 'X7', X32: 'Y7', Y32: 'T7', Z32: 'U7', Q32: 'P7', R32: 'Q7', S32: 'R7', T32: 'S7', I32: 'H7', K32: 'J7' };
  for (const [a, src] of Object.entries(wiring)) {
    fmt('Lueftung', a, "'Berechnung LU'!" + src, '4.12-wire-' + a, ch4, '接线（含错位）');
  }
  num('Lueftung', 'Q32', 25.7809, '4.12-Q32', ch4, 5e-3);
  num('Lueftung', 'Y32', 3.894e-14, '4.12-Y32', ch4, '≈0 (错位链 0 值)', 1e-10);
  // 4.13 formula 10 fans
  fmt('BLU', 'E19', 'IF(OR(I6="einstufig",I6="1 vitesse",I6="1 velocità"),E18,E18*0.67)', '4.13-E19', ch4);
  fmt('BLU', 'E20', 'IF(OR(I6="einstufig",I6="1 vitesse",I6="1 velocità"),E18,IF(OR(I6="zweistufig",I6="2 vitesses",I6="2 velocità"),E18*0.67,E18*0.33))', '4.13-E20', ch4);
  fmt('BLU', 'I14', 'IF(E18<MAX(E19:E20),IF(ISERROR(E16*(E18^2.5)/(E19^2.5)),0,E16*(E18^2.5)/(MAX(E18:E20)^2.5)),E16)', '4.13-I14', ch4, 'P∝V^2.5');
  num('BLU', 'E18', 8578.571, '4.13-E18', ch4, 1e-3);
  num('BLU', 'E16', 3.43143, '4.13-E16', ch4, 'G6/2', 1e-4);
  num('BLU', 'M67', 6.862857, '4.13-M67', ch4, '= G6 一致性', 1e-5);
  num('BLU', 'M58', 0.625, '4.13-M58', ch4, '档位 1 时间占比', 1e-6);
  num('BLU', 'L58', 50, '4.13-L58', ch4, '因子 1');
  num('BLU', 'L61', 80, '4.13-L61', ch4, '80 h/周');
  // 4.14 quirks
  errVal('BLU', 'AQ121', '#NAME?', '4.14-AQ121', ch4);
  errVal('BLU', 'AS121', '#VALUE!', '4.14-AS121', ch4);
  num('BLU', 'AD181', 59, '4.14-AD181', ch4, 'AD = n−122');
  num('BLU', 'AE181', 157.6, '4.14-AE181', ch4, 'h(9, 59 g/kg) 过饱和', 0.5);
  fmtContains('BLU', 'T121', 'MIN(', '4.14-T121', ch4, 'MIN 单参 no-op');
  // inputs from 4.3
  const inp = { C6: 8578.571, D6: 0, E6: 0, F6: 0.8, K6: 80, L6: 20, M6: 21, E11: 500, E12: 3, E28: 0.8, E33: 0, E32: 0, E39: 'ja', E40: -13, E42: 'ja', E43: 35, E45: 6, E46: 12, E47: 'ja', E49: 'Adiabatisch Bef.', E51: 10, E52: 0, E54: 'Benutzerdefiniert' };
  for (const [a, v] of Object.entries(inp)) {
    if (typeof v === 'number') num('BLU', a, v, '4.3-' + a, ch4, 'IST 输入', 1e-3);
    else str('BLU', a, v, '4.3-' + a, ch4);
  }
  // motor efficiency table
  num('BLU', 'C108', 1, '4.3-C108', ch4, 'η_ZUL,IST = IE5 行');
  num('BLU', 'B102', 1, '4.3-B102', ch4, 'IE5 行功率带查表');
  fmtContains('BLU', 'B102', 'IF(E$16<1.1,N11', '4.3-B102-f', ch4);
  fmtContains('BLU', 'C102', 'IF(E$17=A102,B102,0)', '4.3-C102-f', ch4);
  num('BLU', 'B110', 0, '4.3-B110', ch4, '过滤器压降 0 Pa');
}

// ---------- chapter 5 ----------
const ch5 = 'ch05';
{
  // 5.2 catalog
  const ng = { E3: 3, E4: 4, E5: 4, E6: 7.5, E7: 15, E8: 15, E11: 0.8, E12: 0.8, E13: 0.6, E14: 0.7, E15: 0.7, E16: 0.98, E17: 0.93, E18: 1, E19: 0.5, E21: 3, E22: 2.2, E23: 4.3, E24: 3.1, E25: 4.3, E26: 3.1, E29: 0.75, E30: 0.75, E31: 0.55, E32: 0.6, E33: 0.65, E34: 1, E35: 1, E36: 0.65, E38: 0.5, E39: 2.2, E40: 2.4, E41: 1.9 };
  for (const [a, v] of Object.entries(ng)) {
    num('Nutzungsgrad', a, v, '5.2-' + a, ch5, '目录 Nutzungsgrad', 1e-6);
  }
  const ngNames = { C3: 'Kompaktkältemaschine 7°C', C4: 'Kompaktkältemaschine 14°C', C11: 'Ölfeuerung kondensierend ', C21: 'Wärmepumpe Aussenluft 35°C', C25: 'Wärmepumpe Grundwasser 35°C' };
  for (const [a, v] of Object.entries(ngNames)) {
    str('Nutzungsgrad', a, v, '5.2-name-' + a, ch5, '', true);
  }
  // 5.4 formula 1
  fmt('Erzeugung', 'L7', '(Gebäude!Q$35+Lüftung!Q$23)*F7%*(100+IF($J7<>"",$J7,$H7))%', '5.4-L7-f', ch5);
  num('Erzeugung', 'L7', 134.357, '5.4-L7', ch5, '(167.138+36.433)×0.6×1.1', 1e-3);
  num('Erzeugung', 'M7', 55.7223, '5.4-M7', ch5, '(61.207+2.113)×0.8×1.1', 1e-3);
  num('Erzeugung', 'L8', 89.5714, '5.4-L8', ch5, '223.928×0.4×1.1', 1e-3);
  num('Erzeugung', 'M8', 13.9306, '5.4-M8', ch5, 1e-3);
  num('Erzeugung', 'L10', 223.928, '5.4-L10', ch5, '203.571×1.1', 1e-3);
  num('Erzeugung', 'F7', 60, '5.4-F7', ch5);
  num('Erzeugung', 'G7', 80, '5.4-G7', ch5);
  num('Erzeugung', 'H7', 10, '5.4-H7', ch5);
  fmt('Erzeugung', 'M7', '(Gebäude!R$35+Lüftung!R$23)*G7%*(100+IF($J7<>"",$J7,$H7))%', '5.4-M7-f', ch5);
  // 5.5 formula 2 WW
  fmt('Erzeugung', 'L25', 'Gebäude!V$35*4.186/3.6*50/L$29/1000*F25%*(100+IF($J25<>"",$J25,$H25))%', '5.5-L25-f', ch5);
  num('Erzeugung', 'L25', 3.401125, '5.5-L25', ch5, '835.7×(4.186/3.6)×50/6/1000×0.3×1.4', 1e-4);
  num('Erzeugung', 'L29', 6, '5.5-L29', ch5, 'Aufheizzeit 6 h/d');
  num('Erzeugung', 'F25', 30, '5.5-F25', ch5);
  num('Erzeugung', 'H25', 40, '5.5-H25', ch5);
  fmt('Erzeugung', 'M25', '(Gebäude!W$35*G25%)*(100+IF($J25<>"",$J25,$H25))%', '5.5-M25-f', ch5);
  // 5.6 formula 3
  fmt('Erzeugung', 'N7', 'IF(L7=0,0,M7*1000/L7)', '5.6-N7-f', ch5);
  fmt('Erzeugung', 'P7', 'IF(D7=0,0,$L7/IF($E7<>"",$E7,$D7))', '5.6-P7-f', ch5);
  fmt('Erzeugung', 'Q7', 'IF(D7=0,0,$M7/IF($E7<>"",$E7,$D7))', '5.6-Q7-f', ch5);
  num('Erzeugung', 'N7', 414.733, '5.6-N7', ch5, '55.72×1000/134.36', 1e-2);
  num('Erzeugung', 'P7', 11.1964, '5.6-P7', ch5, '134.36/12', 1e-3);
  num('Erzeugung', 'Q7', 4.64353, '5.6-Q7', ch5, '55.72/12', 1e-3);
  num('Erzeugung', 'E7', 12, '5.6-E7', ch5, '项目 COP');
  num('Erzeugung', 'D7', 15, '5.6-D7', ch5, '标准 COP (KE06)');
  fmt('Erzeugung', 'N10', 'M10*1000/L10', '5.6-N10-f', ch5, 'Total 行无 IF 守卫');
  // 5.7 PV/WKK
  const ee = { D34: 30, G34: 0.21, O34: 8, P34: -45, Q34: 0.83, D35: 5, E35: 16, G35: 0.27, H35: 0.51, L35: 3500 };
  for (const [a, v] of Object.entries(ee)) {
    num('Erzeugung', a, v, '5.7-' + a, ch5, 'Elektrizitätserzeugung');
  }
  // 5.8 matrix
  const mat = { D7: 55.8229, E7: 54.6442, F7: 45.57, G7: 129.6861, H7: 3, I7: 21.03, J7: 41.3754, K7: 59.9020, L7: 9.20786, M7: 32.4834, N7: 33.5893, O7: 8.12617, P7: 17.7691, Q7: 11.8202, R7: 1.25968, S7: 2.62392, T7: 207.594, U7: 320.316 };
  for (const [a, v] of Object.entries(mat)) {
    num('Resultate', a, v, '5.8-' + a, ch5, 'El 行矩阵', 2e-3);
  }
  fmt('Resultate', 'O7', 'SUMIF(Erzeugung!$R$7:$R$9,$B7,Erzeugung!$Q$7:$Q$9)', '5.8-O7-f', ch5);
  fmt('Resultate', 'P7', 'SUMIF(Erzeugung!$R$16:$R$18,$B7,Erzeugung!$P$16:$P$18)', '5.8-P7-f', ch5);
  fmt('Resultate', 'Q7', 'SUMIF(Erzeugung!$R$16:$R$18,$B7,Erzeugung!$Q$16:$Q$18)', '5.8-Q7-f', ch5);
  fmt('Resultate', 'R7', 'SUMIF(Erzeugung!$R$25:$R$27,$B7,Erzeugung!$P$25:$P$27)', '5.8-R7-f', ch5);
  fmt('Resultate', 'S7', 'SUMIF(Erzeugung!$R$25:$R$27,$B7,Erzeugung!$Q$25:$Q$27)', '5.8-S7-f', ch5);
  fmt('Resultate', 'T7', 'SUM(D7,F7,H7,J7,L7,N7,P7,R7)', '5.8-T7-f', ch5);
  fmt('Resultate', 'U7', 'E7+G7+I7+K7+M7+O7+Q7+S7', '5.8-U7-f', ch5);
  // 5.9 formula 5 sums
  num('Resultate', 'Q10', 23.2182, '5.9-Q10', ch5, 'Pell Heizung', 1e-3);
  num('Resultate', 'S10', 4.35974, '5.9-S10', ch5, 'Pell WW', 1e-3);
  num('Resultate', 'U15', 347.894, '5.9-U15', ch5, 'Endenergie 合计', 1e-3);
  // 5.10 formula 6 weights
  const w = { W7: 2, X7: 2.69, Y7: 0.139, W8: 1, X8: 1.22, Y8: 0.298, W9: 1, X9: 1.06, Y9: 0.228, W10: 0.7, X10: 0.2, Y10: 0.034, W11: 0.7, X11: 0.06, Y11: 0.022, W12: 0.7, X12: 0.05, Y12: 0.022, W13: 1, X13: 0.31, Y13: 0.132, W14: 0.6, X14: 0.55, Y14: 0.1 };
  for (const [a, v] of Object.entries(w)) {
    num('Resultate', a, v, '5.10-w-' + a, ch5, '权重');
  }
  fmt('Resultate', 'E21', 'SUMPRODUCT(E$7:E$17*W7:W17)', '5.10-E21-f', ch5);
  fmt('Resultate', 'D21', 'E21*1000/Gebäude!$D$39', '5.10-D21-f', ch5);
  num('Resultate', 'E21', 109.2884, '5.10-E21', ch5, '54.644×2', 1e-3);
  num('Resultate', 'G21', 259.3722, '5.10-G21', ch5, '129.686×2', 1e-3);
  num('Resultate', 'U21', 620.80, '5.10-U21', ch5, 0.01);
  num('Resultate', 'D21', 16.7826, '5.10-D21', ch5, 'E21×1000/6512', 1e-3);
  // 5.10 bugs
  fmt('Resultate', 'I21', 'SUMPRODUCT(I$7:I$17*Y7:Y17)', '5.10-I21-bug', ch5, '已知错误：误用 THGE 权重列 Y');
  fmt('Resultate', 'G22', 'SUMPRODUCT(E$7:E$17*$X7:$X17)', '5.10-G22-bug', ch5, '已知错误：重复 E 列');
  fmt('Resultate', 'F22', 'G22*1000/Gebäude!$D$39', '5.10-F22-bug', ch5);
  num('Resultate', 'I21', 2.92317, '5.10-I21-v', ch5, '= I25 相同', 1e-4);
  num('Resultate', 'I25', 2.92317, '5.10-I25-v', ch5, 1e-4);
  num('Resultate', 'G22', 146.993, '5.10-G22-v', ch5, '146.99 (错误值)', 1e-2);
  num('Resultate', 'F22', 22.5726, '5.10-F22-v', ch5, '22.57 kWh/m²', 1e-3);
  fmt('Resultate', 'E22', 'SUMPRODUCT(E$7:E$17*$X7:$X17)', '5.10-E22-f', ch5);
  // energy balance
  fmt('Resultate', 'C31', 'Gebäude!R35*1000/Gebäude!D39', '5.8-C31-f', ch5);
  num('Resultate', 'C31', 9.39918, '5.8-C31', ch5, '61.207×1000/6512', 1e-3);
  fmt('Resultate', 'C37', 'Lüftung!V23*1000/Gebäude!D39', '5.8-C37-f', ch5);
  fmt('Resultate', 'C38', 'Lüftung!X23*1000/Gebäude!D39', '5.8-C38-f', ch5);
  num('Resultate', 'C37', 0, '5.8-C37', ch5);
  num('Resultate', 'C38', 0, '5.8-C38', ch5);
  // 5.3 demand sources
  fmtContains('Erzeugung', 'L16', 'Gebäude!T$35+Lüftung!S$23', '5.3-L16-f', ch5, 'Wärme 需求源');
  fmtContains('Erzeugung', 'M16', 'Gebäude!U$35+Lüftung!T$23', '5.3-M16-f', ch5);
  fmtContains('Erzeugung', 'A7', 'INDEX(Nutzungsgrad!$B$3:$C$8,MATCH(Erzeugung!B7,Nutzungsgrad!$C$3:$C$8,0),1)', '5.3-A7-f', ch5);
  fmtContains('Erzeugung', 'D7', 'VLOOKUP($B7,Nutzungsgrad!$C$3:$G$8,3,FALSE)', '5.3-D7-f', ch5);
  fmtContains('Erzeugung', 'R7', 'VLOOKUP($B7,Nutzungsgrad!$C$3:$G$8,4,FALSE)', '5.3-R7-f', ch5);
}

// ---------- chapter 6 ----------
const ch6 = 'ch06';
{
  // 6.3 formula 1 pressure
  fmt('Klima', 'E43', '1013.25*(1-(0.0065*D43)/288.15)^5.255', '6.3-E43-f', ch6);
  num('Klima', 'E43', 948.226, '6.3-E43', ch6, 'Zürich-MeteoSchweiz 556 m', 1e-3);
  num('Klima', 'D43', 556, '6.3-D43', ch6, '海拔 m ü.M.');
  fmt('Klima', 'F44', 'SUM(F4:F43)', '6.3-F44-f', ch6);
  num('Klima', 'F44', 948.226, '6.3-F44', ch6, '选择站气压', 1e-3);
  fmt('Klima', 'H44', 'SUM(H4:H43)', '6.3-H44-f', ch6);
  num('Klima', 'H44', 3440, '6.3-H44', ch6, '选择站 HDD');
  fmt('Klima', 'N1', 'INDEX(B4:B43,Gebäude!D2,0)', '6.2-N1-f', ch6);
  str('Klima', 'N1', 'Zürich-MeteoSchweiz', '6.2-N1', ch6, '选择站名', true);
  num('Gebaeude', 'D2', 40, '6.2-GebD2', ch6, '站序号 40');
  // 6.4 formula 2 hours
  fmt('Klima', 'O5', 'INDEX($S$1:$CT$65,L5,MATCH($O$2,$S$2:$CT$2,0))', '6.4-O5-f', ch6);
  fmt('Klima', 'P6', 'O6+P5', '6.4-P6-f', ch6);
  num('Klima', 'P65', 8760, '6.4-P65', ch6, '年合计');
  num('Klima', 'O65', 0, '6.4-O65', ch6, '+35 °C 区间小时数 0');
  num('Klima', 'O5', 0, '6.4-O5', ch6, '−25 °C 区间小时数 0');
  // 6.5 formula 3 humidity
  fmt('Klima', 'N5', 'INDEX($S$1:$CT$65,L5,MATCH($N$2,$S$2:$CT$2,0))', '6.5-N5-f', ch6);
  fmt('Klima', 'Q5', 'AbsFeuchte(M5,N5,$F$44)', '6.5-Q5-f', ch6);
  num('Klima', 'N20', 0.881667, '6.5-N20', ch6, 'φ(−10)', 1e-4);
  num('Klima', 'Q20', 1.50152, '6.5-Q20', ch6, 'x(−10)', 1e-4);
  num('Klima', 'N50', 0.5925, '6.5-N50', ch6, 'φ(20)');
  num('Klima', 'Q50', 9.21648, '6.5-Q50', ch6, 'x(20)', 1e-3);
  // 6.6 Qhc
  fmt('Qhc', 'G3', 'MATCH(D3,P3:SA3,0)', '6.6-G3-f', ch6);
  num('Qhc', 'G3', 469, '6.6-G3', ch6, '选择站块起始列');
  fmt('Qhc', 'D7', 'INDEX($P$7:$SA$51,$C7,$G$3-1+D$2)', '6.6-D7-f', ch6);
  fmt('Qhc', 'E11', 'INDEX($P$7:$SA$51,$C11,$G$3-1+E$2)', '6.6-E11-f', ch6);
  num('Qhc', 'D11', 43.6565, '6.6-D11', ch6, 'Kühlung Leistung Standard', 1e-3);
  num('Qhc', 'E11', 14.4301, '6.6-E11', ch6, 'Kühlung Energie Standard', 1e-3);
  num('Qhc', 'F11', 19.82335, '6.6-F11', ch6, 'Heizung Leistung Standard', 1e-3);
  str('Qhc', 'D3', 'Zürich-MeteoSchweiz', '6.6-D3', ch6, '', true);
  fmtContains('Qhc', 'P3', '[3]Winter_Auslegung!A5', '6.6-P3-f', ch6, '外部链接 [3]');
  // KZ references
  fmt('KZ', 'G11', 'Qhc_Klimastat!E11', '6.6-KZ-G11-f', ch6);
  fmt('KZ', 'AG11', 'Qhc_Klimastat!D11', '6.6-KZ-AG11-f', ch6);
  fmt('KZ', 'AH11', 'Qhc_Klimastat!F11', '6.6-KZ-AH11-f', ch6);
  num('KZ', 'AG11', 43.6565, '6.6-KZ-AG11', ch6, 1e-3);
  num('KZ', 'G11', 14.4301, '6.6-KZ-G11', ch6, 1e-3);
  num('KZ', 'AH11', 19.82335, '6.6-KZ-AH11', ch6, 1e-3);
  // Berechnung LU consumption
  fmt('BLU', 'N19', 'Klimadaten!F44', '6.7-N19-f', ch6);
}

// ---------- extra cross-boundary checks ----------
{
  // ch1.5 example inputs (chapter claims TemperaturH(12.2406, 8.19…); dump shows AP121=BM121=21.3979, AO121=0)
  num('BLU', 'AP121', 21.3979, 'x1-AP121', 'ch01', '= BM121', 1e-3);
  num('BLU', 'AO121', 0, 'x1-AO121', 'ch01', '温度控分支 X121 = 0');
  check('x1-AN121-inputs', 'ch01', Math.abs((21.3979 - 0 * 2.5016) / (1.006 + 1.86 * 0) - 21.2703) < 0.01, `TemperaturH(AP121=21.3979, AO121=0) = ${((21.3979 - 0 * 2.5016) / (1.006 + 1.86 * 0)).toFixed(4)} °C ≈ AN121 缓存 21.2703 °C（章节示例已按转储修正：焓取室内状态焓 BM121，非 MIL 焓 N121）`);
  // ch1 call-point sweep: AbsFeuchte at both ends of Klimadaten!Q5:Q65
  fmt('Klima', 'Q5', 'AbsFeuchte(M5,N5,$F$44)', 'x1-Q5', 'ch01');
  fmt('Klima', 'Q65', 'AbsFeuchte(M65,N65,$F$44)', 'x1-Q65', 'ch01');
  fmt('BLU', 'AA121', 'IF($E$36=$D$36,MIN(AbsFeuchte(Z121,100%,$N$19),R121),MIN(AbsFeuchte(Z121,100%,$N$19),X121))', 'x1-AA121', 'ch01', '100% 以小数 1 传入');
  fmt('BLU', 'BL121', 'AbsFeuchte(BJ121,BK121,$N$19)', 'x1-BL121', 'ch01');
  // ch2 boundary checks
  num('KZ', 'A51', 12.12, 'x2-A51', 'ch02', 'SIA 代码末行');
  num('KZ', 'AA51', 12.12, 'x2-AA51', 'ch02', '内部代码末行');
  str('Gebaeude', 'L12', 'LA01', 'x2-L12', 'ch02', '通风系统选择');
  num('Gebaeude', 'M8', 3, 'x2-M8', 'ch02', '→ Std!D 列');
  num('Gebaeude', 'V8', 8, 'x2-V8', 'ch02', '→ Std!I 列');
  num('Gebaeude', 'D21', 670, 'x2-D21', 'ch02', 'Parkhaus NGF');
  num('Std', 'E47', 2, 'x2-StdE47', 'ch02', 'Parkhaus 过程新风');
  // ch3: Std O/P/M/N & Kühlraum
  num('Std', 'M10', 0.55, 'x3-M10', 'ch03', 'Spez. Ventilatorleistung');
  str('Std', 'N10', 'einstufig', 'x3-N10', 'ch03', 'Ventilatorregelung Standard');
  num('Std', 'O10', 3900, 'x3-O10', 'ch03', '电基准 Volllaststunden (静态副本)');
  num('Std', 'P10', 4.443214, 'x3-P10', 'ch03', 'Elektrischer Energiebedarf kWh/m²', 1e-4);
  for (const c of ['Q', 'R', 'S', 'T', 'U', 'V']) num('Std', c + '49', 0, 'x3-kuehlraum-' + c, 'ch03', '12.11 Kühlraum 全为 0');
  str('Std', 'B49', 'Kühlraum', 'x3-kuehlraum-B', 'ch03', '', true);
  // ch3: Volll_Lüft derived ratio columns
  fmt('Volll', 'R11', 'F11/D11', 'x3-R11', 'ch03', '2-stufig/1-stufig 比值');
  num('Volll', 'R11', 0.8435897, 'x3-R11-v', 'ch03', 3290/3900, 1e-6);
  fmt('Volll', 'S11', 'J11/D11', 'x3-S11', 'ch03', 'stufenlos/1-stufig 比值');
  num('Volll', 'S11', 0.5538461, 'x3-S11-v', 'ch03', 2160/3900, 1e-6);
  fmt('Volll', 'AJ11', 'IF(AI11="einstufig",$E11,IF(AI11="zweistufig",$I11,$Q11))', 'x3-AJ11', 'ch03', 'C1:2024 块电基准选取');
  // ch3: I6 → Lüftung!J32 wiring & I20
  fmt('BLU', 'I20', 'IF(E52=0,0,(E52*1000)/(3600*(K70/3600)*N23))', 'x3-I20', 'ch03', 'Feuchtelast 使用 K70');
  num('BLU', 'I20', 0, 'x3-I20-v', 'ch03', 'E52=0');
  // ch4: row-168 state chain values
  const r168 = { C168: 10.0367, E168: 0.504877, M168: 10.0367, N168: 47.6506, O168: 47.6506, P168: 0, Q168: 22, R168: 10.0367, S168: 47.6506, T168: 22, U168: 22, V168: 0, W168: 22, X168: 10.0367, Y168: 47.6506, BR168: 24, BS168: 0.504877, BT168: 10.0367, BU168: 24, BW168: 10.0367, L168: 22, Z168: 9, AF168: 9 };
  for (const [a, v] of Object.entries(r168)) {
    num('BLU', a, v, 'x4-' + a, 'ch04', '行 168 状态链', 2e-3);
  }
  fmtContains('BLU', 'T168', 'MIN((L168*($E$35)+BU168*(1-$E$35)))', 'x4-T168-f', 'ch04', 'MIN 单参 no-op');
  fmtContains('BLU', 'BR168', 'IF($DA168<=$B$89,$D$89-($B$89-$DA168)*$J$88', 'x4-BR168-f', 'ch04', '室温曲线插值');
  str('BLU', 'E17', 'IE5 - gefaked', 'x4-E17', 'ch04');
  str('BLU', 'E30', 'ja', 'x4-E30', 'ch04', '旁通存在');
  str('BLU', 'E31', 'ja', 'x4-E31', 'ch04', 'KRG 存在');
  str('BLU', 'S20', 'nein', 'x4-S20', 'ch04', '比较标签');
  str('BLU', 'S21', 'ja', 'x4-S21', 'ch04', '比较标签');
  num('BLU', 'N6', 0, 'x4-N6', 'ch04', '送风设定湿度夏季');
  num('BLU', 'O6', 0, 'x4-O6', 'ch04');
  // ch4 quirks
  fmt('BLU', 'E7', 'IF(OR(E6="",E6=0),C6,E6)', 'x4-E7', 'ch04', 'E18/K70 上游');
  errVal('BLU', 'J11', '#N/A', 'x4-J11', 'ch04', 'SOLL 状态公式 #N/A (4.14-14)');
  errVal('BLU', 'F40', '#N/A', 'x4-F40', 'ch04', 'SOLL 设计温度空 (4.14-14)');
  for (const a of ['K82', 'M82', 'P82', 'R82']) num('BLU', a, 0, 'x4-' + a, 'ch04', 'SOLL 休眠 (4.14-3)');
  num('BLU', 'B189', 0, 'x4-B189', 'ch04', 'SOLL 区间行 0');
  num('BLU', 'F254', 0, 'x4-F254', 'ch04', '能源价格空 → 成本 0 (4.14-7)');
  for (const a of ['CN168', 'CV168']) {
    const f = formulaVal('BLU', a);
    check('x4-' + a, 'ch04', f && /(222|-222)/.test(f), `${a} 图表守卫 (dump: ${f || 'NONE'}) (4.14-6)`);
  }
  const a184 = strVal('BLU', 'A184') || '';
  const d184 = strVal('BLU', 'D184') || '';
  check('x4-A184', 'ch04', a184.includes('LUET') && a184.includes('LUEAB'), `A184 文档行含 LUET/LUEAB (4.14-11)`);
  check('x4-D184', 'ch04', d184.includes('LUET'), `D184 文档行含 LUET (4.14-11)`);
  const bu121 = formulaVal('BLU', 'BU121') || '';
  check('x4-BU121', 'ch04', bu121.includes('#REF!'), `BU121 含 #REF! 死分支 (4.14-13) (dump: ${bu121.slice(0, 60)}…)`);
  for (const a of ['E41', 'E44']) {
    const e = cell('BLU', a);
    check('x4-' + a + '-empty', 'ch04', !e || ((e.f === null || e.f === undefined) && (e.v === null || e.v === undefined) && (e.r === null || e.r === undefined)), `${a} 为空 (4.14-10)`);
  }
  // ch6: station rows & formula-1 generic row
  str('Klima', 'B4', 'Adelboden', 'x6-B4', 'ch06', '首站', true);
  fmt('Klima', 'E4', '1013.25*(1-(0.0065*D4)/288.15)^5.255', 'x6-E4-f', 'ch06');
  num('Klima', 'D4', 1320, 'x6-D4', 'ch06', 'Adelboden 海拔');
  num('Klima', 'E4', 864.428, 'x6-E4', 'ch06', '首站气压', 1e-2);
  str('Klima', 'B16', 'Grand-St-Bernard', 'x6-B16', 'ch06', '', true);
  num('Klima', 'D16', 2472, 'x6-D16', 'ch06', 'Grand-St-Bernard 海拔');
  num('Klima', 'E16', 749.494, 'x6-E16', 'ch06', '≈750 mbar', 1e-2);
  // ch6 headers & boundaries
  fmt('Klima', 'N2', 'N1&N3', 'x6-N2', 'ch06', 'MATCH 键名');
  fmt('Klima', 'O2', 'N1&O3', 'x6-O2', 'ch06');
  str('Klima', 'S4', '[%]', 'x6-S4', 'ch06', '表头单位 [%] 与实际小数不符 (README 0.7-2)');
  num('Klima', 'P5', 0, 'x6-P5', 'ch06', 'P5 = O5+P4 = 0');
  fmt('Qhc', 'D3', 'INDEX(Klimadaten!B4:B43,Gebäude!D2,0)', 'x6-QhcD3', 'ch06');
  num('Qhc', 'D2', 1, 'x6-QhcD2', 'ch06', '块内偏移 1');
  num('Qhc', 'C11', 5, 'x6-QhcC11', 'ch06', '行号列 C7:C51 = 1..45');
}

// ---------- report ----------
let pass = 0, fail = 0, warn = 0;
const fails = [];
const warns = [];
for (const r of results) {
  if (r.ok) pass++;
  else if (r.severity === 'warn') { warn++; warns.push(r); }
  else { fail++; fails.push(r); }
}
console.log(`\n==== ${pass} PASS / ${fail} FAIL / ${warn} WARN ====`);
for (const r of warns) {
  console.log(`WARN [${r.chapter}] ${r.id}: ${r.detail}`);
}
for (const r of fails) {
  console.log(`FAIL [${r.chapter}] ${r.id}: ${r.detail}`);
}
fs.writeFileSync(path.join(__dirname, 'results.json'), JSON.stringify({ pass, fail, warn, fails, warns, results }, null, 2));
console.log('written verify/results.json');
