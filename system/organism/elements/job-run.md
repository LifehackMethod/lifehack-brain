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
  - system/tools/runner-lock.lib.sh
  - system/tools/model.lib.sh
  - system/tools/job-texts.txt
  - system/job-names.txt
  - system/jobs.md (```jobs block)
created_at: 2026-10-27
updated_at: 2026-10-29
status: active
authority: user
---

# job-run — element detail

> **Altitude = BASE.** `system/tools/job-run.sh`: the ONE wrapper every scheduled job runs inside on
> macOS. A job's exit 0 is earned here, not claimed by the job.
>
> **LADDER: ELEMENT. up -> `alarms.md` ; siblings -> `cron.md` (what fires it), `code-root.md`
> (how it is found), `health-line.md` (who reads its state) ; ground truth -> `system/tools/job-run.sh`.**

> Re-traced against job-run.sh on 2026-10-29 (self-monitoring 5.11).

**Why it exists** (`job-run.sh:4-7`): "ran" is not "succeeded". A script that exits 0 on a skip, an absent
input or a swallowed error is dead end [F2], which failed 166 times. The wrapper runs the job's command,
then the OUTPUT CHECK DECLARED IN THE JOB'S ROW must pass before `last-success` is stamped. A job with no
declared check can never succeed.

**Invocation.** By launchd through the plist's launch line (`cron.md`, `job-run.sh:10`), by hand as
`bash system/tools/job-run.sh <job> [--if-overdue] [--force]` (`:56-65`). An unknown flag, or a name that is
empty or not `[a-z0-9-]`, exits 64 (`:63`, `:66-68`). `--force` is by-hand only: it runs a row whose
`enabled` is not `yes` exactly once, never edits the row, and sends no push (no "job down", no recovery,
no queue flush, no other-job check) (`:13-16`, `:324`).

## The run, in order

1. **State dir and capture.** State is `~/.config/lifehack/state/jobs/<job>/`, LOCAL, never Drive
   (`:73-74`). All output of the run goes to `run.current`, stderr included, so `launch.err` stays empty
   unless the launch line itself failed (`:86-88`). If `launch.err` is non-empty, its text is copied into
   the log and it is cleared (`:101-105`). `PATH` is extended and, from `job-fetch-hosts.txt`,
   `SAFE_FETCH_ALLOWLIST` is exported so a scheduled job's web reads are sealed to that host list
   (`:78-82`).
2. **Row lookup.** The job's row in the ```jobs block of `system/jobs.md` (awk on the fence;
   `name | enabled | interval | outcome | check | model | budget | source | command`, command last)
   (`:332-342`). No row: exit 1 (`:341`). The `model` column becomes `MODEL_TIER` (default `none`), `budget`
   becomes `JOB_RUN_BUDGET`, and a per-run calls file `calls.current` is created (`:349-354`). A
   `pending.current` list is created for bookmark files the shared fetch writes (`:358`). Interval not a
   number: exit 1 (`:359`).
3. **State-file sanity (5.9e).** A PRESENT but unreadable `last-success` (not exactly one ISO timestamp)
   exits 1 "corrupt state file", never treated as a first run (`:364-368`). A present `last-run` not shaped
   `<ISO time> rc=<n> ...` exits 1 and is left unrecorded so the bytes stay for inspection (`:369-373`). A
   missing file is normal. An empty `command` exits 1 unless the row is not `yes` and not `--force`
   (`:374`). `enabled` not `yes`: exit 75 "stood down", unless `--force` (`:375-378`).
4. **Per-job declarations.** `NEEDS` comes from the row's `source` (`gmail` -> `gws`) (`:383`). `WATCHDOG`
   seconds: default 3600; `email-summary-write` 1200; `sim-*` jobs 60 only while `LIFEHACK_STATE_DIR` is
   set (`:382-389`); `JOB_RUN_WATCHDOG` (digits) overrides (`:391`). The **output check** is read from the
   row's `check` column, `<path> ~ <extended regex>` split at the first ` ~ ` (`:393-409`): `$HOME`,
   `${HOME}`, `$LIFEHACK_CODE_ROOT`, `$JOB_SIM_DIR` and a leading `~` are expanded in the path
   (`:397-403`). It passes only if the file exists, is newer than the run start (`.run-start`), and some
   line matches (`grep -E`); a malformed check, a missing or stale file, a grep that cannot run, or no
   match returns 1 with a `[check]` line in the log (`:407-418`). An empty or `TBD` check returns 3 (`:406`).
5. **`--if-overdue`.** Only when `last-success` exists: run if its age is at least one period minus a
   grace of `INTERVAL/10` capped at 1800 s; otherwise exit 75 "not overdue" recorded NOWHERE (the call
   passes `record=no`, so `last-run` is not written) (`:422-428`). launchd gives a plist one argument list,
   so the scheduled fire and `RunAtLoad` cannot pass different flags; with the grace every scheduled fire
   is overdue while a login shortly after a success stands down (`:45-48`).
6. **Credentials** through `ingest-run.lib.sh` (`:431`): `ingest_load_gws` runs in a subshell when `NEEDS`
   has `gws`: no gws credentials: 75; pre-flight transient: 2; anything else non-zero: 1 (`:436-444`). A
   `claude` need would require the claude token (`:432-434`), but nothing sets `NEEDS` to `claude`
   (`:383`). (The library's own lock and watchdog are NOT used: its lock `exit 0`s on contention, the F2
   shape; its watchdog only launches `claude -p`, `:50-52`.)
7. **Lock.** `runner_lock_acquire` from `runner-lock.lib.sh` on `/tmp/lifehack-job-<job>.lock`, stale
   window `WATCHDOG + 300` s (`:447-452`). With `LIFEHACK_STATE_DIR` set the lock lives in
   `<root>/.lock-<job>` (`:448`). The lock records its owner pid: a dead owner's lock is taken at once; a
   LIVE owner is a stand-down 75, never 0; a lock present but unreadable is refused and named, exit 1; an
   alive owner on a lock older than the stale window is stolen loudly (pid-reuse guard)
   (`runner-lock.lib.sh:3-11`, `:51-60`; wrapper `:453-457`).
8. **Command under a watchdog.** `.run-start` is touched, then a 1 s sleep so outputs land strictly after
   it (under `LIFEHACK_FAKE_NOW`: no sleep, the start is stamped one fake second earlier) (`:460-465`). The
   command runs via `bash -c`; a background timer sends TERM then, 10 s later, KILL to the child and its
   children after `WATCHDOG` s, and is itself stopped when the command ends (`:466-476`).
9. **Model failure, then command rc.** If `run_model` left a reason in `calls.current.fail` and the rc is
   not 75 or 2, the run fails with that reason, even when the job swallowed its rc (an rc of 0 becomes 1)
   (`:478-482`; `model.lib.sh:43-45`). Command rc: 0 continue; 75 passes through as 75; 2 passes through
   as 2 (transient); anything else fails with that rc (`:483-488`).
10. **Output check, bookmarks, last-success.** Check returns 3: exit 1 "exit 0 alone is never a success";
    any other non-pass: exit 1 "output check failed" (`:491-493`). On a pass and not `--force`, each file
    in `pending.current` is promoted with `email_fetch.py --promote-pending`; a promotion failure exits 1
    with `last-success` NOT stamped (`:495-502`). Only then `last-success` is written and the run exits 0
    "output check passed" (`:503-505`). Its mtime is the clock everything else reads. On any other exit,
    `finish` deletes the pending files unpromoted (a bookmark moves only when the work is done)
    (`:317-322`).

Code locations: header and state map `job-run.sh:18-30`; args `:56-68`; state/capture `:73-88`;
launch.err `:101-105`; `finish` `:302-330`; row lookup `:332-358`; state-file sanity `:360-378`;
declarations `:382-391`; output check `:393-419`; `--if-overdue` `:421-428`; credentials `:430-444`; lock
`:446-457`; watchdog `:459-476`; model failure and rc `:478-488`; output check, promotion and last-success
`:490-505`.

## Exit contract (header `job-run.sh:32-36`)

| rc | meaning | `errors/` file? |
|---|---|---|
| 0 | the output check passed; nothing else ever exits 0 | no |
| 75 | stood down: row not enabled, not configured, not overdue, lock held by a live run | no |
| 2 | transient (network / Google pre-flight, or the job's own rc 2); retried next period | no |
| else | failed (including 64 for bad usage, which exits before `finish`) | yes, `errors/<time>.txt` = copy of the run log (`:313-316`) |

## `finish` (`job-run.sh:302-330`): the one exit path

In order: counts the run's model calls and seconds from the calls file (`:305-308`); records `last-run`
(`<ISO time> rc=<n> calls=<N> secs=<S> model=<tier> ccv=<claude version|none|stub|unknown> <reason>`,
`:311-312`) except when `record` is `no` (the not-overdue stand-down and a corrupt `last-run`); writes the
`errors/` file for a failure (not 0, 75, 2), and if the copy fails says so in the log (`:313-316`); drops
unpromoted pending bookmark files (`:317-322`); releases the lock (`:323`); then, unless `--force`, runs
**`flush_deferred`**, **`alert_check`** and **`watch_jobs`** (`:324`); appends the run to `log` and trims it
to the last 20 runs (`:325-327`); removes `run.current` and the calls files (`:328`).
`claude_version_short` (`:112-122`) asks `claude --version` only when the row names a model tier, capped at
10 s.

- **Flush on every run** (`flush_deferred`, `:181-186`): `notify-send.sh --flush-deferred` replays the
  governor's quiet-hours queue once quiet hours (22-07) are over and drops items older than 18 h
  (`notify-governor.py:79`, `:171`). A night failure is therefore delivered by the first run after 07:00.
  Fail-soft: a failed flush is logged and never changes the exit code.
- **Texts.** Every wording lives in `system/tools/job-texts.txt` (`<key> = <text>`), found at `:138`
  (`LIFEHACK_JOB_TEXTS` overrides); `job_text` falls back to a plain "something needs a look" line if the
  file or key is missing (`:140-146`). Keys job-run uses: `down`, `down_never`, `recovered`, `standdown`,
  `notrunning`, `notrunning_never`, `running_again`. A job's plain name comes from `system/job-names.txt`
  (beside the manifest; `LIFEHACK_JOB_NAMES` overrides), falling back to the code name with dashes turned
  into spaces (`:139`, `:147-154`). `{name}`, `{last_ok}` and `{since}` are filled by `render_text`, with
  times rendered by `when_text` as "2:10 PM", "yesterday 2:10 PM", a weekday, or "Mon D, time"
  (`:155-172`). Texts carry no title and never use priority `critical`, so none can break quiet hours
  (`:129-130`).
- **`notify`** (`:125-134`) sends through `shared/notify/notify-send.sh` (`JOB_RUN_NOTIFY` overrides) with
  source `job-run:<job>`, so the governor's cap of 3 per day applies per job; a recovery goes as priority
  `recovery` (cap-exempt, still respects quiet hours and dedup). It returns notify-send's exit code. A
  failed send logs "NOTIFY FAILED" and never changes the run's exit code.
- **`confirmed_send`** (`:173-176`): a text counts as sent only on notify-send rc 0 (sent, suppressed by
  the governor, or queued for quiet hours). Every marker below is written ONLY on a confirmed send; an
  unconfirmed send leaves the marker unwritten and is retried on the next run.
- **`alert_check <rc> [record]`** (`:269-300`):
  - Any result but 75 removes `standdown-since` (`:270`).
  - rc 0 and a `standdown-alerted` marker (and watching on): push ONE `running_again` recovery, identity
    `job-standdown-up:<job>:<incident>`, then remove the marker (`:271-274`).
  - rc 0 and an `alerted` marker: push ONE `recovered` text (priority `recovery`, identity
    `job-up:<job>:<incident>`) and remove the marker (`:275-280`). rc 0 otherwise: nothing.
  - rc 75: only `standdown_check` (below), never a "down" text (`:281`). No usable period: nothing
    (`:282`). `alerted` marker already present: nothing (one text per incident, `:283`).
  - A failure (including rc 2) pushes ONCE when `last-success` is missing (text `down_never`) or its age
    is `>= 2 x INTERVAL` (text `down`, naming the last success time) (`:284-293`; task 2.5d, the 2nd
    miss, the same instant `health_line.py` says "overdue", `health_line.py:110`). Identity
    `job-down:<job>:<incident>` where incident = the epoch at the failure (`:291-293`), so the governor's
    24 h identity dedup does not swallow the NEXT incident. The `alerted` marker
    (`<ISO time> rc=<n> <incident>`) is written only on a confirmed send (`:295-300`); the session line
    (`health-line.md`) is the backup.
  - The email runner's own alarms were removed (task 2.5c); `job-run.sh` is the one alarm.
- **`standdown_check`** (`:198-211`; 5.10(2)): a streak marker `standdown-since` (its mtime = the first
  recorded 75 of the run of 75s) is created on the first recorded 75 for a row that is `yes`; a run that
  records nothing (`record=no`, `--force`) neither starts nor extends it. Once the streak is longer than
  `SD_MULT x INTERVAL` (2x, `:190`), ONE `standdown` text goes out (identity `job-standdown:<job>:<epoch>`)
  and `standdown-alerted` is written on a confirmed send. A row that is not `yes` is never texted.
- **`watch_jobs` / `watch_others`** (`:214-266`; 5.10(3)): after the job's own work, a fail-safe subshell
  reads every row of the jobs block once (`:252-259`). For each `yes` row other than this job, the
  reference time is the mtime of its `last-run`, else its `last-success`, else (a never-run row, while
  `NEVER_RAN_WATCHED=1`) the first time any job saw it, kept in `jobs/.watch/<name>.seen` (`:220`,
  `:229-238`). If older than `WATCH_MULT x interval` (2x, `:191`) and no `.watch/<name>.alerted` marker
  exists, ONE `notrunning` (or `notrunning_never`) text goes out, source `job-run:<that job>`, identity
  `job-down:<name>:<epoch>` (`:239-246`). When the row is fresh again and a marker exists, ONE
  `running_again` recovery goes out (identity `job-up:<name>:<incident>`) and the marker is removed
  (`:247-251`). A row that is not `yes` has its markers dropped and is never watched (`:230`). Any watch
  error is logged ("WATCH ERROR" / "WATCH STEP FAILED") and never changes this run's exit code
  (`:224-225`, `:262-266`).

## Test seams (all inert when unset)

| Seam | Effect |
|---|---|
| `LIFEHACK_FAKE_NOW` | epoch seconds, digits only (`:92`). Every "now" and age reads it; files whose mtime is a clock (`last-success`, `last-run`, `alerted`, the stand-down and watch markers) are stamped to it; no real 1 s sleep (`:461-462`). NOT an ISO time. |
| `LIFEHACK_STATE_DIR` | replaces `~/.config/lifehack/state` (`:73`); also moves the lock (`:448`); also enables `sim-*` watchdog (`:388`) and `JOB_RUN_NO_WATCH` (`:189`). |
| `LIFEHACK_JOBS_FILE` | replaces the manifest (`:72`). |
| `LIFEHACK_JOB_TEXTS` / `LIFEHACK_JOB_NAMES` | replace `job-texts.txt` / `job-names.txt` (`:138-139`). |
| `LIFEHACK_NOTIFY_LOG` | read by `notify-send.sh:156-162`, AFTER the governor: appends title, message, identity, priority for every send the governor allowed. |
| `JOB_RUN_WATCHDOG` | digits only: shortens the watchdog for a by-hand kill test (`:391`). launchd never sets it. |
| `JOB_RUN_NOTIFY` | alternate notify-send path (`:126`, `:182`). Related: `NOTIFY_STATE_FILE` for the governor's state (`:180`). |
| `JOB_RUN_NO_WATCH` | `1` switches off the stand-down text and the not-running watch, honoured only while `LIFEHACK_STATE_DIR` is set (`:187-189`). |
| `LIFEHACK_MODEL_STUB` | makes the recorded `ccv` read `stub` (`:114`). |

The rig `system/tools/tests/job-sim.sh` drives the real `job-run.sh`, `health_line.py`, `notify-send.sh`
and `notify-governor.py` through these seams (`job-sim.sh:4-11`, `:34-35`).

## Limits

- The output check is per row: any enabled row whose `check` is empty or `TBD` fails with "no output check
  declared" (`:406`, `:492`). Only `email-summary-write` has a per-job watchdog (1200 s); every other job
  gets 3600 s (`:382-385`). Only `source` `gmail` sets `NEEDS` (`:383`).
- A model-using job's failure is only seen if it goes through `run_model` (`:478-482`); a job that fails
  some other way and exits 0 is caught only by its output check.
