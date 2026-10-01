/* =====================================================================
   SRET grid feature: marks. Load after grid-view.js.

   Two tap-to-pick marks drawn inside a cell:
     column.icon {key, label, options}  a health dot before the value; the
       dot shows row[icon.key] (0 to 4, the dashboard's health states).
     column.symbols {prefix, stateKey}  the Icon column (Matt, 2026-09-30):
       an SVG symbol per value (<use href="#prefix+value">), coloured by
       row[stateKey] through the class s-<state>. In setup() defaults a
       deployment adds its own classes to each symbol with symbolClass
       (SRET: 'ms-icon filled', the board's marker colours), or draws the
       symbol itself with renderSymbol(value, item, column) -> html.
   Picking a value goes through onEdit, as a cell edit does.
   ===================================================================== */
(function(root){
  'use strict';
  root.SRETGrid.feature('marks',function(K){
    var h=K.h, esc=K.esc;
    function hdot(icon,v){
      var o=(icon.options||[]).filter(function(x){ return String(x.value)===String(v==null?0:v); })[0]||{label:'N/A'};
      return '<button type="button" class="sg-hdot sg-h-'+esc(v==null?0:v)+'" tabindex="-1" data-sg-hdot="1" aria-label="'+
        esc(icon.label+': '+o.label+'. Change')+'" title="'+esc(icon.label+': '+o.label)+'"></button>';
    }
    function symGlyph(c,v,item){
      var s=K.s(), sy=c.symbols;
      if(s&&typeof s.opts.renderSymbol==='function') return s.opts.renderSymbol(v,item,c);
      var st=item&&sy.stateKey?String(item[sy.stateKey]||'future').toLowerCase():'future';
      var cls=s&&s.opts.symbolClass?esc(s.opts.symbolClass)+' ':'';
      return '<svg class="'+cls+'sg-sym-svg s-'+esc(st)+'" aria-hidden="true" focusable="false"><use href="#'+esc((sy.prefix||'')+(v||'diamond'))+'"/></svg>';
    }
    function symBtn(c,v,item){
      var lab=K.display(c,v)||'None';
      return '<button type="button" class="sg-sym" tabindex="-1" data-sg-sym="1" aria-label="'+esc(c.label+': '+lab+'. Change')+'" title="'+esc(c.label+': '+lab)+'">'+
        symGlyph(c,v,item)+'</button>';
    }
    // Cell decorations, set once per column when the screen opens.
    function iconDecor(c,v,item,txt){ return hdot(c.icon,item?item[c.icon.key]:null)+'<span class="sg-cell-txt">'+txt+'</span>'; }
    function symDecor(c,v,item){ return symBtn(c,v,item)+'<span class="sg-cell-txt">'+esc(String(K.display(c,v)).split(',')[0])+'</span>'; }

    function closePicker(){ var s=K.s(); if(s&&s.hpick){ s.hpick.remove(); s.hpick=null; document.removeEventListener('mousedown',s.hpickOff,true); } }
    function openSymPicker(btn,rowKey,col){
      var s=K.s(), it=s.dv.getItemById(rowKey);
      openPicker(btn,rowKey,{key:col.key,label:col.label,options:col.opts,sg:'icon-picker',attr:'data-sg-icon',cur:it?it[col.key]:null,
        glyph:function(o){ var sp=h('span',{'class':'sg-sym sg-sym--menu','aria-hidden':'true'}); sp.innerHTML=symGlyph(col,o.value,it); return sp; }});
    }
    function openHealthPicker(btn,rowKey,col){
      var s=K.s(), icon=col.icon, it=s.dv.getItemById(rowKey), cur=it?it[icon.key]:null;
      openPicker(btn,rowKey,{key:icon.key,label:icon.label,options:icon.options,sg:'health-picker',attr:'data-sg-health',cur:cur==null?0:cur,
        glyph:function(o){ return h('span',{'class':'sg-hdot sg-h-'+o.value,'aria-hidden':'true'}); }});
    }
    // One tap-to-pick popup for a row value (health dot, icon).
    function openPicker(btn,rowKey,p){
      var s=K.s(); closePicker();
      var pop=h('div',{'class':'sg-menu-pop sg-hpick',role:'menu','aria-label':p.label,'data-sg':p.sg});
      (p.options||[]).forEach(function(o){
        var at={type:'button','class':'sg-menu-item',role:'menuitemradio','aria-checked':String(String(o.value)===String(p.cur)),tabindex:'-1'};
        at[p.attr]=String(o.value);
        var b=h('button',at,[p.glyph(o),h('span',{text:o.label})]);
        b.addEventListener('click',function(e){ e.stopPropagation(); closePicker(); setValue(rowKey,p.key,o.value); });
        pop.appendChild(b);
      });
      s.screen.appendChild(pop); s.hpick=pop;
      K.placePop(pop,btn);
      s.hpickOff=function(e){ if(!pop.contains(e.target)) closePicker(); };
      document.addEventListener('mousedown',s.hpickOff,true);
      pop.addEventListener('keydown',function(e){
        var its=Array.prototype.slice.call(pop.querySelectorAll('.sg-menu-item')), i=its.indexOf(document.activeElement);
        if(e.key==='ArrowDown'){ e.preventDefault(); its[(i+1)%its.length].focus(); }
        else if(e.key==='ArrowUp'){ e.preventDefault(); its[(i-1+its.length)%its.length].focus(); }
        else if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); closePicker(); s.grid.focus(); }
      });
      (pop.querySelector('[aria-checked=true]')||pop.firstChild).focus();
    }
    function setValue(rowKey,key,value){
      var s=K.s(), it=s.dv.getItemById(rowKey); if(!it) return;
      var prev=it[key];
      var ret=typeof s.opts.onEdit==='function'?s.opts.onEdit(rowKey,key,value):undefined;
      if(ret===false){ K.say('That change was not accepted.'); return; }
      var c=Object.assign({},it); c[key]=value; K.prepare(c);
      s.dv.updateItem(rowKey,c);
      if(prev!==value) K.say((s.colByKey[key]||{label:key}).label+' set to '+K.optLabel(s.colByKey[key]||{opts:[]},value)+' for '+rowKey+'.');
    }

    return {
      column:function(c,raw){
        c.symbols=raw.symbols||null;
        c.icon=raw.icon?{key:raw.icon.key,label:raw.icon.label||raw.icon.key,options:K.normOptions(raw.icon.options)}:null;
        if(c.symbols) c.decor=symDecor; else if(c.icon) c.decor=iconDecor;
      },
      grid:function(s){
        var grid=s.grid, dv=s.dv;
        grid.onClick.subscribe(function(e,args){
          var ne=e&&e.getNativeEvent?e.getNativeEvent():e, t=ne&&ne.target;
          var b=t&&t.closest&&t.closest('[data-sg-hdot],[data-sg-sym]'); if(!b) return;
          var c=grid.getColumns()[args.cell], it=dv.getItem(args.row);
          if(!c||!c.sg||!it) return;
          var sym=b.hasAttribute('data-sg-sym');
          if(sym?!c.sg.symbols:!c.sg.icon) return;
          if(e.stopImmediatePropagation) e.stopImmediatePropagation();
          if(!s.opts.editable||(sym&&!c.sg.editable)){ K.say('This view is read only.'); return; }
          if(sym) openSymPicker(b,it[s.rowKey],c.sg); else openHealthPicker(b,it[s.rowKey],c.sg);
        });
      },
      close:function(s){ if(s.hpick){ s.hpick.remove(); document.removeEventListener('mousedown',s.hpickOff,true); } }
    };
  });
})(window);
