// The shared core of the background script. It expects Plume.api, settings, sender and history to be
// loaded already, which is the job of each target's bootstrap (targets/<browser>/).
Plume.api.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === 'plume:send') {
    Plume.settings.loadSettings(Plume.api.storage.local)
      .then((settings) => Plume.sender.sendDraft(msg, settings, { runtime: Plume.api.runtime, fetch }))
      .catch((e) => ({ ok: false, error: 'Plume background error: ' + ((e && e.message) || e) }))
      .then(async (result) => {
        try { // A failing log must never get in the way of the answer.
          await Plume.history.append(Plume.api.storage.local, Plume.history.entryFor(msg.draft, result));
        } catch (e) { /* storage unavailable */ }
        return result;
      })
      .then(reply);
    return true; // answer asynchronously
  }
});
