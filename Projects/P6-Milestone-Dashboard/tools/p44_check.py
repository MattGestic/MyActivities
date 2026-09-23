#!/usr/bin/env python3
"""
P44 check (TEST-46): the card's heading, the saved-edit marks, and the marker
fill convention the board never implemented.

THE FILL CONVENTION IS THE INTERESTING ONE. `.ms-icon.outline` has existed in
the CSS since the start and the legend has always documented "filled = done,
outline = everything else", but every entry in STATES carried render:'filled',
so the only thing the outline rule ever styled was the legend swatch beside the
text claiming it. The board drew one solid mark for every state. Asserted here
as a property of the RENDERED markers (computed fill and stroke-width off real
SVGs on the board), not as a property of the STATES table, because the table
being right is not the claim: what a reader sees is.

Both directions, with counts. A finished milestone must be filled and an
unfinished one must not, and both populations must be non-empty, or "every
marker is outline" would pass the outline half.

THE HEADING RUNS UP TO THE FLOAT. The controls moved to a row of their own so
the heading could have the card's full width. That is a geometric claim about
three boxes and is measured as one: the heading must start at the card's left
padding and end at the float column, and must sit BELOW the controls row.

THE SAVED-EDIT MARK IS NOT THE DIRTY TINT. They mean different things and the
check keeps them apart deliberately: typing shows the tint and no mark, saving
shows the mark and no tint. A check that only asserted "a mark appears" would
pass on code that simply aliased the two.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p44_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p44-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p44-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog');
  const box=el=>{ if(!el) return null; const r=el.getBoundingClientRect();
    const d=dlg().getBoundingClientRect();
    return {l:Math.round(r.left-d.left),r:Math.round(r.right-d.left),
            t:Math.round(r.top-d.top),b:Math.round(r.bottom-d.top),
            w:Math.round(r.width)}; };
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const open=async function(id){
    const w=wrapOf(id); if(!w) return false;
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    w.click(); await settle();
    if(dlg().hidden) throw new Error('card did not open for '+id);
    return true;
  };
  const type=function(id,v){
    const e=$(id); if(!e) return false;
    e.value=v; e.dispatchEvent(new Event('input',{bubbles:true}));
    return true;
  };
  const saveBtn=i=>$('ms-save-actions').querySelectorAll('.ms-act')[i];
  const markShown=f=>{ const e=$('ms-mark-'+f); return !!e&&!e.hidden; };

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();

    // ============ 1. THE FILL CONVENTION, on the rendered board ============
    // Measured off real markers, not off the STATES table. The table has said
    // 'filled' for every state since the start while the CSS and the legend
    // both documented the opposite, so asserting the table would have passed
    // throughout the period the board was wrong.
    const marks=Array.prototype.map.call(
      document.querySelectorAll('#tbody .m-wrap:not(.m-ghost) .ms-icon'),function(ic){
        const cs=getComputedStyle(ic);
        return {cls:ic.getAttribute('class')||'',
                fill:cs.fill,strokeW:parseFloat(cs.strokeWidth)||0};
      });
    const finished=marks.filter(m=>/s-done(\s|$)|s-doneuser/.test(m.cls));
    const unfinished=marks.filter(m=>/s-track|s-risk|s-crit|s-future|s-na/.test(m.cls));
    const isFilled=m=>m.fill!=='none'&&m.cls.indexOf('filled')>=0;
    const isOutline=m=>m.fill==='none'&&m.cls.indexOf('outline')>=0&&m.strokeW>=1.5;
    R.notes.fill={total:marks.length,finished:finished.length,
                  unfinished:unfinished.length,
                  finishedFilled:finished.filter(isFilled).length,
                  unfinishedOutline:unfinished.filter(isOutline).length,
                  sampleFinished:finished[0]||null,sampleUnfinished:unfinished[0]||null};
    ck('fill: the board carries markers of BOTH kinds, so neither half passes vacuously',
       finished.length>0&&unfinished.length>0,
       JSON.stringify({finished:finished.length,unfinished:unfinished.length}));
    ck('fill: every FINISHED marker is filled',
       finished.length>0&&finished.every(isFilled),
       finished.filter(isFilled).length+' of '+finished.length+
       ', sample '+JSON.stringify(finished[0]));
    ck('fill: every UNFINISHED marker is unfilled, with a stroke to be seen by',
       unfinished.length>0&&unfinished.every(isOutline),
       unfinished.filter(isOutline).length+' of '+unfinished.length+
       ', sample '+JSON.stringify(unfinished[0]));
    // The legend is where this convention is written down for the reader. It
    // must agree with what the board now draws, or one of the two is lying.
    const legFilled=document.querySelectorAll('.legend-row .ms-icon.filled').length;
    const legOutline=document.querySelectorAll('.legend-row .ms-icon.outline').length;
    R.notes.legend={filled:legFilled,outline:legOutline};
    ck('fill: the legend still documents both halves of the convention',
       legFilled>0&&legOutline>0, JSON.stringify(R.notes.legend));

    const sample=MILESTONES.filter(m=>msId(m)&&wrapOf(msKeyFor(m)))[0];
    const A=msId(sample);
    R.notes.sample={id:A,state:sample.state};
    ck('sample: a milestone is on the board to open a card for', !!A, String(A));

    // ============ 2. The controls have a row of their own, above ==========
    await open(A);
    const head=dlg().querySelector('.ms-dialog-head');
    const heading=dlg().querySelector('.ms-heading');
    const closeBtn=dlg().querySelector('.ms-close');
    const floatCol=$('ms-float-col');
    const code=$('ms-code');
    R.notes.rows={head:box(head),heading:box(heading),
                  close:box(closeBtn),floatCol:box(floatCol),code:box(code)};
    ck('rows: the heading sits BELOW the controls row, not on it',
       box(heading).t>=box(head).b-1,
       JSON.stringify({headBottom:box(head).b,headingTop:box(heading).t}));
    ck('rows: the controls row holds the close control and nothing from the heading',
       head.contains(closeBtn)&&!head.contains(code)&&!head.contains($('ms-icon-btn')),
       'close in head='+head.contains(closeBtn)+' id in head='+head.contains(code));
    // "The heading should run the full length up to the float."
    // Measured against the card's own CONTENT box, not against the close
    // control: close carries a negative margin so it is deliberately outdented
    // past the padding edge, and comparing to it failed a heading that starts
    // exactly where it should.
    const pad=parseFloat(getComputedStyle(dlg()).paddingLeft)||0;
    const gap=parseFloat(getComputedStyle(dlg().querySelector('.ms-title-row')).columnGap)||0;
    R.notes.rows.pad=Math.round(pad); R.notes.rows.gap=Math.round(gap);
    ck('rows: the heading starts at the card\u2019s left edge and runs up to the float',
       Math.abs(box(heading).l-pad)<=1&&
       Math.abs(box(floatCol).l-box(heading).r-gap)<=1,
       JSON.stringify({pad:pad,headingL:box(heading).l,headingR:box(heading).r,
                       floatL:box(floatCol).l,gap:gap}));
    ck('rows: the heading is wider than the ID it used to share a line with',
       box(heading).w>box(code).w*2,
       box(heading).w+'px heading against '+box(code).w+'px id');

    // ============ 3. The type name is off the heading, on the icon ========
    const headingText=heading.textContent.replace(/\s+/g,' ').trim();
    const tip=$('ms-icon-btn').getAttribute('title')||'';
    R.notes.typeText={heading:headingText,tooltip:tip,
                      typeLabel:TYPE_LABELS[sample.type]};
    ck('type: the heading no longer carries the type name',
       headingText.indexOf(TYPE_LABELS[sample.type])<0&&
       headingText.indexOf('('+sample.type+')')<0,
       headingText);
    ck('type: the icon’s tooltip carries it instead',
       tip.indexOf(TYPE_LABELS[sample.type])>=0&&tip.indexOf('('+sample.type+')')>=0,
       tip);
    ck('type: the card icon is the board’s own mark, drawn by the same helper',
       !!$('ms-icon-btn').querySelector('svg.ms-icon use'),
       $('ms-icon-btn').innerHTML.slice(0,90));
    // And it carries the convention, same as the board.
    const cardIcon=$('ms-icon-btn').querySelector('.ms-icon');
    const cardCls=cardIcon.getAttribute('class')||'';
    const boardCls=wrapOf(msKeyFor(sample)).querySelector('.ms-icon').getAttribute('class')||'';
    R.notes.cardIcon={card:cardCls,board:boardCls};
    ck('type: the card’s mark renders the same way as the board’s',
       (cardCls.indexOf('filled')>=0)===(boardCls.indexOf('filled')>=0)&&
       (cardCls.indexOf('outline')>=0)===(boardCls.indexOf('outline')>=0),
       JSON.stringify(R.notes.cardIcon));

    // ============ 4. The saved-edit mark ============
    // A fresh card on an unedited milestone carries none. The negative control
    // for everything below.
    const fields=['actName','start','date','weight','floatD','progress',
                  'shortTitle','health','marker'];
    const shownAtOpen=fields.filter(markShown);
    R.notes.marksClean={checked:fields.length,shown:shownAtOpen};
    ck('marks: an unedited milestone shows no changed-from-source marks at all',
       shownAtOpen.length===0&&fields.length===9,
       fields.length+' checked, shown: '+(shownAtOpen.join(',')||'none'));

    // Typing is NOT saving. The dirty tint says "typed"; the mark says
    // "stored, and different from the schedule". Aliasing the two would make
    // the mark meaningless, so they are asserted apart.
    type('ms-weight','77');
    await settle();
    R.notes.marksTyped={dirtyTint:$('ms-weight').classList.contains('ms-dirty-field'),
                        mark:markShown('weight')};
    ck('marks: typing shows the unsaved tint and NOT the changed-from-source mark',
       $('ms-weight').classList.contains('ms-dirty-field')&&!markShown('weight'),
       JSON.stringify(R.notes.marksTyped));

    saveBtn(0).click(); await settle(); await settle();
    const wMark=$('ms-mark-weight');
    R.notes.marksSaved={mark:markShown('weight'),
                        tint:$('ms-weight').classList.contains('ms-dirty-field'),
                        tip:wMark?wMark.getAttribute('title'):null,
                        was:sample._msBase?sample._msBase.weight:sample.weight};
    ck('marks: saving shows the mark and clears the unsaved tint',
       markShown('weight')&&!$('ms-weight').classList.contains('ms-dirty-field'),
       JSON.stringify(R.notes.marksSaved));
    ck('marks: the mark’s tooltip reports the value the schedule had',
       !!wMark&&/Changed from the schedule/.test(wMark.getAttribute('title')||'')&&
       (wMark.getAttribute('title')||'').indexOf(String(
         sample._msBase?sample._msBase.weight:sample.weight))>=0,
       wMark?wMark.getAttribute('title'):'no mark');
    ck('marks: only the field that was edited is marked',
       fields.filter(markShown).join(',')==='weight',
       'shown: '+(fields.filter(markShown).join(',')||'none'));
    // It has to SURVIVE a reopen: the mark reads the stores, so a card built
    // fresh from them must show it without anything being typed.
    await open(A);
    R.notes.marksReopen={shown:fields.filter(markShown)};
    ck('marks: the mark survives closing and reopening the card',
       markShown('weight'), 'shown: '+(fields.filter(markShown).join(',')||'none'));
    // NEGATIVE CONTROL: clearing the override must clear the mark. A one-way
    // check passes on code that marks a field and can never unmark it.
    type('ms-weight',String(sample._msBase?sample._msBase.weight:sample.weight));
    await settle();
    saveBtn(0).click(); await settle(); await settle();
    R.notes.marksCleared={shown:fields.filter(markShown),
                          stored:JSON.stringify(MS_FIELD_OVERRIDE[msKeyFor(sample)]||{})};
    ck('marks NEGATIVE CONTROL: typing the schedule’s own value back clears the mark',
       !markShown('weight'), JSON.stringify(R.notes.marksCleared));

    // ============ 5. The mark picker changes the board mark ==============
    await open(A);
    const before=wrapOf(msKeyFor(sample)).querySelector('.ms-icon use')
                   .getAttribute('href');
    $('ms-icon-btn').click(); await settle();
    const menu=$('ms-type-menu');
    const markOpts=menu.querySelectorAll('.ms-type-opt[data-marker]');
    const typeOpts=menu.querySelectorAll('.ms-type-opt[data-type]');
    R.notes.picker={open:!menu.hidden,marks:markOpts.length,types:typeOpts.length,
                    groups:menu.querySelectorAll('.ms-type-grp').length,before:before};
    ck('picker: the icon opens a picker offering both the mark and the type',
       !menu.hidden&&markOpts.length===MS_MARKERS.length&&
       typeOpts.length===Object.keys(TYPE_LABELS).length&&
       menu.querySelectorAll('.ms-type-grp').length===2,
       JSON.stringify(R.notes.picker));
    const other=Array.prototype.filter.call(markOpts,function(o){
      return normalizeMarker(o.getAttribute('data-marker'))!==before.replace('#',''); })[0];
    const wantMark=other.getAttribute('data-marker');
    other.click(); await settle();
    saveBtn(1).click(); await settle(); await settle(); await settle();
    const after=wrapOf(msKeyFor(sample)).querySelector('.ms-icon use').getAttribute('href');
    R.notes.markerRound={before:before,after:after,want:normalizeMarker(wantMark),
                         stored:(MS_FIELD_OVERRIDE[msKeyFor(sample)]||{}).marker};
    ck('picker: picking a mark and saving CHANGES the mark drawn on the board',
       after==='#'+normalizeMarker(wantMark)&&after!==before,
       JSON.stringify(R.notes.markerRound));
    delete MS_FIELD_OVERRIDE[msKeyFor(sample)];
    scheduleRerender(true); await settle(); await settle();
    R.notes.markerReverted={
      href:wrapOf(msKeyFor(sample)).querySelector('.ms-icon use').getAttribute('href'),
      want:before};
    ck('picker NEGATIVE CONTROL: clearing the override puts the original mark back',
       wrapOf(msKeyFor(sample)).querySelector('.ms-icon use').getAttribute('href')===before,
       JSON.stringify(R.notes.markerReverted));

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
        tmp = pathlib.Path(td) / "p44.html"
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
    nospace = re.sub(r"\s+", "", src)
    checks = []

    # The convention lives in STATES, and the point of this change is that it
    # had drifted from the CSS and the legend. Asserted at source as well as on
    # the rendered board, since the two together say the drift cannot recur
    # silently in either direction.
    outline_states = re.findall(r"(TRACK|RISK|CRIT|FUTURE|NA):\{cls:'[^']+',render:'outline'", nospace)
    filled_states = re.findall(r"(DONE|DONEUSER):\{cls:'[^']+',render:'filled'", nospace)
    checks.append((
        "source: the five unfinished states render outline",
        len(set(outline_states)) == 5,
        f"outline: {sorted(set(outline_states))}"))
    checks.append((
        "source: the two finished states render filled",
        len(set(filled_states)) == 2,
        f"filled: {sorted(set(filled_states))}"))
    checks.append((
        "source: the outline rule that was only ever styling the legend is still there",
        ".ms-icon.outline{fill:none" in nospace,
        "the outline rule is gone"))
    # One helper draws the mark, on the board and on the card.
    checks.append((
        "source: the card draws its mark with the board's own renderIcon()",
        src.count("function renderIcon(") == 1 and "renderIcon(msFormMarker()" in src,
        "the card has its own shapes again"))
    checks.append((
        "source: the type name is written in exactly one place",
        "ms-type-inline" not in src.replace(
            "/* .ms-type-inline is gone", "") or src.count('id="ms-type-inline"') == 0,
        "the removed heading element is still referenced"))
    # The saved mark and the unsaved tint must stay separate classes.
    checks.append((
        "source: the saved mark and the unsaved tint are different things",
        ".ms-edited-mark{" in nospace and ".ms-dirty-field{" in nospace,
        "one of the two indicator styles is missing"))
    checks.append((
        "source: the marks have one writer, called from open and from save",
        src.count("function syncMsEditedMarks(") == 1
        and src.count("syncMsEditedMarks();") == 2,
        f"{src.count('syncMsEditedMarks();')} call sites, expected 2"))
    checks.append((
        "source: the marker shape joins the editable fields",
        "'type','marker']" in nospace,
        "marker is not in MS_EDITABLE_FIELDS"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if R.get("err"):
            print(f"PROBE ERROR at {w}x{h}:\n{R['err']}")
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("fill", "legend", "sample", "rows", "typeText", "cardIcon",
                  "marksClean", "marksTyped", "marksSaved", "marksReopen",
                  "marksCleared", "picker", "markerRound", "markerReverted"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")
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
