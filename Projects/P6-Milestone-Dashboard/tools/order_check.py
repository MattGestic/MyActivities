#!/usr/bin/env python3
"""
Board order check for the P6 Milestone Dashboard (TEST-25 / TD-65).

One question: does an imported board present its bands in the order the
schedule presents them?

The board is the client's schedule, so it keeps the client's sequence. The
aggregate step used to sort groups on the WBS path STRING, which is
alphabetical and unrelated to how the schedule is laid out.

Method. The expected order is derived from the workbook itself, not typed in
here: a row carrying a name but no Activity ID is a section heading in this
export, so the headings in sheet order ARE the schedule's sequence. That is
compared against the band sequence the app produces after a real import
through Parse.workbook, showMapper and runIngest.

Reuses tools/import_check.py for the workbook-to-AoA conversion and the
SheetJS stub, so both checks read the reference export identically.

Usage:
  python3 tools/order_check.py [--xlsx FILE] [--html FILE]
Exit code 1 if the board order does not follow the schedule.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import build_aoa, find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="order-out">(.*?)</pre>', re.S)

PROBE = r"""
(function(){
  const R={ok:false};
  function emit(){
    const o=document.createElement('pre'); o.id='order-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  try{
    window.XLSX={
      read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
      utils:{ sheet_to_json:function(s){ return s.__aoa; } }
    };
    PENDING_IMPORT_FILE='reference.xlsx';
    const parsed=Parse.workbook(new Uint8Array([0]));
    showMapper(parsed);
    const dd=document.getElementById('cfg-datadate');
    if(dd) dd.value='2026-08-29';
    DIAG=[];
    runIngest();

    // The band each row belongs to, in board order, de-duplicated to runs.
    // Read off the live model rather than the DOM: the DOM adds band heading
    // rows of its own and would make this look right for the wrong reason.
    const seq=[];
    UPDATE_TASKS.forEach(function(t){
      const label=(t.notes||'')+' | '+(t.disc||'');
      if(!seq.length||seq[seq.length-1]!==label) seq.push(label);
    });
    R.boardBands=seq;
    R.rowCount=UPDATE_TASKS.length;
    R.msCount=UPDATE_MILESTONES.length;
    // First activity id per band, in board order. Activity ids run roughly in
    // schedule order in this export, so a board that follows the schedule
    // should not jump backwards wildly between bands.
    R.firstIds=[];
    let last=null;
    UPDATE_TASKS.forEach(function(t){
      const label=(t.notes||'')+' | '+(t.disc||'');
      if(label!==last){ R.firstIds.push(String(t.src||t.ref||'').split(',')[0].trim()); last=label; }
    });
    R.ok=true;
  }catch(e){ R.err=e.message; R.stack=String(e.stack||'').slice(0,600); }
  emit();
})();
"""


def schedule_structure(aoa):
    """Walk the sheet and return, in sheet order:

      bands    the deepest heading in force over each activity, de-duplicated
               to runs, which is the sequence the board should present
      row_of   Activity ID -> row index in the sheet, so a board band can be
               placed back on the schedule exactly rather than by id arithmetic

    In this export a heading row carries indented text in the Activity ID
    column and an empty Activity Name; indent depth gives the level. The first
    version of this function looked for the opposite shape, found nothing, and
    let the check fall through to a weaker heuristic that passed anyway.
    """
    bands, row_of, stack = [], {}, []
    for idx, row in enumerate(aoa[1:]):
        if not row:
            continue
        col_a = str(row[0] or "")
        name = str(row[1] or "").strip() if len(row) > 1 else ""
        text = col_a.strip()
        if not text:
            continue
        depth = (len(col_a) - len(col_a.lstrip(" "))) // 2
        if not name:                      # heading row
            del stack[depth:]
            stack.append(text)
            continue
        row_of[text] = idx                # activity row
        band = stack[-1] if stack else "(no heading)"
        if not bands or bands[-1] != band:
            bands.append(band)
    return bands, row_of


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default="data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--html", default="src/milestone-dashboard.html")
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    expected, row_of = schedule_structure(aoa)
    if not expected:
        sys.exit("Derived no headings from the workbook. The check would pass "
                 "vacuously, so it fails loudly instead.")

    html = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html.replace("</body>", inject + "</body>")
    if page == html:
        sys.exit("Could not find </body> to inject into.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "probe.html"
        tmp.write_text(page, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu",
             "--virtual-time-budget=30000", "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=300,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit("Probe output not found.\n" + proc.stderr[-3000:])
    import base64
    R = json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))
    if not R.get("ok"):
        print("PROBE FAILED: " + str(R.get("err")))
        print(R.get("stack", ""))
        return 1

    print("Schedule section order (derived from the workbook):")
    for h in expected:
        print("   " + h)

    print("\nBoard band order after import:")
    for b in R["boardBands"]:
        print("   " + b)

    # The decisive assertion, stated exactly rather than by heuristic: place
    # each board band back onto the schedule by the sheet row of its first
    # activity. A board that follows the schedule visits those rows in
    # increasing order. Bands roll up to a discipline under the tag strategy,
    # so band NAMES cannot be compared one to one, but positions can.
    positions, unknown = [], []
    for first in R["firstIds"]:
        if first in row_of:
            positions.append((first, row_of[first]))
        else:
            unknown.append(first)

    print(f"\nBands: {len(R['boardBands'])}   rows: {R['rowCount']}   milestones: {R['msCount']}")
    print("Sheet row of each band's first activity, in board order:")
    print("   " + ", ".join(f"{i}@{r}" for i, r in positions))

    fails = []
    if unknown:
        fails.append(f"could not place these board bands back on the schedule: {unknown}")
    if len(positions) < len(R["boardBands"]):
        fails.append("not every band was placed, so the ordering assertion would be partial")

    rows = [r for _, r in positions]
    inversions = [(positions[i][0], positions[i + 1][0])
                  for i in range(len(rows) - 1) if rows[i + 1] < rows[i]]
    if inversions:
        fails.append(f"{len(inversions)} band(s) appear out of schedule order: " +
                     ", ".join(f"{b} before {a}" for a, b in inversions))

    first_band = R["boardBands"][0] if R["boardBands"] else ""
    if expected and expected[0].lower() not in first_band.lower():
        fails.append(f"board opens with {first_band!r}, schedule opens with {expected[0]!r}")

    for f in fails:
        print("  FAIL " + f)
    if not fails:
        print("\n  ok   every band sits in the schedule's own order, strictly increasing")
        print("  ok   board opens with the schedule's first section")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
