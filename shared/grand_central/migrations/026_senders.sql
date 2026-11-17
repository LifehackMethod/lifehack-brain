-- 026_senders.sql: Phase 3 step "senders". user_version 25 -> 26. Plan Phase 3 "Every sender is tied to an organization; bots are
-- their own kind" (his ruling of 2026-11-16 via the coordinator); Vision 3.7.
-- What code may now write about a sender ADDRESS (the building is senders.py, not this file):
--   sender_kind  person | bot | unknown     person = a real two-way human who matters (the 3.2 rule); bot = a company's automated
--                                            system, shown by its own headers or name; unknown = the question mark.
--   bot_need     junk | fyi | needs_him | unsure   only on a bot: whether it needs him. junk is written ONLY from his own ruling.
-- The tie of an address to its organization is the existing link `belongs_to` (address -> organization), made by domain.
-- Code writes only what it can know: sender_kind by code must be 'sure'; an AI guess may write neither fact; bot_need junk needs
-- his word: the fact is his own (who=owner), or code carrying his ruling over (source_kind=answer, source_ref 'ruling:<fact id>').
INSERT OR IGNORE INTO kg_vocab(list, value, note) VALUES
 ('v:sender_kind', 'person', 'a real two-way human who matters'),
 ('v:sender_kind', 'bot', 'a company''s automated system (not a person)'),
 ('v:sender_kind', 'undecided', 'house rule: every value list has this word; senders use unknown for the question mark'),
 ('v:sender_kind', 'unknown', 'the question mark: not sure it is a person, not sure it is a bot'),
 ('v:bot_need', 'junk', 'goes away (only ever from his own ruling)'),
 ('v:bot_need', 'fyi', 'filed quietly'),
 ('v:bot_need', 'needs_him', 'reaches him: a booking, a failed payment, a flight change'),
 ('v:bot_need', 'undecided', 'house rule: every value list has this word; a bot with no known need is unsure'),
 ('v:bot_need', 'unsure', 'a bot whose need is not known: it stays a question');
INSERT OR IGNORE INTO kg_fact_keys(key, value_list, subject_kinds, note) VALUES
 ('sender_kind', 'v:sender_kind', 'address', 'person, bot or unknown (question mark); code records only what it is sure of'),
 ('bot_need', 'v:bot_need', 'address', 'for a bot: junk, fyi, needs_him or unsure; junk only from his ruling');

CREATE TRIGGER kg_facts_sender_kind_by_code BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'sender_kind' AND NEW.who <> 'owner' AND (NEW.who <> 'code' OR NEW.certainty <> 'sure')
BEGIN SELECT RAISE(ABORT, 'sender_kind: code records only what it is sure of (who=code, certainty=sure); a guess stays a question mark'); END;
CREATE TRIGGER kg_facts_bot_need_by_code BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'bot_need' AND NEW.who NOT IN ('owner', 'code')
BEGIN SELECT RAISE(ABORT, 'bot_need: only code (from headers, patterns or his rulings) or his word may write it, never an AI guess'); END;
CREATE TRIGGER kg_facts_bot_junk_is_his BEFORE INSERT ON kg_facts
WHEN NEW.fact_key = 'bot_need' AND NEW.value = 'junk' AND NEW.who <> 'owner'
 AND NOT (NEW.who = 'code' AND NEW.source_kind = 'answer' AND NEW.source_ref LIKE 'ruling:%')
BEGIN SELECT RAISE(ABORT, 'bot_need junk is only ever his ruling: code never assumes junk'); END;
