#!/usr/bin/env python3
"""Split src/milestone-dashboard.html into named, hashed regions.

A region is the unit the change-scoped runner (tools/run_checks.py) tracks.
Every byte of the app file belongs to exactly one region, so any edit changes
at least one region hash.

Kinds
  js      one per top-level chunk of <script id="app-script">. A chunk starts
          at column 0 at bracket depth 0 (outside strings, comments, template
          literals and regex literals). It is named after what it declares:
          `function NAME` -> `js:NAME` (meta fn=True), `const|let|var NAME` ->
          `js:NAME`, `class NAME` -> `js:NAME`; anything else (IIFEs,
          listeners, 'use strict') -> `js:@js:<sha1 of the statement text>`. The comment
          block directly above a chunk belongs to it.
  vendor  the three embedded libraries, one region each.
  css     one per style rule of the main <style>, including rules nested in
          @media / @supports. Keyed `css:<media ctx>|<selector>` with all
          whitespace removed and ' turned into ", so the key matches the
          browser's CSSOM selectorText normalised the same way. The hash folds in
          the key of the previous rule, so moving a rule (a cascade-order change
          with identical text) also changes a hash. At-rules with declaration
          blocks (@keyframes, @font-face, ...) are `css:@at:<prelude>` and count
          as always used. The @media wrapper text is `csswrap:` (never used:
          a change of condition changes every contained rule key instead).
  markup  one per element with an id (`markup:#id`), anywhere in <body>, and
          one per top-level body element without an id (`markup:body>tag:N`,
          N = ordinal among <body>'s id-less children of that tag). A region's text is the
          element's source with nested id'd elements cut out, so editing a
          card field changes `#that-field`, not `#ms-dialog`.
  rest    everything not covered above (head, the <style>/<script> tags
          themselves, text between body elements). Always used by a browser
          check.

CLI
  python3 tools/check_map/regions.py regions [--list] [--file PATH]
"""
import hashlib
import html.parser
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "src" / "milestone-dashboard.html"

VENDOR_IDS = ("vendor-sheetjs", "vendor-slickgrid", "vendor-slickgrid-css")
REGEX_KW = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete",
            "void", "throw", "yield", "await", "instanceof"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def norm_sel(s):
    """The one normalisation used on both sides (source and CSSOM): drop all
    whitespace and turn ' into ". The source side additionally gets what the
    browser's serializer does on its own: quoted attribute values, legacy
    single-colon pseudo-elements as ::, and an implicit `*` dropped."""
    s = re.sub(r"\[\s*([\w-]+)\s*([~|^$*]?=)\s*([^\"'\]\s]+)\s*\]", r'[\1\2"\3"]', s)
    s = re.sub(r"(?<!:):(before|after|first-line|first-letter)\b", r"::\1", s)
    s = re.sub(r"\*(?=[:.#\[])", "", s)
    return re.sub(r"\s+", "", s).replace("'", '"')


# --------------------------------------------------------------------------
# JS
# --------------------------------------------------------------------------
def js_chunk_starts(src):
    """Offsets of column-0 lines at depth 0 in code state, with a tag:
    'c' if the line opens with a comment, 's' for a statement start."""
    n = len(src)
    i = 0
    depth = 0
    tmpl = []          # depth at which each open `${` was entered
    out = []
    last = ""          # last significant char (or keyword marker 'K' / ident 'I')
    word = ""
    line_start = True

    def regex_ok():
        if last in ("", "(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";",
                    "+", "-", "*", "%", "<", ">", "~", "^", "K"):
            return True
        return False

    while i < n:
        c = src[i]
        if line_start:
            line_start = False
            if depth == 0 and not tmpl and c not in " \t\r\n":
                if src.startswith("//", i) or src.startswith("/*", i):
                    out.append((i, "c"))
                elif c not in "})].+-?:,&|*":
                    out.append((i, "s"))
        if c == "\n":
            line_start = True
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            # newlines inside a block comment are not line starts
            i = n if j < 0 else j + 2
            continue
        if c in "'\"":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            last = "a"
            continue
        if c == "`":
            i = _skip_template(src, i + 1, tmpl, depth)
            if i < 0:     # entered a ${ expression
                i = -i
                depth += 1
                last = "{"
            else:
                last = "a"
            continue
        if c == "/":
            if regex_ok():
                j = i + 1
                cls = False
                while j < n and src[j] != "\n":
                    ch = src[j]
                    if ch == "\\":
                        j += 2
                        continue
                    if ch == "[":
                        cls = True
                    elif ch == "]":
                        cls = False
                    elif ch == "/" and not cls:
                        break
                    j += 1
                j += 1
                while j < n and (src[j].isalnum()):
                    j += 1
                i = j
                last = "a"
                continue
            last = "/"
            i += 1
            continue
        if c.isalnum() or c in "_$":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            word = src[i:j]
            last = "K" if word in REGEX_KW else "a"
            i = j
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if c == "}" and tmpl and depth == tmpl[-1]:
                tmpl.pop()
                k = _skip_template(src, i + 1, tmpl, depth)
                if k < 0:
                    i = -k
                    depth += 1
                    last = "{"
                else:
                    i = k
                    last = "a"
                continue
        last = c
        i += 1
    return out, depth, tmpl


