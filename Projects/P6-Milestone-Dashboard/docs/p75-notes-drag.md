# P75 notes: a drag across week columns moves the Finish

Matt, 2026-10-02: "Drag and drop functionality for milestones should also extend to the columns which would then change the end date of the field."

Working notes for the orchestrator to fold into the kit. No TD or TEST entries were added here.

## What changed

All in the board drag code of `src/milestone-dashboard.html` (`MS_DRAG`, `msDragBegin`, `msDragEnd`, `attachMilestoneDrag`, the pointer listeners) plus the new helpers beside them. `moveMilestoneToRow` and `applyMilestoneMoves` are unchanged.

- **Column move.** A drag ending in a different week column moves `m.date` by whole weeks, weekday kept (`msShiftWeeks`). Row and column can change in one drag; the row move is the existing `moveMilestoneToRow`.
- **Saved as an entry.** `msSetFinishByDrag` calls `addFieldEntry(msKeyFor(ms),'date',iso)`. When the new date is the schedule's own date, it writes `to:null`, which clears the override, the same rule as the card's `formToEntry`. Only `date` is in the change, so the A flag and the Start are untouched. The D-18 edited mark `*` and the ghost tick at the source week come from the existing `msEditedFields` path. No new code was needed for them, and the check verifies both.
- **Order in a combined drag.** The date entry is written first and the row move second. `moveMilestoneToRow` re-keys entries for a milestone with no Activity ID, so the new date entry moves with the milestone.
- **User milestones (`USR-`).** These take the same `addFieldEntry` path, keyed by the ID, because that is how their card saves a date. The user-milestone grid reads the new date through `umsEffective`. Under D-18 they show no `*` and no ghost tick, because they have no source to differ from. The check asserts that.
- **Preview.** While dragging, the ghost snaps to the centre of the target cell: the target week's x, and the target row's y (or the source row's y when the pointer is not over another row). A floating label `#ms-drag-date` under it uses the popover look (`.ms-health-pop` tokens) and reads e.g. `22-Oct-26 (+2 wk)`, or `08-Oct-26 (no date change)`. When the drop would be refused it reads `Before Start 01-Oct-26` in the critical tint.
- **Esc** cancels a live drag. The listener runs in the capture phase and is stopped there, so the panel Esc handler does not also close a drawer. The release's click is swallowed.
- **Undo toast.** `msDragToast(text, actionLabel, action)` and `msDragToastClose()` use `#ms-drag-toast` / `.ms-drag-toast`. The toast is self-contained, names everything for the drag so a shared toast can absorb it later, and is removed from the DOM when it closes. It reads `Finish moved to 22-Oct-26.` with Undo and lasts `MS_DRAG_TOAST_MS` (4 s). Undo (`msUndoDragMove`) adds a new entry back to the earlier date and never deletes one. On a combined drag it also moves the row back, through `moveMilestoneToRow`. No app-wide toast helper existed. The grid view's own `say()` is internal to that module.
- **After the drop:** `scheduleRerender(true)`. `rerender()` already runs `applyFilter()` and `drawDepLines()`, so lines redraw and a milestone can leave or enter the week range. The check counts both calls.

### Two existing drag defects fixed on the way (drag code only)

1. `MS_DRAG.suppressClick` could be left `true` by a drag released off its marker. A browser sends that click to the common ancestor, so no marker handler cleared the flag, and the next plain click on any marker was swallowed. It is now reset on `pointerdown`. The semantics are otherwise unchanged: a drag's own trailing click is still eaten.
2. `holdTimer` was cleared but never nulled. After any touch drag, `pointermove` read the stale id as "touch press still waiting" and cancelled the next mouse drag. It is now nulled in `msDragBegin`, `msDragEnd` and on `pointerdown`.

## Decisions

- **Snapping:** the ghost snaps to the target cell (both axes) and does not follow the pointer freely. The drop targets are the week cells on the board (the date range) that are at least partly in view: not scrolled under the sticky name column, and not past the board scroller. A pointer beyond either end clamps to the first or last of those cells. The board does not auto-scroll during a drag, which is the existing behaviour.
- **Start-date rule: refuse.** If the new Finish would be before the milestone's own Start, the whole drop is refused (row change included, so a diagonal drag never half-happens). The preview already says so, and a toast explains why, with no Undo. Clamping was rejected because it silently lands somewhere the user did not point. The Start never moves.
  - **What counts as "its own Start".** A Start that differs from the schedule Finish, or a schedule Start the Finish was derived from (`finishFromStart`), or a Start set by hand. A true zero-duration milestone carries `start === finish`, and the card shows that as no start (a dash). Refusing every leftward drag of those would make the column move work in one direction only, so they are not constrained (`msOwnStart`).
  - **Consequence, not changed here.** After a zero-duration milestone is moved, its stored start no longer equals its finish, so the card's `isRealTask` test starts showing that start. A Finish typed into the card does exactly the same today. The card is another agent's area, so this is flagged rather than fixed.
- **Touch:** the existing drag is one pointer-event path for mouse and touch (touch starts on press-and-hold). The column move uses the same path, so it works on touch. The check drives a touch press-and-hold drag at both widths with synthetic `pointerType:'touch'` events. It was not tried on a physical device.

## Verification

`tools/p75_drag_date_check.py` runs at 1440x900 and 390x844 in headless Chromium with the fixture. It dispatches `pointerdown` on the marker, then `pointermove`/`pointerup` through the element under the point, each with its matching `mousedown`/`mousemove`/`mouseup`. The app listens to pointer events. The trailing `click` goes where a browser would send it. The check covers +2 / -1 / +0 on three milestones: a zero-duration one, one with its own Start, and a `USR-` one. It also covers the snap and label preview, the entry, the mark and tick, a combined row-and-column move, back-to-schedule clearing, Undo, plain click, double-click collect, Esc, clamping at both edges, the start-date refusal and its boundary, touch, the toast timeout, and the dependency redraw and filter reapply.

The board must be scrolled so the marker is in the middle of the week cells in view, not in the middle of the scroller (the check's `reveal()`). At 390 the sticky name column covers the left part of the scroller, so `scrollIntoView` alone leaves the marker under it.
