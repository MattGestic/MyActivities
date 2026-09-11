# P6 Milestone Dashboard — Test Log

## AI / Automated Tests (Gate 5a — mandatory before any live user test)

| ID | Date | Scope | Framework used | Pass/Fail | Defects raised |
|---|---|---|---|---|---|
| TEST-01 | 2026-09-09 (pre-migration) | Full regression audit of v3.1.0-P1 against every major feature built across the chat development history. Direct file inspection, not assumed. | Feature-presence checklist | Pass — no drops or regressions | None |
| TEST-02 | 2026-09-10 | Live ingest of `data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx` through the `.xlsx` import path | `tools/import_check.py`, EARS | **Mixed** — 8 pass, 1 fail, 1 not testable here, 1 criterion was itself wrong | TD-15, TD-16, TD-17 |
| TEST-03 | 2026-09-09 | Post-migration smoke test: does the committed `src/milestone-dashboard.html` still open and render the baked-in baseline correctly after the file move | Headless Chromium render, DOM assertion | Pass | None |
| TEST-04 | 2026-09-09 | Tokenization audit reproducibility: does an independently written implementation of the documented audit method reproduce the v1 Measurement Log figures | Reconciliation against v1 output | **Fail** — v1 figures not reproducible at full documented scope | TD-06, TD-07 |
| TEST-05 | 2026-09-09 | Theme toggle: does every probed element's computed colour change between light and dark, before and after the v3.1.0-P2 tokenization pass | `tools/theme_check.py`, computed styles, EARS | Pass after fix (before: 7 of 16 frozen) | None outstanding |
| TEST-06 | 2026-09-09 | Post-change regression: does the dashboard still render the baked-in baseline unchanged after the tokenization pass and version bump | Headless Chromium render, DOM assertion | Pass | TD-10 raised from the finding below |
| TEST-07 | 2026-09-10 | Board tokenization: do rows, columns, marker labels, icons and status toggle correctly, and does any text lose contrast against its own background | `tools/theme_check.py` with board probes + WCAG contrast, EARS | Pass after one revert | None outstanding |
| TEST-08 | 2026-09-10 | Post-change regression after the v3.1.0-P3 board pass | Headless Chromium render, DOM assertion | Pass | None |
| TEST-09 | 2026-09-10 | Row model: one row per deliverable, stage chains collapsed. Run against two independent datasets, the PFS `.xlsx` and a 2857-activity EPCM `.xer` | `tools/import_check.py` + `tools/xer_to_aoa.py`, EARS | **Pass on PFS, no effect on EPCM** | TD-20 |
| TEST-10 | 2026-09-10 | Mixed row-aggregation strategies selected per band (stage / tag / area / system / activity), against both datasets | `tools/import_check.py` + `tools/xer_to_aoa.py`, EARS | **Pass** — PFS unchanged at 115 rows, EPCM 2857 to 1948 | None outstanding |
| TEST-11 | 2026-09-10 | Chain-first stage merging, against two reported failures (Bronson Connector Road, Snip Single Line Diagrams) plus the two over-merge guards | `tools/import_check.py`, targeted ID probes | **Pass** — PFS 115 to 110 rows | None outstanding |
| TEST-12 | 2026-09-10 | Dependency-first row building (pass 1 logic, pass 2 deliverable identity), 8 over-merge guards and 8 chain probes, both datasets | `tools/import_check.py` + `tools/xer_to_aoa.py`, targeted ID probes | **Pass** — 8/8 guards, PFS 110 to 108 rows, EPCM 1948 to 1898 | TD-26 |
| TEST-13 | 2026-09-10 | Convergence relaxation (a high-fan-in milestone stands alone only above a measured predecessor threshold), row numbers per banding, and milestone drag between rows driven by real pointer gestures | `tools/import_check.py` + synthesised `PointerEvent` gestures in headless Chromium | **Pass** — 8/8 guards, PFS 108 to 105 rows, drag verified on both input paths | TD-28, TD-29 |
| TEST-14 | 2026-09-10 | Mount manager (three slots, unmount/remount), model export identity and naming, payload validation, and selective annotation import | `tools/import_check.py` harness driving the real panel, export and validator; export round-tripped back through its own validator | **Pass** — 3/3 slots, 5/5 rejection cases, selective import isolates a single category | TD-30 (closed same pass), TD-31, TD-32, TD-33 |
| TEST-15 | 2026-09-10 | Import failure handling: what the UI does when a file cannot be read, and whether a failure clears the previous file's state | Real `File` objects through `handleFile()` in headless Chromium, with the SheetJS CDN unreachable | **Pass after fix** — 4/4 cases; reproduced the reported symptom first | TD-34, TD-35 (both closed same pass), TD-36 |
| TEST-16 | 2026-09-10 | Read-error diagnosis: does each `FileReader` `DOMException` produce its own cause and remedy, and does a transient failure recover on retry | `FileReader` stubbed to force a named exception a set number of times | **Pass** — 4 error names each diagnosed, retry recovers silently | TD-37, TD-38 (both closed same pass) |
| TEST-17 | 2026-09-10 | Data date: placement under step 1, label, previous-Friday default across every weekday and at month/year boundaries, and that editing still drives ingest | Node for the date arithmetic, headless DOM probe for placement and wiring | **Pass** — 7/7 weekdays, 3/3 boundaries, field visible with no file loaded | TD-39 (closed same pass) |
| TEST-18 | 2026-09-10 | Does a real click on the Import button complete an import, and is the form correctly torn down afterwards | Real `.click()` on the rendered button, in a normal page and inside an `about:srcdoc` iframe matching the user's viewer | **Pass after fix** — reproduced the stale form; second press now impossible | TD-40 (closed same pass) |
| TEST-19 | 2026-09-10 | Publish round trip: does a published file open cold with the schedule, timeline and annotations already in place, and does it carry nothing it should not | Publish captured at the Blob boundary, written to disk, then loaded as a separate page | **Pass after two fixes** | TD-41, TD-42 (both closed same pass), TD-43, TD-44 |
| TEST-20 | 2026-09-11 | Does a published file describe itself correctly: mount slots, baseline counts, and the header provenance line | Publish probe extended to capture all three mount slots and the header meta | **Pass after fix** — reproduced the user's report first | TD-47, TD-48 (both closed same pass) |
| TEST-21 | 2026-09-11 | Six requested changes: published schedule as the update, Source cell after a drag, empty-row delete, gutter alignment, column master toggle scope, header chrome colour | Publish round trip plus a combined DOM probe driving each interaction | **5 pass, 1 delivered failing** — the requested `#f4f5f8` is 1.79:1 on the light header | TD-50 (open), TD-51 to TD-55 (closed) |

### TEST-13 detail

Three separate changes, verified separately.

**1. Convergence relaxation (TD-26).** A milestone with in-band predecessors in
more than one row was always split into its own row. That put "Site Plan
-Client Review" on a standalone row, which was reported as wrong: the intent is
to isolate milestones that carry real dependent weight, not any milestone whose
two predecessors happen to sit in different rows.

The threshold was chosen from the measured distribution of total predecessors
across the 146 activities in the reference export, not picked:

| Total predecessors | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 9 | 14 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Activities | 11 | 67 | 36 | 13 | 8 | 3 | 1 | 1 | 3 | 2 | 1 |

