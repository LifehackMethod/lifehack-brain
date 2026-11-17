-- 015_thing_keys.sql: Phase 2 step 2.3 (2 of 5). user_version 14 -> 15. Vision 3.7.3, delta 7.28.
-- `thing_keys` is the append-only record of every key ever minted (key, kind, made_from, created_at). A rebuild reads it and
-- reuses the same key, so diary pointers and confirmations never dangle. It lives in the record layer: no foreign key to
-- kg_things (a rebuild may delete things; the key stays). One row is written for every existing thing, and a trigger writes one
-- for every future thing so no key can exist without its row. Code that knows better (the minting rule, a later step) writes
-- its own row first with a precise made_from; the trigger's INSERT OR IGNORE then leaves it alone.
-- made_from, in order: the legacy table row it was copied from; else the first answer that names the key; else the key
-- format itself (address, domain, item keys are derived from their own content); else the code writer.

CREATE TABLE thing_keys(
  key TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  made_from TEXT NOT NULL,
  created_at TEXT NOT NULL) STRICT;

INSERT INTO thing_keys(key, kind, made_from, created_at)
  SELECT t.key, t.kind,
         COALESCE('legacy:' || t.legacy_ref,
                  (SELECT 'answer:' || MIN(a.id) FROM kg_answers a WHERE a.subject_key = t.key),
                  CASE WHEN t.kind IN ('address', 'domain', 'item') THEN 'key-format:' || t.kind END,
                  'writer:' || t.created_by),
         t.created_at
    FROM kg_things t ORDER BY t.id;

CREATE TRIGGER thing_keys_no_update BEFORE UPDATE ON thing_keys
BEGIN SELECT RAISE(ABORT, 'thing_keys is append-only: UPDATE refused'); END;
CREATE TRIGGER thing_keys_no_delete BEFORE DELETE ON thing_keys
BEGIN SELECT RAISE(ABORT, 'thing_keys is append-only: DELETE refused'); END;

-- every new thing gets its row (the row is the permanent claim on the key; a later rebuild reuses it)
CREATE TRIGGER kg_things_record_key AFTER INSERT ON kg_things
BEGIN
  INSERT OR IGNORE INTO thing_keys(key, kind, made_from, created_at)
  VALUES (NEW.key, NEW.kind,
          COALESCE('legacy:' || NEW.legacy_ref,
                   CASE WHEN NEW.kind IN ('address', 'domain', 'item') THEN 'key-format:' || NEW.kind END,
                   'writer:' || NEW.created_by),
          NEW.created_at);
END;
