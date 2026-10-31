'use strict';
// Ordered, immutable migrations (VW-APP-DB). A migration is a file
// `NNNN_name.sql` in the migrations dir; versions start at 1 and are
// contiguous. Each file's SHA-256 (LF-normalised text) is pinned in
// `manifest.json`; a file that is missing from the manifest or does not
// match it is refused, so an applied migration is never edited in place.
// A new schema version = a new file plus a new manifest line.

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const { StoreError } = require('./errors');

const DEFAULT_DIR = path.join(__dirname, 'migrations');
const FILE_RE = /^(\d{4})_([a-z0-9_]+)\.sql$/;
// Transactions belong to the runner: a migration that opens or ends one
// would break the all-or-nothing apply. (A trigger body's BEGIN / END is
// fine; the runner also checks the transaction is still open after each.)
const TXN_RE = /^\s*(BEGIN\s*(;|DEFERRED\b|IMMEDIATE\b|EXCLUSIVE\b|TRANSACTION\b)|COMMIT\b|END\s+TRANSACTION\b|ROLLBACK\b|SAVEPOINT\b|RELEASE\b)/im;

function sha256Text(text) {
  return crypto.createHash('sha256').update(String(text).replace(/\r\n/g, '\n'), 'utf8').digest('hex');
}

function readManifest(dir) {
  const file = path.join(dir, 'manifest.json');
  let doc;
  try {
    doc = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    throw new StoreError('MIGRATION_MANIFEST', 'migration manifest unreadable: ' + e.message);
  }
  if (!doc || typeof doc !== 'object' || typeof doc.migrations !== 'object' || !doc.migrations) {
    throw new StoreError('MIGRATION_MANIFEST', 'migration manifest has no "migrations" map');
  }
  return doc.migrations;
}

function loadMigrations(dir) {
  const root = dir || DEFAULT_DIR;
  const pins = readManifest(root);
  const names = fs
    .readdirSync(root)
    .filter((n) => n.endsWith('.sql'))
    .sort();
  const out = [];
  for (const name of names) {
    const m = FILE_RE.exec(name);
    if (!m) throw new StoreError('MIGRATION_NAME', 'bad migration file name: ' + name);
    const version = Number(m[1]);
    if (version !== out.length + 1) {
      throw new StoreError('MIGRATION_ORDER', 'migration ' + name + ' breaks the 1..N sequence');
    }
    const sql = fs.readFileSync(path.join(root, name), 'utf8');
    const sha256 = sha256Text(sql);
    if (!pins[name]) throw new StoreError('MIGRATION_UNPINNED', 'migration not in manifest: ' + name);
    if (pins[name] !== sha256) {
      throw new StoreError('MIGRATION_CHANGED', 'migration ' + name + ' differs from its pinned SHA-256');
    }
    if (TXN_RE.test(sql)) {
      throw new StoreError('MIGRATION_TXN', 'migration ' + name + ' must not control transactions');
    }
    out.push({ version, name, sql, sha256 });
  }
  for (const pinned of Object.keys(pins)) {
    if (!names.includes(pinned)) {
      throw new StoreError('MIGRATION_MISSING', 'pinned migration file missing: ' + pinned);
    }
  }
  return out;
}

module.exports = { loadMigrations, sha256Text, DEFAULT_DIR, FILE_RE };
