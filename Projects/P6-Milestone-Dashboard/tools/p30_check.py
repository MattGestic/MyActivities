#!/usr/bin/env python3
"""
P30 check (TEST-33): multi-source ingest, Half 1.

The board can now be built from more than one schedule. Three things have to
hold, and only one of them is about the feature working at all:

  IDENTITY. Every row and every milestone records the schedule it came from,
  that name defaults from the file, it is editable afterwards, and it reaches
  the Source Schedule column and the Source filter. A filter that narrows is
  only half the assertion: nothing outside the selection may survive AND
  nothing inside it may be hidden, or hiding everything would pass.

  APPEND WITHOUT COLLISION. This check appends the SAME workbook to itself,
  so every single Activity ID collides. That is deliberate: it is the worst
  case, it is easy to get wrong quietly, and the cost of getting it wrong is
  not a cosmetic duplicate but two schedules silently sharing annotations and
  merging milestones onto one row. The suffix has to reach m.id, m.notes,
  m.ref, t.ref, t.src and the row's data-ids together, and an annotation keyed
  on a suffixed ID has to resolve to the right milestone.

  NOTHING ELSE MOVED. A single-source import must produce exactly the board it
  produced at P29.

The performance work is checked by COUNTING, not by timing. Chromium's
--virtual-time-budget, which every probe in this project runs under, does not
advance performance.now() with real work: the first version of this file
reported 0ms against every budget and would have gone on reporting 0ms however
slow the code became. So the assertions are the things the optimisations
actually promise -- one index build per rebuild reused across every lookup, one
filter pass per burst of typing rather than one per keystroke, and column
hiding through a generated stylesheet instead of a style write per cell.

Usage:
  python3 tools/p30_check.py [--xlsx FILE] [--html FILE]
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

OUT_RE = re.compile(r'<pre id="p30-out">(.*?)</pre>', re.S)

# One import of the reference workbook, unchanged from P29. Appending it to
# itself must produce exactly twice these.
ONE = {"tasks": 105, "milestones": 146}

PROBE = r"""
(async function(){
  const R={checks:[],notes:{},timings:{}};
  function ck(name,pass,detail){ R.checks.push({name:name,pass:!!pass,detail:detail===undefined?'':String(detail)}); }
  function emit(){
    const o=document.createElement('pre'); o.id='p30-out';
    o.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(R))));
    document.body.appendChild(o);
  }
  const settle=function(){ return new Promise(function(r){ setTimeout(r,250); }); };
  function freeze(){
    const s=document.createElement('style');
    s.textContent='*{transition:none!important;animation:none!important}';
    document.head.appendChild(s); void document.body.offsetWidth;
  }
  const rowsOnBoard=function(){ return Array.from(document.querySelectorAll('tr[data-type="row"]')); };
  const visibleRows=function(){ return rowsOnBoard().filter(function(r){ return !r.classList.contains('hidden-row'); }); };
  // Contiguous RUNS of one band, in board order. De-duplicating by name was
  // wrong here: appending a schedule to itself produces the same 14 band names
  // twice, so a distinct-name count says 14 whether the two schedules sit one
  // after the other or are interleaved row by row. The run sequence is what
  // actually distinguishes those two outcomes.
  const bandRuns=function(){
    const runs=[]; let last=null;
    rowsOnBoard().forEach(function(r){
      const b=r.getAttribute('data-band')||'';
      if(b!==last){ runs.push(b); last=b; }
    });
    return runs;
  };
  function openMapper(file){
    PENDING_IMPORT_FILE=file;
    showMapper(Parse.workbook(new Uint8Array([0])));
    const dd=document.getElementById('cfg-datadate'); if(dd) dd.value='2026-08-29';
  }

  try{
    window.XLSX={
      read:function(){ return {SheetNames:['TASK'],Sheets:{TASK:{__aoa:AOA}}}; },
      utils:{ sheet_to_json:function(s){ return s.__aoa; } }
    };
    freeze();

    // ================= 1. Source identity on one import =================
    openMapper('SNIP_29Aug26_export.xlsx');
    await settle();
    const nameField=document.getElementById('cfg-source-name');
    R.notes.defaultSourceName=nameField?nameField.value:null;
    ck('setup: the source step appears once a file is parsed',
       getComputedStyle(document.getElementById('source-wrap-section')).display!=='none');
    ck('setup: the source name defaults from the file name, without its extension',
       R.notes.defaultSourceName==='SNIP_29Aug26_export', R.notes.defaultSourceName);
    ck('setup: the mode question is not asked when there is nothing to append to',
       document.getElementById('source-mode-row').hidden===true);

    // Edited before Import, which is the point of the field.
    nameField.value='Schedule A';
    DIAG=[]; runIngest();
    await settle();

    R.notes.oneSource={tasks:UPDATE_TASKS.length,milestones:UPDATE_MILESTONES.length,
                       registry:PRIMARY_SOURCES.length};
    ck('identity: one source is registered', PRIMARY_SOURCES.length===1, PRIMARY_SOURCES.length);
    ck('identity: the registry took the edited name, not the file name',
       PRIMARY_SOURCES[0].name==='Schedule A', PRIMARY_SOURCES[0].name);

    const msNoSrc=UPDATE_MILESTONES.filter(function(m){ return !m.source; });
    const tkNoSrc=UPDATE_TASKS.filter(function(t){ return !t.sourceSchedule; });
    ck('identity: there are milestones to check', UPDATE_MILESTONES.length>100, UPDATE_MILESTONES.length);
    ck('identity: every milestone records its source', msNoSrc.length===0, msNoSrc.length+' without');
    ck('identity: every row records its source', tkNoSrc.length===0, tkNoSrc.length+' without');
    ck('identity: the source name is not confused with task.src',
       UPDATE_TASKS[0].src!==UPDATE_TASKS[0].sourceSchedule,
       String(UPDATE_TASKS[0].src).slice(0,24)+' vs '+UPDATE_TASKS[0].sourceSchedule);

    // The column carries it.
    const srcSchCells=Array.from(document.querySelectorAll('tr[data-type="row"] td.c-srcsch'));
    const filled=srcSchCells.filter(function(td){ return td.textContent.trim()==='Schedule A'; });
    R.notes.srcSchCells=srcSchCells.length;
    ck('column: there are Source Schedule cells to measure', srcSchCells.length>50, srcSchCells.length);
    ck('column: every Source Schedule cell names the source',
       filled.length===srcSchCells.length, filled.length+' of '+srcSchCells.length);
    // Column count has to match the header, or every cell after it is offset.
    const hdrCells=document.querySelectorAll('#week-hdr th').length;
    const bodyCells=document.querySelector('tr[data-type="row"]').querySelectorAll('td').length;
    R.notes.hdrCells=hdrCells; R.notes.bodyCells=bodyCells;
    ck('column: header and body cell counts agree', hdrCells===bodyCells, hdrCells+' vs '+bodyCells);

    // One source, so the filter is noise and hides itself.
    ck('filter: the source filter is hidden while only one source is mounted',
       getComputedStyle(document.getElementById('filter-source').closest('.tfb-group')).display==='none');

    const oneBands=bandRuns();
    const oneRows=rowsOnBoard().length;
    R.notes.oneBands=oneBands.length; R.notes.oneRows=oneRows;

    // ================= 2. Append the same workbook to itself =================
    openMapper('SNIP_29Aug26_export.xlsx');
    await settle();
    ck('append: the mode question appears once something is mounted',
       document.getElementById('source-mode-row').hidden===false);
    document.getElementById('cfg-source-name').value='Schedule B';
    document.getElementById('src-mode-append').checked=true;
    const tAppend0=performance.now();
    DIAG=[]; runIngest();
    R.timings.ingestAppend=Math.round(performance.now()-tAppend0);
    await settle(); await settle();

    R.notes.twoSource={tasks:UPDATE_TASKS.length,milestones:UPDATE_MILESTONES.length,
                       registry:PRIMARY_SOURCES.length,names:PRIMARY_SOURCES.map(function(s){return s.name;})};
    ck('append: both sources are registered', PRIMARY_SOURCES.length===2,
       PRIMARY_SOURCES.map(function(s){return s.name;}).join(', '));
    ck('append: the board holds both schedules',
       UPDATE_TASKS.length===TASK_ONE*2 && UPDATE_MILESTONES.length===MS_ONE*2,
       UPDATE_TASKS.length+' tasks / '+UPDATE_MILESTONES.length+' milestones');
    ck('append: TASKS and MILESTONES were re-sliced from the registry',
       TASKS.length===UPDATE_TASKS.length && MILESTONES.length===UPDATE_MILESTONES.length,
       TASKS.length+' / '+MILESTONES.length);

    // Band order: the first schedule's bands, in their original order, then
    // the second's. Interleaving would mean the per-call sort had leaked.
    const twoBands=bandRuns();
    const headMatches=oneBands.every(function(b,i){ return twoBands[i]===b; });
    R.notes.bandsOne=oneBands.length; R.notes.bandsTwo=twoBands.length;
    ck('append: the first schedule keeps its own band order',
       headMatches, twoBands.slice(0,3).join(' | '));
    const tailMatches=oneBands.every(function(b,i){ return twoBands[oneBands.length+i]===b; });
    ck('append: the second schedule adds its bands below rather than interleaving',
       twoBands.length===oneBands.length*2 && tailMatches,
       twoBands.length+' runs vs '+(oneBands.length*2)+' expected');

    // ---- duplicate IDs -------------------------------------------------
    // The same workbook twice, so every Activity ID collides.
    const ids=UPDATE_MILESTONES.map(function(m){ return msId(m); }).filter(Boolean);
    const uniq=new Set(ids);
    R.notes.idCount=ids.length; R.notes.idUnique=uniq.size;
    ck('dedupe: every milestone still has an id', ids.length===UPDATE_MILESTONES.length,
       ids.length+' of '+UPDATE_MILESTONES.length);
    ck('dedupe: no two milestones share an Activity ID',
       uniq.size===ids.length, (ids.length-uniq.size)+' duplicated');
    const suffixedIds=ids.filter(function(i){ return /_\d+$/.test(i); });
    R.notes.suffixed=suffixedIds.length;
    ck('dedupe: the second schedule was suffixed, and every one of its ids was',
       suffixedIds.length===MS_ONE, suffixedIds.length+' of '+MS_ONE);
    const refs=UPDATE_TASKS.map(function(t){ return t.ref; });
    ck('dedupe: no two rows share a ref', new Set(refs).size===refs.length,
       (refs.length-new Set(refs).size)+' duplicated');

    // The suffix has to land in every field that carries the id, together.
    const drift=[];
    UPDATE_MILESTONES.forEach(function(m){
      const id=msId(m);
      if(!/_\d+$/.test(id)) return;
      const fromNotes=extractSnipId(m.notes);
      if(fromNotes!==id) drift.push('notes '+fromNotes+' vs id '+id);
    });
    R.notes.drift=drift.slice(0,6);
    ck('dedupe: there were suffixed milestones to check', suffixedIds.length>0, suffixedIds.length);
    ck('dedupe: m.notes carries the same id as m.id', drift.length===0, drift.slice(0,3).join('; '));
    // data-ids is re-derived from the milestones at render time.
    const rowIdSet=new Set();
    rowsOnBoard().forEach(function(r){
      (r.getAttribute('data-ids')||'').split(',').filter(Boolean).forEach(function(i){ rowIdSet.add(i); });
    });
    const missingOnBoard=ids.filter(function(i){ return !rowIdSet.has(i); });
    R.notes.rowIdCount=rowIdSet.size;
    ck('dedupe: every suffixed id reaches the row it belongs to',
       missingOnBoard.length===0, missingOnBoard.slice(0,4).join(', '));
    // task.src is the Source Activity IDs cell; it must have been rewritten too.
    const srcDrift=UPDATE_TASKS.filter(function(t){
      return String(t.src||'').split(',').some(function(x){
        const id=x.trim();
        return id && !uniq.has(id);
      });
    });
    ck('dedupe: Source Activity IDs cells name ids that exist',
       srcDrift.length===0, srcDrift.length+' rows naming a missing id');

    // An annotation keyed on a suffixed id must reach that milestone and not
    // its unsuffixed twin. This is the whole reason the suffix exists.
    const twin=UPDATE_MILESTONES.filter(function(m){ return /_1$/.test(msId(m)); })[0];
    const baseId=twin?msId(twin).replace(/_1$/,''):null;
    const original=baseId?findMilestoneBySnip(baseId):null;
    MS_COMMENTS[msKeyFor(twin)]='note on the appended copy';
    R.notes.twinId=twin?msId(twin):null;
    ck('dedupe: a suffixed milestone and its twin both resolve', !!twin&&!!original&&twin!==original,
       (twin?msId(twin):'none')+' vs '+(original?msId(original):'none'));
    ck('dedupe: an annotation on the suffixed copy does not land on the original',
       !!twin&&!!original&&MS_COMMENTS[msKeyFor(twin)]==='note on the appended copy'&&
       MS_COMMENTS[msKeyFor(original)]===undefined,
       'twin='+(twin?msKeyFor(twin):'?')+' original='+(original?msKeyFor(original):'?'));
    delete MS_COMMENTS[msKeyFor(twin)];

    // ================= 3. The source filter =================
    const fs=document.getElementById('filter-source');
    ck('filter: the source filter is shown once there are two sources',
       getComputedStyle(fs.closest('.tfb-group')).display!=='none');
    const opts=Array.from(fs.options).map(function(o){ return o.value; });
    R.notes.filterOptions=opts;
    ck('filter: it offers both sources and an all option',
       opts.length===3 && opts.indexOf('Schedule A')>0 && opts.indexOf('Schedule B')>0, opts.join(' | '));
    fs.value='Schedule B'; applyFilter();
    const shownB=visibleRows();
    const wrongIn=shownB.filter(function(r){ return r.getAttribute('data-source')!=='Schedule B'; });
    const hiddenOut=rowsOnBoard().filter(function(r){
      return r.getAttribute('data-source')==='Schedule B' && r.classList.contains('hidden-row');
    });
    R.notes.filteredRows=shownB.length;
    ck('filter: it narrows to something', shownB.length>0 && shownB.length<rowsOnBoard().length,
       shownB.length+' of '+rowsOnBoard().length);
    ck('filter: nothing outside the selected source survives', wrongIn.length===0, wrongIn.length);
    ck('filter: nothing inside the selected source is hidden', hiddenOut.length===0, hiddenOut.length);
    ck('filter: the summary line names the source',
       /source = Schedule B/.test(document.getElementById('filter-info').textContent),
       document.getElementById('filter-info').textContent.slice(0,90));
    clearFilter();
    ck('filter: clearing it restores every row', visibleRows().length===rowsOnBoard().length,
       visibleRows().length+' of '+rowsOnBoard().length);
    // It has to survive a rebuild, which is where the band filter once did not.
    fs.value='Schedule A'; applyFilter();
    scheduleRerender(true); await settle(); await settle();
    ck('filter: the source selection survives a full rebuild',
       document.getElementById('filter-source').value==='Schedule A',
       document.getElementById('filter-source').value);
    clearFilter();
    await settle();

    // ================= 4. Rename after the fact =================
    const b=PRIMARY_SOURCES[1];
    b.name='Client target';
    b.tasks.forEach(function(t){ t.sourceSchedule='Client target'; });
    b.milestones.forEach(function(m){ m.source='Client target'; });
    scheduleRerender(true); await settle(); await settle();
    const renamed=rowsOnBoard().filter(function(r){ return r.getAttribute('data-source')==='Client target'; });
    ck('rename: renaming a source restamps its rows', renamed.length===oneRows,
       renamed.length+' of '+oneRows);
    ck('rename: the filter picks the new name up',
       Array.from(document.getElementById('filter-source').options)
            .map(function(o){return o.value;}).indexOf('Client target')>0);

    // ================= 5. Publish round trip =================
    const payload=publishStatePayload();
    R.notes.publishedSources=(payload.sources||[]).map(function(s){ return s.name+':'+s.milestones; });
    ck('publish: the payload carries one entry per source',
       (payload.sources||[]).length===2, R.notes.publishedSources.join(' | '));
    ck('publish: the row data still carries its own source name',
       (payload.milestones||[]).every(function(m){ return !!m.source; }));
    // Restore it over the live board, which is what a published file does.
    restorePrimarySources(JSON.parse(JSON.stringify(payload)));
    R.notes.restored=PRIMARY_SOURCES.map(function(s){ return s.name+':'+s.milestones.length; });
    ck('publish: the registry comes back with both sources',
       PRIMARY_SOURCES.length===2, R.notes.restored.join(' | '));
    ck('publish: each source keeps its own rows',
       PRIMARY_SOURCES[0].milestones.length===MS_ONE && PRIMARY_SOURCES[1].milestones.length===MS_ONE,
       R.notes.restored.join(' | '));
    ck('publish: the concatenation is unchanged',
       UPDATE_MILESTONES.length===MS_ONE*2 && UPDATE_TASKS.length===TASK_ONE*2,
       UPDATE_TASKS.length+' / '+UPDATE_MILESTONES.length);

    // ================= 6. setViewMode does not drop appended data =========
    TASKS=UPDATE_TASKS.slice(); MILESTONES=UPDATE_MILESTONES.slice(); invalidateMsIndexes();
    VIEW_MODE='update';
    setViewMode('baseline'); await settle();
    const baseCount=MILESTONES.length;
    setViewMode('update'); await settle(); await settle();
    R.notes.afterViewSwitch={baseline:baseCount,update:MILESTONES.length};
    ck('view switch: the baseline is still the embedded one', baseCount===198, baseCount);
    ck('view switch: both appended sources survive a round trip to baseline',
       MILESTONES.length===MS_ONE*2 && TASKS.length===TASK_ONE*2,
       TASKS.length+' / '+MILESTONES.length);

    // ================= 7. The performance work, counted not timed ==========
    // performance.now() does not advance usefully under Chromium's
    // --virtual-time-budget, which is how every probe in this project runs: an
    // earlier version of this block reported 0ms against every budget and
    // would have gone on "passing" whatever the code did. So the optimisations
    // are held by what they actually promise: one index build per rebuild,
    // one filter pass per burst of typing, and no per-cell style writes.
    rerender(true);
    await settle();

    // getMilestones() used to filter the whole of MILESTONES once per row.
    // If the index is live, 300 calls share one object; if it is not, each
    // call rebuilds and the identity changes.
    const idx1=msByRefIndex();
    for(let i=0;i<300;i++) getMilestones('SNIP-101');
    const idx2=msByRefIndex();
    ck('perf: the ref index is built once and reused, not per call',
       idx1===idx2 && !!idx1, idx1===idx2?'same object across 300 calls':'rebuilt');
    ck('perf: the ref index actually indexes the appended board',
       Object.keys(idx1).length===TASK_ONE*2, Object.keys(idx1).length+' refs');
    // ...and a rebuild must drop it, or the board would render stale rows.
    invalidateMsIndexes();
    ck('perf: invalidating drops the index rather than serving a stale one',
       msByRefIndex()!==idx1);

    R.notes.idListLength=allMilestoneIds().length;
    const list1=allMilestoneIds();
    for(let i=0;i<50;i++) allMilestoneIds();
    ck('perf: the cached id list is the full set and is served from cache',
       list1.length===MS_ONE*2 && allMilestoneIds()===list1,
       R.notes.idListLength+' ids, identity '+(allMilestoneIds()===list1?'stable':'rebuilt'));

    // The date range used to write an inline display to every week cell in
    // every row. It is a generated stylesheet now, so no cell should carry one.
    document.getElementById('filter-date-from').value='2026-07-01';
    document.getElementById('filter-date-to').value='2026-08-31';
    applyFilter();
    await settle();
    const styleEl=document.getElementById('range-col-style');
    const inlineHidden=Array.from(document.querySelectorAll('td.col-wk[data-col]'))
      .filter(function(td){ return (td.getAttribute('style')||'').indexOf('display')>=0; });
    const hiddenCols=Array.from(document.querySelectorAll('#week-hdr th.col-wk[data-col]'))
      .filter(function(th){ return getComputedStyle(th).display==='none'; });
    R.notes.rangeStyleRules=styleEl?(styleEl.textContent.match(/\n/g)||[]).length:0;
    R.notes.inlineHiddenCells=inlineHidden.length;
    R.notes.hiddenCols=hiddenCols.length;
    ck('perf: the range filter hid some columns', hiddenCols.length>0, hiddenCols.length+' hidden');
    ck('perf: it hid them through a stylesheet, not a write per cell',
       !!styleEl && styleEl.textContent.length>0 && inlineHidden.length===0,
       (styleEl?R.notes.rangeStyleRules+' rules':'no stylesheet')+', '+inlineHidden.length+' inline writes');
    document.getElementById('filter-date-from').value='';
    document.getElementById('filter-date-to').value='';
    applyFilter();
    await settle();
    const stillHidden=Array.from(document.querySelectorAll('#week-hdr th.col-wk[data-col]'))
      .filter(function(th){ return getComputedStyle(th).display==='none'; });
    ck('perf: clearing the range puts every column back', stillHidden.length===0, stillHidden.length+' still hidden');

    // The two keystroke paths are debounced, so typing must not run the filter
    // synchronously. Asserted by counting real calls, not by reading the code.
    const realApply=applyFilter;
    let calls=0;
    applyFilter=function(){ calls++; return realApply.apply(this,arguments); };
    const tf=document.getElementById('filter-title');
    ['d','de','des','desi','desig','design'].forEach(function(v){
      tf.value=v; onTitleFilterInput(tf);
    });
    const immediate=calls;
    await settle();
    const afterSettle=calls;
    applyFilter=realApply;
    tf.value=''; applyFilter();
    R.notes.debounce={immediate:immediate,afterSettle:afterSettle};
    ck('perf: six keystrokes do not run six filter passes',
       immediate===0, immediate+' synchronous calls');
    ck('perf: the filter still runs once the typing stops',
       afterSettle===1, afterSettle+' call(s) after settle');

    // ================= 8. Dependency lines under a filter =================
    // Reported from the field: "All on" drew nothing. The lines were being
    // drawn, but markerCenter() measured markers whose row or week column the
    // filter had hidden. Those elements are still in the DOM and still answer
    // querySelector; they just have a zero rect, so every one of them resolved
    // to the SAME point at the board's top-left corner. Measured at 308 of 331
    // paths collapsed to zero size under a week plus date-range filter, which
    // is indistinguishable from "the feature is broken".
    clearFilter(); await settle();
    setAllDep('pred',true); await settle();
    const zeroSized=function(){
      return Array.from(document.querySelectorAll('#dep-lines-g path.dep-line'))
        .filter(function(pth){ const r=pth.getBoundingClientRect();
          return r.width<0.5&&r.height<0.5; }).length;
    };
    const pathCount=function(){ return document.querySelectorAll('#dep-lines-g path.dep-line').length; };
    R.notes.depUnfiltered={paths:pathCount(),zero:zeroSized()};
    ck('deps: there are dependency lines to measure', pathCount()>50, pathCount());
    ck('deps: no line is zero-sized with no filter', zeroSized()===0, zeroSized());

    document.getElementById('filter-date-from').value='2026-09-01';
    applyFilter(); await settle(); await settle();
    R.notes.depWithRange={paths:pathCount(),zero:zeroSized()};
    ck('deps: a date range does not collapse lines onto the board corner',
       zeroSized()===0, zeroSized()+' of '+pathCount()+' zero-sized');
    // applyFilter() is the choke point every filter goes through, so the lines
    // must already have been redrawn by the time it returns. Without that they
    // stayed frozen wherever the markers used to be.
    ck('deps: the filter redrew the lines rather than leaving them stale',
       pathCount()<R.notes.depUnfiltered.paths,
       pathCount()+' after vs '+R.notes.depUnfiltered.paths+' before');

    document.getElementById('week-filter').value='5';
    document.getElementById('filter-mode').value='week-plus4';
    applyFilter(); await settle(); await settle();
    R.notes.depWithWeek={paths:pathCount(),zero:zeroSized(),
      rows:document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)').length};
    ck('deps: with everything filtered out, no line is drawn at all rather than piled in the corner',
       zeroSized()===0, zeroSized()+' of '+pathCount()+' zero-sized');

    clearFilter(); await settle(); await settle();
    R.notes.depAfterClear={paths:pathCount(),zero:zeroSized()};
    ck('deps: clearing the filter brings every line back',
       pathCount()===R.notes.depUnfiltered.paths && zeroSized()===0,
       pathCount()+' vs '+R.notes.depUnfiltered.paths);

    // ================= 9. Markers and labels stay inside their row =========
    // Reported from the field. Two offsets compounded: msCellPos() moves a
    // shared marker off the cell midline by a fixed PERCENTAGE, and the label
    // band then moved the stack again from there. A 25px stack in a 34px row
    // has 4.5px of slack and the band was a fixed 15px, so a banded label
    // necessarily landed on the neighbouring row: 31 of 150 stacks, worst
    // 18.2px. Asserted across the slider range, because the failure only
    // appears at particular combinations of row height and icon size.
    clearFilter(); await settle();
    const lblCb=document.getElementById('btn-lbl');
    if(lblCb&&!lblCb.checked){ lblCb.checked=true; toggleLabels(lblCb); }
    setShortTitleMode('both');
    await settle(); await settle();
    const containment=function(){
      let markers=0,label=0,mOut=0,lOut=0,worst=-1e9;
      document.querySelectorAll('tr[data-type="row"]:not(.hidden-row)').forEach(function(tr){
        const rr=tr.getBoundingClientRect();
        if(rr.height===0) return;
        tr.querySelectorAll('.m-wrap:not(.m-ghost)').forEach(function(w){
          const wr=w.getBoundingClientRect();
          if(wr.width||wr.height){
            markers++;
            const ov=Math.max(rr.top-wr.top,wr.bottom-rr.bottom);
            if(ov>0.5) mOut++;
            if(ov>worst) worst=ov;
          }
          const st=w.querySelector('.m-lbl-stack');
          if(st){
            const sr=st.getBoundingClientRect();
            if(sr.width||sr.height){
              label++;
              const ov2=Math.max(rr.top-sr.top,sr.bottom-rr.bottom);
              if(ov2>0.5) lOut++;
              if(ov2>worst) worst=ov2;
            }
          }
        });
      });
      return {markers:markers,labels:label,markersOut:mOut,labelsOut:lOut,
              worst:Math.round(worst*10)/10};
    };
    const settings=[[36,15],[72,15],[59,10],[32,15],[20,24]];
    const results=[];
    for(let i=0;i<settings.length;i++){
      setWkWidth(settings[i][0]); setIcoSize(settings[i][1]); onSizeSliderRelease();
      await settle(); await settle();
      const c=containment();
      c.at=settings[i][0]+'px/'+settings[i][1]+'px';
      results.push(c);
    }
    R.notes.containment=results;
    const sampled=results.every(function(c){ return c.markers>100&&c.labels>100; });
    ck('placement: every slider setting had markers and labels to measure',
       sampled, JSON.stringify(results.map(function(c){return c.at+':'+c.markers+'/'+c.labels;})));
    const badM=results.filter(function(c){ return c.markersOut>0; });
    const badL=results.filter(function(c){ return c.labelsOut>0; });
    ck('placement: no marker sits outside its row at any slider setting',
       badM.length===0, badM.map(function(c){return c.at+'='+c.markersOut;}).join(', '));
    ck('placement: no label stack sits outside its row at any slider setting',
       badL.length===0, badL.map(function(c){return c.at+'='+c.labelsOut;}).join(', '));
    // Rows have to grow when labels are on, or the three bands cannot be
    // separated without leaving the row.
    R.notes.rowHWithLabels=getComputedStyle(document.documentElement).getPropertyValue('--row-min-h').trim();
    ck('placement: rows are held taller while milestone labels are shown',
       parseInt(R.notes.rowHWithLabels,10)>=48, R.notes.rowHWithLabels);
    setShortTitleMode('off');
    if(lblCb&&lblCb.checked){ lblCb.checked=false; toggleLabels(lblCb); }
    await settle(); await settle();
    R.notes.rowHNoLabels=getComputedStyle(document.documentElement).getPropertyValue('--row-min-h').trim();
    ck('placement: and go back to the chosen height once labels are off',
       parseInt(R.notes.rowHNoLabels,10)<48, R.notes.rowHNoLabels);

    R.ok=true;
  }catch(e){ R.ok=false; R.err=e.message; R.stack=(e.stack||'').split('\n').slice(0,4).join(' | '); }
  emit();
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default="data/schedules/103787-13_PFS_Weekly_Update_DD-2026-08-29.xlsx")
    ap.add_argument("--html", default="src/milestone-dashboard.html")
    a = ap.parse_args()

    aoa = build_aoa(pathlib.Path(a.xlsx))
    html = pathlib.Path(a.html).read_text(encoding="utf-8", errors="replace")
    # The expected single-import figures are injected rather than written into
    # the probe, so the numbers live in one place next to their explanation.
    inject = ("<script>const AOA=" + json.dumps(aoa) + ";"
              "const TASK_ONE=" + str(ONE["tasks"]) + ";const MS_ONE=" + str(ONE["milestones"]) + ";</script>\n"
              "<script>\n" + PROBE + "\n</script>\n")
    page = html.replace("</body>", inject + "</body>")
    if page == html:
        sys.exit("Could not find </body> to inject into.")

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / "p30.html"
        tmp.write_text(page, encoding="utf-8")
        proc = subprocess.run(
            [find_chrome(), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--window-size=1600,1200", "--virtual-time-budget=90000",
             "--dump-dom", tmp.as_uri()],
            capture_output=True, text=True, timeout=600,
        )
    m = OUT_RE.search(proc.stdout)
    if not m:
        sys.exit("Probe output not found.\n" + proc.stderr[-3000:])
    R = json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8"))

    if not R.get("ok"):
        print("PROBE FAILED: " + str(R.get("err")))
        print(R.get("stack", ""))
        for c in R.get("checks", []):
            print(("  ok   " if c["pass"] else "  FAIL ") + c["name"])
        return 1

    n = R.get("notes", {})
    for k in ("defaultSourceName", "oneSource", "twoSource", "bandsOne", "bandsTwo",
              "idCount", "idUnique", "suffixed", "rowIdCount", "twinId",
              "filterOptions", "filteredRows", "srcSchCells", "hdrCells", "bodyCells",
              "publishedSources", "restored", "afterViewSwitch", "idListLength", "debounce",
              "rangeStyleRules", "inlineHiddenCells", "hiddenCols",
              "depUnfiltered", "depWithRange", "depWithWeek", "depAfterClear",
              "containment", "rowHWithLabels", "rowHNoLabels"):
        if k in n:
            v = n[k]
            print(f"   {k}: {json.dumps(v) if isinstance(v, (list, dict)) else v}")
    if n.get("drift"):
        print("   id drift: " + json.dumps(n["drift"]))
    print()

    fails = [c for c in R["checks"] if not c["pass"]]
    for c in R["checks"]:
        mark = "ok  " if c["pass"] else "FAIL"
        print(f"  {mark} {c['name']}" + (f"   [{c['detail']}]" if c["detail"] else ""))

    print(f"\n{len(R['checks']) - len(fails)}/{len(R['checks'])} checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
