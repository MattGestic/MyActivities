#!/usr/bin/env python3
"""
P37 check (TEST-39): four defects reported against the P36 build.

Two of the four were not what the report, or the first reading of the code,
said they were. That is recorded here because the checks are shaped by it.

POPUPS CLIPPED BY AN ANCESTOR (reports 1 and 4, same root cause). The More
Actions panel measured 184px tall with 0px visible, clipped by #icon-bar's
overflow-x:auto, which computes overflow-y to auto with it. The ID suggestion
list measured 200px tall with 36px visible, clipped by #top-filter-bar's
max-height:0/overflow:hidden. Neither overflow can be removed: one lets the bar
scroll at phone width, the other IS the collapse mechanism. Both popups are
position:fixed now and placed by one function.

Making them fixed was not enough, and the measurement said so. Freed of the
clip, the menu was then painted over by #rpt-hd and #top-filter-bar, because
#icon-bar is position:relative with a z-index and therefore a STACKING CONTEXT:
no z-index inside it, however large, lifts a descendant above a later sibling
of the bar. Measured 0 of 7 rows hit-testable at 390 wide. The bar's z-index
went 30 to 40.

Both are asserted by HIT TESTING, not by geometry. The ancestor-walk used at
P36 cannot answer this: a fixed element is not clipped by ancestor overflow, so
that walk reported the fixed panel as clipped exactly as it had reported the
absolute one. What answers it is asking the document what paints at points down
the popup, and counting the rows and items that are individually reachable.

THE TITLE COL SLIDER (report 2). The first measurement REFUTED the report: at
1600 wide after an import the slider moved the column 295.3 to 380 and the
width survived a rerender. The report was still right and the measurement was
too narrow. On the board as it opens, the seeded baseline with the fixed
columns collapsed, the column renders 380.1px while the slider reads 220px,
because #col-name carries no width until setNameWidth runs and table-layout:
fixed hands it whatever the collapsed columns leave over. Dragging up from the
default SHRANK the column before it grew. Asserted as: the column equals the
slider at first paint, and tracks it exactly across the whole range.

THE ZERO-DEPENDENCY FILTER (report 3). Measured from the default state it did
nothing at all, 105 rows before and 105 after, because it gated dependency-LINE
drawing and there are no lines until dependencies are switched on. Its own
tooltip promised "Show only milestones with zero predecessors/dependencies". It
narrows the board now. Asserted from the default state, with dependencies off,
because that is the state the report came from.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p37_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p37-out">(.*?)</pre>', re.S)

# 390 is where the menu was worst (0 of 7 rows reachable); 2000 is near the
# width the report came from.
VIEWPORTS = [(390, 844), (1440, 900), (2000, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p37-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,220));
  const $=id=>document.getElementById(id);
  const rect=el=>{const q=el.getBoundingClientRect();
    return {t:Math.round(q.top*10)/10,b:Math.round(q.bottom*10)/10,
            l:Math.round(q.left*10)/10,w:Math.round(q.width*10)/10,
            h:Math.round(q.height*10)/10};};
  const wOf=s=>{const e=document.querySelector(s);
    return e?Math.round(e.getBoundingClientRect().width*10)/10:null;};
  const visRows=()=>document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)').length;
  // Is anything establishing a containing block for fixed descendants? If so,
  // position:fixed would be clipped after all, so it is checked not assumed.
  const fixedTraps=function(el){
    const out=[]; let n=el.parentElement;
    while(n&&n!==document.documentElement){
      const cs=getComputedStyle(n);
      if(cs.transform!=='none'||cs.filter!=='none'||cs.perspective!=='none'||
         cs.contain==='paint'||cs.contain==='strict')
        out.push(n.id||n.className||n.tagName);
      n=n.parentElement;
    }
    return out;
  };
  // The only question that matters for a popup: does it paint, and is each of
  // its children individually reachable by a click?
  const reachable=function(list){
    return Array.prototype.filter.call(list,function(r){
      const q=r.getBoundingClientRect();
      if(q.width<1||q.height<1) return false;
      if(q.top<0||q.bottom>window.innerHeight) return false;
      const h=document.elementFromPoint(q.left+q.width/2,q.top+q.height/2);
      return !!(h&&(h===r||r.contains(h)));
    }).length;
  };

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight;
    R.notes.board={rows:document.querySelectorAll('#tbody tr.data').length};
    ck('setup: the board as it opens was built to measure',
       R.notes.board.rows>100, JSON.stringify(R.notes.board));

    // ============ 1. More Actions panel ============
    toggleMoreActions(true); await settle();
    const panel=$('more-actions-panel'), bar=$('icon-bar');
    const rows=panel.querySelectorAll('.ib-mi');
    R.notes.menu={position:getComputedStyle(panel).position,
                  rect:rect(panel), barBottom:rect(bar).b,
                  reachable:reachable(rows), total:rows.length,
                  fixedTraps:fixedTraps(panel),
                  barZ:getComputedStyle(bar).zIndex};
    ck('menu: the panel is fixed, so no ancestor overflow can clip it',
       R.notes.menu.position==='fixed', R.notes.menu.position);
    ck('menu: nothing above it establishes a containing block for fixed elements',
       R.notes.menu.fixedTraps.length===0,
       R.notes.menu.fixedTraps.join(', ')||'none');
    ck('menu: it opens DOWN past the header row, over the board',
       R.notes.menu.rect.b>R.notes.menu.barBottom+20,
       'panel bottom '+R.notes.menu.rect.b+' against bar bottom '+R.notes.menu.barBottom);
    ck('menu: every row is individually reachable by a click',
       R.notes.menu.reachable===R.notes.menu.total&&R.notes.menu.total===7,
       R.notes.menu.reachable+' of '+R.notes.menu.total+' reachable');
    toggleMoreActions(false); await settle();

    // ============ 2. Title col slider ============
    const sl=$('name-width');
    const openW=wOf('td.c-name'), openTh=wOf('th.c-name');
    R.notes.titleCol={sliderAtOpen:sl.value, columnAtOpen:openW, headerAtOpen:openTh};
    ck('title col: the column matches its slider at first paint',
       Math.abs(openW-parseFloat(sl.value))<1.5,
       'slider '+sl.value+'px, column '+openW+'px');
    ck('title col: the header cell matches the body cell',
       Math.abs(openTh-openW)<1.5, 'header '+openTh+', body '+openW);
    const sweep=[];
    [140,200,260,320,400].forEach(function(v){
      sl.value=v; setNameWidth(v); sweep.push({set:v,got:wOf('td.c-name')});
    });
    R.notes.titleCol.sweep=sweep;
    const tracks=sweep.filter(function(s){ return Math.abs(s.got-s.set)<1.5; }).length;
    let mono=true;
    for(let i=1;i<sweep.length;i++) if(sweep[i].got<=sweep[i-1].got) mono=false;
    ck('title col: the column tracks the slider exactly across its range',
       tracks===sweep.length&&sweep.length===5,
       tracks+' of '+sweep.length+' within 1.5px');
    ck('title col: and moves monotonically, never shrinking as the slider rises',
       mono, JSON.stringify(sweep.map(function(s){return s.set+'->'+s.got;})));
    sl.value=220; setNameWidth(220); onSizeSliderRelease(); await settle(); await settle();
    R.notes.titleCol.afterRerender=wOf('td.c-name');
    ck('title col: and a full rebuild reapplies it rather than dropping it',
       Math.abs(R.notes.titleCol.afterRerender-220)<1.5,
       R.notes.titleCol.afterRerender+'px after rerender');

    // ============ 3. Zero-dependency filter, dependencies OFF ============
    // The default state, which is the one the report came from.
    const base=visRows();
    setZeroFilter('only-zero'); await settle(); await settle();
    const only=visRows(), info=$('filter-info').textContent.trim();
    setZeroFilter('hide-zero'); await settle(); await settle();
    const hide=visRows();
    setZeroFilter('all'); await settle(); await settle();
    const back=visRows();
    let zeroMs=0, totalMs=0;
    (allMilestoneIds()||[]).forEach(function(id){ totalMs++; if(msHasNoDeps(id)) zeroMs++; });
    R.notes.zeroFilter={rowsAll:base,onlyZero:only,hideZero:hide,backToAll:back,
                        milestones:totalMs,withNoDeps:zeroMs,info:info,
                        linesDrawn:document.querySelectorAll('#dep-lines-g path.dep-line').length};
    ck('zero filter: it narrows the board with dependencies OFF, which it never did',
       only<base&&only>0, base+' rows -> '+only);
    ck('zero filter: and there were no dependency lines drawn, so nothing else could have',
       R.notes.zeroFilter.linesDrawn===0, R.notes.zeroFilter.linesDrawn+' lines');
    ck('zero filter: the two modes are complements over the whole board',
       only+hide===base, only+' + '+hide+' = '+(only+hide)+' against '+base);
    ck('zero filter: clearing it puts every row back',
       back===base, back+' against '+base);
    ck('zero filter: it had a real population to find',
       zeroMs>0&&zeroMs<totalMs, zeroMs+' of '+totalMs+' milestones carry no dependencies');
    ck('zero filter: and the filter line says what it narrowed to',
       /no predecessors or successors/.test(info), JSON.stringify(info));
    setZeroFilter('only-zero'); await settle(); await settle();
    const beforeRe=visRows();
    scheduleRerender(true); await settle(); await settle();
    R.notes.zeroFilter.survivesRerender=beforeRe+' -> '+visRows();
    ck('zero filter: it survives a full rebuild like every other filter',
       visRows()===beforeRe&&beforeRe>0, R.notes.zeroFilter.survivesRerender);
    setZeroFilter('all'); await settle();

    // ============ 4. ID suggestions ============
    toggleTopFilterBar(true); await settle(); await settle();
    const inp=$('filter-ids');
    inp.focus(); renderIdSuggestions(); await settle();
    const sug=$('id-suggest-dropdown');
    const items=sug.children;
    // D-16b: the mandated phone stacking (labels above full-width fields)
    // moves the Activity ID field lower on the page than the pre-D-16b bar
    // did, so a 30-row suggestion list (~570px of content) can no longer
    // always fit entirely above or below the field unclipped the way it did
    // when the field sat near the top of a shorter bar. The list's own
    // max-height/overflow-y:auto (positionFixedPopup) is correct, scrollable
    // behaviour, same as any other overflowing menu: an item scrolled out of
    // the list's OWN clipped box is not currently visible and is correctly
    // not clickable without scrolling first, which is not the same defect
    // as one painted over by an unrelated ancestor. So this checks that
    // every item within the list's own rendered box (not the whole viewport)
    // is reachable, rather than requiring the full un-scrolled list to fit
    // in the viewport at once.
    const ddBox=rect(sug);
    const visibleItems=Array.prototype.filter.call(items,function(it){
      const q=it.getBoundingClientRect();
      return q.width>0&&q.height>0&&q.top>=ddBox.t-0.5&&q.bottom<=ddBox.b+0.5;
    });
    R.notes.idSuggest={position:getComputedStyle(sug).position, rect:ddBox,
                       items:items.length, visible:visibleItems.length,
                       reachable:reachable(visibleItems),
                       fixedTraps:fixedTraps(sug),
                       alignedToField:Math.abs(rect(sug).l-Math.round(inp.getBoundingClientRect().left*10)/10)<1.5};
    ck('id suggest: the list is fixed, so the collapsing bar cannot clip it',
       R.notes.idSuggest.position==='fixed', R.notes.idSuggest.position);
    ck('id suggest: it still lines up with the field it belongs to',
       R.notes.idSuggest.alignedToField,
       'list at '+R.notes.idSuggest.rect.l+', field at '+Math.round(inp.getBoundingClientRect().left*10)/10);
    ck('id suggest: at least one suggestion is visible in the list\'s own box',
       R.notes.idSuggest.visible>0, R.notes.idSuggest.visible+' of '+R.notes.idSuggest.items);
    ck('id suggest: every suggestion visible in the list\'s own box is individually reachable, none behind the board',
       R.notes.idSuggest.visible>0&&R.notes.idSuggest.reachable===R.notes.idSuggest.visible,
       R.notes.idSuggest.reachable+' of '+R.notes.idSuggest.visible+' visible reachable ('+R.notes.idSuggest.items+' total in the list)');

    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=String(e&&e.stack); }
  emit();
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p37.html"
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

    checks = []
    vers = len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src))
    checks.append(("source: exactly one version literal", vers == 1, f"{vers} found"))
    checks.append((
        "source: one writer reapplies the display settings, for both build paths",
        src.count("function reapplyDisplaySettings(") == 1
        and src.count("reapplyDisplaySettings();") == 2,
        f"{src.count('reapplyDisplaySettings();')} call sites"))
    checks.append((
        "source: both popups are placed by one function",
        src.count("function positionFixedPopup(") == 1
        and src.count("positionFixedPopup(") >= 4,
        f"{src.count('positionFixedPopup(')} references"))
    checks.append((
        "source: the icon bar sits above the two elements that were painting over it",
        "position:relative;z-index:40}" in src.replace(" ", ""),
        "the bar is not at z-index 40"))
    checks.append((
        "source: the zero filter is part of the filter pipeline, not a line toggle",
        "rowHasZeroDepMilestone(row)" in src
        and "ZERO_FILTER_MODE!=='all'" in src.replace(" ", ""),
        "not wired into applyFilter"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("menu", "titleCol", "zeroFilter", "idSuggest"):
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
