/* =====================================================================
   SRET notes history gallery (P66, Matt). No app globals.

   The "Update history" block of the milestone dialog (docs/mockups/P66),
   reused in the Notes panel grouped per milestone. Pure view-model and
   string renderers plus one delegated listener; the host owns the data and
   re-renders after a save.

   API (window.SRETHistory):
     entryView(entry, ctx)      -> {eid, when, who, followUp, fuClass, canEdit, status,
                                    text, changes:[{label, isComment, text, from, to}]}
     renderEntries(entries, ctx)-> HTML string, newest first (by at, then eid)
     renderGroups(groups, ctx)  -> HTML string; group = {key, id, name, summary, count,
                                    open, entries}
     bind(container, handlers)  -> unbind function. handlers: onSave(eid,{text,status}),
                                    onToggleGroup(key, open), onOpenMilestone(key)
     ctx = {currentPeriod, fmtDate(iso), healthLabel(code), canEdit(entry)?}
   ===================================================================== */
(function(root){
  'use strict';

  var FIELDS = [['status','Status'],['health','Health'],['progress','Progress'],
    ['date','End date'],['start','Start date'],['actName','Name'],['weight','Weight'],
    ['floatD','Float'],['type','Type'],['marker','Mark'],
    ['startActual','Start date is'],['actual','End date is']];
  var STATUS_LABEL = {note:'Note', open:'Open', sent:'Sent', review:'In review',
    outstanding:'Outstanding', done:'Done', closed:'Closed'};
  var STATUS_ORDER = ['note','open','sent','review','outstanding','done','closed'];
  var DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  function esc(s){
    return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }
  function pad2(n){ return (n < 10 ? '0' : '') + n; }
  function norm(status){
    var s = String(status || 'note').toLowerCase();
    if (s === 'pending') s = 'review';
    return STATUS_LABEL[s] ? s : 'note';
  }
  function atMs(v){
    if (typeof v === 'number') return v;
    var t = Date.parse(v);
    return isNaN(t) ? 0 : t;
  }
  function whenText(v){
    var d = new Date(atMs(v));
    if (isNaN(d.getTime())) return 'none';
    return DAYS[d.getDay()] + ' ' + pad2(d.getDate()) + '-' + MONTHS[d.getMonth()] + ' ' +
      pad2(d.getHours()) + ':' + pad2(d.getMinutes());
  }
  function fmtValue(field, v, ctx){
    if (v == null) return 'none';
    if (field === 'date' || field === 'start') return ctx && ctx.fmtDate ? String(ctx.fmtDate(v)) : String(v);
    if (field === 'progress'){
      var s = String(v);
      return /%$/.test(s) ? s : s + '%';
    }
    if (field === 'health') return ctx && ctx.healthLabel ? String(ctx.healthLabel(v)) : String(v);
    if (field === 'actual' || field === 'startActual') return v ? 'Actual' : 'Forecast';
    return String(v);
  }

  function entryView(entry, ctx){
    entry = entry || {}; ctx = ctx || {};
    var ch = entry.changes || {}, changes = [], done = {}, i, k;
    function addDelta(key, label){
      var c = ch[key];
      if (!c) return;
      done[key] = true;
      changes.push({label: label, isComment: false,
        from: fmtValue(key, c.from, ctx),
        to: c.to == null ? 'schedule value' : fmtValue(key, c.to, ctx)});
    }
    for (i = 0; i < FIELDS.length; i++) addDelta(FIELDS[i][0], FIELDS[i][1]);
    for (k in ch) if (Object.prototype.hasOwnProperty.call(ch, k) && !done[k]) addDelta(k, k);
    if (entry.clearText) changes.push({label:'Comments', isComment:true, text:'Remark cleared'});
    else if (entry.text) changes.push({label:'Comments', isComment:true, text:String(entry.text)});
    var status = norm(entry.status);
    return {
      eid: entry.eid,
      when: whenText(entry.updatedAt || entry.at),
      who: entry.by || '',
      followUp: STATUS_LABEL[status],
      fuClass: 'nh-fu-' + status,
      status: status,
      text: entry.text || '',
      canEdit: ctx.canEdit ? !!ctx.canEdit(entry) : entry.period === ctx.currentPeriod,
      changes: changes
    };
  }

  var PENCIL = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" ' +
    'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M9.5 2.5l2 2L5 11l-2.8.8L3 9z"></path></svg>';
  var CHEVRON = '<svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" ' +
    'stroke-width="1.5" aria-hidden="true"><path d="M3.5 2l3 3-3 3"></path></svg>';

  function entryHtml(v){
    var h = '<div class="nh-entry" data-eid="' + esc(v.eid) + '" data-status="' + esc(v.status) +
      '" data-text="' + esc(v.text) + '">' +
      '<div class="nh-head"><span class="nh-meta"><span class="nh-when">' + esc(v.when) + '</span>' +
      (v.who ? ' <span class="nh-who">' + esc(v.who) + '</span>' : '') + '</span> ' +
      '<span class="nh-right"><span class="nh-fu ' + v.fuClass + '">' + esc(v.followUp) + '</span>' +
      (v.canEdit ? ' <button type="button" class="nh-edit" data-act="edit" aria-label="Edit entry" title="Edit entry">' + PENCIL + '</button>' : '') +
      '</span></div><div class="nh-changes">';
    for (var i = 0; i < v.changes.length; i++){
      var c = v.changes[i];
      // Real spaces between the parts (P72): ignored by the grid and flex
      // layout, but the row still reads "Health none → Done" if a viewer
      // shows it without the stylesheet.
      h += '<div class="nh-row"><span class="nh-lbl">' + esc(c.label) + '</span> ';
      if (c.isComment) h += '<span class="nh-text">' + esc(c.text) + '</span>';
      else h += '<span class="nh-delta"><span class="nh-from">' + esc(c.from) + '</span>' +
        ' <span class="nh-arrow">→</span> <span class="nh-to">' + esc(c.to) + '</span></span>';
      h += '</div>';
    }
    return h + '</div></div>';
  }

  function eidCmp(a, b){
    var na = parseInt(String(a).replace(/\D+/g,''), 10), nb = parseInt(String(b).replace(/\D+/g,''), 10);
    if (!isNaN(na) && !isNaN(nb) && na !== nb) return na - nb;
    return String(a) < String(b) ? -1 : String(a) > String(b) ? 1 : 0;
  }
  function renderEntries(entries, ctx){
    var list = (entries || []).slice().sort(function(a, b){
      return atMs(b.at) - atMs(a.at) || eidCmp(b.eid, a.eid);
    });
    var h = '';
    for (var i = 0; i < list.length; i++) h += entryHtml(entryView(list[i], ctx));
    return h;
  }

  function renderGroups(groups, ctx){
    var h = '';
    (groups || []).forEach(function(g){
      var open = !!g.open, label = (g.id ? g.id + ' ' : '') + (g.name || '');
      h += '<section class="nh-group" data-gkey="' + esc(g.key) + '">' +
        '<div class="nh-ghead" data-gkey="' + esc(g.key) + '">' +
        '<button type="button" class="nh-gchev' + (open ? ' is-open' : '') + '" data-act="toggle" aria-expanded="' + open +
        '" aria-label="' + (open ? 'Collapse ' : 'Expand ') + esc(label) + '">' + CHEVRON + '</button>' +
        '<span class="nh-gtitle"><span class="nh-gline">' +
        (g.id ? '<button type="button" class="nh-gid" data-act="open-ms" aria-label="Open milestone ' + esc(g.id) + '">' + esc(g.id) + '</button>' : '') +
        '<span class="nh-gname">' + esc(g.name) + '</span></span>' +
        (g.summary ? '<span class="nh-gsum">' + esc(g.summary) + '</span>' : '') + '</span>' +
        '<span class="nh-gcount">' + esc(g.count != null ? g.count : (g.entries || []).length) + '</span></div>' +
        '<div class="nh-gbody"' + (open ? '' : ' hidden') + '>' +
        ((g.entries && g.entries.length) ? renderEntries(g.entries, ctx) : '<div class="nh-empty">none</div>') +
        '</div></section>';
    });
    return h;
  }

  function editorHtml(status, text){
    var opts = '';
    STATUS_ORDER.forEach(function(s){
      opts += '<option value="' + s + '"' + (s === status ? ' selected' : '') + '>' + STATUS_LABEL[s] + '</option>';
    });
    return '<div class="nh-editor">' +
      '<textarea class="nh-ta" aria-label="Entry text">' + esc(text) + '</textarea>' +
      '<div class="nh-fuwrap"><span class="nh-lbl">Follow-up</span>' +
      '<select class="nh-sel" aria-label="Follow-up status">' + opts + '</select></div>' +
      '<div class="nh-actions"><button type="button" class="nh-btn" data-act="cancel" aria-label="Cancel edit">Cancel</button> ' +
      '<button type="button" class="nh-btn nh-btn-primary" data-act="save" aria-label="Save entry">Save</button></div></div>';
  }

  function bind(container, handlers){
    handlers = handlers || {};
    function closeEditor(entryEl){
      var ed = entryEl.querySelector('.nh-editor');
      if (ed) ed.parentNode.removeChild(ed);
      var ch = entryEl.querySelector('.nh-changes'), pen = entryEl.querySelector('.nh-edit');
      if (ch) ch.hidden = false;
      if (pen){ pen.hidden = false; pen.focus(); }
      entryEl.classList.remove('nh-editing');
    }
    function openEditor(entryEl){
      if (entryEl.querySelector('.nh-editor')) return;
      var ch = entryEl.querySelector('.nh-changes'), pen = entryEl.querySelector('.nh-edit');
      ch.hidden = true; if (pen) pen.hidden = true;
      entryEl.classList.add('nh-editing');
      ch.insertAdjacentHTML('afterend', editorHtml(entryEl.getAttribute('data-status'), entryEl.getAttribute('data-text')));
      var ta = entryEl.querySelector('.nh-ta');
      ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
    }
    function save(entryEl){
      var text = entryEl.querySelector('.nh-ta').value, status = entryEl.querySelector('.nh-sel').value;
      closeEditor(entryEl);
      if (handlers.onSave) handlers.onSave(entryEl.getAttribute('data-eid'), {text: text, status: status});
    }
    function onClick(e){
      var t = e.target.closest ? e.target.closest('[data-act], .nh-ghead') : null;
      if (!t || !container.contains(t)) return;
      var act = t.getAttribute('data-act'), entryEl = t.closest('.nh-entry');
      if (act === 'edit') openEditor(entryEl);
      else if (act === 'cancel') closeEditor(entryEl);
      else if (act === 'save') save(entryEl);
      else if (act === 'open-ms'){
        if (handlers.onOpenMilestone) handlers.onOpenMilestone(t.closest('.nh-ghead').getAttribute('data-gkey'));
      } else if (act === 'toggle' || t.classList.contains('nh-ghead')){
        var head = t.closest('.nh-ghead'), grp = head.parentNode;
        var body = grp.querySelector('.nh-gbody'), chev = head.querySelector('.nh-gchev');
        var open = body.hidden;           // was closed, so it opens now
        body.hidden = !open;
        chev.classList.toggle('is-open', open);
        chev.setAttribute('aria-expanded', String(open));
        chev.setAttribute('aria-label', chev.getAttribute('aria-label').replace(/^(Collapse|Expand)/, open ? 'Collapse' : 'Expand'));
        if (handlers.onToggleGroup) handlers.onToggleGroup(head.getAttribute('data-gkey'), open);
      }
    }
    function onKey(e){
      var ed = e.target.closest ? e.target.closest('.nh-editor') : null;
      if (!ed) return;
      var entryEl = ed.closest('.nh-entry');
      if (e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); closeEditor(entryEl); }
      else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)){ e.preventDefault(); e.stopPropagation(); save(entryEl); }
    }
    container.addEventListener('click', onClick);
    container.addEventListener('keydown', onKey);
    return function unbind(){
      container.removeEventListener('click', onClick);
      container.removeEventListener('keydown', onKey);
    };
  }

  var api = {entryView: entryView, renderEntries: renderEntries, renderGroups: renderGroups, bind: bind};
  root.SRETHistory = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
