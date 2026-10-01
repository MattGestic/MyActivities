#!/usr/bin/env node
/*
Scale benchmark for the P6 Milestone Dashboard (D-26 baseline, TEST-59).

Asks one question: how long does the real app take to import, rebuild, filter
and draw dependency lines as the schedule grows, and where does the time go?

Why synthetic data: the schedules this was first measured on are client data
and never enter the repo. The generator below produces a schedule with the same
shape as a P6 XER run through tools/xer_to_aoa.py (indented Activity ID for WBS
depth, Duration, Start, Finish, Predecessor/Successor Details, Total Float), so
the run is reproducible from the repo alone. Its numbers are appended to
docs/perf/Scale_Measurement_Log.md; they are not expected to match the client
runs exactly, only to scale the same way.

Why the TSV path: it drives the real import (file input, column mapper,
runIngest()) without SheetJS, so the run is offline and has no CDN dependency.

Why Node rather than Python: the other tools shell out to Chromium, but this one
needs Chrome DevTools Protocol metrics (layout and style-recalc time) and
setInputFiles, which Playwright gives directly.

Usage:
  NODE_PATH=$(npm root -g) node tools/scale_bench.mjs [--html FILE] [--activities 2857,5714] [--cpu 1] [--json OUT] [--fixture FILE | --no-fixture]
*/
import { createRequire } from 'module';
import fs from 'fs';
import os from 'os';
import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => (v.startsWith('--') ? a.concat([[v.slice(2), all[i + 1]]]) : a), []));
const here = path.dirname(new URL(import.meta.url).pathname);
const HTML = path.resolve(args.html || path.join(here, '..', 'src', 'milestone-dashboard.html'));
const SIZES = (args.activities || '2857,5714').split(',').map(Number);
const CPU = Number(args.cpu || 1);
const NO_FIXTURE = process.argv.includes('--no-fixture');
const FIXTURE = NO_FIXTURE ? null
  : fs.readFileSync(args.fixture || path.join(here, 'fixtures', 'baseline', 'eskay-p73.json'), 'utf8');

// ---- Synthetic schedule, deterministic ------------------------------------
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
function iso(d) { return d.toISOString().slice(0, 10); }
function generate(n, seed = 7) {
  const r = rng(seed), rows = [['Activity ID', 'Activity Name', 'Duration', 'Start', 'Finish', 'Predecessor Details', 'Successor Details', 'Total Float']];
  const t0 = Date.UTC(2026, 0, 5), spanDays = 7 * 200;            // about 200 week columns, as measured on the client schedule
  const acts = []; let a = 0, g = 0;
  // WBS: 5 levels, headings interleaved with activities in depth-first order
  (function wbs(depth) {
    const kids = depth < 4 ? 2 + Math.floor(r() * 3) : 0;
    const leafActs = depth >= 2 ? 1 + Math.floor(r() * 5) : 0;
    for (let i = 0; i < leafActs && a < n; i++) {
      const id = 'SYN-' + String(1000 + a++), dur = r() < 0.15 ? 0 : 1 + Math.floor(r() * 30);
      const start = t0 + Math.floor(r() * (spanDays - 40)) * 864e5;
      acts.push({ id, depth, name: 'Synthetic activity ' + a, dur, start, finish: start + dur * 864e5, tf: Math.round((r() * 60 - 5) * 10) / 10 });
    }
    for (let k = 0; k < kids && a < n; k++) { acts.push({ heading: 'Synthetic WBS ' + (g++), depth }); wbs(depth + 1); }
  })(0);
  while (a < n) { const start = t0 + Math.floor(r() * spanDays) * 864e5; acts.push({ id: 'SYN-' + String(1000 + a++), depth: 2, name: 'Synthetic activity ' + a, dur: 5, start, finish: start + 5 * 864e5, tf: 10 }); }
  // Logic: about 2.5 links per activity, always to a later activity so there is no cycle
  const leaves = acts.filter(x => x.id), pred = {}, succ = {}, types = ['FS', 'FS', 'FS', 'SS', 'FF'];
  leaves.forEach((x, i) => { const k = Math.floor(r() * 4); for (let j = 0; j < k; j++) { const t = leaves[Math.min(leaves.length - 1, i + 1 + Math.floor(r() * 40))]; if (t === x) continue; const ty = types[Math.floor(r() * types.length)], lag = r() < 0.2 ? ' ' + Math.floor(r() * 10) : ''; (succ[x.id] ||= []).push(t.id + ': ' + ty + lag); (pred[t.id] ||= []).push(x.id + ': ' + ty + lag); } });
  for (const x of acts) {
    const pad = '  '.repeat(x.depth + 1);
    rows.push(x.heading ? [pad + x.heading, '', '', '', '', '', '', ''] : [pad + x.id, x.name, x.dur, iso(new Date(x.start)), iso(new Date(x.finish)), (pred[x.id] || []).join(', '), (succ[x.id] || []).join(', '), x.tf]);
  }
  return { tsv: rows.map(r => r.join('\t')).join('\n'), rows: rows.length - 1, activities: leaves.length, links: Object.values(succ).reduce((s, v) => s + v.length, 0) };
}

