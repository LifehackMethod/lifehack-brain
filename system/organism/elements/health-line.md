---
element: health-line
title: "health-line — element detail (ground/base altitude)"
subsystem: hospital
altitude: base
record_type: organism-element
maturity_label: LIVE
generated_from:
  - system/tools/health_line.py
  - system/hooks/session_context_loader.sh
  - system/hooks/tests/test_session_context_loader.sh
  - system/tools/job-run.sh
  - system/jobs.md (```jobs block)
created_at: 2026-10-27
updated_at: 2026-10-27
status: active
authority: user
---

# health-line — element detail

> **Altitude = BASE.** `system/tools/health_line.py`: the one line printed first in every session. It is
> the BACKUP reader of job health; the alarm is the ntfy text from `job-run.sh` (`alarms.md`).
>
> **LADDER: ELEMENT. up -> `alarms.md` ; producer -> `job-run.md` ; ground truth ->
> `system/tools/health_line.py`.**

## What it does

Reads local files only (`health_line.py:4-9`; stdlib, no Drive, no subprocess) and prints EXACTLY ONE
line. Rewritten 2026-10-27 (task 2.1) from a ~940-line findings/ledger banner; the old text is in git
history (`health_line.py:22-24`). Measured: `jobs: 1 OK` in 0.01 s against the real state, inside the
plan's < 200 ms budget (the Drive read it replaced took a median of 9 s).

**Inputs.** The ENABLED rows of the ```jobs block in `system/jobs.md` (name, period = third
column, seconds; `#` rows and non-numeric periods skipped; `health_line.py:35-55`) and each job's folder
under `~/.config/lifehack/state/jobs/` (`:130`).

**Five states, checked in priority order; the first that matches wins** (`compute`, `:75-118`):

| # | Condition | Line |
|---|---|---|
| 1 | any job folder (enabled or not) has a non-empty `launch.err` (`:79-89`) | `jobs cannot find the code - open any desk once to repair` (the em dash form is in the code) |
| 2 | an enabled job has no `last-run` (`:91-94`) | `never ran: a, b` - never reported as OK (dead end [F2]) |
| 3 | `last-success` missing, or `age >= 2 x period` (`:96-107`) | `<n> overdue: job (9h), ...`; a missing one reads `job (never succeeded)` |
| 4 | a job's `last-run` shows `rc=75` (`:109-115`) | `stood down: <job> (<reason from last-run>)` |
| 5 | otherwise (`:118`) | `jobs: <n> OK` |

Ages print as minutes under 1 h, hours under 48 h, then days (`_age`, `:58-64`). The OK line does not
name the jobs; only the failure forms do.

**Overdue = 2 periods, on purpose.** It is the same instant `job-run.sh` sends "Job down"
(`job-run.sh:122`), so the line and the text never disagree about when a job went bad.

**Never raises, never exits non-zero.** Any exception becomes `job health: could not read (<Type>: <msg>)`
(`:135-137`), the line is whitespace-collapsed (`:137`), and the process always exits 0 (`:142-149`).
The hook adds its own guard: if the tool did not start or printed nothing, the session prints
`note: health_line.py did not run this session (rc=N) - job health unavailable`
(`session_context_loader.sh:143-153`). The hook prints it FIRST, ahead of the `=== Session context`
header (`:155`).

## Test seams (inert when unset; `health_line.py:123-133`)

`LIFEHACK_FAKE_NOW` (epoch seconds, digits only), `LIFEHACK_STATE_DIR` (root; jobs under `<root>/jobs`),
`LIFEHACK_JOBS_FILE` (manifest). Fixture overrides: `argv[1]` state dir, `argv[2]` manifest, or
`LIFEHACK_JOBS_STATE_DIR` / `LIFEHACK_JOBS_MANIFEST`. The loader test suite drives all five states plus
the worst-state-wins case (`system/hooks/tests/test_session_context_loader.sh:195-202` and above).

## Limits

- It only speaks when a session opens; the text covers the unattended hours.
- A job with `enabled` other than the literal `yes` is invisible to it (`:50`).
- The line reflects `last-success`'s mtime, which `job-run.sh` stamps only after the output check
  passes (`job-run.md`).
