# P55 token gap inventory and central palette design

Sweep of `src/milestone-dashboard.html` at v3.1.0-P54 (2026-09-26), done before P55 (D-22, palette Option A). It lists every colour that does not come from one central, theme-switched place. Counts live in the Measurement Log, not here. Re-run `tools/colour_audit.py` for current figures.

**Goal (Matt, 2026-09-26):** a theme change is one edit in one place. Nobody has to go looking for stray colours.

## 1. What the sweep found

### 1a. Literal colours in CSS rules (outside the token blocks)

| Where | Selector / line area | Literals | Fix |
|---|---|---|---|
| Print filter note | `#print-filter-note`, `.pfn-close` | cream bg, amber border, brown ink, brown hover wash | `--color-notice-*` role set (bg, border, ink), hover via `color-mix` |
| Drawer, filter bar, suggest dropdown, toggle knob, dep comment panel | `#settings-drawer`, `#filter-bar`, `.id-suggest-dropdown`, `.tsw-slider:before`, `.dep-comment-panel` | five different `rgba(0,0,0,…)` shadows | elevation scale `--shadow-1/2/3` from one `--shadow-color` |
| Week header | `tr.hdr-wk th`, `.past-wk`, `.past-wk:hover` | `#99a`, `#e8e8e8`, `#dcdcdc` | `--color-bg-past`, hover as a surface wash |
| Phase header | `tr.hdr-phase th` | white 15% divider | `--color-band-divider` (derived) |
| Alloc/prog cells | `td.c-alloc,td.c-prog` | `#f7f7fa` | `--color-bg-subtle` |
| Import mapping | `.map-hd`, `.map-cell select`, `.req`, `.import-pass` | navy ink, red required, green-grey border, pass green, fail red | existing text, line, status tokens |
| Diagnostics panel | `#diag-panel`, `.diag-tbl*`, `.diag-none`, `.toggle-btn.diag-warn/err` | a full cream/brown mini-palette, warn amber, error maroon | `--color-notice-*` plus status risk/crit |

The diagnostics panel and the print note were never themed, so they are cream in dark mode today.

### 1b. `var()` with a literal fallback

`.sd-badge--cond`, `.sd-badge--done`, `.rpt-hd` border, `#icon-bar .title:focus`. All four tokens are defined, so the fallbacks never fire. They are still stale copies of old values scattered in rules. **Remove them** under the central rule. This changes the current CLAUDE.md note, which treats them as harmless (see §4).

### 1c. Colours in JS

| Where | What | Fix |
|---|---|---|
| `MONTH_BG` map + `renderPhaseHdr()` inline `th.style.background` + `'#1e2240'` fallback | month header colours per season | month A/B class on the `th`, colours in CSS tokens |
| Seed `MONTHS[].bg` (schedule data block) | colour stored **in the data layer** | drop `bg` from the data; render computes the class. Old files carrying `bg` are ignored, not migrated |
| Milestone tooltip `msTipEl.style.cssText` | navy glass bg, white 14% border, black shadow | a `.ms-tip` CSS class on tokens (`--color-tooltip-*`, `--shadow-2`) |

No canvas drawing colours (the only canvas is a text-measuring context). No literal SVG `fill`/`stroke` in JS or markup.

### 1d. Theme-blind literal tokens in `:root`

These are tokens, but they hold literals that are the same in both themes. Several still carry the retired lavender accent, so P55's teal swap would miss them.

| Group | Tokens | Problem |
|---|---|---|
| Accent washes | `--color-accent-wash-weak/-/-strong` | hardcoded lavender `rgba(139,100,199,…)`. Derive from `--color-accent` with `color-mix` |
| Histogram / label backings | `--color-hist-bar-top`, `--color-label-hrs-backing(-soft)` | lavender literals |
| Phase bands | `--color-band-1..5`, `--color-band-divider` | old categorical set; replaced by §3b of the palette sheet |
| Health dots | `--color-health-*` (good, watch, info, none, borders, rim) | a second status set that duplicates `--color-status-*` with different values. Point at the status tokens |
| Header chrome | `--color-text-on-header(-muted)`, `--color-bg-header-hover/focus` | white washes should derive from the on-header text token |
| Shadows / scrim | `--color-shadow-soft`, `--color-scrim` | fold into the elevation scale and one `--scrim-color` |
| Label backings | `--color-label-backing(-alt)` | white literals; derive from the surface token |
| Misc | `--color-chip-attention-bg/ink`, `--color-crit-border` | literals; map to status risk and crit |

