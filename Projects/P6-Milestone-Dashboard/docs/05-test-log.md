# P6 Milestone Dashboard — Test Log

## AI / Automated Tests (Gate 5a — mandatory before any live user test)

| ID | Date | Scope | Framework used | Pass/Fail | Defects raised |
|---|---|---|---|---|---|
| TEST-01 | 2026-09-09 (pre-migration) | Full regression audit of v3.1.0-P1 against every major feature built across the chat development history. Direct file inspection, not assumed. | Feature-presence checklist | Pass — no drops or regressions | None |
| TEST-02 | Pending | Live ingest of `data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx` through the `.xlsx` import path | EARS | Not run | TD-04 |
| TEST-03 | 2026-09-09 | Post-migration smoke test: does the committed `src/milestone-dashboard.html` still open and render the baked-in baseline correctly after the file move | Headless Chromium render, DOM assertion | Pass | None |
| TEST-04 | 2026-09-09 | Tokenization audit reproducibility: does an independently written implementation of the documented audit method reproduce the v1 Measurement Log figures | Reconciliation against v1 output | **Fail** — v1 figures not reproducible at full documented scope | TD-06, TD-07 |
| TEST-05 | 2026-09-09 | Theme toggle: does every probed element's computed colour change between light and dark, before and after the v3.1.0-P2 tokenization pass | `tools/theme_check.py`, computed styles, EARS | Pass after fix (before: 7 of 16 frozen) | None outstanding |
| TEST-06 | 2026-09-09 | Post-change regression: does the dashboard still render the baked-in baseline unchanged after the tokenization pass and version bump | Headless Chromium render, DOM assertion | Pass | TD-10 raised from the finding below |
| TEST-07 | 2026-09-10 | Board tokenization: do rows, columns, marker labels, icons and status toggle correctly, and does any text lose contrast against its own background | `tools/theme_check.py` with board probes + WCAG contrast, EARS | Pass after one revert | None outstanding |
| TEST-08 | 2026-09-10 | Post-change regression after the v3.1.0-P3 board pass | Headless Chromium render, DOM assertion | Pass | None |

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
| Pre-migration | TEST-01 full feature regression | Banding (FEAT-10), sorting/icon customisation (FEAT-11), JSON round-trip (FEAT-13) all knowingly not built. Tokenization (FEAT-14) knowingly incomplete. Label collision same-row only. Header aliases exact-match only. | File distribution | v3.1.0-P1 |
| 2026-09-09 | Migration to git repository, project kit established | TD-01 version discrepancy open; companion tokenization docs (TD-03) not yet located | Branch `p6-milestone-dashboard` | Migration commit |
