# P6 Milestone Dashboard — Backlog

Hierarchy: **EPIC** → **FEATURE** → **TASK/STORY**. Scoring is Impact vs Complexity at Feature level only; Epics roll up.

Status baseline is the delivered v3.1.0-P1 build. Features marked `Published` were confirmed present by the pre-handoff regression audit (TEST-01) and are not to be re-verified from scratch.

## Epics

| ID | Epic | Features | Status |
|---|---|---|---|
| EPIC-01 | Schedule ingest and data model | FEAT-01, FEAT-02, FEAT-09, FEAT-17 | 4/4 published |
| EPIC-02 | Timeline rendering | FEAT-03, FEAT-04 | 2/2 published |
| EPIC-03 | Annotation and assessment | FEAT-05 | 1/1 published |
| EPIC-04 | Filtering and view control | FEAT-06, FEAT-07 | 2/2 published |
| EPIC-05 | Export and round-trip | FEAT-08, FEAT-13 | 1/2 published, FEAT-13 part-built |
| EPIC-06 | Design system tokenization and development discipline | FEAT-14, FEAT-16 | 1/2 published |
| EPIC-07 | Grouping and presentation (future) | FEAT-10, FEAT-11 | 0/2 published |
| EPIC-08 | Repository and delivery | FEAT-12, FEAT-15 | 1/2 published |

## Features

| ID | Epic | Feature | Linked US | Impact | Complexity | Status | Notes |
|---|---|---|---|---|---|---|---|
| FEAT-01 | EPIC-01 | Baked-in baseline schedule | US-01 | H | L | Published | 15-Aug-2026 P6 export, 159 tasks / 198 milestones. |
| FEAT-02 | EPIC-01 | Live schedule import (xlsx / paste / delimited) | US-02, US-03, US-04 | H | H | Published — TEST-02 run 2026-09-10, two gaps open (TD-15, TD-16) | `Parse.workbook()` / `Parse.delimited()`, `INGEST_CONFIG.headerAliases`, leaf/group hierarchy detection, `classify()`/`aggregate()`. |
| FEAT-03 | EPIC-02 | Week-grid milestone rendering + collision bands | US-05, US-06 | H | H | Published | 3-band cycling, scoped to same-row common case. v3.1.0-P8 adds row numbers and milestone drag between rows; the collision system re-runs on drop, so the target row re-bands itself. |
| FEAT-04 | EPIC-02 | Dependency line system | US-07 | M | H | Published | `drawDepLines()` single choke point with defensive reset. |
| FEAT-05 | EPIC-03 | Milestone dialog: health override, short title, comment | US-08, US-09 | H | M | Published | 5-state health override, comment autosave, actualised-date shading. |
| FEAT-06 | EPIC-04 | Row filtering (title, banding, Activity ID, week range) | US-10, US-11, US-12 | H | M | Published | Includes synced sticky-corner search and Activity ID autocomplete. |
| FEAT-07 | EPIC-04 | Customize View sidebar (columns, text scale, fit) | US-13, US-14 | H | M | Published | 3 independent scale sliders, deliberately not merged. |
| FEAT-08 | EPIC-05 | Export: full JSON model + status/remarks CSV | US-15 | H | M | Published | JSON payload includes dep visibility, health overrides, comments, short titles. |
| FEAT-09 | EPIC-01 | Ingest diagnostics panel | US-17 | M | L | Published | Collapsible, hidden entirely when empty. |
| FEAT-10 | EPIC-07 | Banding / row-collections (user-reorderable grouping) | US-18 | M | H | Not started | Fully specced. Phase 1 auto-derivation not begun. Assume none of it exists. |
| FEAT-11 | EPIC-07 | Row sorting + per-type icon customisation | US-19 | L | M | Not started | Labelled "Future" in the UI. Genuinely not built, not partially built. |
| FEAT-12 | EPIC-08 | Single-file zero-dependency distribution | US-20 | H | L | Published | Constraint, not a feature to be traded away. |
| FEAT-13 | EPIC-05 | Import previously exported JSON model (round-trip) | US-16 | M | M | Dev — annotation layer done at v3.1.0-P9, schedule rehydration not built | Six independently selectable categories, validated on payload identity rather than filename. `tasks`/`milestones`/`timeline` are in the payload but do not rebuild the board (TD-32). |
| FEAT-14 | EPIC-06 | Tokenization retrofit (colour / spacing / text) | — | M | **H** | Dev — theme-blind class complete, Phase 1/2 and spacing/text outstanding | Complexity raised from M on 2026-09-09: the corrected audit shows materially more remaining work than v1 reported. Never state counts here — read the Measurement Log's latest row per metric. Follow the Token Migration Log methodology, do not restart. |
| FEAT-15 | EPIC-08 | Git repository migration + project kit | — | H | L | Published | Orphan branch `p6-milestone-dashboard` as the app's main. Tagged `v3.1.0-P1`. |
| FEAT-16 | EPIC-06 | Lessons-learned capture and promotion of general rules to repository governance | — | M | L | Published | `docs/06-lessons-learned.md`. Two rules promoted to `Governance/` on the hub branch. |
| FEAT-17 | EPIC-01 | Mount manager: three fixed source slots with unmount and remount | — | H | M | Published | v3.1.0-P9. Baseline (locked) / Schedule / Annotations, each showing file name, data date and load time, so an active override is visible as an override. |

