---
element: code-root
title: "code-root — element detail (ground/base altitude)"
subsystem: automation
altitude: base
record_type: organism-element
maturity_label: LIVE
generated_from:
  - system/hooks/session_context_loader.sh
  - system/hooks/tests/test_session_context_loader.sh
  - system/tools/install-schedulers.sh
  - system/tools/job-run.sh
  - system/tools/health_line.py
created_at: 2026-10-27
updated_at: 2026-10-27
status: active
authority: user
---

# code-root — element detail

> **Altitude = BASE.** The one-line pointer file `~/.config/lifehack/code-root`: the path of the copy of
> the harness that scheduled jobs should run. It exists so that **no launchd plist ever carries a code
> path** (self-monitoring plan section B.1).
>
> **LADDER: ELEMENT. siblings -> `pulse-cron.md` (the launch line that reads it), `job-run.md` (what it
> finds) ; ground truth -> `system/hooks/session_context_loader.sh` (the writer).**

## The pointer

- **Content:** one line, the absolute path of a harness root (the plugin root of the session that wrote it).
- **Writer:** only `session_context_loader.sh` (the SessionStart hook), once per session, silently and
  fail-soft. Whatever copy of the harness a session runs from becomes the copy the jobs run.
- **Write rule** (`session_context_loader.sh:85-100`): written only when `CLAUDE_PLUGIN_ROOT` is set AND
  `$CLAUDE_PLUGIN_ROOT/system/tools/job-run.sh` exists, because an older release would point the jobs at
  nothing. A root without `job-run.sh` leaves the existing pointer alone. No rewrite when the content is
  already equal (mtime unchanged).
- **Atomic:** the path is written to `code-root.tmp.<pid>` then `mv -f`'d into place; the temp file is
  removed on failure. An unwritable config dir costs the session nothing: exit 0, normal context, no
  stray temp file.
- **Never hand-written:** in the proven run it appeared from a real session.

## The reader

Every plist's launch line (`install-schedulers.sh`, the `launch=` assignment in `install_mac_launchd`):

`/bin/bash -c 'exec /bin/bash "$(cat "$HOME/.config/lifehack/code-root")/system/tools/job-run.sh" <job> --if-overdue'`

`$HOME` is literal in the plist and expanded by bash at fire time, so an upgrade, a move or a re-clone
needs no re-install: the next session rewrites the pointer.

## When it is broken

If the pointer is missing, stale or names a root that lacks `job-run.sh`, `cat` or `bash` fails and the
error lands in the plist's `StandardErrorPath`, `~/.config/lifehack/state/jobs/<job>/launch.err`. Two
things then notice:

- `health_line.py` prints `jobs cannot find the code - open any desk once to repair` (state 1, the
  highest priority; `health-line.md`), and opening any desk repairs the pointer.
- The next successful `job-run.sh` run copies `launch.err` into the log and clears it
  (`job-run.sh:80-84`).

A broken pointer cannot text by itself (the wrapper never started), so the session line is the signal.

## Tests

`system/hooks/tests/test_session_context_loader.sh`, section "3.3: the code-root pointer is only written
by a root that carries job-run.sh", five cases in a throwaway HOME each: (1) root with `job-run.sh` ->
written; (2) root without -> existing pointer unchanged; (3) no plugin root -> nothing created; (4)
unwritable dir -> exit 0, no temp file left (skipped where chmod does not block writes); (5) already
equal -> not rewritten. Recorded result: suite 33 -> 44 passed, 0 failed; dropping the `job-run.sh`
condition fails case 2.

## Limits

Not tested: two sessions from different roots flipping the pointer. Last writer wins.
