# Migrations

- Files are named `NNN_name.sql` (three digits, strictly increasing, no gaps). `001_baseline.sql` is the live schema as of 2026-11-12.
- NEVER edit a migration that has been applied anywhere. Fix forward with a new file.
- Each migration N brings `PRAGMA user_version` from N-1 to N. The runner (`migrate.py`) sets it; do not put PRAGMA user_version in the SQL.
- Plain SQL statements only (no BEGIN/COMMIT); the runner wraps each file in one transaction.
- `python3 migrate.py` is a dry run. `--apply --backup-ok <file>` acts, and the backup file must exist and be under 10 minutes old.

- 2026-11-16, ruled exception (Grand Central plan, phase 4M): migrations 001, 005, 006, 010 and 014 were edited after being applied, against the rule above. The edits are comment-only, plus the coordinator-ruled split (the owner approved splitting 006 and 013); the schema is identical once comments are stripped. This is a one-time exception, not a precedent: fix forward from here.
