// Run: node tools/notes_export_test.mjs   (exits 1 on any failure)
process.env.TZ = 'UTC';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const require = createRequire(import.meta.url);
const NE = require(path.join(root, 'src/modules/notes-export/notes-export.js'));

// Vendored SheetJS via vm (it declares `var XLSX` at top level)
const ctx = { console, Buffer, TextEncoder, TextDecoder, Uint8Array, ArrayBuffer, Date, Math };
ctx.self = ctx; ctx.window = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root, 'vendor/sheetjs/xlsx.mini.min.js'), 'utf8'), ctx);
const XLSX = ctx.XLSX;

let fails = 0, n = 0;
function t(name, cond, extra) {
  n++;
  if (cond) console.log('PASS ' + name);
  else { fails++; console.log('FAIL ' + name + (extra !== undefined ? '  -> ' + JSON.stringify(extra) : '')); }
}
const eq = (name, a, b) => t(name, JSON.stringify(a) === JSON.stringify(b), { got: a, want: b });

// Stub rollup: latest-wins per field, over the entries given, for one key and period
function rollup(entries, key, { period } = {}) {
  const es = entries.filter(e => e.target.kind === 'general' || String(e.target.key) === String(key))
    .filter(e => !period || e.period === period).sort((a, b) => a.at < b.at ? -1 : 1);
  const values = {}, byField = {}; let lastText = '', openCount = 0;
  for (const e of es) {
    if (e.text) lastText = e.text;
    if (e.status === 'open') openCount++;
    for (const [f, c] of Object.entries(e.changes || {})) { values[f] = c.to; byField[f] = { eid: e.eid, from: c.from, to: c.to, at: e.at }; }
  }
  return { values, byField, lastText, count: es.length, openCount };
}
const MS = { M1: { id: 'A1000', name: 'Mill start' }, M2: { id: 'A2000', name: 'Tailings dam' }, M3: { id: 'A3000', name: 'Camp complete' } };
const SRC = { M1: { start: '2026-09-01', date: '2026-10-29', health: 1, progress: 40 },
              M2: { start: '2026-08-01', date: '2026-11-30', health: 3, progress: 10 },
              M3: { start: '2026-07-01', date: '2026-09-30', health: 1, progress: 90 } };
const msLookup = k => MS[k] || null;
const sourceOf = (k, f) => (SRC[k] || {})[f] ?? null;
const P1 = '2026-09-25', P2 = '2026-10-02';
const E = (eid, target, period, at, o = {}) => Object.assign({ eid, target, links: [], period, at, updatedAt: at, by: null,
  status: 'note', text: '', changes: {}, origin: 'manual', followsUp: null }, o);
const entries = [
  E('E-0001', { kind: 'ms', key: 'M1' }, P1, '2026-09-26T09:05:00Z', { text: 'Remark only', status: 'open' }),
  E('E-0002', { kind: 'ms', key: 'M2' }, P1, '2026-09-26T10:00:00Z', { changes: { date: { from: '2026-11-30', to: '2026-12-14' } } }),
  E('E-0003', { kind: 'ms', key: 'M1' }, P1, '2026-09-27T14:30:00Z', { text: 'Slipping', status: 'sent',
    changes: { date: { from: '2026-10-29', to: '2026-11-12' }, health: { from: 1, to: 3 } } }),
  E('E-0004', { kind: 'ms', key: 'M3' }, P1, '2026-09-27T15:00:00Z', { changes: { progress: { from: 90, to: 95 } } }),
  E('E-0005', { kind: 'ms', key: 'M3' }, P1, '2026-09-28T08:00:00Z', { changes: { progress: { from: 95, to: 100 } }, text: 'Complete' }),
  E('E-0006', { kind: 'ms', key: 'M1' }, P2, '2026-10-03T07:00:00Z', { changes: { date: { from: '2026-11-12', to: null } }, text: 'Back on plan' }),
  E('E-0007', { kind: 'general', key: null }, P2, '2026-10-03T08:00:00Z', { text: 'General note — site wide', links: ['A1000', 'A2000'], status: 'open' }),
  E('E-0008', { kind: 'dep', key: 'A1000>A2000' }, P2, '2026-10-03T09:00:00Z', { text: 'Dep concern', status: 'open' }),
  E('E-0009', { kind: 'row', key: 'ROW-7' }, P2, '2026-10-03T10:00:00Z', { changes: { rowHealth: { from: 1, to: 4 }, rowRemark: { from: null, to: 'Late' } } }),
];
const args = extra => Object.assign({ rollup, msLookup, sourceOf }, extra);
const H = { id: 0, ms: 1, rep: 2, open: 3, rem: 4, ss: 5, sn: 6, fs: 7, fn: 8, hs: 9, hn: 10, ps: 11, pn: 12, last: 13 };
const row = (aoa, id, rep) => aoa.slice(1).find(r => r[0] === id && r[2] === rep);

