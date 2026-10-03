# ui-controls (`SRETControls`)

The form and action controls (D-31): button variants, text input, textarea, select, field, field grid, switch, segmented control, radio cards, chips, badges and counts. The markup carries state in ARIA attributes, and `SRETControls.bind` keeps it in step and emits events.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` |
| Status | Standalone (D-31 Stage A) |
| Global | `window.SRETControls`, also `module.exports` |
| Requires | `ui-tokens`; `ui-icons` where a control shows an icon |

## Interface

The header comment of `ui-controls.js` is the API reference. Events: `ui-change` (`detail.id`, `detail.value`) and `ui-remove`.

## Layout contract

| Control | Size | Padding | Content behaviour |
|---|---|---|---|
| `.ui-btn` | Height `--ui-ctl-h` (32 px; 40 px on touch); hit area at least 40 px | 0 12 px; 8 px gap between icon and label | Label never wraps (`nowrap`). Put buttons in a wrapping row (`.ui-card__footer`, `.ui-toolbar`) so they move to the next line rather than squeeze |
| `.ui-btn--icon` | Square, `--ui-ctl-h` | none | Needs an `aria-label` |
| `.ui-input`, `.ui-select` | Height `--ui-ctl-h`; full width of their field | 0 12 px | `min-width: 0`, so they shrink in grids. Long values scroll inside the box |
| `.ui-textarea` | Min 80 px, grows by vertical resize | 8 px 12 px | Text wraps |
| `.ui-field` | column | none; gap 4 px | Label 12 px. Help and error text wrap |
| `.ui-field-grid` | 2 columns, 1 column at 640 px and below | none; gap 12 px rows, 16 px columns | `--full` spans both columns |
| `.ui-switch` | 36 by 20 px visible; 40 px hit area | none | Pair it with `.ui-switch-row` (label left and truncates, switch right; min height 40 px) |
| `.ui-segmented` | Options at `--ui-ctl-h` minus 4 px | 2 px track, 0 12 px option | No wrap; keep to 2 to 4 short options |
| `.ui-radio-cards` | Auto-fit columns, min 220 px each | 12 px 16 px | Wraps to one column on phones; description text wraps |
| `.ui-chips` | row, **wraps** | none; gap 8 px | Chip label truncates at the row width (`max-width: 100%`) |
| `.ui-badge`, `.ui-count` | 20 and 18 px high | 0 8 px and 0 6 px | Never wrap; numbers use tabular figures |

## Motion

| Change | Animation | Duration |
|---|---|---|
| Hover and pressed on buttons, chips, inputs | Colour, border; pressed scales to 0.98 | 120 ms, standard |
| Switch | Thumb slides (`translateX`) | 120 ms |
| Segmented and radio card selection | Background and border | 120 ms |
| Input focus | Border plus a 3 px tint ring | 120 ms |

## Tests

`tools/ui_kit_check.mjs`: control heights, the 40 px hit area, switch and segmented events, the chip remove event, and the field grid going to one column at 390 px.

## Changelog

| Version | App version | Change |
|---|---|---|
| 0.1.0 | none (standalone) | First version, D-31 Stage A. |
| 0.1.1 | 3.1.0-P79 | Sub-scale spacing on the token scale: `--ui-space-0` (2 px) for the segmented track, the count badge padding on `--ui-space-1`. No literal px in padding, margin or gap (the app's spacing_audit). |
