/* =====================================================================
   SRET notes export. Turns the entry array into the two-sheet workbook
   data (Summary, Log). Pure functions, no DOM, no network, no app globals.
   The rollup, the milestone lookup and the schedule lookup are injected.

   API (global SRETNotesExport, also module.exports):
     buildNotesWorkbookAoA(entries, {rollup, msLookup, sourceOf, periodFilter, fmtDate})
         -> {summary: AoA, log: AoA}
     writeNotesWorkbook(XLSX, aoa, filename)   builds the book, saves it, returns it
     buildNotesBook(XLSX, aoa)                 builds the book only
   ===================================================================== */
(function(root){
  'use strict';

  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var HEALTH={0:'N/A',1:'On track',2:'Done',3:'At risk',4:'Critical'};
  var FIELD_LABEL={actName:'Name',start:'Start',date:'Finish',weight:'Weight',floatD:'Float',
    type:'Type',marker:'Marker',health:'Health',progress:'Progress',
    rowHealth:'Row health',rowRemark:'Row remark',actual:'Finish actual',startActual:'Start actual'};
  var SCHEDULE='schedule value';

  function pad(n){ return (n<10?'0':'')+n; }

  /* 'YYYY-MM-DD' (or an ISO timestamp) -> 'dd-Mmm-yy'. Anything else comes back as text. */
  function defaultFmtDate(v){
    if(v==null||v==='') return '';
    var m=/^(\d{4})-(\d{2})-(\d{2})/.exec(String(v));
    if(!m) return String(v);
    return m[3]+'-'+MON[+m[2]-1]+'-'+m[1].slice(2);
  }
  /* ISO timestamp -> 'dd-Mmm HH:MM' (or 'dd-Mmm-yy HH:MM'), in the viewer's local time. */
  function stamp(iso, withYear){
    if(!iso) return '';
    var d=new Date(iso);
    if(isNaN(d.getTime())) return String(iso);
    var s=pad(d.getDate())+'-'+MON[d.getMonth()];
    if(withYear) s+='-'+String(d.getFullYear()).slice(2);
    return s+' '+pad(d.getHours())+':'+pad(d.getMinutes());
  }
  function clean(v){
    return typeof v==='string' ? v.replace(/[—–]/g,'-') : v;
  }

  function makeFmt(fmtDate){
    var fd=typeof fmtDate==='function'?fmtDate:defaultFmtDate;
    function date(v){ return v==null||v===''?'':String(fd(v)); }
    function healthLabel(v){ return v==null?'':(HEALTH[v]!=null?HEALTH[v]:String(v)); }
    function progress(v){ return v==null||v===''?'':v+'%'; }
    function value(field,v){
      if(v===null||v===undefined) return SCHEDULE;
      if(field==='start'||field==='date') return date(v);
      if(field==='health'||field==='rowHealth') return healthLabel(v);
      if(field==='progress') return progress(v);
      return String(v);
    }
    return {date:date,health:healthLabel,progress:progress,value:value,
      report:function(p){ return p?'W/E '+date(p):''; }};
  }

  function changesText(changes,f){
    var out=[];
    Object.keys(changes||{}).forEach(function(field){
      var c=changes[field]||{};
      var label=FIELD_LABEL[field]||field;
      out.push(label+' '+(('from' in c)?f.value(field,c.from)+' → ':'→ ')+f.value(field,c.to));
    });
    return out.join('; ');
  }

  /* Who a target is: {id, name}. */
  function identify(target,msLookup){
    var t=target||{}, key=t.key==null?'':String(t.key);
    if(t.kind==='general') return {id:'General',name:''};
    if(t.kind==='dep'){
      var parts=key.split(/\s*(?:→|->|>|\|)\s*/);
      return {id:parts.length===2?parts[0]+' → '+parts[1]:key,name:'Dependency'};
    }
    if(t.kind==='row') return {id:'Row: '+key,name:''};
    var m=typeof msLookup==='function'?msLookup(key):null;
    return {id:m&&m.id!=null?m.id:key,name:m&&m.name!=null?m.name:''};
  }

  function groupKey(e){
    var t=e.target||{};
    return t.kind==='general'
      ? 'general||'+e.period
      : (t.kind||'ms')+'|'+(t.key==null?'':t.key)+'|'+e.period;
  }
  function byAtDesc(a,b){ return a.at<b.at?1:a.at>b.at?-1:(a.eid<b.eid?1:a.eid>b.eid?-1:0); }
  function byAtAsc(a,b){ return -byAtDesc(a,b); }

  var SUMMARY_HEAD=['ID','Milestone','Report','Open items','Remarks',
    'Start (schedule)','Start (new)','Finish (schedule)','Finish (new)',
    'Status/Health (schedule)','Status/Health (new)','Progress (schedule)','Progress (new)','Last saved'];
  var LOG_HEAD=['Entry','ID','Milestone','Report','Status','Remark','Changes','Linked IDs','Saved','Origin'];

  function buildNotesWorkbookAoA(entries, opts){
    opts=opts||{};
    var f=makeFmt(opts.fmtDate);
    var rollup=opts.rollup, sourceOf=opts.sourceOf, msLookup=opts.msLookup;
    var pf=opts.periodFilter||null;
    var list=(entries||[]).filter(function(e){ return e&&(!pf||e.period===pf); });

    /* Summary: one row per (target, period) */
    var groups={}, order=[];
    list.forEach(function(e){
      var k=groupKey(e);
      if(!groups[k]){ groups[k]={target:e.target||{},period:e.period,entries:[]}; order.push(k); }
      groups[k].entries.push(e);
    });
    var rows=order.map(function(k){
      var g=groups[k], t=g.target, kind=t.kind||'ms';
      var who=identify(t,msLookup);
      var key=kind==='general'?'':(t.key==null?'':t.key);
      var ru=(typeof rollup==='function'?rollup(g.entries,key,{period:g.period}):null)||{};
      var vals=ru.values||{};
      var remarks=g.entries.filter(function(e){ return e.text; }).sort(byAtDesc)
        .map(function(e){ return stamp(e.at)+' '+e.text; }).join('\n');
      var open=ru.openCount!=null?ru.openCount:g.entries.filter(function(e){ return e.status==='open'; }).length;
      var last=g.entries.reduce(function(m,e){ var u=e.updatedAt||e.at||''; return u>m?u:m; },'');
      function src(field){ return kind==='ms'&&typeof sourceOf==='function'?sourceOf(key,field):null; }
      function nw(field,fmt){ return (field in vals)?(vals[field]===null?SCHEDULE:fmt(vals[field])):''; }
      return {period:g.period,id:String(who.id),row:[
        who.id,who.name,f.report(g.period),open,remarks,
        f.date(src('start')),nw('start',f.date),
        f.date(src('date')),nw('date',f.date),
        f.health(src('health')),nw('health',f.health),
        f.progress(src('progress')),nw('progress',f.progress),
        stamp(last,true)
      ]};
    });
    rows.sort(function(a,b){
      return a.period<b.period?-1:a.period>b.period?1:
        a.id.localeCompare(b.id,undefined,{numeric:true});
    });

    /* Log: one row per entry, oldest first */
    var log=list.slice().sort(byAtAsc).map(function(e){
      var who=identify(e.target,msLookup);
      return [e.eid,who.id,who.name,f.report(e.period),e.status||'',e.text||'',
        changesText(e.changes,f),(e.links||[]).join(', '),
        stamp(e.updatedAt||e.at,true),e.origin==null?'':String(e.origin)];
    });

    function scrub(aoa){ return aoa.map(function(r){ return r.map(clean); }); }
    return {
      summary:scrub([SUMMARY_HEAD].concat(rows.map(function(r){ return r.row; }))),
      log:scrub([LOG_HEAD].concat(log))
    };
  }

  function buildNotesBook(XLSX, aoa){
    var wb=XLSX.utils.book_new();
    function sheet(rows,widths){
      var ws=XLSX.utils.aoa_to_sheet(rows);
      ws['!cols']=widths.map(function(w){ return {wch:w}; });
      return ws;
    }
    XLSX.utils.book_append_sheet(wb,sheet(aoa.summary,[12,34,16,10,60,14,14,14,14,16,16,14,14,18]),'Summary');
    XLSX.utils.book_append_sheet(wb,sheet(aoa.log,[10,12,34,16,12,60,50,18,18,14]),'Log');
    return wb;
  }

  function writeNotesWorkbook(XLSX, aoa, filename){
    var wb=buildNotesBook(XLSX,aoa);
    XLSX.writeFile(wb,filename||'milestone-notes.xlsx');
    return wb;
  }

  var api={buildNotesWorkbookAoA:buildNotesWorkbookAoA,writeNotesWorkbook:writeNotesWorkbook,
    buildNotesBook:buildNotesBook};
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  root.SRETNotesExport=api;
})(typeof window!=='undefined'?window:globalThis);
