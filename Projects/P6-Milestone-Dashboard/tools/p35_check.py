#!/usr/bin/env python3
"""
P35 check (TEST-37): the milestone card rework and the editable Progress field.

THE SHRINK. The card is 90% of its former width, with its vertical rhythm and
its two largest type steps taken down with it. Width is asserted against the
exact arithmetic (306 = 340 x 0.9) AND against the P34 release rendered in the
same browser at the same viewport on the SAME milestone, because a card whose
width shrank while its content grew taller is not a smaller card.

THE ROW. Start, Finish and Progress share one row, with a real column divider
between Finish and Progress, and all three values at one text size. Measured as
geometry (do the three boxes overlap vertically, is the divider's edge between
the two fields it separates) rather than by reading the CSS back, because a
declaration that is present says nothing about what laid out.

THE FOLD. Weight and the two hours figures are in a collapsible row, collapsed
on every open. "Collapsed by default" is asserted on a SECOND card opened after
the first was expanded, since a details element left open is the obvious way for
that claim to be true of the first card only.

THE OVERRIDE. Progress is annotation-layer state. Four things are asserted
together, and the third is the one the three-layer rule turns on:
  - the store takes the value and the .changed indicator shows it,
  - the row rollup and the tooltip move with it,
  - MILESTONES is byte-identical afterwards: the schedule record is never
    written, which is what makes "clearing restores the schedule's value"
    possible at all,
  - and the key the card writes is msKeyFor(m), the key every reader uses. The
    card used to compose its own from extractSnipId(notes) while msKeyFor
    prefers m.id. The divergence count on this dataset is reported, not assumed.

Every assertion that measures a set asserts its own sample size.

Usage:
  python3 tools/p35_check.py [--xlsx FILE] [--html FILE] [--baseline FILE]
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
from import_check import build_aoa, find_chrome  # noqa: E402

OUT_RE = re.compile(r'<pre id="p35-out">(.*?)</pre>', re.S)

# The same three widths P34 was run at. The card is width-capped, so one width
# cannot tell a cap that is being applied from a card that simply fits.
VIEWPORTS = [(390, 844), (768, 1024), (1440, 900)]

# Shared preamble: stub the CDN reader, kill transitions, import the workbook.
SETUP = r"""
  window.XLSX={
    read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
    utils:{ sheet_to_json:function(s){ return s.__aoa; } }
  };
  const st=document.createElement('style');
  st.textContent='*{transition:none!important;animation:none!important}';
  document.head.appendChild(st); void document.body.offsetWidth;
  PENDING_IMPORT_FILE='SNIP_29Aug26_export.xlsx';
  showMapper(Parse.workbook(new Uint8Array([0])));
  const dd=document.getElementById('cfg-datadate'); if(dd) dd.value='2026-08-29';
  await settle();
  runIngest();
  await settle(); await settle();
