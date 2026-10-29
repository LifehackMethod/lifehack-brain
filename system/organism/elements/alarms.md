---
element: alarms
title: "alarms — element detail (ground/base altitude)"
subsystem: alarms
altitude: base
record_type: organism-element
maturity_label: LIVE
gap_disposition: by-design
gap_disposition_note: "REBUILT 2026-10-27 (self-monitoring plan rev 4, Sprints 2-3, commit 0088c24). The detector-and-ledger design this file used to describe is retired; Hospital is now three small pieces (job-run.sh's local job state, health_line.py, job-run.sh's ntfy texts). The old design's claims, corrections and port banners are NOT carried forward: they described files that no longer exist. They are recoverable verbatim: git show 0088c24^:system/organism/elements/alarms.md."
generated_from:
  - system/tools/job-run.sh
  - system/tools/health_line.py
  - shared/notify/notify-send.sh
  - shared/notify/notify-governor.py
  - system/tools/emit_finding.py
  - system/tools/fault_ledger.py
  - system/tools/guard_fire_test_record.py
  - system/tools/guard-fire-test-run.sh
  - system/hooks/session_context_loader.sh
  - system/jobs.md (```jobs block)
  - "git: 0088c24 (3.1 retire the watcher machinery)"
created_at: 2026-08-04
updated_at: 2026-10-27
status: active
authority: user
---

> **RENAMED 2026-10-29 from `alarms.md` (operator's ruling).** This element is **ALARMS**: Bekim's "error handling"
> component — each job's state and error folder, the ntfy texts `job-run.sh` sends, and the session-start backup line.
> "Hospital" is no longer a subsystem name; it now means only the skills SOP's nurse-and-chart picture
> (`system/sops/skill-building-sop.md` PART 0). The old central findings store is retired (2026-10-29). Where the text
> below still says "Hospital", read "Alarms". Sibling: `cron.md` (what runs the jobs).


# hospital — element detail

> **Altitude = BASE.** What Hospital is today, source-traced. The one-line job: *a scheduled job that
> stopped working must be impossible to not-see.*
>
> **LADDER: ELEMENT. siblings -> `job-run.md` (the producer), `health-line.md` (the reader),
> `code-root.md` (how launchd finds the code), `cron.md` (the scheduler). Ground truth ->
> `system/tools/job-run.sh` + `system/tools/health_line.py`.**

## Superseded 2026-10-27 - what Hospital WAS

> **SUPERSEDED 2026-10-27 (task 4.3; the design change landed in commits `120bc68`/Sprint 2 and
> `0088c24`/Sprint 3).** Until then Hospital was a findings pipeline: a fleet of detector jobs (the
> `*-health` rows in `system/jobs.md`: system-health, sentinel-health, planning-health,
> backlog-health, item-store/email freshness, and a dead-man's-switch watching them) each wrote
> structured findings through `emit_finding.py` into a Drive-resident store; `findings_reader.py` and
> `health_line.py` ranked them into a session-start banner (capped at 3, oldest first);
> `fault_ledger.py` kept first-seen/last-seen and a closed-incident history (`faults.json`,
> `incidents.jsonl`); `fault_proposer.py` graded recurring faults INSTANCE / SUBSYSTEM / ORGANISM.
> It failed in the way it was built to prevent: the banner read a Drive store (median 9 s), a fleet of
> watchers had to be kept alive in turn, and a job that exited 0 on a skip looked healthy
> (dead end [F2], 166 occurrences). The record is not erased: the full prior text, including its
> dated corrections, is `git show 0088c24^:system/organism/elements/alarms.md`. What was done to it:
> the 13 watcher rows, 8 watcher runners, `fault_proposer.py`, `findings_deadman.py`, `recommend.py`
> were deleted (`0088c24`); `faults.json` and `incidents.jsonl` (and the Drive mirror `state/incidents/`)
> were MOVED to a dated archive folder, never removed; the session banner was rewritten (941 -> 149
> lines of `health_line.py`).

## What it is now (three pieces)

| Role | Piece | Where |
|---|---|---|
| **Producer** | `job-run.sh`'s per-job LOCAL state: `~/.config/lifehack/state/jobs/<job>/` holds `last-run`, `last-success`, `log` (last 20 runs), `errors/`, `alerted`, `launch.err` | `system/tools/job-run.sh:6-24` (header), `:55` (STATE) |
| **Reader** | `health_line.py`: one line at session start, five states, reads that folder only (no Drive, no subprocess). A BACKUP, not the alarm | `system/tools/health_line.py:10-16`; called at `system/hooks/session_context_loader.sh:143-155` |
| **Alarm** | ntfy texts sent by `job-run.sh` itself ("Job down: <job>", "Job recovered: <job>") through `shared/notify/notify-send.sh`, whose governor owns quiet hours, dedup and the per-source daily cap | `system/tools/job-run.sh:90-99` (notify), `:109-130` (alert_check) |

The design rule: the text is the alarm (it reaches a locked phone with no session open); the session
line is the backup for when the text was suppressed (quiet hours, daily cap, dedup) or never sent. Both
fire at the same instant on purpose: a failure pushes when last-success is missing or >= 2 x the job's
period old (`job-run.sh:122`), and `health_line.py` calls a job "overdue" at the same `age >= 2 * period`
(`health_line.py:104`). See `job-run.md` and `health-line.md` for each side.

## What is still in the tree, and why

Two former Hospital files are KEPT only because a live caller needs them (grep proof in the `0088c24`
commit message):

- `system/tools/emit_finding.py` - called by `system/tools/guard-fire-test-run.sh:102,123`.
- `system/tools/fault_ledger.py` - called through `system/tools/guard_fire_test_record.py:35` from
  `guard-fire-test-run.sh:130`.

Both exist for the guard-fire-test runner (row `guard-fire-test` is `off` in `system/jobs.md:253`;
the runner is kept, not deleted). They are NOT part of the job-health path: nothing in `job-run.sh` or
`health_line.py` imports either. `system/hooks/guard_findings_write.sh` (blocks writes to the findings
store) is likewise still registered. If guard-fire-test is ever retired, these two go with it.

## Gates and honest limits

- A job with no declared output check can never succeed (`job-run.sh:273`): exit 0 alone is never a
  success. This is the structural answer to dead end [F2].
- `health_line.py` never reports a job with no `last-run` as OK: "never ran: <jobs>" (`health_line.py:92-94`).
- Both the text and the line depend on the job having been scheduled at all. A scheduler that never
  fires leaves "never ran" (line) but no text; the installer says so:
  registration is not proof it fires (`system/tools/install-schedulers.sh:241`).
- The session line only appears when a desk is opened; the text does not need one.
- Only `email-summary-write` is enabled in the manifest today (`system/jobs.md:207`), so the
  fleet being watched is one job. Every `yes` row added later is watched automatically (both the
  installer and `health_line.py` read the same `jobs` block).
