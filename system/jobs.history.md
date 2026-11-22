# Scheduled jobs — history

> **History file — archived text, not live guidance.** Created 2026-11-14 (fine-china edit pass, round three
> 'lowerbooks'). Each passage below was moved word for word out of `system/jobs.md` (Batch 4 item 3: retired and
> struck text goes to history, never deleted). Line numbers are those of the frozen copy
> `freeze-2026-11-14/jobs.2026-11-14.md`. Read the live file for what is true today.

> Comment lines that came from inside the ```jobs``` / ```crontab``` blocks are reproduced here as plain text;
> no scheduler reads this file.

## G2-105 · moved 2026-11-14 · frozen L17-22

Reason: the 'NEW FILE' banner, stale (K12); one present-tense sentence stays live.

````
> ⚠ **NEW FILE — did not exist anywhere in this repo before this session.** `pulse.sh` and
> `install-schedulers.sh` cannot do anything without it; **this is the smallest version that makes
> both scripts real**, not a full replay of every job the donor system ever scheduled. Other
> categories' ported runners (ingest, planning's other jobs, archivist, etc.) get their own rows appended
> here **as their own lane ports them** — this file is shared, additive territory, not owned end-to-
> end by one lane. See the commented template row at the bottom of the `jobs` block.
````

## G2-106 · moved 2026-11-14 · frozen L26-31

Reason: the 2026-10-27 CORRECTED banner and its 'used to say' (K12; Batch 4 item 3); its facts are restated in present tense.

````
> ⚠ **CORRECTED 2026-10-27:** the text below used to say Pulse runs on Mac via `cron`. That is no
> longer true. **On macOS, scheduled jobs run through launchd:** `install-schedulers.sh --install`
> writes one `~/Library/LaunchAgents/ai.lifehack.<job>.plist` per row of the `jobs` block whose
> enabled column is `yes`, and each plist runs that job inside `system/tools/job-run.sh`
> (`<job> --if-overdue`). Pulse is not involved on a Mac. See the scheduler section of
> `canon/manual.md`. **`pulse.sh` and the `crontab` block apply to Linux and Windows only.**
````

## G2-106 · moved 2026-11-14 · frozen L65-68

Reason: the 2026-10-27 CORRECTED banner over the exit-code table; its facts are restated in present tense, with job-run.sh's 78.

````
> ⚠ **CORRECTED 2026-10-27:** the right-hand column below describes **Pulse** (Linux/Windows). On
> macOS each job runs inside `system/tools/job-run.sh`, whose contract is: `0` = output check passed ·
> `75` = stood down · `2` = transient · anything else = failed; the alarm is an ntfy text sent by
> `job-run.sh`, not a Pulse breaker. The job commands' own exit codes mean the same thing on both.
````

## G2-116 · moved 2026-11-14 · frozen L198-204

Reason: calendar-store-sync's struck 'no claude -p' claim and the stale-docstring note (Batch 4 item 3).

````
# calendar-store-sync: refreshes state/item-store/calendar/ via calendar_store_sync.py --sync
# ~~(mechanical, no claude -p — confirmed)~~ ⛔ STRUCK 2026-09-19, FALSE: it DOES call claude -p.
# calendar_store_sync.py imports run_intake_judge at :163 and calls it at :548, UNCONDITIONALLY on
# every item carrying free text (:546) — a real haiku call (intake_reader.py:46,:164-166). The
# module's own docstring :15 ("No LLM in the write path") is stale and was the source of this error.
# LIVE — see the note above. Interval matches the runner's
# own header ("own absence horizon... writers run ~daily", STALE_AFTER_HOURS=30). 1-day cadence.
````

## G2-116 · moved 2026-11-14 · frozen L207-214

Reason: tasks-store-sync's struck 'no claude -p' claim and the stale-docstring note (Batch 4 item 3).

````
# tasks-store-sync: refreshes state/item-store/tasks/ via tasks_store_sync.py --sync ~~(mechanical,
# no claude -p — confirmed)~~ ⛔ STRUCK 2026-09-19, FALSE: tasks_store_sync.py imports
# run_intake_judge at :102 and calls it at :391, UNCONDITIONALLY on every task carrying free text.
# Its own docstring :13 carries the identical stale "No LLM in the write path" wording as calendar.
# LIVE for the SAME reason as calendar-store-sync immediately above —
# tasks-store-sync-run.sh shared the identical GWS_CREDS-missing branch and got the identical fix.
# Interval matches the runner's own header ("writers run ~daily", STALE_AFTER_HOURS=30). 1-day
# cadence.
````

## G2-118 · moved 2026-11-14 · frozen L217-229

Reason: email-summary-write's struck claim and the asymmetry note; settled 2026-11-14: the reader on flagged spans only is the Sentinel pipeline as defined (LW3).

````
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
````

## G2-121 · moved 2026-11-14 · frozen L257-260

Reason: the archivist-deepmine TENSION note, stale (K12).

````
# ⚠ TENSION, flagged not silently resolved: .claude/skills/archivist-deepmine/SKILL.md still
# says "its scheduled runner does NOT ship... the skill IS the interactive path" — that line
# predates this port and is now stale; this task's own plan named the missing scheduled leg as
# the gap to close. The skill file is outside this row's ownership to correct.
````

## G2-125 · moved 2026-11-14 · frozen L312-314

Reason: the 2026-10-27 CORRECTED banner and its 'originally said' (Batch 4 item 3).

````
> ⚠ **CORRECTED 2026-10-27:** this block is **Linux and Windows only**. macOS does not read it: a Mac
> installs launchd LaunchAgents built from the `jobs` block (see "How it works" above and
> `canon/manual.md`). The text below originally said "crontab on Mac/Linux".
````

## G2-115 · 2026-11-14 · frozen L180-196

The 2026-08-14 comment block (the rc 3 → 75 credential fix and the 'Flipped `enabled` to `yes`' note) was
replaced by a present-tense comment. Its words are not carried into this shipped file; they were moved to the
maintainer's private records, 2026-11-14.
