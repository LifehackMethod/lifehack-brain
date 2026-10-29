---
element: the-door
title: "the-door — element detail (ground/base altitude)"
subsystem: cron
altitude: base
record_type: organism-element
maturity_label: LIVE
generated_from:
  - system/tools/install-schedulers.sh
  - system/tools/shared-fetch-allowlist.txt
  - system/tools/vendor-read-allowlist.txt
  - system/tools/model.lib.sh
  - system/pulse-config.md (```jobs block)
  - system/tools/tests/job-sim.sh
created_at: 2026-10-29
updated_at: 2026-10-29
status: active
authority: user
---

# the-door — element detail

> **Altitude = BASE.** The check every scheduled job must pass before it is allowed to run. It lives in
> `system/tools/install-schedulers.sh`: `--install` writes a launchd agent ONLY for rows that pass, and
> `--check-row <job>` tests one row and prints `PASS` or one reason per line (exit 0 pass, 1 refused,
> 2 no such row). A refused row gets no plist, so it cannot run by accident.
>
> **LADDER: ELEMENT. up -> `manual.md` → CRON AND ALARMS ; siblings -> `cron.md` (what runs a passing row),
> `job-run.md` (what judges each run) ; ground truth -> the rule list in the header comment of
> `system/tools/install-schedulers.sh` (section "1a) THE DOOR").**

## What it refuses

Source: the header comment of `install-schedulers.sh`, rules (a)–(g), and the `presence_grade` function.

| rule | refused when |
|---|---|
| contract | any of `outcome`, `check`, `model`, `budget`, `source` is missing or `TBD`; `model` is not `none | small | medium | large`; `budget` is not a whole number above 0 (unless `model=none`) |
| content check | the check only tests an exit code written to a file, that the file is non-empty, or that it exists or is fresh ("presence-grade check") |
| code path | a script the command runs resolves outside the code root or the private desk repo, or the command pins an absolute clone or plugin path instead of `$LIFEHACK_CODE_ROOT` |
| outside reads | a static scan of the runner, what it sources, the scripts it calls, and the helper files beside it finds a raw Gmail read, Calendar read, Sheets values read, `curl`, `urllib` or `requests` — except in the files listed in `system/tools/shared-fetch-allowlist.txt` |
| silenced errors | a line that fetches, writes, pushes or calls a model ends in `|| true`, `|| :` or `2>/dev/null` |
| model ids | a literal model id anywhere but the one model table (`model.lib.sh`, `model_ids.py`) |

**What it allows on purpose.**
- **Writes** to the owner's own Google account from a job (operator's ruling 2026-10-28: a known risk he accepts).
- **One vendor-read exception:** a row with `model=none` may make its own logged-in read of the owner's own vendor
  account from the ONE file named for it in `system/tools/vendor-read-allowlist.txt`. It ends the moment the row's
  model is anything but `none`. A raw Gmail read and `curl` are never a vendor read.
- **An OFF row may be refused.** A row switched to `yes` must pass.

## What it is not

- **A string matcher, not a proof.** The scan reads code text; a determined author can phrase a call it does not
  recognise (for example, Python imports are not followed). The real guard on a new job is a person reading its
  check when it is switched on.
- **Not a runtime guard.** It runs at install. What a job does while running is judged by `job-run.sh`'s content
  check (`job-run.md`).

## How it is tested

`bash system/tools/tests/job-sim.sh` carries one scenario per rule, and `--bite` plants a known fault for each and
must see it refused and named exactly. `--gate` runs the bite first.
