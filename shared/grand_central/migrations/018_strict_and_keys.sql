-- 018_strict_and_keys.sql: Phase 2 step 2.3 (4 of 5, numbered 018 because another helper took 017) with step 2.7 (the one date rule). user_version 17 -> 18. Vision 3.7.1, 3.7.3, delta 7.05, 7.26, 7.08.
-- Every model table is rebuilt (a table cannot become STRICT or gain a foreign key in place): kg_things, kg_links, kg_facts, kg_answers,
-- kg_vocab, kg_fact_keys, kg_scores and queue. Column order and every existing row are kept; ids are copied, so every pointer still points.
-- STRICT: a field holds only its declared type.
-- Declared foreign keys (enforced: db.connect turns foreign_keys ON):
--   kg_links.from_id, to_id -> kg_things; kg_links.answer_id -> kg_answers; kg_links.replaced_by -> kg_links
--   kg_facts.thing_id -> kg_things; kg_facts.fact_key -> kg_fact_keys; kg_facts.answer_id -> kg_answers; kg_facts.replaced_by -> kg_facts
--   kg_answers.queue_id -> queue
-- Not declared, on purpose: kg_answers.subject_key (an answer may name a thing that a rebuild has not made yet; thing_keys holds the key),
-- kg_answers.legacy_answer_log_id (points at a legacy table that step 2.6 freezes), kg_things.merged_into (the column does not exist yet).
-- THE ONE DATE RULE (step 2.7): a calendar date is ISO text, YYYY-MM-DD, or a partial YYYY-MM or YYYY. It is a CHECK on kg_facts.true_from,
-- true_until, kg_links.true_from, true_until, kg_answers.said_on, true_until. Existing values are converted on copy: a legal shape is kept;
-- an ISO date-time keeps its own date part; anything else is copied as it is and so FAILS the CHECK, which aborts and rolls back this whole
-- migration (refused, never guessed). On the 2026-11-16 data every value is already a legal full date, so nothing changes.
-- Timestamps (created_at, recorded_at, computed_at, queue.answered_at) are instants, not calendar dates: left as the writers wrote them.
-- The triggers, indexes and the two 013 approval triggers on the rebuilt tables are recreated exactly as they were.

PRAGMA legacy_alter_table = ON;

CREATE TABLE queue_new(
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  subject_ref TEXT NOT NULL,           -- e.g. 'person:12', 'rule:7', 'item:301'
  question TEXT NOT NULL,
  proposed_answer TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','answered','dismissed')),
  created_at TEXT NOT NULL, answered_at TEXT, answer TEXT) STRICT;
INSERT INTO queue_new(id, kind, subject_ref, question, proposed_answer, status, created_at, answered_at, answer)
  SELECT id, kind, subject_ref, question, proposed_answer, status, created_at, answered_at, answer FROM queue;
DROP TABLE queue;
ALTER TABLE queue_new RENAME TO queue;
CREATE INDEX queue_status ON queue(status);

CREATE TABLE kg_vocab_new(
  list TEXT NOT NULL,                  -- thing_kind | link_kind | who | certainty | source_kind | v:<value list name>
  value TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(list, value)) STRICT;
INSERT INTO kg_vocab_new(list, value, note) SELECT list, value, note FROM kg_vocab;
DROP TABLE kg_vocab;
ALTER TABLE kg_vocab_new RENAME TO kg_vocab;

CREATE TABLE kg_fact_keys_new(
  key TEXT PRIMARY KEY,
  value_list TEXT,                     -- e.g. 'v:inbox'; NULL = free text
  subject_kinds TEXT NOT NULL,         -- comma list of thing kinds it may describe, or '*'
  note TEXT) STRICT;
INSERT INTO kg_fact_keys_new(key, value_list, subject_kinds, note) SELECT key, value_list, subject_kinds, note FROM kg_fact_keys;
DROP TABLE kg_fact_keys;
ALTER TABLE kg_fact_keys_new RENAME TO kg_fact_keys;

