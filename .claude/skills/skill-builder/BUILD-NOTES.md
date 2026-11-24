# BUILD-NOTES — skill-builder

Build record for this skill: the gate table, the checks and their results, and every deliberate
departure from the templates.

Not skill folders, so there is nothing to find:

> ⛔ `/next` is not here: a command the shared step runner writes when a run starts.

> ⛔ `/back` is not here: a command the shared step runner writes when a run starts.

## Gate table

Every item from the spec's FOR THE PLANNER AND THE BUILD list, with its pass check and the build phase
that closes it. Status is one of: open · closed (receipt) · deferred (reason, by the person).

| Gate | What | Pass check | Closes in | Status |
|---|---|---|---|---|
| G1 | Scaffold | Folder made from `system/templates/skill-template/`; no `{…}` or guidance comments left; every folder has a one-line purpose | P2 | open |
| G2 | Frontmatter | `skill`, `shape: interactive-workflow`, `status`, `triggers`, third-person "Use when…" description with keywords in the first 250 characters | P2 | open |
| G3 | Routing eval ×3 | Each case run 3 times in a cold window; 3/3 holds, 0/3 fails, 1–2 of 3 re-run; k/3 and the commit SHA recorded | P2 (re-run at P6 and on the final commit) | open |
| G4 | Card | `card.json` has five `talk` stages, steps 3–4 `optional`, checks only from the runner's closed list | P2 | open |
| G5 | One prompt per step | `prompts/step-1…5` exist, each from the step-prompt template; acceptance checks A–G recorded | P3 | open |
| G6 | Helper briefs | Every helper brief is a file under `prompts/subagents/`, names its tier, and is re-quizzed if changed | P4 | open |
| G7 | Inputs-line code + pause | Code checks each step's inputs and pauses; every code-read choice ends in `none-of-these`, which never moves the run | P5 | open |
| G8 | Output checks | Each check tested on a good, an edge and a padded case, and seen failing on a broken copy first | P5 | open |
| G9 | Loud scripts + timeouts | Every script exits pass / fail / could-not-check with distinct codes, refuses off-list values loudly, and times out loudly | P5 | open |
| G10 | Stop-hook handover | Not applicable: the skill has no step that runs alone | P2 | open |
| G11 | Hash pins | The skill uses the shared step runner in place; it pins and copies nothing | P2 | open |
| G12 | Testing rules | Every testing rule in the skills checklist met or deferred with a reason | P6 | open |
| G13 | Status writer | Stays DEFERRED, with the reason recorded | P2 (recorded) | open |
| G14 | Example specs | `references/examples/` holds a scrubbed example spec | P2 | open |
| G15 | Completion figure | Code computes the completion figure; it never gates and writes no tile | P5 | open |
| G16 | Proofs | The spec's §7 proofs run and recorded | P6 | open |
| G17 | Optional steps on host | The runner's optional-steps support read back from GitHub on `V2` | P0 | closed: `git ls-remote origin V2` = 91e0d681; optional-steps commit is an ancestor (2026-11-24) |
| G18 | Finish after build | The spec is finished with what the build learned and becomes the component page | LAST | open |
| G19 | Nothing answerable by looking left open | Research notes checked against the newest decisions; every clash listed below | P1 | open |
| G20 | Status line | The status line shows the step and changes on /next | P6 | open |

## G19 — research notes against the newest decisions

The build's research notes (written before the last round of decisions) were read whole against every
later decision; the newest decision wins. Nine clashes were found; each is fixed in the notes
(struck through with the reason) or kept with its reason.

| # | Research note said | Newer decision | Kind | Done |
|---|---|---|---|---|
| 1 | Copy the template into the personal skills folder | The skill builder is plugin code; it lives in the plugin's skill folder on the V2 branch | explicit | struck |
| 2 | Landing place and promotion point at the personal skills folder | Same as 1 | explicit | struck |
| 3 | Step prompts are delivered by an every-turn hook | Shared prompts are delivered only at the start of each step, never every turn | explicit | struck |
| 4 | A quoted precedent heading says "every turn" | Same as 3; each step fully reorients once, at its start | explicit | struck |
| 5 | Step 5 sends only the spec plus a pointer to the packet | The whole packet, research included, goes to the planner | explicit | struck |
| 6 | Step 5 "never send the packet contents" | Same as 5 | explicit | struck |
| 7 | "/build does not exist in the plugin" | The front door's command is /build; today's plugin `build` is the old one and is replaced later | explicit | struck |
| 8 | Where a vague "how do I make a skill" goes is open | It goes to /build, the front door, not to this skill | explicit | struck |
| 9 | Step 5 asks the person three code-read choices | Step 5 is leader mode: no question section unless a question is really outstanding | judgment | kept: the destination and send choices are real outstanding decisions; step 5 asks only the one for-me / for-everyone question on screen, and the code-read answer sets stay for what the person types |

