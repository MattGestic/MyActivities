# notes-history (`SRETHistory`)

Update history gallery for the milestone card and Notes panel (P66, M6).

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Embedded in `src/milestone-dashboard.html`. Run `python3 tools/modules_embed.py --list` for its current app lines. |
| Global | `window.SRETHistory`, also `module.exports` where defined. No other global is set. |
| Requires | none |
| Uses when loaded | none |

## Interface

The header comment of `notes-history.js` is the API reference (signatures, inputs, outputs). Keep it current with every change.

## Files and placement

Files: `notes-history.js`, `notes-history.css`

- **js:** slot `app-script-modules`, order 40; pasted: `notes-history.js`
- **css:** slot `style-modules`, order 10; pasted: `notes-history.css`

## Tests

Run these on the module alone before embedding; after `--embed`, `tools/run_checks.py` selects the app checks.

- `tools/notes_history_check.py`
- `tools/p66_check.py`

## Changing this module

1. Edit only the files in this folder. Never edit its region in the app: `modules_embed.py --check` reports that as TAMPERED.
2. Run the tests above.
3. Bump `version` in `MODULES.json` (major: interface change, with a migration note below and the app adapter updated in the same change; minor: additive; patch: fix) and add a changelog row.
4. `python3 tools/modules_embed.py --embed notes-history` if embedded, then `python3 tools/run_checks.py`.

## Changelog

| Version | App version | Change |
|---|---|---|
| 1.0.0 | 3.1.0-P75 | first embedded before D-30; baseline as at app 3.1.0-P75 (D-30). |
| 1.1.0 | 3.1.0-P78 | P78 (TD-244): labels for the three people fields. Additive. Changed in the app before D-30 was merged; versioned when the two met. |
