/* =====================================================================
   SRET grid view (D-09). One full-screen table view, three uses:
   annotation collections, user-defined milestones, schedule activities.

   Contract (docs/grid-view-integration.md):
     SRETGrid.open({
       title, columns:[{key,label,type,editable,options,width}], rows, rowKey,
       editable, onEdit(rowKey,key,value), onAdd(), onDelete(rowKeys),
       onBack(), exportName, ensureXLSX, host, canEdit(rowKey,key),
       lists:{ store, refOf(rowKey), labelOf(ref), onChange(result) },
       openColumn, onOpenItem(rowKey), importer:{...},
       views:[{id,label,count}], view, onView(id)   (title becomes a view switcher)
       pickers:[{sg,label,items:[{id,label,checked}],onSelect(id)}], note,
       toolsItems:[{label,sg,onSelect}]   importer.noun:['task','tasks']
     })
     SRETGrid.close()   SRETGrid.setRows(rows)   SRETGrid.patchRows(rows)   SRETGrid.isOpen()
     SRETGrid.dialog(title, build)   SRETGrid.importAoa(aoa, fileName)
   Column extras: min/max (numbers), hidden (kept for export and the
   import template, not shown), tones {value: tone} (shaded cell),
   icon {key,label,options} (a tap-to-edit dot before the value).
   Return false from onEdit to refuse a value (the cell reverts), from
   onDelete to keep the rows. onAdd returns the new row object (with its
   rowKey) or nothing to add no row. canEdit, optional, refuses an edit on
   one row where the column is otherwise editable.
   lists, optional, adds My temp list: "Add to temp list" for the selected
   rows, a "Temp list only" filter, and an expandable panel listing the temp
   items, where selected items are added to a saved list (existing or new),
   removed from the temp list, or the temp list is cleared. It also adds
   a read-only List column (left of the checkbox) and a mark on temp rows. store is the caller's SRETCollections
   store (data in); refOf maps a rowKey to the store's item ref; labelOf(ref),
   optional, names an item in the panel; onChange(result) runs after every
   change so the caller can persist. All rules live in the shared
   SRETCollections module (src/modules/collections/), never here.

   Data in, callbacks out. This module never reads or writes an app global.
   Rows are copied on open, so an edit reaches the caller only through
   onEdit; the caller's own objects are never mutated here. The only globals
   it touches are the grid library (Slick) and, for export, the SheetJS
   library object that ensureXLSX() resolves with (or window.XLSX if the
   loader resolves with nothing, which is what the app's ensureXLSX does).

   Engine: SlickGrid 5 (MIT), vendored under vendor/slickgrid/. The engine
   supplies virtual rendering, keyboard navigation, the edit lock (Enter to
   edit and commit, Esc to cancel), column resize and checkbox selection.
   This file supplies the screen, the editors, header filters, quick
   search, export and the callbacks.
   ===================================================================== */
