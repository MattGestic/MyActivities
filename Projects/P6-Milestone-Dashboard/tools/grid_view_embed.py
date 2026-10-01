#!/usr/bin/env python3
"""Re-paste the grid view module into the app (TD-229, P70).

The app embeds src/modules/grid-view/ by pasting, not by a build: the core
and the features the app uses, each file unchanged, in load order, between
fixed banners. This rewrites exactly those two blocks of
src/milestone-dashboard.html from the module files, so a re-paste is one
command and touches nothing else:

  1. main <style>: from the "GRID VIEW (D-09" banner to the end of the grid
     CSS (the end of the main style, where P61 put it);
  2. top of app-script: from the "GRID VIEW MODULE (D-09" banner to
     "// ============ END GRID VIEW MODULE ============".

The app's SRETGrid.setup() call, beside openGridView(), says which features
are on; APP_FEATURES below must name the same ones (tools/p61_check.py
checks both).

  python3 tools/grid_view_embed.py           # rewrite the two blocks
  python3 tools/grid_view_embed.py --check   # exit 1 if the app is not the module, pasted
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "src" / "milestone-dashboard.html"
MOD = ROOT / "src" / "modules" / "grid-view"
# The app has no lists (SRETCollections) or import (SRETMsImport) screens and
# no refs columns, so only these are pasted. Order: the core's load order.
APP_FEATURES = ["marks", "bulk-edit", "xlsx"]

CSS_START = "/* ============================================================\n   GRID VIEW (D-09"
JS_START = "// ============================================================\n// GRID VIEW MODULE (D-09"
JS_END = "// ============ END GRID VIEW MODULE ============"


def parts(ext):
    out = [("grid-view." + ext, (MOD / ("grid-view." + ext)).read_text(encoding="utf-8").rstrip("\n"))]
    for f in APP_FEATURES:
        p = MOD / "features" / f"{f}.{ext}"
        if p.exists():
            out.append((f"features/{f}.{ext}", p.read_text(encoding="utf-8").rstrip("\n")))
        elif ext == "js":
            sys.exit(f"features/{f}.js is missing.")
    return out


def css_block():
    names = ", ".join(n for n, _ in parts("css"))
    head = ("/* ============================================================\n"
            "   GRID VIEW (D-09, P61; core and features P70, TD-229): " + names + ",\n"
            "   pasted unchanged by tools/grid_view_embed.py. Tier 3 component styles on\n"
            "   --color-* roles and D-16 tokens. Edit the module files and re-run the tool.\n"
            "   ============================================================ */")
    return head + "\n" + "\n".join(f"/* ---- {n} ---- */\n{t}" for n, t in parts("css")) + "\n"


def js_block():
    names = ", ".join(n for n, _ in parts("js"))
    head = ("// ============================================================\n"
            "// GRID VIEW MODULE (D-09, P61; core and features P70, TD-229): " + names + ",\n"
            "// pasted unchanged by tools/grid_view_embed.py. The core defines window.SRETGrid;\n"
            "// each feature registers itself with it. No app global is read. The app's\n"
            "// setup() call and adapters (openGridView) live beside the Workspace code.\n"
            "// ============================================================")
    return head + "\n" + "\n".join(f"// ---- {n} ----\n{t}" for n, t in parts("js")) + "\n" + JS_END


def rebuild(src):
    a = src.index(CSS_START)
    b = src.index("</style>", a)
    if src.count(CSS_START) != 1:
        sys.exit("Expected one GRID VIEW CSS banner.")
    src = src[:a] + css_block() + src[b:]
    c = src.index(JS_START)
    d = src.index(JS_END, c) + len(JS_END)
    if src.count(JS_START) != 1 or src.count(JS_END) != 1:
        sys.exit("Expected one GRID VIEW MODULE banner and one end marker.")
    return src[:c] + js_block() + src[d:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    for _, t in parts("js"):
        if "</script" in t.lower():
            sys.exit("A grid file contains </script.")
    src = APP.read_text(encoding="utf-8")
    out = rebuild(src)
    if a.check:
        if out != src:
            print("STALE: the app's grid blocks differ from the module files. Run tools/grid_view_embed.py.")
            return 1
        print("The app's grid blocks are the module files, pasted.")
        return 0
    APP.write_text(out, encoding="utf-8")
    print(f"Pasted {', '.join(['core'] + APP_FEATURES)} into {APP.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
