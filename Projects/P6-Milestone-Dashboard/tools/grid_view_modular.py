#!/usr/bin/env python3
"""Grid view: the core and its features stand alone (Matt, 2026-09-30).

The grid is a core (src/modules/grid-view/grid-view.js) plus optional
features (src/modules/grid-view/features/*.js), set up once per deployment
with SRETGrid.setup(). This check builds bare pages, with none of the demo
app, and proves:

  core only        the core opens, edits, filters, adds and deletes with no
                   feature loaded; feature controls are absent; options that
                   need a feature fail at open with a message naming it;
                   unknown column types show as text.
  refs + bulk-edit two features without the others: bulk edit uses the
                   refs token field; no lists, export or import controls.
  all + setup()    setup fails fast (unknown feature, a feature whose helper
                   module is missing, a bad layout value); features left out
                   of setup() are off; defaults reach every screen and a
                   screen's own options win; text, date format, layout and
                   symbolClass settings take effect.

  python3 tools/grid_view_modular.py            # exit 1 on any failure
  python3 tools/grid_view_modular.py --prove-fails   # each breakage below must fail the check
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from grid_view_assemble import token_blocks, safe_inline, MOD, VENDOR, COLL  # noqa: E402
from import_check import find_chrome  # noqa: E402

FEATURES = ["refs", "marks", "bulk-edit", "lists", "xlsx", "import"]

# Each one breaks one promise of the split; --prove-fails asserts the check catches all.
MUTATIONS = {
    "disabled-feature-still-runs": ("function enabled(name){ return !CONF||!CONF.features||CONF.features.indexOf(name)>=0; }",
                                    "function enabled(name){ return true; }"),
    "setup-accepts-unknown-feature": ("      if(unknown.length) throw new Error('SRETGrid.setup: feature'", "      if(false) throw new Error('SRETGrid.setup: feature'"),
    "defaults-ignored": ("var opts=Object.assign({},CONF&&CONF.defaults,cfg);", "var opts=Object.assign({},cfg);"),
    "screen-cannot-override-defaults": ("var opts=Object.assign({},CONF&&CONF.defaults,cfg);", "var opts=Object.assign({},cfg,CONF&&CONF.defaults);"),
    "missing-feature-silent": ("      if(o[k]&&names.indexOf(NEEDS[k])<0)\n", "      if(false)\n"),
    "needs-not-checked": ("      if(!root[g]) throw new Error('SRETGrid.'+where", "      if(false) throw new Error('SRETGrid.'+where"),
    "date-format-setting-ignored": ("  function fmtDate(v){ return DATES.format(v); }", "  function fmtDate(v){ return fmtDateDMY(v); }"),
    "core-needs-lists": ("    for(var i=0;i<s.rowFilters.length;i++) if(!s.rowFilters[i](item)) return false;",
                         "    if(s.scope.type) return false;"),
    "phone-pin-set-ignored": ("    var phone=s.pinPhoneKeys&&s.screen.clientWidth<LAYOUT.phoneBelow;", "    var phone=false;"),
    "pin-set-switch-keeps-old-order": ("    if(s.pinned&&s.pinSet!==keys.join()) unpin(s);\n", ""),
    "bulk-refs-needs-refs-feature-order": ("      if(c.type==='refs'&&R){", "      if(c.type==='refs'&&!R){"),
}

HARNESS = r"""
<script>
(async function(){
const R={checks:[]};
function ok(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:pass?null:detail}); }
function throws(fn,re){ try{ fn(); return 'no error'; }catch(e){ return re.test(String(e.message))?true:String(e.message); } }
const $=(s,r)=>(r||document).querySelector(s), $$=(s,r)=>Array.from((r||document).querySelectorAll(s));
function rows(){ return [{id:'A-1',name:'Pump',finish:'2026-10-09',qty:3,kind:'x',pred:'A-2'},{id:'A-2',name:'Valve',finish:'2026-11-01',qty:7,kind:'y',pred:''},
                         {id:'A-3',name:'Pipe',finish:'2026-12-15',qty:1,kind:'x',pred:''}]; }
