/* =====================================================================
   SRET entries (P65, M1 + M2). The one append-only record of every
   milestone update: a remark, a start or finish date, a health or status,
   a progress figure, any other field edit. Each is an ENTRY in one array.

   The stores the app already reads (MS_COMMENTS, MS_HEALTH_OVERRIDE,
   MS_PROGRESS_OVERRIDE, MS_FIELD_OVERRIDE, DEP_COMMENTS, the row overrides
   and NOTES) become PROJECTIONS of that array, in their exact current
   shapes, so their readers stay as they are. projectEntries() is that
   projection. migrateLegacy() / importLegacy() turn a P64-or-older payload
   into entries, idempotently.

   Entry (fixed contract):
     { eid:'E-0001', target:{kind:'ms'|'general'|'dep'|'row', key:string|null},
       links:[ID], period:'YYYY-MM-DD', at:ISO, updatedAt:ISO, by:null,
       status:'note'|'open'|'sent'|'review'|'outstanding'|'done'|'closed',
       text:string, changes:{ <field>:{from, to} }, origin:string,
       followsUp:eid|null, nid?:'N-###', sig?:string, clearText?:true }
   to:null in a change means "back to the schedule / no override".

   Pure functions over an array the caller owns and persists. create() is a
   thin convenience that binds them to one array and one clock.

   Reads and writes no app global. Never touches schedule data. No network,
   no dependencies. Exposes window.SRETEntries, and module.exports for Node.
   ===================================================================== */
