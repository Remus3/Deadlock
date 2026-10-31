-- VW-APP-DB v1: app key/value settings. Later epics add their own tables
-- in new migration files; this file is immutable once released.
CREATE TABLE kv (
  key TEXT PRIMARY KEY NOT NULL,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
) WITHOUT ROWID;