const COLS=[{key:'id',label:'ID',type:'text'},{key:'name',label:'Name',type:'text',editable:true},{key:'finish',label:'Finish',type:'date',editable:true},
            {key:'qty',label:'Qty',type:'number',editable:true},{key:'kind',label:'Kind',type:'select',editable:true,options:['x','y']},
            {key:'pred',label:'Predecessors',type:'refs',editable:true}];
const log=[];
function cfg(extra){ return Object.assign({title:'Parts',rowKey:'id',editable:true,columns:COLS,rows:rows(),
  onEdit:function(k,f,v){ log.push([k,f,v]); },onAdd:function(){ return {id:'A-9',name:'New'}; },onDelete:function(){},
  refOptions:function(){ return rows().map(function(r){ return {id:r.id,name:r.name}; }); }},extra||{}); }
function editCell(key,value){
  const e=SRETGrid._engine(), g=e.grid, ci=g.getColumns().findIndex(c=>c.id===key);
  g.setActiveCell(0,ci); g.editActiveCell(); const ed=g.getCellEditor(); ed.el.value=value; g.getEditorLock().commitCurrentEdit();
}
try{
__BODY__
}catch(err){ ok('probe ran without throwing', false, String(err&&err.stack||err)); }
ok('no uncaught page errors', window.__errs.length===0, window.__errs);
const pre=document.createElement('pre'); pre.id='out'; pre.textContent=JSON.stringify(R); document.body.appendChild(pre);
})();
</script>
"""

CORE_ONLY = r"""
ok('core only: no features loaded', JSON.stringify(SRETGrid.features())==='[]', SRETGrid.features());
SRETGrid.open(cfg());
const e=SRETGrid._engine();
ok('core only: opens with every row and the checkbox column', e.dataView.getLength()===3 && e.grid.getColumns()[0].id==='_checkbox_selector', e.dataView.getLength());
editCell('name','Pump set');
ok('core only: a cell edit reaches onEdit(rowKey,key,value)', JSON.stringify(log[log.length-1])==='["A-1","name","Pump set"]', log);
const f=$('[data-sg-filter="qty"]'); f.value='>=3'; f.dispatchEvent(new Event('input',{bubbles:true}));
ok('core only: header filters and operators work', e.dataView.getLength()===2, e.dataView.getLength());
f.value=''; f.dispatchEvent(new Event('input',{bubbles:true}));
$('[data-sg=add]').click(); SRETGrid._engine().grid.getEditorLock().cancelCurrentEdit();
ok('core only: Add row adds the row onAdd returns', e.dataView.getLength()===4, e.dataView.getLength());
$('[data-sg=add-more]').click();
const items=$$('[data-sg=add-more-menu] > *').map(x=>x.getAttribute('data-sg')||(x.classList.contains('sg-menu-sep')?'---':''));
ok('core only: the Add row menu holds Delete only (no export, template or import without their features)', JSON.stringify(items)==='["delete"]', items);
$('[data-sg=add-more]').click();
ok('core only: no feature controls (bulk edit, temp list, rail, export button)', !$('[data-sg=bulk-edit]') && !$('[data-sg=temp-add]') && !$('.sg-rail') && !$('[data-sg=export]'));
const ci=e.grid.getColumns().findIndex(c=>c.id==='pred');
ok('core only: a type no loaded feature provides (refs) is edited as text', e.grid.getColumns()[ci].editor&&e.grid.getColumns()[ci].editor.name==='Editor', e.grid.getColumns()[ci].editor&&e.grid.getColumns()[ci].editor.name);
ok('core only: feature API (exportVisible, importAoa) is absent', typeof SRETGrid.exportVisible==='undefined' && typeof SRETGrid.importAoa==='undefined');
SRETGrid.close();
const L=throws(()=>SRETGrid.open(cfg({lists:{store:{},refOf:x=>x}})),/lists needs the lists feature \(features\/lists\.js\), which is not loaded/);
ok('core only: lists fails at open, naming the feature file', L===true, L);
const I=throws(()=>SRETGrid.open(cfg({importer:{}})),/importer needs the import feature/);
ok('core only: importer fails at open, naming the feature', I===true, I);
ok('core only: a failed open leaves no screen behind', !SRETGrid.isOpen() && !$('.sg-screen'));
const U=throws(()=>SRETGrid.setup({features:['lists']}),/feature not loaded: lists\. Loaded: none\./);
ok('core only: setup names a feature that is not loaded', U===true, U);
"""

PAIR = r"""
ok('refs + bulk-edit: exactly those features', JSON.stringify(SRETGrid.features())==='["refs","bulk-edit"]', SRETGrid.features());
SRETGrid.open(cfg());
const e=SRETGrid._engine();
const ci=e.grid.getColumns().findIndex(c=>c.id==='pred');
ok('refs + bulk-edit: refs columns get the token editor', e.grid.getColumns()[ci].editor&&e.grid.getColumns()[ci].editor.name==='RefsEditor');
e.grid.setSelectedRows([0,1]);
const b=$('[data-sg=bulk-edit]');
ok('refs + bulk-edit: Edit shows for the selection', b && !b.hidden && b.textContent==='Edit 2 rows', b&&b.textContent);
b.click();
ok('refs + bulk-edit: bulk edit uses the refs token field for a refs column', !!$('[data-sg=bulk-ctl-pred] [data-sg=refs-input]') && !!$('[data-sg=bulk-mode-pred]'));
$('[data-sg=dialog-close]').click();
ok('refs + bulk-edit: no lists, export or import controls', !$('[data-sg=temp-add]') && !$('.sg-rail') && !$('[data-sg=export]') && !$('[data-sg=import]'));
SRETGrid.close();
"""

ALL_SETUP = r"""
ok('all: every feature loaded, in load order', JSON.stringify(SRETGrid.features())===JSON.stringify(__FEATURES__), SRETGrid.features());
let m=throws(()=>SRETGrid.setup({features:['refs','charts']}),/feature not loaded: charts\. Loaded: refs, marks, bulk-edit, lists, xlsx, import\./);
ok('setup: an unknown feature fails, listing what is loaded', m===true, m);
m=throws(()=>SRETGrid.setup({layout:{pinBelow:-5}}),/layout\.pinBelow must be a positive number/);
ok('setup: a bad layout value fails', m===true, m);
m=throws(()=>SRETGrid.setup({layout:{pinWidth:5}}),/unknown layout setting pinWidth/);
ok('setup: an unknown layout setting fails', m===true, m);
const keep=window.SRETCollections; delete window.SRETCollections;
m=throws(()=>SRETGrid.setup({features:['lists']}),/the lists feature needs SRETCollections, which is not loaded/);
const kept=SRETGrid.features().length;
window.SRETCollections=keep;
ok('setup: a feature whose helper module is missing fails at setup, not on first use', m===true, m);
ok('setup: a failed setup leaves the previous one in place', kept===__FEATURES__.length, kept);

