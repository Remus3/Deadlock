'use strict';
// GitHub Releases feed (SEC-U1): one unauthenticated GET of this repo's
// releases list, ETag-cached; only https on GitHub hosts is accepted. The
// owner/repo is not tracked in the repo (privacy rule): it is baked into the
// package at build time (scripts/write-feed.js -> build/feed.json).

const INSTALLER_RE = /^VeilWalker-Setup-(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\.exe$/;
const SUMS_NAME = 'SHA256SUMS.txt';
const ALLOWED_HOSTS = [/^github\.com$/, /^api\.github\.com$/, /^[a-z0-9-]+\.githubusercontent\.com$/];

function allowedUrl(raw) {
  try {
    const u = new URL(raw);
    return u.protocol === 'https:' && ALLOWED_HOSTS.some((rx) => rx.test(u.hostname));
  } catch (e) {
    return false;
  }
}

function parseVersion(v) {
  const m = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$/.exec(String(v || ''));
  if (!m) return null;
  return { major: +m[1], minor: +m[2], patch: +m[3], pre: m[4] || '' };
}

// -1 / 0 / 1; a prerelease sorts before its release.
function compareVersions(a, b) {
  const x = parseVersion(a);
  const y = parseVersion(b);
  if (!x || !y) throw new Error('bad version');
  for (const k of ['major', 'minor', 'patch']) {
    if (x[k] !== y[k]) return x[k] < y[k] ? -1 : 1;
  }
  if (x.pre === y.pre) return 0;
  if (!x.pre) return 1;
  if (!y.pre) return -1;
  return x.pre < y.pre ? -1 : 1;
}

// Reduce a GitHub release object to what the updater needs, or null.
function toRelease(rel) {
  if (!rel || rel.draft) return null;
  const version = String(rel.tag_name || '').replace(/^v/, '');
  if (!parseVersion(version)) return null;
  const assets = Array.isArray(rel.assets) ? rel.assets : [];
  const inst = assets.find((a) => {
    const m = INSTALLER_RE.exec(a.name || '');
    return m && m[1] === version;
  });
  const sums = assets.find((a) => a.name === SUMS_NAME);
  if (!inst || !sums) return null;
  if (!allowedUrl(inst.browser_download_url) || !allowedUrl(sums.browser_download_url)) return null;
  return {
    version,
    prerelease: Boolean(rel.prerelease),
    installer: { name: inst.name, url: inst.browser_download_url },
    sums: { name: SUMS_NAME, url: sums.browser_download_url },
  };
}

function createGithubFeed(opts) {
  const repo = opts.repo;
  const fetchImpl = opts.fetchImpl;
  const cache = opts.cache || { etag: null, body: null };
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo || '')) throw new Error('feed repo must be owner/repo');
  const listUrl = 'https://api.github.com/repos/' + repo + '/releases?per_page=30';

  async function list() {
    const headers = { accept: 'application/vnd.github+json', 'user-agent': 'veilwalker-updater' };
    if (cache.etag) headers['if-none-match'] = cache.etag;
    const res = await fetchImpl(listUrl, { headers });
    if (res.status === 304 && cache.body) return cache.body;
    if (!res.ok) throw new Error('feed http ' + res.status);
    const body = await res.json();
    cache.etag = (res.headers && res.headers.get && res.headers.get('etag')) || null;
    cache.body = body;
    return body;
  }

  async function releases(channel) {
    const body = await list();
    return (Array.isArray(body) ? body : [])
      .map(toRelease)
      .filter((r) => r && (channel === 'beta' || !r.prerelease));
  }

  return {
    cache,
    async latest(channel) {
      const rs = await releases(channel);
      rs.sort((a, b) => compareVersions(b.version, a.version));
      return rs[0] || null;
    },
    async byVersion(version) {
      const rs = await releases('beta');
      return rs.find((r) => r.version === version) || null;
    },
  };
}

module.exports = { createGithubFeed, toRelease, compareVersions, parseVersion, allowedUrl, SUMS_NAME };
