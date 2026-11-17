-- 029_first_run_seed.sql: step 4M.7. user_version 28 -> 29. No tables; first-run rows only.
-- A brand-new database gets the one-time rows the model rebuild (store_graph.rebuild_model: copy_legacy's world thing,
-- common.seed_settings) always writes, so `gc check` on a database that has never run compares like with like. Until now
-- only the old pipeline's first run wrote them. The values are common.DEFAULT_SETTINGS, written as seed_settings writes
-- them (who=code, sure, source code, ref plan:STEP3).
-- Guarded: a database that already has a row keeps it (INSERT OR IGNORE on the unique key; a setting is written only when
-- no current fact for that setting name exists), so on an existing database this migration changes nothing.

INSERT OR IGNORE INTO kg_things(kind, key, name, legacy_ref, created_by, created_at)
  VALUES ('world', 'world:world', 'world', NULL, 'code', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));
INSERT OR IGNORE INTO kg_things(kind, key, name, legacy_ref, created_by, created_at)
  VALUES ('topic', 'topic:engine window', 'engine window', NULL, 'code', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));

INSERT INTO kg_facts(thing_id, fact_key, value, who, certainty, source_kind, source_ref, answer_id, true_from, true_until,
                     replaced_by, created_at, condition)
  SELECT t.id, 'setting', s.name || '=' || s.val, 'code', 'sure', 'code', 'plan:STEP3', NULL, NULL, NULL, NULL,
         strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), NULL
    FROM kg_things t,
         (SELECT 1 AS ord, 'calendar_back_days' AS name, '14' AS val UNION ALL SELECT 2, 'calendar_ahead_days', '62'
          UNION ALL SELECT 3, 'calendar_focus_days', '14' UNION ALL SELECT 4, 'tasks_done_days', '14'
          UNION ALL SELECT 5, 'email_recent_days', '30' UNION ALL SELECT 6, 'email_inbox_any_age', 'yes') s
   WHERE t.key = 'topic:engine window'
     AND NOT EXISTS (SELECT 1 FROM kg_facts f WHERE f.thing_id = t.id AND f.fact_key = 'setting' AND f.replaced_by IS NULL
                     AND (f.value = s.name OR f.value LIKE s.name || '=%'))
   ORDER BY s.ord;