// Features left out of setup() are off.
const r1=SRETGrid.setup({features:['xlsx']});
ok('setup: returns the effective settings', JSON.stringify(r1.features)==='["xlsx"]' && r1.layout.pinBelow===1024 && r1.dates.excel==='d-mmm-yy', r1);
m=throws(()=>SRETGrid.open(cfg()),/column type "refs" needs the refs feature, which is not enabled in setup\(\)/);
ok('setup: a column type from a feature left out fails at open', m===true, m);
const noRefs=COLS.filter(c=>c.key!=='pred');
m=throws(()=>SRETGrid.open(cfg({columns:noRefs,lists:{store:SRETCollections.newStore(),refOf:x=>x}})),/lists needs the lists feature \(features\/lists\.js\), which is not enabled in setup\(\)/);
ok('setup: an option whose feature is left out fails at open', m===true, m);
SRETGrid.open(cfg({columns:noRefs}));
ok('setup: only the enabled features act (export on, bulk edit off)', SRETGrid._engine().features.join()==='xlsx' && !$('[data-sg=bulk-edit]'), SRETGrid._engine().features);
SRETGrid.close();

// Defaults, text, dates, layout, symbol class.
const host=document.createElement('div'); host.id='host2'; host.style.cssText='position:relative;width:900px;height:600px'; document.body.appendChild(host);
const r2=SRETGrid.setup({
  defaults:{host:host,pin:['id','name'],pinPhone:['id'],symbolClass:'brand-mark',editable:false},
  text:{readOnlyCell:'Locked by the source system.',noun:['part','parts']},
  dates:{format:function(v){ return v?v.slice(8,10)+'/'+v.slice(5,7)+'/'+v.slice(0,4):''; },
         parse:function(s){ const x=/^(\d\d)\/(\d\d)\/(\d{4})$/.exec(String(s).trim()); return x?x[3]+'-'+x[2]+'-'+x[1]:null; },excel:'dd/mm/yyyy'},
  layout:{pinBelow:1000,phoneBelow:600}});
