/* =====================================================================
   SRET schedule comparison (Matt, 2026-09-28). No UI, no app globals.

   Storage is by upload: every loaded file is kept under its upload
   reference (the app's source id), with what it is and where it came from:
   snapshot date, data date, file name, file location, and whether it covers
   the full schedule or part of it (an interim, with its scope).

   Designations are applied to uploads through a reference table, one per
   schedule line. Setting "this source is the primary" is one row in that
   table; nothing is copied or moved:

     line      designation   upload
     project   primary       pu-0829     the schedule the board shows
     project   secondary     pu-0822     the usual comparison
     project   alternate     pa-0826     another basis kept on purpose

   Plus the embedded Project baseline. A vendor or contractor schedule is
   its own line, named at import, with its own table rows and no baseline;
   lines never compare with each other.

   Rules:
     - An interim covers part of the schedule (e.g. commissioning), so it
       can be the secondary or alternate but never the primary. Stored
       interims are kept one per scope.
     - Importing as primary (the usual weekly update) is a shortcut for two
       table changes: the old primary becomes the secondary, the new upload
       the primary.
     - Retention: on each import, uploads that hold no designation (and are
       not the latest interim of their scope, nor the baseline) are released.
       So each line keeps its three designated uploads, plus interims.
     - Re-designating never deletes: an upload that loses its designation
       stays listed as not designated until the next import.

   Default basis: primary -> secondary (else baseline); secondary ->
   baseline; alternate, interim or not designated -> primary.
   Differences are calendar days, positive = later (a slip).

   API (window.SRETCompare):
     newStore()                                 -> store
     add(store, meta, rows)                     -> upload (stored, not designated)
        meta: {id, name, role:'project'|'external', dataDate, file, path, snapshotAt, scope (interim only)}
        rows: [{id, name, start, finish, float, actual}]
     designate(store, uploadId, 'primary'|'secondary'|'alternate'|null) -> {ok, previous, error}
     receive(store, meta, rows, as)             -> {snap, released}   import shortcut:
        as 'primary' (default) | 'secondary' | 'alternate' | 'interim' | 'baseline'
     table(store)                               -> [{line, lineName, designation, upload}]  the reference table
     list(store)                                -> [upload] designated, interims, baseline; project line first
     record(store)                              -> every stored upload with its designation, for the Loaded schedules table
     bases(store, upload) / defaultBasis(store, upload) / compare(basis, upload)
     label(upload) -> 'Project secondary, DD 22-Aug-26'    slotName(upload)    summary(result)
     overlay(store, {scopes, movedOnly}) -> {marks:[...], unplaced:[...]}
        Interim dates to draw over the primary on the board (Matt, 2026-09-28:
        optional, display state only). One mark per activity the interim and
        the primary share: {id, name, scope, upload, dataDate, start, finish,
        primaryStart, primaryFinish, finishSlip, moved}. unplaced: activities
        only the interim holds (no row on the board to draw them on).
   ===================================================================== */
