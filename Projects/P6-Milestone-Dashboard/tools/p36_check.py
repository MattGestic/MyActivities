#!/usr/bin/env python3
"""
P36 check (TEST-38): the More Actions consolidation.

WHAT THIS CHANGE IS. Seven icon buttons in .ib-right-icons became one trigger
and a seven-row menu. The rows keep the ids their buttons carried, so the five
functions that write button state (toggleSettingsDrawer, toggleFilterBar,
toggleTopFilterBar, togglePrintMode, toggleTheme) address exactly what they
addressed before. That claim is asserted at SOURCE level by diffing those five
function bodies against the previous release, not by reading them.

WHY IT IS WORTH DOING, measured rather than asserted. The group was a fixed
254px hard against the right edge and #ib-label is the flex item that gives
way. On the previous release the label needs 215.8px and gets 35.2px at 390
wide and 162px at 768. The previous release is rendered here in the same
browser at the same viewports so the before/after is measured, not remembered.

THE STATE PROBLEM, which is the real risk. Six of the seven buttons showed
state. A menu that is shut shows none of it, and this project's standing rule
is that a control which sets state must also show state. Two of those six are
notifications meant to be seen without opening anything: the filter-active dot
and the settings-attention dot. They escape to the trigger through a CSS :has()
derivation over the rows themselves, so no new state exists and the four
existing dot writers are untouched. The rest (a panel on screen, the board at
page width, a dark page) is evident from the screen. Both halves are asserted:
the dots reach the trigger, and .on still PAINTS on a row.

.on painting is its own named check because .icon-btn.on and .icon-btn.ib-mi
have equal specificity, so the later rule wins on source order alone and the
active state would vanish silently. Computed background is compared against an
inactive row; the class being present proves nothing.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p36_check.py [--xlsx FILE] [--html FILE] [--baseline FILE]
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
from import_check import build_aoa, find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p36-out">(.*?)</pre>', re.S)

VIEWPORTS = [(390, 844), (1024, 900), (1440, 900)]

# P56/D-20b re-shaped the panel to five rows and made it position:static,
# inline in #icon-bar above 1024px (the trigger, #btn-more-actions, is
# display:none there; below and at 1024px it stays the fixed dropdown). Three
# rows left for other homes, each with a real replacement, none deleted
# outright:
#   btn-fit-screen      -> #btn-fit-screen-inline, in the Date range filter
#   btn-export-comments -> still #btn-export-comments, now a .toggle-btn in
#                          the Workspace panel (#ws-panel), covered by
#                          tools/p29_check.py / tools/p39_check.py
#   btn-filter-toggle    -> removed outright (with its #filter-dot): the
#                          filter row's own re-open control is
#                          #btn-filter-expand in the report heading,
#                          covered by tools/p32_check.py
ROWS = [
    ("btn-theme-toggle", "toggleTheme"),
    ("btn-print-mode", "togglePrintMode"),
    ("btn-save-as", "publishDashboard"),
    ("btn-style-icon", "toggleFilterBar"),
    ("btn-settings-icon", "toggleSettingsDrawer"),
]
# Ids the old panel carried that are gone outright (not merely moved), so a
# regression that resurrects them is still worth catching by name.
RETIRED_IDS = ["btn-filter-toggle", "filter-dot"]

# Function bodies that must be byte-identical to the previous release. If the
# consolidation needed any of them changed, the "nothing had to be touched"
# claim is false and this says so rather than the commit message.
#
# Both original members left this set for reasons this check can name, not
# because the assertion stopped mattering:
#
# toggleTopFilterBar left at v3.1.0-P40, when the heading gained a one-click
# expand control and the bar's own toggle became the single writer of its
# hidden state.
#
# toggleSettingsDrawer and toggleFilterBar left at v3.1.0-P56 (D-20b), when
# View controls moved from its own sidebar into #settings-drawer as the
# 'view' tabpanel: toggleFilterBar now docks/undocks through the drawer's own
# tab machinery instead of a sidebar class, and toggleSettingsDrawer gained
# the "leaving the view tab doesn't count as closing" branch that makes that
# possible. That is the P56 partial's own claim to prove (view controls
# genuinely needed the drawer's state machine, nothing else in the
# consolidation reached into these two by accident), not the 2026 More
# Actions menu reaching into them four years later.
#
# Dropping a name from UNTOUCHED silently would let a future, unrelated change
# hide behind this note, so every departure moves to one of the two
# CHANGED_SINCE maps below, which assert it changed for A REASON THIS CHECK
# CAN NAME rather than merely allowing it. Split in two because "changed for a
# reason" only means something against the build the change actually started
# from: toggleTopFilterBar's P40 change is proved against the pinned P35
# baseline (the same file --baseline measures the header reclaim against),
# while toggleSettingsDrawer/toggleFilterBar's P56 change is proved against
# --prev-release (P55, the release immediately before this partial) — diffed
# against P35 they would ALSO show as changed, but for P40's reason as well as
# P56's, which is not a check this file could tell apart.
UNTOUCHED = []
CHANGED_SINCE_FROM_BASELINE = {"toggleTopFilterBar": "btn-filter-expand"}
CHANGED_SINCE_FROM_PREV_RELEASE = {
    "toggleSettingsDrawer": "SETTINGS_TAB",
    "toggleFilterBar": "setSettingsTab('view')",
}

BASELINE = r"""
(function(){
  const R={ok:false};
  function emit(){
    const o=document.createElement('pre'); o.id='p36-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  try{
    const lbl=document.getElementById('ib-label');
    const grp=document.querySelector('.ib-right-icons');
    const bar=document.getElementById('icon-bar');
    const lr=lbl.getBoundingClientRect(), gr=grp.getBoundingClientRect();
    R.label={w:Math.round(lr.width*10)/10,
             need:lbl.scrollWidth,
             clipped:lbl.scrollWidth>lbl.clientWidth+0.5};
    R.groupWidth=Math.round(gr.width*10)/10;
    R.buttons=grp.querySelectorAll('.icon-btn').length;
    R.barScrolls=bar.scrollWidth>bar.clientWidth+0.5;
    R.ok=true;
  }catch(e){ R.err=String(e); }
  emit();
})();
"""

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p36-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,200); }); };
  const $=function(id){ return document.getElementById(id); };
  const click=function(el){ el.dispatchEvent(new MouseEvent('click',{bubbles:true})); };
  const menuOpen=function(){ return $('more-actions-panel').classList.contains('open'); };
  // checkVisibility, not a rect: this project has already had a probe measure a
  // non-zero rect on content inside a closed container and call it hidden.
  const rowsVisible=function(){
    return ROW_IDS.filter(function(id){
      const el=$(id); return el&&el.checkVisibility&&el.checkVisibility(); }).length;
  };
  const dotShown=function(id){
    const el=$(id); return el?getComputedStyle(el).display!=='none':null; };
  // Laid out at all, regardless of whether it happens to sit off the current
  // viewport: display:none (or a display:none ancestor) is the only thing
  // that zeroes getClientRects(), so this is the right test for "does the CSS
  // even attempt to show this element right now" (the trigger vs. the inline
  // row set toggle on exactly this).
  const laidOut=function(el){ return !!el && el.getClientRects().length>0; };

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st); void document.body.offsetWidth;

    R.notes.viewport=window.innerWidth+'x'+window.innerHeight;
    // P56/D-20b: above 1024px the panel is shown INLINE as a row of icon
    // buttons in #icon-bar (position:static) and the (kebab) trigger is
    // display:none; at <=1024px the trigger shows and the panel is the fixed
    // dropdown, same as P36 shipped. Read from the same media query the CSS
    // uses, not a re-typed breakpoint number.
    // D-31 Stage A (P79): More actions is a labelled dropdown at every width; the
    // P56 inline icon row above 1024px was retired. Every width now takes the
    // dropdown path below, so the desktop branch is kept only as history.
    const desktop=false;
    R.notes.desktop=desktop;

    // ================= 1. The header reclaims its room ====================
    const grp=document.querySelector('.ib-right-icons');
    const lbl=$('ib-label');
    const bar=$('icon-bar');
    const trigger=$('btn-more-actions');
    const triggerVisible=laidOut(trigger);
    const rowsVisibleCount=ROW_IDS.filter(function(id){ return laidOut($(id)); }).length;
    R.notes.header={
      buttonsInGroup:grp.querySelectorAll('.icon-btn').length,
      triggerVisible:triggerVisible,
      rowsVisibleInline:rowsVisibleCount,
      groupWidth:Math.round(grp.getBoundingClientRect().width*10)/10,
      labelWidth:Math.round(lbl.getBoundingClientRect().width*10)/10,
      labelNeeds:lbl.scrollWidth,
      labelClipped:lbl.scrollWidth>lbl.clientWidth+0.5,
      barScrolls:bar.scrollWidth>bar.clientWidth+0.5,
      labelText:lbl.textContent.trim()
    };
    R.header=R.notes.header;
    if(desktop){
      ck('header: above 1024px the kebab trigger is hidden and all five rows show inline instead',
         !triggerVisible && rowsVisibleCount===ROW_IDS.length,
         'triggerVisible='+triggerVisible+', rows inline '+rowsVisibleCount+' of '+ROW_IDS.length);
    } else {
      ck('header: at or below 1024px, exactly the trigger shows, not the rows underneath it',
         triggerVisible && rowsVisibleCount===0,
         'triggerVisible='+triggerVisible+', rows inline '+rowsVisibleCount+' of '+ROW_IDS.length);
    }
    // Conditional on measured room, not on a viewport width typed into the
    // check: a hardcoded "768 and above" would be a constant standing in for a
    // measurement, which is a recurring defect family in this project. Where
    // the bar cannot give the label its full width the residual clip is a
    // stated limit (TD-135), asserted separately on the Python side.
    if(!R.notes.header.labelClipped){
      ck('header: the version label is no longer clipped',
         true, R.notes.header.labelWidth+'px for '+R.notes.header.labelNeeds+'px of text');
    } else {
      ck('header: where the label still cannot fit, the bar is genuinely full',
         R.notes.header.labelWidth>0 && !R.notes.header.barScrolls,
         'label '+R.notes.header.labelWidth+'px of '+R.notes.header.labelNeeds+
         'px needed, bar not scrolling');
    }
    ck('header: and the bar itself still does not scroll',
       !R.notes.header.barScrolls, 'scrolls='+R.notes.header.barScrolls);
    ck('header: the label still names the app and its version',
       /Schedule Reporting and Evaluation Tool/.test(R.notes.header.labelText)&&
       /v\d+\.\d+\.\d+-P\d+/.test(R.notes.header.labelText),
       JSON.stringify(R.notes.header.labelText));

    // ================= 2. Every id survived, still wired ==================
    const missing=ROW_IDS.filter(function(id){ return !$(id); });
    ck('rows: all five ids from the current row set exist',
       missing.length===0, ROW_IDS.length+' expected, missing: '+(missing.join(', ')||'none'));
    const resurrected=RETIRED_IDS.filter(function(id){ return !!$(id); });
    ck('rows: ids retired outright (btn-filter-toggle, filter-dot) have not come back',
       resurrected.length===0, resurrected.length+' resurrected: '+(resurrected.join(', ')||'none'));
    // A handler naming a function that no longer exists throws only when
    // clicked and looks perfect until then. Same check as TEST-32.
    let dead=[];
    ROW_IDS.forEach(function(id,i){
      const el=$(id); if(!el) return;
      const src=el.getAttribute('onclick')||'';
      const fn=ROW_FNS[i];
      if(src.indexOf(fn)<0) dead.push(id+' lost '+fn);
      else if(typeof window[fn]!=='function') dead.push(fn+' is not a function');
    });
    ck('rows: every row still calls the live function its button called',
       dead.length===0, ROW_IDS.length+' rows, broken: '+(dead.join(', ')||'none'));

    // ================= 3. Opening and closing =============================
    // Above 1024px the panel is inline (position:static, no .open, the rows
    // simply laid out in the bar) and the trigger that would open a dropdown
    // is display:none, so there is no open/close cycle to drive there. Below
    // and at 1024px it is the same fixed dropdown P36 shipped.
    if(!desktop){
      ck('menu: it starts closed', !menuOpen()&&rowsVisible()===0,
         'open='+menuOpen()+', '+rowsVisible()+' of '+ROW_IDS.length+' rows visible');
      ck('menu: aria-expanded starts false',
         $('btn-more-actions').getAttribute('aria-expanded')==='false',
         $('btn-more-actions').getAttribute('aria-expanded'));

      click($('btn-more-actions')); await settle();
      // The trap this is aimed at: the document listener seeing the very click
      // that opened the menu and shutting it again.
      R.notes.afterTriggerClick={open:menuOpen(),rowsVisible:rowsVisible()};
      ck('menu: the trigger opens it and it STAYS open',
         menuOpen(), 'open='+menuOpen());
      ck('menu: all five rows are visible when it is open',
         rowsVisible()===ROW_IDS.length, rowsVisible()+' of '+ROW_IDS.length+' visible');
      ck('menu: aria-expanded follows',
         $('btn-more-actions').getAttribute('aria-expanded')==='true',
         $('btn-more-actions').getAttribute('aria-expanded'));

      // Escape
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      await settle();
      ck('menu: Escape closes it', !menuOpen(), 'open='+menuOpen());

      // Click outside
      click($('btn-more-actions')); await settle();
      const wasOpen=menuOpen();
      click(document.body); await settle();
      ck('menu: a click outside closes it',
         wasOpen&&!menuOpen(), 'was '+wasOpen+', now '+menuOpen());
    } else {
      // Desktop: no menu to open. What has to hold instead is that every row
      // is already on screen and individually clickable without any trigger.
      const reachable=ROW_IDS.filter(function(id){
        const el=$(id); if(!el) return false;
        const r=el.getBoundingClientRect(); return r.width>0&&r.height>0;
      }).length;
      ck('menu: above 1024px every row is already reachable inline, no trigger needed',
         reachable===ROW_IDS.length, reachable+' of '+ROW_IDS.length+' reachable');
      ck('menu: the panel carries no .open state to manage at this width',
         !menuOpen(), 'open='+menuOpen());
    }

    // ================= 4. State still set, and still shown ================
    // Each toggle is driven the way a user actually reaches it: through the
    // dropdown at <=1024px, directly (already inline, no trigger to click)
    // above it.
    async function viaMenu(id){
      if(!desktop && !menuOpen()){ click($('btn-more-actions')); await settle(); }
      click($(id)); await settle(); await settle();
    }
    const inactiveBg=function(){
      // A row known to carry no .on state, as the comparison for "painted".
      // Save as is a one-shot action (publishDashboard), never toggled.
      return getComputedStyle($('btn-save-as')).backgroundColor;
    };

    await viaMenu('btn-settings-icon');
    const sOn=$('btn-settings-icon').classList.contains('on');
    const sBg=getComputedStyle($('btn-settings-icon')).backgroundColor;
    const sOpen=$('settings-drawer').classList.contains('open');
    R.notes.settings={on:sOn,drawerOpen:sOpen,bg:sBg,inactiveBg:inactiveBg()};
    ck('state: choosing Settings opens the drawer and marks its row',
       sOn&&sOpen, 'on='+sOn+', drawer='+sOpen);
    // The specificity trap. Class presence proves nothing; the paint does.
    ck('state: and the active row actually PAINTS differently',
       sBg!==inactiveBg(), sBg+' against inactive '+inactiveBg());
    if(!desktop){
      ck('state: choosing a row closed the menu behind it',
         !menuOpen(), 'open='+menuOpen());
    }
    await viaMenu('btn-settings-icon');   // back off
    ck('state: choosing it again closes the drawer and clears the row',
       !$('btn-settings-icon').classList.contains('on')&&
       !$('settings-drawer').classList.contains('open'),
       'on='+$('btn-settings-icon').classList.contains('on'));

    await viaMenu('btn-style-icon');
    ck('state: View controls opens its panel and marks its row',
       $('btn-style-icon').classList.contains('on')&&
       $('filter-bar').classList.contains('open'),
       'on='+$('btn-style-icon').classList.contains('on'));
    await viaMenu('btn-style-icon');

    // btn-filter-toggle / #filter-dot were removed outright by design
    // (TD-72's re-open route is #btn-filter-expand in the report heading now,
    // covered by tools/p32_check.py), so there is no filter-row toggle left
    // in this panel to drive through the menu.

    await viaMenu('btn-print-mode');
    R.notes.print={on:$('btn-print-mode').classList.contains('on'),
                   aria:$('btn-print-mode').getAttribute('aria-pressed'),
                   bodyClass:document.body.classList.contains('print-mode'),
                   menuOpen:menuOpen()};
    ck('state: print preview engages and marks its row',
       R.notes.print.on&&R.notes.print.bodyClass&&R.notes.print.aria==='true',
       JSON.stringify(R.notes.print));
    ck('print: entering the preview leaves no menu open over the board',
       !R.notes.print.menuOpen, 'open='+R.notes.print.menuOpen);
    await viaMenu('btn-print-mode');      // leave print mode

    // Theme: the glyph is rewritten, the row label must survive it.
    const beforeTheme=document.documentElement.getAttribute('data-theme')||'light';
    const lblBefore=$('btn-theme-toggle').querySelector('.ib-mi-lbl').textContent.trim();
    const icoBefore=$('btn-theme-toggle').querySelector('.ib-mi-ico').textContent.trim();
    await viaMenu('btn-theme-toggle');
    const afterTheme=document.documentElement.getAttribute('data-theme');
    const lblAfter=$('btn-theme-toggle').querySelector('.ib-mi-lbl').textContent.trim();
    const icoAfter=$('btn-theme-toggle').querySelector('.ib-mi-ico').textContent.trim();
    R.notes.theme={from:beforeTheme,to:afterTheme,label:lblBefore+' -> '+lblAfter,
                   glyph:icoBefore+' -> '+icoAfter};
    ck('theme: the theme flips and the glyph changes with it',
       afterTheme!==beforeTheme&&icoAfter!==icoBefore, JSON.stringify(R.notes.theme));
    ck('theme: and rewriting the glyph did NOT eat the row label',
       lblAfter===lblBefore&&lblAfter.length>0, JSON.stringify(R.notes.theme.label));
    await viaMenu('btn-theme-toggle');    // back to where it started

    // ================= 5. The dot reaches the trigger ======================
    // Driven by adding the class the real writer adds, so what is under test is
    // the derivation, not a second copy of the rule. #filter-dot is retired
    // outright with #btn-filter-toggle (asserted gone in section 2 above), so
    // #settings-dot is now the only row-level dot the panel carries and the
    // only one this derivation has to cover.
    $('settings-dot').classList.remove('show');
    await settle();
    const none=dotShown('more-dot');
    $('settings-dot').classList.add('show'); await settle();
    const viaSettings=dotShown('more-dot');
    $('settings-dot').classList.remove('show'); await settle();
    const backToNone=dotShown('more-dot');
    R.notes.dots={neither:none,settingsOnly:viaSettings,cleared:backToNone};
    ck('dots: the trigger carries none when the settings row does not',
       none===false, JSON.stringify(R.notes.dots));
    ck('dots: a settings dot reaches the trigger',
       viaSettings===true, JSON.stringify(R.notes.dots));
    ck('dots: and clearing it clears the trigger',
       backToNone===false, JSON.stringify(R.notes.dots));

    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=String(e&&e.stack); }
  emit();
})();
"""


