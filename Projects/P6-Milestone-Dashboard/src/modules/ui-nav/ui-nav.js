/* ============================================================
   ui-nav (SRETNav): generic left navigation panel (D-31).
   Renders from a config object; knows nothing about the app's data.
   Selecting an item calls back to the host; the host decides what opens.

   Config
     {
       ariaLabel: 'Main',
       brand:  { title, subtitle?, icon? },             // icon: SRETIcons name
       groups: [ { id, label?, collapsible?, collapsed?,
                   items: [ { id, label, icon?, badge?: {value, tone?}, sub? } ] } ],
       footer: [ { id, label, icon, badge? } ],          // pinned to the bottom
       collapseControl: true                             // adds Collapse/Expand
     }
     badge.tone: neutral (default) | warn | danger | accent

   API
     SRETNav.mount(hostEl, config, opts) -> nav
        opts.active            id of the current item
        opts.onSelect(id, item)
        opts.onCollapseToggle()   the Collapse/Expand control was pressed
        opts.onClose()            the drawer close button was pressed
        opts.shell             an element with class ui-shell to follow
                               (mode and context come from its ui-shell:change)
     nav.setActive(id)
     nav.setBadge(id, badge|null)
     nav.setMode('expanded'|'rail')     when not following a shell
     nav.setContext('docked'|'overlay'|'drawer')
     nav.update(config)
     nav.el, nav.destroy()
   Keyboard: Arrow Up/Down and Home/End move between items; Enter/Space select.
   Rail mode shows each label as a tooltip on hover and keyboard focus.
   ============================================================ */
