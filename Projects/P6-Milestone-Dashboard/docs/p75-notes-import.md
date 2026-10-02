# P75 notes: week-range picker end date, Import button, Import panel order

For the orchestrator to fold into TD / TEST. Matt, 2026-10-02, desktop screenshots. Base: `2a83203` (v3.1.0-P74). `APP_VERSION` not bumped.

## 1. Week-range picker would not take an end week

**Symptom.** A first click set the start. A second click on another week did nothing. The head read "W/E06 Sep 26→06 Sep 26", with no space after W/E.

**Root cause: event handling and re-rendering.**
- `wrHoverWeek()` (each cell's `onmouseenter`) called `renderWeekRangePopover()`. That function rebuilt the whole popover with `pop.innerHTML`, so it replaced the week cell under the pointer.
- When the node under a resting pointer is replaced, Chromium fires `mouseenter` on the new node. That called the rebuild again.
- So once a start was picked, the grid rebuilt continuously while the pointer rested on any week.
- When `mousedown` and `mouseup` land on two different (replaced) cells, the click is dispatched to neither cell, so `wrPickWeek()` never ran for the end.
- With the pointer still on the start cell, `hoverCol` was the start itself. That produced the "06 Sep → 06 Sep" head.
- Reproduced with real pointer events (Playwright): after the first click, the target cell was "detached from the DOM" on every retry.

**Missing space.** The head's `.wr-tag` / `.wr-val` / `.wr-arrow` / `.wr-div` / `.wr-count` were styled only under `#top-filter-bar .wr-field`. Inside the popover head they had no gap.

**Fix** (`src/milestone-dashboard.html`, D-16b picker block):
- `renderWeekRangePopover()` now builds the structure only. It runs once per open, and again when Range start or Range end rebuilds the timeline.
- A new paint pass, `wrPaintWeekRange()`, toggles `end` / `in` / `preview` / `pending` and `aria-pressed` on the existing cells, rewrites the head, and sets Apply's `disabled`.
- `wrHoverWeek()`, `wrPickWeek()` and `wrPickQuick()` call the paint pass, never the rebuild. Hovering the week already hovered is a no-op.
- The head reads "Start <date> | Pick an end week" until the pointer moves to another week.
- **Behaviour:**
  - The first click sets the start.
  - A second click on a later week sets the end.
  - A second click on an earlier week **swaps**: it becomes the start, and the first pick becomes the end. This is the existing min/max behaviour, kept.
  - A second click on the same week gives a one-week range.
  - Weeks strictly between the start and the end get `.in`, and get `.preview` while hovering.
  - The legend gained an "In range" swatch.
- **Head styles:** the field's selectors are extended to `.wr-head .wr-*`. No new values. Real spaces were also added around the tag and the arrow in the markup, in both the head and the field, so the text reads "W/E 06 Sep 26 → 04 Oct 26".
- **Keyboard:** `weekRangePopoverKeydown()` no longer turns Enter on a week cell, a button or a field into Apply. Before this, Enter on a week applied whatever was selected instead of picking that week. Focus now stays on the week, because nothing is rebuilt.

## 2. Import button "inactive" at "✓ Ready to import"

**Finding.** In every run, `disabled` was false, there was no `aria-disabled`, opacity was 1, `pointer-events` was auto, nothing covered the button, and a click imported. The runs covered the file path and the paste path, light and dark themes, the empty app, the fixture, and the published empty copy. I could not reproduce a button that was actually disabled.

**Root cause of the inactive look.**
- Discard and Import were rendered as `.toggle-btn` / `.toggle-btn.active`. That is the app's 10px on/off toggle-chip style, 17px tall. It is identical to the "Parse pasted data" chip directly above, and to the other "toggle is on" chips.
- Import therefore read as a toggle that happened to be on, not as the action that commits the import. Elsewhere the primary-action style is `.ds-btn.primary` (the empty state's Import schedule, the picker's Apply).

**Fix.**
- The summary buttons are now `button.ds-btn#import-discard-btn` and `button.ds-btn.primary#import-run-btn`, in an `.import-summary-actions` flex row.
- Import writes `aria-disabled` explicitly ("false" / "true") alongside `disabled`.
- A disabled primary (Finish unmapped) is dimmed by `.import-summary-actions .ds-btn.primary:disabled`.

## 3. Import tab order

New order:
1. Import a schedule: file and paste box. Badge: Required.
2. Map columns. Badge: Once a file loads.
3. Source: name and mode. Badge: Once a file loads.
4. **Import date range**: subheader "Filter import date range" (`#import-dates-sub`). Badge: Optional.

Step 4 is a new `.sd-step#import-dates-section`, holding:
- Data date (`#cfg-datadate-main`) and Report date (`#cfg-reportdate`). They moved from step 1 with the same ids, handlers and help text.
- Below them, the old step 3 range filter, still `#range-wrap-section`, now a plain wrapper. It keeps the Board span label, `#range-note`, `#cfg-range-from`, `#cfg-range-to` and `#btn-range-reset`.

Visibility:
- Step 4 is always shown, because both dates are editable with or without a file (the report date has no other editor).
- `#range-wrap-section` still appears only once a file loads, and is cleared and hidden after an import or Discard (`setRangeSectionVisible`, unchanged).
- The range row label carries the "Once a file loads" badge.

`syncImportSteps()` now reads the steps in the new order. It treats step 4 as reached when `#range-wrap-section` is shown. Before a file, step 1 is current and steps 2 to 4 are waiting. With a file loaded, steps 1 to 3 are done and step 4 is current.

## 4. Paste box cleared after a successful import

`runIngest()`'s success path empties `#paste-box`. It already nulled `LAST_PARSE` / `LAST_MAP` and cleared the summary. The box stays open if it was open. A second "Parse pasted data" then reports "Paste box is empty." and stages nothing.

## 5. Pasted export lost its Activity ID column (follow-up commit)

**Symptom.** Matt's screenshot: after a paste, Activity ID mapped to "not present", 196 rows came through, and the board built 109/150. The reference export reproduces it: 117 deliverables instead of 105.

**Root cause.**
- `Parse.delimited()` split the text into lines first and handled quotes per line, only for commas, never for tabs.
- Excel quotes a cell holding a line break when it copies a range. The P6 export's own header cell is `"\nActivity ID\n"`.
- So the header row broke in two, the Activity ID header became an empty string, and every activity was keyed by name stem instead of ID.

**Fix.**
- `Parse.delimited()` now reads RFC 4180 records, for tab and comma alike. A quoted cell may hold line breaks, the delimiter and doubled quotes (`""`).
- A quote opens a quoted cell only at the start of a cell; mid-cell it is literal (`12" pipe`).
- The delimiter is chosen from the first record, counting only outside quotes.
- An unterminated quote falls back to the old line-by-line reading, so it never swallows the rest of the paste.
- Header cells are trimmed and their inner whitespace (line breaks included) collapsed.
- `Parse.autoMap()` trims and collapses each header before matching. `normKey` already ignored whitespace; this makes the trim explicit.
- `Parse.workbook()` (the file path) is unchanged.

**Check.** `p75_import_check` gained an `excel` run:
- the reference export exactly as Excel puts it on the clipboard (CRLF rows; cells holding a tab, a line break or a quote are quoted, with their quotes doubled);
- asserts Activity ID is header 0 and auto-maps, and that the import equals the file import, 105/146;
- parser unit cases: an embedded comma with `""` in CSV, a quoted TSV header with line breaks, a quoted cell holding a line break and a tab, a literal mid-cell quote, an unterminated quote, and `autoMap` on padded headers.

Against 947ce47's parser the `excel` run fails 5 checks: header `""`, map.id=-1, rows split, and 117/146 instead of 105/146.

The file run's disk read is now handed the same bytes directly, instead of through `FileReader`. Under `--virtual-time-budget`, the real-thread `FileReader` completion was stranded at "Reading ..." about 1 run in 3. Everything after the read is still the app's own: `handleFile()`, the embedded SheetJS, `Parse.workbook()` and `showMapper()`.

## Checks

New: `tools/p75_import_check.py`. It uses the headless Chromium harness, written in the style of `p74_deps_check.py`.

**Picker** (fixture, 1440x900 and 390x844):
- It drives a pointer model. The model re-hit-tests the pointer after every event and fires `mouseenter` when the node under it changes, as Chromium does. It dispatches a click only when `mousedown` and `mouseup` hit the same connected node.
- N=3 different ranges by clicks: the same week, adjacent weeks, and across a month boundary (in Show only). There is also an earlier second week, which swaps.
- For each range it checks:
  - `WR_POP_STATE` after each click;
  - the head text, including the space after W/E, and its flex gap;
  - `.end`, `.in` and `aria-pressed`;
  - Apply;
  - `currentWeekRange()` and the field text;
  - the board: `th.filter-wk` in Highlight, the shown `th.col-wk` in Show only.
- It also checks that Cancel and Escape keep the applied range, and that Enter on a week picks it and keeps focus.

**Import** (`sret:no-fixture`, 1440x900):
- File path: the real `.xlsx` bytes through `handleFile()` and the embedded SheetJS.
- Paste path: the same export as TSV (`build_aoa`) through "Parse pasted data".
- On each path it checks Import's `disabled`, `aria-disabled`, computed opacity, pointer-events and cursor, the primary fill, its size, and that nothing is on top of it.
- Negative case: with Finish unmapped, Import is disabled both ways, then enabled again once Finish is mapped.
- A click imports 105 / 146, the form is put away, and the paste box is empty. A second Parse stages nothing.
- File run only, the panel:
  - order, numbers, headings, badges and the subheader;
  - the two dates are in step 4, above the range filter, and not in step 1;
  - the range text and controls are kept;
  - step states before and after a file;
  - the moved fields' handlers still write `cfg-datadate` and `REPORT_META.reportDate`.

Results:
- Against this change: all pass (207 at 947ce47; 232 with the parser follow-up, three consecutive runs).
- Against the P74 file (`--html` of `2a83203`): the picker fails with Matt's exact symptom. The head reads "W/E07 Jun 26→07 Jun 26", lost=1, churn=25, and the applied range becomes "From ... open end". The panel checks also fail.

`python3 tools/run_checks.py --jobs 3`, three rounds:
- Round 1: 61 selected, 58 passed, 3 failed.
  - `p30_check` hit the runner's 600s subprocess timeout under load. It took 375s, 68/68, on the next round.
  - `persist_check` failed with only a Chromium sandbox warning. Standalone it passed 22/22.
  - `grid_view_check` failed one perf-timing assertion under load (scroll p95 9.2ms against 8ms). Standalone it passed 296/296.
- Round 2: 10 passed; `grid_view_check` failed on timing again.
- Round 3: "9 selected / 53 skipped / 9 passed / 0 failed". Green.

No existing assertion was changed or removed: `p28` / `p29` / `p30` hold as written, because `#range-wrap-section` keeps its show-once-a-file-loads behaviour.
