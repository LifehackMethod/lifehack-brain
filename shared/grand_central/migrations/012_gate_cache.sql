-- 012_gate_cache.sql: skip re-gating a calendar/task item whose gated text is unchanged since its
-- last CLEAN gate verdict (the ~2,500-item daily re-pull paid the full Sentinel lane for text the
-- judge had already cleared). One row per item: sha256 of exactly the text the AI judge inspects
-- (pull._gate_text: FIELD-mode sanitized fields, empties dropped, fixed field order) plus the
-- verdict the gate returned last time. ONLY clean verdicts are stored — a flagged or UNJUDGED item
-- deletes its row and is re-gated on the next pull, every time. Never the item's text.
CREATE TABLE gate_cache(
  item_id TEXT PRIMARY KEY,            -- 'calendar_event:<eid>' / 'task:<tid>' (the staged item id)
  kind TEXT NOT NULL,                  -- calendar_event | task
  text_hash TEXT NOT NULL,             -- sha256 of pull._gate_text(fields) at last clean verdict
  verdict TEXT NOT NULL,               -- always 'CLEAN' today; column keeps the door open
  at TEXT NOT NULL);                   -- when the verdict was recorded (UTC ISO)
