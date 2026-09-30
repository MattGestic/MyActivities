/* =====================================================================
   SRET grid feature: bulk edit (Matt, 2026-09-30). Load after grid-view.js
   (and after refs.js for refs columns).

   Edit, shown while rows are selected on an editable screen: tick the
   fields to change, set a value, and it is set on every selected row
   through onEdit (so the caller's rules still apply). Refs columns can be
   replaced, added to, or have IDs removed. Refused changes are listed, not
   dropped silently.
   ===================================================================== */
(function(root){
  'use strict';
  root.SRETGrid.feature('bulk-edit',function(K){
    var h=K.h;
    function bulkCols(){
      var s=K.s();
      return s.cols.filter(function(c){ return c.editable&&c.key.charAt(0)!=='_'&&c.key!==s.rowKey; })
        .concat(s.cols.filter(function(c){ return c.icon; }).map(function(c){ return s.colByKey[c.icon.key]; }).filter(function(c){ return c&&!c.editable; }));
    }
    function control(c){
      var el, R=K.get('refs');
      if(c.type==='refs'&&R){
        var f=R.tokenField({label:c.label,value:'',options:R.refOptions(c.key,null)});
        var mode=h('select',{'class':'sg-select','data-sg':'bulk-mode-'+c.key,'aria-label':c.label+': how'},
          [['add','Add these IDs'],['replace','Replace with these IDs'],['remove','Remove these IDs']].map(function(o){ return h('option',{value:o[0],text:o[1]}); }));
        el=h('div',{'class':'sg-bulk-refs'},[mode,f.el]);
        return {el:el,focusEl:f.input,value:function(){ return {mode:mode.value,ids:f.tokens()}; },watch:[f.input,mode]};
      }
      if(c.type==='select'){
        el=h('select',{'class':'sg-select','aria-label':c.label},[h('option',{value:'',text:'(blank)'})].concat(c.opts.map(function(o){ return h('option',{value:String(o.value),text:o.label}); })));
        return {el:el,focusEl:el,value:function(){ var v=el.value; for(var i=0;i<c.opts.length;i++) if(String(c.opts[i].value)===v) return c.opts[i].value; return v===''?null:v; },watch:[el]};
      }
      el=h('input',{type:c.type==='date'?'date':'text','class':'sg-search sg-bulk-input','aria-label':c.label,inputmode:c.type==='number'?'decimal':null});
      return {el:el,focusEl:el,value:function(){ var v=el.value.trim(); if(c.type==='number') return v===''?null:Number(v); if(c.type==='date') return v||null; return el.value; },watch:[el]};
    }
    function open(){
      var keys=K.selectedKeys(); if(!keys.length) return;
      var n=keys.length, cols=bulkCols();
      K.openDialog(n>1?'Edit '+n+' rows':'Edit row',function(body,close){
        var rows=[], err=h('p',{'class':'sg-bulk-err','data-sg':'bulk-error',role:'alert',hidden:true});
        body.appendChild(h('p',{'class':'sg-muted',text:'Tick the fields to change. Each ticked field is set on all '+n+(n===1?' row':' rows')+'; the others are left as they are.'}));
        var grid=h('div',{'class':'sg-bulk','data-sg':'bulk-fields'});
        cols.forEach(function(c){
          var ctl=control(c), tick=h('input',{type:'checkbox','data-sg':'bulk-tick-'+c.key,'aria-label':'Change '+c.label});
          ctl.watch.forEach(function(w){ w.addEventListener('input',function(){ tick.checked=true; }); w.addEventListener('change',function(){ tick.checked=true; }); });
          grid.appendChild(h('label',{'class':'sg-bulk-lbl'},[tick,h('span',{text:c.label})]));
          grid.appendChild(h('div',{'class':'sg-bulk-ctl','data-sg':'bulk-ctl-'+c.key},[ctl.el]));
          rows.push({c:c,tick:tick,ctl:ctl});
        });
        body.appendChild(grid); body.appendChild(err);
        var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ close(); }}});
        var apply=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'bulk-apply',text:'Apply to '+n+(n===1?' row':' rows')});
        body.appendChild(h('div',{'class':'sg-confirm-btns'},[cancel,apply]));
        apply.addEventListener('click',function(){
          var todo=rows.filter(function(r){ return r.tick.checked; });
          if(!todo.length){ err.hidden=false; err.textContent='Tick at least one field to change.'; return; }
          for(var i=0;i<todo.length;i++){
            var c=todo[i].c, v=todo[i].ctl.value();
            if(c.type==='number'&&v!=null&&!isFinite(v)){ err.hidden=false; err.textContent=c.label+': enter a number.'; todo[i].ctl.focusEl.focus(); return; }
            if(c.type==='number'&&v!=null&&(c.min!=null&&v<c.min||c.max!=null&&v>c.max)){ err.hidden=false; err.textContent=c.label+': use '+c.min+' to '+c.max+'.'; todo[i].ctl.focusEl.focus(); return; }
          }
          var res=apply1(keys,todo.map(function(r){ return {c:r.c,v:r.ctl.value()}; }));
          body.innerHTML='';
          var ul=h('ul',{'class':'sg-import-summary','data-sg':'bulk-summary'});
          res.lines.forEach(function(l){ ul.appendChild(h('li',{text:l})); });
          var done=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'bulk-done',text:'Done',on:{click:function(){ close(); }}});
          body.appendChild(h('div',{'class':'sg-import-status'},[h('p',{'class':'sg-import-head',text:'Changes applied'}),ul,h('div',{'class':'sg-confirm-btns'},[h('span'),done])]));
          K.say(res.lines[0]); done.focus();
        });
        (rows[0]&&rows[0].ctl.focusEl||apply).focus();
      });
    }
    function apply1(keys,sets){
      var s=K.s(), changed=0, rowsChanged={}, refused=[], can=s.opts.canEdit, R=K.get('refs');
      s.dv.beginUpdate();
      keys.forEach(function(k){
        var it=s.dv.getItemById(k); if(!it) return;
        var c2=Object.assign({},it), any=false;
        sets.forEach(function(st){
          var key=st.c.key, v=st.c.type==='refs'&&R?R.combine(it[key],st.v.mode,st.v.ids):st.v;
          if(String(v==null?'':v)===String(it[key]==null?'':it[key])) return;
          if(typeof can==='function'&&can(k,key)===false){ refused.push(k+' '+st.c.label); return; }
          var ret=typeof s.opts.onEdit==='function'?s.opts.onEdit(k,key,v):undefined;
          if(ret===false){ refused.push(k+' '+st.c.label); return; }
          c2[key]=v; any=true; changed++;
        });
        if(any){ K.prepare(c2); s.dv.updateItem(k,c2); rowsChanged[k]=1; }
      });
      s.dv.endUpdate();
      s.grid.invalidate(); K.updateStatus();
      var nr=Object.keys(rowsChanged).length;
      var lines=[changed?'Updated '+nr+(nr===1?' row':' rows')+' ('+changed+(changed===1?' change':' changes')+').':'Nothing to change: the rows already had those values.'];
      lines.push('Fields: '+sets.map(function(st){ return st.c.label; }).join(', ')+'.');
      if(refused.length) lines.push((refused.length===1?'1 change was':refused.length+' changes were')+' not accepted: '+refused.slice(0,10).join('; ')+(refused.length>10?'; and '+(refused.length-10)+' more':'')+'.');
      return {lines:lines,changed:changed,refused:refused};
    }

    return {
      use:function(o){ return !!o.editable&&(o.columns||[]).some(function(c){ return c.editable&&c.key!==o.rowKey; }); },
      bar2:function(s){
        s.editBtn=h('button',{type:'button','class':'sg-btn','data-sg':'bulk-edit',hidden:true,text:'Edit row',
          title:'Change fields on all the selected rows'});
        s.editBtn.addEventListener('click',open);
        return [{order:40,el:s.editBtn}];
      },
      status:function(s,sel){ s.editBtn.hidden=!sel; s.editBtn.textContent=sel>1?'Edit '+sel+' rows':'Edit row'; }
    };
  });
})(window);
