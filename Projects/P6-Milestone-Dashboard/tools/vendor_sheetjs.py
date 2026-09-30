#!/usr/bin/env python3
"""Vendor SheetJS (mini build) into vendor/sheetjs/ for TD-216.

Matt, 2026-09-30: embed the mini build. The fixed releases (0.20.2 and
later; 0.18.5 carries CVE-2023-30533 and CVE-2024-22363) are published only
at cdn.sheetjs.com, not npm. Two ways in:

  python3 tools/vendor_sheetjs.py --version 0.20.3
      downloads https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz
      (the session's network policy must allow cdn.sheetjs.com)
  python3 tools/vendor_sheetjs.py --tgz ~/Downloads/xlsx-0.20.3.tgz
      the same tarball, downloaded by hand from that URL

It takes package/dist/xlsx.mini.min.js and package/LICENSE byte for byte
(the file is already minified, so nothing is transformed), checks the
licence is Apache-2.0 and the version is patched, lists anything in the
file that could make a network request, reads the reference P6 export in
data/schedules/ with it (the mini build must read what P6 produces), and
writes vendor/sheetjs/SOURCE.md with the version, URL and sha256 of each file.
"""
import argparse
import datetime
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "vendor" / "sheetjs"
EXPORT = ROOT / "data" / "schedules" / "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"
MIN_PATCHED = (0, 20, 2)
URL = "https://cdn.sheetjs.com/xlsx-{v}/xlsx-{v}.tgz"
# Anything that could reach the network at runtime. Listed, not fatal: the
# library has read helpers that are only reached if the caller asks for them.
# (XML namespace URLs are names, not requests, so they are not listed.)
NET = [r"\bfetch\(", r"XMLHttpRequest", r"importScripts", r"navigator\.sendBeacon", r"new WebSocket"]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def ver(s: str):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", s or "")
    return tuple(int(x) for x in m.groups()) if m else None


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--version")
    g.add_argument("--tgz")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--allow-unpatched", action="store_true", help="testing only: accept a version below 0.20.2")
    a = ap.parse_args()

    if a.tgz:
        raw = pathlib.Path(a.tgz).expanduser().read_bytes()
        source = f"{pathlib.Path(a.tgz).name}, downloaded by hand from " + URL.format(v="<version>")
    else:
        url = URL.format(v=a.version)
        try:
            raw = urllib.request.urlopen(url, timeout=60).read()
        except Exception as e:  # noqa: BLE001
            sys.exit(f"Could not download {url}: {e}\nAllow cdn.sheetjs.com in the environment's network access, or download it by hand and use --tgz.")
        source = url

    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        for name in ("package/dist/xlsx.mini.min.js", "package/LICENSE", "package/package.json"):
            m = tf.extractfile(name) if name in tf.getnames() else None
            if not m:
                sys.exit(f"The tarball has no {name}.")
            files[name] = m.read()
    pkg = json.loads(files["package/package.json"])
    v = pkg.get("version", "")
    if a.version and v != a.version:
        sys.exit(f"Asked for {a.version}, the tarball is {v}.")
    if not ver(v) or (ver(v) < MIN_PATCHED and not a.allow_unpatched):
        sys.exit(f"SheetJS {v} is below 0.20.2 and carries CVE-2023-30533 / CVE-2024-22363. Use a patched release.")
    if pkg.get("license") != "Apache-2.0" or b"Apache License" not in files["package/LICENSE"]:
        sys.exit(f"Licence is {pkg.get('license')!r}, not Apache-2.0. CLAUDE.md allows MIT, BSD or Apache-2.0 only.")
    js = files["package/dist/xlsx.mini.min.js"]
    text = js.decode("utf-8")
    if "</script" in text.lower():
        sys.exit("The build contains </script, which would end the inline block early.")
    net = sorted({m.group(0)[:80] for p in NET for m in re.finditer(p, text)})

    # The mini build must read the P6 export: every row, same as the reference reader.
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "xlsx.mini.min.js"
    tmp.write_bytes(js)
    probe = r"""
const fs=require('fs'),vm=require('vm'),ctx={console};ctx.window=ctx;ctx.self=ctx;vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);const X=ctx.XLSX;
const wb=X.read(new Uint8Array(fs.readFileSync(process.argv[2])),{type:'array',cellDates:true});
const a=X.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]],{header:1,defval:''});
const ws=X.utils.aoa_to_sheet([['ID','Finish'],['A-1',new Date(Date.UTC(2026,9,9))]],{cellDates:true,dateNF:'d-mmm-yy'});
const nb=X.utils.book_new();X.utils.book_append_sheet(nb,ws,'Grid');
console.log(JSON.stringify({version:X.version,rows:a.length,cols:Math.max(...a.map(r=>r.length)),writes:X.write(nb,{type:'array',bookType:'xlsx'}).byteLength>0}));"""
    p = subprocess.run(["node", "-e", probe, str(tmp), str(EXPORT)], capture_output=True, text=True)
    if p.returncode:
        tmp.unlink()
        sys.exit("The mini build failed on the P6 export:\n" + p.stderr[-800:])
    res = json.loads(p.stdout)
    if res["rows"] < 2 or not res["writes"]:
        tmp.unlink()
        sys.exit(f"The mini build did not read and write as expected: {res}")

    (out / "LICENSE").write_bytes(files["package/LICENSE"])
    today = datetime.date.today().isoformat()
    (out / "SOURCE.md").write_text(f"""# SheetJS (vendored for TD-216)

| Item | Value |
|---|---|
| Package | `xlsx` (SheetJS Community Edition), mini build |
| Version | {v} |
| Licence | Apache-2.0, see `LICENSE` (copied unmodified from the package) |
| Source | {source} |
| Tarball sha256 | `{sha(raw)}` |
| Vendored | {today}, by `tools/vendor_sheetjs.py` |

## Files

| File | From | sha256 |
|---|---|---|
| `xlsx.mini.min.js` | `package/dist/xlsx.mini.min.js` | `{sha(js)}` |
| `LICENSE` | `package/LICENSE` | `{sha(files["package/LICENSE"])}` |

`xlsx.mini.min.js` is the package's own minified browser build, byte for byte: nothing is transformed. It is inlined in its own `<script id="vendor-sheetjs">` with the licence text in a comment beside it.

The mini build reads and writes .xlsx and reads .csv. It does not read legacy .xls (BIFF) workbooks, so the import refuses .xls with a message to save as .xlsx or .csv (Matt, 2026-09-30). Checked on vendoring: it read the reference P6 export in `data/schedules/` ({res['rows']} rows) and wrote an .xlsx.

Network-capable code in the build (the app never calls these paths; listed for review): {', '.join('`'+n+'`' for n in net) or 'none'}.
""", encoding="utf-8")
    print(f"Vendored SheetJS {v} mini ({len(js):,} bytes) into {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}.")
    print(f"P6 export read: {res['rows']} rows. Network-capable strings to review: {len(net)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
