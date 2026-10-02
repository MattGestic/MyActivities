#!/usr/bin/env python3
"""P76 check: loss prevention controls (Matt, 2026-10-02, TD-242).

"Can we add a refresh lock that prevents the screen from refreshing if there
have been unsaved changes? ... a cache to store files as a backup and ...
revision control on them."

Two halves.

A. In-page, headless Chromium with --dump-dom through chrome_fixture.py (the
   test fixture seeded as every check gets it), so the coverage map sees it:
   A1 at 1440x900 and 390x844 (with the fixture):
      - pull-to-refresh lock: computed overscroll-behavior-y on html, body,
        #scroll-wrap, the Data & view scroller and #ws-panel is contain/none;
      - leave guard: a BeforeUnloadEvent is not cancelled on a clean board;
        after an edit it is cancelled and returnValue is set; Save (the real
        publishDashboard()) and the model export clear it again; an open
        milestone card with an edit in it counts as unsaved on its own;
      - the published (saved) copy carries no cache UI: the Backups list,
        status and banner message are empty and the banner is hidden;
      - layout: the Backups tab and panel (the "where" line, rows and their
        three buttons on screen, no sideways scroll) and the recovery banner
        inside the viewport;
      - P72: the heading still scrolls away and back with the board;
      - Info and About (Matt, 2026-10-02): both tabs open, Info between Help
        and About, every rail tab on screen, the headings in order, the
        wording, no em dash, the version filled in, the Save / Backups /
        import options / Help links go where they say, no sideways scroll.
   A2 IndexedDB that throws (window.indexedDB stubbed): the app boots and
      works, backups fall back to localStorage (a revision lands there after
      the debounce) and the warning shows once, not per write.
   A3 the empty app as it ships (sret:no-fixture): no recovery banner.

B. Real time, Node + Playwright (NODE_PATH=$(npm root -g)), a file:// page
   (the fixture injected by chrome_fixture.inject(), as the wrapper would) in
   a persistent profile (user-data-dir), since IndexedDB, reload and
   beforeunload need a real browser:
      - leave guard: a reload with an edit raises a `beforeunload` dialog; a
        clean reload raises none;
      - autosave: 3 edits (a remark, a user milestone, a note), then after the
        debounce the newest revision's payload holds all 3; a
        visibilitychange to hidden writes one at once; a second dashboard
        identity keeps its own revisions;
      - reload and recovery: edit, reload, Leave: the banner shows; Dismiss
        keeps the revision; reload again; Restore brings the edits back and a
        Before restore revision exists; the panel's Restore (inline confirm
        with the counts) also restores;
      - revisions: N>=3 with sequential rev; retention evicts the oldest
        unpinned (count capped, one per day kept, older than 14 days gone),
        pinned kept; Download gives a model .json that the existing mount
        reads back to the same counts in a fresh app; Delete and Clear all;
      - the empty app in a fresh profile: no banner.

    python3 tools/p76_loss_check.py [--html FILE] [--skip-playwright]
Exit 1 if any check fails.
"""
import argparse
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "check_map"))
from import_check import find_chrome  # noqa: E402
import chrome_fixture  # noqa: E402

OPT_OUT = "<!-- sret:no-fixture: P76 A3 opens the app as it ships -->"
EARLY = r"""<script>
window.__errs=[];
addEventListener('error',function(e){ if(/^ResizeObserver loop/.test(e.message||'')) return; __errs.push('error: '+e.message+' @'+e.lineno); });
(function(){ var o=console.error; console.error=function(){ __errs.push('console.error: '+Array.prototype.join.call(arguments,' ')); return o.apply(console,arguments); }; })();
</script>"""
NO_IDB = r"""<script>
// A2: IndexedDB refuses, as some file:// and private contexts do.
try{ Object.defineProperty(window,'indexedDB',{configurable:true,get:function(){ throw new Error('IndexedDB blocked (P76 A2 stub)'); }}); }catch(e){}
</script>"""

COMMON = r"""
const R={checks:[],notes:{}};
const TAG=__TAG__;
function ck(n,p,d){ R.checks.push({name:TAG+': '+n,pass:!!p,detail:d===undefined?'':String(d).slice(0,400)}); }
function emit(){ R.errs=window.__errs.slice(); const o=document.createElement('pre'); o.id='p76-out';
  o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R)))); document.body.appendChild(o); }
const settle=(ms)=>new Promise(r=>setTimeout(r,ms||250));
const $=id=>document.getElementById(id);
const rc=el=>el.getBoundingClientRect();
function bu(){ const ev=document.createEvent('BeforeUnloadEvent'); ev.initEvent('beforeunload',false,true); window.dispatchEvent(ev); return {cancelled:ev.defaultPrevented,rv:ev.returnValue}; }
function onScreen(el){ const r=rc(el); return r.width>0&&r.left>=-0.5&&r.right<=innerWidth+0.5&&r.top>=-0.5&&r.bottom<=innerHeight+0.5; }
function noSideways(){ return document.documentElement.scrollWidth<=innerWidth+1; }
// Anchor clicks (downloads) are captured, not followed.
const CAPT=[];
const _click=HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click=function(){ if(this.download){ CAPT.push({name:this.download,href:this.href}); return; } return _click.apply(this,arguments); };
async function blobText(href){ const r=await fetch(href); return r.text(); }
"""

