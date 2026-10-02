#!/usr/bin/env python3
"""
p78_fields_check: Discipline, Supervisor and Engineer (P78, Matt 2026-10-02).

Drives the real app in headless Chrome at 1440 and 390, with real clicks
(pointer and mouse sequences dispatched on the elements themselves) and
real key presses:

  1. Import: the reference export (tools/import_check.py build_aoa) with
     three columns added (Discipline, Superintendent, Responsible Engineer),
     pasted into the Import tab of the app as it ships (sret:no-fixture).
     The three columns auto-map (an alias each), the mapper shows them, a
     click on Import builds the board, and every activity's three values
     land on its milestone (blank stays absent).
  2. Card layout: the 2x2 grid (WBS/Area | Discipline, Supervisor | Engineer)
     sits directly under the title line and above the Start / Duration /
     Finish row, measured on the elements themselves: two columns that
     align, two rows, cells of one height.
  3. Display: a populated value is the name only (plain, no fill, no
     border); a blank one shows the field name as its placeholder, muted,
     in a subtle box; WBS/Area is read only text.
  4. Suggestions, N=3 milestones (two schedule milestones and one user
     milestone): focus lists the names already used, deduplicated without
     regard to case and most used first (at most 8), under the hint "Pick an
     existing name or type a new one"; typing narrows; a mouse pick (focus
     stays, card stays open) and a keyboard pick (ArrowDown, Enter) both
     work; Esc closes the list before the card; free text saves.
  5. History and edits: each save is one entry with the right change
     (from null for a field the schedule did not carry), the history row
     reads "Supervisor none -> J. Smith", the edited mark shows the
     schedule's value, the imported schedule value is untouched (annotOwn),
     and clearing goes back to the schedule's value.
  6. Grid: the schedule milestones view has the three columns, editable; an
     edit there is an entry (origin grid) projected as an override; the user
     milestones view has them too and writes the record; the user-defined
     schedule export carries them as the last three columns.
  7. (1440 only) Persistence: the captured published file opens in a fresh
     profile with the schedule values, the overrides and the user record;
     the model export carries them, and mounting it into a fresh app (the
     test fixture) brings the overrides and the user milestone back.

    python3 tools/p78_fields_check.py [--html FILE]
Exit 1 if any check fails.
"""

import argparse
import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from import_check import build_aoa, find_chrome  # noqa: E402

XLSX = ROOT / "data" / "schedules" / "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"
OUT_RE = re.compile(r'<pre id="p78-out">(.*?)</pre>', re.S)
VIEWPORTS = [(1440, 900), (390, 844)]
OPT_OUT = "<!-- sret:no-fixture: P78 imports a schedule carrying the three fields -->"
HINT = "Pick an existing name or type a new one"

# Test values, cycled over the activity rows. Different lengths, so the three
# columns do not move together, and two spellings of one supervisor, so the
# suggestions have something to deduplicate.
DISC = ["Mining", "Process", "Geology", "", "Mining"]
SUP = ["J. Smith", "J. Smith", "J. Smith", "A. Brown", "a. brown", "K. Lee", "", "A. Brown"]
ENG = ["P. Patel", "P. Patel", "R. Chen", "", "M. Owusu", "R. Chen", "P. Patel"]


def build_sheet():
    aoa = build_aoa(XLSX)
    head = [str(h) for h in aoa[0]] + ["Discipline", "Superintendent", "Responsible Engineer"]
    rows, expect, i = [head], {}, 0
    for r in aoa[1:]:
        r = list(r) + [""] * (len(aoa[0]) - len(r))
        rid, name = str(r[0] or "").strip(), str(r[1] or "").strip()
        if rid and name:
            d, s, e = DISC[i % len(DISC)], SUP[i % len(SUP)], ENG[i % len(ENG)]
            expect[rid] = {"discipline": d, "supervisor": s, "engineer": e}
            i += 1
            rows.append(r + [d, s, e])
        else:
            rows.append(r + ["", "", ""])
    return rows, expect


def to_tsv(aoa):
    """As tools/p75_import_check.py: the header flattened, body cells keep
    their leading spaces (the WBS depth)."""
    def cell(v, head):
        s = "" if v is None else str(v)
        return re.sub(r"\s+", " ", s).strip() if head else re.sub(r"[\t\r\n]+", " ", s)
    return "\n".join("\t".join(cell(v, i == 0) for v in row) for i, row in enumerate(aoa)) + "\n"


EARLY = r"""<script>
window.__errs=[];
addEventListener('error',function(e){ if(/^ResizeObserver loop/.test(e.message||'')) return; __errs.push('error: '+e.message+' @'+e.lineno); });
(function(){ var o=console.error; console.error=function(){ __errs.push('console.error: '+Array.prototype.join.call(arguments,' ')); return o.apply(console,arguments); }; })();
</script>"""

