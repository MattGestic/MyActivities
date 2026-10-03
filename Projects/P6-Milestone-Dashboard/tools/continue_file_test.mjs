// P79 continue-file tests (src/modules/continue-file/continue-file.js).
// Run: node tools/continue_file_test.mjs
// Prints PASS/FAIL per check and exits 1 on any failure. No network, no deps.
// Real saved files: data/published/Milestone_Dashboard_empty.html (a saved
// empty dashboard) and the app itself (a blank copy, no state block). The
// round trip through a saved dashboard WITH data is tools/p79_continue_check.py.
import { createRequire } from 'module';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const C = require(join(here, '..', 'src', 'modules', 'continue-file', 'continue-file.js'));
const read = f => readFileSync(join(here, '..', f), 'utf8');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('PASS ' + name); }
  else { fail++; console.log('FAIL ' + name + (detail !== undefined ? '  :: ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); }
}

// A minimal whole state, in the shape publishStatePayload() writes.
function state(over) {
  return Object.assign({
    publishedAt: '2026-08-29T06:00:00.000Z', fromVersion: '3.1.0-P78',
    publishChain: [{ at: '2026-08-29T06:00:00.000Z', fromVersion: '3.1.0-P78' }],
    tasks: [{ ref: 'T1' }], milestones: [{ id: 'M1' }, { id: 'M2' }],
    sources: [{ id: 's1', name: 'PFS Weekly', file: 'x.xlsx', dataDate: '2026-08-29' }],
    baseline: { tasks: [], milestones: [] },
    timeline: { labels: ['06-Sep'], dates: ['2026-09-06T00:00:00.000Z'], months: [], nowCol: 0 },
    source: { label: 'PFS', file: 'x.xlsx', dataDate: '2026-08-29' },
    reportTitle: 'Report', projectNo: '000000-0',
    entries: [{ eid: 'E-0001' }], notes: [{ id: 'N-1' }], milestoneComments: { M1: 'c' },
    overrides: {}, userMilestones: [{ id: 'USR-001' }]
  }, over || {});
}
// What publishDashboard() writes: JSON with < > & escaped, then a semicolon.
function savedHtml(p, extra) {
  const json = JSON.stringify(p).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026');
  return '<!doctype html>\n<html><head><script id="published-state">window.__PUBLISHED_STATE__=' + json +
    ';</script>' + (extra || '') + '</head><body><script id="app-script">var x=1;</script></body></html>';
}
const CTX = { appVersion: '3.1.0-P79' };

// ---- happy path ----
let r = C.read(savedHtml(state()), 'Milestone_Dashboard_2026-08-29.html', CTX);
check('saved .html: read ok', r.ok && r.format === 'html', r.errors);
check('saved .html: payload is the state', r.payload && r.payload.milestones.length === 2);
check('summary: counts', r.summary.milestones === 2 && r.summary.tasks === 1 && r.summary.userTasks === 1 &&
  r.summary.entries === 1 && r.summary.notes === 1, r.summary);
check('summary: identity', r.summary.projectNo === '000000-0' && r.summary.dataDate === '2026-08-29' &&
  r.summary.savedAt === '2026-08-29T06:00:00.000Z' && r.summary.savedBy === '3.1.0-P78' && r.summary.hasBaseline &&
  r.summary.sources.join() === 'PFS Weekly' && r.summary.fileName === 'Milestone_Dashboard_2026-08-29.html', r.summary);
check('older version: a warning, not an error', r.ok && r.warnings.some(w => /3\.1\.0-P78.*brought up to 3\.1\.0-P79/.test(w)), r.warnings);

// Text that needed escaping survives the round trip exactly.
const tricky = 'a </script><script>alert(1)</script> & <b>x</b>';
r = C.read(savedHtml(state({ reportTitle: tricky })), 'f.html', CTX);
check('escaped < > & round-trip exactly, including a closing script tag in the data', r.ok && r.payload.reportTitle === tricky, r.payload && r.payload.reportTitle);

// Nothing in the file is executed: a script that would set a global is inert.
globalThis.__pwned = false;
r = C.read(savedHtml(state(), '<script>globalThis.__pwned=true;</script>'), 'f.html', CTX);
check('scripts in the file are never run', r.ok && globalThis.__pwned === false);

// Attribute order and quoting the reader tolerates.
const alt = savedHtml(state()).replace('<script id="published-state">', "<script type='text/javascript' id='published-state'>");
check('state block found with other attributes and single quotes', C.read(alt, 'f.html', CTX).ok);

// ---- full-state JSON ----
r = C.read(JSON.stringify(Object.assign({ kind: 'milestone-dashboard-model', schemaVersion: 1 }, state())), 'backup.json', CTX);
check('backup .json (whole state with a model identity block): read ok', r.ok && r.format === 'json', r.errors);
r = C.read('\uFEFF' + JSON.stringify(state()), 'bom.json', CTX);
check('bare state .json with a BOM: read ok', r.ok, r.errors);

// ---- refusals ----
r = C.read(JSON.stringify({ kind: 'milestone-dashboard-model', schemaVersion: 1, timeline: { labels: ['06-Sep'], nowCol: 0 },
  tasks: [], milestones: [], milestoneComments: { M1: 'c' } }), 'model.json', CTX);
check('annotations-only model export: refused with a pointer to Sources', !r.ok && /annotations export/.test(r.errors[0]) && /Sources/.test(r.errors[0]), r.errors);
r = C.read(read('src/milestone-dashboard.html'), 'milestone-dashboard.html', CTX);
check('the blank app itself: refused, no saved data', !r.ok && /no saved dashboard data/.test(r.errors[0]), r.errors);
r = C.read(read('data/published/Milestone_Dashboard_empty.html'), 'Milestone_Dashboard_empty.html', CTX);
check('a real saved EMPTY dashboard: refused as empty', !r.ok && /empty/.test(r.errors.join(' ')) && r.summary && r.summary.empty, r.errors);
r = C.read('<!doctype html><html><body><h1>Report</h1></body></html>', 'Report.html', CTX);
check('a shared report or other page: refused', !r.ok && r.errors.length === 1, r.errors);
r = C.read('Activity ID,Name\nA1,x', 'sched.csv', CTX);
check('a CSV: refused as not a saved dashboard', !r.ok && /not a saved dashboard/.test(r.errors[0]), r.errors);
r = C.read('{ not json', 'x.json', CTX);
check('broken JSON: refused', !r.ok && /not valid JSON/.test(r.errors[0]));
r = C.read(savedHtml(state()).replace('"milestones":[', '"milestones":[[[['), 'bad.html', CTX);
check('damaged state block: refused', !r.ok && /damaged/.test(r.errors[0]), r.errors);
r = C.read(savedHtml(state({ timeline: { labels: ['a'], dates: [] } })), 'tl.html', CTX);
check('timeline labels and dates disagree: refused', !r.ok, r.errors);
r = C.read('', 'empty.html', CTX);
check('empty file: refused', !r.ok);
r = C.read(null, null, CTX);
check('null input: refused without throwing', !r.ok);

// ---- versions ----
r = C.read(savedHtml(state({ fromVersion: '4.0.0-P1' })), 'f.html', CTX);
check('newer MAJOR version: refused', !r.ok && /newer major/.test(r.errors[0]), r.errors);
r = C.read(savedHtml(state({ fromVersion: '3.1.0-P90' })), 'f.html', CTX);
check('newer partial: loads with a warning', r.ok && r.warnings.some(w => /newer than this copy/.test(w)), r.warnings);
r = C.read(savedHtml(state({ fromVersion: '3.1.0-P79' })), 'f.html', CTX);
check('same version: no version warning', r.ok && !r.warnings.length, r.warnings);
r = C.read(savedHtml(state()), 'f.html');
check('no ctx: loads, no version notes', r.ok && !r.warnings.length);
check('compareVersions', C.compareVersions('3.1.0-P78', '3.1.0-P79') === -1 && C.compareVersions('3.2.0-P1', '3.1.0-P99') === 1 &&
  C.compareVersions('3.1.0', '3.1.0-P0') === 0 && C.compareVersions('junk', '3.1.0-P1') === 0);

// ---- provenance ----
check('chainOf: carries the saved chain', C.chainOf(state()).length === 1 && C.chainOf(state())[0].fromVersion === '3.1.0-P78');
check('chainOf: tolerates a missing or odd chain', C.chainOf({}).length === 0 && C.chainOf({ publishChain: [null, 3, { at: 'x' }] }).length === 1);

// ---- user-facing text ----
const msgs = [];
['', '{', '<html></html>', savedHtml(state({ fromVersion: '4.0.0' })), savedHtml(state({ fromVersion: '3.1.0-P1' }))]
  .forEach(t => { const x = C.read(t, 'f', CTX); msgs.push(...x.errors, ...x.warnings); });
check('no em dash in any message', !msgs.some(m => /\u2014/.test(m)), msgs.filter(m => /\u2014/.test(m)));

console.log(`${pass}/${pass + fail} checks passed`);
process.exit(fail ? 1 : 0);
