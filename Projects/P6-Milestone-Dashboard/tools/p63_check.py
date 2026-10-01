#!/usr/bin/env python3
"""
P63 check: the grid opened from the Workspace panel where the panel overlays
the board, and the view switcher in the grid title (TD-223).

Runs the real app in headless Chromium with the host resolver pointed at
nothing, and reads DOM, classList, elementFromPoint and store contents, never
a screenshot. Four page loads, so each part starts from a clean app:

  mobile  390x844, where the Workspace panel is full width over the board.
          Three user milestones and three milestone comments are made
          through the real paths. From Comments & markups, View opens the
          grid, the Workspace panel is closed and the grid is the element at
          its own centre (inside #grid-host). Back reopens the panel on
          Comments & markups with focus on that View button. The same for
          User milestones > View items. Back after switching views from the
          title still returns to the section and button the grid was opened
          from. The switcher's title fits the screen, with no sideways page
          scroll.
  tablet  900x800, below the docking breakpoint: the same panel behaviour
          (the panel overlays there too).
  desktop 1440x900, where the panel docks: the panel stays open while the
          grid is open, the grid is at its centre, the icon bar and report
          header stay clickable, and Back returns focus to the button with
          the panel still on its section.
  switch  1440x900. N=3 user milestones, N=3 milestone comments and one
          health override. The title is a menu button (aria-haspopup=menu,
          an accessible name) listing exactly: User milestones (3), Milestone
          comments (3), Milestone health overrides (1), Schedule milestones,
          Schedule updates (3), All schedule activities, with counts from the
          stores; empty annotation types are absent; the current view is
          checked. Each view switched to shows its row count and title.
          Schedule views: schedule columns have no editor, an attempted edit
          opens none, the adapter refuses every schedule column, there is no
          Add row and no Delete, and TASKS, MILESTONES and USER_MILESTONES
          deep-compare equal to a snapshot. Annotation edits land in the right
          store and no other: comment, health and short title from Schedule
          milestones; the row remark and row health from All schedule
          activities. Schedule updates then lists the newly annotated
          milestone. Keyboard: ArrowDown opens the menu on its first item,
          arrows move, Esc closes it back to the button, and Enter (native
          button activation) switches view with focus on the new title.
          Back after several switches returns to where the grid was first
          opened, for both origins.

Source assertions: the four tag counts are 1; the version grep returns 1 and
APP_VERSION is 3.1.0-P63 or later; no script start tag inside a script; no CDN
URL; no em or en dash in the P63 view labels and columns.

Usage:
  python3 tools/p63_check.py [--html FILE]
Exit code 1 if any assertion fails.
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
OUT_RE = re.compile(r'<pre id="p63-out">(.*?)</pre>', re.S)

MODES = {
    "mobile": (390, 844),
    "tablet": (900, 800),
    "desktop": (1440, 900),
    "switch": (1440, 900),
}

PROBE = r"""
(function(){
  const MODE=__MODE__;
  try{ localStorage.clear(); }catch(e){}
  document.head.insertAdjacentHTML('beforeend','<style>*,*::before,*::after{transition:none!important;animation:none!important}</style>');
  const R={checks:[]};
  function ck(n,p,d){ R.checks.push({name:'['+MODE+'] '+n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p63-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const hitIn=(el,sel)=>{ const r=rc(el); const at=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
                          return !!at&&!!at.closest(sel); };
  const panelOpen=()=>{ const p=$('ws-panel'); return !!p&&p.classList.contains('open')&&getComputedStyle(p).display!=='none'; };
  const host=()=>$('grid-host');
  const titleBtn=()=>document.querySelector('#grid-host [data-sg="view"]');
  const titleText=()=>{ const t=document.querySelector('#grid-host .sg-title'); return t?t.textContent:''; };
  const eng=()=>SRETGrid._engine&&SRETGrid._engine();
  const rows=()=>{ const E=eng(); return E?E.dataView.getLength():-1; };
  const colIdx=k=>eng().grid.getColumns().findIndex(c=>c.id===k);
  const snap=()=>({comments:JSON.stringify(MS_COMMENTS),msHealth:JSON.stringify(MS_HEALTH_OVERRIDE),
    msProgress:JSON.stringify(MS_PROGRESS_OVERRIDE),msFields:JSON.stringify(MS_FIELD_OVERRIDE),
    shortTitles:JSON.stringify(MS_SHORT_TITLES),depComments:JSON.stringify(DEP_COMMENTS),
    notes:JSON.stringify(NOTES),rowOverrides:JSON.stringify(snapshotOverrides()),
    TASKS:JSON.stringify(TASKS),MILESTONES:JSON.stringify(MILESTONES),USER_MILESTONES:JSON.stringify(USER_MILESTONES)});
  const diff=(a,b)=>Object.keys(a).filter(k=>a[k]!==b[k]);
  // Deep copy of the schedule arrays, compared value by value afterwards.
  const schedSnap=()=>JSON.parse(JSON.stringify({TASKS:TASKS,MILESTONES:MILESTONES,USER_MILESTONES:USER_MILESTONES}));
  function deepEq(a,b){
    if(a===b) return true;
    if(typeof a!==typeof b||a===null||b===null||typeof a!=='object') return false;
    if(Array.isArray(a)!==Array.isArray(b)) return false;
    const ka=Object.keys(a), kb=Object.keys(b);
    if(ka.length!==kb.length) return false;
    return ka.every(k=>Object.prototype.hasOwnProperty.call(b,k)&&deepEq(a[k],b[k]));
  }
  function addMs(name){ openAddMilestone(); $('add-ms-name').value=name; saveAddMilestone(); }
  function boardKeys(){
    const out=[], seen={};
    document.querySelectorAll('#tbody .m-wrap[data-ms]').forEach(function(w){
      if(w.classList.contains('m-ghost')||w.classList.contains('m-wrap-loe')) return;
      const id=w.getAttribute('data-ms'); if(seen[id]||/^USR-/.test(id)) return; seen[id]=1; out.push(w); });
    return out;
  }
  // Three user milestones, three milestone comments through the card and,
  // with health, a health override on the first.
  async function seed(health){
    addMs('Probe one'); addMs('Probe two'); addMs('Probe three');
    await wait(120);
    const wraps=boardKeys(), keys=[];
    for(let i=0;i<3;i++){
      wraps[i].click(); await wait(60);
      keys.push(msDialogFor);
      $('ms-comment-text').value='Probe comment '+(i+1); onMsCommentInput();
      if(health&&i===0) onMsHealthClick(document.querySelector('#ms-dialog .health-dot[data-val="1"]'));
      saveMsDialog(true); await wait(20);
    }
    await wait(300);
    return {keys:keys,wraps:wraps};
  }
  function gridOnTop(label){
    const scr=document.querySelector('#grid-host .sg-screen');
    ck(label+': the grid is open in #grid-host', SRETGrid.isOpen()&&!!scr&&!host().hidden);
    if(!scr) return;
    const r=rc(scr), at=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
    ck(label+': the element at the grid centre is inside #grid-host', !!at&&!!at.closest('#grid-host'),
       at?(at.id||at.className||at.tagName):'none');
  }
  async function pressBack(){
    const b=document.querySelector('#grid-host [data-sg="back"]'); if(b) b.click();
    await wait(300);
  }
  async function pick(viewId){
    const tb=titleBtn(); if(!tb) return false;
    tb.click(); await wait(30);
    const it=document.querySelector('#grid-host [data-sg="view-'+viewId+'"]');
    if(!it) return false;
    it.click(); await wait(150);
    return true;
  }

  // ---- panel behaviour: mobile and tablet (overlay) ----
  async function overlayMode(){
    ck('viewport is below the docking breakpoint ('+innerWidth+'px)', !matchMedia('(min-width:1025px)').matches, innerWidth);
    await seed(false);
    // Comments & markups
    setWorkspaceSection('comments',true); await wait(40);
    const vb=$('btn-ye-view-comments');
    ck('Comments & markups is open, with a View button', panelOpen()&&!!vb);
    if(!vb) return;
    const ml=parseFloat(getComputedStyle(document.body).marginLeft), pr=rc($('ws-panel')).right;
    ck('the panel overlays the board here (the body makes no room for it)', pr>ml+100, 'panel right '+pr+', body margin '+ml);
    vb.focus(); vb.click(); await wait(150);
    ck('comments: View closes the Workspace panel', !panelOpen()&&!document.body.classList.contains('ws-open'));
    gridOnTop('comments');
    const tb=titleBtn();
    ck('comments: the title switcher fits the screen', !!tb&&rc(tb).right<=innerWidth+0.5&&rc(tb).left>=0, tb&&JSON.stringify(rc(tb)));
    ck('comments: no sideways page scroll', document.documentElement.scrollWidth<=innerWidth, document.documentElement.scrollWidth);
    await pressBack();
    ck('comments: Back closes the grid', !SRETGrid.isOpen()&&!document.body.classList.contains('grid-open'));
    ck('comments: Back reopens the panel on Comments & markups', panelOpen()&&WS_SECTION==='comments', WS_SECTION);
    const a1=document.activeElement;
    ck('comments: focus is on the same View button', !!a1&&a1.id==='btn-ye-view-comments', a1&&a1.id);
    ck('comments: that button is visible and on top', !!a1&&a1.id==='btn-ye-view-comments'&&hitIn(a1,'#btn-ye-view-comments'));

    // User milestones
    setWorkspaceSection('userms',true); await wait(40);
    const ub=$('btn-userms-view');
    ck('User milestones is open, with View items', panelOpen()&&!!ub);
    if(!ub) return;
    ub.focus(); ub.click(); await wait(150);
    ck('userms: View items closes the Workspace panel', !panelOpen());
    gridOnTop('userms');
    ck('userms: the grid holds the three user milestones', rows()===3, rows());
    await pressBack();
    ck('userms: Back reopens the panel on User milestones', panelOpen()&&WS_SECTION==='userms', WS_SECTION);
    const a2=document.activeElement;
    ck('userms: focus is on View items', !!a2&&a2.id==='btn-userms-view', a2&&a2.id);
    ck('userms: View items is visible and on top', !!a2&&a2.id==='btn-userms-view'&&hitIn(a2,'#btn-userms-view'));

    // Switch views, then Back: still the origin.
    setWorkspaceSection('comments',true); await wait(40);
    $('btn-ye-view-comments').focus(); $('btn-ye-view-comments').click(); await wait(150);
    const ok1=await pick('sched-ms'), ok2=ok1&&await pick('userms');
    ck('switched twice from the title (Schedule milestones, User milestones)', ok1&&ok2&&/^User milestones/.test(titleText()), titleText());
    ck('the panel stays closed while switching', !panelOpen());
    gridOnTop('after switching');
    await pressBack();
    const a3=document.activeElement;
    ck('Back after switching reopens Comments & markups with focus on its View button',
       panelOpen()&&WS_SECTION==='comments'&&!!a3&&a3.id==='btn-ye-view-comments', WS_SECTION+' '+(a3&&a3.id));
  }

  // ---- panel behaviour: desktop (docked) ----
  function headerClickable(){
    const ib=$('icon-bar'), hd=document.querySelector('.rpt-hd');
    const shown=[...ib.querySelectorAll('button[id]')].filter(b=>rc(b).width>0&&rc(b).height>0);
    return hitIn(ib,'#icon-bar')&&hitIn(hd,'.rpt-hd')&&shown.length>0&&shown.every(b=>hitIn(b,'#'+b.id));
  }
  async function desktopMode(){
    ck('viewport docks the panel ('+innerWidth+'px)', matchMedia('(min-width:1025px)').matches, innerWidth);
    await seed(false);
    for(const [sec,id] of [['comments','btn-ye-view-comments'],['userms','btn-userms-view']]){
      setWorkspaceSection(sec,true); await wait(40);
      const b=$(id);
      ck(sec+': the panel is open and docked (the body makes room for it)', panelOpen()&&document.body.classList.contains('ws-open')&&
         parseFloat(getComputedStyle(document.body).marginLeft)>100, getComputedStyle(document.body).marginLeft);
      if(!b) { ck(sec+': the button exists', false); continue; }
      b.focus(); b.click(); await wait(150);
      ck(sec+': the panel stays open while the grid is open (unchanged)', panelOpen()&&document.body.classList.contains('ws-open'));
      gridOnTop(sec);
      ck(sec+': the icon bar and report header stay clickable (elementFromPoint)', headerClickable());
      await pressBack();
      const a=document.activeElement;
      ck(sec+': Back returns focus to the button, the panel still on its section', !!a&&a.id===id&&panelOpen()&&WS_SECTION===sec,
         (a&&a.id)+' '+WS_SECTION);
    }
  }

  // ---- the view switcher ----
  async function switchMode(){
    const s=await seed(true);
    const [K1,K2,K3]=s.keys;
    const nonUser=MILESTONES.filter(m=>(m.source||'')!=='User-defined');
    const expMs=new Set(nonUser.map(m=>msKeyFor(m))).size;
    const expAll=new Set(TASKS.filter(t=>(t.sourceSchedule||'')!=='User-defined').map(t=>t.ref)).size;
    ck('the schedule has milestones and rows to show', expMs>3&&expAll>0, expMs+' '+expAll);
    setWorkspaceSection('userms',true); await wait(40);
    $('btn-userms-view').focus(); $('btn-userms-view').click(); await wait(150);
    const tb=titleBtn();
    ck('the grid title is a menu button', !!tb&&tb.getAttribute('aria-haspopup')==='menu'&&!!tb.closest('.sg-title'));
    if(!tb) return;
    ck('it has an accessible name (its text, the current view)', tb.textContent.trim()==='User milestones', tb.textContent);
    ck('User milestones opens with its three rows', rows()===3, rows());
    tb.click(); await wait(30);
    const pop=document.querySelector('#grid-host [data-sg="view-menu"]');
    const items=[...document.querySelectorAll('#grid-host [data-sg^="view-"].sg-menu-item')];
    const labels=items.map(i=>i.textContent.replace(/^✓/,'').trim());
    const want=['User milestones (3)','Milestone comments (3)','Milestone health overrides (1)',
                'Schedule milestones ('+expMs+')','Schedule updates (3)','All schedule activities ('+expAll+')'];
    ck('the menu lists exactly the expected views, in order, with counts', JSON.stringify(labels)===JSON.stringify(want), JSON.stringify(labels));
    ck('the menu is a labelled menu of radio items', !!pop&&pop.getAttribute('role')==='menu'&&!!pop.getAttribute('aria-label')&&
       items.every(i=>i.getAttribute('role')==='menuitemradio'));
    ck('the current view is the checked one', items.filter(i=>i.getAttribute('aria-checked')==='true').map(i=>i.getAttribute('data-sg')).join()==='view-userms');
    ck('empty annotation types are not listed', !items.some(i=>/Custom short titles|Notes|progress|field edits|Row health|Dependency/.test(i.textContent)));
    tb.click(); await wait(20);

    // Each view: rows and title.
    const expect={'annot:comments':['Milestone comments (3)',3],'annot:msHealth':['Milestone health overrides (1)',1],
      'sched-ms':['Schedule milestones ('+expMs+')',expMs],'sched-upd':['Schedule updates (3)',3],
      'sched-all':['All schedule activities ('+expAll+')',expAll],'userms':['User milestones',3]};
    for(const id of Object.keys(expect)){
      const ok=await pick(id);
      ck('switch to '+id+': title "'+expect[id][0]+'" and '+expect[id][1]+' rows',
         ok&&titleText()===expect[id][0]&&rows()===expect[id][1], titleText()+' / '+rows());
      ck('switch to '+id+': no trip back to the panel (still in the grid)', SRETGrid.isOpen()&&document.body.classList.contains('grid-open'));
    }
    ck('Schedule updates lists the three commented milestones',
       await pick('sched-upd')&&[K1,K2,K3].every(k=>!!eng().dataView.getItemById(k)));

    // ---- Schedule milestones: read only schedule, editable annotations ----
    await pick('sched-ms');
    const E=eng(), g=E.grid, dv=E.dataView, h=host();
    const schedCols=['id','name','band','start','finish','float','state','progress'];
    ck('sched-ms: the schedule columns are all there', schedCols.every(c=>colIdx(c)>=0), g.getColumns().map(c=>c.id).join());
    ck('sched-ms: schedule columns have no editor', schedCols.every(c=>colIdx(c)>=0&&g.getColumns()[colIdx(c)].editor==null));
    ck('sched-ms: comment, health and short title are editable', ['comment','health','shortTitle'].every(c=>colIdx(c)>=0&&!!g.getColumns()[colIdx(c)].editor));
    ck('sched-ms: no Add row and no Delete', !h.querySelector('[data-sg="add"]')&&!h.querySelector('[data-sg="tools"]')&&!h.querySelector('[data-sg="add-more"]'));
    const K4=Object.keys(dv.getItems().reduce((o,r)=>(o[r.key]=1,o),{})).find(k=>![K1,K2,K3].includes(k));
    const r4=dv.getItemById(K4);
    ck('sched-ms: a row shows the schedule\'s own values', !!r4&&r4.id===msId(findMilestoneById(r4.id))&&!!r4.finish, JSON.stringify(r4));
    const base=schedSnap();
    let s0=snap();
    // Try to edit every schedule column through the engine: no editor opens.
    const opened=[];
    for(const c of schedCols){
      g.setActiveCell(dv.getIdxById(K4),colIdx(c)); g.editActiveCell();
      if(h.querySelector('.sg-editor')){ opened.push(c); g.getEditorLock().cancelCurrentEdit(); }
    }
    ck('sched-ms: an edit on a schedule column opens no editor', opened.length===0, opened.join());
    const refused=schedCols.map(c=>schedGridEdit(K4,c,c==='progress'||c==='float'?5:'Probe')).every(v=>v===false);
    ck('sched-ms: the adapter refuses a write to every schedule column', refused);
    ck('sched-ms: nothing changed', JSON.stringify(diff(s0,snap()))==='[]', JSON.stringify(diff(s0,snap())));
    async function edit(key,col,val){
      g.scrollRowIntoView(dv.getIdxById(key)); g.setActiveCell(dv.getIdxById(key),colIdx(col)); g.editActiveCell();
      const ed=h.querySelector('.sg-editor'); if(!ed) return 'no editor';
      ed.value=String(val); g.getEditorLock().commitCurrentEdit(); await wait(40);
      const it=dv.getItemById(key); return it?it[col]:undefined;
    }
    s0=snap();
    await edit(K4,'comment','Comment from the schedule view');
    ck('sched-ms: a comment lands in MS_COMMENTS and no other store', MS_COMMENTS[K4]==='Comment from the schedule view'&&
       JSON.stringify(diff(s0,snap()))==='["comments"]', JSON.stringify(diff(s0,snap())));
    s0=snap();
    await edit(K4,'health',4);
    ck('sched-ms: health Critical lands in MS_HEALTH_OVERRIDE (card code 4) only', MS_HEALTH_OVERRIDE[K4]===4&&
       JSON.stringify(diff(s0,snap()))==='["msHealth"]', JSON.stringify(diff(s0,snap())));
    s0=snap();
    await edit(K4,'shortTitle','Probe short');
    ck('sched-ms: a short title lands in MS_SHORT_TITLES only', MS_SHORT_TITLES[K4]==='Probe short'&&
       JSON.stringify(diff(s0,snap()))==='["shortTitles"]', JSON.stringify(diff(s0,snap())));
    s0=snap();
    ck('sched-ms: an unknown health code is refused', schedGridEdit(K4,'health',9)===false&&JSON.stringify(diff(s0,snap()))==='[]');
    ck('sched-ms: TASKS, MILESTONES and USER_MILESTONES deep-equal the snapshot', deepEq(base,schedSnap()));

    // ---- Schedule updates picks the new one up (counts at open) ----
    await pick('sched-upd');
    ck('sched-upd: now four annotated milestones, including the one just edited',
       rows()===4&&!!eng().dataView.getItemById(K4)&&/Comment/.test(eng().dataView.getItemById(K4).edits), rows());
    tb2=titleBtn(); tb2.click(); await wait(30);
    const lab=[...document.querySelectorAll('#grid-host [data-sg^="view-"].sg-menu-item')].map(i=>i.textContent.replace(/^✓/,'').trim());
    ck('the menu counts are read at open (Milestone comments (4), Schedule updates (4))',
       lab.includes('Milestone comments (4)')&&lab.includes('Schedule updates (4)')&&lab.includes('Milestone health overrides (2)')&&
       lab.includes('Custom short titles (1)'), JSON.stringify(lab));
    tb2.click(); await wait(20);

    // ---- All schedule activities: rows, their health and remark ----
    await pick('sched-all');
    const E2=eng(), g2=E2.grid, dv2=E2.dataView;
    const ref=dv2.getItems().map(r=>r.key).find(k=>{ const tr=document.querySelector('tr[data-type="row"][data-ref="'+k+'"]');
      return tr&&tr.querySelector('.remarks')&&!tr.querySelector('.remarks').textContent.trim()&&tr.querySelector('.health-dot[data-orig-health]'); });
    ck('sched-all: a row with a board remark cell to edit', !!ref, ref);
    const cols2=['id','name','band','start','finish','float','state','progress'];
    ck('sched-all: schedule columns read only, health and remark editable',
       cols2.every(c=>{ const i=g2.getColumns().findIndex(x=>x.id===c); return i>=0&&g2.getColumns()[i].editor==null; })&&
       ['health','comment'].every(c=>{ const i=g2.getColumns().findIndex(x=>x.id===c); return i>=0&&!!g2.getColumns()[i].editor; }));
    if(ref){
      const b2=schedSnap();
      s0=snap();
      const i=dv2.getIdxById(ref), ci=g2.getColumns().findIndex(x=>x.id==='comment');
      g2.setActiveCell(i,ci); g2.editActiveCell();
      const ed=host().querySelector('.sg-editor'); if(ed){ ed.value='Row remark from the schedule view'; g2.getEditorLock().commitCurrentEdit(); }
      await wait(40);
      const so=snapshotOverrides();
      ck('sched-all: the remark lands on the board row (row overrides) only',
         !!so[ref]&&so[ref].remarks==='Row remark from the schedule view'&&JSON.stringify(diff(s0,snap()))==='["rowOverrides"]', JSON.stringify(diff(s0,snap())));
      s0=snap();
      ck('sched-all: a finish date write is refused', schedGridEdit(ref,'finish','2030-01-01')===false&&JSON.stringify(diff(s0,snap()))==='[]');
      g2.setActiveCell(i,g2.getColumns().findIndex(x=>x.id==='name')); g2.editActiveCell();
      ck('sched-all: the name cell opens no editor', !host().querySelector('.sg-editor'));
      ck('sched-all: TASKS, MILESTONES and USER_MILESTONES deep-equal the snapshot', deepEq(b2,schedSnap()));
    }
    ck('the whole run left TASKS, MILESTONES and USER_MILESTONES as they were', deepEq(base,schedSnap()));

    // ---- keyboard ----
    let t=titleBtn();
    t.focus();
    t.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
    await wait(20);
    let pop2=document.querySelector('#grid-host [data-sg="view-menu"]');
    const first=document.activeElement;
    ck('keyboard: ArrowDown on the title opens the menu on its first item', !!pop2&&!pop2.hidden&&!!first&&first.getAttribute('data-sg')==='view-userms',
       first&&first.getAttribute('data-sg'));
    first.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
    await wait(10);
    ck('keyboard: ArrowDown moves to the next view', document.activeElement.getAttribute('data-sg')==='view-annot:comments', document.activeElement.getAttribute('data-sg'));
    document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
    await wait(10);
    ck('keyboard: Esc closes the menu and returns focus to the title', pop2.hidden&&document.activeElement===titleBtn());
    t=titleBtn();
    t.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true})); await wait(10);
    document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'End',bubbles:true,cancelable:true})); await wait(10);
    document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowUp',bubbles:true,cancelable:true})); await wait(10);
    const target=document.activeElement.getAttribute('data-sg');
    // Enter on a focused button is the browser's own activation: click().
    document.activeElement.click(); await wait(150);
    ck('keyboard: Enter on a view switches to it (End, ArrowUp: Schedule updates)',
       target==='view-sched-upd'&&/^Schedule updates \(/.test(titleText()), target+' '+titleText());
    ck('keyboard: focus lands on the new title', document.activeElement===titleBtn(), document.activeElement&&document.activeElement.getAttribute('data-sg'));

    // ---- Back after switching: the origin (User milestones) ----
    await pressBack();
    const a=document.activeElement;
    ck('Back after switching returns to User milestones and View items', !SRETGrid.isOpen()&&WS_SECTION==='userms'&&!!a&&a.id==='btn-userms-view',
       WS_SECTION+' '+(a&&a.id));
    // And from an annotation type.
    setWorkspaceSection('comments',true); await wait(40);
    $('btn-ye-view-comments').focus(); $('btn-ye-view-comments').click(); await wait(150);
    await pick('userms'); await pick('sched-all');
    await pressBack();
    const a2=document.activeElement;
    ck('Back after switching from Milestone comments returns to its View button', WS_SECTION==='comments'&&!!a2&&a2.id==='btn-ye-view-comments',
       WS_SECTION+' '+(a2&&a2.id));
    const net=performance.getEntriesByType('resource').map(e=>e.name).filter(u=>/^https?:/i.test(u));
    ck('the page made zero http(s) requests', net.length===0, net.join(', '));
  }
  let tb2=null;

  window.addEventListener('load',function(){ setTimeout(async function(){
    try{
      if(MODE==='mobile'||MODE==='tablet') await overlayMode();
      else if(MODE==='desktop') await desktopMode();
      else await switchMode();
    }catch(e){ ck('probe ran without throwing', false, e&&e.stack||e); }
    emit();
  },900); });
})();
"""


def render(html: str, size) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    out = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                          "--host-resolver-rules=MAP * ~NOTFOUND",
                          f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=60000",
                          "--dump-dom", "file://" + path],
                         capture_output=True, text=True, timeout=300).stdout
    m = OUT_RE.search(out)
    if not m:
        return {"checks": [{"name": "probe produced output", "pass": False, "detail": ""}]}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def source_checks(src: str) -> list:
    out = []

    def ck(name, ok, detail=""):
        out.append({"name": "[source] " + name, "pass": bool(ok), "detail": str(detail)})

    for t in ("</body>", "<head>", "</head>", "</html>"):
        ck(f"the page holds exactly one {t}", src.count(t) == 1, src.count(t))
    ck("version grep returns 1", len(re.findall(r"3\.[0-9]*\.[0-9]*-P", src)) == 1)
    m = re.search(r"const APP_VERSION='3\.1\.0-P(\d+)';", src)
    ck("APP_VERSION is 3.1.0-P63 or a later partial", bool(m) and int(m.group(1)) >= 63, m and m.group(0))
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", src, re.S)
    ck("no literal script start tag inside any script", not any(re.search(r"<script", s, re.I) for s in scripts))
    ck("no CDN URL in the file", not re.search(r"cdnjs|cdn\.sheetjs|jsdelivr|unpkg", src))
    a = src.find("// ---- P63 (TD-223): views from the grid title")
    b = src.find("function setGridTitle(", a)
    block = src[a:b] if a >= 0 and b > a else ""
    ck("the P63 views block is present", bool(block))
    strings = re.findall(r"'([^'\n]*)'", block)
    bad = [s for s in strings if "—" in s or "–" in s]
    ck("no em or en dash in the view labels and column names", not bad, bad)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks = source_checks(src)
    for mode, size in MODES.items():
        html = src.replace("</body>", "<script>\n" + PROBE.replace("__MODE__", json.dumps(mode)) + "\n</script>\n</body>")
        checks += render(html, size)["checks"]
    fails = 0
    for c in checks:
        ok = c["pass"]
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + c["name"] + ("" if ok else f"  ({c['detail']})"))
    print(f"\n{len(checks) - fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
