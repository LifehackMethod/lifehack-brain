# History log for connecting-an-outside-service-sop.md

Text cut or moved out of the SOP, copied verbatim first. Append-only.

- 2026-11-16: landed in round four, canon-files checked, on Enver's 'land it'.

## 2026-11-16 - reason: landing-commit citation check; a per-person file named without its directory path, since it is never in the repo
Line 67 (before): "A key kept in `.claude/settings.local.json` (each person's own file, not shipped) is an exception to the line above: the file sits inside the repo folder, chosen deliberately for this release (`.gitignore:34-44`), and only `.gitignore` keeps it out of commits (passive conformance friction: no message, it simply is not staged)." ⛔ the path quoted here is each person's own file, not shipped.
Line 164 (before): "- `.gitignore` — keeps `.claude/settings.local.json` and `local.settings.json` (each person's own files, not shipped) out of commits (passive; no message)." ⛔ the paths quoted here are each person's own files, not shipped.
