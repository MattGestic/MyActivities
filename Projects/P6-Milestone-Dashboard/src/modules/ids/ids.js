/* =====================================================================
   SRET user task IDs and identity (Matt, 2026-09-29). No UI, no app globals.

   IDs people read: a prefix, a dash and a number, numbered within each
   prefix's own series. The default prefix is U + the user's initials:
     Matt Garrett  -> UMG-001, UMG-002        Jo Ruiz -> UJR-001
   The user can set their own prefix to group tasks, e.g. A100 while
   working on area 100 (A100-001, A100-002), then A200 (A200-001); going
   back to A100 carries on at A100-003. Prefix: 1 to 8 letters or digits,
   starting with a letter, stored in upper case. Initials: first letter of
   the first and last word of the confirmed user name (SRETUser); a
   one-word name gives its first two letters; no name gives UXX. Tasks
   created before this keep their USR-013 IDs.

   Identity for merging: every user task also carries a GUID, set once when
   it is created (or when an older task is first loaded) and never changed.
   Merging another file's tasks in, an incoming task whose ID is already
   here is
     - the same task (same GUID)          -> kept once, not duplicated
     - a different task (different GUID)  -> given the next free number in
       its own series (A100-004 stays A100-, USR-013 stays USR-), and every
       reference to it in the incoming data (predecessors, successors,
       annotation keys) is rewritten to match.
   This happens when two people use the same prefix. Older tasks without a GUID match when the ID, name and created
   date all agree; otherwise they are treated as different tasks.

   API (window.SRETIds):
     prefix(name)                   -> 'UMG'   ('Matt Garrett'), 'UDU' ('Demo user'), 'UXX' (no name): the default
     checkPrefix(p, scheduleIds)    -> {ok, value:'A100', warning} | {ok:false, error}
     next(existingIds, prefix, taken) -> 'A100-004' (one above the highest in that prefix's series)
     seriesOf(id)                   -> 'A100' for A100-004, null if not prefix-dash-number
     isUserId(id, prefixes)         -> true for USR-, U + two letters, or any prefix in the list
     guid()                         -> '3f2a9c1e-7b4d-4e8a-9f10-2c6d8e4b1a07' (random, version 4)
     ensureGuids(tasks)             -> number of older tasks given a GUID
     merge(local, incoming, opts)   -> {add, same, renamed:[{from,to,name,guid}], map:{from:to}}
        opts: {idKey:'id', refKeys:['pred','succ'], nameKey:'name', createdKey:'created'}
     rewriteKeys(obj, map)          -> copy of the incoming file's ID-keyed store (annotations), keys renamed
     rewriteRefs(text, map)         -> a predecessor/successor string with IDs renamed
   ===================================================================== */
(function(root){
  'use strict';
  // Any series: a prefix (starting with a letter), a dash, a number.
  var RX=/^([A-Z][A-Z0-9]{0,7})-(\d+)$/;
  var DEFAULT_RX=/^(U[A-Z]{2}|USR)-\d+$/;

  function prefix(name){
    var w=String(name||'').replace(/[^A-Za-z\s'-]/g,' ').trim().split(/[\s'-]+/).filter(Boolean);
    if(!w.length) return 'UXX';
    var s=w.length===1?(w[0]+'X').slice(0,2):w[0].charAt(0)+w[w.length-1].charAt(0);
    return 'U'+s.toUpperCase();
  }
  function checkPrefix(p,scheduleIds){
    var v=String(p==null?'':p).trim().toUpperCase().replace(/-+$/,'');
    if(!v) return {ok:false,error:'Enter a prefix, e.g. A100.'};
    if(!/^[A-Z][A-Z0-9]*$/.test(v)) return {ok:false,error:'Use letters and digits only, starting with a letter.'};
    if(v.length>8) return {ok:false,error:'Use 8 characters or fewer.'};
    var clash=(scheduleIds||[]).some(function(id){ return String(id).toUpperCase().indexOf(v+'-')===0; });
    return {ok:true,value:v,warning:clash?'Schedule activities already use '+v+'-. Task IDs will look like theirs.':''};
  }
  function seriesOf(id){ var m=RX.exec(String(id||'').toUpperCase()); return m?m[1]:null; }
  function isUserId(id,prefixes){
    var s=String(id||'').toUpperCase();
    if(DEFAULT_RX.test(s)) return true;
    var se=seriesOf(s); return !!se&&(prefixes||[]).map(function(x){ return String(x).toUpperCase(); }).indexOf(se)>=0;
  }
  function pad(n){ return String(n).padStart(3,'0'); }
  function seriesNext(series,ids){
    var max=0;
    ids.forEach(function(id){ var m=RX.exec(String(id||'').toUpperCase()); if(m&&m[1]===series) max=Math.max(max,+m[2]); });
    return series+'-'+pad(max+1);
  }
  function next(existing,pfx,taken){ return seriesNext(String(pfx||'UXX').toUpperCase(),(existing||[]).concat(taken||[])); }
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
      // A different task under the same ID: the next free number in its own series.
      var nid=seriesNext(seriesOf(id)||'USR',taken);
      taken.push(nid); map[id]=nid; t[o.idKey]=nid;
      res.renamed.push({from:id,to:nid,name:t[o.nameKey]||'',guid:t.guid||''});
      res.add.push(t);
    });
    // References inside the incoming tasks follow the renames.
    if(Object.keys(map).length) res.add.concat(res.same).forEach(function(t){ o.refKeys.forEach(function(k){ if(k in t) t[k]=rewriteRefs(t[k],map); }); });
    return res;
  }

  root.SRETIds={prefix:prefix,checkPrefix:checkPrefix,seriesOf:seriesOf,isUserId:isUserId,guid:guid,next:next,ensureGuids:ensureGuids,merge:merge,rewriteKeys:rewriteKeys,rewriteRefs:rewriteRefs};
})(window);
