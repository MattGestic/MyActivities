# Check map and the change-scoped runner

`tools/run_checks.py` replaces running the whole suite one check after another. It keeps a record of what each check actually exercised the last time it ran, and on each round it runs only the checks whose inputs changed (Matt, 2026-10-01). The record is `tools/check_map/ledger.json`; the human-readable view of it is `docs/component-register.md`, which is generated.

## How to use it

```
python3 tools/run_checks.py               # default (--changed): run what this round's edits can affect
python3 tools/run_checks.py --dry-run     # show the selection and why each check was picked; run nothing
python3 tools/run_checks.py --all         # run everything and rebuild the whole map
python3 tools/run_checks.py --jobs 3      # parallel checks (default 3)
python3 tools/run_checks.py --only p68_check,ds_check
python3 tools/run_checks.py --regions     # region counts for the current app file
python3 tools/run_checks.py --register    # regenerate docs/component-register.md only
```

Each check prints one summary line, then the run prints `selected / skipped / passed / failed`. The full output of every check run goes to `tools/check_map/last_run.txt` (not committed). The exit code is non-zero if any check that ran failed.

The suite is the one the old `suite.sh` ran: every `tools/*.py` except `d01_render`, `xer_to_aoa`, `p65_fixtures`, `import_check_lib` and the runner itself; `grid_view_assemble` runs as `--check`; `colour_audit` runs with `--strict`; plus the three node tests. A new `tools/*.py` is picked up automatically and runs because it has no record.

Every check still runs standalone exactly as before (`python3 tools/p68_check.py`). The only change to the checks is that their Chromium lookup honours `SRET_CHROME` when it is set.

## How it works

### 1. Regions

`tools/check_map/regions.py` splits `src/milestone-dashboard.html` into named regions, each with a sha256 of its text. Every byte belongs to exactly one region, so any edit changes at least one hash.

- **JS:** one region per top-level chunk of `<script id="app-script">` (a chunk starts at column 0, outside strings, comments, template literals and regexes). Named after what it declares (`js:openMsDialog`); other statements (IIFEs, listeners) are `js:@js:<hash of the statement text>`. The comment block directly above a declaration belongs to it.
- **CSS:** one region per rule of the main `<style>`, including rules inside `@media`. Keyed by selector plus media context with whitespace removed and `'` turned into `"`, so the key matches the browser's CSSOM `selectorText`. A rule's hash also folds in the key of the rule before it, so moving a rule (a cascade-order change with identical text) changes a hash.
- **Markup:** one region per element with an id (`markup:#ms-dialog`, `markup:#top-filter-bar`, `markup:#tfb-find`...) and per id-less top-level body element. A region's text has its nested id'd elements cut out, so an edit inside one card field changes that field's region, not the whole dialog.
- **Vendor:** `vendor-sheetjs`, `vendor-slickgrid`, `vendor-slickgrid-css`, one region each.
- **rest:** everything else (head, tags, text between body elements).

### 2. Coverage capture

`tools/check_map/run_one.py` runs a check with three environment additions:

- `SRET_CHROME` points at `tools/check_map/chrome_cov.py`. For each `--dump-dom` launch of the current app it instruments the temp page in place: a first-call counter at the top of every top-level function, and a sampler that records which main-stylesheet rules match an element (pseudo-classes stripped, `@media` only when it matches), which markup regions are rendered or looked up by the page, the classes and ids present, and whether the page walked the stylesheet's `cssRules`. It samples at load, every 1s of virtual time, at the end of the budget, and whenever the page measures layout after a DOM change, so a probe that opens the card, measures it and closes it in one task is still seen. The coverage block is stripped from the dumped DOM before the check sees it. `--screenshot` and `--print-to-pdf` launches are not instrumented and make the check `unmapped`. A page that is not the current app (the grid prototype, a `releases/` snapshot, a harness page) is passed through and recorded as such.
- `PYTHONPATH` puts `tools/check_map/hook/` first. Its `sitecustomize.py` installs a `sys.addaudithook()` on `open` in every Python process the check starts, and records the project files read: the check script, imported tools, fixtures, data files, modules. A file the check wrote itself is an output and is not recorded.
- `TMPDIR` is per check, so parallel checks never share temp directories or Chromium profiles.

### 3. The ledger

