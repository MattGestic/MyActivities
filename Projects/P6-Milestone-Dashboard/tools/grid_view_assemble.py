#!/usr/bin/env python3
"""
Assembles prototypes/grid-view/demo.html (D-09 grid view prototype).

The demo has to be one self-contained page, the same shape as the app, so it
inlines: the app's token blocks (copied, read-only, from
src/milestone-dashboard.html), the grid module CSS and JS, the vendored
SlickGrid subset, and fixtures built from the committed reference P6 export.
Keeping those as separate source files and inlining them here means there is
one copy of each to edit. This is a dev-time helper for the prototype only;
the app itself stays a hand-edited single file (docs/grid-view-integration.md
describes the manual paste for the merge).

Usage:
  python3 tools/grid_view_assemble.py           # write demo.html
  python3 tools/grid_view_assemble.py --check   # exit 1 if demo.html is stale
"""

import argparse
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import import_check  # noqa: E402  (reuses its dependency-free .xlsx reader)

APP = ROOT / "src" / "milestone-dashboard.html"
MOD = ROOT / "src" / "modules" / "grid-view"
COLL = ROOT / "src" / "modules" / "collections"
VENDOR = ROOT / "vendor" / "slickgrid"
PROTO = ROOT / "prototypes" / "grid-view"
XLSX = ROOT / "data" / "schedules" / "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def token_blocks() -> str:
    """The app's tier 1 palette blocks, the tier 2 :root, and the D-16
    coarse-pointer switch: from the first html[data-theme] rule to the end of
    the @media (pointer:coarse) block that follows :root."""
    html = APP.read_text(encoding="utf-8")
    style = re.search(r"<style[^>]*>(.*?)</style>", html, re.S).group(1)
    start = style.index('html[data-theme="light"]{')
    m = re.search(r"@media \(pointer:coarse\)\{\s*:root\{[^}]*\}\s*\}", style[start:])
    if not m:
        sys.exit("Could not find the coarse-pointer token block in the app file.")
    block = style[start:start + m.end()]
    return ("/* Copied from src/milestone-dashboard.html by tools/grid_view_assemble.py.\n"
            "   Do not edit here: edit the app's palette and re-assemble. */\n" + block +
            "\nhtml[data-theme=\"light\"]{color-scheme:light}\nhtml[data-theme=\"dark\"]{color-scheme:dark}\n"
            ":root{accent-color:var(--color-accent)}\n*{box-sizing:border-box;margin:0;padding:0}")


def iso(s: str):
    s = (s or "").strip().rstrip("A").rstrip("*").strip()
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{2})$", s)
    if not m:
        return None
    return f"20{m.group(3)}-{MONTHS.index(m.group(2).title()) + 1:02d}-{int(m.group(1)):02d}"


def num(s):
    try:
        return float(s) if "." in str(s) else int(s)
    except (TypeError, ValueError):
        return None


def schedule_rows():
    aoa = import_check.build_aoa(XLSX)
    rows, stack = [], []
    for r in aoa[1:]:
        raw_id = str(r[0])
        level = (len(raw_id) - len(raw_id.lstrip(" "))) // 2
        rid = raw_id.strip()
        if not rid:
            continue
        if not str(r[1]).strip():          # WBS heading
            stack = stack[:level] + [rid]
            continue
        band = stack[-1] if stack else ""
        rows.append({
            "id": rid, "name": str(r[1]).strip(), "wbs": band, "dur": num(r[2]),
            "start": iso(r[3]), "finish": iso(r[4]), "float": num(r[7]),
            "pred": str(r[5]).strip(), "succ": str(r[6]).strip(),
            "actual": "Yes" if (str(r[3]).strip().endswith("A") or str(r[4]).strip().endswith("A")) else "No",
            "short": "", "health": None, "comment": "",
        })
    return rows


