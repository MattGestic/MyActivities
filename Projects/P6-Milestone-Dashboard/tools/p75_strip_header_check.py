#!/usr/bin/env python3
"""
p75_strip_header_check: the collection strip, the header buttons and the
one-row desktop filter bar (P75, Matt 2026-10-02, desktop screenshots).

Drives the REAL app in headless Chromium (the fixture is seeded by
find_chrome()) and reads classList, attributes, computed style and
getBoundingClientRect of the elements themselves, never a screenshot.
Double clicks are real: two clicks on one marker inside the 350ms window.

1. Collection strip (#collect-bar):
  - a double click that adds an ID shows the toast "<ID> added" and pulses
    the new chip (.is-landed); a repeat shows "Already in the list"; each
    toast disappears by itself (about 1.6s); the toast is a polite live
    region, a body child outside the card, and a click on it leaves an open
    card open;
  - left to right: Add to list, Copy, a divider, the chips, clear-all; all
    on one line, clear-all at the far right;
  - clear-all carries an aria-label, empties the collection and hides the
    strip; its toast offers Undo, which puts the same IDs back in order;
    left alone, the Undo toast goes after about 4s and the list stays empty;
  - Add to list looks enabled (no aria-disabled, full opacity) and, with
    no Lists section in the app, says so in a toast and changes nothing.

2. Header: the filter toggle and + Milestone sit on the left of the details
   row, straight after the View / Baseline shadow group (measured with that
   group shown, and first on the row with it hidden); the icon group stays
   top right; the header row does not overflow.

3. Filter bar: at 1920 (and at 1680, 1px inside the threshold) the three
   boxes share one row (tops within 4px) with nothing wrapping inside them
   and no box overflowing; at 1679 (1px outside), 1440 and 1024 the old
   layout (status box on its own row below); a docked Data & view panel at
   1920 narrows the bar below the threshold and the old layout returns; at
   390 the phone shape (fb-phone, never fb-wide).

Every run: no horizontal page scroll.

Usage:
  python3 tools/p75_strip_header_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p75-out">(.*?)</pre>', re.S)

# (width, height, full): full runs every part; the two boundary runs only
# the filter layout.
VIEWPORTS = [(390, 844, True), (1024, 768, True), (1440, 900, True), (1920, 1080, True),
             (1679, 900, False), (1680, 900, False)]

FB_WIDE_MIN = 1636

PROBE = r"""
(async function(){
  const FULL=__FULL__, WIDE_MIN=__WIDE__;
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p75-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const settle=()=>wait(240);
  const gap=()=>wait(420);
  const $=id=>document.getElementById(id);
  const rc=e=>e.getBoundingClientRect();
  const shown=e=>{ if(!e) return false; const q=rc(e); return q.width>0&&q.height>0&&getComputedStyle(e).visibility!=='hidden'; };
  const W=window.innerWidth;
  const dlg=()=>$('ms-dialog');
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const dbl=async function(id){ await gap(); const w=wrapOf(id); w.click(); w.click(); await settle(); };
  const chips=()=>Array.prototype.map.call($('collect-chips').querySelectorAll('.ms-dep-chip'),b=>b.getAttribute('data-id'));
  const toast=$('app-toast'), tmsg=$('app-toast-msg'), tact=$('app-toast-act');
  const toastOn=()=>toast.classList.contains('is-shown')&&parseFloat(getComputedStyle(toast).opacity)>0.5;
  const toastOff=()=>!toast.classList.contains('is-shown')&&parseFloat(getComputedStyle(toast).opacity)<0.05;
  try{
    // Transitions off so computed opacity is the end state; timers are real.
    const st=document.createElement('style');
    st.textContent='*{transition:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();
    R.notes.w=W;

    if(FULL){
      // ===== 1. Collection strip =====
      setMsCollection([]);
      const all=MILESTONES.map(msId).filter(id=>id&&!!wrapOf(id));
      const A=all[0], B=all[1], C=all[2];
      ck('sample: three markers on the board', !!(A&&B&&C), [A,B,C].join(' '));
      R.notes.sample=[A,B,C].join(' ');

      ck('toast: a polite live region', toast&&toast.getAttribute('aria-live')==='polite'&&toast.getAttribute('role')==='status', '');
      ck('toast: outside the card and the board (a page-level element)', !dlg().contains(toast)&&!toast.closest('#scroll-wrap,#collect-bar')&&getComputedStyle(toast).position==='fixed',
         toast.parentElement&&toast.parentElement.id);
      ck('toast: hidden at rest', toastOff(), toast.className);

      await dbl(A);
      ck('add: the ID is collected', MS_COLLECTION===A, MS_COLLECTION);
      ck('add: the toast shows "'+A+' added"', toastOn()&&tmsg.textContent===A+' added', tmsg.textContent+' / '+toast.className);
      ck('add: no action button on a plain confirmation', tact.hidden, '');
      const chipA=$('collect-chips').querySelector('.ms-dep-chip[data-id="'+CSS.escape(A)+'"]');
      ck('add: the new chip pulses (.is-landed)', chipA&&chipA.classList.contains('is-landed'), chipA&&chipA.className);
      ck('add: the toast is on screen', (()=>{ const q=rc(toast); return q.left>=-0.5&&q.right<=W+0.5&&q.bottom<=window.innerHeight+0.5&&q.top>=0; })(),
         JSON.stringify(rc(toast)));
      // A click on the toast is not a click away from the open card.
      const cardOpen=!dlg().hidden;
      toast.click(); await wait(60);
      ck('toast: a click on it leaves the open card open', cardOpen&&!dlg().hidden, 'card open before '+cardOpen);
      await wait(1700);
      ck('add: the toast disappears by itself (about 1.6s)', toastOff(), toast.className);
      ck('add: the pulse ends', chipA&&!chipA.classList.contains('is-landed'), chipA&&chipA.className);

      await dbl(A);
      ck('repeat: nothing added', MS_COLLECTION===A&&chips().length===1, MS_COLLECTION);
      ck('repeat: the toast says "Already in the list"', toastOn()&&tmsg.textContent==='Already in the list', tmsg.textContent);
      await wait(1700);
      ck('repeat: the toast disappears by itself', toastOff(), toast.className);

      await dbl(B); await dbl(C);
      ck('add: N=3, three chips in order', chips().join(',')===[A,B,C].join(','), chips().join(','));
      ck('add: the third toast names the third ID', tmsg.textContent===C+' added', tmsg.textContent);
      await wait(1700);

      // Order, left to right.
      const bar=$('collect-bar'), add=$('collect-add'), cp=$('collect-copy'), dv=$('collect-div'), host=$('collect-chips'), clr=$('collect-clear');
      const q={add:rc(add),cp:rc(cp),dv:rc(dv),host:rc(host),clr:rc(clr),bar:rc(bar)};
      R.notes.strip=Object.keys(q).map(k=>k+' '+Math.round(q[k].left)+'-'+Math.round(q[k].right)).join(', ');
      ck('order: Add to list first', q.add.left>=q.bar.left-0.5&&q.add.right<=q.cp.left+0.5&&/Add to list/.test(add.textContent), R.notes.strip);
      ck('order: Copy (the clipboard) second', q.cp.right<=q.dv.left+0.5&&!!cp.querySelector('svg'), R.notes.strip);
      ck('order: the divider third, a visible vertical rule', shown(dv)&&q.dv.width>=0.5&&q.dv.width<=2&&q.dv.height>=12&&q.dv.right<=q.host.left+0.5,
         Math.round(q.dv.width*10)/10+'x'+Math.round(q.dv.height));
      ck('order: the chip list fourth', q.host.right<=q.clr.left+0.5, R.notes.strip);
      const pr=parseFloat(getComputedStyle(bar).paddingRight)||0;
      ck('order: clear-all at the far right', q.clr.right>=q.bar.right-pr-1.5&&q.clr.right<=q.bar.right+0.5,
         Math.round(q.clr.right)+' vs '+Math.round(q.bar.right)+' pad '+pr);
      const mids=[q.add,q.cp,q.host,q.clr].map(r=>(r.top+r.bottom)/2);
      ck('order: one line (centres within 4px)', Math.max.apply(null,mids)-Math.min.apply(null,mids)<=4, mids.map(Math.round).join(','));
      // Many chips: still one line, scrolling sideways.
      const many=all.slice(3,40);
      const h1=Math.round(q.bar.height);
      setMsCollection([A,B,C].concat(many));
      const tops=new Set(Array.prototype.map.call(host.querySelectorAll('.ms-dep-chip'),b=>Math.round(rc(b).top)));
      ck('strip: '+(3+many.length)+' chips stay on one line and scroll sideways', tops.size===1&&Math.round(rc(bar).height)===h1&&host.scrollWidth>host.clientWidth,
         'tops '+tops.size+' h '+h1+'->'+Math.round(rc(bar).height)+' sw '+host.scrollWidth+'/'+host.clientWidth);
      ck('strip: clear-all stays at the far right with many chips', rc(clr).right>=rc(bar).right-pr-1.5, Math.round(rc(clr).right)+' vs '+Math.round(rc(bar).right));
      setMsCollection([A,B,C]);

      // Clear-all and Undo.
      ck('clear: has an aria-label', /clear/i.test(clr.getAttribute('aria-label')||''), clr.getAttribute('aria-label'));
      clr.click(); await wait(60);
      ck('clear: empties the collection', MS_COLLECTION===''&&chips().length===0, MS_COLLECTION);
      ck('clear: the strip hides', bar.hidden, '');
      ck('clear: the toast offers Undo', toastOn()&&!tact.hidden&&tact.textContent==='Undo', tmsg.textContent+' / '+tact.textContent);
      await wait(2000);
      ck('clear: Undo is still offered after 2s', toastOn()&&!tact.hidden, toast.className);
      tact.click(); await wait(60);
      ck('undo: restores the same IDs in order', MS_COLLECTION===[A,B,C].join(',')&&chips().join(',')===[A,B,C].join(','), MS_COLLECTION);
      ck('undo: the strip shows again', !bar.hidden, '');
      let stU=null; try{ stU=localStorage.getItem('sret-ms-collection'); }catch(x){}
      ck('undo: stored again as display state', stU===MS_COLLECTION, stU);
      await wait(1700);
      clr.click(); await wait(60);
      await wait(4300);
      ck('clear: left alone, the Undo toast goes after about 4s', toastOff()&&tact.hidden, toast.className);
      ck('clear: and the list stays empty', MS_COLLECTION==='', MS_COLLECTION);

      // Add to list.
      setMsCollection([A,B]);
      ck('add to list: looks enabled', !add.hasAttribute('aria-disabled')&&!add.disabled&&parseFloat(getComputedStyle(add).opacity)===1&&getComputedStyle(add).cursor==='pointer',
         add.getAttribute('aria-disabled')+' '+getComputedStyle(add).opacity+' '+getComputedStyle(add).cursor);
      const listsLoaded=typeof SRETCollections!=='undefined';
      R.notes.lists=listsLoaded?'present':'absent';
      add.click(); await wait(60);
      ck('add to list: Lists is not in the app, and the toast says lists come with the Lists section',
         !listsLoaded&&toastOn()&&/Lists section/.test(tmsg.textContent), (listsLoaded?'Lists present: ':'')+tmsg.textContent);
      ck('add to list: the collection is unchanged', MS_COLLECTION===A+','+B, MS_COLLECTION);
      ck('toast: no em dash in any message', !/—/.test(tmsg.textContent), tmsg.textContent);
      await wait(1700);
      setMsCollection([]);
      if(!dlg().hidden){ discardMsDialog(); await settle(); }

      // ===== 2. Header =====
      const vgrp=document.querySelector('.rpt-sub-view'), row=document.querySelector('.rpt-sub-below');
      const tg=$('btn-filter-expand'), am=$('btn-add-ms'), icons=document.querySelector('#icon-bar .ib-right-icons');
      const vwas=vgrp.style.display;
      vgrp.style.display=''; await wait(60);
      const v=rc(vgrp), t=rc(tg), m=rc(am), rw=rc(row);
      R.notes.header='view '+Math.round(v.left)+'-'+Math.round(v.right)+' toggle '+Math.round(t.left)+'-'+Math.round(t.right)+' +ms '+Math.round(m.left)+'-'+Math.round(m.right)+' row '+Math.round(rw.left)+'-'+Math.round(rw.right);
      const sameLine=Math.abs((v.top+v.bottom)/2-(t.top+t.bottom)/2)<=4;
      if(sameLine){
        ck('header: the filter toggle sits straight after the View group', t.left>=v.right-0.5&&t.left-v.right<=24, R.notes.header);
      } else {
        // The row wrapped (phone): the pair starts the next line, at its left edge.
        ck('header: the filter toggle sits straight after the View group (wrapped: left of the next line)', t.top>=v.bottom-0.5&&t.left-rw.left<=2, R.notes.header);
      }
      ck('header: + Milestone straight after the toggle', m.left>=t.right-0.5&&m.left-t.right<=12&&Math.abs(m.top-t.top)<=2, R.notes.header);
      ck('header: the pair is anchored left, not pushed right', rw.right-m.right>8&&(sameLine?t.left<rw.left+rw.width/2:true), R.notes.header);
      vgrp.style.display='none'; await wait(60);
      ck('header: with the View group hidden, the toggle is first on the row', rc(tg).left-rc(row).left<=2, Math.round(rc(tg).left)+' vs '+Math.round(rc(row).left));
      vgrp.style.display=vwas; await wait(60);
      const ic=rc(icons);
      ck('header: the icon group stays top right', shown(icons)&&ic.right>=W-24&&ic.bottom<=rc(tg).top+0.5, Math.round(ic.left)+'-'+Math.round(ic.right)+' top '+Math.round(ic.top));
      ck('header: the row does not overflow', row.scrollWidth<=row.clientWidth+1&&rc(am).right<=W+0.5, row.scrollWidth+'/'+row.clientWidth+' +ms right '+Math.round(rc(am).right));
    }

    // ===== 3. Filter bar =====
    const fb=$('top-filter-bar'), find=$('tfb-find'), when=$('tfb-when'), crit=$('tfb-crit');
    const boxes=[find,when,crit];
    const wrappedIn=function(box){
      const bad=[];
      box.querySelectorAll('.fb-line, .ds-seg, .fb-inline').forEach(function(l){
        if(!shown(l)) return;
        const kids=Array.prototype.filter.call(l.children,k=>shown(k)&&getComputedStyle(k).position!=='absolute'&&getComputedStyle(k).position!=='fixed');
        const mids=kids.map(k=>{ const q=rc(k); return (q.top+q.bottom)/2; });
        if(mids.length>1&&Math.max.apply(null,mids)-Math.min.apply(null,mids)>4) bad.push(l.id||l.className);
      });
      return bad;
    };
    const railW=document.body.classList.contains('rail-collapsed')?0:(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ws-rail-w'))||44);
    const wideExpected=W>=768&&(W-railW)>=WIDE_MIN;
    R.notes.rail=railW;
    R.notes.filter=fb.className;
    if(W>=768){
      const T=boxes.map(b=>rc(b));
      R.notes.boxes=T.map(r=>Math.round(r.left)+','+Math.round(r.top)+' '+Math.round(r.width)+'x'+Math.round(r.height)).join(' | ');
      if(wideExpected){
        ck('filter: one-row layout on (fb-wide)', fb.classList.contains('fb-wide'), fb.className);
        ck('filter: Find, Date range and Status share one row (tops within 4px)', Math.abs(T[0].top-T[1].top)<=4&&Math.abs(T[0].top-T[2].top)<=4, R.notes.boxes);
        ck('filter: left to right Find, Date range, Status', T[0].right<=T[1].left+0.5&&T[1].right<=T[2].left+0.5, R.notes.boxes);
        ck('filter: each keeps its own box (border)', boxes.every(b=>parseFloat(getComputedStyle(b).borderTopWidth)>0), '');
        const wr=boxes.map(wrappedIn);
        ck('filter: nothing wraps inside the three boxes', wr.every(x=>!x.length), JSON.stringify(wr));
        ck('filter: no box overflows', boxes.every(b=>b.scrollWidth<=b.clientWidth+1), boxes.map(b=>b.scrollWidth+'/'+b.clientWidth).join(' '));
        const panels=['fb-dd-status','fb-dd-float','fb-dd-annot'].map(i=>document.querySelector('#'+i+' .fb-dd-panel'));
        ck('filter: each status group keeps its chips on one line', panels.every(p=>{ const ts=new Set(Array.prototype.map.call(Array.prototype.filter.call(p.querySelectorAll('button'),shown),b=>Math.round(rc(b).top))); return shown(p)&&ts.size===1; }), '');
        ck('filter: the three boxes sit inside the bar', T.every(r=>r.left>=rc(fb).left-0.5&&r.right<=rc(fb).right+0.5), R.notes.boxes);
        ck('filter: the Weeks field keeps its 220px minimum', rc($('wr-field')).width>=219.5, rc($('wr-field')).width);
        if(FULL&&W>=1900){
          toggleSettingsDrawer(true); await wait(400);
          const narrowed=!fb.classList.contains('fb-wide')&&rc(crit).top>=rc(find).bottom-0.5;
          ck('filter: a docked Data & view panel narrows the bar and the two-row layout returns', narrowed, fb.className);
          toggleSettingsDrawer(false); await wait(400);
          ck('filter: closing it brings the one row back', fb.classList.contains('fb-wide'), fb.className);
        }
      } else {
        ck('filter: below the threshold, no one-row layout', !fb.classList.contains('fb-wide'), fb.className);
        ck('filter: below the threshold, the old layout: Status on its own row below Find', T[2].top>=T[0].bottom-0.5, R.notes.boxes);
        ck('filter: below the threshold, Find and Date range as before', W>=1280?Math.abs(T[0].top-T[1].top)<=4:T[1].top>=T[0].bottom-0.5, R.notes.boxes);
      }
    } else {
      ck('filter: phone shape (fb-phone), never fb-wide', fb.classList.contains('fb-phone')&&!fb.classList.contains('fb-wide'), fb.className);
    }
    ck('page: no horizontal scroll', document.documentElement.scrollWidth<=W, document.documentElement.scrollWidth+' > '+W);
    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.message||err)});
    R.err=String(err&&err.stack||err);
    emit();
  }
})();
"""


def render(html_path, width, height, full):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    probe = PROBE.replace("__FULL__", "true" if full else "false").replace("__WIDE__", str(FB_WIDE_MIN))
    out = page.replace("</body>", "<script>\n" + probe + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p75.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=90000",
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
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal",
                   len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))
    checks.append(("source: the threshold here matches the app's FB_WIDE_MIN",
                   f"var FB_WIDE_MIN={FB_WIDE_MIN};" in src, ""))
    bar = src[src.index('<div class="collect-bar"'):src.index('</div></th>', src.index('<div class="collect-bar"'))]
    checks.append(("source: no em dash in the strip markup", "—" not in bar and "&mdash;" not in bar, ""))
    fns = src[src.index("function collectMsFromBoard("):src.index("function hideToast(")]
    checks.append(("source: no em dash in the toast strings", "—" not in fns and "&mdash;" not in fns, ""))

    for (w, h, full) in VIEWPORTS:
        R = render(html, w, h, full)
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===  {n.get('sample', '')}  lists {n.get('lists', '-')}  filter [{n.get('filter')}]  boxes {n.get('boxes', '-')}")
        if n.get("strip"):
            print("  strip  " + n["strip"])
        if n.get("header"):
            print("  header " + n["header"])
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
