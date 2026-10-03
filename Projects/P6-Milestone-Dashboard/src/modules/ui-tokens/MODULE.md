# ui-tokens

The one shared styling resource for the SRET UI kit (D-32). Every `ui-*` module reads only these custom properties.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Embedded in the app from v3.1.0-P81 (D-32 Stage A). `python3 tools/modules_embed.py --list` gives its current lines. |
| Global | none (CSS only) |
| Requires | none |
| Theme | Light only for now. Dark is a later slot. |

## What it defines

| Group | Tokens | Notes |
|---|---|---|
| Palette | `--pal-*` | Supplied by the host. The app supplies them in its two `html[data-theme]` blocks (P55). Standalone hosts load `ui-palette.css` (a copy of the app's light palette, the only literal colours in the kit). `ui-tokens.css` itself holds no literal colour. |
| Colour roles | `--ui-bg-*`, `--ui-text*`, `--ui-border*`, `--ui-accent*`, `--ui-brand*`, `--ui-on-brand*`, `--ui-ok/warn/danger*`, `--ui-scrim`, `--ui-focus` | Components use roles, never `--pal-*` directly. |
| Spacing | `--ui-space-0..8` = 2, 4, 8, 12, 16, 20, 24, 32, 40 px; `--ui-gutter` | Gutter is 16 px on phone and tablet, 24 px from 1025 px. |
| Type | `--ui-font`, `--ui-font-mono`, `--ui-text-xs..2xl` with matching `--ui-lh-*`, weights, `--ui-tracking-label` | 11, 12, 13, 14, 16, 20 px. Body is 13/20. |
| Shape | `--ui-radius-sm/md/lg/xl/pill` | 4, 6, 8, 12 px. |
| Elevation | `--ui-shadow-1/2/3` | Level 1 cards, 2 popovers, 3 drawers and dialogs (design-standard levels). |
| Controls | `--ui-ctl-h` (32 px, also on touch), `--ui-ctl-h-sm`, `--ui-hit` (40 px), `--ui-icon`, `--ui-icon-sm` | Touch targets reach 40 px through `::after`, never by growing the visible box. |
| Motion | `--ui-dur-fast/base/slow` = 120/200/240 ms; `--ui-ease-standard/enter/exit` | See Motion below. |
| Layers | `--ui-z-nav` up to `--ui-z-toast` | Fixed order: nav, aside, scrim, drawer, dialog, popover, toast. A host may override the values to sit the kit among its own layers (the app does). |
| Shell sizes | `--ui-nav-w-expanded/rail/drawer`, `--ui-header-h`, `--ui-aside-w`, `--ui-nav-col` | 240, 60, 288, 52, 380 px. `--ui-nav-col` is the nav column in use, written by `SRETShell`. |
| Breakpoints | documented constants | Phone up to 640, tablet 641 to 1024, desktop from 1025, wide from 1280. CSS cannot read variables in media queries, so each module repeats these numbers. |

## Layout contract

| Rule | Value |
|---|---|
| Who owns spacing | Containers own their padding. Children never set outer margins; siblings are spaced with `gap`. |
| Text in flex rows | Every flex child that holds text gets `min-width: 0`, so it can truncate or wrap instead of pushing its row wider. |
| Long content | Scrolls inside its region. The page itself never scrolls sideways. |
| `.ui-root` | Sets `box-sizing: border-box`, the font, body size and colour, and the focus ring for everything inside it. |

## Motion

| Use | Duration | Easing | Industry reference |
|---|---|---|---|
| Hover, toggles, small state changes | 120 ms (`--ui-dur-fast`) | standard | Material 3 "short", Fluent "faster" |
| Panels, nav width, exits | 200 ms (`--ui-dur-base`) | exit: accelerate | Material 3 "medium", Fluent "normal" |
| Drawers and dialogs entering | 240 ms (`--ui-dur-slow`) | enter: decelerate | Material 3 "medium", Fluent "slow" |

Budget for every module:
- One animation per user action.
- No staggers or chained sequences.
- No motion on data.
- Only transform and opacity animate, except deliberate width changes (nav, pinned aside).

The OS "reduce motion" accessibility setting sets every duration to 0 automatically. There is no control for it in the UI.

## Changelog

| Version | App version | Change |
|---|---|---|
| 0.1.0 | none (standalone) | First version, D-32 Stage A. |
| 0.2.0 | 3.1.0-P81 | Literal palette moved to `ui-palette.css`, loaded only by standalone hosts; in the app the roles resolve to its own `--pal-*` blocks (P55), so `colour_audit --strict` is unaffected. Touch control height 32 px (design-standard), hit area stays 40 px. Layer tokens documented as host-overridable. `--ui-nav-col` default added. `--ui-space-0` (2 px) added; `.ui-visually-hidden` drops its -1px margin. |
