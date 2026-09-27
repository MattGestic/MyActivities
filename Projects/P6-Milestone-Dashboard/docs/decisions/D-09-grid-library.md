# D-09 Grid library for the table view

**Status:** Recommended, prototype built on it. **Final pick [CONFIRM WITH MATT].**
**Date:** 2026-09-27. **Branch:** `claude/sret-grid-view`.
**Direction (Matt, 2026-09-27):** a grid-like interface on its own screen, used for annotation collections, user milestones and loaded schedule activities, built on a lightweight template available online rather than a component developed from scratch.

## Recommendation

**SlickGrid 5.20.2 (MIT), vendored as a six-file subset, minified once at vendoring time.** Tabulator 6.5.3 is the fallback if Matt prefers fewer lines in our wrapper over a smaller file.

Why SlickGrid over Tabulator, which FEAT-23 had pencilled in:

1. **Half the inline weight.** The subset the grid needs is 217 KB minified (54 KB gzip) against Tabulator's 477 KB (106 KB gzip). In a single file with no caching split, that is the difference between the app growing by about a quarter and by about a half.
2. **Keyboard model is the product, not an add-on.** Arrow keys, Tab, Enter to edit, Enter to commit, Esc to cancel, and the edit lock that guarantees one editor at a time, all out of the box. Tabulator gets there through `selectableRange` plus keybinding configuration.
3. **Virtual rendering is its core design** (rows are absolutely positioned and recycled). 2,000 rows measured at 33 ms to open with 36 rows in the DOM (`tools/grid_view_check.py`).
4. **No theme to fight.** We vendor only the structural stylesheet and skin it entirely from `--color-*` roles. Tabulator's stylesheet paints with literal colours throughout (its CSS has no custom properties), so every rule would need overriding anyway.

What SlickGrid does not ship, and our wrapper supplies (all inside `src/modules/grid-view/grid-view.js`): header filter inputs, quick search, `.xlsx` export via SheetJS, the four editors (native text, number, date and select inputs, which also removes the Flatpickr dependency of its own date editor), the screen chrome and the callbacks. That is the trade: a thicker wrapper for a much smaller vendored engine.

## Comparison

Sizes are measured from the distributed npm tarballs downloaded 2026-09-27, `gzip -9`. "Inline bytes" is what would be pasted into the HTML file.

| Criterion | **SlickGrid 5.20.2** | Tabulator 6.5.3 | Grid.js 6.2.0 | AG Grid Community 36.2.0 | RevoGrid 4.28.1 |
|---|---|---|---|---|---|
| Licence | MIT | MIT | MIT | MIT (Community); Enterprise features commercial | MIT |
| Inline bytes, what we'd use | **221,778** (subset JS min 217,423 + structural CSS 4,355) | 476,876 (min JS 448,396 + min CSS 28,480) | 60,952 (UMD min incl. Preact + theme CSS) | 2,058,454 (min, styles in JS) | 890,563 across lazy-loaded chunks |
| Gzip of the above | **54,817** | 105,475 | 19,049 | 521,163 | 199,215 |
| As distributed, unminified subset | 462,366 (browser builds are not minified) | 809,045 | n/a | n/a | n/a |
| Runtime dependencies | None used (SortableJS only for column drag reorder, left off) | None | Preact (bundled in UMD) | ag-stack, ag-charts-types | None, but Stencil lazy loader expects chunk files |
| Single-file inlining | Yes (plain IIFE browser builds) | Yes (UMD) | Yes | Yes, but size rules it out | **No**: chunks are fetched by URL at runtime |
| Inline editing | Yes (engine); editors supplied by us | Yes, built-in editors | **No** | Yes | Yes |
| Sorting | Yes | Yes | Yes | Yes | Yes |
| Header / column filters | Engine gives a header row; filter inputs are ours | Built-in `headerFilter` | Global search only | Yes | Yes |
| Row selection with checkboxes | Yes (plugin, vendored) | Yes (`rowHeader` + `rowSelection`) | Separate plugin package | Yes | Partial |
| Keyboard navigation and edit | **Full spreadsheet model** | Partial by default; range selection mode adds it | No | Full | Full |
| Virtual rendering | **Yes, core design** | Yes (virtual DOM renderer) | **No** (pagination) | Yes | Yes |
| Column resize | Yes | Yes | Yes | Yes | Yes |
| `.xlsx` export | Ours, via SheetJS (`ensureXLSX()`) | Built-in, via global SheetJS | No | Enterprise only | Plugin |
| Theming through CSS variables | Partial (its alpine theme uses `--alpine-*` with literal fallbacks); we skip the theme and use our roles | **None** in `tabulator.css` (literal colours throughout) | None in `mermaid.css` | Yes (theming API) | Yes |
| Accessibility | ARIA roles grid, row, gridcell, columnheader; thin `aria-*` use. Wrapper adds labels on filters, editors, toolbar | Stronger: roles plus 22 `aria-*` uses | Roles, no editing | Strong | Moderate |
| Maintenance | Active; 5.20.2 published 2026-09-17; project since 2013 | Active; 6.5.3 published 2026-09-15 | Last release 2024-03-03 | Active; 2026-09-16 | Active; 2026-09-22 |
| Verdict | **Recommended** | Fallback | Fails must-haves (editing, virtual) | Too large | Cannot inline |