0 to 4 covers 124 of 146 (85%), then the tail thins out. The natural cut is at
5 or 6. **6 was chosen, not 5**, because `SNIP-161` "MEL - Issue for Client
Review" sits at exactly 5 and belongs in the Mechanical Equipment List chain; a
threshold of 5 would have pulled it out and traded one reported defect for
another. The external-share condition (30% of predecessors outside the band) is
a second, independent route to standalone, so a milestone drawing widely from
elsewhere still separates even below 6.

Measured outcome, PFS reference export:

| Probe | Before (P7) | After (P8) |
|---|---|---|
| Rows | 108 | 105 |
| `SNIP-189` Site Plan -Client Review | standalone | merged with `SNIP-300` Preliminary Overall Site Plan |
| `SNIP-161` MEL - Issue for Client Review | in the 5-marker MEL chain | unchanged |
| `SNIP-255` / `SNIP-258` Draft Report (14 and 7 predecessors) | — | still grouped, above threshold but name-compatible |
| Bronson Connector Road chain | 4 markers | 4 markers |
| Snip Single Line Diagrams chain | 4 markers | 4 markers |
| Over-merge guards (7 Stage Gate approvals + Draft TOC) | 8/8 standalone | 8/8 standalone |

**2. Row numbers.** 105 of 105 imported data rows and 159 of 159 baseline rows
render a number, restarting at 1 in each of the 14 bandings. The number is a
flex slot beside the health dot rather than a text prefix, because the drag
handle lands in the same slot in the next stage.

**3. Milestone drag.** Verified by dispatching real `PointerEvent`s, not by
calling the handler:

| Assertion | Mouse | Touch |
|---|---|---|
| Arms on `pointerdown` | yes | yes |
| Does not drag under the 4px threshold | yes | n/a |
| Early move stays a page scroll, drag disarmed | n/a | yes |
| Drag starts after the 400ms hold | n/a | yes |
| Ghost follows the pointer | yes | yes |
| Row under the pointer highlights as the drop target | yes | yes |
| Marker lands in the target row | yes | yes (0 to 1 markers) |
| Click suppressed so the dialog does not open | yes | yes |
| Ghost hidden and all drag state cleared on drop | yes | yes |

The target row re-lays itself out because the drop calls `scheduleRerender(true)`
and the existing three-band label-collision system runs again. Proven by moving
a marker into a row holding a marker one column away: the target row went from
`mid` to `mid, top`, so the incoming marker was pushed to a different vertical
band rather than overlapping.

Annotations survive a move. `msKeyFor()` falls back to a composite embedding the
row ref when a milestone carries no SNIP id, so a move would silently orphan
that milestone's health override, comment and short title. `moveMilestoneToRow()`
re-points all three stores; the probe sets all three, moves the milestone, and
asserts they are readable under the new key and gone from the old one.

**Defect found and fixed during this test.** `.row-num` was first written with
`--color-text-faint`, which measures **1.99:1** on a dark row. The contrast check
did not catch it, because it skipped any element with a transparent background,
and a row number has no background of its own. The checker now resolves a
transparent element to its nearest painting ancestor, which reproduced the
finding; the token was changed to `--color-text-muted` (4.68:1 light, 5.18:1
dark), the same token `.remarks` already uses on that surface. Raised as TD-28.

That change also surfaced two findings on `.s-track` and `.s-future`, which were
**probe artifacts, not defects**: both probes wrapped the class around a literal
"x", and querying the rendered board confirmed neither class is ever applied to
text anywhere in the app. The probes now carry no content, so the toggle
assertion still holds and no impossible text case is measured.

### TEST-14 detail

**1. Mount panel.** Three fixed slots render on a clean load and after an
import. Baseline is listed with zero action buttons, which is the assertion
that it cannot be unmounted. Importing the reference export flips the schedule
slot to an `override active` badge carrying file name, data date (29-Aug-26),
report date and load time, with the baseline still listed above it at
15-Aug-26 — so the override reads as an override rather than as the only
source. Unmount reverts to baseline (159 tasks / 198 milestones, `SEED_*`
untouched) and the slot returns to a Mount button.

**2. Export identity and naming.** `exportModel()` was captured at the Blob and
anchor boundary rather than by inspecting the code:

| Assertion | Result |
|---|---|
| Filename matches `eskay-dashboard_model_<data date>_<stamp>.json` | `eskay-dashboard_model_2026-08-29_20260910-1600.json` |
| `kind` | `eskay-milestone-dashboard-model` |
| `schemaVersion` | 1 |
| `exportedAt` present | yes |

**3. Validation.** Driven by feeding a real export straight back into the
validator, plus four constructed failures. Nothing in the validator reads the
filename; all five verdicts come from payload contents.

| Case | Verdict |
|---|---|
| Real export, matching schedule | accepted, no warnings |
| Malformed JSON | rejected, parse error surfaced |
| `kind` of another producer | rejected, names the kind it found |
| `schemaVersion` 99 | rejected, names both versions |
| Valid but carries no annotations | rejected |
| Legacy export with no identity block | accepted with a warning, read on contents |

The data-date mismatch check was tested in **both** directions, because a
warning that only ever stays quiet is indistinguishable from dead code:

| Payload | Warning |
|---|---|
| `scheduleDataDate` matches what is mounted | none |
| `scheduleDataDate` 2026-07-04 against 29-Aug-26 mounted | fires, naming both dates |
| Field absent (legacy) | none, check skipped rather than guessed |

**4. Selective import.** The dialog lists six categories with live counts and
disables the ones the file cannot supply. With all three annotation stores
cleared, only "Milestone comments" was ticked:

| Store | After importing comments only |
|---|---|
| `MS_COMMENTS` | 1 |
| `MS_HEALTH_OVERRIDE` | 0 |
| `MS_SHORT_TITLES` | 0 |
| `ANNOT_MOUNT.applied` | `['comments']` |

The annotations slot then shows the file, the data date it was saved against,
its export time, its load time, and what was actually imported from it.

**Defect found and fixed during this test.** Two, both mine, neither visible by
reading:

- The mismatch warning first compared `p.dataDate` — which is the week-ending
  **label** of the now column ("13-Sep"), not a data date — against a real data
  date, so it fired on every clean round trip. A `scheduleDataDate` field was
  added and the comparison moved onto it.
- `.mnt-name` was written with `--color-text-small` (**1.18:1** on a dark card)
  and `.mnt-badge` with `--color-purple-dark` on the accent wash (**1.13:1**).
  TD-28 had already named the first token by value. Reading the CSS did not
  catch either; the probes did. Raised as TD-33.

**Pre-existing defect found.** `LAST_MARKUP_AT` was assigned but never
declared, so it existed only as an implicit global **after** the first markup
edit. `exportModel()` reads it, so exporting on a clean load threw a
`ReferenceError` and the download silently never happened. It survived this
long because every manual export test had made an edit first. Declared and
closed as TD-30.

### TEST-15 detail

Raised by the user as "the import button doesn't show when a file is uploaded".
**Reproduced before changing anything**, by pushing real `File` objects through
`handleFile()` with the SheetJS CDN unreachable — which is what a locked-down
network, an offline machine, or a strict policy on a `file://` page all look
like.

**Reproduction, on the build as shipped:**

| Observed | Value |
|---|---|
| `2 · Map columns` section visible | no |
| Import button present in the DOM | no |
| Only signal | `ingest-status`, 9.5px italic |
| Its text | "SheetJS could not be loaded (offline?). Save the schedule as CSV and use the paste box." |

