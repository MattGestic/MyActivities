# D-31: One left nav, slim command bar, pinned milestone pane

**Status:** Proposed (Matt to choose an option). Mockups only: no app code changed. TD-247.
**Directed by:** Matt, 2026-10-03. Two side panels plus a stacked header read as confusing. He asked for one segmented left panel in the style of a Power Apps model-driven app, with Settings, Import and Info at the bottom, dedicated screens where a panel is too cramped, and a pinned right pane for milestone editing that shows an empty state rather than collapsing. The central dashboard frame stays.

**Mockups:** [`docs/mockups/D-31/shell-options.html`](../mockups/D-31/shell-options.html), with renders in `docs/mockups/D-31/png/`. Mid fidelity, current navy theme, `--pal-*` light values only. The Option 1 frames are clickable.

## Conflict to resolve first

`CLAUDE.md` "Do not change" fixes the D-20 split: annotations on the left (`#ws-rail`, `#ws-panel`), schedule and format on the right (`#settings-drawer`), and the top filter bar. Every option here retires that split. **That rule has to change, with its reason recorded, before any build.** This proposal does not edit it.

## Options

| | Option 1, recommended | Option 2 | Option 3 |
|---|---|---|---|
| Shape | Labelled left nav (Views, My work, Saved views; Import, Settings, Help at the bottom), 52 px command bar, chip filter row, pinned right pane | 56 px icon rail, one context panel at a time on the left, milestone edit as an overlay | Top tabs, chip filters, milestone edit kept as the P66 modal |
| Strength | One place to navigate. Edit-next-milestone is one click with no reflow | Thinnest chrome | Cheapest build |
| Weakness | Pane takes width (it unpins, and the nav collapses to 60 px) | Icon-only discoverability, the same issue as today. Overlay hides current and future weeks | Keeps the per-click modal. Tabs overflow once saved views arrive |

The full comparison is the "Comparison" tab of the mockup.

## Placement rule (all options)

- **See the effect while changing it** → right pane beside the live board: Display (labels, layers) and Datasets.
- **Set once, or admin work** → dedicated full screen: Import and data, Settings, Help.
- **The board resizes only on pin, unpin or nav collapse, never on selection.** Selecting a milestone swaps the pane content only. This answers the reflow cost Matt raised: no layout pass per click, and nothing moves on screen.

## Mapping

Where each current control lands, and the entry point it keeps (`toggleSettingsDrawer`, `setSettingsTab`, `toggleWorkspace`, `setWorkspaceSection`, `toggleFilterBar`, `openMsDialog`, `openGridView`): see the "Where things move" tab of the mockup. Old ids and entry points stay as the migration seam, as `CLAUDE.md` requires.

## Open decisions (Matt)

1. Pick an option.
2. Approve the change to the D-20 rule in `CLAUDE.md`.
3. Filters: a chip row with Add filter, or a Filters tab in the right pane. Recommended: the chip row.
4. Right pane default: always pinned with the empty state, or pinned on the first selection. Recommended: always pinned.
5. Which saved views ship first.

## Inputs

- The Untitled UI sample nav: segmented groups, count badges, a collapsible group.
- `Colors That Ruin.fig`: light, dark and warm theme sets, and a confirm dialog.
- `Design 2025.fig`: modal over scrim pattern sheets.
- Not inspected: the Drive copies of `Micro Dashboard.fig`, `Dashboard Flaws.fig` and `Micro-Animations.fig`. They are too large to pull through the connector [CONFIRM: export key frames as PNG if they should inform this].

## Not in scope

Pixel spec, redlines, motion, dark-theme frames, an implementation plan, and any change to `src/`. Detailed design follows once an option is chosen.