Excluded on licence before measuring: **Handsontable** (registry licence field "SEE LICENSE IN LICENSE.txt", proprietary since v7), **simple-datatables** (LGPL-3.0). Both fail the MIT/BSD/Apache rule.

Assumption flagged: accessibility and capability rows come from the shipped source (grep of roles, attributes, option names) plus the libraries' documented options, not from an assistive-technology test. A screen-reader pass on the prototype is still owed.

**Scroll finding (Matt's review, 2026-09-27: "not smooth, stutters").** Two SlickGrid defaults caused it, both measured on the 2,000-row set before the fix. (1) `enableMouseWheelScrollHandler` (on by default, meant for frozen columns) moved `scrollTop` itself on each wheel tick, in whole-row steps and against the native scroll (one downward tick moved it -11 px). (2) The 10 ms scroll-render throttle left 285 visible rows blank across 10 fast scrolls. The wrapper now turns the handler off, renders synchronously, positions rows with transforms and keeps a larger row buffer: 0 blank rows, 0 wheel interference, p95 render cost under 2 ms per step. `tools/grid_view_check.py` asserts all four. Anyone switching to Tabulator should re-run the same scroll assertions, since they test behaviour, not SlickGrid options.

## Size and licence impact on the single file

| | Bytes | Gzip |
|---|---|---|
| App today (`src/milestone-dashboard.html`, base `81cfd7a`) | 878,041 | 236,950 |
| Added: vendored engine (min JS + structural CSS) | 221,778 | 54,817 |
| Added: our wrapper and the shared lists module (`grid-view.js`, `grid-view.css`, `collections.js`) | 50,429 | 14,966 |
| **Total added (before app adapters)** | **272,207 (about 31% of today's file)** | 69,783 |

Tabulator for comparison would add about 477 KB plus a smaller wrapper, roughly 57%.

Licence obligation: MIT requires the copyright and permission notice to travel with the code. At merge the vendored block keeps the esbuild `--legal-comments=inline` banners and gains the full MIT text as a comment at the top of the vendor `<script>` (see `docs/grid-view-integration.md`). `vendor/slickgrid/LICENSE` is the source of that text.

## Constraint change (applied 2026-09-28, Matt)

`CLAUDE.md`, Hard constraints, today:

> - Single self-contained HTML file. **No npm, no build step, no bundler, no framework.**
> - Only external dependency is an on-demand CDN load of SheetJS for `.xlsx` import. Nothing else.

Proposed:

> - Single self-contained HTML file. **No npm, no build step, no bundler, no framework** in the app. Third-party code is allowed only as a **vendored inline block**: MIT, BSD or Apache licensed, recorded in `vendor/<lib>/SOURCE.md` with version, URL and sha256, licence text carried in the block, loaded from no network location. Current vendored blocks: SlickGrid (D-09).
> - Only external **network** dependency is an on-demand CDN load of SheetJS for `.xlsx` import and export. Nothing else.

Two sign-off points inside that wording:
1. **Vendoring third-party code at all.** Matt's direction on 2026-09-27 covers it; this records it.
2. **The one-time minify.** SlickGrid ships readable, unminified browser files. Inlining them as-is costs 462 KB instead of 222 KB. The minified file is produced once at vendoring time with a pinned `npx esbuild@0.24.0` command (recorded in `SOURCE.md`); the app is never built. If that reads as a build step, the alternative is to inline the unminified files and accept the extra 240 KB. **[CONFIRM WITH MATT]**

The colour rules need no change: vendored CSS sits in its own `<style id="vendor-slickgrid-css">` block, which `tools/colour_audit.py --strict` does not scan (it reads the first `<style>` only), and every colour it could paint is overridden by the tokenised skin. That is proven at runtime, not by reading: `tools/grid_view_check.py` runs a palette swap across the whole grid screen in idle, editing and confirm states in both themes, and `tools/palette_swap_check.py` passes on the demo.

## Decisions needed from Matt

1. SlickGrid (recommended) or Tabulator. **[CONFIRM WITH MATT]**
2. Minified vendored block (222 KB) or unminified (462 KB). **[CONFIRM WITH MATT]**
3. ~~Apply the constraint wording~~ **Done 2026-09-28.** Matt widened it: third-party code only when permissively licensed and embedded in the file, never loaded from the internet, and SheetJS is to be embedded too (TD-216). The applied wording is in `CLAUDE.md`, Hard constraints; the proposal above is kept as history.
