# P6 Milestone Dashboard — Project Context

Application name in-app: **Schedule Reporting and Evaluation Tool (SRET)**
Instance: Eskay Creek PFS Deliverable Milestone Dashboard

## 1. Baseline (Phase 1)

- **Problem statement (why):** P6 schedule exports are not a review or reporting instrument. Deliverable end dates sit buried in a 190+ row activity list, with no week-by-week visual, no deliverable-level aggregation, and no way for the study coordinator or discipline leads to annotate status, health, or remarks without editing the schedule itself. Manual re-plotting each weekly update cycle is slow and error prone.
- **Objective (what):** A single, self-contained HTML dashboard that ingests a P6 export (or its own baked-in baseline) and renders every activity end date as a milestone marker on a week-by-week timeline, with rows aggregated by schedule hierarchy, plus persistent user annotation and export. Reporting/review tool only — it never writes back to P6.
- **Description (how):** One HTML file, no build step, no framework, no runtime dependencies except an on-demand CDN load of SheetJS for `.xlsx` import. Loads a baked-in baseline on open so it is useful with zero setup. Live schedule updates overlay the baseline without mutating baseline data. Extensive display controls held in session state, never written back into the schedule model. Exports full JSON model or status/remarks CSV.
- **Phasing/timeline (when):**
  - Phase 1: Chat-based development to v3.1.0-P1 — **Done** (claude.ai, closed out 2026-09-09)
  - Phase 2: Migration to git repository, project kit established — **In progress** (this session)
  - Phase 3: Tokenization completion (colour/spacing/text retrofit across whole file) — **Not started**
  - Phase 4: Banding / row-collections (user-reorderable custom grouping) — **Not started**, Phase 1 auto-derivation not begun
  - Phase 5: Sorting + per-type icon customisation — **Not started** (labelled "Future" in-app)

## 2. Owner / Access

