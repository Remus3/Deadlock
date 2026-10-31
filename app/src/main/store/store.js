'use strict';
// Local SQLite store (VW-APP-DB, charter R-DATA-1, SEC-P2). Zero runtime
// dependencies: Node's built-in `node:sqlite` (DatabaseSync), present
// without flags in Node 24 and in Electron 45's main process (decision
// D-DB in docs/companion-app.md section 8).
//
// openStore():
// - refuses a DB whose schema_version is newer than the newest migration
//   this build knows (DB_TOO_NEW), or a DB with tables but no
//   schema_version (NOT_VW_DB), before any write;
// - refuses when an applied migration's recorded SHA-256 differs from the
//   shipped file (MIGRATION_CHANGED): migrations are immutable;
// - with pending migrations on an existing DB, first writes a consistent
//   backup copy (`VACUUM INTO`) to the backup dir and prunes that dir to the
//   newest `keepBackups` copies;
// - applies every pending migration in ONE transaction; any failure rolls
//   the whole batch back (the DB stays at its old version) and the backup
//   is kept;
// - a second open with nothing pending changes nothing (idempotent).

const fs = require('node:fs');
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');

const { StoreError } = require('./errors');
const { loadMigrations } = require('./migrations');

const DB_NAME = 'veilwalker.db';
const KEEP_BACKUPS = 5;
const BACKUP_RE = /^veilwalker-v(\d+)-(\d{8}T\d{9}Z)(?:-(\d+))?\.db$/;

const SCHEMA_VERSION_DDL =
  'CREATE TABLE IF NOT EXISTS schema_version (' +
  'version INTEGER PRIMARY KEY NOT NULL, ' +
  'name TEXT NOT NULL, ' +
  'sha256 TEXT NOT NULL, ' +
  'applied_at TEXT NOT NULL)';

// Per-user location, resolved at run time from Electron's userData dir.
function storePaths(userDataDir) {
  if (!userDataDir || !path.isAbsolute(userDataDir)) {
    throw new StoreError('BAD_PATH', 'userData dir must be an absolute path');
  }
  const dir = path.join(userDataDir, 'data');
  return { file: path.join(dir, DB_NAME), backupDir: path.join(dir, 'backups') };
}

function hasTable(db, name) {
  return !!db.prepare("SELECT 1 AS x FROM sqlite_master WHERE type = 'table' AND name = ?").get(name);
}

function userTableCount(db) {
  return db.prepare("SELECT COUNT(*) AS n FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").get().n;
}

function readVersion(db) {
  if (!hasTable(db, 'schema_version')) {
    if (userTableCount(db) > 0) {
      throw new StoreError('NOT_VW_DB', 'database has tables but no schema_version; refusing to touch it');
    }
    return 0;
  }
  const row = db.prepare('SELECT MAX(version) AS v FROM schema_version').get();
  return row && row.v ? Number(row.v) : 0;
}

function verifyApplied(db, migrations) {
  if (!hasTable(db, 'schema_version')) return;
  const rows = db.prepare('SELECT version, name, sha256 FROM schema_version ORDER BY version').all();
  for (const r of rows) {
    const m = migrations[Number(r.version) - 1];
    if (!m) continue; // newer than this build: caught by the version check
    if (m.sha256 !== r.sha256 || m.name !== r.name) {
      throw new StoreError(
        'MIGRATION_CHANGED',
        'applied migration v' + r.version + ' (' + r.name + ') does not match the shipped ' + m.name
      );
    }
  }
}

function stamp(date) {
  // 2026-10-31T12:34:56.789Z -> 20261031T123456789Z (sortable, file-safe)
  return date.toISOString().replace(/[-:.]/g, '');
}

function listBackups(backupDir) {
  let names;
  try {
    names = fs.readdirSync(backupDir);
  } catch (e) {
    return [];
  }
  return names
    .map((n) => ({ n, m: BACKUP_RE.exec(n) }))
    .filter((x) => x.m)
    .sort((a, b) => {
      if (a.m[2] !== b.m[2]) return a.m[2] < b.m[2] ? -1 : 1;
      return Number(a.m[3] || 0) - Number(b.m[3] || 0);
    })
    .map((x) => x.n);
}

