---
element: ingest-run-lib
maturity_label: DORMANT
record_type: organism-element
altitude: index-line
---

Shared bash scaffold (`system/tools/ingest-run.lib.sh`) that desk-level cron ingest runners source instead of duplicating ~60 lines of platform plumbing — headless auth, single-instance lock, cheap new-mail gate, and watchdog. Adopted Phase 4B (2026-06-12) after Emily's verified patterns were proven; each desk runner sources the lib, sets its own vars, and supplies only the policy prompt (what to flag/score stays in the desk's SKILL.md). ~~Currently wired into at least the Deryl and Emily ingest runners~~; dormant in the sense that it has no dedicated organism entry and is invoked silently by cron, not interactively.
> **CORRECTED — the Deryl/Emily examples are not verifiable from this repo, and what IS
> verifiable points at different current usage.** A repo-wide grep for actual `source` invocations
> (not comments/mentions) of `ingest-run.lib.sh` finds only TWO callers: `system/tools/sentinel-health-run.sh`
> and `system/tools/system-health-run.sh` — both system/security health-check runners, not desk-level
> ingest cron jobs. This repo has no `desks/` directory at all (desk material lives outside the
> repo, in the person's own AI Brain), so whether Deryl/Emily runners source this lib there cannot
> be checked from here. The lib's stated PURPOSE (shared plumbing for headless runners) is accurate;
> its flagship named examples are unconfirmed, and the only usage visible in this repo today is by
> two health-monitoring scripts, not desk ingest.

### INTENT: let every desk's cron ingest runner share one proven platform scaffold (auth, lock, new-mail gate, watchdog) instead of re-deriving and re-breaking the same ~60 lines per desk.

> INDEX-LINE ONLY — dormant per the 2026-07-24 usage cross-ref; expand to a full entry only if it proves load-bearing.

generated_from: system/tools/ingest-run.lib.sh
