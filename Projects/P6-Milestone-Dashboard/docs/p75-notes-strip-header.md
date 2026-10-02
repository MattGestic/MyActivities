# P75: collection strip, header buttons, one-row desktop filter bar

Matt, 2026-10-02 (desktop screenshots). Built on v3.1.0-P74 (2a83203). `APP_VERSION` is not bumped. The milestone card (`#ms-dialog`), the Import panel and the week-range picker are not touched.

## 1. Collection strip (`#collect-bar`)

### Toast

No app-level toast existed. The grid view has its own internal `say()` toast (`.sg-msg`), but it is scoped to the open grid screen. The card's `#ms-saved-flash` belongs to the card. So the app now has a small toast of its own:

- `#app-toast`: a page-level element that is `position:fixed` at the bottom centre. It has `role="status"` and `aria-live="polite"`. It holds a message span and one optional action button.
- `showToast(text, {action, run, ms})` and `hideToast()` are its only writers. A new message replaces the last one.
- It never takes focus and ignores the pointer while faded, so it does not block anything. It dismisses itself after 1.6s by default.
- It is outside the card and its click-away rule: a click on the toast stops at the toast, so pressing Undo never closes an open card.
- Tokens only: `--color-tooltip-bg`, `--color-text-on-header`, `--color-text-on-header-accent`, `--shadow-2`, `--radius-overlay`, `--space-*`, `--group-gap`, `--text-md`. This is the same treatment as the grid's `.sg-msg`.

The double click (or double tap) on a marker now calls `collectMsFromBoard(id)`, which wraps `addToMsCollection()`:

- When an ID is added, the toast reads "SNIP-123 added" and the new chip pulses briefly. The pulse reuses the existing `.is-landed` animation, which also handles reduced motion.
- When the ID is already collected, the toast reads "Already in the list".

### Add to list

**The Lists module is not in the app.**
- `SRETCollections` and the grid's `lists` feature exist only as source under `src/modules/collections/` and `src/modules/grid-view/features/lists.js`.
- P70 embedded the grid core plus `marks`, `bulk-edit` and `xlsx`, but not `lists`.
- `USER_LISTS` and a "Lists section" do not appear in the app.

Add to list is therefore the fallback case:
- The button is enabled: `aria-disabled` and the dimmed style are removed.
- `addMsCollectionToList()` shows the toast "Lists come with the Lists section. Use Copy to take the IDs for now." The collection does not change.
- When Lists lands, `addMsCollectionToList()` is the single place to wire it.

### Order and clear-all

The strip now runs, left to right:
1. Add to list
2. Copy (the clipboard icon, moved from the far right)
3. `#collect-div`, a 1px vertical rule (`--color-line-default`)
4. The chips, still on one line and scrolling sideways
5. `#collect-clear`, a clear-all cross with `aria-label="Clear all collected IDs"`

`clearMsCollection()` empties the collection. Its toast reads "N IDs cleared" and offers **Undo** for 4s. Undo puts back the same IDs in the same order, stores them again and confirms "Collection restored".

## 2. Header buttons anchored left

`.rpt-hd-actions` loses `margin-left:auto`. The filter toggle and + Milestone now follow the View toggle / Baseline shadow group on the details row at every width.
- While that group is hidden (one schedule, nothing to compare), the two buttons are first on the row.
- At phone width the row wraps, the pair starts the second line, and nothing overflows.
- The icon group in the icon bar stays top right.

## 3. One-row desktop filter bar

**Threshold:** the bar width must be at least `FB_WIDE_MIN` = **1636px**. With the rail shown, that is a **1680px viewport**. The bar width is computed as the viewport less the rail and any docked panel, the same layout state `syncFbNarrow()` already uses for `.fb-narrow`. At or above the threshold the bar gets `.fb-wide` (never at phone width):
- `.fb-top` becomes `display:contents`, so Find, Date range and the status box form one flex row. There is no DOM move, and `syncFbShape()`'s phone moves are untouched.
- Find and Date range share the remaining width equally. The status box takes its natural width.

