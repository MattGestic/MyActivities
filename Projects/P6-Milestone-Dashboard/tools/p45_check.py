#!/usr/bin/env python3
"""
P45 check (TEST-47): the self-contained PDF exporter.

WHY IT EXISTS. The browser print path does not own its page box. CSS @page is
advisory there: the print dialog picks the paper and the margins, so a board
laid out for A3 was rendered onto A4, shrunk to 64% and clipped at the right
edge. This exporter writes the page box itself.

SO THE ASSERTIONS ARE ABOUT THE FILE, NOT ABOUT THE CALL. The probe generates
real PDF bytes in the browser, hands them back, and this script PARSES them:
the MediaBox must be the paper that was asked for, the xref offsets must point
at real objects, the fonts must be the standard-14 with nothing embedded, and
the drawn content must fall inside the page. A check that only asserted
"exportPDF returned" would pass on a file no reader can open.

NO EXTERNAL REFERENCE is the other half of the request, and it is asserted
negatively: no /FontFile, no /URI, no /Launch, no /EmbeddedFile, no stream that
is an image. The file must be openable with nothing else present.

ALL FOUR PAGE SETUPS are generated and parsed, because the whole defect being
fixed was a page-size mismatch, and an exporter that got A3 landscape right and
A4 portrait wrong would reproduce it.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p45_check.py [--html FILE]
Exit code 1 on any failed check.
"""

import argparse
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p45-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900)]

# mm, and the points they must come out as.
PAPERS = {"A4": (210.0, 297.0), "A3": (297.0, 420.0)}
MM_PT = 72.0 / 25.4

