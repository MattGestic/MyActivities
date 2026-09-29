/* =====================================================================
   SRET user task identity (Matt, 2026-09-29). No UI, no app globals.

   The USR- ID stays what people read (USR-001, USR-002, numbered in
   order). Two people adding tasks in their own copies can both create
   USR-013, so the ID alone cannot say which task is which when their files
   are merged. Each task therefore carries a GUID, set once when it is
   created (or when an older task is first loaded) and never changed.

   Merging another file's tasks in, an incoming task whose USR- ID is
   already here is
     - the same task (same GUID)          -> kept once, not duplicated
     - a different task (different GUID)  -> given the next free USR- number,
       and every reference to it in the incoming data (predecessors,
       successors, annotation keys) is rewritten to match.
   Older tasks without a GUID match when the ID, name and created date all
   agree; otherwise they are treated as different tasks.

   API (window.SRETIds):
     guid()                         -> '3f2a9c1e-7b4d-4e8a-9f10-2c6d8e4b1a07' (random, version 4)
     next(existingIds, taken)       -> 'USR-014' (one above the highest in use)
     ensureGuids(tasks)             -> number of older tasks given a GUID
     merge(local, incoming, opts)   -> {add, same, renamed:[{from,to,name,guid}], map:{from:to}}
        opts: {idKey:'id', refKeys:['pred','succ'], nameKey:'name', createdKey:'created'}
     rewriteKeys(obj, map)          -> copy of the incoming file's ID-keyed store (annotations), keys renamed
     rewriteRefs(text, map)         -> a predecessor/successor string with IDs renamed
   ===================================================================== */
(function(root){
  'use strict';
  var RX=/^USR-(\d+)$/;

  function pad(n){ return String(n).padStart(3,'0'); }
  function next(existing,taken){
    var max=0;
    (existing||[]).concat(taken||[]).forEach(function(id){ var m=RX.exec(String(id||'')); if(m) max=Math.max(max,+m[1]); });
    return 'USR-'+pad(max+1);
  }
  function guid(){
    try{ if(root.crypto&&root.crypto.randomUUID) return root.crypto.randomUUID(); }catch(e){}
    var b=new Uint8Array(16);
    try{ root.crypto.getRandomValues(b); }catch(e){ for(var k=0;k<16;k++) b[k]=Math.floor(Math.random()*256); }
    b[6]=(b[6]&15)|64; b[8]=(b[8]&63)|128;
    var h=Array.prototype.map.call(b,function(x){ return (x+256).toString(16).slice(1); }).join('');
    return h.slice(0,8)+'-'+h.slice(8,12)+'-'+h.slice(12,16)+'-'+h.slice(16,20)+'-'+h.slice(20);
  }
  function ensureGuids(tasks){ var n=0; (tasks||[]).forEach(function(t){ if(t&&!t.guid){ t.guid=guid(); n++; } }); return n; }

  function rewriteRefs(text,map){
    if(text==null||text==='') return text;
    return String(text).split(/([,;])/).map(function(tok){
      if(tok===','||tok===';') return tok;
      return tok.replace(/^(\s*)([^\s:]+)/,function(all,sp,id){ return sp+(map[id]||id); });
    }).join('');
  }
  function rewriteKeys(obj,map){
    var out={}; Object.keys(obj||{}).forEach(function(k){ out[map[k]||k]=obj[k]; }); return out;
  }
  function sameTask(a,b,o){
    if(a.guid&&b.guid) return a.guid===b.guid;
    return String(a[o.nameKey]||'')===String(b[o.nameKey]||'')&&String(a[o.createdKey]||'')===String(b[o.createdKey]||'');
  }
  function merge(local,incoming,opts){
    var o=Object.assign({idKey:'id',refKeys:['pred','succ'],nameKey:'name',createdKey:'created'},opts||{});
    var byId={}; (local||[]).forEach(function(t){ byId[t[o.idKey]]=t; });
    var taken=Object.keys(byId), map={}, res={add:[],same:[],renamed:[],map:map};
    var copies=(incoming||[]).map(function(t){ return Object.assign({},t); });
    // IDs used by the incoming file itself also count as taken.
    copies.forEach(function(t){ taken.push(t[o.idKey]); });
    copies.forEach(function(t){
      var id=t[o.idKey], here=byId[id];
      if(!here){ res.add.push(t); return; }
      if(sameTask(here,t,o)){ res.same.push(t); return; }
      // A different task under the same ID: the next free USR- number.
      var nid=next(taken,[]);
      taken.push(nid); map[id]=nid; t[o.idKey]=nid;
      res.renamed.push({from:id,to:nid,name:t[o.nameKey]||'',guid:t.guid||''});
      res.add.push(t);
    });
    // References inside the incoming tasks follow the renames.
    if(Object.keys(map).length) res.add.concat(res.same).forEach(function(t){ o.refKeys.forEach(function(k){ if(k in t) t[k]=rewriteRefs(t[k],map); }); });
    return res;
  }

  root.SRETIds={guid:guid,next:next,ensureGuids:ensureGuids,merge:merge,rewriteKeys:rewriteKeys,rewriteRefs:rewriteRefs};
})(window);
