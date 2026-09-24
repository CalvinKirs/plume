const test = require('node:test');
const assert = require('node:assert');
const { load, entryFor, append, clear } = require('../src/history');

// In-memory stand-in for chrome.storage.local (get with defaults, set).
function memory() {
  let data = {};
  return {
    get: async (defaults) => ({ ...defaults, ...data }),
    set: async (values) => { data = { ...data, ...values }; },
  };
}

const draft = { subject: 'Re: [VOTE]', to: ['dev@apache.org'], cc: ['c@x.org'], bcc: [], text: 'never stored' };

test('a successful send is summarised without the message text', () => {
  const e = entryFor(draft, { ok: true, messageId: '<m@apache.org>', relayResponse: '250 queued as A1', relaySeconds: 0.6, archived: false }, 1000);
  assert.deepStrictEqual(e, {
    at: 1000, ok: true, subject: 'Re: [VOTE]', to: ['dev@apache.org'], cc: ['c@x.org'], bcc: [],
    messageId: '<m@apache.org>', relayResponse: '250 queued as A1', relaySeconds: 0.6, archived: false, error: null,
  });
  assert.ok(!JSON.stringify(e).includes('never stored'));
});

test('a failure keeps the error', () => {
  const e = entryFor(draft, { ok: false, error: 'relay rejected the login' }, 5);
  assert.deepStrictEqual([e.ok, e.error, e.messageId], [false, 'relay rejected the login', null]);
});

test('newest first, capped, and clearable', async () => {
  const s = memory();
  assert.deepStrictEqual(await load(s), []);
  for (let i = 1; i <= 5; i++) await append(s, { at: i }, 3);
  assert.deepStrictEqual((await load(s)).map((e) => e.at), [5, 4, 3]);
  await clear(s);
  assert.deepStrictEqual(await load(s), []);
});

test('a corrupt stored value is treated as empty', async () => {
  const s = memory();
  await s.set({ history: 'garbage' });
  assert.deepStrictEqual(await load(s), []);
  await append(s, { at: 1 });
  assert.strictEqual((await load(s)).length, 1);
});
