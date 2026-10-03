/* ============================================================
   ui-surfaces (SRETSurfaces): behaviour for the surface primitives (D-32).

   API
     SRETSurfaces.tabs(tablistEl, opts?) -> { select(id) }
        Wires a role=tablist of .ui-tab buttons (each aria-controls a
        .ui-tabpanel). Arrow Left/Right, Home and End move between tabs
        (APG tabs pattern, automatic activation). opts.onChange(id).
     SRETSurfaces.toast(text, opts?) -> void
        Shows a short message at the bottom centre for opts.ms (default
        3000). One region per page, created on first use.
   ============================================================ */
(function (root) {
  'use strict';
  function tabs(list, opts) {
    opts = opts || {};
    var btns = Array.prototype.slice.call(list.querySelectorAll('.ui-tab'));
    function select(id, focus) {
      btns.forEach(function (b) {
        var on = b.id === id || b.getAttribute('aria-controls') === id;
        b.setAttribute('aria-selected', String(on));
        b.tabIndex = on ? 0 : -1;
        var p = document.getElementById(b.getAttribute('aria-controls'));
        if (p) p.hidden = !on;
        if (on && focus) b.focus();
      });
      if (opts.onChange) opts.onChange(id);
    }
    list.setAttribute('role', 'tablist');
    btns.forEach(function (b, i) {
      b.setAttribute('role', 'tab');
      b.addEventListener('click', function () { select(b.id); });
      b.addEventListener('keydown', function (e) {
        var j = null;
        if (e.key === 'ArrowRight') j = (i + 1) % btns.length;
        else if (e.key === 'ArrowLeft') j = (i - 1 + btns.length) % btns.length;
        else if (e.key === 'Home') j = 0;
        else if (e.key === 'End') j = btns.length - 1;
        if (j !== null) { e.preventDefault(); select(btns[j].id, true); }
      });
    });
    var start = btns.filter(function (b) { return b.getAttribute('aria-selected') === 'true'; })[0] || btns[0];
    if (start) select(start.id);
    return { select: function (id) { select(id); } };
  }

  var region = null;
  function toast(text, opts) {
    opts = opts || {};
    if (!region) {
      region = document.createElement('div');
      region.className = 'ui-toast-region ui-root';
      region.setAttribute('role', 'status');
      region.setAttribute('aria-live', 'polite');
      document.body.appendChild(region);
    }
    var t = document.createElement('div');
    t.className = 'ui-toast';
    var s = document.createElement('span');
    s.className = 'ui-toast__text';
    s.textContent = text;
    t.appendChild(s);
    region.appendChild(t);
    requestAnimationFrame(function () { t.setAttribute('data-show', 'true'); });
    setTimeout(function () {
      t.setAttribute('data-show', 'false');
      setTimeout(function () { t.remove(); }, 260);
    }, opts.ms || 3000);
  }

  var api = { tabs: tabs, toast: toast };
  root.SRETSurfaces = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