(function(root){
  'use strict';
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var DES=['primary','secondary','alternate'];
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
  function newStore(){ return {uploads:{},order:[],refs:{},lines:{},baseline:null}; }
  // The cached designation on each upload mirrors the reference table.
  function sync(store){
    Object.keys(store.uploads).forEach(function(id){ var u=store.uploads[id]; u.slot=u===store.baseline?'baseline':u.partial?'interim':'none'; });
    Object.keys(store.refs).forEach(function(k){ DES.forEach(function(d){ var id=store.refs[k][d]; if(id&&store.uploads[id]) store.uploads[id].slot=d; }); });
  }
  function add(store,meta,rows,isBaseline){
    var key=isBaseline?'project':lineKey(meta);
    var partial=!!(meta.scope&&!isBaseline);
    var u={id:meta.id||('up-'+(++seq)),line:key,role:key==='project'?'project':'external',
           lineName:key==='project'?'Project':String(meta.name||'External schedule').trim(),
           dataDate:meta.dataDate||null,snapshotAt:meta.snapshotAt||new Date().toISOString(),
           file:meta.file||'',path:meta.path||'',rows:snapRows(rows),partial:partial,scope:partial?String(meta.scope).trim():'',slot:'none'};
    store.uploads[u.id]=u; store.order.push(u.id);
    if(!store.refs[key]){ store.refs[key]={primary:null,secondary:null,alternate:null}; store.lines[key]=u.lineName; }
    if(isBaseline) store.baseline=u;
    sync(store);
    return u;
  }
  function designate(store,id,d){
    var u=store.uploads[id];
    if(!u) return {ok:false,error:'That upload is not loaded.'};
    if(u===store.baseline) return {ok:false,error:'The baseline is embedded and is not designated.'};
    if(d&&DES.indexOf(d)<0) return {ok:false,error:'Unknown designation.'};
    if(d==='primary'&&u.partial) return {ok:false,error:'An interim update covers part of the schedule, so it cannot be the primary.'};
    var t=store.refs[u.line], prev=d?t[d]:null;
    DES.forEach(function(x){ if(t[x]===id) t[x]=null; });
    if(d) t[d]=id;
    sync(store);
    return {ok:true,previous:prev&&prev!==id?prev:null};
  }
  function kept(store,u){
    if(u===store.baseline||u.slot!=='none'&&u.slot!=='interim') return true;
    if(!u.partial) return false;
    // the newest stored interim of its scope, per line
    return !store.order.some(function(id){ var o=store.uploads[id];
      return o&&o!==u&&o.partial&&o.line===u.line&&o.scope.toLowerCase()===u.scope.toLowerCase()&&store.order.indexOf(id)>store.order.indexOf(u.id); });
  }
  function prune(store){
    var released=[];
    store.order.slice().forEach(function(id){ var u=store.uploads[id]; if(u&&!kept(store,u)){ released.push(u); delete store.uploads[id]; store.order.splice(store.order.indexOf(id),1); } });
    released.forEach(function(u){ u.slot='released'; });
    return released;
  }
  function receive(store,meta,rows,as){
    as=as==='latest'?'primary':(as||'primary');
    var u=add(store,meta,rows,as==='baseline');
    if(as==='primary'){
      var t=store.refs[u.line];
      if(t.primary) designate(store,t.primary,'secondary');
      designate(store,u.id,'primary');
    } else if(as==='secondary'||as==='alternate') designate(store,u.id,as);
    return {snap:u,released:as==='baseline'?[]:prune(store)};
  }
  function table(store){
    var out=[];
    lineKeys(store).forEach(function(k){ DES.forEach(function(d){ out.push({line:k,lineName:store.lines[k],designation:d,upload:store.refs[k][d]}); }); });
    return out;
  }
  function lineKeys(store){ return Object.keys(store.refs).sort(function(a,b){ return a==='project'?-1:b==='project'?1:store.order.indexOf(a)-store.order.indexOf(b); }); }
  function lineSnaps(store,key){
    var t=store.refs[key]; if(!t) return [];
    var out=DES.map(function(d){ return t[d]&&store.uploads[t[d]]; }).filter(Boolean);
    store.order.map(function(id){ return store.uploads[id]; })
      .filter(function(u){ return u.line===key&&u.slot==='interim'; })
      .sort(function(a,b){ return String(b.dataDate)<String(a.dataDate)?-1:1; }).forEach(function(x){ out.push(x); });
    if(key==='project'&&store.baseline) out.push(store.baseline);
    return out;
  }
  function list(store){ var out=[]; lineKeys(store).forEach(function(k){ lineSnaps(store,k).forEach(function(s){ if(out.indexOf(s)<0) out.push(s); }); }); return out; }
  function slotName(s){
    if(!s) return '';
    if(s.slot==='baseline') return 'Project baseline';
    var part=s.partial?' (interim: '+s.scope+')':'';
    if(s.slot==='interim') return s.lineName+' interim ('+s.scope+')';
    if(s.slot==='none') return s.lineName+' upload, not designated'+part;
    return s.lineName+' '+s.slot+part;
  }
  function label(s){ return s?slotName(s)+(s.dataDate?', DD '+fmt(s.dataDate):''):'Nothing to compare with'; }
  function defaultBasis(store,s){
    var t=store.refs[s.line]||{}, base=s.line==='project'?store.baseline:null, get=function(d){ return t[d]&&store.uploads[t[d]]||null; };
    if(s.slot==='primary') return get('secondary')||base||null;
    if(s.slot==='secondary') return base||null;
    if(s.slot==='baseline') return null;
    var p=get('primary'); return p&&p!==s?p:null;
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
    var shown=list(store), rest=store.order.map(function(id){ return store.uploads[id]; }).filter(function(u){ return shown.indexOf(u)<0; });
    return shown.concat(rest).map(function(s){
      return {id:s.id,slot:slotName(s),dataDate:s.dataDate,snapshotAt:s.snapshotAt,file:s.file,path:s.path,activities:Object.keys(s.rows).length,partial:!!s.partial,designation:s.slot};
    });
  }

  // Interim dates over the primary. Never changes the primary or any store:
  // the board draws these as extra markers when the overlay is switched on.
  function overlay(store,opts){
    opts=opts||{};
    var t=store.refs.project, prim=t&&t.primary&&store.uploads[t.primary], marks=[], unplaced=[];
    if(!prim) return {marks:marks,unplaced:unplaced,primary:null};
    var want=opts.scopes?opts.scopes.map(function(x){ return String(x).toLowerCase(); }):null;
    list(store).filter(function(u){ return u.line==='project'&&u.partial&&u!==prim&&(!want||want.indexOf(u.scope.toLowerCase())>=0); })
      .forEach(function(u){
        Object.keys(u.rows).sort().forEach(function(id){
          var r=u.rows[id], p=prim.rows[id];
          if(!p){ unplaced.push({id:id,name:r.n,scope:u.scope,upload:u.id,finish:r.f}); return; }
          var slip=days(p.f,r.f), moved=!!(slip||days(p.s,r.s));
          if(opts.movedOnly&&!moved) return;
          marks.push({id:id,name:r.n,scope:u.scope,upload:u.id,dataDate:u.dataDate,start:r.s,finish:r.f,
                      primaryStart:p.s,primaryFinish:p.f,finishSlip:slip,moved:moved});
        });
      });
    return {marks:marks,unplaced:unplaced,primary:prim.id};
  }
  root.SRETCompare={overlay:overlay,newStore:newStore,add:add,designate:designate,receive:receive,table:table,list:list,bases:bases,
                    defaultBasis:defaultBasis,compare:compare,label:label,slotName:slotName,summary:summary,record:record,_days:days};
})(window);
