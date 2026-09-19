#!/usr/bin/env python3
"""
P32 check (TEST-34): marker placement, and three filter-row defects.

PLACEMENT. Markers sharing a cell used to alternate above and below the midline
on i%2, as a fixed percentage of a height the render could not know. Measured on
P31 that produced exactly two vertical bands for every N from 2 to 6 (N=3 came
out [28, 72, 28]), so the first and third marker in a cell sat on top of each
other and from N=5 their icons overlapped for real. The percentage also meant
the spread grew with the row: 7.5px at 34px, 14px at 65px, so a tall row stopped
reading as one line.

Placement is now anchored at the cell's own centre with PIXEL offsets, cascading
diagonally. The assertions are the properties that model promises, not the
numbers it happens to produce: every marker inside its row at every setting,
no two markers in a cell sharing a y, and offsets monotonic in both axes.

LABELS DO NOT MOVE LAYOUT. This is the user's requirement, stated in their
words: "should be able to toggle the labels on and off without impacting the
layout. If the rows are too condensed, there is the row height control." So the
assertion is equality of every row height across the toggle, and separately
that the row height control is a real remedy: label overflow at a short row has
to go to zero once the row is tall enough, or the advice is wrong.

P31 held rows at a 48px floor while labels were on, and did it WITHOUT
rebuilding: 105 of 105 rows changed height while 0 of 146 markers moved. Both
halves are asserted here, in the opposite direction.

THREE DEFECTS, each from a user report:
  A. Hiding the filter row hid the only control that could bring it back.
  B. Two fields drove the same title filter.
  C. Changing a milestone's health cleared the week filter. The cause was
     general: teardown() dropped the week options, taking the selection with
     them, and rebuildWeekFilter() never put it back, so EVERY rerender lost it.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p32_check.py [--xlsx FILE] [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p32-out">(.*?)</pre>', re.S)

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p32-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  function freeze(){
    const s=document.createElement('style');
    s.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(s); void document.body.offsetWidth;
  }

  // Overflow past the marker's OWN row. Measured on the row's border box,
  // which is the frame getBoundingClientRect reports for both.
  function containment(){
    let markers=0,labels=0,mOut=0,lOut=0,worstM=-1e9,worstL=-1e9;
    document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)').forEach(function(tr){
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
    return Array.from(document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)'))
      .map(function(tr){ return Math.round(tr.getBoundingClientRect().height*100)/100; });
  }
  function visibleRows(){
    return document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)').length;
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

    // ============ 1. The offset generator, N=1..6 ============
    // Taken straight from msCellOffset rather than from the 4 two-marker cells
    // the real board happens to contain, because the defect this replaces only
    // appeared from N=3 and the data cannot reach it.
    const geo=[];
    for(let n=1;n<=6;n++){
      const o=[]; for(let i=0;i<n;i++) o.push(msCellOffset(i,n,15,36,34));
      geo.push({n:n,dx:o.map(function(p){return Math.round(p.dx*100)/100;}),
                     dy:o.map(function(p){return Math.round(p.dy*100)/100;})});
    }
    R.notes.geometry=geo;
    ck('offsets: a lone marker is dead centre',
       geo[0].dx[0]===0&&geo[0].dy[0]===0, 'dx '+geo[0].dx[0]+' dy '+geo[0].dy[0]);
    // The headline property. Two markers on one y is what i%2 produced.
    const sharedY=geo.filter(function(g){
      return g.n>1 && new Set(g.dy).size!==g.n; });
    ck('offsets: there are multi-marker cases to check', geo.length===6, geo.length+' values of N');
    // Inverted at P33. Vertical separation moved OUT of this function and into
    // the row's band, because markers sharing a cell are consecutive in their
    // proximity run and the band already puts them on different lines. Two
    // vertical offsets would compound, which is the failure P32 removed between
    // the spread and the label band. msCellOffset is horizontal-only now, and
    // the vertical property is asserted in tools/p33_check.py against the
    // combined position.
    const anyDy=geo.filter(function(g){ return g.dy.some(function(v){ return v!==0; }); });
    ck('offsets: this function no longer offsets vertically at all',
       anyDy.length===0, anyDy.map(function(g){return 'n='+g.n+' '+JSON.stringify(g.dy);}).join(' | '));
    // Diagonal means monotonic in BOTH axes, which is what makes the cascade
    // read as one sequence rather than a scatter.
    const notMono=geo.filter(function(g){
      if(g.n<2) return false;
      for(let i=1;i<g.n;i++){ if(!(g.dx[i]>g.dx[i-1])) return true; }
      return false;
    });
    ck('offsets: the horizontal spread is strictly increasing across the cell',
       notMono.length===0, notMono.map(function(g){return 'n='+g.n;}).join(', '));
    // Symmetric about the centre: the cell's midline stays the anchor.
    const notSym=geo.filter(function(g){
      const s=g.dy.reduce(function(a,b){return a+b;},0);
      return Math.abs(s)>0.05; });
    ck('offsets: the cascade is symmetric about the cell centre',
       notSym.length===0, notSym.map(function(g){return 'n='+g.n;}).join(', '));
    // Budgeted, not clamped afterwards: the outermost centre plus half an icon
    // has to sit inside the row the user asked for.
    const overBudget=[];
    [[15,36,34],[24,36,28],[10,72,65],[24,20,28]].forEach(function(cfg){
      for(let n=2;n<=6;n++) for(let i=0;i<n;i++){
        const p=msCellOffset(i,n,cfg[0],cfg[1],cfg[2]);
        if(Math.abs(p.dy)+cfg[0]/2 > cfg[2]/2+0.01)
          overBudget.push('ico'+cfg[0]+'/col'+cfg[1]+'/row'+cfg[2]+' n'+n+' i'+i);
      }
    });
    ck('offsets: no offset can put an icon past the row it was budgeted for',
       overBudget.length===0, overBudget.slice(0,5).join(', '));

    // ============ 2. Labels do not move layout ============
    const lblCb=document.getElementById('btn-lbl');
    if(lblCb&&lblCb.checked){ lblCb.checked=false; toggleLabels(lblCb); }
    setShortTitleMode('off');
    setRowHeight(34); setIcoSize(15); setWkWidth(36); onSizeSliderRelease();
    await settle(); await settle();
    const hOff=rowHeights();
    // Counting rerenders directly. A toggle that quietly rebuilds the board is
    // not "no layout impact", it is the same impact paid for twice.
    let rerenders=0;
    const _rr=window.rerender;
    window.rerender=function(){ rerenders++; return _rr.apply(this,arguments); };

    if(lblCb&&!lblCb.checked){ lblCb.checked=true; toggleLabels(lblCb); }
    await settle(); await settle();
    const hLbl=rowHeights();
    const lblRerenders=rerenders;
    setShortTitleMode('both');
    await settle(); await settle();
    const hBoth=rowHeights();
    window.rerender=_rr;

    function sameHeights(a,b){
      if(a.length!==b.length) return a.length+' vs '+b.length+' rows';
      let bad=0; for(let i=0;i<a.length;i++) if(Math.abs(a[i]-b[i])>0.5) bad++;
      return bad?(bad+' of '+a.length+' rows changed'):'';
    }
    R.notes.rowHeights={off:hOff[0],labels:hLbl[0],idTitle:hBoth[0],sample:hOff.length};
    ck('labels: there are rows to compare', hOff.length>100, hOff.length+' rows');
    ck('labels: turning milestone labels on does not change any row height',
       sameHeights(hOff,hLbl)==='', sameHeights(hOff,hLbl)||'identical at '+hOff[0]+'px');
    ck('labels: nor does switching the title mode to ID + Title',
       sameHeights(hOff,hBoth)==='', sameHeights(hOff,hBoth)||'identical at '+hOff[0]+'px');
    ck('labels: the toggle does not rebuild the board behind the scenes',
       lblRerenders===0, lblRerenders+' rerender(s)');

    // ============ 3. Containment across the sweep ============
    // Labels ON and ID + Title throughout, which is the heaviest case and the
    // one the user runs.
    const sweep=[];
    const settings=[[34,15,36],[28,15,36],[34,24,36],[34,10,20],[48,15,36],[65,15,36],[65,15,72],[72,24,72]];
    for(let i=0;i<settings.length;i++){
      const s=settings[i];
      // Drive the slider ELEMENTS, not only the setters. rerender() reapplies
      // display settings by reading ico-size and wk-width back off their
      // sliders, so a bare setIcoSize(24) is undone by the rebuild it triggers
      // and this sweep was measuring the default over and over. Found while
      // writing p33_check, by a diagnostic that asked for a 10px icon and
      // measured 15.
      const _r=document.getElementById('row-height'), _i=document.getElementById('ico-size'),
            _w=document.getElementById('wk-width');
      if(_r) _r.value=s[0]; if(_i) _i.value=s[1]; if(_w) _w.value=s[2];
      setRowHeight(s[0]); setIcoSize(s[1]); setWkWidth(s[2]); onSizeSliderRelease();
      await settle(); await settle();
      const c=containment(); c.at='row '+s[0]+' / ico '+s[1]+' / wk '+s[2]; c.rowH=s[0];
      sweep.push(c);
    }
    R.notes.sweep=sweep;
    ck('containment: every setting had markers and labels to measure',
       sweep.every(function(c){ return c.markers>100&&c.labels>100; }),
       sweep.map(function(c){return c.at+':'+c.markers+'/'+c.labels;}).join(' | '));
    const mBad=sweep.filter(function(c){ return c.markersOut>0; });
    ck('containment: no marker sits outside its row at any setting',
       mBad.length===0, mBad.map(function(c){return c.at+'='+c.markersOut;}).join(', '));
    // Labels are allowed out of the row on a short one: that is the trade the
    // user chose over rows growing underneath them. What is NOT allowed is an
    // unbounded spill, or the row height control failing to fix it.
    const worstSpill=Math.max.apply(null,sweep.map(function(c){ return c.labelsOut?c.worstLabel:0; }));
    ck('containment: a label never spills more than one label line',
       worstSpill<=20, 'worst '+worstSpill+'px');
    // "Use the row height control" is only sound advice if more row height
    // actually buys less spill and eventually none. Asserted as that property
    // rather than against a guessed threshold: measured, a 25px stack banded
    // 13px off the centre needs about 52px of row, so it clears between the
    // 48px and 65px settings.
    const byRow={};
    sweep.forEach(function(c){ byRow[c.rowH]=Math.max(byRow[c.rowH]||0,c.labelsOut); });
    const rowsAsc=Object.keys(byRow).map(Number).sort(function(a,b){return a-b;});
    R.notes.spillByRowHeight=rowsAsc.map(function(r){ return r+'px:'+byRow[r]; });
    ck('containment: the sweep covers a range of row heights', rowsAsc.length>=4,
       rowsAsc.join(', '));
    // Not monotonic at P33, and deliberately so. The band amplitude now scales
    // with the row until it caps, so going 28 -> 34 buys a bigger stagger
    // before the row is tall enough to contain it, and spill rises before it
    // falls. What the row height control actually promises is that spill CLEARS
    // once the row has room, which is what is asserted, plus a bound on how far
    // a label can ever reach.
    const tallest=rowsAsc[rowsAsc.length-1];
    ck('containment: and reaches zero, so the row height control is a real remedy',
       byRow[tallest]===0, tallest+'px leaves '+byRow[tallest]);

    // ============ 4. Ghosts still follow the P27 rule ============
    setRowHeight(34); setIcoSize(15); setWkWidth(36); onSizeSliderRelease();
    await settle(); await settle();
    // The baseline overlay is off by default, so without this the ghost block
    // measures an empty set. The sample-size assertion below is what caught it.
    const gb=document.getElementById('btn-baseline-ms');
    if(gb&&!gb.checked){ gb.checked=true; toggleBaselineMilestones(gb); }
    await settle(); await settle();
    const ghosts=Array.from(document.querySelectorAll('.m-ghost'));
    let paired=0,offY=0;
    ghosts.forEach(function(g){
      const key=g.getAttribute('data-ghost-for');
      const live=key?document.querySelector('.m-wrap:not(.m-ghost)[data-ms-key="'+CSS.escape(key)+'"]'):null;
      if(!live) return;
      paired++;
      const gr=g.getBoundingClientRect(), lr=live.getBoundingClientRect();
      if(gr.height&&lr.height&&Math.abs((gr.top+gr.height/2)-(lr.top+lr.height/2))>1) offY++;
    });
    R.notes.ghosts={total:ghosts.length,paired:paired,offY:offY};
    ck('ghosts: there are baseline ghosts to measure', paired>50, paired+' paired of '+ghosts.length);
    ck('ghosts: every ghost still sits level with its own pair',
       offY===0, offY+' off their pair');

    // ============ 5. Defect A: the filter row can always be brought back ============
    const hdrBtn=document.getElementById('btn-filter-toggle');
    const bar=document.getElementById('top-filter-bar');
    ck('defect A: the toggle lives in the header, outside the bar it hides',
       !!hdrBtn && !bar.contains(hdrBtn), hdrBtn?('in bar: '+bar.contains(hdrBtn)):'missing');
    toggleTopFilterBar(false);
    await settle();
    const barHidden=bar.getBoundingClientRect().height<2;
    ck('defect A: hiding the row really collapses it', barHidden,
       bar.getBoundingClientRect().height+'px');
    // The rule TD-72 records is that the control OUTLIVES what it hides, not
    // that it is a visible header button. P36 moved it into the More Actions
    // menu, so the assertion follows the PATH: something laid out on screen,
    // not inside the bar it would restore, that exposes the toggle when used.
    //
    // HOW "on screen" is measured matters more than it looks. Measured against
    // this build, a control trapped inside the collapsed bar reports
    // offsetParent non-null, height 24px, one client rect AND checkVisibility()
    // true, because the bar clips with max-height:0/overflow:hidden and that
    // does not zero its children's boxes. Every obvious API says the trapped
    // control is fine. (checkVisibility DOES answer the closed-<details> case,
    // so it is not a general answer to "is this hidden".) What discriminates is
    // intersecting the element's box with every clipping ancestor: the bar's
    // clip is 1px tall, so the 24px child survives as ~1px of visible height.
    const visibleH=function(el){
      if(!el) return 0;
      let r=el.getBoundingClientRect();
      let top=r.top, bot=r.bottom;
      let n=el.parentElement;
      while(n&&n!==document.body){
        const cs=getComputedStyle(n);
        if(cs.overflowY==='hidden'||cs.overflowY==='clip'||cs.overflow==='hidden'){
          const nr=n.getBoundingClientRect();
          top=Math.max(top,nr.top); bot=Math.min(bot,nr.bottom);
        }
        n=n.parentElement;
      }
      top=Math.max(top,0); bot=Math.min(bot,window.innerHeight);
      return Math.max(0,Math.round((bot-top)*10)/10);
    };
    const reacher=document.getElementById('btn-more-actions')||hdrBtn;
    const reacherLive=visibleH(reacher)>8;
    const reacherOutside=!!reacher&&!bar.contains(reacher);
    if(typeof toggleMoreActions==='function') toggleMoreActions(true);
    await settle();
    const exposed=visibleH(hdrBtn)>8;
    if(typeof toggleMoreActions==='function') toggleMoreActions(false);
    await settle();
    const stillReachable=reacherLive&&reacherOutside&&exposed;
    R.notes.defectA={reacher:reacher?reacher.id:null,
                     reacherVisibleH:visibleH(reacher),
                     reacherOutsideBar:reacherOutside,
                     toggleVisibleHWhenMenuOpen:exposed};
    ck('defect A: with the row hidden, the toggle is still reachable from screen',
       stillReachable, JSON.stringify(R.notes.defectA));
    // Does the rewritten assertion still catch the defect it exists for? Put
    // the toggle back inside the collapsed bar, which is the TD-72 state, and
    // require the same expression to go false. The first version of this
    // rewrite passed here, which is how the measurement above was found to be
    // the wrong one.
    const homeParent=hdrBtn?hdrBtn.parentNode:null;
    const homeNext=hdrBtn?hdrBtn.nextSibling:null;
    let trappedVerdict=null, trappedVisibleH=null;
    if(hdrBtn&&homeParent){
      bar.appendChild(hdrBtn);
      await settle();
      trappedVisibleH=visibleH(hdrBtn);
      trappedVerdict=(reacherLive&&reacherOutside&&trappedVisibleH>8);
      homeParent.insertBefore(hdrBtn,homeNext);
      await settle();
    }
    R.notes.defectA.visibleHWhenTrapped=trappedVisibleH;
    R.notes.defectA.verdictWhenTrapped=trappedVerdict;
    ck('defect A: and that check still FAILS when the toggle is trapped in the bar',
       trappedVerdict===false, 'trapped visible height '+trappedVisibleH+
       'px, verdict '+trappedVerdict);
    ck('defect A: the toggle shows the state it sets',
       hdrBtn && hdrBtn.getAttribute('aria-pressed')==='false' && !hdrBtn.classList.contains('on'),
       hdrBtn?(hdrBtn.getAttribute('aria-pressed')+' / on='+hdrBtn.classList.contains('on')):'');
    toggleTopFilterBar(true);
    await settle();
    ck('defect A: clicking it brings the row back',
       bar.getBoundingClientRect().height>20, bar.getBoundingClientRect().height+'px');
    const hideBtn=document.getElementById('btn-filter-hide');
    // getComputedStyle reports the USED value of margin-left, a pixel number,
    // never the literal 'auto'. Right-alignment is a position, so it is
    // measured as one: within a few px of the bar's own right edge.
    const hr=hideBtn?hideBtn.getBoundingClientRect():null;
    const br=bar.getBoundingClientRect();
    ck('defect A: the bar also carries its own hide control',
       !!hideBtn && hr.width>0, hideBtn?(hr.width+'px wide'):'missing');
    ck('defect A: and that control sits on the right-hand side',
       !!hr && (br.right-hr.right)<24, hr?Math.round(br.right-hr.right)+'px from the right edge':'n/a');

    // ============ 6. Defect B: one field, one filter ============
    const titleFields=Array.from(document.querySelectorAll('#top-filter-bar input[type="text"]'))
      .filter(function(el){ return /title/i.test(el.id); });
    R.notes.titleFields=titleFields.map(function(el){return el.id;});
    ck('defect B: exactly one title field drives the title filter',
       titleFields.length===1, titleFields.map(function(e){return e.id;}).join(', ')||'none');
    ck('defect B: it is the id applyFilter and clearFilter already read',
       titleFields.length===1&&titleFields[0].id==='filter-title',
       titleFields.length?titleFields[0].id:'none');
    // And it still filters, which a field left as a decoration would not.
    const beforeT=visibleRows();
    const tf=document.getElementById('filter-title');
    tf.value='PFD'; onTitleFilterInput(tf);
    await settle(); await settle();
    const afterT=visibleRows();
    ck('defect B: typing in it narrows the board',
       afterT>0&&afterT<beforeT, afterT+' of '+beforeT);
    clearOneFilter('filter-title');
    await settle();
    ck('defect B: clearing it restores the board', visibleRows()===beforeT,
       visibleRows()+' vs '+beforeT);

    // ============ 7. Defect C: a rebuild must not drop the week filter ============
    const wf=document.getElementById('week-filter');
    const targetWeek=String(Math.min(6,WE_LABELS.length-1));
    wf.value=targetWeek; applyFilter();
    await settle(); await settle();
    const filteredRows=visibleRows();
    ck('defect C: the week filter narrowed the board to start with',
       filteredRows>0&&filteredRows<R.notes.board.rows, filteredRows+' of '+R.notes.board.rows);

    // The user's exact path: open a milestone and change its health dot.
    const anyMarker=document.querySelector('tr[data-type="row"]:not(.hidden-row) .m-wrap:not(.m-ghost)[data-ms]');
    let took=false;
    if(anyMarker){ anyMarker.click(); await settle(); }
    const dot=document.querySelector('#ms-health-dots .health-dot');
    if(dot && msDialogFor){ onMsHealthClick(dot); took=true; }
    await settle(); await settle();
    R.notes.healthPath={opened:!!anyMarker,dotClicked:took,
                        weekAfter:wf.value,rowsAfter:visibleRows()};
    ck('defect C: the health change actually happened, so this is not a vacuous pass',
       took, JSON.stringify(R.notes.healthPath));
    ck('defect C: the week filter is still selected after it',
       wf.value===targetWeek, '"'+wf.value+'" vs "'+targetWeek+'"');
    ck('defect C: and the board is still narrowed, not silently full again',
       visibleRows()===filteredRows, visibleRows()+' vs '+filteredRows);

    // Same defect, reached the general way, because health was only one caller.
    wf.value=targetWeek; applyFilter(); await settle();
    scheduleRerender(true);
    await settle(); await settle();
    ck('defect C: nor after any other rebuild, which is where the fault really was',
       wf.value===targetWeek&&visibleRows()===filteredRows,
       '"'+wf.value+'", '+visibleRows()+' rows');

    // Both bounds: a remembered index past the end of a shorter timeline must
    // not be restored.
    const saved=WE_LABELS.length;
    wf.value=String(saved-1); applyFilter(); await settle();
    ck('defect C: the restore is bounded at the top of the range',
       parseInt(wf.value,10)<saved, wf.value+' of '+saved);

    clearFilter(); await settle();
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
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html.replace("</body>", inject + "</body>")
    if page == html:
        sys.exit("Could not find </body> to inject into.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p32.html"
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
    for k in ("board", "rowHeights", "titleFields", "ghosts", "healthPath",
              "spillByRowHeight"):
        if k in n:
            print(f"   {k}: {json.dumps(n[k])}")
    if "geometry" in n:
        print("   cascade offsets at 15px icon / 36px column / 34px row:")
        for g in n["geometry"]:
            print(f"     n={g['n']}  dx={g['dx']}  dy={g['dy']}")
    if "sweep" in n:
        print("   containment sweep (labels on, ID + Title):")
        for c in n["sweep"]:
            print("     %-28s markers %3d out %d (worst %5s)  labels %3d out %2d (worst %5s)"
                  % (c["at"], c["markers"], c["markersOut"], c["worstMarker"],
                     c["labels"], c["labelsOut"], c["worstLabel"]))
    print()

    fails = [c for c in R["checks"] if not c["pass"]]
    for c in R["checks"]:
        mark = "ok  " if c["pass"] else "FAIL"
        print(f"  {mark} {c['name']}" + (f"   [{c['detail']}]" if c["detail"] else ""))

    print(f"\n{len(R['checks']) - len(fails)}/{len(R['checks'])} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
