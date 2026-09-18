#!/usr/bin/env python3
"""
P33 check (TEST-35): proximity-scoped marker staggering.

THE RULE. A marker's vertical position is a property of the marker, and the
label is a child of the marker's wrap, so it rides whatever the wrap does. P32
kept every icon on the row's centreline and moved only the text, which meant a
label's height told you nothing about which marker owned it. Now a row's
markers are cut into proximity RUNS and each run's members are put on bands.

The three things that would make this a regression:

  THE SEQUENCE. A run of 2 is top then bottom, leftmost up. A run of 3 is top,
  middle, bottom. From 4 the cycle REPEATS, so the fourth is top again.

  P33 shipped a triangle wave here instead (fourth on the middle band) to keep
  markers 1 and 4 off one line. P34 reversed it against a rendered case: row 69
  of the Aug-29 board carries four markers in directly adjacent columns and the
  user asked for the fourth to reset to the top. These two assertions and their
  names move with that reversal; the collision they guarded against is real and
  is now an accepted trade, measured in tools/p34_check.py rather than avoided.

  The reference board's densest cell holds two markers, so this is asserted
  against the generator, not against the data.

  THE BUDGET. Every offset is pixels budgeted from the row height, so an icon
  cannot leave its row at any combination of row height, icon size and column
  width. A cell holding more than three markers grows ITS row, and only its row,
  because markers sharing an x cannot reuse a band the way markers in different
  cells can.

  THE LABEL RIDES ITS ICON. Per marker, the stack's vertical centre equals its
  own wrap's centre. This is the property the whole partial exists for, so it is
  asserted for every marker on the board rather than sampled, and the absence of
  any independent label offset is asserted separately.

Also here: the renderMarker() factory (one writer for --mdx/--mdy, so a ghost
cannot desync from its pair) and the derived hidden-marker early-out in
markerCenter(), which must agree exactly with the measurement it replaces.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p33_check.py [--xlsx FILE] [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p33-out">(.*?)</pre>', re.S)

# Measured on releases/v3.1.0-P32_*.html with THIS probe's corrected sweep, so
# the comparison is like for like. The first version of these numbers came from
# the broken sweep and was not: it reported 28 at every setting because the
# settings were never being applied.
#
# Both halves matter and they move in opposite directions at one setting. The
# COUNT can rise because P33 bands more markers (a proximity run is wider than
# P32's per-cluster reset), which is the feature working. The DEPTH decides
# whether a label reads as a tight fit or lands on the neighbouring row, so that
# is what is asserted per setting, with the total count asserted across the
# sweep.
P32_SPILL = {
    "row 34 / ico 15 / wk 36": {"n": 28, "worst": 8.9},
    "row 28 / ico 15 / wk 36": {"n": 28, "worst": 8.9},
    "row 34 / ico 24 / wk 36": {"n": 28, "worst": 8.9},
    "row 34 / ico 10 / wk 20": {"n": 28, "worst": 10.3},
    "row 48 / ico 15 / wk 36": {"n": 28, "worst": 2.1},
    "row 65 / ico 15 / wk 36": {"n": 0, "worst": -6.4},
    "row 72 / ico 24 / wk 72": {"n": 0, "worst": -7.0},
}

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p33-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  function freeze(){
    const s=document.createElement('style');
    s.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(s); void document.body.offsetWidth;
  }
  const rows=function(){ return Array.from(
    document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)')); };
  // Drive the real controls, not just the setters. rerender() reapplies display
  // settings by READING the slider elements back:
  //     setWkWidth(document.getElementById('wk-width').value)
  //     setIcoSize(document.getElementById('ico-size').value)
  // so a bare setIcoSize(10) is undone by the very rebuild it triggers, and the
  // sweep silently measures one setting over and over. Caught by a diagnostic
  // that printed iconSize 15 after being asked for 10. Row height is the other
  // way round (applyRowHeight pushes the variable onto the slider), but it is
  // set here too so all three read the same way.
  function setDisplay(rowH,ico,wk){
    const r=document.getElementById('row-height'), i=document.getElementById('ico-size'),
          w=document.getElementById('wk-width');
    if(r) r.value=rowH; if(i) i.value=ico; if(w) w.value=wk;
    setRowHeight(rowH); setIcoSize(ico); setWkWidth(wk);
    onSizeSliderRelease();
  }

  function containment(){
    let markers=0,labels=0,mOut=0,lOut=0,worstM=-1e9,worstL=-1e9;
    rows().forEach(function(tr){
      const rr=tr.getBoundingClientRect();
      if(rr.height===0) return;
      tr.querySelectorAll('.m-wrap:not(.m-ghost)').forEach(function(w){
        const wr=w.getBoundingClientRect();
        if(wr.width||wr.height){
          markers++;
          const ov=Math.max(rr.top-wr.top,wr.bottom-rr.bottom);
          if(ov>0.5) mOut++;
          if(ov>worstM) worstM=ov;
        }
        const st=w.querySelector('.m-lbl-stack');
        if(st){
          const sr=st.getBoundingClientRect();
          if(sr.width||sr.height){
            labels++;
            const o2=Math.max(rr.top-sr.top,sr.bottom-rr.bottom);
            if(o2>0.5) lOut++;
            if(o2>worstL) worstL=o2;
          }
        }
      });
    });
    return {markers:markers,labels:labels,markersOut:mOut,labelsOut:lOut,
            worstMarker:Math.round(worstM*10)/10, worstLabel:Math.round(worstL*10)/10};
  }
  function rowHeights(){
    return rows().map(function(tr){ return Math.round(tr.getBoundingClientRect().height*100)/100; });
  }

  try{
    window.XLSX={
      read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
      utils:{ sheet_to_json:function(s){ return s.__aoa; } }
    };
    freeze();
    PENDING_IMPORT_FILE='SNIP_29Aug26_export.xlsx';
    showMapper(Parse.workbook(new Uint8Array([0])));
    const dd=document.getElementById('cfg-datadate'); if(dd) dd.value='2026-08-29';
    await settle();
    runIngest();
    await settle(); await settle();
    R.notes.board={rows:document.querySelectorAll('#tbody tr.data').length,
                   markers:document.querySelectorAll('.m-wrap:not(.m-ghost)').length};
    ck('setup: a board was built to measure',
       R.notes.board.rows>100&&R.notes.board.markers>100, JSON.stringify(R.notes.board));

    // ================= 1. The sequence =================
    // Against the generator: the board's densest cell holds two markers, so the
    // case this rule exists for is unreachable from the data.
    // Columns one apart, i.e. every marker in its own cell, which is the case
    // the sequence rule describes. The same-cell case is section 8.
    const colsOf=function(n){ const a=[]; for(let k=0;k<n;k++) a.push(k); return a; };
    const seq={}; for(let n=1;n<=8;n++) seq[n]=msRunLevels(colsOf(n),3);
    R.notes.sequence=seq;
    ck('sequence: a run of one is the middle band',
       seq[1].length===1&&seq[1][0]===1, JSON.stringify(seq[1]));
    ck('sequence: a run of two is top then bottom, leftmost up',
       seq[2].join(',')==='0,2', JSON.stringify(seq[2]));
    ck('sequence: a run of three cascades top, middle, bottom',
       seq[3].join(',')==='0,1,2', JSON.stringify(seq[3]));
    // The discriminating case, taken from the user's own worked example.
    ck('sequence: the fourth marker RESETS to the top band (P34 reversal)',
       seq[4][3]===0, 'got level '+seq[4][3]+' in '+JSON.stringify(seq[4]));
    ck('sequence: and the fifth is the middle band, so the cycle repeats cleanly',
       seq[5][4]===1, JSON.stringify(seq[5]));
    // The property that makes a triangle wave worth having over a repeat.
    let adjacentSame=[];
    for(let n=2;n<=8;n++) for(let k=1;k<seq[n].length;k++)
      if(seq[n][k]===seq[n][k-1]) adjacentSame.push('n='+n+' at '+k);
    ck('sequence: no two ADJACENT markers in a run share a band, for n up to 8',
       adjacentSame.length===0, adjacentSame.join(', '));
    let badLevel=[];
    for(let n=1;n<=8;n++) seq[n].forEach(function(l){ if(l<0||l>2) badLevel.push('n='+n+' level '+l); });
    ck('sequence: every level is one of the three bands',
       badLevel.length===0, badLevel.join(', '));

    // ================= 2. The budget =================
    const overBudget=[];
    [[15,36,34],[24,36,28],[10,72,65],[24,20,28],[15,36,72]].forEach(function(cfg){
      const ico=cfg[0], rowH=cfg[2];
      for(let levels=3;levels<=6;levels++){
        const rh=Math.max(rowH,msRowHeightFor(levels,ico));
        for(let l=0;l<levels;l++){
          const dy=msBandOffset(l,levels,ico,rh);
          if(Math.abs(dy)+ico/2 > rh/2+0.01)
            overBudget.push('ico'+ico+'/row'+rowH+' levels'+levels+' l'+l+' dy'+dy.toFixed(1));
        }
      }
    });
    ck('budget: no band offset can put an icon past the row it was budgeted for',
       overBudget.length===0, overBudget.slice(0,4).join(', '));
    // A row needing only three bands must NOT be grown.
    ck('budget: three bands never grow the row',
       msRowHeightFor(3,15)===0&&msRowHeightFor(2,24)===0,
       msRowHeightFor(3,15)+' / '+msRowHeightFor(2,24));
    ck('budget: four or more bands do grow it, and monotonically',
       msRowHeightFor(4,15)>0 && msRowHeightFor(5,15)>msRowHeightFor(4,15),
       msRowHeightFor(4,15)+' then '+msRowHeightFor(5,15));
    ck('budget: how many bands a row needs follows its densest cell',
       msRowBands(1)===3&&msRowBands(3)===3&&msRowBands(5)===5,
       [msRowBands(1),msRowBands(3),msRowBands(5)].join(','));

    // ================= 3. The label rides its own icon =================
    const lblCb=document.getElementById('btn-lbl');
    if(lblCb&&!lblCb.checked){ lblCb.checked=true; toggleLabels(lblCb); }
    setShortTitleMode('both');
    setDisplay(34,15,36);
    await settle(); await settle();

    let pairs=0, offCentre=[];
    document.querySelectorAll('.m-wrap:not(.m-ghost)').forEach(function(w){
      const st=w.querySelector('.m-lbl-stack');
      if(!st) return;
      const wr=w.getBoundingClientRect(), sr=st.getBoundingClientRect();
      if(!(wr.height&&sr.height)) return;
      pairs++;
      const d=Math.abs((wr.top+wr.height/2)-(sr.top+sr.height/2));
      if(d>1) offCentre.push(Math.round(d*10)/10);
    });
    R.notes.labelRide={pairs:pairs,off:offCentre.length};
    ck('label: there are marker and label pairs to measure', pairs>100, pairs+' pairs');
    ck('label: EVERY label sits at its own icon’s height',
       offCentre.length===0, offCentre.length+' off by up to '+(offCentre.length?Math.max.apply(null,offCentre):0)+'px');
    // And nothing carries an offset of its own any more.
    const strays=Array.from(document.querySelectorAll('.m-wrap,[class*="lbl-band"]'))
      .filter(function(e){ return e.style.getPropertyValue('--lbl-dy')||/lbl-band/.test(e.className); });
    ck('label: no element carries an independent label offset or band class',
       strays.length===0, strays.length+' found');

    // ================= 4. The factory =================
    // One writer for geometry. Asserted on the live DOM: every positioned wrap
    // has both custom properties, and the LoE variant has neither, which is
    // only true if they all came through renderMarker().
    let posWraps=0, missing=0, loe=0, loeWithGeom=0;
    document.querySelectorAll('.m-wrap').forEach(function(w){
      if(w.classList.contains('m-wrap-loe')){
        loe++;
        if(w.style.getPropertyValue('--mdx')||w.style.getPropertyValue('--mdy')) loeWithGeom++;
        return;
      }
      posWraps++;
      if(!w.style.getPropertyValue('--mdx')||!w.style.getPropertyValue('--mdy')) missing++;
    });
    R.notes.factory={positioned:posWraps,missingGeom:missing,loe:loe,loeWithGeom:loeWithGeom};
    ck('factory: there are positioned wraps to audit', posWraps>100, posWraps);
    ck('factory: every positioned wrap carries both offsets',
       missing===0, missing+' without');
    ck('factory: and the flow-layout LoE variant carries neither',
       loeWithGeom===0, loeWithGeom+' of '+loe+' with geometry');

    // ================= 5. Ghosts take their pair's band =================
    const gb=document.getElementById('btn-baseline-ms');
    if(gb&&!gb.checked){ gb.checked=true; toggleBaselineMilestones(gb); }
    await settle(); await settle();
    let paired=0, offY=0, worstG=0;
    document.querySelectorAll('.m-ghost').forEach(function(g){
      const key=g.getAttribute('data-ghost-for');
      const live=key?document.querySelector('.m-wrap:not(.m-ghost)[data-ms-key="'+CSS.escape(key)+'"]'):null;
      if(!live) return;
      paired++;
      const gr=g.getBoundingClientRect(), lr=live.getBoundingClientRect();
      if(!(gr.height&&lr.height)) return;
      const d=Math.abs((gr.top+gr.height/2)-(lr.top+lr.height/2));
      if(d>1){ offY++; if(d>worstG) worstG=d; }
    });
    R.notes.ghosts={paired:paired,offY:offY};
    ck('ghosts: there are ghosts paired to a live marker', paired>50, paired+' paired');
    ck('ghosts: every ghost sits level with its pair, so it inherited the band',
       offY===0, offY+' off by up to '+Math.round(worstG*10)/10+'px');
    if(gb&&gb.checked){ gb.checked=false; toggleBaselineMilestones(gb); }
    await settle();

    // ================= 6. Labels still do not move layout =================
    if(lblCb&&lblCb.checked){ lblCb.checked=false; toggleLabels(lblCb); }
    setShortTitleMode('off');
    await settle(); await settle();
    const hOff=rowHeights();
    let rerenders=0; const _rr=window.rerender;
    window.rerender=function(){ rerenders++; return _rr.apply(this,arguments); };
    if(lblCb&&!lblCb.checked){ lblCb.checked=true; toggleLabels(lblCb); }
    await settle(); await settle();
    const hOn=rowHeights();
    const lblRerenders=rerenders;
    setShortTitleMode('both');
    await settle(); await settle();
    const hBoth=rowHeights();
    window.rerender=_rr;
    function diff(a,b){ if(a.length!==b.length) return a.length+' vs '+b.length+' rows';
      let n=0; for(let i=0;i<a.length;i++) if(Math.abs(a[i]-b[i])>0.5) n++;
      return n?(n+' of '+a.length+' moved'):''; }
    ck('layout: there are rows to compare', hOff.length>100, hOff.length);
    ck('layout: turning labels on changes no row height',
       diff(hOff,hOn)==='', diff(hOff,hOn)||'identical at '+hOff[0]+'px');
    ck('layout: nor does ID + Title',
       diff(hOff,hBoth)==='', diff(hOff,hBoth)||'identical at '+hOff[0]+'px');
    ck('layout: and the toggle does not rebuild the board',
       lblRerenders===0, lblRerenders+' rerender(s)');

    // ================= 7. Containment and spill across the sweep =================
    const sweep=[];
    [[28,15,36],[34,15,36],[34,24,36],[34,10,20],[48,15,36],[65,15,36],[72,24,72]]
      .forEach(function(s){ sweep.push(s); });
    const results=[];
    for(let i=0;i<sweep.length;i++){
      const s=sweep[i];
      setDisplay(s[0],s[1],s[2]);
      await settle(); await settle();
      const c=containment(); c.at='row '+s[0]+' / ico '+s[1]+' / wk '+s[2]; c.rowH=s[0];
      results.push(c);
    }
    R.notes.sweep=results;
    ck('containment: every setting had markers and labels to measure',
       results.every(function(c){ return c.markers>100&&c.labels>100; }),
       results.map(function(c){return c.at+':'+c.markers;}).join(' | '));
    const mBad=results.filter(function(c){ return c.markersOut>0; });
    ck('containment: no marker sits outside its row at any setting',
       mBad.length===0, mBad.map(function(c){return c.at+'='+c.markersOut;}).join(', '));
    // Against the P32 figures, injected rather than remembered, and measured
    // with this same corrected sweep.
    const deeper=[], compared=[];
    let nowTotal=0, wasTotal=0;
    results.forEach(function(c){
      const b=P32_SPILL[c.at];
      if(!b) return;
      compared.push(c.at);
      nowTotal+=c.labelsOut; wasTotal+=b.n;
      if(c.worstLabel>b.worst+0.2) deeper.push(c.at+': '+c.worstLabel+'px vs '+b.worst+'px');
    });
    R.notes.spillVsP32=results.map(function(c){
      const b=P32_SPILL[c.at];
      return c.at+'  ->  '+c.labelsOut+' out, worst '+c.worstLabel+'px'
             +(b?('    P32: '+b.n+' out, worst '+b.worst+'px'):'    no P32 figure'); });
    R.notes.spillTotals={p33:nowTotal,p32:wasTotal,settings:compared.length};
    ck('spill: there are P32 figures to compare against', compared.length>=6, compared.length+' settings');
    ck('spill: no setting spills DEEPER than it did at P32',
       deeper.length===0, deeper.join(', '));
    ck('spill: and fewer labels spill across the sweep overall',
       nowTotal<wasTotal, nowTotal+' vs '+wasTotal+' over '+compared.length+' settings');
    const tall=results.filter(function(c){ return c.rowH>=65; });
    ck('spill: there are tall-row settings to check', tall.length>=2, tall.length);
    ck('spill: and it still reaches zero once the row has room',
       tall.every(function(c){ return c.labelsOut===0; }),
       tall.map(function(c){return c.at+'='+c.labelsOut;}).join(', '));

    // ================= 8. Hidden markers: derived == measured =================
    // markerCenter() now answers "is this filtered out" from the state the
    // filter wrote, instead of measuring a zero rect per dependency endpoint.
    // The two must agree on EVERY marker under every filter, or the derived
    // path has become a second source of truth, which is the failure mode a
    // stored flag would have had.
    // Runs BEFORE the clone experiment below, on the clean imported board.
    // The first attempt ran after it and tried to rebuild by emptying
    // MILESTONES and calling runIngest() again, which left the board empty and
    // the agreement assertion passing against zero markers. The sample-size
    // assertion beside it caught that, which is what it is for.
    setDisplay(34,15,36); await settle(); await settle();

    function agreement(){
      let n=0, disagree=0;
      document.querySelectorAll('.m-wrap:not(.m-ghost)[data-ms]').forEach(function(el){
        n++;
        const derived=markerHidden(el);
        const r=el.getBoundingClientRect();
        const measured=(r.width===0&&r.height===0);
        // A marker the derived test calls hidden must measure as having no
        // layout, and vice versa.
        if(derived!==measured) disagree++;
      });
      return {n:n,disagree:disagree};
    }
    const agree={};
    agree.none=agreement();
    document.getElementById('week-filter').value='6'; applyFilter();
    await settle(); agree.week=agreement();
    document.getElementById('week-filter').value=''; applyFilter(); await settle();
    document.getElementById('filter-date-from').value='2026-08-01';
    document.getElementById('filter-date-to').value='2026-09-30'; applyFilter();
    await settle(); agree.range=agreement();
    const bandSel=document.getElementById('filter-band');
    if(bandSel&&bandSel.options.length>1){ bandSel.value=bandSel.options[1].value; applyFilter(); }
    await settle(); agree.all=agreement();
    clearFilter(); await settle(); agree.cleared=agreement();
    R.notes.hiddenAgreement=agree;
    const sampled=['none','week','range','all','cleared'].every(function(k){ return agree[k].n>100; });
    ck('hidden: every filter state had markers to compare', sampled,
       JSON.stringify(Object.keys(agree).map(function(k){return k+':'+agree[k].n;})));
    const bad=['none','week','range','all','cleared'].filter(function(k){ return agree[k].disagree>0; });
    ck('hidden: the derived test agrees with the measurement on every marker, under every filter',
       bad.length===0, bad.map(function(k){return k+'='+agree[k].disagree;}).join(', '));
    // And the lines it feeds still come out the same.
    ck('hidden: dependency lines still draw with no filter active',
       (function(){ if(typeof drawDepLines!=='function') return true;
         setAllDep('succ',true); drawDepLines();
         const n=document.querySelectorAll('#dep-line-layer path').length;
         R.notes.depLines=n; return n>100; })(), R.notes.depLines+' paths');

    // ================= 9. Same-cell overflow grows only its own row =================
    setDisplay(34,15,36);
    await settle(); await settle();
    const baseHeights=rowHeights();
    // Clone four extra milestones onto one row, all on the SAME date, which is
    // the case the reference board cannot produce: its densest cell holds two.
    const seed=MILESTONES.filter(function(m){ return m.date; })[0];
    var clones=[];
    for(let k=0;k<4;k++){
      const c=JSON.parse(JSON.stringify(seed));
      c.id=(seed.id||'X')+'_c'+k; c.notes='['+c.id+'] - clone '+k;
      clones.push(c);
    }
    clones.forEach(function(c){ MILESTONES.push(c); UPDATE_MILESTONES.push(c); });
    if(typeof invalidateMsIndexes==='function') invalidateMsIndexes();
    scheduleRerender(true);
    await settle(); await settle();
    const denseTr=Array.from(document.querySelectorAll('tr[data-type="row"]'))
      .filter(function(tr){ return (tr.getAttribute('data-ids')||'').indexOf(seed.ref)>=0
                                || tr.querySelector('.m-wrap[data-ms="'+CSS.escape(seed.id||'')+'"]'); })[0];
    const grown=denseTr?denseTr.style.getPropertyValue('--row-h-eff'):'';
    const cellWraps=denseTr?Array.from(denseTr.querySelectorAll('td.c-wk')).map(function(td){
      return td.querySelectorAll('.m-wrap:not(.m-ghost)').length; }):[];
    const maxCell=cellWraps.length?Math.max.apply(null,cellWraps):0;
    R.notes.overflow={foundRow:!!denseTr,grown:grown,maxInCell:maxCell};
    ck('overflow: the clones really landed in one cell, so this is not vacuous',
       maxCell>3, 'densest cell now holds '+maxCell);
    ck('overflow: that row grew', !!grown, grown||'not grown');
    // Distinct bands for every marker in the crowded cell.
    let ys=[];
    if(denseTr) Array.from(denseTr.querySelectorAll('td.c-wk')).forEach(function(td){
      const ws=td.querySelectorAll('.m-wrap:not(.m-ghost)');
      if(ws.length>3) ys=Array.from(ws).map(function(w){
        const r=w.getBoundingClientRect(); return Math.round((r.top+r.height/2)*10)/10; });
    });
    ck('overflow: every marker in that cell got its own line',
       ys.length>3 && new Set(ys).size===ys.length, JSON.stringify(ys));
    // And no other row moved.
    const afterHeights=rowHeights();
    let othersMoved=0;
    const n=Math.min(baseHeights.length,afterHeights.length);
    for(let i=0;i<n;i++) if(Math.abs(baseHeights[i]-afterHeights[i])>0.5) othersMoved++;
    R.notes.overflowSpread={rowsMoved:othersMoved,of:n};
    ck('overflow: and it is the ONLY row that grew',
       othersMoved<=1, othersMoved+' of '+n+' rows changed height');

    R.ok=true;
  }catch(e){ R.ok=false; R.err=e.message; R.stack=(e.stack||'').split('\n').slice(0,5).join(' | '); }
  emit();
})();
"""


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=str(root / "data" / "schedules" /
                                          "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"))
    ap.add_argument("--html", default=str(root / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    html = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";"
              "const P32_SPILL=" + json.dumps(P32_SPILL) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html.replace("</body>", inject + "</body>")
    if page == html:
        sys.exit("Could not find </body> to inject into.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p33.html"
        tmp.write_text(page, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--window-size=1600,1200", "--virtual-time-budget=90000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit("Probe output not found.\n" + proc.stderr[-3000:])
    R = json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))

    if not R.get("ok"):
        print("PROBE FAILED: " + str(R.get("err")))
        print(R.get("stack", ""))
        for c in R.get("checks", []):
            print(("  ok   " if c["pass"] else "  FAIL ") + c["name"])
        return 1

    n = R.get("notes", {})
    for k in ("board", "labelRide", "factory", "ghosts", "overflow",
              "overflowSpread", "spillTotals", "hiddenAgreement", "depLines"):
        if k in n:
            print(f"   {k}: {json.dumps(n[k])}")
    for line in n.get("spillVsP32", []):
        print("   " + line)
    if "sequence" in n:
        print("   run levels (0 top, 1 middle, 2 bottom):")
        for k in sorted(n["sequence"], key=int):
            print(f"     n={k}  {n['sequence'][k]}")
    if "sweep" in n:
        print("   containment sweep (labels on, ID + Title):")
        for c in n["sweep"]:
            print("     %-28s markers %3d out %d   labels %3d out %2d (worst %5s)"
                  % (c["at"], c["markers"], c["markersOut"], c["labels"],
                     c["labelsOut"], c["worstLabel"]))
    print()

    fails = [c for c in R["checks"] if not c["pass"]]
    for c in R["checks"]:
        print(("  ok   " if c["pass"] else "  FAIL ") + c["name"]
              + (f"   [{c['detail']}]" if c["detail"] else ""))
    print(f"\n{len(R['checks']) - len(fails)}/{len(R['checks'])} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
