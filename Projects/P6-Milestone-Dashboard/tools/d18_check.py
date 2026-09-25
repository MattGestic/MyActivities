#!/usr/bin/env python3
"""
D-18 check (TEST-??): the on-board "edited" mark.

A milestone whose effective Finish/Start date, health/status, or progress
comes from a user override (MS_FIELD_OVERRIDE / MS_HEALTH_OVERRIDE /
MS_PROGRESS_OVERRIDE, keyed by msKeyFor()) now carries a small mark beside its
board icon, reusing the P44 card's own .ms-edited-mark class/token/colour. A
Finish override that crosses a week column also leaves a faint ghost tick
(.m-edit-ghost) in the SOURCE week, reusing the baseline ghost's own styling.

Everything here manipulates the override STORES directly rather than driving
the milestone card's UI, because that is the actual annotation layer
(architecture: schedule data / annotation layer / display state stay
separate) and it lets each store be set to values a normal save could never
produce on its own — an override literally equal to the source, in
particular, which a real save always deletes rather than storing (TD-174's
own put()), so testing msEditedFields()'s OWN dedup rather than that guard
requires writing the store directly.

Read the DOM (classList, title, getBoundingClientRect), never a screenshot.

Usage:
  python3 tools/d18_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="d18-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='d18-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,260));
  const $=id=>document.getElementById(id);
  const wrapOf=m=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(msId(m))+'"]');
  const markOf=m=>{ const w=wrapOf(m); return w?w.querySelector('.m-board-edit-mark'):null; };
  const isoOf=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  const rerenderNow=async function(){ scheduleRerender(true); await settle(); };

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle();

    // A pool of milestones actually on the board, with a real id (so wrapOf
    // can find them) and a Finish date inside the visible weeks (so a Finish
    // override has somewhere valid to move to and a column to test against).
    // The progress-bearing tests need m.progress to be a real number, or the
    // '(none)' formatting branch would fire and the exact-tooltip assertion
    // would compare against the wrong shape.
    const pool=MILESTONES.filter(function(m){
      return msId(m)&&wrapOf(m)&&dateToCol(m.date)>=0&&!m.userAdded;
    });
    const mDate=pool[0], mHealth=pool[1], mUntouched=pool[2], mSameWeek=pool[3];
    const used={}; [mDate,mHealth,mUntouched,mSameWeek].forEach(function(m){used[msId(m)]=1;});
    const withProgress=pool.filter(function(m){ return m.progress!=null&&!used[msId(m)]; });
    R.notes.poolSize=pool.length;
    ck('setup: enough milestones on the board to sample from',
       pool.length>=6&&withProgress.length>=2, 'pool='+pool.length+', withProgress='+withProgress.length);

    const mProg=withProgress[0], mEqual=withProgress[1];
    R.notes.sample={date:msId(mDate),health:msId(mHealth),progress:msId(mProg),
                    untouched:msId(mUntouched),equal:msId(mEqual),sameWeek:msId(mSameWeek)};

    // ============ 0. NEGATIVE CONTROL: an untouched milestone has no mark ===
    ck('untouched: no mark, no ghost, on a milestone nobody has edited',
       !markOf(mUntouched)&&document.querySelectorAll('.m-edit-ghost').length===0,
       'mark='+!!markOf(mUntouched));

    // ============ 1. Date (Finish) override, crossing a week column =========
    const srcCol=dateToCol(mDate.date);
    const targetCol=(srcCol+3<WE_DATES.length)?srcCol+3:Math.max(0,srcCol-3);
    const targetIso=isoOf(WE_DATES[targetCol]);
    const srcDateKey=msKeyFor(mDate);
    MS_FIELD_OVERRIDE[srcDateKey]={date:targetIso};
    await rerenderNow();
    const dMark=markOf(mDate);
    R.notes.dateMark={present:!!dMark,title:dMark?dMark.getAttribute('title'):null,
                      srcCol:srcCol,targetCol:targetCol};
    ck('date override: the mark appears on the edited milestone',
       !!dMark, JSON.stringify(R.notes.dateMark));
    const wantLine='Finish edited: source '+fmtTipDate(mDate._msBase.date)+
                   ', now '+fmtTipDate(mDate.date);
    ck('date override: the tooltip reports the source and the current value, one line',
       !!dMark&&dMark.getAttribute('title')===wantLine,
       JSON.stringify({want:wantLine,got:dMark&&dMark.getAttribute('title')}));
    const srcTd=document.querySelectorAll('#tbody tr[data-ref="'+mDate.ref+'"] td.c-wk')[srcCol];
    const ghosts=srcTd?srcTd.querySelectorAll('.m-edit-ghost').length:-1;
    R.notes.crossWeekGhost={srcCol:srcCol,newCol:dateToCol(mDate.date),ghosts:ghosts};
    ck('date override across weeks: exactly one ghost tick in the SOURCE week',
       dateToCol(mDate.date)!==srcCol&&ghosts===1, JSON.stringify(R.notes.crossWeekGhost));
    ck('date override across weeks: no ghost anywhere else for this milestone',
       document.querySelectorAll('.m-edit-ghost').length===1,
       'total ghosts='+document.querySelectorAll('.m-edit-ghost').length);

    // Icon geometry: the mark must not change what the icon itself is.
    const icon=wrapOf(mDate).querySelector('.ms-icon');
    const untouchedIcon=wrapOf(mUntouched).querySelector('.ms-icon');
    const iconBox=icon.getBoundingClientRect(), markBox=dMark.getBoundingClientRect();
    const iconSizeEdited=Math.round(iconBox.width), iconSizeUnedited=Math.round(untouchedIcon.getBoundingClientRect().width);
    const overlap=!(markBox.right<=iconBox.left||markBox.left>=iconBox.right||
                    markBox.bottom<=iconBox.top||markBox.top>=iconBox.bottom);
    R.notes.geometry={iconBox:{l:Math.round(iconBox.left),t:Math.round(iconBox.top),
                               w:Math.round(iconBox.width),h:Math.round(iconBox.height)},
                      markBox:{l:Math.round(markBox.left),t:Math.round(markBox.top),
                               w:Math.round(markBox.width),h:Math.round(markBox.height)},
                      overlap:overlap,iconSizeEdited:iconSizeEdited,iconSizeUnedited:iconSizeUnedited};
    ck('geometry: the mark box does not overlap the icon box',
       !overlap, JSON.stringify(R.notes.geometry));
    ck('geometry: the icon itself is the same size edited or not',
       iconSizeEdited===iconSizeUnedited,
       iconSizeEdited+'px edited vs '+iconSizeUnedited+'px unedited');

    // ============ 1b. Same-week Finish override: mark, no ghost =============
    const swKey=msKeyFor(mSameWeek);
    const swCol=dateToCol(mSameWeek.date);
    const swSrc=new Date(mSameWeek.date+'T00:00:00');
    // Nudge by one day, clamped to stay inside the same week-ending column:
    // back off a day if that would push past the week end, forward a day if
    // it would push before the week start (whichever direction stays in-week
    // depends on where in the week the source date already falls).
    let swDate=new Date(swSrc.getTime());
    swDate.setDate(swDate.getDate()+(dateToCol(isoOf(new Date(swSrc.getFullYear(),swSrc.getMonth(),swSrc.getDate()+1)))===swCol?1:-1));
    const swIso=isoOf(swDate);
    MS_FIELD_OVERRIDE[swKey]={date:swIso};
    await rerenderNow();
    const swMark=markOf(mSameWeek);
    const swGhostCount=document.querySelectorAll('.m-edit-ghost').length;
    R.notes.sameWeek={srcCol:swCol,newCol:dateToCol(mSameWeek.date),
                      mark:!!swMark,totalGhosts:swGhostCount};
    ck('date override, SAME week: the mark still appears',
       !!swMark, JSON.stringify(R.notes.sameWeek));
    ck('date override, SAME week: no ghost tick is drawn (nothing moved columns)',
       dateToCol(mSameWeek.date)===swCol&&swGhostCount===1 /* the P1 cross-week ghost only */,
       JSON.stringify(R.notes.sameWeek));
    delete MS_FIELD_OVERRIDE[swKey];

    // ============ 2. Health override =========================================
    const hKey=msKeyFor(mHealth);
    const srcState=mHealth.state;
    const hOv=(srcState==='TRACK')?3:1; // land on a state guaranteed to differ
    MS_HEALTH_OVERRIDE[hKey]=hOv;
    await rerenderNow();
    const hMark=markOf(mHealth);
    const wantHealthLine='Health edited: source '+(STATE_LABELS[srcState]||srcState)+
                         ', now '+(STATE_LABELS[effectiveState(mHealth)]||effectiveState(mHealth));
    R.notes.healthMark={present:!!hMark,title:hMark?hMark.getAttribute('title'):null,
                        src:srcState,now:effectiveState(mHealth)};
    ck('health override: the mark appears',
       !!hMark, JSON.stringify(R.notes.healthMark));
    ck('health override: the tooltip line matches source/now exactly',
       !!hMark&&hMark.getAttribute('title')===wantHealthLine,
       JSON.stringify({want:wantHealthLine,got:hMark&&hMark.getAttribute('title')}));

    // Clearing it removes the mark.
    delete MS_HEALTH_OVERRIDE[hKey];
    await rerenderNow();
    R.notes.healthCleared={mark:!!markOf(mHealth)};
    ck('health override CLEARED: the mark is gone',
       !markOf(mHealth), JSON.stringify(R.notes.healthCleared));

    // ============ 3. Progress override =======================================
    const pKey=msKeyFor(mProg);
    const srcProg=mProg.progress==null?0:mProg.progress;
    const newProg=Math.min(100,srcProg+37<=100?srcProg+37:srcProg-37);
    MS_PROGRESS_OVERRIDE[pKey]=newProg;
    await rerenderNow();
    const pMark=markOf(mProg);
    const wantProgLine='Progress edited: source '+srcProg+'%, now '+newProg+'%';
    R.notes.progMark={present:!!pMark,title:pMark?pMark.getAttribute('title'):null,
                      src:srcProg,now:newProg};
    ck('progress override: the mark appears',
       !!pMark, JSON.stringify(R.notes.progMark));
    ck('progress override: the tooltip line matches source/now exactly',
       !!pMark&&pMark.getAttribute('title')===wantProgLine,
       JSON.stringify({want:wantProgLine,got:pMark&&pMark.getAttribute('title')}));

    // Clearing it (delete, the way a card that restores the schedule's value
    // does) removes the mark.
    delete MS_PROGRESS_OVERRIDE[pKey];
    await rerenderNow();
    ck('progress override CLEARED: the mark is gone',
       !markOf(mProg), 'mark='+!!markOf(mProg));

    // ============ 4. An override EQUAL to the source is not an edit =========
    // Written directly to the store (bypassing saveMsDialog's own delete-on-
    // match guard), so this proves msEditedFields() itself treats "equal to
    // source" as no edit, not merely that a real save never stores one.
    const eKey=msKeyFor(mEqual);
    MS_PROGRESS_OVERRIDE[eKey]=(mEqual.progress==null?0:mEqual.progress);
    await rerenderNow();
    R.notes.equalOverride={stored:MS_PROGRESS_OVERRIDE[eKey],source:mEqual.progress,
                           mark:!!markOf(mEqual)};
    ck('override EQUAL to the source value: no mark, even though the store holds one',
       !markOf(mEqual), JSON.stringify(R.notes.equalOverride));
    delete MS_PROGRESS_OVERRIDE[eKey];
    await rerenderNow();

    // ============ 5. User-added milestones are never marked =================
    const usr=MILESTONES.filter(function(m){return m.userAdded;})[0];
    if(usr){
      const uKey=msKeyFor(usr);
      MS_PROGRESS_OVERRIDE[uKey]=(usr.progress==null?0:usr.progress)+10;
      MS_HEALTH_OVERRIDE[uKey]=1;
      await rerenderNow();
      const uWrap=document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(msId(usr)||'')+'"]')||
                  wrapOf(usr);
      R.notes.userAdded={found:true,fields:msEditedFields(usr).length};
      ck('user-added milestone: never marked, even with overrides set on it',
         msEditedFields(usr).length===0,
         'msEditedFields returned '+msEditedFields(usr).length+' entries');
      delete MS_PROGRESS_OVERRIDE[uKey]; delete MS_HEALTH_OVERRIDE[uKey];
      await rerenderNow();
    } else {
      R.notes.userAdded={found:false};
      ck('user-added milestone: none on this board to test (skipped, not failed)',
         true,'no userAdded milestone present');
    }

    // ============ 6. Legend =================================================
    const legendSwatch=document.querySelector('.legend .ms-edited-mark.li-swatch');
    const legendRow=legendSwatch?legendSwatch.closest('.li'):null;
    R.notes.legend={present:!!legendSwatch,
                    text:legendRow?legendRow.textContent.replace(/\s+/g,' ').trim():null};
    ck('legend: an entry reading "Edited, not the source value" is present',
       !!legendSwatch&&/Edited, not the source value/.test(R.notes.legend.text||''),
       JSON.stringify(R.notes.legend));

    // ============ 7. Re-apply one mark, then check print mode and theme =====
    MS_HEALTH_OVERRIDE[hKey]=hOv;
    await rerenderNow();
    document.body.classList.add('print-mode');
    await settle();
    const printMark=markOf(mHealth);
    const printVisible=printMark&&printMark.getBoundingClientRect().width>0&&
                        getComputedStyle(printMark).display!=='none'&&
                        getComputedStyle(printMark).visibility!=='hidden';
    R.notes.print={present:!!printMark,visible:printVisible};
    ck('print mode: the mark is present and visibly rendered',
       printVisible, JSON.stringify(R.notes.print));
    const printLegend=document.querySelector('.legend .ms-edited-mark.li-swatch');
    ck('print mode: the legend entry is still present',
       !!printLegend&&getComputedStyle(printLegend.closest('.legend-row')).display!=='none',
       'present='+!!printLegend);
    document.body.classList.remove('print-mode');
    await settle();

    // ============ 8. Dark theme toggles the mark's colour ====================
    const lightColor=getComputedStyle(markOf(mHealth)).color;
    document.documentElement.setAttribute('data-theme','dark');
    await settle();
    const darkColor=getComputedStyle(markOf(mHealth)).color;
    document.documentElement.setAttribute('data-theme','light');
    R.notes.theme={light:lightColor,dark:darkColor};
    ck('dark theme: the mark’s colour differs from light (it toggles, not frozen)',
       lightColor!==darkColor, JSON.stringify(R.notes.theme));

    delete MS_HEALTH_OVERRIDE[hKey];
    delete MS_FIELD_OVERRIDE[srcDateKey];
    await rerenderNow();

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
        tmp = pathlib.Path(td) / "d18.html"
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

    checks.append((
        "source: msEditedFields exists as one helper",
        src.count("function msEditedFields(") == 1,
        f"found {src.count('function msEditedFields(')} definitions"))
    checks.append((
        "source: the board mark reuses the P44 card mark's own class",
        "ms-edited-mark m-board-edit-mark" in src,
        "renderMarker does not append the shared class pair"))
    checks.append((
        "source: the mark sits outside the icon box (negative offsets, not inside it)",
        bool(re.search(r"\.m-board-edit-mark\{[^}]*top:-\d", nospace)) and
        bool(re.search(r"\.m-board-edit-mark\{[^}]*right:-\d", nospace)),
        "no negative top/right offset found on .m-board-edit-mark"))
    checks.append((
        "source: the edit ghost is a distinct class from the baseline ghost",
        "m-edit-ghost" in nospace and ".m-ghost.m-wrap" in nospace,
        "m-edit-ghost class is missing"))
    checks.append((
        "source: the legend carries the edited-mark entry",
        "Edited, not the source value" in src,
        "legend text not found"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        if R.get("err"):
            print(f"PROBE ERROR at {w}x{h}:\n{R['err']}")
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("poolSize", "sample", "dateMark", "crossWeekGhost", "geometry",
                  "sameWeek", "healthMark", "healthCleared", "progMark",
                  "equalOverride", "userAdded", "legend", "print", "theme"):
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
