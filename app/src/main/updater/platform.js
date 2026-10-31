'use strict';
// Electron-side wiring for the updater: HTTPS download through Chromium's
// net stack (GitHub hosts only), and the silent per-user NSIS run.

const { spawn } = require('node:child_process');
const { allowedUrl } = require('./feed');

const MAX_BYTES = 400 * 1024 * 1024;

function makeDownload(fetchImpl) {
  return async function download(url) {
    if (!allowedUrl(url)) throw new Error('download url not allowed');
    const res = await fetchImpl(url, { redirect: 'follow', headers: { 'user-agent': 'veilwalker-updater' } });
    if (!res.ok) throw new Error('download http ' + res.status);
    if (res.url && !allowedUrl(res.url)) throw new Error('redirected off GitHub');
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length > MAX_BYTES) throw new Error('download too large');
    return buf;
  };
}

// electron-builder NSIS flags: /S silent, --updated marks an update run,
// --force-run relaunches the app after install. Detached so it outlives us.
function runInstaller(file) {
  return new Promise((resolve, reject) => {
    const child = spawn(file, ['/S', '--updated', '--force-run'], {
      detached: true,
      stdio: 'ignore',
      windowsHide: true,
    });
    child.once('error', reject);
    child.once('spawn', () => {
      child.unref();
      resolve();
    });
  });
}

module.exports = { makeDownload, runInstaller };
