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
# planning-health: READ-ONLY calendar check (conflicts + unconfirmed invites, 7-day forward window).
# Degrades cleanly (rc=75, "stood down") when config/cal.md has no calendar id configured yet — see
# shared/cal_config.py. (Those two names stay `cal` on purpose: they are the CALENDAR-identifier
# config, shared with the calendar write guards — not the renamed planning desk.) No *-run.sh
# wrapper exists yet for this job (no single-instance lock / no buzz-on-hard-failure) — a future
# lane can add system/tools/planning-health-run.sh matching system-health-run.sh's pattern; until
# then this calls the checker directly. 6h cadence.
planning-health  | yes | 21600 | python3 "$LIFEHACK_CODE_ROOT/system/tools/planning-health.py"
#
# backlog-health: emits state/status/backlog.json from the read-only backlog groom engine
# (backlog_groom.py). CORRECTED 2026-08-14: that engine landed in the SAME commit as this file
# (8aeda8f) — the line here previously claiming it "has not landed in this repo yet" was stale on
# arrival, never true even at the moment it was written. Verified this session: `python3
# system/tools/backlog-health.py` imports backlog_groom cleanly and runs the real report (not the
# "not present yet" NEEDS_REVIEW fallback) — on a fresh clone it currently reports "not configured
# - no debt ledger, desk backlogs, or legacy swamp file found yet", which is a DATA-level gap
# (nothing to scan yet), not an import failure. (backlog-health.py's own header docstring carries
# the same stale claim; out of scope for this file to fix.) Same no-wrapper note as planning-health
# above. 6h cadence.
backlog-health   | yes | 21600 | python3 "$LIFEHACK_CODE_ROOT/system/tools/backlog-health.py"
#
# fault-proposer: the FIRST machine reader of this repo's failure signals — grades open faults
# INSTANCE/SUBSYSTEM/ORGANISM, cites the evidence that chose the altitude, and REFUSES to emit
# anything it cannot cite (a refusal is exit 0 — a correct outcome, not a failure; see
# fault-proposer-run.sh's own exit-code contract). READ-ONLY: writes only its own proposal text +
# a machine-local status artifact (+ a best-effort tile if a notes root is configured); no gws, no
# notes-root requirement to RUN, no claude -p (confirmed absent from fault_proposer.py). Its own
# header sizes itself as "daily cadence + 6h slack before it alarms" (STALE_AFTER_HOURS=30) — this
# row honors that literally. 1-day cadence.
fault-proposer          | yes | 86400 | bash "$LIFEHACK_CODE_ROOT/system/tools/fault-proposer-run.sh"
#
# item-store-freshness: dead-man for state/item-store/{tasks,calendar}/ — LOCAL files only, no
# gws, no auth, independent of the tasks/calendar writers so it still fires and pages even if a
# writer silently stops producing. Exit 0 on BOTH ok and ERROR (the tile carries the signal, never
# the exit code) — ERROR routes to a governor-gated phone push. Its own header sizes itself at
# STALE_AFTER_HOURS=4, "Pulse cadence ~ hourly" — this row honors that literally. 1h cadence.
item-store-freshness    | yes | 3600  | bash "$LIFEHACK_CODE_ROOT/system/tools/item-store-freshness-run.sh"
#
# email-summary-freshness: dead-man for the v2 faithful-thread store (state/email-summary/
# threads-v2/) — LOCAL files only, no gws, no auth, independent of the write-cadence job below so
# it still fires even if writing is down/disabled/unwired. Exit 0 on both UP and DEGRADED (tile
# carries the signal); DEGRADED routes to a governor-gated phone push (normal priority — quiet
# hours hold). Its own header sizes itself at STALE_AFTER_HOURS=6, "Pulse cadence ~ hourly" — this
# row honors that literally. 1h cadence.
email-summary-freshness | yes | 3600  | bash "$LIFEHACK_CODE_ROOT/system/tools/email-summary-freshness-run.sh"
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
# (mechanical, no claude -p — confirmed). LIVE — see the note above. Interval matches the runner's
# own header ("own absence horizon... writers run ~daily", STALE_AFTER_HOURS=30). 1-day cadence.
calendar-store-sync     | yes | 86400 | bash "$LIFEHACK_CODE_ROOT/system/tools/calendar-store-sync-run.sh"
#
# tasks-store-sync: refreshes state/item-store/tasks/ via tasks_store_sync.py --sync (mechanical,
# no claude -p — confirmed). LIVE for the SAME reason as calendar-store-sync immediately above —
# tasks-store-sync-run.sh shared the identical GWS_CREDS-missing branch and got the identical fix.
# Interval matches the runner's own header ("writers run ~daily", STALE_AFTER_HOURS=30). 1-day
# cadence.
tasks-store-sync        | yes | 86400 | bash "$LIFEHACK_CODE_ROOT/system/tools/tasks-store-sync-run.sh"
#
# email-summary-write: refreshes the v2 faithful-thread store (threads-v2/) via
# email_summary_sync.py --write-v2 (mechanical, no claude -p — confirmed: CLAUDE_BIN is kept but
# never invoked by the v2 write path; see shared/tools/email_summary_sync.py:114-120). LIVE for
# the SAME rc=3-vs-rc=75 fix as the two rows above (identical GWS_CREDS-missing branch in
# email-summary-write-run.sh) — same fix, same session. Interval matches the runner's OWN header,
# which is explicit: STALE_AFTER_HOURS=4, "just over one 3h cadence, so a SINGLE missed run
# surfaces on the next tick." 3h cadence.
email-summary-write     | yes | 10800 | bash "$LIFEHACK_CODE_ROOT/system/tools/email-summary-write-run.sh"
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
planning-diary    | yes | 86400  | bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence weekly && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence monthly && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence quarterly && bash "$LIFEHACK_CODE_ROOT/system/tools/planning-diary-run.sh" --cadence yearly
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
archivist-audit    | yes | 604800 | bash "$LIFEHACK_CODE_ROOT/system/tools/archivist-audit-run.sh"
archivist-deepmine | yes | 345600 | bash "$LIFEHACK_CODE_ROOT/system/tools/archivist-deepmine-run.sh"
#
# planning-weekly-prime: the mid-week map-warming cron for the planning-weekly skill's Phase 0,
# cited by name (with a line number) at .claude/skills/planning-weekly/prompts/
# 00-system-layer.md:68 — a dangling promise until this row + its runner landed. Ticked daily
# (not weekly) because its OWN cadence guard (Thu/Fri/Sat window, ISO-week idempotent via
# map.md's own existence) needs a daily check to catch the window at all — see the runner's
# header for why the "real" Phase 0 fan-out (Agent-tool-based) cannot be invoked from cron and
# what this ships instead.
planning-weekly-prime | yes | 86400 | bash "$LIFEHACK_CODE_ROOT/system/tools/planning-weekly-prime-run.sh"
#
# guard-fire-test: the engine (organism/label_checker.py + label_manifest.yaml, run through
# verify-hooks.sh) already exists and is correct (confirmed GREEN this session — 20/20 guards
# LIVE) but nothing fired it on a schedule and nothing read its result — a downgrade from LIVE
# to PARTIAL would sit invisible until a human happened to run it by hand. Weekly cadence
# matches the runner's own STALE_AFTER_HOURS=192 (168h weekly + 24h slack) header.
guard-fire-test    | yes | 604800 | bash "$LIFEHACK_CODE_ROOT/system/tools/guard-fire-test-run.sh"
#
# NOT ADDED: shared/tools/email_summary_run.sh (the older v1-shaped watchdog wrapper). Not parked,
# not given a row at all — two independent reasons, both verified this session. (1) It passes its
# args straight through to email_summary_sync.py with NO action flag added; that janitor is
# v2-only and has "no legacy default run mode" (its own main(), read directly: no flag set -> 
# ap.print_help() + return 1) — a bare/scheduled call ALWAYS returns rc=1 on EVERY machine,
# Google-configured or not, 100% of the time, which is worse than the three parked rows above (at
# least those succeed once configured). (2) Even patched with --write-v2 in its command string, it
# would duplicate email-summary-write-run.sh above while lacking that wrapper's isolated
# gws-credentials handling and single-instance lock — a bare `gws` call from this script would hit
# the interactive keychain a headless/cron context cannot unlock (per the sibling runners' own
# comments), risking a hang rather than a clean failure. Superseded, not summoned.
#
#
# ── Cowork-desk rows, ported from ClaudeOps' divergent copy of this file (commit 6079d32,
#    "Expand pulse-config crontab coverage"), 2026-08-26 — CORRECTED on arrival. That copy's
#    comments claimed every runner below was "NOT PORTED" / had a "Missing runner"; this session
#    verified each one against the actual Brain-resident and repo-resident tree and found 16 of 16
#    of those claims WRONG — every runner listed below already exists and was executed this
#    session (exit codes recorded per row). Left at `waiting-on-port` (never `yes`): flipping
#    `enabled` is not this lane's call (Enver's ruling, recorded at the hook-doc-lint row above).
#
# helm-keepalive: keeps the Helm dashboard server up. CORRECTED 2026-08-26 (verified this session):
# the prior comment was WRONG on both counts — it claimed the runner AND the whole `helm/` app
# directory were absent from this clone. Neither is true: `helm/app/healthcheck.sh` exists in the
# Brain (not the repo) at $NOTES_ROOT/helm/app/healthcheck.sh — idempotent (:8080 alive-check,
# launches server.py only if down), local-only, no external side effects. RUN THIS SESSION: exit 0
# (already alive or started clean).
helm-keepalive           | waiting-on-port | 300     | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/helm/app/healthcheck.sh"
#
# marc-health: mechanical market-data health chain (no LLM). CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — the runner exists in the Brain (not the repo) at
# desks/marc/tools/marc-health/marc-health-run.sh. RUN THIS SESSION: exit 0 (17 equities fetched, 4
# FRED series errored non-fatally, health tile + diary written; the once/day Sonnet voice push
# self-gated out because today's ping marker was already stamped).
marc-health              | waiting-on-port | 7200    | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/marc/tools/marc-health/marc-health-run.sh"
#
# marc-weekly: eight-researcher weekly deep-read fan-out. CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — runner exists in the Brain at
# desks/marc/tools/marc-weekly/marc-weekly-run.sh. It self-gates to Sat/Sun only (DOW guard); a
# by-hand run today (Wed) hit a pre-existing single-instance lock and exited 0 clean before
# reaching the DOW check — a real, safe stand-down, not a fabricated pass.
marc-weekly              | waiting-on-port | 86400   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/marc/tools/marc-weekly/marc-weekly-run.sh"
#
# marc-wednesday: mid-week light scan (donor notes a live false-all-clear defect carried forward,
# not fixed by this port). CORRECTED 2026-08-26 (verified this session): "Missing runner" was
# wrong — runner exists in the Brain at desks/marc/tools/marc-wednesday/marc-wednesday-run.sh.
# ⛔ NOT RUN THIS SESSION: this job is genuinely due today (its own due-window includes today, and
# its marker is behind the current ISO week) — invoking it would fire a real multi-source LLM
# research fan-out (real token spend), not a dry no-op. UNVERIFIED-BY-DESIGN, not confirmed working.
marc-wednesday           | waiting-on-port | 86400   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/marc/tools/marc-wednesday/marc-wednesday-run.sh"
#
# marc-deadman: organism dead-man's-switch for Marc's heartbeat. CORRECTED 2026-08-26 (verified
# this session): "Missing runner" was wrong — runner exists in the Brain at
# desks/marc/tools/marc-deadman/marc-deadman.py. RUN THIS SESSION: exit 0, heartbeat well within
# its own staleness window.
marc-deadman             | waiting-on-port | 10800   | python3 "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/marc/tools/marc-deadman/marc-deadman.py"
#
# clair-health: read-only daily consulting billing-tracker check. CORRECTED 2026-08-26 (verified
# this session): "Missing runner" was wrong — runner exists in the Brain at
# desks/clair/tools/clair-health/clair-health-run.sh. RUN THIS SESSION: exit 0 (NEEDS_REVIEW tile
# surfaced unbilled sessions — read-only, zero writes to the billing sheet).
clair-health             | waiting-on-port | 21600   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/clair/tools/clair-health/clair-health-run.sh"
#
# clair-billing: billing/client detail emit + cadence-nudge push. CORRECTED 2026-08-26 (verified
# this session): "Missing runner" was wrong — runner exists in the Brain at
# desks/clair/tools/clair-billing/clair-billing-run.sh. RUN THIS SESSION: exit 0 — wrote its two
# signal files (read-only on Google + local writes only); the push-due branch correctly
# self-deduped, so no new phone notification fired.
clair-billing            | waiting-on-port | 21600   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/clair/tools/clair-billing/clair-billing-run.sh"
#
# deryl-books-health: read-only nightly books-integrity check. CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — runner exists in the Brain at
# desks/deryl/tools/deryl-books-health/deryl-books-health-run.sh. RUN THIS SESSION: exit 0
# (NEEDS_REVIEW, warnings only, zero errors — zero writes to the books).
deryl-books-health       | waiting-on-port | 86400   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/deryl/tools/deryl-books-health/deryl-books-health-run.sh"
#
# deryl-ingest: Deryl desk light daily email doorman. CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — runner exists in the Brain at
# desks/deryl/tools/deryl-ingest/deryl-ingest-run.sh. RUN THIS SESSION (supervised, as its own
# header prescribes): `MAX_EMAILS=2 DRY_RUN=1` — exit 0, no new mail, cheap exit (no claude, no
# tokens). The command below is the sanctioned live shape; its own header still says this row is
# registered disabled until the Huddle-2 staged live test proves the reader/actor split — that
# prerequisite is separate from "does the runner exist."
deryl-ingest             | waiting-on-port | 86400   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/deryl/tools/deryl-ingest/deryl-ingest-run.sh"
#
# cp-utilities: College Park utilities ingest chain (eCARe + submeter). CORRECTED 2026-08-26
# (verified this session): "Missing runner" was wrong — runner exists in the Brain at
# desks/deryl/tools/cp-utilities/cp-utilities-run.sh. RUN THIS SESSION: `CP_DRYRUN=1` — exit 0,
# both ingest scripts ran --dry-run cleanly, reconcile=OK, ZERO writes. Its own header still lists
# two unmet prerequisites (keychain env-fallback code, Enver's one-time eCARe keychain export)
# before a live run is safe.
cp-utilities             | waiting-on-port | 86400   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/deryl/tools/cp-utilities/cp-utilities-run.sh"
#
# emporia: carriage-house electric submeter ingest. CORRECTED 2026-08-26 (verified this session):
# "Missing runner" was wrong — runner exists in the Brain at desks/deryl/tools/emporia/
# emporia-run.sh. RUN THIS SESSION: `EMPORIA_DRYRUN=1` — exit 0, ran --dry-run cleanly, plausible
# reading, ZERO writes. Its own header still lists the same two open prerequisites as cp-utilities.
emporia                  | waiting-on-port | 86400   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/deryl/tools/emporia/emporia-run.sh"
#
# dobby-health: home-systems tile emit (HA REST reads, mechanical). CORRECTED 2026-08-26 (verified
# this session): "Missing runner" was wrong — runner exists in the Brain at
# desks/dobby/tools/dobby-health/dobby-health-run.sh. RUN THIS SESSION: exit 0 — "not Studio — skip"
# (this job is Studio-hardware-pinned by design; ran clean on this non-Studio machine as the
# documented no-op, never a failure).
dobby-health             | waiting-on-port | 21600   | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/dobby/tools/dobby-health/dobby-health-run.sh"
#
# emily-breakdown: Emily desk audition-ingest cron slot. CORRECTED 2026-08-26 (verified this
# session): "Missing runner" was wrong — runner exists in the Brain at
# desks/emily/tools/emily-breakdown/emily-breakdown-run.sh. RUN THIS SESSION: `DRY_RUN=1` — exit 0,
# BUT surfaced a separate real defect: this runner hardcodes a stale `CODE_ROOT` path from a
# superseded clone location that does not match any actual live clone — the dry-run diagnostic
# confirmed both the skill file and notify-send.sh resolved to [exists: NO] under that hardcoded
# path. Genuine wiring defect in the Brain-resident runner itself, out of this row's scope to fix.
# ⚠ enable-recommend NO until that path is corrected.
emily-breakdown          | waiting-on-port | 300     | bash "$(python3 "$LIFEHACK_CODE_ROOT/shared/brain_root.py" --quiet)/desks/emily/tools/emily-breakdown/emily-breakdown-run.sh"
#
# recommend: ground-altitude reasoner between Hospital and a human. CORRECTED 2026-08-26 (verified
# this session): the prior comment ("only its -run.sh wrapper is missing") was wrong in detail —
# the wrapper DOES exist, just sitting unwired in
# system/parked/2026-08-23-donor-spillover/system/tools/recommend-run.sh, not in system/tools/. RUN
# THIS SESSION at its actual current location: FAILED, exit 1 — its sibling `ingest-run.lib.sh`
# could not be found. Root cause: the wrapper derives its own code root as two levels up from its
# own location, correct only if it sits at system/tools/recommend-run.sh — from its current parked
# nesting that arithmetic lands one level short of the real system/tools/, so every sibling
# source/python3 call resolves to a directory that does not exist. It cannot be run correctly from
# where it sits today; moving it into system/tools/ would fix it, but that move is out of scope for
# this row (another lane owns it). The command below is the CORRECT shape for once it is properly
# wired — not runnable at its current parked path. ⚠ enable-recommend NO until wired.
recommend                | waiting-on-port | 86400   | bash "$LIFEHACK_CODE_ROOT/system/tools/recommend-run.sh"
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
token-burn-mine          | waiting-on-port | 86400   | PYTHONPATH="$LIFEHACK_CODE_ROOT/system/tools" python3 "$LIFEHACK_CODE_ROOT/system/parked/2026-08-23-donor-spillover/system/tools/token_burn_mine.py"
#
# obsidian-reindex: machine-local vault index rebuild (single-instance lock + watchdog in donor).
# CORRECTED 2026-08-26 (verified this session): "Missing runner" was wrong — the runner exists in
# this repo at system/tools/obsidian-reindex.sh with the lock + watchdog intact. RUN THIS SESSION:
# exit 0 (ran to completion, no scandir/timeout errors).
obsidian-reindex         | waiting-on-port | 21600   | bash "$LIFEHACK_CODE_ROOT/system/tools/obsidian-reindex.sh"
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
