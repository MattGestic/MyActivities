/* =====================================================================
   SRET user-defined collections. The one implementation of "put these
   items in a collection", shared by the grid view and the dashboard
   (Notes list bulk bar, board selection). Both call these functions; neither
   keeps its own copy of the rules.

   Pure functions over a store object the caller owns and persists:
     { seq: 0, list: [ { id, name, items: [ref, ...], createdAt, updatedAt } ] }
   A ref is a string the caller chooses, stable across sessions, e.g.
   'activity:SNIP-118' for a schedule item or user milestone, 'annot:A-004'
   for an annotation entry. Using the same ref from two screens means the same
   member, so adding SNIP-118 from the grid and from the board is one item.

   This module reads and writes no app global. It lives in the annotation
   layer: it never touches schedule data.

   API (window.SRETCollections):
     newStore()
     list(store)                       -> [{id,label,count}]
     create(store, name, now)          -> {collection} | {error}
     assign(store, id, refs, now)      -> {collection, added, already} | {error}
     unassign(store, id, refs, now)    -> {collection, removed} | {error}
     membership(store, ref)            -> [collection names]
     describe(result)                  -> one user-facing sentence
   ===================================================================== */
(function(root){
  'use strict';

  function newStore(){ return {seq:0,list:[]}; }
  function normName(n){ return String(n==null?'':n).replace(/\s+/g,' ').trim(); }
  function find(store,id){
    for(var i=0;i<store.list.length;i++) if(store.list[i].id===id) return store.list[i];
    return null;
  }
  function findByName(store,name){
    var k=normName(name).toLowerCase();
    for(var i=0;i<store.list.length;i++) if(store.list[i].name.toLowerCase()===k) return store.list[i];
    return null;
  }
  function uniqueRefs(refs){
    var out=[];
    (refs||[]).forEach(function(r){ r=String(r); if(r && out.indexOf(r)<0) out.push(r); });
    return out;
  }
  function stamp(now){ return now||new Date().toISOString(); }

  function list(store){
    return store.list.map(function(c){ return {id:c.id,label:c.name,count:c.items.length}; });
  }
  function create(store,name,now){
    var n=normName(name);
    if(!n) return {error:'Enter a name for the collection.'};
    if(n.length>60) return {error:'Keep the collection name to 60 characters or fewer.'};
    if(findByName(store,n)) return {error:'A collection called "'+n+'" already exists.'};
    store.seq=(store.seq||0)+1;
    var c={id:'UC-'+String(store.seq).padStart(3,'0'),name:n,items:[],createdAt:stamp(now),updatedAt:stamp(now)};
    store.list.push(c);
    return {collection:c};
  }
  // Idempotent: a ref already in the collection is counted, never duplicated.
  function assign(store,id,refs,now){
    var c=find(store,id);
    if(!c) return {error:'That collection no longer exists.'};
    var added=0, already=0;
    uniqueRefs(refs).forEach(function(r){
      if(c.items.indexOf(r)>=0) already++;
      else { c.items.push(r); added++; }
    });
    if(added) c.updatedAt=stamp(now);
    return {collection:c,added:added,already:already};
  }
  function unassign(store,id,refs,now){
    var c=find(store,id);
    if(!c) return {error:'That collection no longer exists.'};
    var removed=0;
    uniqueRefs(refs).forEach(function(r){
      var i=c.items.indexOf(r); if(i>=0){ c.items.splice(i,1); removed++; }
    });
    if(removed) c.updatedAt=stamp(now);
    return {collection:c,removed:removed};
  }
  function membership(store,ref){
    ref=String(ref);
    return store.list.filter(function(c){ return c.items.indexOf(ref)>=0; }).map(function(c){ return c.name; });
  }
  function plural(n,word){ return n+' '+word+(n===1?'':'s'); }
  function describe(r){
    if(!r) return '';
    if(r.error) return r.error;
    var name='"'+r.collection.name+'"';
    if(r.removed!=null) return 'Removed '+plural(r.removed,'item')+' from '+name+'.';
    var s=r.added?('Added '+plural(r.added,'item')+' to '+name+'.'):('No new items added to '+name+'.');
    if(r.already) s+=' '+plural(r.already,'item')+' '+(r.already===1?'was':'were')+' already in it.';
    return s;
  }

  root.SRETCollections={newStore:newStore,list:list,create:create,assign:assign,unassign:unassign,
                        membership:membership,describe:describe};
})(window);
