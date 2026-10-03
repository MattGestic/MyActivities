#!/usr/bin/env python3
"""Change-scoped check runner (Matt, 2026-10-01). See docs/check-map.md.

    python3 tools/run_checks.py               # --changed: run only what an edit can affect
    python3 tools/run_checks.py --dry-run     # print the selection and the reason for each check
    python3 tools/run_checks.py --all         # run everything and rebuild the whole map
    python3 tools/run_checks.py --jobs 3      # parallel checks (default 3)
    python3 tools/run_checks.py --only p68_check,ds_check
    python3 tools/run_checks.py --register    # regenerate docs/component-register.md only
    python3 tools/run_checks.py --regions     # region counts per kind for the current app file

Every run captures coverage (tools/check_map/run_one.py) and rewrites the run
checks' records in tools/check_map/ledger.json. A check is selected when any
of these holds:
  - it has no ledger record, or its last result was a fail;
  - it is `unmapped` (node, or a launch that could not be instrumented);
  - it is a static or node check whose last run took under 5s;
  - one of the files it read changed or disappeared;
  - one of the app regions it exercised changed or disappeared;
  - (browser checks) a region that did not exist at its last run could reach
    it: new load-time JS, a new rule with no class/id, a new rule whose
    classes/ids it rendered, a redefinition of a function it ran.
"""
import argparse
import concurrent.futures as cf
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "check_map"))
import regions as R  # noqa: E402
import run_one  # noqa: E402
import static_lits  # noqa: E402

APP_REL = "src/milestone-dashboard.html"
LEDGER = ROOT / "tools" / "check_map" / "ledger.json"
LAST_RUN = ROOT / "tools" / "check_map" / "last_run.txt"
REGISTER = ROOT / "docs" / "component-register.md"
EXCLUDE = {"d01_render", "xer_to_aoa", "grid_view_assemble", "p65_fixtures", "import_check_lib", "run_checks"}
EXTRA_ARGS = {"colour_audit": ["--strict"], "grid_view_embed": ["--check"], "modules_embed": ["--check"]}
NODE_TESTS = ["notes_store_test", "form_to_entry_test", "notes_export_test", "continue_file_test"]
FAST = 5.0


def suite():
    """[(name, cmd)] in suite.sh order."""
    out = []
    for f in sorted((ROOT / "tools").glob("*.py")):
        b = f.stem
        if b in EXCLUDE:
            continue
        out.append((b, ["python3", f"tools/{b}.py"] + EXTRA_ARGS.get(b, [])))
    out.append(("grid_view_assemble", ["python3", "tools/grid_view_assemble.py", "--check"]))
    for t in NODE_TESTS:
        out.append((t, ["node", f"tools/{t}.mjs"]))
    return out


def fhash(path):
    try:
        return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()[:16]
    except OSError:
        return None


def load_ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"version": 1, "app": APP_REL, "universes": {}, "checks": {}}


def save_ledger(led):
    # one line per check record so a round's git diff shows which records moved
    lines = ["{", f' "version": {led["version"]},', f' "app": {json.dumps(led["app"])},', ' "universes": {']
    us = sorted(led["universes"].items())
    for i, (k, v) in enumerate(us):
        lines.append(f'  {json.dumps(k)}: {json.dumps(v, separators=(",", ":"))}' + ("," if i < len(us) - 1 else ""))
    lines.append(" },")
    lines.append(' "checks": {')
    cs = sorted(led["checks"].items())
    for i, (k, v) in enumerate(cs):
        lines.append(f'  {json.dumps(k)}: {json.dumps(v, sort_keys=True, separators=(",", ":"))}'
                     + ("," if i < len(cs) - 1 else ""))
    lines.append(" }")
    lines.append("}")
    LEDGER.write_text("\n".join(lines) + "\n", encoding="utf-8")


def git_commit():
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", APP_REL], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        return sha + ("+app-modified" if dirty else "")
    except OSError:
        return "unknown"


