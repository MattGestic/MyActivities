#!/usr/bin/env python3
"""
Ingest check for the P6 Milestone Dashboard (TEST-02 / TD-04).

Drives the application's real import pipeline against a committed reference
P6 export and asserts the EARS acceptance criteria in docs/05-test-log.md.

WHAT IS REAL AND WHAT IS STUBBED
--------------------------------
Real: Parse.workbook header detection, Parse.autoMap, showMapper, runIngest,
normalise, classify, join, aggregate, buildTimeline, parseLooseDate, the
diagnostics panel and the resulting DOM. That is everything the project owns.

Stubbed: SheetJS itself. The app loads it from cdnjs on demand and this
environment's proxy refuses that host, so the library cannot load here. The
stub stands in at exactly the app's boundary with it (XLSX.read plus
XLSX.utils.sheet_to_json) and returns an array-of-arrays built in Python from
the same workbook.

That stub has to be faithful in one specific way. The app calls
sheet_to_json with raw:false, which means SheetJS applies each cell's number
format before the app ever sees the value. Every date cell in the reference
export carries builtin numFmtId 15 (d-mmm-yy), so a stored serial such as
46352 reaches the app as "29-Aug-26", not as a bare number. The AoA built
here reproduces that. Getting this wrong would test a code path the real
import never takes.

Consequence worth knowing: the Excel-serial branch in parseLooseDate is
therefore not reachable through the .xlsx route. It still matters for pasted
or delimited input, where raw numbers do arrive.

AC-01 (the library loads and parses) cannot be tested here and is reported as
NOT TESTED rather than passed. It needs a network-enabled run.

Usage:
  python3 tools/import_check.py [--xlsx FILE] [--html FILE] [--json OUT]
Exit code 1 if any testable criterion fails.
"""

import argparse
import base64
import datetime
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Builtin Excel number formats that render as a date. Only the ones this
# workbook actually uses are listed; an unlisted id falls through as a number,
# which is what SheetJS would also do for a General cell.
DATE_BUILTINS = {14: "%m/%d/%y", 15: "d-mmm-yy", 16: "d-mmm", 17: "mmm-yy", 22: "datetime"}


def serial_to_date(serial: float) -> datetime.date:
    """Excel 1900-system serial to date, accounting for the 1900 leap-year bug."""
    return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(serial))


def fmt_date(d: datetime.date, code: str) -> str:
    if code == "d-mmm-yy":
        return f"{d.day}-{MONTHS[d.month - 1]}-{d.strftime('%y')}"
    if code == "d-mmm":
        return f"{d.day}-{MONTHS[d.month - 1]}"
    if code == "mmm-yy":
        return f"{MONTHS[d.month - 1]}-{d.strftime('%y')}"
    return d.strftime("%m/%d/%y")


def build_aoa(xlsx: pathlib.Path):
    """Array-of-arrays as SheetJS sheet_to_json(header:1, raw:false, defval:'') would produce."""
    z = zipfile.ZipFile(xlsx)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")):
            shared.append("".join(t.text or "" for t in si.iter(NS + "t")))

    styles = ET.fromstring(z.read("xl/styles.xml"))
    custom = {nf.get("numFmtId"): nf.get("formatCode") for nf in styles.iter(NS + "numFmt")}
    cellxfs = [x.get("numFmtId") for x in styles.find(NS + "cellXfs")]

    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    grid, width = [], 0
    for row in sheet.iter(NS + "row"):
        cells = {}
        for c in row:
            ref = c.get("r", "")
            col = re.match(r"([A-Z]+)", ref)
            if not col:
                continue
            idx = 0
            for ch in col.group(1):
                idx = idx * 26 + (ord(ch) - 64)
            idx -= 1
            v = c.find(NS + "v")
            t = c.get("t")
            if v is None or v.text is None:
                val = ""
            elif t == "s":
                val = shared[int(v.text)]
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(NS + "t"))
            else:
                s = c.get("s")
                nid = cellxfs[int(s)] if s is not None and int(s) < len(cellxfs) else "0"
                code = custom.get(nid) or DATE_BUILTINS.get(int(nid))
                if code and code != "datetime":
                    try:
                        val = fmt_date(serial_to_date(float(v.text)), code)
                    except (ValueError, OverflowError):
                        val = v.text
                else:
                    val = v.text
            cells[idx] = val
            width = max(width, idx + 1)
        grid.append(cells)
    return [[r.get(i, "") for i in range(width)] for r in grid]


