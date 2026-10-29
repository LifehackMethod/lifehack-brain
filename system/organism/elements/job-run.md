---
element: job-run
title: "job-run — element detail (ground/base altitude)"
subsystem: automation
altitude: base
record_type: organism-element
maturity_label: LIVE
generated_from:
  - system/tools/job-run.sh
  - system/tools/ingest-run.lib.sh
  - system/tools/health_line.py
  - system/tools/install-schedulers.sh
  - shared/notify/notify-send.sh
  - shared/notify/notify-governor.py
  - system/tools/tests/job-sim.sh
  - system/jobs.md (```jobs block)
created_at: 2026-10-27
updated_at: 2026-10-27
status: active
authority: user
---

# job-run — element detail

> **Altitude = BASE.** `system/tools/job-run.sh`: the ONE wrapper every scheduled job runs inside on
> macOS. A job's exit 0 is earned here, not claimed by the job.
>
> **LADDER: ELEMENT. up -> `alarms.md` ; siblings -> `cron.md` (what fires it), `code-root.md`
> (how it is found), `health-line.md` (who reads its state) ; ground truth -> `system/tools/job-run.sh`.**

**Why it exists** (`job-run.sh:2-8`): "ran" is not "succeeded". A script that exits 0 on a skip, an absent
input or a swallowed error is dead end [F2], which failed 166 times. The wrapper runs the job's command,
then a PER-JOB OUTPUT CHECK must pass before `last-success` is stamped. A job with no declared check can
never succeed.

**Invocation.** By launchd through the plist's launch line (`cron.md`), by hand as
`bash system/tools/job-run.sh <job> [--if-overdue]`. A name that is empty or not `[a-z0-9-]` exits 64.

## The run, in order

1. **State dir and capture.** State is `~/.config/lifehack/state/jobs/<job>/`, LOCAL, never Drive. All
   output of the run goes to `run.current`, stderr included, so `launch.err` stays empty unless the
   launch line itself failed. If `launch.err` is non-empty, its text is copied into the log and it is
   cleared: reaching this line proves the pointer works again.
2. **Row lookup.** The job's row in the ```jobs block of the manifest (awk on the fence;
   `name | enabled | interval | outcome | check | model | budget | source | command`, command last). No row: exit 1. Interval not a number: exit 1. `enabled`
   not `yes`: exit 75 "stood down".
3. **Per-job declarations.** `NEEDS` comes from the row's `source` (`gmail` -> `gws`); `WATCHDOG`
   seconds (default 3600; email 1200). The **output check** is read from the row's `check` column,
   `<path> ~ <extended regex>`: it passes only if the file exists, is newer than the run start, and some
   line matches. An empty or `TBD` check exits 1 "no output check declared". email-summary-write's check
   requires its worklog to carry `v2 write DONE` with `written` or `unchanged` of at least 1: write_v2
   skips unchanged threads and exits 0 on a hard stop, so an empty result is not a success.
4. **`--if-overdue`.** Only when `last-success` exists: run if its age is at least one period minus a
   grace of `INTERVAL/10` capped at 1800 s; otherwise exit 75 "not overdue" WITHOUT recording
   `last-run`. launchd gives a plist one argument list, so the scheduled fire and `RunAtLoad` cannot
   pass different flags; with the grace every scheduled fire is overdue while a login shortly after a
   success stands down.
5. **Credentials** through `ingest-run.lib.sh`: no gws credentials: 75; gws pre-flight transient: 2;
   pre-flight broke: 1. (The library's own lock and watchdog are NOT used: its lock `exit 0`s on
   contention, the F2 shape; its watchdog only launches `claude -p`.)
6. **Lock.** `mkdir /tmp/lifehack-job-<job>.lock`; held by another run: exit 75, never 0. A lock older
   than `WATCHDOG + 300` s is stale and stolen. With `LIFEHACK_STATE_DIR` set the lock lives in
   `<root>/.lock-<job>`.
7. **Command under a watchdog.** `.run-start` is touched (then a 1 s sleep so outputs land strictly
   after it); the command runs via `bash -c`; a background timer sends TERM then, 10 s later, KILL to
   the child tree after `WATCHDOG` s, and is itself stopped when the command ends. Command rc: 0
   continue; 75 passes through as 75; 2 passes through as 2 (transient); anything else fails with that rc.
8. **Output check, then last-success.** No `check_*` function: exit 1 "exit 0 alone is never a
   success". Check fails: exit 1. Only a pass writes `last-success` and exits 0. Its mtime is the clock
   everything else reads.

> ⚠ **CHANGED SINCE THIS WAS TRACED (2026-10-29 note; full re-trace after the self-monitoring Gate 5).** Steps 5–8 and
> the line numbers below describe the 2026-10-27 wrapper. Since then: the check is read from the ROW's `check` column
> (`<path> ~ <ERE>`, 5.1), not a `check_*` function · a model failure recorded by `run_model` fails the run even if the
> job swallowed its rc (5.3) · a lock records its owner pid, a dead owner's lock is taken at once and a live owner is a
> stand-down 75 (5.9h) · a corrupt state file is refused and named, never "start fresh" (5.9e) · a bookmark advances only
> when the work is done (5.9f). Built 2026-10-29 (5.10): texts retry until confirmed sent; a persistent stand-down texts
> once; each run checks the other jobs and texts once for one that is not running. Until the re-trace, `job-run.sh`
> itself and `manual.md` → CRON AND ALARMS are the truth.

Code locations: state `job-run.sh:54-55`; launch.err handling `:80-84`; row lookup `:150-162`;
declarations `:166-175`; `--if-overdue` `:207-214`; credentials `:217-229`; lock `:231-243`; watchdog
`:245-266`; output check and last-success `:269-277`.

## Exit contract (header `job-run.sh:20-24`)

| rc | meaning | `errors/` file? |
|---|---|---|
| 0 | the output check passed; nothing else ever exits 0 | no |
| 75 | stood down: row not enabled, not configured, not overdue, lock held | no |
| 2 | transient (network / Google pre-flight); retried next period | no |
| else | failed | yes, `errors/<time>.txt` = copy of the run log |

## `finish` (`job-run.sh:132-148`): the one exit path

Records `last-run` (`<ISO time> rc=<n> <reason>`; skipped for the not-overdue stand-down), writes the
`errors/` file for a failure (not 0, 75, 2), releases the lock, **flushes the notify queue**, runs
**`alert_check`**, appends the run to `log` and trims it to the last 20 runs (`:144`).

- **Flush on every run** (`flush_deferred`, `:102-107`; task 2.5a): every run of any job calls
  `notify-send.sh --flush-deferred`, which replays the governor's quiet-hours queue once quiet hours
  (22-07) are over and drops items older than 18 h (`notify-governor.py:71`). A night failure is
  therefore delivered by the first run after 07:00. Fail-soft.
- **`alert_check <rc>`** (`:109-130`):
  - rc 0 and an `alerted` marker exists: push ONE recovery ("Job recovered: <job>", priority
    `recovery`, identity `job-up:<job>:<incident>`) and remove the marker.
  - rc 75: nothing, ever. No usable period: nothing. Marker already present: nothing (one text per
    incident).
  - A failure (including rc 2) pushes ONCE when `last-success` is missing (a job that never succeeded
    pages on its first failure) or its age is `>= 2 x INTERVAL` (`:122`; task 2.5d, the 2nd miss, the
    same instant `health_line.py` says "overdue"). Title "Job down: <job>"; the text names the exit
    code, the age of the last success and where the error file is.
  - **Per-incident identity:** `job-down:<job>:<incident>` where incident = the epoch at the failure
    (`:125`). The marker already dedups within an incident, and the governor's 24 h identity dedup must
    not swallow the NEXT incident. The `alerted` marker (`<ISO time> rc=<n> <incident>`) is written even
    when the governor suppresses the text, so the session line (`health-line.md`) is the backup.
  - Sent via `notify()` (`:90-99`) to `shared/notify/notify-send.sh` with source `job-run:<job>`, so the
    governor's cap of 3 per day applies per job (task 2.5b); a recovery is cap-exempt but still respects
    quiet hours and dedup. A push that fails logs one line and never changes the exit code.
  - The email runner's own alarms were removed (task 2.5c); `job-run.sh` is the one alarm.

## Test seams (all inert when unset)

| Seam | Effect |
|---|---|
| `LIFEHACK_FAKE_NOW` | epoch seconds, digits only (`:71`). Every "now" and age reads it; files whose mtime is a clock (`last-success`, `last-run`, `alerted`) are stamped to it; no real 1 s sleep. NOT an ISO time. |
| `LIFEHACK_STATE_DIR` | replaces `~/.config/lifehack/state` (`:55`); also moves the lock; also enables `sim-*` jobs (`:172`). |
| `LIFEHACK_JOBS_FILE` | replaces the manifest (`:54`). |
| `LIFEHACK_NOTIFY_LOG` | read by `notify-send.sh:126-131`, AFTER the governor: appends title, message, identity, priority for every send the governor allowed. |
| `JOB_RUN_WATCHDOG` | digits only: shortens the watchdog for a by-hand kill test (`:174-175`). launchd never sets it. |
| `JOB_RUN_NOTIFY` | alternate notify-send path (`:91`, `:103`). Related: `NOTIFY_STATE_FILE` for the governor's state. |

The rig `system/tools/tests/job-sim.sh` drives these (died-and-stayed-dead, died-then-recovered, hang
kills and records, two jobs, night failure delivered once after 07:00, and a leak check that a full run
leaves the real state untouched).

## Limits

- Only `email-summary-write` has a declared output check and `NEEDS`; any other job enabled in the
  manifest fails with "no output check declared" until one is added to `job-run.sh`.
- The watchdog and the scheduled-time fire were proven by forced tests, not by waiting for them.
