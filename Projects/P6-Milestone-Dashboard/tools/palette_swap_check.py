#!/usr/bin/env python3
"""
Palette-swap probe for the P6 Milestone Dashboard (P55 central-token rule).

Proves that a theme/brand change needs editing only tier 1 (--pal-*,
--shadow-color): every rendered colour on the page has to be REACHABLE from
the palette, i.e. it has to actually change when the palette changes.

Method (two-sentinel, per theme):
  1. Enumerate every --pal-* (and --shadow-color) custom property defined on
     the active theme's html[data-theme="..."] rule, by reading the parsed
     stylesheet (document.styleSheets) rather than getComputedStyle, which
     cannot enumerate custom properties at all.
  2. Run A: set every one of those properties on document.documentElement.style
     to a distinct saturated sentinel colour from set A (golden-angle hue
     spread, deterministic).
  3. Run B: same properties, a second distinct sentinel set B (offset 181deg
     from set A so no hue can coincide).
  4. After each run, force a style recalc and read the computed colour-bearing
     properties of every element (plus non-empty ::before/::after) in the
     document: color, background-color, background-image, the four border-
     side colours (only where that side's border-width > 0), outline-color
     (only where outline-style isn't none), box-shadow, text-shadow, fill and
     stroke (SVG shape elements only), and text-decoration-color (only where
     a decoration line is set).
  5. An element/property whose value is IDENTICAL between run A and run B,
     and is not transparent/none/rgba(0,0,0,0), never moved with the palette:
     it ESCAPED tier 1. Reported as theme + selector path + property + value.

Both themes are probed (data-theme flipped the same way tools/theme_check.py
does). The milestone dialog and the settings drawer are opened first (via the
app's own openMsDialog/toggleSettingsDrawer/setSettingsTab, not by faking DOM)
so their content is in the document, and therefore measured, for the whole
run. See --coverage-notes for what this does and does not reach.

Usage:
  python3 tools/palette_swap_check.py [path-to-html] [--json out.json]
Exit code 1 if any escape is found in either theme.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
]

PROBE_JS = r"""
(function(){
function palettePropsForTheme(theme){
  const names = new Set();
  for (const sheet of document.styleSheets){
    let rules;
    try { rules = sheet.cssRules; } catch(e){ continue; }
    if(!rules) continue;
    (function walk(list){
      for (const rule of list){
        // Some engines expose an (empty) cssRules on a plain CSSStyleRule too,
        // so gate recursion on it actually holding rules, not merely existing.
        if (rule.cssRules && rule.cssRules.length){ walk(rule.cssRules); continue; }
        if (!rule.selectorText) continue;
        const sel = rule.selectorText.trim();
        const m = sel.match(/^html\s*\[\s*data-theme\s*=\s*["']?(\w+)["']?\s*\]$/);
        if (!m || m[1] !== theme) continue;
        const style = rule.style;
        for (let i=0;i<style.length;i++){
          const name = style.item(i);
          if (name.indexOf('--pal-') === 0 || name === '--shadow-color') names.add(name);
        }
      }
    })(rules);
  }
  return Array.from(names);
}

function sentinel(i, setName){
  const offset = setName === 'A' ? 0 : 181; // never lets A and B coincide
  const hue = (i * 137.508 + offset) % 360;
  return 'hsl(' + hue.toFixed(2) + 'deg 85% 45%)';
}

const PROPS = ['color','background-color','background-image',
  'border-top-color','border-right-color','border-bottom-color','border-left-color',
  'outline-color','box-shadow','text-shadow','fill','stroke','text-decoration-color'];

function elPath(el){
  if (!el || el.nodeType !== 1) return '';
  const parts = [];
  let n = el;
  while (n && n.nodeType === 1 && parts.length < 6){
    let part = n.tagName.toLowerCase();
    if (n.id){ parts.unshift(part + '#' + n.id); break; }
    if (n.className && typeof n.className === 'string' && n.className.trim()){
      part += '.' + n.className.trim().split(/\s+/).slice(0,2).join('.');
    }
    const parent = n.parentElement;
    if (parent){
      const same = Array.from(parent.children).filter(c => c.tagName === n.tagName);
      if (same.length > 1) part += ':nth-of-type(' + (same.indexOf(n)+1) + ')';
    }
    parts.unshift(part);
    n = parent;
  }
  return parts.join('>');
}

function isSvgShape(el){
  return el.namespaceURI === 'http://www.w3.org/2000/svg' &&
    ['path','rect','circle','ellipse','line','polygon','polyline','text'].indexOf(el.tagName.toLowerCase()) >= 0;
}

function recordFor(el, cs){
  const rec = {};
  for (const p of PROPS) rec[p] = cs.getPropertyValue(p).trim();
  if (!isSvgShape(el)){ delete rec.fill; delete rec.stroke; }
  rec._borderW = {
    top: parseFloat(cs.borderTopWidth)||0, right: parseFloat(cs.borderRightWidth)||0,
    bottom: parseFloat(cs.borderBottomWidth)||0, left: parseFloat(cs.borderLeftWidth)||0
  };
  rec._outlineStyle = cs.outlineStyle;
  rec._textDecorationLine = cs.textDecorationLine;
  rec._hasText = Array.from(el.childNodes || [])
    .filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim().length > 0;
  return rec;
}

function snapshotElements(){
  const out = [];
  // document.body only: <head> (title, the style element itself) is never
  // painted, so it is not a palette question. <symbol> contents are inert
  // icon TEMPLATES referenced later via <use>; the colour that actually
  // renders is on the <use> (or its wrapper), not the template, so scanning
  // the template reports a "fill never changes" false positive for every icon.
  const all = document.body.querySelectorAll('*');
  for (const el of all){
    if (el.closest('symbol')) continue;
    out.push({path: elPath(el), rec: recordFor(el, getComputedStyle(el))});
    for (const pseudo of ['::before','::after']){
      let pcs;
      try { pcs = getComputedStyle(el, pseudo); } catch(e){ continue; }
      const content = pcs.getPropertyValue('content');
      if (!content || content === 'none' || content === '""' || content === "''") continue;
      out.push({path: elPath(el)+pseudo, rec: recordFor(el, pcs)});
    }
  }
  return out;
}

function applySentinels(names, setName){
  names.forEach((name,i) => document.documentElement.style.setProperty(name, sentinel(i,setName)));
}
function clearSentinels(names){
  names.forEach(name => document.documentElement.style.removeProperty(name));
}

function openExtraSurfaces(coverage){
  try {
    const wrap = document.querySelector('#tbody .m-wrap:not(.m-ghost)');
    if (wrap){
      wrap.click();
      const dlg = document.getElementById('ms-dialog');
      coverage.msDialogOpened = !!(dlg && !dlg.hidden);
    } else coverage.msDialogOpened = false;
  } catch(e){ coverage.msDialogError = String(e); }
  try {
    if (typeof toggleSettingsDrawer === 'function'){
      toggleSettingsDrawer(true);
      const dr = document.getElementById('settings-drawer');
      coverage.settingsDrawerOpened = !!(dr && dr.classList.contains('open'));
      if (typeof SETTINGS_TABS !== 'undefined' && typeof setSettingsTab === 'function'){
        coverage.settingsTabsSeen = SETTINGS_TABS.slice();
        // Visiting every tab at least once mounts anything built lazily; the
        // measurement pass itself reads whichever tab is left active PLUS
        // every other tab's markup, since [hidden] panels still resolve
        // computed colour values in Chromium even though they have no layout.
        SETTINGS_TABS.forEach(t => setSettingsTab(t));
        setSettingsTab('sources');
      }
    } else coverage.settingsDrawerOpened = false;
  } catch(e){ coverage.settingsDrawerError = String(e); }
}

function run(){
  const result = { light: null, dark: null };
  for (const theme of ['light','dark']){
    document.documentElement.setAttribute('data-theme', theme);
    document.body.offsetHeight;
    const names = palettePropsForTheme(theme);
    const coverage = { paletteCount: names.length };
    openExtraSurfaces(coverage);
    document.body.offsetHeight;

    applySentinels(names, 'A');
    document.body.offsetHeight;
    const snapA = snapshotElements();
    clearSentinels(names);

    applySentinels(names, 'B');
    document.body.offsetHeight;
    const snapB = snapshotElements();
    clearSentinels(names);

    result[theme] = { names: names, snapA: snapA, snapB: snapB, coverage: coverage };
  }
  const pre = document.createElement('pre');
  pre.id = 'palette-swap-out';
  pre.textContent = JSON.stringify(result);
  document.body.appendChild(pre);
}
run();
})();
"""


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    sys.exit("No headless Chromium found. Checked: " + ", ".join(CHROME_CANDIDATES))


def run(html_path: pathlib.Path) -> dict:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    # Transitions would let a colour still be mid-animation from run A when run B
    # is read, so both runs would report the same in-between value and it would
    # look like an escape. Freeze them for the probe only.
    freeze = "<style>*,*::before,*::after{transition:none!important;animation:none!important}</style>"
    injected = html.replace("</body>", f"{freeze}\n<script>\n{PROBE_JS}\n</script>\n</body>")
    if injected == html:
        sys.exit("Could not find </body> to inject the probe script.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "probe.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             "--virtual-time-budget=8000", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=120,
        )
    m = re.search(r'<pre id="palette-swap-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        sys.exit("Probe output not found. The page likely threw before the probe ran.\n"
                 + proc.stderr[-2000:])
    raw = (m.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
           .replace("&quot;", '"'))
    return json.loads(raw)


NON_LITERAL_VALUES = {"", "none", "rgba(0, 0, 0, 0)", "transparent", "normal"}


def _applicable(prop: str, rec: dict) -> bool:
    if prop in ("color",):
        return rec.get("_hasText", False)
    if prop == "background-color":
        return True
    if prop == "background-image":
        return rec.get(prop, "none") != "none"
    if prop.startswith("border-") and prop.endswith("-color"):
        side = prop.split("-")[1]
        return rec.get("_borderW", {}).get(side, 0) > 0
    if prop == "outline-color":
        return rec.get("_outlineStyle", "none") != "none"
    if prop == "box-shadow":
        return rec.get(prop, "none") != "none"
    if prop == "text-shadow":
        return rec.get(prop, "none") != "none" and rec.get("_hasText", False)
    if prop in ("fill", "stroke"):
        return prop in rec and rec.get(prop) not in ("", "none")
    if prop == "text-decoration-color":
        return rec.get("_textDecorationLine", "none") != "none"
    return True


PROPS = ["color", "background-color", "background-image",
         "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
         "outline-color", "box-shadow", "text-shadow", "fill", "stroke",
         "text-decoration-color"]


def find_escapes(theme_data: dict, theme: str) -> list:
    escapes = []
    snap_a = theme_data["snapA"]
    snap_b = theme_data["snapB"]
    if len(snap_a) != len(snap_b):
        # DOM shape changed between the two runs (should not happen, since only
        # custom properties changed). Compare by path instead of by index.
        b_by_path = {e["path"]: e for e in snap_b}
        pairs = [(e, b_by_path.get(e["path"])) for e in snap_a]
    else:
        pairs = list(zip(snap_a, snap_b))
    for a, b in pairs:
        if a is None or b is None:
            continue
        ra, rb = a["rec"], b["rec"]
        for prop in PROPS:
            va, vb = ra.get(prop), rb.get(prop)
            if va is None or vb is None:
                continue
            if va != vb:
                continue  # moved with the palette: fine
            if va.strip().lower() in NON_LITERAL_VALUES:
                continue
            if not _applicable(prop, ra):
                continue
            escapes.append({"theme": theme, "path": a["path"], "property": prop, "value": va})
    return escapes


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("html", nargs="?", default=root / "src" / "milestone-dashboard.html")
    ap.add_argument("--json", default=None)
    ap.add_argument("--exceptions", default=root / "tools" / "colour_exceptions.json",
                     help="Same exceptions file as colour_audit.py --strict. An escape whose "
                          "path substring-matches line_contains and whose value matches "
                          "literal is excluded.")
    ap.add_argument("--coverage-notes", action="store_true",
                     help="Print what DOM states this probe does and does not exercise, then exit.")
    args = ap.parse_args()

    if args.coverage_notes:
        print(__doc__)
        return 0

    data = run(pathlib.Path(args.html))

    exceptions = []
    exc_path = pathlib.Path(args.exceptions)
    if exc_path.exists():
        exceptions = json.loads(exc_path.read_text(encoding="utf-8"))

    all_escapes = []
    for theme in ("light", "dark"):
        if not data.get(theme):
            print(f"[{theme}] probe produced no data (page likely threw before the theme ran).")
            continue
        cov = data[theme]["coverage"]
        print(f"[{theme}] {cov.get('paletteCount', 0)} palette token(s) found; "
              f"milestone dialog opened: {cov.get('msDialogOpened')}; "
              f"settings drawer opened: {cov.get('settingsDrawerOpened')}")
        all_escapes.extend(find_escapes(data[theme], theme))

    kept = []
    for e in all_escapes:
        matched = any(
            exc.get("line_contains", "") in e["path"]
            and str(exc.get("literal", "")).lower() == e["value"].lower()
            for exc in exceptions
        )
        if not matched:
            kept.append(e)

    print()
    print(f"Escapes: {len(kept)} (excepted: {len(all_escapes) - len(kept)})")
    print()
    for e in kept[:15]:
        print(f"  [{e['theme']}] {e['path']}  {e['property']}={e['value']}")
    if len(kept) > 15:
        print(f"  ... and {len(kept) - 15} more")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nFull snapshot written to {args.json}")

    return 1 if kept else 0


if __name__ == "__main__":
    sys.exit(main())
