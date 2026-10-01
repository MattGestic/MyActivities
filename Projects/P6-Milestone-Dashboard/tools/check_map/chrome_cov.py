#!/usr/bin/env python3
"""Coverage-capturing stand-in for headless Chromium.

Point SRET_CHROME at this file and every check that looks Chromium up through
find_chrome() (or its own candidate list) launches this instead. For each
launch it:

  1. finds the file:// HTML argument;
  2. if the launch is --dump-dom and the page carries <script id="app-script">,
     instruments that temp file in place:
       - a first-call counter at the start of every top-level
         `function NAME(...){` of the app script;
       - a sampler script (before the app script) that records, at load, every
         1s of virtual time, at the end of the budget, and whenever the page is
         measured after a DOM change:
           * main-stylesheet rules whose selector (pseudo-classes and
             pseudo-elements stripped) matches an element, descending into
             @media only when matchMedia matches;
           * static markup regions that are rendered (getClientRects) or
             returned by a DOM lookup (getElementById / querySelector[All] /
             closest), plus <use href="#id"> targets;
           * classes and ids present in the DOM (used to place NEW CSS rules);
           * whether the page read the main sheet's cssRules (CSSOM walk).
         The result is written to <pre id="__sret_cov"> as JSON;
  3. runs the real Chromium with the original args, strips the coverage block
     and sampler script out of stdout, appends the coverage to $SRET_COV_OUT
     (one JSON line per launch), and passes stdout and the exit code through;
  4. leaves any other launch (--screenshot, --print-to-pdf, a page that is not
     the app) un-instrumented and records it as such.
"""
import html as htmlmod
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import regions  # noqa: E402

REAL_CANDIDATES = [
    "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome",
]


def real_chrome():
    env = os.environ.get("SRET_CHROME_REAL")
    if env:
        return env
    for c in REAL_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    sys.exit("chrome_cov: no real Chromium found")


