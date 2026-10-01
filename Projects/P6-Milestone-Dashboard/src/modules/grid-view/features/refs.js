/* =====================================================================
   SRET grid feature: refs (Matt, 2026-09-30). Load after grid-view.js.

   Adds the column type 'refs': a list of row IDs kept as text
   ('SNIP-101, UMG-003'), e.g. predecessors and successors. Each item may
   carry a relationship after the ID ('SNIP-101: FS'); it is kept as
   written. The editor shows the items as tokens with a cross, and an input
   that filters the IDs the caller offers (opts.refOptions(key, rowKey) ->
   [{id, name}]) as the user types:
     starts with a letter -> IDs that start with it   (S -> SNIP-...), then,
                             from two letters, names with a word starting
                             with it (pump -> 'Feed pump install')
     digits only          -> IDs whose number starts with them (117 -> SNIP-117)
   Enter adds the highlighted ID. Delete clears what has been typed;
   Backspace deletes characters. The cross removes one token.

   Provides 'refs' to other features: {tokenField, refOptions, combine}.
   Text: refsPlaceholder, refsUnknown (set per deployment in setup()).
   ===================================================================== */
(function(root){
  'use strict';
  root.SRETGrid.feature('refs',function(K){
    var h=K.h, REF_LIMIT=50;
    function refSplit(v){ return String(v==null?'':v).split(/[,;]+/).map(function(x){ return x.trim(); }).filter(Boolean); }
    function refId(tok){ return String(tok).split(/[:\s]/)[0].toUpperCase(); }
    function refNum(id){ var m=/(\d+)\D*$/.exec(id); return m?m[1]:''; }
    // Words, lower case, joined by single spaces: 'Feed-pump install' -> ' feed pump install'.
    function words(s){ return ' '+String(s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim(); }
    function refMatch(q,opts,taken){
      q=String(q||'').trim().toUpperCase();
      var digits=/^\d+$/.test(q), qw=q.length>=2&&!digits?words(q):'', out=[];
      for(var i=0;i<opts.length;i++){
        var o=opts[i], id=String(o.id).toUpperCase(), tier=1;
        if(taken[id]) continue;
        if(q){
          if(digits){ var n=refNum(id); if(!(n.indexOf(q)===0||n.replace(/^0+/,'').indexOf(q)===0)) continue; }
          else if(id.indexOf(q)!==0){
            // Names too (Matt, 2026-09-30), from two letters, on word starts: 'pump' finds 'Feed pump install'.
            if(!qw||(o._w||(o._w=words(o.name))).indexOf(qw)<0) continue;
            tier=2;
          }
          if(id===q||(digits&&refNum(id).replace(/^0+/,'')===q.replace(/^0+/,''))) tier=0;
        }
        out.push({o:o,t:tier});
      }
      // An exact ID or number first, then IDs that match, then names that match; each in ID order.
      return out.sort(function(a,b){ return a.t-b.t||String(a.o.id).localeCompare(String(b.o.id),undefined,{numeric:true,sensitivity:'base'}); })
                .map(function(x){ return x.o; });
    }
    function refOptions(key,rowKey){
      var s=K.s(), f=s&&s.opts.refOptions;
      var list=typeof f==='function'?(f(key,rowKey)||[]):[];
      return list.filter(function(o){ return o&&o.id!=null&&String(o.id)!==String(rowKey); })
        .map(function(o){ return {id:String(o.id),name:o.name||''}; });
    }
    // Add, replace or remove IDs in a refs value (bulk edit).
    function combine(cur,mode,ids){
      var toks=refSplit(cur);
      if(mode==='replace') return ids.join(', ');
      if(mode==='remove'){ var rm={}; ids.forEach(function(x){ rm[refId(x)]=1; }); return toks.filter(function(x){ return !rm[refId(x)]; }).join(', '); }
      var have={}; toks.forEach(function(x){ have[refId(x)]=1; });
      ids.forEach(function(x){ if(!have[refId(x)]){ toks.push(x); have[refId(x)]=1; } });
      return toks.join(', ');
    }

    // The token field itself; used by the cell editor and by bulk edit.
    // o: {label, value, options:[{id,name}], onEnterEmpty(), onEscape(), onTab(back), onChange()}
    var uidN=0;
    function tokenField(o){
      var toks=refSplit(o.value), known={}, hi=0, shown=[];
      o.options.forEach(function(x){ known[x.id.toUpperCase()]=x; });
      var uid='sg-refs-'+(++uidN);
      var list=h('div',{'class':'sg-refs-toks',role:'list'});
      var input=h('input',{type:'text','class':'sg-refs-input',role:'combobox','aria-autocomplete':'list','aria-expanded':'false',
                           'aria-controls':uid,'aria-label':o.label+': type an ID to add','data-sg':'refs-input',autocomplete:'off',spellcheck:'false',
                           placeholder:K.t('refsPlaceholder')});
      var lb=h('div',{'class':'sg-refs-list',id:uid,role:'listbox','aria-label':o.label+' matches','data-sg':'refs-list',hidden:true});
      var more=h('div',{'class':'sg-refs-more','data-sg':'refs-more',hidden:true});
      var box=h('div',{'class':'sg-refs','data-sg':'refs'},[list,input,lb,more]);
      function taken(){ var m={}; toks.forEach(function(x){ m[refId(x)]=1; }); return m; }
      function drawToks(){
        list.innerHTML='';
        toks.forEach(function(tok,i){
          var id=refId(tok), k=known[id];
          var x=h('button',{type:'button','class':'sg-tok-x','aria-label':'Remove '+tok,title:'Remove','data-sg':'tok-x',tabindex:'-1',text:'×'});
          x.addEventListener('mousedown',function(e){ e.preventDefault(); });
          x.addEventListener('click',function(e){ e.stopPropagation(); toks.splice(i,1); drawToks(); filter(); input.focus(); if(o.onChange) o.onChange(); });
          list.appendChild(h('span',{'class':'sg-tok'+(k?'':' sg-tok--unknown'),role:'listitem','data-sg-tok':id,
                                     title:k?(k.id+'  '+k.name):id+': '+K.t('refsUnknown')},[h('span',{text:tok}),x]));
        });
      }
      function filter(){
        var q=input.value.trim();
        shown=refMatch(q,o.options,taken());
        lb.innerHTML='';
        var vis=shown.slice(0,REF_LIMIT);
        hi=Math.min(hi,Math.max(0,vis.length-1));
        vis.forEach(function(x,i){
          var op=h('div',{'class':'sg-refs-opt'+(i===hi?' is-hi':''),role:'option','aria-selected':String(i===hi),id:uid+'-'+i,'data-sg-ref':x.id},
                   [h('b',{text:x.id}),h('span',{text:x.name})]);
          op.addEventListener('mousedown',function(e){ e.preventDefault(); });
          op.addEventListener('click',function(e){ e.stopPropagation(); add(x.id); });
          lb.appendChild(op);
        });
        var open=vis.length>0&&(q!==''||document.activeElement===input);
        lb.hidden=!open; input.setAttribute('aria-expanded',String(open));
        if(open) input.setAttribute('aria-activedescendant',uid+'-'+hi); else input.removeAttribute('aria-activedescendant');
        more.hidden=shown.length<=REF_LIMIT; more.textContent=(shown.length-REF_LIMIT)+' more. Keep typing to narrow the list.';
        if(q&&!vis.length){ more.hidden=false; more.textContent='No ID matches "'+q+'".'; }
      }
      function add(id){ toks.push(id); input.value=''; hi=0; drawToks(); filter(); input.focus(); if(o.onChange) o.onChange(); }
      function move(d){ var n=Math.min(shown.length,REF_LIMIT); if(!n) return; hi=(hi+d+n)%n; filter(); var el=lb.children[hi]; if(el&&el.scrollIntoView) el.scrollIntoView({block:'nearest'}); }
      input.addEventListener('input',function(){ hi=0; filter(); });
      input.addEventListener('focus',filter);
      input.addEventListener('keydown',function(e){
        var k=e.key;
        if(k==='ArrowDown'||k==='ArrowUp'){ e.preventDefault(); e.stopImmediatePropagation(); move(k==='ArrowDown'?1:-1); return; }
        if(k==='Enter'){
          e.preventDefault(); e.stopImmediatePropagation();
          if(input.value.trim()!==''){ var x=shown[hi]; if(x) add(x.id); return; }
          if(o.onEnterEmpty) o.onEnterEmpty();
          return;
        }
        if(k==='Escape'&&o.onEscape){ e.preventDefault(); e.stopImmediatePropagation(); o.onEscape(); return; }
        if(k==='Tab'&&o.onTab){ e.preventDefault(); e.stopImmediatePropagation(); o.onTab(e.shiftKey); return; }
        if(k==='Delete'){ e.preventDefault(); e.stopImmediatePropagation(); input.value=''; hi=0; filter(); return; }
        if(k==='Backspace'||k==='ArrowLeft'||k==='ArrowRight'||k==='Home'||k==='End'||k===' '){ e.stopImmediatePropagation(); return; }
      });
      drawToks();
      return {el:box,input:input,value:function(){ return toks.join(', '); },tokens:function(){ return toks.slice(); },
              set:function(v){ toks=refSplit(v); drawToks(); filter(); }};
    }

    // Cell editor: the token field in a popup over the cell, since tokens
    // and the match list do not fit in a 24px row.
    function RefsEditor(args){
      var s=K.s();
      this.args=args; this.col=args.column.sg;
      this.rowKey=args.item?args.item[s.rowKey]:null;
      this.def=args.item?args.item[this.col.key]:'';
      // The popup lives outside the grid, so it saves, cancels and moves on itself.
      var lock=s.grid.getEditorLock(), grid=s.grid;
      this.field=tokenField({label:this.col.label,value:this.def,options:refOptions(this.col.key,this.rowKey),
        onEnterEmpty:function(){ if(lock.commitCurrentEdit()) grid.focus(); },
        onEscape:function(){ lock.cancelCurrentEdit(); grid.focus(); },
        onTab:function(back){ if(lock.commitCurrentEdit()){ grid.focus(); if(back) grid.navigatePrev(); else grid.navigateNext(); } }});
      var pop=h('div',{'class':'sg-refs-pop','data-sg':'refs-pop'},[this.field.el]);
      this.pop=pop;
      args.container.appendChild(h('span',{'class':'sg-refs-cell',text:String(this.def||'')}));
      s.screen.appendChild(pop);
      this.position();
      var self=this;
      this.onScroll=function(){ self.position(); };
      s.grid.onScroll.subscribe(this.onScroll);
      // A press outside the popup saves, as moving to another cell does.
      this.onOut=function(e){ if(!pop.contains(e.target)&&!self.args.container.contains(e.target)&&lock.isActive()) lock.commitCurrentEdit(); };
      document.addEventListener('mousedown',this.onOut,true);
      this.field.input.focus();
    }
    RefsEditor.prototype.position=function(){
      var s=K.s(), cell=this.args.container.getBoundingClientRect(), sr=s.screen.getBoundingClientRect(), pop=this.pop;
      pop.style.minWidth=Math.max(cell.width,280)+'px';
      var left=cell.left-sr.left, top=cell.top-sr.top;
      if(left+pop.offsetWidth>sr.width-4) left=Math.max(4,sr.width-4-pop.offsetWidth);
      if(top+pop.offsetHeight>sr.height-4) top=Math.max(4,sr.height-4-pop.offsetHeight);
      pop.style.left=left+'px'; pop.style.top=top+'px';
    };
    RefsEditor.prototype.destroy=function(){ var s=K.s(); if(s) s.grid.onScroll.unsubscribe(this.onScroll); document.removeEventListener('mousedown',this.onOut,true); this.pop.remove(); };
    RefsEditor.prototype.focus=function(){ this.field.input.focus(); };
    RefsEditor.prototype.loadValue=function(){};
    RefsEditor.prototype.serializeValue=function(){ return this.field.value(); };
    RefsEditor.prototype.applyValue=function(item,state){ item[this.col.key]=state; };
    RefsEditor.prototype.isValueChanged=function(){ return this.field.value()!==refSplit(this.def).join(', '); };
    RefsEditor.prototype.validate=function(){ return {valid:true,msg:null}; };

    K.provide('refs',{tokenField:tokenField,refOptions:refOptions,combine:combine});
    return {
      types:{refs:{width:160,editor:RefsEditor}},
      text:{refsPlaceholder:'Type an ID',refsUnknown:'not found'}
    };
  });
})(window);
