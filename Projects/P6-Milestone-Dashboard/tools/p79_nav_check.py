#!/usr/bin/env python3
"""P79 check (D-31 Stage A, TD-248): the kit's left nav in the app, and the base-screen tidy.

Matt, 2026-10-03: one left navigation panel, built as a reusable module (ui-nav)
on the shared kit (ui-tokens, ui-shell page variant), with the base screen's
containers tidied. Only functions the app already has appear in the nav.

Runs the app (with the reference fixture, as every check does) at 390, 768,
1024 and 1440 wide and asserts, by class and computed style, not screenshots:

  A  band state from SRETShell: drawer below 641, rail to 1024, expanded above;
     --ui-nav-col and the body offset equal the nav column; the nav is fixed;
     no horizontal page scroll; the version literal appears once;
  B  each nav item calls its entry point: Notes, Comments and markups, User
     milestones open that Workspace section (and the current item follows);
     Grid opens the grid and Timeline leaves it; Print preview enters and
     Timeline leaves it; Display options, Import and data, Settings, Help and
     about open Data & view on their tab;
  C  desktop: Collapse to the 60px rail is remembered across a reload; the old
     sret-rail value 'collapsed' migrates to 'rail'; the docked Workspace panel
     still pushes the board by nav + panel width;
  D  phone and tablet: the header menu button opens the nav (drawer or
     slide-over), choosing an item closes it, Esc and the scrim close it and
     focus returns to the button; the rest of the page is inert while it is open;
  E  the notes and user-milestone badges match the stores;
  F  the board fills the viewport: #scroll-wrap ends one gutter above the
     viewport bottom, within 2px, with the page scrolled to the top;
  G  More actions is a labelled dropdown at every width.

    python3 tools/p79_nav_check.py [--html FILE]
Exit 1 if any check fails.
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
OUT_RE = re.compile(r'<pre id="p79-out">(.*?)</pre>', re.S)

PROBE = r"""
(function(){
  const ARGS=__ARGS__;
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:'['+ARGS.tag+'] '+n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p79-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,320));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const cs=el=>getComputedStyle(el);
  const W=window.innerWidth;
  const navCol=()=>parseFloat(cs(document.documentElement).getPropertyValue('--ui-nav-col'));
  const item=id=>document.querySelector('#ws-rail .ui-nav__item[data-id="'+id+'"]');
  const current=()=>{ const b=document.querySelector('#ws-rail .ui-nav__item[aria-current="page"]'); return b?b.dataset.id:null; };
  const pick=async id=>{ const s=APP_SHELL.state(); if(s.band!=='desktop'&&!s.navOpen){ $('ws-toggle').click(); await settle(); } item(id).click(); await settle(); };
  window.addEventListener('load',function(){ setTimeout(async function(){
   try{
    // Geometry straight after state changes: no transitions (as p59 does).
    document.head.insertAdjacentHTML('beforeend','<style>*,*::before,*::after{transition:none!important}</style>');
    const st=APP_SHELL.state();
    // ---------- A ----------
    // A returning user whose P59 rail was collapsed starts on the 60px rail.
    const want=W<=640?'drawer':(W<=1024||ARGS.legacy?'rail':'expanded');
    ck('A band state is '+want, document.body.dataset.nav===want, document.body.dataset.nav);
    const col=W<=640?0:(want==='rail'?60:240);
    ck('A --ui-nav-col is '+col+'px', navCol()===col, navCol());
    ck('A body offset equals the nav column', Math.round(parseFloat(cs(document.body).marginLeft))===col, cs(document.body).marginLeft);
    ck('A the nav is fixed', cs($('ws-rail')).position==='fixed');
    if(want!=='drawer') ck('A the nav is as wide as its column', Math.round(rc($('ws-rail')).width)===col, rc($('ws-rail')).width);
    ck('A no horizontal page scroll', document.documentElement.scrollWidth<=W, document.documentElement.scrollWidth);
    ck('A the menu button shows only where the nav is a drawer', (cs($('ws-toggle')).display!=='none')===(want==='drawer'), cs($('ws-toggle')).display);
    ck('A the menu button sits inside the header', $('icon-bar').contains($('ws-toggle')));

    // ---------- G ----------
    const trig=$('btn-more-actions');
    ck('G More actions trigger is shown', cs(trig).display!=='none');
    ck('G the menu is closed until asked', !$('more-actions-panel').classList.contains('open'));
    trig.click(); await settle();
    const lbl=document.querySelector('#more-actions-panel .ib-mi-lbl');
    ck('G opened, the menu rows carry visible labels', $('more-actions-panel').classList.contains('open')&&rc(lbl).width>20, rc(lbl).width);
    trig.click(); await settle();

    // ---------- F ----------
    window.scrollTo(0,0); sizeBoardHeight(); await settle();
    const gap=parseFloat(cs(document.documentElement).getPropertyValue('--group-gap'))||16;
    const sw=$('scroll-wrap');
    if(sw.scrollHeight>sw.clientHeight+4){
      ck('F the board ends one gutter above the viewport bottom', Math.abs((innerHeight-gap)-rc(sw).bottom)<=2, (innerHeight-rc(sw).bottom).toFixed(1));
    }
    ck('F the board height is measured, not the old 150px guess', /px$/.test(sw.style.getPropertyValue('--board-max-h')), sw.style.getPropertyValue('--board-max-h'));

    // ---------- E ----------
    const nb=item('notes').querySelector('.ui-nav__badge'), ub=item('userms').querySelector('.ui-nav__badge');
    const openNotes=collectionInfo(reportPeriodISO()).open;
    ck('E notes badge matches the open notes', openNotes?(nb&&nb.textContent===String(openNotes)):!nb, (nb&&nb.textContent)+' vs '+openNotes);
    ck('E user milestone badge matches the store', USER_MILESTONES.length?(ub&&ub.textContent===String(USER_MILESTONES.length)):!ub, (ub&&ub.textContent)+' vs '+USER_MILESTONES.length);

    // ---------- B ----------
    for(const sec of ['notes','comments','userms']){
      await pick(sec);
      ck('B '+sec+' opens its Workspace section', $('ws-panel').classList.contains('open')&&WS_SECTION===sec&&!document.querySelector('#ws-panel .ws-sec[data-sec="'+sec+'"]').hidden);
      ck('B '+sec+' is the current nav item', current()===sec, current());
    }
    if(W>1024){
      const ml=parseFloat(cs(document.body).marginLeft);
      ck('C the docked Workspace panel pushes the board by nav + panel', Math.round(ml)===col+320, ml);
    }
    await pick('userms');
    ck('B choosing the open section again closes it', !$('ws-panel').classList.contains('open'));
    ck('B the current item falls back to Timeline', current()==='timeline', current());

    await pick('grid');
    ck('B Grid opens the grid view', document.body.classList.contains('grid-open')&&!$('grid-host').hidden);
    ck('B Grid is the current item', current()==='grid', current());
    await pick('timeline');
    ck('B Timeline leaves the grid', !document.body.classList.contains('grid-open'));
    await pick('print');
    ck('B Print preview enters print mode', document.body.classList.contains('print-mode'));
    ck('B the nav is hidden in print preview', cs($('ws-rail')).display==='none');
    togglePrintMode(false); await settle();
    ck('B leaving print preview restores the nav', cs($('ws-rail')).display!=='none');
    for(const [id,tab] of [['view','view'],['import','import'],['defaults','defaults'],['help','help']]){
      await pick(id);
      ck('B '+id+' opens Data & view on '+tab, $('settings-drawer').classList.contains('open')&&SETTINGS_TAB===tab, SETTINGS_TAB);
      toggleSettingsDrawer(false); await settle();
    }

    // ---------- C ----------
    if(W>1024){
      if(ARGS.legacy){
        ck('C the P59 key migrates: collapsed becomes the rail', document.body.dataset.nav==='rail', document.body.dataset.nav);
        let k=null, old=null; try{ k=localStorage.getItem('sret-nav'); old=localStorage.getItem('sret-rail'); }catch(e){}
        ck('C the new key is written and the old one removed', k==='rail'&&old===null, k+'/'+old);
      } else {
        document.querySelector('#ws-rail .ui-nav__collapse').click(); await settle();
        ck('C Collapse gives the 60px rail', document.body.dataset.nav==='rail'&&navCol()===60&&Math.round(parseFloat(cs(document.body).marginLeft))===60);
        let k=null; try{ k=localStorage.getItem('sret-nav'); }catch(e){}
        ck('C the rail is remembered', k==='rail', k);
        setRailState('expanded'); await settle();
        ck('C setRailState(expanded) restores it', document.body.dataset.nav==='expanded');
        setRailState('collapsed'); await settle();
        ck('C the P59 value collapsed still works (as the rail)', document.body.dataset.nav==='rail');
        setRailState('expanded'); await settle();
      }
    }

    // ---------- D ----------
    if(W<=1024){
      const tg=$('ws-toggle');
      if(want==='drawer'){ tg.focus(); tg.click(); }
      else { document.querySelector('#ws-rail .ui-nav__collapse').click(); }
      await settle();
      ck('D the nav opens', APP_SHELL.state().navOpen&&cs($('ws-rail')).visibility!=='hidden');
      ck('D the scrim is up', document.body.dataset.scrim==='true');
      ck('D the page behind is inert', $('icon-bar').hasAttribute('inert')&&!$('ws-rail').hasAttribute('inert'));
      if(want==='drawer') ck('D the menu button reports expanded', tg.getAttribute('aria-expanded')==='true');
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      await settle();
      ck('D Esc closes it', !APP_SHELL.state().navOpen&&!$('icon-bar').hasAttribute('inert'));
      if(want==='drawer') ck('D focus returns to the menu button', document.activeElement===tg, document.activeElement&&document.activeElement.id);
      if(want==='drawer'){ tg.click(); } else { document.querySelector('#ws-rail .ui-nav__collapse').click(); }
      await settle();
      document.querySelector('.ui-shell__scrim').click(); await settle();
      ck('D a scrim click closes it', !APP_SHELL.state().navOpen);
    }
   }catch(e){ ck('probe ran without an exception', false, e&&e.stack||e); }
   emit();
  },900); });
})();
"""

RUNS = [
    {"tag": "1440", "w": 1440, "h": 900},
    {"tag": "1440-legacy", "w": 1440, "h": 900, "legacy": "collapsed"},
    {"tag": "1024", "w": 1024, "h": 768},
    {"tag": "768", "w": 768, "h": 1024},
    {"tag": "390", "w": 390, "h": 844},
]


def render(html: str, w: int, h: int) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    out = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                          f"--window-size={w},{h}", "--virtual-time-budget=60000",
                          "--dump-dom", "file://" + path],
                         capture_output=True, text=True, timeout=300).stdout
    m = OUT_RE.search(out)
    if not m:
        return {"checks": [{"name": f"[{w}] probe produced output", "pass": False, "detail": ""}]}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    fails = total = 0
    n = len(re.findall(r"3\.[0-9]*\.[0-9]*-P", src))
    total += 1
    fails += 0 if n == 1 else 1
    print(("PASS " if n == 1 else "FAIL ") + f"A the version literal appears once in the source ({n})")
    for run in RUNS:
        args = {"tag": run["tag"], "legacy": run.get("legacy")}
        html = src.replace("</body>", f"<script>\n{PROBE.replace('__ARGS__', json.dumps(args))}\n</script>\n</body>")
        if run.get("legacy"):
            # Before the app boots, so the nav reads the old P59 key as a returning user's browser would.
            early = f"<script>try{{localStorage.setItem('sret-rail',{json.dumps(run['legacy'])});}}catch(e){{}}</script>"
            html = html.replace("<head>", "<head>" + early, 1)
        r = render(html, run["w"], run["h"])
        for c in r["checks"]:
            total += 1
            ok = c["pass"]
            fails += 0 if ok else 1
            print(("PASS " if ok else "FAIL ") + c["name"] + ("" if ok else f"  ({c['detail']})"))
    print(f"\n{total - fails}/{total} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
