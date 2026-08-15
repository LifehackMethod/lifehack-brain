---
topic: [system-architecture]
title: "Pulse — Job Definitions"
record_type: system-doc
status: active
authority: user
created_at: 2026-08-14
---

# Pulse — Job Definitions

Shared job config for the heartbeat daemon (`system/tools/pulse.sh`) and the OS-level scheduler
installer (`system/tools/install-schedulers.sh`). This file is CODE, not personal data — it lives in
the repo, travels with `git pull`, and carries no identifiers of its own (see `system/tools/pulse.sh`
and every job's own file for how each resolves ITS notes root through `shared/brain_root.py`).

> ⚠ **NEW FILE — did not exist anywhere in this repo before this session.** `pulse.sh` and
> `install-schedulers.sh` cannot do anything without it; **this is the smallest version that makes
> both scripts real**, not a full replay of every job the donor system ever scheduled. Other
> categories' ported runners (ingest, cal's other jobs, archivist, etc.) get their own rows appended
> here **as their own lane ports them** — this file is shared, additive territory, not owned end-to-
> end by one lane. See the commented template row at the bottom of the `jobs` block.

## How it works

`pulse.sh` runs on a schedule (installed by `install-schedulers.sh` — every 5 minutes on Mac/Linux
via `cron`, or via Windows Task Scheduler on Windows; see that script's own header for why the
mechanism differs by OS while the dispatcher itself does not). On each run it reads the `jobs` block
below and executes any job whose interval has elapsed since its last run.

## Job format

Each line inside the fenced `jobs` block:

```
name | enabled | interval_seconds | command
```

- **enabled**: `yes` to run. Anything else is a DECLARED disposition, not just "off" — write the
  actual word (`no`, `parked`, `waiting-on-<thing>`) so a future health sweeper can render your own
  decision back to you as "by design," never as unexplained breakage. Never leave the field ambiguous
  just to silence a job.
- **interval_seconds**: minimum seconds between runs.
- **command**: literal bash, OR an internal builtin (leading `@`):
  - `@trim_md_days <file> <days>` — drop `## YYYY-MM-DD` sections older than N days
  - `@find_delete <dir> <days>` — delete `*.jsonl` under dir older than N days
- A command is a **stand-alone shell command** — it is executed as `bash -c "$cmd"`, so quote
  anything with spaces yourself (see the rows below).

Comment a line out with a leading `#`.

### Exit-code contract every job command should honor

| rc | meaning | counted by Pulse as |
|---|---|---|
| `0` | ran and succeeded (including "checked, found nothing wrong") | `ran` |
| `75` | the job's OWN preflight decided not to run this tick — e.g. required config/credentials aren't set up yet | `skipped` (never a fault) |
| `2` | a transient pre-flight/infra failure (network blip, auth hiccup) | held — never trips the breaker |
| anything else | a real failure | counted toward the 3-strike circuit breaker |

**Reaching a model from a scheduled job — HARD RULE.** `claude` is not on cron's (or Task
Scheduler's) PATH — a bare `claude -p ...` in a job command will resolve to nothing and exit 127,
which prints an EMPTY stdout indistinguishable from "the model ran and found nothing." No job in
THIS file invokes a model directly today, but if you add one that does, follow the house pattern
already live in `system/tools/ingest-run.lib.sh` (`CLAUDE_BIN` resolution + the
`~/.config/lifehack/claude-oauth-token` file) rather than inventing a new one — and treat rc=127 as a
FAILURE, never as "found nothing."

## Intervals reference

| Interval | Seconds |
|----------|---------|
| 5 min    | 300     |
| 30 min   | 1800    |
| 1 hour   | 3600    |
| 6 hours  | 21600   |
| 1 day    | 86400   |
| 7 days   | 604800  |

## Jobs

