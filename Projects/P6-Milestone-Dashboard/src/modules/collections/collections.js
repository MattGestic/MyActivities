/* =====================================================================
   SRET lists. The one implementation of "My temp list" and saved lists,
   shared by the grid view and the dashboard. Both call these functions;
   neither keeps its own copy of the rules.

   Purpose (Matt, 2026-09-27): let the user keep track of important
   activities in groups, aggregate them by a scope or reason, and build a
   selection set to bulk edit across several filtered states.

   Flow:
     1. My temp list: a quick pick list. Items are added from any screen and
        any filter state, and removed the same way.
     2. Then one of:
        A. Save new list      the temp items become a new named list
        B. Add to existing    the temp items join a saved list
        C. Clear              the temp list is emptied
     A and B empty the temp list afterwards (it has been fed).

   Rules:
     - An item is in at most one saved list. Adding it to another list moves
       it, and the result says how many moved and from where.
     - The temp list is independent of saved lists: an item can be picked
       whether or not it is already in a list.
     - The temp list is working state for the session; saved lists belong to
       the annotation layer and are persisted by the caller.

   Store (owned and persisted by the caller):
     { seq, temp: [ref], list: [ { id, name, items: [ref], createdAt, updatedAt } ] }
   A ref is a caller-chosen stable string, e.g. 'activity:SNIP-118' (schedule
   activity or user milestone, so the same activity from any screen is one
   item) or 'annot:A-004'.

   Reads and writes no app global. Never touches schedule data.
   ===================================================================== */
(function(root){
  'use strict';

  function newStore(){ return {seq:0,temp:[],list:[]}; }
  function ensure(store){ if(!store.temp) store.temp=[]; if(!store.list) store.list=[]; return store; }
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
  function listOf(store,ref){
    for(var i=0;i<store.list.length;i++) if(store.list[i].items.indexOf(ref)>=0) return store.list[i];
    return null;
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
  function membership(store,ref){
    var c=listOf(ensure(store),String(ref)); return c?c.name:'';
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
  // Adds refs to one list. An item already in another list moves; one already
  // in this list is counted, never duplicated.
  function assign(store,id,refs,now){
    ensure(store);
    var c=find(store,id);
    if(!c) return {error:'That list no longer exists.'};
    var added=0, already=0, movedFrom={};
    uniqueRefs(refs).forEach(function(r){
      if(c.items.indexOf(r)>=0){ already++; return; }
      var other=listOf(store,r);
      if(other){
        other.items.splice(other.items.indexOf(r),1); other.updatedAt=stamp(now);
        movedFrom[other.name]=(movedFrom[other.name]||0)+1;
      }
      c.items.push(r); added++;
    });
    if(added) c.updatedAt=stamp(now);
    return {kind:'assign',collection:c,added:added,already:already,movedFrom:movedFrom};
  }
  function unassign(store,refs,now){
    ensure(store);
    var removed=0;
    uniqueRefs(refs).forEach(function(r){
      var c=listOf(store,r); if(c){ c.items.splice(c.items.indexOf(r),1); c.updatedAt=stamp(now); removed++; }
    });
    return {kind:'unassign',removed:removed};
  }

  // ---------- A and B: feed the temp list into a list ----------
  function saveTemp(store,name,now){
    ensure(store);
    if(!store.temp.length) return {error:'The temp list is empty. Add rows to it first.'};
    var made=create(store,name,now); if(made.error) return made;
    var r=assign(store,made.collection.id,store.temp,now);
    tempClear(store); r.kind='saveTemp'; r.total=0;
    return r;
  }
  function addTempTo(store,id,now){
    ensure(store);
    if(!store.temp.length) return {error:'The temp list is empty. Add rows to it first.'};
    if(!find(store,id)) return {error:'That list no longer exists.'};
    var r=assign(store,id,store.temp,now);
    tempClear(store); r.kind='addTempTo'; r.total=0;
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
    }
    var name='"'+r.collection.name+'"';
    var s=(r.kind==='saveTemp'?'Saved '+plural(r.added+r.already,'item')+' as the new list '+name+'.'
          :(r.added?'Added '+plural(r.added,'item')+' to '+name+'.':'No new items added to '+name+'.'));
    if(r.already) s+=' '+plural(r.already,'item')+' '+(r.already===1?'was':'were')+' already in it.';
    var mv=Object.keys(r.movedFrom||{});
    if(mv.length) s+=' Moved from '+mv.map(function(k){ return '"'+k+'" ('+r.movedFrom[k]+')'; }).join(', ')+'.';
    if(r.kind==='saveTemp'||r.kind==='addTempTo') s+=' My temp list is now empty.';
    return s;
  }

  root.SRETCollections={newStore:newStore,temp:temp,inTemp:inTemp,tempAdd:tempAdd,tempRemove:tempRemove,
                        tempClear:tempClear,list:list,membership:membership,create:create,assign:assign,
                        unassign:unassign,saveTemp:saveTemp,addTempTo:addTempTo,describe:describe};
})(window);
