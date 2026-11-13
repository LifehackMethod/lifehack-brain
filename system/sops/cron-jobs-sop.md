---
topic: [system-architecture]
id: system-playbook-cron-jobs-sop
title: "Cron jobs SOP: how a scheduled job is added, checked and switched on"
record_type: playbook
status: active
authority: user
reader_note: "How it works lives in system/organism/manual.md (CRON AND ALARMS); this file is the HOW-TO. If either disagrees with the code: the code is what runs; check it."
history: "system/sops/cron-jobs-sop.history.md (retired and moved text; never read in normal use)"
route_format: "[section, line_in_this_file, purpose]; find a section by grep -n on its heading text; generated last, regenerate after any edit"
route:
  - ["§1", 38, "the three layers: alarm clock, envelope, steps; which layer a bug is in"]
  - ["§2", 52, "the seven principles every job follows, and what holds each one"]
  - ["§3", 66, "what is shared, what is the desk's, where files live"]
  - ["§4", 75, "the chain from launchd to the text; local state; exit codes; the alert rule"]
  - ["§5", 102, "the row contract: one row per job, its nine columns"]
  - ["§6", 124, "the check: path ~ regex, written against the outcome; what the door refuses"]
  - ["§7", 132, "the door: what it refuses, its limits, reads through the shared fetch"]
  - ["§8", 152, "state, locks, bookmarks"]
  - ["§9", 159, "the cost line (last-run) and run_model"]
  - ["§10", 169, "the rig: job-sim.sh, the bite, a generated scenario per personal job and hand-written receipts for plugin jobs, what it does not cover"]
  - ["§11", 179, "add a job: the recipe, with a worked example"]
  - ["§11a", 223, "bring an existing job into line: personal folder, what may change, refusal texts, the steps, running outside the checker"]
  - ["§12", 350, "the switch-on protocol"]
  - ["§13", 362, "debugging a job from the session line"]
  - ["§14", 371, "texts are written for a person; the approved wording"]
  - ["§15", 408, "questions for the person: PROPOSED lines moved out of the live text"]
---

# Cron jobs SOP

**Read this first.** A scheduled job is an alarm clock plus an envelope around something you could run by hand. This SOP owns the alarm clock and the envelope: the **Cron** subsystem (it runs jobs) and the **Alarms** subsystem (it tells you one broke). It does NOT own what happens inside the routine, and nothing in this SOP is a reason to edit a skill. The one exception is a job being brought into line (section 11a): that changes the job's own code, and does not change what the job reads, writes or sends, apart from its own receipt line and exit code (the two allowed fixes are the presence-grade check and the "nothing to do" exit 75). Every path here is in the HARNESS folder, resolved from the plugin root (manual, THREE HOMES), never relative to your working folder. `$CODE` below is the harness code root: whatever `$HOME/.config/lifehack/code-root` says. Never type it as a path.

On Linux and Windows, jobs run through `pulse.sh`, not through `job-run.sh`; for what that leaves out, read the manual's "Non-Mac is unchanged" paragraph (`system/organism/manual.md`, CRON AND ALARMS).

> **Shared tools:** `system/organism/elements/shared-layer.md` — common tools exist once in `shared/` (list: `system/register/toolbox.md`); use them, never copy them.

## 1. The three layers

| layer | plain name | its one question | owner |
|---|---|---|---|
| trigger | the alarm clock | is it time? | launchd (macOS). On Linux (cron) and Windows (schtasks) the trigger starts `pulse.sh`, which has none of the steps below. |
| job | the envelope | did one run start, finish in time, and pass its content check? | this SOP: `job-run.sh`, the row, the door, the texts |
| routine | the steps | what are the steps, in what order, and which one broke? | the skill; drawn as a card when it needs one |

- Keep the top two dumb. A row's command checks whether there is work, then starts the routine, or stands down with 75. Anything longer belongs in the skill.
- The test: if a person can run it by hand as a slash command or a script, that thing is the routine. The schedule is one way of pressing its button.
- The seam has two points only. (1) The command runs the routine. (2) The check reads the routine's result. Neither side needs the other's inside. Bringing a job into line (section 11a) changes the job's own code (its runner), never the skill it calls. A skill rewrite happens only if the person starts that conversation.
- Card or no card is the skills rule, not this SOP's: `system/sops/skill-building-sop.md`, "The Procedure", "Build a skill", step 1 (command or skill) and step 5 (the stage card). Read it there; do not copy it here. A card is an upgrade, never a prerequisite: a job can be scheduled with its routine as it is.
- Bugs: ask "which layer?" first. Did not fire: trigger. Did not come back, or the check failed: job. Step N was wrong: routine.

## 2. The principles every job follows

Every job obeys these, carded or not. The door and the rig check what code can judge.

