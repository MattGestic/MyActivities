#!/usr/bin/env python3
"""
p66_check: the milestone card re-laid to Matt's approved design (P66).

docs/mockups/P66/milestone-dialog.dc.html is the reference. This check drives
the REAL card in headless Chrome, opened by clicking a marker on the board,
and asserts the behaviour the re-skin added or changed, not just the markup:

  - 380px wide; the save pair is always on screen and DISABLED while clean,
    and a click on a disabled control does nothing (no save, no close, no
    "Saved" flash);
  - the icon save stores, stays open, flashes "Saved", and re-disables;
  - the remark box is a NEW remark: it opens empty even when a remark is
    stored, the save clears it, and the Follow-up select sets the entry's
    status (open / sent / done);
  - the health pill opens the existing dots as a popover; picking a dot goes
    through onMsHealthClick (the pill's label follows) and closes it; Escape
    closes the popover before it discards the card;
  - the changed-dots are the 6px accent dot, and their titles carry the
    previous value ("Previous: X", health "Updated · was X");
  - Duration is the calendar days from start to finish, and follows a typed
    finish date;
  - predecessor and successor chips match DEP_DATA, their dot is the linked
    milestone's effective state, the count reads "N pred · N succ", and a chip
    opens that milestone's card;
  - the read-first fields have no fill or border at rest;
  - the history mount #ms-history exists, open, with its placeholder;
  - the fields the design has no place for are kept in "More fields".

Usage:
  python3 tools/p66_check.py [--html FILE]
Exit code 1 on any failed check.
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

OUT_RE = re.compile(r'<pre id="p66-out">(.*?)</pre>', re.S)

VIEWPORTS = [(1440, 900), (390, 844)]

PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(n,p,d){ R.checks.push({name:n,pass:!!p,detail:d===undefined?'':String(d)}); }
  function emit(){ const o=document.createElement('pre'); o.id='p66-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o); }
  const settle=()=>new Promise(r=>setTimeout(r,240));
  const $=id=>document.getElementById(id);
  const dlg=()=>$('ms-dialog');
  const cs=el=>getComputedStyle(el);
  const wrapOf=id=>document.querySelector('#tbody .m-wrap[data-ms="'+CSS.escape(id)+'"]');
  const open=async function(id){
    const w=wrapOf(id); if(!w) return false;
    if(!dlg().hidden){ discardMsDialog(); await settle(); }
    w.click(); await settle();
    if(dlg().hidden) throw new Error('card did not open for '+id);
    return true;
  };
  const type=function(id,v){
    const e=$(id); if(!e) return false;
    e.value=v; e.dispatchEvent(new Event('input',{bubbles:true}));
    return true;
  };
  const acts=()=>$('ms-save-actions');
  const btn=i=>acts().querySelectorAll('.ms-act')[i];
  const enabled=()=>acts().getAttribute('aria-disabled')==='false'&&
    Array.prototype.every.call(acts().querySelectorAll('.ms-act'),b=>b.getAttribute('aria-disabled')==='false');
  const msEntries=k=>ENTRIES.filter(e=>e.target.kind==='ms'&&e.target.key===k);

  try{
    const st=document.createElement('style');
    st.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(st);
    await settle(); await settle();

    // A milestone with a start date, on the board, with relationships at
    // least one of which is itself on the board, so every section is real.
    const onBoard=m=>!!wrapOf(msKeyFor(m));
    const ids=v=>String(v||'').split(',').map(x=>x.trim()).filter(Boolean);
    const cands=MILESTONES.filter(function(m){
      const id=msId(m); if(!id||!onBoard(m)) return false;
      if(!(m.start&&fmtTipDate(m.start)!==fmtTipDate(m.date))) return false;
      const d=DEP_DATA[id]; if(!d) return false;
      return ids(d.pred).concat(ids(d.succ)).some(x=>!!wrapOf(x));
    });
    const S=cands[0];
    ck('sample: a started milestone with an on-board relationship exists', !!S,
       S?msId(S):'none of '+MILESTONES.length);
    const A=msId(S), key=msKeyFor(S);
    R.notes.sample=A;

    // ===== 1. Width and the save pair at rest =====
    await open(A);
    const w=Math.round(dlg().getBoundingClientRect().width);
    ck('width: 380px, or the viewport less 24px on a phone',
       w===Math.min(380,window.innerWidth-24), w+' at '+window.innerWidth);
    const b0=btn(0), b1=btn(1);
    ck('save pair: both on screen at rest',
       !!b0&&!!b1&&b0.getBoundingClientRect().width>0&&b1.getBoundingClientRect().width>0&&!acts().hidden,
       acts().outerHTML.slice(0,80));
    ck('save pair: DISABLED while the form is clean (aria-disabled, muted)',
       !enabled()&&parseFloat(cs(b1).opacity)<1, 'aria='+acts().getAttribute('aria-disabled')+' opacity='+cs(b1).opacity);
    const nBefore=ENTRIES.length;
    b0.click(); await settle(); b1.click(); await settle();
    ck('save pair: a click while disabled does nothing (open, no entry, no flash)',
       !dlg().hidden&&ENTRIES.length===nBefore&&$('ms-saved-flash').hidden,
       JSON.stringify({open:!dlg().hidden,entries:ENTRIES.length-nBefore,flash:!$('ms-saved-flash').hidden}));

    // ===== 2. Read first, edit on touch =====
    const fin=$('ms-date');
    ck('fields: the finish date has no fill and no border at rest',
       cs(fin).backgroundColor==='rgba(0, 0, 0, 0)'&&parseFloat(cs(fin).borderTopWidth)===0,
       cs(fin).backgroundColor+' / '+cs(fin).borderTopWidth);
    ck('fields: the title is 16px semibold, no fill at rest',
       cs($('ms-title')).fontSize==='16px'&&+cs($('ms-title')).fontWeight>=600&&
       cs($('ms-title')).backgroundColor==='rgba(0, 0, 0, 0)',
       cs($('ms-title')).fontSize+' '+cs($('ms-title')).fontWeight);
    ck('fields: the type and mark picker is the meta line’s diamond button',
       dlg().querySelector('.ms-heading').contains($('ms-icon-btn')), '');

    // ===== 3. Duration =====
    const days=(a,b)=>Math.round((msDateMs(b)-msDateMs(a))/86400000);
    const want=days(S.start,S.date)+'d';
    ck('duration: calendar days from start to finish', $('ms-duration').textContent===want,
       $('ms-duration').textContent+' want '+want);
    const nd=new Date(S.date+'T00:00:00'); nd.setDate(nd.getDate()+10);
    type('ms-date',fmtTipDate(isoDay(nd)));
    ck('duration: follows a typed finish date', $('ms-duration').textContent===(days(S.start,S.date)+10)+'d',
       $('ms-duration').textContent);
    ck('save pair: a typed edit ENABLES both', enabled(), acts().getAttribute('aria-disabled'));
    discardMsDialog(); await settle();

    // ===== 4. Remark box, follow-up, icon save and flash =====
    await open(A);
    type('ms-comment-text','P66 first remark');
    $('ms-followup').value='sent';
    btn(0).click(); await settle();
    let eA=msEntries(key), last=eA[eA.length-1];
    ck('save: the icon save stores the remark and stays open',
       !dlg().hidden&&!!last&&last.text==='P66 first remark'&&MS_COMMENTS[key]==='P66 first remark',
       JSON.stringify(last&&{text:last.text,status:last.status}));
    ck('follow-up: the select sets the entry status (sent)', !!last&&last.status==='sent', last&&last.status);
    ck('save: "Saved" flashes after the icon save', !$('ms-saved-flash').hidden, '');
    ck('save: the remark box and follow-up reset for the next remark, and the pair disables',
       $('ms-comment-text').value===''&&$('ms-followup').value==='open'&&!enabled(),
       JSON.stringify({box:$('ms-comment-text').value,fu:$('ms-followup').value,enabled:enabled()}));
    discardMsDialog(); await settle();
    await open(A);
    ck('remark: the box opens EMPTY although a remark is stored',
       $('ms-comment-text').value===''&&MS_COMMENTS[key]==='P66 first remark',
       JSON.stringify({box:$('ms-comment-text').value,stored:MS_COMMENTS[key]}));
    ck('remark: the placeholder is "Add a comment"', $('ms-comment-text').placeholder==='Add a comment',
       $('ms-comment-text').placeholder);
    const nC=msEntries(key).length;
    type('ms-title',$('ms-title').value+' P66');
    btn(1).click(); await settle(); await settle();
    eA=msEntries(key); last=eA[eA.length-1];
    ck('remark: a save with the box empty makes no clear, and keeps the stored remark',
       dlg().hidden&&MS_COMMENTS[key]==='P66 first remark'&&!eA.some(e=>e.clearText),
       JSON.stringify({entries:eA.length-nC,stored:MS_COMMENTS[key]}));
    // The default, on a milestone with no entry yet, so the save is a new
    // entry rather than one coalesced into the "sent" entry above (a
    // coalesced save keeps the entry it folds into, status included).
    const S2=cands.filter(m=>msKeyFor(m)!==key&&!msEntries(msKeyFor(m)).length)[0];
    await open(msId(S2));
    ck('follow-up: the select opens on Open', $('ms-followup').value==='open', $('ms-followup').value);
    type('ms-comment-text','P66 default follow-up');
    btn(1).click(); await settle(); await settle();
    const e2=msEntries(msKeyFor(S2));
    ck('follow-up: a new entry saved with the default is open',
       e2.length===1&&e2[0].status==='open'&&e2[0].text==='P66 default follow-up', JSON.stringify(e2.map(e=>e.status)));

    // ===== 5. Health pill and popover =====
    await open(A);
    const pill=$('ms-health-pill'), pop=$('ms-health-pop');
    ck('health: the pill holds a dot and the state label, popover shut',
       pill.contains($('ms-status'))&&!!pill.querySelector('.ms-pill-dot')&&pop.hidden&&
       $('ms-status').textContent===(STATE_LABELS[effectiveState(S)]||''),
       $('ms-status').textContent);
    const pillBg=cs(pill).backgroundColor;
    pill.click(); await settle();
    ck('health: clicking the pill opens the dots under it',
       !pop.hidden&&pill.getAttribute('aria-expanded')==='true'&&
       pop.getBoundingClientRect().top>=pill.getBoundingClientRect().bottom-1&&
       pop.contains($('ms-health-dots')), JSON.stringify(pop.getBoundingClientRect()));
    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
    await settle();
    ck('health: Escape closes the popover first, not the card', pop.hidden&&!dlg().hidden, '');
    pill.click(); await settle();
    const target=(effectiveState(S)==='RISK')?4:3;
    document.querySelector('#ms-health-dots .health-dot[data-val="'+target+'"]').click(); await settle();
    ck('health: picking a dot goes through onMsHealthClick and closes the popover',
       pop.hidden&&msFormHealth===target&&$('ms-status').textContent===(target===3?'At risk':'Critical')&&enabled(),
       JSON.stringify({hidden:pop.hidden,form:msFormHealth,label:$('ms-status').textContent}));
    ck('health: the pill takes the new state’s tint', cs(pill).backgroundColor!==pillBg, pillBg+' -> '+cs(pill).backgroundColor);
    btn(0).click(); await settle(); await settle();
    const hm=$('ms-mark-health');
    ck('changed-dot: shows beside the pill once health is overridden, titled "Updated · was X"',
       !hm.hidden&&/^Updated · was /.test(hm.title)&&hm.nextElementSibling===pill,
       hm.title);
    const r=hm.getBoundingClientRect();
    const accent=cs(document.documentElement).getPropertyValue('--color-accent').trim();
    const probe=document.createElement('span'); probe.style.color='var(--color-accent)'; document.body.appendChild(probe);
    const accentRgb=cs(probe).color; probe.remove();
    ck('changed-dot: the 6px accent dot', Math.round(r.width)===6&&Math.round(r.height)===6&&
       cs(hm).backgroundColor===accentRgb, Math.round(r.width)+'x'+Math.round(r.height)+' '+cs(hm).backgroundColor+' vs '+accentRgb);
    // Field changed-dot title.
    const fm=$('ms-mark-actName');
    ck('changed-dot: a field mark titles its previous value "Previous: X"',
       !fm.hidden&&/^Previous: /.test(fm.title), fm.hidden?'hidden':fm.title);
    discardMsDialog(); await settle();

    // ===== 6. Predecessors and successors =====
    await open(A);
    const d=DEP_DATA[A], P=ids(d.pred), Q=ids(d.succ);
    const pc=Array.prototype.slice.call($('ms-dep-pred-chips').querySelectorAll('.ms-dep-chip'));
    const qc=Array.prototype.slice.call($('ms-dep-succ-chips').querySelectorAll('.ms-dep-chip'));
    ck('chips: one per predecessor and successor, in DEP_DATA order',
       pc.map(c=>c.getAttribute('data-id')).join()===P.join()&&qc.map(c=>c.getAttribute('data-id')).join()===Q.join(),
       JSON.stringify({pred:P,succ:Q}));
    ck('chips: the count reads "N pred · N succ"',
       $('ms-dep-count').textContent===P.length+' pred · '+Q.length+' succ', $('ms-dep-count').textContent);
    const bad=pc.concat(qc).filter(function(c){
      const lm=findMilestoneById(c.getAttribute('data-id'));
      const want=lm?statusClassOf(effectiveState(lm)):'future';
      return c.querySelector('.ms-chip-dot').getAttribute('data-st')!==want; });
    ck('chips: each dot is the linked milestone’s effective state', bad.length===0&&pc.length+qc.length>0,
       bad.map(c=>c.getAttribute('data-id')).join(',')||'all '+(pc.length+qc.length)+' agree');
    const lm0=findMilestoneById((pc[0]||qc[0]).getAttribute('data-id'));
    ck('chips: the title is the linked milestone’s name', !!lm0&&(pc[0]||qc[0]).title.indexOf(lm0.actName||'')===0, (pc[0]||qc[0]).title);
    ck('chips: the raw ID textareas are kept, hidden, with the same values',
       $('ms-dep-pred-list').value===P.join(', ')&&$('ms-dep-succ-list').value===Q.join(', ')&&
       $('ms-dep-pred-list').closest('[hidden]')!==null, '');
    ck('chips: the board-line toggles live in this section',
       $('ms-dep-lists').contains($('ms-toggle-pred'))&&$('ms-dep-lists').contains($('ms-toggle-succ')), '');
    const live=pc.concat(qc).filter(c=>!c.classList.contains('is-off'))[0];
    const liveId=live.getAttribute('data-id');
    $('ms-dep-lists').open=true; await settle();
    live.click(); await settle(); await settle();
    ck('chips: clicking an on-board chip opens THAT milestone’s card',
       !dlg().hidden&&$('ms-code').textContent===liveId, $('ms-code').textContent+' want '+liveId);
    discardMsDialog(); await settle();

    // ===== 7. History mount and More fields =====
    await open(A);
    const hist=$('ms-history');
    // Integration (orchestrator): the history is now filled from ENTRIES by
    // SRETHistory. The empty placeholder is asserted on a milestone with none.
    const keyA=msDialogFor, mine=msEntriesFor(keyA);
    const rows=[...hist.querySelectorAll('.nh-entry')];
    ck('history: #ms-history is the open section’s body and lists this milestone’s entries',
       $('ms-hist-fold').open&&$('ms-hist-fold').contains(hist)&&mine.length>=1&&rows.length===mine.length,
       rows.length+' rows vs '+mine.length+' entries');
    const ats=rows.map(r=>{ const e=mine.find(x=>x.eid===r.getAttribute('data-eid')); return e?String(e.at):''; });
    ck('history: newest first', ats.every((a,i)=>i===0||ats[i-1]>=a), ats.join(' | '));
    ck('history: the count reads N entries', $('ms-hist-count').textContent===mine.length+' entr'+(mine.length===1?'y':'ies'),
       $('ms-hist-count').textContent);
    // N=3 editability: make one entry an earlier report's; it loses its pencil.
    const per=reportPeriodISO();
    while(msEntriesFor(keyA).length<3){
      $('ms-comment-text').value='P66 filler '+msEntriesFor(keyA).length; onMsCommentInput();
      saveMsDialog(false); await settle();
      // New remarks inside the merge window would merge; age the newest one.
      const L=msEntriesFor(keyA); L.forEach(e=>{ e.updatedAt=new Date(Date.now()-3600e3).toISOString(); });
    }
    const all3=msEntriesFor(keyA), old=all3[0];
    const oldPeriod=old.period; old.period='2000-01-02';
    renderMsHistory(); await settle();
    const pens=[...hist.querySelectorAll('.nh-entry')].filter(r=>r.querySelector('.nh-edit')).map(r=>r.getAttribute('data-eid'));
    ck('pencil: on every current-report entry and not on the earlier one',
       pens.length===all3.length-1&&pens.indexOf(old.eid)<0, pens.join(',')+' / old '+old.eid);
    const pen=hist.querySelector('.nh-entry .nh-edit'), pr=pen.getBoundingClientRect(),
          pil=pen.closest('.nh-entry').querySelector('.nh-fu').getBoundingClientRect();
    ck('pencil: sits right of the status pill', pr.left>=pil.right-1, pr.left+' vs '+pil.right);
    // Edit round trip through the store, with the newest entry.
    const tgt=pen.closest('.nh-entry').getAttribute('data-eid');
    pen.click(); await settle();
    const ta=hist.querySelector('.nh-ta'), sel=hist.querySelector('.nh-sel');
    ck('pencil: opens an editor with the entry text', !!ta&&!!sel, '');
    ta.value='P66 edited remark'; sel.value='sent';
    hist.querySelector('[data-act="save"]').click(); await settle(); await settle();
    const te=ENTRIES.find(e=>e.eid===tgt);
    ck('pencil: Save writes the entry (text and follow-up) and re-renders',
       te&&te.text==='P66 edited remark'&&te.status==='sent'&&/P66 edited remark/.test(hist.textContent)&&!dlg().hidden,
       te?te.text+'/'+te.status:'gone');
    ck('pencil: an edited latest remark is what the board reads', MS_COMMENTS[keyA]==='P66 edited remark', MS_COMMENTS[keyA]);
    old.period=oldPeriod; projectEntryStores();
    // Notes panel: the same gallery, grouped under a milestone heading.
    setWorkspaceSection&&setWorkspaceSection('notes'); NOTES_VIEW.coll='all'; renderNotes(); await settle();
    const grp=[...document.querySelectorAll('#notes-ms-groups .nh-group')].find(g=>(g.querySelector('.nh-gid')||{}).textContent===$('ms-code').textContent);
    ck('notes panel: a heading groups this milestone’s entries, with ID, count and roll-up line',
       !!grp&&grp.querySelector('.nh-gcount').textContent.indexOf(String(msEntriesFor(keyA).length))>=0&&!!grp.querySelector('.nh-gsum'),
       grp?grp.querySelector('.nh-ghead').textContent:'no group');
    grp.querySelector('.nh-gchev').click(); await settle();
    ck('notes panel: the group opens to the same entries, pencil included',
       grp.querySelectorAll('.nh-entry').length===msEntriesFor(keyA).length&&!!grp.querySelector('.nh-edit'), '');
    NOTES_VIEW.coll='current'; renderNotes();
    ck('drift: the card, pencil and panel flows adopted nothing', ENTRY_DRIFT_ADOPTED===0, ENTRY_DRIFT_ADOPTED);
    // A milestone with no entries shows the placeholder.
    discardMsDialog(); await settle();
    const bare=MILESTONES.find(m=>!msEntriesFor(msKeyFor(m)).length&&document.querySelector('.m-wrap[data-ms="'+msId(m)+'"]'));
    if(bare){ document.querySelector('.m-wrap[data-ms="'+msId(bare)+'"]').click(); await settle(); }
    ck('history: a milestone with no entries shows "No updates yet"', !!bare&&/No updates yet/.test($('ms-history').textContent),
       bare?msId(bare):'none found');
    discardMsDialog(); await settle();
    await open(A);
    const fold=$('ms-metrics-fold');
    ck('more fields: collapsed, holding the display label and the weight',
       !fold.open&&fold.contains($('ms-shorttitle-input'))&&fold.contains($('ms-weight'))&&
       /More fields/.test(fold.querySelector('summary').textContent), '');
    ck('meta line: "<Band> · <Type>" or the type alone, muted',
       $('ms-sub').textContent.indexOf(TYPE_LABELS[msFormType()])>=0, $('ms-sub').textContent);
    discardMsDialog(); await settle();

    emit();
  }catch(err){
    R.checks.push({name:'PROBE THREW',pass:false,detail:String(err&&err.message||err)});
    R.err=String(err&&err.stack||err);
    emit();
  }
})();
"""


def render(html_path, width, height):
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", "<script>\n" + PROBE + "\n</script>\n</body>")
    if out == page:
        sys.exit("Could not find </body> to inject into.")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p66.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=60000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found at {width}x{height}.\n" + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "src" / "milestone-dashboard.html"))
    args = ap.parse_args()
    html = pathlib.Path(args.html)
    src = html.read_text(encoding="utf-8", errors="replace")

    checks = []
    block = src[src.index('<div id="ms-dialog"'):src.index('<div id="print-filter-note"')]
    checks.append(("source: no em dash in the card markup", "—" not in block and "&mdash;" not in block, ""))
    checks.append(("source: exactly one </body>", src.count("</body>") == 1, str(src.count("</body>"))))
    checks.append(("source: exactly one version literal",
                   len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src)) == 1, ""))

    for (w, h) in VIEWPORTS:
        R = render(html, w, h)
        print(f"\n=== {w}x{h} ===  sample {R.get('notes', {}).get('sample')}")
        if R.get("err"):
            print(R["err"])
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

    fails = 0
    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
