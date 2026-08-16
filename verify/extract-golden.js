// Extract inputs + cached results from all verify cases into golden JSON files.
// Usage: node extract-golden.js <verify-cases-dir> <golden-out-dir>
const ExcelJS = require('exceljs');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const casesDir = process.argv[2];
const outDir = process.argv[3];
fs.mkdirSync(outDir, { recursive: true });

const CASE_FILES = [
  'case-01.xlsm', 'case-02.xlsm', 'case-03.xlsm', 'case-04.xlsm', 'case-05.xlsm', 'case-06.xlsm',
];

function cellVal(cell) {
  if (!cell) return null;
  const v = cell.value;
  if (v === null || v === undefined) return null;
  if (typeof v === 'object') {
    if (v.formula) {
      if (v.result !== undefined && v.result !== null) return { formula: v.formula, value: v.result };
      return { formula: v.formula, error: 'no-cached-value' };
    }
    if (v.error) return { error: v.error };
    if (v.richText) return v.richText.map(t => t.text).join('');
    return JSON.stringify(v);
  }
  return v;
}

function dumpRange(ws, r1, c1, r2, c2, prefix) {
  const out = {};
  for (let r = r1; r <= r2; r++) {
    for (let c = c1; c <= c2; c++) {
      const cell = ws.getCell(r, c);
      const v = cellVal(cell);
      if (v !== null) out[`${prefix}${cell.address}`] = v;
    }
  }
  return out;
}

(async () => {
  const manifest = [];
  for (const f of CASE_FILES) {
    const wb = new ExcelJS.Workbook();
    await wb.xlsx.readFile(path.join(casesDir, f));
    const geb = wb.getWorksheet('Gebäude');
    const luef = wb.getWorksheet('Lüftung');
    const erz = wb.getWorksheet('Erzeugung');
    const res = wb.getWorksheet('Resultate');
    const blu = wb.getWorksheet('Berechnung LU');

    const golden = {
      case: f.replace('.xlsm', ''),
      source: 'Excel workbook recalculated by user in Excel (authoritative reference)',
      inputs: {
        Gebaeude: dumpRange(geb, 2, 2, 2, 4, '') // D2..J2 header area
          .concat ? null : dumpRange(geb, 5, 2, 5, 2, ''),
        rooms: dumpRange(geb, 12, 2, 32, 23, ''), // B12:W32 full block
        Lueftung: dumpRange(luef, 7, 2, 22, 26, ''), // B7:Z22
        Erzeugung: dumpRange(erz, 7, 1, 27, 18, ''), // A7:R27
      },
      outputs: {
        Gebaeude_totals: dumpRange(geb, 33, 5, 36, 23, ''), // E33:W36
        Resultate: dumpRange(res, 6, 1, 21, 21, ''), // A6:U21
        Lueftung_results: dumpRange(luef, 23, 1, 32, 26, ''), // A23:Z32 (incl. Totals)
        Erzeugung_totals: dumpRange(erz, 10, 1, 27, 18, ''), // A10:R27
        BerechnungLU: dumpRange(blu, 251, 1, 263, 22, ''), // A251:V263 (result block)
      },
    };
    // fix inputs.Gebaeude merge
    golden.inputs.Gebaeude = {
      ...dumpRange(geb, 2, 2, 2, 4, ''),
      ...dumpRange(geb, 5, 2, 5, 2, ''),
      ...dumpRange(geb, 8, 5, 9, 23, ''),
    };

    const json = JSON.stringify(golden, null, 1);
    const outFile = path.join(outDir, `${golden.case}.json`);
    fs.writeFileSync(outFile, json, 'utf8');
    const hash = crypto.createHash('sha256').update(json).digest('hex').slice(0, 12);
    const nInputs = Object.keys(golden.inputs.rooms).length + Object.keys(golden.inputs.Lueftung).length;
    const nOutputs = Object.keys(golden.outputs.Resultate).length + Object.keys(golden.outputs.Lueftung_results).length + Object.keys(golden.outputs.BerechnungLU).length + Object.keys(golden.outputs.Gebaeude_totals).length;
    manifest.push({ case: golden.case, file: outFile, sha256_12: hash, input_cells: nInputs, output_cells: nOutputs });
    console.log(`${golden.case}: inputs=${nInputs} outputs=${nOutputs} sha=${hash}`);
  }
  fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
  console.log('manifest written');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
