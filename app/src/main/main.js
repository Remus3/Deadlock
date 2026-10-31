'use strict';
// VeilWalker companion - Electron main process (VW-APP-SCAFFOLD).
// Game safety floor: this process never opens, reads, writes or sends input
// to the game. It is a separate OS window that loads only packaged pages.

const fs = require('node:fs');
const path = require('node:path');
const { app, BrowserWindow, ipcMain, net, protocol, session } = require('electron');

const { webPreferences } = require('./webprefs');
const { SCHEME, ORIGIN, resolveRequest, isAppUrl, responseHeaders } = require('./appProtocol');
const { runSelfTest } = require('./selftest');
const { isInMatch } = require('./matchGate');
const { createLog } = require('./log');
const { createStateStore } = require('./updater/state');
const { createGithubFeed } = require('./updater/feed');
const { createUpdater } = require('./updater/updater');
const { makeDownload, runInstaller } = require('./updater/platform');
const { createBus, createBusIpcHandler, CHANNEL: BUS_CHANNEL } = require('./bus');
const { openStore, storePaths } = require('./store');

const APP_ROOT = path.join(__dirname, '..', '..');
const RENDERER = path.join(APP_ROOT, 'src', 'renderer');
const TICK_MS = 15 * 60 * 1000;
const SELF_TEST = process.argv.includes('--vw-self-test');

// SEC-E4: sandbox every renderer, before ready.
app.enableSandbox();
protocol.registerSchemesAsPrivileged([
  { scheme: SCHEME, privileges: { standard: true, secure: true, supportFetchAPI: true } },
]);

const GOT_LOCK = SELF_TEST || app.requestSingleInstanceLock();
if (!GOT_LOCK) app.quit();

let log = () => {};
let updater = null;
let bus = null;
let store = null;
let mainWindow = null;
let quitting = false;

function readFeedConfig() {
  try {
    const doc = JSON.parse(fs.readFileSync(path.join(APP_ROOT, 'build', 'feed.json'), 'utf8'));
    if (doc && typeof doc.repo === 'string') return doc;
  } catch (e) {
    // no feed baked in: updater stays off (fail closed)
  }
  return null;
}

// VW-APP-DB: per-user SQLite store. A refused DB (newer schema, foreign
// file, failed migration) leaves the app running without a store; the
// pre-migration backup stays in <userData>/data/backups/.
function openAppStore() {
  try {
    const s = openStore(Object.assign(storePaths(app.getPath('userData')), { log }));
    log('store open at schema v' + s.version + (s.applied.length ? ' (migrated from v' + s.from + ')' : ''));
    return s;
  } catch (e) {
    log('store refused: ' + (e && e.code) + ' ' + (e && e.message));
    return null;
  }
}

function hardenWebContents() {
  app.on('web-contents-created', (_e, contents) => {
    contents.setWindowOpenHandler(() => ({ action: 'deny' }));
    const block = (ev, url) => {
      if (!isAppUrl(url)) ev.preventDefault();
    };
    contents.on('will-navigate', block);
    contents.on('will-redirect', block);
    contents.on('will-frame-navigate', (ev) => {
      if (!isAppUrl(ev.url)) ev.preventDefault();
    });
    contents.on('will-attach-webview', (ev) => ev.preventDefault());
  });
}

function denyPermissions() {
  const s = session.defaultSession;
  s.setPermissionRequestHandler((_wc, _perm, cb) => cb(false));
  s.setPermissionCheckHandler(() => false);
}

function registerProtocol() {
  protocol.handle(SCHEME, (request) => {
    const hit = resolveRequest(request.url, RENDERER);
    if (!hit) return new Response('not found', { status: 404 });
    try {
      return new Response(fs.readFileSync(hit.file), { status: 200, headers: responseHeaders(hit.type) });
    } catch (e) {
      return new Response('not found', { status: 404 });
    }
  });
}

function createDashboard() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 720,
    show: false,
    backgroundColor: '#0f1218',
    title: 'VeilWalker',
    autoHideMenuBar: true,
    webPreferences: webPreferences({ devTools: !app.isPackaged }),
  });
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
  mainWindow.loadURL(ORIGIN + '/index.html');
}

