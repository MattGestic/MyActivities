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
| TEST-39 | 2026-09-21 | Four defects reported against the P36 build: the More Actions menu clipped to the header row, the Title col slider appearing to do nothing, the zero-dependency filter doing nothing, and the ID suggestions painting behind the board | `tools/p37_check.py` at 390x844, 1440x900 and 2000x900, plus five source-level assertions. Both popups are asserted by **hit-test profile** and by counting individually reachable children, because the clipping-aware ancestor walk written at P36 cannot answer the question for a `position:fixed` element. The zero filter is asserted from the DEFAULT state with dependencies off, which is the state the report came from | **Pass 65/65**, after the first measurement refuted one report and the P36 measurement technique wrongly reported a working fix as broken | TD-137 to TD-140, TD-141 raised |
| TEST-38 | 2026-09-19 | More Actions: seven header icon buttons collapsed into one menu, with the app name and version text beside it | `tools/p36_check.py` at three viewport widths, plus the previous release rendered in the same browser at the same viewports for the before/after. The claim that no state-writing function had to change is asserted by **diffing those function bodies against the previous release**, not by reading them. The active-row state is asserted on computed background against an inactive row, because `.icon-btn.on` and `.icon-btn.ib-mi` have equal specificity and class presence proves nothing. `p32_check`'s TD-72 guard was rewritten to the new contract and given a negative control | **Pass 95/95**, after one wrong assumption about the phone-width label and one wrong measurement in the rewritten TD-72 guard | TD-134, TD-135, TD-136 |
| TEST-37 | 2026-09-18 | Milestone card rework: the 10% shrink, Start / Finish / Progress on one row behind a divider at one text size, the collapsible weight/hours row, and Progress as an editable annotation-layer override | `tools/p35_check.py` at three viewport widths, plus `tools/persist_check.py` extended to round-trip an override. The shrink is measured against the **P34 release rendered in the same browser at the same viewport on the same milestone**, because a card that got narrower while getting taller is not a smaller card. The three-layer rule is asserted by snapshotting every milestone record before the edit and comparing all 146 after. The three-field row is measured on a milestone chosen for carrying a real start date, because the first suitable target hides its Start field | **Pass 117/117**, after three probe defects and one vacuous comparison were found and fixed | TD-130 to TD-133 |
| TEST-33 | 2026-09-16 | Does every row and milestone record its source; does the Source Schedule column and filter narrow in both directions; does appending a schedule to itself keep the two separable; does a multi-source board survive publish and a view switch | `tools/p30_check.py`. Appends the SAME workbook to itself, so every Activity ID collides: the worst case rather than a convenient one. The suffix is checked across `m.id`, `m.notes`, `m.ref`, `t.ref`, `t.src` and the row's `data-ids` together, and an annotation keyed on a suffixed ID must not land on its twin. Band order is measured as contiguous RUNS, not distinct names, because appending a file to itself repeats every band name. Performance is asserted by COUNTING (one index build reused across 300 lookups, one filter pass per typing burst, zero per-cell style writes), never by wall clock: `performance.now()` does not advance under virtual time and the first draft reported 0ms against every budget | **Pass 55/55** | TD-99 to TD-103 (closed) |
| TEST-32 | 2026-09-16 | Does the rebuilt settings panel actually hold one spacing contract; does every control still reach a function that exists; did anything on the board move | `tools/p29_check.py`. The inline padding/margin count must be **zero**, not smaller. Gutter, row step, separator and radius each asserted as a single computed value across the real panel. Every inline `onclick`/`onchange`/`oninput` in the drawer is parsed and checked against `window`, because a handler naming a function that no longer exists throws only when clicked and looks perfect until then. Baseline and imported board figures captured separately, the baseline taken before a single control is touched | **Pass 46/46** | TD-94, TD-95, TD-96 (closed), TD-97, TD-98 (open) |
| TEST-31 | 2026-09-15 | Does an import span the schedule's own dates rather than a fixed window; does a typed range override it; does a user-typed range narrow the board, survive a rebuild and intersect the week dropdown | `tools/p28_check.py`. The expected span is derived from the WORKBOOK here, independently of the app, so the assertion is against the source. The decisive setup check is that no milestone fails to plot, not that a timeline was built | **Pass 34/34**, after a probe counting every row's cells and a real dead-fitter bug were found | TD-89 to TD-93 (all closed) |
| TEST-30 | 2026-09-15 | Are the dependency counts legible rather than merely present; does the baseline overlay place each ghost on its pair's Y, in its own baseline date's column, behind everything; does the A3 preview hold the board at page width and put it back on the way out | `tools/p27_check.py`. Chips measured for position, size, backing and overlap against their own icon and label stack, not for existence. Ghosts paired through the `data-ghost-for` link rather than guessed from position. Page frame measured against a live `100mm` probe, not an assumed 96dpi | **Pass 32/32**, after a board-duplication bug, a ghost hidden under its pair, and two vacuous assertions were found | TD-82, TD-83, TD-84, TD-85, TD-86, TD-87 (all closed), TD-88 (open) |
| TEST-29 | 2026-09-14 | Week filter highlights the heading only; month highlight is white; milestone card reordered with a float column | Filter driven through `setFilterWeek`, computed backgrounds compared against an unfiltered cell; card measured on an **imported** milestone that actually has a discipline and a float | **Pass**, after two assertions were found passing vacuously | TD-79, TD-80, TD-81 (all closed) |
| TEST-28 | 2026-09-14 | Marker placement is a property of the cell; title in the top row; activity title wrap toggle | Every marker's centre measured as a percentage of its cell's **padding box**, the frame it is positioned in; N=3, 4 and 5 forced into a real cell | **Pass** | TD-74, TD-75, TD-76, TD-77 (closed), TD-78 (open) |
| TEST-27 | 2026-09-14 | Dependency tooltip and notes dialog show one row per activity as `#ID: Title`, truncated | Real builders driven with a real ID pair; text-range alignment; a 400 character title forced to prove the box does not grow | **Pass** | TD-72 (closed), TD-73 (open) |
| TEST-26 | 2026-09-14 | Ten presentation and default changes, each measured in the running app | Computed style, bounding rects and text ranges on a real render; controls driven both ways; milestone card opened by a real marker click | **Pass**, two defects found and fixed first | TD-68, TD-69, TD-70, TD-71 (all closed) |
| TEST-25 | 2026-09-14 | An imported board presents its bands in the schedule's own order | `tools/order_check.py` — derives the schedule's section sequence from the workbook itself, runs a real import, then places each board band back onto the sheet by the row of its first activity and asserts those rows strictly increase | **Pass** on P22, **fails on P21** with 7 bands out of order | TD-65, TD-66 (closed), TD-67 (open) |
| TEST-24 | 2026-09-11 | Header darkened and its text tokens split out; data date rule on a Friday; republish provenance chain | Contrast measured on every text colour landing on `--color-bg-header` in both themes; the date rule driven through the real function on all seven weekdays plus month and year boundaries; the chain built by the real payload function | **Pass**, contrast gate green | TD-50, TD-46, TD-44, TD-63, TD-64 (all closed) |
| TEST-23 | 2026-09-11 | Every kind of board markup survives a publish, and the two layout changes replay onto a schedule that has never seen them | `tools/persist_check.py` — three stages against real headless renders: edit and capture both real downloads, read the published file back, replay the exported model onto a clean board | **Pass** (20 checks) | TD-27, TD-58, TD-59, TD-60, TD-61 (all closed) |
| TEST-22 | 2026-09-11 | Heading bar split into two containers with responsive stacking, subtitle relocated, and the search moved to its own sticky row | Bounding-rect measurement at two viewport widths, and again after 900px of real scroll inside `#scroll-wrap` | **Pass** | TD-56, TD-57 (both closed) |

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

### TEST-22 detail

**Layout, measured by bounding rect rather than read from the CSS.**

