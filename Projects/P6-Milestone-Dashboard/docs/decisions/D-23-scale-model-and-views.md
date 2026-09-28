# D-23 to D-29: Scale, schedule model and saved views

**Status:** Proposed, agreed in principle with Matt on 2026-09-27. Not built. This file is the single source for the design; the kit rows in `01-requirements.md`, `02-backlog.md`, `03-todo.md` and `04-architecture.md` reference it by D number rather than restating it.

**Why this exists:** the full Eskay Creek live schedule (XER, all activities, full logic) was run through the real import path and the board was not serviceable at its current size, and degraded faster than linearly at twice the size. Results and method: `docs/perf/Scale_Measurement_Log.md`, TEST-59. The design below fixes the cause, then builds the grouping and view features on the corrected model so they are not built twice.

| D | Subject | Backlog | Supersedes or extends |
|---|---|---|---|
| D-23 | SheetJS embed: placement and audit handling | TD-216 | Detail for TD-216; resolves TD-36 / TASK-41 |
| D-24 | In-app XER import alongside Excel and paste | FEAT-24 | Resolves TD-21; TD-22 must close first |
| D-25 | Schedule model | FEAT-25 | Designed together with D-02 (FEAT-18) and FEAT-19 |
| D-26 | Batch rendering | FEAT-26 | Replaces the per-week cell board |
| D-27 | Hierarchies, saved views and the view selector | FEAT-10 (re-specced) | Replaces the FEAT-10 phase-band spec; absorbs TASK-09, TASK-26, TASK-31 |
| D-28 | Discipline and Activity Owner fields | FEAT-27 | New |
| D-29 | New since last import control | FEAT-21 (D-12) | Extends it |
| (D-10) | Change register export | FEAT-20 | Matt chose option A on 2026-09-27: register only, no XER patch |

---

## D-23 SheetJS embedded: placement and audit handling only

**The embed itself is TD-216** (Matt, 2026-09-28: SheetJS embedded, never fetched), under the vendoring rules in `CLAUDE.md` Hard constraints (permissive licence, inline with its licence text, `vendor/sheetjs/SOURCE.md` with version, URL and sha256, no network request at runtime). TD-216 also sets the **version**: a release with the fixes for the two published advisories against 0.18.5, and full or mini build is open with Matt there. This section adds only what TD-216 does not say:

- **Placement:** the `<script id="vendor-sheetjs">` block is the last element inside `<body>`, after `#app-script`. Not after `</body>`: the parser silently moves it back into the body, and markup after `</body>` is a parse error. Not before `#app-script`: it would parse a library most sessions never use ahead of the app. Verified in Chromium on 2026-09-27: all three placements run; only the in-body ones are valid HTML.
- **`ensureXLSX()`:** it already returns early when `XLSX` is defined. TD-216 goes further and removes the script injection entirely, which supersedes the "keep the CDN branch as a fallback" idea this section first carried.
- **Audits:** every tool that scans the whole file skips vendored `<script id="vendor-*">` blocks, as it must already for SlickGrid (D-09), so colour, spacing and em-dash counts measure the app only.
- Verified on 2026-09-27 with 0.18.5 embedded: the reference export parsed offline through `Parse.workbook()` to the row count recorded for it in `04-architecture.md`, with no network requests. The same check is repeated on the version TD-216 settles on.

## D-24 In-app XER import

- A JavaScript port of `tools/xer_to_aoa.py`, similar in size, no library. A minimal JS table reader was timed on the client XER; see `docs/perf/Scale_Measurement_Log.md` metric `xer_table_read_ms`.
- **All three formats stay supported:** `.xlsx` (SheetJS), paste/CSV/TSV (`Parse.delimited`), and `.xer`. All three feed one model builder (D-25). XER skips the column mapper because its fields are named.
- A check runs the reference `.xlsx`, a pasted copy of it, and an XER through the builder and asserts the same activities, dates, links and headings wherever the sources carry the same data.
- **TD-22 closes first:** durations and float convert with each activity's own calendar hours per day (`TASK.clndr_id` to `CALENDAR.day_hr_cnt`), not a fixed 8.
- The XER carries far more than the dashboard uses (resources, UDFs, activity codes, notebooks). Only what the model needs is read; activity codes are kept available for a future hierarchy type (D-27).

## D-25 Schedule model

Replaces the parallel flat arrays and comma-string logic with one model, built only on import. Nothing is read back from the DOM.

| Part | Contents | Editable |
|---|---|---|
| `Activity` | Imported values, frozen. Getters resolve the effective value: annotation override, else imported value. **One place** a value is resolved. | No (overrides go to the annotation layer) |
| Links | Predecessor/successor objects `{from, to, type, lag}`, parsed once | No |
| `HierarchyNode` | One node type for every hierarchy: name, parent, children, rows. Roll-ups (start, finish, lowest float, weighted progress, counts, worst health) computed bottom-up once per hierarchy. | Base hierarchies no; saved views yes (D-27) |
| Row | A deliverable stage chain (existing row-building logic, unchanged). Group then Row then Activity. | Membership editable in saved views |
| `Schedule` | Indexes, data date, timeline. Rebuilt on import only. | No |
| Annotation stores | Unchanged in shape, still separate, still exported | Yes |

