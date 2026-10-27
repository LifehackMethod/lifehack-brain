---
topic: [system-architecture]
element: pulse-cron
title: "pulse-cron — element detail (ground/base altitude)"
subsystem: automation
altitude: base
record_type: organism-element
maturity_label: LIVE
gap_disposition: by-design
gap_disposition_note: "REWRITTEN 2026-10-27 (task 4.3). On macOS the scheduler is now launchd, one agent per enabled job (self-monitoring plan section B.1); Linux and Windows still use pulse.sh behind the crontab block / Task Scheduler. The prior 776-line description (Pulse as the only dispatcher, its breaker, park file, runner contract, Drive heartbeat) is recoverable: git show 0088c24^:system/organism/elements/pulse-cron.md."
generated_from:
  - system/tools/install-schedulers.sh
  - system/tools/job-run.sh
  - system/hooks/session_context_loader.sh
  - system/tools/pulse.sh
  - system/pulse-config.md (```jobs + ```crontab blocks)
  - "git: 0088c24 (3.1: pulse.sh, pulse-park.sh and the crontab block KEPT for non-Mac installs)"
created_at: 2026-07-23
updated_at: 2026-10-27
status: active
authority: user
---

# pulse-cron — element detail (the scheduler)

> **Altitude = BASE.** Which OS mechanism fires which job on which machine, and what each leaves behind.
>
> **LADDER: ELEMENT. up -> manual#pulse-cron ; siblings -> `job-run.md`, `code-root.md`,
> `health-line.md`, `hospital.md` ; ground truth -> `system/tools/install-schedulers.sh` +
> `system/pulse-config.md`.**

## Superseded 2026-10-27 - what it WAS

> **SUPERSEDED 2026-10-27 for macOS.** Pulse used to be the single dispatcher everywhere: one cron line
> (or Windows task) ticked `pulse.sh` every 5 minutes and it ran whatever job in the `jobs` block was
> due, behind a 3-strike circuit breaker with doubling backoff, a durable park file, an rc 0/75/2/else
> contract and a Drive-mirrored heartbeat that a dead-man's-switch watched. On a Mac that is gone: the OS
> scheduler now owns the schedule and `job-run.sh` owns each run. The old text (every mode, store and
> gate) is `git show 0088c24^:system/organism/elements/pulse-cron.md`.

## One manifest, two schedulers

Both read the same file, the ```jobs block of `system/pulse-config.md` (rows `name | enabled | interval
seconds | command`; `system/pulse-config.md:146-147`). Which mechanism acts depends on the OS, decided in
`install-schedulers.sh:107-118` (Darwin = mac, Linux = linux, anything else = windows).

### macOS: launchd, one agent per enabled job

- `bash system/tools/install-schedulers.sh --install` (`install-schedulers.sh:137` `install_mac_launchd`,
  dispatched at `:244-246`). Without `--install` it only prints the plan (`:179-183`); the test seams are
  `LAUNCHAGENTS_DIR` (default `~/Library/LaunchAgents`) and `LIFEHACK_INSTALL_DRY_RUN=1`, which writes
  plists but skips every `launchctl` call (`:120-130`).
- It writes one `ai.lifehack.<job>.plist` per row whose `enabled` column is `yes` (`:157`, `:206`).
  Rows set `off` or `waiting-on-port` get no agent.
- **The launch line** (`:209`) is
  `/bin/bash -c 'exec /bin/bash "$(cat "$HOME/.config/lifehack/code-root")/system/tools/job-run.sh" <job> --if-overdue'`.
  `$HOME` stays literal for bash to expand at fire time, so no plist carries a code path: the pointer
  file does (see `code-root.md`). Moving or upgrading the harness changes the pointer, never the plists.
- Schedule: `StartCalendarInterval` at every N hours from 00:00, plus `RunAtLoad` (`:227-230`).
  Only intervals that are a whole number of hours dividing 86400 (3600 ... 86400) are accepted; any
  other value, or an unsafe job name, aborts with FATAL before anything is touched (`:166-174`).
  `--if-overdue` in the launch line is what makes the login fire stand down when a success is recent
  (`job-run.md`).
- `StandardErrorPath` is `~/.config/lifehack/state/jobs/<job>/launch.err` (`:231`): the only place a
  broken launch line can speak. `job-run.sh` and `health_line.py` both read it.
- Idempotent: it boots out every loaded `ai.lifehack.*` label, deletes `ai.lifehack.*.plist`, rewrites,
  runs `plutil -lint` on each, then `launchctl bootstrap gui/<uid>` (`:188-239`).
- The installer's own caveat (`:241`): registration is not proof it fires; check
  `~/.config/lifehack/state/jobs/<job>/last-success` after the first scheduled run.

### Linux and Windows: pulse.sh plus the crontab block (kept)

- `pulse.sh` is unchanged and still the dispatcher there: a `pulse` row in the ```crontab block
  (`system/pulse-config.md:379`, `*/5 * * * *`, with a PATH prefix) runs `system/tools/pulse.sh` every 5
  minutes on Linux; on Windows `install_windows` registers a Task Scheduler task that launches Git Bash
  against `pulse.sh` (`install-schedulers.sh:409`, `:356-362`).
- Pulse reads the same `jobs` block, runs jobs that are due, holds a failing job behind a circuit
  breaker, honours a durable park file and treats rc 75 as stood-down (`pulse.sh:21`, `:336-460`); it
  still replays the quiet-hours notification queue each tick (`pulse.sh:520-521`).
- These two branches were deliberately NOT moved onto `job-run.sh`. Retained in `0088c24` with the
  grep proof: `install-schedulers.sh:96,325,339` still read the crontab block and dispatch through
  `pulse.sh`; deleting them would leave non-Mac installs with no scheduler.
- Consequence to know: jobs on Linux/Windows do not get `job-run.sh`'s output check, per-incident texts
  or local state, so `health_line.py` reports them "never ran" until they are routed through it.

## Interop

- `job-run.md` - what runs when launchd fires. `code-root.md` - the pointer the launch line reads.
- `health-line.md` / `hospital.md` - what reports on the result.
- `notify-plane.md` - the governor behind the texts.
