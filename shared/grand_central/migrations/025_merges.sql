-- 025_merges.sql: Phase 3 step 3.6. user_version 24 -> 25. Vision 3.7.4 rule 2; plan 3.6.
-- A merge of two people or two organizations happens only on his word (a kg_answers row, fact_key 'merge_into'; an undo is
-- 'unmerge'). It re-points the retiring thing's current facts and links onto the survivor, keeps every old row as history, and sets
-- merged_into + retired_at (migration 021) on the retiring thing. Nothing is deleted; both keys stay in thing_keys.
-- The one thing added: every fact and link row a merge touched (the old row it retired, the new row it wrote) carries the id of the
-- answer that caused it, so an un-merge can find exactly those rows and put them back from the record.
ALTER TABLE kg_facts ADD COLUMN merge_answer_id INTEGER REFERENCES kg_answers(id);
ALTER TABLE kg_links ADD COLUMN merge_answer_id INTEGER REFERENCES kg_answers(id);
CREATE INDEX kg_facts_merge ON kg_facts(merge_answer_id) WHERE merge_answer_id IS NOT NULL;
CREATE INDEX kg_links_merge ON kg_links(merge_answer_id) WHERE merge_answer_id IS NOT NULL;
