#!/usr/bin/env python3
"""
D-17a Sources tab check (v3.1.0-P51).

Drives the real app pipeline (runIngest, saveAddMilestone, the Sources tab's
own toggle/remove/export functions, publishStatePayload/applyPublishedState)
in headless Chromium and asserts the D-17a acceptance criteria from the plan
(gleaming-enchanting-tide.md, "D-17 Data manager") and the build brief.

Reuses find_chrome() and build_aoa() from tools/import_check.py rather than
duplicating them (same reference workbook, same numFmt-aware AoA builder).
XLSX is stubbed at the same boundary those checks use (XLSX.read /
utils.sheet_to_json / utils.aoa_to_sheet / writeFile), so no network call is
needed for either direction (ingest or the schedule-format export).

Usage:
  python3 tools/d17a_check.py [--html FILE] [--json OUT]
Exit code 1 if any assertion fails.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import build_aoa, find_chrome  # noqa: E402

HARNESS = r"""
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

let READ_AOA=null, CAP_WB=null;
window.XLSX = {
  utils:{
    book_new:function(){ return {SheetNames:[], Sheets:{}}; },
    book_append_sheet:function(wb,ws,name){ wb.SheetNames.push(name); wb.Sheets[name]=ws; },
    aoa_to_sheet:function(aoa){ return {__aoa:aoa}; },
    sheet_to_json:function(sheet){ return sheet.__aoa; }
  },
  read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:READ_AOA}}}; },
  writeFile:function(wb, filename){
    CAP_WB={filename:filename, sheets:{}};
    wb.SheetNames.forEach(function(n){ CAP_WB.sheets[n]=wb.Sheets[n].__aoa; });
  }
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
function addUserMs(id,name,dateISO){
  openAddMilestone(null,null);
  document.getElementById('add-ms-id').value=id;
  document.getElementById('add-ms-name').value=name;
  document.getElementById('add-ms-date').value=dateISO;
  saveAddMilestone();
}