1. A check tests CONTENT, never presence. A file existing, being non-empty, being fresh, or holding an exit code proves nothing. *(Held by the door.)*
2. A step that changes something is safe to run twice, or records what it did before acting. Writes to the person's own Google account have no shared writer: the routine calls them directly, so it must make them repeat-safe itself (for example, record each item's message id in a ledger BEFORE the append and skip ids already there; or write in place by a key column).
3. Exit 0 is never proof of work. Check the artifact. A bookmark moves only on rc 0 AND a passing check. *(Held by the run wrapper, which writes last-success only after the check, and by the shared email reader for its bookmark.)*
4. Never silence a step's errors. A failed fetch must not read as "nothing new". *(Held by the door, for the spellings it scans: `|| true`, `|| :`, `2>/dev/null`.)*
5. The runner writes the record. The AI never does. AI steps get only the tools they need (read-only, or a per-job grant scoped to the job's own output folder). The AI can never write job state or a bookmark. *(Held by `run_model`: `model.lib.sh`, its READ-ONLY note and the `--allowedTools Read` call.)*
6. Refuse a truncated or corrupt record, loudly, and name the file. *(Held by the run wrapper.)*
7. Test the tester first: plant known faults and see every one named (the rig's bite, section 10). *(Held by the rig.)*

Also: "ran" is not "succeeded". No job writes job state to Drive: content yes, state no.

## 3. What is shared, what is the desk's

- If two desks would WANT it to behave differently, it is the desk's: prompt, verdict set, what is written, where.
- If a person would be UPSET that it behaved differently in two desks, it is shared, exactly one copy in `$CODE`: fetch, sanitise, scan, pause, auth, lock, timeout, output check, cost, notify, state location.
- The middle is shared shape, desk content: the loop and its guardrails are shared; the desk hands in its prompt, closed verdict set and output format.
- Where files live: shared code in `$CODE` (the public harness). Desk runners, prompts and notes in your personal code folder (find it with `python3 $CODE/shared/personal_code_root.py --quiet`) and the brain folder (the driver's logbook: the knowledge layer; `shared/brain_root.py` finds it). Your own scheduled jobs are rows in `<personal-code>/jobs.md`, and their code is in `<personal-code>/tools/<job>/`; never in the plugin, because a plugin update overwrites it. The setup (`bootstrap.py`) makes the personal folder when it is missing, then the places in it; the installer makes those places only when the folder already exists. Neither overwrites anything (section 11a). Never put desk code in the public harness. Never copy a shared file into a desk.
- The door (`system/tools/install-schedulers.sh`) allows a runner under `$CODE` and under your personal code folder, which it finds itself with `shared/personal_code_root.py`. There is nothing to set. `LIFEHACK_DESK_REPO` overrides that for tests only; a row is in line only if it passes without it (section 11a, "Check the way the run does").
- Everything ingested, in a session or a job, goes through the security system (the door, section 7).

## 4. The chain

```
launchd -> code-root pointer -> job-run.sh -> the row's command -> the row's check -> last-success -> session line / text
```

1. **launchd** runs one LaunchAgent per `yes` row (`ai.lifehack.<job>`), written by `install-schedulers.sh --install`. Its only line: `/bin/bash -c 'exec /bin/bash "$(cat "$HOME/.config/lifehack/code-root")/system/tools/job-run.sh" <job> --if-overdue'`. A run missed in sleep fires once on wake. An interval is either a whole number of hours that divides 86400 (3600, 7200 ... 86400) or a multiple of 86400 (a weekly row gets a daily trigger, and `--if-overdue` enforces the real interval); any other value stops the installer loudly.
2. **The pointer** `$HOME/.config/lifehack/code-root` holds one line, the code root. The session-start hook rewrites it every session. A plist never holds a code path. If it is wrong, launchd's stderr lands in `launch.err` and the session line says to open any desk once to repair.
3. **job-run.sh** reads the row, takes the lock, runs the command under a watchdog, then runs the check. It is the only place exit 0 is earned.
4. **The command** is `bash -c "<command>"`. By hand: `bash $CODE/system/tools/job-run.sh <job> [--force]`.
5. **The check** (section 6) runs only if the command exited 0. A pass stamps `last-success`; nothing else ever does.
6. **The session line** (`health_line.py`) is the first line of every session, read from local state. **The text** is one ntfy push on break, one on recovery, sent through the governed notify (quiet hours, dedup, cap of 3 per job per day; recovery is exempt from the cap).

State is local, never Drive: `$HOME/.config/lifehack/state/jobs/<job>/` holds `last-run`, `last-success`, `log` (last 20 runs), `errors/` (one file per failed run), `alerted` (a "job down" push is out), `launch.err`. Env `PATH` under launchd is bare; job-run.sh adds `~/.local/bin` and Homebrew, so use the pointer and `$LIFEHACK_CODE_ROOT`, never a bare tool name you have not tested.

**Exit codes** (a command's and job-run.sh's alike):

| rc | meaning | effect |
|---|---|---|
| 0 | the output check passed | last-success stamped |
| 75 | stood down: nothing configured, not logged in, not overdue, row not `yes`, lock held by a live owner | never a fault; shown on the session line; an unbroken run of them longer than 2 x the interval sends one 'paused' text, and one 'running again' text when it next passes (never for a row that is not `yes`) |
| 2 | transient (network, Google 5xx) | retried next period |
| 78 | the door refused the row at run time | a failed run: an `errors/` file is written and it counts toward the alert |
| other | failed | `errors/` file written; counts toward the alert |

**Alert rule (Alarms).** A failed run (any rc not 0 or 75; 2 counts) pushes ONCE when `last-success` is missing or at least 2 x interval old (the second miss), then leaves `alerted`. The next success pushes one recovery and removes it. A push that fails never changes the exit code. A `--force` run never pushes. Also: `alerted` is written only on a confirmed send, so a failed text retries; a job that keeps standing down texts once; every run checks the other jobs and texts once for one that is not running. Every text follows section 14.

## 5. The row contract

One row per job, in a `jobs` block. A job that ships with the plugin is a row in `$CODE/system/jobs.md`. A person's own job is a row in the same format in `<personal-code>/jobs.md` (the plugin ships no such list, and an update would overwrite anything the person put in its own). One scheduler reads both (`shared/jobs_manifest.py`). To change a plugin job, copy it under a NEW name into your own folder: the row goes in your `jobs.md`, its code in `<personal-code>/tools/<new-name>/`, and the new job is yours and not supported by the plugin; the plugin's job keeps running unchanged (section 11a, "Copying a plugin job to change it"; decided by the owner, in session, 2026-11-05). The code still lets a personal row with a plugin row's name win, with a warning that names it; that is not the way to change a plugin job. A broken plugin job is reported through the PR rulebook, `system/sops/pr-sop.md`. A row in your own `jobs.md` that the checker refuses may run outside the checker only when you knowingly chose it and the row carries the mark above it (section 11a, T5).

```
name | enabled | interval | outcome | check | model | budget | source | command
```

| column | rule |
|---|---|
| name | lowercase letters, digits, hyphens. Also the state folder and the plist label |
| enabled | `yes` runs. Any other word is a declared disposition (`off`, `waiting-on-<thing>`). Never ambiguous |
| interval | seconds: a whole-hour divisor of 86400, or a multiple of 86400 (section 4) |
| outcome | ONE sentence: what is true after a good run. The check is written against it |
| check | `<path> ~ <ERE>` (section 6) |
| model | `none`, `small`, `medium` or `large`. Ids live only in `system/tools/model.lib.sh` |
| budget | max model calls per run, an integer: count the calls a good run makes at its largest (one per item x the cap, plus any summary call) and add a margin of about half again. It is a tripwire that names a runaway, not a cost target. 0 only when model is `none` |
| source | the shared reader that FEEDS it (what it reads, never what it writes): `gmail`, `web`, `gsheet` or `none`. A job that reads email and writes a Sheet is `gmail`. `gmail` makes job-run load the Google credentials. Only `gmail` changes anything (it loads the Google login); the door accepts any non-empty word |
| command | LAST, because it may contain `\|`. Literal bash, or a leading-`@` builtin. No other column may contain `\|` |

A row describes the envelope only. It does not carry steps, prompts or verdict lists. `TBD` in any contract column means the job can never succeed and the door refuses it.

## 6. The check

`<path> ~ <regex>`, split at the FIRST ` ~ `. It passes only when the file exists, was written after this run started, and some line matches the regex (`grep -E`). `$HOME`, `$LIFEHACK_CODE_ROOT` and a leading `~` expand in the path. No `|` in the regex: write alternation as an optional group.

Write the check against the outcome sentence, and make it match something the routine had to do real work to produce (a count of 1 or more, a verdict word, a date). The receipt it reads is written by the runner AFTER it verified the artifact, never by the model.

The door refuses presence-grade checks: a regex that tests only an exit code written to a file (`"rc":0`), non-empty (`^.+$`), or existence or mtime alone (a check without ` ~ `). A check like `^done$` is refused because it is the same on every run; the door looks for a check that contains something that varies, such as an `=`, a number or a captured value. Wrong: `last-run.json ~ "rc":0`. Right: `receipt.txt ~ ^example-digest ok .*items=[1-9]`.

## 7. The door

`job-run.sh` runs the same test before every run of a `yes` row, and every forced run (an `off` row stands down first), so no unmarked run can get around the door.

`install-schedulers.sh --install` refuses a `yes` row, writes no plist, prints the reason, and exits 1. `install-schedulers.sh --check-row <name>` runs the same test on any row and prints `PASS` or the reasons. A row is refused for:

- a missing or `TBD` contract column, a bad model word, or a bad budget;
- a presence-grade check;
- a runner outside `$CODE` and your personal code folder, or a pinned code path (a clone or plugin-cache folder) where `$LIFEHACK_CODE_ROOT` belongs;
- a command with no script in it; a script path built from any setting other than the code root or home; a script that does not exist; or a status-tile call that names a different job;
- a raw outside READ (Gmail or Calendar reads, sheets `values get`, `curl`, `urllib`, `requests`) anywhere in the runner, what it sources or invokes, or the helper files beside it. Only files named in `system/tools/shared-fetch-allowlist.txt` may hold one. Never add a desk runner to that list. **Writes** to the owner's own Google account (labels, archive, Sheets, Tasks, Calendar, Docs) are allowed: an accepted risk (ruled 2026-10-28). The one change: a write to a Sheet the person has named as fine china meets fine china protection A, "can't edit it without talking to the human first" (an ask before the edit; `system/sops/build-conformance-sop.md` §2 (the asks) and §5.11 (the friction levels)); a Sheet not named stays under the accepted risk. With nobody at the screen, as in a scheduled run, protections A and B are denied with a sign and parked for the morning, and the run carries on; protection C (a speed bump with a sign in front of a mass delete: a whole folder or hundreds of files) has its sign logged, and the action waits for the morning rather than being blocked outright. **One vendor-read exception:** a row whose model is exactly `none` may make its own logged-in read (python `requests` or `urllib` only) of the person's own vendor account from ONE file listed as `<job> <file>` in the person's own `<personal-code>/vendor-read-allowlist.txt` (`<file>` relative to the job's tools folder; the plugin's `system/tools/vendor-read-allowlist.txt` ships empty and is read first). A raw Gmail read and `curl` are never a vendor read. It ends if the row gains an AI step;
- a literal model id (or `--model X`) anywhere outside `model.lib.sh`. Name a tier;
- a silenced error: `|| true`, `|| :` or `2>/dev/null` on a fetch, write, push or model call. Stderr goes to the job log.

The door matches patterns; it cannot judge whether a check is meaningful. A person reads each check at switch-on (section 12; ruled 2026-10-29).

The static scan follows `source` and `bash`/`python` invocations. It does not follow Python imports, so keep raw calls out of imported modules too. Session side: the ingest-gate hook refuses the same raw reads typed in a session. Honest limit: a person typing a raw command in a terminal is outside the system.

**Reads go through the shared fetch.** Email: `shared/tools/email_fetch.py` only. What it hands back is already sanitised, scanned and judged: a message the judge could not clear is withheld (the run fails loudly), and a real attack pauses the label and sends one critical text. A runner never re-reads the raw message. It sets NO read policy: the job must pass `--query`, `--cap` and `--since`. Which mail, how many and from when is the SKILL's decision, made with the person when the skill is built; never a default here. Web: `system/tools/safe_fetch.py` and `safe_search_api.sh`; job-run seals web reads for scheduled runs to the plugin's `system/tools/job-fetch-hosts.txt` plus your own `<personal-code>/job-fetch-hosts.txt` (the setup makes it). Add a host to your own list, never to the plugin's: an update overwrites that. A list that exists but cannot be read refuses the run (exit 78) the way the door's run-time refusal does: a failed run with an `errors/` file, `last-run` saying rc=78, and the usual alert. Sheets: `safe_sheets.py`. Push: `shared/notify/notify-send.sh` only, and a runner usually should not push at all because job-run alerts. The credentials live only in the shared fetch; never export them into a runner.

## 8. State, locks, bookmarks

- A corrupt state, governor or bookmark file is refused and named: the run fails and the text names the file. It never "starts fresh".
- Email bookmarks are `$HOME/.config/lifehack/<consumer>-last-seen`. The fetch writes `<consumer>-last-seen.pending`; job-run promotes it to the real file only on rc 0 AND a passing check. A fetch that peeked never advances anything.
- Locks record the owner pid. A dead owner's lock is taken at once. A live owner gives exit 75, never 0. A runner's own lock contention also exits 75.
- Where a new consumer starts reading (its bookmark) is that skill's read policy, set with the person at its gate. An unattended job never drains a backlog without the person deciding it.

## 9. The cost line (`last-run`)

Every run that gets past the overdue test rewrites `last-run`:

```
<ISO time> rc=<n> calls=<N> secs=<S> model=<tier> ccv=<claude version> <reason>
```

`calls` and `secs` are the model calls this run made through `run_model` (0 and 0 for a job with no AI). `ccv=` is the Claude version. To call a model, a runner sources `$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh` and calls `run_model <tier> <prompt-file> <out-file> [marker]`. It maps tier to id from the one table, takes the token, times out (`MODEL_TIMEOUT`, default 600 s), refuses an empty reply or a missing marker, counts the call, and refuses the call that would exceed `budget`. AI steps run with only the tools they need (read-only, `--allowedTools Read`, or a per-job grant scoped to the job's own output folder): the runner writes every file and the record, the model returns text. A model failure `run_model` recorded fails the run and is named even if the runner swallowed the return code.

## 10. The rig

`system/tools/tests/job-sim.sh` replays days in seconds against the real `job-run.sh`, `health_line.py` and notify scripts, on a fake clock and a throwaway state tree. It never touches real state, pushes or the network.

- Run it green before every commit, and with `--gate` at every gate (200 fuzz reps).
- `--bite` plants known faults, one per rule, and asserts each is caught and NAMED exactly. `--gate` runs the bite first. A rig that was never shown to fail is not trusted.
- A change that cannot be expressed as a rig scenario is suspect. Add the scenario first.
- **A person's job needs no scenario written by hand.** The rig reads the merged job list (`shared/jobs_manifest.py`: the plugin's `system/jobs.md` plus `<personal-code>/jobs.md`; on a name clash the personal row is the one tested) and generates one scenario per personal row, named `personal:<job>`. The row's own check is shown to pass on a good receipt line and fail on a wrong one, with a generic stub standing in for the runner (the real command never runs; throwaway home, fake clock, no network). The good line is built from the check's regex, the bad line is one the regex does not match, and both are verified with the same `grep -E` the runner uses; a regex that cannot be built, or whose every bad candidate matches, is a named failure that says why. The expected model calls are 0 for model `none`, else 1. An optional `<personal-code>/job-sim/<job>.json` with `{"good": "...", "bad": "...", "calls": N}` replaces any key it gives; a malformed file (not JSON, wrong types, an unknown key) is a named failure. It lives in the personal code folder, never in the plugin. A row whose check is `TBD` or empty, or that the door refuses, prints `SKIP personal:<job>: <reason>` and is not a failure: the door is its gate. `off` rows are tested too. The plugin's own jobs (rows in `system/jobs.md`) keep hand-written receipts in `job-sim.sh`, which the plugin maintains (`job-sim.sh`, the `receipt_contract` rows in its main run; not every plugin row has one). A plugin job's scenario duty is therefore unchanged: its receipt is hand-written in `job-sim.sh`, not generated.
- Not covered by the rig: real launchd wake behavior, real logins, real push delivery, real Google or Claude auth. One live `launchctl kickstart` per gate keeps those honest. Not covered: if no job runs at all (scheduler stopped, Mac off, every job unloaded), no text is sent; the session line at the start of a session is the only backstop.

## 11. Add a job (the recipe)

A blind session can do this from here alone. Never skip a step; never flip the row to `yes` (section 12).

1. **Write the outcome in one sentence.** If you cannot, the job is not ready.
2. **Decide the layer.** The routine (steps, prompts, verdicts) is a skill, or a script a person can run by hand. If it needs a card, see `system/sops/skill-building-sop.md`, "Build a skill", steps 1 and 5. This job is only the envelope.
3. **Write a thin runner.** A job of your own lives in your personal code folder, in `<personal-code>/tools/<job>/` (the setup makes `tools/`; the door allows any path under the folder, and the vendor-read line needs the path to end `/tools/<job>/<file>`). A job every installer would want is a change to the plugin and goes through the PR rulebook (`system/sops/pr-sop.md`), never a direct edit of `$CODE/system/tools/`. Never copy shared files into a desk. Resolve everything from `$LIFEHACK_CODE_ROOT`. Use the shared fetch for any read, `run_model` for any AI call, no silenced errors, exit 75 when there is nothing to do or a lock is held, and write a receipt AFTER verifying the artifact.
4. **Add the row, `off`,** to your own `<personal-code>/jobs.md`. A job every installer should get is a change to the plugin: it goes through the PR rulebook (`system/sops/pr-sop.md`, not written yet ⏳ unruled; until it exists, a report is an issue on the plugin's GitHub page, decided by the owner, in session, 2026-11-05), never a direct edit. Fill all five contract columns (outcome, check, model, budget, source). Check the interval against section 4.
5. **Run the door** the way `job-run.sh` does, with no session-only settings (command in section 11a, "Check the way the run does") until it prints `rc=0` and the line above it is `PASS` (`job-run.sh`, step 1c, "THE DOOR AT RUN TIME": exit code 0 and last line `PASS`).
6. **Read policy** (if it reads email): the query, cap and start point the skill decided with the person. Do not invent one.
7. **Run the rig:** `bash $CODE/system/tools/tests/job-sim.sh`. It tests a row in your own `jobs.md` by itself (section 10); there is no scenario to add. If it prints `SKIP personal:<job>: <reason>`, the check is still `TBD` or empty, or the door still refuses the row: go back to step 5. A named failure says what to fix. Add `<personal-code>/job-sim/<job>.json` (`good`, `bad`, `calls`) only if the generated receipt lines or call count do not fit the job.
8. **One forced test run, only on the person's yes.** Ask first, with your best guess, and say what a run does for real: the runner's own writes and any model spend. Then `bash $CODE/system/tools/job-run.sh <name> --force`. Read `$HOME/.config/lifehack/state/jobs/<name>/last-run` and `log`. Expect `rc=0 ... [check] ok`. A forced run pushes nothing, moves no email bookmark and never changes the row. Without a yes, skip this step (step 9 still applies) and report the job as checked, not run.
9. **Commit** a personal job's code, row and notes in your own personal code folder, never to `$CODE`. A change to a plugin job or a shared tool is a PR (`system/sops/pr-sop.md`, not written yet; until it exists, a report is an issue on the plugin's GitHub page, decided by the owner, in session, 2026-11-05), never a commit to `$CODE` from here. Report what the run proved and what it did not test.

**Worked example.** A job that summarises a local drop folder once a day with one small model call.

Row (one line in the `jobs` block):

```
example-digest | off | 86400 | Each day the files in the drop folder are summarised in one note and the receipt records at least one item. | $HOME/.config/lifehack/example-digest/receipt.txt ~ ^example-digest ok .*items=[1-9] | small | 2 | none | bash "$HOME/lifehack-personal-code/tools/example-digest/run.sh"
```

Runner `<personal-code>/tools/example-digest/run.sh` (an illustration; no such file ships). It sources the shared `model.lib.sh` from `$LIFEHACK_CODE_ROOT`, which `job-run.sh` sets:

```bash
#!/usr/bin/env bash
set -uo pipefail
: "${LIFEHACK_CODE_ROOT:?run me through job-run.sh}"
. "$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh" || exit 1
DROP="$HOME/.local/share/lifehack/example-digest/drop"; OUT="$HOME/.local/share/lifehack/example-digest"
RCPT="$HOME/.config/lifehack/example-digest/receipt.txt"
mkdir -p "$OUT" "$(dirname "$RCPT")" || exit 1
N=$(find "$DROP" -type f | wc -l | tr -d ' ')
[ "$N" -gt 0 ] || { echo "nothing in the drop folder"; exit 75; }        # stood down, not a fault
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
{ echo "Summarise these files in 5 bullets. Begin with the word DIGEST."; cat "$DROP"/*; } > "$WORK/prompt.txt"
run_model small "$WORK/prompt.txt" "$WORK/reply.txt" "DIGEST" || exit 1   # counted, bounded, shape-checked
cp "$WORK/reply.txt" "$OUT/digest-$(date +%F).md" || exit 1               # the runner writes, the model never
[ -s "$OUT/digest-$(date +%F).md" ] || exit 1
echo "example-digest ok items=$N" > "$RCPT"                               # receipt AFTER verifying the artifact
```

Why it conforms: the check names a verified count (`items=[1-9]`), not an exit code; the only read is local so `source` is `none`; the model is a tier word and `budget 2` is a tripwire above the one call it makes; nothing is silenced; nothing is pushed.

## 11a. Bring an existing job into line

For a job that already exists and whose row the door refuses, or that was never checked by the door. §11 is the road for a new job; this is the same road for one already built. The section title is the one the personal refusal text names.

### Where a person's own jobs are saved

**DECIDED** (P-127, round 4): the root problem is "students or subscribers can't use the plugin to save their kron jobs", because an update overwrites the plugin. So the personal code folder holds what a person needs to save their own jobs, mirroring "only ... the stuff that ... would actually need".

The scaffold (`shared/tools/personal_jobs_scaffold.py`) creates these, relative to the personal code folder (find it with `python3 $CODE/shared/personal_code_root.py --quiet`); an existing piece is skipped untouched (the file is opened with mode `x`):

| piece | what it is for |
|---|---|
| `jobs.md` | the person's job rows: an empty `jobs` block, with the nine columns named above it |
| `job-fetch-hosts.txt` | websites the person's jobs may read, one host per line; added after the plugin's list by `job-run.sh` |
| `vendor-read-allowlist.txt` | `<job> <file>` lines for the one vendor-read exception (section 7) |
| `job-sim/README.txt` | how to override a generated test receipt with `job-sim/<job>.json` (section 10) |
| `tools/` | an empty folder: **job code goes in `tools/<job>/`**; a row's command points at a script there |
| `JOBS-README.txt` | one page: what goes where |

`job-names.txt` (`<job> = <plain name>`) is read when present but the scaffold does not create it. Who runs the scaffold: `system/tools/bootstrap.py` at setup, and `install-schedulers.sh` (`--install` and the plan-only run, not `--check-row`) whenever the personal folder already exists. The scaffold never makes the folder and exits 1 when there is none; `bootstrap.py` makes it first (`ensure_personal_code`, then `scaffold_personal_jobs`), and the installer never does. By hand: `python3 $CODE/shared/tools/personal_jobs_scaffold.py`; a second run creates nothing.

### What may change, and what may not

**DECIDED** (P-127, round 4, the fuller lines): "do we change the nature of the job no we shouldn't change the nature of the job", and "we just want to stay focused on how a kron drop gets made". **DECIDED** (P-127, round 4): the aim is to "stay in our lane": the shared code correctly divided between the plugin and the personal folder, "saved in conformance", and "enforced when it's on its own". What holds it: the job door refuses a row's runner that breaks the rules (`install-schedulers.sh`), and `job-run.sh` runs the same door before each run of a `yes` row and every forced run; the ingest-gate hook refuses raw reads of outside content typed in a session (SOP §7). Writing into shared plugin code meets a hard block with a sign (`build-conformance-sop.md` §2 (the asks) and §5.11 (the friction levels), decided 2026-11-03); the one exception is the operator's own hands at the terminal, with no administrator-key machinery (P-90's note). **DECIDED** (P-127, round 3): rewriting a skill is not planned and not prevented; if the person's own conversation goes there, that is fine.

**Never install by hand and never go around the door:** no crontab, no hand-written plist, no edit to `shared-fetch-allowlist.txt` to make a row pass. A fix is made in the person's own files only.

### The window offers, in one line, every time (DECIDED, P-127 rounds 1 and 4)

When the door refuses a personal row, the window says one short line and asks, for example: "This job isn't in line with the Lifehack checker. Want me to bring it into line?" **DECIDED** (P-127, round 4): the offer is made every time the refusal comes up, as "just the small little lines like, hey, this isn't in conformance", "never a huge block"; a person who asks for the fix without being offered gets the same road (round 1). **DECIDED** (B5, 2026-11-11): every time, as a one-line sign, never a pop-up. When the window asks anything, it gives its best guess.

### Whose job decides the refusal

One scheduler reads two lists: the plugin's `system/jobs.md` and the person's `<personal-code>/jobs.md`. A refusal ends with one of two texts, by the list the row came from. A row is plugin-origin ONLY when it is in the plugin's own list, `$CODE/system/jobs.md` (real paths compared), before the `# ── personal rows (from …) ──` marker. A row after the marker, or read from any other manifest file (`LIFEHACK_JOBS_FILE` or `PULSE_CONFIG` pointing anywhere else, such as a branch's `jobs.md`), is personal; a name in both lists counts as personal (`install-schedulers.sh`, `door_origin_step`). For `--check-row` it is the last line; `--install` and the plan-only run print each applicable text once, after the count line, to stderr. The exact wording, as coded in `install-schedulers.sh` (`DOOR_NEXT_STEP_PERSONAL`, `DOOR_NEXT_STEP_PLUGIN`):

- **Personal row** (`DOOR_NEXT_STEP_PERSONAL`):
  > Rulebook: `system/sops/cron-jobs-sop.md`, section "Bring an existing job into line". This job isn't in line yet: offer the person, in one short line, to bring it into line. Don't install it by hand. The main window runs this check itself and reads this line; never rely on a summary.
- **Plugin row** (`DOOR_NEXT_STEP_PLUGIN`):
  > Rulebook: `system/sops/pr-sop.md`. This job ships with the plugin: tell the person to report it. Don't edit plugin files, and don't copy the job under its own name to fix it. The main window runs this check itself and reads this line; never rely on a summary.

**A broken plugin job** (DECIDED, P-127, round 4): "I would just tell them to report it that's it", following the PR rulebook ("assume that there is a pr sop"), `system/sops/pr-sop.md`. No window tells the person to copy the row to fix it: once the plugin fixes the job "they would have two copies of the same job". The window says plainly that the job should be reported, and does not edit it. The refusal for a broken plugin job is "report it", never a copy.

**Copying a plugin job to change it** (DECIDED, the owner, in session, 2026-11-05, T6; and P-127, round 4: a fork carries "you broke it you bought it"): the copy is a NEW job, under a NEW name, in the person's own folder. Its row goes in the person's `jobs.md`, and its code goes in `<personal-code>/tools/<new-name>/`. The new job is the person's own and is not supported by the plugin. The plugin's original job keeps running unchanged. The window does not recommend a same-name copy that replaces the plugin job. The code still lets a personal row with a plugin row's name win, with a warning that names the override (`job-run.sh`, step 1c, "THE DOOR AT RUN TIME"); that is not the way to change a plugin job, and the refusal for a broken plugin job is "report it" (above). The fork warning still stands: the new job will not get plugin fixes, "you broke it, you bought it".

### Check the way the run does

A row is in line only if the check passes as `job-run.sh` runs it (`job-run.sh`, step 1c, "THE DOOR AT RUN TIME"): `2>&1`, exit code 0 and last line `PASS` (a personal copy of a plugin row prints a warning line first), and none of the test seams set (`LIFEHACK_DESK_REPO`, `LIFEHACK_JOBS_FILE`, `PULSE_CONFIG`, `LIFEHACK_PERSONAL_JOBS_FILE`, `LIFEHACK_VENDOR_ALLOWLIST`; the command below does set `LIFEHACK_CODE_ROOT`, to the real root, on purpose). `env -i` approximates launchd's bare environment (`job-run.sh`, the launchd `PATH` line).

```
CODE="$(cat "$HOME/.config/lifehack/code-root")"
env -i HOME="$HOME" PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  LIFEHACK_CODE_ROOT="$CODE" bash "$CODE/system/tools/install-schedulers.sh" --check-row <name> 2>&1; echo "rc=$?"
```

In line only if the last line is `rc=0` and the line above it is `PASS`. A refusal prints one reason per line, then a rulebook text, then `rc=1` (`rc=2` = no such row, which prints the personal text: check the name against the job list before offering anything).

### Checking a job on a branch

To check a row that lives on a branch (a worktree's own `jobs.md`), point the checker at that file. A row read from any file other than `$CODE/system/jobs.md` is personal, so a refusal gives the personal text. With `LIFEHACK_JOBS_FILE` set the personal list is not merged in, so the branch's file needs the row itself. This is a test check, not the "in line" check above (it sets a seam):

```
CODE="$(cat "$HOME/.config/lifehack/code-root")"
env -i HOME="$HOME" PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  LIFEHACK_CODE_ROOT="$CODE" LIFEHACK_JOBS_FILE=<worktree>/jobs.md \
  bash "$CODE/system/tools/install-schedulers.sh" --check-row <name> 2>&1; echo "rc=$?"
```

The main window runs this check itself and reads the last line; it never relies on a helper's summary of it.

To read the branch's own runner too, write the personal row's command with the personal-folder variable: `bash "$LIFEHACK_PERSONAL_CODE/tools/<job>/<job>-run.sh"`. The door expands `$LIFEHACK_PERSONAL_CODE` to the personal code folder it resolves (the `LIFEHACK_DESK_REPO` seam moves it), and `job-run.sh` exports the same folder (from `personal_root.lib.sh`, the same answer as `shared/personal_code_root.py`) before it runs the command. Rows with a fixed path keep working unchanged. A branch check is then:

```
LIFEHACK_DESK_REPO=<worktree> LIFEHACK_PERSONAL_JOBS_FILE=<worktree>/jobs.md bash system/tools/install-schedulers.sh --check-row <job>
```

It reads the branch's `jobs.md` and the branch's runner.

### The steps, after the person's yes

0. **If the personal folder has no `tools/` or `job-fetch-hosts.txt`** (plugin updated, installer and `bootstrap.py` not run since), run the scaffold by hand first (see "Where a person's own jobs are saved"). The installer's plan-only run also writes these pieces.
1. **Get the reasons** with the command above. A reason that points into a plugin file is not fixed here: report it (above).
2. **Fix each reason the standard way** (table), in the person's own files, changing nothing the job reads, writes or sends apart from its own receipt line and exit code (the two allowed fixes: the presence-grade check and the "nothing to do" exit 75). Job code stays in `<personal-code>/tools/<job>/`, and the job's scripts are listed in the person's own `register.jsonl` beside `jobs.md` (`build-conformance-sop.md` §1.5).
3. **Re-run step 1 until `rc=0` and `PASS`.** One fix can uncover another. The scan does not follow Python imports.
4. **Run the rig** with the five seams unset (the rig's own door check clears only some of them): `env -u LIFEHACK_DESK_REPO -u LIFEHACK_JOBS_FILE -u PULSE_CONFIG -u LIFEHACK_PERSONAL_JOBS_FILE -u LIFEHACK_VENDOR_ALLOWLIST bash $CODE/system/tools/tests/job-sim.sh`. It tests a personal job by itself (section 10). `SKIP personal:<job>: <reason>` means the check is still `TBD`/empty or the door still refuses it: back to step 1.
5. **The first real test run needs the person's yes** (DECIDED, P-127 round 2: approval first; the PROPOSED details are in section 15).
6. **Switch on only through the gate** (§12), never by flipping the row. (A PROPOSED line on a row already `yes` is in section 15.)

| the reason says | the standard fix | where |
|---|---|---|
| `missing contract`, `bad model`, `bad budget` | fill the column; model is a tier word; budget an integer above 0 (0 only for model `none`) | §5 |
| `presence-grade check` | check an outcome on a value that varies, e.g. `items=[1-9]` | §6, §11 |
| `pinned code path in command` | use `$LIFEHACK_CODE_ROOT` | §7, §11 step 3 |
| `no runner script`, `unparseable command`, `unresolvable variable`, runner outside the code roots or missing | one real script in the personal `<personal-code>/tools/<job>/` (a personal job's code is never in the plugin) | §3, §5 |
| `raw curl / urllib / requests`, web fetch or search | read through `safe_fetch.py` or `safe_search_api.sh`; **a new host goes in `<personal-code>/job-fetch-hosts.txt`**; never add a runner to the allowlist | §7 |
| raw mail read | `shared/tools/email_fetch.py`. First check the line is a read: the door calls any mail verb not on its short write list a "read" | §7 |
| raw calendar read | `system/tools/safe_calendar.py`. Same check for a write the door does not list | reason text |
| raw sheets read | `system/tools/safe_sheets.py` | §7 |
| `hard-coded model id` | name a tier; call `run_model <tier> ...` | §5, §9 |
| `silenced ... error` (including the row's own `\|\| true`) | remove the silencer; let stderr reach the log; for "nothing to do" exit 75 | §2, §7, §11 |
| `silenced <fetch\|write\|push\|model> error at <file>:<line>` (the text of the `silenced_call` reason in `install-schedulers.sh`; the row-command version, the `cmd_swallows` reason, is the row above) | the text names `\|\| true`, `\|\| :` and `2>/dev/null`, but the rule (`door_rules.py`, `SILENCER`) also catches `&>/dev/null` and `>/dev/null 2>&1`: remove any of them from that line, log the failure to stderr and fail the step | §2, §7 |
| `raw curl to a Google/Gmail API host: go through the shared email tool (shared/tools/email_fetch.py; system/register/toolbox.md) at <file>:<line>` (`door_rules.py`, `GOOGLE_CURL_WHY`, printed where `install-schedulers.sh` calls `google_curl`) | read mail through `shared/tools/email_fetch.py`, not `safe_fetch.py` (the curl row above is for other hosts) | §7 |
| `status tile named 'x' but ...` or `... is not set to a literal in this file` | pass the row's own name as a literal, or a variable the file sets to it | reason text |
| a vendor read refused | only model exactly `none`, python `requests`/`urllib` only, on a `<job> <file>` line (`<file>` relative to `tools/<job>/`) in the person's own `vendor-read-allowlist.txt` | §7 |
| `shared-fetch allowlist unreadable` | not a job fault: the plugin copy is damaged. Do not edit it; report it | none |

A personal `job-fetch-hosts.txt` that exists but cannot be read makes `job-run.sh` refuse the run (exit 78 through `finish`: an `errors/` file, `last-run` says rc=78, the usual alert); fix its permissions, never work around it. This table is not the full list. A missing "how" is not a licence to invent one: use the reason text and tell the person.

### A person may knowingly run their own job outside the checker (DECIDED, P-127, round 3; T5 DECIDED, the owner, in session, 2026-11-05)

The aim is to stop an LLM changing something unknowingly or a new user building out of line by accident, not to stop a determined person. **Only a job in the person's own `jobs.md`.** A mark on a plugin job is ignored.

1. **Warn first, plainly** (DECIDED: "the window says it plainly"). The window says that the checker refuses the job, and that outside it nothing watches the job as the checker does, so errors, unscanned outside content or paths that break at an update can go unseen.
2. **The person says yes in their own words** (DECIDED). A yes to "may I fix it" is not this; a window never infers it.
3. **Mark the row** (DECIDED, T5, 2026-11-05): a comment line directly above the row in the person's own `jobs.md`, of the exact form `# outside the checker, by choice, YYYY-MM-DD`, with no `|` in it.
4. **No session-start line** (DECIDED, P-127, round 3). (A PROPOSED line on the offer for such a row is in section 15.)

**What the harness then does** (DECIDED, the owner, in session, 2026-11-05, T5): it installs and runs a marked personal row that the checker refuses, and prints a one-line warning that names the first refusal reason. The code that does this is in `install-schedulers.sh` and `job-run.sh`. The mark does nothing for a row from the plugin's `system/jobs.md`.

### Sources

- P-127, round 4 (2026-11-05, cron door window, "approved"; written from plan quotes, not heard directly by the coordinator): (1) root problem and "mirror ... only ... what they need" settle the personal folder section; (2) "I would just tell them to report it", "two copies of the same job", "you broke it you bought it" settle plugin-job reporting and that a fork carries "you broke it you bought it" (the warning itself is PROPOSED); (3) "hey, this isn't in conformance ... never a huge block" settles T2 (one line every time, replacing "do not re-offer"); (4) "stay in our lane ... enforced when it's on its own" gives the aim; T5, T6 and T7 were settled afterwards by the owner, in session, 2026-11-05.
- P-127 round 4, the fuller lines (relayed verbatim by claudeops-ce, now written into P-127): "do we change the nature of the job no we shouldn't change the nature of the job" (the wording of the what-may-change rule is PROPOSED); "I do think it could keep offering it" (re-offering a fix in general; its use for a job chosen outside the checker is PROPOSED); "we only have to mirror the stuff that ... would actually need" (the personal folder; the hosts list is PROPOSED, P-127 never names it).
- P-127 rounds 1-3: offer in the moment; asking also works; first real run needs approval; best guess when asked; personal jobs are personal code; the outside-the-checker mark; no session-start line; skill rewriting not planned, not prevented.
- PROPOSED, not in P-127: listed in section 15. DECIDED by the owner, in session, 2026-11-05 (T5, T6, T7): the comment-line form, running a marked job with a one-line warning, a copy of a plugin job as a new-name job, and reporting a broken plugin job on the plugin's GitHub page.
- Code: `system/tools/install-schedulers.sh` (`DOOR_NEXT_STEP_*`, scaffold call before the OS step), `system/tools/job-run.sh` (personal hosts list, exit 0 and last line `PASS`), `shared/tools/personal_jobs_scaffold.py`, `shared/personal_code_root.py`, `system/tools/bootstrap.py` (`scaffold_personal_jobs`), `system/tools/tests/job-sim.sh` header 5.15.
- Rulebook: `cron-jobs-sop.md` §3, §5-§7, §10-§12; `build-conformance-sop.md` §1.5.

## 12. The switch-on protocol

A row flips from `off` to `yes` one job at a time, only at a human gate, on the person's word. (A PROPOSED line on a row that was `yes` is in section 15.) At the gate:

1. Confirm the migration still holds: `--check-row` PASS (`rc=0`, last line `PASS`), the rig green, and, if the person said yes to a test run, the forced test run still passes.
2. Apply the job's one-time fixes (stale feed, stale skill that invokes it).
3. Ask the person three questions: (1) is this spend necessary for the outcome in the row? (2) watch the first run in a session, or background? (3) fix the invoking skill now? For a job that reads a backlog, also ask how to handle it.
4. On the word: flip `enabled` to `yes`, run `install-schedulers.sh --install`, then one forced test run (on the person's yes, as in section 11 step 8).
5. Passive after. The gate is passed when the row's check passed once live and the session line names the job OK. Do not wait on a soak: force a test, then read the record at the next gate.

No job waits for a card to be switched on.

## 13. Debugging a job

- Session line says `never ran: x`: enabled but no `last-run`. Run `job-run.sh x --force` by hand and read the log.
- `N overdue: x (9h)`: no success in 2 x interval. Read `errors/` newest first, then `log`.
- `stood down: x (reason)`: rc 75 is deliberate; read the reason before touching anything.
- `jobs cannot find the code`: `launch.err` is non-empty. Open any desk once; the hook rewrites the pointer.
- `paused: <label>`: the sentinel found a real injection in that label. Only a person removes the line from the pause file.
- Always read `last-run` first: `rc`, `calls`, `secs` and the reason usually answer it.

## 14. Texts are written for a person

Every text that reaches the person's phone is read by a regular person, not a programmer.

**Every text answers three things, in plain words:** what happened · whether it matters · what to do (or "nothing to
do"). A text that needs the person ends with: **"Open Claude and say: what broke?"**

**Every text carries a short plain title** (default "Lifehack", set by `notify-send.sh`). On 2026-10-29 a set of
title-less texts reached the alert server but never popped up on the phone; with a title they did. The cause was not
proven, so the title is the safe rule. Never send a text without one.

**Never in a text:** a job's code name (use its plain name from `system/job-names.txt`, or from `<personal-code>/job-names.txt` for a person's own job, one line per job), an exit
code, a file path, a script name, a flag, or a word only a programmer knows ("output check", "stood down", "rc").
**A new job adds its plain name** in the same change that adds its row: to `system/job-names.txt` for a plugin job, to `<personal-code>/job-names.txt` (`<job> = <plain name>`, one line per job) for a person's own.

**Only something that needs the person right now may wake them at night** (a dangerous email the security
system blocked). Everything else waits until morning.

**The wording lives in ONE place:** `system/tools/job-texts.txt`, so it can be changed without touching code. A new
kind of text is added there, in the same voice, never written inline in a runner. The wording the person approved
(2026-10-29), with `{name}` the plain name and `{last_ok}` / `{since}` a time like "2:10 PM" or "Tuesday 8 AM":

| when | text |
|---|---|
| it broke | ⚠ Your {name} stopped updating. It last worked at {last_ok}. Nothing is lost. Open Claude and say: what broke? |
| it never worked | ⚠ Your {name} stopped updating. It has not worked yet. Nothing is lost. Open Claude and say: what broke? |
| it's fixed | ✅ Your {name} is working again. |
| paused too long | ⏸ Your {name} has been paused since {since}, so it isn't updating. Open Claude and say: what broke? |
| hasn't run | ⚠ Your {name} hasn't run since {since}. Your Mac may have been off. Open Claude once and it will check. |
| hasn't run since switch-on | ⚠ Your {name} hasn't run yet since it was switched on. Open Claude once and it will check. |
| running again | ✅ Your {name} is running again. |
| dangerous email (may wake you) | 🛑 I blocked a suspicious email. It looked like an attempt to trick your assistant. I didn't open it, and I've paused reading that folder. Open Claude and say: what broke? |
| the alert system itself | ⚠ Your alert system needs a quick fix: its memory got damaged, so it might repeat or miss texts. Open Claude and say: what broke? |

**The check is the person.** At every switch-on gate (section 12) the person sees the job's real texts on their phone
before saying yes. A text they cannot understand is a reason to say no.

## 15. Questions for the person (PROPOSED lines, not live text)

These lines were PROPOSED in the live text, not ruled. They wait here, word for word, for the person's ruling (P-40).

- From section 11a, "Where a person's own jobs are saved": **PROPOSED:** each piece comes with a template, created when missing and never overwritten (P-127 asks for "a location and all the folders and everything it needs", not for templates).
- From section 11a, "What may change, and what may not": **PROPOSED:** the reading of that as "a fix does not change what the job reads, writes or sends, apart from its own receipt line and exit code"; P-127 gives neither that wording nor the examples. Two fixes are allowed under it: the presence-grade check fix (the receipt line and the check are made to carry a value that varies) and the "nothing to do" exit 75.
- From section 11a, "What may change, and what may not": **PROPOSED:** this section adds no new block of its own (P-127 does not say it).
- From section 11a, "The window offers": **PROPOSED:** the line says that the job's own code changes and what it reads, writes and sends does not. **PROPOSED:** a job the person chose to run outside the checker (below) gets the same one short line. P-127 round 4 says "I do think it could keep offering it" about re-offering a fix in general, and adds "If adding that in makes it harder, then fuck it. We'll just warn them one time and leave it"; it does not name a job already chosen outside the checker, and round 3 dropped a repeated session-start line as annoying. **PROPOSED:** a no leaves everything as it is.
- From section 11a, "Whose job decides the refusal": The exact wording is PROPOSED (not in P-127), as coded in `install-schedulers.sh`.
- From section 11a, "A broken plugin job": **PROPOSED:** this also holds when the fault is inside a plugin runner or shared script that a personal row calls: report it, change nothing in the plugin (P-127 speaks of a broken plugin job, not of a personal row that calls one).
- From section 11a, "Copying a plugin job to change it": **PROPOSED:** the window says that warning in one plain line before the copy is made (the wording is the draft's).
- From section 11a, the fix table, the web-fetch row: **PROPOSED:** P-127 round 4 says "we only have to mirror the stuff that ... would actually need" outside the plugin to save a job, and never mentions a hosts list.
- From section 11a, the fix table, the vendor-read row: **PROPOSED:** add a line only if the person chooses it in their own words.
- From section 11a, "The steps", step 5 (after "approval first"): Say what a run does for real: the runner's own writes and any model spend; no email bookmark moves and no alert is sent. On the yes: `bash $CODE/system/tools/job-run.sh <name> --force`, then read `last-run` and `log`. Without a yes, report the job as checked and rig-tested, not run.
- From section 11a, "The steps", step 6: **PROPOSED:** a row already `yes` goes to `off` first (with the person's yes), is fixed, and returns through §12.
- From section 11a, after "The steps": **Cannot pass?** Stop, say what refuses it and why, and ask what they want, with your best guess (PROPOSED). Nothing is installed, switched on or loosened meanwhile.
- From section 11a, "A person may knowingly run their own job outside the checker", step 4: **PROPOSED:** the offer line above still applies each time the refusal comes up for such a row (see the offer section: P-127 does not name this case); it is one line, never a block.
- From section 11a, "Sources": PROPOSED, not in P-127: the exact wording of both refusal texts (code, dated 2026-11-05, no owner named), the example offer line, the fork-warning wording, "a no leaves everything as it is", step 5's details, step 6's `off`-first.
- From section 12: **PROPOSED:** a job whose row was `yes` and which has been changed to pass the door goes back to `off` first and comes through this gate again (section 11a, step 6).