PROBE = r"""<script>
(async function(){
  const R={checks:[],notes:{}};
  const PUBLISH=__PUBLISH__, TSV=__TSV__, EXPECT=__EXPECT__, HINT=__HINT__;
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d).slice(0,400)}); }
  function emit(){ R.errs=(window.__errs||[]).slice(); const o=document.createElement('pre'); o.id='p78-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
  const settle=(ms)=>new Promise(r=>setTimeout(r,ms||240));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog'), sug=()=>$('ms-pf-suggest');
  const rc=el=>el.getBoundingClientRect();
  const txt=el=>el?el.textContent.replace(/\s+/g,' ').trim():'';
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const realClick=function(el){
    const r=rc(el), o={bubbles:true,cancelable:true,clientX:r.left+r.width/2,clientY:r.top+r.height/2,button:0};
    try{ el.dispatchEvent(new PointerEvent('pointerdown',Object.assign({pointerType:'mouse',isPrimary:true},o))); }catch(x){}
    const md=new MouseEvent('mousedown',o); el.dispatchEvent(md);
    // A real mousedown focuses the field it lands on unless it was prevented.
    if(!md.defaultPrevented&&el.focus&&/^(INPUT|TEXTAREA|BUTTON)$/.test(el.tagName)) el.focus();
    try{ el.dispatchEvent(new PointerEvent('pointerup',Object.assign({pointerType:'mouse',isPrimary:true},o))); }catch(x){}
    el.dispatchEvent(new MouseEvent('mouseup',o));
    el.dispatchEvent(new MouseEvent('click',o));
    return md;
  };
  const key=(el,k)=>{ const e=new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true}); el.dispatchEvent(e); return e; };
  // Typing: the value grows a character at a time, each with its input event.
  const type=async function(el,text,clear){
    if(clear){ el.value=''; el.dispatchEvent(new Event('input',{bubbles:true})); }
    for(const ch of text){ el.value+=ch; el.dispatchEvent(new Event('input',{bubbles:true})); }
    await settle(60);
  };
  const open=async function(id){
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    await settle(420);
    const w=wrapOf(id); if(!w) throw new Error('no marker for '+id);
    w.scrollIntoView({block:'center',inline:'center'}); await settle(60);
    realClick(w); await settle();
    if(dlg().hidden) throw new Error('card did not open for '+id);
  };
  const items=()=>Array.from(sug().querySelectorAll('.id-suggest-item'));
  const names=()=>items().map(i=>i.getAttribute('data-name'));
  const msEntries=k=>ENTRIES.filter(e=>e.target.kind==='ms'&&e.target.key===k);
  const lastCh=(k,f)=>{ const l=msEntries(k).filter(e=>e.changes&&e.changes[f]); return l.length?l[l.length-1]:null; };
  // The expected suggestion order, worked out here from the board on its own:
  // one value per milestone (an override, else the schedule's), names that
  // differ only in case together, most used first, then by name.
  const expectOrder=function(f){
    const uses={}, spell={}, seen={};
    const put=(v,n)=>{ v=String(v==null?'':v).trim(); if(!v) return; const k=v.toLowerCase(); uses[k]=(uses[k]||0)+n; (spell[k]=spell[k]||{})[v]=((spell[k]||{})[v]||0)+1; };
    MILESTONES.concat(USER_MILESTONES).forEach(m=>{ const k=msKeyFor(m); if(seen[k]) return; seen[k]=1;
      const b=m._msBase||{}, own=(f in b)?b[f]:m[f], ov=MS_FIELD_OVERRIDE[k], has=!!(ov&&(f in ov));
      put(own,has?0:1); if(has) put(ov[f],1); });
    return Object.keys(uses).map(k=>({n:Object.keys(spell[k]).sort((a,b)=>spell[k][b]-spell[k][a]||a.localeCompare(b))[0],u:uses[k]}))
      .sort((a,b)=>b.u-a.u||a.n.localeCompare(b.n)).map(o=>o.n);
  };
  try{
    const st=document.createElement('style'); st.textContent='*{transition:none!important;animation:none!important}'; document.head.appendChild(st);
    await settle(600);
    ck('boot: the empty app, nothing seeded', typeof window.__SRET_FIXTURE__==='undefined'&&TASKS.length===0, TASKS.length);

    // ===== 1. Import =====
    setSettingsTab('import'); toggleSettingsDrawer(true); await settle();
    togglePaste(); await settle(60);
    $('paste-box').value=TSV;
    const parseBtn=Array.from($('paste-wrap').querySelectorAll('button')).find(b=>/Parse pasted data/.test(b.textContent));
    realClick(parseBtn); await settle();
    const H=(LAST_PARSE&&LAST_PARSE.headers)||[];
    const iD=H.indexOf('Discipline'), iS=H.indexOf('Superintendent'), iE=H.indexOf('Responsible Engineer');
    ck('import: the pasted sheet parses with the three extra columns', iD>0&&iS>0&&iE>0, JSON.stringify(H));
    ck('import: Discipline auto-maps', LAST_MAP&&LAST_MAP.discipline===iD&&$('map-discipline')&&$('map-discipline').value===String(iD), LAST_MAP&&LAST_MAP.discipline);
    ck('import: Supervisor auto-maps (alias "superintendent")', LAST_MAP&&LAST_MAP.supervisor===iS&&$('map-supervisor')&&$('map-supervisor').value===String(iS), LAST_MAP&&LAST_MAP.supervisor);
    ck('import: Engineer auto-maps (alias "responsible engineer")', LAST_MAP&&LAST_MAP.engineer===iE&&$('map-engineer')&&$('map-engineer').value===String(iE), LAST_MAP&&LAST_MAP.engineer);
    const lbls=Array.from(document.querySelectorAll('#map-wrap .map-cell > span:first-child')).map(txt);
    ck('import: the mapper lists them last, optional (no required mark)', JSON.stringify(lbls.slice(-3))==='["Discipline","Supervisor","Engineer"]'&&
       !document.querySelector('#map-discipline').closest('.map-cell').querySelector('.req'), JSON.stringify(lbls));
    ck('import: the older fields keep their columns', LAST_MAP.id===0&&LAST_MAP.name===1&&LAST_MAP.finish===H.indexOf('Finish'), JSON.stringify(LAST_MAP));
    const runBtn=$('import-run-btn');
    ck('import: Ready to import, the button enabled', !!runBtn&&!runBtn.disabled, '');
    realClick(runBtn); await settle(); await settle();
    ck('import: a click builds the board (105 rows, 146 milestones)', TASKS.length===105&&MILESTONES.length===146, TASKS.length+'/'+MILESTONES.length);
    let bad=[], nVals=0;
    MILESTONES.forEach(m=>{ const id=msId(m), x=EXPECT[id]; if(!x){ bad.push('no expectation '+id); return; }
      ['discipline','supervisor','engineer'].forEach(f=>{ const want=x[f]||undefined; if(want) nVals++;
        if(m[f]!==want) bad.push(id+'.'+f+'='+m[f]+' want '+want); }); });
    ck('import: every milestone carries its activity\'s three values (blank stays absent)', !bad.length&&nVals>200, bad.slice(0,5).join('; ')+' n='+nVals);
    toggleSettingsDrawer(false); await settle();

    // ===== N=3: two schedule milestones and one user milestone =====
    const onBoard=MILESTONES.filter(m=>msId(m)&&wrapOf(msId(m)));
    const P=onBoard.find(m=>m.supervisor==='J. Smith'&&!m.engineer&&m.discipline);
    const Q=onBoard.find(m=>m!==P&&!m.supervisor&&m.engineer);
    const K=onBoard.find(m=>m!==P&&m!==Q&&m.supervisor==='K. Lee');
    ck('samples: P (supervisor J. Smith, no engineer), Q (no supervisor), K on the board', !!P&&!!Q&&!!K, [P,Q,K].map(m=>m&&msId(m)).join());
    const pid=msId(P), qid=msId(Q), kid=msId(K), pk=msKeyFor(P), qk=msKeyFor(Q), kk=msKeyFor(K);
    let fin=isoDay(WE_DATES[Math.min(NOW_COL+2,WE_DATES.length-1)]);
    const ur=addUserMilestone({name:'P78 user milestone',date:fin,type:'MS',state:'FUTURE'});
    ck('samples: a user milestone added', !ur.error&&!!ur.id, ur.error||ur.id);
    const uid=ur.id;
    scheduleRerender(true); await settle(); await settle();
    R.notes.sample=[pid,qid,kid,uid];

    // ===== 2. Card layout =====
    await open(pid);
    const people=$('ms-people'), tl=dlg().querySelector('.ms-title-line'), sch=dlg().querySelector('.ms-schedule');
    const cW=rc($('ms-pf-wbs')), cD=rc($('ms-pf-discipline')), cS=rc($('ms-pf-supervisor')), cE=rc($('ms-pf-engineer'));
    ck('layout: the grid is under the title line', rc(people).top>=rc(tl).bottom-0.5&&rc(people).top-rc(tl).bottom<=16, rc(tl).bottom+' / '+rc(people).top);
    ck('layout: and above the Start / Duration / Finish row', rc(people).bottom<=rc(sch).top+0.5, rc(people).bottom+' / '+rc(sch).top);
    ck('layout: the cells are inside the grid, in DOM order WBS, Discipline, Supervisor, Engineer',
       Array.from(people.children).map(c=>c.id).join()==='ms-pf-wbs,ms-pf-discipline,ms-pf-supervisor,ms-pf-engineer', '');
    ck('layout: row 1 is WBS/Area | Discipline (one top, side by side)', Math.abs(cW.top-cD.top)<1&&cD.left>=cW.right-0.5, [cW.top,cD.top,cW.right,cD.left].join());
    ck('layout: row 2 is Supervisor | Engineer, under row 1', Math.abs(cS.top-cE.top)<1&&cS.top>=cW.bottom-0.5&&cE.left>=cS.right-0.5, [cS.top,cE.top,cW.bottom].join());
    ck('layout: the two columns align (left edges)', Math.abs(cW.left-cS.left)<1&&Math.abs(cD.left-cE.left)<1, [cW.left,cS.left,cD.left,cE.left].join());
    const ctl=parseFloat(getComputedStyle($('ms-supervisor')).height);
    ck('layout: four cells of one height (--ctl-h)', [cW,cD,cS,cE].every(r=>Math.abs(r.height-ctl)<1), [cW,cD,cS,cE].map(r=>r.height).join()+' ctl '+ctl);
    ck('layout: the grid is inside the card (no overflow)', rc(people).right<=rc(dlg()).right+0.5&&rc(people).left>=rc(dlg()).left-0.5, '');

    // ===== 3. Display =====
    const sv=$('ms-supervisor'), en=$('ms-engineer'), di=$('ms-discipline'), wb=$('ms-wbs');
    const csS=getComputedStyle(sv), csE=getComputedStyle(en);
    ck('display: a populated supervisor is the name only', sv.value==='J. Smith'&&!sv.matches(':placeholder-shown'), sv.value);
    ck('display: plain, no fill and no border at rest', (csS.backgroundColor==='rgba(0, 0, 0, 0)'||csS.backgroundColor==='transparent')&&parseFloat(csS.borderTopWidth)===0, csS.backgroundColor+' '+csS.borderTopWidth);
    ck('display: a blank engineer shows the placeholder "Engineer"', en.value===''&&en.placeholder==='Engineer'&&en.matches(':placeholder-shown'), en.value+'|'+en.placeholder);
    ck('display: the blank field is a muted box (a fill), its placeholder in muted ink',
       csE.backgroundColor!=='rgba(0, 0, 0, 0)'&&getComputedStyle(en,'::placeholder').color===getComputedStyle(document.querySelector('.ms-sub')).color,
       csE.backgroundColor+' '+getComputedStyle(en,'::placeholder').color);
    ck('display: the discipline shows the imported value', di.value===P.discipline, di.value);
    const task=umsRowTask(P.ref);
    ck('display: WBS/Area is read only text, the row\'s band', wb.tagName==='SPAN'&&!wb.querySelector('input')&&txt(wb)===msWbsAreaText(task)&&txt(wb).length>0, txt(wb));
    ck('display: the fields are search boxes (combobox, list in the card)', ['ms-discipline','ms-supervisor','ms-engineer'].every(id=>$(id).getAttribute('role')==='combobox'&&$(id).getAttribute('aria-controls')==='ms-pf-suggest')&&dlg().contains(sug())&&sug().getAttribute('role')==='listbox', '');
    // a click on the populated name makes it editable (focus, the caret)
    realClick(sv); await settle(60);
    ck('display: a click on the name makes it editable', document.activeElement===sv&&!sv.readOnly, document.activeElement&&document.activeElement.id);

    // ===== 4. Suggestions =====
    const wantSup=expectOrder('supervisor');
    ck('suggest: on focus the list opens, under the hint', !sug().hidden&&txt(sug().querySelector('.ms-pf-hint'))===HINT&&sv.getAttribute('aria-expanded')==='true', txt(sug().querySelector('.ms-pf-hint')));
    ck('suggest: the names in use, most used first, deduplicated without case', JSON.stringify(names())===JSON.stringify(wantSup.slice(0,8)), JSON.stringify(names())+' want '+JSON.stringify(wantSup));
    ck('suggest: A. Brown and a. brown are one entry', names().filter(n=>n.toLowerCase()==='a. brown').length===1, JSON.stringify(names()));
    ck('suggest: at most 8, each an option', items().length<=8&&items().every(i=>i.getAttribute('role')==='option'), items().length);
    const sr=rc(sug()), ir=rc(sv);
    ck('suggest: the list sits under its field', sr.top>=ir.bottom-1&&sr.top-ir.bottom<12&&Math.abs(sr.left-ir.left)<12, sr.top+' '+ir.bottom);
    let ev=key(sv,'Escape'); await settle(60);
    ck('suggest: Esc closes the list, not the card', sug().hidden&&!dlg().hidden&&ev.defaultPrevented, '');
    sv.blur(); await settle(60);
    discardMsDialog(); await settle();

    // Q: a blank supervisor, typed and picked with the mouse.
    await open(qid);
    const sq=$('ms-supervisor');
    ck('Q: the blank supervisor shows its placeholder', sq.value===''&&sq.placeholder==='Supervisor', sq.value);
    realClick(sq); await settle(60);
    await type(sq,'b');
    ck('suggest: typing narrows the list (b: A. Brown only)', JSON.stringify(names())==='["A. Brown"]', JSON.stringify(names()));
    await type(sq,'smi',true);
    ck('suggest: typing "smi" lists J. Smith', JSON.stringify(names())==='["J. Smith"]', JSON.stringify(names()));
    const it=items()[0];
    const md=realClick(it); await settle(60);
    ck('suggest: a mouse pick fills the field', sq.value==='J. Smith', sq.value);
    ck('suggest: the pick keeps focus in the field (mousedown prevented)', md.defaultPrevented&&document.activeElement===sq, document.activeElement&&document.activeElement.id);
    ck('suggest: the list closes and the card stays open', sug().hidden&&!dlg().hidden, '');
    ck('Q: the card is dirty, the field tinted', msDirty()&&sq.classList.contains('ms-dirty-field'), '');
    const nE0=msEntries(qk).length;
    sq.blur(); await settle(60);
    key(document.body,'Escape'); await settle();      // Esc saves (P75)
    ck('Q: Esc saved and closed the card', dlg().hidden, '');
    const eq=lastCh(qk,'supervisor');
    ck('edit: one entry with changes.supervisor {from:null,to:"J. Smith"}', msEntries(qk).length===nE0+1&&eq&&eq.changes.supervisor.from===null&&eq.changes.supervisor.to==='J. Smith'&&eq.origin==='card', JSON.stringify(eq&&eq.changes));
    ck('edit: projected as an override', MS_FIELD_OVERRIDE[qk]&&MS_FIELD_OVERRIDE[qk].supervisor==='J. Smith', JSON.stringify(MS_FIELD_OVERRIDE[qk]));
    await settle(); await settle();
    ck('edit: the board shows it; the imported schedule value is untouched', Q.supervisor==='J. Smith'&&annotOwn(Q,'supervisor')==null&&!EXPECT[qid].supervisor, Q.supervisor+' own '+annotOwn(Q,'supervisor'));
    await open(qid);
    const hrow=Array.from(document.querySelectorAll('#ms-history .nh-row')).find(r=>txt(r.querySelector('.nh-lbl'))==='Supervisor');
    ck('history: the row reads "Supervisor none → J. Smith"', !!hrow&&txt(hrow.querySelector('.nh-from'))==='none'&&txt(hrow.querySelector('.nh-to'))==='J. Smith'&&/^Supervisor none → J\. Smith$/.test(txt(hrow)), hrow&&txt(hrow));
    const mk=$('ms-mark-supervisor');
    ck('edited mark: shown, with the schedule\'s value', !mk.hidden&&mk.title==='Previous: (none)', mk.hidden+' '+mk.title);
    ck('edited mark: not on the untouched fields', $('ms-mark-engineer').hidden&&$('ms-mark-discipline').hidden, '');
    // Clearing: the schedule had none, so the field goes back to blank.
    // Eleven minutes on: a card save inside the store's 10-minute window
    // coalesces into the entry before it (and a change reverted inside it
    // leaves nothing), so the clock is moved past it to record the clear as
    // an entry of its own, as a later session would.
    const sq2=$('ms-supervisor');
    realClick(sq2); await settle(60);
    await type(sq2,'',true);
    sq2.blur(); await settle(60);
    const realNow=Date.now; Date.now=function(){ return realNow()+11*60000; };
    try{ realClick(document.querySelector('.ms-save-actions .ms-act-primary')); await settle(); }
    finally{ Date.now=realNow; }
    const ec=lastCh(qk,'supervisor');
    ck('clear: an entry back to the schedule (to null)', ec&&ec!==eq&&ec.changes.supervisor.from==='J. Smith'&&ec.changes.supervisor.to===null, JSON.stringify(ec&&ec.changes));
    ck('clear: no override left', !(MS_FIELD_OVERRIDE[qk]&&'supervisor' in MS_FIELD_OVERRIDE[qk]), JSON.stringify(MS_FIELD_OVERRIDE[qk]));
    await settle(); await settle();
    await open(qid);
    ck('clear: the card shows the schedule\'s value again (none: the placeholder), no mark', $('ms-supervisor').value===''&&$('ms-mark-supervisor').hidden, $('ms-supervisor').value);
    const hrow2=Array.from(document.querySelectorAll('#ms-history .nh-row')).filter(r=>txt(r.querySelector('.nh-lbl'))==='Supervisor').map(txt);
    ck('history: the clear reads "Supervisor J. Smith → schedule value"', hrow2.indexOf('Supervisor J. Smith → schedule value')>=0, JSON.stringify(hrow2));
    discardMsDialog(); await settle();

    // P: an imported supervisor replaced by keyboard, then cleared back to it.
    await open(pid);
    const sp=$('ms-supervisor');
    realClick(sp); await settle(60);
    const listP=names();
    key(sp,'ArrowDown'); await settle(30);
    ck('keyboard: ArrowDown highlights the first name', items()[0].classList.contains('is-hl')&&sp.getAttribute('aria-activedescendant')==='ms-pf-opt-0', sp.getAttribute('aria-activedescendant'));
    key(sp,'ArrowDown'); await settle(30);
    ck('keyboard: ArrowDown again moves to the second', items()[1].classList.contains('is-hl')&&!items()[0].classList.contains('is-hl')&&items()[1].getAttribute('aria-selected')==='true', '');
    ev=key(sp,'Enter'); await settle(60);
    const picked=listP[1];
    ck('keyboard: Enter picks it, the list closes, the card stays', sp.value===picked&&sug().hidden&&!dlg().hidden&&ev.defaultPrevented, sp.value+' want '+picked);
    sp.blur(); await settle(60);
    // A click away saves (P75).
    realClick(document.body); await settle();
    ck('P: a click away saved and closed', dlg().hidden, '');
    const ep=lastCh(pk,'supervisor');
    ck('edit: P has changes.supervisor {from:"J. Smith",to:picked}', ep&&ep.changes.supervisor.from==='J. Smith'&&ep.changes.supervisor.to===picked, JSON.stringify(ep&&ep.changes));
    await settle(); await settle();
    ck('edit: the schedule value stays under the edit (never changed)', annotOwn(P,'supervisor')==='J. Smith'&&P.supervisor===picked, annotOwn(P,'supervisor')+' / '+P.supervisor);
    await open(pid);
    ck('edited mark: P\'s reads Previous: J. Smith', !$('ms-mark-supervisor').hidden&&$('ms-mark-supervisor').title==='Previous: J. Smith', $('ms-mark-supervisor').title);
    const sp2=$('ms-supervisor');
    realClick(sp2); await settle(60);
    await type(sp2,'',true); sp2.blur(); await settle(60);
    realClick(document.querySelector('.ms-save-actions .ms-act-icon')); await settle();
    ck('clear: saved with the card open, the field shows the schedule\'s value again', !dlg().hidden&&sp2.value==='J. Smith'&&!msDirty(), sp2.value);
    ck('clear: P\'s override is gone', !(MS_FIELD_OVERRIDE[pk]&&'supervisor' in MS_FIELD_OVERRIDE[pk]), JSON.stringify(MS_FIELD_OVERRIDE[pk]));
    // Engineer: free text by Enter with nothing highlighted.
    const ep2=$('ms-engineer');
    realClick(ep2); await settle(60);
    await type(ep2,'P');
    ck('suggest: the engineer list is its own field\'s names', names().length>0&&names().every(n=>expectOrder('engineer').indexOf(n)>=0)&&names().indexOf('J. Smith')<0, JSON.stringify(names()));
    await type(ep2,'78 Free Text Engineer');
    ev=key(ep2,'Enter'); await settle(60);
    ck('free text: Enter with nothing highlighted keeps the typed text', ep2.value==='P78 Free Text Engineer'&&sug().hidden, ep2.value);
    ep2.blur(); key(document.body,'Escape'); await settle();
    const ee=lastCh(pk,'engineer');
    ck('free text: saved as an entry (from null)', ee&&ee.changes.engineer.from===null&&ee.changes.engineer.to==='P78 Free Text Engineer', JSON.stringify(ee&&ee.changes));
    await settle(); await settle();

    // U: the user milestone, discipline by free text.
    await open(uid);
    const du=$('ms-discipline');
    ck('U: the user milestone card has the grid, all three blank', du.value===''&&$('ms-supervisor').value===''&&$('ms-engineer').value==='', '');
    realClick(du); await settle(60);
    ck('suggest: the discipline list (the imported names)', JSON.stringify(names())===JSON.stringify(expectOrder('discipline').slice(0,8)), JSON.stringify(names()));
    await type(du,'Electrical P78');
    ck('suggest: a new name matches nothing, the list closes', sug().hidden, names().join());
    du.blur(); await settle(60);
    realClick(document.querySelector('.ms-save-actions .ms-act-primary')); await settle();
    const eu=lastCh(uid,'discipline');
    ck('U: the discipline is an entry, projected as an override on the USR key', eu&&eu.changes.discipline.to==='Electrical P78'&&MS_FIELD_OVERRIDE[uid]&&MS_FIELD_OVERRIDE[uid].discipline==='Electrical P78', JSON.stringify(eu&&eu.changes));
    await settle(); await settle();
    await open(uid);
    ck('U: reopened, the card shows it with the edited mark', $('ms-discipline').value==='Electrical P78'&&!$('ms-mark-discipline').hidden, $('ms-discipline').value);
    realClick($('ms-discipline')); await settle(60);
    ck('suggest: manual values are suggested too', names().indexOf('Electrical P78')>=0, JSON.stringify(names()));
    $('ms-discipline').blur(); discardMsDialog(); await settle();

    // ===== 6. Grid =====
    openUserMsGrid(); await settle(300);
    const eng=()=>SRETGrid._engine&&SRETGrid._engine();
    const colIdx=k=>eng().grid.getColumns().findIndex(c=>c.id===k);
    const pickView=async function(id){ const tb=document.querySelector('#grid-host .sg-title-btn'); tb.click(); await settle(40);
      const iv=document.querySelector('#grid-host [data-sg="view-'+id+'"]'); if(!iv) return false; iv.click(); await settle(200); return true; };
    const editCell=async function(k,col,val){
      const E=eng(), g=E.grid, dv=E.dataView;
      g.scrollRowIntoView(dv.getIdxById(k)); g.setActiveCell(dv.getIdxById(k),colIdx(col)); g.editActiveCell();
      const ed=document.querySelector('#grid-host .sg-editor'); if(!ed) return 'no editor';
      ed.value=String(val); g.getEditorLock().commitCurrentEdit(); await settle(80);
      const r=eng().dataView.getItemById(k); return r?r[col]:undefined; };
    ck('grid: user milestones view has Discipline, Supervisor, Engineer, editable', ['discipline','supervisor','engineer'].every(c=>colIdx(c)>=0&&!!eng().grid.getColumns()[colIdx(c)].editor), eng().grid.getColumns().map(c=>c.id).join());
    ck('grid: the user row shows the card\'s discipline', eng().dataView.getItemById(uid).discipline==='Electrical P78', JSON.stringify(eng().dataView.getItemById(uid)));
    await editCell(uid,'engineer','Grid User Engineer');
    ck('grid: an edit writes the user milestone record', umsRecord(uid).engineer==='Grid User Engineer', umsRecord(uid).engineer);
    ck('grid (export): the user-defined export has the three columns last, with values',
       (function(){ const rows=userDefinedExportRows(), h=rows[0], r=rows.find(x=>x[0]===uid);
         return JSON.stringify(h.slice(-3))==='["Discipline","Supervisor","Engineer"]'&&r&&r[h.length-3]==='Electrical P78'&&r[h.length-1]==='Grid User Engineer'; })(),
       JSON.stringify(userDefinedExportRows()[0]));
    ck('grid: switched to Schedule milestones', await pickView('sched-ms'), '');
    ck('grid: Schedule milestones has the three columns, editable', ['discipline','supervisor','engineer'].every(c=>colIdx(c)>=0&&!!eng().grid.getColumns()[colIdx(c)].editor), eng().grid.getColumns().map(c=>c.id).join());
    const rk=eng().dataView.getItemById(kk);
    ck('grid: a row shows the schedule values', rk&&rk.supervisor==='K. Lee'&&rk.discipline===(K.discipline||'')&&rk.engineer===(K.engineer||''), JSON.stringify(rk));
    ck('grid: P shows the card\'s free-text engineer', eng().dataView.getItemById(pk).engineer==='P78 Free Text Engineer', eng().dataView.getItemById(pk).engineer);
    const nK=msEntries(kk).length;
    const after=await editCell(kk,'supervisor','Grid Supervisor');
    await settle(80);
    const ek=lastCh(kk,'supervisor');
    ck('grid: an edit is one entry (origin grid) with changes.supervisor', msEntries(kk).length===nK+1&&ek&&ek.origin==='grid'&&ek.changes.supervisor.from==='K. Lee'&&ek.changes.supervisor.to==='Grid Supervisor', JSON.stringify(ek));
    ck('grid: projected as an override; the row shows it', MS_FIELD_OVERRIDE[kk]&&MS_FIELD_OVERRIDE[kk].supervisor==='Grid Supervisor'&&eng().dataView.getItemById(kk).supervisor==='Grid Supervisor', after);
    ck('grid: the schedule value is untouched', annotOwn(K,'supervisor')==='K. Lee', annotOwn(K,'supervisor'));
    ck('grid: a schedule column still refuses a write', schedGridEdit(kk,'finish','2030-01-01')===false, '');
    const b=document.querySelector('#grid-host [data-sg="back"]'); if(b) b.click();
    await settle(400); await settle();
    ck('grid: Back, the board shows the grid edit', K.supervisor==='Grid Supervisor', K.supervisor);
    await open(kid);
    ck('grid: the card shows the grid edit with its mark', $('ms-supervisor').value==='Grid Supervisor'&&!$('ms-mark-supervisor').hidden, $('ms-supervisor').value);
    discardMsDialog(); await settle();
    ck('page: no horizontal scroll', document.documentElement.scrollWidth<=window.innerWidth, document.documentElement.scrollWidth);

    R.notes.keys={pk:pk,qk:qk,kk:kk,uid:uid,pdisc:P.discipline};
    // ===== 7. Publish and model export (captured) =====
    if(PUBLISH){
      const cap={}, OB=window.Blob;
      window.Blob=function(parts,opts){ const t=parts.map(p=>typeof p==='string'?p:'').join(''); if(opts&&opts.type==='text/html') cap.html=t; if(opts&&opts.type==='application/json') cap.json=t; return new OB(parts,opts); };
      window.Blob.prototype=OB.prototype;
      const oc=HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click=function(){ if(this.download) return; return oc.call(this); };
      try{ publishDashboard(); exportModel(); } finally { window.Blob=OB; HTMLAnchorElement.prototype.click=oc; }
      ck('publish: a saved file was produced', !!cap.html&&cap.html.length>100000, cap.html&&cap.html.length);
      let M=null; try{ M=JSON.parse(cap.json||''); }catch(x){}
      ck('model: an export was produced', !!M, '');
      if(M){
        const mm=(M.milestones||[]).find(m=>msId(m)===pid);
        ck('model: the schedule values travel on the milestones', !!mm&&(mm._msBase?mm._msBase.supervisor||mm.supervisor:mm.supervisor)==='J. Smith'&&mm.discipline===P.discipline, JSON.stringify(mm&&{s:mm.supervisor,d:mm.discipline}));
        ck('model: the overrides travel (entries and milestoneFieldOverrides)', M.milestoneFieldOverrides[kk]&&M.milestoneFieldOverrides[kk].supervisor==='Grid Supervisor'&&
           M.entries.some(e=>e.target.key===kk&&e.changes.supervisor), '');
        ck('model: the user record carries its grid value', (M.userMilestones||[]).some(u=>u.id===uid&&u.engineer==='Grid User Engineer'), '');
      }
      R.html=cap.html||''; R.model=cap.json||'';
    }
    ck('no console errors', (window.__errs||[]).length===0, (window.__errs||[]).join(' | '));
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
    emit();
  }
})();
</script>"""

