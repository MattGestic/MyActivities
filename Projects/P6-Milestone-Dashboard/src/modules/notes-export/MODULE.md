# notes-export (`SRETNotesExport`)

Entry array to the two-sheet notes workbook (Summary, Log). Pure.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Standalone: built and tested outside the app, not yet pasted in. |
| Global | `window.SRETNotesExport`, also `module.exports` where defined. No other global is set. |
| Requires | none |
| Uses when loaded | none |

## Interface

The header comment of `notes-export.js` is the API reference (signatures, inputs, outputs). Keep it current with every change.

## Files and placement

Files: `notes-export.js`

- Not embedded. Used by `prototypes/grid-view/demo.html` (assembled by `tools/grid_view_assemble.py`).

## Tests

Run these on the module alone before embedding; after `--embed`, `tools/run_checks.py` selects the app checks.

- `tools/notes_export_test.mjs`

## Changing this module

1. Edit only the files in this folder. Never edit its region in the app: `modules_embed.py --check` reports that as TAMPERED.
2. Run the tests above.
3. Bump `version` in `MODULES.json` (major: interface change, with a migration note below and the app adapter updated in the same change; minor: additive; patch: fix) and add a changelog row.
4. `python3 tools/modules_embed.py --embed notes-export` if embedded, then `python3 tools/run_checks.py`.

## Changelog

| Version | App version | Change |
|---|---|---|
| 0.1.0 | 3.1.0-P75 | standalone baseline as at app 3.1.0-P75; becomes 1.0.0 when first embedded in a release (D-30). |
| 0.2.0 | 3.1.0-P78 | P78 (TD-244): people field labels; `pred:`/`succ:` prefix stripped from dependency remark keys. Changed in the app before D-30 was merged; versioned when the two met. |