const { summary, log } = NE.buildNotesWorkbookAoA(entries, args());
const pairs = new Set(entries.map(e => (e.target.kind === 'general' ? 'g' : e.target.kind + e.target.key) + '|' + e.period));
t('summary row count = distinct (key, period)', summary.length - 1 === pairs.size, [summary.length - 1, pairs.size]);
t('log row count = entry count', log.length - 1 === entries.length);
eq('summary header', summary[0], ['ID','Milestone','Report','Open items','Remarks','Start (schedule)','Start (new)','Finish (schedule)','Finish (new)','Status/Health (schedule)','Status/Health (new)','Progress (schedule)','Progress (new)','Last saved']);
eq('log header', log[0], ['Entry','ID','Milestone','Report','Status','Remark','Changes','Linked IDs','Saved','Origin']);

const m1p1 = row(summary, 'A1000', 'W/E 25-Sep-26');
t('M1 P1 row exists', !!m1p1);
eq('M1 P1 milestone', m1p1[H.ms], 'Mill start');
eq('M1 P1 remarks newest first with time', m1p1[H.rem], '27-Sep 14:30 Slipping\n26-Sep 09:05 Remark only');
eq('M1 P1 open items', m1p1[H.open], 1);
eq('M1 P1 finish schedule / new', [m1p1[H.fs], m1p1[H.fn]], ['29-Oct-26', '12-Nov-26']);
eq('M1 P1 health schedule / new', [m1p1[H.hs], m1p1[H.hn]], ['On track', 'At risk']);
eq('M1 P1 start schedule / new blank', [m1p1[H.ss], m1p1[H.sn]], ['01-Sep-26', '']);
eq('M1 P1 progress schedule / new blank', [m1p1[H.ps], m1p1[H.pn]], ['40%', '']);
eq('M1 P1 last saved', m1p1[H.last], '27-Sep-26 14:30');

const m2p1 = row(summary, 'A2000', 'W/E 25-Sep-26');
eq('M2 changes-only: remarks blank', m2p1[H.rem], '');
eq('M2 changes-only: finish new', m2p1[H.fn], '14-Dec-26');
eq('M2 changes-only: health new blank', m2p1[H.hn], '');
eq('M2 health schedule At risk', m2p1[H.hs], 'At risk');

const m3p1 = row(summary, 'A3000', 'W/E 25-Sep-26');
eq('two entries same field: later wins in Summary', m3p1[H.pn], '100%');
eq('M3 remark from second entry only', m3p1[H.rem], '28-Sep 08:00 Complete');
t('both same-field entries appear in Log', log.some(r => r[0] === 'E-0004' && r[6] === 'Progress 90% → 95%') && log.some(r => r[0] === 'E-0005' && r[6] === 'Progress 95% → 100%'));

