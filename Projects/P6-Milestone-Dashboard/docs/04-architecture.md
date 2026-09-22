# P6 Milestone Dashboard — Architecture

## Front-end / Back-end Split

- **Front-end:** Single self-contained HTML file. Vanilla JS in one `<script>` block, no modules, no bundler, no framework. All CSS in one `<style>` block including token definitions.
- **Back-end:** None. There is no server, no API, no database, no auth. This is deliberate, not a gap.
- **Decoupling approach:** N/A. The only external boundary is the user's local file system (import in, export out) and one on-demand CDN fetch of SheetJS for `.xlsx` parsing.

## Compute / Hosting Strategy

No hosting. The file is opened directly from disk or a file share.

Well-Architected trade-offs behind that:
- **Operational excellence:** zero deploy pipeline, zero environment drift. The file a reviewer opens is byte-identical to the one that was tested.
- **Cost:** nil.
- **Reliability:** no runtime dependency that can go down, except the SheetJS CDN load, which only affects the `.xlsx` path. Paste and delimited import work fully offline.
- **Security:** no data leaves the machine. Schedule data is commercially sensitive and client-owned, so a hosted variant would need a data-handling review that has not been done and is not currently wanted.
- **Performance:** full DOM rebuild on rerender is the known cost. Mitigated by `scheduleRerender()` debouncing, not by incremental DOM diffing. Revisit only if a real dataset makes it visible again.

**Constraint:** any proposal that introduces npm, a build step, a bundler, or a hosted back end conflicts with this section and with `00-project-context.md` §4. Flag it before building, do not implement around it.

## Runtime Structure

| Unit | Purpose | Notes |
|---|---|---|
| `APP_VERSION` | Single source of truth for the version string | Read by the title, the icon-bar label, and the export payload. Never hand-edit any of the three. |
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

**Baked-in baseline:** 15-Aug-2026 P6 export, 159 tasks / 198 milestones, embedded in the file.

## State Model

Three layers, kept strictly separate. Display state must never mutate schedule data.

1. **Schedule data** — the baked-in baseline, or an import overlaying it. An import does not touch the baseline.
2. **Annotation layer** — health overrides, progress overrides, comments, short titles, row remarks. Exported.
3. **Display state** — column visibility, text scale multipliers, dependency line visibility and thickness, filters, theme. Session-scoped. Not exported except dependency visibility.

Export is currently one-directional. There is no import path that reads the JSON payload back in. Round-trip is FEAT-13, new work, not a bug fix.

## Panel Systems

Three distinct systems. Do not conflate them.

| Panel | Element | Toggle | Scope |
|---|---|---|---|
| Style / Customize View | `#filter-bar`, left docked sidebar | Palette icon | Layout, field visibility, label text sizing, dependency line visibility/thickness |
| Top filter bar | `#top-filter-bar`, collapsible horizontal bar | Magnifying glass | Row filtering: Title contains, Banding, Source, Activity ID(s), Week range, Date range. The Source group hides itself while only one schedule is mounted, since a filter that can only mean "all" is noise. |
| Settings / Data Settings | `#settings-drawer`, right docked overlay | Gear | Four tabs: Sources (what is mounted), Import (the setup stepper), Defaults (settings that outlive an import), Diagnostics. Publish and the exports live in a sticky action footer reachable from every tab. |

Plus the sticky-corner quick search in the top-left sticky table cell, two-way synced with the Top Filter Bar Title field.

