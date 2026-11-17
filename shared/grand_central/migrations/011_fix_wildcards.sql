-- 011_fix_wildcards.sql: fix forward. 010 appended ',item' to subject_kinds, which turned note's wildcard '*' into
-- the literal list '*,item' (so 'note' was refused on addresses). Restore any '*,…' to '*'. user_version 10 -> 11.
UPDATE kg_fact_keys SET subject_kinds='*' WHERE subject_kinds LIKE '*,%';
