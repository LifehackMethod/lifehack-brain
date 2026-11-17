-- 007_shape_review1.sql: World Model Trial review point 1 (after Step 1). user_version 6 -> 7.
-- The 2026-11-13 audit, split into 294 single decisions, showed kinds of answer the 005 shape had no home for.
-- Fixed here, before Step 2 pours his answers in:
--   * words_kind: not all "words" are his literal speech (old grade rounds are summaries; some are one bundled
--     approval covering many items; some answer by item number). Recorded, so nothing passes a summary off as a quote.
--   * condition: "ride receipts yes, vouchers no" is one subject with a condition (a subject word), not two subjects.
--     A fact with a condition replaces only the fact with the same condition.
--   * topic: a named theme of how he works ("junk handling", "Trash", "the stale middle"), many per world.
--   * account: one of his own mail accounts (route student mail by which account it came to).
--   * new fact keys for process rules, definitions, keyword lists, never-catch safety lists, review dates, shelf life
--     in his words; exception and tier widened to the subjects he actually gave them for.
ALTER TABLE kg_answers ADD COLUMN words_kind TEXT NOT NULL DEFAULT 'verbatim';
ALTER TABLE kg_answers ADD COLUMN condition TEXT;
ALTER TABLE kg_facts ADD COLUMN condition TEXT;

INSERT INTO kg_vocab(list, value, note) VALUES
 ('words_kind','verbatim','his exact typed or dictated words'),
 ('words_kind','summary','a window''s summary of what he said (e.g. old grade rounds in answer_log)'),
 ('words_kind','bundle_approval','one approval of a list the window wrote; the item is the window''s, the yes is his'),
 ('words_kind','by_number','he answered by item number; the subject was resolved from the list shown'),
 ('thing_kind','topic','a named theme of how he works'),
 ('thing_kind','account','one of his own mail accounts');

UPDATE kg_fact_keys SET subject_kinds='rule,address,domain,company,person,label,topic' WHERE key='exception';
UPDATE kg_fact_keys SET subject_kinds='person,address,domain,company,topic' WHERE key='tier';
UPDATE kg_fact_keys SET subject_kinds='address,domain,company,person,label,topic,project,desk,trip,place' WHERE key='importance';
UPDATE kg_fact_keys SET subject_kinds='address,domain,company,person,label,topic,rule' WHERE key='inbox';
UPDATE kg_fact_keys SET subject_kinds='address,domain,company,person,rule,label,topic' WHERE key='destination';
UPDATE kg_fact_keys SET subject_kinds='address,domain,company,person,rule,topic,project,trip' WHERE key='label';
UPDATE kg_fact_keys SET subject_kinds='address,domain,rule,company,person,label,topic' WHERE key='need';

INSERT INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('shelf_life',NULL,'*','shelf life in his words ("important until the event passes")'),
 ('process_rule',NULL,'*','how the system must behave, in his words'),
 ('definition',NULL,'topic,label,desk','what one of his words means'),
 ('filter_keywords',NULL,'topic,label,desk,domain,address','a keyword list he set, comma-separated'),
 ('never_catch',NULL,'label,topic,rule','a safety list: senders/domains this filter or label must never catch, comma-separated'),
 ('routing_signal',NULL,'topic,account,label,desk','what decides where mail goes'),
 ('review_by',NULL,'*','a date (YYYY-MM-DD) to look at this again'),
 ('label_role',NULL,'label','what the label is for, in his words');
