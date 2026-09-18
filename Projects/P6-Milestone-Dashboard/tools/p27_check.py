#!/usr/bin/env python3
"""
P27 check (TEST-30): dependency-count chips, the baseline overlay, and the
A3 print preview.

Four questions, each asked of the rendered page rather than of the source:

  1. Do the dependency counts land somewhere a reader can actually see them?
     They were always in the DOM; the defect was that they sat on the row
     boundary below the icon, unbacked at 8px, with the label stack over the
     right-hand one. So this measures POSITION and OVERLAP, not existence.

  2. Does the baseline overlay place each ghost on its pair's own Y, in its
     own baseline date's column, behind the live marker?

  3. Does the print preview hold the board at A3 portrait's printable width?

  4. Does leaving the preview put the board back the way it was found?

Needs a real import for (2): the overlay only runs in the Update view, and
the whole point is the ID match between the imported schedule and the
embedded baseline. Reuses tools/import_check.py for the workbook-to-AoA
conversion and the SheetJS stub.

Usage:
  python3 tools/p27_check.py [--xlsx FILE] [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p27-out">(.*?)</pre>', re.S)

PROBE = r"""
(async function(){
  const R={checks:[]};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p27-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  // scheduleRerender() debounces on a 40ms setTimeout. Timers DO fire under
  // --virtual-time-budget, but only if the probe yields to them; reading
  // straight after a toggle measured the page before the rebuild and reported
  // zero ghosts for a feature that works.
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  // Transitions do not advance under --virtual-time-budget, so anything read
  // back from an animated property would be the START value. Kill them first.
  function freeze(){
    const s=document.createElement('style');
    s.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(s);
    void document.body.offsetWidth;
  }
  function rect(el){ const r=el.getBoundingClientRect(); return {l:r.left,r:r.right,t:r.top,b:r.bottom,w:r.width,h:r.height,cx:(r.left+r.right)/2,cy:(r.top+r.bottom)/2}; }
  function overlaps(a,b){ return a.l<b.r&&b.l<a.r&&a.t<b.b&&b.t<a.b; }

  try{
    freeze();
    const ROWS_AT_START=document.querySelectorAll('tr[data-type="row"]').length;
    R.rowsAtStart=ROWS_AT_START;

    // ---------- 1. Dependency count chips ----------
    const cb=document.getElementById('toggle-counts');
    cb.checked=true; cb.dispatchEvent(new Event('change'));
    // The toggle goes through scheduleRerender(), which debounces 40ms. Read
    // synchronously, every chip assertion below passed against an empty set.
    await settle();
    freeze();
    ck('counts: body carries the counts-on class',
       document.body.classList.contains('counts-on'));
    const chips=Array.from(document.querySelectorAll('.ms-count'));
    ck('counts: chips are rendered', chips.length>0, chips.length+' chips');
    // Every measurement below is over `chips`. With an empty set they all pass
    // for the wrong reason, so the sample size is asserted, not assumed.
    ck('counts: the chip measurements had a sample to measure', chips.length>=50, chips.length+' sampled');
    // A rebuild must REPLACE the board, not append a second copy of it.
    ck('counts: the toggle did not duplicate the board',
       document.querySelectorAll('tr[data-type=\"row\"]').length===ROWS_AT_START,
       ROWS_AT_START+' rows before, '+document.querySelectorAll('tr[data-type=\"row\"]').length+' after');

    // Each chip must be level with its own icon (the defect put them a row
    // boundary below it) and clear of that icon's label stack.
    let offCentre=0, coveredByLabel=0, tooSmall=0, unbacked=0, sampled=0;
    chips.forEach(function(c){
      const wrap=c.closest('.m-wrap'); if(!wrap) return;
      const icon=wrap.querySelector('.ms-icon'); if(!icon) return;
      sampled++;
      const rc=rect(c), ri=rect(icon);
      // Level with the icon: centres within 2px vertically.
      if(Math.abs(rc.cy-ri.cy)>2) offCentre++;
      // Big enough to read: the old chips measured 4.5 x 8.
      if(rc.w<10||rc.h<9) tooSmall++;
      const bg=getComputedStyle(c).backgroundColor;
      if(bg==='rgba(0, 0, 0, 0)'||bg==='transparent') unbacked++;
      const stack=wrap.querySelector('.m-lbl-stack');
      if(stack){
        const rs=rect(stack);
        if(rs.w>0&&rs.h>0&&overlaps(rc,rs)) coveredByLabel++;
      }
    });
    R.chipSampled=sampled;
    ck('counts: every chip sits level with its own icon', offCentre===0, offCentre+' off by >2px');
    ck('counts: every chip is at least 10x9 (was 4.5x8)', tooSmall===0, tooSmall+' too small');
    ck('counts: every chip has a backing', unbacked===0, unbacked+' unbacked');
    ck('counts: no chip is under its own label stack', coveredByLabel===0, coveredByLabel+' covered');
    // And the chip has to say the right number.
    let wrongNum=0, numChecked=0;
    chips.forEach(function(c){
      const wrap=c.closest('.m-wrap'); const id=wrap&&wrap.getAttribute('data-ms');
      if(!id||!DEP_DATA[id]) return;
      numChecked++;
      const want=parseIds(c.classList.contains('pred')?DEP_DATA[id].pred:DEP_DATA[id].succ).length;
      if(String(want)!==c.textContent) wrongNum++;
    });
    ck('counts: chip value matches DEP_DATA', wrongNum===0&&numChecked>0, numChecked+' checked, '+wrongNum+' wrong');
    // Toggling back off must remove both the chips and the class.
    cb.checked=false; cb.dispatchEvent(new Event('change'));
    await settle();
    R.chipsAfterOff=document.querySelectorAll('.ms-count').length;
    R.classAfterOff=document.body.classList.contains('counts-on');
    ck('counts: toggling off clears the chips and the class',
       R.chipsAfterOff===0&&!R.classAfterOff,
       R.chipsAfterOff+' chips left, class='+R.classAfterOff);

    // ---------- 2. Baseline overlay ----------
    window.XLSX={
      read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
      utils:{ sheet_to_json:function(s){ return s.__aoa; } }
    };
    PENDING_IMPORT_FILE='reference.xlsx';
    showMapper(Parse.workbook(new Uint8Array([0])));
    const dd=document.getElementById('cfg-datadate'); if(dd) dd.value='2026-08-29';
    DIAG=[]; runIngest();
    setViewMode('update');
    await settle();
    const gb=document.getElementById('btn-baseline-ms');
    ck('baseline: the toggle is enabled once an update is loaded', !gb.disabled);
    gb.checked=true; gb.dispatchEvent(new Event('change'));
    await settle();
    freeze();

    const ghosts=Array.from(document.querySelectorAll('.m-ghost'));
    R.ghostCount=ghosts.length;
    ck('baseline: ghosts are drawn', ghosts.length>0, ghosts.length+' ghosts');

    // Build the ID -> baseline date map the same way the app does, so the
    // ghost's COLUMN can be checked against the baseline date rather than
    // against whatever column it happens to be in.
    // The ghost names its own pair via data-ghost-for. Inferring the pair from
    // position instead reported three false failures: two markers in one row
    // can share a baseline column, and the guess picked the other one.
    const blIdx=getBaselineIdIndex();
    const pairOf=new Map();
    R.yOutliers=[];
    let wrongCol=0, wrongY=0, notBehind=0, notGrey=0, pairsChecked=0, noPair=0, wrongBlCol=0;
    ghosts.forEach(function(g){
      const td=g.closest('td.c-wk'); if(!td) return;
      const tr=g.closest('tr');
      const col=parseInt(td.getAttribute('data-col'),10);
      const key=g.getAttribute('data-ghost-for');
      const pair=key?tr.querySelector('.m-wrap:not(.m-ghost)[data-ms-key="'+CSS.escape(key).replace(/\\/g,'\\')+'"]'):null;
      if(!pair){ noPair++; return; }
      pairOf.set(g,pair);
      pairsChecked++;
      const rg=rect(g), rp=rect(pair);
      // Y: the ghost sits on its pair's own line.
      if(Math.abs(rg.cy-rp.cy)>1.5){
        wrongY++;
        if(R.yOutliers.length<6) R.yOutliers.push({key:key,
          dy:Math.round((rg.cy-rp.cy)*10)/10,
          ghostMy:g.style.getPropertyValue('--my'), pairMy:pair.style.getPropertyValue('--my')});
      }
      // X: the ghost's column is the column its own BASELINE date maps to.
      const id=pair.getAttribute('data-ms');
      const bl=blIdx[id]||[];
      let colIsABaselineDate=false;
      for(let i=0;i<bl.length;i++){ if(dateToCol(bl[i].date)===col) colIsABaselineDate=true; }
      if(!colIsABaselineDate) wrongBlCol++;
      const rt=td.getBoundingClientRect();
      if(rg.cx<rt.left-1||rg.cx>rt.right+1) wrongCol++;
      // Behind: a lower z-index than the live marker.
      const zg=parseInt(getComputedStyle(g).zIndex,10);
      const zp=parseInt(getComputedStyle(pair).zIndex,10);
      if(!(zg<zp)) notBehind++;
      // Greyed, by the baseline convention in the legend.
      const ic=g.querySelector('.ms-icon');
      if(!ic||!ic.classList.contains('baseline')||!ic.classList.contains('s-baseline')) notGrey++;
    });
    ck('baseline: ghost column is its own baseline date\u2019s column',
       wrongBlCol===0, wrongBlCol+' in the wrong week');
    R.ghostPairs=pairsChecked; R.ghostNoPair=noPair;
    ck('baseline: every ghost was matched back to a live marker by Activity ID',
       pairsChecked>0&&noPair===0, pairsChecked+' paired, '+noPair+' unpaired');
    ck('baseline: ghost Y equals its pair’s Y', wrongY===0, wrongY+' off by >1.5px');
    ck('baseline: ghost X sits in its own baseline date’s column', wrongCol===0, wrongCol+' outside');
    ck('baseline: ghost paints behind its live marker', notBehind===0, notBehind+' not behind');
    ck('baseline: ghost uses the greyed baseline icon', notGrey===0, notGrey+' not greyed');
    // A ghost whose baseline has NOT moved must not hide under the live icon.
    const same=ghosts.filter(function(g){ return g.classList.contains('m-ghost-same-col'); });
    R.ghostSameCol=same.length;
    // Compared against its OWN pair, not against whatever marker happens to be
    // first in the cell: the rule is that a ghost never hides under the marker
    // it is the baseline for.
    let hidden=0, hiddenAny=0;
    R.hiddenSamples=[];
    same.forEach(function(g){
      const pair=pairOf.get(g); if(!pair) return;
      const rg=rect(g);
      if(Math.abs(rg.cx-rect(pair).cx)<3){
        hidden++;
        if(R.hiddenSamples.length<6) R.hiddenSamples.push({id:pair.getAttribute('data-ms'),
          dx:Math.round((rg.cx-rect(pair).cx)*10)/10});
      }
      const td=g.closest('td.c-wk');
      const near=Array.from(td.querySelectorAll('.m-wrap:not(.m-ghost)')).some(function(o){
        return Math.abs(rg.cx-rect(o).cx)<3&&Math.abs(rg.cy-rect(o).cy)<3;
      });
      if(near) hiddenAny++;
    });
    R.ghostHiddenUnderAny=hiddenAny;
    ck('baseline: an unmoved ghost is offset clear of its own live icon', hidden===0,
       same.length+' same-column, '+hidden+' hidden');
    // The tooltip must name the real baseline, not a literal date.
    const tip=ghosts.length?ghosts[0].getAttribute('data-tip'):'';
    R.ghostTip=tip;
    ck('baseline: tooltip names the live baseline label',
       tip.indexOf(BASELINE_LABEL_TEXT)===0&&tip.indexOf('29-Jul-26')<0);

    // ---------- 3 & 4. A3 print preview ----------
    const wkBefore=document.getElementById('wk-width').value;
    toggleFilterBar(true);   // open the view-controls panel, to prove it closes
    togglePrintMode(true);
    await settle();
    freeze();
    ck('print: body enters print-mode', document.body.classList.contains('print-mode'));
    ck('print: the view-controls panel was closed', !document.body.classList.contains('cv-open'));
    const ps=document.getElementById('print-page-style');
    ck('print: an @page rule is injected for A3 portrait',
       !!ps&&/size:297mm 420mm/.test(ps.textContent)&&/margin:8mm/.test(ps.textContent),
       ps?ps.textContent:'(no style element)');
    const frame=document.getElementById('page-frame');
    const fw=frame.getBoundingClientRect().width;
    // The frame is one A3 sheet across, border-box, so its outer width is 297mm.
    const mm=(function(){ const p=document.createElement('div');
      p.style.cssText='position:absolute;visibility:hidden;width:100mm;height:0';
      document.body.appendChild(p); const v=p.getBoundingClientRect().width/100; p.remove(); return v; })();
    R.frameW=Math.round(fw); R.mmPx=Math.round(mm*1000)/1000; R.expectFrameW=Math.round(297*mm);
    R.printNonWk=(function(){ const row=document.querySelector('tr.data'); if(!row) return -1;
      return Math.round(Array.from(row.cells).filter(function(td){
        return !td.classList.contains('col-wk')&&td.offsetParent!==null&&getComputedStyle(td).display!=='none';
      }).reduce(function(s,td){ return s+td.getBoundingClientRect().width; },0)); })();
    R.printWkCols=(function(){ const row=document.querySelector('tr.data'); if(!row) return -1;
      return Array.from(row.querySelectorAll('td.col-wk')).filter(function(td){
        return td.offsetParent!==null&&getComputedStyle(td).display!=='none'; }).length; })();
    ck('print: the page frame is one A3 sheet wide',
       Math.abs(fw-297*mm)<2, Math.round(fw)+'px vs '+Math.round(297*mm)+'px');
    ck('print: the preview banner is shown',
       getComputedStyle(document.getElementById('pm-banner')).display!=='none');
    const wkIn=parseInt(document.getElementById('wk-width').value,10);
    ck('print: week columns were refitted', wkIn!==parseInt(wkBefore,10)||wkIn===20,
       wkBefore+'px -> '+wkIn+'px');
    // The board must not be wider than the printable area unless the fit hit
    // its 20px floor, in which case the banner has to say so.
    const tbl=document.getElementById('main-table').getBoundingClientRect().width;
    const printable=281*mm;
    const detail=document.getElementById('pm-banner-detail').textContent;
    R.tableW=Math.round(tbl); R.printableW=Math.round(printable); R.banner=detail;
    ck('print: the board fits the page, or the banner says it cannot',
       tbl<=printable+2||/exceed the page width/.test(detail),
       Math.round(tbl)+'px board vs '+Math.round(printable)+'px printable');

    togglePrintMode(false);
    await settle();
    freeze();
    ck('print: leaving clears print-mode', !document.body.classList.contains('print-mode'));
    ck('print: leaving clears the @page rule',
       document.getElementById('print-page-style').textContent==='');
    ck('print: leaving restores the week width',
       document.getElementById('wk-width').value===wkBefore,
       wkBefore+' -> '+document.getElementById('wk-width').value);
    ck('print: leaving reopens the view-controls panel it closed',
       document.body.classList.contains('cv-open'));
    ck('print: the page frame is display:contents again',
       getComputedStyle(document.getElementById('page-frame')).display==='contents');

    R.ok=true;
  }catch(e){ R.err=String(e&&e.message); R.stack=String(e&&e.stack||'').slice(0,900); }
  emit();
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default="data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--html", default="src/milestone-dashboard.html")
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    html = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html.replace("</body>", inject + "</body>")
    if page == html:
        sys.exit("Could not find </body> to inject into.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p27.html"
        tmp.write_text(page, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--window-size=1600,1200", "--virtual-time-budget=40000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=420,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit("Probe output not found.\n" + proc.stderr[-3000:])
    R = json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))

    if not R.get("ok"):
        print("PROBE FAILED: " + str(R.get("err")))
        print(R.get("stack", ""))
        return 1

    for k in ("chipSampled", "ghostCount", "ghostPairs", "ghostSameCol",
              "frameW", "expectFrameW", "tableW", "printableW",
              "chipsAfterOff", "printNonWk", "printWkCols", "mmPx",
              "rowsAtStart", "ghostHiddenUnderAny"):
        if k in R:
            print(f"   {k}: {R[k]}")
    print(f"   banner: {R.get('banner','')}")
    print(f"   ghost tooltip line 1: {str(R.get('ghostTip','')).splitlines()[:1]}")
    if R.get("yOutliers"):
        print("   Y outliers: " + json.dumps(R["yOutliers"]))
    if R.get("hiddenSamples"):
        print("   hidden samples: " + json.dumps(R["hiddenSamples"]))
    print()

    fails = [c for c in R["checks"] if not c["pass"]]
    for c in R["checks"]:
        mark = "ok  " if c["pass"] else "FAIL"
        print(f"  {mark} {c['name']}" + (f"   [{c['detail']}]" if c["detail"] else ""))
    print(f"\n{len(R['checks']) - len(fails)}/{len(R['checks'])} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
