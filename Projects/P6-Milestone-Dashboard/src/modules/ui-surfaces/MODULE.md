# ui-surfaces (`SRETSurfaces`)

The internal cards and content containers (D-32): card, section, panel header, toolbar, tabs, fold, list, empty state and toast.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` |
| Status | Standalone (D-32 Stage A) |
| Global | `window.SRETSurfaces` (`tabs`, `toast`), also `module.exports` |
| Requires | `ui-tokens`; `ui-icons` for the fold chevron |

## Layout contract

| Part | Direction and wrap | Padding | Gap | Content behaviour |
|---|---|---|---|---|
| `.ui-card` | column | none (its parts pad) | none | `min-width: 0`. Border 1 px, radius 8, elevation 1 |
| `.ui-card__header` | row, no wrap | 12 px 16 px | 8 px | Title truncates with an ellipsis; actions keep their size |
| `.ui-card__body` | column | 16 px | 12 px | Children stack; text wraps |
| `.ui-card__footer` | row, **wraps**, right-aligned | 12 px 16 px | 8 px | Buttons wrap to a new line on narrow widths, never squeezed |
| `.ui-section` | column | none | 8 px | Uppercase 11 px label, then content |
| `.ui-panel-header` | row, no wrap | 8 px 12 px 8 px 16 px; min height 52 px | 8 px | Title truncates; actions keep their size |
| `.ui-toolbar` | row, **wraps** | none | 8 px | `--scroll` variant: no wrap, scrolls sideways (use where a second line would push content down, such as a filter row on desktop) |
| `.ui-tabs` | row, no wrap | 0 12 px | 4 px | Scrolls sideways when the tabs do not fit; tabs never wrap or truncate |
| `.ui-fold` | summary row; body column | body 0 0 12 px | 12 px | Native `details`, so it works without script |
| `.ui-list-item` | row, no wrap | 8 px 16 px; min height 44 px | 12 px | Title truncates; meta line is 12 px muted; the end slot keeps its size |
| `.ui-empty` | column, centred | 32 px 20 px | 12 px | Text wraps at 36 characters |
| `.ui-toast` | row | 12 px 16 px | 12 px | Max 420 px wide or the viewport minus 32 px; text wraps |

## Motion

| Change | Animation | Duration and easing |
|---|---|---|
| Tab selected | Indicator grows (`scaleX`) | 200 ms, standard |
| Fold opened | Chevron rotates | 200 ms, standard. The body appears without animation (native `details`), on purpose |
| Interactive card hover | Shadow and border | 120 ms |
| Toast in and out | Fade plus 8 px rise | 200 ms, decelerate |

## Tests

`tools/ui_kit_check.mjs` covers padding and gaps against this table, tab keyboard behaviour, and toast timing.

## Changelog

| Version | App version | Change |
|---|---|---|
| 0.1.0 | none (standalone) | First version, D-32 Stage A. |
| 0.1.1 | 3.1.0-P81 | Same spacing-token pass as ui-controls 0.1.1. |
