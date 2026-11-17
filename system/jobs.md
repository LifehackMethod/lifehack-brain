---
topic: [system-architecture]
title: "Scheduled jobs — the shared job table"
record_type: system-doc
status: active
authority: user
created_at: 2026-08-14
---

# Scheduled jobs — the shared job table

Shared job table for the scheduler: `install-schedulers.sh` builds one launchd job per enabled row on a
Mac, each run through `system/tools/job-run.sh`; on Linux and Windows `system/tools/pulse.sh` dispatches
the rows. This file is CODE, not personal data — it lives in
the repo, travels with `git pull`, and carries no identifiers of its own (see `system/tools/pulse.sh`
and every job's own file for how each resolves ITS notes root through `shared/brain_root.py`).

The shared table holds product jobs only; a person's own jobs live in `<personal-code>/jobs.md` (see the
block header).

## How it works

On a Mac, `install-schedulers.sh --install` writes one `~/Library/LaunchAgents/ai.lifehack.<job>.plist`
per row of the `jobs` block whose enabled column is `yes`, and each plist runs that job inside
`system/tools/job-run.sh` (`<job> --if-overdue`); Pulse is not involved there (see the scheduler section
of `system/organism/manual.md`). `pulse.sh` and the `crontab` block apply to Linux and Windows only.

On Linux and Windows, `pulse.sh` runs on a schedule (installed by `install-schedulers.sh` — every 5
minutes via `cron` on Linux, or via Windows Task Scheduler on Windows; see that script's own header
for why the mechanism differs by OS while the dispatcher itself does not). On each run it reads the
`jobs` block below and executes any job whose interval has elapsed since its last run. The `jobs`
block itself is shared: macOS reads the same rows (name, enabled, command) to build its launchd jobs.

## Job format

Each line inside the fenced `jobs` block:

```
name | enabled | interval_seconds | outcome | check | model | budget | source | command
```

The five contract columns (outcome, check, model, budget, source) are documented in the `jobs` block's header comment;
`command` stays last because it may contain `|`.

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

On a Mac each job runs inside `system/tools/job-run.sh`, whose contract is: `0` = output check passed ·
`75` = stood down · `2` = transient · `78` = the door refused the row at run time (counts toward the
alert) · anything else = failed; the alarm is an ntfy text sent by `job-run.sh`, not a Pulse breaker. The
right-hand column below is Pulse's (Linux and Windows). The job commands' own exit codes mean the same
thing on both.

| rc | meaning | counted by Pulse as |
|---|---|---|
| `0` | ran and succeeded (including "checked, found nothing wrong") | `ran` |
| `75` | the job's OWN preflight decided not to run this tick — e.g. required config/credentials aren't set up yet | `skipped` (never a fault) |
| `2` | a transient pre-flight/infra failure (network blip, auth hiccup) | held — never trips the breaker |
| anything else | a real failure | counted toward the 3-strike circuit breaker |

**Reaching a model from a scheduled job.** A runner sources `$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh`
and calls `run_model <tier> ...`; it names a tier, and a literal model id or `--model X` anywhere else is
refused by the door (`canon/cron-jobs-sop.md` §5, §9). `claude` is not on the scheduler's PATH, so a bare
`claude -p` exits 127 with empty output: a failed step must not read as "nothing new" (§7). Anything a job
reads from outside goes through the Sentinel pipeline before a model sees it.