CREATE TABLE kg_scores_new(
  id INTEGER PRIMARY KEY,
  subject_ref TEXT NOT NULL,           -- 'item:301' | 'thing:12'
  signal TEXT NOT NULL, signal_version INTEGER NOT NULL,
  value REAL, reason TEXT,
  computed_at TEXT NOT NULL,
  UNIQUE(subject_ref, signal)) STRICT;
INSERT INTO kg_scores_new(id, subject_ref, signal, signal_version, value, reason, computed_at)
  SELECT id, subject_ref, signal, signal_version, value, reason, computed_at FROM kg_scores;
DROP TABLE kg_scores;
ALTER TABLE kg_scores_new RENAME TO kg_scores;

CREATE TABLE kg_things_new(
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,                  -- checked against kg_vocab(thing_kind)
  key TEXT NOT NULL UNIQUE,            -- '<kind>:<normalized name>'; every key has a row in thing_keys
  name TEXT NOT NULL,                  -- display
  legacy_ref TEXT,                     -- 'people:3', 'circles:2', 'rules:17' ... for things copied from today's tables
  created_by TEXT NOT NULL,            -- who: owner | code | ai_research | ai_guess
  created_at TEXT NOT NULL) STRICT;
INSERT INTO kg_things_new(id, kind, key, name, legacy_ref, created_by, created_at)
  SELECT id, kind, key, name, legacy_ref, created_by, created_at FROM kg_things;
DROP TABLE kg_things;
ALTER TABLE kg_things_new RENAME TO kg_things;
CREATE INDEX kg_things_kind ON kg_things(kind);

CREATE TABLE kg_answers_new(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question TEXT NOT NULL,              -- the question as asked (or the topic, for answers caught up from older notes)
  words TEXT NOT NULL,                 -- the owner's exact words
  asked_by TEXT NOT NULL,              -- window or skill name
  said_on TEXT NOT NULL,               -- the day it was said: YYYY-MM-DD
  subject_key TEXT,                    -- kg_things.key the decision is about (NULL = no fact, e.g. a plain yes to a proposal)
  subject_kind TEXT, subject_name TEXT,-- so the thing can be re-created on rebuild
  fact_key TEXT,                       -- a kg_fact_keys key, or 'link:<link_kind>' (value is then the target thing key)
  value TEXT,
  true_until TEXT,
  queue_id INTEGER REFERENCES queue(id),
  legacy_answer_log_id INTEGER,
  recorded_at TEXT NOT NULL, words_kind TEXT NOT NULL DEFAULT 'verbatim', condition TEXT,
  CHECK((fact_key IS NULL) = (value IS NULL)),
  CHECK(fact_key IS NULL OR subject_key IS NOT NULL),
  CHECK(said_on IS NULL OR (said_on GLOB '[0-9][0-9][0-9][0-9]' AND date(said_on || '-01-01') IS said_on || '-01-01') OR (said_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(said_on || '-01') IS said_on || '-01') OR (said_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(said_on) IS said_on)),
  CHECK(true_until IS NULL OR (true_until GLOB '[0-9][0-9][0-9][0-9]' AND date(true_until || '-01-01') IS true_until || '-01-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_until || '-01') IS true_until || '-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_until) IS true_until))) STRICT;