HARNESS = r"""
(function(){
const AOA = __AOA__;
const result = {steps:[], errors:[]};
function step(name, fn){
  try { result.steps.push({name:name, value:fn()}); }
  catch(e){ result.errors.push(name+': '+(e && e.message ? e.message : String(e))); }
}

// Baseline, captured before anything is imported, so AC-09 can compare.
// SEED_* is the immutable baked-in baseline. TASKS/MILESTONES are the ACTIVE
// VIEW and are expected to change when an update is imported, so asserting on
// them would report a correct view switch as baseline corruption.
const baseline = {seedTasks: SEED_TASKS.length, seedMilestones: SEED_MILESTONES.length,
                  viewTasks: TASKS.length, viewMilestones: MILESTONES.length,
                  sourceMode: (typeof DATA_SOURCE!=='undefined' && DATA_SOURCE) ? DATA_SOURCE.mode : null};

// Stand in for SheetJS at exactly the boundary the app uses.
window.XLSX = {
  read: function(){ return {SheetNames:['TASK'], Sheets:{TASK:{__aoa:AOA}}}; },
  utils: { sheet_to_json: function(sheet){ return sheet.__aoa; } }
};

let parsed = null;
step('parse', function(){
  PENDING_IMPORT_FILE = '103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx';
  parsed = Parse.workbook(new Uint8Array([0]));
  return {rows: parsed.rows.length, headers: parsed.headers, headerScore: parsed.headerScore,
          sheet: parsed.sheet};
});

step('automap', function(){
  showMapper(parsed);
  const fields = ['id','name','finish','start','float','status','wbs','budget','pct'];
  const map = {};
  fields.forEach(function(f){
    const sel = document.getElementById('map-'+f);
    map[f] = sel ? parseInt(sel.value,10) : -2;
  });
  return {map: map, autoMap: LAST_MAP};
});

step('ingest', function(){
  const dd = document.getElementById('cfg-datadate');
  if (dd) dd.value = '2026-08-29';
  DIAG = [];
  runIngest();
  return {
    tasks: (typeof UPDATE_TASKS!=='undefined' && UPDATE_TASKS) ? UPDATE_TASKS.length : null,
    milestones: (typeof UPDATE_MILESTONES!=='undefined' && UPDATE_MILESTONES) ? UPDATE_MILESTONES.length : null,
    diagCount: DIAG.length,
    diagSample: DIAG.slice(0,6),
    imported: (typeof IMPORTED_SETTINGS!=='undefined' && IMPORTED_SETTINGS) ? {
      file: IMPORTED_SETTINGS.file, rows: IMPORTED_SETTINGS.rows,
      tasks: IMPORTED_SETTINGS.tasks, milestones: IMPORTED_SETTINGS.milestones,
      dataDate: String(IMPORTED_SETTINGS.dataDate)
    } : null,
    sourceLabel: (typeof UPDATE_SOURCE!=='undefined' && UPDATE_SOURCE) ? UPDATE_SOURCE.label : null
  };
});

// Date handling, straight from the app's own parser.
step('dates', function(){
  const probes = ['29-Aug-26','1-May-26 A','15-Jun-26 A','46352','29-Aug-26 *','', null];
  const out = {};
  probes.forEach(function(p){
    const r = parseLooseDate(p);
    out[String(p)] = r ? {date: r.date.toISOString().slice(0,10), actual: r.actual, starred: r.starred} : null;
  });
  return out;
});

step('milestone_flags', function(){
  if (typeof UPDATE_MILESTONES === 'undefined' || !UPDATE_MILESTONES) return null;
  let actual = 0, starred = 0, withDate = 0;
  let startStarred = 0;
  UPDATE_MILESTONES.forEach(function(m){
    if (m.actual) actual++;
    if (m.starred) starred++;          // finish-date constrained flag
    if (m.startStarred) startStarred++;
    if (m.date) withDate++;
  });
  return {total: UPDATE_MILESTONES.length, actual: actual,
          finishStarred: starred, startStarred: startStarred, withDate: withDate,
          sampleKeys: UPDATE_MILESTONES.length ? Object.keys(UPDATE_MILESTONES[0]) : []};
});

step('baseline_intact', function(){
  return {before: baseline,
          seedTasksAfter: SEED_TASKS.length, seedMilestonesAfter: SEED_MILESTONES.length,
          viewTasksAfter: TASKS.length, viewMilestonesAfter: MILESTONES.length};
});

step('data_date_rendered', function(){
  const el = document.querySelector('.import-summary-row') || document.getElementById('rpt-sub');
  const meta = document.body.innerText || '';
  const m = meta.match(/Data date:?\s*([^\n·]*)/i);
  return {found: !!m, text: m ? m[1].trim().slice(0,40) : null,
          hasNotSet: /not set/i.test(meta)};
});

step('dom_after_import', function(){
  const tb = document.getElementById('tbody');
  return {rows: tb ? tb.querySelectorAll('tr').length : 0,
          markers: tb ? tb.querySelectorAll('.m-wrap').length : 0,
          depLines: document.querySelectorAll('#dep-line-layer .dep-line').length};
});

step('diagnostics_panel', function(){
  const sect = document.getElementById('diag-sect');
  const body = document.getElementById('diag-body');
  const badge = document.getElementById('diag-badge-text');
  const sev = {};
  DIAG.forEach(function(d){ sev[d.stage+'/'+d.sev] = (sev[d.stage+'/'+d.sev]||0) + 1; });
  return {sectExists: !!sect, sectHidden: sect ? (sect.offsetParent === null) : null,
          bodyRows: body ? body.children.length : null,
          badge: badge ? badge.textContent.trim() : null,
          diagCount: DIAG.length, bySeverity: sev};
});

// Dependency data is a baked-in constant parsed from a 22-Aug-26 export. The
// mapper exposes no predecessor/successor field, so an import never refreshes
// it. Measure how far the imported activity set has drifted from it.
step('dep_data_coverage', function(){
  if (typeof UPDATE_MILESTONES === 'undefined' || !UPDATE_MILESTONES) return null;
  const ids = {};
  UPDATE_MILESTONES.forEach(function(m){ if (m.ref) ids[m.ref] = 1; });
  const importedIds = Object.keys(ids);
  let covered = 0;
  importedIds.forEach(function(id){ if (DEP_DATA[id]) covered++; });
  const depIds = Object.keys(DEP_DATA);
  const staleOnly = depIds.filter(function(id){ return !ids[id]; });
  return {importedActivityIds: importedIds.length, inDepData: covered,
          missingFromDepData: importedIds.length - covered,
          depDataIds: depIds.length, inDepDataButNotImported: staleOnly.length,
          sampleMissing: importedIds.filter(function(id){ return !DEP_DATA[id]; }).slice(0,8)};
});

const pre = document.createElement('pre');
pre.id = 'import-probe-out';
pre.textContent = JSON.stringify(result);
document.body.appendChild(pre);
})();
"""


