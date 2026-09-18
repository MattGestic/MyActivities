#!/usr/bin/env python3
"""
P34 check (TEST-36): marker anchoring, and the two header heights CSS guessed.

THE LEVEL CYCLE. P33 put a run of four on a triangle wave, so the fourth marker
sat on the middle band. Row 69 of the Aug-29 board carries four markers in
directly adjacent columns and the user asked for the fourth, SNIP-212, to reset
to the top. Capping the run length cannot do that, because msRunLevels returns
the middle band for a run of one, so the cycle itself changed to [0,1,2].

That reversal has a known cost, and it is reported rather than hidden: markers
1 and 4 of a run now share a line, here three columns apart, which is exactly
what P33's comment predicted. The band distribution is printed before and after
so the trade stays visible.

THE RUN BOUNDARY. A run continues while consecutive markers are at most two
blank columns apart. The threshold is a fixed count of schedule columns and is
deliberately NOT a rendered label width, because a label width moves with the
label scale controls and would re-anchor every marker when the text size
changed. Asserted at both bounds, per the rule dateToCol() was fixed under.

THE PAIR RULE. Two markers sharing one cell were excluded from the symmetric
pair rule and took top and middle. No row on this board reaches it, so the
assertion is against the generator and the check says so rather than claiming a
visible fix.

THE HEADER HEIGHTS. The week header row stuck at a literal 19.5px standing in
for the month row's height, which renders 16px: a 3.5px seam that data rows
scrolled through, at every width. The filter bar's open cap was a literal 160px
against 202px of wrapped content at phone width. Both are measured now, from one
ResizeObserver each, and both are asserted at three viewport widths because a
single width cannot tell a measured height from a lucky constant.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p34_check.py [--xlsx FILE] [--html FILE]
Exit code 1 on any failed check.
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

OUT_RE = re.compile(r'<pre id="p34-out">(.*?)</pre>', re.S)

# Three widths, because one cannot tell a measured height from a constant that
# happens to be right. 390 is the phone the defects were reported from.
VIEWPORTS = [(390, 844), (768, 1024), (1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p34-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  const rows=function(){ return Array.from(
    document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)')); };
  // rerender() reapplies the display settings by reading the slider ELEMENTS
  // back, so a bare setIcoSize(10) is undone by the rebuild it triggers. TD-123.
  function setDisplay(rowH,ico,wk){
    const r=document.getElementById('row-height'), i=document.getElementById('ico-size'),
          w=document.getElementById('wk-width');
    if(r) r.value=rowH; if(i) i.value=ico; if(w) w.value=wk;
    setRowHeight(rowH); setIcoSize(ico); setWkWidth(wk);
    onSizeSliderRelease();
  }
  // The offset the week band must sit at is the month ROW's height, not one of
  // its cells: the metadata cells carry padding:0 and the month cells 3px.
  function seam(){
    const ph=document.getElementById('phase-hdr'), wh=document.getElementById('week-hdr');
    if(!ph||!wh) return null;
    const wth=wh.querySelector('th:not(.sticky)')||wh.querySelector('th');
    const rowH=ph.getBoundingClientRect().height;
    const top=parseFloat(getComputedStyle(wth).top);
    return {rowH:Math.round(rowH*100)/100, stickyTop:Math.round(top*100)/100,
            seam:Math.round((rowH-top)*100)/100};
  }
  function markerCols(tr){
    const out=[];
    tr.querySelectorAll('.m-wrap:not(.m-ghost)').forEach(function(w){
      const td=w.closest('td.c-wk'); if(!td) return;
      out.push({col:+td.getAttribute('data-col'),
                mdy:parseFloat(w.style.getPropertyValue('--mdy'))||0,
                tip:w.getAttribute('data-tip')||''});
    });
    out.sort(function(a,b){ return a.col-b.col; });
    return out;
  }

  try{
    window.XLSX={
      read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
      utils:{ sheet_to_json:function(s){ return s.__aoa; } }
    };
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st); void document.body.offsetWidth;

    // ================= 1. The header heights =================
    // Taken BEFORE the import, so the month band is the static one, and again
    // after, so a rebuilt month band is covered too.
    R.notes.seamEmpty=seam();

    PENDING_IMPORT_FILE='SNIP_29Aug26_export.xlsx';
    showMapper(Parse.workbook(new Uint8Array([0])));
    const dd=document.getElementById('cfg-datadate'); if(dd) dd.value='2026-08-29';
    await settle();
    runIngest();
    await settle(); await settle();

    R.notes.board={rows:document.querySelectorAll('#tbody tr.data').length,
                   markers:document.querySelectorAll('.m-wrap:not(.m-ghost)').length,
                   viewport:window.innerWidth+'x'+window.innerHeight};
    ck('setup: a board was built to measure',
       R.notes.board.rows>100&&R.notes.board.markers>100, JSON.stringify(R.notes.board));

    const seams=[{at:'after import',v:seam()}];
    setDisplay(56,20,48); await settle();
    seams.push({at:'row 56 / ico 20 / wk 48',v:seam()});
    setDisplay(28,10,20); await settle();
    seams.push({at:'row 28 / ico 10 / wk 20',v:seam()});
    setDisplay(34,15,36); await settle();
    togglePrintMode(); await settle();
    seams.push({at:'print mode',v:seam()});
    togglePrintMode(); await settle();
    fitToScreen(); await settle();
    seams.push({at:'fit to screen',v:seam()});
    setDisplay(34,15,36); await settle();
    seams.push({at:'back to default',v:seam()});
    R.notes.seams=seams;

    const bad=seams.filter(function(s){ return !s.v||Math.abs(s.v.seam)>0.5; });
    ck('header: the week band sticks exactly at the month row’s measured height',
       seams.length===6&&bad.length===0,
       seams.length+' states, off: '+(bad.map(function(s){
         return s.at+' '+(s.v?s.v.seam:'null'); }).join(', ')||'none'));
    ck('header: and the measured height is not the old 19.5px literal',
       seams[0].v&&Math.abs(seams[0].v.stickyTop-19.5)>0.5,
       'sticky top '+(seams[0].v?seams[0].v.stickyTop:'null'));
    ck('header: --hdr-phase-h is actually written, not left on its fallback',
       (document.documentElement.style.getPropertyValue('--hdr-phase-h')||'').length>0,
       JSON.stringify(document.documentElement.style.getPropertyValue('--hdr-phase-h')));

    // ================= 2. The filter bar =================
    const bar=document.getElementById('top-filter-bar');
    function barState(tag){
      return {at:tag, open:bar.classList.contains('open'),
              scrollH:bar.scrollHeight, clientH:bar.clientHeight,
              maxH:getComputedStyle(bar).maxHeight};
    }
    const barStates=[];
    toggleTopFilterBar(true); await settle(); await settle();
    barStates.push(barState('open'));
    toggleTopFilterBar(false); await settle();
    barStates.push(barState('closed'));
    toggleTopFilterBar(true); await settle(); await settle();
    barStates.push(barState('reopened'));
    R.notes.filterBar=barStates;
    const clipped=barStates.filter(function(b){
      return b.open && b.scrollH>b.clientH+0.5; });
    ck('filter bar: nothing is clipped while it is open, at this width',
       barStates.length===3&&clipped.length===0,
       barStates.length+' states, clipped: '+(clipped.map(function(b){
         return b.at+' '+b.scrollH+' in '+b.clientH; }).join(', ')||'none'));
    ck('filter bar: and it still collapses to nothing when closed',
       barStates[1].clientH===0, 'closed clientH '+barStates[1].clientH);
    ck('filter bar: the cap is measured, not the old 160px literal',
       barStates[0].maxH!=='160px', barStates[0].maxH);

    // ================= 3. The sequence, against the generator =================
    // Columns one apart, so every marker is in its own cell, which is the case
    // the sequence rule describes. The same-cell case is section 5.
    const colsOf=function(n){ const a=[]; for(let k=0;k<n;k++) a.push(k); return a; };
    const seq={}; for(let n=1;n<=8;n++) seq[n]=msRunLevels(colsOf(n),3);
    R.notes.sequence=seq;
    ck('sequence: a run of one is the middle band',
       seq[1].join(',')==='1', JSON.stringify(seq[1]));
    ck('sequence: a run of two is top then bottom, leftmost up',
       seq[2].join(',')==='0,2', JSON.stringify(seq[2]));
    ck('sequence: a run of three cascades top, middle, bottom',
       seq[3].join(',')==='0,1,2', JSON.stringify(seq[3]));
    // The P34 reversal. P33 asserted the opposite here, deliberately.
    ck('sequence: the fourth marker RESETS to the top band',
       seq[4][3]===0, 'got level '+seq[4][3]+' in '+JSON.stringify(seq[4]));
    ck('sequence: the fifth is the middle band and the sixth the bottom',
       seq[6][4]===1&&seq[6][5]===2, JSON.stringify(seq[6]));
    let adjacentSame=[];
    for(let n=2;n<=8;n++) for(let k=1;k<seq[n].length;k++)
      if(seq[n][k]===seq[n][k-1]) adjacentSame.push('n='+n+' at '+k);
    ck('sequence: no two ADJACENT markers in a run share a band, for n up to 8',
       Object.keys(seq).length===8&&adjacentSame.length===0,
       Object.keys(seq).length+' run lengths, clashes: '+(adjacentSame.join(', ')||'none'));

    // ================= 4. The run boundary, both bounds =================
    ck('boundary: the threshold is two blank columns, i.e. a gap of three',
       MS_PROXIMITY_COLS===3, 'MS_PROXIMITY_COLS '+MS_PROXIMITY_COLS);
    // The rendered consequence, which is what the constant is for. A marker
    // further than the threshold from BOTH neighbours is a run of one and must
    // sit dead centre; a marker exactly at the threshold is in a run and must
    // not. Both directions, and both sample sizes.
    let isolated=0, isolatedOff=0, atBound=0, atBoundCentred=0;
    rows().forEach(function(tr){
      const ms=markerCols(tr);
      for(let k=0;k<ms.length;k++){
        const prev=k>0?ms[k].col-ms[k-1].col:1e9;
        const next=k<ms.length-1?ms[k+1].col-ms[k].col:1e9;
        const near=Math.min(prev,next);
        if(near>MS_PROXIMITY_COLS){ isolated++; if(Math.abs(ms[k].mdy)>0.5) isolatedOff++; }
        else if(near===MS_PROXIMITY_COLS){ atBound++; }
      }
      // A run whose members are all centred would mean the boundary broke it.
      let i=0;
      while(i<ms.length){
        let j=i+1;
        while(j<ms.length && (ms[j].col-ms[j-1].col)<=MS_PROXIMITY_COLS) j++;
        if(j-i>1){
          const gaps=[]; for(let k=i+1;k<j;k++) gaps.push(ms[k].col-ms[k-1].col);
          if(gaps.indexOf(MS_PROXIMITY_COLS)>=0){
            const centred=ms.slice(i,j).filter(function(m){ return Math.abs(m.mdy)<=0.5; });
            if(centred.length===j-i) atBoundCentred++;
          }
        }
        i=j;
      }
    });
    R.notes.boundary={isolated:isolated,isolatedOffCentre:isolatedOff,
                      atThreshold:atBound,runsAtThresholdAllCentred:atBoundCentred};
    ck('boundary, outer bound: a marker beyond the threshold sits dead centre',
       isolated>0&&isolatedOff===0, isolated+' isolated markers, '+isolatedOff+' off centre');
    ck('boundary, inner bound: a gap exactly at the threshold still joins a run',
       atBound>0&&atBoundCentred===0,
       atBound+' markers at the threshold, '+atBoundCentred+' runs wrongly broken');

    // ================= 5. The pair rule =================
    const pair={'diff cols, L=3':msRunLevels([0,1],3), 'same cell, L=3':msRunLevels([5,5],3),
                'diff cols, L=5':msRunLevels([0,1],5), 'same cell, L=5':msRunLevels([5,5],5)};
    R.notes.pair=pair;
    const asym=Object.keys(pair).filter(function(k){
      const p=pair[k], L=k.indexOf('L=5')>=0?5:3, mid=(L-1)/2;
      return p.length!==2 || Math.abs((p[0]-mid)+(p[1]-mid))>1e-9 || !(p[0]<p[1]);
    });
    ck('pair: two markers are symmetric about the midpoint, leftmost up',
       Object.keys(pair).length===4&&asym.length===0,
       '4 cases, asymmetric: '+(asym.join(', ')||'none'));
    ck('pair: the same-cell case is no longer excluded from that rule',
       pair['same cell, L=3'].join(',')===pair['diff cols, L=3'].join(','),
       'same '+JSON.stringify(pair['same cell, L=3'])+' vs diff '+JSON.stringify(pair['diff cols, L=3']));

    // ================= 6. SNIP-212, the case this partial exists for =========
    let target=null;
    rows().forEach(function(tr){
      const src=(tr.querySelector('td.c-src')||{}).textContent||'';
      if(src.indexOf('SNIP-212')>=0) target=tr;
    });
    if(target){
      const ms=markerCols(target);
      const me=ms.filter(function(m){ return m.tip.indexOf('SNIP-212')>=0; })[0];
      R.notes.snip212={cols:ms.map(function(m){return m.col;}),
                       mdy:ms.map(function(m){return m.mdy;}),
                       snip212mdy:me?me.mdy:null};
      ck('SNIP-212: its row still carries four markers in adjacent columns',
         ms.length===4&&(ms[3].col-ms[0].col)===3, JSON.stringify(R.notes.snip212.cols));
      ck('SNIP-212: and it now sits on the TOP band, not the middle',
         !!me&&me.mdy<-0.5, 'mdy '+(me?me.mdy:'not found'));
    }else{
      ck('SNIP-212: its row was found on the board', false, 'no row matched SNIP-212');
    }

    // ================= 7. Board effect, reported not predicted ==============
    const dist={}, runLen={};
    rows().forEach(function(tr){
      const ms=markerCols(tr);
      if(!ms.length) return;
      let i=0;
      while(i<ms.length){
        let j=i+1;
        while(j<ms.length && (ms[j].col-ms[j-1].col)<=MS_PROXIMITY_COLS) j++;
        runLen[j-i]=(runLen[j-i]||0)+1; i=j;
      }
      ms.forEach(function(m){
        const k=m.mdy<-0.5?'top':(m.mdy>0.5?'bottom':'middle');
        dist[k]=(dist[k]||0)+1;
      });
    });
    R.notes.runLengths=runLen;
    R.notes.bandDistribution=dist;
    const total=Object.keys(dist).reduce(function(a,k){ return a+dist[k]; },0);
    ck('board: every marker landed on one of the three bands',
       total===R.notes.board.markers, total+' banded of '+R.notes.board.markers);

    // ================= 8. Nothing else moved =================
    let markers=0, out=0, worst=-1e9;
    rows().forEach(function(tr){
      const rr=tr.getBoundingClientRect();
      if(rr.height===0) return;
      tr.querySelectorAll('.m-wrap:not(.m-ghost)').forEach(function(w){
        const wr=w.getBoundingClientRect();
        if(!(wr.width||wr.height)) return;
        markers++;
        const ov=Math.max(rr.top-wr.top,wr.bottom-rr.bottom);
        if(ov>0.5) out++;
        if(ov>worst) worst=ov;
      });
    });
    R.notes.containment={markers:markers,out:out,worst:Math.round(worst*10)/10};
    ck('containment: no marker leaves its own row',
       markers>100&&out===0, markers+' markers, '+out+' out, worst '+R.notes.containment.worst);

    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=String(e&&e.stack); }
  emit();
})();
"""


