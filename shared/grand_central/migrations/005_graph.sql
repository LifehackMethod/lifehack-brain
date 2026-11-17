-- 005_graph.sql: World Model Trial Step 1, the flexible memory (a knowledge graph with provenance). user_version 4 -> 5.
-- Six pieces BESIDE today's tables; nothing is dropped or changed. Prefixed kg_ because `facts` already exists (legacy).
--   kg_things   everything in his world, one row each, with a kind
--   kg_links    any two things connected, the kind of link named
--   kg_facts    a statement about one thing: who said it, how sure, where from, true-from/until, what replaced it
--   kg_answers  his answers, ONE PER DECISION, append-only. Each carries its decision in plain columns
--               (subject + fact_key + value), so every fact and link he gave can be rebuilt from this table alone.
--   kg_scores   code-computed numbers (signal name + version + when). Disposable; recomputable.
--   kg_vocab / kg_fact_keys   allowed words. The front door (store_graph.py) refuses anything not listed here.
-- Reached only through store.py -> store_graph.py. No foreign keys, same as 003 (ids are stable; rebuilds keep them).

CREATE TABLE kg_vocab(
  list TEXT NOT NULL,                  -- thing_kind | link_kind | who | certainty | source_kind | v:<value list name>
  value TEXT NOT NULL,
  note TEXT,
  PRIMARY KEY(list, value));

-- which facts may exist. value_list NULL = free text (still non-empty); else every value must be in kg_vocab(list=value_list).
CREATE TABLE kg_fact_keys(
  key TEXT PRIMARY KEY,
  value_list TEXT,                     -- e.g. 'v:inbox'; NULL = free text
  subject_kinds TEXT NOT NULL,         -- comma list of thing kinds it may describe, or '*'
  note TEXT);

CREATE TABLE kg_things(
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,                  -- checked against kg_vocab(thing_kind)
  key TEXT NOT NULL UNIQUE,            -- '<kind>:<normalized name>', e.g. 'address:someone@example.com', 'label:example'
  name TEXT NOT NULL,                  -- display
  legacy_ref TEXT,                     -- 'people:3', 'circles:2', 'rules:17' ... for things copied from today's tables
  created_by TEXT NOT NULL,            -- who: owner | code | ai_research | ai_guess
  created_at TEXT NOT NULL);
CREATE INDEX kg_things_kind ON kg_things(kind);

CREATE TABLE kg_links(
  id INTEGER PRIMARY KEY,
  from_id INTEGER NOT NULL,
  kind TEXT NOT NULL,                  -- kg_vocab(link_kind)
  to_id INTEGER NOT NULL,
  role TEXT,                           -- optional free word on the link (legacy circle role)
  who TEXT NOT NULL, certainty TEXT NOT NULL,
  source_kind TEXT NOT NULL, source_ref TEXT,
  answer_id INTEGER,                   -- kg_answers.id when he said it
  true_from TEXT, true_until TEXT,
  replaced_by INTEGER,                 -- kg_links.id that superseded this one (NULL = current)
  created_at TEXT NOT NULL);
CREATE INDEX kg_links_from ON kg_links(from_id, kind);
CREATE INDEX kg_links_to ON kg_links(to_id, kind);

CREATE TABLE kg_facts(
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
  created_at TEXT NOT NULL,
  CHECK(who <> 'owner' OR answer_id IS NOT NULL));  -- his word always points at the answer it came from
CREATE INDEX kg_facts_thing ON kg_facts(thing_id, fact_key);
CREATE INDEX kg_facts_answer ON kg_facts(answer_id);

CREATE TABLE kg_answers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question TEXT NOT NULL,              -- the question as asked (or the topic, for answers caught up from older notes)
  words TEXT NOT NULL,                 -- his exact words
  asked_by TEXT NOT NULL,              -- window or skill name
  said_on TEXT NOT NULL,               -- YYYY-MM-DD he said it
  subject_key TEXT,                    -- kg_things.key the decision is about (NULL = no fact, e.g. a plain yes to a proposal)
  subject_kind TEXT, subject_name TEXT,-- so the thing can be re-created on rebuild
  fact_key TEXT,                       -- a kg_fact_keys key, or 'link:<link_kind>' (value is then the target thing key)
  value TEXT,
  true_until TEXT,
  queue_id INTEGER,                    -- the queue row it answered, if any
  legacy_answer_log_id INTEGER,
  recorded_at TEXT NOT NULL,
  CHECK((fact_key IS NULL) = (value IS NULL)),
  CHECK(fact_key IS NULL OR subject_key IS NOT NULL));
CREATE TRIGGER kg_answers_no_update BEFORE UPDATE ON kg_answers
BEGIN SELECT RAISE(ABORT, 'kg_answers is append-only: UPDATE refused'); END;
CREATE TRIGGER kg_answers_no_delete BEFORE DELETE ON kg_answers
BEGIN SELECT RAISE(ABORT, 'kg_answers is append-only: DELETE refused'); END;

CREATE TABLE kg_scores(
  id INTEGER PRIMARY KEY,
  subject_ref TEXT NOT NULL,           -- 'item:301' | 'thing:12'
  signal TEXT NOT NULL, signal_version INTEGER NOT NULL,
  value REAL, reason TEXT,
  computed_at TEXT NOT NULL,
  UNIQUE(subject_ref, signal));        -- recompute replaces

