# P6 Milestone Dashboard — Requirements

Back-derived from the delivered v3.1.0-P1 build and the chat-to-code handoff. Everything marked `Built` was confirmed present in the migrated file by the pre-handoff regression audit (see `05-test-log.md`, TEST-01). Nothing here is speculative — items not yet built are marked `Draft`.

## Personas

| ID | Persona | Goal | Context |
|---|---|---|---|
| P-01 | Study Coordinator (Matthew) | See every deliverable milestone against a weekly timeline, annotate health and remarks, produce a reviewable status view each update cycle | Weekly P6 update cycle. Owns the file, does the import, publishes the view. |
| P-02 | Discipline Lead | Find their own deliverables quickly, check dates and dependencies, sanity-check what has slipped | Ad hoc. Opens the file from a share or email, does not import anything. |
| P-03 | Client / IPMT reviewer | Read a clean milestone picture without schedule software or training | Periodic review. Read-only, no import, no annotation. |
| P-04 | Project Controls / Planner | Cross-check the dashboard view against the P6 source, confirm nothing was mis-mapped on ingest | On import. Cares about column mapping, data date, and diagnostics. |

## User Stories

Format: `As a [persona], I want [capability], so that [outcome].`

| ID | Persona | Linked Feature | Story | Priority | Status |
|---|---|---|---|---|---|
| US-01 | P-02, P-03 | FEAT-01 | As a reviewer, I want the dashboard to open with a useful baseline already loaded, so that I never have to import anything to see the schedule picture. | High | Built |
| US-02 | P-01 | FEAT-02 | As the coordinator, I want to import a live P6 export by file upload or paste, so that I can refresh the view each weekly cycle. | High | Built |
| US-03 | P-01, P-04 | FEAT-02 | As the coordinator, I want imported columns auto-mapped with a manual override step, so that a non-standard export still lands correctly. | High | Built |
| US-04 | P-01 | FEAT-02 | As the coordinator, I want an import to overlay the view without touching the baked-in baseline, so that I can always fall back to a known-good state. | High | Built |
| US-05 | P-02, P-03 | FEAT-03 | As a reviewer, I want every activity end date shown as a marker on a week-by-week timeline, so that I can read slippage and clustering at a glance. | High | Built |
| US-06 | P-02 | FEAT-03 | As a discipline lead, I want markers that land close together to be offset vertically, so that labels stay readable in a dense week. | Med | Built |
| US-07 | P-02, P-04 | FEAT-04 | As a lead, I want dependency lines drawn between related milestones, with visibility and thickness I can control, so that I can trace a driving path without opening P6. | Med | Built |
| US-08 | P-01 | FEAT-05 | As the coordinator, I want to override a milestone's health state, add a short title, and leave a comment that autosaves, so that the view carries my assessment, not just the raw dates. | High | Built |
| US-09 | P-01 | FEAT-05 | As the coordinator, I want actualised dates visually distinguished, so that confirmed progress reads differently from forecast. | High | Built |
| US-10 | P-02 | FEAT-06 | As a lead, I want to filter rows by title, banding, Activity ID, and week range, so that I can isolate my scope. | High | Built |
| US-11 | P-02 | FEAT-06 | As a lead, I want an always-visible quick search in the sticky corner, kept in sync with the full filter bar, so that the common case takes one action. | Med | Built |
| US-12 | P-02 | FEAT-06 | As a lead, I want an Activity ID field that autocompletes but still accepts a pasted comma list, so that both entry styles work. | Med | Built |
| US-13 | P-01, P-03 | FEAT-07 | As a user, I want to control column visibility, label text sizing, and layout fit, so that the view suits my screen and my audience. | High | Built |
| US-14 | P-01 | FEAT-07 | As the coordinator, I want three independent text scale controls (label, title, hours), so that I can tune density without one slider fighting another. | Med | Built |
| US-15 | P-01 | FEAT-08 | As the coordinator, I want to export the full model as JSON including my annotations, or a status/remarks CSV, so that the assessment survives outside the file. | High | Built |
| US-16 | P-01 | FEAT-08 | As the coordinator, I want to re-import a previously exported JSON model, so that annotations survive a version upgrade of the dashboard file. | Med | Draft |
| US-17 | P-01, P-04 | FEAT-09 | As the coordinator, I want diagnostics on what was ingested and what was skipped, hidden when there is nothing to report, so that mapping problems surface without adding noise. | Med | Built |
| US-18 | P-01 | FEAT-10 | As the coordinator, I want to define and reorder my own row groupings, so that the view matches how the study is actually reported rather than the fixed phase bands. | Med | Draft |
| US-19 | P-02 | FEAT-11 | As a lead, I want to sort rows and customise the icon per milestone type, so that the view emphasises what I care about. | Low | Draft |
| US-20 | P-01, P-03 | FEAT-12 | As a user, I want the whole tool to be one file I can email or drop on a share, opening with no install, so that anyone on the study can use it. | High | Built |

