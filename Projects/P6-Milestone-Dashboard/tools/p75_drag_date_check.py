#!/usr/bin/env python3
"""
p75_drag_date_check (P75, Matt 2026-10-02):
  "Drag and drop functionality for milestones should also extend to the
   columns which would then change the end date of the field."

Drives the board drag with pointer events (pointerdown on the marker,
pointermove / pointerup through the document, the click a browser fires after
a release), plus the matching mouse events, at 1440 and 390:
  - moves of +2 and -1 weeks and +0 (no change), N=3 milestones: one with no
    start of its own, one with a start, and a user milestone (USR-);
  - each move: the new m.date (weekday kept), the marker in the new column,
    an entry with changes.date, the edited mark and the ghost tick at the
    source week (a USR- milestone has no source, so no mark, per D-18), the
    A flag unchanged, the Start unchanged;
  - the ghost snapped to the target cell and the floating date label during
    the drag;
  - a combined row-and-column drag does both;
  - back to the schedule week clears the override;
  - Undo restores the date with a new entry (history only grows);
  - a plain click still opens the card, a double click still collects, Esc
    cancels;
  - a drop past the visible weeks clamps to the last visible column;
  - a Finish dragged before the milestone's own Start is refused;
  - dependency lines redraw and the filters reapply after a drop;
  - touch (press and hold) moves the column too.
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

OUT_RE = re.compile(r'<pre id="p75d-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900), (390, 844)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p75d-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const settle=()=>wait(260);
  const $=id=>document.getElementById(id);
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const msOf=id=>MILESTONES.find(m=>msId(m)===id);
  const colOf=w=>w?+w.closest('td.c-wk').getAttribute('data-col'):-1;
  const rowOf=w=>w?w.closest('tr.data').getAttribute('data-ref'):null;
  const addDays=(iso,n)=>{ const d=new Date(iso+'T00:00:00'); d.setDate(d.getDate()+n); return isoDay(d); };
  const dow=iso=>new Date(iso+'T00:00:00').getDay();
  const lastEntryOn=key=>{ for(let i=ENTRIES.length-1;i>=0;i--){ const e=ENTRIES[i]; if(e.target&&e.target.kind==='ms'&&e.target.key===key) return e; } return null; };
  const cardOpen=()=>!$('ms-dialog').hidden;
  function closeCard(){ if(cardOpen()) discardMsDialog(); }

  // ---- pointer driver ----
  function fire(el,type,x,y,ptype){
    const o={bubbles:true,cancelable:true,composed:true,clientX:x,clientY:y,button:0,buttons:type.endsWith('up')?0:1,
             pointerId:ptype==='touch'?2:1,pointerType:ptype||'mouse',isPrimary:true,view:window};
    el.dispatchEvent(new PointerEvent('pointer'+type,o));
    if((ptype||'mouse')==='mouse') el.dispatchEvent(new MouseEvent('mouse'+type,o));
  }
  function at(x,y){ return document.elementFromPoint(Math.max(0,Math.min(innerWidth-1,x)),Math.max(0,Math.min(innerHeight-1,y)))||document.body; }
  function centre(el){ const r=el.getBoundingClientRect(); return [r.left+r.width/2,r.top+r.height/2]; }
  function cellCentre(ref,col){
    const tr=document.querySelector('#tbody tr.data[data-ref="'+CSS.escape(ref)+'"]');
    const td=tr&&tr.querySelector('td.c-wk[data-col="'+col+'"]');
    if(!td) return null;
    const r=td.getBoundingClientRect(), rr=tr.getBoundingClientRect();
    return [r.left+r.width/2, rr.top+rr.height/2];
  }
  // Press on the marker, move in steps to (tx,ty), optionally inspect mid
  // drag, then release (or press Esc first). The click is dispatched where a
  // browser would send it: the marker when released on it, else the common
  // ancestor (which no marker handler sees).
  async function drag(w,tx,ty,opt){
    opt=opt||{};
    const ptype=opt.touch?'touch':'mouse';
    const [sx,sy]=centre(w);
    fire(w,'down',sx,sy,ptype);
    if(opt.touch) await wait(MS_DRAG_HOLD_MS+80);
    const steps=6;
    for(let i=1;i<=steps;i++){
      const x=sx+(tx-sx)*i/steps, y=sy+(ty-sy)*i/steps;
      fire(at(x,y),'move',x,y,ptype);
    }
    let mid=null;
    if(opt.inspect) mid=opt.inspect();
    if(opt.esc) document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
    const upEl=at(tx,ty);
    fire(upEl,'up',tx,ty,ptype);
    if(w.isConnected&&(upEl===w||w.contains(upEl))) w.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,clientX:tx,clientY:ty}));
    else { const tb=$('tbody'); tb.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,clientX:tx,clientY:ty})); }
    await settle(); await settle();
    return mid;
  }
  async function dragCols(id,dCols,opt){
    opt=opt||{};
    let w=await reveal(id);
    const ref=opt.toRef||rowOf(w);
    const p=opt.point||cellCentre(ref,colOf(w)+dCols);
    if(!p) throw new Error('no target cell for '+id+' '+dCols);
    return drag(w,p[0],p[1],opt);
  }
  function plainClick(w){
    const [x,y]=centre(w);
    fire(w,'down',x,y); fire(w,'up',x,y);
    w.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,clientX:x,clientY:y}));
  }
  // Bring the marker to the middle of the week cells actually in view: the
  // sticky name column covers the scroller's left part, so scrollIntoView's
  // centre is not the middle of what can be dropped on (at 390 especially).
  async function reveal(id){
    let w=wrapOf(id);
    w.scrollIntoView({block:'center',inline:'center'}); await settle();
    w=wrapOf(id);
    const tr=w.closest('tr.data');
    let sc=tr.parentElement;
    while(sc&&sc!==document.body){ const ox=getComputedStyle(sc).overflowX; if(ox==='auto'||ox==='scroll') break; sc=sc.parentElement; }
    if(sc&&sc!==document.body){
      const nm=tr.querySelector('td.c-name.sticky').getBoundingClientRect().right;
      const sr=sc.getBoundingClientRect();
      const lo=Math.max(nm,sr.left), hi=Math.min(sr.right,innerWidth);
      sc.scrollLeft+=centre(w)[0]-(lo+hi)/2;
      await settle();
    }
    return wrapOf(id);
  }
  function visibleCols(id){ const w=wrapOf(id); return msDragVisibleCols(w.closest('tr.data')).map(c=>c.col); }

  try{
    const st=document.createElement('style'); st.textContent='*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
    await settle(); await settle();
    // Spies: the redraw choke point and the filter pass, counted per drop.
    let depN=0, filtN=0;
    const _dl=window.drawDepLines, _af=window.applyFilter;
    window.drawDepLines=function(){ depN++; return _dl.apply(this,arguments); };
    window.applyFilter=function(){ filtN++; return _af.apply(this,arguments); };

    // ---- picks (N=3) ----
    const onBoard=MILESTONES.filter(m=>{ const id=msId(m); return id&&wrapOf(id)&&dateToCol(m.date)>=2&&dateToCol(m.date)<=NCOLS-4; });
    // A: a true zero-duration milestone (start equal to its finish).
    const A=onBoard.find(m=>m.start&&m.start===m.date&&!msOwnStart(m)&&!m.actual);
    const B=onBoard.find(m=>{ const s=msOwnStart(m); if(!s||m===A) return false;
      const gap=(msDateMs(m.date)-msDateMs(s))/864e5; return gap>=7&&gap<14; });
    const uDate=isoDay(new Date(WE_DATES[Math.min(NOW_COL+4,NCOLS-4)].getTime()-3*864e5));
    const ur=addUserMilestone({name:'Drag probe',date:uDate,type:'MS',state:'FUTURE'});
    scheduleRerender(true); await settle(); await settle();
    const Cid=ur.record&&ur.record.id;
    ck('setup: three milestones picked (no own start, own start, user)', A&&B&&Cid, [A&&msId(A),B&&msId(B),Cid].join(' / '));
    R.notes.picks=[A&&msId(A),B&&msId(B),Cid];
    const aId=msId(A), bId=msId(B);
    const aKey=msKeyFor(A), bKey=msKeyFor(B);
    const aOwn=A.date, aRef=A.ref, aActual=A.actual;

    // ---- clicks ----
    closeCard(); MS_LAST_TAP={key:null,at:0};
    let w=await reveal(aId);
    plainClick(w); await settle();
    ck('click: a plain click still opens the card', cardOpen() && msDialogFor===aKey, msDialogFor);
    closeCard(); await settle(); MS_LAST_TAP={key:null,at:0};
    const collBefore=msCollectionIds().slice();
    w=wrapOf(aId); plainClick(w); await wait(60); w=wrapOf(aId); plainClick(w); await settle();
    ck('click: a double click still collects the ID', msCollectionIds().indexOf(aId)>=0, msCollectionIds().join(','));
    if(collBefore.indexOf(aId)<0) removeFromMsCollection(aId);
    closeCard(); await settle(); MS_LAST_TAP={key:null,at:0};

    // ---- +0: moved past the threshold, released in the same cell ----
    const n0=ENTRIES.length;
    w=await reveal(aId); const [x0,y0]=centre(w);
    const r0=w.closest('td.c-wk').getBoundingClientRect();
    await drag(w,Math.min(x0+8,r0.right-2),y0+1);
    ck('+0: no entry, no date change, same column', ENTRIES.length===n0&&A.date===aOwn&&colOf(wrapOf(aId))===dateToCol(aOwn), ENTRIES.length-n0+' '+A.date);
    ck('+0: the release did not open the card', !cardOpen(), '');
    ck('+0: no toast', !$('ms-drag-toast'), '');

    // ---- +2 ----
    const aCol=colOf(wrapOf(aId));
    const vis=visibleCols(aId);
    R.notes.visibleAtA=vis.join(',');
    ck('+2: the target week is visible to drag onto', vis.indexOf(aCol+2)>=0, vis.join(','));
    depN=0; filtN=0;
    const n1=ENTRIES.length;
    const exp2=addDays(aOwn,14);
    const mid=await dragCols(aId,2,{inspect:function(){
      const g=$('ms-drag-ghost'), l=$('ms-drag-date');
      const c=cellCentre(aRef,aCol+2);
      return {ghost:g&&!g.hidden?[parseFloat(g.style.left),parseFloat(g.style.top)]:null,cell:c,
              label:l?l.textContent:null,labelShown:!!(l&&!l.hidden&&l.getBoundingClientRect().width>0),
              labelRefused:!!(l&&l.classList.contains('is-refused'))};
    }});
    ck('+2 preview: the ghost snaps to the target cell centre', mid.ghost&&mid.cell&&Math.abs(mid.ghost[0]-mid.cell[0])<=1&&Math.abs(mid.ghost[1]-mid.cell[1])<=1, JSON.stringify(mid));
    ck('+2 preview: the label reads the new date and the week delta', mid.labelShown&&mid.label===fmtTipDate(exp2)+' (+2 wk)', mid.label);
    ck('+2 preview: the label is gone after the drop', !$('ms-drag-date'), '');
    ck('+2: m.date moved two weeks, weekday kept', A.date===exp2&&dow(A.date)===dow(aOwn), aOwn+' -> '+A.date);
    w=wrapOf(aId);
    ck('+2: the marker is in the new column, same row', colOf(w)===aCol+2&&rowOf(w)===aRef, colOf(w)+' '+rowOf(w));
    let e=lastEntryOn(aKey);
    ck('+2: one new entry with changes.date', ENTRIES.length===n1+1&&e&&e.changes&&e.changes.date&&e.changes.date.to===exp2&&e.changes.date.from===aOwn, JSON.stringify(e&&e.changes));
    ck('+2: the override is the projection of that entry', MS_FIELD_OVERRIDE[aKey]&&MS_FIELD_OVERRIDE[aKey].date===exp2, JSON.stringify(MS_FIELD_OVERRIDE[aKey]));
    ck('+2: the A flag and the Start are unchanged', A.actual===aActual&&!('actual' in (e.changes||{}))&&!('start' in (e.changes||{})), '');
    ck('+2: the edited mark (*) is on the marker', !!(w&&w.querySelector('.m-board-edit-mark')), '');
    const trA=document.querySelector('#tbody tr.data[data-ref="'+CSS.escape(aRef)+'"]');
    ck('+2: the ghost tick sits at the source week', !!trA.querySelector('td.c-wk[data-col="'+aCol+'"] .m-edit-ghost'), '');
    const toast=$('ms-drag-toast');
    ck('+2: the toast reads "Finish moved to <date>." with Undo', toast&&toast.textContent==='Finish moved to '+fmtTipDate(exp2)+'.Undo'&&toast.querySelector('button'), toast&&toast.textContent);
    ck('+2: dependency lines redrawn and filters reapplied', depN>=1&&filtN>=1, 'drawDepLines '+depN+', applyFilter '+filtN);
    ck('+2: the release did not open the card', !cardOpen(), '');

    // ---- Undo ----
    const n2=ENTRIES.length;
    toast.querySelector('button').click(); await settle(); await settle();
    e=lastEntryOn(aKey);
    ck('undo: the date is back', A.date===aOwn&&colOf(wrapOf(aId))===aCol, A.date);
    ck('undo: by a new entry, history not deleted', ENTRIES.length===n2+1&&e.changes.date.to===null, ENTRIES.length-n2+' '+JSON.stringify(e.changes));
    ck('undo: the toast is gone', !$('ms-drag-toast'), '');
    ck('undo: no edited mark left', !wrapOf(aId).querySelector('.m-board-edit-mark'), '');

    // ---- after a drag dropped elsewhere, a plain click still opens the card ----
    closeCard(); MS_LAST_TAP={key:null,at:0};
    await dragCols(aId,2); closeCard(); MS_LAST_TAP={key:null,at:0};
    w=await reveal(aId);
    plainClick(w); await settle();
    ck('click: after a drop elsewhere, the next plain click still opens the card', cardOpen(), '');
    closeCard(); await settle(); MS_LAST_TAP={key:null,at:0};

    // ---- back to the schedule week clears the override ----
    ck('back: precondition, the marker sits two weeks out', A.date===exp2, A.date);
    const n3=ENTRIES.length;
    await dragCols(aId,-2);
    e=lastEntryOn(aKey);
    ck('back: dropping on the schedule week restores the schedule date', A.date===aOwn&&colOf(wrapOf(aId))===aCol, A.date);
    ck('back: the override is cleared (entry to:null)', !(MS_FIELD_OVERRIDE[aKey]&&'date' in MS_FIELD_OVERRIDE[aKey])&&ENTRIES.length===n3+1&&e.changes.date.to===null, JSON.stringify(e.changes));
    ck('back: no edited mark, no ghost tick', !wrapOf(aId).querySelector('.m-board-edit-mark')&&!trA.isConnected||!document.querySelector('#tbody tr.data[data-ref="'+CSS.escape(aRef)+'"] .m-edit-ghost'), '');
    msDragToastClose();

    // ---- Esc cancels ----
    const n4=ENTRIES.length;
    const midE=await dragCols(aId,2,{esc:true,inspect:function(){ return {active:MS_DRAG.active}; }});
    ck('esc: the drag was live before Esc', midE.active, '');
    ck('esc: nothing moved, no entry', A.date===aOwn&&ENTRIES.length===n4&&colOf(wrapOf(aId))===aCol, A.date);
    ck('esc: ghost hidden, label gone, card not opened', $('ms-drag-ghost').hidden&&!$('ms-drag-date')&&!cardOpen(), '');
    ck('esc: no toast', !$('ms-drag-toast'), '');

    // ---- combined row and column ----
    const rowsA=[...document.querySelectorAll('#tbody tr.data')];
    const iA=rowsA.findIndex(t=>t.getAttribute('data-ref')===aRef);
    const other=rowsA[iA+1]||rowsA[iA-1];
    const toRef=other.getAttribute('data-ref');
    const n5=ENTRIES.length;
    const exp1=addDays(aOwn,7);
    await dragCols(aId,1,{toRef:toRef});
    w=wrapOf(aId);
    ck('combined: the milestone changed row', A.ref===toRef&&rowOf(w)===toRef, A.ref);
    ck('combined: and moved one week', A.date===exp1&&colOf(w)===aCol+1, A.date);
    e=lastEntryOn(msKeyFor(A));
    ck('combined: one date entry, on the milestone\'s key', ENTRIES.length===n5+1&&e.changes.date.to===exp1, JSON.stringify(e&&e.changes));
    ck('combined: edited mark and ghost tick in the new row', !!w.querySelector('.m-board-edit-mark')&&!!w.closest('tr.data').querySelector('td.c-wk[data-col="'+aCol+'"] .m-edit-ghost'), '');
    $('ms-drag-toast').querySelector('button').click(); await settle(); await settle();
    ck('combined undo: row and date both restored', A.ref===aRef&&A.date===aOwn&&rowOf(wrapOf(aId))===aRef&&colOf(wrapOf(aId))===aCol, A.ref+' '+A.date);

    // ---- clamp past the visible weeks ----
    w=await reveal(aId);
    const visC=visibleCols(aId), lastVis=visC[visC.length-1];
    const yA=centre(w)[1];
    await drag(w,innerWidth+400,yA);
    ck('clamp: a drop past the right edge lands in the last visible week', colOf(wrapOf(aId))===lastVis&&A.date===addDays(aOwn,7*(lastVis-aCol)), colOf(wrapOf(aId))+' vs '+lastVis+' '+A.date);
    $('ms-drag-toast').querySelector('button').click(); await settle(); await settle();
    w=await reveal(aId);
    const visL=visibleCols(aId), firstVis=visL[0];
    await drag(w,-400,centre(w)[1]);
    const okL=colOf(wrapOf(aId))===firstVis&&A.date===addDays(aOwn,7*(firstVis-aCol));
    ck('clamp: a drop past the left edge lands in the first visible week', okL, colOf(wrapOf(aId))+' vs '+firstVis+' '+A.date);
    if($('ms-drag-toast')) $('ms-drag-toast').querySelector('button').click();
    await settle(); await settle();
    ck('clamp: undone', A.date===aOwn, A.date);

    // ---- B: a milestone with a start of its own ----
    const bOwn=B.date, bStart=B.start, bCol=colOf(wrapOf(bId)), bRef=B.ref, bActual=B.actual;
    const n6=ENTRIES.length;
    const expB=addDays(bOwn,-7);
    const midB=await dragCols(bId,-1,{inspect:function(){ const l=$('ms-drag-date'); return l&&l.textContent; }});
    ck('B -1 preview: label', midB===fmtTipDate(expB)+' (-1 wk)', midB);
    w=wrapOf(bId);
    ck('B -1: m.date one week earlier, weekday kept, Start unchanged', B.date===expB&&dow(expB)===dow(bOwn)&&B.start===bStart, bOwn+' -> '+B.date+' start '+B.start);
    ck('B -1: the marker is in the new column', colOf(w)===bCol-1&&rowOf(w)===bRef, colOf(w));
    e=lastEntryOn(bKey);
    ck('B -1: an entry with changes.date', ENTRIES.length===n6+1&&e.changes.date.to===expB, JSON.stringify(e.changes));
    ck('B -1: the A flag is unchanged', B.actual===bActual, '');
    ck('B -1: edited mark and ghost tick', !!w.querySelector('.m-board-edit-mark')&&!!w.closest('tr.data').querySelector('td.c-wk[data-col="'+bCol+'"] .m-edit-ghost'), '');
    msDragToastClose();
    // Refusal: far enough left to put the Finish before the Start.
    const gapW=Math.floor((msDateMs(B.date)-msDateMs(bStart))/(7*864e5))+1;
    const n7=ENTRIES.length, dateNow=B.date, colNow=colOf(wrapOf(bId));
    const visB=visibleCols(bId);
    ck('start rule: the refused target week is visible', visB.indexOf(colNow-gapW)>=0, visB.join(',')+' want '+(colNow-gapW));
    const midR=await dragCols(bId,-gapW,{inspect:function(){ const l=$('ms-drag-date'); return {t:l&&l.textContent,r:!!(l&&l.classList.contains('is-refused'))}; }});
    ck('start rule: the preview says it is before the Start', midR.r&&midR.t==='Before Start '+fmtTipDate(bStart), JSON.stringify(midR));
    ck('start rule: the drop is refused, nothing written', B.date===dateNow&&ENTRIES.length===n7&&colOf(wrapOf(bId))===colNow&&B.start===bStart, B.date);
    const tR=$('ms-drag-toast');
    ck('start rule: a brief message says why, without Undo', tR&&/^Not moved: the Finish cannot be before the Start/.test(tR.textContent)&&!tR.querySelector('button'), tR&&tR.textContent);
    msDragToastClose();
    // Both sides of the rule: one week less than the refused move was allowed
    // above (B -1, still on or after the Start), and a zero-duration milestone
    // (start equal to its finish, shown on the card as no start) has no Start
    // of its own to cross, so A's left clamp above moved it earlier.
    ck('start rule: the boundary, one week short of the refused move, was allowed', gapW===1, 'gapW '+gapW);
    ck('start rule: a zero-duration milestone has no own Start to cross', A.start===A.date&&msOwnStart(A)===null&&okL&&firstVis<aCol, A.start+' '+A.date);
    await dragCols(bId,1); msDragToastClose();
    ck('B: back to the schedule week clears its override', B.date===bOwn&&!(MS_FIELD_OVERRIDE[bKey]&&'date' in MS_FIELD_OVERRIDE[bKey]), B.date);

    // ---- C: a user milestone ----
    const C=msOf(Cid), cOwn=C.date, cCol=colOf(wrapOf(Cid));
    const n8=ENTRIES.length;
    const expC=addDays(cOwn,14);
    await dragCols(Cid,2);
    const C2=msOf(Cid); w=wrapOf(Cid);
    ck('USR +2: m.date moved two weeks, weekday kept', C2.date===expC&&dow(expC)===dow(cOwn), cOwn+' -> '+C2.date);
    ck('USR +2: the marker is in the new column', colOf(w)===cCol+2, colOf(w));
    e=lastEntryOn(Cid);
    ck('USR +2: an entry with changes.date on its ID, the path its card uses', ENTRIES.length===n8+1&&e.changes.date.to===expC, JSON.stringify(e.changes));
    ck('USR +2: the user milestone grid reads the new date', userMsGridRow(umsRecord(Cid)).finish===expC, userMsGridRow(umsRecord(Cid)).finish);
    ck('USR +2: no edited mark (D-18: a user milestone has no source to differ from)', !w.querySelector('.m-board-edit-mark'), '');
    $('ms-drag-toast').querySelector('button').click(); await settle(); await settle();
    ck('USR undo: back to its own date', msOf(Cid).date===cOwn&&colOf(wrapOf(Cid))===cCol, msOf(Cid).date);

    // ---- touch: press and hold, then drag ----
    const n9=ENTRIES.length;
    await dragCols(aId,1,{touch:true});
    ck('touch: press-and-hold drag moves the column too', A.date===addDays(aOwn,7)&&colOf(wrapOf(aId))===aCol+1&&ENTRIES.length===n9+1, A.date);
    if($('ms-drag-toast')) $('ms-drag-toast').querySelector('button').click();
    await settle(); await settle();

    // ---- the toast times out ----
    await dragCols(aId,1);
    ck('toast: shown after a drop', !!$('ms-drag-toast'), '');
    await wait(MS_DRAG_TOAST_MS+300);
    ck('toast: gone after about 4 seconds', !$('ms-drag-toast'), '');
    await dragCols(aId,-1); msDragToastClose();
    ck('end: A back on its schedule date', A.date===aOwn, A.date);

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
        tmp = pathlib.Path(td) / "p75d.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=120000",
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
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal",
                   len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))
    checks.append(("source: the drop writes the date through addFieldEntry, never the store",
                   "addFieldEntry(msKeyFor(ms),'date'" in src and "MS_FIELD_OVERRIDE[msKeyFor(ms)]=" not in src, ""))
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        print(f"\n=== {w}x{h} ===  notes {json.dumps(R.get('notes', {}))}")
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
