# P6 Milestone Dashboard — Architecture

## Front-end / Back-end Split

- **Front-end:** Single self-contained HTML file. Vanilla JS in one `<script>` block, no modules, no bundler, no framework. All CSS in one `<style>` block including token definitions.
- **Back-end:** None. There is no server, no API, no database, no auth. This is deliberate, not a gap.
- **Decoupling approach:** N/A. The only external boundary is the user's local file system (import in, export out). Third-party code is embedded in the file (CLAUDE.md, Hard constraints); SheetJS is embedded (TD-216), so the app makes no network requests.

## Compute / Hosting Strategy

No hosting. The file is opened directly from disk or a file share.

Well-Architected trade-offs behind that:
- **Operational excellence:** zero deploy pipeline, zero environment drift. The file a reviewer opens is byte-identical to the one that was tested.
- **Cost:** nil.
- **Reliability:** no runtime dependency that can go down: SheetJS is embedded (TD-216). Paste, delimited and `.xlsx` import all work offline.
- **Security:** no data leaves the machine. Schedule data is commercially sensitive and client-owned, so a hosted variant would need a data-handling review that has not been done and is not currently wanted.
- **Performance:** full DOM rebuild on rerender is the known cost. Mitigated by `scheduleRerender()` debouncing, not by incremental DOM diffing. Revisit only if a real dataset makes it visible again.

**Constraint:** any proposal that introduces npm, a build step, a bundler, or a hosted back end conflicts with this section and with `00-project-context.md` §4. Flag it before building, do not implement around it.

## Runtime Structure

| Unit | Purpose | Notes |
|---|---|---|
| `APP_VERSION` | Single source of truth for the version string | Read by the title, the tool-name label (`#ib-label`, at the foot of Data & view since P64), and the export payload. Never hand-edit any of the three. |
| `REPORT_META` | Report meta: `title`, `reportDate`, `projectNo`, `projectNoFromFile` | `projectNo` added at P64 (TD-224). One writer, `setProjectNo()`. Carried by publish (`projectNo`, `projectNoFromFile`), the model export (`projectNo`) and the `reportMeta` mount category. Files from before P64 carry none and keep the current value. |
| `renderInfoBar()` | The schedule info bar (`#info-hdr`), top row of the board's timeline header | Called from `updateHeaderMeta()`. Chips from `PRIMARY_SOURCES` (the baseline when nothing is imported, none when there is no baseline: P74); current is the enabled schedule with the latest data date. Tints that schedule's data-date week (`th.dd-wk`). |
| `window.__SRET_FIXTURE__` (`PREBOOT`) | Pre-boot dataset hook, P74 (TD-239). The test and embedding hook | Read once, at the top of the app script, if defined before it runs. Seeds `SEED_TASKS`, `SEED_MILESTONES`, `DEP_DATA`, the timeline, `BASELINE_SOURCE` and its label, `REPORT_META.projectNo`, the "updated by" name and the heading, exactly as the P73 literals did. Unset in a shipped build. Contract in the Decisions Log, P74. |
| `syncEmptyState()` | The empty state's one writer, P74 (TD-239) | Called at the end of `rerender()` and at INIT. Shows `#empty-state` and sets `body.is-empty` while `isDashboardEmpty()` (no baseline, no imported source, no user milestone). |
| `INGEST_CONFIG` | Header aliases, actual-flag regex, ingest tuning | `headerAliases` is exact-match after normalization, not fuzzy. Accepted gap. |
| `Parse.workbook()` / `Parse.delimited()` | Entry points for `.xlsx` and paste/CSV/TSV | `.xlsx` path loads SheetJS from CDN on demand, `cellDates:false`. |
| `parseLooseDate()` | Date normalization | Handles `dd-MMM-yy`, `dd-MMM-yyyy`, `dd MMM yy`, ISO, `dd/mm/yyyy`, and bare Excel serial. Strips and records the ` A` actualised suffix and the `*` constrained suffix separately. |
| `classify()` / `aggregate()` | Build the milestone list from parsed rows | Hierarchy from a leaf/group pattern: `/^\S*\d\S*$/` on Activity ID (no whitespace + contains a digit = leaf activity; anything else = group/band header). |
| `renderRows()` | Row construction | |
| `rerender(overrides)` | Core rebuild: teardown → phase/week headers → rows and markers → reapply persisted display state → redraw dependency lines → update summary/diagnostics | Expensive, full DOM rebuild. |
| `scheduleRerender()` | 40ms coalescing wrapper over `rerender()` | **Call this, not `rerender()` directly**, unless the DOM must be synchronously current immediately after. None of the 5 existing call sites need that. |
| `drawDepLines()` | Sole entry point for dependency line rendering | Defensively resets SVG layer visibility and clears stuck slider-drag state on every run. Load-bearing — preserve the pattern rather than patching callers. |
| `exportModel()` | Full JSON payload | Includes dependency visibility, milestone health overrides, comments, and short titles alongside row-level health/remarks. |

## Data Mapping

**Source:** P6 export, one row per activity, indented Activity ID column carrying hierarchy.

| Source column | Consumed as | Notes |
|---|---|---|
| Activity ID | Row identity + hierarchy level | Leading whitespace is the hierarchy signal. Leaf/group pattern above. |
| Activity Name | Row title / short-title source | |
| Duration | Milestone detection (0 = milestone) | |
| Start | Start date | May carry ` A` (actualised) or `*` (constrained). |
| Finish | **Primary field** — drives the marker position | Same suffix handling. In a real `.xlsx` export this column is mixed: true dates arrive as Excel serials, dates carrying a suffix arrive as text. Both paths are handled. |
| Predecessor Details | Dependency line source | Format `ACT-ID: TYPE [lag]`, comma separated. |
| Successor Details | Dependency line source | Same format. |
| Total Float | Health/criticality input | |

**Reference sample:** `data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx` — data date 29-Aug-2026, 192 rows, 146 leaf activities, 46 band/group rows.

**Baked-in baseline:** none since P74 (TD-239). Until P73 a 15-Aug-2026 P6 export was embedded as literals; it is now the check suite's reference fixture, `tools/fixtures/baseline/eskay-p73.json`, and never part of the app.

## State Model

Three layers, kept strictly separate. Display state must never mutate schedule data.

1. **Schedule data** — the baseline (the first schedule imported, a published file's own, or the pre-boot hook's; none in a fresh copy) and the imported update over it. A later import does not touch the baseline.
2. **Annotation layer** — health overrides, progress overrides, comments, short titles, row remarks. Exported.
3. **Display state** — column visibility, text scale multipliers, dependency line visibility and thickness, filters, theme. Session-scoped. Not exported except dependency visibility.

Export is currently one-directional. There is no import path that reads the JSON payload back in. Round-trip is FEAT-13, new work, not a bug fix.

## Panel Systems

Two sides plus the filter bar, since P56 (D-20, directed by Matt 2026-09-25/26). Do not conflate them.

