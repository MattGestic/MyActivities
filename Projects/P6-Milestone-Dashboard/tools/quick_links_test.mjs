// P80 quick links tests (src/modules/quick-links/quick-links.js).
// Run: node tools/quick_links_test.mjs
// Prints PASS/FAIL per check and exits 1 on any failure. No network, no deps.
import { createRequire } from 'module';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const Q = require(join(here, '..', 'src', 'modules', 'quick-links', 'quick-links.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('PASS ' + name); }
  else { fail++; console.log('FAIL ' + name + (detail !== undefined ? '  :: ' + JSON.stringify(detail) : '')); }
}
const u = t => Q.normaliseUrl(t);

// ---- addresses ----
check('https kept', u('https://example.sharepoint.com/sites/X/Shared Documents').url === 'https://example.sharepoint.com/sites/X/Shared%20Documents', u('https://example.sharepoint.com/sites/X/Shared Documents'));
check('http kept', u('http://intranet/x').url === 'http://intranet/x');
check('www. gets https', u('www.example.com/a').url === 'https://www.example.com/a');
check('Windows drive path becomes file:', u('C:\\Users\\me\\OneDrive - Org\\Reports').url === 'file:///C:/Users/me/OneDrive%20-%20Org/Reports', u('C:\\Users\\me\\OneDrive - Org\\Reports'));
check('UNC path becomes file:', u('\\\\server\\share\\dash').url === 'file://server/share/dash', u('\\\\server\\share\\dash'));
check('file: kept', u('file:///D:/Saved/').url === 'file:///D:/Saved/');
check('blank is empty, no error', u('   ').url === '' && u('').error === null && u(null).error === null);
for (const bad of ['javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'data:text/html,<b>x</b>', 'vbscript:x', 'mailto:a@b.c', 'ftp://x/y'])
  check('refused: ' + bad, !u(bad).url && /must start with/.test(u(bad).error), u(bad));
check('refused: not an address', !u('not a link').url && /not a web address/.test(u('not a link').error));
check('refused: https with no host', !u('https://').url);

// ---- lists ----
let r = Q.normalise([{ title: ' Saved dashboards ', url: 'https://x.sharepoint.com/a' }, { title: '', url: 'C:\\Data' }]);
check('two links normalised', r.links.length === 2 && !r.errors.length && r.links[0].title === 'Saved dashboards' && r.links[1].url === 'file:///C:/Data', r);
check('label: title when given', Q.label(r.links[0]) === 'Saved dashboards');
check('label: falls back to the last folder of a file path', Q.label(r.links[1]) === 'Data');
check('label: falls back to the host without www.', Q.label({ title: '', url: 'https://www.example.com/x' }) === 'example.com');
r = Q.normalise([{ title: 'A', url: 'https://a.com' }, { title: 'B', url: 'https://b.com' }, { title: 'C', url: 'https://c.com' }]);
check('at most two slots', r.links.length === 2 && r.links[1].title === 'B');
r = Q.normalise([{ title: 'Only a title', url: '' }, { title: 'Bad', url: 'javascript:x' }]);
check('title with no address: error, dropped', r.links.length === 0 && /Link 1: add an address/.test(r.errors[0]), r);
check('refused address: error names the slot', /^Link 2: the address must start with/.test(r.errors[1]), r.errors);
r = Q.normalise([{}, { title: '', url: '' }]);
check('two empty slots: nothing, no error', r.links.length === 0 && !r.errors.length);
check('not a list: nothing', Q.normalise(null).links.length === 0 && Q.normalise('x').links.length === 0);
r = Q.normalise([{ title: 'x'.repeat(200), url: 'https://a.com' }]);
check('title trimmed to TITLE_MAX', r.links[0].title.length === Q.TITLE_MAX);
r = Q.normalise([{ title: 'a\n\t b', url: 'https://a.com' }]);
check('whitespace in a title collapses', r.links[0].title === 'a b');
const msgs = [];
[[{ title: 'x', url: '' }], [{ url: 'javascript:1' }], [{ url: 'zz' }], [{ url: 'https://' }]].forEach(l => msgs.push(...Q.normalise(l).errors));
check('no em dash in any message', !msgs.some(m => /\u2014/.test(m)), msgs);

console.log(`${pass}/${pass + fail} checks passed`);
process.exit(fail ? 1 : 0);
