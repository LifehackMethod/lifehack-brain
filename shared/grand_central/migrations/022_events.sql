-- 022_events.sql: Phase 3 step 3.2. user_version 21 -> 22. Vision 3.7.3 (event kind, key event:<source>:<source_id>) and 3.7.4 rules 1, 5, 7.
-- Adds the `event` thing kind, the two time columns the Vision gives every thing (starts_at, ends_at; a plain copy of the CURRENT
-- time, the history lives in the facts below), and the four facts code writes about an event from the calendar mirror.
-- `involves` (event -> person or address) and `part_of` (event -> project) already exist as link kinds (005). Nothing here depends on 021.
-- The events themselves are built by code (store_events.build_events), not by this file: this only makes them allowed words.
ALTER TABLE kg_things ADD COLUMN starts_at TEXT;
ALTER TABLE kg_things ADD COLUMN ends_at TEXT;
INSERT OR IGNORE INTO kg_vocab(list, value, note) VALUES('thing_kind', 'event', 'one per calendar entry; key event:<source>:<source_id>');
INSERT OR IGNORE INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
  ('starts_at', NULL, 'event', 'when the calendar entry starts, as the mirror holds it (date or date-time); a move is a new fact, the old one kept'),
  ('ends_at', NULL, 'event', 'when the calendar entry ends, as the mirror holds it'),
  ('place', NULL, 'event', 'the calendar entry''s location text, only when the mirror''s scan cleared it'),
  ('event_status', NULL, 'event', 'the calendar''s own word: confirmed | tentative | cancelled');
