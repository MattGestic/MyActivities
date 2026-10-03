#!/usr/bin/env python3
"""P79 check: continue from a saved dashboard (Matt, 2026-10-03, TD-247).

"Open the blank copy ... select the previous file that they saved, with the
schedule and all of their notes ... the previous file is now mirrored in the
current."

Headless Chromium with --dump-dom through chrome_fixture.py, two pages:

  A  the app seeded with the test fixture (as every check gets it): a remark,
     a user milestone, a note and a project number are added, then the real
     Save (publishDashboard()) writes a saved copy, which is captured with the
     counts it should carry.
  B  the app as it ships (sret:no-fixture), the blank copy, at 1440x900 and
     390x844, given A's saved file as a File:
      - interim UI: Continue from saved is on the empty state, on screen, no
        sideways scroll; the dialog fits the viewport;
      - refusals leave the board empty: a report page, an annotations-only
        model export, the blank app itself; a dropped .xlsx is not taken,
        a dropped report page is (and refused);
      - load: the summary names the project and the counts; Load mirrors the
        saved file (rows, milestones, user milestones drawn, entries, notes,
        baseline, project number), the empty state goes, the work shows as
        unsaved, the provenance chain is the saved file's;
      - the saved file's scripts never run (a sentinel script in it stays inert);
      - Save again: the new file reads back to the same counts, chain + 1;
      - loading over a board that has work warns, and keeps a pinned
        Before continue backup;
      - a load that fails part way puts the board back as it was;
      - no em dash in anything the dialog shows; no page errors.

    python3 tools/p79_continue_check.py [--html FILE]
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
sys.path.insert(0, str(ROOT / "tools" / "check_map"))
from import_check import find_chrome  # noqa: E402

OPT_OUT = "<!-- sret:no-fixture: P79 B opens the blank app as it ships -->"
EARLY = r"""<script>
window.__errs=[];
addEventListener('error',function(e){ if(/^ResizeObserver loop/.test(e.message||'')) return; __errs.push('error: '+e.message+' @'+e.lineno); });
(function(){ var o=console.error; console.error=function(){ __errs.push('console.error: '+Array.prototype.join.call(arguments,' ')); return o.apply(console,arguments); }; })();
</script>"""

COMMON = r"""
const R={checks:[],out:{}};
const TAG=__TAG__;
function ck(n,p,d){ R.checks.push({name:TAG+': '+n,pass:!!p,detail:d===undefined?'':String(d).slice(0,400)}); }
function emit(){ R.errs=window.__errs.slice(); const o=document.createElement('pre'); o.id='p79-out';
  o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
const settle=(ms)=>new Promise(r=>setTimeout(r,ms||250));
const $=id=>document.getElementById(id);
const rc=el=>el.getBoundingClientRect();
function onScreen(el){ const r=rc(el); return r.width>0&&r.left>=-0.5&&r.right<=innerWidth+0.5&&r.top>=-0.5&&r.bottom<=innerHeight+0.5; }
function noSideways(){ return document.documentElement.scrollWidth<=innerWidth+1; }
const CAPT=[];
const _click=HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click=function(){ if(this.download){ CAPT.push({name:this.download,href:this.href}); return; } return _click.apply(this,arguments); };
async function blobText(href){ const r=await fetch(href); return r.text(); }
function counts(){ return {rows:TASKS.length,ms:MILESTONES.length,um:USER_MILESTONES.length,entries:ENTRIES.length,
  notes:NOTES.length,baseline:hasBaseline(),projectNo:REPORT_META.projectNo||'',chain:PUBLISH_CHAIN.length}; }
"""

A = r"""<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
try{
  await settle(600);
  ck('fixture seeded a schedule', TASKS.length>0&&hasBaseline(), TASKS.length);
  const k=Object.keys(entryMsIndex())[0];
  addRemarkEntry(k,'P79 remark carried to next period'); noteMarkup();
  const um=addUserMilestone({name:'P79 user milestone',date:isoDay(WE_DATES[Math.min(WE_DATES.length-1,NOW_COL+2)]),type:'MS',state:'FUTURE'});
  noteMarkup(); scheduleRerender(true);
  $('note-input').value='P79 note carried'; saveNewNote();
  setProjectNo('123456-7');
  await settle(600);
  publishDashboard(); await settle(400);
  const pub=CAPT.filter(c=>/\.html$/.test(c.name)).pop();
  ck('Save produced a saved copy', !!pub, CAPT.map(c=>c.name).join(','));
  R.out.counts=counts(); R.out.um=um.id; R.out.name=pub?pub.name:'';
  if(pub) R.out.saved=btoa(unescape(encodeURIComponent(await blobText(pub.href))));
}catch(e){ ck('probe A ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""

B = OPT_OUT + r"""
<script type="text/plain" id="p79-saved">__SAVED__</script>
<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
const EXP=__EXP__;
const savedText=decodeURIComponent(escape(atob($('p79-saved').textContent.trim())));
const file=(t,n,type)=>new File([t],n,{type:type||'text/html'});
const dlgOpen=()=>!$('continue-dialog').hidden;
const dlgText=()=>$('continue-dialog-body').textContent;
async function choose(f){ await continueChosen(f); }
function drop(f){ const dt=new DataTransfer(); dt.items.add(f);
  const ev=new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}); $('empty-state').dispatchEvent(ev); return ev.defaultPrevented; }
const shown=[];
try{
  const st=document.createElement('style'); st.textContent='*{transition:none!important}'; document.head.appendChild(st);
  await settle(800);
  ck('blank copy opens on the empty state', isDashboardEmpty()&&!$('empty-state').hidden);
  const btn=$('es-continue');
  ck('interim UI: Continue from saved is on the empty state and on screen', !!btn&&onScreen(btn), btn&&JSON.stringify(rc(btn)));
  ck('interim UI: no sideways scroll on the empty state', noSideways(), document.documentElement.scrollWidth);
  ck('interim UI: the picker takes .html, .htm and .json', $('continue-file').accept==='.html,.htm,.json');

  // ---- refusals ----
  await choose(file('<!doctype html><html><body><h1>Report</h1></body></html>','Report.html'));
  shown.push(dlgText());
  ck('refused: a report page shows an error and no Load', dlgOpen()&&/no saved dashboard data/.test(dlgText())&&$('continue-apply').hidden, dlgText());
  ck('interim UI: the dialog fits the viewport', onScreen(document.querySelector('#continue-dialog .annot-panel')));
  continueClose();
  ck('refused: Cancel closes and the board stays empty', !dlgOpen()&&isDashboardEmpty());
  await choose(file(JSON.stringify({kind:'milestone-dashboard-model',schemaVersion:1,timeline:{labels:['a'],nowCol:0},tasks:[],milestones:[],milestoneComments:{x:'y'}}),'model.json','application/json'));
  shown.push(dlgText());
  ck('refused: an annotations export points to Sources', /annotations export/.test(dlgText())&&/Sources/.test(dlgText())&&$('continue-apply').hidden, dlgText());
  continueClose();
  ck('refused: Load with nothing pending does nothing', continueApply().ok===false&&isDashboardEmpty());
  ck('drop: a dropped .xlsx is not taken', drop(file('x','sched.xlsx','application/octet-stream'))===false);
  const took=drop(file('<html><body>r</body></html>','Other.html')); for(let i=0;i<40&&!dlgOpen();i++) await settle(50);
  ck('drop: a dropped .html is taken and checked', took&&dlgOpen()&&$('continue-apply').hidden, dlgText());
  continueClose();

  // ---- load ----
  const poisoned=savedText.replace('</head>','<script>window.__p79pwned=1;<\/script></head>');
  await choose(file(poisoned,EXP.name));
  shown.push(dlgText());
  ck('load: the dialog offers Load', dlgOpen()&&!$('continue-apply').hidden, dlgText());
  ck('load: the summary names the project, milestones, user tasks, updates, notes and baseline',
     /Project 123456-7/.test(dlgText())&&new RegExp(EXP.counts.ms+' milestones').test(dlgText())&&/1 user task(?!s)/.test(dlgText())&&
     new RegExp(EXP.counts.entries+' updates?').test(dlgText())&&/Baseline included/.test(dlgText()), dlgText());
  ck('load: no replace warning on an empty board', !/replaces what is on the board/.test(dlgText()));
  ck('load: the dialog fits the viewport', onScreen(document.querySelector('#continue-dialog .annot-panel')));
  $('continue-apply').click(); await settle(800);
  const c=counts();
  ck('load: the dialog closed', !dlgOpen());
  ck('load: the board mirrors the saved file (rows, milestones, user milestones, entries, notes, baseline, project no.)',
     c.rows===EXP.counts.rows&&c.ms===EXP.counts.ms&&c.um===EXP.counts.um&&c.entries===EXP.counts.entries&&
     c.notes===EXP.counts.notes&&c.baseline&&c.projectNo==='123456-7', JSON.stringify(c)+' vs '+JSON.stringify(EXP.counts));
  ck('load: the remark and the note came across', ENTRIES.some(e=>/P79 remark carried/.test(e.text||''))&&NOTES.some(n=>/P79 note carried/.test(JSON.stringify(n))));
  ck('load: the user milestone is drawn on the board', !!document.querySelector('#tbody .m-wrap[data-ms="'+EXP.um+'"]'));
  ck('load: rows are rendered and the empty state is gone', $('tbody').querySelectorAll('tr').length>0&&$('empty-state').hidden&&!document.body.classList.contains('is-empty'));
  ck('load: the work shows as unsaved', $('dirty-indicator').classList.contains('show'));
  ck('load: provenance is the saved file\'s chain', PUBLISH_CHAIN.length===EXP.counts.chain+1&&PUBLISHED_META&&PUBLISHED_META.publishedAt instanceof Date, PUBLISH_CHAIN.length+' vs '+(EXP.counts.chain+1));
  ck('load: CONTINUED_FROM names the file', CONTINUED_FROM&&CONTINUED_FROM.file===EXP.name);
  ck('security: the saved file\'s scripts never ran', window.__p79pwned===undefined);
  ck('load: no sideways scroll', noSideways(), document.documentElement.scrollWidth);

  // ---- save again: round trip is stable, chain extends ----
  publishDashboard(); await settle(400);
  const pub=CAPT.filter(x=>/\.html$/.test(x.name)).pop();
  const again=pub?SRETContinue.read(await blobText(pub.href),pub.name,{appVersion:APP_VERSION}):null;
  ck('save again: the new file reads back to the same counts', again&&again.ok&&again.summary.milestones===EXP.counts.ms&&
     again.summary.entries===EXP.counts.entries&&again.summary.notes===EXP.counts.notes&&again.summary.userTasks===EXP.counts.um,
     again&&JSON.stringify(again.summary));
  ck('save again: the chain grew by one', again&&again.summary.chainLength===EXP.counts.chain+2, again&&again.summary.chainLength);

  // ---- loading over work: warns, keeps a pinned backup ----
  addRemarkEntry(Object.keys(entryMsIndex())[0],'P79 work before reload'); noteMarkup();
  await choose(file(savedText,EXP.name));
  shown.push(dlgText());
  ck('over work: the dialog warns it replaces the board', /replaces what is on the board now/.test(dlgText()), dlgText());
  $('continue-apply').click(); await settle(400);
  ck('over work: the board is the saved file again', ENTRIES.length===EXP.counts.entries&&!ENTRIES.some(e=>/P79 work before reload/.test(e.text||'')));
  try{ await Promise.race([BK.chain,settle(8000)]); }catch(e){}
  const metas=await BK_STORE.list().catch(()=>[]);
  const bc=metas.filter(m=>m.label==='Before continue');
  ck('over work: a pinned Before continue backup holds what was replaced', bc.length>=1&&bc[0].pinned, metas.map(m=>m.label).join(','));

  // ---- a load that fails part way puts the board back ----
  const before=counts(), chainBefore=PUBLISH_CHAIN.slice();
  await choose(file(savedText,EXP.name)); 
  const orig=window.applyPublishedState;
  let calls=0;
  // The incoming file fails; the rollback (the second call) runs the real path.
  window.applyPublishedState=function(){ if(calls++===0) throw new Error('P79 forced failure'); return orig.apply(this,arguments); };
  let res;
  try{ res=continueApply(); } finally{ window.applyPublishedState=orig; }
  $('continue-dialog').hidden=true; await settle(400);
  const after=counts();
  ck('failure: reported, not ok', res&&res.ok===false&&/Could not load/.test(res.message), res&&res.message);
  ck('failure: the board is as it was', JSON.stringify(after)===JSON.stringify(before)&&PUBLISH_CHAIN.length===chainBefore.length,
     JSON.stringify(after)+' vs '+JSON.stringify(before));

  ck('no em dash in anything the dialog showed', !shown.some(t=>/—/.test(t)), shown.filter(t=>/—/.test(t)).join(' | '));
}catch(e){ ck('probe B ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""


def page_with(html, probe):
    page = html.replace("<head>", "<head>" + EARLY, 1)
    i = page.rindex("</body>")
    return page[:i] + probe + "\n" + page[i:]


def run_dump(page, size):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p79.html"
        f.write_text(page, encoding="utf-8")
        p = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                            f"--user-data-dir={td}/prof", f"--window-size={size[0]},{size[1]}",
                            "--virtual-time-budget=240000", "--dump-dom", f.as_uri()],
                           capture_output=True, text=True, timeout=300)
    m = re.search(r'<pre id="p79-out">(.*?)</pre>', p.stdout, re.S)
    if not m:
        return {"checks": [{"name": "probe output found", "pass": False, "detail": p.stderr[-800:]}], "errs": [], "out": {}}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def collect(res, tag):
    out = list(res["checks"])
    errs = res.get("errs") or []
    out.append({"name": tag + ": no page errors", "pass": not errs, "detail": " | ".join(errs)[:400]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()
    html = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks = []
    ra = run_dump(page_with(html, A.replace("__TAG__", json.dumps("A save"))), (1440, 900))
    checks += collect(ra, "A save")
    out = ra.get("out") or {}
    if out.get("saved"):
        exp = json.dumps({"counts": out["counts"], "um": out["um"], "name": out["name"]})
        for size in [(1440, 900), (390, 844)]:
            tag = f"B continue {size[0]}"
            probe = B.replace("__TAG__", json.dumps(tag)).replace("__EXP__", exp).replace("__SAVED__", out["saved"])
            checks += collect(run_dump(page_with(html, probe), size), tag)
    fails = 0
    for c in checks:
        fails += not c["pass"]
        print(("PASS " if c["pass"] else "FAIL ") + c["name"] + ("" if c["pass"] or not c["detail"] else "  [" + c["detail"] + "]"))
    print(f"{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
