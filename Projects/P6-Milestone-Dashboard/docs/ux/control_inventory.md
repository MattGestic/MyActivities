# Control inventory — D-15 control consistency pass

Every `<button>`, `[onclick]` clickable, checkbox/radio toggle, and `select` in
`src/milestone-dashboard.html`, grouped by surface. "Action taken" is blank
where the control already matched the standard and needed nothing.

Two shared rules apply across every surface and are not repeated per row:

- A single `:focus-visible` rule (visible keyboard focus, accent-token ring,
  not shown on a mouse click).
- A single min-hit-target rule for every icon-only button class (28px desktop,
  44px at `pointer:coarse`, via `min-width`/`min-height` only, so glyphs are
  unchanged).

## Icon bar / top chrome

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `#btn-remove-all-filters` | "Remove all filters" | secondary (conditional) | none | |
| `#btn-more-actions` | icon (kebab) | icon | had `title` but no `aria-label` | added `aria-label="More actions"` |
| `#btn-fit-screen`, `#btn-theme-toggle`, `#btn-print-mode`, `#btn-export-comments`, `#btn-filter-toggle`, `#btn-style-icon`, `#btn-settings-icon` | icon + text label (menu items) | menu item | none, has icon + visible label + title | |

## Top filter bar (rebuilt at D-16b, v3.1.0-P49, `docs/03-todo.md` TD-191+)

Every control below uses the D-16 tokens (`docs/ux/design-standard.md`):
`--ctl-h`/`--ctl-h-touch` height, `--ctl-pad-x` padding, `--radius-ctl`
(pill for chips), `--focus-ring` on `:focus-visible`. Keyboard: Tab order
follows visual order; Esc closes the topmost open popover (Custom float, the
week-range picker); Enter applies the week-range picker.

| Id/class | Label | Role | Token class | Keyboard | Notes |
|---|---|---|---|---|---|
| `#filter-title` | "Search activity name" | text field | `.ds-field` (in `.ds-fwrap.has-lead.has-clr`) | text input | two-way synced with the sticky corner search |
| `#sticky-title-clear` | icon (X) | icon, in-field | `.clr` | Tab, Enter/Space | shown only once there is a value |
| `#filter-ids` | "e.g. SNIP-101, SNIP-115" | text field + autocomplete | `.ds-field` (in `.ds-fwrap.has-clr`) | text input, `↓`/`↑`/Enter in the suggestion list | `#id-suggest-dropdown` is moved to a `<body>` child the first time it is shown (TD-197), so it always paints above `#icon-bar` |
| `#filter-band` | "All bands" | select | `.ds-select` | native select | |
| `#filter-source` | "All sources" | select | `.ds-select` | native select | wrapped in `#tfb-source-group.tfb-group`; hidden via `closest('.tfb-group')` while only one source is mounted (`onSourceModeChange()`, unchanged) |
| `#wr-field` | "All weeks" / structured W/E text | button, opens the week-range popover | `.wr-field` | Tab, Enter/Space opens; Esc closes the popover; Enter in the popover applies | replaces the Week select, mode select, Current week/Next 4 weeks buttons and the two date inputs; see below |
| `#wr-mode-seg` (`Highlight`/`Show only`) | segmented toggle | toggle | `.ds-seg` | Tab, arrow keys (native), Enter/Space | picks which pre-existing mechanism (`week-filter`+`filter-mode`, or `filter-date-from`/`-to`) a picked range is expressed through |
| `#filter-status-group` (`Critical`/`At risk`/`On track`/`Done`/`Complete`/`Future`) | status chips | multi-select toggle | `.ds-seg.chips .st-chip` | Tab, Enter/Space | `aria-pressed`; each keeps its own state colour when pressed |
| `#float-chip-group` (`Any`/`0d`/`<10d`/`<3 wk`/`<5 wk`/`Custom…`) | Total float preset chips | single-select toggle | `.ds-seg.chips` | Tab, Enter/Space | replaces the op/val/unit selects and the old ≤13d/≤2wk/≥8wk presets; single hidden hold-state (`filter-float-op`/`-val`/`-unit`) unchanged underneath |
| `#float-custom-pop` (comparison, value, unit, Apply/Cancel) | Custom float popover | popover | `.pop-card` | Esc closes, Tab within | opens under the Custom chip; Apply relabels the chip with the value |
| `#btn-clear-crit` | icon (X) | icon | `.ds-ico.crit-clear` | Tab, Enter/Space | clears status + float together, unchanged |
| `#btn-filter-hide` | icon (X) | icon | `.ds-ico` | Tab, Enter/Space | |
| `#btn-filter-expand` | icon + text ("Expand filters") | secondary | (unchanged, outside `#top-filter-bar`) | Tab, Enter/Space | shows only while the bar is collapsed |

