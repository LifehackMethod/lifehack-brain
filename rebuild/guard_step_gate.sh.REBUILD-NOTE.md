# REBUILD NOTE — guard_step_gate.sh

- **Moved:** ⛔ 2026-10-31, from `system/hooks/guard_step_gate.sh` (skill-system cleanup, approved by Enver 2026-10-31).
- **Was never registered** in `hooks/hooks.json` (checked 2026-10-31).
- **Its partner `step_receipt.sh` was NOT moved:** `/checkin` (`phases/3-propose.md`) and `/save` (`phases/session-close.md`) call it live.
- **Its test `system/hooks/tests/test_guard_step_gate.sh` was left in place** and now points at a missing file.
- **Ledger:** `<notes>/state/projects/skill-system/records/2026-10-31-cleanup-ledger.md`

## What to salvage

Salvage the gate logic as a runner-side check, not a hook.
