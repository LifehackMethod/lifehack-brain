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
> categories' ported runners (ingest, planning's other jobs, archivist, etc.) get their own rows appended
> here **as their own lane ports them** — this file is shared, additive territory, not owned end-to-
> end by one lane. See the commented template row at the bottom of the `jobs` block.

## How it works

> ⚠ **CORRECTED 2026-10-27:** the text below used to say Pulse runs on Mac via `cron`. That is no
> longer true. **On macOS, scheduled jobs run through launchd:** `install-schedulers.sh --install`
> writes one `~/Library/LaunchAgents/ai.lifehack.<job>.plist` per row of the `jobs` block whose
> enabled column is `yes`, and each plist runs that job inside `system/tools/job-run.sh`
> (`<job> --if-overdue`). Pulse is not involved on a Mac. See the scheduler section of
> `system/organism/manual.md`. **`pulse.sh` and the `crontab` block apply to Linux and Windows only.**

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

> ⚠ **CORRECTED 2026-10-27:** the right-hand column below describes **Pulse** (Linux/Windows). On
> macOS each job runs inside `system/tools/job-run.sh`, whose contract is: `0` = output check passed ·
> `75` = stood down · `2` = transient · anything else = failed; the alarm is an ntfy text sent by
> `job-run.sh`, not a Pulse breaker. The job commands' own exit codes mean the same thing on both.

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

