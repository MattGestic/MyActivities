# D-31: One left nav, slim command bar, milestone side panel or dialog

**Status:** Option 1 chosen by Matt, 2026-10-03. Built as a modular UI kit in stages (below). Stage A kit is built standalone and is waiting for Matt's review; no app code changed yet. TD-247, TD-248.
**Directed by:** Matt, 2026-10-03.
- **Round 1:** two side panels plus a stacked header read as confusing. He asked for one segmented left panel in the style of a model-driven app, with Settings, Import and Info at the bottom, dedicated screens where a panel is too cramped, and a pinned right pane for milestone editing that shows an empty state rather than collapsing.
- **Round 2:** Matt chose Option 1 and approved the empty state, Import, Settings and phone views. He asked for four things:
  - a setting that keeps both ways of opening a milestone, dialog or side panel;
  - fields kept faithful to the app, with the reasoning for any change;
  - the unbuilt functions acknowledged;
  - a clearer period control: report date, a comparison schedule beside the baseline, up to three periods plus user-defined tasks.

**Mockups:** [`docs/mockups/D-31/shell-options.html`](../mockups/D-31/shell-options.html), renders in `docs/mockups/D-31/png/`. Mid fidelity, current navy theme, `--pal-*` light values only. Frames are clickable.

## Decision

Option 1: a labelled left nav (Views, My work, Saved views; Import and data, Settings, Help at the bottom), a 52 px command bar, a chip filter row, and the milestone card in a side panel or a dialog.

Options 2 (icon rail) and 3 (top tabs) were considered and not chosen. They are kept in the mockup under "Considered".

## Delivery stages (Matt, 2026-10-03)

The redesign is built as a **modular UI kit**: components developed on their own with no app data, reusable in other instances, embedded into the app only through `tools/modules_embed.py` (D-30). Order: external containers, then internal cards, then app-specific components.

**Kit rules, for every module:**
- One shared token resource (`ui-tokens`) for colour, spacing, type, shape, elevation and motion.
- `ui-` class prefix. No external classes, fonts, icons or network references.
- Responsive for phone (up to 640 px), tablet (641 to 1024 px) and desktop.
- Light theme only for now.
- Containers own their padding; children never set outer margins.
- Each module's `MODULE.md` records a **layout contract** (direction, wrap, padding, gap, and what truncates or scrolls) and a **motion** table.
- Motion follows Material 3 and Fluent 2 durations and easing: one animation per action, no staggers, no motion on data. Anything that pushes past that budget is flagged instead of built.

| Stage | Kit modules | App change | Status |
|---|---|---|---|
| A | `ui-tokens`, `ui-icons`, `ui-shell` (containers), `ui-surfaces` (cards), `ui-controls`, `ui-nav` (generic left nav) | After Matt's review: nav in the app on the existing entry points, base-screen tidy, P79 | Kit built and tested standalone; gallery `prototypes/ui-kit/` |
| B | `ui-dialog`: generic dialog form with the typical controls around a dialog | The current milestone form hosted by it, not redesigned | Next |
| C | `ui-sidepanel`: right panel, pinned, with an empty state | "Open milestones in: Dialog or Side panel" setting | Planned |
| D | `ui-filterbar` (after a short D-32 design round) | Filters re-hosted; state and `applyFilter` kept | Planned |
| Balance | Built from the same kit | Report date in the command bar, Display pane, Import and Settings screens, form refinement, schedule versions, saved views and Lists, phone sheet, CSV people fields (build register IDs) | Roadmap |

**Correction (verified in code):** several schedules can already be uploaded. Append mode keeps them as `PRIMARY_SOURCES`, each with on/off, rename and remove, and they are shown together on one merged board, with source chips, a Source filter and source columns. What is not built is comparing versions of the same schedule (shared IDs are renamed on Append) and re-baselining. Build register B6 and B7 now say this.

## Rules the design follows

- **See the effect while changing it** → right pane beside the live board (Display).
- **Set once, or admin work** → dedicated full screen (Import and data, Settings, Help).
- **The board resizes only on pin, unpin or nav collapse, never on selection.** Selecting a milestone swaps the pane content only, so there is no layout pass per click and nothing moves.
- **Open a milestone in: Side panel or Dialog** is a user setting under Settings, Behaviour. Dialog is the current app behaviour and gives the board full width. Side panel suits working through a list.
- **Periods have one home: the report button in the command bar.** It sets the report date, the current schedule, an optional comparison schedule, the baseline and user-defined tasks. Each period has its own marker style: solid for current, outline for comparison, dashed for baseline, teal for user-defined. A legend shows when more than one is on.
- **Nothing is removed from import, storage or export.** Hiding is a display choice.

## Registers

- [Field register](D-31-field-register.md): every field shown, what the redesign does with it and why.
- [Build register](D-31-build-register.md): what the mockup shows that is not built, what it builds on, a rough size, and the round-2 clarity fixes.

Both are generated from the mockup by `docs/mockups/D-31/registers_to_md.mjs`. Edit the arrays in the HTML and re-run; never hand-edit the outputs.

## Open decisions (Matt)

1. **Project `CLAUDE.md` rule.** The "two sides plus the filter bar" bullet (the D-20 left/right split) still stands. Option 1 retires it. Proposed replacement: *left nav holds navigation and the annotation layer; the right pane holds the selected milestone (or the dialog, per the setting) and live display; admin work gets full screens; entry points and old ids are kept.* Not edited until Matt approves the wording. It must change before the build starts.
2. **Three periods** are taken as baseline, plus one chosen comparison (default: the previous update), plus the current update. More than one comparison at a time is out of scope [CONFIRM].
3. **Free float alias.** The importer maps "free float" to total float, which can understate criticality. Keep or drop the alias [CONFIRM].
4. **Default open mode** for a new user: side panel (proposed) or dialog.
5. **Which saved views ship first.**
6. **Build order.** Suggested: B2 and B3 (pane and setting), then B5 (report date), then B6 and B7 (comparison), then the rest.

## Inputs

- The Untitled UI sample nav, `Colors That Ruin.fig` and `Design 2025.fig` (round 1).
- Not inspected: the Drive copies of `Micro Dashboard.fig`, `Dashboard Flaws.fig` and `Micro-Animations.fig`. They are too large for the connector.

## Not in scope

Pixel spec, redlines, motion, dark-theme frames, and any change to `src/`.
