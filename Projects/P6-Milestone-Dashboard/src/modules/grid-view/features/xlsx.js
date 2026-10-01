/* =====================================================================
   SRET grid feature: xlsx. Load after grid-view.js.

   Export .xlsx (the rows as filtered and sorted) and Download import
   template (the column headers, no rows). The Excel library comes from
   ensureXLSX(), a loader the deployment sets once in setup() defaults; it
   resolves with the SheetJS object (or with nothing, and window.XLSX is
   used). Screens that can add rows show both in the Add row menu; the
   others get a plain Export button. Dates export in setup's dates.excel
   format.
   Provides 'xlsx' to other features: {exportRows, template}.
   Public: SRETGrid.exportVisible() -> Promise of the exported rows.
   ===================================================================== */
(function(root){
  'use strict';
  root.SRETGrid.feature('xlsx',function(K){
    var h=K.h;
    function lib(){
      var o=K.s().opts, loader=typeof o.ensureXLSX==='function'?o.ensureXLSX:function(){ return Promise.resolve(); };
      return Promise.resolve().then(loader).then(function(x){
        var X=x||root.XLSX;
        if(!X||!X.utils) throw new Error('The Excel library is not available.');
        return X;
      });
    }
    function fileName(o){ return String(o.exportName||o.title||'Grid').replace(/[\\\/:*?"<>|]+/g,' ').trim()||'Grid'; }
    function exportRows(){
      var s=K.s(), o=s.opts;
      if(s.expBtn) s.expBtn.disabled=true;
      return lib().then(function(X){
        var aoa=[s.cols.map(function(c){ return c.label; })];
        for(var i=0;i<s.dv.getLength();i++){
          var it=s.dv.getItem(i);
          aoa.push(s.cols.map(function(c){
            var v=it[c.key];
            if(v==null||v==='') return '';
            if(c.type==='number') return Number(v);
            if(c.type==='date' && K.isoOk(v)) return new Date(Date.UTC(+v.slice(0,4),+v.slice(5,7)-1,+v.slice(8,10)));
            if(c.type==='select') return K.optLabel(c,v);
            return String(v);
          }));
        }
        var ws=X.utils.aoa_to_sheet(aoa,{cellDates:true,dateNF:K.dates().excel});
        ws['!cols']=s.cols.map(function(c){ return {wch:Math.max(8,Math.round((c.width||100)/7))}; });
        var wb=X.utils.book_new();
        X.utils.book_append_sheet(wb,ws,'Grid');
        X.writeFile(wb,fileName(o)+'.xlsx');
        K.say('Exported '+(aoa.length-1)+(aoa.length-1===1?' row':' rows')+'.');
        return aoa;
      }).catch(function(err){
        if(K.s()) K.say(err&&err.message?err.message:'Export failed.');
      }).then(function(r){ var cur=K.s(); if(cur&&cur.expBtn) cur.expBtn.disabled=false; return r; });
    }
    // Import template: the column headers the importer expects, no rows.
    function template(){
      var s=K.s(), o=s.opts;
      if(typeof o.onTemplate==='function') return Promise.resolve(o.onTemplate());
      return lib().then(function(X){
        var head=s.cols.filter(function(c){ return c.key.charAt(0)!=='_'; }).map(function(c){ return c.label; });
        var ws=X.utils.aoa_to_sheet([head]);
        var wb=X.utils.book_new();
        X.utils.book_append_sheet(wb,ws,'Import');
        X.writeFile(wb,fileName(o)+' import template.xlsx');
        K.say('Downloaded the import template ('+head.length+' columns).');
        return head;
      }).catch(function(err){ if(K.s()) K.say(err&&err.message?err.message:'Download failed.'); });
    }

    K.provide('xlsx',{exportRows:exportRows,template:template});
    return {
      addMenu:function(){ return {order:20,items:[{label:'Export .xlsx',sg:'export',onSelect:exportRows},
                                                  {label:'Download import template',sg:'template',onSelect:template}]}; },
      bar2:function(s){
        if(s.canAdd) return [];
        s.expBtn=h('button',{type:'button','class':'sg-btn','data-sg':'export',text:'Export .xlsx'});
        s.expBtn.addEventListener('click',exportRows);
        return [{order:30,el:s.expBtn}];
      },
      api:{exportVisible:function(){ return K.s()?exportRows():Promise.resolve(null); }}
    };
  });
})(window);
