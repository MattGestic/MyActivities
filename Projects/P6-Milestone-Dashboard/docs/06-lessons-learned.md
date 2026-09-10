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
| A user reported a missing Import button; the button was fine, the file load had failed and said so only in 9.5px italic text | The failing step rendered nothing at all, and the step's own hint read "Appears once a file loads". A missing step is indistinguishable from a broken control, so the user correctly described what they saw and it pointed at the wrong component | **A step that can fail must render its failure in the space it would have occupied.** Silence in the place a user is looking gets attributed to the nearest visible control. Also: the error text existed and was accurate — being technically informed is not the same as being seen, and a 9.5px italic line next to an empty region is not seen. |
| The same failure also left the PREVIOUS file's mapping and Import button live | Each failure path called `setIngestStatus(...)` and returned, without clearing `LAST_PARSE` | **A failure path has to undo the state a success would have replaced.** Returning early after reporting an error leaves whatever the last success set up, and here that meant offering to import file A while displaying the name of file B. Route every failure through one function so the teardown cannot be forgotten in one branch out of six. |
| A global was assigned but never declared, so exporting on a clean load threw and silently produced no file. It survived from before the migration | `LAST_MARKUP_AT=new Date()` in a non-strict script creates the global on first assignment, so everything worked the moment a user made any edit. Every manual test of export had made an edit first, so the one path that fails is the one nobody walks | **Test the clean-load path explicitly.** A feature that works after any interaction hides a failure that only shows before the first one. Building a round trip caught it immediately, because a round trip has to start from nothing. The file has no `"use strict"`, so this class fails silently rather than at parse time. Swept for it at v3.1.0-P9 by diffing every assignment to an ALL_CAPS identifier against every declaration: `LAST_MARKUP_AT` was the only one, and it is now declared. Re-run that sweep when adding module-level state. |
| The same low-contrast token was walked into twice, on the pass immediately after it was documented by value | TD-28 recorded `--color-text-small` at 1.18:1 on a dark row. The next component built reached for it anyway, because it is the semantically obvious name for a small label and the number lived in a to-do file rather than next to the token | **A measured defect belongs next to the thing measured, not only in a tracker.** A comment on the token definition would have been read at the moment of choosing it; a to-do row was not. The probe caught it either way, which is the argument for probing every new component rather than only new colours. |
| A new row-number element shipped into review at 1.99:1 contrast in dark mode, past a contrast check that reported zero findings | The check skipped any element whose own `background-color` was transparent, on the reasoning that such an element "does not own its backdrop". A row number sits directly on the row and owns nothing, so it fell straight through the skip and was never measured | **A verification tool's skip conditions are assumptions, and they need testing like any other code.** Every `continue` in a checker is a claim about what cannot go wrong there. When adding a component whose shape differs from what the tool has seen before, check whether the tool actually measured it, rather than reading a clean report as coverage. The fix was to resolve a transparent element to its nearest painting ancestor, which reproduced the defect immediately. |
| Closing that blind spot produced two further findings that were not defects | Two probes wrapped an SVG-fill class around a literal "x". No element in the app ever applies those classes to text, so the measured case could not occur | Third instance of this exact pattern here (after `th.c-name` and AC-10). **Before acting on a finding from a synthetic probe, query the rendered app for the case the probe fabricates.** If it does not occur, the probe is wrong, not the code. Fixing it would have changed working code to satisfy a test of something that does not exist. |
| The handoff's companion files were missing at migration and blocked FEAT-14 for a full cycle | Section 5 row 1 repeating itself: the files existed but were never delivered alongside the document that depended on them | Already captured. Worth noting that the predicted failure happened exactly as written, which is the argument for treating that row as a rule rather than an anecdote. |
