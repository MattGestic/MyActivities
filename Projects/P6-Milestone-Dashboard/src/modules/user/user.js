/* =====================================================================
   SRET user name and save history (Matt, 2026-09-28). No app globals.

   Who is using the file. A page opened from disk cannot read the computer's
   login name (browsers block it), so the name is asked once per computer,
   remembered on that computer (localStorage, like the theme), and the user
   confirms or changes it in Data settings.

   Two names are compared on every open:
     - this computer's user: remembered here, never travels with the file;
     - the file's last saver: saved inside the file with its save history.
   When a shared file is opened on another computer, the file still says who
   saved it last, but everything done now (imports, new milestones, saves)
   is recorded against this computer's user. The save history keeps every
   save: time, user, version.

   API (window.SRETUser):
     create({storage, key, file:{savedBy, history}}) -> u
       u.name()              this computer's user ('' until set)
       u.status()            {name, savedBy, state:'unset'|'same'|'other', message}
       u.setName(name)       -> {ok, name} | {ok:false, error}
       u.recordSave(meta)    -> entry {at, by, version}; appended to the history
       u.history()           -> copy, oldest first
       u.fileState()         -> {savedBy, history} to write into the saved file
       u.onChange(fn)        called after setName, setIdPrefix or recordSave; returns an unsubscribe
       u.idPrefix()          the prefix for new task IDs: the one the user set, else U + initials
       u.setIdPrefix(p, scheduleIds) -> {ok, value, warning} | {ok:false, error}; '' goes back to the initials
       u.prefixIsDefault()   true while no prefix of the user's own is set
     buildPrefixField(container, u, {nextId(prefix), scheduleIds(), heading}) -> {destroy}. The task ID
       prefix field (Data settings, and the User tasks grid's Tools menu).
     buildField(container, u, opts) -> {destroy}. Renders the Data settings field: the name,
       Confirm, the comparison with the file's last saver, the save history.
   ===================================================================== */
