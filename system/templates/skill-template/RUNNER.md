# RUNNER.md — wiring the step runner into a long skill

How a multi-stage skill uses the parts-library step runner, `system/parts/stage_runner.py`.
Read with `card.template.json` (beside this file) and the skill-building SOP.

## What the runner owns (and you never re-build)

- **The stage order.** The session never chooses its next stage; the runner does. Stage N+1
  is reachable only through a verified pass on stage N.
- **The run record.** `record.jsonl` in the run folder — append-only, hash-chained,
  re-verified whole on every read. ONLY the runner writes it. Damaged record → exit 6 and
  every command but `verify` refuses.
- **Next / back.** `advance` hands over to the next stage; `back` re-opens the previous one
  with a fresh code word. On a talk step both need the person's typed command (see below).
- **The status line.** `statusline` prints `RUN n/N stage (mode)`.

## Wiring, in order

1. **The card.** Copy `card.template.json` into the skill folder as `card.json`. One entry
   per stage: `id`, `mode` (`talk` = converses with the person, moves on with /next;
   `alone` = runs unattended, advances on a verified pass), optional `optional` (boolean
   only — see "Optional steps" below), `prompt` (a prompt file beside
   the card, using `{{CODE}} {{OUT}} {{PREV}} {{ID}} {{MODE}} {{N}} {{TOTAL}}`), `out`
   (where the stage writes), optional `inputs` (default: the previous stage's `out`),
   and `checks`.
2. **The checks.** Every content check must be one the runner already knows: its own
   (`headings`, `min_words`, `code_word`, `extra`) or a delegated part (`forbid` →
   forbidden_content.py, `require_sections` → section_present.py, `order` → order_lint.py,
   `phase_gate` → phase_gate.py). A card naming a check whose part is missing is refused
   at `start` (fail-closed). "The file exists" is not a check.
3. **The commands.** (⛔ not files in this repo: `start` writes them at run time into the skill folder.) `start` writes `.claude/commands/next.md` and `back.md` into the
   workdir (an unregistered slash command never reaches the hooks).
4. **The hooks.** Registered through the plugin's register (`system/register/register.jsonl`
   → generate), never by hand — that happens when the skill is built (skills SOP / plan
   4P.5). The runner's `statusline` is the status-line wrapper.
5. **The no-AI finish check.** `stage_runner.py --selftest` proves the three plants:
   a hand-edited record is reported DAMAGED (exit 6) and the runner refuses to advance;
   a stage run out of order is refused (exit 3); a card naming a missing check part is
   refused (exit 2). Each is shown FAILING first against a deliberately broken runner
   variant built in a temp dir.

## Commands (the ONE list; the docstring of `stage_runner.py` points here)

All take `--workdir DIR` (default: the current folder).

| Command | What it does |
|---|---|
| `start --card CARD [--run-id ID]` | Begins a run (stores `card_sha`). Marker's run complete: the marker is renamed `.stage-runner.json.done-<run>` and a NEW run starts from step 1 (old code words fail). After `abandon`: starts a new run. Run unfinished: exit 4. |
| `status [--json]` | Where the run is. `--json` adds `snoozed` and `abandoned`. |
| `check` | Runs the current step's checks; writes nothing. |
| `advance [--turn T] [--via V]` | Checks the step, then hands over. |
| `back [--turn T]` | Re-opens the previous step, exactly one, with a fresh code word. |
| `person-turn --turn T --cmd next\|back` | Appends the person's typed command as a `person` line. The ONLY writer of `person` lines. A used turn id: exit 4. A finished run: exit 4. |
| `resume --choice continue` | Reissues the CURRENT step's instructions with a fresh code word ("update the Code word line in <out file>"). Half-done handover: exit 7 (run `recover` first); finished or abandoned: exit 4. Writes no pass/done. The old code word is then refused: "another window took over this run at <time>" (exit 3). Records the newest person prompt from `<run folder>/person.log` in its record line. |
| `abandon --choice start-over` | Appends `abandoned` (with the newest person prompt) if the record verifies; always renames the marker to `.stage-runner.json.abandoned-<run>` (a COMPLETE run gets `.done-<run>`), even on a damaged record, unreadable card or bad marker. Deletes nothing; never writes pass/done/complete. |
| `snooze --choice leave-it` | Appends `snoozed` (with the newest person prompt); the reader stays quiet for this run until a later `person` or `reissue` line (a later `resume` lifts it). |
| `recover` | Completes a handover that died between `intent` and `done`. |
| `verify` | Chain + replay rule + the mover's logs; writes nothing. Reports a `person` line whose turn is not in `<run folder>/mover.log` ("person line not written by the mover", exit 3); a `reissue`/`abandoned`/`snoozed` line whose recorded person prompt is missing from `<run folder>/person.log` or older than the last reissue (exit 3); a changed or unreadable card (exit 6); any record line after `abandoned` (exit 6). The mover hook writes `mover.log` (one `prompt_id` per line) and `person.log` (`prompt_id` and unix time for EVERY person prompt while a run is open); the runner never does. |
| `statusline [--inner CMD]` | Reads Claude Code's status JSON; prints `RUN n/N stage (mode)`. |
| `--selftest` | The no-AI finish check. |