The Customize sidebar docks via a `body.cv-open{margin-left:300px}` class toggle rather than a DOM restructure, because `position:fixed` overlays (the sidebar included) are unaffected by an ancestor's margin. That is what lets it dock without disturbing the rest of the page.

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
| SheetJS on-demand from CDN | Inline the library; drop `.xlsx` support | Keeps the file small for the majority path. `.xlsx` users are on a corporate network with CDN access. | Pre-migration |
| `scheduleRerender()` debounce over incremental DOM diffing | Virtual DOM; targeted patching | Debounce fixed the reported slowdown at a fraction of the complexity and risk. Revisit only if it resurfaces. | Pre-migration |
| Label collision: 3-band cycling, same-row only | General N-marker collision solver | Covers the common case. A 4+ marker cluster in a very tight span can still partially overlap — an explicit, acknowledged scope boundary. | Pre-migration |
| Exact-match header aliases, not fuzzy | Fuzzy/levenshtein matching | Primary `Start`/`Finish` already cover the core need. Fuzzy risks silent mis-mapping, which is worse than a visible failure. | Pre-migration |
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
| A row grows when its densest proximity run reaches the band count | Grow on total marker count; grow on visible markers only; a fixed pixel threshold | Three is where every band is in use and the labels stack hard against each other, so the threshold is MS_LEVEL_CYCLE.length rather than a number chosen. Total count would grow rows whose markers are spread across the board and never collide. Visible-marker growth would match what a filtered screenshot shows, at the cost of row heights changing on every filter pass; recorded as the open alternative in TD-153. | 2026-09-22 |
| The exported CSV separates the schedule's own values from what was entered | Keep the effective value (as before); export two files; add a provenance column per field | One file with two named blocks is what a reader can sort and filter in a spreadsheet. The effective value is the defect: a report that cannot tell a schedule figure from a typed one is the wrong report to send. A provenance column per field doubles the width for information that block position already carries. | 2026-09-22 |
| A control that cannot act is disabled AND made unhittable, not just dimmed | Dim it only; hide it entirely; leave it live and let it scale invisible text | Dimming alone still lets the control be dragged, which is the state it was already in when it read as broken. Hiding it makes the panel jump as toggles flip and removes the affordance that says the setting exists. `disabled` is the real barrier, but it is invisible to any test that can be written, so `pointer-events:none` sits beside it: a second barrier that a hit test can actually measure. The row keeps its own pointer events so the tooltip still explains why. | 2026-09-22 |
| The baseline overlay toggle lives beside the View toggle, and the action bar above the tabs | Leave both where they were; duplicate the baseline toggle into the heading; keep the action bar sticky and offset it against the drawer header | A control belongs next to the thing it depends on: the overlay only means anything in the Update view. A duplicate would need a second writer or a sync between two copies, which is the drift shape this file has paid for four times. The action bar sat below the tables that feed it, so the drawer read machinery first and outcome last; above the tabs it is the first thing seen, and it stops being sticky because `.sd-hd` already occupies `top:0` and there is no measured header height to offset a second sticky element against. | 2026-09-22 |
| The filter row is two containers that wrap as whole columns | One wrapping row (as before); a fixed two-column grid; a media query breakpoint | One row gives a continuum of shapes, most of which break a label away from its control. A fixed grid cannot collapse at phone width. A media query puts the break at a width someone typed rather than where the content stops fitting. A flex basis gives exactly two shapes, and the check asserts it is in one of them rather than asserting which. | 2026-09-22 |
| Stable filename + git tags for versioning | Keep versioned filenames | Versioned filenames make every change a whole-file add, defeating the point of migrating to git. | 2026-09-09 |

---
**Rules:**
- Amend on architecture-impacting changes only.
- If a backlog item conflicts with a decision here, flag it before building.

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
| `--hdr-phase-h` | `#phase-hdr`'s row height | `tr.hdr-wk th { top }` |
| `--tfb-h` | `#top-filter-bar`'s content height | `#top-filter-bar.open { max-height }` |

Three rules that are load-bearing here:

- **Observers, not hooks.** The alternative was hooks in `rerender()`, `applyRowHeight()`, `togglePrintMode()`, `fitToScreen()` and a window resize listener. Five entry points, and a missed entry point has cost this project a cycle four times. An observer has no call sites to forget. Both observed elements survive rerenders: `renderPhaseHdr()` appends cells to the same `<tr>` rather than replacing it.
- **Measure the row, not a cell.** The month row's metadata cells carry `padding:0` and its month cells 3px, so a single `<th>` is shorter than the row and the week band would stick too high.
- **The filter bar's cap over-estimates on purpose.** `scrollHeight` is read from whichever state the bar is in, and while it is closed its vertical padding has transitioned away, so an exact figure taken then would be short by that padding and clip on the way back open. A `max-height` that overshoots costs nothing visible; it is a cap, not a height.

Both literals these replaced were wrong and had been for some time: the week band sat 3.5px below a 16px row, and the filter bar's 160px cap cut 43px off its own content at phone width.
