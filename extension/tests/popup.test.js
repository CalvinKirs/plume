const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const src = path.join(__dirname, '..', 'src');

async function popup(entries) {
  const dom = new JSDOM(fs.readFileSync(path.join(src, 'popup.html'), 'utf8'), {
    url: 'moz-extension://plume/src/popup.html', runScripts: 'outside-only',
  });
  let opened = 0;
  dom.window.Plume = {
    api: { storage: { local: {} }, runtime: { openOptionsPage: () => { opened++; } } },
    history: { load: async () => entries },
  };
  dom.window.eval(fs.readFileSync(path.join(src, 'popup.js'), 'utf8'));
  await new Promise((resolve) => setImmediate(resolve));
  return { document: dom.window.document, opened: () => opened };
}

test('popup shows the five most recent send attempts and links to full history and settings', async () => {
  const entries = Array.from({ length: 6 }, (_, i) => ({
    at: Date.now() - i * 1000, ok: i !== 1,
    subject: i === 0 ? '<unsafe subject>' : `subject ${i}`,
    to: [`person${i}@example.org`], cc: [], bcc: [],
  }));
  const { document, opened } = await popup(entries);
  const rows = document.querySelectorAll('#recent li');
  assert.strictEqual(rows.length, 5);
  assert.match(rows[0].textContent, /<unsafe subject>/);
  assert.strictEqual(rows[0].querySelector('unsafe'), null, 'subjects are text, not HTML');
  assert.match(rows[1].textContent, /not sent/);
  assert.strictEqual(document.querySelector('#all-history').getAttribute('href'), 'history.html');
  document.querySelector('#settings').click();
  assert.strictEqual(opened(), 1);
});

test('popup gives an empty state when there are no sends', async () => {
  const { document } = await popup([]);
  assert.strictEqual(document.querySelector('#recent').children.length, 0);
  assert.strictEqual(document.querySelector('#empty').hidden, false);
});

test('popup shows recipients when a send only has Cc or Bcc', async () => {
  const { document } = await popup([{
    at: Date.now(), ok: true, subject: 'private note', to: [],
    cc: ['copy@example.org'], bcc: ['hidden@example.org'],
  }]);
  assert.match(document.querySelector('#recent li').textContent, /Cc copy@example.org/);
  assert.match(document.querySelector('#recent li').textContent, /Bcc hidden@example.org/);
});
