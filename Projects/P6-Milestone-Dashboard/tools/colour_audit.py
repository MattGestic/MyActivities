#!/usr/bin/env python3
"""
Tokenization audit for the P6 Milestone Dashboard.

Regenerates Hardcoded_Colour_Audit.csv and prints the Measurement Log figures
defined in docs/tokenization/Token_Migration_Log.md.

The audit CSV was previously produced by an ad hoc script that lived outside
version control, which is exactly why it went missing at migration. This is
that method, committed, so any future measurement is reproducible.

Method (from Token_Migration_Log.md, "Re-running the audit"):
  Regex-extract all #hex / rgb() values from the <style> block, excluding the
  :root{} and html[data-theme=...]{} token-definition blocks. Count occurrences
  and distinct values, cross-reference against defined token values. Same
  approach for --space-* / --text-* references vs raw px in padding, margin,
  gap and font-size.

Scope: the <style> block plus inline style="" attributes in the markup. Inline
styles were originally out of scope, which hid a theme-blind gridline until an
exact-count assertion tripped over it (TD-12). The `source` column says which
of the two a row came from.

Usage:
  python3 tools/colour_audit.py [path-to-html] [-o output.csv]
Defaults to src/milestone-dashboard.html and
docs/tokenization/Hardcoded_Colour_Audit.csv relative to the project root.
"""

import argparse
import csv
import pathlib
import re
import sys
from collections import Counter

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
RGB_RE = re.compile(r"rgba?\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*(?:,\s*[\d.]+\s*)?\)")
TOKEN_DEF_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}]+)")
DECL_RE = re.compile(r"([-\w]+)\s*:\s*([^;{}]+)")

# Blocks that define tokens rather than consume them. Occurrences inside these
# are definitions, not hardcoded usage, so they are excluded from the counts.
#
# No preceding-character guard here on purpose. An earlier version required the
# selector to follow "}", "," or start-of-string, which silently missed the
# first theme block (preceded by a comment) and a second :root{} rule further
# down. Their contents were then counted as hardcoded usage, inflating the
# colour occurrence count by roughly 60%. If this regex is ever tightened,
# assert the found block count against the file first.
TOKEN_BLOCK_SELECTOR_RE = re.compile(
    r""":root\b[^{]*\{|html\s*\[\s*data-theme\s*=\s*["']?\w+["']?\s*\][^{]*\{""",
    re.VERBOSE,
)

PX_PROPS = ("padding", "margin", "gap")
PX_VALUE_RE = re.compile(r"\b\d+(?:\.\d+)?px\b")


def extract_style(html: str) -> tuple[str, int]:
    """Return the concatenated <style> content and its offset in the file."""
    blocks = list(re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S | re.I))
    if not blocks:
        sys.exit("No <style> block found.")
    # The file is single-<style> by design; if that ever changes, audit them all
    # but keep offsets honest by reporting against the first.
    return "".join(b.group(1) for b in blocks), blocks[0].start(1)


def token_block_spans(style: str) -> list[tuple[int, int]]:
    """Character spans of :root{} and html[data-theme=...]{} blocks."""
    spans = []
    for m in TOKEN_BLOCK_SELECTOR_RE.finditer(style):
        start = m.end() - 1
        depth, i = 0, start
        while i < len(style):
            if style[i] == "{":
                depth += 1
            elif style[i] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), i + 1))
                    break
            i += 1
    return spans


