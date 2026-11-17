-- 024_levels_above_me.sql: Phase 3 step 3.4. Vision 3.7.3 (levels_above_me), 3.7.4 rule 9, 3.7.5; plan 3.4. No new table: a level is COMPUTED, never stored.
-- Per person, in this order: (1) the number HE set (the fact levels_above_me, who=owner); (2) else the count of reports_to steps from
-- person:me up to that person, if an unbroken chain of his reports_to lines exists; (3) else unknown (level NULL). `source` says which.
-- The machine never places anyone: there is no machine level to store. Depends on nothing from 023: with no reports_to lines the chain
-- is empty and every person without his number is unknown. Direction: "A reports_to B" means B is A's boss, so B is one level above A.
-- Callers (3.5 relation to the person, 3.8 scoring): SELECT level, source FROM v_levels_above_me WHERE person_key = ?  (NULL level counts for nothing).

-- his number must be a whole number (0 = same level); code can never write it (021 trigger covers insert; this covers editing one)
CREATE TRIGGER kg_facts_levels_whole_number BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'levels_above_me' AND (NEW.value = '' OR NEW.value GLOB '*[^0-9]*')
BEGIN SELECT RAISE(ABORT, 'levels_above_me is a whole number (0 = same level)'); END;
CREATE TRIGGER kg_facts_levels_is_his_update BEFORE UPDATE OF fact_key, value, who, answer_id ON kg_facts
WHEN NEW.fact_key = 'levels_above_me' AND NEW.who <> 'owner'
BEGIN SELECT RAISE(ABORT, 'levels_above_me is his word: who=owner and an answer'); END;

CREATE VIEW v_levels_above_me AS
WITH RECURSIVE
  up(id, depth) AS (
    SELECT id, 0 FROM kg_things WHERE key = 'person:me'
    UNION
    SELECT l.to_id, up.depth + 1
      FROM up JOIN kg_links l ON l.from_id = up.id AND l.kind = 'reports_to' AND l.who = 'owner'
                              AND l.replaced_by IS NULL AND l.true_until IS NULL
     WHERE up.depth < 50),
  chain(id, depth) AS (SELECT id, MIN(depth) FROM up GROUP BY id),
  his(thing_id, level) AS (
    SELECT thing_id, CAST(value AS INTEGER) FROM kg_facts
     WHERE fact_key = 'levels_above_me' AND who = 'owner' AND replaced_by IS NULL AND true_until IS NULL
       AND value <> '' AND value NOT GLOB '*[^0-9]*')
SELECT t.key AS person_key, t.name AS person_name,
       CASE WHEN h.level IS NOT NULL THEN h.level WHEN c.id IS NOT NULL THEN c.depth END AS level,
       CASE WHEN h.level IS NOT NULL THEN 'owner' WHEN c.id IS NOT NULL THEN 'chain' ELSE 'unknown' END AS source
  FROM kg_things t
  LEFT JOIN his h ON h.thing_id = t.id
  LEFT JOIN chain c ON c.id = t.id
 WHERE t.kind = 'person' AND t.merged_into IS NULL AND t.retired_at IS NULL;