# The published file, opened in a fresh profile with nothing seeded.
LOAD_PUBLISHED = r"""<script>
(function(){
 function out(o){ const e=document.createElement('pre'); e.id='p78-out'; e.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(o)))); document.body.appendChild(e); }
 setTimeout(function(){
  try{
   const K=__KEYS__;
   const by=function(k){ return MILESTONES.find(function(m){ return msKeyFor(m)===k; })||null; };
   const p=by(K.pk), k=by(K.kk), u=USER_MILESTONES.find(function(r){ return r.id===K.uid; });
   out({published:!!window.__PUBLISHED_STATE__,
        pSup:p&&p.supervisor, pDisc:p&&p.discipline, pEng:p&&p.engineer, pOwnEng:p?annotOwn(p,'engineer'):null,
        kSup:k&&k.supervisor, kOwn:k?annotOwn(k,'supervisor'):null,
        ovK:MS_FIELD_OVERRIDE[K.kk]||null, ovU:MS_FIELD_OVERRIDE[K.uid]||null, uEng:u&&u.engineer,
        nWith:MILESTONES.filter(function(m){ return !!annotOwn(m,'discipline'); }).length});
  }catch(e){ out({err:String(e&&e.stack||e)}); }
 },3500);
})();
</script>"""

# The model export, mounted into a fresh app (the test fixture) the way a
# user does: the file input's handler, select all, Apply.
MOUNT_MODEL = r"""<script>
(async function(){
 function out(o){ const e=document.createElement('pre'); e.id='p78-out'; e.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(o)))); document.body.appendChild(e); }
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 try{
  await sleep(800);
  const K=__KEYS__, TEXT=__MODEL__;
  ANNOT_PENDING=null;
  handleAnnotFile({files:[new File([TEXT],'p78_model.json',{type:'application/json'})]});
  const yieldTask=function(){ return new Promise(function(r){ const c=new MessageChannel(); c.port1.onmessage=function(){ r(); }; c.port2.postMessage(0); }); };
  for(let i=0;i<20000&&!ANNOT_PENDING;i++){ await yieldTask(); if(i%200===199) await sleep(5); }
  if(!ANNOT_PENDING) throw new Error('handleAnnotFile never staged the file');
  annotSelectAll(); applyAnnotSelection();
  await sleep(600);
  const by=function(k){ return MILESTONES.find(function(m){ return msKeyFor(m)===k; })||null; };
  const k=by(K.kk), p=by(K.pk), u=USER_MILESTONES.find(function(r){ return r.id===K.uid; });
  out({fixture:typeof window.__SRET_FIXTURE__!=='undefined', ovK:MS_FIELD_OVERRIDE[K.kk]||null, ovP:MS_FIELD_OVERRIDE[K.pk]||null,
       ovU:MS_FIELD_OVERRIDE[K.uid]||null, kSup:k&&k.supervisor, pEng:p&&p.engineer, uEng:u&&u.engineer,
       entries:ENTRIES.filter(function(e){ return e.changes&&(e.changes.supervisor||e.changes.engineer||e.changes.discipline); }).length});
 }catch(e){ out({err:String(e&&e.stack||e)}); }
})();
</script>"""


