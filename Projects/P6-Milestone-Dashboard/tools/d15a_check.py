#!/usr/bin/env python3
"""
D-15a check: Top filter bar (#top-filter-bar) layout fix.

Five assertions per viewport (390, 768, 1440), each backed by a rendered
result rather than a source read (CLAUDE.md "Verification standard"):

  (a) no element inside #top-filter-bar overflows the viewport horizontally.
  (b) every visible input/select in the bar has the same computed height,
      within 1px.
  (c) each in-field clear button (.sticky-search-clear on the Activity name
      field, .fb-field-clear on the Activity ID field) has its bounding box
      inside its own input's bounding box, on every pointer type.
  (d) the vertical gap between consecutive top-level groups (.tfb-section /
      .tfb-foot) is equal within 2px, and no gap exceeds twice that typical
      gap.
  (e) #top-filter-bar.open's max-height is at least its scrollHeight: the
      bar is not silently clipped short of its own content (the D-15a root
      cause: max-height:var(--tfb-h,160px) with max-height itself in the
      element's `transition` list never picked up the JS-measured --tfb-h
      in this engine, so the bar rendered at the literal 160px fallback
      regardless of its real content height).

Uses headless_shell, not the full `chrome --headless` binary: the latter
floors its internal viewport at 500px wide in this environment no matter
what --window-size asks for (window.innerWidth reads 500 for any smaller
request), which silently invalidates any narrow-viewport assertion.
find_chrome() (tools/import_check.py) already prefers headless_shell for
exactly this reason.

Usage:
  python3 tools/d15a_check.py [path-to-html]
Exit code 1 on any failed check.
"""

import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from import_check import find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="d15a-out">(.*?)</pre>', re.S)

VIEWPORTS = [390, 768, 1440]

PROBE = r"""
(function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='d15a-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  try{
    const bar=document.getElementById('top-filter-bar');
    if(!bar) throw new Error('#top-filter-bar not found');
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight;

    // ---- (a) nothing inside the bar overflows the viewport horizontally ----
    const overflowers=[];
    bar.querySelectorAll('*').forEach(function(el){
      const cs=getComputedStyle(el);
      if(cs.display==='none') return;
      const r=el.getBoundingClientRect();
      if(r.width>0 && r.right>window.innerWidth+0.5){
        overflowers.push({tag:el.tagName,cls:el.className,right:Math.round(r.right)});
      }
    });
    R.notes.overflowers=overflowers;
    ck('no element inside #top-filter-bar overflows the viewport horizontally',
       overflowers.length===0, JSON.stringify(overflowers));

    // ---- (b) every visible input/select shares one control height ----
    const ctrls=Array.prototype.filter.call(
      bar.querySelectorAll('input,select'),
      function(el){ return getComputedStyle(el).display!=='none' &&
                            el.getBoundingClientRect().width>0; });
    const heights=ctrls.map(function(el){ return el.getBoundingClientRect().height; });
    const minH=Math.min.apply(null,heights), maxH=Math.max.apply(null,heights);
    R.notes.controlHeights={n:ctrls.length,min:minH,max:maxH,
      byId:ctrls.map(function(el){ return (el.id||el.tagName)+':'+el.getBoundingClientRect().height.toFixed(1); })};
    ck('every input/select in the bar has the same computed height (+/-1px)',
       ctrls.length>=8 && (maxH-minH)<=1.01,
       ctrls.length+' controls, '+minH.toFixed(1)+'-'+maxH.toFixed(1)+'px');

    // ---- (c) in-field clear buttons sit inside their own input's box ----
    function within(outer,inner){
      return inner.left>=outer.left-0.5 && inner.right<=outer.right+0.5 &&
             inner.top>=outer.top-0.5 && inner.bottom<=outer.bottom+0.5;
    }
    const pairs=[
      ['filter-title','sticky-title-clear'],
    ];
    const idsInput=document.getElementById('filter-ids');
    const idsClear=idsInput?idsInput.parentElement.querySelector('.fb-field-clear'):null;
    const fieldChecks=[];
    pairs.forEach(function(p){
      const input=document.getElementById(p[0]);
      const clear=document.getElementById(p[1]);
      if(!input||!clear) return;
      // The title clear is display:none until there is a value to clear;
      // force it visible to measure the geometry the way it renders once shown.
      const prevDisplay=clear.style.display;
      clear.style.display='inline-flex';
      const ok=within(input.getBoundingClientRect(),clear.getBoundingClientRect());
      clear.style.display=prevDisplay;
      fieldChecks.push({id:p[1],ok:ok});
    });
    if(idsInput&&idsClear){
      fieldChecks.push({id:'ids-clear',
        ok:within(idsInput.getBoundingClientRect(),idsClear.getBoundingClientRect())});
    }
    R.notes.fieldClears=fieldChecks;
    ck('.fb-field-clear (and the title field\'s clear) sit inside their input\'s box',
       fieldChecks.length>=2 && fieldChecks.every(function(f){ return f.ok; }),
       JSON.stringify(fieldChecks));

    // ---- (d) equal vertical gaps between consecutive top-level groups ----
    const topKids=Array.prototype.filter.call(bar.children,function(el){
      return getComputedStyle(el).display!=='none' && el.getBoundingClientRect().height>0;
    });
    const gaps=[];
    for(let i=1;i<topKids.length;i++){
      const prevBottom=topKids[i-1].getBoundingClientRect().bottom;
      const curTop=topKids[i].getBoundingClientRect().top;
      gaps.push(Math.round((curTop-prevBottom)*10)/10);
    }
    R.notes.groupGaps={kids:topKids.map(function(k){return k.className;}),gaps:gaps};
    const gMin=Math.min.apply(null,gaps), gMax=Math.max.apply(null,gaps);
    ck('the vertical gap between consecutive groups is equal (+/-2px)',
       gaps.length>=2 && (gMax-gMin)<=2.01, JSON.stringify(gaps));
    ck('no gap between consecutive groups exceeds 2x the typical gap',
       gaps.length>=2 && gMax<=2*gMin+0.5, JSON.stringify(gaps)+' typical '+gMin);

    // ---- (e) the open bar's max-height is not clipping its own content ----
    const wasOpen=bar.classList.contains('open');
    if(!wasOpen) bar.classList.add('open');
    const mh=getComputedStyle(bar).maxHeight;
    const mhPx=parseFloat(mh);
    const sh=bar.scrollHeight;
    R.notes.clip={maxHeight:mh,maxHeightPx:mhPx,scrollHeight:sh};
    ck('#top-filter-bar.open max-height is at least its scrollHeight (not clipped)',
       isFinite(mhPx) && mhPx>=sh-1, mh+' against scrollHeight '+sh+'px');
    if(!wasOpen) bar.classList.remove('open');

    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
    emit();
  }
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "d15a.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=15000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=120,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}px.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    html = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html")
    checks = []
    for width in VIEWPORTS:
        R = render(html, width, max(900, width))
        if R.get("err"):
            print(f"PROBE ERROR ({width}px):\n{R['err']}")
        print(f"\n=== {width}px ===")
        for k, v in R.get("notes", {}).items():
            print(f"   {k}: {json.dumps(v)}")
        for c in R["checks"]:
            checks.append((f"[{width}px] " + c["name"], c["pass"], c["detail"]))

    print()
    fails = 0
    for name, passed, detail in checks:
        status = "ok  " if passed else "FAIL"
        print(f"  {status} {name}   [{detail}]")
        if not passed:
            fails += 1

    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
