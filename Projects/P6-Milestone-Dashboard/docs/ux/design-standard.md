# Design standard (D-16)

The one standard every control in the dashboard follows. It replaces per-control sizing decisions, which is how the Top filter bar ended up at one size in P46 and a different, oversized one in P47.

**Basis.** Microsoft's Windows UI kit (Fluent 2, Windows 11), Figma Community file 1440832812269040007. The kit was not readable through the Figma connection (Community pages need duplicating to a `/design/` file first), so the values below are the kit's documented Fluent 2 values. **Cross-check every value against the kit file once a `/design/` link is available**, and record any correction in this file.

**Density.** The board is information-dense, so the app uses Fluent's **compact** density on desktop and Fluent's **standard** density on touch screens. Colours are not imported from Fluent: the app keeps its own colour tokens, and this standard maps roles onto them.

## Tokens

| Token | Value | Fluent basis | App token it maps to |
|---|---|---|---|
| `--ctl-h` | 24px | Compact control height | new |
| `--ctl-h-touch` | 32px | Standard control height | new |
| `--ctl-hit-touch` | 40px | Minimum touch target | new, reached with invisible padding, never by enlarging the visual |
| `--ctl-pad-x` | 8px | Control horizontal padding | `--space-4` |
| `--ctl-gap` | 8px | Gap between controls | `--space-4` |
| `--ctl-gap-tight` | 4px | Gap inside a control, between chips | `--space-2` |
| `--field-label-gap` | 12px | Label to control | `--space-5` |
| `--group-gap` | 16px | Between groups; page gutter | `--space-6` |
| `--radius-ctl` | 4px | Control corner | `--radius-sm` |
| `--radius-overlay` | 8px | Flyout, dialog, card corner | new (`--radius-md` is 6px and stays for existing cards until they are migrated) |
| `--focus-ring` | 2px outer, accent | Focus visual | `--color-accent-purple` |
| `--stroke-ctl` | 1px | Control stroke | `--color-btn-secondary-outline` |
| `--icon` / `--icon-btn` | 16px / 24px (32px touch) | Icon sizing | new |

On `pointer:coarse` the sizing tokens switch in one place: `--ctl-h` takes `--ctl-h-touch` and `--icon-btn` becomes 32px. Nothing else in the file sets a control height.

## Type ramp

Segoe UI Variable first, then the app's existing stack: `'Segoe UI Variable Text','Segoe UI',-apple-system,BlinkMacSystemFont,sans-serif`.

| Role | Size / line height | Weight | App token | Used for |
|---|---|---|---|---|
| Caption | 12 / 16 | 400 | `--text-md` | Control text, field labels, chips |
| Caption strong | 12 / 16 | 600 | `--text-md` | Field labels |
| Body | 14 / 20 | 400 | `--text-lg` | Dialog and card body text |
| Body strong | 14 / 20 | 600 | `--text-lg` | Group titles in panels and dialogs |
| Subtitle | 20 / 28 | 600 | new | Panel titles only |

Board labels, meta lines and fine print keep the existing `--text-xs` / `--text-sm` sizes. The ramp governs controls and panels, not the timeline's marker labels.

**Touch field text is 14px**, not 16. The viewport meta gains `maximum-scale=1`, which stops iOS zooming on focus while still allowing pinch zoom (iOS 10 and later ignore it for pinch).

## Colour roles

| Role | Token |
|---|---|
| Accent (focus, selected chip, primary emphasis) | `--color-accent-purple`, text on panels `--color-accent-ink` |
| Primary button | `--color-btn-primary-*` |
| Secondary button, field stroke | `--color-btn-secondary-*` |
| Icon button hover / pressed | `--color-btn-icon-hover-bg` / `--color-btn-icon-pressed-bg` |
| Field fill | `--color-bg-elevated` |
| Text | `--color-text-primary`; secondary text `--color-text-muted` |
| Danger | `--color-status-crit` |

**Never `--color-text-small` for text on a themed panel.** It is near-black in dark (TD-28).

## Controls

Every size below is a token, never a literal.

