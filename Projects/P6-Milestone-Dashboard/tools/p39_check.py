#!/usr/bin/env python3
"""
P39 check (TEST-41): View Controls rework, Baseline shadow in the heading,
the drawer's action bar, and the two-column filter row.

THE DEPENDENCY REPORT WAS REFUTED BY MEASUREMENT and is asserted here rather
than fixed, so a real regression cannot hide behind "that was already broken".
On the current build, from the state the board opens in, with only `input`
events and no manual clicking: 0 lines before, 675 in the DOM and 132 on screen
with both kinds switched on, 478 with the reported date range applied, still 478
after a rerender, back to 675 when the range is cleared, and the SVG layer's
computed visibility follows hidden -> visible. The screenshot the report came
with is a pre-P36 build (separate header icon buttons, a "Title contains" field
that no longer exists) showing the Dependencies "All off" button active.

EVERY SIZE SLIDER IS DEAD WHILE ITS TEXT IS OFF. Asserted on `disabled` AND on
a real drag: setting .value and firing input must not move the CSS custom
property while the control is disabled, because `disabled` alone is a property
a stylesheet can make look right while the handler still runs.

THE THREE LABEL STATES HAVE ONE WRITER. applyMarkerLabelState() now writes the
board, the two checkboxes, the two remarks buttons and the three disabled
states. The assertion drives each one through a DIFFERENT entry point (the
handler, setColButtonState, and a rebuild) and requires the control and the
board to agree after each, because that disagreement is the defect family this
consolidation is closing (TD-59, TD-71, TD-138, TD-145).

THE ACTION BAR IS NO LONGER A STICKY FOOTER, which is a contract change, not a
regression: p29_check's assertion was rewritten to the new one and given teeth
it did not have (its companion check could pass vacuously whenever the open tab
was too short to scroll).

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p39_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p39-out">(.*?)</pre>', re.S)

# 390 is where the filter row must be stacked; 1440 is where it must be two
# columns side by side. 1024 sits at the basis, so the break is measured from
# what actually fits rather than asserted at a width typed into the check.
VIEWPORTS = [(390, 844), (1024, 800), (1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p39-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const $=id=>document.getElementById(id);
  const r1=v=>Math.round(v*10)/10;
  const box=el=>{ if(!el) return null; const q=el.getBoundingClientRect();
    return {t:r1(q.top),b:r1(q.bottom),l:r1(q.left),r:r1(q.right),w:r1(q.width),h:r1(q.height)}; };
  const shown=list=>Array.prototype.filter.call(list,function(e){
    return getComputedStyle(e).display!=='none'; }).length;
  const cssVar=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const drag=function(id,v){ const s=$(id); s.value=String(v);
    s.dispatchEvent(new Event('input',{bubbles:true})); };

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight;

    // ============ 1. Layout section: order, names, range ============
    const layout=document.querySelectorAll('#filter-bar .cv-sect')[0];
    const sliders=Array.prototype.map.call(
      layout.querySelectorAll('input[type=range]'),function(s){return s.id;});
    const labelText=Array.prototype.map.call(
      layout.querySelectorAll('.cv-field-row label'),
      function(l){ return l.textContent.replace(/\s+/g,' ').trim(); });
    R.notes.layout={sliders:sliders,labels:labelText,
                    wkMax:$('wk-width').max,wkMin:$('wk-width').min};
    ck('layout: Title Column, Column Width, Row height then Icon size',
       sliders.join(',')==='name-width,wk-width,row-height,ico-size',
       sliders.join(', '));
    ck('layout: the two renamed controls read as asked',
       /^Title Column:/.test(labelText[0])&&/^Column Width:/.test(labelText[1]),
       labelText.slice(0,2).join(' | '));
    ck('layout: Column Width reaches 144px',
       $('wk-width').max==='144', 'min '+$('wk-width').min+', max '+$('wk-width').max);
    // Not just the attribute: the column has to actually render at it.
    drag('wk-width',144); onSizeSliderRelease(); await settle(); await settle();
    const wide=document.querySelector('#tbody tr.data td.col-wk');
    R.notes.wkAt144={colw:cssVar('--colw'),cell:wide?r1(wide.getBoundingClientRect().width):null};
    ck('layout: and the week column renders at 144px, not just accepts the value',
       R.notes.wkAt144.cell!==null&&Math.abs(R.notes.wkAt144.cell-144)<=1.5,
       JSON.stringify(R.notes.wkAt144));
    drag('wk-width',36); onSizeSliderRelease(); await settle(); await settle();

    // ============ 2. Labels: sliders under their controls, dead when off ====
    // The panel has to be OPEN for any of this: #filter-bar is parked off
    // screen with transform:translateX(100%), so a hit test inside it answers
    // "(nothing)" in both states and could not tell them apart. The first run
    // of this check did exactly that.
    toggleFilterBar(true); await settle(); await settle();
    const labelsSect=Array.prototype.filter.call(
      document.querySelectorAll('#filter-bar .cv-sect'),function(s){
        const t=s.querySelector('.cv-sect-title');
        return t&&t.textContent.trim()==='Labels'; })[0];
    const order=Array.prototype.map.call(
      labelsSect.querySelectorAll('.toggle-switch-row .tsw-label, .cv-field-row'),
      function(e){ return e.id||e.className.indexOf('tsw-label')>=0
        ? (e.id||e.textContent.trim()) : e.textContent.replace(/\s+/g,' ').trim().slice(0,22); });
    R.notes.labelOrder=order;
    // Each slider must come directly after the control that governs it.
    const seq=Array.prototype.map.call(labelsSect.children,function(e){
      return e.id||e.className; });
    R.notes.labelSeq=seq;
    ck('labels: each size slider sits directly under its own control',
       seq.indexOf('row-label-scale')===seq.indexOf('toggle-switch-row')+1||
       (seq[1]==='row-label-scale'&&seq[3]==='row-hrs-scale'&&seq[5]==='row-title-scale'),
       seq.join(' > '));

    // Defaults at first paint: labels off, hours off, title mode id.
    R.notes.enabledAtOpen={label:!$('label-scale').disabled,
                           hrs:!$('hrs-scale').disabled,
                           title:!$('title-scale').disabled};
    ck('labels: the two switched-off sliders are disabled and the title one is live',
       $('label-scale').disabled===true&&$('hrs-scale').disabled===true&&
       $('title-scale').disabled===false, JSON.stringify(R.notes.enabledAtOpen));
    ck('labels: a disabled row is visibly dimmed, not just inert',
       $('row-label-scale').classList.contains('is-disabled')&&
       $('row-hrs-scale').classList.contains('is-disabled')&&
       !$('row-title-scale').classList.contains('is-disabled'),
       'label '+$('row-label-scale').className+' / title '+$('row-title-scale').className);
    // Teeth, by HIT TEST rather than by synthetic drag. A synthetic drag cannot
    // measure this at all: dispatchEvent reaches an oninput listener whether or
    // not the input is disabled, and an untrusted pointer event never drives a
    // range thumb, so neither direction of that experiment discriminates. What
    // does is asking the document what is at the slider's own centre. The first
    // draft of this check dragged, "failed", and was wrong about working code,
    // which is the fourth time a measurement technique has been the defect here.
    const atCentre=function(id){
      const q=$(id).getBoundingClientRect();
      const hit=document.elementFromPoint(q.left+q.width/2,q.top+q.height/2);
      return hit?(hit.id||hit.className||hit.tagName):'(nothing)'; };
    const before=cssVar('--label-scale');
    const hitWhenOff=atCentre('label-scale');
    ck('labels: a DISABLED slider cannot be reached by a click at its own centre',
       hitWhenOff!=='label-scale', 'the point belongs to '+hitWhenOff);
    // Turn it on through the handler, and it must come alive and then work.
    $('btn-lbl').checked=true; toggleLabels($('btn-lbl')); await settle();
    const liveNow=!$('label-scale').disabled;
    const hitWhenOn=atCentre('label-scale');
    drag('label-scale',150); await settle();
    const afterEnabled=cssVar('--label-scale');
    R.notes.scaleControl={before:before,enabled:afterEnabled,liveNow:liveNow,
                          hitOff:hitWhenOff,hitOn:hitWhenOn};
    ck('labels NEGATIVE CONTROL: the same point IS the slider once the label is on, and it moves the board',
       liveNow&&hitWhenOn==='label-scale'&&afterEnabled!==before,
       'hit '+hitWhenOff+' -> '+hitWhenOn+', scale '+before+' -> '+afterEnabled);
    drag('label-scale',100);
    $('btn-lbl').checked=false; toggleLabels($('btn-lbl')); await settle();
    ck('labels: turning it back off disables the slider again',
       $('label-scale').disabled===true, 'disabled '+$('label-scale').disabled);
    // Title mode Off must kill the title slider, on the same click.
    setShortTitleMode('off');
    const titleDeadNow=$('title-scale').disabled;
    await settle(); await settle();
    R.notes.titleOff={disabledImmediately:titleDeadNow,
                      shownTitles:shown(document.querySelectorAll('#tbody .m-short-title'))};
    ck('labels: Off disables the title slider immediately, not after the rebuild',
       titleDeadNow===true&&R.notes.titleOff.shownTitles===0,
       JSON.stringify(R.notes.titleOff));
    setShortTitleMode('id'); await settle(); await settle();
    ck('labels: and selecting a mode brings it back',
       $('title-scale').disabled===false&&
       shown(document.querySelectorAll('#tbody .m-short-title'))>100,
       'disabled '+$('title-scale').disabled);

    // ============ 3. One writer, three entry points ============
    // The control and the board must agree after each, which is the thing that
    // drifted apart four times.
    const agree=function(){
      return {lbl:$('btn-lbl').checked===(shown(document.querySelectorAll('#tbody .m-lbl'))>0),
              hrs:$('btn-mhrs').checked===(shown(document.querySelectorAll('#tbody .m-hrs,#tbody .m-hrs-loe'))>0)};
    };
    $('btn-mhrs').checked=true; toggleMHours($('btn-mhrs')); await settle();
    const viaHandler=agree();
    setColButtonState($('btn-mhrs'),false); await settle();
    const viaColState=agree();
    const cbAfterColState=$('btn-mhrs').checked;
    setColButtonState($('btn-lbl'),true); await settle();
    scheduleRerender(true); await settle(); await settle(); await settle();
    const viaRebuild=agree();
    R.notes.oneWriter={viaHandler:viaHandler,viaColState:viaColState,
                       colStateWroteCheckbox:cbAfterColState,viaRebuild:viaRebuild};
    ck('one writer: control and board agree after the handler, setColButtonState and a rebuild',
       viaHandler.lbl&&viaHandler.hrs&&viaColState.lbl&&viaColState.hrs&&
       cbAfterColState===false&&viaRebuild.lbl&&viaRebuild.hrs,
       JSON.stringify(R.notes.oneWriter));
    setColButtonState($('btn-lbl'),false); await settle();

    // ============ 4. Row Comments field ============
    const rmk={label:document.querySelector('.cv-remarks-row label').textContent.trim(),
               show:$('btn-remarks-show'),hide:$('btn-remarks-hide')};
    R.notes.remarks={label:rmk.label,
                     showActive:rmk.show.classList.contains('active'),
                     hideActive:rmk.hide.classList.contains('active'),
                     shown:shown(document.querySelectorAll('#tbody .remarks'))};
    ck('remarks: the field is labelled Row Comments field with a Show / Hide pair',
       rmk.label==='Row Comments field'&&!!rmk.show&&!!rmk.hide, rmk.label);
    ck('remarks: it opens on Show, and the board agrees',
       R.notes.remarks.showActive&&!R.notes.remarks.hideActive&&
       R.notes.remarks.shown>100,
       JSON.stringify(R.notes.remarks));
    setRemarksVisible(false); await settle();
    const hid={showActive:rmk.show.classList.contains('active'),
               hideActive:rmk.hide.classList.contains('active'),
               shown:shown(document.querySelectorAll('#tbody .remarks'))};
    R.notes.remarksHidden=hid;
    ck('remarks: Hide clears the field and moves the active half with it',
       !hid.showActive&&hid.hideActive&&hid.shown===0, JSON.stringify(hid));
    // Clicking the half that is already active must be a no-op, not a flip.
    setRemarksVisible(false); await settle();
    ck('remarks: clicking the active half again does not flip it back',
       shown(document.querySelectorAll('#tbody .remarks'))===0&&
       rmk.hide.classList.contains('active'),
       shown(document.querySelectorAll('#tbody .remarks'))+' shown');
    setRemarksVisible(true); await settle();

    // Closed again before anything measures the page: the open panel reserves a
    // 300px right margin on <body>, so leaving it open would move every box the
    // rest of this run measures.
    toggleFilterBar(false); await settle(); await settle();

    // ============ 5. Baseline shadow in the heading ============
    const blWrap=$('bl-shadow-wrap'), blCb=$('btn-baseline-ms');
    const vt=document.querySelector('.view-toggle');
    R.notes.baseline={inHeading:!!(blWrap&&blWrap.closest('.rpt-sub-view')),
                      stillInPanel:!!document.querySelector('#filter-bar #btn-baseline-ms'),
                      disabled:blCb?blCb.disabled:null,
                      wrapDisabledClass:blWrap?blWrap.classList.contains('is-disabled'):null,
                      title:(blWrap&&blWrap.title||'').slice(0,60),
                      noteLeft:!!$('baseline-overlay-note'),
                      viewMode:(typeof VIEW_MODE!=='undefined')?VIEW_MODE:'?'};
    ck('baseline: the toggle sits in the heading beside the View toggle',
       R.notes.baseline.inHeading&&!!vt&&
       Math.abs(box(blWrap).t-box(vt).t)<14,
       'in heading '+R.notes.baseline.inHeading+
       (vt?', tops '+box(blWrap).t+' / '+box(vt).t:''));
    ck('baseline: it was MOVED, not duplicated, and the note it replaced is gone',
       !R.notes.baseline.stillInPanel&&!R.notes.baseline.noteLeft,
       'still in panel '+R.notes.baseline.stillInPanel+
       ', note still there '+R.notes.baseline.noteLeft);
    ck('baseline: in the Baseline view it is inactive, and says why',
       R.notes.baseline.viewMode==='baseline'&&R.notes.baseline.disabled===true&&
       R.notes.baseline.wrapDisabledClass===true&&
       /Update view/.test(blWrap.title),
       JSON.stringify(R.notes.baseline));

    // ============ 6. The drawer's action bar ============
    // One row at v3.1.0-P40: the two exports spread across the left, Save and
    // Clear anchored together against the right edge. P39 put Clear on its own
    // line; the user asked for it back in line with Save, so this follows the
    // requested contract. p29_check carries the detailed version of this,
    // including that the exports are genuinely spread and not just left
    // aligned; what is asserted here is the placement relative to the tabs.
    toggleSettingsDrawer(true); await settle(); await settle();
    const DR=$('settings-drawer'), act=DR.querySelector('.sd-actions');
    const tabs=DR.querySelector('.sd-tabs');
    const exportsBox=act.querySelector('.sd-actions-exports');
    const rightBox=act.querySelector('.sd-actions-right');
    const lbl=function(b){ return b.textContent.replace(/[^A-Za-z ]/g,'').trim(); };
    const actOrder=Array.prototype.map.call(act.querySelectorAll('button'),lbl);
    R.notes.actions={order:actOrder,actBox:box(act),tabsBox:box(tabs),
                     exports:box(exportsBox),right:box(rightBox),
                     position:getComputedStyle(act).position};
    ck('actions: the bar is above the tab strip, not a footer under the panels',
       box(act).b<=box(tabs).t+1, 'bar bottom '+box(act).b+', tabs top '+box(tabs).t);
    ck('actions: CSV, JSON, Save as new dashboard, Reset row marks, in that order',
       actOrder.length===4&&/CSV/.test(actOrder[0])&&/JSON/.test(actOrder[1])&&
       /Save as new dashboard/.test(actOrder[2])&&/Reset row marks/.test(actOrder[3]),
       actOrder.join(' | '));
    ck('actions: the right-hand pair reaches the row\u2019s right edge',
       !!rightBox&&Math.abs(box(rightBox).r-box(act.querySelector('.sd-actions-main')).r)<=1,
       box(rightBox).r+' against row right '+box(act.querySelector('.sd-actions-main')).r);
    toggleSettingsDrawer(false); await settle();

    // ============ 7. The filter row ============
    // Three full-width rows at v3.1.0-P40, changed from the two columns P39
    // shipped. The two-column shape put WHAT on the left and WHEN on the right,
    // which left nowhere for a third question; the critical-path set is that
    // third question, so the bar became one row per question. The assertions
    // move with the contract: what they still have teeth on is that every group
    // lives in exactly one row, that the rows are genuinely stacked rather than
    // half-wrapped, and that the date range is anchored right while there is
    // room for it to be.
    toggleTopFilterBar(true); await settle(); await settle();
    const bar=$('top-filter-bar');
    // D-15a renamed the three direct rows to three titled sections
    // (.tfb-section: Find / Critical path / When) and put each section's
    // fields in their own .tfb-fields wrapper, but kept the same "three
    // groups of groups, 4/2/2 fields" contract this test was written
    // against, so only the selector changes here.
    const rows=bar.querySelectorAll(':scope > .tfb-section');
    const foot=bar.querySelector('.tfb-foot');
    const groups=bar.querySelectorAll('.tfb-group');
    const inRows=Array.prototype.reduce.call(rows,function(s,r){
      return s+r.querySelectorAll('.tfb-group').length; },0);
    const tops=Array.prototype.map.call(rows,function(r){ return box(r).t; });
    let stacked=true;
    for(let i=1;i<tops.length;i++) if(tops[i]<=tops[i-1]) stacked=false;
    R.notes.filterRow={rows:rows.length,groups:groups.length,inRows:inRows,
                       tops:tops,stacked:stacked,
                       crit:box($('tfb-crit')),foot:box(foot),
                       textInputs:document.querySelectorAll('#top-filter-bar input[type=text]').length};
    ck('filter row: three rows hold every group between them, none loose',
       rows.length===3&&groups.length===8&&inRows===8,
       rows.length+' rows, '+inRows+' of '+groups.length+' groups inside them');
    ck('filter row: the rows are genuinely stacked, each below the last',
       stacked&&tops.length===3, tops.join(' / '));
    // Row 1 holds the four identity filters, row 2 the critical set, row 3 the
    // two time filters. Asserted by count per row, so moving one between rows
    // fails rather than passing on a total that still adds up.
    const perRow=Array.prototype.map.call(rows,function(r){
      return r.querySelectorAll('.tfb-group').length; });
    R.notes.filterRow.perRow=perRow;
    ck('filter row: name/band/source/IDs, then the critical set, then week and dates',
       perRow.join(',')==='4,2,2', perRow.join(', '));
    // The critical container is ruled off from the rows around it, because it
    // filters on a different property of the data.
    const critCs=getComputedStyle($('tfb-crit'));
    ck('filter row: the critical set is ruled off above and below',
       parseFloat(critCs.borderTopWidth)>0&&parseFloat(critCs.borderBottomWidth)>0,
       critCs.borderTopWidth+' / '+critCs.borderBottomWidth);
    // The date range is anchored right, when the row has not wrapped. Measured,
    // not assumed from the viewport: at 390 the week filter alone overflows and
    // the auto margin correctly does nothing.
    const when=rows[2];
    const wg=when.querySelectorAll('.tfb-group');
    const wrapped=box(wg[1]).t>box(wg[0]).t+2;
    R.notes.filterRow.dateAnchor={wrapped:wrapped,
      dateRight:box(wg[1]).r,rowRight:box(when).r};
    ck('filter row: the date range is anchored right'+(wrapped?', or would be if the row had room':''),
       wrapped||Math.abs(box(wg[1]).r-box(when).r)<=1,
       'date right '+box(wg[1]).r+' against row right '+box(when).r+
       (wrapped?' (wrapped at this width)':''));
    ck('filter row: the summary line runs full width under every row',
       !!foot&&box(foot).t>=tops[tops.length-1], foot?'foot top '+box(foot).t:'missing');
    ck('filter row: only one free-text name field, so no duplicate of it',
       R.notes.filterRow.textInputs===2,
       R.notes.filterRow.textInputs+' text inputs (name + Activity IDs)');
    // The bar collapses by max-height, so a taller bar must not be cut off.
    const inner=Array.prototype.reduce.call(bar.children,function(m,c){
      return Math.max(m,c.getBoundingClientRect().bottom); },0)-box(bar).t;
    R.notes.filterRow.contentH=r1(inner); R.notes.filterRow.boxH=box(bar).h;
    ck('filter row: the open bar is tall enough for its own content',
       box(bar).h>=inner-2, 'box '+box(bar).h+' against content '+r1(inner));
    // Collapsed, the heading offers a one-click way back. Open, it does not.
    toggleTopFilterBar(false); await settle();
    const expClosed=$('btn-filter-expand').hidden;
    toggleTopFilterBar(true); await settle();
    const expOpen=$('btn-filter-expand').hidden;
    R.notes.filterRow.expandIcon={hiddenWhenClosed:expClosed,hiddenWhenOpen:expOpen};
    ck('filter row: the expand control shows only while the bar is collapsed',
       expClosed===false&&expOpen===true,
       'hidden when collapsed '+expClosed+', hidden when open '+expOpen);

    // ============ 8. Dependency lines, the refuted report ============
    const depLines=()=>document.querySelectorAll('#dep-lines-g path.dep-line').length;
    const depSvgVis=function(){ const g=$('dep-lines-g');
      const s=g?g.closest('svg'):null; return s?getComputedStyle(s).visibility:'none'; };
    const onScreenLines=function(){
      return Array.prototype.filter.call(
        document.querySelectorAll('#dep-lines-g path.dep-line'),function(p){
          const q=p.getBoundingClientRect();
          return (q.width>0.5||q.height>0.5)&&q.right>0&&q.left<window.innerWidth
                 &&q.bottom>0&&q.top<window.innerHeight; }).length; };
    const depOpen={lines:depLines(),vis:depSvgVis()};
    setAllDep('pred',true); setAllDep('succ',true); await settle(); await settle();
    const depOn={lines:depLines(),onScreen:onScreenLines(),vis:depSvgVis()};
    scheduleRerender(true); await settle(); await settle(); await settle();
    const depAfter={lines:depLines(),onScreen:onScreenLines(),vis:depSvgVis()};
    R.notes.deps={open:depOpen,on:depOn,afterRebuild:depAfter,
                  data:Object.keys(DEP_DATA).length};
    // Asserted on LINES, not on the layer's visibility. The layer is a
    // pointer-events:none SVG with nothing in it when no kind is switched on,
    // and its computed visibility depends on whether onSizeSliderDrag ran since
    // the last drawDepLines: hidden on a board nothing has touched, visible on
    // one that has drawn and cleared. Both look identical, since an empty SVG
    // paints nothing either way, so visibility is recorded and not asserted.
    // TD-152.
    ck('deps: nothing is drawn until they are switched on, which is the default',
       depOpen.lines===0, JSON.stringify(depOpen));
    // onScreen is a function of how much board is below the header, so the
    // threshold is what a phone can show, not what a desktop can: the P40
    // filter row is three rows rather than two columns, which pushes the board
    // down and took the 390 figure from 38 to 20. D-15a took it from 16 to 8:
    // not a narrower board, a taller (CORRECT) open bar. The bar's max-height
    // used to be capped by a `var(--tfb-h,160px)` that a `transition` on
    // max-height stopped from ever picking up the real, JS-measured value
    // (measured: getComputedStyle read back the literal 160px fallback even
    // though the custom property itself held the right number), so the open
    // bar had ALWAYS been silently clipped short at 390 in every build before
    // this one, including when this threshold was last set. Fixed, the bar is
    // genuinely as tall as its content, which is more of the 844px viewport,
    // which is fewer dependency lines left below it. The point of the
    // assertion is unchanged: that lines REACH THE SCREEN at all, not how
    // many, so the threshold moves with the correction rather than staying
    // pinned to a figure that was itself measured against the bug.
    ck('deps: switching both kinds on draws lines, and puts them on screen',
       depOn.lines>400&&depOn.onScreen>3&&depOn.vis==='visible',
       JSON.stringify(depOn)+' from '+R.notes.deps.data+' milestones with data');
    ck('deps: and they survive a rebuild, which is where they have been lost before',
       depAfter.lines===depOn.lines&&depAfter.onScreen>3&&depAfter.vis==='visible',
       JSON.stringify(depAfter));
    setAllDep('pred',false); setAllDep('succ',false); await settle();
    ck('deps NEGATIVE CONTROL: switching them off takes every line away again',
       depLines()===0, depLines()+' lines');
    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=e&&e.stack; }
  emit();
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p39.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(root / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()
    html = pathlib.Path(a.html)
    src = html.read_text(encoding="utf-8", errors="replace")
    nospace = src.replace(" ", "").replace("\n", "")

    checks = []
    vers = len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src))
    checks.append(("source: exactly one version literal", vers == 1, f"{vers} found"))
    checks.append((
        "source: the fit clamp matches the slider's range, so fitting cannot beat dragging",
        "Math.max(20,Math.min(144,ideal))" in nospace and 'max="144"' in src,
        "the clamp and the slider disagree"))
    # The three dead second writers are the point of the consolidation.
    for gone in ("function toggleShortTitles(", "function toggleRemarks(",
                 "function toggleRemarksBtn("):
        checks.append((
            f"source: {gone[9:-1]} is gone, not left as a second writer",
            gone not in src, "still defined"))
    checks.append((
        "source: one writer for the three board labels and their controls",
        src.count("function applyMarkerLabelState(") == 1
        and src.count("applyMarkerLabelState();") >= 5,
        f"{src.count('applyMarkerLabelState();')} call sites"))
    checks.append((
        "source: one writer for the three sliders' enabled state",
        src.count("function syncLabelScaleEnabled(") == 1
        and src.count("syncLabelScaleEnabled();") == 2,
        f"{src.count('syncLabelScaleEnabled();')} call sites"))
    checks.append((
        "source: the baseline note text lives in one place, as the tooltip",
        src.count("Matches the embedded baseline") == 1,
        f"{src.count('Matches the embedded baseline')} copies"))
    checks.append((
        "source: the action bar is one row with the exports and the right-hand pair split",
        "sd-actions-main" in src and "sd-actions-exports" in src
        and "sd-actions-right" in src and "sd-actions-danger" not in src,
        "the action row containers are not as expected"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("layout", "wkAt144", "labelSeq", "scaleControl", "oneWriter",
                  "remarks", "baseline", "actions", "filterRow", "deps"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