**Decision: the status box stacks its groups in this layout.** On one line its chips need about 1240px. Beside Find and Date range that would need a screen of about 2150px, so it cannot fit at 1920.
- In `.fb-wide` the box becomes a three-row grid: Status, Total float, Annotations.
- It uses a right-aligned label column, the same D-16 field-row pattern as Find and Date range.
- Each chip group stays whole on one line, with the clear cross top right. The separators are hidden because the rows separate the groups.
- The row is about 106px tall, against 148px for the old two rows.

**How the threshold was found** (measured, not assumed). The one-row layout was forced on at a range of widths. At every width from 1280 up, nothing wraps inside the boxes, and from 1440 up no box overflows. The binding constraint is the Weeks field, which has its own 220px design minimum:

| Viewport | Weeks field width |
|---|---|
| 1640px | 206px |
| 1680px | 226px |

Below 1680 the two-row layout stays, so 1600 to 1679 is unchanged. The check tests both sides of the boundary at 1679 and 1680.

The phone layout is unchanged: `.fb-wide` is never set with `.fb-phone`, and every rule is scoped `:not(.fb-phone)`.

## Checks

New: `tools/p75_strip_header_check.py`. It covers 390, 1024, 1440 and 1920, plus 1679 and 1680 for the filter boundary, and asserts:
- the toast appears and disappears on add and on duplicate;
- the pulse on the new chip;
- the strip order, read from x positions;
- the divider is present;
- clear-all, Undo, and the Undo toast expiring;
- Add to list;
- the header buttons sit after the View group and anchor left;
- the icon group stays top right;
- the three filter boxes share one row at 1920 and 1680, with nothing wrapping and nothing overflowing;
- a docked Data & view panel at 1920 narrows the bar and returns the old layout;
- the old layout at 1679, 1440 and 1024;
- the phone shape at 390;
- no horizontal page scroll.

Assertions changed (none deleted):

| Check | Before | After |
|---|---|---|
| `p68_check` | `row: Add to list on the left, copy on the right`: add.right <= chips.left and copy.left >= chips.right | `row: Add to list on the left, copy next to it before the chips (P75)`: add.right <= copy.left and copy.right <= chips.left |
| `p68_check` | `row: Add to list is present but inert for now`: `aria-disabled="true"` | `row: Add to list is present and enabled (P75)`: no `aria-disabled`, not disabled |
| `p32_check` | `defect A: and that control sits on the right-hand side (of the header)`: under 160px from the header's right edge, in its right half | `defect A: and that control sits on the left of the header, after the View group (P75)`: in the header's left half, and either at or after the View group's right edge (group shown) or first on the row (group hidden) |

Results (`python3 tools/run_checks.py --jobs 3`, 2026-10-02):

- **First round.** 61 checks ran: 59 passed and 2 failed.
  - `d15_check` caught a real fault. The toast's action button was empty while hidden, and every text-less button needs an aria-label. It now carries "Undo" as its text, and d15 passes 11/11.
  - `p30_check` timed out at 600s. The machine was running four agents' suites at once, with a load average around 22 on 4 cores. On re-run it passed 68/68.
- **Second round.** `grid_view_check` failed only its timing assertion: scroll p95 under 8 ms, measured at 29.9 ms and then 9.6 ms under the same load. P75 changes no grid code or CSS, and the check passed on re-run (p95 1.9 ms).
- **Final.** The last round was 8 selected / 54 skipped / 8 passed / 0 failed. Every one of the 62 ledger records is a pass, including `p75_strip_header_check` at 221/221, `p68_check` at 89/89, `p32_check` at 38/38, `p59_check`, `p64_check` at 129/129, `p39_check` at 117/117, `ds_check` at 132/132, `p67_check` at 269/269 and `p72_filter_scroll_check` at 293/293.