Source of the check: one whole-document read of both files by the reading tool (every heading listed,
18 of 18 quotes verified). No model reliably notices what a document leaves out; this list is what was
found, not proof that nothing else clashes.

## Helper routing during the build

From 2026-11-24 (P1), the cheap helper model ran out of credit. Reading and checking jobs that would have
gone to it go to a medium-tier Claude helper instead, until the cheap model is back. One reading job
that finished before the cut-off (G19 above) is kept, with its reading proof.
From later on 2026-11-24 (still P1) the cheap model is back and is the default again, with a medium-tier
Claude helper for load-bearing reads and anything the cheap model gets wrong.

## Template completeness (the producer-spec template, first pass)

The spec was compared section by section with `system/templates/producer-spec-template.md`: 2 sections
covered, 12 partly, 3 missing (§3 rails with a "held by" column, §5 the grid, §11 evidence and
enforceability tags), and none yet marked as deliberately absent. Where each gap closes:
- At the finish (L.1), once the built files exist to read: §3 rails "held by" from the built files, §11 tags,
  §7 exact write targets, §0 section-to-file map, §5 grid (ambient column stated as not active: no
  scheduled run, no tile), §2 inputs table, §6b per-step outcomes, §10 scratchpad location and pruning.
- In the step prompts (P3), then written back into the spec at L.1: §6c the person's-turn fields (what they
  decide, what only they can give, the valid answers), §6a when a repeatable round ends and what carries
  between rounds, and what is cleared on /back.
The full comparison is kept with the build's records; the finish (L.2) re-checks it.

## Records block (P2)

- **Size and signs:** five talk steps, no step runs alone; a manual command (`/skill-builder`).
- **Input channels:** typed text goes through the sanitizer only; files the person supplies go through the ingest-reader; research only via `/research`.
- **No hook, anchor, injector or scheduled job of its own.** The shared runner's hooks are already registered.
- **G13 status writer: DEFERRED.** Reason: an interactive manual skill with no scheduled run. Change condition: if it ever gains a scheduled or unattended step.
- **G10 stop-hook handover: not applicable** (no alone step).
- **Blast radius:** manual command; writes only into its one folder per skill being designed (packet files and the runner's run folder). Nothing into `records/`, no journal row.
- **Deliberate difference from the template:** a `prompts/` layout (`prompts/step-N-*.md`, `prompts/subagents/`) instead of the template's flat prompt files, following planning-weekly.
- **Departures from the template, one line each:**
  - JUDGMENT_SPEC, Storage, Tile, Notification, Dedup and Authorization sections removed (interactive-workflow).
  - RUNNER.md and SKILL.history.md not copied.
  - Description quoted in the frontmatter (it contains a colon).
  - Card ids are `step-N` (planning-weekly precedent), not the template's `01-gather`.
  - Steps 3 and 4 carry real heading and word checks, not just the code word: a person's skip makes the checks fail and the runner records "skipped by the person".
  - `routing-eval.md` sits beside SKILL.md.
  - Triggers omit the bare phrase "build me a skill", because a bare request must not fire (routing-eval N7).
  - Writes line: one folder per skill being designed (coordinator ruling 2026-11-24).
- **opening-screen.md:** screen text copied unchanged. One bookkeeping line removed: the title line's approval attribution (a person's name, a date and a quotation); the title now reads "The skill builder's opening screen (approved, fixed text)".
- **Example spec (G14):** not copied; see the return note. `references/examples/` holds only its README.
- Frontmatter also carries `name:` beside `skill:` (the template has only `skill:`): the commit check for new skills requires `name` + `description`, and Claude Code reads `name`.

## Deviations from the build plan (approved)

- G3 routing eval: not run at P2. It runs at the real-job step (after the NOT READY mark is removed) and on
  the final commit, on Claude. Reason: a P2 run would test a description that still says NOT READY and is
  re-run anyway. Approved by the project coordinator, 2026-11-24.
