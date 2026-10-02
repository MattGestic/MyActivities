# notes-store (`SRETEntries`)

The append-only entry record behind every milestone update (P65); the app's stores are projections of it.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Embedded in `src/milestone-dashboard.html`. Run `python3 tools/modules_embed.py --list` for its current app lines. |
| Global | `window.SRETEntries`, also `module.exports` where defined. No other global is set. |
| Requires | none |
| Uses when loaded | none |

## Interface

`INTERFACE.md` in this folder is the contract.

## Files and placement

Files: `notes-store.js`

- **js:** slot `app-script-modules`, order 20; pasted: `notes-store.js`

## Tests

Run these on the module alone before embedding; after `--embed`, `tools/run_checks.py` selects the app checks.

- `tools/notes_store_test.mjs`
- `tools/p65_check.py`

## Changing this module

1. Edit only the files in this folder. Never edit its region in the app: `modules_embed.py --check` reports that as TAMPERED.
2. Run the tests above.
3. Bump `version` in `MODULES.json` (major: interface change, with a migration note below and the app adapter updated in the same change; minor: additive; patch: fix) and add a changelog row.
4. `python3 tools/modules_embed.py --embed notes-store` if embedded, then `python3 tools/run_checks.py`.

## Changelog

| Version | App version | Change |
|---|---|---|
| 1.0.0 | 3.1.0-P75 | first embedded before D-30; baseline as at app 3.1.0-P75 (D-30). |
| 1.1.0 | 3.1.0-P78 | P78 (TD-244): `discipline`, `supervisor`, `engineer` join `MS_FIELDS`. Additive. Changed in the app before D-30 was merged; versioned when the two met. |
