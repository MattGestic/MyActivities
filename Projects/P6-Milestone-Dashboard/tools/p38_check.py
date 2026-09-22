#!/usr/bin/env python3
"""
P38 check (TEST-40): print-preview heading, date-range activation, view defaults.

THE HEADING BARS WERE VIEWPORT WIDTH, THE SHEET WAS NOT. #icon-bar and
.pm-banner sit outside #page-frame, so they took the body's width, which is the
viewport's. Measured on P37: bar and banner 390px wide at phone width and
1440px at desktop, against a 1122.5px A3 sheet. 732px short of the sheet in one
direction, 317px over it in the other, which is the misalignment reported.
Asserted as equality of three edges, and separately as equality of the CONTENT
boxes, since aligning the outer edges alone would still leave the bar's text
offset from the report heading by the frame's 8mm padding.

THE PREVIEW HAD NO CONTROLS OF ITS OWN. Three are added to the banner: re-fit
to the page, leave the preview, and the same More Actions panel. The panel is
not duplicated, the ANCHOR moves, so the seven row ids and the five functions
that write them are untouched. Asserted by hit test, per trigger, plus the
placement actually following the trigger that was clicked.

THE DATE RANGE ALREADY HANDLED ONE OPEN END. The first measurement REFUTED the
report as written: with a `change` event dispatched, a to-date alone narrowed
the board to 20 of 39 weeks and a from-date alone to 24 of 39, at both 390 and
1440. dateRangeToCols() has always left the other end open. What did not work
was the DELIVERY: `change` on a date input does not fire until the field is
committed and left, so a date set with the picker or the spinner sat there doing
nothing. The fix is `oninput`, and the assertion dispatches `input` ONLY. A
probe that fires `change` cannot see this defect at all, which is why the first
one passed.

THE DEFAULTS. Hours labels off, Activity ID labels on. Asserted at first paint
from the rendered board, not from the variables, and each direction carries a
NEGATIVE CONTROL: the hours check is re-run with the toggle flipped and must go
the other way, or "0 visible" would pass on a board that renders no hours at
all for unrelated reasons.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p38_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p38-out">(.*?)</pre>', re.S)

# 390: the sheet is WIDER than the viewport, so the bars fell short of it.
# 1440: the sheet is NARROWER, so the bars overhung it. Opposite failures, one
# fix, so both are measured. 1024 sits between them.
VIEWPORTS = [(390, 844), (1024, 800), (1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p38-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const $=id=>document.getElementById(id);
  const r1=v=>Math.round(v*10)/10;
  const box=function(el){
    if(!el) return null;
    const q=el.getBoundingClientRect(), cs=getComputedStyle(el);
    const bl=parseFloat(cs.borderLeftWidth)||0, br=parseFloat(cs.borderRightWidth)||0;
    const pl=parseFloat(cs.paddingLeft)||0, pr=parseFloat(cs.paddingRight)||0;
    return {l:r1(q.left),r:r1(q.right),w:r1(q.width),
            cl:r1(q.left+bl+pl),cr:r1(q.right-br-pr)};
  };
  // Visible week-header columns. The date range hides columns with a generated
  // stylesheet, so display has to be read computed, not from inline style.
  const visWk=()=>Array.prototype.filter.call(
    document.querySelectorAll('th.col-wk[data-col]'),
    function(th){ return getComputedStyle(th).display!=='none'; }).length;
  const visRows=()=>document.querySelectorAll('#tbody tr.data:not(.hidden-row)').length;
  // Painted, on screen, and the point in the middle of it belongs to it. The
  // same profile used at P37: geometry alone cannot answer "can this be
  // clicked", and an ancestor walk cannot answer it for a fixed element.
  const reachable=function(list){
    return Array.prototype.filter.call(list,function(el){
      const q=el.getBoundingClientRect();
      if(q.width<1||q.height<1) return false;
      if(q.top<0||q.bottom>window.innerHeight) return false;
      if(getComputedStyle(el).visibility==='hidden') return false;
      const h=document.elementFromPoint(q.left+q.width/2,q.top+q.height/2);
      return !!(h&&(h===el||el.contains(h)));
    }).length;
  };
  const wkw=()=>parseInt($('wk-width').value,10);

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight;

    // ============ 0. view defaults, at first paint ============
    const shortTitles=document.querySelectorAll('#tbody .m-short-title');
    const hrsAll=document.querySelectorAll('#tbody .m-hrs,#tbody .m-hrs-loe');
    const shown=function(list){
      return Array.prototype.filter.call(list,function(e){
        return getComputedStyle(e).display!=='none'; }).length; };
    const idLike=Array.prototype.filter.call(shortTitles,function(e){
      return /^#\S/.test(e.textContent.trim()); }).length;
    R.notes.defaults={shortTitles:shortTitles.length,shownTitles:shown(shortTitles),
                      idLike:idLike,hrsNodes:hrsAll.length,shownHrs:shown(hrsAll),
                      mhrsChecked:$('btn-mhrs').checked,
                      idBtnActive:$('btn-title-mode-id').classList.contains('active'),
                      offBtnActive:$('btn-title-mode-off').classList.contains('active'),
                      lblChecked:$('btn-lbl').checked};
    ck('defaults: the board renders a short-title label on every milestone at first paint',
       R.notes.defaults.shownTitles>100&&R.notes.defaults.shownTitles===R.notes.defaults.shortTitles,
       R.notes.defaults.shownTitles+' shown of '+R.notes.defaults.shortTitles+' rendered');
    // NOT "every label starts with #". 38 of the 196 milestones on the seeded
    // board carry no Activity ID, and formatShortTitleDisplay() falls back to
    // the title for those, which is correct. What distinguishes 'id' from the
    // other two modes is that no label carries the ' _ ' that 'both' inserts,
    // and that most of them are IDs.
    const joiner=Array.prototype.filter.call(shortTitles,function(e){
      return e.textContent.indexOf(' _ ')>=0; }).length;
    R.notes.defaults.joiner=joiner;
    ck('defaults: the labels are Activity IDs, and none is an ID+title pair',
       R.notes.defaults.idLike>150&&joiner===0&&SHORT_TITLE_MODE==='id',
       R.notes.defaults.idLike+' of '+R.notes.defaults.shortTitles+
       ' start with #, '+joiner+' carry the ID+title joiner, mode '+SHORT_TITLE_MODE);
    // NEGATIVE CONTROL for the mode. If the joiner count could not tell 'id'
    // from 'both', it would read 0 in both modes.
    setShortTitleMode('both'); await settle(); await settle();
    const bothJoin=Array.prototype.filter.call(
      document.querySelectorAll('#tbody .m-short-title'),
      function(e){ return e.textContent.indexOf(' _ ')>=0; }).length;
    setShortTitleMode('id'); await settle(); await settle();
    const backJoin=Array.prototype.filter.call(
      document.querySelectorAll('#tbody .m-short-title'),
      function(e){ return e.textContent.indexOf(' _ ')>=0; }).length;
    R.notes.defaults.modeControl={both:bothJoin,backToId:backJoin};
    ck('defaults NEGATIVE CONTROL: the same measurement sees ID+title when that mode is set',
       bothJoin>150&&backJoin===0,
       bothJoin+' paired in both-mode, '+backJoin+' back in id-mode');
    ck('defaults: the control says ID, matching what is on the board',
       R.notes.defaults.idBtnActive&&!R.notes.defaults.offBtnActive,
       'id active '+R.notes.defaults.idBtnActive+', off active '+R.notes.defaults.offBtnActive);
    ck('defaults: no hours label is visible, and the toggle agrees',
       R.notes.defaults.shownHrs===0&&R.notes.defaults.mhrsChecked===false,
       R.notes.defaults.shownHrs+' visible of '+R.notes.defaults.hrsNodes+
       ' rendered, checkbox '+R.notes.defaults.mhrsChecked);
    ck('defaults: the type-code label stays off, as it was',
       R.notes.defaults.lblChecked===false, 'btn-lbl '+R.notes.defaults.lblChecked);
    // NEGATIVE CONTROL. "0 visible" has to mean the toggle is off, not that
    // there is nothing to see: flipping it must make them appear, and flipping
    // it back must take them away again.
    $('btn-mhrs').checked=true; toggleMHours($('btn-mhrs')); await settle();
    const hrsOn=shown(document.querySelectorAll('#tbody .m-hrs,#tbody .m-hrs-loe'));
    $('btn-mhrs').checked=false; toggleMHours($('btn-mhrs')); await settle();
    const hrsOff=shown(document.querySelectorAll('#tbody .m-hrs,#tbody .m-hrs-loe'));
    R.notes.defaults.negControl={on:hrsOn,backOff:hrsOff};
    ck('defaults NEGATIVE CONTROL: the same measurement sees hours when they are on',
       hrsOn>100&&hrsOff===0, hrsOn+' visible with the toggle on, '+hrsOff+' back off');

    // ============ 1. date range, input event ONLY ============
    // No `change` anywhere in this block. That is the point of it.
    const from=$('filter-date-from'), to=$('filter-date-to');
    const put=async function(el,v){ el.value=v;
      el.dispatchEvent(new Event('input',{bubbles:true}));
      await settle(); await settle(); };
    const base={visWk:visWk(),rows:visRows()};
    R.notes.range={total:document.querySelectorAll('th.col-wk[data-col]').length,base:base};
    ck('range: the board opens unfiltered, so a narrowing is visible',
       base.visWk===R.notes.range.total&&base.visWk>20,
       base.visWk+' of '+R.notes.range.total+' week columns, '+base.rows+' rows');

    await put(to,'2026-09-30');
    R.notes.range.toOnly={cols:DATE_RANGE_COLS,visWk:visWk(),rows:visRows()};
    ck('range: an END date alone narrows the board, on input, with no change event',
       !!DATE_RANGE_COLS&&R.notes.range.toOnly.visWk<base.visWk&&R.notes.range.toOnly.visWk>0,
       JSON.stringify(R.notes.range.toOnly));
    ck('range: an END date alone leaves the START open, at column 0',
       !!DATE_RANGE_COLS&&DATE_RANGE_COLS.lo===0, JSON.stringify(DATE_RANGE_COLS));

    await put(to,'');
    R.notes.range.cleared={cols:DATE_RANGE_COLS,visWk:visWk(),rows:visRows()};
    ck('range: clearing it puts every column back',
       DATE_RANGE_COLS===null&&visWk()===R.notes.range.total,
       JSON.stringify(R.notes.range.cleared));

    await put(from,'2026-09-01');
    R.notes.range.fromOnly={cols:DATE_RANGE_COLS,visWk:visWk(),rows:visRows()};
    ck('range: a START date alone narrows the board, on input',
       !!DATE_RANGE_COLS&&R.notes.range.fromOnly.visWk<base.visWk&&R.notes.range.fromOnly.visWk>0,
       JSON.stringify(R.notes.range.fromOnly));
    ck('range: a START date alone leaves the END open, at the last column',
       !!DATE_RANGE_COLS&&DATE_RANGE_COLS.hi===R.notes.range.total-1,
       JSON.stringify(DATE_RANGE_COLS));

    // Adding the second end must narrow further, and re-setting it must move
    // the board again: the reported case was setting one end and seeing
    // nothing happen until focus left the field.
    await put(to,'2026-10-31');
    const both={cols:JSON.parse(JSON.stringify(DATE_RANGE_COLS)),visWk:visWk(),rows:visRows()};
    await put(to,'2026-09-15');
    const tighter={cols:JSON.parse(JSON.stringify(DATE_RANGE_COLS)),visWk:visWk(),rows:visRows()};
    R.notes.range.both=both; R.notes.range.tighter=tighter;
    ck('range: re-setting the END end moves the board again, on input',
       tighter.visWk<both.visWk&&both.visWk<R.notes.range.fromOnly.visWk,
       'from-only '+R.notes.range.fromOnly.visWk+' -> both '+both.visWk+' -> tighter '+tighter.visWk);
    await put(from,''); await put(to,'');
    ck('range: cleared again before the rest of the run',
       DATE_RANGE_COLS===null&&visRows()===base.rows,
       visRows()+' rows against '+base.rows);

    // ============ 2. print preview: the three edges ============
    const wkBefore=wkw();
    togglePrintMode(true); await settle(); await settle();
    const frame=box($('page-frame')), bar=box($('icon-bar')), ban=box($('pm-banner'));
    const hd=box(document.querySelector('.rpt-hd'));
    R.notes.print={frame:frame,bar:bar,banner:ban,rptHd:hd,
                   fitted:wkw(),wkBefore:wkBefore,
                   bannerDetail:($('pm-banner-detail')||{}).textContent};
    const near=(a,b)=>Math.abs(a-b)<=1.0;
    ck('print: the icon bar takes the sheet edges, not the viewport',
       near(bar.l,frame.l)&&near(bar.r,frame.r),
       'bar '+bar.l+'..'+bar.r+' against sheet '+frame.l+'..'+frame.r);
    ck('print: the banner takes the sheet edges too',
       near(ban.l,frame.l)&&near(ban.r,frame.r),
       'banner '+ban.l+'..'+ban.r+' against sheet '+frame.l+'..'+frame.r);
    ck('print: the bar CONTENT lines up with the report heading, not just its outer edge',
       near(bar.cl,hd.l)&&near(bar.cr,hd.r),
       'bar content '+bar.cl+'..'+bar.cr+' against heading '+hd.l+'..'+hd.r);
    ck('print: the banner CONTENT lines up with it as well',
       near(ban.cl,hd.l)&&near(ban.cr,hd.r),
       'banner content '+ban.cl+'..'+ban.cr+' against heading '+hd.l+'..'+hd.r);

    // ============ 3. the three banner controls ============
    const ctrls=document.querySelectorAll('#pm-banner .pm-btn');
    R.notes.controls={total:ctrls.length,reachable:reachable(ctrls),
                      ids:Array.prototype.map.call(ctrls,function(b){return b.id;})};
    ck('print: all three preview controls are on screen and individually clickable',
       R.notes.controls.total===3&&R.notes.controls.reachable===3,
       R.notes.controls.reachable+' of '+R.notes.controls.total+' reachable: '+
       R.notes.controls.ids.join(', '));

    // Fit. Moved away from the fitted width, the button has to bring it back.
    const fitted=wkw();
    $('wk-width').value=String(Math.min(72,fitted+9)); setWkWidth($('wk-width').value);
    await settle();
    const moved=wkw();
    $('btn-pm-fit').click(); await settle(); await settle();
    R.notes.fit={fitted:fitted,moved:moved,refitted:wkw()};
    ck('print: the Fit control re-fits the columns to the page width',
       moved!==fitted&&wkw()===fitted,
       'fitted '+fitted+', moved to '+moved+', refitted '+wkw());

    // More Actions, from the banner trigger. The panel is single, so the test
    // is that it follows the trigger that was clicked.
    $('btn-pm-more').click(); await settle();
    const panel=$('more-actions-panel');
    const pb=panel.getBoundingClientRect(), tb=$('btn-pm-more').getBoundingClientRect();
    const rows=panel.querySelectorAll('.ib-mi');
    R.notes.menuFromBanner={open:panel.classList.contains('open'),
      panelRight:r1(pb.right),triggerRight:r1(tb.right),
      panelTop:r1(pb.top),triggerBottom:r1(tb.bottom),
      reachable:reachable(rows),total:rows.length,
      ariaBanner:$('btn-pm-more').getAttribute('aria-expanded'),
      ariaHeader:$('btn-more-actions').getAttribute('aria-expanded')};
    ck('print: the banner trigger opens the menu, anchored to itself',
       R.notes.menuFromBanner.open&&near(pb.right,tb.right)&&pb.top>=tb.bottom,
       'panel right '+r1(pb.right)+' against trigger right '+r1(tb.right)+
       ', panel top '+r1(pb.top)+' against trigger bottom '+r1(tb.bottom));
    ck('print: every menu row opened from the banner is individually clickable',
       R.notes.menuFromBanner.reachable===R.notes.menuFromBanner.total&&
       R.notes.menuFromBanner.total===7,
       R.notes.menuFromBanner.reachable+' of '+R.notes.menuFromBanner.total);
    ck('print: both triggers report the panel open, since both describe it',
       R.notes.menuFromBanner.ariaBanner==='true'&&R.notes.menuFromBanner.ariaHeader==='true',
       'banner '+R.notes.menuFromBanner.ariaBanner+', header '+R.notes.menuFromBanner.ariaHeader);
    toggleMoreActions(false); await settle();

    // The header trigger has to still anchor to ITSELF, or moving the anchor
    // would have broken the control that was already there. Conditional on
    // MEASURED room, not on a typed viewport width: the header bar is one A3
    // sheet wide in the preview, so at anything narrower than 1122.5px its
    // right-hand trigger has scrolled off the visible area and the panel is
    // clamped into the viewport instead, which is what positionFixedPopup is
    // for. Both outcomes require a fully reachable panel.
    $('btn-more-actions').click(); await settle();
    const pb2=panel.getBoundingClientRect(), hb=$('btn-more-actions').getBoundingClientRect();
    const hdrOnScreen=hb.right<=window.innerWidth&&hb.left>=0;
    R.notes.menuFromHeader={open:panel.classList.contains('open'),
      panelRight:r1(pb2.right),triggerRight:r1(hb.right),
      triggerOnScreen:hdrOnScreen,inViewport:pb2.right<=window.innerWidth+1&&pb2.left>=-1,
      reachable:reachable(panel.querySelectorAll('.ib-mi'))};
    ck('print: the header trigger still opens a fully reachable panel'+
       (hdrOnScreen?', anchored to itself':', clamped into the viewport since it has scrolled off the sheet'),
       R.notes.menuFromHeader.open&&R.notes.menuFromHeader.reachable===7&&
       (hdrOnScreen?near(pb2.right,hb.right):R.notes.menuFromHeader.inViewport),
       JSON.stringify(R.notes.menuFromHeader));
    toggleMoreActions(false); await settle();

    // Leave. The control has to do what the header row does, including putting
    // the week width back.
    $('btn-pm-leave').click(); await settle(); await settle();
    const barOut=box($('icon-bar'));
    R.notes.leave={printMode:document.body.classList.contains('print-mode'),
                   wk:wkw(),wkBefore:wkBefore,barW:barOut.w,innerW:window.innerWidth,
                   bannerShown:getComputedStyle($('pm-banner')).display!=='none'};
    ck('print: the Leave control leaves the preview and restores the week width',
       !R.notes.leave.printMode&&R.notes.leave.wk===wkBefore&&!R.notes.leave.bannerShown,
       JSON.stringify(R.notes.leave));
    ck('print: the icon bar goes back to viewport width, leaving no sheet sizing behind',
       Math.abs(barOut.w-window.innerWidth)<=1.0,
       barOut.w+' against viewport '+window.innerWidth);

    // Out of the preview, the banner trigger is not laid out, so the anchor
    // falls back to the header one. Checked, because a stale anchor would place
    // the panel against nothing.
    $('btn-more-actions').click(); await settle();
    const pb3=panel.getBoundingClientRect(), hb3=$('btn-more-actions').getBoundingClientRect();
    R.notes.menuAfter={open:panel.classList.contains('open'),
                       reachable:reachable(panel.querySelectorAll('.ib-mi')),
                       anchoredToHeader:Math.abs(pb3.right-hb3.right)<=1.0,
                       pmTriggerRects:$('btn-pm-more').getClientRects().length};
    ck('after the preview: the menu still opens from the header, anchored to it',
       R.notes.menuAfter.open&&R.notes.menuAfter.reachable===7&&
       R.notes.menuAfter.anchoredToHeader&&R.notes.menuAfter.pmTriggerRects===0,
       JSON.stringify(R.notes.menuAfter));
    toggleMoreActions(false);
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
        tmp = pathlib.Path(td) / "p38.html"
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
    # Not measurable headless: print media emulation needs CDP. Stated as a
    # source check rather than dressed up as a runtime one.
    checks.append((
        "source: the banner and its controls are one element, hidden on paper",
        src.count('class="pm-banner pm-hide-in-print"') == 1,
        "the banner does not carry pm-hide-in-print"))
    # Three since v3.1.0-P40: the two date fields, and the float threshold,
    # which is a typed number with exactly the same problem (change does not
    # fire until the field is left). The count is asserted rather than left
    # open-ended so a field losing its oninput still fails this.
    n_input = src.count('oninput="scheduleFilter()" onchange="applyFilter()"')
    checks.append((
        "source: both date fields and the float threshold fire on input as well as on change",
        n_input == 3, f"{n_input} of 3 fields carry both handlers"))
    checks.append((
        "source: one panel, one anchor resolver, no duplicated menu rows",
        src.count('id="more-actions-panel"') == 1
        and src.count("function moreActionsAnchor(") == 1
        # One definition plus the three placers: open, resize, scroll. A
        # fourth placer added without going through the resolver would leave a
        # popup anchored to whichever trigger is hardcoded there.
        and src.count("moreActionsAnchor()") == 4
        and src.count("positionFixedPopup(panel,") == 3,
        f"{src.count('moreActionsAnchor()')} anchor references, "
        f"{src.count('positionFixedPopup(panel,')} panel placements"))
    checks.append((
        "source: the two heading bars are sized from the sheet token",
        "body.print-mode#icon-bar,body.print-mode.pm-banner{width:var(--page-sheet-w)" in nospace,
        "the print-mode sizing rule is not there"))
    checks.append((
        "source: the ID default is stated in the script and in the markup",
        "SHORT_TITLE_MODE='id'" in nospace and "shortTitlesVisible=true" in nospace
        and 'class="toggle-btn active" id="btn-title-mode-id"' in src,
        "script and markup disagree on the default"))
    checks.append((
        "source: the hours default is off in the script and unchecked in the markup",
        "letmHrsVisible=false" in nospace
        and 'id="btn-mhrs" onchange' in src and 'id="btn-mhrs" checked' not in src,
        "script and markup disagree on the default"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("defaults", "range", "print", "controls", "fit",
                  "menuFromBanner", "menuFromHeader", "leave", "menuAfter"):
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
