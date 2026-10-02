# P75 notes: the milestone card rework

Matt's requests of 2026-10-02, on top of v3.1.0-P74 (`2a83203`). `APP_VERSION` is not bumped. Scope: the card (`#ms-dialog`) and its handlers only. No TD or TEST entries were added; this file is the record.

## What changed

### 1. Start and Finish are date selectors

- The calendar buttons in the labels (`#ms-dp-btn-start`, `#ms-dp-btn-date`) are gone. The field itself is the trigger.
- `#ms-start-date` and `#ms-date` are `readonly` and carry `aria-haspopup="dialog"` and `aria-expanded` (`.ms-date-sel`).
- How they read as selectors: a pointer cursor, a fill on hover, and the accent ring while the picker is open or on keyboard focus.
- At rest they stay plain, with no fill and no border. That is the P66 read-first rule, which `p66_check` asserts. A visible hairline box was tried first; it broke that assertion and was taken out rather than the assertion changed.
- What opens the picker:
  - a click anywhere on the field (`onMsDateClick`), with a mouse or with a touch;
  - a tap on a touch screen opens it on `pointerdown` (`onMsDatePointer`), so the keyboard never comes up;
  - Enter, Space, Alt+Down and F4 (`onMsDateKey`).
- A click on a field whose picker is already open leaves it open. It no longer toggles, because a tap's own click would otherwise close what the tap opened.
- Esc closes the picker and returns focus to the field.
- Everything else is as it was:
  - the Actual checkbox and the A / `*` suffixes;
  - the green ink for actual dates;
  - Clear;
  - `msReadForm()` reading the field's value;
  - the dirty state and the save path. The picker still writes the field and raises `input`.
- The start placeholder for "no start" was an em dash. It is now a plain hyphen.

### 2. One uniform Start / Duration / Finish row

