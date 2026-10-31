'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { createGithubFeed, toRelease, compareVersions, allowedUrl } = require('../src/main/updater/feed');
const { parseSums, sameHash } = require('../src/main/updater/sha');

const DL = 'https://github.com/o/r/releases/download/';

function ghRelease(tag, opts) {
  const o = opts || {};
  const v = tag.replace(/^v/, '');
  return {
    tag_name: tag,
    draft: Boolean(o.draft),
    prerelease: Boolean(o.prerelease),
    assets: [
      { name: 'VeilWalker-Setup-' + v + '.exe', browser_download_url: o.url || DL + tag + '/VeilWalker-Setup-' + v + '.exe' },
      { name: 'SHA256SUMS.txt', browser_download_url: DL + tag + '/SHA256SUMS.txt' },
    ],
  };
}

function fakeFetch(body) {
  const calls = [];
  async function f(url, opts) {
    calls.push({ url, headers: opts.headers });
    if (opts.headers['if-none-match'] === '"e1"') return { status: 304, ok: false, headers: { get: () => null } };
    return { status: 200, ok: true, json: async () => body, headers: { get: (k) => (k === 'etag' ? '"e1"' : null) } };
  }
  f.calls = calls;
  return f;
}

test('compareVersions orders releases and prereleases', () => {
  assert.equal(compareVersions('0.2.0', '0.1.9'), 1);
  assert.equal(compareVersions('0.1.0', '0.1.0'), 0);
  assert.equal(compareVersions('0.2.0-beta.1', '0.2.0'), -1);
  assert.equal(compareVersions('v1.0.0', '0.9.9'), 1);
});

test('toRelease drops drafts, off-GitHub urls and releases without sums', () => {
  assert.equal(toRelease(ghRelease('v0.2.0', { draft: true })), null);
  assert.equal(toRelease(ghRelease('v0.2.0', { url: 'http://github.com/x.exe' })), null);
  assert.equal(toRelease(ghRelease('v0.2.0', { url: 'https://evil.example.com/VeilWalker-Setup-0.2.0.exe' })), null);
  const noSums = ghRelease('v0.2.0');
  noSums.assets.pop();
  assert.equal(toRelease(noSums), null);
  assert.equal(toRelease(ghRelease('v0.2.0')).version, '0.2.0');
});

test('allowedUrl accepts only https GitHub hosts', () => {
  assert.ok(allowedUrl('https://github.com/o/r/releases/download/v1/a.exe'));
  assert.ok(allowedUrl('https://release-assets.githubusercontent.com/x'));
  assert.ok(!allowedUrl('http://github.com/a'));
  assert.ok(!allowedUrl('https://github.com.evil.example/a'));
  assert.ok(!allowedUrl('file:///c:/a.exe'));
});

test('stable channel skips prereleases; beta takes them', async () => {
  const body = [ghRelease('v0.3.0-beta.1', { prerelease: true }), ghRelease('v0.2.0'), ghRelease('v0.1.0')];
  const feed = createGithubFeed({ repo: 'o/r', fetchImpl: fakeFetch(body) });
  assert.equal((await feed.latest('stable')).version, '0.2.0');
  assert.equal((await feed.latest('beta')).version, '0.3.0-beta.1');
  assert.equal((await feed.byVersion('0.1.0')).version, '0.1.0');
});

test('feed sends If-None-Match and reuses the cached body on 304', async () => {
  const f = fakeFetch([ghRelease('v0.2.0')]);
  const feed = createGithubFeed({ repo: 'o/r', fetchImpl: f });
  await feed.latest('stable');
  const second = await feed.latest('stable');
  assert.equal(second.version, '0.2.0');
  assert.equal(f.calls[1].headers['if-none-match'], '"e1"');
  assert.match(f.calls[0].url, /^https:\/\/api\.github\.com\/repos\/o\/r\/releases/);
});

test('feed refuses a malformed repo slug', () => {
  assert.throws(() => createGithubFeed({ repo: 'https://x/y', fetchImpl: fakeFetch([]) }));
});

test('parseSums drops ambiguous names and malformed lines', () => {
  const a = 'a'.repeat(64);
  const b = 'b'.repeat(64);
  const m = parseSums(a + '  one.exe\r\n' + b + ' *two.exe\nnot a line\n' + a + '  dup.exe\n' + b + '  dup.exe\n');
  assert.equal(m.get('one.exe'), a);
  assert.equal(m.get('two.exe'), b);
  assert.equal(m.has('dup.exe'), false);
  assert.ok(sameHash(a, a.toUpperCase()));
  assert.ok(!sameHash(a, b));
  assert.ok(!sameHash(a, 'short'));
});