⛔ **The credential half of that pattern is NOT yours to hand-roll — call
`require_claude_token` from `system/tools/claude-auth.lib.sh`.** It is the single shared
implementation of the missing-token preflight, and it returns **75** (this table's "stood down") —
never 3. History, and the reason the rule is written this strongly: five runners each hand-rolled
that same check with the same wrong `exit 3`, and the bug was fixed TWICE (archivist-run.lib.sh,
planning-weekly-prime-run.sh) before anyone noticed three more copies still carried it — a fix to a
copy reaches only that copy. Usage:
`source "$CODE_ROOT/system/tools/claude-auth.lib.sh"` then `require_claude_token "<job>" || exit 75`
(the helper emits the named stand-down line itself; the caller decides how to terminate and whether
to write a tile first). A stand-down is loud and named — it is never a silent success.

⛔ **Same rule, second credential — gws/Google: call `require_gws_credentials` (or
`load_gws_credentials_optional`) from `system/tools/gws-auth.lib.sh`.** Sibling of the above, same
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
#   interval  minimum seconds between runs (macOS: a whole-hour divisor of 86400).
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
# 2026-10-27 self-monitoring Sprint 1: only email-summary-write is enabled; rows below set off (were yes), restored in later sprints.
# 2026-10-27 self-monitoring 3.1: the watcher rows (system-health, sentinel-health, planning-health, backlog-health,
# fault-proposer, item-store-freshness, email-summary-freshness, helm-keepalive, marc-deadman, clair-health,
# deryl-books-health, dobby-health, recommend) were removed with their runners; git history has them.
#
#
# ── The next three refresh Google-backed stores (calendar item-store, tasks item-store, v2 email
#    thread-store) — LIVE as of 2026-08-14, having just cleared the ONE verified defect that kept
#    them parked. On a MISSING $HOME/.config/lifehack/gws-credentials.json (true for every machine
#    on day 1 before the one-time `gws auth export` step, and PERMANENTLY true for a student with
#    no Google account at all — exactly the population this manifest must not fail loudly for)
#    each runner's "no creds file" branch now does `RC=75; exit 75` — this file's own "stood down,
#    not a fault" convention, matching planning-health/backlog-health above for the identical "config
#    not set up yet" case (was `RC=3; exit 3` before this session, which fell into the "anything
#    else" bucket: 3 consecutive ticks would trip Pulse's circuit breaker and system-health.py's
#    assess() — system/tools/system-health.py:255-257 — would render the job "DOWN, severity:
#    error, attention: True" PERMANENTLY, a red Helm tile for a feature a no-Google student will
#    never configure). SAME SESSION, second half of the fix: each runner's own EXIT trap no longer
#    fires a `--priority critical` phone push on rc=75 either — a stood-down job silently paging
#    the phone on every future dispatch would have been WORSE than the red tile this replaces
#    (critical bypasses quiet hours). Genuine failures (any other non-zero) still page, unchanged.
#    Flipped `enabled` to `yes` now both halves have landed; intervals are unchanged, sourced from
#    each runner's own header.
#
# calendar-store-sync: refreshes state/item-store/calendar/ via calendar_store_sync.py --sync
# ~~(mechanical, no claude -p — confirmed)~~ ⛔ STRUCK 2026-09-19, FALSE: it DOES call claude -p.
# calendar_store_sync.py imports run_intake_judge at :163 and calls it at :548, UNCONDITIONALLY on
# every item carrying free text (:546) — a real haiku call (intake_reader.py:46,:164-166). The
# module's own docstring :15 ("No LLM in the write path") is stale and was the source of this error.
# LIVE — see the note above. Interval matches the runner's
# own header ("own absence horizon... writers run ~daily", STALE_AFTER_HOURS=30). 1-day cadence.
calendar-store-sync | off | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/calendar-store-sync-run.sh"
#
# tasks-store-sync: refreshes state/item-store/tasks/ via tasks_store_sync.py --sync ~~(mechanical,
# no claude -p — confirmed)~~ ⛔ STRUCK 2026-09-19, FALSE: tasks_store_sync.py imports
# run_intake_judge at :102 and calls it at :391, UNCONDITIONALLY on every task carrying free text.
# Its own docstring :13 carries the identical stale "No LLM in the write path" wording as calendar.
# LIVE for the SAME reason as calendar-store-sync immediately above —
# tasks-store-sync-run.sh shared the identical GWS_CREDS-missing branch and got the identical fix.
# Interval matches the runner's own header ("writers run ~daily", STALE_AFTER_HOURS=30). 1-day
# cadence.
tasks-store-sync | off | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/tasks-store-sync-run.sh"
#
# email-summary-write: refreshes the v2 faithful-thread store (threads-v2/) via
# email_summary_sync.py --write-v2 ~~(mechanical, no claude -p — confirmed: CLAUDE_BIN is kept but
# never invoked by the v2 write path; see shared/tools/email_summary_sync.py:114-120)~~
# ⛔ STRUCK 2026-09-19, FALSE: email_summary_sync.py imports run_intake_judge at :197 and calls it
# at :832 inside the per-message loop of process_thread_v2(). ⚠ UNLIKE calendar and tasks, email
# calls the judge CONDITIONALLY — only when scan_for_injection already flagged spans; unflagged
# bodies reach the store with no model having read them. That asymmetry is unexplained and may be
# drift rather than design. The cited proof-lines :114-120 describe the RETIRED v1 digest step, and
# the same file's docstring :19 already lists the decode-and-judge as a live security step. LIVE for
# the SAME rc=3-vs-rc=75 fix as the two rows above (identical GWS_CREDS-missing branch in
# email-summary-write-run.sh) — same fix, same session. Interval matches the runner's OWN header,
# which is explicit: STALE_AFTER_HOURS=4, "just over one 3h cadence, so a SINGLE missed run
# surfaces on the next tick." 3h cadence.
# 2026-10-27 (self-monitoring Sprint 1, Enver's ruling): capped at 3 threads per run, enough to prove
# the scheduled chain without pulling the whole inbox. Remove EMAIL_WRITE_LIMIT=3 to return to full runs.
email-summary-write | yes | 10800 | Keeps the v2 email thread store current: the run reads at least one Gmail thread and records written plus unchanged threads. | ~/.local/share/lifehack/email-summary-write/last-write.log ~ v2 write DONE.*written=(0 unchanged=)?[1-9].* errors=0$ | small | 30 | gmail | EMAIL_WRITE_LIMIT=3 bash "$LIFEHACK_CODE_ROOT/system/tools/email-summary-write-run.sh"
#
# ── T9.8b, 2026-08-15 — five rows closing four previously-missing wiring gaps. Each runner was
#    ported/built THIS session and syntax/dry-path verified (skip branches exercised with real
#    exit codes); none has been LIVE-fired end-to-end against a real headless claude call as
#    part of this port (that would spend real tokens against real notes content to "test" a
#    schedule row — the skip-path verification is the honest substitute). All five are
#    OS-agnostic: they only ever run because THIS row exists, on either scheduler, since both
#    invoke pulse.sh identically — see "How it works" above.
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
# ⚠ TENSION, flagged not silently resolved: .claude/skills/archivist-deepmine/SKILL.md still
# says "its scheduled runner does NOT ship... the skill IS the interactive path" — that line
# predates this port and is now stale; this task's own plan named the missing scheduled leg as
# the gap to close. The skill file is outside this row's ownership to correct.
archivist-audit | off | 604800 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/archivist-audit-run.sh"
archivist-deepmine | off | 345600 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/archivist-deepmine-run.sh"
#
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
# marc-health: Marc's market-data health chain. MIGRATED 2026-10-27 (self-monitoring 5.5 + 5.7), row OFF. The runner is DESK code: it
# lives in the private ClaudeOps repo (desks/marc/tools/marc-health/, origin egjokaj/ClaudeOps), reached as $HOME/.claude/skills/ClaudeOps/...
# (the door allows runners under that repo and refuses any pinned clone path). Every feed read goes through safe_fetch.py with the
# Level-2 domain allowlist ON; its ONE AI call (the daily voice read) goes through run_model, tier small; it never pushes (job-run alerts).
# The check reads the receipt the runner writes after verifying the snapshot it just refreshed (the Drive path itself cannot be written here).
marc-health | off | 7200 | Marc's market snapshot is refreshed from the public feeds through the safe fetch every cycle, with the SPY and VIX core read verified fresh and the daily voice read written, so Marc's weekly reads never start on a stale price feed. | ~/.config/lifehack/marc-health/health-note.txt ~ ^marc-health ok .* core_ok=1 | small | 3 | web | bash "$HOME/.claude/skills/ClaudeOps/desks/marc/tools/marc-health/marc-health-run.sh"
#
# marc-weekly: eight-researcher weekly deep-read fan-out. CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — runner exists in the Brain at
# desks/marc/tools/marc-weekly/marc-weekly-run.sh. It self-gates to Sat/Sun only (DOW guard); a
# by-hand run today (Wed) hit a pre-existing single-instance lock and exited 0 clean before
# reaching the DOW check — a real, safe stand-down, not a fabricated pass.
marc-weekly | waiting-on-port | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/marc/tools/marc-weekly/marc-weekly-run.sh"
#
# marc-wednesday: mid-week light scan (donor notes a live false-all-clear defect carried forward,
# not fixed by this port). CORRECTED 2026-08-26 (verified this session): "Missing runner" was
# wrong — runner exists in the Brain at desks/marc/tools/marc-wednesday/marc-wednesday-run.sh.
# ⛔ NOT RUN THIS SESSION: this job is genuinely due today (its own due-window includes today, and
# its marker is behind the current ISO week) — invoking it would fire a real multi-source LLM
# research fan-out (real token spend), not a dry no-op. UNVERIFIED-BY-DESIGN, not confirmed working.
marc-wednesday | waiting-on-port | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/marc/tools/marc-wednesday/marc-wednesday-run.sh"
#
# clair-billing: billing/client detail emit + cadence-nudge push. CORRECTED 2026-08-26 (verified
# this session): "Missing runner" was wrong — runner exists in the Brain at
# desks/clair/tools/clair-billing/clair-billing-run.sh. RUN THIS SESSION: exit 0 — wrote its two
# signal files (read-only on Google + local writes only); the push-due branch correctly
# self-deduped, so no new phone notification fired.
clair-billing | waiting-on-port | 21600 | TBD | TBD | TBD | 0 | TBD | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/clair/tools/clair-billing/clair-billing-run.sh"
#
# deryl-ingest: Deryl desk light daily email doorman. CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — runner exists in the Brain at
# desks/deryl/tools/deryl-ingest/deryl-ingest-run.sh. RUN THIS SESSION (supervised, as its own
# header prescribes): `MAX_EMAILS=2 DRY_RUN=1` — exit 0, no new mail, cheap exit (no claude, no
# tokens). The command below is the sanctioned live shape; its own header still says this row is
# registered disabled until the Huddle-2 staged live test proves the reader/actor split — that
# prerequisite is separate from "does the runner exist."
deryl-ingest | waiting-on-port | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/deryl/tools/deryl-ingest/deryl-ingest-run.sh"
#
# cp-utilities: property utilities ingest chain (utility portal + submeter). CORRECTED 2026-08-26
# (verified this session): "Missing runner" was wrong — runner exists in the Brain at
# desks/deryl/tools/cp-utilities/cp-utilities-run.sh. RUN THIS SESSION: `CP_DRYRUN=1` — exit 0,
# both ingest scripts ran --dry-run cleanly, reconcile=OK, ZERO writes. Its own header still lists
# two unmet prerequisites (keychain env-fallback code, Enver's one-time utility-portal keychain export)
# before a live run is safe.
cp-utilities | waiting-on-port | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/deryl/tools/cp-utilities/cp-utilities-run.sh"
#
# emporia: carriage-house electric submeter ingest. CORRECTED 2026-08-26 (verified this session):
# "Missing runner" was wrong — runner exists in the Brain at desks/deryl/tools/emporia/
# emporia-run.sh. RUN THIS SESSION: `EMPORIA_DRYRUN=1` — exit 0, ran --dry-run cleanly, plausible
# reading, ZERO writes. Its own header still lists the same two open prerequisites as cp-utilities.
emporia | waiting-on-port | 86400 | TBD | TBD | TBD | 0 | TBD | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/deryl/tools/emporia/emporia-run.sh"
#
# emily-breakdown: Emily desk audition-ingest cron slot. CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — runner exists in the Brain at
# desks/emily/tools/emily-breakdown/emily-breakdown-run.sh. RUN THIS SESSION: `DRY_RUN=1` — exit 0,
# BUT surfaced a separate real defect: this runner hardcodes a stale `CODE_ROOT` path from a
# superseded clone location that does not match any actual live clone — the dry-run diagnostic
# confirmed both the skill file and notify-send.sh resolved to [exists: NO] under that hardcoded
# path. Genuine wiring defect in the Brain-resident runner itself, out of this row's scope to fix.
# ⚠ enable-recommend NO until that path is corrected.
emily-breakdown | waiting-on-port | 300 | TBD | TBD | TBD | 0 | TBD | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/emily/tools/emily-breakdown/emily-breakdown-run.sh"
#
# token-burn-mine: cost-trend Hospital finding mined from the existing transcript corpus.
# CORRECTED 2026-08-26 (verified this session): "Missing runner" was wrong — it exists, parked at
# system/parked/2026-08-23-donor-spillover/system/tools/token_burn_mine.py (underscore, not
# hyphen — confirmed this IS why a naive hyphen-only search missed it earlier). RUN THIS SESSION AT
# ITS PARKED LOCATION (bare): FAILED, exit 1 — missing its `emit_finding` sibling module, which
# only exists in system/tools/, not in its current parked directory. RE-RUN with
# `PYTHONPATH="$LIFEHACK_CODE_ROOT/system/tools"` prefixed: exit 0 — mined the transcript corpus
# cleanly, correct aggregate table, no transcript content leaked. The PYTHONPATH prefix below is a
# workaround for the parked location, not a fix — once properly wired into system/tools/ (out of
# this row's scope today) the prefix becomes unnecessary.
token-burn-mine | waiting-on-port | 86400 | TBD | TBD | TBD | 0 | TBD | PYTHONPATH="$LIFEHACK_CODE_ROOT/system/tools" python3 "$LIFEHACK_CODE_ROOT/system/parked/2026-08-23-donor-spillover/system/tools/token_burn_mine.py"
#
# obsidian-reindex: machine-local vault index rebuild (single-instance lock + watchdog in donor).
# CORRECTED 2026-08-26 (verified this session): "Missing runner" was wrong — the runner exists in
# this repo at system/tools/obsidian-reindex.sh with the lock + watchdog intact. RUN THIS SESSION:
# exit 0 (ran to completion, no scandir/timeout errors).
obsidian-reindex | waiting-on-port | 21600 | TBD | TBD | TBD | 0 | TBD | bash "$LIFEHACK_CODE_ROOT/system/tools/obsidian-reindex.sh"
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

> ⚠ **CORRECTED 2026-10-27:** this block is **Linux and Windows only**. macOS does not read it: a Mac
> installs launchd LaunchAgents built from the `jobs` block (see "How it works" above and
> `system/organism/manual.md`). The text below originally said "crontab on Mac/Linux".
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
# pulse: the ONE entry point. Every job in the ```jobs``` block above only ever runs because THIS
# line exists — install-schedulers.sh treats the row named "pulse" specially on Windows (it launches
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
`$HOME/claudeops-config` into nearly every job's command string — the single largest generalization
item its own port audit found). `install-schedulers.sh` sets this variable when it writes the
crontab/Task-Scheduler entry (derived from its own script location at install time), so the value is
always "wherever THIS clone actually is," never a guess. If you invoke `pulse.sh` by hand instead of
through the installed schedule, export it yourself first: `export LIFEHACK_CODE_ROOT="$(cd
"$(dirname "$0")/.." && pwd)"` from the repo root, or simply `cd` into the repo and run
`bash system/tools/pulse.sh` — the individual job commands above still need `$LIFEHACK_CODE_ROOT`
set for their own `bash "..."` calls to resolve, since `pulse.sh` runs each command through a plain
`bash -c`, which does not know the repo's location on its own.
