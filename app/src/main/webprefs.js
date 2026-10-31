'use strict';
// SEC-E2 / E3 / E4 / E6 / E8: the ONE webPreferences factory. Every
// BrowserWindow is built from it; tests assert the flags. Pure (no electron
// import) so node:test can load it without the runtime.

const path = require('node:path');

const PRELOAD = path.join(__dirname, '..', 'preload', 'preload.js');

const HARDENED = Object.freeze({
  contextIsolation: true,
  nodeIntegration: false,
  nodeIntegrationInWorker: false,
  nodeIntegrationInSubFrames: false,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false,
  experimentalFeatures: false,
  webviewTag: false,
  spellcheck: false,
  devTools: true,
});

function webPreferences(opts) {
  const o = opts || {};
  const prefs = Object.assign({}, HARDENED, { preload: PRELOAD });
  // The only caller-tunable field: packaged builds turn devtools off.
  if (o.devTools === false) prefs.devTools = false;
  return prefs;
}

module.exports = { webPreferences, HARDENED, PRELOAD };