try{

// ============================================================
// N=3 sources: append, toggle off/on, both-bounds (all-off / all-back-on)
// ============================================================
ingestFrom(AOA,'Src A','replace','2026-08-29');
rerender(true);
const srcA=PRIMARY_SOURCES[0];
assert('source A mounted, enabled by default', !!srcA && srcA.enabled===true);
const countA=MILESTONES.length;
note('countA', countA);

ingestFrom(AOA,'Src B','append','2026-09-05');
rerender(true);
const srcB=PRIMARY_SOURCES[PRIMARY_SOURCES.length-1];
assert('source B appended, enabled by default', !!srcB && srcB.enabled===true && srcB!==srcA);
const countAB=MILESTONES.length;
note('countAB', countAB);
assert('B added at least one milestone', countAB>countA);

ingestFrom(AOA,'Src C','append','2026-09-12');
rerender(true);
const srcC=PRIMARY_SOURCES[PRIMARY_SOURCES.length-1];
assert('three sources mounted', PRIMARY_SOURCES.length===3);
const countABC=MILESTONES.length;
note('countABC', countABC);

const bCount=srcB.milestones.length;
toggleSourceEnabled(srcB.id);
rerender(true);
assert('B off reduces MILESTONES by exactly B\'s own count',
  MILESTONES.length===(countABC-bCount),
  {before:countABC, after:MILESTONES.length, bCount:bCount});
assert('B.enabled is false after toggling off', srcB.enabled===false);
assert('sources still listed while B is off (not discarded)', PRIMARY_SOURCES.length===3);
toggleSourceEnabled(srcB.id);
rerender(true);
assert('B on restores the full count', MILESTONES.length===countABC);
assert('B.enabled is true after toggling back on', srcB.enabled===true);

// ---- all off: both-bounds (nothing off -> everything off -> everything on)
toggleSourceEnabled(srcA.id);
toggleSourceEnabled(srcB.id);
toggleSourceEnabled(srcC.id);
rerender(true);
assert('all off: sources still listed (no discardUpdate)', PRIMARY_SOURCES.length===3);
assert('all off: board is empty', TASKS.length===0 && MILESTONES.length===0);
assert('all off: each source keeps its own data', srcA.milestones.length>0 && srcB.milestones.length>0 && srcC.milestones.length>0);
toggleSourceEnabled(srcA.id);
toggleSourceEnabled(srcB.id);
toggleSourceEnabled(srcC.id);
rerender(true);
assert('all back on restores the full count, data intact', MILESTONES.length===countABC);

// ============================================================
// Duplicate warning: constructed directly (append-mode dedupe would
// otherwise suffix every genuine collision away before it could be seen).
// ============================================================
const dupSrc={id:'src-dup-test', name:'Dup Source', kind:'primary',
  tasks:srcA.tasks.map(function(t){ return Object.assign({},t,{sourceSchedule:'Dup Source'}); }),
  milestones:srcA.milestones.map(function(m){ return Object.assign({},m,{source:'Dup Source'}); }),
  dataDate:new Date(), file:'dup.xlsx', rows:srcA.milestones.length,
  importedAt:new Date(), suffixed:0, enabled:true};
PRIMARY_SOURCES.push(dupSrc);
rebuildPrimaryDatasets();
TASKS=UPDATE_TASKS.slice();MILESTONES=UPDATE_MILESTONES.slice();invalidateMsIndexes();
rerender(true);
renderMounts();
let mountHtml=document.getElementById('mount-body').innerHTML;
assert('duplicate warning appears for two enabled sources sharing IDs', mountHtml.indexOf('are in both')>=0);
toggleSourceEnabled(dupSrc.id);
renderMounts();
mountHtml=document.getElementById('mount-body').innerHTML;
assert('duplicate warning disappears once one of the pair is off', mountHtml.indexOf('are in both')<0);
// tear down the synthetic duplicate so it does not pollute later steps
PRIMARY_SOURCES=PRIMARY_SOURCES.filter(function(s){ return s!==dupSrc; });
rebuildPrimaryDatasets();
TASKS=UPDATE_TASKS.slice();MILESTONES=UPDATE_MILESTONES.slice();invalidateMsIndexes();
rerender(true);

// ============================================================
// User-defined milestones: add 3 (header-button path), source tag,
// Source filter, filtering, on/off.
// ============================================================
const wd=WE_DATES||[];
const pick=function(i){ return isoDay(wd[Math.max(0,Math.min(wd.length-1,i))]); };
const d1=pick(2), d2=pick(Math.floor(wd.length/2)), d3=pick(wd.length-3);
addUserMs('USR-9001','D17A Test One',d1);
addUserMs('USR-9002','D17A Test Two',d2);
addUserMs('USR-9003','D17A Test Three',d3);
rerender(true);
assert('3 user-defined milestones added', USER_MILESTONES.length===3, USER_MILESTONES.map(function(m){return m.id;}));
assert('every user-defined milestone carries source User-defined',
  USER_MILESTONES.every(function(m){ return m.source==='User-defined'; }));
rebuildSourceFilter();
const srcSel=document.getElementById('filter-source');
const opts=Array.prototype.map.call(srcSel.options, function(o){ return o.value; });
assert('Source filter lists User-defined', opts.indexOf('User-defined')>=0, opts);
srcSel.value='User-defined';
applyFilter();
const visibleUserRows=Array.prototype.filter.call(
  document.querySelectorAll('tr[data-type="row"]'),
  function(tr){ return tr.style.display!=='none' && tr.getAttribute('data-source')==='User-defined'; }
).length;
assert('filtering to User-defined shows exactly 3 rows', visibleUserRows===3, visibleUserRows);
srcSel.value='';
applyFilter();

const preToggleCount=MILESTONES.length;
toggleUserDefinedEnabled();
rerender(true);
assert('User-defined off hides exactly 3 milestones', MILESTONES.length===preToggleCount-3,
  {before:preToggleCount, after:MILESTONES.length});
assert('USER_MILESTONES store itself is untouched by the off switch', USER_MILESTONES.length===3);
toggleUserDefinedEnabled();
rerender(true);
assert('User-defined on restores the 3 milestones', MILESTONES.length===preToggleCount);

// ============================================================
// Schedule-format export, then round-trip re-import.
// ============================================================
exportUserDefinedSchedule();
await wait(150);
assert('export captured a workbook', !!CAP_WB);
if(CAP_WB){
  const sheet=CAP_WB.sheets['User-defined'];
  assert('export has a sheet named User-defined', !!sheet);
  if(sheet){
    const header=sheet[0];
    const expectHeader=['Activity ID','Activity Name','Start','Finish','Total Float',
      'Status','Predecessor Details','Successor Details','WBS','Budgeted Units','% Complete'];
    assert('export header matches the importer\'s own column names exactly',
      JSON.stringify(header)===JSON.stringify(expectHeader), header);
    assert('export has exactly 3 data rows', sheet.length===4, sheet.length);
    const ids=sheet.slice(1).map(function(r){ return r[0]; });
    assert('export rows carry the 3 USR IDs', JSON.stringify(ids.slice().sort())===JSON.stringify(['USR-9001','USR-9002','USR-9003']), ids);
  }

  const sourcesBeforeReimport=PRIMARY_SOURCES.length;
  ingestFrom(sheet, 'User-defined', 'append', d1);
  rerender(true);
  assert('re-import created no new PRIMARY_SOURCES entry', PRIMARY_SOURCES.length===sourcesBeforeReimport,
    {before:sourcesBeforeReimport, after:PRIMARY_SOURCES.length});
  assert('re-import still shows exactly the 3 USR IDs, no duplicates', USER_MILESTONES.length===3,
    USER_MILESTONES.map(function(m){return m.id;}));
  const reimported=USER_MILESTONES.find(function(m){ return m.id==='USR-9001'; });
  assert('re-imported USR-9001 keeps its name and finish date',
    !!reimported && reimported.actName==='D17A Test One' && reimported.date===d1,
    reimported);
}

// ============================================================
// Publish / reopen: no phantom source, enabled flags restored,
// user milestones present exactly once.
// ============================================================
toggleSourceEnabled(srcB.id); // leave B off deliberately, to prove the flag round-trips
toggleUserDefinedEnabled();   // and User-defined off, likewise
toggleUserDefinedEnabled();   // ...then back on: prove a TRUE flag also round-trips
// A real publish serialises to JSON before ever being read back, so the
// harness has to round-trip it too: publishStatePayload() returns live
// array references, and mutating USER_MILESTONES/PRIMARY_SOURCES next would
// otherwise mutate the "captured" payload out from under this assertion.
const payload=JSON.parse(JSON.stringify(publishStatePayload()));
const sourceNamesBefore=PRIMARY_SOURCES.map(function(s){return s.name;}).sort();
const enabledBefore={}; PRIMARY_SOURCES.forEach(function(s){ enabledBefore[s.name]=(s.enabled!==false); });
const userMsIdsBefore=USER_MILESTONES.map(function(m){return m.id;}).sort();

PRIMARY_SOURCES=[]; SOURCE_SEQ=0;
USER_MILESTONES.length=0; USER_ROWS.length=0; USER_MS_ENABLED=true;
TASKS=[]; MILESTONES=[];
restorePrimarySources(payload);
applyUserMilestones(payload);
TASKS=(UPDATE_TASKS||[]).slice(); MILESTONES=(UPDATE_MILESTONES||[]).slice();
invalidateMsIndexes();
rerender(true);

const sourceNamesAfter=PRIMARY_SOURCES.map(function(s){return s.name;}).sort();
assert('reopen: no phantom User-defined primary source', sourceNamesAfter.indexOf('User-defined')<0, sourceNamesAfter);
assert('reopen: the same real sources come back, nothing extra', JSON.stringify(sourceNamesAfter)===JSON.stringify(sourceNamesBefore),
  {before:sourceNamesBefore, after:sourceNamesAfter});
let enabledOk=true;
PRIMARY_SOURCES.forEach(function(s){ if((s.enabled!==false)!==enabledBefore[s.name]) enabledOk=false; });
assert('reopen: enabled flags restored per source', enabledOk, {before:enabledBefore, after:PRIMARY_SOURCES.map(function(s){return [s.name,s.enabled];})});
assert('reopen: USER_MS_ENABLED restored true', USER_MS_ENABLED===true);
const userMsIdsAfter=USER_MILESTONES.map(function(m){return m.id;}).sort();
assert('reopen: user milestones present exactly once, not duplicated', JSON.stringify(userMsIdsAfter)===JSON.stringify(userMsIdsBefore),
  {before:userMsIdsBefore, after:userMsIdsAfter});

// ============================================================
// Inline confirm layout: text above, Cancel bottom-left, Remove
// bottom-right (design-standard.md "Inline confirmation").
// ============================================================
askRemoveSource(srcA.id);
renderMounts();
const confirmBox=document.querySelector('#mount-body .sd-confirm');
assert('inline confirm box renders for Remove', !!confirmBox);
if(confirmBox){
  const txt=confirmBox.querySelector('.sd-confirm-txt');
  const cancelBtn=Array.prototype.find.call(confirmBox.querySelectorAll('button'), function(b){ return b.textContent.trim()==='Cancel'; });
  const removeBtn=Array.prototype.find.call(confirmBox.querySelectorAll('button'), function(b){ return b.textContent.trim()==='Remove'; });
  assert('confirm has message text, Cancel and Remove buttons', !!txt && !!cancelBtn && !!removeBtn);
  if(txt && cancelBtn && removeBtn){
    const tR=txt.getBoundingClientRect(), cR=cancelBtn.getBoundingClientRect(), rR=removeBtn.getBoundingClientRect();
    assert('message sits above the buttons', tR.bottom<=cR.top+1);
    assert('Cancel is left of Remove, both on the same row', cR.left<rR.left && Math.abs(cR.top-rR.top)<2, {cancel:cR, remove:rR});
  }
}
cancelRemoveSource();
renderMounts();

// ============================================================
// Control sizing: the Sources tab reuses the Settings drawer's existing
// .toggle-switch / .toggle-btn components (already used for every other
// on/off and action in this same tab, e.g. the Baseline shadow switch and
// Rename/Remove on the pre-D-17a mount cards) rather than inventing new
// ones, so the real assertion is CONSISTENCY with those, not the literal
// 24/32px token: a full D-16 pass over .toggle-switch/.toggle-btn is D-16c,
// not D-17a. Measure the element itself, not a parent (CLAUDE.md).
// ============================================================
const newSwitch=document.querySelector('#mount-body .src-row .toggle-switch');
const otherSwitch=document.querySelector('.toggle-switch-row .toggle-switch');
assert('a toggle-switch is present on a Sources-tab row', !!newSwitch);
if(newSwitch && otherSwitch){
  const a=newSwitch.getBoundingClientRect(), b=otherSwitch.getBoundingClientRect();
  assert('its height matches the app\'s one existing toggle-switch component (no second, divergent switch style)',
    Math.abs(a.height-b.height)<0.5, {sourcesTab:a.height, elsewhere:b.height});
}
const newBtn=document.querySelector('#mount-body .src-row .toggle-btn');
const otherBtn=Array.prototype.find.call(document.querySelectorAll('.toggle-btn'),
  function(b){ return !b.closest('#mount-body') && b.getBoundingClientRect().height>0; });
assert('a toggle-btn (Rename/Remove) is present on a Sources-tab row', !!newBtn);
if(newBtn && otherBtn){
  const a=newBtn.getBoundingClientRect(), b=otherBtn.getBoundingClientRect();
  assert('its height matches the app\'s one existing .toggle-btn component (same class, same computed size)',
    Math.abs(a.height-b.height)<3, {sourcesTabBtn:a.height, tabBtn:b.height});
}

}catch(e){
  R.ok=false;
  R.error=(e&&e.stack)?e.stack:String(e);
}

