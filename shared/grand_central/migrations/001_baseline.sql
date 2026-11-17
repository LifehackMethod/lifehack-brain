-- 001_baseline.sql: generated 2026-11-12 from the LIVE rig.db sqlite_master (read-only), in creation order.
-- Column order includes the post-ALTER columns. Includes `events` (no DDL anywhere else in code).
-- Never edit: an applied migration is history.

CREATE TABLE labels(
        id TEXT PRIMARY KEY, name TEXT, type TEXT);

CREATE TABLE threads(
        id TEXT PRIMARY KEY, message_count INTEGER, first_ms INTEGER, last_ms INTEGER);

CREATE TABLE messages(
        id TEXT PRIMARY KEY, thread_id TEXT, internal_date INTEGER, label_ids TEXT, size INTEGER,
        from_addr TEXT, from_name TEXT, to_addrs TEXT, to_names TEXT, cc_addrs TEXT, cc_names TEXT,
        reply_to TEXT, subject TEXT, list_id TEXT, list_unsubscribe_present INTEGER,
        multipart_mixed INTEGER, spf_pass INTEGER, dkim_pass INTEGER, dmarc_pass INTEGER,
        is_sent INTEGER, gate_verdict TEXT, precedence TEXT, auto_submitted TEXT, list_headers_present INTEGER);

CREATE TABLE calendar_events(
        id TEXT PRIMARY KEY, start TEXT, end TEXT, all_day INTEGER, status TEXT,
        organizer_email TEXT, attendee_emails TEXT, summary TEXT, location TEXT, description TEXT,
        gate_verdict TEXT);

CREATE TABLE tasks(
        id TEXT PRIMARY KEY, list_id TEXT, title TEXT, notes TEXT, status TEXT,
        due TEXT, completed TEXT, updated TEXT, gate_verdict TEXT);

CREATE TABLE quarantine(
        item_id TEXT, kind TEXT, verdict TEXT, reason TEXT, at TEXT);

CREATE TABLE errors(
        item_id TEXT, kind TEXT, error TEXT, at TEXT);

CREATE TABLE runs(
        started TEXT, finished TEXT, args TEXT, counts TEXT);

CREATE TABLE planted_results(
        item_id TEXT PRIMARY KEY, kind TEXT, verdict TEXT, expect TEXT, reason TEXT, at TEXT);

CREATE TABLE planted_quarantine(
        item_id TEXT, kind TEXT, verdict TEXT, reason TEXT, at TEXT);

CREATE TABLE source_state(
        source TEXT PRIMARY KEY, last_success_at TEXT, rows INTEGER);

CREATE TABLE filters(
        id TEXT PRIMARY KEY, criteria_json TEXT, action_json TEXT);

CREATE TABLE contacts(
        resource_name TEXT PRIMARY KEY, emails_json TEXT, groups_json TEXT);

CREATE TABLE desk_verdicts(
  message_id TEXT, thread_id TEXT, desk TEXT, verdict TEXT,
  PRIMARY KEY(desk, message_id, thread_id));

CREATE TABLE wm_meta(
  key TEXT PRIMARY KEY, value TEXT, set_at TEXT);

CREATE TABLE answer_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT NOT NULL,          -- file basename
  round INTEGER NOT NULL,
  entry_kind TEXT NOT NULL,
  ordinal INTEGER NOT NULL,           -- position within (file, entry_kind)
  subject_key TEXT,                   -- sender address, or the named org for round-5 'confirmed' lines; else NULL
  grade TEXT, pattern TEXT, note TEXT, circle TEXT,
  text_verbatim TEXT NOT NULL,        -- the answer's own words (free text or the entry joined)
  raw_json TEXT NOT NULL,             -- the entry exactly as in the file
  answered_on TEXT,
  UNIQUE(source_file, entry_kind, ordinal));

CREATE TRIGGER answer_log_no_update BEFORE UPDATE ON answer_log
BEGIN SELECT RAISE(ABORT, 'answer_log is append-only: UPDATE refused'); END;

CREATE TRIGGER answer_log_no_delete BEFORE DELETE ON answer_log
BEGIN SELECT RAISE(ABORT, 'answer_log is append-only: DELETE refused'); END;

CREATE TABLE people(
  id INTEGER PRIMARY KEY,
  label TEXT,                          -- display only
  tier_guess TEXT, tier_override TEXT, -- high | normal | low
  guess_note TEXT,
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT, status TEXT NOT NULL DEFAULT 'active', retired_at TEXT, retired_reason TEXT);

