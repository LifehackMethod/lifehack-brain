# History log for skill-builder.md

Text cut or moved out of the SOP, copied verbatim first. Append-only.

## 2026-11-24 - reason: canon update round 2, 2026-11-24: citation-lint fix; path and line numbers separated, no change of meaning

~~~~
1. **Optional steps in the shared runner** (formerly item 12): his word, "if number four is pretty easy to fix let's just do that". BUILT on the plugin's V2 branch: commit e9632fbb (2026-11-23), "a card step marked optional passes as skipped by the person, only on the person's /next turn; the AI can never skip" (`system/parts/stage_runner.py:339-343, 682-712`; read from the local copy of the plugin on 2026-11-24). CLOSED (coordinator, 2026-11-24): read back on GitHub, origin/V2 carries e9632fbb (2026-11-24); the build re-reads it at its start. So the card marks steps 3 and 4 `optional`; a skip is the person's own `/next`; the §4 fallback (a one-line skip screen for a runner without the field) is NOT built. ⛔ (note 2026-11-24: verbatim copy; the file is `system/parts/stage_runner.py`, and /next is a hook command, not a skill folder.)
~~~~