const pre=document.createElement('pre');
pre.id='d17a-probe-out';
pre.textContent=JSON.stringify(R);
document.body.appendChild(pre);
})();
"""


def run(html_path, aoa, virtual_time=25000):
    html = html_path.read_text(encoding="utf-8", errors="replace")
    js = HARNESS.replace("__AOA__", json.dumps(aoa))
    injected = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "d17a_probe.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             f"--virtual-time-budget={virtual_time}", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=180)
    m = re.search(r'<pre id="d17a-probe-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        sys.exit("Probe output not found. The page threw before the probe finished.\n"
                  + proc.stdout[-2000:] + "\n" + proc.stderr[-3000:])
    raw = (m.group(1).replace("&amp;", "&").replace("&lt;", "<")
           .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    return json.loads(raw)


def check_p50_lacks_the_new_api(html_path):
    """Proves the check is sensitive to the actual regression: P50 (the
    commit this build shipped from) has neither toggleSourceEnabled() nor
    an `enabled` field on PRIMARY_SOURCES entries, so the same harness's
    very first real assertion ("source A mounted, enabled by default")
    fails against it. Run with --virtual-time-budget short since the
    P50 build has no D-17a code to wait on."""
    data = run(html_path, build_aoa(
        pathlib.Path(__file__).resolve().parent.parent / "data" / "schedules" /
        "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"), virtual_time=15000)
    return data


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=root / "src" / "milestone-dashboard.html")
    ap.add_argument("--xlsx", default=root / "data" / "schedules" /
                     "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--json", default=None)
    ap.add_argument("--skip-p50-proof", action="store_true")
    args = ap.parse_args()

    aoa = build_aoa(pathlib.Path(args.xlsx))
    print(f"Reference workbook: {len(aoa)} rows x {len(aoa[0]) if aoa else 0} columns\n")

    data = run(pathlib.Path(args.html), aoa)
    ok = data.get("ok", False)
    for s in data.get("steps", []):
        mark = "PASS" if s["ok"] else "FAIL"
        print(f"[{mark}] {s['name']}" + (f"  {json.dumps(s['detail'])[:200]}" if s["ok"] is False else ""))
    if data.get("error"):
        print("\nHARNESS ERROR:\n" + data["error"])
        ok = False

    print()
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Full result written to {args.json}")

    if not args.skip_p50_proof:
        print("\n--- Proof of regression-sensitivity: same harness against v3.1.0-P50 ---")
        try:
            p50_text = subprocess.run(
                ["git", "show", "HEAD:./src/milestone-dashboard.html"],
                cwd=root, capture_output=True, text=True, timeout=30, check=True).stdout
        except Exception as e:  # noqa: BLE001
            print(f"Could not read P50 from git history ({e}); skipping the proof.")
            p50_text = None
        if p50_text and "3.1.0-P50" in p50_text:
            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(p50_text)
                p50_path = pathlib.Path(f.name)
            p50_data = check_p50_lacks_the_new_api(p50_path)
            p50_ok = p50_data.get("ok", False)
            first_fail = next((s for s in p50_data.get("steps", []) if not s["ok"]), None)
            print(f"P50 result: ok={p50_ok}, error={p50_data.get('error', '')[:200]}")
            if first_fail:
                print(f"First failing assertion on P50: {first_fail['name']}")
            if p50_ok:
                print("UNEXPECTED: the P50 build passed this harness. The check is not "
                      "sensitive to the D-17a regression it claims to guard.")
                return 1
            print("Confirmed: this harness fails against P50, as it must for a real check.")
        else:
            print("HEAD is not v3.1.0-P50; skipping the proof (run from the branch this was built on).")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