CREATE TABLE addresses(
  id INTEGER PRIMARY KEY,
  address TEXT NOT NULL UNIQUE,        -- lowercased
  person_id INTEGER,                   -- many addresses -> one person; NULL for services
  person_id_override INTEGER,
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT, status TEXT NOT NULL DEFAULT 'active', retired_at TEXT, retired_reason TEXT);

CREATE TABLE circles(
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  kind_guess TEXT, kind_override TEXT, -- standing | dated
  domain_guess TEXT, domain_override TEXT, -- a domain (kg_vocab v:domain) | none
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT, status TEXT NOT NULL DEFAULT 'active', retired_at TEXT, retired_reason TEXT);

CREATE TABLE circle_members(
  id INTEGER PRIMARY KEY,
  circle_id INTEGER NOT NULL, person_id INTEGER NOT NULL,
  role TEXT,
  valid_from TEXT, valid_until TEXT,   -- dated membership; NULL = not answered
  valid_until_override TEXT,
  source TEXT, answer_id INTEGER, status TEXT NOT NULL DEFAULT 'active', retired_at TEXT, retired_reason TEXT,
  UNIQUE(circle_id, person_id));

CREATE TABLE rules(
  id INTEGER PRIMARY KEY,
  match_kind TEXT NOT NULL CHECK(match_kind IN ('address','domain')),
  match_value TEXT NOT NULL,           -- lowercased address, or domain without '@'
  subject_glob TEXT NOT NULL DEFAULT '',  -- '' = any subject
  kind_label TEXT,                     -- kind of mail, e.g. receipt, shipping
  need_guess TEXT, need_override TEXT,
  domain_guess TEXT, domain_override TEXT,
  shelf_days_guess INTEGER, shelf_days_override INTEGER,
  shelf_anchor_guess TEXT, shelf_anchor_override TEXT, -- arrival | event_date | job_end | none
  need_basis TEXT, domain_basis TEXT,  -- stated | inferred
  guess_note TEXT,
  status TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN ('proposed','approved','retired')),
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT, folder_guess TEXT, folder_override TEXT, retired_at TEXT, retired_reason TEXT,
  UNIQUE(match_kind, match_value, subject_glob));

CREATE TABLE rule_exceptions(
  id INTEGER PRIMARY KEY,
  rule_id INTEGER NOT NULL,
  word TEXT NOT NULL,                  -- matched case-insensitively in the subject
  need_guess TEXT, need_override TEXT, -- the need when the word appears
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT, status TEXT NOT NULL DEFAULT 'active', retired_at TEXT, retired_reason TEXT,
  UNIQUE(rule_id, word));

CREATE TABLE facts(
  id INTEGER PRIMARY KEY,
  subject_kind TEXT NOT NULL,          -- person | rule | world
  subject_id INTEGER NOT NULL DEFAULT 0,  -- 0 for world-level facts (keeps UNIQUE honest; NULLs never collide)
  fact_key TEXT NOT NULL,
  value_guess TEXT, value_override TEXT,
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT, status TEXT NOT NULL DEFAULT 'active', retired_at TEXT, retired_reason TEXT,
  UNIQUE(subject_kind, subject_id, fact_key));

CREATE TABLE keywords(
  id INTEGER PRIMARY KEY,
  list_name TEXT NOT NULL,             -- job_phrases | current_gig_markers | clock_words
  phrase TEXT NOT NULL,                -- lowercased, matched as substring of the subject
  active_guess INTEGER NOT NULL DEFAULT 1, active_override INTEGER,
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT,
  UNIQUE(list_name, phrase));

CREATE VIEW v_people AS
  SELECT id, label, COALESCE(tier_override, tier_guess) AS tier, valid_from, valid_until FROM people;

CREATE VIEW v_addresses AS
  SELECT id, address, COALESCE(person_id_override, person_id) AS person_id, valid_from, valid_until FROM addresses;

CREATE VIEW v_circles AS
  SELECT id, name, COALESCE(kind_override, kind_guess) AS kind,
         COALESCE(domain_override, domain_guess) AS domain, valid_from, valid_until FROM circles;

