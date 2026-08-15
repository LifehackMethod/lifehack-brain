---
element: compute-mechanically-gate
maturity_label: DORMANT
record_type: organism-element
altitude: index-line
---

Two hooks (`system/hooks/inject_compute_mechanically.sh` + `numbers_flag.sh`) that enforce the no-LLM-arithmetic rule introduced after a major finance error on 2026-06-26. Finance desks (Deryl/Clair-billing) auto-arm on session start; any session can arm manually via `/calculate`; a tight regex backstop catches obvious math tokens everywhere else. Both hooks are read-only inject observers — degrade-safe, never block. The `/calculate` skill is the interactive arm/disarm surface (see calculate element).

### INTENT: mechanically re-inject the no-LLM-arithmetic rule every turn so a session can't silently drift back to head-math after the 2026-06-26 finance error that motivated it.

> INDEX-LINE ONLY — dormant per the 2026-07-24 usage cross-ref; expand to a full entry only if it proves load-bearing.

generated_from: system/hooks/inject_compute_mechanically.sh, system/hooks/numbers_flag.sh
