# MyActivities — Projects Hub

**Default branch. This is the index.**

This repository hosts several independent applications. Each lives on its own **orphan branch** which serves as that application's main branch. Branches share no git history, so unrelated applications never appear in each other's diffs.

This branch holds no application code. It carries three things:

1. **The index** — the project register below.
2. **`Governance/`** — the standards every project in this repository follows.
3. **`Resources/`** — the governed library of reusable components, templates, and snippets.

---

## Project register

| Project | Branch | Status | Version | Docs |
|---|---|---|---|---|
| **P6 Milestone Dashboard** (SRET) — Eskay Creek PFS deliverable milestone tracking | `p6-milestone-dashboard` | Active | `3.1.0-P1` | [README](https://github.com/MattGestic/MyActivities/blob/p6-milestone-dashboard/Projects/P6-Milestone-Dashboard/README.md) · [kit](https://github.com/MattGestic/MyActivities/tree/p6-milestone-dashboard/Projects/P6-Milestone-Dashboard/docs) |
| **MyFitnessPOC** — fitness programme site | `MyFitnessPOC` | Proof of concept | — | — |
| *(unclassified)* | `agent/hiit-audio-package` | Needs triage — classify or delete | — | — |

Register rules:
- One row per application. Add the row in the same change that creates the branch.
- `Status` is one of: Active · Maintenance · Proof of concept · Archived · Needs triage.
- `Version` mirrors the project's own `APP_VERSION` or equivalent. It is copied here, never authored here.

---

## Governance

Repository-wide standards. A project follows these; it does not restate them in its own docs.

| Document | Covers |
|---|---|
| [`Governance/00-repository-model.md`](Governance/00-repository-model.md) | Branch-per-application model, naming, creating and retiring a project |
| [`Governance/01-project-standard.md`](Governance/01-project-standard.md) | Required project structure, the six-file kit, ID schemes, phase gates |
| [`Governance/02-versioning-standard.md`](Governance/02-versioning-standard.md) | Version format, when to bump, tags and release snapshots |
| [`Governance/03-documentation-standard.md`](Governance/03-documentation-standard.md) | Doc conventions, tone, output rules, what belongs where |
| [`Governance/04-resource-governance.md`](Governance/04-resource-governance.md) | Intake criteria for `Resources/`, review cycle, retirement |

---

## Resources

Reusable components, templates, and snippets that have passed intake. See [`Resources/README.md`](Resources/README.md) for the catalogue.

**Nothing enters `Resources/` without passing the intake gate** in `Governance/04-resource-governance.md`. The gate exists because an ungoverned snippet folder becomes a graveyard of half-working code that costs more to evaluate than to rewrite. Every entry must be genuinely reusable, self-contained, documented, and demonstrated.

To propose a resource: copy `Resources/_new-resource/`, fill in `RESOURCE.md`, and run it against the intake checklist. Record the result in the catalogue.

---

## Working in this repository

- **Never merge one application branch into another.** They are independent roots.
- **Never merge an application branch into this one.** This branch carries no application code.
- Changes to a project go on that project's branch. Changes to standards or resources go here.
- Each project branch has its own `CLAUDE.md` with that project's constraints. Read it before touching code.