```jobs
# name           | enabled | interval | command
#
# system-health: THE MISSED-RUN SWEEPER (dead-man's-switch). Reads this manifest x the
# state/status/_pulse.json heartbeat x every state/status/*.json tile -> writes
# state/status/_system-health.json (need_attention[] + groups{}). Catches a job that SHOULD have
# fired and didn't. Also runs health_invariants.py (hooks present / guards untampered / clone fresh
# / coverage complete) and folds its findings in. 5-min cadence (same as Pulse itself, so a missed
# run is caught within one tick of it happening).
system-health    | yes | 300   | bash "$LIFEHACK_CODE_ROOT/system/tools/system-health-run.sh"
#
# sentinel-health: rolls system/logs/sentinel-events.jsonl -> state/status/sentinel.json on its own
# cadence, independent of any per-item check firing (so the tile's last_run doesn't go stale just
# because nothing happened to get scanned for hours). READ-ONLY, local jsonl only. 30-min cadence.
sentinel-health  | yes | 1800  | bash "$LIFEHACK_CODE_ROOT/system/tools/sentinel-health-run.sh"
#
# cal-health: READ-ONLY calendar check (conflicts + unconfirmed invites, 7-day forward window).
# Degrades cleanly (rc=75, "stood down") when config/cal.md has no calendar id configured yet — see
# shared/cal_config.py. No *-run.sh wrapper exists yet for this job (no single-instance lock / no
# buzz-on-hard-failure) — a future lane can add system/tools/cal-health-run.sh matching
# system-health-run.sh's pattern; until then this calls the checker directly. 6h cadence.
cal-health       | yes | 21600 | python3 "$LIFEHACK_CODE_ROOT/system/tools/cal-health.py"
#
# backlog-health: emits state/status/backlog.json from the read-only backlog groom engine. That
# engine (backlog_groom.py) belongs to a DIFFERENT category (PLANNING & BUILD, backlog-authority) and
# has not landed in this repo yet — this job degrades honestly (a clear NEEDS_REVIEW tile saying so,
# never a crash) until it does; see backlog-health.py's own header. Same no-wrapper note as cal-health
# above. 6h cadence.
backlog-health   | yes | 21600 | python3 "$LIFEHACK_CODE_ROOT/system/tools/backlog-health.py"
#
# ── TEMPLATE — copy this row when a new lane wires up a job, then delete the comment. ──────────
# your-job-name  | yes | 3600  | bash "$LIFEHACK_CODE_ROOT/system/tools/your-runner.sh"
```

## The OS-level schedule — installed by `install-schedulers.sh`

> This block is NOT Pulse-dispatched (`pulse.sh` only parses the ```jobs``` block above). It is the
> versioned source of truth for what the OPERATING SYSTEM's own scheduler runs:
> `system/tools/install-schedulers.sh` reads it and installs (crontab on Mac/Linux, Task Scheduler on
> Windows — see that script for why the mechanism differs by OS). **Edit here → run the installer on
> a machine → that machine is current.** Format: `name | schedule (5-field cron) | command` — a
> single-machine install has no `machine` column to filter on (the donor's had one; dropped here, see
> `install-schedulers.sh`'s own header).

```crontab
# name          | schedule           | command
#
# pulse: the ONE entry point. Every job in the ```jobs``` block above only ever runs because THIS
# line exists — install-schedulers.sh treats the row named "pulse" specially on Windows (it launches
# bash.exe against pulse.sh itself, not this row's literal command; see that script). The PATH
# prefix matters: cron's own PATH is a minimal `/usr/bin:/bin` on most systems, which is missing
# `/opt/homebrew/bin` (Apple Silicon Homebrew) and `/usr/local/bin` (Intel Homebrew / most Linux
# user installs) — without it, a job command that shells out to a Homebrew-installed tool by bare
# name would silently fail to find it under cron even though it works fine in an interactive shell.
pulse             | */5 * * * *      | PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LIFEHACK_CODE_ROOT="$LIFEHACK_CODE_ROOT" bash "$LIFEHACK_CODE_ROOT/system/tools/pulse.sh" >> "${TMPDIR:-/tmp}/lifehack-pulse.log" 2>&1
#
# health-deadman: the OUT-OF-BAND watcher for system-health ITSELF. DELIBERATELY its own dedicated
# scheduled entry, NEVER a Pulse job — dispatching it FROM Pulse would make the sweep the sole
# witness to its own death; if Pulse wedges, a Pulse-dispatched watchdog wedges with it and the
# silence would read exactly like health. Hourly: system-health runs every 5 min, so an hour of
# silence from it is unambiguous without being twitchy.
health-deadman    | 17 * * * *       | PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LIFEHACK_CODE_ROOT="$LIFEHACK_CODE_ROOT" bash "$LIFEHACK_CODE_ROOT/system/tools/health-deadman-check.sh" >> "${TMPDIR:-/tmp}/lifehack-health-deadman.log" 2>&1
```

## Why `$LIFEHACK_CODE_ROOT` and not a literal path

Every command above resolves the repo location through the `$LIFEHACK_CODE_ROOT` environment
variable rather than a hardcoded path (the donor's equivalent file hardcoded
`$HOME/claudeops-config` into nearly every job's command string — the single largest generalization
item its own port audit found). `install-schedulers.sh` sets this variable when it writes the
crontab/Task-Scheduler entry (derived from its own script location at install time), so the value is
always "wherever THIS clone actually is," never a guess. If you invoke `pulse.sh` by hand instead of
through the installed schedule, export it yourself first: `export LIFEHACK_CODE_ROOT="$(cd
"$(dirname "$0")/.." && pwd)"` from the repo root, or simply `cd` into the repo and run
`bash system/tools/pulse.sh` — the individual job commands above still need `$LIFEHACK_CODE_ROOT`
set for their own `bash "..."` calls to resolve, since `pulse.sh` runs each command through a plain
`bash -c`, which does not know the repo's location on its own.
