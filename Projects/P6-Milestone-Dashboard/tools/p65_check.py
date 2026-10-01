#!/usr/bin/env python3
"""
P65 check: ENTRIES is the one record, and the stores are projections of it.

WHAT P65 CHANGED. Every milestone update (card save, grid edit, remark, note)
is an entry in ENTRIES (SRETEntries). MS_COMMENTS, MS_HEALTH_OVERRIDE,
MS_PROGRESS_OVERRIDE, MS_FIELD_OVERRIDE and NOTES are rebuilt from it by
projectEntryStores(). Nothing here reimplements a writer: every edit goes
through the app's own functions (openMsDialog + saveMsDialog, annotWrite,
userMsGridEdit, saveNewNote, ...), and every mount goes through the app's own
handleAnnotFile / annotSelectAll / applyAnnotSelection. The network is
unresolvable for every run and probes are injected with replace("</body>", ...).

Numbered as the brief numbers them (each probe check is prefixed A<n>):

  A1  Card entries and latest-wins. Three finish-date saves on one milestone:
      at T, at T+11 min (past the 10 minute window), and in the NEXT report
      period (reportDate + 7 days, inside the window). That is 3 entries, the
      override is the 3rd value, and the marker moved column on the board
      (measured on the .m-wrap's own cell). Then the latest entry is removed
      through SRETEntries.remove, re-projected and repainted: the date falls
      back to the 2nd, then the 1st, then there is no override and the marker
      is back in its schedule column. The purpose is to prove the stores really
      are derived, in both directions, rather than written once.
  A2  Coalescing, both sides of the boundary. A card save at updatedAt+599999 ms
      merges (count unchanged, `to` is the new value, `from` is still the
      original); at +600001 it appends. The inclusive edge (+600000 exactly) is
      asserted too, since the contract says 0 <= dt <= window.
  A3  Remark, and no spurious clear. A card remark makes an entry with that
      text and MS_COMMENTS[key] equals it. P66: the card's box is a NEW remark
      and opens empty, so reopening and saving with it empty makes NO entry
      (no clearText) and the stored remark stays; a later remark shows again.
      Clearing a remark is still covered, through the grid, in A6.
  A4  Health 0 vs automatic. The N/A dot (0) projects MS_HEALTH_OVERRIDE[key]
      === 0 (a present key, not an absent one); clicking the selected dot again
      is the card's "automatic" (-1), and removes the key. Also the case where
      both clicks coalesce into one save window and cancel out (no key, no entry
      left behind).
  A5  Progress equal to the schedule. Entering the schedule's own progress leaves
      no MS_PROGRESS_OVERRIDE key; a different figure sets it; entering the
      schedule's figure again clears it.
  A6  Grid edits. annotWrite msHealth / comments give origin 'grid' entries and
      set the stores; blank clears each. A user milestone added through
      userMsGridAdd() and edited through userMsGridEdit(id,'health',n) puts the
      translated value under its USR- key (USR keys project like any other).
  A7  Notes. saveNewNote (N=3) makes general entries with an nid, setNoteStatus
      changes the entry's status, deleteNote removes the entry; NOTES mirrors
      every step.
  A8  Drift detector. After ALL of the above (the app's own writers only)
      ENTRY_DRIFT_ADOPTED is 0 and each store is byte-identical before and
      after a fresh projectEntryStores(). Then a deliberate direct store write
      IS adopted: the counter goes up, the value survives, and an entry with
      origin 'direct' exists.
  A9  Publish round trip. The real publishDashboard() output carries `entries`
      AND the legacy store fields; loaded back as a reader would, ENTRIES.length
      is equal and every store deep-equals the pre-publish store.
  A10 Mounting a real P64 model file (tools/fixtures/p65/model_p64.json) into a
      CLEAN app through handleAnnotFile -> annotSelectAll -> applyAnnotSelection.
      The four milestone stores and NOTES equal what the file carries; mounting
      the same file again adds no entries.
  A11 Same board as P64. The P64 release and the current app each mount that
      fixture, rebuild, and give one signature per .m-wrap[data-ms] (marker
      classes, edit mark and its title, edit ghost in the row, column cell).
      The two must be identical: the "board looks the same after migration"
      proof. The check also asserts the sample carries edited markers, so an
      empty comparison cannot pass.
  A12 Mounting a v2 file. Three entries are made in the new build, exportModel()
      is captured, and mounting it into a clean new-build app gives exactly 3
      entries and the same stores; mounting again is still 3.

Deviations from the brief are listed where they occur (search "NOTE:").

Usage:
  python3 tools/p65_check.py [--html FILE] [--p64 FILE]
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

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p65chk-out">(.*?)</pre>', re.S)
FIXTURE = HERE / "fixtures" / "p65" / "model_p64.json"

# --------------------------------------------------------------------------
# Shared probe prelude: helpers every stage uses.
# --------------------------------------------------------------------------
PRELUDE = r"""
const R={checks:[],notes:{},err:null};
function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
const $=function(id){ return document.getElementById(id); };
const sleep=function(ms){ return new Promise(function(r){ setTimeout(r,ms); }); };
async function settle(){
  for(let i=0;i<60&&_rerenderPending;i++) await sleep(20);
  await sleep(60);
  for(let i=0;i<60&&_rerenderPending;i++) await sleep(20);
  await sleep(30);
}
function finish(){
  const o=document.createElement('pre'); o.id='p65chk-out';
  o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
  document.body.appendChild(o);
}
const CAP={}; let capName=null;
URL.createObjectURL=function(b){ CAP[capName]=b; return 'blob:captured'; };
HTMLAnchorElement.prototype.click=function(){};
window.confirm=function(){ return true; };
// A controllable clock. entryCtx() reads Date.now(), so this is the only
// stub: FAKE=null is the real clock.
const realNow=Date.now.bind(Date);
let FAKE=null;
Date.now=function(){ return FAKE!==null?FAKE:realNow(); };
const J=function(x){ return JSON.stringify(x); };
function storesNow(){
  return JSON.parse(J({comments:MS_COMMENTS,health:MS_HEALTH_OVERRIDE,
    progress:MS_PROGRESS_OVERRIDE,fields:MS_FIELD_OVERRIDE,notes:NOTES}));
}
function fixtureData(){ return JSON.parse($('p65-data').textContent); }
// Milestones that are on the board as a real marker, with an id, not a user
// milestone, not actualised: safe to edit through the card.
const wrapOf=function(id){ return document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]:not(.m-ghost)'); };
function candidates(){
  return MILESTONES.filter(function(m){
    const id=msId(m);
    return id&&!/^USR-/.test(id)&&m.date&&!m.actual&&wrapOf(id);
  });
}
function addDays(iso,n){ const d=new Date(iso+'T00:00:00'); d.setDate(d.getDate()+n); return isoDay(d); }
function setVal(id,v){
  const e=$(id); if(!e) throw new Error('no #'+id);
  e.value=v; e.dispatchEvent(new Event('input',{bubbles:true}));
}
function healthDot(v){ return document.querySelector('#ms-health-dots .health-dot[data-val="'+v+'"]'); }
function msOf(key){ return MILESTONES.filter(function(x){ return msKeyFor(x)===key; })[0]; }
// The real card: open on the CURRENT board copy, edit the form, save.
async function card(key,edit,close){
  if(!$('ms-dialog').hidden) closeMsDialog();
  const m=msOf(key); if(!m) throw new Error('no milestone for '+key);
  const id=msId(m);
  const task=TASKS.filter(function(t){ return t.ref===m.ref; })[0]||{name:'',disc:'',ref:m.ref,hrs:'',type:'Weighted'};
  openMsDialog(m,id,document.body,computeHours(task),task);
  edit();
  saveMsDialog(close);
  await settle();
}
function msEntries(key){ return ENTRIES.filter(function(e){ return e.target.kind==='ms'&&e.target.key===key; }); }
function colOf(id){
  const w=wrapOf(id); if(!w) return null;
  const td=w.closest('td');
  return td?{dataCol:td.getAttribute('data-col'),cell:td.cellIndex}:null;
}
// Mount a model file the way a user does: the file input's handler reads it,
// the dialog is shown, every category is ticked, Apply is pressed.
async function mountFile(text,name){
  ANNOT_PENDING=null;
  handleAnnotFile({files:[new File([text],name,{type:'application/json'})]});
  // A FileReader completes on real I/O, which virtual time does not wait for:
  // yield to the task queue without timers, and only then fall back to sleeps.
  const yieldTask=function(){ return new Promise(function(r){ const c=new MessageChannel(); c.port1.onmessage=function(){ r(); }; c.port2.postMessage(0); }); };
  for(let i=0;i<20000&&!ANNOT_PENDING;i++){ await yieldTask(); if(i%200===199) await sleep(5); }
  if(!ANNOT_PENDING) throw new Error('handleAnnotFile never staged the file');
  annotSelectAll();
  applyAnnotSelection();
  await settle();
}
"""

# --------------------------------------------------------------------------
# Stage 1: A1..A9 (capture publish + model at the end).
# --------------------------------------------------------------------------
STAGE1 = r"""
(async function(){
  try{
    await sleep(600); await settle();
    const T0=realNow();
    const cand=candidates();
    R.notes.candidates=cand.length;
    ck('sample: the board has at least 8 editable milestones on it', cand.length>=8, cand.length);
    // A needs three consecutive weeks to the right that are still on the board.
    const A=cand.filter(function(m){
      return [7,14,21].every(function(n){ return dateToCol(addDays(m.date,n))>=0; })&&
             dateToCol(addDays(m.date,7))!==dateToCol(m.date); })[0];
    const rest=cand.filter(function(m){ return m!==A; });
    const B=rest[0], C=rest[1], D=rest[2], E=rest[3], F=rest[4], G=rest[5], K=rest[6];
    const kA=msKeyFor(A), kB=msKeyFor(B), kC=msKeyFor(C), kD=msKeyFor(D), kE=msKeyFor(E),
          kF=msKeyFor(F), kG=msKeyFor(G), kK=msKeyFor(K);
    R.keys=[kA,kB,kC,kD,kE,kF,kG,kK];
    const origPeriod=reportPeriodISO();
    const origReport=new Date(REPORT_META.reportDate.getTime());

    // ============================ A1 ============================
    const a0=A.date, colA0=colOf(msId(A));
    const v1=addDays(a0,7), v2=addDays(a0,14), v3=addDays(a0,21);
    FAKE=T0;
    await card(kA,function(){ setVal('ms-date',v1); },true);
    const c1=colOf(kA);
    FAKE=T0+11*60000;
    await card(kA,function(){ setVal('ms-date',v2); },true);
    const c2=colOf(kA);
    // Next report period, inside the coalescing window of the 2nd save: the
    // period alone must force a new entry.
    REPORT_META.reportDate=new Date(origReport.getTime()+7*86400000);
    FAKE=T0+12*60000;
    await card(kA,function(){ setVal('ms-date',v3); },true);
    const c3=colOf(kA);
    const eA=msEntries(kA);
    ck('A1 three saves (T, T+11min, next period) make 3 ms entries for the key',
       eA.length===3, eA.length+' entries');
    ck('A1 each entry carries its own finish date, in order',
       J(eA.map(function(e){ return e.changes.date&&e.changes.date.to; }))===J([v1,v2,v3]),
       J(eA.map(function(e){ return e.changes.date&&e.changes.date.to; })));
    ck('A1 the third entry is in a later period than the second',
       eA.length===3&&eA[2].period>eA[1].period&&eA[1].period===eA[0].period,
       eA.map(function(e){ return e.period; }).join(' | '));
    ck('A1 MS_FIELD_OVERRIDE[key].date equals the 3rd value',
       (MS_FIELD_OVERRIDE[kA]||{}).date===v3, J(MS_FIELD_OVERRIDE[kA]));
    const dc=function(v){ return dateToCol(v); };
    ck('A1 the marker moved on the board: one column per week, measured on its cell',
       !!(colA0&&c1&&c2&&c3)&&c1.cell-colA0.cell===dc(v1)-dc(a0)&&
       c2.cell-c1.cell===dc(v2)-dc(v1)&&c3.cell-c2.cell===dc(v3)-dc(v2)&&
       c3.cell>colA0.cell, J({colA0:colA0,c1:c1,c2:c2,c3:c3}));
    const step=async function(label,wantDate,wantCol){
      const ru=SRETEntries.rollup(ENTRIES,kA);
      const rid=ru.byField.date&&ru.byField.date.eid;
      const gone=SRETEntries.remove(ENTRIES,rid);
      projectEntryStores();
      scheduleRerender(true); await settle();
      const now=(MS_FIELD_OVERRIDE[kA]||{}).date;
      const col=colOf(kA);
      ck('A1 '+label+': removing the latest entry falls back ('+(wantDate||'no override')+')',
         !!gone&&(wantDate?now===wantDate:!(kA in MS_FIELD_OVERRIDE)), 'override='+J(MS_FIELD_OVERRIDE[kA]));
      ck('A1 '+label+': the marker is back in that column',
         !!col&&col.cell===wantCol.cell, J(col)+' want '+J(wantCol));
    };
    await step('3rd removed',v2,c2);
    await step('2nd removed',v1,c1);
    await step('1st removed',null,colA0);
    REPORT_META.reportDate=origReport;

    // ============================ A2 ============================
    const W=600000;
    // The schedule's own date, read BEFORE any save: B is the live board copy
    // and its .date follows the override once the board is rebuilt.
    const b0=B.date;
    const w1=addDays(b0,7), w2=addDays(b0,14), w3=addDays(b0,21), w4=addDays(b0,7);
    FAKE=T0+30*60000;
    await card(kB,function(){ setVal('ms-date',w1); },false);
    let eB=msEntries(kB), last=eB[eB.length-1];
    ck('A2 first save makes one entry', eB.length===1, eB.length);
    FAKE=Date.parse(last.updatedAt)+W-1;
    await card(kB,function(){ setVal('ms-date',w2); },false);
    eB=msEntries(kB); last=eB[eB.length-1];
    ck('A2 a save at updatedAt+599999 ms merges: count unchanged',
       eB.length===1, eB.length);
    ck('A2 ... the entry`s `to` is the new value and `from` is still the original',
       eB.length===1&&last.changes.date&&last.changes.date.to===w2&&
       last.changes.date.from===b0, J(last.changes.date)+' original='+b0);
    FAKE=Date.parse(last.updatedAt)+W+1;
    await card(kB,function(){ setVal('ms-date',w3); },false);
    eB=msEntries(kB); last=eB[eB.length-1];
    ck('A2 a save at updatedAt+600001 ms appends: count +1',
       eB.length===2&&last.changes.date&&last.changes.date.to===w3, eB.length);
    FAKE=Date.parse(last.updatedAt)+W;
    await card(kB,function(){ setVal('ms-date',w4); },false);
    eB=msEntries(kB); last=eB[eB.length-1];
    ck('A2 a save at exactly updatedAt+600000 ms merges (window is inclusive)',
       eB.length===2&&last.changes.date&&last.changes.date.to===w4, eB.length+' '+J(last.changes.date));
    ck('A2 the store follows the merged entry',
       (MS_FIELD_OVERRIDE[kB]||{}).date===w4, J(MS_FIELD_OVERRIDE[kB]));

    // ============================ A3 ============================
    FAKE=T0+60*60000;
    await card(kC,function(){ setVal('ms-comment-text','remark one'); },true);
    let eC=msEntries(kC);
    ck('A3 a card remark creates an entry with that text',
       eC.length===1&&eC[0].text==='remark one', J(eC.map(function(e){ return e.text; })));
    ck('A3 MS_COMMENTS[key] equals it', MS_COMMENTS[kC]==='remark one', MS_COMMENTS[kC]);
    FAKE=T0+61*60000;
    let boxAtOpen=null;
    await card(kC,function(){ boxAtOpen=$('ms-comment-text').value; setVal('ms-comment-text',''); },true);
    eC=msEntries(kC);
    ck('A3 (P66) the card opens with an EMPTY remark box, and saving it empty makes no clearText entry',
       boxAtOpen===''&&eC.length===1&&!eC.some(function(e){ return e.clearText; }),
       J({boxAtOpen:boxAtOpen,entries:eC.map(function(e){ return [e.text,e.clearText]; })}));
    ck('A3 (P66) and the stored remark is untouched by it', MS_COMMENTS[kC]==='remark one', J(MS_COMMENTS[kC]));
    FAKE=T0+62*60000;
    await card(kC,function(){ setVal('ms-comment-text','remark two'); },true);
    ck('A3 a later remark shows again', MS_COMMENTS[kC]==='remark two'&&msEntries(kC).length===2,
       MS_COMMENTS[kC]+' / '+msEntries(kC).length+' entries');

    // ============================ A4 ============================
    FAKE=T0+90*60000;
    await card(kD,function(){ onMsHealthClick(healthDot(0)); },true);
    ck('A4 the N/A dot (health 0) projects MS_HEALTH_OVERRIDE[key] === 0',
       (kD in MS_HEALTH_OVERRIDE)&&MS_HEALTH_OVERRIDE[kD]===0, J(MS_HEALTH_OVERRIDE[kD]));
    FAKE=T0+102*60000;
    await card(kD,function(){
      ck('A4 (setup) the card reopens with the N/A dot selected',
         healthDot(0).classList.contains('selected'));
      onMsHealthClick(healthDot(0));      // the selected dot again = automatic (-1)
    },true);
    const eD=msEntries(kD), lastD=eD[eD.length-1];
    ck('A4 "automatic" (the selected dot clicked again) removes the key',
       !(kD in MS_HEALTH_OVERRIDE), J(MS_HEALTH_OVERRIDE[kD]));
    ck('A4 ... through an explicit health -> null entry',
       eD.length===2&&lastD.changes.health&&lastD.changes.health.to===null, J(lastD&&lastD.changes));
    // Both clicks inside one coalescing window: net nothing.
    FAKE=T0+120*60000;
    await card(kF,function(){ onMsHealthClick(healthDot(0)); },true);
    ck('A4 (setup) N/A on a second milestone is set', MS_HEALTH_OVERRIDE[kF]===0);
    FAKE=T0+121*60000;
    await card(kF,function(){ onMsHealthClick(healthDot(0)); },true);
    ck('A4 set then cleared inside one window: no key and no entry left behind',
       !(kF in MS_HEALTH_OVERRIDE)&&msEntries(kF).length===0,
       J(MS_HEALTH_OVERRIDE[kF])+' / '+msEntries(kF).length+' entries');

    // ============================ A5 ============================
    const P=E.progress, diff=(P===37)?73:37;
    R.notes.schedProgress=P;
    FAKE=T0+150*60000;
    await card(kE,function(){ setVal('ms-progress-input',String(P)); setVal('ms-comment-text','progress equals schedule'); },true);
    ck('A5 a progress equal to the schedule leaves no MS_PROGRESS_OVERRIDE key',
       !(kE in MS_PROGRESS_OVERRIDE), J(MS_PROGRESS_OVERRIDE[kE])+' schedule='+P);
    FAKE=T0+162*60000;
    await card(kE,function(){ setVal('ms-progress-input',String(diff)); },true);
    ck('A5 a different progress sets the key',
       MS_PROGRESS_OVERRIDE[kE]===diff, J(MS_PROGRESS_OVERRIDE[kE])+' want '+diff);
    FAKE=T0+175*60000;
    await card(kE,function(){ setVal('ms-progress-input',String(P)); },true);
    ck('A5 entering the schedule figure again clears the key',
       !(kE in MS_PROGRESS_OVERRIDE), J(MS_PROGRESS_OVERRIDE[kE]));

    // ============================ A6 ============================
    FAKE=T0+200*60000;
    annotWrite('msHealth',kG,'value',3);
    let eG=msEntries(kG);
    ck('A6 annotWrite msHealth 3: a grid entry and the store set',
       eG.length===1&&eG[0].origin==='grid'&&eG[0].changes.health&&eG[0].changes.health.to===3&&
       MS_HEALTH_OVERRIDE[kG]===3, J(eG.map(function(e){ return [e.origin,e.changes]; }))+' store='+J(MS_HEALTH_OVERRIDE[kG]));
    FAKE=T0+201*60000;
    annotWrite('msHealth',kG,'value','');
    ck('A6 a blank health value clears it', !(kG in MS_HEALTH_OVERRIDE), J(MS_HEALTH_OVERRIDE[kG]));
    FAKE=T0+202*60000;
    annotWrite('comments',kG,'value','grid remark');
    ck('A6 annotWrite comments with text: entry (origin grid) and store set',
       MS_COMMENTS[kG]==='grid remark'&&msEntries(kG).some(function(e){ return e.origin==='grid'&&e.text==='grid remark'; }),
       J(MS_COMMENTS[kG]));
    FAKE=T0+203*60000;
    annotWrite('comments',kG,'value','');
    ck('A6 annotWrite comments blank: cleared', !(kG in MS_COMMENTS), J(MS_COMMENTS[kG]));
    FAKE=T0+204*60000;
    const row=userMsGridAdd();
    const rec=USER_MILESTONES[USER_MILESTONES.length-1];
    const kU=msKeyFor(rec);
    ck('A6 userMsGridAdd made a user milestone with a USR- key', !!row&&/^USR-/.test(rec.id)&&/^USR-/.test(kU), rec&&rec.id+' / '+kU);
    FAKE=T0+205*60000;
    const okU=userMsGridEdit(rec.id,'health',3);   // grid 3 (Critical) -> MS_HEALTH_OVERRIDE 4
    ck('A6 userMsGridEdit(id,"health",3) holds the translated value under the USR key',
       okU===true&&MS_HEALTH_OVERRIDE[kU]===UMS_GRID_TO_MSH[3]&&UMS_GRID_TO_MSH[3]===4,
       'ok='+okU+' store='+J(MS_HEALTH_OVERRIDE[kU]));
    ck('A6 ... as a grid entry keyed by the USR id',
       msEntries(kU).some(function(e){ return e.origin==='grid'&&e.changes.health&&e.changes.health.to===4; }),
       J(msEntries(kU).map(function(e){ return [e.origin,e.changes]; })));
    FAKE=T0+206*60000;
    userMsGridEdit(rec.id,'health',4);              // grid 4 (Done) -> 2
    ck('A6 a second edit on the USR milestone wins (latest-wins holds for USR keys)',
       MS_HEALTH_OVERRIDE[kU]===2, J(MS_HEALTH_OVERRIDE[kU]));
    scheduleRerender(true); await settle();

    // ============================ A7 ============================
    FAKE=T0+230*60000;
    const nids=[];
    ['A7 note one','A7 note two','A7 note three'].forEach(function(t,i){
      FAKE=T0+(230+i)*60000;
      $('note-input').value=t; saveNewNote();
      const n=NOTES[NOTES.length-1]; nids.push(n&&n.nid);
    });
    const gen=function(nid){ return ENTRIES.filter(function(e){ return e.target.kind==='general'&&e.nid===nid; })[0]; };
    ck('A7 saveNewNote x3 makes 3 general entries, each with a distinct nid',
       nids.every(Boolean)&&new Set(nids).size===3&&nids.every(function(n){ return !!gen(n)&&gen(n).target.key===null; }), J(nids));
    ck('A7 NOTES mirrors them (nid, text, status open)',
       nids.every(function(n,i){ const x=NOTES.filter(function(q){ return q.nid===n; })[0];
         return x&&x.text==='A7 note '+['one','two','three'][i]&&x.status==='open'; }), J(NOTES.map(function(n){ return [n.nid,n.status]; })));
    setNoteStatus(nids[0],'sent'); setNoteStatus(nids[1],'done');
    ck('A7 setNoteStatus changes the entry status',
       gen(nids[0]).status==='sent'&&gen(nids[1]).status==='done'&&gen(nids[2]).status==='open',
       J(nids.map(function(n){ return gen(n).status; })));
    ck('A7 ... and NOTES mirrors it',
       nids.every(function(n){ return NOTES.filter(function(q){ return q.nid===n; })[0].status===gen(n).status; }));
    deleteNote(nids[2]);
    ck('A7 deleteNote removes the entry', !gen(nids[2]));
    ck('A7 ... and NOTES mirrors it (2 left)',
       !NOTES.some(function(q){ return q.nid===nids[2]; })&&NOTES.filter(function(q){ return nids.indexOf(q.nid)>=0; }).length===2,
       J(NOTES.map(function(n){ return n.nid; })));
    R.notes.nids=nids;

    // ============================ A8 ============================
    FAKE=null;
    projectEntryStores();     // a no-op projection: the baseline for the comparison
    const before=J([MS_COMMENTS,MS_HEALTH_OVERRIDE,MS_PROGRESS_OVERRIDE,MS_FIELD_OVERRIDE,NOTES]);
    ck('A8 after every flow, the app`s own writers adopted nothing (ENTRY_DRIFT_ADOPTED === 0)',
       ENTRY_DRIFT_ADOPTED===0, ENTRY_DRIFT_ADOPTED);
    projectEntryStores();
    const after=J([MS_COMMENTS,MS_HEALTH_OVERRIDE,MS_PROGRESS_OVERRIDE,MS_FIELD_OVERRIDE,NOTES]);
    ck('A8 the stores deep-equal a fresh projection (JSON before === after)', before===after,
       before===after?'':before.slice(0,200)+' /// '+after.slice(0,200));
    ck('A8 the stores are not empty (the comparison is not vacuous)',
       Object.keys(MS_COMMENTS).length>=1&&Object.keys(MS_HEALTH_OVERRIDE).length>=1&&
       Object.keys(MS_FIELD_OVERRIDE).length>=1&&NOTES.length>=2,
       [Object.keys(MS_COMMENTS).length,Object.keys(MS_HEALTH_OVERRIDE).length,
        Object.keys(MS_PROGRESS_OVERRIDE).length,Object.keys(MS_FIELD_OVERRIDE).length,NOTES.length].join(','));
    const drift0=ENTRY_DRIFT_ADOPTED;
    MS_COMMENTS[kK]='direct';
    projectEntryStores();
    ck('A8 a direct store write is adopted: ENTRY_DRIFT_ADOPTED increments',
       ENTRY_DRIFT_ADOPTED===drift0+1, drift0+' -> '+ENTRY_DRIFT_ADOPTED);
    ck('A8 ... the value survives the projection', MS_COMMENTS[kK]==='direct', J(MS_COMMENTS[kK]));
    ck('A8 ... as an entry with origin "direct"',
       msEntries(kK).some(function(e){ return e.origin==='direct'&&e.text==='direct'; }),
       J(msEntries(kK).map(function(e){ return [e.origin,e.text]; })));

    // ============================ A9 (stage 1 half) ============================
    R.entriesLen=ENTRIES.length;
    R.stores=storesNow();
    R.entriesJson=J(ENTRIES);
    R.drift=ENTRY_DRIFT_ADOPTED;
    capName='published'; publishDashboard();
    await sleep(100);
    R.publishedText=await CAP.published.text();
    R.ok=true;
  }catch(e){ R.err=e.message+' '+(e.stack||'').split('\n').slice(0,3).join(' | '); }
  finish();
})();
"""

# --------------------------------------------------------------------------
# Stage 2: load the published file as a reader would.
# --------------------------------------------------------------------------
STAGE2 = r"""
(async function(){
  try{
    await sleep(500); await settle();
    R.entriesLen=ENTRIES.length;
    R.entriesJson=J(ENTRIES);
    R.stores=storesNow();
    R.drift=ENTRY_DRIFT_ADOPTED;
    R.ok=true;
  }catch(e){ R.err=e.message; }
  finish();
})();
"""

# --------------------------------------------------------------------------
# Stage 3: mount the P64 fixture into a clean app, twice.
# --------------------------------------------------------------------------
STAGE3 = r"""
(async function(){
  try{
    await sleep(500); await settle();
    const fx=fixtureData(), text=$('p65-data').textContent;
    R.before={entries:ENTRIES.length,stores:storesNow()};
    const v=validateModelPayload(text,'model_p64.json');
    ck('A10 (setup) validateModelPayload accepts the P64 file with no errors', v.ok&&!v.errors.length, J(v.errors));
    ck('A10 (setup) the file carries no entries (it is a P64 export)', !Array.isArray(fx.entries));
    await mountFile(text,'model_p64.json');
    R.after1={entries:ENTRIES.length,stores:storesNow(),drift:ENTRY_DRIFT_ADOPTED};
    const nonEmpty=function(o){ const r={}; Object.keys(o||{}).forEach(function(k){ if(String(o[k]).trim()!=='') r[k]=o[k]; }); return r; };
    ck('A10 MS_COMMENTS (ignoring empty strings) equals the fixture`s milestoneComments',
       J(Object.keys(MS_COMMENTS).sort().map(function(k){ return [k,MS_COMMENTS[k]]; }))===
       J(Object.keys(nonEmpty(fx.milestoneComments)).sort().map(function(k){ return [k,fx.milestoneComments[k]]; })),
       J(MS_COMMENTS)+' vs '+J(nonEmpty(fx.milestoneComments)));
    const eqObj=function(a,b){ const ka=Object.keys(a).sort(), kb=Object.keys(b).sort();
      return J(ka)===J(kb)&&ka.every(function(k){ return J(a[k])===J(b[k]) ||
        (typeof a[k]==='object'&&a[k]&&J(Object.keys(a[k]).sort().map(function(f){return [f,a[k][f]];}))===
                                        J(Object.keys(b[k]).sort().map(function(f){return [f,b[k][f]];}))); }); };
    ck('A10 MS_HEALTH_OVERRIDE equals milestoneHealthOverrides (incl. the explicit 0)',
       eqObj(MS_HEALTH_OVERRIDE,fx.milestoneHealthOverrides)&&Object.keys(fx.milestoneHealthOverrides).length>=2,
       J(MS_HEALTH_OVERRIDE)+' vs '+J(fx.milestoneHealthOverrides));
    ck('A10 MS_PROGRESS_OVERRIDE equals milestoneProgressOverrides',
       eqObj(MS_PROGRESS_OVERRIDE,fx.milestoneProgressOverrides)&&Object.keys(fx.milestoneProgressOverrides).length>=2,
       J(MS_PROGRESS_OVERRIDE)+' vs '+J(fx.milestoneProgressOverrides));
    ck('A10 MS_FIELD_OVERRIDE equals milestoneFieldOverrides',
       eqObj(MS_FIELD_OVERRIDE,fx.milestoneFieldOverrides)&&Object.keys(fx.milestoneFieldOverrides).length>=2,
       J(MS_FIELD_OVERRIDE)+' vs '+J(fx.milestoneFieldOverrides));
    const byNid=function(l){ const r={}; l.forEach(function(n){ r[n.nid]=n.status; }); return r; };
    ck('A10 NOTES carries the fixture notes` nids and statuses (N=3)',
       fx.notes.length===3&&J(byNid(NOTES))===J(byNid(fx.notes))&&J(Object.keys(byNid(NOTES)).sort())===J(fx.notes.map(function(n){ return n.nid; }).sort()),
       J(byNid(NOTES))+' vs '+J(byNid(fx.notes)));
    ck('A10 ... and their text',
       fx.notes.every(function(n){ const x=NOTES.filter(function(q){ return q.nid===n.nid; })[0]; return x&&x.text===n.text; }));
    ck('A10 mounting carried nothing as drift (the mount path is an app writer)',
       ENTRY_DRIFT_ADOPTED===0, ENTRY_DRIFT_ADOPTED);
    const n1=ENTRIES.length;
    ck('A10 (setup) the first mount made entries', n1>0, n1);
    await mountFile(text,'model_p64.json');
    R.after2={entries:ENTRIES.length,stores:storesNow()};
    ck('A10 mounting the SAME file again leaves ENTRIES.length unchanged',
       ENTRIES.length===n1, n1+' -> '+ENTRIES.length);
    ck('A10 ... and the stores unchanged', J(R.after2.stores)===J(R.after1.stores));
    R.ok=true;
  }catch(e){ R.err=e.message+' '+(e.stack||'').split('\n').slice(0,3).join(' | '); }
  finish();
})();
"""

# --------------------------------------------------------------------------
# Stage 4: board signature after mounting the fixture. Runs unchanged against
# the P64 release and the current app, so it uses no P65 symbol.
# --------------------------------------------------------------------------
STAGE4 = r"""
(async function(){
  try{
    await sleep(500); await settle();
    const text=$('p65-data').textContent;
    await mountFile(text,'model_p64.json');
    scheduleRerender(true); await settle(); await settle();
    const sig=[];
    document.querySelectorAll('#tbody .m-wrap[data-ms]').forEach(function(w){
      const td=w.closest('td'), tr=w.closest('tr');
      const mark=w.querySelector('.m-board-edit-mark');
      const ic=w.querySelector('.ms-icon');
      sig.push({
        id:w.getAttribute('data-ms'),
        cls:w.className.split(/\s+/).filter(Boolean).sort().join(' '),
        icon:ic?String(ic.getAttribute('class')||'').split(/\s+/).filter(Boolean).sort().join(' '):null,
        editMark:!!mark, editTitle:mark?mark.title:null,
        ghostInRow:tr?tr.querySelectorAll('.m-edit-ghost').length:0,
        col:td?td.getAttribute('data-col'):null, cell:td?td.cellIndex:null
      });
    });
    sig.sort(function(a,b){ return (a.id+'|'+a.cls+'|'+a.cell).localeCompare(b.id+'|'+b.cls+'|'+b.cell); });
    const ghosts=[];
    document.querySelectorAll('#tbody .m-edit-ghost').forEach(function(g){
      const td=g.closest('td'), tr=g.closest('tr');
      ghosts.push({ref:tr?tr.getAttribute('data-ref'):null,cell:td?td.cellIndex:null,title:g.title});
    });
    ghosts.sort(function(a,b){ return J(a).localeCompare(J(b)); });
    R.sig=sig; R.ghosts=ghosts; R.version=APP_VERSION;
    R.ok=true;
  }catch(e){ R.err=e.message+' '+(e.stack||'').split('\n').slice(0,3).join(' | '); }
  finish();
})();
"""

# --------------------------------------------------------------------------
# Stage 5: three entries in a clean new-build app, then export the model.
# --------------------------------------------------------------------------
STAGE5 = r"""
(async function(){
  try{
    await sleep(600); await settle();
    const T0=realNow();
    const cand=candidates();
    const A=cand[0], B=cand[1];
    const kA=msKeyFor(A), kB=msKeyFor(B);
    FAKE=T0;
    await card(kA,function(){ setVal('ms-date',addDays(A.date,7)); setVal('ms-comment-text','v2 remark on A'); },true);
    FAKE=T0+1*60000;
    await card(kB,function(){ onMsHealthClick(healthDot(2)); },true);
    FAKE=T0+2*60000;
    $('note-input').value='v2 note about #'+msId(A); saveNewNote();
    FAKE=null;
    ck('A12 (setup) three writes made exactly 3 entries', ENTRIES.length===3, ENTRIES.length);
    R.stores=storesNow();
    capName='model'; exportModel();
    await sleep(50);
    R.modelText=await CAP.model.text();
    R.ok=true;
  }catch(e){ R.err=e.message+' '+(e.stack||'').split('\n').slice(0,3).join(' | '); }
  finish();
})();
"""

# --------------------------------------------------------------------------
# Stage 6: mount that v2 file into a clean new-build app, twice.
# --------------------------------------------------------------------------
STAGE6 = r"""
(async function(){
  try{
    await sleep(500); await settle();
    const text=$('p65-data').textContent, want=JSON.parse($('p65-want').textContent);
    const v=validateModelPayload(text,'model_v2.json');
    ck('A12 (setup) validateModelPayload accepts the v2 file', v.ok&&!v.errors.length, J(v.errors)+J(v.warnings));
    ck('A12 (setup) it carries entries', Array.isArray(v.payload&&v.payload.entries)&&v.payload.entries.length===3,
       v.payload&&v.payload.entries&&v.payload.entries.length);
    await mountFile(text,'model_v2.json');
    ck('A12 mounting the v2 file gives ENTRIES.length === 3', ENTRIES.length===3, ENTRIES.length);
    ck('A12 the stores match the exporting app`s', J(storesNow())===J(want)||
       (function(){ const a=storesNow(); return ['comments','health','progress','fields'].every(function(k){
          return J(Object.keys(a[k]).sort().map(function(x){ return [x,a[k][x]]; }))===
                 J(Object.keys(want[k]).sort().map(function(x){ return [x,want[k][x]]; })); })&&
          J(a.notes.map(function(n){ return [n.nid,n.text,n.status]; }))===J(want.notes.map(function(n){ return [n.nid,n.text,n.status]; })); })(),
       J(storesNow())+' vs '+J(want));
    await mountFile(text,'model_v2.json');
    ck('A12 mounting it again is still 3', ENTRIES.length===3, ENTRIES.length);
    ck('A12 ... and the stores are unchanged', J(storesNow().comments)===J(want.comments)&&NOTES.length===want.notes.length);
    ck('A12 nothing was adopted as drift', ENTRY_DRIFT_ADOPTED===0, ENTRY_DRIFT_ADOPTED);
    R.ok=true;
  }catch(e){ R.err=e.message+' '+(e.stack||'').split('\n').slice(0,3).join(' | '); }
  finish();
})();
"""


def data_block(el_id, payload):
    # application/json script blocks are inert, and escaping the angle brackets
    # keeps a stray closing tag in the data from ending the block.
    safe = payload.replace("<", "\\u003c").replace(">", "\\u003e")
    return f'<script type="application/json" id="{el_id}">{safe}</script>\n'


def probe(html, body, extras="", budget=30000, prelude=True):
    js = (PRELUDE if prelude else "") + "\n" + body
    out = html.replace("</body>", f"{extras}<script>\n{js}\n</script>\n</body>")
    if out == html:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p65chk.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             "--host-resolver-rules=MAP * ~NOTFOUND",
             f"--virtual-time-budget={budget}", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=400)
    hits = OUT_RE.findall(proc.stdout)
    if not hits:
        return {"ok": False, "checks": [], "err": "probe output not found; the page likely threw "
                "before the probe finished. " + proc.stderr[-1500:]}
    return json.loads(base64.b64decode(hits[-1].strip()).decode("utf-8"))


def published_payload(text):
    i = text.find("window.__PUBLISHED_STATE__=")
    if i < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(text[i + len("window.__PUBLISHED_STATE__="):])
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    ap.add_argument("--p64", default=str(ROOT / "releases" / "v3.1.0-P64_schedule-info-bar.html"))
    a = ap.parse_args()

    html = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    p64 = pathlib.Path(a.p64).read_text(encoding="utf-8", errors="replace")
    fixture = FIXTURE.read_text(encoding="utf-8")

    results = []   # (name, passed, detail)

    def add(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    def take(R, stage):
        for c in R.get("checks", []):
            add(c["name"], c["pass"], c["detail"])
        if R.get("err"):
            add(f"{stage} probe ran to completion", False, R["err"])
        elif not R.get("ok") and not R.get("checks"):
            add(f"{stage} probe ran to completion", False, "no result")

    # ---------------- stage 1: A1..A8, then publish ----------------
    R1 = probe(html, STAGE1, budget=90000)
    take(R1, "stage 1 (A1-A8)")

    if R1.get("ok"):
        pub = R1["publishedText"]
        payload = published_payload(pub)
        add("A9 the published file carries a state block", payload is not None)
        if payload is not None:
            add("A9 the payload carries `entries` (the record)",
                isinstance(payload.get("entries"), list) and len(payload["entries"]) == R1["entriesLen"],
                f"{len(payload.get('entries') or [])} entries vs {R1['entriesLen']} live")
            legacy = {"milestoneComments": "comments", "milestoneHealthOverrides": "health",
                      "milestoneProgressOverrides": "progress", "milestoneFieldOverrides": "fields"}
            add("A9 the payload also carries the legacy store fields (for pre-P65 builds)",
                all(k in payload for k in legacy) and "notes" in payload,
                ",".join(k for k in list(legacy) + ["notes"] if k not in payload) or "all present")
            add("A9 the legacy fields equal the pre-publish stores",
                all(payload.get(k) == R1["stores"][v] for k, v in legacy.items())
                and [n["nid"] for n in payload.get("notes", [])] == [n["nid"] for n in R1["stores"]["notes"]],
                "")
        # stage 2: read it back
        R2 = probe(pub, STAGE2, extras="", budget=30000)
        take(R2, "stage 2 (A9)")
        if R2.get("ok"):
            add("A9 ENTRIES.length after loading the published file equals the live count",
                R2["entriesLen"] == R1["entriesLen"], f"{R2['entriesLen']} vs {R1['entriesLen']}")
            for k in ("comments", "health", "progress", "fields"):
                add(f"A9 store {k} deep-equals the pre-publish store",
                    R2["stores"][k] == R1["stores"][k],
                    "" if R2["stores"][k] == R1["stores"][k] else
                    f"got {json.dumps(R2['stores'][k])[:300]} want {json.dumps(R1['stores'][k])[:300]}")
            add("A9 store notes deep-equals the pre-publish store",
                R2["stores"]["notes"] == R1["stores"]["notes"],
                "" if R2["stores"]["notes"] == R1["stores"]["notes"] else
                f"got {json.dumps(R2['stores']['notes'])[:300]}")
            add("A9 the entries themselves survive unchanged (JSON equal)",
                json.loads(R2["entriesJson"]) == json.loads(R1["entriesJson"]),
                "")
            add("A9 loading the published file adopts nothing as drift",
                R2["drift"] == 0, R2["drift"])
    else:
        add("A9 publish round trip", False, "stage 1 did not reach the publish step")

    # ---------------- stage 3: A10 ----------------
    R3 = probe(html, STAGE3, extras=data_block("p65-data", fixture), budget=45000)
    take(R3, "stage 3 (A10)")

    # ---------------- stage 4: A11 ----------------
    R4a = probe(p64, STAGE4, extras=data_block("p65-data", fixture), budget=45000)
    take(R4a, "stage 4 (A11, P64 release)")
    R4b = probe(html, STAGE4, extras=data_block("p65-data", fixture), budget=45000)
    take(R4b, "stage 4 (A11, current app)")
    if R4a.get("ok") and R4b.get("ok"):
        sa, sb = R4a["sig"], R4b["sig"]
        edited = [s for s in sb if s["editMark"]]
        add("A11 (setup) the P64 release is what its label says", "P64" in (R4a.get("version") or ""),
            R4a.get("version"))
        add("A11 (setup) both boards drew markers, and the same number of them",
            len(sa) >= 20 and len(sa) == len(sb), f"P64 {len(sa)}, current {len(sb)}")
        add("A11 (setup) the sample carries edited markers and an edit ghost (not a vacuous match)",
            len(edited) >= 2 and len(R4b["ghosts"]) >= 1,
            f"{len(edited)} edited markers, {len(R4b['ghosts'])} edit ghosts")
        add("A11 marker signatures (classes, edit mark + title, ghost in row, column cell) are identical",
            sa == sb,
            "" if sa == sb else "first difference: " + next(
                (f"{x} != {y}" for x, y in zip(sa, sb) if x != y), "length differs"))
        add("A11 the edit ghosts (row, cell, title) are identical", R4a["ghosts"] == R4b["ghosts"],
            "" if R4a["ghosts"] == R4b["ghosts"] else f"{R4a['ghosts']} vs {R4b['ghosts']}")

    # ---------------- stage 5/6: A12 ----------------
    R5 = probe(html, STAGE5, budget=45000)
    take(R5, "stage 5 (A12 export)")
    if R5.get("ok"):
        model = json.loads(R5["modelText"])
        # NOTE: the brief calls this a "v2 file"; the app's MODEL_SCHEMA_VERSION is
        # still 1 and the export carries entries under schemaVersion 1 (so a P64
        # build still opens it). Asserting schemaVersion === 2 would fail on what
        # looks like a deliberate app choice, so the check asserts the entries and
        # the legacy fields, and reports the declared version.
        add("A12 the export carries 3 entries plus the legacy fields",
            len(model.get("entries", [])) == 3 and "milestoneComments" in model and "notes" in model,
            f"schemaVersion={model.get('schemaVersion')} entries={len(model.get('entries', []))}")
        R6 = probe(html, STAGE6,
                   extras=data_block("p65-data", R5["modelText"]) + data_block("p65-want", json.dumps(R5["stores"])),
                   budget=45000)
        take(R6, "stage 6 (A12 mount)")
    else:
        add("A12 mount a v2 file", False, "stage 5 did not produce an export")

    passed = 0
    for name, ok, detail in results:
        line = ("PASS  " if ok else "FAIL  ") + name
        if not ok and detail:
            line += "\n        " + str(detail)[:600]
        print(line)
        passed += ok
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