(function (root) {
  'use strict';
  function icon(n) { return root.SRETIcons ? root.SRETIcons.svg(n) : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function badgeHtml(b) {
    if (!b || b.value == null || b.value === '') return '';
    return '<span class="ui-nav__badge" data-tone="' + esc(b.tone || 'neutral') + '">' + esc(b.value) + '</span>';
  }
  function itemHtml(it, active) {
    return '<button type="button" class="ui-nav__item' + (it.sub ? ' ui-nav__item--sub' : '') + '" data-id="' + esc(it.id) + '" data-label="' + esc(it.label) + '"' +
      (it.id === active ? ' aria-current="page"' : '') + '>' +
      icon(it.icon || 'list') + '<span class="ui-nav__text">' + esc(it.label) + '</span>' + badgeHtml(it.badge) + '</button>';
  }
  function render(cfg, active, mode) {
    var b = cfg.brand || {};
    var h = '<div class="ui-nav__brand"><span class="ui-nav__mark">' + icon(b.icon || 'diamond') + '</span>' +
      '<span class="ui-nav__brand-text"><span class="ui-nav__brand-title">' + esc(b.title || '') + '</span>' +
      (b.subtitle ? '<span class="ui-nav__brand-sub">' + esc(b.subtitle) + '</span>' : '') + '</span>' +
      '<button type="button" class="ui-btn ui-btn--ghost ui-btn--icon ui-nav__close" data-act="close" aria-label="Close navigation">' + icon('close') + '</button></div>';
    h += '<div class="ui-nav__scroll">';
    (cfg.groups || []).forEach(function (g, gi) {
      if (gi > 0 && g.divider !== false) h += '<div class="ui-nav__divider" role="presentation"></div>';
      var gid = 'ui-nav-g-' + esc(g.id || gi);
      h += '<div class="ui-nav__group" data-group="' + esc(g.id || gi) + '" data-collapsed="' + (!!g.collapsed) + '">';
      if (g.label) {
        h += g.collapsible
          ? '<button type="button" class="ui-nav__label" data-act="group" aria-expanded="' + (!g.collapsed) + '" aria-controls="' + gid + '"><span>' + esc(g.label) + '</span>' + icon('chevronDown') + '</button>'
          : '<div class="ui-nav__label"><span>' + esc(g.label) + '</span></div>';
      }
      h += '<div class="ui-nav__items" id="' + gid + '"><div>' + (g.items || []).map(function (it) { return itemHtml(it, active); }).join('') + '</div></div></div>';
    });
    h += '</div>';
    var foot = (cfg.footer || []).map(function (it) { return itemHtml(it, active); }).join('');
    if (cfg.collapseControl !== false) {
      var rail = mode === 'rail';
      foot += '<button type="button" class="ui-nav__item ui-nav__collapse" data-act="collapse" data-label="' + (rail ? 'Expand' : 'Collapse') + '" aria-label="' + (rail ? 'Expand navigation' : 'Collapse navigation') + '">' +
        icon(rail ? 'expand' : 'collapse') + '<span class="ui-nav__text">' + (rail ? 'Expand' : 'Collapse') + '</span></button>';
    }
    if (foot) h += '<div class="ui-nav__footer">' + foot + '</div>';
    return h;
  }

  var tip = null;
  function showTip(btn) {
    if (!tip) { tip = document.createElement('div'); tip.className = 'ui-nav-tip ui-root'; tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip); }
    var r = btn.getBoundingClientRect();
    tip.textContent = btn.getAttribute('data-label') || '';
    tip.style.left = (r.right + 8) + 'px';
    tip.style.top = (r.top + r.height / 2 - 12) + 'px';
    tip.setAttribute('data-show', 'true');
  }
  function hideTip() { if (tip) tip.setAttribute('data-show', 'false'); }

  function mount(host, config, opts) {
    opts = opts || {};
    var cfg = config, active = opts.active || null, mode = 'expanded', context = 'docked';
    var el = document.createElement('nav');
    el.className = 'ui-nav';
    el.setAttribute('aria-label', cfg.ariaLabel || 'Main');
    host.appendChild(el);

    function paint() {
      el.innerHTML = render(cfg, active, mode);
      el.setAttribute('data-mode', mode);
      el.setAttribute('data-context', context);
    }
    function findItem(id) {
      var all = [];
      (cfg.groups || []).forEach(function (g) { all = all.concat(g.items || []); });
      all = all.concat(cfg.footer || []);
      return all.filter(function (i) { return i.id === id; })[0] || null;
    }
    function items() { return Array.prototype.slice.call(el.querySelectorAll('.ui-nav__item')).filter(function (b) { return b.offsetParent !== null; }); }

    function onClick(e) {
      var b = e.target.closest('button'); if (!b || !el.contains(b)) return;
      var act = b.getAttribute('data-act');
      if (act === 'group') {
        var g = b.closest('.ui-nav__group');
        var c = g.getAttribute('data-collapsed') !== 'true';
        g.setAttribute('data-collapsed', String(c));
        b.setAttribute('aria-expanded', String(!c));
        var gc = (cfg.groups || []).filter(function (x) { return String(x.id) === g.getAttribute('data-group'); })[0];
        if (gc) gc.collapsed = c;
        return;
      }
      if (act === 'collapse') { hideTip(); if (opts.onCollapseToggle) opts.onCollapseToggle(); return; }
      if (act === 'close') { if (opts.onClose) opts.onClose(); return; }
      var id = b.getAttribute('data-id');
      if (id) { ctl.setActive(id); if (opts.onSelect) opts.onSelect(id, findItem(id)); }
    }
    function onKey(e) {
      if (!e.target.classList || !e.target.classList.contains('ui-nav__item')) return;
      var list = items(), i = list.indexOf(e.target), j = null;
      if (e.key === 'ArrowDown') j = Math.min(i + 1, list.length - 1);
      else if (e.key === 'ArrowUp') j = Math.max(i - 1, 0);
      else if (e.key === 'Home') j = 0;
      else if (e.key === 'End') j = list.length - 1;
      if (j !== null) { e.preventDefault(); list[j].focus(); }
    }
    function onOver(e) {
      if (mode !== 'rail') return;
      var b = e.target.closest('.ui-nav__item');
      if (b && el.contains(b)) showTip(b); else hideTip();
    }
    el.addEventListener('click', onClick);
    el.addEventListener('keydown', onKey);
    el.addEventListener('mouseover', onOver);
    el.addEventListener('focusin', onOver);
    el.addEventListener('mouseleave', hideTip);
    el.addEventListener('focusout', hideTip);

    var ctl = {
      el: el,
      setActive: function (id) {   // null clears the current item
        active = id == null ? null : id;
        el.querySelectorAll('.ui-nav__item[data-id]').forEach(function (b) {
          if (b.getAttribute('data-id') === id) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
        });
      },
      setBadge: function (id, badge) {
        var it = findItem(id); if (it) it.badge = badge;
        var b = el.querySelector('.ui-nav__item[data-id="' + String(id).replace(/"/g, '') + '"]');
        if (!b) return;
        var old = b.querySelector('.ui-nav__badge'); if (old) old.remove();
        if (badge) b.insertAdjacentHTML('beforeend', badgeHtml(badge));
      },
      setMode: function (m) { m = m === 'rail' ? 'rail' : 'expanded'; if (m !== mode) { mode = m; paint(); if (m !== 'rail') hideTip(); } },
      setContext: function (c) { context = c || 'docked'; el.setAttribute('data-context', context); },
      update: function (c) { cfg = c; paint(); },
      destroy: function () { if (shellEl) shellEl.removeEventListener('ui-shell:change', onShell); hideTip(); el.remove(); }
    };

    var shellEl = opts.shell || null;
    function onShell(e) {
      var s = e.detail;
      ctl.setMode(s.nav === 'rail' ? 'rail' : 'expanded');
      ctl.setContext(s.nav === 'drawer' ? 'drawer' : (s.nav === 'overlay' ? 'overlay' : 'docked'));
    }
    paint();
    if (shellEl) {
      shellEl.addEventListener('ui-shell:change', onShell);
      var dn = shellEl.getAttribute('data-nav');   // the shell may have mounted first
      if (dn) onShell({ detail: { nav: dn } });
    }
    return ctl;
  }

  var api = { mount: mount };
  root.SRETNav = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