| Side | Element | Opened from | Scope |
|---|---|---|---|
| Workspace (left): your annotations | `#ws-rail` (always visible, full height, slate) + `#ws-panel` | Rail icons; `setWorkspaceSection()` / `toggleWorkspace()` | Notes (D-19/D-19a: `NOTES` with status and #ID links, grouped into collections by reporting period, `NOTE_COLLECTIONS` details, bulk status, collection export), Comments & markups (annotation layers, the three exports, Reset row marks), User milestones. Lists (D-06) joins the rail when built |
| Data & view (right): schedule and format | `#settings-drawer` with a vertical rail `.sd-rail` | Header Colour & theme (`toggleFilterBar()`, opens View controls) and Import & settings (`toggleSettingsDrawer()`) | View controls (the former Customize sidebar, `#filter-bar` moved in), Sources (schedules only), Import, Data settings, Diagnostics, Help, About |
| Top filter bar | `#top-filter-bar` | Always shown; collapsible from its own control | Row filtering |

Both side panels push the board above 1024px (`body.ws-open`, `body.dv-open` margins) and overlay below it. The header's five actions (Light/Dark, Print, Save as, Colour & theme, Import & settings) are one set of buttons: a row of icons above 1024px, the More actions menu at and below it.

Plus the sticky-corner quick search in the top-left sticky table cell, two-way synced with the Top Filter Bar Title field.

Before P56 the Customize sidebar docked via a `body.cv-open` class toggle (retired; `body.ws-open`/`body.dv-open` follow the same pattern) rather than a DOM restructure, because `position:fixed` overlays (the sidebar included) are unaffected by an ancestor's margin. That is what lets it dock without disturbing the rest of the page.

### The `sd-` component set and the drawer's spacing contract

The Settings drawer is built from twelve `sd-` primitives rather than per-section markup. The rule, and the reason it is written down here rather than left to be inferred:

**Nothing inside `#settings-drawer` may set `padding` or `margin` inline.** Every edge resolves to one of six tokens declared once on the drawer itself:

| Token | Value | Role |
|---|---|---|
| `--sd-gutter` | `--space-6` | every left and right edge in the panel |
| `--sd-group-pad` | `--space-6` | group top and bottom |
| `--sd-row-y` | `--space-5` | row top and bottom |
| `--sd-stack` | `--space-4` | label to helper to control |
| `--sd-inline` | `--space-3` | between controls on one line |
| `--sd-card-pad` | `--space-5` | inside a card |

This is recorded because the previous arrangement was not a decision anyone made: it accumulated as 31 inline declarations across 18 values, each individually reasonable. An unwritten convention is one nobody can follow, which is the same failure mode as the board-order rule above. `tools/p29_check.py` asserts the contract rather than trusting it: the inline count must be zero, every group must report the same computed gutter, every interior row the same vertical step, every separator the same hairline, and every bordered surface a radius drawn from `--radius-sm/md/pill`.

The primitives: `.sd-group` (titled block), `.sd-row` (label, helper, control; `--split` puts the control on a 160px label column), `.sd-card` (`--pick` selectable, `--empty` dashed), `.sd-badge` (five modifiers), `.sd-step` (`is-done`/`is-current`/`is-waiting`), `.sd-choice` (radio revealing its own body), `.sd-icon-pick`, `.sd-stat`, `.sd-actions` (sticky footer), plus `.sd-tabs`/`.sd-tab`/`.sd-tabpanel`. Nine of them replaced something that already existed in duplicate.

Two colour rules fell out of building it, both worth stating because both were walked into:

- **A fill token is not an ink token.** `--color-health-good` and `--color-purple-deep` are both used as fills elsewhere, so neither can be retuned for a dark panel without breaking the fill. Accent-coloured text on a themed panel is `--color-accent-ink`; success text is `--color-ok-text`. Merge on role, not on hex.
- **The drawer takes `--color-bg-panel`, not `--color-bg-subtle`.** The latter is declared twice in the dark block (TD-88) and the light value wins, which is load-bearing for the week header (TD-98) and would have left the panel white in dark theme.

## Repository Architecture

The repo `MattGestic/MyActivities` hosts multiple independent applications, each on its own orphan branch which serves as that application's main. Branches share no history. This app's branch is `p6-milestone-dashboard`.

The default branch `main-projects-hub` is the repository hub: index, governing documents common to all projects, and the governed `Resources/` library. It holds no application code. Repository-wide standards defined there (branch model, project kit structure, versioning, documentation conventions, resource intake) govern this project and are not restated in this file.

```
Projects/P6-Milestone-Dashboard/
├── CLAUDE.md                  Constraints a new session must load before touching code
├── README.md                  What this is, how to run it, how versioning works
├── src/milestone-dashboard.html    The application. Stable path, always current.
├── src/modules/               Module sources (D-30). MODULES.json is the index; each <id>/ has MODULE.md
├── releases/                  Point-in-time snapshots, named by version
├── data/schedules/            Reference P6 exports for ingest testing
└── docs/                      The six-file project kit + handoff archive
```

**Versioning:** `Major.Minor.Patch-PartialLetter/Number`, e.g. `3.1.0-P1`. Partials accumulate under a minor version; when a batch of real work has accumulated, bump the minor and reset partials — this does not require confirmation. Bumping the **major** version does require explicit confirmation.

The version lives only in `APP_VERSION`. The working file keeps a stable filename so git diffs are readable; the version is carried by `APP_VERSION`, a git tag, and a snapshot in `releases/`. Versioned filenames were the pre-migration mechanism and are retired.

## Decisions Log

| Decision | Alternatives considered | Why chosen | Date |
|---|---|---|---|
| Single-file, no build step | Vite + modules; React SPA | Study team SOE has no Node. File must open from a share or email attachment with zero tooling. | Pre-migration |
| SheetJS on-demand from CDN | Inline the library; drop `.xlsx` support | Keeps the file small for the majority path. `.xlsx` users are on a corporate network with CDN access. Superseded 2026-09-28, see below. | Pre-migration |
| `scheduleRerender()` debounce over incremental DOM diffing | Virtual DOM; targeted patching | Debounce fixed the reported slowdown at a fraction of the complexity and risk. Revisit only if it resurfaces. | Pre-migration |
| Label collision: 3-band cycling, same-row only | General N-marker collision solver | Covers the common case. A 4+ marker cluster in a very tight span can still partially overlap — an explicit, acknowledged scope boundary. | Pre-migration |
| Exact-match header aliases, not fuzzy | Fuzzy/levenshtein matching | Primary `Start`/`Finish` already cover the core need. Fuzzy risks silent mis-mapping, which is worse than a visible failure. | Pre-migration |
| Embedded third-party code only; the app makes no network requests (Matt, 2026-09-28) | Keep the SheetJS CDN fetch; npm and a build step | The file must work offline and on locked-down networks, and a CDN is a supply-chain and availability risk. Permissive licence (MIT, BSD, Apache-2.0), embedded inline with its licence, recorded in `vendor/<lib>/SOURCE.md`. One-time minification at vendoring is allowed; the app is never built. Supersedes "SheetJS on-demand from CDN". SheetJS embedding: TD-216. | 2026-09-28 |
| Two-sided workspace: annotations left, schedule and format right (D-20) | Keep three separate panel systems; one combined drawer with tabs | The old drawer mixed the user's own layer with the schedule layer, and exports sat in a menu. A hard left/right line makes ownership visible. Existing ids and entry points kept so behaviour and checks carry over | 2026-09-26 (P56) |
| Orphan branch per app | Monorepo on one `main`; separate repos | Apps are independent; a shared `main` makes every diff noisy. A separate repo per app fragments a personal workspace. | 2026-09-09 |
| Board order follows the schedule's own order | Alphabetical by WBS path; by phase; by date | The board presents the client's schedule, so it presents it in the client's sequence. Anything else makes the reader reconcile two orderings, and the schedule's order carries meaning the dashboard does not know. **This rule was assumed rather than recorded, and the code did the opposite for as long as import existed (TD-65).** | 2026-09-14 |
| Baseline overlay is matched by Activity ID, placed at the baseline's own date on the live marker's row line, and painted behind everything | Match by row; match by title; overlay as a separate row; overlay as a date label | The Activity ID is the only key both datasets share and the only one that survives a row being regrouped. Taking Y from the live marker and X from the baseline date makes the horizontal gap between the pair the slip itself, readable without a legend. Behind, because the current schedule is what the board is about and the baseline is context for it. | 2026-09-15 |
| The board is built from a registry of sources, not from one update dataset | Keep one UPDATE_* pair and merge on import; a separate array per source read directly by the renderer | `setViewMode()` re-slices `TASKS`/`MILESTONES` from `UPDATE_*` on every view switch, so a second dataset written anywhere else vanishes the first time someone toggles to baseline and back. One registry with one concatenation point means the view switch keeps working and there is a single place that defines what the board holds. | 2026-09-16 |
| A duplicated Activity ID on append gets a numbered suffix, rewritten across every field that carries it | Namespace the ID by source; keep duplicates and disambiguate at lookup; refuse the append | The ID is a key in more places than it looks: `msKeyFor()` for three annotation stores, `task.ref` for row-to-milestone lookup, `data-ids` for the ID filter, and first-match lookups in `markerCenter()` and `findMilestoneBySnip()`. Disambiguating at lookup would mean changing all of them and hoping none was missed. One suffix, applied once, keeps every existing key correct. Rewriting `id` without `notes` and `ref` is what silently decouples a milestone from its own annotations. | 2026-09-16 |
| Performance claims are asserted by counting, not by wall clock | Timing budgets in the check; no assertion at all | Every probe in this project runs under Chromium's `--virtual-time-budget`, where `performance.now()` does not advance with real work. The first draft of `p30_check.py` reported 0ms against every budget and would have gone on reporting 0ms however slow the code became: a vacuous pass with a number attached, which is worse than no number. Counting what the optimisation promises (one index build reused, one filter pass per burst, zero per-cell writes) is deterministic and fails when the optimisation is removed. | 2026-09-16 |
| The settings panel is a component set with one spacing contract, not per-section markup | Restyle the existing sections; a CSS framework; leave it and add the new controls in the same style | Two halves of multi-source work both add markup to this panel. Building them on 31 inline declarations across 18 values means writing the mess twice and then rewriting it. The contract is asserted by probe rather than claimed, because a convention nobody measures drifts back on the next change. | 2026-09-16 |
| The drawer is tabbed, with a sticky action footer | One long scroll (as before); an accordion; a separate settings page | Six stacked sections put the terminal actions above the thing they act on and buried settings that outlive an import two disclosures deep inside Import. Tabs also give the setup flow somewhere to keep its shape: the steps show state instead of appearing and disappearing. | 2026-09-16 |
| Print preview is a reversible mode, not a print action | A Print button calling `window.print()`; a permanent A3 `@page` rule; a separate print stylesheet only | Page fit is something to check and adjust before printing, not to discover in the print dialog. The `@page` rule is injected only while the mode is on, so a plain Ctrl+P is unaffected for anyone who did not ask for A3. The mode never travels into a published file. | 2026-09-15 |
| | The board's date range is derived from the imported data, not from a fixed window around the data date | Keep the 12-before / 26-after window; make the window bigger; ask at import | The board exists to show a schedule, so its span is a property of that schedule. The fixed window was wrong in both directions on the same file: three milestones past its end plotted nowhere while eight empty weeks sat before its start. The window survives only as the fallback for an import carrying no usable dates, which is the one case where there is nothing to derive from. | 2026-09-15 |
| The week filter marks; the date range filter narrows | Make both narrow; make both mark; one control with a mode | They answer different questions. "What is in week 12" wants the week marked in context, which is why painting its cells was reverted (TD-79). "Show me September to October" wants a September-to-October board. Both resolve to one [lo,hi] column pair, so there is a single definition of in-range and the two intersect rather than fight. | 2026-09-15 |
| A progress override that matches the schedule is discarded; a health override that matches is kept | Store every committed value; store nothing and diff at read time; a separate "cleared" sentinel | The two stores answer different questions. Health has a value ("explicitly N/A") that is genuinely distinct from having no opinion, so key presence is the state. A progress figure has no such value: entering 40 against a schedule that says 40 adds nothing a reader could act on, but it does add a row to the annotation count they are shown when choosing what to restore, and it makes the edited indicator lie. Discarding it keeps the count honest and gives the indicator one meaning: this differs from the schedule. | 2026-09-18 |
| Seven header buttons collapse into one menu, and the rows keep their ids | Rebuild the controls as menu items with new ids and rewire the five functions; a toolbar that wraps; keep the buttons and shrink them | The buttons were a fixed 254px against a label that needed 215.8px and was getting 35.2px at phone width, so something had to give and the buttons are the part with somewhere to go. Keeping the ids is what makes it a layout change rather than a rewrite of five working state machines: the diff against the previous release shows those functions byte-identical. The cost is that six of seven controls no longer show their state at rest, which is paid for by letting the two notification dots escape to the trigger and leaving the rest to be evident from the screen. | 2026-09-19 |
| The print preview's heading bars are sized from the sheet, and the preview's controls sit at the sheet's left edge | Leave the bars at viewport width; wrap the bars inside `#page-frame`; keep the controls on the right and pin them with sticky positioning | The bars are part of the page being previewed, so they take the page's width. Moving them inside the frame would put the app's chrome into the thing being checked for print and would change the normal, non-preview layout, which is the one thing the preview must not do. The controls go left because a sheet wider than the viewport scrolls sideways and the left edge is the only end on screen at every width: measured 0 of 3 reachable at 390 on the right against 3 of 3 on the left. Sticky positioning would keep them visible at the cost of sliding them over the message they sit beside. | 2026-09-22 |
| A second More Actions trigger, not a second menu | Duplicate the panel in the banner; move the panel out of `#ib-menu` into `<body>`; no trigger in the preview at all | The panel's seven rows keep the ids their original buttons carried, which is what let the P36 consolidation leave five state-writing functions untouched. A duplicate panel duplicates those ids and breaks that guarantee immediately. One panel plus `moreActionsAnchor()` means the only new thing is which element the popup is placed against, and all three placers ask the same resolver. | 2026-09-22 |
| Date fields filter on `input` as well as on `change` | `change` only (as before); a Filter button; `blur` | `change` on `<input type="date">` does not fire until the field is committed and left, so a range set with the picker or the spinner did nothing until focus moved elsewhere. `input` fires the moment the value becomes a whole date. It goes through the existing `scheduleFilter()` debounce, so a part-typed date costs one deferred pass rather than one per keystroke. A button would be a second thing to remember for a control that already reads as live. | 2026-09-22 |
| A milestone a person adds lives in the annotation layer and is merged at render time | Write it into TASKS/MILESTONES; a fourth dataset; refuse to support it | The three-layer rule: it never came from P6, so it must not survive as though it had. Merging at the top of renderRows() puts it at the one function every build path goes through, and idempotence means a re-slice that drops it is repaired on the next rebuild rather than losing it. Weight 0, because a weighted addition would silently move every percentage on the board. | 2026-09-22 |
| The print preview lays out for a sheet the user picks, and names it back | Keep a fixed A3 layout; detect the paper; lay out for A4 because it is the common default | CSS @page is advisory in this path: the print dialog owns the paper and there is no API to read what it is set to. So the layout cannot be made to follow the paper, and the paper cannot be made to follow the layout. What is left is to let the person state which sheet they will select and to say it back to them, which is what the header does. A fixed layout of any size reproduces the defect for everyone who picks a different one. | 2026-09-23 |
| One writer moves the @page rule, the sheet width and the column fit together | Set each where it is needed | Those three were set in three places and that is exactly how the preview came to show one sheet while @page asked for another. They are three consequences of one choice, so one function owns them; applyPrintPage() is called from entering the preview and from each control. One PAGE_PAPERS table serves the preview and the PDF exporter, for the same reason. | 2026-09-23 |
| A sheet too narrow for the columns says so instead of shrinking them | Shrink below the 20px floor to fit; drop columns automatically | A4 portrait cannot carry 39 week columns: 194mm printable is 733px and the floor alone needs 780px. Shrinking past the floor produces a board nobody can read while reporting success, which is the worse failure. Dropping columns silently changes what the report says. The clamp message names the three things that would fix it and leaves the choice with the person issuing the report. | 2026-09-23 |
| Unfilled means not finished, filled means finished | Keep every state filled and rely on colour alone; use fill for something else, such as criticality | This is what `.ms-icon.outline` and the legend have documented from the start; only the STATES table disagreed, and it is the single input to the one helper that draws a marker. Colour alone already carries status, so spending fill on the same fact would be redundant; spending it on finished/not finished adds a second, independent channel and makes the board answer "how much is actually done" at a glance. It also compounds the P42 distinction, where the two finished states are the ones that differ in colour. | 2026-09-23 |
| The card's mark is drawn by the board's renderIcon(), not by shapes the card defines | Keep the card's own CSS glyphs; give the card a simplified mark | Two vocabularies drawn by two pieces of code cannot be kept in agreement, and these were not even keyed on the same field: the card's glyphs were keyed on TYPE, the board's mark on MARKER. Calling the board's helper means the card shows the thing that was clicked, including the fill convention, with nothing to keep in step. | 2026-09-23 |
| A saved edit is marked separately from an unsaved one | One indicator for both; no saved indicator at all; a card-level "edited" badge | They answer different questions. The unsaved tint asks "will I lose this if I close?"; the saved mark asks "is this figure the schedule's or somebody's?", which is the question a reader has weeks later and the reason the CSV was split at TD-156. A card-level badge would say something was edited without saying what. The mark reads the stores rather than the form, so it is about what is committed, and its tooltip names the original value. | 2026-09-23 |
| The milestone card holds pending values and commits once, instead of each field writing its own store | Keep per-field autosave and add a Save button beside it; autosave everything and offer an undo | Discard cannot exist without a draft: with every field writing on keystroke, blur or click there is nothing to throw away, which is why the card previously had no close-without-saving at all. A Save button beside autosaving fields is two writers for one value, and the one field that had that arrangement is the defect that was reported. The baseline for "dirty" is read back OUT of the form on open rather than assembled separately, so it cannot drift from what the form was actually given. | 2026-09-23 |
| Close and Escape discard; clicking away from the card saves and closes | Both discard; both save; prompt on leaving | The user's own reasoning: clicking off is leaving, not a decision to destroy work, while the control marked with a cross is deliberate. A prompt on every incidental click-away would make the card hostile to use. The two gestures are on opposite sides of the head so neither can be hit for the other. | 2026-09-23 |
| Field edits live in ONE store applied at render time, not in per-field stores or in MILESTONES | One store per field, mirroring the existing annotation stores; write the edit into MILESTONES directly | Writing into MILESTONES breaks the three-layer separation and cannot be undone once the schedule value is gone. Six parallel stores means six publish keys, six export columns, six import categories and six CSV columns, and six chances to miss one. Applied beside mergeUserMilestones() at the top of renderRows(), the one function every build path goes through, so all 24 sites that read a milestone's date see the edit with no change to any of them. Restore-then-apply makes it idempotent and makes clearing an override work. | 2026-09-23 |
| The Activity ID, the predecessors and the dependencies stay read-only | Make the ID editable like everything else; allow relationship editing | The ID is the key msKeyFor() files every annotation under, so editing it would orphan the comment, health, progress and short title already attached to that milestone. The relationships are the schedule's own graph and the tool never writes back to P6. msKeyFor()'s no-ID fallback was hardened for the same reason: it composed a key from type and date, both now editable, and now reads the schedule's own values from _msBase. | 2026-09-23 |
| A person marking a milestone off resolves to its own DONEUSER state, not to the schedule's DONE | Recolour DONE and accept that both kinds of finished look alike; add a parallel flag beside the override; rename DONE to COMPLETE throughout | The request is for the two to be distinguishable, which means they have to BE two states before any CSS can tell them apart: the colours were already ink and green, and effectiveState() was collapsing them. A parallel flag is a second source of truth for one fact. DONE was not renamed because the embedded P6 seed data literally carries state:"DONE" — DONE is the upload's vocabulary, and STATE_LABELS carries the user-facing word, so the wire format and the wording can move independently. | 2026-09-23 |
| Health values 0 to 3 keep their existing numbers; Done is added as 4 | Renumber to match the new severity order; move to string keys | The numbers are persisted in published files and exported models already in circulation. Renumbering would silently re-colour every one of them on next open, with no version marker to detect it by, which is the kind of change that is invisible until a client opens an old file. Relabelling 3 from Issue / delayed to Critical costs nothing because the number is what is stored. | 2026-09-23 |
| Complete is not settable by a person; black is reserved for what the upload records | Let a person set Complete as well; drop the distinction once a milestone is finished either way | Black means the schedule says this is done. If a person could set it, the board would no longer be able to answer which finished items came from the data and which from this update, which is the whole point of the change. FUTURE is kept as a seventh state although the request's list does not name it: it is a real schedule state meaning not yet started. | 2026-09-23 |
| A row grows when its densest run of VISIBLE markers reaches the band count | Grow on the row's total markers (as shipped at P40); grow on total marker count regardless of proximity; a fixed pixel threshold | Three is where every band is in use and the labels stack hard against each other, so the threshold is MS_LEVEL_CYCLE.length rather than a number chosen. Total marker count ignores proximity and would grow rows whose markers never collide. Counting the row's total markers is what made row 51 grow while the report said it should not: its crowd was off the board behind a date range. Labels that are not on screen collide with nothing, so growth follows what is rendered. The cost is real and accepted: row heights now change when the date range changes, and because --mdx/--mdy are computed from the height at render time, a change means a rebuild rather than a resize. | 2026-09-23 |
| The exported CSV separates the schedule's own values from what was entered | Keep the effective value (as before); export two files; add a provenance column per field | One file with two named blocks is what a reader can sort and filter in a spreadsheet. The effective value is the defect: a report that cannot tell a schedule figure from a typed one is the wrong report to send. A provenance column per field doubles the width for information that block position already carries. | 2026-09-22 |
| A control that cannot act is disabled AND made unhittable, not just dimmed | Dim it only; hide it entirely; leave it live and let it scale invisible text | Dimming alone still lets the control be dragged, which is the state it was already in when it read as broken. Hiding it makes the panel jump as toggles flip and removes the affordance that says the setting exists. `disabled` is the real barrier, but it is invisible to any test that can be written, so `pointer-events:none` sits beside it: a second barrier that a hit test can actually measure. The row keeps its own pointer events so the tooltip still explains why. | 2026-09-22 |
| The baseline overlay toggle lives beside the View toggle, and the action bar above the tabs | Leave both where they were; duplicate the baseline toggle into the heading; keep the action bar sticky and offset it against the drawer header | A control belongs next to the thing it depends on: the overlay only means anything in the Update view. A duplicate would need a second writer or a sync between two copies, which is the drift shape this file has paid for four times. The action bar sat below the tables that feed it, so the drawer read machinery first and outcome last; above the tabs it is the first thing seen, and it stops being sticky because `.sd-hd` already occupies `top:0` and there is no measured header height to offset a second sticky element against. | 2026-09-22 |
| The filter row is two containers that wrap as whole columns | One wrapping row (as before); a fixed two-column grid; a media query breakpoint | One row gives a continuum of shapes, most of which break a label away from its control. A fixed grid cannot collapse at phone width. A media query puts the break at a width someone typed rather than where the content stops fitting. A flex basis gives exactly two shapes, and the check asserts it is in one of them rather than asserting which. | 2026-09-22 |
| No schedule is embedded in the app; the first import becomes the baseline; tests seed their reference data through a pre-boot hook injected centrally (P74, TD-239, Matt 2026-10-01) | Keep the embedded baseline and add an empty state beside it; seed tests through the published-state block; edit every check to import its data | The app is distributed beyond the client whose schedule it carried. The published-state block would make every check's page a published file and change what those checks assert about "published". Per-check imports would rewrite most of the suite and its fixed counts. Detail below. | 2026-10-01 |
| **Proposed, D-30:** modules are the source; the app's module regions are generated between `@module` markers by `tools/modules_embed.py`, indexed and versioned per module in `src/modules/MODULES.json` (`docs/decisions/D-30-module-amalgamation.md`) | Hand-paste between banners (pre-D-30); ES modules plus a bundler; per-module repos or submodules; a `VERSION` constant in each module | The amalgamation pattern (SQLite, stb) keeps the single-file deliverable and no build step, adds a version and a tamper check per module, and replaces greedy banner boundaries that lost CSS in TD-238. A bundler breaks the no-build constraint; separate repos add overhead with one consumer today. | 2026-10-02 |
| Stable filename + git tags for versioning | Keep versioned filenames | Versioned filenames make every change a whole-file add, defeating the point of migrating to git. | 2026-09-09 |
| **D-23 (detail of the embedding decision above):** the embedded SheetJS block sits last inside `<body>`, and whole-file audits skip `vendor-*` blocks | After `</body>` (parse error; the parser moves it into the body anyway); before `#app-script` (parses a library most sessions never use ahead of the app) | Placement verified in Chromium 2026-09-27. The embed, version and build choice are TD-216. | 2026-09-28 |
| **Proposed, D-25/D-26:** schedule model plus batch rendering. Revisits "`scheduleRerender()` debounce over incremental DOM diffing", whose stated trigger ("revisit only if it resurfaces") has now been met. | Milestones-only import (rejected by Matt: all activities and headings are required); row virtualisation (breaks print, sticky headers and off-screen dependency stubs); a charting or grid library for the board | The measured cause is cell count (rows x weeks) and layout reads in dependency drawing, not the debounce. One timeline cell per row, class-only filters and data-derived geometry remove both without changing what the user sees. TD-219, TEST-59. | 2026-09-27 |
| **Proposed, D-27:** grouping hierarchies are independent trees over the same rows; saved views are stored as changes from the system view and are annotation data | One editable hierarchy (conflates imported structure with display); full-copy views (far larger at client scale, metric `view_full_kb` against `view_delta_kb`, and they do not inherit new activities) | Keeps imported structure read-only and the three-layer rule intact; views inherit system positions on each import for free. | 2026-09-27 |
| **Confirmed, D-10:** schedule hand-back is a change register only | XER patch for manual P6 import; regenerated XER | Matt's choice 2026-09-27. "Never writes back to P6" stands unchanged. | 2026-09-27 |
| **Deferred:** D3, as a vendored module subset, for new views only (logic view, trend and S-curve charts) | vis-network (canvas: no CSS theming, nodes invisible to DOM checks, no date axis, cannot be trimmed without a build step); Mermaid (3.5 MB); full D3 bundle | SVG output matches the existing board and check tooling; module subset keeps the inline cost small. Not for the existing board, which needs none of it. | 2026-09-27 |
| The grid view is a core plus optional features, configured once with `SRETGrid.setup()` | One module with every feature (as before); separate grids per use; a configuration object passed to every `open()` | One module made every use carry lists, import and export whether it needed them, and every app-specific string and format lived inside it. Separate grids would fork the engine skin and the tests. Repeating shared settings on every `open()` is what the demo did, and each screen drifted. A core with feature hooks keeps one engine, lets a screen or another app load only what it uses, and puts deployment choices (features, defaults, wording, date format, layout) in one upfront call that fails fast. Measured: no change to open, filter or scroll timings (`tools/grid_view_check.py`); the core alone is proven by `tools/grid_view_modular.py`. | 2026-09-30 |
| **P76 (TD-242): loss prevention is a leave guard, an always-on pull-to-refresh lock and browser-side backups kept as revisions; a backup is the Save payload, keyed by dashboard identity** | Prompt only (no backup); a conditional pull-to-refresh lock; backups in localStorage only; one backup slot per origin; restore by reloading the page with the payload | Matt lost work to a pull-to-refresh on Android (2026-10-02). The prompt alone does not cover phones (some never show it, and a discarded background tab gets no beforeunload), so the backup is the real control and the prompt is the courtesy. The payload is `publishStatePayload()` so a backup holds exactly what Save would and restores through `applyPublishedState()`, the path a saved copy opens by; no second serialiser to drift. IndexedDB because a real schedule's payload outgrows localStorage; localStorage is the fallback and the synchronous last-chance copy. Keyed by identity, not origin, because every file:// page shares one origin. Detail below. | 2026-10-02 |
| **P79 (TD-247, D-31): a blank copy continues from a saved file by reading the file's state as text and loading it through the P76 restore path; the read is a module, the load an adapter, the UI interim** | Save in place with the File System Access API; merge the saved file into what is open; run the saved page in an iframe and read its state; accept the annotations model export as the input | Matt, 2026-10-03, asked for continuation between periods within the fixed constraints (no network, no server, a file that cannot write itself). Every saved file already carries its whole state in one element, and P76 already restores a whole state into a live page. Reading text and `JSON.parse` keeps the picked file inert, where an iframe would run its scripts. A mirror, not a merge, because merging annotations into an open schedule already exists (the Sources mount). Save in place stays possible but needs an IT-policy spike and does not work on Android. Module, adapter and interim UI are separate because the redesign replaces only the UI. Detail below. | 2026-10-03 |

---
**Rules:**
- Amend on architecture-impacting changes only.
- If a backlog item conflicts with a decision here, flag it before building.

### Loss prevention: leave guard, pull-to-refresh lock, backups with revisions (v3.1.0-P76)

TD-242, TEST-79. Matt, 2026-10-02: "a refresh lock that prevents the screen from refreshing if there have been unsaved changes ... a cache to store files as a backup and ... revision control on them". He uses the app on Android (Chrome or Edge, a downloaded file opened from a `content://` URL) and on Windows desktop.

**Unsaved work** is the pill's state, `DIRTY_SINCE_EXPORT` (set by `noteMarkup()`, cleared by `markSaved()` from Save and the model export, unchanged), or an open milestone card whose form differs from what it opened with (`msDirty()`). `hasUnsavedWork()` answers both.

**Leave guard.** The `beforeunload` handler beside `noteMarkup()` (it existed since before P65, with `returnValue=''`) now calls `preventDefault()` and sets a non-empty `returnValue` when `hasUnsavedWork()`, so Chromium shows its own "Leave site?" prompt on refresh, close or navigation. Before deciding, it calls `bkLeaving()`: an edited open card is committed the way closing it would (`saveMsDialog(false)`, the P75 rule that leaving a card is saving it), and a backup is written, so choosing Leave loses nothing.

**Pull-to-refresh lock.** `overscroll-behavior-y: contain` on `html`, `body`, `#scroll-wrap`, the Data & view scroller and `#ws-panel`, always. Chromium on Android starts pull-to-refresh from the root scroller's overscroll; `contain` stops it and stops a scroller handing its overscroll to the page. Scrolling inside each is unchanged, the P72 heading still scrolls away (it reads `#scroll-wrap`'s own scroll events, not chaining), and drag is pointer-driven, so neither depends on overscroll.

