const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { pickApi } = require('../src/platform');

test('the browser namespace is preferred where it exists, otherwise chrome is used', () => {
  const browser = { runtime: {}, tag: 'browser' };
  const chrome = { runtime: {}, tag: 'chrome' };
  assert.strictEqual(pickApi({ browser, chrome }), browser);
  assert.strictEqual(pickApi({ chrome }), chrome);
  assert.strictEqual(pickApi({ browser: {}, chrome }), chrome, 'a browser object without runtime is not the extension API');
  assert.strictEqual(pickApi({}), undefined);
});

// The architecture rule: shared code never names a browser API or loads scripts by itself.
// Browser differences live in src/platform.js and in targets/.
test('no shared source file uses chrome.*, browser.* or importScripts, except the platform layer', () => {
  const src = path.join(__dirname, '..', 'src');
  const offenders = [];
  for (const name of fs.readdirSync(src).filter((f) => f.endsWith('.js') && f !== 'platform.js')) {
    const text = fs.readFileSync(path.join(src, name), 'utf8');
    for (const pattern of [/\bchrome\./, /\bbrowser\./, /\bimportScripts\b/]) {
      if (pattern.test(text)) offenders.push(`${name}: ${pattern}`);
    }
  }
  assert.deepStrictEqual(offenders, []);
});
