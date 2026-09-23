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

## Top filter bar

| Id/class | Label | Role | Issue(s) | Action taken |
|---|---|---|---|---|
| `#sticky-title-clear` | icon (X) | icon | none, has `aria-label` + `title` | |
| `.fb-field-clear` (Activity ID, critical filters, date range) | icon (X) | icon | none, each already has `aria-label` + `title` | |
| `#fs-CRIT`/`#fs-RISK`/`#fs-TRACK`/`#fs-DONEUSER`/`#fs-DONE`/`#fs-FUTURE` | status chip toggles | toggle | none, `aria-pressed` already present | |
| float shortcut buttons (`&le; 13d`, `&le; 2wk`, `&ge; 8wk`) | text | secondary | none | |
| `#btn-clear-crit` | icon (X) | icon | none, has `aria-label` + `title` | |
| "Current week" / "Next 4 weeks" | text | secondary | none | |
| `#btn-clear-date-range` | icon (X) | icon | none, has `aria-label` + `title` | |
| "Full span" | text | secondary | none | |
| `#btn-filter-hide` | icon (X) | icon | none, has `aria-label` + `title` | |
| `#btn-filter-expand` | icon + text ("Expand filters") | secondary | none | |

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
| `select#cfg-weekday`, `select#map-*` (per column, JS-built) | select | select | none | |
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
- **Wholesale token consolidation of `.pm-btn`, `.vt-btn`, `.rpt-hd-btn`**
  (print banner, view toggle, header row) onto `--color-btn-primary-*`/
  `--color-btn-secondary-*` — each of these already has its own internal
  primary/secondary distinction, built on tokens with their own documented
  rationale (header chrome, print-banner "on" state, and the purple accent
  used for the active view). Re-pointing all of them is a larger
  visual-language change than a control-consistency pass and is not one of
  the three confirmed defects; deferred.