def fixtures():
    sched = schedule_rows()
    # A few annotation values already present, as a mounted annotation file would give.
    for i, r in enumerate(sched[:40]):
        if i % 7 == 0:
            r["health"] = [1, 2, 3][i % 3]
        if i % 11 == 0:
            r["comment"] = "Confirm date with the owner's team at the weekly review."
    ms = [r for r in sched if r["dur"] == 0][:12] or sched[:12]
    types = ["MS", "INT", "CLI", "RTN"]
    states = ["FUTURE", "TRACK", "RISK", "CRIT", "DONEUSER"]
    names = ["Client review of draft PFS", "Owner sign-off on design criteria", "Vendor quote round 2 closed",
             "Geotech report issued for review", "Permitting pre-application meeting", "Cost estimate basis frozen",
             "Execution plan workshop", "Water balance model accepted", "Power supply study received",
             "Risk register refreshed", "Board paper lodged", "Final PFS issued"]
    userms = []
    for i, name in enumerate(names):
        a = ms[i % len(ms)]
        b = ms[(i + 1) % len(ms)]
        fin = a["finish"] or a["start"] or "2026-10-30"
        d = datetime.date.fromisoformat(fin) + datetime.timedelta(days=7 * (i % 4))
        userms.append({"id": f"USR-{i + 1:03d}", "name": name, "type": types[i % 4], "state": states[i % 5],
                       "start": None if i % 3 else (d - datetime.timedelta(days=14)).isoformat(),
                       "finish": d.isoformat(), "band": "User Defined Milestones",
                       "pred": a["id"], "succ": b["id"] if i % 2 else "",
                       "progress": [0, 25, 50, 75, 100][i % 5],
                       "comment": "" if i % 3 else "Added at the weekly review."})
    kinds = [("Milestone comment", "comment"), ("Row remark", "remark"), ("Dependency comment", "dep"),
             ("Note", "note"), ("Health override", "health"), ("Progress override", "progress"),
             ("Date override", "date")]
    note_status = ["open", "sent", "review", "outstanding", "done", "note", "closed"]
    annot = []
    for i in range(28):
        k, code = kinds[i % len(kinds)]
        t = sched[(i * 5) % len(sched)]
        if code == "health":
            val = ["On track", "At risk", "Critical"][i % 3]
        elif code == "progress":
            val = str([10, 40, 65, 90][i % 4]) + "%"
        elif code == "date":
            val = (datetime.date(2026, 10, 2) + datetime.timedelta(days=i)).isoformat()
        elif code == "dep":
            val = f"Logic to {sched[(i * 5 + 1) % len(sched)]['id']} needs checking, lag looks short."
        else:
            val = ["Awaiting vendor data.", "Moved per client request.", "Check against the baseline.",
                   "Raised at the coordination meeting."][i % 4]
        annot.append({"aid": f"A-{i + 1:03d}", "kind": k, "target": t["id"], "targetName": t["name"],
                      "value": val, "status": note_status[i % len(note_status)],
                      "author": ["MG", "JR", "AK"][i % 3],
                      "date": (datetime.date(2026, 9, 21) + datetime.timedelta(days=i % 7)).isoformat()})
    health = [{"value": 0, "label": "N/A"}, {"value": 1, "label": "On track"}, {"value": 2, "label": "At risk"},
              {"value": 3, "label": "Critical"}, {"value": 4, "label": "Done"}]
    state = [{"value": "FUTURE", "label": "Future"}, {"value": "TRACK", "label": "On track"},
             {"value": "RISK", "label": "At risk"}, {"value": "CRIT", "label": "Critical"},
             {"value": "DONEUSER", "label": "Done"}]
    nstat = [{"value": "note", "label": "Note"}, {"value": "open", "label": "Open"}, {"value": "sent", "label": "Sent"},
             {"value": "review", "label": "In review"}, {"value": "outstanding", "label": "Outstanding"},
             {"value": "done", "label": "Done"}, {"value": "closed", "label": "Closed"}]
    cols = {
        "userms": [
            {"key": "id", "label": "ID", "type": "text", "width": 90},
            {"key": "name", "label": "Name", "type": "text", "editable": True, "width": 240},
            {"key": "type", "label": "Type", "type": "select", "editable": True, "options": types, "width": 70},
            {"key": "start", "label": "Start", "type": "date", "editable": True},
            {"key": "finish", "label": "Finish", "type": "date", "editable": True},
            {"key": "band", "label": "Band / WBS", "type": "text", "editable": True, "width": 170},
            {"key": "state", "label": "Status", "type": "select", "editable": True, "options": state},
            {"key": "pred", "label": "Predecessor", "type": "text", "editable": True, "width": 100},
            {"key": "succ", "label": "Successor", "type": "text", "editable": True, "width": 100},
            {"key": "progress", "label": "% complete", "type": "number", "editable": True, "width": 90},
            {"key": "comment", "label": "Comment", "type": "text", "editable": True, "width": 220},
        ],
        "annot": [
            {"key": "aid", "label": "Entry", "type": "text", "width": 70},
            {"key": "kind", "label": "Kind", "type": "text", "width": 140},
            {"key": "target", "label": "Activity ID", "type": "text", "width": 100},
            {"key": "targetName", "label": "Activity name", "type": "text", "width": 220},
            {"key": "value", "label": "Comment or value", "type": "text", "editable": True, "width": 280},
            {"key": "status", "label": "Status", "type": "select", "editable": True, "options": nstat},
            {"key": "author", "label": "By", "type": "text", "width": 50},
            {"key": "date", "label": "Entered", "type": "date"},
        ],
        "sched": [
            {"key": "id", "label": "Activity ID", "type": "text", "width": 100},
            {"key": "name", "label": "Activity name", "type": "text", "width": 260},
            {"key": "wbs", "label": "WBS", "type": "text", "width": 160},
            {"key": "dur", "label": "Duration", "type": "number", "width": 72},
            {"key": "start", "label": "Start", "type": "date"},
            {"key": "finish", "label": "Finish", "type": "date"},
            {"key": "actual", "label": "Actual", "type": "text", "width": 60},
            {"key": "float", "label": "Total float", "type": "number", "width": 80},
            {"key": "pred", "label": "Predecessors", "type": "text", "width": 160},
            {"key": "succ", "label": "Successors", "type": "text", "width": 160},
            {"key": "short", "label": "Short title", "type": "text", "editable": True, "width": 140},
            {"key": "health", "label": "Health", "type": "select", "editable": True, "options": health, "width": 90},
            {"key": "comment", "label": "Comment", "type": "text", "editable": True, "width": 220},
        ],
    }
    data = {"sched": sched, "userms": userms, "annot": annot, "cols": cols}
    js = "window.SRET_FIXTURES=" + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";\n"
    js += ("// Stress set: the reference schedule repeated to n rows with unique IDs.\n"
           "window.SRET_STRESS=function(n){var s=window.SRET_FIXTURES.sched,out=[];"
           "for(var i=0;i<n;i++){var r=Object.assign({},s[i%s.length]);"
           "r.id=r.id+'-'+String(Math.floor(i/s.length)+1).padStart(2,'0');out.push(r);}return out;};\n")
    return js


