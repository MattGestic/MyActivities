#!/usr/bin/env python3
"""
Headless check for src/modules/notes-history (P66 update-history gallery).

Builds a harness page that inlines the app's token blocks (copied the way
grid_view_assemble.token_blocks() does), the module CSS and the module JS, runs
assertions in Chromium with the network unresolvable, and reads the DOM,
classList and computed styles back. No screenshots. Exit 1 on any failure.

Usage: python3 tools/notes_history_check.py
"""

import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import grid_view_assemble  # noqa: E402  (token_blocks)
import import_check        # noqa: E402  (find_chrome)

MOD = ROOT / "src" / "modules" / "notes-history"
CSS = MOD / "notes-history.css"
JS = MOD / "notes-history.js"

TESTS = r"""
(function(){
var R = [];
function t(name, ok, detail){ R.push({name:name, ok:!!ok, detail: ok ? '' : String(detail === undefined ? '' : detail)}); }
function $(root, sel){ return root.querySelector(sel); }
function $$(root, sel){ return Array.prototype.slice.call(root.querySelectorAll(sel)); }
function cs(el, p){ return getComputedStyle(el)[p]; }
function tok(name, prop){            // resolve a token to the computed rgb for a property
  var s = document.createElement('span'); s.style[prop || 'color'] = 'var(' + name + ')';
  document.body.appendChild(s); var v = getComputedStyle(s)[prop || 'color']; s.remove(); return v;
}
var H = window.SRETHistory;
function mk(y, m, d, hh, mm){ return new Date(y, m, d, hh, mm).toISOString(); }
var ctx = {currentPeriod:'P2',
  fmtDate:function(iso){ var p = iso.split('-'); return p[2] + '-' + ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][+p[1]-1] + '-' + p[0].slice(2); },
  healthLabel:function(c){ return {risk:'At risk', track:'On track'}[c] || c; }};
var entries = [
  {eid:'e2', target:{kind:'ms', key:'SNIP-110'}, text:'Lab results a week late. Confirm the revised MRE date with process.',
   changes:{progress:{from:45, to:60}, date:{from:'2026-10-29', to:'2026-11-12'}}, status:'sent',
   at:mk(2026,8,29,14,40), period:'P2', by:'M. Gray'},
  {eid:'e1', target:{kind:'ms', key:'SNIP-110'}, text:'', changes:{health:{from:'track', to:'risk'}}, status:'done',
   at:mk(2026,8,28,8,5), period:'P1', by:'M. Gray'},
  {eid:'e3', target:{kind:'ms', key:'SNIP-110'}, text:'Lab confirmed results due Fri 07-Nov. MRE date to follow.', changes:{},
   status:'open', at:mk(2026,9,1,8,0), updatedAt:mk(2026,9,1,9,12), period:'P2', by:'M. Gray'}
];

/* ---- view model ---- */
var v3 = H.entryView(entries[2], ctx), v2 = H.entryView(entries[0], ctx), v1 = H.entryView(entries[1], ctx);
t('view: when format from updatedAt', v3.when === 'Thu 01-Oct 09:12', v3.when);
t('view: who and followUp and fuClass', v3.who === 'M. Gray' && v3.followUp === 'Open' && v3.fuClass === 'nh-fu-open', JSON.stringify(v3));
t('view: canEdit default compares period', v3.canEdit === true && v1.canEdit === false, v3.canEdit + ',' + v1.canEdit);
t('view: ctx.canEdit overrides', H.entryView(entries[1], {currentPeriod:'P2', canEdit:function(){ return true; }}).canEdit === true);
t('view: labels in order, comment last', v2.changes.map(function(c){ return c.label; }).join('|') === 'Progress|End date|Comments', v2.changes.map(function(c){ return c.label; }));
t('view: values formatted', v2.changes[0].from === '45%' && v2.changes[0].to === '60%' && v2.changes[1].from === '29-Oct-26' && v2.changes[1].to === '12-Nov-26', JSON.stringify(v2.changes));
t('view: health via healthLabel', v1.changes[0].from === 'On track' && v1.changes[0].to === 'At risk', JSON.stringify(v1.changes));
var vn = H.entryView({eid:'x', changes:{start:{from:null, to:null}, weight:{from:2, to:3}, actName:{from:'A', to:'B'}, floatD:{from:1,to:2}, type:{from:'a',to:'b'}, marker:{from:'m',to:'n'}, status:{from:'s',to:'t'}}, text:'c', status:'review', at:mk(2026,9,1,9,0), period:'P2'}, ctx);
t('view: null from is none, null to is schedule value', vn.changes[1].from === 'none' && vn.changes[1].to === 'schedule value', JSON.stringify(vn.changes));
t('view: full field order and labels', vn.changes.map(function(c){ return c.label; }).join('|') === 'Status|Start date|Name|Weight|Float|Type|Mark|Comments', vn.changes.map(function(c){ return c.label; }));
t('view: review is In review, who hidden when empty', vn.followUp === 'In review' && vn.who === '', vn.followUp);
var vc = H.entryView({eid:'y', text:'old', clearText:true, changes:{}, status:'note', at:mk(2026,9,1,9,0)}, ctx);
t('view: clearText shows Remark cleared', vc.changes.length === 1 && vc.changes[0].text === 'Remark cleared' && vc.changes[0].isComment, JSON.stringify(vc.changes));
// P78: Discipline, Supervisor, Engineer: labelled, after the older fields, before the comment.
var vp = H.entryView({eid:'p78', changes:{engineer:{from:'P. Patel', to:null}, supervisor:{from:null, to:'J. Smith'}, discipline:{from:'Mining', to:'Process'}, weight:{from:1, to:2}},
  text:'who', status:'open', at:mk(2026,9,1,9,0), period:'P2'}, ctx);
t('P78: labels Discipline, Supervisor, Engineer, after the older fields', vp.changes.map(function(c){ return c.label; }).join('|') === 'Weight|Discipline|Supervisor|Engineer|Comments', vp.changes.map(function(c){ return c.label; }));
t('P78: Supervisor none -> J. Smith, and a clear reads schedule value', vp.changes[2].from === 'none' && vp.changes[2].to === 'J. Smith' && vp.changes[3].from === 'P. Patel' && vp.changes[3].to === 'schedule value' && vp.changes[1].from === 'Mining' && vp.changes[1].to === 'Process', JSON.stringify(vp.changes));
var bp = document.createElement('div'); bp.innerHTML = H.renderEntries([{eid:'p78b', changes:{supervisor:{from:null, to:'J. Smith'}}, text:'', status:'open', at:mk(2026,9,1,9,0), period:'P2'}], ctx);
t('P78: the DOM row reads "Supervisor none → J. Smith"', bp.querySelector('.nh-row').textContent.replace(/\s+/g, ' ').trim() === 'Supervisor none → J. Smith', bp.querySelector('.nh-row').textContent);
var labels = {note:'Note', open:'Open', sent:'Sent', review:'In review', outstanding:'Outstanding', done:'Done', closed:'Closed'};
t('view: status labels', Object.keys(labels).every(function(k){ return H.entryView({status:k}, ctx).followUp === labels[k]; }));

/* ---- entries DOM ---- */
var box = document.getElementById('box');
box.innerHTML = H.renderEntries(entries, ctx);
var els = $$(box, '.nh-entry');
t('entries: 3 render newest first', els.length === 3 && els.map(function(e){ return e.dataset.eid; }).join() === 'e3,e2,e1', els.map(function(e){ return e.dataset.eid; }));
t('entries: ties broken by eid, newer eid first', H.renderEntries([{eid:'e1', at:'2026-10-01T00:00:00Z'}, {eid:'e10', at:'2026-10-01T00:00:00Z'}, {eid:'e2', at:'2026-10-01T00:00:00Z'}], ctx).match(/data-eid="(e\d+)"/g).join() === 'data-eid="e10",data-eid="e2",data-eid="e1"');
var e2 = els[1];
t('entries: labels and order in DOM', $$(e2, '.nh-lbl').map(function(l){ return l.textContent; }).join('|') === 'Progress|End date|Comments');
var rows = $$(e2, '.nh-row');
t('entries: comment is last row and wraps', !!$(rows[rows.length-1], '.nh-text') && cs($(rows[rows.length-1], '.nh-text'), 'whiteSpace') === 'normal');
var from = $(e2, '.nh-from'), to = $(e2, '.nh-to'), arrow = $(e2, '.nh-arrow');
t('entries: from to renders with arrow', from.textContent === '45%' && arrow.textContent === '→' && to.textContent === '60%');
t('entries: from is muted, to is semibold primary', cs(from, 'color') === tok('--color-text-muted') && cs(to, 'color') === tok('--color-text-primary') && +cs(to, 'fontWeight') >= 600 && +cs(from, 'fontWeight') < 600, cs(from, 'color') + ' ' + cs(to, 'color') + ' ' + cs(to, 'fontWeight'));
t('entries: label is uppercase, small, letter-spaced', cs($(e2, '.nh-lbl'), 'textTransform') === 'uppercase' && parseFloat(cs($(e2, '.nh-lbl'), 'letterSpacing')) > 0);
t('entries: changes list has a 2px left rule', cs($(e2, '.nh-changes'), 'borderLeftWidth') === '2px' && cs($(e2, '.nh-changes'), 'borderLeftStyle') === 'solid');
t('entries: when is bold, who is muted', +cs($(e2, '.nh-when'), 'fontWeight') >= 600 && cs($(e2, '.nh-who'), 'color') === tok('--color-text-muted'));
var pens = $$(box, '.nh-edit');
t('pencil: exactly on the two editable entries', pens.length === 2 && !$(els[2], '.nh-edit') && !!$(els[0], '.nh-edit') && !!$(els[1], '.nh-edit'), pens.length);
t('pencil: a11y, type, 14px svg', pens.every(function(p){ var s = $(p, 'svg'); return p.getAttribute('aria-label') === 'Edit entry' && p.title === 'Edit entry' && p.type === 'button' && s.getAttribute('width') === '14' && s.getAttribute('height') === '14'; }));
t('pencil: right of the status pill', [0,1].every(function(i){ var p = $(els[i], '.nh-edit').getBoundingClientRect(), f = $(els[i], '.nh-fu').getBoundingClientRect(); return p.left >= f.right - 0.5 && Math.abs((p.top + p.bottom) / 2 - (f.top + f.bottom) / 2) < 4; }));
var hov = false, foc = false;
Array.prototype.forEach.call(document.styleSheets, function(ss){ Array.prototype.forEach.call(ss.cssRules, function(r){
  if (r.selectorText && r.selectorText.indexOf('.nh-edit:hover') >= 0 && /btn-icon-hover-bg/.test(r.cssText)) hov = true;
  if (r.selectorText && r.selectorText.indexOf('.nh-edit:focus-visible') >= 0 && /outline/.test(r.cssText)) foc = true; }); });
t('pencil: hover background rule and visible focus rule', hov && foc, hov + ',' + foc);
t('pill classes by status', $(els[0], '.nh-fu').classList.contains('nh-fu-open') && $(els[1], '.nh-fu').classList.contains('nh-fu-sent') && $(els[2], '.nh-fu').classList.contains('nh-fu-done'));
t('pill colours by role', cs($(els[0], '.nh-fu'), 'backgroundColor') === tok('--color-chip-attention-bg', 'backgroundColor') && cs($(els[0], '.nh-fu'), 'color') === tok('--color-chip-attention-ink') && cs($(els[1], '.nh-fu'), 'color') === tok('--color-accent-ink') && cs($(els[2], '.nh-fu'), 'color') === tok('--color-text-muted'));
t('pill is fully rounded', parseFloat(cs($(els[0], '.nh-fu'), 'borderTopLeftRadius')) > 50);

/* ---- edit round trip ---- */
var saves = [], h = {onSave:function(id, p){ saves.push([id, p]); }};
var unbind = H.bind(box, h);
var e3 = $(box, '.nh-entry[data-eid="e3"]');
$(e3, '.nh-edit').click();
var ta = $(e3, '.nh-ta'), sel = $(e3, '.nh-sel');
t('edit: editor opens with prefilled text and status', !!ta && ta.value === entries[2].text && sel.value === 'open', ta && ta.value);
t('edit: view hidden, textarea focused', $(e3, '.nh-changes').hidden && document.activeElement === ta);
var cancel = $(e3, '[data-act="cancel"]'), save = $(e3, '[data-act="save"]');
t('edit: Cancel left of Save, Save primary', cancel.getBoundingClientRect().right <= save.getBoundingClientRect().left && save.classList.contains('nh-btn-primary') && !cancel.classList.contains('nh-btn-primary'));
t('edit: buttons typed and labelled', [cancel, save].every(function(b){ return b.type === 'button' && !!b.getAttribute('aria-label'); }) && !!ta.getAttribute('aria-label') && !!sel.getAttribute('aria-label'));
t('edit: select lists all seven statuses', $$(sel, 'option').map(function(o){ return o.value; }).join() === 'note,open,sent,review,outstanding,done,closed');
t('edit: primary button uses button tokens', cs(save, 'backgroundColor') === tok('--color-btn-primary-bg', 'backgroundColor'));
cancel.click();
t('edit: Cancel restores the view', !$(e3, '.nh-editor') && !$(e3, '.nh-changes').hidden && !$(e3, '.nh-edit').hidden && saves.length === 0);
$(e3, '.nh-edit').click(); ta = $(e3, '.nh-ta');
ta.value = 'New text'; $(e3, '.nh-sel').value = 'done';
$(e3, '[data-act="save"]').click();
t('edit: Save calls onSave(eid, {text, status})', saves.length === 1 && saves[0][0] === 'e3' && saves[0][1].text === 'New text' && saves[0][1].status === 'done', JSON.stringify(saves));
t('edit: view restored after Save', !$(e3, '.nh-editor') && !$(e3, '.nh-changes').hidden);
$(e3, '.nh-edit').click(); ta = $(e3, '.nh-ta'); ta.value = 'Changed';
ta.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}));
t('edit: Esc cancels without saving', !$(e3, '.nh-editor') && !$(e3, '.nh-changes').hidden && saves.length === 1);
$(e3, '.nh-edit').click(); ta = $(e3, '.nh-ta'); ta.value = 'Via keys';
ta.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', ctrlKey:true, bubbles:true}));
t('edit: Ctrl+Enter saves', saves.length === 2 && saves[1][1].text === 'Via keys' && !$(e3, '.nh-editor'), JSON.stringify(saves));
unbind();
$(e3, '.nh-edit').click();
t('bind: unbind removes the listener', !$(e3, '.nh-editor'));

/* ---- escaping ---- */
var evil = '<img src=x onerror="window.__pwn=1"><b>bold</b> & "q"';
box.innerHTML = H.renderEntries([{eid:'<i>1', text:evil, by:'<u>me</u>', changes:{actName:{from:'<s>a</s>', to:'<s>b</s>'}}, status:'open', at:mk(2026,9,1,9,0), period:'P2'}], ctx);
t('escape: entry text, by, values, eid are inert', !$(box, 'img') && !$(box, 'b') && !$(box, 'u') && !$(box, 's') && !$(box, 'i') && !window.__pwn && $(box, '.nh-text').textContent === evil && $(box, '.nh-who').textContent === '<u>me</u>', box.innerHTML);
var gh = H.renderGroups([{key:'k', id:'<b>X</b>', name:'<i>n</i>', summary:'<u>s</u>', count:1, open:true, entries:[]}], ctx);
box.innerHTML = gh;
t('escape: group id, name, summary are inert', !$(box, 'b') && !$(box, 'i') && !$(box, 'u'));

/* ---- groups ---- */
var groups = [
  {key:'SNIP-110', id:'SNIP-110', name:'Lab results and revised MRE date for the flotation testwork programme', summary:'Finish 12-Nov-26 · At risk · 60%', count:3, open:true, entries:entries},
  {key:'SNIP-121', id:'SNIP-121', name:'Process Design Criteria', summary:'Finish 30-Nov-26 · On track · 10%', count:1, open:false, entries:[entries[0]]},
  {key:'general', id:'', name:'General', summary:'', count:1, open:true, entries:[{eid:'g1', text:'General note', status:'note', at:mk(2026,9,1,9,0), period:'P2', changes:{}}]}
];
var gbox = document.getElementById('gbox');
gbox.innerHTML = H.renderGroups(groups, ctx);
var ev = {toggle:[], ms:[], saves:[]};
H.bind(gbox, {onToggleGroup:function(k, o){ ev.toggle.push([k, o]); }, onOpenMilestone:function(k){ ev.ms.push(k); }, onSave:function(i, p){ ev.saves.push([i, p]); }});
var gs = $$(gbox, '.nh-group');
t('groups: three groups with headings', gs.length === 3 && $$(gbox, '.nh-ghead').length === 3);
var g1 = gs[0];
t('groups: heading id (mono) and name on one line', $(g1, '.nh-gid').textContent === 'SNIP-110' && /mono|Mono/.test(cs($(g1, '.nh-gid'), 'fontFamily')) && Math.abs($(g1, '.nh-gid').getBoundingClientRect().top - $(g1, '.nh-gname').getBoundingClientRect().top) < 8);
t('groups: name ellipsis on overflow', cs($(g1, '.nh-gname'), 'textOverflow') === 'ellipsis' && cs($(g1, '.nh-gname'), 'whiteSpace') === 'nowrap' && $(g1, '.nh-gname').scrollWidth > $(g1, '.nh-gname').clientWidth);
t('groups: summary line under the heading line', $(g1, '.nh-gsum').textContent === 'Finish 12-Nov-26 · At risk · 60%' && $(g1, '.nh-gsum').getBoundingClientRect().top >= $(g1, '.nh-gline').getBoundingClientRect().bottom - 1);
t('groups: count on the right', $(g1, '.nh-gcount').textContent === '3' && $(g1, '.nh-gcount').getBoundingClientRect().left > $(g1, '.nh-gtitle').getBoundingClientRect().left);
t('groups: entries render inside, newest first', $$(g1, '.nh-entry').map(function(e){ return e.dataset.eid; }).join() === 'e3,e2,e1');
t('groups: collapsed group body hidden and not displayed', gs[1].querySelector('.nh-gbody').hidden && cs(gs[1].querySelector('.nh-gbody'), 'display') === 'none' && $(gs[1], '.nh-gchev').getAttribute('aria-expanded') === 'false');
t('groups: chevron is a typed labelled button', $$(gbox, '.nh-gchev, .nh-gid').every(function(b){ return b.type === 'button' && !!b.getAttribute('aria-label'); }));
var chev = $(g1, '.nh-gchev');
var openRot = cs($(chev, 'svg'), 'transform');
chev.click();
t('groups: click collapses and calls onToggleGroup(key, false)', $(g1, '.nh-gbody').hidden && !chev.classList.contains('is-open') && chev.getAttribute('aria-expanded') === 'false' && ev.toggle.length === 1 && ev.toggle[0].join() === 'SNIP-110,false', JSON.stringify(ev.toggle));
$(g1, '.nh-ghead').click();
t('groups: heading click reopens, onToggleGroup(key, true)', !$(g1, '.nh-gbody').hidden && chev.classList.contains('is-open') && chev.getAttribute('aria-expanded') === 'true' && ev.toggle[1].join() === 'SNIP-110,true', JSON.stringify(ev.toggle));
t('groups: open chevron rotated like the design toggle', cs($(chev, 'svg'), 'transform') !== 'none' && openRot !== 'none');
$(g1, '.nh-gid').click();
t('groups: id click opens milestone and does not toggle', ev.ms.join() === 'SNIP-110' && ev.toggle.length === 2 && !$(g1, '.nh-gbody').hidden, JSON.stringify(ev));
$(gs[1], '.nh-gchev').click();
t('groups: a collapsed group expands', !$(gs[1], '.nh-gbody').hidden && ev.toggle[2].join() === 'SNIP-121,true');
t('groups: General has no id button, is openable and editable', !$(gs[2], '.nh-gid') && $(gs[2], '.nh-gname').textContent === 'General' && $$(gs[2], '.nh-entry').length === 1);
$(gs[2], '.nh-edit').click(); $(gs[2], '.nh-ta').value = 'Edited general'; $(gs[2], '[data-act="save"]').click();
t('groups: save inside a group routes to onSave', ev.saves.length === 1 && ev.saves[0][0] === 'g1' && ev.saves[0][1].text === 'Edited general', JSON.stringify(ev.saves));
$(gs[2], '.nh-ghead').click();
t('groups: General collapses and calls onToggleGroup', ev.toggle[3].join() === 'general,false' && $(gs[2], '.nh-gbody').hidden);
t('groups: empty group shows none', /none/.test(H.renderGroups([{key:'a', id:'A', name:'n', count:0, open:true, entries:[]}], ctx)));

/* ---- themes ---- */
function snap(){
  gbox.innerHTML = H.renderGroups(groups, ctx);
  var e = $(gbox, '.nh-entry[data-eid="e2"]');
  var sent = $(e, '.nh-fu'), open = $(gbox, '.nh-entry[data-eid="e3"] .nh-fu');
  return {when: cs($(e, '.nh-when'), 'color'), to: cs($(e, '.nh-to'), 'color'), from: cs($(e, '.nh-from'), 'color'),
    sentFg: cs(sent, 'color'), sentBg: cs(sent, 'backgroundColor'), openFg: cs(open, 'color'), openBg: cs(open, 'backgroundColor'),
    rule: cs($(e, '.nh-changes'), 'borderLeftColor')};
}
document.documentElement.setAttribute('data-theme', 'light'); var L = snap();
document.documentElement.setAttribute('data-theme', 'dark'); var D = snap();
document.documentElement.setAttribute('data-theme', 'light');
t('theme: primary text colour differs light vs dark', L.when !== D.when && L.to !== D.to, L.when + ' ' + D.when);
t('theme: muted text and rule differ', L.from !== D.from && L.rule !== D.rule);
t('theme: Sent pill colour and background differ', L.sentFg !== D.sentFg && L.sentBg !== D.sentBg, JSON.stringify([L.sentFg, D.sentFg, L.sentBg, D.sentBg]));
t('theme: Open pill background differs', L.openBg !== D.openBg, L.openBg + ' ' + D.openBg);

/* ---- 360px panel ---- */
var panel = document.getElementById('panel');
panel.style.width = '360px';
var longEntry = {eid:'long', text:'Averyveryverylongunbrokenwordaververyverylongunbrokenwordaveryveryverylongunbrokenwordaveryveryverylongunbrokenword https://example.invalid/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', by:'A Very Long User Name Indeed', status:'outstanding',
  changes:{actName:{from:'A long previous activity name that needs wrapping somewhere sensible', to:'Another long replacement activity name that needs wrapping too'}}, at:mk(2026,9,1,9,0), period:'P2'};
panel.innerHTML = H.renderGroups([groups[0], {key:'L', id:'SNIP-999999', name:groups[0].name, summary:groups[0].summary + ' and a very long roll up summary line', count:1234, open:true, entries:[longEntry]}], ctx);
H.bind(panel, {});
$(panel, '.nh-entry[data-eid="long"] .nh-edit').click();
var pr = panel.getBoundingClientRect(), over = [];
$$(panel, '*').forEach(function(el){ if (el.hidden) return; var r = el.getBoundingClientRect(); if (r.width && r.right > pr.right + 0.5) over.push(el.className + ' ' + r.right); });
t('layout: no horizontal overflow at 360px', panel.scrollWidth <= 360 && over.length === 0, panel.scrollWidth + ' ' + over.join(';'));

document.getElementById('out').textContent = JSON.stringify(R);
})();
"""


