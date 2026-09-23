# Lessons Learned — Eskay Creek PFS Dashboard Development

Short-form, grouped by pattern. Each one caused a real bug or wasted a cycle. Purpose is prevention, not record-keeping.

**Scope:** sections 1 to 4 and 6 are specific to this project and stay here. Two items in section 5 were promoted to repository-wide standards on `main-projects-hub` because they apply to every project, not just this one — see section 7. They are kept here as well, so this document still reads as a complete history of what was learned when.

**Read this alongside `CLAUDE.md`.** Where a lesson hardened into a rule, the rule is in `CLAUDE.md` and the reason it exists is here.

---

## 1. Verification methodology

| Issue | Root cause | Recommendation |
|---|---|---|
| Claimed sticky headers were broken based on a failing test | Measured the whole `<tr>`'s bounding box instead of a specific sticky cell inside it — the row itself was never sticky, only cells within it were | When verifying a CSS property on a specific element, measure that element directly, not a parent that may behave differently |
| Misread a screenshot as showing the wrong button highlighted | Trusted a visual read of a small, compressed image over the actual computed style | For state checks (active/selected/checked), read `classList`/computed style directly — screenshots are for the user, not for self-verification |
| Reported "no regression" based on code review alone, more than once | Code that looks correct can still have a runtime-only bug (browser quirks, event timing, CSS specificity) | Test the actual interaction (click, hover, drag) and check resulting DOM/computed state — never conclude "fixed" from a diff alone |

## 2. Edge cases and boundaries

| Issue | Root cause | Recommendation |
|---|---|---|
| `dateToCol()` clamped dates before the visible horizon onto column 0 instead of excluding them | The out-of-range check only tested the upper bound (too late), never the lower bound (too early) | When a range check has two directions, write and test both — a one-sided guard is a common, easy-to-miss bug |
| First fix for the above was itself too aggressive, would have excluded valid first-week dates | Used the week-*ending* date as the cutoff without accounting for the days before it in that same week | Boundary fixes need boundary tests on both sides (just-inside, just-outside) before deploying, not just the one failing case |
| Label collision system re-collided on the 3rd marker in a tight cluster | Built for the 2-marker case (simple alternating toggle) without checking what happens at 3+ | When building a "handle N of something" system, explicitly test N=3 even if the reported case only showed N=2 |

## 3. Incomplete wiring (code exists, isn't connected)

| Issue | Root cause | Recommendation |
|---|---|---|
| Dependency lines went stale after any unrelated UI action | `drawDepLines()` was never added to the main `rerender()` cascade when other features started calling `rerender()` | When a render pipeline gains a new stage, audit every existing entry point that should trigger it — don't assume it's already wired in |
| Hover tooltips never worked on real milestones, only on baseline ghosts | Tooltip content/attributes were correctly built, but the `mouseenter` listener was only ever attached to ghost markers | "The code to do X exists" is not the same as "X is wired up" — check the actual event binding, not just the handler function |
| Dependency All-on/All-off buttons never reflected which state was active | Built as one-way action triggers without considering they represent a togglable state a user needs to see | Any control that sets a state should also visually reflect that state — build both directions together, not the action first and feedback later |
| A published file showed every annotation except row health and remarks, which were in the file and correct | Those two are parked in `PENDING_ROW_OVERRIDES` because they key on rendered rows. `rerender()` drains that queue; the init path builds the first paint through `renderRows()` directly and never did. Two code paths that must end in the same state, only one of which was kept up to date | **Third instance of this exact shape** (import teardown in P13, seed-versus-baseline reads in P16). When state is deferred to "whenever the next rebuild happens", find every path that produces a rebuild — the first paint is one of them, and it is the path a reader of a published file always takes |
| Dependency-line comments were dropped by both the publish and the export | Every other annotation store was added to both payloads as it was built; this one was written months earlier, lived beside the dependency-drawing code rather than with the other stores, and was never added to either | A store is not "saved" because the feature that writes it works. Persistence is a property of the payload, so the test has to enumerate the stores and assert each one, rather than asserting the ones it remembers |
| A background token used as a text colour, invisible in one theme for as long as that theme existed | `--color-bg-header` coloured bold values in the source box. In light it happened to read as blue emphasis; in dark it was the navy header on a dark panel at 1.31:1. No probe, because the probe list was built per component and nobody thought of a background token as something that needs a contrast check | When a colour token changes role, it stops being covered by whatever checked it before. Probe **per text colour that lands on a background**, not per component, and include the tokens being used against their own name |
| A check derived its own expected value, derived nothing, and passed anyway | The TEST-25 probe looked for heading rows with the wrong shape, got an empty list, printed an empty "expected" section and fell through to a weaker heuristic which passed | A derivation that returns nothing is a broken check, not a passing one. Assert the derivation produced something BEFORE asserting anything with it, and prove the check fails on the unfixed build |
| The board reordered the client's schedule for as long as import existed, and no test noticed | The rule "present it in the schedule's order" was assumed by everyone and written down nowhere, so nothing asserted it. The baseline seeds carry no WBS, so the shipped board looked fine and only a real import exposed it | An expectation nobody wrote down is an expectation nothing tests. When a user says "we agreed X", check whether X is recorded: if it is not, that absence is itself the finding |
| A CSS transition never completed under the headless probe, so a correct rule read as broken | Chromium's `--virtual-time-budget` fast-forwards timers but does not advance the CSS transition clock. `#filter-bar.open` matched, `matches()` returned true, and `getComputedStyle` still reported the start value however long the probe waited | **Third virtual-time artifact in this project.** When probing anything behind a `transition`, set `style.transition='none'` and force a reflow before reading, or assert the class rather than the animated value. A computed value that will not move while the selector demonstrably matches is the harness, not the CSS |
| A panel moved side, and the page kept being pushed the old way | `body.cv-open{margin-left:300px}` was written when View Controls opened from the left. Moving the panel changed its own CSS but not the rule that makes room for it, so the board shifted away from the panel and the panel fell off the viewport | A panel's open-state page offset belongs to the panel. When moving one, grep for every rule keyed on its open class, not just the rules that name the panel |
| Every marker measured 0.5px off centre, and the placement was exact | An absolutely positioned element resolves percentages against its containing block's **padding box**; `getBoundingClientRect()` on that container returns its **border box**. This table's cells carry a 1px bottom and 0.5px right border, so the two frames differ by exactly the offset seen | When checking a percentage-positioned element, build the container's padding box from its computed border widths and measure against that. A uniform small offset across every instance is a frame mismatch, not a placement bug |
| A dialog test passed on two fields that were not rendered at all | The card was opened on the first marker on the board, which is always a baseline seed. Every seed carries discipline "Unassigned" and no float, so the parent heading and the float column were both `display:none`, and the position assertions compared against zero rects | Pick the fixture by the property under test, not by whatever is first. When asserting that an element is positioned, assert it is **visible** in the same breath, or a hidden element reports a zero rect and passes every comparison |

