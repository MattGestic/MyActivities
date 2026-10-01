#!/usr/bin/env python3
"""
p67_check: the Top filter bar's phone shape and the moved filter toggle (P67).

Matt's marked-up phone screenshot is docs/mockups/P67/filter-markup.png. This
check drives the REAL app in headless Chromium (network unresolvable) and
reads classList, attributes, computed style and getBoundingClientRect of the
elements themselves, never a screenshot.

Phone shape (max-width:767px, the breakpoint the stacked phone layout already
used), at 390x844 and at 767 (1px inside), light and dark:
  - Find shows only the Activity name field; the control inside its right end
    (P67's chevron, P72's funnel, #fb-find-more-btn) expands Banding and
    Activity ID(s) and collapses them again, with aria-expanded, a pressed
    look while open (P72; was a rotated chevron) and a stored display
    preference;
  - a Banding or Activity ID filter hidden by the collapsed state puts a dot
    on the chevron (N=3: band, IDs, both);
  - no section headings (box titles, the Status/Total float/Annotations row
    labels, the name/Weeks/Mode labels);
  - the Weeks field and the Status, Float and Notes triggers are in ONE tile,
    the Weeks field narrower than it; P72 (Matt 2026-10-01) re-orders the
    tile: Mode and Fit on the Weeks row to its right, the triggers on the
    row below (tools/p72_filter_scroll_check.py owns the full order);
  - Mode and Fit share a row (tops within 4px);
  - the tile and the dropdown checks run with the panel expanded, since P72
    folds the tile into the funnel's panel;
  - the Status trigger opens a panel holding the existing chips; picking 1, 2
    and 3 statuses reads "Status: Critical", "Status: Critical, At risk" and
    "Status: 3 selected", and the visible marker count equals the count with
    the same chips clicked on desktop (compared across runs below);
  - Float presets and Custom... still work through the panel; Notes too;
  - Esc and click-away close the panel, focus returns to the trigger on Esc;
  - every open panel stays inside the viewport; no horizontal page scroll.

Desktop shape, at 768 (1px outside) and 1440x900, light and dark:
  - chips inline and visible, box headings show, no dropdown triggers render,
    the status box is back in the bar (not inside the date-range box);
  - the toggle sits immediately left of + Milestone on the same row;
  - clicking it hides the bar and clicking again shows it, aria-expanded and
    aria-pressed following.

At every width: the bar's own close x (#btn-filter-hide) is gone.

Usage:
  python3 tools/p67_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p67-out">(.*?)</pre>', re.S)

# (width, height, theme, expected shape)
RUNS = [
    (390, 844, "light", "phone"),
    (390, 844, "dark", "phone"),
    (767, 900, "light", "phone"),   # 1px inside the breakpoint
    (768, 900, "light", "desk"),    # 1px outside it
    (1440, 900, "light", "desk"),
    (1440, 900, "dark", "desk"),
]

PROBE = r"""
(async function(ARGS){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p67-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=(ms)=>new Promise(r=>setTimeout(r,ms||200));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const cs=el=>getComputedStyle(el);
  const shown=el=>!!el&&el.getClientRects().length>0&&rc(el).width>0&&rc(el).height>0&&cs(el).visibility!=='hidden';
  const inView=r=>r.left>=-0.5&&r.top>=-0.5&&r.right<=document.documentElement.clientWidth+0.5&&r.bottom<=window.innerHeight+0.5;
  const within=(o,i)=>i.left>=o.left-0.5&&i.right<=o.right+0.5&&i.top>=o.top-0.5&&i.bottom<=o.bottom+0.5;
  const noHScroll=()=>document.documentElement.scrollWidth<=window.innerWidth+1;
  // Markers on rows the filter has not hidden: what the user sees filtered.
  const markerCount=()=>Array.prototype.filter.call(document.querySelectorAll('#tbody .m-wrap[data-ms]'),function(w){
    const tr=w.closest('tr'); return tr&&!tr.classList.contains('hidden-row')&&cs(tr).display!=='none'; }).length;
  const trigTxt=id=>($(id).querySelector('.fb-dd-txt')||{}).textContent||'';
  try{
    document.documentElement.setAttribute('data-theme',ARGS.theme);
    // The bar eases its padding open and shut; headless virtual time does not
    // always advance a CSS transition between two timers, so the end state
    // is measured with the transition off (the state, not the easing, is
    // what is under test).
    const noAnim=document.createElement('style');
    noAnim.textContent='#top-filter-bar{transition:none!important}';
    document.head.appendChild(noAnim);
    toggleTopFilterBar(true); await settle(300);
    const bar=$('top-filter-bar');
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight+' '+ARGS.theme;

    ck('the bar\'s own close x is gone (#btn-filter-hide)', !$('btn-filter-hide'), '');
    ck('the footer holds no close button', !bar.querySelector('.fb-foot button'), '');
    ck('the status/float/notes box and each chip group keep an accessible name',
       ['tfb-find','tfb-when','tfb-crit','filter-status-group','float-chip-group','annot-chip-group'].every(function(id){
         return !!($(id)&&$(id).getAttribute('aria-label')); }), '');

    // ---- the header toggle, at every width ----
    const tg=$('btn-filter-expand'), add=$('btn-add-ms');
    ck('toggle: shown, and the element immediately left of + Milestone',
       shown(tg)&&tg.nextElementSibling===add&&rc(tg).right<=rc(add).left+0.5&&rc(add).left-rc(tg).right<=12,
       shown(tg)?(rc(add).left-rc(tg).right).toFixed(1)+'px apart':'not shown');
    ck('toggle: on the same row as + Milestone',
       Math.abs((rc(tg).top+rc(tg).bottom)/2-(rc(add).top+rc(add).bottom)/2)<=2, rc(tg).top+'/'+rc(add).top);
    ck('toggle: pressed and expanded while the bar is open',
       tg.getAttribute('aria-expanded')==='true'&&tg.getAttribute('aria-pressed')==='true', tg.getAttribute('aria-expanded'));
    const bgOpen=cs(tg).backgroundColor;
    tg.click(); await settle(300);
    ck('toggle: a click hides the bar, aria-expanded/pressed follow',
       !bar.classList.contains('open')&&rc(bar).height<2&&tg.getAttribute('aria-expanded')==='false'&&tg.getAttribute('aria-pressed')==='false',
       rc(bar).height+'px '+tg.getAttribute('aria-expanded'));
    ck('toggle: still on screen with the bar hidden', shown(tg)&&!tg.hidden, '');
    ck('toggle: the pressed state is visible (background differs open vs closed)', cs(tg).backgroundColor!==bgOpen,
       bgOpen+' vs '+cs(tg).backgroundColor);
    tg.click(); await settle(300);
    ck('toggle: a second click shows the bar again',
       bar.classList.contains('open')&&rc(bar).height>20&&tg.getAttribute('aria-expanded')==='true', rc(bar).height+'px');
    ck('no horizontal page scroll (header row with the toggle)', noHScroll(), document.documentElement.scrollWidth);

    const when=$('tfb-when'), crit=$('tfb-crit');
    const trigs=['fb-dd-status-trig','fb-dd-float-trig','fb-dd-annot-trig'].map($);

    if(ARGS.shape==='desk'){
      ck('desktop: the status box is the bar\'s own child, not inside Date range', crit.parentElement===bar&&!when.contains(crit), '');
      ck('desktop: no dropdown trigger renders', trigs.every(function(t){ return !shown(t)&&cs(t).display==='none'; }), '');
      ck('desktop: the chips are inline and visible',
         ['fs-CRIT','fs-FUTURE','float-chip-any','float-chip-custom'].every(function(id){ return shown($(id)); })&&
         shown(document.querySelector('#annot-chip-group button')), '');
      ck('desktop: the status chips sit on one row with their label',
         Math.abs(rc($('fs-CRIT')).top-rc($('fs-FUTURE')).top)<=2, '');
      ck('desktop: the box headings and row labels show',
         shown(document.querySelector('#tfb-find .fb-title'))&&shown(document.querySelector('#tfb-when .fb-title'))&&
         Array.prototype.every.call(document.querySelectorAll('#tfb-crit .fb-dd>label'),shown), '');
      ck('desktop: Find shows Banding and Activity IDs without the chevron',
         shown($('filter-band'))&&shown($('filter-ids'))&&!shown($('fb-find-more-btn')), '');
      ck('desktop: the Weeks field is not shrunk to its content (still grows in its row)',
         rc($('wr-field')).width>=220-0.5, rc($('wr-field')).width);
      // The same chips the phone run clicks, clicked directly: the reference
      // marker counts the phone run is compared against.
      clearCriticalFilters(); await settle();
      R.notes.countAny=markerCount();
      $('fs-CRIT').click(); await settle();
      R.notes.count1=markerCount();
      $('fs-RISK').click(); await settle();
      R.notes.count2=markerCount();
      $('fs-TRACK').click(); await settle();
      R.notes.count3=markerCount();
      clearCriticalFilters(); await settle();
      setFloatPreset('lt10d'); await settle();
      R.notes.countFloat=markerCount();
      setFloatPreset('any'); setAnnotFilter('edited'); await settle();
      R.notes.countAnnot=markerCount();
      setAnnotFilter('any'); await settle();
      emit(); return;
    }

    // ================= phone shape =================
    ck('phone: the status box is inside the Date range box (one tile)', when.contains(crit), crit.parentElement.id);
    // ---- 1. Find ----
    const chev=$('fb-find-more-btn'), title=$('filter-title'), fw=title.closest('.ds-fwrap');
    try{ localStorage.removeItem('sret-fb-find-more'); }catch(e){}
    setFindMore(false); await settle();
    ck('find: only the Activity name field shows by default',
       shown(title)&&!shown($('filter-band'))&&!shown($('filter-ids'))&&!shown(document.querySelector('label[for="filter-ids"]')), '');
    ck('find: the chevron sits inside the right end of the search field',
       shown(chev)&&within(rc(fw),rc(chev))&&rc(fw).right-rc(chev).right<=4, JSON.stringify([rc(fw).right,rc(chev).right]));
    ck('find: the chevron is the --icon-btn square', Math.abs(rc(chev).width-parseFloat(cs(document.documentElement).getPropertyValue('--icon-btn')))<=0.5, rc(chev).width);
    // P72: the chevron became a funnel that looks pressed while open (was:
    // not rotated / rotated). Same intent: the control shows its state.
    const chevBgClosed=cs(chev).backgroundColor;
    ck('find: collapsed funnel reads aria-expanded=false, not pressed',
       chev.getAttribute('aria-expanded')==='false'&&!!chev.querySelector('.fb-chev-ico svg'), chevBgClosed);
    const clr=$('sticky-title-clear'); clr.style.display='inline-flex';
    ck('find: the title clear and the chevron do not overlap, both inside the field',
       rc(clr).right<=rc(chev).left+0.5&&within(rc(title),rc(clr)), rc(clr).right+' vs '+rc(chev).left);
    clr.style.display='none';
    const h0=rc($('tfb-find')).height;
    chev.click(); await settle(300);
    let stored=null; try{ stored=localStorage.getItem('sret-fb-find-more'); }catch(e){}
    ck('find: the chevron expands Banding and Activity IDs below the name',
       shown($('filter-band'))&&shown($('filter-ids'))&&rc($('filter-band')).top>=rc(title).bottom&&rc($('filter-ids')).top>=rc($('filter-band')).bottom,
       '');
    ck('find: expanded reads aria-expanded=true with the pressed funnel look',
       chev.getAttribute('aria-expanded')==='true'&&cs(chev).backgroundColor!==chevBgClosed, chevBgClosed+' vs '+cs(chev).backgroundColor);
    ck('find: the expanded state is stored as a display preference', stored==='open', stored);
    ck('find: the bar grows to fit the expanded tile (not clipped)',
       parseFloat(cs(bar).maxHeight)>=bar.scrollHeight-1, cs(bar).maxHeight+' vs '+bar.scrollHeight);
    ck('no horizontal page scroll (Find expanded)', noHScroll(), document.documentElement.scrollWidth);
    chev.click(); await settle(300);
    try{ stored=localStorage.getItem('sret-fb-find-more'); }catch(e){}
    ck('find: a second click collapses them again', !shown($('filter-band'))&&!shown($('filter-ids'))&&
       chev.getAttribute('aria-expanded')==='false'&&Math.abs(rc($('tfb-find')).height-h0)<1&&stored==='closed', stored);

    // ---- 1b. the hidden-filter dot, N=3 ----
    const dotOn=()=>chev.classList.contains('has-dot')&&cs(chev.querySelector('.fb-dot')).display!=='none'&&rc(chev.querySelector('.fb-dot')).width>0;
    ck('dot: none with no hidden filter set', !dotOn(), '');
    const band=$('filter-band');
    const bandOpt=Array.prototype.find.call(band.options,function(o){ return o.value; });
    if(bandOpt){ band.value=bandOpt.value; band.dispatchEvent(new Event('change')); await settle(); }
    ck('dot: (1) a Banding filter hidden by the collapse shows the dot', !!bandOpt&&dotOn(), bandOpt?bandOpt.value:'no band option');
    const ids=$('filter-ids');
    ids.value='ZZ-NOT-AN-ID'; applyFilter(); await settle();
    ck('dot: (2) Banding plus an Activity ID filter keeps the dot', dotOn(), '');
    band.value=''; applyFilter(); await settle();
    ck('dot: (3) an Activity ID filter alone shows the dot', dotOn(), '');
    setFindMore(true); await settle();
    ck('dot: gone while expanded (the filter is on screen)', !dotOn(), '');
    setFindMore(false);
    clearOneFilter('filter-ids'); await settle();
    ck('dot: gone once the hidden filters are cleared', !dotOn(), '');

    // P72: the date tile (and the dropdown triggers in it) is part of the
    // funnel's panel, so everything from here on runs with the panel open.
    setFindMore(true); await settle(300);
    // ---- 6. headings ----
    const heads=Array.prototype.slice.call(bar.querySelectorAll('.fb-title,.fb-name-lbl label,#wr-field-label,#tfb-when .fb-modefit .fb-inline>label,#tfb-crit .fb-dd>label'));
    ck('headings: no section heading or row label shows', heads.length>=7&&heads.every(function(h){ return !shown(h); }),
       heads.filter(shown).map(function(h){ return h.textContent; }).join('|'));
    ck('headings: the name field keeps an accessible name without its label', title.getAttribute('aria-label')==='Activity name', '');

    // ---- 2/3/4/5. the one tile ----
    const wr=$('wr-field'), tile=rc(when);
    ck('tile: Weeks and the Status, Float and Notes triggers are inside one tile',
       [wr].concat(trigs).every(function(el){ return shown(el)&&when.contains(el)&&within(tile,rc(el)); }),JSON.stringify(trigs.map(function(t){ return [Math.round(rc(t).left),Math.round(rc(t).top)]; })));
    ck('tile: the Weeks control is narrower than the tile', rc(wr).width<tile.width*0.6, Math.round(rc(wr).width)+' of '+Math.round(tile.width));
    ck('tile: the Weeks control is still the field that opens the week-range picker',
       wr.getAttribute('aria-haspopup')==='dialog'&&Math.abs(rc(wr).height-parseFloat(cs(document.documentElement).getPropertyValue('--ctl-h')))<=0.5, '');
    ck('tile: the triggers sit on the row below the Weeks field, from its left edge (P72 row 2)',
       rc(trigs[0]).top>=rc(wr).bottom-0.5&&Math.abs(rc(trigs[0]).left-rc(wr).left)<=0.5, rc(trigs[0]).left+','+rc(trigs[0]).top+' / '+rc(wr).left+','+rc(wr).bottom);
    const seg=$('wr-mode-seg'), fit=$('btn-fit-screen-inline');
    ck('tile: Mode and Fit share one row (tops within 4px)', Math.abs(rc(seg).top-rc(fit).top)<=4&&rc(fit).left>=rc(seg).right,
       rc(seg).top+'/'+rc(fit).top);
    ck('tile: Mode and Fit sit on the Weeks row, to its right (P72 row 1)', Math.abs(rc(seg).top-rc(wr).top)<=4&&rc(seg).left>=rc(wr).right-0.5,
       rc(seg).left+','+rc(seg).top+' / '+rc(wr).right+','+rc(wr).top);
    ck('triggers: the default labels', trigTxt('fb-dd-status-trig')==='Status: Any'&&trigTxt('fb-dd-float-trig')==='Float: Any'&&trigTxt('fb-dd-annot-trig')==='Notes: Any',
       trigs.map(function(t){ return t.textContent.trim(); }).join(' | '));
    ck('triggers: the chips are not inline (they live in the closed panels)',
       !shown($('fs-CRIT'))&&!shown($('float-chip-any'))&&!shown(document.querySelector('#annot-chip-group button')), '');
    ck('triggers: aria-expanded=false while closed', trigs.every(function(t){ return t.getAttribute('aria-expanded')==='false'; }), '');
    ck('no horizontal page scroll (collapsed)', noHScroll(), document.documentElement.scrollWidth);

    // ---- 5. Status dropdown ----
    clearCriticalFilters(); await settle();
    const anyCount=markerCount();
    const sTrig=trigs[0], sPanel=$('filter-status-group');
    sTrig.click(); await settle();
    ck('status: the trigger opens a panel holding the existing chips',
       sTrig.getAttribute('aria-expanded')==='true'&&shown(sPanel)&&sPanel.contains($('fs-CRIT'))&&shown($('fs-CRIT'))&&cs(sPanel).position==='fixed', '');
    ck('status: the open panel stays inside the viewport', inView(rc(sPanel)), JSON.stringify(rc(sPanel)));
    ck('status: the panel\'s columns use minmax(0,...) and every chip is inside the panel',
       /minmax\(0px/.test(cs(sPanel).gridTemplateColumns)||cs(sPanel).gridTemplateColumns.split(' ').length===3&&
       Array.prototype.every.call(sPanel.querySelectorAll('button'),function(b){ return within(rc(sPanel),rc(b)); }),
       cs(sPanel).gridTemplateColumns);
    ck('status: focus moves into the panel', sPanel.contains(document.activeElement), document.activeElement&&document.activeElement.id);
    ck('no horizontal page scroll (Status open)', noHScroll(), document.documentElement.scrollWidth);
    $('fs-CRIT').click(); await settle();
    R.notes.count1=markerCount();
    ck('status: (1) one status reads "Status: Critical", the panel stays open', trigTxt('fb-dd-status-trig')==='Status: Critical'&&shown(sPanel), trigTxt('fb-dd-status-trig'));
    $('fs-RISK').click(); await settle();
    R.notes.count2=markerCount();
    ck('status: (2) two statuses read both names', trigTxt('fb-dd-status-trig')==='Status: Critical, At risk', trigTxt('fb-dd-status-trig'));
    ck('status: the chips show their pressed state', $('fs-CRIT').getAttribute('aria-pressed')==='true'&&$('fs-RISK').getAttribute('aria-pressed')==='true', '');
    $('fs-TRACK').click(); await settle();
    R.notes.count3=markerCount();
    ck('status: (3) three statuses read "Status: 3 selected"', trigTxt('fb-dd-status-trig')==='Status: 3 selected', trigTxt('fb-dd-status-trig'));
    ck('status: the trigger shows a filter is set', sTrig.classList.contains('is-set'), '');
    ck('status: the board narrows (fewer markers than Any with one status)', R.notes.count1<anyCount, R.notes.count1+' of '+anyCount);
    R.notes.countAny=anyCount;
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    await settle();
    ck('status: Esc closes the panel, aria-expanded=false, focus back on the trigger',
       !shown(sPanel)&&sTrig.getAttribute('aria-expanded')==='false'&&document.activeElement===sTrig, document.activeElement&&document.activeElement.id);
    ck('status: closing keeps the filter (behaviour unchanged)', STATUS_FILTER.size===3&&markerCount()===R.notes.count3, STATUS_FILTER.size);
    sTrig.click(); await settle();
    document.querySelector('.rpt-hd .subtitle').click(); await settle();
    ck('status: a click away closes the panel', !shown(sPanel)&&sTrig.getAttribute('aria-expanded')==='false', '');
    sTrig.click(); await settle(); sTrig.click(); await settle();
    ck('status: the trigger itself toggles the panel closed', !shown(sPanel)&&sTrig.getAttribute('aria-expanded')==='false', '');
    clearCriticalFilters(); await settle();
    ck('status: clearing resets the trigger to "Status: Any"', trigTxt('fb-dd-status-trig')==='Status: Any'&&!sTrig.classList.contains('is-set'), '');

    // ---- Float: preset, Custom..., Esc order ----
    const fTrig=trigs[1], fPanel=$('float-pop-wrap');
    fTrig.click(); await settle();
    ck('float: the trigger opens the float chips', shown($('float-chip-lt10d'))&&inView(rc(fPanel)), JSON.stringify(rc(fPanel)));
    $('float-chip-lt10d').click(); await settle();
    R.notes.countFloat=markerCount();
    ck('float: a preset reads "Float: < 10d" and closes the panel', trigTxt('fb-dd-float-trig')==='Float: < 10d'&&!shown(fPanel), trigTxt('fb-dd-float-trig'));
    const sp=floatFilterSpec();
    ck('float: the preset sets the same filter as before (lt 10 days)', sp&&sp.op==='lt'&&sp.days===10, JSON.stringify(sp));
    fTrig.click(); await settle();
    $('float-chip-custom').click(); await settle();
    const cpop=$('float-custom-pop');
    ck('float: Custom... opens its card inside the panel, inside the viewport',
       shown(cpop)&&fPanel.contains(cpop)&&inView(rc(fPanel))&&inView(rc(cpop))&&$('float-chip-custom').getAttribute('aria-expanded')==='true',
       JSON.stringify(rc(fPanel)));
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); await settle();
    ck('float: Esc closes the Custom card first, the panel stays open', !shown(cpop)&&shown(fPanel), '');
    $('float-chip-custom').click(); await settle();
    $('float-custom-val').value='15'; setFloatCustomCmp('le'); setFloatCustomUnit('d');
    cpop.querySelector('.ds-btn.primary').click(); await settle();
    const sp2=floatFilterSpec();
    ck('float: Custom Apply sets the filter, labels the trigger and closes the panel',
       sp2&&sp2.op==='le'&&sp2.days===15&&/^Float: ≤ 15d$/.test(trigTxt('fb-dd-float-trig'))&&!shown(fPanel), trigTxt('fb-dd-float-trig')+' '+JSON.stringify(sp2));
    setFloatPreset('any'); await settle();
    ck('float: Any reads "Float: Any"', trigTxt('fb-dd-float-trig')==='Float: Any', trigTxt('fb-dd-float-trig'));

    // ---- Notes ----
    const aTrig=trigs[2], aPanel=$('annot-chip-group');
    aTrig.click(); await settle();
    ck('notes: the trigger opens the annotation chips inside the viewport', shown(aPanel)&&inView(rc(aPanel)), '');
    aPanel.querySelector('[data-key="edited"]').click(); await settle();
    R.notes.countAnnot=markerCount();
    ck('notes: Edited reads "Notes: Edited", sets the filter and closes', trigTxt('fb-dd-annot-trig')==='Notes: Edited'&&ANNOT_FILTER==='edited'&&!shown(aPanel), trigTxt('fb-dd-annot-trig'));
    setAnnotFilter('any'); await settle();

    // ---- closing the bar closes an open panel ----
    sTrig.click(); await settle();
    toggleTopFilterBar(false); await settle();
    ck('hiding the bar closes an open panel', !shown(sPanel)&&FB_DD_OPEN===null, '');
    toggleTopFilterBar(true); await settle(300);
    ck('no horizontal page scroll (end)', noHScroll(), document.documentElement.scrollWidth);
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
    emit();
  }
})(__ARGS__);
"""


def render(html_path, width, height, args):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    probe = PROBE.replace("__ARGS__", json.dumps(args))
    out = page.replace("</body>", "<script>\n" + probe + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p67.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--host-resolver-rules=MAP * ~NOTFOUND",
             f"--window-size={width},{height}", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
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
    checks.append(("source: no #btn-filter-hide left in the file", "btn-filter-hide" not in src, ""))
    bar = src[src.index('<div id="top-filter-bar"'):src.index('<div id="fb-hidden-state"')]
    bar = re.sub(r"<!--.*?-->", "", bar, flags=re.S)  # user strings, not comments
    checks.append(("source: no em dash in the filter bar markup (comments aside)", "—" not in bar and "&mdash;" not in bar, ""))

    counts = {}
    for (w, h, theme, shape) in RUNS:
        R = render(html, w, h, {"theme": theme, "shape": shape})
        tag = f"[{w}x{h} {theme} {shape}]"
        print(f"\n=== {tag} ===  {json.dumps(R.get('notes', {}))}")
        for c in R["checks"]:
            checks.append((f"{tag} " + c["name"], c["pass"], c["detail"]))
        counts[(w, theme, shape)] = R.get("notes", {})

    # The phone dropdowns filter exactly as the desktop chips do: same visible
    # marker count for the same chips, every phone run against every desktop
    # run, N=1, 2 and 3 statuses plus a float preset and a notes option.
    desk = [n for k, n in counts.items() if k[2] == "desk"]
    phone = [n for k, n in counts.items() if k[2] == "phone"]
    for key in ("countAny", "count1", "count2", "count3", "countFloat", "countAnnot"):
        vals = [n.get(key) for n in desk + phone]
        checks.append((f"[compare] {key}: phone dropdowns and desktop chips give the same visible marker count",
                       len(vals) == len(RUNS) and None not in vals and len(set(vals)) == 1, json.dumps(vals)))
    ns = desk[0] if desk else {}
    checks.append(("[compare] the counts differ between N=1, 2 and 3 (the test can tell them apart)",
                   ns.get("count1") is not None and len({ns.get("count1"), ns.get("count2"), ns.get("count3")}) >= 2,
                   json.dumps([ns.get("count1"), ns.get("count2"), ns.get("count3")])))

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
