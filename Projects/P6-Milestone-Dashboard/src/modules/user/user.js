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
       u.onChange(fn)        called after setName or recordSave; returns an unsubscribe
     buildField(container, u) -> {destroy}. Renders the Data settings field: the name,
       Confirm, the comparison with the file's last saver, the save history.
   ===================================================================== */
(function(root){
  'use strict';
  var KEY='sret-user-name', MAX=60;

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
        var msg=st==='unset'?'Set your name so imports, new milestones and saves are recorded against you.'
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
  function buildField(container,u){
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
      el('p',{'class':'su-help',text:'Remembered on this computer only. Imports, new milestones and saves are recorded against this name. A browser cannot read the computer login name, so it is asked here.'}),
      hist]));
    render();
    var off=u.onChange(render);
    return {render:render,input:input,destroy:off};
  }

  root.SRETUser={create:create,buildField:buildField,_memory:memory};
})(window);
