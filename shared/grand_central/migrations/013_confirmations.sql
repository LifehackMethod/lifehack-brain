-- 013_confirmations.sql: plan B2 step 6 (only his confirmations go back in). user_version 12 -> 13.
-- The N3 nibble's four-link path (answer -> fact -> stored rule copy -> filter) becomes THREE links:
--     his answer (kg_answers)  ->  his dated fact (kg_facts, who='owner', citing the answer)  ->  filter draft (v_filter_spec)
-- v_filter_spec is a view straight over his current, answer-backed facts: nothing is stored in between, so retracting a
-- fact (a later answer that retires it) makes its filter draft disappear on the next read, and nothing needs recompiling
-- by hand. A separate rule item (kg_things kind='rule') exists only for topics, exceptions and approvals.
-- Also here: (1) the approval gate cannot be self-stamped, (2) the three new fact keys, (3) the hand-owned filter list.

-- ---- words ----------------------------------------------------------------------------------------------------
INSERT INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('lean',NULL,'address,domain,company,person','his own tilt on a score: "floor:3.5" | "set:2" | "mute" (confirmed form of a suggested lean)'),
 ('approved_digest',NULL,'rule','sha256 of the staged filter pair he said yes to; only his word, only on an approval rule item'),
 ('hand_owned',NULL,'rule','a live Gmail filter the compiler cannot express: his, by hand, never touched by the compiler (value = why)');

