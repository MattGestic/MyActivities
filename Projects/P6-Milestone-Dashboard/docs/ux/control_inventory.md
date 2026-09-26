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
| `#filter-band` | "All bands" | select | `.ds-select` | native select | P53: sits with Activity name and Source on one nowrap row (`.fb-row-1`), not its own wrapped row |
| `#filter-source` | "All sources" | select | `.ds-select` | native select | wrapped in `#tfb-source-group.tfb-group`; hidden via `closest('.tfb-group')` while only one source is mounted (`onSourceModeChange()`, unchanged) |
| `#wr-field` | "All weeks" / structured W/E text | button, opens the week-range popover | `.wr-field` | Tab, Enter/Space opens; Esc closes the popover; Enter in the popover applies | replaces the Week select, mode select, Current week/Next 4 weeks buttons and the two date inputs; see below. P53: its box (`#tfb-when`) is titled "Date range" (was "When"), and shares one line with `#wr-mode-seg` and `#btn-fit-screen-inline` |
| `#wr-mode-seg` (`Highlight`/`Show only`) | segmented toggle | toggle | `.ds-seg` | Tab, arrow keys (native), Enter/Space | picks which pre-existing mechanism (`week-filter`+`filter-mode`, or `filter-date-from`/`-to`) a picked range is expressed through |
| `#btn-fit-screen-inline` | icon (↔) | icon | `.ds-ico` | Tab, Enter/Space | P53: `fitToScreen()`, moved onto the Date range row as a secondary entry point; `#btn-fit-screen` in the More Actions menu is unchanged and still works |
| `#filter-status-group` (`Critical`/`At risk`/`On track`/`Done`/`Complete`/`Future`) | status chips | multi-select toggle | `.ds-seg.chips .st-chip` | Tab, Enter/Space | `aria-pressed`; each keeps its own state colour when pressed |
| `#float-chip-group` (`Any`/`0d`/`<10d`/`<3 wk`/`<5 wk`/`Custom…`) | Total float preset chips | single-select toggle | `.ds-seg.chips` | Tab, Enter/Space | replaces the op/val/unit selects and the old ≤13d/≤2wk/≥8wk presets; single hidden hold-state (`filter-float-op`/`-val`/`-unit`) unchanged underneath |
| `#float-custom-pop` (comparison, value, unit, Apply/Cancel) | Custom float popover | popover | `.pop-card` | Esc closes, Tab within | opens under the Custom chip; Apply relabels the chip with the value |
| `#annot-chip-group` (`Any`/`Commented`/`Edited`/`Either`) | Annotations preset chips | single-select toggle | `.ds-seg.chips` | Tab, Enter/Space | P53 (item 9): after Total float, a divider before it; drives `ANNOT_FILTER`, read by `applyFilter()`'s `rowMatchesAnnotation()` |
| `#btn-clear-crit` | icon (X) | icon | `.ds-ico.crit-clear` | Tab, Enter/Space | clears status + float + annotations together; the box's own title was removed (P53 item 8) |
| `#btn-filter-hide` | icon (X) | icon | `.ds-ico` | Tab, Enter/Space | |
| `#btn-filter-expand` | icon + text ("Expand filters") | secondary | (unchanged, outside `#top-filter-bar`) | Tab, Enter/Space | shows only while the bar is collapsed |
| `#filter-info` | filter summary text | status text | `.filter-info` | none | P53 (item 11): no reserved hint text; empty and effectively invisible when nothing is filtered, footer keeps only the close (×) control |

### Week-range picker (`#wr-pop-el`, opened by `#wr-field`)

P53: the quick-range list, order and wording changed (This week / This month
/ Next 4 weeks / Next 3 months / Rest of programme / Full programme / Full
range); From only/Until only are gone, replaced by Range start/Range end
date fields plus Reset to schedule.

| Element | Role | Token class | Keyboard |
|---|---|---|---|
| Quick ranges (This week / This month / Next 4 weeks / Next 3 months / Rest of programme / Full programme / Full range) | buttons | `.wr-quick button` | Tab, Enter/Space |
| Week grid (one row per month, one cell per week) | grid of buttons | `.wr-wk` | Tab, Enter/Space per cell (`role="button" tabindex="0"`) |
| `#wr-range-start`, `#wr-range-end` | date fields | `.ds-field` (`input[type=date]`) | text/native date input, `onchange` | edit the board's own bounds (`rebuildTimelineForBaseRange()`); week-snapped to the week-ending day; prefilled from the live timeline on every render |
| Reset to schedule | button | `.ds-btn` | Tab, Enter/Space | restores the span derived from the schedule's own min/max dates (`wrResetToSchedule()`) |
| Clear / Cancel / Apply | buttons | `.wr-foot .ds-btn` | Tab, Enter/Space; Enter anywhere in the popover triggers Apply | Apply with only a start week picked applies as "from", open end (the From-only replacement) |

