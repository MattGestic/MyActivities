#!/usr/bin/env python3
"""
P61 check: the grid view embedded, Workspace > User milestones > View items
(F-01), the Your edits row (E-01) and the renamed exports (E-03).

Runs the real app in headless Chromium with the host resolver pointed at
nothing, and reads DOM, classList, computed geometry and store contents,
never a screenshot. Three page loads, so each part starts from a clean app:

  grid   GRID EMBED  window.Slick and window.SRETGrid exist at load; no
                     <script src>; zero http(s) resource entries at the end
         F-01        three milestones added through the real Add milestone
                     path; View items opens the grid with three rows inside
                     #grid-host; the icon bar and report header stay
                     uncovered (elementFromPoint) and clickable; a name edit
                     lands in USER_MILESTONES; progress 150, -1 and 101 are
                     refused (cell reverts, store unchanged) while 0 and 100
                     are taken; a date either side of the week range is
                     refused, the first and last week are taken; the health
                     dot writes MS_HEALTH_OVERRIDE in its own codes; a comment
                     writes MS_COMMENTS; Add row takes its ID from
                     nextUserMsId(); Delete selected rows removes one;
                     double-click on an ID opens the milestone card above the
                     grid; Export .xlsx goes through ensureXLSX and writes the
                     sheet rows (XLSX.writeFile captured); Back returns focus
                     to View items and the rebuilt board shows the change
  edits  E-01        "No edits yet" on a fresh load; one comment, one health
                     override and one note give exactly those three categories
                     at 1 each, refreshed by the save itself; deleting the note
                     and Reset row marks bring counts down; a dependency
                     comment and a mounted annotation file both reach it
  export E-03        the three export labels are exact and carry no em dash;
                     the All remarks workbook (captured at XLSX.writeFile) has
                     only the four remark sheets and remark columns, and a
                     health-only row is not in it; the CSV has one row per
                     deliverable row on the board

Source assertions: the four tag counts are 1; the vendor blocks sit where
docs/grid-view-integration.md puts them and carry the files unchanged; the MIT
licence and version line precede the engine; no script start tag inside a
script; the version grep returns 1.

Usage:
  python3 tools/p61_check.py [--html FILE]
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
VENDOR = ROOT / "vendor" / "slickgrid"
MOD = ROOT / "src" / "modules" / "grid-view"
OUT_RE = re.compile(r'<pre id="p61-out">(.*?)</pre>', re.S)

PROBE = r"""
(function(){
  const MODE=__MODE__;
  try{ localStorage.clear(); }catch(e){}
  document.head.insertAdjacentHTML('beforeend','<style>*,*::before,*::after{transition:none!important;animation:none!important}</style>');
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:'['+MODE+'] '+n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p61-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const hitIn=(el,sel)=>{ const r=rc(el); const at=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
                          return !!at&&!!at.closest(sel); };
  const ye=()=>{ const o={}; document.querySelectorAll('#ws-your-edits .ye-item').forEach(function(s){ o[s.getAttribute('data-cat')]=+s.getAttribute('data-n'); }); return o; };
  // Capture what the app hands SheetJS instead of downloading it.
  const WRITES=[];
  function stubWrite(){ if(typeof XLSX!=='undefined') XLSX.writeFile=function(wb,name){ WRITES.push({wb:wb,name:name}); }; }
  function sheetRows(wb,name){ return XLSX.utils.sheet_to_json(wb.Sheets[name],{header:1,raw:false,defval:''}); }
  function addMs(name){
    openAddMilestone();
    $('add-ms-name').value=name;
    saveAddMilestone();
  }

  async function gridMode(){
    ck('window.Slick exists at load (the embedded engine)', typeof window.Slick==='object'&&typeof Slick.Grid==='function');
    ck('window.SRETGrid exists at load (the grid view module)', typeof window.SRETGrid==='object'&&typeof SRETGrid.open==='function');
    ck('no <script src> anywhere in the document', !document.querySelector('script[src]'));
    stubWrite();

    // ---- F-01: three milestones through the real Add milestone path ----
    const expect=[nextUserMsId()];
    addMs('Probe one'); expect.push(nextUserMsId());
    addMs('Probe two'); expect.push(nextUserMsId());
    addMs('Probe three');
    await wait(150);
    const ids=USER_MILESTONES.map(m=>m.id);
    ck('three milestones added through saveAddMilestone, IDs from nextUserMsId()',
       ids.length===3&&JSON.stringify(ids)===JSON.stringify(expect), ids.join(','));
    setWorkspaceSection('userms',true);
    await wait(50);
    const btn=$('btn-userms-view');
    ck('User milestones shows an enabled View items button', !!btn&&!btn.disabled&&btn.textContent.trim()==='View items',
       btn&&btn.outerHTML.slice(0,120));
    ck('the disabled Manage… placeholder is gone',
       !/Manage…|Grid arrives in D-17c/.test(($('ws-userms-body')||{}).innerHTML||''));
    if(!btn||typeof SRETGrid==='undefined') return;
    btn.focus(); btn.click();
    await wait(120);
    const host=$('grid-host'), E=SRETGrid._engine();
    ck('View items opens the grid', SRETGrid.isOpen()&&!!E);
    if(!E) return;
    const g=E.grid, dv=E.dataView;
    ck('the grid holds the three milestones', dv.getLength()===3, dv.getLength());
    const scr=document.querySelector('.sg-screen');
    ck('the grid screen lives in #grid-host, shown, with body.grid-open',
       !!scr&&host.contains(scr)&&!host.hidden&&document.body.classList.contains('grid-open'));
    const ib=$('icon-bar'), hd=document.querySelector('.rpt-hd');
    ck('#icon-bar is not covered (elementFromPoint lands in it)', hitIn(ib,'#icon-bar'));
    const shown=[...ib.querySelectorAll('button[id]')].filter(b=>rc(b).width>0&&rc(b).height>0);
    ck('every visible icon bar button is the element at its own centre (clickable)',
       shown.length>0&&shown.every(b=>hitIn(b,'#'+b.id)), shown.map(b=>b.id+':'+hitIn(b,'#'+b.id)).join(' '));
    ck('the report header is not covered either', hitIn(hd,'.rpt-hd'));
    const sr=rc(scr);
    ck('the grid starts below the header', sr.top>=rc(hd).bottom-0.5&&sr.top>=rc(ib).bottom-0.5, sr.top+' vs '+rc(hd).bottom);
    ck('the grid fits the viewport (no page scroll under it)', sr.bottom<=innerHeight+0.5&&sr.height>200, sr.top+'+'+sr.height+' / '+innerHeight);
    ck('the board and filter bar are hidden behind it',
       getComputedStyle($('scroll-wrap')).display==='none'&&getComputedStyle($('top-filter-bar')).display==='none');
    ck('the grid screen paints an opaque background',
       getComputedStyle(scr).backgroundColor!=='rgba(0, 0, 0, 0)');

    const colIdx=k=>g.getColumns().findIndex(c=>c.id===k);
    async function edit(id,key,val){
      g.setActiveCell(dv.getIdxById(id),colIdx(key)); g.editActiveCell();
      const ed=host.querySelector('.sg-editor');
      if(!ed) return {err:'no editor'};
      ed.value=String(val); g.getEditorLock().commitCurrentEdit();
      await wait(20);
      return dv.getItemById(id)[key];
    }
    const [A,B,C]=ids, rec=id=>USER_MILESTONES.find(m=>m.id===id);

    // name
    const nm=await edit(A,'name','Renamed in grid');
    ck('a name edit lands in USER_MILESTONES (and its [ID] - Name notes)',
       rec(A).actName==='Renamed in grid'&&rec(A).notes==='['+A+'] - Renamed in grid'&&nm==='Renamed in grid',
       JSON.stringify([rec(A).actName,rec(A).notes,nm]));
    // P62 (E-02): user milestones are no longer a Your edits row (they have
    // their own section and grid), so the signal is read from MARKUP_COUNT.
    ck('the edit signalled noteMarkup', !('userMs' in ye())&&MARKUP_COUNT>=4, JSON.stringify(ye())+' '+MARKUP_COUNT);

    // progress: both bounds, just inside and just outside
    const p0=rec(B).progress, cnt0=MARKUP_COUNT;
    const v150=await edit(B,'progress',150);
    ck('progress 150 is refused: the cell reverts', v150===p0, v150);
    ck('progress 150 is refused: the store is unchanged',
       rec(B).progress===p0&&!(B in MS_PROGRESS_OVERRIDE)&&MARKUP_COUNT===cnt0, rec(B).progress+' '+MARKUP_COUNT);
    const v101=await edit(B,'progress',101), vm1=await edit(B,'progress',-1);
    ck('progress 101 and -1 are refused too', v101===p0&&vm1===p0&&rec(B).progress===p0, v101+' '+vm1);
    const v100=await edit(B,'progress',100);
    ck('progress 100 is taken', v100===100&&rec(B).progress===100, v100);
    const v0=await edit(B,'progress',0);
    ck('progress 0 is taken', v0===0&&rec(B).progress===0, v0);

    // dates: either side of the week range
    const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
    const first=WE_DATES[0], last=WE_DATES[WE_DATES.length-1];
    const d0=rec(C).date;
    const before=iso(new Date(first.getFullYear(),first.getMonth(),first.getDate()-30));
    const after=iso(new Date(last.getFullYear(),last.getMonth(),last.getDate()+30));
    const vb=await edit(C,'finish',before), va=await edit(C,'finish',after);
    ck('a date before the first week is refused', vb===d0&&rec(C).date===d0, vb);
    ck('a date after the last week is refused', va===d0&&rec(C).date===d0, va);
    const vf=await edit(C,'finish',iso(first));
    ck('the first week ending is taken', vf===iso(first)&&rec(C).date===iso(first), vf);
    const vl=await edit(C,'finish',iso(last));
    ck('the last week ending is taken', vl===iso(last)&&rec(C).date===iso(last), vl);

    // comment and the health dot
    await edit(A,'comment','Grid comment');
    ck('a comment edit writes MS_COMMENTS', MS_COMMENTS[A]==='Grid comment', MS_COMMENTS[A]);
    g.scrollRowIntoView(dv.getIdxById(A)); g.setActiveCell(dv.getIdxById(A),colIdx('id')); g.render();
    const dot=host.querySelector('.slick-cell.active .sg-hdot');
    if(dot){ dot.click(); await wait(30); }
    const pick=host.querySelector('[data-sg-health="3"]');
    if(pick){ pick.click(); await wait(30); }
    const dotId=dot?A:null;
    ck('the health dot picks Critical, stored as the milestone code (CRIT = 4)',
       !!dotId&&MS_HEALTH_OVERRIDE[dotId]===4&&effectiveState(rec(dotId))==='CRIT', dotId+' '+JSON.stringify(MS_HEALTH_OVERRIDE));

    // Add row
    const nextId=nextUserMsId();
    host.querySelector('[data-sg="add"]').click();
    await wait(40);
    if(g.getEditorLock().isActive()) g.getEditorLock().cancelCurrentEdit();
    ck('Add row adds a row whose ID comes from nextUserMsId()',
       dv.getLength()===4&&!!dv.getItemById(nextId)&&!!rec(nextId), nextId+' '+dv.getLength());
    ck('the new row is a real user milestone (the add dialog\'s writer)',
       !!rec(nextId)&&rec(nextId).source===USER_BAND_SOURCE&&rec(nextId).notes==='['+nextId+'] - New milestone'&&dateToCol(rec(nextId).date)>=0);

    // Delete selected rows (B)
    g.setSelectedRows([dv.getIdxById(B)]); await wait(20);
    host.querySelector('[data-sg="tools"]').click(); await wait(20);
    const del=document.querySelector('[data-sg="delete"]');
    if(del) del.click();
    await wait(20);
    const go=host.querySelector('[data-sg="confirm-remove"]');
    if(go) go.click();
    await wait(40);
    ck('Delete selected rows removes that milestone from the grid and the store',
       !rec(B)&&!dv.getItemById(B)&&dv.getLength()===3&&USER_MILESTONES.length===3,
       USER_MILESTONES.map(m=>m.id).join(','));
    ck('and the row it created for itself', !USER_ROWS.some(r=>r.ref===B));

    // Double-click on the ID opens the milestone card
    g.scrollRowIntoView(dv.getIdxById(A)); g.render();
    g.setActiveCell(dv.getIdxById(A),colIdx('id'));
    const idCell=host.querySelector('.slick-cell.active');
    if(idCell) idCell.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true,view:window}));
    await wait(60);
    const dlg=$('ms-dialog');
    ck('double-click on the ID opens the milestone card for it',
       !!dlg&&!dlg.hidden&&msDialogFor===A&&$('ms-title').value==='Renamed in grid', msDialogFor+' '+($('ms-title')||{}).value);
    ck('the card is above the grid (elementFromPoint lands in it)', !!dlg&&!dlg.hidden&&hitIn(dlg,'#ms-dialog'));
    if(dlg&&!dlg.hidden) discardMsDialog();

    // Export .xlsx through ensureXLSX
    WRITES.length=0;
    host.querySelector('[data-sg="add-more"]').click(); await wait(20);
    const ex=document.querySelector('[data-sg="export"]');
    if(ex) ex.click();
    await wait(200);
    const w=WRITES[0];
    ck('Export .xlsx writes one workbook through XLSX.writeFile', WRITES.length===1&&/^User milestones .*\.xlsx$/.test(w&&w.name), w&&w.name);
    if(w){
      const rows=sheetRows(w.wb,w.wb.SheetNames[0]);
      const head=rows[0]||[];
      ck('its header is the grid\'s columns, Health last',
         JSON.stringify(head)===JSON.stringify(['Activity ID','Name','Type','Date','Band','Status','% complete','Comment','Health']), JSON.stringify(head));
      const byId={}; rows.slice(1).forEach(r=>{ byId[r[0]]=r; });
      ck('one sheet row per user milestone, deleted one absent',
         rows.length===4&&byId[A]&&byId[C]&&byId[nextId]&&!byId[B], rows.map(r=>r[0]).join(','));
      ck('the sheet carries the edited name, comment and health',
         byId[A]&&byId[A][1]==='Renamed in grid'&&byId[A][7]==='Grid comment'&&(dotId!==A||byId[A][8]==='Critical'), JSON.stringify(byId[A]));
    }

    // Back
    host.querySelector('[data-sg="back"]').click();
    await wait(250);
    ck('Back closes the grid and gives the board back',
       !SRETGrid.isOpen()&&host.hidden&&!document.body.classList.contains('grid-open')&&getComputedStyle($('scroll-wrap')).display!=='none');
    ck('Back returns focus to View items (after the rebuild)', document.activeElement&&document.activeElement.id==='btn-userms-view',
       document.activeElement&&(document.activeElement.id||document.activeElement.tagName));
    const trA=document.querySelector('tr[data-type="row"][data-ref="'+A+'"]');
    ck('the rebuilt board shows the renamed milestone\'s row', !!trA&&/Renamed in grid/.test(trA.textContent), trA&&trA.textContent.slice(0,80));
    ck('the deleted milestone\'s row is gone and the added one is on the board',
       !document.querySelector('tr[data-type="row"][data-ref="'+B+'"]')&&!!document.querySelector('tr[data-type="row"][data-ref="'+nextId+'"]'));
    ck('the board milestones follow the store',
       !!findMilestoneBySnip(A)&&findMilestoneBySnip(A).actName==='Renamed in grid'&&!findMilestoneBySnip(B)&&!!findMilestoneBySnip(nextId));
    ck('the User milestones count follows (3)', ($('ws-userms-count')||{}).textContent==='3', ($('ws-userms-count')||{}).textContent);

    const net=performance.getEntriesByType('resource').map(e=>e.name).filter(u=>/^https?:/i.test(u));
    ck('the page made zero http(s) requests', net.length===0, net.join(', '));
  }

  async function editsMode(){
    const row=$('ws-your-edits');
    ck('Comments & markups has a Your edits row, first in its group',
       !!row&&row.closest('.sd-group')&&row.closest('.sd-group').querySelector('.sd-row')===row&&/Your edits/.test(row.textContent));
    ck('a fresh load says "No edits yet"', !!row&&/No edits yet/.test(row.textContent)&&!row.querySelector('.ye-item'), row&&row.textContent);

    // One comment and one health override, through the milestone card.
    const wrap=document.querySelector('#tbody .m-wrap');
    wrap.click(); await wait(60);
    const key=msDialogFor;
    $('ms-comment-text').value='A probe comment'; onMsCommentInput();
    onMsHealthClick(document.querySelector('#ms-dialog .health-dot[data-val="3"]'));
    saveMsDialog(true);
    // One note through the composer.
    $('note-input').value='A probe note'; saveNewNote();
    const c1=ye();
    ck('after one comment, one health override and one note: exactly those three, 1 each',
       JSON.stringify(c1)===JSON.stringify({comments:1,notes:1,msHealth:1}), JSON.stringify(c1));
    const labels=[...document.querySelectorAll('#ws-your-edits .ye-item')].map(s=>s.textContent);
    ck('each under its ANNOT_CATEGORIES label',
       JSON.stringify(labels)===JSON.stringify(['Milestone comments: 1','Notes: 1','Milestone health overrides: 1']), JSON.stringify(labels));
    ck('refreshed by the save itself, before any rebuild', !!key&&MS_COMMENTS[key]==='A probe comment');

    // Row health and remarks, then Reset row marks.
    const dot=document.querySelector('tr[data-type="row"] .health-dot[data-orig-health]');
    const orig=+dot.getAttribute('data-orig-health');
    setHealth(dot,orig===3?1:3);
    ck('a row health change counts under Row health and remarks', ye().rowOverrides===1, JSON.stringify(ye()));
    setWorkspaceSection('comments',true); await wait(30);
    $('btn-reset-row-marks').click(); await wait(20);
    const rs=[...document.querySelectorAll('#ws-reset-row .sd-btn-danger')].find(b=>b.textContent.trim()==='Reset');
    if(rs) rs.click();
    await wait(20);
    ck('Reset row marks takes it back off', !('rowOverrides' in ye())&&ye().comments===1, JSON.stringify(ye()));

    // Delete the note.
    deleteNote(NOTES[0].nid);
    ck('deleting the note drops Notes', JSON.stringify(ye())===JSON.stringify({comments:1,msHealth:1}), JSON.stringify(ye()));

    // A dependency comment (the one writer that did not signal before P61).
    activeCommentKeys=['pred:SNIP-101->SNIP-103'];
    $('dep-comment-text').value='Lag looks short';
    saveCommentPanel();
    ck('a dependency comment counts at once', ye().depComments===1, JSON.stringify(ye()));

    // A mounted annotation file (the mount entry point).
    const payload={kind:MODEL_KIND,schemaVersion:MODEL_SCHEMA_VERSION,version:APP_VERSION,
      milestoneComments:{'SNIP-115':'From the mounted file'},milestoneShortTitles:{'SNIP-115':'Mounted title'}};
    const inp=$('annot-file');
    const dt=new DataTransfer(); dt.items.add(new File([JSON.stringify(payload)],'probe-annotations.json',{type:'application/json'}));
    inp.files=dt.files; handleAnnotFile(inp);
    for(let i=0;i<40&&$('annot-dialog').hidden;i++) await wait(50);
    ck('the mount dialog opens for the file', !$('annot-dialog').hidden, (($('annot-dialog-body')||{}).textContent||'').slice(0,200));
    const ap=$('annot-apply'); if(ap) ap.click();
    await wait(200);
    const c2=ye();
    ck('a mounted file reaches the counts (comments 2, short titles 1)', c2.comments===2&&c2.shortTitles===1,
       JSON.stringify(c2)+' mount='+JSON.stringify(ANNOT_MOUNT&&ANNOT_MOUNT.applied));
  }

  async function exportMode(){
    const sec=$('ws-sec-comments');
    const labels=[...sec.querySelectorAll('.sd-row-label')].map(e=>e.textContent.trim());
    ck('the export labels are exact',
       labels.indexOf('All remarks (.xlsx)')>=0&&labels.indexOf('Milestones incl. annotations (.csv)')>=0&&labels.indexOf('Backup to re-import (.json)')>=0,
       JSON.stringify(labels));
    const exportRowsTxt=[...sec.querySelectorAll('.sd-group')].find(g=>/Exports/.test(g.textContent));
    const strings=exportRowsTxt?[exportRowsTxt.textContent].concat([...exportRowsTxt.querySelectorAll('[title]')].map(e=>e.title)):[];
    ck('no em or en dash in the export rows, labels or tooltips', strings.length>1&&!strings.some(s=>/[—–]/.test(s)));
    ck('the old names are gone', !/Comments report|Status report|Model and annotations/.test(sec.textContent));

    stubWrite();
    // A milestone comment through the card, a row remark, a health-only row,
    // a dependency comment and a note.
    const wrap=document.querySelector('#tbody .m-wrap'); wrap.click(); await wait(60);
    const key=msDialogFor;
    $('ms-comment-text').value='Remark on a milestone'; onMsCommentInput(); saveMsDialog(true);
    const rows=[...document.querySelectorAll('tr[data-type="row"]')];
    const rRem=rows.find(tr=>tr.querySelector('.remarks')&&!tr.querySelector('.remarks').textContent.trim());
    const rHealth=rows.find(tr=>tr!==rRem&&tr.querySelector('.remarks')&&!tr.querySelector('.remarks').textContent.trim()&&tr.querySelector('.health-dot[data-orig-health]'));
    rRem.querySelector('.remarks').textContent='Row remark text';
    const hd=rHealth.querySelector('.health-dot'); setHealth(hd,+hd.getAttribute('data-orig-health')===3?1:3);
    activeCommentKeys=['succ:SNIP-101->SNIP-103']; $('dep-comment-text').value='Dependency remark'; saveCommentPanel();
    $('note-input').value='Note remark'; saveNewNote();
    $('btn-export-comments').click();
    await wait(200);
    const w=WRITES[0];
    ck('All remarks writes one workbook', WRITES.length===1&&!!w, WRITES.length);
    if(w){
      ck('its sheets are the four remark sheets, nothing else',
         JSON.stringify(w.wb.SheetNames)===JSON.stringify(['Milestone Comments','Dependency Comments','Row Remarks','Notes']), JSON.stringify(w.wb.SheetNames));
      const mc=sheetRows(w.wb,'Milestone Comments'), dc=sheetRows(w.wb,'Dependency Comments'),
            rr=sheetRows(w.wb,'Row Remarks'), nt=sheetRows(w.wb,'Notes');
      ck('Milestone Comments columns: identity and the comment only',
         JSON.stringify(mc[0])===JSON.stringify(['Activity ID','Source Schedule','Title','Comment']), JSON.stringify(mc[0]));
      ck('Dependency Comments columns: identity and the comment only',
         JSON.stringify(dc[0])===JSON.stringify(['Origin ID','Connector','Comment']), JSON.stringify(dc[0]));
      ck('Row Remarks columns: identity and the remark only (no health)',
         JSON.stringify(rr[0])===JSON.stringify(['Ref','Title','Remark']), JSON.stringify(rr[0]));
      ck('Notes keeps its note record columns', nt[0]&&nt[0][0]==='Note'&&nt[0][7]==='Note text', JSON.stringify(nt[0]));
      ck('no Health, Progress or Status column outside the Notes sheet',
         ![mc[0],dc[0],rr[0]].some(h=>h.some(c=>/health|progress|status|date/i.test(c))));
      ck('the milestone comment is there', mc.length===2&&mc[1][0]===key&&mc[1][3]==='Remark on a milestone', JSON.stringify(mc[1]));
      ck('the dependency comment is there', dc.length===2&&dc[1][2]==='Dependency remark', JSON.stringify(dc[1]));
      const rrRefs=rr.slice(1).map(r=>r[0]);
      ck('the row remark is there, and the health-only row is not',
         rrRefs.indexOf(rRem.getAttribute('data-ref'))>=0&&rrRefs.indexOf(rHealth.getAttribute('data-ref'))<0, JSON.stringify(rrRefs.slice(0,8)));
      ck('every Row Remarks row carries remark text', rr.slice(1).every(r=>String(r[2]).trim()!==''));
      ck('the note is there', nt.length===2&&nt[1][7]==='Note remark', JSON.stringify(nt[1]));
    }

    // CSV: capture the blob instead of downloading.
    let blob=null; const orig=URL.createObjectURL;
    URL.createObjectURL=function(b){ blob=b; return 'blob:probe'; };
    const clk=HTMLAnchorElement.prototype.click; HTMLAnchorElement.prototype.click=function(){};
    $('btn-export-csv').click();
    URL.createObjectURL=orig; HTMLAnchorElement.prototype.click=clk;
    const text=blob?await blob.text():'';
    const lines=text.replace(/^﻿/,'').split('\r\n').filter(l=>l!=='');
    const board=[...document.querySelectorAll('tr[data-type="row"]')].map(tr=>tr.getAttribute('data-ref'));
    const csv=buildCsvRows();
    ck('the CSV has one row per deliverable row on the board', lines.length-1===board.length&&csv.length-1===board.length,
       (lines.length-1)+' vs '+board.length);
    const refCol=csv[0].indexOf('Ref');
    ck('in board order, each deliverable once', JSON.stringify(csv.slice(1).map(r=>r[refCol]))===JSON.stringify(board));
    ck('and it carries the annotations (the milestone comment, the row remark)',
       text.indexOf('Remark on a milestone')>=0&&text.indexOf('Row remark text')>=0);
  }

  window.addEventListener('load',function(){ setTimeout(async function(){
    try{
      if(MODE==='grid') await gridMode();
      else if(MODE==='edits') await editsMode();
      else await exportMode();
    }catch(e){ ck('probe ran without throwing', false, e&&e.stack||e); }
    emit();
  },900); });
})();
"""


def render(html: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    out = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                          "--host-resolver-rules=MAP * ~NOTFOUND",
                          "--window-size=1440,900", "--virtual-time-budget=40000",
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
    # P62 moved the version on; P61's own features are what this check proves.
    m = re.search(r"const APP_VERSION='3\.1\.0-P(\d+)';", src)
    ck("APP_VERSION is 3.1.0-P61 or a later partial", bool(m) and int(m.group(1)) >= 61, m and m.group(0))

    vjs = (VENDOR / "slickgrid.subset.min.js").read_text(encoding="utf-8").rstrip("\n")
    vcss = (VENDOR / "dist" / "slick.grid.css").read_text(encoding="utf-8").rstrip("\n")
    # P70 (TD-229): the module is a core plus features; the app pastes the core and
    # the features it uses (tools/grid_view_embed.py APP_FEATURES), each unchanged.
    import grid_view_embed as GE
    gcss_parts = GE.parts("css")
    gjs_parts = GE.parts("js")
    lic = (VENDOR / "LICENSE").read_text(encoding="utf-8")
    ck("the vendor JS holds no </script and the vendor CSS no </style",
       "</script" not in vjs.lower() and "</style" not in vcss.lower())

    blocks = re.findall(r'<script id="vendor-slickgrid">(.*?)</script>', src, re.S)
    ck("exactly one vendor-slickgrid script block", len(blocks) == 1, len(blocks))
    if blocks:
        body = blocks[0]
        ck("it carries slickgrid.subset.min.js unchanged", vjs in body)
        head = body.split(vjs[:40])[0]
        ck("the full MIT licence text precedes the engine",
           all(line.strip() in head for line in lic.splitlines() if line.strip()) and "MIT" in head)
        ck("with the version line", "SlickGrid 5.20.2" in head)
    ck("vendor-slickgrid sits immediately before the app script",
       re.search(r'</script>\s*<script id="app-script">', src) is not None
       and src.find('<script id="vendor-slickgrid">') < src.find('<script id="app-script">'))
    css_blocks = re.findall(r'<style id="vendor-slickgrid-css">(.*?)</style>', src, re.S)
    ck("one vendor-slickgrid-css block, carrying slick.grid.css unchanged",
       len(css_blocks) == 1 and vcss in css_blocks[0])
    first_close = src.find("</style>")
    ck("it follows the main </style> directly",
       src[first_close + len("</style>"):].lstrip().startswith('<style id="vendor-slickgrid-css">'))
    main_style = src[:first_close]
    ck("grid-view.css and its features are inside the main <style>, unchanged, in order",
       all(t in main_style for _, t in gcss_parts) and
       [main_style.find(t) for _, t in gcss_parts] == sorted(main_style.find(t) for _, t in gcss_parts),
       [n for n, t in gcss_parts if t not in main_style])
    app = src[src.find('<script id="app-script">'):]
    app = app[:app.find("</script>")]
    ck("grid-view.js and its features are at the top of the app script, unchanged, in order",
       all(t in app and app.find(t) < app.find("const APP_VERSION") for _, t in gjs_parts) and
       [app.find(t) for _, t in gjs_parts] == sorted(app.find(t) for _, t in gjs_parts),
       [n for n, t in gjs_parts if t not in app])
    m_set = re.search(r"SRETGrid\.setup\(\{\s*features:\[([^\]]*)\]", app)
    ck("the app's setup() enables exactly the pasted features (grid_view_embed APP_FEATURES)",
       bool(m_set) and re.findall(r"'([^']+)'", m_set.group(1)) == GE.APP_FEATURES, m_set and m_set.group(1))
    ck("collections, ms-import, dates and user modules are not embedded",
       not re.search(r"root\.SRETCollections\s*=|SRETMsImport\s*=|SRETDates\s*=|SRETUser\s*=", src))
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", src, re.S)
    ck("no literal script start tag inside any script", not any(re.search(r"<script", s, re.I) for s in scripts))
    ck("no CDN URL in the file", not re.search(r"cdnjs|cdn\.sheetjs|jsdelivr|unpkg", src))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks = source_checks(src)
    for mode in ("grid", "edits", "export"):
        html = src.replace("</body>", "<script>\n" + PROBE.replace("__MODE__", json.dumps(mode)) + "\n</script>\n</body>")
        checks += render(html)["checks"]
    fails = 0
    for c in checks:
        ok = c["pass"]
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + c["name"] + ("" if ok else f"  ({c['detail']})"))
    print(f"\n{len(checks) - fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
