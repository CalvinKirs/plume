const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const src = path.join(__dirname, '..', 'src');

test('full history lists send outcomes and can clear them without changing settings', async () => {
  const entries = [
    { at: 1000, ok: true, subject: 'sent', to: ['one@example.org'], cc: [], bcc: [], relayResponse: '250 queued', relaySeconds: 0.5, messageId: '<m1>' },
    { at: 2000, ok: false, subject: 'failed', to: ['two@example.org'], cc: [], bcc: [], error: 'relay unavailable' },
  ];
  const dom = new JSDOM(fs.readFileSync(path.join(src, 'history.html'), 'utf8'), {
    url: 'moz-extension://plume/src/history.html', runScripts: 'outside-only',
  });
  let settingsOpened = 0;
  dom.window.Plume = {
    api: {
      storage: { local: {}, onChanged: { addListener: () => {} } },
      runtime: { openOptionsPage: () => { settingsOpened++; } },
    },
    history: {
      load: async () => entries,
      clear: async () => { entries.length = 0; },
    },
  };
  dom.window.eval(fs.readFileSync(path.join(src, 'history-page.js'), 'utf8'));
  await new Promise((resolve) => setImmediate(resolve));
  const document = dom.window.document;
  const rows = document.querySelectorAll('#history tbody tr');
  assert.strictEqual(rows.length, 2);
  assert.match(rows[0].textContent, /sent.*one@example.org.*250 queued/);
  assert.match(rows[1].textContent, /relay unavailable/);
  document.querySelector('#settings').click();
  assert.strictEqual(settingsOpened, 1);
  document.querySelector('#clear').click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.strictEqual(document.querySelectorAll('#history tbody tr').length, 0);
  assert.strictEqual(document.querySelector('#empty').hidden, false);
});