Superseded by the picker but kept as functions for any caller still using
them: `filterCurrentWeek()`, `filterNext4()`, `setDateRangeToFullSpan()`
(the picker's own "Full range" quick range drives the same fields).

### Board headers (P53 items 12/13)

| Element | Role | Notes |
|---|---|---|
| `#week-hdr th.col-wk` | clickable week heading | `title="Filter to W/E … (click)"`; hover/cursor affordance pre-existing (`tr.hdr-wk th:hover`) |
| `#phase-hdr th.mo-band` | clickable month heading | new in P53: `onMonthHeaderClick()`, same range the Date range picker would set for that month; `title="Filter to <Month Year> (click)"`; hover via an inset overlay (the band's own background is set inline per month) |

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

### Sources tab (rebuilt at D-17a, v3.1.0-P51, `docs/03-todo.md` TD-200)

Replaces the row `"Source-manager row actions ... .mnt-btn"` above for the
Schedules/User-defined groups specifically (the Annotations slot, D-17b
territory, is unchanged and still `.mnt-btn`/`.sd-card`). New controls, all
JS-built into `#mount-body`, `.toggle-switch`/`.toggle-btn` per the existing
Settings-drawer convention (see TEST-51's design-decisions note on why these
were reused rather than rebuilt to the mockup's literal 32x16/24px figures):

| Id/class | Label | Role | Token class | Keyboard | Notes |
|---|---|---|---|---|---|
| per-source `.toggle-switch` (`onchange="toggleSourceEnabled(id)"`) | "On"/"Off" via `title` | toggle | `.toggle-switch` | Tab, Space | one per `PRIMARY_SOURCES` entry; the board's rows drop to/return from exactly that source's count |
| baseline row's `.toggle-switch` | "Built in. Cannot be unmounted." | toggle (disabled) | `.toggle-switch` | not tabbable (`disabled`) | always on, never interactive |
| per-source "Rename&hellip;" (`renameSource(id)`) | text | secondary | `.toggle-btn.mnt-btn` | Tab, Enter/Space | unchanged behaviour, unchanged class |
| per-source "Remove" (`askRemoveSource(id)`) | text | secondary/danger | `.toggle-btn.mnt-btn.sd-btn-danger` | Tab, Enter/Space | opens the inline confirm below it, replacing the native `confirm()` |
| inline confirm "Cancel" / "Remove" (`cancelRemoveSource()` / `removeSource(id)`) | text | secondary / danger | `.toggle-btn` / `.toggle-btn.sd-btn-danger` inside `.sd-confirm` | Tab, Enter/Space, Esc (via the drawer's existing Esc-closes-topmost-surface handling) | design standard's inline confirmation: message full width (`.sd-confirm-txt`), Cancel bottom-left, danger action bottom-right (`.sd-confirm-actions`) |
| `.sd-warn` (JS-built, no control) | duplicate-ID warning text | status text, not interactive | `.sd-warn` | n/a | one line per pair of enabled sources sharing an Activity ID; disappears the moment either is switched off |
| User-defined row's `.toggle-switch` (`toggleUserDefinedEnabled()`) | "On"/"Off" via `title` | toggle | `.toggle-switch` | Tab, Space | hides/shows the 3-layer-rule-respecting `USER_MILESTONES` merge without deleting it |
| "Manage&hellip;" (disabled) | text | secondary (disabled) | `.toggle-btn.mnt-btn` | not tabbable while `disabled` | `title="Grid arrives in D-17c"`; the grid itself is out of scope for this pass |
| "Export (schedule format)" (`exportUserDefinedSchedule()`) | text | secondary | `.toggle-btn.mnt-btn` | Tab, Enter/Space | `.xlsx` via the same `ensureXLSX()` loader `exportComments()` uses; falls back to CSV if the library cannot load |
| User-defined "Remove" (`askRemoveUserDefined()`) | text | secondary/danger | `.toggle-btn.mnt-btn.sd-btn-danger` | Tab, Enter/Space | same inline-confirm pattern; deletes `USER_MILESTONES`/`USER_ROWS` only, annotations keyed by Activity ID are kept (stated in the confirm text) |

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

## Histogram row (D-21, v3.1.0-P54)

New controls, built in `renderHistogram()` and mirrored in View Controls.
Both segments reuse `.view-toggle`/`.vt-btn`'s existing token pair
(`--color-vt-divider`, `--color-accent-purple`, `--color-text-on-accent`,
`--color-btn-icon-hover-bg`) rather than a third accent look; the only
addition is `.hist-seg`'s explicit `height:var(--ctl-h)`, so the control
measures the D-16 24px desktop standard on its own box rather than inheriting
a padding-derived height. Keyboard: native `<button>`, tab order follows DOM
order, `role="group"`/`aria-label` on each `.hist-seg` pair.

| Id/class | Label | Role | Token | Keyboard |
|---|---|---|---|---|
| `.hist-seg button[data-measure]` (`#hist-measure-seg`, in the label cell) | Hours / Tasks | segmented toggle | `--ctl-h`, `--color-vt-divider`, `--color-accent-purple` | native button, tab/Enter/Space |
| `.hist-seg button[data-pos]` (`#hist-pos-seg`, in the label cell) | Top / Bottom | segmented toggle | same as above | native button |
| `#btn-hist-measure-hours` / `#btn-hist-measure-tasks` (View Controls > Histogram) | Hours / Tasks | `.toggle-btn` pair (existing "Show/Hide" idiom, TD-147) | `--color-btn-primary-*`/`--color-btn-secondary-*` (unchanged `.toggle-btn`) | native button |
| `#btn-hist-pos-top` / `#btn-hist-pos-bottom` (View Controls > Histogram) | Top / Bottom | `.toggle-btn` pair | same as above | native button |

The label-cell measure/position buttons and the View Controls buttons are
two entry points to the same two globals (`HIST_MEASURE`/`HIST_POS` via
`setHistMeasure()`/`setHistPos()`); `syncHistControlsUI()` is the single
writer that keeps both pairs showing the same `.active` state, since only the
label cell is rebuilt from scratch on every render. Hidden under
`@media print` (`.hist-ctl-row{display:none}`) — interactive chrome, not
report content; the bars and the "Histogram" label still print, wherever
`HIST_POS` placed the row.

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
