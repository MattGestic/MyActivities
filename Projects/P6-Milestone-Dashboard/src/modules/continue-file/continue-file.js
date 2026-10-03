/* =====================================================================
   SRET continue-file (P79). Reads a previously saved dashboard so a blank
   copy can continue from it: last period's schedule, baseline, notes,
   remarks, edits and user tasks, mirrored into the copy that is open now.

   Back end only. No DOM, no app global, no network, no eval. The saved
   file's scripts are never run: the state is found as text and parsed with
   JSON.parse, so a file carrying anything else is inert here.

   Accepted inputs (text of the file the user picked):
     - a saved dashboard (.html): its published-state script element. Only
       an element whose text opens with the assignment counts, because the
       app's own source (this comment too, once embedded) names it. Written
       by publishDashboard() as
       window.__PUBLISHED_STATE__=<json>;  with < > & escaped as < etc.
     - a full-state JSON (.json): a Backups download (P76) or the bare state
       object. It must carry a timeline with dates, which an annotations-only
       model export does not, so that one is refused with a pointer to the
       Sources mount that reads it.

   API (all pure; nothing is stored here):
     read(text, fileName, ctx) -> {
        ok, errors:[string], warnings:[string],
        format:'html'|'json'|null, payload:object|null, summary:object|null }
       ctx: { appVersion: APP_VERSION } (optional; enables the version notes)
     extractState(text) -> { payload, format, error }
     summarise(payload, fileName) -> {
        fileName, savedAt, savedBy (app version), projectNo, reportTitle,
        dataDate, sources:[name], milestones, tasks, userTasks, entries,
        notes, hasBaseline, chainLength, empty }
     check(payload, ctx) -> { errors:[string], warnings:[string] }
     chainOf(payload) -> [{at, fromVersion}]  the provenance to carry on
     compareVersions(a, b) -> -1 | 0 | 1  (major.minor.patch-P<n>, P number last)

   Messages are user-facing: no em dashes (CLAUDE.md, hard constraints).
   Exposes window.SRETContinue, and module.exports for Node.
   ===================================================================== */
