# Grid view: merging into the app

How the D-09 grid view (branch `claude/sret-grid-view`) goes into `src/milestone-dashboard.html` in a later merge stage. Nothing here has been applied to the app file; P59 was editing it concurrently. Line numbers below are at base `81cfd7a` and will move with P59, so each location is also named by a selector or function to search for.

Library choice and sign-off points: `docs/decisions/D-09-grid-library.md`.

## What gets pasted where

The app keeps one `<style>` (scanned by `colour_audit.py --strict`) and one `<script id="app-script">`. The vendored engine goes in blocks of its own so the audit rules and the "no literal colours" rule keep meaning what they mean today.

| # | Source file | Destination in `milestone-dashboard.html` | Why there |
|---|---|---|---|
| 1 | `src/modules/grid-view/grid-view.css` | Inside the main `<style>`, after the Workspace / Data and view panel rules, as its own commented section | Tier 3 component styles; only `--color-*` roles and D-16 tokens, so `--strict` passes with no exception |
| 2 | `vendor/slickgrid/dist/slick.grid.css` | New `<style id="vendor-slickgrid-css">` immediately after the main `</style>` | Unmodified vendor CSS; kept out of the audited block. Every colour it could paint is overridden by #1 (proven by the palette swap in `tools/grid_view_check.py`) |
| 3 | `vendor/slickgrid/slickgrid.subset.min.js` | New `<script id="vendor-slickgrid">` immediately **before** `<script id="app-script">`, preceded by a `/* */` comment holding the full text of `vendor/slickgrid/LICENSE` and the version line from `SOURCE.md` | Must define `window.Slick` before the app script runs; MIT notice travels with the code |
| 4 | `src/modules/grid-view/grid-view.js` | Top of `<script id="app-script">`, before the app's own code, as one commented section | Self-contained IIFE; defines `window.SRETGrid` only |
| 4b | `src/modules/collections/collections.js` | Directly after #4, same script | Self-contained IIFE; defines `window.SRETCollections` only (My temp list and saved lists). Shared by the grid and the dashboard, so it must load before either calls it |
| 5 | The adapters below | In `app-script`, beside the Workspace code (`setWorkspaceSection()`) | The only code that knows both the app's stores and the grid contract |

Check before pasting: neither vendor file contains `</script` or `</style` (`tools/grid_view_assemble.py` asserts this for the demo and would fail the same way).

### Size delta