| Assertion | 1600px | 700px |
|---|---|---|
| Title and details on one line | **yes** | no (stacked, as intended) |
| Details to the right of the title | yes | n/a, stacked |
| Details right-aligned to the bar | yes | yes |
| Subtitle below the whole bar | yes | yes |
| Search row above the month bands | yes | yes |

At 700px the details container drops to `x:10, y:60` under the title at
`x:10, y:40` — stacked, left-aligned, full width.

**Stickiness, which is the part that could have broken.** The search moved into
its own `tr.hdr-search` at the top of the table head, so the two rows below it
had to be re-offset. Both now derive from a single `--hdr-search-h` rather than
the previous hardcoded `top:19.5px`.

The first run of this test proved nothing: `window.scrollTo(0,1200)` left
`scrollY` at 0, because the board scrolls inside `#scroll-wrap`, not the page.
Re-run against the real container with `scrollTop = 900`:

| Row | Top → bottom (1600px) | Top → bottom (700px) |
|---|---|---|
| Search | 77 → 103 | 110 → 136 |
| Phase (months) | 103 → 119 | 136 → 152 |
| Week | 122 → 145 | 156 → 178 |

Three rows stacked in order with no overlap, and the search row's top equals the
scroll container's top, so it is genuinely pinned. Measured on the `th`
elements, not the `tr` — per the lesson that a row's bounding box is not what is
sticky here.

**Subtitle text** reads "Exported milestone view of P6 schedule shown by activity
end dates". Taken from a partly garbled dictation and flagged as an assumption.

### TEST-31 detail

`tools/p28_check.py`, 34 assertions over the two halves of one request.

**Setup: the base range comes from the data.** The expected span is derived
from the workbook inside the Python half, by walking its date columns, so the
app is checked against the source rather than against itself.

| Assertion | Result |
|---|---|
| The range section is hidden until a file loads, shown once it does | passes |
| The note names the schedule's own span before Import is pressed | 01-May-26 to 26-Nov-26 |
| Both fields start blank, meaning the full span | passes |
| The section is put away once the import is built | passes |
| **Every imported milestone lands in a column** | **0 outside the board** |
| The board starts within a week of the earliest date it must show | 4 days of lead |
| The board ends within a week of the latest date it must show | 3 days of tail |
| The import summary states the range used, and the data's own span | passes |
| A typed range is narrower, covers what was typed, and is recorded as typed | 14 weeks vs 31 |
| Clearing the fields restores the full derived range | 31 weeks |
| The app's earliest and latest dates match the workbook's | 01-May-26 / 26-Nov-26, exact |

Measured against v3.1.0-P27 on the same export, the fixed window was wrong in
both directions at once: **3 milestones unplotted and 3 horizon warnings**, on
a **39 column** board. P28 gives **0**, **0**, and **31 columns** — it lost
three real milestones off the end while padding eight empty weeks onto the
front.

**Filter: a user-typed range narrows the board.**

| Assertion | Result |
|---|---|
| Every week column is shown before filtering | 31 of 31 |
| A date range narrows the visible columns | 9 of 31 |
| No column outside the range is still shown, and none inside it was hidden | 0 and 0 |
| The month bands span exactly the columns still shown | 9 colspan vs 9 columns |
| Rows with nothing in the range are hidden | 67 of 105 |
| A week selection outside the range cannot reach back outside it | 0 leaked |
| The range survives a full rebuild | 9 vs 9 |
| Clearing, and Remove all filters, both release the columns | 31 of 31 |
| A from-date alone clamps one end and leaves the other open | hi = last column |
| A backwards range is read as the range the user meant | same 9 columns |
| The A3 preview fits only the columns the range left | 9 columns at 72px |

Both directions of the column assertion are checked deliberately: a filter that
hid *everything* would satisfy "nothing outside the range is shown" on its own.

**Two findings.**

The first two runs compared column counts of 3255 against 31. The probe counted
week cells across every row rather than the header row, so every count was
multiplied by the row count. A probe bug, but it hid the month-colspan
assertion behind a meaningless comparison until it was fixed.

The second is a real defect in shipped code, and it is why the print-plus-range
assertion is in this check at all (TD-92). `fitToScreen()` and `fitPrintPage()`
both measured `document.querySelector('tr.data')`, the first data row in the
document, to learn how wide the non-week columns are. A hidden row has no
layout, so every cell in it reports `offsetParent === null`: with any filter
active that hid the first row, both functions found zero measurable week cells
and returned having done nothing. The A3 preview simply refused to refit. Both
now take the first row that is actually laid out.

### TEST-30 detail

`tools/p27_check.py`. One run, four subjects, 32 assertions. Three real defects
and one probe defect surfaced during the run and are recorded because each one
passed a reading of the code.

**The dependency counts.** The reported symptom was "the button isn't working,
the numbers aren't displayed". Both halves were true, for two unrelated reasons.

| Assertion | Result |
|---|---|
| Chips render when the toggle is on | 262 chips |
| The measurements had a sample to measure | 262 sampled |
| The toggle did not duplicate the board | 159 rows before, 159 after |
| Every chip sits level with its own icon (within 2px) | 0 off |
| Every chip is at least 10 x 9 (the old ones measured 4.5 x 8) | 0 too small |
| Every chip has a backing | 0 unbacked |
| No chip is under its own label stack | 0 covered |
| Chip value matches `DEP_DATA` | 262 checked, 0 wrong |
| Toggling off clears the chips and the class | 0 left |

The first cause (TD-82) is that `onCountsToggle()` called `renderRows()`
directly. `renderRows()` **appends**; `teardown()` is what empties the tbody,
and it only runs inside `rerender()`. So each toggle left the whole previous
board in place and built a second copy under it. Turning counts off then looked
like a no-op, because the 262 chips still on screen belonged to the copy that
same click had just added. The second cause (TD-83) is that the chips, even on
the fresh copy, were 8px unbacked digits placed fully outside the icon on the
boundary between two rows, with the label stack over the right-hand one.

**The baseline overlay**, driven through a real import of the Aug-29 export,
switched to the Update view and toggled on:

| Assertion | Result |
|---|---|
| Ghosts are drawn | 143 |
| Every ghost matched back to a live marker by Activity ID | 143 paired, 0 unpaired |
| Ghost column is its own baseline date's column | 0 in the wrong week |
| Ghost Y equals its pair's Y (within 1.5px) | 0 off |
| Ghost paints behind its live marker | 0 not behind |
| Ghost uses the greyed baseline icon | 0 not greyed |
| An unmoved ghost is offset clear of its own live icon | 91 same-column, 0 hidden |
| Tooltip names the live baseline label | passes |
| Ghosts carry no count chips | 0 |
| Row count unchanged across every toggle | 105 throughout |

Two findings here. Offsetting an unmoved ghost from the **cell centre** left
three of them under a marker, because a cell holding several markers spreads
them off centre; the offset is now taken from the ghost's own pair. And the
first pairing attempt inferred the pair from position, which reported three
false failures: two markers in one row can share a baseline column and the
guess picked the wrong one. The ghost now names its pair in `data-ghost-for`,
which is both a better probe and inspectable in devtools.

**The A3 print preview.** Page geometry is measured against a live `100mm`
probe element rather than an assumed 96dpi, since the browser's CSS pixel ratio
is not guaranteed.

| Assertion | Result |
|---|---|
| Body enters print-mode | passes |
| The View Controls panel was closed | passes |
| An `@page` rule is injected for A3 portrait | `@page{size:297mm 420mm;margin:8mm}` |
| The page frame is one A3 sheet wide | 1123px vs 1122px expected |
| The preview banner is shown | passes |
| Week columns were refitted | 36px to 20px |
| The board fits the page, or the banner says it cannot | banner states it |
| Leaving clears print-mode, the `@page` rule and the week width | passes |
| Leaving reopens the View Controls panel it closed | passes |
| The page frame is `display:contents` again | passes |

**Known and stated, not hidden:** at the full 39-week horizon the board does not
fit an A3 portrait sheet even at the 20px minimum column width. The preview says
so in its banner and names the remedy (hide columns, or filter the week range)
rather than clipping silently.