(function(root){
  'use strict';

  var MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var TYPES={text:1,date:1,number:1,select:1};
  var DEFAULT_WIDTH={text:180,date:96,number:80,select:120};
  var CHECK_ID='_checkbox_selector';
  var S=null;   // the one open screen, or null

  // ---------- value helpers ----------
  function esc(s){
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function isoOk(v){ return typeof v==='string' && /^\d{4}-\d{2}-\d{2}/.test(v); }
  // 2026-08-29 -> 29-Aug-26, the app's board date format.
  function fmtDate(v){
    if(!isoOk(v)) return v==null?'':String(v);
    var y=v.slice(0,4), m=+v.slice(5,7), d=+v.slice(8,10);
    return d+'-'+MONTHS[m-1]+'-'+y.slice(2);
  }
  // Accepts ISO or d-Mmm-yy(yy); returns ISO or null. Used by filter operators.
  function parseDate(s){
    s=String(s).trim();
    if(/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
    var m=/^(\d{1,2})[-\s]([A-Za-z]{3})[-\s](\d{2}|\d{4})$/.exec(s);
    if(!m) return null;
    var mi=MONTHS.map(function(x){return x.toLowerCase();}).indexOf(m[2].toLowerCase());
    if(mi<0) return null;
    var y=m[3].length===2?'20'+m[3]:m[3];
    return y+'-'+String(mi+1).padStart(2,'0')+'-'+String(+m[1]).padStart(2,'0');
  }
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

  // Cell text, with the optional health icon prefix and status shading.
  function cellFormatter(r,cell,v,colDef,item){
    var c=colDef.sg, txt=esc(display(c,v));
    if(c.icon) txt=hdot(c.icon,item?item[c.icon.key]:null)+'<span class="sg-cell-txt">'+txt+'</span>';
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
    if(s.scope && !inScope(item)) return false;
    for(var k in s.filters){
      var f=s.filters[k].trim(); if(!f) continue;
      if(!matchCol(s.colByKey[k],item[k],f)) return false;
    }
    var q=s.quick.trim().toLowerCase();
    if(q){
      for(var i=0;i<s.cols.length;i++)
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
  // Matt, 2026-09-28: the temp list is session only; saved lists are kept.
  var TEMP_HINT='My temp list is for this session only. It clears when the file is closed or reloaded. Add items to a saved list to keep them.';
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
  var LIST_SVG='<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'+
    '<path d="M5 4h8M5 8h8M5 12h8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'+
    '<circle cx="2.5" cy="4" r="1" fill="currentColor"/><circle cx="2.5" cy="8" r="1" fill="currentColor"/><circle cx="2.5" cy="12" r="1" fill="currentColor"/></svg>';

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
    var v=parseFloat(getComputedStyle(el).getPropertyValue('--ctl-h'));
    return isFinite(v)&&v>0?v:24;
  }

  // ---------- status / confirm ----------
  function updateStatus(){
    var s=S; if(!s) return;
    var shown=s.dv.getLength(), total=s.dv.getItems().length, sel=s.grid.getSelectedRows().length;
    s.countEl.textContent=shown===total?(total+(total===1?' row':' rows')):(shown+' of '+total+' rows');
    s.selEl.textContent=sel?('('+sel+' selected)'):'';
    s.selAllBtn.textContent=shown&&sel===shown?'Clear selection':'Select all';
    s.selAllBtn.disabled=!shown;
    if(s.lists) updateLists();
  }
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
    for(var i=0;i<cols.length;i++) if(cols[i].sg && cols[i].id!==L_LIST) return i;
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

  // ---------- lists: My temp list and saved lists ----------
  // The rules live in SRETCollections. This section draws the controls and
  // calls it. Workflow (Matt, 2026-09-27):
  //   1. select rows, Add to temp list
  //   2. open My temp list, select items in it, Add to list
  //   3. Remove selected items from the temp list
  //   4. Clear the temp list (More menu)
  // Layout: one vertical panel docked left, opened from the rail in one of
  // two modes: My temp list, or Saved lists (a dropdown picks the list).
  // Action buttons sit under the title, above the items.
  var L_TMP='_tmp', L_LIST='_list', L_IDS='_lids';
  function M(){ return root.SRETCollections; }
  function listFields(item){
    var s=S, ref=s.lists.refOf(item[s.rowKey]);
    item[L_TMP]=M().inTemp(s.lists.store,ref)?'Yes':'';
    item[L_LIST]=M().membership(s.lists.store,ref).join(', ');
    item[L_IDS]=M().listIdsOf(s.lists.store,ref);
  }
  // Items are the grid's own copies, so the derived fields are written
  // straight onto them; the caller's rows are untouched.
  function refreshLists(){
    var s=S; if(!s||!s.lists) return;
    s.dv.getItems().forEach(listFields);
    s.dv.refresh(); s.grid.invalidate();
    updateStatus();
  }
  function patchRows(rows){
    var s=S; if(!s) return;
    s.dv.beginUpdate();
    (rows||[]).forEach(function(r){
      var k=r&&r[s.rowKey], cur=k!=null&&s.dv.getItemById(k);
      if(cur){ var it=Object.assign({},cur,r); if(s.lists) listFields(it); s.dv.updateItem(k,it); }
    });
    s.dv.endUpdate();
  }
  function selectedRefs(){ var s=S; return selectedKeys().map(function(k){ return s.lists.refOf(k); }); }
  function labelOf(ref){
    var s=S;
    if(typeof s.lists.labelOf==='function'){ var l=s.lists.labelOf(ref); if(l) return String(l); }
    return String(ref).replace(/^[^:]*:/,'');
  }
  function listName(id){
    var c=M().list(S.lists.store).filter(function(x){ return x.id===id; })[0]; return c?c.label:'';
  }
  function listsDone(r){
    var s=S;
    say(M().describe(r));
    if(s.pnlErr) s.pnlErr.textContent=r.error?M().describe(r):'';
    if(!r.error && typeof s.lists.onChange==='function') s.lists.onChange(r);
    if(s.scope&&s.scope.type==='list'&&!listName(s.scope.id)) s.scope=null;
    refreshLists();
    return r;
  }

  // ----- scope filter: only rows on My temp list, or on one saved list -----
  function inScope(item){
    var sc=S.scope;
    if(sc.type==='temp') return item[L_TMP]==='Yes';
    return (item[L_IDS]||[]).indexOf(sc.id)>=0;
  }
  function setScope(sc){ var s=S; s.scope=sc||null; s.dv.refresh(); updateStatus(); }
  function scopeIs(type,id){ var sc=S.scope; return !!sc&&sc.type===type&&(type==='temp'||sc.id===id); }

  // ----- the panel -----
  function panelItems(){
    var s=S, st=s.lists.store;
    return s.panelMode==='temp'?M().temp(st):M().itemsOf(st,s.listId);
  }
  function pickedRefs(){ var s=S; return panelItems().filter(function(r){ return s.picked[r]; }); }
  // Button states only; never rebuilds the item list, so it is safe to call
  // from a checkbox's own change handler.
  function updatePanelButtons(){
    var s=S; if(!s||!s.lists||!s.panelMode) return;
    var items=panelItems(), picked=pickedRefs().length;
    s.pnlAll.checked=!!items.length&&picked===items.length;
    s.pnlAll.indeterminate=picked>0&&picked<items.length;
    s.pnlAll.disabled=!items.length;
    s.pnlPicked.textContent=picked?'('+picked+' selected)':'';
    s.tmpAddMenu.btn.disabled=!picked;
    s.tmpRemove.disabled=!picked;
    s.lstRemove.disabled=!picked;
    s.lstMore.btn.disabled=!s.listId;
  }
  function renderPanel(){
    var s=S, st=s.lists.store, temp=s.panelMode==='temp';
    s.pnlTempHead.hidden=!temp; s.pnlListHead.hidden=temp;
    s.pnlTempActions.hidden=!temp; s.pnlListActions.hidden=temp;
    s.panel.setAttribute('aria-label',temp?'My temp list':'Saved lists');
    s.panel.setAttribute('data-mode',s.panelMode);
    if(!temp){
      var ls=M().list(st);
      if(!ls.some(function(c){ return c.id===s.listId; })) s.listId=ls.length?ls[0].id:null;
      s.lstPick.innerHTML='';
      if(!ls.length) s.lstPick.appendChild(h('option',{value:'',text:'No saved lists yet'}));
      ls.forEach(function(c){ s.lstPick.appendChild(h('option',{value:c.id,text:c.label+' ('+c.count+')'})); });
      s.lstPick.value=s.listId||''; s.lstPick.disabled=!ls.length;
    }
    var items=panelItems();
    Object.keys(s.picked).forEach(function(r){ if(items.indexOf(r)<0) delete s.picked[r]; });
    s.pnlItems.innerHTML='';
    if(!items.length){
      s.pnlItems.appendChild(h('li',{'class':'sg-temp-empty',text:temp?'Empty. Select rows in the table and use Add to temp list.'
        :(s.listId?'This list is empty.':'No saved lists yet. Save one from My temp list.')}));
    }
    items.forEach(function(r){
      var box=h('input',{type:'checkbox','data-sg-item':r,'aria-label':'Select '+labelOf(r)});
      box.checked=!!s.picked[r];
      box.addEventListener('change',function(){ if(box.checked) s.picked[r]=1; else delete s.picked[r]; updatePanelButtons(); });
      var ls=M().membership(st,r);
      s.pnlItems.appendChild(h('li',{'class':'sg-temp-item'+(M().inTemp(st,r)?' sg-in-temp':'')},[
        h('label',{'class':'sg-temp-item-lbl'},[box,h('span',{'class':'sg-temp-item-text'},[
          h('span',{'class':'sg-temp-item-name',text:labelOf(r)}),
          h('span',{'class':'sg-temp-item-lists',text:ls.length?ls.join(', '):'No list'})])])
      ]));
    });
    var here=s.dv.getItems().filter(function(it){ return items.indexOf(s.lists.refOf(it[s.rowKey]))>=0; }).length;
    s.pnlSummary.textContent=items.length+(items.length===1?' item':' items')+(items.length?', '+here+' on this screen':'');
    updatePanelButtons();
  }
  // A control that sets state also shows it: badge, expanded states, the
  // filter pill and enabled buttons all follow the store on every change.
  function updateLists(){
    var s=S; if(!s||!s.lists) return;
    var n=M().temp(s.lists.store).length, sel=s.grid.getSelectedRows().length;
    s.tmpAddBtn.disabled=!sel;
    s.tmpCount.textContent=String(n); s.tmpCount.hidden=!n;
    [['temp',s.railTemp],['list',s.railLists]].forEach(function(p){
      var on=s.panelMode===p[0];
      p[1].setAttribute('aria-expanded',String(on)); p[1].classList.toggle('is-open',on);
    });
    s.pill.hidden=!s.scope;
    if(s.scope) s.pillText.textContent=s.scope.type==='temp'?'My temp list only':'List: '+listName(s.scope.id);
    if(s.panelMode) renderPanel();
  }
  function openPanel(mode){
    var s=S;
    if(mode===s.panelMode) mode=null;
    hideConfirm(); hidePanelForms();
    s.panelMode=mode; s.picked={};
    s.panel.hidden=!mode; s.pnlErr.textContent='';
    updateLists();
    if(s.requestResize) s.requestResize();
    if(mode) (mode==='temp'?s.tmpAddMenu.btn:s.lstPick).focus();
  }
  function closePanel(){ var s=S, m=s.panelMode; if(!m) return; openPanel(m); (m==='temp'?s.railTemp:s.railLists).focus(); }
  function hidePanelForms(){
    var s=S;
    s.pnlConfirm.hidden=true; s.pnlConfirm.innerHTML='';
    s.pnlNewForm.hidden=true; s.pnlName.value='';
  }
  function showNewList(){
    var s=S; if(!pickedRefs().length) return;
    hidePanelForms(); s.pnlNewForm.hidden=false; s.pnlErr.textContent='';
    s.pnlName.focus();
  }
  function saveNewList(){
    var s=S, r=listsDone(M().saveFromTemp(s.lists.store,s.pnlName.value,pickedRefs()));
    if(r.error){ s.pnlName.focus(); return; }
    hidePanelForms(); s.tmpAddMenu.btn.focus();
  }
  function showPanelConfirm(msg,verb,sg,run,back){
    var s=S;
    hidePanelForms();
    var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hidePanelForms(); back.focus(); }}});
    var go=h('button',{type:'button','class':'sg-btn sg-btn--danger','data-sg':sg,text:verb,
      on:{click:function(){ hidePanelForms(); run(); }}});
    s.pnlConfirm.appendChild(h('p',{'class':'sg-confirm-msg',text:msg}));
    s.pnlConfirm.appendChild(h('div',{'class':'sg-confirm-btns'},[cancel,go]));
    s.pnlConfirm.hidden=false;
    cancel.focus();
  }
  function buildPanel(){
    var s=S;
    s.picked={}; s.panelMode=null; s.listId=null;
    var close=h('button',{type:'button','class':'sg-iconbtn','aria-label':'Collapse the panel',title:'Collapse','data-sg':'panel-close',text:'✕'});
    s.pnlTempHead=h('h3',{'class':'sg-temp-title','data-sg':'temp-title',title:TEMP_HINT,'aria-description':TEMP_HINT},[h('span',{'class':'sg-tempmark','aria-hidden':'true'}),h('span',{text:'My temp list'})]);
    s.lstPick=h('select',{'class':'sg-select sg-list-pick','data-sg':'list-pick','aria-label':'Saved list to show'});
    s.pnlListHead=h('span',{'class':'sg-list-head'},[s.lstPick]);
    // Temp mode actions: Add to list (saved lists, New list...), Remove, More.
    s.tmpAddMenu=makeMenu('Add to list','temp-addto',function(){
      var st=s.lists.store, none=!pickedRefs().length;
      return M().list(st).map(function(c){
        return {label:c.label+' ('+c.count+')',list:c.id,disabled:none,
                onSelect:function(){ listsDone(M().addFromTemp(st,c.id,pickedRefs())); }};
      }).concat([{sep:1},{label:'New list…',sg:'temp-newlist',disabled:none,onSelect:showNewList}]);
    },'sg-btn--primary');
    s.tmpRemove=h('button',{type:'button','class':'sg-btn','data-sg':'temp-remove',text:'Remove',
                            title:'Remove the selected items from My temp list'});
    s.tmpMore=makeMenu('More','temp-more',function(){
      return [{label:'Show only these rows in the table',sg:'temp-only-panel',checked:scopeIs('temp'),
               onSelect:function(){ setScope(scopeIs('temp')?null:{type:'temp'}); }},
              {sep:1},
              {label:'Clear temp list…',sg:'temp-clear',disabled:!M().temp(s.lists.store).length,onSelect:function(){
                var n=M().temp(s.lists.store).length;
                showPanelConfirm('Clear My temp list ('+n+(n===1?' item':' items')+')? Saved lists are not changed.','Clear','temp-clear-confirm',
                  function(){ listsDone(M().tempClear(s.lists.store)); s.pnlAll.focus(); },s.tmpMore.btn);
              }}];
    });
    s.pnlTempActions=h('div',{'class':'sg-temp-actions'},[s.tmpAddMenu.wrap,s.tmpRemove,h('span',{'class':'sg-spacer'}),s.tmpMore.wrap]);
    // Saved list mode actions: Remove from this list, More.
    s.lstRemove=h('button',{type:'button','class':'sg-btn','data-sg':'list-remove',text:'Remove from list',
                            title:'Remove the selected items from this list'});
    s.lstMore=makeMenu('More','list-more',function(){
      var id=s.listId;
      return [{label:'Show only these rows in the table',sg:'list-only-panel',checked:scopeIs('list',id),
               onSelect:function(){ setScope(scopeIs('list',id)?null:{type:'list',id:id}); }},
              {sep:1},
              {label:'Delete list…',sg:'list-delete',onSelect:function(){
                var n=M().itemsOf(s.lists.store,id).length;
                showPanelConfirm('Delete the list "'+listName(id)+'" ('+n+(n===1?' item':' items')+')? The items themselves are not changed.','Delete','list-delete-confirm',
                  function(){ listsDone(M().deleteList(s.lists.store,id)); s.lstPick.focus(); },s.lstMore.btn);
              }}];
    });
    s.pnlListActions=h('div',{'class':'sg-temp-actions'},[s.lstRemove,h('span',{'class':'sg-spacer'}),s.lstMore.wrap]);
    s.pnlAll=h('input',{type:'checkbox','data-sg':'panel-all','aria-label':'Select all items'});
    s.pnlSummary=h('span',{'class':'sg-temp-summary','data-sg':'panel-summary'});
    s.pnlPicked=h('span',{'class':'sg-selcount','data-sg':'panel-picked'});
    s.pnlItems=h('ul',{'class':'sg-temp-items','data-sg':'panel-items','aria-label':'Items'});
    s.pnlErr=h('p',{'class':'sg-temp-err',role:'alert','data-sg':'panel-err'});
    s.pnlConfirm=h('div',{'class':'sg-temp-confirm','data-sg':'panel-confirm',hidden:true});
    s.pnlName=h('input',{type:'text','class':'sg-search sg-temp-name','aria-label':'Name for the new list',
                         placeholder:'New list name','data-sg':'temp-name',maxlength:'60'});
    var nCancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hidePanelForms(); s.tmpAddMenu.btn.focus(); }}});
    var nSave=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'temp-newlist-save',text:'Save list',on:{click:saveNewList}});
    s.pnlNewForm=h('div',{'class':'sg-temp-form','data-sg':'temp-newlist-form',hidden:true},[
      h('p',{'class':'sg-temp-form-lbl',text:'Save the selected items as a new list'}),s.pnlName,
      h('div',{'class':'sg-confirm-btns'},[nCancel,nSave])]);
    s.pnlName.addEventListener('keydown',function(e){
      if(e.key==='Enter'){ e.preventDefault(); saveNewList(); }
      else if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); hidePanelForms(); s.tmpAddMenu.btn.focus(); }
    });
    // Title, then the action buttons, then the items (Matt, 2026-09-27).
    s.panel.appendChild(h('div',{'class':'sg-temp-head'},[s.pnlTempHead,s.pnlListHead,h('span',{'class':'sg-spacer'}),close]));
    s.panel.appendChild(s.pnlTempActions);
    s.panel.appendChild(s.pnlListActions);
    s.panel.appendChild(s.pnlNewForm);
    s.panel.appendChild(s.pnlConfirm);
    s.panel.appendChild(s.pnlErr);
    s.panel.appendChild(h('div',{'class':'sg-temp-sub'},[h('label',{'class':'sg-temp-all'},[s.pnlAll,s.pnlSummary]),s.pnlPicked]));
    s.panel.appendChild(s.pnlItems);
    s.pnlAll.addEventListener('change',function(){
      var on=s.pnlAll.checked;
      s.picked={}; if(on) panelItems().forEach(function(r){ s.picked[r]=1; });
      s.pnlItems.querySelectorAll('input[type=checkbox]').forEach(function(b){ b.checked=on; });
      updatePanelButtons();
    });
    s.lstPick.addEventListener('change',function(){ s.listId=s.lstPick.value||null; s.picked={}; hidePanelForms(); renderPanel(); });
    s.tmpRemove.addEventListener('click',function(){ listsDone(M().tempRemove(s.lists.store,pickedRefs())); });
    s.lstRemove.addEventListener('click',function(){ listsDone(M().removeFromList(s.lists.store,s.listId,pickedRefs())); });
    close.addEventListener('click',closePanel);
    s.panel.addEventListener('keydown',function(e){
      if(e.key!=='Escape') return;
      e.preventDefault(); e.stopPropagation();
      if(!s.pnlConfirm.hidden||!s.pnlNewForm.hidden){ hidePanelForms(); (s.panelMode==='temp'?s.tmpAddMenu.btn:s.lstPick).focus(); }
      else closePanel();
    });
  }

  // ----- the List column: collapsed to an indicator, or expanded to names -----
  var LIST_COL_W={collapsed:36,expanded:180};
  function listColName(){
    var ex=S&&S.listExpanded;
    return '<button type="button" class="sg-lcol-toggle" data-sg="list-col-toggle" aria-expanded="'+(ex?'true':'false')+
      '" aria-label="'+(ex?'Collapse':'Expand')+' the List column" title="'+(ex?'Collapse':'Expand')+' the List column">'+
      (ex?'<span>List</span>':'')+'<span class="sg-lcol-arrow" aria-hidden="true">'+(ex?'◂':'▸')+'</span></button>';
  }
  function listColFormatter(r,cell,v){
    var s=S; if(!v) return '';
    if(s&&s.listExpanded) return esc(v);
    var n=String(v).split(', ').length;
    return '<span class="sg-inlist" title="'+esc('In '+v)+'"><span class="sg-inlist-mark" aria-hidden="true"></span>'+n+'</span>';
  }
  function toggleListCol(){
    var s=S; s.listExpanded=!s.listExpanded;
    var cols=s.grid.getColumns();
    cols.forEach(function(c){ if(c.id===L_LIST){ c.width=s.listExpanded?LIST_COL_W.expanded:LIST_COL_W.collapsed; c.name=listColName();
      c.minWidth=s.listExpanded?44:LIST_COL_W.collapsed; } });
    // Collapsed, the column has no filter box; any filter on it is cleared.
    if(!s.listExpanded&&s.filters[L_LIST]){ s.filters[L_LIST]=''; s.dv.refresh(); }
    s.grid.setColumns(cols);
    s.grid.invalidate();
    var b=s.screen.querySelector('[data-sg=list-col-toggle]'); if(b) b.focus();
  }

  // ---------- dialog (centre screen, modal) ----------
  // Used for Import milestones: the app mounts its own schedule import form
  // into the body, so it is the same form, not a copy.
  function focusables(el){
    return Array.prototype.slice.call(el.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'));
  }
  function openDialog(title,build){
    var s=S; if(s.dialog) s.dialog.close();
    var body=h('div',{'class':'sg-dialog-body','data-sg':'dialog-body'});
    var x=h('button',{type:'button','class':'sg-iconbtn','aria-label':'Close',title:'Close','data-sg':'dialog-close',text:'✕'});
    var dlg=h('div',{'class':'sg-dialog',role:'dialog','aria-modal':'true','aria-labelledby':'sg-dialog-title','data-sg':'dialog'},[
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

  // ---------- export ----------
  function exportRows(){
    var s=S, o=s.opts;
    var loader=typeof o.ensureXLSX==='function'?o.ensureXLSX:function(){ return Promise.resolve(); };
    if(s.expBtn) s.expBtn.disabled=true;
    return Promise.resolve().then(loader).then(function(lib){
      var X=lib||root.XLSX;
      if(!X||!X.utils) throw new Error('The Excel library is not available.');
      var aoa=[s.cols.map(function(c){ return c.label; })];
      for(var i=0;i<s.dv.getLength();i++){
        var it=s.dv.getItem(i);
        aoa.push(s.cols.map(function(c){
          var v=it[c.key];
          if(v==null||v==='') return '';
          if(c.type==='number') return Number(v);
          if(c.type==='date' && isoOk(v)) return new Date(Date.UTC(+v.slice(0,4),+v.slice(5,7)-1,+v.slice(8,10)));
          if(c.type==='select') return optLabel(c,v);
          return String(v);
        }));
      }
      var ws=X.utils.aoa_to_sheet(aoa,{cellDates:true,dateNF:'d-mmm-yy'});
      ws['!cols']=s.cols.map(function(c){ return {wch:Math.max(8,Math.round((c.width||100)/7))}; });
      var wb=X.utils.book_new();
      X.utils.book_append_sheet(wb,ws,'Grid');
      var name=String(o.exportName||o.title||'Grid').replace(/[\\\/:*?"<>|]+/g,' ').trim()||'Grid';
      X.writeFile(wb,name+'.xlsx');
      say('Exported '+(aoa.length-1)+(aoa.length-1===1?' row':' rows')+'.');
      return aoa;
    }).catch(function(err){
      if(S) say(err&&err.message?err.message:'Export failed.');
    }).then(function(r){ if(S&&S.expBtn) S.expBtn.disabled=false; return r; });
  }
  // What one imported row is called: importer.noun ['task','tasks'];
  // default milestone (Matt, 2026-09-28: user milestones read as tasks).
  function noun(n){ var im=S&&S.opts.importer, w=im&&im.noun||['milestone','milestones']; return n===1?w[0]:w[1]; }
  function importTitle(){ var w=noun(2); return 'Import '+w; }
  function openImport(){
    var s=S;
    if(s.opts.importer) return openDialog(importTitle(),function(body,close){ return buildImport(body,close); });
    openDialog(importTitle(),function(body,close){ return s.opts.onImport(body,close); });
  }

  // ---------- milestone import (rules in SRETMsImport) ----------
  // Steps in the dialog: choose a file, run the checks, then either a
  // failure notice, a "continue?" question listing what was found, or the
  // summary. Everything found is written to the Import log if the user
  // continues. Rows are added through importer.onCommit, never directly.
  function importCfg(){
    var s=S, im=s.opts.importer;
    return {columns:s.cols.filter(function(c){ return c.key.charAt(0)!=='_'; }),
            idKey:im.idKey||s.rowKey, depKeys:im.depKeys||{},
            existingIds:s.dv.getItems().map(function(it){ return it[s.rowKey]; }),
            knownIds:typeof im.knownIds==='function'?im.knownIds():[],
            dateOrder:S.importUi&&S.importUi.dateSel?S.importUi.dateSel.value:'auto'};
  }
  // Date order for the file: detected from all its dates (SRETDates), or
  // chosen here. Changing it re-runs the checks on the same sheet.
  function dateSelect(ui){
    var sel=h('select',{'class':'sg-select sg-date-order','data-sg':'import-date-order','aria-label':'Date order'},
      [['auto','Detect from the file'],['DMY','Day first (9/10/26 is 9-Oct-26)'],['MDY','Month first (10/9/26 is 9-Oct-26)'],['YMD','Year first (26/10/9 is 9-Oct-26)']]
        .map(function(o){ return h('option',{value:o[0],text:o[1]}); }));
    sel.addEventListener('change',function(){
      if(ui.lastAoa&&ui.status.getAttribute('data-kind')!=='done') runImport(ui.lastAoa,ui.lastFile,ui);
    });
    ui.dateSel=sel;
    return h('label',{'class':'sg-import-date'},[h('span',{text:'Date order'}),sel]);
  }
  function importPanel(ui,kind,children){
    ui.status.innerHTML=''; ui.status.setAttribute('data-kind',kind);
    children.forEach(function(c){ if(c) ui.status.appendChild(c); });
  }
  function issueTable(issues){
    var t=h('table',{'class':'sg-itable','data-sg':'import-issues'});
    t.appendChild(h('thead',{},[h('tr',{},[h('th',{text:'Row'}),h('th',{text:'ID'}),h('th',{text:'Issue'})])]));
    var b=h('tbody');
    issues.slice(0,50).forEach(function(i){ b.appendChild(h('tr',{},[h('td',{text:String(i.rowNum)}),h('td',{text:i.id||'(new)'}),h('td',{text:i.note})])); });
    t.appendChild(b);
    return h('div',{'class':'sg-itable-wrap'},[t,issues.length>50?h('p',{'class':'sg-muted',text:'And '+(issues.length-50)+' more.'}):null]);
  }
  function runImport(aoa,fileName,ui){
    ui.lastAoa=aoa; ui.lastFile=fileName; S.importUi=ui;
    var s=S, res=root.SRETMsImport.check(aoa,importCfg());
    if(res.fatal){
      say('Import failed. '+res.fatal);
      importPanel(ui,'error',[h('p',{'class':'sg-import-head',text:'Import failed'}),h('p',{'data-sg':'import-error',text:res.fatal})]);
      ui.status.setAttribute('role','alert');
      return res;
    }
    var dt=res.dates||{}, D=root.SRETDates;
    if(!res.issues.length&&!dt.ask){ commitImport(res,fileName,ui); return res; }
    var q=res.depIssueRows?'Some dependencies or predecessors are not found. Do you wish to continue with import?'
         :res.issues.length?'Some values could not be read. Do you wish to continue with import?'
         :'The date order could not be confirmed from the file. Do you wish to continue with import?';
    var dateNote=dt.ask?h('p',{'data-sg':'import-date-note',text:'Dates will be read as '+D.orderLabel(dt.order)+' ('+D.example(dt.order)+'). '+
      dt.ambiguous+(dt.ambiguous===1?' date would':' dates would')+' read differently in another order; if that is wrong, choose the order in Date order.'}):null;
    var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ if(ui.onCancel) return ui.onCancel(); importPanel(ui,'',[]); ui.go.focus(); }}});
    var go=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'import-continue',text:'Continue import',
      on:{click:function(){ commitImport(res,fileName,ui); }}});
    importPanel(ui,'confirm',[
      h('p',{'class':'sg-import-head','data-sg':'import-question',text:q}),
      res.depIssueRows&&res.fieldIssueRows?h('p',{text:'Some other values could not be read and will be left blank.'}):null,
      dateNote,
      h('p',{'class':'sg-muted',text:res.rows.length+(res.rows.length===1?' row':' rows')+' will be imported'+
        (res.skipped.length?', '+res.skipped.length+' skipped (ID already in the table)':'')+'.'+(res.issues.length?' Each issue below goes to the Import log.':'')}),
      res.issues.length?issueTable(res.issues):null,
      h('div',{'class':'sg-confirm-btns'},[cancel,go])]);
    ui.status.removeAttribute('role');
    go.focus();
    return res;
  }
  function commitImport(res,fileName,ui){
    var s=S, im=s.opts.importer, idKey=im.idKey||s.rowKey, assigned={}, taken=[];
    var rows=res.rows.map(function(r){
      var d=Object.assign({},r.data);
      if(!d[idKey]){ d[idKey]=im.nextId(taken); taken.push(d[idKey]); assigned[r.rowNum]=d[idKey]; }
      return d;
    });
    var added=typeof im.onCommit==='function'?(im.onCommit(rows)||rows):rows;
    s.dv.beginUpdate();
    added.forEach(function(r){ var c=Object.assign({},r); if(s.lists) listFields(c); s.dv.addItem(c); });
    s.dv.endUpdate();
    var entries=root.SRETMsImport.logEntries(res,{time:new Date().toISOString(),file:fileName,user:(typeof im.user==='function'?im.user():im.user)||'(not set)',assigned:assigned});
    if(im.log) Array.prototype.push.apply(im.log,entries);
    if(entries.length&&typeof im.onLog==='function') im.onLog(entries);
    if(s.lists) refreshLists(); else { s.grid.invalidate(); updateStatus(); }
    var lines=root.SRETMsImport.summary(res,assigned,S.opts.importer.noun);
    say(lines[0]);
    var ul=h('ul',{'class':'sg-import-summary','data-sg':'import-summary'});
    lines.forEach(function(l){ ul.appendChild(h('li',{text:l})); });
    var done=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'import-done',text:'Done',on:{click:function(){ ui.close(); }}});
    var logBtn=entries.length?h('button',{type:'button','class':'sg-btn','data-sg':'import-view-log',text:'View Import log',
      on:{click:function(){ ui.close(); openImportLog(); }}}):h('span');
    ui.pick.hidden=true;
    importPanel(ui,'done',[h('p',{'class':'sg-import-head',text:'Import complete'}),ul,h('div',{'class':'sg-confirm-btns'},[logBtn,done])]);
    done.focus();
  }
  function buildImport(body,close){
    var s=S, o=s.opts;
    var file=h('input',{type:'file',accept:'.xlsx,.xls,.csv','aria-label':'File to import','data-sg':'import-file'});
    var go=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'import-go',text:'Import',disabled:true});
    var tpl=h('button',{type:'button','class':'sg-link','data-sg':'import-template',text:'Download import template',on:{click:downloadTemplate}});
    var pick=h('div',{'class':'sg-import-pick'},[
      h('p',{text:'Choose a file made from the import template (.xlsx or .csv). Rows whose ID is already in the table are skipped; a blank ID is assigned for you.'}),
      h('div',{'class':'sg-import-row'},[file,go])]);
    var status=h('div',{'class':'sg-import-status','data-sg':'import-status'});
    body.appendChild(pick); body.appendChild(status);
    var ui={pick:pick,status:status,go:go,close:close};
    pick.appendChild(h('div',{'class':'sg-import-row'},[dateSelect(ui)]));
    pick.appendChild(h('div',{},[tpl]));
    s.importUi=ui;
    file.addEventListener('change',function(){ go.disabled=!file.files.length; importPanel(ui,'',[]); });
    go.addEventListener('click',function(){
      var f=file.files[0]; go.disabled=true;
      root.SRETMsImport.parseFile(f,o.ensureXLSX).then(function(aoa){ if(S===s) runImport(aoa,f.name,ui); })
        .catch(function(err){
          if(S!==s) return;
          var m=err&&err.message?err.message:'The file could not be read.';
          say('Import failed. '+m);
          importPanel(ui,'error',[h('p',{'class':'sg-import-head',text:'Import failed'}),h('p',{'data-sg':'import-error',text:m})]);
          ui.status.setAttribute('role','alert');
        }).then(function(){ if(S===s) go.disabled=!file.files.length; });
    });
    return function(){ if(s.importUi===ui) s.importUi=null; };
  }
  function fmtStamp(iso){
    var d=new Date(iso); if(isNaN(d)) return String(iso||'');
    var m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getMonth()];
    return d.getDate()+'-'+m+'-'+String(d.getFullYear()).slice(2)+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
  }
  function openImportLog(){
    var s=S, log=(s.opts.importer&&s.opts.importer.log)||[];
    openDialog('Import log',function(body){
      if(!log.length){ body.appendChild(h('p',{'data-sg':'import-log-empty',text:'No import issues logged yet.'})); return; }
      var t=h('table',{'class':'sg-itable','data-sg':'import-log-table'});
      t.appendChild(h('thead',{},[h('tr',{},['Time','File','User','ID','Note'].map(function(x){ return h('th',{text:x}); }))]));
      var b=h('tbody');
      log.slice().reverse().forEach(function(e){
        b.appendChild(h('tr',{},[fmtStamp(e.time),e.file,e.user,e.id,e.note].map(function(x){ return h('td',{text:x==null?'':String(x)}); })));
      });
      t.appendChild(b);
      body.appendChild(h('div',{'class':'sg-itable-wrap'},[t]));
    });
  }

  // ---------- health icon prefix, tap to edit (as the dashboard) ----------
  function hdot(icon,v){
    var o=(icon.options||[]).filter(function(x){ return String(x.value)===String(v==null?0:v); })[0]||{label:'N/A'};
    return '<button type="button" class="sg-hdot sg-h-'+esc(v==null?0:v)+'" tabindex="-1" data-sg-hdot="1" aria-label="'+
      esc(icon.label+': '+o.label+'. Change')+'" title="'+esc(icon.label+': '+o.label)+'"></button>';
  }
  function closeHealthPicker(){ var s=S; if(s&&s.hpick){ s.hpick.remove(); s.hpick=null; document.removeEventListener('mousedown',s.hpickOff,true); } }
  function openHealthPicker(btn,rowKey,col){
    var s=S; closeHealthPicker();
    var icon=col.icon, it=s.dv.getItemById(rowKey), cur=it?it[icon.key]:null;
    var pop=h('div',{'class':'sg-menu-pop sg-hpick',role:'menu','aria-label':icon.label,'data-sg':'health-picker'});
    (icon.options||[]).forEach(function(o){
      var b=h('button',{type:'button','class':'sg-menu-item',role:'menuitemradio','aria-checked':String(String(o.value)===String(cur==null?0:cur)),
                        tabindex:'-1','data-sg-health':String(o.value)},
              [h('span',{'class':'sg-hdot sg-h-'+o.value,'aria-hidden':'true'}),h('span',{text:o.label})]);
      b.addEventListener('click',function(e){ e.stopPropagation(); closeHealthPicker(); setIconValue(rowKey,icon.key,o.value); });
      pop.appendChild(b);
    });
    var r=btn.getBoundingClientRect(), sr=s.screen.getBoundingClientRect();
    pop.style.left=(r.left-sr.left)+'px'; pop.style.top=(r.bottom-sr.top+4)+'px';
    s.screen.appendChild(pop); s.hpick=pop;
    s.hpickOff=function(e){ if(!pop.contains(e.target)) closeHealthPicker(); };
    document.addEventListener('mousedown',s.hpickOff,true);
    pop.addEventListener('keydown',function(e){
      var its=Array.prototype.slice.call(pop.querySelectorAll('.sg-menu-item')), i=its.indexOf(document.activeElement);
      if(e.key==='ArrowDown'){ e.preventDefault(); its[(i+1)%its.length].focus(); }
      else if(e.key==='ArrowUp'){ e.preventDefault(); its[(i-1+its.length)%its.length].focus(); }
      else if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); closeHealthPicker(); s.grid.focus(); }
    });
    (pop.querySelector('[aria-checked=true]')||pop.firstChild).focus();
  }
  function setIconValue(rowKey,key,value){
    var s=S, it=s.dv.getItemById(rowKey); if(!it) return;
    var prev=it[key];
    var ret=typeof s.opts.onEdit==='function'?s.opts.onEdit(rowKey,key,value):undefined;
    if(ret===false){ say('That change was not accepted.'); return; }
    var c=Object.assign({},it); c[key]=value; if(s.lists) listFields(c);
    s.dv.updateItem(rowKey,c);
    if(prev!==value) say((s.colByKey[key]||{label:key}).label+' set to '+optLabel(s.colByKey[key]||{opts:[]},value)+' for '+rowKey+'.');
  }

  // Import template: the column headers the importer expects, no rows.
  function downloadTemplate(){
    var s=S, o=s.opts;
    if(typeof o.onTemplate==='function') return Promise.resolve(o.onTemplate());
    var loader=typeof o.ensureXLSX==='function'?o.ensureXLSX:function(){ return Promise.resolve(); };
    return Promise.resolve().then(loader).then(function(lib){
      var X=lib||root.XLSX;
      if(!X||!X.utils) throw new Error('The Excel library is not available.');
      var head=s.cols.filter(function(c){ return c.key.charAt(0)!=='_'; }).map(function(c){ return c.label; });
      var ws=X.utils.aoa_to_sheet([head]);
      var wb=X.utils.book_new();
      X.utils.book_append_sheet(wb,ws,'Import');
      var name=String(o.exportName||o.title||'Grid').replace(/[\\\/:*?"<>|]+/g,' ').trim()||'Grid';
      X.writeFile(wb,name+' import template.xlsx');
      say('Downloaded the import template ('+head.length+' columns).');
      return head;
    }).catch(function(err){ if(S) say(err&&err.message?err.message:'Download failed.'); });
  }

  // ---------- open / close ----------
  function open(opts){
    if(!root.Slick||!root.Slick.Grid||!root.Slick.Data) throw new Error('SRETGrid: grid library not loaded.');
    if(!opts||!opts.rowKey) throw new Error('SRETGrid.open: rowKey is required.');
    // A view switch replaces the screen but keeps where Back returns to.
    var carried=S&&S.switching?S.returnFocus:null;
    if(S) close(true);
    var rowKey=opts.rowKey;
    var cols=(opts.columns||[]).map(function(c){
      var type=TYPES[c.type]?c.type:'text';
      return {key:c.key,label:c.label==null?c.key:String(c.label),type:type,editable:!!c.editable,
              opts:normOptions(c.options),width:c.width||DEFAULT_WIDTH[type],min:c.min,max:c.max,options:c.options,
              hidden:!!c.hidden,tones:c.tones||null,
              icon:c.icon?{key:c.icon.key,label:c.icon.label||c.icon.key,options:normOptions(c.icon.options)}:null};
    });
    var gridEditable=!!opts.editable;
    var canAdd=gridEditable&&typeof opts.onAdd==='function';
    var canDel=gridEditable&&typeof opts.onDelete==='function';
    var lists=opts.lists&&opts.lists.store&&typeof opts.lists.refOf==='function'?opts.lists:null;
    if(lists&&!root.SRETCollections) throw new Error('SRETGrid.open: lists needs the SRETCollections module.');
    if(lists) cols=[{key:L_LIST,label:'List',type:'text',editable:false,opts:[],width:LIST_COL_W.collapsed}].concat(cols);
    var colByKey={}; cols.forEach(function(c){ colByKey[c.key]=c; });

    var host=opts.host||document.body;
    var fixed=host===document.body;
    var back=h('button',{type:'button','class':'sg-iconbtn sg-back','aria-label':'Back',title:'Back','data-sg':'back'});
    back.innerHTML=BACK_SVG;
    // Views (Matt, 2026-09-28): with more than one, the title is a menu that
    // switches between them (e.g. User milestones, Schedule milestones,
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
    var add=canAdd?h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'add',text:'Add row'}):null;
    // Delete selected rows: the same item in the Add row menu and in Tools.
    var deleteItem=function(){
      var sel=S?S.grid.getSelectedRows().length:0;
      return {label:'Delete selected rows…',sg:'delete',disabled:!sel,onSelect:function(){ if(lists&&S.panelMode) openPanel(S.panelMode); showConfirm(); }};
    };
    // Add row is a split button (Matt, 2026-09-28): Delete selected rows,
    // then export and the template, then import, each group set apart by a
    // separator. Screens that cannot add rows keep a plain Export button.
    var addMenu=canAdd?makeMenu('More add options','add-more',function(){
      var imp=opts.importer||typeof opts.onImport==='function';
      return [canDel?deleteItem():null, canDel?{sep:1}:null,
              {label:'Export .xlsx',sg:'export',onSelect:exportRows},
              {label:'Download import template',sg:'template',onSelect:downloadTemplate},
              imp?{sep:1}:null,
              imp?{label:importTitle()+'…',sg:'import',onSelect:openImport}:null,
              opts.importer?{label:'Import log',sg:'import-log',onSelect:openImportLog}:null];
    },'sg-btn--primary',add):null;
    var exp=canAdd?null:h('button',{type:'button','class':'sg-btn','data-sg':'export',text:'Export .xlsx'});
    var selAll=h('button',{type:'button','class':'sg-link','data-sg':'select-all',text:'Select all'});
    var tmpAdd=lists?h('button',{type:'button','class':'sg-btn','data-sg':'temp-add',disabled:true,
                                 title:'Add the selected rows to My temp list'},
                                [h('span',{'class':'sg-tempmark','aria-hidden':'true'}),h('span',{text:'Add to temp list'})]):null;
    var tmpMenu=lists?makeMenu('More temp list options','temp-add-more',function(){
      var st=lists.store, sel=selectedRefs(), selTemp=sel.filter(function(r){ return M().inTemp(st,r); }).length;
      var ls=M().list(st), it=[
        {label:'Remove selected from My temp list',sg:'temp-remove-rows',disabled:!selTemp,
         onSelect:function(){ listsDone(M().tempRemove(st,selectedRefs())); }},{sep:1}];
      if(!ls.length) it.push({label:'Add to list: no saved lists yet',sg:'add-to-list-none',disabled:true,onSelect:function(){}});
      ls.forEach(function(c){ it.push({label:'Add to "'+c.label+'"',sg:'add-to-list',list:c.id,disabled:!sel.length,
        onSelect:function(){ listsDone(M().assign(st,c.id,selectedRefs())); }}); });
      it.push({sep:1});
      it.push({label:'Show only My temp list',sg:'temp-only',checked:scopeIs('temp'),
               onSelect:function(){ setScope(scopeIs('temp')?null:{type:'temp'}); }});
      return it;
    },null,tmpAdd):null;
    var pillText=h('span');
    var pill=lists?h('button',{type:'button','class':'sg-pill','data-sg':'scope-pill',hidden:true,
                               title:'Click to show all rows'},[pillText,h('span',{'aria-hidden':'true',text:' ✕'})]):null;
    var toolsItems=function(){
      var it=[];
      if(lists) it.push({label:'Expand the List column',sg:'list-col',checked:!!(S&&S.listExpanded),onSelect:toggleListCol});
      if(canDel){
        if(it.length) it.push({sep:1});
        it.push(deleteItem());
      }
      if((opts.toolsItems||[]).length){
        if(it.length) it.push({sep:1});
        opts.toolsItems.forEach(function(x){ it.push({label:x.label,sg:x.sg,onSelect:x.onSelect}); });
      }
      return it;
    };
    var tools=(lists||canDel||(opts.toolsItems||[]).length)?makeMenu('Tools','tools',toolsItems):null;
    var msg=h('span',{'class':'sg-msg',role:'status','aria-live':'polite','data-sg':'msg'});
    // Row 1: back, title. Row 2 (starts in line with the title): search, Add
    // row, Tools, Add to temp list. Row 3: counts, Select all, the filter pill.
    var bar=h('div',{'class':'sg-bar'},[h('div',{'class':'sg-bar-lead'},[back,title])]);
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
    var bar2=h('div',{'class':'sg-bar2'},[search].concat(pickers.map(function(m){ return m.wrap; })).concat([addMenu?addMenu.wrap:exp,tools&&tools.wrap,tmpMenu&&tmpMenu.wrap]));
    var bar3=h('div',{'class':'sg-bar3'},[h('span',{'class':'sg-counts'},[count,selc]),selAll,pill,note]);
    var confirm=h('div',{'class':'sg-confirm',role:'alertdialog','aria-label':'Confirm remove','data-sg':'confirm',hidden:true});
    var tmpCount=lists?h('span',{'class':'sg-badge sg-rail-badge','data-sg':'temp-count',text:'0',hidden:true}):null;
    var railTemp=lists?h('button',{type:'button','class':'sg-rail-btn','data-sg':'temp-open','aria-expanded':'false',
                                   'aria-controls':'sg-panel','aria-label':'My temp list',title:'My temp list (this session only)'},
                                  [h('span',{'class':'sg-tempmark sg-tempmark--rail','aria-hidden':'true'}),tmpCount]):null;
    var railLists=lists?h('button',{type:'button','class':'sg-rail-btn','data-sg':'lists-open','aria-expanded':'false',
                                    'aria-controls':'sg-panel','aria-label':'Saved lists',title:'Saved lists'}):null;
    if(railLists) railLists.innerHTML=LIST_SVG;
    var rail=lists?h('nav',{'class':'sg-rail','aria-label':'Panels'},[railTemp,railLists]):null;
    var panel=lists?h('aside',{'class':'sg-temp',id:'sg-panel','aria-label':'My temp list','data-sg':'panel',hidden:true}):null;
    var gridEl=h('div',{'class':'sg-grid','data-sg':'grid'});
    var body=h('div',{'class':'sg-body'},[rail,panel,gridEl]);
    var screen=h('section',{'class':'sg-screen'+(fixed?' sg-screen--fixed':''),role:'region','aria-label':opts.title||'Table'},
                 [bar,bar2,bar3,confirm,body,msg]);
    host.appendChild(screen);

    var rowH=ctlHeight(screen);
    var dv=new root.Slick.Data.DataView({inlineFilters:false});
    var check=new root.Slick.CheckboxSelectColumn({cssClass:'sg-check',width:32,hideInFilterHeaderRow:true});
    var checkDef=check.getColumnDefinition();
    checkDef.headerCssClass='sg-check-h';
    var colDefs=cols.filter(function(c){ return !c.hidden; }).map(function(c){
      var ed=gridEditable&&c.editable;
      if(c.key===L_LIST) return {id:c.key,field:c.key,name:listColName(),toolTip:'Saved lists this row is in',width:c.width,minWidth:c.width,
              sortable:true,resizable:true,sg:c,editor:null,cssClass:'sg-cell-ro sg-lcol',headerCssClass:'sg-lcol-h',formatter:listColFormatter};
      var cls=(ed?'sg-cell-edit':'sg-cell-ro')+(c.key===opts.openColumn?' sg-cell-open':'');
      return {id:c.key,field:c.key,name:esc(c.label),toolTip:c.key===opts.openColumn?c.label+' (double-click to open)':c.label,
              width:c.width,minWidth:48,sortable:true,resizable:true,
              sg:c,editor:ed?Editor:null,cssClass:cls,headerCssClass:ed?'sg-h-edit':null,formatter:cellFormatter};
    });
    // The List column sits left of the checkbox (Matt, 2026-09-27).
    var slickCols=colDefs.filter(function(d){ return d.id===L_LIST; }).concat([checkDef],colDefs.filter(function(d){ return d.id!==L_LIST; }));
    var grid=new root.Slick.Grid(gridEl,dv,slickCols,{
      editable:gridEditable,autoEdit:false,enableCellNavigation:true,asyncEditorLoading:false,
      enableColumnReorder:false,rowHeight:rowH,headerRowHeight:rowH+8,showHeaderRow:true,
      explicitInitialization:true,forceFitColumns:false,multiColumnSort:false,
      editorCellNavOnLRKeys:false,enableTextSelectionOnCells:true,
      // Scroll smoothness (measured in tools/grid_view_check.py). The engine's
      // own wheel handler exists for frozen columns, which we do not use; left
      // on, it moves scrollTop in whole-row steps against the browser's native
      // scroll, and the two fight on every wheel tick. Sync rendering stops a
      // fast scroll showing blank rows for a frame while the throttle waits,
      // transforms keep row moves on the compositor, and the larger buffer
      // keeps rows ready just outside the viewport.
      enableMouseWheelScrollHandler:false,forceSyncScrolling:true,
      rowTopOffsetRenderType:'transform',minRowBuffer:10
    });
    grid.setSelectionModel(new root.Slick.RowSelectionModel({selectActiveRow:false}));
    grid.registerPlugin(check);

    S={opts:opts,rowKey:rowKey,cols:cols,colByKey:colByKey,filters:{},quick:'',grid:grid,dv:dv,
       screen:screen,host:host,countEl:count,selEl:selc,msgEl:msg,expBtn:exp,searchEl:search,selAllBtn:selAll,tools:tools,openMenu:null,
       confirmEl:confirm,prev:null,returnFocus:carried||document.activeElement,ro:null,viewMenu:viewMenu,
       lists:lists,scope:null,listExpanded:false,tmpAddBtn:tmpAdd,tmpCount:tmpCount,railTemp:railTemp,railLists:railLists,
       pill:pill,pillText:pillText,panel:panel,panelMode:null,dialog:null,msgTimer:0};
    if(lists) buildPanel();
    cols.forEach(function(c){ S.filters[c.key]=''; });

    grid.onHeaderRowCellRendered.subscribe(function(e,args){
      var c=args.column.sg; args.node.innerHTML='';
      if(!c||(c.key===L_LIST&&!S.listExpanded)) return;
      var ops=c.type==='number'||c.type==='date';
      var inp=h('input',{type:'text','class':'sg-hfilter',placeholder:'Filter','aria-label':'Filter '+c.label,'data-sg-filter':c.key,
        title:ops?'Contains, or compare with >, <, >=, <=, = (e.g. >=75'+(c.type==='date'?' or <1-Oct-26':'')+')':'Contains'});
      inp.value=S.filters[c.key]||'';
      inp.addEventListener('input',function(){ S.filters[c.key]=inp.value; dv.refresh(); });
      inp.addEventListener('keydown',function(ev){ ev.stopPropagation(); });
      args.node.appendChild(inp);
    });
    grid.onHeaderCellRendered.subscribe(function(e,args){
      if(args.column.id!==L_LIST) return;
      var b=args.node.querySelector('.sg-lcol-toggle');
      // Its own handler, so a click on the arrow toggles and never sorts.
      if(b) b.addEventListener('click',function(ev){ ev.stopPropagation(); toggleListCol(); });
    });
    grid.onSort.subscribe(function(e,args){
      var c=args.sortCol.sg; if(!c) return;
      dv.sort(comparer(c.key,c),args.sortAsc);
    });
    grid.onBeforeEditCell.subscribe(function(e,args){
      var c=args.column&&args.column.sg;
      if(!gridEditable||!c||!c.editable) return false;
      if(typeof opts.canEdit==='function' && opts.canEdit(args.item[rowKey],c.key)===false){
        say('This value comes from the schedule and cannot be edited here.');
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
    grid.onClick.subscribe(function(e,args){
      var ne=e&&e.getNativeEvent?e.getNativeEvent():e, t=ne&&ne.target;
      var b=t&&t.closest&&t.closest('[data-sg-hdot]'); if(!b) return;
      var c=grid.getColumns()[args.cell], it=dv.getItem(args.row);
      if(!c||!c.sg||!c.sg.icon||!it) return;
      if(e.stopImmediatePropagation) e.stopImmediatePropagation();
      if(!gridEditable){ say('This view is read only.'); return; }
      openHealthPicker(b,it[rowKey],c.sg);
    });
    grid.onDblClick.subscribe(function(e,args){
      var c=grid.getColumns()[args.cell], it=dv.getItem(args.row);
      if(c&&c.id===opts.openColumn&&it&&typeof opts.onOpenItem==='function') opts.onOpenItem(it[rowKey]);
    });
    grid.onSelectedRowsChanged.subscribe(updateStatus);
    dv.onRowCountChanged.subscribe(function(){ grid.updateRowCount(); grid.render(); updateStatus(); });
    dv.onRowsChanged.subscribe(function(e,args){ grid.invalidateRows(args.rows); grid.render(); });

    // Rows on My temp list carry a class; CSS draws the vertical line left of the checkbox.
    if(lists){
      var baseMeta=dv.getItemMetadata.bind(dv);
      dv.getItemMetadata=function(i){
        var m=baseMeta(i), it=dv.getItem(i);
        if(it&&it[L_TMP]==='Yes'){ m=Object.assign({},m||{}); m.cssClasses=((m.cssClasses||'')+' sg-in-temp').trim(); }
        return m;
      };
    }
    grid.init();
    dv.beginUpdate();
    dv.setItems((opts.rows||[]).map(function(r){ return Object.assign({},r); }),rowKey);
    dv.setFilter(rowPasses);
    dv.endUpdate();
    dv.syncGridSelection(grid,false);
    if(lists) refreshLists();

    back.addEventListener('click',function(){ var cb=opts.onBack; close(); if(typeof cb==='function') cb(); });
    search.addEventListener('input',function(){ S.quick=search.value; dv.refresh(); });
    if(exp) exp.addEventListener('click',exportRows);
    if(add) add.addEventListener('click',doAdd);
    selAll.addEventListener('click',function(){
      var n=dv.getLength(), all=n&&grid.getSelectedRows().length===n, rows=[];
      if(!all) for(var i=0;i<n;i++) rows.push(i);
      grid.setSelectedRows(rows);
    });
    if(lists){
      tmpAdd.addEventListener('click',function(){ listsDone(M().tempAdd(lists.store,selectedRefs())); });
      railTemp.addEventListener('click',function(){ openPanel('temp'); });
      railLists.addEventListener('click',function(){ openPanel('list'); });
      pill.addEventListener('click',function(){ setScope(null); });
    }
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
        pending=false; grid.resizeCanvas();
      };
      // A timer, not requestAnimationFrame: it still runs outside the observer
      // callback, and it fires even when no frame is being drawn.
      var schedule=function(){ if(timer) root.clearTimeout(timer); timer=root.setTimeout(doResize,0); };
      grid.onBeforeCellEditorDestroy.subscribe(function(){ if(pending) schedule(); });
      S.requestResize=schedule;
      S.ro=new root.ResizeObserver(function(entries){
        var r=entries[0]&&entries[0].contentRect; if(!r||(r.width===lastW&&r.height===lastH)) return;
        lastW=r.width; lastH=r.height;
        schedule();
      });
      S.ro.observe(gridEl);
    }
    updateStatus();
    if(dv.getLength()) grid.setActiveCell(0,firstDataCell());
    if(carried&&viewMenu) viewMenu.btn.focus();
    return api;
  }

  function close(silent){
    var s=S; if(!s) return;
    if(s.openMenu) s.openMenu.close(false);
    if(s.dialog) s.dialog.close();
    if(s.hpick){ s.hpick.remove(); document.removeEventListener('mousedown',s.hpickOff,true); }
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
    if(s.lists) refreshLists(); else { s.grid.invalidate(); updateStatus(); }
  }

  var api={
    open:open,
    close:function(){ close(); },
    isOpen:function(){ return !!S; },
    setRows:setRows,
    patchRows:patchRows,
    exportVisible:function(){ return S?exportRows():Promise.resolve(null); },
    // A centred modal dialog on the open screen; build(body, close) may return a cleanup.
    dialog:function(title,build){ return S?openDialog(title,build):null; },
    // Reopen the screen with a new config (e.g. after the caller's data
    // changed) keeping where Back returns to.
    refresh:function(o){ if(S) S.switching=true; return open(o); },
    // For the app's own import form: hand in the parsed sheet, and the grid
    // runs the same checks, question, log and summary in its dialog.
    importAoa:function(aoa,fileName){
      if(!S||!S.opts.importer) return null;
      openDialog(importTitle(),function(body,close){
        var ui={pick:h('div'),status:h('div',{'class':'sg-import-status','data-sg':'import-status'}),go:h('button'),close:close,onCancel:close};
        body.appendChild(h('div',{'class':'sg-import-row'},[dateSelect(ui)])); body.appendChild(ui.status);
        runImport(aoa,fileName||'Imported sheet',ui);
      });
      return true;
    },
    // Test hook only: the engine objects of the open screen.
    // requestResize is the exact path a ResizeObserver report takes.
    _engine:function(){ return S?{grid:S.grid,dataView:S.dv,requestResize:S.requestResize}:null; },
    _fmtDate:fmtDate
  };
  root.SRETGrid=api;
})(window);
