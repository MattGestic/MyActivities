#!/usr/bin/env python3
"""
P28 check (TEST-31): the date range, at setup and as a filter.

Two halves, one question each.

  SETUP. Does an import derive its base range from the data, rather than from
  the fixed 12-weeks-before / 26-after window around the data date? The test
  that matters is not "a timeline was built" but "nothing datable in the
  import falls outside it", which is exactly what the old window got wrong.
  A typed range must override that, and a typed range must be what is used.

  FILTER. Does a user-typed range actually narrow the board, put it back when
  cleared, survive a rebuild, and intersect correctly with the week dropdown
  rather than fighting it?

The expected range is derived from the workbook here, independently of the
app, so the assertion is against the source data and not against whatever the
app decided. Reuses tools/import_check.py for the workbook-to-AoA conversion
and the SheetJS stub.

Usage:
  python3 tools/p28_check.py [--xlsx FILE] [--html FILE]
Exit code 1 on any failed check.
"""

import argparse
import base64
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import build_aoa, find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p28-out">(.*?)</pre>', re.S)

PROBE = r"""
(async function(){
  const R={checks:[]};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p28-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  function freeze(){
    const s=document.createElement('style');
    s.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(s); void document.body.offsetWidth;
  }
  // The week HEADER cells, one per column. Counting body cells instead
  // multiplied the answer by the row count and made every comparison against
  // NCOLS meaningless.
  const shownWkCols=function(){
    return Array.from(document.querySelectorAll('#week-hdr th.col-wk[data-col]')).filter(function(th){
      return getComputedStyle(th).display!=='none';
    }).length;
  };
  // Split, because the range fields only exist between these two steps: the
  // success path nulls LAST_PARSE and hides the whole setup section, so a
  // range is something set BEFORE Import, not adjusted after it.
  function openMapper(){
    PENDING_IMPORT_FILE='reference.xlsx';
    showMapper(Parse.workbook(new Uint8Array([0])));
    const dd=document.getElementById('cfg-datadate'); if(dd) dd.value='2026-08-29';
  }
  function pressImport(){ DIAG=[]; runIngest(); }
  function doImport(){ openMapper(); pressImport(); }

  try{
    window.XLSX={
      read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
      utils:{ sheet_to_json:function(s){ return s.__aoa; } }
    };

    // ================= SETUP: derived base range =================
    // The range section must not be offered before a file is parsed.
    R.rangeSectHiddenAtStart=getComputedStyle(document.getElementById('range-wrap-section')).display;
    ck('setup: the date range section is hidden until a file loads',
       R.rangeSectHiddenAtStart==='none');

    openMapper();
    await settle(); freeze();
    ck('setup: the date range section is shown once a file loads',
       getComputedStyle(document.getElementById('range-wrap-section')).display!=='none');
    // The point of deriving at setup is that the min and max are readable
    // while the range can still be set. Asserted against the dates, not
    // against "a note exists".
    R.noteAtSetup=document.getElementById('range-note').textContent;
    ck('setup: the note names the schedule\u2019s own span before Import is pressed',
       /01-May-26/.test(R.noteAtSetup)&&/26-Nov-26/.test(R.noteAtSetup),
       R.noteAtSetup.slice(0,110));
    ck('setup: both range fields start blank, meaning the full span',
       document.getElementById('cfg-range-from').value===''&&
       document.getElementById('cfg-range-to').value==='');
    pressImport();
    await settle(); freeze();
    ck('setup: the section is put away once the import is built',
       getComputedStyle(document.getElementById('range-wrap-section')).display==='none');

    R.weeks=WE_DATES.length;
    R.boardFrom=isoDay(new Date(WE_DATES[0].getFullYear(),WE_DATES[0].getMonth(),WE_DATES[0].getDate()-6));
    R.boardTo=isoDay(WE_DATES[WE_DATES.length-1]);

    // THE assertion for this half. Under the old fixed window, dates outside
    // 12 weeks before / 26 after the data date plotted nowhere and were only
    // reported as a diagnostic. Every milestone must now land in a column.
    let unplotted=[];
    UPDATE_MILESTONES.forEach(function(m){
      if(dateToCol(m.date)<0) unplotted.push(m.id+'@'+m.date);
    });
    R.unplotted=unplotted.slice(0,8);
    ck('setup: every imported milestone lands in a column',
       unplotted.length===0, unplotted.length+' outside the board');

    // The board must not be padded far beyond the data either: a range taken
    // from the data should not run more than a week past it at each end
    // (one week of rounding out to the enclosing week, plus the data date).
    const derived=deriveScheduleRange(UPDATE_TASKS,UPDATE_MILESTONES);
    R.dataFrom=isoDay(derived.min); R.dataTo=isoDay(derived.max);
    const slackStart=Math.round((msDateMs(R.dataFrom)-msDateMs(R.boardFrom))/86400000);
    const slackEnd=Math.round((msDateMs(R.boardTo)-msDateMs(R.dataTo))/86400000);
    R.slackStart=slackStart; R.slackEnd=slackEnd;
    // The data date is pulled into the range when it sits outside it, so the
    // leading slack is measured from whichever of the two comes first.
    const ddMs=msDateMs('2026-08-29');
    const wantStart=Math.min(msDateMs(R.dataFrom),ddMs);
    const wantEnd=Math.max(msDateMs(R.dataTo),ddMs);
    ck('setup: the board starts within a week of the earliest date it must show',
       Math.round((wantStart-msDateMs(R.boardFrom))/86400000)<=7,
       slackStart+' days of lead');
    ck('setup: the board ends within a week of the latest date it must show',
       Math.round((msDateMs(R.boardTo)-wantEnd)/86400000)<=7,
       slackEnd+' days of tail');

    // The setup fields are cleared with the section, so the range that was
    // used has to be legible on the surface that survives the import.
    R.summaryHtml=baseRangeSummaryHtml(IMPORTED_SETTINGS);
    ck('setup: the import summary states the range the board was built over',
       R.summaryHtml.indexOf(fmtTipDate(R.boardFrom))>=0&&
       R.summaryHtml.indexOf(fmtTipDate(R.boardTo))>=0,
       R.summaryHtml.replace(/<[^>]*>/g,'').slice(0,120));
    ck('setup: the import summary also states the data\u2019s own span',
       R.summaryHtml.indexOf(fmtTipDate('2026-05-01'))>=0&&
       R.summaryHtml.indexOf(fmtTipDate('2026-11-26'))>=0);
    ck('setup: the import summary records where the range came from',
       IMPORTED_SETTINGS.baseRangeSource==='data', String(IMPORTED_SETTINGS.baseRangeSource));

    // ---- A typed range must override the derived one ----
    const TYPED_FROM='2026-09-01', TYPED_TO='2026-11-30';
    openMapper();
    await settle();
    document.getElementById('cfg-range-from').value=TYPED_FROM;
    document.getElementById('cfg-range-to').value=TYPED_TO;
    onBaseRangeEdit();
    pressImport();
    await settle(); freeze();
    R.typedWeeks=WE_DATES.length;
    R.typedFrom=isoDay(new Date(WE_DATES[0].getFullYear(),WE_DATES[0].getMonth(),WE_DATES[0].getDate()-6));
    R.typedTo=isoDay(WE_DATES[WE_DATES.length-1]);
    ck('setup: a typed range is narrower than the derived one',
       R.typedWeeks<R.weeks, R.typedWeeks+' weeks vs '+R.weeks);
    ck('setup: a typed range covers the dates that were typed',
       msDateMs(R.typedFrom)<=msDateMs(TYPED_FROM)&&msDateMs(R.typedTo)>=msDateMs(TYPED_TO),
       R.typedFrom+' to '+R.typedTo+' must enclose '+TYPED_FROM+' to '+TYPED_TO);
    ck('setup: a typed range is recorded as typed',
       IMPORTED_SETTINGS.baseRangeSource==='typed', String(IMPORTED_SETTINGS.baseRangeSource));

    // ---- Back to the full derived range for the filter half ----
    openMapper(); await settle();
    document.getElementById('cfg-range-from').value=TYPED_FROM;
    resetBaseRange();
    ck('setup: reset clears both fields',
       document.getElementById('cfg-range-from').value===''&&document.getElementById('cfg-range-to').value==='');
    pressImport();
    await settle(); freeze();
    ck('setup: clearing the fields restores the full derived range',
       WE_DATES.length===R.weeks, WE_DATES.length+' vs '+R.weeks);

    // ================= FILTER: user-defined range =================
    const allCols=shownWkCols();
    R.colsUnfiltered=allCols;
    ck('filter: every week column is shown before filtering', allCols===NCOLS, allCols+' of '+NCOLS);

    const F='2026-09-01', T='2026-10-31';
    document.getElementById('filter-date-from').value=F;
    document.getElementById('filter-date-to').value=T;
    applyFilter(); freeze();
    const narrowed=shownWkCols();
    R.colsFiltered=narrowed;
    ck('filter: a date range narrows the visible week columns',
       narrowed>0&&narrowed<allCols, narrowed+' of '+allCols);

    // Every column still showing must fall inside the typed range, and every
    // column inside the range must still be showing. Both directions, or a
    // filter that hides everything would pass the first one.
    let shownOutside=0, hiddenInside=0;
    const fMs=msDateMs(F), tMs=msDateMs(T);
    document.querySelectorAll('#week-hdr th.col-wk[data-col]').forEach(function(th){
      const c=parseInt(th.getAttribute('data-col'),10);
      const we=WE_DATES[c].getTime();
      const weStart=we-6*86400000;
      const inRange=(we>=fMs&&weStart<=tMs);
      const shown=getComputedStyle(th).display!=='none';
      if(shown&&!inRange) shownOutside++;
      if(!shown&&inRange) hiddenInside++;
    });
    R.shownOutside=shownOutside; R.hiddenInside=hiddenInside;
    ck('filter: no column outside the range is still shown', shownOutside===0, shownOutside+' leaked');
    ck('filter: no column inside the range was hidden', hiddenInside===0, hiddenInside+' lost');

    // The month bands sit above the weeks and carry a colspan, so they have to
    // shrink with them or the header stops lining up with the body.
    let moSpan=0;
    document.querySelectorAll('#phase-hdr th.mo-band').forEach(function(th){
      if(getComputedStyle(th).display!=='none') moSpan+=th.colSpan;
    });
    R.moSpan=moSpan;
    ck('filter: the month bands span exactly the columns still shown',
       moSpan===narrowed, moSpan+' month colspan vs '+narrowed+' columns');

    // Rows with nothing left in range go too.
    const visRows=document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)').length;
    const allRows=document.querySelectorAll('tr[data-type="row"]').length;
    R.visRows=visRows; R.allRows=allRows;
    ck('filter: rows with nothing in the range are hidden',
       visRows>0&&visRows<allRows, visRows+' of '+allRows+' rows');
    // P53 (TD-202): the summary line's date-range wording changed from
    // "date range X to Y (...)" to "between W/E X and W/E Y (...)" (no em
    // dash, middle-dot separators) — rewritten to the new, equally valid
    // contract per the TD-170 precedent, not relaxed.
    ck('filter: the summary line names the range',
       /between W\/E .+ and W\/E /.test(document.getElementById('filter-info').textContent),
       document.getElementById('filter-info').textContent.slice(0,90));

    // ---- Intersecting with the week dropdown ----
    // A week filter set OUTSIDE the date range must not reach back outside it.
    document.getElementById('week-filter').value='0';
    document.getElementById('filter-mode').value='single';
    applyFilter(); freeze();
    let leaked=0;
    document.querySelectorAll('#week-hdr th.col-wk[data-col]').forEach(function(th){
      const c=parseInt(th.getAttribute('data-col'),10);
      if(getComputedStyle(th).display!=='none'&&(c<DATE_RANGE_COLS.lo||c>DATE_RANGE_COLS.hi)) leaked++;
    });
    ck('filter: a week selection outside the range cannot reach back outside it',
       leaked===0, leaked+' columns leaked');
    document.getElementById('week-filter').value='';
    applyFilter();

    // ---- Surviving a rebuild ----
    // teardown() rebuilds every cell and <col>; without the filter being
    // reapplied the hidden columns all come back.
    scheduleRerender(true);
    await settle(); freeze();
    R.colsAfterRerender=shownWkCols();
    ck('filter: the range survives a full rebuild',
       R.colsAfterRerender===narrowed, R.colsAfterRerender+' vs '+narrowed);

    // ---- Clearing ----
    clearDateRangeFilter(); freeze();
    R.colsAfterClear=shownWkCols();
    ck('filter: clearing the range puts every column back',
       R.colsAfterClear===allCols, R.colsAfterClear+' vs '+allCols);
    ck('filter: clearing the range empties both fields',
       document.getElementById('filter-date-from').value===''&&
       document.getElementById('filter-date-to').value==='');

    // "Remove all filters" must also release the columns, not just the fields.
    document.getElementById('filter-date-from').value=F;
    document.getElementById('filter-date-to').value=T;
    applyFilter();
    clearFilter(); freeze();
    R.colsAfterClearAll=shownWkCols();
    ck('filter: Remove all filters releases the columns too',
       R.colsAfterClearAll===allCols, R.colsAfterClearAll+' vs '+allCols);

    // One end only is a one-sided clamp, not all-or-nothing.
    document.getElementById('filter-date-from').value='2026-10-01';
    document.getElementById('filter-date-to').value='';
    applyFilter(); freeze();
    const openEnded=shownWkCols();
    R.colsOpenEnded=openEnded;
    ck('filter: a from-date alone clamps one end and leaves the other open',
       openEnded>0&&openEnded<allCols&&DATE_RANGE_COLS.hi===NCOLS-1,
       openEnded+' of '+allCols+', hi='+(DATE_RANGE_COLS?DATE_RANGE_COLS.hi:'null')+' of '+(NCOLS-1));

    // A backwards range is a typo, and swapping is the reading meant.
    document.getElementById('filter-date-from').value=T;
    document.getElementById('filter-date-to').value=F;
    applyFilter(); freeze();
    R.colsBackwards=shownWkCols();
    ck('filter: a backwards range is read as the range the user meant',
       R.colsBackwards===narrowed, R.colsBackwards+' vs '+narrowed+' for the same pair forwards');

    clearFilter();

    // ---- The A3 preview fits the columns the range left ----
    // fitPrintPage() counts visible week columns; a range that hides some has
    // to reach it, or the preview fits a board wider than the one on screen.
    document.getElementById('filter-date-from').value=F;
    document.getElementById('filter-date-to').value=T;
    applyFilter();
    togglePrintMode(true);
    await settle(); freeze();
    R.printBanner=document.getElementById('pm-banner-detail').textContent;
    R.printWk=document.getElementById('wk-width').value;
    ck('print + range: the preview fits only the columns still shown',
       new RegExp('^'+narrowed+' week columns').test(R.printBanner),
       R.printBanner);
    // With most of the board filtered out it must now actually fit the page,
    // which the full 31-week board does not.
    ck('print + range: a narrowed board fits the A3 sheet',
       !/exceed the page width/.test(R.printBanner), R.printBanner);
    togglePrintMode(false);
    await settle();
    clearFilter();

    R.ok=true;
  }catch(e){ R.err=String(e&&e.message); R.stack=String(e&&e.stack||'').slice(0,900); }
  emit();
})();
"""


