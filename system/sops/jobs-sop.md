---
topic: [system-architecture]
id: system-playbook-jobs-sop
title: "Jobs SOP: how a scheduled job is added, checked and switched on"
record_type: playbook
status: active
authority: user
reader_note: "Self-monitoring task 5.8, written 2026-10-29 from the build window's draft and corrected for the 2026-10-28/29 rulings. How it works lives in system/organism/manual.md (CRON AND ALARMS); this file is the HOW-TO. If either disagrees with the code, the code wins."
---

# Jobs SOP

**Read this first.** A scheduled job is an alarm clock plus an envelope around something you could run by hand. This SOP owns the alarm clock and the envelope: the **Cron** subsystem (it runs jobs) and the **Alarms** subsystem (it tells you one broke). It does NOT own what happens inside the routine, and nothing in this SOP is a reason to edit a skill. Every path here is in the HARNESS home, resolved from the plugin root (manual, THREE HOMES), never relative to your working folder. `$CODE` below is the harness code root: whatever `$HOME/.config/lifehack/code-root` says. Never type it as a path.

## 1. The three layers

| layer | plain name | its one question | owner |
|---|---|---|---|
| trigger | the alarm clock | is it time? | launchd (macOS), cron (Linux), schtasks (Windows) |
| job | the envelope | did one run start, finish in time, and pass its content check? | this SOP: `job-run.sh`, the row, the door, the texts |
| routine | the steps | what are the steps, in what order, and which one broke? | the skill; drawn as a card when it needs one |

- Keep the top two dumb. A row's command checks whether there is work, then starts the routine, or stands down with 75. Anything longer belongs in the skill.
- The test: if a person can run it by hand as a slash command or a script, that thing is the routine. The schedule is one way of pressing its button.
- The seam has two points only. (1) The command runs the routine. (2) The check reads the routine's result. Neither side needs the other's inside.
- Card or no card is the skills rule, not this SOP's: `system/sops/skill-building-sop.md` PART 0 ("The Hospital": the nurse-and-chart picture of how a skill runs its steps), section "When NOT to use a card", bullet "Decision rule: card or no card". Read it there; do not copy it here. A card is an upgrade, never a prerequisite: a job can be scheduled with its routine as it is.
- Bugs: ask "which layer?" first. Did not fire: trigger. Did not come back, or the check failed: job. Step N was wrong: routine.

## 2. The ALWAYS rules

Every job obeys these, carded or not. The door and the rig enforce what code can judge.

