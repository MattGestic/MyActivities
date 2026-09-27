/* =====================================================================
   SRET lists. The one implementation of "My temp list" and saved lists,
   shared by the grid view and the dashboard. Both call these functions;
   neither keeps its own copy of the rules.

   Purpose (Matt, 2026-09-27): let the user keep track of important
   activities in groups, aggregate them by a scope or reason, and build a
   selection set to bulk edit across several filtered states.

   Flow (Matt, 2026-09-27):
     1. Select items and add them to My temp list (any screen, any filter state).
     2. Expand the temp list to view its items; select some or all of them
        and add them to a saved list (an existing one, or a new one).
     3. Remove selected items from the temp list.
     4. Clear the temp list.
   Adding to a saved list leaves the temp list as it is: removing is step 3.

   Rules:
     - An item can be in any number of saved lists (default).
     - settings.singleList (a future setting, "Limit items to a single
       list"): when true, adding an item to a list moves it out of any other
       list, and the result says how many moved and from where.
     - The temp list is independent of saved lists.
     - The temp list is working state for the session; saved lists belong to
       the annotation layer and are persisted by the caller.

   Store (owned and persisted by the caller):
     { seq, settings: { singleList: false }, temp: [ref],
       list: [ { id, name, items: [ref], createdAt, updatedAt } ] }
   A ref is a caller-chosen stable string, e.g. 'activity:SNIP-118' (schedule
   activity or user milestone, so the same activity from any screen is one
   item) or 'annot:A-004'.

   Reads and writes no app global. Never touches schedule data.
   ===================================================================== */