-- current (not replaced, not expired-by-date is left to the reader: dates are compared against a clock, not stored now)
CREATE VIEW kg_current_facts AS
  SELECT f.*, t.kind AS thing_kind, t.key AS thing_key, t.name AS thing_name
    FROM kg_facts f JOIN kg_things t ON t.id = f.thing_id WHERE f.replaced_by IS NULL;
CREATE VIEW kg_current_links AS
  SELECT l.*, a.key AS from_key, b.key AS to_key
    FROM kg_links l JOIN kg_things a ON a.id = l.from_id JOIN kg_things b ON b.id = l.to_id WHERE l.replaced_by IS NULL;

-- ---- allowed words (seed). Extend only by a new migration or store_graph.add_vocab (logged). ----
INSERT INTO kg_vocab(list, value, note) VALUES
 ('thing_kind','person',NULL),('thing_kind','company',NULL),('thing_kind','project',NULL),('thing_kind','trip',NULL),
 ('thing_kind','label',NULL),('thing_kind','place',NULL),('thing_kind','desk',NULL),
 ('thing_kind','address','one exact email address'),('thing_kind','domain','an email domain, no @'),
 ('thing_kind','circle','a group of people (legacy circles)'),('thing_kind','rule','a mail rule (legacy rules)'),
 ('thing_kind','episode','a situation stitched by the engine'),('thing_kind','world','the one world-level thing'),
 ('link_kind','works_at',NULL),('link_kind','is_about',NULL),('link_kind','is_in',NULL),('link_kind','belongs_to',NULL),
 ('link_kind','address_of','address -> person/company'),('link_kind','member_of','person -> circle'),
 ('link_kind','applies_to','rule -> address/domain'),('link_kind','involves','episode -> person/address'),
 ('link_kind','project_of','project -> circle (dated circle IS a project)'),
 ('who','owner','the owner''s own word; always traces to a kg_answers row'),('who','code',NULL),('who','ai_research',NULL),('who','ai_guess',NULL),
 ('certainty','sure',NULL),('certainty','likely',NULL),('certainty','guess',NULL),
 ('source_kind','answer',NULL),('source_kind','item',NULL),('source_kind','file',NULL),('source_kind','legacy',NULL),('source_kind','code',NULL),
 ('v:inbox','stay',NULL),('v:inbox','skip',NULL),('v:inbox','undecided',NULL),
 ('v:destination','inbox',NULL),('v:destination','trash',NULL),('v:destination','promos',NULL),('v:destination','archive',NULL),
 ('v:destination','undecided',NULL),
 ('v:importance','high',NULL),('v:importance','normal',NULL),('v:importance','low',NULL),('v:importance','undecided',NULL),
 ('v:yesno','yes',NULL),('v:yesno','no',NULL),('v:yesno','undecided',NULL),
 ('v:domain','none',NULL),
 ('v:domain','undecided',NULL),
 ('v:need','action-urgent',NULL),('v:need','action-not-urgent',NULL),('v:need','waiting-on-someone',NULL),('v:need','just-see',NULL),
 ('v:need','just-keep',NULL),('v:need','nothing',NULL),('v:need','undecided',NULL),
 ('v:shelf_anchor','arrival',NULL),('v:shelf_anchor','event_date',NULL),('v:shelf_anchor','job_end',NULL),('v:shelf_anchor','none',NULL),
 ('v:shelf_anchor','undecided',NULL),
 ('v:rule_status','proposed',NULL),('v:rule_status','approved',NULL),('v:rule_status','retired',NULL),
 ('v:circle_kind','standing',NULL),('v:circle_kind','dated',NULL),('v:circle_kind','undecided',NULL),
 ('v:match_kind','address',NULL),('v:match_kind','domain',NULL);

INSERT INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('inbox','v:inbox','address,domain,company,person,label','does new mail stay in the inbox or skip it'),
 ('destination','v:destination','address,domain,company,person,rule','where mail goes: inbox/trash/promos/archive'),
 ('label',NULL,'address,domain,company,person,rule','Gmail label name it gets (free text; one fact per label)'),
 ('importance','v:importance','address,domain,company,person,label,project','how much it matters to him'),
 ('label_matters','v:yesno','label','is this label one he cares about'),
 ('domain','v:domain','*','which desk/domain'),
 ('need','v:need','address,domain,rule,company,person','what it needs from him (decision tree Q1)'),
 ('shelf_days',NULL,'address,domain,rule','shelf life in days (integer as text)'),
 ('shelf_anchor','v:shelf_anchor','address,domain,rule','shelf life counts from'),
 ('kind_label',NULL,'rule','kind of mail, e.g. receipt'),
 ('folder',NULL,'rule','legacy rule folder (Gmail label it files to)'),
 ('rule_status','v:rule_status','rule','legacy rule status'),
 ('match_kind','v:match_kind','rule','legacy rule match kind'),
 ('subject_glob',NULL,'rule','legacy rule subject pattern'),
 ('exception',NULL,'rule','a subject word that changes the need: "word=need"'),
 ('tier','v:importance','person','legacy people tier'),
 ('circle_kind','v:circle_kind','circle','standing or dated'),
 ('relationship',NULL,'person,company','how he relates to them, free text'),
 ('life_fact',NULL,'*','a dated statement about his life, free text'),
 ('note',NULL,'*','a free note'),
 ('keyword',NULL,'world','a subject phrase on a list: "list_name=phrase"'),
 ('legacy_fact',NULL,'*','a row of the legacy facts table: "fact_key=value"'),
 ('canon',NULL,'*','a line from desk canon (legacy canon_facts)');