## 4. CSS behaviors that silently break things

| Issue | Root cause | Recommendation |
|---|---|---|
| Text wouldn't wrap despite `overflow-wrap: break-word` | Flex children default to `min-width: auto`, which blocks wrapping regardless of `max-width` | Any text element inside a flex container that needs to wrap or shrink needs explicit `min-width: 0` |
| `position: sticky` silently did nothing on table cells | `border-collapse: collapse` breaks sticky positioning on table cells in most browsers — a known but easy-to-forget limitation | If sticky positioning is needed inside a `<table>`, use `border-collapse: separate; border-spacing: 0` from the start |
| Clicking a link inside a dialog immediately closed the dialog | The click handler rebuilt the link's own container via `innerHTML`, detaching the original event target before the click finished bubbling to a document-level "click outside" listener | Never mutate the DOM subtree containing the clicked element during its own click handler without `stopPropagation()` — the bubble phase will see a detached node |

## 5. Process / documentation hygiene

| Issue | Root cause | Recommendation |
|---|---|---|
| A handoff document referenced companion files that were never actually given to the user | Files existed in the working directory, but existing on disk isn't the same as being delivered — only `present_files` actually surfaces something | Any deliverable that references other files must explicitly present all of them, not just the primary document |
| Token/colour tracking docs drifted significantly out of date (numbers off by 3-4x) | The "update the log whenever a component is touched" convention only holds if every session touches token-relevant work — a long run of unrelated feature work left it stale with no trigger to revisit it | **Adopted as a standing rule (2026-09-09):** avoid static state statements in prose for anything expected to change over time. Capture such values as an append-only log (date/time, source, metric, value); prose references what a metric means and where to find its current value, never the number itself. New measurements append as rows — nothing upstream needs editing. Applied to `Token_Migration_Log.md` and `Tokenization_Path_Plan.md` as the concrete example. |

## 6. Open / unresolved

| Issue | Status |
|---|---|
| Blank Data date / Report date on a real `.xlsx` import | Could not reproduce via paste-import or code review. A "Save as HTML" snapshot of a live session does not preserve runtime JS state (e.g. `UPDATE_MILESTONES`), so a saved-HTML bug report can't be used to inspect the actual failing data — the original file or a fresh live repro is needed. Tracked as `TD-02`, retested by `AC-08` in `05-test-log.md`. |

---

## 7. Promoted to repository standards

These two proved general, not project-specific, and now bind every project in the repository. They live on `main-projects-hub` and are restated here only to record where they came from.

| Lesson | Promoted to | Rule as adopted |
|---|---|---|
| Verification methodology (section 1, all three rows) | `Governance/01-project-standard.md` → Verification standard | A code read-through is not a test. Measure the specific element, not a parent. Read `classList`/computed style, not a screenshot. Test the interaction and assert the resulting DOM state. |
| Static state statements in prose go stale (section 5, row 2) | `Governance/03-documentation-standard.md` → Append-only measurement logs | Never write a number expected to change into prose. Capture it as an append-only log row (date, source, metric, value). Prose says what a metric means and where its current value lives, never the value. New measurements append; nothing upstream is edited. |

## 8. Added after migration

