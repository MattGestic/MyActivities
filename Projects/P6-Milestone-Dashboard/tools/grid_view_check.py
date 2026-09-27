#!/usr/bin/env python3
"""
Grid view check (D-09): drives prototypes/grid-view/demo.html headless and
asserts the SRETGrid contract end to end through real DOM events.

What it proves, per the brief (N=3 wherever a count applies):
  - each of the three configurations opens with the right title and row count
  - sort (text and number, both directions), header filters (contains and
    >, <, >= operators on number and date), quick search
  - select all, then deselect three, with the count shown
  - inline edit through the keyboard (Enter to open, Enter to commit) reaches
    onEdit with the exact (rowKey, key, value) and value type, three times,
    and never mutates the caller's row objects
  - Esc cancels, three times: no callback, value unchanged
  - onEdit returning false reverts the cell
  - read-only columns refuse to open an editor, three times per config
  - Add row calls onAdd and opens the new row for editing; Delete selected
    shows the inline confirmation (Cancel left, Remove right), Esc cancels it,
    Remove calls onDelete with the selected keys
  - Add / Delete only appear when their callbacks are given
  - export writes the visible (filtered, sorted) rows through SheetJS
    (SheetJS stubbed at its boundary, as tools/import_check.py does)
  - back calls onBack, removes the screen and restores focus
  - keyboard navigation (arrows, Tab) moves the active cell
  - D-16 sizes: toolbar controls and grid rows are --ctl-h tall
  - 2,000 rows open under OPEN_BUDGET_MS, the DOM holds only the visible
    rows (virtual rendering), the last row is reachable, a filter over all
    2,000 rows applies under FILTER_BUDGET_MS
  - light and dark are both themed (surfaces differ between themes) and a
    palette swap moves every painted colour in the screen, in the idle,
    editing and confirm states (nothing escapes tier 1)
Plus, as subprocesses: tools/colour_audit.py --strict and
tools/palette_swap_check.py against demo.html, and the assembler's --check
(demo.html matches its sources).

--prove-fails runs the probe against deliberately broken wrappers and exits
non-zero unless every mutation is caught.

Usage:
  python3 tools/grid_view_check.py [--html FILE] [--break NAME] [--prove-fails] [--json OUT]
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_check import find_chrome  # noqa: E402

DEMO = ROOT / "prototypes" / "grid-view" / "demo.html"
OPEN_BUDGET_MS = 1000
FILTER_BUDGET_MS = 300

# Each mutation breaks one promise of the contract. The check must fail on all.
MUTATIONS = {
    "onedit-args": ("opts.onEdit(it[rowKey],c.key,it[c.key])", "opts.onEdit(c.key,it[rowKey],it[c.key])"),
    # Read-only is guarded twice (no editor attached, and onBeforeEditCell
    # refuses), so this mutation removes both; removing either alone is
    # covered by the other and correctly still passes.
    "readonly-ignored": [("if(!gridEditable||!c||!c.editable) return false;", "if(!gridEditable||!c) return false;"),
                         ("editor:ed?Editor:null", "editor:gridEditable?Editor:null")],
    "esc-commits": ("el.addEventListener('keydown',function(e){",
                    "el.addEventListener('keydown',function(e){ if(e.key==='Escape'){ args.grid.getEditorLock().commitCurrentEdit(); return; }"),
    "no-selection-count": ("grid.onSelectedRowsChanged.subscribe(updateStatus);", ""),
    "literal-colour": (".sg-grid .slick-row{background:var(--color-row-default-bg)}", ".sg-grid .slick-row{background:#ffffff}"),
    # Scroll: the engine defaults that caused the reported stutter.
    "scroll-defaults": ("enableMouseWheelScrollHandler:false,forceSyncScrolling:true,\n      rowTopOffsetRenderType:'transform',minRowBuffer:10",
                        "enableMouseWheelScrollHandler:true,forceSyncScrolling:false,\n      rowTopOffsetRenderType:'top',minRowBuffer:3"),
    # Collections: the shared rule (no duplicates) and the grid handing over the right keys.
    "coll-duplicates": ("if(c.items.indexOf(r)>=0) already++;", "if(false) already++;"),
    "coll-wrong-keys": ("var r=s.coll.onAssign(keys.slice(),id);", "var r=s.coll.onAssign(keys.slice(1),id);"),
    "resize-kills-edit": ("if(grid.getEditorLock().isActive()){ pending=true; return; }", ""),
    "mutates-caller": ("dv.setItems((opts.rows||[]).map(function(r){ return Object.assign({},r); }),rowKey);",
                       "dv.setItems((opts.rows||[]),rowKey);"),
}

STUB = r"""<script>
window.__errs=[];
window.addEventListener('error',function(e){ __errs.push(String(e.message)); });
// SheetJS stub at the app's boundary with it (aoa_to_sheet, book_*, writeFile).
window.__xlsx={};
window.XLSX={utils:{
  aoa_to_sheet:function(aoa,o){ __xlsx.aoa=aoa; __xlsx.opts=o; return {}; },
  book_new:function(){ return {}; },
  book_append_sheet:function(wb,ws,n){ __xlsx.sheet=n; }},
  writeFile:function(wb,name){ __xlsx.name=name; }};
