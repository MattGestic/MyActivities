/* =====================================================================
   SRET grid feature: import. Load after grid-view.js (and xlsx.js for the
   template link).

   Import from a file in a centred dialog, with an Import log. Two ways:
     importer: {...}   the grid runs the whole flow: choose a file, check
       it, ask when something is off, then add the rows through
       importer.onCommit and log every issue. The rules live in an import
       engine, importer.engine (default window.SRETMsImport):
         parseFile(file, ensureXLSX) -> Promise aoa
         check(aoa, cfg) -> {fatal, rows, issues, skipped, dates, ...}
         logEntries(res, meta) -> [entries]   summary(res, assigned, noun) -> [lines]
       importer keys: noun ['task','tasks'], idKey, depKeys, knownIds(),
       nextId(taken), onCommit(rows), user, log, onLog(entries), engine.
     onImport(body, close)   the caller mounts its own form in the dialog.
   Date order: detected from the file's dates or chosen in the dialog;
   labels come from window.SRETDates when it is loaded.
   Public: SRETGrid.importAoa(aoa, fileName) runs the checks on a sheet the
   caller has already parsed.
   ===================================================================== */
(function(root){
  'use strict';
  root.SRETGrid.feature('import',function(K){
    var h=K.h;
    function engine(){ var im=K.s().opts.importer; return im&&im.engine||root.SRETMsImport; }
    // What one imported row is called: importer.noun, else the deployment's text.noun.
    function noun(n){ var s=K.s(), im=s&&s.opts.importer, w=im&&im.noun||K.t('noun'); return n===1?w[0]:w[1]; }
    function title(){ return 'Import '+noun(2); }
    function open(){
      var s=K.s();
      if(s.opts.importer) return K.openDialog(title(),function(body,close){ return build(body,close); });
      K.openDialog(title(),function(body,close){ return s.opts.onImport(body,close); });
    }
    function cfg(){
      var s=K.s(), im=s.opts.importer;
      return {columns:s.cols.filter(function(c){ return c.key.charAt(0)!=='_'; }),
              idKey:im.idKey||s.rowKey, depKeys:im.depKeys||{},
              existingIds:s.dv.getItems().map(function(it){ return it[s.rowKey]; }),
              knownIds:typeof im.knownIds==='function'?im.knownIds():[],
              dateOrder:s.importUi&&s.importUi.dateSel?s.importUi.dateSel.value:'auto'};
    }
    // Date order for the file: detected from all its dates, or chosen here.
    // Changing it re-runs the checks on the same sheet.
    function dateSelect(ui){
      var sel=h('select',{'class':'sg-select sg-date-order','data-sg':'import-date-order','aria-label':'Date order'},
        [['auto','Detect from the file'],['DMY','Day first (9/10/26 is 9-Oct-26)'],['MDY','Month first (10/9/26 is 9-Oct-26)'],['YMD','Year first (26/10/9 is 9-Oct-26)']]
          .map(function(o){ return h('option',{value:o[0],text:o[1]}); }));
      sel.addEventListener('change',function(){
        if(ui.lastAoa&&ui.status.getAttribute('data-kind')!=='done') run(ui.lastAoa,ui.lastFile,ui);
      });
      ui.dateSel=sel;
      return h('label',{'class':'sg-import-date'},[h('span',{text:'Date order'}),sel]);
    }
    function panel(ui,kind,children){
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
    function run(aoa,fileName,ui){
      var s=K.s();
      ui.lastAoa=aoa; ui.lastFile=fileName; s.importUi=ui;
      var res=engine().check(aoa,cfg());
      if(res.fatal){
        K.say('Import failed. '+res.fatal);
        panel(ui,'error',[h('p',{'class':'sg-import-head',text:'Import failed'}),h('p',{'data-sg':'import-error',text:res.fatal})]);
        ui.status.setAttribute('role','alert');
        return res;
      }
      var dt=res.dates||{}, D=root.SRETDates;
      if(!res.issues.length&&!dt.ask){ commit(res,fileName,ui); return res; }
      var q=res.depIssueRows?'Some dependencies or predecessors are not found. Do you wish to continue with import?'
           :res.issues.length?'Some values could not be read. Do you wish to continue with import?'
           :'The date order could not be confirmed from the file. Do you wish to continue with import?';
      var dateNote=dt.ask&&D?h('p',{'data-sg':'import-date-note',text:'Dates will be read as '+D.orderLabel(dt.order)+' ('+D.example(dt.order)+'). '+
        dt.ambiguous+(dt.ambiguous===1?' date would':' dates would')+' read differently in another order; if that is wrong, choose the order in Date order.'}):null;
      var cancel=h('button',{type:'button','class':'sg-btn',text:'Cancel',on:{click:function(){ if(ui.onCancel) return ui.onCancel(); panel(ui,'',[]); ui.go.focus(); }}});
      var go=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'import-continue',text:'Continue import',
        on:{click:function(){ commit(res,fileName,ui); }}});
      panel(ui,'confirm',[
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
    function commit(res,fileName,ui){
      var s=K.s(), im=s.opts.importer, E=engine(), idKey=im.idKey||s.rowKey, assigned={}, taken=[];
      var rows=res.rows.map(function(r){
        var d=Object.assign({},r.data);
        if(!d[idKey]){ d[idKey]=im.nextId(taken); taken.push(d[idKey]); assigned[r.rowNum]=d[idKey]; }
        return d;
      });
      var added=typeof im.onCommit==='function'?(im.onCommit(rows)||rows):rows;
      s.dv.beginUpdate();
      added.forEach(function(r){ var c=Object.assign({},r); K.prepare(c); s.dv.addItem(c); });
      s.dv.endUpdate();
      var entries=E.logEntries(res,{time:new Date().toISOString(),file:fileName,user:(typeof im.user==='function'?im.user():im.user)||'(not set)',assigned:assigned});
      if(im.log) Array.prototype.push.apply(im.log,entries);
      if(entries.length&&typeof im.onLog==='function') im.onLog(entries);
      K.rowsChanged();
      var lines=E.summary(res,assigned,im.noun);
      K.say(lines[0]);
      var ul=h('ul',{'class':'sg-import-summary','data-sg':'import-summary'});
      lines.forEach(function(l){ ul.appendChild(h('li',{text:l})); });
      var done=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'import-done',text:'Done',on:{click:function(){ ui.close(); }}});
      var logBtn=entries.length?h('button',{type:'button','class':'sg-btn','data-sg':'import-view-log',text:'View Import log',
        on:{click:function(){ ui.close(); openLog(); }}}):h('span');
      ui.pick.hidden=true;
      panel(ui,'done',[h('p',{'class':'sg-import-head',text:'Import complete'}),ul,h('div',{'class':'sg-confirm-btns'},[logBtn,done])]);
      done.focus();
    }
    function build(body,close){
      var s=K.s(), o=s.opts, X=K.get('xlsx');
      var file=h('input',{type:'file',accept:'.xlsx,.csv','aria-label':'File to import','data-sg':'import-file'});
      var go=h('button',{type:'button','class':'sg-btn sg-btn--primary','data-sg':'import-go',text:'Import',disabled:true});
      var tpl=X?h('button',{type:'button','class':'sg-link','data-sg':'import-template',text:'Download import template',on:{click:X.template}}):null;
      var pick=h('div',{'class':'sg-import-pick'},[
        h('p',{text:'Choose a file made from the import template (.xlsx or .csv). Rows whose ID is already in the table are skipped; a blank ID is assigned for you.'}),
        h('div',{'class':'sg-import-row'},[file,go])]);
      var status=h('div',{'class':'sg-import-status','data-sg':'import-status'});
      body.appendChild(pick); body.appendChild(status);
      var ui={pick:pick,status:status,go:go,close:close};
      pick.appendChild(h('div',{'class':'sg-import-row'},[dateSelect(ui)]));
      if(tpl) pick.appendChild(h('div',{},[tpl]));
      s.importUi=ui;
      file.addEventListener('change',function(){ go.disabled=!file.files.length; panel(ui,'',[]); });
      go.addEventListener('click',function(){
        var f=file.files[0]; go.disabled=true;
        engine().parseFile(f,o.ensureXLSX).then(function(aoa){ if(K.s()===s) run(aoa,f.name,ui); })
          .catch(function(err){
            if(K.s()!==s) return;
            var m=err&&err.message?err.message:'The file could not be read.';
            K.say('Import failed. '+m);
            panel(ui,'error',[h('p',{'class':'sg-import-head',text:'Import failed'}),h('p',{'data-sg':'import-error',text:m})]);
            ui.status.setAttribute('role','alert');
          }).then(function(){ if(K.s()===s) go.disabled=!file.files.length; });
      });
      return function(){ if(s.importUi===ui) s.importUi=null; };
    }
    function stamp(iso){
      var d=new Date(iso); if(isNaN(d)) return String(iso||'');
      var m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getMonth()];
      return d.getDate()+'-'+m+'-'+String(d.getFullYear()).slice(2)+' '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
    }
    function openLog(){
      var s=K.s(), log=(s.opts.importer&&s.opts.importer.log)||[];
      K.openDialog('Import log',function(body){
        if(!log.length){ body.appendChild(h('p',{'data-sg':'import-log-empty',text:'No import issues logged yet.'})); return; }
        var t=h('table',{'class':'sg-itable','data-sg':'import-log-table'});
        t.appendChild(h('thead',{},[h('tr',{},['Time','File','User','ID','Note'].map(function(x){ return h('th',{text:x}); }))]));
        var b=h('tbody');
        log.slice().reverse().forEach(function(e){
          b.appendChild(h('tr',{},[stamp(e.time),e.file,e.user,e.id,e.note].map(function(x){ return h('td',{text:x==null?'':String(x)}); })));
        });
        t.appendChild(b);
        body.appendChild(h('div',{'class':'sg-itable-wrap'},[t]));
      },{wide:true});
    }

    return {
      use:function(o){ return !!o.importer||typeof o.onImport==='function'; },
      text:{noun:['row','rows']},
      addMenu:function(s){
        return {order:30,items:[{label:title()+'…',sg:'import',onSelect:open},
                                s.opts.importer?{label:'Import log',sg:'import-log',onSelect:openLog}:null]};
      },
      api:{
        // For the app's own import form: hand in the parsed sheet, and the grid
        // runs the same checks, question, log and summary in its dialog.
        importAoa:function(aoa,fileName){
          var s=K.s();
          if(!s||!s.opts.importer||!K.active('import')) return null;
          K.openDialog(title(),function(body,close){
            var ui={pick:h('div'),status:h('div',{'class':'sg-import-status','data-sg':'import-status'}),go:h('button'),close:close,onCancel:close};
            body.appendChild(h('div',{'class':'sg-import-row'},[dateSelect(ui)])); body.appendChild(ui.status);
            run(aoa,fileName||'Imported sheet',ui);
          });
          return true;
        }
      }
    };
  });
})(window);
