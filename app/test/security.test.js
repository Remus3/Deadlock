'use strict';
// Electron hardening and game-safety-floor checks that hold without the
// runtime (docs/research/security.md SEC-E1..E16, SEC-G1/G2/G6, SEC-S4).

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { webPreferences, HARDENED } = require('../src/main/webprefs');
const { resolveRequest, isAppUrl, responseHeaders, CSP } = require('../src/main/appProtocol');
const { runSelfTest } = require('../src/main/selftest');
const { isInMatch, setMatchProvider } = require('../src/main/matchGate');
const pkg = require('../package.json');

const APP = path.join(__dirname, '..');
const SRC = path.join(APP, 'src');
const RENDERER = path.join(SRC, 'renderer');

function walk(dir) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out;
}
const SOURCES = walk(SRC).map((f) => ({ f, text: fs.readFileSync(f, 'utf8') }));

test('webPreferences factory is hardened (SEC-E2/E3/E4/E6/E8)', () => {
  const p = webPreferences();
  assert.equal(p.contextIsolation, true);
  assert.equal(p.nodeIntegration, false);
  assert.equal(p.nodeIntegrationInWorker, false);
  assert.equal(p.nodeIntegrationInSubFrames, false);
  assert.equal(p.sandbox, true);
  assert.equal(p.webSecurity, true);
  assert.equal(p.allowRunningInsecureContent, false);
  assert.equal(p.experimentalFeatures, false);
  assert.equal(p.webviewTag, false);
  assert.ok(fs.existsSync(p.preload));
  assert.equal(webPreferences({ devTools: false }).devTools, false);
  assert.ok(Object.isFrozen(HARDENED));
});