## UI/UX Component Requirements

| ID | Linked US | Component | Requirement |
|---|---|---|---|
| UX-01 | US-05 | Timeline table | Sticky `<thead>` with both phase-band and date rows pinned on vertical scroll. Horizontal scroll inside `#scroll-wrap`, never the page body. |
| UX-02 | US-05, US-06 | Milestone marker | `.m-wrap` icon with `.m-lbl-stack` as a genuine DOM child, so positioning anchors to the icon not the week cell. Same-row collision nudges into 3 vertical bands (mid / top-quarter / base, cycling) when markers land within ~4 columns. |
| UX-03 | US-05 | Marker icons | All 5 non-baseline states use solid fill. |
| UX-04 | US-07 | Dependency line layer | SVG overlay redrawn only via `drawDepLines()`, which defensively resets layer visibility and clears stuck drag state on every run. All-on/off button reflects true state. |
| UX-05 | US-08, US-09 | Milestone dialog | Header order fixed; actualised dates get green shading; 5-state health override; comment field autosaves. |
| UX-06 | US-10 | Top filter bar | `#top-filter-bar`, collapsible horizontal bar under the header, magnifying-glass toggle. Fields: Title contains, Banding, Activity ID(s), Week range. |
| UX-07 | US-11 | Sticky corner search | Lives in the top-left sticky table cell, replacing the plain "Deliverable" label. Two-way synced with the Top Filter Bar Title field. |
| UX-08 | US-12 | Activity ID autocomplete | Plain text input (paste-a-comma-list must keep working) with dropdown overlay filtering against text after the last comma, appending on click. Click handler must use `onmousedown` + `preventDefault()`. |
| UX-09 | US-13, US-14 | Style/Customize sidebar | `#filter-bar`, left docked, palette icon toggle. Docked via `body.cv-open{margin-left:300px}` class toggle, not DOM restructure. Controls layout, field visibility, label text sizing, dependency line visibility/thickness. |
| UX-10 | US-14 | Text scale controls | Three independent multipliers `--label-scale`, `--title-scale`, `--hrs-scale`, layered over existing column-width-responsive `clamp()` sizing. Must not be merged back into one control. |
| UX-11 | US-13 | Fit to Screen | Column-width auto-fit action. |
| UX-12 | US-02, US-03, US-15, US-17 | Settings drawer | `#settings-drawer`, right-docked overlay, gear icon. Order: Actions (export, clear comments) → Currently Imported Schedule status → Import (collapsible: "1. Import a Schedule" → "2. Map columns" → Advanced Input Settings → confirm) → Diagnostics (collapsible, hidden entirely when empty). |
| UX-13 | US-20 | Theme | `html[data-theme="light"]` default, `dark` block present and maintained for a future toggle. |
| UX-14 | all | Output text | No em dashes, no AI-associated punctuation patterns in any user-facing or client-facing string the tool produces. |
| UX-15 | US-08 | Annotation colour convention | Red = new/draft, yellow highlight = carried over from prior period, black = confirmed. Distinct from dashboard status colours. |

---
**Rules:**
- New requirement → new ID, never renumber existing ones.
- Conflicting requirement found → flag it in-session, do not silently resolve.
- This file is additive. Status changes update the row, they do not create a new one.
