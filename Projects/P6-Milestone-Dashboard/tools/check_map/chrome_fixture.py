#!/usr/bin/env python3
"""Fixture-seeding stand-in for headless Chromium (P74, TD-239).

Since v3.1.0-P74 the app ships with no schedule and opens on its empty state.
The check suite was written against the baseline P73 embedded, which now lives
in tools/fixtures/baseline/eskay-p73.json. This wrapper puts it back, through
the app's own pre-boot hook, so the checks need no per-check edits:

  1. every check's find_chrome() (tools/import_check.py and the local copies)
     returns THIS file, with or without SRET_CHROME set, so `python3
     tools/x.py` standalone goes through it as well as a run_checks.py run;
  2. for the file:// page on the command line it decides whether to seed:
       - the page is the CURRENT app: it carries <script id="app-script"> and
         the same APP_VERSION as src/milestone-dashboard.html (a releases/
         snapshot is another version and carries its own data);
       - the page carries no data of its own: no published state block
         (`window.__PUBLISHED_STATE__={`) and no dataset already given to the
         hook (`window.__SRET_FIXTURE__={`);
       - the check has not opted out: no `sret:no-fixture` marker anywhere in
         the page (a check that tests the empty app writes it into its probe),
         and SRET_NO_FIXTURE is not set in the environment;
  3. if so, writes `<script id="sret-fixture">window.__SRET_FIXTURE__=...;
     </script>` immediately before the app script, into the check's temp
     page (or, for a page inside the repo, into a temp copy whose URL replaces
     the argument, so a tracked file is never written);
  4. hands the launch on, unchanged otherwise, to $SRET_CHROME when that is set
     and is not this file (tools/check_map/chrome_cov.py, the coverage
     wrapper, which then instruments the seeded page), else to the real
     Chromium. Exit code and stdout pass straight through (exec).

Every launch is handled, --dump-dom or --screenshot alike.

    SRET_FIXTURE=<path>   seed a different fixture file
    SRET_NO_FIXTURE=1     seed nothing (the empty app)
"""
import json
import os
import pathlib
import re
import sys
import tempfile
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP = ROOT / "src" / "milestone-dashboard.html"
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "baseline" / "eskay-p73.json"
OPT_OUT_MARKER = "sret:no-fixture"
APP_TAG = '<script id="app-script">'
VERSION_RE = re.compile(r"const APP_VERSION\s*=\s*['\"]([^'\"]+)")
PUBLISHED_RE = re.compile(r"window\.__PUBLISHED_STATE__\s*=\s*\{")
SEEDED_RE = re.compile(r"window\.__SRET_FIXTURE__\s*=\s*\{")
REAL_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome",
]


def launcher():
    """What every find_chrome() returns: this file, which is executable."""
    return str(pathlib.Path(__file__).resolve())


def next_chrome():
    env = os.environ.get("SRET_CHROME")
    if env and pathlib.Path(env).resolve() != pathlib.Path(__file__).resolve():
        return env
    real = os.environ.get("SRET_CHROME_REAL")
    if real:
        return real
    for c in REAL_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    for c in sorted(pathlib.Path("/opt/pw-browsers").glob("chromium_headless_shell-*/chrome-linux/headless_shell")):
        return str(c)
    sys.exit("chrome_fixture: no headless Chromium found")


def current_version():
    try:
        m = VERSION_RE.search(APP.read_text(encoding="utf-8"))
        return m.group(1) if m else None
    except OSError:
        return None


def wants_fixture(page):
    """The reason it will not seed, or None when it will."""
    if os.environ.get("SRET_NO_FIXTURE"):
        return "SRET_NO_FIXTURE set"
    if APP_TAG not in page:
        return "not the app"
    m = VERSION_RE.search(page)
    cur = current_version()
    if not m or (cur and m.group(1) != cur):
        return "another version of the app"
    # The app's own source spells both names (it writes one and reads the
    # other), so only an ASSIGNMENT of an object counts as data.
    if PUBLISHED_RE.search(page):
        return "carries a published state block"
    if SEEDED_RE.search(page):
        return "already seeded"
    if OPT_OUT_MARKER in page:
        return "opted out"
    return None


def fixture_script():
    path = pathlib.Path(os.environ.get("SRET_FIXTURE") or DEFAULT_FIXTURE)
    data = json.loads(path.read_text(encoding="utf-8"))
    # Nothing in the data may end the script element early.
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return '<script id="sret-fixture">window.__SRET_FIXTURE__=' + text + ";</script>\n"


def inject(page):
    """The page with the fixture in front of the app script."""
    i = page.index(APP_TAG)
    return page[:i] + fixture_script() + page[i:]


def main():
    args = sys.argv[1:]
    idx = next((i for i, a in enumerate(args) if a.startswith("file://")), None)
    if idx is not None:
        url = urllib.parse.urlparse(args[idx])
        path = pathlib.Path(urllib.parse.unquote(url.path))
        try:
            page = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
        except OSError:
            page = None
        if page is not None and wants_fixture(page) is None:
            seeded = inject(page)
            try:
                inside_repo = path.resolve().is_relative_to(ROOT)
            except AttributeError:   # Python < 3.9
                inside_repo = str(path.resolve()).startswith(str(ROOT) + os.sep)
            if inside_repo:
                d = tempfile.mkdtemp(prefix="sret-fixture-")
                path = pathlib.Path(d) / path.name
                args[idx] = urllib.parse.urlunparse(url._replace(path=urllib.parse.quote(str(path))))
            path.write_text(seeded, encoding="utf-8")
    nxt = next_chrome()
    os.execv(nxt, [nxt] + args)


if __name__ == "__main__":
    main()