## Tasks

| ID | Parent | Task | Status | Notes |
|---|---|---|---|---|
| TASK-01 | FEAT-15 | Create orphan branch, project skeleton, migrate v3.1.0-P1 file, schedule sample and handoff doc | Done | 2026-09-09 |
| TASK-02 | FEAT-15 | Write six-file project kit back-derived from the delivered build | Done | 2026-09-09 |
| TASK-03 | FEAT-15 | Add project `CLAUDE.md` so future sessions inherit the constraints without re-reading the handoff | Done | 2026-09-09 |
| TASK-04 | FEAT-15 | Migrate the companion docs into `docs/tokenization/` | Done | Log and path plan supplied 2026-09-09. Audit CSV regenerated rather than recovered. |
| TASK-05 | FEAT-14 | Retrofit `--space-0..7` across older CSS still using raw pixel values | Open | 173 raw px declarations against 38 `var(--space-N)` calls. Check what is already close before adding any new value. |
| TASK-06 | FEAT-14 | Continue colour tokenization pass, role before value | Open | Near-identical hexes may be genuinely different semantic states. See the log for why some were deliberately kept separate. |
| TASK-10 | FEAT-14 | Commit a reproducible tokenization audit (`tools/colour_audit.py`) and reconcile it against the v1 figures | Done | v1 matched hex only and counted token definitions as references. Reconciliation table in the Migration Log. |
| TASK-11 | FEAT-14 | Phase 1: mechanical substitution of the 28 colour occurrences already matching a defined token exactly | Open | Pure substitution, zero design decisions. Safe to batch independently. |
| TASK-12 | FEAT-14 | Phase 2: triage the repeat-use colour values, including the `rgba()` set v1 never measured | Open | Role before hex proximity. Counts live in the Measurement Log, not here. |
| TASK-14 | FEAT-14 | Theme-blind pass: replace every literal frozen at one theme's value, and prove it with computed styles in both themes | Done | v3.1.0-P2. Zero theme-blind occurrences remain. `tools/theme_check.py` added. |
| TASK-15 | FEAT-15 | Make the page title derive from `APP_VERSION` instead of a hardcoded literal | Done | TD-10. Exactly one version literal now exists in the file. |
| TASK-16 | FEAT-14 | Extend the colour audit to inline `style=` attributes | Done | TD-12. Found a theme-blind literal in generated markup on the first run. |
| TASK-17 | FEAT-14 | Tokenize the board: rows, columns, marker labels, icons, status | Done | v3.1.0-P3. Icons gained one default token state each. |
| TASK-18 | FEAT-14 | Add WCAG contrast measurement to the theme check | Done | Caught a regression this pass that the toggle check could not see. |
| TASK-19 | FEAT-02 | Build a committed ingest harness (`tools/import_check.py`) and run TEST-02 against the reference export | Done | Drives the real pipeline; stubs only the SheetJS boundary, faithfully reproducing `raw:false` number formatting. |
| TASK-20 | FEAT-04 | Read Predecessor/Successor columns on import instead of relying on baked-in `DEP_DATA` | Open | TD-16. Needs a mapper field pair and a `normalise` change. |
| TASK-21 | FEAT-02 | Decide and implement handling for a constrained (`*`) finish date | Open | TD-15. Currently parsed then discarded. |
| TASK-22 | FEAT-02 | Ingest Predecessor/Successor columns (mapper field, aliases, normalise) | Done | v3.1.0-P4. Header score 5 to 7 on the reference export. |
| TASK-23 | FEAT-03 | Row model: one row per deliverable, stage chains collapsed with dependency corroboration | Done | v3.1.0-P4. PFS 146 activities to 115 rows. |
| TASK-24 | FEAT-02 | XER extractor (`tools/xer_to_aoa.py`) for testing against real EPCM schedules | Done | Standalone tool, not app code. TD-21 covers in-app ingest. |
| TASK-25 | FEAT-10 | Aggregation axis for EPCM/construction schedules | Done | TD-20. v3.1.0-P5, mixed strategies per band. |
| TASK-26 | FEAT-10 | Sub-headings within a band, chosen by count | Open | TD-23. The unbuilt half of the agreed row rule. |
| TASK-27 | FEAT-03 | Dependency-first row building with a deliverable-identity second pass | Done | v3.1.0-P7. 8/8 over-merge guards, PFS 108 rows, EPCM 1898. |
| TASK-28 | FEAT-03 | Relax the convergence constraint with a measured predecessor threshold | Done | TD-26. v3.1.0-P8. Threshold 6 chosen from the distribution, not assumed. PFS 108 to 105 rows. |
| TASK-29 | FEAT-03 | Row numbers per banding, rendered beside the health dot | Done | v3.1.0-P8. Flex slot, not a text prefix, so the drag handle can join it. |
| TASK-30 | FEAT-03 | Drag a milestone from one row to another, mouse and touch | Done | v3.1.0-P8. Pointer Events; 4px threshold on mouse, 400ms hold on touch. Target row re-bands via the existing collision system. |
| TASK-31 | FEAT-11 | Row dragging (reorder rows within a banding) | Open | TD-29. The handle slot and `data-rownum` are in place; the interaction is not. |
| TASK-32 | FEAT-14 | Re-run the contrast check across transparent-background components now the blind spot is closed | Open | TD-28. `--color-text-small` measures 1.18:1 on a dark row. |
| TASK-33 | FEAT-17 | Mount panel: three fixed slots, each with name, data date and load time | Done | v3.1.0-P9. Replaces the single "Currently Imported Schedule" summary. |
| TASK-34 | FEAT-17 | Unmount and remount actions per slot | Done | v3.1.0-P9. Baseline is locked; unmounting a schedule reverts to it and leaves annotations alone. |
| TASK-35 | FEAT-13 | Model export identity block and file naming convention | Done | v3.1.0-P9. `kind` + `schemaVersion` + `exportedAt`; validation never reads the filename. |
| TASK-36 | FEAT-13 | Selective annotation import, one checkbox per category | Done | v3.1.0-P9. Six categories, counts shown, whole file or just the comments. |
| TASK-37 | FEAT-13 | Rebuild the board from a mounted model's tasks/milestones/timeline | Open | TD-32. The payload carries them; nothing consumes them. |
| TASK-38 | FEAT-14 | Sweep every consumer of `--color-text-small` and `--color-purple-dark` | Open | TD-33. Both measured below 1.2:1 in dark on the surfaces used this pass. |
| TASK-39 | FEAT-02 | Route every import failure through one handler that clears stale parse state | Done | TD-34. v3.1.0-P10. A failure could previously leave the prior file importable. |
| TASK-40 | FEAT-02 | Show a visible failure block where the column-mapping step would have appeared | Done | TD-35. v3.1.0-P10. Names the file, the reason and the remedy. |
| TASK-41 | FEAT-02, FEAT-12 | Decide how `.xlsx` import behaves when the SheetJS CDN is unreachable | Open | TD-36. The only dependency that can remove a whole input format. |
| TASK-42 | FEAT-02 | Report the real `FileReader` DOMException and its remedy instead of a generic message | Done | TD-37. v3.1.0-P11. |
| TASK-43 | FEAT-02 | Retry a failed file read once before reporting | Done | TD-38. v3.1.0-P11. Covers transient OneDrive hydration and antivirus locks. |
| TASK-13 | FEAT-16 | Promote the two general lessons (verification methodology, append-only measurement logs) to repository governance | Done | Applied on `main-projects-hub`. |
| TASK-07 | FEAT-02 | Decide whether `headerAliases` should move from exact-match to fuzzy | Open | Accepted gap today. `"BL1 Start"` will not match a `"bl start"` alias. Primary `Start`/`Finish` cover the core need. |
| TASK-08 | FEAT-03 | Multi-line short-title vertical bleed into neighbouring rows | Open | Separate, smaller problem than the same-row collision system. |
| TASK-09 | FEAT-10 | Banding Phase 1: auto-derivation of row collections | Open | Blocked on FEAT-10 go-ahead. |

---
**Rules:**
- Backlog is Epic/Feature/Task level. Standalone bugs and short-lived next actions go in `03-todo.md`.
- Status changes update the row in place. Never renumber existing IDs.
- Do not duplicate an item that already exists under another ID — update it.
