#!/usr/bin/env python3
"""P80 check: quick links in the blank copy (Matt, 2026-10-03, TD-248).

"In the blank version include two fields for two URLs ... quick links to the
storage location ... If there is a link ... it'd be shown as a link to open
whatever the title of the saved URL is."

Headless Chromium (--dump-dom) through chrome_fixture.py; every page opts out
of the fixture, because the links belong to the blank copy:

  B  the blank app at 1440x900 and 390x844: the fold and its four fields on
     screen with no sideways scroll; a script: address refused with the slot
     named and nothing set or marked unsaved; two links set (an https one
     with a title, a Windows folder path with none) show as two links with
     the right text, address, new-tab target and noopener; the work shows as
     unsaved; clearing them hides the list; Save writes them into the state
     block, and the saved copy carries no stale list, message or open fold.
     It then adds a user milestone and saves again, for C and D.
  C  the saved blank copy opened as a file: the empty state shows both links.
  D  a fresh blank app continues from the saved file with data: the links
     come across. The same file with one address edited by hand to
     javascript: loads with that link dropped.

    python3 tools/p80_quick_links_check.py [--html FILE]
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "check_map"))
from import_check import find_chrome  # noqa: E402

OPT_OUT = "<!-- sret:no-fixture: P80 pages open the blank app as it ships -->"
EARLY = r"""<script>
window.__errs=[];
addEventListener('error',function(e){ if(/^ResizeObserver loop/.test(e.message||'')) return; __errs.push('error: '+e.message+' @'+e.lineno); });
(function(){ var o=console.error; console.error=function(){ __errs.push('console.error: '+Array.prototype.join.call(arguments,' ')); return o.apply(console,arguments); }; })();
</script>"""

COMMON = r"""
const R={checks:[],out:{}};
const TAG=__TAG__;
function ck(n,p,d){ R.checks.push({name:TAG+': '+n,pass:!!p,detail:d===undefined?'':String(d).slice(0,400)}); }
function emit(){ R.errs=window.__errs.slice(); const o=document.createElement('pre'); o.id='p80-out';
  o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
const settle=(ms)=>new Promise(r=>setTimeout(r,ms||250));
const $=id=>document.getElementById(id);
const rc=el=>el.getBoundingClientRect();
function onScreen(el){ const r=rc(el); return r.width>0&&r.left>=-0.5&&r.right<=innerWidth+0.5; }
function noSideways(){ return document.documentElement.scrollWidth<=innerWidth+1; }
const CAPT=[];
const _click=HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click=function(){ if(this.download){ CAPT.push({name:this.download,href:this.href}); return; } return _click.apply(this,arguments); };
async function blobText(href){ const r=await fetch(href); return r.text(); }
const b64=s=>btoa(unescape(encodeURIComponent(s)));
const unb64=s=>decodeURIComponent(escape(atob(s)));
const anchors=()=>Array.from(document.querySelectorAll('#ql-list a.ql-link'));
function fill(i,title,url){ $('ql-title-'+i).value=title; $('ql-url-'+i).value=url; }
"""

SP = "https://example.sharepoint.com/sites/Proj/Shared Documents/Dashboards"
SP_N = "https://example.sharepoint.com/sites/Proj/Shared%20Documents/Dashboards"

B = OPT_OUT + r"""<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
try{
  await settle(800);
  ck('blank copy: empty state, no links shown, fold closed', isDashboardEmpty()&&$('ql-list').hidden&&!$('ql-edit').open);
  $('ql-edit').open=true; await settle(100);
  const fields=['ql-title-0','ql-url-0','ql-title-1','ql-url-1','ql-save'].map($);
  ck('fold: four fields and Save links on screen', fields.every(e=>e&&onScreen(e)), fields.map(e=>e&&JSON.stringify(rc(e))).join(' '));
  ck('fold: no sideways scroll', noSideways(), document.documentElement.scrollWidth);

  fill(0,'Evil','javascript:alert(1)'); fill(1,'','');
  let r=qlSave();
  ck('refused: a script: address, the slot named, nothing set', !r.ok&&/^Link 1: the address must start with/.test($('ql-msg').textContent)&&quickLinksGet().length===0&&$('ql-list').hidden, $('ql-msg').textContent);
  ck('refused: not marked unsaved', !$('dirty-indicator').classList.contains('show'));
  ck('refused: the message shows as an error', $('ql-msg').classList.contains('ql-err'));

  fill(0,'Saved dashboards','__SP__'); fill(1,'','C:\\Users\\me\\OneDrive - Org\\Reports');
  r=qlSave(); await settle(100);
  const a=anchors();
  ck('set: two links shown', r.ok&&a.length===2, $('ql-list').innerHTML);
  ck('set: link 1 text is its title, address normalised', a[0]&&a[0].textContent==='Saved dashboards'&&a[0].getAttribute('href')==='__SPN__', a[0]&&a[0].outerHTML);
  ck('set: link 2 has no title, so it shows the folder name', a[1]&&a[1].textContent==='Reports'&&a[1].getAttribute('href')==='file:///C:/Users/me/OneDrive%20-%20Org/Reports', a[1]&&a[1].outerHTML);
  ck('set: links open in a new tab with noopener', a.length===2&&a.every(x=>x.target==='_blank'&&/noopener/.test(x.rel)));
  ck('set: the links are on screen', a.length===2&&a.every(onScreen));
  ck('set: the work shows as unsaved', $('dirty-indicator').classList.contains('show'));
  ck('set: still the empty state', isDashboardEmpty()&&!$('empty-state').hidden);
  ck('set: the message is not an error', !$('ql-msg').classList.contains('ql-err'), $('ql-msg').textContent);

  // Clearing hides the list; setting again for the save.
  fill(0,'',''); fill(1,'',''); qlSave();
  ck('clear: no links, list hidden', quickLinksGet().length===0&&$('ql-list').hidden);
  fill(0,'Saved dashboards','__SP__'); fill(1,'','C:\\Users\\me\\OneDrive - Org\\Reports'); qlSave();

  publishDashboard(); await settle(400);
  let pub=CAPT.filter(c=>/\.html$/.test(c.name)).pop();
  const html=pub?await blobText(pub.href):'';
  const st=SRETContinue.extractState(html).payload||{};
  ck('save: the state block carries both links', Array.isArray(st.quickLinks)&&st.quickLinks.length===2&&st.quickLinks[0].url==='__SPN__', JSON.stringify(st.quickLinks));
  const doc=new DOMParser().parseFromString(html,'text/html');
  ck('save: no stale list or message, the fold saved closed',
     !doc.getElementById('ql-list').innerHTML.trim()&&!doc.getElementById('ql-msg').textContent.trim()&&!doc.getElementById('ql-edit').hasAttribute('open'));
  R.out.empty=b64(html);

  const um=addUserMilestone({name:'P80 user milestone',date:isoDay(WE_DATES[Math.min(WE_DATES.length-1,NOW_COL+2)]),type:'MS',state:'FUTURE'});
  noteMarkup(); scheduleRerender(true); await settle(500);
  publishDashboard(); await settle(400);
  pub=CAPT.filter(c=>/\.html$/.test(c.name)).pop();
  R.out.data=b64(await blobText(pub.href)); R.out.dataName=pub.name;
}catch(e){ ck('probe B ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""

C = r"""<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
try{
  await settle(800);
  const a=anchors();
  ck('saved blank copy: still the empty state', isDashboardEmpty()&&!$('empty-state').hidden);
  ck('saved blank copy: both links shown, titles and addresses intact',
     a.length===2&&a[0].textContent==='Saved dashboards'&&a[0].getAttribute('href')==='__SPN__'&&a[1].textContent==='Reports', $('ql-list').innerHTML);
  ck('saved blank copy: fold closed, fields filled for editing', !$('ql-edit').open&&$('ql-url-0').value==='__SPN__');
  ck('saved blank copy: not unsaved on open', !$('dirty-indicator').classList.contains('show'));
}catch(e){ ck('probe C ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""

D = OPT_OUT + r"""
<script type="text/plain" id="p80-saved">__SAVED__</script>
<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
try{
  await settle(800);
  const text=unb64($('p80-saved').textContent.trim());
  await continueChosen(new File([text],'__NAME__',{type:'text/html'}));
  $('continue-apply').click(); await settle(600);
  let l=quickLinksGet();
  ck('continue: both links came across', l.length===2&&l[0].label==='Saved dashboards'&&l[1].label==='Reports', JSON.stringify(l));
  const hacked=text.replace('"url":"__SPN__"','"url":"javascript:alert(1)"');
  ck('continue (hand-edited): the file really was edited', hacked!==text);
  await continueChosen(new File([hacked],'edited.html',{type:'text/html'}));
  $('continue-apply').click(); await settle(600);
  l=quickLinksGet();
  ck('continue (hand-edited): the script: link is dropped, the other kept', l.length===1&&l[0].label==='Reports'&&!JSON.stringify(QUICK_LINKS).includes('javascript'), JSON.stringify(l));
}catch(e){ ck('probe D ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""


def sub(s):
    return s.replace("__SPN__", SP_N).replace("__SP__", SP)


def page_with(html, probe):
    page = html.replace("<head>", "<head>" + EARLY, 1)
    i = page.rindex("</body>")
    return page[:i] + probe + "\n" + page[i:]


def run_dump(page, size):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p80.html"
        f.write_text(page, encoding="utf-8")
        p = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                            f"--user-data-dir={td}/prof", f"--window-size={size[0]},{size[1]}",
                            "--virtual-time-budget=240000", "--dump-dom", f.as_uri()],
                           capture_output=True, text=True, timeout=300)
    m = re.search(r'<pre id="p80-out">(.*?)</pre>', p.stdout, re.S)
    if not m:
        return {"checks": [{"name": "probe output found", "pass": False, "detail": p.stderr[-800:]}], "errs": [], "out": {}}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def collect(res, tag):
    out = list(res["checks"])
    errs = res.get("errs") or []
    out.append({"name": tag + ": no page errors", "pass": not errs, "detail": " | ".join(errs)[:400]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    a = ap.parse_args()
    html = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks, out = [], {}
    for size in [(1440, 900), (390, 844)]:
        tag = f"B blank {size[0]}"
        r = run_dump(page_with(html, sub(B).replace("__TAG__", json.dumps(tag))), size)
        checks += collect(r, tag)
        out = out or r.get("out") or {}
    if out.get("empty"):
        saved = base64.b64decode(out["empty"]).decode("utf-8")
        tag = "C saved blank 390"
        checks += collect(run_dump(page_with(saved, sub(C).replace("__TAG__", json.dumps(tag))), (390, 844)), tag)
    if out.get("data"):
        tag = "D continue 1440"
        probe = sub(D).replace("__TAG__", json.dumps(tag)).replace("__SAVED__", out["data"]).replace("__NAME__", out["dataName"])
        checks += collect(run_dump(page_with(html, probe), (1440, 900)), tag)
    fails = 0
    for c in checks:
        fails += not c["pass"]
        print(("PASS " if c["pass"] else "FAIL ") + c["name"] + ("" if c["pass"] or not c["detail"] else "  [" + c["detail"] + "]"))
    print(f"{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
