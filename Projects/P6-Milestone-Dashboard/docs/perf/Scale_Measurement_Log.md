# Scale Measurement Log

Figures behind TD-216, TEST-59 and the D-23 to D-29 spec (`docs/specs/D-23_scale-model-and-views.md`). Prose elsewhere names a metric and points here; it never states the figure.

**Append only.** Add rows as measurements are taken. Never edit or delete a prior row; the last row per metric and source is the current figure.

**Sources:**
- `synthetic`: reproducible from the repo with `tools/scale_bench.mjs` (generated schedule, TSV import path). This is the series later stages are compared against.
- `client`: the Eskay Creek live XER (WE 2026-08-14), converted with `tools/xer_to_aoa.py`, imported as `.xlsx` with SheetJS inlined; `client-2x` is the same schedule duplicated with IDs and link references suffixed so the logic stays intact. The file is client data and is **not** in the repo, so these rows cannot be reproduced from it. They are kept because they are the finding that started D-25, and the synthetic series is checked against them for the same scaling shape.
- `reference`: `data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx`, the committed study extract.
- `micro`, `model`, `vendor`: isolated measurements described per row.

All browser timings: headless Chromium in the cloud session container, CPU unthrottled, offline, viewport 1600 x 900. Times in ms unless the metric says otherwise. KB = 1000 bytes. A corporate laptop may be slower; compare rows within this log, not against wall-clock expectations.

## Board scale (v3.1.0-P58)

| Date | Build | Source | Metric | Value | Method |
|---|---|---|---|---|---|
| 2026-09-27 | P58 | reference | rows / activities | 192 / 146 | session harness, real import path |
| 2026-09-27 | P58 | reference | import_ms | 529 | file input, mapper, `runIngest()` to settled board |
| 2026-09-27 | P58 | reference | rebuild_ms (3 runs) | 124, 232, 292 | `rerender(true)` plus forced layout |
| 2026-09-27 | P58 | reference | filter_0d_ms | 330 | `setFloatPreset('0d')` to settled |
| 2026-09-27 | P58 | reference | dep_all_on_ms | 684 | `setAllDep` pred and succ on, to settled |
| 2026-09-27 | P58 | reference | dom_elements | 8718 | `getElementsByTagName('*')` |
| 2026-09-27 | P58 | reference | scroll_fps | 61 | 1.5 s scripted scroll |
| 2026-09-27 | P58 | client | rows / activities / links | 3480 / 2857 / 7032 | `xer_to_aoa.py` output |
| 2026-09-27 | P58 | client | import_ms | 20691 | as reference |
| 2026-09-27 | P58 | client | rebuild_ms (3 runs) | 22140, 12017, 11467 | as reference |
| 2026-09-27 | P58 | client | filter_0d_ms | 3282 | as reference |
| 2026-09-27 | P58 | client | dep_all_on_ms | 30147 | as reference |
| 2026-09-27 | P58 | client | dep_paths | 5708 | `path.dep-line` count |
| 2026-09-27 | P58 | client | rebuild_with_deps_ms | 50672 | `rerender(true)` with all lines on |
| 2026-09-27 | P58 | client | theme_toggle_ms | 4548 | `toggleTheme()` to second frame |
| 2026-09-27 | P58 | client | dom_elements | 445304 | as reference |
| 2026-09-27 | P58 | client | td_cells | 387347 | `#main-table td` |
| 2026-09-27 | P58 | client | week_columns | 204 | cells per data row |
| 2026-09-27 | P58 | client | visible_rows | 20 | rows intersecting the viewport |
| 2026-09-27 | P58 | client | import_layout_s / import_style_s | 4.98 / 7.20 | CDP `LayoutDuration` / `RecalcStyleDuration` delta over import |
| 2026-09-27 | P58 | client | scroll_fps | 46 | as reference |
| 2026-09-27 | P58 | client | heap_mb | 25 | `performance.memory.usedJSHeapSize` |
| 2026-09-27 | P58 | client-2x | rows / activities / links | 6960 / 5714 / 14064 | duplicated, suffixed |
| 2026-09-27 | P58 | client-2x | import_ms | 45991 | as reference |
| 2026-09-27 | P58 | client-2x | rebuild_ms (3 runs) | 35527, 36097, 36559 | as reference |
| 2026-09-27 | P58 | client-2x | filter_0d_ms | 12287 | as reference |
| 2026-09-27 | P58 | client-2x | dep_all_on_ms | 178870 | as reference |
| 2026-09-27 | P58 | client-2x | dep_paths | 11416 | as reference |
| 2026-09-27 | P58 | client-2x | rebuild_with_deps_ms | 269863 | as reference |
| 2026-09-27 | P58 | client-2x | theme_toggle_ms | 8858 | as reference |
| 2026-09-27 | P58 | client-2x | dom_elements | 888235 | as reference |
| 2026-09-27 | P58 | client-2x | import_layout_s / import_style_s | 7.79 / 14.17 | as client |
| 2026-09-27 | P58 | client-2x | scroll_fps | 39 | as reference |
| 2026-09-27 | P58 | client-2x | heap_mb | 35 | as client |

