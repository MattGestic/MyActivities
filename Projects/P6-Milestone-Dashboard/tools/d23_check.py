#!/usr/bin/env python3
"""
D-23 / TD-216 check: SheetJS is embedded, never fetched.

Unlike the import checks, which stub XLSX at the app's boundary, this one
uses the REAL embedded library, with the browser's host resolver pointed at
nothing, so any network request would fail and be counted.

Source assertions:
  - one <script id="vendor-sheetjs"> block, the last element inside <body>
  - its payload is vendor/sheetjs/xlsx.mini.min.js (sha256 in SOURCE.md)
    changed only by the documented \x3C escape of six HTML tag literals, so
    the page holds one </body> and every tool's inject-before-it stays valid
  - the Apache-2.0 licence text sits in the comment before it
  - no cdnjs / cdn.sheetjs.com URL and no script injection left in ensureXLSX
  - the version grep still returns 1

Runtime assertions (headless Chromium, no network):
  - XLSX is defined at load, version 0.20.3, and ensureXLSX() resolves
  - the reference P6 export parses through Parse.workbook() to its known
    header and data-row count, from the real bytes
  - a workbook written with the embedded library (the export path) reads back
  - choosing a legacy .xls file gives the plain-language message, not a crash
  - the page made zero network requests (Resource Timing, http/https only)

Usage:
  python3 tools/d23_check.py [--html FILE]
Exit code 1 if any assertion fails.
"""

import argparse
import base64
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
VENDOR = ROOT / "vendor" / "sheetjs"
REF = ROOT / "data" / "schedules" / "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"
TAGS = ["</body>", "<body>", "</head>", "<head>", "</html>", "<html>"]
OUT_RE = re.compile(r'<pre id="d23-out">(.*?)</pre>', re.S)

