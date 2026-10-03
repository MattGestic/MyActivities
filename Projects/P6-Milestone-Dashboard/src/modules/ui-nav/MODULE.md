# ui-nav (`SRETNav`)

The generic left navigation panel (D-32). It renders from a config of groups and items and calls the host back when an item is chosen. It has no knowledge of the app's data; counts arrive as badges from the host.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` |
| Status | Embedded in the app from v3.1.0-P81 (D-32 Stage A). `python3 tools/modules_embed.py --list` gives its current lines. |
| Global | `window.SRETNav`, also `module.exports` |
| Requires | `ui-tokens`, `ui-icons`; `ui-controls` for the drawer close button |
| Works with | `ui-shell`: pass `opts.shell` and the nav follows its mode and context |

## Interface

The header comment of `ui-nav.js` is the API reference: config shape, `mount`, `setActive`, `setBadge`, `setMode`, `setContext`, `update`.

## Modes and context

| Shell state | Nav mode | Context | What the user sees |
|---|---|---|---|
| Desktop expanded | expanded | docked | Icons, labels, group labels, badges, a Collapse control |
| Desktop rail | rail | docked | Icons only; badges become 8 px dots; labels show as tooltips on hover and keyboard focus; the control reads Expand |
| Tablet rail | rail | docked | Same as desktop rail; Expand slides the full nav over the content |
| Tablet expanded | expanded | overlay | Full nav over the content, with a scrim |
| Phone | expanded | drawer | Full nav as a drawer with a close button; no Collapse control |

## Layout contract

| Part | Direction and wrap | Padding | Gap | Content behaviour |
|---|---|---|---|---|
| `.ui-nav` | column, no wrap | 12 px 8 px | 4 px | Fills the shell nav region |
| `__brand` | row, no wrap; min height 44 px | 0 8 px 8 px | 12 px | Title and subtitle truncate with an ellipsis |
| `__scroll` | column, no wrap | none | 8 px between groups | Scrolls vertically when the groups are taller than the panel; never scrolls sideways |
| `__group` | column | none | 2 px between items | A divider (1 px with 4 px 8 px margin) sits between groups |
| `__label` | row, no wrap; 28 px high | 0 12 px | 8 px | 11 px uppercase. In rail mode it collapses to a 9 px spacer |
| `__item` | row, no wrap; 40 px high | 0 12 px; sub-items indent to the label line | 12 px | Label truncates with an ellipsis; the badge never shrinks |
| `__footer` | column, no wrap | 8 px top, plus a 1 px top border | 2 px | Pinned below the scroll area |

## Motion

| Change | Animation | Duration and easing |
|---|---|---|
| Expanded and rail | The shell animates the width; labels fade | 200 ms width; 120 ms fade |
| Active item | The left accent bar grows (`scaleY`); background tint | 200 ms and 120 ms |
| Group collapse | Row track animates from 1fr to 0fr (no height jump); chevron rotates | 200 ms, standard |
| Rail tooltip | Fade plus 4 px slide | 120 ms |
| Hover | Background tint | 120 ms |

Within budget. **Flag:** the group-collapse animation is the most involved effect in the nav. If it ever stutters on a slow device, drop it to an instant toggle. It is decoration, not function.

## Accessibility

- A `nav` landmark with `aria-label`.
- The active item has `aria-current="page"`.
- Collapsible group labels are buttons with `aria-expanded`.
- Arrow Up and Down, Home and End move between visible items.
- The drawer close button has an `aria-label`.

## Tests

`tools/ui_kit_check.mjs`: mode and context per band, the tooltip in rail, keyboard movement, badge update, the collapse callback, padding and gaps against this table, and no horizontal overflow.

## Changelog

| Version | App version | Change |
|---|---|---|
| 0.1.0 | none (standalone) | First version, D-32 Stage A. |
| 0.1.1 | 3.1.0-P81 | `setActive(null)` clears the current item. Spacing literals moved onto `--ui-space-0` and `--ui-space-1`. |