# --------------------------------------------------------------------------
# coverage -> used regions
# --------------------------------------------------------------------------
class AppMap:
    def __init__(self, html):
        self.text = html
        self.regs = R.split(html)
        self.by = {r["name"]: r for r in self.regs}
        self.hash = {r["name"]: r["hash"] for r in self.regs}
        self.fn = {}
        self.css = {}
        self.mk = {}
        for r in self.regs:
            if r.get("fn"):
                self.fn.setdefault(r["ident"], []).append(r["name"])
            if r.get("key"):
                self.css.setdefault(r["key"], []).append(r["name"])
            if r["kind"] == "markup":
                self.mk.setdefault(r["name"][len("markup:"):].split("~")[0], []).append(r["name"])
        self.always_browser = [r["name"] for r in self.regs
                               if (r["kind"] == "js" and not r.get("fn")) or r["kind"] in ("vendor", "rest")
                               or (r["kind"] == "css" and r.get("always"))]
        self.all_css = [r["name"] for r in self.regs if r["kind"] == "css"]
        names = sorted(self.hash)
        self.universe_id = hashlib.sha256("\n".join(names).encode()).hexdigest()[:12]
        self.names = names


def classify(res):
    kinds = {}
    for la in res["launches"]:
        k = la.get("launch")
        if k == "app" and (not la.get("cov") or la["cov"].get("fatal")):
            k = "nocov"
        kinds[k] = kinds.get(k, 0) + 1
    return kinds


def build_record(name, cmd, res, amap, commit):
    kinds = classify(res)
    if cmd[0] == "node":
        kind = "node"
    elif kinds.get("uninstrumented") or kinds.get("nocov") or kinds.get("corrupt"):
        kind = "unmapped"
    elif kinds.get("app"):
        kind = "browser"
    else:
        kind = "static"
    used = set()
    seen_c, seen_i, unknown = set(), set(), set()
    cssom = False
    if kind in ("browser", "unmapped") and kinds.get("app"):
        used.update(amap.always_browser)
        for la in res["launches"]:
            c = la.get("cov") or {}
            if la.get("launch") != "app" or c.get("fatal"):
                continue
            for f in c.get("fn", []):
                if f in amap.fn:
                    used.update(amap.fn[f])
                else:
                    unknown.add("fn:" + f)
            for k in c.get("css", []):
                if k in amap.css:
                    used.update(amap.css[k])
                else:
                    unknown.add("css:" + k)
            for k in c.get("mk", []):
                if k in amap.mk:
                    used.update(amap.mk[k])
                else:
                    unknown.add("mk:" + k)
            if c.get("cssom"):
                cssom = True
            seen_c.update(c.get("cls", []))
            seen_i.update(c.get("ids", []))
        if cssom:
            used.update(amap.all_css)
    files = set(res["files"])
    script = cmd[1] if len(cmd) > 1 else None
    if script:
        files.add(script)
    sub_reads_app = [" ".join(p["argv"] or []) for p in res.get("procs", [])
                     if APP_REL in p["reads"] and (p["argv"] or [""])[0] != script]
    if kind == "browser" and not sub_reads_app:
        files.discard(APP_REL)   # represented region by region instead
    for la in res["launches"]:
        for ref in la.get("refs", []) or []:
            try:
                files.add(os.path.relpath(ref, ROOT))
            except ValueError:
                pass
    files = {f: fhash(ROOT / f) for f in sorted(files) if not f.startswith("..") and (ROOT / f).is_file()}
    rec = {
        "cmd": cmd,
        "lastRun": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "commit": commit,
        "result": {"status": "pass" if res["rc"] == 0 else "fail", "rc": res["rc"], "tail": res["tail"]},
        "duration": res["duration"],
        "kind": kind,
        "launches": kinds,
        "used": {n: amap.hash[n] for n in sorted(used)},
        "files": files,
        "universe": amap.universe_id,
    }
    if kind in ("browser", "unmapped") and kinds.get("app"):
        rec["seen"] = {"cls": sorted(seen_c), "ids": sorted(seen_i)}
        rec["cssom"] = cssom
    if sub_reads_app:
        rec["appReadBy"] = sub_reads_app[:5]   # a sub-check read the whole file: whole-file hash kept
    if kind == "browser" and script and (ROOT / script).is_file():
        rec["static"] = static_lits.fingerprint((ROOT / script).read_text(encoding="utf-8"), amap.text)
    if unknown:
        rec["unmappedCoverage"] = sorted(unknown)[:200]
    return rec


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------
def select(name, rec, amap, universes, file_cache):
    """Return a list of reasons (empty = skip)."""
    if rec is None:
        return ["no ledger record"]
    why = []
    if rec["result"]["status"] != "pass":
        why.append("last run failed")
    if rec["kind"] == "unmapped":
        why.append("unmapped (" + ", ".join(f"{k}={v}" for k, v in sorted(rec.get("launches", {}).items())) + ")")
    if rec["kind"] in ("static", "node") and rec["duration"] < FAST:
        why.append(f"{rec['kind']} check under {FAST:.0f}s ({rec['duration']}s)")
    ch = []
    for f, h in rec["files"].items():
        if f not in file_cache:
            file_cache[f] = fhash(ROOT / f)
        if file_cache[f] != h:
            ch.append(f + (" (gone)" if file_cache[f] is None else ""))
    if ch:
        why.append("file changed: " + ", ".join(ch[:4]) + (f" +{len(ch) - 4}" if len(ch) > 4 else ""))
    rch = []
    for n, h in rec["used"].items():
        cur = amap.hash.get(n)
        if cur != h:
            rch.append(n + (" (gone)" if cur is None else ""))
    if rch:
        why.append(f"{len(rch)} used region(s) changed: " + ", ".join(rch[:5]) + (" ..." if len(rch) > 5 else ""))
    if rec.get("static") and not ch:
        script = rec["cmd"][1]
        lits = static_lits.changed((ROOT / script).read_text(encoding="utf-8"), amap.text, rec["static"])
        if lits:
            why.append("static assertion literal count changed: " + ", ".join(repr(x[:40]) for x in lits[:3])
                       + (f" +{len(lits) - 3}" if len(lits) > 3 else ""))
    if rec["kind"] in ("browser", "unmapped") and "seen" in rec:
        old = universes.get(rec.get("universe"))
        if old is None:
            why.append("region universe of last run unknown")
        else:
            oldset = set(old)
            new = [n for n in amap.names if n not in oldset]
            hits = new_region_hits(new, rec, amap)
            if hits:
                why.append("new region(s) can reach it: " + ", ".join(hits[:5]) + (" ..." if len(hits) > 5 else ""))
    return why


