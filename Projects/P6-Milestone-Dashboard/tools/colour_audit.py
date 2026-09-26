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
import json
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


## =========================================================================
## Strict tier-rule mode (P55 central-token rule)
##
## Tier 1: --pal-* / --shadow-color / --pal-*-rgb, ONLY inside
##         html[data-theme="light"]{} / html[data-theme="dark"]{}. These are
##         the only declarations allowed to hold a literal colour.
## Tier 2/3: --color-* in :root, and every component alias. Values must be
##         var(...)/color-mix(...)/transparent/currentColor/inherit/none.
## Everywhere else: no literal colour at all (CSS, markup, JS).
##
## This does NOT reuse the non-strict scan above (which deliberately excludes
## var() fallbacks and only looks at the <style> block plus inline style=).
## Strict mode is a different, wider question, so it is a separate pass with
## its own parser, kept beside the original rather than reusing its
## exclusions, which would silently hide fallback and JS/markup violations.
## =========================================================================

STRICT_HEX_RE = re.compile(r"(?<!&)#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
HSL_RE = re.compile(
    r"hsla?\(\s*[\d.]+\s*(?:deg)?\s*,\s*[\d.]+%\s*,\s*[\d.]+%\s*(?:,\s*[\d.]+\s*)?\)"
)
COLOR_CONTEXT_RE = re.compile(r"color|background|border|fill|stroke|outline|shadow", re.I)

# A working subset of CSS named colours. Not exhaustive by spec, but covers
# every named colour actually reachable in this file's context.
NAMED_COLORS = {
    "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque",
    "black", "blanchedalmond", "blue", "blueviolet", "brown", "burlywood",
    "cadetblue", "chartreuse", "chocolate", "coral", "cornflowerblue", "cornsilk",
    "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray",
    "darkgreen", "darkgrey", "darkkhaki", "darkmagenta", "darkolivegreen",
    "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen",
    "darkslateblue", "darkslategray", "darkslategrey", "darkturquoise",
    "darkviolet", "deeppink", "deepskyblue", "dimgray", "dimgrey", "dodgerblue",
    "firebrick", "floralwhite", "forestgreen", "fuchsia", "gainsboro",
    "ghostwhite", "gold", "goldenrod", "gray", "green", "greenyellow", "grey",
    "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender",
    "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral",
    "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey",
    "lightpink", "lightsalmon", "lightseagreen", "lightskyblue",
    "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow", "lime",
    "limegreen", "linen", "magenta", "maroon", "mediumaquamarine", "mediumblue",
    "mediumorchid", "mediumpurple", "mediumseagreen", "mediumslateblue",
    "mediumspringgreen", "mediumturquoise", "mediumvioletred", "midnightblue",
    "mintcream", "mistyrose", "moccasin", "navajowhite", "navy", "oldlace",
    "olive", "olivedrab", "orange", "orangered", "orchid", "palegoldenrod",
    "palegreen", "paleturquoise", "palevioletred", "papayawhip", "peachpuff",
    "peru", "pink", "plum", "powderblue", "purple", "rebeccapurple", "red",
    "rosybrown", "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen",
    "seashell", "sienna", "silver", "skyblue", "slateblue", "slategray",
    "slategrey", "snow", "springgreen", "steelblue", "tan", "teal", "thistle",
    "tomato", "turquoise", "violet", "wheat", "white", "whitesmoke", "yellow",
    "yellowgreen",
}

# Words that are colour-shaped but explicitly not literals under the P55 rule.
NON_LITERAL_COLOR_WORDS = {"transparent", "currentcolor", "inherit", "none"}


def _mask_span_keep_newlines(text: str, pattern: str, flags=0) -> str:
    """Replace every match of `pattern` with spaces, preserving newlines and
    length, so line numbers computed against the ORIGINAL text still line up
    against this masked copy."""
    def repl(m):
        return "".join(ch if ch == "\n" else " " for ch in m.group(0))
    return re.sub(pattern, repl, text, flags=flags)


def mask_block_comments(text: str) -> str:
    return _mask_span_keep_newlines(text, r"/\*.*?\*/", re.S)


def mask_line_comments(text: str) -> str:
    # Guard against "http://" etc. by requiring the // not be preceded by ':'.
    return _mask_span_keep_newlines(text, r"(?<!:)//[^\n]*")


def mask_html_comments(text: str) -> str:
    return _mask_span_keep_newlines(text, r"<!--.*?-->", re.S)


def find_literals(value: str, prop: str) -> list[str]:
    """Every literal colour token in `value`. Hex/rgb()/hsl() always count;
    a bare named colour counts only when `prop` is a colour-bearing property,
    per the false-positive rule (named words only count in a colour context).
    """
    lits: list[str] = []
    for regex in (STRICT_HEX_RE, RGB_RE, HSL_RE):
        lits.extend(m.group(0) for m in regex.finditer(value))
    if COLOR_CONTEXT_RE.search(prop or ""):
        # Strip custom-property identifiers first: "var(--pal-navy)" contains
        # the substring "navy", which is a real named colour word but is not
        # a literal here, it is a token reference. Without this a --pal-*
        # token whose name happens to embed a colour word (navy, teal, ...)
        # is misread as a literal on every rule that merely consumes it.
        scrubbed = re.sub(r"--[\w-]+", " ", value)
        for wm in re.finditer(r"\b[a-zA-Z]{3,}\b", scrubbed):
            w = wm.group(0).lower()
            if w in NAMED_COLORS:
                lits.append(w)
    return lits


def is_color_literal(val: str) -> bool:
    v = val.strip()
    if not v or v.lower() in NON_LITERAL_COLOR_WORDS or v.startswith("url("):
        return False
    if STRICT_HEX_RE.fullmatch(v) or RGB_RE.fullmatch(v) or HSL_RE.fullmatch(v):
        return True
    return v.lower() in NAMED_COLORS


def parse_css_rules(text: str, base_offset: int = 0) -> list[dict]:
    """Flatten every LEAF rule (selector with a declaration body, no nested
    braces) out of `text`, recursing into @media/@supports wrappers. Returns
    dicts with selector, body, and body's absolute offset into the ORIGINAL
    (unmasked-length-preserved) text `base_offset` was measured against.
    """
    rules: list[dict] = []
    i, n = 0, len(text)
    while i < n:
        brace = text.find("{", i)
        if brace == -1:
            break
        selector = text[i:brace].strip()
        depth, j = 1, brace + 1
        while j < n and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        body = text[brace + 1: j - 1]
        body_start = brace + 1
        if selector.startswith("@"):
            rules.extend(parse_css_rules(body, base_offset + body_start))
        elif selector:
            rules.append({"selector": selector, "body": body,
                          "body_start": base_offset + body_start})
        i = j
    return rules


def _is_pal_decl(prop: str) -> bool:
    p = prop.strip().lower()
    return p.startswith("--pal-") or p == "--shadow-color"


def strict_audit(html_path: pathlib.Path) -> dict:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    html_lines = html.split("\n")

    def line_snippet(abs_pos: int) -> tuple[int, str]:
        line = html.count("\n", 0, abs_pos) + 1
        snippet = html_lines[line - 1].strip() if 0 <= line - 1 < len(html_lines) else ""
        return line, snippet

    style_m = re.search(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)
    if not style_m:
        sys.exit("No <style> block found.")
    style_text = style_m.group(1)
    style_offset = style_m.start(1)
    style_masked = mask_block_comments(style_text)

    script_m = re.search(r'<script\s+id=["\']app-script["\'][^>]*>', html, re.I)
    if not script_m:
        sys.exit('No <script id="app-script"> block found.')
    js_start = script_m.end()
    js_close = html.find("</script>", js_start)
    if js_close == -1:
        js_close = len(html)
    js_text = html[js_start:js_close]
    js_masked = mask_line_comments(mask_block_comments(js_text))

    markup_start = style_m.end()
    markup_text = html[markup_start:script_m.start()]
    markup_masked = mask_html_comments(markup_text)

    violations: list[dict] = []
    warnings: list[dict] = []
    # token -> {theme: line}
    pal_defs: dict[str, dict[str, int]] = {}

    # ---------------- CSS zone ----------------
    for rule in parse_css_rules(style_masked):
        selector = rule["selector"]
        theme_m = re.match(r'html\s*\[\s*data-theme\s*=\s*["\']?(\w+)', selector)
        theme = theme_m.group(1) if theme_m else None
        for decl_m in re.finditer(r"([^:;]+):([^;]+);?", rule["body"]):
            prop = decl_m.group(1).strip()
            value = decl_m.group(2).strip()
            if not prop:
                continue
            abs_pos = style_offset + rule["body_start"] + decl_m.start(2)
            line, snippet = line_snippet(abs_pos)
            is_pal = _is_pal_decl(prop)
            lits = find_literals(value, prop)
            if theme is not None:
                if is_pal:
                    pal_defs.setdefault(prop.lower(), {})[theme] = line
                else:
                    for lit in lits:
                        violations.append({
                            "zone": "css", "line": line, "literal": lit, "snippet": snippet,
                            "kind": "tier1-misuse",
                            "detail": f'{prop} inside html[data-theme="{theme}"] is not '
                                      f'--pal-*/--shadow-color but holds a literal',
                        })
            else:
                if is_pal:
                    violations.append({
                        "zone": "css", "line": line, "literal": lits[0] if lits else prop,
                        "snippet": snippet, "kind": "pal-outside-theme",
                        "detail": f"{prop} defined outside the theme blocks",
                    })
                else:
                    for lit in lits:
                        violations.append({
                            "zone": "css", "line": line, "literal": lit, "snippet": snippet,
                            "kind": "literal-in-css", "detail": f"{prop}:{value}",
                        })
                if selector != ":root":
                    for vm in re.finditer(r"var\(\s*(--pal-[\w-]+)", value):
                        warnings.append({
                            "zone": "css", "line": line, "literal": vm.group(1),
                            "snippet": snippet, "kind": "pal-var-outside-tier2",
                            "detail": f'"{selector}" consumes {vm.group(1)} directly; '
                                      f'rules should consume roles, not palette',
                        })

    for token, themes in pal_defs.items():
        if set(themes) != {"light", "dark"}:
            any_line = next(iter(themes.values()))
            violations.append({
                "zone": "css", "line": any_line, "literal": token, "snippet": "",
                "kind": "pal-missing-theme",
                "detail": f"{token} defined in {sorted(themes)} only, missing from the other theme",
            })

    # ---------------- Markup zone ----------------
    for m in re.finditer(r'style\s*=\s*"([^"]*)"', markup_masked):
        base = markup_start + m.start(1)
        line, snippet = line_snippet(base)
        for part in m.group(1).split(";"):
            if ":" not in part:
                continue
            prop, _, value = part.partition(":")
            for lit in find_literals(value.strip(), prop.strip()):
                violations.append({
                    "zone": "markup", "line": line, "literal": lit, "snippet": snippet,
                    "kind": "literal-inline-style", "detail": part.strip(),
                })

    for m in re.finditer(r'\b(fill|stroke)\s*=\s*"([^"]*)"', markup_masked):
        val = m.group(2)
        if is_color_literal(val):
            base = markup_start + m.start(2)
            line, snippet = line_snippet(base)
            violations.append({
                "zone": "markup", "line": line, "literal": val.strip(), "snippet": snippet,
                "kind": "literal-svg-attr", "detail": f"{m.group(1)}={val!r}",
            })

    # ---------------- JS zone ----------------
    def scan_markup_fragment(frag: str, frag_offset: int, kind_suffix: str):
        for fm in re.finditer(r'style\s*=\s*"([^"]*)"', frag):
            base = frag_offset + fm.start(1)
            line, snippet = line_snippet(base)
            for part in fm.group(1).split(";"):
                if ":" not in part:
                    continue
                prop, _, value = part.partition(":")
                for lit in find_literals(value.strip(), prop.strip()):
                    violations.append({
                        "zone": "js", "line": line, "literal": lit, "snippet": snippet,
                        "kind": f"literal-js-{kind_suffix}", "detail": part.strip(),
                    })
        for fm in re.finditer(r'\b(fill|stroke)\s*=\s*"([^"]*)"', frag):
            val = fm.group(2)
            if is_color_literal(val):
                base = frag_offset + fm.start(2)
                line, snippet = line_snippet(base)
                violations.append({
                    "zone": "js", "line": line, "literal": val.strip(), "snippet": snippet,
                    "kind": f"literal-js-{kind_suffix}", "detail": f"{fm.group(1)}={val!r}",
                })

    # .style.cssText = '...'
    for m in re.finditer(r"\.style\.cssText\s*=\s*(['\"`])(.*?)\1", js_masked, re.S):
        base = js_start + m.start(2)
        for part in m.group(2).split(";"):
            if ":" not in part:
                continue
            prop, _, value = part.partition(":")
            local_line, local_snip = line_snippet(base)
            for lit in find_literals(value.strip(), prop.strip()):
                violations.append({
                    "zone": "js", "line": local_line, "literal": lit, "snippet": local_snip,
                    "kind": "literal-js-style", "detail": part.strip(),
                })

    # .style.<prop> = '...' (and any other .style.x = "literal")
    for m in re.finditer(r"\.style\.([A-Za-z]+)\s*=\s*(['\"`])(.*?)\2", js_masked):
        propname = m.group(1)
        if not COLOR_CONTEXT_RE.search(propname):
            continue
        value = m.group(3)
        base = js_start + m.start(3)
        line, snippet = line_snippet(base)
        lits = find_literals(value, "color")
        if not lits and value.strip().lower() in NAMED_COLORS:
            lits = [value.strip().lower()]
        for lit in dict.fromkeys(lits):
            violations.append({
                "zone": "js", "line": line, "literal": lit, "snippet": snippet,
                "kind": "literal-js-style", "detail": f".style.{propname}={value!r}",
            })

    # canvas fillStyle / strokeStyle
    for m in re.finditer(r"\.(fillStyle|strokeStyle)\s*=\s*(['\"`])(.*?)\2", js_masked):
        value = m.group(3)
        base = js_start + m.start(3)
        line, snippet = line_snippet(base)
        lits = find_literals(value, "color")
        if not lits and value.strip().lower() in NAMED_COLORS:
            lits = [value.strip().lower()]
        for lit in dict.fromkeys(lits):
            violations.append({
                "zone": "js", "line": line, "literal": lit, "snippet": snippet,
                "kind": "literal-js-canvas", "detail": f".{m.group(1)}={value!r}",
            })

    # JSON-shaped object keys: "bg": "#1D4D3A", fill: 'red', etc.
    for m in re.finditer(
        r'["\']?\b(bg|color|fill|stroke|background|border\w*|outline|shadow\w*)\b["\']?'
        r'\s*:\s*(["\'])((?:(?!\2).)*)\2',
        js_masked,
    ):
        key, value = m.group(1), m.group(3)
        base = js_start + m.start(3)
        line, snippet = line_snippet(base)
        lits = find_literals(value, key)
        if not lits and value.strip().lower() in NAMED_COLORS:
            lits = [value.strip().lower()]
        for lit in dict.fromkeys(lits):
            violations.append({
                "zone": "js", "line": line, "literal": lit, "snippet": snippet,
                "kind": "literal-js-object", "detail": f'"{key}": {value!r}',
            })

    # Template-literal HTML: scan backtick strings the same way as markup.
    for m in re.finditer(r"`([^`]*)`", js_masked, re.S):
        scan_markup_fragment(m.group(1), js_start + m.start(1), "template")

    return {"violations": violations, "warnings": warnings}


def load_exceptions(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def apply_exceptions(violations: list[dict], exceptions: list[dict]) -> tuple[list[dict], list[dict]]:
    kept, excepted = [], []
    for v in violations:
        matched = False
        for exc in exceptions:
            if (exc.get("line_contains", "") in (v.get("snippet") or "")
                    and str(exc.get("literal", "")).lower() == str(v["literal"]).lower()):
                matched = True
                break
        (excepted if matched else kept).append(v)
    return kept, excepted


def run_strict(html_path: pathlib.Path, ceiling: int, exceptions_path: pathlib.Path) -> int:
    result = strict_audit(html_path)
    exceptions = load_exceptions(exceptions_path)
    kept, excepted = apply_exceptions(result["violations"], exceptions)

    print(f"Strict tokenization audit: {html_path}")
    print(f"Violations: {len(kept)} (ceiling {ceiling}); "
          f"excepted: {len(excepted)}; warnings: {len(result['warnings'])}")
    print()
    for v in kept:
        print(f"{v['zone']} {v['line']} {v['literal']} | {v['snippet']}")

    if result["warnings"]:
        print()
        print(f"Warnings (not counted against the ceiling): {len(result['warnings'])}")
        for w in result["warnings"]:
            print(f"  {w['zone']} {w['line']} {w['literal']} | {w['snippet']}")

    print()
    if len(kept) > ceiling:
        print(f"FAIL: {len(kept)} violation(s) exceed ceiling {ceiling}.")
        return 1
    print(f"PASS: {len(kept)} violation(s) at or under ceiling {ceiling}.")
    return 0


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("html", nargs="?", default=root / "src" / "milestone-dashboard.html")
    ap.add_argument("-o", "--out",
                    default=root / "docs" / "tokenization" / "Hardcoded_Colour_Audit.csv")
    ap.add_argument("--strict", action="store_true",
                    help="Apply the P55 tier rule across CSS, markup and JS "
                         "instead of the legacy <style>-block-only scan.")
    ap.add_argument("--ceiling", type=int, default=None,
                    help="Max violations allowed before exiting 1. Defaults to 0 under --strict.")
    ap.add_argument("--exceptions", default=root / "tools" / "colour_exceptions.json")
    args = ap.parse_args()

    if args.strict:
        ceiling = args.ceiling if args.ceiling is not None else 0
        sys.exit(run_strict(pathlib.Path(args.html), ceiling, pathlib.Path(args.exceptions)))

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
