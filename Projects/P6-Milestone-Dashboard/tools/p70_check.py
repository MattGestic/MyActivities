#!/usr/bin/env python3
"""
P70 check: the grid view module re-pasted as a core plus features (TD-229).

Runs the real app in headless Chromium with the host resolver pointed at
nothing, and reads DOM, store contents and engine state, never a screenshot.

  setup   SRETGrid.features() is exactly the pasted set (marks, bulk-edit,
          xlsx); lists and import are not loaded (their helper modules are
          not embedded)
  bulk    three milestones added through the real Add milestone path; View
          items opens the grid; selecting two rows shows "Edit 2 rows"; the
          dialog lists Progress and Health; % complete 50 on two rows reaches
          USER_MILESTONES through the grid's onEdit; 150 is stopped by the
          app's onEdit and listed as not accepted, the store unchanged; a
          date typed as 9-Oct-26 is read in the app's own format; the third
          row is untouched
  tablet  at 900 px the checkbox, ID and Name are pinned (frozen columns)
  phone   at 390 px only the checkbox and ID are pinned

Usage:
  python3 tools/p70_check.py [--html FILE]
Exit code 1 if any assertion fails.
"""
import argparse
import os
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
# The headless shell sizes its window below 500 px (full headless Chromium does not).
SHELLS = sorted(pathlib.Path("/opt/pw-browsers").glob("chromium_headless_shell-*/chrome-linux/headless_shell"))
OUT_RE = re.compile(r'<pre id="p70-out">([^<]*)</pre>')

