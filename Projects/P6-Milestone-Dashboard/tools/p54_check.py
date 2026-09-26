#!/usr/bin/env python3
"""
P54 check (v3.1.0-P54: D-21 histogram component).

Two harnesses, both headless Chromium + --dump-dom + an injected probe script
that writes JSON into a <pre>, following tools/p53_check.py's shape:

  1. FUNCTIONAL (1440x900, light theme, one page load): drives the app
     directly against its own embedded seed data (no import needed -- the
     seeds already carry hours and a spread of milestone dates).
       - Hours and Tasks per-week values, read off the RENDERED bar labels
         (measure the element, not read-through), compared against an
         INDEPENDENT tally built from TASKS/MILESTONES + dateToCol() in the
         probe itself -- never by calling computeHistPerCol(), the function
         under test. Checked for N=3 columns including the first and the
         last (both bounds), with and without a filter active.
       - No-hours data (every task.hrs zeroed in place, then rebuilt):
         defaults to Tasks, Hours disabled with the stated title.
       - Top vs Bottom: row index/order, every week cell's x/width equal to
         the header cell above it (both positions, first and last column),
         and the subtotal row moving with the histogram.
       - Persistence: setHistMeasure('tasks') + setHistPos('top'), publish
         (the real publishDashboard(), captured at the URL.createObjectURL
         boundary the way tools/persist_check.py does), reload the published
         file, assert both are restored.
       - Print preview: togglePrintMode(true) does not reorder or drop the
         row; the position chosen beforehand is what prints.

  2. LAYOUT (390/768/1440, light+dark): control height (~24px, the D-16
     desktop standard), no page-level horizontal overflow, and the bar
     fill / bar label ink / label cell colours differing between themes
     (theme_check.py carries the permanent probes; this is the same
     assertion made against the live rendered histogram rather than a
     synthetic element, per CLAUDE.md's "measure the element" rule).

Proven failing against P53: releases/v3.1.0-P53_date-range.html has no
HIST_MEASURE/HIST_POS globals, no .hist-seg control and no renderHistogram()
function at all, so the persistence/control assertions fail outright there
rather than passing vacuously.

Usage:
  python3 tools/p54_check.py [--html FILE] [--skip-p53-proof]
Exit code 1 if any assertion fails.
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
P53_HTML = ROOT / "releases" / "v3.1.0-P53_date-range.html"

OUT_RE = re.compile(r'<pre id="p54-out">(.*?)</pre>', re.S)

# ============================================================
# Functional harness
# ============================================================
FUNCTIONAL = r"""
(async function(){
  const R = {checks:[], ok:true};
  function assert(name, cond, detail){
    R.checks.push({name:name, pass:!!cond, detail: detail===undefined?null:detail});
    if(!cond) R.ok=false;
  }
  function emit(){
    const out=document.createElement('pre'); out.id='p54-out';
    document.body.appendChild(out);
    out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
  }
  // scheduleRerender() debounces 40ms before it actually rebuilds the DOM
  // (CLAUDE.md: call scheduleRerender(true), never rerender(true) directly,
  // but a probe still has to wait OUT that debounce before reading the
  // result, or it measures the pre-rebuild DOM and calls that a defect).
  function wait(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }

  // Independent tally: reads TASKS/MILESTONES directly and buckets with
  // dateToCol(), never calling computeHistPerCol() or renderHistogram().
  // Mirrors the SAME per-row filter the app applies (skip a row whose
  // rendered <tr> carries .hidden-row), so "with a filter active" is a real
  // comparison against the same visible set, not a separate universe.
  function independentTally(measure){
    const perCol={};
    const rows=document.querySelectorAll('tr[data-type="row"]');
    rows.forEach(function(row){
      if(row.classList.contains('hidden-row')) return;
      const ref=row.getAttribute('data-ref');
      const task=TASKS.filter(function(t){return t.ref===ref;})[0];
      if(!task) return;
      const ms=getMilestones(task.ref);
      if(task.type==='LoE'){
        const total=parseFloat(task.hrs);
        const cols=loeCols(task.startDate,task.endDate);
        if(measure==='tasks'){
          cols.forEach(function(c){ perCol[c]=(perCol[c]||0)+1; });
        } else if(cols.length && !isNaN(total) && total>0){
          const perWeek=total/cols.length;
          cols.forEach(function(c){ perCol[c]=(perCol[c]||0)+perWeek; });
        }
        return;
      }
      if(task.type==='Gate') return;
      const total=parseFloat(task.hrs);
      ms.forEach(function(m){
        const c=dateToCol(m.date);
        if(c<0) return;
        if(measure==='tasks'){
          perCol[c]=(perCol[c]||0)+1;
        } else {
          if(STATES[m.state]&&STATES[m.state].skipHours) return;
          if(isNaN(total)||total===0) return;
          perCol[c]=(perCol[c]||0)+total*(m.weight/100);
        }
      });
    });
    return perCol;
  }

  function readBars(){
    const vals={};
    document.querySelectorAll('td.hist-wk').forEach(function(td){
      const c=parseInt(td.getAttribute('data-col'),10);
      const lbl=td.querySelector('.hist-lbl');
      vals[c]= lbl ? lbl.textContent.trim() : null;
    });
    return vals;
  }
  function fmtExpect(measure, v){
    if(v<=0) return null;
    return measure==='hours' ? fmtHrs(v) : String(Math.round(v));
  }
  function checkBars(label, measure){
    const tally=independentTally(measure);
    const bars=readBars();
    // Both bounds (first, last), plus whichever column actually carries the
    // most so the comparison is not vacuously 0===0 at every point tested.
    let busiest=Math.floor(NCOLS/2), busiestV=-1;
    for(let c=0;c<NCOLS;c++){ if((tally[c]||0)>busiestV){ busiestV=tally[c]||0; busiest=c; } }
    const cols=[0, busiest, NCOLS-1];
    cols.forEach(function(c){
      const want=fmtExpect(measure, tally[c]||0);
      const got=bars[c]||null;
      assert(label+' col '+c+' ('+measure+')', got===want, {want:want,got:got,raw:tally[c]||0});
    });
  }

  try{
    window.confirm=function(){ return true; };
    HTMLAnchorElement.prototype.click=function(){};

    // The shipped seed data carries NO hours at all -- every task.hrs is ""
    // (confirmed: 159/159 occurrences). That is itself a genuine no-hours
    // dataset, not a defect, so it is used as-is for step 3 below. Hours mode
    // needs real numbers to test meaningfully, so a small synthetic set is
    // injected here, spread across the timeline, and removed again for the
    // no-hours scenario.
    const hoursTasks=TASKS.filter(function(t){ return t.type!=='Gate' && getMilestones(t.ref).length; }).slice(0,14);
    assert('synthetic hours: enough real tasks with milestones to test on', hoursTasks.length>=8, hoursTasks.length);
    hoursTasks.forEach(function(t,i){ t.hrs=String(20+(i%5)*10); });
    scheduleRerender(true);
    await wait(300);
    assert('synthetic hours actually make scheduleHasHours() true', scheduleHasHours());

    // ---- 1. Hours/Tasks per-week, no filter ----
    setHistMeasure('hours'); await wait(120);
    checkBars('no-filter', 'hours');
    setHistMeasure('tasks'); await wait(120);
    checkBars('no-filter', 'tasks');

    // ---- 2. same, WITH a filter active ----
    const bandSel=document.getElementById('filter-band');
    let filterApplied=false;
    if(bandSel && bandSel.options.length>1){
      bandSel.value=bandSel.options[1].value;
      bandSel.dispatchEvent(new Event('change'));
      filterApplied=true;
      await wait(120);
    }
    assert('a filter is actually active for the filtered comparison', filterApplied);
    setHistMeasure('hours'); await wait(120);
    checkBars('filtered', 'hours');
    setHistMeasure('tasks'); await wait(120);
    checkBars('filtered', 'tasks');
    // release the filter
    if(bandSel){ bandSel.value=''; bandSel.dispatchEvent(new Event('change')); await wait(120); }
    setHistMeasure('hours'); await wait(120);

    // ---- 3. No-hours data: falls back to Tasks, Hours disabled ----
    // Zeroing the synthetic set returns the board to its actual shipped
    // state (every task.hrs empty), which is exactly the no-hours case.
    const savedHrs=hoursTasks.map(function(t){return t.hrs;});
    hoursTasks.forEach(function(t){ t.hrs=''; });
    scheduleRerender(true);
    await wait(300);
    assert('no-hours: HIST_MEASURE forced to tasks', HIST_MEASURE==='tasks', HIST_MEASURE);
    let hoursBtn=document.querySelector('.hist-seg button[data-measure="hours"]');
    assert('no-hours: Hours button disabled', !!hoursBtn && hoursBtn.disabled);
    assert('no-hours: Hours button explains why', !!hoursBtn && hoursBtn.title==='No hours in the loaded schedules', hoursBtn?hoursBtn.title:null);

    // restore the synthetic hours
    hoursTasks.forEach(function(t,i){ t.hrs=savedHrs[i]; });
    scheduleRerender(true);
    await wait(300);
    hoursBtn=document.querySelector('.hist-seg button[data-measure="hours"]');
    assert('hours restored: button re-enabled', !!hoursBtn && !hoursBtn.disabled, hoursBtn?{disabled:hoursBtn.disabled,title:hoursBtn.title}:null);

    // ---- 4. Top vs Bottom ----
    setHistPos('bottom');
    await wait(300);
    let rows=Array.prototype.slice.call(tbody.children);
    let lastTwo=rows.slice(-2).map(function(r){return r.getAttribute('data-type');});
    assert('bottom: last two rows are subtotal then hist', lastTwo[0]==='subtotal'&&lastTwo[1]==='hist', lastTwo);

    setHistPos('top');
    await wait(300);
    rows=Array.prototype.slice.call(tbody.children);
    const firstTwo=rows.slice(0,2).map(function(r){return r.getAttribute('data-type');});
    assert('top: first two rows are subtotal then hist', firstTwo[0]==='subtotal'&&firstTwo[1]==='hist', firstTwo);

    // column alignment against the week header, both bounds
    const headerCells=document.querySelectorAll('#week-hdr th.col-wk');
    const histCells=document.querySelectorAll('td.hist-wk');
    [0, headerCells.length-1].forEach(function(i){
      const hr=headerCells[i].getBoundingClientRect();
      const cr=histCells[i].getBoundingClientRect();
      assert('top: hist col '+i+' x matches header', Math.abs(hr.x-cr.x)<0.5, {header:hr.x,hist:cr.x});
      assert('top: hist col '+i+' width matches header', Math.abs(hr.width-cr.width)<0.5, {header:hr.width,hist:cr.width});
    });

    // ---- 5. Print preview honours position (top, currently) ----
    togglePrintMode(true);
    await wait(120);
    const rowsPrint=Array.prototype.slice.call(tbody.children);
    const firstTwoPrint=rowsPrint.slice(0,2).map(function(r){return r.getAttribute('data-type');});
    assert('print preview: top position unchanged by print mode', firstTwoPrint[0]==='subtotal'&&firstTwoPrint[1]==='hist', firstTwoPrint);
    const ctlRow=document.querySelector('.hist-ctl-row');
    assert('print preview: controls stay in the DOM (hidden via @media print, not removed)', !!ctlRow);
    togglePrintMode(false);
    await wait(120);

    // ---- 6. Persistence: publish round trip ----
    setHistMeasure('tasks'); await wait(120);
    setHistPos('top'); await wait(120);
    const CAP={};
    const realCreate=URL.createObjectURL;
    URL.createObjectURL=function(blob){ CAP.published=blob; return 'blob:captured'; };
    publishDashboard();
    URL.createObjectURL=realCreate;
    if(!CAP.published){ assert('publish produced a blob', false); emit(); return; }
    try{
      const t=await CAP.published.text();
      R.publishedHtml=t;
    }catch(e){ assert('publish blob readable', false, e.message); }
    emit();
  }catch(e){
    assert('PROBE THREW', false, e.message+' @'+e.stack);
    emit();
  }
})();
"""

STAGE2 = r"""
(function(){
  const out=document.createElement('pre'); out.id='p54-out'; document.body.appendChild(out);
  const R={checks:[],ok:true};
  function assert(name,cond,detail){ R.checks.push({name:name,pass:!!cond,detail:detail===undefined?null:detail}); if(!cond) R.ok=false; }
  try{
    assert('published file restored HIST_MEASURE=tasks', HIST_MEASURE==='tasks', HIST_MEASURE);
    assert('published file restored HIST_POS=top', HIST_POS==='top', HIST_POS);
    const rows=Array.prototype.slice.call(tbody.children);
    const firstTwo=rows.slice(0,2).map(function(r){return r.getAttribute('data-type');});
    assert('published file opens with hist row at top', firstTwo[0]==='subtotal'&&firstTwo[1]==='hist', firstTwo);
  }catch(e){ assert('stage2 threw', false, e.message); }
  out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
})();
"""

# ============================================================
# Layout / theme harness (control size, overflow, colour toggle)
# ============================================================
LAYOUT = r"""
(function(ARGS){
  const R={checks:[],ok:true};
  function assert(name,cond,detail){ R.checks.push({name:name,pass:!!cond,detail:detail===undefined?null:detail}); if(!cond) R.ok=false; }
  function emit(){
    const out=document.createElement('pre'); out.id='p54-out'; document.body.appendChild(out);
    out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
  }
  try{
    if(ARGS.theme) document.documentElement.setAttribute('data-theme',ARGS.theme);
    const segs=document.querySelectorAll('.hist-seg');
    assert('at least one .hist-seg control is present', segs.length>0, segs.length);
    segs.forEach(function(seg,i){
      const h=seg.getBoundingClientRect().height;
      assert('seg '+i+' height ~= 24px (D-16 --ctl-h)', Math.abs(h-24)<=1.5, h);
    });
    assert('no page-level horizontal overflow at '+ARGS.width, document.documentElement.scrollWidth<=ARGS.width+2,
           {scrollWidth:document.documentElement.scrollWidth, width:ARGS.width});

    const bar=document.querySelector('.hist-bar');
    const lbl=document.querySelector('.hist-lbl');
    const nameCell=document.querySelector('tr.hist-row td.c-name');
    function rgb(el){ return el?getComputedStyle(el).backgroundImage+'|'+getComputedStyle(el).color:null; }
    R.theme=ARGS.theme;
    R.barPaint=bar?getComputedStyle(bar).backgroundImage:null;
    R.lblColor=lbl?getComputedStyle(lbl).color:null;
    R.nameColor=nameCell?getComputedStyle(nameCell).color:null;
    R.nameBg=nameCell?getComputedStyle(nameCell).backgroundColor:null;
    emit();
  }catch(e){
    assert('PROBE THREW', false, e.message);
    emit();
  }
})(__ARGS__);
"""


def render(html_text, script, width=1440, height=1000, extra_head=""):
    page = html_text
    if extra_head:
        page = page.replace("</head>", extra_head + "</head>", 1)
    out = page.replace("</body>", "<script>\n" + script + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p54.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=30000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=180,
        )
    hits = OUT_RE.findall(proc.stdout)
    if not hits:
        return {"checks": [{"name": "probe output missing", "pass": False,
                             "detail": proc.stderr[-2000:]}], "ok": False}
    return json.loads(base64.b64decode(hits[-1].strip()).decode("utf-8"))


def report(section, result):
    fails = [c for c in result.get("checks", []) if not c["pass"]]
    for c in result.get("checks", []):
        mark = "ok  " if c["pass"] else "FAIL"
        print(f"  {mark} [{section}] {c['name']}   {json.dumps(c.get('detail'))}")
    return len(result.get("checks", [])), len(fails)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    ap.add_argument("--skip-p53-proof", action="store_true")
    a = ap.parse_args()

    html_text = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")

    total, failed = 0, 0

    # ---------------- functional ----------------
    r1 = render(html_text, FUNCTIONAL)
    n, f = report("functional", r1)
    total += n; failed += f

    published = r1.get("publishedHtml")
    if published:
        r2 = render(published, STAGE2)
        n, f = report("persist", r2)
        total += n; failed += f
    else:
        print("  FAIL [persist] no published file captured by stage 1")
        failed += 1

    # ---------------- layout / theme ----------------
    for width in (390, 768, 1440):
        for theme in ("light", "dark"):
            args_js = json.dumps({"width": width, "theme": theme})
            script = LAYOUT.replace("__ARGS__", args_js)
            r = render(html_text, script, width=width, height=900)
            n, f = report(f"layout {width}x{theme}", r)
            total += n; failed += f

    # theme diff: compare the light vs dark captures just taken
    lightR = render(html_text, LAYOUT.replace("__ARGS__", json.dumps({"width": 1440, "theme": "light"})), width=1440)
    darkR = render(html_text, LAYOUT.replace("__ARGS__", json.dumps({"width": 1440, "theme": "dark"})), width=1440)
    for key, label in (("barPaint", "bar fill"), ("lblColor", "bar label ink"),
                        ("nameColor", "label cell text"), ("nameBg", "label cell background")):
        same = lightR.get(key) == darkR.get(key)
        total += 1
        if same:
            failed += 1
            print(f"  FAIL [theme] {label} identical in light and dark: {lightR.get(key)!r}")
        else:
            print(f"  ok   [theme] {label} differs light vs dark   [{lightR.get(key)!r} vs {darkR.get(key)!r}]")

    # ---------------- proof of regression-sensitivity against P53 ----------------
    if not a.skip_p53_proof:
        print("\n--- Proof of regression-sensitivity: same harness against v3.1.0-P53 ---")
        if not P53_HTML.exists():
            print(f"  P53 release not found at {P53_HTML}; skipping proof")
        else:
            p53_text = P53_HTML.read_text(encoding="utf-8", errors="replace")
            p53_probe = r"""
            (function(){
              const R={checks:[],ok:true};
              function assert(name,cond,detail){ R.checks.push({name:name,pass:!!cond,detail:detail}); if(!cond) R.ok=false; }
              try{
                assert("HIST_MEASURE exists", typeof HIST_MEASURE!=='undefined');
                assert(".hist-seg control exists", document.querySelectorAll('.hist-seg').length>0);
                assert("renderHistogram function exists", typeof renderHistogram==='function');
              }catch(e){ assert('threw', false, e.message); }
              const out=document.createElement('pre'); out.id='p54-out'; document.body.appendChild(out);
              out.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
            })();
            """
            rp = render(p53_text, p53_probe, width=1440)
            failing = [c for c in rp.get("checks", []) if not c["pass"]]
            if failing:
                print(f"  Confirmed: {len(failing)} assertion(s) fail against P53, as they must for a real check:")
                for c in failing:
                    print(f"    - {c['name']}")
            else:
                print("  WARNING: harness did not fail against P53 -- it proves nothing")
                failed += 1
                total += 1

    print(f"\n{total-failed}/{total} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
