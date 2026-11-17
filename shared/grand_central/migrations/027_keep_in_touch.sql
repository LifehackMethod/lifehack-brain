-- 027_keep_in_touch.sql: Phase 3 tie-up (e). user_version 26 -> 27. Step 3.7 `gc due` reads the fact keep_in_touch_days, but the word was
-- never in the allowed list, so nobody could have one. Added here: a person fact, a whole number of days, HIS WORD ONLY (code and AI
-- guesses are refused, like levels_above_me). The onboarding sheet may ask it for his top people; nothing guesses it.
INSERT OR IGNORE INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('keep_in_touch_days', NULL, 'person', 'how many days at most he wants to go without two-way contact with this person (a whole number of days); his word only');

CREATE TRIGGER kg_facts_keep_in_touch_is_his BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'keep_in_touch_days' AND NEW.who <> 'owner'
BEGIN SELECT RAISE(ABORT, 'keep_in_touch_days is his word: who=owner and an answer'); END;
CREATE TRIGGER kg_facts_keep_in_touch_whole_number BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'keep_in_touch_days' AND (NEW.value = '' OR NEW.value GLOB '*[^0-9]*' OR NEW.value = '0' OR length(NEW.value) > 4)
BEGIN SELECT RAISE(ABORT, 'keep_in_touch_days is a whole number of days (1 to 9999)'); END;
CREATE TRIGGER kg_facts_keep_in_touch_is_his_update BEFORE UPDATE OF fact_key, value, who, answer_id ON kg_facts
WHEN NEW.fact_key = 'keep_in_touch_days' AND NEW.who <> 'owner'
BEGIN SELECT RAISE(ABORT, 'keep_in_touch_days is his word: who=owner and an answer'); END;