ok('setup: all features on when features is not given', r2.features.length===__FEATURES__.length, r2.features);
SRETGrid.open(cfg({canEdit:function(k,f){ return f!=='finish'; },importer:{nextId:()=>'A-99'},
  columns:[COLS[0],{key:'mark',label:'Icon',type:'select',editable:true,options:['diamond'],symbols:{prefix:'ico-',stateKey:'kind'}}].concat(COLS.slice(1)),
  rows:rows().map(r=>Object.assign(r,{mark:'diamond'}))}));
ok('defaults: host from setup (screen mounts in the given element)', !!host.querySelector('.sg-screen'));
ok('defaults: pin from setup applies below layout.pinBelow (900 < 1000)', SRETGrid._engine().grid.getOptions().frozenColumn===2, SRETGrid._engine().grid.getOptions().frozenColumn);
ok('defaults: a screen option wins over the default (editable:true beats false)', !!$('[data-sg=add]'));
const cell=$$('.slick-cell').find(c=>/\d\d\/\d\d\/2026/.test(c.textContent));
ok('dates: the deployment format shows in cells', !!cell && cell.textContent==='09/10/2026', cell&&cell.textContent);
const fl=$('[data-sg-filter="finish"]'); fl.value='<01/11/2026'; fl.dispatchEvent(new Event('input',{bubbles:true}));
ok('dates: filter operators parse the deployment format', SRETGrid._engine().dataView.getLength()===1, SRETGrid._engine().dataView.getLength());
fl.value=''; fl.dispatchEvent(new Event('input',{bubbles:true}));
// Pinning follows width changes within one screen: tablet, phone, tablet, desktop.
const E=SRETGrid._engine(), frozenIds=()=>{ const f=E.grid.getOptions().frozenColumn; return f<0?'none':E.grid.getColumns().slice(0,f+1).map(c=>c.id).join(); };
const nameW0=E.grid.getColumns().find(c=>c.id==='name').width;
const seq=[]; for(const px of [500,900,1200]){ host.style.width=px+'px'; E.requestResize(); await new Promise(r=>setTimeout(r,30)); seq.push(px+':'+frozenIds()); }
ok('layout: pinPhone below phoneBelow, pin below pinBelow, none above; switching sets restores the order',
   seq.join(' | ')==='500:_checkbox_selector,id | 900:_checkbox_selector,id,name | 1200:none' &&
   E.grid.getColumns().map(c=>c.id).join()==='_checkbox_selector,id,mark,name,finish,qty,kind,pred' && E.grid.getColumns().find(c=>c.id==='name').width>=nameW0, seq);
