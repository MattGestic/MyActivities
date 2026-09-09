# P6 Milestone Dashboard — session rules

Read this before touching any file in this project. It is the short form; `docs/00-project-context.md` and `docs/04-architecture.md` carry the reasoning.

## Where things are

| Path | What |
|---|---|
| `src/milestone-dashboard.html` | **The application.** One file. Always the current working version. |
| `releases/` | Point-in-time snapshots named by version. Never edited. |
| `data/schedules/` | Reference P6 exports for ingest testing. |
| `docs/00-project-context.md` | Baseline, decisions, constraints, what not to change |
| `docs/01-requirements.md` | Personas, `US-##` stories, `UX-##` component requirements |
| `docs/02-backlog.md` | `EPIC-##` / `FEAT-##` / `TASK-##` |
| `docs/03-todo.md` | `TD-##` tactical items. Has the current next code task at the bottom. |
| `docs/04-architecture.md` | Runtime structure, data mapping, state model, decisions log |
| `docs/05-test-log.md` | `TEST-##` / `UT-##`, acceptance criteria, publish record |
| `docs/06-lessons-learned.md` | Patterns that caused real bugs here. Prevention, not record-keeping. |
| `docs/tokenization/` | Migration Log (component status + append-only Measurement Log), Path Plan, generated audit CSV |
| `tools/colour_audit.py` | Regenerates the audit CSV and every Measurement Log metric |
| `docs/handoff/` | Archive of the original claude.ai chat-to-code handoff |

Read `docs/03-todo.md` first in any session. One fact lives in one file — reference by ID, do not restate.

## Hard constraints

- Single self-contained HTML file. **No npm, no build step, no bundler, no framework.**
- Only external dependency is an on-demand CDN load of SheetJS for `.xlsx` import. Nothing else.
- **Never writes back to P6.** Read and render only.
- **No em dashes, no AI-associated punctuation patterns** in any user-facing or client-facing string the tool produces. This applies to the app's output, not to these docs.
- Display state never mutates schedule data. Three layers stay separate: schedule data / annotation layer / display state.

Any proposal that breaks one of these conflicts with `docs/04-architecture.md`. Flag it before building, do not implement around it.

## Do not change

- `APP_VERSION` is the only place the version string is written. The title, icon-bar label, and export payload all read from it. Never hand-edit any of the three.
- `.m-lbl-stack` must stay a genuine DOM child of `.m-wrap`, not a sibling in the table cell.
- `drawDepLines()` is the single choke point for dependency rendering. Its defensive reset of SVG layer visibility and stuck drag state on every run is load-bearing.
- The Activity ID autocomplete uses `onmousedown` + `event.preventDefault()`. Load-bearing. Removing it reintroduces a focus-stealing bug.
- Call `scheduleRerender(true)`, not `rerender(true)`, after a user action needing a rebuild.
- Sticky corner search and Top Filter Bar Title field are two-way synced.
- The three panel systems (Customize sidebar / Top filter bar / Settings drawer) are distinct. Do not conflate them.

## Versioning

`Major.Minor.Patch-PartialLetter/Number`, e.g. `3.1.0-P1`.

- Partials accumulate under a minor version.
- Bumping the **minor** and resetting partials once real work has accumulated does **not** need confirmation.
- Bumping the **major** version **does** need explicit confirmation.
- Bump `APP_VERSION` in `src/milestone-dashboard.html`, tag the commit, and drop a snapshot into `releases/` for anything shipped to a user.
- Versioned filenames are retired — the working file keeps a stable path so diffs are readable.

## Verification standard

This file has a real history of code that read correctly and behaved wrongly at runtime: CSS specificity conflicts, browser focus-stealing, a stuck-invisible SVG layer. **A code read-through is not a test.** Back any claim of "fixed" or "working" with an actual result — computed style check, DOM state check, before/after comparison. Test the interaction.

Three specific traps, each from a real wasted cycle (`docs/06-lessons-learned.md` §1):

- **Measure the element, not its parent.** Sticky headers were declared broken because the whole `<tr>` bounding box was measured; the row was never sticky, only cells inside it were.
- **Never self-verify from a screenshot.** For active/selected/checked state, read `classList` or computed style. A compressed image was misread as the wrong button being highlighted.
- **A passing diff is not a passing test.** "No regression" was reported from code review alone more than once, and was wrong.

Do not re-verify the TEST-01 regression audit in `docs/05-test-log.md`. It was done directly against the file at handoff. Treat it as ground truth and spend verification effort on new work.

## Traps this file has already hit

Full detail and root causes in `docs/06-lessons-learned.md`. Each cost a real cycle.

- **Range checks need both bounds.** `dateToCol()` clamped early dates onto column 0 because only the upper bound was tested. The first fix then over-corrected and would have excluded valid first-week dates. Boundary fixes need just-inside and just-outside tests on **both** sides.
- **Test N=3, not just the reported N=2.** The label collision system re-collided on the third marker in a cluster because it was built as a two-state toggle.
- **"The code exists" is not "the code is wired up."** Dependency lines went stale because `drawDepLines()` was never added to the `rerender()` cascade. Tooltips never fired on real milestones because the listener was only bound to baseline ghosts. When a pipeline gains a stage, audit every entry point that should trigger it.
- **A control that sets state must also show state.** The dependency All-on/All-off buttons never reflected which was active. Build both directions together.
- **`border-collapse: collapse` silently kills `position: sticky` on table cells.** This table uses `separate` with `border-spacing: 0` for that reason. Do not change it.
- **Flex children default to `min-width: auto`,** which blocks wrapping regardless of `overflow-wrap` or `max-width`. Text in a flex container that must wrap needs explicit `min-width: 0`.
- **Never `innerHTML`-rebuild the subtree containing the clicked element inside its own click handler** without `stopPropagation()`. The bubble phase reaches a detached node, and a document-level click-outside listener fires. This closed the milestone dialog on every internal link click.

## Tokenization discipline

No invented values without cause. Every colour, spacing, and text token so far was derived from what the file already predominantly used. Before adding a value, check what is already close. Merge two colours on **role**, not on hex proximity — several "looked identical" clusters turned out to be genuinely different semantic states.

Docs live in `docs/tokenization/`: the Migration Log (component status + the append-only Measurement Log), the Path Plan (remaining phases), and the generated `Hardcoded_Colour_Audit.csv`.

**Before starting any tokenization phase, re-run the audit:**

```
python3 tools/colour_audit.py
```

It regenerates the CSV and prints every Measurement Log metric. Append the results as new rows. **Never edit or delete a prior row** — the log is the history, and the last row per metric is the current figure.

**Never write a count into prose**, here or in any doc. Prose says what a metric means and where to find it. The number lives only in the Measurement Log. This rule exists because the tracking docs previously drifted 3-4x out of date with no trigger to revisit them.

## Working style

Direct, fast, no filler. Concrete implementation for well-scoped requests, not proposals. State an interpretation and proceed when something is ambiguous, rather than blocking, unless proceeding risks real wasted work. Review and approval is expected before large structural changes.
