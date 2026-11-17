-- 004_quarantine_detail.sql: keep the judge's one-line reason for every quarantined item. Brings user_version 3 -> 4.
-- Nullable: old rows stay NULL. Holds the phrase layer's flag label and/or the AI reader's short reason.
-- Never the item's text (the text goes to a local untrusted-zone file, never to the DB).
ALTER TABLE quarantine ADD COLUMN detail TEXT;
