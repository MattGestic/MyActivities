#!/usr/bin/env python3
"""
p68_check: the milestone card's fold memory, its one-step back arrow, and the
double-click collection (P68, Matt 2026-10-01).

Drives the real card in headless Chrome by clicking markers on the board:

  - Predecessors & successors and Update history open as last left, on N=3
    cards, and the choice is stored;
  - a dependency chip jump shows a back arrow naming the card it came from;
    using it returns there and clears it; a second jump replaces it (one
    step only); any other open or a close clears it;
  - two clicks on one marker inside 350ms add its ID once to a
    comma-separated collection and leave its card open; a repeat adds
    nothing; three markers give three chips in order; a single click still
    opens and closes as before;
  - the row sits above Start / Duration / Finish, is one line that scrolls
    sideways, Add to list on the left (inert), copy on the right; the cross
    removes one ID; copy writes the string; a chip opens that card;
  - markers take touch-action: manipulation, so a double tap is not a zoom.

Usage:
  python3 tools/p68_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p68-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900), (390, 844)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p68-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const gap=()=>new Promise(r=>setTimeout(r,420));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog');
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const cur=()=>$('ms-code').textContent.trim();
  const open=async function(id){
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    await gap();
    wrapOf(id).click(); await settle();
    if(dlg().hidden) throw new Error('card did not open for '+id);
  };
  const dbl=async function(id){ await gap(); const w=wrapOf(id); w.click(); w.click(); await settle(); };
  const chips=()=>Array.prototype.map.call($('ms-collect-chips').querySelectorAll('.ms-dep-chip'),b=>b.getAttribute('data-id'));
  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    setMsCollection([]); MS_FOLD_STATE.deps=false; MS_FOLD_STATE.hist=true; saveMsFoldState();

    const ids=v=>String(v||'').split(',').map(x=>x.trim()).filter(Boolean);
    const onB=id=>!!wrapOf(id);
    const depsOn=id=>{ const d=DEP_DATA[id]; return d?ids(d.pred).concat(ids(d.succ)).filter(onB):[]; };
    const all=MILESTONES.map(msId).filter(id=>id&&onB(id));
    const A=all.find(id=>depsOn(id).some(x=>x!==id&&depsOn(x).some(y=>y!==x)));
    ck('sample: a milestone with an on-board relationship that has its own', !!A, A||'none');
    const X=depsOn(A).find(x=>x!==A&&depsOn(x).some(y=>y!==x));
    const Y=depsOn(X).find(y=>y!==X);
    const others=all.filter(id=>[A,X,Y].indexOf(id)<0);
    const B=others[0], C=others[1], D=others[2];
    R.notes.sample=[A,X,Y,B,C,D].join(' ');

    // ===== 1. Fold memory =====
    await open(A);
    ck('folds: first card opens with the defaults (relationships closed, history open)',
       !$('ms-dep-lists').open&&$('ms-hist-fold').open, '');
    $('ms-dep-lists').querySelector('summary').click();
    $('ms-hist-fold').querySelector('summary').click();
    await settle();
    let stored=null; try{ stored=JSON.parse(localStorage.getItem('sret-ms-folds')); }catch(x){}
    ck('folds: the choice is stored', stored&&stored.deps===true&&stored.hist===false, JSON.stringify(stored));
    for(const id of [B,C,D]){
      await open(id);
      ck('folds: '+id+' opens as last left (relationships open, history closed)',
         $('ms-dep-lists').open&&!$('ms-hist-fold').open,
         'deps '+$('ms-dep-lists').open+' hist '+$('ms-hist-fold').open);
    }
    $('ms-dep-lists').querySelector('summary').click();
    $('ms-hist-fold').querySelector('summary').click();
    await settle();
    await open(A);
    ck('folds: set back, the next card follows again', !$('ms-dep-lists').open&&$('ms-hist-fold').open, '');

    // ===== 2. Back =====
    ck('back: hidden on a card opened from the board', $('ms-back').hidden, '');
    $('ms-dep-lists').open=true;
    const chipOf=id=>document.querySelector('#ms-dep-lists .ms-dep-chip[data-id="'+CSS.escape(id)+'"]');
    chipOf(X).click(); await settle();
    ck('back: a chip jump opens the linked card', cur()===X, cur());
    ck('back: the arrow shows, naming where it goes', !$('ms-back').hidden&&$('ms-back').title==='Back to '+A, $('ms-back').title);
    const bR=$('ms-back').getBoundingClientRect(), cR=dlg().querySelector('.ms-close').getBoundingClientRect();
    ck('back: top left, right next to close', Math.abs(bR.top-cR.top)<2&&bR.left>=cR.right&&bR.left-cR.right<16,
       Math.round(cR.right)+' -> '+Math.round(bR.left));
    $('ms-back').click(); await settle();
    ck('back: returns to the card it came from', cur()===A, cur());
    ck('back: cleared once used', $('ms-back').hidden&&MS_BACK===null, '');
    $('ms-dep-lists').open=true;
    chipOf(X).click(); await settle();
    $('ms-dep-lists').open=true;
    chipOf(Y).click(); await settle();
    ck('back: a second jump replaces the step (one instance)', cur()===Y&&$('ms-back').title==='Back to '+X, cur()+' / '+$('ms-back').title);
    $('ms-back').click(); await settle();
    ck('back: goes one step only, then nothing', cur()===X&&$('ms-back').hidden, cur());
    $('ms-dep-lists').open=true;
    chipOf(Y).click(); await settle();
    await open(B);
    ck('back: cleared by opening another card from the board', $('ms-back').hidden, '');
    $('ms-dep-lists').open=false;

    // ===== 3. Collection =====
    await open(A);
    ck('collect: row hidden while empty', $('ms-collect').hidden, '');
    await dbl(A);
    ck('collect: a double click on the open card\'s marker adds it and the card stays on it',
       MS_COLLECTION===A&&!dlg().hidden&&cur()===A, MS_COLLECTION+' / '+cur()+' hidden '+dlg().hidden);
    await dbl(A);
    ck('collect: a repeat adds nothing', MS_COLLECTION===A&&chips().length===1, MS_COLLECTION);
    discardMsDialog(); await settle();
    await dbl(B);
    ck('collect: from a closed card, the double click opens it and adds', MS_COLLECTION===A+','+B&&!dlg().hidden&&cur()===B, MS_COLLECTION);
    await dbl(C);
    ck('collect: three markers, three chips in order', chips().join(',')===[A,B,C].join(',')&&MS_COLLECTION===[A,B,C].join(','), chips().join(','));
    ck('collect: chips carry the state dot like the dependency chips',
       $('ms-collect-chips').querySelectorAll('.ms-dep-chip .ms-chip-dot').length===3, '');
    ck('collect: each chip ends in a remove cross', $('ms-collect-chips').querySelectorAll('.ms-dep-chip .ms-collect-x').length===3&&
       Array.prototype.every.call($('ms-collect-chips').querySelectorAll('.ms-dep-chip'),b=>b.lastElementChild.classList.contains('ms-collect-x')), '');
    let stC=null; try{ stC=localStorage.getItem('sret-ms-collection'); }catch(x){}
    ck('collect: kept as display state', stC===MS_COLLECTION, stC);
    await gap();
    wrapOf(C).click(); await settle();
    ck('collect: a single click after the window still closes the card', dlg().hidden&&MS_COLLECTION===[A,B,C].join(','), '');
    await gap();
    wrapOf(D).click(); await settle();
    ck('collect: a single click opens a card and collects nothing', !dlg().hidden&&cur()===D&&chips().length===3, MS_COLLECTION);
    // Layout
    const row=$('ms-collect'), host=$('ms-collect-chips');
    const rR=row.getBoundingClientRect(), sR=dlg().querySelector('.ms-schedule').getBoundingClientRect();
    ck('row: above Start / Duration / Finish', rR.bottom<=sR.top+1, Math.round(rR.bottom)+' <= '+Math.round(sR.top));
    const add=$('ms-collect-add'), cp=$('ms-collect-copy');
    const aR=add.getBoundingClientRect(), hR=host.getBoundingClientRect(), pR=cp.getBoundingClientRect();
    ck('row: Add to list on the left, copy on the right', aR.right<=hR.left+1&&pR.left>=hR.right-1&&/Add to list/.test(add.textContent),
       Math.round(aR.right)+' '+Math.round(hR.left)+'-'+Math.round(hR.right)+' '+Math.round(pR.left));
    ck('row: Add to list is present but inert for now', add.getAttribute('aria-disabled')==='true', '');
    const h1=Math.round(rR.height);
    const many=all.filter(id=>[A,B,C].indexOf(id)<0).slice(0,12);
    setMsCollection([A,B,C].concat(many));
    const h2=Math.round(row.getBoundingClientRect().height);
    const tops=new Set(Array.prototype.map.call(host.querySelectorAll('.ms-dep-chip'),b=>Math.round(b.getBoundingClientRect().top+host.scrollTop)));
    ck('row: 15 chips stay on one line', tops.size===1&&h2===h1, 'tops '+tops.size+' h '+h1+' -> '+h2);
    ck('row: it scrolls sideways instead', host.scrollWidth>host.clientWidth&&getComputedStyle(host).overflowX==='auto',
       host.scrollWidth+' > '+host.clientWidth);
    ck('row: the card does not widen', Math.round(dlg().getBoundingClientRect().width)===Math.min(380,window.innerWidth-24), '');
    ck('page: no horizontal scroll', document.documentElement.scrollWidth<=window.innerWidth, document.documentElement.scrollWidth);
    setMsCollection([A,B,C]);
    host.querySelector('.ms-dep-chip[data-id="'+CSS.escape(B)+'"] .ms-collect-x').click(); await settle();
    ck('remove: the cross takes out that ID only', MS_COLLECTION===A+','+C&&chips().join(',')===A+','+C, MS_COLLECTION);
    ck('remove: the card stays open', !dlg().hidden&&cur()===D, cur());
    let copied=null;
    try{ Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:t=>{ copied=t; return Promise.resolve(); }}}); }catch(x){}
    cp.click(); await settle();
    ck('copy: writes the comma-separated string', copied===A+','+C, String(copied));
    ck('copy: shows it worked', cp.classList.contains('is-copied'), '');
    host.querySelector('.ms-dep-chip[data-id="'+CSS.escape(C)+'"]').click(); await settle();
    ck('chip: opens that milestone\'s card', cur()===C, cur());
    ck('touch: markers do not zoom on a double tap', getComputedStyle(wrapOf(A)).touchAction==='manipulation', getComputedStyle(wrapOf(A)).touchAction);
    setMsCollection([]);
    ck('collect: emptied, the row hides', $('ms-collect').hidden, '');
    discardMsDialog(); await settle();
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
        tmp = pathlib.Path(td) / "p68.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
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

    checks = []
    block = src[src.index('<div id="ms-dialog"'):src.index('<div id="print-filter-note"')]
    checks.append(("source: no em dash in the card markup", "—" not in block and "&mdash;" not in block, ""))
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal",
                   len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))

    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        print(f"\n=== {w}x{h} ===  sample {R.get('notes', {}).get('sample')}")
        if R.get("err"):
            print(R["err"])
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

    fails = 0
    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