CREATE VIEW v_rules AS
  SELECT id, match_kind, match_value, subject_glob, kind_label,
         COALESCE(need_override, need_guess) AS need,
         COALESCE(domain_override, domain_guess) AS domain,
         COALESCE(shelf_days_override, shelf_days_guess) AS shelf_days,
         COALESCE(shelf_anchor_override, shelf_anchor_guess) AS shelf_anchor,
         status, valid_from, valid_until FROM rules;

CREATE VIEW v_rule_exceptions AS
  SELECT id, rule_id, word, COALESCE(need_override, need_guess) AS need, valid_from, valid_until FROM rule_exceptions;

CREATE VIEW v_circle_members AS
  SELECT id, circle_id, person_id, role, valid_from, COALESCE(valid_until_override, valid_until) AS valid_until FROM circle_members;

CREATE VIEW v_facts AS
  SELECT id, subject_kind, subject_id, fact_key, COALESCE(value_override, value_guess) AS value, valid_from, valid_until FROM facts;

CREATE VIEW v_keywords AS
  SELECT id, list_name, phrase FROM keywords WHERE COALESCE(active_override, active_guess) = 1;

CREATE VIEW s_ref_now AS SELECT MAX(internal_date) AS now_ms FROM messages;

CREATE VIEW s_me AS SELECT DISTINCT lower(from_addr) AS address FROM messages WHERE is_sent = 1 AND from_addr IS NOT NULL;

CREATE VIEW s_msg_addr AS
  SELECT id AS message_id, thread_id, internal_date, is_sent, 'from' AS role, lower(from_addr) AS address
    FROM messages WHERE from_addr IS NOT NULL AND from_addr <> ''
  UNION ALL
  SELECT m.id, m.thread_id, m.internal_date, m.is_sent, 'to', lower(j.value)
    FROM messages m, json_each(CASE WHEN json_valid(m.to_addrs) THEN m.to_addrs ELSE '[]' END) j
  UNION ALL
  SELECT m.id, m.thread_id, m.internal_date, m.is_sent, 'cc', lower(j.value)
    FROM messages m, json_each(CASE WHEN json_valid(m.cc_addrs) THEN m.cc_addrs ELSE '[]' END) j;

CREATE VIEW s_thread_first AS
  SELECT m.thread_id, m.id AS first_message_id, lower(m.from_addr) AS first_from, m.is_sent AS first_is_sent
    FROM messages m
   WHERE m.id = (SELECT m2.id FROM messages m2 WHERE m2.thread_id = m.thread_id
                  ORDER BY m2.internal_date, m2.id LIMIT 1);

CREATE VIEW s_addr_signals AS
  WITH a AS (SELECT DISTINCT address FROM s_msg_addr WHERE address NOT IN (SELECT address FROM s_me)),
  frm AS (SELECT address, COUNT(DISTINCT message_id) n, MAX(internal_date) last_ms, MIN(internal_date) first_ms
            FROM s_msg_addr WHERE role='from' AND is_sent=0 GROUP BY address),
  rep AS (SELECT address, COUNT(DISTINCT message_id) n, MAX(internal_date) last_ms
            FROM s_msg_addr WHERE role IN ('to','cc') AND is_sent=1 GROUP BY address),
  dir AS (SELECT address, COUNT(DISTINCT message_id) n
            FROM s_msg_addr WHERE role='to' AND is_sent=1 GROUP BY address),
  inb AS (SELECT first_from address, COUNT(*) n FROM s_thread_first WHERE first_is_sent=0 GROUP BY first_from),
  outb AS (SELECT sa.address, COUNT(DISTINCT sa.thread_id) n
             FROM s_msg_addr sa JOIN s_thread_first tf ON tf.thread_id=sa.thread_id AND tf.first_is_sent=1
            WHERE sa.role IN ('to','cc') GROUP BY sa.address),
  shared AS (SELECT f.address, COUNT(DISTINCT f.thread_id) n
               FROM s_msg_addr f JOIN s_msg_addr s ON s.thread_id=f.thread_id AND s.is_sent=1
              WHERE f.role='from' AND f.is_sent=0 GROUP BY f.address)
  SELECT a.address,
         COALESCE(frm.n,0) AS msgs_from,
         COALESCE(rep.n,0) AS replies_to,
         COALESCE(dir.n,0) AS sent_direct_to,
         COALESCE(inb.n,0) AS threads_they_started,
         COALESCE(outb.n,0) AS threads_i_started_with,
         COALESCE(shared.n,0) AS threads_both_spoke,
         CASE WHEN COALESCE(frm.n,0)>0 AND COALESCE(rep.n,0)>0 THEN 1 ELSE 0 END AS two_way,
         frm.first_ms, frm.last_ms AS last_from_ms, rep.last_ms AS last_to_ms,
         CAST((SELECT now_ms FROM s_ref_now) - MAX(COALESCE(frm.last_ms,0), COALESCE(rep.last_ms,0)) AS INTEGER)/86400000 AS days_since_last
    FROM a LEFT JOIN frm USING(address) LEFT JOIN rep USING(address) LEFT JOIN dir USING(address)
         LEFT JOIN inb USING(address) LEFT JOIN outb USING(address) LEFT JOIN shared USING(address);