- The three-layer rule (schedule data / annotation / display state) is preserved and made structural: imported values are frozen.
- Export stays byte-compatible through explicit `toJSON()`.
- **Sequencing with D-02 and FEAT-19:** D-02 moves schedule data into a JSON envelope with a schema version, and FEAT-19 wraps the annotation stores in an edit ledger. Both touch the same stores as this model. Build D-25 as the in-memory side of D-02's envelope, and route D-27/D-28 annotation writes through FEAT-19's ledger, rather than building three overlapping layers.
- Migration is staged: model plus a compatibility view first with every existing check passing unchanged, then rendering moves over.

## D-26 Batch rendering

The measured cause of the slowdown: the board creates one table cell per row per week, so cell count is rows x weeks, while only a screenful of rows is visible (metric `visible_rows`). Style recalculation and layout of those cells dominate import time. Dependency lines read each endpoint's position from the laid-out page, so their cost grows with both line count and page size, which is why they scaled worst.

| Principle | Change |
|---|---|
| One timeline cell per row | The week columns become one cell per row. Week gridlines are a painted background; markers are positioned at week index x column width. Same look, same rows, same headings. An isolated micro-benchmark at client scale compared the two shapes; see metrics `microbench_per_week_ms` and `microbench_one_cell_ms`. |
| Build once, filter by class | Filters evaluate on the model and toggle one class per row. No rebuild on filter, only on data change. |
| Compute on the data | Roll-ups, aggregates and levelling on the model (D-25). Dependency line geometry from row index and date, not `getBoundingClientRect`. |

- `drawDepLines()` stays the single entry point with its defensive reset; only its geometry source changes.
- Touches row building, `dateToCol()` placement, the same-row label collision system and print. Each gets a check; the collision history in `06-lessons-learned.md` applies (test N=3, both bounds).
- **Gate:** `tools/scale_bench.mjs` is re-run after each stage and appended to the measurement log. A stage that does not improve the numbers is not merged on the strength of a code read.
- Row virtualisation (render only rows near the viewport) is **not** planned. It breaks print, sticky headers and off-screen dependency stubs, and is only reconsidered if the above falls short.

## D-27 Hierarchies, saved views and the view selector

### Hierarchies (the "group by" types)

| Type | Built from | Built when | Editable |
|---|---|---|---|
| Indent | Activity ID indentation of the export | Import | No |
| WBS | XER `PROJWBS`, or a mapped WBS column | Import | No |
| Discipline | D-28 field | On change | No (group order yes) |
| Owner | D-28 field | On change | No (group order yes) |

- Each is an independent `HierarchyNode` tree over the same rows. Every activity appears exactly once per hierarchy.
- Availability by source: Excel gives Indent (and WBS only if a WBS column is mapped); paste gives Indent if leading spaces survive; XER gives WBS, and its Indent is the same tree because an XER has no layout. An unavailable type is shown disabled with the reason.
- No WBS or indentation detected: activities go under one **Ungrouped** heading and Diagnostics reports the count. No structure is invented.
- WBS headings with no activities are hidden by default, with a View setting to show them `[CONFIRM default]`.
- Future type on the same node: an XER activity code (area, discipline, system).

### Saved views

- A saved view belongs to one type and is stored as **changes from that type's system view**: moved rows and activities, added/renamed/deleted/reordered groups, removed rows. Size per view measured at client scale for both storage forms; see metrics `view_delta_kb` and `view_full_kb`.
- Storing changes gives inheritance for free: anything the user has not moved follows the system position on every import.
- Several views per type, soft cap **10 per type** `[CONFIRM]`. Measured cost of more views is negligible: only the active view is drawn, and reconciling each view on import is small (metrics `view_reconcile_ms`, `view_switch_flatten_ms`).
- Views are annotation data: saved with the file (publish) and in the JSON export and selective import. Which view is active is display state.
- Existing edits become view operations: marker moves between rows (`MS_MOVES`), removed rows (`DELETED_ROWS`), user rows and headers (`USER_ROWS`). Their checks (`persist_check.py` and others) must keep passing.

### Editing workflow

| Situation | Behaviour |
|---|---|
| Edit while on a system view | It becomes "WBS (unsaved)\*". No dialog. |
| Edit a custom view | Its title gains \*. No dialog. |
| Save on a custom view | Overwrites it |
| Save on an unsaved view | Asks for a name; at the cap, asks which view to replace |
| Switch view with unsaved changes | Save, Discard, Cancel |