One record per check: the command, `lastRun`, commit, result (pass or fail plus the tail line), duration, `kind` (`browser`, `static`, `node` or `unmapped`), `used` (`{region: hash}`), `files` (`{path: hash}`), and for browser checks the classes and ids it saw and a static-assertion fingerprint (below).

`used` holds every function the check executed, every non-function top-level JS chunk (they run at load), every vendor region and `rest`, every CSS rule it matched plus every rule with no class or id in its selector (`:root`, `html[data-theme]`, `body`, `*`), and every markup region it rendered or looked up. If the page read the main sheet's `cssRules`, every CSS rule is used.

For a static check the app file is in `files` as a whole-file hash. For a browser check it is represented region by region instead, unless a sub-check it spawns (for example `colour_audit` inside `grid_view_check`) read the whole file, in which case the whole-file hash is kept as well.

**Static-assertion fingerprint.** Most browser checks also assert on the source text directly (`src.count("positionFixedPopup(") >= 4`, `"top:19.5px" not in src`, the version-literal count). Region coverage cannot see those, so for each browser check the runner counts every code-like string literal of the check script in the app text (verbatim, with whitespace removed, and as a regex when it looks like one). If any count changes, the check is selected. Literals found more than 50 times are left out: they move with almost any edit and are not assertion targets.

### 4. Selection

`--changed` recomputes region and file hashes and selects a check when:

- it has no ledger record, or its last result was a fail;
- it is `unmapped` (node, or a launch that could not be instrumented);
- it is a static or node check whose last run took under 5s;
- a file it read changed or disappeared;
- a region it used changed or disappeared;
- a static-assertion literal count changed;
- for a browser check, a region that did not exist at its last run can reach it: new top-level non-function JS (runs at load), a new vendor block, a new CSS rule with no class or id, a new CSS rule whose classes and ids the check saw in the DOM, or a second declaration of a function it ran.

A new markup element needs no rule of its own: it changes its parent region's text (or `rest` for a new top-level element).

The selected checks then run with coverage capture on and their records are replaced. Skipped checks keep their records and their `lastRun`.

## Limits: what this can miss

- **Code a check never executed, reached by a path the check never took.** The map is per run. If a change makes an already-exercised function call something new, that function's own region changed, so the check is selected. But if a check passes because a branch was never taken, a change that would make it take that branch elsewhere is caught only if the change is in a region the check used.
- **Load-time code is all-or-nothing.** Every top-level non-function chunk, which includes whole modules pasted as one IIFE (grid view, notes history, entries), counts as used by every browser check. Editing one of them selects every browser check. Safe, but not selective.
- **CSS matching is by selector, not by effect.** A rule counts as used if its selector (pseudo-classes stripped) matched any element at a sample point, rendered or not. That over-selects. It under-selects only for an element that existed for less than one task and was never measured, which no assertion can see either.
- **Static assertions built at runtime.** The fingerprint covers string literals written in the check script. An assertion whose search text is built from pieces (an f-string, a joined list) or lives in an imported helper is not fingerprinted.
- **Inputs outside Python and Chromium.** Files read by a node test are not recorded (node tests are fast and always run). Files a page loads by itself (`<script src>`) are recorded from the page text, not observed.
- **Non-determinism.** A flaky check that passed once is not re-run until its inputs change.
- **Environment.** Chromium, Python or fixtures outside the project directory changing are not tracked. Run `--all` after any toolchain change.
- **The ledger is only as fresh as the last run on this tree.** It records the commit each check ran against. Run `--all` after switching branches or merging, and whenever the runner itself changes.

## Each development round

```
python3 tools/run_checks.py --dry-run     # optional: see what will run and why
python3 tools/run_checks.py               # run it
```

Commit `tools/check_map/ledger.json` and `docs/component-register.md` with the round. Run `--all` before a release, after a merge, and after editing anything in `tools/check_map/`.

## Modules (D-30)

Module regions in the app are pasted by `tools/modules_embed.py` between `@module` markers. After `--embed`, run `tools/run_checks.py` as usual: the changed module region selects the checks.

**Limit (TD-246):** a module's IIFE is one top-level JS chunk, and it runs at load, so every browser check uses it. A change to an embedded module therefore re-selects every browser check that loads the app. The module's own test (`MODULE.md`, Tests) is the fast loop during development; the full selection runs once per embed.