host.style.width='900px'; E.requestResize(); await new Promise(r=>setTimeout(r,30));
const g=SRETGrid._engine().grid, fi=g.getColumns().findIndex(c=>c.id==='finish');
g.setActiveCell(0,fi); g.editActiveCell();
ok('text: readOnlyCell from setup', $('[data-sg=msg]').textContent==='Locked by the source system.', $('[data-sg=msg]').textContent);
$('[data-sg=add-more]').click();
const imp=$('[data-sg=add-more-menu] [data-sg=import]');
ok('text: noun from setup names the import', !!imp && imp.textContent.indexOf('Import parts')>=0, imp&&imp.textContent);
$('[data-sg=add-more]').click();
const sym=$('.sg-sym svg');
ok('marks: symbolClass from setup is on each symbol', !!sym && sym.getAttribute('class').split(' ')[0]==='brand-mark', sym&&sym.getAttribute('class'));
SRETGrid.close();
SRETGrid.open(cfg({text:{readOnlyCell:'This screen says no.'},canEdit:function(){ return false; },host:document.body,pin:[]}));
const g2=SRETGrid._engine().grid; g2.setActiveCell(0,2); g2.editActiveCell();
ok('text: a screen text setting wins over the deployment one', $('[data-sg=msg]').textContent==='This screen says no.', $('[data-sg=msg]').textContent);
ok('defaults: a screen host wins over the default host', !host.querySelector('.sg-screen') && !!document.body.querySelector(':scope > .sg-screen'));
SRETGrid.close();
SRETGrid.setup({});
"""


def page(features, body):
    vendor_js = (VENDOR / "slickgrid.subset.min.js").read_text(encoding="utf-8")
    vendor_css = (VENDOR / "dist" / "slick.grid.css").read_text(encoding="utf-8")
    css = [(MOD / "grid-view.css").read_text(encoding="utf-8")]
    js = [(MOD / "grid-view.js").read_text(encoding="utf-8")]
    for f in features:
        p = MOD / "features" / f"{f}.css"
        if p.exists():
            css.append(p.read_text(encoding="utf-8"))
        js.append((MOD / "features" / f"{f}.js").read_text(encoding="utf-8"))
    helpers = [(COLL / "collections.js").read_text(encoding="utf-8")] if "lists" in features else []
    harness = HARNESS.replace("__BODY__", body).replace("__FEATURES__", json.dumps(features))
    return ("<!doctype html><html data-theme=\"light\"><head><meta charset=\"utf-8\"><style>" + token_blocks() + "\n" +
            safe_inline(vendor_css, "</style", "vendor CSS") + "\n" + "\n".join(css) + "</style>"
            "<script>window.__errs=[];window.addEventListener('error',function(e){ __errs.push(String(e.message)); });</script>"
            "</head><body><script>" + safe_inline(vendor_js, "</script", "vendor JS") + "</script><script>" +
            "\n".join(helpers + js) + "</script>" + harness + "</body></html>")


PAGES = [("core only", [], CORE_ONLY), ("refs + bulk-edit", ["refs", "bulk-edit"], PAIR), ("all + setup()", FEATURES, ALL_SETUP)]


def run_page(html):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "modular.html"
        f.write_text(html, encoding="utf-8")
        proc = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--window-size=1440,900",
                               "--virtual-time-budget=8000", "--dump-dom", f.as_uri()],
                              capture_output=True, text=True, timeout=180)
    m = re.search(r'<pre id="out">(.*?)</pre>', proc.stdout, re.S)
    if not m:
        return [{"name": "page produced output", "pass": False, "detail": proc.stderr[-1500:]}]
    raw = m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")
    return json.loads(raw)["checks"]


def run_all(breaker=None):
    checks = []
    for label, feats, body in PAGES:
        html = page(feats, body)
        if breaker:
            old, new = MUTATIONS[breaker]
            n = html.count(old)
            if n == 0 and label == PAGES[-1][0]:
                sys.exit(f"Mutation {breaker}: anchor not found. Update MUTATIONS.")
            html = html.replace(old, new)
        for c in run_page(html):
            c["name"] = f"[{label}] {c['name']}"
            checks.append(c)
    return checks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prove-fails", action="store_true")
    ap.add_argument("--break", dest="breaker", choices=sorted(MUTATIONS))
    a = ap.parse_args()
    if a.prove_fails:
        missed = []
        for name in MUTATIONS:
            failed = [c["name"] for c in run_all(name) if not c["pass"]]
            print(f"-- mutation {name}: {'CAUGHT' if failed else 'MISSED'} ({len(failed)} failing checks)")
            for f in failed[:4]:
                print(f"     FAIL  {f}")
            if not failed:
                missed.append(name)
        print(f"\n{len(MUTATIONS) - len(missed)} of {len(MUTATIONS)} mutations caught.")
        return 1 if missed else 0
    checks = run_all(a.breaker)
    fails = [c for c in checks if not c["pass"]]
    print(f"== grid view modular check: {len(checks) - len(fails)} pass, {len(fails)} fail")
    for c in checks:
        line = f"  {'PASS' if c['pass'] else 'FAIL'}  {c['name']}"
        if not c["pass"] and c.get("detail") is not None:
            line += f"  :: {json.dumps(c['detail'])[:300]}"
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
