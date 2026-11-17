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
  with a fresh code word.
- **The status line.** `statusline` prints `RUN n/N stage (mode)`.

## Wiring, in order

1. **The card.** Copy `card.template.json` into the skill folder as `card.json`. One entry
   per stage: `id`, `mode` (`talk` = converses with the person, moves on with /next;
   `alone` = runs unattended, advances on a verified pass), `prompt` (a prompt file beside
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

## Exit codes

0 OK · 2 USAGE / cannot-evaluate · 3 CHECKFAIL (stage refused) · 4 NOTHING (no-op) ·
5 NORUN · 6 DAMAGED (record failed verification) · 7 DANGLING (run `recover`).
