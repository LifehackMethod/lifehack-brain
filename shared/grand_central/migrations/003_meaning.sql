-- 003_meaning.sql: Step 5, the meaning pieces. Depends on 002 (items). Brings user_version 2 -> 3.
-- No foreign keys on purpose: the world-model tables (people, circles, ...) are wiped and rebuilt from answer_log,
-- and rows here point at them by id. Rebuilds give back the same ids (see store_meaning.rebuild_model).
-- Urgency is NOT stored anywhere: see store_meaning.urgency (pure function with a clock parameter).

-- A dated circle IS a project: circle_id links to the existing circle (no duplicated name/dates).
-- A project with no circle (circle_id NULL) carries its own name.
CREATE TABLE projects(
  id INTEGER PRIMARY KEY,
  circle_id INTEGER UNIQUE,            -- the dated circle this project is, or NULL
  name TEXT,                           -- only for circle-less projects; circle-linked take the circle's name
  due_on TEXT,                         -- YYYY-MM-DD; NULL = use the circle's valid_until
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','done','retired')),
  source TEXT, answer_id INTEGER, created_at TEXT NOT NULL,
  CHECK(circle_id IS NOT NULL OR name IS NOT NULL));

CREATE TABLE item_projects(
  item_id INTEGER NOT NULL, project_id INTEGER NOT NULL,
  source TEXT, answer_id INTEGER, created_at TEXT NOT NULL,
  PRIMARY KEY(item_id, project_id));

CREATE TABLE notes(
  id INTEGER PRIMARY KEY,
  subject_kind TEXT NOT NULL CHECK(subject_kind IN ('person','project')),
  subject_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  source TEXT, answer_id INTEGER, created_at TEXT NOT NULL);

-- ONE overrides list, any level. Every row says why and when to look again.
CREATE TABLE overrides(
  id INTEGER PRIMARY KEY,
  level TEXT NOT NULL CHECK(level IN ('item','project','person','rule')),
  subject_id INTEGER NOT NULL,         -- items.id | projects.id | people.id | rules.id, per level
  type TEXT NOT NULL CHECK(type IN ('pin','quiet-until')),
  until_on TEXT,                       -- quiet-until only: YYYY-MM-DD
  reason TEXT NOT NULL CHECK(length(trim(reason)) > 0),
  review_by TEXT NOT NULL,             -- YYYY-MM-DD
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','retired')),
  source TEXT, answer_id INTEGER, created_at TEXT NOT NULL, retired_at TEXT,
  CHECK((type = 'quiet-until') = (until_on IS NOT NULL)));
CREATE INDEX overrides_subject ON overrides(level, subject_id, status);

-- Questions for the planning skills.
CREATE TABLE queue(
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  subject_ref TEXT NOT NULL,           -- e.g. 'person:12', 'rule:7', 'item:301'
  question TEXT NOT NULL,
  proposed_answer TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','answered','dismissed')),
  created_at TEXT NOT NULL, answered_at TEXT, answer TEXT);
CREATE INDEX queue_status ON queue(status);

-- Projects with their effective name, due date and domain (circle-linked read through to the circle).
CREATE VIEW v_projects AS
  SELECT p.id, p.circle_id, COALESCE(c.name, p.name) AS name,
         COALESCE(p.due_on, c.valid_until) AS due_on,
         c.domain AS domain, p.status
    FROM projects p LEFT JOIN v_circles c ON c.id = p.circle_id;

-- Relationship score rolled up from address to person: the best of his addresses (override beats guess per address).
CREATE VIEW v_person_scores AS
  SELECT a.person_id, COUNT(*) AS n_addresses, COUNT(s.score) AS n_scored, MAX(s.score) AS score,
         (SELECT a2.address FROM v_addresses a2 JOIN v_relationship_scores s2 ON s2.address = a2.address
           WHERE a2.person_id = a.person_id ORDER BY s2.score DESC, a2.address LIMIT 1) AS best_address
    FROM v_addresses a LEFT JOIN v_relationship_scores s ON s.address = a.address
   WHERE a.person_id IS NOT NULL
   GROUP BY a.person_id;
