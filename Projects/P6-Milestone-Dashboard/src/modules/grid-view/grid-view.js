/* =====================================================================
   SRET grid view (D-09). One full-screen table view, three uses:
   annotation collections, user-defined milestones, schedule activities.

   Contract (docs/grid-view-integration.md):
     SRETGrid.open({
       title, columns:[{key,label,type,editable,options,width}], rows, rowKey,
       editable, onEdit(rowKey,key,value), onAdd(), onDelete(rowKeys),
       onBack(), exportName, ensureXLSX, host, canEdit(rowKey,key),
       lists:{ store, refOf(rowKey), onChange(result) }
     })
     SRETGrid.close()   SRETGrid.setRows(rows)   SRETGrid.patchRows(rows)   SRETGrid.isOpen()
   Return false from onEdit to refuse a value (the cell reverts), from
   onDelete to keep the rows. onAdd returns the new row object (with its
   rowKey) or nothing to add no row. canEdit, optional, refuses an edit on
   one row where the column is otherwise editable.
   lists, optional, adds My temp list: "Add to temp list" for the selected
   rows, a "Temp list only" filter, and a panel with A. Save new list,
   B. Add to existing, C. Clear, plus remove-selected. It also adds read-only
   List and Temp columns. store is the caller's SRETCollections store (data
   in); refOf maps a rowKey to the store's item ref; onChange(result) runs
   after every change so the caller can persist. All rules live in the
   shared SRETCollections module (src/modules/collections/), never here.

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

  function ctlHeight(el){
    var v=parseFloat(getComputedStyle(el).getPropertyValue('--ctl-h'));
    return isFinite(v)&&v>0?v:24;
  }

  // ---------- status / confirm ----------
  function updateStatus(){
    var s=S; if(!s) return;
    var shown=s.dv.getLength(), total=s.dv.getItems().length, sel=s.grid.getSelectedRows().length;
    s.countEl.textContent=shown===total?(total+(total===1?' row':' rows')):(shown+' of '+total+' rows');
    s.selEl.textContent=sel?(sel+' selected'):'';
    if(s.delBtn) s.delBtn.disabled=!sel;
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
    var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hideConfirm(); s.delBtn.focus(); }}});
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
  // The rules (temp list, one list per item, save / add / clear) live in
  // SRETCollections. This section only draws the controls and calls it.
  var L_TMP='_tmp', L_LIST='_list';
  function M(){ return root.SRETCollections; }
  function listFields(item){
    var s=S, ref=s.lists.refOf(item[s.rowKey]);
    item[L_TMP]=M().inTemp(s.lists.store,ref)?'Yes':'';
    item[L_LIST]=M().membership(s.lists.store,ref);
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
  function listsDone(r){
    var s=S;
    s.msgEl.textContent=M().describe(r);
    s.tmpErr.textContent=r.error?M().describe(r):'';
    if(!r.error && typeof s.lists.onChange==='function') s.lists.onChange(r);
    refreshLists();
    return r;
  }
  // A control that sets state also shows it: counts, pressed and expanded
  // states and enabled buttons all follow the store on every change.
  function updateLists(){
    var s=S; if(!s||!s.lists) return;
    var st=s.lists.store, tmp=M().temp(st), n=tmp.length, sel=s.grid.getSelectedRows().length;
    var here=s.dv.getItems().filter(function(it){ return it[L_TMP]==='Yes'; }).length;
    s.tmpAddBtn.disabled=!sel;
    s.tmpBtn.textContent='My temp list ('+n+')';
    s.tmpBtn.setAttribute('aria-expanded',String(!s.tmpPanel.hidden));
    s.tmpOnlyBtn.setAttribute('aria-pressed',String(!!s.tempOnly));
    s.tmpOnlyBtn.classList.toggle('is-on',!!s.tempOnly);
    s.tmpSummary.textContent='My temp list holds '+n+(n===1?' item':' items')+
      (n?', '+here+' of them on this screen.':'. Select rows and use Add to temp list.');
    var cur=s.tmpTarget.value;
    s.tmpTarget.innerHTML='';
    var ls=M().list(st);
    if(!ls.length) s.tmpTarget.appendChild(h('option',{value:'',text:'No saved lists yet'}));
    ls.forEach(function(c){ s.tmpTarget.appendChild(h('option',{value:c.id,text:c.label+' ('+c.count+')'})); });
    if(ls.some(function(c){ return c.id===cur; })) s.tmpTarget.value=cur;
    s.tmpSave.disabled=!n; s.tmpAddTo.disabled=!n||!ls.length; s.tmpTarget.disabled=!ls.length;
    s.tmpClear.disabled=!n;
    s.tmpRemove.disabled=!selectedKeys().some(function(k){ return M().inTemp(st,s.lists.refOf(k)); });
  }
  function toggleTempPanel(show){
    var s=S; if(show==null) show=s.tmpPanel.hidden;
    if(show) hideConfirm();
    hideTempConfirm();
    s.tmpPanel.hidden=!show; s.tmpErr.textContent='';
    updateLists();
    if(show) s.tmpName.focus(); else s.tmpBtn.focus();
  }
  function hideTempConfirm(){ var s=S; s.tmpConfirm.hidden=true; s.tmpConfirm.innerHTML=''; s.tmpActions.hidden=false; }
  function showTempConfirm(){
    var s=S, n=M().temp(s.lists.store).length; if(!n) return;
    s.tmpConfirm.innerHTML='';
    var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hideTempConfirm(); s.tmpClear.focus(); }}});
    var go=h('button',{type:'button','class':'sg-btn sg-btn--danger','data-sg':'temp-clear-confirm',text:'Clear',
      on:{click:function(){ hideTempConfirm(); listsDone(M().tempClear(s.lists.store)); s.tmpName.focus(); }}});
    s.tmpConfirm.appendChild(h('p',{'class':'sg-confirm-msg',
      text:'Clear My temp list ('+n+(n===1?' item':' items')+')? Saved lists are not changed.'}));
    s.tmpConfirm.appendChild(h('div',{'class':'sg-confirm-btns'},[cancel,go]));
    s.tmpActions.hidden=true; s.tmpConfirm.hidden=false;
    cancel.focus();
  }
  function buildTempPanel(){
    var s=S;
    s.tmpSummary=h('p',{'class':'sg-temp-summary','data-sg':'temp-summary'});
    s.tmpName=h('input',{type:'text','class':'sg-search sg-temp-name','aria-label':'Name for the new list',
                         placeholder:'List name','data-sg':'temp-name',maxlength:'60'});
    s.tmpSave=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'temp-save',text:'Save new list'});
    s.tmpTarget=h('select',{'class':'sg-select','aria-label':'Saved list to add to','data-sg':'temp-target'});
    s.tmpAddTo=h('button',{type:'button','class':'sg-btn','data-sg':'temp-addto',text:'Add to list'});
    s.tmpRemove=h('button',{type:'button','class':'sg-btn','data-sg':'temp-remove',text:'Remove selected from temp list'});
    s.tmpClear=h('button',{type:'button','class':'sg-btn','data-sg':'temp-clear',text:'Clear temp list'});
    s.tmpErr=h('p',{'class':'sg-temp-err',role:'alert','data-sg':'temp-err'});
    s.tmpConfirm=h('div',{'class':'sg-temp-confirm','data-sg':'temp-confirm',hidden:true});
    var close=h('button',{type:'button','class':'sg-iconbtn','aria-label':'Close My temp list',title:'Close','data-sg':'temp-close',text:'✕'});
    s.tmpActions=h('div',{'class':'sg-temp-actions'},[
      h('div',{'class':'sg-temp-row'},[h('span',{'class':'sg-temp-lbl',text:'A. Save new list'}),s.tmpName,s.tmpSave]),
      h('div',{'class':'sg-temp-row'},[h('span',{'class':'sg-temp-lbl',text:'B. Add to existing'}),s.tmpTarget,s.tmpAddTo]),
      h('div',{'class':'sg-temp-row'},[h('span',{'class':'sg-temp-lbl',text:'C. Clear'}),s.tmpClear,s.tmpRemove])
    ]);
    s.tmpPanel.appendChild(h('div',{'class':'sg-temp-head'},[h('h3',{'class':'sg-temp-title',text:'My temp list'}),close]));
    s.tmpPanel.appendChild(s.tmpSummary);
    s.tmpPanel.appendChild(s.tmpActions);
    s.tmpPanel.appendChild(s.tmpConfirm);
    s.tmpPanel.appendChild(s.tmpErr);
    var save=function(){ var r=listsDone(M().saveTemp(s.lists.store,s.tmpName.value)); if(!r.error) s.tmpName.value=''; else s.tmpName.focus(); };
    s.tmpSave.addEventListener('click',save);
    s.tmpName.addEventListener('keydown',function(e){ if(e.key==='Enter'){ e.preventDefault(); save(); } });
    s.tmpAddTo.addEventListener('click',function(){ listsDone(M().addTempTo(s.lists.store,s.tmpTarget.value)); });
    s.tmpRemove.addEventListener('click',function(){ listsDone(M().tempRemove(s.lists.store,selectedRefs())); });
    s.tmpClear.addEventListener('click',showTempConfirm);
    close.addEventListener('click',function(){ toggleTempPanel(false); });
    s.tmpPanel.addEventListener('keydown',function(e){
      if(e.key!=='Escape') return;
      e.preventDefault(); e.stopPropagation();
      if(!s.tmpConfirm.hidden){ hideTempConfirm(); s.tmpClear.focus(); } else toggleTempPanel(false);
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
      s.msgEl.textContent='Exported '+(aoa.length-1)+(aoa.length-1===1?' row':' rows')+'.';
      return aoa;
    }).catch(function(err){
      if(S) S.msgEl.textContent=err&&err.message?err.message:'Export failed.';
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
    var del=canDel?h('button',{type:'button','class':'sg-btn','data-sg':'delete',text:'Delete selected',disabled:true}):null;
    var tmpAdd=lists?h('button',{type:'button','class':'sg-btn','data-sg':'temp-add',text:'Add to temp list',disabled:true,
                                 title:'Add the selected rows to My temp list'}):null;
    var tmpBtn=lists?h('button',{type:'button','class':'sg-btn','data-sg':'temp-open','aria-expanded':'false',
                                 'aria-controls':'sg-temp-panel',text:'My temp list (0)'}):null;
    var tmpOnly=lists?h('button',{type:'button','class':'sg-chip','data-sg':'temp-only','aria-pressed':'false',
                                  text:'Temp list only',title:'Show only rows on My temp list'}):null;
    var msg=h('span',{'class':'sg-msg',role:'status','aria-live':'polite','data-sg':'msg'});
    var bar=h('div',{'class':'sg-bar'},[
      h('div',{'class':'sg-bar-lead'},[back,title]),
      h('div',{'class':'sg-bar-tools'},[search,h('span',{'class':'sg-counts'},[count,selc]),msg,tmpAdd,tmpBtn,tmpOnly,exp,add,del])
    ]);
    var confirm=h('div',{'class':'sg-confirm',role:'alertdialog','aria-label':'Confirm remove','data-sg':'confirm',hidden:true});
    var tmpPanel=h('div',{'class':'sg-temp',id:'sg-temp-panel',role:'region','aria-label':'My temp list','data-sg':'temp-panel',hidden:true});
    var gridEl=h('div',{'class':'sg-grid','data-sg':'grid'});
    var screen=h('section',{'class':'sg-screen'+(fixed?' sg-screen--fixed':''),role:'region','aria-label':opts.title||'Table'},
                 [bar,confirm,tmpPanel,gridEl]);
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
       screen:screen,host:host,countEl:count,selEl:selc,msgEl:msg,delBtn:del,expBtn:exp,searchEl:search,
       confirmEl:confirm,prev:null,returnFocus:document.activeElement,ro:null,
       lists:lists,tempOnly:false,tmpAddBtn:tmpAdd,tmpBtn:tmpBtn,tmpOnlyBtn:tmpOnly,tmpPanel:tmpPanel};
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
        S.msgEl.textContent='This value comes from the schedule and cannot be edited here.';
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
        S.msgEl.textContent='That change was not accepted.';
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
    if(del) del.addEventListener('click',function(){ if(lists) toggleTempPanel(false); showConfirm(); });
    if(lists){
      tmpAdd.addEventListener('click',function(){ listsDone(M().tempAdd(lists.store,selectedRefs())); });
      tmpBtn.addEventListener('click',function(){ toggleTempPanel(); });
      tmpOnly.addEventListener('click',function(){ S.tempOnly=!S.tempOnly; dv.refresh(); updateStatus(); });
    }
    screen.addEventListener('keydown',function(e){
      if(e.key==='Escape' && !confirm.hidden){ e.stopPropagation(); hideConfirm(); if(del) del.focus(); }
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