**Backups.** One module, `bk*` functions, placed before INIT; `bkBoot()` runs last in INIT.
- *Payload:* `publishStatePayload()` minus provenance (`publishedAt`, `publishChain`, `fromVersion`) and the counter (`markupCount`, `lastMarkupAt`), which change without the work changing. The rest, as JSON, is the revision's content; its FNV-1a hash plus length (`sig`) decides "same work". The counter rides on the record. Restore puts both back and keeps this file's own provenance.
- *When:* debounced 2 s after `noteMarkup()`, `rerender()` (imports, view settings, restores), `saveHistSettings()` and `setProjectNo()`; a 20 s safety tick for a change that reaches none of them; at once on `visibilitychange` to hidden and on `pagehide` (`bkLeaving()`), because a mobile browser discards a background tab without `beforeunload`. A save is skipped when the content's `sig` equals the last one. Labelled, pinned revisions: `Before import` (start of `runIngest()` and of a model mount), `Before restore`, `Saved copy` (Save and the model export).
- *Store:* IndexedDB `sret-backups`, stores `revs` (records: `{id, dashKey, dashLabel, place, rev, savedAt, appVersion, label, pinned, summary, sizeBytes, sig, markupCount, lastMarkupAt}`; the list reads only these) and `payloads` (`{id, json}`, read to restore or download). If IndexedDB throws or refuses (some `file://` and private contexts), the same records go to localStorage (`sret-bk-index`, `sret-bk-p:<id>`) under a 3M-character budget, and the user is told once. An open that never answers falls back after 5 s without a message (headless virtual time does this; so may a slow phone). `bkLeaving()` also writes a synchronous last-chance copy (`sret-bk-pending`, up to 2M characters) because an IndexedDB transaction started during unload may not commit; the next open adopts it as a revision unless one with the same `sig` exists, and moves any fallback records into IndexedDB once it opens. Every call is in try/catch or a caught promise chain; a failure never reaches the app.
- *Key (storage-key choice):* `bkIdentity()`. With a schedule: `p:<project no>|<data date>|<file>` of the primary schedule, which is the baseline when there is one (the dashboard's first schedule, which a weekly update appended or swapped in does not replace) and otherwise the first source. With none: `t:<document title without the version>|<path>`. Not the origin: Chromium gives every `file://` page one origin, so two dashboards opened from two files share one IndexedDB and are kept apart only by this key. Each revision also records `place` (protocol, host and path of the page that made it). Recovery and the panel take revisions matching the current key, the key the page opened with, or the place, so work done in an empty copy that then imported a schedule (its key changed) is still found when that same copy is reopened empty.
- *Revisions and retention:* `rev` counts up per key. After each write, per key: the newest 20 autosaves; older ones keep the newest of each day for 14 days; pinned (labelled) ones, newest 10. Across all keys, over 150 MB the oldest unpinned go first, then the oldest pinned, never the newest of a key. A write refused for quota evicts the oldest unpinned and retries. The panel reports this dashboard's count and size and the browser's total.
- *Restore:* takes a `Before restore` revision, then `bkApplyPayload()`: empties what `applyPublishedState()` merges into (baseline, sources, user milestones and rows, moves, deleted rows, short titles, dependency comments and visibility, `ENTRIES`, note collections, row overrides), sets the payload as `window.__PUBLISHED_STATE__` for the call and puts the previous value back, keeps `PUBLISHED_META` and `PUBLISH_CHAIN`, then `rerender({})` (which drains the row overrides). The projected stores are never written here; `applyPublishedState()` rebuilds them from `ENTRIES`. Restored work shows as unsaved.
- *Download:* the payload under a model identity block (`kind`, `schemaVersion`, `exportedAt`, `scheduleDataDate`, ...), so the existing Sources mount (`validateModelPayload()`, `applyAnnotSelection()`) reads it back.
- *Recovery on open:* `bkCheckRecovery()` shows `#bk-banner` (non-blocking, fixed, no focus taken) when the newest relevant revision differs from what the file opened with, is newer than the file's own `publishedAt`, is not a `Saved copy` and is not empty, and the user has changed nothing yet. Restore, Dismiss (this visit only; the revision stays) or View backups.
- *A saved copy* carries no cache UI: `bk-list`, `bk-status`, `bk-clear-row` and the banner message are in `PUBLISH_CLEAR_IDS`, and the banner is saved hidden.

**Platform limits (recorded, not fixable from the page):**
- Chrome shows the leave prompt only after the user has interacted with the page, and never lets the page set its text. Some mobile browsers do not show it at all, and a background tab the system discards gets no `beforeunload`; the backup written on `visibilitychange`/`pagehide` is what covers those.
- Backups are per browser, per device, per profile. They do not follow the file, and clearing site data (or a private window closing) removes them. Chrome and Edge on the same machine have separate stores.
- All `file://` pages share one origin in Chromium, hence the identity key. A `content://` page on Android has its own storage rules; where IndexedDB is refused the localStorage fallback applies, and where neither is allowed backups are off and the panel says so. Not tested on a device here: the checks run desktop headless Chromium.
- An edited, still-open card is committed on hide as well as on leave, so switching apps on a phone saves the card's edits (the card stays open). Text typed into a card that is then discarded by the system before any hide event is not recoverable.
- The 2 s debounce means a change made in the last 2 s before a crash with no hide event can be missed.

### Continue from a saved dashboard (v3.1.0-P79)

TD-247, TEST-82. The contract, the decisions and the redesign hand-off are in `docs/decisions/D-31-continue-from-saved.md`, and are not repeated here.

**Path.** File, then `continueRead()`, then `SRETContinue.read()` (text, the published-state element's assignment, then `JSON.parse`, then checks and summary), then the pending file. `continueApply()` then runs `bkSaveNow('Before continue')` (captured synchronously, skipped on an empty board) and `bkApplyPayload(payload)`, the same path as a P76 restore and so as a saved copy opening. Then `PUBLISHED_META` and `PUBLISH_CHAIN` are set from the payload, and `renderMounts()` and `syncEmptyState()` run. No store is written outside `applyPublishedState()`, so the P65 projection rule holds.

**Failure.** `bkApplyPayload()` empties the stores before applying. A board that had work is therefore captured first (`bkCapture()`) and re-applied if the load throws or returns false, with the provenance put back.

**What is not carried.** Anything outside `publishStatePayload()`: display state in localStorage (filter bar folds, Workspace sections) and this browser's backups. That is the same set a saved copy opening does not carry.

**Limits.**
- The reader matches the element `publishDashboard()` writes. A saved file edited by hand so that the element no longer opens with the assignment is refused, not repaired.
- The summary's counts are what the file holds. Rows hidden by a disabled source are counted, because the payload carries every source in full.

### No embedded baseline, the pre-boot hook, and central fixture injection (v3.1.0-P74)

TD-239, TEST-76. Matt, 2026-10-01: remove the embedded baseline and open on an empty state.

**What the app holds at boot.** Nothing. `SEED_TASKS`, `SEED_MILESTONES`, `DEP_DATA` and the timeline are empty unless the pre-boot hook supplies them, and INIT gives an empty board a window of weeks around today (`freeTimeline()`: four weeks before, 22 after, widened to take every user milestone) so the first user milestone has somewhere to land. The heading is "Milestone Dashboard" and stays editable in place.

**Where the baseline comes from.** One of, in order: a published file's own (`p.baseline`, restored by `restoreBaseline()`); the pre-boot hook's seeds; or a deep copy of the first schedule imported (`captureBaseline()`, called from `runIngest()` when `hasBaseline()` is false). `BASELINE_ORIGIN` records which (`published`, `preboot`, `import`) and `BASELINE_FROM_SOURCE` the source id a captured one came from. The Sources semantics are unchanged: the first import is still a primary source and the board shows it in the Update view; the baseline is a separate copy behind it.

**When there is something to compare.** `canCompareBaseline()`: a baseline and an update exist, and the update is not simply the import the baseline was copied from. Until then the Baseline / Update toggle and the baseline shadow switch (one group, `.rpt-sub-view`) are hidden; a second import (replace or append) shows them. A pre-P74 published file carries no baseline, so its published schedule becomes the baseline by the same rule.

**Removing.** Discarding the update falls back to the baseline, as before, unless the baseline is a copy of a schedule being removed (or already removed) with nothing else mounted; then the board empties and the empty state returns (`baselineGoesWithSources()`, and the inline confirmation says so).

**What a published file carries now.** The literals used to travel inside the app script. Publish now writes them into the state block: `baseline` (null when there is none) and `scheduleDependencies` (the schedule's own links, `DEP_DATA_SCHEDULE`). A published empty dashboard opens on the empty state.

**The pre-boot hook (test and embedding hook).** `window.__SRET_FIXTURE__`, read once, at the top of the app script, only if defined before `<script id="app-script">` runs. Shape (`kind: "sret-preboot-fixture"`, `schemaVersion: 1`):

| Field | Seeds |
|---|---|
| `tasks`, `milestones` | `SEED_TASKS`, `SEED_MILESTONES` (copied), and through them the baseline |
| `depData` | `DEP_DATA` and its pristine copy `DEP_DATA_SCHEDULE` |
| `timeline` | `labels`, `dates` (ISO `YYYY-MM-DD`, read as local midnight), `months`, `nowCol` |
| `meta` | `title` and `documentTitle` (heading and tab title), `projectNo`, `sourceName`, `baselineLabel`, `sourceLabel`, `dataDate`, `file`, `updatedBy` |

A malformed value is ignored rather than thrown on. The published-state block was considered for this and rejected: a page seeded through it IS a published file (`PUBLISHED_META`, the update view, the "published" badge and chain), which would change what most of the suite asserts about published copies. The hook's own `<script id="sret-fixture">` is removed from anything `publishDashboard()` writes; what it seeded travels in the state block like any other schedule.

**Central injection.** `tools/check_map/chrome_fixture.py` stands in for Chromium. Every check's `find_chrome()` (`tools/import_check.py` and the local copies in `d01_render`, `d16_check`, `p65_fixtures`, `palette_swap_check`, `persist_check`, `theme_check`, plus the launcher lists in `p70_check` and `grid_view_responsive`) returns it whether or not `SRET_CHROME` is set, so a check run standalone is seeded the same way as one run by `tools/run_checks.py`. It injects `tools/fixtures/baseline/eskay-p73.json` immediately before the app script when the page is the current app (`#app-script` and the same `APP_VERSION` as `src/`), carries no data of its own (no `window.__PUBLISHED_STATE__={` and no `window.__SRET_FIXTURE__={`), and the check has not opted out (a `sret:no-fixture` marker in the page, or `SRET_NO_FIXTURE` in the environment). A page inside the repo is copied to a temp file first, so a tracked file is never written. It then hands the launch on to `$SRET_CHROME` (the coverage wrapper, `chrome_cov.py`, which instruments the seeded page) or to the real Chromium. `releases/` snapshots are another version and are never seeded. `tools/scale_bench.mjs` (Playwright) seeds the same file with `addInitScript`. `tools/check_map/run_one.py` records the fixture as an input of every seeded check, and ignores the wrapper's read of the app file, which is mapped by coverage instead.

**Schedule links (TD-240).** The dependency layer reads `DEP_DATA`, the schedule's links plus the user's (`applyUserDeps()`). The schedule's part, `DEP_DATA_SCHEDULE`, is no longer a literal: it is rebuilt by `rebuildScheduleDeps()` at the start of every `applyUserDeps()` from the view shown. Update view: the union of the enabled sources' `src.deps`, each built at import from that file's Predecessor Details / Successor Details (`depsFromActivities()`). Baseline view: `BASELINE_DEPS` (the pre-boot hook's, a published file's `baseline.deps`, or a copy of the first import's). Publish and the model export write `deps` on each source in the manifest, `baseline.deps`, and the board's set as `scheduleDependencies`; a source from a file that carried only the board's set takes that set on reopen.

**The fixture** is the P73 baseline exactly, extracted from commit `e24d02a` by `tools/fixtures/baseline/extract_p73.py` (`--check` compares the committed file with a fresh extraction). It is the repo's own test data and never part of the app.

### Marker placement (v3.1.0-P34)

Three rules, in order of how much they constrain everything else.

**1. A marker's vertical position is a property of the marker.** Every label is a child of `.m-wrap`, so it rides whatever the wrap does and always sits at its own icon's height. That is what makes a label traceable to the marker that owns it. There is exactly one vertical offset per marker and exactly one writer for it, `renderMarker()`.

**2. The anchor is the cell's true centre; every offset is pixels.** `.m-wrap` sits at `left:50%; top:50%`, which resolves against the cell's real padding box whatever height the row turns out to be. `--mdx`/`--mdy` are pixel offsets budgeted from `ROW_HEIGHT` and `COL_WIDTH`, which are minimums the rendered cell can only exceed. So an offset that fits the budget fits the cell, and the error direction is "used less room than was available", which is invisible. A percentage had the opposite direction, needed correcting against a height the render could not know, and grew the spread as the row got taller.

**3. Staggering is proximity-scoped.** A row's markers are walked in column order and cut into runs. A run continues while consecutive markers are at most **two blank columns** apart, a gap of three (`MS_PROXIMITY_COLS`); anything further out starts a new run, and a run of one is dead centre.

The threshold is a fixed count of schedule columns and is deliberately **not** derived from the rendered label width, which is what it was until P34. A label width moves with the label scale controls, so deriving the boundary from it meant changing the text size re-anchored every marker on the board. Marker anchoring answers to the data; only the data may move it.

Within a run the levels **repeat**: top, middle, bottom, top, middle, bottom, with top and bottom for a run of two and the pair symmetric about the midpoint whatever cells its members occupy.

P33 used a triangle wave here instead, so the fourth marker sat on the middle band, on the argument that a plain repeat puts markers one and four on the same line a few columns apart. **That argument is correct and the collision is real.** It was reversed at P34 against a rendered case: row 69 of the reference board carries four markers in directly adjacent columns and the fourth was wanted at the top. Capping the run length cannot deliver that, because a run of one is the middle band by definition. The collision is now an accepted cost, measured rather than avoided. Do not restore the wave from the old reasoning alone; it needs a rendered case of its own.

**Band reuse is legitimate across cells and illegitimate within one.** Markers sharing a cell share an x, so the band is all that separates them. A cell holding more than three grows *its* row via `--row-h-eff`, by the minimum that gives each of them a line. Data-driven, never display-driven: a denser import can change row heights, no toggle ever does.

**Labels never affect layout.** The band is budgeted on the icon, not on the label stack, so it cannot depend on whether labels are shown. The accepted consequence is that a label on a short row can overlap the gutter; it is bounded and clears once the row has room.

`msCellOffset()` is horizontal-only. Two vertical offsets would compound, which is the failure removed at P32 between the icon spread and the label band.

Anything `msCellOffset()` or the band reads (icon size, column width, row height) must flag `_placementNeedsRebuild`, because the offsets are written once at render time.

**Hidden markers are derived, never stored.** `markerHidden()` reads the row's `hidden-row` class and the cell's `data-col` against `DATE_RANGE_COLS`, so it costs no layout and cannot go stale. A stored flag would need writing at four entry points, and this file has three separate defects from a rule applied at some and not others.

### The More Actions menu (v3.1.0-P36)

Seven header icon buttons became one trigger and a seven-row menu. Two rules hold it together.

**The rows keep their ids.** Each row carries the id its button carried, so `toggleSettingsDrawer`, `toggleFilterBar`, `toggleTopFilterBar`, `togglePrintMode` and the two dot writers address exactly what they addressed before and none of them was touched. That is asserted by diffing those function bodies against the previous release, not claimed. A consolidation that rewrites the five functions it consolidates is a much larger change wearing a layout change's clothes.

**State that is a notification escapes the menu; state that is evident does not.** This project's standing rule is that a control which sets state must also show state, and a shut menu shows none of it. The two dots are notifications, meant to be seen without opening anything, so the trigger carries a dot when either row does. It is a CSS `:has()` derivation over the rows themselves, so there is no new state and the four existing dot writers keep their call sites. Everything else the buttons showed is evident from the screen without the menu: a panel is on it, the board is at page width, the page is dark.

Two collisions the move had to survive, both recorded because neither is visible in a code read:

- `.icon-btn.on` and `.icon-btn.ib-mi` have **equal specificity**, so the active state loses on source order alone. The rule is restated for the row, and the check compares computed background against an inactive row rather than testing for the class.
- `toggleTheme` wrote the button's whole `innerHTML`, which on a row with a label would have eaten the label. One `setThemeGlyph()` writer targets the icon span and both call sites use it.

The filter-row toggle now lives in the menu, which touches TD-72 directly: that control was moved into the header so that hiding the filter row could not hide the only way back. The rule is unchanged and still holds, because the trigger outlives the bar and exposes the toggle. What changed is how it is asserted, and that turned out to matter more than the move (TD-136).

### The print preview is a sheet, and the heading bars belong to it (v3.1.0-P38)

`#page-frame` holds the board at one A3 portrait sheet, 297mm, which renders 1122.5px. `#icon-bar` and `.pm-banner` sit **outside** that frame, so they took the body's width, which is the viewport's. That is the misalignment: measured 390px and 1440px wide against a 1122.5px sheet, short of it in one direction and over it in the other.

Both bars now take the sheet's own width, centring and side inset, so the frame's content box and the bars' content boxes coincide. The alignment is asserted on the content boxes as well as the outer edges, because matching the outer edges alone leaves the bar's text offset from the report heading by the frame's 8mm padding.

**A consequence, accepted rather than worked around.** At any viewport narrower than an A3 sheet the whole sheet scrolls sideways, heading included, so the right-hand end of a sheet-width bar is off screen. That is what a page preview is. The controls the preview needs therefore sit at the sheet's **left** edge, which is on screen at every width: measured 0 of 3 reachable at 390 with them on the right, 3 of 3 with them on the left.

**Two triggers, one panel.** The banner carries a second More Actions trigger. The panel is not duplicated, because duplicating it would duplicate seven row ids and the five functions that write them, which is the whole point of the P36 design. Instead `moreActionsAnchor()` resolves which trigger the fixed panel hangs off, preferring the one that was clicked and otherwise taking whichever is laid out. All three placers (open, resize, scroll) go through it, so there is one answer to "where does this panel go". The banner trigger's dot is the same `:has()` derivation as the header one, taken from `<body>` rather than `#ib-menu` since the trigger is not inside the menu.

### Display state has one writer, and it states the state (v3.1.0-P37, extended P38)

`reapplyDisplaySettings()` is the single place that puts display state back onto a freshly built board, called from `rerender()` and from init's first paint. P37 gave it the five slider-owned settings after the Title col slider was found missing from one path (TD-138). P38 added `applyMarkerLabelState()` to it, holding the three things drawn on the board that a fresh render always creates visible: the type-code label, the milestone hours and the remarks field.

That was the same defect again. The rebuild path hid all three, init's path hid one, and a new `mHrsVisible=false` default rendered 196 visible hours labels at first paint (TD-145). Four occurrences of this family now (TD-59, TD-71, TD-138, TD-145), every one of them a second entry point that did not get a line someone added to the first.

The rule this settles: **anything that has to be reapplied after a rebuild goes inside this function, never beside a call to it.** And the function writes both directions (`display = on ? '' : 'none'`) rather than hiding when off, so it states the state instead of depending on what a fresh render happens to leave behind.

### Row height is render-time state, so changing it means rebuilding (v3.1.0-P41)

A row grows by half again when its densest proximity run of **visible** markers reaches the band count. The visible part is what makes it agree with what a reader sees: a label that is off the board collides with nothing, so a row whose crowd the date range is hiding should read like any other row.

That turns a render-time decision into one that depends on display state, and the mechanics are worth recording because neither is optional.

**One run cut, two callers.** `isDenseRunCols()` is the only place a proximity run is measured for this purpose. The renderer hands it the columns it is about to draw; the filter pass hands it the columns it reads back off the DOM. Two copies of a run cut is the drift shape this file has paid for five times.

**The height cannot change in place.** `--mdx` and `--mdy` are computed from the row height at render time, so a height changed underneath them leaves every marker positioned for the previous one. Nothing resizes a row: the filter pass asks whether the rendered heights still match what the visible columns call for, and calls `scheduleRerender(true)` when they do not.

**Three entry points carry that check, not two.** Both exits of `applyFilter()`, including the early return, and `clearFilter()`, which un-hides every row and column itself rather than routing through `applyFilter()`. The third was missed on the first pass and caught by an existing probe (TD-159). The count is asserted at source, so a fourth entry point added without the check fails immediately. This is the same list `drawDepLines()` has to appear on, for the same reason, and the comment describing it was already sitting three lines above the line that was missing.

It terminates because `rerender()` ends by calling `applyFilter()`, and by then the rendered state matches what it was just built for. On a filter that does not change which columns are on the board, which is most of them, it is one cheap pass and no rebuild.

### A milestone a person adds is annotation, not schedule (v3.1.0-P40)

The three-layer rule decides where this lives. A milestone added on the board never came from P6 and must not survive as though it had, so it goes in `USER_MILESTONES`/`USER_ROWS` beside the comment and override stores, round-trips through publish, the model export and selective import exactly as they do, and is **merged** into `TASKS`/`MILESTONES` at render time rather than written into them. `SEED_MILESTONES` and `SEED_TASKS` are byte-identical after an add, and that is asserted rather than claimed.

The merge sits at the top of `renderRows()`, the one function that builds rows, and is idempotent. `TASKS`/`MILESTONES` are re-sliced from `BASELINE_*` or `UPDATE_*` in three places and a fourth would be easy to add; a merge that repairs itself on the next rebuild cannot be defeated by one of them being missed, which is the defect family this file has paid for five times. It is deliberately **not** in `reapplyDisplaySettings()`, which both build paths also call but only after the rows exist.

Two decisions inside the record itself:

- **Weight 0.** A weighted addition would silently move every percentage on the board, and a milestone someone added is not part of the schedule's earned-value rollup.
- **`notes` carries the `[ID] - Name` form.** `data-ids`, `msKeyFor` and `extractSnipId` all re-derive the Activity ID from it, so writing `id` without `notes` is what decouples a milestone from its own annotations. Same reason the multi-source suffix rewrites five fields rather than one.

Activity IDs are `USR-NNN`, numbered from the highest already present so re-importing a published file and adding another cannot reuse a key an annotation store is already keyed on. A collision with a typed ID is refused rather than silently suffixed: the append path may rename an incoming ID because nobody chose it, but quietly renaming what a person typed is worse than telling them.

### Filters compose on one property each (v3.1.0-P40)

The filter bar is three rows because there are three questions: WHAT (name, band, source, Activity IDs), HOW (status and float) and WHEN (week, date range). The critical set is ruled off as its own container because it filters on a different property of the data from the rows either side.

Every row filter is lifted from milestones the same way: a row shows when **any** of its milestones matches. A deliverable with one critical milestone is a critical deliverable, and requiring every milestone to match would hide exactly the rows the filter exists to find. That is the same rule `rowHasZeroDepMilestone` already used, now stated once and applied twice.

Two properties of the status filter worth recording, because both are choices rather than consequences:

- **Empty means no constraint, and that is not the same as all five selected.** The chips start empty and the filter is off until one is pressed. The check asserts that all five selected shows the same board as none, which is what makes the empty default coherent rather than merely convenient.
- **It reads the EFFECTIVE state.** A milestone whose health was overridden on the board filters as what the board shows, not as what the schedule said, because a filter that disagrees with the board it filters is worse than no filter.

The float filter converts weeks to days at the edge so there is one unit downstream, and a milestone with no recorded float satisfies neither direction. An unknown reported as critical is the kind of wrong that reaches a client.

### A report is two blocks: what the schedule says, then what a person entered (v3.1.0-P40)

The exported CSV carried the **effective** Progress % and Status, which is the schedule's own figure unless an override exists, with nothing in the file saying which of the two you were looking at. A report that cannot distinguish "the schedule says 40%" from "someone typed 40%" is the wrong report to send to a client.

`CSV_BASE_HEADER` now holds only values that never move with an annotation, and `CSV_ENTERED_HEADER` holds the annotation layer, blank wherever nothing was entered. Overrides are keyed per milestone and a row can hold several, so a row with more than one entry lists them as `ID: value` pairs rather than picking one and hiding the rest.

`exportCSV()` was split from `buildCsvRows()` for the same reason the rest of this file is shaped the way it is: a check that has to click a download can only assert headers, and the headers were never the defect.

### A control shows its own state, and a dead control looks dead (v3.1.0-P39)

Two rules the View Controls panel now holds to, both of them old rules finally applied consistently.

**A control that sets state also shows state.** `applyMarkerLabelState()` writes the board, the two label checkboxes and the two Row Comments buttons in one pass, and every path that changes one of those three variables goes through it: the handlers, `setColButtonState` (which is what a published file and an imported settings block reach), and the rebuild reapply. The three functions that used to carry their own copy of the display write are gone, two of them already dead. The Remarks control stopped being a single button that relabelled itself to its own action, which read as an action while every other segmented control in the same panel reads as a state.

**A control that cannot do anything is disabled and looks it.** Each label size slider sits under the control that turns its text on and is disabled while that text is off, derived by `syncLabelScaleEnabled()` from the same variables the board reads rather than toggled from each handler.

The mechanism worth recording: `disabled` on an input **cannot be measured through a synthetic event**. `dispatchEvent` reaches an `oninput` listener whether or not the control is disabled, and an untrusted pointer event never drives a range thumb, so the same experiment "fails" on working code and on broken code alike. `pointer-events:none` on the disabled input is the second barrier and the observable one: the element at the slider's own centre is the row when off and the slider when on.

### Where a control lives is part of what it means (v3.1.0-P39)

The baseline overlay toggle moved from the View Controls panel to the report heading, beside the View toggle. It only does anything in the Update view, so it belongs next to the thing that selects the view, and `updateViewToggleUI()` was already its single writer for both the disabled state and the explanatory text, which became its tooltip.

It was **moved, not duplicated**. Two controls for one flag is the shape this file has drifted on repeatedly, and a second copy would have needed a second writer or a sync between them.

The settings drawer's action bar moved the same way: from a sticky footer under the source and import tables to a block above the tabs, so the first thing read in the drawer is the outcome rather than the machinery. It is not sticky any more, because `.sd-hd` is itself sticky at `top:0` and there is no measured header height to offset a second sticky element against.

### The filter row has two shapes, not a continuum (v3.1.0-P39)

Every filter used to be a sibling in one wrapping flex row, so at any width between "all on one line" and "one per line" the groups broke wherever they happened to land. Two containers at `flex: 1 1 340px` now hold their own groups and wrap as whole columns: WHAT narrows the rows on the left, WHEN narrows the columns on the right, with a rule between the week filter and the date range and the summary line full width beneath both.

The basis is a flex basis rather than a media query, so the break happens when the content genuinely stops fitting instead of at a width someone typed, and the assertion is "side by side XOR cleanly stacked" with which one decided by measured room.

### The filter row's phone shape (P67)

Matt's marked-up phone screenshot (`docs/mockups/P67/filter-markup.png`, 2026-10-01). Below 768px, the breakpoint the stacked phone layout already used (`@media (max-width:767px)`, the design standard's <768 field-row rule), and only there:

- Find shows the name field alone. A chevron inside its right end (`#fb-find-more-btn`, `toggleFindMore()`) opens Banding, Source and Activity IDs (`.fb-more`). The open state is display state in `localStorage` (`sret-fb-find-more`). The chevron carries a dot while a filter it is hiding is set.
- Date range and status are **one tile**. CSS cannot put children of two boxes on one flex row, so `syncFbShape()` moves `#tfb-crit` into `#tfb-when` while `FB_PHONE_MQ` (the same query string as the CSS) matches, and back into the bar when it does not. The chips, their ids and their handlers move unchanged, so every filter function and check that clicks a chip still works.
- Status, Total float and Annotations are dropdowns. Each trigger (`.fb-dd-trig`) opens the group's **existing** chips (`.fb-dd-panel`) as a fixed popover placed by `placeFbDropdown()` inside the viewport. The triggers read from the chips' pressed state in `syncFbDropdownTriggers()`, called from `syncStatusFilterUI()`, which every filter change already passes through.
- Box titles and row labels are hidden. Each box keeps `role=group` and an `aria-label`.

At every width, the header toggle `#btn-filter-expand` (the old expand-only icon's id, kept for the checks) sits left of + Milestone, always shown, pressed while the row is open, and is the row's only show/hide control. The bar's own close x `#btn-filter-hide` is gone. `toggleTopFilterBar()` is still the one writer of both states.

### The filter panel collapses to the search field; the heading scrolls away (P72)

TD-236, from Matt's phone screenshots (2026-10-01). Builds on the P67 phone shape above.

**Panel (below 768px, `FB_PHONE_MQ`).** The P67 chevron is now a funnel (same id, `#fb-find-more-btn`; same state `FB_FIND_OPEN`, `setFindMore()` / `toggleFindMore()` / `syncFindMore()`; same storage key `sret-fb-find-more`), and it folds the whole panel, not only Banding and IDs. `syncFbShape()` moves `#tfb-when` (with `#tfb-crit` already inside it) into `#tfb-find` straight after the search field, so the DOM order, and so the tab order, is the visual order: search; Weeks, Mode, Fit; Status, Float, Notes, x; Banding, Source; Activity ID(s). On desktop it goes back into `.fb-top` beside Find. Find's search row is `display:contents` at phone width so its children and the moved tile are Find's own flex items. The dot reads `fbHiddenFilterSet()`, every filter except the name search, from the same state `applyFilter()` reads.

**Heading (below 1024px, `CHROME_AWAY_MQ`).** Every width has two scrollers: the board inside `#scroll-wrap` and the window for whatever the heading pushes past `100vh - 150px`. `onBoardScrollForChrome()` (a passive listener on `#scroll-wrap`) sets `html.chrome-away` after 12px of travel down once the board is past its own info row plus 24px, and clears it after 12px up or back near the top. `setChromeAway()`:
- puts a negative top margin of the board's measured document offset on `#icon-bar` (`--chrome-shift`, set on `#icon-bar` and `.ws-toggle` only), so icon bar, heading, filter bar and board move up together with nothing re-laid between them; a window already scrolled part way is folded into the shift first, so nothing jumps;
- makes the board as tall as the viewport while any shift applies (`html.chrome-shift`), set at the start of hiding and cleared at the end of showing, when its bottom edge is below the viewport either way;
- sticks the info row cells at minus `--hdr-info-h` (just above the board's top edge) and the bands at 0 and `--hdr-phase-h`, the measured variables `watchStickyHeights()` already writes; the info row stays in the table, so nothing re-measures;
- animates only while `html.chrome-anim` is set (200ms), never under `prefers-reduced-motion`.

Three findings that shaped it, each measured on the reference board at 390px:
- **Classes on `<html>`, not `<body>`.** A change to the body's classes re-runs `syncInfoBarWidth()` through its MutationObserver, about 0.3s, which stalled the slide's first frame.
- **No custom property on `:root` per change.** Setting one restyles the whole document, about 0.1s.
- **The info strip's ResizeObserver now acts on width changes only.** The scroll-away changes the board's height; a height change cannot change the strip's width.

`chromeAwayBlocked()` freezes the state both ways while any `[aria-haspopup][aria-expanded="true"]` exists (every dropdown, menu and popover reports this), while the milestone card, the add, PDF or annotation dialogs, a dependency comment panel, the ID suggestions or the float Custom card are shown, while the settings drawer or Workspace panel is open, or while a field in the heading has focus (the phone keyboard). The card is `position:fixed` and is never inside a moved or transformed box. Grid view and print mode are excluded in the CSS selectors and in `chromeAwayEligible()`. Display state only, never stored.

### The milestone Progress override (v3.1.0-P35)

Progress is the first **editable number** in the annotation layer. Everything before it was a colour, a comment or a piece of text, none of which anything else computed from.

`MS_PROGRESS_OVERRIDE` keys through `msKeyFor()` alongside `MS_COMMENTS`, `MS_HEALTH_OVERRIDE` and `MS_SHORT_TITLES`, carries through publish, the model export and selective import as its own `ANNOT_CATEGORIES` entry, and moves with a milestone whose key changes when it is dragged to another row.

Four rules hold it to the three-layer split:

- **`effectiveProgress(m)` is the only reader.** The milestone record is never written, so the schedule's own value is always recoverable, which is the whole mechanism behind "clear the field to restore it". Every consumer of progress goes through the accessor: the card, the progress bar, earned hours, the milestone tooltip, and `computeProgress()`, which is the row's rollup. A card that moved while the row beside it did not would be the same defect class as a marker that reads as belonging to the wrong row.
- **An override equal to the schedule's own value is deleted, not stored.** This is the opposite of `MS_HEALTH_OVERRIDE`, deliberately. Selecting the white health dot is a real choice ("explicitly N/A") distinct from never having touched the control, so that store tests key *presence*. A progress of 40 against a schedule that already says 40 asserts nothing the schedule does not, so storing it would inflate the annotation count a reader is shown when choosing what to restore. It also makes the edited indicator mean exactly one thing: this differs from the schedule.
- **Blank and unparseable both restore.** Neither is saved. The one field whose job is to carry a number does not get to hold something that is not one.
- **The card writes under `msKeyFor(m)`.** It used to compose its own key from `extractSnipId(m.notes)` while every reader used `msKeyFor()`, which prefers `m.id`. Equal on the reference dataset (measured: 146 milestones, 0 divergent) and nothing enforced it, so a milestone whose id and notes disagreed would have had its annotations written where the board never looked.

Marking a milestone complete sets progress to 100%, **one direction only**. Clearing the Complete dot does not drop it back: by then the user may have typed over it, and discarding a number they entered is worse than leaving one they can clear themselves.

The field commits on blur or Enter, not per keystroke, because a commit rerenders the board. The comment field autosaves per keystroke precisely because it costs no rerender.

### Sticky header offsets (v3.1.0-P34)

The two header rows stack: the month band sticks at the top of the scroller, the week band directly below it. The week band's offset is **measured, never a literal**.

`watchStickyHeights()` is the single writer. It puts two custom properties on `:root` from `ResizeObserver`s:

| Property | Source | Read by |
|---|---|---|
| `--hdr-info-h` | `#info-hdr`'s row height (P64; also written by `renderInfoBar()` straight after its content changes) | `tr.hdr-phase th { top }`, and added into `tr.hdr-wk th { top }` |
| `--hdr-phase-h` | `#phase-hdr`'s row height | `tr.hdr-wk th { top }` |
| `--tfb-h` | `#top-filter-bar`'s content height | `#top-filter-bar.open { max-height }` |

Three rules that are load-bearing here:

- **Observers, not hooks.** The alternative was hooks in `rerender()`, `applyRowHeight()`, `togglePrintMode()`, `fitToScreen()` and a window resize listener. Five entry points, and a missed entry point has cost this project a cycle four times. An observer has no call sites to forget. Both observed elements survive rerenders: `renderPhaseHdr()` appends cells to the same `<tr>` rather than replacing it.
- **Measure the row, not a cell.** The month row's metadata cells carry `padding:0` and its month cells 3px, so a single `<th>` is shorter than the row and the week band would stick too high.
- **The filter bar's cap over-estimates on purpose.** `scrollHeight` is read from whichever state the bar is in, and while it is closed its vertical padding has transitioned away, so an exact figure taken then would be short by that padding and clip on the way back open. A `max-height` that overshoots costs nothing visible; it is a cap, not a height.

Both literals these replaced were wrong and had been for some time: the week band sat 3.5px below a 16px row, and the filter bar's 160px cap cut 43px off its own content at phone width.

### The milestone card is the Claude Design dialog; history is one gallery (v3.1.0-P66)

TD-231. Matt's design (`docs/mockups/P66/`) is the source for the card's layout; the app keeps its own fonts, tokens and control sizes (D-16), since it is offline and colour-audited.

- **Every element id the card had is kept,** so its form logic (`msReadForm`, `msDirty`, `saveMsDialog`, the edited marks) is unchanged; the re-lay is CSS and markup order. Fields the design does not show sit in a collapsed More fields fold.
- **The comment box is a new remark, always empty on open.** Earlier remarks are in the history. Saving appends an entry; the follow-up select sets its status, also when the save merges into the previous card entry.
- **One gallery, two places.** `SRETHistory` (module `src/modules/notes-history/`) renders entries for the card (one milestone) and for the Notes panel (grouped per milestone). Both containers stop click propagation: the gallery rebuilds its own markup in its click handlers, and the card's document-level click-away would otherwise close the card (CLAUDE.md trap).
- **Edits from the pencil go through `SRETEntries.edit`,** which refuses entries outside the current report, then the stores are re-projected.

### Entries are the record; the stores are projections (v3.1.0-P65)

Matt's decision of 2026-09-30 (TD-230): every update to a milestone is its own entry, and a roll-up gives the compiled view.

- **One writer path.** Remarks, notes and card or grid edits append or change entries in `ENTRIES` (module `SRETEntries`). `projectEntryStores()` rebuilds `MS_COMMENTS`, `MS_HEALTH_OVERRIDE`, `MS_PROGRESS_OVERRIDE`, `MS_FIELD_OVERRIDE` and `NOTES` from it. Readers were left alone; only writers changed.
- **Latest wins per field**, ordered by `at` then eid. `to:null` is "back to the schedule". Removing an entry falls back to the one before.
- **Projection runs on an entry change, never inside `renderRows`,** so `previewEffState`'s temporary health write and any render path stay as they were.
- **Direct store writes are adopted, not lost.** `adoptStoreDrift()` runs before every writer and projection, compares the stores with the last projection, and turns any difference into an entry with origin `direct`. It exists for older code paths and harnesses; the app's own writers never trip it (`p65_check` asserts 0).
- **Files keep `schemaVersion` 1.** `entries` is added beside the legacy store fields, which are still written (as projections), so a P64 build still opens a P65 file. A file without `entries` is migrated: one carried entry per milestone key.
- **Short titles, dependency comments and row remarks keep their own stores in P65.** Short titles are a display setting and stay that way; dependency and row remarks become entries in P67.
- **Modules.** `src/modules/notes-store/`, `src/modules/notes-card/`, `src/modules/notes-export/`, each with a Node test, pasted unchanged into the app script after the grid view module.

### Schedule info bar and report meta (v3.1.0-P64)

Matt's approved mockup of 2026-09-29 (TD-224). The project details left the app heading for a bar on top of the board's timeline header. Recorded here because the header now has three sticky rows and the report meta changed shape.

- **The bar is a table row, not a div above the table.** It is the first row of `<thead>`, so it scrolls and sticks by the same mechanism as the month and week rows (`border-collapse:separate`, sticky cells) and is captured by the PDF export's header collection with them. A div before the table could not stay pinned sideways: a sticky element cannot leave its containing block, which is only as wide as the scroller.
- **One cell, spanning the laid-out columns.** `syncInfoBarSpan()` sets the span to the number of `<col>`s not set to `display:none`, the one way both the metadata toggles and the date range hide a column. A `MutationObserver` on the colgroup calls it, so no writer has to. A span past the grid would add phantom columns.
- **The strip inside the cell is sticky at left 0 and as wide as the scroller's client width, capped at the board's own width** (`--sib-w`; uncapped, a strip wider than a narrow board stretched every column, the label column past its slider). Its left part is the label column's width (`--sib-lbl-w`, written by `setNameWidth()`), its right part sits over the timeline. `100cqw` was tried for the width and counts the vertical scrollbar, so the strip overhung the scroller by the scrollbar's width and drifted sideways on horizontal scroll. The width is read by a `ResizeObserver` on the scroller and, synchronously, by a `MutationObserver` on the body's class list, where every docking panel and print preview announce a width change; `setNameWidth()` and `setWkWidth()` re-fit it in the same task.
- **The grid view needed `#page-frame` to be a real box while it is open** (`body.grid-open #page-frame{display:block}`). SlickGrid's init treats an ancestor without client rects as hidden, and `display:contents` has none, so it measured the grid's viewport from a shrink-to-fit copy of `#page-frame`: as wide as the widest header line. P63's long project-details line hid this; without it the grid measured 397px at 1440 and never drew its right-hand columns (p61, p63).
- **Current schedule.** The app has no separate notion of a current source (`UPDATE_SOURCE` is only the latest import, whatever its data date), so current is the enabled schedule with the latest data date. Chips are display only; a click opens Data & view > Sources.
- **Project number.** `REPORT_META.projectNo`, seeded from `SEED_PROJECT_NO` for the embedded board, never a markup literal. An import fills it from a leading `^\d{4,}(?:-\d+)?` token in the file name only when it is empty, and marks it `projectNoFromFile` until the user edits or confirms it. A mount applies a non-empty value only, so a mount never blanks a number that is set.

