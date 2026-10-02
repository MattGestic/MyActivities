# P78 notes: Discipline, Supervisor and Engineer

Matt's request of 2026-10-02, on top of v3.1.0-P75 (`643bca6`). `APP_VERSION` is not bumped. No TD or TEST entries were added; this file is the record.

> "Extend the import and schedule table to include the fields for discipline, supervisor, and engineer. These may be fields that are set and imported with the schedule or they may be allocated manually by the user. The fields in the card should be included underneath the title: Wbs/ Area | Discipline, Supervisor | Engineering. Fields for the supervisor and engineer, if populated, should just show their name. If blank show the field name and it should be a search box or free text that the user can start entering. If there are already supervisors listed, it should provide a tooltip to use one of the already set ones."

"Engineering" in the request is read as Engineer.

## Data decisions

### `discipline` is a new per-milestone field, not the existing `disc`

`disc` is a row field. The ingest derives it from the WBS path (the segment after "Engineering", or the second-last segment, else "Unassigned"). It is the heading the board groups rows under (`tr.disc`), and the card's meta line shows it as the band.

`discipline` is kept separate from it, for four reasons:

- **It is per activity.** A Discipline column in a P6 export is a value per activity, so per milestone. One row can hold several activities whose disciplines differ.
- **`disc` drives the board's grouping.** Writing an edited or imported discipline into `disc` would move rows between band headings. A card edit would then rebuild the board's structure. That edits the schedule layer from the annotation layer.
- **The two can disagree.** `disc` is often "Unassigned" when a real discipline is known. A WBS band named "Electrical" can hold an activity whose trade is something else.
- **D-28 settles it.** D-28 already plans a row value with activity exceptions for Discipline. A per-milestone field is the "activity" half of that. The row half is the band, which stays as it is.

So:

- **The band is shown as WBS/Area.** It is the row's `disc` heading, or the row's phase when `disc` is "Unassigned" (`msWbsAreaText()`). It is read only.
- **Discipline is a field of its own.** It is imported, or set by hand.

### The model

- `discipline`, `supervisor` and `engineer` are plain strings on the milestone, set by `aggregate()` from the activity's own row. A blank cell leaves the property absent.
- They are in `MS_EDITABLE_FIELDS` (the app) and `MS_FIELDS` (`src/modules/notes-store/notes-store.js`, re-pasted). So a hand value is an override, never the schedule:
  - the card and the grids write an entry, with `changes.discipline`, `supervisor` or `engineer` set to `{from, to}`;
  - `projectEntries()` projects it into `MS_FIELD_OVERRIDE`;
  - `applyFieldOverrides()` lays it over the board copy, and keeps the schedule's value on `_msBase`.
