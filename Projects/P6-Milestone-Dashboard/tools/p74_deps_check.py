#!/usr/bin/env python3
"""P74 follow-up check (TD-240, TEST-76): an imported schedule brings its own links.

Matt, 2026-10-01: "the predecessors and successors component isn't showing".
With no embedded baseline, the dependency layer has to come from the imported
file's own Predecessor Details / Successor Details columns.

Runs the app as it ships, with NO fixture (`sret:no-fixture`), at 1440x900,
imports data/schedules/...DD-2026-08-29.xlsx through the app's own import path
(tools/import_check.py build_aoa, Parse.workbook, showMapper, runIngest), and
asserts:
  - SNIP-155's card lists predecessors SNIP-147, SNIP-133 and successors
    SNIP-255, SNIP-161, exactly as the export's columns give them, with the
    relationship text (type and lag) kept;
  - lines are drawn in the SVG for a milestone whose links are on the board;
  - the counts beside the marker match the export for N=3 milestones;
  - turning the source off takes its links away, and on brings them back;
  - a user link layers on top without touching the schedule's own set;
  - publish, then reopen: the same links, chips and lines;
  - the first import is the baseline, so the Baseline view shows the same links.

    python3 tools/p74_deps_check.py [--html FILE]
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

XLSX = ROOT / "data" / "schedules" / "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"
OPT_OUT = "<!-- sret:no-fixture: P74 tests the app as it ships, with no schedule -->"
EARLY = r"""<script>
window.__errs=[];
addEventListener('error',function(e){ if(/^ResizeObserver loop/.test(e.message||'')) return; __errs.push('error: '+e.message+' @'+e.lineno); });
(function(){ var o=console.error; console.error=function(){ __errs.push('console.error: '+Array.prototype.join.call(arguments,' ')); return o.apply(console,arguments); }; })();
</script>"""

COMMON = r"""
const R={checks:[],notes:{}};
function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d).slice(0,400)}); }
function emit(){ R.errs=window.__errs.slice(); const o=document.createElement('pre'); o.id='p74d-out';
  o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
const settle=()=>new Promise(r=>setTimeout(r,300));
const $=id=>document.getElementById(id);
const lst=v=>String(v||'').split(',').map(s=>s.trim()).filter(Boolean);
const same=(a,b)=>a.length===b.length&&a.every((x,i)=>x===b[i]);
const chips=k=>Array.from($('ms-dep-'+k+'-chips').querySelectorAll('.ms-dep-chip')).map(b=>b.getAttribute('data-id'));
async function openCard(id){
  if(!$('ms-dialog').hidden){ discardMsDialog(); await settle(); }
  const w=document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  if(!w) throw new Error('no marker for '+id);
  w.click(); await settle();
  const f=$('ms-dep-lists'); if(f&&!f.open){ f.querySelector('summary').click(); await settle(); }
}
async function closeCard(){ if(!$('ms-dialog').hidden){ discardMsDialog(); await settle(); } }
const lines=()=>Array.from(document.querySelectorAll('#dep-lines-g path.dep-line')).map(function(p){
  const n=(p.getAttribute('d').match(/-?\d+(\.\d+)?/g)||[]).map(Number);
  return {a:{x:n[0],y:n[1]},b:{x:n[n.length-2],y:n[n.length-1]}}; });
const near=(p,q)=>p&&q&&Math.hypot(p.x-q.x,p.y-q.y)<=40;
const hasLine=(from,to)=>{ const f=markerCenter(from), t=markerCenter(to);
  return !!f&&!!t&&lines().some(l=>near(l.a,f)&&near(l.b,t)); };
const onBoard=id=>!!document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
async function cardChecks(tag){
  await openCard('SNIP-155');
  ck(tag+': SNIP-155 card lists predecessors SNIP-147 and SNIP-133', same(chips('pred'),['SNIP-147','SNIP-133']), chips('pred'));
  ck(tag+': SNIP-155 card lists successors SNIP-255 and SNIP-161', same(chips('succ'),['SNIP-255','SNIP-161']), chips('succ'));
  await closeCard();
}
async function lineChecks(tag){
  // A milestone with links whose other ends are on the board.
  const d=DEP_DATA['SNIP-155'];
  const on=lst(d&&d.pred).filter(onBoard).concat(lst(d&&d.succ).filter(onBoard));
  setAllDep('pred',true); setAllDep('succ',true); await settle();
  const drawn=document.querySelectorAll('#dep-lines-g path.dep-line').length;
  const p=lst(d.pred).filter(onBoard), s=lst(d.succ).filter(onBoard);
  ck(tag+': dependency lines are drawn in the SVG', drawn>0, drawn);
  ck(tag+': SNIP-155 has a line from each on-board predecessor and to each on-board successor',
     on.length>0&&p.every(x=>hasLine(x,'SNIP-155'))&&s.every(x=>hasLine('SNIP-155',x)), JSON.stringify({p:p,s:s}));
  setAllDep('pred',false); setAllDep('succ',false); await settle();
  ck(tag+': all off clears them', document.querySelectorAll('#dep-lines-g path.dep-line').length===0);
}
"""

PROBE = r"""<script>
(function(){
const AOA=__AOA__, EXPECT=__EXPECT__;
""" + COMMON + r"""
const OB=window.Blob; let pubText='';
window.Blob=function(parts,opts){ if(opts&&opts.type==='text/html') pubText=parts.join(''); return new OB(parts,opts); };
window.Blob.prototype=OB.prototype;
const oc=HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click=function(){ if(this.download) return; return oc.call(this); };
window.confirm=function(){ return true; }; window.alert=function(){};
setTimeout(async function(){
 try{
  const st=document.createElement('style'); st.textContent='*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
  ck('boot: nothing seeded, no links', typeof window.__SRET_FIXTURE__==='undefined'&&Object.keys(DEP_DATA).length===0);
  const real=window.XLSX;
  window.XLSX={ read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
    utils:{ sheet_to_json:function(sheet){ return sheet.__aoa; } } };
  PENDING_IMPORT_FILE='103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx';
  showMapper(Parse.workbook(new Uint8Array([0])));
  $('cfg-datadate').value='2026-08-29';
  runIngest();
  window.XLSX=real;
  await settle(); await settle();
  ck('import: 105 rows and 146 milestones', TASKS.length===105&&MILESTONES.length===146, TASKS.length+'/'+MILESTONES.length);
  const sch=DEP_DATA_SCHEDULE['SNIP-155']||{};
  ck('import: SNIP-155 takes the export’s own links', sch.pred==='SNIP-147,SNIP-133'&&sch.succ==='SNIP-255,SNIP-161', JSON.stringify(sch));
  ck('import: the relationship type and lag are kept beside the IDs', sch.predRel==='SNIP-147: SS 5, SNIP-133: SS 5'&&sch.succRel==='SNIP-255: FF, SNIP-161: SS 2', JSON.stringify(sch));
  ck('import: the source holds them, and so does the baseline copied from it', !!PRIMARY_SOURCES[0].deps&&!!PRIMARY_SOURCES[0].deps['SNIP-155']&&
     !!BASELINE_DEPS['SNIP-155']&&BASELINE_DEPS!==PRIMARY_SOURCES[0].deps);
  await cardChecks('import');
  await lineChecks('import');
  // Counts beside the marker, N=3, against the export's own columns.
  if(!SHOW_COUNTS){ $('toggle-counts').click(); await settle(); }
  const got={};
  Object.keys(EXPECT).forEach(function(id){
    const w=document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
    const p=w&&w.querySelector('.ms-count.pred'), s=w&&w.querySelector('.ms-count.succ');
    got[id]={pred:p?+p.textContent:0, succ:s?+s.textContent:0};
    ck('counts: '+id+' shows '+EXPECT[id].pred+' predecessors and '+EXPECT[id].succ+' successors, as the export',
       got[id].pred===EXPECT[id].pred&&got[id].succ===EXPECT[id].succ, JSON.stringify(got[id]));
  });
  ck('counts: three milestones compared', Object.keys(EXPECT).length===3);
  // A source turned off takes its links with it.
  toggleSourceEnabled(PRIMARY_SOURCES[0].id); await settle(); await settle();
  ck('source off: its links leave the board', Object.keys(DEP_DATA_SCHEDULE).length===0&&!DEP_DATA['SNIP-155'], Object.keys(DEP_DATA_SCHEDULE).length);
  toggleSourceEnabled(PRIMARY_SOURCES[0].id); await settle(); await settle();
  ck('source on: they come back', (DEP_DATA_SCHEDULE['SNIP-155']||{}).succ==='SNIP-255,SNIP-161');
  // The Baseline view (the first import) shows the baseline's links.
  ck('baseline: the first import is the baseline', hasBaseline()&&BASELINE_ORIGIN==='import');
  // A user link layers on top; the schedule's own set is untouched.
  const r=addUserMilestone({name:'Vendor review',date:isoDay(WE_DATES[NOW_COL]),type:'MS',state:'FUTURE'});
  r.record.pred='SNIP-155';
  scheduleRerender(true); await settle(); await settle();
  ck('user link: shown on SNIP-155 as a successor', lst(DEP_DATA['SNIP-155'].succ).indexOf(r.id)>=0, DEP_DATA['SNIP-155'].succ);
  ck('user link: the schedule’s own set is not written', DEP_DATA_SCHEDULE['SNIP-155'].succ==='SNIP-255,SNIP-161'&&
     JSON.stringify(PRIMARY_SOURCES[0].deps).indexOf('USR-')<0&&JSON.stringify(BASELINE_DEPS).indexOf('USR-')<0);
  removeUserMilestones([r.id]); scheduleRerender(true); await settle(); await settle();
  // Model export carries them.
  let model=null;
  const ob=window.Blob; window.Blob=function(parts,opts){ if(opts&&opts.type==='application/json') model=parts.join(''); return new ob(parts,opts); };
  window.Blob.prototype=ob.prototype;
  exportModel(); window.Blob=ob;
  let mp=null; try{ mp=JSON.parse(model); }catch(e){}
  ck('model export: the source carries its links, and the board’s set travels too', !!mp&&mp.sources[0].deps&&mp.sources[0].deps['SNIP-155']&&
     mp.scheduleDependencies&&mp.scheduleDependencies['SNIP-155']&&mp.scheduleDependencies['SNIP-155'].pred==='SNIP-147,SNIP-133');
  publishDashboard();
  ck('publish: the state block carries the links', /"scheduleDependencies":\{[^]*"SNIP-155":\{"pred":"SNIP-147,SNIP-133"/.test(pubText));
  R.published=pubText;
  ck('no console errors', window.__errs.length===0, window.__errs.join(' | '));
 }catch(e){ ck('probe ran to the end', false, String(e&&e.stack||e)); }
 emit();
},2500);
})();
</script>"""

REOPEN = r"""<script>
(function(){
""" + COMMON + r"""
setTimeout(async function(){
 try{
  const st=document.createElement('style'); st.textContent='*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
  ck('reopen: a published file with the imported board', !!window.__PUBLISHED_STATE__&&TASKS.length===105&&MILESTONES.length===146);
  ck('reopen: SNIP-155 keeps its links', (DEP_DATA_SCHEDULE['SNIP-155']||{}).pred==='SNIP-147,SNIP-133'&&
     (DEP_DATA_SCHEDULE['SNIP-155']||{}).succ==='SNIP-255,SNIP-161', JSON.stringify(DEP_DATA_SCHEDULE['SNIP-155']));
  ck('reopen: the source and the baseline keep theirs', !!(PRIMARY_SOURCES[0].deps||{})['SNIP-155']&&!!BASELINE_DEPS['SNIP-155']);
  await cardChecks('reopen');
  await lineChecks('reopen');
  setViewMode('baseline'); await settle(); await settle();
  ck('reopen: the Baseline view shows the baseline’s links', VIEW_MODE==='baseline'&&(DEP_DATA_SCHEDULE['SNIP-155']||{}).succ==='SNIP-255,SNIP-161');
  ck('reopen: no console errors', window.__errs.length===0, window.__errs.join(' | '));
 }catch(e){ ck('reopen probe ran to the end', false, String(e&&e.stack||e)); }
 emit();
},2500);
})();
</script>"""


def page_with(html, probe):
    page = html.replace("<head>", "<head>" + EARLY, 1)
    i = page.rindex("</body>")
    return page[:i] + OPT_OUT + "\n" + probe + "\n" + page[i:]


def run(page):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p74d.html"
        f.write_text(page, encoding="utf-8")
        p = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                            f"--user-data-dir={td}/prof", "--window-size=1440,900",
                            "--virtual-time-budget=60000", "--dump-dom", f.as_uri()],
                           capture_output=True, text=True, timeout=300)
    m = re.search(r'<pre id="p74d-out">(.*?)</pre>', p.stdout, re.S)
    if not m:
        sys.exit("Probe output not found.\n" + p.stderr[-2000:])
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def expected(aoa):
    """{id: {pred, succ}} from the export's own columns, for SNIP-155 and the
    next two activities that have both."""
    hdr = [str(h).strip().lower() for h in aoa[0]]
    ci = hdr.index("activity id")
    pi = hdr.index("predecessor details")
    si = hdr.index("successor details")
    n = lambda v: len([t for t in str(v or "").split(",") if t.strip()])
    out = {}
    rows = {str(r[ci]).strip(): r for r in aoa[1:] if len(r) > si}
    out["SNIP-155"] = {"pred": n(rows["SNIP-155"][pi]), "succ": n(rows["SNIP-155"][si])}
    for k, r in rows.items():
        if len(out) == 3:
            break
        if k != "SNIP-155" and re.match(r"^[A-Z]+-\d+$", k) and n(r[pi]) and n(r[si]):
            out[k] = {"pred": n(r[pi]), "succ": n(r[si])}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()
    html = pathlib.Path(a.html).read_text(encoding="utf-8")
    aoa = build_aoa(XLSX)
    exp = expected(aoa)
    R = run(page_with(html, PROBE.replace("__AOA__", json.dumps(aoa)).replace("__EXPECT__", json.dumps(exp))))
    checks = R["checks"]
    if R.get("published"):
        checks += run(page_with(R["published"], REOPEN))["checks"]
    else:
        checks.append({"name": "publish: a copy was captured", "pass": False, "detail": ""})
    fails = 0
    for c in checks:
        fails += not c["pass"]
        print(("PASS " if c["pass"] else "FAIL ") + c["name"] + ("" if c["pass"] or not c["detail"] else "  [" + c["detail"] + "]"))
    print(f"{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
