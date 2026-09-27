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
| 4c | `src/modules/ms-import/ms-import.js` | Directly after #4b, same script | Self-contained IIFE; defines `window.SRETMsImport` only (the milestone import rules). The grid's import dialog calls it; the app's own import form can too |
| 4d | `src/modules/dates/dates.js` | Directly after #4b, before #4c | `window.SRETDates`: the one date reader for every import (grid and dashboard). #4c needs it |
| 4e | `src/modules/user/user.js`, `src/modules/user/user.css` | JS after #4d; CSS in the main `<style>` after #1 | `window.SRETUser`: the user name and save history, and the Data settings field |
| 5 | The adapters below | In `app-script`, beside the Workspace code (`setWorkspaceSection()`) | The only code that knows both the app's stores and the grid contract |

Check before pasting: neither vendor file contains `</script` or `</style` (`tools/grid_view_assemble.py` asserts this for the demo and would fail the same way).

### Size delta

| | Bytes | Gzip |
|---|---|---|
| App at base `81cfd7a` | 878,041 | 236,950 |
| #2 + #3 vendored engine | 221,778 | 54,817 |
| #1 + #4 + #4b + #4c wrapper, shared lists module and import rules | 109,648 | 30,174 |
| Adapters (#5), estimate | about 8,000 | about 2,500 |
| **Total added** | **about 339,000 (about 39%)** | about 87,000 |

If Matt chooses the unminified vendor files (D-09 decision 2), #3 grows from 217,423 to 458,011 bytes and the total becomes about 580,000 (about 66%).

## The contract the app calls

```js
SRETGrid.open({
  title,                       // shown beside the back arrow
  columns: [{ key, label, type: 'text'|'date'|'number'|'select', editable, options, width,
               min, max,               // numbers: import rejects values outside
               hidden,                 // not shown; kept in export and the import template
               tones,                  // { value: 'future'|'track'|'risk'|'crit'|'done' } shades the cell
               icon }],                // { key, label, options }: tap-to-edit dot before the value
  rows,                        // plain objects; copied on open, never mutated
  rowKey,                      // property holding a unique id
  editable,                    // grid-level switch; false = read-only screen
  onEdit(rowKey, key, value),  // return false to refuse (cell reverts)
  onAdd(),                     // optional; returns the new row object, shows "Add row"
  onDelete(rowKeys),           // optional; shows "Delete selected"; return false to keep
  canEdit(rowKey, key),        // optional per-row refusal
  onBack(),                    // after the screen has closed
  importer: {                  // optional: Add row menu > Import milestones and Import log
    idKey, depKeys,            //   e.g. 'id', { pred:'Predecessors', succ:'Successors' }
    user,                      //   name for the Import log: a string, or a function read at commit (USER.name)
    log,                       //   the app's array; entries {time,file,user,id,row,field,note} are pushed
    nextId(taken),             //   next free ID; taken = IDs already given out in this import
    knownIds(),                //   every ID a dependency may name (schedule and user milestones)
    onCommit(rows),            //   add rows to the app store; return the rows as stored
    onLog(entries)             //   optional, after entries are pushed, so the app persists
  },
  onImport(body, close),       // fallback when there is no importer: mount a form into the dialog
  openColumn, onOpenItem(key), // double-click in openColumn calls onOpenItem (the milestone form)
  onTemplate(),                // optional: Download import template; default is an .xlsx of the
                               //   column headers (derived List column excluded)
  exportName,                  // .xlsx file name, no extension
  ensureXLSX,                  // pass the app's ensureXLSX
  host,                        // element the screen covers
  lists: {                     // optional: My temp list and saved lists
    store,                     //   the app's SRETCollections store (data in)
    refOf(rowKey),             //   rowKey -> stable item ref, e.g. 'activity:SNIP-118'
    labelOf(ref),              //   optional: name shown for an item in the temp list panel
    onChange(result)           //   after every change, so the app persists
  }
});
SRETGrid.close(); SRETGrid.setRows(rows); SRETGrid.patchRows(rows); SRETGrid.isOpen();
SRETGrid.dialog(title, build);        // the grid's centred modal, for the app's own content
SRETGrid.importAoa(aoa, fileName);    // run the import checks on a sheet the app already parsed
```

### Milestone import rules (`SRETMsImport`, Matt 2026-09-27)

| Case | Result |
|---|---|
| File empty, no ID column, no rows, not .xlsx/.csv, unreadable | **Import failed** panel (role=alert) and toast; nothing added |
| Duplicate IDs within the file | Fails: "There are duplicate activity IDs within the list: X (rows a, b). Only unique IDs, or blank IDs, can be imported." |
| ID already in the table | Row skipped, listed in the summary |
| Blank ID | Assigned by `nextId(taken)` on commit; unique within the import |
| Predecessor or successor not in the table, `knownIds()` or the file | Asks "Some dependencies or predecessors are not found. Do you wish to continue with import?" and lists "Predecessors not found: A, B" per row |
| Date, number or choice that cannot be read | Left blank; asks "Some values could not be read. Do you wish to continue with import?" when there are no dependency issues |
| Continue | Rows added; every issue written to the Import log (time, file, user, ID, note). Cancel adds and logs nothing |
| Success | **Import complete** summary: imported, IDs assigned, skipped, issues logged; View Import log button when issues were logged |

Dates: see **Date reading** below. `.xls`/`.xlsm` go through SheetJS like `.xlsx`.

### Date reading (`SRETDates`, Matt 2026-09-28)

One engine for every import. The order of a file's numeric dates is worked out from all of them together, before any value is read:

| Evidence in the file | Order |
|---|---|
| A first part above 12 (13/10/26) | Day first |
| A middle part above 12 (10/13/26) | Month first |
| The first part barely changes across rows (26-10-09, 26-11-05, ...) | Year first |
| A four-digit first part (2026-10-09, 20261009) | Always year first; does not vote |
| Nothing decides | Day first (the default). If any date would read differently another way, the dialog asks first and offers **Date order** |

Breaks: `-` `/` `.` space or comma. Month names in any position (`9 Oct 26`, `Oct 9, 2026`, `2026-Oct-09`), Excel serials and a trailing time are read directly. Impossible dates (31-Feb, month 13) fail and are logged. Two-digit years are 20yy, as today.

**Dashboard import at merge.** `parseLooseDate()` today reads `10/09/2026` as 10-Sep but `10-09-2026`, `10.09.2026` and `10 09 2026` as 9-Oct, because those fall through to `Date.parse`, which is month first (measured in Chromium). At merge: strip the P6 `A` and `*` suffixes as today, run `SRETDates.detect()` over the file's date columns once per import, then `SRETDates.parse(value, order)` per cell, and drop the `Date.parse` fallback. `parseMsDate()` (typed dates in the milestone card) uses `SRETDates.parse(value, 'DMY')`.

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
| `wbs` | the WBS of the linked schedule row | Yes |
| `state` | `m.state`, options from `STATE_LABELS` | Yes |
| `pred`, `succ` | the milestone's dependency annotations | Yes |
| `progress` | `m.progress`, 0 to 100 | Yes; refuse outside 0 to 100 (the demo shows the `return false` pattern) |
| `comment` | the milestone comment annotation | Yes |
| `created`, `createdBy` | set when the milestone is added or imported; the far-right columns | No |
| `health` | the milestone health annotation; shown as the dot before the ID (tap to change) and a hidden column exported last | Via the dot |

### User name and save history (`SRETUser`, Matt 2026-09-28)

A page opened from disk cannot read the computer's login name (browsers block it; there is no `environ` equivalent), so:

- **First use on a computer:** the app asks "Who is using this file?" with the name field. The name is remembered on that computer (`localStorage` key `sret-user-name`, like the theme) and never travels with the file.
- **Data settings > Your name:** confirm or change it any time. The field shows the comparison with the file: "You are working as A. Lee. This file was last saved by J. Ruiz."
- **Shared file:** the file keeps `savedBy` and its save history. Opened on another computer, everything done there (imports, new milestones, saves) is recorded against that computer's user, and their save becomes the file's last saver.
- **Save history:** every save appends `{at, by, version}`; nothing is removed.

Wiring: `let USER=SRETUser.create({file:{savedBy:PUBLISHED.savedBy, history:PUBLISH_CHAIN}})` at load. `publishStatePayload()` calls `USER.recordSave({at, version:APP_VERSION})` and writes `savedBy` plus the chain; `PUBLISH_CHAIN` entries gain `by` (older entries without it show "(not set)"). The importer passes `user:()=>USER.name()`, and Created by uses the same. Call `SRETUser.buildField()` in the Data settings tab. On load, if `USER.status().state==='unset'`, open the prompt.

`state` carries `tones` so the Status cell is shaded per status. `openColumn:'id'` with `onOpenItem:id=>openMsDialog(id)` opens the existing milestone form on double-click. 
`onAdd` calls the same code path as the Add milestone dialog (so ID numbering via `nextUserMsId()` and the collision check stay single-sourced) and returns the new row. `onDelete` calls the existing per-item removal. Every callback ends with `noteMarkup()` and the persistence the existing handlers already do.

### 2. Workspace > Comments & markups: a collection row

Today: `renderCollections()` (line ~7238) renders `.coll-row` buttons into `#coll-list`, each calling `selectCollection(period)`. Add a "View as table" action in the collection detail (`#coll-detail`) that calls `openCollectionGrid(period)` with title `'Annotations: W/E ' + <period in d-Mmm-yy>`.

One row per annotation entry in that collection: milestone comment, row remark, dependency comment, note, and field edits (health, progress, date overrides). Columns as in the demo's annotation config: entry, kind, activity ID, activity name (read-only), comment or value and status (editable). `canEdit` refuses the value cell for entries whose value is not user-entered. Edits go back through the same setters the card and Notes panes use, so the annotation layer stays the only thing written.

### Shared: My temp list and saved lists

Purpose (Matt, 2026-09-27): keep track of important activities in groups, aggregate them by a scope or reason, and build a selection set to bulk edit across several filtered states.

**Workflow (Matt, 2026-09-27):**
1. Select rows in any grid, under any filter, and click **Add to temp list**. The count appears as a badge on the rail button.
2. Open **My temp list** from the rail. It's a vertical panel docked left of the grid, collapsed by default. Its action buttons sit under the title, above the items. Tick items, then use **Add to list ▾** to pick a saved list, or **New list…** to name a new one. The temp list stays as it is.
3. **Remove** takes the ticked items off the temp list.
4. **More ▾ > Clear temp list…** empties it, after an inline confirmation.

**Shortcuts from the Add to temp list ▾ menu:**
- Remove selected from My temp list.
- **Add to "<list>"**, one entry per saved list. It adds the selected rows straight to that list, without going through the temp list.
- Show only My temp list.

**Saved lists** is the second rail button. It opens the same panel style, with a dropdown in the header to choose the list:
- **Remove from list** affects only that list.
- **More ▾** holds Show only these rows in the table and **Delete list…**, which asks first. Deleting a list leaves the items themselves unchanged.

While a filter is on, a pill in row 3 names it ("My temp list only" or "List: <name>"). Clicking the pill clears it.

**Grid columns:**
- **List** is collapsed by default: a narrow column with a dot and the number of lists the row is in.
  - The arrow in its header, or **Tools ▾ > Expand the List column**, widens it to show the list names.
  - Clicking the arrow never sorts.
- **Rows on My temp list** carry a vertical accent line to the left of their checkbox. The same line is the temp list's icon on the rail button, the panel title and the Add to temp list button.

**Rules**, all in `SRETCollections` (`src/modules/collections/collections.js`) and nowhere else:
- An item can be in any number of saved lists. That's the default.
- `settings.singleList` implements the future setting **"Limit items to a single list"**. When it is on, adding an item to a list moves it out of the others, and the message names where it moved from. It is already implemented and tested, but has no UI yet: it's the one flag on the store (`SRETCollections.newStore({singleList:true})`, or set `store.settings.singleList`).
- The temp list is independent of saved lists. It is working state for the session. Saved lists are annotation-layer data. Neither touches schedule data.

**Screen layout (Matt, 2026-09-27).**
- **Row 1:** back arrow and title.
- **Row 2:** search, **Add row ▾**, **Tools ▾**, **Add to temp list ▾**. It starts in line with the title text, so the strip above the rail stays clear up to the back arrow.
  - **Add row ▾** is a split button. Its menu, in groups split by a hairline: Delete selected rows…; Export .xlsx, Download import template; Import milestones…, Import log. Delete is also in Tools.
  - Screens without Add row, such as the read-only schedule, show a plain Export .xlsx button in the same place.
  - **Tools ▾** holds Expand the List column and Delete selected rows….
  - **Add to temp list ▾** is also a split button.
- **Row 3**, under the buttons: "12 rows (3 selected)", **Select all**, and the filter pill.
- **Left of the grid:** the rail, with the My temp list button (count badge) and the Saved lists button.
- **Import milestones** opens a centred modal dialog, not a side panel:
  - Esc, the close button or a click on the backdrop closes it.
  - Tab stays inside it, and focus returns to the menu button afterwards.
  - The dialog runs the checks in `SRETMsImport` itself when `importer` is passed. If the app's own import form (Data & view > Import) also imports milestones, it parses the sheet as today and calls `SRETGrid.importAoa(aoa, file.name)`, so both places apply one set of rules.
- **Messages:** status messages are a toast over the grid.
- **Verification:** `tools/grid_view_check.py` measures the header alignment and the row order at 1440 px.

**Wiring at merge:**
- **Store.** One app global, e.g. `let USER_LISTS=SRETCollections.newStore();`. Persist `USER_LISTS.list` wherever `NOTE_COLLECTIONS` is persisted: publish state, the model and annotations `.json` export, and the mount path. `USER_LISTS.temp` is not persisted: session only (Matt, 2026-09-28). The panel title and rail button say so on hover.
- **Item refs.** Use `'activity:'+activityId` for schedule activities and user milestones, so the same activity from the board or either grid is one item. Use `'note:'+nid` for notes and `'annot:'+entryId` for other annotation entries. Activity IDs are the key the annotation stores already use, so refs survive a re-import.
- **Grid.** Every `SRETGrid.open()` config passes `lists:{store:USER_LISTS, refOf:toRef, labelOf:refLabel, onChange:()=>noteMarkup()}`, where `refLabel` returns `'SNIP-118  Name'` from the app's own stores. The grid calls `SRETCollections` itself on that store, and adds the read-only **List** column (sortable, filterable when expanded, exported) and the temp row mark.
- **Dashboard.** The same functions are called on the same store:
  - The Notes list bulk bar (beside the status action in `renderNotes()`) gets "Add to temp list", which calls `SRETCollections.tempAdd(USER_LISTS, NOTES_SELECTED.map(n=>'note:'+n))`.
  - A board selection, if P59 adds one, calls the same function with `'activity:'` refs.
  - The temp list panel belongs in the Workspace, beside Notes and Comments and markups (annotation side, per D-20). It should reuse the grid's panel pattern (vertical, from a rail button, core buttons plus More), the same four steps (`addFromTemp` / `saveFromTemp` on the ticked items, `tempRemove`, `tempClear`) and the same `describe()` sentence.
  - "Limit items to a single list", when it becomes a setting, belongs in Data & view > Data settings and just sets `USER_LISTS.settings.singleList`.
- **Relationship to week collections (P58, D-19a).** These are separate. A note keeps its reporting week; lists are the user's own working groups.

### 3. Views from the title: user milestones and the schedule (Matt, 2026-09-28)

The grid's title is a view switcher (`views`, `view`, `onView`). One grid screen, four views, each reopening the grid with its own config; Back returns to where the grid was first opened.

| View | Rows | Editable |
|---|---|---|
| User milestones | `USER_MILESTONES` | Yes (section 1) |
| Schedule milestones | **[CONFIRM WITH MATT]** The demo uses zero-duration activities. The board plots every leaf activity as a milestone (`MILESTONES`, built in the ingest), so in the app this view is either those board milestones (then "All schedule activities" adds only the WBS-level rows) or P6 milestone-type activities only | Annotation columns only |
| Schedule updates | Schedule activities carrying an annotation: short title, health or comment | Annotation columns only |
| All schedule activities | Every schedule activity | Annotation columns only |

Schedule columns (ID, name, WBS, duration, dates, float, predecessors, successors, actual flag) are **read-only**; there is no `onAdd` and no `onDelete` on schedule views. Annotation edits go through `onEdit` to the annotation stores, never to `TASKS` / `MILESTONES`, so schedule data is never mutated. Counts in the menu come from the app's stores at open.

Entry: the existing "View items" button (section 1) opens User milestones; the other views are reached from the title, so no separate Data & view button is needed.

## Verification at merge

1. `python3 tools/grid_view_check.py` still passes on `prototypes/grid-view/demo.html` (unchanged modules). It covers scroll smoothness on 2,000 rows (every visible row present on fast scrolls, no engine wheel handling, transform positioning, per-step cost) the three-row header aligned to the title, the Add row / Tools / Add to temp list menus, the import dialog, the collapsible List column (left of the checkbox, no filter when collapsed) and the temp row mark, the milestone import rules end to end (failures, duplicate IDs, skipped and assigned IDs, the continue question, Cancel, the Import log, `importAoa`), Band and WBS as separate columns, Date created and Created by far right, Health exported last, status tones, the health dot picker, double-click to open, both panel modes, and the four-step lists workflow (temp list built across three filter states, Temp list only, ticked temp items into existing and new lists, one item in two lists, remove, clear with confirmation, the temp list carried across screens, and the single-list setting).
2. `python3 tools/colour_audit.py --strict` and `python3 tools/palette_swap_check.py` on the app, with a grid open for the swap (add the open to the swap check's setup the way it opens the milestone dialog).
3. `python3 tools/theme_check.py` on the app.
4. A merge-stage probe that clicks each of the three real entry points, edits one value per entry point and asserts the value lands in the right store and survives `scheduleRerender(true)` and a publish round trip. That probe does not exist yet: it can only be written against the merged file.
5. The existing suite (`ds_check.py`, `import_check.py`, `persist_check.py`, the `p*_check.py` probes) unchanged.