| Issue | Root cause | Recommendation |
|---|---|---|
| Audit script v1 under-reported hardcoded colour by a third, and mis-stated spacing in both directions, for an unknown period | The script lived outside version control and its implementation had silently diverged from its own documented method — it matched hex only, never `rgb()`/`rgba()`, and counted token definitions as token references | A measurement tool is part of the deliverable. Commit it next to what it measures. An uncommitted script cannot be diffed, reviewed, or reproduced, and its drift from the documented method is invisible until someone reimplements it. |
| Reimplementing the audit initially produced a count 60% too high | The new script's block-matching regex required the token-definition selector to follow `}`, `,` or start-of-string, so it missed the first theme block (preceded by a comment) and a second `:root{}` rule, counting their definitions as hardcoded usage | When a script excludes regions of a file, assert the **count** of regions found against what the file actually contains. A silent under-match of an exclusion zone inflates every downstream number without erroring. |
| The fix for that made the failure visible but threw away the exception that named its cause, so the next report was a screenshot of the new message and still no diagnosis | `FileReader.onerror` carries a `DOMException` whose `name` is the entire diagnosis — `NotReadableError` (open in Excel, cloud-only OneDrive file, antivirus), `NotFoundError`, `SecurityError`. The handler wrote a generic sentence and dropped `r.error` | **Never discard a structured error to write a friendlier one.** Say what happened AND what the system reported. A user-facing message that omits the error name turns a two-minute diagnosis into another round trip. Corollary: the prediction was wrong too — the CDN was blamed and had loaded fine; the error name would have said so immediately. |
| A published file carried its data correctly and told the user it had not, so a working feature was reported as broken | The publish path replaced the baseline data but not the several places that *describe* the baseline: counts read from the original seeds, a label held in a `const`, and two strings whose wording only made sense in a non-published file. The test asserted the payload and never the description | **When a feature changes what a file is, audit everything that says what the file is.** Data and provenance are separate surfaces and only one of them was migrated. The user's report was "it didn't save" about a file that had saved perfectly — which is the expensive failure mode, because it invites re-doing work that was already correct. Assert the labels, not just the values. |
| A user reported "the Import button doesn't click"; it had clicked, and worked | The success path tore down some of the import form but not the "Ready to import / Discard / Import" panel, so a completed import still looked pending. Pressing Import again then did nothing, because the same success path had nulled `LAST_PARSE`. Two separate teardown lists had drifted apart: `cancelIngest()` cleared the panel, `runIngest()` did not | **A success path and a cancel path tear down the same UI and must share one teardown.** Where they are written separately they drift, and the half that survives is the half that lies about state. Also: an action that succeeds must visibly stop offering itself — leaving the control live invites a second press, and the second press hits a state the first one destroyed. |
| A user reported a missing Import button; the button was fine, the file load had failed and said so only in 9.5px italic text | The failing step rendered nothing at all, and the step's own hint read "Appears once a file loads". A missing step is indistinguishable from a broken control, so the user correctly described what they saw and it pointed at the wrong component | **A step that can fail must render its failure in the space it would have occupied.** Silence in the place a user is looking gets attributed to the nearest visible control. Also: the error text existed and was accurate — being technically informed is not the same as being seen, and a 9.5px italic line next to an empty region is not seen. |
| The same failure also left the PREVIOUS file's mapping and Import button live | Each failure path called `setIngestStatus(...)` and returned, without clearing `LAST_PARSE` | **A failure path has to undo the state a success would have replaced.** Returning early after reporting an error leaves whatever the last success set up, and here that meant offering to import file A while displaying the name of file B. Route every failure through one function so the teardown cannot be forgotten in one branch out of six. |
| A test harness proved a feature worked and simultaneously broke it, and the breakage was read as a product defect for several rounds | The feature serialises the live DOM. The harness injects its own script into that DOM, so the harness ended up inside the artefact it was testing, ran on load, and overwrote state the product had set correctly | **When a feature captures its environment, the test harness is part of the environment it captures.** Hours went into a page-title discrepancy that was the harness talking to itself. Worth the cost only because it exposed the real defect underneath: any browser extension or viewer wrapper would have been baked in the same way. Where a feature serialises "everything present", define what legitimately belongs and drop the rest by identity, not by guessing what to exclude. |
| A `const` declared after the init block threw inside a try/catch, so half a state restore applied and half silently did not | Module-level state is declared where it reads best next to the code that uses it, and init sits at the bottom of the file, so anything init reaches for that lives below it is in the temporal dead zone. The catch turned a hard failure into a partial one | **Partial application is worse than none, so a restore path should verify it finished, not just not throw.** The symptom was a correct-looking board with two fields quietly wrong. Second instance of this class after `LAST_MARKUP_AT`: state that init touches must be declared above init, and the sweep for that should include `const`/`let` ordering, not only undeclared globals. |
| A global was assigned but never declared, so exporting on a clean load threw and silently produced no file. It survived from before the migration | `LAST_MARKUP_AT=new Date()` in a non-strict script creates the global on first assignment, so everything worked the moment a user made any edit. Every manual test of export had made an edit first, so the one path that fails is the one nobody walks | **Test the clean-load path explicitly.** A feature that works after any interaction hides a failure that only shows before the first one. Building a round trip caught it immediately, because a round trip has to start from nothing. The file has no `"use strict"`, so this class fails silently rather than at parse time. Swept for it at v3.1.0-P9 by diffing every assignment to an ALL_CAPS identifier against every declaration: `LAST_MARKUP_AT` was the only one, and it is now declared. Re-run that sweep when adding module-level state. |
| The same low-contrast token was walked into twice, on the pass immediately after it was documented by value | TD-28 recorded `--color-text-small` at 1.18:1 on a dark row. The next component built reached for it anyway, because it is the semantically obvious name for a small label and the number lived in a to-do file rather than next to the token | **A measured defect belongs next to the thing measured, not only in a tracker.** A comment on the token definition would have been read at the moment of choosing it; a to-do row was not. The probe caught it either way, which is the argument for probing every new component rather than only new colours. |
| A new row-number element shipped into review at 1.99:1 contrast in dark mode, past a contrast check that reported zero findings | The check skipped any element whose own `background-color` was transparent, on the reasoning that such an element "does not own its backdrop". A row number sits directly on the row and owns nothing, so it fell straight through the skip and was never measured | **A verification tool's skip conditions are assumptions, and they need testing like any other code.** Every `continue` in a checker is a claim about what cannot go wrong there. When adding a component whose shape differs from what the tool has seen before, check whether the tool actually measured it, rather than reading a clean report as coverage. The fix was to resolve a transparent element to its nearest painting ancestor, which reproduced the defect immediately. |
| Closing that blind spot produced two further findings that were not defects | Two probes wrapped an SVG-fill class around a literal "x". No element in the app ever applies those classes to text, so the measured case could not occur | Third instance of this exact pattern here (after `th.c-name` and AC-10). **Before acting on a finding from a synthetic probe, query the rendered app for the case the probe fabricates.** If it does not occur, the probe is wrong, not the code. Fixing it would have changed working code to satisfy a test of something that does not exist. |
| A toggle that rebuilt the board **appended** a second copy of it instead of replacing it, for as long as the toggle has existed | `renderRows()` appends rows; the only thing that empties the tbody is `teardown()`, which runs inside `rerender()`. One handler called `renderRows()` on its own. Every use of that toggle added another 159 rows under the existing ones | **A render function that does not clear is only safe where something else just cleared.** The repo rule already said to call `scheduleRerender(true)` for a user action needing a rebuild; the one place that ignored it is the one place that broke. When a function's safety depends on its caller, say so at the function, and grep its call sites when the invariant is discovered rather than fixing only the reported one. The symptom was also perfectly misleading: turning the toggle OFF looked like a no-op because the elements that stayed on screen belonged to the copy the same click had just created. |
| A feature was reported as not working when every element it draws was present, correctly valued, visible and measurable | The elements were 4.5 x 8px, unbacked, placed fully outside their icon on the boundary between two rows, and half-covered by another layer that starts at the same edge. `getBoundingClientRect()` reports all of that as fine | **Existence is not legibility, and a probe that asserts existence will pass on an invisible feature.** Assert position relative to the thing the element annotates, size against a floor a reader can actually resolve, and overlap against the layers that share its anchor. A screenshot is what exposed this, which is the narrow case where looking is worth more than measuring: not to verify, but to find out what to measure. |
| An overlay meant to sit level with the marker it shadows was 3px below it and, in crowded cells, exactly underneath it | Two separate copies of a placement decision. The overlay took the **live** marker's x, which encodes the crowding of a different cell, and a CSS rule nudged it in both axes when only one axis was wanted. The "so it is not hidden" nudge was then measured from the cell centre, but a cell with several markers spreads them off centre, so the nudge moved the overlay onto one of them | **An offset that exists to separate two elements has to be measured from the element it is separating from, not from the container.** The container's centre is only the other element's position in the single-occupant case, which is exactly the case where the offset does not matter. |
| A probe reported three false failures on correct code, and the fix was to change the product | Two markers in one row can share a baseline column, so the probe's attempt to infer which live marker an overlay belonged to picked the wrong one. The overlay now names its pair in a `data-` attribute | **When a probe cannot reconstruct a relationship the code knows, publish the relationship rather than loosening the assertion.** Loosening it would have hidden the real cases too. The attribute is also inspectable in devtools, so the product got better rather than just the test. |
| Two assertions passed against an empty set, the third occurrence of this in one project | The toggle under test goes through a debounced rerender. The probe read the DOM synchronously, found nothing, and every "every element satisfies X" assertion was vacuously true | **`every()` over an empty set is the default failure mode of a DOM probe, not an edge case.** Every probe that measures a set now asserts its sample size as its own named check. Timers do fire under `--virtual-time-budget`, but only if the probe yields to them, which is a second entry in the growing list of virtual-time artefacts alongside transitions never completing. |
| A window that framed the data was inherited as a constant and never questioned, and was wrong in both directions at once on the same file | The board spanned a fixed 12 weeks before the data date to 26 after it. That happened to fit the seeded baseline it was written for, so it read as correct for as long as nobody imported a schedule shaped differently. On the real export it dropped three milestones past its end and padded eight empty weeks onto its front | **A framing constant is a claim about the data, and it should be derived from the data or justified against it.** The three lost milestones were not silent — they raised a diagnostic — but a warning that the board cannot show part of the schedule was being treated as information rather than as a defect. When a check reports the same thing on every run, decide whether it is a report or a symptom. |
| A button did nothing, reported nothing, and had done nothing for as long as it had existed alongside filtering | Two fitters measured `document.querySelector('tr.data')` to learn a column width. A hidden row has no layout, so every cell in it returns `offsetParent === null`; with any filter that hid the first row, the visible-cell list came back empty and both functions returned early | **"The first one" is only safe where nothing can hide one.** Any query that takes the first match of something the UI can hide needs to take the first VISIBLE match instead. Also: an early return on an empty measurement is the quietest possible failure — the function did exactly what it was told and the user sees a dead control. Found by a test of a different feature, because the new feature made the hidden-row case ordinary rather than rare. |
| The handoff's companion files were missing at migration and blocked FEAT-14 for a full cycle | Section 5 row 1 repeating itself: the files existed but were never delivered alongside the document that depended on them | Already captured. Worth noting that the predicted failure happened exactly as written, which is the argument for treating that row as a rule rather than an anecdote. |