(function(root){
  'use strict';
  var KEY='sret-user-name', PKEY='sret-task-prefix', MAX=60;

  function memory(){ var m={}; return {getItem:function(k){ return k in m?m[k]:null; },setItem:function(k,v){ m[k]=String(v); },removeItem:function(k){ delete m[k]; }}; }
  function clean(v){ return String(v==null?'':v).replace(/[\u0000-\u001f\u007f]/g,'').replace(/\s+/g,' ').trim(); }
  function same(a,b){ return clean(a).toLowerCase()===clean(b).toLowerCase(); }

  function create(opts){
    opts=opts||{};
    var store=opts.storage||null, key=opts.key||KEY;
    if(!store){ try{ store=root.localStorage; store.getItem(key); }catch(e){ store=memory(); } }
    var file=opts.file||{};
    var hist=Array.isArray(file.history)?file.history.map(function(e){ return Object.assign({},e); }):[];
    var savedBy=clean(file.savedBy||(hist.length?hist[hist.length-1].by:''));
    var subs=[];
    function read(){ try{ return clean(store.getItem(key)); }catch(e){ return ''; } }
    function fire(){ subs.forEach(function(f){ try{ f(); }catch(e){} }); }
    var u={
      name:read,
      status:function(){
        var n=read(), st=!n?'unset':(!savedBy||same(n,savedBy)?'same':'other');
        var msg=st==='unset'?'Set your name so imports, new tasks and saves are recorded against you.'
               :st==='other'?'You are working as '+n+'. This file was last saved by '+savedBy+'.'
               :'You are working as '+n+'.';
        return {name:n,savedBy:savedBy,state:st,message:msg};
      },
      setName:function(v){
        var n=clean(v);
        if(!n) return {ok:false,error:'Enter a name.'};
        if(n.length>MAX) return {ok:false,error:'Use '+MAX+' characters or fewer.'};
        try{ store.setItem(key,n); }catch(e){ return {ok:false,error:'This browser would not store the name.'}; }
        fire();
        return {ok:true,name:n};
      },
      recordSave:function(meta){
        meta=meta||{};
        var e={at:meta.at||new Date().toISOString(),by:read(),version:meta.version||''};
        hist.push(e); savedBy=e.by;
        fire();
        return Object.assign({},e);
      },
      // Task ID prefix (Matt, 2026-09-29): the user's own, e.g. A100 for area 100, else U + initials.
      idPrefix:function(){
        var own=''; try{ own=clean(store.getItem(PKEY)); }catch(e){}
        return own||(root.SRETIds?root.SRETIds.prefix(read()):'UXX');
      },
      prefixIsDefault:function(){ try{ return !clean(store.getItem(PKEY)); }catch(e){ return true; } },
      setIdPrefix:function(v,scheduleIds){
        if(clean(v)===''){ try{ store.removeItem(PKEY); }catch(e){} fire(); return {ok:true,value:u.idPrefix(),warning:''}; }
        var r=root.SRETIds?root.SRETIds.checkPrefix(v,scheduleIds):{ok:true,value:clean(v).toUpperCase(),warning:''};
        if(!r.ok) return r;
        try{ store.setItem(PKEY,r.value); }catch(e){ return {ok:false,error:'This browser would not store the prefix.'}; }
        fire();
        return r;
      },
      history:function(){ return hist.map(function(e){ return Object.assign({},e); }); },
      fileState:function(){ return {savedBy:savedBy,history:u.history()}; },
      onChange:function(fn){ subs.push(fn); return function(){ subs=subs.filter(function(f){ return f!==fn; }); }; }
    };
    return u;
  }

  // ---------- Data settings field ----------
  function el(tag,attrs,kids){
    var n=document.createElement(tag);
    Object.keys(attrs||{}).forEach(function(k){
      if(k==='text') n.textContent=attrs[k];
      else if(k==='on') Object.keys(attrs.on).forEach(function(ev){ n.addEventListener(ev,attrs.on[ev]); });
      else if(attrs[k]!=null&&attrs[k]!==false) n.setAttribute(k,attrs[k]===true?'':attrs[k]);
    });
    (kids||[]).forEach(function(c){ if(c) n.appendChild(c); });
    return n;
  }
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function stamp(iso){
    var d=new Date(iso); if(isNaN(d)) return String(iso||'');
    return d.getDate()+'-'+MON[d.getMonth()]+'-'+String(d.getFullYear()).slice(2)+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
  }
  function buildField(container,u,opts){
    var input=el('input',{type:'text','class':'sg-search su-name',maxlength:String(MAX),autocomplete:'name','aria-label':'Your name','data-sg':'user-name'});
    var ok=el('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'user-confirm',text:'Confirm'});
    var note=el('p',{'class':'su-note','data-sg':'user-status',role:'status'});
    var err=el('p',{'class':'su-error','data-sg':'user-error',role:'alert',hidden:true});
    var hist=el('div',{'class':'su-hist'});
    function render(){
      var st=u.status();
      if(document.activeElement!==input) input.value=st.name;
      note.textContent=st.message; note.setAttribute('data-state',st.state);
      hist.innerHTML='';
      var rows=u.history();
      hist.appendChild(el('h4',{'class':'su-h',text:'Save history'}));
      if(!rows.length){ hist.appendChild(el('p',{'class':'su-note','data-sg':'user-history-empty',text:'Not saved yet.'})); return; }
      var t=el('table',{'class':'sg-itable','data-sg':'user-history'},[
        el('thead',{},[el('tr',{},['Saved','By','Version'].map(function(x){ return el('th',{text:x}); }))])]);
      var b=el('tbody');
      rows.slice().reverse().forEach(function(e){ b.appendChild(el('tr',{},[stamp(e.at),e.by||'(not set)',e.version||''].map(function(x){ return el('td',{text:x}); }))); });
      t.appendChild(b); hist.appendChild(t);
    }
    function confirm(){
      var r=u.setName(input.value);
      err.hidden=r.ok; err.textContent=r.ok?'':r.error;
      if(r.ok) render(); else input.focus();
    }
    ok.addEventListener('click',confirm);
    input.addEventListener('keydown',function(e){ if(e.key==='Enter'){ e.preventDefault(); confirm(); } });
    // Host pages style bare p; .su-box scopes these rules above them.
    container.appendChild(el('div',{'class':'su-box','data-sg':'user-box'},[
      el('div',{'class':'su-field','data-sg':'user-field'},[el('label',{'class':'su-label'},[el('span',{text:'Your name'}),input]),ok]),
      err,note,
      el('p',{'class':'su-help',text:'Remembered on this computer only. Imports, new tasks and saves are recorded against this name. A browser cannot read the computer login name, so it is asked here.'}),
      hist]));
    var pf=opts&&opts.prefix?buildPrefixField(container,u,opts.prefix):null;
    render();
    var off=u.onChange(render);
    return {render:render,input:input,destroy:function(){ off(); if(pf) pf.destroy(); }};
  }
  // Task ID prefix: type A100 before adding the tasks for area 100, A200 for
  // the next set. Blank goes back to the initials.
  function buildPrefixField(container,u,o){
    o=o||{};
    var input=el('input',{type:'text','class':'sg-search su-prefix',maxlength:'8',autocomplete:'off','aria-label':'Task ID prefix','data-sg':'prefix-input',
                          placeholder:'e.g. A100'});
    var set=el('button',{type:'button','class':'sg-btn','data-sg':'prefix-set',text:'Set prefix'});
    var reset=el('button',{type:'button','class':'sg-link','data-sg':'prefix-reset'});
    var note=el('p',{'class':'su-note','data-sg':'prefix-status',role:'status'});
    var err=el('p',{'class':'su-error','data-sg':'prefix-error',role:'alert',hidden:true});
    function render(){
      var p=u.idPrefix();
      if(document.activeElement!==input) input.value=u.prefixIsDefault()?'':p;
      input.placeholder=p+' (default: your initials)';
      var nxt=typeof o.nextId==='function'?o.nextId(p):p+'-001';
      note.textContent='New tasks are numbered '+p+'-001, '+p+'-002 and so on. Next task: '+nxt+'.';
      reset.textContent='Use my initials ('+(root.SRETIds?root.SRETIds.prefix(u.name()):'UXX')+')';
      reset.hidden=u.prefixIsDefault();
    }
    function apply(v){
      var r=u.setIdPrefix(v,typeof o.scheduleIds==='function'?o.scheduleIds():[]);
      err.hidden=r.ok&&!r.warning; err.textContent=r.ok?(r.warning||''):r.error;
      err.setAttribute('data-kind',r.ok?'warning':'error');
      render(); if(!r.ok) input.focus();
    }
    set.addEventListener('click',function(){ apply(input.value); });
    input.addEventListener('keydown',function(e){ if(e.key==='Enter'){ e.preventDefault(); apply(input.value); } });
    reset.addEventListener('click',function(){ input.value=''; apply(''); });
    container.appendChild(el('div',{'class':'su-box','data-sg':'prefix-box'},[
      o.heading===false?null:el('h4',{'class':'su-h',text:'Task ID prefix'}),
      el('div',{'class':'su-field'},[el('label',{'class':'su-label'},[el('span',{text:'Prefix for new task IDs'}),input]),set,reset]),
      err,note,
      el('p',{'class':'su-help',text:'Use a prefix to group tasks, e.g. A100 while adding the tasks for area 100, then A200 for the next set. Each prefix has its own numbering. Leave it blank to use your initials. Remembered on this computer only.'})]));
    render();
    var off=u.onChange(render);
    return {render:render,input:input,destroy:off};
  }

  root.SRETUser={create:create,buildField:buildField,buildPrefixField:buildPrefixField,_memory:memory};
})(window);
