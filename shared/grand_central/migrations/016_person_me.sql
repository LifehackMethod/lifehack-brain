-- 016_person_me.sql: Phase 2 step 2.3 (3 of 5). user_version 15 -> 16. Vision 3.7.3, delta 7.36.
-- The person is one `person` thing with the fixed key `person:me`; every "in relation to the person" lookup starts here.
-- The key is recorded in thing_keys first, with the precise reason, so the 015 trigger leaves it alone.
-- Nothing links to it yet: the person's own mail accounts (delta 7.37) and the facts about the person are separate, later steps.
-- Guard: the row cannot be removed, re-keyed or re-kinded.

INSERT INTO thing_keys(key, kind, made_from, created_at)
  VALUES ('person:me', 'person', 'fixed: the person themself (Vision 3.7.3)', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

INSERT INTO kg_things(kind, key, name, created_by, created_at)
  SELECT 'person', 'person:me', 'me', 'code', created_at FROM thing_keys WHERE key = 'person:me';

CREATE TRIGGER kg_things_person_me_fixed BEFORE UPDATE OF key, kind ON kg_things
WHEN OLD.key = 'person:me'
BEGIN SELECT RAISE(ABORT, 'person:me is the fixed row: its key and kind cannot change'); END;

CREATE TRIGGER kg_things_person_me_kept BEFORE DELETE ON kg_things
WHEN OLD.key = 'person:me'
BEGIN SELECT RAISE(ABORT, 'person:me is the fixed row: it cannot be deleted'); END;
