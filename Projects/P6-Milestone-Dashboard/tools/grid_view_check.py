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
    "esc-commits": ("    el.addEventListener('keydown',function(e){\n      if((e.key==='ArrowLeft'",
                    "    el.addEventListener('keydown',function(e){ if(e.key==='Escape'){ args.grid.getEditorLock().commitCurrentEdit(); return; }\n      if((e.key==='ArrowLeft'"),
    "no-selection-count": ("grid.onSelectedRowsChanged.subscribe(updateStatus);", ""),
    "literal-colour": (".sg-grid .slick-row{background:var(--color-row-default-bg)}", ".sg-grid .slick-row{background:#ffffff}"),
    # Scroll: the engine defaults that caused the reported stutter.
    "scroll-defaults": ("enableMouseWheelScrollHandler:false,forceSyncScrolling:true,\n      rowTopOffsetRenderType:'transform',minRowBuffer:10",
                        "enableMouseWheelScrollHandler:true,forceSyncScrolling:false,\n      rowTopOffsetRenderType:'top',minRowBuffer:3"),
    # Collections: the shared rule (no duplicates) and the grid handing over the right keys.
    # Lists: each rule the temp list flow depends on.
    "temp-wrong-keys": ("listsDone(M().tempAdd(lists.store,selectedRefs()));", "listsDone(M().tempAdd(lists.store,selectedRefs().slice(1)));"),
    "temp-duplicates": ("if(store.temp.indexOf(r)>=0) already++; else", "if(false) already++; else"),
    "single-list-setting-ignored": ("      if(single(store)) listsOf(store,r)", "      if(false) listsOf(store,r)"),
    "multi-list-broken": ("settings:{singleList:!!(opts&&opts.singleList)}", "settings:{singleList:true}"),
    "step2-takes-whole-temp": ("listsDone(M().addFromTemp(st,c.id,pickedRefs()));", "listsDone(M().addFromTemp(st,c.id,M().temp(st)));"),
    # Header (Matt, 2026-09-27): rows 2 and 3 start in line with the title; counts sit under the buttons.
    "search-not-indented": (".sg-bar2,.sg-bar3{padding-left:var(--sg-indent)}", ""),
    "counts-above-buttons": ("[bar,bar2,bar3,confirm,body,msg]", "[bar,bar3,bar2,confirm,body,msg]"),
    "panel-open-by-default": ("'data-sg':'panel',hidden:true}", "'data-sg':'panel'}"),
    "menu-stays-open": ("b.addEventListener('click',function(e){ e.stopPropagation(); close(true); it.onSelect(); });",
                        "b.addEventListener('click',function(e){ e.stopPropagation(); it.onSelect(); });"),
    "import-in-side-panel": ("if(s.opts.importer) return openDialog('Import milestones',function(body,close){ return buildImport(body,close); });",
                             "if(s.opts.importer) return buildImport(s.screen.querySelector('.sg-body'),function(){});"),
    "list-toggle-sorts": ("if(b) b.addEventListener('click',function(ev){ ev.stopPropagation(); toggleListCol(); });",
                          "if(b) b.addEventListener('click',function(ev){ toggleListCol(); });"),
    "temp-row-mark-missing": ("m.cssClasses=((m.cssClasses||'')+' sg-in-temp').trim();", ""),
    "panel-actions-below-items": ("    s.panel.appendChild(s.pnlItems);\n", "    s.panel.appendChild(s.pnlItems); s.panel.appendChild(s.pnlTempActions); s.panel.appendChild(s.pnlListActions);\n"),
    "remove-from-list-removes-everywhere": ("listsDone(M().removeFromList(s.lists.store,s.listId,pickedRefs()));", "listsDone(M().unassign(s.lists.store,pickedRefs()));"),
    "temp-only-ignored": ("    if(s.scope && !inScope(item)) return false;\n", ""),
    "filter-state-not-shown": ("    s.pill.hidden=!s.scope;\n", ""),
    "resize-kills-edit": ("if(grid.getEditorLock().isActive()){ pending=true; return; }", ""),
    "mutates-caller": ("dv.setItems((opts.rows||[]).map(function(r){ return Object.assign({},r); }),rowKey);",
                       "dv.setItems((opts.rows||[]),rowKey);"),
    # Round 7 (Matt, 2026-09-27): import rules, table changes
    "import-dup-ids-allowed": ("    if(dup.length){\n", "    if(false){\n"),
    "import-existing-ids-imported": ("if(id&&existing[id]){ res.skipped.push", "if(false){ res.skipped.push"),
    "import-blank-id-kept": ("if(!d[idKey]){ d[idKey]=im.nextId(taken);", "if(false){ d[idKey]=im.nextId(taken);"),
    "import-same-id-twice": ("d[idKey]=im.nextId(taken); taken.push(d[idKey]);", "d[idKey]=im.nextId([]);"),
    "import-deps-unchecked": ("if(missing.length){ dep=true;", "if(false){ dep=true;"),
    "import-no-question": ("    if(!res.issues.length&&!dt.ask){ commitImport(res,fileName,ui); return res; }", "    commitImport(res,fileName,ui); return res;"),
    "import-log-not-written": ("if(im.log) Array.prototype.push.apply(im.log,entries);", ""),
    "import-bad-date-kept": ("row[c.key]=null; return;\n        }", "row[c.key]=norm(v); return;\n        }"),
    "import-silent-fail": ("importPanel(ui,'error',[h('p',{'class':'sg-import-head',text:'Import failed'}),h('p',{'data-sg':'import-error',text:res.fatal})]);", ""),
    "status-tone-missing": ("return {text:txt,addClasses:'sg-tone sg-tone-'+c.tones[v]};", "return txt;"),
    "open-on-any-column": ("if(c&&c.id===opts.openColumn&&it&&", "if(c&&it&&"),
    "health-dot-no-edit": ("var ret=typeof s.opts.onEdit==='function'?s.opts.onEdit(rowKey,key,value):undefined;", "var ret;"),
    "collapsed-list-filter": ("if(!c||(c.key===L_LIST&&!S.listExpanded)) return;", "if(!c) return;"),
    "add-menu-no-separators": ("return [canDel?deleteItem():null, canDel?{sep:1}:null,", "return [canDel?deleteItem():null,"),
    # Round 8 (Matt, 2026-09-28): shared date engine, user name
    "dates-order-fixed": ("var chosen=cfg.dateOrder&&cfg.dateOrder!=='auto'?cfg.dateOrder:null, det=D.detect(dv);",
                          "var chosen=cfg.dateOrder&&cfg.dateOrder!=='auto'?cfg.dateOrder:'DMY', det=D.detect(dv);"),
    "dates-no-year-stability": ("if(yearFirst&&yearLast&&nums.length>=3&&distinct[0]!==distinct[2]){", "if(false){"),
    "dates-never-ask": ("numeric:det.numeric,ambiguous:det.ambiguous,ask:!chosen&&!det.confirmed};", "numeric:det.numeric,ambiguous:det.ambiguous,ask:false};"),
    "dates-iso-votes": ("if(s.kind==='num'&&s.p[0].length!==4) nums.push(s.p);", "if(s.kind==='num') nums.push(s.p);"),
    "user-not-remembered": ("try{ store.setItem(key,n); }catch(e){", "try{ }catch(e){"),
    "save-not-attributed": ("var e={at:meta.at||new Date().toISOString(),by:read(),", "var e={at:meta.at||new Date().toISOString(),by:savedBy,"),
    "shared-file-adopts-author": ("var n=read(), st=!n?'unset'", "var n=read()||savedBy, st=!n?'unset'"),
    "no-first-use-prompt": ("if(USERS.status().state==='unset') openSettings('Who is using this file?');", ""),
    "view-switch-loses-back": ("var carried=S&&S.switching?S.returnFocus:null;", "var carried=null;"),
    "view-title-clips-menu": (".sg-title--views{overflow:visible}", ""),
    "view-no-current-mark": ("radio:true,checked:v.id===opts.view,", "radio:true,checked:false,"),
    "health-shown-in-grid": ("if(lists) cols=[{key:L_LIST", "cols=cols.filter(function(c){ return c.key!=='health'; }).concat(cols.filter(function(c){ return c.key==='health'; }).map(function(c){ return Object.assign({},c,{hidden:false}); }));\n    if(lists) cols=[{key:L_LIST"),
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
  // What the page showed on load, before the timing run closes the screen.
  var d=document.querySelector('[data-sg=dialog]');
  window.__onLoad={dialog:d?d.querySelector('.sg-dialog-title').textContent:null,
                   nameValue:d&&d.querySelector('[data-sg=user-name]')?d.querySelector('[data-sg=user-name]').value:null,
                   state:d&&d.querySelector('[data-sg=user-status]')?d.querySelector('[data-sg=user-status]').getAttribute('data-state'):null};
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
// Column positions by id: the List column sits left of the checkbox, so indexes are never assumed.
function CK(){ return eng().grid.getColumns().findIndex(c=>c.id==='_checkbox_selector'); }
function FD(){ return CK()+1; }
function rowCheckbox(row){ const n=eng().grid.getCellNode(row,CK()); return n&&n.querySelector('input[type=checkbox]'); }
function selCount(){ return eng().grid.getSelectedRows().length; }
function h(el){ return el?Math.round(el.getBoundingClientRect().height*10)/10:null; }
// Dropdown menus: items only exist while the menu is open.
async function menuItem(menu,item){ const b=$('[data-sg='+menu+']'); if(b.getAttribute('aria-expanded')!=='true'){ b.click(); await sleep(10); }
  return $('[data-sg='+menu+'-menu] [data-sg='+item+']'); }
