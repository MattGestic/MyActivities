/* =====================================================================
   SRET stored-key migration (Matt, 2026-09-28). No UI, no app globals.

   "User milestones" are renamed "user tasks" everywhere, including the
   keys and values saved in files, so names and storage stay in sync. Files
   saved before the rename still open: every load path runs its payload
   through here first, which rewrites the old keys and values to the new
   ones. Saving always writes the new names only.

     payload key    userMilestones          -> userTasks
     payload key    userMsEnabled           -> userTasksEnabled
     source value   'User-defined'          -> 'User tasks'   (sourceSchedule / source)
     band value     'User Defined Milestones' -> 'User Tasks' (row notes / band)
     setting        sret-ws-section 'userms' -> 'usertasks'
     export sheet   'User-defined'          -> 'User tasks'

   Pure and idempotent: a payload already in the new names comes back
   unchanged, with nothing reported. The input is never mutated.

   API (window.SRETMigrate):
     userTasks(payload)   -> {payload, changed:[...notes], conflicts:[...notes]}
     value(v)             -> the new value for an old source or band value, else v
     wsSection(v)         -> 'usertasks' for 'userms', else v
     sheetName(name)      -> true when name is the user tasks sheet, old or new
     KEYS                 -> the tables above
   ===================================================================== */
(function(root){
  'use strict';
  var KEYS={
    payload:{userMilestones:'userTasks',userMsEnabled:'userTasksEnabled'},
    values:{'User-defined':'User tasks','User Defined Milestones':'User Tasks'},
    wsSection:{userms:'usertasks'},
    sheet:{old:'User-defined',now:'User tasks'}
  };
  // Fields that carry a source or band value, on tasks, rows and milestones.
  var VALUE_FIELDS=['source','sourceSchedule','notes','band'];

  function clone(x){ return x==null?x:JSON.parse(JSON.stringify(x)); }
  function value(v){ return typeof v==='string'&&Object.prototype.hasOwnProperty.call(KEYS.values,v)?KEYS.values[v]:v; }
  function wsSection(v){ return KEYS.wsSection[v]||v; }
  function sheetName(n){ var s=String(n||'').trim().toLowerCase(); return s===KEYS.sheet.old.toLowerCase()||s===KEYS.sheet.now.toLowerCase(); }

  function fixRecords(list,where,changed){
    var n=0;
    (list||[]).forEach(function(r){
      if(!r||typeof r!=='object') return;
      VALUE_FIELDS.forEach(function(f){ var v=value(r[f]); if(v!==r[f]){ r[f]=v; n++; } });
    });
    if(n) changed.push(where+': '+n+' value'+(n===1?'':'s')+' renamed');
  }
  function userTasks(payload){
    var out={payload:payload,changed:[],conflicts:[]};
    if(!payload||typeof payload!=='object') return out;
    var p=clone(payload);
    Object.keys(KEYS.payload).forEach(function(oldK){
      var newK=KEYS.payload[oldK];
      if(!(oldK in p)) return;
      if(newK in p) out.conflicts.push('Both '+oldK+' and '+newK+' present; kept '+newK+'.');
      else { p[newK]=p[oldK]; out.changed.push(oldK+' -> '+newK); }
      delete p[oldK];
    });
    fixRecords(p.userTasks,'userTasks',out.changed);
    fixRecords(p.userRows,'userRows',out.changed);
    fixRecords(p.tasks,'tasks',out.changed);
    fixRecords(p.milestones,'milestones',out.changed);
    // Registered sources (publish state) carry the source name too.
    (p.sources||[]).forEach(function(s){ if(s&&typeof s==='object'){ var v=value(s.name); if(v!==s.name){ s.name=v; out.changed.push('sources: '+s.id+' renamed'); } } });
    out.payload=out.changed.length||out.conflicts.length?p:payload;
    return out;
  }

  root.SRETMigrate={userTasks:userTasks,value:value,wsSection:wsSection,sheetName:sheetName,KEYS:KEYS};
})(window);
