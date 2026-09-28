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
| 4f | `src/modules/compare/compare.js` | After #4e | `window.SRETCompare`: stored uploads, the designation reference table, and the Schedule changes comparison |
| 4g | `src/modules/migrate/migrate.js` | After #4f | `window.SRETMigrate`: renames old stored keys and values (user milestones to user tasks) on every load |
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

**Checked at P61 (TD-221):**

- The parent of `#scroll-wrap` is `#page-frame`, which is `display:contents`. It has no box, so it cannot be positioned, and the next box up is `<body>`. Covering `<body>` would cover the icon bar.
- The app therefore has its own host, `#grid-host`, placed after `.rpt-hd` and `position:relative`. It is shown while `body.grid-open` is set. That class hides the filter bar, `#scroll-wrap`, the legend and the print filter note.
- The host's height is the viewport less its top edge. It is set on open, on a window resize, and whenever `.rpt-hd` changes size, which happens when a side panel docks.
- The icon bar and report header stay visible and clickable. `tools/p61_check.py` measures this with `elementFromPoint`.

Back returns focus to the element that had it when `open()` ran, so opening from a Workspace button and pressing back lands on that button. `onBack` runs after the screen has closed: use it to re-render anything the edits changed (`scheduleRerender(true)`, never `rerender(true)`).

## Entry points to wire

"The code exists" is not "the code is wired up" (CLAUDE.md traps). Each entry below is a separate wiring task and each needs its own probe assertion in the merge-stage check.

### 1. Workspace > User milestones: "View items"

Today: `renderMounts()` (line ~10737) renders a disabled `Manage…` button titled "Grid arrives in D-17c" in the User-defined group, which lands in `#ws-userms-body`. Replace it with an enabled "View items" button calling `openUserMsGrid()`.

Adapter outline (field names from the `USER_MILESTONES.push` in the add-milestone handler, line ~12704; after TD-217 these are `USER_TASKS` and the add-task handler):

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

**Built at P62 (TD-222, E-02), per annotation type rather than per period.** Matt's feedback asked for one row per collection of annotations with a count, each opening an editable table. Only notes carry a period, so a collection is read as an annotation type: the Your edits row in Comments & markups lists each non-empty type with its count and a View button calling `openAnnotGrid(type)`, the `openUserMsGrid()` pattern. Grouping by week or source file waits on the D-03 edit ledger. The period-collection table above is not built.

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

### 3. Views from the title (Matt, 2026-09-28)

The grid's title is a view switcher (`views`, `view`, `onView`). Back returns to where the grid was first opened.

| View | Rows | Editable |
|---|---|---|
| User tasks | The user's own items (`USER_TASKS`, today `USER_MILESTONES`). Called tasks in the grid to keep them apart from schedule milestones | Yes (section 1) |
| Schedule milestones | Every activity from an uploaded schedule (the board plots each as a milestone: `MILESTONES` from `PRIMARY_SOURCES`) | Annotation columns only |
| Schedule updates | Schedule milestones carrying an annotation: short title, health or comment | Annotation columns only |
| Schedule changes | Section 4 | Read-only |
| Comments and markups | The current annotation collection (section 2) | As section 2 |

Schedule columns (ID, name, WBS, duration, dates, float, predecessors, successors, actual flag) are **read-only**; annotation edits go through `onEdit` to the annotation stores, never to `TASKS` / `MILESTONES`. The importer passes `noun:['task','tasks']`, so the menu, dialog and summary say "Import tasks" and "Imported 3 tasks".

