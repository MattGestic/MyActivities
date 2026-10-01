#!/usr/bin/env python3
"""
P62 check: Workspace > Comments & markups, one row per annotation type with a
View control that opens that type as an editable table (E-02).

Runs the real app in headless Chromium with the host resolver pointed at
nothing, and reads DOM, classList, elementFromPoint and store contents, never
a screenshot. One page load (tables) plus a source pass:

  tables  "No edits yet" and no View control on a fresh load. Entries made
          through the real paths: three milestone comments, one health
          override, one progress override and three field edits (title,
          finish, weight) through the milestone card; two notes through the
          composer; a row health change and a row remark on the board; a
          dependency comment through the comment panel. The rows are exactly
          the non-zero types, each with its ANNOT_CATEGORIES label, its count
          and a View button; short titles (zero) are hidden; user milestones
          are never a row. For each type: View opens the grid with the right
          title "<label> (<n>)" and row count, the icon bar and header stay
          the element at their centre; one edit lands in that store and in no
          other store, and TASKS, MILESTONES and USER_MILESTONES are
          untouched; an invalid value (progress 150, 101, -1; an unknown
          health code or note status; an unreadable date or weight) is
          refused and changes nothing; clearing removes the entry and the row
          count drops; Delete selected removes entries. Double-click on an ID
          opens the milestone card, on a note number the Notes pane at that
          note. Export .xlsx writes the table's rows (XLSX.writeFile
          captured). Back returns focus to that type's View button and the
          board shows the edit (the marker's health class, the row remark,
          the row health dot).

Source assertions: the four tag counts are 1; the version grep returns 1 and
APP_VERSION is 3.1.0-P62 or later; no script start tag inside a script; no CDN URL.

Usage:
  python3 tools/p62_check.py [--html FILE]
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_HTML = ROOT / "src" / "milestone-dashboard.html"
OUT_RE = re.compile(r'<pre id="p62-out">(.*?)</pre>', re.S)

PROBE = r"""
(function(){
  try{ localStorage.clear(); }catch(e){}
  document.head.insertAdjacentHTML('beforeend','<style>*,*::before,*::after{transition:none!important;animation:none!important}</style>');
  const R={checks:[]};
  function ck(n,p,d){ R.checks.push({name:'[tables] '+n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p62-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  const $=id=>document.getElementById(id);
  const rc=el=>el.getBoundingClientRect();
  const hitIn=(el,sel)=>{ const r=rc(el); const at=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
                          return !!at&&!!at.closest(sel); };
  const ye=()=>{ const o={}; document.querySelectorAll('#ws-your-edits .ye-item').forEach(function(s){ o[s.getAttribute('data-cat')]=+s.getAttribute('data-n'); }); return o; };
  const WRITES=[];
  function stubWrite(){ if(typeof XLSX!=='undefined') XLSX.writeFile=function(wb,name){ WRITES.push({wb:wb,name:name}); }; }
  function sheetRows(wb,name){ return XLSX.utils.sheet_to_json(wb.Sheets[name],{header:1,raw:false,defval:''}); }
  // Every annotation store plus the schedule data, so an edit can be shown to
  // land in one place and nowhere else.
  const snap=()=>({comments:JSON.stringify(MS_COMMENTS),msHealth:JSON.stringify(MS_HEALTH_OVERRIDE),
    msProgress:JSON.stringify(MS_PROGRESS_OVERRIDE),msFields:JSON.stringify(MS_FIELD_OVERRIDE),
    shortTitles:JSON.stringify(MS_SHORT_TITLES),depComments:JSON.stringify(DEP_COMMENTS),
    notes:JSON.stringify(NOTES),rowOverrides:JSON.stringify(snapshotOverrides()),
    TASKS:JSON.stringify(TASKS),MILESTONES:JSON.stringify(MILESTONES),USER_MILESTONES:JSON.stringify(USER_MILESTONES)});
  const diff=(a,b)=>Object.keys(a).filter(k=>a[k]!==b[k]);

  // ---- the grid ----
  let E=null,g=null,dv=null,host=null;
  const colIdx=k=>g.getColumns().findIndex(c=>c.id===k);
  async function openType(type){
    setWorkspaceSection('comments',true); await wait(30);
    const b=$('btn-ye-view-'+type);
    if(!b) return null;
    b.focus(); b.click();
    await wait(120);
    host=$('grid-host'); E=SRETGrid._engine();
    if(!E) return null;
    g=E.grid; dv=E.dataView;
    return b;
  }
  const titleText=()=>{ const t=document.querySelector('#grid-host .sg-title'); return t?t.textContent:''; };
  async function edit(key,col,val){
    g.scrollRowIntoView(dv.getIdxById(key)); g.setActiveCell(dv.getIdxById(key),colIdx(col)); g.editActiveCell();
    const ed=host.querySelector('.sg-editor');
    if(!ed) return {err:'no editor'};
    ed.value=String(val); g.getEditorLock().commitCurrentEdit();
    await wait(30);
    const it=dv.getItemById(key);
    return it?it[col]:undefined;
  }
  async function del(keys){
    g.setSelectedRows(keys.map(k=>dv.getIdxById(k))); await wait(20);
    host.querySelector('[data-sg="tools"]').click(); await wait(20);
    const d=document.querySelector('[data-sg="delete"]'); if(d) d.click(); await wait(20);
    const go=host.querySelector('[data-sg="confirm-remove"]'); if(go) go.click();
    await wait(60);
  }
  function headerClickable(){
    const ib=$('icon-bar'), hd=document.querySelector('.rpt-hd');
    const shown=[...ib.querySelectorAll('button[id]')].filter(b=>rc(b).width>0&&rc(b).height>0);
    return hitIn(ib,'#icon-bar')&&hitIn(hd,'.rpt-hd')&&shown.length>0&&shown.every(b=>hitIn(b,'#'+b.id));
  }
  async function back(type){
    host.querySelector('[data-sg="back"]').click();
    await wait(300);
    ck(type+': Back closes the grid and gives the board back',
       !SRETGrid.isOpen()&&host.hidden&&!document.body.classList.contains('grid-open')&&getComputedStyle($('scroll-wrap')).display!=='none');
    const a=document.activeElement;
    return a&&a.id;
  }
  function common(type,label,n){
    ck(type+': View opens the grid in #grid-host', SRETGrid.isOpen()&&!!E&&host.contains(document.querySelector('.sg-screen')));
    ck(type+': title is "'+label+' ('+n+')"', titleText()===label+' ('+n+')', titleText());
    ck(type+': the grid holds '+n+' rows', dv&&dv.getLength()===n, dv&&dv.getLength());
    ck(type+': the icon bar and report header stay clickable (elementFromPoint)', headerClickable());
    ck(type+': no Add row (annotations are made on the board)', !host.querySelector('[data-sg="add"]'));
  }

  async function run(){
    stubWrite();
    ck('a fresh load says "No edits yet" and offers no View control',
       /No edits yet/.test(($('ws-your-edits')||{}).textContent||'')&&!document.querySelector('#ws-your-edits .ye-view'));

    // ---- entries through the real paths ----
    const wraps=[]; const seen={};
    document.querySelectorAll('#tbody .m-wrap[data-ms]').forEach(function(w){
      if(w.classList.contains('m-ghost')||w.classList.contains('m-wrap-loe')) return;
      const id=w.getAttribute('data-ms'); if(seen[id]) return; seen[id]=1; wraps.push(w); });
    const keys=[];
    for(let i=0;i<4;i++){
      wraps[i].click(); await wait(60);
      keys.push(msDialogFor);
      if(i<3){ $('ms-comment-text').value='Probe comment '+(i+1); onMsCommentInput(); }
      if(i===0) onMsHealthClick(document.querySelector('#ms-dialog .health-dot[data-val="1"]'));
      if(i===1){ const m=msDialogMs; $('ms-progress-input').value=String(m&&m.progress===37?38:37); }
      if(i===3){
        const m=msDialogMs;
        $('ms-title').value='Probe field title';
        const d=new Date(m.date+'T00:00:00'); d.setDate(d.getDate()+7);
        // P69: keep the milestone's own A, so this stays a date edit only
        // (a date typed without the A now also saves the finish as a forecast).
        $('ms-date').value=fmtTipDate(d)+(m.actual?' A':'');
        $('ms-weight').value=String(m.weight===7.5?8.5:7.5);
        onMsFieldInput();
      }
      saveMsDialog(true); await wait(20);
    }
    const [K1,K2,K3,K4]=keys;
    $('note-input').value='First probe note on #'+K1; saveNewNote();
    $('note-input').value='Second probe note'; saveNewNote();
    const rows=[...document.querySelectorAll('tr[data-type="row"]')];
    const rH=rows.find(tr=>tr.querySelector('.health-dot[data-orig-health]')&&tr.querySelector('.remarks'));
    const rR=rows.find(tr=>tr!==rH&&tr.querySelector('.remarks')&&!tr.querySelector('.remarks').textContent.trim());
    const hdot=rH.querySelector('.health-dot'); const hOrig=+hdot.getAttribute('data-orig-health');
    setHealth(hdot,hOrig===3?1:3);
    const rem=rR.querySelector('.remarks'); rem.focus(); rem.textContent='Probe row remark';
    rem.dispatchEvent(new Event('input',{bubbles:true})); rem.blur();
    activeCommentKeys=['pred:SNIP-101->SNIP-103']; $('dep-comment-text').value='Probe dependency comment'; saveCommentPanel();
    await wait(300);   // the card saves scheduled rebuilds; let them land

    const c=ye();
    const want={comments:3,notes:2,msHealth:1,msProgress:1,msFields:3,rowOverrides:2,depComments:1};
    ck('the rows are exactly the non-zero types with their counts',
       JSON.stringify(c)===JSON.stringify(want), JSON.stringify(c));
    ck('a zero-count type (Custom short titles) is hidden', !('shortTitles' in c)&&!$('btn-ye-view-shortTitles'));
    ck('each row carries its ANNOT_CATEGORIES label and count',
       [...document.querySelectorAll('#ws-your-edits .ye-item')].every(s=>{
         const cat=ANNOT_CATEGORIES.find(x=>x.key===s.getAttribute('data-cat'));
         return cat&&s.textContent===cat.label+': '+s.getAttribute('data-n'); }));
    ck('each row has an enabled View button', Object.keys(want).every(k=>{ const b=$('btn-ye-view-'+k); return b&&!b.disabled&&b.textContent.trim()==='View'; }));
    const nm0=USER_MILESTONES.length;
    openAddMilestone(); $('add-ms-name').value='Probe user milestone'; saveAddMilestone(); await wait(60);
    ck('a user milestone is never a row here', USER_MILESTONES.length===nm0+1&&!('userMs' in ye())&&!document.querySelector('#ws-your-edits [data-cat="userMs"]'));

    // ---- Milestone comments: edit, clear, delete, export, double-click ----
    let b=await openType('comments');
    if(!b||!E){ ck('comments: View opens the grid', false); return; }
    common('comments','Milestone comments',3);
    const cols=g.getColumns().map(x=>x.name);
    ck('comments: Activity ID and name are read only; the comment is editable',
       g.getColumns()[colIdx('id')].editor==null&&g.getColumns()[colIdx('name')].editor==null&&!!g.getColumns()[colIdx('value')].editor, JSON.stringify(cols));
    const nm=findMilestoneById(K1);
    ck('comments: the name is resolved from the schedule', dv.getItemById(K1).name!==''&&dv.getItemById(K1).name===(nm.actName||''), dv.getItemById(K1).name);
    let s0=snap();
    await edit(K1,'value','Edited in the table');
    let s1=snap();
    ck('comments: an edit lands in MS_COMMENTS', MS_COMMENTS[K1]==='Edited in the table');
    ck('comments: and in no other store, schedule data untouched', JSON.stringify(diff(s0,s1))==='["comments"]', JSON.stringify(diff(s0,s1)));
    await edit(K2,'value','');
    await wait(30);
    ck('comments: clearing removes the entry and the row', !(K2 in MS_COMMENTS)&&!dv.getItemById(K2)&&dv.getLength()===2, dv.getLength());
    ck('comments: the title count follows', titleText()==='Milestone comments (2)', titleText());
    ck('comments: the Your edits row follows', ye().comments===2, JSON.stringify(ye()));
    WRITES.length=0;
    const ex=host.querySelector('[data-sg="export"]'); if(ex) ex.click();
    await wait(200);
    const w=WRITES[0];
    ck('comments: Export .xlsx writes one workbook named after the type', WRITES.length===1&&/^Milestone comments .*\.xlsx$/.test(w&&w.name), w&&w.name);
    if(w){
      const r=sheetRows(w.wb,w.wb.SheetNames[0]);
      ck('comments: the sheet has the columns and one row per entry',
         JSON.stringify(r[0])===JSON.stringify(['Activity ID','Activity name','Comment'])&&r.length===3, JSON.stringify(r));
      ck('comments: carrying the edit', r.some(x=>x[0]===K1&&x[2]==='Edited in the table'));
    }
    // double-click on ID
    g.scrollRowIntoView(dv.getIdxById(K1)); g.setActiveCell(dv.getIdxById(K1),colIdx('id'));
    const idCell=host.querySelector('.slick-cell.active');
    if(idCell) idCell.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true,view:window}));
    await wait(200);
    const dlg=$('ms-dialog');
    ck('comments: double-click on the ID opens the milestone card', !!dlg&&!dlg.hidden&&msDialogFor===K1, msDialogFor);
    ck('comments: the card is above the grid', !!dlg&&!dlg.hidden&&hitIn(dlg,'#ms-dialog'));
    if(dlg&&!dlg.hidden) discardMsDialog();
    s0=snap();
    await del([K3]);
    ck('comments: Delete selected removes the entry', !(K3 in MS_COMMENTS)&&dv.getLength()===1&&titleText()==='Milestone comments (1)', dv.getLength()+' '+titleText());
    ck('comments: delete touched only MS_COMMENTS', JSON.stringify(diff(s0,snap()))==='["comments"]', JSON.stringify(diff(s0,snap())));
    let f=await back('comments');
    ck('comments: Back returns focus to its View button', f==='btn-ye-view-comments', f);

    // ---- health ----
    b=await openType('msHealth');
    if(!E){ ck('msHealth: View opens the grid', false); return; }
    common('msHealth','Milestone health overrides',1);
    s0=snap();
    const hv=await edit(K1,'value',4);
    ck('msHealth: Critical is stored as the card code 4', MS_HEALTH_OVERRIDE[K1]===4&&effectiveState(findMilestoneById(K1))==='CRIT', JSON.stringify(MS_HEALTH_OVERRIDE));
    ck('msHealth: only MS_HEALTH_OVERRIDE changed', JSON.stringify(diff(s0,snap()))==='["msHealth"]', JSON.stringify(diff(s0,snap())));
    s0=snap(); const mk0=MARKUP_COUNT;
    const bad=annotGridEdit(K1,'value',9);
    ck('msHealth: an unknown health code is refused and nothing changes', bad===false&&JSON.stringify(diff(s0,snap()))==='[]'&&MARKUP_COUNT===mk0);
    f=await back('msHealth');
    ck('msHealth: Back returns focus to its View button', f==='btn-ye-view-msHealth', f);
    const ico=document.querySelector('#tbody .m-wrap[data-ms="'+K1+'"] svg.ms-icon');
    ck('msHealth: the board marker shows Critical', !!ico&&ico.classList.contains(STATES.CRIT.cls), ico&&ico.getAttribute('class'));

    // ---- progress ----
    b=await openType('msProgress');
    common('msProgress','Milestone progress overrides',1);
    const p0=MS_PROGRESS_OVERRIDE[K2];
    s0=snap();
    const v150=await edit(K2,'value',150), v101=await edit(K2,'value',101), vm1=await edit(K2,'value',-1);
    ck('msProgress: 150, 101 and -1 are refused, the cell reverts', v150===p0&&v101===p0&&vm1===p0, [v150,v101,vm1].join(','));
    ck('msProgress: and the store is unchanged', JSON.stringify(diff(s0,snap()))==='[]', JSON.stringify(diff(s0,snap())));
    const sp=findMilestoneById(K2).progress;
    const target=sp===100?99:100;
    await edit(K2,'value',target);
    ck('msProgress: '+target+' is taken into MS_PROGRESS_OVERRIDE only', MS_PROGRESS_OVERRIDE[K2]===target&&JSON.stringify(diff(s0,snap()))==='["msProgress"]', JSON.stringify(diff(s0,snap())));
    await edit(K2,'value','');
    await wait(30);
    ck('msProgress: clearing restores the schedule value (entry and row gone)', !(K2 in MS_PROGRESS_OVERRIDE)&&dv.getLength()===0&&titleText()==='Milestone progress overrides (0)', dv.getLength());
    f=await back('msProgress');
    ck('msProgress: with the type empty its row is gone and focus lands on a View button',
       !$('btn-ye-view-msProgress')&&!!f&&/^btn-ye-view-/.test(f), f);

    // ---- field edits ----
    b=await openType('msFields');
    common('msFields','Milestone field edits',3);
    const fk=f2=>K4+'|'+f2;
    ck('msFields: one row per (milestone, field), field read only',
       !!dv.getItemById(fk('actName'))&&!!dv.getItemById(fk('date'))&&!!dv.getItemById(fk('weight'))&&g.getColumns()[colIdx('fieldLabel')].editor==null);
    s0=snap();
    const d0=MS_FIELD_OVERRIDE[K4].date;
    const bd=await edit(fk('date'),'value','not a date');
    ck('msFields: an unreadable date is refused, store unchanged', MS_FIELD_OVERRIDE[K4].date===d0&&JSON.stringify(diff(s0,snap()))==='[]', bd);
    const bw=await edit(fk('weight'),'value','heavy');
    ck('msFields: a weight that is not a number is refused', JSON.stringify(diff(s0,snap()))==='[]', bw);
    const nd=new Date(d0+'T00:00:00'); nd.setDate(nd.getDate()+7);
    const ndIso=nd.getFullYear()+'-'+String(nd.getMonth()+1).padStart(2,'0')+'-'+String(nd.getDate()).padStart(2,'0');
    await edit(fk('date'),'value',fmtTipDate(nd));
    ck('msFields: a d-Mmm-yy date is read and stored as ISO in MS_FIELD_OVERRIDE only',
       MS_FIELD_OVERRIDE[K4].date===ndIso&&JSON.stringify(diff(s0,snap()))==='["msFields"]', MS_FIELD_OVERRIDE[K4].date+' '+JSON.stringify(diff(s0,snap())));
    await edit(fk('actName'),'value','');
    await wait(30);
    ck('msFields: clearing a field removes just that override', !('actName' in MS_FIELD_OVERRIDE[K4])&&dv.getLength()===2&&titleText()==='Milestone field edits (2)', dv.getLength());
    f=await back('msFields');
    ck('msFields: Back returns focus to its View button', f==='btn-ye-view-msFields', f);

    // ---- row health and remarks ----
    b=await openType('rowOverrides');
    common('rowOverrides','Row health and remarks',2);
    const refH=rH.getAttribute('data-ref'), refR=rR.getAttribute('data-ref');
    s0=snap();
    await edit(refR,'value','Remark edited in the table');
    ck('rowOverrides: a remark edit lands on the row, nothing else changes',
       snapshotOverrides()[refR]&&snapshotOverrides()[refR].remarks==='Remark edited in the table'&&JSON.stringify(diff(s0,snap()))==='["rowOverrides"]', JSON.stringify(diff(s0,snap())));
    await edit(refH,'health','');
    await wait(30);
    ck('rowOverrides: clearing the health restores the row\'s own and the row leaves', !(refH in snapshotOverrides())&&dv.getLength()===1, JSON.stringify(snapshotOverrides()));
    f=await back('rowOverrides');
    ck('rowOverrides: Back returns focus to its View button', f==='btn-ye-view-rowOverrides', f);
    const trR=document.querySelector('tr[data-type="row"][data-ref="'+refR+'"] .remarks');
    const trH=document.querySelector('tr[data-type="row"][data-ref="'+refH+'"] .health-dot');
    ck('rowOverrides: the rebuilt board shows the remark and the restored health',
       !!trR&&trR.textContent==='Remark edited in the table'&&trR.classList.contains('changed')&&!!trH&&+trH.getAttribute('data-current-health')===hOrig&&!trH.classList.contains('changed'),
       (trR&&trR.textContent)+' '+(trH&&trH.className));

    // ---- dependency comments ----
    b=await openType('depComments');
    common('depComments','Dependency line comments',1);
    const dk='pred:SNIP-101->SNIP-103', dr=dv.getItemById(dk);
    ck('depComments: keyed by the line, shown as PRED to SUCC from the anchor', !!dr&&dr.dep==='SNIP-101 to SNIP-103'&&dr.id==='SNIP-103'&&dr.line==='Predecessor', JSON.stringify(dr));
    s0=snap();
    await edit(dk,'value','Dependency edited');
    ck('depComments: an edit lands in DEP_COMMENTS only', DEP_COMMENTS[dk]==='Dependency edited'&&JSON.stringify(diff(s0,snap()))==='["depComments"]', JSON.stringify(diff(s0,snap())));
    await del([dk]);
    ck('depComments: Delete selected removes it', !(dk in DEP_COMMENTS)&&dv.getLength()===0);
    f=await back('depComments');
    ck('depComments: the type leaves the rows', !$('btn-ye-view-depComments')&&!('depComments' in ye()));

    // ---- notes ----
    b=await openType('notes');
    common('notes','Notes',2);
    const n1=NOTES.find(n=>/First probe/.test(n.text)), n2=NOTES.find(n=>/Second probe/.test(n.text));
    const nr=dv.getItemById(n1.nid);
    ck('notes: the linked ID and its name show, the period is read only',
       nr.id===K1&&nr.name!==''&&nr.period===n1.period&&g.getColumns()[colIdx('period')].editor==null, JSON.stringify(nr));
    s0=snap();
    await edit(n1.nid,'status','review');
    ck('notes: a status edit lands in NOTES only', n1.status==='review'&&JSON.stringify(diff(s0,snap()))==='["notes"]', JSON.stringify(diff(s0,snap())));
    s0=snap();
    ck('notes: an unknown status is refused', annotGridEdit(n1.nid,'status','bogus')===false&&JSON.stringify(diff(s0,snap()))==='[]');
    const bt=await edit(n2.nid,'value','');
    ck('notes: an empty note text is refused (as the Notes pane)', n2.text==='Second probe note'&&JSON.stringify(diff(s0,snap()))==='[]', bt);
    await edit(n2.nid,'value','Second note, edited');
    ck('notes: a text edit lands in NOTES', n2.text==='Second note, edited');
    g.scrollRowIntoView(dv.getIdxById(n2.nid)); g.setActiveCell(dv.getIdxById(n2.nid),colIdx('nid'));
    const nc=host.querySelector('.slick-cell.active');
    if(nc) nc.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true,view:window}));
    await wait(60);
    const card=document.querySelector('#notes-list .note-card[data-nid="'+n2.nid+'"]');
    ck('notes: double-click on the note number opens the Notes pane at that note',
       WS_SECTION==='notes'&&!!card&&card.classList.contains('is-landed')&&/Second note, edited/.test(card.textContent));
    s0=snap();
    await del([n2.nid]);
    ck('notes: Delete selected removes the note', !NOTES.some(n=>n.nid===n2.nid)&&dv.getLength()===1&&JSON.stringify(diff(s0,snap()))==='["notes"]');
    f=await back('notes');
    ck('notes: Back returns to Comments & markups and focus to its View button', f==='btn-ye-view-notes'&&WS_SECTION==='comments', f+' '+WS_SECTION);

    const fin=ye();
    ck('the rows end at the expected counts', JSON.stringify(fin)===JSON.stringify({comments:1,notes:1,msHealth:1,msFields:2,rowOverrides:1}), JSON.stringify(fin));
    const net=performance.getEntriesByType('resource').map(e=>e.name).filter(u=>/^https?:/i.test(u));
    ck('the page made zero http(s) requests', net.length===0, net.join(', '));
  }

  window.addEventListener('load',function(){ setTimeout(async function(){
    try{ await run(); }catch(e){ ck('probe ran without throwing', false, e&&e.stack||e); }
    emit();
  },900); });
})();
"""


def render(html: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        path = f.name
    out = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                          "--host-resolver-rules=MAP * ~NOTFOUND",
                          "--window-size=1440,900", "--virtual-time-budget=60000",
                          "--dump-dom", "file://" + path],
                         capture_output=True, text=True, timeout=300).stdout
    m = OUT_RE.search(out)
    if not m:
        return {"checks": [{"name": "probe produced output", "pass": False, "detail": ""}]}
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8"))


def source_checks(src: str) -> list:
    out = []

    def ck(name, ok, detail=""):
        out.append({"name": "[source] " + name, "pass": bool(ok), "detail": str(detail)})

    for t in ("</body>", "<head>", "</head>", "</html>"):
        ck(f"the page holds exactly one {t}", src.count(t) == 1, src.count(t))
    ck("version grep returns 1", len(re.findall(r"3\.[0-9]*\.[0-9]*-P", src)) == 1)
    # P63 moved the version on; P62's own features are what this check proves.
    m = re.search(r"const APP_VERSION='3\.1\.0-P(\d+)';", src)
    ck("APP_VERSION is 3.1.0-P62 or a later partial", bool(m) and int(m.group(1)) >= 62, m and m.group(0))
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", src, re.S)
    ck("no literal script start tag inside any script", not any(re.search(r"<script", s, re.I) for s in scripts))
    ck("no CDN URL in the file", not re.search(r"cdnjs|cdn\.sheetjs|jsdelivr|unpkg", src))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    a = ap.parse_args()
    src = pathlib.Path(a.html).read_text(encoding="utf-8")
    checks = source_checks(src)
    html = src.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    checks += render(html)["checks"]
    fails = 0
    for c in checks:
        ok = c["pass"]
        fails += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + c["name"] + ("" if ok else f"  ({c['detail']})"))
    print(f"\n{len(checks) - fails}/{len(checks)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
