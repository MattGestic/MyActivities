/* =====================================================================
   SRET milestone import rules (Matt, 2026-09-27). Pure checks over a parsed
   sheet; no UI, no app globals. The grid's Import milestones dialog uses
   it, and the app's own import path can hand it the same array-of-arrays.

   Rules:
     - The file must have an ID column and at least one row.
     - Duplicate IDs within the file block the import: only unique IDs and
       blank IDs are allowed.
     - A row whose ID is already in the table is not imported (skipped).
     - A blank ID is assigned by the application when the row is added.
     - Predecessors and successors must name an ID that exists (in the
       app, or in the file). Missing ones are listed per row, comma
       separated, and the user is asked whether to continue.
     - Other fields are checked the same way: a date, number or choice that
       cannot be read is left blank, listed, and the user is asked.
     - Dates: the order (day, month or year first) is worked out from every
       date in the file by the shared SRETDates engine. When the file cannot
       settle it and some dates would read differently, the user is asked.
     - If the user continues, every issue goes to the Import log with the
       import time, file, user and note.

   API (window.SRETMsImport):
     parseFile(file, ensureXLSX) -> Promise<aoa>   (.csv built in, .xlsx via SheetJS)
     parseCsv(text)             -> aoa
     check(aoa, cfg)            -> result          (see below)
     logEntries(result, meta)   -> [{time,file,user,id,field,note}]
     summary(result, assigned, noun) -> [sentences]; noun ['task','tasks'], default milestone
   cfg: { columns:[{key,label,type,options,min,max}], idKey, depKeys:{pred:'Predecessors',...},
          existingIds:[...], knownIds:[...], dateOrder:'auto'|'DMY'|'MDY'|'YMD' }
   result.dates: {order, chosen, confirmed, reason, numeric, ambiguous, ask}
   ===================================================================== */