### Week-range picker (`#wr-pop-el`, opened by `#wr-field`)

| Element | Role | Token class | Keyboard |
|---|---|---|---|
| Quick ranges (Next 4 weeks / Next 3 months / This month / Rest of programme / Full span) | buttons | `.wr-quick button` | Tab, Enter/Space |
| Week grid (one row per month, one cell per week) | grid of buttons | `.wr-wk` | Tab, Enter/Space per cell (`role="button" tabindex="0"`) |
| From only / Until only | segmented toggle | `.wr-foot .ds-seg` | Tab, Enter/Space |
| Clear / Cancel / Apply | buttons | `.wr-foot .ds-btn` | Tab, Enter/Space; Enter anywhere in the popover triggers Apply |

Superseded by the picker but kept as functions for any caller still using
them: `filterCurrentWeek()`, `filterNext4()`, `setDateRangeToFullSpan()`
(the picker's "Full span" quick range drives the same fields).

## Settings drawer

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `.sd-close` | icon (X) | icon | no `aria-label`, no `title` | added both, "Close" |
| `#sd-tab-sources`/`#sd-tab-import`/`#sd-tab-defaults`/`#sd-tab-diag` | tab labels | tab | none | |
| `#annot-all` "Select all", "Cancel", `#annot-apply` "Import selected" | text | secondary/primary | none, vocabulary already matches standard | |
| "Export &darr; CSV" / "Export &darr; JSON" | text | secondary | none | |
| "Save as new dashboard" (`.active`, primary) | text | primary | none | |
| **"Clear all comments"** (`.sd-btn-danger`) | text | secondary/danger | **defect 2: label did not describe what `resetChanges()` actually resets (row health dots + remarks, not card comments)** | relabelled to **"Reset row marks"**; `title` now states exactly what is reset and that card comments are untouched |
| `#btn-range-reset` "Reset to full range" | text | secondary | none, vocabulary already matches ("Reset") | |
| "or paste CSV/TSV", "Parse pasted data" | text | secondary/primary | none | |
| "&darr; Export diagnostics" | text | secondary | none | |
| Import-step "Discard" / "Import" (JS-built) | text | secondary/primary | none, vocabulary already matches | |
| Source-manager row actions "Rename&hellip;", "Remove", "Add&hellip;", "Mount&hellip;", "Unmount", "Remount&hellip;" (JS-built, `.mnt-btn`) | text | secondary | none, one vocabulary already, own actions bounded to each row | |
| `#toggle-diag-onscreen` (checkbox, `.toggle-switch`) | toggle | toggle | none | |
| radios `#src-mode-replace` / `#src-mode-append` | toggle | toggle | none, each carries adjacent label text | |
| `#st-weekday-seg` (Mon..Sun) | "Week ends on" | segmented toggle | added at D-16b (TD-194): was a 5-option `select#cfg-weekday` (Tue/Wed missing) | `.ds-seg` segmented toggle, the sheet's `.st-row` mock; Tab, Enter/Space; `select#cfg-weekday` kept, extended to all 7 days, hidden, and kept in sync — still the one place `onchange`/`runIngest()` reads the value from |
| `select#map-*` (per column, JS-built) | select | select | none | |
| checkboxes `#annot-cb-*` (JS-built) | toggle | toggle | none | |

## Print preview banner

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `#btn-pm-print` "Print" (`.pm-btn-go`) | text + icon | primary | none | |
| `#btn-pm-fit` "Fit columns to page" | text | secondary | none | |
| `#btn-pm-leave` "Leave preview" | text | secondary | none | |
| `#btn-pm-more` | icon (kebab) | icon | had `title` but no `aria-label` | added `aria-label="More actions"` |
| Paper (`A4`/`A3`) and orientation (`Portrait`/`Landscape`) toggles | text | toggle | none, `data-paper`/`data-orient` already drive active state | |

## Board header / view toggle

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `#vt-baseline` / `#vt-update` | "Baseline" / "Update" | toggle | none | |
| `#btn-add-ms` "+ Milestone" | text | primary-weight action, styled as header button | none, deferred (see below) | |
| `#btn-filter-expand` | see Top filter bar | | | |
| `.fb-close` | icon (X) | icon | had `aria-label` but no `title` | added `title="Close"` |

## Style / column panel (`toggleFilterBar`)

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `#btn-toggle-all-cols` "Show All Columns" | text | secondary | none | |
| `#btn-ref`/`#btn-hrs`/`#btn-alloc`/`#btn-prog`/`#btn-type`/`#btn-doc`/`#btn-task`/`#btn-src`/`#btn-srcsch` | column toggles | toggle | none | |
| `#btn-remarks-show` / `#btn-remarks-hide` | "Show" / "Hide" | toggle | none, vocabulary already matches | |
| `#btn-title-mode-off`/`-title`/`-id`/`-both` | text | toggle | none | |
| `#btn-pred-all-on`/`-off`, `#btn-succ-all-on`/`-off` | "All on" / "All off" | toggle | none (unstyled `<button>`, no `toggle-btn` class; pre-existing, layout-adjacent to other toggle chips) | deferred, see below |
| `#btn-zerofilter-all`/`-hide`/`-only` | text | toggle | none | |
| `#btn-dname-wrap`, `#btn-lbl`, `#btn-mhrs`, `#toggle-counts`, `#btn-baseline-ms` (checkboxes, `.toggle-switch`) | toggle | toggle | none, each wrapped in a `<label>` with visible text | |

## Dependency comment panel

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `.dep-comment-close` | icon (X) | icon | had `aria-label` but no `title` | added `title="Close"` |
| "Cancel" (unstyled `<button>`) | text | secondary | button used `--color-line-hairline`/`--color-dialog-elev`/`--color-text-mono`, not the standard secondary-button tokens | repointed to `--color-btn-secondary-*` |
| `.save` "Save" | text | primary | used `--color-accent-purple` directly rather than the standard primary-button tokens | repointed to `--color-btn-primary-*` |

## Add-milestone dialog

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `.ms-close` | icon (X) | icon | had `aria-label` but no `title` | added `title="Close"` |
| "Cancel" | text | secondary | none | |
| `#add-ms-save` "Add milestone" (`.active`) | text | primary | none | |
| `select#add-ms-type`, `select#add-ms-state` | select | select | none | |

## PDF export dialog

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `.ms-close` | icon (X) | icon | had `aria-label` but no `title` | added `title="Close"` |
| Paper (`A4`/`A3`) and orientation (`Portrait`/`Landscape`) toggles | text | toggle | none | |
| "Cancel" | text | secondary | none | |
| "&darr; Export PDF" (`.active`) | text | primary | none | |

## Milestone card (`#ms-dialog`)

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `.ms-close` (`discardMsDialog`) | icon (X) | icon | none, already had `aria-label` + `title` | |
| **`#ms-save-actions` save pair** (`.ms-act`) | **"&#128190;" / "&#128190; & Close" (emoji glyphs)** | icon-only x2, both rendered identically (accent-purple) | **defect 3: both buttons looked the same weight (two competing primaries), and were icon-only with no `aria-label`** | relabelled to text **"Save"** (secondary, `.ms-act-secondary`) and **"Save & close"** (primary, `.ms-act-primary`); `id`s, `onclick`, and the dirty-state show/hide logic unchanged |
| `#ms-icon-btn` (type/mark picker) | icon (SVG mark) | icon | no `aria-label` (title was set dynamically by `renderMsIcon()`, but only after first render) | added static `aria-label`/`title` in markup, which persists across `innerHTML` re-renders of its child SVG |
| Type menu options (JS-built, `.ms-type-opt`) | text | menu item | none | |
| `#ms-toggle-pred`, `#ms-toggle-succ` (checkboxes) | toggle | toggle | none, wrapped in `<label>` with visible text | |
| Health-dot picker options (`.health-picker`, JS-built) | icon swatches | icon | out of scope for this pass, no onclick change made; deferred | see below |

## Row-level controls (rendered per row)

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `.row-del` | icon (&times;) | icon | had `title` but no `aria-label` | added `aria-label="Remove this row"` |
| `.health-dot` (`openHealthPicker`) | icon swatch | icon | has `title`, click target is the dot itself (deferred, see below) | |

## Print filter note

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `.pfn-close` | icon (X) | icon | had `aria-label` but no `title` | added `title="Dismiss"` |

## Deferred (not changed this pass)

- **`#btn-pred-all-on`/`-off`, `#btn-succ-all-on`/`-off`** — unstyled `<button>`
  elements sitting beside `.toggle-btn` chips in the same row. Restyling them
  onto `.toggle-btn` would change their visual weight next to the dependency
  count chips they sit under; that is a layout judgement call, not a bounded
  token fix, so left as-is.
- **`.health-dot` click targets** — the health-dot swatches on each row (and
  inside `.health-picker`) are small, deliberately-sized colour indicators
  that double as click targets. Bringing them to the 28px minimum would mean
  either enlarging the dot itself (against the "don't enlarge glyphs" rule,
  since here the dot *is* the glyph) or adding an invisible padded hit-area,
  which is a small interaction redesign. Deferred rather than done partially.
  Its `title` text carries the current state.
- **`#btn-add-ms` "+ Milestone"** — the closest thing this header row has to a
  primary action, but it is styled with `.rpt-hd-btn`, a header-chrome class
  using `--color-bg-header-hover`/`--color-text-on-header` tokens rather than
  `--color-btn-primary-*`. Those header tokens are documented in `:root` as
  deliberately separate from the panel button tokens (the header stays dark
  in both themes). Reclassing it risks the header-contrast reasoning recorded
  there; deferred.
- **Pre-existing em dash in `#print-filter-note`'s static text** ("This view
  is filtered &mdash; ...") predates this pass and is not a string this pass
  added; left untouched per the bounded scope (this pass only relabels and
  fixes accessibility/token attributes, not unrelated copy).
- **Colour consolidation of `.pm-btn`, `.vt-btn`, `.rpt-hd-btn`**
  (print banner, view toggle, header row) onto `--color-btn-primary-*`/
  `--color-btn-secondary-*` — still deferred, and on inspection this is a
  correctness call, not just a larger-than-this-pass one. All three sit on
  surfaces the panel button tokens are not built for: `.rpt-hd-btn` is on
  `--color-bg-header`, which stays dark in both themes by design (the same
  reasoning that keeps `#btn-add-ms` off these tokens, above); `.pm-btn` is
  on the print banner's `--color-chip-attention-bg`, a warm "attention" fill
  the panel tokens were never checked against; `.vt-btn` is a Baseline/Update
  **segmented toggle**, the design standard's own "Selected = accent fill
  with on-accent text" role, not a primary/secondary action pair — it
  already follows that role (`.vt-btn.active` is accent-purple on
  on-accent text). Forcing the panel button tokens onto any of the three
  risks a real contrast defect (`--color-btn-secondary-bg` is near-white in
  light theme, which would sit invisibly on the dark header) rather than a
  cosmetic mismatch, so this is left as a colour decision for the same
  reason `#btn-add-ms` was: it needs a person to weigh in, not a token swap.
  **D-16 (this pass) did migrate what was safe** across the three: shared
  `--ctl-pad-x`/`--space-1` padding and `--radius-ctl` where a literal
  already matched the new token's value (`.view-toggle`'s border-radius,
  the padding on all three button classes and on `.toggle-btn`), so their
  box-model no longer carries raw literals even though their colour
  families stay separate. See `docs/ux/design-standard.md`'s new
  `--ctl-*` tokens.
