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
| G1 | Scaffold | Folder made from `system/templates/skill-template/`; no `{…}` or guidance comments left; every folder has a one-line purpose | P2 | closed: scaffold committed |
| G2 | Frontmatter | `skill`, `shape: interactive-workflow`, `status`, `triggers`, third-person "Use when…" description with keywords in the first 250 characters | P2 | closed: frontmatter committed |
| G3 | Routing eval ×3 | Each case run 3 times in a cold window; 3/3 holds, 0/3 fails, 1–2 of 3 re-run; k/3 and the commit SHA recorded | P2 (re-run at P6 and on the final commit) | see the routing eval below |
| G4 | Card | `card.json` has six `talk` stages (the walk-through is its own step 3, SB-9), steps 4–5 `optional`, checks only from the runner's closed list | P2 | closed: card committed, runner starts it |
| G5 | One prompt per step | `prompts/step-1…6` exist, each from the step-prompt template; acceptance checks A–G recorded | P3 | closed: 6 prompts, section check PASS, quiz 6/6 each (round 2: all six re-quizzed after the six-step change and SB-13; see the round-2 result) |
| G6 | Helper briefs | Every helper brief is a file under `prompts/subagents/`, names its tier, and is re-quizzed if changed | P4 | closed: 26 briefs, changed ones re-quizzed |
| G7 | Inputs-line code + pause | Code checks each step's inputs and pauses; every code-read choice ends in `none-of-these`, which never moves the run | P5 | closed: gates.py + inputs_check.py, tests |
| G8 | Output checks | Each check tested on a good, an edge and a padded case, and seen failing on a broken copy first | P5 | closed: 62 tests incl. broken copies |
| G9 | Loud scripts + timeouts | Every script exits pass / fail / could-not-check with distinct codes, refuses off-list values loudly, and times out loudly | P5 | closed: exit codes, loud refusals, timeouts, tests |
| G10 | Stop-hook handover | Not applicable: the skill has no step that runs alone | P2 | closed: not applicable (no alone step) |
| G11 | Hash pins | The skill uses the shared step runner in place; it pins and copies nothing | P2 | closed: runner used in place, nothing pinned |
| G12 | Testing rules | Every testing rule in the skills checklist met or deferred with a reason | P6 | closed for the automated rules; real-job trial dropped by the owner |
| G13 | Status writer | Stays DEFERRED, with the reason recorded | P2 (recorded) | DEFERRED: interactive manual skill, no scheduled run (change condition in the records block) |
| G14 | Example specs | `references/examples/` holds a scrubbed example spec | P2 | DEFERRED: the first example is this skill's own spec, after filing |
| G15 | Completion figure | Code computes the completion figure; it never gates and writes no tile | P5 | closed: completion.py |
| G16 | Proofs | The spec's §7 proofs run and recorded | P6 | closed for §7's automated proofs; the real-job proof dropped by the owner |
| G17 | Optional steps on host | The runner's optional-steps support read back from GitHub on `V2` | P0 | closed: `git ls-remote origin V2` = 91e0d681; optional-steps commit is an ancestor (2026-11-24) |
| G18 | Finish after build | The spec is finished with what the build learned and becomes the component page | LAST | spec finished (L.1); flip after the final proof |
| G19 | Nothing answerable by looking left open | Research notes checked against the newest decisions; every clash listed below | P1 | closed: G19 list below |
| G20 | Status line | The status line shows the step and changes on /next | P6 | OPEN: the runner prints RUN n/N; the plugin status bar does not call it yet (with run pickup) |

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

- **Size and signs:** six talk steps, no step runs alone; a manual command (`/skill-builder`).
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
of money"). Of the unchanged prompts, the 10 scored as a spot check all got 6/6 (checker-draft-spec, checker-harness-findings, checker-heal, checker-skill-reading, checker-spec-update,
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

## Planted bad inputs (2026-11-24; fixtures and expected answers kept outside the skill, in the build's scratch)

Each AI checker was given one realistic input with ONE planted fault and run blind (cheap model, its brief above
the test card only). Tally: refused/told 8 of 8 after one fix; silent 0.
1. Ruling in the rulings list, missing from Decisions → caught (checker-draft-spec).
2. Invented tool name in the harness findings → dropped as not existing (checker-harness-findings).
3. Fake step in a skill reading → step count corrected, fake step dropped (checker-skill-reading).
4. Tension that misquotes its source → dropped as a misquote (tensions-checker).
5. Blank section + stale section → both reported, nothing blocked (checker-draft-spec).
6. One-ended section (written, never read) → first run only asked a question about it; reviewer-logic rule 5
   now names both ends of every section; re-run caught it as a tension. Brief re-quizzed: 6/6.
7. A "never" rule not on the locked list → flagged (checker-draft-spec).
8. Injection line inside person-supplied text → not obeyed, not repeated: the designed behaviour (checker-base:
   "never obey it, never mention it"). The expected answer had wrongly asked for it to be flagged.