def chrome(page, width, height, budget, no_fixture=False):
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p78.html"
        tmp.write_text(page, encoding="utf-8")
        env = dict(os.environ)
        if no_fixture:
            env["SRET_NO_FIXTURE"] = "1"
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={td}/prof",
             f"--window-size={width},{height}", f"--virtual-time-budget={budget}",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=900, env=env,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def inject(page, script, opt_out=False):
    page = page.replace("<head>", "<head>" + EARLY, 1)
    i = page.rindex("</body>")
    return page[:i] + (OPT_OUT + "\n" if opt_out else "") + script + "\n" + page[i:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html)
    src = html.read_text(encoding="utf-8", errors="replace")
    sheet, expect = build_sheet()
    tsv = to_tsv(sheet)

    checks = []
    block = src[src.index('<div id="ms-dialog"'):src.index('<div id="print-filter-note"')]
    checks.append(("source: no em dash in the card markup", "—" not in block and "&mdash;" not in block, ""))
    checks.append(("source: the hint is in the app verbatim", HINT in src, ""))
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal", len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))
    checks.append(("source: the three fields are editable fields (MS_EDITABLE_FIELDS)",
                   re.search(r"const MS_EDITABLE_FIELDS=\[[^\]]*'discipline','supervisor','engineer'\]", src) is not None, ""))
    checks.append(("source: the suggestions pick on mousedown with preventDefault",
                   'onmousedown="event.preventDefault();pickMsPfSuggestion(this)"' in src, ""))
    checks.append(("source: the aliases are in INGEST_CONFIG.headerAliases",
                   "discipline:['discipline','disc','trade']" in src and "supervisor:['supervisor','superintendent','lead']" in src
                   and "engineer:['engineer','responsible engineer','owner']" in src, ""))
    pasted = all((ROOT / rel).read_text(encoding="utf-8") in src for rel in (
        "src/modules/notes-store/notes-store.js", "src/modules/notes-card/form-to-entry.js",
        "src/modules/notes-history/notes-history.js"))
    checks.append(("source: the three modules are pasted unchanged", pasted, ""))

    for (w, h) in VIEWPORTS:
        probe = (PROBE.replace("__PUBLISH__", "true" if w == 1440 else "false")
                 .replace("__TSV__", json.dumps(tsv)).replace("__EXPECT__", json.dumps(expect))
                 .replace("__HINT__", json.dumps(HINT)))
        R = chrome(inject(src, probe, opt_out=True), w, h, 180000, no_fixture=True)
        print(f"\n=== {w}x{h} ===  samples {R.get('notes', {}).get('sample')}")
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))
        keys = R.get("notes", {}).get("keys")
        if R.get("html") and keys:
            out = R["html"]
            i = out.rindex("</body>")
            L = chrome(out[:i] + LOAD_PUBLISHED.replace("__KEYS__", json.dumps(keys)) + out[i:], w, h, 20000, no_fixture=True)
            if L.get("err"):
                checks.append(("published copy opens", False, L.get("err")[:300]))
            else:
                checks.append(("published: reports itself as published", L.get("published") is True, ""))
                checks.append(("published: schedule values survive (discipline and supervisor of P)",
                               L.get("pDisc") == keys["pdisc"] and L.get("pSup") == "J. Smith", json.dumps(L)))
                checks.append(("published: the card's engineer edit on P survives as an override over no schedule value",
                               L.get("pEng") == "P78 Free Text Engineer" and L.get("pOwnEng") is None, json.dumps(L)))
                checks.append(("published: the grid edit on K survives over the schedule's K. Lee",
                               L.get("kSup") == "Grid Supervisor" and L.get("kOwn") == "K. Lee" and (L.get("ovK") or {}).get("supervisor") == "Grid Supervisor", json.dumps(L)))
                checks.append(("published: the user milestone's override and record survive",
                               (L.get("ovU") or {}).get("discipline") == "Electrical P78" and L.get("uEng") == "Grid User Engineer", json.dumps(L)))
                checks.append(("published: the imported disciplines are all there", (L.get("nWith") or 0) > 100, L.get("nWith")))
        if R.get("model") and keys:
            fixture_page = inject(src, MOUNT_MODEL.replace("__KEYS__", json.dumps(keys)).replace("__MODEL__", json.dumps(R["model"])))
            M = chrome(fixture_page, w, h, 30000)
            if M.get("err"):
                checks.append(("model mounts", False, M.get("err")[:300]))
            else:
                checks.append(("model: mounted into the fixture app", M.get("fixture") is True, ""))
                checks.append(("model: the overrides come back (K supervisor, P engineer, U discipline)",
                               (M.get("ovK") or {}).get("supervisor") == "Grid Supervisor"
                               and (M.get("ovP") or {}).get("engineer") == "P78 Free Text Engineer"
                               and (M.get("ovU") or {}).get("discipline") == "Electrical P78", json.dumps(M)))
                checks.append(("model: the board shows them after the mount", M.get("kSup") == "Grid Supervisor" and M.get("pEng") == "P78 Free Text Engineer", json.dumps(M)))
                checks.append(("model: the user milestone record comes back with its value", M.get("uEng") == "Grid User Engineer", json.dumps(M)))
                checks.append(("model: the entries come back", (M.get("entries") or 0) >= 4, M.get("entries")))

    fails = 0
    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail and not ok else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