⛔ **The credential half of that pattern is NOT yours to hand-roll — call
`require_claude_token` from `system/tools/claude-auth.lib.sh`.** It is the single shared
implementation of the missing-token preflight, and it returns **75** (this table's "stood down") —
never 3. History, and the reason this is written so strongly: five runners each hand-rolled
that same check with the same wrong `exit 3`, and the bug was fixed TWICE (archivist-run.lib.sh,
planning-weekly-prime-run.sh) before anyone noticed three more copies still carried it — a fix to a
copy reaches only that copy. Usage:
`source "$CODE_ROOT/system/tools/claude-auth.lib.sh"` then `require_claude_token "<job>" || exit 75`
(the helper emits the named stand-down line itself; the caller decides how to terminate and whether
to write a tile first). A stand-down is loud and named — it is never a silent success.

⛔ **Same pattern, second credential — gws/Google.** Google credentials live only in the shared fetch; a
runner never loads or exports them (`canon/cron-jobs-sop.md` §7). The shared fetch's own preflight is
`require_gws_credentials` / `load_gws_credentials_optional` in `system/tools/gws-auth.lib.sh`. Sibling of the above, same
contract, same reason. It went ELEVEN copies deep before being consolidated, and the `exit 3` bug
was in six of them; three were fixed (calendar-store-sync, tasks-store-sync, email-summary-write)
while `ingest_load_gws()` in `ingest-run.lib.sh` kept `exit 3` — and unlike those three (latent, no
scheduler row) that one was REACHABLE. ⭐ It is also the WORSE branch of the two: a missing claude
token is fixed by one `claude setup-token`, but "no Google account connected" is **permanent** for a
large share of installs, so `exit 3` there auto-disabled a runner forever for the majority case.
Usage:
`source "$CODE_ROOT/system/tools/gws-auth.lib.sh"` then, picking by what the job does WITHOUT Google:

| your job without Google | call | on absent/unusable creds |
|---|---|---|
| cannot do its work at all | `require_gws_credentials "<job>" \|\| exit 75` | rc **75**, named line, job does not run |
| still produces a real, degraded result | `load_gws_credentials_optional "<job>"` | always rc **0**, one named NOTE, job continues |

Both take an optional 2nd arg — the name of your own logger function — so a caller with its own
timestamped log format keeps it (`... "<job>" _my_logger`). On success both export
`GOOGLE_WORKSPACE_CLI_{CONFIG_DIR,CREDENTIALS_FILE,KEYRING_BACKEND}`; both publish `$GWS_CREDS_FILE`
and `$GWS_AUTH_STANDDOWN_REASON`. Neither exits on your behalf — several callers must set their own
`RC` global first so their EXIT trap records the stand-down, and one must `return` from inside a
function rather than kill its wrapper.

**A present-but-unusable credential file is a stand-down too, with its OWN reason.** Every one of
the eleven hand-rolled copies gated on `[ -s "$GWS_CREDS" ]`, which passes a file holding only a
newline and passes a truncated/corrupt export — so they exported garbage and failed downstream with
empty output, i.e. "I could not look" spelled as "I looked and it was fine." The helper reads and
JSON-parses it, and reports `empty-gws-credentials` / `unparseable-gws-credentials` distinctly from
`no-gws-credentials`. (`system/build-rules-index.md`, ABSENT-SUBJECT-RULE-v1.) A **missing library**,
by contrast, is `exit 1` — a real defect, never a stand-down.

⚠ **NOT in that lib, deliberately — the live `gws … getProfile` pre-flight that follows it.** Seven
runners retry that call 3×/4s and exit **2** on failure. Do not fold it into the 75: reaching it
means credentials exist and parse, so the person IS configured and a failing call is a transient/
infra condition — this table's rc=2 ("held", never the breaker). Collapsing it would report a
configured machine as unconfigured and hide genuinely dead auth forever. It also ends differently by
design — FATAL in calendar-store-sync / tasks-store-sync / email-summary-write / `ingest_load_gws`,
warn-only in planning-vault / planning-vault-weekly / planning-diary, which degrade and mark the source unavailable.
That severity difference is real, so the loop stays with its callers.

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
# name | enabled | interval | outcome | check | model | budget | source | command
#
# COLUMNS (self-monitoring 5.1 - a row carries its contract; `command` is LAST because a command may contain `|`,
# so NO other column may contain a `|` character):
#   name      job name; also the launchd label fragment and the state folder.
#   enabled   `yes` runs; any other word is a declared disposition (`off`, `waiting-on-port`, ...).
#   interval  minimum seconds between runs (macOS: a whole-hour divisor of 86400, or a multiple of 86400).
#   outcome   ONE sentence: what is true after a good run. The `check` is written against it. `TBD` until written.
#   check     `<path> ~ <extended regex>`, evaluated by job-run.sh after the command exits 0. Passes only if <path>
#             exists, its mtime is newer than the run start, and some line of it matches the regex (grep -E).
#             $HOME, ${HOME}, $LIFEHACK_CODE_ROOT and a leading ~ are expanded in <path>. Split at the FIRST ` ~ `.
#             No `|` inside the regex (it is the column delimiter): write alternation as an optional group instead.
#             Empty or `TBD` = no check declared = the job can never succeed.
#   model     none | small | medium | large  (the model tier the job may use; named in one place, not here). `TBD` if unset.
#   budget    max model calls per run, an integer; a generous tripwire sized to the outcome. 0 = none.
#   source    which shared fetch feeds the job: gmail | web | gsheet | none. `gmail` makes job-run.sh load the gws
#             credentials (NEEDS=gws). `TBD` if unset.
#   command   literal bash (executed as `bash -c`), or a leading-`@` builtin. Everything after the 8th `|` is the command.
#
# 2026-10-27 self-monitoring Sprint 1: only email-summary-write was enabled; now off (2026-11-14); rows below set off (were yes), restored in later sprints.
# 2026-10-27 self-monitoring 3.1: the watcher rows (system-health, sentinel-health, planning-health, backlog-health,
# fault-proposer, item-store-freshness, email-summary-freshness, a dashboard keepalive and the per-desk health watchers) were
# removed with their runners; git history has them.
#
# 3b.7 B (2026-11-01): PERSONAL jobs (a person's own desks and scripts) do not live in this shared table. They go in
# <personal-code>/jobs.md (same nine columns, its own ```jobs block) with their plain names in <personal-code>/job-names.txt.
# Every scheduler entry point (pulse.sh, job-run.sh, install-schedulers.sh, health_line.py, pulse-park.sh) reads this table
# PLUS that one through shared/jobs_manifest.py; on a name clash the personal row wins, with a warning. No personal file = none.
#
#
# ── The next three refresh Google-backed stores (calendar, tasks, the email thread store). A missing or
#    unusable credential file stands the run down (rc 75), never a fault, and a stood-down run never
#    pages the phone. All three ship off: outside connections stay off until the person switches them on.
#
# calendar-store-sync: refreshes the calendar item store via calendar_store_sync.py --sync. It calls the
# intake reader (claude -p, small tier) on every item carrying free text. Daily (the runner's
# STALE_AFTER_HOURS=30).
calendar-store-sync | off | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/calendar-store-sync-run.sh"
#
# tasks-store-sync: refreshes the tasks item store via tasks_store_sync.py --sync. It calls the intake
# reader (claude -p, small tier) on every task carrying free text. Daily (the runner's
# STALE_AFTER_HOURS=30).
tasks-store-sync | off | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/tasks-store-sync-run.sh"
#
# email-summary-write: refreshes the email thread store via email_summary_sync.py --write-v2. It calls
# the intake reader only on spans the injection scan flagged — the Sentinel pipeline as defined. Every 3h
# (the runner's STALE_AFTER_HOURS=4).
# 2026-10-27 (self-monitoring Sprint 1, the owner's ruling): capped at 3 threads per run, enough to prove
# the scheduled chain without pulling the whole inbox. Remove EMAIL_WRITE_LIMIT=3 to return to full runs.
email-summary-write | off | 10800 | Keeps the v2 email thread store current: the run reads at least one Gmail thread and records written plus unchanged threads. | ~/.local/share/lifehack/email-summary-write/last-write.log ~ v2 write DONE.*written=(0 unchanged=)?[1-9].* errors=0$ | small | 30 | gmail | EMAIL_WRITE_LIMIT=3 bash "$LIFEHACK_CODE_ROOT/system/tools/email-summary-write-run.sh"
#
# ── T9.8b, 2026-08-15 — five rows closing four previously-missing wiring gaps. Each runner was
#    ported/built THIS session and syntax/dry-path verified (skip branches exercised with real
#    exit codes); none has been LIVE-fired end-to-end against a real headless claude call as
#    part of this port (that would spend real tokens against real notes content to "test" a
#    schedule row — the skip-path verification is the honest substitute). All five are
#    OS-agnostic: they only ever run because THIS row exists. On a Mac launchd runs each yes row through
#    job-run.sh; on Linux and Windows pulse.sh dispatches it — see "How it works" above.
#
# planning-diary: planning-diary-capture.py (daily) + planning-diary-rollup.py (weekly/monthly/
# quarterly/yearly, each period-idempotently self-gated — see planning-diary-run.sh's own header)
# were ported without a row in this manifest, missed by the pass that wired seven other orphaned
# runners. ONE row chains all five cadence checks — each periodic call is a cheap no-op except on
# its own due date, so a single daily tick is sufficient to drive every cadence. && (not ;) so a
# real daily failure is not masked by continuing to the periodic checks.
planning-diary | off | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence weekly && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence monthly && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence quarterly && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence yearly
#
# archivist-audit / archivist-deepmine: archivist-run.lib.sh (shared engine) + both wrappers
# were entirely absent — no file, no row — so the weekly structural audit and the monthly
# per-desk deep-mine were manual forever. Two rows, not one: they are genuinely different
# cadences and different prompts, not one operation with a period flag (unlike planning-diary
# above). archivist-deepmine's own STAGGER lives inside the wrapper (a notes-durable ledger
# picks the single most-overdue desk each tick) — the row below just has to tick often enough
# for that internal stagger to work; 4-day cadence matches the wrapper's own derivation.
archivist-audit | off | 604800 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/archivist-audit-run.sh"
archivist-deepmine | off | 345600 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/archivist-deepmine-run.sh"
#
# LEGACY (2026-11-17, CR-9 step 3; the owner's Fable answer 6): planning-weekly-prime is the old
# plumbing, replaced by Grand Central's engine. The row stays off and its contract stays unfilled;
# deleting the row and its runner is the owner's separate yes.
# planning-weekly-prime: the mid-week map-warming cron for the planning-weekly skill's Phase 0,
# cited by name (with a line number) at .claude/skills/planning-weekly/prompts/
# 00-system-layer.md:68 — a dangling promise until this row + its runner landed. Ticked daily
# (not weekly) because its OWN cadence guard (Thu/Fri/Sat window, ISO-week idempotent via
# map.md's own existence) needs a daily check to catch the window at all — see the runner's
# header for why the "real" Phase 0 fan-out (Agent-tool-based) cannot be invoked from cron and
# what this ships instead.
planning-weekly-prime | off | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/planning-weekly-prime-run.sh"
#
# guard-fire-test: the engine (organism/label_checker.py + label_manifest.yaml, run through
# verify-hooks.sh) already exists and is correct (confirmed GREEN this session — 20/20 guards
# LIVE) but nothing fired it on a schedule and nothing read its result — a downgrade from LIVE
# to PARTIAL would sit invisible until a human happened to run it by hand. Weekly cadence
# matches the runner's own STALE_AFTER_HOURS=192 (168h weekly + 24h slack) header.
guard-fire-test | off | 604800 | Every guard was fire-tested this week and the verdict (GREEN or a named downgrade) reached the findings store, so a weakened guard shows on the session line. | ~/.config/lifehack/guard-fire-test/last-run.json ~ "verdict":"[GD][A-Z]+","named":"[^"]+" | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/guard-fire-test-run.sh"
#
# obsidian-reindex: machine-local vault index rebuild (single-instance lock + watchdog in donor).
# CORRECTED 2026-08-26 (verified this session): "Missing runner" was wrong — the runner exists in
# this repo at system/tools/obsidian-reindex.sh with the lock + watchdog intact. RUN THIS SESSION:
# exit 0 (ran to completion, no scandir/timeout errors).
obsidian-reindex | off | 21600 | The Obsidian vault search index was rebuilt from the Drive notes and the archived-copy prune ran, so vault search reflects notes written up to six hours ago. | ~/.config/lifehack/obsidian-reindex/last-index.txt ~ ^obsidian-reindex ok index_rc=0 prune_rc=0 db_bytes=[1-9][0-9]+ | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/obsidian-reindex.sh"
#
# mirror-fetch: M14 — the scheduled fetch that keeps mirror_line.sh's (M9/M13) "behind" and
# "ahead" figures honest. mirror_line.sh reads only local refs by contract (a session-start line
# must not touch the network), so without something else fetching, "behind" can only ever read 0.
# FETCH ONLY: git fetch origin --prune against THIS clone (never pull/merge/checkout, never
# touches a working tree or a local branch) — a REPORT, not a gate, per SOP §9. Hourly cadence:
# frequent enough that "behind" stays close to true without hammering the remote on every tick.
mirror-fetch | off | 3600 | This clone's remote-tracking refs are freshly fetched from origin, so the session line's "behind" figure is true. | ~/.config/lifehack/mirror-fetch/last-ok ~ ^mirror-fetch DONE behind=[0-9]+ ahead=[0-9]+ | none | 0 | git | bash "$LIFEHACK_CODE_ROOT/system/tools/mirror-fetch-run.sh"
#
# ── TEMPLATE — copy this row when a new lane wires up a job, then delete the comment. ──────────
# your-job-name  | yes | 3600  | <one-sentence outcome> | <path> ~ <regex> | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/your-runner.sh"
```

## The OS-level schedule — installed by `install-schedulers.sh`

> This block is read on Linux and Windows only; a Mac builds its launchd jobs from the ```jobs``` block
> (see "How it works" and `system/organism/manual.md`).
>
> This block is NOT Pulse-dispatched (`pulse.sh` only parses the ```jobs``` block above). It is the
> versioned source of truth for what the OPERATING SYSTEM's own scheduler runs on Linux/Windows:
> `system/tools/install-schedulers.sh` reads it and installs (crontab on Linux, Task Scheduler on
> Windows — see that script for why the mechanism differs by OS). **Edit here → run the installer on
> a machine → that machine is current.** Format: `name | schedule (5-field cron) | command` — a
> single-machine install has no `machine` column to filter on (the donor's had one; dropped here, see
> `install-schedulers.sh`'s own header).

```crontab
# name          | schedule           | command
#
# pulse: the one entry point on Linux and Windows. There, every job in the ```jobs``` block runs only because THIS
# line exists (a Mac never reads this block) — install-schedulers.sh treats the row named "pulse" specially on Windows (it launches
# bash.exe against pulse.sh itself, not this row's literal command; see that script). The PATH
# prefix matters: cron's own PATH is a minimal `/usr/bin:/bin` on most systems, which is missing
# `/opt/homebrew/bin` (Apple Silicon Homebrew) and `/usr/local/bin` (Intel Homebrew / most Linux
# user installs) — without it, a job command that shells out to a Homebrew-installed tool by bare
# name would silently fail to find it under cron even though it works fine in an interactive shell.
# `$HOME/.local/bin` LEADS THE LIST, and it is not hypothetical: on a Mac with no Homebrew and no
# sudo, that is where a standalone binary goes, and it is where the Google Workspace CLI (`gws`)
# actually lives on this system. Without it every scheduled job that touches Google reported "not
# installed" while the same command worked perfectly in an interactive shell — the failure is
# silent, and it is invisible from the shell you would test in. Found 2026-08-23 (open loop #34a),
# fixed 2026-08-24. It stays UNEXPANDED here on purpose: install-schedulers.sh substitutes only
# `$LIFEHACK_CODE_ROOT`, so `$HOME` is written literally into the crontab and expanded by /bin/sh
# at fire time — which makes the same manifest correct on every machine and every user account.
pulse             | */5 * * * *      | PATH=$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin LIFEHACK_CODE_ROOT="$LIFEHACK_CODE_ROOT" bash "$LIFEHACK_CODE_ROOT/system/tools/pulse.sh" >> "${TMPDIR:-/tmp}/lifehack-pulse.log" 2>&1
#
# (2026-10-27 3.1: the health-deadman watcher row was removed with its script, health-deadman-check.sh.)
```

## Why `$LIFEHACK_CODE_ROOT` and not a literal path

Every command above resolves the repo location through the `$LIFEHACK_CODE_ROOT` environment
variable rather than a hardcoded path (the donor's equivalent file hardcoded
its own clone folder into nearly every job's command string — the single largest generalization
item its own port audit found). `install-schedulers.sh` sets this variable when it writes the
crontab/Task-Scheduler entry (derived from its own script location at install time), so the value is
always "wherever THIS clone actually is," never a guess. If you invoke `pulse.sh` by hand instead of
through the installed schedule, export it yourself first: `export LIFEHACK_CODE_ROOT="$(cd
"$(dirname "$0")/.." && pwd)"` from the repo root, or simply `cd` into the repo and run
`bash system/tools/pulse.sh` — the individual job commands above still need `$LIFEHACK_CODE_ROOT`
set for their own `bash "..."` calls to resolve, since `pulse.sh` runs each command through a plain
`bash -c`, which does not know the repo's location on its own.