**Vacuous passes (TD-87).** The first run of this probe read the chips
synchronously after the toggle, before the debounced rerender had rebuilt the
board. Every chip assertion passed against an empty set. This is the third
occurrence in this project (TD-66, and the P26 float column), so each probe that
measures a set now asserts its sample size as its own check.

### TEST-29 detail

**The week filter**, driven through the app's own `setFilterWeek`:

| Assertion | Result |
|---|---|
| Body cells no longer painted | filtered cell background equals a plain cell's; border width 0 |
| Cells still tagged for fit-to-screen | `.filter-col` still applied, and fit-to-screen still finds its columns |
| Week heading highlighted | white on the accent |
| Month heading highlighted | "Sep 2026", **white** on the accent |
| Clearing the filter clears all three marks | week 0, month 0, column 0 |

**The milestone card.** Measured by bounding rect: the parent heading sits above
the title, the short title below it, and the float column beside both, spanning
their full height with the value above the label. The label measures 11px, the
same as the short title field, which is what was asked. The title no longer
carries the float tag.

**Two assertions passed vacuously on the first run.** The card was opened on the
first marker on the board, which is a baseline seed: every seed carries the
discipline "Unassigned", so the parent heading was `display:none`, and seeds
carry no float, so the float column was hidden too. "Parent above title" was
comparing against a zero rect, and the float column was never rendered at all.
Re-run against an **imported** milestone with a real discipline (Key Milestones)
and a real float (26 day), both assertions became meaningful and both hold.
Recorded because the first run reported a clean pass on two things it had not
tested.

One correction during the work: the float column initially took only its own
content height, so its divider stopped short of the short title. `align-items`
on the row was `flex-start`; set to `stretch` with the content centred, the
column runs beside both rows as a column should.

Contrast gate 63 probes, 0 frozen, 0 below 3.0:1, with new probes for the float
value, the float label and the highlighted month band. Board order, persistence
20/20, ingest and the baseline render all re-run clean.

### TEST-28 detail

**Marker placement**, measured across the whole rendered board:

| Assertion | Result |
|---|---|
| A lone marker is centred in its cell | **186 of 186** cells |
| Cells sharing markers offset along x | 5 of 5, distinct x for every marker |
| and alternate above and below | 5 of 5 |
| No centre inside the 10% clearance | **0 violations**; tightest actual clearance 28% |
| Row heights preserved by the strut | unchanged |

**The first reading said 0 of 186 were centred, and the probe was wrong.** Every
marker measured 1.4% off on both axes, a consistent 0.5px. An absolutely
positioned element resolves its percentages against its containing block's
**padding box**, while `getBoundingClientRect()` on the cell returns the
**border box**, and this table's cells carry a 1px bottom and 0.5px right
border. Measured in the frame the marker is actually positioned in, all 186 are
exact. Same family as the standing "measure the element, not its parent" trap,
and recorded because the first number looked like a total failure of the change.

**N=3 was tested, not just the N=2 the board happens to contain.** The reference
schedule never puts more than two markers in one cell, so three, four and five
were cloned into a real cell and measured:

| Markers in one cell | Centres (x,y as % of cell) | Clearance violations |
|---|---|---|
| 3 | 24,28 · 50,72 · 76,28 | 0 |
| 4 | 11,28 · 37,72 · 63,28 · 89,72 | 0 |
| 5 | 10,28 · 30,72 · 50,28 · 70,72 · 90,28 | 0 |

**A limit found rather than assumed (TD-78).** At three or more, the icons
overlap slightly at the default 36px week column: three 15px icons do not fit a
36px cell however they are arranged. Re-measured at a 60px column, the overlap
is **0** for both three and four. Widening the vertical alternation instead
would push icons past the row boundary and reintroduce the defect this change
fixes, so the column width is the right remedy.

**Title and wrap toggle.** The report title now sits in the icon bar at 13px,
`white-space:nowrap` with an ellipsis, expanding while focused for editing. The
wrap toggle defaults off, `.dname` computes `nowrap` and clips; switching it on
gives `normal` and switching back returns `nowrap`, so the control shows and
sets state in both directions.

Contrast gate 60 probes, 0 frozen, 0 below 3.0:1. Board order, persistence
20/20 and ingest all re-run clean.

### TEST-27 detail

Driven through the real `depIdRowsHtml`, `showTooltip` and `openCommentPanel`
with an ID pair taken off the board, not a hand-built fixture.

| Assertion | Result |
|---|---|
| One row per activity | 2 rows, second below the first |
| Font a step smaller | 10px to **9px**, tooltip and notes dialog both |
| IDs left aligned with each other | yes, by text range |
| Titles left aligned with each other | yes, by text range |
| Title truncated, not wrapped | `white-space:nowrap`, `text-overflow:ellipsis` |
| Notes dialog uses the same rows | same builder, same 9px, same ellipsis |
| Click-to-copy unchanged | still `#SNIP-127 | #SNIP-166` |

**The truncation is proved, not assumed.** A 400 character title was forced into
the first row and the tooltip's height stayed at 33px, with the title element's
`scrollWidth` exceeding its `clientWidth`. Asserting the CSS properties alone
would have passed even if a flex child had refused to shrink, which is the
standing trap here: `min-width:0` on `.dep-id-title` is load-bearing, because a
flex child defaults to `min-width:auto` and will not shrink below its content.

Two probes added for the new colours, since the ID and the title are now
separate colours on the dialog background rather than one inherited colour.
Contrast gate 60 probes, 0 frozen, 0 below 3.0:1.

Baseline render unchanged at 163 rows / 196 markers / 159 tasks / 198
milestones; board order, persistence 20/20 and ingest all re-run clean.

### TEST-26 detail

Every item measured against a real render rather than read off the diff.

| Requested | Measured |
|---|---|
| No derived-weights remark on generated rows | rows carrying that note: **0** (ingest path and the baked seeds) |
| Columns collapsed by default | `colState` all false; a `col-ref` cell and its `colgroup` entry both `display:none` at first paint |
| Milestone labels off by default | `.m-lbl` `display:none`; the toggle unchecked |
| View Controls on the right | open state flush to the viewport's right edge; closed 300px clear of it |
| Its launcher beside Settings | `btn-style-icon` immediately precedes `btn-settings-icon` in the icon group |
| App name and version top right | label right-aligned, icon group still hard against the right edge |
| Report details under the subtitle | details left edge matches the title's text left edge; details sit below the subtitle |
| Comments icon fits its button | 26x26 button, 24x24 content, no overflow |
| Gutter spacing, remarks aligned to the title | gutter gap 9px, fixed 42px; **title text and remark text both start at x=52** |
| Subtitle wording | exact string asserted |
| Predecessor / dependency lists | two columns side by side, comma-space joined, collapsed by default, hidden for a milestone with no id |
| Search inline with the filters | search inside `#top-filter-bar`, the separate header row gone, bar open by default on its grey panel |

Controls were then driven in both directions: Show All Columns makes the ref
cell `table-cell`, Hide All returns it to `none`, and the label toggle brings
`.m-lbl` back to `block`. A control that changes a default has to still work in
both directions, which is the standing rule here.

**Two defects found by measuring, both invisible in the diff.**

TD-70: `.remarks` set `margin-left` twice in the same rule. The new gutter
indent was written first and the original `-3px` second, so the later
declaration won and the indent did nothing. The remark text measured at x=49
against a title at x=52 and only a text-range measurement showed it, because
the element's box edge and its text differ by the 3px padding.

TD-69: `body.cv-open` still applied `margin-left:300px`, correct only while the
panel opened from the left. With the panel on the right the board was pushed
away from it.

**A third finding was the harness, not the app.** After the TD-69 fix the panel
still measured 300px off-screen with the open class demonstrably matching.
Chromium's `--virtual-time-budget` fast-forwards timers but does not advance the
CSS transition clock, so `getComputedStyle` reported the transition's start
value however long the probe waited. Disabling the transition and forcing a
reflow gave `translateX(0)` and a right edge flush with the viewport. Recorded
rather than quietly worked around, because on the first reading it looked like a
real layout defect and a less careful pass would have "fixed" working CSS.

