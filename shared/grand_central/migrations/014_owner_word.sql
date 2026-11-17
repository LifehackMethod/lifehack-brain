-- 014_owner_word.sql: Phase 2 step 2.3 (1 of 5). user_version 13 -> 14.
-- The owner's first name leaves the database. The word is `owner` (Vision 3.7.3, delta 7.48).
-- Four places held the name: the `who` vocabulary, the data (kg_facts.who, kg_things.created_by), the table CHECK on
-- kg_facts, and the two approval triggers plus the views that test `who`; the asker rule in code (ASKER_RE) and the
-- trigger now say `owner-session` instead of the first name's `-session`.
-- kg_answers.asked_by is NOT rewritten: it is append-only (no update, by design) and no approval answer exists yet.
-- Only the `who` word changes; ai_guess / ai_research stay until step 2.5. kg_facts is rebuilt (a CHECK cannot be edited in place).

DROP TRIGGER kg_facts_no_self_approval;
DROP TRIGGER kg_facts_no_edit_into_approval;

-- (the data rename from an owner's first name to 'owner' lives in that owner's setup migrations)

PRAGMA legacy_alter_table = ON;
PRAGMA defer_foreign_keys = ON;

CREATE TABLE kg_facts_new(
  id INTEGER PRIMARY KEY,
  thing_id INTEGER NOT NULL,
  fact_key TEXT NOT NULL,              -- kg_fact_keys.key
  value TEXT NOT NULL,                 -- 'undecided' is a legal value in every list
  who TEXT NOT NULL,                   -- owner | code | ai_research | ai_guess
  certainty TEXT NOT NULL,             -- sure | likely | guess
  source_kind TEXT NOT NULL,           -- answer | item | file | legacy | code
  source_ref TEXT,                     -- answer id / item id / file path#section / 'rules:17'
  answer_id INTEGER,
  true_from TEXT, true_until TEXT,
  replaced_by INTEGER,                 -- kg_facts.id that superseded this one (NULL = current)
  created_at TEXT NOT NULL, condition TEXT,
  CHECK(who <> 'owner' OR answer_id IS NOT NULL));
INSERT INTO kg_facts_new(id, thing_id, fact_key, value, who, certainty, source_kind, source_ref, answer_id,
                         true_from, true_until, replaced_by, created_at, condition)
  SELECT id, thing_id, fact_key, value, who, certainty, source_kind, source_ref, answer_id,
         true_from, true_until, replaced_by, created_at, condition FROM kg_facts;
DROP TABLE kg_facts;
ALTER TABLE kg_facts_new RENAME TO kg_facts;
CREATE INDEX kg_facts_thing ON kg_facts(thing_id, fact_key);
CREATE INDEX kg_facts_answer ON kg_facts(answer_id);

PRAGMA legacy_alter_table = OFF;

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

-- the two views that tested who = the first name
DROP VIEW v_confirmed_filter_facts;
CREATE VIEW v_confirmed_filter_facts AS
  SELECT f.id, f.thing_id, f.fact_key, f.value, f.condition, f.answer_id, f.source_ref, f.source_kind, f.who,
         t.kind AS tkind, t.key AS tkey
    FROM kg_facts f JOIN kg_things t ON t.id = f.thing_id
   WHERE f.replaced_by IS NULL AND f.fact_key IN ('label', 'destination', 'inbox') AND f.value <> 'undecided'
     AND t.kind IN ('address', 'domain', 'company', 'person', 'topic', 'label', 'rule')
     AND ((f.who = 'owner' AND f.answer_id IS NOT NULL AND EXISTS (
              SELECT 1 FROM kg_answers a WHERE a.id = f.answer_id AND a.subject_key = t.key AND a.fact_key = f.fact_key
                 AND a.value = f.value AND a.condition IS f.condition))
          OR (f.who = 'code' AND f.source_kind = 'legacy' AND f.source_ref LIKE 'rules:%' AND EXISTS (
              SELECT 1 FROM kg_things r
                JOIN kg_current_links l ON l.from_id = r.id AND l.kind = 'applies_to' AND l.to_id = f.thing_id
                JOIN kg_facts rs ON rs.thing_id = r.id AND rs.fact_key = 'rule_status' AND rs.source_kind = 'legacy'
                                AND rs.source_ref = f.source_ref
               WHERE r.kind = 'rule' AND r.legacy_ref = f.source_ref)));

DROP VIEW v_approvals;
CREATE VIEW v_approvals AS
  SELECT f.id AS fact_id, f.value AS digest, f.answer_id, a.said_on, a.words, a.asked_by, a.words_kind
    FROM kg_facts f JOIN kg_answers a ON a.id = f.answer_id
   WHERE f.fact_key = 'approved_digest' AND f.replaced_by IS NULL AND f.who = 'owner'
     AND a.question = 'approve staged filters sha256:' || f.value;