SAMPLER = r"""
(function(){
try{
var W=window; if(W.__sretF) return;
var F=W.__sretF=Object.create(null);
var MK=Object.create(null), CK=Object.create(null), SC=Object.create(null), SI=Object.create(null);
var D=Document.prototype, E=Element.prototype, DF=DocumentFragment.prototype;
var oQS=D.querySelector, oQSA=D.querySelectorAll, oEQS=E.querySelector, oEQSA=E.querySelectorAll,
    oFQS=DF.querySelector, oFQSA=DF.querySelectorAll, oGEBI=D.getElementById, oCl=E.closest,
    oGCR=E.getClientRects, oGBCR=E.getBoundingClientRect, oGCS=W.getComputedStyle, oMatches=E.matches,
    oGTN=D.getElementsByTagName;
var rulesGet=Object.getOwnPropertyDescriptor(CSSStyleSheet.prototype,'cssRules').get;
var st={cssom:false,n:0,hooked:0,err:null};
var PRE=document.createElement('pre'); PRE.id='__sret_cov'; PRE.setAttribute('hidden','');
var pending=false;
function write(){ pending=false; try{ PRE.textContent=JSON.stringify({fn:Object.keys(F),css:Object.keys(CK),mk:Object.keys(MK),
  cls:Object.keys(SC),ids:Object.keys(SI),cssom:st.cssom,n:st.n,hooked:st.hooked,err:st.err,keys:KEYS}); }catch(e){} }
function sched(){ if(!pending){ pending=true; Promise.resolve().then(write); } }
W.__sretC=function(name){ F[name]=1; sched(); };
function norm(s){ return s.replace(/\s+/g,'').replace(/'/g,'"'); }
function stripPseudo(s){
  var out='', i=0, n=s.length, br=0;
  while(i<n){ var c=s[i];
    if(c==='['){ br++; out+=c; i++; continue; }
    if(c===']'){ br--; out+=c; i++; continue; }
    if(c===':' && br===0){ i++; if(s[i]===':') i++;
      while(i<n && /[A-Za-z0-9_-]/.test(s[i])) i++;
      if(s[i]==='('){ var d=0; while(i<n){ if(s[i]==='(') d++; else if(s[i]===')'){ d--; if(d===0){ i++; break; } } i++; } }
      continue; }
    out+=c; i++; }
  out=out.trim();
  if(out==='' || /[>+~]$/.test(out)) out+='*';
  return out;
}
function splitTop(s){ var parts=[], d=0, cur=''; for(var i=0;i<s.length;i++){ var c=s[i];
  if(c==='('||c==='[') d++; else if(c===')'||c===']') d--; if(c===','&&d===0){ parts.push(cur); cur=''; } else cur+=c; }
  parts.push(cur); return parts; }
// classes and ids a selector needs present somewhere in the DOM before it can match
function toks(s){ var x=s.replace(/\[[^\]]*\]/g,''); var o=[], m, re=/([.#])([A-Za-z_][\w-]*)/g;
  while((m=re.exec(x))) o.push(m[1]+m[2]); return o; }
var MAIN=null, all=oQSA.call(document,'style');
for(var i=0;i<all.length;i++){ if(!all[i].id){ MAIN=all[i]; break; } }
var RULES=[], KEYS=[];
function walk(list, ctx, conds){
  for(var i=0;i<list.length;i++){ var r=list[i];
    if(r.type===1){ var k=ctx+'|'+norm(r.selectorText); KEYS.push(k);
      RULES.push({k:k, s:splitTop(r.selectorText).map(stripPseudo).map(function(x){ return {q:x, t:toks(x)}; }), c:conds}); }
    else if(r.type===4){ walk(r.cssRules, ctx+norm('@media '+r.media.mediaText), conds.concat([{m:r.media.mediaText}])); }
    else if(r.type===12){ walk(r.cssRules, ctx+norm('@supports '+r.conditionText), conds.concat([{s:r.conditionText}])); }
  } }
if(MAIN && MAIN.sheet) walk(rulesGet.call(MAIN.sheet), '', []);
var PEND=RULES;
// static markup -> region key
var WM=new WeakMap(), ROOTS=Object.create(null);
var kids=document.body ? document.body.children : [];
function tag(el, key){ if(el.id) key='#'+el.id; WM.set(el,key); if(el.id) ROOTS[key]=el;
  for(var c=el.firstElementChild;c;c=c.nextElementSibling) tag(c,key); }
var ord=Object.create(null);
for(var j=0;j<kids.length;j++){ var el=kids[j], ln=el.localName; if(ln==='script'||ln==='style') continue;
  var key=null; if(!el.id){ ord[ln]=(ord[ln]||0); key='body>'+ln+':'+ord[ln]; ord[ln]++; ROOTS[key]=el; }
  tag(el,key); }
function markEl(el){ if(!el) return; var k=WM.get(el); if(k!==undefined && !MK[k]){ MK[k]=1; sched(); } }
function rendered(el){ try{ if(oGCR.call(el).length>0) return true;
  if(oGCS.call(W,el).display==='contents'){ for(var c=el.firstElementChild;c;c=c.nextElementSibling) if(oGCR.call(c).length>0) return true; } }catch(e){}
  return false; }
var inS=false;
var lastW=-1, lastH=-1;
function sample(force){
  if(inS) return;
  var recs=mo.takeRecords();
  for(var i=0;i<recs.length && !dirty;i++){ if(recs[i].target!==PRE && recs[i].target.parentNode!==PRE) dirty=true; }
  if(!force && !dirty && W.innerWidth===lastW && W.innerHeight===lastH) return;
  dirty=false; lastW=W.innerWidth; lastH=W.innerHeight;
  inS=true; st.n++;
  try{
    var NOW=Object.create(null), els=oGTN.call(document,'*');
    for(var e=0;e<els.length;e++){ var x=els[e]; if(x.id){ NOW['#'+x.id]=1; SI[x.id]=1; } var cl=x.classList;
      if(cl) for(var q=0;q<cl.length;q++){ NOW['.'+cl[q]]=1; SC[cl[q]]=1; } }
    function present(t){ for(var i=0;i<t.length;i++) if(!NOW[t[i]]) return false; return true; }
    var cache={};
    function ok(conds){ for(var i=0;i<conds.length;i++){ var c=conds[i], key=c.m!==undefined?'m'+c.m:'s'+c.s;
      if(!(key in cache)){ try{ cache[key]= c.m!==undefined ? W.matchMedia(c.m).matches : CSS.supports(c.s); }catch(e){ cache[key]=true; } }
      if(!cache[key]) return false; } return true; }
    var keep=[];
    for(var i=0;i<PEND.length;i++){ var r=PEND[i], hit=false;
      if(ok(r.c)){ for(var j=0;j<r.s.length && !hit;j++){ if(!present(r.s[j].t)) continue;
        try{ if(oQS.call(document,r.s[j].q)) hit=true; }catch(e){ hit=true; } } }
      if(hit) CK[r.k]=1; else keep.push(r); }
    PEND=keep;
    for(var k in ROOTS){ if(!MK[k] && rendered(ROOTS[k])) MK[k]=1; }
    var us=oGTN.call(document,'use');
    for(var u=0;u<us.length;u++){ var h=us[u].getAttribute('href')||us[u].getAttribute('xlink:href');
      if(h && h[0]==='#' && oGCR.call(us[u]).length>0){ var t=oGEBI.call(document,h.slice(1)); if(t) markEl(t); } }
  }catch(e){ st.err=String(e); }
  inS=false; write();
}
var dirty=true;
var mo=new MutationObserver(function(recs){ for(var i=0;i<recs.length;i++){ if(recs[i].target!==PRE && recs[i].target.parentNode!==PRE){ dirty=true; break; } } });
function maybe(){ if(inS) return; var n=st.n; sample(false); if(st.n!==n) st.hooked++; }
// lookups
D.getElementById=function(id){ var e=oGEBI.call(this,id); markEl(e); return e; };
function wrapQ(proto, o){ proto.querySelector=function(s){ var e=o.call(this,s); markEl(e); return e; }; }
function wrapQA(proto, o){ proto.querySelectorAll=function(s){ var l=o.call(this,s); for(var i=0;i<l.length;i++) markEl(l[i]); return l; }; }
wrapQ(D,oQS); wrapQ(E,oEQS); wrapQ(DF,oFQS); wrapQA(D,oQSA); wrapQA(E,oEQSA); wrapQA(DF,oFQSA);
E.closest=function(s){ var e=oCl.call(this,s); markEl(e); return e; };
// CSSOM reads of the main sheet
Object.defineProperty(CSSStyleSheet.prototype,'cssRules',{configurable:true,get:function(){ if(MAIN && this===MAIN.sheet && !inS) st.cssom=true; return rulesGet.call(this); }});
// measurement after a DOM change -> sample first
W.getComputedStyle=function(){ maybe(); return oGCS.apply(W,arguments); };
E.getBoundingClientRect=function(){ maybe(); return oGBCR.apply(this,arguments); };
E.getClientRects=function(){ maybe(); return oGCR.apply(this,arguments); };
[[HTMLElement.prototype,['offsetWidth','offsetHeight','offsetTop','offsetLeft','offsetParent','innerText']],
 [E,['clientWidth','clientHeight','scrollWidth','scrollHeight']]].forEach(function(p){
  p[1].forEach(function(name){ var d=Object.getOwnPropertyDescriptor(p[0],name); if(!d||!d.get) return;
    Object.defineProperty(p[0],name,{configurable:true,enumerable:d.enumerable,get:function(){ maybe(); return d.get.call(this); },set:d.set}); }); });
document.head.appendChild(PRE);
mo.observe(document.documentElement,{subtree:true,childList:true,attributes:true,characterData:true});
sample(true);
document.addEventListener('DOMContentLoaded',function(){ sample(true); });
W.addEventListener('load',function(){ sample(true); });
setInterval(function(){ sample(false); },1000);
var B=__BUDGET__; if(B>0) setTimeout(function(){ sample(true); }, Math.max(0,B-5));
}catch(e){ try{ var p=document.createElement('pre'); p.id='__sret_cov'; p.textContent=JSON.stringify({fatal:String(e)}); document.head.appendChild(p);}catch(_){} }
})();
"""

