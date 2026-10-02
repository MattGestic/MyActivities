#!/usr/bin/env python3
"""P75 check: the week-range picker's second click, and the Import panel.

Matt, 2026-10-02 (desktop screenshots):
  1. the week-range picker would not take an end week: a first click set the
     start, a second click on another week did nothing, and the head read
     "W/E06 Sep 26->06 Sep 26";
  2. the Import button looked inactive at "Ready to import" after a paste;
  3. the Import tab reordered: Import a schedule, Map columns, Source, then
     Import date range (the data date and report date above the range filter);
  4. the paste box cleared after a successful import.

Root cause of 1: every hover rebuilt the popover, replacing the week cell under
the pointer; Chromium then fires mouseenter on the new cell, which rebuilt it
again, so with a start picked the grid churned while the pointer rested on a
week, and a click whose mousedown and mouseup land on two different cells is
not dispatched to either. A synthetic .click() on a held element does not
reproduce that, so the picker probe drives a small pointer model: it keeps a
pointer position, re-hit-tests it after every event and fires mouseenter on
whatever is now under it (as Chromium does when the node under a resting
pointer is replaced), and dispatches click only when mousedown and mouseup hit
the same connected element. Against the P74 file it fails; against the fix it
passes.

Runs:
  - picker at 1440x900 and 390x844, with the test fixture (the board data):
    N=3 ranges by real pointer clicks (the same week, adjacent weeks, across a
    month boundary) plus an earlier second week (swaps), Show only on one of
    them, Cancel and Escape; checks the popover head, the in-range highlight,
    WR_POP_STATE, the field text, currentWeekRange() and the board columns;
  - import, the app as it ships (sret:no-fixture), at 1440x900:
      file:  the real .xlsx bytes through handleFile() and the embedded
             SheetJS (data/schedules/...DD-2026-08-29.xlsx);
      paste: the same export as TSV (tools/import_check.py build_aoa) through
             the paste box and "Parse pasted data";
    each checks Import is enabled (disabled, aria-disabled, computed style,
    the primary look, nothing on top of it), that a click imports, and that
    the paste box is empty afterwards; the file run also checks the panel's
    order, headings, badges and where the two dates sit.

    python3 tools/p75_import_check.py [--html FILE]
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
OPT_OUT = "<!-- sret:no-fixture: P75 imports into the app as it ships -->"
EARLY = r"""<script>
window.__errs=[];
addEventListener('error',function(e){ if(/^ResizeObserver loop/.test(e.message||'')) return; __errs.push('error: '+e.message+' @'+e.lineno); });
(function(){ var o=console.error; console.error=function(){ __errs.push('console.error: '+Array.prototype.join.call(arguments,' ')); return o.apply(console,arguments); }; })();
</script>"""

COMMON = r"""
const R={checks:[],notes:{}};
const TAG=__TAG__;
function ck(n,p,d){ R.checks.push({name:TAG+': '+n,pass:!!p,detail:d===undefined?'':String(d).slice(0,400)}); }
function emit(){ R.errs=window.__errs.slice(); const o=document.createElement('pre'); o.id='p75-out';
  o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
const settle=(ms)=>new Promise(r=>setTimeout(r,ms||250));
const $=id=>document.getElementById(id);
const txt=el=>el?el.textContent.replace(/\s+/g,' ').trim():'';
"""

PICKER = r"""<script>
(function(){
""" + COMMON + r"""
// ---- pointer model (see the module docstring) ----
const PTR={x:-1,y:-1,el:null};
function hit(){ return document.elementFromPoint(PTR.x,PTR.y); }
function fire(el,type){ el.dispatchEvent(new MouseEvent(type,{bubbles:type!=='mouseenter',cancelable:true,clientX:PTR.x,clientY:PTR.y,view:window})); }
// Re-hit-test until the node under the pointer stops changing. Returns how
// many times it changed: a grid that rebuilds under a resting pointer never
// stops, and is capped.
function settlePointer(){
  let n=0;
  for(;n<25;n++){
    const h=hit();
    if(h===PTR.el) break;
    PTR.el=h;
    if(h){ fire(h,'mouseover'); fire(h,'mouseenter'); }
  }
  return n;
}
function moveTo(el){
  const r=el.getBoundingClientRect();
  PTR.x=r.left+r.width/2; PTR.y=r.top+r.height/2;
  return settlePointer();
}
let CHURN=0, LOST=0;
function clickAt(el){
  CHURN=Math.max(CHURN,moveTo(el));
  const down=hit(); if(!down) return false;
  fire(down,'mousedown');
  CHURN=Math.max(CHURN,settlePointer());
  const up=hit(); if(!up) return false;
  fire(up,'mouseup');
  if(down===up&&down.isConnected){ down.click(); CHURN=Math.max(CHURN,settlePointer()); return true; }
  LOST++; // Chromium sends the click to a common ancestor, never to either cell
  return false;
}
const cell=c=>document.querySelector('#wr-pop-el .wr-wk[data-col="'+c+'"]');
const fmt=d=>String(d.getDate()).padStart(2,'0')+' '+MONTH_NAMES[d.getMonth()]+' '+String(d.getFullYear()).slice(2);
function openPicker(){
  const f=$('wr-field');
  if(f&&f.getBoundingClientRect().width>0){ f.click(); } else { openWeekRangePopover(); }
}
function markedWeeks(){ return document.querySelectorAll('th.filter-wk').length; }
function shownWeekCols(){
  return Array.prototype.filter.call(document.querySelectorAll('th.col-wk[data-col]'),function(th){ return getComputedStyle(th).display!=='none'; })
    .map(function(th){ return +th.getAttribute('data-col'); });
}
async function pickRange(name,a,b,expLo,expHi){
  openPicker(); await settle();
  const pop=$('wr-pop-el');
  ck(name+': the popover opens', !!pop);
  if(!pop) return;
  const ca=cell(a), cb=cell(b);
  ck(name+': both weeks are on screen in the popover', !!ca&&!!cb&&ca.getBoundingClientRect().bottom<=innerHeight&&cb.getBoundingClientRect().bottom<=innerHeight,
     ca&&cb?Math.round(ca.getBoundingClientRect().bottom)+'/'+Math.round(cb.getBoundingClientRect().bottom)+' of '+innerHeight:'missing');
  CHURN=0; LOST=0;
  clickAt(ca); await settle(60);
  const s1=Object.assign({},WR_POP_STATE);
  ck(name+': the first click sets the start', s1.startCol===a&&s1.lo===a&&s1.hi==null, JSON.stringify(s1));
  ck(name+': with the pointer resting on the start, the head asks for the end week',
     /^Start \d\d \w{3} \d\d/.test(txt(pop.querySelector('.wr-head')))&&/Pick an end week/.test(txt(pop.querySelector('.wr-head'))), txt(pop.querySelector('.wr-head')));
  ck(name+': the start cell is the same node after the click (no rebuild under the pointer)', cell(a)===ca&&ca.isConnected);
  if(a!==b){
    CHURN=Math.max(CHURN,moveTo(cb)); await settle(60);
    const lo=Math.min(a,b), hi=Math.max(a,b);
    ck(name+': hovering the end previews the range', WR_POP_STATE.hoverCol===b&&pop.querySelectorAll('.wr-wk.preview').length===Math.max(0,hi-lo-1),
       JSON.stringify(WR_POP_STATE)+' preview='+pop.querySelectorAll('.wr-wk.preview').length);
  }
  clickAt(cell(b)); await settle(60);
  const s2=Object.assign({},WR_POP_STATE);
  ck(name+': the second click sets the end', s2.startCol==null&&s2.lo===expLo&&s2.hi===expHi, JSON.stringify(s2));
  ck(name+': no click was lost, and the grid settles under a resting pointer', LOST===0&&CHURN<3, 'lost='+LOST+' churn='+CHURN);
  const n=expHi-expLo+1;
  const head=txt(pop.querySelector('.wr-head'));
  const want='W/E '+fmt(WE_DATES[expLo])+' → '+fmt(WE_DATES[expHi]);
  ck(name+': the head reads the range, with a space after W/E', head.indexOf(want)===0&&head.indexOf(n+' wk'+(n===1?'':'s'))>0, head+' | want '+want);
  const hv=pop.querySelector('.wr-head .wr-val'), hcs=hv&&getComputedStyle(hv);
  ck(name+': the head lays out tag, dates and arrow with a gap', !!hcs&&/flex/.test(hcs.display)&&parseFloat(hcs.columnGap)>0, hcs?hcs.display+' '+hcs.columnGap:'');
  const ends=Array.from(pop.querySelectorAll('.wr-wk.end')).map(e=>+e.dataset.col);
  const ins=Array.from(pop.querySelectorAll('.wr-wk.in')).map(e=>+e.dataset.col);
  ck(name+': the start and end are marked, and every week between them is highlighted',
     JSON.stringify(ends)===JSON.stringify(expLo===expHi?[expLo]:[expLo,expHi])&&ins.length===Math.max(0,n-2)&&ins.every(c=>c>expLo&&c<expHi),
     'ends='+JSON.stringify(ends)+' in='+ins.length);
  ck(name+': the marked ends read as pressed', Array.from(pop.querySelectorAll('.wr-wk.end')).every(e=>e.getAttribute('aria-pressed')==='true'));
  const ap=$('wr-apply-btn');
  ck(name+': Apply is enabled', !!ap&&!ap.disabled);
  clickAt(ap); await settle();
  ck(name+': Apply closes the popover', !$('wr-pop-el')&&WR_POP_STATE===null);
  const r=currentWeekRange();
  ck(name+': the applied range is the picked one', !!r&&r.lo===expLo&&r.hi===expHi&&!r.open, JSON.stringify(r));
  const ft=txt($('wr-field'));
  ck(name+': the field shows the same range', ft.indexOf(want)>=0&&ft.indexOf(n+' wk'+(n===1?'':'s'))>=0, ft);
  return {lo:expLo,hi:expHi,n:n};
}
setTimeout(async function(){
 try{
  const st=document.createElement('style'); st.textContent='*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
  await settle();
  ck('boot: a board with weeks', WE_DATES.length>20, WE_DATES.length);
  setWeekFilterModeUI('highlight',true);
  // A month boundary near the top of the grid: the first column whose month
  // differs from the one before it, at least two weeks in.
  let mb=-1; for(let i=3;i<WE_DATES.length-3;i++){ if(WE_DATES[i].getMonth()!==WE_DATES[i-1].getMonth()){ mb=i; break; } }
  ck('setup: a month boundary to cross', mb>0, mb);
  const ranges=[];
  // 1. the same week twice: a one-week range
  let g=await pickRange('same week',2,2,2,2); ranges.push(g);
  ck('same week: the board marks exactly one week', markedWeeks()===1, markedWeeks());
  // 2. adjacent weeks
  g=await pickRange('adjacent weeks',5,6,5,6); ranges.push(g);
  ck('adjacent weeks: the board marks the two weeks', markedWeeks()===2&&Array.from(document.querySelectorAll('th.filter-wk')).map(t=>+t.dataset.col).join()==='5,6',
     Array.from(document.querySelectorAll('th.filter-wk')).map(t=>t.dataset.col).join());
  // 3. across a month boundary, in Show only: the board narrows to it
  setWeekFilterModeUI('only',true);
  g=await pickRange('across a month boundary',mb-1,mb+1,mb-1,mb+1); ranges.push(g);
  const shown=shownWeekCols();
  ck('across a month boundary: the two weeks are in different months', WE_DATES[mb-1].getMonth()!==WE_DATES[mb+1].getMonth());
  ck('across a month boundary: Show only narrows the board to the three weeks', shown.join()===[mb-1,mb,mb+1].join(), shown.join());
  ck('three different ranges were applied', ranges.length===3&&new Set(ranges.map(x=>x.lo+'-'+x.hi)).size===3, JSON.stringify(ranges));
  setWeekFilterModeUI('highlight',true);
  // 4. an earlier second week swaps: it becomes the start
  await pickRange('earlier second week',9,7,7,9);
  ck('earlier second week: the board marks weeks 7 to 9', markedWeeks()===3);
  // Cancel and Escape keep the applied range.
  openPicker(); await settle();
  clickAt(cell(12)); clickAt(cell(14)); await settle(60);
  clickAt(Array.from($('wr-pop-el').querySelectorAll('.wr-foot .ds-btn')).find(b=>b.textContent==='Cancel')); await settle();
  let r=currentWeekRange();
  ck('cancel: closes and keeps the applied range', !$('wr-pop-el')&&r&&r.lo===7&&r.hi===9, JSON.stringify(r));
  openPicker(); await settle();
  ck('reopen: the applied range is shown as the selection', WR_POP_STATE.lo===7&&WR_POP_STATE.hi===9&&$('wr-pop-el').querySelectorAll('.wr-wk.end').length===2);
  clickAt(cell(12)); await settle(60);
  document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
  await settle();
  r=currentWeekRange();
  ck('escape: closes and keeps the applied range', !$('wr-pop-el')&&r&&r.lo===7&&r.hi===9, JSON.stringify(r));
  // Keyboard: Enter on a week picks it rather than applying.
  openPicker(); await settle();
  const k1=cell(3); k1.focus(); k1.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true})); await settle(60);
  ck('keyboard: Enter on a week picks it as the start, the popover stays open', !!$('wr-pop-el')&&WR_POP_STATE&&WR_POP_STATE.startCol===3, JSON.stringify(WR_POP_STATE));
  ck('keyboard: focus stays on that week', document.activeElement===k1);
  const k2=cell(4); k2.focus(); k2.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true})); await settle(60);
  ck('keyboard: Enter on a second week sets the end', WR_POP_STATE&&WR_POP_STATE.lo===3&&WR_POP_STATE.hi===4, JSON.stringify(WR_POP_STATE));
  closeWeekRangePopover(); clearWeekRange(); await settle();
  ck('clear: no range afterwards', currentWeekRange()===null);
  ck('no console errors', window.__errs.length===0, window.__errs.join(' | '));
 }catch(e){ ck('probe ran to the end', false, String(e&&e.stack||e)); }
 emit();
},2500);
})();
</script>"""

IMPORT = r"""<script>
(function(){
""" + COMMON + r"""
const MODE=__MODE__, XB64=__XB64__, TSV=__TSV__, EXP=__EXP__;
window.confirm=function(){ return true; }; window.alert=function(){};
function bgOf(v){ const sp=document.createElement('span'); sp.style.background='var('+v+')'; document.body.appendChild(sp); const c=getComputedStyle(sp).backgroundColor; sp.remove(); return c; }
function steps(){ return Array.from($('import-sect').querySelectorAll('.sd-step')); }
function before(a,b){ return !!(a.compareDocumentPosition(b)&Node.DOCUMENT_POSITION_FOLLOWING); }
async function importButtonChecks(path){
  const b=$('import-run-btn');
  ck(path+': the summary reads Ready to import', /Ready to import/.test(txt($('import-summary-wrap'))), txt($('import-summary-wrap')));
  ck(path+': an Import button is there', !!b&&b.textContent.trim()==='Import');
  if(!b) return;
  ck(path+': Import is enabled (disabled false, aria-disabled false)', b.disabled===false&&b.getAttribute('aria-disabled')==='false', b.disabled+'/'+b.getAttribute('aria-disabled'));
  b.scrollIntoView({block:'center'}); await settle(80);
  const cs=getComputedStyle(b), r=b.getBoundingClientRect();
  ck(path+': Import is not dimmed or click-through', cs.opacity==='1'&&cs.pointerEvents!=='none'&&cs.cursor==='pointer'&&cs.visibility==='visible', cs.opacity+' '+cs.pointerEvents+' '+cs.cursor);
  ck(path+': Import has the primary look (the primary fill, as the empty state’s Import schedule)',
     cs.backgroundColor===bgOf('--color-btn-primary-bg')&&b.classList.contains('primary')&&b.classList.contains('ds-btn'), cs.backgroundColor+' vs '+bgOf('--color-btn-primary-bg'));
  ck(path+': Import is a full-size control, not a 10px chip', parseFloat(cs.fontSize)>=11&&r.height>=22, cs.fontSize+' '+Math.round(r.height)+'px');
  const top=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
  ck(path+': nothing sits on top of Import', top===b, top?(top.id||top.className||top.tagName):'null');
  // The negative: no Finish mapped, Import is off and says so both ways.
  const fin=$('map-finish'), keep=fin.value;
  fin.value='-1'; fin.dispatchEvent(new Event('change',{bubbles:true})); await settle(60);
  const b2=$('import-run-btn');
  ck(path+': with Finish unmapped Import is disabled, both ways', b2.disabled===true&&b2.getAttribute('aria-disabled')==='true'&&/Finish column must be mapped/.test(txt($('import-summary-wrap'))));
  fin.value=keep; fin.dispatchEvent(new Event('change',{bubbles:true})); await settle(60);
  ck(path+': mapped again, Import is enabled again', $('import-run-btn').disabled===false&&$('import-run-btn').getAttribute('aria-disabled')==='false');
}
async function clickImport(path){
  $('import-run-btn').click();
  await settle(); await settle();
  ck(path+': a click imports the schedule', TASKS.length===EXP.tasks&&MILESTONES.length===EXP.ms, TASKS.length+'/'+MILESTONES.length+' want '+EXP.tasks+'/'+EXP.ms);
  ck(path+': the form is put away', !LAST_PARSE&&$('import-summary-wrap').innerHTML===''&&!$('import-run-btn'));
  ck(path+': the paste box is empty afterwards', $('paste-box').value==='', JSON.stringify($('paste-box').value.slice(0,40)));
}
setTimeout(async function(){
 try{
  const st=document.createElement('style'); st.textContent='*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
  ck('boot: the empty app, nothing seeded', typeof window.__SRET_FIXTURE__==='undefined'&&TASKS.length===0, TASKS.length);
  setSettingsTab('import'); toggleSettingsDrawer(true); await settle();
  ck('before a file: no Import button yet', !$('import-run-btn'));
  if(MODE==='file'){
    // ---- panel: order, headings, badges, where the dates sit ----
    const S=steps();
    ck('panel: the four steps in the new order', S.map(s=>s.id).join()==='ingest-bar,map-wrap-section,source-wrap-section,import-dates-section', S.map(s=>s.id).join());
    ck('panel: numbered 1 to 4', S.map(s=>txt(s.querySelector('.sd-step-num'))).join()==='1,2,3,4', S.map(s=>txt(s.querySelector('.sd-step-num'))).join());
    ck('panel: headings Import a schedule, Map columns, Source, Import date range',
       S.map(s=>txt(s.querySelector('.sd-step-name'))).join('|')==='Import a schedule|Map columns|Source|Import date range', S.map(s=>txt(s.querySelector('.sd-step-name'))).join('|'));
    ck('panel: badges Required, Once a file loads, Once a file loads, Optional',
       S.map(s=>txt(s.querySelector('.sd-step-hd .sd-badge'))).join('|')==='Required|Once a file loads|Once a file loads|Optional', S.map(s=>txt(s.querySelector('.sd-step-hd .sd-badge'))).join('|'));
    const sec4=$('import-dates-section');
    ck('panel: step 4 carries the subheader "Filter import date range"', txt($('import-dates-sub'))==='Filter import date range'&&sec4.contains($('import-dates-sub')));
    const dd=$('cfg-datadate-main'), rd=$('cfg-reportdate'), rw=$('range-wrap-section');
    ck('panel: the data date and the report date are in step 4', sec4.contains(dd)&&sec4.contains(rd));
    ck('panel: neither is in step 1 any more', !$('ingest-bar').contains(dd)&&!$('ingest-bar').contains(rd));
    ck('panel: both sit above the range filter, data date first', before(dd,rd)&&before(rd,rw)&&sec4.contains(rw));
    ck('panel: the range filter keeps its text and controls', /Left blank, the board spans the imported schedule/.test(txt($('range-note')))&&
       rw.contains($('cfg-range-from'))&&rw.contains($('cfg-range-to'))&&rw.contains($('btn-range-reset'))&&/Board span/.test(txt(rw)));
    ck('panel: step 1 holds the file and the paste box', $('ingest-bar').contains($('sched-file'))&&$('ingest-bar').contains($('paste-box')));
    ck('panel: step 4 and its dates are on screen before a file, the range filter is not',
       getComputedStyle(sec4).display!=='none'&&dd.getBoundingClientRect().width>0&&rd.getBoundingClientRect().width>0&&getComputedStyle(rw).display==='none');
    ck('panel: before a file, step 1 is current and the rest wait', S[0].classList.contains('is-current')&&S.slice(1).every(s=>s.classList.contains('is-waiting')),
       S.map(s=>s.className).join(' | '));
    // The moved fields keep their handlers.
    dd.value='2026-08-29'; dd.dispatchEvent(new Event('change',{bubbles:true})); await settle(60);
    ck('panel: the data date still writes the import’s data date', $('cfg-datadate').value==='2026-08-29', $('cfg-datadate').value);
    rd.value='2026-09-04'; rd.dispatchEvent(new Event('change',{bubbles:true})); await settle(60);
    ck('panel: the report date still sets the report date', isoDay(REPORT_META.reportDate)==='2026-09-04', isoDay(REPORT_META.reportDate));
    // ---- the real file, through handleFile and the embedded SheetJS ----
    const bin=atob(XB64), u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i);
    const file=new File([u],'103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx',{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    handleFile({files:[file]});
    for(let i=0;i<40&&!$('import-run-btn');i++) await settle(150);
    ck('file: the workbook parses to the export’s rows', LAST_PARSE&&LAST_PARSE.rows.length===EXP.rows, LAST_PARSE?LAST_PARSE.rows.length:'no parse');
    const S2=steps();
    ck('panel: with a file, steps 1 to 3 read done and step 4 is current',
       S2.slice(0,3).every(s=>s.classList.contains('is-done'))&&S2[3].classList.contains('is-current')&&getComputedStyle(rw).display!=='none', S2.map(s=>s.className).join(' | '));
    await importButtonChecks('file');
    await clickImport('file');
    setSettingsTab('import'); await settle(60);
    ck('panel: after the import the range filter is put away, the dates stay', getComputedStyle(rw).display==='none'&&dd.getBoundingClientRect().width>0&&rd.getBoundingClientRect().width>0);
  } else {
    // ---- the pasted export, through the paste box ----
    togglePaste(); await settle(60);
    $('paste-box').value=TSV;
    const parseBtn=Array.from($('paste-wrap').querySelectorAll('button')).find(b=>/Parse pasted data/.test(b.textContent));
    parseBtn.click(); await settle();
    ck('paste: the pasted export parses to its rows', LAST_PARSE&&LAST_PARSE.rows.length===EXP.rows, LAST_PARSE?LAST_PARSE.rows.length:'no parse');
    await importButtonChecks('paste');
    await clickImport('paste');
    // A second Parse finds nothing to reuse.
    parseBtn.click(); await settle();
    ck('paste: a second Parse after the import finds the box empty and stages nothing',
       !LAST_PARSE&&!$('import-run-btn')&&/Paste box is empty/.test(txt($('ingest-status'))), txt($('ingest-status')));
  }
  ck('no console errors', window.__errs.length===0, window.__errs.join(' | '));
 }catch(e){ ck('probe ran to the end', false, String(e&&e.stack||e)); }
 emit();
},2500);
})();
</script>"""


def page_with(html, probe, opt_out):
    page = html.replace("<head>", "<head>" + EARLY, 1)
    i = page.rindex("</body>")
    return page[:i] + (OPT_OUT + "\n" if opt_out else "") + probe + "\n" + page[i:]


def run(page, size):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p75.html"
        f.write_text(page, encoding="utf-8")
        p = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                            f"--user-data-dir={td}/prof", f"--window-size={size[0]},{size[1]}",
                            "--virtual-time-budget=90000", "--dump-dom", f.as_uri()],
                           capture_output=True, text=True, timeout=300)
    m = re.search(r'<pre id="p75-out">(.*?)</pre>', p.stdout, re.S)
    if not m:
        return {"checks": [{"name": "probe output found", "pass": False, "detail": p.stderr[-800:]}]}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def to_tsv(aoa):
    """The export as Excel copies it, except that the header's line breaks
    (the file's own "\nActivity ID\n") are flattened; body cells keep their
    leading spaces, which carry the WBS depth."""
    def cell(v, head):
        s = "" if v is None else str(v)
        return re.sub(r"\s+", " ", s).strip() if head else re.sub(r"[\t\r\n]+", " ", s)
    return "\n".join("\t".join(cell(v, i == 0) for v in row) for i, row in enumerate(aoa)) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()
    html = pathlib.Path(a.html).read_text(encoding="utf-8")
    aoa = build_aoa(XLSX)
    rows = sum(1 for r in aoa[1:] if any(str(v or "").strip() for v in r))
    exp = {"rows": rows, "tasks": 105, "ms": 146}
    checks = []
    for size in [(1440, 900), (390, 844)]:
        tag = f"picker {size[0]}"
        probe = PICKER.replace("__TAG__", json.dumps(tag))
        checks += run(page_with(html, probe, False), size)["checks"]
    for mode in ["file", "paste"]:
        probe = (IMPORT.replace("__TAG__", json.dumps("import " + mode))
                 .replace("__MODE__", json.dumps(mode))
                 .replace("__EXP__", json.dumps(exp))
                 .replace("__TSV__", json.dumps(to_tsv(aoa)) if mode == "paste" else "''")
                 .replace("__XB64__", json.dumps(base64.b64encode(XLSX.read_bytes()).decode()) if mode == "file" else "''"))
        checks += run(page_with(html, probe, True), (1440, 900))["checks"]
    fails = 0
    for c in checks:
        fails += not c["pass"]
        print(("PASS " if c["pass"] else "FAIL ") + c["name"] + ("" if c["pass"] or not c["detail"] else "  [" + c["detail"] + "]"))
    print(f"{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