CREATE VIEW s_cooccur AS
  WITH p AS (SELECT DISTINCT message_id, address FROM s_msg_addr WHERE address NOT IN (SELECT address FROM s_me))
  SELECT x.address AS addr_a, y.address AS addr_b, COUNT(*) AS msgs_together
    FROM p x JOIN p y ON x.message_id=y.message_id AND x.address < y.address
   GROUP BY x.address, y.address;

CREATE VIEW s_machine AS
  SELECT id AS message_id,
         CASE WHEN list_id IS NOT NULL AND list_id<>'' THEN 1 ELSE 0 END AS has_list_id,
         CASE WHEN precedence IN ('bulk','list','junk') THEN 1 ELSE 0 END AS bulk_precedence,
         CASE WHEN auto_submitted IS NOT NULL AND auto_submitted NOT IN ('','no') THEN 1 ELSE 0 END AS auto_submitted_flag,
         COALESCE(list_unsubscribe_present,0) AS list_unsubscribe,
         CASE WHEN lower(from_addr) GLOB '*noreply*' OR lower(from_addr) GLOB '*no-reply*' OR lower(from_addr) GLOB '*no.reply*'
                OR lower(from_addr) GLOB '*no_reply*' OR lower(from_addr) GLOB '*donotreply*' OR lower(from_addr) GLOB '*do-not-reply*'
                OR lower(from_addr) GLOB 'notification*' OR lower(from_addr) GLOB 'alert*' OR lower(from_addr) GLOB 'auto*'
                OR lower(from_addr) GLOB 'automated*' OR lower(from_addr) GLOB 'billpay*' THEN 1 ELSE 0 END AS noreply_pattern
    FROM messages;

CREATE VIEW s_subject_dates AS
  SELECT id AS message_id,
         CASE WHEN lower(subject) GLOB '*[0-9]/[0-9]*'
                OR lower(subject) GLOB '*20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]*'
                OR lower(subject) GLOB '*jan[a-z]* [0-9]*' OR lower(subject) GLOB '*feb[a-z]* [0-9]*'
                OR lower(subject) GLOB '*mar[a-z]* [0-9]*' OR lower(subject) GLOB '*apr[a-z]* [0-9]*'
                OR lower(subject) GLOB '*may [0-9]*' OR lower(subject) GLOB '*jun[a-z]* [0-9]*'
                OR lower(subject) GLOB '*jul[a-z]* [0-9]*' OR lower(subject) GLOB '*aug[a-z]* [0-9]*'
                OR lower(subject) GLOB '*sep[a-z]* [0-9]*' OR lower(subject) GLOB '*oct[a-z]* [0-9]*'
                OR lower(subject) GLOB '*nov[a-z]* [0-9]*' OR lower(subject) GLOB '*dec[a-z]* [0-9]*'
                OR lower(subject) GLOB '*tomorrow*' OR lower(subject) GLOB '*today*'
              THEN 1 ELSE 0 END AS subject_has_date
    FROM messages;

CREATE VIEW s_msg_location AS
  SELECT m.id AS message_id,
    MAX(CASE WHEN j.value='INBOX' THEN 1 ELSE 0 END) AS in_inbox,
    MAX(CASE WHEN j.value='SPAM' THEN 1 ELSE 0 END) AS in_spam,
    MAX(CASE WHEN j.value='TRASH' THEN 1 ELSE 0 END) AS in_trash,
    MAX(CASE WHEN j.value='UNREAD' THEN 1 ELSE 0 END) AS is_unread,
    MAX(CASE WHEN j.value='STARRED' THEN 1 ELSE 0 END) AS is_starred,
    MAX(CASE WHEN j.value='CATEGORY_PROMOTIONS' THEN 1 ELSE 0 END) AS cat_promotions,
    MAX(CASE WHEN l.type='user' AND l.name LIKE '%Archive' THEN 1 ELSE 0 END) AS in_desk_archive,
    group_concat(CASE WHEN l.type='user' THEN l.name END, '|') AS user_labels
  FROM messages m
  LEFT JOIN json_each(CASE WHEN json_valid(m.label_ids) THEN m.label_ids ELSE '[]' END) j
  LEFT JOIN labels l ON l.id = j.value
  GROUP BY m.id;

