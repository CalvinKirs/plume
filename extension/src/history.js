// A short log of recent sends, kept in this browser only (chrome.storage.local). It stores
// recipients, subject and outcome, but never the message text, so a missed notification can
// still be checked later.
(function (root) {
  const P = (root.Plume = root.Plume || {});
  const MAX = 50;

  async function load(storage) {
    const { history } = await storage.get({ history: [] });
    return Array.isArray(history) ? history : [];
  }

  function entryFor(draft, result, now = Date.now()) {
    return {
      at: now, ok: !!result.ok, subject: draft.subject || '',
      to: draft.to || [], cc: draft.cc || [], bcc: draft.bcc || [],
      messageId: result.messageId || null, relayResponse: result.relayResponse || null,
      relaySeconds: result.relaySeconds == null ? null : result.relaySeconds,
      archived: !!result.archived, error: result.ok ? null : result.error || 'unknown error',
    };
  }

  // Newest first, capped at max entries.
  async function append(storage, entry, max = MAX) {
    const list = await load(storage);
    list.unshift(entry);
    await storage.set({ history: list.slice(0, max) });
  }

  const clear = (storage) => storage.set({ history: [] });

  P.history = { MAX, load, entryFor, append, clear };
  if (typeof module !== 'undefined') module.exports = P.history;
})(typeof globalThis !== 'undefined' ? globalThis : this);
