'use strict';
// Post-update self-test (charter D-1): run by the NEW build at startup,
// before any window, and by `VeilWalker.exe --vw-self-test` (prints JSON,
// exit 0 / 1). Pure: inputs are passed in so node:test can drive it.

const fs = require('node:fs');
const path = require('node:path');
const { webPreferences, HARDENED } = require('./webprefs');
const { resolveRequest, CSP } = require('./appProtocol');

const REQUIRED = [
  'src/main/main.js',
  'src/preload/preload.js',
  'src/renderer/index.html',
  'src/renderer/app.js',
  'src/renderer/app.css',
  'src/renderer/tokens.css',
];

function runSelfTest(opts) {
  const failures = [];
  const root = opts.appRoot;
  if (opts.target && opts.version !== opts.target) {
    failures.push('version ' + opts.version + ' != expected ' + opts.target);
  }
  for (const rel of REQUIRED) {
    if (!fs.existsSync(path.join(root, rel))) failures.push('missing ' + rel);
  }
  const prefs = webPreferences();
  for (const [k, v] of Object.entries(HARDENED)) {
    if (k !== 'devTools' && prefs[k] !== v) failures.push('webPreferences.' + k);
  }
  const page = resolveRequest('app://vw/index.html', path.join(root, 'src', 'renderer'));
  if (!page || !fs.existsSync(page.file)) failures.push('app:// index unresolved');
  if (resolveRequest('app://vw/..%2f..%2fpackage.json', path.join(root, 'src', 'renderer'))) {
    failures.push('app:// traversal not refused');
  }
  if (/unsafe-(inline|eval)/.test(CSP)) failures.push('CSP allows unsafe-*');
  if (opts.sandboxed === false) failures.push('sandbox not enabled');
  return { ok: failures.length === 0, failures, version: opts.version };
}

module.exports = { runSelfTest, REQUIRED };
