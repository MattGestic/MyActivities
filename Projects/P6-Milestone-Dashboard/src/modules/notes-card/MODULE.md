# notes-card (`SRETFormToEntry`)

Milestone card save reduced to one entry draft (P65, M5). Pure.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Embedded in `src/milestone-dashboard.html`. Run `python3 tools/modules_embed.py --list` for its current app lines. |
| Global | `window.SRETFormToEntry`, also `module.exports` where defined. No other global is set. |
| Requires | none |
| Uses when loaded | `notes-store` |

## Interface

The header comment of `form-to-entry.js` is the API reference (signatures, inputs, outputs). Keep it current with every change.

## Files and placement

Files: `form-to-entry.js`

- **js:** slot `app-script-modules`, order 30; pasted: `form-to-entry.js`

## Tests

Run these on the module alone before embedding; after `--embed`, `tools/run_checks.py` selects the app checks.

- `tools/form_to_entry_test.mjs`

## Changing this module

1. Edit only the files in this folder. Never edit its region in the app: `modules_embed.py --check` reports that as TAMPERED.
2. Run the tests above.
3. Bump `version` in `MODULES.json` (major: interface change, with a migration note below and the app adapter updated in the same change; minor: additive; patch: fix) and add a changelog row.
4. `python3 tools/modules_embed.py --embed notes-card` if embedded, then `python3 tools/run_checks.py`.

## Changelog

| Version | App version | Change |
|---|---|---|
| 1.0.0 | 3.1.0-P75 | first embedded before D-30; baseline as at app 3.1.0-P75 (D-30). |
| 1.1.0 | 3.1.0-P78 | P78 (TD-244): the three people fields map from the card; dash normalising written as escapes. Additive. Changed in the app before D-30 was merged; versioned when the two met. |