**User tasks across the dashboard, names and stored keys in sync (Matt, 2026-09-28).** Tracked as TD-217. Everything is renamed: the words people read, the keys and values saved in files, and the code identifiers, so they cannot drift apart. Files saved before the rename still open because every load path runs `SRETMigrate.userTasks()` first (`src/modules/migrate/migrate.js`, paste as #4g after #4f). Saving writes only the new names.

*Stored keys and values (migrated on load):*

| Stored where | Old | New |
|---|---|---|
| Publish, model and annotations payload key | `userMilestones` | `userTasks` |
| Payload key | `userMsEnabled` | `userTasksEnabled` |
| `source` / `sourceSchedule` value on tasks, rows, milestones, registered sources | `User-defined` | `User tasks` |
| Band value (`notes` on the band's rows) | `User Defined Milestones` | `User Tasks` |
| `localStorage` `sret-ws-section` value | `userms` | `usertasks` (via `SRETMigrate.wsSection`) |
| Export sheet name / file name part | `User-defined` / `_user-defined_` | `User tasks` / `_user-tasks_`; re-import accepts both (`SRETMigrate.sheetName`) |

*Where the app calls the migration (by function, base `81cfd7a`):* `applyPublishedState()` (published file), the `ANNOT_CATEGORIES` entry that applies `userMilestones` (model and annotations `.json` import and mount), `restorePrimarySources()`, the user route in `runIngest()` (`srcName===USER_BAND_SOURCE` must also accept the old value through `SRETMigrate.value`), and the start-up read of `sret-ws-section`. Each takes the migrated payload and never reads the old key again.

*Code identifiers (renamed with every reference):*

| Old | New |
|---|---|
| `USER_MILESTONES`, `USER_MS_ENABLED`, `USER_BAND`, `USER_BAND_SOURCE` | `USER_TASKS`, `USER_TASKS_ENABLED`, `USER_TASKS_BAND`, `USER_TASKS_SOURCE` |
| `applyUserMilestones()`, `nextUserMsId()`, `exportUserDefinedSchedule()`, `userDefinedExportRows()` | `applyUserTasks()`, `nextUserTaskId()`, `exportUserTasks()`, `userTaskExportRows()` |
| `openAddMilestone()` / `closeAddMilestone()`, ids and classes `add-ms-*`, `#btn-add-ms` | `openAddTask()` / `closeAddTask()`, `add-task-*`, `#btn-add-task` |
| Workspace section `userms`, ids `ws-tab-userms`, `ws-sec-userms`, `ws-userms-body`, `ws-userms-count`, `WS_TITLES.userms` | `usertasks`, `ws-tab-usertasks`, `ws-sec-usertasks`, `ws-usertasks-body`, `ws-usertasks-count`, `WS_TITLES.usertasks` |
| `ANNOT_CATEGORIES` key `userMs`, label "Milestones added on the board" | `userTasks`, "Tasks added on the board" |

*Words people read:* Workspace button and heading "User tasks"; "Add a task" (header button, dialog, help list); Sources group "User tasks" and its description; status messages ("3 user tasks restored", "Showing user tasks", "Deleted 2 user tasks", "Exported 12 user tasks", "No user tasks yet"); the band label "User Tasks". The board keeps drawing user tasks with the markers they have today.

*Stays the same:* the `USR-` ID prefix, because annotations, comments and dependency links in saved files and other people's copies are keyed by these IDs. **[CONFIRM WITH MATT]**

*Drift check at merge:* the rendered text and the source both contain no `user milestone`, `User-defined`, `User Defined Milestones`, `userMilestones`, `userMsEnabled` or `userms`, except inside `SRETMigrate.KEYS`; an older published file, an older model `.json` and an older user-defined export all load, and saving them writes only the new names. Re-grep at merge: P59 may have added references.

**Built at P63 (TD-223).** The grid module already had `views`/`view`/`onView`, so the switcher is the module's own title menu (a menu button with `aria-haspopup`, arrow keys, Home/End, Esc back to the button, the current view checked); `grid-view.js` is unchanged. The adapter in the app:

- **Views, in order:** User milestones (the P61 config, `userMsGridConfig()`); one view per annotation type that has entries (the P62 configs, `annotGridConfig(type)`, under the Your edits labels; empty types are not listed); Schedule milestones; Schedule updates; All schedule activities. `gridViews()` builds the list with counts from the stores each time a view opens.
- **Switching:** `openGridView(id)` is both the opener and `onView`. It reopens the grid in place with that view's config; the module carries the Back focus across the switch.
- **Back:** every view's `onBack` is `closeGridView()`, which returns to where the grid was first opened (`GRID_ORIGIN`: the section and the button), however many switches came between. The P61 and P62 entry points, `openUserMsGrid()` and `openAnnotGrid(type)`, set the origin; `closeUserMsGrid()` and `closeAnnotGrid()` are folded into it.
- **Narrow screens:** at and below 1024px the Workspace panel overlays the board instead of docking, so a grid opened from it would sit behind it. A fresh open (`gridBegin()`) reads that layout state (`wsPanelDocked()`, the `(min-width:1025px)` query the panel CSS docks on) and, when the panel is open and not docked, closes it with `toggleWorkspace(false)`. Back reopens it with `setWorkspaceSection()` on the same section and focuses the button that opened the grid. Where the panel docks, it stays open, as before.
- **Schedule milestones:** the board milestones, `MILESTONES` less the user milestones, one row per `msKeyFor()` key. **[CONFIRM WITH MATT]** that this is wanted rather than P6 milestone-type activities only; `schedMilestoneSet()` is the one place to change it.
- **Schedule updates:** the schedule milestones carrying any annotation: comment, health, short title, progress override, field edit, a note linking the ID, or a dependency comment on either end of a line. An Annotations column names which.
- **All schedule activities:** `TASKS`, one row per board row (a deliverable, the activities the ingest grouped into it), less user rows. Start, finish, float, status and % complete are read from the row's milestones (earliest start, latest finish, least float, worst status, weighted progress).
- **Columns:** ID, name, band, start, finish, float, status and % complete are read only and show the schedule's own values (under any card field edit). The editable columns are annotations, written through `annotWrite()`, the P62 tables' setters: comment (`MS_COMMENTS`), health (`MS_HEALTH_OVERRIDE`, the card's codes) and short title (`MS_SHORT_TITLES`) on the milestone views; the row's health dot and remark on All schedule activities, which are board rows and have no short title. `schedGridEdit()` refuses every other column. No `onAdd`, no `onDelete`; `TASKS`, `MILESTONES` and the imported sources are never written.
- **Title after an edit:** `syncGridView()` (formerly `syncAnnotGrid()`) rebuilds the open annotation or schedule view and sets the switcher's label text (`setGridTitle()`), so the menu survives, and the view's count in the menu follows.
- **Checked by** `tools/p63_check.py` (TEST-64) at 390x844, 900x800 and 1440x900.

### 4. Schedule changes (`SRETCompare`, Matt 2026-09-28)

Lists what moved between a loaded schedule and a basis: Later, Earlier, Completed, New, Removed, Float only, with old and new start, finish and float and the days moved (**calendar days**, positive is later). Biggest slips first; read-only; exportable; rows can go to the temp list. Tools > Loaded schedules lists what is held.

**Storage by upload, designations by reference (Matt, 2026-09-28).** Every loaded file is stored once under its upload reference. What role it plays is a row in a reference table, so "set this source as the primary" changes one row and copies nothing.

```
SOURCE_DESIGNATIONS                     (per schedule line)
line      designation   source id
project   primary       src-12      the schedule the board shows
project   secondary     src-9       the usual comparison
project   alternate     src-11      another basis kept on purpose (can be an interim)
```

Plus the embedded **Project baseline**. A vendor or contractor schedule is its own line (named at import) with its own three rows and no baseline; lines never compare with each other.

**Each stored upload records:** upload reference, snapshot date (when loaded), data date, file name, file location (typed at import: a browser gives the file name only), coverage (full schedule, or part with the interim's scope), activity count.

**Rules:**

| Rule | Detail |
|---|---|
| Import as primary (the weekly update) | A shortcut for two table changes: old primary becomes secondary, the new upload becomes primary |
| Interim update | Stored with its scope (e.g. Commissioning), no designation. Can be set as secondary or alternate, **never primary**. One kept per scope. Never changes the board |
| Re-designating | Never deletes. An upload that loses its designation stays stored, shown as not designated |
| Retention | On each import, uploads with no designation are released, except the latest interim of each scope and the baseline. So each line holds its three designated uploads, plus interims |
| Default comparison | Primary vs secondary (else baseline); secondary vs baseline; alternate, interim or not designated vs primary |

**Comparing a partial interim.** Activities outside its scope are counted as outside the interim, never Removed or New. An activity only the interim holds is New when the interim is viewed, and "Only in interim" when the full schedule is compared against it.

**What the app must add at merge (it keeps no history today; `PRIMARY_SOURCES` is replaced on import):**
1. **Storage.** Keep each upload's full source record (the tasks and milestones a `PRIMARY_SOURCES` entry already holds) under its source id, not just the comparison fields. The board must be able to render whichever upload is primary, so the full rows are needed. Size: one full source per designated upload and per interim scope, instead of one today. **Decided (Matt, 2026-09-28): keep full copies**, so any stored upload can be made primary without re-importing.
2. **Reference table.** `SOURCE_DESIGNATIONS` as above, persisted with the annotations and publish state. The board renders `SOURCE_DESIGNATIONS.project.primary` (plus enabled external sources as today). Changing the primary calls `scheduleRerender(true)`.
3. **Import** asks: Primary update / Interim update (with scope) / Alternate / an external schedule by name, and the optional location. Before an import releases uploads, the confirmation names them.
4. **Data & view > Sources** shows the reference table and the stored uploads with a Set as control, as in the demo's Tools > Loaded schedules.
5. `SRETCompare` reads the same records: `add()` takes the app's source id as the upload reference.

**Interim dates over the primary on the board (Matt, 2026-09-28: yes, optional).** Tracked as TD-218.
- A View controls toggle, off by default: "Show interim dates". It is display state only; it never changes the primary, the reference table or any stored upload.
- When on, `SRETCompare.overlay(store, {scopes, movedOnly})` gives one mark per activity the interim shares with the primary: the interim's start and finish, the primary's, and the finish slip. The board draws each as an extra marker on that activity's row, styled apart from the baseline ghost (the baseline is the past; the interim is newer than the primary), with a tooltip naming the interim, its scope and data date.
- Options beside the toggle: which interim scopes to show (default all), and "Moved only" (default on) so unchanged activities add no marker.
- Activities only the interim holds have no row on the board; they are counted in a line under the toggle ("1 activity in the interim is not on the board") and listed in Schedule changes as New.
- Dependency lines: interim markers take no part in `drawDepLines()`; lines stay on the primary's markers.

## Verification at merge

1. `python3 tools/grid_view_check.py` still passes on `prototypes/grid-view/demo.html` (unchanged modules). It covers scroll smoothness on 2,000 rows (every visible row present on fast scrolls, no engine wheel handling, transform positioning, per-step cost) the three-row header aligned to the title, the Add row / Tools / Add to temp list menus, the import dialog, the collapsible List column (left of the checkbox, no filter when collapsed) and the temp row mark, the milestone import rules end to end (failures, duplicate IDs, skipped and assigned IDs, the continue question, Cancel, the Import log, `importAoa`), Band and WBS as separate columns, Date created and Created by far right, Health exported last, status tones, the health dot picker, double-click to open, both panel modes, and the four-step lists workflow (temp list built across three filter states, Temp list only, ticked temp items into existing and new lists, one item in two lists, remove, clear with confirmation, the temp list carried across screens, and the single-list setting).
2. `python3 tools/colour_audit.py --strict` and `python3 tools/palette_swap_check.py` on the app, with a grid open for the swap (add the open to the swap check's setup the way it opens the milestone dialog).
3. `python3 tools/theme_check.py` on the app.
4. A merge-stage probe that clicks each of the three real entry points, edits one value per entry point and asserts the value lands in the right store and survives `scheduleRerender(true)` and a publish round trip. That probe does not exist yet: it can only be written against the merged file.
5. The existing suite (`ds_check.py`, `import_check.py`, `persist_check.py`, the `p*_check.py` probes) unchanged.
