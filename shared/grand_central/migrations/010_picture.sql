-- 010_picture.sql: STEP 6 (fix the picture). user_version 9 -> 10. Allowed words only; no tables.
-- items become things (key item:<items.id>) so near items can be linked to his projects; reps and their assistants
-- (desk canon); company <-> sender domain; the three-layer picture's facts; plain-word display names.
INSERT INTO kg_vocab(list, value, note) VALUES
 ('thing_kind','item','one source item (email/event/task); key item:<items.id>'),
 ('link_kind','assistant_of','person -> the person they assist (desk canon)'),
 ('link_kind','part_of','item/episode -> the project it belongs to'),
 ('link_kind','domain_of','domain -> the company that sends from it');
UPDATE kg_fact_keys SET subject_kinds='person,company,address,domain,topic,project' WHERE key='relationship';
UPDATE kg_fact_keys SET subject_kinds=subject_kinds||',item' WHERE key IN ('note','importance');
INSERT INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('storyline',NULL,'project','layer 1: one line on what this project is in his life, months-long'),
 ('month_state',NULL,'project','layer 2: what this month looks like for the project ("work is heating up")'),
 ('near_line',NULL,'item,project,episode','layer 3: what this near item MEANS for him, one line'),
 ('cites',NULL,'project,item,episode','item ids a synthesis line rests on, comma-separated (a line with none is dropped)'),
 ('display_name',NULL,'*','the plain words to show him instead of an internal name ("<Desk>" -> "plain words")'),
 ('role',NULL,'person','their job in his life, from desk canon ("lead agent", "manager", "assistant")');
