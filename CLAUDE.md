# MyActivities — repository hub session rules

You are on `main-projects-hub`, the default branch. **This branch holds no application code.**

## Before doing anything

Work out which branch the task belongs to.

| Task | Branch |
|---|---|
| Change an application | That application's branch — see the register in `README.md` |
| Change a repository-wide standard | Here (`Governance/`) |
| Add or change a reusable resource | Here (`Resources/`) |
| Add a new application | New orphan branch, then add its register row here |

If the task is application work, **switch branches first**. Do not add application code here.

## Hard rules

- **Never merge an application branch into this one, or into another application branch.** They are unrelated orphan roots. A merge between them proposes merging two whole trees.
- **Never open a pull request between application branches or into this branch.**
- `main-projects-hub` stays the repository default branch.
- A branch without a register row is invisible. A register row without a branch is a lie. Create both in the same change.

## Governance is binding

`Governance/` is the standard every project follows, not a suggestion:

| Document | Covers |
|---|---|
| `00-repository-model.md` | Branch model, naming, creating and retiring a project |
| `01-project-standard.md` | Required project structure, six-file kit, ID schemes, phase gates |
| `02-versioning-standard.md` | Version format, when to bump, tags and snapshots |
| `03-documentation-standard.md` | Doc conventions, tone, output rules, what belongs where |
| `04-resource-governance.md` | Resource intake criteria, review, retirement |

If a project needs to break a standard, change the standard here first with the reason recorded. Do not silently diverge.

## Resources are gated

Nothing enters `Resources/` without passing the R1 to R8 intake gate in `Governance/04-resource-governance.md`, with the result recorded in the resource's own `RESOURCE.md` and a catalogue row added.

**R5 (Demonstrated) and R7 (clean of sensitive content) are the two that get skipped.** R5 requires an example that was actually run, with the real result recorded — not a description. R7 requires actively checking for client data (Skeena, Ausenco, P6 schedule, cost, tonnage) in sample data, fixtures, defaults, comments, and committed example output.

A resource added without a completed intake record is not admitted, regardless of quality.

## Writing standard

Lead with the answer. Structured, short, no filler. Acronyms used freely without expansion. Flag assumptions with `[CONFIRM]` rather than guessing.

**Every "do not change" rule carries its reason.** A rule without a reason gets removed by whoever comes next, and the bug comes back.

**Never write a number expected to change into prose.** Counts, percentages, coverage figures and remaining-work totals go in an append-only measurement log — append rows, never edit or delete one. Prose says what a metric means and where to find it. Commit the measuring script next to what it measures. Full rules in `Governance/03-documentation-standard.md`.

Full conventions in `Governance/03-documentation-standard.md`.
