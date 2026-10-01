#!/usr/bin/env python3
"""P74 check (TD-239, TEST-76): no embedded baseline, and the empty state.

Matt, 2026-10-01: "Please remove imbedded baseline, and include an empty state
screen on the dashboard. The empty state should include a simple example that
highlights the utility and a call to action for Import and Add milestone."

Runs the app with NO fixture: every page this check loads carries the
`sret:no-fixture` marker, so tools/check_map/chrome_fixture.py does not seed
the reference baseline that every other check runs on. Asserts:

  A  source: no client identifier anywhere in the file, one version literal,
     no embedded seed data;
  B  at 390x844 and 1440x900, light and dark: the app opens on the empty
     state (heading, the example board with its four statuses, the edited
     mark, the note and the dependency line, both calls to action), with the
     filter bar, the board, the info bar, the legend and the view toggle
     hidden, no horizontal scroll and no console error;
  C  (1440, light) Import schedule opens the import path, and a real import of
     data/schedules/...DD-2026-08-29.xlsx through it (tools/import_check.py
     build_aoa, the app's own Parse/showMapper/runIngest) takes the empty state
     away and draws 105 rows and 146 milestones; the first import becomes the
     baseline with the view toggle still hidden, a second shows the toggle,
     and removing the only schedule brings the empty state back;
  D  (1440, light) Add milestone opens the dialog; saving takes the empty state
     away with the marker on the board under User-defined; a date beyond the
     window widens it; removing them brings the empty state back;
  E  a published copy of the empty dashboard opens on the empty state.

    python3 tools/p74_check.py [--html FILE] [--screenshots]

--screenshots also writes docs/mockups/P74/empty-state_<w>_<theme>.png.
Exit 1 if any check fails.
"""
import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_check import build_aoa, find_chrome  # noqa: E402

DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
XLSX = ROOT / "data" / "schedules" / "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"
SHOTS = ROOT / "docs" / "mockups" / "P74"
OPT_OUT = "<!-- sret:no-fixture: P74 tests the app as it ships, with no schedule -->"
CLIENT_STRINGS = ["Eskay", "Snip", "SNIP-", "103787", "Matthew", "Garrett", "Ausenco", "Bronson", "SRK"]
VIEWS = [(390, 844, "light"), (390, 844, "dark"), (1440, 900, "light"), (1440, 900, "dark")]

# Ahead of everything, so an exception thrown while the app boots is caught.
EARLY = r"""<script>
window.__errs=[];
window.__step='boot';
window.__roLoops=0;
addEventListener('error',function(e){
  // Chromium reports a ResizeObserver callback that changes layout again as an
  // error EVENT, not an exception and not a console message. The board's
  // sticky-header observers do that whenever the board appears; it is counted
  // (R.info.resizeObserverLoops) rather than failed.
  if(/^ResizeObserver loop/.test(e.message||'')){ window.__roLoops++; return; }
  __errs.push('error: '+e.message+' @'+e.lineno+' during '+window.__step); });
addEventListener('unhandledrejection',function(e){ __errs.push('rejection: '+(e.reason&&e.reason.message||e.reason)); });
(function(){ var o=console.error; console.error=function(){ __errs.push('console.error: '+Array.prototype.join.call(arguments,' ')); return o.apply(console,arguments); }; })();
</script>"""

