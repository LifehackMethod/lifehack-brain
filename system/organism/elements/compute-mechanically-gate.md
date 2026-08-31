---
element: compute-mechanically-gate
maturity_label: ~~DORMANT~~ ⚠ CORRECTED 2026-08-25: LIVE (see body correction below)
record_type: organism-element
altitude: index-line
---

~~Two hooks~~ **One hook** (`system/hooks/inject_compute_mechanically.sh`) plus one non-hook flag-CLI (`numbers_flag.sh`) that enforce the no-LLM-arithmetic rule introduced after a major finance error on 2026-06-26. Finance desks (Deryl/Clair-billing) auto-arm on session start; any session can arm manually via `/calculate`; a tight regex backstop catches obvious math tokens everywhere else. ~~Both hooks are read-only inject observers — degrade-safe, never block.~~
> **CORRECTED: `numbers_flag.sh` is not itself a hook.** Fed with no subcommand argument, it
> printed `usage: numbers_flag.sh arm | clear | status` and exited 2, not 0 — it does not degrade
> the way a real PreToolUse/UserPromptSubmit hook would. Its own header confirms it is a
> flag-arm/clear/status CLI invoked by the `/calculate` skill, not a per-turn inject observer;
> this repo's own `.claude/settings.json` registers `inject_compute_mechanically.sh` as a hook —
> `numbers_flag.sh` never appears there. It is the switch this gate reads, not a second injector.
The `/calculate` skill is the interactive arm/disarm surface (see calculate element).

### INTENT: mechanically re-inject the no-LLM-arithmetic rule every turn so a session can't silently drift back to head-math after the 2026-06-26 finance error that motivated it.

> ~~INDEX-LINE ONLY — dormant per the 2026-07-24 usage cross-ref; expand to a full entry only if it proves load-bearing.~~
> ⚠ CORRECTED 2026-08-25: NOT dormant. `system/hooks/inject_compute_mechanically.sh` is registered on `UserPromptSubmit` and fires on EVERY prompt of every session, not just finance desks: confirmed this session by piping a synthetic payload (`{"prompt":"can we afford $500?","cwd":"/tmp"}`) to the script on stdin, which printed the live "[NUMBERS CHECK (hard math token) — added by the system, not typed by the person.]" injection text and exited 0, and by grepping the live `~/.claude/settings.json:95` for its registration. The 2026-07-24 usage cross-ref this DORMANT label rested on is stale; the index-only treatment should be lifted to a full entry, not left index-only. ⛔ `system/hooks/registrations.json` and `system/organism/generated/capability-census.md` — both private-only tracking/generated artifacts that do not ship here; the two corroborating cites this correction originally rested on were dropped rather than ported.

generated_from: system/hooks/inject_compute_mechanically.sh, system/hooks/numbers_flag.sh