INSERT INTO kg_answers_new(id, question, words, asked_by, said_on, subject_key, subject_kind, subject_name, fact_key, value, true_until,
                           queue_id, legacy_answer_log_id, recorded_at, words_kind, condition)
  SELECT id, question, words, asked_by, CASE WHEN said_on IS NULL THEN NULL WHEN ((said_on GLOB '[0-9][0-9][0-9][0-9]' AND date(said_on || '-01-01') IS said_on || '-01-01') OR (said_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(said_on || '-01') IS said_on || '-01') OR (said_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(said_on) IS said_on)) THEN said_on WHEN length(said_on) > 10 AND substr(said_on, 11, 1) IN ('T', ' ') AND substr(said_on, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(substr(said_on, 1, 10)) IS substr(said_on, 1, 10) THEN substr(said_on, 1, 10) ELSE said_on END, subject_key, subject_kind, subject_name, fact_key, value, CASE WHEN true_until IS NULL THEN NULL WHEN ((true_until GLOB '[0-9][0-9][0-9][0-9]' AND date(true_until || '-01-01') IS true_until || '-01-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_until || '-01') IS true_until || '-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_until) IS true_until)) THEN true_until WHEN length(true_until) > 10 AND substr(true_until, 11, 1) IN ('T', ' ') AND substr(true_until, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(substr(true_until, 1, 10)) IS substr(true_until, 1, 10) THEN substr(true_until, 1, 10) ELSE true_until END,
         queue_id, legacy_answer_log_id, recorded_at, words_kind, condition FROM kg_answers;
DROP TABLE kg_answers;
ALTER TABLE kg_answers_new RENAME TO kg_answers;
CREATE TRIGGER kg_answers_no_update BEFORE UPDATE ON kg_answers
BEGIN SELECT RAISE(ABORT, 'kg_answers is append-only: UPDATE refused'); END;
CREATE TRIGGER kg_answers_no_delete BEFORE DELETE ON kg_answers
BEGIN SELECT RAISE(ABORT, 'kg_answers is append-only: DELETE refused'); END;

CREATE TABLE kg_links_new(
  id INTEGER PRIMARY KEY,
  from_id INTEGER NOT NULL REFERENCES kg_things(id),
  kind TEXT NOT NULL,                  -- kg_vocab(link_kind)
  to_id INTEGER NOT NULL REFERENCES kg_things(id),
  role TEXT,                           -- optional free word on the link (the meaning, in their own words)
  who TEXT NOT NULL, certainty TEXT NOT NULL,
  source_kind TEXT NOT NULL, source_ref TEXT,
  answer_id INTEGER REFERENCES kg_answers(id),   -- kg_answers.id when the owner said it
  true_from TEXT, true_until TEXT,
  replaced_by INTEGER REFERENCES kg_links(id),   -- kg_links.id that superseded this one (NULL = current)
  created_at TEXT NOT NULL,
  CHECK(true_from IS NULL OR (true_from GLOB '[0-9][0-9][0-9][0-9]' AND date(true_from || '-01-01') IS true_from || '-01-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_from || '-01') IS true_from || '-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_from) IS true_from)),
  CHECK(true_until IS NULL OR (true_until GLOB '[0-9][0-9][0-9][0-9]' AND date(true_until || '-01-01') IS true_until || '-01-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_until || '-01') IS true_until || '-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_until) IS true_until))) STRICT;
