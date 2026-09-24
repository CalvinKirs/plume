// Best-effort lookup of the RFC 5322 Message-ID / References of the message being answered,
// so replies thread correctly on mailing lists. Failure is never fatal: callers get null.
(function (root) {
  const P = (root.Plume = root.Plume || {});

  function hexToDecimal(hex) {
    return BigInt('0x' + hex).toString(10);
  }

  function parseRawHeaders(raw) {
    const head = raw.split(/\r?\n\r?\n/)[0].replace(/\r?\n[ \t]+/g, ' ');
    const headers = {};
    for (const line of head.split(/\r?\n/)) {
      const i = line.indexOf(':');
      if (i > 0) headers[line.slice(0, i).trim().toLowerCase()] = line.slice(i + 1).trim();
    }
    return headers;
  }

  function contextFromHeaders(headers) {
    const id = headers['message-id'];
    if (!id) return null;
    const refs = (headers['references'] || '').trim();
    return { inReplyTo: id, references: refs ? `${refs} ${id}` : id };
  }

  // The last message of the thread that is open behind the compose window. Newer Gmail markup
  // carries the decimal id in data-message-id ("#msg-f:1784..."), older markup a hex
  // data-legacy-message-id; either becomes a decimal id.
  function findReplyTarget(doc) {
    const modern = [...doc.querySelectorAll('[data-message-id]')]
      .filter((el) => /msg-f:\d+/.test(el.getAttribute('data-message-id')));
    const legacy = doc.querySelectorAll('[data-legacy-message-id]');
    let last, decimal;
    if (modern.length) {
      last = modern[modern.length - 1];
      decimal = /msg-f:(\d+)/.exec(last.getAttribute('data-message-id'))[1];
    } else if (legacy.length) {
      last = legacy[legacy.length - 1];
      decimal = hexToDecimal(last.getAttribute('data-legacy-message-id'));
    } else {
      return null;
    }
    const threadEl = last.closest('[data-legacy-thread-id]') || doc.querySelector('[data-legacy-thread-id]');
    return {
      messageId: decimal,
      threadId: threadEl ? threadEl.getAttribute('data-legacy-thread-id').replace(/^#?thread-f:/, '') : null,
    };
  }

  function accountIndex(pathname) {
    const m = /\/mail\/u\/(\d+)/.exec(pathname);
    return m ? m[1] : '0';
  }

  // Returns {ctx, reason}: ctx is {inReplyTo, references, threadId} or null, and reason says why it is null.
  async function fetchReplyContext(doc, loc, fetchFn) {
    const target = findReplyTarget(doc);
    if (!target) return { ctx: null, reason: 'no message id found in the open thread' };
    try {
      const url = `${loc.origin}/mail/u/${accountIndex(loc.pathname)}/?view=om&permmsgid=msg-f%3A${target.messageId}`;
      const res = await fetchFn(url, { credentials: 'same-origin' });
      if (!res.ok) return { ctx: null, reason: `fetching the original message failed: HTTP ${res.status}` };
      const ctx = contextFromHeaders(parseRawHeaders(await res.text()));
      if (!ctx) return { ctx: null, reason: 'the original message has no readable Message-ID header' };
      return { ctx: { ...ctx, threadId: target.threadId }, reason: null };
    } catch (e) {
      return { ctx: null, reason: 'fetching the original message failed: ' + ((e && e.message) || e) };
    }
  }

  P.replyContext = { hexToDecimal, parseRawHeaders, contextFromHeaders, findReplyTarget, accountIndex, fetchReplyContext };
  if (typeof module !== 'undefined') module.exports = P.replyContext;
})(typeof globalThis !== 'undefined' ? globalThis : this);