| | Bytes | Gzip |
|---|---|---|
| App at base `81cfd7a` | 878,041 | 236,950 |
| #2 + #3 vendored engine | 221,778 | 54,817 |
| #1 + #4 + #4b wrapper and shared lists module | 50,429 | 14,966 |
| Adapters (#5), estimate | about 6,000 | about 2,000 |
| **Total added** | **about 278,000 (about 32%)** | about 72,000 |

If Matt chooses the unminified vendor files (D-09 decision 2), #3 grows from 217,423 to 458,011 bytes and the total becomes about 519,000 (about 59%).

## The contract the app calls

```js
SRETGrid.open({
  title,                       // shown beside the back arrow
  columns: [{ key, label, type: 'text'|'date'|'number'|'select', editable, options, width }],
  rows,                        // plain objects; copied on open, never mutated
  rowKey,                      // property holding a unique id
  editable,                    // grid-level switch; false = read-only screen
  onEdit(rowKey, key, value),  // return false to refuse (cell reverts)
  onAdd(),                     // optional; returns the new row object, shows "Add row"
  onDelete(rowKeys),           // optional; shows "Delete selected"; return false to keep
  canEdit(rowKey, key),        // optional per-row refusal
  onBack(),                    // after the screen has closed
  exportName,                  // .xlsx file name, no extension
  ensureXLSX,                  // pass the app's ensureXLSX
  host,                        // element the screen covers
  lists: {                     // optional: My temp list and saved lists
    store,                     //   the app's SRETCollections store (data in)
    refOf(rowKey),             //   rowKey -> stable item ref, e.g. 'activity:SNIP-118'
    onChange(result)           //   after every change, so the app persists
  }
});
SRETGrid.close(); SRETGrid.setRows(rows); SRETGrid.patchRows(rows); SRETGrid.isOpen();
```

Types: dates are ISO `YYYY-MM-DD` strings in and out (shown `d-Mmm-yy`, the board format). Numbers are numbers; an empty number cell is `null`. Select values keep the option's own type (e.g. the numeric health codes stay numbers).

The wrapper reads no app global. SheetJS arrives as whatever `ensureXLSX()` resolves with, or `window.XLSX` when it resolves with nothing, which is what the app's `ensureXLSX()` does today.

### Host and "keeps the app header"

`host` is the element the screen covers with `position:absolute; inset:0`. Pass the board container so the app header and icon bar stay visible and clickable: today that is the parent of `#scroll-wrap` (`#scroll-wrap` itself scrolls, so covering it would scroll with the table). The host must be positioned (`position:relative`); `#scroll-wrap` already is, its parent needs checking after P59 moves the header. **[CONFIRM AT MERGE against the P59 layout]**

Back returns focus to the element that had it when `open()` ran, so opening from a Workspace button and pressing back lands on that button. `onBack` runs after the screen has closed: use it to re-render anything the edits changed (`scheduleRerender(true)`, never `rerender(true)`).

## Entry points to wire

"The code exists" is not "the code is wired up" (CLAUDE.md traps). Each entry below is a separate wiring task and each needs its own probe assertion in the merge-stage check.

### 1. Workspace > User milestones: "View items"

Today: `renderMounts()` (line ~10737) renders a disabled `Manage…` button titled "Grid arrives in D-17c" in the User-defined group, which lands in `#ws-userms-body`. Replace it with an enabled "View items" button calling `openUserMsGrid()`.

Adapter outline (field names from the `USER_MILESTONES.push` in the add-milestone handler, line ~12704):

| Grid column (`key`) | From `USER_MILESTONES` record | Editable |
|---|---|---|
| `id` | `m.id` | No (it keys every annotation store; renaming is out of scope) |
| `name` | `m.actName` (and `notes` must be re-derived as `'['+id+'] - '+name`, see the comment at the push site) | Yes |
| `type` | `m.type` (MS / INT / CLI / RTN, the `#add-ms-type` options) | Yes |
| `start`, `finish` | the record's start and `m.date` | Yes; refuse a date outside the week range the same way the add dialog does (`dateToCol(date)<0`) |
| `band` | the owning row's band (`USER_ROWS` `notes`) | Yes |
| `state` | `m.state`, options from `STATE_LABELS` | Yes |
| `pred`, `succ` | the milestone's dependency annotations | Yes |
| `progress` | `m.progress`, 0 to 100 | Yes; refuse outside 0 to 100 (the demo shows the `return false` pattern) |
| `comment` | the milestone comment annotation | Yes |

`onAdd` calls the same code path as the Add milestone dialog (so ID numbering via `nextUserMsId()` and the collision check stay single-sourced) and returns the new row. `onDelete` calls the existing per-item removal. Every callback ends with `noteMarkup()` and the persistence the existing handlers already do.

### 2. Workspace > Comments & markups: a collection row

Today: `renderCollections()` (line ~7238) renders `.coll-row` buttons into `#coll-list`, each calling `selectCollection(period)`. Add a "View as table" action in the collection detail (`#coll-detail`) that calls `openCollectionGrid(period)` with title `'Annotations: W/E ' + <period in d-Mmm-yy>`.

One row per annotation entry in that collection: milestone comment, row remark, dependency comment, note, and field edits (health, progress, date overrides). Columns as in the demo's annotation config: entry, kind, activity ID, activity name (read-only), comment or value and status (editable). `canEdit` refuses the value cell for entries whose value is not user-entered. Edits go back through the same setters the card and Notes panes use, so the annotation layer stays the only thing written.

### Shared: My temp list and saved lists

Purpose (Matt, 2026-09-27): keep track of important activities in groups, aggregate them by a scope or reason, and build a selection set to bulk edit across several filtered states.

**Flow.** 1. **My temp list** (quick pick list): add selected rows from any screen and any filter state; remove selected rows the same way. Then one of **A. Save new list**, **B. Add to existing**, **C. Clear** (with inline confirmation). A and B empty the temp list afterwards. **Temp list only** filters any grid down to the picked rows, so they can be selected together for a bulk action.

**Rules**, all in `SRETCollections` (`src/modules/collections/collections.js`) and nowhere else:
- An item is in at most one saved list. Adding it to another list moves it, and the message names the list it came from.
- The temp list is independent of saved lists: an item can be picked whether or not it is already in a list.
- The temp list is working state for the session. Saved lists are annotation-layer data. Neither touches schedule data.

**Wiring at merge:**
- **Store.** One app global, e.g. `let USER_LISTS=SRETCollections.newStore();`. Persist `USER_LISTS.list` wherever `NOTE_COLLECTIONS` is persisted: publish state, the model and annotations `.json` export, and the mount path. `USER_LISTS.temp` is not persisted. **[CONFIRM WITH MATT]** whether the temp list should survive a reload.
- **Item refs.** Use `'activity:'+activityId` for schedule activities and user milestones, so the same activity from the board or either grid is one item. Use `'note:'+nid` for notes and `'annot:'+entryId` for other annotation entries. Activity IDs are the key the annotation stores already use, so refs survive a re-import.
- **Grid.** Every `SRETGrid.open()` config passes `lists:{store:USER_LISTS, refOf:toRef, onChange:()=>noteMarkup()}`. The grid calls `SRETCollections` itself on that store, and adds read-only **List** and **Temp** columns (sortable, filterable, exported).
- **Dashboard.** The same functions are called on the same store:
  - The Notes list bulk bar (beside the status action in `renderNotes()`) gets "Add to temp list", which calls `SRETCollections.tempAdd(USER_LISTS, NOTES_SELECTED.map(n=>'note:'+n))`.
  - A board selection, if P59 adds one, calls the same function with `'activity:'` refs.
  - The temp list panel belongs in the Workspace, beside Notes and Comments and markups (annotation side, per D-20), using the same A / B / C actions and the `describe()` sentence.
- **Relationship to week collections (P58, D-19a).** These are separate. A note keeps its reporting week; lists are the user's own working groups.

### 3. Data & view: Schedule activities

Add a "Schedule activities" row with a "View as table" button in the Data & view drawer's Sources tab (`setSettingsTab('sources')`), calling `openScheduleGrid()`. Schedule columns (ID, name, WBS, duration, dates, float, predecessors, successors, actual flag) are **read-only**; there is no `onAdd` and no `onDelete`, so those buttons do not render. Only annotation columns are editable (short title, health, comment), and their `onEdit` writes to the annotation stores, never to `TASKS` / `MILESTONES`. This keeps the three layers separate: schedule data is never mutated by the grid.

Where exactly the button goes in Data & view (Sources, or View controls) is a layout call for the main thread. **[CONFIRM WITH MATT]**

## Verification at merge

1. `python3 tools/grid_view_check.py` still passes on `prototypes/grid-view/demo.html` (unchanged modules). It covers scroll smoothness on 2,000 rows (every visible row present on fast scrolls, no engine wheel handling, transform positioning, per-step cost) and the lists flow (temp list built across three filter states, Temp list only, A / B / C including the one-list move, clear confirmation, the temp list carried across screens).
2. `python3 tools/colour_audit.py --strict` and `python3 tools/palette_swap_check.py` on the app, with a grid open for the swap (add the open to the swap check's setup the way it opens the milestone dialog).
3. `python3 tools/theme_check.py` on the app.
4. A merge-stage probe that clicks each of the three real entry points, edits one value per entry point and asserts the value lands in the right store and survives `scheduleRerender(true)` and a publish round trip. That probe does not exist yet: it can only be written against the merged file.
5. The existing suite (`ds_check.py`, `import_check.py`, `persist_check.py`, the `p*_check.py` probes) unchanged.