def find_chrome():
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    sys.exit("No headless Chromium found.")


def run(html_path, aoa):
    html = html_path.read_text(encoding="utf-8", errors="replace")
    js = HARNESS.replace("__AOA__", json.dumps(aoa))
    injected = html.replace("</body>", f"<script>\n{js}\n</script>\n</body>")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "import_probe.html"
        tmp.write_text(injected, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             "--virtual-time-budget=15000", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=180)
    m = re.search(r'<pre id="import-probe-out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        sys.exit("Probe output not found. The page threw before the probe finished.\n"
                 + proc.stderr[-3000:])
    raw = (m.group(1).replace("&amp;", "&").replace("&lt;", "<")
           .replace("&gt;", ">").replace("&quot;", '"'))
    return json.loads(raw)


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=root / "data" / "schedules" /
                    "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--html", default=root / "src" / "milestone-dashboard.html")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    aoa = build_aoa(pathlib.Path(args.xlsx))
    print(f"Reference workbook: {len(aoa)} rows x {len(aoa[0]) if aoa else 0} columns")
    print(f"Header row as the app will see it: {aoa[0]}")
    print(f"Sample data row: {aoa[3]}")
    print()

    data = run(pathlib.Path(args.html), aoa)
    steps = {s["name"]: s["value"] for s in data["steps"]}
    if data["errors"]:
        print("ERRORS DURING RUN:")
        for e in data["errors"]:
            print("  " + e)
        print()

    print(json.dumps(steps, indent=2)[:4000])

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nFull result written to {args.json}")
    return 1 if data["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