def new_region_hits(new, rec, amap):
    seen_c = set(rec["seen"]["cls"])
    seen_i = set(rec["seen"]["ids"])
    used_fn = {amap.by[n]["ident"] for n in rec["used"] if n in amap.by and amap.by[n].get("fn")}
    used_fn |= {n.split(":", 1)[1].split("~")[0] for n in rec["used"] if n.startswith("js:")}
    hits = []
    for n in new:
        r = amap.by[n]
        k = r["kind"]
        if k in ("vendor", "rest"):
            hits.append(n)
        elif k == "js":
            if not r.get("fn") or r["ident"] in used_fn:
                hits.append(n)
        elif k == "css":
            if r.get("always") or rec.get("cssom"):
                hits.append(n)
            else:
                for part in r.get("tokens", []):
                    if all(c in seen_c for c in part["cls"]) and all(i in seen_i for i in part["ids"]):
                        hits.append(n)
                        break
        # markup: a new element changes its parent region's text (placeholder),
        # or `rest` for a new top-level element, so it is already caught.
    return hits


# --------------------------------------------------------------------------
def main(argv):
    ap = argparse.ArgumentParser(description="Change-scoped check runner")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--changed", action="store_true", help="(default) run checks whose inputs changed")
    g.add_argument("--all", action="store_true", help="run every check and rebuild the map")
    ap.add_argument("--dry-run", action="store_true", help="print selection and reasons, run nothing")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only", help="comma-separated check names (restricts the suite)")
    ap.add_argument("--register", action="store_true", help="regenerate docs/component-register.md and exit")
    ap.add_argument("--regions", action="store_true", help="print region counts for the app file and exit")
    ap.add_argument("--app", help="evaluate the selection against this app file instead (dry-run only)")
    ap.add_argument("--json", help="write the selection as JSON to this path")
    a = ap.parse_args(argv)

    if a.regions:
        R.main(["regions"])
        return 0
    app_path = pathlib.Path(a.app) if a.app else ROOT / APP_REL
    if a.app and not a.dry_run:
        sys.exit("--app is for --dry-run only (checks always read src/milestone-dashboard.html)")
    led = load_ledger()
    amap = AppMap(app_path.read_text(encoding="utf-8"))
    if a.register:
        import register
        register.write(led, amap, REGISTER, suite())
        print(f"wrote {REGISTER.relative_to(ROOT)}")
        return 0

    checks = suite()
    if a.only:
        want = set(a.only.split(","))
        checks = [c for c in checks if c[0] in want]
        missing = want - {c[0] for c in checks}
        if missing:
            sys.exit("unknown check(s): " + ", ".join(sorted(missing)))
    file_cache = {}
    if a.app:
        file_cache[APP_REL] = fhash(app_path)
    plan = []
    for name, cmd in checks:
        rec = led["checks"].get(name)
        if a.all:
            why = ["--all"]
        else:
            why = select(name, rec, amap, led["universes"], file_cache)
            if rec and rec.get("cmd") != cmd:
                why.append("command changed")
        plan.append((name, cmd, why))
    sel = [p for p in plan if p[2]]
    skip = [p for p in plan if not p[2]]

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"selected": {n: w for n, _, w in sel},
                                                     "skipped": [n for n, _, _ in skip]}, indent=1))
    if a.dry_run:
        for name, _, why in sel:
            print(f"RUN   {name:28s} {'; '.join(why)}")
        for name, _, _ in skip:
            rec = led["checks"][name]
            print(f"skip  {name:28s} unchanged since {rec['lastRun']} ({rec['kind']}, {len(rec['used'])} regions, "
                  f"{len(rec['files'])} files)")
        print(f"\n{len(sel)} selected / {len(skip)} skipped of {len(plan)}")
        return 0

    commit = git_commit()
    lock = threading.Lock()
    results = {}
    t_all = time.time()
    order = sorted(sel, key=lambda p: -(led["checks"].get(p[0], {}).get("duration", 60)))

    def work(p):
        name, cmd, why = p
        res = run_one.run(cmd)
        rec = build_record(name, cmd, res, amap, commit)
        with lock:
            results[name] = (res, rec, why)
            st = "PASS" if res["rc"] == 0 else "FAIL"
            print(f"{st}  {name:28s} {res['duration']:7.1f}s  {rec['kind']:9s} {res['tail'][:90]}", flush=True)
        return name

    print(f"running {len(sel)} of {len(plan)} checks, {a.jobs} at a time", flush=True)
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        list(ex.map(work, order))
    wall = time.time() - t_all

    # the app file must not have moved under us; if it did, keep the pre-run
    # hashes (the next --changed run then re-selects these checks)
    now = R.split((ROOT / APP_REL).read_text(encoding="utf-8"))
    if {r["name"]: r["hash"] for r in now} != amap.hash:
        print("WARNING: the app file changed during the run; records keep the pre-run hashes")
    led["universes"][amap.universe_id] = amap.names
    for name, (res, rec, why) in results.items():
        led["checks"][name] = rec
    live = {u for u in (r.get("universe") for r in led["checks"].values()) if u}
    led["universes"] = {k: v for k, v in led["universes"].items() if k in live}
    save_ledger(led)
    try:
        import register
        register.write(led, amap, REGISTER, suite())
    except Exception as e:  # the register is documentation; never fail the run on it
        print(f"WARNING: register not regenerated: {e}")

    npass = sum(1 for r in results.values() if r[0]["rc"] == 0)
    nfail = len(results) - npass
    summary = (f"{len(sel)} selected / {len(skip)} skipped / {npass} passed / {nfail} failed"
               f"  (wall {wall / 60:.1f} min, {a.jobs} jobs)")
    with LAST_RUN.open("w", encoding="utf-8") as fh:
        fh.write(f"run_checks {' '.join(argv)}  at {datetime.datetime.now().isoformat(timespec='seconds')}"
                 f"  commit {commit}\n{summary}\n\n")
        for name, cmd, why in plan:
            if name in results:
                res, rec, w = results[name]
                fh.write(f"{'PASS' if res['rc'] == 0 else 'FAIL'}  {name}  {res['duration']}s  kind={rec['kind']}"
                         f"  launches={rec['launches']}\n  why: {'; '.join(w)}\n  tail: {res['tail']}\n")
            else:
                fh.write(f"skip  {name}\n")
        fh.write("\n\n======== full output of each check run ========\n")
        for name in sorted(results):
            res, rec, _ = results[name]
            fh.write(f"\n---------------- {name}  rc={res['rc']}  {' '.join(rec['cmd'])}\n{res['output']}\n")
            if rec.get("unmappedCoverage"):
                fh.write(f"[coverage not mapped to a region: {rec['unmappedCoverage'][:20]}]\n")
    print("\n" + summary)
    print(f"full results: {LAST_RUN.relative_to(ROOT)}")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
