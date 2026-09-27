/* =====================================================================
   SRET grid view (D-09). One full-screen table view, three uses:
   annotation collections, user-defined milestones, schedule activities.

   Contract (docs/grid-view-integration.md):
     SRETGrid.open({
       title, columns:[{key,label,type,editable,options,width}], rows, rowKey,
       editable, onEdit(rowKey,key,value), onAdd(), onDelete(rowKeys),
       onBack(), exportName, ensureXLSX, host, canEdit(rowKey,key),
       lists:{ store, refOf(rowKey), labelOf(ref), onChange(result) }
     })
     SRETGrid.close()   SRETGrid.setRows(rows)   SRETGrid.patchRows(rows)   SRETGrid.isOpen()
   Return false from onEdit to refuse a value (the cell reverts), from
   onDelete to keep the rows. onAdd returns the new row object (with its
   rowKey) or nothing to add no row. canEdit, optional, refuses an edit on
   one row where the column is otherwise editable.
   lists, optional, adds My temp list: "Add to temp list" for the selected
   rows, a "Temp list only" filter, and an expandable panel listing the temp
   items, where selected items are added to a saved list (existing or new),
   removed from the temp list, or the temp list is cleared. It also adds
   read-only List and Temp columns. store is the caller's SRETCollections
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
    if(s.tempOnly && item[L_TMP]!=='Yes') return false;
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
  function makeMenu(label,sg,getItems,extraClass){
    var btn=h('button',{type:'button','class':'sg-btn sg-btn--menu'+(extraClass?' '+extraClass:''),'aria-haspopup':'menu',
                        'aria-expanded':'false','data-sg':sg},[h('span',{text:label})]);
    var chev=h('span',{'class':'sg-chev'}); chev.innerHTML=CHEVRON; btn.appendChild(chev);
    var pop=h('div',{'class':'sg-menu-pop',role:'menu','aria-label':label,'data-sg':sg+'-menu',hidden:true});
    var wrap=h('span',{'class':'sg-menu'},[btn,pop]);
    var m={btn:btn,pop:pop,wrap:wrap};
    function enabled(){ return Array.prototype.slice.call(pop.querySelectorAll('.sg-menu-item:not([disabled])')); }
    function render(){
      pop.innerHTML='';
      getItems().forEach(function(it){
        if(!it) return;
        if(it.sep){ pop.appendChild(h('div',{'class':'sg-menu-sep',role:'separator'})); return; }
        var box=it.checked!=null;
        var b=h('button',{type:'button','class':'sg-menu-item',role:box?'menuitemcheckbox':'menuitem',tabindex:'-1',
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
  //   2. open the My temp list panel, select items in it, Add to list
  //   3. Remove selected items from the temp list
  //   4. Clear the temp list (More menu)
  // Layout (Matt, 2026-09-27, after the Aconex register): a vertical panel
  // docked left, opened from the rail, with only the core buttons showing.
  var L_TMP='_tmp', L_LIST='_list';
  function M(){ return root.SRETCollections; }
  function listFields(item){
    var s=S, ref=s.lists.refOf(item[s.rowKey]);
    item[L_TMP]=M().inTemp(s.lists.store,ref)?'Yes':'';
    item[L_LIST]=M().membership(s.lists.store,ref).join(', ');
  }
  // Items are the grid's own copies, so the two derived fields are written
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
  function pickedRefs(){ var s=S; return M().temp(s.lists.store).filter(function(r){ return s.tmpPicked[r]; }); }
  function labelOf(ref){
    var s=S;
    if(typeof s.lists.labelOf==='function'){ var l=s.lists.labelOf(ref); if(l) return String(l); }
    return String(ref).replace(/^[^:]*:/,'');
  }
  function listsDone(r){
    var s=S;
    say(M().describe(r));
    s.tmpErr.textContent=r.error?M().describe(r):'';
    if(!r.error && typeof s.lists.onChange==='function') s.lists.onChange(r);
    refreshLists();
    return r;
  }
  function setTempOnly(on){
    var s=S; s.tempOnly=!!on; s.dv.refresh(); updateStatus();
  }
  // Button states only; never rebuilds the item list, so it is safe to call
  // from a checkbox's own change handler.
  function updateTempButtons(){
    var s=S; if(!s||!s.lists) return;
    var tmp=M().temp(s.lists.store), picked=pickedRefs().length;
    s.tmpAllBox.checked=!!tmp.length&&picked===tmp.length;
    s.tmpAllBox.indeterminate=picked>0&&picked<tmp.length;
    s.tmpAllBox.disabled=!tmp.length;
    s.tmpPickedEl.textContent=picked?'('+picked+' selected)':'';
    s.tmpAddMenu.btn.disabled=!picked;
    s.tmpRemove.disabled=!picked;
  }
  function renderTempItems(){
    var s=S, st=s.lists.store, tmp=M().temp(st);
    Object.keys(s.tmpPicked).forEach(function(r){ if(tmp.indexOf(r)<0) delete s.tmpPicked[r]; });
    s.tmpItems.innerHTML='';
    if(!tmp.length){
      s.tmpItems.appendChild(h('li',{'class':'sg-temp-empty',text:'Empty. Select rows in the table and use Add to temp list.'}));
    }
    tmp.forEach(function(r){
      var box=h('input',{type:'checkbox','data-sg-temp-item':r,'aria-label':'Select '+labelOf(r)});
      box.checked=!!s.tmpPicked[r];
      box.addEventListener('change',function(){ if(box.checked) s.tmpPicked[r]=1; else delete s.tmpPicked[r]; updateTempButtons(); });
      var ls=M().membership(st,r);
      s.tmpItems.appendChild(h('li',{'class':'sg-temp-item'},[
        h('label',{'class':'sg-temp-item-lbl'},[box,h('span',{'class':'sg-temp-item-text'},[
          h('span',{'class':'sg-temp-item-name',text:labelOf(r)}),
          h('span',{'class':'sg-temp-item-lists',text:ls.length?ls.join(', '):'No list'})])])
      ]));
    });
    var here=s.dv.getItems().filter(function(it){ return it[L_TMP]==='Yes'; }).length;
    s.tmpSummary.textContent=tmp.length+(tmp.length===1?' item':' items')+(tmp.length?', '+here+' on this screen':'');
    updateTempButtons();
  }
  // A control that sets state also shows it: badge, expanded state, the
  // filter pill and enabled buttons all follow the store on every change.
  function updateLists(){
    var s=S; if(!s||!s.lists) return;
    var n=M().temp(s.lists.store).length, sel=s.grid.getSelectedRows().length;
    s.tmpAddBtn.disabled=!sel;
    s.tmpBtnCount.textContent=String(n);
    s.tmpBtnCount.hidden=!n;
    s.tmpBtn.setAttribute('aria-expanded',String(!s.tmpPanel.hidden));
    s.tmpBtn.classList.toggle('is-open',!s.tmpPanel.hidden);
    s.tmpOnlyPill.hidden=!s.tempOnly;
    if(!s.tmpPanel.hidden) renderTempItems();
  }
  function toggleTempPanel(show){
    var s=S; if(show==null) show=s.tmpPanel.hidden;
    if(show) hideConfirm();
    hideTempForms();
    s.tmpPanel.hidden=!show; s.tmpErr.textContent='';
    updateLists();
    if(show) s.tmpAllBox.focus(); else s.tmpBtn.focus();
  }
  function hideTempForms(){
    var s=S;
    s.tmpConfirm.hidden=true; s.tmpConfirm.innerHTML='';
    s.tmpNewForm.hidden=true; s.tmpName.value='';
    s.tmpFoot.hidden=false;
  }
  function showNewList(){
    var s=S; if(!pickedRefs().length) return;
    hideTempForms(); s.tmpFoot.hidden=true; s.tmpNewForm.hidden=false; s.tmpErr.textContent='';
    s.tmpName.focus();
  }
  function saveNewList(){
    var s=S, r=listsDone(M().saveFromTemp(s.lists.store,s.tmpName.value,pickedRefs()));
    if(r.error){ s.tmpName.focus(); return; }
    hideTempForms(); s.tmpAddMenu.btn.focus();
  }
  function showTempConfirm(){
    var s=S, n=M().temp(s.lists.store).length; if(!n) return;
    hideTempForms();
    var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hideTempForms(); s.tmpMore.btn.focus(); }}});
    var go=h('button',{type:'button','class':'sg-btn sg-btn--danger','data-sg':'temp-clear-confirm',text:'Clear',
      on:{click:function(){ hideTempForms(); listsDone(M().tempClear(s.lists.store)); s.tmpAllBox.focus(); }}});
    s.tmpConfirm.appendChild(h('p',{'class':'sg-confirm-msg',
      text:'Clear My temp list ('+n+(n===1?' item':' items')+')? Saved lists are not changed.'}));
    s.tmpConfirm.appendChild(h('div',{'class':'sg-confirm-btns'},[cancel,go]));
    s.tmpFoot.hidden=true; s.tmpConfirm.hidden=false;
    cancel.focus();
  }
  function buildTempPanel(){
    var s=S;
    s.tmpPicked={};
    s.tmpAllBox=h('input',{type:'checkbox','data-sg':'temp-all','aria-label':'Select all items on My temp list'});
    s.tmpSummary=h('span',{'class':'sg-temp-summary','data-sg':'temp-summary'});
    s.tmpPickedEl=h('span',{'class':'sg-selcount','data-sg':'temp-picked'});
    s.tmpItems=h('ul',{'class':'sg-temp-items','data-sg':'temp-items','aria-label':'Items on My temp list'});
    s.tmpErr=h('p',{'class':'sg-temp-err',role:'alert','data-sg':'temp-err'});
    s.tmpConfirm=h('div',{'class':'sg-temp-confirm','data-sg':'temp-confirm',hidden:true});
    // New list: a small inline form, same layout as the inline confirmation.
    s.tmpName=h('input',{type:'text','class':'sg-search sg-temp-name','aria-label':'Name for the new list',
                         placeholder:'New list name','data-sg':'temp-name',maxlength:'60'});
    var nCancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hideTempForms(); s.tmpAddMenu.btn.focus(); }}});
    var nSave=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'temp-newlist-save',text:'Save list',on:{click:saveNewList}});
    s.tmpNewForm=h('div',{'class':'sg-temp-form','data-sg':'temp-newlist-form',hidden:true},[
      h('p',{'class':'sg-temp-form-lbl',text:'Save the selected items as a new list'}),s.tmpName,
      h('div',{'class':'sg-confirm-btns'},[nCancel,nSave])]);
    s.tmpName.addEventListener('keydown',function(e){
      if(e.key==='Enter'){ e.preventDefault(); saveNewList(); }
      else if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); hideTempForms(); s.tmpAddMenu.btn.focus(); }
    });
    // Core buttons: Add to list, Remove. Everything else is under More.
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
      return [{label:'Show only these rows in the table',sg:'temp-only-panel',checked:!!s.tempOnly,onSelect:function(){ setTempOnly(!s.tempOnly); }},
              {sep:1},
              {label:'Clear temp list…',sg:'temp-clear',disabled:!M().temp(s.lists.store).length,onSelect:showTempConfirm}];
    });
    s.tmpFoot=h('div',{'class':'sg-temp-foot'},[s.tmpAddMenu.wrap,s.tmpRemove,h('span',{'class':'sg-spacer'}),s.tmpMore.wrap]);
    var close=h('button',{type:'button','class':'sg-iconbtn','aria-label':'Collapse My temp list',title:'Collapse','data-sg':'temp-close',text:'✕'});
    s.tmpPanel.appendChild(h('div',{'class':'sg-temp-head'},[
      h('h3',{'class':'sg-temp-title',text:'My temp list'}),h('span',{'class':'sg-spacer'}),close]));
    s.tmpPanel.appendChild(h('div',{'class':'sg-temp-sub'},[
      h('label',{'class':'sg-temp-all'},[s.tmpAllBox,s.tmpSummary]),s.tmpPickedEl]));
    s.tmpPanel.appendChild(s.tmpItems);
    s.tmpPanel.appendChild(s.tmpNewForm);
    s.tmpPanel.appendChild(s.tmpConfirm);
    s.tmpPanel.appendChild(s.tmpErr);
    s.tmpPanel.appendChild(s.tmpFoot);
    s.tmpAllBox.addEventListener('change',function(){
      var on=s.tmpAllBox.checked;
      s.tmpPicked={}; if(on) M().temp(s.lists.store).forEach(function(r){ s.tmpPicked[r]=1; });
      s.tmpItems.querySelectorAll('input[type=checkbox]').forEach(function(b){ b.checked=on; });
      updateTempButtons();
    });
    s.tmpRemove.addEventListener('click',function(){ listsDone(M().tempRemove(s.lists.store,pickedRefs())); });
    close.addEventListener('click',function(){ toggleTempPanel(false); });
    s.tmpPanel.addEventListener('keydown',function(e){
      if(e.key!=='Escape') return;
      e.preventDefault(); e.stopPropagation();
      if(!s.tmpConfirm.hidden||!s.tmpNewForm.hidden){ hideTempForms(); s.tmpAddMenu.btn.focus(); } else toggleTempPanel(false);
    });
  }

  // ---------- export ----------
  function exportRows(){
    var s=S, o=s.opts;
    var loader=typeof o.ensureXLSX==='function'?o.ensureXLSX:function(){ return Promise.resolve(); };
    s.expBtn.disabled=true;
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
    }).then(function(r){ if(S) S.expBtn.disabled=false; return r; });
  }

  // ---------- open / close ----------
  function open(opts){
    if(!root.Slick||!root.Slick.Grid||!root.Slick.Data) throw new Error('SRETGrid: grid library not loaded.');
    if(!opts||!opts.rowKey) throw new Error('SRETGrid.open: rowKey is required.');
    if(S) close(true);
    var rowKey=opts.rowKey;
    var cols=(opts.columns||[]).map(function(c){
      var type=TYPES[c.type]?c.type:'text';
      return {key:c.key,label:c.label==null?c.key:String(c.label),type:type,editable:!!c.editable,
              opts:normOptions(c.options),width:c.width||DEFAULT_WIDTH[type]};
    });
    var gridEditable=!!opts.editable;
    var canAdd=gridEditable&&typeof opts.onAdd==='function';
    var canDel=gridEditable&&typeof opts.onDelete==='function';
    var lists=opts.lists&&opts.lists.store&&typeof opts.lists.refOf==='function'?opts.lists:null;
    if(lists&&!root.SRETCollections) throw new Error('SRETGrid.open: lists needs the SRETCollections module.');
    if(lists) cols=[{key:L_LIST,label:'List',type:'text',editable:false,opts:[],width:140},
                    {key:L_TMP,label:'Temp',type:'text',editable:false,opts:[],width:64}].concat(cols);
    var colByKey={}; cols.forEach(function(c){ colByKey[c.key]=c; });

    var host=opts.host||document.body;
    var fixed=host===document.body;
    var back=h('button',{type:'button','class':'sg-iconbtn sg-back','aria-label':'Back',title:'Back','data-sg':'back'});
    back.innerHTML=BACK_SVG;
    var title=h('h2',{'class':'sg-title',text:opts.title||'Table'});
    var search=h('input',{type:'search','class':'sg-search',placeholder:'Search','aria-label':'Search all columns','data-sg':'search'});
    var count=h('span',{'class':'sg-count','data-sg':'count'});
    var selc=h('span',{'class':'sg-selcount','data-sg':'selcount'});
    var exp=h('button',{type:'button','class':'sg-btn','data-sg':'export',text:'Export .xlsx'});
    var add=canAdd?h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'add',text:'Add row'}):null;
    var selAll=h('button',{type:'button','class':'sg-link','data-sg':'select-all',text:'Select all'});
    var tmpAdd=lists?h('button',{type:'button','class':'sg-btn','data-sg':'temp-add',text:'Add to temp list',disabled:true,
                                 title:'Add the selected rows to My temp list'}):null;
    var tmpOnlyPill=lists?h('button',{type:'button','class':'sg-pill','data-sg':'temp-only-pill',hidden:true,
                                      title:'Showing only rows on My temp list. Click to show all rows.'},
                                     [h('span',{text:'Temp list only'}),h('span',{'aria-hidden':'true',text:' ✕'})]):null;
    var toolsItems=function(){
      var st=lists&&lists.store, sel=S?S.grid.getSelectedRows().length:0;
      var selTemp=lists&&S?selectedRefs().filter(function(r){ return M().inTemp(st,r); }).length:0;
      var it=[];
      if(lists){
        it.push({label:'Show only rows on My temp list',sg:'temp-only',checked:!!(S&&S.tempOnly),onSelect:function(){ setTempOnly(!S.tempOnly); }});
        it.push({label:'Remove selected rows from My temp list',sg:'temp-remove-rows',disabled:!selTemp,
                 onSelect:function(){ listsDone(M().tempRemove(st,selectedRefs())); }});
      }
      if(canDel){
        if(it.length) it.push({sep:1});
        it.push({label:'Delete selected rows…',sg:'delete',disabled:!sel,onSelect:function(){ if(lists) toggleTempPanel(false); showConfirm(); }});
      }
      return it;
    };
    var tools=(lists||canDel)?makeMenu('Tools','tools',toolsItems):null;
    var msg=h('span',{'class':'sg-msg',role:'status','aria-live':'polite','data-sg':'msg'});
    // Row 1: back, title; Export anchored right. Row 2: search, counts, core
    // actions and Tools; Add row anchored right (Matt, 2026-09-27).
    var bar=h('div',{'class':'sg-bar'},[
      h('div',{'class':'sg-bar-lead'},[back,title]),h('span',{'class':'sg-spacer'}),exp]);
    var bar2=h('div',{'class':'sg-bar2'},[
      search,h('span',{'class':'sg-counts'},[count,selc]),selAll,tmpAdd,tools&&tools.wrap,tmpOnlyPill,
      h('span',{'class':'sg-spacer'}),add]);
    var confirm=h('div',{'class':'sg-confirm',role:'alertdialog','aria-label':'Confirm remove','data-sg':'confirm',hidden:true});
    var tmpBtnCount=lists?h('span',{'class':'sg-badge sg-rail-badge','data-sg':'temp-count',text:'0',hidden:true}):null;
    var tmpBtn=lists?h('button',{type:'button','class':'sg-rail-btn','data-sg':'temp-open','aria-expanded':'false',
                                 'aria-controls':'sg-temp-panel','aria-label':'My temp list',title:'My temp list'}):null;
    if(tmpBtn){ tmpBtn.innerHTML=LIST_SVG; tmpBtn.appendChild(tmpBtnCount); }
    var rail=lists?h('nav',{'class':'sg-rail','aria-label':'Panels'},[tmpBtn]):null;
    var tmpPanel=lists?h('aside',{'class':'sg-temp',id:'sg-temp-panel','aria-label':'My temp list','data-sg':'temp-panel',hidden:true}):null;
    var gridEl=h('div',{'class':'sg-grid','data-sg':'grid'});
    var body=h('div',{'class':'sg-body'},[rail,tmpPanel,gridEl]);
    var screen=h('section',{'class':'sg-screen'+(fixed?' sg-screen--fixed':''),role:'region','aria-label':opts.title||'Table'},
                 [bar,bar2,confirm,body,msg]);
    host.appendChild(screen);

    var rowH=ctlHeight(screen);
    var dv=new root.Slick.Data.DataView({inlineFilters:false});
    var check=new root.Slick.CheckboxSelectColumn({cssClass:'sg-check',width:32,hideInFilterHeaderRow:true});
    var checkDef=check.getColumnDefinition();
    checkDef.headerCssClass='sg-check-h';
    var slickCols=[checkDef].concat(cols.map(function(c){
      var ed=gridEditable&&c.editable;
      return {id:c.key,field:c.key,name:esc(c.label),toolTip:c.label,width:c.width,minWidth:48,sortable:true,resizable:true,
              sg:c,editor:ed?Editor:null,cssClass:ed?'sg-cell-edit':'sg-cell-ro',headerCssClass:ed?'sg-h-edit':null,
              formatter:function(r,cell,v,colDef){ return esc(display(colDef.sg,v)); }};
    }));
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
       confirmEl:confirm,prev:null,returnFocus:document.activeElement,ro:null,
       lists:lists,tempOnly:false,tmpAddBtn:tmpAdd,tmpBtn:tmpBtn,tmpBtnCount:tmpBtnCount,tmpOnlyPill:tmpOnlyPill,tmpPanel:tmpPanel,msgTimer:0};
    if(lists) buildTempPanel();
    cols.forEach(function(c){ S.filters[c.key]=''; });

    grid.onHeaderRowCellRendered.subscribe(function(e,args){
      var c=args.column.sg; args.node.innerHTML='';
      if(!c) return;
      var ops=c.type==='number'||c.type==='date';
      var inp=h('input',{type:'text','class':'sg-hfilter',placeholder:'Filter','aria-label':'Filter '+c.label,'data-sg-filter':c.key,
        title:ops?'Contains, or compare with >, <, >=, <=, = (e.g. >=75'+(c.type==='date'?' or <1-Oct-26':'')+')':'Contains'});
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
    grid.onSelectedRowsChanged.subscribe(updateStatus);
    dv.onRowCountChanged.subscribe(function(){ grid.updateRowCount(); grid.render(); updateStatus(); });
    dv.onRowsChanged.subscribe(function(e,args){ grid.invalidateRows(args.rows); grid.render(); });

    grid.init();
    dv.beginUpdate();
    dv.setItems((opts.rows||[]).map(function(r){ return Object.assign({},r); }),rowKey);
    dv.setFilter(rowPasses);
    dv.endUpdate();
    dv.syncGridSelection(grid,false);
    if(lists) refreshLists();

    back.addEventListener('click',function(){ var cb=opts.onBack; close(); if(typeof cb==='function') cb(); });
    search.addEventListener('input',function(){ S.quick=search.value; dv.refresh(); });
    exp.addEventListener('click',exportRows);
    if(add) add.addEventListener('click',doAdd);
    selAll.addEventListener('click',function(){
      var n=dv.getLength(), all=n&&grid.getSelectedRows().length===n, rows=[];
      if(!all) for(var i=0;i<n;i++) rows.push(i);
      grid.setSelectedRows(rows);
    });
    if(lists){
      tmpAdd.addEventListener('click',function(){ listsDone(M().tempAdd(lists.store,selectedRefs())); });
      tmpBtn.addEventListener('click',function(){ toggleTempPanel(); });
      tmpOnlyPill.addEventListener('click',function(){ setTempOnly(false); });
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
    if(dv.getLength()) grid.setActiveCell(0,1);
    return api;
  }

  function close(silent){
    var s=S; if(!s) return;
    if(s.openMenu) s.openMenu.close(false);
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
    // Test hook only: the engine objects of the open screen.
    // requestResize is the exact path a ResizeObserver report takes.
    _engine:function(){ return S?{grid:S.grid,dataView:S.dv,requestResize:S.requestResize}:null; },
    _fmtDate:fmtDate
  };
  root.SRETGrid=api;
})(window);
