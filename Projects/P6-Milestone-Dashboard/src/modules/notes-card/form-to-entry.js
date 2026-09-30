/* =====================================================================
   SRETFormToEntry: the milestone card's save, reduced to ONE entry draft.
   Pure: no DOM, no app globals, no stores. The caller passes in what it
   knows (ctx) and gets back a draft to hand to the entry writer.

   formToEntry(clean, now, ctx) -> {draft, shortTitle} | null

     clean  msReadForm() taken when the card opened
     now    msReadForm() taken at save
     ctx    {key, own(field), current(field), scheduleProgress,
             floatReadOnly, parseDate(str) -> ISO | null}
              own(field)      the milestone's source value (_msBase or m[f])
              current(field)  the effective value shown before editing

   draft = {target:{kind:'ms', key}, text, changes:{field:{from, to}},
            origin:'card', status:'open'}
   changes only carry fields the user TOUCHED (now[f] !== clean[f]).
   from = ctx.current(field). to = the new value, or null = "back to the
   schedule value".

   Differences from saveMsDialog (deliberate, entries record intent):
     - saveMsDialog also re-puts a field that is untouched but already has a
       stored override (its `!(f in ov)` guard). Here an untouched field is
       never included, however it is stored.
     - A change whose result equals what the card already showed is dropped.
     - shortTitle is not an entry field; it is returned beside the draft.
   ===================================================================== */
(function(root){
  'use strict';

  // form key -> entry field name
  var FIELD = {title:'actName', start:'start', date:'date', weight:'weight',
               floatD:'floatD', type:'type', marker:'marker',
               progress:'progress', health:'health'};
  var ORDER = ['title','start','date','weight','floatD','type','marker','progress','health'];

  function norm(v){ return (v===undefined||v===''||v!==v)?null:v; }
  function same(a,b){
    a=norm(a); b=norm(b);
    if(a===b) return true;
    if(a===null||b===null) return false;
    return String(a)===String(b);
  }

  // The new value for one form field. {skip:true} = leave alone, otherwise
  // {to}, where to === null means back to the schedule value.
  function newValue(f, now, ctx){
    var raw=now[f], s;
    switch(f){
      case 'title': case 'marker': case 'type':
        s=(raw==null)?'':String(raw).trim();
        return {to:s===''?null:s};
      case 'start': case 'date':
        s=(raw==null)?'':String(raw).trim();
        if(s==='') return {to:null};
        var iso=ctx.parseDate(s);
        if(!iso) return {skip:true};          // a typo is not an instruction
        return {to:iso};
      case 'weight': case 'floatD':
        if(f==='floatD'&&ctx.floatReadOnly) return {skip:true};
        s=(raw==null)?'':String(raw).trim();
        var n=(s==='')?NaN:parseFloat(s);
        return {to:isNaN(n)?null:n};
      case 'progress':
        s=(raw==null)?'':String(raw).replace('%','').trim();
        var p=(s==='')?NaN:parseFloat(s);
        if(isNaN(p)) return {to:null};
        p=Math.min(100,Math.max(0,Math.round(p)));
        return {to:same(p,ctx.scheduleProgress)?null:p};
      case 'health':
        return {to:(raw===-1||raw==null)?null:raw};   // 0 is a real value
    }
    return {skip:true};
  }

  function formToEntry(clean, now, ctx){
    if(!now) return null;
    clean=clean||now;
    var changes={}, nChanges=0;

    ORDER.forEach(function(f){
      if(now[f]===clean[f]) return;                    // untouched
      var r=newValue(f, now, ctx);
      if(r.skip) return;
      var to=r.to, ef=FIELD[f], from=ctx.current(ef);
      // A value equal to the schedule's own means back to the schedule.
      if(to!==null&&f!=='health'&&same(to,ctx.own(ef))) to=null;
      // Dropped when nothing would change: to equals from, or "back to
      // schedule" while the card already showed the schedule value.
      if(same(to,from)) return;
      if(to===null&&f!=='health'){
        var sched=(f==='progress')?ctx.scheduleProgress:ctx.own(ef);
        if(sched!==undefined&&same(sched,from)) return;
      }
      changes[ef]={from:from, to:to};
      nChanges++;
    });

    var shortTitle=(now.shortTitle!==clean.shortTitle)?now.shortTitle:null;
    var text=String(now.comment==null?'':now.comment).trim();
    var carried=text===String(clean.comment==null?'':clean.comment).trim();

    if(!nChanges&&(text===''||carried)){
      // Nothing for the entry log. A short-title-only edit still has to reach
      // the app's own store, so it is returned without a draft.
      return shortTitle===null?null:{draft:null, shortTitle:shortTitle};
    }
    return {
      draft:{target:{kind:'ms', key:ctx.key}, text:text, changes:changes,
             origin:'card', status:'open'},
      shortTitle:shortTitle
    };
  }

  var api={formToEntry:formToEntry};
  root.SRETFormToEntry=api;
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
})(typeof window!=='undefined'?window:(typeof globalThis!=='undefined'?globalThis:this));
