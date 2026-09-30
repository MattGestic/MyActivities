/* =====================================================================
   SRET grid view (D-09): the core. One full-screen table view with
   optional features, each in its own file under features/. The core has
   no knowledge of any one app: everything app-specific comes in through
   setup() once per deployment, or through open() per screen.

   1. Deployment (once, upfront; docs/grid-view-integration.md section 6):
     SRETGrid.setup({
       features: ['refs','marks','bulk-edit','lists','xlsx','import'],
                   // optional: which loaded features to use (default all loaded)
       defaults: { host, ensureXLSX, pin:['id','name'], renderSymbol, ... },
                   // any open() option; each screen's own options win
       text:     { readOnlyCell, noun:['task','tasks'], refsPlaceholder, refsUnknown },
       dates:    { format(iso)->text, parse(text)->iso|null, excel:'d-mmm-yy' },
       layout:   { pinBelow:1024, phoneBelow:768, pinShare:0.62, pinMin:100 }
     }) -> {features, text, dates, layout}
   It fails fast: an unknown feature name, or a feature whose module is not
   loaded (lists needs SRETCollections), throws here rather than on first use.

   2. Screen (per use):
     SRETGrid.open({
       title, columns:[{key,label,type,editable,options,width}], rows, rowKey,
       editable, onEdit(rowKey,key,value), onAdd(), onDelete(rowKeys),
       onBack(), exportName, ensureXLSX, host, canEdit(rowKey,key),
       openColumn, onOpenItem(rowKey), text:{...},
       views:[{id,label,count}], view, onView(id)   (title becomes a view switcher)
       pickers:[{sg,label,items:[{id,label,checked}],onSelect(id)}], note,
       pin:['id','name']   columns kept in view on narrow screens (with the checkbox)
       pinPhone:['id']     pinned instead below layout.phoneBelow (default: pin)
       toolsItems:[{label,sg,onSelect}]
       + feature options: lists (lists), importer / onImport (import),
         refOptions (refs), renderSymbol (marks), onTemplate (xlsx)
     })
     SRETGrid.close()   SRETGrid.setRows(rows)   SRETGrid.patchRows(rows)   SRETGrid.isOpen()
     SRETGrid.dialog(title, build, {wide})   SRETGrid.refresh(cfg)   SRETGrid.features()
     Features add: SRETGrid.exportVisible() (xlsx), SRETGrid.importAoa(aoa, fileName) (import).
   Column types: text, date, number, select, plus those features add (refs).
   A type no loaded feature provides is shown as text. Column extras:
   min/max (numbers), hidden (kept for export and the import template, not
   shown), tones {value: tone} (shaded cell); marks adds icon and symbols.
   Return false from onEdit to refuse a value (the cell reverts), from
   onDelete to keep the rows. onAdd returns the new row object (with its
   rowKey) or nothing to add no row. canEdit, optional, refuses an edit on
   one row where the column is otherwise editable.

   3. Features (SRETGrid.feature(name, function(kit){ return hooks; })):
   the factory runs once when its file loads and gets the kit (the core's
   helpers: h, esc, s() for the open screen, t(key), say, makeMenu,
   openDialog, placePop, display, optLabel, normOptions, isoOk, dates(),
   selectedKeys, hideConfirm, updateStatus, prepare, refreshAll,
   rowsChanged, provide(name, obj), get(name), active(name)). Hooks, all
   optional; the core calls only those of features active on the screen:
     needs:[globals]        checked by setup() and open()
     use(opts) -> bool      active on this screen (default: always)
     types:{name:{width, editor}}   text:{key: default}   api:{name: fn}
     init(s)                first, on the new screen state
     column(c, raw)         per column; may set c.decor(c,v,item,txt) -> html
     columns(cols) -> cols  add columns (aux, beforeCheck, filterShown, slickDef)
     bar2(s) / bar3(s) -> [{order, el}]   header controls, placed by order
     addMenu(s) / tools(s) -> {order, items}   menu groups, separated
     body(s) -> [el]        before the grid (rail, panels)
     grid(s)                after the engine is built, before it is drawn
     prepare(item)          derive fields on every row copy the grid holds
     rowFilter(item) -> bool   rowClass(item) -> class
     status(s, selected)    busy(s) -> bool (keeps the counts row shown)
     beforeConfirm(s)       close(s)
   Kept per screen: the grid holds copies; the caller's rows are never
   mutated, and an edit reaches the caller only through onEdit.

   Data in, callbacks out. No app globals. The only globals touched are the
   grid engine (Slick), window.XLSX as a fallback for export, and the
   helper modules a feature names in needs.

   Engine: SlickGrid 5 (MIT), vendored under vendor/slickgrid/. The engine
   supplies virtual rendering, keyboard navigation, the edit lock (Enter to
   edit and commit, Esc to cancel), column resize and checkbox selection.
   ===================================================================== */
