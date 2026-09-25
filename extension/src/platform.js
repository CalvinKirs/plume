// The one place that knows which browser this code runs in. Everything else reaches the extension
// API through Plume.api, so browser differences stay here and in the per-browser targets (targets/).
//
// Firefox provides `browser`, whose functions return promises. Chrome provides `chrome`, which
// returns promises in Manifest V3 as well. Preferring `browser` where it exists gives promise
// behaviour in both without any polyfill.
(function (root) {
  const P = (root.Plume = root.Plume || {});

  function pickApi(scope) {
    if (scope.browser && scope.browser.runtime) return scope.browser;
    return scope.chrome;
  }

  P.platform = { pickApi };
  P.api = pickApi(root);
  if (typeof module !== 'undefined') module.exports = P.platform;
})(typeof globalThis !== 'undefined' ? globalThis : this);