- `.ms-schedule` has three equal tracks with `align-items:start`, so the blocks sit at the top, directly under the hairline (after the row's own top padding).
- Each label line has one fixed height (`--space-5`), with no buttons in it.
- Each value box (`#ms-start-date`, `#ms-duration`, `#ms-date`) has one height (`--ctl-h`), a line height equal to that height, no border, the same font and left alignment. They share a top, a height and a baseline, including when the finish is highlighted (dirty tint or actual green).
- Finish is no longer right-aligned. All three blocks read the same way.

### 3. Float follows a moved finish

- `renderMsFloat()` runs from `renderMsDuration()`, so it follows the picker live.
- When the finish the card shows (a saved override or a date just picked) differs from the schedule's own finish (`_msBase.date`, else `m.date`):
  - the schedule float is shown struck through in `<s id="ms-float-was">`;
  - the adjusted figure follows in `#ms-float-adj`. It is the schedule float minus the days the finish moved later, or plus the days it moved earlier.
- **Calendar days.** Duration is counted the same way, and the assumption is written in a comment beside `MS_FLOAT_BASE`.
- The float area becomes focusable and gets a tooltip (`#ms-float-tip`, `role="tooltip"`). It shows on hover and on keyboard focus (CSS), and on a tap (`.is-open`, toggled by click, Enter or Space). It lists the previous (schedule) end date, the current end date, and the disclaimer verbatim.
- Esc closes the tooltip before the card. A click elsewhere in the card closes it too.
- Float stays read only: `#ms-float-val` is untouched and still holds the schedule figure. A user milestone and a completed milestone have no base (`MS_FLOAT_BASE` null), so they read as before ("-") and never strike.

### 4. Every way out saves; only the cross discards

- `msLeaveDialog()` is the one "leave" writer: it saves if the card is dirty, then closes.
- The exits that now go through it:
  - a click away;
  - Esc, after any open popover is closed;
  - a second click on the card's own marker. Before P75 this discarded.
- `openMsDialog()` now starts with a guard: if another card is open and dirty, it is saved before the new one opens. This covers every way a card is opened: another marker (which used to drop the edits silently), a note chip, the collection, the grid, a chip jump, and Back. The last three already saved; the guard makes it structural.
- Esc order:
  1. date picker;
  2. type menu;
  3. health popover;
  4. float tooltip;
  5. then save (if dirty) and close.

  The P72 Add-ID suggestion list keeps its own Esc. The Esc handler now ignores keys when the card is closed.
- The cross (`discardMsDialog`) is the only discard. Its title is now "Close without saving (discards unsaved changes). Clicking away or Esc saves." Its aria-label says the same.
- The Help line now reads: "Esc closes the topmost popover, panel or card. A milestone card is saved as it closes; only its × discards changes."

### 5. Copy milestone

- `#ms-copy-btn` sits in the card header, immediately left of the save icon and outside the save pair, so a clean card can be copied too. It has a copy glyph and the label "Copy milestone".
- `copyMsMilestone()` does the following, in order:
  1. Saves the card if it is dirty (`saveMsDialog(false)`).
  2. Reads the form, which now holds the effective values.
  3. Calls `addUserMilestone()`, the writer that `saveAddMilestone()` and the grid's Add row use. That keeps the `USR-NNN` numbering, the collision and week-range checks, the record and its own row under the user band.
- What the copy carries:
  - the title;
  - the effective finish;
  - the type;
  - the mark (written onto the new record).
- What it does not carry:
  - float: a user milestone has none;
  - start: the add path has no start field;
  - progress, health, links and remarks.

  The copy starts as Future.
- History: one entry on the copy, `changes.copiedFrom {from: <source ID>, to: <copy ID>}`. The card's history shows it as "Copied from" (`HISTORY_DEP_LABELS`). It is not projected into any store.
- After the board rebuild, the copy's card opens through `openNoteMilestone()`. Two animations play:
  - the card scales and fades in over 200 ms (`.ms-copy-in`);
  - the new marker pulses an accent outline (`.ms-copy-pulse`).

  Both classes are removed once played. Under `prefers-reduced-motion: reduce` the script does not add them, and the CSS also sets `animation:none`.

## Decisions

- **Typing: no.** The date fields are `readonly`, so the field behaves as a selector. Clear in the picker restores the schedule's own date, as an emptied field did before.
- **User section: "User Defined Milestones"** (`USER_BAND`). A copy gets its own row there, under the disc line "User added", which is what the header Add button already does.
- Finish is left aligned like the other two blocks, for one uniform row.
- A click on an open date field does not close the picker. Esc or a click elsewhere does.
- The copy keeps the source's title unchanged, with no "Copy of" prefix: the request and the check ask for the same title.
- The copy's history uses a change record rather than a remark. A remark would project into `MS_COMMENTS` and show as a comment on the board.

## Checks

- New: `tools/p75_card_check.py`. It runs at 1440 and 390, using pointer, mouse and click sequences dispatched on the elements themselves. At 1440 it also captures a publish and opens the saved file in a fresh profile.

### Assertions changed (none deleted)

| Check | Before | After |
|---|---|---|
| `p43_check` | `escape: discards like the close control, storing nothing`. It read `MS_FIELD_OVERRIDE[..].title`, a field the store does not have, so it could not fail. | `escape: saves and closes like a click away (P75), only the cross discards`. It reads `.actName` and requires the typed title to be stored. |
| `p43_check` | `columns: a milestone with no start shows a dash`, with placeholder `'—'` | The same assertion, with placeholder `'-'` (no em dashes in UI strings) |
| `p43_check` | `editable: every field ... is a live, writable control`. A readonly input counted as not editable. | Same; Start and Finish count as live when they are readonly date selectors with `aria-haspopup="dialog"` (written through the picker) |
| `p69_check` | `buttons: a calendar button in the Start and Finish labels` | `trigger: the Start and Finish fields open the picker (P75: the label buttons are gone)` |
| `p69_check` | `picker: opens from the finish button` (aria-expanded on the button) | `picker: opens from the finish field` (aria-expanded on the field). All later "button" clicks in the check are clicks on the fields. |
| `p69_check` | `typing: " A" typed turns the field green` / `typing: removing it turns it back` | `value: " A" written turns the field green` / `value: removing it turns it back`, plus a new assertion: `no typing: the date fields are readonly (P75)` |

### Results

- `python3 tools/p75_card_check.py`: `230/230 checks passed` (1440 and 390, plus the published copy opened in a fresh profile).
- `python3 tools/run_checks.py --jobs 3` (2026-10-02T01:58, on `2a83203` plus these edits): `61 selected / 1 skipped / 61 passed / 0 failed  (wall 17.2 min, 3 jobs)`.
  - `p43_check 38/38`, `p66_check 101/101`, `p69_check 105/105`, `p72_deps_check`, `p30_check 68/68`.
- How it got there:
  - The first full run had two fails.
  - `p66_check` failed on "the finish date has no fill and no border at rest". The selector box had a 1px border. The border was removed (see "What changed", item 1); the assertion is unchanged.
  - `p30_check` timed out at 600 s. Four suites were running on four cores at once (other agents' worktrees). It passed on the rerun, unchanged.