COV_RE = re.compile(r'<pre id="__sret_cov" hidden="">(.*?)</pre>', re.S)
SAMPLER_RE = re.compile(r'<script id="__sret_cov_js">.*?</script>\n?', re.S)


VERSION_RE = re.compile(r"const APP_VERSION\s*=\s*['\"]([^'\"]+)")


def current_version():
    root = os.environ.get("SRET_ROOT")
    app = pathlib.Path(root) / "src" / "milestone-dashboard.html" if root else HERE.parents[1] / "src" / "milestone-dashboard.html"
    try:
        m = VERSION_RE.search(app.read_text(encoding="utf-8"))
        return m.group(1) if m else None
    except OSError:
        return None


def page_kind(page):
    """'app' for the current app (a check's temp copy, probe injected and
    possibly mutated), 'otherapp' for another version of it (a releases/
    snapshot), 'nonapp' for anything else (the grid prototype, a harness)."""
    if '<script id="app-script">' not in page:
        return "nonapp"
    m = VERSION_RE.search(page)
    if not m:
        return "nonapp"
    cur = current_version()
    return "app" if cur is None or m.group(1) == cur else "otherapp"


def instrument(page, budget):
    """Return the instrumented page text."""
    m = re.search(r'<script id="app-script">', page)
    s0 = m.end()
    s1 = page.index("</script>", s0)
    src = page[s0:s1]
    starts, depth, tmpl = regions.js_chunk_starts(src)
    inserts = []
    for off, t in starts:
        if t != "s":
            continue
        fm = regions.FN_RE.match(src, off)
        if not fm:
            continue
        name = fm.group(1)
        p = src.find("(", fm.end() - 1)
        b = _body_brace(src, p)
        if b < 0:
            continue
        inserts.append((b + 1, '__sretF["%s"]||__sretC("%s");' % (name, name)))
    out = []
    prev = 0
    for pos, txt in inserts:
        out.append(src[prev:pos])
        out.append(txt)
        prev = pos
    out.append(src[prev:])
    sampler = SAMPLER.replace("__BUDGET__", str(int(budget)))
    return (page[:m.start()] + '<script id="__sret_cov_js">' + sampler + "</script>\n" +
            page[m.start():s0] + "".join(out) + page[s1:])