INSERT INTO kg_links_new(id, from_id, kind, to_id, role, who, certainty, source_kind, source_ref, answer_id, true_from, true_until, replaced_by, created_at)
  SELECT id, from_id, kind, to_id, role, who, certainty, source_kind, source_ref, answer_id, CASE WHEN true_from IS NULL THEN NULL WHEN ((true_from GLOB '[0-9][0-9][0-9][0-9]' AND date(true_from || '-01-01') IS true_from || '-01-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_from || '-01') IS true_from || '-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_from) IS true_from)) THEN true_from WHEN length(true_from) > 10 AND substr(true_from, 11, 1) IN ('T', ' ') AND substr(true_from, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(substr(true_from, 1, 10)) IS substr(true_from, 1, 10) THEN substr(true_from, 1, 10) ELSE true_from END, CASE WHEN true_until IS NULL THEN NULL WHEN ((true_until GLOB '[0-9][0-9][0-9][0-9]' AND date(true_until || '-01-01') IS true_until || '-01-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_until || '-01') IS true_until || '-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_until) IS true_until)) THEN true_until WHEN length(true_until) > 10 AND substr(true_until, 11, 1) IN ('T', ' ') AND substr(true_until, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(substr(true_until, 1, 10)) IS substr(true_until, 1, 10) THEN substr(true_until, 1, 10) ELSE true_until END, NULL, created_at
    FROM kg_links;
CREATE TEMP TABLE kg_links_pointers AS SELECT id, replaced_by FROM kg_links WHERE replaced_by IS NOT NULL;
DROP TABLE kg_links;
ALTER TABLE kg_links_new RENAME TO kg_links;
-- a self-pointing foreign key cannot survive a drop of its own table mid-copy, so the supersession pointers go back after the rename
UPDATE kg_links SET replaced_by = (SELECT p.replaced_by FROM kg_links_pointers p WHERE p.id = kg_links.id) WHERE id IN (SELECT id FROM kg_links_pointers);
DROP TABLE kg_links_pointers;
CREATE INDEX kg_links_from ON kg_links(from_id, kind);
CREATE INDEX kg_links_to ON kg_links(to_id, kind);

CREATE TABLE kg_facts_new(
  id INTEGER PRIMARY KEY,
  thing_id INTEGER NOT NULL REFERENCES kg_things(id),
  fact_key TEXT NOT NULL REFERENCES kg_fact_keys(key),
  value TEXT NOT NULL,                 -- 'undecided' is a legal value in every list
  who TEXT NOT NULL,                   -- owner | code | ai_research | ai_guess
  certainty TEXT NOT NULL,             -- sure | likely | guess
  source_kind TEXT NOT NULL,           -- answer | item | file | legacy | code
  source_ref TEXT,                     -- answer id / item id / file path#section / 'rules:17'
  answer_id INTEGER REFERENCES kg_answers(id),
  true_from TEXT, true_until TEXT,
  replaced_by INTEGER REFERENCES kg_facts(id),   -- kg_facts.id that superseded this one (NULL = current)
  created_at TEXT NOT NULL, condition TEXT,
  CHECK(who <> 'owner' OR answer_id IS NOT NULL),
  CHECK(true_from IS NULL OR (true_from GLOB '[0-9][0-9][0-9][0-9]' AND date(true_from || '-01-01') IS true_from || '-01-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_from || '-01') IS true_from || '-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_from) IS true_from)),
  CHECK(true_until IS NULL OR (true_until GLOB '[0-9][0-9][0-9][0-9]' AND date(true_until || '-01-01') IS true_until || '-01-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_until || '-01') IS true_until || '-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_until) IS true_until))) STRICT;