def _skip_template(src, i, tmpl, depth):
    """Scan template literal body from i. Returns offset after the closing
    backtick, or -(offset after `${`) having pushed onto tmpl."""
    n = len(src)
    while i < n:
        ch = src[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "`":
            return i + 1
        if ch == "$" and i + 1 < n and src[i + 1] == "{":
            tmpl.append(depth)
            return -(i + 2)
        i += 1
    return n


FN_RE = re.compile(r"(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)")
DECL_RE = re.compile(r"(?:const|let|var|class)\s+([A-Za-z_$][\w$]*)")


def js_regions(src, base):
    starts, depth, tmpl = js_chunk_starts(src)
    if depth != 0 or tmpl:
        raise SystemExit(f"regions: JS scan ended at depth {depth} (template stack {tmpl});"
                         " the tokenizer lost track. Fix js_chunk_starts before trusting the map.")
    # Attach a run of comment-starts to the statement that follows it.
    chunks = []
    pending = None
    for off, t in starts:
        if t == "c":
            if pending is None:
                pending = off
            continue
        chunks.append((pending if pending is not None else off, off))
        pending = None
    regs = []
    for k, (cstart, sstart) in enumerate(chunks):
        end = chunks[k + 1][0] if k + 1 < len(chunks) else len(src)
        if k == 0:
            cstart = 0  # leading comments / newline belong to the first chunk
        text = src[cstart:end]
        first = src[sstart:src.find("\n", sstart) if src.find("\n", sstart) >= 0 else len(src)]
        m = FN_RE.match(first)
        fn = False
        if m:
            name, fn = m.group(1), True
        else:
            m = DECL_RE.match(first)
            # anonymous chunks are content-addressed (the statement text, not
            # the comment above it), so inserting one does not rename the others
            name = m.group(1) if m else "@js:" + hashlib.sha1(src[sstart:end].strip().encode()).hexdigest()[:10]
        lead = src[cstart:sstart]
        regs.append({"name": "js:" + name, "kind": "js", "fn": fn, "ident": name,
                     "start": base + cstart, "end": base + end, "text": text,
                     "note": _behaviour_note(lead), "line0": first.strip()[:160]})
    return regs


def _behaviour_note(lead):
    """The comment block directly above the declaration (contiguous lines, no
    blank line between it and the declaration), flattened to one line."""
    lines = lead.rstrip("\n").split("\n")
    block = []
    for ln in reversed(lines):
        if not ln.strip():
            break
        block.append(ln)
    block.reverse()
    txt = " ".join(re.sub(r"^\s*(//+|/\*+|\*+/?)\s?", "", ln).replace("*/", "").strip()
                   for ln in block)
    txt = re.sub(r"\s+", " ", txt).strip(" =-")
    return txt[:240]


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)


