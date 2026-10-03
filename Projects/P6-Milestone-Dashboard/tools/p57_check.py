#!/usr/bin/env python3
"""
P57 (D-19) Notes panel check.

Stage 1 drives the real app: adds N=3 notes through the composer (button and
Ctrl+Enter), then exercises status, the period / status / search filters, the
#ID chips (link parsing, open-the-card, missing-on-board), the card's
"Mentioned in N notes" cross-link, edit, delete and Clear notes with their
inline confirmations, escaping of note text, the Notes export rows, the
selective-import category, and finally captures the real publishDashboard()
and exportModel() output.

Stage 2 opens the published file as a reader would and asserts the notes came
back with their status, period and links, and render in the Workspace.

Usage:
  python3 tools/p57_check.py [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p57-out">(.*?)</pre>', re.S)

STAGE1 = r"""
(function(){
  const R={checks:[]};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  const CAP={}; let capName=null;
  URL.createObjectURL=function(b){ CAP[capName]=b; return 'blob:x'; };
  HTMLAnchorElement.prototype.click=function(){};
  window.confirm=function(){ return true; };
  const $=function(id){ return document.getElementById(id); };
  const qa=function(s){ return Array.prototype.slice.call(document.querySelectorAll(s)); };
  function finish(){
    const o=document.createElement('pre'); o.id='p57-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  window.addEventListener('load',function(){ setTimeout(function(){
   try{
    // The seed board's milestone ids, so the chips point at real markers.
    const ids=qa('.m-wrap[data-ms]').map(function(w){ return w.getAttribute('data-ms'); })
                .filter(function(v,i,a){ return v&&a.indexOf(v)===i; });
    const A=ids[0], B=ids[1], C=ids[2];
    R.ids=[A,B,C];
    ck('the board has at least three milestone ids to link', !!(A&&B&&C), ids.length);

    // ---- rail and section ----
    // D-32 (P81): the left nav's My work group, Notes first.
    const rail=qa('#ws-rail .ui-nav__group[data-group="work"] .ui-nav__item').map(function(b){ return b.dataset.id; });
    ck('Notes is the first item under My work in the nav', rail[0]==='notes', rail.join(','));
    setWorkspaceSection('notes',true);
    ck('the Notes section is showing', !$('ws-sec-notes').hidden&&$('ws-panel').classList.contains('open')&&
       $('ws-hd-title').textContent==='Notes', $('ws-hd-title').textContent);

    // ---- add three notes (N=3): button, button, Ctrl+Enter ----
    const inp=$('note-input');
    inp.value='Geotech slipping, owner to confirm #'+A; saveNewNote();
    inp.value='Tie-in revised:\n- markup issued #'+B+'\n- process to review #'+C+' and #'+A; saveNewNote();
    inp.value='Plain note, no links';
    inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',ctrlKey:true,bubbles:true}));
    ck('three notes saved (two by button, one by Ctrl+Enter)', NOTES.length===3, NOTES.length);
    ck('the composer clears after saving', inp.value==='', JSON.stringify(inp.value));
    ck('links are parsed from the text, de-duplicated, upper-cased',
       JSON.stringify(NOTES[1].links)===JSON.stringify([B,C,A]), JSON.stringify(NOTES[1].links));
    ck('a note with no #ID has no links', NOTES[2].links.length===0);
    const per=reportPeriodISO();
    ck('each note is stamped with the reporting period (week ending on or after the Report date)',
       NOTES.every(function(n){ return n.period===per; }), per);
    const rd=REPORT_META.reportDate, pd=new Date(per+'T00:00:00');
    ck('the period is on or after the Report date and within 6 days of it',
       pd>=new Date(rd.getFullYear(),rd.getMonth(),rd.getDate())&&(pd-rd)<7*864e5, per+' vs '+rd.toISOString());
    const cards=qa('#notes-list .note-card');
    ck('all three render, newest first', cards.length===3&&cards[0].getAttribute('data-nid')===NOTES[2].nid,
       cards.map(function(c){ return c.getAttribute('data-nid'); }).join(','));
    ck('bullets render as a list', !!document.querySelector('#notes-list .note-card[data-nid="'+NOTES[1].nid+'"] ul li'));
    const nb=()=>{ const b=document.querySelector('#ws-rail .ui-nav__item[data-id="notes"] .ui-nav__badge'); return b?b.textContent:''; };
    ck('the nav badge counts open notes in this period', nb()==='3', nb());

    // ---- status ----
    setNoteStatus(NOTES[0].nid,'sent'); setNoteStatus(NOTES[1].nid,'closed');
    const sel=document.querySelector('#notes-list .note-card[data-nid="'+NOTES[0].nid+'"] select.note-status');
    ck('status shows on the note (class and value)', sel&&sel.value==='sent'&&sel.classList.contains('st-sent'));
    ck('a closed note drops out of the badge count', nb()==='2', nb());

    // ---- filters ----
    setNotesStatus('sent');
    ck('status filter: Sent shows exactly the sent note', qa('#notes-list .note-card').length===1);
    setNotesStatus('all');
    setNotesSearch(B);
    ck('search finds the note mentioning an id', qa('#notes-list .note-card').length===1&&
       qa('#notes-list .note-card')[0].getAttribute('data-nid')===NOTES[1].nid);
    setNotesSearch('');
    const rdWas=isoDay(REPORT_META.reportDate);
    const nextWeek=new Date(REPORT_META.reportDate.getTime()+7*864e5);
    setReportDate(isoDay(nextWeek));
    ck('moving the Report date a week on moves the current period, so This period is empty',
       qa('#notes-list .note-card').length===0&&reportPeriodISO()!==per, reportPeriodISO());
    setNotesCollection('all');
    ck('All still shows all three, each labelled with its collection',
       qa('#notes-list .note-card').length===3&&qa('#notes-list .note-meta')[0].textContent.indexOf(fmtPeriod(per))===0);
    ck('the collection dropdown lists the earlier collection and the new current one',
       qa('#notes-coll-sel option').length===2);
    setReportDate(rdWas); setNotesCollection('current');
    ck('back on the original Report date the three are current again', qa('#notes-list .note-card').length===3);

    // ---- chips ----
    const chip=document.querySelector('#notes-list .note-card[data-nid="'+NOTES[0].nid+'"] .note-id');
    ck('an #ID is a chip', !!chip&&chip.textContent==='#'+A&&!chip.classList.contains('is-missing'));
    inp.value='Check #ZZQ-9999 later'; saveNewNote();
    const miss=document.querySelector('#notes-list .note-id[data-id="ZZQ-9999"]');
    ck('an id not on the board renders as a struck-through chip with no action', !!miss&&miss.classList.contains('is-missing')&&!miss.getAttribute('onclick'));
    deleteNote(NOTES[3].nid);
    chip.click();
    setTimeout(function(){
     try{
      const dlg=$('ms-dialog');
      ck('clicking a chip opens that milestone\'s card', !dlg.hidden&&msDialogFor===A, msDialogFor);
      const ref=$('ms-notes-ref');
      ck('the card says how many notes mention it', !ref.hidden&&ref.textContent==='Mentioned in 2 notes', ref.textContent);
      ref.click();
      ck('the card link opens Notes filtered to that milestone',
         !$('ws-sec-notes').hidden&&$('notes-search').value==='#'+A&&qa('#notes-list .note-card').length===2,
         $('notes-search').value+' / '+qa('#notes-list .note-card').length);
      discardMsDialog(); setNotesSearch(''); $('notes-search').value=''; NOTES_VIEW.coll='current'; renderNotes();

      // ---- edit ----
      editNote(NOTES[2].nid);
      const ed=$('note-edit-text');
      ck('Edit opens the note in place', !!ed&&ed.value==='Plain note, no links');
      ed.value='Now linked to #'+C; saveNoteEdit(NOTES[2].nid);
      ck('saving an edit updates the text and re-derives the links',
         NOTES[2].text==='Now linked to #'+C&&JSON.stringify(NOTES[2].links)===JSON.stringify([C]));

      // ---- escaping ----
      inp.value='<img src=x onerror="window.__xss=1"> & <b>bold</b>'; saveNewNote();
      ck('note text is escaped, never inserted as markup',
         !document.querySelector('#notes-list img')&&!document.querySelector('#notes-list .note-body b')&&!window.__xss);

      // ---- export rows ----
      const rows=collectNotesRows();
      ck('the Notes sheet has a header and one row per note', rows.length===NOTES.length+1&&rows[0][0]==='Note'&&rows[0][7]==='Note text', rows.length);
      const r1=rows.find(function(r){ return r[0]===NOTES[1].nid; });
      ck('an export row carries status, period and linked milestones',
         r1&&r1[1]==='Closed'&&r1[3]===fmtPeriod(per)&&r1[6]===[B,C,A].join(', '), JSON.stringify(r1));
      const src=exportComments.toString();
      ck('the comments workbook appends the Notes sheet', /collectNotesRows\(\)\),\s*'Notes'/.test(src));

      // ---- delete with inline confirm ----
      const victim=NOTES[NOTES.length-1].nid;
      askDeleteNote(victim);
      const conf=document.querySelector('#notes-list .note-card[data-nid="'+victim+'"] .sd-confirm');
      const btns=conf?conf.querySelectorAll('.sd-confirm-actions button'):[];
      ck('Delete asks inline: Cancel first, then the danger Delete',
         btns.length===2&&/Cancel/.test(btns[0].textContent)&&btns[1].classList.contains('sd-btn-danger')&&/Delete/.test(btns[1].textContent));
      btns[0].click();
      ck('Cancel keeps the note', !!noteById(victim)&&!document.querySelector('#notes-list .sd-confirm'));
      askDeleteNote(victim); deleteNote(victim);
      ck('Delete removes exactly that note', !noteById(victim)&&NOTES.length===3, NOTES.length);

      // ---- selective import category ----
      const cat=ANNOT_CATEGORIES.find(function(c){ return c.key==='notes'; });
      ck('Notes is a selective-import category', !!cat&&cat.count({notes:[1,2]})===2);
      const before=NOTES.length;
      applyNotes({notes:[{nid:NOTES[0].nid,text:'Replaced #'+B,status:'pending',period:per,at:NOTES[0].at},
                         {nid:'N-900',text:'Imported note',status:'open',period:per,at:new Date().toISOString()}]});
      ck('applying notes replaces by id and adds new ones (a P57 "pending" reads as In review)',
         NOTES.length===before+1&&noteById(NOTES[0].nid).status==='review'&&!!noteById('N-900'));

      // ---- D-19a: status set, layout, bulk, collections, collection export ----
      ck('the status set is Note, Open, Sent, In review, Outstanding, Done, Closed',
         JSON.stringify(NOTE_STATUSES.map(function(s){ return NOTE_STATUS_LABELS[s]; }))===
         JSON.stringify(['Note','Open','Sent','In review','Outstanding','Done','Closed']));
      setWorkspaceSection('notes',true); setNotesTab('list'); setNotesCollection('current');
      const head=document.querySelector('#notes-list .note-card .note-head');
      const stSel=head&&head.querySelector('select.note-status'), meta=head&&head.querySelector('.note-meta');
      ck('the status sits at the right of the note', !!stSel&&head.lastElementChild===stSel&&
         stSel.getBoundingClientRect().left>meta.getBoundingClientRect().left);
      // A second, earlier collection with three notes (N=3).
      const prev=isoDay(new Date(new Date(per+'T00:00:00').getTime()-7*864e5));
      ['Earlier one #'+A,'Earlier two','Earlier three'].forEach(function(t){
        NOTES.push({nid:nextNoteId(),text:t,status:'sent',links:noteLinks(t),period:prev,at:new Date(Date.now()-864e5).toISOString(),updatedAt:new Date().toISOString()});
      });
      renderNotes();
      setNotesCollection(prev);
      ck('choosing a collection in the dropdown shows only its notes',
         qa('#notes-list .note-card').length===3&&$('notes-coll-sel').value===prev);
      toggleSelectAllNotes(true);
      ck('Select all picks every visible note', NOTES_SELECTED.length===3&&$('notes-sel-all').checked);
      const keep=NOTES_SELECTED[1];
      toggleNoteSelected(keep,false);
      ck('deselecting one leaves the rest, and Select all shows mixed',
         NOTES_SELECTED.length===2&&$('notes-sel-all').indeterminate);
      $('notes-bulk-status').value='done'; applyBulkNoteStatus();
      const inPrev=NOTES.filter(function(n){ return n.period===prev; });
      ck('bulk update sets exactly the selected notes',
         inPrev.filter(function(n){ return n.status==='done'; }).length===2&&noteById(keep).status==='sent',
         inPrev.map(function(n){ return n.status; }).join(','));
      ck('the selection clears after applying', NOTES_SELECTED.length===0);
      setNotesTab('coll');
      const rowsC=qa('#coll-list .coll-row');
      ck('Collections lists one row per collection, current first', rowsC.length===2&&rowsC[0].getAttribute('data-period')===per);
      const prevRow=rowsC[1];
      ck('a collection row summarises notes, open and closed',
         /3 notes/.test(prevRow.textContent)&&/1 open/.test(prevRow.textContent)&&/2 closed/.test(prevRow.textContent), prevRow.textContent);
      prevRow.click();
      ck('selecting a collection shows its details form below the list',
         COLL_SELECTED===prev&&!!$('coll-name')&&!!$('coll-to')&&!!$('coll-on')&&!!$('coll-remarks'));
      $('coll-to').value='J. Smith'; $('coll-to').dispatchEvent(new Event('change'));
      ck('editing a detail saves it to the collection', NOTE_COLLECTIONS[prev].issuedTo==='J. Smith'&&
         /to J\. Smith/.test(document.querySelector('#coll-list .coll-row[data-period="'+prev+'"]').textContent));
      const cr=collectCollectionRows(prev);
      const hdr=cr.findIndex(function(r){ return r[0]==='Note'; });
      ck('the collection export heads with its details and ends with one row per note plus reply columns',
         cr[0][1]===collectionInfo(prev).name&&cr[2][1]==='J. Smith'&&hdr>0&&cr[hdr][4]==='Addressed (Y/N)'&&cr[hdr][5]==='Response'&&cr.length-hdr-1===3);
      // Export with "Set Open notes to Sent": stub the workbook library at the boundary.
      const openOne=NOTES.find(function(n){ return n.period===prev; }); openOne.status='open';
      window.ensureXLSX=function(){ return Promise.resolve(); };
      window.XLSX={utils:{book_new:function(){ return {}; },aoa_to_sheet:function(x){ return x; },
                   book_append_sheet:function(wb,sh,n){ wb[n]=sh; }},writeFile:function(wb,name){ window.__wb={wb:wb,name:name}; }};
      renderCollections();
      $('coll-mark-sent').checked=true;
      $('btn-coll-export').click();
      setTimeout(function(){
       try{
        ck('Export collection writes one workbook named for the collection',
           !!window.__wb&&/^Notes_.*\.xlsx$/.test(window.__wb.name)&&window.__wb.wb.Notes.length===collectCollectionRows(prev).length, window.__wb&&window.__wb.name);
        ck('with "Set Open notes to Sent" ticked, the open note is now Sent', openOne.status==='sent');
        $('btn-coll-view').click();
        ck('View notes opens that collection in the Notes list',
           NOTES_TAB==='list'&&!$('notes-pane-list').hidden&&qa('#notes-list .note-card').length===3&&$('notes-coll-sel').value===prev);
        setNotesCollection('current');
        // ---- publish + model capture ----
      R.expectNotes=NOTES.map(function(n){ return {nid:n.nid,status:n.status,period:n.period,links:n.links}; });
      R.expectColl=JSON.parse(JSON.stringify(NOTE_COLLECTIONS));
      capName='model'; exportModel();
      capName='published'; publishDashboard();
      Promise.all(['model','published'].map(function(n){
        return CAP[n]?CAP[n].text().then(function(t){ R[n]=t; }):Promise.reject(new Error('no '+n));
      })).then(function(){
        try{ const m=JSON.parse(R.model); ck('the model export carries the notes', (m.notes||[]).length===NOTES.length, (m.notes||[]).length); }
        catch(e){ ck('the model export is JSON', false, e.message); }
        delete R.model; finish();
      },function(e){ R.err=e.message; finish(); });
       }catch(e){ R.err=e.message+' '+e.stack; finish(); }
      },200);
     }catch(e){ R.err=e.message+' '+e.stack; finish(); }
    },300);
   }catch(e){ R.err=e.message+' '+e.stack; finish(); }
  },1200); });
})();
"""

STAGE2 = r"""
(function(){
  const R={checks:[]};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  window.addEventListener('load',function(){ setTimeout(function(){
    try{
      const exp=JSON.parse(document.getElementById('p57-expect').textContent);
      ck('published file: every note came back', NOTES.length===exp.length, NOTES.length+' of '+exp.length);
      const same=exp.every(function(e){ const n=NOTES.find(function(x){ return x.nid===e.nid; });
        return n&&n.status===e.status&&n.period===e.period&&JSON.stringify(n.links)===JSON.stringify(e.links); });
      ck('published file: status, period and links survive', same);
      const ec=JSON.parse(document.getElementById('p57-expect-coll').textContent);
      ck('published file: collection details survive', JSON.stringify(NOTE_COLLECTIONS)===JSON.stringify(ec));
      setWorkspaceSection('notes',true); NOTES_VIEW.coll='all'; renderNotes();
      ck('published file: the notes render in the Workspace',
         document.querySelectorAll('#notes-list .note-card').length===exp.length);
    }catch(e){ R.err=e.message; }
    const o=document.createElement('pre'); o.id='p57-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  },1500); });
})();
"""


def render(html: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "p.html"
        f.write_text(html, encoding="utf-8")
        out = subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                              "--window-size=1440,900", "--virtual-time-budget=30000",
                              "--dump-dom", f.as_uri()], capture_output=True, text=True, timeout=300).stdout
    hits = OUT_RE.findall(out)
    if not hits:
        sys.exit("Probe output not found; the page likely threw before the probe ran.")
    return json.loads(base64.b64decode(hits[-1].strip()).decode("utf-8"))


def inject(html: str, script: str, extra: str = "") -> str:
    out = html.replace("</body>", f"{extra}<script>\n{script}\n</script>\n</body>")
    if out == html:
        sys.exit("Could not find </body> to inject into.")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default="src/milestone-dashboard.html")
    a = ap.parse_args()
    html = pathlib.Path(a.html).read_text(encoding="utf-8")
    r1 = render(inject(html, STAGE1))
    checks = r1["checks"]
    if r1.get("err"):
        print("STAGE 1 ERROR:", r1["err"])
    if r1.get("published"):
        exp = json.dumps(r1["expectNotes"]).replace("<", "\\u003c")
        ec = json.dumps(r1["expectColl"]).replace("<", "\\u003c")
        block = (f'<script type="application/json" id="p57-expect">{exp}</script>\n'
                 f'<script type="application/json" id="p57-expect-coll">{ec}</script>\n')
        r2 = render(inject(r1["published"], STAGE2, block))
        checks += r2["checks"]
        if r2.get("err"):
            print("STAGE 2 ERROR:", r2["err"])
    else:
        checks.append({"name": "publish captured", "pass": False, "detail": ""})
    fails = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("  ok   " if c["pass"] else "  FAIL ") + c["name"] + ("   [" + c["detail"] + "]" if c["detail"] and not c["pass"] else ""))
    print(f"{len(checks)-len(fails)}/{len(checks)} checks passed")
    return 1 if fails or r1.get("err") else 0


if __name__ == "__main__":
    sys.exit(main())
