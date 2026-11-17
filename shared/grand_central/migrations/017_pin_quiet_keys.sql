-- 017_pin_quiet_keys.sql: Phase 2 step 2.4 (reader 4). Numbered after 016 (another helper's, step 2.3) because 014-016 were taken
-- when this step started. The old `overrides` table (pins and quiet-until, 0 rows) gets a home in the one model: two fact keys.
--   pin          value = the reason in short; the fact is his word (who = owner, with the answer that carries his words)
--   quiet_until  value = the date YYYY-MM-DD it stays quiet until
-- Both may sit on an item, project, person or rule. A fact value of 'off' means it was ended (the old row's status 'retired'):
-- never deleted, so a rebuild from the answers replays it. The review date is the existing `review_by` fact on the same thing.
-- No data to move: the old table had 0 rows.
INSERT INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
  ('pin', NULL, 'item,project,person,rule', 'keep this at the top of the urgent list: the reason in short (his word); ''off'' = ended'),
  ('quiet_until', NULL, 'item,project,person,rule', 'hide this until the date YYYY-MM-DD (his word); ''off'' = ended');