def build_harness() -> str:
    css = CSS.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    return ("<!doctype html><html data-theme=\"light\"><head><meta charset=\"utf-8\"><style>\n"
            + grid_view_assemble.token_blocks() + "\nbody{background:var(--color-bg-elevated);color:var(--color-text-primary);font-family:var(--font-sans)}\n"
            + css + "\n</style></head><body>\n"
            "<div id=\"box\" style=\"width:460px\"></div><div id=\"gbox\" style=\"width:460px\"></div>"
            "<div id=\"panel\"></div><pre id=\"out\"></pre>\n<script>\n" + js + "\n</script>\n<script>\n"
            + TESTS + "\n</script></body></html>")


def static_checks():
    res = []
    bad_col = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
    for p in (CSS, JS):
        txt = p.read_text(encoding="utf-8")
        hits = bad_col.findall(txt)
        res.append({"name": f"static: no literal colours in {p.name}", "ok": not hits, "detail": str(hits[:5])})
        fb = re.findall(r"var\(--[\w-]+\s*,", txt)
        res.append({"name": f"static: no var() fallbacks in {p.name}", "ok": not fb, "detail": str(fb[:5])})
        res.append({"name": f"static: no em dash in {p.name}", "ok": "—" not in txt and "\\u2014" not in txt, "detail": ""})
    js = JS.read_text(encoding="utf-8")
    res.append({"name": "static: IIFE sets SRETHistory and module.exports",
                "ok": "root.SRETHistory" in js and "module.exports" in js and js.lstrip().startswith("/*") and "(function(root){" in js,
                "detail": ""})
    return res


def main() -> int:
    results = static_checks()
    with tempfile.TemporaryDirectory() as td:
        page = pathlib.Path(td) / "notes_history_harness.html"
        page.write_text(build_harness(), encoding="utf-8")
        proc = subprocess.run(
            [import_check.find_chrome(), "--no-sandbox", "--disable-gpu",
             "--host-resolver-rules=MAP * ~NOTFOUND", "--virtual-time-budget=8000",
             "--window-size=900,1200", "--dump-dom", page.as_uri()],
            capture_output=True, text=True, timeout=120)
    m = re.search(r'<pre id="out">(.*?)</pre>', proc.stdout, re.S)
    if not m or not m.group(1).strip():
        print("Harness produced no result: the page threw before finishing.\n" + proc.stderr[-2000:])
        return 1
    raw = (m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))
    results += json.loads(raw)
    fails = 0
    for r in results:
        print(("PASS  " if r["ok"] else "FAIL  ") + r["name"] + ("" if r["ok"] else "  -> " + r["detail"]))
        fails += 0 if r["ok"] else 1
    print(f"\n{len(results) - fails}/{len(results)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
