#!/usr/bin/env python3
"""
Theme toggle check for the P6 Milestone Dashboard.

Renders the dashboard headlessly, flips data-theme between light and dark, and
reports the computed colour of every probe element in both states.

Why this exists: a colour hardcoded to one theme's value looks perfectly
correct in that theme and wrong in the other. Reading the CSS does not reveal
it reliably, and this project's history is full of code that read correctly
and behaved wrongly at runtime. This measures the rendered result instead.

A probe is FROZEN if every colour property it declares is byte-identical in
both themes. That is a defect for a structural role (text, background, border)
and expected for a deliberately constant one, so probes carry an `expect`
field: "toggle" or "constant".

Usage:
  python3 tools/theme_check.py [path-to-html] [--json out.json]
Exit code 1 if any probe expecting "toggle" came back frozen.
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

# Each probe: (id, expectation, how to obtain the element).
# `build` is JS returning an element. Elements that exist in the rendered page
# are queried; those that only appear on interaction are constructed with the
# ancestor context their selectors actually require, because a bare div with
# the class would not match `tr.hist-row td.c-wk.now-col` and would silently
# report a false pass.
# Wrapped in an IIFE. The app declares its own globals (tbody among them) and
# an element with id="tbody" also creates one, so top-level const here collides
# with "Identifier 'tbody' has already been declared" and the probe never runs.
PROBES = r"""
(function(){
const mk = (html, mount) => {
  const host = mount || document.body;
  const tpl = document.createElement('template');
  tpl.innerHTML = html.trim();
  const el = tpl.content.firstElementChild;
  host.appendChild(el);
  return el;
};
const table = mk('<table style="position:absolute;left:-9999px"><tbody></tbody></table>');
const tbody = table.querySelector('tbody');

const PROBES = [
  ['.sticky-search-icon',        'toggle',   () => document.querySelector('.sticky-search-icon')],
  ['.sticky-search-clear',       'toggle',   () => document.querySelector('.sticky-search-clear')],
  ['.view-toggle',               'toggle',   () => document.querySelector('.view-toggle')],
  ['th.c-name (column header)',  'toggle',   () => document.querySelector('th.c-name:not(.sticky)')
                                              || document.querySelectorAll('th.c-name')[1]],
  // Status classes set an SVG fill and are never applied to text anywhere in
  // the app, confirmed by querying the rendered board. They carry no content
  // here so the contrast pass does not measure a text case that cannot occur;
  // the colour still resolves, so the toggle assertion is unaffected.
  ['.s-track',                   'toggle',   () => mk('<span class="s-track"></span>')],
  ['.s-future',                  'toggle',   () => mk('<span class="s-future"></span>')],
  ['hist now-col',               'toggle',   () => {
      const tr = mk('<tr class="hist-row"><td class="c-wk now-col"></td></tr>', tbody);
      return tr.querySelector('td');
  }],
  ['.dep-tooltip',               'toggle',   () => mk('<div class="dep-tooltip">x</div>')],
  ['.dep-comment-panel',         'toggle',   () => mk('<div class="dep-comment-panel">x</div>')],
  ['.dep-comment-close',         'toggle',   () => mk('<button class="dep-comment-close">x</button>')],
  ['.dep-comment-ids',           'toggle',   () => mk('<span class="dep-comment-ids">x</span>')],
  ['dep-panel textarea',         'toggle',   () => {
      const p = mk('<div class="dep-comment-panel"><textarea></textarea></div>');
      return p.querySelector('textarea');
  }],
  ['dep-actions button',         'toggle',   () => {
      const p = mk('<div class="dep-comment-actions"><button>x</button></div>');
      return p.querySelector('button');
  }],
  ['subtotal past-col',          'toggle',   () => {
      const tr = mk('<tr class="subtotal-row"><td class="c-wk past-col"></td></tr>', tbody);
      return tr.querySelector('td');
  }],

  // --- Board: rows, columns, marker labels, icons, status ---
  // Marker label backings were plain white before v3.1.0-P3, so a white pill
  // sat on the dark board in dark theme.
  ['.m-lbl',                     'toggle',   () => mk('<div class="m-lbl">x</div>')],
  ['.m-short-title',             'toggle',   () => mk('<div class="m-short-title">x</div>')],
  ['.m-hrs',                     'toggle',   () => mk('<div class="m-hrs">x</div>')],
  ['alt row .m-lbl',             'toggle',   () => {
      const tr = mk('<tr class="data alt"><td><div class="m-lbl">x</div></td></tr>', tbody);
      return tr.querySelector('.m-lbl');
  }],
  ['td.c-wk.past-col',           'toggle',   () => {
      const tr = mk('<tr class="data"><td class="c-wk past-col"></td></tr>', tbody);
      return tr.querySelector('td');
  }],
  ['td.c-wk.filter-col',         'toggle',   () => {
      const tr = mk('<tr class="data"><td class="c-wk filter-col"></td></tr>', tbody);
      return tr.querySelector('td');
  }],
  ['subtotal .c-hrs',            'toggle',   () => {
      const tr = mk('<tr class="subtotal-row"><td class="c-hrs">1</td></tr>', tbody);
      return tr.querySelector('td');
  }],
  ['.remarks:empty placeholder', 'toggle',   () => mk('<div class="remarks"></div>')],

  // Milestone drag states. The drop-target wash is a translucent :root
  // constant, so it is only themed by virtue of the row background beneath it.
  // Probing the composite is the only way to prove that actually holds.
  ['tr.data.ms-drop-target td',  'toggle',   () => {
      const tr = mk('<tr class="data ms-drop-target"><td class="c-wk"></td></tr>', tbody);
      return tr.querySelector('td');
  }],
  // Mount panel and the selective-import dialog. Small text on a card and on
  // tinted message strips: exactly the shape that slipped past the contrast
  // check before it resolved transparent elements to a painting ancestor.
  ['.mnt-slot',                  'toggle',   () => mk('<div class="mnt-slot">x</div>')],
  ['.mnt-name',                  'toggle',   () => {
      const d = mk('<div class="mnt-slot"><div class="mnt-hd"><span class="mnt-name">Schedule</span></div></div>');
      return d.querySelector('.mnt-name');
  }],
  ['.mnt-lines',                 'toggle',   () => {
      const d = mk('<div class="mnt-slot"><div class="mnt-lines">Data date</div></div>');
      return d.querySelector('.mnt-lines');
  }],
  // Saturated chip: the fill carries the meaning and the text is chosen
  // against the fill, not the page, so frozen is correct.
  ['.mnt-badge (constant)',      'constant', () => {
      const d = mk('<div class="mnt-slot"><span class="mnt-badge">override</span></div>');
      return d.querySelector('.mnt-badge');
  }],
  ['.imp-fail',                  'toggle',   () => mk('<div class="imp-fail">x</div>')],
  ['.imp-fail-hd',               'toggle',   () => {
      const d = mk('<div class="imp-fail"><div class="imp-fail-hd">Could not read</div></div>');
      return d.querySelector('.imp-fail-hd');
  }],
  ['.imp-fail-hints li',         'toggle',   () => {
      const d = mk('<div class="imp-fail"><div class="imp-fail-msg"><ul class="imp-fail-hints"><li>close it in Excel</li></ul></div></div>');
      return d.querySelector('.imp-fail-hints li');
  }],
  ['.imp-fail-msg',              'toggle',   () => {
      const d = mk('<div class="imp-fail"><div class="imp-fail-msg">why it failed</div></div>');
      return d.querySelector('.imp-fail-msg');
  }],
  ['.annot-panel',               'toggle',   () => mk('<div class="annot-panel">x</div>')],
  ['.annot-err',                 'toggle',   () => mk('<div class="annot-msg annot-err">error</div>')],
  // Amber attention strip, same category: :root tokens, ink picked for the fill.
  ['.annot-warn (constant)',     'constant', () => mk('<div class="annot-msg annot-warn">warning</div>')],
  ['.annot-count',               'toggle',   () => {
      const d = mk('<div class="annot-panel"><label class="annot-row"><span class="annot-count">12</span></label></div>');
      return d.querySelector('.annot-count');
  }],

  ['.row-num',                   'toggle',   () => {
      const tr = mk('<tr class="data"><td class="c-name"><span class="row-num">1</span></td></tr>', tbody);
      return tr.querySelector('.row-num');
  }],

  // Icon default states. Each paints from its own --color-icon-* token.
  ['icon s-done',                'toggle',   () => mk('<svg class="ms-icon filled s-done"></svg>')],
  ['icon s-track',               'toggle',   () => mk('<svg class="ms-icon filled s-track"></svg>')],
  ['icon s-risk',                'toggle',   () => mk('<svg class="ms-icon filled s-risk"></svg>')],
  ['icon s-crit',                'toggle',   () => mk('<svg class="ms-icon filled s-crit"></svg>')],
  ['icon s-future',              'toggle',   () => mk('<svg class="ms-icon filled s-future"></svg>')],
  ['icon s-baseline',            'toggle',   () => mk('<svg class="ms-icon baseline s-baseline"></svg>')],

  // Controls. These already read from tokens, so they prove the harness can
  // see a real difference rather than reporting everything as frozen.
  ['#icon-bar (control)',        'toggle',   () => document.getElementById('icon-bar')],
  ['body (control)',             'toggle',   () => document.body],

  // Deliberately constant: a saturated fill carries the meaning and the text
  // or rim on it is chosen for contrast against the fill, not the page, so a
  // frozen result here is correct.
  ['.vt-btn.active (constant)',  'constant', () => mk('<button class="vt-btn active">x</button>')],
  ['phase band pb1 (constant)',  'constant', () => {
      const tr = mk('<tr class="phase-band pb1"><td>x</td></tr>', tbody);
      return tr.querySelector('td');
  }],
  ['health h-1 (constant)',      'constant', () => mk('<span class="health-dot h-1"></span>')],
  ['health h-2 (constant)',      'constant', () => mk('<span class="health-dot h-2"></span>')],
  ['health mh-1 (constant)',     'constant', () => mk('<span class="health-dot mh-1"></span>')],
];

const PROPS = ['color', 'background-color', 'border-top-color', 'border-right-color',
               'border-bottom-color', 'border-left-color', 'outline-color'];

function snapshot(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.body.offsetHeight; // force style recalc
  const out = {};
  for (const [name, , get] of PROBES) {
    let el = null;
    try { el = get(); } catch (e) { el = null; }
    if (!el) { out[name] = null; continue; }
    const cs = getComputedStyle(el);
    const rec = {};
    for (const p of PROPS) rec[p] = cs.getPropertyValue(p).trim();
    // Contrast only means something where there is text to read. An empty
    // status dot inherits a colour it never paints.
    rec._hasText = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3)
      .map(n => n.textContent).join('').trim().length > 0;
    // Text on a transparent element is still read against something. Walk up
    // to the nearest ancestor that actually paints, so a colour chosen for one
    // surface and dropped onto another is measured rather than skipped.
    // Missing this is how a row number ended up at 2:1 in dark mode.
    rec._effectiveBg = (function(){
      let n = el;
      while (n && n !== document.documentElement) {
        const b = getComputedStyle(n).backgroundColor;
        if (b && b !== 'rgba(0, 0, 0, 0)' && b !== 'transparent') return b;
        n = n.parentElement;
      }
      return getComputedStyle(document.body).backgroundColor;
    })();
    out[name] = rec;
  }
  return out;
}

const result = { expectations: {}, light: null, dark: null };
for (const [name, expect] of PROBES.map(p => [p[0], p[1]])) result.expectations[name] = expect;
result.light = snapshot('light');
result.dark = snapshot('dark');

const pre = document.createElement('pre');
pre.id = 'theme-probe-out';
pre.textContent = JSON.stringify(result);
document.body.appendChild(pre);
})();
"""


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    sys.exit("No headless Chromium found. Checked: " + ", ".join(CHROME_CANDIDATES))


def run(html_path: pathlib.Path) -> dict:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    injected = html.replace("</body>", f"<script>\n{PROBES}\n</script>\n</body>")
    if injected == html:
        sys.exit("Could not find </body> to inject the probe script.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "probe.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             "--virtual-time-budget=6000", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=120,
        )
    m = re.search(r'<pre id="theme-probe-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        sys.exit("Probe output not found. The page likely threw before the probe ran.\n"
                 + proc.stderr[-2000:])
    raw = (m.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
           .replace("&quot;", '"'))
    return json.loads(raw)


def _parse_rgb(v: str):
    m = re.match(r"rgba?\(([^)]+)\)", v or "")
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).replace("/", ",").split(",")]
    try:
        r, g, b = (float(parts[i]) for i in range(3))
        a = float(parts[3]) if len(parts) > 3 else 1.0
    except (ValueError, IndexError):
        return None
    return r, g, b, a


def _luminance(r, g, b):
    def ch(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(fg: str, bg: str, page_bg: str):
    """WCAG contrast ratio of fg over bg, compositing bg's alpha over page_bg.

    A "does it toggle" check cannot see a text colour that changed in step with
    its background and stayed unreadable, so contrast is measured separately.
    """
    f, b, p = _parse_rgb(fg), _parse_rgb(bg), _parse_rgb(page_bg)
    if not f or not b or not p:
        return None
    if b[3] < 1.0:  # composite the translucent surface over the page
        b = tuple(b[i] * b[3] + p[i] * (1 - b[3]) for i in range(3)) + (1.0,)
    if f[3] < 1.0:
        f = tuple(f[i] * f[3] + b[i] * (1 - f[3]) for i in range(3)) + (1.0,)
    l1, l2 = _luminance(*f[:3]), _luminance(*b[:3])
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


MIN_CONTRAST = 3.0  # small UI text on the board; 4.5 is the AA body-text bar


def contrast_report(data):
    """Flag probes whose text is hard to read against its own background."""
    findings = []
    for theme in ("light", "dark"):
        snap = data[theme]
        page = (snap.get("body (control)") or {}).get("background-color", "rgb(255,255,255)")
        for name, rec in snap.items():
            if not rec:
                continue
            if not rec.get("_hasText"):
                continue  # nothing to read; an empty dot inherits an unused colour
            bg = rec.get("background-color", "")
            if not bg or bg == "rgba(0, 0, 0, 0)":
                # Transparent: read against whatever ancestor actually paints.
                bg = rec.get("_effectiveBg", "")
            if not bg or bg == "rgba(0, 0, 0, 0)":
                continue
            c = contrast(rec.get("color", ""), bg, page)
            if c is not None and c < MIN_CONTRAST:
                findings.append((theme, name, rec.get("color"), bg, c))
    return findings


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("html", nargs="?", default=root / "src" / "milestone-dashboard.html")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    data = run(pathlib.Path(args.html))
    light, dark, expect = data["light"], data["dark"], data["expectations"]

    frozen_defects, ok, constant_ok, missing = [], [], [], []
    for name in expect:
        l, d = light.get(name), dark.get(name)
        if l is None or d is None:
            missing.append(name)
            continue
        differing = [p for p in l if p not in ("_hasText","_effectiveBg") and l[p] != d[p]]
        if differing:
            # Something changed with the theme. That is what we want for a
            # "toggle" probe, and merely informational for a "constant" one.
            ok.append((name, differing, l, d))
        elif expect[name] == "toggle":
            frozen_defects.append((name, [], l, d))
        else:
            constant_ok.append((name, [], l, d))

    print(f"Probes: {len(expect)}   toggling: {len(ok)}   "
          f"frozen: {len(frozen_defects)}   constant-as-expected: {len(constant_ok)}"
          + (f"   not found: {len(missing)}" if missing else ""))
    print()
    if frozen_defects:
        print("FROZEN (identical in both themes, expected to toggle):")
        for name, _, l, _ in frozen_defects:
            shown = {p: v for p, v in l.items()
                     if p not in ("_hasText","_effectiveBg") and v and v != "rgba(0, 0, 0, 0)"}
            print(f"  {name:<28} {shown}")
        print()
    if ok:
        print("TOGGLING correctly:")
        for name, diff, l, d in ok:
            for p in diff:
                print(f"  {name:<28} {p:<21} light={l[p]:<22} dark={d[p]}")
    if constant_ok:
        print()
        print("CONSTANT by design (frozen is correct here):")
        for name, _, l, _ in constant_ok:
            print(f"  {name}")
    if missing:
        print()
        print("NOT FOUND (probe could not resolve an element):")
        for name in missing:
            print(f"  {name}")

    low = contrast_report(data)
    if low:
        print()
        print(f"LOW CONTRAST (text over its own background, below {MIN_CONTRAST}:1):")
        for theme, name, fg, bg, ratio in low:
            print(f"  [{theme}] {name:<26} {ratio:4.2f}:1   {fg} on {bg}")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nFull snapshot written to {args.json}")

    return 1 if (frozen_defects or low) else 0


if __name__ == "__main__":
    sys.exit(main())
