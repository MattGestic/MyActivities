/* =====================================================================
   SRET schedule comparison (Matt, 2026-09-28). No UI, no app globals.

   Every schedule line keeps three loaded imports at any one time, plus the
   embedded baseline for the project:

     Project schedule             the latest import (what the board shows)
     Project schedule comparison  the previous latest: moved here when a new
                                  latest is imported; the one before is dropped
     Project schedule alternate   loaded on purpose as an alternative basis
                                  (an interim cut, a what-if); replaced only
                                  when another alternate is loaded
     Project baseline             embedded in the file; never replaced here

   Interim updates (Matt, 2026-09-28) are loaded as well, but are never the
   full project update: an interim may cover only part of the schedule
   (e.g. just commissioning). Each is filed under a scope named at import
   and held beside the three slots; the next interim of the same scope
   replaces it. It never moves the latest into comparison. Compared as a
   part: activities outside its scope are neither Removed nor New, they are
   counted as outside the interim.

   A schedule from someone else (vendor, contractor) is its own line, named
   at import, with the same three slots and no baseline. Lines never compare
   with each other, so a vendor's IDs never meet the project's.

   Each loaded import records: snapshot date (when it was taken), data date,
   file name and file location. A browser does not reveal a file's folder,
   so the location is what the user typed at import (optional).

   Default basis:
     latest      -> comparison (else the baseline)
     comparison  -> the baseline
     alternate   -> latest
     interim     -> latest (what the interim changes against the full update)
   Any other slot of the same line (and the baseline) can be picked.
   Differences are calendar days, positive = later (a slip).

   API (window.SRETCompare):
     newStore()                                  -> store
     receive(store, meta, rows, slot)            -> {snap, dropped}   slot 'latest' (default) | 'alternate' | 'interim' | 'baseline'
        meta: {name, role:'project'|'external', dataDate, file, path, snapshotAt, scope (interim only)}
        rows: [{id, name, start, finish, float, actual}]
     list(store)                                 -> [snap]  project first: latest, comparison, alternate, interims (newest first), baseline; then external lines
     bases(store, snap)                          -> [{snap, label, isDefault}]
     defaultBasis(store, snap)                   -> snap | null
     compare(basis, snap)                        -> {rows, counts}
     label(snap)                                 -> 'Project schedule comparison, DD 22-Aug-26'
     slotName(snap)                              -> 'Project schedule comparison'
     summary(result)                             -> '14 later, 8 earlier, ...'
     record(store)                               -> [{slot, dataDate, snapshotAt, file, path}] for the Loaded schedules table
   ===================================================================== */