The button was never broken. The `.xlsx` load failed, `showMapper()` was never
reached, and the step that renders the button rendered nothing. Because that
step is labelled "Appears once a file loads", its absence reads as a broken
control rather than as an error.

**A second, more dangerous defect surfaced while reproducing.** Loading a good
file and then a bad one left the good file's column mapping and Import button
on screen, because each failure path called `setIngestStatus(...)` and returned
without clearing `LAST_PARSE`. The board would import file A while naming file
B. Raised as TD-34.

**After the fix**, all four cases measured:

| Case | Import button | Map section | Failure block |
|---|---|---|---|
| Clean load, `.xlsx`, CDN blocked | hidden | hidden | shown, with the reason and two actions |
| Good CSV after that failure | **shown** | shown | cleared |
| Bad file after a good one | **hidden** | hidden | shown (TD-34: was previously still offering Import) |
| File with no data rows | hidden | hidden | shown |

The failure block names the file, states why it failed, says that mapping and
the Import button stay hidden until a file reads cleanly, and offers "Use the
paste box instead" and "Pick another file". The SheetJS message was rewritten
to say what actually happened and what still works, rather than guessing
"(offline?)".

Two probe runs initially showed the CSV cases failing. That was the probe, not
the app: `FileReader` callbacks had not fired inside the 700ms wait under
Chromium's virtual-time budget. Extending the wait showed all four correct.
Recorded because the first reading looked like a real regression and would have
been reported as one.

### TEST-16 detail

The user hit a real failure on their own `.xlsx` and sent a screenshot. The
message read "The file could not be read from disk." and the block offered only
"Pick another file". Both details identify the path exactly: `FileReader.onerror`
on the workbook branch, with `offerPaste` false.

**That rules out the CDN.** `ensureXLSX()` had resolved, so SheetJS loaded fine
and TD-36 was not the cause — the prediction made when P10 shipped was wrong,
and the error name would have said so on the first screenshot had it been shown.

Forced each `DOMException` by stubbing `FileReader`:

| Forced name | Reported as | Hints | Retry attempts |
|---|---|---|---|
| `NotReadableError` | "Windows would not let the browser read the file" | open in Excel / cloud-only OneDrive / antivirus | 2 |
| `NotFoundError` | "The file was not there when the browser went to read it" | moved or renamed / sync replaced it | 2 |
| `SecurityError` | "The browser was not permitted to read the file" | policy blocking / copy it locally | 2 |
| unrecognised name | generic, but still names the exception | close it elsewhere / OneDrive download | 2 |

Transient case, failing once then succeeding: failure block never shown, Import
button appears, 2 attempts. So a placeholder that hydrates on the second try
costs the user nothing.

Paste is now offered on this path. Withholding it in P10 was wrong: a file that
cannot be READ says nothing about whether the app can handle the data once it
has it.

The TEST-15 suite was re-run and initially showed two cases failing again. Same
`FileReader` virtual-time artifact as before, now needing a longer wait because
the sequence is longer. At 4000ms all four are correct. Recorded a second time
because it has now misled twice.

### TEST-17 detail

**Placement.** Measured on the rendered DOM, not from the markup:

| Assertion | Result |
|---|---|
| Label | "Data date" |
| Inside the Import section | yes |
| Inside `advanced-input-wrap` (hidden until a file loads) | no |
| Visible with no file loaded | **yes** (previously not) |
| Precedes Report date | yes |
| Precedes the file picker | yes |

**Previous-Friday default.** The arithmetic was checked across a whole week and
across boundaries rather than on one sample date:

| Day | Resolves to | Days back |
|---|---|---|
| Sun 6 Sep | Fri 4 Sep | 2 |
| Mon 7 Sep | Fri 4 Sep | 3 |
| Tue 8 Sep | Fri 4 Sep | 4 |
| Wed 9 Sep | Fri 4 Sep | 5 |
| Thu 10 Sep | Fri 4 Sep | 6 |
| **Fri 11 Sep** | **Fri 4 Sep** | **7** |
| Sat 12 Sep | Fri 11 Sep | 1 |

Month and year boundaries: 1 Jan 2026 → 26 Dec 2025; 1 Mar 2026 → 27 Feb 2026;
3 Jan 2027 → 1 Jan 2027.

**Assumption, stated because it is a real choice.** "Previous Friday" is read as
the most recent Friday *strictly before* today, so on a Friday it returns the
week before. A weekly update is cut to the week just closed, and that day's own
update does not exist yet in the morning. A project that cuts its update on
Friday itself would want same-day instead.

**Wiring.** The visible field and the hidden `cfg-datadate` the ingest reads both
initialise to the computed default and match; editing the visible field still
mirrors into the hidden one (`2026-08-28` in, `2026-08-28` out).

**One probe assertion was wrong, not the code.** A check for "no stale `2026-07-29`
literal" scanned the whole document and failed on a genuine baseline milestone
date (SNIP-110) and on the explanatory comment. The default itself is computed.

### TEST-18 detail

