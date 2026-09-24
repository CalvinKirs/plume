const test = require('node:test');
const assert = require('node:assert');
const { page } = require('./fixtures');
const rc = require('../src/reply-context');

const RAW = 'Received: x\r\nMessage-ID: <abc@mail.example>\r\nReferences: <r1@x>\r\n <r2@x>\r\nSubject: hi\r\n\r\nMessage-ID: <in-body@x>\r\n';

test('hex to decimal handles 64-bit ids', () => {
  assert.strictEqual(rc.hexToDecimal('ff'), '255');
  assert.strictEqual(rc.hexToDecimal('18c2f5a3b7d9e001'), '1784258485905121281');
});

test('raw headers: unfolding, header block only', () => {
  const h = rc.parseRawHeaders(RAW);
  assert.strictEqual(h['message-id'], '<abc@mail.example>');
  assert.strictEqual(h['references'], '<r1@x> <r2@x>');
  assert.deepStrictEqual(rc.contextFromHeaders(h), { inReplyTo: '<abc@mail.example>', references: '<r1@x> <r2@x> <abc@mail.example>' });
  assert.strictEqual(rc.contextFromHeaders({}), null);
});

test('reply target: modern data-message-id wins, legacy hex is converted, none gives null', () => {
  const modern = page('<div data-legacy-thread-id="18aa"><div data-message-id="#msg-f:111"></div><div data-message-id="#msg-f:222"></div></div>');
  assert.deepStrictEqual(rc.findReplyTarget(modern), { messageId: '222', threadId: '18aa' });
  const legacy = page('<div data-legacy-thread-id="18aa"><div data-legacy-message-id="11"></div><div data-legacy-message-id="ff"></div></div>');
  assert.deepStrictEqual(rc.findReplyTarget(legacy), { messageId: '255', threadId: '18aa' });
  assert.strictEqual(rc.findReplyTarget(page('<div></div>')), null);
});

test('fetches the original by decimal id from the right account and says why it failed', async () => {
  const doc = page('<div data-legacy-thread-id="18aa"><div data-legacy-message-id="ff"></div></div>');
  const loc = { origin: 'https://mail.google.com', pathname: '/mail/u/2/' };
  let asked;
  const ok = async (url) => ((asked = url), { ok: true, text: async () => RAW });
  const { ctx, reason } = await rc.fetchReplyContext(doc, loc, ok);
  assert.strictEqual(asked, 'https://mail.google.com/mail/u/2/?view=om&permmsgid=msg-f%3A255');
  assert.deepStrictEqual([ctx.threadId, ctx.inReplyTo, reason], ['18aa', '<abc@mail.example>', null]);
  assert.match((await rc.fetchReplyContext(doc, loc, async () => ({ ok: false, status: 404 }))).reason, /HTTP 404/);
  assert.match((await rc.fetchReplyContext(doc, loc, async () => { throw new Error('net'); })).reason, /net/);
  assert.match((await rc.fetchReplyContext(doc, loc, async () => ({ ok: true, text: async () => 'Subject: x\r\n\r\nbody' }))).reason, /no readable Message-ID/);
  assert.match((await rc.fetchReplyContext(page('<div></div>'), loc, ok)).reason, /no message id/);
});
