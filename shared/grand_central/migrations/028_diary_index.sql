-- 028_diary_index.sql: Phase 4 step 4.4. user_version 27 -> 28. The diary index: one row per diary entry FILE, so a person's page
-- (step 4.7) can list the entries that mention them. DERIVED from the entry files (they stay the truth and are never rewritten):
-- store_diary.refresh_index re-reads them, so a rebuild from files reproduces it and `gc rebuild` leaves it out of its comparison.
-- keys_mentioned and staged_ids are JSON lists, taken ONLY from what the entry's own front matter carries (never guessed from prose).
CREATE TABLE diary_index (
  id            INTEGER PRIMARY KEY,
  diary         TEXT NOT NULL,            -- the main diary's name, '<Desk>-Diary'
  date          TEXT NOT NULL CHECK (date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  keys_mentioned TEXT NOT NULL DEFAULT '[]',
  staged_ids    TEXT NOT NULL DEFAULT '[]',
  entry_path    TEXT NOT NULL,            -- relative to the notes root
  confidence    TEXT CHECK (confidence IS NULL OR confidence IN ('low','medium','high')),
  indexed_at    TEXT NOT NULL,
  UNIQUE (diary, entry_path)
);
CREATE INDEX diary_index_date ON diary_index(diary, date);
