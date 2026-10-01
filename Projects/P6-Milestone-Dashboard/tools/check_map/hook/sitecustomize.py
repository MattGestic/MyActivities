"""File-read capture for tools/check_map/run_one.py.

run_one.py puts this directory first on PYTHONPATH, so every Python process a
check starts (the check itself, any Python child it spawns, the Chromium
wrapper) imports this at startup. When SRET_FILES_OUT is set it installs a
sys.addaudithook() on the `open` event and, at exit, appends one JSON line
{pid, argv, reads, writes} with the project files the process opened.
Without SRET_FILES_OUT it does nothing. It then chains to the next
sitecustomize on sys.path, so the interpreter behaves as it would without it.
"""
import os
import sys


def _install():
    out = os.environ.get("SRET_FILES_OUT")
    root = os.environ.get("SRET_ROOT")
    if not out or not root:
        return
    root = os.path.realpath(root)
    skip = os.path.join(root, "tools", "check_map")
    reads, writes = set(), set()
    wflags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def norm(p):
        if isinstance(p, int):
            return None
        if isinstance(p, bytes):
            p = os.fsdecode(p)
        try:
            p = os.path.realpath(os.fspath(p))
        except Exception:
            return None
        if not p.startswith(root + os.sep) or p.startswith(skip):
            return None
        if "__pycache__" in p:   # a cached module stands for its source file
            d, f = os.path.split(p)
            p = os.path.join(os.path.dirname(d), f.split(".")[0] + ".py")
        return p

    def hook(event, args):
        if event != "open":
            return
        try:
            path, mode, flags = args
            p = norm(path)
            if p is None:
                return
            if mode is None:
                w = bool(flags & wflags)
            else:
                w = any(c in mode for c in "wax+")
            (writes if w else reads).add(p)
        except Exception:
            pass

    def flush():
        import json
        line = json.dumps({"pid": os.getpid(), "argv": sys.argv[:3],
                           "reads": sorted(reads), "writes": sorted(writes)}) + "\n"
        try:
            fd = os.open(out, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            os.write(fd, line.encode("utf-8"))
            os.close(fd)
        except Exception:
            pass

    import atexit
    atexit.register(flush)
    sys.addaudithook(hook)


_install()


def _chain():
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    for p in sys.path:
        if not p or os.path.abspath(p) == here:
            continue
        cand = os.path.join(p, "sitecustomize.py")
        if os.path.isfile(cand):
            spec = importlib.util.spec_from_file_location("_sret_chained_sitecustomize", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return


_chain()