`--choice` is validated against the closed menu (`continue` / `start-over` / `leave-it`, each command
takes its own word); anything else is exit 2, "ask the person again".

## Record events

`start` (with `card_sha`) · `person {turn, cmd}` · `pass` · `fail` · `handover` · `back` · `intent` ·
`done` · `complete` · `reissue {code_hash, choice}` · `abandoned {choice}` · `snoozed {choice}` ·
`recover`. Replay rule: a forward `intent` needs a `pass` of the step it leaves since that step
opened, `done` needs its `intent`, `complete` needs the last step's pass; a card or prompt file
edited mid-run reads as DAMAGED ("card changed mid-run").

## The person-turn rule, and talk vs alone

- A **talk** step moves only on the person's typed command: `advance` needs an unconsumed
  `person{cmd:next}` with the same `--turn` (none: exit 3 "no person turn"; turn already used:
  exit 4). `back` always needs an unconsumed `person{cmd:back}` with its `--turn`.
- A **person line is consumed by its first use, whatever the result**: a failed check means the
  person types /next again. One person turn moves the run at most one step; typing /back
  twice with one turn id goes back one step.
- An **alone** step advances on a verified pass alone, as before; no person is needed.
- Only `person-turn` writes `person` lines. Renaming a `.abandoned-` marker back revives
  nothing: `advance`, `back` and `person-turn` refuse once the record says `abandoned` (exit 4),
  and `verify` reports any line after `abandoned` as damaged.
- **Optional steps (the owner's yes, 2026-11-23): "if number four is pretty easy to fix let's just
  do that".** A talk step marked `"optional": true` may be skipped BY THE PERSON: when `advance`
  runs on a `person{cmd:next}` turn (same `--turn`, the normal turn gate) and the step's checks
  fail or its output is missing, the runner records a `pass` with `{"skipped": "by the person",
  "turn": <the turn's prompt id>}` and hands over as normal — no new command. Without a person
  turn it is refused exactly as today: the AI can never skip. A non-optional step is unchanged.
  The replay rule accepts the skipped pass because it names the person turn; `verify` stays OK.
  Card validation accepts the boolean only — anything else is refused at `start` (exit 2).
- Friction, not perfect enforcement: forging the record is a named bypass, and it shows as damage,
  a `person` line missing from `mover.log`, or a `reissue`/`abandoned`/`snoozed` line whose person
  prompt is missing from `person.log`.

## Exit codes

0 OK · 2 USAGE / cannot-evaluate / bad `--choice` · 3 CHECKFAIL (stage refused; also "no person
turn", "another window took over this run", unlogged person line in `verify`) · 4 NOTHING (no-op,
repeat turn, unfinished run on `start`) · 5 NORUN · 6 DAMAGED (record failed verification,
card changed, bad marker) · 7 DANGLING (run `recover`).

**A job wrapper maps 4 to the cron stand-down code itself** — the runner's 4 means "nothing to do",
and the wrapper decides what that means to the scheduler.
