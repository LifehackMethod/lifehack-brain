-- 020_freeze_old_tables.sql: Phase 2 step 2.6. user_version 19 -> 20. Vision 3.7.4, plan 2.6.
-- The old (pre-graph) world-model tables become read-only history: a trigger REFUSES insert, update and delete on each.
-- Reads still work and nothing is deleted. NOT frozen (still written by live code): queue (the proposals table: daily.py's
-- apply-label and flag-urgent proposals, and every question), the kg_* model, thing_keys, the intake mirrors and item layer,
-- events, runs, errors, quarantine, filters, contacts, labels. Frozen as the coordinator ruled at stop 2b; engine/screen.py and
-- engine/synthesize.py stay as code but nothing live runs them.
-- To unfreeze one table (e.g. for a replay), DROP its three triggers frozen_<table>_no_insert/_no_update/_no_delete.
CREATE TRIGGER frozen_answer_log_no_insert BEFORE INSERT ON answer_log
BEGIN SELECT RAISE(ABORT, 'answer_log is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_answer_log_no_update BEFORE UPDATE ON answer_log
BEGIN SELECT RAISE(ABORT, 'answer_log is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_answer_log_no_delete BEFORE DELETE ON answer_log
BEGIN SELECT RAISE(ABORT, 'answer_log is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_people_no_insert BEFORE INSERT ON people
BEGIN SELECT RAISE(ABORT, 'people is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_people_no_update BEFORE UPDATE ON people
BEGIN SELECT RAISE(ABORT, 'people is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_people_no_delete BEFORE DELETE ON people
BEGIN SELECT RAISE(ABORT, 'people is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_addresses_no_insert BEFORE INSERT ON addresses
BEGIN SELECT RAISE(ABORT, 'addresses is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_addresses_no_update BEFORE UPDATE ON addresses
BEGIN SELECT RAISE(ABORT, 'addresses is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_addresses_no_delete BEFORE DELETE ON addresses
BEGIN SELECT RAISE(ABORT, 'addresses is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_circles_no_insert BEFORE INSERT ON circles
BEGIN SELECT RAISE(ABORT, 'circles is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_circles_no_update BEFORE UPDATE ON circles
BEGIN SELECT RAISE(ABORT, 'circles is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_circles_no_delete BEFORE DELETE ON circles
BEGIN SELECT RAISE(ABORT, 'circles is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_circle_members_no_insert BEFORE INSERT ON circle_members
BEGIN SELECT RAISE(ABORT, 'circle_members is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_circle_members_no_update BEFORE UPDATE ON circle_members
BEGIN SELECT RAISE(ABORT, 'circle_members is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_circle_members_no_delete BEFORE DELETE ON circle_members
BEGIN SELECT RAISE(ABORT, 'circle_members is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_rules_no_insert BEFORE INSERT ON rules
BEGIN SELECT RAISE(ABORT, 'rules is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_rules_no_update BEFORE UPDATE ON rules
BEGIN SELECT RAISE(ABORT, 'rules is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_rules_no_delete BEFORE DELETE ON rules
BEGIN SELECT RAISE(ABORT, 'rules is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_rule_exceptions_no_insert BEFORE INSERT ON rule_exceptions
BEGIN SELECT RAISE(ABORT, 'rule_exceptions is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_rule_exceptions_no_update BEFORE UPDATE ON rule_exceptions
BEGIN SELECT RAISE(ABORT, 'rule_exceptions is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_rule_exceptions_no_delete BEFORE DELETE ON rule_exceptions
BEGIN SELECT RAISE(ABORT, 'rule_exceptions is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_facts_no_insert BEFORE INSERT ON facts
BEGIN SELECT RAISE(ABORT, 'facts is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_facts_no_update BEFORE UPDATE ON facts
BEGIN SELECT RAISE(ABORT, 'facts is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_facts_no_delete BEFORE DELETE ON facts
BEGIN SELECT RAISE(ABORT, 'facts is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_keywords_no_insert BEFORE INSERT ON keywords
BEGIN SELECT RAISE(ABORT, 'keywords is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_keywords_no_update BEFORE UPDATE ON keywords
BEGIN SELECT RAISE(ABORT, 'keywords is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_keywords_no_delete BEFORE DELETE ON keywords
BEGIN SELECT RAISE(ABORT, 'keywords is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_canon_facts_no_insert BEFORE INSERT ON canon_facts
BEGIN SELECT RAISE(ABORT, 'canon_facts is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_canon_facts_no_update BEFORE UPDATE ON canon_facts
BEGIN SELECT RAISE(ABORT, 'canon_facts is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_canon_facts_no_delete BEFORE DELETE ON canon_facts
BEGIN SELECT RAISE(ABORT, 'canon_facts is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_corrections_no_insert BEFORE INSERT ON corrections
BEGIN SELECT RAISE(ABORT, 'corrections is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_corrections_no_update BEFORE UPDATE ON corrections
BEGIN SELECT RAISE(ABORT, 'corrections is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_corrections_no_delete BEFORE DELETE ON corrections
BEGIN SELECT RAISE(ABORT, 'corrections is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_relationship_scores_no_insert BEFORE INSERT ON relationship_scores
BEGIN SELECT RAISE(ABORT, 'relationship_scores is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_relationship_scores_no_update BEFORE UPDATE ON relationship_scores
BEGIN SELECT RAISE(ABORT, 'relationship_scores is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_relationship_scores_no_delete BEFORE DELETE ON relationship_scores
BEGIN SELECT RAISE(ABORT, 'relationship_scores is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_chapters_no_insert BEFORE INSERT ON chapters
BEGIN SELECT RAISE(ABORT, 'chapters is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_chapters_no_update BEFORE UPDATE ON chapters
BEGIN SELECT RAISE(ABORT, 'chapters is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_chapters_no_delete BEFORE DELETE ON chapters
BEGIN SELECT RAISE(ABORT, 'chapters is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_chapter_closures_no_insert BEFORE INSERT ON chapter_closures
BEGIN SELECT RAISE(ABORT, 'chapter_closures is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_chapter_closures_no_update BEFORE UPDATE ON chapter_closures
BEGIN SELECT RAISE(ABORT, 'chapter_closures is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_chapter_closures_no_delete BEFORE DELETE ON chapter_closures
BEGIN SELECT RAISE(ABORT, 'chapter_closures is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_entity_resets_no_insert BEFORE INSERT ON entity_resets
BEGIN SELECT RAISE(ABORT, 'entity_resets is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_entity_resets_no_update BEFORE UPDATE ON entity_resets
BEGIN SELECT RAISE(ABORT, 'entity_resets is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_entity_resets_no_delete BEFORE DELETE ON entity_resets
BEGIN SELECT RAISE(ABORT, 'entity_resets is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_overrides_no_insert BEFORE INSERT ON overrides
BEGIN SELECT RAISE(ABORT, 'overrides is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_overrides_no_update BEFORE UPDATE ON overrides
BEGIN SELECT RAISE(ABORT, 'overrides is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_overrides_no_delete BEFORE DELETE ON overrides
BEGIN SELECT RAISE(ABORT, 'overrides is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_notes_no_insert BEFORE INSERT ON notes
BEGIN SELECT RAISE(ABORT, 'notes is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_notes_no_update BEFORE UPDATE ON notes
BEGIN SELECT RAISE(ABORT, 'notes is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_notes_no_delete BEFORE DELETE ON notes
BEGIN SELECT RAISE(ABORT, 'notes is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_projects_no_insert BEFORE INSERT ON projects
BEGIN SELECT RAISE(ABORT, 'projects is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_projects_no_update BEFORE UPDATE ON projects
BEGIN SELECT RAISE(ABORT, 'projects is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_projects_no_delete BEFORE DELETE ON projects
BEGIN SELECT RAISE(ABORT, 'projects is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_item_projects_no_insert BEFORE INSERT ON item_projects
BEGIN SELECT RAISE(ABORT, 'item_projects is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_item_projects_no_update BEFORE UPDATE ON item_projects
BEGIN SELECT RAISE(ABORT, 'item_projects is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_item_projects_no_delete BEFORE DELETE ON item_projects
BEGIN SELECT RAISE(ABORT, 'item_projects is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_desk_verdicts_no_insert BEFORE INSERT ON desk_verdicts
BEGIN SELECT RAISE(ABORT, 'desk_verdicts is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_desk_verdicts_no_update BEFORE UPDATE ON desk_verdicts
BEGIN SELECT RAISE(ABORT, 'desk_verdicts is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_desk_verdicts_no_delete BEFORE DELETE ON desk_verdicts
BEGIN SELECT RAISE(ABORT, 'desk_verdicts is frozen history (migration 020): DELETE refused'); END;
CREATE TRIGGER frozen_wm_meta_no_insert BEFORE INSERT ON wm_meta
BEGIN SELECT RAISE(ABORT, 'wm_meta is frozen history (migration 020): INSERT refused'); END;
CREATE TRIGGER frozen_wm_meta_no_update BEFORE UPDATE ON wm_meta
BEGIN SELECT RAISE(ABORT, 'wm_meta is frozen history (migration 020): UPDATE refused'); END;
CREATE TRIGGER frozen_wm_meta_no_delete BEFORE DELETE ON wm_meta
BEGIN SELECT RAISE(ABORT, 'wm_meta is frozen history (migration 020): DELETE refused'); END;
