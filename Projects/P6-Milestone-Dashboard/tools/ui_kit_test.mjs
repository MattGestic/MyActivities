// Unit test for the pure parts of the UI kit (D-31 Stage A). No browser.
//   node tools/ui_kit_test.mjs
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const shell = require('../src/modules/ui-shell/ui-shell.js');
const icons = require('../src/modules/ui-icons/ui-icons.js');
let fail = 0;
const eq = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) { fail++; console.log('FAIL', name, 'got', JSON.stringify(got), 'want', JSON.stringify(want)); }
  else console.log('ok  ', name);
};
const pick = (s) => ({ band: s.band, nav: s.nav, navOpen: s.navOpen, aside: s.aside, scrim: s.scrim });
// Band edges: both sides of each boundary (lessons-learned: range checks need both bounds).
eq('640 is phone', shell.bandFor(640), 'phone');
eq('641 is tablet', shell.bandFor(641), 'tablet');
eq('1024 is tablet', shell.bandFor(1024), 'tablet');
eq('1025 is desktop', shell.bandFor(1025), 'desktop');
eq('phone closed', pick(shell.layoutFor(390, 'expanded', false, false)), { band: 'phone', nav: 'drawer', navOpen: false, aside: 'overlay', scrim: false });
eq('phone drawer open', pick(shell.layoutFor(390, 'expanded', true, false)), { band: 'phone', nav: 'drawer', navOpen: true, aside: 'overlay', scrim: true });
eq('phone aside open', pick(shell.layoutFor(390, 'rail', false, true)), { band: 'phone', nav: 'drawer', navOpen: false, aside: 'overlay', scrim: true });
eq('tablet ignores pref', pick(shell.layoutFor(768, 'expanded', false, false)), { band: 'tablet', nav: 'rail', navOpen: false, aside: 'overlay', scrim: false });
eq('tablet expanded is overlay', pick(shell.layoutFor(768, 'rail', true, false)), { band: 'tablet', nav: 'overlay', navOpen: true, aside: 'overlay', scrim: true });
eq('desktop expanded', pick(shell.layoutFor(1440, 'expanded', true, false)), { band: 'desktop', nav: 'expanded', navOpen: false, aside: 'push', scrim: false });
eq('desktop rail, aside pushes without scrim', pick(shell.layoutFor(1440, 'rail', false, true)), { band: 'desktop', nav: 'rail', navOpen: false, aside: 'push', scrim: false });
eq('unknown pref falls back to expanded', shell.layoutFor(1440, 'bogus', false, false).nav, 'expanded');
eq('icon renders svg', /^<svg class="ui-icon"/.test(icons.svg('menu')), true);
eq('unknown icon is an empty box, not a throw', icons.svg('nope').includes('viewBox="0 0 24 24"'), true);
eq('icon names include nav set', ['menu','collapse','expand','close'].every(n => icons.has(n)), true);
console.log(fail ? `${fail} FAILED` : 'all passed');
process.exit(fail ? 1 : 0);
