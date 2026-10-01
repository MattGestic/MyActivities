#!/usr/bin/env python3
"""Extract the P73 embedded baseline into a test fixture (P74, TD-239).

Up to v3.1.0-P73 the app shipped with a client schedule baked into its script
(SEED_TASKS, SEED_MILESTONES, DEP_DATA, the timeline and the report meta). P74
removed it: the app now opens empty. The check suite was written against that
data, so it is kept here as the repo's own test data and seeded into the app
before boot through the documented hook (window.__SRET_FIXTURE__, see
docs/04-architecture.md, P74) by tools/check_map/chrome_fixture.py.

This script is the only way the fixture is produced. It reads the P73 file out
of git, never a hand-edited copy, evaluates each literal with Node (they are JS
object literals, not JSON), and writes eskay-p73.json beside itself.

    python3 tools/fixtures/baseline/extract_p73.py [--rev e24d02a] [--check]

--check exits 1 if the committed fixture differs from a fresh extraction.
"""
import argparse
import html
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
APP_REL = "Projects/P6-Milestone-Dashboard/src/milestone-dashboard.html"
OUT = HERE / "eskay-p73.json"


def git_show(rev):
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout.strip()
    return subprocess.run(["git", "show", f"{rev}:{APP_REL}"], cwd=top, capture_output=True,
                          check=True).stdout.decode("utf-8")


def literal(src, decl, opener, closer):
    """The text of a JS literal: from the opener after `decl` to its balanced closer."""
    i = src.index(decl)
    s = src.index(opener, i + len(decl) - 1)
    depth, q, j = 0, None, s
    while j < len(src):
        c = src[j]
        if q:
            if c == "\\":
                j += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return src[s:j + 1]
        j += 1
    raise ValueError("unbalanced literal after " + decl)


def node_eval(js_literals):
    """{name: js literal text} -> {name: value}, evaluated by Node."""
    body = "const out={};\n" + "".join(f"out[{json.dumps(k)}]=({v});\n" for k, v in js_literals.items()) + \
        "process.stdout.write(JSON.stringify(out));"
    r = subprocess.run(["node", "-e", body], capture_output=True, check=True)
    return json.loads(r.stdout.decode("utf-8"))


def one(src, pattern, what):
    m = re.search(pattern, src, re.S)
    if not m:
        sys.exit(f"extract_p73: {what} not found")
    return m.group(1)


def extract(rev):
    src = git_show(rev)
    app = src[src.index('<script id="app-script">'):]
    lits = {
        "tasks": literal(app, "const SEED_TASKS=", "[", "]"),
        "milestones": literal(app, "const SEED_MILESTONES=", "[", "]"),
        "depData": literal(app, "const DEP_DATA=", "{", "}"),
        "labels": literal(app, "let WE_LABELS=", "[", "]"),
        "months": literal(app, "let MONTHS=", "[", "]"),
        "baselineSource": literal(app, "const BASELINE_SOURCE=", "{", "}"),
    }
    # The one non-literal in BASELINE_SOURCE is its data date.
    lits["baselineSource"] = lits["baselineSource"].replace("new Date(2026,7,15)", "'2026-08-15'")
    v = node_eval(lits)
    # WE_DATES was derived from the labels in the P73 script: May..Dec are 2026,
    # Jan..Apr 2027. Stored explicitly so the fixture does not carry that rule.
    mi = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    dates = []
    for lbl in v["labels"]:
        d, m = lbl.split("-")
        y = 2026 if mi[m] >= 4 else 2027
        dates.append(f"{y}-{mi[m] + 1:02d}-{int(d):02d}")
    now_col = int(one(app, r"const SEED_TIMELINE=\{[^}]*nowCol:(\d+)\}", "SEED_TIMELINE nowCol"))
    heading = one(src, r'<span class="title" id="rpt-title-text"[^>]*>(.*?)</span>', "heading markup")
    bs = v["baselineSource"]
    meta = {
        "title": html.unescape(heading),
        "documentTitle": html.unescape(one(src, r"<title>(.*?)</title>", "<title>")),
        "projectNo": one(app, r"const SEED_PROJECT_NO='([^']*)'", "SEED_PROJECT_NO"),
        "sourceName": one(app, r"const BASELINE_SOURCE_NAME='([^']*)'", "BASELINE_SOURCE_NAME"),
        "baselineLabel": one(app, r"let BASELINE_LABEL_TEXT='([^']*)'", "BASELINE_LABEL_TEXT"),
        "sourceLabel": bs["label"],
        "dataDate": bs["dataDate"],
        "file": bs["file"],
        "updatedBy": one(app, r"const REPORT_UPDATED_BY='([^']*)'", "REPORT_UPDATED_BY"),
    }
    return {
        "kind": "sret-preboot-fixture",
        "schemaVersion": 1,
        "extractedFrom": {"rev": rev, "file": APP_REL,
                          "version": one(app, r"const APP_VERSION='([^']*)'", "APP_VERSION")},
        "meta": meta,
        "timeline": {"labels": v["labels"], "dates": dates, "months": v["months"], "nowCol": now_col},
        "tasks": v["tasks"],
        "milestones": v["milestones"],
        "depData": v["depData"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default="e24d02a")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    fx = extract(a.rev)
    text = json.dumps(fx, ensure_ascii=False, indent=1) + "\n"
    if a.check:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("fixture matches a fresh extraction" if same else "fixture DIFFERS from a fresh extraction")
        return 0 if same else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(fx['tasks'])} tasks, {len(fx['milestones'])} milestones, "
          f"{len(fx['depData'])} dependency records, {len(fx['timeline']['labels'])} weeks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