Reported as "Import button doesn't click", with a screenshot showing the status
line reading a **completed** build ("Built 105 deliverables / 146 milestones
from 146 activities") while the form below still read "Ready to import" with
Discard and Import. Those two states are contradictory under the code as
written, which is what pointed at the defect.

**A real click was tested, not a direct call to `runIngest()`.** In a normal
page it worked: 159 tasks to 105, `DATA_SOURCE.mode` baseline to update, 105
rows rendered, no errors. So the button and its handler were never broken.

The screenshot's page was `about:srcdoc`, so the same test was run inside an
iframe with the app in `srcdoc`, matching the viewer:

| Measure | Before fix | After fix |
|---|---|---|
| Import completes on click | yes (159 to 105) | yes (159 to 105) |
| `map-wrap-section` hidden afterwards | yes | yes |
| **"Ready to import" panel cleared** | **no** | **yes** |
| Import button still present afterwards | **yes** | no |
| Second press | does nothing | not possible |
| Uncaught errors | none | none |

`runIngest()` hid the mapper and nulled `LAST_PARSE` but never cleared
`import-summary-wrap`; `cancelIngest()` did. So a finished import looked
unfinished, and pressing Import again hit `if(!LAST_PARSE)` and returned
silently. The first press had worked.

`runIngest()` with nothing staged now reports which file is already mounted
rather than "Nothing parsed yet.", verified by calling it bare after a
successful import: it explains itself and leaves the 105 tasks untouched.

**The `Uncaught TypeError: Cannot set properties of null (setting 'onclick')` in
the screenshot is not from this app.** It is reported at `about:srcdoc:6806`;
the file is 5935 lines, and the app's only two `.onclick=` assignments are both
made on elements created by `createElement` in the same statement, so neither
can be null. Reproducing the app inside a `srcdoc` iframe produced no errors at
all. The error comes from the viewer's own injected script.

### TEST-19 detail

The publish path is only meaningful end to end, so the test publishes a file,
writes it to disk, and opens **that file** as a separate page. Nothing is
asserted about the publishing page.

**Round trip, measured on the published file at load:**

| Assertion | Result |
|---|---|
| Deliverables / milestones | 105 / 146, matching what was published |
| Rows rendered from a cold start | 105 |
| Markers rendered | 143 |
| Timeline preserved | 39 week columns, now-column 14 |
| `BASELINE_TIMELINE` replaced, not just the live one | 39 labels |
| Data date field | 2026-08-29, the published date |
| Comments / health / short titles / dependency visibility | 1 / 1 / 1 / 1 |
| Import form offered on load | no |
| Uncaught errors | none |
| Script tags in the file | 2 (`#app-script`, `#published-state`) |
| Tab title still carries `APP_VERSION` | yes |

Published size 530 KB against a 435 KB source; the state block is ~94 KB.

**Two defects found, both real, both raised.**

**TD-41.** `const MS_COMMENTS={}` was declared *after* the init block, so
`applyPublishedState()` — called from init — hit a temporal dead zone on it and
threw. The catch turned that into a partial restore: the timeline, tasks and
source applied, everything after the throw did not. The board looked correct
while the data date field and published metadata were quietly wrong. Second
instance of the class TD-30 raised.

**TD-42.** `publishDashboard()` cloned every `script` element in the DOM. Any
script injected by a browser extension, a document viewer wrapper, or a
debugging snippet would be **baked into a file that then gets uploaded to
SharePoint and opened by other people**. The app's script now carries
`id="app-script"` and publish drops every other script, logging the count.

**A long detour worth recording.** The page title in the published file kept
losing its version, and this was investigated as a product defect across several
rounds — top-level error capture, a `document.title` property trap, isolating
the state block. The cause was the test harness: `import_check.py` injects its
script into the page, publish cloned the live DOM, and the harness therefore
ended up inside the published file and re-ran on load, calling `setReportTitle`
and overwriting a title the product had set correctly. The harness was proving
the feature worked and breaking it in the same step. It was only worth the cost
because it exposed TD-42 underneath.

### TEST-20 detail

Reported as "I uploaded and saved it as a new dashboard, the current I had
loaded didn't save into the copy." **It had saved.** The published file held 105
tasks, 146 milestones, 105 rendered rows, 143 markers and all four annotation
stores. What failed was everything that *describes* the file.

Reproduced by extending the publish probe to read the mount panel and header:

| Surface | Before | After |
|---|---|---|
| Baseline slot counts | 159 / 198 (the original seeds) | **105 / 146** |
| Baseline slot badge | `embedded` | `published` |
| Baseline provenance | none | "Built into this file on … (v…)" |
| Header baseline | "Baseline DD 15th Aug" | "Published DD 29-Aug-26" |
| Header update | "No update imported" | "Built into this file" |
| Schedule slot | "Nothing mounted / Showing the embedded baseline" | "No override mounted / The published schedule above is what this file shows" |

Each old value was literally true of the internals — there genuinely is no
mounted update in a published file, and `SEED_*` genuinely is the embedded data
— and every one of them was wrong about what the user had just done.

Root causes: `renderMounts()` read `SEED_TASKS`/`SEED_MILESTONES` rather than
`BASELINE_TASKS`/`BASELINE_MILESTONES`, which are the same in a shipped build and
different in a published one; `BASELINE_LABEL_TEXT` was a `const` the publish
path never updated; and two strings were worded for the non-published case only.

**Why it shipped:** TEST-19 asserted the payload and the rendered board, never
what the UI said about them. The probe now captures all three mount slots and
the header meta line, and the non-published panel is asserted in the same run so
the two wordings cannot drift.

### TEST-21 detail

**1. Published schedule installs as the update, not the baseline.** Overwriting
the baseline destroyed what the baseline is for. Measured on a published file
opened cold:

| Assertion | Result |
|---|---|
| `VIEW_MODE` on load | `update` |
| Update toggle enabled and active | yes / yes |
| `UPDATE_TASKS` | 105 |
| `BASELINE_TASKS` / `BASELINE_MILESTONES` intact | **159 / 198** |
| Baseline slot | `embedded`, 159 / 198 |
| Schedule slot | `published`, the source file, 105 / 146, "Built into this file on…" |
| Header baseline | "Baseline DD 15th Aug" |

**2. Source cell follows a dragged milestone.** Moving `SNIP-142` from its own
row into the `SNIP-152` row: source row `"SNIP-142"` → `""`, target row
`"SNIP-152"` → `"SNIP-142, SNIP-152"`.

**3. Empty-row delete.** The control appears on the emptied row and not on the
populated one; deleting took `TASKS` 105 → 104, removed the row from the DOM,
and removed it from `UPDATE_TASKS` so it does not return on the next rebuild.

**4. Gutter.** `.row-gutter` renders with the row number and health dot as its
only children, at a fixed width so names align across 1- and 3-digit numbers.

**5. Column master toggle.** "Hide All Columns" hides the ref column
(`refColHidden: true`) while milestone labels stay visible and the label toggle
stays checked. Previously `btn-lbl` and `btn-mhrs` were in its id list.

**6. Header chrome colour — delivered, and failing the gate.** `#f4f5f8` was
applied to the icon-bar version label and the report subtitle as requested.
Measured:

| Surface | Contrast |
|---|---|
| `#f4f5f8` on dark header `#15182F` | 16.00:1 |
| `#f4f5f8` on light header `#a6bbdc` | **1.79:1** |

Neither element had a probe, which is why the surface was already wrong and
nobody had seen it: the previous values measured 1.5:1 (`--color-text-note`) and
2.40:1 (`--color-text-muted`). Probes added, so the contrast pass now **fails**
at 1.79:1 and has been left failing rather than suppressed. TD-50 carries the
decision: darken the header, or keep it light and use a dark token.

### TEST-05 detail

`tools/theme_check.py` injects a probe into a temporary copy, flips `data-theme` between light and dark, and reads `getComputedStyle` for colour, background, all four borders and outline on each probe. It is a measurement of the rendered result, not of the CSS text.

| | Before | After |
|---|---|---|
| Probes expecting to toggle | 16 | 16 |
| Toggling correctly | 9 | **16** |
| Frozen (identical in both themes) | **7** | **0** |
| Constant by design, correctly frozen | 1 | 1 |

Frozen before the fix: `.sticky-search-icon`, `.sticky-search-clear`, `.s-track`, `.s-future`, `.dep-tooltip`, `.dep-comment-close`, `.dep-comment-ids`.

**Worst case, and the reason this mattered:** `.dep-comment-panel` had its background reading a token that toggles to `rgba(253, 253, 252, 0.92)` in light mode, while its text stayed frozen at `rgb(232, 238, 248)`. Near-white text on a near-white panel. The dependency comment panel was effectively unreadable in light theme.

Two control probes (`#icon-bar`, `body`) were already tokenized and toggled in both runs, which is what proves the harness detects a real difference rather than reporting everything as frozen.

**One false-positive class was found and excluded before any code changed.** The audit initially flagged five `.rpt-hd` literals as theme-blind. They are `var(--token, #fallback)` fallbacks, which resolve only when the token is undefined and therefore still follow the toggle. Acting on them would have meant changing code that already worked. `tools/colour_audit.py` now detects the fallback position and reports it separately.

### TEST-02 detail

`tools/import_check.py` drives the application's real pipeline: `Parse.workbook` header detection, `Parse.autoMap`, `showMapper`, `runIngest`, `normalise`, `classify`, `join`, `aggregate`, `buildTimeline`, `parseLooseDate`, the diagnostics panel and the resulting DOM.

**What is stubbed, and why it matters.** SheetJS is loaded from cdnjs on demand and this environment's proxy refuses that host, so the library cannot load here. The stub stands in at exactly the app's boundary with it (`XLSX.read` plus `XLSX.utils.sheet_to_json`) and returns an array-of-arrays built from the same workbook in Python.

That stub had to be faithful in one specific way. The app calls `sheet_to_json` with `raw:false`, so SheetJS applies each cell's number format before the app sees the value. Every date cell in this export carries builtin `numFmtId` 15 (`d-mmm-yy`), so a stored serial such as `46352` reaches the app as `29-Aug-26`, **not** as a bare number. Building the stub the naive way would have tested a code path the real import never takes.

**Consequence:** the Excel-serial branch in `parseLooseDate` is not reachable through the `.xlsx` route at all. It still matters for pasted and delimited input, where raw numbers do arrive.

#### Results

| AC | Criterion | Result |
|---|---|---|
| AC-01 | SheetJS loads and parses the workbook | **Not tested** — CDN blocked in this environment. Needs a network-enabled run. |
| AC-02 | All columns auto-map without manual override | **Pass** — header score 5, sheet `TASK`, 192 data rows. `id`/`name`/`start`/`finish`/`float` all mapped. `status`/`wbs`/`budget`/`pct` map to -1 because this export has no such columns, which is correct, not a failure. |
| AC-03 | 146 leaf activities, 46 group rows | **Pass** — 146 milestones built, group rows skipped as hierarchy labels. Matches the static count exactly. |
| AC-04 | A bare Excel serial renders the same calendar date | **Pass, with the caveat above** — `parseLooseDate('46352')` returns 2026-11-26 correctly, but no serial reaches this route. |
| AC-05 | Trailing ` A` recorded as actualised | **Pass** — 49 milestones flagged actual. |
| AC-06 | Trailing `*` recorded as constrained, distinctly from actualised | **Fail** — see below. |
| AC-07 | Blank finish skipped without aborting or corrupting adjacent rows | **Pass** — 192 rows in, 146 activities out, import completed. Blank-finish rows are skipped silently by design. |
| AC-08 | Data date / report date is not blank (TD-02 regression) | **Pass** — renders `29-Aug-26`, no "not set" fallback triggered. TD-02 did not recur. |
| AC-09 | Baked-in baseline left unmodified and restorable | **Pass** — `SEED_TASKS` 159 and `SEED_MILESTONES` 198 unchanged after import. |
| AC-10 | Dependency lines drawn between corresponding markers | **Criterion was wrong** — see below. |
| AC-11 | Diagnostics lists skipped rows, hidden when empty | **Pass on the first half** — panel visible, badge reads `Diagnostics (151) 3 warning(s)`, entries split 56 `normalise/info`, 92 `classify/info`, 3 `aggregate/warn`. Hidden-when-empty was not exercised, since this import produced entries. |

#### AC-06 failure: the finish-date constrained flag is discarded

The workbook contains 8 starred dates. Seven are in the **Start** column and one (`E13`, `11-Sep-26*`) is in the **Finish** column.

`parseLooseDate` detects the star correctly in both cases, verified directly. But `normalise` records only `startStarred` on the activity it builds. `fin.starred` is parsed and then dropped on the floor, so the one constrained **finish** date loses its marker. Measured: `startStarred` 7, finish-starred 0 against 1 present.

This is a gap in the original design rather than a regression: the handoff describes the star as tracked "so a start date carrying it can still show that marker in the dialog", i.e. start only. The acceptance criterion asserted more than the app ever promised. Raised as TD-15 rather than fixed here, because adding the field alone would produce data nothing consumes.

#### AC-10 was a bad criterion, and one real finding behind it

The probe found zero dependency lines after import. Before concluding anything, the same measurement was run against the **baseline** with no import at all: also zero, with `DEP_VIS` empty. Dependency lines are opt-in per milestone, so zero is the correct default and the criterion was simply wrong. It is restated below.

The genuine finding sits underneath it. `DEP_DATA` is a **baked-in constant parsed from the 22-Aug-26 export**, and the column mapper exposes no predecessor or successor field, so `normalise` never reads the `Predecessor Details` / `Successor Details` columns that are present in every export. **An import never refreshes dependency data.** Coverage against the 29-Aug import: 143 activity IDs in `DEP_DATA`, 106 of them not in the imported set, and 1 imported activity (`A1000`) with no dependency data at all. Raised as TD-16.

**Restated criterion (AC-10r):** when a user enables dependencies for a milestone, the system shall draw lines to the corresponding markers using dependency data from the currently loaded schedule.

#### Worth a look, not a failure

The import yields 38 deliverable groups from 146 activities, against 159 groups in the baseline. Roughly 3.8 milestones per group versus 1.2. That may be correct given `minGroupSize` and a different source export, but it is a large enough shape change to be worth confirming against expectation. Raised as TD-18.

### TEST-12 detail

Row building is now two passes, dependency first.

**Pass 1, schedule logic.** Within a band: an activity whose only in-band predecessor sits in a row continues that row. An activity with several in-band predecessors that all already sit in **one** row also continues it. An activity whose predecessors span **different** rows is a convergence point and stays on its own.

**Pass 2, deliverable identity.** Each dependency-formed row is re-read by name and split where the members are plainly different deliverables. Two discriminators, both needed:

| Discriminator | Catches |
|---|---|
| Fewer than 2 shared identity tokens, unless the token sets are identical | CAPEX vs OPEX (share only "issued"); Draft TOC vs Draft Report (share only "draft"). The identical-set arm is what lets "PFD" match "PFD", a single-token identity that can never reach a count of two. |
| Differing numbers after the stage strip | Stage Gate No.1 vs No.3, No.2 vs No.4 vs No.5. These genuinely run in sequence, so dependency alone merges them, and no amount of shared wording separates them. |

Dependency-first found more real chains than name-first did, because it does not depend on the wording holding steady across a chain.

| | PFS `.xlsx` | EPCM `.xer` |
|---|---|---|
| Activities | 146 | 2857 |
| Rows | **108** (was 110) | **1898** (was 1948) |
| Chains merged | 16 | 15 |
| Pass-2 splits | 7 | 2 |

**Guards, all 1 member as required:** Stage Gate No.1, No.2, No.3, No.4; CAPEX; OPEX; Draft TOC; SRK Process cost estimate. 8 of 8.

**Chains, all merged:** PFD 4, Bronson Connector Road 4, Snip Single Line Diagrams 4, Process Design Criteria 4.

#### One consequence worth a decision (TD-26)

`SNIP-189` "Site Plan -Client Review" now stands alone rather than joining the Site Plan row. It has two in-band finish-to-start predecessors in different rows, `SNIP-300` "Preliminary Overall Site Plan" and `SNIP-173` "Site Plan -Internal Review", so pass 1 classifies it as a convergence point. That is the specified rule behaving correctly.

It is arguably still the same deliverable. A refinement would be: where a convergence node is name-compatible with exactly one of its candidate rows, join that one. Not implemented, because the rule as agreed says a convergence point stands alone, and this is exactly the judgement the rule reserved.

### TEST-11 detail

Two deliverables were reported as splitting across rows when they should each be one. Both are clean finish-to-start chains in the source; the names drift across the chain, and keying on the name split them.

| Reported | Chain | Why it split |
|---|---|---|
| Bronson Connector Road | `SNIP-159 → 164 → 169 → 174` | The first three read "Acceptance Review Memo", the last reads "**Update and issue** Memo-Final Issue". Different stem. |
| Snip Single Line Diagrams | `SNIP-170 → 181 → 192 → 229` | "Diagram**s**" against "Diagram" mid-chain, plus a doubled suffix "-final Issue-Final Issue". |

**Fix: chain first, name second.** Activities are joined along in-band finish-to-start links, and the name is used only as a guard against joining two genuinely different deliverables. A join requires both ends to carry a stage phrase and to share at least two identity tokens, and the whole component must share two tokens as well.

Two bugs of mine were fixed in the process:

1. `deliverableStem` used `indexOf` where a **suffix** match needs `lastIndexOf`. In "…-final issue-final issue" the first occurrence fails the end-of-string test, so nothing was stripped at all and `SNIP-229` never matched its own chain. Stripping now also repeats, since P6 carries doubled suffixes.
2. A linear chain walk requiring exactly one successor stopped at the first branch. P6 carries redundant skip-links: Process Design Criteria has both `115→123` and `115→134`. Replaced with connected components over the FS edges.

| Probe | Expected | Result |
|---|---|---|
| `SNIP-159` and `SNIP-174` | one row | **4 members, same row** |
| `SNIP-198` "MTO and Model Review" | separate, despite being FS-linked from 174 | **1 member** — carries no stage phrase, so the chain breaks there |
| `SNIP-170` and `SNIP-229` | one row | **4 members, same row** |
| `SNIP-115` and `SNIP-134` | one row | 4 members |
| `SNIP-204` / `SNIP-320` SRK Process vs Mining | separate | **1 each** — no FS link between them |

PFS: 146 activities to **110 rows**, 15 chains merged, ten rows carrying 4 markers against seven at v3.1.0-P5. EPCM is unchanged at 1948 rows: its bands resolve to the tag, area and system strategies, which this change does not touch.

### TEST-10 detail

One rule does not fit every schedule, so a strategy is now chosen per band from what that band's activities actually carry, rather than assumed.

| Strategy | Key | Chosen when |
|---|---|---|
| `tag` | equipment/structure tag in the Activity ID | at least half the band's activities carry one |
| `system` | process system matched in the activity name | 60%+ and band over the large-band threshold |
| `area` | four-digit area code | 60%+ and band over the large-band threshold |
| `stage` | deliverable stem, corroborated by a finish-to-start link or stage phrasing | fallback |
| `activity` | one row per activity | nothing else applies |

Choosing `tag` also rolls that band up from its full WBS path to its discipline, which is what lets one tag collect its stages into a single row. Keyed on the full path the same tag appears once per area and never merges.

| Dataset | Activities | Rows | Bands by strategy | Max markers on a row |
|---|---|---|---|---|
| PFS `.xlsx` | 146 | **115** | stage 16, activity 22 | 4 |
| EPCM `.xer` | 2857 | **1948** | tag 95, activity 208, stage 10, system 7, area 6 | 15 |

PFS is byte-identical to v3.1.0-P4: 100 rows with 1 marker, 6 with 2, 2 with 3, 7 with 4. The engineering behaviour is unchanged by the addition of the construction strategies, which is the point.

Discipline roll-up on the EPCM data, measured before implementation: Mechanical 267 activities to 33 rows, Electrical 359 to 30, Piping 90 to 24, Structural Steel 64 to 20, Platework 74 to 19.

**Two regressions were caught by measurement during this pass and fixed, not shipped.**

1. Rolling every band up to its discipline unconditionally diluted the stage ratio of engineering bands, so chains fell back to one row each and PFS rose from 115 rows to 121. The roll-up is now a consequence of choosing `tag`, never a precondition.
2. Gating stage clustering behind a staged-fraction threshold lost real chains in mixed bands, leaving PFS at 119. Stage is self-corroborating (it merges only on a finish-to-start link or on every member differing purely by a stage phrase, and otherwise returns one row per activity), so it cannot over-merge and is now the fallback rather than `activity`. That restored 115 exactly.

A row that grows past `maxRowMarkers` (15) is split by the work-type prefix of the Activity ID rather than shipped. Without it the EPCM fabrication area bucket produced a single 95-marker row, which is less readable than the ungrouped activities it replaced. 16 such splits occurred.

`INGEST_CONFIG.rowStrategy` defaults to `'auto'` and can be forced to any single strategy for a schedule that does not classify cleanly.

**Scope boundary:** this changes row grouping only. Sub-headings within a band, the second half of the agreed rule ("either subheadings or rows depending on numbers"), are not built. 1769 of the EPCM rows still carry a single marker, concentrated in the 208 `activity` bands.

### TEST-09 detail

New row model: band is the deepest heading; within a band, activities sharing a deliverable stem collapse into one row **only** when corroborated, either by a finish-to-start link between them or by every member differing purely by a recognised stage phrase.

| Dataset | Activities | Bands | Rows | Chains collapsed |
|---|---|---|---|---|
| PFS `.xlsx` (29-Aug-26) | 146 | 38 | **115** | 15 |
| EPCM `.xer` (WE 2026.8.14) | 2857 | 449 | **2856** | 1 |

PFS marker distribution: 100 rows with 1 marker, 6 with 2, 2 with 3, 7 with 4. The 4-marker rows are exactly the review sequences (`Process Design Criteria`, `PFD`, `Mass and Water Balance`, `MEL`), each carrying 8 corroborating finish-to-start links.

`Predecessor Details` and `Successor Details` now auto-map: header score rose from 5 to 7. TD-16's ingest half is done.

**The EPCM result is the finding.** The rule does essentially nothing on construction data, because construction activities are not named by review stage. Measured directly: the largest bands carry **zero** in-band finish-to-start edges (87 items / 0 edges, 52 / 0, 48 / 0, 44 / 0).

Those activities are heavily sequenced, just not along the band axis. Grouping instead by the equipment tag embedded in the Activity ID (`CN-3110ST001-C1050`) finds the real chains:

| Tag | Activities | Bands spanned | Internal FS links |
|---|---|---|---|
| `3110ST001` | 76 | 14 | 85 |
| `4130ML001` | 68 | 7 | 87 |
| `4110ST001` | 67 | 12 | 76 |
| `4250ST002` | 63 | 15 | 74 |

So the sequential structure the rule was meant to exploit is present, but it runs **across** bands rather than within one, and a 76-activity row would be worse than the problem being solved. Only 1285 of 2857 activities (70 tags) carry a recognisable tag at all.

Left as an open design question (TD-20) rather than guessed at. The PFS behaviour is correct and shipped; the EPCM axis needs a decision.

**Baseline regression:** unchanged at 163 rows / 196 markers / 159 tasks / 198 milestones, because the baked-in baseline bypasses `aggregate()` entirely. Theme check still 33 toggling, 0 frozen, 0 low-contrast.

### TEST-07 detail

Probe set extended from 17 to 35, adding the board: marker label, short title and hours backings, alt-row label, past and filtered week columns, subtotal hours, remarks placeholder, all six icon states, and constant-by-design probes for phase bands and health dots.

| | Result |
|---|---|
| Probes expecting to toggle | 33 |
| Toggling correctly | **33** |
| Frozen | **0** |
| Constant by design, correctly frozen | 2 |
| Probes below 3.0:1 contrast, either theme | **0** |

**A change was measured, judged wrong, and reverted inside this test.** The marker label backings were first made per-theme, and they did toggle. The newly added contrast check then measured dark-theme label text at 1.16:1 to 1.97:1 against those backings. The backings are stickers over the board and the label text colour was chosen against the sticker, not the page, so making them follow the theme rendered them unreadable. They were moved back to constant, tokenized in the non-themed `:root`. The original constant white was correct design, not a defect.

That is the second time in two passes that the audit pointed at something which turned out to be working as intended, after the `var()` fallbacks in TEST-05. Both are recorded because the pattern matters more than either instance: a tokenization signal is a candidate, not a verdict.

**Why the contrast check was added.** A "does it toggle" assertion cannot see a text colour that changed in step with its background and stayed unreadable. Toggling and legibility are different properties and need different measurements.

**One contrast finding was a probe artifact, not a defect.** An earlier run reported the sticky corner cell at 1.00:1, white on white. That cell's own text is whitespace; its visible glyphs are children carrying their own tokenized colours. The check now judges an element's own text nodes only, and the probe targets a real column header rather than the sticky corner.

### TEST-08 detail

| Assertion | Result |
|---|---|
| Page loads, no console errors | Pass |
| Rows and markers | Pass — 163 rows, 196 markers, unchanged since TEST-03 |
| App summary stat | Pass — `159 tasks` / `198 milestones`, unchanged |
| Icons rendered | Pass — 221 `.ms-icon` elements |
| `APP_VERSION` propagates to title and label | Pass — `v3.1.0-P3` |
| Version literals in file | Pass — exactly one |

### TEST-06 detail

| Assertion | Result |
|---|---|
| Page loads, no console errors | Pass |
| Rows and markers rendered | Pass — 163 rows, 196 markers, unchanged from TEST-03 |
| App summary stat | Pass — `159 tasks` / `198 milestones`, unchanged |
| `APP_VERSION` propagates to icon-bar label | Pass — `v3.1.0-P2` |
| `APP_VERSION` propagates to page title | **Failed on first run**, then fixed and re-tested — see below |
| Version literals in file | Pass — exactly one, the `APP_VERSION` constant itself |

**Correction to TEST-03.** TEST-03 recorded "`APP_VERSION` propagates to page title: Pass". That was wrong. The `<title>` contained its own hardcoded `v3.1.0-P1` and never read `APP_VERSION` at all; the assertion passed only because the hardcoded string happened to equal the constant at the time. Bumping to P2 exposed it — the tab read P1 while the icon bar read P2.

This is recorded rather than quietly corrected because the single-source-of-truth invariant is one the project explicitly protects, and a test that passes by coincidence is worse than no test. The title and the static label text now both derive from `APP_VERSION` at load, and the assertion is a real one: exactly one version literal exists in the file. Raised as TD-10 (closed in the same change).

An em dash was removed from the title in the same edit, since the tab title is user-facing text and the project bans em dashes there.

### TEST-04 detail

`tools/colour_audit.py` was written from the method documented in `Token_Migration_Log.md`, run against `src/milestone-dashboard.html`, and its output compared to v1's logged figures rather than either being assumed correct.

| Assertion | Result |
|---|---|
| Full documented scope reproduces v1 | **Fail** — 131 colour occurrences against v1's 99 |
| Restricting to hex only reproduces v1 exactly | Pass — 99 occurrences, 72 distinct, 24 matching a token, all three exact |
| `--space-*` reference count reproduces v1 | **Fail** — 38 against 57; v1 counted the 18 `:root` definitions as references |
| Restricting px spacing to whole properties approximates v1 | Pass — 114 against 117 |
| `var(--text-*)` count reproduces v1 | Pass — 7, exact |
| px font-size count reproduces v1 | Pass — 100 against 101, within regex noise |

**Root cause:** v1 matched hex only, never `rgb()`/`rgba()`, despite its own documented method stating otherwise, and counted token definitions as token references. It was not under version control, so the divergence between its implementation and its documentation was invisible until reimplemented.

**Consequence:** the FEAT-14 backlog was scoped against understated figures. 32 `rgba()` occurrences (21 distinct) had never entered triage. Raised as TD-06 and TD-07.

A defect in the new script was found and fixed during the same run: it initially detected 2 of 4 token-definition blocks and reported 159 occurrences. Recorded in the Migration Log rather than silently corrected, since the inflated figure was quoted mid-session.

Scope boundary: this tests the **measurement**, not the dashboard. No application behaviour was exercised or changed.

### TEST-03 detail

Rendered `src/milestone-dashboard.html` in headless Chromium (`--virtual-time-budget=6000 --dump-dom`) and asserted against the resulting DOM. Not a code read-through.

| Assertion | Result |
|---|---|
| Page loads, process exits 0 | Pass |
| No errors or warnings on stderr | Pass |
| `#tbody` present and populated | Pass — 163 `<tr>` rendered (activity rows plus band headers) |
| Milestone markers rendered | Pass — 196 `.m-wrap` elements in the rendered week window |
| App's own summary stat | Pass — reports `159 tasks` / `198 milestones`, matching the documented baseline exactly |
| `APP_VERSION` propagates to page title | ~~Pass~~ — **incorrect, corrected by TEST-06.** The title was a hardcoded literal that happened to equal the constant. |
| `APP_VERSION` propagates to icon-bar label | Pass — `Schedule Reporting and Evaluation Tool | v3.1.0-P1` |

Note: 196 rendered marker elements against a reported 198 milestones is expected, not a defect — the summary counts the data model, the DOM counts what falls inside the rendered week window. Flagged here only so a future session does not read it as a discrepancy.

Scope boundary: this confirms the file survived migration intact and boots correctly. It does **not** re-test the TEST-01 feature set, and it does not exercise import, filtering, annotation, or export.

### TEST-01 detail (treat as ground truth, do not re-verify from scratch)

| Area | Checked | Result |
|---|---|---|
| Version single-source-of-truth | `APP_VERSION` constant present and consistent | Pass — `3.1.0-P1` |
| Colour token system | Primary/secondary button tokens, accent/crit tint tokens, row/badge tokens | Pass |
| Spacing/text tokens | `--space-0..7`, `--text-xs..lg` | Pass |
| Independent label-scale sliders | 3 separate controls (label/title/hrs) | Pass — not merged back into one |
| Milestone dialog | Header reorder, actualised-date green shading, 5-state health override, comment autosave | Pass |
| Dependency system | Redraw-on-rerender fix, All-on/off button state reflection, full export payload | Pass |
| Label collision avoidance | 3-band cycling system | Pass |
| Performance fix | `scheduleRerender()` debounce wrapper | Pass — wired to all 5 real call sites |
| Settings drawer reorg | Renamed titles, section order, collapsible Import/Diagnostics | Pass |
| Search/filter system | Sticky corner box, synced Title field, Activity ID autocomplete | Pass |
| Solid-fill icons | All 5 non-baseline states set to `filled` | Pass |
| Sticky header rows | Both phase-band and date rows pinned on vertical scroll | Pass |
| Fit to Screen | Column-width auto-fit function | Pass |
| Baseline data | 15-Aug-2026 source, 159 tasks / 198 milestones | Pass |
| Pre-history architecture | Dependency-line drawing, short-title core mechanism, start-date/actual/starred-date fallback handling | Pass |
| Banding spec | Confirmed still not implemented (correct — matches documented Phase 1 status) | As expected |

### TEST-02 acceptance criteria (EARS, to run)

Source file shape confirmed by static inspection of the workbook: 192 data rows, 146 leaf activities, 46 band/group rows, columns `Activity ID / Activity Name / Duration / Start / Finish / Predecessor Details / Successor Details / Total Float`, data date 29-Aug-2026. Finish column is mixed: 129 Excel serial values, 57 text values carrying ` A` or `*` suffixes, 6 blank.

| # | Criterion |
|---|---|
| AC-01 | When an `.xlsx` file is selected for import, the system shall load SheetJS and parse the workbook without error. |
| AC-02 | When header auto-detection runs on this file, the system shall map all eight columns without manual override. |
| AC-03 | When hierarchy detection runs, the system shall classify 146 rows as leaf activities and 46 as group/band headers. |
| AC-04 | When a Finish value is a bare Excel serial, the system shall render the same calendar date as the P6 source. |
| AC-05 | When a Finish value carries a trailing ` A`, the system shall record it as actualised and shade it accordingly in the milestone dialog. |
| AC-06 | When a Finish value carries a trailing `*`, the system shall record it as constrained, distinctly from actualised. |
| AC-07 | When a Finish value is blank, the system shall skip the marker without aborting the import or corrupting adjacent rows. |
| AC-08 | When the import completes, the system shall display a non-blank Data date / Report date (regression check on TD-02). |
| AC-09 | When the import completes, the system shall leave the baked-in 15-Aug-2026 baseline unmodified and restorable. |
| AC-10 | When predecessor/successor details are present, the system shall draw dependency lines between the corresponding markers. |
| AC-11 | When the import completes, the Diagnostics panel shall list any skipped or unmapped rows, and shall remain hidden if there are none. |

**Gate rule:** TEST-02 must pass before any live user test (Gate 5b) is prescribed.

## Live User Tests (Gate 5b — only after 5a clears)

| ID | Date requested | Scope prescribed | Pass criteria | Result | Reported |
|---|---|---|---|---|---|
| — | — | None yet. Blocked on TEST-02. | — | — | — |

## Feedback Triage

| Feedback item | Linked UT | Classified as | Routed to | Timing decided |
|---|---|---|---|---|
| Blank Data-date / Report-date on a real `.xlsx` import | — (pre-migration report) | Bug, root cause unconfirmed | TD-02, retested by AC-08 | Now, if TEST-02 reproduces it |
| Multiple rapid UI interactions caused visible slowdown | — (pre-migration report) | Bug | Fixed pre-migration via `scheduleRerender()` | Closed |
| One shared text-scale slider fought itself across label/title/hours | — (pre-migration report) | Requirement gap | US-14, FEAT-07 | Closed — split into three |

## Acceptance & Publish Record

| Date | Accepted criteria | Exceptions accepted | Publish target | Version/tag |
|---|---|---|---|---|
| 2026-09-09 | TEST-05 theme toggle (0 frozen of 16), TEST-06 render regression (163 rows / 196 markers / 159 tasks / 198 milestones unchanged), single version literal asserted | Colour occurrences with no token match not yet triaged; spacing and text tokens untouched; board phase bands, discipline band rows, marker icon states and remarks field states still not tokenized | File distribution | v3.1.0-P2 |
| 2026-09-10 | TEST-07 board toggle and contrast (33 toggling, 0 frozen, 0 below 3.0:1), TEST-08 render regression unchanged | Spacing and text tokens still untouched; colours outside the board with no token match not triaged; discipline band rows still not tokenized; hover and focus states are not probed headlessly | File distribution | v3.1.0-P3 |
| 2026-09-10 | TEST-09 row model on two datasets; baseline render unchanged; theme check clean | EPCM/construction schedules gain nothing from the rule (TD-20 open); XER is converted by an external tool, not ingested by the app (TD-21) | File distribution | v3.1.0-P4 |
| 2026-09-10 | TEST-10 mixed strategies on both datasets; PFS unchanged at 115 rows; baseline render unchanged; theme check clean | Sub-headings within a band not built; 208 EPCM bands still fall back to one row per activity; discipline and system term lists are fixed rather than learned | File distribution | v3.1.0-P5 |
| 2026-09-10 | TEST-11 chain-first merging; both reported failures fixed; both over-merge guards hold; baseline render unchanged | Sub-headings within a band still not built (TD-23); stage phrase list is fixed rather than learned | File distribution | v3.1.0-P6 |
| 2026-09-10 | TEST-12 dependency-first rows, 8/8 guards, chains intact, baseline unchanged | Convergence nodes always stand alone even when name-compatible with one candidate row (TD-26); sub-headings still not built (TD-23) | File distribution | v3.1.0-P7 |
| 2026-09-10 | TEST-13 convergence relaxation, row numbers and milestone drag; 8/8 guards; baseline render unchanged; theme check clean at 37 probes | Row drag itself not built (the handle slot is reserved, TD-29); moves are session-scoped and a re-import does not replay them (TD-27); sub-headings still not built (TD-23) | File distribution | v3.1.0-P8 |
| 2026-09-10 | TEST-14 mount manager, export identity, validation and selective import; baseline render unchanged; theme check clean at 45 probes | Round trip covers the annotation layer only (TD-32); unmounting annotations does not roll back imported values (TD-31); two low-contrast tokens still need a sweep across their other consumers (TD-33) | File distribution | v3.1.0-P9 |
| 2026-09-10 | TEST-15 import failure handling, 4/4 cases; baseline render unchanged; theme check clean at 48 probes | `.xlsx` import still depends on reaching the SheetJS CDN and is impossible without it (TD-36, open) | File distribution | v3.1.0-P10 |
| 2026-09-10 | TEST-16 read-error diagnosis and retry; TEST-15 re-run 4/4; baseline unchanged; theme check 49 probes | The user's own failure is not yet confirmed resolved — P11 names the cause, it does not remove it | File distribution | v3.1.0-P11 |
| 2026-09-10 | TEST-17 data date placement, default and wiring; full suite re-run; baseline unchanged; theme check 49 probes | Previous-Friday rule returns the week before when today is a Friday, by design (see TEST-17) | File distribution | v3.1.0-P12 |
| 2026-09-10 | TEST-18 real Import click in a normal page and in an `about:srcdoc` iframe; full suite re-run; baseline unchanged; theme check 49 probes | The viewer-injected `onclick` TypeError is outside this app and is not addressed here | File distribution | v3.1.0-P13 |
| 2026-09-10 | TEST-19 publish round trip on a real published file; full suite re-run; baseline unchanged; theme check 49 probes | A published file still carries the original seeds as a fallback and is larger than needed (TD-43); readers can republish from a published file (TD-44, undecided); the SharePoint upload itself is not yet exercised with a real library | File distribution | v3.1.0-P14 |
| 2026-09-11 | TEST-20 published-file provenance; TEST-19 unchanged; baseline render unchanged; theme check 50 probes | The SharePoint upload itself is now user-confirmed working; provenance wording not yet reviewed by a reader of a published file | File distribution | v3.1.0-P16 |
| 2026-09-11 | TEST-21 five of six changes verified; baseline render unchanged | **Contrast gate failing by design pending TD-50**: the requested `#f4f5f8` is 1.79:1 on the light header. Delivered as asked and reported, not suppressed. | File distribution | v3.1.0-P18 |
| Pre-migration | TEST-01 full feature regression | Banding (FEAT-10), sorting/icon customisation (FEAT-11), JSON round-trip (FEAT-13) all knowingly not built. Tokenization (FEAT-14) knowingly incomplete. Label collision same-row only. Header aliases exact-match only. | File distribution | v3.1.0-P1 |
| 2026-09-09 | Migration to git repository, project kit established | TD-01 version discrepancy open; companion tokenization docs (TD-03) not yet located | Branch `p6-milestone-dashboard` | Migration commit |
