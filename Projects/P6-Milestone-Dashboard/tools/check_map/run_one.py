#!/usr/bin/env python3
"""Run one check with coverage capture on, and report what it touched.

    python3 tools/check_map/run_one.py [--json] -- python3 tools/p68_check.py

The check runs exactly as it would on its own (same argv, cwd = project root),
with three environment additions:

  SRET_CHROME     -> tools/check_map/chrome_cov.py, so every --dump-dom launch
                     of the app is instrumented (function, CSS and markup
                     coverage, appended to SRET_COV_OUT);
  PYTHONPATH      -> tools/check_map/hook first, whose sitecustomize installs a
                     sys.addaudithook() on `open` in every Python process the
                     check starts and appends the project files it read to
                     SRET_FILES_OUT;
  SRET_ROOT       -> the project root (only files under it are recorded).

Returns (and with --json prints) {rc, tail, duration, output, launches, files}.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(cmd, timeout=1800, capture=True):
    with tempfile.TemporaryDirectory(prefix="sret-run-") as td:
        cov = os.path.join(td, "cov.jsonl")
        files = os.path.join(td, "files.jsonl")
        env = dict(os.environ)
        env["SRET_CHROME"] = str(HERE / "chrome_cov.py")
        env["SRET_COV_OUT"] = cov
        env["SRET_FILES_OUT"] = files
        env["SRET_ROOT"] = str(ROOT)
        env["PYTHONPATH"] = str(HERE / "hook") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        # each check gets its own TMPDIR so parallel Chromium profiles and temp
        # pages can never share a directory
        tmp = os.path.join(td, "tmp")
        os.mkdir(tmp)
        env["TMPDIR"] = tmp
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=timeout)
            rc = p.returncode
            output = p.stdout.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired as e:
            rc = 124
            output = (e.stdout or b"").decode("utf-8", errors="replace") + f"\n[run_one] timeout after {timeout}s"
        dur = time.time() - t0
        launches = _jsonl(cov)
        reads, writes = set(), set()
        procs = []
        for r in _jsonl(files):
            argv0 = (r.get("argv") or [""])[0]
            if argv0.endswith("chrome_cov.py"):
                continue   # the wrapper's own reads are not the check's inputs
            reads.update(r.get("reads", []))
            writes.update(r.get("writes", []))
            procs.append({"argv": r.get("argv"), "reads": sorted(os.path.relpath(x, ROOT) for x in r.get("reads", []))})
    lines = [ln for ln in output.splitlines() if ln.strip()]
    tail = lines[-1].strip() if lines else ""
    # a file the check wrote itself is an output, not an input
    rel = sorted(os.path.relpath(p, ROOT) for p in reads - writes if os.path.exists(p))
    return {"rc": rc, "tail": tail[:300], "duration": round(dur, 1), "output": output,
            "launches": launches, "files": rel, "procs": procs}


def _jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except ValueError:
                        out.append({"launch": "corrupt"})
    return out


def main(argv):
    as_json = False
    if argv and argv[0] == "--json":
        as_json = True
        argv = argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        sys.exit(__doc__)
    r = run(argv)
    if as_json:
        r = dict(r)
        r["output"] = r["output"][-4000:]
        print(json.dumps(r, indent=1)[:200000])
    else:
        sys.stdout.write(r["output"])
        kinds = {}
        for la in r["launches"]:
            kinds[la.get("launch")] = kinds.get(la.get("launch"), 0) + 1
        print(f"[run_one] rc={r['rc']} {r['duration']}s launches={kinds} files={len(r['files'])}")
    return r["rc"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
