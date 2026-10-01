#!/usr/bin/env python3
"""
p71_check: a saved copy (publishDashboard) keeps the embedded libraries, and
a copy saved from a fresh load carries empty annotation state (P71,
2026-10-01). P74 (TD-239): the app ships with no schedule, so a fresh load is
the empty state and this check runs WITHOUT the reference fixture
(SRET_NO_FIXTURE on its launches, not a marker in the page, which publishing
would carry into the saved copy); its saved copy is the empty dashboard.

Stage 1: the app loads as it ships, in a fresh profile: the empty state, no
  schedule. Every annotation store is empty; a foreign script is injected into
  the live DOM; publishDashboard() runs and its output is captured.
Stage 2: assertions on the saved file's source: app-script, vendor-sheetjs,
  vendor-slickgrid and vendor-slickgrid-css present once each, the foreign
  script gone, one published-state block, one </body>, one version literal.
Stage 3: the saved file opens in a fresh profile: XLSX and Slick are defined,
  the board builds the same rows and milestones, every annotation store is
  still empty, and it reports itself as a published copy.

Usage: python3 tools/p71_check.py [--html FILE] [--save DIR]
  --save DIR also writes the saved copy into DIR.
Exit code 1 on any failed check.
"""
import argparse, base64, json, os, pathlib, re, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

STORES = r"""
  const n=v=>v==null?null:(Array.isArray(v)?v.length:Object.keys(v).length);
  const st={entries:n(ENTRIES),comments:n(MS_COMMENTS),health:n(MS_HEALTH_OVERRIDE),progress:n(MS_PROGRESS_OVERRIDE),
    fields:n(MS_FIELD_OVERRIDE),notes:n(NOTES),userMs:n(USER_MILESTONES),shortTitles:n(MS_SHORT_TITLES),
    depComments:(typeof DEP_COMMENTS!=='undefined')?n(DEP_COMMENTS):0};
  const board={tasks:TASKS.length,milestones:MILESTONES.length,markers:document.querySelectorAll('#tbody .m-wrap').length,
    version:APP_VERSION,published:!!window.__PUBLISHED_STATE__,xlsx:typeof XLSX,slick:typeof Slick,
    empty:document.body.classList.contains('is-empty')&&!document.getElementById('empty-state').hidden};
"""

PUBLISH = r"""<script>
(function(){
 const cap={};
 const OB=window.Blob;
 window.Blob=function(parts,opts){ if(opts&&opts.type==='text/html') cap.text=parts.join(''); return new OB(parts,opts); };
 window.Blob.prototype=OB.prototype;
 const oc=HTMLAnchorElement.prototype.click;
 HTMLAnchorElement.prototype.click=function(){ if(this.download){ cap.name=this.download; return; } return oc.call(this); };
 function out(o){ const e=document.createElement('pre'); e.id='__out'; e.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(o)))); document.body.appendChild(e); }
 setTimeout(function(){
  try{
""" + STORES + r"""
  const intr=document.createElement('script'); intr.id='intruder'; intr.textContent='window.__INTRUDER__=1;'; document.body.appendChild(intr);
  // The probe's own script is not part of the file either; it is dropped too.
  publishDashboard();
  out({st:st,board:board,name:cap.name,html:cap.text||''});
  }catch(e){ out({err:String(e&&e.stack||e)}); }
 },3000);
})();
</script></body>"""

LOAD = r"""<script>
(function(){
 function out(o){ const e=document.createElement('pre'); e.id='__out'; e.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(o)))); document.body.appendChild(e); }
 setTimeout(function(){
  try{
""" + STORES + r"""
  out({st:st,board:board,intruder:!!window.__INTRUDER__});
  }catch(e){ out({err:String(e&&e.stack||e)}); }
 },3000);
})();
</script></body>"""


