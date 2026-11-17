-- 019_links_current_unique.sql: Phase 2 step 2.3 (5 of 5). user_version 18 -> 19. Vision 3.7.3, delta 7.27.
-- One current line per pair: a relationship of a given kind between two things has at most one row that is not superseded.
-- (0 duplicates on 2026-11-16, so no clean-up is needed to add it. A superseded row keeps its place: the index covers current rows only.)
CREATE UNIQUE INDEX kg_links_current_uq ON kg_links(from_id, kind, to_id) WHERE replaced_by IS NULL;