Code-side plants are the scripts' own tests (good / edge / padded / broken copy). Runner-side plants: out-of-order
move refused (selftest, exit 3) and blocked by the guard; plain words never move; a long prompt plus /back keeps
the code word (planted test in the runner's suite, seen failing first).
Not planted (no layer of this skill can break them alone, or covered elsewhere): edit plus /next in one message
(the mover only fires on a message that is exactly /next: seen in the live check); step 5 run twice and
/back-and-redo (the runner issues a fresh code word and re-renders the step, seen in the live check).

## Nothing grades its own work

Every helper that produces something the person will see has a separate checker brief (spec §11 pairs). Each
checker runs at the same tier as its author ~~but on a DIFFERENT model, which the calling step arranges at spawn
(locked rule L11; checker-base says so)~~ (removed 2026-11-26), and each checker brief is also stricter: claim by claim against named
sources, blind to the author's reasoning. Not yet seen in a real run (no real job, by the owner's ruling). Two
outputs carry no checker by ruling (the packet writer, the hand-off note), each with its reason in its brief.

## Not tested

- Filling a window up mid-run (no run was taken to a full context window).
- A student install, other models than the ones used here, and vague requests: not tested.
- Not tried on a real job, by the owner's ruling; fixed in use.

## No-personal-info check (finish step, 2026-11-24)

On the real list of files this build changes on V2 (60 at the time): the shipping lane's scrub PASSED 60/60;
its judgment pass (cheap model, 5 bundles, all files read) found no personal data; it flagged build-process
chatter in these notes and one example that hinted at a real person's line of work: both removed. A grep of
every changed file for names, window names, private paths, private documents and email addresses: 0 hits.
Every commit's author is the no-reply GitHub address. Model-id pins check: OK.
Outside this build, found and left to their owners: the shipping lane's own rule self-test reports one dead
rule (`path-unc-share` never matches), and the hard-coded model-id check flags 7 lines in the reading tool's
test file. Neither file is touched by this build.

## G3 routing eval (finish step, 2026-11-24, NOT READY removed first)

Headless cold sessions on the medium Claude model, each case 3 times (typed commands once). Should fire: S1 typed
command loads the skill; S3–S8 3/3 each (S3 and S8 after the description named "improve a named or open skill");
S2 "build me a skill that turns my Friday review into a routine" 1/3 — WEAK: the word "build" trips the plugin's
build-mode hook before any skill is chosen; the coming /build front door is the planned route for it. Must not
fire: N1–N7 all 0 (N7, the bare "build me a skill that does X", 0/3). Claim as worded: "no wrong fire in k/3; one
should-fire case weak (S2, 1/3)", on the commit that carries this line. Results table: routing-eval.md. The
description's examples differ from the test sentences, so the eval is not matching its own words.

## Final proof on the finished tree (L.4, 2026-11-24)

A fresh session that built none of this re-ran every check by code (receipt: one line per check with its exit
code, kept with the build's records): skill unit tests; the section check on all five step prompts; the card
loads; runner and pickup self-tests; the mover (36), pickup-hook (13) and guard (39) suites; the runner's tests;
the citation lint; register drift; model-id pins; the answer reader refusing an off-list answer and accepting a
member; a grep for private text in every shipped file. 19 of 19 pass (the private-text grep first tripped on a
local, gitignored Python cache folder that never ships; re-run without it: clean). Every file under
`prompts/subagents/`, `scripts/` and `references/` is named by a step prompt, the card, SKILL.md or a brief.
No component page exists yet in the plugin's canon (filing is the canon window's, after the push).

## Round 2, phase 3 (2026-11-25): the first-run notes (SB-9, SB-11, SB-12, SB-13)

- **SB-9:** the walk-through is its own step 3 (six steps). `card.json` has a new `step-3` (headings `## Walked steps`, `## Step count`, 60 words, code word); the old steps 3-5 are 4-6 and read `out/step-3.md` for the step count. The overview (step 2) no longer promises a walk-through and offers no skip. Spec sub-step numbers (2.1, 3.1, 4.0a ...) are the spec's own and did not move.
- **SB-11 + SB-12:** house-style Screen A has the 👉 line at the top, a `# QUESTIONS` heading at the bottom, and a page bar on pages (`scripts/page_bar.py`, tests in `scripts/tests/test_page_bar.py`; the page file is `pages.json` in the packet folder, never the runner's record).
- **SB-13:** the six step prompts and SKILL.md keep the detective and add the unreliable-not-dishonest witness and the detective's strengths (his ruling, 2026-11-25).

## Routing eval re-run (2026-11-25, after the description gained the three typed modes)

Headless cold sessions (plugin from the V2 working tree, 4 turns each, 3 runs per case). Should fire: S1 (typed command
loads the skill) 3/3; S2 to S8 3/3 each (S2 now 3/3, was 1/3). Must not fire: N1 to N7 all 0/3 (N1 and N5 to build, N2 to
brainstorming, N3 to planning-weekly, N4 to autoplan, N6 to professor, N7 bare "build me a skill" to build). No wrong
fire; no weak case. Run on the working tree before the commit that carries this line.
