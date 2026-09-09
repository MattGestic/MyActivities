# Handoff — Eskay Creek PFS Deliverable Milestone Dashboard

**For:** Claude Code (migrating from a claude.ai chat-based development session)
**Current file:** `Eskay_Creek_PFS_Deliverable_Milestone_Dashboard_v3_1_0.html`
**Current version string:** `v3.1.0-P1` (see `APP_VERSION` constant near the top of the `<script>` block — single source of truth, do not hand-edit the title/label separately)
**Companion docs:** `Token_Migration_Log.md` (colour/spacing/text tokenization progress and rationale), `Tokenization_Path_Plan.md`, `Hardcoded_Colour_Audit.csv`

This document was written after an explicit audit of the current file against everything built across the full development history — confirmed present and working, not assumed. See the **Regression Audit** section at the end for what was checked and how.

---

## 1. Project context

**Owner:** Matthew Garrett, Engineering Technical Lead / Study Coordinator, Ausenco Engineering Canada Inc.
**Project:** Eskay Creek 2026 Pre-Feasibility Study (PFS) — Study No. 103787-13, for client Skeena Gold & Silver Ltd. The study integrates ore from the Snip and Albino satellite deposits into the existing Eskay Creek processing plant.
**This tool's role:** A single-file, self-contained HTML dashboard that ingests P6 schedule exports (or the project's own embedded baseline) and renders every activity's end date as a milestone marker on a week-by-week timeline, with deliverable rows aggregated by schedule hierarchy. It is a reporting/review tool, not a scheduling tool — it never writes back to P6.

**Separate, related but NOT the same thing:** there is a parallel EPCM/P8010 structural-steel dashboard (Ocean Steel, Aconex, COR/PCO workflow) that shares some heritage but is a different file, different data, different contract. Also a `EPCM_Schedule_Dashboard_v1.html` exists but has been explicitly left unmaintained since early in the project (a deliberate "single-template" decision) — don't assume parity between it and the PFS file.

---

## 2. Objective

Keep the PFS dashboard as a **single, self-contained HTML file** (no build step, no external dependencies except an on-demand CDN load of a spreadsheet-parsing library for `.xlsx` import) that:

1. Loads a baked-in baseline schedule on open (currently the 15-Aug-2026 P6 export, 159 tasks / 198 milestones), with no import required to see something useful.
2. Lets the user import a live P6 schedule update (file upload or paste) that overlays/replaces the baseline view without touching the baseline data itself.
3. Gives the user extensive, persistent-within-session display controls (column visibility, label text sizing, dependency-line visibility, milestone health overrides, etc.) without ever mutating the underlying schedule data.
4. Exports either a full JSON model (including all user annotations) or a status/remarks CSV.

The project has been moving, deliberately and incrementally, toward a **tokenized design system** (colour, spacing, text) rather than ad hoc styling — this is an explicit, ongoing initiative, not finished. See §4 and the Token Migration Log.

---

## 3. Established parameters & conventions

These are conventions the user has explicitly set and expects maintained, not just implementation details:

- **No em dashes, no AI-associated punctuation patterns** in any user-facing or client-facing text this tool produces.
- **Colour convention on markers/text:** red = new/draft, yellow highlight = carried over from prior period, black = confirmed. This is separate from the dashboard's own status colours (see §4).
- **Versioning:** `Major.Minor.Patch-PartialLetter/Number` (e.g. `3.1.0-P1`). Partials accumulate under a minor version; when a batch of real work has accumulated, bump the minor and reset partials — this does **not** require explicit user confirmation. Bumping the **major** version does require explicit confirmation. The version lives in exactly one place (`APP_VERSION`) and is read everywhere else (title, icon-bar label, export payload) — never hand-edit any of the three copies independently again.
- **No invented values without cause.** Every spacing/colour/text token added so far was derived from what the file already predominantly used, not picked arbitrarily. Continue that discipline — if a new value is needed, check what's already close before adding a new one.
- **Every UI state change should be genuinely verified, not assumed correct from reading the code.** This file has a real history of computed-style-vs-visual-appearance mismatches and CSS-specificity conflicts that looked fine on paper and weren't. Test interactions, don't just review the diff.

---

## 4. Architecture

### 4.1 File structure
Single HTML file. Roughly:
- `<style>` block: all CSS, including the token definitions (see below), organized loosely by component.
- Body: header/title/stats row, the three panel systems (see §4.3), the scrollable table (`#scroll-wrap` → `<table>` → sticky `<thead>` rows → `<tbody id="tbody">`), the milestone dialog, the Settings drawer, the Style/Customize sidebar.
- `<script>` block: everything else. No modules, no bundler — one large script, organized by section comments (`// === TIMELINE ===` etc., though these comments are not rigorously maintained as true section boundaries).

### 4.2 Token system (in progress, not complete)
Defined in a theme-independent `:root{}` block plus two theme-scoped blocks (`html[data-theme="light"]` / `html[data-theme="dark"]`).

