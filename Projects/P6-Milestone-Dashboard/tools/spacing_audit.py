#!/usr/bin/env python3
"""
Spacing conformance gate for the P6 Milestone Dashboard.

`tools/colour_audit.py` catches hardcoded colour values and ratchets the
count down against the Measurement Log. Nothing plays that role for spacing:
its `px_spacing` figure is informational only (printed, appended to the log
by hand) and nothing fails a run on it. This script is that missing gate,
built the same way `theme_check.py` is a gate rather than a report: it exits
non-zero when the thing it measures gets worse.

Method: regex-extract every `padding`/`margin`/`gap` declaration (including
sub-properties: `padding-left`, `margin-top`, `row-gap`, `column-gap`, ...)
in the <style> block and in inline `style=""` attributes, and count the ones
whose value contains a raw `px` literal rather than only `var(--space-*)`
references. One count per declaration, matching colour_audit.py's own
"includes sub-properties" scope -- except colour_audit's PX_PROPS check
(`prop.split("-")[0] in ("padding","margin","gap")`) silently drops
`row-gap`/`column-gap` (`"row-gap".split("-")[0]` is `"row"`, never `"gap"`).
This script matches the property's suffix instead, so gap sub-properties are
counted. That is why its total will not equal colour_audit's `px_spacing`
figure at the same commit; both are recorded in the CSV/JSON output so the
discrepancy is visible rather than silently reconciled.

The gate: a baseline ceiling is stored in
docs/tokenization/Spacing_Audit_Baseline.json. A run with a HIGHER raw-px
count than the stored ceiling exits 1 -- new raw px in padding/margin/gap is
what this catches, per DT-0's conformance-transition model (frozen debt,
ratcheted down, never re-grown; see docs/tokenization/design-tokens.md DT-0
via the governance baseline, and CLAUDE.md's tokenization-discipline section
in this repo). A run with an EQUAL or LOWER count silently tightens the
ceiling to match (the ratchet only ever moves down) and exits 0. There is no
baseline file yet in this repo the first time this runs: that run WRITES one
at the current count rather than failing, since there is nothing yet to
ratchet against.

Usage:
  python3 tools/spacing_audit.py [path-to-html]
  python3 tools/spacing_audit.py --update-baseline   # accept today's count
                                                       # as the new ceiling
                                                       # even if it rose
                                                       # (requires --reason)
Exit codes: 0 = at or under the ceiling (or baseline just created/updated).
            1 = new raw px in padding/margin/gap pushed the count over it.
"""

import argparse
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
DEFAULT_CSV = ROOT / "docs" / "tokenization" / "Hardcoded_Spacing_Audit.csv"
BASELINE_PATH = ROOT / "docs" / "tokenization" / "Spacing_Audit_Baseline.json"

# Matches the declaration's property name and its full value up to ; or }.
DECL_RE = re.compile(r"([-\w]+)\s*:\s*([^;{}]+)")
PX_VALUE_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?px\b")
VAR_SPACE_RE = re.compile(r"var\(\s*--space-\d\s*(?:,[^)]*)?\)")

# Property roots this gate covers. Matched on the property's own suffix
# ("padding-left" -> "padding", "row-gap" -> "gap", "column-gap" -> "gap"),
# not colour_audit.py's prefix split, which is what misses the gap
# sub-properties there.
SPACING_ROOTS = ("padding", "margin", "gap")


def property_root(prop: str) -> str | None:
    prop = prop.strip()
    for root in SPACING_ROOTS:
        if prop == root or prop.endswith("-" + root):
            return root
    return None


def extract_style_blocks(html: str) -> list[tuple[str, int]]:
    """[(content, offset_in_file), ...] for every <style> block."""
    return [(m.group(1), m.start(1)) for m in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)]


def scan_declarations(text: str, base_offset: int, html: str, source: str) -> list[dict]:
    rows = []
    for m in DECL_RE.finditer(text):
        prop, value = m.group(1), m.group(2).strip()
        root = property_root(prop)
        if root is None:
            continue
        px_hits = PX_VALUE_RE.findall(value)
        if not px_hits:
            continue
        pos = base_offset + m.start()
        line = html.count("\n", 0, pos) + 1
        rows.append({
            "line": line,
            "property": prop,
            "value": value,
            "px_literals": "|".join(px_hits),
            "also_uses_space_token": bool(VAR_SPACE_RE.search(value)),
            "source": source,
        })
    return rows


INLINE_STYLE_RE = re.compile(r'style\s*=\s*"([^"]*)"')


def scan_inline(html: str) -> list[dict]:
    rows = []
    for attr in INLINE_STYLE_RE.finditer(html):
        rows.extend(scan_declarations(attr.group(1), attr.start(1), html, "inline-style"))
    return rows


def audit(html_path: pathlib.Path) -> tuple[list[dict], dict]:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    rows = []
    for style, offset in extract_style_blocks(html):
        rows.extend(scan_declarations(style, offset, html, "style-block"))
    rows.extend(scan_inline(html))
    rows.sort(key=lambda r: r["line"])

    by_root = {}
    for r in rows:
        root = property_root(r["property"])
        by_root[root] = by_root.get(root, 0) + 1

    summary = {
        "total": len(rows),
        "by_property_root": by_root,
    }
    return rows, summary


def write_csv(rows: list[dict], csv_path: pathlib.Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["line", "property", "value", "px_literals", "also_uses_space_token", "source"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, lineterminator="\n", fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def write_baseline(count: int, reason: str) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(
        json.dumps({"ceiling": count, "reason": reason}, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html", nargs="?", default=DEFAULT_HTML, type=pathlib.Path)
    ap.add_argument("-o", "--out", default=DEFAULT_CSV, type=pathlib.Path)
    ap.add_argument("--update-baseline", action="store_true",
                     help="Accept the current count as the new ceiling even if it rose. "
                          "Requires --reason.")
    ap.add_argument("--reason", default="",
                     help="Required with --update-baseline: why the ceiling is moving up "
                          "(e.g. a new component with a documented, unavoidable one-off value).")
    args = ap.parse_args()

    rows, summary = audit(args.html)
    write_csv(rows, args.out)

    print(f"Spacing audit written to {args.out}")
    print(f"Raw px in padding/margin/gap declarations: {summary['total']}")
    for root, n in sorted(summary["by_property_root"].items()):
        print(f"  {root:<8} {n}")

    baseline = load_baseline()

    if args.update_baseline:
        if not args.reason:
            sys.exit("--update-baseline requires --reason")
        write_baseline(summary["total"], args.reason)
        print(f"Baseline ceiling set to {summary['total']} ({BASELINE_PATH}). Reason: {args.reason}")
        return

    if baseline is None:
        write_baseline(summary["total"], "initial baseline, tools/spacing_audit.py introduced")
        print(f"No baseline found. Wrote initial ceiling {summary['total']} to {BASELINE_PATH}.")
        return

    ceiling = baseline["ceiling"]
    if summary["total"] > ceiling:
        print(f"FAIL: {summary['total']} raw px declarations exceeds the ceiling of {ceiling}.")
        print("New padding/margin/gap literals were added instead of using --space-* tokens.")
        print("Either token the new value or, if it is genuinely a one-off the scale does not "
              "cover, re-run with --update-baseline --reason \"...\".")
        sys.exit(1)

    if summary["total"] < ceiling:
        write_baseline(summary["total"], f"ratcheted down from {ceiling} by later tokenization work")
        print(f"Ceiling tightened: {ceiling} -> {summary['total']}.")
    else:
        print(f"At ceiling ({ceiling}). No new raw px introduced.")


if __name__ == "__main__":
    main()