(function(root){
  'use strict';

  // The element's text must open with the assignment; group 1 is the JSON
  // and its closing semicolon. \x3C is '<': no literal script tag inside a
  // script (CLAUDE.md, hard constraints; docs/06-lessons-learned.md).
  var STATE_BLOCK=/\x3Cscript\b[^>]*\bid\s*=\s*["']?published-state["']?[^>]*>\s*window\.__PUBLISHED_STATE__\s*=\s*([\s\S]*?)\x3C\/script>/i;

  function isObj(v){ return !!v&&typeof v==='object'&&!Array.isArray(v); }
  function len(v){ return Array.isArray(v)?v.length:(isObj(v)?Object.keys(v).length:0); }

  // The JSON between the prefix and the closing semicolon. Publish escapes
  // every < > & inside the data, so the first closing script tag after the
  // block's start is its own.
  function extractState(text){
    var t=String(text==null?'':text);
    var head=t.slice(0,4096).replace(/^﻿/,'').replace(/^\s+/,'');
    if(head.charAt(0)==='{'){
      try{ return {payload:JSON.parse(t.replace(/^﻿/,'')),format:'json',error:null}; }
      catch(e){ return {payload:null,format:'json',error:'The file is not valid JSON.'}; }
    }
    if(!/<html|<!doctype/i.test(head)&&!STATE_BLOCK.test(t))
      return {payload:null,format:null,error:'This is not a saved dashboard. Choose an .html file made with Save, or a backup .json.'};
    var m=STATE_BLOCK.exec(t);
    if(!m) return {payload:null,format:'html',
      error:'This page holds no saved dashboard data. It may be a blank copy of the app or a shared report, not a file made with Save.'};
    var body=m[1].replace(/;\s*$/,'');
    try{ return {payload:JSON.parse(body),format:'html',error:null}; }
    catch(e){ return {payload:null,format:'html',error:'The saved data in this file is damaged and cannot be read.'}; }
  }

  // 'major.minor.patch-P<n>' -> [major,minor,patch,n]. Anything unparseable compares as equal, so an
  // odd version string never blocks a load on its own.
  function vparts(v){
    var m=/^(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z]*(\d+))?/.exec(String(v||''));
    return m?[+m[1],+m[2],+m[3],m[4]==null?0:+m[4]]:null;
  }
  function compareVersions(a,b){
    var x=vparts(a), y=vparts(b);
    if(!x||!y) return 0;
    for(var i=0;i<4;i++){ if(x[i]!==y[i]) return x[i]<y[i]?-1:1; }
    return 0;
  }

  function chainOf(p){
    var c=isObj(p)&&Array.isArray(p.publishChain)?p.publishChain:[];
    return c.filter(isObj).map(function(e){ return {at:e.at||null,fromVersion:e.fromVersion||null}; });
  }

  function dataDateOf(p){
    if(isObj(p.source)&&p.source.dataDate) return String(p.source.dataDate).slice(0,10);
    if(p.scheduleDataDate) return String(p.scheduleDataDate).slice(0,10);
    var s=Array.isArray(p.sources)?p.sources.filter(function(x){ return isObj(x)&&x.dataDate; }):[];
    return s.length?String(s[0].dataDate).slice(0,10):null;
  }

  function summarise(p,fileName){
    p=isObj(p)?p:{};
    var userTasks=len(p.userTasks)||len(p.userMilestones);
    var s={
      fileName:fileName||'',
      savedAt:p.publishedAt||p.exportedAt||p.savedAt||null,
      savedBy:p.fromVersion||p.version||p.appVersion||null,
      projectNo:p.projectNo||'',
      reportTitle:p.reportTitle||'',
      dataDate:dataDateOf(p),
      sources:(Array.isArray(p.sources)?p.sources:[]).filter(isObj).map(function(x){ return x.name||x.file||'Schedule'; }),
      milestones:len(p.milestones),
      tasks:len(p.tasks),
      userTasks:userTasks,
      entries:len(p.entries),
      notes:len(p.notes),
      hasBaseline:isObj(p.baseline),
      chainLength:chainOf(p).length
    };
    s.empty=!s.milestones&&!s.tasks&&!s.userTasks&&!s.entries&&!s.notes&&
            !len(p.milestoneComments)&&!len(p.overrides);
    return s;
  }

  function check(p,ctx){
    ctx=ctx||{};
    var errors=[], warnings=[];
    if(!isObj(p)){ errors.push('The file does not contain a saved dashboard.'); return {errors:errors,warnings:warnings}; }
    var tl=p.timeline;
    var fullState=isObj(tl)&&Array.isArray(tl.labels)&&Array.isArray(tl.dates)&&tl.labels.length===tl.dates.length;
    if(!fullState){
      if(p.kind&&/milestone-dashboard-model$/.test(String(p.kind))&&!(isObj(tl)&&Array.isArray(tl.dates)))
        errors.push('This is an annotations export, not a whole dashboard. Mount it from Data and view, Sources, after importing the schedule.');
      else errors.push('The file does not contain a whole saved dashboard (no timeline).');
      return {errors:errors,warnings:warnings};
    }
    if(!Array.isArray(p.milestones)||!Array.isArray(p.tasks))
      errors.push('The saved dashboard is missing its schedule rows.');
    if(summarise(p).empty)
      errors.push('The saved dashboard is empty: no schedule, user tasks or notes to continue from.');
    var by=p.fromVersion||p.version||p.appVersion;
    if(ctx.appVersion&&by){
      var c=compareVersions(by,ctx.appVersion), bv=vparts(by), av=vparts(ctx.appVersion);
      if(c>0&&bv&&av&&bv[0]>av[0])
        errors.push('Saved by version '+by+', a newer major version than this copy ('+ctx.appVersion+'). Open it in that version.');
      else if(c>0)
        warnings.push('Saved by version '+by+', newer than this copy ('+ctx.appVersion+'). Anything this version does not know about will not load.');
      else if(c<0)
        warnings.push('Saved by version '+by+'. It will be brought up to '+ctx.appVersion+' when you save.');
    }
    return {errors:errors,warnings:warnings};
  }

  function read(text,fileName,ctx){
    var x=extractState(text);
    var out={ok:false,errors:[],warnings:[],format:x.format,payload:null,summary:null};
    if(x.error){ out.errors.push(x.error); return out; }
    var c=check(x.payload,ctx);
    out.errors=c.errors; out.warnings=c.warnings;
    out.summary=summarise(x.payload,fileName);
    if(!out.errors.length){ out.payload=x.payload; out.ok=true; }
    return out;
  }

  var api={read:read,extractState:extractState,summarise:summarise,check:check,
           chainOf:chainOf,compareVersions:compareVersions};
  root.SRETContinue=api;
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
})(typeof window!=='undefined'?window:(typeof globalThis!=='undefined'?globalThis:this));
