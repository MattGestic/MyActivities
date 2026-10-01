#!/usr/bin/env python3
"""
p72_deps_check: predecessors and successors on user milestones, no float on
them, and float read only on schedule milestones (P72, Matt 2026-10-01).

Stage 1, at 1440 and 390 px, drives the real app in headless Chrome:
  - adds a user milestone through the header button and the Add milestone
    dialog (openAddMilestone / saveAddMilestone);
  - on its card, types into the predecessor Add field and picks SNIP-102 from
    the suggestions with a cancelable mousedown (the onmousedown +
    preventDefault rule: the field keeps focus, the card stays open), and adds
    successor SNIP-126 with Enter; Save & close;
  - reopens: own chips with a remove cross; SNIP-102's card lists the user
    milestone among its successors, SNIP-126's among its predecessors, with no
    cross (read only); the dependency layer holds a line for each link, read
    from the SVG DOM, with its ends at the right markers, both directions;
    counts on the markers and in the card; the zero-count filter; the update
    history shows the change in words;
  - removes SNIP-102 with its cross, saves: gone from the record, the card,
    SNIP-102's card, DEP_DATA and the lines;
  - Discard after adding a link keeps nothing; a click away saves;
  - float: "-" and read only on the user milestone, no float in its tooltip,
    float filters treat it as unknown without throwing; read only and the
    schedule's own value on a schedule milestone; a legacy float override
    seeded through the entry store no longer changes the board;
  - N=3: two more user milestones chained A -> B -> C -> SNIP-126, with the
    inbound links shown on each card and four lines drawn.
  At 1440 it then captures publishDashboard() and exportModel().
Stage 2 opens the published copy; stage 3 imports the model into a clean app
through the real import categories. Both must carry the links. DEP_DATA with
the user links taken out must equal the schedule literal in the source at
every stage, and the published file's literal must be byte identical.

Usage: python3 tools/p72_deps_check.py [--html FILE]
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
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p72-out">(.*?)</pre>', re.S)
VIEWPORTS = [(1440, 900), (390, 844)]

COMMON = r"""
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p72-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const gap=()=>new Promise(r=>setTimeout(r,420));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog');
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const open=async function(id){
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    await gap(); const w=wrapOf(id); if(!w) throw new Error('no marker for '+id);
    w.click(); await settle();
    if(dlg().hidden) throw new Error('card did not open for '+id);
    const f=$('ms-dep-lists'); if(f&&!f.open){ f.querySelector('summary').click(); await settle(); }
  };
  const chips=k=>Array.from($('ms-dep-'+k+'-chips').querySelectorAll('.ms-dep-chip')).map(b=>b.getAttribute('data-id'));
  const ownChips=k=>Array.from($('ms-dep-'+k+'-chips').querySelectorAll('.ms-dep-chip.is-own')).map(b=>b.getAttribute('data-id'));
  const lst=v=>String(v||'').split(',').map(s=>s.trim()).filter(Boolean);
  // DEP_DATA with every user link taken out: what the schedule said.
  const strip=function(dd){
    const o={};
    Object.keys(dd).forEach(function(k){
      if(/^USR-/.test(k)) return;
      const p=lst(dd[k].pred).filter(x=>!/^USR-/.test(x)).join(',');
      const s=lst(dd[k].succ).filter(x=>!/^USR-/.test(x)).join(',');
      if(!(k in DEP_DATA_SCHEDULE)&&!p&&!s) return;
      o[k]={pred:p,succ:s};
    });
    return o;
  };
  const canon=function(v){ if(v===null||typeof v!=='object') return JSON.stringify(v);
    return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canon(v[k])).join(',')+'}'; };
  const lines=()=>Array.from(document.querySelectorAll('#dep-lines-g path.dep-line')).map(function(p){
    const n=(p.getAttribute('d').match(/-?\d+(\.\d+)?/g)||[]).map(Number);
    return {a:{x:n[0],y:n[1]},b:{x:n[n.length-2],y:n[n.length-1]},cls:p.getAttribute('class')}; });
  const near=(p,q)=>p&&q&&Math.hypot(p.x-q.x,p.y-q.y)<=40;
  // A drawn line from one marker to another (arrow at the second).
  const hasLine=(from,to)=>{ const f=markerCenter(from), t=markerCenter(to);
    return !!f&&!!t&&lines().some(l=>near(l.a,f)&&near(l.b,t)); };
  const allFlagsOff=()=>{ Object.keys(DEP_VIS).forEach(k=>{ DEP_VIS[k].pred=false; DEP_VIS[k].succ=false; }); drawDepLines(); };