1. A check tests CONTENT, never presence. A file existing, being non-empty, being fresh, or holding an exit code proves nothing.
2. A step that changes something is safe to run twice, or records what it did before acting. Writes to the owner's own Google account have no shared writer: the routine calls them directly, so it must make them repeat-safe itself (for example, record each item's message id in a ledger BEFORE the append and skip ids already there; or write in place by a key column).
3. Exit 0 is never proof of work. Check the artifact. A bookmark moves only on rc 0 AND a passing check.
4. Never silence a step's errors. A failed fetch must not read as "nothing new".
5. The runner writes the record. The AI never does. AI steps get only the tools they need (today: read-only; per-job grants scoped to the job's own output folder are ruled, not yet built). The AI can never write job state or a bookmark.
6. Refuse a truncated or corrupt record, loudly, and name the file.
7. Test the tester first: plant known faults and see every one named (the rig's bite, section 10).

Also from the system laws: "ran" is not "succeeded" (dead end F2, 166 silent failures). No job writes job state to Drive: content yes, state no.

## 3. The layer law (what is shared, what is the desk's)

- If two desks would WANT it to behave differently, it is the desk's: prompt, verdict set, what is written, where.
- If a person would be UPSET that it behaved differently in two desks, it is shared, exactly one copy in `$CODE`: fetch, sanitise, scan, pause, auth, lock, timeout, output check, cost, notify, state location.
- The middle is shared shape, desk content: the loop and its guardrails are shared; the desk hands in its prompt, closed verdict set and output format.
- Where files live: shared code in `$CODE` (the public harness). Desk runners, prompts and notes in the private desk repo (default `$HOME/.claude/skills/ClaudeOps`, override `LIFEHACK_DESK_REPO`) and the notes folder. Never put desk code in the public harness. Never copy a shared file into a desk.
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
| 75 | stood down: nothing configured, not logged in, not overdue, row not `yes`, lock held by a live owner | never a fault, never a page, always shown on the session line |
| 2 | transient (network, Google 5xx) | retried next period |
| other | failed | `errors/` file written; counts toward the alert |

**Alert rule (Alarms).** A failed run (any rc not 0 or 75; 2 counts) pushes ONCE when `last-success` is missing or at least 2 x interval old (the second miss), then leaves `alerted`. The next success pushes one recovery and removes it. A push that fails never changes the exit code. A `--force` run never pushes. Being built (self-monitoring 5.10): `alerted` is written only on a confirmed send, so a failed text retries; a job that keeps standing down texts once; every run checks the other jobs and texts once for one that is not running.

## 5. The row contract

One row per job, in the `jobs` block of `$CODE/system/pulse-config.md`:

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
| source | the shared reader that FEEDS it (what it reads, never what it writes): `gmail`, `web`, `gsheet` or `none`. A job that reads email and writes a Sheet is `gmail`. `gmail` makes job-run load the Google credentials |
| command | LAST, because it may contain `\|`. Literal bash, or a leading-`@` builtin. No other column may contain `\|` |

A row describes the envelope only. It does not carry steps, prompts or verdict lists. `TBD` in any contract column means the job can never succeed and the door refuses it.

## 6. The check

`<path> ~ <regex>`, split at the FIRST ` ~ `. It passes only when the file exists, was written after this run started, and some line matches the regex (`grep -E`). `$HOME`, `$LIFEHACK_CODE_ROOT` and a leading `~` expand in the path. No `|` in the regex: write alternation as an optional group.

Write the check against the outcome sentence, and make it match something the routine had to do real work to produce (a count of 1 or more, a verdict word, a date). The receipt it reads is written by the runner AFTER it verified the artifact, never by the model.

The door refuses presence-grade checks (5.9): a regex that tests only an exit code written to a file (`"rc":0`), non-empty (`^.+$`), or existence or mtime alone (a check without ` ~ `). Wrong: `last-run.json ~ "rc":0`. Right: `receipt.txt ~ ^example-digest ok .*items=[1-9]`.

## 7. The door

`install-schedulers.sh --install` refuses a `yes` row, writes no plist, prints the reason, and exits 1. `install-schedulers.sh --check-row <name>` runs the same test on any row and prints `PASS` or the reasons. A row is refused for:

- a missing or `TBD` contract column, a bad model word, or a bad budget;
- a presence-grade check (5.9);
- a runner outside `$CODE` and the private desk repo, or a pinned code path (a clone or plugin-cache folder) where `$LIFEHACK_CODE_ROOT` belongs;
- a raw outside READ (Gmail or Calendar reads, sheets `values get`, `curl`, `urllib`, `requests`) anywhere in the runner, what it sources or invokes, or the helper files beside it. Only files named in `system/tools/shared-fetch-allowlist.txt` may hold one. Never add a desk runner to that list. **Writes** to the owner's own Google account (labels, archive, Sheets, Tasks, Calendar, Docs) are allowed: an accepted risk (ruled 2026-10-28). **One vendor-read exception:** a row with `model=none` may make its own logged-in read of the owner's own vendor account from ONE file listed in `system/tools/vendor-read-allowlist.txt`; it ends if the row gains an AI step;
- a literal model id (or `--model X`) anywhere outside `model.lib.sh`. Name a tier;
- a silenced error (5.9): `|| true`, `|| :` or `2>/dev/null` on a fetch, write, push or model call. Stderr goes to the job log.

The static scan follows `source` and `bash`/`python` invocations. It does not follow Python imports, so keep raw calls out of imported modules too. Session side: the ingest-gate hook refuses the same raw reads typed in a session. Honest limit: a person typing a raw command in a terminal is outside the system.

**Reads go through the shared fetch.** Email: `shared/tools/email_fetch.py` only. What it hands back is already sanitised, scanned and judged: a message the judge could not clear is withheld (the run fails loudly), and a real attack pauses the label and sends one critical text. A runner never re-reads the raw message. It sets NO read policy: the job must pass `--query`, `--cap` and `--since`. Which mail, how many and from when is the SKILL's decision, made with the owner when the skill is built; never a default here. Web: `system/tools/safe_fetch.py` and `safe_search_api.sh`; job-run seals web reads to `system/tools/job-fetch-hosts.txt` for scheduled runs, so add a host there. Sheets: `safe_sheets.py`. Push: `shared/notify/notify-send.sh` only, and a runner usually should not push at all because job-run alerts. The credentials live only in the shared fetch; never export them into a runner.

## 8. State, locks, bookmarks (5.9)

- A corrupt state, governor or bookmark file is refused and named: the run fails and the text names the file. It never "starts fresh".
- Email bookmarks are `$HOME/.config/lifehack/<consumer>-last-seen`. The fetch writes `<consumer>-last-seen.pending`; job-run promotes it to the real file only on rc 0 AND a passing check. A fetch that peeked never advances anything.
- Locks record the owner pid. A dead owner's lock is taken at once. A live owner gives exit 75, never 0. A runner's own lock contention also exits 75.
- Where a new consumer starts reading (its bookmark) is that skill's read policy, set with the owner at its gate. An unattended job never drains a backlog without the owner deciding it.

## 9. The cost line (`last-run`)

Every run that gets past the overdue test rewrites `last-run`:

```
<ISO time> rc=<n> calls=<N> secs=<S> model=<tier> ccv=<claude version> <reason>
```

`calls` and `secs` are the model calls this run made through `run_model` (0 and 0 for a job with no AI). `ccv=` is the Claude version (5.9). To call a model, a runner sources `$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh` and calls `run_model <tier> <prompt-file> <out-file> [marker]`. It maps tier to id from the one table, takes the token, times out (`MODEL_TIMEOUT`, default 600 s), refuses an empty reply or a missing marker, counts the call, and refuses the call that would exceed `budget`. AI steps run with only the tools they need (today read-only, `--allowedTools Read`; per-job grants scoped to the job's own output folder are ruled, not yet built): the runner writes every file and the record, the model returns text. A model failure `run_model` recorded fails the run and is named even if the runner swallowed the return code.

## 10. The rig

`system/tools/tests/job-sim.sh` replays days in seconds against the real `job-run.sh`, `health_line.py` and notify scripts, on a fake clock and a throwaway state tree. It never touches real state, pushes or the network.

- Run it green before every commit, and with `--gate` at every gate (200 fuzz reps).
- `--bite` (5.9) plants known faults, one per rule, and asserts each is caught and NAMED exactly. `--gate` runs the bite first (5.9). A rig that was never shown to fail is not trusted.
- A change that cannot be expressed as a rig scenario is suspect. Add the scenario first.
- **Every job adds one scenario** before its forced run: a `<job>-contract` scenario that runs the real row under the rig with a stub, and proves its check passes on a good output and fails on an empty or wrong one. Copy `marc-health-contract` or `mirror-fetch-contract` in `job-sim.sh`.
- Not covered by the rig: real launchd wake behavior, real logins, real push delivery, real Google or Claude auth. One live `launchctl kickstart` per gate keeps those honest.

## 11. Add a job (the recipe)

A blind session can do this from here alone. Never skip a step; never flip the row to `yes` (section 12).

1. **Write the outcome in one sentence.** If you cannot, the job is not ready.
2. **Decide the layer.** The routine (steps, prompts, verdicts) is a skill, or a script a person can run by hand. If it needs a card, stop and use the skills SOP v2 PART 0 rule. This job is only the envelope.
3. **Write a thin runner.** A job that serves ONE owner's desk lives in the private desk repo (`desks/<desk>/tools/<job>/`); a job every installer would want lives in `$CODE/system/tools/`. Never copy shared files into a desk. Resolve everything from `$LIFEHACK_CODE_ROOT`. Use the shared fetch for any read, `run_model` for any AI call, no silenced errors, exit 75 when there is nothing to do or a lock is held, and write a receipt AFTER verifying the artifact.
4. **Add the row, `off`.** Fill all five contract columns. Check the interval against section 4.
5. **Run the door:** `bash $CODE/system/tools/install-schedulers.sh --check-row <name>` until it prints `PASS`.
6. **Read policy** (if it reads email): the query, cap and start point the skill decided with the owner. Do not invent one.
7. **Add the rig scenario** (section 10). Run `bash $CODE/system/tools/tests/job-sim.sh`.
8. **One forced dry run:** `bash $CODE/system/tools/job-run.sh <name> --force`. Read `$HOME/.config/lifehack/state/jobs/<name>/last-run` and `log`. Expect `rc=0 ... [check] ok`. A forced run pushes nothing and never changes the row.
9. **Commit** shared work to `$CODE` and desk work to the private desk repo, per the GitHub SOP. Report what the run proved and what it did not test.

**Worked example.** A job that summarises a local drop folder once a day with one small model call.

Row (one line in the `jobs` block):

```
example-digest | off | 86400 | Each day the files in the drop folder are summarised in one note and the receipt records at least one item. | $HOME/.config/lifehack/example-digest/receipt.txt ~ ^example-digest ok .*items=[1-9] | small | 2 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/example-digest-run.sh"
```

Runner `$CODE/system/tools/example-digest-run.sh`:

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

## 12. The switch-on protocol

A row flips from `off` to `yes` only at a human gate, on the owner's word, one job per sprint, never in the prep phase. At the gate:

1. Confirm the migration still holds: `--check-row` PASS, the rig green, the forced dry run still passes.
2. Apply the job's one-time fixes (stale feed, stale skill that invokes it).
3. Ask the owner three questions: (1) is this spend necessary for the outcome in the row? (2) watch the first run in a session, or background? (3) fix the invoking skill now? For a job that reads a backlog, also ask how to handle it.
4. On the word: flip `enabled` to `yes`, run `install-schedulers.sh --install`, then one forced run.
5. Passive after. The gate is passed when the row's check passed once live and the session line names the job OK. Do not wait on a soak: force a test, then read the record at the next gate.

A carded routine is switched on the same way: its row runs the card's runner and its check reads the run's record. No job waits for a card to be switched on.

## 13. Debugging a job

- Session line says `never ran: x`: enabled but no `last-run`. Run `job-run.sh x --force` by hand and read the log.
- `N overdue: x (9h)`: no success in 2 x interval. Read `errors/` newest first, then `log`.
- `stood down: x (reason)`: rc 75 is deliberate; read the reason before touching anything.
- `jobs cannot find the code`: `launch.err` is non-empty. Open any desk once; the hook rewrites the pointer.
- `paused: <label>`: the sentinel found a real injection in that label. Only a person removes the line from the pause file.
- Always read `last-run` first: `rc`, `calls`, `secs` and the reason usually answer it.

## 14. Texts are written for a person (operator's rule, 2026-10-29)

Every text that reaches the owner's phone is read by a regular person, not a programmer. The operator, on the first
drill: *"I have no idea what drill never, drill fail [means]. None of this stuff is written for humans."*

**Every text answers three things, in plain words:** what happened · whether it matters · what to do (or "nothing to
do"). A text that needs the owner ends with: **"Open Claude and say: what broke?"**

**Never in a text:** a job's code name (use its plain name from the jobs table's name list), an exit code, a file
path, a script name, a flag, or a word only a programmer knows ("output check", "stood down", "rc").

**Only something that needs the owner right now may wake them at night.** Everything else waits until morning.

**The wording lives in ONE place** (the message file beside `job-run.sh`), so it can be changed without touching code.
A new kind of text is added there, in the same voice, never written inline in a runner.

| instead of | write |
|---|---|
| Job down: email-summary-write · exit 1 · last success 6h ago | ⚠ Your email summary stopped updating. It last worked at 2:10 PM. Nothing is lost. Open Claude and say: what broke? |
| Job recovered: email-summary-write | ✅ Your email summary is working again. |
| Job standing down: x · no gws credentials | ⏸ Your email summary is paused: your Google login expired. Open Claude and say: reconnect Google. |
| Job not running: x · launchd agent may be unloaded | ⚠ Your email summary hasn't run since Tuesday. Open Claude once and it will check. |

**The check is the owner.** At every switch-on gate (section 12) the owner sees the job's real texts on their phone
before saying yes. A text they cannot understand is a reason to say no.
