# grid-view (`SRETGrid`)

Full-screen table view (D-09): core plus optional features, configured once with SRETGrid.setup().

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Embedded in `src/milestone-dashboard.html`. Run `python3 tools/modules_embed.py --list` for its current app lines. |
| Global | `window.SRETGrid`, also `module.exports` where defined. No other global is set. |
| Requires | none |
| Uses when loaded | `collections`, `ms-import`, `dates` ; vendor `vendor/slickgrid/` |

## Interface

The header comment of `grid-view.js` is the API reference (signatures, inputs, outputs). Keep it current with every change. Integration and the `setup()` settings: `docs/grid-view-integration.md` §6.

## Files and placement

Files: `grid-view.js`, `features/marks.js`, `features/bulk-edit.js`, `features/xlsx.js`, `features/import.js`, `features/lists.js`, `features/refs.js`, `grid-view.css`, `features/marks.css`, `features/bulk-edit.css`, `features/import.css`, `features/lists.css`, `features/refs.css`

- **css:** slot `style-end`, order 10; pasted: `grid-view.css`, `features/marks.css`, `features/bulk-edit.css`
- **js:** slot `app-script-modules`, order 10; pasted: `grid-view.js`, `features/marks.js`, `features/bulk-edit.js`, `features/xlsx.js`
- **Not pasted** (used by the prototype only): `features/import.js`, `features/lists.js`, `features/refs.js`, `features/import.css`, `features/lists.css`, `features/refs.css`

## Tests

Run these on the module alone before embedding; after `--embed`, `tools/run_checks.py` selects the app checks.

- `tools/grid_view_check.py`
- `tools/grid_view_modular.py`
- `tools/grid_view_responsive.py`
- `tools/p61_check.py`

## Changing this module

1. Edit only the files in this folder. Never edit its region in the app: `modules_embed.py --check` reports that as TAMPERED.
2. Run the tests above.
3. Bump `version` in `MODULES.json` (major: interface change, with a migration note below and the app adapter updated in the same change; minor: additive; patch: fix) and add a changelog row.
4. `python3 tools/modules_embed.py --embed grid-view` if embedded, then `python3 tools/run_checks.py`.

## Changelog

| Version | App version | Change |
|---|---|---|
| 1.0.0 | 3.1.0-P75 | first embedded before D-30; baseline as at app 3.1.0-P75 (D-30). |