CREATE VIEW s_filter_hits AS
  SELECT f.id AS filter_id,
         lower(json_extract(f.criteria_json,'$.from')) AS from_criterion,
         j.value AS add_label_id, l.name AS add_label_name
    FROM filters f
    LEFT JOIN json_each(CASE WHEN json_valid(f.action_json) AND json_type(f.action_json,'$.addLabelIds')='array'
                             THEN json_extract(f.action_json,'$.addLabelIds') ELSE '[]' END) j
    LEFT JOIN labels l ON l.id = j.value
   WHERE json_extract(f.criteria_json,'$.from') IS NOT NULL;

CREATE VIEW s_contact_addr AS
  SELECT lower(e.value) AS address, c.groups_json AS groups_json
    FROM contacts c, json_each(CASE WHEN json_valid(c.emails_json) THEN c.emails_json ELSE '[]' END) e;

CREATE VIEW s_cal_addr AS
  SELECT lower(a.value) AS address, COUNT(*) AS events
    FROM calendar_events ce, json_each(CASE WHEN json_valid(ce.attendee_emails) THEN ce.attendee_emails ELSE '[]' END) a
   GROUP BY lower(a.value);

CREATE TABLE canon_facts(
  id INTEGER PRIMARY KEY,
  category TEXT NOT NULL,              -- representation | agency | person | family | tenant | accountant | union | bank | property | production | vendor | address | entity
  entity TEXT NOT NULL,                -- the name or address as the canon writes it
  detail_guess TEXT, detail_override TEXT,   -- one plain line: what the canon says (verbatim snippet)
  domain_guess TEXT, domain_override TEXT,   -- a domain (kg_vocab v:domain) | none
  hint TEXT,                           -- e.g. 'inactive?' when the canon line says parted / inactive / ended
  status TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN ('proposed','approved','retired')),
  source TEXT, answer_id INTEGER, valid_from TEXT, valid_until TEXT,
  retired_at TEXT, retired_reason TEXT,
  UNIQUE(category, entity));

CREATE TABLE corrections(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('wrong_domain','wrong_need','wrong_shelf_life','missing_exception','wrong_person_or_circle')),
  target TEXT NOT NULL, old TEXT, new TEXT, source TEXT NOT NULL, answer_id INTEGER);

CREATE TABLE relationship_scores(
  address TEXT PRIMARY KEY,
  score_guess REAL, score_override REAL,
  basis TEXT, source TEXT);

CREATE TABLE chapters(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, starts_on TEXT NOT NULL, scope TEXT, made_at TEXT NOT NULL);

CREATE TABLE chapter_closures(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chapter_id INTEGER NOT NULL, table_name TEXT NOT NULL, row_id INTEGER NOT NULL, prev_valid_until TEXT);

CREATE TABLE entity_resets(
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, entity TEXT NOT NULL, table_name TEXT NOT NULL, row_id INTEGER NOT NULL,
  before_text TEXT, reason TEXT);

CREATE VIEW v_rules_v1 AS SELECT id, match_kind, match_value, subject_glob, kind_label,
        COALESCE(need_override, need_guess) AS need, COALESCE(domain_override, domain_guess) AS domain,
        COALESCE(folder_override, folder_guess) AS folder,
        COALESCE(shelf_days_override, shelf_days_guess) AS shelf_days, COALESCE(shelf_anchor_override, shelf_anchor_guess) AS shelf_anchor,
        status, valid_from, valid_until FROM rules;

CREATE VIEW v_canon_facts AS SELECT id, category, entity, COALESCE(detail_override, detail_guess) AS detail,
        COALESCE(domain_override, domain_guess) AS domain, hint, status, source FROM canon_facts;

CREATE VIEW v_relationship_scores AS SELECT address, COALESCE(score_override, score_guess) AS score, basis FROM relationship_scores;

CREATE TABLE events(at TEXT, kind TEXT, detail TEXT);
