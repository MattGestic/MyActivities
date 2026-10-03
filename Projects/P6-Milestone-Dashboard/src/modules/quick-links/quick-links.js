/* =====================================================================
   SRET quick links (P80). Two named links to where this dashboard's files
   are kept (a SharePoint library, a synced OneDrive folder), set once in the
   blank copy and carried in every file saved from it, so whoever opens it can
   get to last period's saved file before choosing Continue from saved.

   Back end only. No DOM, no app global, no network. Pure functions over a
   list the caller owns and persists.

   A link is { title:string, url:string }. Rules:
     - at most MAX (2) slots; a slot with no URL is empty and dropped;
     - the URL must be http:, https: or file: (a OneDrive or network path
       written as file:///...). A Windows path (C:\... or \\server\share\...)
       is turned into a file: URL. Anything else, javascript: and data:
       included, is refused, because the link is opened by whoever reads
       the file, not only by whoever typed it;
     - the title is trimmed to TITLE_MAX characters; a blank title falls
       back to the host name, or the last part of a file path.

   API:
     normaliseUrl(text) -> { url, error }       url is '' when text is blank
     normalise(list)    -> { links:[{title,url}], errors:[string] }
                           errors name the slot (Link 1, Link 2); a refused
                           slot is left out of links
     label(link)        -> the text to show for a link
     MAX, TITLE_MAX

   Messages are user-facing: no em dashes (CLAUDE.md, hard constraints).
   Exposes window.SRETQuickLinks, and module.exports for Node.
   ===================================================================== */
(function(root){
  'use strict';

  var MAX=2, TITLE_MAX=60;
  var OK_SCHEMES=/^(https?|file):$/i;

  function str(v){ return v==null?'':String(v); }

  function normaliseUrl(text){
    var t=str(text).trim();
    if(!t) return {url:'',error:null};
    // Windows paths, as copied from Explorer's address bar.
    if(/^[A-Za-z]:[\\/]/.test(t)) t='file:///'+t.replace(/\\/g,'/');
    else if(/^\\\\[^\\]/.test(t)) t='file://'+t.slice(2).replace(/\\/g,'/');
    else if(/^www\./i.test(t)) t='https://'+t;
    var u;
    try{ u=new URL(t); }catch(e){ return {url:'',error:'is not a web address or a folder path.'}; }
    if(!OK_SCHEMES.test(u.protocol)) return {url:'',error:'must start with https://, http:// or file://.'};
    if(/^https?:$/i.test(u.protocol)&&!u.hostname) return {url:'',error:'has no site name.'};
    return {url:u.href,error:null};
  }

  function fallbackTitle(url){
    try{
      var u=new URL(url);
      if(u.protocol==='file:'){
        var parts=decodeURIComponent(u.pathname).split('/').filter(Boolean);
        return parts.length?parts[parts.length-1]:'Folder';
      }
      return u.hostname.replace(/^www\./i,'');
    }catch(e){ return 'Link'; }
  }

  function label(link){
    var t=str(link&&link.title).trim();
    return t||fallbackTitle(link&&link.url);
  }

  function normalise(list){
    var src=Array.isArray(list)?list:[];
    var links=[], errors=[];
    for(var i=0;i<Math.min(src.length,MAX);i++){
      var it=src[i]||{};
      var n=normaliseUrl(it.url);
      var title=str(it.title).replace(/\s+/g,' ').trim().slice(0,TITLE_MAX);
      if(n.error){ errors.push('Link '+(i+1)+': the address '+n.error); continue; }
      if(!n.url){ if(title) errors.push('Link '+(i+1)+': add an address for "'+title+'", or clear the title.'); continue; }
      links.push({title:title,url:n.url});
    }
    return {links:links,errors:errors};
  }

  var api={normaliseUrl:normaliseUrl,normalise:normalise,label:label,MAX:MAX,TITLE_MAX:TITLE_MAX};
  root.SRETQuickLinks=api;
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
})(typeof window!=='undefined'?window:(typeof globalThis!=='undefined'?globalThis:this));