VENDOR_JS_ORDER = ["slick.core.js", "slick.interactions.js", "slick.grid.js", "slick.dataview.js",
                   "slick.checkboxselectcolumn.js", "slick.rowselectionmodel.js"]


def safe_inline(text: str, closer: str, what: str) -> str:
    if closer in text.lower():
        sys.exit(f"{what} contains {closer}, which would end the inline block early.")
    return text


def build() -> str:
    tpl = (PROTO / "demo.template.html").read_text(encoding="utf-8")
    vendor_js = (VENDOR / "slickgrid.subset.min.js").read_text(encoding="utf-8")
    vendor_css = (VENDOR / "dist" / "slick.grid.css").read_text(encoding="utf-8")
    parts = {
        "/*@TOKENS@*/": token_blocks(),
        "/*@GRID_CSS@*/": (MOD / "grid-view.css").read_text(encoding="utf-8"),
        "/*@VENDOR_CSS@*/": safe_inline(vendor_css, "</style", "vendor CSS"),
        "/*@VENDOR_JS@*/": safe_inline(vendor_js, "</script", "vendor JS"),
        "/*@GRID_JS@*/": safe_inline((MOD / "grid-view.js").read_text(encoding="utf-8"), "</script", "grid-view.js"),
        "/*@COLLECTIONS_JS@*/": safe_inline((COLL / "collections.js").read_text(encoding="utf-8"), "</script", "collections.js"),
        "/*@FIXTURES@*/": safe_inline(fixtures(), "</script", "fixtures"),
    }
    for k, v in parts.items():
        if k not in tpl:
            sys.exit(f"Template placeholder {k} missing.")
        tpl = tpl.replace(k, v)
    return tpl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if demo.html differs from a fresh build")
    ap.add_argument("--out", default=str(PROTO / "demo.html"))
    a = ap.parse_args()
    html = build()
    out = pathlib.Path(a.out)
    if a.check:
        cur = out.read_text(encoding="utf-8") if out.exists() else ""
        if cur != html:
            print("STALE: demo.html differs from a fresh assemble. Run tools/grid_view_assemble.py.")
            return 1
        print("demo.html is current.")
        return 0
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)} ({len(html.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
