# Project Standard

Required structure and documentation for every application in this repository.

## Required structure

```
Projects/<App-Name>/
├── CLAUDE.md              Constraints a dev session must load before touching code
├── README.md              What it is, how to run it, limitations
├── src/                   The application
├── releases/              Point-in-time version snapshots (see 02-versioning-standard.md)
├── data/                  Reference/sample inputs for testing, if the app ingests anything
├── tools/                 Scripts that measure or check the project (see below)
└── docs/
    ├── 00-project-context.md
    ├── 01-requirements.md
    ├── 02-backlog.md
    ├── 03-todo.md
    ├── 04-architecture.md
    ├── 05-test-log.md
    ├── 06-lessons-learned.md
    └── handoff/           Archive of any migration or handover document
```

`src/`, `releases/`, `data/`, `tools/` and `handoff/` are omitted only where genuinely not applicable. The seven `docs/` files and both root files are always present.

**`tools/` is not optional once a project measures anything about itself.** A measurement script committed next to what it measures can be diffed, reviewed, and reproduced. One that lives on someone's machine cannot, and its drift from its own documented method is invisible until somebody reimplements it. See the append-only measurement log rules in `03-documentation-standard.md`.

## The seven-file kit

One fact lives in exactly one file. Other files reference it by ID rather than restating it. This is what stops requirements, backlog, and decisions being re-litigated every session.

| File | Holds | Updated |
|---|---|---|
| `00-project-context.md` | Problem, objective, description, phasing. Architecture decisions and rationale. Style constraints. What not to change. | Phase 1, then on major decisions only |
| `01-requirements.md` | Personas, user stories (`US-##`), UI/UX component requirements (`UX-##`) | Phase 2, then additive |
| `02-backlog.md` | `EPIC-##` / `FEAT-##` / `TASK-##` hierarchy. Impact vs Complexity scored at Feature level. | Every session that changes scope |
| `03-todo.md` | `TD-##` short-lived tactical items: standalone bugs, next actions, blockers with no feature parent. Ends with the current next code task on one line. | Continuously |
| `04-architecture.md` | Front-end/back-end split, hosting strategy, runtime structure, data mapping, state model, decisions log | Phase 3, then on architecture-impacting changes |
| `05-test-log.md` | `TEST-##` automated runs, `UT-##` live user tests, feedback triage, acceptance and publish record | Phase 5 onward |
| `06-lessons-learned.md` | Patterns that caused a real bug or a wasted cycle, grouped by pattern with root cause and recommendation | Whenever one is learned |

**On `06-lessons-learned.md`:** its purpose is prevention, not record-keeping. A lesson that stays only in this file has not done its job — once a lesson hardens into a rule, put the rule in the project's `CLAUDE.md` (or here, if it is general) and leave the reason in the lessons file. A rule without its reason gets removed by whoever comes next, and the bug comes back.

### ID hierarchy

Three tiers. Do not invent a fourth.

- **`EPIC-##`** — a body of work grouping related features. Scored only by rollup, never directly.
- **`FEAT-##`** — a shippable increment. The level Impact vs Complexity applies to, and the level that moves through Dev → AI Test → Live Test → Published.
- **`TASK-##`** (technical) or **`US-##`** (user-facing story) — the build-level unit under a Feature, or standalone in `03-todo.md` as `TD-##` if it has no feature parent.

If something needs sub-tasks under a Task, it is a Feature that was scoped too small. Split it back up to `FEAT-##`.

### Anti-duplication rule

Before writing anything into requirements, backlog, or to-do: check whether it already exists under another ID. If it does, update it in place. Never create a near-duplicate.

If a new item conflicts with something already on file — a requirement, a backlog item, an architecture decision — **flag the conflict immediately**. Do not silently overwrite.

Never renumber an existing ID. Other files and any generated views reference by ID.

## Phase gates

| Phase | Trigger | Output |
|---|---|---|
| 1 — Idea distillation | Raw notes, brainstorm, "here's an idea" | `00-project-context.md` baseline. Anything vague marked `[CONFIRM]` rather than guessed. |
| 2 — Product definition | Phase 1 approved | `01-requirements.md` + `02-backlog.md` |
| 3 — Architecture | Phase 2 approved, or an architecture question mid-build | `04-architecture.md` |
| 4 — Build | Request to start coding | Code, organised by component. Anything deferred goes to `03-todo.md`. |
| 5a — AI/automated test | Build complete | `05-test-log.md` entry with acceptance criteria (INVEST or EARS, state which) and pass/fail per criterion. **Mandatory before 5b.** |
| 5b — Live user test | 5a passed | Prescribed scope, pass criteria, and how to capture results, logged before it goes out |
| 5c — Feedback triage | Results reported | Each item classified (requirement gap / backlog / bug / out of scope) and routed. Not just logged — decided. |
| 6 — Acceptance | 5a and 5b clear, or explicit accept-with-exceptions | Acceptance record in `05-test-log.md`. Exceptions listed explicitly. |

Do not jump to a later phase's output format on an earlier phase's input. If skipping ahead is requested, note what was skipped.

## Verification standard

**A code read-through is not a test.**

Back any claim of "fixed" or "working" with an actual result: a computed style check, a DOM state assertion, a test run, a before/after comparison. Record it in `05-test-log.md` with what was asserted and what came back.

Where a project's test log already records a completed regression audit, treat it as ground truth. Do not re-verify it from scratch — spend verification effort on the new work.

### Three rules that came from real wasted cycles

*Adopted 2026-09-09, from the P6 Milestone Dashboard. Each caused a wrong conclusion that survived review.*

1. **Measure the element, not a parent.** When verifying a CSS property on a specific element, measure that element directly. A parent can behave differently — sticky headers were declared broken after measuring a whole `<tr>` whose cells, not the row, were the sticky things.
2. **Never self-verify from a screenshot.** For state checks (active, selected, checked), read `classList` or computed style directly. Screenshots are for showing the user, not for confirming your own work; a compressed image was misread as the wrong control being highlighted.
3. **A passing diff is not a passing test.** Code that reads correctly can still fail at runtime through browser quirks, event timing, or CSS specificity. Exercise the actual interaction and assert the resulting state.

### Report what happened

If a test fails, say so and show the output. If a step was skipped, say it was skipped. If a measurement disagrees with a recorded one, reconcile it before adopting either figure, and record why they differed.

A finding that contradicts an earlier claim of yours gets written down, not quietly corrected. The quiet correction loses the reason the earlier claim looked right, which is the thing that stops it recurring.

## `CLAUDE.md` contract

Every project's `CLAUDE.md` carries, in this order:

1. Where things are — the file map, and which file to read first.
2. Hard constraints — stack rules that must not be traded away.
3. Do not change — load-bearing implementation details, each with the reason it is load-bearing. A rule without a reason gets removed by the next person.
4. Versioning — per `02-versioning-standard.md`.
5. Verification standard — how "working" is proven in this project.
6. Working style.

It is the short form. Reasoning lives in `docs/00-project-context.md` and `docs/04-architecture.md`.