Baseline render unchanged at 163 rows / 196 markers / 159 tasks / 198
milestones. TEST-25 board order, TEST-23 persistence 20/20, ingest and the
contrast gate all re-run clean.

### TEST-25 detail

The expected order is **derived from the workbook**, not typed into the test: in
this export a heading row carries indented text in the Activity ID column and an
empty Activity Name, so walking the sheet with an indent stack gives the section
in force over every activity. Band names cannot be compared one to one, because
the tag strategy rolls inner sections up into a discipline. Positions can, and
that is the assertion: place each board band back onto the sheet by the row of
its first activity, and require those rows to strictly increase.

**On v3.1.0-P22** the board walks the schedule top to bottom:

| Board band | First activity | Sheet row |
|---|---|---|
| Key Milestones | SNIP-101 | 2 |
| Inputs From Others | SNIP-136 | 28 |
| Project Management | SNIP-105 | 36 |
| Engineering: Process | SNIP-118 | 49 |
| Engineering: Mechanical & Piping | SNIP-128 | 69 |
| Engineering: Layout | SNIP-300 | 86 |
| Engineering: Civil | SNIP-146 | 97 |
| Engineering: Structural & Concrete | SNIP-215 | 118 |
| Engineering: Electrical & Instrumentation | SNIP-124 | 131 |
| Engineering: Site Services | SNIP-202 | 160 |
| Project Execution Plan / Schedule | SNIP-214 | 162 |
| Capital and Operating Cost Estimate | SNIP-232 | 173 |
| Financial Model | SNIP-242 | 182 |
| Technical Report | SNIP-255 | 189 |

Strictly increasing, and the board opens with the section the schedule opens
with.

**Run against the shipped v3.1.0-P21 the same check fails**, which is what makes
it worth having: seven bands out of order, the board opening on Capital and
Operating Cost Estimate at sheet row 167 while Key Milestones at row 2 came
fourth. That reproduces the user's report exactly.

**The first version of this check passed for the wrong reason (TD-66).** It
looked for heading rows with an empty Activity ID column, which is the inverse of
this export's shape, so it derived nothing, printed an empty expected list, and
fell through to a weaker id-monotonicity heuristic that happened to pass. An
empty derivation now exits with an error instead.

Baseline render unchanged at 163 rows / 196 markers / 159 tasks / 198
milestones. The seeds carry no WBS and form a single ungrouped band, which is
why the shipped board never showed this defect and only a real import exposed it.

### TEST-24 detail

**The header.** `--color-bg-header` moved from `#a6bbdc` to `#2e4f82`, which is
what the user chose when given the TD-50 options. Measured, both themes:

| Text on the header | Light `#2e4f82` | Dark `#15182F` |
|---|---|---|
| `--color-text-on-header` `#f4f5f8` (requested) | **7.53:1** (was 1.79:1) | 16.00:1 |
| `--color-text-on-header-muted` `#c4d2e8` (new) | **5.37:1** | 11.41:1 |
| `--color-text-on-accent` `#ffffff` (`.sd-hd`) | 8.21:1 | 17.45:1 |

Darkening moved every text colour on that surface, which is exactly the TD-46
trap. Values that would have shipped broken if the token had not been split:
`--color-text-on-panel-muted` at **1.22:1**, `--color-text-ink` (the report
title) at **2.14:1**, `--color-text-note` (the field divider) at **2.53:1**.
None of the three was a new defect introduced here; each was a pairing that
only worked because the header happened to be light.

**The contrast gate is green for the first time since v3.1.0-P15.** 58 probes,
0 frozen, 0 below 3.0:1, exit 0.

Two probes were reclassified from `toggle` to `constant`: the sticky search
icon and clear button. They moved from a themed panel token to the non-themed
header token, so they are no longer expected to differ between themes. Both
headers are now dark and take the same light text. Recorded because
reclassifying a probe is indistinguishable from silencing one unless the reason
is written down.

**A defect the sweep found (TD-64).** Adding a probe for every consumer of
`--color-bg-header` caught two that use it as a *text* colour rather than a
background. At `#a6bbdc` that was 1.79:1 on the panel; in dark it was the navy
header on a dark panel at **1.31:1**, and had been since the dark palette was
written. Now `--color-text-emphasis`, themed per surface.

**The data date rule**, driven through the real function rather than
reimplemented:

| From | Returns |
|---|---|
| Sun 6 Sep … Thu 10 Sep | 4 Sep (the Friday just gone) |
| **Fri 11 Sep** | **11 Sep, the same day** |
| Sat 12 Sep | 11 Sep |
| Thu 1 Oct (month boundary) | 25 Sep |
| **Fri 1 Jan 2027** (year boundary) | **1 Jan 2027, the same day** |

**The republish chain.** A file already carrying two publish entries, published
again through the real `publishStatePayload()`: three entries, the original
first entry preserved, the last entry stamped with this build and sharing the
payload's own `publishedAt`.

### TEST-23 detail

`tools/persist_check.py`. The question is asked in three places because the three
paths had drifted apart before and nothing tested them together.

Both downloads are captured by stubbing `URL.createObjectURL` at the app's
boundary with the browser, so the payloads asserted are the ones the real
`publishDashboard()` and `exportModel()` produce. Nothing is reimplemented.

**Stage 1 — one of every kind of edit**, against the real functions: a drag
through `moveMilestoneToRow()`, a milestone comment, a health override, a custom
short title, a dependency-line comment, row health and a remark set on the
rendered row, and a row removal through `deleteRow()`.

**Stage 2 — the published file, opened cold.**

| Assertion | Result |
|---|---|
| Dependency-line comment | present |
| Milestone comment, health override, short title | all present |
| Milestone sits on the row it was dragged to | yes |
| Row health and remark applied to the rendered row | yes, after the TD-59 fix |
| Removed row stayed removed | yes |
| Move and removal records carried as history | yes |
| Markup line describes the edits rather than "no markup edits yet" | yes |

**Stage 3 — replay onto a clean board that has never seen any of it.** This is
the case a merge cannot cover and the one TD-27 was open on. The clean board is
asserted to start in the pre-move state first, so "it was already there" cannot
be mistaken for a working replay.

| Assertion | Result |
|---|---|
| Clean board starts with the milestone on its original row | yes |
| Move replays onto the new schedule | yes |
| Row removal replays | yes |
| Dependency comment imports | yes |
| Importing the same file twice changes nothing further | yes, no extra move records |

**Two probe faults, recorded because both first read as product defects.** The
first run put the row override and the row deletion on the same row: the row the
milestone had just left was the row that then qualified as empty, so a correctly
discarded override looked like a lost one. The second read the markup line from
an element id that does not exist, and reported an empty string as a pass. Both
are the same trap as the TEST-22 scroll container: the probe was wrong, and a
less careful reading would have produced a fix for a defect that was not there.

