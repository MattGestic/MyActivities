# Design Token Status

**Purpose:** Current tokenization state of `src/milestone-dashboard.html`, for anyone deciding what to touch next.

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
| 2026-09-09 22:40 | Audit script v2, literals frozen at one theme's token value (excludes `var()` fallbacks) | Theme-blind colour occurrences | 19 |
| 2026-09-09 23:30 | Audit script v2, after the v3.1.0-P2 theme-blind pass | Hardcoded colour occurrences | 99 |
| 2026-09-09 23:30 | Audit script v2, after the v3.1.0-P2 theme-blind pass | Distinct hardcoded colour values | 73 |
| 2026-09-09 23:30 | Audit script v2, after the v3.1.0-P2 theme-blind pass | Colour occurrences matching an existing token exactly | 9 |
| 2026-09-09 23:30 | Audit script v2, after the v3.1.0-P2 theme-blind pass | Theme-blind colour occurrences | 0 |
| 2026-09-09 23:30 | `tools/theme_check.py`, computed styles in both themes | Probes expected to toggle, frozen | 0 |
| 2026-09-09 23:30 | `tools/theme_check.py` | Probes expected to toggle, toggling correctly | 16 |
| 2026-09-10 | Audit script v3, scope extended to inline `style=` attributes (TD-12) | Hardcoded colour occurrences | 100 |
| 2026-09-10 | Audit script v3, inline `style=` attributes only | Hardcoded colour occurrences | 1 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P3 board pass | Hardcoded colour occurrences | 54 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P3 board pass | Distinct hardcoded colour values | 43 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P3 board pass | Colour occurrences matching an existing token exactly | 10 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P3 board pass | Theme-blind colour occurrences | 0 |
| 2026-09-10 | `tools/theme_check.py`, board probes added | Probes expected to toggle | 33 |
| 2026-09-10 | `tools/theme_check.py` | Probes expected to toggle, frozen | 0 |
| 2026-09-10 | `tools/theme_check.py` | Probes expected to be constant, correctly frozen | 2 |
| 2026-09-10 | `tools/theme_check.py`, WCAG contrast of own text over own background, both themes | Probes below 3.0:1 | 0 |

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

### Board pass, v3.1.0-P3 (2026-09-10)

Tokenized the board interior: rows, columns, marker labels, icons and status.

**Icons now have a default token state each.** Icons paint from `currentColor`, so before this they inherited whatever the status text class set and could not be retuned without moving the text with them. Each state now has its own alias, resolving per theme because `:root` and the theme blocks both target `<html>`:

| Token | Defaults to |
|---|---|
| `--color-icon-done` | `--color-text-ink` |
| `--color-icon-track` | `--color-status-track` |
| `--color-icon-risk` | `--color-status-risk-fill` |
| `--color-icon-crit` | `--color-status-crit` |
| `--color-icon-future` | `--color-status-future` |
| `--color-icon-baseline` | `--color-text-note` |
| `--color-icon-na` | `--color-text-ink` |

Point one of these at a different value to restyle a single icon state without touching the status palette. This is the groundwork the "per-type icon customisation" future item needs.

**Per theme:** `--color-col-filtered-bg`, `--color-row-hover-bg`, `--color-subtotal-accent`.

**Constant by design, in the non-themed `:root`:** phase band fills `--color-band-1..5` plus `--color-band-divider`; accent washes (alpha over whatever is beneath, so one value is right in both themes); health dot fills and rims; shadows; the history bar gradient stop; and the marker label backings.

**A change measured, judged wrong, and reverted in the same pass.** The marker label backings were first split per theme, which made them toggle. The contrast check then measured dark-theme label text at **1.16:1 to 1.97:1**: the backings are stickers sitting over the board, and the label text colour was chosen against the sticker rather than against the page, so following the theme made them unreadable. They were moved back to constant. The original white backing was correct design, not a defect. This is the second time this pass that a "fix" would have broken working code, after the `var()` fallbacks in P2.

**Two additions to the tooling, both from things that nearly slipped through:**

- The audit now scans inline `style=` attributes as well as the `<style>` block (TD-12). It immediately found a theme-blind `#c00000` inside JS-generated diagnostics markup. The `source` column says which of the two a row came from.
- `theme_check.py` now measures WCAG contrast of each probe's own text over its own background in both themes, and fails below 3.0:1. A "does it toggle" check cannot see a text colour that changed in step with its background and stayed unreadable, which is exactly what the label backings did.

Contrast findings are judged on an element's **own** text nodes. An earlier version counted descendants and reported the sticky corner search cell at 1.00:1, which was a probe artifact: its visible glyphs are children carrying their own tokenized colours.

**Scope boundary:** colour only. Spacing and text tokens are still untouched, and colours with no token match outside the board were not triaged.

### Theme-blind pass, v3.1.0-P2 (2026-09-09)

