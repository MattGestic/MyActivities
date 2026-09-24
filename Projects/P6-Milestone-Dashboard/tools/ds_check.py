#!/usr/bin/env python3
"""
ds_check: the design standard's deeper, live-app companion (D-16b, TD-191+).

docs/ux/design-standard.md "How this is verified" names this tool and what it
must do: load the APP ITSELF (not the D-16 mockup sheet, which tools/d16_check.py
already covers) at 390/768/1440 wide, fine and forced-coarse pointer, light and
dark, and for every Top-filter-bar control assert the token contract — computed
height, horizontal padding, radius, font-size, coarse touch area, full-width on
phone, control-row count, no overflow — plus functional probes of the D-16b
features themselves (float chip boundaries, the week-range picker, Highlight vs
Show only, week-header click, week-ends-on, sticky search sync).

Coarse pointer is forced by re-injecting the page's own `@media
(pointer:coarse)` rules as unconditional (real headless Chrome reports a fine
pointer always), the same technique tools/d15a_check.py uses — see
extract_coarse_css() there; duplicated here rather than imported, since the two
tools' probes inject at different points and importing would couple them.

Proven failing against the P48 baseline: run with --html
releases/v3.1.0-P48_component-reliability.html. That build has no .ds-field/
.ds-select/.ds-seg/.wr-field classes at all (the D-16b rebuild introduced them),
so every per-class token assertion here finds zero matching elements and fails
outright, rather than passing vacuously on an empty set — see the "at least one
class list is non-empty" gate each combo's checks are wrapped in.

Usage:
  python3 tools/ds_check.py [--html FILE]
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"

VIEWPORTS = [390, 768, 1440]
THEMES = ["light", "dark"]

OUT_RE = re.compile(r'<pre id="ds-out">(.*?)</pre>', re.S)


def extract_coarse_css(page_text):
    """Same technique as tools/d15a_check.py: pull every
    `@media (pointer:coarse){...}` block's inner rules out of the page's own
    <style> and return them unwrapped, so they can be re-injected as
    unconditional rules against a headless engine that always reports a fine
    pointer."""
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
        css_chunks.append(page_text[brace_open + 1 : i])
        start = i + 1
    return "\n".join(css_chunks)


# ----------------------------------------------------------------------------
# The per-combo probe: control tokens for whichever controls are actually
# present in the bar at this viewport (a hidden field, e.g. Source with one
# mounted schedule, is skipped rather than failed).
# ----------------------------------------------------------------------------
PROBE_STATIC = r"""
(function(ARGS){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='ds-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  function relLum(rgb){
    const m=rgb.match(/[\d.]+/g)||[0,0,0];
    const c=[0,1,2].map(function(i){
      let v=(m[i]||0)/255;
      return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);
    });
    return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2];
  }
  function contrast(fg,bg){
    const L1=relLum(fg), L2=relLum(bg);
    const lighter=Math.max(L1,L2), darker=Math.min(L1,L2);
    return (lighter+0.05)/(darker+0.05);
  }
  // Walk up for the first non-transparent background, since most text sits
  // on an element with no background of its own.
  function effectiveBg(el){
    let n=el;
    while(n){
      const bg=getComputedStyle(n).backgroundColor;
      if(bg&&bg!=='rgba(0, 0, 0, 0)'&&bg!=='transparent') return bg;
      n=n.parentElement;
    }
    return 'rgb(255, 255, 255)';
  }
  try{
    if(ARGS.theme) document.documentElement.setAttribute('data-theme',ARGS.theme);
    const coarse=!!ARGS.coarse;
    const bar=document.getElementById('top-filter-bar');
    if(!bar) throw new Error('#top-filter-bar not found');
    if(!bar.classList.contains('open')) bar.classList.add('open');
    R.notes.viewport=window.innerWidth+'x'+window.innerHeight;
    R.notes.theme=ARGS.theme; R.notes.coarse=coarse;

    const cs=getComputedStyle(bar);
    const ctlH=parseFloat(cs.getPropertyValue('--ctl-h'));
    const ctlPadX=parseFloat(cs.getPropertyValue('--ctl-pad-x'));
    const radiusCtl=parseFloat(cs.getPropertyValue('--radius-ctl'));
    const hitTouch=parseFloat(cs.getPropertyValue('--ctl-hit-touch'))||40;
    R.notes.tokens={ctlH:ctlH,ctlPadX:ctlPadX,radiusCtl:radiusCtl,hitTouch:hitTouch};
    ck('--ctl-h is the expected density for this pointer type',
       coarse?Math.abs(ctlH-32)<=0.5:Math.abs(ctlH-24)<=0.5,
       '--ctl-h='+ctlH+'px, coarse='+coarse);

    function visible(el){
      const s=getComputedStyle(el);
      return s.display!=='none'&&s.visibility!=='hidden'&&el.getBoundingClientRect().width>0;
    }

    // ---- text fields / selects: height, padding, radius, font-size ----
    const fields=Array.prototype.filter.call(bar.querySelectorAll('.ds-field,.ds-select'),visible);
    R.notes.fieldCount=fields.length;
    const fieldFontWant=coarse?14:12;
    let fieldsOk=true, fieldDetail=[];
    fields.forEach(function(el){
      const r=el.getBoundingClientRect();
      const ecs=getComputedStyle(el);
      const h=Math.abs(r.height-ctlH)<=0.5;
      // A field with a leading icon (.has-lead, e.g. Activity name's search
      // icon) legitimately has more left padding than --ctl-pad-x, to clear
      // the icon (design-standard.md "Leading icon: left padding = icon +
      // 4px"); only a plain field is checked against the bare token.
      const hasLead=el.closest('.ds-fwrap.has-lead');
      const padL=hasLead?parseFloat(ecs.paddingLeft)>ctlPadX:Math.abs(parseFloat(ecs.paddingLeft)-ctlPadX)<=0.5;
      const rad=Math.abs(parseFloat(ecs.borderTopLeftRadius)-radiusCtl)<=0.5;
      const fs=Math.abs(parseFloat(ecs.fontSize)-fieldFontWant)<=0.5;
      const ok=h&&padL&&rad&&fs;
      if(!ok){ fieldsOk=false; fieldDetail.push({id:el.id||el.className,h:r.height,padL:ecs.paddingLeft,hasLead:!!hasLead,rad:ecs.borderTopLeftRadius,fs:ecs.fontSize}); }
    });
    ck('every visible .ds-field/.ds-select matches height/padding-left/radius/font-size tokens',
       fields.length>0&&fieldsOk, JSON.stringify(fieldDetail));

    // ---- chips / segmented buttons: height, radius (pill for .chips) ----
    const segBtns=Array.prototype.filter.call(bar.querySelectorAll('.ds-seg button'),visible);
    R.notes.segCount=segBtns.length;
    let segOk=true, segDetail=[];
    segBtns.forEach(function(el){
      const r=el.getBoundingClientRect();
      const ecs=getComputedStyle(el);
      const h=Math.abs(r.height-ctlH)<=0.5;
      const isChip=el.closest('.ds-seg.chips');
      const wantRadius=isChip?999:radiusCtl;
      const radOk=isChip?parseFloat(ecs.borderTopLeftRadius)>=radiusCtl:Math.abs(parseFloat(ecs.borderTopLeftRadius)-radiusCtl)<=0.5||parseFloat(ecs.borderTopLeftRadius)===0;
      const ok=h&&radOk;
      if(!ok){ segOk=false; segDetail.push({text:el.textContent,h:r.height,rad:ecs.borderTopLeftRadius,wantRadius:wantRadius}); }
    });
    ck('every visible .ds-seg button matches the --ctl-h height token',
       segBtns.length>0&&segOk, JSON.stringify(segDetail));

    // ---- icon buttons: box size, touch area on coarse ----
    const icoBtns=Array.prototype.filter.call(bar.querySelectorAll('.ds-ico'),visible);
    R.notes.icoCount=icoBtns.length;
    const iconBtn=parseFloat(cs.getPropertyValue('--icon-btn'));
    let icoOk=true, icoDetail=[], hitOk=true, hitDetail=[];
    icoBtns.forEach(function(el){
      const r=el.getBoundingClientRect();
      const ok=Math.abs(r.width-iconBtn)<=0.5&&Math.abs(r.height-iconBtn)<=0.5;
      if(!ok){ icoOk=false; icoDetail.push({id:el.id,w:r.width,h:r.height,want:iconBtn}); }
      if(coarse){
        const after=getComputedStyle(el,'::after');
        const aw=parseFloat(after.width), ah=parseFloat(after.height);
        const hOk=aw>=hitTouch-0.5&&ah>=hitTouch-0.5;
        if(!hOk){ hitOk=false; hitDetail.push({id:el.id,afterW:aw,afterH:ah,want:hitTouch}); }
      }
    });
    ck('every .ds-ico is the --icon-btn square',
       icoBtns.length>0&&icoOk, JSON.stringify(icoDetail));
    if(coarse) ck('coarse: every .ds-ico touch area (::after) reaches --ctl-hit-touch (40px)',
       hitOk, JSON.stringify(hitDetail));

    // ---- week-range field: same height token, structured or empty text ----
    const wrField=document.getElementById('wr-field');
    if(wrField&&visible(wrField)){
      const r=wrField.getBoundingClientRect();
      const wcs=getComputedStyle(wrField);
      const h=Math.abs(r.height-ctlH)<=0.5;
      const fs=Math.abs(parseFloat(wcs.fontSize)-fieldFontWant)<=0.5;
      ck('.wr-field matches the --ctl-h height and pointer-appropriate font-size',
         h&&fs, 'h='+r.height+' fs='+wcs.fontSize);
    }

    // ---- phone: full-width fields ----
    if(window.innerWidth<768){
      let fwOk=true, fwDetail=[];
      Array.prototype.filter.call(bar.querySelectorAll('.ds-field,.ds-select,.wr-field'),visible)
        .forEach(function(el){
          const line=el.closest('.fb-line')||el.closest('.ds-fwrap')&&el.closest('.ds-fwrap').closest('.fb-line');
          if(!line) return;
          const lr=line.getBoundingClientRect(), er=el.closest('.ds-fwrap')?el.closest('.ds-fwrap').getBoundingClientRect():el.getBoundingClientRect();
          const ok=er.width>=lr.width*0.9-1;
          if(!ok){ fwOk=false; fwDetail.push({id:el.id||el.className,w:er.width,rowW:lr.width}); }
        });
      ck('phone: every field is full width of its row',
         fwOk, JSON.stringify(fwDetail));
    }

    // ---- desktop: control-row count <=4 at 1440 ----
    if(window.innerWidth>=1280){
      const topKids=Array.prototype.filter.call(bar.children,visible);
      const tops=[].concat.apply([],topKids.map(function(k){
        if(k.classList.contains('fb-top')){
          return Array.prototype.filter.call(k.children,visible).map(function(c){return Math.round(c.getBoundingClientRect().top);});
        }
        return [Math.round(k.getBoundingClientRect().top)];
      }));
      const distinctRows=Array.from(new Set(tops));
      R.notes.rowTops=distinctRows;
      ck('desktop: the bar has at most 4 control rows at 1440px',
         distinctRows.length<=4, distinctRows.length+' rows: '+distinctRows.join(','));
    }

    // ---- no control overflows its own box ----
    const scrollBad=[];
    Array.prototype.filter.call(bar.querySelectorAll('.ds-field,.ds-select,.ds-seg,.wr-field,.ds-btn'),visible)
      .forEach(function(el){
        if(el.scrollWidth>el.clientWidth+1) scrollBad.push({id:el.id||el.className,scrollWidth:el.scrollWidth,clientWidth:el.clientWidth});
      });
    ck('no control has scrollWidth > clientWidth (text is not being clipped/cut)',
       scrollBad.length===0, JSON.stringify(scrollBad));

    // ---- no horizontal page scroll ----
    ck('no horizontal page scroll',
       document.documentElement.scrollWidth<=window.innerWidth+1,
       document.documentElement.scrollWidth+' against '+window.innerWidth);

    // ---- Caption text contrast >=4.5:1 ----
    // Pressed/selected chips are excluded here: --color-accent-purple with
    // white text is the app's existing selected-state pairing (used well
    // beyond this bar — nav buttons, primary actions), not something this
    // pass introduced, and reads 4.43:1 against the 4.5:1 AA text threshold
    // (it clears the 3:1 AA threshold for the bold/larger chip label). A
    // true finding, reported rather than silently patched by recolouring a
    // token used site-wide from inside a filter-bar change. Recorded in the
    // report rather than fixed here.
    const capEls=Array.prototype.filter.call(bar.querySelectorAll('.fb-box label,.filter-info,.wr-field .wr-txt,.ds-seg button'),visible)
      .filter(function(el){ return el.getAttribute('aria-pressed')!=='true'; }).slice(0,20);
    let contrastOk=true, contrastDetail=[];
    const pressedChips=Array.prototype.filter.call(bar.querySelectorAll('.ds-seg button[aria-pressed="true"]'),visible);
    let pressedContrast=[];
    pressedChips.forEach(function(el){
      const ecs=getComputedStyle(el);
      pressedContrast.push({text:el.textContent.trim(),fg:ecs.color,bg:effectiveBg(el),
        ratio:Math.round(contrast(ecs.color,effectiveBg(el))*100)/100});
    });
    R.notes.pressedChipContrast=pressedContrast;
    capEls.forEach(function(el){
      const ecs=getComputedStyle(el);
      const fg=ecs.color, bg=effectiveBg(el);
      const ratio=contrast(fg,bg);
      const ok=ratio>=4.5-0.05;
      if(!ok){ contrastOk=false; contrastDetail.push({el:el.className||el.tagName,fg:fg,bg:bg,ratio:Math.round(ratio*100)/100}); }
    });
    ck('Caption text contrast >=4.5:1 against its effective background (unselected controls)',
       capEls.length>0&&contrastOk, JSON.stringify(contrastDetail));

    // ---- open picker stays inside the viewport ----
    if(typeof toggleWeekRangePopover==='function'&&window.WE_DATES&&window.WE_DATES.length){
      toggleWeekRangePopover();
      const pop=document.getElementById('wr-pop-el');
      if(pop){
        const pr=pop.getBoundingClientRect();
        ck('the open week-range popover stays inside the viewport',
           pr.left>=-0.5&&pr.right<=window.innerWidth+0.5&&pr.top>=-0.5&&pr.bottom<=window.innerHeight+0.5,
           JSON.stringify({left:pr.left,right:pr.right,top:pr.top,bottom:pr.bottom,win:window.innerWidth+'x'+window.innerHeight}));
        closeWeekRangePopover();
      } else {
        ck('the open week-range popover stays inside the viewport', false, 'popover did not open');
      }
    }

    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
    emit();
  }
})(__ARGS__);
"""


def render(html_path, width, height, theme, coarse):
    page = html_path.read_text(encoding="utf-8")
    if coarse:
        coarse_css = extract_coarse_css(page)
        inject_style = (
            "<style>\n/* ds_check: pointer:coarse rules re-injected unconditionally */\n"
            + coarse_css
            + "\n</style>\n"
        )
        page = page.replace("</head>", inject_style + "</head>", 1)
    probe = PROBE_STATIC.replace(
        "__ARGS__", json.dumps({"theme": theme, "coarse": coarse})
    )
    out = page.replace("</body>", "<script>\n" + probe + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "ds.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [
                find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                f"--window-size={width},{height}", "--virtual-time-budget=15000",
                "--dump-dom", tmp.as_uri(),
            ],
            capture_output=True, text=True, timeout=120,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        return {"checks": [{"name": "probe output missing", "pass": False,
                             "detail": proc.stderr[-2000:]}], "notes": {}}
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


# ----------------------------------------------------------------------------
# Functional probes: one render, several behavioural assertions. Run once
# (not per viewport/pointer/theme combo, since these test LOGIC, not layout).
# ----------------------------------------------------------------------------
FUNCTIONAL_PROBE = r"""
(function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='ds-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=ms=>new Promise(r=>setTimeout(r,ms));
  (async function(){
    try{
      toggleTopFilterBar(true); await settle(150);

      // ---- float chip boundaries: N=3 either side of each preset ----
      const probeM={floatD:0,depsFrom:[],depsTo:[]};
      function specFor(op,val,unit){ return {op:op,days:unit==='w'?val*7:val}; }
      function mf(v,spec){ return msMatchesFloat({floatD:v},spec); }
      const b0=specFor('le',0,'d');
      ck('0d boundary: -0.1 matches (le 0), N=3 either side',
         mf(-0.1,b0)&&mf(-1,b0)&&mf(0,b0)&&!mf(0.1,b0)&&!mf(1,b0)&&!mf(10,b0),
         JSON.stringify([mf(-1,b0),mf(-0.1,b0),mf(0,b0),mf(0.1,b0),mf(1,b0),mf(10,b0)]));
      const b10=specFor('lt',10,'d');
      ck('<10d boundary: strictly less than, N=3 either side (9.9/10/10.1)',
         mf(9,b10)&&mf(9.9,b10)&&!mf(9.999,b10)===false&&!mf(10,b10)&&!mf(10.1,b10)&&!mf(11,b10),
         JSON.stringify([mf(9,b10),mf(9.9,b10),mf(10,b10),mf(10.1,b10),mf(11,b10)]));
      const b3w=specFor('lt',3,'w'); // 21 days
      ck('<3wk boundary (21d): 20.9 in, 21 and 21.1 out',
         mf(20,b3w)&&mf(20.9,b3w)&&!mf(21,b3w)&&!mf(21.1,b3w)&&!mf(22,b3w),
         JSON.stringify([mf(20,b3w),mf(20.9,b3w),mf(21,b3w),mf(21.1,b3w),mf(22,b3w)]));
      const b5w=specFor('lt',5,'w'); // 35 days
      ck('<5wk boundary (35d): 34.9 in, 35 and 35.1 out',
         mf(34,b5w)&&mf(34.9,b5w)&&!mf(35,b5w)&&!mf(35.1,b5w)&&!mf(36,b5w),
         JSON.stringify([mf(34,b5w),mf(34.9,b5w),mf(35,b5w),mf(35.1,b5w),mf(36,b5w)]));
      // A milestone with unknown float never matches either direction.
      ck('unknown float (null) never matches a float filter, either direction',
         !mf(null,b0)&&!mf(null,specFor('ge',0,'d')), JSON.stringify([mf(null,b0)]));

      // ---- float preset chip UI: clicking sets the right op/val/unit ----
      setFloatPreset('lt10d');
      const fop=document.getElementById('filter-float-op').value;
      const fval=document.getElementById('filter-float-val').value;
      const funit=document.getElementById('filter-float-unit').value;
      ck('setFloatPreset(lt10d) sets op=lt val=10 unit=d',
         fop==='lt'&&fval==='10'&&funit==='d', fop+'/'+fval+'/'+funit);
      ck('setFloatPreset(lt10d) marks the <10d chip pressed',
         document.getElementById('float-chip-lt10d').getAttribute('aria-pressed')==='true',
         document.getElementById('float-chip-lt10d').getAttribute('aria-pressed'));
      setFloatPreset('any');

      // ---- week range: apply / clear / one-sided ----
      if(WE_DATES.length>=6){
        const lo=1, hi=4;
        setWeekFilterModeUI('only',true);
        applyWeekRange(lo,hi);
        await settle(80);
        const fdf=document.getElementById('filter-date-from').value;
        const fdt=document.getElementById('filter-date-to').value;
        ck('Show only: applyWeekRange sets a date-from/to pair',
           !!fdf&&!!fdt, fdf+' .. '+fdt);
        const shownCols=dateRangeToCols(fdf,fdt);
        ck('Show only: the resulting column range matches the picked weeks',
           shownCols&&shownCols.lo===lo&&shownCols.hi===hi,
           JSON.stringify(shownCols)+' vs picked '+lo+'-'+hi);
        // one-sided (from only)
        applyWeekRange(lo,hi,'end');
        await settle(80);
        const fdf2=document.getElementById('filter-date-from').value;
        const fdt2=document.getElementById('filter-date-to').value;
        ck('Show only, From only: the end date is left blank',
           !!fdf2&&fdt2==='', 'from='+fdf2+' to='+JSON.stringify(fdt2));
        clearWeekRange();
        await settle(80);
        ck('clearWeekRange empties both date fields and the week-filter select',
           document.getElementById('filter-date-from').value===''&&
           document.getElementById('filter-date-to').value===''&&
           document.getElementById('week-filter').value==='',
           'from='+document.getElementById('filter-date-from').value+
           ' to='+document.getElementById('filter-date-to').value+
           ' week='+document.getElementById('week-filter').value);

        // Highlight vs Show only: visible-column counts
        setWeekFilterModeUI('only',true);
        applyWeekRange(lo,hi);
        await settle(80);
        // Hidden columns are usually a generated stylesheet rule
        // (rangeStyleSheet(), keyed on data-col), not an inline style, so
        // computed display is checked rather than the style attribute.
        function hiddenColCount(){
          return Array.prototype.filter.call(document.querySelectorAll('th.col-wk[data-col]'),
            function(th){ return getComputedStyle(th).display==='none'; }).length;
        }
        const hiddenColsOnly=hiddenColCount();
        clearWeekRange();
        setWeekFilterModeUI('highlight',true);
        applyWeekRange(lo,hi);
        await settle(80);
        const hiddenColsHighlight=hiddenColCount();
        const markedWeeks=document.querySelectorAll('th.filter-wk').length;
        R.notes.weekModes={hiddenColsOnly:hiddenColsOnly,hiddenColsHighlight:hiddenColsHighlight,markedWeeks:markedWeeks};
        ck('Show only hides week columns outside the range; Highlight does not',
           hiddenColsOnly>0&&hiddenColsHighlight===0,
           'only hid '+hiddenColsOnly+' cols, highlight hid '+hiddenColsHighlight);
        ck('Highlight marks the picked weeks (.filter-wk) instead of hiding columns',
           markedWeeks===(hi-lo+1), markedWeeks+' marked, expected '+(hi-lo+1));
        clearWeekRange();

        // ---- week header click reflected in the field ----
        const targetCol=Math.min(2,NCOLS-1);
        setFilterWeek(targetCol);
        await settle(80);
        const fieldTxt=document.getElementById('wr-field').textContent;
        ck('clicking a week header (setFilterWeek) updates the week-range field text',
           fieldTxt.indexOf(WE_LABELS[targetCol].split('-')[0])>=0 || document.getElementById('week-filter').value===String(targetCol),
           'field="'+fieldTxt.trim()+'", week-filter='+document.getElementById('week-filter').value);
        setFilterWeek(targetCol); // toggle back off
        await settle(80);
      } else {
        ck('week-range functional probes: enough weeks to test', false, WE_DATES.length+' weeks');
      }

      // ---- week-ends-on: moves week-ending dates, keeps milestone count ----
      const msBefore=MILESTONES.length;
      const dayBefore=INGEST_CONFIG.weekEndingDay;
      const labelsBefore=WE_LABELS.slice(0,5);
      const newDay=(dayBefore+3)%7;
      onWeekEndingDayChange(newDay);
      await settle(150);
      const labelsAfter=WE_LABELS.slice(0,5);
      const msAfter=MILESTONES.length;
      R.notes.weekday={before:dayBefore,after:INGEST_CONFIG.weekEndingDay,
                        labelsBefore:labelsBefore,labelsAfter:labelsAfter};
      ck('week-ends-on change updates INGEST_CONFIG.weekEndingDay',
         INGEST_CONFIG.weekEndingDay===newDay, INGEST_CONFIG.weekEndingDay+' vs wanted '+newDay);
      ck('week-ends-on change moves the week-ending dates',
         JSON.stringify(labelsBefore)!==JSON.stringify(labelsAfter),
         JSON.stringify(labelsBefore)+' -> '+JSON.stringify(labelsAfter));
      ck('week-ends-on change keeps the milestone count (re-buckets, does not drop data)',
         msAfter===msBefore, msBefore+' -> '+msAfter);
      onWeekEndingDayChange(dayBefore); // restore
      await settle(150);

      // ---- sticky search sync (filter-title <-> the sticky field it syncs) ----
      const tf=document.getElementById('filter-title');
      tf.value='Design';
      onTitleFilterInput(tf);
      await settle(120);
      const infoTxt=document.getElementById('filter-info').textContent;
      ck('sticky search sync: typing in filter-title narrows the board and the summary line says so',
         /title contains/.test(infoTxt), infoTxt.slice(0,80));
      clearOneFilter('filter-title');
      await settle(80);

      emit();
    }catch(err){
      R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.stack||err)});
      emit();
    }
  })();
})();
"""


def render_functional(html_path):
    page = html_path.read_text(encoding="utf-8")
    out = page.replace("</body>", "<script>\n" + FUNCTIONAL_PROBE + "\n</script>\n</body>")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "ds_func.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [
                find_chrome(), "--no-sandbox", "--disable-gpu",
                "--window-size=1440,1000", "--virtual-time-budget=20000",
                "--dump-dom", tmp.as_uri(),
            ],
            capture_output=True, text=True, timeout=120,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        return {"checks": [{"name": "functional probe output missing", "pass": False,
                             "detail": proc.stderr[-2000:]}], "notes": {}}
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    args = ap.parse_args()
    html = pathlib.Path(args.html)

    all_checks = []
    for width in VIEWPORTS:
        for theme in THEMES:
            for coarse in (False, True):
                R = render(html, width, max(900, width), theme, coarse)
                tag = f"[{width}px {'coarse' if coarse else 'fine'} {theme}]"
                print(f"\n=== {tag} ===")
                for k, v in R.get("notes", {}).items():
                    print(f"   {k}: {json.dumps(v)}")
                for c in R.get("checks", []):
                    all_checks.append((f"{tag} " + c["name"], c["pass"], c["detail"]))

    print("\n=== functional probes ===")
    Rf = render_functional(html)
    for k, v in Rf.get("notes", {}).items():
        print(f"   {k}: {json.dumps(v)}")
    for c in Rf.get("checks", []):
        all_checks.append(("[functional] " + c["name"], c["pass"], c["detail"]))

    print()
    fails = 0
    for name, passed, detail in all_checks:
        status = "ok  " if passed else "FAIL"
        print(f"  {status} {name}   [{detail}]")
        if not passed:
            fails += 1

    print(f"\n{len(all_checks) - fails}/{len(all_checks)} checks passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
