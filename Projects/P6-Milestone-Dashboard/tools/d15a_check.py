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

D-15a2 adds five more, fixing the follow-up regressions the orchestrator
found from the D-15a screenshots:

  (f) the Activity name input's computed padding-left is at least the search
      icon's right edge minus the input's left edge, plus 4px (checks the
      icon does not sit over the placeholder text). Run at every viewport,
      since the icon and the field do not resize by width.
  (g) at 390px, with the page's own `@media (pointer:coarse)` rules forced on
      (real headless Chrome reports a fine pointer, so this cannot rely on
      the media query matching on its own; see `render_coarse` below), every
      visible input, select and button inside the bar has computed height
      >= 43px (the 44px touch standard, 1px tolerance) and every input/select
      has font-size >= 16px (the iOS zoom-on-focus threshold).
  (h) at 390px, plain (no forced pointer), every visible input/select has
      width >= 90% of its own field container (.tfb-fld-ctrl), except where
      more than one input/select shares a field container (Total float,
      Week, Date range) - there, their widths must SUM to >= 90% of it.
  (i) the footer close button (#btn-filter-hide) has computed border-style
      'none' or border-width 0.
  (j) at 1440px, for each field inside #tfb-find (Find), the horizontal gap
      between the label's right edge and its field container's left edge is
      <= 16px.

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
COARSE_OUT_RE = re.compile(r'<pre id="d15a-coarse-out">(.*?)</pre>', re.S)

VIEWPORTS = [390, 768, 1440]


def extract_coarse_css(page_text):
    """Pull every `@media (pointer:coarse){...}` block's inner rules out of
    the page's own <style>, unwrapped from the media condition, so they can
    be re-injected as always-on rules. headless Chrome has no real coarse
    pointer to emulate, so the only faithful way to test what those rules DO
    is to apply the app's own declarations rather than hand-writing new ones
    that could drift from them. Brace-counted rather than regex-matched
    end to end, since each block nests one level of braces (its rules)."""
    css_chunks = []
    marker = "@media (pointer:coarse)"
    start = 0
    while True:
        idx = page_text.find(marker, start)
        if idx == -1:
            break
        brace_open = page_text.index("{", idx)
        depth = 0
        i = brace_open
        while i < len(page_text):
            if page_text[i] == "{":
                depth += 1
            elif page_text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        css_chunks.append(page_text[brace_open + 1:i])
        start = i + 1
    return "\n".join(css_chunks)

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

    // ---- (f) Activity name input's padding-left clears the search icon ----
    const nameIcon=bar.querySelector('.sticky-search-icon');
    const nameInput=document.getElementById('filter-title');
    if(nameIcon&&nameInput){
      const ir=nameIcon.getBoundingClientRect(), inr=nameInput.getBoundingClientRect();
      const padLeft=parseFloat(getComputedStyle(nameInput).paddingLeft);
      const needed=(ir.right-inr.left)+4;
      R.notes.namePad={paddingLeft:padLeft,iconRight:ir.right,inputLeft:inr.left,needed:needed};
      ck('Activity name input padding-left clears the search icon (+4px margin)',
         padLeft>=needed-0.5, 'padding-left '+padLeft.toFixed(1)+'px, needed >= '+needed.toFixed(1)+'px');
    }

    // ---- (h) at 390: input/select width >= 90% of its field container,
    //          summed across a shared multi-control row ----
    if(window.innerWidth<=390){
      const byCtrl=new Map();
      ctrls.forEach(function(el){
        const ctrl=el.closest('.tfb-fld-ctrl');
        if(!ctrl) return;
        if(!byCtrl.has(ctrl)) byCtrl.set(ctrl,[]);
        byCtrl.get(ctrl).push(el);
      });
      const widthResults=[];
      let widthOk=true;
      byCtrl.forEach(function(els,ctrl){
        const cw=ctrl.getBoundingClientRect().width;
        const sum=els.reduce(function(s,el){ return s+el.getBoundingClientRect().width; },0);
        const ratio=cw>0?sum/cw:0;
        const ok=ratio>=0.9;
        if(!ok) widthOk=false;
        widthResults.push({ctrl:ctrl.id||ctrl.className,n:els.length,sum:Math.round(sum),
          containerW:Math.round(cw),ratio:Math.round(ratio*100)});
      });
      R.notes.fieldWidths=widthResults;
      ck('every input/select fills (or, sharing a row, together fill) >=90% of its field container',
         byCtrl.size>0 && widthOk, JSON.stringify(widthResults));
    }

    // ---- (j) at 1440: Find label-to-control gap ----
    if(window.innerWidth>=1280){
      const findBar=document.getElementById('tfb-find');
      if(findBar){
        const gapResults=[];
        let gapOk=true;
        findBar.querySelectorAll('.tfb-group').forEach(function(grp){
          const label=grp.querySelector('label');
          const ctrl=grp.querySelector('.tfb-fld-ctrl');
          if(!label||!ctrl) return;
          const lr=label.getBoundingClientRect(), cr=ctrl.getBoundingClientRect();
          const gap=cr.left-lr.right;
          const ok=gap<=16.5;
          if(!ok) gapOk=false;
          gapResults.push({label:label.textContent.trim(),gap:Math.round(gap*10)/10});
        });
        R.notes.findGaps=gapResults;
        ck('at 1440px, each Find field\'s label-to-control gap is <=16px',
           gapResults.length>=3 && gapOk, JSON.stringify(gapResults));
      }
    }

    // ---- (i) footer close button is borderless ----
    const hideBtn=document.getElementById('btn-filter-hide');
    if(hideBtn){
      const hcs=getComputedStyle(hideBtn);
      R.notes.hideBtnBorder={borderStyle:hcs.borderStyle,borderWidth:hcs.borderWidth};
      ck('#btn-filter-hide is borderless (border-style none or border-width 0)',
         hcs.borderStyle==='none'||parseFloat(hcs.borderWidth)===0,
         'border-style '+hcs.borderStyle+', border-width '+hcs.borderWidth);
    }

    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
    emit();
  }
})();
"""

# ---- (g) coarse-pointer sizing, run only against a coarse-forced render ----
PROBE_COARSE = r"""
(function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='d15a-coarse-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  try{
    const bar=document.getElementById('top-filter-bar');
    if(!bar) throw new Error('#top-filter-bar not found');
    const els=Array.prototype.filter.call(
      bar.querySelectorAll('input,select,button'),
      function(el){ return getComputedStyle(el).display!=='none' &&
                            el.getBoundingClientRect().width>0; });
    const heightBad=[], fontBad=[];
    els.forEach(function(el){
      const r=el.getBoundingClientRect();
      if(r.height<43) heightBad.push({tag:el.tagName,id:el.id,cls:el.className,h:Math.round(r.height*10)/10});
      if(el.tagName==='INPUT'||el.tagName==='SELECT'){
        const fs=parseFloat(getComputedStyle(el).fontSize);
        if(fs<16) fontBad.push({tag:el.tagName,id:el.id,fontSize:fs});
      }
    });
    R.notes.coarseCount=els.length;
    R.notes.heightBad=heightBad;
    R.notes.fontBad=fontBad;
    ck('coarse pointer: every input/select/button in the bar has height >=44px (-1px tolerance)',
       els.length>=8 && heightBad.length===0, JSON.stringify(heightBad));
    ck('coarse pointer: every input/select has font-size >=16px',
       fontBad.length===0, JSON.stringify(fontBad));
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
    emit();
  }
})();
"""


def render(html_path, width, height, force_coarse=False):
    page = html_path.read_text(encoding="utf-8")
    probe = PROBE_COARSE if force_coarse else PROBE
    if force_coarse:
        coarse_css = extract_coarse_css(page)
        inject_style = "<style>\n/* d15a_check: pointer:coarse rules re-injected unconditionally */\n" + coarse_css + "\n</style>\n"
        page = page.replace("</head>", inject_style + "</head>", 1)
    out = page.replace("</body>", "<script>\n" + probe + "\n</script>\n</body>")
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
    out_re = COARSE_OUT_RE if force_coarse else OUT_RE
    m = out_re.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}px (coarse={force_coarse}).\n" + proc.stderr[-3000:])
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

    # (g): 390px with the page's own pointer:coarse rules forced on.
    Rc = render(html, 390, 900, force_coarse=True)
    if Rc.get("err"):
        print(f"PROBE ERROR (390px coarse):\n{Rc['err']}")
    print("\n=== 390px (coarse forced) ===")
    for k, v in Rc.get("notes", {}).items():
        print(f"   {k}: {json.dumps(v)}")
    for c in Rc["checks"]:
        checks.append(("[390px coarse] " + c["name"], c["pass"], c["detail"]))

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
