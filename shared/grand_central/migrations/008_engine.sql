-- 008_engine.sql: World Model Trial Step 3, the engine's words. user_version 7 -> 8.
-- The engine (engine/) is a blackboard pipeline: gather -> score -> stitch -> rank -> gaps. It talks only through the
-- memory (kg_*). These are the fact keys and the value list it writes with. The window settings (how many days back,
-- ahead...) are seeded by code as 'setting' facts on topic:engine window, so a later answer from him can change them.
-- member_item, setting and trigger may hold many values at once: that is set in store_graph.MULTI (code), not here.
INSERT INTO kg_vocab(list, value, note) VALUES
 ('v:whose_move','him','the next move is his'),
 ('v:whose_move','them','the next move is theirs'),
 ('v:whose_move','nobody','no one has to move (e.g. only a calendar event)'),
 ('v:whose_move','undecided',NULL);

INSERT INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('setting',NULL,'topic','an engine setting, free text "name=value"'),
 ('member_item',NULL,'episode','an item in this episode, free text "item:<id>"'),
 ('date_window',NULL,'episode,trip,project','free text "YYYY-MM-DD..YYYY-MM-DD"'),
 ('whose_move','v:whose_move','episode','who has to move next'),
 ('trigger',NULL,'episode','why the engine opened this episode');