PROBE = r"""<script>
(function(){
const AOA=__AOA__, FLOWS=__FLOWS__, THEME=__THEME__;
const R={checks:[], info:{}};
function ck(name, ok, detail){ R.checks.push({name:name, ok:!!ok, detail:(detail===undefined?'':String(detail)).slice(0,400)}); }
function $(id){ return document.getElementById(id); }
function shown(el){ if(!el) return false; if(!el.getClientRects().length) return false; const cs=getComputedStyle(el); return cs.visibility!=='hidden'&&cs.display!=='none'; }
function out(){ R.errs=window.__errs.slice(); R.info.resizeObserverLoops=window.__roLoops; const e=document.createElement('pre'); e.id='p74-out'; e.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(e); }
function wait(ms){ return new Promise(function(r){ setTimeout(r,ms); }); }
// Stand in for SheetJS at exactly the boundary the app uses (tools/import_check.py).
// Installed for the import only, so the zero-data sweep exports with the real one.
const REAL_XLSX=window.XLSX;
const STUB_XLSX={ read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
  utils:{ sheet_to_json:function(sheet){ return sheet.__aoa; } } };
// The published file: the Blob the app builds, and the name it would download as.
const cap={};
const OB=window.Blob;
window.Blob=function(parts,opts){ if(opts&&opts.type==='text/html') cap.text=parts.join(''); return new OB(parts,opts); };
window.Blob.prototype=OB.prototype;
const oc=HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click=function(){ if(this.download){ cap.name=this.download; return; } return oc.call(this); };
window.confirm=function(){ return true; };
// A blocking dialog would stall the headless page; recorded instead.
const alerts=[];
window.alert=function(m){ alerts.push(String(m)); };

function emptyStateChecks(tag){
  const es=$('empty-state');
  ck(tag+': the empty state is shown', es&&!es.hidden&&shown(es)&&document.body.classList.contains('is-empty'));
  ck(tag+': its heading is shown', shown($('es-title'))&&/\S/.test($('es-title').textContent), $('es-title')&&$('es-title').textContent);
  ck(tag+': its one line on what the dashboard is for is shown', shown(document.querySelector('.es-lede')));
  ck(tag+': the example board is shown, labelled as an example',
     shown($('es-board'))&&$('es-board').getAttribute('role')==='img'&&/^Example/.test($('es-board').getAttribute('aria-label')||'')&&
     /Example only/.test(document.querySelector('.es-cap').textContent));
  ck(tag+': Import schedule is shown, as the primary action', shown($('es-import'))&&$('es-import').classList.contains('primary')&&
     $('es-import').textContent.trim()==='Import schedule');
  ck(tag+': Add milestone is shown, as the secondary action', shown($('es-add-ms'))&&!$('es-add-ms').classList.contains('primary')&&
     $('es-add-ms').textContent.trim()==='Add milestone');
  ck(tag+': the filter bar is hidden', !shown($('top-filter-bar')));
  ck(tag+': the board is hidden', !shown($('scroll-wrap'))&&!shown($('main-table')));
  ck(tag+': the info bar is hidden', !shown($('info-hdr'))&&!shown($('sib')));
  ck(tag+': the view toggle and the baseline shadow are hidden', !shown($('vt-baseline'))&&!shown($('vt-update'))&&!shown($('bl-shadow-wrap')));
  ck(tag+': the legend is hidden', !shown(document.querySelector('.legend')));
  ck(tag+': the header and the icon bar stay', shown($('icon-bar'))&&shown(document.querySelector('.rpt-hd'))&&shown($('btn-add-ms')));
  ck(tag+': no horizontal page scroll', document.documentElement.scrollWidth<=window.innerWidth+1,
     document.documentElement.scrollWidth+' > '+window.innerWidth);
  const card=document.querySelector('.es-card').getBoundingClientRect();
  ck(tag+': the card sits inside the viewport', card.left>=0&&card.right<=window.innerWidth+0.5, card.left+'..'+card.right);
}
function exampleChecks(tag){
  const b=$('es-board');
  const icons=b.querySelectorAll('svg.ms-icon');
  const cls=Array.prototype.map.call(icons,function(i){ return i.getAttribute('class'); });
  ck(tag+': example: 4 rows with fictional M- IDs', b.querySelectorAll('.es-id').length===4&&
     Array.prototype.every.call(b.querySelectorAll('.es-id'),function(e){ return /^M-\d{4}$/.test(e.textContent); }));
  ck(tag+': example: markers drawn with renderIcon in four statuses (complete, on track, at risk, critical)',
     icons.length===4&&['s-done','s-track','s-risk','s-crit'].every(function(c){ return cls.some(function(x){ return x.indexOf(c)>=0; }); }), cls.join(' | '));
  // The same icon as the board would draw it, measured outside the example.
  const t=document.createElement('div'); t.innerHTML=renderIcon('Diamond','RISK',15);
  const ref=t.firstChild; document.body.appendChild(ref);
  const want=getComputedStyle(ref).color, got=getComputedStyle(b.querySelector('svg.s-risk')).color;
  ref.remove();
  ck(tag+': example: the markers carry the board’s own status colours', want===got&&want!=='', got+' vs '+want);
  ck(tag+': example: a few weeks of timeline', b.querySelectorAll('.es-hd').length===7);
  ck(tag+': example: one edited mark *', b.querySelectorAll('.ms-edited-mark').length===1&&b.querySelector('.ms-edited-mark').textContent==='*');
  ck(tag+': example: one note callout', b.querySelectorAll('.es-note').length===1&&shown(b.querySelector('.es-note')));
  // Measured, not read: the line has to start at the first marker and end at
  // the second at this width, the trap a stale layout falls into.
  const g=$('es-dep-line');
  const pr=g?g.getBoundingClientRect():null;
  const ia=b.querySelector('[data-es-id="M-1020"] .ms-icon').getBoundingClientRect();
  const ib=b.querySelector('[data-es-id="M-1030"] .ms-icon').getBoundingClientRect();
  ck(tag+': example: one dependency line, from one marker to the next', !!g&&g.querySelectorAll('line.es-dep').length===3&&
     g.querySelectorAll('line[marker-end]').length===1&&!!pr&&pr.width>4&&
     Math.abs(pr.left-ia.right)<=4&&Math.abs(pr.right-ib.left)<=6&&
     Math.abs(pr.top-(ia.top+ia.height/2))<=3&&Math.abs(pr.bottom-(ib.top+ib.height/2))<=3,
     'line '+(pr&&[pr.left,pr.right,pr.top,pr.bottom].map(Math.round))+' a '+[ia.right,ia.top].map(Math.round)+' b '+[ib.left,ib.top].map(Math.round));
  const nt=b.querySelector('.es-note');
  ck(tag+': example: the note reads, its text not cut away', !!nt&&nt.scrollWidth<=nt.clientWidth+1&&
     getComputedStyle(nt).color!==getComputedStyle(nt).backgroundColor, nt&&(nt.scrollWidth+' > '+nt.clientWidth));
  ck(tag+': example: static, nothing in it can be focused or clicked', b.querySelectorAll('[tabindex],button,a,input,[onclick]').length===0);
}

setTimeout(async function(){
 try{
  if(THEME==='dark'){ document.documentElement.setAttribute('data-theme','dark'); }
  R.info.version=APP_VERSION; R.info.width=window.innerWidth;
  ck('boot: no dataset was seeded (the pre-boot hook is unset)', typeof window.__SRET_FIXTURE__==='undefined'&&!document.getElementById('sret-fixture'));
  ck('boot: the board holds nothing', TASKS.length===0&&MILESTONES.length===0&&!hasBaseline()&&PRIMARY_SOURCES.length===0&&USER_MILESTONES.length===0,
     TASKS.length+'/'+MILESTONES.length);
  ck('boot: no seed data, no schedule dependencies', SEED_TASKS.length===0&&SEED_MILESTONES.length===0&&Object.keys(DEP_DATA_SCHEDULE).length===0);
  ck('boot: the heading and the tab title are neutral', $('rpt-title-text').textContent.trim()==='Milestone Dashboard'&&
     document.title==='Milestone Dashboard v'+APP_VERSION, document.title);
  ck('boot: the empty board still has weeks, around today', WE_LABELS.length>=20&&dateToCol(new Date())>=0, WE_LABELS.length);
  const txt=document.body.innerText;
  ck('boot: no client identifier on the page', !/Eskay|Snip|SNIP-|103787|Matthew|Garrett|Ausenco|Bronson|SRK/.test(txt));
  emptyStateChecks('empty');
  exampleChecks('empty');
  ck('empty: the Sources tab says what will become the baseline', /No baseline yet/.test($('mount-body').textContent)&&
     /first schedule you import becomes the baseline/.test($('mount-body').textContent));

  // ---- every path with zero data: no exception, and still the empty state ----
  window.__step='sweep';
  const thrown=[];
  const tryIt=async function(name,fn){ try{ await fn(); }catch(e){ thrown.push(name+': '+(e&&e.message||e)); } };
  for(const t of SETTINGS_TABS){ await tryIt('Data & view tab '+t,function(){ setSettingsTab(t); toggleSettingsDrawer(true); }); }
  await tryIt('close Data & view',function(){ toggleSettingsDrawer(false); });
  await tryIt('View controls',function(){ toggleFilterBar(true); toggleFilterBar(false); });
  await tryIt('Workspace rail',function(){ setRailState('rail'); });
  for(const sec of WS_SECTIONS){ await tryIt('Workspace '+sec,function(){ setWorkspaceSection(sec,true); }); }
  await tryIt('Notes tabs',function(){ setNotesTab('coll'); setNotesTab('list'); renderNotes(); });
  await tryIt('Workspace collapse',function(){ setRailState('collapsed'); });
  await tryIt('histogram',function(){ setHistMeasure('tasks'); setHistPos('top'); setHistMeasure('hours'); setHistPos('bottom'); });
  await tryIt('filters',function(){ applyFilter(); setFloatPreset('0d'); clearCriticalFilters(); clearFilter(); });
  await tryIt('dependency lines',function(){ setAllDep('pred',true); setAllDep('succ',true); setAllDep('pred',false); setAllDep('succ',false); });
  await tryIt('info bar',function(){ renderInfoBar(); });
  await tryIt('print preview',function(){ togglePrintMode(true); togglePrintMode(false); });
  await tryIt('grid view',function(){ openUserMsGrid(); closeGridView(); });
  await tryIt('model export',function(){ exportModel(); window.__modelName=cap.name; });
  await tryIt('status CSV',function(){ exportCSV(); });
  await tryIt('remarks workbook',function(){ exportComments(); });
  await tryIt('diagnostics export',function(){ exportDiagnostics(); });
  await tryIt('rebuild',function(){ rerender(true); });
  await wait(300);
  ck('sweep: every path runs with zero data, without an exception', thrown.length===0, thrown.join(' | '));
  ck('sweep: the only notice is that there are no diagnostics to export', alerts.length===1&&/No diagnostics/.test(alerts[0]), alerts.join(' | '));
  ck('sweep: the model export names a neutral file', /^milestone-dashboard_model_/.test(window.__modelName||''), window.__modelName);
  ck('sweep: still the empty state afterwards', document.body.classList.contains('is-empty')&&!$('empty-state').hidden&&shown($('es-import')));
  cap.name=null; cap.text=null;

  if(FLOWS){
   // ---- E (part 1): publish the empty dashboard -------------------------
   window.__step='publish';
   publishDashboard();
   ck('publish: an empty dashboard publishes', !!cap.text&&cap.text.indexOf('window.__PUBLISHED_STATE__=')>0, cap.name);
   ck('publish: named as an empty dashboard', cap.name==='Milestone_Dashboard_empty.html', cap.name);
   const pm=/window\.__PUBLISHED_STATE__=(\{.*?\});<\/script>/.exec(cap.text||'');
   let ps=null; try{ ps=JSON.parse(pm[1]); }catch(e){}
   ck('publish: the state block carries no schedule and no baseline', !!ps&&ps.tasks.length===0&&ps.milestones.length===0&&ps.baseline===null&&
      ps.sources.length===0, ps&&JSON.stringify({t:ps.tasks.length,b:ps.baseline}));
   R.published=cap.text||'';
   R.publishedName=cap.name||'';

   // ---- D: Add milestone --------------------------------------------------
   window.__step='add';
   $('es-add-ms').click();
   ck('add: the Add milestone call to action opens the dialog', !$('add-ms-dialog').hidden&&shown($('add-ms-dialog')));
   $('add-ms-name').value='Kick-off meeting';
   const today=isoToday();
   $('add-ms-date').value=today;
   saveAddMilestone();
   await wait(200);
   ck('add: saving takes the empty state away', !document.body.classList.contains('is-empty')&&$('empty-state').hidden);
   const mk=document.querySelectorAll('#tbody .m-wrap');
   const row=document.querySelector('#tbody tr[data-type="row"]');
   ck('add: the marker is on the board', mk.length===1&&shown(mk[0])&&!!row&&/USR-001/.test(row.getAttribute('data-ids')||''),
      mk.length+' '+(row&&row.getAttribute('data-ids')));
   ck('add: under User-defined', !!row&&row.getAttribute('data-source')===USER_BAND_SOURCE&&
      document.body.innerText.indexOf(USER_BAND)>=0, row&&row.getAttribute('data-source'));
   ck('add: the board and filter bar are back', shown($('scroll-wrap'))&&shown($('top-filter-bar')));
   ck('add: still nothing to compare, so the view toggle stays hidden', !shown($('vt-baseline')));
   // A date past the window around today widens the weeks rather than being refused.
   window.__step='add-far';
   const far=new Date(); far.setDate(far.getDate()+7*60);
   const weeksBefore=WE_LABELS.length;
   openAddMilestone(null,null);
   $('add-ms-name').value='Handover';
   $('add-ms-date').value=isoDay(far);
   saveAddMilestone();
   await wait(200);
   ck('add: a date beyond the window widens the timeline to take it', USER_MILESTONES.length===2&&WE_LABELS.length>weeksBefore&&dateToCol(far)>=0&&
      document.querySelectorAll('#tbody .m-wrap').length===2, weeksBefore+' -> '+WE_LABELS.length);
   // Sources > User-defined > Remove, the action that deletes them all.
   window.__step='remove-user';
   askRemoveUserDefined();
   removeAllUserDefined();
   await wait(200);
   ck('add: removing them brings the empty state back', USER_MILESTONES.length===0&&document.body.classList.contains('is-empty')&&!$('empty-state').hidden&&
      shown($('es-import')));

   // ---- C: Import schedule ---------------------------------------------------
   window.__step='import-cta';
   $('es-import').click();
   ck('import: the Import schedule call to action opens Data & view at Import', $('settings-drawer').classList.contains('open')&&
      SETTINGS_TAB==='import'&&!$('import-sect').hidden&&shown($('sched-file')));
   function importOnce(){
     window.XLSX=STUB_XLSX;
     PENDING_IMPORT_FILE='103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx';
     const parsed=Parse.workbook(new Uint8Array([0]));
     showMapper(parsed);
     $('cfg-datadate').value='2026-08-29';
     runIngest();
     window.XLSX=REAL_XLSX;
   }
   window.__step='import-1';
   importOnce();
   await wait(300);
   ck('import: the empty state is gone', !document.body.classList.contains('is-empty')&&$('empty-state').hidden);
   const rows=document.querySelectorAll('#tbody tr[data-type="row"]').length;
   const markers=document.querySelectorAll('#tbody .m-wrap').length;
   ck('import: the board draws 105 rows and 146 milestones', rows===105&&markers===146&&TASKS.length===105&&MILESTONES.length===146,
      rows+' rows, '+markers+' markers, '+TASKS.length+'/'+MILESTONES.length);
   ck('import: the board, filter bar and info bar are shown', shown($('scroll-wrap'))&&shown($('top-filter-bar'))&&shown($('sib')));
   ck('import: the first schedule became the baseline', hasBaseline()&&BASELINE_ORIGIN==='import'&&BASELINE_TASKS.length===105&&
      BASELINE_MILESTONES.length===146&&BASELINE_FROM_SOURCE===PRIMARY_SOURCES[0].id, BASELINE_ORIGIN);
   ck('import: the baseline is a copy, not the same records', BASELINE_MILESTONES[0]!==UPDATE_MILESTONES[0]);
   ck('import: the baseline is labelled with its data date', BASELINE_LABEL_TEXT==='Baseline DD 29-Aug-26'&&
      ($('meta-baseline')||{}).textContent==='Baseline DD 29-Aug-26', BASELINE_LABEL_TEXT);
   ck('import: one schedule is nothing to compare, so the view toggle stays hidden', !canCompareBaseline()&&!shown($('vt-baseline'))&&!shown($('bl-shadow-wrap')));
   ck('import: the project number fills from the file name', REPORT_META.projectNo==='103787-13');
   ck('import: the Sources tab names the baseline and where it came from', !!$('src-baseline-row')&&
      /Copied from the first schedule imported/.test($('src-baseline-row').textContent), $('src-baseline-row')&&$('src-baseline-row').textContent);
   window.__step='import-2';
   // A second import (replace) is the update: now there are two to compare.
   importOnce();
   await wait(300);
   ck('import: a second schedule is the update, and the view toggle appears', canCompareBaseline()&&shown($('vt-baseline'))&&shown($('vt-update'))&&
      shown($('bl-shadow-wrap'))&&VIEW_MODE==='update'&&BASELINE_MILESTONES.length===146);
   window.__step='view';
   setViewMode('baseline');
   await wait(100);
   ck('import: the Baseline view shows the first schedule', VIEW_MODE==='baseline'&&document.querySelectorAll('#tbody tr[data-type="row"]').length===105);
   setViewMode('update');
   window.__step='discard';
   discardUpdate(true);
   await wait(200);
   ck('import: discarding the update falls back to the baseline, not to empty', hasBaseline()&&!document.body.classList.contains('is-empty')&&
      TASKS.length===105&&VIEW_MODE==='baseline');
   // Start again from one import, then remove it: it was the baseline too.
   window.__step='restart';
   clearBaseline(); PRIMARY_SOURCES=[]; rebuildPrimaryDatasets(); scheduleRerender(true);
   await wait(200);
   importOnce();
   await wait(300);
   const only=PRIMARY_SOURCES[0];
   window.__step='remove';
   askRemoveSource(only.id);
   ck('import: removing the only schedule warns that the board will be empty', /board will be empty/.test($('mount-body').textContent));
   removeSource(only.id);
   await wait(300);
   ck('import: removing the only schedule brings the empty state back', !hasBaseline()&&PRIMARY_SOURCES.length===0&&
      document.body.classList.contains('is-empty')&&!$('empty-state').hidden&&TASKS.length===0);
  }
  ck('no console errors', window.__errs.length===0, window.__errs.join(' | '));
 }catch(e){ ck('probe ran to the end', false, String(e&&e.stack||e)); }
 out();
},2500);
})();
</script>"""