A third fault was real. Stage 1's output element was appended to the body before
the publish, so the published clone carried an empty copy of it and stage 2's
reader matched that one instead of its own output. The element is now created
only at the moment it is written, and the reader takes the last match.

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
| 2026-09-11 | TEST-22 heading layout and sticky search row; full suite re-run; baseline render unchanged | **Contrast gate still failing by design pending TD-50** (two probes at 1.79:1, delivered as requested). Subtitle wording is an assumption from garbled dictation. | File distribution | v3.1.0-P19 |
| 2026-09-11 | TEST-23 persistence round trip, 20/20; full suite re-run; baseline render unchanged at 163 rows / 196 markers / 159 tasks / 198 milestones | **Contrast gate still failing by design pending TD-50** (two probes at 1.79:1, delivered as requested). Replayed import categories do not yet report how many entries actually landed (TD-62). | File distribution | v3.1.0-P20 |
| 2026-09-11 | TEST-24 header darkening and token split, data date on a Friday, republish chain; full suite re-run; baseline render unchanged | **Contrast gate green, 0 below 3.0:1** for the first time since v3.1.0-P15. The `.xlsx` CDN dependency (TD-36) is still open and is now the only outstanding High. | File distribution | v3.1.0-P21 |
| 2026-09-14 | TEST-25 board order follows the schedule; full suite re-run; baseline render unchanged; contrast gate green | The schedule's inner headings within a band are still collapsed into the discipline and not shown (TD-67, with TD-23). `.xlsx` CDN dependency (TD-36) still open. | File distribution | v3.1.0-P22 |
| 2026-09-14 | TEST-26 ten presentation and default changes; full suite re-run; baseline render unchanged; contrast gate green | The schedule's inner headings within a band are still not shown (TD-67, awaiting the user's choice). `.xlsx` CDN dependency (TD-36) still open. | File distribution | v3.1.0-P23 |
| 2026-09-14 | TEST-27 dependency tooltip and notes dialog format; full suite re-run; baseline unchanged; contrast gate green | ID navigation is not built (TD-73, open). Inner band headings still not shown (TD-67). `.xlsx` CDN dependency (TD-36) open. | File distribution | v3.1.0-P24 |
| 2026-09-14 | TEST-28 marker placement, title row, activity title wrap; full suite re-run; contrast gate green | Crowded cells still overlap slightly at the default column width (TD-78). ID navigation (TD-73), inner band headings (TD-67) and the `.xlsx` CDN dependency (TD-36) all open. | File distribution | v3.1.0-P25 |
| 2026-09-14 | TEST-29 filter highlight and milestone card layout; full suite re-run; contrast gate green | ID navigation (TD-73), inner band headings (TD-67), crowded cells (TD-78) and the `.xlsx` CDN dependency (TD-36) all open. | File distribution | v3.1.0-P26 |
| 2026-09-15 | TEST-30 dependency-count chips, baseline overlay placement and the A3 print preview, 32/32; full suite re-run; baseline render unchanged; contrast gate green | The board overflows an A3 portrait sheet at the full week horizon even at the minimum column width; the preview states this rather than clipping silently. A duplicate dark-theme declaration of `--color-bg-subtle` is open (TD-88). ID navigation (TD-73), inner band headings (TD-67), crowded cells (TD-78) and the `.xlsx` CDN dependency (TD-36) all open. | File distribution | v3.1.0-P27 |
| 2026-09-16 | TEST-33 multi-source ingest Half 1, 55/55; full suite re-run (TEST-32 49/49, TEST-30 32/32, TEST-31 34/34, persistence 20/20, ingest and order exit 0); contrast gate 90 probes, 0 frozen, 0 below 3.0:1 | A single-source import still produces the P29 board exactly. Appending the reference workbook to itself gives 210 deliverables / 292 milestones with 146 suffixed Activity IDs, no duplicated id and no duplicated row ref. Compare mode, the 10% new-scope rule, generated IDs and Add Task are Half 2 and are not in this partial. TD-97 and TD-98 still open. | File distribution | v3.1.0-P30 |
| 2026-09-16 | TEST-32 settings panel design system, 46/46; full suite re-run (TEST-30 32/32, TEST-31 34/34, persistence 20/20, ingest and order exit 0); contrast gate 90 probes, 0 frozen, 0 below 3.0:1; baseline render unchanged at 159 rows / 196 markers / 159 tasks / 198 milestones and the imported board unchanged at 105 rows / 146 milestones | No behaviour or data change. Two latent contrast defects were surfaced and fixed (TD-96). Two remain open and are recorded rather than quietly patched: the four View Controls occurrences of `--color-purple-deep` on a dark panel (TD-97), and the `--color-bg-subtle` duplicate, whose consumer sweep now shows it is load-bearing for the week header (TD-98, TD-88). ID navigation (TD-73), inner band headings (TD-67), crowded cells (TD-78) and the `.xlsx` CDN dependency (TD-36) all still open. | File distribution | v3.1.0-P29 |
| 2026-09-15 | TEST-31 date range at setup and as a filter, 34/34; full suite re-run; baseline render unchanged; contrast gate green | The board no longer refills the screen width after a range narrows it; fit-to-screen and the A3 preview both do, and both now work with a filter active (TD-92). `--color-bg-subtle` duplicate open (TD-88). ID navigation (TD-73), inner band headings (TD-67), crowded cells (TD-78) and the `.xlsx` CDN dependency (TD-36) all open. | File distribution | v3.1.0-P28 |
| Pre-migration | TEST-01 full feature regression | Banding (FEAT-10), sorting/icon customisation (FEAT-11), JSON round-trip (FEAT-13) all knowingly not built. Tokenization (FEAT-14) knowingly incomplete. Label collision same-row only. Header aliases exact-match only. | File distribution | v3.1.0-P1 |
| 2026-09-09 | Migration to git repository, project kit established | TD-01 version discrepancy open; companion tokenization docs (TD-03) not yet located | Branch `p6-milestone-dashboard` | Migration commit |

---

## TEST-34 — Marker placement, and three filter-row defects (v3.1.0-P32)

`tools/p32_check.py`, **36/36**. Headless Chromium, the reference workbook through the real ingest pipeline.

**Measured first, on P31, before any edit.** Two of the three diagnoses written from reading the source did not survive it and were corrected rather than built on:

| Claim from source reading | Measured verdict |
|---|---|
| A frame mismatch pushes markers out of their row | **Refuted.** `markersOut: 0` and `labelsOut: 0` at every setting, including row 65 / ID + Title, which is the user's own configuration. The belief gap is a constant 1px (the bottom border), and at the low end of the slider the code under-estimates the row, which is the safe direction. |
| The `i%2` spread only ever produces two bands | **Confirmed exactly.** `distinctY = 2` for every N from 2 to 6. N=3 is `[28, 72, 28]`. From N=5 the same-y pair overlaps: 0.6px at N=5, 3.5px at N=6. |
| Toggling labels resizes rows without a rebuild | **Confirmed, worse than written.** 105 of 105 rows change 34.34 to 48px; 0 of 146 markers reposition. |

Two findings the probe was not looking for: the spread is a fraction of the row, so scatter grows with row height (±7.5px at 34px, ±14px at 65px), and the Row height slider's bottom of range is dead (TD-117).

### After

| Group | Assertions |
|---|---|
| Offsets | a lone marker is dead centre; **no two markers in a cell share a y, for every N from 2 to 6**; the cascade is monotonic across and down; symmetric about the cell centre; no offset can put an icon past the row it was budgeted for, checked at four icon/column/row combinations |
| Labels do not move layout | 105 rows compared; turning labels on changes **no** row height; nor does switching to ID + Title; **0 rerenders** behind the toggle |
| Containment | 8 settings, 146 markers and 146 labels each; **no marker outside its row at any setting**; a label never spills more than one line (worst 8.9px); spill never increases as the row grows; and reaches zero, so the row height control is a real remedy rather than advice |
| Ghosts | 146 of 146 paired, 0 off their pair's Y under the new transform |
| Defect A | the toggle is outside the bar it hides; hiding really collapses the bar (1px); the toggle is still laid out and clickable (`offsetParent` non-null, 26px tall); it shows the state it sets; clicking restores the bar; the bar's own hide control sits 8px from the right edge |
| Defect B | exactly one title field; it is the id `applyFilter` already reads; typing narrows the board (2 of 105); clearing restores it |
| Defect C | the week filter narrows first; the health change actually happened; **the filter survives it**; survives any other rebuild, which is where the fault really was; and the restore is bounded at the top of the range |

Marker containment by setting, labels on, ID + Title:

| Setting | Markers out | Labels out | Worst label |
|---|---|---|---|
| row 34 / ico 15 / wk 36 | 0 | 28 | 8.9px |
| row 34 / ico 24 / wk 36 | 0 | 28 | 8.9px |
| row 48 / ico 15 / wk 36 | 0 | 28 | 2.1px |
| row 65 / ico 15 / wk 36 | 0 | **0** | inside |
| row 72 / ico 24 / wk 72 | 0 | **0** | inside |

