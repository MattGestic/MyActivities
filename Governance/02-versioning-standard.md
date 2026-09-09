# Versioning Standard

## Format

```
Major.Minor.Patch-PartialLetter/Number
```

Example: `3.1.0-P1`

| Component | Meaning | Confirmation needed |
|---|---|---|
| **Major** | Breaking change, or a deliberate reset of the product's shape | **Yes — explicit confirmation required** |
| **Minor** | A batch of real work has accumulated under the current minor. Bump and reset partials to `P1`. | No |
| **Patch** | Fix within the current minor | No |
| **Partial** (`-P#`) | Incremental work accumulating under the current minor | No |

Partials accumulate under a minor version. When a batch of real work has accumulated, bump the minor and reset the partial. That does not require asking. **Bumping the major does.**

## Single source of truth

The version lives in **exactly one place** in the code — a single constant (`APP_VERSION` or equivalent). Everything else reads from it: page title, UI labels, export payloads, about screens.

**Never hand-edit a derived copy.** Every project that has tried this has had the copies drift.

If a project has a version string appearing somewhere that does not read from the constant, that is a defect. Raise it as a `TD-##`.

## Filenames

**Versioned filenames are not used.** The working file keeps a stable path.

Version-in-filename (`dashboard_v3_1_0.html`) makes every change a whole-file add rather than a diff, which defeats the reason for using git at all. It also produces silent ambiguity — a file saved as `_11` may mean partial 11, or may be the eleventh save copy. That exact ambiguity cost a round trip on the P6 Milestone Dashboard migration.

Version identity comes from three places instead:

1. The `APP_VERSION` constant in the working file.
2. A git tag on the commit: `v3.1.0-P1`.
3. A snapshot in `releases/`, named `v<version>_<short-description>.<ext>`.

## Releasing

For anything shipped to a user:

```bash
# 1. Bump the version constant in the working file. Nothing else.
# 2. Commit.
# 3. Tag.
git tag -a v3.1.0-P1 -m "<app> v3.1.0-P1 — <one line on what shipped>"
git push origin <branch> && git push origin v3.1.0-P1
# 4. Copy the working file into releases/v3.1.0-P1_<description>.<ext>
```

`releases/` snapshots are never edited after the fact. If a release was wrong, ship a new one.

## Recording it

Every release gets a row in the project's `05-test-log.md` acceptance record: date, criteria met, exceptions accepted, publish target, version.

"Exceptions accepted" is not optional. A release with known open items is fine; a release whose known open items were not written down is not.
