# continue-file (`SRETContinue`)

Reads a previously saved dashboard so a blank copy can continue from it (P79, TD-247). Back end only: finds the saved state in the file's text and checks it. It has no DOM, sets no app global, and never runs the file's scripts.

| Field | Value |
|---|---|
| Version | see `src/modules/MODULES.json` (the only place it is written) |
| Status | Embedded in `src/milestone-dashboard.html`. Run `python3 tools/modules_embed.py --list` for its current app lines. |
| Global | `window.SRETContinue`, also `module.exports` where defined. No other global is set. |
| Requires | none |
| Uses when loaded | none |

## Interface

The header comment of `continue-file.js` is the API reference: `read()`, `extractState()`, `summarise()`, `check()`, `chainOf()` and `compareVersions()`.

Any UI uses the app adapter (`continueRead`, `continueApply`, `continueCancel`), not this module. The adapter contract and the UI hand-off are in `docs/decisions/D-31-continue-from-saved.md`.

## Files and placement

Files: `continue-file.js`

- **js:** slot `app-script-modules`, order 50; pasted: `continue-file.js`

## Tests

Run these on the module alone before embedding. After `--embed`, `tools/run_checks.py` selects the app checks.

- `tools/continue_file_test.mjs`: the module alone, in Node, against real saved files from the repo.
- `tools/p79_continue_check.py`: a save with data in the seeded app, then a continue into the blank app as it ships, at 1440 and 390 wide.

## Rules for this module

- **Only a published-state element whose text opens with the assignment counts.** The app's own source names the element, and so does this file's header comment once embedded. The first version matched the bare tag, so the blank app read as a "damaged" saved file. `continue_file_test.mjs` ("the blank app itself") guards this.
- **Never write a literal script start or end tag here.** The regex spells `<` as `\x3C` because this file is pasted inside the app's script (CLAUDE.md hard constraints; `docs/06-lessons-learned.md`).
- **Never `eval` the state or insert the file into a document.** Parsing text with `JSON.parse` is what makes a picked file inert. `p79_continue_check.py` ("scripts never ran") guards this.

## Changing this module

1. Edit only the files in this folder. Never edit its region in the app: `modules_embed.py --check` reports that as TAMPERED.
2. Run the tests above.
3. Bump `version` in `MODULES.json` (major: interface change, with a migration note below and the app adapter updated in the same change; minor: additive; patch: fix) and add a changelog row.
4. Run `python3 tools/modules_embed.py --embed continue-file`, then `python3 tools/run_checks.py`.

## Changelog

| Version | App version | Change |
|---|---|---|
| 1.0.0 | 3.1.0-P79 | P79 (TD-247): first version, embedded. |
