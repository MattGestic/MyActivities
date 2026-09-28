/* =====================================================================
   SRET schedule comparison (Matt, 2026-09-28). No UI, no app globals.

   What "changed" means depends on what the current schedule is compared
   with, and not every import is a project update. Each import is filed
   with a role and a lineage:

     role 'project'   a formal update of the project schedule (lineage 'project')
     role 'interim'   an interim cut of the project schedule between formal
                      updates (lineage 'project'); never becomes the default
                      basis for a formal update
     role 'external'  a schedule from someone else: vendor, contractor
                      (lineage = its name, e.g. 'Ocean Steel fabrication').
                      Only ever compared with earlier imports of itself.

   Default basis (the user can pick any other eligible one):
     project  -> the previous formal project update
     interim  -> the latest formal project update before it
     external -> the previous import of the same external schedule
   Eligible bases: earlier snapshots of the same lineage (by data date, then
   import time), plus the project baseline for the project lineage.

   Activities match by Activity ID within the lineage. Differences are in
   calendar days, positive = later (a slip). Float is as exported.

   API (window.SRETCompare):
     snapshot(meta, rows)     -> {id, lineage, role, name, dataDate, file, importedAt, rows:{ID:{n,s,f,fl,a}}}
                                meta: {id, role, name, dataDate, file, importedAt}
                                rows: [{id, name, start, finish, float, actual}]
     bases(snaps, current)    -> [{snap, label, isDefault}]   newest first
     defaultBasis(snaps, cur) -> snap | null
     compare(basis, current)  -> {rows:[...], counts:{later, earlier, completed, added, removed, float, unchanged}}
     label(snap)              -> 'Project update, DD 22-Aug-26'
   ===================================================================== */
(function(root){
  'use strict';
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var ROLE={project:'Project update',interim:'Interim update',external:'',baseline:'Baseline'};

  function lineageOf(meta){ return meta.role==='external'?'ext:'+String(meta.name||'').trim().toLowerCase():'project'; }
  function fmt(iso){ if(!iso) return ''; var p=String(iso).split('-'); return (+p[2])+'-'+MON[+p[1]-1]+'-'+p[0].slice(2); }
  function days(a,b){
    if(!a||!b) return null;
    return Math.round((Date.UTC(+b.slice(0,4),+b.slice(5,7)-1,+b.slice(8,10))-Date.UTC(+a.slice(0,4),+a.slice(5,7)-1,+a.slice(8,10)))/86400000);
  }
  function snapshot(meta,rows){
    var r={};
    (rows||[]).forEach(function(x){
      if(!x||x.id==null||x.id==='') return;
      r[String(x.id)]={n:x.name||'',s:x.start||null,f:x.finish||null,fl:x.float==null||x.float===''?null:+x.float,a:x.actual==='Yes'||x.actual===true};
    });
    return {id:meta.id,lineage:meta.role==='baseline'?'project':lineageOf(meta),role:meta.role||'project',name:meta.name||'',
            dataDate:meta.dataDate||null,file:meta.file||'',importedAt:meta.importedAt||null,rows:r};
  }
  function label(s){
    if(!s) return 'Nothing to compare with';
    var what=s.role==='external'?s.name:ROLE[s.role]||s.role;
    return what+(s.dataDate?', DD '+fmt(s.dataDate):'');
  }
  function before(a,b){  // a earlier than b
    if(a.dataDate&&b.dataDate&&a.dataDate!==b.dataDate) return a.dataDate<b.dataDate;
    return String(a.importedAt||'')<String(b.importedAt||'');
  }
  function eligible(snaps,cur){
    return (snaps||[]).filter(function(s){
      return s!==cur&&s.id!==cur.id&&s.lineage===cur.lineage&&(s.role==='baseline'||before(s,cur));
    }).sort(function(a,b){
      if(a.role==='baseline'!==(b.role==='baseline')) return a.role==='baseline'?1:-1;   // baseline listed last
      return before(a,b)?1:-1;                                                             // newest first
    });
  }
  function defaultBasis(snaps,cur){
    var el=eligible(snaps,cur);
    if(cur.role==='external') return el.filter(function(s){ return s.role==='external'; })[0]||null;
    // project and interim: the latest formal project update before it
    return el.filter(function(s){ return s.role==='project'; })[0]||el.filter(function(s){ return s.role==='baseline'; })[0]||null;
  }
  function bases(snaps,cur){
    var d=defaultBasis(snaps,cur);
    return eligible(snaps,cur).map(function(s){ return {snap:s,label:label(s),isDefault:s===d}; });
  }
  function compare(basis,cur){
    var out=[], c={later:0,earlier:0,completed:0,added:0,removed:0,float:0,unchanged:0};
    var ids={}; Object.keys(cur.rows).forEach(function(k){ ids[k]=1; }); if(basis) Object.keys(basis.rows).forEach(function(k){ ids[k]=1; });
    Object.keys(ids).sort().forEach(function(id){
      var was=basis?basis.rows[id]:null, now=cur.rows[id];
      var row={id:id,name:(now||was).n,
        startWas:was?was.s:null,startNow:now?now.s:null,finishWas:was?was.f:null,finishNow:now?now.f:null,
        floatWas:was?was.fl:null,floatNow:now?now.fl:null,
        startSlip:was&&now?days(was.s,now.s):null,finishSlip:was&&now?days(was.f,now.f):null,
        floatChange:was&&now&&was.fl!=null&&now.fl!=null?now.fl-was.fl:null,change:''};
      if(!basis){ return; }
      if(!was){ row.change='New'; c.added++; }
      else if(!now){ row.change='Removed'; c.removed++; }
      else if(now.a&&!was.a){ row.change='Completed'; c.completed++; }
      else if(row.finishSlip>0||(!row.finishSlip&&row.startSlip>0)){ row.change='Later'; c.later++; }
      else if(row.finishSlip<0||(!row.finishSlip&&row.startSlip<0)){ row.change='Earlier'; c.earlier++; }
      else if(row.floatChange){ row.change='Float only'; c.float++; }
      else { c.unchanged++; return; }
      out.push(row);
    });
    // Biggest slips first, then the rest by ID.
    out.sort(function(a,b){ return (b.finishSlip||0)-(a.finishSlip||0)||(a.id<b.id?-1:1); });
    return {rows:out,counts:c};
  }
  function summary(r){
    var c=r.counts, parts=[];
    if(c.later) parts.push(c.later+' later'); if(c.earlier) parts.push(c.earlier+' earlier');
    if(c.completed) parts.push(c.completed+' completed'); if(c.added) parts.push(c.added+' new'); if(c.removed) parts.push(c.removed+' removed');
    if(c.float) parts.push(c.float+' float only');
    return parts.length?parts.join(', ')+'; '+c.unchanged+' unchanged.':'No changes; '+c.unchanged+' unchanged.';
  }

  root.SRETCompare={snapshot:snapshot,bases:bases,defaultBasis:defaultBasis,compare:compare,label:label,summary:summary,_days:days};
})(window);
