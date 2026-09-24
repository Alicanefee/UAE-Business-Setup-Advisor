-- Canonical source records. Every claim the system makes points to exactly
-- one row in one of these tables.

CREATE TABLE IF NOT EXISTS laws (
  id             TEXT PRIMARY KEY,
  biz_type       TEXT NOT NULL,          -- mainland | freezone | multinational
  emirate        TEXT,                   -- NULL = applies to all emirates
  activity       TEXT,                   -- NULL or 'general' = applies to all activities
  title          TEXT NOT NULL,
  body           TEXT NOT NULL,
  effective_from TEXT NOT NULL,
  effective_to   TEXT,                   -- NULL = currently in force
  superseded_by  TEXT
);

CREATE TABLE IF NOT EXISTS documents (
  id            TEXT PRIMARY KEY,
  law_id        TEXT NOT NULL REFERENCES laws(id),
  name          TEXT NOT NULL,
  issuer        TEXT,
  how_to_obtain TEXT,
  is_mandatory  INTEGER NOT NULL DEFAULT 1,
  notes         TEXT
);

CREATE TABLE IF NOT EXISTS penalties (
  id             TEXT PRIMARY KEY,
  law_id         TEXT NOT NULL REFERENCES laws(id),
  condition      TEXT NOT NULL,
  amount_aed     TEXT,
  note           TEXT,
  effective_from TEXT NOT NULL,
  effective_to   TEXT
);

CREATE TABLE IF NOT EXISTS alternatives (
  id              TEXT PRIMARY KEY,
  missing_doc     TEXT NOT NULL,
  alternative_doc TEXT NOT NULL,
  conditions      TEXT,
  effective_from  TEXT NOT NULL,
  effective_to    TEXT
);

CREATE TABLE IF NOT EXISTS institutions (
  id       TEXT PRIMARY KEY,
  name     TEXT NOT NULL,
  emirate  TEXT,                         -- NULL = federal
  biz_type TEXT,                         -- NULL = all structures
  address  TEXT,
  website  TEXT,
  phone    TEXT,
  email    TEXT,
  notes    TEXT
);

-- Rule sets from config/rules/*.yaml, stored and hashed like any other source.
CREATE TABLE IF NOT EXISTS rules (
  id      TEXT PRIMARY KEY,
  version INTEGER NOT NULL,
  body    TEXT NOT NULL
);
