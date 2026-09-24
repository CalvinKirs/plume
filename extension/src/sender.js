(function (root) {
  const P = (root.Plume = root.Plume || {});
  const HOST = 'org.plume.host';
  const NATIVE_TIMEOUT_MS = 90000; // Longer than the host's own SMTP timeouts.

  function buildPayload(draft, ctx, settings) {
    const payload = {
      from: settings.from, to: draft.to, cc: draft.cc, bcc: draft.bcc,
      subject: draft.subject, text: draft.text,
    };
    const name = (settings.fromName || '').trim();
    if (name) payload.fromName = name;
    if (ctx) {
      payload.inReplyTo = ctx.inReplyTo;
      payload.references = ctx.references;
      if (ctx.threadId) payload.threadId = ctx.threadId;
    }
    return payload;
  }

  const fail = (error) => ({ ok: false, error });
  const done = (data, payload) => ({
    ok: true, from: payload.fromName ? `${payload.fromName} <${payload.from}>` : payload.from, messageId: data.messageId || null,
    archived: !!data.archived, archiveError: data.archiveError || null,
    relayResponse: data.relayResponse || null, relaySeconds: data.relaySeconds == null ? null : data.relaySeconds,
  });

  // Default transport: Chrome starts the local Plume host when it is needed (native messaging).
  async function viaNative(payload, runtime, timeoutMs) {
    let data, timer;
    const silence = new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('TIMEOUT')), timeoutMs);
    });
    try {
      data = await Promise.race([runtime.sendNativeMessage(HOST, { type: 'send', payload }), silence]);
    } catch (e) {
      if (String(e && e.message) === 'TIMEOUT') {
        return fail(`The Plume host did not answer within ${Math.round(timeoutMs / 1000)} s. Run \`plume setup\` again; if a macOS dialog is waiting for you, answer it.`);
      }
      const m = String((e && e.message) || e);
      if (/not found/i.test(m)) {
        return fail('Plume host is not installed. Run the Plume setup program (`plume setup`), then restart Chrome.');
      }
      if (/forbidden/i.test(m)) return fail('The Plume host does not allow this extension id; re-run `plume setup`.');
      return fail('Plume host failed: ' + m);
    } finally {
      clearTimeout(timer);
    }
    if (!data) return fail('The Plume host did not answer (it exited early).');
    return data.ok ? done(data, payload) : fail(data.error || 'Plume host reported an error');
  }

  // Optional transport for debugging: talk to `python3 -m plume serve` over localhost HTTP.
  // No host installation is needed.
  async function viaHttp(payload, settings, fetchFn) {
    if (!settings.token) return fail('HTTP mode needs the token in the Plume options.');
    let res;
    try {
      res = await fetchFn(`http://127.0.0.1:${settings.port}/send`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${settings.token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      return fail(`Cannot reach the Plume server on 127.0.0.1:${settings.port}. Is it running?`);
    }
    let data = {};
    try { data = await res.json(); } catch (e) { /* non-JSON error page */ }
    return res.ok ? done(data, payload) : fail(data.error || `Plume server answered HTTP ${res.status}`);
  }

  // deps is { runtime, fetch }. Always resolves to {ok, ...} and never throws, so the caller only
  // has to show the outcome.
  async function sendDraft({ draft, ctx }, settings, deps) {
    if (!settings.from) return fail('Open the Plume options and set your @apache.org address.');
    const payload = buildPayload(draft, ctx, settings);
    return settings.mode === 'http' ? viaHttp(payload, settings, deps.fetch) : viaNative(payload, deps.runtime, deps.timeoutMs || NATIVE_TIMEOUT_MS);
  }

  P.sender = { buildPayload, sendDraft };
  if (typeof module !== 'undefined') module.exports = P.sender;
})(typeof globalThis !== 'undefined' ? globalThis : this);