No dialog interrupts a drag. The choice is made at save time, as in model-driven apps.

### Delete rules

| Action | Result |
|---|---|
| Delete a row holding activities | Blocked, with the count and a "Move activities to" shortcut (as today: `deleteRow()` refuses a row with milestones) |
| Delete an empty row | Allowed after confirmation (as today) |
| Delete a group with contents | Allowed; its rows move to the parent group. Nothing is lost. |
| Delete anything on a system view | Starts an unsaved custom view |

Activities are schedule data: they can be moved, never deleted.

### View selector

One control at the top of the board, **single list** (decided 2026-09-27), sectioned by type:

```
[ Owner · Internal Wkly Meeting *  v ]
   Search views
   BY INDENT      Indent (system), <custom views>
   BY WBS         WBS (system) [default], <custom views>
   BY DISCIPLINE  Discipline (system), <custom views>
   BY OWNER       Owner (system), Internal Wkly Meeting *
   Save | Save as | Discard | Rename | Delete | Set default
```

- The title always shows type and view name; \* marks unsaved changes.
- Save as creates the view under the current type.
- Disabled types show why.

## D-28 Discipline and Activity Owner

| Field | Input | List |
|---|---|---|
| Discipline | Pick from a user-defined list | Add, rename, reorder, retire; rename propagates. Seeded from the discipline the app already derives, and from an XER activity code if mapped `[CONFIRM which code]`. |
| Activity Owner | Free text with suggestions from names in use | Kept as a list so a spelling fix propagates |

**Row value with activity exceptions (decided 2026-09-27):**
- A row carries one value per field; its activities inherit it.
- An activity may override it. Only overrides are stored, so exceptions are always explicit. Setting an activity back to the row's value removes the override.
- Resolved value = activity override, else row value.
- In Discipline and Owner views the row keeps its chain and sits under its row value, with a **mixed indicator** (for example "1 of 4 differs"; hover lists the exceptions; the exception's marker is outlined).
- **Sub-row toggle** (View setting, off by default) draws exceptions on an indented sub-row under their parent row.
- Group totals count by each activity's resolved value, so reporting is accurate. The group that owns an exception shows "includes N activities displayed in another group" with a click-through.
- Bulk assign at row, group or selection level. Row-level assign offers to clear existing exceptions.
- Both fields are annotation data: exported, published, listed in the change register (D-10) by activity.

## D-29 New since last import

After each import, in the notification area:

- **"N new activities since last import"**, with:
  - **Apply system positions to all**: each new activity takes its system-determined position in every custom view at once (per-view option available).
  - **Expand**: list of ID, name, proposed group, start, finish, with checkboxes to apply a subset.
  - **Export to Excel**: ID, name, WBS, proposed group, start, finish (uses the SheetJS embedded by TD-216).
  - **Copy IDs**: comma-separated, no spaces, for example `A1010,A1020` `[CONFIRM spacing]`.
- Unapplied items stay in a **New since last import** group until placed.
- The same control reports **"N activities no longer in the schedule"** so removals are as visible as additions.
- This is the first slice of FEAT-21 (D-12 import reconciliation), not a separate mechanism.

## D-10 Change register (Matt's choice, 2026-09-27)

- **Option A only:** an `.xlsx` register of Activity ID, field, imported value, dashboard value, who, when. The scheduler applies it in P6.
- No XER patch and no regenerated XER. "Never writes back to P6" stands unchanged; FEAT-20 already describes this workbook.
- Built on D-25: every difference between an activity's imported value and its resolved value is one register row.

## Deferred, recorded so it is not re-derived

- **D3 for new views** (logic view, milestone trend analysis, S-curve, float erosion): vendored as a module subset, not the full bundle. Module groups: scales and axes; label collision (`d3-quadtree`, `d3-force`); optional zoom. Sizes in metrics `vendor_*_kb`. Not used for the existing board. vis-network was assessed and not chosen (canvas rendering breaks CSS theming and DOM-based checks; no date axis; cannot be trimmed without a build step). Mermaid not chosen (bundle size, metric `vendor_mermaid_kb`). Any D3 modules follow the same vendoring rules as SlickGrid (D-09) and SheetJS (TD-216).
- **Logic quality checks** (open ends, SF links, negative and large lags, constraints) into the existing Diagnostics channel: plain JavaScript, no library.

## Open items

| Item | Proposed default | Owner |
|---|---|---|
| Order of D-23 to D-29 against the current staged plan (D-16c then D-02 with D-06) | D-23 first (small, independent); D-24 to D-26 with D-02; D-27 to D-29 after FEAT-19 | Matt |
| Saved-view cap per type | 10 | Matt |
| Copy IDs spacing | No spaces | Matt |
| Empty WBS headings | Hidden by default | Matt |
| Discipline seed from XER activity code | Which code | Matt |
