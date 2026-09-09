# P6 Milestone Dashboard — To-Do

Short-lived, tactical. Bugs, blockers, immediate next actions. Close items out rather than archiving them here.

| ID | Item | Linked | Priority | Status | Raised |
|---|---|---|---|---|---|
| TD-01 | Version string mismatch: the migrated file was supplied as `..._v3_1_0_11.html` but `APP_VERSION` reads `3.1.0-P1`. Confirm whether the constant was left un-bumped at P11 or the filename is wrong, then set `APP_VERSION` correctly. Do not hand-edit the title or icon-bar label. | FEAT-15 | H | Open | 2026-09-09 |
| TD-02 | Blank Data-date / Report-date on `.xlsx` import. Reported against a real file, not reproducible via paste import (tried twice, including the exact field-editing sequence) or static review. A defensive fallback ("not set" instead of a bare blank) is in place; root cause unconfirmed. Needs the triggering file to diagnose. | FEAT-02 | M | Open (blocked) | Pre-migration |
| TD-03 | Companion docs referenced by the handoff were not supplied: `Token_Migration_Log.md`, `Tokenization_Path_Plan.md`, `Hardcoded_Colour_Audit.csv`. Locate and commit into `docs/`. FEAT-14 should not resume without the log — its methodology is the reason near-identical colours were deliberately kept separate. | TASK-04, FEAT-14 | H | Open | 2026-09-09 |
| TD-04 | Run the 29-Aug-2026 export through import as a live ingest test. Known shape: 192 rows, 146 leaf activities, 46 band/group rows, Finish column mixed (129 Excel serial, 57 text with ` A` / `*` suffixes, 6 blank). Confirm serial handling and hierarchy detection both land correctly. | TEST-02, FEAT-02 | H | Open | 2026-09-09 |
| TD-05 | Confirm whether `main` in this repo should carry a top-level README pointing at each app's branch, or stay untouched as the MyActivities fitness site only. | FEAT-15 | L | Open | 2026-09-09 |

---
**Next code task (single line, always current):** TD-01 — resolve the `APP_VERSION` / filename version discrepancy before any further code change, so version history starts from a known-correct value.
