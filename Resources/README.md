# Resources — Catalogue

Reusable components, templates, and snippets that have passed the intake gate in [`Governance/04-resource-governance.md`](../Governance/04-resource-governance.md).

**Nothing enters this folder without passing intake.** See that document for the criteria and the process. The short version: genuinely reusable, no project coupling, self-contained, documented, demonstrated with a run result, limits stated, clean of client data, licence-safe.

## Catalogue

| Resource | Category | Version | Purpose | Advisory | Last reviewed | Status |
|---|---|---|---|---|---|---|
| *(none yet)* | | | | | | |

Column notes:
- **Advisory** lists which of A1 (tests) · A2 (no build step) · A3 (theme-agnostic) · A4 (accessible) the resource meets. Not blocking, but tells a reader what they are picking up.
- **Status**: `Active` · `Stale` (unreviewed 12 months) · `Retired` (folder removed, row kept as the record).
- Retired rows stay. Deleting them loses the knowledge that something was tried and dropped.

## Adding a resource

```bash
cp -r Resources/_new-resource Resources/<Category>/<resource-name>
```

Then:

1. Fill in `RESOURCE.md` completely. Placeholders left in place fail R4.
2. Run the working example. Record the actual result under Verification.
3. Run R1 to R8 and record the outcome in the intake table.
4. Add the row above.
5. Commit to `main-projects-hub`.

## Candidates not yet admitted

Things worth extracting from existing projects, but which have not been through intake. Listed here so they are not forgotten and not mistaken for admitted resources.

| Candidate | Source | Why it might qualify | Blocker |
|---|---|---|---|
| Loose date parser | P6 Milestone Dashboard, `parseLooseDate()` | Handles `dd-MMM-yy`, ISO, `dd/mm/yyyy`, bare Excel serial, plus P6 ` A` actualised and `*` constrained suffixes. Any P6 or Primavera ingest needs this. | R5 — needs extraction and a standalone test harness with synthetic dates |
| Six-file project kit | `Governance/01-project-standard.md` | Every new application here needs it. | R4/R5 — needs the empty template set placed under `Resources/Templates/` |
| Debounced rerender wrapper | P6 Milestone Dashboard, `scheduleRerender()` | 40ms coalescing wrapper over an expensive full-DOM rebuild. Generic pattern. | R2 — currently coupled to that project's `rerender()` signature |
| Design token block (colour/spacing/text) | P6 Milestone Dashboard `:root{}` and theme blocks | A worked light/dark token set with a documented consolidation methodology. | R1 and R2 — colour values are project-specific; the *methodology* may be the reusable part, not the values. |
| CSS tokenization audit script | P6 Milestone Dashboard, `tools/colour_audit.py` | Extracts hardcoded colour, spacing and font-size against defined tokens in any single-file HTML app, and emits both a CSV and measurement-log figures. Generic method, no project data. | R1 — needs a named second use case. Currently only one project. R5 satisfied already (run, reconciled against a prior implementation, discrepancies explained). |

A candidate row is not a commitment. It is a note that something looked reusable, and what stands in the way.
