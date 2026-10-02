#!/usr/bin/env python3
"""
p77_share_report_check: Share report (P77, Matt 2026-10-02).

Headless Chromium, the dump-dom harness of p75_* (the fixture is seeded by
tools/check_map/chrome_fixture.py; the empty stage opts out with the
sret:no-fixture marker).

  1. (empty app, sret:no-fixture) the Share button is in the header action
     group, disabled, with a tooltip saying why; a click opens nothing.
  2. (fixture, 1440) the button sits in .rpt-hd-actions after + Milestone,
     enabled, primary styled, with an icon. N=3 updates are seeded through
     addEntry, the card's own entry path: a finish move, a status (health)
     change, a comment, plus a second card save on the finish milestone inside
     the coalescing window (it must count once). The dialog is driven by
     clicks: the period defaults to reportPeriodISO() and offers All periods,
     From is typed and remembered, Include Excel detail is on by default.
       - Share with navigator.share stubbed and canShare true: share is called
         once with both files (report .html, workbook .xlsx), named
         <Title>_Report_<W/E>.html and <Title>_Updates_<W/E>.xlsx.
       - canShare false: no share call, both files go through the download
         path (Blob + anchor intercepted, as p71_check does).
       - canShare true for the report alone: the report is shared, the
         workbook downloaded.
       - Download: always downloads, never shares.
     The workbook is parsed back with the embedded SheetJS: Summary rows equal
     the updated milestones, Log rows equal the period's entries.
  3. The captured report HTML (Python side): every section heading; the three
     updates with their labels and old -> new values; the At a glance counts
     equal the board's own markers; no <script; no em or en dash; under a sane
     size; no external reference.
  4. The report opened on its own in a fresh page at 390 and 1440: no console
     error, no horizontal scroll at 390, every section visible; print
     emulation (the page's @media print rules applied at A4 printable width)
     keeps the section headings with their content and the update cards,
     tiles and table rows unbroken, with no horizontal overflow; and Chromium
     prints it to a PDF.

  --save DIR writes the fixture report and its 390 / 1440 screenshots there
  (docs/mockups/P77).
"""

import argparse
import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_RE = re.compile(r'<pre id="p77-out">(.*?)</pre>', re.S)
HEADINGS = ["At a glance", "Updates this period", "Attention", "New milestones proposed"]
MAX_BYTES = 400_000

