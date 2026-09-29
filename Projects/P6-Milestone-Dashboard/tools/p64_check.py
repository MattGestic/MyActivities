#!/usr/bin/env python3
"""
P64 check (TD-224, TEST-65): the schedule info bar, the header moves and the
editable project number, from Matt's approved mockup of 2026-09-29.

Runs the real app in headless Chromium with the network unresolvable
(--host-resolver-rules=MAP * ~NOTFOUND) at 1440 and 390. Reads geometry, DOM
state, classList, computed style and the stores, never a screenshot. Extra
schedules are loaded through the real import path (Parse.workbook, showMapper,
runIngest) with SheetJS stood in at its boundary, as d17a_check does, fed the
reference workbook's rows.

  H   heading: no project details are left in the app heading; the Unsaved
      changes pill sits immediately left of the More actions control in the
      top row (the inline icon cluster on desktop, the trigger on a phone);
      the tool name and version are out of the header and at the foot of
      Data & view, read from APP_VERSION, visible in every section
  B   info bar: directly above the month row; left part over the frozen label
      column, right part over the timeline; sticky on vertical scroll (the bar
      element itself is measured); stays put on horizontal scroll without
      breaking the frozen column; shows the project number, report date and
      its W/E
  C   chips, N=3 loaded schedules: three chips with the right data dates,
      exactly one current (the latest data date among enabled schedules), a
      disabled one dimmed, clicking one opens Data & view > Sources and changes
      nothing; the current data-date week is tinted in the week row
  P   project number: editing it in Data settings updates the bar; blank shows
      "Project No. not set" and its link opens the field; auto-fill from a
      file named 123456-7_Something.xlsx only when empty, with the hint, never
      overwriting a set value; the hint clears on edit or on OK
  R   round trips: publish (set and blank), a published file without the
      field, the model export and mount, an old model without the field
  M   phone (390): the bar wraps to at most two lines; the chips scroll
      sideways inside the bar; the page does not
  X   print preview: the bar is present above the month row

Usage:
  python3 tools/p64_check.py [--html FILE]
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
from import_check import build_aoa, find_chrome  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
XLSX = ROOT / "data" / "schedules" / "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"
OUT_RE = re.compile(r'<pre id="p64-out">(.*?)</pre>', re.S)

COMMON = r"""
  const R={checks:[],notes:{},cap:{}};
  function ck(n,p,d){ R.checks.push({name:'['+ARGS.tag+'] '+n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p64-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,260));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const cs=el=>getComputedStyle(el);
  const near=(a,b,t)=>Math.abs(a-b)<=(t===undefined?1:t);
  const vis=el=>!!el&&(el.checkVisibility?el.checkVisibility():el.getClientRects().length>0);
  let READ_AOA=null;
  function stubXLSX(){
    window.XLSX={read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:READ_AOA}}}; },
                 utils:{sheet_to_json:function(s){ return s.__aoa; }}};
  }
  function ingest(name,mode,dd,file){
    READ_AOA=AOA;
    PENDING_IMPORT_FILE=file||(name+'.xlsx');
    showMapper(Parse.workbook(new Uint8Array([0])));
    const radio=document.querySelector('input[name="src-mode"][value="'+mode+'"]'); if(radio) radio.checked=true;
    $('cfg-source-name').value=name;
    $('cfg-datadate').value=dd; $('cfg-datadate-main').value=dd;
    DIAG=[]; runIngest();
  }
  function typeProjectNo(v){ const f=$('cfg-projectno'); f.value=v; f.dispatchEvent(new Event('input',{bubbles:true})); }
  function headingText(){ return (document.querySelector('.rpt-hd').innerText||'')+'\n'+($('icon-bar').innerText||''); }
  function weekCovers(col,iso){
    if(col<0||!WE_DATES[col]) return false;
    const d=new Date(iso+'T00:00:00'), we=WE_DATES[col];
    const lo=new Date(we.getFullYear(),we.getMonth(),we.getDate()-6);
    return d>=lo&&d<=we;
  }
