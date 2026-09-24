const test = require('node:test');
const assert = require('node:assert');
const { buildPayload, sendDraft } = require('../src/sender');

const settings = { from: 'me@apache.org', mode: 'native', token: '', port: 8765 };
const draft = { to: ['a@x.org'], cc: [], bcc: [], subject: 's', text: 'hi' };
const native = (impl) => ({ runtime: { sendNativeMessage: impl } });

test('payload carries reply headers and thread id only for replies', () => {
  assert.strictEqual(buildPayload(draft, null, settings).inReplyTo, undefined);
  const p = buildPayload(draft, { inReplyTo: '<1@x>', references: '<0@x> <1@x>', threadId: 'th' }, settings);
  assert.deepStrictEqual([p.inReplyTo, p.threadId, p.from], ['<1@x>', 'th', 'me@apache.org']);
});

test('native: sends the payload to the org.plume.host host', async () => {
  let call;
  const deps = native(async (host, msg) => ((call = { host, msg }), { ok: true, archived: true }));
  const r = await sendDraft({ draft, ctx: null }, settings, deps);
  assert.deepStrictEqual(r, { ok: true, archived: true, archiveError: null });
  assert.strictEqual(call.host, 'org.plume.host');
  assert.strictEqual(call.msg.type, 'send');
  assert.strictEqual(call.msg.payload.from, 'me@apache.org');
});

test('native: host errors, missing host, forbidden id and early exit become readable errors', async () => {
  const run = (impl) => sendDraft({ draft }, settings, native(impl));
  assert.deepStrictEqual(await run(async () => ({ ok: false, error: 'relay rejected the login' })), { ok: false, error: 'relay rejected the login' });
  assert.match((await run(async () => { throw new Error('Specified native messaging host not found.'); })).error, /plume setup/);
  assert.match((await run(async () => { throw new Error('Access to the specified native messaging host is forbidden.'); })).error, /extension id/);
  assert.match((await run(async () => undefined)).error, /exited early/);
  assert.match((await run(async () => { throw new Error('boom'); })).error, /boom/);
});

test('unconfigured address is reported before anything is sent', async () => {
  const r = await sendDraft({ draft }, { ...settings, from: '' }, native(async () => assert.fail('must not send')));
  assert.match(r.error, /options/);
});

test('http mode still works and needs a token', async () => {
  const http = { ...settings, mode: 'http', token: 't0k' };
  let call;
  const fetchFn = async (url, init) => ((call = { url, init }), { ok: true, json: async () => ({ archived: false }) });
  assert.deepStrictEqual(await sendDraft({ draft }, http, { fetch: fetchFn }), { ok: true, archived: false, archiveError: null });
  assert.strictEqual(call.url, 'http://127.0.0.1:8765/send');
  assert.strictEqual(call.init.headers.Authorization, 'Bearer t0k');
  assert.match((await sendDraft({ draft }, { ...http, token: '' }, { fetch: fetchFn })).error, /token/);
  assert.match((await sendDraft({ draft }, http, { fetch: async () => { throw new TypeError('x'); } })).error, /Is it running/);
  const bad = await sendDraft({ draft }, http, { fetch: async () => ({ ok: false, status: 502, json: async () => ({ error: 'relay rejected the login' }) }) });
  assert.strictEqual(bad.error, 'relay rejected the login');
});

test('a host that never answers ends in a readable timeout, not a silent hang', async () => {
  const deps = { runtime: { sendNativeMessage: () => new Promise(() => {}) }, timeoutMs: 30 };
  const r = await sendDraft({ draft }, settings, deps);
  assert.strictEqual(r.ok, false);
  assert.match(r.error, /did not answer within/);
});
