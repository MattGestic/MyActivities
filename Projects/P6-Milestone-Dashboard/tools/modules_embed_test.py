#!/usr/bin/env python3
"""Scenario test for tools/modules_embed.py (D-30). Static, no browser.

Runs the tool against a throwaway copy of src/ and tools/ in a temp folder,
so the real app and manifest are never touched, and proves each finding
fires on the edit that should cause it and clears after the right fix:

  1. the committed app is clean;
  2. a hand edit inside a module region in the app  -> TAMPERED, and --embed refuses;
  3. a module source edit without a version bump    -> STALE + UNVERSIONED;
     bump the version, --embed                       -> clean, marker carries the new version;
  4. --embed changes only the module's own region (bytes outside it identical);
  5. a module region deleted from the app            -> MISSING; --embed re-inserts it at its slot;
  6. --extract lifts app lines into a module unchanged; the app differs only by markers.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))
    if not ok:
        fails.append(name)


def main():
    with tempfile.TemporaryDirectory() as td:
        t = pathlib.Path(td)
        shutil.copytree(ROOT / "src", t / "src")
        (t / "tools").mkdir()
        shutil.copy(ROOT / "tools" / "modules_embed.py", t / "tools")
        app = t / "src" / "milestone-dashboard.html"
        man_p = t / "src" / "modules" / "MODULES.json"
        store = t / "src" / "modules" / "notes-store" / "notes-store.js"

        def run(*args):
            r = subprocess.run([sys.executable, str(t / "tools" / "modules_embed.py"), *args],
                               capture_output=True, text=True)
            return r.returncode, r.stdout + r.stderr

        rc, out = run("--check")
        ck("1. committed app is clean", rc == 0, out.strip())
        clean_app, clean_man, clean_store = app.read_text(), man_p.read_text(), store.read_text()

        # 2. Hand edit inside a pasted region.
        s = clean_app
        i = s.index("root.SRETEntries=api;")
        app.write_text(s[:i] + "/*hand edit*/" + s[i:])
        rc, out = run("--check")
        ck("2a. hand edit in the app -> TAMPERED", rc == 1 and "TAMPERED    notes-store js" in out, out.strip())
        rc, out = run("--embed", "notes-store")
        ck("2b. --embed refuses to overwrite it", rc != 0 and "Refusing to overwrite" in out, out.strip())
        app.write_text(clean_app)

        # 3. Source edit without, then with, a version bump.
        store.write_text(clean_store.replace("root.SRETEntries=api;", "root.SRETEntries=api; /*v-next*/"))
        rc, out = run("--check")
        ck("3a. source edit -> STALE", rc == 1 and "STALE       notes-store js" in out, out.strip())
        ck("3b. source edit, same version -> UNVERSIONED", "UNVERSIONED notes-store" in out, out.strip())
        man = json.loads(clean_man)
        next(m for m in man["modules"] if m["id"] == "notes-store")["version"] = "1.0.1"
        man_p.write_text(json.dumps(man, indent=2) + "\n")
        before = app.read_text()
        rc, out = run("--embed", "notes-store")
        after = app.read_text()
        ck("3c. bump + --embed -> clean", rc == 0, out.strip())
        ck("3d. the marker carries the new version", "// @module notes-store js 1.0.1 sha256=" in after)
        ck("3e. the new source text is in the app", "root.SRETEntries=api; /*v-next*/" in after)

        # 4. Only the module's own region changed.
        b0 = before.index("// @module notes-store js ")
        e0 = before.index("// @module notes-store js END")
        b1 = after.index("// @module notes-store js ")
        e1 = after.index("// @module notes-store js END")
        ck("4. bytes outside the region are identical", before[:b0] == after[:b1] and before[e0:] == after[e1:])
        app.write_text(clean_app)
        man_p.write_text(clean_man)
        store.write_text(clean_store)

        # 5. Region deleted -> MISSING -> re-inserted at its slot.
        s = clean_app
        a = s.index("// @module notes-history js ")
        e = s.index("// @module notes-history js END\n") + len("// @module notes-history js END\n")
        app.write_text(s[:a] + s[e:])
        rc, out = run("--check")
        ck("5a. deleted region -> MISSING", rc == 1 and "MISSING     notes-history js" in out, out.strip())
        rc, out = run("--embed", "notes-history")
        ck("5b. --embed re-inserts it at the slot and the app is clean again", rc == 0 and app.read_text() == clean_app,
           out.strip())

        # 6. --extract: a pure move.
        app.write_text(clean_app)
        man_p.write_text(clean_man)
        lines = clean_app.split("\n")
        k = next(n for n, l in enumerate(lines, 1) if l.startswith("const APP_VERSION="))
        rc, out = run("--extract", "pilot", "--js-lines", f"{k}-{k}", "--global", "")
        ext_app = app.read_text()
        body = (t / "src" / "modules" / "pilot" / "pilot.js").read_text()
        ck("6a. --extract writes the lifted lines unchanged", rc == 0 and body == lines[k - 1] + "\n", out.strip())
        stripped = "\n".join(l for l in ext_app.split("\n") if not re.match(r"// @module pilot js ", l))
        ck("6b. the app differs only by the two marker lines", stripped == clean_app)
        rc, out = run("--check")
        ck("6c. the app is clean after --extract", rc == 0, out.strip())

    print(f"\n{'FAILED: ' + ', '.join(fails) if fails else 'All modules_embed scenarios passed.'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
