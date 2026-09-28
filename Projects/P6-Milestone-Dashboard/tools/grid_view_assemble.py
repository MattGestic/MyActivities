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


def _shift(iso_d, n):
    if not iso_d:
        return iso_d
    import datetime
    d = datetime.date.fromisoformat(iso_d) + datetime.timedelta(days=n)
    return d.isoformat()


def comparison_snapshots(sched):
    def row(r, **kw):
        x = {"id": r["id"], "name": r["name"], "start": r["start"], "finish": r["finish"], "float": r["float"], "actual": r["actual"]}
        x.update(kw)
        return x
    prev, interim, base = [], [], []
    for i, r in enumerate(sched):
        if i % 31 == 5:                      # new since the previous update
            continue
        p = row(r)
        if i % 9 == 0:
            p["finish"] = _shift(r["finish"], -7)      # now 7 days later
        elif i % 13 == 0:
            p["finish"] = _shift(r["finish"], 3)       # now 3 days earlier
        elif i % 17 == 0 and r["float"] is not None:
            p["float"] = r["float"] + 5                # float only
        if r["actual"] == "Yes" and i % 4 == 0:
            p["actual"] = "No"                         # completed since
        prev.append(p)
        q = row(r)
        if i % 9 == 0:
            q["finish"] = _shift(r["finish"], -3)
        interim.append(q)
        b = row(r)
        if i % 5 == 0:
            b["finish"] = _shift(r["finish"], -14)
        base.append(b)
    prev += [{"id": "SNIP-901", "name": "Superseded interface review", "start": "2026-09-07", "finish": "2026-09-18", "float": 4, "actual": "No"},
             {"id": "SNIP-902", "name": "Deleted duplicate survey task", "start": "2026-09-14", "finish": "2026-09-16", "float": 10, "actual": "No"}]
    names = ["Shop drawings issued", "Shop drawings approved", "Material order placed", "Mill certificates received",
             "Fabrication start, grid A", "Fabrication complete, grid A", "Fabrication start, grid B", "Fabrication complete, grid B",
             "Blast and paint", "Trial assembly", "Inspection and test", "Load-out", "Sea freight", "Arrive at port",
             "Road transport to site", "Delivered to laydown"]
    v1, v2 = [], []
    for i, n in enumerate(names):
        st = _shift("2026-09-01", i * 7)
        fi = _shift(st, 6)
        v1.append({"id": "OS-%d" % (100 + i * 10), "name": n, "start": st, "finish": fi, "float": 10 - (i % 5), "actual": "Yes" if i < 2 else "No"})
        slip = 0 if i < 3 else (5 if i < 9 else 9)
        v2.append({"id": "OS-%d" % (100 + i * 10), "name": n, "start": _shift(st, slip if i >= 4 else 0), "finish": _shift(fi, slip),
                   "float": 10 - (i % 5) - (2 if i >= 9 else 0), "actual": "Yes" if i < 3 else "No"})
    # Loaded in this order (Matt, 2026-09-28: three per schedule plus the
    # embedded baseline). The demo then imports the live 29-Aug update as the
    # latest, so 22-Aug becomes the comparison and 15-Aug is dropped.
    proj = "P:\\103787 SRET\\05 Controls\\Schedule\\Weekly updates"
    vend = "P:\\103787 SRET\\07 Procurement\\P8010 Ocean Steel\\Schedules"
    # Interim update of part of the schedule only (Matt, 2026-09-28): the cost
    # estimate band, cut after the latest full update, with moves and one
    # activity the full schedule does not have yet.
    part = []
    for k, r in enumerate([r for r in sched if r["wbs"] == "Capital and Operating Cost Estimate"]):
        x = row(r)
        if k % 3 == 0:
            x["finish"] = _shift(r["finish"], 5)
        part.append(x)
    part.append({"id": "SNIP-950", "name": "Estimate peer review", "start": "2026-10-05", "finish": "2026-10-09", "float": 6, "actual": "No"})
    return [
        {"slot": "interim", "meta": {"id": "pi-0902", "role": "project", "dataDate": "2026-09-02", "scope": "Cost estimate",
                                     "file": "PFS interim, cost estimate only DD-2026-09-02.xlsx", "path": proj + "\\Interim",
                                     "snapshotAt": "2026-09-03T10:00:00Z"}, "rows": part},
        {"slot": "baseline", "meta": {"id": "bl", "role": "project", "dataDate": "2026-08-15", "file": "Embedded baseline",
                                      "path": "(inside this file)", "snapshotAt": "2026-08-18T08:00:00Z"}, "rows": base},
        {"slot": "latest", "meta": {"id": "pu-0815", "role": "project", "dataDate": "2026-08-15", "file": "103787-13_PFS_Weekly_Update_DD-2026-08-15.xlsx",
                                    "path": proj, "snapshotAt": "2026-08-18T08:05:00Z"}, "rows": base},
        {"slot": "latest", "meta": {"id": "pu-0822", "role": "project", "dataDate": "2026-08-22", "file": "103787-13_PFS_Weekly_Update_DD-2026-08-22.xlsx",
                                    "path": proj, "snapshotAt": "2026-08-24T08:00:00Z"}, "rows": prev},
        {"slot": "alternate", "meta": {"id": "pa-0826", "role": "project", "dataDate": "2026-08-26", "file": "PFS recovery option DD-2026-08-26.xlsx",
                                       "path": proj + "\\Options", "snapshotAt": "2026-08-26T15:00:00Z"}, "rows": interim},
        {"slot": "latest", "meta": {"id": "os-0820", "role": "external", "name": "Ocean Steel fabrication", "dataDate": "2026-08-20",
                                    "file": "OceanSteel_P8010_2026-08-20.xlsx", "path": vend, "snapshotAt": "2026-08-21T09:00:00Z"}, "rows": v1},
        {"slot": "latest", "meta": {"id": "os-0827", "role": "external", "name": "Ocean Steel fabrication", "dataDate": "2026-08-27",
                                    "file": "OceanSteel_P8010_2026-08-27.xlsx", "path": vend, "snapshotAt": "2026-08-28T09:00:00Z"}, "rows": v2},
    ]


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
                       "finish": d.isoformat(), "band": "User Defined Milestones", "wbs": a["wbs"],
                       "pred": a["id"], "succ": b["id"] if i % 2 else "",
                       "progress": [0, 25, 50, 75, 100][i % 5],
                       "comment": "" if i % 3 else "Added at the weekly review.",
                       "created": (datetime.date(2026, 9, 1) + datetime.timedelta(days=i)).isoformat(),
                       "createdBy": ["MG", "JR", "AK"][i % 3], "health": [1, 2, 3, 4, 0][i % 5]})
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
            # ID carries the health icon (tap to change, as the dashboard); Health itself is a
            # hidden column so it exports last and appears last in the import template.
            {"key": "id", "label": "ID", "type": "text", "width": 104,
             "icon": {"key": "health", "label": "Health", "options": health}},
            {"key": "name", "label": "Name", "type": "text", "editable": True, "width": 240},
            {"key": "type", "label": "Type", "type": "select", "editable": True, "options": types, "width": 70},
            {"key": "start", "label": "Start", "type": "date", "editable": True},
            {"key": "finish", "label": "Finish", "type": "date", "editable": True},
            {"key": "band", "label": "Band", "type": "text", "editable": True, "width": 170},
            {"key": "wbs", "label": "WBS", "type": "text", "editable": True, "width": 150},
            {"key": "state", "label": "Status", "type": "select", "editable": True, "options": state,
             "tones": {"FUTURE": "future", "TRACK": "track", "RISK": "risk", "CRIT": "crit", "DONEUSER": "done"}},
            {"key": "pred", "label": "Predecessor", "type": "text", "editable": True, "width": 110},
            {"key": "succ", "label": "Successor", "type": "text", "editable": True, "width": 110},
            {"key": "progress", "label": "% complete", "type": "number", "editable": True, "width": 90, "min": 0, "max": 100},
            {"key": "comment", "label": "Comment", "type": "text", "editable": True, "width": 220},
            {"key": "created", "label": "Date created", "type": "date", "width": 100},
            {"key": "createdBy", "label": "Created by", "type": "text", "width": 90},
            {"key": "health", "label": "Health", "type": "select", "editable": True, "options": health, "hidden": True},
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
    # Schedule changes (Matt, 2026-09-28): earlier imports kept as snapshots.
    # Synthetic, derived from the reference export so the demo has something to
    # compare: a baseline, the previous formal update, an interim cut, and a
    # vendor schedule imported twice. The current project update is `sched`.
    snaps = comparison_snapshots(sched)
    # The file as shared: last saved by someone else, with its save history.
    file_state = {"savedBy": "J. Ruiz", "history": [
        {"at": "2026-09-14T08:05:00Z", "by": "M. Garrett", "version": "3.1.0-P57"},
        {"at": "2026-09-20T09:12:00Z", "by": "J. Ruiz", "version": "3.1.0-P58"}]}
    data = {"sched": sched, "userms": userms, "annot": annot, "cols": cols, "fileState": file_state, "snaps": snaps}
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
        "/*@USER_CSS@*/": (ROOT / "src" / "modules" / "user" / "user.css").read_text(encoding="utf-8"),
        "/*@VENDOR_CSS@*/": safe_inline(vendor_css, "</style", "vendor CSS"),
        "/*@VENDOR_JS@*/": safe_inline(vendor_js, "</script", "vendor JS"),
        "/*@GRID_JS@*/": safe_inline((MOD / "grid-view.js").read_text(encoding="utf-8"), "</script", "grid-view.js"),
        "/*@COLLECTIONS_JS@*/": safe_inline((COLL / "collections.js").read_text(encoding="utf-8"), "</script", "collections.js"),
        "/*@DATES_JS@*/": safe_inline((ROOT / "src" / "modules" / "dates" / "dates.js").read_text(encoding="utf-8"), "</script", "dates.js"),
        "/*@USER_JS@*/": safe_inline((ROOT / "src" / "modules" / "user" / "user.js").read_text(encoding="utf-8"), "</script", "user.js"),
        "/*@COMPARE_JS@*/": safe_inline((ROOT / "src" / "modules" / "compare" / "compare.js").read_text(encoding="utf-8"), "</script", "compare.js"),
        "/*@MSIMPORT_JS@*/": safe_inline((ROOT / "src" / "modules" / "ms-import" / "ms-import.js").read_text(encoding="utf-8"), "</script", "ms-import.js"),
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
