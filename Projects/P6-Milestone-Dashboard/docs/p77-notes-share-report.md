# P77 notes: Share report

Matt's request of 2026-10-02, on top of v3.1.0-P75 (`643bca6`). `APP_VERSION` is not bumped. Scope: the header action group, one new dialog, a new code block after the PDF exporter, the notes-export module and `tools/colour_audit.py`. The Data & view drawer, the storage and backup code and the milestone card are untouched. No TD or TEST entries were added; this file is the record.

The use case: walk through the schedule, record progress, then share the updates as something the receiver can read without the app.

## What changed

### 1. The button

- `#btn-share-report` ("Share", with an upload icon) sits in `.rpt-hd-actions`, straight after + Milestone, so the group reads filter toggle, + Milestone, Share. It is anchored left like the rest of the group since P75.
- It is the group's one primary button (`.rpt-hd-primary`). It takes the primary button tokens (`--color-btn-primary-*`), so it follows both themes.
- `syncShareReportBtn()` is the only code that writes its `disabled` and `title`. `syncEmptyState()` calls it on every rebuild and at INIT. While the dashboard is empty, the button is disabled and its tooltip says why: "nothing to report yet. Import a schedule or add a milestone first."

### 2. The dialog

- `#share-dialog` and `#share-scrim` reuse the add-milestone dialog's classes: centred, modal, a scrim behind it. The only new CSS is `.share-check`.
- **Period** (`#share-period`):
  - the current report period comes first and is the default (`reportPeriodISO()`, shown with `fmtPeriod()`);
  - then any earlier period that has entries;
  - then All periods.
- **From** (`#share-from`): free text. It is remembered as display state in `localStorage` under `sret-report-from`, the same way the other `sret-*` view settings are. It goes into the report as "Prepared by".
- **Include Excel detail** (`#share-xlsx`): on by default.
- **Share** (`#share-go`) and **Download** (`#share-download`):
  - Download always downloads.
  - Share uses `navigator.share` when `navigator.canShare({files})` accepts the files. It sends both files together if the share sheet takes both. If it takes the report alone, the report is shared and the workbook is downloaded. If it takes neither, both files are downloaded.
  - If the person cancels the share sheet (`AbortError`), nothing else happens. Any other share failure falls back to download.
- Esc and the scrim close the dialog. It is in `chromeAwayBlocked()`'s list, so the heading does not scroll away while it is open.

### 3. The report page

`buildShareReportHtml(shareReportModel(period, from))` produces one self-contained `.html` file:

- inline CSS only;
- no script;
- no app code and no raw state;
- no external reference.

The file is named `<Title>_Report_<W/E ISO date>.html`. `<Title>` is the board heading as shown (`#rpt-title-text`, which is what publish reads too), reduced to letters, digits, `_` and `-` (`shareFileStem()`). With All periods, the date in the file name is the current period's W/E date.

Sections:

1. **Header.** The board heading, then Project, Report period (W/E, or "All periods (to W/E ...)"), Report date, Schedule data date (`DATA_SOURCE`, else the baseline's), Prepared by, and the generated date and time.
2. **At a glance.**
   - Stat tiles for Complete (DONE and DONEUSER), On track, At risk, Critical and Future.
   - A Not rated tile appears only when some milestone is N/A.
   - A second row of tiles: milestones updated, and follow-ups open (`open`, `review`, `outstanding`), sent and done (`done`, `closed`), for the entries in the period.
   - The tiles are CSS grid and need no script.
3. **Updates this period.**
   - One card per updated milestone.
   - Each change is shown as `label old → new`, then the comment, "Follow-up: <status>", and who and when.
   - All of this is built from `ENTRIES` for the period. Entries coalesced at save time are already one entry, so they count once.
4. **Attention.** Every At risk or Critical milestone on the board, by finish date. Each row shows the finish (marked "(edited)" when the finish is an override), the float (`n/a` for user milestones) and the latest comment (`SRETEntries.rollup(...).lastText`).
5. **New milestones proposed.** Every user milestone (`USR-`), with its start, finish and status. `USER_MILESTONES` records carry no creation time, so this section lists them all, whatever period is chosen.
6. **Footer.** "Prepared with Milestone Dashboard {APP_VERSION}. Dates are as at the schedule data date; edited dates are proposals, not changes to the master schedule."

An empty section says so ("No updates this period", "No milestones at risk or critical", "No new milestones proposed"). No section is ever left out.

Layout:

- The page is at most 960px wide.
- Below 600px, the tables turn into labelled rows (`data-l`), so nothing scrolls sideways at 390px.
- Print CSS:
  - `@page` margins;
  - headings kept with what follows them;
  - update cards, tile rows and table rows never split across pages;
  - table headings repeated on each page;
  - tile and comment fills printed.

The finished string has every em and en dash replaced with a hyphen, so text typed into a remark cannot bring one in.

### 4. The Excel detail

- `src/modules/notes-export/notes-export.js` (`SRETNotesExport`) is now pasted into the app script, unchanged from its source file, straight after the update history module. It sits between the `NOTES EXPORT MODULE` banners.
- `buildShareWorkbookAoA(period)` calls the module with:
  - `rollup`: `SRETEntries.rollup`, using the kind of the group's own entries;
  - `msLookup`: the board's ID and name;
  - `sourceOf`: the schedule's start, finish and progress, and its state as a health code;
  - `periodFilter`: the chosen period, or none for All periods;
  - `fmtDate`: `fmtTipDate`.
- The output is a workbook of two sheets:
  - **Summary:** one row per milestone and period with updates, giving each field's schedule value and its rolled-up new value.
  - **Log:** one row per entry.
- The workbook is named `<Title>_Updates_<W/E ISO date>.xlsx`. SheetJS is the embedded copy (`vendor-sheetjs`). If that copy is missing, the report is still produced and the status line says the workbook could not be built.

### 5. Module fix: dependency keys

The app files a dependency remark under `pred:A->B` or `succ:A->B`. `identify()` split the key on the arrow but kept the side prefix, so the ID read `pred:A1000 → A2000`. It now removes `pred:` and `succ:` first. Three assertions were added to `tools/notes_export_test.mjs`.

The module's own em and en dash regex is now written as `—` and `–` escapes, so the app gains no literal em dash from the paste. Dependency remarks are not entries yet (P66 scope), so the fix only matters once they are.

## Decisions

- **Ordering: newest first.** Updates are ordered by each milestone's last save, newest first, with the Activity ID breaking a tie. This is the update history module's order, and the receiver reads the latest change first. The Attention section already groups the milestones that need someone.
- **One card per milestone.** All of a milestone's entries in the period roll into one card:
  - each field goes from its first `from` to its last `to`;
  - a field moved and then moved back drops out;
  - the comment is the latest remark (or "Remark cleared");
  - the follow-up status, author and time are the latest entry's;
  - "(N updates)" is shown when there was more than one entry.
- **Labels are the update history module's.** The cards go through `SRETHistory.entryView` and `historyEntriesView`, so the report reads exactly like the card's Update history. That means "End date", "Start date", "Health" and "Progress", where the brief gave "Finish date" and "Status" as examples. The module's wording won because the brief also said to use the same labels as the update-history module.
  - One deviation: a health value of null means automatic. The module shows that as "none". The report shows the schedule's own status instead, for example "On track (schedule)".
- **Counts are the board's.**
  - A milestone is counted when it is inside the board's week range, so the tiles equal the markers the board draws. Filters do not change the count.
  - A milestone outside the week range is not counted. A line under the tiles says how many there are. The fixture has two, completed in May, before the first column.
- **Colour audit: the report palette is counted as a token block.**
  - The report is a separate file and cannot read the app's theme tokens. Its colours are a small palette in its own `:root{}` (`--rpt-*`), defined once in the `REPORT_PALETTE_CSS` constant. The rest of the report CSS uses only those tokens.
  - Before P77, `colour_audit.py --strict` did not see a literal in a plain JS string at all. It only scanned style-shaped contexts (`cssText`, `.style.x`, colour-keyed object literals, template-literal markup).
  - The audit now flags every hex, `rgb()` and `hsl()` literal anywhere in the app script (`literal-js-string`), with one exception: the `--rpt-*` token values inside `REPORT_PALETTE_CSS`. Those are reported as "Report palette tokens (REPORT_PALETTE_CSS, counted as token definitions)", not as violations.
  - A literal anywhere else is a violation, and so is a non-`--rpt-*` literal inside that constant. This was tested against a copy with one of each planted: both were caught, and the run exited 1.
  - The app script had no such literal before this change, so the stricter scan adds no debt. `--strict` stays at 0.
  - The report is light-only on purpose: it is a document for print and email, not a themed view.

## Verification

`tools/p77_share_report_check.py` uses headless Chromium and the fixture. `--save DIR` also writes the sample report and its screenshots. Its stages:

- **Empty app (`sret:no-fixture`).** The button is in the group, shown, disabled, with the tooltip. Neither a click nor `openShareDialog()` opens anything.
- **Fixture, 1440.**
  - The button's position, icon, label and primary background.
  - N=3 updates are seeded through `addEntry`, the card's entry path:
    - a finish moved two weeks (follow-up open);
    - a health change to At risk (sent);
    - a comment (done);
    - plus a second card save on the first milestone inside the coalescing window, which counts once.
  - The dialog, driven by clicks: the default period, All periods offered, Excel detail on, From typed and remembered.
  - Share with `canShare` true: one call, both files, correct names and types.
  - `canShare` false: no share, two downloads.
  - `canShare` true for one file: the report is shared and the workbook downloaded.
  - Download: never shares; with Excel detail off, the report only.
  - All periods.
  - Esc closes the dialog.
  - The workbook is parsed back with the embedded SheetJS:
    - the sheet names are Summary and Log;
    - Summary rows equal the updated milestones;
    - Log rows equal the period's entries;
    - the finish and status roll-ups are correct;
    - no cell holds an em dash.
  - Captured files are read synchronously from the intercepted Blob and File parts. An async `blob.text()` let headless virtual time run on, so the DOM was dumped before the probe finished, intermittently.
- **The report HTML.**
  - Every heading and header field, the From value, the footer line.
  - The three updates, each with its label and its old → new value. The coalesced comment appears once.
  - Newest first.
  - The tiles equal the board's own markers by state, and the total is right; the off-board line.
  - Milestones updated and follow-up counts.
  - Attention complete, with the changed milestone in it.
  - The empty "New milestones proposed" message.
  - No `<script`, no em or en dash, no `src`/`href`/`url()`, no app code or state.
  - Under 400 KB, and the palette is in its own `:root`.
- **The report on its own.**
  - At 390 and 1440: no error caught in the page or in Chromium's console log, no horizontal scroll, nothing past the right edge, every section visible.
  - At 703px (A4 printable width at 96 dpi) with the page's `@media print` rules applied: no overflow; headings `break-after: avoid`; cards, tile rows and table rows `break-inside: avoid`; table headings repeat.
  - Chromium `--print-to-pdf` produces a PDF.

Not verified: the share sheet on a real Android or iOS device. The check stubs `navigator.share` and `navigator.canShare`. Which file types a platform's share sheet accepts is decided by the platform. Chromium on Android is understood to accept `.html` but not `.xlsx`; in that case the report is shared and the workbook downloaded, which is the one-file path above. That behaviour on the device has not been observed.

## Files

- `src/milestone-dashboard.html`:
  - the button and its CSS;
  - the dialog;
  - the `P77: SHARE REPORT` block after `doPdfExport()`;
  - the notes-export paste;
  - one call in `syncEmptyState()`;
  - `share-dialog` added to `chromeAwayBlocked()`.
- `src/modules/notes-export/notes-export.js`: the `pred:` / `succ:` fix and the escaped dash regex.
- `tools/notes_export_test.mjs`: dependency-prefix assertions.
- `tools/colour_audit.py`: the script-wide literal scan and the report palette allowance.
- `tools/p77_share_report_check.py`: new.
- `docs/mockups/P77/`:
  - `sample-report.html`, generated from the fixture by the check;
  - `sample-report-390.png`;
  - `sample-report-1440.png`.
