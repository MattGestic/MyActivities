# Design Token Status

**Purpose:** Current tokenization state of `src/milestone-dashboard.html`, for anyone deciding what to touch next.

**How to use this:** Before styling anything, check the component table below. If `Tokenized`, use its existing tokens. If `Partial` or `Not tokenized`, either token it properly as part of your change or leave it alone. For current counts, always read the bottom row of the Measurement Log per metric, never a number written into prose elsewhere in this file — prose here never states a count directly, only what a metric means and where to find it.

---

## Measurement Log

Append new rows here as measurements are taken. Never edit or delete a prior row — the log itself is the history; the last row per metric is the current figure.

The log is a record of readings, not of changes, so a gap between two rows belongs to every partial in that gap. No audit was run between v3.1.0-P30 and v3.1.0-P35, so the movement between those two sets of rows covers P31 through P35 together and none of it can be attributed to any one of them.

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
| 2026-09-10 | Audit script v3, after the v3.1.0-P8 pass | Hardcoded colour occurrences | 54 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P8 pass | Distinct hardcoded colour values | 43 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P8 pass | Colour occurrences matching an existing token exactly | 10 |
| 2026-09-10 | `tools/theme_check.py`, drag-state and row-number probes added | Probes expected to toggle | 35 |
| 2026-09-10 | `tools/theme_check.py`, after the v3.1.0-P8 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-10 | `tools/theme_check.py`, after the v3.1.0-P8 pass | Probes expected to be constant, correctly frozen | 2 |
| 2026-09-10 | `tools/theme_check.py`, contrast now resolves a transparent element to its nearest painting ancestor | Probes below 3.0:1, before the `.row-num` token fix | 1 |
| 2026-09-10 | `tools/theme_check.py`, contrast now resolves a transparent element to its nearest painting ancestor | Probes below 3.0:1, after the `.row-num` token fix | 0 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P9 mount manager | Hardcoded colour occurrences | 54 |
| 2026-09-10 | Audit script v3, after the v3.1.0-P9 mount manager | Colour occurrences matching an existing token exactly | 11 |
| 2026-09-10 | `tools/theme_check.py`, mount panel and import dialog probes added | Probes expected to toggle | 41 |
| 2026-09-10 | `tools/theme_check.py`, after the v3.1.0-P9 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-10 | `tools/theme_check.py`, after the v3.1.0-P9 pass | Probes expected to be constant, correctly frozen | 4 |
| 2026-09-10 | `tools/theme_check.py`, first run of the new mount-panel probes | Probes below 3.0:1, before the token fixes | 2 |
| 2026-09-10 | `tools/theme_check.py`, after the token fixes | Probes below 3.0:1 | 0 |
| 2026-09-11 | `tools/theme_check.py`, `tr.hist-row` probe added after the header colour change | Probes expected to toggle | 46 |
| 2026-09-11 | `tools/theme_check.py`, header `#ffffff` to `#a6bbdc`, before darkening the muted token | Probes below 3.0:1 | 2 |
| 2026-09-11 | `tools/theme_check.py`, after darkening `--color-text-on-panel-muted` to `#575c67` | Probes below 3.0:1 | 0 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P29 settings-panel rebuild | Hardcoded colour occurrences | 38 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P29 settings-panel rebuild | Distinct hardcoded colour values | 34 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P29 settings-panel rebuild | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P29 settings-panel rebuild | `--space-*` token references in file | 68 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P29 settings-panel rebuild | Hardcoded padding/margin/gap declarations (px) | 194 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P29 settings-panel rebuild | `var(--text-*)` font-size references in file | 29 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P29 settings-panel rebuild | Hardcoded font-size declarations (px) | 109 |
| 2026-09-16 | `tools/p29_check.py`, settings drawer only | Inline padding/margin declarations in the drawer markup, before | 31 |
| 2026-09-16 | `tools/p29_check.py`, settings drawer only | Inline padding/margin declarations in the drawer markup, after | 0 |
| 2026-09-16 | `tools/p29_check.py`, settings drawer only | Distinct values those declarations used, before | 18 |
| 2026-09-16 | `tools/theme_check.py`, settings-drawer component probes added | Probes total | 90 |
| 2026-09-16 | `tools/theme_check.py`, settings-drawer component probes added | Probes expected to toggle | 74 |
| 2026-09-16 | `tools/theme_check.py`, first run of the new drawer probes | Probes expected to toggle, frozen | 1 |
| 2026-09-16 | `tools/theme_check.py`, first run of the new drawer probes | Probes below 3.0:1 | 6 |
| 2026-09-16 | `tools/theme_check.py`, after the drawer background, note ink and accent ink fixes | Probes expected to toggle, frozen | 0 |
| 2026-09-16 | `tools/theme_check.py`, after the drawer background, note ink and accent ink fixes | Probes below 3.0:1 | 0 |
| 2026-09-16 | `tools/theme_check.py`, after the v3.1.0-P29 pass | Probes expected to be constant, correctly frozen | 16 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P30 multi-source pass | Hardcoded colour occurrences | 38 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P30 multi-source pass | Distinct hardcoded colour values | 34 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P30 multi-source pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P30 multi-source pass | `--space-*` token references in file | 68 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P30 multi-source pass | Hardcoded padding/margin/gap declarations (px) | 195 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P30 multi-source pass | `var(--text-*)` font-size references in file | 29 |
| 2026-09-16 | Audit script v3, after the v3.1.0-P30 multi-source pass | Hardcoded font-size declarations (px) | 110 |
| 2026-09-16 | `tools/theme_check.py`, after the v3.1.0-P30 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-16 | `tools/theme_check.py`, after the v3.1.0-P30 pass | Probes below 3.0:1 | 0 |
| 2026-09-18 | Audit script v3, after the v3.1.0-P35 milestone card rework | Hardcoded colour occurrences | 38 |
| 2026-09-18 | Audit script v3, after the v3.1.0-P35 milestone card rework | Distinct hardcoded colour values | 34 |
| 2026-09-18 | Audit script v3, after the v3.1.0-P35 milestone card rework | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-18 | Audit script v3, after the v3.1.0-P35 milestone card rework | `--space-*` token references in file | 70 |
| 2026-09-18 | Audit script v3, after the v3.1.0-P35 milestone card rework | Hardcoded padding/margin/gap declarations (px) | 201 |
| 2026-09-18 | Audit script v3, after the v3.1.0-P35 milestone card rework | `var(--text-*)` font-size references in file | 30 |
| 2026-09-18 | Audit script v3, after the v3.1.0-P35 milestone card rework | Hardcoded font-size declarations (px) | 112 |
| 2026-09-18 | `tools/theme_check.py`, after the v3.1.0-P35 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-18 | `tools/theme_check.py`, after the v3.1.0-P35 pass | Probes below 3.0:1 | 0 |
| 2026-09-19 | Audit script v3, after the v3.1.0-P36 More Actions consolidation | Hardcoded colour occurrences | 38 |
| 2026-09-19 | Audit script v3, after the v3.1.0-P36 More Actions consolidation | Distinct hardcoded colour values | 34 |
| 2026-09-19 | Audit script v3, after the v3.1.0-P36 More Actions consolidation | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-19 | Audit script v3, after the v3.1.0-P36 More Actions consolidation | `--space-*` token references in file | 71 |
| 2026-09-19 | Audit script v3, after the v3.1.0-P36 More Actions consolidation | Hardcoded padding/margin/gap declarations (px) | 204 |
| 2026-09-19 | Audit script v3, after the v3.1.0-P36 More Actions consolidation | `var(--text-*)` font-size references in file | 30 |
| 2026-09-19 | Audit script v3, after the v3.1.0-P36 More Actions consolidation | Hardcoded font-size declarations (px) | 115 |
| 2026-09-19 | `tools/theme_check.py`, after the v3.1.0-P36 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-19 | `tools/theme_check.py`, after the v3.1.0-P36 pass | Probes below 3.0:1 | 0 |
| 2026-09-21 | Audit script v3, after the v3.1.0-P37 defect pass | Hardcoded colour occurrences | 38 |
| 2026-09-21 | Audit script v3, after the v3.1.0-P37 defect pass | Distinct hardcoded colour values | 34 |
| 2026-09-21 | Audit script v3, after the v3.1.0-P37 defect pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-21 | Audit script v3, after the v3.1.0-P37 defect pass | `--space-*` token references in file | 71 |
| 2026-09-21 | Audit script v3, after the v3.1.0-P37 defect pass | Hardcoded padding/margin/gap declarations (px) | 203 |
| 2026-09-21 | Audit script v3, after the v3.1.0-P37 defect pass | `var(--text-*)` font-size references in file | 30 |
| 2026-09-21 | Audit script v3, after the v3.1.0-P37 defect pass | Hardcoded font-size declarations (px) | 115 |
| 2026-09-21 | `tools/theme_check.py`, after the v3.1.0-P37 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-21 | `tools/theme_check.py`, after the v3.1.0-P37 pass | Probes below 3.0:1 | 0 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P38 pass | Hardcoded colour occurrences | 38 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P38 pass | Distinct hardcoded colour values | 34 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P38 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P38 pass | `--space-*` token references in file | 71 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P38 pass | Hardcoded padding/margin/gap declarations (px) | 209 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P38 pass | `var(--text-*)` font-size references in file | 30 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P38 pass | Hardcoded font-size declarations (px) | 117 |
| 2026-09-22 | `tools/theme_check.py`, after the v3.1.0-P38 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-22 | `tools/theme_check.py`, after the v3.1.0-P38 pass | Probes below 3.0:1 | 0 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P39 pass | Hardcoded colour occurrences | 38 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P39 pass | Distinct hardcoded colour values | 34 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P39 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P39 pass | `--space-*` token references in file | 76 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P39 pass | Hardcoded padding/margin/gap declarations (px) | 213 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P39 pass | `var(--text-*)` font-size references in file | 30 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P39 pass | Hardcoded font-size declarations (px) | 117 |
| 2026-09-22 | `tools/theme_check.py`, after the v3.1.0-P39 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-22 | `tools/theme_check.py`, after the v3.1.0-P39 pass | Probes below 3.0:1 | 0 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P40 pass | Hardcoded colour occurrences | 38 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P40 pass | Distinct hardcoded colour values | 34 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P40 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P40 pass | `--space-*` token references in file | 79 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P40 pass | Hardcoded padding/margin/gap declarations (px) | 224 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P40 pass | `var(--text-*)` font-size references in file | 31 |
| 2026-09-22 | Audit script v3, after the v3.1.0-P40 pass | Hardcoded font-size declarations (px) | 124 |
| 2026-09-22 | `tools/theme_check.py`, after the v3.1.0-P40 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-22 | `tools/theme_check.py`, after the v3.1.0-P40 pass | Probes below 3.0:1 | 0 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P41 pass | Hardcoded colour occurrences | 38 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P41 pass | Distinct hardcoded colour values | 34 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P41 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P41 pass | `--space-*` token references in file | 79 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P41 pass | Hardcoded padding/margin/gap declarations (px) | 224 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P41 pass | `var(--text-*)` font-size references in file | 31 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P41 pass | Hardcoded font-size declarations (px) | 124 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P41 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P41 pass | Probes below 3.0:1 | 0 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P42 pass | Hardcoded colour occurrences | 38 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P42 pass | Distinct hardcoded colour values | 34 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P42 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P42 pass | `--space-*` token references in file | 79 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P42 pass | Hardcoded padding/margin/gap declarations (px) | 224 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P42 pass | `var(--text-*)` font-size references in file | 31 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P42 pass | Hardcoded font-size declarations (px) | 124 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P42 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P42 pass | Probes below 3.0:1 | 0 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P43 pass | Hardcoded colour occurrences | 38 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P43 pass | Distinct hardcoded colour values | 34 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P43 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P43 pass | `--space-*` token references in file | 92 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P43 pass | Hardcoded padding/margin/gap declarations (px) | 227 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P43 pass | `var(--text-*)` font-size references in file | 31 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P43 pass | Hardcoded font-size declarations (px) | 123 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P43 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P43 pass | Probes below 3.0:1 | 0 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P44 pass | Hardcoded colour occurrences | 38 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P44 pass | Distinct hardcoded colour values | 34 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P44 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P44 pass | `--space-*` token references in file | 93 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P44 pass | Hardcoded padding/margin/gap declarations (px) | 228 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P44 pass | `var(--text-*)` font-size references in file | 31 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P44 pass | Hardcoded font-size declarations (px) | 122 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P44 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-23 | `tools/theme_check.py`, after the v3.1.0-P44 pass | Probes below 3.0:1 | 0 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P45 pass | Hardcoded colour occurrences | 38 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P45 pass | Distinct hardcoded colour values | 34 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P45 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P45 pass | `--space-*` token references in file | 101 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P45 pass | Hardcoded padding/margin/gap declarations (px) | 229 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P45 pass | `var(--text-*)` font-size references in file | 31 |
| 2026-09-23 | Audit script v3, after the v3.1.0-P45 pass | Hardcoded font-size declarations (px) | 125 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P46/P47/P48 passes (no audit run between P45 and P48, so this movement covers D-15, D-15a and the component-reliability pass together, not any one of them) | Hardcoded colour occurrences | 38 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P46/P47/P48 passes | Distinct hardcoded colour values | 34 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P46/P47/P48 passes | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P46/P47/P48 passes | `--space-*` token references in file | 111 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P46/P47/P48 passes | Hardcoded padding/margin/gap declarations (px) | 228 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P46/P47/P48 passes | `var(--text-*)` font-size references in file | 28 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P46/P47/P48 passes | Hardcoded font-size declarations (px) | 127 |
| 2026-09-24 | `tools/spacing_audit.py` (new gate, TD-188; a separate, ratcheted count — see its own header for why it will not equal the `px_spacing` row above) | Raw px in padding/margin/gap declarations, ceiling | 153 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P49 pass (D-16b filter bar rebuild) | Hardcoded colour occurrences | 38 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P49 pass | Distinct hardcoded colour values | 34 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P49 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P49 pass | `--space-*` token references in file | 120 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P49 pass | Hardcoded padding/margin/gap declarations (px) | 227 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P49 pass | `var(--text-*)` font-size references in file | 35 |
| 2026-09-24 | Audit script v3, after the v3.1.0-P49 pass | Hardcoded font-size declarations (px) | 134 |
| 2026-09-24 | `tools/theme_check.py`, after the v3.1.0-P49 pass | Probes expected to toggle, frozen | 0 |
| 2026-09-24 | `tools/spacing_audit.py`, after the v3.1.0-P49 pass | Raw px in padding/margin/gap declarations, ceiling | 152 |
| 2026-09-25 | Audit script v3, after the v3.1.0-P50 pass (D-18 on-board "edited" mark) | Hardcoded colour occurrences | 38 |
| 2026-09-25 | Audit script v3, after the v3.1.0-P50 pass | Distinct hardcoded colour values | 34 |
| 2026-09-25 | Audit script v3, after the v3.1.0-P50 pass | Colour occurrences matching an existing token exactly | 7 |
| 2026-09-25 | Audit script v3, after the v3.1.0-P50 pass | `--space-*` token references in file | 122 |
| 2026-09-25 | Audit script v3, after the v3.1.0-P50 pass | Hardcoded padding/margin/gap declarations (px) | 227 |
| 2026-09-25 | Audit script v3, after the v3.1.0-P50 pass | `var(--text-*)` font-size references in file | 35 |
| 2026-09-25 | Audit script v3, after the v3.1.0-P50 pass | Hardcoded font-size declarations (px) | 134 |
| 2026-09-25 | `tools/spacing_audit.py`, after the v3.1.0-P50 pass — the mark's own top/right/width/height/border are geometry, not padding/margin/gap, so only its legend-swatch margin counted, and that one was tokened onto `--space-1` | Raw px in padding/margin/gap declarations, ceiling | 152 (unchanged, at ceiling) |
| 2026-09-25 | `tools/theme_check.py`, `.m-board-edit-mark` and the legend swatch added (D-18; deliberately `--color-accent-ink`, not the P44 card mark's `--color-accent-purple`, which is constant across themes) | Probes expected to toggle, frozen | 0 |
| 2026-09-25 | `tools/theme_check.py`, after the v3.1.0-P50 pass | Probes expected to toggle | 77 |
| 2026-09-25 | Audit script v3, after v3.1.0-P53 (date range filter revision: Fallback window UI removed, Find/Date range layout, Annotations filter, em-dash fixes incl. the subtotal-row colour fix) | Hardcoded colour occurrences | 40 |
| 2026-09-25 | Audit script v3, after v3.1.0-P53 | Distinct hardcoded colour values | 36 |
| 2026-09-25 | Audit script v3, after v3.1.0-P53 | Colour occurrences matching an existing token exactly | 9 |
| 2026-09-25 | Audit script v3, after v3.1.0-P53 | `--space-*` token references in file | 128 |
| 2026-09-25 | Audit script v3, after v3.1.0-P53 | Hardcoded padding/margin/gap declarations (px) | 227 |
| 2026-09-25 | Audit script v3, after v3.1.0-P53 | `var(--text-*)` font-size references in file | 41 |
| 2026-09-25 | Audit script v3, after v3.1.0-P53 | Hardcoded font-size declarations (px) | 135 |
| 2026-09-25 | `tools/spacing_audit.py`, after v3.1.0-P53 — all new spacing in the Range start/end footer, the Annotations chip group and the Find/Date range row layout used existing `var(--space-*)`/`--ctl-*` tokens; no new raw px | Raw px in padding/margin/gap declarations, ceiling | 152 (unchanged, at ceiling) |
| 2026-09-25 | `tools/theme_check.py`, after v3.1.0-P53 (subtotal row's text colour moved from the fixed `--color-text-on-accent` to the themed `--color-text-primary`, fixing a near-invisible white-on-pale-lilac reading in light theme) | Probes toggling / frozen | 77 toggling / 0 frozen |

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
| Icon bar and More Actions menu | Tokenized. Built at v3.1.0-P36 on existing tokens only; the audit's colour counts are unchanged across the change. Re-checked at v3.1.0-P38 when the bar gained print-preview sizing and the menu a second trigger; no colour touched | 2026-09-22 |
| Top filter bar, including the critical-path set | Tokenized. The status chips at v3.1.0-P40 take `--color-status-crit/risk/track/done` and `--color-text-muted`, the same five the board paints with, so the filter reads in the board's vocabulary. No new values | 2026-09-22 |
| Add-a-milestone dialog | Tokenized. Built at v3.1.0-P40 on the same dialog, input and scrim tokens `.ms-dialog` and the settings drawer already use. No new values; the audit's colour counts are unchanged across the change | 2026-09-22 |
| Print preview banner and its controls | Tokenized. The three controls added at v3.1.0-P38 take `--color-chip-attention-bg` / `--color-chip-attention-ink`, the pair the strip already carries, inverted on hover, and `--color-crit` for the notification dot. No new values; the audit's colour counts are unchanged across the change | 2026-09-22 |
| Milestone dialog | Tokenized. Reworked at v3.1.0-P35 (10% smaller, one schedule row, editable Progress) adding no hardcoded colour: every new declaration uses an existing token | 2026-09-18 |
| Dependency lines | Tokenized | 2026-09-09 |
| Dependency tooltip + comment panel | Tokenized — was frozen at dark values, near-white text over a background that toggled to near-white | 2026-09-09 |
| Settings drawer | Tokenized and rebuilt on the `sd-` component set at v3.1.0-P29. One gutter, one row step, one radius family, no inline spacing. Two hardcoded label inks, three import-status inks and two import-control borders replaced; three new tokens, `--color-ok-text`, `--color-accent-ink` and `--radius-sm/md/pill` | 2026-09-16 |
| View Controls sidebar | Tokenized. Still on its own `.cv-*` classes; `.cv-sect-title` and three siblings paint `--color-purple-deep` on a dark panel in dark theme, which measures 1.79:1 (TD-97) | 2026-09-16 |
| Board phase bands | Tokenized — `--color-band-1..5`, constant by design | 2026-09-10 |
| Discipline band rows | Not tokenized | 2026-09-10 (re-checked, unchanged) |
| Health dot colours | Tokenized — `--color-health-*` fills and rims, constant by design | 2026-09-10 |
| Milestone status text (`.s-done`/`.s-track`/`.s-future`) | Tokenized — all three were frozen at dark values | 2026-09-09 |
| Milestone marker icon states (DONE/TRACK/RISK/CRIT/FUTURE) | Tokenized — one `--color-icon-*` default state per icon | 2026-09-10 |
| Subtotal row | Tokenized — week-column bands now use `--color-col-past-bg` / `--color-col-filtered-alt-bg`; a malformed colour declaration was also repaired | 2026-09-09 |
| Milestone card | Tokenized — the card's editable fields, type picker and save pair use the spacing scale; three accent-text rules moved off `--color-purple-dark`, which is ink for a light tint and measured 1.13:1 on a themed panel in dark, onto `--color-accent-ink` | 2026-09-23 |
| Remarks field states | Tokenized — accent washes plus `--color-text-faint` placeholder | 2026-09-10 |
| On-board "edited" mark + legend swatch (D-18) | Tokenized — reuses the P44 card mark's `.ms-edited-mark` class/shape, but its background is `--color-accent-ink`, not that mark's `--color-accent-purple`: the latter is deliberately the same hex in both themes (see the `.ms-act`/`.ms-type-opt.active` constants), which would make the board mark invisible against a dark-theme icon and fail `theme_check`'s toggle expectation. One new spacing use (`--space-1` for the legend swatch's own gap), no new colour values | 2026-09-25 |

Update the status cell **and** the date together whenever a row is re-checked, whether or not the status changed — an unchanged status with a fresh date is still useful information (confirms it wasn't silently missed).

## Spacing & Text

| | Status | Last confirmed |
|---|---|---|
| `--space-0` through `--space-7` scale | Defined, applied to recently-built components only | 2026-09-09 |
| `--text-xs/sm/base/md/lg` scale | Defined, applied to recently-built components only | 2026-09-09 |
| Older/untouched components | Raw pixel values throughout | 2026-09-09 |

**Working convention:** any time a component is touched for another reason, bring its tokens up to date in the same pass, and log the measurement + status update here rather than only in memory of the change.
