#!/usr/bin/env python3
"""Grid view: phone, tablet and desktop (Matt, 2026-09-30).

Loads prototypes/grid-view/demo.html at 390, 768 and 1440 px wide, each with
a fine pointer and a forced coarse (touch) pointer, and asserts:

  - the page never scrolls sideways; every header control is on screen
    (User tasks and Schedule changes, which has the most controls);
  - touch: every tap target reaches --ctl-hit-touch (40px): chrome buttons
    through their invisible ::after area, the controls inside a cell
    (row checkbox, health dot, icon) through the cell, which is the tap area;
  - menus, pickers and dialogs open inside the screen;
  - phones: search sits behind a button and opens on tap; the counts row
    shows only while something is selected;
  - below 1024 px the checkbox, ID and Name are pinned (below 768, the ID
    only: Matt, 2026-09-30): they stay put when
    the rest scrolls sideways, and scrolling up and down over them moves
    the whole table; at 1440 nothing is pinned.

Coarse pointer is forced the way tools/ds_check.py does it: the page's own
@media (pointer:coarse) rules are re-injected unconditionally, since headless
Chromium always reports a fine pointer. Uses the headless shell, because the
full headless browser will not size its window below 500 px.

  python3 tools/grid_view_responsive.py            # exit 1 on any failure
  python3 tools/grid_view_responsive.py --json OUT
  python3 tools/grid_view_responsive.py --prove-fails   # each breakage below must fail the check
"""
import argparse
import html as htmlmod
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO = ROOT / "prototypes" / "grid-view" / "demo.html"
SHELLS = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium_headless_shell-*/chrome-linux/headless_shell"))
# P74 (TD-239): every launch goes through tools/check_map/chrome_fixture.py, which
# seeds the reference baseline into the current app (none other) and hands on to
# $SRET_CHROME (tools/run_checks.py coverage capture) when set, else Chromium.
sys.path.insert(0, str(ROOT / "tools" / "check_map"))
import chrome_fixture  # noqa: E402
SHELLS = [pathlib.Path(chrome_fixture.launcher())]
SIZES = [(390, 844), (768, 1024), (1440, 900)]
HIT = 40
# Each one breaks one promise; --prove-fails asserts the check catches all.
MUTATIONS = {
    "no-touch-tap-area": (".sg-btn::after,.sg-iconbtn::after,", ""),
    "menus-run-off": ("      keepInside(pop);\n", ""),
    "pinned-pane-cannot-scroll": (".sg-grid .slick-pane-left .slick-viewport{overflow-y:auto!important;", ".sg-grid .slick-pane-left .slick-viewport{"),
    "phone-search-always-shown": ("  .sg-screen:not(.is-search-open):not(.has-search) .sg-search{display:none}\n", ""),
    "no-pinning": ("s.baseOrder=grid.getColumns().map(function(c){ return c.id; }); s.pinned=false;", "s.baseOrder=grid.getColumns().map(function(c){ return c.id; }); s.pinned=false; s.pinKeys=[];"),
    "touch-rows-stay-small": ("  .sg-screen{--sg-row-h:var(--ctl-hit-touch);", "  .sg-screen{--sg-row-h:var(--ctl-h);"),
}


def coarse_css(text):
    out, start, marker = [], 0, "@media (pointer:coarse)"
    while True:
        i = text.find(marker, start)
        if i < 0:
            return "\n".join(out)
        o = text.index("{", i)
        d, j = 0, o
        while j < len(text):
            d += text[j] == "{"
            d -= text[j] == "}"
            if d == 0:
                break
            j += 1
        out.append(text[o + 1:j])
        start = j + 1