| Control | Height | Padding | Radius | Text | Notes |
|---|---|---|---|---|---|
| Primary button | `--ctl-h` | 0 `--ctl-pad-x` | `--radius-ctl` | Caption strong | One per surface |
| Secondary button | `--ctl-h` | 0 `--ctl-pad-x` | `--radius-ctl` | Caption | 1px stroke |
| Icon button | `--icon-btn` square | 0 | `--radius-ctl` | 16px glyph | Borderless; hover and pressed fill only; `aria-label` and `title` |
| Text field | `--ctl-h` | 0 `--ctl-pad-x` | `--radius-ctl` | Caption (14px on touch) | Leading icon: left padding = icon + 4px. Clear button sits inside the right edge; it never widens the field |
| Select, number, date | `--ctl-h` | 0 `--ctl-pad-x` | `--radius-ctl` | Caption | Same box as the text field |
| Chip / toggle chip | `--ctl-h` | 0 `--ctl-pad-x` | pill | Caption | Selected = accent fill with on-accent text; `aria-pressed` |
| Segmented toggle | `--ctl-h` | 0 `--ctl-pad-x` | `--radius-ctl` outer | Caption | Baseline / Update |
| Checkbox / switch | 16px box / 32×16 switch | - | 2px / pill | Caption label | Label is the hit area |
| Group header | - | - | - | Caption strong, uppercase, accent ink | One per group; 16px above, 8px below |

## Field row pattern

| Width | Label | Control | Multi-control fields | Quick buttons |
|---|---|---|---|---|
| ≥ 768px | Inline, left, fixed label column per group | Natural width, min 120px | Side by side, `--ctl-gap` | Same row, after a `--ctl-gap` |
| < 768px | Above, `--ctl-gap-tight` below it | Full width | Share the row evenly | Own row beneath, wrapping as one group |

Groups are separated by `--group-gap` and a 1px hairline. There is no empty space inside a group.

## Touch

- The visual control is `--ctl-h-touch` (32px). The touch area reaches `--ctl-hit-touch` (40px) through padding on the row or a positioned pseudo-element, never by growing the box.
- In-field icons (clear, search) never take a touch-size minimum. Their touch area is a pseudo-element.

## Dates and weeks

- **Week ending day** is a setting (Settings, Defaults, "Week ends on", a Mon to Sun segmented toggle). The default is Sunday, matching the current board. It drives the board's week columns, the week-range picker and the week filter together. Changing it re-buckets milestones into the new weeks. Comments and edits are unaffected.
- **The week-range picker snaps to whole weeks.** It lists week-ending dates grouped by month, not a day calendar. Markers: the selected start and end are accent-filled; the data-date week is outlined; the programme's first and last weeks carry an opening and closing bracket in `--color-text-primary`. No per-week milestone indicator.
- **Closed-state range text** is structured, never a sentence: a muted uppercase tag (`W/E`, `From`, `Until`), dates in semibold, a muted arrow between them, a 1px divider, then a count pill (`8 wks`, `open end`, `open start`). Quick ranges use programme wording ("Rest of programme").
- **Overlays stay inside their frame.** A popover is `box-sizing:border-box`, `max-width` bounded, and its grid columns use `minmax(0,…)` so content wraps rather than spills. Footer buttons grow in height rather than letting text cross the button edge.

## Focus and keyboard

- The same `--focus-ring` on `:focus-visible` everywhere. The mouse never shows it.
- Tab order follows visual order. Esc closes the topmost surface. Enter submits a field.

## How this is verified

`tools/d16_check.py` renders `docs/mockups/D-16/component_sheet.html` (the sign-off sheet referenced above) at each committed width, measures its own full content height rather than guessing one, and diffs the result pixel-for-pixel against the committed PNG in `docs/mockups/D-16/png/`. It fails on a dimension change or on more than 0.1% of pixels differing beyond anti-aliasing tolerance, so a control-sizing regression (a token value change breaking a control's dimensions) fails the diff instead of shipping silently. Run it before merging any change touching control CSS; `--update` re-renders and accepts the current sheet as the new baseline after a reviewed, intentional visual change. This checks the SHEET, not the live app.

`tools/ds_check.py` (built at D-16b, not yet written) is the deeper, live-app companion: it will load the app itself at 390, 768 and 1440 wide, with fine and forced-coarse pointer, in light and dark. For every control class in the table above it will assert:
- computed height equals the token (±0.5px)
- horizontal padding
- border radius
- font-size
- the touch area on coarse pointers: the measured box plus padding or pseudo-element reaches ≥ 40px
- label-to-control gap on desktop
- the full-width rule on phones
- text contrast of at least 4.5:1 for Caption against its surface in both themes

A control with no class in the table fails the check until it is given one.
