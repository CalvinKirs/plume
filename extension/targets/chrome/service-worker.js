// Chrome's background entry point: a Manifest V3 service worker. It has to load its own scripts,
// and does so with importScripts. The paths are relative to this file.
importScripts(
  '../../src/platform.js',
  '../../src/settings.js',
  '../../src/sender.js',
  '../../src/history.js',
  '../../src/background.js',
);
