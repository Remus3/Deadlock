'use strict';
// VW-APP-DB: SQLite store, versioned migrations, backup, rollback, refusal.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const { openStore, storePaths, listBackups, loadMigrations, sha256Text, StoreError } = require('../src/main/store');
const { DEFAULT_DIR } = require('../src/main/store/migrations');

// Released migrations, pinned a second time here: editing a released file
// AND its manifest line still fails this test. Append a line per release.
const RELEASED = {
  '0001_init.sql': 'a9eda0ea817d18d9d2027294b9587f6cdb0b29878421dac946cfa2dfba5a7ba6',
};

const FIXTURE = [
  ['0001_people.sql', 'CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT NOT NULL);\n'],
  ['0002_people_age.sql', 'ALTER TABLE people ADD COLUMN age INTEGER;\n'],
  [
    '0003_audit.sql',
    'CREATE TABLE audit (id INTEGER PRIMARY KEY, what TEXT NOT NULL);\n' +
      'CREATE TRIGGER people_ins AFTER INSERT ON people\n' +
      'BEGIN\n  INSERT INTO audit (what) VALUES (NEW.name);\nEND;\n',
  ],
];

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'vw-store-'));
}

function writeMigrations(dir, entries) {
  fs.mkdirSync(dir, { recursive: true });
  const pins = {};
  for (const [name, sql] of entries) {
    fs.writeFileSync(path.join(dir, name), sql, 'utf8');
    pins[name] = sha256Text(sql);
  }
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify({ migrations: pins }), 'utf8');
  return dir;
}