**Two assertions in the first run were wrong about the app rather than the app being wrong** (TD-118): the right-alignment check read `getComputedStyle().marginLeft` expecting the literal `auto`, which is never observable, and the ghost block measured an empty set because the baseline overlay is off by default. The sample-size rule caught the second, as designed.

`tools/p30_check.py` moves to **67/67**: its two row-height assertions encoded the coupling the user asked to be removed and are inverted, and its label-containment assertion becomes a bounded-spill assertion, with the row-height sweep that proves the remedy living in `p32_check.py`.

### Full suite at v3.1.0-P32

| Suite | Result |
|---|---|
| TEST-34 placement and filter-row defects | **36/36** |
| TEST-33 multi-source ingest | **67/67** |
| TEST-32 settings panel design system | **49/49** |
| TEST-31 date range | **34/34** |
| TEST-30 counts, baseline overlay, print | **32/32** |
| TEST-23 persistence round trip | **20/20** |
| Ingest, board order | exit 0 |
| Contrast gate | 0 frozen, 0 below 3.0:1 |
| Baseline render | unchanged, 105 rows / 146 milestones imported |

**Published:** `releases/v3.1.0-P32_marker-placement-and-filter-row-fixes.html`

---

## TEST-39 — Four defects reported against the P36 build (v3.1.0-P37)

`tools/p37_check.py`, **65/65**, at 390x844, 1440x900 and 2000x900. Five assertions are source-level.

**Two of the four were not what they looked like**, which is what the checks are shaped around.

### What each report measured before anything was changed

| Report | Measured on the P36 build |
|---|---|
| More Actions menu clipped to the header row | panel **184px tall, 0px visible**, clipped by `#icon-bar{overflow-x:auto}` (which computes `overflow-y` to auto with it) |
| ID suggestions behind the timeline | list **200px tall, 36px visible**, clipped by `#top-filter-bar{max-height:0;overflow:hidden}`, with a `TD` painting over what was left |
| Title col slider does nothing | **refuted at first**: at 1600 wide after an import it moved the column 295.3 to 380 and survived a rerender |
| Zero-dependency filter does nothing | **105 rows before, 105 after, 0 lines drawn** |

### The two popups, and the half of the fix that measurement caught

Neither ancestor overflow can be removed: `#icon-bar`'s lets the bar scroll at phone width, and `#top-filter-bar`'s **is** the collapse mechanism. Both popups became `position:fixed`, placed by one `positionFixedPopup()`.

**That was only half of it.** Freed of the clip, the menu was painted over by `#rpt-hd` and `#top-filter-bar`: `#icon-bar` is `position:relative` with a z-index and therefore a **stacking context**, so no z-index inside it, however large, lifts a descendant above a later sibling of the bar. Measured **0 of 7 rows hit-testable at 390 wide**. The bar went z-index 30 to 40, clearing those two and the table headers (max 26) while staying below the drawers (700/850/900), which still cover it.

After: **7 of 7** menu rows and **30 of 30** suggestions individually reachable, at every width.

### The Title col slider: the report was right and the first measurement was too narrow

On the board as it actually opens, the seeded baseline with the fixed columns collapsed, the column rendered **380.1px while the slider read 220px**. `#col-name` carries no width until `setNameWidth()` runs, and `setNameWidth` was in **neither** build path, so `table-layout:fixed` handed the column whatever the collapsed fixed columns left over. Dragging up from the default therefore **shrank** it to ~240 before it grew.

Fixed by `reapplyDisplaySettings()`, one function holding all five slider-owned settings, called from `rerender()` and from init's first paint. The init block already carried a comment about exactly that trap while omitting three of the five.

Measured after: column equals slider at first paint (220/220), tracks exactly across 140/200/260/320/400, moves monotonically, and survives a rebuild.

### The zero-dependency filter: a control whose label and behaviour disagreed

Its tooltip promised *"Show only milestones with zero predecessors/dependencies"* and it gated dependency-**line** drawing, which is invisible until dependencies are switched on. It narrows the board now, from inside `applyFilter()` so it composes with the other filters and is reapplied on rebuild.

| Mode | Rows (baseline board, dependencies off) |
|---|---|
| All | 159 |
| Only zero | **46** |
| Hide zero | **113** |

The two are complements (46 + 113 = 159), 50 of 193 milestones carry no dependencies, and the filter line states what it narrowed to. Asserted with **0 dependency lines drawn**, so nothing else could have produced the change.

### The measurement that was wrong about a working fix

The clipping-aware ancestor walk written at P36 reported the fixed panel as 0px visible, exactly as it had reported the absolute one: it walks the DOM chain intersecting overflow boxes, and **a fixed element is not clipped by ancestor overflow at all**. `elementFromPoint` at a single centre point was no better, returning false for a panel that was genuinely on top.

What answers it is a hit-test **profile**: what paints at several points down the popup, plus how many of its children are individually reachable. **Third consecutive partial in which the measurement technique, not the code, was the thing that was wrong** (TD-133, TD-136, TD-140).

### Found and deliberately not fixed

`drawUnresolvedStub()` emits the same `zero-stub` class as a true zero stub while meaning "N not on board". Any CSS rule or probe targeting zero stubs catches both. **TD-141, open** — nothing reported it, and changing a class the dependency layer keys on is its own change with its own verification.

### Full suite at v3.1.0-P37

| Suite | Result |
|---|---|
| TEST-39 four P36 defect reports | **65/65**, across three viewport widths |
| TEST-38 More Actions consolidation | **95/95** |
| TEST-37 milestone card rework | **117/117** |
| TEST-36 marker anchoring and header heights | **73/73** |
| TEST-35 marker staggering | **38/38** |
| TEST-34 placement and filter-row defects | **36/36** |
| TEST-33 multi-source ingest | **67/67** |
| TEST-32 settings panel design system | **49/49** |
| TEST-31 date range | **34/34** |
| TEST-30 counts, baseline overlay, print | **32/32** |
| TEST-23 persistence round trip | **22/22** |
| Ingest, board order | exit 0 |
| Contrast gate | 0 frozen, 0 below 3.0:1 |

**Published:** `releases/v3.1.0-P37_popup-layering-and-filter-fixes.html`

---

## TEST-38 — The More Actions consolidation (v3.1.0-P36)

`tools/p36_check.py`, **95/95**, at 390x844, 768x1024 and 1440x900. Five assertions are source-level, including the one that carries the most weight.

### The before/after, measured in the same browser at the same viewports

| Width | Buttons | Icon group | Label got | Label needs | Clipped |
|---|---|---|---|---|---|
| 390 before | 7 | 254px | 35.2px | 216px | yes |
| 390 after | 1 | 26px | **167px** | 216px | **still yes (TD-135)** |
| 768 before | 7 | 254px | 162px | 216px | yes |
| 768 after | 1 | 26px | **215.8px** | 216px | no |
| 1440 before | 7 | 254px | 215.8px | 216px | no |
| 1440 after | 1 | 26px | 215.8px | 216px | no |

228px of header width returned at every viewport.

### Groups

| Group | Assertions |
|---|---|
| Header | one button in the bar, not seven; the previous release really did carry seven; 228px reclaimed; the label gets its full width where the bar has room, and where it does not the residual clip is stated with its figures rather than passed over; the bar still does not scroll; the label still names the app and its version |
| Rows | all seven ids survive; every row still calls the live function its button called, parsed from the `onclick` and checked against `window`, because a handler naming a dead function throws only when clicked |
| Menu | starts closed with 0 of 7 rows visible; the trigger opens it and **it stays open**; 7 of 7 rows visible; `aria-expanded` follows; Escape closes; a click outside closes; choosing a row closes it behind them |
| State | Settings, View controls, the filter row and print preview each toggle **through the menu row**, not by a direct call; `aria-pressed` still tracks; and the active row **actually paints** differently from an inactive one |
| Theme | the theme flips and the glyph changes with it, and rewriting the glyph does not eat the row's label |
| Dots | none on the trigger when neither row carries one; a filter dot reaches it; a settings dot reaches it; clearing them clears it, both directions |
| Source | one version literal; the state-writing functions byte-identical to the previous release; the active-row rule restated rather than left to source order; the trigger's dot derived rather than written; one theme-glyph writer |