EMPTY_PROBE = r"""
// sret:no-fixture  (this stage tests the app as it ships)
(async function(){
  const R={checks:[]};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p77-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,300));
  try{
    await settle(); await settle();
    const b=document.getElementById('btn-share-report');
    ck('empty: the dashboard is empty', isDashboardEmpty()&&document.body.classList.contains('is-empty'));
    ck('empty: Share button present in the header action group', !!b&&!!b.closest('.rpt-hd-actions'));
    ck('empty: Share button is disabled', !!b&&b.disabled===true);
    ck('empty: Share button shown (not hidden)', !!b&&b.getClientRects().length>0);
    ck('empty: tooltip says why', !!b&&/nothing to report/i.test(b.title)&&/import a schedule|add a milestone/i.test(b.title), b&&b.title);
    if(b) b.click();
    await settle();
    ck('empty: a click opens no dialog', document.getElementById('share-dialog').hidden===true);
    openShareDialog(); await settle();
    ck('empty: openShareDialog() refuses too', document.getElementById('share-dialog').hidden===true);
  }catch(e){ R.err=String(e&&e.stack||e); }
  emit();
})();
"""

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p77-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,300));
  const $=id=>document.getElementById(id);
  // Capture: every Blob the app builds, every anchor download, every share.
  const cap={blobs:[],downloads:[],shares:[]};
  // Parts are kept so the probe reads a file synchronously: an async Blob
  // read lets headless virtual time run on and the DOM dump comes early.
  const OB=window.Blob, OF=window.File, PARTS=new WeakMap();
  window.Blob=function(parts,opts){ const b=new OB(parts,opts); PARTS.set(b,parts); cap.blobs.push(b); return b; };
  window.Blob.prototype=OB.prototype;
  window.File=function(parts,name,opts){ const f=new OF(parts,name,opts); PARTS.set(f,parts); return f; };
  window.File.prototype=OF.prototype;
  const flat=function(x){ const ps=PARTS.get(x); if(!ps) return [];
    return ps.reduce(function(a,p){ return a.concat(PARTS.has(p)?flat(p):[p]); },[]); };
  const oc=HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click=function(){ if(this.download){ cap.downloads.push({name:this.download,href:this.href}); return; } return oc.call(this); };
  const urlBlob={}, ocu=URL.createObjectURL;
  URL.createObjectURL=function(b){ const u=ocu.call(URL,b); urlBlob[u]=b; return u; };
  URL.revokeObjectURL=function(){};
  let canShareMode='all';
  navigator.share=function(d){ cap.shares.push(d); return Promise.resolve(); };
  navigator.canShare=function(d){
    if(canShareMode==='none') return false;
    if(canShareMode==='one') return !!(d&&d.files&&d.files.length===1);
    return true;
  };
  const reset=()=>{ cap.downloads.length=0; cap.shares.length=0; };
  const textOf=b=>flat(b).map(String).join('');
  const bufOf=b=>{ const ps=flat(b); return ps.length===1?ps[0]:null; };
  try{
    await settle(); await settle();
    const b=$('btn-share-report'), add=$('btn-add-ms'), grp=b&&b.closest('.rpt-hd-actions');
    ck('button: in the header action group', !!grp&&grp.contains(add)&&grp.contains($('btn-filter-expand')));
    ck('button: right after + Milestone', !!b&&b.previousElementSibling===add);
    ck('button: visible and enabled with a schedule', !!b&&b.getClientRects().length>0&&b.disabled===false);
    ck('button: has an icon and a short label', !!b&&!!b.querySelector('svg')&&b.textContent.trim().length>0&&b.textContent.trim().length<=12, b&&b.textContent.trim());
    const sp=document.createElement('span'); sp.style.background='var(--color-btn-primary-bg)'; document.body.appendChild(sp);
    const prim=getComputedStyle(sp).backgroundColor; sp.remove();
    ck('button: primary styled (primary button background token)', !!b&&getComputedStyle(b).backgroundColor===prim, b&&getComputedStyle(b).backgroundColor+' vs '+prim);

    // ---- seed N=3 updates through addEntry (the card's own entry path) ----
    const per=reportPeriodISO();
    const before=ENTRIES.filter(e=>e.period===per).length;
    const done=m=>{ const s=effectiveState(m); return s==='DONE'||s==='DONEUSER'; };
    const cand=MILESTONES.filter(m=>msId(m)&&!isUserMs(m)&&!done(m)&&m.date&&
      document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(msId(m))+'"]')&&
      !ENTRIES.some(e=>e.target.key===msKeyFor(m)));
    const A=cand[0], B=cand.find(m=>m!==A&&(effectiveState(m)==='TRACK'||effectiveState(m)==='FUTURE')), C=cand.find(m=>m!==A&&m!==B);
    ck('seed: three distinct schedule milestones', !!A&&!!B&&!!C, [A,B,C].map(m=>m&&msId(m)).join(','));
    const plus=(iso,n)=>{ const d=new Date(+iso.slice(0,4),+iso.slice(5,7)-1,+iso.slice(8,10)+n); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); };
    const aTo=plus(A.date,14), bFromState=effectiveState(B);
    addEntry({target:{kind:'ms',key:msKeyFor(A)},changes:{date:{from:A.date,to:aTo}},origin:'card',status:'open'});
    addEntry({target:{kind:'ms',key:msKeyFor(B)},changes:{health:{from:null,to:3}},origin:'card',status:'sent'});
    addEntry({target:{kind:'ms',key:msKeyFor(C)},text:'Vendor drawings received, review under way',origin:'card',status:'done'});
    // A second save on A inside the window: coalesces into A's entry.
    addEntry({target:{kind:'ms',key:msKeyFor(A)},text:'Moved two weeks for vendor data',origin:'card',status:'open'});
    scheduleRerender(true);
    await settle(); await settle();
    const inPer=ENTRIES.filter(e=>e.period===per);
    ck('seed: the coalesced save counts once (3 new entries, not 4)', inPer.length-before===3, inPer.length-before);
    const ids={A:msId(A),B:msId(B),C:msId(C)};
    R.notes.ids=ids; R.notes.aFrom=fmtTipDate(A._msBase&&A._msBase.date||A.date); R.notes.aFromIso=(A._msBase&&A._msBase.date)||null;
    R.notes.aTo=fmtTipDate(aTo); R.notes.bFrom=STATE_LABELS[B.state]; R.notes.bFromState=bFromState;
    R.notes.aName=String(A.actName||''); R.notes.bName=String(B.actName||''); R.notes.cName=String(C.actName||'');
    ck('seed: B now At risk on the board', effectiveState(B)==='RISK');

    // ---- the board's own counts, from its markers ----
    const cls={'s-done':'DONE','s-doneuser':'DONE','s-track':'TRACK','s-risk':'RISK','s-crit':'CRIT','s-future':'FUTURE','s-na':'NA'};
    const bc={DONE:0,TRACK:0,RISK:0,CRIT:0,FUTURE:0,NA:0}; let markers=0;
    document.querySelectorAll('#tbody .m-wrap[data-ms]:not(.m-ghost) svg.ms-icon').forEach(function(ic){
      markers++;
      for(const c in cls) if(ic.classList.contains(c)){ bc[cls[c]]++; break; }
    });
    R.notes.board=bc; R.notes.markers=markers;
    R.notes.followUps={open:inPer.filter(e=>['open','review','outstanding'].indexOf(e.status)>=0).length,
      sent:inPer.filter(e=>e.status==='sent').length,done:inPer.filter(e=>['done','closed'].indexOf(e.status)>=0).length};
    R.notes.updated=new Set(inPer.filter(e=>e.target.kind==='ms').map(e=>e.target.key)).size;
    R.notes.attention=MILESTONES.filter(m=>{ const s=effectiveState(m); return (s==='RISK'||s==='CRIT')&&dateToCol(m.date)>=0; }).length;
    R.notes.offBoard=MILESTONES.filter(m=>dateToCol(m.date)<0).length;
    R.notes.userMs=USER_MILESTONES.length;

    // ---- the dialog, by clicks ----
    b.click(); await settle();
    const dlg=$('share-dialog'), sel=$('share-period');
    ck('dialog: opens from the button', !dlg.hidden&&!$('share-scrim').hidden);
    ck('dialog: period defaults to the current report period', sel.value===per, sel.value+' vs '+per);
    ck('dialog: All periods is offered', Array.from(sel.options).some(o=>o.value==='all'&&/All periods/.test(o.textContent)));
    ck('dialog: Include Excel detail is on by default', $('share-xlsx').checked===true);
    ck('dialog: Share and Download actions', !!$('share-go')&&!!$('share-download'));
    ck('dialog: no em dash in its text', !/[—–]/.test(dlg.textContent));
    $('share-from').value='MG'; $('share-from').dispatchEvent(new Event('input',{bubbles:true}));

    // Share, both files accepted
    reset(); canShareMode='all';
    $('share-go').click(); await settle(); await settle();
    ck('share: dialog closes', dlg.hidden);
    ck('share: navigator.share called once', cap.shares.length===1, cap.shares.length);
    const sh=cap.shares[0]||{files:[]};
    const names=sh.files.map(f=>f.name);
    R.notes.names=names;
    ck('share: with both files together', sh.files.length===2&&/\.html$/.test(names[0])&&/\.xlsx$/.test(names[1]), names.join(' | '));
    ck('share: no download alongside', cap.downloads.length===0, cap.downloads.length);
    const stem=shareFileStem();
    ck('share: file names <Title>_Report_<W/E>.html and <Title>_Updates_<W/E>.xlsx',
      names[0]===stem+'_Report_'+per+'.html'&&names[1]===stem+'_Updates_'+per+'.xlsx', names.join(' | '));
    ck('share: title is filename-safe', /^[A-Za-z0-9_-]+$/.test(stem), stem);
    const ttl=document.getElementById('rpt-title-text').textContent.trim();
    const want=ttl.replace(/[^A-Za-z0-9 _-]+/g,' ').trim().replace(/\s+/g,'_').replace(/_+/g,'_').slice(0,80).replace(/^[_-]+|[_-]+$/g,'');
    ck('share: file name built from the heading shown', stem===want&&stem.length>0, ttl+' -> '+stem);
    R.notes.title=ttl;
    ck('share: file types', sh.files[0]&&sh.files[0].type==='text/html'&&/spreadsheetml/.test(sh.files[1]&&sh.files[1].type));
    R.html=sh.files[0]?textOf(sh.files[0]):'';
    if(sh.files[1]){
      const wb=XLSX.read(new Uint8Array(bufOf(sh.files[1])),{type:'array'});
      const S=XLSX.utils.sheet_to_json(wb.Sheets.Summary,{header:1}), L=XLSX.utils.sheet_to_json(wb.Sheets.Log,{header:1});
      R.notes.sheets=wb.SheetNames;
      ck('xlsx: Summary and Log sheets', JSON.stringify(wb.SheetNames)===JSON.stringify(['Summary','Log']), wb.SheetNames.join(','));
      ck('xlsx: Summary rows equal the updated milestones', S.length-1===R.notes.updated, (S.length-1)+' vs '+R.notes.updated);
      ck('xlsx: Log rows equal the period entries', L.length-1===inPer.length, (L.length-1)+' vs '+inPer.length);
      const sIds=S.slice(1).map(r=>String(r[0]));
      ck('xlsx: Summary carries the three seeded IDs', [ids.A,ids.B,ids.C].every(i=>sIds.indexOf(i)>=0), sIds.join(','));
      const aRow=S.find(r=>String(r[0])===ids.A)||[];
      ck('xlsx: Summary rolls up the finish move (Finish new)', aRow[8]===fmtTipDate(aTo), JSON.stringify(aRow));
      const bRow=S.find(r=>String(r[0])===ids.B)||[];
      ck('xlsx: Summary rolls up the status change (Status/Health new)', bRow[10]==='At risk', JSON.stringify(bRow));
      const lA=L.find(r=>String(r[1])===ids.A)||[];
      ck('xlsx: Log change text for the finish move', /^Finish .* → /.test(String(lA[6])), String(lA[6]));
      ck('xlsx: no em or en dash in any cell', !/[—–]/.test(JSON.stringify([S,L])));
    }

    // From is remembered
    b.click(); await settle();
    ck('dialog: From is remembered', $('share-from').value==='MG', $('share-from').value);

    // canShare false: download path
    reset(); canShareMode='none';
    $('share-go').click(); await settle(); await new Promise(r=>setTimeout(r,1500));
    ck('no canShare: share not called', cap.shares.length===0, cap.shares.length);
    ck('no canShare: both files downloaded', cap.downloads.length===2&&/\.html$/.test(cap.downloads[0].name)&&/\.xlsx$/.test(cap.downloads[1].name),
      cap.downloads.map(d=>d.name).join(' | '));

    // canShare only for one file: the report shared, the workbook downloaded
    b.click(); await settle();
    reset(); canShareMode='one';
    $('share-go').click(); await settle(); await new Promise(r=>setTimeout(r,1500));
    ck('one file: report shared alone', cap.shares.length===1&&cap.shares[0].files.length===1&&/\.html$/.test(cap.shares[0].files[0].name));
    ck('one file: workbook downloaded', cap.downloads.length===1&&/\.xlsx$/.test(cap.downloads[0].name), cap.downloads.map(d=>d.name).join(' | '));

    // Download always downloads; Excel detail off gives the report alone
    b.click(); await settle();
    reset(); canShareMode='all';
    $('share-xlsx').checked=false;
    $('share-download').click(); await settle(); await new Promise(r=>setTimeout(r,1500));
    ck('download: never shares', cap.shares.length===0);
    ck('download: report only when Excel detail is off', cap.downloads.length===1&&/\.html$/.test(cap.downloads[0].name), cap.downloads.map(d=>d.name).join(' | '));

    // All periods
    b.click(); await settle();
    reset(); $('share-period').value='all'; $('share-xlsx').checked=true;
    $('share-download').click(); await settle(); await new Promise(r=>setTimeout(r,1500));
    const allBlob=cap.downloads[0]&&urlBlob[cap.downloads[0].href];
    const allHtml=allBlob?textOf(allBlob):'';
    ck('all periods: report says so', /All periods/.test(allHtml)&&/Updates, all periods/.test(allHtml));
    ck('all periods: workbook too', cap.downloads.length===2);

    // Escape closes the dialog
    b.click(); await settle();
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    await settle();
    ck('dialog: Esc closes it', $('share-dialog').hidden);
  }catch(e){ R.err=String(e&&e.stack||e); }
  emit();
})();
"""

# Injected into the report page itself (a test copy): error capture first,
# then measures, then print emulation.
REPORT_HEAD = r"""<script>
window.__errs=[];
window.addEventListener('error',function(e){ window.__errs.push(String(e.message||(e.target&&(e.target.src||e.target.href))||'error')); },true);
(function(){ const oe=console.error; console.error=function(){ window.__errs.push(Array.from(arguments).join(' ')); return oe.apply(console,arguments); }; })();
</script>"""

REPORT_PROBE = r"""<script>
(function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  setTimeout(function(){
    try{
      const W=window.innerWidth, de=document.documentElement;
      R.notes.width=W; R.notes.scrollW=de.scrollWidth;
      ck('no horizontal scroll', de.scrollWidth<=W+1, de.scrollWidth+' > '+W);
      const wide=Array.from(document.querySelectorAll('.page *')).filter(el=>el.getBoundingClientRect().right>W+1).map(el=>el.tagName+'.'+el.className).slice(0,5);
      ck('nothing runs past the right edge', wide.length===0, wide.join(', '));
      const hs=Array.from(document.querySelectorAll('h2')).map(h=>h.textContent);
      R.notes.h2=hs;
      ck('every section is visible', Array.from(document.querySelectorAll('section')).every(s=>s.getClientRects().length>0&&s.getBoundingClientRect().height>20));
      ck('no console or load error', window.__errs.length===0, window.__errs.join(' | '));
      if(__PRINT__){
      // Print emulation: the page's own @media print rules applied as
      // unconditional rules, in a window as wide as an A4 page's printable
      // area (210mm less the report's 12mm side margins, at 96 dpi), which is
      // also the width print media queries see.
      const rules=[];
      for(const sh of document.styleSheets) for(const r of sh.cssRules){
        if(r.type===CSSRule.MEDIA_RULE&&/print/.test(r.media.mediaText)) for(const x of r.cssRules) rules.push(x.cssText);
      }
      ck('print: the page has print rules', rules.length>0, rules.length);
      const st=document.createElement('style'); st.textContent=rules.join('\n'); document.head.appendChild(st);
      ck('print: no overflow at A4 width', de.scrollWidth<=W+1, de.scrollWidth+' > '+W);
      const cs=(el,p)=>getComputedStyle(el)[p];
      const h2=Array.from(document.querySelectorAll('h2'));
      ck('print: each heading stays with its content', h2.length>=4&&h2.every(h=>cs(h,'breakAfter')==='avoid'), h2.map(h=>cs(h,'breakAfter')).join(','));
      const cards=Array.from(document.querySelectorAll('.upd'));
      ck('print: update cards are not split', cards.length>0&&cards.every(c=>cs(c,'breakInside')==='avoid'), cards.length);
      const tiles=Array.from(document.querySelectorAll('.tiles'));
      ck('print: tile rows are not split', tiles.length>=2&&tiles.every(t=>cs(t,'breakInside')==='avoid'));
      const rows=Array.from(document.querySelectorAll('tbody tr'));
      ck('print: table rows are not split', rows.every(r=>cs(r,'breakInside')==='avoid'), rows.length);
      const th=Array.from(document.querySelectorAll('thead'));
      ck('print: table headings repeat on each page', th.every(t=>cs(t,'display')==='table-header-group'), th.length);
      ck('print: every section still visible', Array.from(document.querySelectorAll('section')).every(s=>s.getClientRects().length>0));
      }
    }catch(e){ R.err=String(e&&e.stack||e); }
    const o=document.createElement('pre'); o.id='p77-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o);
  },200);
})();
</script>"""


def chrome(page, width, height, budget, no_fixture=False, extra=None):
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p77.html"
        tmp.write_text(page, encoding="utf-8")
        env = dict(os.environ)
        if no_fixture:
            env["SRET_NO_FIXTURE"] = "1"
        cmd = [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={td}/prof",
               f"--window-size={width},{height}", f"--virtual-time-budget={budget}",
               "--enable-logging=stderr", "--v=0"] + (extra or []) + ["--dump-dom", tmp.as_uri()]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height} (exit {proc.returncode}, {len(proc.stdout)} bytes of DOM, "
                 f"no-fixture {no_fixture}).\n" + proc.stdout[-600:] + "\n" + proc.stderr[-1500:])
    R = json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))
    R["_stderr"] = proc.stderr
    return R


def app_page(probe):
    src = (ROOT / "src" / "milestone-dashboard.html").read_text(encoding="utf-8", errors="replace")
    out = src.replace("</body>", "<script>\n" + probe + "\n</script>\n</body>")
    if out == src:
        sys.exit("Could not find </body> to inject into.")
    return out


def report_page(html, printing=False):
    assert html.count("<head>") == 1 and html.count("</body>") == 1
    probe = REPORT_PROBE.replace("__PRINT__", "true" if printing else "false")
    return html.replace("<head>", "<head>" + REPORT_HEAD, 1).replace("</body>", probe + "</body>", 1)


def console_errors(stderr):
    return [ln for ln in stderr.splitlines() if "CONSOLE" in ln and ("ERROR" in ln or "Uncaught" in ln)]


def shot(html, width, height, png):
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "r.html"
        tmp.write_text(html, encoding="utf-8")
        subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={td}/prof",
                        f"--window-size={width},{height}", f"--screenshot={png}", tmp.as_uri()],
                       capture_output=True, text=True, timeout=300)


def print_pdf(html):
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "r.html"
        pdf = pathlib.Path(td) / "r.pdf"
        tmp.write_text(html, encoding="utf-8")
        subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", f"--user-data-dir={td}/prof",
                        "--no-pdf-header-footer", f"--print-to-pdf={pdf}", tmp.as_uri()],
                       capture_output=True, text=True, timeout=300)
        return pdf.read_bytes() if pdf.exists() else b""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None, help="write the sample report and its screenshots here")
    args = ap.parse_args()
    src = (ROOT / "src" / "milestone-dashboard.html").read_text(encoding="utf-8", errors="replace")
    mod = (ROOT / "src" / "modules" / "notes-export" / "notes-export.js").read_text(encoding="utf-8")

    checks = []
    checks.append(("source: notes-export module pasted unchanged", mod.rstrip("\n") in src, ""))
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, src.count("</body>")))
    checks.append(("source: exactly one version literal", len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))
    blk = src[src.index("// P77: SHARE REPORT"):src.index("function exportCSV()")]
    checks.append(("source: no em or en dash in the Share report code", not re.search("[—–]", blk), ""))
    checks.append(("source: the report is built with no fetch, XHR or external URL",
                   not re.search(r"fetch\(|XMLHttpRequest|https?://", blk), ""))

    # 1. empty app
    E = chrome(app_page(EMPTY_PROBE), 1440, 900, 20000, no_fixture=True)
    if E.get("err"):
        checks.append(("empty stage ran", False, E["err"][:300]))
    for c in E["checks"]:
        checks.append(("[empty] " + c["name"], c["pass"], c["detail"]))

    # 2. fixture
    R = chrome(app_page(PROBE), 1440, 900, 120000)
    if R.get("err"):
        checks.append(("fixture stage ran", False, R["err"][:400]))
    for c in R["checks"]:
        checks.append(("[1440] " + c["name"], c["pass"], c["detail"]))
    html = R.get("html", "")
    N = R.get("notes", {})

    # 3. the report HTML
    checks.append(("report: captured", len(html) > 1000, len(html)))
    for h in HEADINGS:
        checks.append((f"report: heading '{h}'", f"<h2>{h} " in html or f"<h2>{h}<" in html, ""))
    checks.append(("report: header fields", all(x in html for x in
                   ["Project", "Report period", "Report date", "Schedule data date", "Prepared by", "Generated"]), ""))
    checks.append(("report: title is the board's heading", f"<h1>{_esc(N.get('title', '?'))}</h1>" in html, N.get("title")))
    checks.append(("report: Prepared by carries From", "<dt>Prepared by</dt><dd>MG</dd>" in html, ""))
    checks.append(("report: footer line", re.search(
        r"Prepared with Milestone Dashboard 3\.[0-9]+\.[0-9]+-P[0-9A-Za-z]+\. Dates are as at the schedule data date; "
        r"edited dates are proposals, not changes to the master schedule\.", html) is not None, ""))
    ids = N.get("ids", {})

    def card(i):
        m = re.search(r'<article class="upd"><div class="upd-h"><span class="id">' + re.escape(i) + r'</span>(.*?)</article>', html, re.S)
        return m.group(1) if m else ""
    ca, cb, cc = card(ids.get("A", "?")), card(ids.get("B", "?")), card(ids.get("C", "?"))
    checks.append(("report: update A (finish move) with label and old -> new",
                   f'<span class="lbl">End date</span> <span class="from">{N.get("aFrom")}</span> → <span class="to">{N.get("aTo")}</span>' in ca, ca[:300]))
    checks.append(("report: update A carries the coalesced comment once", ca.count("Moved two weeks for vendor data") == 1 and "(2 updates)" not in ca, ""))
    checks.append(("report: update B (status) with label and old -> new",
                   f'<span class="lbl">Health</span> <span class="from">{N.get("bFrom")} (schedule)</span> → <span class="to">At risk</span>' in cb, cb[:300]))
    checks.append(("report: update C (comment)", '<p class="cmt">Vendor drawings received, review under way</p>' in cc, cc[:300]))
    checks.append(("report: follow-up status on each", "Follow-up: Open" in ca and "Follow-up: Sent" in cb and "Follow-up: Done" in cc, ""))
    checks.append(("report: names shown", all(N.get(k, "") and _esc(N[k]) in html for k in ("aName", "bName", "cName")), ""))
    order = [html.find(f'<span class="id">{ids.get(k, "?")}</span>') for k in ("C", "B", "A")]
    checks.append(("report: newest first (C, B, A by last save)", all(x >= 0 for x in order) and order == sorted(order), order))

    def tile(label):
        m = re.search(r'<div class="tile [^"]*"><b>(\d+)</b><span>' + re.escape(label) + "</span>", html)
        return int(m.group(1)) if m else None
    bc = N.get("board", {})
    got = {k: tile(lbl) for k, lbl in (("DONE", "Complete"), ("TRACK", "On track"), ("RISK", "At risk"),
                                        ("CRIT", "Critical"), ("FUTURE", "Future"))}
    checks.append(("report: status counts equal the board's markers",
                   all(got[k] == bc.get(k) for k in got) and (bc.get("NA", 0) == 0 or tile("Not rated") == bc.get("NA")),
                   f"report {got} board {bc}"))
    checks.append(("report: total equals the board's markers",
                   re.search(r"<h2>At a glance <span class=\"n\">" + str(N.get("markers")) + " milestones", html) is not None, N.get("markers")))
    ob = N.get("offBoard", 0)
    checks.append(("report: milestones outside the week range are named, not counted",
                   (ob == 0 and "outside the board" not in html) or f"{ob} milestones fall outside the board\u2019s week range" in html, ob))
    checks.append(("report: milestones updated", tile("Milestones updated") == N.get("updated"), f"{tile('Milestones updated')} vs {N.get('updated')}"))
    fu = N.get("followUps", {})
    checks.append(("report: follow-ups open / sent / done",
                   (tile("Follow-ups open"), tile("Follow-ups sent"), tile("Follow-ups done")) == (fu.get("open"), fu.get("sent"), fu.get("done")),
                   f"{fu}"))
    checks.append(("report: Attention lists every At risk / Critical milestone",
                   re.search(r"<h2>Attention <span class=\"n\">" + str(N.get("attention")) + " at risk or critical", html) is not None
                   and html.count('<td data-l="ID" class="id">') >= N.get("attention", 0), N.get("attention")))
    checks.append(("report: B (now At risk) is in Attention", f'<td data-l="ID" class="id">{ids.get("B")}</td>' in html, ""))
    checks.append(("report: empty section says so (no user milestones in the fixture)",
                   N.get("userMs") != 0 or "No new milestones proposed" in html, N.get("userMs")))
    checks.append(("report: no <script", "<script" not in html.lower(), ""))
    checks.append(("report: no em or en dash", not re.search("[—–]", html), ""))
    checks.append(("report: no external reference", not re.search(r"(src|href)\s*=|@import|url\(", html), ""))
    checks.append(("report: no app code or raw state",
                   all(x not in html for x in ("__PUBLISHED_STATE__", "SRETEntries", "function(", "app-script", '"entries"')), ""))
    checks.append((f"report: under {MAX_BYTES // 1000} KB", 0 < len(html.encode("utf-8")) < MAX_BYTES, len(html.encode("utf-8"))))
    checks.append(("report: palette defined in its own :root", re.search(r":root\{--rpt-[\w-]+:#", html) is not None, ""))

    # 4. the report opened on its own
    if html:
        for (w, h, pr) in ((390, 844, False), (1440, 900, False), (703, 1000, True)):
            P = chrome(report_page(html, pr), w, h, 3000, no_fixture=True)
            w = f"print A4 {w}px" if pr else w
            if P.get("err"):
                checks.append((f"[report {w}] probe ran", False, P["err"][:300]))
            for c in P["checks"]:
                checks.append((f"[report {w}] " + c["name"], c["pass"], c["detail"]))
            errs = console_errors(P["_stderr"])
            checks.append((f"[report {w}] no console error in Chromium's log", not errs, " | ".join(errs)[:300]))
            checks.append((f"[report {w}] every heading rendered", all(any(x.startswith(hh) for x in P["notes"].get("h2", [])) for hh in HEADINGS), P["notes"].get("h2")))
        pdf = print_pdf(html)
        pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
        checks.append(("report prints to PDF (Chromium print)", pdf.startswith(b"%PDF") and pages >= 1, f"{pages} page(s)"))

        if args.save:
            out = pathlib.Path(args.save)
            out.mkdir(parents=True, exist_ok=True)
            (out / "sample-report.html").write_text(html, encoding="utf-8")
            shot(html, 390, 2600, str((out / "sample-report-390.png").resolve()))
            shot(html, 1440, 1500, str((out / "sample-report-1440.png").resolve()))
            print(f"saved sample report and screenshots to {out}")

    fails = 0
    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail not in ("", None) and not ok else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


if __name__ == "__main__":
    sys.exit(main())