function registerIpc(state) {
  ipcMain.handle('vw:get-info', (event) => {
    const frameUrl = event.senderFrame && event.senderFrame.url;
    if (!isAppUrl(frameUrl)) {
      log('ipc refused: sender not app://');
      return null;
    }
    const s = state ? state.read() : {};
    return {
      version: app.getVersion(),
      inMatch: isInMatch(),
      update: s.lastResult ? { result: s.lastResult.result, version: s.lastResult.version || null } : null,
    };
  });
  // SEC-E13 runtime half (VW-APP-BUS): sender frame and payload checked here.
  ipcMain.handle(BUS_CHANNEL, createBusIpcHandler({ bus, isAppUrl, log: (l) => log(l) }));
}

function setupUpdater(state) {
  const feedCfg = readFeedConfig();
  if (!feedCfg || !app.isPackaged) {
    log('updater off (' + (feedCfg ? 'dev run' : 'no feed baked in') + ')');
    return null;
  }
  const cache = state.read().feedCache || { etag: null, body: null };
  const fetchImpl = (url, opts) => net.fetch(url, opts);
  return createUpdater({
    currentVersion: app.getVersion(),
    channel: feedCfg.channel === 'beta' ? 'beta' : 'stable',
    checkHours: Number(feedCfg.checkHours) > 0 ? Number(feedCfg.checkHours) : 24,
    feed: createGithubFeed({ repo: feedCfg.repo, fetchImpl, cache }),
    download: makeDownload(fetchImpl),
    dir: path.join(app.getPath('userData'), 'updates'),
    state,
    isInMatch,
    // Idle = no window focused (the player is in the game or away).
    isIdle: () => !BrowserWindow.getFocusedWindow(),
    runInstaller,
    log,
    quit: () => {
      quitting = true;
      app.quit();
    },
  });
}

async function selfTestMode() {
  const r = runSelfTest({ version: app.getVersion(), target: app.getVersion(), appRoot: APP_ROOT });
  const out = JSON.stringify(r);
  process.stdout.write(out + '\n');
  const arg = process.argv.find((a) => a.startsWith('--vw-self-test-out='));
  if (arg) {
    try {
      fs.writeFileSync(arg.slice('--vw-self-test-out='.length), out + '\n', 'utf8');
    } catch (e) {
      // stdout already carries the result
    }
  }
  app.exit(r.ok ? 0 : 1);
}

app.whenReady().then(async () => {
  if (SELF_TEST) return selfTestMode();
  if (!GOT_LOCK) return undefined;
  log = createLog(path.join(app.getPath('userData'), 'logs', 'main.log'));
  const state = createStateStore(path.join(app.getPath('userData'), 'updates', 'state.json'));
  bus = createBus({ log: (l) => log(l) });
  hardenWebContents();
  denyPermissions();
  registerProtocol();
  registerIpc(state);
  store = openAppStore();

  updater = setupUpdater(state);
  if (updater) {
    const first = await updater.onStartup(async (target) =>
      runSelfTest({ version: app.getVersion(), target, appRoot: APP_ROOT })
    );
    if (first.action === 'rolling-back') return undefined;
  }

  createDashboard();

  if (updater) {
    const tick = () => updater.tick().catch((e) => log('update tick error: ' + (e && e.message)));
    setTimeout(tick, 60 * 1000);
    setInterval(tick, TICK_MS).unref();
  }
  return undefined;
});

app.on('second-instance', () => {
  // SEC-E15: focus the dashboard, never during a match (R-APP-2).
  if (mainWindow && !isInMatch()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

// Natural quit: the one moment besides idle that a staged update may apply.
app.on('before-quit', (ev) => {
  if (quitting || !updater) return;
  ev.preventDefault();
  quitting = true;
  updater
    .applyIfSafe('quit')
    .catch((e) => log('apply on quit error: ' + (e && e.message)))
    .finally(() => app.quit());
});

app.on('will-quit', () => {
  if (store) store.close();
  store = null;
});

app.on('window-all-closed', () => app.quit());