A1 = r"""<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
try{
  const st=document.createElement('style'); st.textContent='*{transition:none!important}'; document.head.appendChild(st);
  await settle(400);
  // ---- pull-to-refresh lock ----
  const sel=['html','body','#scroll-wrap','#settings-drawer .sd-main','#ws-panel'];
  const ob=sel.map(s=>{ const el=document.querySelector(s); return s+'='+(el?getComputedStyle(el).overscrollBehaviorY:'missing'); });
  ck('pull-to-refresh lock: overscroll-behavior-y is contain or none on html, body, #scroll-wrap and the panels',
     ob.every(x=>/=(contain|none)$/.test(x)), ob.join(' '));
  // ---- leave guard ----
  ck('booted: backups started with the board', BK.booted===true, BK.booted);
  let r=bu();
  ck('leave guard: clean board, beforeunload is not cancelled', !r.cancelled&&!r.rv, JSON.stringify(r));
  ck('leave guard: the pill is off on a clean board', !$('dirty-indicator').classList.contains('show'));
  const key0=Object.keys(entryMsIndex())[0];
  addRemarkEntry(key0,'P76 leave guard remark'); noteMarkup();
  r=bu();
  ck('leave guard: after an edit, beforeunload is cancelled and returnValue is set', r.cancelled&&!!r.rv, JSON.stringify(r));
  ck('leave guard: the Unsaved changes pill shows', $('dirty-indicator').classList.contains('show'));
  // Save (publishDashboard) clears it.
  publishDashboard(); await settle(300);
  r=bu();
  ck('leave guard: Save clears it (no prompt after publishDashboard())', !r.cancelled, JSON.stringify(r));
  const pub=CAPT.filter(c=>/\.html$/.test(c.name)).pop();
  ck('save: a saved copy was produced', !!pub, CAPT.map(c=>c.name).join(','));
  if(pub){
    const html=await blobText(pub.href);
    const doc=new DOMParser().parseFromString(html,'text/html');
    const ban=doc.getElementById('bk-banner');
    ck('saved copy: the Backups list, status and clear row are empty',
       !!doc.getElementById('bk-list')&&!doc.getElementById('bk-list').innerHTML.trim()&&!doc.getElementById('bk-status').innerHTML.trim()&&!doc.getElementById('bk-clear-row').innerHTML.trim(),
       (doc.getElementById('bk-list')||{}).innerHTML);
    ck('saved copy: the recovery banner is hidden and empty', !!ban&&ban.hasAttribute('hidden')&&!doc.getElementById('bk-banner-msg').textContent.trim());
    const leak=html.match(/.{0,60}("sizeBytes":\d|data-bk-id="[^']).{0,60}/);
    ck('saved copy: no backup records or rows travel in the file', !leak, leak&&leak[0]);
  }
  // The model export clears it too.
  addRemarkEntry(key0,'P76 leave guard remark 2'); noteMarkup();
  ck('leave guard: dirty again after another edit', bu().cancelled);
  exportModel(); await settle(200);
  ck('leave guard: the model export clears it', !bu().cancelled);
  // An open card with an edit in it counts on its own.
  const wrap=document.querySelector('#tbody .m-wrap[data-ms]');
  if(wrap){ wrap.click(); await settle(400); }
  const dlg=$('ms-dialog');
  ck('card: a milestone card opened', !!dlg&&!dlg.hidden);
  ck('card: open but unedited is not unsaved', !bu().cancelled&&!hasUnsavedWork());
  const t=$('ms-title'); t.value=t.value+' P76'; t.dispatchEvent(new Event('input',{bubbles:true}));
  ck('card: an open card with an edit counts as unsaved (pill off, prompt on)',
     !DIRTY_SINCE_EXPORT&&hasUnsavedWork()&&bu().cancelled, 'dirty='+DIRTY_SINCE_EXPORT);
  ck('card: leaving commits the card the way closing it would (a backup can hold it)', DIRTY_SINCE_EXPORT&&!msDirty(), 'dirty='+DIRTY_SINCE_EXPORT+' msDirty='+msDirty());
  discardMsDialog&&discardMsDialog(); await settle(200);
  // ---- Backups panel layout ----
  setSettingsTab('backups'); toggleSettingsDrawer(true); await settle(400);
  const tab=$('sd-tab-backups'), pan=$('sd-panel-backups');
  ck('panel: the Backups tab is in the Data & view rail and selected', !!tab&&tab.classList.contains('is-active')&&tab.getAttribute('aria-selected')==='true');
  ck('panel: its section is the one shown', !!pan&&!pan.hidden&&$('sd-hd-title').textContent==='Backups', $('sd-hd-title').textContent);
  ck('panel: the plain where-and-limits line',
     ($('bk-where').textContent||'').trim()==='Stored in this browser on this device only. Clearing site data removes them. Use Save to keep a copy.', $('bk-where').textContent);
  // Rows: three fake records rendered through the real renderer. A backup
  // finishing meanwhile would re-list the real ones, so that is held off.
  await Promise.race([BK.chain,settle(9000)]); await settle(300);
  const _refresh=bkRefreshPanel; bkRefreshPanel=function(){ return Promise.resolve(); };
  const now=Date.now();
  const FAKE=[1,2,3].map(i=>({id:'test-'+i,dashKey:bkIdentity().key,place:BK.place,rev:i,savedAt:now-(3-i)*60000,label:i===2?'Before import':'Autosave',pinned:i===2,
    summary:{entries:4+i,userMs:1,notes:2,delta:{entries:1,userMs:0,notes:0,changed:true}},sizeBytes:200000+i,sig:'x'+i}));
  BK.metas=FAKE;
  bkRenderPanel();   // read at once: a list already in flight would re-render the real ones
  const rows=Array.from(document.querySelectorAll('#bk-list .bk-row'));
  ck('panel: rows render newest first', rows.length===3&&rows[0].getAttribute('data-bk-id')==='test-3'&&rows[2].getAttribute('data-bk-id')==='test-1', rows.map(x=>x.getAttribute('data-bk-id')).join(','));
  ck('panel: a row shows time, label, summary and size', /Autosave/.test(rows[0].textContent)&&/Rev 3/.test(rows[0].textContent)&&/7 entries/.test(rows[0].textContent)&&/KB/.test(rows[0].textContent), rows[0]&&rows[0].textContent);
  const btns=rows.length?Array.from(rows[0].querySelectorAll('button')):[];
  ck('panel: Restore, Download and Delete on each row, all on screen', btns.map(b=>b.textContent).join('/')==='Restore/Download/Delete'&&btns.every(onScreen), btns.map(b=>b.textContent+':'+Math.round(rc(b).right)).join(' '));
  BK.metas=FAKE; bkAskRestore('test-3');
  const conf=document.querySelector('#bk-list .bk-confirm');
  ck('panel: Restore asks inline, with the counts', !!conf&&/7 entries, 1 user milestone, 2 notes/.test(conf.textContent)&&/Before restore/.test(conf.textContent), conf?conf.textContent:(BK.metas.map(m=>m.id).join(',')+' '+BK.confirm+' '+document.getElementById('bk-list').innerHTML.slice(0,300)));
  ck('panel: the confirm is on screen', !!conf&&Array.from(conf.querySelectorAll('button')).every(onScreen));
  BK.metas=FAKE; bkCancelConfirm(); bkAskClear();
  ck('panel: Clear all backups asks inline', !!$('bk-clear-go')&&/Delete all \d+ backups? of this dashboard\? This cannot be undone\./.test($('bk-clear-row').textContent), $('bk-clear-row').textContent);
  bkCancelConfirm();
  ck('panel: no sideways scroll', noSideways(), document.documentElement.scrollWidth+' vs '+innerWidth);
  bkRefreshPanel=_refresh;
  const strings=[$('sd-panel-backups').textContent,$('bk-banner').textContent];
  ck('panel: no em dash in the UI strings', !strings.some(x=>/\u2014/.test(x)));
  toggleSettingsDrawer(false); await settle(200);
  // ---- Info and About (Matt, 2026-10-02) ----
  const heads=id=>Array.from($(id).querySelectorAll('.sd-group-title')).map(e=>e.textContent.trim());
  const railTabs=Array.from(document.querySelectorAll('#settings-drawer .sd-rail .sd-tab')).filter(b=>!b.hidden);
  setSettingsTab('info'); toggleSettingsDrawer(true); await settle(300);
  ck('rail: Info sits between Help and About', !!$('sd-tab-info')&&$('sd-tab-help').nextElementSibling===$('sd-tab-info')&&$('sd-tab-info').nextElementSibling===$('sd-tab-about'));
  ck('rail: every visible tab, Backups and Info included, is on screen', railTabs.length>=8&&railTabs.every(onScreen),
     railTabs.filter(b=>!onScreen(b)).map(b=>b.id+'@'+Math.round(rc(b).bottom)).join(' ')+' of '+innerHeight);
  ck('info: the tab opens its own section', !$('sd-panel-info').hidden&&$('sd-tab-info').classList.contains('is-active')&&$('sd-hd-title').textContent==='Info', $('sd-hd-title').textContent);
  const expInfo=['Good to know','Save your work','Backups on this device','One file, one copy','Looking after the data','What the numbers mean','Browsers and devices','Need help?'];
  ck('info: the headings, in order', JSON.stringify(heads('sd-panel-info'))===JSON.stringify(expInfo), heads('sd-panel-info').join(' | '));
  const infoTxt=$('sd-panel-info').textContent.replace(/\s+/g,' ');
  ck('info: the wording as given (spot sentences)',
     infoTxt.includes('Your changes are kept in the open page until you save. To keep them, use Save. It creates a new copy of the dashboard file with everything in it.')&&
     infoTxt.includes('Some phone browsers do not show this warning, so save regularly.')&&
     infoTxt.includes('You can restore an earlier version from Backups.')&&
     infoTxt.includes('Backups are a safety net, not a replacement for Save.')&&
     infoTxt.includes('bring updates together using the import options.')&&
     infoTxt.includes('See Help for how to get around the dashboard.'), infoTxt.slice(0,200));
  ck('info: no em dash', !/\u2014/.test($('sd-panel-info').textContent));
  ck('info: no sideways scroll, every group inside the drawer', noSideways()&&Array.from($('sd-panel-info').querySelectorAll('.sd-group')).every(g=>rc(g).right<=innerWidth+0.5));
  const link=t=>Array.from($('sd-panel-info').querySelectorAll('.sd-inline-link')).find(b=>b.textContent===t);
  ck('info: Save, Backups, import options and Help are links', ['Save','Backups','import options','Help'].every(t=>!!link(t)));
  link('Backups').click(); await settle(200);
  ck('info: Backups link opens Backups', SETTINGS_TAB==='backups'&&!$('sd-panel-backups').hidden, SETTINGS_TAB);
  setSettingsTab('info'); link('Help').click(); await settle(100);
  ck('info: Help link opens Help', SETTINGS_TAB==='help'&&!$('sd-panel-help').hidden, SETTINGS_TAB);
  setSettingsTab('info'); link('import options').click(); await settle(100);
  ck('info: import options link opens Import', SETTINGS_TAB==='import', SETTINGS_TAB);
  setSettingsTab('info'); const nCapt=CAPT.length; link('Save').click(); await settle(300);
  ck('info: Save link is the Save action (a saved copy is produced)', CAPT.length===nCapt+1&&/\.html$/.test(CAPT[CAPT.length-1].name), CAPT.slice(nCapt).map(c=>c.name).join(','));
  setSettingsTab('backups'); await settle(100);
  const bkSave=$('bk-where').querySelector('.sd-inline-link');
  ck('backups: its Save is the Save action too', !!bkSave&&/publishDashboard\(\)/.test(bkSave.getAttribute('onclick')||''));
  setSettingsTab('about'); await settle(200);
  ck('about: the tab opens its own section', !$('sd-panel-about').hidden&&$('sd-hd-title').textContent==='About');
  ck('about: the headings, in order', JSON.stringify(heads('sd-panel-about'))===JSON.stringify(['Milestone Dashboard','What it is','What you can use it for','Why it is built this way']), heads('sd-panel-about').join(' | '));
  ck('about: Version is filled from APP_VERSION', $('about-version').textContent===APP_VERSION&&/Version 3\.\d+\.\d+-P\d+/.test($('sd-panel-about').textContent.replace(/\s+/g,' ')), $('about-version').textContent);
  const aboutTxt=$('sd-panel-about').textContent.replace(/\s+/g,' ');
  ck('about: the five reasons', ['One file, nothing to install.','Works offline.','Your data stays with you.','Easy to share.','Safe for your schedule.'].every(t=>aboutTxt.includes(t))&&
     aboutTxt.includes('No installation, no admin rights, no IT request.'), aboutTxt.slice(0,160));
  const uses=Array.from(document.querySelectorAll('#about-uses > li')).map(li=>li.textContent.trim());
  ck('about: What you can use it for has its five items', uses.length===5&&
     ['Progress updates.','Schedule reviews.','One-page snapshot.','Key milestones.','Your own tasks.'].every((h,i)=>uses[i].indexOf(h)===0)&&
     uses[1]==="Schedule reviews. Check the logic: see each milestone's predecessors and successors and follow the links across the timeline.", uses.join(' | ').slice(0,300));
  ck('about: no em dash', !/\u2014/.test($('sd-panel-about').textContent));
  ck('about: no sideways scroll, every group inside the drawer', noSideways()&&Array.from($('sd-panel-about').querySelectorAll('.sd-group')).every(g=>rc(g).right<=innerWidth+0.5));
  ck('about: the tool-name footer is still there', !!$('sd-foot')&&/Schedule Reporting and Evaluation Tool/.test($('sd-foot').textContent));
  toggleSettingsDrawer(false); await settle(200);
  // ---- banner layout ----
  bkShowBanner(FAKE[2]); await settle(100);
  const ban=$('bk-banner');
  ck('banner: shows the time and the count of updates', !ban.hidden&&/^Unsaved work from \d\d:\d\d found/.test($('bk-banner-msg').textContent), $('bk-banner-msg').textContent);
  ck('banner: inside the viewport, its three buttons on screen', onScreen(ban)&&Array.from(ban.querySelectorAll('button')).every(onScreen)&&
     Array.from(ban.querySelectorAll('button')).map(b=>b.textContent).join('/')==='Restore/Dismiss/View backups',
     JSON.stringify(rc(ban)));
  ck('banner: non-blocking (the board under it still takes a click)', getComputedStyle(ban).position==='fixed'&&document.activeElement!==ban);
  bkBannerDismiss();
  ck('banner: Dismiss hides it', ban.hidden);
  // ---- P72 scroll-away still works (phones) ----
  if(innerWidth<1024&&typeof chromeAwayEligible==='function'&&chromeAwayEligible()){
    const sw=$('scroll-wrap');
    for(let y=0;y<=600;y+=60){ sw.scrollTop=y; sw.dispatchEvent(new Event('scroll')); await settle(30); }
    await settle(400);
    const away=document.documentElement.classList.contains('chrome-away');
    for(let y=600;y>=0;y-=60){ sw.scrollTop=y; sw.dispatchEvent(new Event('scroll')); await settle(30); }
    await settle(400);
    ck('P72: the heading still scrolls away with the board and comes back', away&&!document.documentElement.classList.contains('chrome-away'), 'away='+away);
  }
}catch(e){ ck('probe ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""

A2 = r"""<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
try{
  let toasts=[];
  const _st=showToast; showToast=function(t,o){ toasts.push(String(t)); return _st(t,o); };
  await settle(500);
  ck('no IndexedDB: the app booted and backups started', BK.booted===true);
  ck('no IndexedDB: backups fell back to localStorage', BK.kind==='ls', BK.kind);
  const key0=Object.keys(entryMsIndex())[0];
  addRemarkEntry(key0,'P76 fallback remark'); noteMarkup(); scheduleRerender(true);
  await settle(2600);
  let idx=[]; try{ idx=JSON.parse(localStorage.getItem('sret-bk-index')||'[]'); }catch(e){}
  ck('no IndexedDB: an autosave landed in localStorage after the debounce', idx.length===1&&idx[0].label==='Autosave'&&idx[0].rev===1, JSON.stringify(idx.map(m=>[m.rev,m.label])));
  const pay=idx.length?localStorage.getItem('sret-bk-p:'+idx[0].id):'';
  ck('no IndexedDB: its payload holds the edit', /P76 fallback remark/.test(pay||''), (pay||'').length);
  addRemarkEntry(key0,'P76 fallback remark 2'); noteMarkup();
  await settle(2600);
  try{ idx=JSON.parse(localStorage.getItem('sret-bk-index')||'[]'); }catch(e){}
  ck('no IndexedDB: a second revision, rev 2', idx.length===2&&idx[1].rev===2, idx.length);
  const warned=toasts.filter(t=>/Backups/.test(t)||/IndexedDB/.test(t));
  // The warning was raised at boot, before this probe wrapped showToast: it is
  // on BK.note and BK.warned, and no write since has raised it again.
  ck('no IndexedDB: warned once (at boot), not again per write', BK.warned===true&&/IndexedDB is unavailable/.test(BK.note)&&warned.length===0, BK.note+' / '+warned.join('|'));
  setSettingsTab('backups'); toggleSettingsDrawer(true); await settle(300);
  ck('no IndexedDB: the panel lists them and says where they are', document.querySelectorAll('#bk-list .bk-row').length===2&&/localStorage/.test($('bk-status').textContent), $('bk-status').textContent);
  toggleSettingsDrawer(false);
  rerender(true);
  ck('no IndexedDB: the board still rebuilds', document.querySelectorAll('#tbody tr').length>10);
}catch(e){ ck('probe ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""

A3 = OPT_OUT + r"""
<script>
addEventListener('load',function(){ setTimeout(async function(){
""" + COMMON + r"""
try{
  await settle(6000);
  ck('empty app: booted', BK.booted===true&&isDashboardEmpty());
  ck('empty app: no recovery banner', $('bk-banner').hidden);
  ck('empty app: not unsaved', !bu().cancelled);
}catch(e){ ck('probe ran without throwing', false, e.stack||e); }
emit();
},600); });
</script>"""


def page_with(html, probe, early=""):
    page = html.replace("<head>", "<head>" + EARLY + early, 1)
    i = page.rindex("</body>")
    return page[:i] + probe + "\n" + page[i:]


def run_dump(page, size):
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p76.html"
        f.write_text(page, encoding="utf-8")
        p = subprocess.run([find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                            f"--user-data-dir={td}/prof", f"--window-size={size[0]},{size[1]}",
                            "--virtual-time-budget=60000", "--dump-dom", f.as_uri()],
                           capture_output=True, text=True, timeout=300)
    m = re.search(r'<pre id="p76-out">(.*?)</pre>', p.stdout, re.S)
    if not m:
        return {"checks": [{"name": "probe output found", "pass": False, "detail": p.stderr[-800:]}], "errs": []}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def collect(res, tag):
    out = list(res["checks"])
    errs = res.get("errs") or []
    out.append({"name": tag + ": no page errors", "pass": not errs, "detail": " | ".join(errs)[:400]})
    return out


# ---------------------------------------------------------------------------
# B: Playwright
# ---------------------------------------------------------------------------
PW = r"""
const { createRequire } = require('module');
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const CFG = JSON.parse(process.argv[2]);
const checks = [];
const ck = (n, p, d) => checks.push({ name: 'B: ' + n, pass: !!p, detail: d === undefined ? '' : String(d).slice(0, 400) });
const sleep = ms => new Promise(r => setTimeout(r, ms));

let STAGE = '';
const stage = s => { STAGE = s; process.stderr.write('[p76] ' + s + '\n'); };
const chainDone = page => page.evaluate(() => Promise.race([BK.chain, new Promise(r => setTimeout(r, 8000))]));
async function boot(page) {
  await page.waitForFunction(() => window.BK && BK.booted && BK.kind, null, { timeout: 30000 });
  await chainDone(page);
  await sleep(150);
}
const revs = page => page.evaluate(() => BK_STORE.list().then(a => a.sort((x, y) => x.rev - y.rev)));
const mine = page => page.evaluate(() => BK_STORE.list().then(a => bkRelevant(a).sort((x, y) => x.rev - y.rev)));

(async () => {
  // ---------- persistent profile, file:// page with the fixture ----------
  let ctx = await chromium.launchPersistentContext(CFG.prof, { headless: true, viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  let page = ctx.pages()[0] || await ctx.newPage();
  page.setDefaultTimeout(20000);
  const errs = [];
  const watch = p => { p.on('pageerror', e => errs.push(String(e))); };
  watch(page);
  const dialogs = [];
  const onDialog = async d => { dialogs.push(d.type()); await d.accept(); };
  page.on('dialog', onDialog);
  await page.goto(CFG.url);
  await boot(page);
  ck('IndexedDB opens on a file:// page', (await page.evaluate(() => BK.kind)) === 'idb', await page.evaluate(() => BK.kind));
  ck('fresh profile: no banner', await page.evaluate(() => document.getElementById('bk-banner').hidden));
  ck('fresh profile: no backups yet', (await revs(page)).length === 0);

  // ---- clean reload: no prompt ----
  stage('clean reload');
  await page.click('.rpt-hd', { position: { x: 3, y: 3 } });
  await page.reload(); await boot(page);
  ck('leave guard: a clean reload raises no beforeunload dialog', dialogs.length === 0, dialogs.join(','));

  // ---- three edits -> autosave ----
  stage('three edits');
  const ids = await page.evaluate(() => {
    const k = Object.keys(entryMsIndex())[0];
    addRemarkEntry(k, 'P76 edit one remark'); noteMarkup();
    const r = addUserMilestone({ name: 'P76 user milestone', date: isoDay(WE_DATES[Math.min(WE_DATES.length - 1, NOW_COL + 2)]), type: 'MS', state: 'FUTURE' });
    noteMarkup(); scheduleRerender(true);
    document.getElementById('note-input').value = 'P76 note three'; saveNewNote();
    return { key: k, um: r.id };
  });
  await sleep(500);
  ck('autosave: nothing written inside the debounce', (await revs(page)).length === 0);
  await sleep(2600);
  let list = await revs(page);
  const top = list[list.length - 1];
  const topJson = top ? await page.evaluate(id => BK_STORE.get(id), top.id) : '';
  ck('autosave: a revision after the debounce, with all 3 edits in its payload',
     !!top && /P76 edit one remark/.test(topJson) && topJson.includes(ids.um) && /P76 note three/.test(topJson),
     list.map(m => m.rev + ':' + m.label).join(','));
  ck('autosave: the record carries rev, savedAt, appVersion, label, summary and size',
     !!top && top.rev >= 1 && top.savedAt > 0 && top.appVersion === CFG.version && top.label === 'Autosave' && top.summary && top.summary.userMs >= 1 && top.summary.notes >= 1 && top.sizeBytes === topJson.length,
     JSON.stringify(top && { rev: top.rev, appVersion: top.appVersion, label: top.label, summary: top.summary, size: top.sizeBytes }));

  // ---- visibilitychange writes at once ----
  stage('visibility');
  const before = list.length;
  await page.evaluate(() => {
    addRemarkEntry(Object.keys(entryMsIndex())[1], 'P76 edit four before hide'); noteMarkup();
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
    document.dispatchEvent(new Event('visibilitychange'));
  });
  await sleep(400);
  list = await revs(page);
  const vj = list.length > before ? await page.evaluate(id => BK_STORE.get(id), list[list.length - 1].id) : '';
  ck('visibilitychange to hidden writes a revision at once (inside the 2s debounce)', list.length === before + 1 && /P76 edit four before hide/.test(vj), before + ' -> ' + list.length);
  await page.evaluate(() => { delete document.visibilityState; });

  // ---- reload with unsaved work: prompt, Leave, banner ----
  stage('dirty reload');
  dialogs.length = 0;
  await page.evaluate(() => { addRemarkEntry(Object.keys(entryMsIndex())[2], 'P76 edit five, last before reload'); noteMarkup(); });
  await page.click('.rpt-hd', { position: { x: 3, y: 3 } });
  await page.reload(); await boot(page);
  ck('leave guard: a reload with unsaved work raises a beforeunload dialog', dialogs.includes('beforeunload'), dialogs.join(','));
  await sleep(300);
  let ban = await page.evaluate(() => ({ hidden: document.getElementById('bk-banner').hidden, msg: document.getElementById('bk-banner-msg').textContent }));
  ck('recovery: after Leave the banner offers the unsaved work', !ban.hidden && /^Unsaved work from \d\d:\d\d found \(\d+ updates?\)\.$/.test(ban.msg), JSON.stringify(ban));
  list = await revs(page);
  const lastJ = await page.evaluate(id => BK_STORE.get(id), list[list.length - 1].id);
  ck('recovery: the edit made just before the reload was kept (Leave lost nothing)', /P76 edit five, last before reload/.test(lastJ), list.length);
  ck('recovery: the board itself opened as the file has it', await page.evaluate(() => !ENTRIES.some(e => /P76/.test(e.text || '')) && !USER_MILESTONES.length));
  const nBefore = list.length;
  await page.click('#bk-banner-dismiss');
  ck('recovery: Dismiss hides the banner', await page.evaluate(() => document.getElementById('bk-banner').hidden));
  ck('recovery: Dismiss keeps the revision', (await revs(page)).length === nBefore);

  // ---- reload again, Restore from the banner ----
  stage('banner restore');
  dialogs.length = 0;
  await page.reload(); await boot(page);
  ck('leave guard: no prompt when nothing changed since opening', dialogs.length === 0, dialogs.join(','));
  ban = await page.evaluate(() => ({ hidden: document.getElementById('bk-banner').hidden, msg: document.getElementById('bk-banner-msg').textContent }));
  ck('recovery: the banner is back on the next open (Dismiss is for this visit)', !ban.hidden, JSON.stringify(ban));
  await page.click('#bk-banner-restore');
  await page.waitForFunction(() => document.getElementById('bk-banner').hidden && ENTRIES.some(e => /P76 edit five/.test(e.text || '')), null, { timeout: 15000 }).catch(() => {});
  await chainDone(page);
  const st = await page.evaluate(um => ({
    remark: ENTRIES.some(e => /P76 edit one remark/.test(e.text || '')),
    five: ENTRIES.some(e => /P76 edit five/.test(e.text || '')),
    um: USER_MILESTONES.some(m => m.id === um) && !!document.querySelector('#tbody .m-wrap[data-ms="' + um + '"]'),
    note: NOTES.some(n => /P76 note three/.test(n.text || '')),
    pill: document.getElementById('dirty-indicator').classList.contains('show'),
    banner: document.getElementById('bk-banner').hidden
  }), ids.um);
  ck('restore (banner): the edits are back on the board (remark, user milestone drawn, note)', st.remark && st.five && st.um && st.note, JSON.stringify(st));
  ck('restore (banner): restored work shows as unsaved, the banner goes', st.pill && st.banner, JSON.stringify(st));
  list = await revs(page);
  ck('restore: a Before restore revision was taken first, pinned', list.some(m => m.label === 'Before restore' && m.pinned), list.map(m => m.rev + ':' + m.label).join(','));
  // ---- sequential revs ----
  const revNums = list.map(m => m.rev);
  ck('revisions: N>=3, numbered 1..N in order', revNums.length >= 3 && revNums.every((r, i) => r === i + 1), revNums.join(','));

  // ---- the panel's Restore: inline confirm with counts ----
  stage('panel restore');
  await page.evaluate(() => { setSettingsTab('backups'); toggleSettingsDrawer(true); });
  await sleep(400);
  const first = list[0];
  await page.click('#bk-list [data-bk-id="' + first.id + '"] .bk-restore');
  const conf = await page.textContent('#bk-list .bk-confirm');
  ck('restore (panel): asks inline with the counts', /Restore rev 1 from/.test(conf) && /\d+ entr(y|ies), \d+ user milestones?, \d+ notes?/.test(conf), conf);
  await page.click('#bk-list .bk-restore-go');
  await sleep(800); await chainDone(page);
  const st2 = await page.evaluate(() => ({ five: ENTRIES.some(e => /P76 edit five/.test(e.text || '')), one: ENTRIES.some(e => /P76 edit one remark/.test(e.text || '')) }));
  ck('restore (panel): the board is rev 1 again (its edits, not the later ones)', st2.one && !st2.five, JSON.stringify(st2));
  list = await revs(page);
  ck('restore (panel): another Before restore revision', list.filter(m => m.label === 'Before restore').length === 2, list.map(m => m.rev + ':' + m.label).join(','));

  // ---- Download -> model .json -> mount in a fresh app ----
  stage('download');
  const dlRev = list.find(m => m.label === 'Before restore' && m.rev === list.filter(x => x.label === 'Before restore').slice(-1)[0].rev);
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#bk-list [data-bk-id="' + dlRev.id + '"] .bk-download')]);
  const dlPath = path.join(CFG.tmp, dl.suggestedFilename());
  await dl.saveAs(dlPath);
  const dlText = fs.readFileSync(dlPath, 'utf8');
  const v = await page.evaluate(t => { const r = validateModelPayload(t, 'x.json'); return { ok: r.ok, errors: r.errors, e: (r.payload.entries || []).length, u: (r.payload.userMilestones || []).length, n: (r.payload.notes || []).length }; }, dlText);
  ck('download: a model .json the mount validates', v.ok && /^milestone-dashboard_model_backup-r\d+_\d{8}-\d{4}\.json$/.test(dl.suggestedFilename()), dl.suggestedFilename() + ' ' + JSON.stringify(v.errors));
  ck('download: its counts are the revision\'s', v.e === dlRev.summary.entries && v.u === dlRev.summary.userMs && v.n === dlRev.summary.notes, JSON.stringify(v) + ' vs ' + JSON.stringify(dlRev.summary));
  const ctx2 = await chromium.launch({ headless: true });
  const p2 = await ctx2.newPage(); watch(p2);
  await p2.goto(CFG.url); await boot(p2);
  await p2.setInputFiles('#annot-file', dlPath);
  await p2.waitForFunction(() => !document.getElementById('annot-dialog').hidden, null, { timeout: 10000 });
  await p2.evaluate(() => { annotSelectAll(); applyAnnotSelection(); });
  await sleep(500);
  const back = await p2.evaluate(() => ({ e: ENTRIES.length, u: USER_MILESTONES.length, n: NOTES.length }));
  ck('download: imports back through the existing mount to the same counts', back.e === v.e && back.u === v.u && back.n === v.n, JSON.stringify(back) + ' vs ' + JSON.stringify(v));
  await ctx2.close();

  // ---- a second dashboard identity stays separate ----
  stage('identity');
  const keyA = await page.evaluate(() => bkIdentity().key);
  const aRevs = (await revs(page)).filter(m => m.dashKey === keyA).length;
  await page.evaluate(() => { setProjectNo('P76-OTHER', false); addRemarkEntry(Object.keys(entryMsIndex())[3], 'P76 other dashboard'); noteMarkup(); });
  await sleep(2600);
  const keyB = await page.evaluate(() => bkIdentity().key);
  list = await revs(page);
  const bList = list.filter(m => m.dashKey === keyB);
  ck('identity: a different dashboard gets its own key and its own rev 1', keyA !== keyB && bList.length === 1 && bList[0].rev === 1, keyA + ' / ' + keyB + ' ' + bList.map(m => m.rev).join(','));
  ck('identity: the first dashboard\'s revisions are untouched', list.filter(m => m.dashKey === keyA).length === aRevs, aRevs);
  await page.evaluate(() => { setProjectNo(BK.bootDash.key.split('|')[0].slice(2), false); });
  await sleep(2600);

  // ---- retention ----
  stage('retention');
  const ret = await page.evaluate(async () => {
    const key = bkIdentity().key;
    const all0 = (await BK_STORE.list()).filter(m => m.dashKey === key);
    await bkSaveNow('Autosave', { force: true, savedAt: Date.now() - 20 * 864e5 });
    await bkSaveNow('Autosave', { force: true, savedAt: Date.now() - 2 * 864e5 - 60e3 });
    await bkSaveNow('Autosave', { force: true, savedAt: Date.now() - 2 * 864e5 });
    const old = (await BK_STORE.list()).filter(m => m.dashKey === key).sort((a, b) => b.rev - a.rev).slice(0, 3).map(m => m.id).reverse();
    for (let i = 0; i < 24; i++) await bkSaveNow('Autosave', { force: true });
    await bkSaveNow('Before import', { force: true });
    const after = (await BK_STORE.list()).filter(m => m.dashKey === key).sort((a, b) => a.rev - b.rev);
    const autos = after.filter(m => !m.pinned), pins = after.filter(m => m.pinned);
    return { pinsBefore: all0.filter(m => m.pinned).map(m => m.id), pinsAfter: pins.map(m => m.id), autos: autos.length,
             old, kept: after.map(m => m.id), oldestAutoRev: autos.length ? autos[0].rev : null, maxRev: after[after.length - 1].rev };
  });
  const keptOld = ret.old.map(id => ret.kept.includes(id));
  ck('retention: newest 20 autosaves kept, plus one a day: the older autosaves are evicted', ret.autos === 21, JSON.stringify(ret).slice(0, 300));
  ck('retention: the day-old ones keep only the newest of that day; 20 days old is gone', JSON.stringify(keptOld) === '[false,false,true]', JSON.stringify(keptOld));
  ck('retention: every pinned (labelled) revision is kept', ret.pinsBefore.every(id => ret.pinsAfter.includes(id)) && ret.pinsAfter.length === ret.pinsBefore.length + 1, ret.pinsBefore.length + ' -> ' + ret.pinsAfter.length);
  const plan = await page.evaluate(() => {
    const now = Date.now(), m = [];
    for (let i = 1; i <= 30; i++) m.push({ id: 'a' + i, dashKey: 'k', rev: i, savedAt: now - (30 - i) * 1000, pinned: false, sizeBytes: 10 });
    for (let i = 1; i <= 12; i++) m.push({ id: 'p' + i, dashKey: 'k', rev: 30 + i, savedAt: now - 500 + i, pinned: true, sizeBytes: 10 });
    const ev = bkPlanEvictions(m, now, 0);
    const evB = bkPlanEvictions(m.filter(x => !ev.includes(x.id)), now, 25 * 10);
    return { ev: ev.sort(), evB };
  });
  const expEv = ['a1','a2','a3','a4','a5','a6','a7','a8','a9','a10','p1','p2'].sort();
  ck('retention plan: count cap evicts the oldest unpinned; pinned cap the oldest pinned', JSON.stringify(plan.ev) === JSON.stringify(expEv), plan.ev.join(','));
  ck('retention plan: over the size budget, unpinned go before any pinned, oldest first', plan.evB.length === 5 && plan.evB.every(id => /^a/.test(id)) && plan.evB[0] === 'a11', plan.evB.join(','));

  // ---- Delete, Clear all ----
  stage('delete');
  await page.evaluate(() => { setSettingsTab('backups'); toggleSettingsDrawer(true); });
  await sleep(400);
  const n0 = (await mine(page)).length;
  const victim = (await mine(page))[0];
  await page.click('#bk-list [data-bk-id="' + victim.id + '"] .bk-delete');
  await sleep(400); await chainDone(page);
  const afterDel = await mine(page);
  ck('delete: removes that revision, only that one', afterDel.length === n0 - 1 && !afterDel.some(m => m.id === victim.id), n0 + ' -> ' + afterDel.length);
  ck('delete: the panel lists one row less', (await page.$$('#bk-list .bk-row')).length === n0 - 1);
  await page.click('#btn-bk-clear');
  ck('clear all: asks inline first', /Delete all \d+ backups? of this dashboard/.test(await page.textContent('#bk-clear-row')) && (await mine(page)).length === n0 - 1);
  await page.click('#bk-clear-go');
  await sleep(400); await chainDone(page);
  ck('clear all: no backups left for this dashboard', (await mine(page)).length === 0 && /No backups yet/.test(await page.textContent('#bk-list')));
  ck('no page errors (persistent profile)', errs.length === 0, errs.join(' | '));
  page.off('dialog', onDialog);
  await ctx.close();

  // ---------- the empty app, fresh profile ----------
  stage('empty app');
  const ctx3 = await chromium.launchPersistentContext(CFG.prof2, { headless: true, viewport: { width: 390, height: 844 } });
  const p3 = ctx3.pages()[0] || await ctx3.newPage();
  const e3 = []; p3.on('pageerror', e => e3.push(String(e)));
  await p3.goto(CFG.emptyUrl); await boot(p3); await sleep(500);
  ck('empty app: no banner, no backups', await p3.evaluate(() => isDashboardEmpty() && document.getElementById('bk-banner').hidden) && (await revs(p3)).length === 0);
  // Matt's case: an empty copy, work done in it that changes the dashboard's
  // identity (a project number, a milestone), the tab killed; the same copy
  // reopens empty, under the empty identity, and still offers the work.
  stage('empty app, identity changed');
  await p3.evaluate(() => {
    setProjectNo('P76-EMPTY', false);
    const d = new Date(); d.setDate(d.getDate() + 14);
    addUserMilestone({ name: 'P76 empty-copy milestone', date: isoDay(d), type: 'MS', state: 'FUTURE' });
    noteMarkup(); scheduleRerender(true);
  });
  await sleep(2700);
  const keyNow = await p3.evaluate(() => bkIdentity().key);
  ck('empty app: the work is backed up under the new identity', /^p:P76-EMPTY/.test(keyNow) && (await revs(p3)).some(m => m.dashKey === keyNow), keyNow);
  await p3.reload(); await boot(p3); await sleep(300);
  const b3 = await p3.evaluate(() => ({ empty: isDashboardEmpty(), key: bkIdentity().key, hidden: document.getElementById('bk-banner').hidden, msg: document.getElementById('bk-banner-msg').textContent }));
  ck('empty app: reopened empty, the banner still finds the work made in this file', b3.empty && /^t:/.test(b3.key) && !b3.hidden, JSON.stringify(b3));
  await p3.click('#bk-banner-restore');
  await p3.waitForFunction(() => USER_MILESTONES.some(m => m.actName === 'P76 empty-copy milestone'), null, { timeout: 10000 }).catch(() => {});
  ck('empty app: Restore brings the milestone and the project number back', await p3.evaluate(() => USER_MILESTONES.some(m => m.actName === 'P76 empty-copy milestone') && REPORT_META.projectNo === 'P76-EMPTY' && !isDashboardEmpty()));
  ck('empty app: no page errors', e3.length === 0, e3.join(' | '));
  await ctx3.close();
  console.log('P76JSON' + JSON.stringify(checks));
})().catch(e => { console.log('P76JSON' + JSON.stringify(checks.concat([{ name: 'B: script ran without throwing (stage: ' + STAGE + ')', pass: false, detail: String(e && e.stack || e).slice(0, 600) }]))); });
"""


def run_playwright(html):
    td = tempfile.mkdtemp(prefix="p76-pw-")
    try:
        app = pathlib.Path(td) / "Milestone_Dashboard_p76.html"
        app.write_text(chrome_fixture.inject(html.replace("<head>", "<head>" + EARLY, 1)), encoding="utf-8")
        empty = pathlib.Path(td) / "Milestone_Dashboard_empty_p76.html"
        empty.write_text(html, encoding="utf-8")
        script = pathlib.Path(td) / "p76_pw.js"
        script.write_text(PW, encoding="utf-8")
        version = re.search(r"const APP_VERSION='([^']+)'", html).group(1)
        cfg = {"url": app.as_uri(), "emptyUrl": empty.as_uri(), "prof": str(pathlib.Path(td) / "prof"),
               "prof2": str(pathlib.Path(td) / "prof2"), "tmp": td, "version": version}
        env = dict(os.environ)
        try:
            env["NODE_PATH"] = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
        except OSError:
            pass
        p = subprocess.run(["node", str(script), json.dumps(cfg)], stdout=subprocess.PIPE,
                           stderr=None if os.environ.get("P76_DEBUG") else subprocess.PIPE, text=True, timeout=600, env=env)
        m = re.search(r"P76JSON(.*)", p.stdout)
        if not m:
            return [{"name": "B: Playwright output found", "pass": False, "detail": (p.stdout + (p.stderr or ""))[-800:]}]
        return json.loads(m.group(1))
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(ROOT / "src" / "milestone-dashboard.html"))
    ap.add_argument("--skip-playwright", action="store_true")
    ap.add_argument("--only-playwright", action="store_true")
    a = ap.parse_args()
    html = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks = []
    for size in ([] if a.only_playwright else [(1440, 900), (390, 844)]):
        tag = f"A1 {size[0]}"
        checks += collect(run_dump(page_with(html, A1.replace("__TAG__", json.dumps(tag))), size), tag)
    if not a.only_playwright:
        checks += collect(run_dump(page_with(html, A2.replace("__TAG__", json.dumps("A2 no IndexedDB")), NO_IDB), (1440, 900)), "A2 no IndexedDB")
        res = run_dump(page_with(html, A3.replace("__TAG__", json.dumps("A3 empty"))), (390, 844))
        checks += collect(res, "A3 empty")
    if not a.skip_playwright:
        checks += run_playwright(html)
    fails = 0
    for c in checks:
        fails += not c["pass"]
        print(("PASS " if c["pass"] else "FAIL ") + c["name"] + ("" if c["pass"] or not c["detail"] else "  [" + c["detail"] + "]"))
    print(f"{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
