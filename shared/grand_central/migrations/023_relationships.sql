-- 023_relationships.sql: Phase 3 step 3.3. user_version 22 -> 23. Vision 3.7.3 (relationship table) and 3.7.4 rules 8, 10, 11; plan 3.3.
-- The five relationships (member_of, part_of, involves, knows, reports_to) are already words in the vocabulary (005, 010, 021).
-- What this adds is the two ends each one may join, and the rules behind them, as the second lock under the front door
-- (store_graph.add_link refuses the same things in words first):
--   * endpoint kinds: member_of person->organization; part_of organization->organization, project->organization, item/event->project;
--     involves event/project->person or address; knows and reports_to person->person.
--     Old frozen kinds stay readable and replayable: member_of person->circle/company, part_of and involves from `episode`.
--   * `involves` written by code is only the calendar's attendee list (event, sure, source code); a project's people, or anyone
--     not on the invite, need his word. (Placement of member_of / part_of an organization / reports_to / knows is already his word, 021.)
--   * no loops: a reports_to line, or an organization part_of line, that would make a thing sit above itself is refused.
-- Nothing is written here; the schema carries rules only. Structure left empty (no members, no chart) stays valid.

CREATE TRIGGER kg_links_ends_insert BEFORE INSERT ON kg_links
WHEN NEW.kind IN ('member_of', 'part_of', 'involves', 'knows', 'reports_to')
 AND NOT EXISTS (
   SELECT 1 FROM kg_things a, kg_things b WHERE a.id = NEW.from_id AND b.id = NEW.to_id AND (
        (NEW.kind = 'member_of' AND a.kind = 'person' AND b.kind IN ('organization', 'circle', 'company'))
     OR (NEW.kind = 'part_of' AND ((a.kind = 'organization' AND b.kind = 'organization')
                                OR (a.kind = 'project' AND b.kind = 'organization')
                                OR (a.kind IN ('item', 'event', 'episode') AND b.kind = 'project')))
     OR (NEW.kind = 'involves' AND a.kind IN ('event', 'project', 'episode') AND b.kind IN ('person', 'address'))
     OR (NEW.kind IN ('knows', 'reports_to') AND a.kind = 'person' AND b.kind = 'person')))
BEGIN SELECT RAISE(ABORT, 'wrong ends: that relationship does not join those two kinds of thing'); END;

CREATE TRIGGER kg_links_involves_by_code_insert BEFORE INSERT ON kg_links
WHEN NEW.kind = 'involves' AND NEW.who <> 'owner'
 AND NOT ((SELECT kind FROM kg_things WHERE id = NEW.from_id) = 'episode'
          OR ((SELECT kind FROM kg_things WHERE id = NEW.from_id) = 'event' AND NEW.certainty = 'sure' AND NEW.source_kind = 'code'))
BEGIN SELECT RAISE(ABORT, 'involves by code is only the invite list of an event; anyone else, and every project, is his word'); END;

-- loops. A line is live while it is not replaced and has not ended. The new line closes a loop when its far end already
-- reaches its near end going up the live lines (or when both ends are one thing).
CREATE TRIGGER kg_links_no_loop_insert BEFORE INSERT ON kg_links
WHEN NEW.replaced_by IS NULL AND NEW.true_until IS NULL
 AND (NEW.kind = 'reports_to' OR (NEW.kind = 'part_of' AND (SELECT kind FROM kg_things WHERE id = NEW.from_id) = 'organization'))
 AND (NEW.from_id = NEW.to_id OR EXISTS (
   WITH RECURSIVE up(id) AS (
     SELECT NEW.to_id
     UNION
     SELECT l.to_id FROM kg_links l JOIN up ON l.from_id = up.id
      WHERE l.kind = NEW.kind AND l.replaced_by IS NULL AND l.true_until IS NULL)
   SELECT 1 FROM up WHERE id = NEW.from_id))
BEGIN SELECT RAISE(ABORT, 'loop: that line would put someone above themselves'); END;

-- add_link writes a replacing line as superseded first and only then makes it current; the check is repeated at that moment.
CREATE TRIGGER kg_links_no_loop_update BEFORE UPDATE OF replaced_by, true_until ON kg_links
WHEN NEW.replaced_by IS NULL AND NEW.true_until IS NULL AND (OLD.replaced_by IS NOT NULL OR OLD.true_until IS NOT NULL)
 AND (NEW.kind = 'reports_to' OR (NEW.kind = 'part_of' AND (SELECT kind FROM kg_things WHERE id = NEW.from_id) = 'organization'))
 AND (NEW.from_id = NEW.to_id OR EXISTS (
   WITH RECURSIVE up(id) AS (
     SELECT NEW.to_id
     UNION
     SELECT l.to_id FROM kg_links l JOIN up ON l.from_id = up.id
      WHERE l.kind = NEW.kind AND l.replaced_by IS NULL AND l.true_until IS NULL AND l.id <> NEW.id)
   SELECT 1 FROM up WHERE id = NEW.from_id))
BEGIN SELECT RAISE(ABORT, 'loop: that line would put someone above themselves'); END;
