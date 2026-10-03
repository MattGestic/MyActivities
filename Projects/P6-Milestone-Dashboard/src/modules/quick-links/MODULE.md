# quick-links (`SRETQuickLinks`)

Two named links to where the dashboard's files are kept, checked and normalised (P80, TD-248). Back end only: no DOM, no app global.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Embedded in `src/milestone-dashboard.html`. Run `python3 tools/modules_embed.py --list` for its current app lines. |
| Global | `window.SRETQuickLinks`, also `module.exports` where defined. No other global is set. |
| Requires | none |
| Uses when loaded | none |

## Interface

The header comment of `quick-links.js` is the API reference: `normaliseUrl()`, `normalise()`, `label()`, `MAX`, `TITLE_MAX`.

Any UI uses the app adapter (`quickLinksGet`, `quickLinksSet`, the `sret:quicklinks` event), not this module. Contract: `docs/decisions/D-31-continue-from-saved.md` §8.

## Files and placement

Files: `quick-links.js`

- **js:** slot `app-script-modules`, order 60; pasted: `quick-links.js`

## Tests

- `tools/quick_links_test.mjs`: the module alone, in Node.
- `tools/p80_quick_links_check.py`: the blank app, a saved blank copy, and continue from a saved file, in the browser.

## Rules for this module

- **Only http:, https: and file: addresses are allowed.** A saved file is opened by people other than whoever typed the link, so a `javascript:` or `data:` address would run in their page. The app re-checks the links with `normalise()` whenever a file is loaded, so a hand-edited file cannot plant one either (`p80_quick_links_check.py`, D).
- **A Windows path becomes a file: URL** (`C:\...` and `\\server\share\...`), because that is what people copy from Explorer.

## Changing this module

1. Edit only the files in this folder. Never edit its region in the app: `modules_embed.py --check` reports that as TAMPERED.
2. Run the tests above.
3. Bump `version` in `MODULES.json` (major: interface change, with a migration note below and the app adapter updated in the same change; minor: additive; patch: fix) and add a changelog row.
4. Run `python3 tools/modules_embed.py --embed quick-links`, then `python3 tools/run_checks.py`.

## Changelog

| Version | App version | Change |
|---|---|---|
| 1.0.0 | 3.1.0-P80 | P80 (TD-248): first version, embedded. |