PROBE = r"""
(function(){
  const R={checks:[]};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='d23-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const b64ToBytes=b=>{ const s=atob(b); const u=new Uint8Array(s.length); for(let i=0;i<s.length;i++) u[i]=s.charCodeAt(i); return u; };
  window.addEventListener('load',function(){ setTimeout(async function(){
   try{
    ck('XLSX is defined at load, from the embedded block', typeof XLSX!=='undefined'&&typeof XLSX.read==='function');
    ck('it is SheetJS 0.20.3', XLSX&&XLSX.version==='0.20.3', XLSX&&XLSX.version);
    let ok=false; try{ await ensureXLSX(); ok=true; }catch(e){}
    ck('ensureXLSX() resolves without loading anything', ok);
    ck('no <script src> anywhere in the document',
       !document.querySelector('script[src]'), (document.querySelector('script[src]')||{}).src);

    // The reference export, through the app's own workbook parser.
    const parsed=Parse.workbook(b64ToBytes(REF_B64));
    ck('the reference export parses to its data rows', parsed.rows.length===REF_ROWS, parsed.rows.length+' vs '+REF_ROWS);
    ck('with its header row found (score >= 2)', parsed.headerScore>=2, parsed.headerScore);
    ck('and the Activity ID column among the headers',
       parsed.headers.some(h=>/activity\s*id/i.test(h)), parsed.headers.slice(0,6).join('|'));

    // The export path: write with the embedded library, read it back.
    const wb=XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet([['ID','Remark'],['SNIP-101','Tie-in revised'],['SNIP-115',42]]),'Remarks');
    const out=XLSX.write(wb,{bookType:'xlsx',type:'array'});
    const back=XLSX.utils.sheet_to_json(XLSX.read(out,{type:'array'}).Sheets.Remarks,{header:1,raw:true});
    ck('a workbook written by the embedded library reads back unchanged',
       JSON.stringify(back)===JSON.stringify([['ID','Remark'],['SNIP-101','Tie-in revised'],['SNIP-115',42]]), JSON.stringify(back));

    // A legacy .xls chosen in the import: plain message, no parse attempt.
    const input=document.getElementById('sched-file');
    const dt=new DataTransfer(); dt.items.add(new File([new Uint8Array([0xD0,0xCF,0x11,0xE0])],'old-p6-export.xls'));
    input.files=dt.files; handleFile(input);
    await new Promise(r=>setTimeout(r,300));
    const err=document.getElementById('import-error-wrap');
    const txt=err?err.textContent:'';
    ck('a legacy .xls gets the plain-language message', /Excel 97-2003/.test(txt)&&/\.xlsx or CSV/.test(txt), txt.slice(0,160));

    // The same content renamed .xlsx reaches the parser and still gets it.
    const dt2=new DataTransfer(); dt2.items.add(new File([b64ToBytes(XLS_B64)],'renamed.xlsx'));
    input.files=dt2.files; handleFile(input);
    await new Promise(r=>setTimeout(r,800));
    for(let i=0;i<20&&!/Excel 97-2003/.test((document.getElementById('import-error-wrap')||{}).textContent||'');i++) await new Promise(r=>setTimeout(r,250));
    const txt2=(document.getElementById('import-error-wrap')||{}).textContent||'';
    ck('a legacy workbook renamed .xlsx gets the same message', /Excel 97-2003/.test(txt2), txt2.slice(0,160)+' | status: '+((document.getElementById('ingest-status')||{}).textContent||''));

    const net=performance.getEntriesByType('resource').map(e=>e.name).filter(u=>/^https?:/i.test(u));
    ck('the page made zero network requests', net.length===0, net.join(', '));
   }catch(e){ ck('probe ran without throwing', false, e&&e.stack||e); }
   emit();
  },800); });
})();
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks = []

    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # ---- source ----
    lib = (VENDOR / "xlsx.mini.min.js").read_text(encoding="utf-8")
    lib_sha = hashlib.sha256((VENDOR / "xlsx.mini.min.js").read_bytes()).hexdigest()
    ck("SOURCE.md records the vendored file's sha256",
       lib_sha in (VENDOR / "SOURCE.md").read_text(encoding="utf-8"), lib_sha)
    blocks = re.findall(r'<script id="vendor-sheetjs">(.*?)</script>', src, re.S)
    ck("exactly one vendor-sheetjs block", len(blocks) == 1, len(blocks))
    if blocks:
        body = blocks[0]
        # The one documented change: the six HTML tag literals in the library's
        # table-export template have their "<" written as \x3C (SOURCE.md).
        emb = lib
        for t in TAGS:
            emb = emb.replace(t, "\\x3C" + t[1:])
        ck("the block carries the library, changed only by the documented \\x3C escapes",
           emb.rstrip() in body and emb.count("\\x3C") - lib.count("\\x3C") == len(TAGS))
        lic_head = (VENDOR / "LICENSE").read_text(encoding="utf-8").strip().splitlines()[0].strip()
        ck("the Apache-2.0 licence is in the comment before it",
           lic_head in body.split(lib[:40])[0] and "Apache License" in body.split(lib[:40])[0])
    for t in ("</body>", "<head>", "</head>", "</html>"):
        ck(f"the page holds exactly one {t} (tools inject before it)", src.count(t) == 1, src.count(t))
    tail = src[src.rfind("</script>") + len("</script>"):]
    ck("the block is the last element inside <body>",
       src.rfind('<script id="vendor-sheetjs">') > src.rfind('id="app-script"')
       and tail.strip().startswith("</body>"), tail.strip()[:30])
    ck("no CDN URL left in the file", not re.search(r"cdnjs|cdn\.sheetjs|jsdelivr|unpkg", src))
    m = re.search(r"function ensureXLSX\(\)\{(.*?)\n\}", src, re.S)
    ck("ensureXLSX() no longer injects a script",
       m is not None and "createElement('script')" not in m.group(1) and ".src" not in m.group(1))
    ck("version grep returns 1", len(re.findall(r"3\.[0-9]*\.[0-9]*-P", src)) == 1)

    # ---- runtime ----
    # The reference sample's row count, as recorded in docs/04-architecture.md.
    ref_rows = 192
    # The renamed-legacy case: a real Excel 97-2003 (BIFF8) workbook, written
    # once by the full 0.18.5 build into tools/fixtures/, which mini cannot parse.
    xls_bytes = (ROOT / "tools" / "fixtures" / "legacy_excel97.xls").read_bytes()
    consts = ("const REF_B64=" + json.dumps(base64.b64encode(REF.read_bytes()).decode()) + ";"
              "const REF_ROWS=" + str(ref_rows) + ";"
              "const XLS_B64=" + json.dumps(base64.b64encode(xls_bytes).decode()) + ";")
    html = src.replace("</body>", f"<script>{consts}\n{PROBE}</script>\n</body>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    out = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                          "--host-resolver-rules=MAP * ~NOTFOUND",
                          "--window-size=1440,900", "--virtual-time-budget=60000",
                          "--dump-dom", "file://" + path],
                         capture_output=True, text=True, timeout=240).stdout
    mm = OUT_RE.search(out)
    if not mm:
        ck("the runtime probe produced output", False)
    else:
        for c in json.loads(base64.b64decode(mm.group(1)).decode("utf-8"))["checks"]:
            ck(c["name"], c["pass"], c["detail"])

    fails = 0
    for name, ok, detail in checks:
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  ({detail})"))
    print(f"\n{len(checks) - fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