"""

PROBE = r"""
(async function(){
""" + COMMON + r"""
  const typeAdd=async function(kind,text){
    const a=$('ms-dep-add-'+kind); a.focus(); a.value=text;
    a.dispatchEvent(new Event('input',{bubbles:true})); await settle(); return a; };
  const sugIds=()=>Array.from(document.querySelectorAll('#ms-dep-suggest .id-suggest-item')).map(e=>e.getAttribute('data-id'));
  const pick=async function(id){
    const it=document.querySelector('#ms-dep-suggest .id-suggest-item[data-id="'+CSS.escape(id)+'"]');
    if(!it) return {found:false};
    const md=new MouseEvent('mousedown',{bubbles:true,cancelable:true});
    const notCancelled=it.dispatchEvent(md);
    it.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));
    it.click(); await settle();
    return {found:true,prevented:!notCancelled};
  };
  const enterAdd=async function(kind,text){
    const a=await typeAdd(kind,text);
    a.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true})); await settle(); };
  const saveClose=async function(){ document.querySelector('#ms-save-actions .ms-act-primary').click(); await gap(); await settle(); };
  const addUser=async function(name){
    $('btn-add-ms').click(); await settle();
    $('add-ms-name').value=name;
    $('add-ms-date').value=isoDay(WE_DATES[NOW_COL]);
    const id=$('add-ms-id').value;
    $('add-ms-save').click(); await gap(); await settle();
    return id;
  };
  const msEntries=k=>ENTRIES.filter(e=>e.target.kind==='ms'&&e.target.key===k);
  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    R.notes.literalStrip0=canon(strip(DEP_DATA));
    ck('load: DEP_DATA is the schedule copy before any user milestone', canon(DEP_DATA)===canon(DEP_DATA_SCHEDULE), '');
    const S102=JSON.parse(JSON.stringify(DEP_DATA['SNIP-102'])), S126=JSON.parse(JSON.stringify(DEP_DATA['SNIP-126']));
    ck('sample: SNIP-102 and SNIP-126 are on the board', !!wrapOf('SNIP-102')&&!!wrapOf('SNIP-126'), '');

    // ===== 1. Add a user milestone through the app's own add path =====
    const A=await addUser('P72 user A');
    R.notes.A=A;
    ck('add: the user milestone exists and is on the board', /^USR-/.test(A)&&!!umsRecord(A)&&!!wrapOf(A), A);
    ck('zero filter: a fresh user milestone counts as no deps', msHasNoDeps(A)===true, '');

    // ===== 2. Its card: float, and the Add fields =====
    await open(A);
    const fv=$('ms-float-val');
    ck('user float: "-" (empty, placeholder) and read only', fv.value===''&&fv.placeholder==='-'&&fv.readOnly===true, JSON.stringify([fv.value,fv.placeholder,fv.readOnly]));
    ck('user float: says it carries none', /no float/i.test(fv.title), fv.title);
    ck('card: predecessor and successor Add fields shown', !$('ms-dep-add-pred').hidden&&!$('ms-dep-add-succ').hidden&&
       $('ms-dep-add-pred').getBoundingClientRect().width>0, '');
    ck('card: no links yet', chips('pred').length===0&&chips('succ').length===0, chips('pred')+'|'+chips('succ'));
    ck('card: clean on open', $('ms-save-actions').getAttribute('aria-disabled')==='true', '');

    // Predecessor by the suggestion list (mousedown + preventDefault).
    await typeAdd('pred','SNIP-10');
    ck('suggest: list opens under the field with SNIP-102 in it', !$('ms-dep-suggest').hidden&&sugIds().indexOf('SNIP-102')>=0, sugIds().slice(0,6).join(','));
    ck('suggest: the card itself is not offered', sugIds().indexOf(A)<0, '');
    const pk=await pick('SNIP-102');
    ck('pick: mousedown default prevented (focus kept)', pk.found&&pk.prevented, JSON.stringify(pk));
    ck('pick: focus stays in the Add field', document.activeElement===$('ms-dep-add-pred'), document.activeElement&&document.activeElement.id);
    ck('pick: the card stays open', !dlg().hidden, '');
    ck('pick: SNIP-102 is an own chip with a cross', ownChips('pred').indexOf('SNIP-102')>=0&&
       !!$('ms-dep-pred-chips').querySelector('.ms-dep-chip[data-id="SNIP-102"] .ms-dep-x'), ownChips('pred').join(','));
    ck('pick: the Add field is cleared and the list closed', $('ms-dep-add-pred').value===''&&$('ms-dep-suggest').hidden, '');
    ck('pick: the card is dirty (save enabled)', $('ms-save-actions').getAttribute('aria-disabled')==='false', '');
    ck('pick: nothing stored before Save', !umsRecord(A).pred&&lst(DEP_DATA['SNIP-102'].succ).indexOf(A)<0, String(umsRecord(A).pred));
    ck('suggest: an ID already linked is not offered again', (await typeAdd('pred','SNIP-102'), sugIds().indexOf('SNIP-102')<0), sugIds().join(','));
    // Escape closes only the list.
    await typeAdd('succ','SNIP-12');
    $('ms-dep-add-succ').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})); await settle();
    ck('Escape: closes the list, not the card', $('ms-dep-suggest').hidden&&!dlg().hidden, '');
    // Successor by Enter on a full ID.
    await enterAdd('succ','SNIP-126');
    ck('Enter: SNIP-126 added as a successor', ownChips('succ').join(',')==='SNIP-126', ownChips('succ').join(','));
    ck('count line: 1 pred, 1 succ', /^1 pred . 1 succ$/.test($('ms-dep-count').textContent), $('ms-dep-count').textContent);
    const n0=msEntries(A).length;
    await saveClose();
    ck('save: the card closed', dlg().hidden, '');
    const recA=umsRecord(A);
    ck('save: the record holds the links (rec.pred / rec.succ)', recA.pred==='SNIP-102'&&recA.succ==='SNIP-126', recA.pred+' | '+recA.succ);
    const eA=msEntries(A).slice(-1)[0];
    ck('save: one entry with changes.pred and changes.succ', msEntries(A).length===n0+1&&eA&&eA.changes.pred&&eA.changes.pred.from===''&&eA.changes.pred.to==='SNIP-102'&&
       eA.changes.succ&&eA.changes.succ.to==='SNIP-126', JSON.stringify(eA&&eA.changes));
    ck('save: link changes project into no override store', !(A in MS_FIELD_OVERRIDE), JSON.stringify(MS_FIELD_OVERRIDE[A]||null));
    ck('effective: DEP_DATA[A] lists both', DEP_DATA[A]&&lst(DEP_DATA[A].pred).join()==='SNIP-102'&&lst(DEP_DATA[A].succ).join()==='SNIP-126', JSON.stringify(DEP_DATA[A]));
    ck('effective: SNIP-102 gains A as a successor, after its own', DEP_DATA['SNIP-102'].succ===(S102.succ?S102.succ+',':'')+A&&DEP_DATA['SNIP-102'].pred===S102.pred, DEP_DATA['SNIP-102'].succ);
    ck('effective: SNIP-126 gains A as a predecessor, after its own', DEP_DATA['SNIP-126'].pred===(S126.pred?S126.pred+',':'')+A&&DEP_DATA['SNIP-126'].succ===S126.succ, DEP_DATA['SNIP-126'].pred);
    ck('pristine: DEP_DATA_SCHEDULE untouched', canon(strip(DEP_DATA_SCHEDULE))===R.notes.literalStrip0&&!JSON.stringify(DEP_DATA_SCHEDULE).includes('USR-'), '');
    ck('pristine: DEP_DATA minus user links equals the schedule', canon(strip(DEP_DATA))===R.notes.literalStrip0, '');
    ck('zero filter: the user milestone now has deps', msHasNoDeps(A)===false, '');

    // ===== 3. Reopen and the other side =====
    await open(A);
    ck('reopen: chips present, own, with crosses', ownChips('pred').join()==='SNIP-102'&&ownChips('succ').join()==='SNIP-126'&&
       $('ms-dep-lists').querySelectorAll('.ms-dep-x').length===2, ownChips('pred')+'|'+ownChips('succ'));
    ck('reopen: clean', $('ms-save-actions').getAttribute('aria-disabled')==='true', '');
    const hist=$('ms-history').textContent;
    ck('history: the change is listed in words', /Predecessors/.test(hist)&&/Successors/.test(hist)&&/SNIP-102/.test(hist)&&/SNIP-126/.test(hist)&&!/\bpred\b/.test(hist), hist.slice(0,200));
    ck('history: an empty side reads "none"', /none/.test(hist), '');
    await open('SNIP-102');
    ck('SNIP-102 card: lists A among its successors', chips('succ').indexOf(A)>=0, chips('succ').join(','));
    ck('SNIP-102 card: read only (no crosses, no Add field)', $('ms-dep-lists').querySelectorAll('.ms-dep-x').length===0&&$('ms-dep-add-pred').hidden&&$('ms-dep-add-succ').hidden, '');
    ck('SNIP-102 card: its schedule successors still listed', lst(S102.succ).every(x=>chips('succ').indexOf(x)>=0), '');
    const sf=$('ms-float-val'), S102m=findMilestoneBySnip('SNIP-102');
    ck('schedule float: read only', sf.readOnly===true, '');
    await open('SNIP-126');
    ck('SNIP-126 card: lists A among its predecessors', chips('pred').indexOf(A)>=0, chips('pred').join(','));
    ck('SNIP-126 card: count line includes A', $('ms-dep-count').textContent.indexOf((lst(S126.pred).length+1)+' pred')===0, $('ms-dep-count').textContent);
    discardMsDialog(); await settle();

    // ===== 4. Lines through drawDepLines(), both directions =====
    allFlagsOff();
    ck('lines: none with every flag off', lines().length===0, lines().length);
    await open(A);
    $('ms-toggle-pred').click(); $('ms-toggle-succ').click(); await settle();
    discardMsDialog(); await settle();
    ck('lines: user card toggles draw exactly two lines', lines().length===2, lines().length);
    ck('lines: SNIP-102 -> A', hasLine('SNIP-102',A), JSON.stringify(lines()));
    ck('lines: A -> SNIP-126', hasLine(A,'SNIP-126'), JSON.stringify(markerCenter(A)));
    allFlagsOff();
    depFlags('SNIP-102').succ=true; drawDepLines();
    ck('lines: from the schedule side, SNIP-102 succ includes the line to A', hasLine('SNIP-102',A), lines().length);
    allFlagsOff();
    depFlags('SNIP-126').pred=true; drawDepLines();
    ck('lines: from the schedule side, SNIP-126 pred includes the line from A', hasLine(A,'SNIP-126'), lines().length);
    allFlagsOff();

    // ===== 5. Counts on the markers =====
    if(!$('toggle-counts').checked){ $('toggle-counts').click(); }
    await gap(); await settle();
    const cnt=(id,k)=>{ const e=wrapOf(id)&&wrapOf(id).querySelector('.ms-count.'+k); return e?e.textContent:''; };
    ck('counts: A shows 1 pred and 1 succ', cnt(A,'pred')==='1'&&cnt(A,'succ')==='1', cnt(A,'pred')+'/'+cnt(A,'succ'));
    ck('counts: SNIP-102 succ includes A', cnt('SNIP-102','succ')===String(lst(S102.succ).length+1), cnt('SNIP-102','succ'));
    ck('counts: SNIP-126 pred includes A', cnt('SNIP-126','pred')===String(lst(S126.pred).length+1), cnt('SNIP-126','pred'));
    // Zero-count filter: only-zero hides the user row now it has deps.
    setZeroFilter('only-zero'); await settle();
    const rowA=document.querySelector('#tbody tr[data-ref="'+CSS.escape(umsRecord(A).ref)+'"]');
    ck('zero filter: only-zero hides the user milestone row', rowA&&getComputedStyle(rowA).display==='none', rowA?getComputedStyle(rowA).display:'no row');
    setZeroFilter('all'); await settle();

    // ===== 6. Float =====
    const Am=findMilestoneBySnip(A);
    const tipA=wrapOf(A).getAttribute('data-tip')||'';
    ck('user tooltip: no float', !/Float/i.test(tipA), tipA.split('\n')[3]||'');
    const was=Am.floatD; Am.floatD=12;
    ck('user tooltip: no float even with a float on the record', !/Float/.test(buildMsTip(Am,0,false)), '');
    let threw=null, fm=null;
    try{ fm=[msMatchesFloat(Am,{op:'le',days:100}),msMatchesFloat(Am,{op:'ge',days:0}),
            rowMatchesCritical(document.querySelector('#tbody tr[data-ref="'+CSS.escape(Am.ref)+'"]'),{op:'le',days:100})]; }catch(e){ threw=e.message; }
    ck('float filter: a user milestone never matches, and nothing throws', !threw&&fm.every(x=>x===false), threw||JSON.stringify(fm));
    Am.floatD=was;
    await open(A);
    ck('user card: still "-" with the record float set back', $('ms-float-val').value==='', '');
    discardMsDialog(); await settle();
    // A schedule milestone with a float, not done.
    const SF=MILESTONES.find(m=>!isUserMs(m)&&m.floatD!=null&&!isNaN(m.floatD)&&effectiveState(m)!=='DONE'&&effectiveState(m)!=='DONEUSER'&&wrapOf(msId(m)));
    ck('sample: a schedule milestone with float on the board', !!SF, SF?msId(SF):'none');
    const SFid=msId(SF), SFkey=msKeyFor(SF), SFfloat=SF.floatD;
    await open(SFid);
    ck('schedule float: shows the schedule value', $('ms-float-val').value===String(Math.round(SFfloat)), $('ms-float-val').value+' vs '+SFfloat);
    ck('schedule float: read only', $('ms-float-val').readOnly===true&&$('ms-float-val').getAttribute('readonly')!==null, '');
    // A person cannot type into it; a script that does is not a request either.
    $('ms-float-val').value='99'; $('ms-float-val').dispatchEvent(new Event('input',{bubbles:true}));
    ck('schedule float: no input handler (stays clean)', $('ms-save-actions').getAttribute('aria-disabled')==='true', '');
    $('ms-title').value=$('ms-title').value+' x'; $('ms-title').dispatchEvent(new Event('input',{bubbles:true}));
    const nS=msEntries(SFkey).length;
    onMsSaveClick(true); await gap(); await settle();
    const eS=msEntries(SFkey).slice(-1)[0];
    ck('schedule float: a save never carries floatD', msEntries(SFkey).length===nS+1&&eS&&!('floatD' in eS.changes)&&!!eS.changes.actName, JSON.stringify(eS&&eS.changes));
    // Legacy float override, seeded through the store.
    SRETEntries.append(ENTRIES,{target:{kind:'ms',key:SFkey},changes:{floatD:{from:SFfloat,to:SFfloat+50}},origin:'mount:legacy.json',status:'note'},entryCtx());
    projectEntryStores(); scheduleRerender(true); await gap(); await settle();
    const SF2=findMilestoneBySnip(SFid);
    ck('legacy float override: kept in the entries', ENTRIES.some(e=>e.target.key===SFkey&&e.changes.floatD&&e.changes.floatD.to===SFfloat+50), '');
    ck('legacy float override: not projected to MS_FIELD_OVERRIDE', !(MS_FIELD_OVERRIDE[SFkey]&&'floatD' in MS_FIELD_OVERRIDE[SFkey]), JSON.stringify(MS_FIELD_OVERRIDE[SFkey]||null));
    ck('legacy float override: the board keeps the schedule float', SF2.floatD===SFfloat, SF2.floatD+' vs '+SFfloat);
    ck('legacy float override: the tooltip shows the schedule float', (wrapOf(SFid).getAttribute('data-tip')||'').indexOf('Float: '+SFfloat+'d')>=0, '');
    // And a legacy store write (an older file's msFieldOverrides) migrates without it.
    const mig=SRETEntries.migrateLegacy({milestoneFieldOverrides:{[SFkey]:{floatD:SFfloat+7}},reportDate:'2026-10-01'},{now:Date.now()});
    ck('legacy file: a float-only field override migrates to nothing', mig.length===0, JSON.stringify(mig));
    await open(SFid);
    ck('legacy float override: the card shows the schedule float', $('ms-float-val').value===String(Math.round(SFfloat)), $('ms-float-val').value);
    ck('legacy float override: no edited mark on float', $('ms-mark-floatD').hidden, '');
    discardMsDialog(); await settle();
    ck('MS_EDITABLE_FIELDS: no floatD', MS_EDITABLE_FIELDS.indexOf('floatD')<0, MS_EDITABLE_FIELDS.join(','));

    // ===== 7. Remove with the cross =====
    await open(A);
    const x=$('ms-dep-pred-chips').querySelector('.ms-dep-chip[data-id="SNIP-102"] .ms-dep-x');
    x.click(); await settle();
    ck('remove: the cross click leaves the card open', !dlg().hidden, '');
    ck('remove: the chip is gone, card dirty', chips('pred').indexOf('SNIP-102')<0&&$('ms-save-actions').getAttribute('aria-disabled')==='false', chips('pred').join(','));
    // Out of the store's 10-minute coalescing window, so the removal is its
    // own entry. (Inside the window it folds into the add, and a link added
    // and removed again leaves nothing to record: the store's rule for every
    // card field.) The entry's clock is moved back; nothing else is touched.
    msEntries(A).forEach(function(e){ const t=new Date(Date.now()-20*60000).toISOString(); e.at=t; e.updatedAt=t; });
    const nR=msEntries(A).length;
    await saveClose();
    ck('remove: record pred empty, succ kept', umsRecord(A).pred===''&&umsRecord(A).succ==='SNIP-126', JSON.stringify([umsRecord(A).pred,umsRecord(A).succ]));
    const eR=msEntries(A).slice(-1)[0];
    ck('remove: recorded as its own history entry', msEntries(A).length===nR+1&&eR&&eR.changes.pred&&eR.changes.pred.from==='SNIP-102'&&eR.changes.pred.to===''&&!('succ' in eR.changes), JSON.stringify(eR&&eR.changes)+' n='+(msEntries(A).length-nR));
    await open(A);
    ck('remove: history reads SNIP-102 to none', /Predecessors\s*SNIP-102\s*\u2192\s*none/.test($('ms-history').textContent), $('ms-history').textContent.slice(0,160));
    discardMsDialog(); await settle();
    ck('remove: SNIP-102 is back to its schedule links', canon(DEP_DATA['SNIP-102'])===canon(S102), JSON.stringify(DEP_DATA['SNIP-102']));
    ck('remove: DEP_DATA[A] has no predecessor', lst(DEP_DATA[A].pred).length===0, JSON.stringify(DEP_DATA[A]));
    await open('SNIP-102');
    ck('remove: gone from SNIP-102\'s card', chips('succ').indexOf(A)<0, chips('succ').join(','));
    discardMsDialog(); await settle();
    depFlags('SNIP-102').succ=true; depFlags(A).pred=true; drawDepLines();
    ck('remove: no line between SNIP-102 and A', !hasLine('SNIP-102',A), '');
    allFlagsOff();

    // ===== 8. Discard keeps nothing; a click away saves =====
    const recBefore=JSON.stringify(umsRecord(A)), nD=ENTRIES.length, ddBefore=canon(DEP_DATA);
    await open(A);
    await typeAdd('pred','SNIP-104'); await pick('SNIP-104');
    ck('discard: the link was pending', ownChips('pred').indexOf('SNIP-104')>=0, '');
    document.querySelector('#ms-dialog .ms-close').click(); await gap(); await settle();
    ck('discard: card closed', dlg().hidden, '');
    ck('discard: record unchanged', JSON.stringify(umsRecord(A))===recBefore, JSON.stringify(umsRecord(A)));
    ck('discard: no entry added', ENTRIES.length===nD, ENTRIES.length-nD);
    ck('discard: DEP_DATA unchanged', canon(DEP_DATA)===ddBefore, '');
    await open(A);
    ck('discard: reopen shows no SNIP-104', chips('pred').indexOf('SNIP-104')<0, chips('pred').join(','));
    await typeAdd('pred','SNIP-104'); await pick('SNIP-104');
    document.body.dispatchEvent(new MouseEvent('click',{bubbles:true})); await gap(); await settle();
    ck('click away: card closed and the link saved', dlg().hidden&&umsRecord(A).pred==='SNIP-104'&&lst(DEP_DATA['SNIP-104'].succ).indexOf(A)>=0, umsRecord(A).pred);
    await open(A);
    $('ms-dep-pred-chips').querySelector('.ms-dep-chip[data-id="SNIP-104"] .ms-dep-x').click(); await settle();
    await saveClose();
    ck('click away: link removed again', umsRecord(A).pred==='', umsRecord(A).pred);

    // ===== 9. N=3: A -> B -> C -> SNIP-126 =====
    const B=await addUser('P72 user B'), C=await addUser('P72 user C');
    R.notes.B=B; R.notes.C=C;
    await open(B);
    await typeAdd('pred',A.slice(-3)); await pick(A);
    await typeAdd('succ',C); await pick(C);
    await saveClose();
    await open(C);
    ck('N=3: C shows B as an inbound predecessor without a cross', chips('pred').indexOf(B)>=0&&ownChips('pred').indexOf(B)<0, chips('pred').join(','));
    await enterAdd('succ','SNIP-126');
    await saveClose();
    ck('N=3: records', umsRecord(B).pred===A&&umsRecord(B).succ===C&&umsRecord(C).succ==='SNIP-126'&&!umsRecord(C).pred, JSON.stringify([umsRecord(B).pred,umsRecord(B).succ,umsRecord(C).pred,umsRecord(C).succ]));
    ck('N=3: effective A', lst(DEP_DATA[A].succ).join()==='SNIP-126,'+B, JSON.stringify(DEP_DATA[A]));
    ck('N=3: effective B', lst(DEP_DATA[B].pred).join()===A&&lst(DEP_DATA[B].succ).join()===C, JSON.stringify(DEP_DATA[B]));
    ck('N=3: effective C', lst(DEP_DATA[C].pred).join()===B&&lst(DEP_DATA[C].succ).join()==='SNIP-126', JSON.stringify(DEP_DATA[C]));
    ck('N=3: SNIP-126 lists A and C after its own predecessors', DEP_DATA['SNIP-126'].pred===(S126.pred?S126.pred+',':'')+A+','+C, DEP_DATA['SNIP-126'].pred);
    await open(A);
    ck('N=3: A card shows B (inbound, no cross) and SNIP-126 (own)', chips('succ').join()==='SNIP-126,'+B&&ownChips('succ').join()==='SNIP-126', chips('succ').join(','));
    await open('SNIP-126');
    ck('N=3: SNIP-126 card lists A and C', chips('pred').indexOf(A)>=0&&chips('pred').indexOf(C)>=0, chips('pred').join(','));
    discardMsDialog(); await settle();
    [A,B,C].forEach(id=>{ depFlags(id).succ=true; }); drawDepLines();
    ck('N=3: four lines from the three successor toggles', lines().length===4, lines().length);
    ck('N=3: A -> SNIP-126, A -> B, B -> C, C -> SNIP-126 all drawn', hasLine(A,'SNIP-126')&&hasLine(A,B)&&hasLine(B,C)&&hasLine(C,'SNIP-126'), '');
    allFlagsOff();
    const cnt2=(id,k)=>{ const e=wrapOf(id)&&wrapOf(id).querySelector('.ms-count.'+k); return e?e.textContent:''; };
    ck('N=3: counts on B', cnt2(B,'pred')==='1'&&cnt2(B,'succ')==='1', cnt2(B,'pred')+'/'+cnt2(B,'succ'));
    ck('N=3: DEP_DATA minus user links still equals the schedule', canon(strip(DEP_DATA))===R.notes.literalStrip0, '');
    // Hidden user milestones take their links with them.
    USER_MS_ENABLED=false; scheduleRerender(true); await gap(); await settle();
    ck('hidden: user links leave DEP_DATA', canon(DEP_DATA)===canon(DEP_DATA_SCHEDULE), '');
    USER_MS_ENABLED=true; scheduleRerender(true); await gap(); await settle();
    ck('shown again: links back', lst(DEP_DATA['SNIP-126'].pred).indexOf(C)>=0, '');

    R.notes.stripEnd=canon(strip(DEP_DATA));
    R.notes.userMs=USER_MILESTONES.map(r=>({id:r.id,pred:r.pred||'',succ:r.succ||''}));
    R.notes.effective={A:DEP_DATA[A],B:DEP_DATA[B],C:DEP_DATA[C],S126:DEP_DATA['SNIP-126']};
    if(window.__P72_CAPTURE__){
      const CAP={}; let capName=null;
      URL.createObjectURL=function(blob){ CAP[capName]=blob; return 'blob:captured'; };
      HTMLAnchorElement.prototype.click=function(){};
      capName='model'; exportModel();
      capName='published'; publishDashboard();
      R.modelText=await CAP.model.text();
      R.publishedText=await CAP.published.text();
    }
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.message||err)});
    R.err=String(err&&err.stack||err);
    emit();
  }
})();
"""

# Opens a copy (published file, or a clean app with the model to import) and
# reads the links back.
REOPEN = r"""
(async function(){
""" + COMMON + r"""
  try{
    await settle(); await settle();
    const E=JSON.parse($('p72-expect').textContent);
    const modelEl=$('p72-model');
    if(modelEl){
      const P=JSON.parse(modelEl.textContent);
      ck('import: clean app starts with no user milestones', USER_MILESTONES.length===0, USER_MILESTONES.length);
      ANNOT_CATEGORIES.forEach(function(c){ c.apply(P); });
      if(typeof projectEntryStores==='function') projectEntryStores();
      scheduleRerender(true); await gap(); await settle();
    }
    const got=USER_MILESTONES.map(r=>({id:r.id,pred:r.pred||'',succ:r.succ||''}));
    ck('records: pred/succ survive', JSON.stringify(got)===JSON.stringify(E.userMs), JSON.stringify(got));
    ck('effective: the same links rebuilt', canon({A:DEP_DATA[E.A],B:DEP_DATA[E.B],C:DEP_DATA[E.C],S126:DEP_DATA['SNIP-126']})===canon(E.effective), JSON.stringify(DEP_DATA[E.A]));
    ck('pristine: DEP_DATA_SCHEDULE carries no user link', !JSON.stringify(DEP_DATA_SCHEDULE).includes('USR-'), '');
    R.notes.strip=canon(strip(DEP_DATA));
    R.notes.sched=canon(DEP_DATA_SCHEDULE);
    await open('SNIP-126');
    ck('card: SNIP-126 lists A and C', chips('pred').indexOf(E.A)>=0&&chips('pred').indexOf(E.C)>=0, chips('pred').join(','));
    await open(E.B);
    ck('card: B shows its own links with crosses', ownChips('pred').join()===E.A&&ownChips('succ').join()===E.C, ownChips('pred')+'|'+ownChips('succ'));
    discardMsDialog(); await settle();
    [E.A,E.B,E.C].forEach(id=>{ depFlags(id).succ=true; }); drawDepLines();
    ck('published layer: the arrow markers and the line group survive', !!$('dep-lines-g')&&!!$('arrow-pred')&&!!$('arrow-succ')&&!!$('arrow-muted'), '');
    ck('lines: the chain draws', hasLine(E.A,E.B)&&hasLine(E.B,E.C)&&hasLine(E.C,'SNIP-126'), lines().length);
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.message||err)});
    R.err=String(err&&err.stack||err);
    emit();
  }
})();
"""


def run_page(page, probe, width, height, extra=""):
    i = page.rindex("</body>")
    out = page[:i] + extra + "<script>\n" + probe + "\n</script>\n" + page[i:]
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p72.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--user-data-dir={td}/prof", f"--window-size={width},{height}",
             "--virtual-time-budget=120000", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=900,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def literal(src):
    m = re.search(r"^const DEP_DATA=(\{.*?\});$", src, re.M)
    return m.group(0) if m else None


def canon(v):
    if not isinstance(v, dict):
        return json.dumps(v, separators=(",", ":"))
    return "{" + ",".join(json.dumps(k) + ":" + canon(v[k]) for k in sorted(v)) + "}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    src = pathlib.Path(args.html).read_text(encoding="utf-8", errors="replace")
    checks = []
    ck = lambda n, p, d="": checks.append((n, bool(p), str(d)))

    lit = literal(src)
    ck("source: one schedule DEP_DATA literal", lit is not None and src.count("const DEP_DATA=") == 1)
    lit_obj = json.loads(lit[len("const DEP_DATA="):-1])
    lit_canon = canon(lit_obj)
    ck("source: exactly one </body>", src.count("</body>") == 1, src.count("</body>"))
    ck("source: exactly one version literal", len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1)
    ck("source: the Add fields use onmousedown + preventDefault", "onmousedown=\"event.preventDefault();pickMsDepSuggestion(this)\"" in src)
    ck("source: MS_EDITABLE_FIELDS has no floatD",
       re.search(r"const MS_EDITABLE_FIELDS=\[[^\]]*\]", src) and "floatD" not in re.search(r"const MS_EDITABLE_FIELDS=\[[^\]]*\]", src).group(0))
    block = src[src.index('<div id="ms-dialog"'):src.index('<div id="print-filter-note"')]
    ck("source: no em dash in the card markup", "—" not in block and "&mdash;" not in block)

    stage1 = None
    for (w, h) in VIEWPORTS:
        cap = (w == 1440)
        extra = "<script>window.__P72_CAPTURE__=true;</script>\n" if cap else ""
        R = run_page(src, PROBE, w, h, extra)
        print(f"=== stage 1 {w}x{h} ===  user milestones {R.get('notes', {}).get('A')}, {R.get('notes', {}).get('B')}, {R.get('notes', {}).get('C')}")
        if R.get("err"):
            print(R["err"])
        for c in R["checks"]:
            ck(f"[{w}x{h}] " + c["name"], c["pass"], c["detail"])
        n = R.get("notes", {})
        ck(f"[{w}x{h}] strip before == source literal", n.get("literalStrip0") == lit_canon)
        ck(f"[{w}x{h}] strip after edits == source literal", n.get("stripEnd") == lit_canon)
        if cap:
            stage1 = R

    if stage1 and stage1.get("publishedText"):
        pub = stage1["publishedText"]
        model = json.loads(stage1["modelText"])
        n = stage1["notes"]
        expect = json.dumps({"A": n["A"], "B": n["B"], "C": n["C"], "userMs": n["userMs"], "effective": n["effective"]})
        ck("publish: the published DEP_DATA literal is byte identical to the source", literal(pub) == lit)
        ck("publish: the published file carries no user link in its schedule literal", "USR-" not in (literal(pub) or ""))
        um = {r["id"]: r for r in model.get("userMilestones", [])}
        ck("model export: userMilestones carry pred/succ",
           um.get(n["B"], {}).get("pred") == n["A"] and um.get(n["B"], {}).get("succ") == n["C"]
           and um.get(n["C"], {}).get("succ") == "SNIP-126", json.dumps([um.get(n["B"]), um.get(n["C"])])[:200])
        exp_tag = "<script type=\"application/json\" id=\"p72-expect\">" + expect.replace("<", "\\u003c") + "</script>\n"
        R2 = run_page(pub, REOPEN, 1440, 900, exp_tag)
        for c in R2["checks"]:
            ck("[published copy] " + c["name"], c["pass"], c["detail"])
        ck("[published copy] strip == source literal", R2["notes"].get("strip") == lit_canon)
        ck("[published copy] DEP_DATA_SCHEDULE == source literal", R2["notes"].get("sched") == lit_canon)
        model_tag = "<script type=\"application/json\" id=\"p72-model\">" + stage1["modelText"].replace("<", "\\u003c") + "</script>\n"
        R3 = run_page(src, REOPEN, 1440, 900, exp_tag + model_tag)
        for c in R3["checks"]:
            ck("[model import] " + c["name"], c["pass"], c["detail"])
        ck("[model import] strip == source literal", R3["notes"].get("strip") == lit_canon)
        ck("[model import] DEP_DATA_SCHEDULE == source literal", R3["notes"].get("sched") == lit_canon)
    else:
        ck("publish/model capture produced output", False, "nothing captured")

    fails = 0
    print()
    for name, ok, detail in checks:
        fails += not ok
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
