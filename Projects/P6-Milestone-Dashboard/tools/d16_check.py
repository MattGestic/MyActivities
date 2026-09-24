#!/usr/bin/env python3
"""
D-16 component-sheet visual regression gate.

docs/mockups/D-16/component_sheet.html is the sign-off reference: "every
control drawn to one standard." Its two committed screenshots
(docs/mockups/D-16/png/sheet-1440.png, sheet-420.png) existed with nothing
that ever re-rendered and diffed them -- a control-sizing regression (a
token value change breaking a control's dimensions) could land silently.
This is that gate.

What it does NOT do: this is not tools/ds_check.py, the computed-style
assertion tool design-standard.md's "How this is verified" section
describes (per-class height/padding/radius/contrast, across viewports,
pointer type and theme, against the LIVE app). That tool checks the app;
this one checks that the SHEET itself has not visibly changed, which is a
narrower, cheaper, pixel-level guard meant to run before merging any change
that touches control CSS. Both are useful; only this one exists so far.

Method: render component_sheet.html at the same window sizes the committed
PNGs were captured at (measured from those PNGs' own headers, not assumed),
screenshot with headless Chromium the same way tools/d01_render.py does,
then diff the fresh render against the committed PNG pixel-by-pixel. The
diff itself also runs in headless Chromium (two <canvas> elements +
getImageData), the same "inject JS, --dump-dom, parse a <pre>" pattern
tools/theme_check.py uses, so this needs no new dependency (no Pillow, no
npm package) beyond what every other tool/ script here already uses.

A pixel counts as changed if any RGB channel differs by more than
CHANNEL_TOLERANCE (anti-aliasing/font-hinting jitter, not a real change).
Fails if the changed-pixel fraction exceeds DIFF_TOLERANCE, or if the
rendered size no longer matches the committed PNG's own size (a dimension
change is itself the regression, not something to average away).

Usage:
  python3 tools/d16_check.py              # check against the committed PNGs
  python3 tools/d16_check.py --update     # re-render and REPLACE the
                                           # committed PNGs (after a reviewed,
                                           # intentional visual change)
Exit codes: 0 = sheet matches (or --update wrote new baselines).
            1 = a rendered sheet differs from its committed PNG.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHEET_HTML = ROOT / "docs" / "mockups" / "D-16" / "component_sheet.html"
PNG_DIR = ROOT / "docs" / "mockups" / "D-16" / "png"

CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
]

CHANNEL_TOLERANCE = 8      # per-channel 0-255 delta below which a pixel counts as unchanged
DIFF_TOLERANCE = 0.001     # fraction of pixels allowed to exceed that and still pass (0.1%)


def find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    sys.exit("No headless Chromium found. Checked: " + ", ".join(CHROME_CANDIDATES))


def measure_full_height(chrome: str, width: int) -> int:
    """documentElement.scrollHeight at this width, so the capture height is
    derived from the page's real content instead of a guessed constant.

    The sheet HTML has no </body></html> in its source (the DOM tree still
    closes them implicitly; Chromium's own --dump-dom output shows them, but
    they are not literal text in the file), so a probe cannot be spliced in
    with a "</body>" string replace -- that silently no-ops. Appending the
    probe <script> after all existing content works either way: a trailing
    script tag still runs after everything above it has parsed.

    A window height that does not reach the true content height is exactly
    the bug this replaced: the two PNGs this script first found committed
    (1440x3000, 420x3400) were both shorter than their pages' real
    scrollHeight (3627 and ~6800-6974 depending on scrollbar presence), so
    they were partial, scrolled captures, not full-page ones, and a
    scrollbar's reserved width in one render and not another was the actual
    source of an early false "24%/54% of pixels differ" reading against
    them -- not a real difference in the sheet's content. Sizing the window
    to the measured height means no scrollbar is ever needed, which removes
    that source of drift entirely.
    """
    probe = ("<script>(function(){const p=document.createElement('pre');"
              "p.id='height-probe';p.textContent=String(document.documentElement.scrollHeight);"
              "document.body.appendChild(p);})();</script>")
    injected = SHEET_HTML.read_text(encoding="utf-8") + probe
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "probe.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [chrome, "--headless", "--no-sandbox", "--disable-gpu",
             f"--window-size={width},1200", "--virtual-time-budget=4000", "--dump-dom",
             tmp.as_uri()],
            capture_output=True, text=True, timeout=60,
        )
    m = re.search(r'<pre id="height-probe">(\d+)</pre>', proc.stdout)
    if not m:
        sys.exit(f"Could not measure scrollHeight at width {width}.\n" + proc.stderr[-2000:])
    # +4px slack against sub-pixel rounding forcing an unwanted 1px scrollbar.
    return int(m.group(1)) + 4


def screenshot(chrome: str, width: int, height: int, out_path: pathlib.Path) -> None:
    cmd = [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
           f"--window-size={width},{height}", f"--screenshot={out_path}",
           SHEET_HTML.as_uri()]
    subprocess.run(cmd, check=True, capture_output=True, timeout=60)


DIFF_JS_TEMPLATE = r"""
(function(){
function load(src){
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('failed to load ' + src));
    img.src = src;
  });
}
Promise.all([load(%(a)s), load(%(b)s)]).then(([a, b]) => {
  const out = {aw: a.naturalWidth, ah: a.naturalHeight, bw: b.naturalWidth, bh: b.naturalHeight};
  if (out.aw !== out.bw || out.ah !== out.bh) {
    out.sizeMismatch = true;
  } else {
    const cv = document.createElement('canvas');
    cv.width = a.naturalWidth; cv.height = a.naturalHeight;
    const ctx = cv.getContext('2d');
    ctx.drawImage(a, 0, 0);
    const da = ctx.getImageData(0, 0, cv.width, cv.height).data;
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.drawImage(b, 0, 0);
    const db = ctx.getImageData(0, 0, cv.width, cv.height).data;
    let changed = 0;
    const tol = %(tol)d;
    for (let i = 0; i < da.length; i += 4) {
      if (Math.abs(da[i] - db[i]) > tol || Math.abs(da[i+1] - db[i+1]) > tol ||
          Math.abs(da[i+2] - db[i+2]) > tol) {
        changed++;
      }
    }
    out.sizeMismatch = false;
    out.totalPixels = cv.width * cv.height;
    out.changedPixels = changed;
  }
  const pre = document.createElement('pre');
  pre.id = 'diff-out';
  pre.textContent = JSON.stringify(out);
  document.body.appendChild(pre);
}).catch(err => {
  const pre = document.createElement('pre');
  pre.id = 'diff-out';
  pre.textContent = JSON.stringify({error: String(err)});
  document.body.appendChild(pre);
});
})();
"""


def diff_pngs(chrome: str, path_a: pathlib.Path, path_b: pathlib.Path) -> dict:
    js = DIFF_JS_TEMPLATE % {
        "a": json.dumps(path_a.as_uri()),
        "b": json.dumps(path_b.as_uri()),
        "tol": CHANNEL_TOLERANCE,
    }
    html = f"<!DOCTYPE html><html><head></head><body><script>{js}</script></body></html>"
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "diff.html"
        tmp.write_text(html, encoding="utf-8")
        proc = subprocess.run(
            [chrome, "--no-sandbox", "--disable-gpu", "--allow-file-access-from-files",
             "--virtual-time-budget=6000", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=60,
        )
    m = re.search(r'<pre id="diff-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        sys.exit("Diff probe output not found.\n" + proc.stderr[-2000:])
    raw = (m.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
           .replace("&quot;", '"'))
    return json.loads(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true",
                     help="Re-render and replace the committed PNGs instead of diffing "
                          "against them.")
    args = ap.parse_args()

    if not SHEET_HTML.exists():
        sys.exit(f"{SHEET_HTML} not found.")

    chrome = find_chrome()
    baselines = sorted(PNG_DIR.glob("sheet-*.png")) if PNG_DIR.exists() else []
    if not baselines and not args.update:
        sys.exit(f"No committed baselines in {PNG_DIR}. Run with --update to create them.")

    failures = []

    # Widths come from whatever baselines already exist (so a third breakpoint
    # added later is picked up automatically), or the two documented D-16
    # widths if none exist yet. Height is always MEASURED from the page's own
    # scrollHeight at that width, never read off a committed PNG or guessed:
    # see measure_full_height()'s docstring for why a fixed guess is exactly
    # the bug this tool replaced.
    widths = [int(p.stem.split("-")[1]) for p in baselines] or [1440, 420]

    if args.update:
        PNG_DIR.mkdir(parents=True, exist_ok=True)
        for width in widths:
            height = measure_full_height(chrome, width)
            out = PNG_DIR / f"sheet-{width}.png"
            screenshot(chrome, width, height, out)
            print(f"Wrote {out} ({width}x{height})")
        return

    for baseline in baselines:
        width = int(baseline.stem.split("-")[1])
        height = measure_full_height(chrome, width)
        with tempfile.TemporaryDirectory() as td:
            fresh = pathlib.Path(td) / baseline.name
            screenshot(chrome, width, height, fresh)
            result = diff_pngs(chrome, baseline, fresh)

        if "error" in result:
            failures.append(f"{baseline.name}: diff harness error: {result['error']}")
            continue
        if result["sizeMismatch"]:
            failures.append(
                f"{baseline.name}: rendered size {result['bw']}x{result['bh']} != "
                f"committed size {result['aw']}x{result['ah']}")
            continue
        frac = result["changedPixels"] / result["totalPixels"]
        status = "ok" if frac <= DIFF_TOLERANCE else "FAIL"
        print(f"  {status:<4} {baseline.name}: {result['changedPixels']}/{result['totalPixels']} "
              f"px changed ({frac:.4%})")
        if frac > DIFF_TOLERANCE:
            failures.append(f"{baseline.name}: {frac:.4%} of pixels changed "
                             f"(tolerance {DIFF_TOLERANCE:.4%})")

    if failures:
        print(f"\n{len(failures)} of {len(baselines)} sheet(s) regressed:")
        for f in failures:
            print(f"  - {f}")
        print("\nIf this is an intentional, reviewed visual change, re-run with --update "
              "to accept it as the new baseline.")
        sys.exit(1)

    print(f"\n{len(baselines)}/{len(baselines)} sheets match their committed baseline.")


if __name__ == "__main__":
    main()