### 1e. Hue-named tokens

`--color-accent-purple`, `--color-purple-deep`, `--color-comment-indicator` (lavender). Once the accent is teal, a token called `purple` is a trap. Rename by role: `--color-accent`, `--color-accent-strong`. The comment indicator becomes an alias of `--color-accent`.

### 1f. Token definitions spread across the file

Colour tokens are defined in the light block, the dark block and the first `:root`. Four more `:root` blocks further down hold sizing tokens (touch sizing, page sheet, row gutter, column width). They are not colours, but "one place" should mean one place. Fold them into the top token section.

## 2. Central palette design (proposed for P55)

Three tiers. **Literal colour values may appear in tier 1 only.**

| Tier | Prefix | Defined | Holds | Example |
|---|---|---|---|---|
| 1 Palette | `--pal-*` | twice: `html[data-theme="light"]` and `html[data-theme="dark"]`, at the top of `<style>`, nowhere else | the approved Option A values, plus the §3b group and month tones | `--pal-navy`, `--pal-teal`, `--pal-teal-ink`, `--pal-status-risk`, `--pal-band-3`, `--shadow-rgb` |
| 2 Role | `--color-*` | once, in `:root`, below the palette | a `var(--pal-*)` or a `color-mix()` of one. Never a literal | `--color-accent: var(--pal-teal)`; `--color-accent-wash: color-mix(in srgb, var(--color-accent) 10%, transparent)` |
| 3 Component | `--<component>-*` | beside the component's CSS, if needed at all | a `var(--color-*)` only | `--hist-bar: var(--color-accent-wash-strong)` |

**Derived scales (tier 2):**
- **Elevation:** `--shadow-1/2/3`, each built from `--shadow-color` (tier 1, one value per theme).
- **Wash:** `--wash-weak/-/-strong` as percentages of the accent.
- **Surface interaction:** `--hover`, `--pressed` as percentages of the ink over the current surface.
- **Scrim:** `--scrim` from `--pal-ink`.

**What a theme change becomes:** edit the tier 1 values. Every role, wash, shadow, band, month and component follows.

**Browser support:** `color-mix()` is supported in every evergreen browser (Chrome/Edge 111+, Safari 16.2+, Firefox 113+). No older-browser requirement is recorded in `docs/00-project-context.md`. **[CONFIRM WITH MATT]** that IE-mode Edge or an older locked-down browser is not in use at site.

## 3. Enforcement (so it stays central)

1. **`colour_audit.py` is extended.** A literal colour anywhere outside the two tier-1 blocks fails. That covers CSS rules, other `:root` blocks, inline `style=""`, JS strings (including `style.cssText` and data blocks), `var()` fallbacks and SVG attributes. Ceiling 0.
2. **A palette-swap probe (new, in `theme_check.py`).** At runtime it overrides every `--pal-*` with sentinel colours. It then walks every rendered element's computed `color`, `background-color`, `border-*-color`, `outline-color`, `box-shadow`, `fill` and `stroke`, and fails on any value that is not built from a sentinel. This is the direct proof that a theme change needs no hunting: a colour that escaped the palette cannot take on the sentinel.
3. **`docs/ux/design-standard.md` colour roles table** is rewritten against the tier 2 names, including which component uses which elevation level.

## 4. Decisions needed

1. **Remove `var()` literal fallbacks.** Recommended: yes. This reverses the CLAUDE.md note that calls them "not defects". They work, but they are scattered stale copies, and the centrality goal outranks them.
2. **Group bands become theme-scoped.** The current comment says bands stay constant across themes to keep the text pairing. The §3b set keeps white text at AA in both themes, so scoping them is safe. Recommended: yes.
3. **Health-dot colours merge into the status set.** Recommended: yes. Today health green `#158a28` and status complete are two different greens for one meaning. This lines up with the pending state/health marker redesign.