function takeBackup(db, backupDir, fromVersion, now) {
  fs.mkdirSync(backupDir, { recursive: true });
  const base = 'veilwalker-v' + fromVersion + '-' + stamp(now);
  let file = path.join(backupDir, base + '.db');
  for (let i = 1; fs.existsSync(file); i += 1) file = path.join(backupDir, base + '-' + i + '.db');
  // VACUUM INTO writes a consistent, self-contained copy (WAL-safe).
  db.prepare('VACUUM INTO ?').run(file);
  return file;
}

function pruneBackups(backupDir, keep) {
  const all = listBackups(backupDir);
  const drop = all.slice(0, Math.max(0, all.length - keep));
  for (const n of drop) {
    try {
      fs.unlinkSync(path.join(backupDir, n));
    } catch (e) {
      // a locked old backup is retried on the next migration
    }
  }
  return drop;
}

function applyPending(db, pending, now) {
  db.exec('BEGIN IMMEDIATE');
  let current = null;
  try {
    db.exec(SCHEMA_VERSION_DDL);
    const ins = db.prepare('INSERT INTO schema_version (version, name, sha256, applied_at) VALUES (?, ?, ?, ?)');
    for (const m of pending) {
      current = m;
      db.exec(m.sql);
      if (typeof db.isTransaction === 'boolean' && !db.isTransaction) {
        throw new Error('migration ended the runner transaction');
      }
      ins.run(m.version, m.name, m.sha256, now.toISOString());
    }
    db.exec('COMMIT');
  } catch (e) {
    try {
      if (typeof db.isTransaction !== 'boolean' || db.isTransaction) db.exec('ROLLBACK');
    } catch (e2) {
      // nothing open to roll back
    }
    const which = current ? 'v' + current.version + ' (' + current.name + ')' : 'bootstrap';
    throw new StoreError('MIGRATION_FAILED', 'migration ' + which + ' failed: ' + e.message, e);
  }
}

function openStore(opts) {
  const o = opts || {};
  if (!o.file) throw new StoreError('BAD_PATH', 'openStore needs { file }');
  const log = typeof o.log === 'function' ? o.log : () => {};
  const now = typeof o.now === 'function' ? o.now : () => new Date();
  const keep = Number.isInteger(o.keepBackups) && o.keepBackups > 0 ? o.keepBackups : KEEP_BACKUPS;
  const backupDir = o.backupDir || path.join(path.dirname(o.file), 'backups');
  const migrations = loadMigrations(o.migrationsDir);
  const latest = migrations.length;

  fs.mkdirSync(path.dirname(o.file), { recursive: true });
  const existed = fs.existsSync(o.file) && fs.statSync(o.file).size > 0;
  const db = new DatabaseSync(o.file);
  try {
    const from = readVersion(db);
    if (from > latest) {
      throw new StoreError(
        'DB_TOO_NEW',
        'database schema v' + from + ' is newer than this build knows (v' + latest + '); update the app'
      );
    }
    verifyApplied(db, migrations);
    db.exec('PRAGMA foreign_keys = ON');
    const pending = migrations.slice(from);
    let backup = null;
    let pruned = [];
    if (pending.length) {
      if (existed) {
        backup = takeBackup(db, backupDir, from, now());
        pruned = pruneBackups(backupDir, keep);
        log('store: backup of v' + from + ' written before migrating');
      }
      applyPending(db, pending, now());
      log('store: migrated v' + from + ' -> v' + latest);
    }
    return {
      db,
      file: o.file,
      version: latest,
      from,
      applied: pending.map((m) => m.version),
      backup,
      pruned,
      close: () => db.close(),
    };
  } catch (e) {
    try {
      db.close();
    } catch (e2) {
      // already closed
    }
    throw e;
  }
}

module.exports = { openStore, storePaths, listBackups, DB_NAME, KEEP_BACKUPS, BACKUP_RE };
