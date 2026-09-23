#!/usr/bin/env python3
"""
P43 check (TEST-45): the milestone card becomes a form.

THE CARD USED TO HAVE NO STATE OF ITS OWN. Every field wrote straight to its
annotation store: the comment on each keystroke, progress on blur, health on
click. There was therefore nothing to save and nothing to discard, and the one
control that did say Save (the short title's) wrote without hiding itself,
which is the defect that was reported.

So the assertions here are about a FORM: it knows when it is dirty, it can be
committed, and it can be thrown away. Each of the three is measured in both
directions, because a one-way check passes on code that can save and never
stop showing the save control, or discard and never restore anything.

TWO DIRECTIONS OUT, DELIBERATELY OPPOSITE. Close (left, marked with a cross)
and Escape discard. Clicking away from the card saves and closes, on the
reasoning that clicking off is leaving, not a decision to destroy work. Both
are driven here as a real user gesture, not by calling the handler, because
the click-away path only exists as a document listener.

GEOMETRY IS MEASURED, NOT READ OFF THE MARKUP. "Close on the left", "icon then
ID", "save pair top right" and "three equal columns that do not move" are all
claims about where things land, and source order does not settle any of them.
They are asserted from getBoundingClientRect on the rendered card, and the
fixed-position claim is asserted across TWO cards (one with a start date, one
without) since that is the case that used to shift the row.

THE ROUND TRIP IS THE PROOF OF WIRING. An edited field that does not reach the
board is a form that lies. The finish date is edited, saved, and the marker is
required to have MOVED COLUMN, with a negative control that clearing the
override puts it back where the schedule had it.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p43_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p43-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p43-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog');
  const L=el=>el?Math.round(el.getBoundingClientRect().left):null;
  // Offset from the CARD's own left edge. "Fixed positions" is a claim about
  // where the fields sit in the card; measured against the viewport it also
  // carries where the card was placed, and the card is centred on the marker
  // that opened it, so two milestones in different weeks give two different
  // absolute positions for a layout that never moved.
  const RL=el=>el?Math.round(el.getBoundingClientRect().left-
                             dlg().getBoundingClientRect().left):null;
  const W=el=>el?Math.round(el.getBoundingClientRect().width):null;
  // Open a card the way a person does, by clicking the marker. Calling
  // openMsDialog() directly would skip the listener that owns the toggle.
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const open=async function(id){
    const w=wrapOf(id); if(!w) return false;
    // The marker TOGGLES its own card, so an already-open card has to be shut
    // first or this click closes it and everything after works on a hidden
    // dialog. The first draft of this check missed that and reported the
    // round trip as broken when the code was fine.
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    w.click(); await settle();
    if(dlg().hidden) throw new Error('card did not open for '+id);
    return true;
  };
  // A real typed edit: set the value AND fire the event the field listens on,
  // since assigning .value alone never reaches an oninput handler.
  const type=function(id,v){
    const e=$(id); if(!e) return false;
    e.value=v; e.dispatchEvent(new Event('input',{bubbles:true}));
    return true;
  };
  const colOf=function(id){
    const w=wrapOf(id); if(!w) return null;
    const td=w.closest('td[data-col]');
    return td?td.getAttribute('data-col'):null;
  };
  const saveShown=()=>$('ms-save-actions')&&!$('ms-save-actions').hidden;

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();

    // Samples must be RENDERED, not merely present in the data: a milestone
    // dated outside the visible week window draws no marker, so there is no
    // card to open and nothing to measure. This cost three false failures at
    // P42 and the filter is kept for the same reason.
    const onBoard=m=>!!wrapOf(msKeyFor(m));
    const withStart=MILESTONES.filter(function(m){
      return m.start&&fmtTipDate(m.start)!==fmtTipDate(m.date)&&msId(m)&&onBoard(m); })[0];
    const noStart=MILESTONES.filter(function(m){
      return !(m.start&&fmtTipDate(m.start)!==fmtTipDate(m.date))&&!m.finishFromStart&&
             msId(m)&&onBoard(m); })[0];
    R.notes.sample={withStart:withStart?msId(withStart):null,
                    noStart:noStart?msId(noStart):null};
    ck('sample: the board carries a milestone with a start date and one without',
       !!withStart&&!!noStart, JSON.stringify(R.notes.sample));
    const A=msId(withStart), B=msId(noStart);

    // ============ 1. Head order: close, then icon, then ID ============
    await open(A);
    const closeBtn=dlg().querySelector('.ms-close');
    const icoBtn=$('ms-icon-btn'), code=$('ms-code');
    R.notes.head={close:L(closeBtn),icon:L(icoBtn),code:L(code),
                  codeText:code?code.textContent:null};
    ck('head: close sits LEFT of the icon, which sits left of the ID',
       L(closeBtn)!==null&&L(closeBtn)<L(icoBtn)&&L(icoBtn)<L(code),
       JSON.stringify(R.notes.head));
    ck('head: the ID is the milestone’s own',
       (code.textContent||'').indexOf(A)>=0, code.textContent);
    // className on an SVGElement is an SVGAnimatedString, not a string. The
    // card's mark became a real <svg> at P44 so it could carry the board's own
    // outline / filled convention through renderIcon(), and reading .className
    // threw rather than failing.
    const glyphCls=function(){
      const b=$('ms-icon-btn'); const g=b?b.querySelector('.ms-icon'):null;
      return g?(g.getAttribute('class')||''):''; };
    ck('head: the icon is the board\u2019s own mark for this milestone',
       /ms-icon/.test(glyphCls())&&!!$('ms-icon-btn').querySelector('use'),
       glyphCls());

    // ============ 2. A fresh card is CLEAN ============
    // The negative control for everything below: if the save pair showed on an
    // untouched card, every "it appears when dirty" check would pass trivially.
    ck('dirty: a card nobody has edited shows no save controls at all',
       !saveShown(), 'save pair hidden='+String(!saveShown()));

    // ============ 3. Dirty puts two save controls at the TOP RIGHT ========
    type('ms-shorttitle-input','Probe short title');
    await settle();
    const acts=$('ms-save-actions');
    const actBtns=acts?acts.querySelectorAll('.ms-act'):[];
    R.notes.dirty={shown:saveShown(),buttons:actBtns.length,
                   actLeft:L(acts),codeLeft:L(code),
                   labels:Array.prototype.map.call(actBtns,b=>b.getAttribute('title')).join(' | ')};
    ck('dirty: editing a field reveals exactly two save controls',
       saveShown()&&actBtns.length===2, JSON.stringify(R.notes.dirty));
    ck('dirty: the save controls sit to the RIGHT of the ID',
       L(acts)>L(code), 'acts '+L(acts)+' against id '+L(code));
    ck('dirty: the pair is Save and Save-and-close',
       R.notes.dirty.labels==='Save | Save and close', R.notes.dirty.labels);

    // ============ 4. Save, staying open, CLEARS the save controls ==========
    // The reported defect, stated for every field rather than for the one that
    // had its own button.
    actBtns[0].click(); await settle(); await settle();
    R.notes.saved={stillOpen:!dlg().hidden,saveShown:saveShown(),
                   stored:MS_SHORT_TITLES[msKeyFor(withStart)]||null};
    ck('save: the card stays open and the save controls go away',
       !dlg().hidden&&!saveShown(), JSON.stringify(R.notes.saved));
    ck('save: the value reached its store',
       MS_SHORT_TITLES[msKeyFor(withStart)]==='Probe short title',
       String(MS_SHORT_TITLES[msKeyFor(withStart)]));

    // ============ 5. Close is a DISCARD ============
    type('ms-shorttitle-input','Thrown away');
    await settle();
    const dirtyBeforeClose=saveShown();
    closeBtn.click(); await settle(); await settle();
    R.notes.discard={dirtyBefore:dirtyBeforeClose,closed:dlg().hidden,
                     stored:MS_SHORT_TITLES[msKeyFor(withStart)]||null};
    ck('discard: the close control closes the card and keeps the SAVED value',
       dirtyBeforeClose&&dlg().hidden&&
       MS_SHORT_TITLES[msKeyFor(withStart)]==='Probe short title',
       JSON.stringify(R.notes.discard));
    await open(A);
    ck('discard: reopening shows the saved value, not the discarded one',
       $('ms-shorttitle-input').value==='Probe short title',
       $('ms-shorttitle-input').value);

    // ============ 6. Clicking AWAY saves and closes ============
    type('ms-shorttitle-input','Kept by clicking away');
    await settle();
    document.getElementById('tbody').click(); await settle(); await settle();
    R.notes.clickAway={closed:dlg().hidden,
                       stored:MS_SHORT_TITLES[msKeyFor(withStart)]||null};
    ck('click away: an edited card is SAVED and closed, not discarded',
       dlg().hidden&&MS_SHORT_TITLES[msKeyFor(withStart)]==='Kept by clicking away',
       JSON.stringify(R.notes.clickAway));

    // ============ 7. Three equal columns that do not move ============
    await open(A);
    const fieldsA=dlg().querySelectorAll('.ms-schedule .ms-field');
    const geomA=Array.prototype.map.call(fieldsA,e=>({l:RL(e),w:W(e)}));
    await open(B);
    const fieldsB=dlg().querySelectorAll('.ms-schedule .ms-field');
    const geomB=Array.prototype.map.call(fieldsB,e=>({l:RL(e),w:W(e)}));
    R.notes.columns={withStart:geomA,noStart:geomB,
                     startShown:!$('ms-start-field').hidden,
                     startValue:$('ms-start-date').value,
                     startPlaceholder:$('ms-start-date').placeholder};
    ck('columns: the card shows three schedule fields on both cards',
       fieldsA.length===3&&fieldsB.length===3,
       fieldsA.length+' and '+fieldsB.length);
    // Equal weight, within a pixel of rounding.
    const eq=g=>Math.max(g[0].w,g[1].w,g[2].w)-Math.min(g[0].w,g[1].w,g[2].w)<=1;
    ck('columns: the three are equally weighted on a card WITH a start date',
       eq(geomA), JSON.stringify(geomA));
    ck('columns: and equally weighted on a card WITHOUT one',
       eq(geomB), JSON.stringify(geomB));
    // The case that used to move them: Start hid itself and the other two slid.
    const sameL=geomA.every((g,i)=>Math.abs(g.l-geomB[i].l)<=1);
    ck('columns: FIXED positions, the same on both cards',
       sameL, JSON.stringify({withStart:geomA.map(g=>g.l),noStart:geomB.map(g=>g.l)}));
    ck('columns: a milestone with no start shows a dash, not a blank',
       $('ms-start-date').value===''&&$('ms-start-date').placeholder==='—',
       JSON.stringify({v:$('ms-start-date').value,p:$('ms-start-date').placeholder}));

    // ============ 8. The icon opens a type picker that changes the type ====
    await open(A);
    const beforeType=withStart.type;
    $('ms-icon-btn').click(); await settle();
    const menu=$('ms-type-menu');
    // The picker offers the MARK and the type since P44, so the type options
    // are the ones carrying data-type.
    const opts=menu?menu.querySelectorAll('.ms-type-opt[data-type]'):[];
    R.notes.typeMenu={open:menu&&!menu.hidden,options:opts.length,
                      vocab:Object.keys(TYPE_LABELS).length,
                      before:beforeType};
    ck('type: clicking the icon opens a picker with one option per known type',
       menu&&!menu.hidden&&opts.length===Object.keys(TYPE_LABELS).length,
       JSON.stringify(R.notes.typeMenu));
    const other=Array.prototype.filter.call(opts,
      o=>o.getAttribute('data-type')!==beforeType)[0];
    const newType=other.getAttribute('data-type');
    other.click(); await settle();
    ck('type: picking one marks the form dirty without storing anything yet',
       saveShown()&&!(MS_FIELD_OVERRIDE[msKeyFor(withStart)]||{}).type,
       'dirty='+saveShown()+' stored='+JSON.stringify(MS_FIELD_OVERRIDE[msKeyFor(withStart)]||{}));
    $('ms-save-actions').querySelectorAll('.ms-act')[0].click();
    await settle(); await settle();
    R.notes.typeSaved={want:newType,
                       stored:(MS_FIELD_OVERRIDE[msKeyFor(withStart)]||{}).type,
                       onBoard:(MILESTONES.filter(m=>msId(m)===A)[0]||{}).type};
    ck('type: saving writes the override AND the board milestone carries it',
       (MF=>MF.type===newType)(MS_FIELD_OVERRIDE[msKeyFor(withStart)]||{})&&
       (MILESTONES.filter(m=>msId(m)===A)[0]||{}).type===newType,
       JSON.stringify(R.notes.typeSaved));

    // ============ 9. THE ROUND TRIP. An edited date moves the marker =======
    // The proof that applyFieldOverrides() is actually wired into the build.
    // A form whose edits never reach the board is a form that lies.
    const colBefore=colOf(A);
    await open(A);
    const origDate=(MILESTONES.filter(m=>msId(m)===A)[0]||{}).date;
    const moved=new Date(origDate+'T00:00:00');
    moved.setDate(moved.getDate()+21);
    type('ms-date',fmtTipDate(moved.toISOString().slice(0,10)));
    await settle();
    $('ms-save-actions').querySelectorAll('.ms-act')[1].click();
    await settle(); await settle(); await settle();
    const colAfter=colOf(A);
    R.notes.roundTrip={before:colBefore,after:colAfter,
                       stored:(MS_FIELD_OVERRIDE[msKeyFor(withStart)]||{}).date,
                       closed:dlg().hidden};
    ck('round trip: Save and close closes the card',
       dlg().hidden, 'hidden='+String(dlg().hidden));
    ck('round trip: an edited finish date MOVES the marker on the board',
       colBefore!==null&&colAfter!==null&&colBefore!==colAfter,
       JSON.stringify(R.notes.roundTrip));
    // NEGATIVE CONTROL: clearing the override must put the marker back. A
    // one-way check passes on code that can move a milestone and never
    // restore it, which is the same shape as an override that cannot be
    // cleared.
    delete MS_FIELD_OVERRIDE[msKeyFor(withStart)];
    scheduleRerender(true); await settle(); await settle(); await settle();
    R.notes.reverted={col:colOf(A),want:colBefore,
                      date:(MILESTONES.filter(m=>msId(m)===A)[0]||{}).date,
                      wantDate:origDate};
    ck('round trip NEGATIVE CONTROL: clearing the override puts the marker back',
       colOf(A)===colBefore&&
       (MILESTONES.filter(m=>msId(m)===A)[0]||{}).date===origDate,
       JSON.stringify(R.notes.reverted));

    // ============ 10. What is editable, and what is not ============
    await open(A);
    const editable=['ms-title','ms-shorttitle-input','ms-start-date','ms-date',
                    'ms-weight','ms-float-val','ms-progress-input','ms-comment-text'];
    const notEditable=editable.filter(function(id){
      const e=$(id);
      return !e||e.readOnly||e.disabled||
             (e.tagName!=='INPUT'&&e.tagName!=='TEXTAREA');
    });
    R.notes.editable={checked:editable.length,notEditable:notEditable};
    ck('editable: every field the request names is a live, writable control',
       notEditable.length===0&&editable.length===8,
       editable.length+' checked, blocked: '+(notEditable.join(',')||'none'));
    const pred=$('ms-dep-pred-list'), succ=$('ms-dep-succ-list');
    ck('editable: predecessors and dependencies stay read-only, as excepted',
       !!pred&&!!succ&&pred.readOnly&&succ.readOnly,
       'pred readOnly='+(pred&&pred.readOnly)+' succ readOnly='+(succ&&succ.readOnly));
    ck('editable: the milestone ID is NOT a control, since it keys every store',
       code.tagName==='SPAN'&&!dlg().querySelector('input#ms-code'),
       code.tagName);
    // Escape discards, mirroring the close control it stands in for.
    type('ms-title','Escape should throw this away');
    await settle();
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    await settle(); await settle();
    R.notes.escape={closed:dlg().hidden,
                    storedTitle:(MS_FIELD_OVERRIDE[msKeyFor(withStart)]||{}).title||null};
    ck('escape: discards like the close control, storing nothing',
       dlg().hidden&&!(MS_FIELD_OVERRIDE[msKeyFor(withStart)]||{}).title,
       JSON.stringify(R.notes.escape));

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
        tmp = pathlib.Path(td) / "p43.html"
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

    # ---- source-level assertions ----
    # The override store has to reach every place an annotation store is
    # handled, or an edit survives on screen and vanishes on publish. Each of
    # these was a separate wiring site and a missed one is silent.
    for (label, needle) in [
        ("the publish payload", "milestoneFieldOverrides:MS_FIELD_OVERRIDE,"),
        ("selective import", "Object.assign(MS_FIELD_OVERRIDE,p.milestoneFieldOverrides||{})"),
        ("the CSV report", "csvEnteredCell(ms,MS_FIELD_OVERRIDE,"),
    ]:
        found = needle.replace(" ", "") in nospace
        checks.append((
            f"source: field edits reach {label}",
            found,
            "" if found else f"not found: {needle}"))
    checks.append((
        "source: field edits are carried when a milestone is moved to another row",
        nospace.count("MS_PROGRESS_OVERRIDE,MS_FIELD_OVERRIDE].forEach") == 2,
        f"{nospace.count('MS_PROGRESS_OVERRIDE,MS_FIELD_OVERRIDE].forEach')} of 2 key-migration sites"))
    # Applied from the ONE function every build path goes through, beside the
    # user-milestone merge, and from nowhere else. A second call site is how
    # this family of defect starts (TD-106, TD-145, TD-159).
    checks.append((
        "source: overrides are applied from exactly one place, beside the merge",
        src.count("applyFieldOverrides();") == 1
        and "mergeUserMilestones();" in src
        and src.index("applyFieldOverrides();") > src.index("mergeUserMilestones();"),
        f"{src.count('applyFieldOverrides();')} call sites"))
    # The key definition must not be able to move when an edited field moves.
    checks.append((
        "source: the annotation key reads the schedule's own type and date, not the edited ones",
        "const b=m._msBase||{};" in src and "'noid-'+m.ref+type+date" in src,
        "msKeyFor still composes from the live values"))
    checks.append((
        "source: the ID and the relationships are absent from the editable list",
        "const MS_EDITABLE_FIELDS=['actName','start','date','weight','floatD','type','marker']" in src,
        "the editable field list changed"))
    # The short title's own Save button is what was reported. It should be gone
    # rather than fixed in place beside a second save control.
    checks.append((
        "source: the short title's separate Save button is gone",
        "ms-shorttitle-save" not in src and "saveMsShortTitle" not in src,
        "a second save control for one field is still present"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if R.get("err"):
            print(f"PROBE ERROR at {w}x{h}:\n{R['err']}")
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("sample", "head", "dirty", "saved", "discard", "clickAway",
                  "columns", "typeMenu", "typeSaved", "roundTrip", "reverted",
                  "editable", "escape"):
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
