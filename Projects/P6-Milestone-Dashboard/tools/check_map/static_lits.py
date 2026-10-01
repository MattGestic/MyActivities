"""Static-assertion fingerprint for browser checks.

Most browser checks also assert on the app's source text directly, e.g.
`src.count("positionFixedPopup(") >= 4`, `"top:19.5px" not in src`, or the
version-literal count. Those assertions do not run in the browser, so region
coverage cannot see them. This module covers them from the check's side:

  every string literal of the check script (6+ chars) is counted in the app
  text three ways: verbatim, with all whitespace removed on both sides, and,
  if it looks like a regex, as a regex match count.

The counts are stored per check; when any count changes, the check is
selected. That catches a new occurrence, a removed one, and an absence
assertion being broken, wherever in the file the edit happened. It can over-
select (a literal that a probe uses as a CSS selector also counts), never
under-select for an assertion written as a literal in the script itself.
"""
import ast
import hashlib
import io
import re
import tokenize

MIN = 6
COMMON = 50
REGEX_HINT = re.compile(r"\\[.dswbSWD]|\[[^\]]+\][+*?]|\(\?|\[0-9\]|\.\*|\.\+")
# keep literals that look like code or markup (punctuation, or a camelCase /
# snake_case identifier); plain prose words ("checks", "detail") would select
# the check on unrelated edits
CODEY = re.compile(r"[.#:;(){}\[\]=<>_'\"/$\\]|[a-z][A-Z]")
_cache = {}


def literals(script_text):
    out = set()
    try:
        toks = tokenize.generate_tokens(io.StringIO(script_text).readline)
        for t in toks:
            if t.type != tokenize.STRING:
                continue
            s = t.string
            pre = s[:s.index(s[-1])].lower() if s[-1] in "'\"" else ""
            if "f" in pre or "b" in pre:
                continue
            try:
                v = ast.literal_eval(s)
            except Exception:
                continue
            if isinstance(v, str) and MIN <= len(v) <= 400 and (CODEY.search(v) or (len(v.strip()) >= 12 and " " in v.strip())):
                out.add(v)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return sorted(out)


def _ws(s):
    return re.sub(r"\s+", "", s)


def counts(lits, app_text):
    key = hashlib.sha256(app_text.encode()).hexdigest()
    if key not in _cache:
        _cache.clear()
        _cache[key] = (_ws(app_text), {})
    nows, memo = _cache[key]
    out = {}
    for L in lits:
        if L in memo:
            out[L] = memo[L]
            continue
        c = [app_text.count(L)]
        w = _ws(L)
        c.append(nows.count(w) if len(w) >= MIN else 0)
        if REGEX_HINT.search(L):
            try:
                c.append(len(re.findall(L, app_text)))
            except re.error:
                pass
        v = ",".join(map(str, c))
        memo[L] = v
        out[L] = v
    return out


def fingerprint(script_text, app_text):
    """{short literal hash: counts} for every literal of the script."""
    lits = literals(script_text)
    cs = counts(lits, app_text)
    # a literal found more than COMMON times (a generic regex such as
    # `([A-Z]+)`, a common token) is not an assertion target, and its count
    # would move with almost any edit
    return {hashlib.sha1(L.encode()).hexdigest()[:10]: cs[L] for L in lits
            if max(int(x) for x in cs[L].split(",")) <= COMMON}


def changed(script_text, app_text, stored):
    """Literals whose count differs from the stored fingerprint."""
    lits = literals(script_text)
    cs = counts(lits, app_text)
    out = []
    for L in lits:
        h = hashlib.sha1(L.encode()).hexdigest()[:10]
        if h in stored and stored[h] != cs[L] and max(int(x) for x in stored[h].split(",")) <= COMMON:
            out.append(L)
    return out