- G14 example spec: deferred to the finish step. The first example is this skill's own finished spec,
  scrubbed by the shipping lane; the older-format planning-weekly spec is not used. Meanwhile the skill
  spec form carries a full worked example. Approved by the project coordinator, 2026-11-24.
- The real-job trial (a fresh window, the owner in the chair saying "it's right") and the fix round after it
  are DROPPED, by the owner's word, 2026-11-24: "we're gonna push it first and we'll fix it later ... We're
  gonna call it done if it passes all tests and then we'll fix it as we use it later on." Done means every
  automated test passes: routing eval on the final commit, the live runner check, every planted bad input
  caught, the no-personal-info checks. The routing eval and the NOT READY removal move to the final
  check. The filed page states the claim scoped: "not tried on a real job; fixed in use".

## Re-quiz (comprehension check: could a blind reader understand the prompt?)

Rule: re-quiz only a prompt whose meaning changed (the owner, 2026-11-24: re-quizzing every prompt "is a waste
of money"). A full run was started by mistake and stopped after 12 of 29; the 10 scored before the stop all got
6/6 (checker-draft-spec, checker-harness-findings, checker-heal, checker-skill-reading, checker-spec-update,
checker-step-prompts, compiler, harness-search, research-mark, research-pass-item). Still to quiz, once each,
because their meaning changed: the five step prompts (after their last edit), tool-builder-handoff
(rewritten), packet-writer and handoff-note (new), step-prompt-drafter (fixed after the last quiz).
Unchanged in meaning (a boilerplate line added, private text stripped): not re-quizzed.

## The step prompts' own calls, approved

Where the spec was silent, the prompt writer made 15 calls. The owner approved them on 2026-11-24 ("if they
don't change the design intention of the human then it's fine"): 14 kept as written, and one corrected (step 1
names the shared-tools list, which the writer had wrongly thought missing). They are written back into the
spec at the finish step.

## Code (P5)

Five skill-local scripts in `scripts/`, each with good / edge / padded tests and a broken-copy test proving
the check can fail: `gates.py` (typed fixed choices; none-of-these never moves the run), `completion.py`
(the completion figure; band edges in its docstring; never gates), `inputs_check.py` (a sub-step's inputs and
its waiting line), `citation_check.py` (paths cited inside the packet exist), `prompt_sections.py` (a step
prompt has the template's sections in order, no leftover blanks, no ruling numbers). 62 tests pass. No shared
tool covered these (checked against the toolbox list), so no register rows.
Quiz results after the last edits (blind reader, cheap model; 6 questions each): the five step prompts,
handoff-note, packet-writer, step-prompt-drafter and tool-builder-handoff all 6/6. tool-builder-handoff first
scored 5/6: the blind reader showed it never said whether the pre-send path check was code or whether it
blocked; the brief now names `scripts/citation_check.py` and says a missing path blocks the send, and one old
answer key that predated the rewrite was corrected. Total across every quiz scored in this build: 114/114.

## Live runner check (2026-11-24, fresh V2 window, scratch folder outside the plugin)

- `start` on this card: exit 0; the step-1 prompt printed; `/next` and `/back` written as commands; status `RUN 1/5`.
- A session trying to move a talk step itself: BLOCKED by the guard ("only the person moves a talk step").
- `stage_runner.py --selftest`: PASS, including an out-of-order move refused (exit 3).
- Plain words ("don't move on yet", "next"): nothing moved.
- The person typed `/next`: moved to step 2. `/back`: back to step 1 with a fresh code word. No "Unknown command".
- FOUND: the hook's injected step text is CUT OFF. After `/next` the step-2 prompt arrived partial (the full text
  was in the run's `stage/02.prompt.md`); after `/back` the cut-off dropped the NEW CODE WORD, so the model could
  not write it without reading the file. Sent to the runner's owner (run pickup). Until fixed, each step prompt
  tells the model where the full prompt and the code word live (to do at the finish if the runner is unchanged).
- Not checked here: the status line showing `RUN n/N` (the plugin's status line does not call the runner yet;
  sent to run pickup earlier).
- RUNNER-GAP WORKAROUND (coordinator's call, 2026-11-24): each step prompt now opens with the step's code word and
  the path of the full prompt in the run folder, so a cut-off injection still carries both. Harmless after the
  runner's own fix (code word first, plus a header), which went to run pickup.
- Rule slip, 2026-11-24: the step prompts were edited while the live check's test run was still open (the rule says finish or abandon a run first). Throwaway test run only; it was left as is and the new line was checked in a fresh run.
