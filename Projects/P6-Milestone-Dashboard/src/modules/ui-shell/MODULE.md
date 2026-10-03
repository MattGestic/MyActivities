# ui-shell (`SRETShell`)

The external containers of an app screen (D-31): nav (left), header (command bar), main (content) and aside (right). It knows nothing about the app's data. It decides how the nav and aside behave at the current width.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` |
| Status | Standalone (D-31 Stage A) |
| Global | `window.SRETShell`, also `module.exports` |
| Requires | `ui-tokens` |

## Interface

The header comment of `ui-shell.js` is the API reference (`mount`, `layoutFor`, controller methods, the `ui-shell:change` event).

Markup:
```html
<div class="ui-shell ui-root">
  <aside class="ui-shell__nav">…nav goes here…</aside>
  <header class="ui-shell__header ui-on-brand">
    <div class="ui-shell__header-start">
      <button class="ui-btn ui-btn--ghost ui-btn--icon ui-shell__menu">…</button>
      <span class="ui-shell__title">…</span>
    </div>
    <div class="ui-shell__header-end">…actions…</div>
  </header>
  <main class="ui-shell__main">…</main>
  <aside class="ui-shell__aside">…</aside>
</div>
```
The host gives `.ui-shell` a height, for example `height: 100dvh`.

## Page variant

For a host whose document scrolls (the dashboard app keeps the body as the page scroller for sticky table headers and print preview):

```js
SRETShell.mount(document.body, { variant: 'page', nav: navHostEl, inert: () => [contentEls] })
```

- The host element gets class `.ui-shell-page` and the same `data-*` state attributes.
- The nav region is fixed at the left, with the same widths and drawer and overlay behaviour as the grid variant.
- `--ui-nav-col` (240, 60 or 0 px) is written on `<html>`. The host offsets its own content with it, for example `body { margin-left: var(--ui-nav-col) }`.
- The width bands use the viewport width.

## Behaviour by width

| Band | Nav | Aside | Scrim |
|---|---|---|---|
| Phone, up to 640 px | Off-canvas drawer (288 px or 86 vw). Opened by the header menu button. | Overlay from the right, full width up to 380 px | Yes, while the drawer or aside is open |
| Tablet, 641 to 1024 px | Icon rail (60 px). Expanding it slides the full nav over the content. | Overlay | Yes, while the expanded nav or aside is open |
| Desktop, from 1025 px | The user's choice: expanded (240 px) or rail (60 px). Remembered through `opts.persist`. | Pushes the content (380 px) | No |

When the drawer or overlay nav is up, the header and main are marked `inert`, so keyboard focus cannot reach what is behind the scrim. Esc closes the topmost overlay, and so does a scrim click.

## Layout contract

| Region | Direction and wrap | Padding | Gap | Overflow and content |
|---|---|---|---|---|
| `.ui-shell` | CSS grid: columns nav, main, aside; rows header, body | none | none | `overflow: hidden`; regions scroll, never the page |
| `__nav` | column, no wrap | none (the nav component pads itself) | none | `overflow: hidden`; the nav's own list scrolls |
| `__header` | row, **no wrap** | 0 `--ui-gutter` inline | `--ui-space-3` | `overflow: hidden`. The start group (`flex: 1 1 auto; min-width: 0`) shrinks first and the title truncates with an ellipsis. The end group never shrinks, so on narrow screens hosts move secondary actions into a More menu instead of letting them wrap. |
| `__main` | block | `--ui-gutter` (16 px phone and tablet, 24 px desktop); `data-flush` removes it for full-bleed content such as a board | none | `overflow: auto`; scroll stays inside main |
| `__aside` | column, no wrap | none (the panel component pads itself) | none | `overflow: hidden`; the panel body scrolls |

## Motion

| Change | Animation | Duration and easing |
|---|---|---|
| Nav expanded and rail (desktop) | Grid column width | 200 ms, standard |
| Drawer or overlay opens | Slide in (transform) | 240 ms, decelerate |
| Drawer or overlay closes | Slide out | 200 ms, accelerate |
| Aside push open and close | Grid column width | 200 ms, standard |
| Scrim | Fade | 200 ms, standard |

All within budget: one animation per action and no stagger. Nothing animates at boot: transitions wait for `data-ui-ready`, set two frames after mount, so a page that opens on a phone or on the rail does not slide in from the default width. Page-variant hosts gate their own offset transition the same way (`body:not([data-ui-ready])`). The content does not reflow when a milestone is selected, only when the aside or nav changes width.

## Tests

- `tools/ui_kit_test.mjs`: `layoutFor` across the band edges.
- `tools/ui_kit_check.mjs`: the gallery at 390, 768 and 1440.

## Changelog

| Version | App version | Change |
|---|---|---|
| 0.1.0 | none (standalone) | First version, D-31 Stage A. |
| 0.2.0 | 3.1.0-P79 | No motion before `data-ui-ready` (boot). Page variant (`variant:'page'`, class `.ui-shell-page`) for hosts whose document scrolls: fixed nav, `--ui-nav-col` written on `<html>` for the host to offset its content. Esc listener in the capture phase, stops the event only when it closed something. |