// ---- Measurement -------------------------------------------------------------
const settle = async p => { let n = -1; for (let i = 0; i < 400; i++) { await p.waitForTimeout(150); const m = await p.evaluate(() => window.__rt.length); if (m === n) break; n = m; } await p.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))); };
const timed = async (p, fn) => { await p.evaluate(() => window.__rt = []); const t = Date.now(); await p.evaluate(fn); await settle(p); return Date.now() - t; };

const out = [];
const browser = await chromium.launch({ args: ['--enable-precise-memory-info'] });
for (const n of SIZES) {
  const gen = generate(n), f = path.join(os.tmpdir(), `scale_bench_${n}.tsv`);
  fs.writeFileSync(f, gen.tsv);
  const ctx = await browser.newContext({ offline: true, viewport: { width: 1600, height: 900 } });
  const p = await ctx.newPage(), cdp = await ctx.newCDPSession(p), errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await cdp.send('Performance.enable');
  if (CPU > 1) await cdp.send('Emulation.setCPUThrottlingRate', { rate: CPU });
  // P74 (TD-239): the app ships with no schedule. The benchmark was measured
  // with the reference baseline behind the import (the import is the update),
  // so it seeds that baseline before boot, through the app's own pre-boot
  // hook, the way tools/check_map/chrome_fixture.py does for every Python
  // check. --no-fixture measures the empty app instead (the import is then
  // the first schedule and also becomes the baseline).
  if (FIXTURE) await p.addInitScript({ content: 'window.__SRET_FIXTURE__=' + FIXTURE + ';' });
  await p.goto('file://' + HTML); await p.waitForTimeout(1500);
  // Time every rerender() including the forced layout that follows it
  await p.evaluate(() => { window.__rt = []; const o = window.rerender; window.rerender = function () { const t = performance.now(); const r = o.apply(this, arguments); document.body.offsetHeight; window.__rt.push(performance.now() - t); return r; }; });
  await p.setInputFiles('#sched-file', f);
  await p.waitForFunction(() => typeof LAST_PARSE !== 'undefined' && LAST_PARSE, { timeout: 300000 });
  const metric = async k => (await cdp.send('Performance.getMetrics')).metrics.find(x => x.name === k).value;
  const L0 = await metric('LayoutDuration'), S0 = await metric('RecalcStyleDuration');
  const importMs = await timed(p, () => runIngest());
  const layoutS = +((await metric('LayoutDuration')) - L0).toFixed(2), styleS = +((await metric('RecalcStyleDuration')) - S0).toFixed(2);
  const board = await p.evaluate(() => ({ dom: document.getElementsByTagName('*').length, td: document.querySelectorAll('#main-table td').length, rows: document.querySelectorAll('#main-table tbody tr').length, markers: document.querySelectorAll('#main-table .m-wrap').length, heapMB: Math.round(performance.memory.usedJSHeapSize / 1048576) }));
  const rebuildMs = []; for (let i = 0; i < 3; i++) rebuildMs.push(await p.evaluate(() => { const t = performance.now(); rerender(true); document.body.offsetHeight; return Math.round(performance.now() - t); }));
  const filterMs = await timed(p, () => setFloatPreset('0d'));
  await timed(p, () => clearCriticalFilters());
  const depOnMs = await timed(p, () => { setAllDep('pred', true); setAllDep('succ', true); });
  const depPaths = await p.evaluate(() => document.querySelectorAll('path.dep-line').length);
  const rebuildWithDepsMs = await p.evaluate(() => { const t = performance.now(); rerender(true); document.body.offsetHeight; return Math.round(performance.now() - t); });
  await timed(p, () => { setAllDep('pred', false); setAllDep('succ', false); });
  const themeMs = await p.evaluate(() => new Promise(r => { const t = performance.now(); toggleTheme(); document.body.offsetHeight; requestAnimationFrame(() => requestAnimationFrame(() => r(Math.round(performance.now() - t)))); }));
  const rec = { date: new Date().toISOString().slice(0, 10), build: await p.evaluate(() => APP_VERSION), source: 'synthetic', cpu: CPU + 'x', rows: gen.rows, activities: gen.activities, links: gen.links, importMs, rebuildMs, filterMs, depOnMs, depPaths, rebuildWithDepsMs, themeMs, layoutS, styleS, ...board, errors: errs.length };
  console.log(JSON.stringify(rec)); out.push(rec);
  // written per size, so a run stopped part way keeps what it measured
  if (args.json) fs.writeFileSync(args.json, JSON.stringify(out, null, 2));
  await ctx.close(); fs.unlinkSync(f);
}
await browser.close();
