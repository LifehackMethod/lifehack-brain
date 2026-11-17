-- 021_organizations.sql: Phase 3 step 3.1. user_version 20 -> 21. Vision 3.7.3, 3.7.4 (rules 2, 8, 9); plan 3.1.
-- ONE kind `organization` with four types held as the fact `org_type` (company, department, team, group); nesting is `part_of`.
-- Things are never deleted: an old `company` or `circle` thing is retired (retired_at) and merged (merged_into) into its
-- organization. The DATA move (the 13 companies and 6 circles) is org_moves.py, run after this schema, and is recorded in
-- `org_moves` (the permanent record layer, like thing_keys) so a rebuild reproduces it exactly.
-- Placement is his word (rule 8): a member_of / part_of to an organization, reports_to, knows and levels_above_me are refused
-- unless who = 'owner' (the front door says so in words; the triggers below are the second lock).

ALTER TABLE kg_things ADD COLUMN merged_into INTEGER REFERENCES kg_things(id);
ALTER TABLE kg_things ADD COLUMN retired_at TEXT;

INSERT INTO kg_vocab(list, value, note) VALUES
 ('thing_kind', 'organization', 'a company, department, team or group (its type is the fact org_type)'),
 ('link_kind', 'reports_to', 'person -> person (their boss); his word only'),
 ('link_kind', 'knows', 'person -> person (a tie between people); his word only'),
 ('v:org_type', 'company', 'a company or any formal body (has a hierarchy inside)'),
 ('v:org_type', 'department', 'a part of a company'),
 ('v:org_type', 'team', 'a working group inside a company or department'),
 ('v:org_type', 'group', 'a family, a circle of friends, a club: no parent, no reporting lines'),
 ('v:org_type', 'undecided', NULL);

INSERT INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('org_type', 'v:org_type', 'organization', 'company / department / team / group'),
 ('levels_above_me', NULL, 'person', 'how many levels above him this person is (a whole number, 0 = same level); his word only');

-- every fact that could describe a company may describe an organization
UPDATE kg_fact_keys SET subject_kinds = subject_kinds || ',organization'
 WHERE subject_kinds <> '*' AND (',' || subject_kinds || ',') LIKE '%,company,%' AND (',' || subject_kinds || ',') NOT LIKE '%,organization,%';

-- the record of the moves: which old thing became which organization (append-only; rebuild reads it)
CREATE TABLE org_moves(
  id INTEGER PRIMARY KEY,
  old_key TEXT NOT NULL UNIQUE,
  old_kind TEXT NOT NULL,
  new_key TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  org_type TEXT NOT NULL,
  certainty TEXT NOT NULL,
  source TEXT NOT NULL,
  moved_at TEXT NOT NULL) STRICT;
CREATE TRIGGER org_moves_no_update BEFORE UPDATE ON org_moves
BEGIN SELECT RAISE(ABORT, 'org_moves is append-only: UPDATE refused'); END;
CREATE TRIGGER org_moves_no_delete BEFORE DELETE ON org_moves
BEGIN SELECT RAISE(ABORT, 'org_moves is append-only: DELETE refused'); END;

-- Placement is his word (Vision 3.7.4 rule 8). A line that places someone (member_of or part_of INTO an organization, reports_to,
-- knows) and the fact levels_above_me are refused unless who = 'owner'; his line must carry the answer it came from.
CREATE TRIGGER kg_links_placement_is_his_insert BEFORE INSERT ON kg_links
WHEN (NEW.kind IN ('reports_to', 'knows')
      OR (NEW.kind IN ('member_of', 'part_of') AND (SELECT kind FROM kg_things WHERE id = NEW.to_id) = 'organization'))
 AND (NEW.who <> 'owner' OR NEW.answer_id IS NULL)