A colour hardcoded to one theme's value renders correctly in that theme and wrong in the other. The audit gained a `toggle_verdict` column to name that class directly, and `tools/theme_check.py` now measures it from computed styles in both themes rather than from the CSS text.

What was fixed, all replaced with tokens that already existed per theme, none invented:

| Area | Was | Now |
|---|---|---|
| Sticky search icon, placeholder, clear | `#8ab`, the dark value | `--color-text-on-panel-muted` |
| View toggle border | `#4a5580` | `--color-vt-divider` |
| Column header gridline | `#2a2e50`, in the CSS rule **and** one inline style in markup | `--color-line-default` |
| Milestone status text | `#111` / `#1355c4` / `#c8c8c8` | `--color-text-ink` / `--color-status-track` / `--color-status-future` |
| History and subtotal week-column bands | `#252945` / `#3a2d5c` / `#3a3d70` / `#7050a8` | `--color-col-past-bg` / `--color-col-filtered-alt-bg` |
| Dependency tooltip and comment panel | near-white text and dark borders frozen at dark values | `--color-text-primary` / `--color-text-mono` / `--color-text-muted` / `--color-line-default` / `--color-line-hairline` / `--color-dialog-bg` |

Three roles are genuinely constant and were tokenized into the **non-themed** `:root` rather than being theme-scoped, because the saturated fill carries the meaning and the ink against it must stay dark in both themes: `--color-chip-attention-bg`, `--color-chip-attention-ink`, `--color-crit-border`.

Two latent defects were repaired in the same pass, both pre-existing and unrelated to the toggle work, both consistent with a botched earlier find-and-replace:

- `--color-border-panel` in the dark block was defined as `var(--color-border-panel)`, a self-referential cycle. It resolved to the guaranteed-invalid value, so every dark-theme border reading that token silently fell back. Measured before the fix, the column header bottom border computed to white in dark mode.
- `tr.subtotal-row td.c-wk.past-col` carried `color:var(--color-text-note)9cc`, a malformed declaration that the parser dropped entirely.

**Scope boundary:** this pass targeted the theme-blind class only. Colours with no token match were not triaged, and spacing and text were not touched. See the Path Plan for what remains.

A defect found in v2 during this same run is recorded here rather than quietly fixed: its first version detected only 2 of the 4 token-definition blocks, because the block-matching regex required the selector to follow `}`, `,` or start-of-string, which neither the first theme block (preceded by a comment) nor the second `:root{}` rule does. Their contents were counted as hardcoded usage and inflated the colour occurrence count to 159. Fixed, with the reason recorded in the script so it is not reintroduced.

---

## Colour — by component

| Component | Status | Last confirmed |
|---|---|---|
| Theme architecture (light/dark) | Tokenized | 2026-09-09 |
| App header / icon bar | Tokenized | 2026-09-09 |
| Filter bars (top + sticky search) | Tokenized — sticky search muted text was frozen at the dark value and now follows the theme | 2026-09-09 |
| Button states (primary/secondary/icon, incl. hover/pressed) | Tokenized | 2026-09-09 |
| Milestone dialog | Tokenized | 2026-09-09 |
| Dependency lines | Tokenized | 2026-09-09 |
| Dependency tooltip + comment panel | Tokenized — was frozen at dark values, near-white text over a background that toggled to near-white | 2026-09-09 |
| Settings drawer / View Controls sidebar | Tokenized | 2026-09-09 |
| Board phase bands | Tokenized — `--color-band-1..5`, constant by design | 2026-09-10 |
| Discipline band rows | Not tokenized | 2026-09-10 (re-checked, unchanged) |
| Health dot colours | Tokenized — `--color-health-*` fills and rims, constant by design | 2026-09-10 |
| Milestone status text (`.s-done`/`.s-track`/`.s-future`) | Tokenized — all three were frozen at dark values | 2026-09-09 |
| Milestone marker icon states (DONE/TRACK/RISK/CRIT/FUTURE) | Tokenized — one `--color-icon-*` default state per icon | 2026-09-10 |
| Subtotal row | Tokenized — week-column bands now use `--color-col-past-bg` / `--color-col-filtered-alt-bg`; a malformed colour declaration was also repaired | 2026-09-09 |
| Remarks field states | Tokenized — accent washes plus `--color-text-faint` placeholder | 2026-09-10 |

Update the status cell **and** the date together whenever a row is re-checked, whether or not the status changed — an unchanged status with a fresh date is still useful information (confirms it wasn't silently missed).

## Spacing & Text

| | Status | Last confirmed |
|---|---|---|
| `--space-0` through `--space-7` scale | Defined, applied to recently-built components only | 2026-09-09 |
| `--text-xs/sm/base/md/lg` scale | Defined, applied to recently-built components only | 2026-09-09 |
| Older/untouched components | Raw pixel values throughout | 2026-09-09 |

**Working convention:** any time a component is touched for another reason, bring its tokens up to date in the same pass, and log the measurement + status update here rather than only in memory of the change.
