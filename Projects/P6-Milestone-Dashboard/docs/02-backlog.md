# P6 Milestone Dashboard — Backlog

Hierarchy: **EPIC** → **FEATURE** → **TASK/STORY**. Scoring is Impact vs Complexity at Feature level only; Epics roll up.

Status baseline is the delivered v3.1.0-P1 build. Features marked `Published` were confirmed present by the pre-handoff regression audit (TEST-01) and are not to be re-verified from scratch.

## Epics

| ID | Epic | Features | Status |
|---|---|---|---|
| EPIC-01 | Schedule ingest and data model | FEAT-01, FEAT-02, FEAT-09 | 3/3 published |
| EPIC-02 | Timeline rendering | FEAT-03, FEAT-04 | 2/2 published |
| EPIC-03 | Annotation and assessment | FEAT-05 | 1/1 published |
| EPIC-04 | Filtering and view control | FEAT-06, FEAT-07 | 2/2 published |
| EPIC-05 | Export and round-trip | FEAT-08, FEAT-13 | 1/2 published |
| EPIC-06 | Design system tokenization | FEAT-14 | 0/1 published |
| EPIC-07 | Grouping and presentation (future) | FEAT-10, FEAT-11 | 0/2 published |
| EPIC-08 | Repository and delivery | FEAT-12, FEAT-15 | 1/2 published |

## Features

| ID | Epic | Feature | Linked US | Impact | Complexity | Status | Notes |
|---|---|---|---|---|---|---|---|
| FEAT-01 | EPIC-01 | Baked-in baseline schedule | US-01 | H | L | Published | 15-Aug-2026 P6 export, 159 tasks / 198 milestones. |
| FEAT-02 | EPIC-01 | Live schedule import (xlsx / paste / delimited) | US-02, US-03, US-04 | H | H | Published | `Parse.workbook()` / `Parse.delimited()`, `INGEST_CONFIG.headerAliases`, leaf/group hierarchy detection, `classify()`/`aggregate()`. |
| FEAT-03 | EPIC-02 | Week-grid milestone rendering + collision bands | US-05, US-06 | H | H | Published | 3-band cycling, scoped to same-row common case. |
| FEAT-04 | EPIC-02 | Dependency line system | US-07 | M | H | Published | `drawDepLines()` single choke point with defensive reset. |
| FEAT-05 | EPIC-03 | Milestone dialog: health override, short title, comment | US-08, US-09 | H | M | Published | 5-state health override, comment autosave, actualised-date shading. |
| FEAT-06 | EPIC-04 | Row filtering (title, banding, Activity ID, week range) | US-10, US-11, US-12 | H | M | Published | Includes synced sticky-corner search and Activity ID autocomplete. |
| FEAT-07 | EPIC-04 | Customize View sidebar (columns, text scale, fit) | US-13, US-14 | H | M | Published | 3 independent scale sliders, deliberately not merged. |
| FEAT-08 | EPIC-05 | Export: full JSON model + status/remarks CSV | US-15 | H | M | Published | JSON payload includes dep visibility, health overrides, comments, short titles. |
| FEAT-09 | EPIC-01 | Ingest diagnostics panel | US-17 | M | L | Published | Collapsible, hidden entirely when empty. |
| FEAT-10 | EPIC-07 | Banding / row-collections (user-reorderable grouping) | US-18 | M | H | Not started | Fully specced. Phase 1 auto-derivation not begun. Assume none of it exists. |
| FEAT-11 | EPIC-07 | Row sorting + per-type icon customisation | US-19 | L | M | Not started | Labelled "Future" in the UI. Genuinely not built, not partially built. |
| FEAT-12 | EPIC-08 | Single-file zero-dependency distribution | US-20 | H | L | Published | Constraint, not a feature to be traded away. |
| FEAT-13 | EPIC-05 | Import previously exported JSON model (round-trip) | US-16 | M | M | Not started | Export is one-directional by design today. This is new work, not a bug fix. |
| FEAT-14 | EPIC-06 | Tokenization retrofit (colour / spacing / text) | — | M | M | Dev | Colour approx 50/50 tokenized. Spacing/text tokens applied to recently touched components only. Follow the Token Migration Log methodology, do not restart. |
| FEAT-15 | EPIC-08 | Git repository migration + project kit | — | H | L | Dev | This session. Orphan branch `p6-milestone-dashboard` as the app's main. |

## Tasks

| ID | Parent | Task | Status | Notes |
|---|---|---|---|---|
| TASK-01 | FEAT-15 | Create orphan branch, project skeleton, migrate v3.1.0-P1 file, schedule sample and handoff doc | Done | 2026-09-09 |
| TASK-02 | FEAT-15 | Write six-file project kit back-derived from the delivered build | Done | 2026-09-09 |
| TASK-03 | FEAT-15 | Add project `CLAUDE.md` so future sessions inherit the constraints without re-reading the handoff | Done | 2026-09-09 |
| TASK-04 | FEAT-15 | Migrate the companion docs (`Token_Migration_Log.md`, `Tokenization_Path_Plan.md`, `Hardcoded_Colour_Audit.csv`) into `docs/` | Open | Referenced by the handoff but not supplied with it. Needed before FEAT-14 continues. |
| TASK-05 | FEAT-14 | Retrofit `--space-0..7` across older CSS still using raw pixel values | Open | Check what is already close before adding any new value. |
| TASK-06 | FEAT-14 | Continue colour tokenization pass, role before value | Open | Near-identical hexes may be genuinely different semantic states. See the log for why some were deliberately kept separate. |
| TASK-07 | FEAT-02 | Decide whether `headerAliases` should move from exact-match to fuzzy | Open | Accepted gap today. `"BL1 Start"` will not match a `"bl start"` alias. Primary `Start`/`Finish` cover the core need. |
| TASK-08 | FEAT-03 | Multi-line short-title vertical bleed into neighbouring rows | Open | Separate, smaller problem than the same-row collision system. |
| TASK-09 | FEAT-10 | Banding Phase 1: auto-derivation of row collections | Open | Blocked on FEAT-10 go-ahead. |

---
**Rules:**
- Backlog is Epic/Feature/Task level. Standalone bugs and short-lived next actions go in `03-todo.md`.
- Status changes update the row in place. Never renumber existing IDs.
- Do not duplicate an item that already exists under another ID — update it.