const m1p2 = row(summary, 'A1000', 'W/E 02-Oct-26');
eq('to:null revert in Summary', m1p2[H.fn], 'schedule value');
t('to:null revert in Log', log.some(r => r[0] === 'E-0006' && r[6] === 'Finish 12-Nov-26 → schedule value'));
const l3 = log.find(r => r[0] === 'E-0003');
eq('log changes string', l3[6], 'Finish 29-Oct-26 → 12-Nov-26; Health On track → At risk');
eq('log row E-0003', [l3[1], l3[2], l3[3], l3[4], l3[5], l3[8], l3[9]], ['A1000', 'Mill start', 'W/E 25-Sep-26', 'sent', 'Slipping', '27-Sep-26 14:30', 'manual']);

const gen = row(summary, 'General', 'W/E 02-Oct-26');
t('general row exists', !!gen);
eq('general remark has no em dash', gen[H.rem], '03-Oct 08:00 General note - site wide');
eq('general schedule columns blank', [gen[H.ss], gen[H.fs], gen[H.hs], gen[H.ps]], ['', '', '', '']);
eq('general linked IDs in log', log.find(r => r[0] === 'E-0007')[7], 'A1000, A2000');
const dep = summary.find(r => r[1] === 'Dependency');
eq('dependency ID', dep && dep[0], 'A1000 → A2000');
eq('dependency log ID', log.find(r => r[0] === 'E-0008')[1], 'A1000 → A2000');
const rw = summary.find(r => String(r[0]).startsWith('Row: '));
eq('row ID', rw && rw[0], 'Row: ROW-7');
eq('row log changes', log.find(r => r[0] === 'E-0009')[6], 'Row health On track → Critical; Row remark schedule value → Late');

t('blank cells for unchanged fields (M1 P2 start/health/progress new)', [m1p2[H.sn], m1p2[H.hn], m1p2[H.pn]].every(v => v === ''));
t('no em/en dashes in any output', !/[—–]/.test(JSON.stringify([summary, log])));

// periodFilter
const f1 = NE.buildNotesWorkbookAoA(entries, args({ periodFilter: P1 }));
t('periodFilter limits summary', f1.summary.slice(1).every(r => r[2] === 'W/E 25-Sep-26') && f1.summary.length - 1 === 3, f1.summary.length);
t('periodFilter limits log', f1.log.length - 1 === 5 && f1.log.slice(1).every(r => r[3] === 'W/E 25-Sep-26'));
const f2 = NE.buildNotesWorkbookAoA(entries, args({ periodFilter: P2 }));
t('periodFilter P2 counts', f2.summary.length - 1 === 4 && f2.log.length - 1 === 4, [f2.summary.length, f2.log.length]);
const f0 = NE.buildNotesWorkbookAoA([], args());
t('empty entries -> headers only', f0.summary.length === 1 && f0.log.length === 1);

const cf = NE.buildNotesWorkbookAoA(entries, args({ fmtDate: v => 'D(' + v + ')' }));
t('custom fmtDate used', row(cf.summary, 'A1000', 'W/E D(2026-09-25)') !== undefined);

const before = JSON.stringify(entries);
NE.buildNotesWorkbookAoA(entries, args());
t('inputs not mutated', JSON.stringify(entries) === before);

// Round trip through SheetJS
const wb = NE.buildNotesBook(XLSX, { summary, log });
const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
const back = XLSX.read(buf, { type: 'buffer' });
eq('sheet names survive', back.SheetNames, ['Summary', 'Log']);
const bs = XLSX.utils.sheet_to_json(back.Sheets.Summary, { header: 1, blankrows: true });
const bl = XLSX.utils.sheet_to_json(back.Sheets.Log, { header: 1, blankrows: true });
t('summary count survives', bs.length === summary.length, [bs.length, summary.length]);
t('log count survives', bl.length === log.length, [bl.length, log.length]);
t('multi-line remark survives', bs.find(r => r[0] === 'A1000' && r[2] === 'W/E 25-Sep-26')[4] === m1p1[H.rem]);
t('change text survives', bl.find(r => r[0] === 'E-0003')[6] === l3[6]);

console.log(`\n${n - fails}/${n} passed`);
process.exit(fails ? 1 : 0);
