# Documentation Standard

## What belongs where

| Question | File |
|---|---|
| Why does this exist, what is it for, what must not change | `docs/00-project-context.md` |
| Who uses it and what do they need it to do | `docs/01-requirements.md` |
| What is planned, in progress, or done, at feature level | `docs/02-backlog.md` |
| What is broken or next, right now | `docs/03-todo.md` |
| How is it built and why that way | `docs/04-architecture.md` |
| What was tested and what was accepted | `docs/05-test-log.md` |
| How do I run it | `README.md` |
| What do I need to know before editing it | `CLAUDE.md` |
| How do all projects here work | `Governance/` on `main-projects-hub` |

If a fact is in two files, one of them is wrong. Reference by ID instead.

## Writing rules

- **Lead with the answer.** Context after, if it is needed at all.
- **Structured.** Headings and bullets or tables. Not prose blocks.
- **Short.** If it can be said in fewer words, do it.
- **Acronyms used freely** — EPCM, NPI, SMP, IFC, ITR, PCM, RFI, ITT, SoW, BOQ, P&ID, EOR, CAPEX, OPEX, EV, ETC, WHS, TQ, MR, PR, PO, IPMT. No expansion unless asked.
- **Flag assumptions explicitly.** Use `[CONFIRM]` or `[INSERT VALUE]` for anything unknown. Never guess and present it as fact.
- **Every "do not change" rule carries its reason.** A rule without a reason gets removed by whoever comes next, and the bug comes back.
- **No filler.** No restating what is about to be done.

## Output produced by an application

Distinct from the documentation rules above. These govern strings the application itself emits to a user or a client.

- **No em dashes, and no AI-associated punctuation patterns.** This is a hard rule on client-facing output.
- Where a project defines its own annotation or status colour convention, it lives in that project's `00-project-context.md`, not here.

## Recording a decision

Architecture decisions go in the `04-architecture.md` decisions log with four columns: decision, alternatives considered, why chosen, date.

"Alternatives considered" is the column that earns its place. A decision without recorded alternatives gets re-argued in six months because nobody can tell whether the obvious option was already rejected for a good reason.

## Recording a limitation

Known limitations are listed explicitly in the project `README.md` and carried as backlog or to-do items with their status.

An acknowledged scope boundary and a hidden gap look identical to the next reader unless the boundary is written down. Write it down, and say it was deliberate.

## Handover documents

Any migration or handover document is archived verbatim in `docs/handoff/`, named `YYYY-MM-DD_<description>.md`.

It is a historical record. Do not edit it to match the current state — the kit files carry current state, the handoff carries what was true at handover.
