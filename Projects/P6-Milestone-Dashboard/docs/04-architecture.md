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
| Top filter bar | `#top-filter-bar`, collapsible horizontal bar | Magnifying glass | Row filtering: Title contains, Banding, Activity ID(s), Week range |
| Settings / Data Settings | `#settings-drawer`, right docked overlay | Gear | Actions, imported-schedule status, Import, Diagnostics |

Plus the sticky-corner quick search in the top-left sticky table cell, two-way synced with the Top Filter Bar Title field.

The Customize sidebar docks via a `body.cv-open{margin-left:300px}` class toggle rather than a DOM restructure, because `position:fixed` overlays (the sidebar included) are unaffected by an ancestor's margin. That is what lets it dock without disturbing the rest of the page.

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
| Print preview is a reversible mode, not a print action | A Print button calling `window.print()`; a permanent A3 `@page` rule; a separate print stylesheet only | Page fit is something to check and adjust before printing, not to discover in the print dialog. The `@page` rule is injected only while the mode is on, so a plain Ctrl+P is unaffected for anyone who did not ask for A3. The mode never travels into a published file. | 2026-09-15 |
| | The board's date range is derived from the imported data, not from a fixed window around the data date | Keep the 12-before / 26-after window; make the window bigger; ask at import | The board exists to show a schedule, so its span is a property of that schedule. The fixed window was wrong in both directions on the same file: three milestones past its end plotted nowhere while eight empty weeks sat before its start. The window survives only as the fallback for an import carrying no usable dates, which is the one case where there is nothing to derive from. | 2026-09-15 |
| The week filter marks; the date range filter narrows | Make both narrow; make both mark; one control with a mode | They answer different questions. "What is in week 12" wants the week marked in context, which is why painting its cells was reverted (TD-79). "Show me September to October" wants a September-to-October board. Both resolve to one [lo,hi] column pair, so there is a single definition of in-range and the two intersect rather than fight. | 2026-09-15 |
| Stable filename + git tags for versioning | Keep versioned filenames | Versioned filenames make every change a whole-file add, defeating the point of migrating to git. | 2026-09-09 |

---
**Rules:**
- Amend on architecture-impacting changes only.
- If a backlog item conflicts with a decision here, flag it before building.