### The assumption the run refuted

**The label is still clipped at 390.** The check was written expecting the consolidation to clear it everywhere. It does not: the bar at phone width also carries the editable report title, so 216px of label plus that title plus the trigger does not fit in 390px. The gain is real (35.2px to 167px, 4.7x) and the residual clip is now asserted as a stated limit with its figures printed, conditional on **measured room** rather than on a viewport width typed into the check. A hardcoded "768 and above" would have been a constant standing in for a measurement, which is the recurring defect family here. Logged as TD-135, open, because resolving it is a design call on what gives way at phone width.

### The regression, and the measurement that was wrong about it

`p32_check`'s TD-72 assertion, that the filter-row toggle stays on screen when the filter row is hidden, failed. The rule TD-72 records is that the control **outlives what it hides**, and it still does: the trigger outlives the bar and exposes the toggle. So the assertion was rewritten to follow the path rather than to test for a visible header button.

**A negative control was then added, and the first rewrite passed it**, which is how the rewrite was found to be measuring the wrong thing. Putting the toggle back inside the collapsed bar, which is the TD-72 state exactly, it reports:

| | trapped in the collapsed bar |
|---|---|
| `offsetParent !== null` | **true** |
| height | **24px** |
| `getClientRects().length` | **1** |
| `checkVisibility()` | **true** |
| box intersected with clipping ancestors | **0px** |

`max-height:0; overflow:hidden` does not zero its children's boxes, so every obvious API says the trapped control is fine. `elementFromPoint` did not discriminate either. The guard now intersects the element's box with every clipping ancestor and **demonstrably fails when the defect is reintroduced**, which is asserted as its own check rather than assumed.

Worth holding onto: `checkVisibility()` answered the closed-`<details>` case at TEST-37 and is wrong here. It is container-specific, not a general answer to "is this hidden".

### Full suite at v3.1.0-P36

| Suite | Result |
|---|---|
| TEST-38 More Actions consolidation | **95/95**, across three viewport widths |
| TEST-37 milestone card rework | **117/117** |
| TEST-36 marker anchoring and header heights | **73/73** |
| TEST-35 marker staggering | **38/38** |
| TEST-34 placement and filter-row defects | **36/36**, TD-72 guard rewritten and given a negative control |
| TEST-33 multi-source ingest | **67/67** |
| TEST-32 settings panel design system | **49/49** |
| TEST-31 date range | **34/34** |
| TEST-30 counts, baseline overlay, print | **32/32** |
| TEST-23 persistence round trip | **22/22** |
| Ingest, board order | exit 0 |
| Contrast gate | 0 frozen, 0 below 3.0:1 |

**Published:** `releases/v3.1.0-P36_more-actions-menu.html`

---

## TEST-37 — The milestone card rework and the editable Progress field (v3.1.0-P35)

`tools/p35_check.py`, **117/117**. Headless Chromium, the reference workbook through the real ingest pipeline, run at three viewport widths (390x844, 768x1024, 1440x900). Seven of the assertions are source-level greps, for the standing reason: a literal that happens to be correct measures as correct.

The card is driven the way a user drives it. Cards are opened by dispatching a click on the marker, the field is changed by setting its value and firing `input`, and it is committed by blurring it, so the path under test is the one the markup wires up rather than a direct call to `saveMsProgress()`.

| Group | Assertions |
|---|---|
| Shrink | the card renders at 306px, which is 340 x 0.9 exactly; **and is 10.0% narrower and 22.6% shorter than the P34 release** measured in the same browser, at the same viewport, on the same milestone |
| The row | Start, Finish and Progress all overlap vertically (every pair, not just against the first); Progress is the right-hand field; a 1px left border on the Progress field falls between Finish's right edge and Progress's left edge; every value in the row is one computed text size. Re-measured on a milestone carrying a real start date so **three** boxes are compared, and separately confirmed that P34's two date sizes really did differ (18px against 14px) |
| The fold | weight, MS hours and earned hours are in a `<details>` that is closed on open, `checkVisibility()` false on all three while shut and true on all three when open, the fold's own height 16px to 66px; **and closed again on the next card**, not left where the last one was put |
| The key | every one of the 146 milestones examined for a divergence between `msKeyFor()` and the notes id (**0 found**, so the alignment is hygiene on this dataset rather than a live fix), and the key the card writes equals `msKeyFor(m)` |
| The override | the committed value reaches the store; the field keeps it and stays marked as edited; the progress bar tracks it; **the row rollup moves 0% to 45%**; the milestone tooltip reports 45%, not the schedule's 0%; it counts as markup; committing an unchanged field adds none |
| The three layers | every milestone record snapshotted before the edit and compared after: **all 146 unchanged** |
| Restoring | clearing the field deletes the override rather than saving a blank, the field shows the schedule's value again unmarked, and the rollup goes back with it; entering the schedule's own value leaves no override behind; text that is not a number restores; over 100 shows 100 and under 0 shows 0 |
| Complete | marking the icon complete sets Progress to 100% and the row follows; a milestone the schedule already has at 100% gains **no** redundant override |
| Payload | progress overrides are their own selectable annotation category |

### Round trip (TEST-23 extended), `tools/persist_check.py`, **22/22**

A progress override is now one of the edits stage 1 makes. It survives publish, and stage 3 replays it onto a clean board that has never seen it: the override restores at 37% **with the milestone record still reading its schedule value of 100%**. The check refuses to pass if the override it chose happens to equal the schedule's own value, which would make restoring it prove nothing.

### Four findings from the run

- **A rect inside a closed `<details>` measures nothing.** The fold assertion required zero height on the three fields and got non-zero at every width. Verified against a three-line page in the same build: a child of a closed `<details>` reports a non-zero rect here, for a plain div and for a grid. `checkVisibility()` distinguishes the two states and is what the check uses, with the fold's own height as a second read. Sixth headless measurement artefact in this project.
- **The tooltip assertion read a detached node.** It used the wrap handle captured before the edit; a commit rerenders the board, so that handle still carried its pre-edit tooltip. Re-queried after the rebuild, the tooltip is correct.
- **The clamp assertion was measuring the wrong rule.** It read the store after typing `-5`. The target's schedule value is 0 and `-5` clamps to 0, so the store correctly held nothing and the check was testing deduplication rather than clamping. It now asserts the effective value the user sees.
- **The three-field row assertion was comparing two fields.** The first suitable target carries no separate start date, so its Start field is `display:none`. Second time a milestone-card assertion has compared against a field that was not rendering (TEST-29). A milestone with a real start date is now opened on purpose for that case.

### Full suite at v3.1.0-P35

| Suite | Result |
|---|---|
| TEST-37 milestone card rework | **117/117**, across three viewport widths |
| TEST-36 marker anchoring and header heights | **73/73** |
| TEST-35 marker staggering | **38/38** |
| TEST-34 placement and filter-row defects | **35/35** |
| TEST-33 multi-source ingest | **67/67** |
| TEST-32 settings panel design system | **49/49** |
| TEST-31 date range | **34/34** |
| TEST-30 counts, baseline overlay, print | **32/32** |
| TEST-23 persistence round trip | **22/22**, extended with a progress override |
| Ingest, board order | exit 0 |
| Contrast gate | 0 frozen, 0 below 3.0:1 |

**Published:** `releases/v3.1.0-P35_milestone-card-and-progress-override.html`

---

## TEST-36 — Marker anchoring and the measured header heights (v3.1.0-P34)

`tools/p34_check.py`, **73/73**. Headless Chromium, the reference workbook through the real ingest pipeline, **run at three viewport widths** (390x844, 768x1024, 1440x900) because one width cannot tell a measured height from a constant that happens to be right.

