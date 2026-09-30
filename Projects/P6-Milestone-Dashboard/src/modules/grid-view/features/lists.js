/* =====================================================================
   SRET grid feature: lists (My temp list and saved lists). Load after
   grid-view.js; needs window.SRETCollections, which holds every rule.

   Screen option lists: {store, refOf(rowKey), labelOf(ref), onChange(result)}
   adds "Add to temp list" for the selected rows, a "Temp list only"
   filter, a rail and a panel docked left listing the temp items (selected
   items go to a saved list, existing or new, or come off the temp list),
   a read-only List column left of the checkbox, and a mark on temp rows.
   store is the caller's SRETCollections store (data in); refOf maps a
   rowKey to the store's item ref; labelOf names an item in the panel;
   onChange runs after every change so the caller can persist.

   Workflow (Matt, 2026-09-27):
     1. select rows, Add to temp list
     2. open My temp list, select items in it, Add to list
     3. Remove selected items from the temp list
     4. Clear the temp list (More menu)
   ===================================================================== */
(function(root){
  'use strict';
  root.SRETGrid.feature('lists',function(K){
    var h=K.h, esc=K.esc;
    var L_TMP='_tmp', L_LIST='_list', L_IDS='_lids';
    // Matt, 2026-09-28: the temp list is session only; saved lists are kept.
    var TEMP_HINT='My temp list is for this session only. It clears when the file is closed or reloaded. Add items to a saved list to keep them.';
    var LIST_SVG='<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'+
      '<path d="M5 4h8M5 8h8M5 12h8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'+
      '<circle cx="2.5" cy="4" r="1" fill="currentColor"/><circle cx="2.5" cy="8" r="1" fill="currentColor"/><circle cx="2.5" cy="12" r="1" fill="currentColor"/></svg>';
    function M(){ return root.SRETCollections; }

    // Items are the grid's own copies, so the derived fields are written
    // straight onto them; the caller's rows are untouched.
    function listFields(item){
      var s=K.s(), ref=s.lists.refOf(item[s.rowKey]);
      item[L_TMP]=M().inTemp(s.lists.store,ref)?'Yes':'';
      item[L_LIST]=M().membership(s.lists.store,ref).join(', ');
      item[L_IDS]=M().listIdsOf(s.lists.store,ref);
    }
    function selectedRefs(){ var s=K.s(); return K.selectedKeys().map(function(k){ return s.lists.refOf(k); }); }
    function labelOf(ref){
      var s=K.s();
      if(typeof s.lists.labelOf==='function'){ var l=s.lists.labelOf(ref); if(l) return String(l); }
      return String(ref).replace(/^[^:]*:/,'');
    }
    function listName(id){
      var c=M().list(K.s().lists.store).filter(function(x){ return x.id===id; })[0]; return c?c.label:'';
    }
    function listsDone(r){
      var s=K.s();
      K.say(M().describe(r));
      if(s.pnlErr) s.pnlErr.textContent=r.error?M().describe(r):'';
      if(!r.error && typeof s.lists.onChange==='function') s.lists.onChange(r);
      if(s.scope&&s.scope.type==='list'&&!listName(s.scope.id)) s.scope=null;
      K.refreshAll();
      return r;
    }

    // ----- scope filter: only rows on My temp list, or on one saved list -----
    function inScope(item){
      var sc=K.s().scope; if(!sc) return true;
      if(sc.type==='temp') return item[L_TMP]==='Yes';
      return (item[L_IDS]||[]).indexOf(sc.id)>=0;
    }
    function setScope(sc){ var s=K.s(); s.scope=sc||null; s.dv.refresh(); K.updateStatus(); }
    function scopeIs(type,id){ var sc=K.s().scope; return !!sc&&sc.type===type&&(type==='temp'||sc.id===id); }

    // ----- the panel -----
    function panelItems(){
      var s=K.s(), st=s.lists.store;
      return s.panelMode==='temp'?M().temp(st):M().itemsOf(st,s.listId);
    }
    function pickedRefs(){ var s=K.s(); return panelItems().filter(function(r){ return s.picked[r]; }); }
    // Button states only; never rebuilds the item list, so it is safe to call
    // from a checkbox's own change handler.
    function updatePanelButtons(){
      var s=K.s(); if(!s||!s.lists||!s.panelMode) return;
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
      var s=K.s(), st=s.lists.store, temp=s.panelMode==='temp';
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
    function updateLists(s,sel){
      var n=M().temp(s.lists.store).length;
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
      var s=K.s();
      if(mode===s.panelMode) mode=null;
      K.hideConfirm(); hidePanelForms();
      s.panelMode=mode; s.picked={};
      s.panel.hidden=!mode; s.pnlErr.textContent='';
      updateLists(s,s.grid.getSelectedRows().length);
      if(s.requestResize) s.requestResize();
      if(mode) (mode==='temp'?s.tmpAddMenu.btn:s.lstPick).focus();
    }
    function closePanel(){ var s=K.s(), m=s.panelMode; if(!m) return; openPanel(m); (m==='temp'?s.railTemp:s.railLists).focus(); }
    function hidePanelForms(){
      var s=K.s();
      s.pnlConfirm.hidden=true; s.pnlConfirm.innerHTML='';
      s.pnlNewForm.hidden=true; s.pnlName.value='';
    }
    function showNewList(){
      var s=K.s(); if(!pickedRefs().length) return;
      hidePanelForms(); s.pnlNewForm.hidden=false; s.pnlErr.textContent='';
      s.pnlName.focus();
    }
    function saveNewList(){
      var s=K.s(), r=listsDone(M().saveFromTemp(s.lists.store,s.pnlName.value,pickedRefs()));
      if(r.error){ s.pnlName.focus(); return; }
      hidePanelForms(); s.tmpAddMenu.btn.focus();
    }
    function showPanelConfirm(msg,verb,sg,run,back){
      var s=K.s();
      hidePanelForms();
      var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ hidePanelForms(); back.focus(); }}});
      var go=h('button',{type:'button','class':'sg-btn sg-btn--danger','data-sg':sg,text:verb,
        on:{click:function(){ hidePanelForms(); run(); }}});
      s.pnlConfirm.appendChild(h('p',{'class':'sg-confirm-msg',text:msg}));
      s.pnlConfirm.appendChild(h('div',{'class':'sg-confirm-btns'},[cancel,go]));
      s.pnlConfirm.hidden=false;
      cancel.focus();
    }
    function buildPanel(s){
      s.picked={}; s.panelMode=null; s.listId=null;
      var close=h('button',{type:'button','class':'sg-iconbtn','aria-label':'Collapse the panel',title:'Collapse','data-sg':'panel-close',text:'✕'});
      s.pnlTempHead=h('h3',{'class':'sg-temp-title','data-sg':'temp-title',title:TEMP_HINT,'aria-description':TEMP_HINT},[h('span',{'class':'sg-tempmark','aria-hidden':'true'}),h('span',{text:'My temp list'})]);
      s.lstPick=h('select',{'class':'sg-select sg-list-pick','data-sg':'list-pick','aria-label':'Saved list to show'});
      s.pnlListHead=h('span',{'class':'sg-list-head'},[s.lstPick]);
      // Temp mode actions: Add to list (saved lists, New list...), Remove, More.
      s.tmpAddMenu=K.makeMenu('Add to list','temp-addto',function(){
        var st=s.lists.store, none=!pickedRefs().length;
        return M().list(st).map(function(c){
          return {label:c.label+' ('+c.count+')',list:c.id,disabled:none,
                  onSelect:function(){ listsDone(M().addFromTemp(st,c.id,pickedRefs())); }};
        }).concat([{sep:1},{label:'New list…',sg:'temp-newlist',disabled:none,onSelect:showNewList}]);
      },'sg-btn--primary');
      s.tmpRemove=h('button',{type:'button','class':'sg-btn','data-sg':'temp-remove',text:'Remove',
                              title:'Remove the selected items from My temp list'});
      s.tmpMore=K.makeMenu('More','temp-more',function(){
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
      s.lstMore=K.makeMenu('More','list-more',function(){
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
    var LIST_COL_W={collapsed:40,expanded:180};
    function listColName(){
      var s=K.s(), ex=s&&s.listExpanded;
      return '<button type="button" class="sg-lcol-toggle" data-sg="list-col-toggle" aria-expanded="'+(ex?'true':'false')+
        '" aria-label="'+(ex?'Collapse':'Expand')+' the List column" title="'+(ex?'Collapse':'Expand')+' the List column">'+
        (ex?'<span>List</span>':'')+'<span class="sg-lcol-arrow" aria-hidden="true">'+(ex?'◂':'▸')+'</span></button>';
    }
    function listColFormatter(r,cell,v){
      var s=K.s(); if(!v) return '';
      if(s&&s.listExpanded) return esc(v);
      var n=String(v).split(', ').length;
      return '<span class="sg-inlist" title="'+esc('In '+v)+'"><span class="sg-inlist-mark" aria-hidden="true"></span>'+n+'</span>';
    }
    function toggleListCol(){
      var s=K.s(); s.listExpanded=!s.listExpanded;
      var cols=s.grid.getColumns();
      cols.forEach(function(c){ if(c.id===L_LIST){ c.width=s.listExpanded?LIST_COL_W.expanded:LIST_COL_W.collapsed; c.name=listColName();
        c.minWidth=s.listExpanded?44:LIST_COL_W.collapsed; } });
      // Collapsed, the column has no filter box; any filter on it is cleared.
      if(!s.listExpanded&&s.filters[L_LIST]){ s.filters[L_LIST]=''; s.dv.refresh(); }
      s.grid.setColumns(cols);
      s.grid.invalidate();
      var b=s.screen.querySelector('[data-sg=list-col-toggle]'); if(b) b.focus();
    }

    return {
      needs:['SRETCollections'],
      use:function(o){
        if(!o.lists) return false;
        if(!o.lists.store||typeof o.lists.refOf!=='function') throw new Error('SRETGrid.open: lists needs store and refOf(rowKey).');
        return true;
      },
      // The List column sits left of the checkbox (Matt, 2026-09-27).
      columns:function(cols){
        return [{key:L_LIST,label:'List',type:'text',editable:false,opts:[],width:LIST_COL_W.collapsed,aux:true,beforeCheck:true,
                 filterShown:function(){ var s=K.s(); return !!(s&&s.listExpanded); },
                 slickDef:function(c){ return {id:c.key,field:c.key,name:listColName(),toolTip:'Saved lists this row is in',width:c.width,minWidth:c.width,
                   sortable:true,resizable:true,sg:c,editor:null,cssClass:'sg-cell-ro sg-lcol',headerCssClass:'sg-lcol-h',formatter:listColFormatter}; }}].concat(cols);
      },
      init:function(s){ s.lists=s.opts.lists; s.scope=null; s.listExpanded=false; },
      bar2:function(s){
        s.tmpAddBtn=h('button',{type:'button','class':'sg-btn','data-sg':'temp-add',disabled:true,title:'Add the selected rows to My temp list'},
                                [h('span',{'class':'sg-tempmark','aria-hidden':'true'}),h('span',{text:'Add to temp list'})]);
        var m=K.makeMenu('More temp list options','temp-add-more',function(){
          var st=s.lists.store, sel=selectedRefs(), selTemp=sel.filter(function(r){ return M().inTemp(st,r); }).length;
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
        },null,s.tmpAddBtn);
        s.tmpAddBtn.addEventListener('click',function(){ listsDone(M().tempAdd(s.lists.store,selectedRefs())); });
        return [{order:60,el:m.wrap}];
      },
      bar3:function(s){
        s.pillText=h('span');
        s.pill=h('button',{type:'button','class':'sg-pill','data-sg':'scope-pill',hidden:true,title:'Click to show all rows'},
                 [s.pillText,h('span',{'aria-hidden':'true',text:' ✕'})]);
        s.pill.addEventListener('click',function(){ setScope(null); });
        return [{order:30,el:s.pill}];
      },
      tools:function(s){ return {order:10,items:[{label:'Expand the List column',sg:'list-col',checked:!!s.listExpanded,onSelect:toggleListCol}]}; },
      body:function(s){
        s.tmpCount=h('span',{'class':'sg-badge sg-rail-badge','data-sg':'temp-count',text:'0',hidden:true});
        s.railTemp=h('button',{type:'button','class':'sg-rail-btn','data-sg':'temp-open','aria-expanded':'false',
                               'aria-controls':'sg-panel','aria-label':'My temp list',title:'My temp list (this session only)'},
                              [h('span',{'class':'sg-tempmark sg-tempmark--rail','aria-hidden':'true'}),s.tmpCount]);
        s.railLists=h('button',{type:'button','class':'sg-rail-btn','data-sg':'lists-open','aria-expanded':'false',
                                'aria-controls':'sg-panel','aria-label':'Saved lists',title:'Saved lists'});
        s.railLists.innerHTML=LIST_SVG;
        s.panel=h('aside',{'class':'sg-temp',id:'sg-panel','aria-label':'My temp list','data-sg':'panel',hidden:true});
        buildPanel(s);
        s.railTemp.addEventListener('click',function(){ openPanel('temp'); });
        s.railLists.addEventListener('click',function(){ openPanel('list'); });
        return [h('nav',{'class':'sg-rail','aria-label':'Panels'},[s.railTemp,s.railLists]),s.panel];
      },
      grid:function(s){
        s.grid.onHeaderCellRendered.subscribe(function(e,args){
          if(args.column.id!==L_LIST) return;
          var b=args.node.querySelector('.sg-lcol-toggle');
          // Its own handler, so a click on the arrow toggles and never sorts.
          if(b) b.addEventListener('click',function(ev){ ev.stopPropagation(); toggleListCol(); });
        });
      },
      // Rows on My temp list carry a class; CSS draws the vertical line left of the checkbox.
      rowClass:function(item){ return item[L_TMP]==='Yes'?'sg-in-temp':''; },
      prepare:listFields,
      rowFilter:inScope,
      busy:function(s){ return !!s.scope; },
      status:updateLists,
      beforeConfirm:function(s){ if(s.panelMode) openPanel(s.panelMode); }
    };
  });
})(window);