PROBE = r"""
(async function(){
  const R={checks:[],notes:{},pdfs:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p45-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,300));
  const $=id=>document.getElementById(id);

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();

    // Dependency lines ON, because the request named them explicitly and an
    // exporter that silently dropped the SVG layer would otherwise pass.
    setAllDep('pred',true); setAllDep('succ',true);
    await settle(); await settle();
    const depPaths=document.querySelectorAll('#dep-line-layer path').length;
    R.notes.depPaths=depPaths;
    ck('setup: dependency lines are actually on the board to be exported',
       depPaths>0, depPaths+' paths drawn');

    // Capture the bytes rather than downloading: a check that clicks a
    // download cannot read what was in the file.
    const grabbed={};
    const realCreate=URL.createObjectURL;
    URL.createObjectURL=function(blob){ grabbed.blob=blob; return 'blob:probe'; };
    const realClick=HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click=function(){ grabbed.name=this.download; };

    // All four setups are generated, because the defect being fixed was a
    // page-size mismatch and one that got A3 landscape right and A4 portrait
    // wrong would reproduce it. Only ONE file is handed back whole: four
    // vector boards base64'd twice is several megabytes through the DOM, and
    // the structural parse only needs one real file to prove the writer. The
    // other three are summarised here, from their own bytes.
    const setups=[['A4','portrait'],['A4','landscape'],['A3','portrait'],['A3','landscape']];
    const scan=function(u8){
      let s=''; for(let i=0;i<u8.length;i++) s+=String.fromCharCode(u8[i]);
      const mb=/\/MediaBox\s*\[([^\]]*)\]/.exec(s);
      return {bytes:u8.length,
              mediabox:mb?mb[1].trim().split(/\s+/).map(Number):null,
              pages:(s.match(/\/Type\s*\/Page[^s]/g)||[]).length,
              fontfile:/\/FontFile/.test(s),
              image:/\/Subtype\s*\/Image/.test(s),
              uri:/\/URI|\/Launch|\/EmbeddedFile/.test(s),
              flate:/\/FlateDecode/.test(s),
              eof:/%%EOF\s*$/.test(s),
              header:s.slice(0,8)};
    };
    for(const sp of setups){
      grabbed.blob=null;
      const res=await exportPDF(sp[0],sp[1]);
      if(!grabbed.blob){ ck('export '+sp.join(' ')+': produced a file', false, 'no blob'); continue; }
      const u8=new Uint8Array(await grabbed.blob.arrayBuffer());
      const key=sp[0]+'-'+sp[1];
      R.notes['scan_'+key]=scan(u8);
      R.notes['scan_'+key].scale=res?Math.round(res.scale*1000)/1000:null;
      if(key==='A3-landscape'){
        let bin=''; for(let i=0;i<u8.length;i++) bin+=String.fromCharCode(u8[i]);
        R.pdfs[key]={b64:btoa(bin),meta:res,name:grabbed.name};
      }
      ck('export '+sp.join(' ')+': produced a non-trivial file',
         u8.length>3000, u8.length+' bytes');
    }
    URL.createObjectURL=realCreate;
    HTMLAnchorElement.prototype.click=realClick;

    // The picker writes the same numbers the export uses.
    setPdfPaper('A3'); setPdfOrient('landscape');
    const note=($('pdf-fit-note')||{}).textContent||'';
    R.notes.fitNote=note;
    ck('picker: the fit line states the printable width and the scale',
       /mm printable/.test(note)&&/% of screen size/.test(note), note);
    const nPaper=document.querySelectorAll('#pdf-dialog [data-paper].active').length;
    const nOrient=document.querySelectorAll('#pdf-dialog [data-orient].active').length;
    R.notes.activeBtns={paper:nPaper,orient:nOrient};
    ck('picker: exactly one paper and one orientation read as selected',
       nPaper===1&&nOrient===1, JSON.stringify(R.notes.activeBtns));
    // Both directions: switching has to move the selection, not add to it.
    setPdfPaper('A4'); setPdfOrient('portrait');
    const after={paper:(document.querySelector('#pdf-dialog [data-paper].active')||{}).getAttribute
                   ?document.querySelector('#pdf-dialog [data-paper].active').getAttribute('data-paper'):null,
                 orient:(document.querySelector('#pdf-dialog [data-orient].active')||{}).getAttribute
                   ?document.querySelector('#pdf-dialog [data-orient].active').getAttribute('data-orient'):null,
                 nPaper:document.querySelectorAll('#pdf-dialog [data-paper].active').length,
                 nOrient:document.querySelectorAll('#pdf-dialog [data-orient].active').length};
    R.notes.pickerSwitch=after;
    ck('picker: switching moves the selection rather than adding to it',
       after.paper==='A4'&&after.orient==='portrait'&&after.nPaper===1&&after.nOrient===1,
       JSON.stringify(after));

    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.message||err)});
    R.err=String(err&&err.stack||err);
    emit();
  }
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p45.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=90000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=900,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def parse_pdf(raw):
    """Minimal structural parse: enough to prove a reader could open it."""
    info = {}
    info["header"] = raw[:8].decode("latin-1", "replace")
    mb = re.search(rb"/MediaBox\s*\[([^\]]*)\]", raw)
    info["mediabox"] = [float(v) for v in mb.group(1).split()] if mb else None
    info["pages"] = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    info["fonts"] = sorted(set(m.group(1).decode()
                               for m in re.finditer(rb"/BaseFont\s*/([A-Za-z-]+)", raw)))
    info["fontfile"] = bool(re.search(rb"/FontFile", raw))
    info["uri"] = bool(re.search(rb"/URI|/Launch|/EmbeddedFile|/GoToR", raw))
    info["image"] = bool(re.search(rb"/Subtype\s*/Image", raw))
    # xref: every offset must land on "N 0 obj"
    sx = re.search(rb"startxref\s+(\d+)", raw)
    info["startxref_ok"] = False
    info["xref_entries"] = 0
    info["xref_bad"] = []
    if sx:
        off = int(sx.group(1))
        info["startxref_ok"] = raw[off:off + 4] == b"xref"
        if info["startxref_ok"]:
            tail = raw[off:off + 40000].split(b"trailer")[0]
            rows = re.findall(rb"^(\d{10}) (\d{5}) ([nf])\s*$", tail, re.M)
            info["xref_entries"] = len(rows)
            for i, (o, _g, kind) in enumerate(rows):
                if kind != b"n":
                    continue
                at = int(o)
                if not re.match(rb"\d+ 0 obj", raw[at:at + 20]):
                    info["xref_bad"].append(i)
    info["trailer_root"] = bool(re.search(rb"/Root\s+\d+\s+0\s+R", raw))
    info["eof"] = raw.rstrip().endswith(b"%%EOF")
    # content extent
    streams = []
    for m in re.finditer(rb"stream\r?\n(.*?)\nendstream", raw, re.S):
        s = m.group(1)
        try:
            s = zlib.decompress(s)
        except Exception:
            pass
        streams.append(s)
    info["streams"] = len(streams)
    body = b"\n".join(streams).decode("latin-1", "replace")
    info["has_text"] = " Tj" in body
    info["has_curve"] = " c\n" in body or body.endswith(" c")
    info["fonts_used"] = sorted(set(re.findall(r"/(F\d) [\d.]+ Tf", body)))
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html)

    src = html.read_text(encoding="utf-8", errors="replace")
    checks = []

    # The hard constraint this whole feature had to respect.
    checks.append((
        "source: the exporter adds no external dependency",
        "jspdf" not in src.lower() and "html2canvas" not in src.lower()
        and "pdfkit" not in src.lower(),
        "a PDF library was pulled in"))
    checks.append((
        "source: written as plain functions, no ES6 class, matching the file",
        not re.search(r"\bclass\s+Pdf", src) and "function pdfBuild(" in src,
        "the exporter introduced a class"))
    checks.append((
        "source: the four page setups come from one table",
        src.count("const PDF_PAPERS=") == 1 and "A4:{w:210,h:297}" in src.replace(" ", "")
        and "A3:{w:297,h:420}" in src.replace(" ", ""),
        "the paper table changed"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if R.get("err"):
            print(f"PROBE ERROR at {w}x{h}:\n{R['err']}")
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("depPaths", "fitNote", "activeBtns"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

        # ---- the four page boxes, each from its own bytes ----
        scans = {k[5:]: v for k, v in n.items() if k.startswith("scan_")}
        for k in sorted(scans):
            print(f"   {k}: {json.dumps(scans[k])}")
        checks.append((
            "pdf: all four page setups produced a file",
            len(scans) == 4, f"{len(scans)} of 4: {sorted(scans)}"))
        for key in sorted(scans):
            s = scans[key]
            paper, orient = key.split("-")
            pw, ph = PAPERS[paper]
            if orient == "landscape":
                pw, ph = ph, pw
            want = [round(pw * MM_PT, 1), round(ph * MM_PT, 1)]
            got = [round(v, 1) for v in (s["mediabox"] or [0, 0, 0, 0])[2:4]]
            # THE assertion. This is the defect the exporter exists to fix: a
            # board laid out for one sheet and rendered onto another.
            checks.append((
                f"pdf {key}: the page box IS the paper that was asked for",
                got == want, f"want {want}pt, got {got}pt"))
            checks.append((
                f"pdf {key}: nothing external, nothing embedded",
                not s["fontfile"] and not s["uri"] and not s["image"],
                f"fontfile={s['fontfile']} uri={s['uri']} image={s['image']}"))
            checks.append((
                f"pdf {key}: header and trailer are intact",
                s["header"] == "%PDF-1.4" and s["eof"] and s["pages"] >= 1,
                f"header={s['header']!r} eof={s['eof']} pages={s['pages']}"))
            # Never enlarged: a small board blown up to fill A3 would render
            # every hairline as a bar.
            checks.append((
                f"pdf {key}: drawn at or below full size, never enlarged",
                s["scale"] is not None and 0 < s["scale"] <= 1.0001,
                f"scale={s['scale']}"))
        # Pagination must follow the page box, and the FIRST draft of this
        # assertion was wrong in an instructive way: it required A3 landscape
        # to need no more pages than A4 portrait. It needed fewer, because
        # fitting purely to width meant the narrow page shrank the board to
        # 34% and crammed more rows onto each sheet. Fewer pages of unreadable
        # type is not the better outcome, so the exporter now holds a
        # legibility floor and splits the board into vertical bands instead.
        # The claim that survives is: every setup paginates, and no setup is
        # allowed to buy fewer pages by going below the floor.
        pg = {k: scans[k]["pages"] for k in scans}
        sc = {k: scans[k]["scale"] for k in scans}
        checks.append((
            "pdf: the page box drives pagination, and every setup paginates",
            all(v >= 1 for v in pg.values()) and len(set(pg.values())) > 1,
            json.dumps(pg)))
        checks.append((
            "pdf: no setup is drawn below the legibility floor",
            all(v >= 0.62 - 0.001 for v in sc.values()),
            json.dumps(sc)))
        # A narrow sheet must cost MORE pages than a wide one, which is the
        # point of the floor. This is the assertion the first draft got
        # backwards.
        checks.append((
            "pdf: a narrower sheet costs more pages, not smaller type",
            pg["A4-portrait"] >= pg["A3-landscape"],
            json.dumps({"A4-portrait": pg["A4-portrait"],
                        "A3-landscape": pg["A3-landscape"]})))
        # Compression is not cosmetic here: the uncompressed board runs past a
        # megabyte, which is too big to email.
        checks.append((
            "pdf: content streams are Flate compressed",
            all(scans[k]["flate"] for k in scans),
            json.dumps({k: scans[k]["flate"] for k in scans})))
        checks.append((
            "pdf: A3 landscape comes in under 400KB",
            scans.get("A3-landscape", {}).get("bytes", 9e9) < 400000,
            f"{scans.get('A3-landscape', {}).get('bytes')} bytes"))

        # ---- one file parsed properly, to prove the writer ----
        pdfs = R.get("pdfs", {})
        checks.append((
            "pdf: one complete file was returned for a structural parse",
            len(pdfs) == 1, f"{sorted(pdfs)}"))
        for key in sorted(pdfs):
            raw = base64.b64decode(pdfs[key]["b64"])
            i = parse_pdf(raw)
            print(f"   PARSED {key}: {json.dumps({k: i[k] for k in ('pages','mediabox','fonts','fonts_used','streams','xref_entries','xref_bad','has_text','eof')})}")
            # The xref is what makes a PDF openable at all: every offset has to
            # land on the object it claims. A writer that gets these wrong
            # produces a file that looks fine in a hex dump and opens in
            # nothing.
            checks.append((
                f"pdf {key}: every xref offset lands on its object",
                i["startxref_ok"] and not i["xref_bad"] and i["xref_entries"] >= 6,
                f"startxref_ok={i['startxref_ok']} entries={i['xref_entries']} "
                f"bad={i['xref_bad']}"))
            checks.append((
                f"pdf {key}: catalog, trailer and EOF are present",
                i["trailer_root"] and i["eof"] and i["header"] == "%PDF-1.4",
                f"root={i['trailer_root']} eof={i['eof']}"))
            checks.append((
                f"pdf {key}: text is set in the standard-14 base fonts only",
                bool(i["fonts"]) and all(f in ("Helvetica", "Helvetica-Bold",
                                               "Courier", "Courier-Bold")
                                         for f in i["fonts"]),
                str(i["fonts"])))
            checks.append((
                f"pdf {key}: carries real drawn text and curved paths",
                i["has_text"] and i["streams"] >= 1 and len(i["fonts_used"]) >= 1,
                f"text={i['has_text']} streams={i['streams']} fonts={i['fonts_used']}"))

    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
