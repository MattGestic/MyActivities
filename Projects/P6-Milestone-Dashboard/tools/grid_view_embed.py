#!/usr/bin/env python3
"""Re-paste the grid view module into the app (TD-229, P70). Since D-30 a thin
wrapper over tools/modules_embed.py, kept because tools/p61_check.py imports
parts() and APP_FEATURES from here.

Which grid files are pasted, in what order, is now the "grid-view" entry of
src/modules/MODULES.json (embed.js.files / embed.css.files). The app's
SRETGrid.setup() call, beside openGridView(), says which features are on;
APP_FEATURES below is derived from the manifest and tools/p61_check.py
checks the two agree.

  python3 tools/grid_view_embed.py           # same as modules_embed.py --embed grid-view
  python3 tools/grid_view_embed.py --check   # exit 1 if the grid regions are not the module, pasted
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import modules_embed as ME  # noqa: E402

ROOT = ME.ROOT
APP = ME.APP
MOD = ROOT / "src" / "modules" / "grid-view"


def _grid():
    return next(m for m in ME.load_manifest()["modules"] if m["id"] == "grid-view")


# Features pasted into the app, in the core's load order (features/<name>.js).
APP_FEATURES = [f[len("features/"):-len(".js")] for f in _grid()["embed"]["js"]["files"] if f.startswith("features/")]


def parts(ext):
    """[(name, text)] of the grid files the app pastes for ext ('js' or 'css'), in order."""
    names = _grid()["embed"][ext]["files"]
    return [(n, (MOD / n).read_text(encoding="utf-8").rstrip("\n")) for n in names]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    man = ME.load_manifest()
    src = APP.read_text(encoding="utf-8")
    if not a.check:
        src, changed = ME.embed(man, src, {"grid-view"})
        APP.write_text(src, encoding="utf-8")
        ME.save_manifest(man)
        for c in changed:
            print("rewrote", c)
    bad = [(k, msg) for k, msg in ME.check(man, src) if msg.startswith("grid-view")]
    for k, msg in bad:
        print(f"{k:<12}{msg}")
    if bad:
        return 1
    print("The app's grid regions are the module files, pasted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
