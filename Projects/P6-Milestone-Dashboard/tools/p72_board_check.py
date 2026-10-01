#!/usr/bin/env python3
"""
p72_board_check (P72, Matt 2026-10-01):
  - the embedded baseline carries no P6 WBS summary rows: every milestone has
    an Activity ID, no task row is a WBS node, the three activity rows that
    had WBS milestones attached keep only their real IDs;
  - the board's edited mark (*) sits at the same place on every marker: just
    outside the ICON's top-left corner, whether or not the marker shows a
    label (N=3, one of them in a cluster);
  - the update history reads with real spaces: "Label value", "from -> to",
    the date apart from the follow-up pill, which sits at the right edge with
    the pencil after it.
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
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p72b-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900), (390, 844)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p72b-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,260));
  const $=id=>document.getElementById(id);
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const WBS=["3D Model", "Bronson Connector Road Design  Review Memo", "Capital and Operating Cost Estimate", "Civil", "Concrete MTO", "Design Criteria", "Electrical & Instrumentation", "Electrical Update", "Engineering", "Equipment List", "Equipment Sizing", "Eskay  Load List", "Eskay Creek PFS - Current", "Eskay HV SLD", "Financial Model", "Foundation(NPI & Portals )", "Generator Sizing Report", "Inputs From Others", "Key Milestones", "Layout", "MEL", "MTO", "Mass  and Water Balance", "Mechanical & Piping", "Metallurgical Testwork Review", "NPI Facility Detailed Layout", "On-Site Waste Dump", "Overall Site Plan", "PFD", "PFS", "PFS Baseline Schedule", "Process", "Project Execution Plan / Schedule", "Project Management", "SNIP Water Management", "Site Services", "Snip Building List", "Snip HV SLD", "Snip Load List", "Structural & Concrete", "Structural Design Criteria", "Technical Report"];
  try{
    const st=document.createElement('style'); st.textContent='*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
    await settle(); await settle();
    // ===== 1. Baseline has no WBS summaries =====
    const noId=MILESTONES.filter(m=>!extractActivityId(m.notes));
    ck('baseline: every milestone has an Activity ID', noId.length===0, noId.map(m=>m.id).join('|'));
    const wbsMs=MILESTONES.filter(m=>WBS.indexOf(String(m.id))>=0);
    ck('baseline: no milestone is a P6 WBS node', wbsMs.length===0, wbsMs.map(m=>m.id).join('|'));
    const wbsRows=TASKS.filter(t=>WBS.indexOf(String(t.ref))>=0||t.ref===t.name);
    ck('baseline: no row is a WBS node', wbsRows.length===0, wbsRows.map(t=>t.ref).join('|'));
    const mixed=['SNIP-133','SNIP-155','SNIP-242'].map(r=>TASKS.find(t=>t.ref===r));
    ck('baseline: the three activity rows keep only real IDs in their source list',
       mixed.every(t=>t&&String(t.src).split(',').every(x=>WBS.indexOf(x.trim())<0)), mixed.map(t=>t&&t.src).join(' / '));
    ck('baseline: every row still has at least one milestone',
       TASKS.every(t=>MILESTONES.some(m=>m.ref===t.ref)), '');
    ck('baseline: counts', TASKS.length===120&&MILESTONES.length===151, TASKS.length+'/'+MILESTONES.length);
    // ===== 2. Edited mark placement =====
    const all=MILESTONES.filter(m=>wrapOf(msId(m)));
    // one labelled marker, one in a multi-marker cell, one more
    const inCluster=all.find(m=>{ const w=wrapOf(msId(m)); return w&&w.parentElement&&w.parentElement.querySelectorAll('.m-wrap').length>1; });
    const picks=[all[0],inCluster,all[Math.floor(all.length/2)]].filter(Boolean).filter((m,i,a)=>a.indexOf(m)===i);
    picks.forEach(function(m){ const d=new Date(m.date+'T00:00:00'); d.setDate(d.getDate()+1); addFieldEntry(msKeyFor(m),'date',d.toISOString().slice(0,10)); });
    projectEntryStores(); scheduleRerender(true); await settle(); await settle();
    const offs=[];
    picks.forEach(function(m){
      const w=wrapOf(msId(m)); const mk=w&&w.querySelector('.m-board-edit-mark'); const ic=w&&w.querySelector('svg');
      if(!mk||!ic){ ck('mark: present on '+msId(m), false, ''); return; }
      const a=mk.getBoundingClientRect(), b=ic.getBoundingClientRect();
      offs.push([Math.round(b.left-a.left),Math.round(b.top-a.top)]);
      ck('mark: '+msId(m)+' sits at the icon\'s top-left, outside it',
         a.right<=b.left+4&&a.bottom<=b.top+8&&a.left<b.left&&a.top<b.top,
         'mark '+[a.left,a.top,a.right,a.bottom].map(Math.round)+' icon '+[b.left,b.top].map(Math.round));
    });
    ck('mark: one placement on every marker (N='+offs.length+')', offs.length>=3&&offs.every(o=>Math.abs(o[0]-offs[0][0])<=1&&Math.abs(o[1]-offs[0][1])<=1), JSON.stringify(offs));
    ck('mark: N=3 includes a marker sharing its cell', !!inCluster&&picks.indexOf(inCluster)>=0, inCluster&&msId(inCluster));
    // ===== 3. History spacing =====
    const H=picks[0]; const w=wrapOf(msId(H)); w.click(); await settle();
    $('ms-comment-text').value='Spacing probe'; onMsCommentInput(); onMsSaveClick(false); await settle();
    const ent=$('ms-history').querySelector('.nh-entry');
    const rows=[...$('ms-history').querySelectorAll('.nh-row')].map(r=>r.textContent);
    const delta=rows.find(t=>/→/.test(t));
    ck('history: a change reads "Label from → to" with spaces', delta&&/^\S.*\S \S.* → \S/.test(delta), JSON.stringify(rows));
    const com=rows.find(t=>/Spacing probe/.test(t));
    ck('history: a comment reads "Label text" with a space', com&&/ Spacing probe$/.test(com), com);
    const head=ent.querySelector('.nh-head');
    ck('history: the date and the follow-up pill are separated by a space', / /.test(head.textContent.replace(/^[^ ]+ [^ ]+/,'')) , head.textContent);
    const hR=head.getBoundingClientRect(), right=head.querySelector('.nh-right').getBoundingClientRect();
    ck('history: the pill and pencil are anchored to the right edge', Math.abs(right.right-hR.right)<=2, Math.round(right.right)+' vs '+Math.round(hR.right));
    const pen=head.querySelector('.nh-edit'), pill=head.querySelector('.nh-fu');
    ck('history: the pencil sits right of the pill', pen&&pen.getBoundingClientRect().left>=pill.getBoundingClientRect().right, '');
    discardMsDialog(); await settle();
    emit();
  }catch(err){ R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.message||err)}); R.err=String(err&&err.stack||err); emit(); }
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p72b.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html)
    src = html.read_text(encoding="utf-8", errors="replace")

    checks = []
    block = src[src.index('<div id="ms-dialog"'):src.index('<div id="print-filter-note"')]
    checks.append(("source: no em dash in the card markup", "—" not in block and "&mdash;" not in block, ""))
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal",
                   len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))

    gv = src.find("/* ============================================================\n   GRID VIEW (D-09")
    nh = src.find(".nh-head{")
    checks.append(("source: the history CSS sits above the GRID VIEW banner (grid_view_embed.py rewrites from the banner to </style>; the P70 re-paste dropped it)",
                   0 < nh < gv, f"nh-head at {nh}, grid banner at {gv}"))
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        print(f"\n=== {w}x{h} ===  sample {R.get('notes', {}).get('sample')}")
        if R.get("err"):
            print(R["err"])
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

    fails = 0
    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
