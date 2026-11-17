-- 006_vocab_fix.sql: user_version 5 -> 6. An owner's own domain word came in here; it now lives in that owner's
-- setup migrations. Nothing for the plugin to do at this step (the number stays so the series stays contiguous).
SELECT 1;  -- no-op: keeps the plugin series contiguous