function fileSha(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function versionOf(file) {
  const db = new DatabaseSync(file, { readOnly: true });
  try {
    return db.prepare('SELECT MAX(version) AS v FROM schema_version').get().v;
  } finally {
    db.close();
  }
}

function setup(upTo) {
  const root = tmp();
  const file = path.join(root, 'data', 'veilwalker.db');
  const backupDir = path.join(root, 'data', 'backups');
  if (upTo > 0) {
    const s = openStore({ file, backupDir, migrationsDir: writeMigrations(path.join(root, 'm' + upTo), FIXTURE.slice(0, upTo)) });
    s.close();
  }
  return { root, file, backupDir };
}

let clock = Date.parse('2026-10-31T10:00:00.000Z');
const tick = () => new Date((clock += 1000));

// --- shipped migrations ---------------------------------------------------

test('shipped migrations are contiguous, pinned and released ones unchanged', () => {
  const ms = loadMigrations();
  assert.ok(ms.length >= 1);
  ms.forEach((m, i) => assert.equal(m.version, i + 1));
  const manifest = JSON.parse(fs.readFileSync(path.join(DEFAULT_DIR, 'manifest.json'), 'utf8')).migrations;
  for (const [name, sha] of Object.entries(RELEASED)) {
    assert.equal(manifest[name], sha, name + ' manifest pin changed');
    assert.equal(ms.find((m) => m.name === name).sha256, sha, name + ' file changed');
  }
});

test('shipped migrations apply from empty and are idempotent', () => {
  const { file } = setup(0);
  const s1 = openStore({ file });
  assert.equal(s1.from, 0);
  assert.equal(s1.version, loadMigrations().length);
  assert.equal(s1.backup, null, 'fresh DB has nothing to back up');
  s1.db.prepare("INSERT INTO kv (key, value, updated_at) VALUES ('k', 'v', 'now')").run();
  s1.close();
  const before = fileSha(file);
  const s2 = openStore({ file });
  assert.deepEqual(s2.applied, []);
  assert.equal(s2.db.prepare("SELECT value FROM kv WHERE key = 'k'").get().value, 'v');
  s2.close();
  assert.equal(fileSha(file), before, 'a no-op open must not change the file');
});

// --- paths ----------------------------------------------------------------

test('DB lives under the per-user userData dir, resolved at run time', () => {
  const ud = path.join(tmp(), 'VeilWalker');
  const p = storePaths(ud);
  assert.equal(path.dirname(path.dirname(p.file)), ud);
  assert.equal(path.basename(p.file), 'veilwalker.db');
  assert.ok(p.backupDir.startsWith(path.join(ud, 'data')));
  assert.throws(() => storePaths('relative/dir'), (e) => e.code === 'BAD_PATH');
  assert.throws(() => storePaths(''), (e) => e.code === 'BAD_PATH');
  const main = fs.readFileSync(path.join(__dirname, '..', 'src', 'main', 'main.js'), 'utf8');
  assert.match(main, /storePaths\(app\.getPath\('userData'\)\)/);
});

// --- schema_version and migrate-up ----------------------------------------

test('schema_version records every applied migration with its SHA-256', () => {
  const { root, file } = setup(0);
  const dir = writeMigrations(path.join(root, 'm'), FIXTURE);
  const s = openStore({ file, migrationsDir: dir, now: tick });
  const rows = s.db.prepare('SELECT version, name, sha256 FROM schema_version ORDER BY version').all();
  assert.deepEqual(
    rows.map((r) => [r.version, r.name, r.sha256]),
    FIXTURE.map(([n, sql], i) => [i + 1, n, sha256Text(sql)])
  );
  s.close();
});

for (let from = 0; from <= FIXTURE.length; from += 1) {
  test('migrate up from v' + from + ' reaches v' + FIXTURE.length + ' and is idempotent', () => {
    const { root, file, backupDir } = setup(from);
    const dir = writeMigrations(path.join(root, 'all'), FIXTURE);
    const s1 = openStore({ file, backupDir, migrationsDir: dir, now: tick });
    assert.equal(s1.from, from);
    assert.equal(s1.version, FIXTURE.length);
    assert.deepEqual(s1.applied, FIXTURE.slice(from).map((_x, i) => from + i + 1));
    s1.db.prepare("INSERT INTO people (name, age) VALUES ('a', 1)").run();
    assert.equal(s1.db.prepare('SELECT COUNT(*) AS n FROM audit').get().n, 1);
    s1.close();
    const backupsAfterFirst = listBackups(backupDir);
    const sha = fileSha(file);
    const s2 = openStore({ file, backupDir, migrationsDir: dir, now: tick });
    assert.deepEqual(s2.applied, []);
    assert.equal(s2.backup, null);
    s2.close();
    assert.equal(fileSha(file), sha);
    assert.deepEqual(listBackups(backupDir), backupsAfterFirst, 'no backup when nothing is pending');
    assert.equal(versionOf(file), FIXTURE.length);
  });
}

// --- backup ---------------------------------------------------------------

test('a backup of the pre-migration DB is taken first and kept', () => {
  const { root, file, backupDir } = setup(1);
  const db = new DatabaseSync(file);
  db.prepare("INSERT INTO people (name) VALUES ('keep-me')").run();
  db.close();
  const s = openStore({ file, backupDir, migrationsDir: writeMigrations(path.join(root, 'all'), FIXTURE), now: tick });
  assert.ok(s.backup && fs.existsSync(s.backup));
  assert.match(path.basename(s.backup), /^veilwalker-v1-\d{8}T\d{9}Z\.db$/);
  s.close();
  assert.equal(versionOf(s.backup), 1, 'backup holds the old schema version');
  const b = new DatabaseSync(s.backup, { readOnly: true });
  assert.equal(b.prepare('SELECT name FROM people').get().name, 'keep-me');
  b.close();
  assert.deepEqual(listBackups(backupDir), [path.basename(s.backup)]);
});

test('backups are bounded to keepBackups, oldest pruned first', () => {
  const { root, file, backupDir } = setup(0);
  const keep = 2;
  for (let v = 1; v <= FIXTURE.length; v += 1) {
    const dir = writeMigrations(path.join(root, 'k' + v), FIXTURE.slice(0, v));
    openStore({ file, backupDir, keepBackups: keep, migrationsDir: dir, now: tick }).close();
  }
  // v0 -> v1 is a fresh file (no backup); v1 -> v2 and v2 -> v3 back up.
  assert.deepEqual(listBackups(backupDir).map((n) => n.split('-')[1]), ['v1', 'v2']);
  // Seed older junk-free backups and push past the bound.
  fs.writeFileSync(path.join(backupDir, 'veilwalker-v0-20200101T000000000Z.db'), '');
  fs.writeFileSync(path.join(backupDir, 'unrelated.txt'), 'x');
  const dir4 = writeMigrations(path.join(root, 'k4'), FIXTURE.concat([['0004_more.sql', 'CREATE TABLE more (x INTEGER);\n']]));
  const s = openStore({ file, backupDir, keepBackups: keep, migrationsDir: dir4, now: tick });
  s.close();
  const left = listBackups(backupDir);
  assert.equal(left.length, keep);
  assert.equal(left[left.length - 1], path.basename(s.backup));
  assert.ok(!left.includes('veilwalker-v0-20200101T000000000Z.db'), 'oldest pruned');
  assert.ok(fs.existsSync(path.join(backupDir, 'unrelated.txt')), 'non-backup files untouched');
});

// --- failure and rollback -------------------------------------------------

test('a failed migration rolls the whole batch back and keeps the backup', () => {
  const { root, file, backupDir } = setup(1);
  const db = new DatabaseSync(file);
  db.prepare("INSERT INTO people (name) VALUES ('x')").run();
  db.close();
  const sha = fileSha(file);
  const bad = FIXTURE.slice(0, 2).concat([['0003_broken.sql', 'CREATE TABLE ok_one (x INTEGER);\nTHIS IS NOT SQL;\n']]);
  const dir = writeMigrations(path.join(root, 'bad'), bad);
  assert.throws(
    () => openStore({ file, backupDir, migrationsDir: dir, now: tick }),
    (e) => e instanceof StoreError && e.code === 'MIGRATION_FAILED' && /v3/.test(e.message)
  );
  assert.equal(versionOf(file), 1, 'v2 (which succeeded) rolled back with v3');
  const check = new DatabaseSync(file, { readOnly: true });
  const cols = check.prepare('PRAGMA table_info(people)').all().map((c) => c.name);
  assert.ok(!cols.includes('age'));
  assert.equal(check.prepare("SELECT COUNT(*) AS n FROM sqlite_master WHERE name = 'ok_one'").get().n, 0);
  check.close();
  assert.equal(fileSha(file), sha, 'DB bytes equal the pre-migration state');
  const backups = listBackups(backupDir);
  assert.equal(backups.length, 1, 'backup kept after the failure');
  assert.equal(versionOf(path.join(backupDir, backups[0])), 1);
  // Fixed release: the same DB migrates cleanly afterwards.
  const s = openStore({ file, backupDir, migrationsDir: writeMigrations(path.join(root, 'good'), FIXTURE), now: tick });
  assert.equal(s.version, 3);
  s.close();
});

test('a migration that tries to control the transaction is refused', () => {
  const { root, file } = setup(0);
  const dir = writeMigrations(path.join(root, 'txn'), [['0001_x.sql', 'CREATE TABLE a (x);\nCOMMIT;\n']]);
  assert.throws(() => openStore({ file, migrationsDir: dir }), (e) => e.code === 'MIGRATION_TXN');
});

// --- refusal --------------------------------------------------------------

test('refuses a DB newer than the app knows, without touching it', () => {
  const { root, file, backupDir } = setup(3);
  const sha = fileSha(file);
  const older = writeMigrations(path.join(root, 'old'), FIXTURE.slice(0, 2));
  assert.throws(
    () => openStore({ file, backupDir, migrationsDir: older }),
    (e) => e instanceof StoreError && e.code === 'DB_TOO_NEW' && /v3/.test(e.message)
  );
  assert.equal(fileSha(file), sha);
  assert.deepEqual(listBackups(backupDir).filter((n) => n.startsWith('veilwalker-v3')), []);
});

test('refuses a foreign DB (tables, no schema_version)', () => {
  const { file } = setup(0);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new DatabaseSync(file);
  db.exec('CREATE TABLE something_else (x INTEGER)');
  db.close();
  assert.throws(() => openStore({ file }), (e) => e.code === 'NOT_VW_DB');
});

// --- immutability ---------------------------------------------------------

test('an applied migration edited in place is refused', () => {
  const { root, file } = setup(2);
  const edited = FIXTURE.slice(0, 2).map(([n, s]) => [n, s]);
  edited[1][1] = 'ALTER TABLE people ADD COLUMN age TEXT;\n';
  const dir = writeMigrations(path.join(root, 'edited'), edited);
  assert.throws(() => openStore({ file, migrationsDir: dir }), (e) => e.code === 'MIGRATION_CHANGED');
});

test('loader refuses unpinned, mismatched, gapped and missing migrations', () => {
  const root = tmp();
  const d1 = writeMigrations(path.join(root, 'a'), FIXTURE.slice(0, 1));
  fs.writeFileSync(path.join(d1, '0002_extra.sql'), 'SELECT 1;\n');
  assert.throws(() => loadMigrations(d1), (e) => e.code === 'MIGRATION_UNPINNED');

  const d2 = writeMigrations(path.join(root, 'b'), FIXTURE.slice(0, 1));
  fs.appendFileSync(path.join(d2, FIXTURE[0][0]), '-- edit\n');
  assert.throws(() => loadMigrations(d2), (e) => e.code === 'MIGRATION_CHANGED');

  const d3 = writeMigrations(path.join(root, 'c'), [FIXTURE[0], ['0003_gap.sql', 'SELECT 1;\n']]);
  assert.throws(() => loadMigrations(d3), (e) => e.code === 'MIGRATION_ORDER');

  const d4 = writeMigrations(path.join(root, 'd'), FIXTURE.slice(0, 2));
  fs.unlinkSync(path.join(d4, FIXTURE[1][0]));
  assert.throws(() => loadMigrations(d4), (e) => e.code === 'MIGRATION_MISSING');

  const d5 = writeMigrations(path.join(root, 'e'), [['0001_Bad-Name.sql', 'SELECT 1;\n']]);
  assert.throws(() => loadMigrations(d5), (e) => e.code === 'MIGRATION_NAME');
});

test('CRLF checkout of a migration hashes the same as LF', () => {
  assert.equal(sha256Text('a;\r\nb;\r\n'), sha256Text('a;\nb;\n'));
});
