-- 002_items.sql: STEP 4. One common shape (items) for every source, thin per-source detail that LINKS to the
-- raw rows (never copies them), an append-only history (item_events), and pointers to bulky-text files.
-- The text of an email/event/task never enters these tables. Never edit once applied.

CREATE TABLE items(
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,                -- gmail | calendar | tasks | (later sources)
  source_id TEXT NOT NULL,             -- the source's own id (message id, event id, task id)
  kind TEXT NOT NULL,                  -- email | event | task | (later kinds)
  title TEXT,                          -- subject / summary / task title
  person_address TEXT,                 -- from address / organizer address, lowercased; NULL if none
  occurred_at TEXT,                    -- ISO-8601 UTC or source-local with offset: when it happened / starts
  due_at TEXT,                         -- when it is due, if it has a due date
  status TEXT,                         -- source's own state, plain words
  created_at TEXT NOT NULL,            -- when the rig first made this row (UTC)
  UNIQUE(source, source_id));

CREATE INDEX items_occurred ON items(occurred_at);
CREATE INDEX items_kind ON items(kind);

CREATE TABLE item_email(
  item_id INTEGER PRIMARY KEY REFERENCES items(id),
  message_id TEXT NOT NULL UNIQUE REFERENCES messages(id),
  thread_id TEXT);

CREATE TABLE item_calendar(
  item_id INTEGER PRIMARY KEY REFERENCES items(id),
  calendar_event_id TEXT NOT NULL UNIQUE REFERENCES calendar_events(id),
  all_day INTEGER);

CREATE TABLE item_task(
  item_id INTEGER PRIMARY KEY REFERENCES items(id),
  task_id TEXT NOT NULL UNIQUE REFERENCES tasks(id),
  list_id TEXT);

CREATE TABLE item_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id INTEGER NOT NULL REFERENCES items(id),
  at TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(length(kind) > 0),   -- arrived | labeled | archived | replied | returned | ...
  detail TEXT,                                  -- short note, never body text
  actor TEXT);

CREATE INDEX item_events_item ON item_events(item_id, at);

CREATE TRIGGER item_events_no_update BEFORE UPDATE ON item_events
BEGIN SELECT RAISE(ABORT, 'item_events is append-only: UPDATE refused'); END;

CREATE TRIGGER item_events_no_delete BEFORE DELETE ON item_events
BEGIN SELECT RAISE(ABORT, 'item_events is append-only: DELETE refused'); END;

-- Pointers to bulky-text files in <data root>/handoff/. No text column, by design.
CREATE TABLE text_pointers(
  id INTEGER PRIMARY KEY,
  item_id INTEGER REFERENCES items(id),
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK(length(sha256) = 64),
  bytes INTEGER NOT NULL CHECK(bytes >= 0),
  added_at TEXT NOT NULL,
  UNIQUE(path, sha256));
