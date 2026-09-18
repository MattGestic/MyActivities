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
2. **Annotation layer** — health overrides, comments, short titles, row remarks. Exported.
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
| Stable filename + git tags for versioning | Keep versioned filenames | Versioned filenames make every change a whole-file add, defeating the point of migrating to git. | 2026-09-09 |

---
**Rules:**
- Amend on architecture-impacting changes only.
- If a backlog item conflicts with a decision here, flag it before building.

### Marker placement (v3.1.0-P33)

Three rules, in order of how much they constrain everything else.

**1. A marker's vertical position is a property of the marker.** Every label is a child of `.m-wrap`, so it rides whatever the wrap does and always sits at its own icon's height. That is what makes a label traceable to the marker that owns it. There is exactly one vertical offset per marker and exactly one writer for it, `renderMarker()`.

**2. The anchor is the cell's true centre; every offset is pixels.** `.m-wrap` sits at `left:50%; top:50%`, which resolves against the cell's real padding box whatever height the row turns out to be. `--mdx`/`--mdy` are pixel offsets budgeted from `ROW_HEIGHT` and `COL_WIDTH`, which are minimums the rendered cell can only exceed. So an offset that fits the budget fits the cell, and the error direction is "used less room than was available", which is invisible. A percentage had the opposite direction, needed correcting against a height the render could not know, and grew the spread as the row got taller.

**3. Staggering is proximity-scoped.** A row's markers are walked in column order and cut into runs; a marker more than `MS_PROXIMITY_COLS` from the previous one starts a new run, and a run of one is dead centre. Four columns because that is about how wide a rendered label is, so a run is exactly the set whose labels can collide. Within a run: top/bottom for two, top/middle/bottom for three, and a triangle wave beyond, so the fourth is the middle band. A plain repeat would put markers one and four on the same line a few columns apart, which is the two-state trap this file has hit three times.

**Band reuse is legitimate across cells and illegitimate within one.** Markers sharing a cell share an x, so the band is all that separates them. A cell holding more than three grows *its* row via `--row-h-eff`, by the minimum that gives each of them a line. Data-driven, never display-driven: a denser import can change row heights, no toggle ever does.

**Labels never affect layout.** The band is budgeted on the icon, not on the label stack, so it cannot depend on whether labels are shown. The accepted consequence is that a label on a short row can overlap the gutter; it is bounded and clears once the row has room.

`msCellOffset()` is horizontal-only. Two vertical offsets would compound, which is the failure removed at P32 between the icon spread and the label band.

Anything `msCellOffset()` or the band reads (icon size, column width, row height) must flag `_placementNeedsRebuild`, because the offsets are written once at render time.

**Hidden markers are derived, never stored.** `markerHidden()` reads the row's `hidden-row` class and the cell's `data-col` against `DATE_RANGE_COLS`, so it costs no layout and cannot go stale. A stored flag would need writing at four entry points, and this file has three separate defects from a rule applied at some and not others.