(function(root){
  'use strict';

  function norm(v){ return v==null?'':String(v).replace(/\s+/g,' ').trim(); }
  function idNorm(v){ return norm(v).toUpperCase(); }
  function toNumber(v,col){
    if(v==null||norm(v)==='') return {ok:true,value:null};
    var n=Number(norm(v).replace(/%$/,''));
    if(!isFinite(n)) return {ok:false,why:'is not a number'};
    if(col.min!=null&&n<col.min||col.max!=null&&n>col.max) return {ok:false,why:'is outside '+col.min+' to '+col.max};
    return {ok:true,value:n};
  }
  function toOption(v,col){
    if(v==null||norm(v)==='') return {ok:true,value:null};
    var s=norm(v).toLowerCase(), opts=col.options||[];
    for(var i=0;i<opts.length;i++){
      var o=opts[i], val=o&&typeof o==='object'?o.value:o, lab=o&&typeof o==='object'?o.label:o;
      if(String(val).toLowerCase()===s||String(lab).toLowerCase()===s) return {ok:true,value:val};
    }
    return {ok:false,why:'is not one of '+opts.map(function(o){ return o&&typeof o==='object'?o.label:o; }).join(', ')};
  }
  function depIds(v){
    return norm(v).split(/[,;]+/).map(function(t){ return idNorm(t.split(/[:\s]/).filter(Boolean)[0]||''); }).filter(Boolean);
  }

  // RFC 4180 style: quoted fields, doubled quotes, CR/LF line ends.
  function parseCsv(text){
    var rows=[], row=[], f='', q=false, i=0, c;
    text=String(text).replace(/^﻿/,'');
    for(;i<text.length;i++){
      c=text[i];
      if(q){ if(c==='"'){ if(text[i+1]==='"'){ f+='"'; i++; } else q=false; } else f+=c; }
      else if(c==='"') q=true;
      else if(c===','){ row.push(f); f=''; }
      else if(c==='\n'||c==='\r'){ if(c==='\r'&&text[i+1]==='\n') i++; row.push(f); rows.push(row); row=[]; f=''; }
      else f+=c;
    }
    if(f!==''||row.length){ row.push(f); rows.push(row); }
    return rows;
  }
  function parseFile(file,ensureXLSX){
    if(!file) return Promise.reject(new Error('Choose a file first.'));
    var name=file.name||'';
    if(/\.csv$/i.test(name)) return file.text().then(parseCsv);
    // The embedded SheetJS is the mini build (TD-216, Matt 2026-09-30): no legacy .xls.
    if(/\.xls$/i.test(name)) return Promise.reject(new Error('"'+name+'" is an old-style .xls workbook, which cannot be read here. Open it in Excel, save it as .xlsx or .csv, and import that.'));
    if(!/\.xlsx$/i.test(name)) return Promise.reject(new Error('Use an .xlsx or .csv file. "'+name+'" is neither.'));
    var loader=typeof ensureXLSX==='function'?ensureXLSX:function(){ return Promise.resolve(); };
    return Promise.all([Promise.resolve().then(loader),file.arrayBuffer()]).then(function(r){
      var X=r[0]||root.XLSX;
      if(!X||!X.read) throw new Error('The Excel library is not available, so .xlsx files cannot be read. Save the sheet as .csv and import that instead.');
      var wb=X.read(r[1],{type:'array',cellDates:true});
      var ws=wb.Sheets[wb.SheetNames[0]];
      return X.utils.sheet_to_json(ws,{header:1,raw:false,defval:'',dateNF:'d-mmm-yy'});
    });
  }

  function check(aoa,cfg){
    var res={fatal:null,rows:[],skipped:[],issues:[],depIssueRows:0,fieldIssueRows:0,unknownColumns:[]};
    aoa=(aoa||[]).map(function(r){ return (r||[]).map(function(v){ return v; }); });
    var h=0; while(h<aoa.length&&!aoa[h].some(function(v){ return norm(v)!==''; })) h++;
    if(h>=aoa.length){ res.fatal='The file is empty.'; return res; }
    var head=aoa[h].map(norm), map={}, byLabel={};
    cfg.columns.forEach(function(c){ byLabel[norm(c.label).toLowerCase()]=c; byLabel[String(c.key).toLowerCase()]=c; });
    head.forEach(function(t,i){ var c=byLabel[t.toLowerCase()]; if(c) map[i]=c; else if(t) res.unknownColumns.push(t); });
    var idCol=null; for(var k in map) if(map[k].key===cfg.idKey) idCol=+k;
    if(idCol==null){ res.fatal='The file has no "'+(cfg.columns.filter(function(c){ return c.key===cfg.idKey; })[0]||{label:'ID'}).label+
      '" column. Use Download import template for the expected columns.'; return res; }
    var data=[];
    for(var r=h+1;r<aoa.length;r++){
      if(!aoa[r].some(function(v){ return norm(v)!==''; })) continue;
      data.push({rowNum:r+1,cells:aoa[r]});
    }
    if(!data.length){ res.fatal='The file has no rows to import.'; return res; }
    // Duplicate IDs within the file block the import.
    var seen={};
    data.forEach(function(d){ var id=idNorm(d.cells[idCol]); if(id) (seen[id]=seen[id]||[]).push(d.rowNum); });
    var dup=Object.keys(seen).filter(function(id){ return seen[id].length>1; });
    if(dup.length){
      res.fatal='There are duplicate activity IDs within the list: '+dup.map(function(id){ return id+' (rows '+seen[id].join(', ')+')'; }).join('; ')+
        '. Only unique IDs, or blank IDs, can be imported.';
      res.duplicates=dup; return res;
    }
    // Date order, from every date cell in the file together.
    var D=root.SRETDates, dateCols=Object.keys(map).filter(function(i){ return map[i].type==='date'; }), dv=[];
    data.forEach(function(d){ dateCols.forEach(function(i){ dv.push(d.cells[i]); }); });
    var chosen=cfg.dateOrder&&cfg.dateOrder!=='auto'?cfg.dateOrder:null, det=D.detect(dv);
    res.dates={order:chosen||det.order,chosen:chosen?'user':'auto',confirmed:chosen?true:det.confirmed,reason:chosen?'Chosen in the dialog.':det.reason,
               numeric:det.numeric,ambiguous:det.ambiguous,ask:!chosen&&!det.confirmed};
    var existing={}; (cfg.existingIds||[]).forEach(function(id){ existing[idNorm(id)]=1; });
    var valid={}; Object.keys(existing).forEach(function(id){ valid[id]=1; });
    (cfg.knownIds||[]).forEach(function(id){ valid[idNorm(id)]=1; });
    Object.keys(seen).forEach(function(id){ valid[id]=1; });
    data.forEach(function(d){
      var idRaw=norm(d.cells[idCol]), id=idNorm(idRaw);
      if(id&&existing[id]){ res.skipped.push({rowNum:d.rowNum,id:idRaw}); return; }
      var row={}, notes=[], dep=false;
      Object.keys(map).forEach(function(i){
        var c=map[i], v=d.cells[i], out;
        if(c.key===cfg.idKey){ row[c.key]=idRaw||null; return; }
        if(c.type==='date'){ out=D.parse(v,res.dates.order); if(!out.ok) out.why='is not a valid date'+(/^\s*\d{1,2}\D+\d{1,2}\D+\d{2,4}\s*$/.test(norm(v))?' (read as '+D.orderLabel(res.dates.order)+')':''); }
        else if(c.type==='number') out=toNumber(v,c);
        else if(c.type==='select') out=toOption(v,c);
        else out={ok:true,value:norm(v)};
        if(!out.ok){
          notes.push({field:c.key,note:c.label+' "'+norm(v)+'" '+(out.why||'is not a valid date')+'. Left blank.'});
          row[c.key]=null; return;
        }
        row[c.key]=out.value;
      });
      Object.keys(cfg.depKeys||{}).forEach(function(k){
        if(!(k in row)||!row[k]) return;
        var missing=depIds(row[k]).filter(function(x){ return !valid[x]; });
        if(missing.length){ dep=true; notes.push({field:k,note:cfg.depKeys[k]+' not found: '+missing.join(', ')}); }
      });
      if(dep) res.depIssueRows++;
      if(notes.some(function(n){ return !(n.field in (cfg.depKeys||{})); })) res.fieldIssueRows++;
      notes.forEach(function(n){ res.issues.push({rowNum:d.rowNum,id:idRaw||null,field:n.field,note:n.note}); });
      res.rows.push({rowNum:d.rowNum,data:row});
    });
    if(!res.rows.length&&res.skipped.length) res.fatal='Nothing to import: every ID in the file is already in the table ('+res.skipped.map(function(s){ return s.id; }).join(', ')+').';
    return res;
  }

  // meta: {time, file, user, assigned: {rowNum: id}}
  function logEntries(res,meta){
    return res.issues.map(function(i){
      return {time:meta.time,file:meta.file,user:meta.user,id:i.id||(meta.assigned&&meta.assigned[i.rowNum])||'',
              row:i.rowNum,field:i.field,note:i.note};
    });
  }
  function plural(n,w){ return n+' '+w+(n===1?'':'s'); }
  function summary(res,assigned,noun){
    var ids=Object.keys(assigned||{}).map(function(k){ return assigned[k]; }), w=noun||['milestone','milestones'];
    var out=['Imported '+res.rows.length+' '+(res.rows.length===1?w[0]:w[1])+'.'];
    if(res.dates&&res.dates.numeric) out.push('Dates read as '+root.SRETDates.orderLabel(res.dates.order)+'. '+res.dates.reason);
    if(ids.length) out.push('IDs assigned to '+plural(ids.length,'row')+' with a blank ID: '+ids.join(', ')+'.');
    if(res.skipped.length) out.push('Skipped '+plural(res.skipped.length,'row')+' already in the table: '+res.skipped.map(function(s){ return s.id; }).join(', ')+'.');
    if(res.issues.length) out.push(plural(res.issues.length,'issue')+' recorded in the Import log.');
    return out;
  }

  root.SRETMsImport={parseFile:parseFile,parseCsv:parseCsv,check:check,logEntries:logEntries,summary:summary};
})(window);
