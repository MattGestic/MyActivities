#!/usr/bin/env python3
"""
P42 check (TEST-44): the status vocabulary, and two kinds of finished.

THE DISTINCTION IS THE FEATURE. A milestone the UPLOAD records as finished
paints in ink and reads "Complete". A milestone a PERSON marks off in the
current update paints green and reads "Done". Before this they were one state:
effectiveState() mapped a user override of 2 onto the schedule's own DONE, so
both rendered black and a reader could not tell what had just been marked off
from what arrived finished.

So the assertion that matters is not "green exists". It is that the two are
DIFFERENT, measured as computed colour on the rendered marker, on the same
milestone, before and after a person marks it. A check that only asserts the
green one would pass on code that painted everything green.

STORED VALUES KEEP THEIR MEANING. Health numbers 0 to 3 are unchanged and 4 is
new, because every published file and exported model already carries them and
renumbering would silently re-colour existing boards. Milestone override 2
still means "a person marked this", which is what it has always meant; only the
colour it resolves to has changed. Both are asserted against a round trip.

ONE VOCABULARY, THREE SURFACES. The board's status, the row health dot and the
filter chips all have to name the same thing the same way. The check reads the
labels off the live controls and requires them to match STATE_LABELS and
HEALTH_LABELS rather than a list typed in here, so a rename reaches all three or
fails.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p42_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p42-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p42-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const $=id=>document.getElementById(id);
  const iconOf=function(id){
    const w=document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
    if(!w) return null;
    const ic=w.querySelector('.ms-icon');
    if(!ic) return null;
    return {cls:ic.getAttribute('class'),colour:getComputedStyle(ic).color};
  };
  const visRows=()=>document.querySelectorAll('#tbody tr.data:not(.hidden-row)').length;

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();

    // ============ 1. The vocabulary ============
    R.notes.labels={state:STATE_LABELS,health:HEALTH_LABELS};
    ck('vocabulary: the six statuses read as asked',
       STATE_LABELS.CRIT==='Critical'&&STATE_LABELS.RISK==='At risk'&&
       STATE_LABELS.TRACK==='On track'&&STATE_LABELS.DONEUSER==='Done'&&
       STATE_LABELS.DONE==='Complete'&&STATE_LABELS.NA==='N/A',
       JSON.stringify(STATE_LABELS));
    ck('vocabulary: the health numbers say the same words',
       HEALTH_LABELS[0]==='N/A'&&HEALTH_LABELS[1]==='On track'&&
       HEALTH_LABELS[2]==='At risk'&&HEALTH_LABELS[3]==='Critical'&&
       HEALTH_LABELS[4]==='Done',
       JSON.stringify(HEALTH_LABELS));
    // Stored numbers must not have moved. 0-3 already exist in published files.
    ck('vocabulary: health 0 to 3 keep the numbers they always had',
       Object.keys(HEALTH_LABELS).length===5&&
       HEALTH_LABELS[1]==='On track'&&HEALTH_LABELS[2]==='At risk',
       Object.keys(HEALTH_LABELS).join(','));

    // ============ 2. THE DISTINCTION. Same milestone, before and after ====
    // Both samples must be RENDERED, not merely present in the data: a
    // milestone dated outside the visible week window draws no marker, and a
    // colour comparison against a marker that does not exist measures nothing.
    // The first draft of this check picked SNIP-101, which is dated 01-May and
    // off the board, and reported three failures about working code.
    const onBoard=function(m){
      return !!document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(msId(m)||'')+'"]'); };
    const uploadDone=MILESTONES.filter(function(m){
      return m.state==='DONE'&&msId(m)&&!m.userAdded&&onBoard(m); })[0];
    // One that is not, which a person will mark off.
    const notDone=MILESTONES.filter(function(m){
      return m.state!=='DONE'&&m.state!=='BASELINE'&&msId(m)&&!m.userAdded&&onBoard(m); })[0];
    R.notes.sample={uploadDone:uploadDone?msId(uploadDone):null,
                    notDone:notDone?msId(notDone):null,
                    notDoneState:notDone?notDone.state:null};
    ck('distinction: the board carries both a schedule-finished milestone and an unfinished one',
       !!uploadDone&&!!notDone, JSON.stringify(R.notes.sample));

    const completeIcon=iconOf(msId(uploadDone));
    // Mark the OTHER one off, the way a person does: the card's override store.
    const key=msKeyFor(notDone);
    MS_HEALTH_OVERRIDE[key]=2;
    scheduleRerender(true); await settle(); await settle(); await settle();
    const doneIcon=iconOf(msId(notDone));
    R.notes.colours={complete:completeIcon,done:doneIcon,
                     effComplete:effectiveState(uploadDone),
                     effDone:effectiveState(notDone)};
    ck('distinction: the upload’s finished milestone resolves to DONE and paints in ink',
       effectiveState(uploadDone)==='DONE'&&!!completeIcon&&
       /s-done(\s|$)/.test(completeIcon.cls),
       JSON.stringify(R.notes.colours.complete)+' state '+effectiveState(uploadDone));
    ck('distinction: a milestone a person marks resolves to DONEUSER, not to DONE',
       effectiveState(notDone)==='DONEUSER'&&!!doneIcon&&
       /s-doneuser/.test(doneIcon.cls),
       JSON.stringify(R.notes.colours.done)+' state '+effectiveState(notDone));
    // The measurement that matters: they are not the same colour.
    ck('distinction: THE TWO ARE DIFFERENT COLOURS on the rendered board',
       !!completeIcon&&!!doneIcon&&completeIcon.colour!==doneIcon.colour,
       'Complete '+(completeIcon&&completeIcon.colour)+
       ' against Done '+(doneIcon&&doneIcon.colour));
    // And green is the one a person set, ink the one the upload set. Asserted
    // by channel rather than by hex, so a token change does not fail this.
    const rgb=function(s){ const m=/(\d+),\s*(\d+),\s*(\d+)/.exec(s||'');
      return m?[+m[1],+m[2],+m[3]]:null; };
    const cRGB=rgb(completeIcon&&completeIcon.colour), dRGB=rgb(doneIcon&&doneIcon.colour);
    R.notes.rgb={complete:cRGB,done:dRGB};
    ck('distinction: the person-marked one is green, the upload one is dark',
       !!cRGB&&!!dRGB&&dRGB[1]>dRGB[0]&&dRGB[1]>dRGB[2]&&
       (cRGB[0]+cRGB[1]+cRGB[2])<200,
       'Complete rgb '+JSON.stringify(cRGB)+', Done rgb '+JSON.stringify(dRGB));
    // NEGATIVE CONTROL: clearing the override must put it back, not leave it
    // green. A one-way check passes on code that can never undo the mark.
    delete MS_HEALTH_OVERRIDE[key];
    scheduleRerender(true); await settle(); await settle(); await settle();
    const reverted=iconOf(msId(notDone));
    R.notes.reverted={cls:reverted&&reverted.cls,state:effectiveState(notDone)};
    ck('distinction NEGATIVE CONTROL: clearing the mark returns it to the schedule’s own state',
       effectiveState(notDone)===notDone.state&&!!reverted&&
       !/s-doneuser/.test(reverted.cls),
       JSON.stringify(R.notes.reverted)+' against schedule state '+notDone.state);

    // ============ 2b. The distinction survives the dark theme ==============
    // theme_check cannot carry this. Its "constant" probes are informational:
    // a probe that starts toggling is reported as toggling and still exits 0,
    // so a s-doneuser rule that stopped applying would pass there silently.
    // The assertion has to read the real colours, which is what this file
    // already does, so it is made here instead.
    MS_HEALTH_OVERRIDE[key]=2;
    const themeWas=document.documentElement.getAttribute('data-theme');
    document.documentElement.setAttribute('data-theme','dark');
    scheduleRerender(true); await settle(); await settle(); await settle();
    const dkComplete=iconOf(msId(uploadDone)), dkDone=iconOf(msId(notDone));
    const dkC=rgb(dkComplete&&dkComplete.colour), dkD=rgb(dkDone&&dkDone.colour);
    R.notes.dark={complete:dkC,done:dkD};
    // Green carries the same meaning in either theme. P55 (palette Option A)
    // lifts the dark value so it reads on the dark surface, so the check is
    // that it stays green (green channel dominant), not that the bytes match.
    ck('dark theme: the person-marked marker is still green',
       !!dkD&&!!dRGB&&dkD[1]>dkD[0]+40&&dkD[1]>dkD[2]+30&&dRGB[1]>dRGB[0]+40,
       'light '+JSON.stringify(dRGB)+' against dark '+JSON.stringify(dkD));
    // The upload one paints from ink, so it must follow the theme and go light.
    ck('dark theme: the upload’s finished milestone follows the ink and goes light',
       !!dkC&&(dkC[0]+dkC[1]+dkC[2])>400,
       'light '+JSON.stringify(cRGB)+' against dark '+JSON.stringify(dkC));
    // Which is the point: still two different colours, not both light.
    ck('dark theme: the two are still different colours',
       !!dkComplete&&!!dkDone&&dkComplete.colour!==dkDone.colour,
       'Complete '+(dkComplete&&dkComplete.colour)+
       ' against Done '+(dkDone&&dkDone.colour));
    if(themeWas) document.documentElement.setAttribute('data-theme',themeWas);
    else document.documentElement.removeAttribute('data-theme');
    delete MS_HEALTH_OVERRIDE[key];
    scheduleRerender(true); await settle(); await settle();

    // ============ 3. Both kinds of finished still count as finished =======
    // credit:1 drives the rollup, and a person marking something off must not
    // silently remove it from the completed total.
    R.notes.credit={DONE:STATES.DONE.credit,DONEUSER:STATES.DONEUSER.credit};
    ck('rollup: both kinds of finished carry credit, so marking one off does not lose it',
       STATES.DONE.credit===1&&STATES.DONEUSER.credit===1,
       JSON.stringify(R.notes.credit));

    // ============ 4. The filter chips ============
    toggleTopFilterBar(true); await settle();
    const chips=Array.prototype.map.call(
      document.querySelectorAll('#filter-status-group .st-chip'),function(b){
        return {id:b.id.replace(/^fs-/,''),label:b.textContent.trim()}; });
    R.notes.chips=chips;
    ck('chips: one per filterable status, in the declared order',
       chips.length===STATUS_FILTER_KEYS.length&&
       chips.every(function(c,i){ return c.id===STATUS_FILTER_KEYS[i]; }),
       chips.map(function(c){return c.id;}).join(','));
    // Read off the controls, matched against the labels, so a rename that
    // reaches the board and misses a chip fails here.
    const mismatched=chips.filter(function(c){ return c.label!==STATE_LABELS[c.id]; });
    ck('chips: every chip is labelled from the one vocabulary',
       mismatched.length===0,
       mismatched.map(function(c){return c.id+' reads "'+c.label+'"';}).join('; ')||'all match');
    // The two kinds of finished filter separately.
    // A person marks one off first, so the Done filter has something to find.
    // Without it Done matches nothing and "different results" would be
    // satisfied by zero, which is a pass that proves nothing.
    MS_HEALTH_OVERRIDE[key]=2;
    scheduleRerender(true); await settle(); await settle(); await settle();
    const base=visRows();
    toggleStatusFilter('DONE'); await settle();
    const onlyComplete=visRows();
    toggleStatusFilter('DONE'); toggleStatusFilter('DONEUSER'); await settle();
    const onlyDone=visRows();
    R.notes.chipFilter={base:base,onlyComplete:onlyComplete,onlyDone:onlyDone,
                        markedOff:msId(notDone)};
    ck('chips: Complete and Done are separate filters, each finding its own rows',
       onlyComplete>0&&onlyComplete<base&&onlyDone>0&&onlyDone<base&&
       onlyComplete!==onlyDone,
       JSON.stringify(R.notes.chipFilter));
    clearCriticalFilters(); delete MS_HEALTH_OVERRIDE[key];
    scheduleRerender(true); await settle(); await settle();

    // ============ 5. The row health picker ============
    const dot=document.querySelector('#tbody .health-dot');
    dot.dispatchEvent(new MouseEvent('click',{bubbles:true}));
    await settle();
    const items=Array.prototype.map.call(
      document.querySelectorAll('.health-picker .health-picker-item'),function(it){
        return it.textContent.trim(); });
    R.notes.picker=items;
    ck('picker: it offers the five settable health values',
       items.length===5, items.join(' | '));
    // Every label must come from HEALTH_LABELS, so the picker cannot drift from
    // the CSV column or the tooltip.
    const unknown=items.filter(function(lbl){
      return !Object.keys(HEALTH_LABELS).some(function(k){
        return lbl===HEALTH_LABELS[k]||lbl===HEALTH_LABELS[k]+' / clear'; }); });
    ck('picker: every option is named from the one vocabulary',
       unknown.length===0, unknown.join('; ')||'all match');
    ck('picker: Critical replaced Issue / delayed, and Done was added',
       items.indexOf('Critical')>=0&&items.indexOf('Done')>=0&&
       items.indexOf('Issue / delayed')<0, items.join(' | '));
    closeHealthPicker();
    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=e&&e.stack; }
  emit();
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p42.html"
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
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(root / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()
    html = pathlib.Path(a.html)
    src = html.read_text(encoding="utf-8", errors="replace")
    nospace = src.replace(" ", "").replace("\n", "")

    checks = []
    vers = len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src))
    checks.append(("source: exactly one version literal", vers == 1, f"{vers} found"))
    checks.append((
        "source: a user override resolves to DONEUSER, never to the upload's DONE",
        "if(ov===2)return'DONEUSER';" in nospace and "if(ov===2)return'DONE';" not in nospace,
        "the override still collapses into the schedule's state"))
    checks.append((
        "source: the two finished states have their own colour tokens",
        "--color-icon-doneuser:var(--color-status-done)" in nospace
        and "--color-icon-done:var(--color-text-ink)" in nospace,
        "the pair does not differ by token"))
    checks.append((
        "source: one list of filterable statuses, read by both the chips and the summary",
        src.count("const STATUS_FILTER_KEYS=") == 1
        and src.count("STATUS_FILTER_KEYS") == 3,
        f"{src.count('STATUS_FILTER_KEYS')} references, expected 3"))
    checks.append((
        "source: the picker labels come from HEALTH_LABELS, not from typed strings",
        "label:HEALTH_LABELS[3]" in nospace and "'Issue/delayed'" not in nospace,
        "a label is still typed at the picker"))
    checks.append((
        "source: both kinds of finished are treated as actualised",
        "m.state==='DONE'||m.state==='DONEUSER'" in src,
        "the actualised test knows only one of them"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("labels", "sample", "colours", "rgb", "reverted", "credit",
                  "chips", "chipFilter", "picker"):
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