## A probe that outlives the thing it probed passes against nothing

`tools/theme_check.py` carried four probes that built `.mnt-slot`, `.mnt-name`, `.mnt-lines` and `.mnt-badge` elements by hand. When v3.1.0-P29 replaced those classes, the probes kept passing: the constructed `<div>` still inherited the body's colours, and body colours toggle. Nothing failed, the count stayed green, and the mount panel had no contrast coverage at all.

This is the fourth vacuous pass in this project (TD-66, the P26 float column, TD-87, and now this), and the first where the probe was measuring a live element that simply no longer had the class it was named for. The sample-size rule from TD-87 does not catch it, because the sample size is one.

Two things came out of it:

- **A probe that constructs its own subject must fail if the subject's class no longer exists.** The drawer probes now mount inside `#settings-drawer` through a helper that throws when the panel is missing, so the element is measured in the frame it really appears in, against the panel's own background and custom properties.
- **Retire the probe in the same commit as the class.** A probe is part of the component, not part of the test suite's furniture.

## The same run proved that reading the CSS could not have found either defect

`--color-text-note` measured 2.98:1 on the drawer background and always had. The gate reported zero failures because no probe had ever put that ink on that background: the pairing existed in the product and not in the test. It only surfaced because the rebuild turned helper text from an occasional footnote into a primary component, which added the probe.

`.ingest-status.ok` was frozen at a hardcoded `#1a6b3a`. The obvious replacement, `--color-health-good`, is a **fill** and is constant across themes by design, so using it as ink froze it again in a way that reads perfectly correct in the CSS. That is the TD-28 shape a third time, and it generalises:

> A token's role is part of its name. A fill token pressed into service as ink will be frozen, or will be dark-on-dark, and neither is visible in the declaration.

`--color-purple-deep` is the same trap with a twist: it is genuinely used as ink, as a fill, and as ink on a light tint, in three different places. There is no single value that satisfies all three in dark theme, so it cannot be fixed by retuning. The role had to be split (`--color-accent-ink`), which is the tokenisation rule this project already had written down and had not applied here.

## A duplicate declaration can be load-bearing

TD-88 recorded a duplicated `--color-bg-subtle` in the dark theme block and said it needed a consumer sweep before removal. The sweep, done here, shows the duplicate is what keeps the week header a light strip in dark theme, because `tr.hdr-wk th` paints `--color-text-small` on it and that token is `#334` in dark. Deleting the duplicate would have made the week header near-black on near-black.

So the fix for the drawer was not to remove the duplicate but to stop depending on it: the panel takes `--color-bg-panel`, which already toggles. **When a duplicate has survived, find out what is standing on it before removing it.** The tidier change was the one that would have broken the board.

## An id-based smoke test cannot see a reparented element

A stray `</div>` in the new setup step closed `#settings-drawer` one level early. The browser reparented the Defaults panel, the Diagnostics panel and the whole action footer onto `<body>`. Every `getElementById` still resolved, every handler still fired, and the ad-hoc smoke probe reported a clean load with the right row and milestone counts.

`tools/p29_check.py` caught it immediately, because it asks a different question: it queries **through** `#settings-drawer` rather than by id. `DR.querySelector('.sd-actions')` came back null and the probe threw.

> A check that looks elements up by id is testing that the ids exist. A check that looks them up through their container is testing that the structure is what you think it is. Unbalanced markup only fails the second kind.

This is why the structural assertions in `p29_check.py` are scoped to the panel rather than to the document, and why the theme probes mount inside the real drawer instead of on `document.body`.

## The band-order assertion that could not tell the two outcomes apart

`p30_check.py` appends the reference workbook to **itself**, so the two schedules carry identical band names. The first version of the assertion collected distinct band names and expected the count to double. It reported 14 against an expected 28 and looked like a real failure.

It was the assertion that was wrong. A distinct-name count returns 14 whether the two schedules sit one after the other or are interleaved row by row: the measurement cannot distinguish the outcome being tested from its opposite. Counting **contiguous runs** of one band down the board can, and it holds: 28 runs, the second 14 matching the first.

> Before trusting a failing assertion, check that it could have distinguished pass from fail in the first place. A measurement that returns the same value for both is not evidence either way.

Same family as the vacuous passes (TD-66, TD-87), but the opposite symptom: a vacuous **failure**. Both come from not asking what else could produce this number.

---

## A correction the measurement refused (v3.1.0-P32)

Three defects were written up from reading the source, with confidence, before a probe was run. **Two of the three were wrong.** The headline one, that a coordinate-frame mismatch was pushing markers out of their rows, measured `markersOut: 0` at every setting including the user's own. The belief gap was a constant 1px, and it pointed the safe way.

The plan said measurement was step one and it was, which is the only reason the rework was built on the two real defects instead of the invented one. Had it been skipped, the fix would have been elaborate, plausible, and aimed at nothing.

**A diagnosis read off the source is a hypothesis.** It earns the word "cause" after a measurement, not before. This is the same rule as "a code read-through is not a test", applied one step earlier: to the explanation, not just to the fix.

## The two-state toggle, found in the second place it lived

`CLAUDE.md` has carried this since P25: *"Test N=3, not just the reported N=2. The label collision system re-collided on the third marker in a cluster because it was built as a two-state toggle."*

The **label** system was rebuilt as three bands then. The **icon** spread in the same function kept `y = 50 ± 22` on `i%2` and was never revisited, so it produced exactly two distinct positions for every N from 2 to 6 for four more partials. N=3 came out `[28, 72, 28]`.

Writing a lesson down fixes the instance. It does not find the other places the same shape already exists. When a defect class is named, the next move is a search for that shape across the file, not only a fix where it was reported.

## A control that hides something must outlive what it hides

The only control that could reopen the filter row lived inside the filter row. Hiding it collapsed the container to `max-height: 0; overflow: hidden`, and the way back went with it.

This is TD-92's shape again, and TD-105's: an element still in the DOM, still answering `querySelector`, with no layout whatsoever. Three separate defects in this project now trace to treating "present in the DOM" as "available to the user". The test that distinguishes them is `offsetParent !== null` or a non-zero rect, and it is the one the P32 check makes.

