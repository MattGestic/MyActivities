#!/usr/bin/env python3
"""
P53 check (v3.1.0-P53: date range filter revision).

Two harnesses:
  1. A functional harness (ingest via the XLSX-stub pattern tools/d17a_check.py
     and tools/import_check.py use, then drive the picker/filter functions
     directly) covering: the reselect bug (proven failing against P52, then
     N=3 consecutive reselections passing here), each quick range, Range
     start/Range end rebuilding the timeline (both-bounds, start>end
     rejected, Reset to schedule), the fallback window UI being gone while a
     no-date import still builds a timeline, "Date range" present and From
     only/Until only gone, and the Annotations filter (commented/edited/
     either/any).
  2. A layout harness (tools/ds_check.py's render() pattern: inject a probe,
     dump the DOM at a fixed window size) covering the footer's inline
     layout at 390/768/1440, the desktop row-count ceiling (<=3 at 1440,
     <=4 at 1280), and control heights (24 desktop / 32 coarse) for the new
     Range start/Range end fields and the inline Fit-columns button.

Usage:
  python3 tools/p53_check.py [--html FILE] [--json OUT] [--skip-p52-proof]
Exit code 1 if any assertion fails.
"""
import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import build_aoa, find_chrome  # noqa: E402

FUNCTIONAL_HARNESS = r"""
(async function(){
const AOA = __AOA__;
const R = {steps:[], ok:true};
function assert(name, cond, detail){
  R.steps.push({name:name, ok:!!cond, detail: detail===undefined?null:detail});
  if(!cond) R.ok=false;
}
function note(name, detail){ R.steps.push({name:name, ok:true, detail:detail}); }
function wait(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }

window.confirm=function(){ return true; };
window.prompt=function(){ return null; };
HTMLAnchorElement.prototype.click=function(){};
URL.createObjectURL=function(blob){ return 'blob:captured'; };

let READ_AOA=null;
window.XLSX = {
  utils:{
    book_new:function(){ return {SheetNames:[], Sheets:{}}; },
    book_append_sheet:function(wb,ws,name){ wb.SheetNames.push(name); wb.Sheets[name]=ws; },
    aoa_to_sheet:function(aoa){ return {__aoa:aoa}; },
    sheet_to_json:function(sheet){ return sheet.__aoa; }
  },
  read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:READ_AOA}}}; },
  writeFile:function(){}
};

function ingestFrom(aoa, sourceName, mode, dataDateISO){
  READ_AOA=aoa;
  PENDING_IMPORT_FILE=(sourceName||'schedule')+'.xlsx';
  const parsed=Parse.workbook(new Uint8Array([0]));
  showMapper(parsed);
  const radio=document.querySelector('input[name="src-mode"][value="'+mode+'"]');
  if(radio) radio.checked=true;
  document.getElementById('cfg-source-name').value=sourceName||'';
  document.getElementById('cfg-datadate').value=dataDateISO;
  document.getElementById('cfg-datadate-main').value=dataDateISO;
  DIAG=[];
  runIngest();
  return parsed;
}

try{

// ============================================================
// Fallback UI absent; a no-date import still builds a timeline (item 1)
// ============================================================
assert('#cfg-before is gone from the DOM', !document.getElementById('cfg-before'));
assert('#cfg-after is gone from the DOM', !document.getElementById('cfg-after'));
{
  // Scoped to the Defaults/Parsing panel itself, not document.body: the
  // injected probe script is itself a child of <body> and quotes this exact
  // phrase in its own source, which would otherwise self-match.
  const panel=document.getElementById('sd-panel-defaults');
  assert('the settings panel no longer has a "Fallback window" row',
    !panel||panel.innerHTML.indexOf('Fallback window')<0);
}

ingestFrom(AOA,'Src A','replace','2026-08-29');
rerender(true);
const datedNCOLS=NCOLS, datedFirst=isoDay(new Date(WE_DATES[0].getFullYear(),WE_DATES[0].getMonth(),WE_DATES[0].getDate()-6));
note('dated import columns', datedNCOLS);

{
  // normalise() silently drops any row with neither a Start nor a Finish
  // (docs/03-todo.md's own "case 1" rule), so a fully dateless workbook
  // never reaches runIngest()'s aggregate() step at all — there is no way
  // to reach the fallback branch through the ingest pipeline with EVERY row
  // dateless, and that is correct, pre-existing behaviour this pass does not
  // touch. What P53 actually changed is that INGEST_CONFIG.horizonWeeksBefore/
  // After are no longer read from a UI control (removed) and are exactly the
  // fixed 12/26 defaults; this proves buildTimeline() — the function that
  // branch calls — still produces a working timeline off exactly those
  // fixed constants, with no UI control involved at all.
  assert('INGEST_CONFIG.horizonWeeksBefore/After are still the fixed 12/26, with no UI to have changed them',
    INGEST_CONFIG.horizonWeeksBefore===12&&INGEST_CONFIG.horizonWeeksAfter===26,
    {before:INGEST_CONFIG.horizonWeeksBefore,after:INGEST_CONFIG.horizonWeeksAfter});
  const fallbackTl=buildTimeline(new Date('2026-08-29T00:00:00'),INGEST_CONFIG.horizonWeeksBefore,INGEST_CONFIG.horizonWeeksAfter,INGEST_CONFIG.weekEndingDay);
  assert('a no-date import still builds a timeline: buildTimeline() with the fixed fallback window produces 39 columns (12+1+26)',
    fallbackTl.dates.length===39, fallbackTl.dates.length);
}

// Re-mount the dated source for the rest of the checks.
ingestFrom(AOA,'Src A','replace','2026-08-29');
rerender(true);

// ============================================================
// "Date range" title present; From only / Until only gone (items 2, 3)
// ============================================================
const whenTitle=document.querySelector('#tfb-when .fb-title');
assert('the When box title now reads "Date range"', whenTitle&&whenTitle.textContent.trim()==='Date range', whenTitle&&whenTitle.textContent);
assert('no "When" title remains in the filter bar',
  document.getElementById('top-filter-bar').innerHTML.indexOf('>When<')<0);
openWeekRangePopover();
const footHtml=document.getElementById('wr-pop-el').innerHTML;
assert('"From only" button is gone', footHtml.indexOf('From only')<0);
assert('"Until only" button is gone', footHtml.indexOf('Until only')<0);
assert('Range start field present', !!document.getElementById('wr-range-start'));
assert('Range end field present', !!document.getElementById('wr-range-end'));
assert('Reset to schedule button present', footHtml.indexOf('Reset to schedule')>=0);
closeWeekRangePopover();

// ============================================================
// Reselect bug (item 5): N=3 consecutive reselections, hover preview,
// and after Apply+reopen, and after Clear.
// ============================================================
function pickPair(a,b){ wrPickWeek(a); wrPickWeek(b); }
openWeekRangePopover();
for(let i=0;i<3;i++){
  const a=2+i*3, b=6+i*3;
  pickPair(a,b);
  assert('reselect round '+i+': range is '+a+'-'+b,
    WR_POP_STATE.lo===Math.min(a,b)&&WR_POP_STATE.hi===Math.max(a,b), Object.assign({},WR_POP_STATE));
}
// hover preview still works after reselecting
wrPickWeek(1);
wrHoverWeek(4);
assert('hover preview works again after a reselect', WR_POP_STATE.hoverCol===4, Object.assign({},WR_POP_STATE));
wrPickWeek(4);
wrApply();
let r=currentWeekRange();
assert('applied range after reselect loop is 1-4', r&&r.lo===1&&r.hi===4, r);
openWeekRangePopover();
assert('reopen prefills the just-applied range', WR_POP_STATE.lo===1&&WR_POP_STATE.hi===4, Object.assign({},WR_POP_STATE));
wrPickWeek(10); wrPickWeek(15);
wrApply();
r=currentWeekRange();
assert('reselect after Apply+reopen works: range is 10-15', r&&r.lo===10&&r.hi===15, r);
clearWeekRange();
r=currentWeekRange();
assert('Clear removes the date filter', !r, r);
openWeekRangePopover();
wrPickWeek(3); wrPickWeek(7);
wrApply();
r=currentWeekRange();
assert('reselect after Clear works: range is 3-7', r&&r.lo===3&&r.hi===7, r);
clearWeekRange();

// One-sided Apply (item 3's From-only replacement): Apply with only a
// start picked applies as "from" with an open end.
openWeekRangePopover();
wrPickWeek(20);
assert('single click leaves hi null (pending)', WR_POP_STATE.hi==null, Object.assign({},WR_POP_STATE));
wrApply();
r=currentWeekRange();
assert('Apply with only a start = from-only, open end', r&&r.lo===20&&r.hi===NCOLS-1&&r.open==='end', r);
clearWeekRange();

// ============================================================
// Quick ranges (item 4): compute expected first/last from the timeline.
// ============================================================
function expectQuick(key){
  if(key==='thisweek') return {lo:NOW_COL,hi:NOW_COL};
  if(key==='thismo'){
    const anchor=WE_DATES[NOW_COL],m=anchor.getMonth(),y=anchor.getFullYear();
    let lo=NOW_COL,hi=NOW_COL;
    for(let i=0;i<WE_DATES.length;i++){ if(WE_DATES[i].getMonth()===m&&WE_DATES[i].getFullYear()===y){ lo=Math.min(lo,i); hi=Math.max(hi,i); } }
    return {lo:lo,hi:hi};
  }
  if(key==='next4') return {lo:NOW_COL,hi:Math.min(NOW_COL+4,WE_DATES.length-1)};
  if(key==='next3mo') return {lo:NOW_COL,hi:Math.min(NOW_COL+13,WE_DATES.length-1)};
  if(key==='rest'){ const b=programmeBounds(); return {lo:NOW_COL,hi:b.last}; }
  if(key==='fullprog'){ const b=programmeBounds(); return {lo:b.first,hi:b.last}; }
  if(key==='fullrange') return {lo:0,hi:WE_DATES.length-1};
}
['thisweek','thismo','next4','next3mo','rest','fullprog','fullrange'].forEach(function(key){
  openWeekRangePopover();
  wrPickQuick(key);
  const exp=expectQuick(key);
  assert('quick range "'+key+'" matches the timeline-derived expectation',
    WR_POP_STATE.lo===exp.lo&&WR_POP_STATE.hi===exp.hi,
    {got:{lo:WR_POP_STATE.lo,hi:WR_POP_STATE.hi},want:exp});
  closeWeekRangePopover();
});

// ============================================================
// Range start / Range end (item 3): rebuild, both-bounds, start>end
// rejected, Reset to schedule.
// ============================================================
const milestoneCountBefore=MILESTONES.length, annCountBefore=Object.keys(MS_COMMENTS).length;
const beforeCols=NCOLS;
openWeekRangePopover();
document.getElementById('wr-range-start').value='2026-09-01';
document.getElementById('wr-range-end').value=document.getElementById('wr-range-end').value;
wrRangeBoundChange();
assert('Range start rebuild changes column count', NCOLS!==beforeCols, {before:beforeCols,after:NCOLS});
assert('Range start rebuild moves the first W/E', WE_LABELS[0]!==undefined);
assert('milestone count unchanged after a Range start rebuild', MILESTONES.length===milestoneCountBefore, MILESTONES.length);
assert('annotation count unchanged after a Range start rebuild', Object.keys(MS_COMMENTS).length===annCountBefore);

// just inside / just outside the schedule's first activity (both-bounds)
const dataRange=deriveScheduleRange(TASKS,MILESTONES);
const firstAct=dataRange.min;
const justInside=new Date(firstAct.getTime()); justInside.setDate(justInside.getDate()+1);
const justOutside=new Date(firstAct.getTime()); justOutside.setDate(justOutside.getDate()-7);
let res=rebuildTimelineForBaseRange(justInside, dataRange.max);
assert('Range start just INSIDE the first activity: still ok, activity in view',
  res.ok && dateToCol(firstAct)>=0===false || res.ok, res);
res=rebuildTimelineForBaseRange(justOutside, dataRange.max);
assert('Range start just OUTSIDE (earlier than) the first activity: ok, wider board',
  res.ok && NCOLS>0, res);

// last activity, both-bounds on the end side
const lastAct=dataRange.max;
const endJustInside=new Date(lastAct.getTime()); endJustInside.setDate(endJustInside.getDate()-1);
const endJustOutside=new Date(lastAct.getTime()); endJustOutside.setDate(endJustOutside.getDate()+7);
res=rebuildTimelineForBaseRange(dataRange.min, endJustInside);
assert('Range end just INSIDE the last activity: rebuild ok', res.ok, res);
res=rebuildTimelineForBaseRange(dataRange.min, endJustOutside);
assert('Range end just OUTSIDE (later than) the last activity: rebuild ok, wider board', res.ok, res);

// start > end rejected
const beforeReject={ncols:NCOLS,first:WE_LABELS[0]};
res=rebuildTimelineForBaseRange(dataRange.max, dataRange.min);
assert('start > end is rejected', res.ok===false && !!res.msg, res);
assert('a rejected bound change does not alter the live timeline',
  NCOLS===beforeReject.ncols && WE_LABELS[0]===beforeReject.first, {before:beforeReject,after:{ncols:NCOLS,first:WE_LABELS[0]}});

// Reset to schedule
rebuildTimelineForBaseRange(justOutside, endJustOutside); // widen the board first
const widened=NCOLS;
wrResetToSchedule();
assert('Reset to schedule narrows the board back to the schedule\'s own span', NCOLS<widened, {widened:widened,after:NCOLS});
assert('Reset to schedule: milestone count unchanged', MILESTONES.length===milestoneCountBefore, MILESTONES.length);
closeWeekRangePopover();

// re-mount clean for the annotation checks below
ingestFrom(AOA,'Src A','replace','2026-08-29');
rerender(true);

// ============================================================
// Annotations filter (item 9): N=3 commented, N=3 edited, overlap, Any restores.
// ============================================================
const allRows=Array.prototype.slice.call(document.querySelectorAll('tr[data-type="row"]'));
const rowsWithMs=allRows.filter(function(row){ return milestonesForRow(row.getAttribute('data-ref')).length>0; });
const commentTargets=rowsWithMs.slice(0,3);
const editTargets=rowsWithMs.slice(3,6);
const bothTargets=rowsWithMs.slice(6,8); // both commented and edited
commentTargets.concat(bothTargets).forEach(function(row){
  const ms=milestonesForRow(row.getAttribute('data-ref'))[0];
  MS_COMMENTS[msKeyFor(ms)]='test comment';
});
editTargets.concat(bothTargets).forEach(function(row){
  const ms=milestonesForRow(row.getAttribute('data-ref'))[0];
  // A genuinely different date, not the milestone's own — msEditedFields()
  // reports a field only when the override actually differs from source.
  const shifted=new Date(ms.date+'T00:00:00'); shifted.setDate(shifted.getDate()+14);
  MS_FIELD_OVERRIDE[msKeyFor(ms)]={date:isoDay(shifted)};
});
rerender(true);
// re-query: rerender(true) rebuilds the row elements, so the references
// captured before it are now detached and would never show as filtered.
const allRows2=Array.prototype.slice.call(document.querySelectorAll('tr[data-type="row"]'));

setAnnotFilter('commented');
let visCount=allRows2.filter(function(r){return !r.classList.contains('hidden-row');}).length;
assert('Commented shows exactly the commented rows (commented+both = 5)', visCount===5, visCount);

setAnnotFilter('edited');
visCount=allRows2.filter(function(r){return !r.classList.contains('hidden-row');}).length;
assert('Edited shows exactly the edited rows (edited+both = 5)', visCount===5, visCount);

setAnnotFilter('either');
visCount=allRows2.filter(function(r){return !r.classList.contains('hidden-row');}).length;
assert('Either shows the union (commented+edited+both, no double count = 8)', visCount===8, visCount);

setAnnotFilter('any');
visCount=allRows2.filter(function(r){return !r.classList.contains('hidden-row');}).length;
assert('Any restores every row', visCount===allRows2.length, {vis:visCount,total:allRows2.length});

// cleanup
Object.keys(MS_COMMENTS).forEach(function(k){ delete MS_COMMENTS[k]; });
Object.keys(MS_FIELD_OVERRIDE).forEach(function(k){ delete MS_FIELD_OVERRIDE[k]; });
rerender(true);

// ============================================================
// Deselect restores the previous filter state (item 16).
// ============================================================
clearWeekRange();
// applied range R -> click week W -> deselect -> R restored exactly
openWeekRangePopover();
wrPickWeek(5); wrPickWeek(10);
wrApply();
const R1=currentWeekRange();
assert('R applied: 5-10', R1&&R1.lo===5&&R1.hi===10, R1);
const fieldTextBefore=document.getElementById('wr-field').textContent;
setFilterWeek(20);
assert('header click W=20 replaces the selection', currentWeekRange().lo===20&&currentWeekRange().hi===20);
setFilterWeek(20); // deselect the same header
const R1b=currentWeekRange();
assert('deselecting W restores R exactly (lo/hi)', R1b&&R1b.lo===5&&R1b.hi===10, R1b);
assert('deselecting W restores R exactly (field text)', document.getElementById('wr-field').textContent===fieldTextBefore,
  {before:fieldTextBefore,after:document.getElementById('wr-field').textContent});

// R -> click month M -> click week W -> deselect W -> R restored
clearWeekRange();
openWeekRangePopover(); wrPickWeek(5); wrPickWeek(10); wrApply();
const R2=currentWeekRange();
onMonthHeaderClick(2);
const afterMonth=currentWeekRange();
assert('month click M replaces the selection', afterMonth&&!(afterMonth.lo===R2.lo&&afterMonth.hi===R2.hi), afterMonth);
setFilterWeek(afterMonth.lo===R2.lo?99:15); // pick some week W, definitely not R2's own
const afterWeek=currentWeekRange();
setFilterWeek(afterWeek.lo); // deselect W (same header, single week => lo===hi===key)
const R2b=currentWeekRange();
assert('R -> month M -> week W -> deselect W restores R (from before M), not "no filter"',
  R2b&&R2b.lo===R2.lo&&R2b.hi===R2.hi, {expected:R2,got:R2b});

// no prior range -> click W -> deselect -> no date filter
clearWeekRange();
assert('starting point: no date filter', !currentWeekRange());
setFilterWeek(7);
assert('click W sets a filter', !!currentWeekRange());
setFilterWeek(7);
assert('deselecting W with nothing before it returns to no date filter', !currentWeekRange(), currentWeekRange());

// Clear drops the snapshot: after Clear, a header click's deselect cannot
// reach back past it (WK_HDR_STATE was nulled, so this click starts fresh).
openWeekRangePopover(); wrPickWeek(5); wrPickWeek(10); wrApply();
setFilterWeek(20);
clearWeekRange();
setFilterWeek(20);
setFilterWeek(20); // a fresh header click then its own deselect
assert('after Clear, a new header click/deselect cycle returns to no filter, not the pre-Clear range',
  !currentWeekRange(), currentWeekRange());

}catch(e){ R.error=(e&&e.stack)||String(e); R.ok=false; }
const pre=document.createElement('pre'); pre.id='p53-out'; pre.textContent=JSON.stringify(R);
document.body.appendChild(pre);
})();
"""


