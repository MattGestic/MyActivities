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
| Pre-migration | TEST-01 full feature regression | Banding (FEAT-10), sorting/icon customisation (FEAT-11), JSON round-trip (FEAT-13) all knowingly not built. Tokenization (FEAT-14) knowingly incomplete. Label collision same-row only. Header aliases exact-match only. | File distribution | v3.1.0-P1 |
| 2026-09-09 | Migration to git repository, project kit established | TD-01 version discrepancy open; companion tokenization docs (TD-03) not yet located | Branch `p6-milestone-dashboard` | Migration commit |
