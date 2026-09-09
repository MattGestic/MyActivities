# P6 Milestone Dashboard

**Schedule Reporting and Evaluation Tool (SRET)** — Eskay Creek PFS Deliverable Milestone Dashboard

A single, self-contained HTML dashboard that ingests P6 schedule exports and renders every activity end date as a milestone marker on a week-by-week timeline, with deliverable rows aggregated by schedule hierarchy.

Reporting and review tool only. It never writes back to P6.

**Project:** Eskay Creek 2026 Pre-Feasibility Study, Study No. 103787-13
**Client:** Skeena Gold & Silver Ltd. · **Owner:** Ausenco Engineering Canada Inc.
**Current version:** `3.1.0-P1` (see `docs/03-todo.md` TD-01 — version string needs confirming)

## Run it

Open `src/milestone-dashboard.html` in a browser. That is the whole procedure.

No install, no server, no build step. A baked-in baseline schedule (15-Aug-2026 P6 export, 159 tasks / 198 milestones) loads on open, so the file is useful with zero setup.

## Import a schedule update

Gear icon → Import → "1. Import a Schedule" → "2. Map columns" → confirm.

- **File upload** (`.xlsx`) — loads SheetJS from CDN on demand. Needs network access on first use.
- **Paste** (CSV / TSV / tab-delimited) — works fully offline.

Expected P6 export columns: `Activity ID`, `Activity Name`, `Duration`, `Start`, `Finish`, `Predecessor Details`, `Successor Details`, `Total Float`. Header auto-detection is exact-match after normalization; anything it misses can be mapped by hand in step 2.

Hierarchy comes from the Activity ID column: leading whitespace plus the leaf pattern (no whitespace, contains a digit) marks an activity; anything else is treated as a group/band header.

An import overlays the view. It does not modify the baked-in baseline.

A reference export is committed at `data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx` (data date 29-Aug-2026, 192 rows).

## Export

Gear icon → Actions.

- **JSON** — full model including dependency visibility, milestone health overrides, comments, short titles, and row-level health/remarks.
- **CSV** — status and remarks only.

Export is one-directional today. There is no import path that reads the JSON payload back in (`FEAT-13`, not built).

## Repository layout

```
Projects/P6-Milestone-Dashboard/
├── CLAUDE.md                Constraints for any dev session. Read first.
├── README.md                This file.
├── src/
│   └── milestone-dashboard.html      The application.
├── releases/                Point-in-time version snapshots.
├── data/schedules/          Reference P6 exports for ingest testing.
└── docs/
    ├── 00-project-context.md    Baseline, decisions, what not to change
    ├── 01-requirements.md       Personas, US-##, UX-##
    ├── 02-backlog.md            EPIC-## / FEAT-## / TASK-##
    ├── 03-todo.md               TD-## tactical items + current next task
    ├── 04-architecture.md       Runtime structure, data mapping, state model
    ├── 05-test-log.md           TEST-## / UT-##, acceptance, publish record
    └── handoff/                 Original chat-to-code handoff archive
```

## Branch model

This repository hosts several independent applications, each on its own **orphan branch** which acts as that application's main. Branches share no history, so an unrelated app never appears in this app's diffs.

This application's main branch is **`p6-milestone-dashboard`**. Do not merge it into any other branch.

The default branch `main-projects-hub` holds the repository index, the governing documents common to all projects, and the governed `Resources/` library. Repository-wide standards live there and are not restated here.

## Versioning

`Major.Minor.Patch-PartialLetter/Number`, e.g. `3.1.0-P1`.

The version lives in exactly one place: the `APP_VERSION` constant in `src/milestone-dashboard.html`. The page title, icon-bar label, and export payload all read from it. Never hand-edit any of those three.

The working file keeps a stable filename so git diffs stay readable. Shipped versions get a git tag and a snapshot in `releases/`.

## Constraints

- Single self-contained HTML file. No npm, no build step, no bundler, no framework.
- Only external dependency is the on-demand SheetJS CDN load for `.xlsx` import.
- No write-back to P6, ever.
- No em dashes or AI-associated punctuation patterns in any user-facing or client-facing string the tool produces.

## Known limitations

Acknowledged scope boundaries, not hidden gaps. Detail in `docs/02-backlog.md` and `docs/03-todo.md`.

- Label collision avoidance handles the same-row case only. A cluster of 4+ markers in a very tight span can still partially overlap. Multi-line short titles bleeding vertically into a neighbouring row is a separate, unaddressed problem.
- Column header auto-mapping is exact-match, not fuzzy. `"BL1 Start"` will not match a `"bl start"` alias.
- Spacing and text tokens are applied to recently touched components only, not retrofitted across the whole file. Colour is roughly half tokenized.
- Banding / row-collections (user-reorderable grouping) is fully specced but not started.
- Sorting and per-type icon customisation are labelled "Future" in the UI and are genuinely not built.
- A blank Data-date / Report-date on `.xlsx` import was reported pre-migration and could not be reproduced. A defensive fallback is in place; root cause unconfirmed.

## Not this project

- The **P8010 structural steel dashboard** (Ocean Steel, Aconex, COR/PCO workflow) shares some heritage but is a different file, different data, different contract.
- `EPCM_Schedule_Dashboard_v1.html` has been deliberately unmaintained since early in the project. Do not assume parity with this file.