(function(root){
  'use strict';

  var MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  // Built-in column types; features register more (TYPES[name].feature).
  var TYPES={text:{width:180},date:{width:96},number:{width:80},select:{width:120}};
  var CHECK_ID='_checkbox_selector';
  var S=null;   // the one open screen, or null

  // ---------- deployment settings (setup) ----------
  var REG=[];          // loaded features, in load order: {name, hooks}
  var SVC={}, SVC_OF={}, LOADING=null;
  var TEXT={readOnlyCell:'This value cannot be edited here.'};
  var CONF=null;       // null until setup(); then {features, defaults, text}
  var DATES=null, LAYOUT=null;
  function defaultDates(){ return {format:fmtDateDMY,parse:parseDateDMY,excel:'d-mmm-yy'}; }
  function defaultLayout(){ return {pinBelow:1024,phoneBelow:768,pinShare:0.62,pinMin:100}; }

  function enabled(name){ return !CONF||!CONF.features||CONF.features.indexOf(name)>=0; }
  function checkNeeds(f,where){
    (f.hooks.needs||[]).forEach(function(g){
      if(!root[g]) throw new Error('SRETGrid.'+where+': the '+f.name+' feature needs '+g+', which is not loaded.');
    });
  }
  function setup(cfg){
    cfg=cfg||{};
    var names=REG.map(function(f){ return f.name; });
    if(cfg.features){
      var unknown=cfg.features.filter(function(n){ return names.indexOf(n)<0; });
      if(unknown.length) throw new Error('SRETGrid.setup: feature'+(unknown.length>1?'s':'')+' not loaded: '+unknown.join(', ')+
        '. Loaded: '+(names.join(', ')||'none')+'.');
    }
    var d=defaultDates(), l=defaultLayout();
    ['format','parse'].forEach(function(k){
      if(cfg.dates&&cfg.dates[k]!=null&&typeof cfg.dates[k]!=='function') throw new Error('SRETGrid.setup: dates.'+k+' must be a function.');
    });
    Object.keys(cfg.layout||{}).forEach(function(k){
      if(!(k in l)) throw new Error('SRETGrid.setup: unknown layout setting '+k+'.');
      if(!(typeof cfg.layout[k]==='number'&&isFinite(cfg.layout[k])&&cfg.layout[k]>0)) throw new Error('SRETGrid.setup: layout.'+k+' must be a positive number.');
    });
    var next={features:cfg.features?cfg.features.slice():null,defaults:Object.assign({},cfg.defaults),text:Object.assign({},cfg.text)};
    var prev=CONF; CONF=next;
    try{ REG.forEach(function(f){ if(enabled(f.name)) checkNeeds(f,'setup'); }); }
    catch(e){ CONF=prev; throw e; }
    DATES=Object.assign(d,cfg.dates); LAYOUT=Object.assign(l,cfg.layout);
    return {features:features(),text:Object.assign({},TEXT,CONF.text),dates:Object.assign({},DATES),layout:Object.assign({},LAYOUT)};
  }
  function features(){ return REG.filter(function(f){ return enabled(f.name); }).map(function(f){ return f.name; }); }
  function feature(name,factory){
    if(REG.some(function(f){ return f.name===name; })) throw new Error('SRETGrid.feature: '+name+' is already loaded.');
    LOADING=name;
    var hooks;
    try{ hooks=factory(KIT)||{}; } finally { LOADING=null; }
    Object.keys(hooks.types||{}).forEach(function(k){ TYPES[k]=Object.assign({feature:name},hooks.types[k]); });
    Object.keys(hooks.text||{}).forEach(function(k){ if(!(k in TEXT)) TEXT[k]=hooks.text[k]; });
    Object.keys(hooks.api||{}).forEach(function(k){ api[k]=hooks.api[k]; });
    REG.push({name:name,hooks:hooks});
  }
  // Text: the screen's own, then the deployment's, then the defaults.
  function t(key){
    var o=S&&S.opts.text;
    if(o&&o[key]!=null) return o[key];
    if(CONF&&CONF.text[key]!=null) return CONF.text[key];
    return TEXT[key];
  }

  // ---------- value helpers ----------
  function esc(s){
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function isoOk(v){ return typeof v==='string' && /^\d{4}-\d{2}-\d{2}/.test(v); }
  // Default date format: 2026-08-29 -> 29-Aug-26 (the SRET board's).
  function fmtDateDMY(v){
    if(!isoOk(v)) return v==null?'':String(v);
    var y=v.slice(0,4), m=+v.slice(5,7), d=+v.slice(8,10);
    return d+'-'+MONTHS[m-1]+'-'+y.slice(2);
  }
  // Accepts ISO or d-Mmm-yy(yy); returns ISO or null. Used by filter operators.
  function parseDateDMY(s){
    s=String(s).trim();
    if(/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    var m=/^(\d{1,2})[-\s]([A-Za-z]{3})[-\s](\d{2}|\d{4})$/.exec(s);
    if(!m) return null;
    var mi=MONTHS.map(function(x){return x.toLowerCase();}).indexOf(m[2].toLowerCase());
    if(mi<0) return null;
    var y=m[3].length===2?'20'+m[3]:m[3];
    return y+'-'+String(mi+1).padStart(2,'0')+'-'+String(+m[1]).padStart(2,'0');
  }
  DATES=defaultDates(); LAYOUT=defaultLayout();
  function fmtDate(v){ return DATES.format(v); }
  function parseDate(s){ return DATES.parse(s); }
  function normOptions(opts){
    return (opts||[]).map(function(o){
      return (o && typeof o==='object')?{value:o.value,label:o.label==null?String(o.value):String(o.label)}
                                       :{value:o,label:String(o)};
    });
  }
  function optLabel(col,v){
    for(var i=0;i<col.opts.length;i++) if(String(col.opts[i].value)===String(v)) return col.opts[i].label;
    return String(v);
  }
  function display(col,v){
    if(v==null||v==='') return '';
    if(col.type==='date') return fmtDate(v);
    if(col.type==='select') return optLabel(col,v);
    return String(v);
  }

  // Cell text, with a feature's decoration (set per column at open) and status shading.
  function cellFormatter(r,cell,v,colDef,item){
    var c=colDef.sg, txt=esc(display(c,v));
    if(c.decor) txt=c.decor(c,v,item,txt);
    if(c.tones&&v!=null&&c.tones[v]) return {text:txt,addClasses:'sg-tone sg-tone-'+c.tones[v]};
    return txt;
  }

  // ---------- editors (SlickGrid editor interface) ----------
  // One class for all four types. Native inputs so the browser draws the date
  // picker and select list in the active colour-scheme.
  function Editor(args){
    this.args=args;
    this.col=args.column.sg;
    var type=this.col.type, el;
    if(type==='select'){
      el=document.createElement('select');
      var blank=document.createElement('option'); blank.value=''; blank.textContent='';
      el.appendChild(blank);
      this.col.opts.forEach(function(o){
        var op=document.createElement('option'); op.value=String(o.value); op.textContent=o.label; el.appendChild(op);
      });
    } else {
      el=document.createElement('input');
      el.type=type==='date'?'date':'text';
      if(type==='number') el.inputMode='decimal';
    }
    el.className='sg-editor';
    el.setAttribute('aria-label',this.col.label);
    // Left/right move the caret inside a text field rather than the active cell.
    el.addEventListener('keydown',function(e){
      if((e.key==='ArrowLeft'||e.key==='ArrowRight') && el.tagName==='INPUT') e.stopImmediatePropagation();
    });
    args.container.appendChild(el);
    this.el=el;
    el.focus();
  }
  Editor.prototype.destroy=function(){ this.el.remove(); };
  Editor.prototype.focus=function(){ this.el.focus(); };
  Editor.prototype.loadValue=function(item){
    this.def=item[this.col.key];
    this.el.value=this.def==null?'':String(this.def);
    if(this.el.select) this.el.select();
  };
  Editor.prototype.serializeValue=function(){
    var v=this.el.value;
    if(this.col.type==='number') return v.trim()===''?null:Number(v);
    if(this.col.type==='date') return v||null;
    if(this.col.type==='select'){
      for(var i=0;i<this.col.opts.length;i++) if(String(this.col.opts[i].value)===v) return this.col.opts[i].value;
      return v===''?null:v;
    }
    return v;
  };
  Editor.prototype.applyValue=function(item,state){ item[this.col.key]=state; };
  Editor.prototype.isValueChanged=function(){
    var a=this.serializeValue(), b=this.def;
    return String(a==null?'':a)!==String(b==null?'':b);
  };
  Editor.prototype.validate=function(){
    var v=this.el.value.trim();
    if(this.col.type==='number' && v!=='' && !isFinite(Number(v))) return {valid:false,msg:'Enter a number'};
    return {valid:true,msg:null};
  };
  // ---------- filtering and sorting ----------
  var OP_RE=/^(>=|<=|>|<|=)\s*(.+)$/;
  function cmpOp(op,a,b){
    return op==='>'?a>b:op==='<'?a<b:op==='>='?a>=b:op==='<='?a<=b:a===b;
  }
  // Number and date columns take >, <, >=, <=, = operators; everything else
  // (and those columns without an operator) is a case-insensitive contains
  // match on the displayed text, which is what the user sees.
  function matchCol(col,v,f){
    var m=(col.type==='number'||col.type==='date')?OP_RE.exec(f):null;
    if(m){
      if(v==null||v==='') return false;
      if(col.type==='number'){ var n=Number(m[2]); return isFinite(n) && cmpOp(m[1],Number(v),n); }
      var d=parseDate(m[2]); return !!d && isoOk(v) && cmpOp(m[1],v.slice(0,10),d);
    }
    return display(col,v).toLowerCase().indexOf(f.toLowerCase())>=0;
  }
  function rowPasses(item){
    var s=S; if(!s) return true;
    for(var i=0;i<s.rowFilters.length;i++) if(!s.rowFilters[i](item)) return false;
    for(var k in s.filters){
      var f=s.filters[k].trim(); if(!f) continue;
      if(!matchCol(s.colByKey[k],item[k],f)) return false;
    }
    var q=s.quick.trim().toLowerCase();
    if(q){
      for(i=0;i<s.cols.length;i++)
        if(display(s.cols[i],item[s.cols[i].key]).toLowerCase().indexOf(q)>=0) return true;
      return false;
    }
    return true;
  }
  function comparer(key,col){
    return function(a,b){
      var x=a[key], y=b[key];
      var ex=(x==null||x===''), ey=(y==null||y==='');
      if(ex||ey) return ex===ey?0:(ex?-1:1);
      if(col.type==='number') return Number(x)-Number(y);
      if(col.type==='date') return x<y?-1:x>y?1:0;   // ISO strings order as dates
      return display(col,x).localeCompare(display(col,y),undefined,{numeric:true,sensitivity:'base'});
    };
  }
  // ---------- DOM helpers ----------
  function h(tag,attrs,kids){
    var el=document.createElement(tag);
    for(var k in (attrs||{})){
      if(k==='text') el.textContent=attrs[k];
      else if(k==='on') for(var ev in attrs.on) el.addEventListener(ev,attrs.on[ev]);
      else if(attrs[k]!=null && attrs[k]!==false) el.setAttribute(k,attrs[k]===true?'':attrs[k]);
    }
    (kids||[]).forEach(function(c){ if(c) el.appendChild(c); });
    return el;
  }
  var SEARCH_SVG='<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'+
    '<circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10.5 10.5 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  var BACK_SVG='<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'+
               '<path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  // ---------- dropdown menu (as the Aconex register's "Tools" menu) ----------
  // Secondary actions live in menus so only the core buttons show by default.
  // Items are drawn when the menu opens, so their enabled and checked states
  // are always current. Keyboard: ArrowDown opens, arrows move, Esc closes.
  var CHEVRON='<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true" focusable="false">'+
              '<path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  // split: an existing main button; the menu then becomes the arrow half of a
  // split button (main action on the left, its options on the right).
  // A menu opens below its button, left-aligned; where that would run off
  // the screen it aligns right instead, and caps its width to the screen.
  function keepInside(pop){
    var s=S; if(!s) return;
    pop.style.left=''; pop.style.right=''; pop.style.maxWidth='';
    var sr=s.screen.getBoundingClientRect(), r=pop.getBoundingClientRect(), room=sr.width-8;
    if(r.width>room) pop.style.maxWidth=room+'px';
    r=pop.getBoundingClientRect();
    if(r.right>sr.right-4){
      var wrap=pop.offsetParent?pop.offsetParent.getBoundingClientRect():sr;
      pop.style.left='auto'; pop.style.right='0px';
      r=pop.getBoundingClientRect();
      if(r.left<sr.left+4){ pop.style.right='auto'; pop.style.left=(sr.left+4-wrap.left)+'px'; }
    }
  }
  function makeMenu(label,sg,getItems,extraClass,split){
    var btn=split
      ?h('button',{type:'button','class':'sg-btn sg-split-chev'+(extraClass?' '+extraClass:''),'aria-haspopup':'menu',
                   'aria-expanded':'false','aria-label':label,title:label,'data-sg':sg})
      :h('button',{type:'button','class':'sg-btn sg-btn--menu'+(extraClass?' '+extraClass:''),'aria-haspopup':'menu',
                   'aria-expanded':'false','data-sg':sg},[h('span',{text:label})]);
    var chev=h('span',{'class':'sg-chev'}); chev.innerHTML=CHEVRON; btn.appendChild(chev);
    var pop=h('div',{'class':'sg-menu-pop',role:'menu','aria-label':label,'data-sg':sg+'-menu',hidden:true});
    if(split) split.classList.add('sg-split-main');
    var wrap=h('span',{'class':'sg-menu'+(split?' sg-split':'')},split?[split,btn,pop]:[btn,pop]);
    var m={btn:btn,pop:pop,wrap:wrap};
    function enabled(){ return Array.prototype.slice.call(pop.querySelectorAll('.sg-menu-item:not([disabled])')); }
    function render(){
      pop.innerHTML='';
      getItems().forEach(function(it){
        if(!it) return;
        if(it.sep){ pop.appendChild(h('div',{'class':'sg-menu-sep',role:'separator'})); return; }
        var box=it.checked!=null;
        var b=h('button',{type:'button','class':'sg-menu-item',role:box?(it.radio?'menuitemradio':'menuitemcheckbox'):'menuitem',tabindex:'-1',
                          'data-sg':it.sg||null,'data-sg-list':it.list||null,disabled:!!it.disabled},
                [h('span',{'class':'sg-menu-check','aria-hidden':'true',text:it.checked?'✓':''}),h('span',{text:it.label})]);
        if(box) b.setAttribute('aria-checked',String(!!it.checked));
        // Hides the menu, never rebuilds it, before running the action.
        b.addEventListener('click',function(e){ e.stopPropagation(); close(true); it.onSelect(); });
        pop.appendChild(b);
      });
    }
    function onDoc(e){ if(!wrap.contains(e.target)) close(false); }
    function open(){
      if(S&&S.openMenu&&S.openMenu!==m) S.openMenu.close(false);
      render(); pop.hidden=false; btn.setAttribute('aria-expanded','true'); btn.classList.add('is-open');
      keepInside(pop);
      if(S) S.openMenu=m;
      document.addEventListener('mousedown',onDoc,true);
      var f=enabled()[0]; if(f) f.focus();
    }
    function close(refocus){
      if(pop.hidden) return;
      pop.hidden=true; btn.setAttribute('aria-expanded','false'); btn.classList.remove('is-open');
      if(S&&S.openMenu===m) S.openMenu=null;
      document.removeEventListener('mousedown',onDoc,true);
      if(refocus) btn.focus();
    }
    btn.addEventListener('click',function(){ if(pop.hidden) open(); else close(true); });
    btn.addEventListener('keydown',function(e){ if(e.key==='ArrowDown'){ e.preventDefault(); open(); } });
    pop.addEventListener('keydown',function(e){
      var its=enabled(), i=its.indexOf(document.activeElement);
      if(!its.length) return;
      if(e.key==='ArrowDown'){ e.preventDefault(); its[(i+1)%its.length].focus(); }
      else if(e.key==='ArrowUp'){ e.preventDefault(); its[(i-1+its.length)%its.length].focus(); }
      else if(e.key==='Home'){ e.preventDefault(); its[0].focus(); }
      else if(e.key==='End'){ e.preventDefault(); its[its.length-1].focus(); }
      else if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); close(true); }
      else if(e.key==='Tab') close(false);
    });
    m.open=open; m.close=close; m.isOpen=function(){ return !pop.hidden; };
    return m;
  }

  // Status messages show as a toast over the grid, so they never push the
  // toolbar onto a second row. The text stays readable after it fades.
  function say(text){
    var s=S; if(!s) return;
    s.msgEl.textContent=text||'';
    s.msgEl.classList.toggle('is-shown',!!text);
    if(s.msgTimer) root.clearTimeout(s.msgTimer);
    if(text) s.msgTimer=root.setTimeout(function(){ if(S===s) s.msgEl.classList.remove('is-shown'); },6000);
  }
  function ctlHeight(el){
    var cs=getComputedStyle(el), v=parseFloat(cs.getPropertyValue('--sg-row-h'));
    if(!(isFinite(v)&&v>0)) v=parseFloat(cs.getPropertyValue('--ctl-h'));
    return isFinite(v)&&v>0?v:24;
  }

  // ---------- selection, confirm, add ----------
  function selectedKeys(){
    var s=S;
    return s.grid.getSelectedRows().map(function(r){ var it=s.dv.getItem(r); return it&&it[s.rowKey]; })
            .filter(function(k){ return k!=null; });
  }
  function hideConfirm(){
    var s=S; if(!s) return;
    s.confirmEl.hidden=true; s.confirmEl.innerHTML='';
  }
  function showConfirm(){
    var s=S, keys=selectedKeys(); if(!keys.length) return;
    var n=keys.length;
    s.confirmEl.innerHTML='';
    var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hideConfirm(); if(s.tools) s.tools.btn.focus(); }}});
    var go=h('button',{type:'button','class':'sg-btn sg-btn--danger','data-sg':'confirm-remove',text:'Remove',
      on:{click:function(){ doDelete(keys); }}});
    s.confirmEl.appendChild(h('p',{'class':'sg-confirm-msg',
      text:'Remove '+n+(n===1?' row':' rows')+'? This cannot be undone.'}));
    s.confirmEl.appendChild(h('div',{'class':'sg-confirm-btns'},[cancel,go]));
    s.confirmEl.hidden=false;
    cancel.focus();
  }
  function doDelete(keys){
    var s=S;
    var ok=s.opts.onDelete(keys.slice());
    hideConfirm();
    if(ok===false) return;
    s.grid.setSelectedRows([]);
    s.dv.beginUpdate();
    keys.forEach(function(k){ if(s.dv.getItemById(k)) s.dv.deleteItem(k); });
    s.dv.endUpdate();
    s.grid.invalidate();
    updateStatus();
    s.grid.focus();
  }
  function doAdd(){
    var s=S;
    var row=s.opts.onAdd();
    if(!row || row[s.rowKey]==null) return;
    var copy=Object.assign({},row);
    s.dv.addItem(copy);
    var idx=s.dv.getIdxById(copy[s.rowKey]);
    if(idx==null){ // hidden by a filter: clear filters so the new row is visible
      clearFilters();
      idx=s.dv.getIdxById(copy[s.rowKey]);
    }
    updateStatus();
    if(idx!=null){
      s.grid.scrollRowIntoView(idx);
      var first=firstEditableCell();
      if(first>=0){ s.grid.setActiveCell(idx,first); s.grid.editActiveCell(); }
    }
  }
  function firstDataCell(){
    var cols=S.grid.getColumns();
    for(var i=0;i<cols.length;i++) if(cols[i].sg && !cols[i].sg.aux) return i;
    return 0;
  }
  function firstEditableCell(){
    var cols=S.grid.getColumns();
    for(var i=0;i<cols.length;i++) if(cols[i].sg && cols[i].sg.editable && S.opts.editable) return i;
    return -1;
  }
  function clearFilters(){
    var s=S;
    s.quick=''; s.searchEl.value='';
    for(var k in s.filters) s.filters[k]='';
    s.screen.querySelectorAll('.sg-hfilter').forEach(function(i){ i.value=''; });
    s.dv.refresh();
  }

  // ---------- pinned columns on narrow screens (Matt, 2026-09-30, option A) ----------
  // Below layout.pinBelow px of grid width, the checkbox and the columns named in
  // opts.pin (e.g. ['id','name']) stay put while the rest scrolls sideways.
  // Below layout.phoneBelow of screen width, opts.pinPhone (e.g. ['id']) is pinned instead, so
  // a phone keeps most of its width for the scrolling columns (Matt, 2026-09-30).
  // The last pinned column narrows so the pinned part takes at most about
  // layout.pinShare of the width. SlickGrid's pinned pane cannot scroll up and down on
  // its own (it relies on a wheel handler we keep off for smooth scrolling),
  // so it scrolls natively with its scrollbar hidden and follows the main pane.
  function unpin(s){
    var g=s.grid, byId={}; g.getColumns().forEach(function(c){ byId[c.id]=c; });
    var back=s.baseOrder.map(function(id){ return byId[id]; }).filter(Boolean);
    back.forEach(function(c){ if(s.pinWidths[c.id]) c.width=s.pinWidths[c.id]; });
    s.pinned=false; s.pinSet='';
    g.setOptions({frozenColumn:-1}); g.setColumns(back); g.invalidate();
  }
  function applyPin(){
    var s=S; if(!s||!s.pinKeys.length) return;
    var w=s.gridEl.clientWidth, g=s.grid;
    // Phone is judged on the screen's width (as the CSS phone layout), pinning on the grid's.
    var phone=s.pinPhoneKeys&&s.screen.clientWidth<LAYOUT.phoneBelow;
    var keys=!(w>0)?[]:phone?s.pinPhoneKeys:w<LAYOUT.pinBelow?s.pinKeys:[];
    if(!keys.length){ if(s.pinned) unpin(s); return; }
    // A different set (phone to tablet): back to the full order first.
    if(s.pinned&&s.pinSet!==keys.join()) unpin(s);
    var cols=g.getColumns();
    var ids=[CHECK_ID].concat(keys), pins=[], rest=[];
    ids.forEach(function(id){ var c=cols.filter(function(x){ return x.id===id; })[0]; if(c) pins.push(c); });
    cols.forEach(function(c){ if(pins.indexOf(c)<0) rest.push(c); });
    var last=pins[pins.length-1];
    if(!s.pinned){ s.pinWidths={}; s.pinWidths[last.id]=last.width; }
    var fixed=pins.slice(0,-1).reduce(function(a,c){ return a+c.width; },0);
    last.width=Math.max(LAYOUT.pinMin,Math.min(s.pinWidths[last.id],Math.floor(w*LAYOUT.pinShare)-fixed));
    var was=s.pinned; s.pinned=true; s.pinSet=keys.join();
    g.setColumns(pins.concat(rest));
    if(!was) g.setOptions({frozenColumn:pins.length-1});
    g.invalidate();
    syncPinnedScroll();
  }
  function syncPinnedScroll(){
    var s=S, left=s.gridEl.querySelector('.slick-pane-top.slick-pane-left .slick-viewport'),
        right=s.gridEl.querySelector('.slick-pane-top.slick-pane-right .slick-viewport');
    if(!left||!right||left.__sgSync) return;
    left.__sgSync=true;
    left.addEventListener('scroll',function(){ if(Math.abs(right.scrollTop-left.scrollTop)>0.5) right.scrollTop=left.scrollTop; },{passive:true});
  }

  // ---------- dialog (centre screen, modal) ----------
  // Used for Import milestones: the app mounts its own schedule import form
  // into the body, so it is the same form, not a copy.
  function focusables(el){
    return Array.prototype.slice.call(el.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'));
  }
  function openDialog(title,build,o){
    var s=S; if(s.dialog) s.dialog.close();
    var body=h('div',{'class':'sg-dialog-body','data-sg':'dialog-body'});
    var x=h('button',{type:'button','class':'sg-iconbtn','aria-label':'Close',title:'Close','data-sg':'dialog-close',text:'✕'});
    var dlg=h('div',{'class':'sg-dialog'+(o&&o.wide?' sg-dialog--wide':''),role:'dialog','aria-modal':'true','aria-labelledby':'sg-dialog-title','data-sg':'dialog'},[
      h('div',{'class':'sg-dialog-head'},[h('h3',{'class':'sg-dialog-title',id:'sg-dialog-title',text:title}),x]),body]);
    var scrim=h('div',{'class':'sg-scrim','data-sg':'dialog-scrim'},[dlg]);
    var ret=document.activeElement, cleanup=null;
    var d={el:dlg};
    d.close=function(){
      if(s.dialog!==d) return;
      s.dialog=null;
      if(typeof cleanup==='function') cleanup();
      scrim.remove();
      if(ret&&ret.focus&&document.contains(ret)) ret.focus();
    };
    s.dialog=d;
    s.screen.appendChild(scrim);
    x.addEventListener('click',d.close);
    scrim.addEventListener('mousedown',function(e){ if(e.target===scrim) d.close(); });
    dlg.addEventListener('keydown',function(e){
      if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); d.close(); return; }
      if(e.key!=='Tab') return;
      var f=focusables(dlg); if(!f.length) return;
      if(e.shiftKey&&document.activeElement===f[0]){ e.preventDefault(); f[f.length-1].focus(); }
      else if(!e.shiftKey&&document.activeElement===f[f.length-1]){ e.preventDefault(); f[0].focus(); }
    });
    cleanup=build(body,d.close);
    var first=focusables(body)[0]||x; first.focus();
    return d;
  }

  // Put a popup under its anchor inside the screen, flipping left or up
  // when it would run off the right or bottom edge.
  function placePop(pop,anchor){
    var s=S, r=anchor.getBoundingClientRect(), sr=s.screen.getBoundingClientRect();
    var w=pop.offsetWidth, hgt=pop.offsetHeight, left=r.left-sr.left, top=r.bottom-sr.top+4;
    if(left+w>sr.width-4) left=Math.max(4,sr.width-4-w);
    if(top+hgt>sr.height-4&&r.top-sr.top-hgt-4>=0) top=r.top-sr.top-hgt-4;
    pop.style.left=left+'px'; pop.style.top=top+'px';
  }

  // ---------- rows held by the grid ----------
  // Every row copy passes through the active features' prepare hooks (e.g.
  // the lists feature derives the List column), so there is one path for it.
  function prepare(item){
    var s=S; if(!s) return item;
    for(var i=0;i<s.prepares.length;i++) s.prepares[i](item);
    return item;
  }
  function refreshAll(){
    var s=S; if(!s) return;
    if(s.prepares.length) s.dv.getItems().forEach(prepare);
    s.dv.refresh(); s.grid.invalidate();
    updateStatus();
  }
  // After rows were added or replaced.
  function rowsChanged(){
    var s=S; if(!s) return;
    if(s.prepares.length) refreshAll(); else { s.grid.invalidate(); updateStatus(); }
  }
  function patchRows(rows){
    var s=S; if(!s) return;
    s.dv.beginUpdate();
    (rows||[]).forEach(function(r){
      var k=r&&r[s.rowKey], cur=k!=null&&s.dv.getItemById(k);
      if(cur){ var it=Object.assign({},cur,r); prepare(it); s.dv.updateItem(k,it); }
    });
    s.dv.endUpdate();
  }

  // ---------- status ----------
  function updateStatus(){
    var s=S; if(!s) return;
    var shown=s.dv.getLength(), total=s.dv.getItems().length, sel=s.grid.getSelectedRows().length, busy=false, i;
    s.countEl.textContent=shown===total?(total+(total===1?' row':' rows')):(shown+' of '+total+' rows');
    s.selEl.textContent=sel?('('+sel+' selected)'):'';
    s.selAllBtn.textContent=shown&&sel===shown?'Clear selection':'Select all';
    s.selAllBtn.disabled=!shown;
    for(i=0;i<s.feats.length;i++) if(s.feats[i].busy&&s.feats[i].busy(s)) busy=true;
    s.bar3.classList.toggle('is-idle',!sel&&!busy);
    for(i=0;i<s.feats.length;i++) if(s.feats[i].status) s.feats[i].status(s,sel);
  }

  // ---------- features on a screen ----------
  // Which loaded features take part: enabled in setup() and use(opts) true.
  // Screen options that need a feature fail here when it is missing.
  var NEEDS={lists:'lists',importer:'import',onImport:'import'};
  function activeFeatures(o){
    var on=[];
    REG.forEach(function(f){
      if(!enabled(f.name)) return;
      if(f.hooks.use&&!f.hooks.use(o)) return;
      checkNeeds(f,'open');
      on.push(f);
    });
    var names=on.map(function(f){ return f.name; });
    Object.keys(NEEDS).forEach(function(k){
      if(o[k]&&names.indexOf(NEEDS[k])<0)
        throw new Error('SRETGrid.open: '+k+' needs the '+NEEDS[k]+' feature (features/'+NEEDS[k]+'.js), which is not '+
          (REG.some(function(f){ return f.name===NEEDS[k]; })?'enabled in setup()':'loaded')+'.');
    });
    return on;
  }
  function typeOf(t){
    var T=TYPES[t];
    if(!T) return 'text';
    if(T.feature&&!enabled(T.feature)) throw new Error('SRETGrid.open: column type "'+t+'" needs the '+T.feature+' feature, which is not enabled in setup().');
    return t;
  }
  // Menu groups from the core and the features, in order, split by separators.
  function joinGroups(groups){
    var out=[];
    groups.filter(function(g){ return g&&(g.items||[]).some(Boolean); })
      .sort(function(a,b){ return a.order-b.order; })
      .forEach(function(g,i){ if(i) out.push({sep:1}); g.items.forEach(function(x){ if(x) out.push(x); }); });
    return out;
  }
  function collect(s,hook){
    var out=[];
    s.feats.forEach(function(f){ if(f[hook]){ var r=f[hook](s); if(r) out=out.concat(r); } });
    return out;
  }
  function placed(items){
    return items.filter(function(x){ return x&&x.el; }).sort(function(a,b){ return a.order-b.order; }).map(function(x){ return x.el; });
  }

  // ---------- open / close ----------
  function open(cfg){
    if(!root.Slick||!root.Slick.Grid||!root.Slick.Data) throw new Error('SRETGrid: grid library not loaded.');
    // The deployment's defaults, then this screen's own options.
    var opts=Object.assign({},CONF&&CONF.defaults,cfg);
    if(!opts.rowKey) throw new Error('SRETGrid.open: rowKey is required.');
    var feats=activeFeatures(opts), hooks=feats.map(function(f){ return f.hooks; });
    var rowKey=opts.rowKey;
    var cols=(opts.columns||[]).map(function(c){
      var type=typeOf(c.type);
      var col={key:c.key,label:c.label==null?c.key:String(c.label),type:type,editable:!!c.editable,
               opts:normOptions(c.options),width:c.width||TYPES[type].width,min:c.min,max:c.max,options:c.options,
               hidden:!!c.hidden,tones:c.tones||null};
      hooks.forEach(function(f){ if(f.column) f.column(col,c); });
      return col;
    });
    hooks.forEach(function(f){ if(f.columns) cols=f.columns(cols); });
    var colByKey={}; cols.forEach(function(c){ colByKey[c.key]=c; });

    // A view switch replaces the screen but keeps where Back returns to.
    var carried=S&&S.switching?S.returnFocus:null;
    if(S) close(true);
    var gridEditable=!!opts.editable;
    var s={opts:opts,rowKey:rowKey,cols:cols,colByKey:colByKey,filters:{},quick:'',
           feats:hooks,featNames:feats.map(function(f){ return f.name; }),
           prepares:hooks.filter(function(f){ return f.prepare; }).map(function(f){ return f.prepare; }),
           rowFilters:hooks.filter(function(f){ return f.rowFilter; }).map(function(f){ return f.rowFilter; }),
           canAdd:gridEditable&&typeof opts.onAdd==='function',canDel:gridEditable&&typeof opts.onDelete==='function',
           openMenu:null,prev:null,returnFocus:carried||document.activeElement,ro:null,dialog:null,msgTimer:0};
    S=s;
    cols.forEach(function(c){ s.filters[c.key]=''; });
    hooks.forEach(function(f){ if(f.init) f.init(s); });

    var host=opts.host||document.body;
    var fixed=host===document.body;
    var back=h('button',{type:'button','class':'sg-iconbtn sg-back','aria-label':'Back',title:'Back','data-sg':'back'});
    back.innerHTML=BACK_SVG;
    // Views (Matt, 2026-09-28): with more than one, the title is a menu that
    // switches between them (e.g. User tasks, Schedule milestones,
    // Schedule updates). The caller reopens the grid in onView(id).
    var views=(opts.views||[]).filter(function(v){ return v&&v.id; });
    var viewMenu=views.length>1&&typeof opts.onView==='function'?makeMenu(opts.title||'Table','view',function(){
      return views.map(function(v){ return {label:v.label+(v.count!=null?' ('+v.count+')':''),sg:'view-'+v.id,radio:true,checked:v.id===opts.view,
        onSelect:function(){ if(v.id===opts.view) return; S.switching=true; opts.onView(v.id); if(S&&S.opts===opts) S.switching=false; }}; });
    },'sg-title-btn'):null;
    if(viewMenu){ viewMenu.btn.title='Switch view'; viewMenu.pop.setAttribute('aria-label','Views'); }
    var title=viewMenu?h('h2',{'class':'sg-title sg-title--views'},[viewMenu.wrap]):h('h2',{'class':'sg-title',text:opts.title||'Table'});
    var search=h('input',{type:'search','class':'sg-search',placeholder:'Search','aria-label':'Search all columns','data-sg':'search'});
    var count=h('span',{'class':'sg-count','data-sg':'count'});
    var selc=h('span',{'class':'sg-selcount','data-sg':'selcount'});
    var add=s.canAdd?h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'add',text:'Add row'}):null;
    // Delete selected rows: the same item in the Add row menu and in Tools.
    var deleteItem=function(){
      var sel=S&&S.grid?S.grid.getSelectedRows().length:0;
      return {label:'Delete selected rows…',sg:'delete',disabled:!sel,onSelect:function(){
        S.feats.forEach(function(f){ if(f.beforeConfirm) f.beforeConfirm(S); }); showConfirm(); }};
    };
    // Add row is a split button (Matt, 2026-09-28): Delete selected rows,
    // then the features' groups (export and the template, then import),
    // each set apart by a separator.
    var addMenu=s.canAdd?makeMenu('More add options','add-more',function(){
      return joinGroups([s.canDel?{order:10,items:[deleteItem()]}:null].concat(collect(s,'addMenu')));
    },'sg-btn--primary',add):null;
    var selAll=h('button',{type:'button','class':'sg-link','data-sg':'select-all',text:'Select all'});
    var toolsGroups=function(){
      return joinGroups([s.canDel?{order:20,items:[deleteItem()]}:null,
        (opts.toolsItems||[]).length?{order:30,items:opts.toolsItems.map(function(x){ return {label:x.label,sg:x.sg,onSelect:x.onSelect}; })}:null]
        .concat(collect(s,'tools')));
    };
    var tools=toolsGroups().length?makeMenu('Tools','tools',toolsGroups):null;
    var msg=h('span',{'class':'sg-msg',role:'status','aria-live':'polite','data-sg':'msg'});
    // Row 1: back, title. Row 2 (starts in line with the title): search,
    // pickers, Add row, then feature controls and Tools. Row 3: counts,
    // Select all, feature pills, the note.
    // Phones: search sits behind this button in the title row (shown by CSS only below 768px).
    var searchToggle=h('button',{type:'button','class':'sg-iconbtn sg-search-toggle','aria-label':'Search','aria-expanded':'false',title:'Search','data-sg':'search-toggle'});
    searchToggle.innerHTML=SEARCH_SVG;
    var bar=h('div',{'class':'sg-bar'},[h('div',{'class':'sg-bar-lead'},[back,title]),searchToggle]);
    // Pickers (e.g. Schedule changes: which schedule, compared with what):
    // radio menus after the search; the caller reopens the grid in onSelect.
    var pickers=(opts.pickers||[]).map(function(p){
      var cur=(p.items||[]).filter(function(i){ return i.checked; })[0];
      var m=makeMenu((p.label?p.label+': ':'')+(cur?cur.label:'None'),p.sg||'picker',function(){
        return (p.items||[]).map(function(i){ return {label:i.label,sg:(p.sg||'picker')+'-'+i.id,radio:true,checked:!!i.checked,
          onSelect:function(){ if(i.checked) return; S.switching=true; p.onSelect(i.id); if(S&&S.opts===opts) S.switching=false; }}; });
      },'sg-picker');
      if(!(p.items||[]).length) m.btn.disabled=true;
      return m;
    });
    var note=opts.note?h('span',{'class':'sg-note','data-sg':'note',text:opts.note,title:opts.note}):null;
    var bar2=h('div',{'class':'sg-bar2'},placed([{order:10,el:search}]
      .concat(pickers.map(function(m){ return {order:20,el:m.wrap}; }),
              [{order:30,el:addMenu&&addMenu.wrap},{order:50,el:tools&&tools.wrap}],collect(s,'bar2'))));
    var bar3=h('div',{'class':'sg-bar3'},placed([{order:10,el:h('span',{'class':'sg-counts'},[count,selc])},{order:20,el:selAll},{order:40,el:note}]
      .concat(collect(s,'bar3'))));
    var confirm=h('div',{'class':'sg-confirm',role:'alertdialog','aria-label':'Confirm remove','data-sg':'confirm',hidden:true});
    var gridEl=h('div',{'class':'sg-grid','data-sg':'grid'});
    var body=h('div',{'class':'sg-body'},collect(s,'body').concat([gridEl]));
    var screen=h('section',{'class':'sg-screen'+(fixed?' sg-screen--fixed':''),role:'region','aria-label':opts.title||'Table'},
                 [bar,bar2,bar3,confirm,body,msg]);
    host.appendChild(screen);

    var rowH=ctlHeight(screen);
    var dv=new root.Slick.Data.DataView({inlineFilters:false});
    var check=new root.Slick.CheckboxSelectColumn({cssClass:'sg-check',width:40,hideInFilterHeaderRow:true});
    var checkDef=check.getColumnDefinition();
    checkDef.headerCssClass='sg-check-h';
    var colDefs=cols.filter(function(c){ return !c.hidden; }).map(function(c){
      if(c.slickDef) return c.slickDef(c);
      var ed=gridEditable&&c.editable;
      var cls=(ed?'sg-cell-edit':'sg-cell-ro')+(c.key===opts.openColumn?' sg-cell-open':'');
      return {id:c.key,field:c.key,name:esc(c.label),toolTip:c.key===opts.openColumn?c.label+' (double-click to open)':c.label,
              width:c.width,minWidth:48,sortable:true,resizable:true,
              sg:c,editor:ed?(TYPES[c.type].editor||Editor):null,cssClass:cls,headerCssClass:ed?'sg-h-edit':null,formatter:cellFormatter};
    });
    // Columns a feature puts before the checkbox (the List column), then the checkbox, then the rest.
    var slickCols=colDefs.filter(function(d){ return d.sg.beforeCheck; }).concat([checkDef],colDefs.filter(function(d){ return !d.sg.beforeCheck; }));
    var grid=new root.Slick.Grid(gridEl,dv,slickCols,{
      editable:gridEditable,autoEdit:false,enableCellNavigation:true,asyncEditorLoading:false,
      enableColumnReorder:false,rowHeight:rowH,headerRowHeight:rowH+8,showHeaderRow:true,
      explicitInitialization:true,forceFitColumns:false,multiColumnSort:false,
      editorCellNavOnLRKeys:false,enableTextSelectionOnCells:true,
      // Scroll smoothness (measured in tools/grid_view_check.py). The engine's
      // own wheel handler exists for frozen columns; left on, it moves
      // scrollTop in whole-row steps against the browser's native scroll, and
      // the two fight on every wheel tick (pinned columns scroll natively
      // instead, see applyPin). Sync rendering stops a fast scroll showing
      // blank rows for a frame while the throttle waits, transforms keep row
      // moves on the compositor, and the larger buffer keeps rows ready just
      // outside the viewport.
      enableMouseWheelScrollHandler:false,forceSyncScrolling:true,
      rowTopOffsetRenderType:'transform',minRowBuffer:10
    });
    grid.setSelectionModel(new root.Slick.RowSelectionModel({selectActiveRow:false}));
    grid.registerPlugin(check);

    Object.assign(s,{grid:grid,dv:dv,screen:screen,host:host,countEl:count,selEl:selc,msgEl:msg,searchEl:search,selAllBtn:selAll,
       tools:tools,confirmEl:confirm,viewMenu:viewMenu,bar3:bar3,gridEl:gridEl});

    grid.onHeaderRowCellRendered.subscribe(function(e,args){
      var c=args.column.sg; args.node.innerHTML='';
      if(!c||(c.filterShown&&!c.filterShown())) return;
      var ops=c.type==='number'||c.type==='date';
      var inp=h('input',{type:'text','class':'sg-hfilter',placeholder:'Filter','aria-label':'Filter '+c.label,'data-sg-filter':c.key,
        title:ops?'Contains, or compare with >, <, >=, <=, = (e.g. >=75'+(c.type==='date'?' or <'+fmtDate('2026-10-01'):'')+')':'Contains'});
      inp.value=S.filters[c.key]||'';
      inp.addEventListener('input',function(){ S.filters[c.key]=inp.value; dv.refresh(); });
      inp.addEventListener('keydown',function(ev){ ev.stopPropagation(); });
      args.node.appendChild(inp);
    });
    grid.onSort.subscribe(function(e,args){
      var c=args.sortCol.sg; if(!c) return;
      dv.sort(comparer(c.key,c),args.sortAsc);
    });
    grid.onBeforeEditCell.subscribe(function(e,args){
      var c=args.column&&args.column.sg;
      if(!gridEditable||!c||!c.editable) return false;
      if(typeof opts.canEdit==='function' && opts.canEdit(args.item[rowKey],c.key)===false){
        say(t('readOnlyCell'));
        return false;
      }
      S.prev={key:args.item[rowKey],field:c.key,value:args.item[c.key]};
      return true;
    });
    grid.onCellChange.subscribe(function(e,args){
      var c=args.column.sg, it=args.item, prev=S.prev;
      var ret=typeof opts.onEdit==='function'?opts.onEdit(it[rowKey],c.key,it[c.key]):undefined;
      if(ret===false && prev && prev.key===it[rowKey] && prev.field===c.key){
        it[c.key]=prev.value;
        say('That change was not accepted.');
      }
      dv.updateItem(it[rowKey],it);
      S.prev=null;
    });
    // Tapping anywhere in the checkbox cell ticks the row, so the tap area is
    // the whole cell, not the 16px box.
    grid.onClick.subscribe(function(e,args){
      var ne=e&&e.getNativeEvent?e.getNativeEvent():e, t=ne&&ne.target, c=grid.getColumns()[args.cell];
      if(!c||c.id!==CHECK_ID||(t&&t.tagName==='INPUT')) return;
      var sel=grid.getSelectedRows().slice(), i=sel.indexOf(args.row);
      if(i>=0) sel.splice(i,1); else sel.push(args.row);
      grid.setSelectedRows(sel);
      if(e.stopImmediatePropagation) e.stopImmediatePropagation();
    });
    grid.onDblClick.subscribe(function(e,args){
      var c=grid.getColumns()[args.cell], it=dv.getItem(args.row);
      if(c&&c.id===opts.openColumn&&it&&typeof opts.onOpenItem==='function') opts.onOpenItem(it[rowKey]);
    });
    grid.onSelectedRowsChanged.subscribe(updateStatus);
    dv.onRowCountChanged.subscribe(function(){ grid.updateRowCount(); grid.render(); updateStatus(); });
    dv.onRowsChanged.subscribe(function(e,args){ grid.invalidateRows(args.rows); grid.render(); });

    // Row classes from features (e.g. rows on My temp list).
    var rowClass=hooks.filter(function(f){ return f.rowClass; }).map(function(f){ return f.rowClass; });
    if(rowClass.length){
      var baseMeta=dv.getItemMetadata.bind(dv);
      dv.getItemMetadata=function(i){
        var m=baseMeta(i), it=dv.getItem(i); if(!it) return m;
        var cls='';
        for(var j=0;j<rowClass.length;j++){ var x=rowClass[j](it); if(x) cls+=' '+x; }
        if(cls){ m=Object.assign({},m||{}); m.cssClasses=((m.cssClasses||'')+cls).trim(); }
        return m;
      };
    }
    hooks.forEach(function(f){ if(f.grid) f.grid(s); });
    grid.init();
    dv.beginUpdate();
    dv.setItems((opts.rows||[]).map(function(r){ return Object.assign({},r); }),rowKey);
    dv.setFilter(rowPasses);
    dv.endUpdate();
    dv.syncGridSelection(grid,false);
    if(s.prepares.length) refreshAll();

    back.addEventListener('click',function(){ var cb=opts.onBack; close(); if(typeof cb==='function') cb(); });
    search.addEventListener('input',function(){ S.quick=search.value; dv.refresh(); screen.classList.toggle('has-search',!!search.value); });
    searchToggle.addEventListener('click',function(){
      var open=!screen.classList.contains('is-search-open');
      screen.classList.toggle('is-search-open',open); searchToggle.setAttribute('aria-expanded',String(open));
      if(open) search.focus(); else searchToggle.focus();
    });
    search.addEventListener('keydown',function(e){
      if(e.key==='Escape'&&!search.value&&screen.classList.contains('is-search-open')){ e.stopPropagation(); searchToggle.click(); }
    });
    if(add) add.addEventListener('click',doAdd);
    selAll.addEventListener('click',function(){
      var n=dv.getLength(), all=n&&grid.getSelectedRows().length===n, rows=[];
      if(!all) for(var i=0;i<n;i++) rows.push(i);
      grid.setSelectedRows(rows);
    });
    screen.addEventListener('keydown',function(e){
      if(e.key==='Escape' && !confirm.hidden){ e.stopPropagation(); hideConfirm(); if(tools) tools.btn.focus(); }
    });
    if(root.ResizeObserver){
      // Resize on the next frame and only when the box really changed. Calling
      // resizeCanvas() inside the observer callback changes layout in the same
      // pass, which loops the observer ("ResizeObserver loop completed").
      // The observer always reports once on observe(); the grid was sized at
      // init, so seed the last size and let that first report be a no-op.
      var box=gridEl.getBoundingClientRect(), lastW=box.width, lastH=box.height, timer=0, pending=false;
      // resizeCanvas() discards an open editor and the text typed into it
      // (measured: in every direction). A resize that lands mid-edit waits
      // until the editor closes, then runs.
      var doResize=function(){
        timer=0; if(!S||S.grid!==grid) return;
        if(grid.getEditorLock().isActive()){ pending=true; return; }
        pending=false; grid.resizeCanvas(); applyPin();
      };
      // A timer, not requestAnimationFrame: it still runs outside the observer
      // callback, and it fires even when no frame is being drawn.
      var schedule=function(){ if(timer) root.clearTimeout(timer); timer=root.setTimeout(doResize,0); };
      grid.onBeforeCellEditorDestroy.subscribe(function(){ if(pending) schedule(); });
      s.requestResize=schedule;
      s.ro=new root.ResizeObserver(function(entries){
        var r=entries[0]&&entries[0].contentRect; if(!r||(r.width===lastW&&r.height===lastH)) return;
        lastW=r.width; lastH=r.height;
        schedule();
      });
      s.ro.observe(gridEl);
    }
    updateStatus();
    var shown=function(k){ return !!colByKey[k]&&!colByKey[k].hidden; };
    s.pinKeys=(opts.pin||[]).filter(shown);
    s.pinPhoneKeys=opts.pinPhone?opts.pinPhone.filter(shown):null;
    if(s.pinPhoneKeys&&!s.pinPhoneKeys.length) s.pinPhoneKeys=null;
    s.baseOrder=grid.getColumns().map(function(c){ return c.id; }); s.pinned=false;
    applyPin();
    if(dv.getLength()) grid.setActiveCell(0,firstDataCell());
    if(carried&&viewMenu) viewMenu.btn.focus();
    return api;
  }

  function close(silent){
    var s=S; if(!s) return;
    if(s.openMenu) s.openMenu.close(false);
    if(s.dialog) s.dialog.close();
    s.feats.forEach(function(f){ if(f.close) f.close(s); });
    S=null;
    if(s.ro) s.ro.disconnect();
    if(s.grid.getEditorLock().isActive()) s.grid.getEditorLock().cancelCurrentEdit();
    s.grid.destroy();
    s.screen.remove();
    if(!silent && s.returnFocus && s.returnFocus.focus && document.contains(s.returnFocus)) s.returnFocus.focus();
  }

  // Replace the rows in the open grid (e.g. after the caller changes its data).
  function setRows(rows){
    var s=S; if(!s) return;
    s.grid.setSelectedRows([]);
    s.dv.setItems((rows||[]).map(function(r){ return Object.assign({},r); }),s.rowKey);
    rowsChanged();
  }

  var api={
    setup:setup,
    feature:feature,
    features:features,
    open:open,
    close:function(){ close(); },
    isOpen:function(){ return !!S; },
    setRows:setRows,
    patchRows:patchRows,
    // A centred modal dialog on the open screen; build(body, close) may return a cleanup.
    dialog:function(title,build,o){ return S?openDialog(title,build,o):null; },
    // Reopen the screen with a new config (e.g. after the caller's data
    // changed) keeping where Back returns to.
    refresh:function(o){ if(S) S.switching=true; return open(o); },
    // Test hook only: the engine objects of the open screen.
    // requestResize is the exact path a ResizeObserver report takes.
    _engine:function(){ return S?{grid:S.grid,dataView:S.dv,requestResize:S.requestResize,features:S.featNames.slice()}:null; },
    _fmtDate:fmtDate
  };

  // What a feature gets: the core's helpers, and the open screen through s().
  var KIT={
    root:root, h:h, esc:esc, t:t, say:say,
    s:function(){ return S; },
    makeMenu:makeMenu, openDialog:openDialog, placePop:placePop,
    display:display, optLabel:optLabel, normOptions:normOptions, isoOk:isoOk,
    dates:function(){ return DATES; },
    selectedKeys:selectedKeys, hideConfirm:hideConfirm, updateStatus:updateStatus,
    prepare:prepare, refreshAll:refreshAll, rowsChanged:rowsChanged,
    // Services between features (refs gives bulk edit its token field).
    // get() answers only while the providing feature is enabled.
    provide:function(name,obj){ SVC[name]=obj; SVC_OF[name]=LOADING; },
    get:function(name){ return SVC[name]&&enabled(SVC_OF[name])?SVC[name]:null; },
    active:function(name){ return !!S&&S.featNames.indexOf(name)>=0; }
  };
  root.SRETGrid=api;
})(window);