async function menuClose(menu){ const b=$('[data-sg='+menu+']'); if(b&&b.getAttribute('aria-expanded')==='true'){ b.click(); await sleep(10); } }
async function menuPick(menu,item){ const it=await menuItem(menu,item); it.click(); await sleep(20); return it; }
async function delEnabled(){ const d=await menuItem('tools','delete'); const on=!!d&&!d.disabled; await menuClose('tools'); return on; }

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
  // ============ Who is using the file (SRETUser, Matt 2026-09-28) ============
  { const btn=n=>$('[data-sg='+n+']'), U=window.DEMO_USER;
    const L0=window.__onLoad;
    ok('user: first use on this computer asks for the name on load (a browser cannot read the login name); the file says who saved it last',
       L0.dialog==='Who is using this file?' && L0.nameValue==='' && L0.state==='unset' && U.status().savedBy==='J. Ruiz' && btn('demo-user').textContent==='Name not set', L0);
    // The timing run closed that screen; reopen Data settings from the header, the path a user takes later.
    btn('demo-settings').click(); await sleep(10);
    ok('user: header Data settings opens the same field', !!btn('dialog') && $('.sg-dialog-title').textContent==='Data settings' && btn('user-name').value==='');
    const hRows=$$('[data-sg=user-history] tbody tr').map(tr=>Array.from(tr.children).map(td=>td.textContent));
    ok('user: the save history from the file is shown, newest first', hRows.length===2 && hRows[0][1]==='J. Ruiz' && hRows[1][1]==='M. Garrett' && hRows[0][2]==='3.1.0-P58', hRows);
    btn('user-name').value='   '; btn('user-confirm').click(); await sleep(10);
    ok('user: a blank name is refused with a message; nothing stored', !btn('user-error').hidden && btn('user-error').textContent==='Enter a name.' && U.name()==='');
    btn('user-name').value='  Demo   user '; key(btn('user-name'),'Enter'); await sleep(10);
    ok('user: Enter confirms; the name is tidied, remembered on this computer, and compared with the file: "You are working as Demo user. This file was last saved by J. Ruiz."',
       U.name()==='Demo user' && localStorage.getItem('sret-user-name')==='Demo user' && btn('user-error').hidden &&
       btn('user-status').textContent==='You are working as Demo user. This file was last saved by J. Ruiz.' && btn('user-status').getAttribute('data-state')==='other' &&
       btn('demo-user').textContent==='Working as Demo user, last saved by J. Ruiz', [U.name(),btn('user-status').textContent]);
    const ns=getComputedStyle(btn('user-status')).color, dc=getComputedStyle(btn('dialog')).color;
    ok('user: the status text keeps the dialog colour (host p rules do not leak)', ns===dc, [ns,dc]);
    btn('demo-save').click(); await sleep(10);
    const h3=U.history();
    ok('user: a save is recorded against this user and becomes the file\'s last saver; history kept (3 entries)', h3.length===3 && h3[2].by==='Demo user' &&
       U.fileState().savedBy==='Demo user' && btn('user-status').textContent==='You are working as Demo user.' &&
       $$('[data-sg=user-history] tbody tr')[0].children[1].textContent==='Demo user' && lastLog('onSave').args[0]==='Demo user', h3);
    // The same file opened on another computer: its user, not the author, is who works on it now.
    const other=SRETUser._memory(); other.setItem('sret-user-name','A. Lee');
    const u2=SRETUser.create({storage:other,file:U.fileState()});
    ok('user: shared file opened elsewhere: "You are working as A. Lee. This file was last saved by Demo user."',
       u2.status().state==='other' && u2.status().message==='You are working as A. Lee. This file was last saved by Demo user.');
    u2.recordSave({version:'x'});
    ok('user: their save updates the last saver and keeps the whole history', u2.fileState().savedBy==='A. Lee' && u2.history().map(e=>e.by).join('|')==='M. Garrett|J. Ruiz|Demo user|A. Lee');
    const fresh=SRETUser.create({storage:SRETUser._memory(),file:{}});
    ok('user: a new computer with no name is unset even when the file has a last saver; a name over 60 characters is refused',
       fresh.status().state==='unset' && !fresh.setName('x'.repeat(61)).ok && fresh.setName('x'.repeat(60)).ok);
    key(btn('dialog'),'Escape'); await sleep(10);
    ok('user: the prompt closes; the grid is usable', !btn('dialog') && SRETGrid.isOpen()); }

  // ============ User milestones (opened on load) ============
  ok('userms: screen open on load', SRETGrid.isOpen() && !!$('.sg-screen'));
  ok('userms: title', $('.sg-title').textContent==='User milestones', $('.sg-title').textContent);
  ok('userms: row count', visibleCount()===F.userms.length && $('[data-sg=count]').textContent===F.userms.length+' rows',
     $('[data-sg=count]').textContent);
  ok('userms: My temp list panel collapsed on open; rail shows collapsed', $('[data-sg=panel]').hidden && $('[data-sg=temp-open]').getAttribute('aria-expanded')==='false');
  ok('userms: Add row present; Delete in the Tools menu', !!$('[data-sg=add]') && !!(await menuItem('tools','delete'))); await menuClose('tools');

  // keyboard navigation
  { const g=eng().grid, f=FD(); g.setActiveCell(0,f); await sleep(10);
    key(g.getActiveCellNode(),'ArrowDown'); await sleep(10); const a=g.getActiveCell();
    key(g.getActiveCellNode(),'ArrowRight'); await sleep(10); const b=g.getActiveCell();
    key(g.getActiveCellNode(),'ArrowDown'); await sleep(10); const c=g.getActiveCell();
    ok('keyboard: arrows move the active cell (N=3)', a.row===1&&a.cell===f && b.row===1&&b.cell===f+1 && c.row===2&&c.cell===f+1, [a,b,c]); }

  // Round 7 (Matt, 2026-09-27): columns, status tones, health icon, open on double-click, narrow List column
  { const btn=n=>$('[data-sg='+n+']'), ids=eng().grid.getColumns().map(c=>c.id), data=ids.filter(k=>k!=='_list'&&k!=='_checkbox_selector');
    ok('columns: List, checkbox, then ID first; Band and WBS separate; Date created and Created by far right; Health not shown',
       ids[0]==='_list' && ids[1]==='_checkbox_selector' && data[0]==='id' && data.indexOf('band')>=0 && data.indexOf('wbs')===data.indexOf('band')+1 &&
       data.slice(-2).join('|')==='created|createdBy' && data.indexOf('health')<0 &&
       header('band').textContent.trim().startsWith('Band') && !/WBS/.test(header('band').textContent) && header('wbs').textContent.trim().startsWith('WBS'), ids);
    const r0=eng().dataView.getItem(0), ci=colIdx('created'), cb=colIdx('createdBy');
    ok('Date created shows as a date; Created by shows the user; both read-only', /^\d{1,2}-[A-Z][a-z]{2}-\d\d$/.test(cellText(0,'created')) &&
       cellText(0,'createdBy')===r0.createdBy && !(await tryOpenEditor(0,'created')) && !(await tryOpenEditor(0,'createdBy')), [cellText(0,'created'),cellText(0,'createdBy')]);
    ok('List column collapsed by default: 40px or less, no filter box', eng().grid.getColumns()[0].width<=40 && !filterInput('_list') &&
       !$('.slick-headerrow-column.l0 input'), eng().grid.getColumns()[0].width);
    // status tones: one class and one background per status
    const tone={FUTURE:'future',TRACK:'track',RISK:'risk',CRIT:'crit',DONEUSER:'done'}, si=colIdx('state'), seen={};
    for(let r=0;r<eng().dataView.getLength();r++){ const st=eng().dataView.getItem(r).state; if(st in tone && !(st in seen)) seen[st]=eng().grid.getCellNode(r,si); }
    const bgs=Object.keys(seen).map(st=>[st,seen[st].classList.contains('sg-tone-'+tone[st]),getComputedStyle(seen[st]).backgroundColor]);
    ok('Status: every status has its own tone class and a distinct shaded background', bgs.length===5 && bgs.every(b=>b[1]) &&
       new Set(bgs.map(b=>b[2])).size===5 && bgs.every(b=>b[2]!=='rgba(0, 0, 0, 0)'), bgs);
    // health icon on the ID
    const dots=[0,1,2].map(r=>eng().grid.getCellNode(r,colIdx('id')).querySelector('[data-sg-hdot]'));
    ok('ID cell: a health dot before the ID, class follows the health value, labelled', dots.every((d,r)=>!!d && d.classList.contains('sg-h-'+(eng().dataView.getItem(r).health||0)) &&
       /^Health: /.test(d.getAttribute('aria-label'))) && eng().grid.getCellNode(0,colIdx('id')).textContent===eng().dataView.getItem(0).id, dots.map(d=>d&&d.outerHTML));
    const hk=eng().dataView.getItem(0).id, h0=eng().dataView.getItem(0).health||0, pick=h0===3?1:3;
    dots[0].dispatchEvent(new MouseEvent('click',{bubbles:true})); await sleep(10);
    const hp=btn('health-picker');
    ok('tap the health dot: the picker opens with the health options, current one checked', !!hp && $$('[data-sg-health]',hp).length===5 &&
       $('[data-sg-health="'+h0+'"]',hp).getAttribute('aria-checked')==='true', hp&&hp.outerHTML.slice(0,200));
    $('[data-sg-health="'+pick+'"]',hp).click(); await sleep(20);
    const he=lastLog('onEdit'), nd=eng().grid.getCellNode(eng().dataView.getRowById(hk),colIdx('id')).querySelector('[data-sg-hdot]');
    ok('picking a health value calls onEdit(id, "health", value), the dot updates, the picker closes', !!he && he.args[0]===hk && he.args[1]==='health' && he.args[2]===pick &&
       nd.classList.contains('sg-h-'+pick) && !btn('health-picker') && eng().dataView.getItemById(hk).health===pick, he&&he.args);
    // double-click the ID opens the milestone form; elsewhere it does not
    const o0=count('onOpenItem');
    eng().grid.getCellNode(1,colIdx('name')).dispatchEvent(new MouseEvent('dblclick',{bubbles:true})); await sleep(10);
    const ed=$('.sg-editor'); if(ed){ key(ed,'Escape'); await sleep(10); }
    ok('double-click on a non-ID cell does not open the milestone form', count('onOpenItem')===o0 && !$('[data-sg=demo-ms-form]'));
    const k1=eng().dataView.getItem(1).id;
    eng().grid.getCellNode(1,colIdx('id')).dispatchEvent(new MouseEvent('dblclick',{bubbles:true})); await sleep(20);
    ok('double-click on the ID opens the milestone form for that row', count('onOpenItem')===o0+1 && lastLog('onOpenItem').args[0]===k1 &&
       !!$('[data-sg=demo-ms-form]') && !$('.sg-editor'), lastLog('onOpenItem'));
    if(btn('dialog')){ key(btn('dialog'),'Escape'); await sleep(10); }
    // export: Health appended as the last column
    window.__xlsx={}; await menuPick('add-more','export'); await sleep(20);
    const eh=(window.__xlsx.aoa||[[]])[0];
    ok('export: Health is the last column, after Date created and Created by', eh.slice(-3).join('|')==='Date created|Created by|Health', eh);
    window.__xlsx={}; await menuPick('add-more','template'); await sleep(20);
    const th=(window.__xlsx.aoa||[[]])[0];
    ok('import template: Health is the last column', th[th.length-1]==='Health' && th.indexOf('Band')>=0 && th.indexOf('WBS')>=0, th);
  }

  // D-16 sizes
  { const ctl=parseFloat(getComputedStyle($('.sg-screen')).getPropertyValue('--ctl-h'));
    const hs=['search','add','add-more','tools','temp-add','temp-add-more'].map(k=>h($('[data-sg='+k+']'))).concat([h($('.sg-hfilter'))]);
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
    ok('select all selects every row', s0===n && t0==='('+n+' selected)', [s0,t0]);
    ok('deselect one at a time (N=3)', s1===n-1&&s2===n-2&&s3===n-3 && t3==='('+(n-3)+' selected)', [s1,s2,s3,t3]);
    ok('Tools > Delete enabled with a selection', await delEnabled());
    all().click(); await sleep(10);
    const sAll=selCount(), checkedAll=all().checked;
    all().click(); await sleep(10);
    ok('select-all after a partial selection selects all again, and shows checked', sAll===n && checkedAll, [sAll,checkedAll]);
    ok('select-all toggles off; Tools > Delete disabled', selCount()===0 && $('[data-sg=selcount]').textContent==='' && !(await delEnabled()), selCount());
    const link=$('[data-sg=select-all]'); link.click(); await sleep(10);
    const a1=selCount(), lbl1=link.textContent; link.click(); await sleep(10);
    ok('Select all link selects every visible row, then reads Clear selection and clears', a1===n && lbl1==='Clear selection' && selCount()===0 && link.textContent==='Select all', [a1,lbl1]); }

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
    await menuPick('tools','delete');
    ok('Tools menu closes after choosing', $('[data-sg=tools]').getAttribute('aria-expanded')==='false' && $('[data-sg=tools-menu]').hidden);
    const cf=$('[data-sg=confirm]'); const btns=$$('button',cf).map(b=>b.textContent);
    ok('Delete shows inline confirmation with count', !cf.hidden && /^Remove 2 rows\?/.test($('.sg-confirm-msg').textContent), $('.sg-confirm-msg').textContent);
    ok('confirmation: Cancel left, Remove right (danger)', btns.join('|')==='Cancel|Remove' && $$('button',cf)[1].classList.contains('sg-btn--danger'), btns);
    R.notes.swap_confirm=swapEscapes('light/confirm');
    key(document.activeElement,'Escape'); await sleep(10);
    ok('Esc cancels the confirmation, nothing deleted', cf.hidden && count('onDelete')===d0 && visibleCount()===n0);
    await menuPick('add-more','delete');
    ok('Add row menu > Delete selected rows opens the same confirmation', !cf.hidden && /^Remove 2 rows\?/.test($('.sg-confirm-msg').textContent) &&
       $('[data-sg=add-more-menu]').hidden, $('.sg-confirm-msg').textContent);
    key(document.activeElement,'Escape'); await sleep(10);
    await menuPick('tools','delete'); $('[data-sg=confirm-remove]').click(); await sleep(20);
    const e=lastLog('onDelete');
    ok('Remove calls onDelete with the selected keys', count('onDelete')===d0+1 && JSON.stringify(e.args[0].slice().sort())===JSON.stringify(keys), [e&&e.args,keys]);
    ok('deleted rows leave the grid', visibleCount()===n0-2 && keys.every(k=>!eng().dataView.getItemById(k))); }

  // Header (Matt, 2026-09-27): row 1 back and title; row 2 search, Add row (split), Tools,
  // Add to temp list (split), starting in line with the title text; row 3 counts and Select all.
  function headerLayout(){
    const box=e=>e.getBoundingClientRect(), mid=r=>r.top+r.height/2, bad=[];
    const t=box($('.sg-title')), se=box($('[data-sg=search]')), cnt=box($('[data-sg=count]')), bk=box($('[data-sg=back]'));
    if(Math.abs(se.left-t.left)>1) bad.push(['search not in line with the title text',Math.round(se.left-t.left)]);
    if(Math.abs(cnt.left-t.left)>1) bad.push(['counts not in line with the title text',Math.round(cnt.left-t.left)]);
    if(se.left<=bk.right) bad.push(['search not clear of the back arrow column']);
    const order=['search','add','add-more','tools','temp-add','temp-add-more'].map(s=>$('[data-sg='+s+']')).filter(Boolean);
    for(let i=1;i<order.length;i++){ const a=box(order[i-1]), b=box(order[i]);
      if(Math.abs(mid(a)-mid(b))>3) bad.push(['row 2 not on one line',order[i].dataset.sg]);
      if(b.left<a.right-1) bad.push(['row 2 order',order[i].dataset.sg]); }
    if(!(mid(t)<mid(se)&&mid(se)<mid(cnt))) bad.push(['rows not in order: title, buttons, counts',[mid(t),mid(se),mid(cnt)].map(Math.round)]);
    return {bad:bad,rows:[mid(t),mid(se),mid(cnt)].map(Math.round)};
  }

  // My temp list and saved lists (Matt, 2026-09-27)
  { const L=window.DEMO_LISTS, M=SRETCollections, btn=n=>$('[data-sg='+n+']');
    const msg=()=>$('[data-sg=msg]').textContent, n=visibleCount(), sorted=a=>a.slice().sort();
    const itemsIn=v=>eng().dataView.getItems().filter(i=>i._tmp===v);
    const boxes=()=>$$('[data-sg=panel-items] input[type=checkbox]');
    const pick=async idx=>{ for(const b of boxes()) if(b.checked) b.click(); for(const i of idx) boxes()[i].click(); await sleep(10); };
    const labels=m=>$$('[data-sg='+m+'-menu] .sg-menu-item').map(b=>b.textContent.replace(/^✓/,''));
    const rowIdx=id=>eng().dataView.getIdxById(id);
    eng().grid.setSelectedRows([]); await sleep(10);
    ok('panel collapsed; rail buttons show collapsed; badge hidden at 0', btn('panel').hidden &&
       btn('temp-open').getAttribute('aria-expanded')==='false' && btn('lists-open').getAttribute('aria-expanded')==='false' && btn('temp-count').hidden);
    ok('temp list: hover on the title and the rail button says it is session only', btn('temp-title').title==='My temp list is for this session only. It clears when the file is closed or reloaded. Add items to a saved list to keep them.' &&
       btn('temp-open').title==='My temp list (this session only)', [btn('temp-title').title,btn('temp-open').title]);
    ok('Temp column dropped; List column left of the checkbox', colIdx('_tmp')===-1 && colIdx('_list')===0 && CK()===1);
    // Add row split button and its menu
    const am=await menuItem('add-more','import');
    const aml=$$('[data-sg=add-more-menu] > *').map(e=>e.classList.contains('sg-menu-sep')?'---':e.textContent.replace(/^✓/,''));
    const delOff=$('[data-sg=add-more-menu] [data-sg=delete]').disabled, sepH=$$('[data-sg=add-more-menu] .sg-menu-sep').map(e=>e.getBoundingClientRect().height);
    await menuClose('add-more');
    ok('Add row menu (Matt, 2026-09-28): Delete selected rows first, separator, Export .xlsx, Download import template, separator, Import milestones, Import log',
       !!btn('add') && !!am && aml.join('|')==='Delete selected rows…|---|Export .xlsx|Download import template|---|Import milestones…|Import log' &&
       btn('add').parentNode===btn('add-more').parentNode, aml);
    ok('Add row menu: Delete is disabled with nothing selected; separators are 1px hairlines', delOff && sepH.length===2 && sepH.every(v=>v===1), [delOff,sepH]);
    window.__xlsx={}; await menuPick('add-more','export'); await sleep(20);
    ok('Add row menu > Export .xlsx writes the visible rows', window.__xlsx.name==='User milestones.xlsx' && (window.__xlsx.aoa||[]).length===n+1, window.__xlsx.name);
    window.__xlsx={}; await menuPick('add-more','template'); await sleep(20);
    ok('Add row menu > Download import template: the column headers only, without derived columns', window.__xlsx.name==='User milestones import template.xlsx' &&
       JSON.stringify(window.__xlsx.aoa)===JSON.stringify([F.cols.userms.map(c=>c.label)]), [window.__xlsx.name,window.__xlsx.aoa]);
    // Import milestones: centred modal dialog, real checks (Matt, 2026-09-27)
    const importCsv=async(name,text)=>{
      if(!btn('dialog')) await menuPick('add-more','import');
      const inp=btn('import-file'), dt=new DataTransfer(), fl=new File([text],name,{type:'text/csv'}); FILE_TEXT.set(fl,text); dt.items.add(fl);
      inp.files=dt.files; inp.dispatchEvent(new Event('change')); btn('import-go').click(); await settled();
    };
    // Blob reads do not hold Chromium's virtual clock, so --dump-dom can fire mid-read. Only the byte
    // read is served from memory; the file input, change event, Import button, parseFile and the checks are real.
    const FILE_TEXT=new WeakMap(), fileText=File.prototype.text;
    File.prototype.text=function(){ return FILE_TEXT.has(this)?Promise.resolve(FILE_TEXT.get(this)):fileText.call(this); };
    // The file read is real I/O; virtual time can run past any timer, so wait on the DOM instead.
    const settled=()=>new Promise(res=>{ const st=btn('import-status'), done=()=>!!st.getAttribute('data-kind');
      if(done()) return res(); const mo=new MutationObserver(()=>{ if(done()){ mo.disconnect(); res(); } });
      mo.observe(st,{attributes:true,attributeFilter:['data-kind']}); });
    const closeDlg=async()=>{ if(btn('dialog')){ key(btn('dialog'),'Escape'); await sleep(10); } };
    const nRows=()=>eng().dataView.getItems().length, HEAD='ID,Name,Type,Start,Finish,Band,WBS,Status,Predecessor,Successor,% complete,Comment';
    await menuPick('add-more','import');
    const dlg=btn('dialog'), dr=dlg&&dlg.getBoundingClientRect(), sr=$('.sg-screen').getBoundingClientRect();
    ok('Import milestones opens a centred modal dialog with a file picker', !!dlg && dlg.getAttribute('aria-modal')==='true' &&
       Math.abs((dr.left+dr.right)/2-(sr.left+sr.right)/2)<=2 && Math.abs((dr.top+dr.bottom)/2-(sr.top+sr.bottom)/2)<=2 &&
       !!btn('import-file') && btn('import-go').disabled && $('.sg-dialog-title').textContent==='Import milestones');
    R.notes.swap_dialog=swapEscapes('light/import-dialog');
    const n0=nRows(), fails=[];
    for(const [nm,txt] of [['empty.csv',''],['noid.csv','Name,Finish\nA milestone,1-Oct-26\n'],['headonly.csv',HEAD+'\n'],
                           ['dups.csv',HEAD+'\nUSR-050,One,MS\nUSR-050,Two,MS\n,Blank,MS\n'],['notes.txt','x']]){
      await importCsv(nm,txt); const e=btn('import-error'); fails.push([nm,e?e.textContent:null,btn('import-status').getAttribute('role')]); }
    ok('import fails with a clear notice: empty file, no ID column, no rows, wrong file type; nothing added', fails[0][1]==='The file is empty.' &&
       /has no "ID" column/.test(fails[1][1]) && fails[2][1]==='The file has no rows to import.' && /Use an \.xlsx or \.csv file/.test(fails[4][1]) &&
       fails.every(f=>f[2]==='alert') && nRows()===n0 && /^Import failed\./.test(msg()), fails);
    ok('import fails on duplicate IDs within the file, naming them and their rows; blank IDs are fine', fails[3][1]===
       'There are duplicate activity IDs within the list: USR-050 (rows 2, 3). Only unique IDs, or blank IDs, can be imported.' && nRows()===n0, fails[3][1]);
    // clean import: one existing ID (skipped), one new ID, two blank IDs (assigned), valid dependencies
    const maxUsr=Math.max(...eng().dataView.getItems().map(i=>+(/^USR-(\d+)$/.exec(i.id)||[0,0])[1]));
    const nx=k=>'USR-'+String(maxUsr+k).padStart(3,'0'), have=eng().dataView.getItems()[0].id;
    await importCsv('clean.csv',HEAD+'\n'+have+',Already here,MS\nUSR-050,New one,INT,,2026-10-09,,,TRACK,SNIP-101,,40\n'+
      ',First blank,CLI,,9-Oct-26,,,,USR-050,,\n,Second blank,MS,,10/10/2026,,,RISK,,SNIP-118,\n');
    const sum=$$('[data-sg=import-summary] li').map(l=>l.textContent);
    const it50=eng().dataView.getItemById('USR-050'), itA=eng().dataView.getItemById(nx(1)), itB=eng().dataView.getItemById(nx(2));
    ok('clean import: summary lists imported, the date order used, assigned and skipped', JSON.stringify(sum)===JSON.stringify(['Imported 3 milestones.',
       'Dates read as day/month/year. Every date reads the same either way.',
       'IDs assigned to 2 rows with a blank ID: '+nx(1)+', '+nx(2)+'.','Skipped 1 row already in the table: '+have+'.']) && msg()==='Imported 3 milestones.', sum);
    ok('clean import: rows added with assigned IDs, values read (ISO, d-Mmm-yy, d/m/yyyy dates; labels to values), created by and date set',
       nRows()===n0+3 && !!it50&&it50.finish==='2026-10-09'&&it50.type==='INT'&&it50.progress===40&&it50.state==='TRACK' &&
       !!itA&&itA.finish==='2026-10-09'&&itA.pred==='USR-050' && !!itB&&itB.finish==='2026-10-10'&&itB.state==='RISK' &&
       [it50,itA,itB].every(i=>i.createdBy==='Demo user'&&/^\d{4}-\d\d-\d\d$/.test(i.created)) &&
       eng().dataView.getItemById(have).name!=='Already here', [it50,itA,itB]);
    ok('clean import: nothing logged, no View log button', window.DEMO_IMPORT_LOG.length===0 && !btn('import-view-log'));
    btn('import-done').click(); await sleep(10);
    ok('Done closes the dialog', !btn('dialog'));
    // dependencies and other fields not found: ask first; Cancel imports nothing
    const bad=HEAD+'\nUSR-060,Bad deps,MS,,1-Nov-26,,,,"NOPE-1, SNIP-101",ZZZ-9,\nUSR-061,Bad fields,XYZ,,31-Feb-26,,,,,,150\n';
    await importCsv('bad.csv',bad);
    const q=btn('import-question'), notes=$$('[data-sg=import-issues] tbody tr').map(tr=>Array.from(tr.children).map(td=>td.textContent));
    ok('missing dependencies: the dialog asks "Some dependencies or predecessors are not found. Do you wish to continue with import?"',
       !!q && q.textContent==='Some dependencies or predecessors are not found. Do you wish to continue with import?', q&&q.textContent);
    ok('the question lists each issue by row and ID: predecessors and successors not found (comma separated), bad date, choice and number left blank',
       JSON.stringify(notes)===JSON.stringify([['2','USR-060','Predecessors not found: NOPE-1'],['2','USR-060','Successors not found: ZZZ-9'],
         ['3','USR-061','Type "XYZ" is not one of MS, INT, CLI, RTN. Left blank.'],['3','USR-061','Finish "31-Feb-26" is not a valid date. Left blank.'],
         ['3','USR-061','% complete "150" is outside 0 to 100. Left blank.']]), notes);
    $$('[data-sg=import-status] button').find(b=>b.textContent==='Cancel').click(); await sleep(10);
    ok('Cancel imports nothing and logs nothing', nRows()===n0+3 && window.DEMO_IMPORT_LOG.length===0 && !eng().dataView.getItemById('USR-060'));
    btn('import-go').click(); await settled(); btn('import-continue').click(); await sleep(20);
    const i60=eng().dataView.getItemById('USR-060'), i61=eng().dataView.getItemById('USR-061'), L0=window.DEMO_IMPORT_LOG;
    ok('Continue imports the rows; unreadable values left blank; dependencies kept as written', !!i60 && i60.pred==='NOPE-1, SNIP-101' && !!i61 &&
       i61.type==null && i61.finish==null && i61.progress==null, [i60,i61]);
    ok('Continue writes every issue to the Import log with time, file, user, ID and note', L0.length===5 &&
       L0.every(e=>e.file==='bad.csv'&&e.user==='Demo user'&&/^\d{4}-/.test(e.time)) && L0[0].id==='USR-060' && L0[0].note==='Predecessors not found: NOPE-1', L0);
    ok('the summary counts the logged issues', $$('[data-sg=import-summary] li').map(l=>l.textContent).indexOf('5 issues recorded in the Import log.')>=0);
    btn('import-view-log').click(); await sleep(20);
    const lh=$$('[data-sg=import-log-table] th').map(t=>t.textContent), lr=$$('[data-sg=import-log-table] tbody tr').map(tr=>Array.from(tr.children).map(td=>td.textContent));
    ok('Import log table: Time, File, User, ID, Note; one row per issue', JSON.stringify(lh)===JSON.stringify(['Time','File','User','ID','Note']) &&
       lr.length===5 && lr.every(r=>r[1]==='bad.csv'&&r[2]==='Demo user'&&/^\d{1,2}-[A-Z][a-z]{2}-\d\d \d\d:\d\d$/.test(r[0])), lr);
    await closeDlg();
    await menuPick('add-more','import-log');
    ok('Add row menu > Import log opens the same table', $$('[data-sg=import-log-table] tbody tr').length===5); await closeDlg();
    // a blank-ID row with an issue is logged under the ID it was given
    await importCsv('blank.csv',HEAD+'\n,Blank with bad dep,MS,,,,,,QQQ-1,\n'); btn('import-continue').click(); await sleep(20);
    const lastLog0=window.DEMO_IMPORT_LOG[window.DEMO_IMPORT_LOG.length-1], newId=eng().dataView.getItems().find(i=>i.name==='Blank with bad dep').id;
    ok('a blank-ID row is logged under the ID the app assigned', lastLog0.id===newId && /^USR-\d{3}$/.test(newId), [lastLog0,newId]);
    await closeDlg();
    // only field issues: the other question
    await importCsv('fields.csv',HEAD+'\nUSR-070,Only a bad date,MS,,not a date,,,,,,\n');
    ok('only unreadable values: the dialog asks "Some values could not be read. Do you wish to continue with import?"',
       btn('import-question').textContent==='Some values could not be read. Do you wish to continue with import?');
    $$('[data-sg=import-status] button').find(b=>b.textContent==='Cancel').click(); await sleep(10); await closeDlg();
    ok('dialog: Esc closes and focus returns to the menu button', !btn('dialog') && document.activeElement===btn('add-more'));
    // Date order (Matt, 2026-09-28): worked out from every date in the file by the shared SRETDates engine
    { const DT=window.SRETDates, det=v=>{ const r=DT.detect(v); return r.order+(r.confirmed?'':'?'); };
      const cases=[[['13/10/26','05/11/26','01-12-2026'],'DMY'],[['10/13/26','11/05/26','12 01 2026'],'MDY'],
                   [['26-10-09','26-11-05','26-12-01','26-09-30'],'YMD'],[['31.10.2026','01.11.2026'],'DMY'],
                   [['05/06/26','07/08/26','09/10/26'],'DMY?'],[['2026-10-09','9-Oct-26','10/10/2026'],'DMY'],[['13/10/26','10/13/26'],'DMY?']];
      const got=cases.map(c=>det(c[0]));
      ok('SRETDates.detect: day above 12 first = day first; above 12 in the middle = month first; a repeated first part = year first; any break (- / . space); undecided = day first, not confirmed',
         got.join('|')===cases.map(c=>c[1]).join('|'), got);
      const pv=['9-Oct-26','Oct 9, 2026','9 October 2026','2026-10-09','20261009','46304','09/10/26','09-Oct-26 08:00','2026-10-09T08:00:00Z'].map(v=>DT.parse(v,'DMY').value);
      ok('SRETDates.parse: month names in any position, ISO, compact, Excel serial, trailing time: all 9-Oct-26', pv.every(v=>v==='2026-10-09'), pv);
      ok('SRETDates.parse: impossible dates fail on both bounds (31-Feb, 32nd, month 13); 29-Feb only in a leap year',
         !DT.parse('31/02/26','DMY').ok && !DT.parse('32/01/26','DMY').ok && !DT.parse('01/13/26','DMY').ok && DT.parse('31/01/26','DMY').ok &&
         DT.parse('29/02/28','DMY').value==='2028-02-29' && !DT.parse('29/02/26','DMY').ok); }
    const DH='ID,Name,Type,Start,Finish';
    await importCsv('us.csv',DH+'\nUSR-201,US one,MS,10/13/26,10/20/26\nUSR-202,US two,MS,11/5/26,11/12/26\n');
    const us=eng().dataView.getItemById('USR-202'), sumUS=$$('[data-sg=import-summary] li').map(l=>l.textContent);
    ok('import: a file with a middle part above 12 is read month first, with no question; the summary says so',
       !!us && us.start==='2026-11-05' && us.finish==='2026-11-12' && sumUS[1]==='Dates read as month/day/year. A middle part above 12 is a day.', [us&&us.start,sumUS]);
    await closeDlg();
    await importCsv('ymd.csv',DH+'\nUSR-203,Y one,MS,26-10-09,26 10 20\nUSR-204,Y two,MS,26.11.05,26/11/12\n');
    const ym=eng().dataView.getItemById('USR-204');
    ok('import: year first when the first part barely changes (26 on every row), across - . / and space breaks',
       !!ym && ym.start==='2026-11-05' && ym.finish==='2026-11-12' && eng().dataView.getItemById('USR-203').finish==='2026-10-20', ym&&[ym.start,ym.finish]);
    await closeDlg();
    const nD=nRows();
    await importCsv('amb.csv',DH+'\nUSR-205,A one,MS,05/06/26,07/08/26\nUSR-206,A two,MS,09/10/26,11/12/26\n');
    ok('import: dates that could be read either way ask first: "The date order could not be confirmed from the file. Do you wish to continue with import?"',
       !!btn('import-question') && btn('import-question').textContent==='The date order could not be confirmed from the file. Do you wish to continue with import?' &&
       /^Dates will be read as day\/month\/year \(9\/10\/26 is 9-Oct-26\)\. 4 dates would read differently in another order; if that is wrong, choose the order in Date order\.$/.test(btn('import-date-note').textContent) &&
       !$('[data-sg=import-issues]') && nRows()===nD, btn('import-date-note')&&btn('import-date-note').textContent);
    const sel=btn('import-date-order'); sel.value='MDY'; sel.dispatchEvent(new Event('change')); await sleep(20);
    const a5=eng().dataView.getItemById('USR-205');
    ok('import: choosing Month first re-runs the checks and imports with that order; the summary says it was chosen',
       !!a5 && a5.start==='2026-05-06' && a5.finish==='2026-07-08' && $$('[data-sg=import-summary] li')[1].textContent==='Dates read as month/day/year. Chosen in the dialog.', a5&&[a5.start,a5.finish]);
    await closeDlg();
    await importCsv('amb2.csv',DH+'\nUSR-207,B one,MS,05/06/26,\nUSR-208,B two,MS,09/10/26,\n'); btn('import-continue').click(); await sleep(20);
    ok('import: continuing reads the undecided dates day first (the default)', eng().dataView.getItemById('USR-207').start==='2026-06-05');
    await closeDlg();
    // The app's own import form hands in the parsed sheet: same checks, question, log and summary
    const nA=nRows();
    ok('importAoa: same question; the text keeps the dialog colour (host p rules do not leak)', SRETGrid.importAoa([['ID','Name','Predecessor'],['USR-090','From app','NOPE-9']],'app.xlsx')===true &&
       !!btn('import-question') && getComputedStyle(btn('import-question')).color===getComputedStyle(btn('dialog')).color,
       btn('import-question')&&[getComputedStyle(btn('import-question')).color,getComputedStyle(btn('dialog')).color]);
    $$('[data-sg=import-status] button').find(b=>b.textContent==='Cancel').click(); await sleep(10);
    ok('importAoa: Cancel closes the dialog; nothing added', !btn('dialog') && nRows()===nA);
    SRETGrid.importAoa([['ID','Name'],['USR-091','From app']],'app.xlsx'); await sleep(10);
    ok('importAoa: a clean sheet imports and shows the summary', nRows()===nA+1 && $$('[data-sg=import-summary] li')[0].textContent==='Imported 1 milestone.');
    btn('import-done').click(); await sleep(10);
    const nAll=eng().dataView.getItems().length;
    // 1: add to the temp list, across filter states
    ok('1: Add to temp list disabled with nothing selected', btn('temp-add').disabled);
    await setFilter('type','INT'); const intKeys=[0,1].map(r=>eng().dataView.getItem(r).id);
    eng().grid.setSelectedRows([0,1]); await sleep(10);
    const c0=count('onListsChange'); btn('temp-add').click(); await sleep(20);
    ok('1: Add to temp list takes exactly the selected rows (filter state 1)', JSON.stringify(sorted(M.temp(L)))===JSON.stringify(sorted(intKeys.map(k=>'activity:'+k))) && count('onListsChange')===c0+1, M.temp(L));
    const lay=headerLayout();
    ok('header: search in line with the title text; row 2 is search, Add row, Tools, Add to temp list on one line; counts below the buttons (1440px)', lay.bad.length===0, lay);
    ok('status message is a toast over the grid, not in the header', !$('.sg-bar [data-sg=msg],.sg-bar2 [data-sg=msg],.sg-bar3 [data-sg=msg]') &&
       btn('msg').classList.contains('is-shown') && getComputedStyle(btn('msg')).position==='absolute' && msg().indexOf('Added 2 items to My temp list')===0, msg());
    await setFilter('type','CLI'); const cliKey=eng().dataView.getItem(0).id;
    eng().grid.setSelectedRows([0]); await sleep(10); btn('temp-add').click(); await sleep(20);
    await setFilter('type','INT'); eng().grid.setSelectedRows([0]); await sleep(10); btn('temp-add').click(); await sleep(20);
    const againMsg=msg(); await setFilter('type','');
    const picked=intKeys.concat([cliKey]);
    ok('1: builds across three filter states, no duplicates', M.temp(L).length===3 && new Set(M.temp(L)).size===3 &&
       againMsg==='No new items added to My temp list. 1 item was already on it. It now holds 3 items.', [M.temp(L),againMsg]);
    // the temp mark: a vertical line left of the checkbox, the same mark on the rail, title and button
    const markRows=eng().dataView.getItems().filter(i=>{ const n0=eng().grid.getCellNode(rowIdx(i.id),CK()); return n0&&n0.parentNode.classList.contains('sg-in-temp'); }).map(i=>i.id).sort();
    const cs=getComputedStyle(eng().grid.getCellNode(rowIdx(cliKey),CK())), cs0=getComputedStyle(eng().grid.getCellNode(rowIdx(eng().dataView.getItems().find(i=>picked.indexOf(i.id)<0).id),CK()));
    const acc=getComputedStyle(btn('temp-open').querySelector('.sg-tempmark')).backgroundColor;
    ok('1: temp rows marked by a vertical line left of the checkbox (exactly the picked rows)', JSON.stringify(markRows)===JSON.stringify(sorted(picked)) &&
       /3px 0px 0px 0px inset/.test(cs.boxShadow) && cs.boxShadow.indexOf(acc)>=0 && !/3px 0px 0px 0px inset/.test(cs0.boxShadow), [markRows,cs.boxShadow]);
    ok('1: the same mark on the rail button, the Add to temp list button and the panel title', !!btn('temp-add').querySelector('.sg-tempmark') &&
       !!btn('temp-title').querySelector('.sg-tempmark') && getComputedStyle(btn('temp-add').querySelector('.sg-tempmark')).backgroundColor===acc);
    ok('1: rail badge shows 3', btn('temp-count').textContent==='3' && !btn('temp-count').hidden);
    // Add to temp list split menu
    eng().grid.setSelectedRows([rowIdx(cliKey)]); await sleep(10);
    const tm=await menuItem('temp-add-more','temp-only'); const tml=labels('temp-add-more');
    ok('Add to temp list menu: Remove selected from My temp list, Add to each saved list, Show only My temp list',
       tml.join('|')==='Remove selected from My temp list|Add to "Site walk 3-Oct"|Add to "Owner review items"|Show only My temp list' && tm.getAttribute('aria-checked')==='false', tml);
    $('[data-sg=temp-add-more-menu] [data-sg-list="UL-002"]').click(); await sleep(20);
    ok('Add to temp list menu > Add to a list: adds the selected rows straight to that list', JSON.stringify(M.itemsOf(L,'UL-002'))===JSON.stringify(['activity:'+cliKey]) &&
       msg()==='Added 1 item to "Owner review items".', msg());
    await menuPick('temp-add-more','temp-only');
    ok('Show only My temp list: exactly the 3 picked rows; the pill names the filter', visibleCount()===3 && !btn('scope-pill').hidden &&
       btn('scope-pill').textContent.indexOf('My temp list only')===0, visibleCount());
    btn('scope-pill').click(); await sleep(20);
    ok('clicking the pill clears the filter; all rows back', visibleCount()===nAll && btn('scope-pill').hidden);
    eng().grid.setSelectedRows([]); await sleep(10);
    // List column: collapsed indicator, expandable
    const li=colIdx('_list'), lcol=()=>eng().grid.getColumns()[li], cellL=()=>eng().grid.getCellNode(rowIdx(cliKey),li);
    const sortedBefore=JSON.stringify(eng().grid.getSortColumns());
    ok('List column collapsed: narrow, an indicator with the count, the arrow shows collapsed', lcol().width<=60 &&
       !!cellL().querySelector('.sg-inlist-mark') && cellL().textContent==='1' && btn('list-col-toggle').getAttribute('aria-expanded')==='false', [lcol().width,cellL().innerHTML]);
    btn('list-col-toggle').click(); await sleep(20);
    ok('List column expanded: wide, the list names, arrow shows expanded; the click did not sort', lcol().width>=160 && cellL().textContent==='Owner review items' &&
       btn('list-col-toggle').getAttribute('aria-expanded')==='true' && JSON.stringify(eng().grid.getSortColumns())===sortedBefore, [lcol().width,cellL().textContent]);
    await menuPick('tools','list-col');
    ok('Tools > Expand the List column toggles it back', lcol().width<=60 && btn('list-col-toggle').getAttribute('aria-expanded')==='false');
    // 2: My temp list panel, actions above the items
    btn('temp-open').click(); await sleep(30);
    const refs=boxes().map(b=>b.getAttribute('data-sg-item'));
    const pr=btn('panel').getBoundingClientRect(), gr=$('.sg-grid').getBoundingClientRect();
    ok('2: the rail opens a vertical panel docked left of the grid, listing the temp items', !btn('panel').hidden &&
       btn('temp-open').getAttribute('aria-expanded')==='true' && btn('temp-open').classList.contains('is-open') &&
       pr.height>pr.width && Math.abs(pr.right-gr.left)<=1 && JSON.stringify(sorted(refs))===JSON.stringify(sorted(M.temp(L))) &&
       btn('panel-summary').textContent==='3 items, 3 on this screen', [pr.width,pr.height,btn('panel-summary').textContent]);
    const ab=btn('temp-addto').getBoundingClientRect(), tb=btn('temp-title').getBoundingClientRect(), ib=btn('panel-items').getBoundingClientRect();
    ok('2: action buttons sit below the title and above the items', ab.top>=tb.bottom && ab.bottom<=ib.top, [tb.bottom,ab.top,ab.bottom,ib.top]);
    ok('2: Add to list and Remove disabled until items are selected', btn('temp-addto').disabled && btn('temp-remove').disabled);
    R.notes.swap_temp=swapEscapes('light/temp-panel');
    await pick([0,1]); const two=refs.slice(0,2);
    ok('2: selecting items shows the count and a partial select-all', btn('panel-picked').textContent==='(2 selected)' && btn('panel-all').indeterminate);
    btn('temp-addto').click(); await sleep(10);
    const al=labels('temp-addto');
    ok('2: Add to list menu lists the saved lists and New list…', al.join('|')==='Site walk 3-Oct (0)|Owner review items (1)|New list…', al);
    R.notes.swap_menu=swapEscapes('light/add-to-list-menu');
    $('[data-sg=temp-addto-menu] [data-sg-list="UL-001"]').click(); await sleep(20);
    const sw=L.list.find(c=>c.id==='UL-001');
    ok('2: adds only the selected temp items; temp list unchanged; menu closed', JSON.stringify(sorted(sw.items))===JSON.stringify(sorted(two)) &&
       M.temp(L).length===3 && msg()==='Added 2 items to "Site walk 3-Oct".' && btn('temp-addto-menu').hidden, [msg(),sw.items]);
    await pick([1,2]);
    await menuPick('temp-addto','temp-newlist');
    const nm=btn('temp-name');
    ok('2: New list… opens the name form with the field focused', !btn('temp-newlist-form').hidden && document.activeElement===nm);
    const errs=[];
    for(const v of ['  ','site WALK 3-oct','My temp list']){ nm.value=v; key(nm,'Enter'); await sleep(10); errs.push(btn('panel-err').textContent); }
    ok('2: empty, duplicate and reserved names refused; nothing changes', errs[0]==='Enter a name for the list.' && /already exists/.test(errs[1]) &&
       /used by the temp list/.test(errs[2]) && M.list(L).length===2, errs);
    nm.value='Punch list'; btn('temp-newlist-save').click(); await sleep(20);
    const pl=L.list.find(c=>c.name==='Punch list');
    ok('2: new list made from the selected items; form closes', !!pl && JSON.stringify(sorted(pl.items))===JSON.stringify(sorted(refs.slice(1,3))) &&
       msg()==='Saved 2 items as the new list "Punch list".' && btn('temp-newlist-form').hidden, [msg(),pl&&pl.items]);
    const both=refs[1];
    ok('multiple lists per item: one item in both lists, shown in the panel', JSON.stringify(M.membership(L,both))===JSON.stringify(['Site walk 3-Oct','Punch list']) &&
       $$('.sg-temp-item').some(li=>li.querySelector('input').getAttribute('data-sg-item')===both && li.querySelector('.sg-temp-item-lists').textContent==='Site walk 3-Oct, Punch list'));
    // 3: remove from the temp list
    const lists0=JSON.stringify(L.list);
    await pick([0]); const gone=boxes()[0].getAttribute('data-sg-item');
    btn('temp-remove').click(); await sleep(20);
    ok('3: Remove takes only the selected items off the temp list; saved lists unchanged', M.temp(L).length===2 && !M.inTemp(L,gone) &&
       boxes().length===2 && JSON.stringify(L.list)===lists0 && btn('temp-count').textContent==='2', M.temp(L));
    // 4: clear, via More, with inline confirmation
    await menuItem('temp-more','temp-clear'); const ml=labels('temp-more'); await menuClose('temp-more');
    ok('More: Show only these rows in the table, Clear temp list', ml.join('|')==='Show only these rows in the table|Clear temp list…', ml);
    await menuPick('temp-more','temp-clear');
    const cf=btn('panel-confirm'), cb=$$('button',cf).map(b=>b.textContent);
    ok('4: Clear asks first, with the count; Cancel left, Clear right (danger)', !cf.hidden &&
       $('[data-sg=panel-confirm] .sg-confirm-msg').textContent==='Clear My temp list (2 items)? Saved lists are not changed.' &&
       cb.join('|')==='Cancel|Clear' && $$('button',cf)[1].classList.contains('sg-btn--danger'), cb);
    key(document.activeElement,'Escape'); await sleep(10);
    ok('4: Esc cancels the clear; panel stays open', cf.hidden && !btn('panel').hidden && M.temp(L).length===2);
    await menuPick('temp-more','temp-clear'); btn('temp-clear-confirm').click(); await sleep(20);
    ok('4: Clear empties the temp list and leaves saved lists unchanged', M.temp(L).length===0 && JSON.stringify(L.list)===lists0 &&
       msg()==='Cleared My temp list (2 items).' && itemsIn('Yes').length===0 && btn('temp-count').hidden && $$('.sg-temp-empty').length===1, msg());
    // Saved lists: the second rail button, same panel style, a dropdown picks the list
    btn('lists-open').click(); await sleep(20);
    const opts=Array.from(btn('list-pick').options).map(o=>o.textContent);
    ok('Saved lists: the rail button switches the panel; the header is a dropdown of saved lists', !btn('panel').hidden && btn('panel').getAttribute('data-mode')==='list' &&
       btn('lists-open').getAttribute('aria-expanded')==='true' && btn('temp-open').getAttribute('aria-expanded')==='false' &&
       opts.join('|')==='Site walk 3-Oct (2)|Owner review items (1)|Punch list (2)' && btn('temp-title').offsetParent===null, opts);
    const lb=btn('list-remove').getBoundingClientRect(), pk=btn('list-pick').getBoundingClientRect(), ib2=btn('panel-items').getBoundingClientRect();
    ok('Saved lists: actions below the header dropdown and above the items', lb.top>=pk.bottom && lb.bottom<=ib2.top);
    btn('list-pick').value=pl.id; btn('list-pick').dispatchEvent(new Event('change')); await sleep(10);
    ok('Saved lists: choosing a list shows its items', JSON.stringify(sorted(boxes().map(b=>b.getAttribute('data-sg-item'))))===JSON.stringify(sorted(pl.items)));
    await menuPick('list-more','list-only-panel');
    ok('Saved lists > More > Show only these rows: the grid shows that list; the pill names it', visibleCount()===pl.items.length &&
       btn('scope-pill').textContent.indexOf('List: Punch list')===0, [visibleCount(),btn('scope-pill').textContent]);
    btn('scope-pill').click(); await sleep(20);
    await pick([0]); const rm=boxes()[0].getAttribute('data-sg-item'), keepSw=JSON.stringify(sw.items);
    btn('list-remove').click(); await sleep(20);
    ok('Saved lists > Remove from list: only this list changes', pl.items.length===1 && pl.items.indexOf(rm)<0 && JSON.stringify(sw.items)===keepSw &&
       msg()==='Removed 1 item from "Punch list".', msg());
    await menuPick('list-more','list-delete');
    ok('Saved lists > Delete list asks first', !btn('panel-confirm').hidden && /^Delete the list "Punch list" \(1 item\)\?/.test($('[data-sg=panel-confirm] .sg-confirm-msg').textContent));
    btn('list-delete-confirm').click(); await sleep(20);
    ok('Saved lists > Delete list removes the list; the dropdown moves to another list', !L.list.some(c=>c.name==='Punch list') &&
       Array.from(btn('list-pick').options).length===2 && btn('list-pick').value==='UL-001' &&
       msg()==='Deleted the list "Punch list" (1 item). The items themselves are unchanged.', msg());
    key(btn('list-pick'),'Escape'); await sleep(10);
    ok('panel: Esc collapses it, rail shows collapsed, focus back on the rail button', btn('panel').hidden && btn('lists-open').getAttribute('aria-expanded')==='false' &&
       document.activeElement===btn('lists-open'));
    eng().grid.setSelectedRows([]); await sleep(10); }

  // idle palette swap, both themes, and theming differs between themes
  { R.notes.swap_idle_light=swapEscapes('light/idle');
    const bgL=getComputedStyle($('.sg-grid .slick-row')).backgroundColor, hdL=getComputedStyle($('.sg-bar')).backgroundColor, txL=getComputedStyle($('.sg-grid .slick-cell')).color;
    document.documentElement.setAttribute('data-theme','dark'); await sleep(10);
    R.notes.swap_idle_dark=swapEscapes('dark/idle');
    const bgD=getComputedStyle($('.sg-grid .slick-row')).backgroundColor, hdD=getComputedStyle($('.sg-bar')).backgroundColor, txD=getComputedStyle($('.sg-grid .slick-cell')).color;
    document.documentElement.setAttribute('data-theme','light'); await sleep(10);
    ok('light and dark both themed (row, toolbar, text differ)', bgL!==bgD && hdL!==hdD && txL!==txD, {bgL,bgD,hdL,hdD,txL,txD});
    const esc=[].concat(R.notes.swap_idle_light,R.notes.swap_idle_dark,R.notes.swap_edit_light,R.notes.swap_edit_dark,R.notes.swap_confirm,R.notes.swap_temp,R.notes.swap_menu,R.notes.swap_dialog);
    ok('palette swap: every painted colour in the screen moves with --pal-* (idle, editing, confirm, panel, open menu, dialog; both themes)', esc.length===0, esc.slice(0,12)); }

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
    ok('annot: no Add (no onAdd); Delete in Tools', !$('[data-sg=add]') && !!(await menuItem('tools','delete'))); await menuClose('tools');
    const rk=eng().dataView.getItem(2).aid; await editCell(2,'value','Revised comment text'); const e=lastLog('onEdit');
    ok('annot: comment edit reaches onEdit', e.args[0]===rk && e.args[1]==='value' && e.args[2]==='Revised comment text', e.args);
    await editCell(3,'status','done'); const e2=lastLog('onEdit');
    ok('annot: status select edit reaches onEdit', e2.args[1]==='status' && e2.args[2]==='done', e2.args);
    const res=[]; for(const k of ['aid','kind','target']) res.push(await tryOpenEditor(0,k));
    ok('annot: read-only columns refuse edits (N=3)', res.every(x=>x===false), res);
    SRETGrid.close(); }

  // ============ Views from the title (Matt, 2026-09-28) ============
  { const btn=n=>$('[data-sg='+n+']'), launcher=$('#go-userms');
    SRETGrid.close(); launcher.focus(); DEMO_OPEN('userms'); await sleep(20);
    const nUms=eng().dataView.getItems().length, nMs=F.sched.filter(r=>r.dur===0).length, nUpd=F.sched.filter(r=>!!(r.short||r.comment||(r.health!=null&&r.health!==''))).length;
    const vb=btn('view'), fs=getComputedStyle(vb).fontSize, tfs=getComputedStyle($('.sg-title')).fontSize;
    ok('views: the title is a menu button in the heading\'s own size, labelled User milestones', !!vb && vb.textContent==='User milestones' &&
       vb.getAttribute('aria-haspopup')==='menu' && fs===tfs && fs==='20px' && vb.title==='Switch view', [vb&&vb.textContent,fs,tfs]);
    vb.click(); await sleep(10);
    const items=$$('[data-sg=view-menu] .sg-menu-item'), pop=btn('view-menu'), pr=pop.getBoundingClientRect();
    const hit=document.elementFromPoint(pr.left+pr.width/2,pr.top+pr.height/2);
    ok('views: the menu lists User milestones, Schedule milestones, Schedule updates, All schedule activities with counts; the current one checked',
       items.map(i=>i.textContent.replace(/^✓/,'')).join('|')==='User milestones ('+nUms+')|Schedule milestones ('+nMs+')|Schedule updates ('+nUpd+')|All schedule activities ('+F.sched.length+')' &&
       items.every(i=>i.getAttribute('role')==='menuitemradio') && items[0].getAttribute('aria-checked')==='true' && items[1].getAttribute('aria-checked')==='false',
       items.map(i=>i.textContent));
    ok('views: the menu is not clipped by the heading (hit test lands inside it)', pr.height>40 && pop.contains(hit), [pr.height,hit&&hit.className]);
    btn('view-schedms').click(); await sleep(20);
    const focusAfter=document.activeElement===btn('view'), ms=eng().dataView.getItems();
    ok('views: Schedule milestones shows only zero-duration schedule activities, read-only schedule columns kept', lastLog('onView').args[0]==='schedms' &&
       btn('view').textContent==='Schedule milestones' && ms.length===nMs && nMs>0 && ms.every(r=>r.dur===0) && !(await tryOpenEditor(0,'finish')), [ms.length,nMs]);
    ok('views: after a switch, focus is on the view button', focusAfter);
    await menuPick('view','view-schedupd');
    const up=eng().dataView.getItems();
    ok('views: Schedule updates shows only schedule rows with an annotation (short title, health or comment)', btn('view').textContent==='Schedule updates' &&
       up.length===nUpd && nUpd>0 && up.every(r=>!!(r.short||r.comment||(r.health!=null&&r.health!==''))), [up.length,nUpd]);
    const rk=eng().dataView.getItem(0).id; await editCell(0,'comment','Checked at the site walk');
    await menuPick('view','view-sched'); const all=eng().dataView.getItemById(rk);
    ok('views: an annotation edited in one view is there in another (All schedule activities)', !!all && all.comment==='Checked at the site walk' && visibleCount()===F.sched.length);
    btn('back').click(); await sleep(20);
    ok('views: Back after switching views returns to where the grid was opened from', !SRETGrid.isOpen() && document.activeElement===launcher, document.activeElement&&document.activeElement.id);
    DEMO_OPEN('annot'); await sleep(20);
    ok('views: a screen without views keeps a plain title', !btn('view') && $('.sg-title').textContent.indexOf('Annotations')===0);
    SRETGrid.close(); DEMO_OPEN('userms'); await sleep(20); }

  // ============ Schedule activities + export ============
  { DEMO_OPEN('sched'); await sleep(20);
    ok('sched: title and row count', $('.sg-title').textContent==='Schedule activities' && visibleCount()===F.sched.length && F.sched.length>100,
       [visibleCount(),F.sched.length]);
    ok('sched: panel collapsed on open; a plain Export button (no Add row)', $('[data-sg=panel]').hidden && !!$('[data-sg=export]') && !$('[data-sg=add-more]'));
    ok('sched: no Add, no Delete (read-only schedule)', !$('[data-sg=add]') && !(await menuItem('tools','delete'))); await menuClose('tools');
    const res=[]; for(const k of ['id','name','start','finish','float']) res.push(await tryOpenEditor(1,k));
    ok('sched: schedule columns refuse edits (N=5)', res.every(x=>x===false), res);
    const rk=eng().dataView.getItem(1).id; await editCell(1,'health','2'); const e=lastLog('onEdit');
    ok('sched: annotation column (health) edits, numeric option value kept', e.args[0]===rk && e.args[1]==='health' && e.args[2]===2, e.args);
    ok('sched: health shows its label', cellText(1,'health')==='At risk', cellText(1,'health'));
    // the temp list is shared across screens: pick here, see it on User milestones
    { const L=window.DEMO_LISTS, k=[0,1].map(r=>eng().dataView.getItem(r).id);
      eng().grid.setSelectedRows([0,1]); await sleep(10); $('[data-sg=temp-add]').click(); await sleep(20);
      eng().grid.setSelectedRows([]); SRETGrid.close(); DEMO_OPEN('userms'); await sleep(20);
      ok('temp list carries across screens (2 schedule rows picked, then seen on User milestones)',
         $('[data-sg=temp-count]').textContent==='2' && k.every(x=>SRETCollections.inTemp(L,'activity:'+x)),
         $('[data-sg=temp-count]').textContent);
      SRETCollections.tempClear(L); SRETGrid.close(); DEMO_OPEN('sched'); await sleep(20); }
    // export visible rows after a filter and a sort
    await setFilter('wbs','Key'); header('finish').click(); await sleep(20);
    const vis=visibleCount();
    await SRETGrid.exportVisible();
    const aoa=window.__xlsx.aoa||[];
    ok('export: header row plus exactly the visible rows', aoa.length===vis+1 && vis>0 && vis<F.sched.length, [aoa.length,vis]);
    ok('export: headers are List, then the column labels', JSON.stringify(aoa[0])===JSON.stringify(['List'].concat(F.cols.sched.map(c=>c.label))), aoa[0]);
    const fi=aoa[0].indexOf('Finish'), ii=aoa[0].indexOf('Activity ID');
    const firstId=eng().dataView.getItem(0).id;
    ok('export: row order follows the sort', aoa[1][ii]===firstId, [aoa[1]&&aoa[1][ii],firstId]);
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
    const lay2=headerLayout();
    ok('header: layout holds with a long title', lay2.bad.length===0 && $('.sg-title').scrollWidth>=$('.sg-title').clientWidth, lay2);
    const domRows=$$('.sg-grid .slick-row').length; R.notes.dom_rows_2000=domRows;
    ok('stress: virtual rendering (DOM rows far below 2,000)', domRows>0 && domRows<150, domRows);
    eng().grid.scrollRowIntoView(1999); await sleep(50);
    const lastId=eng().dataView.getItem(1999).id;
    ok('stress: last row reachable by scrolling', $$('.sg-grid .slick-cell.l'+colIdx('id')).some(c=>c.textContent===lastId), lastId);
    SRETGrid.close(); }
  // shared module, direct
  { const M=SRETCollections, st=M.newStore();
    const a=M.create(st,'  Weekly   review ','2026-09-27T00:00:00Z');
    ok('module: name trimmed and spaces collapsed; ids sequential', a.collection.name==='Weekly review' && a.collection.id==='UL-001');
    ok('module: 61-character name refused', !!M.create(st,'x'.repeat(61)).error);
    const t=M.tempAdd(st,['a','a','b','c']);
    ok('module: duplicate refs in one temp add count once', t.added===3 && t.total===3, t);
    ok('module: step 2 needs selected temp items; refs not on the temp list are ignored', !!M.addFromTemp(st,'UL-001',[]).error && !!M.addFromTemp(st,'UL-001',['zz']).error);
    M.saveFromTemp(st,'Scope 1',['a','b']); M.addFromTemp(st,'UL-001',['b','c']);
    ok('module: default allows several lists per item; temp list untouched by step 2', JSON.stringify(M.membership(st,'b'))===JSON.stringify(['Weekly review','Scope 1']) && M.temp(st).length===3, st.list);
    const one=M.newStore({singleList:true}); M.create(one,'X'); M.create(one,'Y'); M.tempAdd(one,['p','q']);
    M.addFromTemp(one,'UL-001',['p','q']); const mv=M.addFromTemp(one,'UL-002',['p']);
    ok('module: settings.singleList (future setting) moves the item and says from where', JSON.stringify(M.membership(one,'p'))===JSON.stringify(['Y']) &&
       mv.movedFrom.X===1 && / Moved from "X" \(1\)\./.test(M.describe(mv)), M.describe(mv));
    ok('module: unknown list is an error, not a throw', !!M.assign(st,'UL-999',['c']).error && !!M.addFromTemp(st,'UL-999',['a']).error);
    const u=M.unassign(st,['b','zz']);
    ok('module: unassign takes an item out of every list', u.removed===1 && M.membership(st,'b').length===0, u);
    const msgs=[M.describe(mv),M.describe(u),M.describe(M.tempAdd(st,['q'])),M.describe(M.tempRemove(st,['q'])),M.describe(M.tempClear(st))];
    ok('module: user-facing sentences have no em or en dashes', msgs.every(m=>!/[–—]/.test(m)), msgs); }
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