REOPEN = r"""<script>
(function(){
const R={checks:[]};
function ck(name, ok, detail){ R.checks.push({name:name, ok:!!ok, detail:(detail===undefined?'':String(detail)).slice(0,400)}); }
function shown(el){ if(!el) return false; if(!el.getClientRects().length) return false; const cs=getComputedStyle(el); return cs.visibility!=='hidden'&&cs.display!=='none'; }
setTimeout(function(){
 try{
  const $=function(id){ return document.getElementById(id); };
  ck('reopen: the copy is a published file', !!window.__PUBLISHED_STATE__&&!!PUBLISHED_META);
  ck('reopen: it opens on the empty state', document.body.classList.contains('is-empty')&&!$('empty-state').hidden&&shown($('es-title'))&&
     shown($('es-import'))&&shown($('es-add-ms'))&&shown($('es-board')));
  ck('reopen: the board, filter bar, info bar and view toggle are hidden', !shown($('scroll-wrap'))&&!shown($('top-filter-bar'))&&
     !shown($('sib'))&&!shown($('vt-baseline')));
  ck('reopen: nothing on the board', TASKS.length===0&&MILESTONES.length===0&&!hasBaseline());
  ck('reopen: no console errors', window.__errs.length===0, window.__errs.join(' | '));
 }catch(e){ ck('reopen probe ran to the end', false, String(e&&e.stack||e)); }
 const e=document.createElement('pre'); e.id='p74-out'; e.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(e);
},2500);
})();
</script>"""