def run(html_path, aoa, width, height):
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", inject + "</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p34.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=90000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=str(root / "data" / "schedules" /
                                          "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"))
    ap.add_argument("--html", default=str(root / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    html = pathlib.Path(a.html)

    # Source-level assertions. The literals these replace cannot be caught by
    # measuring, because a literal that happens to be right measures as correct.
    src = html.read_text(encoding="utf-8", errors="replace")
    static = []
    # The NAME survives in the comment that records why the token went. What
    # must not survive is a declaration or a reader, so those are what is tested.
    dead = src.count("--hdr-search-h:") + src.count("var(--hdr-search-h")
    static.append(("source: the --hdr-search-h token has no declaration and no reader",
                   dead == 0, str(dead) + " live uses remain"))
    static.append(("source: the dead tr.hdr-search rule is gone",
                   "tr.hdr-search" not in src, "still present"))
    static.append(("source: no header row sticks at a hardcoded offset",
                   "top:calc(var(--hdr-search-h)" not in src and "top:19.5px" not in src,
                   "calc offset or bare literal still present"))
    static.append(("source: the week band's offset reads the measured property",
                   "top:var(--hdr-phase-h" in src, "not found"))
    static.append(("source: the filter bar's open cap reads the measured property",
                   "max-height:var(--tfb-h" in src, "not found"))
    static.append(("source: the level cycle is the plain repeat",
                   "const MS_LEVEL_CYCLE=[0,1,2];" in src, "not found"))
    vers = len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src))
    static.append(("source: exactly one version literal", vers == 1, str(vers) + " found"))

    checks, fails = [], 0
    for name, ok, detail in static:
        checks.append((name, ok, detail if not ok else ""))

    for (w, h) in VIEWPORTS:
        R = run(html, aoa, w, h)
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("board", "boundary", "snip212", "runLengths", "bandDistribution",
                  "containment", "pair"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")
        if "seams" in n:
            for s in n["seams"]:
                v = s["v"] or {}
                print("   seam %-26s row %-6s sticky %-6s gap %s"
                      % (s["at"], v.get("rowH"), v.get("stickyTop"), v.get("seam")))
        if "filterBar" in n:
            for b in n["filterBar"]:
                print("   bar  %-10s content %4d  box %4d  cap %s"
                      % (b["at"], b["scrollH"], b["clientH"], b["maxH"]))
        if "sequence" in n:
            print("   run levels (0 top, 1 middle, 2 bottom):")
            for k in sorted(n["sequence"], key=int):
                print(f"     n={k}  {n['sequence'][k]}")
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