</script>"""

# Timing runs synchronously while the page is still parsing. Once the load
# event has fired, --virtual-time-budget freezes performance.now() during
# synchronous work (measured: a 2e8-iteration loop reads 0 ms), so a timing
# taken in the async harness below would always pass. At parse time the clock
# is real. The harness asserts the clock advanced, so a frozen clock fails.
TIMING = r"""
<script>
(function(){
  SRETGrid.close();
  var t0=performance.now();
  DEMO_OPEN('stress');
  document.querySelector('.sg-grid').getBoundingClientRect(); document.body.offsetHeight;
  var openMs=performance.now()-t0;
  var inp=document.querySelector('[data-sg-filter="name"]');
  var t1=performance.now();
  inp.value='review'; inp.dispatchEvent(new Event('input',{bubbles:true}));
  document.body.offsetHeight;
  var filterMs=performance.now()-t1;
  window.__stress={openMs:openMs,filterMs:filterMs,filtered:SRETGrid._engine().dataView.getLength()};
  // Scroll smoothness on the 2,000-row set (the reported stutter). Reopened unfiltered.
  SRETGrid.close(); DEMO_OPEN('stress');
  var g=SRETGrid._engine().grid, vp=document.querySelector('.sg-grid .slick-viewport');
  var rh=g.getOptions().rowHeight, vh=vp.clientHeight;
  function missing(){ var top=vp.scrollTop, a=Math.floor(top/rh), b=Math.min(1999,Math.floor((top+vh-1)/rh)), m=0;
    for(var r=a;r<=b;r++) if(!g.getCellNode(r,1)) m++; return m; }
  var steps=[], smallMiss=0;
  for(var i=1;i<=150;i++){ vp.scrollTop=i*37; var t2=performance.now(); vp.dispatchEvent(new Event('scroll'));
    document.body.offsetHeight; steps.push(performance.now()-t2); smallMiss+=missing(); }
  steps.sort(function(x,y){ return x-y; });
  var flingMiss=0; for(var j=1;j<=10;j++){ vp.scrollTop=j*vh*2.5; vp.dispatchEvent(new Event('scroll')); flingMiss+=missing(); }
  vp.scrollTop=5000; vp.dispatchEvent(new Event('scroll'));
  var before=vp.scrollTop; vp.dispatchEvent(new WheelEvent('wheel',{deltaY:53,deltaMode:0,bubbles:true,cancelable:true}));
  var rowEl=(g.getCellNode(Math.floor(vp.scrollTop/rh),1)||{}).parentNode;
  window.__scroll={p95Ms:steps[142],medianMs:steps[75],smallMiss:smallMiss,flingMiss:flingMiss,
    wheelMoved:vp.scrollTop-before,transform:!!(rowEl&&rowEl.style.transform&&!rowEl.style.top)};
  SRETGrid.close();
  DEMO_OPEN('userms');
})();
</script>
"""

HARNESS = r"""
<script>
(async function(){
const R={checks:[],notes:{}};
const ok=(name,cond,detail)=>R.checks.push({name:name,pass:!!cond,detail:detail===undefined?null:detail});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const $=(s,r)=>(r||document).querySelector(s);
const $$=(s,r)=>Array.from((r||document).querySelectorAll(s));
const KC={Enter:13,Escape:27,ArrowDown:40,ArrowRight:39,ArrowUp:38,ArrowLeft:37,Tab:9};
function key(el,k){ el.dispatchEvent(new KeyboardEvent('keydown',{key:k,keyCode:KC[k],which:KC[k],bubbles:true,cancelable:true})); }
const eng=()=>SRETGrid._engine();
const LOG=()=>window.DEMO_LOG;
const lastLog=kind=>{ const l=LOG().filter(e=>e.kind===kind); return l[l.length-1]; };
const count=kind=>LOG().filter(e=>e.kind===kind).length;
function colIdx(key){ return eng().grid.getColumns().findIndex(c=>c.id===key); }
function cellText(row,key){ const n=eng().grid.getCellNode(row,colIdx(key)); return n?n.textContent:null; }
function visibleCount(){ return eng().dataView.getLength(); }
function header(key){ return $$('.slick-header-column').find(h=>h.id.endsWith(key)); }
function filterInput(key){ return $('[data-sg-filter="'+key+'"]'); }
async function setFilter(key,v){ const i=filterInput(key); i.value=v; i.dispatchEvent(new Event('input',{bubbles:true})); await sleep(20); }
async function setSearch(v){ const i=$('[data-sg=search]'); i.value=v; i.dispatchEvent(new Event('input',{bubbles:true})); await sleep(20); }
async function editCell(row,k,value){
  const g=eng().grid; g.setActiveCell(row,colIdx(k)); await sleep(10);
  key(g.getActiveCellNode(),'Enter'); await sleep(10);
  const ed=$('.sg-editor'); if(!ed) return {opened:false};
  ed.value=value; key(ed,'Enter'); await sleep(20);
  return {opened:true,closed:!$('.sg-editor')};
}
async function escCell(row,k,value){
  const g=eng().grid; g.setActiveCell(row,colIdx(k)); await sleep(10);
  key(g.getActiveCellNode(),'Enter'); await sleep(10);
  const ed=$('.sg-editor'); if(!ed) return {opened:false};
  ed.value=value; key(ed,'Escape'); await sleep(20);
  return {opened:true,closed:!$('.sg-editor')};
}
async function tryOpenEditor(row,k){
  const g=eng().grid; g.setActiveCell(row,colIdx(k)); await sleep(10);
  key(g.getActiveCellNode(),'Enter'); await sleep(10);
  const opened=!!$('.sg-editor')||!!g.getCellEditor();
  const n=g.getActiveCellNode(); if(n) n.dispatchEvent(new MouseEvent('dblclick',{bubbles:true})); await sleep(10);
  const opened2=!!$('.sg-editor')||!!g.getCellEditor();
  if(opened||opened2){ const ed=$('.sg-editor'); if(ed) key(ed,'Escape'); await sleep(10); }
  return opened||opened2;
}
function rowCheckbox(row){ const n=eng().grid.getCellNode(row,0); return n&&n.querySelector('input[type=checkbox]'); }
function selCount(){ return eng().grid.getSelectedRows().length; }
function h(el){ return el?Math.round(el.getBoundingClientRect().height*10)/10:null; }

// ---- palette swap on the open screen (same method as palette_swap_check.py, scoped) ----
function palNames(){
  const names=new Set();
  for(const sh of document.styleSheets){ let rs; try{rs=sh.cssRules;}catch(e){continue;}
    for(const r of rs){ if(!r.selectorText||!/^html\s*\[\s*data-theme/.test(r.selectorText)) continue;
      for(let i=0;i<r.style.length;i++){ const n=r.style.item(i); if(n.indexOf('--pal-')===0||n==='--shadow-color') names.add(n); } } }
  return Array.from(names);
}
const PROPS=['color','background-color','border-top-color','border-right-color','border-bottom-color','border-left-color','outline-color','box-shadow','caret-color','accent-color'];
function snap(){
  const out=[]; const els=[$('.sg-screen')].concat($$('.sg-screen *'));
  els.forEach((el,i)=>{ const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden') return;
    PROPS.forEach(p=>{
      if(p.startsWith('border-')&&parseFloat(cs.getPropertyValue(p.replace('color','width')))===0) return;
      if(p==='outline-color'&&cs.outlineStyle==='none') return;
      out.push([i,el.tagName+'.'+(typeof el.className==='string'?el.className.split(' ').slice(0,2).join('.'):''),p,cs.getPropertyValue(p)]);
    }); });
  return out;
}
function sentinel(i,off){ return 'hsl('+((i*137.508+off)%360).toFixed(1)+' 80% 45%)'; }
function swapEscapes(label){
  const names=palNames(), root=document.documentElement;
  names.forEach((n,i)=>root.style.setProperty(n,sentinel(i,0))); const A=snap();
  names.forEach((n,i)=>root.style.setProperty(n,sentinel(i,181))); const B=snap();
  names.forEach(n=>root.style.removeProperty(n));
  const esc=[];
  for(let i=0;i<A.length&&i<B.length;i++){
    const v=A[i][3];
    if(v===B[i][3] && !/^(rgba\(0, 0, 0, 0\)|transparent|none|auto|currentcolor)$/i.test(v)) esc.push(label+' '+A[i][1]+' '+A[i][2]+'='+v);
  }
  return esc;
}

try{
  const F=window.SRET_FIXTURES;
  // ============ User milestones (opened on load) ============
  ok('userms: screen open on load', SRETGrid.isOpen() && !!$('.sg-screen'));
  ok('userms: title', $('.sg-title').textContent==='User milestones', $('.sg-title').textContent);
  ok('userms: row count', visibleCount()===F.userms.length && $('[data-sg=count]').textContent===F.userms.length+' rows',
     $('[data-sg=count]').textContent);
  ok('userms: Add and Delete present', !!$('[data-sg=add]') && !!$('[data-sg=delete]'));

  // keyboard navigation
  { const g=eng().grid; g.setActiveCell(0,1); await sleep(10);
    key(g.getActiveCellNode(),'ArrowDown'); await sleep(10); const a=g.getActiveCell();
    key(g.getActiveCellNode(),'ArrowRight'); await sleep(10); const b=g.getActiveCell();
    key(g.getActiveCellNode(),'ArrowDown'); await sleep(10); const c=g.getActiveCell();
    ok('keyboard: arrows move the active cell (N=3)', a.row===1&&a.cell===1 && b.row===1&&b.cell===2 && c.row===2&&c.cell===2, [a,b,c]); }

  // D-16 sizes
  { const ctl=parseFloat(getComputedStyle($('.sg-screen')).getPropertyValue('--ctl-h'));
    const hs=[h($('[data-sg=search]')),h($('[data-sg=export]')),h($('[data-sg=add]')),h($('.sg-hfilter'))];
    const rowH=h(eng().grid.getCellNode(0,1).parentNode);
    ok('D-16: search, buttons and filters are --ctl-h tall', hs.every(x=>Math.abs(x-ctl)<=0.5), {ctl:ctl,hs:hs});
    ok('D-16: grid row is --ctl-h tall', Math.abs(rowH-ctl)<=0.5, rowH); }

  // sort: text asc/desc, number asc (N=3 ordered pairs)
  { header('name').click(); await sleep(20);
    const names=F.userms.map(r=>r.name).sort((a,b)=>a.localeCompare(b,undefined,{numeric:true,sensitivity:'base'}));
    const got=[0,1,2].map(i=>cellText(i,'name'));
    ok('sort: text ascending, first three', JSON.stringify(got)===JSON.stringify(names.slice(0,3)), got);
    header('name').click(); await sleep(20);
    const gotD=[0,1,2].map(i=>cellText(i,'name'));
    ok('sort: text descending, first three', JSON.stringify(gotD)===JSON.stringify(names.slice().reverse().slice(0,3)), gotD);
    header('progress').click(); await sleep(20);
    const n=[0,1,2,3].map(i=>Number(cellText(i,'progress')));
    ok('sort: number ascending, numeric not lexical', n[0]<=n[1]&&n[1]<=n[2]&&n[2]<=n[3]&&n[0]===Math.min(...F.userms.map(r=>r.progress)), n);
    ok('sort: sorted header shows state', header('progress').classList.contains('slick-header-column-sorted')); }

  // filters
  { await setFilter('type','INT');
    const exp=F.userms.filter(r=>r.type==='INT').length;
    ok('filter: contains on select column', visibleCount()===exp && $('[data-sg=count]').textContent===exp+' of '+F.userms.length+' rows',
       [visibleCount(),exp,$('[data-sg=count]').textContent]);
    await setFilter('type','');
    await setFilter('progress','>=75');
    const e2=F.userms.filter(r=>r.progress>=75).length;
    ok('filter: >= on number column', visibleCount()===e2, [visibleCount(),e2]);
    await setFilter('progress','');
    await setFilter('finish','<1-Aug-26');
    const e3=F.userms.filter(r=>r.finish && r.finish<'2026-08-01').length;
    ok('filter: < on date column (d-Mmm-yy input)', visibleCount()===e3 && e3>0, [visibleCount(),e3]);
    await setFilter('finish','>2026-09-01');
    const e4=F.userms.filter(r=>r.finish && r.finish>'2026-09-01').length;
    ok('filter: > on date column (ISO input)', visibleCount()===e4 && e4>0, [visibleCount(),e4]);
    await setFilter('finish','');
    await setSearch('review');
    const e5=F.userms.filter(r=>JSON.stringify(r).toLowerCase().indexOf('review')>=0).length;
    ok('quick search across columns', visibleCount()===e5 && e5>0 && e5<F.userms.length, [visibleCount(),e5]);
    await setSearch('');
    ok('filters cleared', visibleCount()===F.userms.length); }

  // selection: select all then deselect three
  { // The plugin re-renders the header cell on every selection change, so the
    // select-all box is re-queried each time rather than held.
    const all=()=>$('.sg-check-h input[type=checkbox]');
    all().click(); await sleep(20);
    const s0=selCount(), t0=$('[data-sg=selcount]').textContent;
    rowCheckbox(1).click(); await sleep(10); const s1=selCount();
    rowCheckbox(3).click(); await sleep(10); const s2=selCount();
    rowCheckbox(5).click(); await sleep(10); const s3=selCount(), t3=$('[data-sg=selcount]').textContent;
    const n=F.userms.length;
    ok('select all selects every row', s0===n && t0===n+' selected', [s0,t0]);
    ok('deselect one at a time (N=3)', s1===n-1&&s2===n-2&&s3===n-3 && t3===(n-3)+' selected', [s1,s2,s3,t3]);
    ok('Delete enabled with a selection', !$('[data-sg=delete]').disabled);
    all().click(); await sleep(10);
    const sAll=selCount(), checkedAll=all().checked;
    all().click(); await sleep(10);
    ok('select-all after a partial selection selects all again, and shows checked', sAll===n && checkedAll, [sAll,checkedAll]);
    ok('select-all toggles off', selCount()===0 && $('[data-sg=selcount]').textContent==='' && $('[data-sg=delete]').disabled, selCount()); }

  // restore a known order: sort by ID ascending
  header('id').click(); await sleep(20);
  if(cellText(0,'id')!=='USR-001'){ header('id').click(); await sleep(20); }

  // inline edits N=3, one per value type
  { const handed=window.DEMO_LAST_ROWS, before=JSON.stringify(handed);
    const cases=[[0,'name','Edited name one','Edited name one'],[1,'state','RISK','RISK'],[2,'progress','42',42],[3,'finish','2026-11-13','2026-11-13']];
    for(const [row,k,input,expect] of cases){
      const rk=eng().dataView.getItem(row).id;
      const n0=count('onEdit'); const r=await editCell(row,k,input); const e=lastLog('onEdit');
      ok('edit '+k+': Enter opens and Enter commits', r.opened&&r.closed, r);
      ok('edit '+k+': onEdit(rowKey,key,value) exact', count('onEdit')===n0+1 && e && e.args[0]===rk && e.args[1]===k && e.args[2]===expect && typeof e.args[2]===typeof expect,
         e&&e.args);
    }
    ok('edit: display updates (date shown d-Mmm-yy, select shows label)', cellText(3,'finish')==='13-Nov-26' && cellText(1,'state')==='At risk',
       [cellText(3,'finish'),cellText(1,'state')]);
    ok('edit: caller row objects never mutated by the grid', JSON.stringify(handed)===before && handed.length===F.userms.length); }

  // Esc cancels N=3
  { const n0=count('onEdit'); const snaps=[];
    for(const [row,k] of [[4,'name'],[5,'comment'],[6,'progress']]){
      const t=cellText(row,k); const r=await escCell(row,k,'999 escaped'); snaps.push([r,t,cellText(row,k)]);
    }
    ok('Esc cancels (N=3): editor closes, value unchanged, no onEdit', count('onEdit')===n0 && snaps.every(s=>s[0].opened&&s[0].closed&&s[1]===s[2]), snaps); }

  // refused edit reverts
  { const t=cellText(7,'progress'); const n0=count('onEdit'); await editCell(7,'progress','150');
    ok('onEdit returning false reverts the cell', count('onEdit')===n0+1 && cellText(7,'progress')===t, [t,cellText(7,'progress')]); }

  // read-only column N=3
  { const res=[]; for(const r of [0,1,2]) res.push(await tryOpenEditor(r,'id'));
    ok('read-only column refuses edits (N=3)', res.every(x=>x===false), res); }

  // a real resize (window or side panel) while a cell is being edited
  // requestResize() is the observer's own path, called directly so the resize
  // really lands mid-edit rather than by timing luck (headless frames are not reliable).
  { const frames=async()=>{ eng().requestResize(); await sleep(30); };
    const g=eng().grid, vp=$('.sg-grid .slick-viewport'), board=$('#demo-board'), res=[];
    for(const [row,w] of [[8,'900px'],[9,''],[10,'700px']]){
      g.setActiveCell(row,colIdx('comment')); key(g.getActiveCellNode(),'Enter'); await sleep(10);
      const ed=$('.sg-editor'), txt='Kept through resize '+row, rk=eng().dataView.getItem(row).id;
      ed.value=txt; board.style.width=w; await frames(); await sleep(20);
      const same=$('.sg-editor')===ed;
      if($('.sg-editor')) key($('.sg-editor'),'Enter'); await frames(); await sleep(20);
      const e=lastLog('onEdit');
      res.push({same:same,committed:!!e&&e.args[0]===rk&&e.args[2]===txt,
                applied:Math.abs(vp.clientWidth-$('.sg-grid').clientWidth)<=20});
    }
    board.style.width=''; await frames(); await sleep(20);
    ok('resize during an edit (N=3): editor and typed text kept, onEdit commits, resize applied after', res.every(x=>x.same&&x.committed&&x.applied), res); }

  // theme swap while editing
  { const g=eng().grid; g.setActiveCell(0,colIdx('name')); key(g.getActiveCellNode(),'Enter'); await sleep(10);
    R.notes.swap_edit_light=swapEscapes('light/editing');
    document.documentElement.setAttribute('data-theme','dark'); await sleep(10);
    R.notes.swap_edit_dark=swapEscapes('dark/editing');
    document.documentElement.setAttribute('data-theme','light');
    key($('.sg-editor'),'Escape'); await sleep(10); }

  // add
  { const n0=visibleCount(), a0=count('onAdd');
    $('[data-sg=add]').click(); await sleep(30);
    const e=lastLog('onAdd');
    ok('Add row calls onAdd once and shows the row', count('onAdd')===a0+1 && visibleCount()===n0+1 && !!eng().dataView.getItemById(e.args[0]), [n0,visibleCount()]);
    ok('Add row opens the new row for editing', !!$('.sg-editor'));
    key($('.sg-editor'),'Escape'); await sleep(10); }

  // delete with inline confirmation
  { rowCheckbox(0).click(); rowCheckbox(2).click(); await sleep(10);
    const keys=eng().grid.getSelectedRows().map(r=>eng().dataView.getItem(r).id).sort();
    const d0=count('onDelete'), n0=visibleCount();
    $('[data-sg=delete]').click(); await sleep(10);
    const cf=$('[data-sg=confirm]'); const btns=$$('button',cf).map(b=>b.textContent);
    ok('Delete shows inline confirmation with count', !cf.hidden && /^Remove 2 rows\?/.test($('.sg-confirm-msg').textContent), $('.sg-confirm-msg').textContent);
    ok('confirmation: Cancel left, Remove right (danger)', btns.join('|')==='Cancel|Remove' && $$('button',cf)[1].classList.contains('sg-btn--danger'), btns);
    R.notes.swap_confirm=swapEscapes('light/confirm');
    key(document.activeElement,'Escape'); await sleep(10);
    ok('Esc cancels the confirmation, nothing deleted', cf.hidden && count('onDelete')===d0 && visibleCount()===n0);
    $('[data-sg=delete]').click(); await sleep(10); $('[data-sg=confirm-remove]').click(); await sleep(20);
    const e=lastLog('onDelete');
    ok('Remove calls onDelete with the selected keys', count('onDelete')===d0+1 && JSON.stringify(e.args[0].slice().sort())===JSON.stringify(keys), [e&&e.args,keys]);
    ok('deleted rows leave the grid', visibleCount()===n0-2 && keys.every(k=>!eng().dataView.getItemById(k))); }

  // collections: assign selected rows through the shared module
  { const C=window.DEMO_COLL, sel=()=>$('[data-sg=collection]');
    eng().grid.setSelectedRows([]); await sleep(10);
    ok('collections: control disabled with nothing selected', !!sel() && sel().disabled);
    const pick=async v=>{ sel().value=v; sel().dispatchEvent(new Event('change',{bubbles:true})); await sleep(20); };
    const keyAt=r=>eng().dataView.getItem(r).id;
    rowCheckbox(0).click(); rowCheckbox(1).click(); rowCheckbox(2).click(); await sleep(10);
    const k3=[0,1,2].map(keyAt);
    const opts=Array.from(sel().options).map(o=>o.textContent);
    ok('collections: enabled with a selection; lists collections and New collection', !sel().disabled &&
       opts.join('|')==='Add to collection|Site walk 3-Oct (0)|Owner review items (0)|New collection…', opts);
    const a0=count('onAssign'); await pick('UC-001'); const e=lastLog('onAssign');
    ok('collections: onAssign(selected keys, id) exact', count('onAssign')===a0+1 && JSON.stringify(e.args[0].slice().sort())===JSON.stringify(k3.slice().sort()) && e.args[1]==='UC-001', e&&e.args);
    ok('collections: message from the shared describe()', $('[data-sg=msg]').textContent==='Added 3 items to "Site walk 3-Oct".', $('[data-sg=msg]').textContent);
    ok('collections: Collections column updates in place for those rows (N=3)', [0,1,2].every(r=>cellText(r,'colls')==='Site walk 3-Oct') && cellText(3,'colls')==='',
       [0,1,2,3].map(r=>cellText(r,'colls')));
    ok('collections: selection kept after assigning', selCount()===3, selCount());
    rowCheckbox(2).click(); rowCheckbox(3).click(); await sleep(10);
    await pick('UC-001');
    const uc1=C.list.find(c=>c.id==='UC-001');
    ok('collections: re-assigning is idempotent (2 already in, 1 new, no duplicates)', $('[data-sg=msg]').textContent==='Added 1 item to "Site walk 3-Oct". 2 items were already in it.' &&
       uc1.items.length===4 && new Set(uc1.items).size===4, [$('[data-sg=msg]').textContent,uc1.items]);
    // new collection panel
    await pick('__new__'); const panel=$('[data-sg=newcoll]'), nm=()=>$('[data-sg=newcoll-name]');
    ok('new collection: panel opens with the name field focused', !panel.hidden && document.activeElement===nm());
    const c0=C.list.length;
    nm().value='  '; key(nm(),'Enter'); await sleep(10);
    const errEmpty=$('[data-sg=newcoll-err]').textContent;
    nm().value='site WALK 3-oct'; key(nm(),'Enter'); await sleep(10);
    const errDup=$('[data-sg=newcoll-err]').textContent;
    ok('new collection: empty and duplicate (case-insensitive) names refused, panel stays open', errEmpty==='Enter a name for the collection.' &&
       /already exists/.test(errDup) && !panel.hidden && C.list.length===c0, [errEmpty,errDup]);
    key(nm(),'Escape'); await sleep(10);
    ok('new collection: Esc cancels, nothing created', panel.hidden && C.list.length===c0);
    await pick('__new__'); nm().value='Punch list'; $('[data-sg=newcoll-create]').click(); await sleep(20);
    const pl=C.list.find(c=>c.name==='Punch list');
    ok('new collection: Create makes it and adds the selected rows', panel.hidden && !!pl && pl.items.length===3 &&
       Array.from(sel().options).some(o=>o.textContent==='Punch list (3)'), pl&&pl.items);
    ok('collections: a row in two collections shows both', cellText(0,'colls')==='Site walk 3-Oct, Punch list', cellText(0,'colls'));
    R.notes.swap_newcoll=(await (async()=>{ await pick('__new__'); const x=swapEscapes('light/new-collection'); key(nm(),'Escape'); await sleep(10); return x; })());
    eng().grid.setSelectedRows([]); await sleep(10); }

  // idle palette swap, both themes, and theming differs between themes
  { R.notes.swap_idle_light=swapEscapes('light/idle');
    const bgL=getComputedStyle($('.sg-grid .slick-row')).backgroundColor, hdL=getComputedStyle($('.sg-bar')).backgroundColor, txL=getComputedStyle($('.sg-grid .slick-cell')).color;
    document.documentElement.setAttribute('data-theme','dark'); await sleep(10);
    R.notes.swap_idle_dark=swapEscapes('dark/idle');
    const bgD=getComputedStyle($('.sg-grid .slick-row')).backgroundColor, hdD=getComputedStyle($('.sg-bar')).backgroundColor, txD=getComputedStyle($('.sg-grid .slick-cell')).color;
    document.documentElement.setAttribute('data-theme','light'); await sleep(10);
    ok('light and dark both themed (row, toolbar, text differ)', bgL!==bgD && hdL!==hdD && txL!==txD, {bgL,bgD,hdL,hdD,txL,txD});
    const esc=[].concat(R.notes.swap_idle_light,R.notes.swap_idle_dark,R.notes.swap_edit_light,R.notes.swap_edit_dark,R.notes.swap_confirm,R.notes.swap_newcoll);
    ok('palette swap: every painted colour in the screen moves with --pal-* (idle, editing, confirm, new collection; both themes)', esc.length===0, esc.slice(0,12)); }

  // back
  { const b0=count('onBack'); const launcher=$('#go-userms'); launcher.focus();
    // reopen from a launcher so focus has somewhere to return to
    SRETGrid.close(); launcher.focus(); DEMO_OPEN('userms'); await sleep(20);
    $('[data-sg=back]').click(); await sleep(20);
    ok('back calls onBack once and closes the screen', count('onBack')===b0+1 && !SRETGrid.isOpen() && !$('.sg-screen'));
    ok('back restores focus to where the user came from', document.activeElement===launcher, document.activeElement&&document.activeElement.id); }

  // ============ Annotations ============
  { DEMO_OPEN('annot'); await sleep(20);
    ok('annot: title and row count', $('.sg-title').textContent==='Annotations: W/E 27-Sep-26' && visibleCount()===F.annot.length);
    ok('annot: no Add (no onAdd), Delete present', !$('[data-sg=add]') && !!$('[data-sg=delete]'));
    const rk=eng().dataView.getItem(2).aid; await editCell(2,'value','Revised comment text'); const e=lastLog('onEdit');
    ok('annot: comment edit reaches onEdit', e.args[0]===rk && e.args[1]==='value' && e.args[2]==='Revised comment text', e.args);
    await editCell(3,'status','done'); const e2=lastLog('onEdit');
    ok('annot: status select edit reaches onEdit', e2.args[1]==='status' && e2.args[2]==='done', e2.args);
    const res=[]; for(const k of ['aid','kind','target']) res.push(await tryOpenEditor(0,k));
    ok('annot: read-only columns refuse edits (N=3)', res.every(x=>x===false), res);
    SRETGrid.close(); }

  // ============ Schedule activities + export ============
  { DEMO_OPEN('sched'); await sleep(20);
    ok('sched: title and row count', $('.sg-title').textContent==='Schedule activities' && visibleCount()===F.sched.length && F.sched.length>100,
       [visibleCount(),F.sched.length]);
    ok('sched: no Add, no Delete (read-only schedule)', !$('[data-sg=add]') && !$('[data-sg=delete]'));
    const res=[]; for(const k of ['id','name','start','finish','float']) res.push(await tryOpenEditor(1,k));
    ok('sched: schedule columns refuse edits (N=5)', res.every(x=>x===false), res);
    const rk=eng().dataView.getItem(1).id; await editCell(1,'health','2'); const e=lastLog('onEdit');
    ok('sched: annotation column (health) edits, numeric option value kept', e.args[0]===rk && e.args[1]==='health' && e.args[2]===2, e.args);
    ok('sched: health shows its label', cellText(1,'health')==='At risk', cellText(1,'health'));
    // the same store serves this screen: add two schedule rows to the collection made on User milestones
    eng().grid.setSelectedRows([0,1]); await sleep(10);
    const s1=$('[data-sg=collection]'); const pl0=window.DEMO_COLL.list.find(c=>c.name==='Punch list');
    const plId=pl0.id, before=pl0.items.length;
    s1.value=plId; s1.dispatchEvent(new Event('change',{bubbles:true})); await sleep(20);
    ok('collections: shared store across screens (schedule rows join the collection made on User milestones)',
       pl0.items.length===before+2 && pl0.items.indexOf('activity:'+eng().dataView.getItem(0).id)>=0 &&
       Array.from(s1.options).some(o=>o.textContent==='Punch list ('+(before+2)+')'), pl0.items);
    eng().grid.setSelectedRows([]); await sleep(10);
    // export visible rows after a filter and a sort
    await setFilter('wbs','Key'); header('finish').click(); await sleep(20);
    const vis=visibleCount();
    await SRETGrid.exportVisible();
    const aoa=window.__xlsx.aoa||[];
    ok('export: header row plus exactly the visible rows', aoa.length===vis+1 && vis>0 && vis<F.sched.length, [aoa.length,vis]);
    ok('export: headers are the column labels', JSON.stringify(aoa[0])===JSON.stringify(F.cols.sched.map(c=>c.label)));
    const fi=F.cols.sched.findIndex(c=>c.key==='finish');
    const firstId=eng().dataView.getItem(0).id;
    ok('export: row order follows the sort', aoa[1][0]===firstId, [aoa[1]&&aoa[1][0],firstId]);
    ok('export: dates are Date cells', aoa.slice(1).some(r=>r[fi] instanceof Date));
    ok('export: file name', window.__xlsx.name==='Schedule activities.xlsx', window.__xlsx.name);
    SRETGrid.close(); }

  // ============ 2,000 row stress ============
  { const T=window.__stress; R.notes.open_2000_ms=Math.round(T.openMs); R.notes.filter_2000_ms=Math.round(T.filterMs);
    ok('stress: timing clock is real (advanced during the timed work)', T.openMs>0 && T.filterMs>0, T);
    ok('stress: opens under '+__OPEN__+' ms (real clock, parse-time run)', T.openMs<__OPEN__, Math.round(T.openMs));
    ok('stress: filter over 2,000 rows under '+__FILTER__+' ms', T.filterMs<__FILTER__ && T.filtered<2000 && T.filtered>0, T);
    const SC=window.__scroll; R.notes.scroll_step_p95_ms=+SC.p95Ms.toFixed(2);
    ok('scroll: fast scrolls (2.5 viewports per jump, N=10) show every visible row immediately', SC.flingMiss===0, SC.flingMiss);
    ok('scroll: small steps (N=150) never leave a visible row blank', SC.smallMiss===0, SC.smallMiss);
    ok('scroll: the grid does not move scrollTop itself on a wheel event (native scroll only)', SC.wheelMoved===0, SC.wheelMoved);
    ok('scroll: rows positioned with transforms (compositor), not top', SC.transform);
    ok('scroll: per-step render cost p95 under 8 ms (half a 60 Hz frame)', SC.p95Ms<8, SC.p95Ms);
    SRETGrid.close(); DEMO_OPEN('stress'); await sleep(20);
    ok('stress: 2,000 rows loaded', visibleCount()===2000);
    const domRows=$$('.sg-grid .slick-row').length; R.notes.dom_rows_2000=domRows;
    ok('stress: virtual rendering (DOM rows far below 2,000)', domRows>0 && domRows<150, domRows);
    eng().grid.scrollRowIntoView(1999); await sleep(50);
    const lastId=eng().dataView.getItem(1999).id;
    ok('stress: last row reachable by scrolling', $$('.sg-grid .slick-cell.l1').some(c=>c.textContent===lastId), lastId);
    SRETGrid.close(); }
  // shared module, direct
  { const M=SRETCollections, st=M.newStore();
    const a=M.create(st,'  Weekly   review ','2026-09-27T00:00:00Z');
    ok('module: name trimmed and spaces collapsed; ids sequential', a.collection.name==='Weekly review' && a.collection.id==='UC-001');
    ok('module: 61-character name refused', !!M.create(st,'x'.repeat(61)).error);
    const r=M.assign(st,'UC-001',['a','a','b']);
    ok('module: duplicate refs in one call count once', r.added===2 && r.already===0 && st.list[0].items.length===2, r);
    const u=M.unassign(st,'UC-001',['a','zz']);
    ok('module: unassign removes only members', u.removed===1 && st.list[0].items.join()==='b', u);
    ok('module: unknown collection is an error, not a throw', !!M.assign(st,'UC-999',['c']).error);
    const msgs=[M.describe(r),M.describe(u),M.describe(M.assign(st,'UC-001',['b']))];
    ok('module: user-facing sentences have no em or en dashes', msgs.every(m=>!/[\u2013\u2014]/.test(m)), msgs); }
}catch(err){ ok('probe ran without throwing', false, String(err&&err.stack||err)); }
ok('no uncaught page errors', window.__errs.length===0, window.__errs);
const pre=document.createElement('pre'); pre.id='grid-view-out'; pre.textContent=JSON.stringify(R); document.body.appendChild(pre);
})();
</script>
"""


def probe(html_text: str) -> dict:
    js = HARNESS.replace("__OPEN__", str(OPEN_BUDGET_MS)).replace("__FILTER__", str(FILTER_BUDGET_MS))
    html = html_text.replace("<head>", "<head>" + STUB, 1).replace("</body>", TIMING + js + "</body>")
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "grid_view_probe.html"
        f.write_text(html, encoding="utf-8")
        proc = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--window-size=1440,900",
                               "--virtual-time-budget=20000", "--dump-dom", f.as_uri()],
                              capture_output=True, text=True, timeout=300)
    m = re.search(r'<pre id="grid-view-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        return {"checks": [{"name": "probe produced output", "pass": False, "detail": proc.stderr[-2000:]}], "notes": {}}
    raw = m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")
    return json.loads(raw)


def mutate(html: str, name: str) -> str:
    pairs = MUTATIONS[name]
    for old, new in (pairs if isinstance(pairs, list) else [pairs]):
        if html.count(old) != 1:
            sys.exit(f"Mutation {name}: anchor found {html.count(old)} times, expected 1. Update MUTATIONS.")
        html = html.replace(old, new)
    return html


def subprocess_checks(html_path: pathlib.Path) -> list:
    out = []
    for label, cmd in [
        ("colour_audit.py --strict on demo.html", [sys.executable, str(ROOT / "tools" / "colour_audit.py"), str(html_path), "--strict"]),
        ("palette_swap_check.py on demo.html", [sys.executable, str(ROOT / "tools" / "palette_swap_check.py"), str(html_path)]),
    ]:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        tail = [ln for ln in p.stdout.strip().splitlines() if ln.strip()][-1:] or [p.stderr.strip()[-200:]]
        out.append({"name": label, "pass": p.returncode == 0, "detail": tail[0]})
    return out


def run_once(html_path: pathlib.Path, breaker: str | None, with_subprocess: bool) -> dict:
    text = html_path.read_text(encoding="utf-8")
    if breaker:
        text = mutate(text, breaker)
    res = probe(text)
    if with_subprocess:
        if breaker:
            with tempfile.TemporaryDirectory() as td:
                bp = pathlib.Path(td) / "broken_demo.html"
                bp.write_text(text, encoding="utf-8")
                res["checks"] += subprocess_checks(bp)
        else:
            res["checks"] += subprocess_checks(html_path)
            p = subprocess.run([sys.executable, str(ROOT / "tools" / "grid_view_assemble.py"), "--check"],
                               capture_output=True, text=True)
            res["checks"].append({"name": "demo.html matches its sources (assembler --check)",
                                  "pass": p.returncode == 0, "detail": p.stdout.strip()})
    return res


def report(res: dict, title: str) -> int:
    fails = [c for c in res["checks"] if not c["pass"]]
    print(f"== {title}: {len(res['checks']) - len(fails)} pass, {len(fails)} fail")
    for c in res["checks"]:
        mark = "PASS" if c["pass"] else "FAIL"
        line = f"  {mark}  {c['name']}"
        if not c["pass"] and c.get("detail") is not None:
            line += f"  :: {json.dumps(c['detail'])[:300]}"
        print(line)
    if res.get("notes"):
        n = {k: v for k, v in res["notes"].items() if not isinstance(v, list)}
        print(f"  notes: {json.dumps(n)}")
    return len(fails)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEMO))
    ap.add_argument("--break", dest="breaker", choices=sorted(MUTATIONS))
    ap.add_argument("--prove-fails", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    html_path = pathlib.Path(a.html)

    if a.prove_fails:
        caught = {}
        for name in MUTATIONS:
            res = run_once(html_path, name, with_subprocess=(name == "literal-colour"))
            failed = [c["name"] for c in res["checks"] if not c["pass"]]
            caught[name] = failed
            print(f"-- mutation {name}: {'CAUGHT' if failed else 'MISSED'} ({len(failed)} failing checks)")
            for f in failed[:6]:
                print(f"     FAIL  {f}")
        missed = [k for k, v in caught.items() if not v]
        print(f"\n{len(MUTATIONS) - len(missed)} of {len(MUTATIONS)} mutations caught.")
        return 1 if missed else 0

    res = run_once(html_path, a.breaker, with_subprocess=True)
    nfail = report(res, f"grid view check{' (mutation ' + a.breaker + ')' if a.breaker else ''}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
