#!/usr/bin/env python3
"""
p75_card_check: the milestone card rework (P75, Matt 2026-10-02).

Drives the real card in headless Chrome at 1440 and 390, with clicks on the
elements themselves (pointer and mouse events, then click), the harness style
of p69_check / p72_board_check:

  1. Start and Finish are date selectors: readonly (no free typing); a click
     anywhere on the field opens the picker (mouse and touch), Enter, Space
     and Alt+Down open it, Esc closes it; the field carries aria-expanded; the
     old calendar buttons are gone. A pick, the A flag and Clear save as
     before (one entry with date / actual), and the green ink follows A.
  2. Start, Duration and Finish are one uniform row: equal widths, the same
     top (within 1px), directly under the hairline (measured on the blocks
     themselves), equal label heights, and value boxes of one top, height,
     font and line height, also with the finish highlighted (dirty, actual).
  3. Float follows a moved finish, N=3: later (strike + float minus days),
     earlier (strike + float plus days), none (no strike); a saved override
     keeps the strike on reopen; the tooltip shows both end dates and the
     disclaimer verbatim, on keyboard focus and on a tap; Esc closes it first.
     A user milestone and a completed one never strike.
  4. Click-away saves from every exit: a click away, another marker, the same
     marker, a dependency chip jump, the back arrow, opening another card;
     Esc saves (popover first, then the card); only the cross discards. The
     cross's title and aria-label and the Help line say so.
  5. Copy milestone: the button sits immediately left of the save icon; it
     saves the card first, creates exactly one USR- milestone with the same
     title, finish, type and mark through addUserMilestone, in the
     "User Defined Milestones" band, with a "Copied from" history entry and
     no float; the copy's card opens with the arrival animation classes; with
     reduced motion there are none, and the CSS turns them off too.
  6. (1440 only) the copy survives publish: the captured saved file carries
     both copies in userMilestones and the copy entry, and a fresh load of the
     saved file has them in USER_MILESTONES.
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p75-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900), (390, 844)]

DISCLAIMER = ("Float is an indication based on the end date adjustment. Float is not recalculated "
              "by a scheduling engine and does not consider any changes of related activities.")

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  const PUBLISH=__PUBLISH__;
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p75-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const gap=()=>new Promise(r=>setTimeout(r,420));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog'), dp=()=>$('ms-dp');
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const rc=el=>el.getBoundingClientRect();
  // A real click: the pointer and mouse sequence a person's click sends,
  // then the click itself. A touch tap is pointerdown(touch) then click.
  const realClick=function(el,touch){
    const r=rc(el), o={bubbles:true,cancelable:true,clientX:r.left+r.width/2,clientY:r.top+r.height/2,button:0};
    let pd=null;
    try{ pd=new PointerEvent('pointerdown',Object.assign({pointerType:touch?'touch':'mouse',isPrimary:true},o)); el.dispatchEvent(pd); }catch(x){}
    if(!touch){ el.dispatchEvent(new MouseEvent('mousedown',o)); }
    try{ el.dispatchEvent(new PointerEvent('pointerup',Object.assign({pointerType:touch?'touch':'mouse',isPrimary:true},o))); }catch(x){}
    if(!touch){ el.dispatchEvent(new MouseEvent('mouseup',o)); }
    el.dispatchEvent(new MouseEvent('click',o));
    return pd;
  };
  const key=(el,k,extra)=>el.dispatchEvent(new KeyboardEvent('keydown',Object.assign({key:k,bubbles:true,cancelable:true},extra||{})));
  const esc=()=>key(document.activeElement&&document.activeElement!==document.body?document.activeElement:document,'Escape');
  const open=async function(id){
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    await gap(); realClick(wrapOf(id)); await settle();
    if(dlg().hidden||!wrapOf(id)) throw new Error('card did not open for '+id);
  };
  const day=iso=>dp().querySelector('.ms-dp-day[data-iso="'+iso+'"]');
  const addDays=(iso,n)=>{ const d=new Date(+iso.slice(0,4),+iso.slice(5,7)-1,+iso.slice(8,10)+n); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); };
  // Pick a date the way a person does: open from the field, step months,
  // optionally tick Actual, click the day.
  const pick=async function(fieldId,iso,actual){
    realClick($(fieldId)); await settle();
    for(let i=0;i<24&&!day(iso);i++){
      const cur=MS_DP.y*12+MS_DP.m, want=(+iso.slice(0,4))*12+(+iso.slice(5,7)-1);
      dp().querySelector(want>cur?'.ms-dp-next':'.ms-dp-prev').click(); await settle();
    }
    if(actual) $('ms-dp-actual').click();
    realClick(day(iso)); await settle();
  };
  const setTitle=function(t){ $('ms-title').value=t; $('ms-title').dispatchEvent(new Event('input',{bubbles:true})); };
  const savedTitle=k=>(MS_FIELD_OVERRIDE[k]||{}).actName;
  const msEntries=k=>ENTRIES.filter(e=>e.target.kind==='ms'&&e.target.key===k);
  const colorOf=v=>{ const sp=document.createElement('span'); sp.style.color='var('+v+')'; document.body.appendChild(sp); const c=getComputedStyle(sp).color; sp.remove(); return c; };
  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    const GREEN=colorOf('--color-status-done');
    const onBoard=MILESTONES.filter(m=>msId(m)&&wrapOf(msId(m)));
    const isDoneM=m=>{ const s=effectiveState(m); return s==='DONE'||s==='DONEUSER'; };
    // F: a schedule milestone with a real start, a float, not complete.
    const F=onBoard.find(m=>!isUserMs(m)&&!m.actual&&m.start&&m.floatD!=null&&!isNaN(m.floatD)&&!isDoneM(m)&&!m.startActual);
    ck('sample: a forecast schedule milestone with float on the board', !!F, F?msId(F):'none');
    const A=msId(F), AK=msKeyFor(F), AF=Math.round(F.floatD), AFIN=F.date;
    R.notes.sample=A;
    const others=onBoard.filter(m=>m!==F&&!isUserMs(m));

    // ===== 1. Date fields are selectors =====
    await open(A);
    const fS=$('ms-start-date'), fF=$('ms-date');
    ck('field: no calendar buttons any more, the field is the trigger', !$('ms-dp-btn-start')&&!$('ms-dp-btn-date')&&!dlg().querySelector('.ms-dp-btn'), '');
    ck('field: readonly (no free typing), a selector by role', fS.readOnly&&fF.readOnly&&fF.getAttribute('aria-haspopup')==='dialog'&&fS.getAttribute('aria-haspopup')==='dialog', '');
    // A selector by behaviour; at rest it stays plain (P66 read-first: no
    // fill, no border, which p66_check asserts).
    ck('field: a pointer cursor, plain at rest (P66)', getComputedStyle(fF).cursor==='pointer'&&getComputedStyle(fS).cursor==='pointer'&&parseFloat(getComputedStyle(fF).borderTopWidth)===0, getComputedStyle(fF).cursor+' '+getComputedStyle(fF).borderTopWidth);
    // Mouse click anywhere on the field: at its right edge, not its centre.
    { const r=rc(fF), o={bubbles:true,cancelable:true,clientX:r.right-3,clientY:r.top+3,button:0};
      fF.dispatchEvent(new PointerEvent('pointerdown',Object.assign({pointerType:'mouse'},o)));
      fF.dispatchEvent(new MouseEvent('mousedown',o)); fF.dispatchEvent(new MouseEvent('mouseup',o)); fF.dispatchEvent(new MouseEvent('click',o)); }
    await settle();
    ck('desktop: a click on the finish field opens the picker', !dp().hidden&&MS_DP.field==='ms-date'&&fF.getAttribute('aria-expanded')==='true', MS_DP.field);
    ck('desktop: the picker opens on the field\'s own date', day(AFIN)&&day(AFIN).classList.contains('is-sel'), AFIN);
    realClick(fF); await settle();
    ck('desktop: a second click on the open field leaves it open', !dp().hidden&&MS_DP.field==='ms-date', '');
    esc(); await settle();
    ck('Esc: closes the picker, the card stays', dp().hidden&&!dlg().hidden&&fF.getAttribute('aria-expanded')==='false', '');
    realClick(fS); await settle();
    ck('desktop: a click on the start field opens the picker for start', !dp().hidden&&MS_DP.field==='ms-start-date', MS_DP.field);
    esc(); await settle();
    const pe=realClick(fS,true); await settle();
    ck('touch: a tap opens the picker, the keyboard is held back', pe&&pe.defaultPrevented&&!dp().hidden&&MS_DP.field==='ms-start-date', pe&&pe.defaultPrevented);
    esc(); await settle();
    const pe2=realClick(fF,true); await settle();
    ck('touch: a tap on finish opens the picker for finish, and its click does not close it', pe2&&pe2.defaultPrevented&&!dp().hidden&&MS_DP.field==='ms-date', '');
    esc(); await settle();
    fF.focus(); key(fF,'Enter'); await settle();
    ck('keys: Enter on the field opens the picker', !dp().hidden&&MS_DP.field==='ms-date', '');
    esc(); await settle();
    ck('keys: Esc returns focus to the field', document.activeElement===fF, document.activeElement&&document.activeElement.id);
    key(fF,' '); await settle();
    ck('keys: Space on the field opens the picker', !dp().hidden, '');
    esc(); await settle();
    key(fF,'ArrowDown',{altKey:true}); await settle();
    ck('keys: Alt+Down on the field opens the picker', !dp().hidden, '');
    esc(); await settle();
    ck('keys: three Escs closed only the picker, never the card', !dlg().hidden, '');
    ck('field: still clean after opening and closing', $('ms-save-actions').getAttribute('aria-disabled')==='true', '');
    // Pick with the A flag, save, then Clear.
    const d2=addDays(AFIN,3);
    await pick('ms-date',d2,true);
    ck('pick: "<date> A" written, green at once', fF.value===fmtTipDate(d2)+' A'&&fF.classList.contains('is-actualised')&&getComputedStyle(fF).color===GREEN, fF.value);
    ck('pick: the card is dirty', $('ms-save-actions').getAttribute('aria-disabled')==='false', '');
    realClick($('ms-save-actions').querySelector('.ms-act-icon')); await settle();
    const E=msEntries(AK).slice(-1)[0];
    ck('save: one entry with the date and the A flag', E&&E.changes.date&&E.changes.date.to===d2&&E.changes.actual&&E.changes.actual.to===true, JSON.stringify(E&&E.changes));
    ck('save: projected to the store', MS_FIELD_OVERRIDE[AK]&&MS_FIELD_OVERRIDE[AK].date===d2&&MS_FIELD_OVERRIDE[AK].actual===true, JSON.stringify(MS_FIELD_OVERRIDE[AK]));
    await gap();
    await open(A);
    ck('reopen: the stored value is read back, A and green', fF.value===fmtTipDate(d2)+' A'&&fF.classList.contains('is-actualised'), fF.value);
    realClick(fF); await settle();
    dp().querySelector('.ms-dp-clear').click(); await settle();
    ck('clear: empties the field', fF.value==='', fF.value);
    realClick($('ms-save-actions').querySelector('.ms-act-icon')); await settle();
    ck('clear: back to the schedule date', !MS_FIELD_OVERRIDE[AK]||(!('date' in MS_FIELD_OVERRIDE[AK])&&!('actual' in MS_FIELD_OVERRIDE[AK])), JSON.stringify(MS_FIELD_OVERRIDE[AK]||{}));
    discardMsDialog(); await gap();

    // ===== 2. Uniform row =====
    await open(A);
    const measureRow=function(tag){
      const sch=dlg().querySelector('.ms-schedule'), cs=getComputedStyle(sch);
      const rule=rc(sch).top+parseFloat(cs.borderTopWidth);
      const blocks=[$('ms-start-field'),$('ms-dur-field'),$('ms-fin-field')];
      const vals=[$('ms-start-date'),$('ms-duration'),$('ms-date')];
      const lbls=blocks.map(b=>b.querySelector('.ms-lbl'));
      const B=blocks.map(rc), V=vals.map(rc), L=lbls.map(rc);
      const r=a=>a.map(x=>Math.round(x*10)/10);
      R.notes['row_'+tag]={w:r(B.map(b=>b.width)),top:r(B.map(b=>b.top)),rule:Math.round(rule*10)/10,pad:cs.paddingTop,vTop:r(V.map(v=>v.top)),vH:r(V.map(v=>v.height)),lH:r(L.map(l=>l.height))};
      ck('row '+tag+': the three blocks have the same width', Math.max(...B.map(b=>b.width))-Math.min(...B.map(b=>b.width))<=1, r(B.map(b=>b.width)).join(','));
      ck('row '+tag+': the same top within 1px', Math.max(...B.map(b=>b.top))-Math.min(...B.map(b=>b.top))<=1, r(B.map(b=>b.top)).join(','));
      ck('row '+tag+': directly under the rule (the row\'s own top padding, nothing more)', B.every(b=>Math.abs(b.top-(rule+parseFloat(cs.paddingTop)))<=1)&&L.every(l=>Math.abs(l.top-(rule+parseFloat(cs.paddingTop)))<=1), 'rule '+Math.round(rule)+' pad '+cs.paddingTop+' tops '+r(B.map(b=>b.top)));
      ck('row '+tag+': equal label heights', Math.max(...L.map(l=>l.height))-Math.min(...L.map(l=>l.height))<=0.5, r(L.map(l=>l.height)).join(','));
      ck('row '+tag+': value boxes share a top and a height', Math.max(...V.map(v=>v.top))-Math.min(...V.map(v=>v.top))<=0.5&&Math.max(...V.map(v=>v.height))-Math.min(...V.map(v=>v.height))<=0.5, 'tops '+r(V.map(v=>v.top))+' h '+r(V.map(v=>v.height)));
      const fs=vals.map(v=>{ const c=getComputedStyle(v); return [c.fontSize,c.lineHeight,c.fontWeight,c.paddingTop,c.borderTopWidth,c.verticalAlign].join('/'); });
      ck('row '+tag+': value boxes share font, line height, padding and border (one baseline)', fs.every(x=>x===fs[0]), fs.join(' | '));
      ck('row '+tag+': value text left aligned in all three', vals.every(v=>getComputedStyle(v).textAlign==='left'||getComputedStyle(v).textAlign==='start'), vals.map(v=>getComputedStyle(v).textAlign).join(','));
    };
    measureRow('at rest');
    await pick('ms-date',addDays(AFIN,2),true);
    ck('highlight: the finish carries the dirty tint', fF.classList.contains('ms-dirty-field'), '');
    measureRow('finish highlighted');
    discardMsDialog(); await settle();

    // ===== 3. Float follows a moved finish (N=3) =====
    await open(A);
    const fv=$('ms-float-val'), was=$('ms-float-was'), adj=$('ms-float-adj'), col=$('ms-float-col'), tip=$('ms-float-tip');
    ck('float: at rest, the schedule figure, no strike', fv.value===String(AF)&&was.hidden&&adj.hidden&&!col.classList.contains('is-moved')&&getComputedStyle(fv).display!=='none', fv.value+' vs '+AF);
    const shifts=[[3,'later'],[-5,'earlier'],[0,'none']];
    for(const s of shifts){
      await pick('ms-date',addDays(AFIN,s[0]),false);
      if(s[0]===0){
        ck('float none: the same finish, no strike', !col.classList.contains('is-moved')&&was.hidden&&adj.hidden&&fv.value===String(AF)&&getComputedStyle(fv).display!=='none', col.className);
      } else {
        ck('float '+s[1]+': the schedule float struck through (<s>)', !was.hidden&&was.tagName==='S'&&was.textContent===String(AF)&&getComputedStyle(was).textDecorationLine.indexOf('line-through')>=0, was.tagName+' '+was.textContent);
        ck('float '+s[1]+': the adjusted float is schedule '+(s[0]>0?'minus ':'plus ')+Math.abs(s[0]), !adj.hidden&&adj.textContent===String(AF-s[0]), adj.textContent+' vs '+(AF-s[0]));
        ck('float '+s[1]+': still read only', fv.readOnly, '');
      }
    }
    // A cleared finish is the schedule's own date: no strike.
    realClick(fF); await settle(); dp().querySelector('.ms-dp-clear').click(); await settle();
    ck('float: Clear removes the strike', !col.classList.contains('is-moved'), '');
    // Saved override: the strike stays on reopen.
    await pick('ms-date',addDays(AFIN,4),false);
    realClick($('ms-save-actions').querySelector('.ms-act-primary')); await gap(); await settle();
    await open(A);
    ck('float override: the strike stays on reopen', col.classList.contains('is-moved')&&was.textContent===String(AF)&&adj.textContent===String(AF-4), was.textContent+' '+adj.textContent);
    // Tooltip: keyboard focus, tap, content, Esc.
    ck('tooltip: hidden at rest', getComputedStyle(tip).display==='none', '');
    ck('tooltip: the float is focusable when it carries one', col.tabIndex===0&&col.getAttribute('aria-describedby')==='ms-float-tip', '');
    col.focus(); await settle();
    ck('tooltip: shown on keyboard focus', document.activeElement===col&&getComputedStyle(tip).display==='block', getComputedStyle(tip).display);
    const tt=tip.textContent;
    ck('tooltip: the previous (schedule) end date', tt.indexOf(fmtTipDate(AFIN))>=0&&/Previous end date/.test(tt), tt.slice(0,80));
    ck('tooltip: the current end date', tt.indexOf(fmtTipDate(addDays(AFIN,4)))>=0&&/Current end date/.test(tt), '');
    ck('tooltip: the disclaimer verbatim', tt.indexOf(__DISC__)>=0, '');
    ck('tooltip: no em dash', tt.indexOf('—')<0, '');
    const tr=rc(tip), dr=rc(dlg());
    ck('tooltip: inside the card horizontally', tr.left>=dr.left-1&&tr.right<=dr.right+1, [tr.left,tr.right,dr.left,dr.right].map(Math.round).join(','));
    col.blur(); $('ms-title').focus(); await settle();
    ck('tooltip: hidden again on blur', getComputedStyle(tip).display==='none', '');
    realClick(col,true); await settle();
    ck('tooltip: a tap opens it', col.classList.contains('is-open')&&getComputedStyle(tip).display==='block', '');
    key(document,'Escape'); await settle();
    ck('tooltip: Esc closes it first, the card stays', !col.classList.contains('is-open')&&!dlg().hidden, '');
    realClick(col,true); await settle();
    realClick($('ms-title')); await settle();
    ck('tooltip: a click elsewhere in the card closes it', !col.classList.contains('is-open')&&!dlg().hidden, '');
    discardMsDialog(); await settle();
    // Completed and user milestones never strike.
    // A schedule-complete milestone, and one with a float marked done on
    // the card (health Done), which is the case that has a float to strike.
    const D=onBoard.find(m=>!isUserMs(m)&&isDoneM(m));
    ck('sample: a completed schedule milestone on the board', !!D, D?msId(D):'none');
    if(D){ await open(msId(D)); await pick('ms-date',addDays(D.date,6),false);
      ck('float done (schedule): reads "-" and no strike after a move', fv.value===''&&!col.classList.contains('is-moved')&&was.hidden, fv.value+' '+col.className);
      discardMsDialog(); await settle(); }
    const DF=onBoard.find(m=>m!==F&&!isUserMs(m)&&!isDoneM(m)&&m.floatD!=null&&!isNaN(m.floatD));
    await open(msId(DF));
    onMsHealthClick(document.querySelector('#ms-health-dots .health-dot[data-val="2"]'));
    realClick($('ms-save-actions').querySelector('.ms-act-primary')); await gap(); await settle();
    await open(msId(DF));
    ck('float done (marked on the card): the milestone reads complete', /status-done/.test(dlg().className), dlg().className);
    await pick('ms-date',addDays(DF.date,6),false);
    ck('float done (marked on the card): "-" and no strike after a move', fv.value===''&&!col.classList.contains('is-moved')&&was.hidden&&adj.hidden, fv.value+' '+col.className);
    discardMsDialog(); await settle();
    // A user milestone carries no float, moved or not (the copies below
    // assert the same on their own cards).

    // ===== 4. Every exit saves; only the cross discards =====
    const B1=others[0], B2=others[1], B3=others[2];
    const k1=msKeyFor(B1), k2=msKeyFor(B2), k3=msKeyFor(B3);
    // (a) click away
    await open(msId(B1)); setTitle('P75 away '+R.notes.sample);
    realClick(document.body); await settle();
    ck('exit click-away: saved and closed', dlg().hidden&&savedTitle(k1)==='P75 away '+R.notes.sample, savedTitle(k1));
    await gap();
    // (b) another marker
    await open(msId(B1)); setTitle('P75 marker');
    realClick(wrapOf(msId(B2))); await settle();
    ck('exit another marker: saved, and the other card is open', savedTitle(k1)==='P75 marker'&&!dlg().hidden&&msDialogFor===k2, savedTitle(k1)+' / '+msDialogFor);
    await gap();
    // (c) the same marker again
    if(dlg().hidden) await open(msId(B2));
    setTitle('P75 same marker');
    realClick(wrapOf(msId(B2))); await settle();
    ck('exit same marker: saved and closed', dlg().hidden&&savedTitle(k2)==='P75 same marker', savedTitle(k2));
    await gap();
    // (d) opening another card (a note chip / grid open goes through here)
    await open(msId(B2)); setTitle('P75 other card');
    openNoteMilestone(null,msId(B3)); await settle();
    ck('exit opening another card: saved, the other card is open', savedTitle(k2)==='P75 other card'&&!dlg().hidden&&msDialogFor===k3, savedTitle(k2)+' / '+msDialogFor);
    discardMsDialog(); await gap();
    // (e) a dependency chip jump, then (f) the back arrow
    const J=onBoard.find(m=>{ const d=DEP_DATA[msId(m)]; return d&&parseIds(d.succ).concat(parseIds(d.pred)).some(x=>x!==msId(m)&&wrapOf(x)); });
    ck('sample: a milestone with a linked milestone on the board', !!J, J?msId(J):'none');
    if(J){
      const jk=msKeyFor(J), jid=msId(J);
      await open(jid);
      const chip=[...dlg().querySelectorAll('#ms-dep-pred-chips .ms-dep-chip:not(.is-off), #ms-dep-succ-chips .ms-dep-chip:not(.is-off)')].find(c=>c.getAttribute('data-id')!==jid);
      const tid=chip&&chip.getAttribute('data-id'), tk=tid&&msKeyFor(findMilestoneById(tid));
      setTitle('P75 chip');
      realClick(chip); await gap(); await settle();
      ck('exit chip jump: saved, the linked card is open', savedTitle(jk)==='P75 chip'&&!dlg().hidden&&msDialogFor===tk, savedTitle(jk)+' / '+msDialogFor+' vs '+tk);
      ck('back: the arrow is offered after the jump', !$('ms-back').hidden, '');
      setTitle('P75 back');
      realClick($('ms-back')); await gap(); await settle();
      ck('exit back arrow: saved, back on the first card', savedTitle(tk)==='P75 back'&&!dlg().hidden&&msDialogFor===jk, savedTitle(tk)+' / '+msDialogFor);
      discardMsDialog(); await gap();
    }
    // (g) Esc: popover first, then save and close
    await open(msId(B3)); setTitle('P75 esc');
    realClick(fF); await settle();
    esc(); await settle();
    ck('Esc 1: closes the picker only', dp().hidden&&!dlg().hidden&&$('ms-title').value==='P75 esc', '');
    toggleMsHealthPop(); await settle();
    key(document,'Escape'); await settle();
    ck('Esc 2: closes the health popover only', $('ms-health-pop').hidden&&!dlg().hidden, '');
    toggleMsTypeMenu(); await settle();
    key(document,'Escape'); await settle();
    ck('Esc 3: closes the type menu only', $('ms-type-menu').hidden&&!dlg().hidden, '');
    key(document,'Escape'); await settle();
    ck('Esc: does not discard, it saves and closes', dlg().hidden&&savedTitle(k3)==='P75 esc', savedTitle(k3));
    await gap();
    await open(msId(B3));
    key(document,'Escape'); await settle();
    ck('Esc on a clean card: closes it, nothing written', dlg().hidden&&savedTitle(k3)==='P75 esc', '');
    await gap();
    // (h) the cross discards
    await open(msId(B3)); const nX=ENTRIES.length; setTitle('P75 cross');
    realClick(dlg().querySelector('.ms-close')); await settle();
    ck('cross: discards, nothing written', dlg().hidden&&savedTitle(k3)==='P75 esc'&&ENTRIES.length===nX, savedTitle(k3));
    const cx=dlg().querySelector('.ms-close');
    ck('cross: title says it discards and that the other ways save', /without saving/i.test(cx.title)&&/discard/i.test(cx.title)&&/sav/i.test(cx.title.replace(/without saving/i,'')), cx.title);
    ck('cross: aria-label says the same', /without saving/i.test(cx.getAttribute('aria-label'))&&/discard/i.test(cx.getAttribute('aria-label')), cx.getAttribute('aria-label'));
    const help=$('sd-panel-help')?$('sd-panel-help').textContent:'';
    ck('help: the Esc line says the card is saved and only the cross discards', /Esc/.test(help)&&/saved/.test(help)&&/only its .{1,3} discards/.test(help), '');
    await gap();

    // ===== 5. Copy milestone =====
    const S=others[3], SK=msKeyFor(S), sid=msId(S);
    await open(sid);
    const cb=$('ms-copy-btn'), saveIco=$('ms-save-actions').querySelector('.ms-act-icon');
    ck('copy: the button is labelled "Copy milestone"', cb&&cb.getAttribute('aria-label')==='Copy milestone'&&cb.title==='Copy milestone', '');
    ck('copy: immediately left of the save icon', cb&&cb.nextElementSibling===$('ms-save-actions')&&$('ms-save-actions').firstElementChild===saveIco&&rc(cb).right<=rc(saveIco).left&&rc(saveIco).left-rc(cb).right<=12&&Math.abs(rc(cb).top-rc(saveIco).top)<=1, Math.round(rc(saveIco).left-rc(cb).right));
    ck('copy: at the top right of the header', dlg().querySelector('.ms-dialog-head').contains(cb)&&rc(cb).left>rc(dlg()).left+rc(dlg()).width/2, '');
    ck('copy: enabled on a clean card', cb.getAttribute('aria-disabled')!=='true'&&!cb.disabled, '');
    // Edit the card: a new title, a later finish, the star and type INT.
    setTitle('P75 copy source');
    const cfin=addDays(S.date,7);
    await pick('ms-date',cfin,false);
    pickMsType('INT'); pickMsMarker('star'); await settle();
    const nUser=USER_MILESTONES.length, nUsr=MILESTONES.filter(m=>/^USR-/.test(msId(m)||'')).length;
    // The animation lasts 200 ms and is removed once played, so it is caught
    // as it is applied: a MutationObserver records the class and the computed
    // animation name at that moment.
    const seen={dlg:null,wrap:null};
    const mo=new MutationObserver(function(list){ list.forEach(function(r){
      const t=r.target; if(r.attributeName!=='class'||!t.classList) return;
      if(t.id==='ms-dialog'&&t.classList.contains('ms-copy-in')&&!seen.dlg) seen.dlg={id:msDialogFor,anim:getComputedStyle(t).animationName};
      if(t.classList.contains('m-wrap')&&t.classList.contains('ms-copy-pulse')&&!seen.wrap) seen.wrap={id:t.getAttribute('data-ms'),anim:getComputedStyle(t).animationName};
    }); });
    mo.observe(document.body,{attributes:true,attributeFilter:['class'],subtree:true});
    realClick(cb); await settle();
    ck('copy: the source was saved first', savedTitle(SK)==='P75 copy source'&&MS_FIELD_OVERRIDE[SK].date===cfin&&MS_FIELD_OVERRIDE[SK].type==='INT'&&/star/i.test(MS_FIELD_OVERRIDE[SK].marker||''), JSON.stringify(MS_FIELD_OVERRIDE[SK]));
    ck('copy: exactly one new user milestone', USER_MILESTONES.length===nUser+1, USER_MILESTONES.length+' vs '+nUser);
    const C=USER_MILESTONES[USER_MILESTONES.length-1];
    R.notes.copy=C&&C.id;
    ck('copy: a USR- id', C&&/^USR-\d{3}$/.test(C.id), C&&C.id);
    ck('copy: the same title', C&&C.actName==='P75 copy source', C&&C.actName);
    ck('copy: the effective finish', C&&C.date===cfin, C&&C.date+' vs '+cfin);
    ck('copy: the same type and mark', C&&C.type==='INT'&&/star/i.test(C.marker), C&&(C.type+' '+C.marker));
    ck('copy: no float', C&&C.floatD==null, C&&C.floatD);
    // Wait for the copy's card.
    let opened=false;
    for(let i=0;i<60;i++){ if(!dlg().hidden&&msDialogFor===C.id){ opened=true; break; } await new Promise(r=>setTimeout(r,20)); }
    ck('copy: its card opens', opened, msDialogFor);
    await settle();
    ck('copy: the card scales in (animation class applied, animation running)', seen.dlg&&seen.dlg.id===C.id&&seen.dlg.anim==='ms-copy-in', JSON.stringify(seen.dlg));
    const cw=wrapOf(C.id);
    ck('copy: the new marker pulses (animation class applied, animation running)', seen.wrap&&seen.wrap.id===C.id&&seen.wrap.anim==='ms-copy-pulse', JSON.stringify(seen.wrap));
    ck('copy: one more USR- milestone on the board', MILESTONES.filter(m=>/^USR-/.test(msId(m)||'')).length===nUsr+1, '');
    const ctr=cw&&cw.closest('tr[data-type="row"]');
    let band=null; for(let t=ctr&&ctr.previousElementSibling;t;t=t.previousElementSibling){ if(t.getAttribute('data-type')==='phase'){ band=t.textContent.trim(); break; } }
    R.notes.band=band;
    ck('copy: sits in the user section "User Defined Milestones"', band==='User Defined Milestones'&&USER_BAND==='User Defined Milestones'&&TASKS.find(t=>t.ref===ctr.getAttribute('data-ref')).notes===USER_BAND, band);
    ck('copy: its card shows the title and the finish', $('ms-title').value==='P75 copy source'&&parseMsDate($('ms-date').value)===cfin, $('ms-title').value+' '+$('ms-date').value);
    ck('copy: its card shows no float and no strike', $('ms-float-val').value===''&&!$('ms-float-col').classList.contains('is-moved'), '');
    const ce=msEntries(C.id);
    ck('copy: history records where it came from', ce.length===1&&ce[0].changes.copiedFrom&&ce[0].changes.copiedFrom.from===sid&&ce[0].changes.copiedFrom.to===C.id&&/Copied from/.test($('ms-history').textContent)&&$('ms-history').textContent.indexOf(sid)>=0, JSON.stringify(ce.map(e=>e.changes)));
    ck('copy: the source is unchanged by the copy', MILESTONES.some(m=>msKeyFor(m)===SK), '');
    await new Promise(r=>setTimeout(r,1500));
    ck('copy: the animation classes are removed once played', !dlg().classList.contains('ms-copy-in')&&!(wrapOf(C.id)||{classList:{contains:()=>false}}).classList.contains('ms-copy-pulse'), dlg().className);
    // Reduced motion: no classes, and the CSS turns them off as well.
    const mm=window.matchMedia;
    window.matchMedia=function(q){ if(/prefers-reduced-motion/.test(q)) return {matches:true,media:q,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}}; return mm.call(window,q); };
    let C2=null;
    try{
      const nU2=USER_MILESTONES.length;
      realClick($('ms-copy-btn')); await settle();
      C2=USER_MILESTONES[USER_MILESTONES.length-1];
      seen.dlg=null; seen.wrap=null;
      for(let i=0;i<60;i++){ if(!dlg().hidden&&msDialogFor===C2.id) break; await new Promise(r=>setTimeout(r,20)); }
      await settle();
      ck('reduced motion: the classes were never applied', !seen.dlg&&!seen.wrap, JSON.stringify(seen));
      ck('reduced motion: the copy of a copy is made (one more)', USER_MILESTONES.length===nU2+1&&C2.actName==='P75 copy source'&&C2.date===cfin, C2&&C2.id);
      ck('reduced motion: its card opens with no animation class', !dlg().hidden&&msDialogFor===C2.id&&!dlg().classList.contains('ms-copy-in')&&getComputedStyle(dlg()).animationName==='none', dlg().className);
      ck('reduced motion: no pulse on the marker', wrapOf(C2.id)&&!wrapOf(C2.id).classList.contains('ms-copy-pulse'), '');
    } finally { window.matchMedia=mm; mo.disconnect(); }
    let mediaOff=false;
    for(const sh of document.styleSheets){ let rs; try{ rs=sh.cssRules; }catch(x){ continue; }
      for(const r of rs){ if(r.media&&/prefers-reduced-motion/.test(r.media.mediaText)){ for(const ir of r.cssRules){ if(/ms-copy-in/.test(ir.selectorText)&&/ms-copy-pulse/.test(ir.selectorText)&&/none/.test(ir.style.animation||ir.style.animationName)) mediaOff=true; } } } }
    ck('reduced motion: the CSS turns both animations off as well', mediaOff, '');
    discardMsDialog(); await settle();
    R.notes.copies=[C&&C.id,C2&&C2.id];
    // ===== 6. Publish (captured) =====
    if(PUBLISH){
      const cap={}, OB=window.Blob;
      window.Blob=function(parts,opts){ if(opts&&opts.type==='text/html') cap.text=parts.join(''); return new OB(parts,opts); };
      window.Blob.prototype=OB.prototype;
      const oc=HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click=function(){ if(this.download){ cap.name=this.download; return; } return oc.call(this); };
      try{ publishDashboard(); } finally { window.Blob=OB; HTMLAnchorElement.prototype.click=oc; }
      const m=/window.__PUBLISHED_STATE__=(.*?);<\/script>/s.exec(cap.text||'');
      let S2=null; try{ S2=m?JSON.parse(m[1]):null; }catch(x){}
      const um=(S2&&S2.userMilestones)||[];
      ck('publish: a saved file was produced', !!cap.text&&cap.text.length>100000, cap.name);
      ck('publish: both copies are in userMilestones with title, finish, type and mark',
         [C,C2].every(c=>um.some(u=>u.id===c.id&&u.actName===c.actName&&u.date===c.date&&u.type==='INT'&&/star/i.test(u.marker))), JSON.stringify(um.map(u=>u.id)));
      ck('publish: the copy entry is in the saved entries', (S2&&S2.entries||[]).some(e=>e.target&&e.target.key===C.id&&e.changes&&e.changes.copiedFrom), '');
      R.html=cap.text||'';
    }
    ck('page: no horizontal scroll', document.documentElement.scrollWidth<=window.innerWidth, document.documentElement.scrollWidth);
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.message||err)});
    R.err=String(err&&err.stack||err);
    emit();
  }
})();
"""