## A rule applied in two of the three places that need it

`rebuildBandingFilter()` and `rebuildSourceFilter()` both save their selection before rebuilding options and restore it after. `rebuildWeekFilter()` did neither, so `teardown()` dropped the selection and every `scheduleRerender(true)` silently cleared the week filter.

It surfaced as "changing a health icon unfilters the dashboard", which is a true report of a symptom whose cause lives nowhere near health. **A user-reported trigger is one caller, not the defect.** The fix belonged at the rebuild, not at the health handler, and the check asserts both the reported path and the general one.

## Assert the observable value, not the authored one

A check read `getComputedStyle(el).marginLeft` expecting `"auto"` and got `"911.188px"`. `getComputedStyle` reports used values; `auto` is an input, never an output. Right-alignment is a position, so it has to be measured as one.

Sibling of the padding-box/border-box finding at P25: both are cases of asserting in a frame the browser does not report in.

---

## A probe that drove the model instead of the control (v3.1.0-P33)

Three separate probes set placement by calling `setIcoSize(24)` and `setWkWidth(20)` directly. `rerender()` reapplies display settings by reading the slider **elements** back:

```js
setWkWidth(document.getElementById('wk-width').value);
setIcoSize(document.getElementById('ico-size').value);
```

So every call was undone by the rebuild it triggered, and each sweep measured the default over and over while printing seven different setting labels. Two shipped checks had been reporting that way for a full partial.

It surfaced sideways: a P33 assertion said 17 markers had left their row, the arithmetic said they could not, and a diagnostic printed `iconSize: 15` after being asked for 10. The failure was in the probe, and so was the earlier P32 baseline the comparison depended on.

**Drive the control, not the model.** A probe that sets a variable the app treats as derived is testing a state the app will not hold. And when a check and the arithmetic disagree, suspect the check: it is the thing with no tests.

Note the asymmetry that made this easy to miss. `applyRowHeight()` pushes `ROW_HEIGHT` onto its slider, so row height is variable-is-truth; `wk-width` and `ico-size` are slider-is-truth. Two conventions in one cascade.

## Reviving a defect by moving its neighbour

Anchoring the label stack at `left:50%` so it unfurls from behind its icon was a visual change with no obvious relation to dependency counts. But `body.counts-on` cleared the right-hand count chip with a margin measured from `left:100%`, so moving the anchor half an icon left put the stack back under the chip: TD-83, returning by a route nobody would think to check.

`p27_check` caught it. A check written for one partial earned its keep three partials later, against a change that had nothing to do with it.

**A positioned element's offsets are a contract with everything else positioned against it.** Before moving an anchor, grep for what else is measured from it.

## A generator that knew the count but not the context

The first same-cell implementation asked `msRunLevels(n)` for a sequence and got the triangle wave, which is right for markers in different cells and wrong inside one: five markers in a single cell came out `[0,1,2,1,0]`, putting two pairs on the same line in the one place where band reuse is illegitimate, because those markers share an x.

The row had already been grown to carry five bands. The generator simply had no way to use them, because its only input was how many markers there were, not where they sat.

**When a rule has an exception that depends on context, the function applying it needs that context as an argument.** Passing `n` where the rule needs the columns is how the exception ends up unrepresentable.

## A hardcoded constant standing in for a measured height (v3.1.0-P34)

The week header row stuck at `top: calc(var(--hdr-search-h) + 19.5px)`. The `19.5px` was a stand-in for the month row's height. That row renders 16px, so a 3.5px band sat between the two sticky rows and data rows scrolled through the seam. It had been there at every viewport width, which is why it took a phone screenshot to notice: on a desktop the eye reads it as a border.

The filter bar's `max-height: 160px` was the same shape. The bar wraps, so the cap is only correct at widths where the content happens to fit under it.

Both are now measured from one `ResizeObserver` each. The alternative was hooking `rerender()`, `applyRowHeight()`, `togglePrintMode()`, `fitToScreen()` and a resize listener: five entry points, which is the trap recorded three times above. **An observer has no call sites to forget.**

The generalisation, and the fourth time this family has appeared here: **a literal in CSS that names a rendered dimension is a hypothesis about that dimension.** It is right the day it is written and nothing revisits it. If CSS needs a dimension it cannot compute, measure it into a custom property and let one writer own it.

Two details that only measurement would have given:

- The month row's height had to be read from the **row**, not one of its cells. Its metadata cells carry `padding:0` and its month cells 3px, so a single `<th>` is shorter than the row.
- The filter bar's cap has to **over-estimate**. `scrollHeight` is read from whichever state the bar is in, and while closed its vertical padding has transitioned away, so an exact figure taken then is short by that padding and clips on the way back open.

## A diagnosis from the source, refuted for the third time in three partials (v3.1.0-P34)

Three cases came in with red markup. The plan named a cause for each, read off the source with confidence. Measuring the build first:

- **One diagnosis was simply wrong.** SNIP-218 and SNIP-219 were said to be two markers sharing a cell and getting an asymmetric pair of bands. They are in different rows, each the only marker in its row, and both already dead centre, at two viewport widths. The rule blamed for the screenshot had nothing to do with it. The rule was still inconsistent and was fixed, but as an inconsistency with no visible effect, and the check says so rather than claiming the screenshot.
- **The rule the user chose did not reach the case they chose it for.** They specified that a run should break on more than two blank columns. The marker they wanted moved sits in a run of four directly adjacent columns, so no proximity threshold touches it. Shipping the rule and reporting that it changed nothing there was the honest move; quietly substituting a different rule was not.
- **The obvious alternative fix failed on arithmetic, before any build.** Capping a run at three members would split that run into three plus one, and a run of one is the middle band by definition, so the marker would have landed back where it started. Checking that on paper cost a minute; discovering it in a render would have cost a cycle.

This is now a standing habit rather than a lesson: **measure the current build against the reported case before writing the fix, and say what the measurement contradicted.** It has changed the plan in each of the last three partials.


## A rect that measures nothing inside a closed `<details>` (v3.1.0-P35)

The new collapsible weight/hours row was asserted collapsed by reading `getBoundingClientRect().height` on the three fields inside it and requiring zero. All three came back non-zero at all three viewport widths, and the check failed.

The code was right and the probe was wrong. Checked against a three-line page in the same headless build, a child of a **closed** `<details>` still reports a non-zero rect, for a plain `<div>` and for the `display:grid` this uses. `checkVisibility()` answers correctly (`false` shut, `true` open), and the `<details>` element's own height is a second, independent read: 16px shut, 66px open.

Two things worth keeping from it:

- **This is the sixth virtual-time/headless measurement artefact in this project**, after transitions never completing, `performance.now()` never advancing, timers needing the probe to yield, a probe driving the model instead of the control, and a probe outliving the element it measured. The pattern is always the same: a browser API that is correct in a real browser and misleading under `--dump-dom`. Treat any *new* measurement technique as unproven until it has been shown to distinguish the two states it is meant to distinguish.
- **It failed loudly, which is the good outcome.** The same mistake in the other direction, requiring non-zero and getting it, would have been a vacuous pass. The reason it failed loudly is that the assertion was written against the state that is harder to produce accidentally.

Two other probe defects in the same run, both of the standing families:

- The tooltip assertion read `data-tip` off the wrap handle captured **before** the edit. A commit rerenders the board, so that handle is a detached node still carrying its pre-edit tooltip: the probe was measuring the old board. Same family as the probe that outlived the thing it probed; the fix is to re-query after anything that rebuilds.
- The clamp assertion read the **store** after typing `-5`. The target's schedule value is 0 and `-5` clamps to 0, so the store correctly held nothing, and the assertion was measuring the deduplication rule rather than the clamp it was aimed at. **Assert the value the user sees**, not the intermediate the implementation happens to keep.

## A card assertion that compared three fields while two were rendering (v3.1.0-P35)

The Start / Finish / Progress row was asserted on the first suitable milestone the board offered. That milestone carries no separate start date, so its Start field is `display:none` and the "all three sit on one row" and "all three are the same text size" checks were comparing two boxes, passing, and saying three.

**Second time a milestone-card assertion has compared against a field that was not being rendered** (TEST-29, where the card was opened on a baseline seed and the parent heading and float column were both `display:none`, so two position assertions ran against zero rects). The card hides fields that do not apply, so *any* assertion about its layout has to state which fields were actually showing, and a claim about a field only appears when a milestone that renders it has been opened on purpose.

## The API that answered one hiding mechanism and not the next (v3.1.0-P36)

TEST-37 established that `getBoundingClientRect()` lies about content inside a closed `<details>` and that `checkVisibility()` tells the truth there. One partial later, the filter-row toggle moved into a menu and the TD-72 guard had to be rewritten to follow the path to a control rather than test for a visible button. A negative control was added to the rewrite, putting the toggle back inside the collapsed filter bar and requiring the assertion to go false.

**The first rewrite passed the negative control.** Measured against a control trapped inside a `max-height:0; overflow:hidden` bar:

| | trapped in the collapsed bar |
|---|---|
| `offsetParent !== null` | true |
| height | 24px |
| `getClientRects().length` | 1 |
| `checkVisibility()` | **true** |
| `elementFromPoint` at its centre | did not discriminate |
| box intersected with clipping ancestors | **0px** |

A clip does not zero its children's boxes. Every obvious API reports the trapped control as present and laid out, which is exactly what it reports for a control sitting in an open menu.

Three things worth keeping:

- **`checkVisibility()` is container-specific.** It is correct for `display:none` and for a closed `<details>`, and wrong for an `overflow:hidden` clip. "Is this hidden" has no single API answer; the answer depends on the mechanism doing the hiding. Before using a visibility API in a new context, show it distinguishing the two states in *that* context.
- **The general measurement is geometric.** Intersect the element's box with the box of every clipping ancestor and with the viewport. That is what the user's eye does, and it is mechanism-independent.
- **A rewritten guard needs a negative control, always.** The rewrite was reasoned about carefully and was still wrong. What caught it was six lines that reintroduced the original defect and demanded a failure. **Any assertion rewritten to accommodate a change has stopped being the assertion that was passing before, and is unproven until it has been shown to fail on the thing it guards.** This is the seventh measurement artefact in this project and the first found by deliberately breaking the code rather than by a surprising result.

## An assumption about a layout change, refuted at one viewport out of three (v3.1.0-P36)

The More Actions consolidation was expected to unclip the version label, and the check was written asserting exactly that. It holds at 768 and 1440 and fails at 390, where the bar also carries the editable report title and 216px of label plus that title plus the trigger does not fit.

The fix was not to widen the change until the assertion passed. It was to assert what actually holds: the full width where the bar has room, and where it does not, the residual clip stated with its figures and the gain required to be real (35.2px to 167px). The condition is read from the **measurement** — does the label reach the width it needs — rather than from a viewport width typed into the check, because a hardcoded breakpoint is a constant standing in for a measured value, which is the defect family with the most occurrences in this file.

The general form: **when a change delivers at some sizes and not others, the check says where, in numbers.** An assertion quietly scoped to the widths where it passes is the same defect as the hardcoded constant, one level up.

## A measurement that was right once and wrong for the next positioning mode (v3.1.0-P37)

P36 established that a control trapped in a `max-height:0; overflow:hidden` bar reports `offsetParent` non-null, height 24px, one client rect and `checkVisibility()` true, and that intersecting the element's box with every clipping ancestor is what discriminates it. That measurement was written, proven with a negative control, and correct.

One partial later it reported a working fix as broken. Two popups were moved to `position:fixed` to escape exactly that kind of clip, and the ancestor walk said the fixed panel was 0px visible **exactly as it had said of the absolute one** — because a fixed element is not clipped by ancestor overflow at all, so walking the DOM chain intersecting overflow boxes answers a question that no longer applies.

`elementFromPoint` at a single centre point was no better: it returned false for a panel that was genuinely on top, because one point can land on a child, a gap, or a shadow.

What answers it is a hit-test **profile**: ask the document what paints at several points down the popup, and count how many of its children are individually reachable. That is mechanism-independent, and it is the same question the user is asking ("can I click this?").

Two things worth keeping:

- **A measurement is only valid for the mechanism it was derived against.** The clipping walk is correct for statically positioned content in a scroll container and meaningless for fixed content. `checkVisibility()` is correct for `display:none` and for a closed `<details>` and wrong for an `overflow:hidden` clip. There is no general "is this hidden" primitive, and each new positioning mode needs the technique re-proved, not reused.
- **Third consecutive partial where the technique, not the code, was the thing that was wrong** (TD-133, TD-136, TD-140). The pattern is now strong enough to state as a rule: **when a check fails on a change you have reason to believe is correct, suspect the measurement first and prove it can still tell the two states apart.** In all three cases that took under ten minutes and in all three the code was fine.

## Escaping a clip is half the job; the other half is the stacking context (v3.1.0-P37)

Making the More Actions panel `position:fixed` removed the clip and the panel still could not be clicked: `#rpt-hd` and `#top-filter-bar` painted over it, and 0 of 7 rows were hit-testable at 390 wide.

`#icon-bar` is `position:relative` with a `z-index`, which makes it a **stacking context**. Every descendant is stacked *within* it, so the panel's `z-index: 2147483000` competes with nothing outside the bar: what decides the outcome is the bar's own `z-index: 30` against later siblings at the same level, which also sat at 30 and won on document order.

The generalisation, and it is easy to get wrong because the symptom looks like a z-index that is not big enough: **a huge z-index on a descendant is inert if an ancestor established a stacking context.** The number that matters is the ancestor's. Raising the popup is the instinct and it cannot work; raising the context is the fix.

