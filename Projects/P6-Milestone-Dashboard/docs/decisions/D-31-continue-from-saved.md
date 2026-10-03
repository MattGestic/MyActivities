# D-31: Continue from a saved dashboard (P79, TD-247)

Matt, 2026-10-03: "Open the blank copy that is linked within the environment. Select the previous file that they saved, with the schedule and all of their notes ... the previous file is now mirrored in the current." He also directed that the front end and back end be built separately. The UI is to be as simple as possible, because it will be rebuilt into the redesigned layout and form being developed through another path.

This file is the hand-off for that redesign: what the back end does, the contract a UI calls, and what the interim UI is.

## 1. The user's flow

1. Open the blank dashboard from the link.
2. Choose **Continue from saved** and pick last period's saved file. A saved `.html` (Save output) or a Backups `.json` download both work.
3. Check the summary: saved date and version, project number, data date, milestones, user tasks, updates, notes and whether a baseline is included. Then choose **Load**.
4. The board is now that file's dashboard. Import this period's P6 update through the normal Import path. The baseline stays, the update replaces the schedule, and a `Before import` backup is pinned (P76).
5. Save. The new file's provenance chain continues from the old file's chain.

Upgrade path: the blank copy is always the newest app version, so loading an old file into it brings that file's data up to date. Replacing the one linked blank file rolls out a new version.

## 2. Separation

| Layer | Where | Replaced by the redesign? |
|---|---|---|
| **Module** `SRETContinue` | `src/modules/continue-file/`, pasted between `@module continue-file` markers | No |
| **App adapter** `continueRead` / `continueApply` / `continueCancel` | app script, banner `CONTINUE FROM A SAVED DASHBOARD`, after `bkRestore()` | No |
| **Interim UI** | app script, banner `CONTINUE UI, INTERIM`; markup `#es-continue`, `#continue-file`, `#continue-dialog` | **Yes: delete it all** |

The interim UI calls only the adapter, and the adapter calls only the module plus the existing P76 restore path (`bkApplyPayload()` → `applyPublishedState()`). A redesigned UI therefore needs nothing from the interim block.

## 3. Adapter contract (what a UI calls)

```
continueRead(file: File) -> Promise<{
  ok: boolean,
  errors: string[],        // user-facing; ok is false when any is present
  warnings: string[],      // user-facing; show them, they do not block
  summary: null | {
    fileName, savedAt (ISO), savedBy (app version), projectNo, reportTitle,
    dataDate ('YYYY-MM-DD' | null), sources: string[],
    milestones, tasks, userTasks, entries, notes,   // counts
    hasBaseline: boolean, chainLength, empty: boolean
  },
  replacesWork: boolean,   // the board has work now; warn before Load
  fileName: string
}>
continueApply() -> { ok: boolean, message: string }
continueCancel() -> void
```

- `continueRead` never changes the board. On `ok` it holds the file as pending, and a second call replaces the pending file.
- `continueApply` loads the pending file. It **replaces** the board (a mirror, not a merge), pins a `Before continue` backup when the board had work, marks the work unsaved, and sets the status line. On failure it puts the board back and returns `ok:false`.
- Messages contain no em dashes (CLAUDE.md). Show them as given.
- `CONTINUED_FROM` (`{file, summary, at}`) records what this session continued from, for any "continued from" label the redesign wants.

## 4. What the redesign must provide

Minimum, in this order:

1. **An entry point** that opens a file picker with `accept=".html,.htm,.json"`. Today it is on the empty state only. Decide whether it also belongs in a File or Data menu for a board that already has work; the adapter supports both, and warns through `replacesWork`.
2. **A confirm step** showing `errors` (no Load), or the `summary`, then `warnings`, plus a replace warning when `replacesWork` is true. Load calls `continueApply()`; Cancel calls `continueCancel()`.
3. **The result**: show `message` (the interim UI uses a toast; the status line is set either way).

Optional: dropping a file on the empty state (the interim UI does this for `.html`, `.htm` and `.json` only, so a dropped schedule is not taken).

## 5. Interim UI (to delete)

- `#es-continue`: a third button on the empty state, **Continue from saved**, beside Import schedule and Add milestone. The hint under them names the option.
- `#continue-file`: the hidden file input.
- `#continue-dialog`: reuses the annotations dialog's classes (`.annot-dialog`, `.annot-panel`, `.annot-msg`), so it adds no CSS.
- `continuePick`, `continueChosen`, `continueShowDialog`, `continueClose`, `continueConfirm`, and the drop listener on `#empty-state`.
- `continue-dialog-body` is in `PUBLISH_CLEAR_IDS`. Remove it there too.

## 6. Decisions taken (flag to reverse)

| Decision | Alternative | Why |
|---|---|---|
| Load replaces the board | Merge into what is open | "Mirrored" was the ask. Merging annotations into an open schedule is already the Sources mount (`.json`). |
| The copy takes the saved file's provenance (`PUBLISHED_META`, `PUBLISH_CHAIN`) | A fresh chain | The next Save extends the old file's chain, so period-to-period history is kept. |
| `.json` accepted when it is a whole state (has a timeline with dates) | `.html` only | A Backups download (P76) is a whole state, so it becomes recoverable from any device. An annotations-only model export is refused, with a pointer to the Sources mount. |
| A newer major version is refused; a newer partial loads with a warning | Refuse anything newer | `applyPublishedState()` ignores keys it does not know. A major bump is the agreed signal for a breaking change. |
| Entry only on the empty state (interim) | Also in the header | Simplest. Placement is the redesign's call (§4). |

## 7. Tests

- `tools/continue_file_test.mjs`: the module alone.
- `tools/p79_continue_check.py`: end to end in the browser.
- Results: `docs/05-test-log.md`, TEST-82.