## Rendering shape (isolated)

| Date | Build | Source | Metric | Value | Method |
|---|---|---|---|---|---|
| 2026-09-27 | n/a | micro | microbench_per_week_ms | 14367 | 2053 rows x (8 fixed + 204 week cells), `innerHTML` then forced layout; 439344 elements |
| 2026-09-27 | n/a | micro | microbench_one_cell_ms | 1514 | 2053 rows x (8 fixed + 1 timeline cell, CSS gradient gridlines, absolutely placed marker); 22585 elements |
| 2026-09-27 | n/a | micro | class_toggle_ms | 8 | toggle one class on 2053 rows of the one-cell shape, forced layout |

## Model and views (isolated, Node, client schedule)

| Date | Build | Source | Metric | Value | Method |
|---|---|---|---|---|---|
| 2026-09-27 | n/a | model | xer_table_read_ms | 307 | cp1252 decode and `%T/%F/%R` split of the 4.5 MB XER, all tables |
| 2026-09-27 | n/a | model | view_full_kb / gzip | 116 / 25 | JSON of 624 indent groups plus 2857 activity placements |
| 2026-09-27 | n/a | model | view_delta_kb | 1.9 | JSON of 50 moved activities plus 10 renamed groups |
| 2026-09-27 | n/a | model | view_reconcile_ms | 7.51 | match one view's placements against a new import by ID (5% added, 2% removed) |
| 2026-09-27 | n/a | model | view_switch_flatten_ms | 2.45 | depth-first flatten of the indent tree to row order |

## Vendored library sizes (minified, as fetched from jsDelivr)

| Date | Source | Metric | Value | Notes |
|---|---|---|---|---|
| 2026-09-27 | vendor | vendor_sheetjs_kb | 882 | `xlsx@0.18.5/dist/xlsx.full.min.js`, same version the CDN loads |
| 2026-09-27 | vendor | vendor_d3_full_kb | 280 | `d3@7` bundle |
| 2026-09-27 | vendor | vendor_d3_scales_axes_kb | 75.7 | array, color, format, interpolate, time, time-format, scale, axis |
| 2026-09-27 | vendor | vendor_d3_collision_kb | 17.4 | quadtree, force, dispatch, timer |
| 2026-09-27 | vendor | vendor_d3_zoom_kb | 46.4 | selection, dispatch, drag, ease, timer, transition, zoom |
| 2026-09-27 | vendor | vendor_vis_network_kb | 620 | `vis-network@9` standalone UMD |
| 2026-09-27 | vendor | vendor_mermaid_kb | 3573 | `mermaid@11` |

## Synthetic series (`tools/scale_bench.mjs`)

| Date | Build | Source | Metric | Value | Method |
|---|---|---|---|---|---|