- A value equal to the schedule's is not stored. A blank value is `to:null`, which goes back to the schedule's value.
- `from` is `null` (not `undefined`) for a field the schedule did not carry. That applies to the card (`saveMsDialog`'s `current()`) and the grid (`addFieldEntry`). The history then reads "Supervisor none → J. Smith".
- **A bug found by the check and fixed.** `applyFieldOverrides()` now keeps `null` on `_msBase` for an absent field. Before, it kept `undefined`. A published file carries `_msBase` as JSON, which drops `undefined`, so a reopened publish read the override back as the schedule's own value.
- **User milestones:**
  - On the card, they work like every other field: an entry, projected as an override on the `USR-` key. Their title and finish already did this.
  - In the User milestones grid, they write the record, the path that grid's name and type take (`userMsGridEdit`). A card override on the same field is dropped with the write, as for the name.

### Import

- `INGEST_CONFIG.headerAliases` gains three fields:

  | Field | Aliases |
  |---|---|
  | `discipline` | discipline, disc, trade |
  | `supervisor` | supervisor, superintendent, lead |
  | `engineer` | engineer, responsible engineer, owner |

- They are listed last, so every older field gets its column first.
- `autoMap()` maps them only to a column no other field has taken (`INGEST_CONFIG.peopleFields`). So an Owner column already mapped elsewhere stays where it is. The older fields' rule is unchanged.
- The mapper lists them last, as optional (no required mark), and `runIngest()` reads their selects.
- The P75 panel order, headings and badges are untouched. `p75_import_check` passes.
- The user-defined schedule export (`userDefinedExportRows`) carries Discipline, Supervisor and Engineer as its last three columns, under those names. A re-import maps them back.

### Persistence

| Path | What travels |
|---|---|
| Schedule values | They are properties of the milestones, so they travel wherever milestones do: publish (`tasks` / `milestones`), the model export, and the source registry. |
| Overrides | They travel as entries, plus the `milestoneFieldOverrides` projection. So they survive publish, model export, mount and the P64-era migration (`migrateLegacy` reads them from `milestoneFieldOverrides`). |
| User milestone records | They travel in `userMilestones`. |

Mounting a model file applies annotations, not the schedule. The schedule values come from the schedule import, as before.

## The card

### Layout

- `#ms-people` sits directly under `.ms-title-row` and above `.ms-schedule`. It is a 2x2 grid:
  - row 1: WBS/Area | Discipline;
  - row 2: Supervisor | Engineer.
- Each cell is one `--ctl-h` high, left aligned, with no border, in the P75 row's shape. The styles use tokens only.

### Behaviour

- **WBS/Area** (`#ms-wbs`) is read-only text. When there is none, it shows "WBS/Area" muted.
- **Discipline, Supervisor and Engineer** are inputs (`#ms-discipline`, `#ms-supervisor`, `#ms-engineer`), styled as the card's read-first fields:
  - **populated:** the name as plain text, with no fill and no border; a click makes it editable;
  - **blank:** the field name is the placeholder, in muted ink, in a subtle box (`:placeholder-shown`).
- **Suggestions** use one list, `#ms-pf-suggest` (`role="listbox"`). It sits inside the card and is fixed-positioned under the field. Each input is a `combobox` with `aria-controls`, `aria-expanded` and `aria-activedescendant`.
  - **Contents:**
    - On focus, it lists the names already used for that field across the board.
    - Typing narrows the list to names that contain the typed text.
    - The hint line reads "Pick an existing name or type a new one".
  - **Order (`msPfOptions`):**
    - Each milestone counts once, for the value it shows (an override, else the schedule's).
    - An imported name that has since been overridden is still offered.
    - Names that differ only in case are one entry, shown in the spelling used most.
    - Most used first, then by name. At most 8 are shown.
  - **Picking:**
    - A pick is on `onmousedown` with `event.preventDefault()`, the Activity ID autocomplete's rule. The field keeps focus and the card stays open.
    - ArrowDown and ArrowUp move a highlight. Nothing is highlighted at first, so Enter keeps the typed text (free text).
    - Enter on a highlighted name picks it.
    - Esc closes the list first. A second Esc leaves the card (and saves), as in P75.
- **The P75 card rules still apply:**
  - the fields make the card dirty and take the dirty tint;
  - a click away and Esc save;
  - the × discards;
  - the edited mark (`#ms-mark-<field>`) shows the schedule's value ("Previous: (none)" when the schedule had none).
- **A save that keeps the card open** repaints the three fields from the stores (`renderMsPeople`). A cleared field therefore shows the schedule's value again.
- **History:** `src/modules/notes-history/notes-history.js` labels the changes Discipline, Supervisor and Engineer, after the older fields:
  - a new value reads "Supervisor none → J. Smith";
  - a clear reads "Supervisor J. Smith → schedule value".
- **The store's 10-minute coalescing applies.** A second card save on the same milestone inside the window folds into the first. A value set and then cleared inside the window leaves no entry at all. That is the store's existing rule; the check moves the clock past the window to record a clear on its own.

## Schedule table (grid)

- **Schedule milestones** and **Schedule updates** gain Discipline, Supervisor and Engineer columns. They are editable:
  - they show the value the card shows;
  - they write through `schedPfWrite()` as an entry (`origin:'grid'`), projected as an override, as the card does;
  - blank, or the schedule's own value, goes back to the schedule.
- The schedule columns stay read only (`schedGridEdit` still refuses them).
- **All schedule activities** is one row per deliverable (several milestones), so it has no single value per field. The three columns are not added there.
- **User milestones** gains the three columns, editable, written to the record.
- The **Milestone field edits** annotation table labels them (`MS_FIELD_LABELS`) and edits them like any other field.

## Not built: Banding filter or board grouping by these fields

**Filter:** moderate, about a day.

- These are per-milestone values, not row values.
- A filter would be a milestone-level select fed by `msPfOptions()`, applied in `applyFilter()` the way Activity ID(s) is, plus its checks.

**Grouping the board:** large.

- Rows are deliverable chains grouped by the WBS band, and a row's milestones can differ.
- That is D-28's row value with activity exceptions (mixed indicator, sub-rows) on D-23's hierarchy model: FEAT-27, not a small change.

## Checks

New: `tools/p78_fields_check.py`. It runs at 1440 and 390 with real pointer, mouse and key events, on N=3 milestones (two schedule milestones and one user milestone).

- **Import:**
  - The reference export (`build_aoa`) is extended with Discipline, Superintendent and Responsible Engineer columns.
  - It is pasted into the app as it ships (`sret:no-fixture`).
  - It checks auto-map and the mapper, and that the values land on every milestone.
- **Layout:** measured on the elements themselves.
- **Display:** populated and blank.
- **Suggestions:**
  - order and dedupe;
  - typing;
  - a mouse pick;
  - a keyboard pick;
  - Esc;
  - free text.
- **Entries, history, edited marks and clearing:**
  - a clear back to blank;
  - a clear back to an imported value.
- **The grids** and the user-defined export.
- **At 1440 only:**
  - the publish, opened in a fresh profile;
  - the model export, mounted into a fresh app with the test fixture.

Module tests gained P78 cases:

- `tools/notes_store_test.mjs`;
- `tools/form_to_entry_test.mjs`;
- `tools/notes_history_check.py`.

### Assertions changed (none deleted)

| Check | Before | After |
|---|---|---|
| `p43_check` | `source: the ID and the relationships are absent from the editable list` matched `const MS_EDITABLE_FIELDS=['actName','start','date','weight','type','marker','actual','startActual']` | The same assertion, matching the list with `'discipline','supervisor','engineer'` appended (on a second line) |
| `p61_check` | `[grid] its header is the grid's columns, Health last`, expecting `...,'Comment','Health'` | The same assertion, expecting `...,'Comment','Discipline','Supervisor','Engineer','Health'` (the User milestones grid gained the columns, and its own export follows them) |
| `p61_check` | `[grid] the sheet carries the edited name, comment and health`, Health read at index 8 | The same assertion, Health read at index 11 (the three new columns sit before it) |
| `d17a_check` | `export header matches the importer's own column names exactly`, expecting the 11 columns ending `'% Complete'` | The same assertion, expecting `'Discipline','Supervisor','Engineer'` after `'% Complete'` |

`p44_check` (`marker` is in `MS_EDITABLE_FIELDS`) and `p72_deps_check` (no `floatD`) match a prefix or a pattern, so they pass unchanged.

### Results

- `python3 tools/p78_fields_check.py`: `196/196 checks passed`. That covers 1440 and 390, plus the published copy and the mounted model.
- Module tests:
  - `node tools/notes_store_test.mjs`: `139 passed, 0 failed`;
  - `node tools/form_to_entry_test.mjs`: `85/85 passed`;
  - `python3 tools/notes_history_check.py`: `74/74 passed`.
- `python3 tools/run_checks.py --jobs 3` (2026-10-02, on `643bca6` plus these edits): `65 selected / 1 skipped / 63 passed / 2 failed (wall 34.2 min, 3 jobs)`.
  - **`p61_check` 93/95.** The User milestones grid export now carries the three columns. The two assertions were updated (table above), and it then passed 95/95.
  - **`p30_check` timed out at its own 600 s subprocess limit** under the 3-job coverage run, while the machine's load average was about 8 on 4 cores. Standalone and back to back, it passed 68/68 against both the base file and this one, in a comparable time (72 s base, 77 s P78). So the timeout was load, not this change.
- Re-run of both through the runner (`--only p30_check,p61_check`): `2 selected / 0 skipped / 2 passed / 0 failed`. `p30_check` took 542 s there, inside the limit.