(function(root){
  'use strict';
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var SLOTS=['latest','comparison','alternate'];
  var seq=0;

  function fmt(iso){ if(!iso) return ''; var p=String(iso).split('-'); return (+p[2])+'-'+MON[+p[1]-1]+'-'+p[0].slice(2); }
  function days(a,b){
    if(!a||!b) return null;
    return Math.round((Date.UTC(+b.slice(0,4),+b.slice(5,7)-1,+b.slice(8,10))-Date.UTC(+a.slice(0,4),+a.slice(5,7)-1,+a.slice(8,10)))/86400000);
  }
  function lineKey(meta){ return meta.role==='external'?'ext:'+String(meta.name||'').trim().toLowerCase():'project'; }
  function snapRows(rows){
    var r={};
    (rows||[]).forEach(function(x){
      if(!x||x.id==null||x.id==='') return;
      r[String(x.id)]={n:x.name||'',s:x.start||null,f:x.finish||null,fl:x.float==null||x.float===''?null:+x.float,a:x.actual==='Yes'||x.actual===true};
    });
    return r;
  }
  function newStore(){ return {lines:{},order:[],baseline:null}; }
  function receive(store,meta,rows,slot){
    slot=slot||'latest';
    var key=slot==='baseline'?'project':lineKey(meta);
    var snap={id:meta.id||('snap-'+(++seq)),line:key,role:key==='project'?'project':'external',
              lineName:key==='project'?'Project schedule':String(meta.name||'External schedule').trim(),
              slot:slot,dataDate:meta.dataDate||null,snapshotAt:meta.snapshotAt||new Date().toISOString(),
              file:meta.file||'',path:meta.path||'',rows:snapRows(rows),
              partial:slot==='interim',scope:slot==='interim'?String(meta.scope||'Interim').trim():''};
    if(slot==='baseline'){ var old=store.baseline; store.baseline=snap; return {snap:snap,dropped:old}; }
    var ln=store.lines[key];
    if(!ln){ ln=store.lines[key]={name:snap.lineName,latest:null,comparison:null,alternate:null,interims:{}}; store.order.push(key); }
    var dropped=null;
    if(slot==='interim'){ var sk=snap.scope.toLowerCase(); dropped=ln.interims[sk]||null; ln.interims[sk]=snap; }
    else if(slot==='alternate'){ dropped=ln.alternate; ln.alternate=snap; }
    else {
      dropped=ln.comparison;
      if(ln.latest){ ln.comparison=ln.latest; ln.comparison.slot='comparison'; }
      ln.latest=snap; snap.slot='latest';
    }
    if(dropped) dropped.slot='dropped';
    return {snap:snap,dropped:dropped};
  }
  function lineSnaps(store,key){
    var ln=store.lines[key]; if(!ln) return [];
    var out=SLOTS.map(function(s){ return ln[s]; }).filter(Boolean);
    Object.keys(ln.interims).map(function(k){ return ln.interims[k]; })
      .sort(function(a,b){ return String(b.dataDate)<String(a.dataDate)?-1:1; }).forEach(function(x){ out.push(x); });
    if(key==='project'&&store.baseline) out.push(store.baseline);
    return out;
  }
  function list(store){
    var keys=store.order.slice().sort(function(a,b){ return a==='project'?-1:b==='project'?1:0; });
    if(!store.lines.project&&store.baseline) keys.unshift('project');
    var out=[]; keys.forEach(function(k){ lineSnaps(store,k).forEach(function(s){ if(out.indexOf(s)<0) out.push(s); }); });
    return out;
  }
  function slotName(s){
    if(!s) return '';
    if(s.slot==='baseline') return 'Project baseline';
    if(s.slot==='interim') return s.lineName.replace(/ schedule$/,'')+' interim update ('+s.scope+')';
    return s.lineName+({latest:'',comparison:' comparison',alternate:' alternate'}[s.slot]||'');
  }
  function label(s){ return s?slotName(s)+(s.dataDate?', DD '+fmt(s.dataDate):''):'Nothing to compare with'; }
  function defaultBasis(store,s){
    var ln=store.lines[s.line]||{}, base=s.line==='project'?store.baseline:null;
    if(s.slot==='latest') return ln.comparison||base||null;
    if(s.slot==='comparison') return base||null;
    if(s.slot==='alternate'||s.slot==='interim') return ln.latest||null;
    return null;
  }
  function bases(store,s){
    var d=defaultBasis(store,s);
    return lineSnaps(store,s.line).filter(function(x){ return x!==s; })
      .map(function(x){ return {snap:x,label:label(x),isDefault:x===d}; });
  }
  function compare(basis,cur){
    var out=[], c={later:0,earlier:0,completed:0,added:0,removed:0,float:0,unchanged:0,outside:0,onlyInterim:0};
    if(!basis||!cur) return {rows:out,counts:c};
    var ids={}; Object.keys(cur.rows).forEach(function(k){ ids[k]=1; }); Object.keys(basis.rows).forEach(function(k){ ids[k]=1; });
    Object.keys(ids).sort().forEach(function(id){
      var was=basis.rows[id], now=cur.rows[id];
      // An interim covers part of the schedule: what it does not hold is out of scope, not Removed or New.
      if((!now&&cur.partial)||(!was&&basis.partial)){ c.outside++; return; }
      var row={id:id,name:(now||was).n,
        startWas:was?was.s:null,startNow:now?now.s:null,finishWas:was?was.f:null,finishNow:now?now.f:null,
        floatWas:was?was.fl:null,floatNow:now?now.fl:null,
        startSlip:was&&now?days(was.s,now.s):null,finishSlip:was&&now?days(was.f,now.f):null,
        floatChange:was&&now&&was.fl!=null&&now.fl!=null?now.fl-was.fl:null,change:''};
      if(!was){ row.change='New'; c.added++; }
      // Held by the interim basis but not by this full schedule: the interim added it; nothing was removed.
      else if(!now&&basis.partial){ row.change='Only in interim'; c.onlyInterim++; }
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
    if(c.float) parts.push(c.float+' float only'); if(c.onlyInterim) parts.push(c.onlyInterim+' only in the interim');
    var tail=c.outside?' '+c.outside+' outside the interim.':'';
    return (parts.length?parts.join(', ')+'; '+c.unchanged+' unchanged.':'No changes; '+c.unchanged+' unchanged.')+tail;
  }
  function record(store){
    return list(store).map(function(s){
      return {id:s.id,slot:slotName(s),dataDate:s.dataDate,snapshotAt:s.snapshotAt,file:s.file,path:s.path,activities:Object.keys(s.rows).length,partial:!!s.partial};
    });
  }

  root.SRETCompare={newStore:newStore,receive:receive,list:list,bases:bases,defaultBasis:defaultBasis,compare:compare,
                    label:label,slotName:slotName,summary:summary,record:record,_days:days};
})(window);