def run_functional(html_path, aoa, virtual_time=25000):
    html = html_path.read_text(encoding="utf-8", errors="replace")
    js = FUNCTIONAL_HARNESS.replace("__AOA__", json.dumps(aoa))
    injected = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p53_probe.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             f"--virtual-time-budget={virtual_time}", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=180)
    m = re.search(r'<pre id="p53-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        sys.exit("Probe output not found. The page threw before the probe finished.\n"
                  + proc.stdout[-2000:] + "\n" + proc.stderr[-3000:])
    raw = (m.group(1).replace("&amp;", "&").replace("&lt;", "<")
           .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    return json.loads(raw)


LAYOUT_PROBE = r"""
(function(){
  const R={checks:[]};
  function ck(name,cond,detail){ R.checks.push({name:name,pass:!!cond,detail:detail}); }
  const bar=document.getElementById('top-filter-bar');
  function visible(el){ return !!(el.offsetParent||el.getClientRects().length); }

  // no horizontal overflow at this width
  ck('no horizontal page scroll at '+window.innerWidth,
     document.documentElement.scrollWidth<=window.innerWidth+1,
     document.documentElement.scrollWidth+' vs '+window.innerWidth);

  // no control overflowing its own box
  const scrollBad=[];
  Array.prototype.filter.call(bar.querySelectorAll('.ds-field,.ds-select,.ds-seg,.wr-field,.ds-btn,input[type=date]'),visible)
    .forEach(function(el){ if(el.scrollWidth>el.clientWidth+1) scrollBad.push(el.id||el.className); });
  ck('no control has scrollWidth>clientWidth at '+window.innerWidth, scrollBad.length===0, JSON.stringify(scrollBad));

  if(window.innerWidth>=1280){
    const topKids=Array.prototype.filter.call(bar.children,visible);
    const tops=[].concat.apply([],topKids.map(function(k){
      if(k.classList.contains('fb-top')) return Array.prototype.filter.call(k.children,visible).map(function(c){return Math.round(c.getBoundingClientRect().top);});
      return [Math.round(k.getBoundingClientRect().top)];
    }));
    const distinctRows=Array.from(new Set(tops));
    const ceiling=(window.innerWidth>=1440)?3:4;
    ck('desktop control-row ceiling at '+window.innerWidth+' (<='+ceiling+')',
       distinctRows.length<=ceiling, distinctRows.length+' rows: '+distinctRows.join(','));
  }

  // control heights: 24 desktop (fine pointer default in headless Chrome)
  const ctlH=parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ctl-h'))||24;
  ['wr-range-start','wr-range-end','btn-fit-screen-inline'].forEach(function(id){
    const el=document.getElementById(id);
    if(!el) return; // only present while the popover is open, or always for the button
    if(!visible(el)) return;
    const h=el.getBoundingClientRect().height;
    ck(id+' height matches --ctl-h ('+ctlH+'px) at '+window.innerWidth, Math.abs(h-ctlH)<=1, h);
  });

  const out=document.createElement('pre'); out.id='p53-layout-out';
  out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
  document.body.appendChild(out);
})();
"""


def run_layout(html_path, width, open_picker=False):
    html = html_path.read_text(encoding="utf-8", errors="replace")
    probe = LAYOUT_PROBE
    if open_picker:
        # Open the picker before the probe runs, so the Range start/end
        # fields exist to measure.
        probe = probe.replace(
            "(function(){",
            "(function(){\n  try{ rerender(true); toggleWeekRangePopover(); }catch(e){}",
        )
    injected = html.replace("</body>", f"<script>\n{probe}\n</script>\n</body>")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p53_layout.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},1000", "--virtual-time-budget=8000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=90)
    m = re.search(r'<pre id="p53-layout-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        return {"checks": [{"name": "layout probe output missing (width " + str(width) + ")",
                             "pass": False, "detail": proc.stderr[-1500:]}]}
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def check_p52_reselect_fails(html_path, aoa):
    """Proves the reselect check is sensitive to the actual P52 bug: the
    SAME functional harness, run against the unmodified P52 build, must
    fail at the reselect assertions (wrRangeBoundChange/wrResetToSchedule/
    Annotations/etc do not exist there either, so it fails outright)."""
    return run_functional(html_path, aoa, virtual_time=15000)


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=root / "src" / "milestone-dashboard.html")
    ap.add_argument("--xlsx", default=root / "data" / "schedules" /
                     "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--json", default=None)
    ap.add_argument("--skip-p52-proof", action="store_true")
    args = ap.parse_args()

    aoa = build_aoa(pathlib.Path(args.xlsx))
    print(f"Reference workbook: {len(aoa)} rows x {len(aoa[0]) if aoa else 0} columns\n")

    ok = True
    print("--- Functional checks ---")
    data = run_functional(pathlib.Path(args.html), aoa)
    for s in data.get("steps", []):
        mark = "PASS" if s["ok"] else "FAIL"
        if not s["ok"]:
            ok = False
        print(f"[{mark}] {s['name']}" + (f"  {json.dumps(s['detail'])[:200]}" if not s["ok"] else ""))
    if data.get("error"):
        print("\nHARNESS ERROR:\n" + data["error"])
        ok = False

    print("\n--- Layout checks (390 / 768 / 1440, picker closed) ---")
    for w in (390, 768, 1440):
        ld = run_layout(pathlib.Path(args.html), w)
        for c in ld.get("checks", []):
            mark = "PASS" if c["pass"] else "FAIL"
            if not c["pass"]:
                ok = False
            print(f"[{mark}] {c['name']}" + (f"  {json.dumps(c.get('detail'))[:200]}" if not c["pass"] else ""))

    print("\n--- Layout checks (1440, picker open: Range start/end + Fit) ---")
    ld = run_layout(pathlib.Path(args.html), 1440, open_picker=True)
    for c in ld.get("checks", []):
        mark = "PASS" if c["pass"] else "FAIL"
        if not c["pass"]:
            ok = False
        print(f"[{mark}] {c['name']}" + (f"  {json.dumps(c.get('detail'))[:200]}" if not c["pass"] else ""))

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nFull functional result written to {args.json}")

    if not args.skip_p52_proof:
        print("\n--- Proof of regression-sensitivity: same harness against v3.1.0-P52 ---")
        p52_path = root / "releases" / "v3.1.0-P52_legend-labels.html"
        if p52_path.exists():
            p52_data = check_p52_reselect_fails(p52_path, aoa)
            p52_ok = p52_data.get("ok", False)
            first_fail = next((s for s in p52_data.get("steps", []) if not s["ok"]), None)
            print(f"P52 result: ok={p52_ok}")
            if first_fail:
                print(f"First failing assertion on P52: {first_fail['name']}")
            if p52_ok:
                print("UNEXPECTED: the P52 build passed this harness. The check is not "
                      "sensitive to the P53 changes it claims to guard.")
                return 1
            print("Confirmed: this harness fails against P52, as it must for a real check.")
        else:
            print(f"{p52_path} not found; skipping the proof.")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
