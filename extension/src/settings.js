(function (root) {
  const P = (root.Plume = root.Plume || {});
  const DEFAULTS = { from: '', mode: 'native', token: '', port: 8765 };

  // chrome.storage.local, never sync: the token must not leave this machine.
  async function loadSettings(storage) {
    const stored = await storage.get(DEFAULTS);
    return { ...DEFAULTS, ...stored };
  }

  P.settings = { DEFAULTS, loadSettings, saveSettings: (storage, s) => storage.set(s) };
  if (typeof module !== 'undefined') module.exports = P.settings;
})(typeof globalThis !== 'undefined' ? globalThis : this);