def in_spans(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def block_theme(style: str, start: int) -> str:
    """Which theme a token-definition block belongs to: light, dark or base."""
    head = style[start : style.index("{", start)]
    m = re.search(r"data-theme\s*=\s*[\"']?(\w+)", head)
    return m.group(1) if m else "base"


def defined_tokens(style: str, spans: list[tuple[int, int]]) -> dict[str, list[tuple[str, str]]]:
    """Map normalised token value -> [(token name, theme), ...].

    A value can be defined in more than one theme block. Keeping every
    definition (rather than the first) is what lets the audit tell a
    theme-blind hardcoded colour from a legitimately constant one: a literal
    matching only the dark theme's value is frozen dark in light mode.
    """
    tokens: dict[str, list[tuple[str, str]]] = {}
    for a, b in spans:
        theme = block_theme(style, a)
        for m in TOKEN_DEF_RE.finditer(style[a:b]):
            name, value = m.group(1), m.group(2).strip().rstrip(";").strip()
            key = normalise_colour(value)
            entry = (name, theme)
            if entry not in tokens.setdefault(key, []):
                tokens[key].append(entry)
    return tokens


def normalise_colour(value: str) -> str:
    """Lowercase, and expand #abc to #aabbcc so shorthand matches longhand."""
    v = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        v = "#" + "".join(c * 2 for c in v[1:])
    elif re.fullmatch(r"#[0-9a-f]{4}", v):
        v = "#" + "".join(c * 2 for c in v[1:])
    return re.sub(r"\s+", "", v)


def enclosing_declaration(style: str, pos: int) -> tuple[str, str]:
    """The CSS property and full value the occurrence at pos sits inside."""
    start = max(style.rfind(";", 0, pos), style.rfind("{", 0, pos)) + 1
    end = pos
    for terminator in (";", "}"):
        idx = style.find(terminator, pos)
        if idx != -1:
            end = min(end, idx) if end != pos else idx
    end = min(x for x in (style.find(";", pos), style.find("}", pos)) if x != -1)
    decl = style[start:end].strip()
    m = DECL_RE.match(decl)
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", decl)


def in_var_fallback(style: str, pos: int) -> bool:
    """True if the literal at pos is the fallback arm of a var() call.

    var(--tok, #hex) uses #hex only when --tok is undefined, so such a literal
    still follows the theme toggle and is not a tokenization defect. Walk back
    from the occurrence: if an unclosed "var(" opens before it and a comma
    separates them, the literal is in the fallback position.
    """
    depth = 0
    i = pos - 1
    saw_comma = False
    while i >= 0 and pos - i < 200:
        ch = style[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            if depth == 0:
                return saw_comma and style[max(0, i - 3): i] == "var"
            depth -= 1
        elif ch == "," and depth == 0:
            saw_comma = True
        elif ch in ";{}":
            return False
        i -= 1
    return False


def enclosing_selector(style: str, pos: int) -> str:
    """Best-effort selector for the rule containing pos."""
    open_brace = style.rfind("{", 0, pos)
    if open_brace == -1:
        return ""
    prev = max(style.rfind("}", 0, open_brace), style.rfind("{", 0, open_brace))
    sel = style[prev + 1 : open_brace].strip()
    return re.sub(r"\s+", " ", sel.splitlines()[-1].strip() if sel else "")


INLINE_STYLE_RE = re.compile(r'style\s*=\s*"([^"]*)"')


def classify(norm: str, tokens: dict, fallback: bool) -> tuple[str, list, list]:
    """Shared verdict logic for a colour literal, wherever it was found."""
    defs = tokens.get(norm, [])
    themes = sorted({t for _, t in defs})
    if fallback:
        verdict = "var() fallback, toggles correctly"
    elif len(themes) == 1 and themes[0] in ("light", "dark"):
        verdict = f"theme-blind ({themes[0]}-only)"
    elif defs:
        verdict = "matches token in all themes"
    else:
        verdict = ""
    return verdict, defs, themes


def _scan_inline_styles(html: str, tokens: dict) -> list[dict]:
    """Colour literals inside style="" attributes in the markup."""
    body = html[html.index("</style>"):] if "</style>" in html else html
    offset = html.index("</style>") if "</style>" in html else 0
    out = []
    for attr in INLINE_STYLE_RE.finditer(body):
        decls = attr.group(1)
        base = offset + attr.start(1)
        for regex in (HEX_RE, RGB_RE):
            for m in regex.finditer(decls):
                norm = normalise_colour(m.group(0))
                prop, value = enclosing_declaration(decls + ";", m.start())
                fallback = in_var_fallback(decls, m.start())
                verdict, defs, themes = classify(norm, tokens, fallback)
                # Element identity for an inline style is the tag it sits on.
                tag = re.search(r"<(\w+)[^>]*$", body[:attr.start()] + "<x")
                out.append({
                    "line": html.count("\n", 0, base + m.start()) + 1,
                    "selector": f"[inline] {(tag.group(1) if tag else '?')}",
                    "property": prop,
                    "raw_value": m.group(0),
                    "normalised_value": norm,
                    "declaration": value,
                    "matches_existing_token": "|".join(n for n, _ in defs),
                    "defined_in_themes": "|".join(themes),
                    "toggle_verdict": verdict,
                    "source": "inline-style",
                })
    return out


def audit(html_path: pathlib.Path, csv_path: pathlib.Path) -> dict[str, object]:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    style, style_offset = extract_style(html)
    spans = token_block_spans(style)
    tokens = defined_tokens(style, spans)

    rows = []
    rows.extend(_scan_inline_styles(html, tokens))
    for regex in (HEX_RE, RGB_RE):
        for m in regex.finditer(style):
            if in_spans(m.start(), spans):
                continue  # a token definition, not hardcoded usage
            raw = m.group(0)
            norm = normalise_colour(raw)
            prop, value = enclosing_declaration(style, m.start())
            if prop.startswith("--"):
                continue  # a token definition outside the theme blocks
            line = html.count("\n", 0, style_offset + m.start()) + 1
            defs = tokens.get(norm, [])
            themes = sorted({t for _, t in defs})
            fallback = in_var_fallback(style, m.start())
            # A literal that matches a token defined in exactly one theme is
            # frozen at that theme's value: it cannot follow the toggle.
            #
            # Unless it is a var() fallback. var(--tok, #hex) resolves to #hex
            # only when --tok is undefined, so a fallback still toggles
            # correctly and is NOT a defect. Reporting those as theme-blind
            # produced five false positives on the first pass, all in .rpt-hd,
            # which would have meant "fixing" code that already worked.
            if fallback:
                verdict = "var() fallback, toggles correctly"
            elif len(themes) == 1 and themes[0] in ("light", "dark"):
                verdict = f"theme-blind ({themes[0]}-only)"
            elif defs:
                verdict = "matches token in all themes"
            else:
                verdict = ""
            rows.append(
                {
                    "line": line,
                    "selector": enclosing_selector(style, m.start()),
                    "property": prop,
                    "raw_value": raw,
                    "normalised_value": norm,
                    "declaration": value,
                    "matches_existing_token": "|".join(n for n, _ in defs),
                    "defined_in_themes": "|".join(themes),
                    "toggle_verdict": verdict,
                    "source": "style-block",
                }
            )

    rows.sort(key=lambda r: r["line"])
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        # lineterminator is explicit: csv defaults to \r\n, which would make the
        # regenerated CSV show as fully rewritten in every diff.
        w = csv.DictWriter(fh, lineterminator="\n",
                           fieldnames=list(rows[0].keys()) if rows else
                           ["line", "selector", "property", "raw_value",
                            "normalised_value", "declaration",
                            "matches_existing_token", "defined_in_themes",
                            "toggle_verdict", "source"])
        w.writeheader()
        w.writerows(rows)

    # Spacing and text metrics, same exclusion of definition blocks.
    consumable = "".join(
        style[a:b]
        for a, b in _complement(spans, len(style))
    )
    space_refs = len(re.findall(r"var\(\s*--space-\d\s*\)", consumable))
    text_refs = len(re.findall(r"font-size\s*:\s*[^;}]*var\(\s*--text-[\w-]+\s*\)",
                               consumable))
    px_spacing = sum(
        1
        for m in DECL_RE.finditer(consumable)
        if m.group(1).strip().split("-")[0] in PX_PROPS
        and PX_VALUE_RE.search(m.group(2))
    )
    px_font = sum(
        1
        for m in DECL_RE.finditer(consumable)
        if m.group(1).strip() == "font-size" and PX_VALUE_RE.search(m.group(2))
    )

    distinct = {r["normalised_value"] for r in rows}
    matched = sum(1 for r in rows if r["matches_existing_token"])
    return {
        "occurrences": len(rows),
        "distinct": len(distinct),
        "matched": matched,
        "space_refs": space_refs,
        "text_refs": text_refs,
        "px_spacing": px_spacing,
        "px_font": px_font,
        "clusters": Counter(r["normalised_value"] for r in rows),
        "csv": csv_path,
    }


def _complement(spans, total):
    """Spans of the style block that are NOT token-definition blocks."""
    out, cursor = [], 0
    for a, b in sorted(spans):
        if a > cursor:
            out.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < total:
        out.append((cursor, total))
    return out


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("html", nargs="?", default=root / "src" / "milestone-dashboard.html")
    ap.add_argument("-o", "--out",
                    default=root / "docs" / "tokenization" / "Hardcoded_Colour_Audit.csv")
    args = ap.parse_args()

    r = audit(pathlib.Path(args.html), pathlib.Path(args.out))

    print(f"Audit written to {r['csv']}")
    print()
    print("Measurement Log values (append these as rows, never edit prior rows):")
    print(f"  Hardcoded colour occurrences                     {r['occurrences']}")
    print(f"  Distinct hardcoded colour values                 {r['distinct']}")
    print(f"  Colour occurrences matching an existing token    {r['matched']}")
    print(f"  --space-* token references in file               {r['space_refs']}")
    print(f"  Hardcoded padding/margin/gap declarations (px)   {r['px_spacing']}")
    print(f"  var(--text-*) font-size references in file       {r['text_refs']}")
    print(f"  Hardcoded font-size declarations (px)            {r['px_font']}")
    print()
    repeats = [(v, n) for v, n in r["clusters"].most_common() if n > 1]
    print(f"Values used more than once (Phase 2 consolidation candidates): {len(repeats)}")
    for value, n in repeats[:12]:
        print(f"  {value:<28} x{n}")


if __name__ == "__main__":
    main()
