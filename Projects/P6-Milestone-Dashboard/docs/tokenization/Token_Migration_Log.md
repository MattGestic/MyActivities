# Design Token Status

**Purpose:** Current tokenization state of `Eskay_Creek_PFS_Deliverable_Milestone_Dashboard_v3_1_0.html`, for anyone deciding what to touch next.

**How to use this:** Before styling anything, check the component table below. If `Tokenized`, use its existing tokens. If `Partial` or `Not tokenized`, either token it properly as part of your change or leave it alone. For current counts, always read the bottom row of the Measurement Log per metric, never a number written into prose elsewhere in this file — prose here never states a count directly, only what a metric means and where to find it.

---

## Measurement Log

Append new rows here as measurements are taken. Never edit or delete a prior row — the log itself is the history; the last row per metric is the current figure.

| Date/Time (UTC) | Source | Metric | Value |
|---|---|---|---|
| 2026-09-09 21:15 | Audit script v1, regex vs. live file, excludes `:root`/theme-block token definitions | Hardcoded colour occurrences | 99 |
| 2026-09-09 21:15 | Audit script v1 | Distinct hardcoded colour values | 72 |
| 2026-09-09 21:15 | Audit script v1 | Colour occurrences matching an existing token exactly | ~24 |
| 2026-09-09 21:15 | Audit script v1 | `--space-*` token references in file | 57 |
| 2026-09-09 21:15 | Audit script v1 | Hardcoded padding/margin/gap declarations (px) | 117 |
| 2026-09-09 21:15 | Audit script v1 | `var(--text-*)` font-size references in file | 7 |
| 2026-09-09 21:15 | Audit script v1 | Hardcoded font-size declarations (px) | 101 |
| 2026-09-09 22:40 | Audit script v2 (`tools/colour_audit.py`, committed), full documented scope: hex **and** `rgb()`/`rgba()`, excludes all 4 token-definition blocks | Hardcoded colour occurrences | 131 |
| 2026-09-09 22:40 | Audit script v2 | Distinct hardcoded colour values | 93 |
| 2026-09-09 22:40 | Audit script v2 | Colour occurrences matching an existing token exactly | 28 |
| 2026-09-09 22:40 | Audit script v2, hex-only subset (v1-comparable scope) | Hardcoded colour occurrences | 99 |
| 2026-09-09 22:40 | Audit script v2, hex-only subset (v1-comparable scope) | Distinct hardcoded colour values | 72 |
| 2026-09-09 22:40 | Audit script v2, `rgb()`/`rgba()` only (the gap v1 never measured) | Hardcoded colour occurrences | 32 |
| 2026-09-09 22:40 | Audit script v2, `rgb()`/`rgba()` only | Distinct hardcoded colour values | 21 |
| 2026-09-09 22:40 | Audit script v2, `var(--space-N)` in consuming CSS only, definitions excluded | `--space-*` token references in file | 38 |
| 2026-09-09 22:40 | Audit script v2, includes sub-properties (`padding-left`, `margin-top`, ...) | Hardcoded padding/margin/gap declarations (px) | 173 |
| 2026-09-09 22:40 | Audit script v2, whole properties only (v1-comparable scope) | Hardcoded padding/margin/gap declarations (px) | 114 |
| 2026-09-09 22:40 | Audit script v2 | `var(--text-*)` font-size references in file | 7 |
| 2026-09-09 22:40 | Audit script v2 | Hardcoded font-size declarations (px) | 100 |

**Re-running the audit:** run `python3 tools/colour_audit.py` from the project root. It regenerates `Hardcoded_Colour_Audit.csv` and prints every metric above.

Method: regex-extract all `#hex` and `rgb()`/`rgba()` values from the `<style>` block, excluding the token-definition blocks (`:root{}` x2 and `html[data-theme=...]{}` x2 — **four blocks, not two**). Count occurrences and distinct values, cross-reference against defined token values. Same approach for `var(--space-*)`/`var(--text-*)` references vs. raw px in `padding`/`margin`/`gap`/`font-size`.