Six of the assertions are source-level greps rather than measurements, for the same reason: a literal that happens to be correct measures as correct.

| Group | Assertions |
|---|---|
| Sequence | against the generator for n = 1 to 8: run of one is the middle band; run of two is top then bottom, leftmost up; run of three cascades top, middle, bottom; **the fourth resets to the top**, reversing TEST-35; the fifth is middle and the sixth bottom; no two adjacent markers in a run share a band |
| Run boundary, both bounds | the threshold is a gap of three columns, i.e. two blank ones. Outer bound: 95 markers further than that from both neighbours, **0 off centre**. Inner bound: 3 markers at exactly the threshold, **0 runs wrongly broken** |
| Pair rule | four cases (same cell and different cells, at three bands and at five), all symmetric about the midpoint with the leftmost up; the same-cell case now matches the different-cell case exactly |
| SNIP-212 | its row still carries four markers in adjacent columns 18 to 21, and **it sits on the top band**, measured at all three widths |
| Header seam | six display states (after import, two slider combinations, print mode, fit to screen, and back to default): the week band sticks exactly at the month row's measured height, **seam 0.00px in every one**, at every width; the offset is not 19.5px; `--hdr-phase-h` is written rather than left on its fallback |
| Filter bar | open, closed and reopened at each width: **nothing clipped while open**, collapses to 0 when closed, and the cap is not the old 160px |
| Board effect | run lengths and band distribution reported, not predicted, so the cost of the plain repeat stays visible |
| Containment | 146 markers, **0 outside their row**, at every width |

### What the three reported cases measured before anything was changed

| Case | P33 build |
|---|---|
| Row 69, SNIP-212 | four markers at columns 18, 19, 20, 21 on the triangle wave, SNIP-212 on the middle band |
| SNIP-218 / SNIP-219 | **different rows**, each the only marker in its row, both dead centre, at 1600 and at 390 wide |
| Month header row | renders 16.00px against a hardcoded 19.5px sticky offset |
| Filter bar at 390 wide | content 202px in a 159px box |
| Filter bar at 1600 wide | 63px in 63px, nothing clipped |

### Two findings from measuring first

- **A diagnosis written from the source was refuted for the third time in three partials** (TD-129). The plan named a same-cell pair rule as the cause of the SNIP-218/219 markup. The two markers are in different rows and both already centred, so the rule it blamed was not what rendered. The pair rule was still wrong and is fixed, but as an inconsistency with no visible effect, which is what the check reports.
- **The obvious fix for SNIP-212 does not work, and arithmetic caught it rather than a build.** Capping a run at three members splits row 69 into a run of three and a run of one, and a run of one is the middle band by definition, so SNIP-212 would have landed back where it started. The cycle itself had to change.

### Full suite at v3.1.0-P34

| Suite | Result |
|---|---|
| TEST-36 marker anchoring and header heights | **73/73** |
| TEST-35 marker staggering | **38/38**, two sequence assertions moved with the reversal |
| TEST-34 placement and filter-row defects | **35/35** |
| TEST-33 multi-source ingest | **67/67** |
| TEST-32 settings panel design system | **49/49** |
| TEST-31 date range | **34/34** |
| TEST-30 counts, baseline overlay, print | **32/32** |
| TEST-23 persistence round trip | **20/20** |
| Ingest, board order | exit 0 |
| Contrast gate | 0 frozen, 0 below 3.0:1 |

**Published:** `releases/v3.1.0-P34_marker-anchoring-and-compact-header.html`

---

## TEST-35 — Proximity-scoped marker staggering (v3.1.0-P33)

`tools/p33_check.py`, **38/38**. Headless Chromium, the reference workbook through the real ingest pipeline.

The rule: a marker's vertical position is a property of the marker, and the label is a child of its wrap, so it rides whatever the wrap does.

| Group | Assertions |
|---|---|
| Sequence | asserted against the generator for n = 1 to 8, because the board's densest cell holds two markers and cannot reach the case: run of one is the middle band; run of two is top then bottom, leftmost up; run of three cascades top, middle, bottom; **the fourth is the middle band, not a repeat back to top**; the fifth returns to top; no two adjacent markers in a run share a band; every level is one of the three |
| Budget | no band offset can put an icon past the row it was budgeted for, across five icon/row combinations and three to six bands; three bands never grow the row; four or more do, monotonically; band count follows the densest cell |
| Label rides its icon | 146 of 146 label stacks centred on their own wrap, asserted **per marker**; no element carries an independent offset or a band class |
| Factory | 146 positioned wraps, all carrying both offsets; the flow-layout LoE variant carrying neither |
| Ghosts | 146 paired, **0 off their pair**, so the ghost inherited the band through the shared writer |
| Labels do not move layout | 105 rows identical with labels off, on and in ID + Title; 0 rerenders behind the toggle |
| Containment | 7 settings, 146 markers each, **0 outside their row at any setting** |
| Hidden markers | the derived test and the zero-rect measurement agree on all 146 markers under no filter, a week filter, a date range, all three combined, and after clearing; 641 dependency paths still drawn |
| Same-cell overflow | four clones forced into one cell (densest cell 5): that row grew to 64px, every marker in it got its own line, and **1 of 105 rows changed height** |

### Spill, measured against the P32 release with the same corrected sweep

| Setting | P33 out | P33 worst | P32 out | P32 worst |
|---|---|---|---|---|
| row 28 / ico 15 / wk 36 | **0** | 0.4px | 28 | 8.9px |
| row 34 / ico 15 / wk 36 | 31 | 3.4px | 28 | 8.9px |
| row 34 / ico 24 / wk 36 | **0** | inside | 28 | 8.9px |
| row 34 / ico 10 / wk 20 | 31 | 7.3px | 28 | 10.3px |
| row 48 / ico 15 / wk 36 | **0** | 0.1px | 28 | 2.1px |
| row 65 / ico 15 / wk 36 | 0 | inside | 0 | inside |
| row 72 / ico 24 / wk 72 | 0 | inside | 0 | inside |

Total labels outside their row across the sweep: **62, down from 140.** No setting spills deeper than it did. The count rises at 34px because a proximity run is wider than P32's per-cluster reset, so more markers are banded, which is the feature; the depth, which is what decides whether a label lands on a neighbouring row, falls everywhere.

### Four defects found by verification

- **Three probes were measuring nothing** (TD-123). `p30_check`, `p32_check` and the screenshot probe drove placement through `setIcoSize()` / `setWkWidth()` alone, but `rerender()` reapplies display settings by reading the slider elements back, so every call was undone by the rebuild it triggered. Found by a diagnostic that asked for a 10px icon and measured 15, while investigating an apparent 17 markers leaving their row. With the settings actually applied, that failure did not exist. The P32 spill baseline had to be re-measured before the comparison above meant anything.
- **The unfurl put the label stack under the count chip** (TD-124), reviving TD-83. Caught by `p27_check`.
- **The first same-cell implementation put two pairs on one line inside one cell**, because the level generator knew the run length but not the columns, so it could not tell reuse across cells from reuse within one.
- **The agreement assertion passed against zero markers on its first run**, because the rebuild before it left the board empty. The sample-size assertion beside it caught that, as designed.

### Full suite at v3.1.0-P33

| Suite | Result |
|---|---|
| TEST-35 marker staggering | **38/38** |
| TEST-34 placement and filter-row defects | **35/35**, two assertions inverted to the new contract |
| TEST-33 multi-source ingest | **67/67** |
| TEST-32 settings panel design system | **49/49** |
| TEST-31 date range | **34/34** |
| TEST-30 counts, baseline overlay, print | **32/32** |
| TEST-23 persistence round trip | **20/20** |
| Ingest, board order | exit 0 |
| Contrast gate | 0 frozen, 0 below 3.0:1 |
| Baseline render | unchanged, 105 rows / 146 milestones imported |

**Published:** `releases/v3.1.0-P33_proximity-marker-staggering.html`