def _body_brace(src, p):
    """src[p] == '('. Skip the balanced parameter list, return the index of
    the body's opening brace."""
    if p < 0:
        return -1
    d = 0
    i = p
    n = len(src)
    q = None
    while i < n:
        c = src[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                j = src.find("{", i)
                return j
        i += 1
    return -1


def local_refs(page, base):
    """file paths the page itself loads (script src / link href / img src)."""
    out = []
    for m in re.finditer(r'<(?:script|link|img|iframe)\b[^>]*?(?:src|href)="([^"#?]+)"', page):
        ref = m.group(1)
        if re.match(r"^[a-z]+:", ref) and not ref.startswith("file:"):
            continue
        p = (base.parent / urllib.parse.unquote(ref.replace("file://", ""))).resolve()
        out.append(str(p))
    return out


def record(rec):
    out = os.environ.get("SRET_COV_OUT")
    if not out:
        return
    line = json.dumps(rec) + "\n"
    fd = os.open(out, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def main():
    args = sys.argv[1:]
    url = next((a for a in args if a.startswith("file://")), None)
    path = pathlib.Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)) if url else None
    dump = "--dump-dom" in args
    budget = 0
    for a in args:
        if a.startswith("--virtual-time-budget="):
            budget = int(a.split("=", 1)[1] or 0)
    rec = {"t": time.time(), "args": [a for a in args if a.startswith("--window-size") or a.startswith("--virtual")]}
    page = None
    if path and path.exists():
        page = path.read_text(encoding="utf-8", errors="replace")
        rec["refs"] = local_refs(page, path)
    if not dump or page is None:
        rec["launch"] = "uninstrumented"
        rec["why"] = "not --dump-dom" if not dump else "no file:// page"
        record(rec)
        os.execv(real_chrome(), [real_chrome()] + args)
    kind = page_kind(page)
    if kind != "app":
        rec["launch"] = kind
        record(rec)
        os.execv(real_chrome(), [real_chrome()] + args)
    inst = instrument(page, budget)
    path.write_text(inst, encoding="utf-8")
    proc = subprocess.run([real_chrome()] + args, stdout=subprocess.PIPE)
    out = proc.stdout.decode("utf-8", errors="surrogateescape")
    m = COV_RE.search(out)
    if m:
        try:
            cov = json.loads(htmlmod.unescape(m.group(1)))
        except ValueError as e:
            cov = {"fatal": "unparseable coverage: " + str(e)}
        out = out[:m.start()] + out[m.end():]
    else:
        cov = {"fatal": "no coverage block in dump (exit %d)" % proc.returncode}
    out = SAMPLER_RE.sub("", out, count=1)
    rec["launch"] = "app"
    rec["cov"] = cov
    record(rec)
    sys.stdout.buffer.write(out.encode("utf-8", errors="surrogateescape"))
    sys.stdout.flush()
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