Two things to check together whenever a popup is not visible, because fixing either alone leaves it broken:

1. Is anything clipping it (an ancestor's `overflow`, and for a fixed element, an ancestor with `transform`/`filter`/`contain` that makes it a containing block)?
2. Is anything painting over it (which ancestor establishes its stacking context, and what does *that* compete with)?

## A control whose label promised one thing and whose code did another (v3.1.0-P37)

The zero-dependency filter's tooltip read *"Show only milestones with zero predecessors/dependencies"*. It gated dependency-**line** drawing, and lines only exist once dependencies are switched on, so from the default state it did nothing at all: 105 rows before, 105 rows after, 0 lines drawn.

Nothing was broken in the sense of throwing or rendering wrongly. The code did exactly what it said in its own comment. The defect lived in the gap between the comment and the tooltip, and only a user reading the tooltip could find it.

**A control's label is part of its contract, and it is the part nothing tests.** Worth asking of any filter or toggle: what does the label promise, in what state will a user first try it, and does it do that *there* rather than only in the state the author had set up. This one worked perfectly in the state its author was in and was inert in the state it ships in.

## A probe that could not fire the event the defect lived in (v3.1.0-P38)

The report was that setting one end of the date range did nothing. The first measurement refuted it: an end date alone narrowed the board to 20 of 39 week columns, a start date alone to 24 of 39, identical at 390 and 1440. `dateRangeToCols()` had always left the other end open.

The report was right and the measurement was answering a different question. The probe dispatched a `change` event. `change` on `<input type="date">` does not fire until the field is committed and left, so a date set with the picker or the spinner sat there doing nothing until focus moved elsewhere. The logic was never the defect; **the event was.**

Two things to carry:

- **A synthetic event is a claim about how the control is used.** Dispatching `change` asserts "the user finished and left the field". Every earlier probe in this project fired `change` on these inputs and every one of them passed, because none of them could express the case the user was in. The fix's assertion dispatches `input` **only**, and would fail if `oninput` were removed.
- **When a measurement refutes a user's report, the next question is what the measurement did differently from the user**, not whether the user was wrong. Both of the last two reports refuted at first measurement (TD-138, TD-143) turned out to be real, in a state or an interaction the probe had not reproduced.

## The fourth occurrence of the same two-paths family, surfaced by a one-word default change (v3.1.0-P38)

Changing `let mHrsVisible=true` to `false` should have been the whole change. It rendered **196 visible hours labels at first paint**, with the checkbox correctly reporting false.

`rerender()` hid all three things a fresh render creates visible (type-code label, milestone hours, remarks); init's first-paint path hid only the label. So the declared default took effect the first time anything triggered a rebuild and not before. TD-59, TD-71 and TD-138 are the same shape: a line added to one build path and not the other.

The fix was not a fourth line at the second call site. The three lines were folded into `applyMarkerLabelState()` inside `reapplyDisplaySettings()`, the function both paths already call, and deleted from both.

**A default is a claim about first paint, so it has to be measured at first paint.** Reading the variable proves nothing: the variable was correct in every one of these four cases. And when the same family reaches its third occurrence, stop fixing the instance: move the thing being forgotten somewhere it cannot be, and let the call sites shrink.

The companion rule, now recorded in the architecture: **anything that must be reapplied after a rebuild goes inside that one function, never beside a call to it.** Written both directions too (`display = on ? '' : 'none'`), so it states the state rather than depending on what a fresh render leaves behind.

## A fix that moved a control off screen, and the measurement that caught it in the same run (v3.1.0-P38)

Aligning the print preview's heading bars to the A3 sheet was correct and made three brand-new controls unreachable: the hit-test profile counted **0 of 3 on screen at 390** and 2 of 3 at 1024. Nothing had broken. A sheet is 1122.5px, the viewport was 390, the page scrolls sideways, and the right-hand end of a sheet-width strip is simply not on screen.

The controls moved to the sheet's left edge, which is on screen at every width, and read 3 of 3 everywhere.

**Widening an element to match a wider thing moves everything at its far end out of reach.** This is a general consequence of aligning chrome to a page rather than to a viewport, and it applies to any control that was safe at the right edge of a viewport-width bar.

The related habit worth keeping: the assertion about the header bar's own trigger, which now scrolls with the sheet, is **conditional on measured room** rather than on a typed viewport width. Where the trigger is on screen the panel must anchor to it; where it is not, the panel must be clamped into the viewport. Both branches still require every row individually reachable. A hardcoded width in that assertion would have been a fifth instance of the constant-standing-in-for-a-measurement family.

## A property the browser enforces that no test can see (v3.1.0-P39)

Three size sliders were disabled while the text they scale is switched off. The check set `.value` and dispatched `input`, watched the CSS custom property move, and reported working code as broken.

The experiment could not answer the question in either direction. `dispatchEvent` delivers to an `oninput` listener whether or not the input is disabled, and an untrusted pointer event never drives a range thumb, so an **enabled** slider would have failed the same test. `disabled` is real, the browser enforces it, and nothing writable from a probe can observe it.

The fix was not a cleverer event. It was a **second barrier that is observable**: `pointer-events:none` on the disabled input, measured by asking the document what is at the slider's own centre. Off, the point belongs to the row; on, it belongs to the slider. The negative control runs on the same point.

Two things to carry:

- **When a property cannot be measured, add a mechanism that can, rather than asserting the property and hoping.** `disabled` plus `pointer-events` is also better behaviour, not just a more testable one.
- **Fourth consecutive occasion where the measurement technique, not the code, was the thing that was wrong** (TD-133, TD-136, TD-140, TD-146). The rule stated at TD-140 held again: when a check fails on a change you have reason to believe is correct, suspect the measurement first and prove it can still tell the two states apart. Here the proof took one line, the enabled case, and it failed too.

## A report against a build that no longer exists (v3.1.0-P39)

"The predecessors and dependencies are not displaying on the page" measured, on the current build, as 675 lines in the DOM and 132 on screen the moment both kinds were switched on, unchanged through a date range, a rerender and a clear, and 0 again when switched off. Nothing was broken.

The screenshot attached to the report was the answer: a **pre-P36 build**, identifiable from the separate header icon buttons, a "Title contains" filter that no longer exists, and a `Title col:` reading the panel no longer produces. In it, the Dependencies row's **All off** button is the active one.

Two things worth keeping:

- **Read the screenshot for which build it is before reading it for the defect.** Three of the eight items in that batch turned on this: one asked to remove a field that had already been removed, one reported a control that works, and the third named labels the current build no longer uses. None of that is the reporter's fault; a user reports against what they have open.
- **A refuted report gets an assertion, not a shrug.** The measured behaviour is now part of the standing check, so if it ever does break, the failure names itself instead of landing in a thread that already concluded "that was already broken".

## A control that reads as an action among controls that read as state (v3.1.0-P39)

The Remarks row was one button labelled with what it would do next: it read "Hide" while the field was showing. Every other segmented control in the same panel labels the state it selects. Two idioms side by side, one of them inverted, and the only way to know which was which was to try it.

It is now a `Show` / `Hide` pair where the active half is the current state, driven by `setRemarksVisible(on)` which takes the value rather than flipping, so clicking the half that is already active is a no-op instead of turning the field off.

**Within one panel, pick one idiom and keep it.** A relabelling button is defensible on its own; beside four segmented state controls it is a trap. The check asserts the no-op case explicitly, because a flip-on-click implementation passes every other assertion in the set.

## The reported example that contradicts itself once you look at the whole board (v3.1.0-P40)

A request named four rows: "18 is OK, 37 would be increased, 46 would be increased, 51 is OK." The rule built from that reading, grow a row whose densest proximity run reaches the band count, matched three of them and not row 51.

The measurement explained it rather than the rule being bent to fit. Row 51 carries four milestones at columns 13, 14, 15 and 17: one run of four, identically dense to rows 37 and 46. It read as fine in the screenshot because that board had a date range opening at column 15, so two of its four markers were off the visible board.

**No rule reading the data could have separated row 51 from 37 and 46.** The distinguishing property was not in the data at all; it was in the filter the reporter had applied.

Three things to carry:

- **When one example out of a set disagrees, measure that example before adjusting the rule.** The instinct is to add a condition until all four fit. Here any such condition would have been fitted to an artefact of someone's date range.
- **A screenshot shows a filtered board, and the filter is part of what it shows.** The same trap as the previous batch, where a report arrived against a build three versions old. Read what state the picture is in before reading what it says.
- **Assert the disagreement, do not hide it.** The check asserts row 51 grown, asserts that two of its four markers fall before the reported window, and names the alternative rule (grow on VISIBLE markers) that would match the report at the cost of row heights moving on every filter pass. The gap between the rule and the report is on the record and the choice is the user's.

## A change that is correct and still costs something, measured in the same run (v3.1.0-P40)

Growing the dense rows introduced exactly one degenerate dependency line: a quarter of a pixel long, at a legitimate board position, drawn as its own arrowhead. It was isolated by rendering the same board with the growth factor at 1.0, which gives zero.

The check it failed exists for a real catastrophe: markerCenter() measuring hidden elements, which have a zero rect, so 308 of 331 lines once resolved to the same point at the board's top-left corner. One tiny line elsewhere is not that.

The temptation was to delete the check or to loosen it until it passed. Neither is right: the first throws away the guard for the catastrophic case, the second leaves an assertion that no longer means anything. What the check now asserts is the failure it was written for, lines **at the board origin**, at zero, and it bounds the degenerate count separately with the current figure recorded.

**When a correct change breaks an assertion, the question is what that assertion was protecting.** Re-aim it at that, keep its teeth for the case it was written for, and record the residue as its own item rather than absorbing it into a relaxed threshold.

## A check that can only see the headers cannot see the defect (v3.1.0-P40)

The exported CSV mixed the schedule's own Progress % and Status with a person's overrides, both under the same headers. Splitting them into a schedule block and an entered block is easy; proving it is not, because `exportCSV()` triggered a download and a probe cannot read a download.

A header-only assertion would have passed on the exact file the change exists to fix: two blocks with the right names, both carrying the same effective value.

`exportCSV()` was split into `buildCsvRows()` plus a thin writer, so the check sets an override and then requires the two blocks to **disagree**: base reads 100%, entered reads 55%.

**If the observable thing is the content, make the content observable.** Splitting the builder from the writer took two minutes and turned a check that could only confirm the shape into one that confirms the substance. The same move paid off earlier in this file when `positionFixedPopup` was extracted, and for the same reason: a function that does one thing can be asked what it did.

## The comment three lines above the bug was already describing it (v3.1.0-P41)

Row growth became dependent on which columns are visible, so `applyFilter()` gained a check for whether the rendered heights still matched. Both of its exits got it, including the early return, which felt like the careful version.

`clearFilter()` did not. It un-hides every row and column **itself** rather than routing through `applyFilter()`, so Remove all filters put the columns back and left rows that should have grown sitting at the short height.

The code directly above the line that was missing reads:

> *clearFilter() un-hides every row and column itself rather than routing through applyFilter(), so it is a SECOND entry point into "what is on the board just changed" and needs the same redraw.*

That comment was written for TD-106, when the dependency lines hit the identical gap. Reading it did not stop the same mistake being made in the same function one change later.

Three things:

- **Fourth instance of this family** (TD-59, TD-71, TD-106, TD-159), and the first where the warning was already written at the site. A comment records a trap; it does not check for it. What actually caught this was `p33_check`, a probe written two partials earlier for a different purpose.
- **Count the entry points at source.** The check now asserts that exactly three call sites carry the staleness check, so a fourth added without it fails immediately rather than three partials later. A prose warning cannot do that.
- **A failure message that says "4 of 105 rows changed height" says a regression happened and nothing about where to look.** Naming the rows turned a twenty-minute hunt into a one-line read: the clone row plus three that went 34.3 to 51, which is the growth ratio, which is the answer. Assertions over sets should name the members that broke them.

## The defect was one state too early, not in the colours (v3.1.0-P42)

The report was that a milestone someone marks off and a milestone the upload records as complete both render black, and the obvious reading is a colour defect. It was not. `--color-icon-done` already resolved to ink and the card's dot was already green. `effectiveState()` mapped a person's override of 2 onto the schedule's own `DONE`, so the two were the same state before any CSS ran, and no amount of work on the tokens could have separated them.

**Two things that look alike on screen cannot be made different by styling if they are the same value upstream.** Find where they stop being distinguishable before touching what paints them. Half an hour reading `effectiveState()` beat any number of passes over the colour tokens.

## A probe that cannot fail is not a probe (v3.1.0-P42)

Two probes were added to `theme_check.py` for the new class, and then tested by pointing one at a class that does not exist. It inherited the ink colour, which toggles with the theme, was reported under TOGGLING correctly, and the script exited 0. The tool's `constant` expectation is informational by design: only the `toggle` direction can fail.

So the two new probes asserted nothing, and would have sat in the file looking like coverage. **Every guard needs its negative control run once, including a guard added to a tool that already passes.** The assertion went where the colours are read for what they are instead. TD-161 carries the fix to the tool, deliberately not made inside an unrelated partial, because changing the semantics would put eighteen existing constant probes in play at once.

## The sample has to be on the board (v3.1.0-P42)

The first draft of `p42_check` picked `SNIP-101` and reported three failures about working code. SNIP-101 is dated 01-May, outside the visible week window, so no marker is drawn for it and there was nothing to read a colour off. A second weak spot in the same file: a chip assertion compared `onlyDone: 0` against a base count and passed trivially, because 0 differs from 159.

**Filter a sample to what is actually rendered, and make sure a count you are comparing cannot be zero.** Both failures pointed at the app; both were in the check.

