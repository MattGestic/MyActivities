/* ============================================================
   ui-shell (SRETShell): layout controller for the app frame (D-31).
   Knows nothing about the app's data. It only decides how the nav and
   aside regions behave at the current width and writes that state as
   data attributes on the .ui-shell element (CSS does the rest).

   Width bands (match ui-tokens):
     phone   <= 640    nav = drawer (off-canvas), aside = overlay
     tablet  641-1024  nav = rail, opening it slides the expanded nav over
                       the content (overlay); aside = overlay
     desktop >= 1025   nav = the user's preference (expanded | rail),
                       aside = push (content reflows only on open/close)

   API
     SRETShell.layoutFor(width, pref, navOpen, asideOpen) -> state   (pure)
     SRETShell.mount(el, opts) -> controller
        opts.navPref       'expanded' | 'rail' (default 'expanded')
        opts.persist       { get(): pref|null, set(pref) }   optional
        opts.onChange      fn(state)                          optional
        opts.width         fn() -> number, for tests          optional
     controller.toggleNav()  desktop: flips the preference; else opens/closes
     controller.openNav() / closeNav()
     controller.openAside() / closeAside() / toggleAside()
     controller.state() -> { band, nav, navOpen, aside, asideOpen, scrim, pref }
     controller.destroy()
   Events: 'ui-shell:change' (CustomEvent, detail = state) on the element.
   Keyboard: Esc closes the topmost overlay (nav drawer, then aside overlay).
   ============================================================ */
(function (root) {
  'use strict';
  var PHONE_MAX = 640, TABLET_MAX = 1024;

  function bandFor(w) { return w <= PHONE_MAX ? 'phone' : (w <= TABLET_MAX ? 'tablet' : 'desktop'); }

  function layoutFor(width, pref, navOpen, asideOpen) {
    var band = bandFor(width);
    var s = { band: band, pref: pref === 'rail' ? 'rail' : 'expanded', asideOpen: !!asideOpen };
    if (band === 'phone') { s.nav = 'drawer'; s.navOpen = !!navOpen; s.aside = 'overlay'; }
    else if (band === 'tablet') { s.nav = navOpen ? 'overlay' : 'rail'; s.navOpen = !!navOpen; s.aside = 'overlay'; }
    else { s.nav = s.pref; s.navOpen = false; s.aside = 'push'; }
    s.scrim = !!((s.nav === 'drawer' && s.navOpen) || s.nav === 'overlay' || (s.aside === 'overlay' && s.asideOpen));
    return s;
  }

  function mount(el, opts) {
    opts = opts || {};
    var widthFn = opts.width || function () { return el.getBoundingClientRect().width || root.innerWidth; };
    var pref = (opts.persist && opts.persist.get && opts.persist.get()) || opts.navPref || 'expanded';
    var navOpen = false, asideOpen = false, lastBand = null, state = null, lastFocus = null;

    var scrim = el.querySelector(':scope > .ui-shell__scrim');
    if (!scrim) { scrim = document.createElement('div'); scrim.className = 'ui-shell__scrim'; el.appendChild(scrim); }
    scrim.setAttribute('aria-hidden', 'true');
    var nav = el.querySelector(':scope > .ui-shell__nav');
    var main = el.querySelector(':scope > .ui-shell__main');
    var header = el.querySelector(':scope > .ui-shell__header');

    function apply() {
      var w = widthFn();
      var band = bandFor(w);
      if (band !== lastBand) { navOpen = false; lastBand = band; }
      var prev = state;
      state = layoutFor(w, pref, navOpen, asideOpen);
      el.setAttribute('data-band', state.band);
      el.setAttribute('data-nav', state.nav);
      el.setAttribute('data-nav-open', String(state.navOpen));
      el.setAttribute('data-aside', state.aside);
      el.setAttribute('data-aside-open', String(state.asideOpen));
      el.setAttribute('data-scrim', String(state.scrim));
      // While a drawer or overlay nav is up, the content behind it is inert.
      var modalNav = state.navOpen && (state.nav === 'drawer' || state.nav === 'overlay');
      [main, header].forEach(function (n) { if (n) { if (modalNav) n.setAttribute('inert', ''); else n.removeAttribute('inert'); } });
      if (nav && state.nav === 'drawer' && !state.navOpen) nav.setAttribute('aria-hidden', 'true');
      else if (nav) nav.removeAttribute('aria-hidden');
      if (!prev || JSON.stringify(prev) !== JSON.stringify(state)) {
        el.dispatchEvent(new CustomEvent('ui-shell:change', { detail: state }));
        if (opts.onChange) opts.onChange(state);
      }
    }

    function focusFirstNavItem() {
      if (!nav) return;
      var f = nav.querySelector('[aria-current="page"], button, a[href]');
      if (f) f.focus({ preventScroll: true });
    }

    var ctl = {
      state: function () { return Object.assign({}, state); },
      openNav: function () {
        if (state.band === 'desktop') { ctl.setPref('expanded'); return; }
        lastFocus = document.activeElement; navOpen = true; apply();
        setTimeout(focusFirstNavItem, 0);
      },
      closeNav: function () {
        if (!navOpen) return;
        navOpen = false; apply();
        if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
      },
      toggleNav: function () {
        if (state.band === 'desktop') ctl.setPref(pref === 'expanded' ? 'rail' : 'expanded');
        else if (navOpen) ctl.closeNav(); else ctl.openNav();
      },
      setPref: function (p) {
        pref = p === 'rail' ? 'rail' : 'expanded';
        if (opts.persist && opts.persist.set) opts.persist.set(pref);
        apply();
      },
      openAside: function () { asideOpen = true; apply(); },
      closeAside: function () { asideOpen = false; apply(); },
      toggleAside: function () { asideOpen = !asideOpen; apply(); },
      refresh: apply,
      destroy: function () {
        ro.disconnect();
        document.removeEventListener('keydown', onKey);
        scrim.removeEventListener('click', onScrim);
      }
    };

    function onKey(e) {
      if (e.key !== 'Escape') return;
      if (navOpen) { ctl.closeNav(); e.stopPropagation(); return; }
      if (state.aside === 'overlay' && asideOpen) { ctl.closeAside(); e.stopPropagation(); }
    }
    function onScrim() {
      if (navOpen) ctl.closeNav();
      if (state.aside === 'overlay' && asideOpen) ctl.closeAside();
    }
    // On the document, so Esc works wherever focus is while an overlay is up.
    document.addEventListener('keydown', onKey);
    scrim.addEventListener('click', onScrim);
    var ro = new ResizeObserver(function () { apply(); });
    ro.observe(el);
    apply();
    return ctl;
  }

  var api = { mount: mount, layoutFor: layoutFor, bandFor: bandFor, PHONE_MAX: PHONE_MAX, TABLET_MAX: TABLET_MAX };
  root.SRETShell = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
