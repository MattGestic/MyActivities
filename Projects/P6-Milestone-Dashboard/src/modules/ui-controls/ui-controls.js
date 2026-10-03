/* ============================================================
   ui-controls (SRETControls): behaviour for stateful controls (D-32).
   Markup-first: the HTML carries the state in ARIA attributes; this
   module only keeps them in step with clicks and keys, and reports.

   API
     SRETControls.bind(rootEl) -> unbind()
        Delegated handling inside rootEl for:
          .ui-switch           aria-checked flips; emits 'ui-change' {value:boolean}
          .ui-segmented        radio group; arrow keys move; emits {value}
          .ui-radio-cards      same, for .ui-radio-card children
          .ui-chip[aria-pressed] toggles pressed; emits {value:boolean}
          .ui-chip__remove     emits 'ui-remove' on its chip, then removes it
     'ui-change' and 'ui-remove' bubble and carry detail.value / detail.id
     (the control's data-id or id).
   ============================================================ */
(function (root) {
  'use strict';
  function emit(el, type, value) {
    el.dispatchEvent(new CustomEvent(type, { bubbles: true, detail: { id: el.dataset.id || el.id || null, value: value } }));
  }
  function groupOf(el) { return el.closest('.ui-segmented, .ui-radio-cards'); }
  function optsOf(g) { return Array.prototype.slice.call(g.querySelectorAll('.ui-segmented__opt, .ui-radio-card')); }
  function choose(g, opt, focus) {
    optsOf(g).forEach(function (o) {
      var on = o === opt;
      o.setAttribute('aria-checked', String(on));
      o.tabIndex = on ? 0 : -1;
    });
    if (focus) opt.focus();
    emit(g, 'ui-change', opt.dataset.value || opt.textContent.trim());
  }
  function init(rootEl) {
    rootEl.querySelectorAll('.ui-segmented, .ui-radio-cards').forEach(function (g) {
      g.setAttribute('role', 'radiogroup');
      var os = optsOf(g), any = false;
      os.forEach(function (o) { o.setAttribute('role', 'radio'); if (o.getAttribute('aria-checked') === 'true') any = true; });
      os.forEach(function (o, i) { o.tabIndex = (o.getAttribute('aria-checked') === 'true' || (!any && i === 0)) ? 0 : -1; });
    });
    rootEl.querySelectorAll('.ui-switch').forEach(function (s) {
      s.setAttribute('role', 'switch');
      if (!s.hasAttribute('aria-checked')) s.setAttribute('aria-checked', 'false');
    });
  }
  function bind(rootEl) {
    init(rootEl);
    function onClick(e) {
      var rm = e.target.closest('.ui-chip__remove');
      if (rm && rootEl.contains(rm)) {
        var chip = rm.closest('.ui-chip');
        emit(chip, 'ui-remove', null);
        chip.remove();
        return;
      }
      var sw = e.target.closest('.ui-switch');
      if (sw && rootEl.contains(sw)) {
        var v = sw.getAttribute('aria-checked') !== 'true';
        sw.setAttribute('aria-checked', String(v));
        emit(sw, 'ui-change', v);
        return;
      }
      var opt = e.target.closest('.ui-segmented__opt, .ui-radio-card');
      if (opt && rootEl.contains(opt)) { choose(groupOf(opt), opt); return; }
      var chp = e.target.closest('.ui-chip[aria-pressed]');
      if (chp && rootEl.contains(chp)) {
        var p = chp.getAttribute('aria-pressed') !== 'true';
        chp.setAttribute('aria-pressed', String(p));
        emit(chp, 'ui-change', p);
      }
    }
    function onKey(e) {
      var opt = e.target.closest && e.target.closest('.ui-segmented__opt, .ui-radio-card');
      if (!opt) return;
      var g = groupOf(opt), os = optsOf(g), i = os.indexOf(opt), j = null;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') j = (i + 1) % os.length;
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') j = (i - 1 + os.length) % os.length;
      if (j !== null) { e.preventDefault(); choose(g, os[j], true); }
    }
    rootEl.addEventListener('click', onClick);
    rootEl.addEventListener('keydown', onKey);
    return function unbind() { rootEl.removeEventListener('click', onClick); rootEl.removeEventListener('keydown', onKey); };
  }
  var api = { bind: bind };
  root.SRETControls = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
