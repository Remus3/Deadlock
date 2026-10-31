'use strict';
// VW updater core (charter D-1 as amended by D-1a, docs/companion-app.md).
//
//   tick()      check the feed (rate-limited), stage a verified installer,
//               apply when safe. Never touches the network or applies while
//               a match is live (R-APP-2, SEC-U3).
//   stage()     download installer + SHA256SUMS.txt from the GitHub release,
//               refuse on any SHA-256 mismatch (SEC-U2); also fetch and verify
//               the CURRENT version's installer as the rollback image.
//   applyIfSafe(reason)
//               re-verify, record a pending marker, run the installer
//               silently (it relaunches the new build) and quit.
//   onStartup(selfTest)
//               in the new build, before any window: self-test; on failure
//               (or a boot loop) re-install the verified rollback image.
//
// Every side effect is injected so the logic tests without Electron.

const fs = require('node:fs');
const path = require('node:path');
const { sha256File, parseSums, sameHash } = require('./sha');
const { compareVersions, allowedUrl } = require('./feed');

const MAX_BOOTS = 2;
const HOUR_MS = 3600 * 1000;

function createUpdater(deps) {
  const d = Object.assign(
    {
      channel: 'stable',
      checkHours: 24,
      isIdle: () => true,
      now: () => Date.now(),
      log: () => {},
      quit: () => {},
    },
    deps
  );
  for (const k of ['currentVersion', 'feed', 'download', 'dir', 'state', 'isInMatch', 'runInstaller']) {
    if (d[k] === undefined || d[k] === null) throw new Error('updater: missing dependency ' + k);
  }
  const st = d.state;

  function record(result, extra) {
    const entry = Object.assign({ result, at: new Date(d.now()).toISOString() }, extra || {});
    st.update((s) => {
      s.lastResult = entry;
      return s;
    });
    d.log('update ' + result + (extra && extra.reason ? ' (' + extra.reason + ')' : ''));
    return entry;
  }

  // Download one asset and verify it against the release's SHA256SUMS.txt.
  async function fetchVerified(release, subdir) {
    if (!allowedUrl(release.installer.url) || !allowedUrl(release.sums.url)) {
      return { ok: false, reason: 'url-not-allowed' };
    }
    const sumsBuf = await d.download(release.sums.url);
    const expected = parseSums(sumsBuf.toString('utf8')).get(release.installer.name);
    if (!expected) return { ok: false, reason: 'no-published-checksum' };
    const dir = path.join(d.dir, subdir);
    fs.mkdirSync(dir, { recursive: true });
    const final = path.join(dir, release.installer.name);
    if (fs.existsSync(final) && sameHash(await sha256File(final), expected)) {
      return { ok: true, file: final, sha256: expected };
    }
    const partial = final + '.partial';
    fs.writeFileSync(partial, await d.download(release.installer.url));
    const got = await sha256File(partial);
    if (!sameHash(got, expected)) {
      fs.rmSync(partial, { force: true });
      return { ok: false, reason: 'sha256-mismatch', expected, got };
    }
    fs.renameSync(partial, final);
    return { ok: true, file: final, sha256: expected };
  }

  async function check() {
    const rel = await d.feed.latest(d.channel);
    if (!rel || compareVersions(rel.version, d.currentVersion) <= 0) return null;
    // A version that failed its self-test is not offered again (no update loop).
    if (st.read().skipVersion === rel.version) return null;
    return rel;
  }

  async function stage(release) {
    const next = await fetchVerified(release, 'staged');
    if (!next.ok) return { ok: false, ...record('refused', { version: release.version, reason: next.reason }) };
    const cur = await d.feed.byVersion(d.currentVersion);
    if (!cur) return { ok: false, ...record('refused', { version: release.version, reason: 'no-rollback-release' }) };
    const back = await fetchVerified(cur, 'rollback');
    if (!back.ok) return { ok: false, ...record('refused', { version: release.version, reason: 'rollback-' + back.reason }) };
    st.update((s) => {
      s.staged = {
        version: release.version,
        installer: next.file,
        sha256: next.sha256,
        rollback: { version: cur.version, installer: back.file, sha256: back.sha256 },
      };
      return s;
    });
    record('staged', { version: release.version });
    return { ok: true, version: release.version };
  }

  // reason: 'idle' (periodic, needs isIdle) or 'quit' (natural quit).
  async function applyIfSafe(reason) {
    const s = st.read();
    const staged = s.staged;
    if (!staged) return { action: 'nothing' };
    if (d.isInMatch()) return { action: 'deferred', ...record('deferred', { version: staged.version, reason: 'in-match' }) };
    if (reason !== 'quit' && !d.isIdle()) return { action: 'deferred', ...record('deferred', { version: staged.version, reason: 'busy' }) };
    // Re-verify both images right before use (no swap between stage and apply).
    for (const img of [staged, staged.rollback]) {
      let ok = false;
      try {
        ok = sameHash(await sha256File(img.installer), img.sha256);
      } catch (e) {
        ok = false;
      }
      if (!ok) {
        st.update((x) => {
          delete x.staged;
          return x;
        });
        return { action: 'refused', ...record('refused', { version: staged.version, reason: 'sha256-mismatch-at-apply' }) };
      }
    }
    st.update((x) => {
      x.pending = {
        phase: 'installing',
        target: staged.version,
        from: d.currentVersion,
        installer: staged.installer,
        sha256: staged.sha256,
        rollback: staged.rollback,
        boots: 0,
      };
      delete x.staged;
      return x;
    });
    record('applying', { version: staged.version });
    await d.runInstaller(staged.installer);
    d.quit();
    return { action: 'applying', version: staged.version };
  }

  async function tick() {
    if (d.isInMatch()) return { action: 'deferred', reason: 'in-match' };
    const s = st.read();
    if (!s.staged) {
      const due = !s.lastCheck || d.now() - s.lastCheck >= d.checkHours * HOUR_MS;
      if (!due) return { action: 'nothing', reason: 'not-due' };
      st.update((x) => {
        x.lastCheck = d.now();
        return x;
      });
      const rel = await check();
      if (!rel) return { action: 'nothing', reason: 'up-to-date' };
      const r = await stage(rel);
      if (!r.ok) return { action: 'refused', reason: r.reason };
    }
    return applyIfSafe('idle');
  }

  async function rollback(p, why) {
    let ok = false;
    try {
      ok = sameHash(await sha256File(p.rollback.installer), p.rollback.sha256);
    } catch (e) {
      ok = false;
    }
    if (!ok) {
      st.update((x) => {
        delete x.pending;
        return x;
      });
      return { action: 'rollback-failed', ...record('rollback-failed', { version: p.target, reason: 'rollback-image-' + why }) };
    }
    st.update((x) => {
      x.pending = Object.assign({}, p, { phase: 'rolling-back', why });
      x.skipVersion = p.target;
      return x;
    });
    record('rolling-back', { version: p.target, reason: why });
    await d.runInstaller(p.rollback.installer);
    d.quit();
    return { action: 'rolling-back', reason: why };
  }

  // Called first thing at startup, before any window. selfTest(version) ->
  // {ok, failures[]} (may be async).
  async function onStartup(selfTest) {
    const p = st.read().pending;
    if (!p) return { action: 'none' };
    if (p.phase === 'installing') {
      if (d.currentVersion === p.target) {
        const boots = (p.boots || 0) + 1;
        st.update((x) => {
          x.pending.boots = boots;
          return x;
        });
        if (boots > MAX_BOOTS) return rollback(p, 'boot-loop');
        let r;
        try {
          r = await selfTest(p.target);
        } catch (e) {
          r = { ok: false, failures: ['self-test threw: ' + (e && e.message)] };
        }
        if (!r || !r.ok) return rollback(p, 'self-test-failed');
        st.update((x) => {
          delete x.pending;
          // The verified installer of the running version is the next rollback image.
          x.current = { version: p.target, installer: p.installer, sha256: p.sha256 };
          return x;
        });
        return { action: 'updated', ...record('updated', { version: p.target, from: p.from }) };
      }
      st.update((x) => {
        delete x.pending;
        return x;
      });
      return { action: 'install-failed', ...record('install-failed', { version: p.target, reason: 'still-on-' + d.currentVersion }) };
    }
    if (p.phase === 'rolling-back') {
      st.update((x) => {
        delete x.pending;
        return x;
      });
      if (d.currentVersion === p.from) {
        return { action: 'rolled-back', ...record('rolled-back', { version: p.target, from: p.from, reason: p.why }) };
      }
      return { action: 'rollback-failed', ...record('rollback-failed', { version: p.target, reason: 'still-on-' + d.currentVersion }) };
    }
    return { action: 'none' };
  }

  return { tick, check, stage, applyIfSafe, onStartup, fetchVerified };
}

module.exports = { createUpdater, MAX_BOOTS };