"""

MAIN = r"""
(function(){
  const ARGS=__ARGS__;
  const AOA=__AOA__;
""" + COMMON + r"""
  try{ localStorage.clear(); }catch(e){}
  document.head.insertAdjacentHTML('beforeend','<style>*,*::before,*::after{transition:none!important;animation:none!important}</style>');
  window.confirm=function(){ return true; };
  window.addEventListener('load',function(){ setTimeout(async function(){
   try{
    const phone=!!ARGS.phone;
    R.notes.W=window.innerWidth;

    // ================= H: heading =================
    const ht=headingText();
    const leaked=(ht.match(/Project No|Report date|Data date|Activities|Baseline:|Baseline DD|Updated by|tasks ·/gi)||[]);
    ck('H the app heading carries no project details (Project No., Report date, Data date, Activities, Baseline, Updated by)',
       !leaked.length&&ht.indexOf(REPORT_META.projectNo||'103787-13')<0, leaked.join(', '));
    ck('H the tool name and version are not in the header',
       !/Schedule Reporting and Evaluation Tool/.test(ht)&&ht.indexOf(APP_VERSION)<0, ht.slice(0,160));
    const di=$('dirty-indicator');
    di.classList.add('show');
    const ctl=phone?$('btn-more-actions'):$('ib-menu');
    const pr=rc(di), cr=rc(ctl), ib=rc($('icon-bar'));
    ck('H the More actions control is laid out at this width', cr.width>0&&cr.height>0, cr.width+'x'+cr.height);
    ck('H the pill is in the top row (#icon-bar), not on the subtitle line',
       $('icon-bar').contains(di)&&!document.querySelector('.rpt-hd').contains(di));
    ck('H the pill sits left of the More actions control', pr.right<=cr.left+0.5&&cr.left-pr.right<=16,
       Math.round(pr.right)+' vs '+Math.round(cr.left));
    ck('H the pill and the control share the row', near((pr.top+pr.bottom)/2,(cr.top+cr.bottom)/2,3)&&
       pr.top>=ib.top-0.5&&pr.bottom<=ib.bottom+0.5, [pr.top,pr.bottom,cr.top,cr.bottom].map(Math.round).join(','));
    ck('H the pill is the element right before the icon cluster', di.nextElementSibling===$('ib-menu'));
    di.classList.remove('show');

    const lbl=$('ib-label'), foot=$('sd-foot');
    ck('H the tool name and version are at the foot of Data & view',
       !!foot&&$('settings-drawer').contains(foot)&&foot.contains(lbl)&&
       foot===document.querySelector('#settings-drawer .sd-main').lastElementChild);
    ck('H the label reads APP_VERSION', /Schedule Reporting and Evaluation Tool/.test(lbl.textContent)&&
       lbl.textContent.indexOf('v'+APP_VERSION)>=0, lbl.textContent);
    const drawer=$('settings-drawer');
    const tabs=['sources','import','defaults','view','help','about'];
    const seen=[];
    for(const t of tabs){
      setSettingsTab(t); toggleSettingsDrawer(true); await settle();
      const fr=rc(foot), dr=rc(drawer);
      const hit=document.elementFromPoint((fr.left+fr.right)/2,(fr.top+fr.bottom)/2);
      if(vis(foot)&&fr.height>0&&near(fr.bottom,Math.min(dr.bottom,window.innerHeight),1.5)&&hit&&foot.contains(hit)) seen.push(t);
    }
    ck('H the foot is visible at the bottom of the panel in every section', seen.length===tabs.length, seen.join(','));
    toggleSettingsDrawer(false); await settle();

    // ================= B: info bar =================
    const cell=$('info-cell'), sib=$('sib'), L=$('sib-left'), Rt=$('sib-right'), sw=$('scroll-wrap');
    // Re-read after anything that rebuilds the header: a rerender replaces the month cells.
    const moCell=()=>document.querySelector('#phase-hdr th.mo-band');
    let mo=moCell();
    const nm=document.querySelector('#week-hdr th.c-name');
    const wk0=Array.prototype.find.call(document.querySelectorAll('#week-hdr th.col-wk'),function(t){ return rc(t).width>0; });
    ck('B the bar is the first row of the board header', cell&&cell.closest('thead')&&
       cell.parentElement===document.querySelector('#main-table thead tr'));
    ck('B the bar sits directly above the month row', near(rc(cell).bottom,rc(mo).top), rc(cell).bottom+' vs '+rc(mo).top);
    if(!phone){
      // On a phone the left part takes the whole first line (M below).
      ck('B its left part aligns with the frozen label column', near(rc(L).left,rc(nm).left)&&near(rc(L).right,rc(nm).right),
         [rc(L).left,rc(L).right,rc(nm).left,rc(nm).right].map(Math.round).join(','));
      ck('B its right part starts over the timeline', near(rc(Rt).left,rc(wk0).left), Math.round(rc(Rt).left)+' vs '+Math.round(rc(wk0).left));
      const swRight=rc(sw).left+sw.clientLeft+sw.clientWidth;
      ck('B its right part ends at the board\'s visible edge', near(rc(Rt).right,swRight), Math.round(rc(Rt).right)+' vs '+Math.round(swRight)+' sib '+Math.round(rc(sib).right)+' var '+document.documentElement.style.getPropertyValue('--sib-w')+' cw '+sw.clientWidth);
      const colsShown=Array.prototype.filter.call(document.querySelectorAll('#main-table colgroup col'),function(c){ return cs(c).display!=='none'; }).length;
      ck('B the bar spans every laid-out column', cell.colSpan===colsShown, cell.colSpan+' / '+colsShown);
    }
    // Vertical scroll: the bar element itself, not its row.
    sw.scrollTop=0; await settle();
    const firstRow=document.querySelector('#tbody tr.data');
    const t0=rc(cell).top, s0=rc(sib).top, r0=rc(firstRow).top;
    sw.scrollTop=600; await settle();
    ck('B the board really scrolled', sw.scrollTop>100&&rc(firstRow).top<r0-100, sw.scrollTop);
    ck('B sticky: the bar cell stays put on vertical scroll', near(rc(cell).top,t0), t0+' -> '+rc(cell).top);
    ck('B sticky: the bar strip stays put on vertical scroll', near(rc(sib).top,s0), s0+' -> '+rc(sib).top);
    ck('B sticky: the month row stays directly under the bar', near(rc(cell).bottom,rc(mo).top), rc(cell).bottom+' vs '+rc(mo).top);
    // Horizontal scroll: the strip and the frozen column both hold.
    const l0=rc(L).left, n0=rc(nm).left, rr0=rc(Rt).right, fc=document.querySelector('#tbody tr.data td.c-name'), f0=rc(fc).left;
    sw.scrollLeft=400; await settle();
    ck('B the board really scrolled sideways', sw.scrollLeft>100, sw.scrollLeft);
    ck('B sideways: the bar\'s left part stays over the label column', near(rc(L).left,l0)&&near(rc(L).left,rc(nm).left), l0+' -> '+rc(L).left);
    ck('B sideways: the frozen label column still holds (header and body)', near(rc(nm).left,n0)&&near(rc(fc).left,f0),
       [n0,rc(nm).left,f0,rc(fc).left].map(Math.round).join(','));
    ck('B sideways: the bar\'s right part stays on screen', near(rc(Rt).right,rr0), rr0+' -> '+rc(Rt).right);
    sw.scrollLeft=0; sw.scrollTop=0; await settle();

    const txt=sib.innerText;
    ck('B the seeded project number comes from the store', REPORT_META.projectNo==='103787-13'&&
       $('meta-projectno')&&$('meta-projectno').textContent==='103787-13', REPORT_META.projectNo);
    ck('B the bar shows the project number, the report date and its W/E',
       txt.indexOf('103787-13')>=0&&txt.indexOf(fmtTipDate(REPORT_META.reportDate))>=0&&txt.indexOf(fmtPeriod(reportPeriodISO()))>=0,
       txt.replace(/\s+/g,' ').slice(0,160));
    const meta=$('sib-meta').textContent;
    ck('B the right-hand meta carries baseline, counts and updated by',
       meta.indexOf(TASKS.length+' tasks')>=0&&meta.indexOf(MILESTONES.length+' milestones')>=0&&
       /updated by Matthew Garrett/.test(meta)&&meta.indexOf(BASELINE_LABEL_TEXT)>=0, meta);
    ck('B the meta is right-aligned in the bar', near(rc($('sib-meta')).right+parseFloat(cs(Rt).paddingRight),rc(Rt).right,1.5)||phone,
       rc($('sib-meta')).right+' vs '+rc(Rt).right);
    const seedChips=Rt.querySelectorAll('.sib-chip');
    ck('B unimported: one chip, the embedded baseline, current, with its data date',
       seedChips.length===1&&seedChips[0].classList.contains('is-current')&&
       seedChips[0].textContent.indexOf('DD '+fmtTipDate(BASELINE_SOURCE.dataDate))>=0, seedChips.length&&seedChips[0].textContent);
    const dd0=document.querySelectorAll('#week-hdr th.dd-wk');
    ck('B unimported: the baseline data-date week is tinted',
       dd0.length===1&&weekCovers(+dd0[0].getAttribute('data-col'),isoDay(BASELINE_SOURCE.dataDate)), dd0.length);

    stubXLSX();
    if(!phone){
      // ================= P: project number =================
      typeProjectNo('777-1'); await settle();
      ck('P editing the field updates the bar', REPORT_META.projectNo==='777-1'&&$('meta-projectno')&&$('meta-projectno').textContent==='777-1',
         $('meta-projectno')&&$('meta-projectno').textContent);
      ck('P the field lives in Data & view > Data settings', !!$('cfg-projectno').closest('#sd-panel-defaults'));
      typeProjectNo(''); await settle();
      const link=$('sib-pn-set');
      ck('P blank shows "Project No. not set"', /Project No\. not set/.test(sib.innerText)&&!!link&&!$('meta-projectno'), sib.innerText.slice(0,80));
      toggleSettingsDrawer(false); setSettingsTab('sources'); await settle();
      link.click(); await settle();
      ck('P its link opens Data settings on the field', drawer.classList.contains('open')&&SETTINGS_TAB==='defaults'&&
         !$('sd-panel-defaults').hidden&&document.activeElement===$('cfg-projectno'), SETTINGS_TAB+' '+(document.activeElement&&document.activeElement.id));
      // Auto-fill, only into an empty field.
      ingest('Auto one','replace','2026-08-29','123456-7_Something.xlsx'); await settle();
      setSettingsTab('defaults'); toggleSettingsDrawer(true); await settle();
      const hint=$('cfg-projectno-hint');
      ck('P an import into an empty field fills it from the file name', REPORT_META.projectNo==='123456-7'&&
         $('cfg-projectno').value==='123456-7'&&$('meta-projectno')&&$('meta-projectno').textContent==='123456-7', REPORT_META.projectNo);
      ck('P it is marked "from file name"', !hint.hidden&&vis(hint)&&/from file name/.test(hint.textContent)&&
         rc(hint).left>=rc($('cfg-projectno')).right-1, hint.hidden);
      ingest('Auto two','append','2026-09-05','999999-1_Other.xlsx'); await settle();
      ck('P a second import does not overwrite an auto-filled value', REPORT_META.projectNo==='123456-7', REPORT_META.projectNo);
      hint.querySelector('button').click(); await settle();
      ck('P OK confirms it: the hint goes, the value stays', hint.hidden&&REPORT_META.projectNo==='123456-7');
      typeProjectNo('555-5'); await settle();
      ingest('Auto three','append','2026-09-12','888888-2_X.xlsx'); await settle();
      ck('P an import never overwrites a value the user set', REPORT_META.projectNo==='555-5'&&$('cfg-projectno').value==='555-5'&&hint.hidden,
         REPORT_META.projectNo);
      typeProjectNo(''); await settle();
      ingest('Auto four','replace','2026-08-29','123456-7_Something.xlsx'); await settle();
      ck('P blank again: auto-fill with the hint', REPORT_META.projectNo==='123456-7'&&!hint.hidden);
      typeProjectNo('123456-8'); await settle();
      ck('P editing clears the hint', hint.hidden&&REPORT_META.projectNo==='123456-8');
      ingest('Pasted','append','2026-09-05','User update - 2026-09-29'); await settle();
      ck('P a name with no leading number fills nothing', REPORT_META.projectNo==='123456-8');
      toggleSettingsDrawer(false); await settle();
    }

    // ================= C: chips, N=3 =================
    const names=phone?['Weekly update schedule A','Weekly update schedule B','Weekly update schedule C']:['Src A','Src B','Src C'];
    ingest(names[0],'replace','2026-08-29'); await settle();
    ingest(names[1],'append','2026-09-05'); await settle();
    ingest(names[2],'append','2026-09-12'); await settle();
    rerender(true); await settle();
    let chips=Array.prototype.slice.call(Rt.querySelectorAll('.sib-chip'));
    ck('C three loaded schedules give three chips', PRIMARY_SOURCES.length===3&&chips.length===3, PRIMARY_SOURCES.length+'/'+chips.length);
    const wantDD=['29-Aug-26','05-Sep-26','12-Sep-26'];
    ck('C each chip carries its schedule name and data date', chips.length===3&&chips.every(function(c,i){
         return c.textContent===names[i]+' · DD '+wantDD[i]; }), chips.map(function(c){ return c.textContent; }).join(' | '));
    const cur=function(){ return chips.filter(function(c){ return c.classList.contains('is-current'); }); };
    ck('C exactly one chip is current: the latest data date', cur().length===1&&cur()[0]===chips[2], cur().length);
    ck('C the current chip is highlighted', cs(chips[2]).backgroundColor!==cs(chips[0]).backgroundColor, cs(chips[2]).backgroundColor);
    let ddw=document.querySelectorAll('#week-hdr th.dd-wk');
    ck('C the current data-date week is tinted, and only it', ddw.length===1&&weekCovers(+ddw[0].getAttribute('data-col'),'2026-09-12')&&
       cs(ddw[0]).backgroundColor!==cs(document.querySelector('#week-hdr th.col-wk:not(.dd-wk):not(.now-wk):not(.past-wk)')||ddw[0]).backgroundColor,
       ddw.length&&ddw[0].textContent);
    const B=PRIMARY_SOURCES[1], Cs=PRIMARY_SOURCES[2];
    toggleSourceEnabled(B.id); await settle();
    chips=Array.prototype.slice.call(Rt.querySelectorAll('.sib-chip'));
    ck('C a disabled schedule\'s chip is dimmed', chips[1].classList.contains('is-off')&&parseFloat(cs(chips[1]).opacity)<0.8&&
       parseFloat(cs(chips[0]).opacity)===1, cs(chips[1]).opacity);
    ck('C still exactly one current with one off', cur().length===1&&cur()[0]===chips[2]);
    toggleSourceEnabled(Cs.id); await settle();
    chips=Array.prototype.slice.call(Rt.querySelectorAll('.sib-chip'));
    ddw=document.querySelectorAll('#week-hdr th.dd-wk');
    ck('C with the latest off, current moves to the latest enabled, and the tint with it',
       cur().length===1&&cur()[0]===chips[0]&&ddw.length===1&&weekCovers(+ddw[0].getAttribute('data-col'),'2026-08-29'),
       cur().map(function(c){ return c.textContent; }).join());
    toggleSourceEnabled(B.id); toggleSourceEnabled(Cs.id); await settle();
    chips=Array.prototype.slice.call(Rt.querySelectorAll('.sib-chip'));
    const before=PRIMARY_SOURCES.map(function(s){ return s.enabled; }).join();
    toggleSettingsDrawer(false); setSettingsTab('defaults'); await settle();
    chips[1].click(); await settle();
    ck('C clicking a chip opens Data & view > Sources', drawer.classList.contains('open')&&SETTINGS_TAB==='sources'&&
       !$('sd-panel-sources').hidden, SETTINGS_TAB);
    ck('C a chip is display only: nothing is toggled', PRIMARY_SOURCES.map(function(s){ return s.enabled; }).join()===before);
    toggleSettingsDrawer(false); await settle();

    if(phone){
      // ================= M: phone =================
      const sr=rc(sib);
      const parts=Array.prototype.slice.call(sib.querySelectorAll('.sib-item,.sib-chip,.sib-meta')).filter(function(e){ return rc(e).width>0; });
      const tops=[];
      parts.forEach(function(e){ const t=rc(e).top; if(!tops.some(function(x){ return Math.abs(x-t)<4; })) tops.push(t); });
      ck('M the bar wraps to at most two lines', tops.length<=2&&tops.length>=1, tops.map(Math.round).join(','));
      ck('M line one is the project and report date, line two the chips', rc(L).bottom<=rc(Rt).top+1&&rc(L).width>=sr.width-1,
         [rc(L).bottom,rc(Rt).top].map(Math.round).join(' / '));
      ck('M the bar fits the screen', sr.left>=-0.5&&sr.right<=window.innerWidth+0.5, sr.left+'..'+sr.right);
      ck('M the chips overflow and scroll inside the bar', Rt.scrollWidth>Rt.clientWidth+1&&/auto|scroll/.test(cs(Rt).overflowX),
         Rt.scrollWidth+'/'+Rt.clientWidth+' '+cs(Rt).overflowX);
      Rt.scrollLeft=80; await settle();
      ck('M the chips row really scrolls sideways', Rt.scrollLeft>0, Rt.scrollLeft);
      Rt.scrollLeft=0;
      const de=document.documentElement;
      ck('M the page body has no horizontal scroll', de.scrollWidth<=window.innerWidth&&document.body.scrollWidth<=window.innerWidth,
         de.scrollWidth+'/'+document.body.scrollWidth+'/'+window.innerWidth);
      mo=moCell();
      ck('M the bar still sits directly above the month row', near(rc(cell).bottom,rc(mo).top), rc(cell).bottom+' vs '+rc(mo).top);
    } else {
      // ================= X: print preview =================
      typeProjectNo('P64-PRINT'); await settle();
      togglePrintMode(true); await settle(); mo=moCell();
      const pc=rc(cell);
      ck('X print preview: the bar is present', document.body.classList.contains('print-mode')&&vis(cell)&&pc.height>0&&
         $('page-frame').contains(cell), pc.height);
      ck('X print preview: directly above the month row', near(pc.bottom,rc(mo).top), pc.bottom+' vs '+rc(mo).top);
      ck('X print preview: it shows the project number and the chips', sib.innerText.indexOf('P64-PRINT')>=0&&
         Rt.querySelectorAll('.sib-chip').length===3);
      togglePrintMode(false); await settle();
    }
   }catch(e){ ck('probe ran without throwing', false, e&&e.stack||e); }
   emit();
  },900); });
})();
"""

# Publish and model export, set and blank.
STAGE1 = r"""
(function(){
  const ARGS={tag:'R1'};
""" + COMMON + r"""
  // Captured synchronously at the Blob constructor: publish and the model
  // export both build their Blob from one string. Reading a Blob back with
  // text() is real I/O that the virtual-time budget can run out on.
  const CAP={}; let capName=null;
  const RealBlob=window.Blob;
  window.Blob=function(parts,opts){ if(capName) CAP[capName]=parts.join(''); return new RealBlob(parts,opts); };
  URL.createObjectURL=function(){ return 'blob:captured'; };
  HTMLAnchorElement.prototype.click=function(){};
  window.confirm=function(){ return true; };
  window.addEventListener('load',function(){ setTimeout(async function(){
   try{
    typeProjectNo('424242-9'); await settle();
    ck('the field set the store', REPORT_META.projectNo==='424242-9');
    capName='model'; exportModel();
    capName='published'; publishDashboard();
    capName=null; await settle();
    typeProjectNo(''); await settle();
    capName='blank'; publishDashboard();
    capName=null;
    for(const n of ['model','published','blank']){
      if(CAP[n]) R.cap[n]=CAP[n]; else ck('captured '+n,false);
    }
   }catch(e){ ck('stage 1 ran without throwing', false, e&&e.stack||e); }
   emit();
  },900); });
})();
"""

# Reads a published file back.
STAGE2 = r"""
(function(){
  const ARGS={tag:'__TAG__'};
  const WANT=__WANT__;
""" + COMMON + r"""
  window.addEventListener('load',function(){ setTimeout(async function(){
   try{
    const txt=$('sib').innerText;
    if(WANT){
      ck('the project number survives the round trip', REPORT_META.projectNo===WANT&&$('meta-projectno')&&
         $('meta-projectno').textContent===WANT&&$('cfg-projectno').value===WANT, REPORT_META.projectNo);
      ck('the published bar shows it', txt.indexOf(WANT)>=0&&$('info-cell').getBoundingClientRect().height>0, txt.slice(0,80));
    } else {
      ck('a blank project number stays blank', REPORT_META.projectNo===''&&/Project No\. not set/.test(txt)&&!!$('sib-pn-set'),
         JSON.stringify(REPORT_META.projectNo));
    }
    ck('the published file shows the report date and its W/E', txt.indexOf(fmtTipDate(REPORT_META.reportDate))>=0&&
       txt.indexOf(fmtPeriod(reportPeriodISO()))>=0);
    ck('the published file has one current chip', $('sib-right').querySelectorAll('.sib-chip.is-current').length===1);
   }catch(e){ ck('stage 2 ran without throwing', false, e&&e.stack||e); }
   emit();
  },900); });
})();
"""

# Mounts the exported model (and an old one without the field) on a clean app.
STAGE3 = r"""
(function(){
  const ARGS={tag:'R3'};
  const P=__MODEL__;
""" + COMMON + r"""
  window.addEventListener('load',function(){ setTimeout(async function(){
   try{
    const v=validateModelPayload(JSON.stringify(P),'model.json');
    ck('the exported model carries projectNo and validates', P.projectNo==='424242-9'&&v.ok, v.errors.join('; '));
    const rm=ANNOT_CATEGORIES.filter(function(c){ return c.key==='reportMeta'; })[0];
    ck('the report meta category counts the project number', rm&&rm.count(P)===3, rm&&rm.count(P));
    typeProjectNo(''); await settle();
    ANNOT_CATEGORIES.forEach(function(c){ c.apply(P); });
    scheduleRerender(true); await settle(); await settle();
    ck('mounting the model restores the project number', REPORT_META.projectNo==='424242-9'&&
       $('meta-projectno')&&$('meta-projectno').textContent==='424242-9'&&$('cfg-projectno').value==='424242-9', REPORT_META.projectNo);
    // An old export has no projectNo at all.
    const old=JSON.parse(JSON.stringify(P)); delete old.projectNo;
    typeProjectNo('SET-1'); await settle();
    const v2=validateModelPayload(JSON.stringify(old),'old.json');
    ck('an old model without it still validates', v2.ok, v2.errors.join('; '));
    ck('and its report meta count is the title and date only', rm.count(old)===2, rm.count(old));
    let threw=null;
    try{ ANNOT_CATEGORIES.forEach(function(c){ c.apply(old); }); }catch(e){ threw=e.message; }
    scheduleRerender(true); await settle(); await settle();
    ck('mounting an old model breaks nothing and keeps the number that is set', !threw&&REPORT_META.projectNo==='SET-1'&&
       $('meta-projectno')&&$('meta-projectno').textContent==='SET-1', threw||REPORT_META.projectNo);
   }catch(e){ ck('stage 3 ran without throwing', false, e&&e.stack||e); }
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
                          f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=90000",
                          "--dump-dom", "file://" + path],
                         capture_output=True, text=True, timeout=400).stdout
    hits = OUT_RE.findall(out)
    if not hits:
        return {"checks": [{"name": f"[{size[0]}] probe produced output", "pass": False, "detail": ""}], "cap": {}}
    return json.loads(base64.b64decode(hits[-1]).decode("utf-8"))


def inject(html: str, script: str) -> str:
    return html.replace("</body>", "<script>\n" + script + "\n</script>\n</body>", 1)


def source_checks(src: str) -> list:
    out = []

    def ck(name, ok, detail=""):
        out.append({"name": "[source] " + name, "pass": bool(ok), "detail": str(detail)})

    for t in ("</body>", "<head>", "</head>", "</html>"):
        ck(f"the page holds exactly one {t}", src.count(t) == 1, src.count(t))
    ck("version grep returns 1", len(re.findall(r"3\.[0-9]*\.[0-9]*-P", src)) == 1)
    m = re.search(r"const APP_VERSION='3\.1\.0-P(\d+)';", src)
    ck("APP_VERSION is 3.1.0-P64 or a later partial", bool(m) and int(m.group(1)) >= 64, m and m.group(0))
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", src, re.S)
    ck("no literal script start tag inside any script", not any(re.search(r"<script", s, re.I) for s in scripts))
    markup = re.sub(r"<script[^>]*>.*?</script>", "", src, flags=re.S)
    markup = re.sub(r"<!--.*?-->", "", markup, flags=re.S)
    ck("the project number is not a literal in the markup", "103787-13" not in markup.replace(
        "103787-13_Eskay", ""), markup.count("103787-13"))
    ck("the markup has no Project No. literal in the heading", "Project No.: <b>" not in src)
    a = src.find("// P64 (TD-224): projectNo joins the report meta.")
    b = src.find("function openProjectNoField(", a)
    c = src.find("// P64 (TD-224): SCHEDULE INFO BAR")
    d = src.find("function watchInfoBar(", c)
    blocks = (src[a:b] if a >= 0 and b > a else "") + (src[c:d] if c >= 0 and d > c else "")
    ck("the P64 blocks are present", a >= 0 and c >= 0 and b > a and d > c)
    strings = re.findall(r"'([^'\n]*)'", blocks)
    bad = [s for s in strings if "—" in s or "–" in s or "\\u2014" in s or "\\u2013" in s]
    ck("no em or en dash in the P64 user strings", not bad, bad)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    aoa = json.dumps(build_aoa(XLSX))
    checks = source_checks(src)

    for tag, size, phone in (("1440", (1440, 900), False), ("390", (390, 844), True)):
        args = json.dumps({"tag": tag, "phone": phone})
        probe = MAIN.replace("__ARGS__", args).replace("__AOA__", aoa)
        checks += render(inject(src, probe), size)["checks"]

    s1 = render(inject(src, STAGE1), (1440, 900))
    checks += s1["checks"]
    cap = s1.get("cap", {})
    if all(k in cap for k in ("model", "published", "blank")):
        model = json.loads(cap["model"])
        checks.append({"name": "[R1] the model export carries projectNo", "pass": model.get("projectNo") == "424242-9",
                       "detail": model.get("projectNo")})
        pub = cap["published"]
        checks.append({"name": "[R1] the publish payload carries projectNo",
                       "pass": '"projectNo":"424242-9"' in pub, "detail": ""})
        stage2 = STAGE2.replace("__TAG__", "R2 publish").replace("__WANT__", json.dumps("424242-9"))
        checks += render(inject(pub, stage2), (1440, 900))["checks"]
        stage2b = STAGE2.replace("__TAG__", "R2 blank").replace("__WANT__", json.dumps(""))
        checks += render(inject(cap["blank"], stage2b), (1440, 900))["checks"]
        # A file published before P64: no projectNo in its state block.
        oldpub = re.sub(r'"projectNo":"[^"]*",', "", pub)
        oldpub = re.sub(r'"projectNoFromFile":(?:true|false),', "", oldpub)
        checks.append({"name": "[R2 old] the stripped payload really has no projectNo",
                       "pass": '"projectNo"' not in oldpub and '"projectNoFromFile"' not in oldpub, "detail": ""})
        stage2c = STAGE2.replace("__TAG__", "R2 old publish").replace("__WANT__", json.dumps("103787-13"))
        checks += render(inject(oldpub, stage2c), (1440, 900))["checks"]
        stage3 = STAGE3.replace("__MODEL__", cap["model"].replace("</", "<\\/"))
        checks += render(inject(src, stage3), (1440, 900))["checks"]
    else:
        checks.append({"name": "[R1] publish and model export were captured", "pass": False, "detail": list(cap)})

    fails = 0
    for c in checks:
        ok = c["pass"]
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + c["name"] + ("" if ok else f"  ({c['detail']})"))
    print(f"\n{len(checks) - fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
