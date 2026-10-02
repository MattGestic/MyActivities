#!/usr/bin/env python3
"""
p69_check: Start and Finish as date fields with a picker, and the A flag
(P69, Matt 2026-10-01). Also the row-health dot colours (a stray quote had
dropped the h-3 and h-4 rules since P42).

Drives the real card in headless Chrome:
  - the Start and Finish fields are the picker's triggers (P75 moved it off
    the calendar buttons in the labels); the picker opens on the field's own
    date, inside the viewport, with Actual UNticked by default;
  - a pick unticked writes a forecast date (no A, not green); ticked writes
    "<date> A" and the field turns green at once;
  - saving records the date and the flag as one entry (actual / startActual),
    projected to the board (m.actual) and shown on reopen; unticking an actual
    back to the schedule's forecast clears the override; Clear restores the
    schedule date;
  - month navigation, arrow keys, PageDown, Alt+Down, Esc (picker first, then
    the card), a click elsewhere in the card closes only the picker, and a
    touch tap opens the picker instead of the keyboard;
  - P6 suffixes: "A" means actual, "*" is kept and ignored.
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

OUT_RE = re.compile(r'<pre id="p69-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900), (390, 844)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p69-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const gap=()=>new Promise(r=>setTimeout(r,420));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog'), dp=()=>$('ms-dp');
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const open=async function(id){
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    await gap(); wrapOf(id).click(); await settle();
    if(dlg().hidden) throw new Error('card did not open for '+id);
  };
  const colorOf=v=>{ const sp=document.createElement('span'); sp.style.color='var('+v+')'; document.body.appendChild(sp); const c=getComputedStyle(sp).color; sp.remove(); return c; };
  const bgOf=v=>{ const sp=document.createElement('span'); sp.style.background='var('+v+')'; document.body.appendChild(sp); const c=getComputedStyle(sp).backgroundColor; sp.remove(); return c; };
  const day=iso=>dp().querySelector('.ms-dp-day[data-iso="'+iso+'"]');
  const addDays=(iso,n)=>{ const d=new Date(+iso.slice(0,4),+iso.slice(5,7)-1,+iso.slice(8,10)+n); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); };
  let f0x=null;
  const msEntries=k=>ENTRIES.filter(e=>e.target.kind==='ms'&&e.target.key===k);
  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    const GREEN=colorOf('--color-status-done');
    // A forecast finish with a real start, on the board.
    const F=MILESTONES.find(m=>!m.actual&&m.start&&wrapOf(msId(m))&&!m.startActual);
    const FS=MILESTONES.find(m=>!m.actual&&wrapOf(msId(m))&&m!==F);
    ck('sample: a forecast milestone on the board', !!F, F?msId(F):'none');
    const A=msId(F), key=msKeyFor(F);
    R.notes.sample=A;

    // ===== 1. Controls =====
    await open(A);
    // P75: the trigger is the field itself; the label buttons are gone.
    const bS=$('ms-start-date'), bF=$('ms-date');
    ck('trigger: the Start and Finish fields open the picker (P75: the label buttons are gone)', !!bS&&!!bF&&
       bS.getAttribute('aria-haspopup')==='dialog'&&bF.getAttribute('aria-haspopup')==='dialog'&&!$('ms-dp-btn-start')&&!$('ms-dp-btn-date')&&
       bS.getBoundingClientRect().width>0&&bF.getBoundingClientRect().width>0, '');
    ck('picker: hidden at rest', dp().hidden, '');
    const finIso=parseMsDate($('ms-date').value);
    bF.click(); await settle();
    ck('picker: opens from the finish field', !dp().hidden&&bF.getAttribute('aria-expanded')==='true', '');
    ck('picker: on the field\'s own month', $('ms-dp-month').textContent===MONTH_NAMES[+finIso.slice(5,7)-1].slice(0,3)+' '+finIso.slice(0,4), $('ms-dp-month').textContent);
    ck('picker: the field\'s date is selected', day(finIso)&&day(finIso).classList.contains('is-sel'), finIso);
    ck('picker: Actual is unticked by default', $('ms-dp-actual').checked===false&&/forecast/i.test($('ms-dp-mode').textContent), $('ms-dp-mode').textContent);
    ck('picker: Actual sits in the heading', !!$('ms-dp-actual').closest('.ms-dp-head'), '');
    const r=dp().getBoundingClientRect();
    ck('picker: inside the viewport', r.left>=0&&r.top>=0&&r.right<=window.innerWidth&&r.bottom<=window.innerHeight, [r.left,r.top,r.right,r.bottom].map(Math.round).join(','));
    ck('picker: a 7-column grid of 42 days', dp().querySelectorAll('.ms-dp-day').length===42, '');

    // ===== 2. Forecast pick =====
    const d1=addDays(finIso,2);
    if(!day(d1)){ dp().querySelector('.ms-dp-next').click(); await settle(); }
    day(d1).click(); await settle();
    ck('forecast: pick writes the date with no A', $('ms-date').value===fmtTipDate(d1), $('ms-date').value);
    ck('forecast: picker closes', dp().hidden&&bF.getAttribute('aria-expanded')==='false', '');
    ck('forecast: not green', !$('ms-date').classList.contains('is-actualised')&&getComputedStyle($('ms-date')).color!==GREEN, getComputedStyle($('ms-date')).color);
    ck('forecast: the card is dirty (save enabled)', $('ms-save-actions').getAttribute('aria-disabled')==='false', '');
    ck('card: still open after the pick', !dlg().hidden, '');

    // ===== 3. Actual pick =====
    bF.click(); await settle();
    ck('reopen: Actual unticked again', $('ms-dp-actual').checked===false, '');
    $('ms-dp-actual').click(); await settle();
    ck('actual: ticking says so', /actual/i.test($('ms-dp-mode').textContent)&&dp().classList.contains('is-actual'), $('ms-dp-mode').textContent);
    const d2=addDays(finIso,3);
    if(!day(d2)){ dp().querySelector('.ms-dp-next').click(); await settle(); }
    day(d2).click(); await settle();
    ck('actual: pick writes "<date> A"', $('ms-date').value===fmtTipDate(d2)+' A', $('ms-date').value);
    ck('actual: the field turns green at once', $('ms-date').classList.contains('is-actualised')&&getComputedStyle($('ms-date')).color===GREEN, getComputedStyle($('ms-date')).color+' vs '+GREEN);
    const n0=msEntries(key).length;
    onMsSaveClick(false); await settle();
    const E=msEntries(key).slice(-1)[0];
    ck('save: one entry carrying the date and the flag', E&&E.changes.date&&E.changes.date.to===d2&&E.changes.actual&&E.changes.actual.to===true, JSON.stringify(E&&E.changes));
    ck('save: projected to the override store', MS_FIELD_OVERRIDE[key]&&MS_FIELD_OVERRIDE[key].actual===true&&MS_FIELD_OVERRIDE[key].date===d2, JSON.stringify(MS_FIELD_OVERRIDE[key]));
    await gap(); await settle();
    const Fm=MILESTONES.find(m=>msKeyFor(m)===key);
    ck('save: the milestone reads actual on the board model', Fm&&Fm.actual===true&&Fm.date===d2, Fm&&(Fm.actual+' '+Fm.date));
    await open(A);
    ck('reopen: the card shows the A and the green', $('ms-date').value===fmtTipDate(d2)+' A'&&$('ms-date').classList.contains('is-actualised'), $('ms-date').value);
    const hist=$('ms-history').textContent;
    ck('history: the change reads Forecast to Actual', /End date is/.test(hist)&&/Forecast/.test(hist)&&/Actual/.test(hist), '');

    // ===== 4. Back to forecast, and Clear =====
    bF.click(); await settle();
    day(d2).click(); await settle();
    ck('untick: same day unticked drops the A', $('ms-date').value===fmtTipDate(d2), $('ms-date').value);
    onMsSaveClick(false); await settle();
    ck('untick: back to the schedule forecast clears the flag override', MS_FIELD_OVERRIDE[key]&&!('actual' in MS_FIELD_OVERRIDE[key])&&MS_FIELD_OVERRIDE[key].date===d2, JSON.stringify(MS_FIELD_OVERRIDE[key]));
    bF.click(); await settle();
    dp().querySelector('.ms-dp-clear').click(); await settle();
    ck('clear: empties the field', $('ms-date').value==='', '');
    onMsSaveClick(false); await settle();
    ck('clear: the date goes back to the schedule', !MS_FIELD_OVERRIDE[key]||!('date' in MS_FIELD_OVERRIDE[key]), JSON.stringify(MS_FIELD_OVERRIDE[key]||{}));

    // ===== 5. Start field =====
    await open(A);
    bS.click(); await settle();
    const stIso=parseMsDate($('ms-start-date').value);
    ck('start: picker opens on the start date', day(stIso)&&day(stIso).classList.contains('is-sel'), stIso);
    $('ms-dp-actual').click();
    day(stIso).click(); await settle();
    ck('start: same day ticked becomes "<date> A", green', $('ms-start-date').value===fmtTipDate(stIso)+' A'&&$('ms-start-date').classList.contains('is-actualised'), $('ms-start-date').value);
    onMsSaveClick(false); await settle();
    const E2=msEntries(key).slice(-1)[0];
    ck('start: saved as a startActual change only', E2&&E2.changes.startActual&&E2.changes.startActual.to===true&&!E2.changes.start, JSON.stringify(E2&&E2.changes));

    // ===== 6. Navigation and keys =====
    bF.click(); await settle();
    const foc=document.activeElement;
    ck('keys: the selected day has focus on open', foc&&foc.classList.contains('ms-dp-day'), foc&&(foc.id||foc.className));
    const t0=$('ms-dp-month').textContent;
    dp().querySelector('.ms-dp-next').click(); await settle();
    const t1=$('ms-dp-month').textContent;
    dp().querySelector('.ms-dp-prev').click(); await settle();
    ck('nav: next and previous month', t1!==t0&&$('ms-dp-month').textContent===t0, t0+' > '+t1);
    day(f0x=foc.getAttribute('data-iso')).focus();
    const f0=f0x;
    foc.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true})); await settle();
    ck('keys: ArrowRight moves one day', document.activeElement.getAttribute('data-iso')===addDays(f0,1), document.activeElement.getAttribute('data-iso'));
    document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true})); await settle();
    ck('keys: ArrowDown moves one week', document.activeElement.getAttribute('data-iso')===addDays(f0,8), document.activeElement.getAttribute('data-iso'));
    const mBefore=$('ms-dp-month').textContent;
    document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'PageDown',bubbles:true})); await settle();
    ck('keys: PageDown is the next month', $('ms-dp-month').textContent!==mBefore, $('ms-dp-month').textContent);
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); await settle();
    ck('Esc: closes the picker, not the card', dp().hidden&&!dlg().hidden, '');
    $('ms-date').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',altKey:true,bubbles:true})); await settle();
    ck('keys: Alt+Down on the field opens the picker', !dp().hidden, '');
    $('ms-title').click(); await settle();
    ck('click elsewhere in the card closes only the picker', dp().hidden&&!dlg().hidden, '');
    let pe=null;
    try{ pe=new PointerEvent('pointerdown',{pointerType:'touch',bubbles:true,cancelable:true}); }catch(x){}
    if(pe){ $('ms-start-date').dispatchEvent(pe); await settle(); }
    ck('touch: a tap on the field opens the picker, not the keyboard', pe&&pe.defaultPrevented&&!dp().hidden&&MS_DP.field==='ms-start-date', '');
    $('ms-start-date').dispatchEvent(new MouseEvent('click',{bubbles:true})); await settle();
    ck('touch: the tap\'s own click does not close it again', !dp().hidden, '');
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); await settle();
    discardMsDialog(); await settle();

    // ===== 7. The value's A, and P6 suffixes =====
    // P75: the field is readonly (no free typing); the value is written by
    // the picker, which raises the same input event this writes.
    await open(A);
    ck('no typing: the date fields are readonly (P75)', $('ms-date').readOnly&&$('ms-start-date').readOnly, '');
    $('ms-date').value=fmtTipDate(finIso)+' A'; $('ms-date').dispatchEvent(new Event('input',{bubbles:true}));
    ck('value: " A" written turns the field green', $('ms-date').classList.contains('is-actualised'), '');
    $('ms-date').value=fmtTipDate(finIso); $('ms-date').dispatchEvent(new Event('input',{bubbles:true}));
    ck('value: removing it turns it back', !$('ms-date').classList.contains('is-actualised'), '');
    discardMsDialog(); await settle();
    ck('suffix: "A *" parses and reads actual', parseMsDate('15-Jun-26 A *')==='2026-06-15'&&msDateIsActual('15-Jun-26 A *'), '');
    ck('suffix: "*" alone parses and reads forecast', parseMsDate('15-Jun-26 *')==='2026-06-15'&&!msDateIsActual('15-Jun-26 *'), '');
    ck('suffix: a name ending in A is not a flag', !msDateIsActual('15-Jun-26A'), '');
    const AM=MILESTONES.find(m=>m.actual&&wrapOf(msId(m)));
    if(AM){ await open(msId(AM));
      ck('schedule actual: opens with A and green', / A/.test($('ms-date').value)&&$('ms-date').classList.contains('is-actualised')&&getComputedStyle($('ms-date')).color===GREEN, $('ms-date').value);
      discardMsDialog(); await settle(); }

    // ===== 8. Row-health dot colours (stray quote fix) =====
    const dot=c=>{ const sp=document.createElement('span'); sp.className='health-dot '+c; document.body.appendChild(sp); const v=getComputedStyle(sp).backgroundColor; sp.remove(); return v; };
    ck('health dots: h-3 is the critical colour', dot('h-3')===bgOf('--color-crit'), dot('h-3')+' vs '+bgOf('--color-crit'));
    ck('health dots: h-4 is the done colour', dot('h-4')===bgOf('--color-status-done'), dot('h-4')+' vs '+bgOf('--color-status-done'));
    ck('page: no horizontal scroll', document.documentElement.scrollWidth<=window.innerWidth, document.documentElement.scrollWidth);
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
        tmp = pathlib.Path(td) / "p69.html"
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
