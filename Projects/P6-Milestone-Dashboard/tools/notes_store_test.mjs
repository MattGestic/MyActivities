// P65 notes store tests (src/modules/notes-store/notes-store.js).
// Run: node tools/notes_store_test.mjs
// Prints PASS/FAIL per check and exits 1 on any failure. No network, no deps.
// Fixtures in tools/fixtures/p65/ are real app output, made by
// tools/p65_fixtures.py driving the app headless.
import { createRequire } from 'module';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const S = require(join(here, '..', 'src', 'modules', 'notes-store', 'notes-store.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('PASS ' + name); }
  else { fail++; console.log('FAIL ' + name + (detail !== undefined ? '  :: ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : '')); }
}
function canon(v) {
  if (v === undefined) return 'null';
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(canon).join(',') + ']';
  return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canon(v[k])).join(',') + '}';
}
const eq = (a, b) => canon(a) === canon(b);

const T0 = Date.parse('2026-09-30T09:00:00Z');
const MIN = 60 * 1000;
const P = '2026-10-04', P_OLD = '2026-09-27';
const W = S.DEFAULT_WINDOW_MS;
const ms = (key, changes, text) => ({ target: { kind: 'ms', key }, changes: changes || {}, text: text || '' });

// ---------- latest-wins over N=3, then removal falls back ----------
{
  const E = [];
  const a = S.append(E, Object.assign(ms('SNIP-1', { date: { from: '2026-08-01', to: '2026-08-08' } }), { origin: 'grid' }), { now: T0, period: P });
  const b = S.append(E, Object.assign(ms('SNIP-1', { date: { from: '2026-08-08', to: '2026-08-15' } }), { origin: 'grid' }), { now: T0 + MIN, period: P });
  const c = S.append(E, Object.assign(ms('SNIP-1', { date: { from: '2026-08-15', to: '2026-08-22' } }), { origin: 'grid' }), { now: T0 + 2 * MIN, period: P });
  check('latest-wins: three entries appended, eids E-0001..E-0003', E.length === 3 && a.eid === 'E-0001' && c.eid === 'E-0003', E.map(e => e.eid));
  check('latest-wins: 3rd entry wins', S.rollup(E, 'SNIP-1').values.date === '2026-08-22');
  check('latest-wins: projection carries 3rd', S.projectEntries(E).fields['SNIP-1'].date === '2026-08-22');
  S.remove(E, c.eid);
  check('latest-wins: delete 3rd falls back to 2nd', S.rollup(E, 'SNIP-1').values.date === '2026-08-15');
  S.remove(E, b.eid);
  check('latest-wins: delete 2nd falls back to 1st', S.rollup(E, 'SNIP-1').values.date === '2026-08-08');
  S.remove(E, a.eid);
  const r = S.rollup(E, 'SNIP-1');
  check('latest-wins: delete 1st leaves nothing', !('date' in r.values) && r.count === 0 && !('SNIP-1' in S.projectEntries(E).fields));
  // Same-at tie breaks on eid
  const F = [];
  S.append(F, Object.assign(ms('K', { progress: { from: null, to: 10 } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(F, Object.assign(ms('K', { progress: { from: 10, to: 20 } }), { origin: 'grid' }), { now: T0, period: P });
  check('latest-wins: identical at, higher eid wins', S.rollup(F, 'K').values.progress === 20);
  // Order is by at, not array position
  const G = [];
  const late = S.append(G, Object.assign(ms('K', { weight: { from: null, to: 5 } }), { origin: 'grid' }), { now: T0 + 5 * MIN, period: P });
  const early = S.append(G, Object.assign(ms('K', { weight: { from: null, to: 9 } }), { origin: 'grid' }), { now: T0, period: P });
  check('latest-wins: ordered by at, not by array position', S.rollup(G, 'K').values.weight === 5 && S.rollup(G, 'K').byField.weight.eid === late.eid && early.eid === 'E-0002');
}

// ---------- to:null clears ----------
{
  const E = [];
  S.append(E, Object.assign(ms('SNIP-2', { date: { from: null, to: '2026-09-01' }, health: { from: null, to: 3 } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('SNIP-2', { date: { from: '2026-09-01', to: null }, health: { from: 3, to: null } }), { origin: 'grid' }), { now: T0 + MIN, period: P });
  const r = S.rollup(E, 'SNIP-2'), pr = S.projectEntries(E);
  check('to:null clears the field in rollup values', !('date' in r.values) && !('health' in r.values));
  check('to:null is still the latest in byField', r.byField.date.to === null && r.byField.date.eid === 'E-0002');
  check('to:null clears field override and health override in projection', !('SNIP-2' in pr.fields) && !('SNIP-2' in pr.health));
}

// ---------- progress vs source ----------
{
  const E = [];
  S.append(E, Object.assign(ms('A', { progress: { from: 40, to: 40 } }), { origin: 'grid' }), { now: T0, period: P });
  check('progress: a no-op change (from === to) is not recorded', E.length === 0);
  S.append(E, Object.assign(ms('A', { progress: { from: null, to: 40 } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('B', { progress: { from: null, to: 41 } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('C', { progress: { from: null, to: 0 } }), { origin: 'grid' }), { now: T0, period: P });
  const src = { A: 40, B: 40, C: null };
  const pr = S.projectEntries(E, (k, f) => f === 'progress' ? src[k] : undefined);
  check('progress: equal to source (40 vs 40) is not projected', !('A' in pr.progress));
  check('progress: different from source (41 vs 40) is projected', pr.progress.B === 41);
  check('progress: source null, 0 is projected', pr.progress.C === 0);
  check('progress: rollup still reports the entry value equal to source', S.rollup(E, 'A').values.progress === 40);
}

// ---------- health 0 IS projected ----------
{
  const E = [];
  S.append(E, Object.assign(ms('H0', { health: { from: null, to: 0 } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('H2', { health: { from: null, to: 2 } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('H4', { health: { from: null, to: 4 } }), { origin: 'grid' }), { now: T0, period: P });
  const pr = S.projectEntries(E, () => 0);
  check('health: explicit 0 (N/A) is projected, key present', ('H0' in pr.health) && pr.health.H0 === 0);
  check('health: 2 and 4 projected, no equal-to-source rule', pr.health.H2 === 2 && pr.health.H4 === 4);
}

// ---------- fields vs source; empty object deleted ----------
{
  const E = [];
  S.append(E, Object.assign(ms('F1', { actName: { from: null, to: 'Same name' }, date: { from: null, to: '2026-10-10' } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('F2', { actName: { from: null, to: 'Same name' } }), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('F3', { weight: { from: null, to: 3 } }), { origin: 'grid' }), { now: T0, period: P });
  const own = { F1: { actName: 'Same name', date: '2026-10-03' }, F2: { actName: 'Same name' }, F3: { weight: 2 } };
  const pr = S.projectEntries(E, (k, f) => (own[k] || {})[f]);
  check('fields: a field equal to source is dropped, the differing one kept', eq(pr.fields.F1, { date: '2026-10-10' }), pr.fields.F1);
  check('fields: an object left empty is deleted, not stored as {}', !('F2' in pr.fields));
  check('fields: a differing number is kept', pr.fields.F3 && pr.fields.F3.weight === 3);
}

// ---------- coalescing ----------
{
  const mk = () => [];
  const d1 = ms('C1', { date: { from: '2026-08-01', to: '2026-08-08' } }, 'Moved a week');
  const d2 = ms('C1', { progress: { from: 20, to: 50 } }, 'Moved a week');
  let E = mk();
  const a = S.append(E, d1, { now: T0, period: P });
  const b = S.append(E, d2, { now: T0 + W - 1, period: P });
  check('coalesce: at windowMs - 1 merges into the same entry', E.length === 1 && a === b && eq(Object.keys(a.changes).sort(), ['date', 'progress']));
  check('coalesce: merged entry updatedAt moves, at stays', a.at === new Date(T0).toISOString() && a.updatedAt === new Date(T0 + W - 1).toISOString());
  E = mk(); S.append(E, d1, { now: T0, period: P }); S.append(E, d2, { now: T0 + W, period: P });
  check('coalesce: at exactly windowMs merges (inclusive bound)', E.length === 1);
  E = mk(); S.append(E, d1, { now: T0, period: P }); S.append(E, d2, { now: T0 + W + 1, period: P });
  check('coalesce: at windowMs + 1 appends a new entry', E.length === 2);
  // Window measured from updatedAt, so N=3 saves chain.
  E = mk();
  S.append(E, d1, { now: T0, period: P });
  S.append(E, d2, { now: T0 + W - 1, period: P });
  S.append(E, ms('C1', { weight: { from: 1, to: 2 } }), { now: T0 + 2 * W - 2, period: P });
  check('coalesce: N=3 saves each within the window of the last stay one entry', E.length === 1 && eq(Object.keys(E[0].changes).sort(), ['date', 'progress', 'weight']));
  E = mk(); S.append(E, d1, { now: T0, period: P }); S.append(E, d2, { now: T0 + MIN, period: P_OLD });
  check('coalesce: a different period does not merge', E.length === 2);
  E = mk(); S.append(E, Object.assign({}, d1, { origin: 'grid' }), { now: T0, period: P }); S.append(E, d2, { now: T0 + MIN, period: P });
  check('coalesce: previous entry origin grid does not merge', E.length === 2);
  E = mk(); S.append(E, d1, { now: T0, period: P }); S.append(E, Object.assign({}, d2, { origin: 'grid' }), { now: T0 + MIN, period: P });
  check('coalesce: new draft origin grid does not merge', E.length === 2);
  E = mk(); S.append(E, d1, { now: T0, period: P }); S.append(E, ms('C2', { weight: { from: 1, to: 2 } }), { now: T0 + MIN, period: P });
  check('coalesce: a different target does not merge', E.length === 2);
  // A later entry on the target that is not a card blocks merging into an older card entry.
  E = mk(); S.append(E, d1, { now: T0, period: P });
  S.append(E, Object.assign(ms('C1', { weight: { from: 1, to: 2 } }), { origin: 'grid' }), { now: T0 + MIN, period: P });
  S.append(E, d2, { now: T0 + 2 * MIN, period: P });
  check('coalesce: only the LATEST entry on the target is a merge candidate', E.length === 3);
  // Text-loss guard
  E = mk(); S.append(E, ms('T', {}, 'Delayed by rain'), { now: T0, period: P });
  S.append(E, ms('T', {}, 'Crane down'), { now: T0 + MIN, period: P });
  check('coalesce: text guard, unrelated new text appends a new entry', E.length === 2 && E[0].text === 'Delayed by rain' && E[1].text === 'Crane down');
  E = mk(); S.append(E, ms('T', {}, 'Delayed by rain'), { now: T0, period: P });
  S.append(E, ms('T', {}, 'Delayed by rain, recovering'), { now: T0 + MIN, period: P });
  check('coalesce: text guard, extended text merges', E.length === 1 && E[0].text === 'Delayed by rain, recovering');
  E = mk(); S.append(E, ms('T', {}, 'Delayed by rain'), { now: T0, period: P });
  S.append(E, ms('T', { weight: { from: 1, to: 2 } }, ''), { now: T0 + MIN, period: P });
  check('coalesce: text guard, empty new text merges and keeps old text', E.length === 1 && E[0].text === 'Delayed by rain' && E[0].changes.weight.to === 2);
  E = mk(); S.append(E, ms('T', { weight: { from: 1, to: 2 } }, ''), { now: T0, period: P });
  S.append(E, ms('T', {}, 'Now with a remark'), { now: T0 + MIN, period: P });
  check('coalesce: text guard, empty old text merges and takes new text', E.length === 1 && E[0].text === 'Now with a remark');
  E = mk(); S.append(E, ms('T', {}, 'Delayed by rain'), { now: T0, period: P });
  S.append(E, ms('T', {}, 'Delayed'), { now: T0 + MIN, period: P });
  check('coalesce: text guard, a shortened text is a loss and appends', E.length === 2);
  // Earlier from and later to
  E = mk();
  S.append(E, ms('R', { date: { from: 'A', to: 'B' } }), { now: T0, period: P });
  S.append(E, ms('R', { date: { from: 'B', to: 'C' } }), { now: T0 + MIN, period: P });
  check('coalesce: keeps the earlier from and the later to', E.length === 1 && eq(E[0].changes.date, { from: 'A', to: 'C' }));
  // Revert within window drops out
  E = mk();
  S.append(E, ms('R', { date: { from: 'A', to: 'B' }, weight: { from: 1, to: 2 } }), { now: T0, period: P });
  S.append(E, ms('R', { date: { from: 'B', to: 'A' } }), { now: T0 + MIN, period: P });
  check('coalesce: a change reverted within the window drops out', E.length === 1 && !('date' in E[0].changes) && E[0].changes.weight.to === 2);
  E = mk();
  S.append(E, ms('R', { health: { from: null, to: 3 } }), { now: T0, period: P });
  const last = S.append(E, ms('R', { health: { from: 3, to: null } }), { now: T0 + MIN, period: P });
  check('coalesce: an entry emptied by a revert is removed', E.length === 0 && S.isEmptyEntry(last));
  E = mk();
  S.append(E, ms('R', { health: { from: null, to: 3 } }), { now: T0, period: P });
  S.append(E, ms('R', { health: { from: 3, to: null } }), { now: T0 + W + 1, period: P });
  check('coalesce: the same revert outside the window is kept as its own entry', E.length === 2 && !('R' in S.projectEntries(E).health));
}

// ---------- edit ----------
{
  const E = [];
  const old = S.append(E, ms('E1', {}, 'Last week'), { now: T0, period: P_OLD });
  const cur = S.append(E, ms('E1', {}, 'This week'), { now: T0 + MIN, period: P });
  const r1 = S.edit(E, old.eid, { text: 'Changed' }, { now: T0 + 2 * MIN, period: P });
  check('edit: refused for an entry from an earlier period, returns error', r1.ok === false && r1.error === 'period' && old.text === 'Last week');
  let threw = false; try { S.edit(E, 'E-9999', { text: 'x' }, { period: P }); } catch (e) { threw = true; }
  check('edit: unknown eid returns an error, does not throw', !threw && S.edit(E, 'E-9999', { text: 'x' }, { period: P }).error === 'not-found');
  const r2 = S.edit(E, cur.eid, { text: 'This week, edited', status: 'open' }, { now: T0 + 3 * MIN, period: P });
  check('edit: allowed in the current period and updates updatedAt', r2.ok && cur.text === 'This week, edited' && cur.status === 'open' && cur.updatedAt === new Date(T0 + 3 * MIN).toISOString() && cur.at === new Date(T0 + MIN).toISOString());
  check('edit: an immutable field is refused', S.edit(E, cur.eid, { period: P_OLD }, { period: P }).error === 'immutable');
  check('edit: no ctx.period is refused', S.edit(E, cur.eid, { text: 'x' }, {}).ok === false);
}

// ---------- setStatus, rollup counts and period ----------
{
  const E = [];
  const a = S.append(E, Object.assign(ms('S', { progress: { from: null, to: 10 } }, 'one'), { origin: 'grid', status: 'open' }), { now: T0, period: P_OLD });
  const b = S.append(E, Object.assign(ms('S', { progress: { from: 10, to: 30 } }, 'two'), { origin: 'grid', status: 'sent' }), { now: T0 + MIN, period: P });
  const c = S.append(E, Object.assign(ms('S', {}, 'three'), { origin: 'grid', status: 'note' }), { now: T0 + 2 * MIN, period: P });
  let r = S.rollup(E, 'S');
  check('rollup: count, openCount, lastText, lastAt', r.count === 3 && r.openCount === 2 && r.lastText === 'three' && r.lastAt === c.at);
  r = S.rollup(E, 'S', { period: P_OLD });
  check('rollup: opts.period limits to one report', r.count === 1 && r.values.progress === 10 && r.lastText === 'one');
  const n = S.setStatus(E, [a.eid, b.eid], 'done', { now: T0 + 9 * MIN });
  check('setStatus: sets several, returns count, openCount drops to 0', n === 2 && S.rollup(E, 'S').openCount === 0 && a.updatedAt === new Date(T0 + 9 * MIN).toISOString());
  check('setStatus: unknown status changes nothing', S.setStatus(E, [a.eid], 'bogus') === 0 && a.status === 'done');
  // Kinds are separate: a row ref equal to a milestone key does not mix.
  S.append(E, { target: { kind: 'row', key: 'S' }, changes: { rowRemark: { from: null, to: 'row text' } }, origin: 'grid' }, { now: T0 + 3 * MIN, period: P });
  check('rollup: kind separates a row ref from a milestone key', S.rollup(E, 'S').count === 3 && S.rollup(E, 'S', { kind: 'row' }).values.rowRemark === 'row text');
}

// ---------- general entries, dep, row projection ----------
{
  const E = [];
  const g1 = S.append(E, { target: { kind: 'general' }, text: 'first note #SNIP-1', links: ['SNIP-1'], origin: 'notes' }, { now: T0, period: P });
  const g2 = S.append(E, { target: { kind: 'general' }, text: 'second', origin: 'notes' }, { now: T0 + MIN, period: P });
  check('general: nids assigned N-001, N-002, status defaults open', g1.nid === 'N-001' && g2.nid === 'N-002' && g1.status === 'open' && g1.target.key === null);
  S.append(E, { target: { kind: 'general' }, text: 'third', origin: 'card' }, { now: T0 + 2 * MIN, period: P });
  check('general: never coalesce, even from a card', S.projectEntries(E).notes.length === 3);
  S.append(E, { target: { kind: 'dep', key: 'pred:A->B' }, text: 'old dep', origin: 'grid' }, { now: T0, period: P });
  S.append(E, { target: { kind: 'dep', key: 'pred:A->B' }, text: 'new dep', origin: 'grid' }, { now: T0 + MIN, period: P });
  S.append(E, { target: { kind: 'row', key: 'R1' }, changes: { rowHealth: { from: null, to: '3' } }, origin: 'grid' }, { now: T0, period: P });
  S.append(E, { target: { kind: 'row', key: 'R2' }, changes: { rowRemark: { from: null, to: 'only a remark' } }, origin: 'grid' }, { now: T0, period: P });
  const pr = S.projectEntries(E);
  check('dep: latest wins', pr.depComments['pred:A->B'] === 'new dep');
  check('row: health only projects {health, remarks:""}', eq(pr.rowOverrides.R1, { health: '3', remarks: '' }));
  check('row: remark only projects {health:null, remarks}', eq(pr.rowOverrides.R2, { health: null, remarks: 'only a remark' }));
  check('notes: NOTES shape exactly', eq(Object.keys(pr.notes[0]).sort(), ['at', 'links', 'nid', 'period', 'status', 'text', 'updatedAt']));
}

// ---------- USR keys ----------
{
  const E = [];
  S.append(E, Object.assign(ms('USR-001', { health: { from: null, to: 3 }, progress: { from: null, to: 50 }, date: { from: null, to: '2026-10-01' } }, 'user ms remark'), { origin: 'grid' }), { now: T0, period: P });
  S.append(E, Object.assign(ms('SNIP-9', { health: { from: null, to: 3 } }), { origin: 'grid' }), { now: T0, period: P });
  const pr = S.projectEntries(E);
  check('USR: no health, progress or field override projected', !('USR-001' in pr.health) && !('USR-001' in pr.progress) && !('USR-001' in pr.fields));
  check('USR: text still projects to comments', pr.comments['USR-001'] === 'user ms remark');
  check('USR: a schedule key beside it still projects', pr.health['SNIP-9'] === 3);
}

// ---------- round trip on REAL fixtures ----------
const fx = {
  model: JSON.parse(readFileSync(join(here, 'fixtures', 'p65', 'model_p64.json'), 'utf8')),
  published: JSON.parse(readFileSync(join(here, 'fixtures', 'p65', 'published_p64.json'), 'utf8')),
};
function nonEmpty(o) { const r = {}; Object.keys(o || {}).forEach(k => { if (String(o[k] == null ? '' : o[k]).length) r[k] = o[k]; }); return r; }
function noUsr(o) { const r = {}; Object.keys(o || {}).forEach(k => { if (!/^USR-/.test(k)) r[k] = o[k]; }); return r; }
for (const name of ['model', 'published']) {
  const p = fx[name];
  // The fixture must actually exercise every kind, or the round trip proves nothing.
  const h = p.milestoneHealthOverrides || {};
  const kinds = Object.keys(p.milestoneComments || {}).length >= 3 &&
    Object.values(h).includes(0) && Object.values(h).includes(2) &&
    Object.keys(p.milestoneProgressOverrides || {}).length > 0 &&
    Object.values(p.milestoneFieldOverrides || {}).some(o => 'date' in o) &&
    Object.values(p.milestoneFieldOverrides || {}).some(o => 'actName' in o) &&
    Object.keys(p.dependencyComments || {}).length > 0 &&
    Object.values(p.overrides || {}).some(o => o.remarks && o.health != null) &&
    (p.notes || []).length >= 3 && (p.notes || []).some(n => n.links && n.links.length) &&
    new Set((p.notes || []).map(n => n.status)).size >= 3;
  check(name + ' fixture: carries every annotation kind', kinds);
  const entries = S.migrateLegacy(p, { period: '2000-01-02', now: T0 });
  const pr = S.projectEntries(entries, () => undefined);
  check(name + ' round trip: milestoneComments (empty strings ignored)', eq(pr.comments, nonEmpty(p.milestoneComments)), [pr.comments, p.milestoneComments]);
  check(name + ' round trip: milestoneHealthOverrides', eq(pr.health, noUsr(p.milestoneHealthOverrides)), [pr.health, p.milestoneHealthOverrides]);
  check(name + ' round trip: milestoneProgressOverrides', eq(pr.progress, noUsr(p.milestoneProgressOverrides)), [pr.progress, p.milestoneProgressOverrides]);
  check(name + ' round trip: milestoneFieldOverrides', eq(pr.fields, noUsr(p.milestoneFieldOverrides)), [pr.fields, p.milestoneFieldOverrides]);
  check(name + ' round trip: dependencyComments', eq(pr.depComments, nonEmpty(p.dependencyComments)), [pr.depComments, p.dependencyComments]);
  check(name + ' round trip: overrides (row health and remarks)', eq(pr.rowOverrides, p.overrides), [pr.rowOverrides, p.overrides]);
  check(name + ' round trip: notes reproduced exactly', eq(pr.notes, p.notes), [pr.notes, p.notes]);
  const msE = entries.filter(e => e.target.kind === 'ms');
  check(name + ' migrate: one carried entry per milestone key, status note, from null',
    msE.length === new Set(msE.map(e => e.target.key)).size && msE.every(e => e.origin === 'carried' && e.status === 'note' && Object.values(e.changes).every(c => c.from === null)));
  check(name + ' migrate: period is the reportDate week (' + p.reportDate + ' to 2026-10-04), not opts.period',
    msE.every(e => e.period === '2026-10-04'));
  check(name + ' migrate: short titles are not entries', !entries.some(e => 'shortTitle' in e.changes));
}
{
  // Period falls back to opts.period when reportDate is absent.
  const e = S.migrateLegacy({ milestoneComments: { K: 'x' } }, { period: '2026-10-11' });
  check('migrate: no reportDate falls back to opts.period', e.length === 1 && e[0].period === '2026-10-11');
}

// ---------- idempotency ----------
{
  const E = [];
  const r1 = S.importLegacy(E, fx.model, { now: T0 });
  const n1 = E.length;
  const r2 = S.importLegacy(E, fx.model, { now: T0 + 60 * MIN });
  check('idempotent: first import adds entries', r1.added > 0 && r1.added === n1, r1);
  check('idempotent: second import of the same payload adds 0', r2.added === 0 && E.length === n1 && r2.replaced === 0, r2);
  const r3 = S.importLegacy(E, fx.published, { now: T0 + 120 * MIN });
  check('idempotent: the published payload of the same state adds 0', r3.added === 0 && E.length === n1, r3);
  check('idempotent: short titles and collections passed through untouched', eq(r1.shortTitles, fx.model.milestoneShortTitles) && eq(r1.noteCollections, fx.model.noteCollections));
  // A note with the same nid and a new status replaces in place (applyNotes rule).
  const changed = JSON.parse(JSON.stringify(fx.model));
  changed.notes[0].status = 'closed';
  const r4 = S.importLegacy(E, changed, { now: T0 });
  const n = E.find(e => e.nid === changed.notes[0].nid);
  check('idempotent: note by nid is replaced in place, not duplicated', r4.added === 0 && r4.replaced === 1 && n.status === 'closed' && E.filter(e => e.nid === n.nid).length === 1);
  // Projection after the imports still equals the payload.
  const pr = S.projectEntries(E);
  check('idempotent: projection after three imports still equals the payload', eq(pr.health, fx.model.milestoneHealthOverrides) && eq(pr.fields, fx.model.milestoneFieldOverrides));
  // New eids continue after existing ones.
  const x = S.append(E, ms('NEW', {}, 'after import'), { now: T0, period: P });
  check('eids: an append after import continues the sequence', x.eid === 'E-' + String(n1 + 1).padStart(4, '0'), x.eid);
}

// ---------- pending note becomes review ----------
{
  const e = S.migrateLegacy({ notes: [{ nid: 'N-007', text: 'old pending', status: 'pending', links: [], period: '2026-09-27', at: '2026-09-20T00:00:00.000Z' }] }, { period: P });
  check('migrate: a pending note becomes review', e.length === 1 && e[0].status === 'review' && e[0].nid === 'N-007' && e[0].period === '2026-09-27');
  const u = S.migrateLegacy({ notes: [{ nid: 'N-008', text: 'weird', status: 'whatever' }] }, { period: P });
  check('migrate: an unknown note status becomes open (normNoteStatus)', u[0].status === 'open');
}

// ---------- serialize / deserialize / validatePayload ----------
{
  const E = S.migrateLegacy(fx.model, { now: T0 });
  const back = S.deserialize(S.serialize(E));
  check('serialize/deserialize: round trips', eq(back, E));
  check('deserialize: drops invalid entries, keeps valid', S.deserialize([E[0], { eid: 'bad' }, null]).length === 1);
  check('deserialize: bad JSON gives an empty list', S.deserialize('{nope').length === 0);
  const v1 = S.validatePayload(fx.model), v1b = S.validatePayload(fx.published);
  check('validatePayload: v1 model export accepted', v1.ok && v1.schemaVersion === 1);
  check('validatePayload: published payload (no schemaVersion) accepted as v1', v1b.ok && v1b.schemaVersion === 1);
  const v2 = S.validatePayload({ schemaVersion: 2, entries: E });
  check('validatePayload: v2 with entries accepted', v2.ok && v2.schemaVersion === 2 && !v2.warnings.length);
  check('validatePayload: v2 without entries refused', !S.validatePayload({ schemaVersion: 2 }).ok);
  check('validatePayload: v3 refused', !S.validatePayload({ schemaVersion: 3, entries: [] }).ok);
  check('validatePayload: an unrelated object refused', !S.validatePayload({ foo: 1 }).ok);
  const msgs = [v1, v2, S.validatePayload({ schemaVersion: 3 }), S.validatePayload({ foo: 1 }), S.validatePayload({ schemaVersion: 2, entries: [{}] }),
    S.edit([], 'E-1', {}, { period: P }), S.edit(E, E[0].eid, {}, { period: '1999-01-03' })]
    .flatMap(r => [].concat(r.errors || [], r.warnings || [], r.message || []));
  check('user-facing strings: no em dash', msgs.every(s => s.indexOf('—') < 0), msgs);
}

// ---------- create() convenience ----------
{
  let clock = T0;
  const st = S.create({ now: () => clock, seq: 100 });
  const e1 = st.append(ms('Z', { weight: { from: 1, to: 2 } }), { period: P });
  clock += MIN;
  const e2 = st.append(ms('Z', { weight: { from: 2, to: 3 } }), { period: P });
  check('create: bound clock and seq floor; coalesces via the clock', e1 === e2 && e1.eid === 'E-0101' && st.entries.length === 1 && st.rollup('Z').values.weight === 3);
}

console.log('\n' + pass + ' passed, ' + fail + ' failed, ' + (pass + fail) + ' checks');
process.exit(fail ? 1 : 0);