PROBE = r"""<script>
window.addEventListener('load',function(){ setTimeout(async function(){
 const sleep=ms=>new Promise(r=>setTimeout(r,ms)), $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
 const R={checks:[],notes:{}}, ok=(n,c,d)=>R.checks.push({name:n,pass:!!c,detail:d===undefined?null:d});
 const W=innerWidth, H=innerHeight, COARSE=__COARSE__, HIT=__HIT__, btn=n=>$('[data-sg='+n+']');
 const inView=el=>{ const r=el.getBoundingClientRect(); return r.left>=-1&&r.right<=W+1&&r.top>=-1&&r.bottom<=H+1; };
 const tag=el=>el.getAttribute('data-sg')||(el.hasAttribute('data-sg-hdot')?'health-dot':el.hasAttribute('data-sg-sym')?'icon':'')||(el.className&&el.className.baseVal===undefined?el.className.split(' ')[0]:el.tagName);
 try{
 const d=btn('dialog-close'); if(d) d.click(); await sleep(20);
 DEMO_USER.setName('Matt Garrett'); SRETGrid.close(); DEMO_OPEN('usertasks'); await sleep(60);
 const pre=W+'/'+(COARSE?'touch':'mouse')+': ';
 ok(pre+'no sideways page scroll', document.documentElement.scrollWidth<=W, document.documentElement.scrollWidth);
 const chromeOut=$$('.sg-bar > *, .sg-bar2 > *, .sg-bar3 > *').filter(e=>e.getBoundingClientRect().width>0&&!inView(e)).map(tag);
 ok(pre+'every header control is on screen (User tasks)', !chromeOut.length, chromeOut);
 // tap targets: box, or its ::after, or (inside a cell) the cell
 const hitOf=el=>{ const r=el.getBoundingClientRect(); let w=r.width,h=r.height;
   const a=getComputedStyle(el,'::after'); if(a.content&&a.content!=='none'&&a.position==='absolute'){ w=Math.max(w,parseFloat(a.width)||0); h=Math.max(h,parseFloat(a.height)||0); }
   const cell=el.closest('.slick-cell,.slick-header-column'); if(cell){ const c=cell.getBoundingClientRect(); w=Math.max(Math.min(w,c.width),el.closest('.sg-check')?c.width:0); h=Math.max(Math.min(h,c.height),el.closest('.sg-check')?c.height:0); }
   return [Math.round(w),Math.round(h)]; };
 const targets=$$('.sg-screen button, .sg-screen .sg-check input[type=checkbox]').filter(e=>{ const r=e.getBoundingClientRect(); return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('[hidden]'); });
 const small=targets.map(e=>[tag(e)].concat(hitOf(e))).filter(x=>x[1]<HIT||x[2]<HIT);
 const smallU=Array.from(new Set(small.map(x=>x.join(' '))));
 if(COARSE) ok(pre+'every tap target reaches '+HIT+'px (chrome buttons via their tap area; in-cell controls via the cell)', !smallU.length, smallU.slice(0,12));
 else R.notes[W+'_mouse_under40']=smallU.length;
 // row checkbox cell ticks the row
 const cb=$('.slick-row .sg-check'); if(cb){ const n0=SRETGrid._engine().grid.getSelectedRows().length;
   cb.dispatchEvent(new MouseEvent('click',{bubbles:true})); await sleep(20);
   const n1=SRETGrid._engine().grid.getSelectedRows().length;
   ok(pre+'tapping the checkbox cell (not the box) ticks the row', n1===n0+1, [n0,n1]);
   ok(pre+'with a row selected the counts row and Edit show', !!btn('count').offsetParent && !btn('bulk-edit').hidden);
   SRETGrid._engine().grid.setSelectedRows([]); await sleep(20); }
 // phones: search behind a button; counts row only while something is selected
 if(W<768){
   ok(pre+'phone: search sits behind a button; the counts row is hidden while nothing is selected', !btn('search').offsetParent && !!btn('search-toggle').offsetParent && !btn('count').offsetParent);
   btn('search-toggle').click(); await sleep(20);
   ok(pre+'phone: the search button opens search, focused', !!btn('search').offsetParent && document.activeElement===btn('search') && btn('search-toggle').getAttribute('aria-expanded')==='true');
   btn('search-toggle').click(); await sleep(20);
   const hh=Math.round($('.sg-grid').getBoundingClientRect().top-$('.sg-screen').getBoundingClientRect().top);
   R.notes[W+(COARSE?'_touch':'_mouse')+'_header_px']=hh;
   ok(pre+'phone: the header above the table takes at most '+(COARSE?100:90)+'px', hh<=(COARSE?100:90), hh);
 } else ok(pre+'search is in the header row; no search button', !!btn('search').offsetParent && !btn('search-toggle').offsetParent);
 // menus
 const menus=[]; for(const m of ['add-more','tools','view','temp-add-more']){ const b=btn(m); if(!b) continue; b.click(); await sleep(20);
   const p=btn(m+'-menu'); if(p&&!inView(p)) menus.push(m+' '+Math.round(p.getBoundingClientRect().left)+'..'+Math.round(p.getBoundingClientRect().right)); b.click(); await sleep(10); }
 ok(pre+'every menu opens inside the screen', !menus.length, menus);
 // pickers
 const hd=$('.slick-row [data-sg-hdot]'); hd.dispatchEvent(new MouseEvent('click',{bubbles:true})); await sleep(20);
 ok(pre+'the health picker opens inside the screen', btn('health-picker')&&inView(btn('health-picker')));
 document.dispatchEvent(new MouseEvent('mousedown',{bubbles:true})); await sleep(10);
 const g=SRETGrid._engine().grid, pc=g.getColumns().findIndex(c=>c.id==='pred');
 g.setActiveCell(0,pc); await sleep(10); g.getActiveCellNode().dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',keyCode:13,which:13,bubbles:true})); await sleep(30);
 const inp=btn('refs-input'); if(inp){ inp.value='S'; inp.dispatchEvent(new Event('input',{bubbles:true})); await sleep(20); }
 const rp=btn('refs-pop'), rl=btn('refs-list');
 ok(pre+'the predecessor picker and its list open inside the screen', !!rp&&inView(rp)&&!!rl&&!rl.hidden&&rl.getBoundingClientRect().left>=-1&&rl.getBoundingClientRect().right<=W+1,
    rp&&[Math.round(rp.getBoundingClientRect().left),Math.round(rp.getBoundingClientRect().right)]);
 if(inp) inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true})); await sleep(20);
 // dialogs
 const dlg=async(open,name)=>{ await open(); await sleep(30); const x=btn('dialog'); const r=x&&x.getBoundingClientRect();
   ok(pre+name+' opens inside the screen', !!x&&inView(x), r&&[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]);
   const c=btn('dialog-close'); if(c) c.click(); await sleep(20); };
 await dlg(async()=>{ btn('add-more').click(); await sleep(10); $('[data-sg=add-more-menu] [data-sg=import]').click(); },'Import dialog');
 await dlg(async()=>{ g.setSelectedRows([0,1]); await sleep(10); btn('bulk-edit').click(); },'Bulk edit dialog');
 g.setSelectedRows([]); await sleep(10);
 // pinned columns
 const pinned=SRETGrid._engine().grid.getOptions().frozenColumn>=0;
 const leftIds=$$('.sg-grid .slick-pane-header.slick-pane-left .slick-header-column').map(h=>h.id.replace(/^.*?(_checkbox_selector|id|name)$/,'$1'));
 if(W<1024){
   const want=W<768?'_checkbox_selector,id':'_checkbox_selector,id,name';
   ok(pre+(W<768?'phone: only the checkbox and ID are pinned':'tablet: checkbox, ID and Name are pinned'), pinned && leftIds.join()===want, leftIds);
   const lp=$('.sg-grid .slick-pane-top.slick-pane-left').getBoundingClientRect().width, gw=$('.sg-grid').getBoundingClientRect().width;
   R.notes[W+(COARSE?'_touch':'_mouse')+'_pinned_share']=Math.round(lp/gw*100)+'%';
   ok(pre+(W<768?'the pinned part takes under half of a phone grid':'the pinned part takes at most about 70% of the width'), lp/gw<=(W<768?0.45:0.7), Math.round(lp/gw*100)+'%');
   const right=$('.sg-grid .slick-pane-top.slick-pane-right .slick-viewport'), left=$('.sg-grid .slick-pane-top.slick-pane-left .slick-viewport');
   const idCell=()=>$('.sg-grid .slick-pane-top.slick-pane-left .slick-row .l1').getBoundingClientRect().left;
   const x0=idCell(); right.scrollLeft=300; await sleep(30);
   ok(pre+'scrolling sideways moves the other columns, not the pinned ones', right.scrollLeft>0 && Math.abs(idCell()-x0)<1, [right.scrollLeft,x0,idCell()]);
   right.scrollLeft=0; await sleep(10);
   ok(pre+'the pinned pane can scroll up and down itself (no hidden overflow)', getComputedStyle(left).overflowY==='auto', getComputedStyle(left).overflowY);
   DEMO_OPEN('stress'); await sleep(60);
   const L=$('.sg-grid .slick-pane-top.slick-pane-left .slick-viewport'), Rt=$('.sg-grid .slick-pane-top.slick-pane-right .slick-viewport');
   L.scrollTop=600; L.dispatchEvent(new Event('scroll')); await sleep(40);
   ok(pre+'scrolling up and down over the pinned columns moves the whole table (2,000 rows)', Math.abs(Rt.scrollTop-600)<=2 && Math.abs(L.scrollTop-Rt.scrollTop)<=2, [L.scrollTop,Rt.scrollTop]);
   Rt.scrollTop=1200; Rt.dispatchEvent(new Event('scroll')); await sleep(40);
   ok(pre+'and scrolling the table moves the pinned columns with it', Math.abs(L.scrollTop-1200)<=2, [L.scrollTop,Rt.scrollTop]);
   SRETGrid.close(); DEMO_OPEN('usertasks'); await sleep(40);
 } else ok(pre+'wide screen: nothing pinned', !pinned);
 // Schedule changes: the most header controls
 btn('view').click(); await sleep(10); $('[data-sg=view-menu] [data-sg=view-changes]').click(); await sleep(60);
 const cOut=$$('.sg-bar > *, .sg-bar2 > *, .sg-bar3 > *').filter(e=>e.getBoundingClientRect().width>0&&!inView(e)).map(tag);
 ok(pre+'every header control is on screen (Schedule changes)', !cOut.length, cOut);
 const pm=[]; for(const m of ['cmp-cur','cmp-basis']){ btn(m).click(); await sleep(20); const p=btn(m+'-menu'); if(!inView(p)) pm.push(m); btn(m).click(); await sleep(10); }
 ok(pre+'the schedule and compared-with menus open inside the screen', !pm.length, pm);
 await dlg(async()=>{ btn('tools').click(); await sleep(10); $('[data-sg=tools-menu] [data-sg=loaded]').click(); },'Loaded schedules dialog (wide)');
 }catch(e){ ok('probe ran without throwing',false,String(e&&e.stack||e)); }
 document.body.setAttribute('data-r',JSON.stringify(R));
},300); });
</script></body>"""


