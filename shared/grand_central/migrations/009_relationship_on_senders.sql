-- 009_relationship_on_senders.sql: allowed words, widened. user_version 8 -> 9.
-- Research round 1 (rehearsal, 2026-11-13) describes senders (an address or a domain: "Example Insurance = his insurance carrier"),
-- and 'relationship' only allowed person/company, so the front door refused it. Widen to the sender kinds and topic.
UPDATE kg_fact_keys SET subject_kinds='person,company,address,domain,topic' WHERE key='relationship';