def page_with(html, probe):
    page = html.replace("<head>", "<head>" + EARLY, 1)
    i = page.rindex("</body>")
    return page[:i] + OPT_OUT + "\n" + probe + "\n" + page[i:]


def launch(page, w, h, extra=None, td=None):
    with tempfile.TemporaryDirectory() as tdir:
        f = pathlib.Path(tdir) / "p74.html"
        f.write_text(page, encoding="utf-8")
        args = [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tdir}/prof",
                f"--window-size={w},{h}", "--virtual-time-budget=30000"] + (extra or ["--dump-dom"]) + [f.as_uri()]
        p = subprocess.run(args, capture_output=True, text=True, timeout=300)
    return p


def run_probe(page, w, h):
    p = launch(page, w, h)
    m = re.search(r'<pre id="p74-out">(.*?)</pre>', p.stdout, re.S)
    if not m:
        sys.exit("Probe output not found. The page threw before the probe finished.\n" + p.stderr[-2000:])
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def source_checks(html):
    out = []
    for s in CLIENT_STRINGS:
        n = html.count(s)
        out.append({"name": f"source: no '{s}' anywhere in the file", "ok": n == 0, "detail": f"{n} found"})
    n = len(re.findall(r"eskay", html, re.I))
    out.append({"name": "source: no 'eskay' in any case", "ok": n == 0, "detail": f"{n} found"})
    n = len(re.findall(r"3\.[0-9]*\.[0-9]*-P", html))
    out.append({"name": "source: APP_VERSION is the only version literal", "ok": n == 1, "detail": f"{n} found"})
    out.append({"name": "source: the seeds are empty unless the pre-boot hook supplies them",
                "ok": bool(re.search(r"const SEED_TASKS=\(PREBOOT&&Array\.isArray\(PREBOOT\.tasks\)\)", html)) and
                "const SEED_TASKS=[" not in html and "const SEED_MILESTONES=[" not in html, "detail": ""})
    out.append({"name": "source: no dependency literal", "ok": not re.search(r"const DEP_DATA=\{\"", html), "detail": ""})
    out.append({"name": "source: the hook is read once, from window.__SRET_FIXTURE__",
                "ok": html.count("window.__SRET_FIXTURE__:null") == 1, "detail": ""})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    ap.add_argument("--screenshots", action="store_true")
    a = ap.parse_args()
    html = pathlib.Path(a.html).read_text(encoding="utf-8")
    aoa = build_aoa(XLSX)
    checks = source_checks(html)
    published = None
    for w, h, theme in VIEWS:
        flows = (w == 1440 and theme == "light")
        probe = (PROBE.replace("__AOA__", json.dumps(aoa)).replace("__FLOWS__", "true" if flows else "false")
                 .replace("__THEME__", json.dumps(theme)))
        R = run_probe(page_with(html, probe), w, h)
        for c in R["checks"]:
            c["name"] = f"{w}x{h} {theme}: {c['name']}"
            checks.append(c)
        if flows:
            published = R.get("published") or ""
    if published:
        R = run_probe(page_with(published, REOPEN), 1440, 900)
        checks.extend(R["checks"])
    else:
        checks.append({"name": "reopen: a published copy was captured", "ok": False, "detail": ""})
    if a.screenshots:
        SHOTS.mkdir(parents=True, exist_ok=True)
        for w, h, theme in VIEWS:
            shot = SHOTS / f"empty-state_{w}_{theme}.png"
            theme_js = ("<script>document.documentElement.setAttribute('data-theme','dark');</script>"
                        if theme == "dark" else "")
            launch(page_with(html, theme_js), w, h, [f"--screenshot={shot}"])
            print(f"wrote {shot.relative_to(ROOT)}")
    failed = [c for c in checks if not c["ok"]]
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + ("" if c["ok"] or not c["detail"] else "  [" + c["detail"] + "]"))
    print(f"{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
