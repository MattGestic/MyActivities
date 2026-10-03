// Browser check for the UI kit (D-31 Stage A): measured layout, behaviour and contracts.
//   node tools/ui_kit_check.mjs
// Runs prototypes/ui-kit/demo-shell.html (the module files, unbundled) at 390, 768 and 1440,
// then the built gallery once for console errors. Measures computed styles and classes,
// never screenshots (app CLAUDE.md verification standard). Light theme only.
import { createRequire } from 'module';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const globalRoot = execSync('npm root -g').toString().trim();
const { chromium } = createRequire(globalRoot + '/')('playwright');

const DEMO = 'file://' + path.join(root, 'prototypes/ui-kit/demo-shell.html');
const GALLERY = 'file://' + path.join(root, 'prototypes/ui-kit/dist/ui-kit-gallery.html');
let fails = 0, passes = 0;
const check = (name, ok, extra = '') => { if (ok) passes++; else { fails++; console.log('FAIL', name, extra); } };
const settle = (p) => p.waitForTimeout(320);   // longest transition is 240 ms

const browser = await chromium.launch();

async function page(width, height = 900) {
  const ctx = await browser.newContext({ viewport: { width, height } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(DEMO);
  await settle(p);
  return { p, ctx, errs };
}
const attr = (p, a) => p.$eval('#shell', (e, a) => e.getAttribute(a), a);
const box = (p, sel) => p.$eval(sel, e => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; });
const css = (p, sel, prop) => p.$eval(sel, (e, prop) => getComputedStyle(e)[prop], prop);
const noPageOverflow = (p) => p.evaluate(() => document.documentElement.scrollWidth <= innerWidth && document.body.scrollWidth <= innerWidth);

// ---------- Desktop 1440 ----------
{
  const { p, ctx, errs } = await page(1440);
  check('1440 band desktop', await attr(p, 'data-band') === 'desktop');
  check('1440 nav expanded', await attr(p, 'data-nav') === 'expanded');
  check('1440 nav width 240', Math.round((await box(p, '.ui-shell__nav')).w) === 240);
  check('1440 menu button hidden', await css(p, '#menu-btn', 'display') === 'none');
  check('1440 header gutter 24', await css(p, '.ui-shell__header', 'paddingLeft') === '24px');
  check('1440 main padding 24', await css(p, '.ui-shell__main', 'paddingTop') === '24px');
  check('1440 nav padding 12/8', (await css(p, '.ui-nav', 'padding')) === '12px 8px');
  check('1440 nav item 40 high', Math.round((await box(p, '.ui-nav__item')).h) === 40);
  check('1440 button 32 high', Math.round((await box(p, '#save-btn')).h) === 32);
  check('1440 card body padding 16', await css(p, '#card-form .ui-card__body', 'padding') === '16px');
  check('1440 card header padding 12/16', await css(p, '#card-form .ui-card__header', 'padding') === '12px 16px');
  check('1440 card body gap 12', await css(p, '#card-form .ui-card__body', 'rowGap') === '12px');
  check('1440 list item min height 44', (await css(p, '.ui-list-item', 'minHeight')) === '44px');
  check('1440 field grid two columns', (await css(p, '.ui-field-grid', 'gridTemplateColumns')).split(' ').length === 2);
  check('1440 shell transition 200ms', (await css(p, '.ui-shell', 'transitionDuration')) === '0.2s');
  check('1440 long nav label truncates', await p.$eval('.ui-nav__item[data-id="comments"] .ui-nav__text', e => e.scrollWidth > e.clientWidth && getComputedStyle(e).textOverflow === 'ellipsis'));
  check('1440 no page overflow', await noPageOverflow(p));

  // Keyboard movement in the nav
  await p.focus('.ui-nav__item[data-id="dashboard"]');
  await p.keyboard.press('ArrowDown');
  check('1440 ArrowDown moves focus', await p.evaluate(() => document.activeElement.getAttribute('data-id')) === 'timeline');
  await p.keyboard.press('Enter');
  check('1440 Enter selects item', await p.$eval('.ui-nav__item[data-id="timeline"]', e => e.getAttribute('aria-current')) === 'page');
  check('1440 host callback ran', (await p.textContent('#page-title')) === 'Timeline');

  // Badge update from the host
  await p.evaluate(() => window.__kit.nav.setBadge('notes', { value: 9, tone: 'accent' }));
  check('1440 setBadge', (await p.textContent('.ui-nav__item[data-id="notes"] .ui-nav__badge')) === '9');

  // Group collapse
  await p.click('.ui-nav__label[data-act="group"]');
  await settle(p);
  check('1440 group collapses', Math.round((await box(p, '#ui-nav-g-lists')).h) === 0);
  await p.click('.ui-nav__label[data-act="group"]');
  await settle(p);

  // Aside pushes the content
  const mainBefore = (await box(p, '.ui-shell__main')).w;
  await p.click('#aside-btn');
  await settle(p);
  check('1440 aside open', await attr(p, 'data-aside-open') === 'true');
  check('1440 aside 380 wide', Math.round((await box(p, '.ui-shell__aside')).w) === 380);
  check('1440 aside pushes main', Math.round(mainBefore - (await box(p, '.ui-shell__main')).w) === 380);
  check('1440 no scrim on push', await attr(p, 'data-scrim') === 'false');
  await p.click('#aside-close');
  await settle(p);

  // Collapse to rail, remembered across reload
  await p.click('.ui-nav__collapse');
  await settle(p);
  check('1440 collapse to rail', await attr(p, 'data-nav') === 'rail');
  check('1440 rail width 60', Math.round((await box(p, '.ui-shell__nav')).w) === 60);
  check('1440 labels hidden in rail', await css(p, '.ui-nav__item[data-id="notes"] .ui-nav__text', 'opacity') === '0');
  await p.hover('.ui-nav__item[data-id="reports"]');
  await settle(p);
  check('1440 rail tooltip shows label', await p.$eval('.ui-nav-tip', e => e.getAttribute('data-show') === 'true' && e.textContent === 'Reports'));
  await p.reload(); await settle(p);
  check('1440 rail remembered after reload', await attr(p, 'data-nav') === 'rail');
  await p.click('.ui-nav__collapse'); await settle(p);
  check('1440 expand back', await attr(p, 'data-nav') === 'expanded');
  check('1440 no console errors', errs.length === 0, errs.join(' | '));
  await ctx.close();
}

// ---------- Tablet 768 ----------
{
  const { p, ctx, errs } = await page(768);
  check('768 band tablet', await attr(p, 'data-band') === 'tablet');
  check('768 nav rail', await attr(p, 'data-nav') === 'rail');
  check('768 header gutter 16', await css(p, '.ui-shell__header', 'paddingLeft') === '16px');
  const mainW = (await box(p, '.ui-shell__main')).w;
  await p.click('.ui-nav__collapse');
  await settle(p);
  check('768 expand opens overlay', await attr(p, 'data-nav') === 'overlay');
  check('768 overlay nav 240 wide', Math.round((await box(p, '.ui-shell__nav')).w) === 240);
  check('768 overlay does not reflow main', Math.round((await box(p, '.ui-shell__main')).w) === Math.round(mainW));
  check('768 scrim on', await attr(p, 'data-scrim') === 'true');
  check('768 content inert behind overlay', await p.$eval('.ui-shell__main', e => e.hasAttribute('inert')));
  await p.keyboard.press('Escape');
  await settle(p);
  check('768 Esc closes overlay', await attr(p, 'data-nav') === 'rail' && !(await p.$eval('.ui-shell__main', e => e.hasAttribute('inert'))));
  await p.click('#aside-btn');
  await settle(p);
  check('768 aside overlays', await attr(p, 'data-aside') === 'overlay' && Math.round((await box(p, '.ui-shell__main')).w) === Math.round(mainW));
  await p.click('.ui-shell__scrim', { position: { x: 20, y: 400 } });
  await settle(p);
  check('768 scrim click closes aside', await attr(p, 'data-aside-open') === 'false');
  check('768 no page overflow', await noPageOverflow(p));
  check('768 no console errors', errs.length === 0, errs.join(' | '));
  await ctx.close();
}

// ---------- Phone 390 ----------
{
  const { p, ctx, errs } = await page(390, 844);
  check('390 band phone', await attr(p, 'data-band') === 'phone');
  check('390 nav is a hidden drawer', await attr(p, 'data-nav') === 'drawer' && await css(p, '.ui-shell__nav', 'visibility') === 'hidden');
  check('390 menu button shown', await css(p, '#menu-btn', 'display') !== 'none');
  check('390 main gutter 16', await css(p, '.ui-shell__main', 'paddingLeft') === '16px');
  check('390 field grid one column', (await css(p, '.ui-field-grid', 'gridTemplateColumns')).split(' ').length === 1);
  check('390 chips wrap', await css(p, '#toolbar .ui-chips', 'flexWrap') === 'wrap');
  check('390 no page overflow', await noPageOverflow(p));
  check('390 long list title truncates', await p.$$eval('.ui-list-item__title', a => a.some(e => e.scrollWidth > e.clientWidth && getComputedStyle(e).textOverflow === 'ellipsis')));
  check('390 main does not scroll sideways', await p.$eval('.ui-shell__main', e => e.scrollWidth <= e.clientWidth));
  await p.click('#menu-btn');
  await settle(p);
  check('390 drawer opens', await attr(p, 'data-nav-open') === 'true' && await css(p, '.ui-shell__nav', 'visibility') === 'visible');
  check('390 drawer has close, no collapse', await css(p, '.ui-nav__close', 'display') !== 'none' && await css(p, '.ui-nav__collapse', 'display') === 'none');
  check('390 focus moved into drawer', await p.evaluate(() => !!document.activeElement.closest('.ui-nav')));
  await p.click('.ui-nav__item[data-id="reports"]');
  await settle(p);
  check('390 choosing an item closes drawer', await attr(p, 'data-nav-open') === 'false');
  check('390 focus returned to menu button', await p.evaluate(() => document.activeElement.id) === 'menu-btn');
  await p.click('#menu-btn'); await settle(p);
  await p.keyboard.press('Escape'); await settle(p);
  check('390 Esc closes drawer', await attr(p, 'data-nav-open') === 'false');
  await p.click('#menu-btn'); await settle(p);
  await p.click('.ui-shell__scrim', { position: { x: 370, y: 400 } }); await settle(p);
  check('390 scrim click closes drawer', await attr(p, 'data-nav-open') === 'false');

  // Surfaces and controls behaviour
  await p.focus('#t-recent');
  await p.keyboard.press('ArrowRight');
  check('390 tabs: ArrowRight selects next', await p.$eval('#t-assigned', e => e.getAttribute('aria-selected')) === 'true' && await p.$eval('#p-assigned', e => !e.hidden));
  const sw = '#card-form .ui-switch';
  await p.click(sw);
  check('390 switch toggles', await p.$eval(sw, e => e.getAttribute('aria-checked')) === 'false');
  check('390 switch hit area >= 40', await p.$eval(sw, e => parseFloat(getComputedStyle(e, '::after').width) >= 40));
  await p.click('.ui-segmented__opt[data-value="only"]');
  check('390 segmented selects', await p.$eval('.ui-segmented__opt[data-value="only"]', e => e.getAttribute('aria-checked')) === 'true');
  const chips = await p.$$eval('#toolbar .ui-chip', a => a.length);
  await p.click('#toolbar .ui-chip__remove');
  check('390 chip remove', (await p.$$eval('#toolbar .ui-chip', a => a.length)) === chips - 1);
  check('390 no console errors', errs.length === 0, errs.join(' | '));
  await ctx.close();
}

// ---------- Page variant (how the dashboard app hosts the nav) ----------
{
  const PAGE = 'file://' + path.join(root, 'prototypes/ui-kit/demo-page.html');
  for (const [w, nav, col] of [[1440, 'expanded', 240], [768, 'rail', 60], [390, 'drawer', 0]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 800 } });
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.goto(PAGE); await settle(p);
    const bodyAttr = (a) => p.evaluate(a => document.body.getAttribute(a), a);
    check(`page ${w} nav ${nav}`, await bodyAttr('data-nav') === nav);
    check(`page ${w} body offset ${col}`, Math.round(parseFloat(await p.evaluate(() => getComputedStyle(document.body).marginLeft))) === col);
    check(`page ${w} nav is fixed`, await p.$eval('#nav-host', e => getComputedStyle(e).position) === 'fixed');
    await p.mouse.wheel(0, 600); await settle(p);
    check(`page ${w} document scrolls, nav stays`, await p.evaluate(() => scrollY > 0) && Math.round((await box(p, '#nav-host')).y) === 0);
    check(`page ${w} no page overflow`, await noPageOverflow(p));
    if (w === 390) {
      await p.evaluate(() => scrollTo(0, 0));
      await p.click('#menu-btn'); await settle(p);
      check('page 390 drawer opens', await bodyAttr('data-nav-open') === 'true' && await p.$eval('#host-content', e => e.hasAttribute('inert')));
      await p.keyboard.press('Escape'); await settle(p);
      check('page 390 Esc closes drawer', await bodyAttr('data-nav-open') === 'false' && !(await p.$eval('#host-content', e => e.hasAttribute('inert'))));
    }
    if (w === 1440) {
      await p.click('.ui-nav__collapse'); await settle(p);
      check('page 1440 collapse to rail offsets 60', await bodyAttr('data-nav') === 'rail' && Math.round(parseFloat(await p.evaluate(() => getComputedStyle(document.body).marginLeft))) === 60);
      let other = 0; await p.evaluate(() => document.addEventListener('keydown', () => { window.__esc = (window.__esc || 0) + 1; }));
      await p.keyboard.press('Escape');
      check('page 1440 Esc passes through when nothing to close', await p.evaluate(() => window.__esc) === 1);
    }
    check(`page ${w} no console errors`, errs.length === 0, errs.join(' | '));
    await ctx.close();
  }
}