"""

# --------------------------------------------------------------------------
# Baseline probe: the P34 release, same viewport, same milestone. Returns the
# card's rect only. It must run against a build that has no #ms-progress-input,
# so it touches nothing the rework added.
# --------------------------------------------------------------------------
BASELINE = r"""
(async function(){
  const R={ok:false};
  function emit(){
    const o=document.createElement('pre'); o.id='p35-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  try{
""" + SETUP + r"""
    const wrap=Array.from(document.querySelectorAll('.m-wrap:not(.m-ghost)'))
      .filter(function(w){ return (w.getAttribute('data-tip')||'').indexOf('['+TARGET+']')>=0; })[0];
    if(!wrap) throw new Error('target '+TARGET+' not on the P34 board');
    wrap.dispatchEvent(new MouseEvent('click',{bubbles:true}));
    await settle();
    const dlg=document.getElementById('ms-dialog');
    const r=dlg.getBoundingClientRect();
    R.card={w:Math.round(r.width*10)/10,h:Math.round(r.height*10)/10,
            hidden:!!dlg.hidden};
    R.dateSize=parseFloat(getComputedStyle(document.getElementById('ms-date')).fontSize);
    const sd=document.getElementById('ms-start-date');
    R.startSize=sd?parseFloat(getComputedStyle(sd).fontSize):null;
    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=String(e&&e.stack); }
  emit();
})();
"""

# --------------------------------------------------------------------------
# The P35 probe.
# --------------------------------------------------------------------------
PROBE = r"""
(async function(){
  const R={checks:[],notes:{}};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p35-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  const rect=function(el){ const r=el.getBoundingClientRect();
    return {l:Math.round(r.left*10)/10,r:Math.round(r.right*10)/10,
            t:Math.round(r.top*10)/10,b:Math.round(r.bottom*10)/10,
            w:Math.round(r.width*10)/10,h:Math.round(r.height*10)/10}; };
  const size=function(id){ const el=document.getElementById(id);
    return el?parseFloat(getComputedStyle(el).fontSize):null; };
  // Drive the field the way a user does, so the commit path under test is the
  // one the markup actually wires up, not a direct call to saveMsProgress().
  function typeProgress(txt){
    const input=document.getElementById('ms-progress-input');
    input.focus();
    input.value=txt;
    input.dispatchEvent(new Event('input',{bubbles:true}));
  }
  // Committing moved from blur to the card's own Save control at P43: the card
  // is a form now, so leaving a field is no longer a decision to store what is
  // in it (close DISCARDS, which blur-to-commit would have made impossible).
  // Still driven as a user gesture, through the control the markup wires up,
  // rather than by calling saveMsDialog() directly.
  function commit(){
    const acts=document.getElementById('ms-save-actions');
    const btn=acts?acts.querySelector('.ms-act'):null;
    if(!btn) throw new Error('no save control on the card to commit with');
    btn.click();
  }
  function openCardFor(id){
    const wrap=Array.from(document.querySelectorAll('.m-wrap:not(.m-ghost)'))
      .filter(function(w){ return (w.getAttribute('data-tip')||'').indexOf('['+id+']')>=0; })[0];
    if(!wrap) return null;
    wrap.dispatchEvent(new MouseEvent('click',{bubbles:true}));
    return wrap;
  }
  const rowProg=function(ref){
    const tr=document.querySelector('tr[data-ref="'+CSS.escape(ref)+'"]');
    const td=tr?tr.querySelector('td.c-prog'):null;
    return td?td.textContent.trim():null;
  };

  try{
""" + SETUP + r"""
    R.notes.board={rows:document.querySelectorAll('#tbody tr.data').length,
                   markers:document.querySelectorAll('.m-wrap:not(.m-ghost)').length,
                   viewport:window.innerWidth+'x'+window.innerHeight};
    ck('setup: a board was built to measure',
       R.notes.board.rows>100&&R.notes.board.markers>100, JSON.stringify(R.notes.board));

    // ============ 0. The annotation key the card writes ====================
    // msKeyFor() prefers m.id; the card used to compose its own key from
    // extractSnipId(m.notes). Report how far apart they actually are on this
    // dataset rather than asserting they never differ.
    let diverged=0, keyed=0;
    MILESTONES.forEach(function(m){
      keyed++;
      const byNotes=extractSnipId(m.notes)||('noid-'+m.ref+m.type+m.date);
      if(msKeyFor(m)!==byNotes) diverged++;
    });
    R.notes.keys={milestones:keyed,idDiffersFromNotes:diverged};
    ck('key: every milestone was examined for an id/notes divergence',
       keyed>100, keyed+' milestones, '+diverged+' where msKeyFor differs from the notes id');

    // ============ 1. Pick a target the assertions can reason about =========
    // A row carrying exactly ONE weighted milestone, so its rollup cell is that
    // milestone's progress and an override has an unambiguous effect on it.
    let target=null;
    TASKS.forEach(function(t){
      if(target) return;
      const ms=getMilestones(t.ref).filter(function(m){
        return !(STATES[m.state]&&STATES[m.state].skipHours); });
      if(ms.length!==1) return;
      const m=ms[0];
      if(!m.weight||m.progress==null||m.progress>=100) return;
      if(!msId(m)) return;
      target={ref:t.ref,id:msId(m),progress:m.progress,weight:m.weight};
    });
    if(!target) throw new Error('no single-milestone row with a sub-100 progress');
    R.notes.target=target;
    R.target=target.id;

    const wrap=openCardFor(target.id);
    ck('card: the target milestone opens its card on click', !!wrap && !document.getElementById('ms-dialog').hidden,
       target.id+' on row '+target.ref);
    await settle();

    const dlg=document.getElementById('ms-dialog');
    R.notes.card=rect(dlg);
    R.card=R.notes.card;

    // ============ 2. The shrink ============================================
    const capped=Math.min(306,window.innerWidth-24);
    ck('shrink: the card renders at 90% of the old 340px cap',
       Math.abs(R.notes.card.w-capped)<=0.5, R.notes.card.w+'px against '+capped);

    // ============ 3. Start / Finish / Progress on one row ==================
    const startField=document.getElementById('ms-start-field');
    const startShown=startField&&getComputedStyle(startField).display!=='none';
    const fin=rect(document.getElementById('ms-date'));
    const prog=rect(document.getElementById('ms-progress-input'));
    const progField=document.getElementById('ms-prog-field')||
                    document.querySelector('.ms-prog-field');
    const pf=rect(progField);
    const boxes=[{n:'finish',r:fin},{n:'progress',r:prog}];
    if(startShown) boxes.unshift({n:'start',r:rect(document.getElementById('ms-start-date'))});
    R.notes.row={startShown:!!startShown,boxes:boxes};
    // One row means every box overlaps every other vertically. Comparing only
    // against the first would pass for a box that had dropped below the second.
    let notOverlapping=[];
    for(let i=0;i<boxes.length;i++) for(let j=i+1;j<boxes.length;j++){
      const a=boxes[i].r,b=boxes[j].r;
      if(!(a.t<b.b-0.5&&b.t<a.b-0.5)) notOverlapping.push(boxes[i].n+'/'+boxes[j].n);
    }
    ck('row: Start, Finish and Progress all sit on one row',
       boxes.length>=2&&notOverlapping.length===0,
       boxes.length+' fields shown, not sharing a row: '+(notOverlapping.join(', ')||'none'));
    ck('row: Progress is the right-hand field of that row',
       prog.l>fin.r, 'finish ends '+fin.r+', progress starts '+prog.l);

    // The divider, as geometry: a real left border on the Progress field whose
    // edge falls between Finish and Progress.
    const bw=parseFloat(getComputedStyle(progField).borderLeftWidth)||0;
    R.notes.divider={borderLeftWidth:bw,edge:pf.l,finishRight:fin.r,progressLeft:prog.l};
    ck('row: a column divider separates Finish from Progress',
       bw>0&&pf.l>=fin.r-0.5&&pf.l<=prog.l+0.5,
       bw+'px border at x='+pf.l+', between '+fin.r+' and '+prog.l);

    const sizes={finish:size('ms-date'),progress:size('ms-progress-input'),
                 start:startShown?size('ms-start-date'):null};
    R.notes.sizes=sizes;
    const shown=Object.keys(sizes).filter(function(k){ return sizes[k]!=null; });
    const equal=shown.every(function(k){ return Math.abs(sizes[k]-sizes.finish)<0.01; });
    ck('row: every value in that row is the same text size',
       shown.length>=2&&equal, shown.length+' values: '+JSON.stringify(sizes));

    // ============ 3b. The same row, with Start actually showing ============
    // The target above is a bare milestone, so its Start field is display:none
    // and the assertions in section 3 compared TWO boxes while claiming three.
    // A milestone that carries a real start date is opened here so the
    // three-field case is measured rather than assumed. Second time this
    // project has had a card assertion compare against a field that was not
    // being rendered (TEST-29).
    let withStart=null;
    MILESTONES.forEach(function(m){
      if(withStart) return;
      const real=(m.start&&fmtTipDate(m.start)!==fmtTipDate(m.date))||m.finishFromStart;
      if(real&&msId(m)) withStart=m;
    });
    if(withStart&&openCardFor(msId(withStart))){
      await settle();
      const sf=document.getElementById('ms-start-field');
      const three=[{n:'start',r:rect(document.getElementById('ms-start-date'))},
                   {n:'finish',r:rect(document.getElementById('ms-date'))},
                   {n:'progress',r:rect(document.getElementById('ms-progress-input'))}];
      const s3={start:size('ms-start-date'),finish:size('ms-date'),
                progress:size('ms-progress-input')};
      let split=[];
      for(let i=0;i<three.length;i++) for(let j=i+1;j<three.length;j++){
        const A=three[i].r,B=three[j].r;
        if(!(A.t<B.b-0.5&&B.t<A.b-0.5)) split.push(three[i].n+'/'+three[j].n);
      }
      R.notes.threeField={id:msId(withStart),startDisplay:getComputedStyle(sf).display,
                          boxes:three,sizes:s3};
      ck('row: with a real Start date, all THREE fields render and share the row',
         getComputedStyle(sf).display!=='none'&&three.every(function(b){ return b.r.h>0; })&&
         split.length===0,
         '3 boxes, not sharing a row: '+(split.join(', ')||'none'));
      ck('row: and all three are the same text size',
         s3.start===s3.finish&&s3.finish===s3.progress, JSON.stringify(s3));
      ck('row: left to right it reads Start, Finish, Progress',
         three[0].r.l<three[1].r.l&&three[1].r.r<three[2].r.l,
         three.map(function(b){ return b.n+'@'+b.r.l; }).join(' '));
      closeMsDialog(); await settle();
      openCardFor(target.id); await settle();
    } else {
      ck('row: a milestone carrying a real start date was found to measure', false,
         withStart?('no marker for '+msId(withStart)):'none in the dataset');
    }

    // ============ 4. The collapsible weight/hours row ======================
    // NOT getBoundingClientRect on the fields. Measured in this engine, a child
    // of a CLOSED <details> still reports a non-zero rect (checked against a
    // three-line page, for a plain div and for the display:grid this uses), so
    // a rect here would have been a measurement of nothing. checkVisibility()
    // does answer it, and the fold's own height is a second, independent read.
    const fold=document.getElementById('ms-metrics-fold');
    const metricIds=['ms-weight','ms-hours','ms-earned'];
    const vis=function(){ return metricIds.filter(function(id){
      const el=document.getElementById(id);
      return el&&el.checkVisibility&&el.checkVisibility(); }).length; };
    const openOnFirstCard=fold?fold.open:null;
    const shutVis=vis(), shutH=rect(fold).h;
    fold.open=true; await settle();
    const openVis=vis(), openH=rect(fold).h;
    R.notes.fold={present:!!fold,openOnFirstCard:openOnFirstCard,
                  visibleWhileShut:shutVis,visibleWhenOpen:openVis,
                  foldHeight:shutH+' -> '+openH};
    ck('fold: weight, MS hours and earned hours are in a collapsed row',
       !!fold&&openOnFirstCard===false&&shutVis===0&&shutH>0,
       '3 fields, '+shutVis+' visible while shut, open='+openOnFirstCard+', fold '+shutH+'px');
    ck('fold: opening it reveals all three, and the card grows to hold them',
       openVis===3&&openH>shutH,
       openVis+' of 3 visible, fold '+shutH+' -> '+openH+'px');

    // ============ 5. Editing Progress ======================================
    const key=msDialogFor;
    R.notes.dialogKey={msDialogFor:key,msKeyFor:msKeyFor(msDialogMs),
                       scheduleProgress:msDialogMs.progress};
    ck('key: the card writes under msKeyFor(m), the key every reader uses',
       key===msKeyFor(msDialogMs), key+' vs '+msKeyFor(msDialogMs));

    // A snapshot of the schedule record, taken BEFORE any edit. The three-layer
    // rule is the whole point of the store, so it is checked against a copy of
    // the data rather than against a re-read of the same object.
    const recordBefore=JSON.stringify(MILESTONES.map(function(m){
      return [msKeyFor(m),m.progress]; }));
    const rollupBefore=rowProg(target.ref);
    const markupBefore=MARKUP_COUNT;

    const wrapEl=document.getElementById('ms-prog-edit');
    typeProgress('45');
    ck('edit: typing a value that differs from the schedule marks the field edited',
       wrapEl.classList.contains('changed'),
       'classes '+wrapEl.className);
    commit(); await settle(); await settle();

    R.notes.afterEdit={stored:MS_PROGRESS_OVERRIDE[key],
                       effective:effectiveProgress(msDialogMs),
                       field:document.getElementById('ms-progress-input').value,
                       changed:wrapEl.classList.contains('changed'),
                       rollupBefore:rollupBefore,rollupAfter:rowProg(target.ref),
                       fill:document.getElementById('ms-progress-fill').style.width,
                       markupBefore:markupBefore,markupAfter:MARKUP_COUNT};
    ck('edit: the committed value is in the annotation store',
       MS_PROGRESS_OVERRIDE[key]===45, 'stored '+MS_PROGRESS_OVERRIDE[key]);
    ck('edit: and the field still shows it, still marked as an override',
       document.getElementById('ms-progress-input').value==='45'&&
       wrapEl.classList.contains('changed'),
       JSON.stringify(R.notes.afterEdit.field)+' changed='+R.notes.afterEdit.changed);
    ck('edit: the progress bar tracks the override',
       document.getElementById('ms-progress-fill').style.width==='45%',
       R.notes.afterEdit.fill);
    ck('edit: the row rollup moved with it',
       rollupBefore===target.progress+'%'&&rowProg(target.ref)==='45%',
       'row cell '+rollupBefore+' -> '+rowProg(target.ref));
    // Re-queried, not the handle captured before the edit. scheduleRerender
    // rebuilds every row, so the original wrap is a detached node still
    // carrying its pre-edit tooltip: reading it measured the old board.
    const liveWrap=document.querySelector(
      'tr[data-ref="'+CSS.escape(target.ref)+'"] .m-wrap:not(.m-ghost)');
    const tip=liveWrap?(liveWrap.getAttribute('data-tip')||''):'';
    R.notes.tip={detached:liveWrap===wrap,
                 line:String(tip).split('\n').filter(function(l){
                   return l.indexOf('Progress:')>=0; })[0]||''};
    ck('edit: the milestone tooltip reports the override, not the schedule value',
       !!liveWrap&&R.notes.tip.line.indexOf('Progress: 45%')>=0, JSON.stringify(R.notes.tip));
    ck('edit: it counts as markup, so the unsaved-changes state is honest',
       MARKUP_COUNT>markupBefore, markupBefore+' -> '+MARKUP_COUNT);

    // The three-layer rule.
    const recordAfter=JSON.stringify(MILESTONES.map(function(m){
      return [msKeyFor(m),m.progress]; }));
    R.notes.recordUnchanged=(recordBefore===recordAfter);
    ck('layers: not one milestone record was written (all '+MILESTONES.length+' compared)',
       recordBefore===recordAfter, recordBefore===recordAfter?'':'a record changed');

    // ---- committing an unchanged field must not add markup ---------------
    const markupIdle=MARKUP_COUNT;
    commit(); await settle();
    ck('edit: committing an unchanged field is a no-op',
       MARKUP_COUNT===markupIdle&&MS_PROGRESS_OVERRIDE[key]===45,
       'markup '+markupIdle+' -> '+MARKUP_COUNT);

    // ---- clearing restores the schedule's own value ----------------------
    typeProgress(''); commit(); await settle(); await settle();
    R.notes.afterClear={hasKey:(key in MS_PROGRESS_OVERRIDE),
                        field:document.getElementById('ms-progress-input').value,
                        changed:wrapEl.classList.contains('changed'),
                        rollup:rowProg(target.ref)};
    ck('clear: the override is removed rather than saved as a blank',
       !(key in MS_PROGRESS_OVERRIDE), JSON.stringify(R.notes.afterClear));
    ck('clear: the field shows the schedule’s own value again, unmarked',
       document.getElementById('ms-progress-input').value===String(target.progress)&&
       !wrapEl.classList.contains('changed'), JSON.stringify(R.notes.afterClear));
    ck('clear: and the row rollup goes back with it',
       rowProg(target.ref)===target.progress+'%', 'row cell '+rowProg(target.ref));

    // ---- a value equal to the schedule's own is not an override ----------
    typeProgress(String(target.progress)); commit(); await settle();
    ck('edit: entering the schedule’s own value leaves no override behind',
       !(key in MS_PROGRESS_OVERRIDE)&&!wrapEl.classList.contains('changed'),
       'key present: '+(key in MS_PROGRESS_OVERRIDE));

    // ---- both bounds, and a value that is not a number -------------------
    // Asserted on the EFFECTIVE value, not on the store. Clamping -5 gives 0,
    // and this target's schedule value is already 0, so the clamp correctly
    // leaves no override behind: reading the store here measured the
    // deduplication rule rather than the clamp it was aimed at.
    typeProgress('150'); commit(); await settle();
    const hi={eff:effectiveProgress(msDialogMs),stored:MS_PROGRESS_OVERRIDE[key]};
    typeProgress('-5'); commit(); await settle();
    const lo={eff:effectiveProgress(msDialogMs),stored:MS_PROGRESS_OVERRIDE[key]};
    typeProgress('abc'); commit(); await settle();
    const junk=(key in MS_PROGRESS_OVERRIDE);
    R.notes.bounds={above100:hi,below0:lo,scheduleValue:target.progress,
                    unparseableKept:junk};
    ck('bounds: over 100 shows 100 and under 0 shows 0',
       hi.eff===100&&lo.eff===0, JSON.stringify(R.notes.bounds));
    ck('bounds: text that is not a number restores the schedule value',
       !junk, 'override still present');

    // ============ 6. Marking complete ======================================
    // Needs a fresh card, because the health dots are read off msDialogFor.
    closeMsDialog(); await settle();
    openCardFor(target.id); await settle();
    const completeDot=document.querySelector('#ms-health-dots .health-dot[data-val="2"]');
    completeDot.dispatchEvent(new MouseEvent('click',{bubbles:true}));
    await settle();
    // The dot fills the Progress FIELD and marks the form dirty; it does not
    // reach the board until the card is saved. That changed at P43, when
    // health stopped being the one field that committed on click while
    // everything else waited, which was also the one field a discard could
    // not throw away. Asserted in both halves: pending first, then committed.
    const pending={field:document.getElementById('ms-progress-input').value,
                   rollup:rowProg(target.ref),
                   stored:MS_PROGRESS_OVERRIDE[msDialogFor]};
    ck('complete: the dot fills the field and waits for Save, storing nothing yet',
       pending.field==='100'&&pending.stored===undefined,
       JSON.stringify(pending));
    commit(); await settle(); await settle();
    R.notes.complete={pending:pending,stored:MS_PROGRESS_OVERRIDE[msDialogFor],
                      field:document.getElementById('ms-progress-input').value,
                      rollup:rowProg(target.ref)};
    ck('complete: marking the icon complete sets Progress to 100%',
       MS_PROGRESS_OVERRIDE[msDialogFor]===100&&
       document.getElementById('ms-progress-input').value==='100',
       JSON.stringify(R.notes.complete));
    ck('complete: and the row it sits on follows',
       rowProg(target.ref)==='100%', 'row cell '+rowProg(target.ref));

    // A milestone the schedule already has at 100 must not gain an override
    // that changes nothing, or the count a reader is shown is inflated.
    let done=null;
    MILESTONES.forEach(function(m){
      if(done) return;
      if(m.progress===100&&msId(m)&&!(STATES[m.state]&&STATES[m.state].skipHours)) done=m;
    });
    if(done){
      closeMsDialog(); await settle();
      const w2=openCardFor(msId(done));
      if(w2){
        await settle();
        const k2=msDialogFor;
        document.querySelector('#ms-health-dots .health-dot[data-val="2"]')
          .dispatchEvent(new MouseEvent('click',{bubbles:true}));
        await settle();
        R.notes.completeNoop={id:msId(done),keyAdded:(k2 in MS_PROGRESS_OVERRIDE)};
        ck('complete: a milestone already at 100% gains no redundant override',
           !(k2 in MS_PROGRESS_OVERRIDE), JSON.stringify(R.notes.completeNoop));
      } else {
        ck('complete: a milestone already at 100% was found on the board', false,
           'no marker for '+msId(done));
      }
    } else {
      ck('complete: the board carries a milestone already at 100%', false,
         'none found, so the no-op case is untested');
    }

    // ============ 7. The fold is collapsed on the NEXT card too ============
    closeMsDialog(); await settle();
    openCardFor(target.id); await settle();
    R.notes.foldReopened=document.getElementById('ms-metrics-fold').open;
    ck('fold: it is collapsed again on the next card, not left where it was',
       document.getElementById('ms-metrics-fold').open===false,
       'open='+R.notes.foldReopened);

    // ============ 8. Round trip through the real payloads ==================
    // Category wiring only; persist_check.py drives the files themselves.
    typeProgress('63'); commit(); await settle();
    const cat=ANNOT_CATEGORIES.filter(function(c){ return c.key==='msProgress'; })[0];
    const payload={milestoneProgressOverrides:{}};
    payload.milestoneProgressOverrides[msDialogFor]=63;
    R.notes.category={present:!!cat,count:cat?cat.count(payload):null,
                      label:cat?cat.label:null};
    ck('payload: progress overrides are their own selectable annotation category',
       !!cat&&cat.count(payload)===1, JSON.stringify(R.notes.category));

    R.ok=true;
  }catch(e){ R.ok=false; R.err=String(e); R.stack=String(e&&e.stack); }
  emit();
})();
"""


def render(html_path, script, consts, width, height, tag):
    inject = "<script>" + consts + "</script>\n<script>\n" + script + "\n</script>\n"
    page = html_path.read_text(encoding="utf-8", errors="replace")
    out = page.replace("</body>", inject + "</body>")
    if out == page:
        sys.exit(f"Could not find </body> to inject into ({html_path}).")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p35.html"
        tmp.write_text(out, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             f"--window-size={width},{height}", "--virtual-time-budget=90000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit(f"Probe output not found for {tag} at {width}x{height}.\n"
                 + proc.stderr[-3000:])
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=str(root / "data" / "schedules" /
                                          "103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx"))
    ap.add_argument("--html", default=str(root / "src" / "milestone-dashboard.html"))
    ap.add_argument("--baseline", default=str(root / "releases" /
                                             "v3.1.0-P34_marker-anchoring-and-compact-header.html"))
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    html = pathlib.Path(a.html)
    baseline = pathlib.Path(a.baseline)
    aoa_const = "const AOA=" + json.dumps(aoa) + ";"

    # Source-level assertions. A literal that happens to be right measures as
    # correct, so the literals that were removed are checked in the source.
    src = html.read_text(encoding="utf-8", errors="replace")
    checks = []
    vers = len(re.findall(r"3\.[0-9]+\.[0-9]+-P", src))
    checks.append(("source: exactly one version literal", vers == 1, f"{vers} found"))
    # Scoped to the .ms-dialog rule. The bare substring test failed at
    # v3.1.0-P40 on an unrelated dialog added elsewhere in the stylesheet, which
    # is a false positive: this assertion is about the milestone card's own cap,
    # not about the string 340px appearing anywhere in a 10,000 line file.
    ms_rule = ""
    m = re.search(r"\.ms-dialog\{([^}]*)\}", src)
    if m:
        ms_rule = m.group(1)
    checks.append(("source: the card's width cap is 90% of the old 340px",
                   "width:min(306px," in ms_rule and "width:min(340px," not in ms_rule,
                   f"the .ms-dialog rule reads: {ms_rule[:80]!r}"))
    checks.append(("source: the rollup reads effectiveProgress, not the record",
                   "m.weight*(effectiveProgress(m)||0)" in src
                   and "m.weight*(m.progress||0)" not in src,
                   "a rollup still reads m.progress directly"))
    checks.append(("source: the tooltip reads effectiveProgress too",
                   "'|   Progress: '+(m.progress||0)" not in src,
                   "the tooltip still reads m.progress directly"))
    # The one thing a runtime probe cannot prove about code it never reached.
    writes = re.findall(r"\bm\.progress\s*=[^=]", src) + \
        re.findall(r"msDialogMs\.progress\s*=[^=]", src)
    checks.append(("source: nothing assigns to a milestone's progress",
                   not writes, f"{len(writes)} assignment(s) found"))
    for field in ("milestoneProgressOverrides",):
        n = src.count(field)
        # publish payload, applyPublishedState, exportModel, and the category's
        # count + apply. Fewer than five means one of the paths was missed.
        checks.append((f"source: {field} reaches every payload path",
                       n >= 5, f"{n} occurrences"))

    fails = 0
    for (w, h) in VIEWPORTS:
        R = render(html, PROBE, aoa_const, w, h, "P35")
        if not R.get("ok"):
            print(f"PROBE FAILED at {w}x{h}: {R.get('err')}")
            print(R.get("stack", ""))
            return 1
        n = R.get("notes", {})
        print(f"\n=== {w}x{h} ===")
        for k in ("board", "keys", "target", "card", "sizes", "divider",
                  "threeField", "fold", "dialogKey", "afterEdit", "afterClear",
                  "bounds", "complete", "completeNoop", "tip", "category"):
            if k in n:
                print(f"   {k}: {json.dumps(n[k])}")
        for c in R["checks"]:
            checks.append((f"[{w}x{h}] " + c["name"], c["pass"], c["detail"]))

        # The before/after the shrink claim needs: the P34 release, same
        # browser, same viewport, same milestone.
        if baseline.exists():
            B = render(baseline, BASELINE, aoa_const +
                       "const TARGET=" + json.dumps(R["target"]) + ";", w, h, "P34")
            if not B.get("ok"):
                checks.append((f"[{w}x{h}] shrink: the P34 card was measured to compare against",
                               False, str(B.get("err"))))
            else:
                b, c = B["card"], R["card"]
                dw = 100.0 * (b["w"] - c["w"]) / b["w"]
                dh = 100.0 * (b["h"] - c["h"]) / b["h"]
                print("   P34 card: %sx%s   P35 card: %sx%s   (-%.1f%% wide, -%.1f%% tall)"
                      % (b["w"], b["h"], c["w"], c["h"], dw, dh))
                print("   P34 finish/start text: %s / %s px" % (B["dateSize"], B["startSize"]))
                checks.append((f"[{w}x{h}] shrink: narrower than the P34 card, by about a tenth",
                               8.0 <= dw <= 12.0, "%.1f%% (%s -> %s)" % (dw, b["w"], c["w"])))
                checks.append((f"[{w}x{h}] shrink: and no taller, so the card really is smaller",
                               dh >= 0, "%.1f%% (%s -> %s)" % (dh, b["h"], c["h"])))
                checks.append((f"[{w}x{h}] row: P34's two date sizes really did differ",
                               B["startSize"] is not None and B["dateSize"] != B["startSize"],
                               f"{B['dateSize']} vs {B['startSize']}"))
        else:
            checks.append((f"[{w}x{h}] shrink: the P34 release was available to compare against",
                           False, f"missing {baseline}"))

    print()
    for name, ok, detail in checks:
        if not ok:
            fails += 1
        print(("  ok   " if ok else "  FAIL ") + name + (f"   [{detail}]" if detail else ""))
    print(f"\n{len(checks) - fails}/{len(checks)} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