PROBE = r"""
(function(){
  const MODE=__MODE__;
  try{ localStorage.clear(); }catch(e){}
  const R={checks:[]};
  function ck(n,p,d){ R.checks.push({name:'['+MODE+'] '+n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p70-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const $=id=>document.getElementById(id), q=s=>document.querySelector(s);
  function addMs(name){ openAddMilestone(); $('add-ms-name').value=name; saveAddMilestone(); }
  async function openGrid(){
    addMs('Probe one'); addMs('Probe two'); addMs('Probe three'); await wait(150);
    setWorkspaceSection('userms',true); await wait(50);
    $('btn-userms-view').click(); await wait(150);
    return SRETGrid._engine();
  }
  const frozen=E=>{ const f=E.grid.getOptions().frozenColumn; return f<0?'none':E.grid.getColumns().slice(0,f+1).map(c=>c.id).join(','); };

  async function bulkMode(){
    ck('setup: features are exactly marks, bulk-edit, xlsx', JSON.stringify(SRETGrid.features())==='["marks","bulk-edit","xlsx"]', SRETGrid.features());
    ck('lists and import helper modules are not embedded', typeof window.SRETCollections==='undefined'&&typeof window.SRETMsImport==='undefined');
    const E=await openGrid();
    ck('View items opens the grid with the three milestones', !!E&&E.dataView.getLength()===3, E&&E.dataView.getLength());
    if(!E) return;
    ck('no rows selected: no Edit button', !!q('[data-sg=bulk-edit]')&&q('[data-sg=bulk-edit]').hidden);
    const ids=[0,1,2].map(i=>E.dataView.getItem(i).id);
    E.grid.setSelectedRows([0,1]); await wait(30);
    const b=q('[data-sg=bulk-edit]');
    ck('two rows selected: "Edit 2 rows" shows in the header', !!b&&!b.hidden&&b.textContent==='Edit 2 rows', b&&b.textContent);
    b.click(); await wait(40);
    const fields=[...document.querySelectorAll('[data-sg=bulk-fields] .sg-bulk-lbl span')].map(s=>s.textContent);
    ck('the dialog lists the editable fields, Health included', fields.length>2&&fields.some(f=>/complete|Progress/i.test(f))&&fields.includes('Health'), fields.join('|'));
    const pkey=E.grid.getColumns().map(c=>c.sg&&c.sg.key).find(k=>k&&/progress|pct/i.test(k));
    const set=(k,v)=>{ const el=q('[data-sg=bulk-ctl-'+k+'] input, [data-sg=bulk-ctl-'+k+'] select'); el.value=v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); };
    set(pkey,'50'); q('[data-sg=bulk-apply]').click(); await wait(60);
    const ms=id=>USER_MILESTONES.find(m=>m.id===id);
    const pv=id=>{ const m=ms(id); return m&&(m.progress!=null?m.progress:m.pct); };
    ck('% complete 50 reaches USER_MILESTONES for both selected rows; the third is untouched',
       pv(ids[0])==50&&pv(ids[1])==50&&pv(ids[2])!=50, [pv(ids[0]),pv(ids[1]),pv(ids[2])].join(','));
    const sum=[...document.querySelectorAll('[data-sg=bulk-summary] li')].map(l=>l.textContent);
    ck('a summary names the change', /^Updated 2 rows/.test(sum[0]||''), sum.join(' / '));
    q('[data-sg=bulk-done]').click(); await wait(30);
    E.grid.setSelectedRows([0,1]); await wait(20); q('[data-sg=bulk-edit]').click(); await wait(40);
    set(pkey,'150'); q('[data-sg=bulk-apply]').click(); await wait(60);
    const err=q('[data-sg=bulk-error]'), sum2=[...document.querySelectorAll('[data-sg=bulk-summary] li')].map(l=>l.textContent);
    ck('150 is refused (range check or the app\'s onEdit); the store keeps 50',
       pv(ids[0])==50&&pv(ids[1])==50&&((err&&!err.hidden)||/not accepted/.test(sum2.join(' '))), (err&&err.textContent)+' | '+sum2.join(' / '));
    const dlgClose=q('[data-sg=dialog-close]'); if(dlgClose) dlgClose.click(); await wait(20);
    const dkey=E.grid.getColumns().map(c=>c.sg).filter(c=>c&&c.type==='date'&&c.editable).map(c=>c.key)[0];
    if(dkey){
      E.grid.setSelectedRows([0]); await wait(20); q('[data-sg=bulk-edit]').click(); await wait(40);
      const di=q('[data-sg=bulk-ctl-'+dkey+'] input');
      ck('bulk dates are typed in the app\'s format (placeholder e.g. 9-Oct-26), not the browser picker', !!di&&di.type==='text'&&di.placeholder==='e.g. 9-Oct-26', di&&di.placeholder);
      set(dkey,'31-Feb-26'); q('[data-sg=bulk-apply]').click(); await wait(40);
      ck('an impossible date (31-Feb-26) is refused before anything changes', !!q('[data-sg=bulk-error]')&&!q('[data-sg=bulk-error]').hidden, q('[data-sg=bulk-error]')&&q('[data-sg=bulk-error]').textContent);
    }
  }
  async function pinMode(){
    const E=await openGrid();
    if(!E){ ck('grid opened', false); return; }
    await wait(80);
    const want=MODE==='phone'?'_checkbox_selector,id':'_checkbox_selector,id,name';
    ck((MODE==='phone'?'phone (390px): only the checkbox and ID are pinned':'tablet (900px): checkbox, ID and Name are pinned'),
       frozen(E)===want, frozen(E));
  }
  window.addEventListener('load',function(){ setTimeout(async function(){
    try{ if(MODE==='bulk') await bulkMode(); else await pinMode(); }
    catch(e){ ck('probe ran without throwing', false, e&&e.stack||e); }
    emit();
  },900); });
})();
"""


def render(html: str, width: int, height: int) -> list:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    # SRET_CHROME overrides the lookup (tools/run_checks.py coverage capture).
    exe = os.environ.get("SRET_CHROME") or (str(SHELLS[-1]) if SHELLS else "chromium")
    out = subprocess.run([exe, "--headless", "--no-sandbox", "--disable-gpu",
                          "--host-resolver-rules=MAP * ~NOTFOUND",
                          f"--window-size={width},{height}", "--virtual-time-budget=40000",
                          "--dump-dom", "file://" + path],
                         capture_output=True, text=True, timeout=300).stdout
    m = OUT_RE.search(out)
    if not m:
        return [{"name": f"probe at {width}px produced output", "pass": False, "detail": ""}]
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))["checks"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks = []
    for mode, w, h in (("bulk", 1440, 900), ("tablet", 900, 800), ("phone", 390, 844)):
        i = src.rindex("</body>")
        html = src[:i] + "<script>\n" + PROBE.replace("__MODE__", json.dumps(mode)) + "\n</script>\n" + src[i:]
        checks += render(html, w, h)
    fails = 0
    for c in checks:
        fails += 0 if c["pass"] else 1
        print(("PASS " if c["pass"] else "FAIL ") + c["name"] + ("" if c["pass"] else f"  ({c['detail']})"))
    print(f"\n{len(checks) - fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
