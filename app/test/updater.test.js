'use strict';
// Updater core: SHA-256 refusal, self-test rollback, match gate (SEC-U2/U3).

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { createUpdater, MAX_BOOTS } = require('../src/main/updater/updater');
const { createStateStore } = require('../src/main/updater/state');
const { sha256Buffer } = require('../src/main/updater/sha');

const BASE = 'https://github.com/o/r/releases/download/';

function release(version, extra) {
  const name = 'VeilWalker-Setup-' + version + '.exe';
  return Object.assign(
    {
      version,
      prerelease: false,
      installer: { name, url: BASE + 'v' + version + '/' + name },
      sums: { name: 'SHA256SUMS.txt', url: BASE + 'v' + version + '/SHA256SUMS.txt' },
    },
    extra || {}
  );
}

// A fake GitHub: releases with installer bytes and the published sums.
function fakeWorld(opts) {
  const o = opts || {};
  const files = new Map();
  const rels = [];
  const downloads = [];
  function publish(version, bytes, publishedBytes) {
    const r = release(version);
    files.set(r.installer.url, Buffer.from(bytes));
    files.set(r.sums.url, Buffer.from(sha256Buffer(Buffer.from(publishedBytes || bytes)) + '  ' + r.installer.name + '\n'));
    rels.push(r);
    return r;
  }
  const feed = {
    async latest() {
      return rels.slice().sort((a, b) => (a.version < b.version ? 1 : -1))[0] || null;
    },
    async byVersion(v) {
      return rels.find((r) => r.version === v) || null;
    },
  };
  async function download(url) {
    downloads.push(url);
    if (!files.has(url)) throw new Error('404 ' + url);
    return files.get(url);
  }
  return { publish, feed, download, downloads, files, inMatch: Boolean(o.inMatch) };
}

function harness(world, version, extra) {
  const dir = extra && extra.dir ? extra.dir : fs.mkdtempSync(path.join(os.tmpdir(), 'vw-upd-'));
  const state = createStateStore(path.join(dir, 'state.json'));
  const installs = [];
  let quits = 0;
  const u = createUpdater(
    Object.assign(
      {
        currentVersion: version,
        feed: world.feed,
        download: world.download,
        dir,
        state,
        isInMatch: () => world.inMatch,
        runInstaller: async (file) => {
          installs.push(file);
        },
        quit: () => {
          quits += 1;
        },
        checkHours: 0,
      },
      extra || {}
    )
  );
  return { u, dir, state, installs, quits: () => quits };
}

test('SHA-256 mismatch: download refused, nothing staged, installer never run', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'TAMPERED-BYTES', 'installer-0.2.0');
  const h = harness(w, '0.1.0');
  const r = await h.u.tick();
  assert.equal(r.action, 'refused');
  assert.equal(r.reason, 'sha256-mismatch');
  assert.deepEqual(h.installs, []);
  assert.equal(h.state.read().staged, undefined);
  assert.equal(h.state.read().lastResult.reason, 'sha256-mismatch');
  const staged = path.join(h.dir, 'staged');
  assert.deepEqual(fs.existsSync(staged) ? fs.readdirSync(staged) : [], []);
});

test('rollback image mismatch also refuses the update', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'evil-0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const h = harness(w, '0.1.0');
  const r = await h.u.tick();
  assert.equal(r.action, 'refused');
  assert.equal(r.reason, 'rollback-sha256-mismatch');
  assert.deepEqual(h.installs, []);
});

test('missing published checksum refuses', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  const r2 = w.publish('0.2.0', 'installer-0.2.0');
  w.files.set(r2.sums.url, Buffer.from('deadbeef  other.exe\n'));
  const h = harness(w, '0.1.0');
  const r = await h.u.tick();
  assert.equal(r.reason, 'no-published-checksum');
  assert.deepEqual(h.installs, []);
});

test('staged installer tampered after verify is refused at apply', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const h = harness(w, '0.1.0', { isIdle: () => false });
  const r = await h.u.tick();
  assert.equal(r.action, 'deferred');
  const staged = h.state.read().staged;
  fs.writeFileSync(staged.installer, 'swapped');
  const a = await h.u.applyIfSafe('quit');
  assert.equal(a.action, 'refused');
  assert.equal(a.reason, 'sha256-mismatch-at-apply');
  assert.deepEqual(h.installs, []);
});

test('update deferred while in match: no download, no install; applies after the match', async () => {
  const w = fakeWorld({ inMatch: true });
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const h = harness(w, '0.1.0');
  const r = await h.u.tick();
  assert.equal(r.action, 'deferred');
  assert.equal(r.reason, 'in-match');
  assert.deepEqual(w.downloads, []);
  assert.deepEqual(h.installs, []);

  // Staged outside the match, then a match starts: quit-time apply still waits.
  w.inMatch = false;
  const st = await h.u.stage(await h.u.check());
  assert.ok(st.ok);
  w.inMatch = true;
  const q = await h.u.applyIfSafe('quit');
  assert.equal(q.action, 'deferred');
  assert.equal(q.reason, 'in-match');
  assert.deepEqual(h.installs, []);
  assert.equal(h.quits(), 0);

  w.inMatch = false;
  const go = await h.u.applyIfSafe('quit');
  assert.equal(go.action, 'applying');
  assert.equal(h.installs.length, 1);
  assert.match(h.installs[0], /VeilWalker-Setup-0\.2\.0\.exe$/);
  assert.equal(h.quits(), 1);
});

