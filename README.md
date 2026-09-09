# MyActivities — branch: `p6-milestone-dashboard`

This repository hosts several independent applications. Each application lives on its own **orphan branch**, which serves as that application's main branch. Branches share no git history, so unrelated apps never appear in each other's diffs.

**This branch is the main branch for the P6 Milestone Dashboard. Do not merge it into `main`.**

| Branch | Application |
|---|---|
| `main` | MyActivities fitness programme site |
| `p6-milestone-dashboard` | P6 Milestone Dashboard (Eskay Creek PFS deliverable milestone tracking) |

## Contents of this branch

```
Projects/P6-Milestone-Dashboard/
```

See [`Projects/P6-Milestone-Dashboard/README.md`](Projects/P6-Milestone-Dashboard/README.md) to run it, and [`Projects/P6-Milestone-Dashboard/CLAUDE.md`](Projects/P6-Milestone-Dashboard/CLAUDE.md) before making any code change.

## Adding another application

Create a new orphan branch and give it its own folder under `Projects/`:

```bash
git checkout --orphan <app-branch-name>
git rm -rf --cached .
mkdir -p Projects/<App-Name>
```

Work on that branch as the app's main. Do not cross-merge between application branches.
