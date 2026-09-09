# Repository Model

Applies to every branch in `MattGestic/MyActivities`.

## The model

One repository, many independent applications, **one orphan branch per application**.

Branches share no git history. An application branch is that application's main branch. It never merges anywhere and nothing merges into it.

```
main-projects-hub   (default)   index + governance + resources, no application code
├─ p6-milestone-dashboard       P6 Milestone Dashboard
├─ MyFitnessPOC                 fitness programme site
└─ <next-app>                   ...
```

### Why orphan branches rather than a shared root

| Option | Problem |
|---|---|
| One `main`, all apps in folders | Every diff, log, and blame mixes unrelated applications. A fitness site change shows up when reviewing a schedule dashboard. |
| One repository per application | Fragments a personal workspace across many repos. Shared standards and reusable resources have nowhere to live. |
| **Orphan branch per application** | Each app has a clean, isolated history. Standards and resources live once, on the hub. |

The cost is that `git log` across applications is not possible and cherry-picking between them does not work cleanly. That is accepted — these applications share no code, only conventions.

## Branch naming

- Application branches: `kebab-case` describing the application (`p6-milestone-dashboard`) or the established product name (`MyFitnessPOC`).
- No prefixes such as `feature/` or `app/` on an application's main branch. The branch **is** the main.
- Working branches within an application: `<app-branch>/<short-description>`, merged back into the application branch and deleted.
- The hub is always `main-projects-hub` and is always the repository default.

## Creating a new application

```bash
git checkout --orphan <app-branch-name>
git rm -rf --cached .
# remove any files carried over from the previous checkout
mkdir -p Projects/<App-Name>
```

Then, in the same change:

1. Build the project structure required by `01-project-standard.md`.
2. Write the project's `CLAUDE.md` and `README.md`.
3. Add a root `README.md` on the branch stating which application it is and pointing at the hub for standards.
4. Add the register row on `main-projects-hub`.

A branch without a register row is invisible. A register row without a branch is a lie. Do both.

## Retiring an application

1. Set the register row `Status` to `Archived` and note the date.
2. Leave the branch in place. Do not delete it — the register row is the record, and deleting the branch destroys the history it points at.
3. If the work moves elsewhere, put the destination in the register row.

## Hard rules

- **Never merge an application branch into another application branch.** Unrelated roots; the merge would be meaningless and destructive to both histories.
- **Never merge an application branch into `main-projects-hub`.** The hub carries no application code.
- **Never open a pull request from an application branch into the hub or another application branch.** A PR between unrelated roots proposes merging two whole trees.
- Pull requests within an application (working branch into that application's main) are normal and expected.
- The default branch stays `main-projects-hub`. Changing it changes what a fresh clone lands on.

## Per-branch expectations

Every branch has at its root:

- `README.md` — what this branch is, and a pointer to the hub for standards.
- `.gitattributes` — line-ending and binary handling appropriate to that application.

Every application branch additionally has `Projects/<App-Name>/` containing the structure in `01-project-standard.md`.