-- ---- the approval gate: nothing but his word can stamp an approval -------------------------------------------
-- (the nibble's compile code wrote rule_status='approved' as who='code'; that is refused here, at the database)
-- Legacy rule_status rows (source_kind='legacy', copied from the old rules table) are history, not approvals of anything staged.
CREATE TRIGGER kg_facts_no_self_approval BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'approved_digest' OR (NEW.fact_key = 'rule_status' AND NEW.value = 'approved' AND NEW.source_kind <> 'legacy')
BEGIN
  SELECT CASE
    WHEN NEW.who <> 'owner' THEN RAISE(ABORT, 'an approval can only be his word: who must be owner')
    WHEN NEW.answer_id IS NULL OR NOT EXISTS (SELECT 1 FROM kg_answers a WHERE a.id = NEW.answer_id
                                               AND a.question LIKE 'approve staged filters sha256:%'
                                               AND (a.asked_by LIKE 'owner-session%' OR a.asked_by LIKE 'gc approve%'))
      THEN RAISE(ABORT, 'an approval must cite his recorded answer to "approve staged filters sha256:..." asked by a human-facing surface (owner-session / gc approve)')
    WHEN NEW.fact_key = 'approved_digest' AND NOT EXISTS (SELECT 1 FROM kg_answers a WHERE a.id = NEW.answer_id
                                               AND a.question = 'approve staged filters sha256:' || NEW.value)
      THEN RAISE(ABORT, 'the approval answer is about a different staged pair than the digest stamped')
  END;
END;

-- an existing fact cannot be edited INTO an approval, and an approval's who/value/answer cannot be edited
CREATE TRIGGER kg_facts_no_edit_into_approval BEFORE UPDATE OF fact_key, value, who, source_kind, answer_id ON kg_facts
WHEN (NEW.fact_key = 'approved_digest' OR (NEW.fact_key = 'rule_status' AND NEW.value = 'approved' AND NEW.source_kind <> 'legacy'))
 AND NOT (OLD.fact_key = NEW.fact_key AND OLD.value = NEW.value AND OLD.who = NEW.who
          AND OLD.source_kind = NEW.source_kind AND OLD.answer_id IS NEW.answer_id)
BEGIN SELECT RAISE(ABORT, 'an approval cannot be created or changed by editing a fact'); END;

-- ---- where each sender-ish thing points: the Gmail `from` tokens ----------------------------------------------
DROP VIEW IF EXISTS v_thing_senders;
CREATE VIEW v_thing_senders AS
  SELECT t.id AS thing_id, t.key AS thing_key, t.kind AS thing_kind,
         CASE t.kind WHEN 'address' THEN t.name WHEN 'domain' THEN '@' || t.name END AS sender
    FROM kg_things t WHERE t.kind IN ('address', 'domain')
  UNION ALL   -- company -> its domains (domain_of: domain -> company)
  SELECT c.id, c.key, 'company', '@' || d.name
    FROM kg_things c JOIN kg_current_links dl ON dl.to_id = c.id AND dl.kind = 'domain_of'
    JOIN kg_things d ON d.id = dl.from_id WHERE c.kind = 'company'
  UNION ALL   -- person -> their addresses (address_of: address -> person)
  SELECT p.id, p.key, 'person', a.name
    FROM kg_things p JOIN kg_current_links al ON al.to_id = p.id AND al.kind = 'address_of'
    JOIN kg_things a ON a.id = al.from_id WHERE p.kind = 'person';

-- owner = the thing that carries the action fact. A sender-ish thing is its own owner; a rule item (topic / exception)
-- is the owner of whatever it applies_to.
DROP VIEW IF EXISTS v_owner_senders;
CREATE VIEW v_owner_senders AS
  SELECT thing_id AS owner_id, thing_key AS target_key, thing_kind AS target_kind, sender FROM v_thing_senders
  UNION ALL
  SELECT l.from_id, s.thing_key, s.thing_kind, s.sender
    FROM kg_current_links l JOIN kg_things r ON r.id = l.from_id AND r.kind = 'rule'
    JOIN v_thing_senders s ON s.thing_id = l.to_id WHERE l.kind = 'applies_to';

-- owners (or the things a rule item points at) that have no sender tokens: a topic, a label, a company with no domain
DROP VIEW IF EXISTS v_owner_unresolved;
CREATE VIEW v_owner_unresolved AS
  SELECT t.id AS owner_id, t.key AS target_key FROM kg_things t
   WHERE t.kind <> 'rule' AND NOT EXISTS (SELECT 1 FROM v_thing_senders s WHERE s.thing_id = t.id)
  UNION ALL
  SELECT l.from_id, x.key FROM kg_current_links l JOIN kg_things r ON r.id = l.from_id AND r.kind = 'rule'
    JOIN kg_things x ON x.id = l.to_id
   WHERE l.kind = 'applies_to' AND NOT EXISTS (SELECT 1 FROM v_thing_senders s WHERE s.thing_id = l.to_id);

-- ---- links 2 -> 3: ONLY a confirmed fact can drive a filter draft --------------------------------------------
-- confirmed = current, his word (who='owner') AND the answer it cites exists and says the same thing (subject, key, value,
-- condition); or a carried-over legacy fact (the old rules table, copied by code, source_kind='legacy').
-- An AI guess, a research note, or a fact written directly with no matching answer is simply not in this view.
DROP VIEW IF EXISTS v_confirmed_filter_facts;
CREATE VIEW v_confirmed_filter_facts AS
  SELECT f.id, f.thing_id, f.fact_key, f.value, f.condition, f.answer_id, f.source_ref, f.source_kind, f.who,
         t.kind AS tkind, t.key AS tkey
    FROM kg_facts f JOIN kg_things t ON t.id = f.thing_id
   WHERE f.replaced_by IS NULL AND f.fact_key IN ('label', 'destination', 'inbox') AND f.value <> 'undecided'
     AND t.kind IN ('address', 'domain', 'company', 'person', 'topic', 'label', 'rule')
     AND ((f.who = 'owner' AND f.answer_id IS NOT NULL AND EXISTS (
              SELECT 1 FROM kg_answers a WHERE a.id = f.answer_id AND a.subject_key = t.key AND a.fact_key = f.fact_key
                 AND a.value = f.value AND a.condition IS f.condition))
          -- carried-over legacy: only with a witness, a kg rule row copied from the old table (legacy_ref = the same 'rules:N', carrying
          -- its legacy rule_status fact) that applies_to THIS thing. A fact merely labelled legacy does not count.
          OR (f.who = 'code' AND f.source_kind = 'legacy' AND f.source_ref LIKE 'rules:%' AND EXISTS (
              SELECT 1 FROM kg_things r
                JOIN kg_current_links l ON l.from_id = r.id AND l.kind = 'applies_to' AND l.to_id = f.thing_id
                JOIN kg_facts rs ON rs.thing_id = r.id AND rs.fact_key = 'rule_status' AND rs.source_kind = 'legacy'
                                AND rs.source_ref = f.source_ref
               WHERE r.kind = 'rule' AND r.legacy_ref = f.source_ref)));

-- one row per confirmed fact: the filter draft it compiles to, or why it cannot be expressed.
-- rule_id / rule_key = the OWNER (the thing the fact is about, or the rule item); rule_fact_id = HIS fact (link 2).
DROP VIEW IF EXISTS v_filter_spec;
CREATE VIEW v_filter_spec AS
  SELECT f.thing_id AS rule_id, f.tkey AS rule_key, f.id AS rule_fact_id, f.answer_id, f.source_ref, f.fact_key, f.value,
         f.condition,
         (SELECT group_concat(sender, ' OR ') FROM (SELECT DISTINCT sender FROM v_owner_senders s
                                                     WHERE s.owner_id = f.thing_id ORDER BY sender)) AS from_query,
         CASE WHEN f.condition IS NOT NULL AND f.condition <> '' THEN f.condition END AS subject_word,
         CASE
           WHEN f.fact_key = 'label' AND f.value LIKE 'not:%' THEN 'never_label'
           WHEN f.fact_key = 'label' THEN 'add_label'
           WHEN f.fact_key = 'inbox' AND f.value = 'skip' THEN 'skip_inbox'
           WHEN f.fact_key = 'inbox' AND f.value = 'stay' THEN 'stay'
           WHEN f.fact_key = 'destination' AND f.value = 'inbox' THEN 'stay'
           WHEN f.fact_key = 'destination' AND f.value = 'trash' THEN 'trash'
           WHEN f.fact_key = 'destination' AND f.value = 'promos' THEN 'promos'
           WHEN f.fact_key = 'destination' AND f.value = 'archive' THEN 'archive'
           ELSE 'unknown'
         END AS action,
         (SELECT group_concat(target_key, ' | ') FROM v_owner_unresolved u WHERE u.owner_id = f.thing_id) AS unresolved_targets
    FROM v_confirmed_filter_facts f
   WHERE NOT EXISTS (SELECT 1 FROM kg_facts s WHERE s.thing_id = f.thing_id AND s.replaced_by IS NULL
                      AND s.fact_key = 'rule_status' AND s.value = 'retired');

-- ---- approvals and hand-owned filters (rule items) -----------------------------------------------------------
DROP VIEW IF EXISTS v_approvals;
CREATE VIEW v_approvals AS
  SELECT f.id AS fact_id, f.value AS digest, f.answer_id, a.said_on, a.words, a.asked_by, a.words_kind
    FROM kg_facts f JOIN kg_answers a ON a.id = f.answer_id
   WHERE f.fact_key = 'approved_digest' AND f.replaced_by IS NULL AND f.who = 'owner'
     AND a.question = 'approve staged filters sha256:' || f.value;

DROP VIEW IF EXISTS v_hand_owned;
CREATE VIEW v_hand_owned AS
  SELECT t.key AS item_key, t.name AS filter_ref, f.value AS why, f.source_ref
    FROM kg_facts f JOIN kg_things t ON t.id = f.thing_id
   WHERE f.fact_key = 'hand_owned' AND f.replaced_by IS NULL;
