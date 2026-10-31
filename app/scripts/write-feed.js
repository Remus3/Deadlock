'use strict';
// Bake the update feed into build/feed.json (gitignored). The repo's
// owner/repo is never tracked (privacy rule); it comes from VW_UPDATE_REPO,
// else GITHUB_REPOSITORY (CI), else the local git remote "origin".
// No repo found -> no feed file -> the packaged updater stays off.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const OUT = path.join(__dirname, '..', 'build', 'feed.json');
const SLUG = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;

function fromRemote() {
  try {
    const url = execFileSync('git', ['remote', 'get-url', 'origin'], { encoding: 'utf8' }).trim();
    const m = /github\.com[/:]([A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+?)(?:\.git)?$/.exec(url);
    return m ? m[1] : '';
  } catch (e) {
    return '';
  }
}

function resolveRepo(env) {
  for (const v of [env.VW_UPDATE_REPO, env.GITHUB_REPOSITORY]) {
    if (v && SLUG.test(v)) return v;
  }
  return fromRemote();
}

if (require.main === module) {
  const repo = resolveRepo(process.env);
  if (!repo || !SLUG.test(repo)) {
    fs.rmSync(OUT, { force: true });
    process.stdout.write('feed: none (updater will be off)\n');
  } else {
    const channel = process.env.VW_UPDATE_CHANNEL === 'beta' ? 'beta' : 'stable';
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify({ repo, channel, checkHours: 24 }) + '\n', 'utf8');
    process.stdout.write('feed: written (' + channel + ')\n');
  }
}

module.exports = { resolveRepo };