test('every BrowserWindow is built from the factory and loads app:// only (SEC-E1/E2)', () => {
  let windows = 0;
  for (const { f, text } of SOURCES) {
    const n = (text.match(/new BrowserWindow\(/g) || []).length;
    windows += n;
    if (n) {
      const calls = (text.match(/webPreferences: webPreferences\(/g) || []).length;
      assert.equal(calls, n, f);
    }
    assert.doesNotMatch(text, /loadFile\(/, f);
    for (const m of text.matchAll(/loadURL\(([^)]*)\)/g)) assert.match(m[1], /^ORIGIN\b/, f);
  }
  assert.ok(windows >= 1);
});

test('forbidden tokens absent from app source (SEC-E6/E8/E16, SEC-G1/G2/G6)', () => {
  const forbidden = [
    /webSecurity:\s*false/,
    /allowRunningInsecureContent:\s*true/,
    /experimentalFeatures:\s*true/,
    /enableBlinkFeatures/,
    /webviewTag:\s*true/,
    /nodeIntegration\w*:\s*true/,
    /contextIsolation:\s*false/,
    /sandbox:\s*false/,
    /@electron\/remote/,
    /<webview/i,
    /\b(OpenProcess|ReadProcessMemory|WriteProcessMemory|CreateRemoteThread|SetWindowsHookEx|SendInput|keybd_event|mouse_event)\b/,
    /\b(robotjs|nut-js|@nut-tree|ffi-napi|node-ffi|koffi)\b/,
    /globalShortcut/,
    /netconport|gamestate_integration/i,
    /'unsafe-(inline|eval)'/,
  ];
  for (const { f, text } of SOURCES) {
    for (const rx of forbidden) assert.doesNotMatch(text, rx, path.relative(APP, f) + ' ' + rx);
  }
});

test('no runtime dependencies beyond the budget; electron pinned exact (SEC-S4/E12/E16)', () => {
  assert.deepEqual(Object.keys(pkg.dependencies || {}), []);
  for (const [name, v] of Object.entries(pkg.devDependencies)) {
    assert.match(v, /^\d+\.\d+\.\d+$/, name + ' must be pinned exact');
  }
  const major = Number(pkg.devDependencies.electron.split('.')[0]);
  assert.ok(major >= 43, 'electron major ' + major + ' is out of the supported window; bump it');
});

test('app:// resolves only inside the renderer dir (SEC-E1)', () => {
  const ok = resolveRequest('app://vw/index.html', RENDERER);
  assert.ok(ok && ok.file.endsWith('index.html'));
  assert.equal(resolveRequest('app://vw/', RENDERER).file, ok.file);
  // The URL parser folds literal dot segments; whatever survives must stay
  // inside the renderer dir, and encoded traversal must be refused.
  for (const u of ['app://vw/../main/main.js', 'app://vw/%2e%2e/main/main.js']) {
    const r = resolveRequest(u, RENDERER);
    assert.ok(r === null || r.file.startsWith(RENDERER + path.sep), u);
  }
  assert.equal(resolveRequest('app://vw/..%2f..%2fpackage.json', RENDERER), null);
  assert.equal(resolveRequest('app://vw/..%5c..%5cpackage.json', RENDERER), null);
  assert.equal(resolveRequest('app://evil/index.html', RENDERER), null);
  assert.equal(resolveRequest('https://vw/index.html', RENDERER), null);
  assert.equal(resolveRequest('app://vw/x.exe', RENDERER), null);
  assert.ok(isAppUrl('app://vw/index.html'));
  assert.ok(!isAppUrl('https://example.com/'));
  assert.ok(!isAppUrl(undefined));
});

test('CSP header is strict and mirrored in the page (SEC-E7)', () => {
  const h = responseHeaders('text/html');
  assert.equal(h['content-security-policy'], CSP);
  assert.match(CSP, /default-src 'none'/);
  assert.match(CSP, /frame-ancestors 'none'/);
  const html = fs.readFileSync(path.join(RENDERER, 'index.html'), 'utf8');
  assert.ok(html.includes('content="' + CSP + '"'), 'meta CSP must equal the header');
  assert.doesNotMatch(html, /<script(?![^>]*\bsrc=)[^>]*>/i, 'inline script');
  assert.doesNotMatch(html, /\son\w+=/i, 'inline handler');
  assert.doesNotMatch(html, /\sstyle=/i, 'inline style');
  assert.doesNotMatch(html, /https?:\/\//i, 'remote content');
});

test('preload exposes a fixed API only (SEC-E13 shape)', () => {
  const text = fs.readFileSync(path.join(SRC, 'preload', 'preload.js'), 'utf8');
  assert.match(text, /contextBridge\.exposeInMainWorld\('vw'/);
  assert.doesNotMatch(text, /exposeInMainWorld\([^)]*ipcRenderer\s*\)/);
  assert.doesNotMatch(text, /\.send\(|\.on\(/);
  for (const m of text.matchAll(/require\('([^']+)'\)/g)) assert.equal(m[1], 'electron');
});

test('main wires the runtime guards (SEC-E4/E5/E9/E10/E15)', () => {
  const main = fs.readFileSync(path.join(SRC, 'main', 'main.js'), 'utf8');
  for (const needle of [
    'app.enableSandbox()',
    'requestSingleInstanceLock',
    "setWindowOpenHandler(() => ({ action: 'deny' }))",
    "'will-navigate'",
    "'will-redirect'",
    "'will-frame-navigate'",
    'setPermissionRequestHandler',
    'setPermissionCheckHandler',
    'senderFrame',
  ]) {
    assert.ok(main.includes(needle), needle);
  }
});

test('self-test passes on the source tree and catches a version mismatch', () => {
  const ok = runSelfTest({ version: pkg.version, target: pkg.version, appRoot: APP });
  assert.deepEqual(ok.failures, []);
  const bad = runSelfTest({ version: pkg.version, target: '9.9.9', appRoot: APP });
  assert.equal(bad.ok, false);
});

test('match gate: stub says not in match; a throwing provider fails closed', () => {
  setMatchProvider(null);
  assert.equal(isInMatch(), false);
  setMatchProvider(() => true);
  assert.equal(isInMatch(), true);
  setMatchProvider(() => {
    throw new Error('source down');
  });
  assert.equal(isInMatch(), true);
  setMatchProvider(null);
  const src = fs.readFileSync(path.join(SRC, 'main', 'matchGate.js'), 'utf8');
  assert.match(src, /TODO\(VW-APP-INGEST\)/);
});

test('every app source and script file is ASCII + LF', () => {
  const files = walk(SRC).concat(walk(path.join(APP, 'scripts')), walk(path.join(APP, 'test')));
  for (const extra of ['package.json', 'electron-builder.yml', '.npmrc', '.gitignore']) files.push(path.join(APP, extra));
  for (const f of files) {
    const b = fs.readFileSync(f);
    assert.ok(!b.includes(13) && !b.some((x) => x > 127), path.relative(APP, f));
  }
});