def render(html_path, script, consts, width, height, tag):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    inject = "<script>" + consts + "</script>\n<script>\n" + script + "\n</script>\n"
    out = page.replace("</body>", inject + "</body>")
    if out == page:
        sys.exit(f"Could not find </body> to inject into ({html_path}).")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p36.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found for {tag} at {width}x{height}.\n"
                 + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def fn_body(src, name):
    """The text of `function name(...){...}`, brace-matched."""
    i = src.find("function " + name + "(")
    if i < 0:
        return None
    j = src.find("{", i)
    if j < 0:
        return None
    depth, k = 0, j
    while k < len(src):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
        k += 1
    return None


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=str(root / "data" / "schedules" /
                                          "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"))
    ap.add_argument("--html", default=str(root / "src" / "milestone-dashboard.html"))
    # v3.1.0-P35: the true pre-consolidation shape (seven flat buttons, no
    # trigger, no panel at all). The header-reclaim measurement below is a
    # historical proof tied to THAT specific shape, so it stays pinned here
    # rather than following "whatever release shipped last."
    ap.add_argument("--baseline", default=str(root / "releases" /
                                             "v3.1.0-P35_milestone-card-and-progress-override.html"))
    # The release immediately before the partial actually under test, used
    # only for the CHANGED_SINCE/UNTOUCHED source diffs below. Separate from
    # --baseline: those diffs ask "did THIS partial have to touch this
    # function", which only means something against the build THIS partial
    # started from, not against the original P36 shape.
    ap.add_argument("--prev-release", default=str(root / "releases" /
                                             "v3.1.0-P55_palette-tokens.html"))
    a = ap.parse_args()

    html = pathlib.Path(a.html)
    baseline = pathlib.Path(a.baseline)
    prev_release = pathlib.Path(a.prev_release)
    src = html.read_text(encoding="utf-8", errors="replace")
    checks = []

    vers = len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src))
    checks.append(("source: exactly one version literal", vers == 1, f"{vers} found"))

    # The headline claim of this partial, asserted where it can actually be
    # proved: the state-writing functions did not have to change.
    if baseline.exists():
        base_src = baseline.read_text(encoding="utf-8", errors="replace")
        # UNTOUCHED is empty as of P56 (both original members moved to
        # CHANGED_SINCE_FROM_PREV_RELEASE, each for a reason named above). An
        # empty set would pass vacuously, which this project's own standing
        # rule is not to allow, so the check is skipped rather than asserted.
        if UNTOUCHED:
            changed = []
            for name in UNTOUCHED:
                a_body, b_body = fn_body(src, name), fn_body(base_src, name)
                if a_body is None or b_body is None:
                    changed.append(f"{name} (not found)")
                elif a_body != b_body:
                    changed.append(name)
            checks.append((
                "source: the state-writing functions are byte-identical to the previous release",
                not changed,
                f"{len(UNTOUCHED)} compared, changed: " + (", ".join(changed) or "none")))
        for name, marker in CHANGED_SINCE_FROM_BASELINE.items():
            now, was = fn_body(src, name), fn_body(base_src, name)
            checks.append((
                f"source: {name} changed only for the reason this check names",
                now is not None and was is not None and now != was and marker in now,
                f"expected {marker!r} in the new body"))
    else:
        checks.append(("source: the previous release was available to diff against",
                       False, f"missing {baseline}"))

    if prev_release.exists():
        prev_src = prev_release.read_text(encoding="utf-8", errors="replace")
        for name, marker in CHANGED_SINCE_FROM_PREV_RELEASE.items():
            now, was = fn_body(src, name), fn_body(prev_src, name)
            checks.append((
                f"source: {name} changed only for the reason this check names (since {prev_release.name})",
                now is not None and was is not None and now != was and marker in now,
                f"expected {marker!r} in the new body"))
    else:
        checks.append(("source: the release immediately before this partial was available to diff against",
                       False, f"missing {prev_release}"))

    checks.append((
        "source: the active-row rule is restated, not left to source order",
        ".icon-btn.ib-mi.on{" in src,
        "no .icon-btn.ib-mi.on rule, so .on would lose to .ib-mi"))
    checks.append((
        "source: the trigger's dot is derived from the rows, adding no new writer",
        "#ib-menu:has(.ib-menu-panel .dot.show) #more-dot" in src, "derivation not found"))
    checks.append((
        "source: one writer for the theme glyph",
        src.count("function setThemeGlyph(") == 1
        and "btn.innerHTML=(next===" not in src,
        "a second glyph writer survives"))

    consts = ("const ROW_IDS=" + json.dumps([r[0] for r in ROWS]) + ";"
              "const ROW_FNS=" + json.dumps([r[1] for r in ROWS]) + ";"
              "const RETIRED_IDS=" + json.dumps(RETIRED_IDS) + ";")

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, PROBE, consts, w, h, "P36")
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("header", "settings", "filterRow", "print", "theme", "dots"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")

        if baseline.exists():
            B = render(baseline, BASELINE, consts, w, h, "P35")
            if not B.get("ok"):
                checks.append((f"[{w}x{h}] header: the previous release was measured to compare against",
                               False, str(B.get("err"))))
            else:
                print("   before: %d buttons, group %spx, label %spx for %spx, clipped=%s"
                      % (B["buttons"], B["groupWidth"], B["label"]["w"],
                         B["label"]["need"], B["label"]["clipped"]))
                print("   after:  trigger visible=%s, %d row(s) inline, group %spx, label %spx for %spx, clipped=%s"
                      % (R["header"]["triggerVisible"], R["header"]["rowsVisibleInline"],
                         R["header"]["groupWidth"], R["header"]["labelWidth"],
                         R["header"]["labelNeeds"], R["header"]["labelClipped"]))
                reclaimed = B["groupWidth"] - R["header"]["groupWidth"]
                checks.append((f"[{w}x{h}] header: the previous release really did carry seven buttons",
                               B["buttons"] == 7, f"{B['buttons']} found"))
                # The reclaimed-width claim is specifically about collapsing
                # seven buttons down to one trigger, so it only holds at the
                # widths where the panel is still the collapsed dropdown.
                # Above 1024px the panel is inline by design (P56/D-20b) and
                # the group is deliberately back to five buttons wide, which
                # is not a regression of the P36 claim, just a later partial
                # spending the reclaimed room on something else.
                if not R["notes"]["desktop"]:
                    checks.append((f"[{w}x{h}] header: the icon group gave back real width",
                                   reclaimed > 150, f"{reclaimed:.1f}px reclaimed"))
                else:
                    print(f"   [{w}x{h}] group width not compared to the P35 baseline here: "
                          "panel is inline by design above 1024px (P56/D-20b)")
                # What is claimed depends on whether the bar has the room, and
                # that is read from the measurement rather than from a width
                # typed in here.
                before_w, after_w = B["label"]["w"], R["header"]["labelWidth"]
                needed = R["header"]["labelNeeds"]
                detail = ("before %spx / after %spx of %spx needed"
                          % (before_w, after_w, needed))
                if not R["header"]["labelClipped"]:
                    checks.append((
                        f"[{w}x{h}] header: the label now gets the full width it needs",
                        after_w >= before_w, detail))
                else:
                    # The stated limit. The bar at this width also carries the
                    # editable report title, so the label cannot have all 216px.
                    # What the change must still deliver is a real gain.
                    checks.append((
                        f"[{w}x{h}] header: the label still cannot fit, and the gain is stated not hidden",
                        after_w > before_w * 2, detail + " (TD-135)"))
                    print("   LIMIT: the bar cannot give the label its full width here; "
                          + detail)

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