LOAD = r"""<script>
(function(){
 function out(o){ const e=document.createElement('pre'); e.id='p75-out'; e.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(o)))); document.body.appendChild(e); }
 setTimeout(function(){
  try{ out({published:!!window.__PUBLISHED_STATE__,user:USER_MILESTONES.map(function(m){ return {id:m.id,actName:m.actName,date:m.date,type:m.type,marker:m.marker}; }),
            entries:ENTRIES.filter(function(e){ return e.changes&&e.changes.copiedFrom; }).length}); }
  catch(e){ out({err:String(e&&e.stack||e)}); }
 },3000);
})();
</script></body>"""


def chrome(page, width, height, budget, no_fixture=False):
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p75.html"
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


def render(html_path, width, height, publish):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    probe = PROBE.replace("__PUBLISH__", "true" if publish else "false").replace("__DISC__", json.dumps(DISCLAIMER))
    out = page.replace("</body>", "<script>\n" + probe + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    return chrome(out, width, height, 120000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html)
    src = html.read_text(encoding="utf-8", errors="replace")

    checks = []
    block = src[src.index('<div id="ms-dialog"'):src.index('<div id="print-filter-note"')]
    checks.append(("source: no em dash in the card markup", "—" not in block and "&mdash;" not in block, ""))
    checks.append(("source: the disclaimer is in the app verbatim", DISCLAIMER in src, ""))
    checks.append(("source: no em dash in the start placeholder", "startEl.placeholder='—'" not in src, ""))
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal",
                   len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))
    checks.append(("source: copy goes through addUserMilestone",
                   re.search(r"function copyMsMilestone\(e\)\{[\s\S]*?addUserMilestone\(", src) is not None, ""))

    for (w, h) in VIEWPORTS:
        R = render(html, w, h, publish=(w == 1440))
        print(f"\n=== {w}x{h} ===  sample {R.get('notes', {}).get('sample')}  copies {R.get('notes', {}).get('copies')}  band {R.get('notes', {}).get('band')}")
        if R.get("err"):
            print(R["err"])
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))
        if R.get("html"):
            out = R["html"]
            i = out.rindex("</body>")
            L = chrome(out[:i] + LOAD + out[i + 7:], w, h, 20000, no_fixture=True)
            if L.get("err"):
                checks.append(("published copy opens", False, L["err"][:200]))
            else:
                ids = [x for x in R["notes"].get("copies", []) if x]
                have = {u["id"]: u for u in L["user"]}
                checks.append(("published copy opens: reports itself as published", L["published"] is True, ""))
                checks.append(("published copy opens: both copies in USER_MILESTONES",
                               len(ids) == 2 and all(i in have and have[i]["type"] == "INT" and "star" in str(have[i]["marker"]).lower() for i in ids),
                               json.dumps(list(have))))
                checks.append(("published copy opens: the copy entry survives", L["entries"] >= 1, L["entries"]))

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