def run(page, probe):
    i = page.rindex("</body>")
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p.html"
        f.write_text(page[:i] + probe + page[i + 7:], encoding="utf-8")
        p = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", f"--user-data-dir={td}/prof",
                            "--virtual-time-budget=20000", "--dump-dom", f.as_uri()],
                           capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, SRET_NO_FIXTURE="1"))
    m = re.search(r'<pre id="__out">(.*?)</pre>', p.stdout, re.S)
    if not m:
        sys.exit("Probe output not found.\n" + p.stderr[-2000:])
    R = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    if "err" in R:
        sys.exit("Probe threw: " + R["err"])
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    ap.add_argument("--save")
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    checks = []
    ck = lambda n, p, d="": checks.append((n, bool(p), str(d)))

    R = run(src, PUBLISH)
    empty = all(v == 0 for v in R["st"].values())
    ck("fresh load: every annotation store is empty", empty, json.dumps(R["st"]))
    ck("fresh load: opens on the empty state, with no schedule",
       R["board"]["empty"] is True and R["board"]["tasks"] == 0 and R["board"]["milestones"] == 0,
       f'{R["board"]["tasks"]}/{R["board"]["milestones"]}')
    ck("fresh load: not a published copy", R["board"]["published"] is False)
    ck("fresh load: the libraries are live", R["board"]["xlsx"] == "object" and R["board"]["slick"] == "object",
       R["board"]["xlsx"] + " " + R["board"]["slick"])
    out = R["html"]
    ck("publish: a file was produced", len(out) > 100000 and R["name"], f'{R["name"]} {len(out)}')
    for sid in ["app-script", "vendor-sheetjs", "vendor-slickgrid", "vendor-slickgrid-css", "published-state"]:
        ck(f"saved file: one #{sid}", out.count(f'id="{sid}"') == 1, out.count(f'id="{sid}"'))
    ck("saved file: the injected foreign script is dropped", 'id="intruder"' not in out and "__INTRUDER__" not in out)
    ck("saved file: the check's own probe is dropped", "__out" not in out.split("published-state", 1)[0][-200:] and "HTMLAnchorElement.prototype.click" not in out)
    ck("saved file: exactly one </body>", out.count("</body>") == 1, out.count("</body>"))
    ck("saved file: one APP_VERSION literal, the build that saved it",
       len(re.findall(r"const APP_VERSION='3\.[0-9]+\.[0-9]+-P[0-9]+'", out)) == 1 and R["board"]["version"] in out)
    ck("saved file: vendor scripts keep their order (slickgrid before app, sheetjs after)",
       out.index('id="vendor-slickgrid"') < out.index('id="app-script"') < out.index('id="vendor-sheetjs"'))
    m = re.search(r"window.__PUBLISHED_STATE__=(.*?);</script>", out, re.S)
    S = json.loads(m.group(1)) if m else {}
    ent = S.get("entries", [])
    ck("saved state: entries empty", isinstance(ent, list) and len(ent) == 0, len(ent) if isinstance(ent, list) else ent)
    for k in ["milestoneComments", "milestoneHealthOverrides", "milestoneProgressOverrides", "milestoneFieldOverrides", "notes", "userMilestones"]:
        v = S.get(k)
        ck(f"saved state: {k} empty or absent", not v, json.dumps(v)[:80] if v else "")

    R2 = run(out, LOAD)
    ck("saved copy opens: reports itself as published", R2["board"]["published"] is True)
    ck("saved copy opens: SheetJS and SlickGrid are defined", R2["board"]["xlsx"] == "object" and R2["board"]["slick"] == "object",
       R2["board"]["xlsx"] + " " + R2["board"]["slick"])
    ck("saved copy opens: same rows and milestones as the fresh load",
       R2["board"]["tasks"] == R["board"]["tasks"] and R2["board"]["milestones"] == R["board"]["milestones"],
       f'{R2["board"]["tasks"]}/{R2["board"]["milestones"]} vs {R["board"]["tasks"]}/{R["board"]["milestones"]}')
    ck("saved copy opens: on the empty state, like the fresh load, with no markers",
       R2["board"]["empty"] is True and R2["board"]["markers"] == 0 and R2["board"]["markers"] == R["board"]["markers"],
       f'{R2["board"]["markers"]} vs {R["board"]["markers"]}')
    ck("saved copy opens: every annotation store still empty", all(v == 0 for v in R2["st"].values()), json.dumps(R2["st"]))
    ck("saved copy opens: the foreign script never ran", R2["intruder"] is False)

    if a.save:
        d = pathlib.Path(a.save); d.mkdir(parents=True, exist_ok=True)
        (d / R["name"]).write_text(out, encoding="utf-8")
        print("saved", d / R["name"])
    fails = 0
    for n, ok, d in checks:
        fails += not ok
        print(("  ok   " if ok else "  FAIL ") + n + (f"   [{d}]" if d else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