(function(root){
  'use strict';

  var SCHEMA_VERSION=2;
  var KINDS=['ms','general','dep','row'];
  var STATUSES=['note','open','sent','review','outstanding','done','closed'];
  var OPEN_STATUSES=['open','sent','review','outstanding'];
  // The milestone's own schedule fields, exactly MS_EDITABLE_FIELDS in the app.
  var MS_FIELDS=['actName','start','date','weight','floatD','type','marker'];
  var CHANGE_FIELDS=MS_FIELDS.concat(['health','progress','rowHealth','rowRemark']);
  var DEFAULT_WINDOW_MS=10*60*1000;

  // ---- small helpers --------------------------------------------------
  function has(o,k){ return Object.prototype.hasOwnProperty.call(o,k); }
  function isObj(v){ return !!v&&typeof v==='object'&&!Array.isArray(v); }
  function toMs(v){
    if(v==null) return Date.now();
    if(typeof v==='number') return v;
    if(v instanceof Date) return v.getTime();
    var t=Date.parse(v); return isNaN(t)?Date.now():t;
  }
  function iso(ms){ return new Date(ms).toISOString(); }
  function pad(n,w){ n=String(n); while(n.length<w) n='0'+n; return n; }
  function isoDay(d){
    return (d instanceof Date&&!isNaN(d))
      ? d.getFullYear()+'-'+pad(d.getMonth()+1,2)+'-'+pad(d.getDate(),2) : null;
  }
  // The app's weekEndOf(): the week-ending day on or after d, local time.
  function weekEndISO(d,weekDay){
    var x=(d instanceof Date)?new Date(d.getTime()):new Date(String(d).length<=10?d+'T00:00:00':d);
    if(isNaN(x)) return null;
    x.setHours(0,0,0,0);
    x.setDate(x.getDate()+((weekDay||0)-x.getDay()+7)%7);
    return isoDay(x);
  }
  // Canonical JSON: sorted keys, so equal values always serialise equally.
  function canon(v){
    if(v===undefined) return 'null';
    if(v===null||typeof v!=='object') return JSON.stringify(v);
    if(Array.isArray(v)) return '['+v.map(canon).join(',')+']';
    return '{'+Object.keys(v).sort().filter(function(k){ return v[k]!==undefined; })
      .map(function(k){ return JSON.stringify(k)+':'+canon(v[k]); }).join(',')+'}';
  }
  function same(a,b){
    if(a===b) return true;
    if(a==null||b==null) return (a==null)&&(b==null);
    return canon(a)===canon(b);
  }
  function clone(v){ return v==null?v:JSON.parse(JSON.stringify(v)); }
  // Two 32-bit hashes (FNV-1a and djb2) side by side: 64 bits, stable
  // across runs and engines, no crypto API needed.
  function hash(s){
    var h1=0x811c9dc5, h2=5381;
    for(var i=0;i<s.length;i++){
      var c=s.charCodeAt(i);
      h1^=c; h1=Math.imul(h1,0x01000193)>>>0;
      h2=((Math.imul(h2,33)>>>0)^c)>>>0;
    }
    return pad(h1.toString(16),8)+pad(h2.toString(16),8);
  }
  function normStatus(st){
    if(st==='pending') return 'review';           // the app's normNoteStatus()
    return STATUSES.indexOf(st)>=0?st:'open';
  }
  function eidNum(eid){ var m=/^E-(\d+)$/.exec(String(eid||'')); return m?parseInt(m[1],10):0; }
  function nidNum(nid){ var n=parseInt(String(nid||'').replace(/\D/g,''),10); return isNaN(n)?0:n; }
  function nextEid(entries,floor){
    var max=floor||0;
    for(var i=0;i<entries.length;i++){ var n=eidNum(entries[i].eid); if(n>max) max=n; }
    return 'E-'+pad(max+1,4);
  }
  function nextNid(entries){
    var max=0;
    for(var i=0;i<entries.length;i++) if(entries[i].nid){ var n=nidNum(entries[i].nid); if(n>max) max=n; }
    return 'N-'+pad(max+1,3);
  }
  // Latest first is "greater": ordered by at, then by eid number.
  function cmpEntry(a,b){
    var ta=Date.parse(a.at)||0, tb=Date.parse(b.at)||0;
    if(ta!==tb) return ta-tb;
    return eidNum(a.eid)-eidNum(b.eid);
  }
  function sameTarget(e,kind,key){
    return e&&e.target&&e.target.kind===kind&&(e.target.key==null?null:String(e.target.key))===(key==null?null:String(key));
  }
  // Drops every field whose to equals its from: a change that changes nothing.
  function pruneChanges(ch){
    var out={};
    Object.keys(ch||{}).forEach(function(f){
      var c=ch[f]; if(!isObj(c)) return;
      var from=has(c,'from')?c.from:null, to=has(c,'to')?c.to:null;
      if(!same(from,to)) out[f]={from:clone(from),to:clone(to)};
    });
    return out;
  }
  function isEmptyEntry(e){
    // A clearText entry is never empty: clearing a remark is itself the record.
    return !e||(!e.clearText&&!String(e.text||'').length&&!Object.keys(e.changes||{}).length&&e.target.kind!=='general');
  }
  function findIdx(entries,eid){
    for(var i=0;i<entries.length;i++) if(entries[i].eid===eid) return i;
    return -1;
  }
  function latestOn(entries,kind,key){
    var best=null;
    for(var i=0;i<entries.length;i++){
      var e=entries[i];
      if(sameTarget(e,kind,key)&&(!best||cmpEntry(e,best)>0)) best=e;
    }
    return best;
  }

  // ---- M1: the store core ---------------------------------------------

  // draft: {target:{kind,key}, text?, changes?, origin?, links?, status?,
  //         followsUp?, by?, nid?, sig?}
  // ctx:   {now?, period, windowMs?, seq?}
  // Returns the new entry, the entry it was merged into, or null when the
  // draft carries nothing (no text, no real change, not a note).
  function append(entries,draft,ctx){
    ctx=ctx||{};
    draft=draft||{};
    var t=draft.target||{};
    var kind=KINDS.indexOf(t.kind)>=0?t.kind:'ms';
    var key=(kind==='general')?null:(t.key==null?null:String(t.key));
    var nowMs=toMs(ctx.now);
    var windowMs=(typeof ctx.windowMs==='number')?ctx.windowMs:DEFAULT_WINDOW_MS;
    var period=ctx.period||draft.period||null;
    // clearText: an explicit "this remark is now cleared". Its text is always ''.
    var clearText=draft.clearText===true;
    var text=(clearText||draft.text==null)?'':String(draft.text);
    var changes=pruneChanges(draft.changes);
    var origin=draft.origin||'card';
    if(kind!=='general'&&!clearText&&!text.length&&!Object.keys(changes).length) return null;

    // Coalescing: a card save within the window, in the same report, on the
    // same target, folds into the entry it follows rather than adding one.
    // A clear never coalesces (folding it into an entry with text of its own
    // would lose that text), and nothing coalesces into a clear.
    if(kind!=='general'&&origin==='card'&&!clearText){
      var last=latestOn(entries,kind,key);
      if(last&&!last.clearText&&last.origin==='card'&&last.period===period&&
         nowMs-toMs(last.updatedAt)<=windowMs&&nowMs-toMs(last.updatedAt)>=0){
        var oldText=String(last.text||'');
        // Merge text only when nothing is lost.
        var textOk=!text.length||!oldText.length||text.indexOf(oldText)===0;
        if(textOk){
          var merged=clone(last.changes)||{};
          Object.keys(changes).forEach(function(f){
            if(has(merged,f)) merged[f]={from:merged[f].from,to:clone(changes[f].to)};
            else merged[f]=clone(changes[f]);
          });
          last.changes=pruneChanges(merged);
          if(text.length) last.text=text;
          (draft.links||[]).forEach(function(id){
            if(!last.links) last.links=[];
            if(last.links.indexOf(id)<0) last.links.push(id);
          });
          last.updatedAt=iso(nowMs);
          // A change reverted within the window leaves nothing to record.
          if(isEmptyEntry(last)){ var ix=entries.indexOf(last); if(ix>=0) entries.splice(ix,1); }
          return last;
        }
      }
    }

    var e={
      eid:nextEid(entries,ctx.seq),
      target:{kind:kind,key:key},
      links:(draft.links||[]).slice(),
      period:period,
      at:iso(nowMs), updatedAt:iso(nowMs),
      by:(draft.by==null?null:draft.by),
      status:draft.status?normStatus(draft.status):(kind==='general'?'open':'note'),
      text:text,
      changes:changes,
      origin:origin,
      followsUp:draft.followsUp||null
    };
    if(kind==='general') e.nid=draft.nid?String(draft.nid):nextNid(entries);
    else if(draft.nid) e.nid=String(draft.nid);
    if(clearText) e.clearText=true;
    if(draft.sig) e.sig=draft.sig;
    entries.push(e);
    return e;
  }

  var IMMUTABLE=['eid','target','at','period','origin','nid','sig'];
  // patch: any of {text, changes, links, status, followsUp, by}. changes
  // REPLACES the entry's changes (no-op fields are dropped).
  // Returns {ok:true, entry} or {ok:false, error, message}. Never throws.
  function edit(entries,eid,patch,ctx){
    ctx=ctx||{};
    var i=findIdx(entries||[],eid);
    if(i<0) return {ok:false,error:'not-found',message:'No entry '+eid+'.'};
    var e=entries[i];
    if(!ctx.period||e.period!==ctx.period)
      return {ok:false,error:'period',message:'Entry '+eid+' belongs to the report for '+e.period+
              ' and can only be edited in that report.'};
    patch=patch||{};
    for(var k=0;k<IMMUTABLE.length;k++)
      if(has(patch,IMMUTABLE[k])) return {ok:false,error:'immutable',message:'The '+IMMUTABLE[k]+' of an entry cannot be edited.'};
    if(has(patch,'status')&&STATUSES.indexOf(normStatus(patch.status))<0)
      return {ok:false,error:'status',message:'Unknown status.'};
    if(has(patch,'text')) e.text=(patch.text==null)?'':String(patch.text);
    if(has(patch,'clearText')){ if(patch.clearText===true){ e.clearText=true; e.text=''; } else delete e.clearText; }
    if(has(patch,'changes')) e.changes=pruneChanges(patch.changes);
    if(has(patch,'links')) e.links=(patch.links||[]).slice();
    if(has(patch,'status')) e.status=normStatus(patch.status);
    if(has(patch,'followsUp')) e.followsUp=patch.followsUp||null;
    if(has(patch,'by')) e.by=(patch.by==null?null:patch.by);
    e.updatedAt=iso(toMs(ctx.now));
    return {ok:true,entry:e};
  }

  // Removes one entry. Returns it, or null when there is none.
  function remove(entries,eid){
    var i=findIdx(entries||[],eid);
    return i<0?null:entries.splice(i,1)[0];
  }

  // Sets one status on several entries. Returns how many changed.
  function setStatus(entries,eids,status,ctx){
    var st=normStatus(status);
    if(STATUSES.indexOf(status)<0&&status!=='pending') return 0;
    var at=iso(toMs(ctx&&ctx.now)), n=0;
    (Array.isArray(eids)?eids:[eids]).forEach(function(id){
      var i=findIdx(entries,id);
      if(i>=0&&entries[i].status!==st){ entries[i].status=st; entries[i].updatedAt=at; n++; }
    });
    return n;
  }

  // opts: {kind:'ms' (default), period?}. Latest wins per field, by at then
  // eid. A to:null is "not set": it clears values[field] but is still the
  // latest in byField.
  function rollup(entries,key,opts){
    opts=opts||{};
    var kind=opts.kind||'ms';
    var list=(entries||[]).filter(function(e){
      return sameTarget(e,kind,kind==='general'?null:key)&&(!opts.period||e.period===opts.period);
    }).sort(cmpEntry);
    var values={}, byField={}, lastText='', lastAt=null, openCount=0;
    list.forEach(function(e){
      Object.keys(e.changes||{}).forEach(function(f){
        var c=e.changes[f];
        byField[f]={eid:e.eid,from:c.from,to:c.to,at:e.at};
        if(c.to===null||c.to===undefined) delete values[f];
        else values[f]=c.to;
      });
      // The latest entry with text OR a clear decides; a clear resets to ''.
      if(e.clearText) lastText='';
      else if(String(e.text||'').length) lastText=e.text;
      lastAt=e.at;
      if(OPEN_STATUSES.indexOf(e.status)>=0) openCount++;
    });
    return {values:values,lastText:lastText,lastAt:lastAt,count:list.length,openCount:openCount,byField:byField};
  }

  // The existing stores, in their exact shapes, from the entries.
  // sourceOf(key, field) returns the schedule's own value (undefined when
  // unknown, which stores everything).
  function projectEntries(entries,sourceOf){
    var src=(typeof sourceOf==='function')?sourceOf:function(){ return undefined; };
    var out={comments:{},health:{},progress:{},fields:{},depComments:{},rowOverrides:{},notes:[]};
    var keys={ms:{},dep:{},row:{}};
    (entries||[]).forEach(function(e){
      if(!e||!e.target) return;
      var k=e.target.kind;
      if(k==='general'){
        out.notes.push({nid:e.nid,text:e.text,status:normStatus(e.status),links:(e.links||[]).slice(),
                        period:e.period,at:e.at,updatedAt:e.updatedAt});
      } else if(keys[k]&&e.target.key!=null) keys[k][e.target.key]=1;
    });
    Object.keys(keys.ms).forEach(function(key){
      var r=rollup(entries,key,{kind:'ms'});
      if(r.lastText.length) out.comments[key]=r.lastText;
      // USR- keys are treated like any other key: the app writes and reads
      // their overrides through the same stores (userMsGridEdit, saveMsDialog,
      // umsHealth, umsEffective).
      var v=r.values;
      // Health: every explicit code is kept, 0 included. Absent is automatic.
      if(has(v,'health')) out.health[key]=v.health;
      if(has(v,'progress')){
        var sp=src(key,'progress');
        if(!(sp!=null&&v.progress===sp)) out.progress[key]=v.progress;
      }
      var ov={};
      MS_FIELDS.forEach(function(f){
        if(!has(v,f)) return;
        if(v[f]===src(key,f)) return;          // equal to source is not stored
        ov[f]=v[f];
      });
      if(Object.keys(ov).length) out.fields[key]=ov;
    });
    Object.keys(keys.dep).forEach(function(key){
      var r=rollup(entries,key,{kind:'dep'});
      if(r.lastText.length) out.depComments[key]=r.lastText;
    });
    Object.keys(keys.row).forEach(function(key){
      var r=rollup(entries,key,{kind:'row'});
      var v=r.values;
      if(!has(v,'rowHealth')&&!has(v,'rowRemark')) return;
      out.rowOverrides[key]={health:has(v,'rowHealth')?v.rowHealth:null,
                             remarks:has(v,'rowRemark')?v.rowRemark:''};
    });
    return out;
  }

  // ---- M2: migration from P64-or-older payloads ------------------------

  function sigFor(kind,key,text,changes){
    var to={};
    Object.keys(changes||{}).forEach(function(f){ to[f]=changes[f].to; });
    return 's'+hash(canon({k:kind,key:key,text:text||'',to:to}));
  }
  // The report period a payload was made in: the week ending on or after its
  // reportDate, at the week-ending day it was built with.
  function payloadPeriod(p,opts){
    if(p&&typeof p.reportDate==='string'&&/^\d{4}-\d{2}-\d{2}/.test(p.reportDate)){
      var wd=opts.weekEndingDay;
      if(typeof wd!=='number'){
        var d0=p.timeline&&p.timeline.dates&&p.timeline.dates[0];
        var dd=d0?new Date(d0):null;
        wd=(dd&&!isNaN(dd))?dd.getDay():0;   // the app's own default is Sunday (0)
      }
      var per=weekEndISO(p.reportDate.slice(0,10),wd);
      if(per) return per;
    }
    return opts.period||null;
  }

  // Converts a schemaVersion 1 payload (exportModel or publishStatePayload
  // output) into entries. Pure: returns the NEW entries only, numbered after
  // opts.existing, and skips any whose sig (or, for notes, nid) is already in
  // opts.existing. Short titles and note collections are not entries and are
  // not touched.
  // opts: {origin?, period?, now?, weekEndingDay?, existing?:[entry]}
  function migrateLegacy(payload,opts){
    opts=opts||{};
    var p=payload||{};
    var existing=opts.existing||[];
    var sigs={}, nids={};
    existing.forEach(function(e){ if(e.sig) sigs[e.sig]=1; if(e.nid) nids[e.nid]=1; });
    var period=payloadPeriod(p,opts);
    var stamp=p.exportedAt||p.publishedAt||null;
    var atMs=toMs(stamp||opts.now);
    var origin=opts.origin||'carried';
    var out=[];
    var seq=0;
    existing.forEach(function(e){ var n=eidNum(e.eid); if(n>seq) seq=n; });
    function push(e){
      if(e.sig&&sigs[e.sig]) return;
      if(e.sig) sigs[e.sig]=1;
      e.eid='E-'+pad(++seq,4);
      out.push(e);
    }
    function base(kind,key,text,changes,org){
      var e={eid:null,target:{kind:kind,key:key},links:[],period:period,at:iso(atMs),updatedAt:iso(atMs),
             by:null,status:'note',text:text,changes:changes,origin:org,followsUp:null};
      e.sig=sigFor(kind,key,text,changes);
      return e;
    }

    // Milestones: one carried entry per key, gathering all four stores.
    var mk={}, order=[];
    function touch(k){ if(!has(mk,k)){ mk[k]={text:'',changes:{}}; order.push(k); } return mk[k]; }
    var cm=isObj(p.milestoneComments)?p.milestoneComments:{};
    Object.keys(cm).forEach(function(k){
      var t=(cm[k]==null)?'':String(cm[k]);
      if(t.length) touch(k).text=t;          // an empty comment is no comment
    });
    var hm=isObj(p.milestoneHealthOverrides)?p.milestoneHealthOverrides:{};
    Object.keys(hm).forEach(function(k){
      if(hm[k]===null||hm[k]===undefined) return;
      touch(k).changes.health={from:null,to:hm[k]};
    });
    var pm=isObj(p.milestoneProgressOverrides)?p.milestoneProgressOverrides:{};
    Object.keys(pm).forEach(function(k){
      if(pm[k]===null||pm[k]===undefined) return;
      touch(k).changes.progress={from:null,to:pm[k]};
    });
    var fm=isObj(p.milestoneFieldOverrides)?p.milestoneFieldOverrides:{};
    Object.keys(fm).forEach(function(k){
      var ov=fm[k]; if(!isObj(ov)) return;
      MS_FIELDS.forEach(function(f){
        if(has(ov,f)&&ov[f]!==null&&ov[f]!==undefined) touch(k).changes[f]={from:null,to:clone(ov[f])};
      });
    });
    order.forEach(function(k){
      var m=mk[k];
      if(!m.text.length&&!Object.keys(m.changes).length) return;
      push(base('ms',k,m.text,m.changes,'carried'));
    });

    // Notes: one general entry each, keeping nid, status, period, links, at.
    (Array.isArray(p.notes)?p.notes:[]).forEach(function(n){
      if(!n||!n.nid||typeof n.text!=='string') return;
      var nid=String(n.nid);
      if(nids[nid]) return;
      nids[nid]=1;
      var at=n.at||iso(atMs);
      var e={eid:null,target:{kind:'general',key:null},links:Array.isArray(n.links)?n.links.slice():[],
             period:n.period||period,at:at,updatedAt:n.updatedAt||at,by:null,
             status:normStatus(n.status),text:n.text,changes:{},origin:origin,followsUp:null,nid:nid};
      push(e);
    });

    // Dependency-line comments.
    var dc=isObj(p.dependencyComments)?p.dependencyComments:{};
    Object.keys(dc).forEach(function(k){
      var t=(dc[k]==null)?'':String(dc[k]);
      if(!t.length) return;
      push(base('dep',k,t,{},origin));
    });

    // Row health and remarks.
    var ro=isObj(p.overrides)?p.overrides:{};
    Object.keys(ro).forEach(function(ref){
      var o=ro[ref]; if(!isObj(o)) return;
      var ch={};
      if(o.health!==null&&o.health!==undefined) ch.rowHealth={from:null,to:o.health};
      if(o.remarks!==null&&o.remarks!==undefined) ch.rowRemark={from:null,to:String(o.remarks)};
      if(!Object.keys(ch).length) return;
      push(base('row',ref,'',ch,origin));
    });
    return out;
  }

  // Mutating import: appends migrateLegacy()'s entries to `entries`, and
  // REPLACES a note already present by nid (the app's applyNotes() rule).
  // Returns {added, replaced, skipped, shortTitles, noteCollections}; skipped
  // counts sig/nid duplicates (a replaced note is also skipped); the last
  // two are passed through untouched for the caller's own stores.
  function importLegacy(entries,payload,opts){
    opts=opts||{};
    var p=payload||{};
    var byNid={};
    entries.forEach(function(e){ if(e.nid&&e.target&&e.target.kind==='general') byNid[e.nid]=e; });
    var replaced=0;
    (Array.isArray(p.notes)?p.notes:[]).forEach(function(n){
      if(!n||!n.nid||typeof n.text!=='string') return;
      var e=byNid[String(n.nid)]; if(!e) return;
      var next={text:n.text,status:normStatus(n.status),links:Array.isArray(n.links)?n.links.slice():[],
                period:n.period||e.period,at:n.at||e.at,updatedAt:n.updatedAt||n.at||e.updatedAt};
      var diff=Object.keys(next).some(function(k){ return !same(e[k],next[k]); });
      if(diff){ Object.keys(next).forEach(function(k){ e[k]=next[k]; }); replaced++; }
    });
    var mo={origin:opts.origin,period:opts.period,now:opts.now,weekEndingDay:opts.weekEndingDay};
    var all=migrateLegacy(p,mo).length;
    var add=migrateLegacy(p,Object.assign({existing:entries},mo));
    add.forEach(function(e){ entries.push(e); });
    return {added:add.length,replaced:replaced,skipped:all-add.length,
            shortTitles:clone(p.milestoneShortTitles||{}),
            noteCollections:clone(p.noteCollections||{})};
  }

  // ---- persistence -----------------------------------------------------

  function validEntry(e){
    return isObj(e)&&typeof e.eid==='string'&&/^E-\d+$/.test(e.eid)&&isObj(e.target)&&
      KINDS.indexOf(e.target.kind)>=0&&typeof e.text==='string'&&isObj(e.changes)&&
      STATUSES.indexOf(e.status)>=0&&typeof e.at==='string';
  }
  function serialize(entries){ return JSON.stringify({schemaVersion:SCHEMA_VERSION,entries:entries||[]}); }
  // Accepts the serialize() string, a bare array, or {entries}. Invalid
  // entries are dropped rather than failing the whole load; 'pending' reads
  // as 'review'.
  function deserialize(json){
    var v=json;
    if(typeof v==='string'){ try{ v=JSON.parse(v); }catch(e){ return []; } }
    var arr=Array.isArray(v)?v:(isObj(v)&&Array.isArray(v.entries)?v.entries:[]);
    return arr.map(function(e){
      if(isObj(e)&&e.status) e=Object.assign({},e,{status:normStatus(e.status)});
      return e;
    }).filter(validEntry);
  }

  var LEGACY_FIELDS=['milestoneComments','milestoneHealthOverrides','milestoneProgressOverrides',
    'milestoneFieldOverrides','milestoneShortTitles','notes','noteCollections','dependencyComments','overrides','milestones'];
  // Payload-level check. schemaVersion 1 (or none) is the P64 shape; 2
  // carries `entries`. Returns {ok, errors[], warnings[], schemaVersion}.
  function validatePayload(p){
    var out={ok:false,errors:[],warnings:[],schemaVersion:null};
    if(!isObj(p)){ out.errors.push('The file does not contain a model object.'); return out; }
    var sv=(p.schemaVersion==null)?1:p.schemaVersion;
    out.schemaVersion=sv;
    if(sv!==1&&sv!==2){
      out.errors.push(typeof sv==='number'&&sv>SCHEMA_VERSION
        ?'Written by a newer build (schema v'+sv+'; this build reads v1 and v2).'
        :'Unknown schema version: '+sv+'.');
      return out;
    }
    if(sv===2){
      if(!Array.isArray(p.entries)){ out.errors.push('A schema v2 file must carry an entries list.'); return out; }
      var bad=p.entries.filter(function(e){ return !validEntry(isObj(e)?Object.assign({},e,{status:normStatus(e.status)}):e); }).length;
      if(bad) out.warnings.push(bad+' of '+p.entries.length+' entries are not readable and will be skipped.');
      var seen={}, dup=0;
      p.entries.forEach(function(e){ if(e&&e.eid){ if(seen[e.eid]) dup++; seen[e.eid]=1; } });
      if(dup) out.warnings.push(dup+' entries repeat an entry ID already in the file.');
    } else {
      var looks=LEGACY_FIELDS.some(function(f){ return has(p,f); });
      if(!looks){ out.errors.push('This is not a dashboard model export.'); return out; }
    }
    out.ok=!out.errors.length;
    return out;
  }

  // ---- convenience: one array, one clock --------------------------------
  // opts: {now?: function returning ms | fixed value, seq?: eid floor,
  //        entries?: array to adopt}
  function create(opts){
    opts=opts||{};
    var clock=(typeof opts.now==='function')?opts.now:function(){ return opts.now==null?Date.now():toMs(opts.now); };
    var store={entries:opts.entries||[]};
    function withNow(ctx){ ctx=Object.assign({},ctx||{}); if(ctx.now==null) ctx.now=clock(); if(ctx.seq==null&&opts.seq) ctx.seq=opts.seq; return ctx; }
    store.append=function(d,ctx){ return append(store.entries,d,withNow(ctx)); };
    store.edit=function(eid,patch,ctx){ return edit(store.entries,eid,patch,withNow(ctx)); };
    store.remove=function(eid){ return remove(store.entries,eid); };
    store.setStatus=function(eids,st,ctx){ return setStatus(store.entries,eids,st,withNow(ctx)); };
    store.rollup=function(key,o){ return rollup(store.entries,key,o); };
    store.project=function(sourceOf){ return projectEntries(store.entries,sourceOf); };
    store.importLegacy=function(p,o){ return importLegacy(store.entries,p,Object.assign({now:clock()},o||{})); };
    store.serialize=function(){ return serialize(store.entries); };
    return store;
  }

  var api={
    SCHEMA_VERSION:SCHEMA_VERSION,KINDS:KINDS,STATUSES:STATUSES,OPEN_STATUSES:OPEN_STATUSES,
    MS_FIELDS:MS_FIELDS,CHANGE_FIELDS:CHANGE_FIELDS,DEFAULT_WINDOW_MS:DEFAULT_WINDOW_MS,
    create:create,append:append,edit:edit,remove:remove,setStatus:setStatus,rollup:rollup,
    projectEntries:projectEntries,migrateLegacy:migrateLegacy,importLegacy:importLegacy,
    serialize:serialize,deserialize:deserialize,validatePayload:validatePayload,
    // helpers the integrator may want
    normStatus:normStatus,weekEndISO:weekEndISO,isEmptyEntry:isEmptyEntry,compare:cmpEntry,
    nextEid:nextEid,sigFor:sigFor
  };
  root.SRETEntries=api;
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
})(typeof window!=='undefined'?window:(typeof globalThis!=='undefined'?globalThis:this));
