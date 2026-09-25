#!/usr/bin/env python3
"""
P29 check (TEST-32): the settings panel design system.

This partial changes no behaviour and no data. It replaces the drawer's
ad-hoc markup with a component set, one spacing contract and four tabs. So
the question here is not "does it look tidier" but the three things that
would actually make it a regression:

  CONSISTENCY. The panel carried 31 inline padding/margin declarations across
  18 distinct values. Consistency claimed by eye is consistency that drifts
  back on the next change, so every edge, every row step, every radius and
  every helper-text style is measured, and the inline-spacing count must be
  zero rather than merely smaller.

  WIRING. Every control in this panel is bound by an inline onclick/onchange
  to a named function, and the rebuild moved all of them. A handler naming a
  function that no longer exists fails silently at runtime and looks perfect
  in a screenshot, so every control is checked against the live window.

  NOTHING ELSE MOVED. The board is rebuilt from the same data by the same
  pipeline, so its row, marker, task and milestone counts must be identical
  to the P28 snapshot.

Every assertion that measures a SET also asserts its own sample size. Four
separate assertions in this project have passed against zero elements.

Usage:
  python3 tools/p29_check.py [--xlsx FILE] [--html FILE]
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
from import_check import build_aoa, find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p29-out">(.*?)</pre>', re.S)

# The board as P28 left it. Hard-coded on purpose: this partial must not move
# any of them, so a changed number is a failure, not a new baseline.
EXPECT_BASELINE = {"rows": 159, "markers": 196, "tasks": 159, "milestones": 198}
# And the same workbook through the same pipeline. Rows and milestones here are
# what tools/order_check.py derives independently from the sheet, so these two
# are cross-checked rather than self-reported.
EXPECT_IMPORTED = {"rows": 105, "tasks": 105, "milestones": 146}

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p29-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  function freeze(){
    const s=document.createElement('style');
    s.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(s); void document.body.offsetWidth;
  }
  const uniq=function(a){ return Array.from(new Set(a)); };
  const shown=function(el){ return !!el && el.offsetParent!==null; };

  try{
    window.XLSX={
      read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
      utils:{ sheet_to_json:function(s){ return s.__aoa; } }
    };
    const DR=document.getElementById('settings-drawer');
    if(!DR) throw new Error('#settings-drawer missing');
    const snapBoard=function(){ return {
      rows:document.querySelectorAll('#tbody tr.data').length,
      markers:document.querySelectorAll('.m-wrap:not(.m-ghost)').length,
      tasks:(typeof TASKS!=='undefined')?TASKS.length:-1,
      milestones:(typeof MILESTONES!=='undefined')?MILESTONES.length:-1
    }; };
    // Taken before a single control is touched, so it is the shipped baseline
    // board and not something this probe has already changed.
    R.notes.boardBefore=snapBoard();
    toggleSettingsDrawer(true);
    await settle(); freeze();

    // ================= 1. The spacing contract =================
    // The headline number. Not "fewer than before": none.
    const inlineBad=[];
    DR.querySelectorAll('*').forEach(function(el){
      const st=el.getAttribute('style')||'';
      if(/(^|;)\s*(padding|margin)/.test(st)) inlineBad.push((el.id||el.className||el.tagName)+' :: '+st);
    });
    R.notes.inlineSpacing=inlineBad.slice(0,10);
    R.notes.drawerEls=DR.querySelectorAll('*').length;
    ck('spacing: the drawer has elements to audit at all',
       DR.querySelectorAll('*').length>100, R.notes.drawerEls+' elements');
    ck('spacing: no element in the drawer sets padding or margin inline',
       inlineBad.length===0, inlineBad.length+' found (was 31)');

    // One gutter. Measured on the real groups, not a constructed one.
    const groups=Array.from(DR.querySelectorAll('.sd-group'));
    const gutters=uniq(groups.map(function(g){
      const cs=getComputedStyle(g); return cs.paddingLeft+'|'+cs.paddingRight;
    }));
    R.notes.groups=groups.length; R.notes.gutters=gutters;
    ck('spacing: there are groups to measure', groups.length>=4, groups.length+' groups');
    ck('spacing: every group uses the same left and right gutter',
       gutters.length===1, gutters.join(' / '));
    const gutterPx=groups.length?getComputedStyle(groups[0]).paddingLeft:'';
    ck('spacing: the gutter is the token value, 16px', gutterPx==='16px', gutterPx);

    // One vertical step. :first-child and :last-child zero their outer edge on
    // purpose, so those are excluded rather than allowed to widen the set.
    const rows=Array.from(DR.querySelectorAll('.sd-row'));
    const midRows=rows.filter(function(r){
      return r.previousElementSibling && r.nextElementSibling;
    });
    const steps=uniq(midRows.map(function(r){
      const cs=getComputedStyle(r); return cs.paddingTop+'|'+cs.paddingBottom;
    }));
    R.notes.rows=rows.length; R.notes.midRows=midRows.length; R.notes.rowSteps=steps;
    ck('spacing: there are interior rows to measure', midRows.length>=3, midRows.length+' of '+rows.length);
    ck('spacing: every interior row uses the same vertical step',
       steps.length===1, steps.join(' / '));
    ck('spacing: the row step is the token value, 12px',
       midRows.length>0 && getComputedStyle(midRows[0]).paddingTop==='12px',
       midRows.length?getComputedStyle(midRows[0]).paddingTop:'no sample');

    // One hairline between rows.
    const seps=rows.filter(function(r){ return r.previousElementSibling &&
      r.previousElementSibling.classList.contains('sd-row'); });
    const sepStyles=uniq(seps.map(function(r){
      const cs=getComputedStyle(r); return cs.borderTopWidth+'|'+cs.borderTopColor;
    }));
    R.notes.seps=seps.length; R.notes.sepStyles=sepStyles;
    ck('spacing: there are row separators to measure', seps.length>=2, seps.length);
    ck('spacing: every row separator is the same hairline',
       sepStyles.length===1, sepStyles.join(' / '));

    // One radius family. Any value outside the three tokens is a new one-off.
    const ALLOWED=['4px','6px','999px','0px'];
    const surfaces=Array.from(DR.querySelectorAll('.sd-card,.sd-choice-body,.sd-badge,.sd-tab,.imp-fail,.sd-icon-opt'));
    const badRadius=[];
    surfaces.forEach(function(el){
      const r=getComputedStyle(el).borderTopLeftRadius;
      if(ALLOWED.indexOf(r)<0) badRadius.push((el.className||el.tagName)+'='+r);
    });
    R.notes.surfaces=surfaces.length; R.notes.badRadius=badRadius.slice(0,8);
    ck('spacing: there are bordered surfaces to measure', surfaces.length>=4, surfaces.length);
    ck('spacing: every bordered surface uses a radius token',
       badRadius.length===0, badRadius.join(', '));

    // Helper text upright. 9px italic was the least legible text in the panel.
    const helps=Array.from(DR.querySelectorAll('.sd-row-help,.sd-group-desc,.sd-choice-help,.sd-note'));
    const italic=helps.filter(function(h){ return getComputedStyle(h).fontStyle!=='normal'; });
    R.notes.helps=helps.length;
    ck('type: there is helper text to measure', helps.length>=6, helps.length);
    ck('type: no helper text is italic', italic.length===0, italic.length+' italic');

    // ================= 2. Layout =================
    R.notes.drawerWidth=getComputedStyle(DR).width;
    ck('layout: the drawer is 360px wide', getComputedStyle(DR).width==='360px', R.notes.drawerWidth);
    const strip=DR.querySelector('.sd-tabs');
    ck('layout: the tab strip scrolls rather than wrapping',
       !!strip && getComputedStyle(strip).overflowX==='auto' && getComputedStyle(strip).flexWrap!=='wrap',
       strip?getComputedStyle(strip).overflowX+'/'+getComputedStyle(strip).flexWrap:'missing');
    // The action bar moved above the tabs at v3.1.0-P39 (TD-149), so it is no
    // longer a sticky footer. The contract it replaces: it is the first thing
    // in the drawer under the heading, above the tab strip, and on screen
    // without scrolling when the drawer opens. Asserted in BOTH document order
    // and geometry, because either alone can be satisfied while the other is
    // wrong. The old sticky assertion's companion check ("still on screen when
    // scrolled to the foot") could pass vacuously whenever the open tab was
    // short enough not to scroll, so it is not carried over in that form.
    const act=DR.querySelector('.sd-actions');
    R.notes.actionsPos=act?getComputedStyle(act).position:'missing';
    ck('layout: the action bar comes before the tab strip in document order',
       !!act && !!strip &&
       (act.compareDocumentPosition(strip)&Node.DOCUMENT_POSITION_FOLLOWING)!==0,
       act?'position '+R.notes.actionsPos:'missing');
    DR.scrollTop=0; await settle();
    const ar=act.getBoundingClientRect(), dr=DR.getBoundingClientRect();
    const sr=strip.getBoundingClientRect();
    R.notes.actionsBox=Math.round(ar.top)+'..'+Math.round(ar.bottom)+
                       ' drawer '+Math.round(dr.top)+'..'+Math.round(dr.bottom)+
                       ' tabs at '+Math.round(sr.top);
    ck('layout: it sits above the tabs and is on screen with the drawer opened',
       ar.bottom<=sr.top+1 && ar.top>=dr.top-1 && ar.bottom<=dr.bottom,
       R.notes.actionsBox);
    // One row at v3.1.0-P40, changed from the two-row shape P39 shipped: the
    // two exports spread across the left, the two right-hand actions anchored
    // together against the edge. The P39 arrangement put the destructive
    // action on its own line; the user asked for it back in line with Save as
    // new dashboard, so the assertion follows the requested contract rather
    // than the one this check preferred. What it still asserts with teeth: the
    // order, the right anchor, and that the destructive button is LAST, so it
    // is never the one next to the button you meant to press.
    const main=act.querySelector('.sd-actions-main');
    const exports=act.querySelector('.sd-actions-exports');
    const right=act.querySelector('.sd-actions-right');
    const danger=act.querySelector('.sd-actions-right .sd-btn-danger');
    const lbl=function(b){ return b.textContent.replace(/[^A-Za-z ]/g,'').trim(); };
    const expLabels=exports?Array.prototype.map.call(exports.querySelectorAll('button'),lbl):[];
    const rightLabels=right?Array.prototype.map.call(right.querySelectorAll('button'),lbl):[];
    R.notes.actionOrder={exports:expLabels,right:rightLabels};
    ck('layout: CSV and JSON on the left, Save then Reset on the right',
       expLabels.length===2 && /CSV/.test(expLabels[0]) && /JSON/.test(expLabels[1]) &&
       rightLabels.length===2 && /Save as new dashboard/.test(rightLabels[0]) &&
       /Reset row marks/.test(rightLabels[1]),
       expLabels.join(' | ')+'  ///  '+rightLabels.join(' | '));
    const rr=right?right.getBoundingClientRect():null;
    const mr=main?main.getBoundingClientRect():null;
    ck('layout: the right-hand pair is anchored to the right edge of the row',
       !!rr && !!mr && Math.abs(rr.right-mr.right)<=1,
       rr?Math.round(rr.right)+' against row right '+Math.round(mr.right):'missing');
    // Spread, not bunched: the two exports must not simply sit side by side at
    // the left, which is what removing the justify-content would give.
    const eb=exports?exports.querySelectorAll('button'):[];
    const gap=(eb.length===2)
      ? Math.round(eb[1].getBoundingClientRect().left-eb[0].getBoundingClientRect().right)
      : -1;
    R.notes.exportGap=gap;
    ck('layout: the two exports are distributed across their share of the width',
       gap>12, gap+'px between them');
    const db=danger?danger.getBoundingClientRect():null;
    R.notes.dangerBox=db?Math.round(db.left)+' vs row right '+Math.round(mr.right):'missing';
    ck('layout: the destructive action is the last control in the row',
       !!db && !!rr && Math.abs(db.right-rr.right)<=1, R.notes.dangerBox);

    // ================= 3. Tabs =================
    const panels=Array.from(DR.querySelectorAll('.sd-tabpanel'));
    const tabs=Array.from(DR.querySelectorAll('.sd-tab'));
    R.notes.panels=panels.length; R.notes.tabs=tabs.length;
    ck('tabs: four tabs and four panels', tabs.length===4 && panels.length===4,
       tabs.length+' tabs / '+panels.length+' panels');
    const tabResults=[];
    ['sources','import','defaults'].forEach(function(t){
      setSettingsTab(t);
      const visible=panels.filter(function(p){ return !p.hidden; }).map(function(p){ return p.getAttribute('data-tab'); });
      const actives=tabs.filter(function(b){ return b.classList.contains('is-active'); });
      tabResults.push({tab:t,visible:visible,actives:actives.length});
    });
    R.notes.tabResults=tabResults;
    ck('tabs: selecting a tab shows exactly its own panel',
       tabResults.length===3 && tabResults.every(function(r){
         return r.visible.length===1 && r.visible[0]===r.tab; }),
       JSON.stringify(tabResults.map(function(r){ return r.tab+'->'+r.visible.join(','); })));
    ck('tabs: exactly one tab is marked active at a time',
       tabResults.every(function(r){ return r.actives===1; }));
    // Diagnostics only exists when there is something to report.
    setSettingsTab('sources');
    R.notes.diagTabHiddenEmpty=document.getElementById('sd-tab-diag').hidden;
    ck('tabs: the diagnostics tab is hidden while there are no diagnostics',
       document.getElementById('sd-tab-diag').hidden===true);
    setSettingsTab('diag');
    ck('tabs: asking for diagnostics when empty lands on sources, not a blank panel',
       SETTINGS_TAB==='sources', SETTINGS_TAB);

    // ================= 4. Wiring =================
    // The rebuild moved every control. A handler naming a function that no
    // longer exists throws at click time and looks perfect until then.
    const handlers=[];
    DR.querySelectorAll('[onclick],[onchange],[oninput]').forEach(function(el){
      ['onclick','onchange','oninput'].forEach(function(a){
        const v=el.getAttribute(a);
        if(!v) return;
        const m=v.match(/([A-Za-z_$][\w$]*)\s*\(/g)||[];
        m.forEach(function(call){
          const fn=call.slice(0,-1).trim();
          handlers.push({el:(el.id||el.className||el.tagName),attr:a,fn:fn});
        });
      });
    });
    const missing=handlers.filter(function(h){
      return typeof window[h.fn]!=='function';
    });
    R.notes.handlerCount=handlers.length;
    R.notes.missingHandlers=missing.slice(0,10);
    ck('wiring: there are handlers to check', handlers.length>=15, handlers.length+' bindings');
    ck('wiring: every control in the drawer names a function that exists',
       missing.length===0, missing.map(function(m){ return m.fn+' on '+m.el; }).join(', '));

    // Every id the rest of the file addresses by getElementById must resolve.
    const NEEDED=['annot-dialog','annot-dialog-body','annot-all','annot-apply','annot-file',
      'mount-body','current-import-sect','current-import-advanced','current-import-advanced-wrap',
      'import-sect','ingest-bar','cfg-datadate','cfg-datadate-main','cfg-reportdate',
      'sched-file','file-picker-wrap','paste-wrap','paste-box','ingest-status',
      'import-error-wrap','map-wrap','map-wrap-section','range-wrap-section','range-note',
      'cfg-range-from','cfg-range-to','btn-range-reset','import-summary-wrap',
      'cfg-weekday','cfg-crit','cfg-risk',
      'diag-sect','diag-badge-text','diag-body','toggle-diag-onscreen','sd-src-box'];
    const gone=NEEDED.filter(function(id){ return !document.getElementById(id); });
    R.notes.missingIds=gone;
    ck('wiring: every id the rest of the file addresses still exists',
       gone.length===0, gone.join(', '));
    // P53 (TD-202): cfg-before/cfg-after (the Fallback window setting) were
    // removed from NEEDED above and are asserted GONE here instead — the
    // fallback window is now a fixed internal assumption with no UI control,
    // so their absence is the correct contract, not a wiring gap.
    ck('wiring: cfg-before/cfg-after (Fallback window) are gone, not merely unwired',
       !document.getElementById('cfg-before')&&!document.getElementById('cfg-after'));

    // The paste box is a .sd-row now, so showing it must restore the row's
    // layout rather than flattening it. Toggled through the real handler.
    setSettingsTab('import');
    const pw=document.getElementById('paste-wrap');
    const wasHidden=pw.hidden;
    togglePaste(); await settle();
    const openDisp=getComputedStyle(pw).display;
    togglePaste(); await settle();
    R.notes.pasteOpenDisplay=openDisp;
    ck('wiring: the paste box starts hidden and opens as a row',
       wasHidden===true && openDisp==='flex' && pw.hidden===true, openDisp);

    // ================= 5. The import flow, end to end =================
    PENDING_IMPORT_FILE='reference.xlsx';
    showMapper(Parse.workbook(new Uint8Array([0])));
    const dd=document.getElementById('cfg-datadate'); if(dd) dd.value='2026-08-29';
    await settle();
    setSettingsTab('import');
    const s1=document.getElementById('ingest-bar');
    const s3=document.getElementById('range-wrap-section');
    // Asserted as the invariant rather than by naming a step: P30 added a
    // fourth step, which made "step 3 is the current one" false without
    // anything being wrong. What must hold is that exactly one visible step is
    // current, it is the last one, and every earlier visible step reads done.
    const visSteps=Array.from(DR.querySelectorAll('.sd-step')).filter(function(el){
      return getComputedStyle(el).display!=='none';
    });
    const currents=visSteps.filter(function(el){ return el.classList.contains('is-current'); });
    const earlierAllDone=visSteps.slice(0,-1).every(function(el){ return el.classList.contains('is-done'); });
    R.notes.stepStateAtSetup=visSteps.map(function(el){ return (el.id||'?')+':'+el.className; });
    ck('steps: the range step appears once a file is parsed',
       getComputedStyle(s3).display!=='none');
    ck('steps: there are several visible steps to reason about', visSteps.length>=3, visSteps.length);
    ck('steps: exactly one visible step is the current one',
       currents.length===1, currents.length+' current');
    ck('steps: the current step is the last visible one',
       currents.length===1 && currents[0]===visSteps[visSteps.length-1],
       currents.length?(currents[0].id||'?')+' vs '+(visSteps[visSteps.length-1].id||'?'):'none');
    ck('steps: every step before it reads as done',
       earlierAllDone && s1.classList.contains('is-done'),
       R.notes.stepStateAtSetup.join(' | '));

    DIAG=[]; runIngest();
    await settle(); freeze();
    R.notes.diagCount=DIAG.length;
    ck('import: the import produced diagnostics to surface', DIAG.length>0, DIAG.length);
    ck('tabs: the diagnostics tab appears once there is something to report',
       document.getElementById('sd-tab-diag').hidden===false);
    ck('tabs: the diagnostics tab carries the count',
       document.getElementById('sd-diag-count').textContent===String(DIAG.length),
       document.getElementById('sd-diag-count').textContent+' vs '+DIAG.length);
    setSettingsTab('diag'); await settle();
    ck('tabs: diagnostics is reachable once it exists', SETTINGS_TAB==='diag', SETTINGS_TAB);
    ck('import: the diagnostics table rendered',
       document.querySelectorAll('#diag-body .diag-tbl tr').length>1,
       document.querySelectorAll('#diag-body .diag-tbl tr').length+' rows');

    // D-17a rewrote the Sources tab: the Schedules and User-defined groups
    // are .sd-group/.sd-row (name, data date, counts, on/off switch, Rename,
    // Remove), not .sd-card any more — that shape has controls a read-only
    // card never carried (a switch, an inline confirm, a duplicate warning).
    // The Annotations slot (unchanged by D-17a, D-17b territory) still uses
    // mountSlotHtml()'s .sd-card, so both shapes should be present together.
    setSettingsTab('sources'); await settle();
    const mountGroups=document.querySelectorAll('#mount-body .sd-group');
    const mountRows=document.querySelectorAll('#mount-body .sd-group .sd-row');
    const cards=document.querySelectorAll('#mount-body .sd-card');
    R.notes.mountGroups=mountGroups.length; R.notes.mountRows=mountRows.length; R.notes.mountCards=cards.length;
    ck('sources: the Sources tab renders its two groups (Schedules, User-defined)', mountGroups.length>=2, mountGroups.length+' groups');
    ck('sources: each group renders rows (schedule/baseline/user-defined entries)', mountRows.length>=2, mountRows.length+' rows');
    ck('sources: the Annotations slot still renders as a card (D-17b territory, untouched)', cards.length>=1, cards.length+' cards');
    ck('sources: no mount slot still uses the retired classes',
       document.querySelectorAll('#mount-body .mnt-slot,#mount-body .mnt-title,#mount-body .mnt-lines').length===0);
    const cardRadii=uniq(Array.from(cards).map(function(c){ return getComputedStyle(c).borderTopLeftRadius; }));
    ck('sources: every annotation card shares one radius', cardRadii.length===1, cardRadii.join('/'));
    ck('sources: every schedule row has an on/off switch',
       document.querySelectorAll('#mount-body .src-row .toggle-switch').length>=1,
       document.querySelectorAll('#mount-body .src-row .toggle-switch').length+' switches');

    // ================= 6. Nothing else moved =================
    R.notes.boardAfter=snapBoard();

    // The tab choice is display state and must survive a rebuild, which is
    // where the old panel lost things.
    setSettingsTab('defaults');
    scheduleRerender(true);
    await settle(); await settle();
    ck('state: the chosen tab survives a full rebuild', SETTINGS_TAB==='defaults', SETTINGS_TAB);
    const visAfter=Array.from(DR.querySelectorAll('.sd-tabpanel')).filter(function(p){ return !p.hidden; })
                        .map(function(p){ return p.getAttribute('data-tab'); });
    ck('state: the rebuild did not reveal a second panel',
       visAfter.length===1 && visAfter[0]==='defaults', visAfter.join(','));

    R.ok=true;
  }catch(e){ R.ok=false; R.err=e.message; R.stack=(e.stack||'').split('\n').slice(0,4).join(' | '); }
  emit();
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default="data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--html", default="src/milestone-dashboard.html")
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    html = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html.replace("</body>", inject + "</body>")
    if page == html:
        sys.exit("Could not find </body> to inject into.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p29.html"
        tmp.write_text(page, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--window-size=1600,1200", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=480,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit("Probe output not found.\n" + proc.stderr[-3000:])
    R = json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))

    if not R.get("ok"):
        print("PROBE FAILED: " + str(R.get("err")))
        print(R.get("stack", ""))
        return 1

    n = R.get("notes", {})
    for k in ("drawerEls", "groups", "gutters", "rows", "midRows", "rowSteps",
              "seps", "sepStyles", "surfaces", "helps", "drawerWidth",
              "handlerCount", "mountCards", "diagCount", "footerBottom",
              "pasteOpenDisplay"):
        if k in n:
            print(f"   {k}: {json.dumps(n[k]) if isinstance(n[k], (list, dict)) else n[k]}")
    if n.get("inlineSpacing"):
        print("   inline spacing still present: " + json.dumps(n["inlineSpacing"]))
    if n.get("missingHandlers"):
        print("   missing handlers: " + json.dumps(n["missingHandlers"]))
    print()

    fails = [c for c in R["checks"] if not c["pass"]]
    for c in R["checks"]:
        mark = "ok  " if c["pass"] else "FAIL"
        print(f"  {mark} {c['name']}" + (f"   [{c['detail']}]" if c["detail"] else ""))

    # The board is rebuilt by the same pipeline from the same data, so every
    # one of these must be what P28 produced. Compared here rather than in the
    # page so the expected figures live outside the thing being tested.
    before = n.get("boardBefore") or {}
    after = n.get("boardAfter") or {}
    extra = 0
    print("\nBoard, unchanged by this partial:")
    if not before or not after:
        print("  FAIL no board figures were captured, so this would pass vacuously")
        fails.append({"name": "board capture"})
        extra = 1
    else:
        for label, got_map, want_map in (("baseline", before, EXPECT_BASELINE),
                                         ("imported", after, EXPECT_IMPORTED)):
            for k, want in want_map.items():
                got = got_map.get(k)
                ok = got == want
                mark = "ok  " if ok else "FAIL"
                print(f"  {mark} board ({label}): {k}   [{got} vs {want}]")
                if not ok:
                    fails.append({"name": f"board {label} {k}"})
                extra += 1

    total = len(R["checks"]) + extra
    print(f"\n{total - len(fails)}/{total} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
