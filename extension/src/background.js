importScripts('settings.js', 'sender.js');

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === 'plume:send') {
    Plume.settings.loadSettings(chrome.storage.local)
      .then((settings) => Plume.sender.sendDraft(msg, settings, { runtime: chrome.runtime, fetch }))
      .catch((e) => ({ ok: false, error: 'Plume background error: ' + ((e && e.message) || e) }))
      .then(reply);
    return true; // answer asynchronously
  }
});
