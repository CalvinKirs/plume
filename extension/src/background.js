importScripts('settings.js', 'sender.js', 'history.js');

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === 'plume:send') {
    Plume.settings.loadSettings(chrome.storage.local)
      .then((settings) => Plume.sender.sendDraft(msg, settings, { runtime: chrome.runtime, fetch }))
      .catch((e) => ({ ok: false, error: 'Plume background error: ' + ((e && e.message) || e) }))
      .then(async (result) => {
        try { // the log must never get in the way of the answer
          await Plume.history.append(chrome.storage.local, Plume.history.entryFor(msg.draft, result));
        } catch (e) { /* storage unavailable */ }
        return result;
      })
      .then(reply);
    return true; // answer asynchronously
  }
});