- **Colour**: partially tokenized. Real, measured numbers as of the last audit: colour usage split roughly 50/50 tokenized vs. still-hardcoded hex, and that ratio has been improving pass by pass (see Token Migration Log for the full history of what's been consolidated and why some near-identical colours were deliberately kept separate — several "looked the same" clusters turned out to be genuinely different semantic states, e.g. a pale-red error tint vs. a pale-purple accent tint that happened to be visually close).
- **Spacing**: `--space-0` through `--space-7` (0–24px), built from what the file already mostly used rather than invented fresh. Applied to newer components (top filter bar, Customize View panel, milestone dialog); **not yet retrofitted across the whole file** — most older CSS still uses raw pixel values.
- **Text**: `--text-xs/sm/base/md/lg` (9–14px). Same status — applied where recently touched, not retrofitted everywhere.
- **Button states**: full primary/secondary system — `--color-btn-primary-bg/text/outline/hover-bg/pressed-bg` and the same five for `secondary`, plus a separate `--color-btn-icon-hover-bg/pressed-bg` pair specifically because the icon-bar's background itself changes between light/dark themes in a way a shared hover token couldn't handle correctly.
- **On-board label text scale**: three independent user-adjustable multipliers — `--label-scale`, `--title-scale`, `--hrs-scale` — layered on top of the existing column-width-responsive `clamp()` sizing for the type-code label, the short-title, and the hours text respectively. These were originally one shared slider; split into three by explicit request.

**If continuing the tokenization work:** the Token Migration Log documents the methodology that's worked (check actual CSS property/role before merging two colours just because the hex is close; role matters more than value) and should be followed, not restarted from scratch.

### 4.3 The three panel systems — do not conflate these
1. **Style/Customize View** (`#filter-bar`, left docked sidebar, toggled by the palette icon in the sticky corner). Controls layout, field visibility, label text sizing, dependency line visibility/thickness. Docked via a `body.cv-open{margin-left:300px}` class toggle — deliberately *not* a DOM restructure, because `position:fixed` overlay elements (this sidebar included) are unaffected by an ancestor's margin, which is what makes this technique work without touching the rest of the page's layout.
2. **Top filter bar** (`#top-filter-bar`, collapsible horizontal bar under the header, toggled by the magnifying-glass icon). Row filtering: Title contains, Banding, Activity ID(s) (with a custom autocomplete/multi-select dropdown — see §4.5), Week range.
3. **Settings / Data Settings drawer** (`#settings-drawer`, right-docked overlay, gear icon). Actions (export, clear comments), Currently Imported Schedule status, Import (collapsible, nested "1. Import a Schedule" → "2. Map columns" → Advanced Input Settings → confirm button, in that order), Diagnostics (collapsible, hidden entirely when empty).

There is also a **sticky-corner quick search box** (in the top-left sticky table cell, replacing what was originally just a plain "Deliverable" label) — a lightweight, always-visible title-search input kept in two-way sync with the Top Filter Bar's own Title field. Don't let these drift apart if either is touched.

### 4.4 Rendering pipeline
`rerender(overrides)` is the core rebuild function: teardown → rebuild phase/week headers → rebuild every row and marker → reapply persisted display state → redraw dependency lines → update summary/diagnostics. It is expensive (full DOM rebuild) and is now **debounced** via `scheduleRerender()` — a 40ms coalescing wrapper added specifically because multiple rapid UI interactions were each triggering a full independent rebuild with no cancellation, causing a real, user-reported slowdown. **New code that needs a rebuild after a user action should call `scheduleRerender(true)`, not `rerender(true)` directly**, unless it genuinely needs the DOM to be synchronously up to date immediately afterward (checked: none of the current 5 call sites do).

Markers are positioned via `.m-wrap` (icon) with the label stack (`.m-lbl-stack`) as a genuine DOM **child** of `.m-wrap` (not a sibling in the table cell) — this was a deliberate fix so CSS positioning anchors to the icon itself, not the whole (much wider) week cell. A same-row label-collision system nudges markers into one of three vertical bands (mid / top-quarter / base, cycling) when several land within ~4 columns of each other — deliberately scoped to the common case, not a fully general N-marker collision solver (a 4+ marker cluster within a very tight span can still partially overlap; this was an explicit, acknowledged scope boundary, not an oversight).

Dependency lines are drawn by `drawDepLines()`, which is the **single choke point** everything routes through — it defensively resets the SVG layer's visibility and clears any stuck slider-drag state every time it runs, specifically because a previous bug let the layer get stuck invisible if a drag/release pairing was ever interrupted, making every subsequent toggle look broken even though it was working correctly underneath. If you touch dependency rendering, preserve this "defensive reset at the one real entry point" pattern rather than patching individual callers.

### 4.5 Ingest pipeline
`Parse.workbook()` / `Parse.delimited()` → header auto-detection via `INGEST_CONFIG.headerAliases` (**exact match after normalization, not fuzzy** — e.g. `"BL1 Start"` will not match a `"bl start"` alias; this is a known, accepted gap since the primary `Start`/`Finish` columns already cover the core need) → hierarchy detection via a leaf/group pattern (`/^\S*\d\S*$/` — no whitespace + contains a digit = leaf activity; anything else = group/band header) → `classify()`/`aggregate()` build the milestone list → `renderRows()` displays it.

Date parsing (`parseLooseDate()`) explicitly handles P6's `dd-MMM-yy` format with an actual-date suffix (` A`) and a starred/constrained-date suffix (`*`) — both confirmed working against a real EPCM-style export reviewed mid-project.

The Activity ID filter field has a custom autocomplete: a plain text input (so paste-a-comma-list-from-elsewhere still works unmodified) with a dropdown overlay that filters against whatever's after the *last* comma and appends on click. Note: clicking a dropdown item uses `onmousedown` with `event.preventDefault()` — this is load-bearing, not incidental. Removing it will silently reintroduce a focus-stealing bug where the text cursor jumps to the start of the field after a click (a real, confirmed browser behaviour: mousedown on a non-focusable element blurs the currently-focused input before a click handler can react).

### 4.6 State that is NOT currently exported (flagged, not yet decided on)
`exportModel()`'s JSON payload includes dependency visibility, milestone health overrides, milestone comments, and milestone short titles (added recently — previously it only included row-level health/remarks overrides, which was a real gap). There is currently **no import path that reads this payload back in** — export is one-directional. If a "restore from exported JSON" feature is ever wanted, that's new work, not a bug fix.

---

## 5. Known limitations / open items (explicitly acknowledged, not hidden gaps)

- **Label collision avoidance** only handles the same-row case; wrapped multi-line short-titles bleeding vertically into a neighbouring row is a separate, smaller, not-yet-addressed problem.
- **A blank Data-date/Report-date bug** was reported against a real `.xlsx` file import. It could not be reproduced via paste-import (tried twice, including the user's exact field-editing sequence) or via static code review — the construction logic looks correct. A defensive fallback ("not set" instead of a bare blank) was added, but the actual root cause is unconfirmed. If it recurs, the triggering file itself will be needed to diagnose properly.
- **Banding / row-collections** (a spec for user-reorderable custom grouping, replacing the current fixed phase-band system) is fully designed but Phase 1 (auto-derivation) has not been started. Don't assume any of it exists.
- **Sorting and per-type icon customisation** are labeled "Future" in the UI itself — genuinely not built, not partially built.
- **Spacing/text tokens** are applied to recently-touched components only, not retrofitted across the whole file (see §4.2).
- **Column header auto-mapping** is exact-match, not fuzzy (see §4.5) — a real, accepted gap, not an oversight.

---

## 6. Regression audit (performed for this handoff)

Given the length of this project's history, the current file was directly checked — not assumed — against every major feature built, immediately before writing this document:

| Area | Checked | Result |
|---|---|---|
| Version single-source-of-truth | `APP_VERSION` constant present and consistent | ✅ `3.1.0-P1` |
| Colour token system | Primary/secondary button tokens, accent/crit tint tokens, row/badge tokens | ✅ present |
| Spacing/text tokens | `--space-0..7`, `--text-xs..lg` | ✅ present |
| Independent label-scale sliders | 3 separate controls (label/title/hrs) | ✅ present, not merged back into one |
| Milestone dialog | Header reorder, actualized-date green shading, 5-state health override, comment autosave | ✅ present |
| Dependency system | Redraw-on-rerender fix, All-on/off button state reflection, full export payload | ✅ present |
| Label collision avoidance | 3-band cycling system | ✅ present |
| Performance fix | `scheduleRerender()` debounce wrapper | ✅ present, wired to all 5 real call sites |
| Settings drawer reorg | Renamed titles, section order, collapsible Import/Diagnostics | ✅ present |
| Search/filter system | Sticky corner box, synced Title field, Activity ID autocomplete | ✅ present |
| Solid-fill icons | All 5 non-baseline states set to `filled` | ✅ present |
| Sticky header rows | Both phase-band and date rows pinned on vertical scroll | ✅ present |
| Fit to Screen | Column-width auto-fit function | ✅ present |
| Baseline data | 15-Aug-2026 source, 159 tasks / 198 milestones | ✅ present |
| Pre-history architecture | Dependency-line drawing, short-title core mechanism, start-date/actual/starred-date fallback handling | ✅ present |
| Banding spec | Confirmed still *not* implemented (correct — matches its documented Phase 1 status) | ✅ as expected |

No drops or regressions found. Nothing in this audit should be re-verified from scratch by Claude Code — treat the table above as ground truth as of this handoff, and focus verification effort on whatever new work is actually being done.

---

## 7. Working style notes for whoever picks this up

- The user reviews and approves direction before large structural changes are implemented, but expects concrete implementation (not just proposals) for well-scoped requests.
- Direct, fast-paced, precise. No filler, no restating what's about to be done — just do it.
- When something is ambiguous, state the interpretation being used and proceed, rather than blocking on a clarifying question, unless the ambiguity is severe enough that proceeding risks real wasted work.
- Claims of "fixed" or "working" should be backed by an actual test result (computed style check, DOM state check, before/after comparison), not a code read-through alone — this file's history includes several cases where code looked correct on inspection but had a real runtime bug (CSS specificity conflicts, browser focus-stealing behaviour, a stuck-hidden SVG layer) that only surfaced under actual interaction.