(function(root){
  'use strict';

  function newStore(opts){ return {seq:0,settings:{singleList:!!(opts&&opts.singleList)},temp:[],list:[]}; }
  function ensure(store){
    if(!store.temp) store.temp=[]; if(!store.list) store.list=[]; if(!store.settings) store.settings={singleList:false};
    return store;
  }
  function single(store){ return !!(store.settings&&store.settings.singleList); }
  function normName(n){ return String(n==null?'':n).replace(/\s+/g,' ').trim(); }
  function stamp(now){ return now||new Date().toISOString(); }
  function uniqueRefs(refs){
    var out=[];
    (refs||[]).forEach(function(r){ r=r==null?'':String(r); if(r && out.indexOf(r)<0) out.push(r); });
    return out;
  }
  function find(store,id){
    for(var i=0;i<store.list.length;i++) if(store.list[i].id===id) return store.list[i];
    return null;
  }
  function findByName(store,name){
    var k=normName(name).toLowerCase();
    for(var i=0;i<store.list.length;i++) if(store.list[i].name.toLowerCase()===k) return store.list[i];
    return null;
  }
  function listsOf(store,ref){
    return store.list.filter(function(c){ return c.items.indexOf(ref)>=0; });
  }

  // ---------- temp list ----------
  function temp(store){ return ensure(store).temp.slice(); }
  function inTemp(store,ref){ return ensure(store).temp.indexOf(String(ref))>=0; }
  function tempAdd(store,refs){
    ensure(store);
    var added=0, already=0;
    uniqueRefs(refs).forEach(function(r){
      if(store.temp.indexOf(r)>=0) already++; else { store.temp.push(r); added++; }
    });
    return {kind:'tempAdd',added:added,already:already,total:store.temp.length};
  }
  function tempRemove(store,refs){
    ensure(store);
    var removed=0;
    uniqueRefs(refs).forEach(function(r){ var i=store.temp.indexOf(r); if(i>=0){ store.temp.splice(i,1); removed++; } });
    return {kind:'tempRemove',removed:removed,total:store.temp.length};
  }
  function tempClear(store){
    ensure(store);
    var n=store.temp.length; store.temp=[];
    return {kind:'tempClear',cleared:n,total:0};
  }

  // ---------- saved lists ----------
  function list(store){
    return ensure(store).list.map(function(c){ return {id:c.id,label:c.name,count:c.items.length}; });
  }
  // Names of every saved list holding ref, in list order.
  function membership(store,ref){
    return listsOf(ensure(store),String(ref)).map(function(c){ return c.name; });
  }
  function create(store,name,now){
    ensure(store);
    var n=normName(name);
    if(!n) return {error:'Enter a name for the list.'};
    if(n.length>60) return {error:'Keep the list name to 60 characters or fewer.'};
    if(n.toLowerCase()==='my temp list') return {error:'That name is used by the temp list. Choose another.'};
    if(findByName(store,n)) return {error:'A list called "'+n+'" already exists.'};
    store.seq=(store.seq||0)+1;
    var c={id:'UL-'+String(store.seq).padStart(3,'0'),name:n,items:[],createdAt:stamp(now),updatedAt:stamp(now)};
    store.list.push(c);
    return {collection:c};
  }
  // Adds refs to one list. One already in this list is counted, never
  // duplicated. With settings.singleList, one in another list moves.
  function assign(store,id,refs,now){
    ensure(store);
    var c=find(store,id);
    if(!c) return {error:'That list no longer exists.'};
    var added=0, already=0, movedFrom={};
    uniqueRefs(refs).forEach(function(r){
      if(c.items.indexOf(r)>=0){ already++; return; }
      if(single(store)) listsOf(store,r).forEach(function(other){
        other.items.splice(other.items.indexOf(r),1); other.updatedAt=stamp(now);
        movedFrom[other.name]=(movedFrom[other.name]||0)+1;
      });
      c.items.push(r); added++;
    });
    if(added) c.updatedAt=stamp(now);
    return {kind:'assign',collection:c,added:added,already:already,movedFrom:movedFrom};
  }
  // The items of one saved list (a copy), or [] when it does not exist.
  function itemsOf(store,id){ var c=find(ensure(store),id); return c?c.items.slice():[]; }
  // ids of every saved list holding ref (for filtering by list).
  function listIdsOf(store,ref){
    return listsOf(ensure(store),String(ref)).map(function(c){ return c.id; });
  }
  // Takes refs out of one saved list; the items and other lists are untouched.
  function removeFromList(store,id,refs,now){
    ensure(store);
    var c=find(store,id);
    if(!c) return {error:'That list no longer exists.'};
    var removed=0;
    uniqueRefs(refs).forEach(function(r){ var i=c.items.indexOf(r); if(i>=0){ c.items.splice(i,1); removed++; } });
    if(removed) c.updatedAt=stamp(now);
    return {kind:'removeFromList',collection:c,removed:removed};
  }
  // Deletes the list itself. Its items stay wherever else they are.
  function deleteList(store,id){
    ensure(store);
    var c=find(store,id);
    if(!c) return {error:'That list no longer exists.'};
    store.list.splice(store.list.indexOf(c),1);
    return {kind:'deleteList',collection:c,count:c.items.length};
  }
  function unassign(store,refs,now){
    ensure(store);
    var removed=0;
    uniqueRefs(refs).forEach(function(r){
      var cs=listsOf(store,r); cs.forEach(function(c){ c.items.splice(c.items.indexOf(r),1); c.updatedAt=stamp(now); });
      if(cs.length) removed++;
    });
    return {kind:'unassign',removed:removed};
  }

  // ---------- step 2: selected temp items into a saved list ----------
  // refs: the temp items the user selected; only refs on the temp list count.
  // The temp list is left as it is.
  function pickFromTemp(store,refs){
    return uniqueRefs(refs).filter(function(r){ return store.temp.indexOf(r)>=0; });
  }
  function addFromTemp(store,id,refs,now){
    ensure(store);
    var picked=pickFromTemp(store,refs);
    if(!picked.length) return {error:'Select items on My temp list first.'};
    if(!find(store,id)) return {error:'Choose a saved list to add to.'};
    var r=assign(store,id,picked,now); r.kind='addFromTemp';
    return r;
  }
  function saveFromTemp(store,name,refs,now){
    ensure(store);
    var picked=pickFromTemp(store,refs);
    if(!picked.length) return {error:'Select items on My temp list first.'};
    var made=create(store,name,now); if(made.error) return made;
    var r=assign(store,made.collection.id,picked,now); r.kind='saveFromTemp';
    return r;
  }

  // ---------- the sentence both UIs show ----------
  function plural(n,word){ return n+' '+word+(n===1?'':'s'); }
  function describe(r){
    if(!r) return '';
    if(r.error) return r.error;
    switch(r.kind){
      case 'tempAdd':
        return (r.added?'Added '+plural(r.added,'item')+' to My temp list.':'No new items added to My temp list.')+
               (r.already?' '+plural(r.already,'item')+' '+(r.already===1?'was':'were')+' already on it.':'')+
               ' It now holds '+plural(r.total,'item')+'.';
      case 'tempRemove': return 'Removed '+plural(r.removed,'item')+' from My temp list. It now holds '+plural(r.total,'item')+'.';
      case 'tempClear':  return 'Cleared My temp list ('+plural(r.cleared,'item')+').';
      case 'unassign':   return 'Removed '+plural(r.removed,'item')+' from their lists.';
      case 'removeFromList': return 'Removed '+plural(r.removed,'item')+' from "'+r.collection.name+'".';
      case 'deleteList':  return 'Deleted the list "'+r.collection.name+'" ('+plural(r.count,'item')+'). The items themselves are unchanged.';
    }
    var name='"'+r.collection.name+'"';
    var s=(r.kind==='saveFromTemp'?'Saved '+plural(r.added+r.already,'item')+' as the new list '+name+'.'
          :(r.added?'Added '+plural(r.added,'item')+' to '+name+'.':'No new items added to '+name+'.'));
    if(r.already) s+=' '+plural(r.already,'item')+' '+(r.already===1?'was':'were')+' already in it.';
    var mv=Object.keys(r.movedFrom||{});
    if(mv.length) s+=' Moved from '+mv.map(function(k){ return '"'+k+'" ('+r.movedFrom[k]+')'; }).join(', ')+'.';
    return s;
  }

  root.SRETCollections={newStore:newStore,temp:temp,inTemp:inTemp,tempAdd:tempAdd,tempRemove:tempRemove,
                        tempClear:tempClear,list:list,membership:membership,create:create,assign:assign,
                        unassign:unassign,listIdsOf:listIdsOf,itemsOf:itemsOf,removeFromList:removeFromList,deleteList:deleteList,
                        addFromTemp:addFromTemp,saveFromTemp:saveFromTemp,describe:describe};
})(window);