def _match_brace(clean, i):
    """clean[i] == '{'; return index of the matching '}'."""
    d = 0
    n = len(clean)
    q = None
    while i < n:
        ch = clean[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "{":
            d += 1
        elif ch == "}":
            d -= 1
            if d == 0:
                return i
        i += 1
    raise SystemExit("regions: unbalanced CSS braces")


def has_class_or_id(sel):
    s = re.sub(r"\[[^\]]*\]", "", sel)   # attribute selectors may contain . or #
    s = re.sub(r"\"[^\"]*\"|'[^']*'", "", s)
    return bool(re.search(r"[.#][A-Za-z_\\-]", s))


def sel_tokens(sel):
    """Classes and ids in each comma part's compound selectors (pseudos and
    attribute selectors dropped). Used to decide whether a NEW rule could match
    anything a check rendered."""
    parts = []
    for part in _split_top(sel, ","):
        p = re.sub(r"\[[^\]]*\]", "", part)
        p = re.sub(r"::?[A-Za-z-]+(\((?:[^()]|\([^()]*\))*\))?", "", p)
        parts.append({"cls": re.findall(r"\.([A-Za-z_][\w-]*)", p),
                      "ids": re.findall(r"#([A-Za-z_][\w-]*)", p)})
    return parts


def _split_top(s, sep):
    out, d, cur = [], 0, ""
    for ch in s:
        if ch in "([":
            d += 1
        elif ch in ")]":
            d -= 1
        if ch == sep and d == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def css_regions(css, base):
    clean = _strip_comments(css)
    regs = []
    state = {"prev": ""}

    def walk(lo, hi, ctx):
        seg = lo
        i = lo
        while i < hi:
            if clean[i].isspace():
                i += 1
                continue
            j = i
            while j < hi and clean[j] not in "{;}":
                j += 1
            if j >= hi or clean[j] == "}":
                break
            prelude = clean[i:j].strip()
            if clean[j] == ";":
                regs.append(_css_reg("css:@at:" + norm_sel(prelude), css, seg, j + 1, base,
                                     always=True, ctx=ctx, prelude=prelude, state=state))
                seg = i = j + 1
                continue
            close = _match_brace(clean, j)
            low = prelude.lower()
            if low.startswith(("@media", "@supports", "@container", "@layer", "@scope", "@document")):
                c2 = ctx + [norm_sel(prelude)]
                regs.append({"name": "csswrap:" + "".join(c2) + f"@{base + j}", "kind": "csswrap",
                             "start": base + seg, "end": base + j + 1, "text": css[seg:j + 1],
                             "pieces": [(base + seg, base + j + 1)]})
                inner_end = walk(j + 1, close, c2)
                # closing brace (+ any trailing whitespace inside) belongs to the wrapper
                regs.append({"name": "csswrap:" + "".join(c2) + f"@{base + close}", "kind": "csswrap",
                             "start": base + inner_end, "end": base + close + 1,
                             "text": css[inner_end:close + 1],
                             "pieces": [(base + inner_end, base + close + 1)]})
            elif low.startswith("@"):
                regs.append(_css_reg("css:@at:" + norm_sel(prelude), css, seg, close + 1, base,
                                     always=True, ctx=ctx, prelude=prelude, state=state))
            else:
                nested = "{" in clean[j + 1:close]
                regs.append(_css_reg("css:" + "".join(ctx) + "|" + norm_sel(prelude), css, seg,
                                     close + 1, base, always=nested or not has_class_or_id(prelude),
                                     ctx=ctx, prelude=prelude, state=state, sel=prelude))
            seg = i = close + 1
        return seg

    end = walk(0, len(clean), [])
    return regs, end


def _css_reg(name, css, a, b, base, always, ctx, prelude, state, sel=None):
    text = css[a:b]
    h = sha(text + "\0prev:" + state["prev"])
    state["prev"] = name
    r = {"name": name, "kind": "css", "start": base + a, "end": base + b, "text": text,
         "hash": h, "always": always, "ctx": "".join(ctx)}
    if sel is not None:
        r["key"] = "".join(ctx) + "|" + norm_sel(sel)
        r["tokens"] = sel_tokens(sel)
    return r


# --------------------------------------------------------------------------
# Markup
# --------------------------------------------------------------------------
class _BodyParser(html.parser.HTMLParser):
    def __init__(self, text, base):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.base = base
        self.lines = [0]
        for m in re.finditer("\n", text):
            self.lines.append(m.end())
        self.stack = []       # [tag, start, id, is_body_child_index]
        self.elems = []       # finished: dict(tag,id,start,end,depth,bodyidx)
        self.body_ord = {}
        self.in_body = False

    def off(self):
        ln, col = self.getpos()
        return self.lines[ln - 1] + col

    def _open(self, tag, attrs, selfclose):
        if tag == "body":
            self.in_body = True
            return
        if not self.in_body:
            return
        start = self.off()
        d = dict(attrs)
        depth = len(self.stack)
        bidx = None
        if depth == 0 and not d.get("id") and tag not in ("script", "style"):
            # ordinal among <body>'s id-less children of the same tag
            bidx = self.body_ord.get(tag, 0)
            self.body_ord[tag] = bidx + 1
        rec = {"tag": tag, "id": d.get("id"), "start": start, "depth": depth, "bodyidx": bidx}
        if selfclose or tag in VOID:
            rec["end"] = self.text.index(">", start) + 1
            self.elems.append(rec)
        else:
            self.stack.append(rec)

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
            return
        if not self.stack:
            return
        if not any(r["tag"] == tag for r in self.stack):
            return
        end = self.text.index(">", self.off()) + 1
        while self.stack:
            r = self.stack.pop()
            r["end"] = end
            self.elems.append(r)
            if r["tag"] == tag:
                break


def markup_regions(text, base, skip_ids):
    p = _BodyParser(text, base)
    p.feed(text)
    p.close()
    elems = [e for e in p.elems if "end" in e]
    regs = []
    owners = []
    for e in elems:
        if e["id"] in skip_ids or e["tag"] in ("script", "style"):
            continue
        if e["id"]:
            owners.append(e)
        elif e["depth"] == 0:
            owners.append(e)
    owners.sort(key=lambda e: e["start"])
    seen = {}
    for e in owners:
        e["name"] = ("markup:#" + e["id"]) if e["id"] else f"markup:body>{e['tag']}:{e['bodyidx']}"
        k = seen.get(e["name"], 0)
        seen[e["name"]] = k + 1
        if k:
            e["name"] += f"~{k + 1}"
    for e in owners:
        kids = [c for c in owners if c is not e and c["start"] >= e["start"] and c["end"] <= e["end"]]
        # only direct region children (not grandchildren already inside a kid)
        direct = [c for c in kids if not any(o is not c and o["start"] <= c["start"] and c["end"] <= o["end"]
                                             for o in kids)]
        pieces, cur, parts = [], e["start"], []
        for c in sorted(direct, key=lambda c: c["start"]):
            pieces.append((base + cur, base + c["start"]))
            parts.append(text[cur:c["start"]] + "<" + c["name"] + ">")
            cur = c["end"]
        pieces.append((base + cur, base + e["end"]))
        parts.append(text[cur:e["end"]])
        regs.append({"name": e["name"], "kind": "markup", "start": base + e["start"], "end": base + e["end"],
                     "text": "".join(parts), "pieces": pieces, "id": e["id"], "tag": e["tag"],
                     "bodyidx": e["bodyidx"]})
    return regs


# --------------------------------------------------------------------------
# Whole file
# --------------------------------------------------------------------------
def _element_span(html, ident, tag):
    m = re.search(r'<%s id="%s"[^>]*>' % (tag, re.escape(ident)), html)
    if not m:
        return None
    close = html.index("</%s>" % tag, m.end())
    return m.start(), m.end(), close, close + len("</%s>" % tag)


def split(html):
    regs = []
    # vendor
    vendor_spans = {}
    for vid in VENDOR_IDS:
        tag = "style" if vid.endswith("-css") else "script"
        sp = _element_span(html, vid, tag)
        if sp:
            vendor_spans[vid] = sp
            regs.append({"name": "vendor:" + vid, "kind": "vendor", "start": sp[0], "end": sp[3],
                         "text": html[sp[0]:sp[3]]})
    # app script
    sp = _element_span(html, "app-script", "script")
    if not sp:
        raise SystemExit('regions: <script id="app-script"> not found')
    js = js_regions(html[sp[1]:sp[2]], sp[1])
    regs += js
    # main style: the first <style> with no id
    m = re.search(r"<style>", html)
    if not m:
        raise SystemExit("regions: main <style> not found")
    s_end = html.index("</style>", m.end())
    css, _ = css_regions(html[m.end():s_end], m.end())
    regs += css
    # markup
    b0 = html.index("<body", html.index("</head>"))
    b1 = html.rindex("</body>") + len("</body>")
    regs += markup_regions(html[b0:b1], b0, set(VENDOR_IDS) | {"app-script"})

    # names unique (js and css)
    seen = {}
    for r in regs:
        k = seen.get(r["name"], 0)
        seen[r["name"]] = k + 1
        if k:
            r["name"] += f"~{k + 1}"
            r["dup"] = True

    # rest: every byte not covered by a region's own pieces
    covered = bytearray(len(html))
    for r in regs:
        for a, b in r.get("pieces", [(r["start"], r["end"])]):
            covered[a:b] = b"\x01" * (b - a)
    rest = []
    i = 0
    n = len(html)
    while i < n:
        if not covered[i]:
            j = i
            while j < n and not covered[j]:
                j += 1
            rest.append(html[i:j])
            i = j
        else:
            i += 1
    regs.append({"name": "rest", "kind": "rest", "start": 0, "end": n, "text": "\x00".join(rest)})
    for r in regs:
        if "hash" not in r:
            r["hash"] = sha(r["text"])
    return regs


def region_map(html):
    """{name: hash} plus the region records keyed by name."""
    regs = split(html)
    return {r["name"]: r for r in regs}


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", nargs="?", default="regions", choices=["regions"])
    ap.add_argument("--file", default=str(APP))
    ap.add_argument("--list", action="store_true", help="print every region name and hash")
    a = ap.parse_args(argv)
    html = pathlib.Path(a.file).read_text(encoding="utf-8")
    regs = split(html)
    counts = {}
    for r in regs:
        k = r["kind"] + ("/fn" if r.get("fn") else "") + ("/always" if r.get("always") else "")
        counts[k] = counts.get(k, 0) + 1
    if a.list:
        for r in regs:
            print(f"{r['hash']}  {r['name']}")
    for k in sorted(counts):
        print(f"{counts[k]:6d}  {k}")
    print(f"{len(regs):6d}  total")
    dups = [r["name"] for r in regs if r.get("dup")]
    if dups:
        print("duplicate names (suffixed ~N):", ", ".join(dups[:20]), "..." if len(dups) > 20 else "")


if __name__ == "__main__":
    main(sys.argv[1:])
