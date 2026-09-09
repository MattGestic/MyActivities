# Resource Governance

Governs everything in `Resources/`.

## Purpose

`Resources/` is a library of things that can be dropped into a new project and work. Reusable components, document and code templates, and snippets worth keeping.

It is not a scratch folder, not an archive, and not a place to park code that might be useful one day.

**The failure mode this governance prevents:** an ungoverned snippet library becomes a graveyard. Six months in, nobody trusts anything in it, because evaluating whether a given entry still works costs more than rewriting it from scratch. At that point the library has negative value — it consumes storage, attention, and search results while delivering nothing.

The gate below is deliberately strict. A small library of things that definitely work beats a large one that might.

## Categories

| Folder | Holds | Example |
|---|---|---|
| `Resources/Components/` | Working, self-contained functional units. Drop in and call. | A date parser handling P6 loose formats; a debounced rerender wrapper |
| `Resources/Templates/` | Starting points that get copied and filled in. | Project kit file set; report skeleton; single-file HTML app shell |
| `Resources/Snippets/` | Short, high-value fragments not worth a full component. | A CSS token block; a regex with its test cases |

If a candidate does not clearly fit one, it is probably not a resource yet.

## Intake gate

Every candidate is run against the criteria below **before** it enters `Resources/`. All mandatory criteria must pass. A candidate failing any mandatory criterion is either fixed until it passes, or not admitted.

### Mandatory criteria

| # | Criterion | Passes when |
|---|---|---|
| **R1** | **Genuinely reusable** | It is already used in two or more projects, **or** there is a specific, named second use case it would serve unchanged. "Might be useful" fails. |
| **R2** | **No project coupling** | No hardcoded project names, client names, file paths, schedule IDs, colour values, or magic numbers specific to its origin project. Everything project-specific is a declared input. |
| **R3** | **Self-contained** | Dependencies are declared and pinned. Any build or runtime requirement is stated up front. A resource that silently needs something not on the list fails. |
| **R4** | **Documented** | A complete `RESOURCE.md` (template in `Resources/_new-resource/`): purpose, inputs, outputs, dependencies, integration steps, known limits, owner. |
| **R5** | **Demonstrated** | A minimal working example is included and has actually been run. Not described — run, with the result recorded. |
| **R6** | **Limits stated** | Known limitations, edge cases, and scope boundaries are written down. A resource with "no known limitations" fails R6 — it means nobody looked. |
| **R7** | **Clean of sensitive content** | No client data, no commercially sensitive schedule or cost content, no credentials, no tokens, no internal hostnames. Sample data is synthetic or explicitly cleared for use. |
| **R8** | **Licence-safe** | Any third-party code carries a compatible licence, recorded in `RESOURCE.md`. Unattributed copied code fails. |

### R7 is the one that bites

Much of the work in this repository touches client-confidential engineering data — Skeena, Ausenco, P6 schedules, cost and tonnage information. A resource extracted from that work will carry traces of it unless someone actively strips them.

Check for: sample data files, test fixtures, default values, comments naming a client or package, screenshots, and committed example outputs. Strip or synthesise before intake, not after.

### Advisory criteria

Not blocking, but recorded in the catalogue so a reader knows what they are picking up.

| # | Criterion |
|---|---|
| A1 | Has automated tests |
| A2 | Works standalone with no build step |
| A3 | Theme-aware or style-agnostic, where visual |
| A4 | Accessible (keyboard, contrast, semantics), where it renders UI |

## Intake process

1. Copy `Resources/_new-resource/` to `Resources/<Category>/<resource-name>/`.
2. Fill in `RESOURCE.md` completely. Placeholders left in place mean R4 fails.
3. Run the working example. Record the actual result in `RESOURCE.md` under Verification.
4. Run the candidate against R1 to R8 and record the outcome in the intake table at the bottom of `RESOURCE.md`. One line per criterion — pass, or what was changed to make it pass.
5. Add the row to the catalogue in `Resources/README.md`.
6. Commit to `main-projects-hub` with a message naming the resource and the category.

A resource added without steps 3, 4, and 5 is not admitted, regardless of quality.

## Review cycle

Every resource carries a `Last reviewed` date.

- Review on use. If you pull a resource into a project, confirm it still works and refresh the date.
- Anything unreviewed for **12 months** is marked `Stale` in the catalogue.
- `Stale` is a warning to the next reader, not a deletion trigger.

## Retirement

Retire a resource when it no longer passes R1 or R3, when it has been superseded, or when it has been stale and unused for two review cycles.

To retire: remove the folder, and change its catalogue row to `Retired` with the date and the reason. Keep the row.

The row is the record. Deleting it loses the knowledge that something was tried and dropped, which is exactly the knowledge that stops it being tried again.

## Changing a resource

A resource in use elsewhere is a shared dependency, but there is no automatic propagation — projects hold copies.

- Breaking change: bump the resource version in `RESOURCE.md`, note it in the changelog section, and list the projects known to hold a copy so they can be updated deliberately.
- Non-breaking fix: bump the patch version and note it. No propagation needed.

Never edit a resource in place without a version bump. A silently changed resource means two projects hold different code under the same name.