def run_one(page, w, h, coarse):
    extra = ("<style>" + coarse_css(page) + "</style></head>") if coarse else "</head>"
    probe = PROBE.replace("__COARSE__", "true" if coarse else "false").replace("__HIT__", str(HIT))
    # The last </body>: embedded libraries (SheetJS) carry the string too.
    doc = page.replace("</head>", extra, 1)
    i = doc.rindex("</body>")
    doc = doc[:i] + probe + doc[i + len("</body>"):]
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "responsive.html"
        f.write_text(doc, encoding="utf-8")
        p = subprocess.run([str(SHELLS[-1]), "--no-sandbox", "--disable-gpu", f"--window-size={w},{h}",
                            "--virtual-time-budget=15000", "--dump-dom", f.as_uri()], capture_output=True, text=True, timeout=300)
    m = re.search(r'data-r="([^"]*)"', p.stdout)
    if not m:
        return {"checks": [{"name": f"{w}/{'touch' if coarse else 'mouse'}: probe produced output", "pass": False, "detail": p.stderr[-400:]}], "notes": {}}
    return json.loads(htmlmod.unescape(m.group(1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEMO))
    ap.add_argument("--json")
    ap.add_argument("--prove-fails", action="store_true")
    a = ap.parse_args()
    if not SHELLS:
        sys.exit("No Chromium headless shell found under /opt/pw-browsers.")
    page = pathlib.Path(a.html).read_text(encoding="utf-8")
    if a.prove_fails:
        missed = []
        for name, (old, new) in MUTATIONS.items():
            if page.count(old) != 1:
                sys.exit(f"Mutation {name}: anchor found {page.count(old)} times, expected 1.")
            broken = page.replace(old, new)
            fails = sum(1 for w, h in SIZES for coarse in (False, True)
                        for c in run_one(broken, w, h, coarse)["checks"] if not c["pass"])
            print(f"-- mutation {name}: {'CAUGHT' if fails else 'MISSED'} ({fails} failing checks)")
            if not fails:
                missed.append(name)
        print(f"{len(MUTATIONS) - len(missed)} of {len(MUTATIONS)} mutations caught.")
        sys.exit(1 if missed else 0)
    checks, notes = [], {}
    for w, h in SIZES:
        for coarse in (False, True):
            r = run_one(page, w, h, coarse)
            checks += r["checks"]
            notes.update(r.get("notes", {}))
    bad = [c for c in checks if not c["pass"]]
    print(f"== grid view responsive: {len(checks) - len(bad)} pass, {len(bad)} fail")
    for c in checks:
        if not c["pass"]:
            print("  FAIL ", c["name"], " :: ", json.dumps(c["detail"])[:300])
    print("  notes:", json.dumps(notes))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"checks": checks, "notes": notes}, indent=1))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
