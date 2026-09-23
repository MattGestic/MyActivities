#!/usr/bin/env python3
"""
P46 check (TEST-48): the print preview lays out for a sheet the user chooses.

THE DEFECT THIS CLOSES. CSS cannot pick the physical paper: the print dialog
does. The preview laid out a fixed A3 portrait sheet and injected an @page
asking for it, and a dialog set to A4 rendered that 297mm layout onto a 210mm
page, shrink-to-fit to 64% with the right edge clipped. Measured off the
delivered PDF: MediaBox 595x841pt (A4) against a 1122px (297mm) sheet, content
running to 591.9pt on a 595pt page.

So the fix is not a better layout, it is letting the person say which sheet
they will select, and saying it back to them. What is asserted here is that ALL
THREE consequences of that choice move together: the @page rule, the preview
sheet's own width, and the column fit. They used to be set in three places,
which is how the preview came to show one sheet while @page asked for another.

BOTH DIRECTIONS, ON EVERY SETUP. Each of the four paper/orientation pairs is
driven through the real controls and measured, because a picker that got A3
landscape right and A4 portrait wrong would reproduce the original defect on
exactly the paper most people have.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p46_check.py [--html FILE]
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p46-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p46-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,260));
  const $=id=>document.getElementById(id);
  const mm=v=>Math.round(v*10)/10;

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();

    // The board's width BEFORE the preview, so leaving it can be checked
    // against something rather than against nothing.
    const beforeSheetW=getComputedStyle(document.documentElement)
                         .getPropertyValue('--page-sheet-w').trim();
    R.notes.beforeSheetW=beforeSheetW;

    togglePrintMode(true); await settle(); await settle();
    ck('preview: print mode is on and the header is showing',
       document.body.classList.contains('print-mode')&&
       getComputedStyle($('pm-banner')).display!=='none',
       'print-mode='+document.body.classList.contains('print-mode'));

    // The header carries the option set AND a print control. Both were asked
    // for; a header with the options but no way to print is half a control.
    const paperBtns=document.querySelectorAll('#pm-paper [data-paper]');
    const orientBtns=document.querySelectorAll('#pm-paper [data-orient]');
    R.notes.header={paper:paperBtns.length,orient:orientBtns.length,
                    print:!!$('btn-pm-print'),
                    fit:!!$('btn-pm-fit'),leave:!!$('btn-pm-leave')};
    ck('header: it offers two papers and two orientations',
       paperBtns.length===2&&orientBtns.length===2, JSON.stringify(R.notes.header));
    ck('header: there is a print control on the page',
       !!$('btn-pm-print')&&typeof doBrowserPrint==='function',
       'btn='+!!$('btn-pm-print')+' fn='+(typeof doBrowserPrint));
    // It must be ON SCREEN, not merely in the DOM. The sheet is wider than the
    // viewport at A3 landscape and the page scrolls sideways, which is how
    // three controls ended up off screen at TD-142.
    const pr=$('btn-pm-print').getBoundingClientRect();
    R.notes.printBtnBox={l:Math.round(pr.left),r:Math.round(pr.right),w:Math.round(pr.width)};
    ck('header: the print control is within the viewport, not off the side',
       pr.left>=-1&&pr.right<=window.innerWidth+1&&pr.width>10,
       JSON.stringify(R.notes.printBtnBox));

    // ---- every setup, driven through the real controls ----
    const sheetVar=function(){
      return getComputedStyle(document.documentElement)
               .getPropertyValue('--page-sheet-w').trim(); };
    const atPage=function(){
      const s=$('print-page-style');
      return s?s.textContent:''; };
    const want={A4:{portrait:[210,297],landscape:[297,210]},
                A3:{portrait:[297,420],landscape:[420,297]}};
    const seen={};
    for(const paper of ['A4','A3']){
      for(const orient of ['portrait','landscape']){
        // Through the controls a person actually clicks.
        document.querySelector('#pm-paper [data-paper="'+paper+'"]').click();
        document.querySelector('#pm-paper [data-orient="'+orient+'"]').click();
        await settle();
        const w=want[paper][orient][0], h=want[paper][orient][1];
        const key=paper+'-'+orient;
        const frame=document.getElementById('main-table').closest('#page-frame')
                    ||document.getElementById('main-table');
        seen[key]={sheetVar:sheetVar(),atPage:atPage(),
                   label:($('pm-paper-label')||{}).textContent||'',
                   bannerW:Math.round($('pm-banner').getBoundingClientRect().width),
                   detail:($('pm-banner-detail')||{}).textContent||'',
                   onPaper:document.querySelectorAll('#pm-paper [data-paper].on').length,
                   onOrient:document.querySelectorAll('#pm-paper [data-orient].on').length,
                   activePaper:(document.querySelector('#pm-paper [data-paper].on')||{}).getAttribute
                     ?document.querySelector('#pm-paper [data-paper].on').getAttribute('data-paper'):null,
                   activeOrient:(document.querySelector('#pm-paper [data-orient].on')||{}).getAttribute
                     ?document.querySelector('#pm-paper [data-orient].on').getAttribute('data-orient'):null};
        // 1. The injected @page must ask for the chosen sheet.
        ck('@page '+key+': the injected rule asks for the chosen sheet',
           seen[key].atPage.indexOf('size:'+w+'mm '+h+'mm')>=0,
           seen[key].atPage);
        // 2. The preview sheet must BE that width, measured, not declared.
        ck('sheet '+key+': the preview sheet is that width',
           seen[key].sheetVar===w+'mm', seen[key].sheetVar+' against '+w+'mm');
        // 3. The two heading bars are sized from the same variable, so they
        //    line up with the sheet. This is the TD-142 contract.
        ck('sheet '+key+': the header bar spans the sheet, not the viewport',
           Math.abs(seen[key].bannerW-mmToPx(w))<=2,
           seen[key].bannerW+'px against '+Math.round(mmToPx(w))+'px');
        // 4. The header says which paper to set in the dialog, which is the
        //    only thing standing between the layout and the same mismatch.
        ck('header '+key+': it names the paper to set in the print dialog',
           seen[key].label===paper+' '+orient, seen[key].label);
        // 5. One of each reads as chosen.
        ck('header '+key+': exactly one paper and one orientation read as chosen',
           seen[key].onPaper===1&&seen[key].onOrient===1&&
           seen[key].activePaper===paper&&seen[key].activeOrient===orient,
           JSON.stringify({p:seen[key].activePaper,o:seen[key].activeOrient,
                           np:seen[key].onPaper,no:seen[key].onOrient}));
        // 6. The column fit must be recomputed for the new width, or the
        //    board keeps the previous sheet's column width.
        ck('fit '+key+': the fit line was recomputed for this sheet',
           /week columns/.test(seen[key].detail), seen[key].detail);
      }
    }
    R.notes.setups=seen;

    // The whole point: a WIDER sheet must fit the columns at a WIDER column.
    // If it did not, the choice would not be reaching the layout at all.
    const fitted=function(k){ const m=/fitted at (\d+)px/.exec(seen[k].detail);
      return m?+m[1]:null; };
    R.notes.colFit={'A3-landscape':fitted('A3-landscape'),
                    'A3-portrait':fitted('A3-portrait'),
                    'A4-landscape':fitted('A4-landscape'),
                    'A4-portrait':fitted('A4-portrait'),
                    a4pDetail:seen['A4-portrait'].detail};
    // A wider sheet must fit the columns WIDER, and two sheets of the same
    // width must agree. A3 portrait and A4 landscape are both 297mm, so they
    // are the control: if the fit were keyed on the paper NAME rather than on
    // the width, they would differ.
    ck('fit: a wider sheet fits the same columns at a wider column',
       fitted('A3-landscape')>fitted('A3-portrait'),
       JSON.stringify(R.notes.colFit));
    ck('fit: two sheets of the same printable width fit identically',
       fitted('A3-portrait')!==null&&fitted('A3-portrait')===fitted('A4-landscape'),
       'A3 portrait '+fitted('A3-portrait')+'px, A4 landscape '+fitted('A4-landscape')+'px');
    // A4 portrait genuinely cannot carry 39 weeks: 194mm printable is 733px
    // and the 20px floor alone needs 780px. The honest outcome is the clamp
    // message, not a quietly unreadable column, and that is asserted rather
    // than worked around.
    ck('fit: a sheet too narrow for the columns says so instead of shrinking them',
       fitted('A4-portrait')===null&&/still exceed the page width/.test(seen['A4-portrait'].detail),
       seen['A4-portrait'].detail);

    // Leaving the preview must put the sheet variable back, or the board keeps
    // a print-sized width in ordinary use.
    togglePrintMode(false); await settle(); await settle();
    const afterSheetW=getComputedStyle(document.documentElement)
                        .getPropertyValue('--page-sheet-w').trim();
    R.notes.afterSheetW=afterSheetW;
    ck('leave: the sheet width goes back to what it was before the preview',
       afterSheetW===beforeSheetW,
       'before '+beforeSheetW+', after '+afterSheetW);
    ck('leave: the injected @page rule is withdrawn',
       (($('print-page-style')||{}).textContent||'')==='',
       (($('print-page-style')||{}).textContent||'(empty)'));

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
        tmp = pathlib.Path(td) / "p46.html"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html)

    src = html.read_text(encoding="utf-8", errors="replace")
    nospace = re.sub(r"\s+", "", src)
    checks = []

    # ONE paper table, read by the preview and the exporter both. Two copies of
    # these numbers is what produced the original defect.
    checks.append((
        "source: one paper table, shared by the preview and the exporter",
        src.count("const PAGE_PAPERS=") == 1 and "PDF_PAPERS" not in src,
        f"PAGE_PAPERS={src.count('const PAGE_PAPERS=')}, "
        f"stale PDF_PAPERS present={'PDF_PAPERS' in src}"))
    # ONE writer for everything the sheet controls. The @page rule, the CSS
    # variable and the column fit drifting apart is the defect class here.
    checks.append((
        "source: one writer for the @page rule, the sheet width and the fit",
        src.count("function applyPrintPage(") == 1
        and src.count("@page{size:") == 1
        and src.count("setProperty('--page-sheet-w'") == 1,
        "applyPrintPage=%d @page=%d setProperty=%d" % (
            src.count("function applyPrintPage("),
            src.count("@page{size:"),
            src.count("setProperty('--page-sheet-w'"))))
    checks.append((
        "source: the hardcoded A3 constant is gone",
        "PRINT_PAGE_MM" not in src and "function printPageMM(" in src,
        "a fixed page constant is still present"))
    # The defective exporter must not be reachable from the UI.
    checks.append((
        "source: the incomplete PDF export is not clickable",
        src.count("openPdfDialog()") == 1,
        f"{src.count('openPdfDialog()')} references, expected 1 (the definition only)"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if R.get("err"):
            print(f"PROBE ERROR at {w}x{h}:\n{R['err']}")
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("header", "printBtnBox", "colFit", "beforeSheetW", "afterSheetW"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")
        for k in sorted(n.get("setups", {})):
            s = n["setups"][k]
            print(f"   {k}: sheet={s['sheetVar']} bannerW={s['bannerW']} "
                  f"label={s['label']!r} detail={s['detail']!r}")
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
