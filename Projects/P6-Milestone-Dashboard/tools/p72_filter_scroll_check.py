#!/usr/bin/env python3
"""
p72_filter_scroll_check: the collapsible phone filter panel and the screen
heading that scrolls away (P72, Matt 2026-10-01; his phone screenshots are
the brief, the P67 phone shape is the starting point).

Drives the REAL app in headless Chromium (network unresolvable) and reads
classList, attributes, computed style and getBoundingClientRect of the
elements themselves, never a screenshot. Scrolling is the real thing: the
board's scrollTop is moved in steps, the browser dispatches its own scroll
events, and the probe waits before measuring.

A. Phone filter panel (max-width:767px), at 390x844 and 767 (1px inside):
  - collapsed by default: the only controls showing in the bar are the search
    field and the funnel, which sits inside the field's right end;
  - the funnel reports aria-expanded and looks pressed while open; the state
    is stored as display state and a fresh load of the page reads it back;
  - expanded, row 1 is Weeks, Mode, Fit (tops within 4px, left to right),
    row 2 is Status, Float, Notes and the clear x on one line, then Banding,
    Source and Activity ID(s) below;
  - a dot shows on the funnel while a hidden filter is set (status, float,
    notes, week range, banding, IDs), not while expanded, not once cleared;
  - the header toggle (#btn-filter-expand) hides and shows the whole bar at
    every width;
  - filters behave as before: three filter combinations (statuses; status plus float; banding plus status) set through the
    phone dropdowns give the same visible marker count as the same filters
    set on desktop (compared across every run below).
  At 768 and up the desktop row is unchanged: no funnel, the date tile back
  in .fb-top beside Find.

B. The heading scrolls away (max-width:1023px, CHROME_AWAY_MQ), at 390, 767,
   768 and 1023 (1px inside); unchanged at 1024 (1px outside) and 1440:
  - scrolling the board down hides the icon bar, the heading, the filter bar
    and the info rows (out of view or visibility:hidden, by their rects), and
    the month and week band cells sit at the top of the viewport (month top
    within 2px of 0, week top within 2px of the month band's bottom); they
    stay there scrolling further (sticky); also from a window already
    scrolled part way;
  - scrolling up brings everything back where it was;
  - an open dropdown, the week-range popover or the milestone card blocks
    any change (and the card, position:fixed, does not move);
  - prefers-reduced-motion: no transition class is ever set (the 390 dark
    run is launched with --force-prefers-reduced-motion);
  - no horizontal page scroll anywhere.

Usage:
  python3 tools/p72_filter_scroll_check.py [--html FILE]
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

# (width, height, theme, filter shape, scroll-away expected, reduced motion)
RUNS = [
    (390, 844, "light", "phone", True, False),
    (390, 844, "dark", "phone", True, True),
    (767, 900, "light", "phone", True, False),   # 1px inside the phone breakpoint
    (768, 900, "light", "desk", True, False),    # 1px outside it; still narrow
    (1023, 768, "light", "desk", True, False),   # 1px inside the scroll-away query
    (1024, 768, "light", "desk", False, False),  # 1px outside it
    (1440, 900, "light", "desk", False, False),
    (1440, 900, "dark", "desk", False, False),
]

PROBE = r"""
(async function(ARGS){
  if(window.top!==window) return;   // the persistence iframe loads this page too
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p72-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=(ms)=>new Promise(r=>setTimeout(r,ms||200));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const cs=el=>getComputedStyle(el);
  const shown=el=>!!el&&el.getClientRects().length>0&&rc(el).width>0&&rc(el).height>0&&cs(el).visibility!=='hidden';
  const within=(o,i)=>i.left>=o.left-0.5&&i.right<=o.right+0.5&&i.top>=o.top-0.5&&i.bottom<=o.bottom+0.5;
  const noHScroll=()=>document.documentElement.scrollWidth<=window.innerWidth+1;
  const markerCount=()=>Array.prototype.filter.call(document.querySelectorAll('#tbody .m-wrap[data-ms]'),function(w){
    const tr=w.closest('tr'); return tr&&!tr.classList.contains('hidden-row')&&cs(tr).display!=='none'; }).length;
  const f1=v=>Math.round(v*10)/10;
  const html=document.documentElement;
  try{
    html.setAttribute('data-theme',ARGS.theme);
    // End states are measured with the transitions off: headless virtual time
    // does not reliably advance a CSS transition between two timers. The
    // classes and the timers that drive them are untouched.
    const noAnim=document.createElement('style');
    noAnim.textContent='#top-filter-bar,#icon-bar,.ws-toggle,.rpt-hd,#scroll-wrap,thead th{transition:none!important}';
    document.head.appendChild(noAnim);
    toggleTopFilterBar(true); await settle(300);
    const bar=$('top-filter-bar'), sw=$('scroll-wrap');
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight+' '+ARGS.theme+(ARGS.reduce?' reduced-motion':'');

    // ================= A. the filter panel =================
    const fun=$('fb-find-more-btn'), title=$('filter-title'), fw=title.closest('.ds-fwrap');
    const find=$('tfb-find'), when=$('tfb-when');
    const tg=$('btn-filter-expand');
    tg.click(); await settle(300);
    ck('header toggle: hides the whole bar', !bar.classList.contains('open')&&rc(bar).height<2&&tg.getAttribute('aria-expanded')==='false', rc(bar).height);
    tg.click(); await settle(300);
    ck('header toggle: shows it again', bar.classList.contains('open')&&rc(bar).height>20&&tg.getAttribute('aria-expanded')==='true', rc(bar).height);

    if(ARGS.shape==='phone'){
      try{ localStorage.removeItem('sret-fb-find-more'); }catch(e){}
      setFindMore(false); await settle();
      const ctrls=Array.prototype.filter.call(bar.querySelectorAll('button,input,select,[role=button]'),shown);
      ck('collapsed: only the search field and the funnel show in the bar',
         ctrls.length===2&&ctrls.indexOf(title)>=0&&ctrls.indexOf(fun)>=0, ctrls.map(function(c){ return c.id||c.className; }).join('|'));
      ck('collapsed: the date tile, its rows and the summary line are hidden',
         !shown(when)&&!shown($('wr-field'))&&!shown($('fb-dd-status-trig'))&&!shown($('btn-clear-crit'))&&!shown($('filter-band'))&&!shown($('filter-ids'))&&!shown(bar.querySelector('.fb-foot')), '');
      ck('funnel: inside the search field, at its right end',
         shown(fun)&&within(rc(fw),rc(fun))&&rc(fw).right-rc(fun).right<=4, JSON.stringify([f1(rc(fw).right),f1(rc(fun).right)]));
      ck('funnel: a funnel icon (svg path), not the old chevron glyph',
         !!fun.querySelector('svg path')&&!/▾/.test(fun.textContent), fun.textContent);
      ck('funnel: the --icon-btn square', Math.abs(rc(fun).width-parseFloat(cs(html).getPropertyValue('--icon-btn')))<=0.5, rc(fun).width);
      ck('funnel: collapsed reads aria-expanded=false', fun.getAttribute('aria-expanded')==='false', fun.getAttribute('aria-expanded'));
      const bgClosed=cs(fun).backgroundColor;
      const clr=$('sticky-title-clear'); clr.style.display='inline-flex';
      ck('funnel: the title clear sits left of it, both inside the field', rc(clr).right<=rc(fun).left+0.5&&within(rc(title),rc(clr)), '');
      clr.style.display='none';
      ck('no horizontal page scroll (collapsed)', noHScroll(), document.documentElement.scrollWidth);

      fun.click(); await settle(300);
      let stored=null; try{ stored=localStorage.getItem('sret-fb-find-more'); }catch(e){}
      ck('funnel: expanded reads aria-expanded=true', fun.getAttribute('aria-expanded')==='true', '');
      ck('funnel: looks pressed while open (background differs)', cs(fun).backgroundColor!==bgClosed, bgClosed+' vs '+cs(fun).backgroundColor);
      ck('funnel: the open state is stored as display state', stored==='open', stored);
      ck('expanded: the date tile sits inside Find, right after the search field (DOM order = visual order)',
         find.contains(when)&&fw.nextElementSibling===when, when.parentElement&&when.parentElement.className);
      const wr=$('wr-field'), seg=$('wr-mode-seg'), fit=$('btn-fit-screen-inline');
      const row1=[wr,seg,fit];
      ck('row 1: Weeks, Mode and Fit show', row1.every(shown), '');
      ck('row 1: tops within 4px', Math.max.apply(null,row1.map(function(e){ return rc(e).top; }))-Math.min.apply(null,row1.map(function(e){ return rc(e).top; }))<=4,
         row1.map(function(e){ return f1(rc(e).top); }).join('/'));
      ck('row 1: left to right Weeks, Mode, Fit, inside the bar',
         rc(wr).right<=rc(seg).left+0.5&&rc(seg).right<=rc(fit).left+0.5&&rc(fit).right<=rc(bar).right+0.5, row1.map(function(e){ return f1(rc(e).left); }).join('/'));
      ck('row 1: below the search field', rc(wr).top>=rc(fw).bottom-0.5, '');
      const st=$('fb-dd-status-trig'), fl=$('fb-dd-float-trig'), nt=$('fb-dd-annot-trig'), x=$('btn-clear-crit');
      const row2=[st,fl,nt,x];
      ck('row 2: Status, Float, Notes and the clear x show', row2.every(shown), '');
      ck('row 2: one line (tops within 4px), the x inline at its end',
         Math.max.apply(null,row2.map(function(e){ return rc(e).top; }))-Math.min.apply(null,row2.map(function(e){ return rc(e).top; }))<=4&&
         rc(st).right<=rc(fl).left+0.5&&rc(fl).right<=rc(nt).left+0.5&&rc(nt).right<=rc(x).left+0.5,
         row2.map(function(e){ return f1(rc(e).left)+','+f1(rc(e).top); }).join(' '));
      ck('row 2: below row 1', rc(st).top>=Math.max(rc(wr).bottom,rc(seg).bottom,rc(fit).bottom)-0.5, '');
      ck('then Banding and Activity ID(s), below row 2',
         shown($('filter-band'))&&shown($('filter-ids'))&&rc($('filter-band')).top>=rc(x).bottom-0.5&&rc($('filter-ids')).top>=rc($('filter-band')).bottom-0.5, '');
      const src=$('tfb-source-group');
      src.style.display=''; await settle();
      ck('Source (when shown) shares Banding\'s row, after it', shown($('filter-source'))&&Math.abs(rc($('filter-source')).top-rc($('filter-band')).top)<=4&&rc($('filter-source')).left>=rc($('filter-band')).right-0.5,
         f1(rc($('filter-source')).top)+'/'+f1(rc($('filter-band')).top));
      src.style.display='none'; await settle();
      ck('expanded: section labels stay hidden, accessible names stay',
         !shown(find.querySelector('.fb-title'))&&!shown(when.querySelector('.fb-title'))&&!shown($('wr-field-label'))&&
         title.getAttribute('aria-label')==='Activity name'&&!!when.getAttribute('aria-label')&&!!$('tfb-crit').getAttribute('aria-label'), '');
      ck('expanded: the bar is not clipped', parseFloat(cs(bar).maxHeight)>=bar.scrollHeight-1, cs(bar).maxHeight+' vs '+bar.scrollHeight);
      ck('no horizontal page scroll (expanded)', noHScroll(), document.documentElement.scrollWidth);

      // A long week range must not push Fit onto a second line.
      if(typeof WE_DATES!=='undefined'&&WE_DATES.length>6){ applyWeekRange(2,5); await settle(); }
      ck('row 1: still one line with a week range set', Math.abs(rc(wr).top-rc(fit).top)<=4&&rc(fit).right<=rc(bar).right+0.5,
         f1(rc(wr).top)+'/'+f1(rc(fit).top)+' '+wr.textContent.trim());
      clearWeekRange(); await settle();

      // ---- persistence: a fresh load of the page reads the stored state ----
      const fr=document.createElement('iframe');
      fr.style.cssText='position:fixed;left:0;top:0;width:390px;height:600px;opacity:0;pointer-events:none;border:0';
      fr.src=location.href;
      document.body.appendChild(fr);
      await new Promise(function(res){ fr.onload=res; setTimeout(res,20000); });
      await settle(800);
      let reOpen=null;
      try{ const d=fr.contentDocument; reOpen=d.getElementById('tfb-find').classList.contains('fb-more-open')&&d.getElementById('fb-find-more-btn').getAttribute('aria-expanded')==='true'; }catch(e){ reOpen='err '+e; }
      ck('persistence: a fresh load opens expanded after "open" was stored', reOpen===true, reOpen);
      setFindMore(false); await settle();
      try{ fr.contentWindow.location.reload(); }catch(e){}
      await new Promise(function(res){ fr.onload=res; setTimeout(res,20000); });
      await settle(800);
      try{ const d=fr.contentDocument; reOpen=d.getElementById('tfb-find').classList.contains('fb-more-open'); }catch(e){ reOpen='err '+e; }
      ck('persistence: and collapsed after "closed" was stored', reOpen===false, reOpen);
      fr.remove();

      // ---- the dot, N=3 and more: each hidden filter alone ----
      const dotOn=()=>fun.classList.contains('has-dot')&&shown(fun.querySelector('.fb-dot'));
      setFindMore(false); await settle();
      ck('dot: none with no filter set', !dotOn(), '');
      const cases=[
        ['status',function(){ toggleStatusFilter('CRIT'); },function(){ clearCriticalFilters(); }],
        ['float',function(){ setFloatPreset('lt10d'); },function(){ setFloatPreset('any'); }],
        ['notes',function(){ setAnnotFilter('edited'); },function(){ setAnnotFilter('any'); }],
        ['week range',function(){ applyWeekRange(2,5); },function(){ clearWeekRange(); }],
        ['banding',function(){ const b=$('filter-band'); const o=Array.prototype.find.call(b.options,function(o){ return o.value; }); if(o){ b.value=o.value; applyFilter(); } },function(){ $('filter-band').value=''; applyFilter(); }],
        ['activity IDs',function(){ $('filter-ids').value='ZZ-NOT-AN-ID'; applyFilter(); },function(){ clearOneFilter('filter-ids'); }]
      ];
      for(const c of cases){
        c[1](); await settle();
        const on=dotOn();
        setFindMore(true); await settle(); const offOpen=!dotOn(); setFindMore(false); await settle();
        c[2](); await settle();
        ck('dot: '+c[0]+' alone shows it while collapsed, not while expanded, not once cleared', on&&offOpen&&!dotOn(), on+'/'+offOpen);
      }
      ck('dot: the funnel\'s accessible name says a filter is set', (toggleStatusFilter('CRIT'),/a filter is set/.test(fun.getAttribute('aria-label'))), fun.getAttribute('aria-label'));
      clearCriticalFilters(); await settle();

      // ---- filters behave as before: three combinations through the UI ----
      setFindMore(true); await settle(300);
      const pick=async function(trig,sel){ $(trig).click(); await settle(); document.querySelector(sel).click(); await settle(); };
      const closeDd=async function(){ if(FB_DD_OPEN) closeFbDropdown(); await settle(); };
      clearCriticalFilters(); await settle();
      await pick('fb-dd-status-trig','#fs-CRIT'); document.querySelector('#fs-RISK').click(); await settle(); await closeDd();
      R.notes.combo1=markerCount();
      clearCriticalFilters(); await settle();
      await pick('fb-dd-status-trig','#fs-TRACK'); await closeDd();
      await pick('fb-dd-float-trig','#float-chip-lt3w'); await closeDd();
      R.notes.combo2=markerCount();
      clearCriticalFilters(); setFloatPreset('any'); await settle();
      { const b=$('filter-band'); b.value=Array.prototype.find.call(b.options,function(o){ return o.value; }).value; b.dispatchEvent(new Event('change')); await settle(); }
      await pick('fb-dd-status-trig','#fs-RISK'); await closeDd();
      await pick('fb-dd-annot-trig','#annot-chip-group [data-key="any"]'); await closeDd();
      R.notes.combo3=markerCount();
      $('filter-band').value=''; applyFilter(); await settle();
      setAnnotFilter('edited'); toggleStatusFilter('CRIT'); await settle();
      ck('the clear x clears the status, float and notes filters', ($('btn-clear-crit').click(),STATUS_FILTER.size===0&&ANNOT_FILTER==='any'), STATUS_FILTER.size+' '+ANNOT_FILTER);
      setAnnotFilter('any'); clearCriticalFilters(); await settle();
      R.notes.combo0=markerCount();
      setFindMore(false); await settle(300);
    } else {
      ck('desktop: no funnel', !shown(fun), '');
      ck('desktop: the date tile is back in .fb-top beside Find', when.parentElement===find.parentElement&&find.nextElementSibling===when, when.parentElement&&when.parentElement.className);
      ck('desktop: Banding, Activity IDs and the inline chips show', shown($('filter-band'))&&shown($('filter-ids'))&&shown($('fs-CRIT')), '');
      clearCriticalFilters(); setFloatPreset('any'); setAnnotFilter('any'); await settle();
      R.notes.combo0=markerCount();
      toggleStatusFilter('CRIT'); toggleStatusFilter('RISK'); await settle();
      R.notes.combo1=markerCount();
      clearCriticalFilters(); toggleStatusFilter('TRACK'); setFloatPreset('lt3w'); await settle();
      R.notes.combo2=markerCount();
      clearCriticalFilters(); setFloatPreset('any');
      { const b=$('filter-band'); b.value=Array.prototype.find.call(b.options,function(o){ return o.value; }).value; applyFilter(); }
      toggleStatusFilter('RISK'); await settle();
      R.notes.combo3=markerCount();
      $('filter-band').value=''; applyFilter(); await settle();
      clearCriticalFilters(); setAnnotFilter('any'); await settle();
    }

    // ================= B. the heading scrolls away =================
    const icon=$('icon-bar'), hd=document.querySelector('.rpt-hd');
    const infoTh=document.querySelector('#info-hdr th');
    const lastOf=sel=>{ const a=document.querySelectorAll(sel); return a[a.length-1]; };
    const phaseTh=lastOf('#phase-hdr th'), phaseCorner=document.querySelector('#phase-hdr th.sticky')||document.querySelector('#phase-hdr th');
    const wkTh=lastOf('#week-hdr th'), wkCorner=document.querySelector('#week-hdr th.sticky')||document.querySelector('#week-hdr th');
    const gone=el=>!el||cs(el).visibility==='hidden'||rc(el).bottom<=0.5||!shown(el);
    // The real scroll: scrollTop moves, then the scroll event is dispatched.
    // Under --virtual-time-budget Chromium delivers the native event for the
    // first change only (no frames are produced between timers), so it is
    // dispatched explicitly; a native one arriving as well is a no-op (dy 0).
    const setBoard=function(y){ sw.scrollTop=y; sw.dispatchEvent(new Event('scroll')); };
    async function scrollBoardTo(to){
      const from=sw.scrollTop, n=8;
      for(let i=1;i<=n;i++){ setBoard(from+(to-from)*i/n); await settle(40); }
      await settle(500);
    }
    window.scrollTo(0,0); setBoard(0); await settle(400);
    if(CHROME_AWAY) setChromeAway(false,true);
    await settle(300);
    const r0={icon:rc(icon).top,hd:rc(hd).top,bar:rc(bar).top,sw:rc(sw).top,info:rc(infoTh).top,phase:rc(phaseTh).top};
    R.notes.start=JSON.stringify(r0);
    ck('start: heading, filter bar and info row on screen, the bands under the info row',
       shown(icon)&&shown(hd)&&shown(bar)&&shown(infoTh)&&Math.abs(rc(infoTh).top-rc(sw).top)<=1&&Math.abs(rc(phaseTh).top-rc(infoTh).bottom)<=1.5, JSON.stringify(r0));

    if(ARGS.away){
      await scrollBoardTo(600);
      ck('down: html.chrome-away is set', html.classList.contains('chrome-away'), html.className);
      ck('down: icon bar, heading and filter bar are out of view or hidden',
         gone(icon)&&gone(hd)&&gone(bar), [icon,hd,bar].map(function(e){ return f1(rc(e).bottom)+':'+cs(e).visibility; }).join(' '));
      ck('down: the hamburger (when shown) is gone too', !shown($('ws-toggle'))||gone($('ws-toggle')), '');
      ck('down: the info row is out of view (its cells above the board\'s top edge)',
         rc(infoTh).bottom<=0.5&&rc(document.querySelector('#info-hdr')).bottom<=0.5, f1(rc(infoTh).top)+'..'+f1(rc(infoTh).bottom));
      ck('down: the board starts at the top of the viewport and the window is not scrolled', Math.abs(rc(sw).top)<=0.5&&window.scrollY===0, f1(rc(sw).top)+' '+window.scrollY);
      ck('down: month band cells at the top (within 2px of 0)', Math.abs(rc(phaseTh).top)<=2&&Math.abs(rc(phaseCorner).top)<=2, f1(rc(phaseTh).top)+'/'+f1(rc(phaseCorner).top));
      ck('down: week band cells directly under it (within 2px), no gap',
         Math.abs(rc(wkTh).top-rc(phaseTh).bottom)<=2&&Math.abs(rc(wkCorner).top-rc(phaseCorner).bottom)<=2, f1(rc(wkTh).top)+' vs '+f1(rc(phaseTh).bottom));
      ck('down: the board reaches the viewport\'s bottom', rc(sw).bottom>=window.innerHeight-1, f1(rc(sw).bottom));
      ck('no horizontal page scroll (heading hidden)', noHScroll(), document.documentElement.scrollWidth);
      await scrollBoardTo(1400);
      ck('further down: still away, bands still sticky at the top',
         html.classList.contains('chrome-away')&&Math.abs(rc(phaseTh).top)<=2&&Math.abs(rc(wkTh).top-rc(phaseTh).bottom)<=2&&sw.scrollTop>1000,
         f1(rc(phaseTh).top)+' scrollTop '+sw.scrollTop);
      await scrollBoardTo(sw.scrollTop-80);
      ck('up: html.chrome-away cleared', !html.classList.contains('chrome-away'), html.className);
      ck('up: icon bar, heading and filter bar back where they were',
         shown(icon)&&shown(hd)&&shown(bar)&&Math.abs(rc(icon).top-r0.icon)<=1&&Math.abs(rc(hd).top-r0.hd)<=1&&Math.abs(rc(bar).top-r0.bar)<=1&&Math.abs(rc(sw).top-r0.sw)<=1,
         JSON.stringify({icon:rc(icon).top,hd:rc(hd).top,bar:rc(bar).top,sw:rc(sw).top}));
      ck('up: the info row is back at the board\'s top, the bands under it',
         shown(infoTh)&&Math.abs(rc(infoTh).top-rc(sw).top)<=1&&Math.abs(rc(phaseTh).top-rc(infoTh).bottom)<=1.5&&Math.abs(rc(wkTh).top-rc(phaseTh).bottom)<=1.5,
         f1(rc(infoTh).top)+' '+f1(rc(sw).top)+' '+f1(rc(phaseTh).top));
      ck('up: the shift is cleared (no leftover margin)', !html.classList.contains('chrome-shift')&&cs(icon).marginTop==='0px', cs(icon).marginTop);

      // From a window already scrolled part of the way (the old page scroll).
      setBoard(0); await settle(300);
      const maxY=document.documentElement.scrollHeight-window.innerHeight;
      window.scrollTo(0,Math.min(100,maxY)); await settle(300);
      const y0=window.scrollY;
      await scrollBoardTo(600);
      ck('from a scrolled window ('+y0+'px): bands at the top, window back at 0',
         html.classList.contains('chrome-away')&&Math.abs(rc(phaseTh).top)<=2&&window.scrollY===0&&Math.abs(rc(sw).top)<=0.5, y0+' '+f1(rc(phaseTh).top)+' '+window.scrollY);
      await scrollBoardTo(500);
      setBoard(0); await settle(400);
      ck('back at the top of the board: everything shown', !html.classList.contains('chrome-away')&&shown(bar)&&shown(infoTh), html.className);

      // Motion: the transition class exists only while it moves, never under reduced motion.
      setChromeAway(true); const animOn=html.classList.contains('chrome-anim'); await settle(600);
      const animAfter=html.classList.contains('chrome-anim');
      setChromeAway(false); await settle(600);
      if(ARGS.reduce) ck('reduced motion: no transition class is set', !animOn&&!animAfter, animOn+'/'+animAfter);
      else ck('motion: the transition class is set while it moves and cleared after', animOn&&!animAfter, animOn+'/'+animAfter);

      // ---- blocking: a dropdown / popover, then the milestone card ----
      if(ARGS.shape==='phone'){
        setFindMore(true); await settle(300);
        openFbDropdown('status'); await settle();
        await scrollBoardTo(600);
        ck('blocked: an open filter dropdown keeps everything shown', FB_DD_OPEN==='status'&&!html.classList.contains('chrome-away')&&shown(bar), FB_DD_OPEN+' '+html.className);
        closeFbDropdown(); setBoard(0); await settle(400);
        setFindMore(false); await settle(300);
      }
      $('wr-field').click(); await settle(300);
      const wrOpen=$('wr-field').getAttribute('aria-expanded')==='true';
      await scrollBoardTo(600);
      ck('blocked: the open week-range popover keeps everything shown', wrOpen&&!html.classList.contains('chrome-away'), wrOpen+' '+html.className);
      if(typeof closeWeekRangePopover==='function') closeWeekRangePopover(); else $('wr-field').click();
      await settle(300); setBoard(0); await settle(400);

      const wrap=document.querySelector('#tbody .m-wrap[data-ms]');
      const openCard=function(){
        const m=MILESTONES.filter(function(x){ return msId(x); })[0];
        const id=msId(m);
        const task=TASKS.filter(function(t){ return t.ref===m.ref; })[0]||{name:'',disc:'',ref:m.ref,hrs:'',type:'Weighted'};
        openMsDialog(m,id,wrap||document.body,computeHours(task),task);
      };
      openCard(); await settle(300);
      const dlg=$('ms-dialog'), d0=rc(dlg);
      await scrollBoardTo(600);
      ck('blocked: an open milestone card keeps everything shown', shown(dlg)&&!html.classList.contains('chrome-away'), html.className);
      ck('the card (position:fixed) did not move', cs(dlg).position==='fixed'&&Math.abs(rc(dlg).top-d0.top)<=0.5&&Math.abs(rc(dlg).left-d0.left)<=0.5, f1(d0.top)+' -> '+f1(rc(dlg).top));
      closeMsDialog(); await settle(300);
      await scrollBoardTo(1200);
      ck('the card closed: scrolling hides the heading again', html.classList.contains('chrome-away'), html.className);
      openCard(); await settle(300);
      const d1=rc(dlg);
      await scrollBoardTo(sw.scrollTop-200);
      ck('blocked both ways: scrolling up with the card open does not bring the heading back, the card stays put',
         shown(dlg)&&html.classList.contains('chrome-away')&&Math.abs(rc(dlg).top-d1.top)<=0.5, html.className+' '+f1(d1.top)+' -> '+f1(rc(dlg).top));
      closeMsDialog(); await settle(300);
      setBoard(0); await settle(500);
      ck('end: everything shown again at the top of the board', !html.classList.contains('chrome-away')&&shown(bar)&&shown(hd), html.className);
    } else {
      await scrollBoardTo(600);
      ck('desktop: scrolling the board changes nothing above it',
         !html.classList.contains('chrome-away')&&!html.classList.contains('chrome-shift')&&Math.abs(rc(icon).top-r0.icon)<=0.5&&Math.abs(rc(hd).top-r0.hd)<=0.5&&Math.abs(rc(bar).top-r0.bar)<=0.5&&Math.abs(rc(sw).top-r0.sw)<=0.5&&cs(icon).marginTop==='0px',
         JSON.stringify({icon:rc(icon).top,hd:rc(hd).top,bar:rc(bar).top,sw:rc(sw).top}));
      ck('desktop: the info row and bands stick exactly as before (info at the board\'s top, bands under it)',
         Math.abs(rc(infoTh).top-rc(sw).top)<=1&&Math.abs(rc(phaseTh).top-rc(infoTh).bottom)<=1.5&&Math.abs(rc(wkTh).top-rc(phaseTh).bottom)<=1.5,
         f1(rc(infoTh).top)+' '+f1(rc(sw).top)+' '+f1(rc(phaseTh).top));
      ck('desktop: the board keeps its max-height (100vh - 150px)', Math.abs(parseFloat(cs(sw).maxHeight)-(window.innerHeight-150))<=1, cs(sw).maxHeight);
      await scrollBoardTo(0);
    }
    ck('no horizontal page scroll (end)', noHScroll(), document.documentElement.scrollWidth);
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
    emit();
  }
})(__ARGS__);
"""


def render(html_path, width, height, args, reduce):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    probe = PROBE.replace("__ARGS__", json.dumps(args))
    out = page.replace("</body>", "<script>\n" + probe + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p72.html"
        tmp.write_text(out, encoding="utf-8")
        cmd = [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
               "--host-resolver-rules=MAP * ~NOTFOUND", "--allow-file-access-from-files",
               f"--window-size={width},{height}", "--virtual-time-budget=90000"]
        if reduce:
            cmd.append("--force-prefers-reduced-motion")
        cmd += ["--dump-dom", tmp.as_uri()]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    m = OUT_RE.search(proc.stdout)
    if not m:
        return {"checks": [{"name": "probe produced output", "pass": False,
                            "detail": proc.stderr[-2000:]}], "notes": {}}
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html)
    src = html.read_text(encoding="utf-8", errors="replace")

    checks = []
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal",
                   len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))
    checks.append(("source: the table keeps border-collapse:separate",
                   "table{border-collapse:separate;border-spacing:0" in src, ""))
    checks.append(("source: the scroll-away query is max-width:1023px in both the CSS and CHROME_AWAY_MQ",
                   "var CHROME_AWAY_MQ='(max-width:1023px)'" in src and "@media (max-width:1023px){\n  html.chrome-shift" in src, ""))
    checks.append(("source: reduced motion turns the transitions off",
                   "@media (max-width:1023px) and (prefers-reduced-motion:reduce)" in src, ""))
    bar = src[src.index('<div id="top-filter-bar"'):src.index('<div id="fb-hidden-state"')]
    bar = re.sub(r"<!--.*?-->", "", bar, flags=re.S)
    checks.append(("source: no em dash in the filter bar markup (comments aside)", "—" not in bar and "&mdash;" not in bar, ""))

    counts = []
    for (w, h, theme, shape, away, reduce) in RUNS:
        R = render(html, w, h, {"theme": theme, "shape": shape, "away": away, "reduce": reduce}, reduce)
        tag = f"[{w}x{h} {theme} {shape}{' away' if away else ''}{' reduced' if reduce else ''}]"
        print(f"\n=== {tag} ===  {json.dumps(R.get('notes', {}))}")
        for c in R["checks"]:
            checks.append((f"{tag} " + c["name"], c["pass"], c["detail"]))
        counts.append(R.get("notes", {}))

    # Filters behave as before: the same three combinations give the same
    # visible marker count through the phone dropdowns as on desktop.
    for key in ("combo0", "combo1", "combo2", "combo3"):
        vals = [n.get(key) for n in counts]
        checks.append((f"[compare] {key}: every width gives the same visible marker count",
                       len(vals) == len(RUNS) and None not in vals and len(set(vals)) == 1, json.dumps(vals)))
    n0 = counts[0] if counts else {}
    checks.append(("[compare] the combinations narrow the board and differ from each other (the test can tell them apart)",
                   None not in [n0.get(k) for k in ("combo0", "combo1", "combo2", "combo3")]
                   and len({n0.get("combo1"), n0.get("combo2"), n0.get("combo3")}) >= 2
                   and max(n0.get("combo1"), n0.get("combo2"), n0.get("combo3")) < n0.get("combo0"),
                   json.dumps([n0.get(k) for k in ("combo0", "combo1", "combo2", "combo3")])))

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