BEGIN SELECT RAISE(ABORT, 'placement is his word: member_of / part_of an organization, reports_to and knows need who=owner and an answer'); END;
CREATE TRIGGER kg_links_placement_is_his_update BEFORE UPDATE OF kind, to_id, who, answer_id ON kg_links
WHEN (NEW.kind IN ('reports_to', 'knows')
      OR (NEW.kind IN ('member_of', 'part_of') AND (SELECT kind FROM kg_things WHERE id = NEW.to_id) = 'organization'))
 AND (NEW.who <> 'owner' OR NEW.answer_id IS NULL)
BEGIN SELECT RAISE(ABORT, 'placement is his word: member_of / part_of an organization, reports_to and knows need who=owner and an answer'); END;
CREATE TRIGGER kg_facts_levels_is_his BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'levels_above_me' AND NEW.who <> 'owner'
BEGIN SELECT RAISE(ABORT, 'levels_above_me is his word: who=owner and an answer'); END;

-- The Gmail filter compiler's source view (v_filter_spec reads it): redefined so his company-level rules still count after the move.
-- A confirmed fact now sits on an organization, but its answer was recorded under the old company key: org_moves maps one to the other.
DROP VIEW v_confirmed_filter_facts;
CREATE VIEW v_confirmed_filter_facts AS
  SELECT f.id, f.thing_id, f.fact_key, f.value, f.condition, f.answer_id, f.source_ref, f.source_kind, f.who,
         t.kind AS tkind, t.key AS tkey
    FROM kg_facts f JOIN kg_things t ON t.id = f.thing_id
   WHERE f.replaced_by IS NULL AND f.fact_key IN ('label', 'destination', 'inbox') AND f.value <> 'undecided'
     AND t.kind IN ('address', 'domain', 'company', 'organization', 'person', 'topic', 'label', 'rule')
     AND ((f.who = 'owner' AND f.answer_id IS NOT NULL AND EXISTS (
              SELECT 1 FROM kg_answers a WHERE a.id = f.answer_id AND (a.subject_key = t.key OR a.subject_key IN (SELECT old_key FROM org_moves WHERE new_key = t.key)) AND a.fact_key = f.fact_key
                 AND a.value = f.value AND a.condition IS f.condition))
          OR (f.who = 'code' AND f.source_kind = 'legacy' AND f.source_ref LIKE 'rules:%' AND EXISTS (
              SELECT 1 FROM kg_things r
                JOIN kg_current_links l ON l.from_id = r.id AND l.kind = 'applies_to' AND l.to_id = f.thing_id
                JOIN kg_facts rs ON rs.thing_id = r.id AND rs.fact_key = 'rule_status' AND rs.source_kind = 'legacy'
                                AND rs.source_ref = f.source_ref
               WHERE r.kind = 'rule' AND r.legacy_ref = f.source_ref)));

-- Where a sender-ish thing points (the Gmail `from` tokens): an organization's domains count exactly as a company's did
-- (v_owner_senders and v_owner_unresolved read this view; without it an organization's domains would look unresolved).
DROP VIEW v_thing_senders;
CREATE VIEW v_thing_senders AS
  SELECT t.id AS thing_id, t.key AS thing_key, t.kind AS thing_kind,
         CASE t.kind WHEN 'address' THEN t.name WHEN 'domain' THEN '@' || t.name END AS sender
    FROM kg_things t WHERE t.kind IN ('address', 'domain')
  UNION ALL   -- company or organization -> its domains (domain_of: domain -> company/organization)
  SELECT c.id, c.key, c.kind, '@' || d.name
    FROM kg_things c JOIN kg_current_links dl ON dl.to_id = c.id AND dl.kind = 'domain_of'
    JOIN kg_things d ON d.id = dl.from_id WHERE c.kind IN ('company', 'organization')
  UNION ALL   -- person -> their addresses (address_of: address -> person)
  SELECT p.id, p.key, 'person', a.name
    FROM kg_things p JOIN kg_current_links al ON al.to_id = p.id AND al.kind = 'address_of'
    JOIN kg_things a ON a.id = al.from_id WHERE p.kind = 'person';