### v1 to v2 reconciliation (2026-09-09)

v2 was written independently from the documented method, then reconciled against v1's figures rather than either set being assumed correct. Every difference is explained. None is unexplained drift.

| Metric | v1 | v2 | Why they differ |
|---|---|---|---|
| Colour occurrences | 99 | 131 | **v1 counted hex only.** It never matched `rgb()`/`rgba()`, despite its own documented method saying it did. v2's hex-only subset reproduces 99 exactly. The 32 `rgba()` occurrences (21 distinct) were invisible to the plan. |
| Distinct colours | 72 | 93 | Same cause. v2 hex-only subset reproduces 72 exactly. |
| Colour matching a token | ~24 | 28 | Same cause. v2 hex-only subset reproduces 24 exactly. |
| `--space-*` references | 57 | 38 | **v1 counted the 18 definitions in `:root` as references.** 39 mentions in consuming CSS + 18 definitions = 57. True consumption is 38 `var(--space-N)` calls. |
| px padding/margin/gap | 117 | 173 | **v1 counted whole properties only**, missing `padding-left`, `margin-top` and similar. v2 restricted to whole properties gives 114 against v1's 117. |
| `var(--text-*)` references | 7 | 7 | Exact match. |
| px font-size | 101 | 100 | Off by one, within the noise of two independently written regexes. |

**Net effect: v1 systematically understated the remaining work** — on colour by excluding `rgba()`, and on spacing both by over-counting references and under-counting raw px. Plan against the v2 rows.

A defect found in v2 during this same run is recorded here rather than quietly fixed: its first version detected only 2 of the 4 token-definition blocks, because the block-matching regex required the selector to follow `}`, `,` or start-of-string, which neither the first theme block (preceded by a comment) nor the second `:root{}` rule does. Their contents were counted as hardcoded usage and inflated the colour occurrence count to 159. Fixed, with the reason recorded in the script so it is not reintroduced.

---

## Colour — by component

| Component | Status | Last confirmed |
|---|---|---|
| Theme architecture (light/dark) | Tokenized | 2026-09-09 |
| App header / icon bar | Tokenized | 2026-09-09 |
| Filter bars (top + sticky search) | Tokenized | 2026-09-09 |
| Button states (primary/secondary/icon, incl. hover/pressed) | Tokenized | 2026-09-09 |
| Milestone dialog | Tokenized | 2026-09-09 |
| Dependency lines | Tokenized | 2026-09-09 |
| Settings drawer / View Controls sidebar | Tokenized | 2026-09-09 |
| Board phase bands | Not tokenized — hardcoded hex per phase (`.pb0`–`.pb3`) | 2026-09-09 |
| Discipline band rows | Not tokenized | 2026-09-04 (not re-checked this pass) |
| Health dot colours | Partial — 4 of 5 states hardcoded, 1 (`mh-4`) tokenized | 2026-09-09 |
| Milestone marker icon states (DONE/TRACK/RISK/CRIT/FUTURE) | Not tokenized | 2026-09-04 (not re-checked this pass) |
| Subtotal row | Partial | 2026-09-04 (not re-checked this pass) |
| Remarks field states | Not tokenized | 2026-09-04 (not re-checked this pass) |

Update the status cell **and** the date together whenever a row is re-checked, whether or not the status changed — an unchanged status with a fresh date is still useful information (confirms it wasn't silently missed).

## Spacing & Text

| | Status | Last confirmed |
|---|---|---|
| `--space-0` through `--space-7` scale | Defined, applied to recently-built components only | 2026-09-09 |
| `--text-xs/sm/base/md/lg` scale | Defined, applied to recently-built components only | 2026-09-09 |
| Older/untouched components | Raw pixel values throughout | 2026-09-09 |

**Working convention:** any time a component is touched for another reason, bring its tokens up to date in the same pass, and log the measurement + status update here rather than only in memory of the change.