- **User:** Matthew Garrett — Engineering Technical Lead / Study Coordinator, Ausenco Engineering Canada Inc.
- **Project:** Eskay Creek 2026 Pre-Feasibility Study, Study No. 103787-13, client Skeena Gold & Silver Ltd. Integrates Snip and Albino satellite deposit ore into the existing Eskay Creek processing plant.
- **Repo:** `MattGestic/MyActivities`
- **Branch (this app's main):** `p6-milestone-dashboard` — orphan branch, no shared history with `main`. Other independent apps in this repo use their own branch as their main.
- **Working file:** `Projects/P6-Milestone-Dashboard/src/milestone-dashboard.html`
- **Hosting:** None. Local file, opened directly in a browser. No server, no deploy target.
- **Current live URL:** N/A — distributed as a file.

## 3. Architecture Decisions Made

| Decision | Rationale | Date |
|---|---|---|
| Single self-contained HTML file, no build step | Must be openable by anyone on the study team from a file share or email with zero tooling. Corporate SOE has no Node. | Pre-migration |
| Vanilla JS, one `<script>` block, no modules/bundler | Follows directly from no-build-step. Section comments only, not enforced boundaries. | Pre-migration |
| SheetJS loaded on demand from CDN, only for `.xlsx` | Avoids a multi-hundred-KB inline payload for a path many users never take. Paste/CSV import works fully offline. | Pre-migration |
| `APP_VERSION` as single source of truth for version string | Three independent copies (title, icon-bar label, export payload) had already drifted once. | Pre-migration |
| Tokenized design system (colour/spacing/text) over ad hoc styling | Incremental, deliberate initiative. Not finished — see §4 and Token Migration Log. | Pre-migration |
| `body.cv-open{margin-left:300px}` class toggle for sidebar dock, not DOM restructure | `position:fixed` overlays are unaffected by an ancestor margin, so the sidebar docks without touching page layout. | Pre-migration |
| `scheduleRerender()` 40ms debounce wrapper over `rerender()` | Rapid UI interactions each triggered an independent full DOM rebuild with no cancellation. User-reported slowdown, confirmed fixed. | Pre-migration |
| Orphan branch per app in shared repo | Apps are independent; a shared `main` would mix unrelated trees and make every diff noisy. | 2026-09-09 |
| Stable filename `src/milestone-dashboard.html`, version in git tags + `releases/` snapshots | Versioned filenames defeat git diffing, which is the entire reason for migrating. `APP_VERSION` still carries the version string. | 2026-09-09 |

## 4. Style / Constraints

**Hard stack constraints**
- No npm, no build step, no bundler, no framework.
- Single HTML file. No external assets except the SheetJS CDN load.
- No write-back to P6 under any circumstance. Read and render only.

**Text/output conventions**
- No em dashes and no AI-associated punctuation patterns in any user-facing or client-facing text the tool produces.

**Marker/text colour convention (annotation state, distinct from dashboard status colours)**
- Red = new/draft
- Yellow highlight = carried over from prior period
- Black = confirmed

**Design tokens** — defined in a theme-independent `:root{}` plus `html[data-theme="light"]` / `html[data-theme="dark"]` blocks.
- Colour: roughly 50/50 tokenized vs still-hardcoded hex as of last audit, improving pass by pass.
- Spacing: `--space-0` through `--space-7` (0-24px), derived from values already predominant in the file.
- Text: `--text-xs/sm/base/md/lg` (9-14px).
- Buttons: full primary/secondary system (`--color-btn-primary-bg/text/outline/hover-bg/pressed-bg` and secondary equivalents), plus a separate `--color-btn-icon-hover-bg/pressed-bg` pair because the icon bar's own background changes between themes.
- Label scale: three independent user multipliers `--label-scale`, `--title-scale`, `--hrs-scale`, layered over column-width-responsive `clamp()` sizing.

**No invented values without cause.** Every token added so far was derived from what the file already predominantly used. Before adding a new value, check what is already close.

## 5. What NOT to Change

- `APP_VERSION` is the only place the version is written. Never hand-edit the title, icon-bar label, or export payload version independently.
- `.m-lbl-stack` must remain a genuine DOM child of `.m-wrap`, not a sibling in the table cell. CSS positioning anchors to the icon, not the much wider week cell.
- `drawDepLines()` is the single choke point for dependency rendering. Its defensive reset of SVG layer visibility and stuck slider-drag state on every run is load-bearing — a prior bug left the layer permanently invisible after an interrupted drag/release. Preserve the pattern; do not patch individual callers instead.
- The Activity ID autocomplete dropdown uses `onmousedown` with `event.preventDefault()`. This is load-bearing. Removing it silently reintroduces a focus-stealing bug where the cursor jumps to the start of the field (mousedown on a non-focusable element blurs the focused input before any click handler runs).
- New code needing a rebuild after a user action calls `scheduleRerender(true)`, **not** `rerender(true)`. All 5 existing call sites were checked — none need synchronous DOM.
- Sticky corner search box and Top Filter Bar Title field are two-way synced. Do not let them drift apart.
- The three panel systems (Style/Customize sidebar, Top filter bar, Settings drawer) are distinct. Do not conflate them.
- Display state never mutates schedule data. Overrides and annotations are a separate layer.

## 6. Future Phases (not started)

- Tokenization retrofit across the whole file (spacing/text tokens currently applied only to recently touched components).
- Banding / row-collections: fully specced user-reorderable custom grouping to replace the fixed phase-band system. Phase 1 (auto-derivation) not started.
- Sorting and per-type icon customisation — labelled "Future" in the UI, genuinely not built.
- Import path for the exported JSON model (restore-from-export). Export is currently one-directional by design; this would be new work, not a bug fix.
- Multi-line short-title vertical bleed into neighbouring rows (label collision handles same-row only).

## 7. Related but separate — do not conflate

- **P8010 structural steel dashboard** (Ocean Steel, Aconex, COR/PCO workflow) — shares some heritage, different file, different data, different contract. Covered by its own skill.
- **`EPCM_Schedule_Dashboard_v1.html`** — deliberately unmaintained since early in the project under a single-template decision. Do not assume parity with the PFS file.

---
*Last updated: 2026-09-09 — migration from claude.ai chat development to git repository.*