test('busy app defers the idle apply but not the natural-quit apply', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const h = harness(w, '0.1.0', { isIdle: () => false });
  assert.equal((await h.u.tick()).reason, 'busy');
  assert.equal((await h.u.applyIfSafe('quit')).action, 'applying');
});

test('failed self-test in the new build rolls back to the verified old installer', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const old = harness(w, '0.1.0');
  assert.equal((await old.u.tick()).action, 'applying');

  // The installer ran; the NEW build starts on the same user-data dir.
  const neu = harness(w, '0.2.0', { dir: old.dir });
  let tested = null;
  const r = await neu.u.onStartup(async (target) => {
    tested = target;
    return { ok: false, failures: ['missing src/renderer/index.html'] };
  });
  assert.equal(tested, '0.2.0');
  assert.equal(r.action, 'rolling-back');
  assert.equal(r.reason, 'self-test-failed');
  assert.equal(neu.installs.length, 1);
  assert.match(neu.installs[0], /rollback[\\/]VeilWalker-Setup-0\.1\.0\.exe$/);
  assert.equal(neu.quits(), 1);
  assert.equal(neu.state.read().skipVersion, '0.2.0');

  // The rollback installer relaunches the OLD build: recorded, and the bad
  // version is not offered again.
  const back = harness(w, '0.1.0', { dir: old.dir });
  const b = await back.u.onStartup(async () => ({ ok: true }));
  assert.equal(b.action, 'rolled-back');
  assert.equal(back.state.read().pending, undefined);
  const again = await back.u.tick();
  assert.equal(again.reason, 'up-to-date');
  assert.deepEqual(back.installs, []);
});

test('self-test that throws counts as a failure and rolls back', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const old = harness(w, '0.1.0');
  await old.u.tick();
  const neu = harness(w, '0.2.0', { dir: old.dir });
  const r = await neu.u.onStartup(async () => {
    throw new Error('boom');
  });
  assert.equal(r.action, 'rolling-back');
});

test('boot loop rolls back without waiting for a self-test', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const old = harness(w, '0.1.0');
  await old.u.tick();
  // Simulate MAX_BOOTS starts that died before the self-test finished.
  old.state.update((s) => {
    s.pending.boots = MAX_BOOTS;
    return s;
  });
  const neu = harness(w, '0.2.0', { dir: old.dir });
  let called = false;
  const r = await neu.u.onStartup(async () => {
    called = true;
    return { ok: true };
  });
  assert.equal(r.action, 'rolling-back');
  assert.equal(r.reason, 'boot-loop');
  assert.equal(called, false);
});

test('passing self-test completes the update and keeps the new image as next rollback', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const old = harness(w, '0.1.0');
  await old.u.tick();
  const neu = harness(w, '0.2.0', { dir: old.dir });
  const r = await neu.u.onStartup(async () => ({ ok: true, failures: [] }));
  assert.equal(r.action, 'updated');
  const s = neu.state.read();
  assert.equal(s.pending, undefined);
  assert.equal(s.current.version, '0.2.0');
  assert.deepEqual(neu.installs, []);
});

test('installer that did not take leaves the old build running and records it', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const old = harness(w, '0.1.0');
  await old.u.tick();
  const same = harness(w, '0.1.0', { dir: old.dir });
  const r = await same.u.onStartup(async () => ({ ok: true }));
  assert.equal(r.action, 'install-failed');
  assert.deepEqual(same.installs, []);
});

test('rollback refused when the rollback image was tampered', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  w.publish('0.2.0', 'installer-0.2.0');
  const old = harness(w, '0.1.0');
  await old.u.tick();
  const p = old.state.read().pending;
  fs.writeFileSync(p.rollback.installer, 'swapped');
  const neu = harness(w, '0.2.0', { dir: old.dir });
  const r = await neu.u.onStartup(async () => ({ ok: false }));
  assert.equal(r.action, 'rollback-failed');
  assert.deepEqual(neu.installs, []);
});

test('check is rate-limited by checkHours', async () => {
  const w = fakeWorld();
  w.publish('0.1.0', 'installer-0.1.0');
  let t = 1000;
  const h = harness(w, '0.1.0', { checkHours: 24, now: () => t });
  assert.equal((await h.u.tick()).reason, 'up-to-date');
  t += 3600 * 1000;
  assert.equal((await h.u.tick()).reason, 'not-due');
});

test('missing dependency fails closed', () => {
  assert.throws(() => createUpdater({ currentVersion: '0.1.0' }), /missing dependency/);
});