def expected_range_from_workbook(aoa):
    """Earliest and latest date anywhere in the sheet's date columns, derived
    here rather than taken from the app, so the app's own range can be checked
    against the source instead of against itself."""
    if not aoa:
        return None, None
    hdr = [str(h or "").strip().lower() for h in aoa[0]]
    date_cols = [i for i, h in enumerate(hdr)
                 if any(k in h for k in ("start", "finish", "date"))]
    if not date_cols:
        return None, None
    pat = re.compile(r"^\s*(\d{1,2})-([A-Za-z]{3})-(\d{2})")
    lo = hi = None
    for row in aoa[1:]:
        for i in date_cols:
            if i >= len(row):
                continue
            m = pat.match(str(row[i] or ""))
            if not m:
                continue
            day, mon, yr = m.groups()
            try:
                d = dt.datetime.strptime(f"{day}-{mon.title()}-{yr}", "%d-%b-%y").date()
            except ValueError:
                continue
            if lo is None or d < lo:
                lo = d
            if hi is None or d > hi:
                hi = d
    return lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default="data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--html", default="src/milestone-dashboard.html")
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    want_lo, want_hi = expected_range_from_workbook(aoa)

    html = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html.replace("</body>", inject + "</body>")
    if page == html:
        sys.exit("Could not find </body> to inject into.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p28.html"
        tmp.write_text(page, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--window-size=1600,1200", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=480,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit("Probe output not found.\n" + proc.stderr[-3000:])
    R = json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))

    if not R.get("ok"):
        print("PROBE FAILED: " + str(R.get("err")))
        print(R.get("stack", ""))
        return 1

    for k in ("weeks", "boardFrom", "boardTo", "dataFrom", "dataTo",
              "slackStart", "slackEnd", "typedWeeks", "typedFrom", "typedTo",
              "colsUnfiltered", "colsFiltered", "moSpan", "visRows", "allRows",
              "colsAfterRerender", "colsAfterClear", "colsAfterClearAll",
              "colsOpenEnded", "colsBackwards", "printWk"):
        if k in R:
            print(f"   {k}: {R[k]}")
    if R.get("printBanner"):
        print("   print banner: " + R["printBanner"])
    if R.get("unplotted"):
        print("   unplotted sample: " + json.dumps(R["unplotted"]))
    print()

    fails = [c for c in R["checks"] if not c["pass"]]
    for c in R["checks"]:
        mark = "ok  " if c["pass"] else "FAIL"
        print(f"  {mark} {c['name']}" + (f"   [{c['detail']}]" if c["detail"] else ""))

    # Cross-check the app's derived range against the workbook, independently.
    if want_lo and want_hi:
        print(f"\nWorkbook's own date span (derived here, not from the app): {want_lo} to {want_hi}")
        app_lo = R.get("dataFrom")
        app_hi = R.get("dataTo")
        ok_lo = app_lo == want_lo.isoformat()
        ok_hi = app_hi == want_hi.isoformat()
        for label, ok, got, want in (("earliest", ok_lo, app_lo, want_lo),
                                     ("latest", ok_hi, app_hi, want_hi)):
            mark = "ok  " if ok else "FAIL"
            print(f"  {mark} setup: the app's {label} date matches the workbook   [{got} vs {want}]")
            if not ok:
                fails.append({"name": f"workbook {label}"})
    else:
        print("\n  FAIL could not derive a date span from the workbook, so the "
              "cross-check would pass vacuously")
        fails.append({"name": "workbook derivation"})

    print(f"\n{len(R['checks']) + 2 - len(fails)}/{len(R['checks']) + 2} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