INSERT INTO kg_facts_new(id, thing_id, fact_key, value, who, certainty, source_kind, source_ref, answer_id, true_from, true_until, replaced_by, created_at, condition)
  SELECT id, thing_id, fact_key, value, who, certainty, source_kind, source_ref, answer_id, CASE WHEN true_from IS NULL THEN NULL WHEN ((true_from GLOB '[0-9][0-9][0-9][0-9]' AND date(true_from || '-01-01') IS true_from || '-01-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_from || '-01') IS true_from || '-01') OR (true_from GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_from) IS true_from)) THEN true_from WHEN length(true_from) > 10 AND substr(true_from, 11, 1) IN ('T', ' ') AND substr(true_from, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(substr(true_from, 1, 10)) IS substr(true_from, 1, 10) THEN substr(true_from, 1, 10) ELSE true_from END, CASE WHEN true_until IS NULL THEN NULL WHEN ((true_until GLOB '[0-9][0-9][0-9][0-9]' AND date(true_until || '-01-01') IS true_until || '-01-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' AND date(true_until || '-01') IS true_until || '-01') OR (true_until GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(true_until) IS true_until)) THEN true_until WHEN length(true_until) > 10 AND substr(true_until, 11, 1) IN ('T', ' ') AND substr(true_until, 1, 10) GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(substr(true_until, 1, 10)) IS substr(true_until, 1, 10) THEN substr(true_until, 1, 10) ELSE true_until END, NULL, created_at, condition
    FROM kg_facts;
CREATE TEMP TABLE kg_facts_pointers AS SELECT id, replaced_by FROM kg_facts WHERE replaced_by IS NOT NULL;
DROP TABLE kg_facts;
ALTER TABLE kg_facts_new RENAME TO kg_facts;
-- a self-pointing foreign key cannot survive a drop of its own table mid-copy, so the supersession pointers go back after the rename
UPDATE kg_facts SET replaced_by = (SELECT p.replaced_by FROM kg_facts_pointers p WHERE p.id = kg_facts.id) WHERE id IN (SELECT id FROM kg_facts_pointers);
DROP TABLE kg_facts_pointers;
CREATE INDEX kg_facts_thing ON kg_facts(thing_id, fact_key);
CREATE INDEX kg_facts_answer ON kg_facts(answer_id);

-- triggers of the rebuilt tables, recreated exactly as 014 / 015 / 016 made them
CREATE TRIGGER kg_facts_no_self_approval BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'approved_digest' OR (NEW.fact_key = 'rule_status' AND NEW.value = 'approved' AND NEW.source_kind <> 'legacy')
BEGIN
  SELECT CASE
    WHEN NEW.who <> 'owner' THEN RAISE(ABORT, 'an approval can only be the owner''s word: who must be owner')
    WHEN NEW.answer_id IS NULL OR NOT EXISTS (SELECT 1 FROM kg_answers a WHERE a.id = NEW.answer_id
                                               AND a.question LIKE 'approve staged filters sha256:%'
                                               AND (a.asked_by LIKE 'owner-session%' OR a.asked_by LIKE 'gc approve%'))
      THEN RAISE(ABORT, 'an approval must cite the owner''s recorded answer to "approve staged filters sha256:..." asked by a human-facing surface (owner-session / gc approve)')
    WHEN NEW.fact_key = 'approved_digest' AND NOT EXISTS (SELECT 1 FROM kg_answers a WHERE a.id = NEW.answer_id
                                               AND a.question = 'approve staged filters sha256:' || NEW.value)
      THEN RAISE(ABORT, 'the approval answer is about a different staged pair than the digest stamped')
  END;
END;

CREATE TRIGGER kg_facts_no_edit_into_approval BEFORE UPDATE OF fact_key, value, who, source_kind, answer_id ON kg_facts
WHEN (NEW.fact_key = 'approved_digest' OR (NEW.fact_key = 'rule_status' AND NEW.value = 'approved' AND NEW.source_kind <> 'legacy'))
 AND NOT (OLD.fact_key = NEW.fact_key AND OLD.value = NEW.value AND OLD.who = NEW.who
          AND OLD.source_kind = NEW.source_kind AND OLD.answer_id IS NEW.answer_id)
BEGIN SELECT RAISE(ABORT, 'an approval cannot be created or changed by editing a fact'); END;

CREATE TRIGGER kg_things_record_key AFTER INSERT ON kg_things
BEGIN
  INSERT OR IGNORE INTO thing_keys(key, kind, made_from, created_at)
  VALUES (NEW.key, NEW.kind,
          COALESCE('legacy:' || NEW.legacy_ref,
                   CASE WHEN NEW.kind IN ('address', 'domain', 'item') THEN 'key-format:' || NEW.kind END,
                   'writer:' || NEW.created_by),
          NEW.created_at);
END;

CREATE TRIGGER kg_things_person_me_fixed BEFORE UPDATE OF key, kind ON kg_things
WHEN OLD.key = 'person:me'
BEGIN SELECT RAISE(ABORT, 'person:me is the fixed row: its key and kind cannot change'); END;

CREATE TRIGGER kg_things_person_me_kept BEFORE DELETE ON kg_things
WHEN OLD.key = 'person:me'
BEGIN SELECT RAISE(ABORT, 'person:me is the fixed row: it cannot be deleted'); END;

PRAGMA legacy_alter_table = OFF;