// ---------- Rules over the module sources ----------
{
  const fs = await import('fs');
  const dirs = ['ui-tokens', 'ui-icons', 'ui-shell', 'ui-surfaces', 'ui-controls', 'ui-nav'];
  for (const d of dirs) {
    const dir = path.join(root, 'src/modules', d);
    for (const f of fs.readdirSync(dir).filter(f => /\.(css|js)$/.test(f))) {
      const t = fs.readFileSync(path.join(dir, f), 'utf8');
      check(`${d}/${f} has no network reference`, !/https?:\/\//.test(t));
      if (f !== 'ui-palette.css' && f.endsWith('.css')) {
        const lit = t.replace(/\/\*[\s\S]*?\*\//g, '').match(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/g);
        check(`${d}/${f} has no literal colour`, !lit, lit ? lit.join(',') : '');
      }
      if (f.endsWith('.css')) {
        const dur = t.replace(/\/\*[\s\S]*?\*\//g, '').match(/\b\d+m?s\b/g) || [];
        check(`${d}/${f} uses motion tokens only`, d === 'ui-tokens' || dur.filter(x => x !== '0s').length === 0, dur.join(','));
      }
    }
  }
}

// ---------- Built gallery ----------
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(GALLERY); await settle(p);
  check('gallery loads with no console errors', errs.length === 0, errs.join(' | '));
  check('gallery embeds module docs', await p.$eval('#dp-nav', e => e.querySelectorAll('table').length >= 3));
  check('gallery has no network loads', await p.evaluate(() => performance.getEntriesByType('resource').every(r => !/^https?:/.test(r.name))));
  await ctx.close();
}

await browser.close();
console.log(`${passes} passed, ${fails} failed`);
process.exit(fails ? 1 : 0);
