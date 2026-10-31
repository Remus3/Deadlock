'use strict';
// The renderer's tokens.css stays in sync with the VW-APP-UX token set.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');

const { expected, OUT } = require('../scripts/gen-tokens');

test('tokens.css matches config/app/tokens.json (run npm run tokens)', () => {
  assert.equal(fs.readFileSync(OUT, 'utf8'), expected());
});

test('write-feed resolves the repo from env and refuses junk', () => {
  const { resolveRepo } = require('../scripts/write-feed');
  assert.equal(resolveRepo({ VW_UPDATE_REPO: 'a/b' }), 'a/b');
  assert.equal(resolveRepo({ VW_UPDATE_REPO: 'nope', GITHUB_REPOSITORY: 'c/d' }), 'c/d');
});
