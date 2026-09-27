#!/usr/bin/env python3
"""
P59 layout and consistency check (Matt's P59 feedback, items A, B, C, D, X).

Runs the real app in headless Chromium at several widths and reads geometry
and computed style, never a screenshot:

  A-01  the Unsaved changes pill sits on the subtitle line, right-aligned
  A-02  header controls share --ctl-h; the shadow switch is 32x16; the More
        actions trigger is an --icon-btn, and on touch stays 32px visible
        (its 40px hit area is a pseudo-element, not a bigger box)
  B-01  three rail states: rail, collapsed (toggle in the header's left slot),
        panel; the state persists; phones start collapsed; opening a section
        from collapsed shows the rail
  B-02  the header's title and subtitle do not move between rail states
  X-02  the rail badge sits clear of its icon (offset up and right)
  C-01  Find fits its card at wide widths: Source stays inside, Banding is not
        clipped
  C-02  Activity name takes half of Find's first row
  C-03  phone: each label sits just above its own field
  C-04  Fit columns is a labelled button
  C-05  phone: the Mode toggle keeps its natural width
  D-01  the card is wide enough for an actualised date ("04-Aug-26 A")
  D-02  icon then ID, close together, icon 15px
  D-03  float sits between the ID and the status; "-" placeholder; read-only
        "-" on a completed milestone
  D-04  status is right-aligned on an underlined heading
  D-05  Save / Save & close at the larger size
  D-06  the title spans the card with a background
  D-07  "Display label:" row above the title
  X-01  the card is opaque

Usage:
  python3 tools/p59_check.py [--html FILE]
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
from ds_check import extract_coarse_css  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
OUT_RE = re.compile(r'<pre id="p59-out">(.*?)</pre>', re.S)

PROBE = r"""
(function(){
  const ARGS=__ARGS__;
  try{ localStorage.clear(); }catch(e){}
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:'['+ARGS.tag+'] '+n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p59-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,260));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const cs=el=>getComputedStyle(el);
  const px=v=>parseFloat(cs(document.documentElement).getPropertyValue(v));
  const W=window.innerWidth;
  window.addEventListener('load',function(){ setTimeout(async function(){
   try{
    const ctlH=px('--ctl-h'), iconBtn=px('--icon-btn');
    R.notes.ctlH=ctlH; R.notes.iconBtn=iconBtn; R.notes.W=W;

    // ---------- B-01 default state ----------
    const collapsed=()=>document.body.classList.contains('rail-collapsed');
    if(ARGS.phone){
      ck('B-01 a phone starts with the rail collapsed', collapsed());
    } else {
      ck('B-01 a wide screen starts with the rail showing', !collapsed());
    }

    if(!ARGS.phone && !ARGS.coarse){
      // ---------- A-01 ----------
      const pill=$('dirty-indicator');
      pill.style.display='inline-block';
      const top=pill.parentElement, sub=document.querySelector('.rpt-hd .subtitle');
      ck('A-01 the pill shares the subtitle line', top.classList.contains('rpt-hd-top')&&top.contains(sub));
      const pr=rc(pill), sr=rc(sub), hr=rc(document.querySelector('.rpt-hd'));
      ck('A-01 the pill is right-aligned in the header', hr.right-pr.right<=12, (hr.right-pr.right).toFixed(1));
      ck('A-01 the pill is level with the subtitle',
         Math.abs((pr.top+pr.bottom)/2-(sr.top+sr.bottom)/2)<=3, [pr.top,sr.top].map(Math.round).join('/'));
      pill.style.display='';

      // ---------- A-02 ----------
      ['vt-baseline','vt-update','btn-add-ms','btn-filter-expand'].forEach(function(id){
        const e=$(id); if(!e||!e.offsetParent) return;
        ck('A-02 '+id+' is --ctl-h tall', Math.abs(rc(e).height-ctlH)<0.6, rc(e).height);
      });
      const sw=document.querySelector('.bl-shadow .toggle-switch');
      if(sw) ck('A-02 the Baseline shadow switch is 32x16', Math.round(rc(sw).width)===32&&Math.round(rc(sw).height)===16,
                rc(sw).width+'x'+rc(sw).height);

      // ---------- B-02 / B-01 transitions ----------
      const title=$('rpt-title-text');
      const before={t:rc(title).left, s:rc(sub).left, h:rc(document.querySelector('.rpt-hd')).top};
      setRailState('collapsed'); await settle();
      const after={t:rc(title).left, s:rc(sub).left, h:rc(document.querySelector('.rpt-hd')).top};
      ck('B-01 collapsing hides the rail', cs($('ws-rail')).display==='none');
      const tg=$('ws-toggle');
      ck('B-01 the Workspace toggle takes the header left slot', cs(tg).display!=='none'&&rc(tg).left===0&&rc(tg).top===0,
         rc(tg).left+','+rc(tg).top);
      ck('B-01 the board takes the rail width back', parseFloat(cs(document.body).marginLeft)===0, cs(document.body).marginLeft);
      ck('B-02 the report title does not move', Math.abs(after.t-before.t)<1, (after.t-before.t).toFixed(2));
      ck('B-02 the subtitle does not move', Math.abs(after.s-before.s)<1, (after.s-before.s).toFixed(2));
      ck('B-02 the toggle does not overlap the title', rc(tg).right<=rc(title).left, rc(tg).right+' vs '+rc(title).left);
      let stored=null; try{ stored=localStorage.getItem('sret-rail'); }catch(e){}
      ck('B-01 the collapsed state persists', stored==='collapsed', stored);
      setWorkspaceSection('notes',true); await settle();
      ck('B-01 opening a section from collapsed shows the rail and the panel',
         !collapsed()&&cs($('ws-rail')).display!=='none'&&$('ws-panel').classList.contains('open'));
      toggleWorkspace(false); await settle();
      ck('B-01 closing the panel leaves the rail', !collapsed()&&!$('ws-panel').classList.contains('open'));
      $('ws-tab-collapse').click(); await settle();
      ck('B-01 the rail\'s own first button collapses it', collapsed());
      tg.click(); await settle();
      ck('B-01 the toggle brings the rail back', !collapsed()&&tg.getAttribute('aria-expanded')==='true');

      // ---------- X-02 ----------
      const bd=document.querySelector('#ws-rail .ws-bd');
      if(bd){
        const had=bd.textContent; bd.textContent='3';
        const b=rc(bd), i=rc(bd.parentElement);
        ck('X-02 the badge is offset up and right of its icon', b.top<i.top&&b.right>i.right,
           [b.top,i.top,b.right,i.right].map(Math.round).join(','));
        bd.textContent=had;
      }

      // ---------- C-01 / C-02 ----------
      const grp=$('tfb-source-group');
      grp.style.display=''; grp.parentElement.classList.add('has-source');
      if(!$('filter-bar').classList.contains('open')) toggleFilterBar();
      await settle();
      const find=$('tfb-find'), fr=rc(find);
      const nameW=rc(document.querySelector('#tfb-find .fb-row-1 .ds-fwrap')).width;
      const rowW=rc(document.querySelector('#tfb-find .fb-row-1')).width;
      ck('C-02 Activity name takes about half of Find\'s first row', nameW/rowW>0.44&&nameW/rowW<0.56, (nameW/rowW).toFixed(2));
      const src=$('filter-source');
      ck('C-01 Source stays inside the Find card', rc(src).right<=fr.right-1, Math.round(rc(src).right)+' vs '+Math.round(fr.right));
      const bl=document.querySelector('#tfb-find label[for="filter-band"]');
      ck('C-01 the Banding label is not clipped', bl.scrollWidth<=bl.clientWidth+1&&rc(bl).right<=rc($('filter-band')).left,
         bl.scrollWidth+'/'+bl.clientWidth);
      ck('C-01 the name field is not truncated to a sliver', nameW>=200, nameW);

      // ---------- C-04 ----------
      const fit=$('btn-fit-screen-inline');
      ck('C-04 Fit columns is a labelled button', fit.classList.contains('ds-btn')&&/Fit/.test(fit.textContent)&&
         parseFloat(cs(fit).borderTopWidth)>=1&&Math.abs(rc(fit).height-ctlH)<0.6, fit.textContent.trim()+' '+rc(fit).height);

      // ---------- D (card) ----------
      const wraps=Array.prototype.slice.call(document.querySelectorAll('#tbody .m-wrap[data-ms]'));
      const dlg=$('ms-dialog');
      async function openCard(w){ if(!dlg.hidden){ discardMsDialog(); await settle(); } w.click(); await settle(); return !dlg.hidden; }
      ck('D the board has milestones to open', wraps.length>0, wraps.length);
      await openCard(wraps[0]);
      const d=rc(dlg);
      ck('D-01 the card is 340px wide', Math.round(d.width)===340, d.width);
      ck('X-01 the card background is opaque', /^rgb\(/.test(cs(dlg).backgroundColor)||/, 1\)$/.test(cs(dlg).backgroundColor),
         cs(dlg).backgroundColor);
      const hd=dlg.querySelector('.ms-heading'), ib=$('ms-icon-btn'), code=$('ms-code'), st=$('ms-status'), fc=$('ms-float-col');
      ck('D-02 icon 15px in an --icon-btn button', Math.round(rc(ib.querySelector('svg')).width)===15&&Math.round(rc(ib).width)===iconBtn,
         rc(ib).width);
      ck('D-02 icon sits further left than the card padding', rc(ib).left-d.left<=parseFloat(cs(dlg).paddingLeft), rc(ib).left-d.left);
      ck('D-02 icon to ID gap is tight', rc(code).left-rc(ib).right<=5, (rc(code).left-rc(ib).right).toFixed(1));
      ck('D-03 float sits between the ID and the status', fc.parentElement===hd&&rc(fc).left>rc(code).right&&rc(fc).right<=rc(st).left,
         [rc(code).right,rc(fc).left,rc(fc).right,rc(st).left].map(Math.round).join(','));
      ck('D-03 a blank float shows "-"', $('ms-float-val').getAttribute('placeholder')==='-');
      ck('D-04 status is right-aligned', Math.abs(rc(st).right-rc(hd).right)<=1, (rc(hd).right-rc(st).right).toFixed(1));
      ck('D-04 the heading is underlined', parseFloat(cs(hd).borderBottomWidth)>=1);
      const t=$('ms-title'), stl=dlg.querySelector('.ms-shorttitle-lbl');
      ck('D-06 the title spans the card', rc(t).width>=d.width-2*parseFloat(cs(dlg).paddingLeft)-2, rc(t).width);
      ck('D-06 the title has a background', cs(t).backgroundColor!=='rgba(0, 0, 0, 0)', cs(t).backgroundColor);
      ck('D-07 "Display label:" sits above the title', stl&&stl.textContent==='Display label:'&&rc(stl).bottom<=rc(t).top,
         stl&&stl.textContent);
      $('ms-title').value=$('ms-title').value+' x'; $('ms-title').dispatchEvent(new Event('input',{bubbles:true}));
      await settle();
      const sb=document.querySelectorAll('#ms-save-actions .ms-act');
      ck('D-05 Save buttons at the larger size', sb.length===2&&parseFloat(cs(sb[0]).fontSize)>=11&&rc(sb[1]).height>=20,
         cs(sb[0]).fontSize+' '+rc(sb[1]).height);
      discardMsDialog(); await settle();
      // D-01: an actualised finish fits.
      const probe=$('ms-date');
      await openCard(wraps[0]); probe.value='04-Aug-26 A';
      ck('D-01 an actualised date fits its field', probe.scrollWidth<=probe.clientWidth+1, probe.scrollWidth+'/'+probe.clientWidth);
      discardMsDialog(); await settle();
      // D-03: a completed milestone reads "-" and is read-only.
      const doneW=wraps.find(function(w){ return w.querySelector('.ms-icon.s-done,.ms-icon.s-doneuser'); });
      if(doneW){
        await openCard(doneW);
        ck('D-03 a completed milestone\'s float is a read-only "-"', $('ms-float-val').readOnly&&$('ms-float-val').value==='');
        discardMsDialog(); await settle();
      } else ck('D-03 the seed has a completed milestone to test', false);
    }

    if(ARGS.phone){
      if(!$('filter-bar').classList.contains('open')) toggleFilterBar();
      await settle();
      // ---------- C-03 ----------
      [['filter-title','.ds-fwrap'],['filter-ids','.ds-fwrap'],['wr-field',null]].forEach(function(p){
        const f=$(p[0]); const box=p[1]?f.closest(p[1]):f;
        const lb=document.querySelector('label[for="'+p[0]+'"]');
        const gap=rc(box).top-rc(lb).bottom;
        ck('C-03 '+p[0]+' label sits just above its field', gap>=0&&gap<=6, gap.toFixed(1));
      });
      // ---------- C-05 ----------
      const seg=$('wr-mode-seg'), card=$('tfb-when');
      ck('C-05 the Mode toggle keeps its natural width', rc(seg).width<rc(card).width*0.8, Math.round(rc(seg).width)+'/'+Math.round(rc(card).width));
      // B-02 on a phone: the toggle and the title do not overlap.
      const tg=$('ws-toggle'), title=$('rpt-title-text');
      ck('B-02 phone: the toggle does not overlap the title', rc(tg).right<=rc(title).left+0.5, rc(tg).right+' vs '+rc(title).left);
    }

    if(ARGS.coarse){
      const mb=$('btn-more-actions');
      if(mb&&mb.offsetParent){
        ck('A-02 touch: the More actions trigger stays 32px visible', Math.round(rc(mb).width)===32&&Math.round(rc(mb).height)===32,
           rc(mb).width+'x'+rc(mb).height);
        const hit=getComputedStyle(mb,'::after');
        ck('A-02 touch: its hit area is 40px from a pseudo-element', parseFloat(hit.width)===40, hit.width);
        ck('A-02 touch: it has no white tile background', cs(mb).backgroundColor==='rgba(0, 0, 0, 0)', cs(mb).backgroundColor);
      } else ck('A-02 touch: the More actions trigger is showing at this width', false);
    }
   }catch(e){ ck('probe ran without throwing', false, e&&e.stack||e); }
   emit();
  },900); });
})();
"""

RUNS = [
    {"tag": "1920", "w": 1920, "h": 1080},
    {"tag": "1440", "w": 1440, "h": 900},
    {"tag": "390", "w": 390, "h": 844, "phone": True},
    {"tag": "900-coarse", "w": 900, "h": 900, "coarse": True},
]


def render(html: str, w: int, h: int) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    out = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                          f"--window-size={w},{h}", "--virtual-time-budget=40000",
                          "--dump-dom", "file://" + path],
                         capture_output=True, text=True, timeout=240).stdout
    m = OUT_RE.search(out)
    if not m:
        return {"checks": [{"name": f"[{w}] probe produced output", "pass": False, "detail": ""}]}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    coarse_css = extract_coarse_css(src)
    fails = 0
    total = 0
    for run in RUNS:
        args = {"tag": run["tag"], "phone": bool(run.get("phone")), "coarse": bool(run.get("coarse"))}
        extra = f"<style>{coarse_css}</style>" if run.get("coarse") else ""
        html = src.replace("</body>", f"{extra}<script>\n{PROBE.replace('__ARGS__', json.dumps(args))}\n</script>\n</body>")
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
