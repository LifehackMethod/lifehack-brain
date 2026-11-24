---
component: skill-builder
title: "Skill builder — Specification"
state: component               # flipped 2026-11-24 at the build's final proof (19/19 checks); filed only after the push and the canon window's run
id: skill-builder-spec-2026-11-24
record_type: design-spec
desk: root
created_at: 2026-11-23
status: unproven (receipt missing) — BUILT: the design is ruled by the owner; built, tested (19/19 on the final tree) and pushed to origin/V2 @07254c40, read back 2026-11-24; not yet filed in canon
parent: none                   # no first-principles document: the owner's rulings are the source
also_follows: canon/skill-building-sop.md; system/templates/skill-spec-form/house-style.md
source: origin/V2
scope:
  - .claude/skills/skill-builder/SKILL.md
  - .claude/skills/skill-builder/card.json
  - .claude/skills/skill-builder/routing-eval.md
  - .claude/skills/skill-builder/BUILD-NOTES.md
  - .claude/skills/skill-builder/prompts/README.md
  - .claude/skills/skill-builder/prompts/step-*.md              # the five step prompts
  - .claude/skills/skill-builder/prompts/subagents/*.md         # the helper briefs and their README
  - .claude/skills/skill-builder/references/**
  - .claude/skills/skill-builder/scripts/*.py                   # the five checks
  - .claude/skills/skill-builder/scripts/README.md
  - .claude/skills/skill-builder/scripts/tests/*.py
shared:
  - {paths: [system/parts/stage_runner.py, system/parts/run_pickup.py, system/hooks/run_step_hook.sh, system/hooks/run_pickup_hook.sh, system/hooks/guard_run_commands.sh, system/templates/skill-template/RUNNER.md], home: false, role_here: friction, file_home: run-pickup}
checks:                        # ids are named here; the register carries no row for them yet (added at filing)
  - {id: skill-unit-tests, watches: "the five scripts do what their docstrings say: every test passes (`python3 -m unittest discover -s scripts/tests`, 62)"}
  - {id: runner-live-check, watches: "only the person's typed /next or /back moves a step; a session cannot move a talk step; plain words move nothing (live check, BUILD-NOTES)"}
  - {id: planted-bad-inputs, watches: "each AI checker refuses or reports one planted fault and none passes it silently (8 of 8, BUILD-NOTES)"}
  - {id: prompt-quiz, watches: "a blind reader understands each prompt whose meaning changed (6 of 6 each, BUILD-NOTES)"}
  - {id: routing-eval, watches: "the skill starts on the S cases and never on the N cases (routing-eval.md; pending on the final commit)"}
receipts:
  - <brain>/status/component-skill-builder.json
health: []
---
# The skill builder: draft spec (compiled 2026-11-23, by the packet's COMPILE step)

<!-- roll-up, generated: <LABEL> · checked <date> · valid until <date> · <receipt> · Health · as-built sha · last reading -->

**Cover sheet.** Building: the skill builder, registered as `/skill-builder`, a skill (five steps) that interviews a person, acts the future skill out, and writes that skill's spec. Status: BUILT in the Lifehack plugin's V2 sandbox (`.claude/skills/skill-builder/`), tested by the automated checks recorded in "Covered / not covered" below, and not yet pushed (the push is the owner's act); not tried on a real job, by the owner's ruling (fixed in use). State: `spec` (the flip to `component` is a later step). Designed through the restarted play-act; step 3 (role-play) was skipped for this design run (by the owner's ruling); shake the tree has not run on this spec as a whole. THE LIVING SPEC from 2026-11-24 (an older working copy is no longer edited); brought up to date 2026-11-24 with the owner's rulings of 2026-11-23 and 2026-11-24 and the items recovered from the session, then with the coordinator's rulings of 2026-11-24; the five step prompts and 26 helper brief files are BUILT as files in the skill's `prompts/` and `prompts/subagents/` and quizzed (§11; 120/120 on the prompts whose meaning changed). Home: the Lifehack plugin, branch V2 (§1). Landing spot: the plugin's `canon/components/`, once approved. Checklists pointed to: the skills checklist (§6). This spec goes to /autoplan ON TOP of everything gathered: the whole packet folder, research included, goes with it (supersedes the older "only the spec"; pointer list in §6). Form: the skill spec form (`system/templates/skill-spec-form/`), plus three sections the form lacks (§9, §10, §11) and the compile sections at the end; the finish pass of 2026-11-24 adds the built-skill sections, the producer-spec template's sections T0–T11 and the component page's Part B fields (all after §11).

**Words.** Step = a point where the run stops and waits (for the person, a time or a hand-over). Sub-step = the moves inside a step, numbered N.M. In code a step is a "stage" (`stage_runner.py`); the code names stay. Marks: a line ending `[inferred]` or `[hypothesis]` is not confirmed by the person; no mark means confirmed (L3). Built marks (finish pass, 2026-11-24): **BUILT** = exists at that path today; **CHANGES** = exists and this spec changes it; **NEW** = does not exist yet. A mechanism claim is **[tested]** (with its record, a section of the skill's `BUILD-NOTES.md`) or **[to prove]** (not run, with why).

## 1. WHAT THIS SKILL IS FOR

- **Desired outcome** (confirmed "Yeah"). Designing a skill used to mean building code, running the whole thing, finding one thing off, rebuilding in another window, relaunching: no fast iteration. With the skill builder the AI pretends the skill already exists and acts it out; the person reacts and changes their mind as often as they like; the AI approximates each change, researches it as if it would build it, and writes it into the packet (the spec itself is brought up to date once, at 4.0a). The sub-steps (1A, 1B, 1C) are decided in the background. For a new Lifehack user it is onboarding without an onboarding: they keep using their own skills, the builder points out where the harness does better, and they say how they want the skill to change. The session ends with a real result and a spec /autoplan can build in one shot. It is the skills piece of a larger idea: the system learns how a person wants things by watching them work, never by a list of preference rules.
- **How the person will know it worked**: a skill that is fully conformant, with its own spec, wired into the shared plumbing, that spec filed in canon; over months and years, pleasant to use.
- **The game** (two tracks). Person: it looks like using a skill and reacting; a minimum of questions at the start, at most four of the most leveraged at the end of a round, or a question shown inside the scene. AI: a separate standing goal, every blank filled so the skill comes out conformant, never surfacing a long list; one answer can settle many blanks; the question list is rebuilt every round.
- **Small lookups** mid-game are allowed and saved to research.md [inferred].
- **Research now, not later**: anything that can be answered by LOOKING is researched by background sub-agents during the session, at any step, and by the end of step 4 at the latest (its research pass, 4.1b); only what truly needs the build (code that does not exist yet, test results, the real run) is left for the planner. Every finding made in the background, at any step, is saved to the packet's findings document (`research.md`) as it happens and need not be surfaced to the person. All research uses a recency bias: the newer source wins.
- **The chain** (detail in §4):
  1. **What you want.** The approved opening screen (`opening-screen.md`), then the highest altitude first: purpose, what differs in the person's life, one question "how does this look over days, weeks, months and years?", what it saves, the friction it removes, and as a minor question "what would make you stop trusting it?". Each round names its altitude; the step stays high until "yes, that's it". Two ways in: "I want a skill that does X", or pointing at an existing skill, read quietly and played back as "it looks like four or five steps". Launched inside another skill it first asks "which skill, the one you're in or a new one?", then researches (a short wait is fine), then starts. Quietly, as ALONE sub-steps beside the rounds: the harness check (1.6, 1.7), the research mark (1.8), the size sense (1.9). **Too big** (his definition: multi-step with a large amount of smaller parts, a large database, or a thin layer over a subsystem): it STRONGLY RECOMMENDS going back to /build, saves progress, and does not enforce; /build creates the project, never the skill builder.
  2. **The proposed steps.** Medium altitude: what Lifehack's skills can and cannot do, honestly, including whether this is really a bigger system. Two parts inside the step: first one short overview screen (name and one line per step), then a walk-through two steps per screen, each as conversational prose long enough to give a clear sense of everything that will happen, in sections with the emoji key: 🤖 This session · 🙋 Your part · ➡️🏃 Sub-agents · 🌙 Earlier machinery. 🌙 ALWAYS shows; it means anything existing before the skill runs: work from /build or earlier in the session, and tools, hooks, cron jobs, databases or older skills to migrate; when nothing is known it is a question ("is there anything here I am missing?"), never "nothing here". Two or three leveraged questions under each step. These emoji sections belong only to step 2. Three altitudes: overview = top, walk-through = medium, the spec = ground, never shown. The overview is shown once; returning to the walk-through does not show it again ("We don't need to see the overall scale just when you start showing two at a time"). Each walked step is long enough: step 1's role-played length was right, a clipped one-liner is too short. It is shown as the skill builder running, in its own screen frame, never as a description of a screen ("run it through skill builder, pretend we're doing skill builder"). Quietly, for each agreed step, it drafts that step's start-of-step instruction into the packet, never shown (§11) [inferred as to place]. `/next` only after every step is walked. Counts the steps: one = a command, two or more = a skill. Works out steps, sub-steps and proofs before any acting.
  3. **Role-play it.** OPTIONAL on the card: the person may skip it with `/next` (§4 Skipping). "Ready to try it? It isn't built yet, but I can act it out". It acts the skill out screen by screen in the person's chair, until the spec is filled. It DOES real work by hand with what the system can do today and never claims the machinery exists; it notes what it did by hand for the plan; anything it cannot do it says plainly and asks whether to use made-up data. Harness guards still apply (supersedes "sandbox only"). Each acted screen is the skill's own screen, in its own frame, as the person would see it [inferred as to step 3; his words were said of step 2's play-act]. Mid-scene notes are just said, no command; the step ends only on `/next`. When something breaks it keeps going while a background helper finds the fix and records it in the packet; it never edits the harness or the skill (L2). It warns where something would not fit the harness and teaches the harness. **Watching mode**: when improving an existing skill it may become a shell around that skill, which really runs while the builder watches, takes notes and asks questions; not prescribed, not binary, the AI judges; the hard line is never to fabricate data or machinery and present it as real (L22).
  4. **Shake the tree.** Explained to the person as a five-angle check. Opens with a PREP REPORT (4.0) of what is undecided; the person decides now or lets the reviewers guess first. The order (option A, approved): the four reviewers, one lens each, at the same time (4.1a) → a RESEARCH PASS, as many small parallel sub-agents as needed, one per open item answerable by looking, including facts the four said were missing (4.1b) → the fifth, the rulebook proposer, LAST, with the facts: it checks the spec against the skills checklist and SOP and works out PROPOSALS (it fills no blank) (4.1c) → the checker → the person, six at a time. The recipe is a working file of the build (§6); it now carries the research pass and the comprehension quiz (ROUTED NOTES 17, landed). Findings are verified, de-duplicated, ordered most to least load-bearing, each marked optional or not, up to six at a time. Then a VALIDATION MOMENT (4.5, 4.6): the spec is brought up to date with the person's answers and re-validated, 100% as a hope never a demand. OPTIONAL on the card: how thorough to be is the person's choice, and a skip is their own `/next` (§4 Skipping). A one-step command skips this step.
  5. **The hand-off.** LEADER MODE: the person is no longer doing the work, so there is no question section; the step tells them plainly what was made, what happens next and what they do, "gently directionally accurate", never an invented question; the only questions are real open ones (the parts round's, and "who is this for?" when unknown). First a quick parts round with the tool builder, only when a part is owed (5.0), then it compiles one clean draft spec and reads it back as a readout, at three altitudes: "we have not built this skill yet; make sure the readout is correct"; the "go ahead and build this skill?" moment is the person's `/next` after "if the readout is right, type /next and I'll hand it over" [inferred]. WHO IS IT FOR?: asked once, into the destination: for me → `~/.claude/skills/<name>/`; for everyone → inside the Lifehack plugin repo, on a branch, offered back as a PR (`canon/manual.md:963`); repo, branch and push routing follow the GitHub SOP (§0c), never this skill. TWO hand-offs: a technical one for the next AI and a plain on-screen one for the person. Everything gathered goes to /autoplan (most likely) or back to the main project window: the design on top, treated as settled, plus the whole packet, research included, so nothing is researched twice (supersedes the older "only the spec"); the packet is also filed as the record. THE ENDING, corrected: there is no extra stage after the build. /autoplan makes the plan, and the plan's FINAL step sharpens and finalizes this draft spec with everything the build discovered (code, JSON, checkers, telemetry), then files the skill and its spec in the right place: for most people `~/.claude/skills/<name>/` (`canon/build-conformance-sop.md:49`). A coordinator window and a build window after /autoplan are best practice, never required.
  Moving between steps is only ever the person typing `/next` or `/back`, never the AI; `/back` moves exactly one step. Every turn of every step ends with the standing line "keep discussing this round, or ready to move on?", `/next` and `/back` beside it (L24); in step 5 it takes the leader form "Type `/next` to hand it over, or `/back` if you want to change something" [inferred as to wording].
  **Every step fully reorients**: each step opens, at its START only, with its step instruction (§11), whose first blocks are the audience profile (L23) and the detective role (L20); the person is treated "as if ... a completely new user" every time a step starts, told where they are in the whole run, what the step is for and what ROLE they play now. The two shared prompts are NOT injected every turn ("overkill ... in the context window").
- **What it is NOT.** Not /build (the front door: keeps the tracking list, decides size, hands over, never fills a form). Not /autoplan. Not a builder of anything: it writes the spec only. Not an onboarding course. Not a questionnaire that walks every blank. Choosing its jobs is not its business; the coordinator does that (round one). Not the tool builder or component builder: it calls them, or /build or project-manager, in any direction, by prompt hand-off with the packet; if the builder does not exist yet the piece is deferred work.
- **Where this skill lives** (coordinator, 2026-11-24): it is for everyone, so it is Lifehack plugin code: `.claude/skills/skill-builder/`, built in the V2 sandbox (branch V2); the push is the owner's own act, nothing goes to main without his word, and no personal information goes into any shipped file. (Where the skills it DESIGNS are filed is the person's "who is it for?" answer, L27.)
- **A day with it:** types /skill-builder, says what they want or points at a skill, answers a few big questions, then mostly reacts to a role-played version; sees a status bar at the foot of every reply; never sees the form [inferred].
- **A week, a month, a year:** each skill they touch gets cleaner and more conformant; "the more you use ... life hack harness, the sharper it gets" [inferred].
- **What it saves:** "a huge amount of time and stress, which would equal money". Ends the broken-run loop and removes the onboarding wall.
- **What would make the person stop trusting it** [inferred; he called it "not really relevant quite yet"]: agreeing too fast and building; asking what it could have looked up; asking twice; making something up; handing the planner a spec with gaps. Sub-step 1.4 asks the person as a minor question; their answer replaces this list and feeds §10's "it worked" blank.
- **What it must never do:** §2.

## 2. THE LOCKED LIST

`L<n> — <what> · <HARD | MOSTLY LOCKED> · <who may change it> · <ruling>`. MOSTLY LOCKED levels other than L15 are the builder's choice [inferred].

- L1 — Never rushes to a solution: the solution comes out of filling the form with questions · HARD · the person only
- L2 — Never builds anything: it writes the spec; no build and no automated run of the skill inside it. Acting the skill out by hand with what the system can do today is allowed, as is watching an existing skill really run · HARD · the person only
- L3 — Only the person's "yes, that's it" settles a line; unconfirmed lines end `[inferred]` or `[hypothesis]` · HARD · the person only
- L4 — Role-playing is offered in every round and is the main way of working · HARD · the person only
- L5 — Never makes anything up: an unknown stays blank and is listed as open with a recommendation · HARD · the person only
- L6 — The packet travels with the work between builders. At the hand-off to /autoplan everything gathered is sent: the updated spec on top, treated as settled, plus the whole packet, research included, so nothing is researched twice; the packet is also filed as the record (supersedes the older "only the spec") · MOSTLY LOCKED · a dated ruling. STALE MARK (coordinator, 2026-11-24): the older L6 wording, "the packet is archived, never sent", which two of the build's reviewers found contradicting the hand-offs, is stale; the whole packet goes, settled
- L7 — Never states a tool, path, command or ID it has not seen; "can't tell" is the answer · HARD · the person only
- L8 — Nothing outside the Lifehack plugin is truth, the person's own setup included · HARD · the person only
- L9 — Never blocks the person over non-conformance: warns plainly, the person decides; no perfect code gate · HARD · the person only
- L10 — No cues from v1 builds, with one exception: the old skill builder's flow (outcome, steps, sub-steps acted out, shake the tree), made conversational · HARD · the person only
- L11 — Nothing a helper produced reaches the person before a separate checker has checked it · MOSTLY LOCKED · a dated ruling
- L12 — Never asks the person what it could find out itself (plugin, packet, existing skill) · MOSTLY LOCKED · a dated ruling
- L13 — Before the hand-off every dated ruling is in the draft spec's Decisions and every routed note has landed · MOSTLY LOCKED · a dated ruling
- L14 — Harness first: looks for what Lifehack already solves before designing · HARD · the person only
- L15 — Parachute in: questions go high, medium, low; never to details before the outcome is framed · MOSTLY LOCKED (his "principle, not a rule") · a dated ruling
- L16 — At most four questions a round, most leveraged first; they are the questions in the status bar. Exceptions: step 2's walk-through (two or three under each walked step, so up to six on a screen) and step 4 (up to six findings at a time). Step 5 is leader mode: no question section, and no question that is not really open · MOSTLY LOCKED · a dated ruling
- L17 — A status bar ends every reply: completion, the round's questions, and a sliding scale as last words: "not ready to move on" (load-bearing items undecided, most of the form unfilled) → "wouldn't recommend moving on yet" (mostly filled, some gaps) → about 90% and up, "probably okay to move on" [middle band's edges inferred; the 90% is his]. It INFORMS and never insists; nothing is gated on it. The same state is what the system reads if the person tries to close or save. The bar's first line is the locked text `🛠 Skill builder · Step N of 5: <name>`; the status line shows the runner's position, `RUN n/N stage (mode)` (§8-2, §8-4 closed). The figure is computed by code, never the AI, and must be accurate (method in "FOR THE PLANNER AND THE BUILD"). In step 5 the bar carries no questions · MOSTLY LOCKED · a dated ruling
- L18 — One form: the spec is the only list; its blanks are what make the skill conformant; how thorough to be is the person's call · HARD · the person only
- L19 — Count the steps: one step makes a command, two or more a skill; the count opens or closes the form's step-runner sections; every skill gets the one form; a one-step switch command is only the trigger, what it turns on is a separate part; a one-step command skips step 4 · HARD · the person only
- L20 — The standing role: an earnest detective interviewing an honest witness (lead, don't follow; go slow; frame big first; play it back; never one-shot; come with a guess; measure against the plugin), delivered by the step instruction at the START of each step (its opening detective block, §11), never injected every turn; the person never sees the role text · HARD · the person only · the owner's ruling
- L21 — Only the person typing `/next` or `/back` moves a step; `/back` moves exactly one; no plain-speech "next"; at every gate (1.4, 2.1, 3.1, 4.3, 4.6, 5.0, 5.3) an edit sent in the same message is made first, then the person types `/next`; the AI may suggest another round but the person decides · HARD · the person only
- L22 — Honest acting: real work by hand, never claims the automation exists, never invents results; made-up data only on the person's yes; guards still apply; in watching mode the other skill really runs; the one hard line is never to fabricate data or machinery and present it as real · HARD · the person only
- L23 — The audience: every step speaks to someone who has never built a skill, never used Lifehack, has not seen this session, may be anxious, and wants no busy work; every step reassures and orients in under two sentences (what is happening now, where it sits in the run). The audience profile is delivered by the step instruction at the START of each step (its opening block, §11), never every turn, and each step FULLY REORIENTS the person as if brand new: where they are in the whole run, what this step is for, and what ROLE they play now · HARD · the person only
- L24 — Every turn of every step ends with the standing line, `/next` and `/back` beside it; shared, built into every skill, beside the status bar; in step 5 it takes the leader form (tell them what to type, no question) · HARD · the person only [inferred as to HARD and the step 5 wording]
- L25 — The screen never stalls on a helper: when the person types `/next` while a sub-agent or checker is still working, the screen moves on at once and says plainly what is still finishing, that nothing is lost, and where the result will show, in under two sentences ("always freaked out about not knowing what's going on") · HARD · the person only [inferred as to HARD]
- L26 — Research what can be looked up: anything answerable by looking is researched by background sub-agents during the session (by the end of step 4's research pass at the latest), with the newer source winning; only what truly needs the build is left for the planner; background findings are saved to the packet as they happen · MOSTLY LOCKED · a dated ruling [inferred as to the locked level]
- L27 — Who is it for decides where the skill is filed (for me: `~/.claude/skills/<name>/`; for everyone: the plugin repo on a branch, offered back as a PR); repo, branch and push routing follow the GitHub SOP (§0c), never this skill · HARD · the person only [inferred as to HARD]

### Rails: what holds each HARD rule (read from the built files, 2026-11-24)

**Why this block exists** (producer-spec template §3): a skill built in isolation silently re-derives, and subtly weakens, rules the surrounding system already settled, and the column that matters most is what enforces each rail. The rails are the 19 HARD rules above (counted by code). **Source** is the ruling above and the built file that states the rule. **Held by**, read from the built files in `.claude/skills/skill-builder/` and from the shared runner files, is **CODE** (a script or the runner), **HOOK**, **PROMPT** (a prompt file states it; nothing checks any reply against it) or **PROSE-ONLY** (no built file holds it). Light enforcement is the owner's ruling (L9): there is no perfect code gate, so a prompt-only HARD rule is flagged here, not hidden. What the card's checks prove is that headings, a word count and the code word are present in a step's output file, never that the content is right (the runner's own "declared uncheckable" bound, `system/parts/stage_runner.py` header).

| Rail | Source | Held by |
|---|---|---|
| L1 Never rushes to a solution | the owner's ruling; `prompts/step-1-what-you-want.md` (its "Never" list) | **PROMPT:** `prompts/step-1-what-you-want.md`. Nothing checks a reply. |
| L2 Never builds anything | the owner's ruling; `SKILL.md` (Musts, "What this does NOT do") | **PROMPT:** `SKILL.md`, `prompts/step-3-role-play-it.md`, `prompts/step-5-the-hand-off.md`, `prompts/subagents/healer.md`, `prompts/subagents/checker-heal.md`. No code or hook stops a build. |
| L3 Only the person's "yes, that's it" settles a line | the owner's ruling; the step prompts | **PROMPT:** `prompts/step-1-what-you-want.md`, `step-2-the-proposed-steps.md`, `step-4-shake-the-tree.md`, `prompts/subagents/packet-writer.md`, `spec-updater.md`, `checker-spec-update.md`. CODE only counts: `scripts/completion.py` reads a line marked `[inferred]` or `[hypothesis]` as not done; it cannot tell whether an unmarked line was confirmed. |
| L4 Role-playing is offered every round | the owner's ruling | **PROMPT:** `references/opening-screen.md` (its closing offer), `prompts/step-1-what-you-want.md` (each round's closing offer), `prompts/step-2-the-proposed-steps.md` ("every round offers the acting-out in one line"). No code. |
| L5 Never makes anything up | the owner's ruling; the step prompts | **PROMPT:** all five `prompts/step-N-*.md`; the checker briefs `checker-harness-findings.md`, `checker-skill-reading.md` and `tensions-checker.md` drop invented items (seen refusing on planted inputs 2, 3 and 4, BUILD-NOTES "Planted bad inputs"). No code. |
| L7 Never states a tool, path, command or ID it has not seen | the owner's ruling | **CODE (paths only):** `scripts/citation_check.py` fails a backticked path in a packet file that does not exist in the packet (plugin paths and paths starting `/`, `~` or `<` are skipped and counted "not checked"). **PROMPT (the rest):** the five step prompts, `prompts/subagents/harness-search.md`, `checker-harness-findings.md`. |
| L8 Nothing outside the plugin is truth | the owner's ruling | **PROMPT:** `SKILL.md` (Musts), `prompts/subagents/harness-search.md`, `skill-reader.md`, `checker-harness-findings.md`. No code. |
| L9 Never blocks the person over non-conformance | the owner's ruling | **CODE:** `scripts/completion.py` never gates (its FAIL exit is unused: it prints a figure only); `scripts/gates.py` (`none-of-these` never moves the run). **PROMPT:** the five step prompts, `prompts/subagents/checker-base.md`, `checker-draft-spec.md` (they report, never block). |
| L10 No cues from v1 builds | the owner's ruling | **PROSE-ONLY:** no built file holds it; it governed how the skill was made (scaffolded from the skill template, the archived skill not copied: BUILD-NOTES "Records block (P2)"). |
| L14 Harness first | the owner's ruling | **CODE (a heading only):** `card.json` step 1 requires `## Harness check`, checked by `system/parts/stage_runner.py`. **PROMPT:** `prompts/step-1-what-you-want.md` (the 1.6 and 1.7 helper lines), `prompts/subagents/harness-search.md`, `checker-harness-findings.md`. |
| L18 One form; thoroughness is the person's call | the owner's ruling | **PROMPT:** `prompts/step-4-shake-the-tree.md` (its "Never" list). `scripts/completion.py` informs and never gates. |
| L19 Count the steps; a one-step command skips step 4 | the owner's rulings | **CODE:** `card.json` step 2 requires `## Step count`; steps 3 and 4 carry `optional`, so a skip is the person's own `/next` (`system/parts/stage_runner.py`, only on the person's turn). **PROMPT:** `prompts/step-2-the-proposed-steps.md`, `step-4-shake-the-tree.md`. |
| L20 The standing role, delivered at the start of each step, never every turn | the owner's ruling | **HOOK:** `system/hooks/run_step_hook.sh` hands the step prompt over when the person types `/next` or `/back` (`system/hooks/run_pickup_hook.sh` does the same on a resume); nothing re-injects it each turn. **CODE:** `scripts/prompt_sections.py` (the step-prompt template's sections, which carry the role, are present and in order). **PROMPT:** section 2 of each `prompts/step-N-*.md`. That the person never sees the role text is PROMPT-only. |
| L21 Only the person's `/next` or `/back` moves a step | the owner's ruling | **HOOK:** `system/hooks/run_step_hook.sh` (moves a step only on a prompt that is exactly `/next` or `/back`, never from a peer message or a notification; its injection starts with the full-prompt path and the code word) and `system/hooks/guard_run_commands.sh` (a session cannot run the runner's person-turn, nor advance or back on a talk step). **CODE:** `system/parts/stage_runner.py` (order; no person turn: exit 3; hash-chained record). **PROMPT:** the "Edit first" section of each step prompt (an edit sent with the move is made first). Seen live: BUILD-NOTES "Live runner check". |
| L22 Honest acting | the owner's ruling | **PROMPT:** `prompts/step-3-role-play-it.md`, `prompts/step-5-the-hand-off.md`. Nothing can see whether data was made up (§11: human_in_the_loop). |
| L23 The audience, reoriented at the start of each step | the owner's ruling | **HOOK:** `system/hooks/run_step_hook.sh` (the start of a step only). **CODE:** `scripts/prompt_sections.py` (section 1, "Who you're talking to", is present). **PROMPT:** section 1 of each `prompts/step-N-*.md`; whether a screen is clear to a beginner is judged by `prompts/subagents/reviewer-screens.md` only. |
| L24 The standing line ends every turn | the owner's ruling | **PROMPT:** the closing-line instruction in each `prompts/step-N-*.md` (step 1 offers `/next` only). No code or hook checks that a reply carries it. |
| L25 The screen never stalls on a helper | the owner's ruling | **CODE:** the runner checks only the step's own output file, so it has no wait on a helper (`system/parts/stage_runner.py`). **PROMPT:** `prompts/step-4-shake-the-tree.md` and `step-5-the-hand-off.md` (the house style's "still finishing" line). |
| L27 Who is it for decides filing | the owner's ruling | **CODE:** `scripts/gates.py --set-id audience` (`for-me`, `for-everyone`, `none-of-these`). **PROMPT:** `prompts/step-5-the-hand-off.md`, `prompts/subagents/handoff-note.md`. Repo, branch and push are the GitHub SOP's, never held here. |

**Tally of the 19:** a code or hook layer exists, in full or in part, for 9 (L7, L9, L14, L19, L20, L21, L23, L25, L27); 9 are held by a prompt file alone (L1, L2, L3, L4, L5, L8, L18, L22, L24); 1 is PROSE-ONLY (L10). Two MOSTLY LOCKED rules are read here too, because the built files differ from the rule's wording. **L11** is PROMPT only: the checker briefs say "a different model" (`checker-base.md`: "the caller arranges that"), but every brief runs at tier medium and nothing in code or in the spawn arranges a different model; the pairing is held by a stricter brief, claim by claim against named sources (BUILD-NOTES "Nothing grades its own work"). **L17** is CODE: `scripts/completion.py` computes the figure, the bar and the phrase (band edges 50 and 90; the 50 is the script's own judgment, the 90 is the owner's).

## 3. HOW IT GETS TRIGGERED · THE TWO DOORS

- **What starts it.** (a) Anyone types `/skill-builder` directly. (b) /build hands a skill over at Stage 5 (small path) or Stage 8 (bigger skill) of its decision tree; that only means many blanks are already filled. Both start 1.1. No fresh-window rule for a direct `/skill-builder` (§8-5, closed); round one's "fresh window reporting to the build-skill window" was for this design run.
- **No separate setup stage:** with nothing handed over, /build's questions are empty blanks asked in the normal rounds [inferred]. **No schedule:** on demand only. **A run that outlasts a window** picks up through the harness's shared run pickup.
- **Which door.** Door One, a new skill from nothing. **Kept** from the old skill builder: its flow and its presentation rules (§6). **Gone:** everything else about the old skill, which is legacy.

## 4. THE STEPS (the ladder)

Five steps: WHAT YOU WANT, THE PROPOSED STEPS, ROLE-PLAY IT, SHAKE THE TREE, THE HAND-OFF. Moving between steps goes only through the shared step runner's `/next` and `/back` as run pickup delivers them; the skill has no move-on logic of its own. The decision tree for this ladder is a working file of the build (pointer, one home, §6). The harness's routing picks the models.

Rules for every sub-step (stated once, not repeated below):
- **Every TALK sub-step carries three lines:** it saves the person's words verbatim to the packet FIRST, labelled SAID, never RULED (L3); EDIT FIRST: an edit sent with `/next` is made first, then the person types `/next`; an empty or failed result is said on screen and stops, never a quiet success [inferred]. The step's own output file is kept current every turn, because the runner checks it the moment the person types `/next` (approved 2026-11-24). `/next` is typed on its own: the AI makes the edit first, then the person types `/next` as a message by itself (approved 2026-11-24). Every TALK reply ends with the status bar (L17) and the standing line (L24); the sub-step's ⑂ line is that same question, and its CODE choice is made only from the person's `/next`, `/back` or answer. A three-way ⑂ means: "more" = keep discussing, "redesign" = the person types `/back`, "move on" = the person types `/next` [inferred].
- **Choices the code reads:** every `→ CODE (...)` has a fixed set ending in `none-of-these`; `none-of-these` never moves the run: the sub-step stays put, asks again in its own words `→ LLM (open)`, and offers the fixed choices again [inferred].
- **Skipping** (the one skip-line rule, stated here once; the prompts of steps 3 and 4 quote it). Steps 3 and 4 carry `optional` on the card (§8-1, closed: the shared runner has the field, commit e9632fbb on origin/V2). A skip is the person's own `/next` on an optional step, recorded "skipped by the person" with that turn (step 4's thoroughness is the person's choice). Steps 3 and 4 write their output file only after the person's first real work in the step, so a `/next` typed before that is a skip, never a fake pass (approved 2026-11-24). The runner never skips on its own and nothing fakes a "done". Each of steps 3 and 4 says once, on its first screen, the form's skip line: "You can skip this: type `/next`." [inferred as to placement]. The older fallback (a one-line skip screen for a runner without the field) is NOT built. An arrow below that jumps a step (2.1 to 4.0, 2.1 to 5.0, 3.1 to 5.0) is the person typing `/next` once per step jumped, and the screen says so; skipping several steps takes one typed `/next` per step, each recorded as its own skip (approved 2026-11-24).
- **Screens**: every screen is the house style (`system/templates/skill-spec-form/house-style.md` in the plugin), named by path, never copied: Screen A on steps 1–4, Screen B (leader mode) on step 5, Block C for step 2's walk-through. When the skill being designed is a one-step command, its screens are the house style's "Screen A, command form": no step line, no step in the bar, no `/next` · `/back` line; it ends with its result or its one question.
- **Never stalled on a helper** (L25): see L25. **Waiting**: while sub-agents run the AI keeps working inline where it can and stops with "wait" only when truly gated; no fixed time limit.
- **Question rules:** never ask the person to do the AI's synthesis; ask questions that help them think, never a choice among options they do not understand; never a question without a best guess [inferred]. Every question the skill builder asks, at every step, carries three things in the house style's question block: its RECOMMENDATION, how CONFIDENT it is (high, medium, low) and how LOAD-BEARING the decision is (high, medium, low). **Audience:** L23. In step 4 the limit of six at a time also covers the prep report (4.0) and the list of slots still missing (4.6) (approved 2026-11-24).
- **Helper rules,** carried by every launch message: read every file in full or say what was skipped; read only the files named; each prompt file describes its own step only; every spawn names a model tier (never a model name); a checker is never the model that did the work; the classifying sub-steps (1.8, 1.9) are not on the cheapest tier (skills SOP, Don't Retry) [inferred]; in every research job the newer source wins; every finding a helper makes is saved to the packet's findings document as it happens, whether or not it is shown.
- **A hand-over that proves incomplete:** when the AI is about to ask the person something a hand-over should already have answered, it treats that as a signal that not everything was handed over, not as one missing answer; it asks up the chain (the window or builder that handed over, and on up), first stating what it knows and what it does not know, so the gap can be filled ("first you need to tell them what you have and what you don't have ... I would send it all the way up the chain"); it asks the person only what the chain cannot answer (L12) [inferred as to place].
- **Step instructions** (§11): each step opens with its own instruction file, handed over by the code at the START of that step only; it describes that step only and opens with the audience profile and the detective role.
- **Hand-off messages** (1.4, 2.1, 3.4, 5.0): the message lists every file the packet cites, built from the packet's own citations and checked mechanically (a search of the packet for paths) before it is sent [inferred].
- **Going back** (L21): `/back` moves one step; from step 5 to Role-play it is two `/back`s (one for a command, which has no step 4); a 🔁 line never moves a step itself. After a `/back`, every spec section filled from the step returned to onward is marked **stale** until re-confirmed, and a stale section never counts as filled; the marks live in the packet's list "stale" (scratchpad section, §5), written by the TALK sub-step the person lands on, never by the runner [inferred].
- **Waiting and stopped** follow the skill spec form's waiting-and-stopped rule: an ALONE sub-step writes "status" when it waits or stops, and the next TALK sub-step shows it.

```
├ 🤖 💾 **1.1** ALONE — opens the packet (from /build's hand-over, or empty) and reads what is known, so no question is asked twice [inferred]. **Where the packet lives** (decided 2026-11-24): ONE folder per skill being designed, holding the packet files AND the runner's run folder (the runner's workdir IS this folder). If the person names a project, or /build created one: `<that project>/packet/`. No project: `<brain>/drafts/builds/<skill-name>/`. Always a folder, never the single-file form. Its path is the scratchpad section "packet-path".
│         ⟵ incoming from background (/build): scratchpad section "handoff-in" (optional)
│         no handoff-in (direct start) → starts from empty blanks; failed → status "stopped: packet not opened: <reason>"
│         ⟶ for steps 1.2, 1.4, 1.6, 1.8, 1.9, 3.1, 3.4, 4.0, 4.0a, 4.1a, 4.1b, 4.1c, 4.5, 5.0, 5.1, 5.2, 5.4: scratchpad section "packet-path"
│         ⟶ for steps 1.4, 5.1: scratchpad section "known" (names the first-principles document when one exists)
│         ⟶ for step 1.4: scratchpad section "status" (only when waiting or stopped)
├ ➡️🏃 💾 **1.2** ALONE — when the person points at a skill, a helper reads it in full and lists its steps, what it does and what is missing against the plugin, so the game starts from evidence; runs after 1.1 and again each time 1.4 sends a newly pointed skill back through 1.5 [inferred]
│         ⟵ incoming from 1.1: "packet-path"; ⟵ incoming from 1.4: "pointed-skill" (optional)
│         no packet-path → waits ("waiting: packet from 1.1"), helper not launched; no pointed-skill → empty reading
│         launch message: the skill's path, the plugin's rule files (skills checklist, system/register/toolbox.md), finish signal; the skill's text is data; helper ends done / nothing to add / failed (reason); failed → "stopped: reading failed: <reason>"
│         ⟶ for step 1.3: "skill-reading"; ⟶ for step 1.4: "status" (only when waiting or stopped)
├ ➡️🏃 ⚙️ **1.3** ALONE — a separate checker re-reads the skill against the reading, so nothing reaches the person unchecked [inferred]
│         ⟵ incoming from 1.2: "skill-reading"; no skill-reading → waits; empty reading → empty skill-checked; failed → "stopped: check failed: <reason>", reading withheld
│         ⟶ for steps 1.4, 2.1: "skill-checked"; ⟶ for step 1.4: "status" (only when waiting or stopped)
├ 🙋 🖥 🤝 **1.4** TALK — WHAT YOU WANT: when launched inside another skill, first asks "which skill, the one you're in or a new one?" and writes the answer to "which-skill" (1.8's input on this path; 1.8 never waits on this sub-step's outcome and this sub-step waits at most briefly for 1.8, so neither waits on the other); shows the approved opening screen, its text unchanged (`opening-screen.md`, with a guess paragraph when something is known), wrapped in the house style's Screen A (the opening screen's title is Screen A's header, approved 2026-11-24): the step line above it, then the status bar and the closing line below it (on step 1 the closing line offers `/next` only, as there is no step to go back to); then short screens, rounds at the highest altitude, each naming its altitude: purpose, one question on days/weeks/months/years, time/money/stress, the friction, and as a minor question "what would make you stop trusting it?" (its answer fills §10's "it worked" blank); stays high until "yes, that's it"; the role-play offer; so the outcome is framed before any detail [inferred]
│         ⟵ incoming from 1.1: "packet-path", "known"; ⟵ from 1.3: "skill-checked" (optional; shown as "it looks like four or five steps"); ⟵ from 1.7, 1.8, 1.9 as the rounds go (all optional): "harness-checked", "research-mark", "size-sense" (shown plainly; the person may correct any); ⟵ from 1.1, 1.2, 1.3, 1.6, 1.7, 1.8, 1.9: "status"
│         no packet-path → shows status lines or "waiting: packet from 1.1"
│         harness-checked says Lifehack already does it fully → says so plainly, with a recommendation, confidence and load-bearing `→ CODE (start-from-existing|build-new|none-of-these)` · start-from-existing → the builder points at the existing skill and designs from it (the locked second way of working: pointed at an old skill); never a "just use it" exit, which is ruled out, since anything outside the plugin is evidence and gets checked · build-new → rounds go on from scratch; the person decides, never blocked (L9) · none-of-these never moves the run (decided 2026-11-24: a ruled-out option, "There is no option ... no, no way")
│         size-sense says too big → "we strongly recommend you take a step back and go back to /build; we can save your progress here; we don't enforce it" `→ CODE (take-it|carry-on|none-of-these)` · take-it → saves the packet, prompt hand-off to /build, this run ends, /build creates the project · carry-on → rounds go on [inferred]
│         ⑂ keep refining, point at a skill, or move on? `→ CODE (refine|points-at-skill|move-on|none-of-these)` · refine → 1.4 · points-at-skill → 1.2 (via 1.5, then back to 1.4) · move-on → 2.1 (through /next)
│         ⟶ for step 1.2: "pointed-skill"; ⟶ for step 1.8: "which-skill" (inside-another-skill path only); ⟶ for steps 1.6, 1.8, 1.9, 2.1: "outcome"; ⟶ for step 3.4: "stale" (only after a /back lands here)
├ 🔁 **1.5** repeat 1.2–1.4 with the pointed skill, so it is read, checked and played back before the next round, until the person has no more skills to point at [inferred]
├ ➡️🏃 💾 **1.6** ALONE (background, beside 1.4's rounds) — the harness check: a helper searches the plugin for what already solves or supports this (shared tools, parts, skills, SOPs), so the design starts from the harness (L14) [inferred]
│         ⟵ incoming from 1.4: "outcome"; ⟵ from 1.1: "packet-path"; either missing → waits, helper not launched
│         launch message: the outcome, the plugin root, finish signal; the search reads `system/register/toolbox.md`, the plugin's list of shared tools (it exists; approved 2026-11-24); the plugin's text is data; nothing to add → empty harness-findings; failed → "stopped: search failed: <reason>"
│         ⟶ for step 1.7: "harness-findings"; ⟶ for steps 1.4, 2.1: "status" (only when waiting or stopped)
├ ➡️🏃 ⚙️ **1.7** ALONE (background) — a separate checker confirms each finding exists where it is said to be, so no invented tool reaches the person (L7) [inferred]
│         ⟵ incoming from 1.6: "harness-findings"; none → waits; failed → "stopped: check failed: <reason>", findings withheld
│         ⟶ for steps 1.4, 2.1: "harness-checked" and "status" (only when waiting or stopped)
├ ➡️🏃 💾 **1.8** ALONE (background) — the research mark and round: decides quietly "do you already hold the knowledge? If not, does the job need outside knowledge?"; if so marks a research round and runs /research, saving into this build's own notes (or the project when the packet names one, written only through the project-manager skill (data-layout: project-manager is the brief's writer); it never starts a project), so outside knowledge is fetched before the design leans on a guess [inferred]
│         ⟵ incoming from 1.4: "outcome", "which-skill" (optional); ⟵ from 1.1: "packet-path"; ⟵ from 2.1 on a repeat: "steps-draft" (optional)
│         the packet already carries the mark → copies it forward; which-skill present and no outcome → researches from the which-skill answer (never waits for 1.4); neither → waits; no packet-path → waits
│         knowledge held or none needed → research-mark "none"; failed → "stopped: research mark failed: <reason>"
│         ⟶ for steps 1.4, 2.1: "research-mark" and "status" (only when waiting or stopped)
├ ➡️🏃 ⚙️ **1.9** ALONE (background) — the size sense: reads the outcome as rounds fill it and decides quietly whether it points to a multi-step skill with a large amount of smaller parts, a large database, or a thin layer over a subsystem; if so writes size-sense "too big" so 1.4 can strongly recommend /build, never enforced [inferred]
│         ⟵ incoming from 1.4: "outcome"; ⟵ from 1.1: "packet-path"; either missing → waits; not too big → size-sense "none", nothing shown; failed → "stopped: size sense failed: <reason>"
│         ⟶ for step 1.4: "size-sense"; ⟶ for steps 1.4, 2.1: "status" (only when waiting or stopped)
├ 🙋 🖥 🤝 **2.1** TALK — THE PROPOSED STEPS, medium altitude: what Lifehack's skills can and cannot do here, honestly; whether this is really a bigger system; proposes the skill's steps, each with its outcome, a first draft of sub-steps and proofs, and the step count, all before any role-play; in two parts: the first screen is the one-line-per-step overview, then the walk-through two steps per screen as prose with the emoji sections in order (§1 item 2), in the house style's Block C exactly (overview once; the key line on the first walk-through screen only; the four labelled sections per step; the questions in the bar), two or three leveraged questions under each step (up to six on a screen is L16's exception) [placement inferred]; the overview shown once, never again on returning to the walk-through; each walked step long enough, shown in the skill builder's own screen frame; quietly drafts each agreed step's start-of-step instruction into the packet (§11) [inferred as to place]; the person discusses and corrects as they go; `/next` only after every step is walked and agreed; the role-play offer; so the shape is agreed before anything is acted out [inferred]
│         ⟵ incoming from 1.4: "outcome"; ⟵ from 1.3, 1.7: "skill-checked" (optional), "harness-checked"; ⟵ from 1.8: "research-mark" (optional); ⟵ from 1.6, 1.7, 1.8, 1.9: "status"
│         no harness-checked → shows status lines or "waiting: findings checked by 1.7"
│         too big for a skill → says so plainly and, as at 1.4, strongly recommends handing off, never enforced `→ CODE (take-it|carry-on|none-of-these)` · take-it → calls /build or the component builder by prompt hand-off, this run ends, the packet travels with it [fork inferred]
│         the step count is decided here and carried in "steps-draft"; a command skips step 4
│         ⑂ keep refining, move on, or skip the role-play? `→ CODE (refine|move-on|skip-role-play|none-of-these)` · refine → 1.8 (looks again at the changed steps, passes through when nothing changed, then 2.1) · move-on → 3.1 (through /next) · skip-role-play → 4.0 (the screen says "you can also skip the acting-out and go straight to the check"; a skip per the skipping rule) · a one-step command skips to 5.0 instead [inferred]
│         the quiet drafting: helper `prompts/subagents/step-prompt-drafter.md`, one per agreed step, writes "step-prompts"; a separate checker (`checker-base.md` + `checker-step-prompts.md`, a different model) checks them into "step-prompts-checked"; only checked drafts are what step 3 acts by and what 4.0a writes into §11
│         ⟶ for steps 1.8, 3.1, 4.0, 4.1a, 4.1c: "steps-draft"; ⟶ for 2.1's checker: "step-prompts"; ⟶ for steps 3.1, 3.4, 4.0a: "step-prompts-checked"; ⟶ for step 3.4: "stale" (only after a /back lands here)
├ 🙋 🖥 🤝 **3.1** TALK — ROLE-PLAY IT: "Ready to try it?" then acts the skill out screen by screen in the person's chair, until the spec is filled; real work by hand, never claims the automation exists, notes in the background what it did by hand for the plan; guards still apply; the person gives feedback on each step; refines sub-steps and proofs while acting; questions shown in the scene or at most four at the end of a round; warns on non-conformance; sub-steps, proofs and the §9/§10 blanks are worked out in the background and recorded in the packet (they reach the spec once, at 4.0a); notes mid-scene are just said; the step runs until `/next`, no other end point; anything done by hand is recorded and checked before it is done again (safe to run twice); each acted screen is shown in the skill's own frame; the step-prompt drafts from 2.1 are what each acted step follows, and the person's reactions refine them, saved by 3.4 [inferred]
│         WATCHING MODE: as in §1 item 3; no extra command, fork or code choice; the one hard line is L22
│         ⟵ incoming from 1.1: "packet-path"; ⟵ from 2.1: "steps-draft", "step-prompts-checked" (what each acted step follows); ⟵ from 3.3: "heal-checked" (optional); ⟵ from 4.3 (via 4.4): "tension-rulings" (optional); ⟵ from 5.3 (via 5.6): "correction" (optional); ⟵ from 3.2, 3.3, 3.4: "status"
│         no steps-draft → shows status lines or "waiting: steps from 2.1"
│         anything the system cannot do yet (for example a service not connected) is said plainly and the person is asked whether to use made-up data; used only on their yes and labelled made up [labelling inferred] (L22); a file the person hands over in this step is read through the plugin's `ingest-reader` agent at the small tier, never read raw (approved 2026-11-24)
│         a flow-changing break comes back as "my helper found something that changes how this works; I need your view"
│         ⑂ keep refining or move on? `→ CODE (refine|move-on|none-of-these)` · refine → 3.1 · move-on → 4.0 (through /next); a command skips to 5.0 and 4.0a–4.6 never run for it
│         ⟶ for step 3.2: "break" (only when something breaks); ⟶ for step 3.4: "answers"; ⟶ for step 3.4: "stale" (only after a /back lands here)
├ ➡️🏃 ⚙️ **3.2** ALONE — self-healing: when something breaks, a background helper finds what is broken (a component, a skill, a part) and researches a fix while 3.1 keeps going; records the fix in the packet (deferred work for the build), never edits the harness or the skill (L2) [inferred]
│         ⟵ incoming from 3.1: "break"; no break → doesn't run, no status; launch message: the break, packet path, plugin root, finish signal; failed → "stopped: heal failed: <reason>"
│         ⟶ for step 3.3: "heal-proposal"; ⟶ for step 3.1: "status" (only when waiting or stopped)
├ ➡️🏃 ⚙️ **3.3** ALONE — a separate checker confirms the fix against the plugin; a clear fix goes to 3.4 for the packet without asking; a flow-changing one is flagged for 3.1 [inferred]
│         ⟵ incoming from 3.2: "heal-proposal"; none → waits; failed → "stopped: check failed: <reason>", fix withheld
│         ⟶ for steps 3.1, 3.4: "heal-checked"; ⟶ for step 3.1: "status" (only when waiting or stopped)
├ ➡️🏃 💾 **3.4** ALONE — saves into the packet every turn: his words as SAID (a ruling only on his yes on a play-back), the rulings, research, notes, what 3.1 did by hand or saw while watching (carried in "answers"), the refinements to the step-prompt drafts, every background finding as it happens, and any needed part as deferred work the moment it is found; it does NOT rewrite the spec's blanks (the spec is brought up to date once, at 4.0a) [inferred]
│         ⟵ incoming from 1.1: "packet-path"; ⟵ from 3.1, 3.3: "answers", "heal-checked" (optional); ⟵ from 2.1: "step-prompts-checked" (the drafts it refines); ⟵ from the TALK sub-step landed on after a /back: "stale" (optional)
│         helper: `prompts/subagents/packet-writer.md` (BUILT; tier medium, approved 2026-11-24), a model tier named, never a model; its §5 sections are the existing "packet-updated", "stale" and "status"; **no checker:** internal output, not shown to the person here; the person sees the packet again at step 5 (nothing reaches the PERSON unchecked; decided 2026-11-24)
│         no packet-path → waits; no answers → writes nothing, "waiting: answers from 3.1"; failed → "stopped: packet write failed: <reason>"
│         marks each section named in "stale" as stale (the mark only) and removes it when the person re-confirms it [inferred]
│         a needed part (a hook, a scheduled job, an outside connection, a sheet) is never designed here: the tool builder is called by prompt hand-off with the packet, or, while it does not exist, the part is deferred work
│         ⟶ for steps 4.1a, 4.1c: "packet-updated" (a command has no step 4); ⟶ for step 5.2: "stale"; ⟶ for the project's tracking list, through the project-manager skill only (or the packet's own deferred work): a plain description of the part; ⟶ for step 3.1: "status"
├ ➡️🏃 💾 **4.0a** ALONE — BRING THE SPEC UP TO DATE, the first thing in step 4: a sub-agent writes every ruling made since the spec was last written into the spec, and a second sub-agent, a different model, checks every ruling landed and nothing old contradicts it, so the five reviewers read the current design [inferred]
│         ⟵ incoming from 1.1: "packet-path"; ⟵ from 2.1: "step-prompts-checked" (written into §11); launch messages carry the packet path and the form; failed → "stopped: spec update failed: <reason>", the reviewers do not run on an old spec
│         ⟶ for step 4.0: "status" (only when waiting or stopped)
├ 🙋 🖥 🤝 **4.0** TALK — THE PREP REPORT: orients in under two sentences; a leveraged list of what is still undecided (open §8 items and the most load-bearing `[inferred]` lines), most to least load-bearing, each with the AI's recommendation, how confident it is and how load-bearing, at most six at a time, with the current completion figure; the person decides now or lets the five reviewers guess first; reached by `/next` from step 3, or from step 2 when step 3 was skipped [inferred]
│         ⟵ incoming from 4.0a: "status"; ⟵ from 1.1: "packet-path"; ⟵ from 2.1: "steps-draft"; missing → "waiting: packet from 1.1" / "waiting: steps from 2.1"
│         ⑂ decide now, or let the reviewers guess first? `→ CODE (decide-now|let-reviewers-guess|none-of-these)` · decide-now → 4.0 (written to the packet; confirmed only on their yes) · let-reviewers-guess → 4.1a (items stay open; proposals reach the person at 4.3) [inferred]
│         ⟶ for steps 4.1a, 4.1c: "prep-decisions"
├ ➡️🏃 ⚙️ **4.1a** ALONE — THE FOUR REVIEWERS read the whole draft spec blind, at the same time where possible (a strong recommendation, not a rule): four critics from the old tension swarm, with the logic lens rewritten by the owner's ruling: the screens (a beginner taught and oriented on every screen; every sentence names who does what; the specific ROLE the person plays at this moment is clear), the logic (AI handing back to code is the first suspect for a brittle break), what gets saved (all the value and trust for the fewest tokens; ends with the context-rot line), and the order (a second look with the others' findings, only if they found something); the recipe holds the exact prompts (§6); a tension is reported only where two parts would produce different work or a blank is open, each with a suggested fix; each reviewer also lists the facts it found missing that LOOKING could answer [inferred]
│         ⟵ incoming from 2.1: "steps-draft"; ⟵ from 3.4: "packet-updated" (absent when step 3 was skipped); ⟵ from 1.1: "packet-path" (used when "packet-updated" is absent); ⟵ from 4.0: "prep-decisions" (optional)
│         a one-step command → never runs; on a repeat after a `/back`, full pass or targeted is the AI's judgment
│         no steps-draft or no packet → waits, helpers not launched; each launch message carries its lens, the draft spec's path, the steps-draft, the finish signal; nothing to add → empty tensions; failed → rerun once, then "stopped: critic failed: <reason>"
│         ⟶ for step 4.2: "tensions"; ⟶ for step 4.1b: "open-facts" (the open items answerable by looking: those the prep report left open, plus the facts the four said were missing); ⟶ for step 4.3: "status" (only when waiting or stopped)
├ ➡️🏃 💾 **4.1b** ALONE — THE RESEARCH PASS (option A, approved): as many small parallel sub-agents as needed, one per open item answerable by looking, each with the newer source winning, so the proposer works from facts, not guesses; every finding saved to the packet's findings document as it happens; items that truly need the build are left for the planner (L26) [inferred as to method]
│         ⟵ incoming from 4.1a: "open-facts"; ⟵ from 1.1: "packet-path"; no open-facts → waits; empty open-facts → empty facts, nothing launched; failed → rerun once, then "stopped: research pass failed: <reason>" (4.1c runs without the facts and says so)
│         ⟶ for step 4.1c: "facts"; ⟶ for step 4.3: "status" (only when waiting or stopped)
├ ➡️🏃 ⚙️ **4.1c** ALONE — THE RULEBOOK PROPOSER, always LAST: orthogonal; reads the whole draft spec blind, the skills checklist and SOP (the plugin's `canon/skill-building-sop.md` is handed to it; approved 2026-11-24), and the facts; works out accurate directional PROPOSALS for whatever is unresolved, working down the recipe's fixed order of sources, never filling a blank itself; writes for the audience of L23; the recipe holds how it works out its solutions (§6) [inferred]
│         ⟵ incoming from 4.1b: "facts" (empty when nothing was answerable by looking); ⟵ from 2.1: "steps-draft"; ⟵ from 3.4: "packet-updated" (or "packet-path" from 1.1 when absent); ⟵ from 4.0: "prep-decisions" (optional)
│         launch message: the draft spec's path, the steps-draft, the facts, the checklist's and SOP's paths, the finish signal; nothing to add → empty proposals; failed → rerun once, then "stopped: proposer failed: <reason>"
│         ⟶ for step 4.2: "proposals"; ⟶ for step 4.3: "status" (only when waiting or stopped)
├ ➡️🏃 ⚙️ **4.2** ALONE — a separate checker (a different model from the helpers) verifies every tension and proposal against the spec's actual text, then de-duplicates them "to make sure we're not surfacing 100 options that are really five", orders them most to least load-bearing, marks each optional or not [inferred]
│         ⟵ incoming from 4.1a: "tensions"; ⟵ from 4.1c: "proposals"; either missing → waits; failed → "stopped: check failed: <reason>", tensions withheld
│         ⟶ for step 4.3: "tensions-checked", "status" (only when waiting or stopped)
├ 🙋 🖥 🤝 **4.3** TALK — explains step 4 from scratch as a five-angle check, as if to someone new: "the audit ran, N problems found, here is what is still unresolved, with my suggestion"; shows the checked findings, de-duplicated and ordered, each marked optional or not, each with a concise conversational explanation and fix, up to six at a time, then the next batch, as many rounds as it takes, with no step-runner machinery for the rounds; the person rules (advisory, never blocking); the role-play offer [inferred]
│         ⟵ incoming from 4.2: "tensions-checked"; ⟵ from 4.1a, 4.1b, 4.1c, 4.2: "status"; none → shows status lines or "waiting: checked tensions from 4.2"; nothing to report → "the five readers found nothing that changes the work"
│         ⑂ the next batch, a redesign, or move on? `→ CODE (more|redesign|move-on|none-of-these)` · more → 4.3 (next six) · redesign → 4.4 · move-on → 4.5 (through /next; validation first); in step 4 "move on" moves between the sub-steps inside the step, only a typed `/next` changes the step, and the validation check finishes as step 5 opens (approved 2026-11-24)
│         ⟶ for step 3.1: "tension-rulings"
├ 🔁 **4.4** tells the person to type `/back` once (step 4 to step 3), where the fixes ("tension-rulings") are applied to the acted-out skill and the spec and checked again, until move-on at 4.3 (a `/back` may also replay one role-play step); never moves the step itself; a small fix needing no new acting is made inside 4.3; after the `/back` 3.1 marks the sections from 3.1 on stale in the packet [inferred]
├ ➡️🏃 💾 **4.5** ALONE — THE VALIDATION MOMENT, the work: a sub-agent writes every answer and ruling from 4.3 into the spec (as 4.0a does), and a second, a different model, re-validates how complete the spec is, load-bearing slots first, noting any not confirmed or stale; aiming for 100% as a hope only; nothing is gated on it; lists the slots still missing so the person sees them before the hand-off [inferred as to method]
│         ⟵ incoming from 1.1: "packet-path"; launch messages carry the packet path and the form; nothing missing → validation "complete"; failed → "stopped: validation failed: <reason>" (4.6 says the check did not run; the person may still move on)
│         if the person types `/next` while this finishes (L25), the screen moves on at once and the check finishes as the opening of step 5 [placement inferred]
│         ⟶ for steps 4.6, 5.0: "validation" (complete, or the missing slots with a best guess each), "status" (only when waiting or stopped)
├ 🙋 🖥 🤝 **4.6** TALK — THE VALIDATION MOMENT, the screen, for the audience of L23: orients in under two sentences, says plainly "your answers are in; I checked the whole design; all of the important parts are filled" or lists, up to six at a time, the slots still missing each with a recommendation, how confident it is and how load-bearing, and a one-line reason it matters; ends with the sliding-scale last words (L17), which inform and never insist [inferred]
│         ⟵ incoming from 4.5: "validation", "status"; none → shows status lines or "waiting: validation from 4.5"
│         ⑂ fill the gaps, or move on? `→ CODE (fill-gaps|move-on|none-of-these)` · fill-gaps → 4.5 (answers written in, spec checked again) · move-on → 5.0 (through /next, never held for a running check, L25; a slot still missing stays an open §8 item with a recommendation, L5, and never blocks, L9) [inferred]
├ 🙋 🖥 🤝 **5.0** TALK — THE PARTS ROUND (its own sub-step), once the whole skill is locked and before the compile: opens with "a few more quick questions are coming for the tool builder; it'll be quick because everything carries over, and only what you alone can answer is asked", for the audience of L23; when the packet carries a part still owed (a hook, a scheduled job, a connection, a sheet) a quick round with the tool builder by prompt hand-off, which pre-fills from the whole packet and asks only what only the person can give, in the same window when there is room; results land in the packet; when the tool builder does not exist yet the part stays deferred work, and then 5.0 asks no parts questions and says so in one line (approved 2026-11-24); when none is owed it says so in one line and the person types `/next`; the heads-up and the round run only when a part is owed (no question that is not really open) [inferred as to its place]
│         ⟵ incoming from 1.1: "packet-path"; ⟵ from 4.5: "validation", "status" (optional; when the check was still finishing, 5.0 opens by saying so, L25)
│         ⑂ keep going with the parts, or move on? `→ CODE (refine|move-on|none-of-these)` · refine → 5.0 · move-on → 5.1 (through /next)
│         helper: `prompts/subagents/tool-builder-handoff.md` (a model tier named, never a model); it writes "tool-builder-message" (one per owed part, only when the tool builder exists), which 5.0 sends after the mechanical path check; no checker: that path check and the tool builder's own round with the person stand in for one [inferred]
│         ⟶ for step 5.0 (to send): "tool-builder-message"; ⟶ for step 5.1: "parts-result" (what the tool builder settled, "none owed", or "deferred")
├ ➡️🏃 💾 **5.1** ALONE — compiles one clean draft spec: every ruling into Decisions, research folded in with pointers, notes routed (deferred work to the tracking list or packet; SOP candidates; brief notes, written through the project-manager skill only); names the first-principles document as a source when one exists; carries the step-prompt drafts into §11 whole [inferred]
│         ⟵ incoming from 1.1: "packet-path", "known" (optional); ⟵ from 5.0: "parts-result" (optional); no packet-path → waits; failed → "stopped: compile failed: <reason>"
│         ⟶ for steps 5.2, 5.3, 5.4: "draft-spec"; ⟶ for step 5.3: "status" (only when waiting or stopped)
├ ➡️🏃 ⚙️ **5.2** ALONE — a separate checker: every ruling is in Decisions, every routed note landed, and a report of which blanks are empty, what the form's "ready for the planner?" check says, which sections are still stale, whether the section "FOR THE PLANNER AND THE BUILD" is carried in, and any step with no step-prompt draft in §11; it reports and informs and never blocks (L9) [inferred]
│         ⟵ incoming from 5.1: "draft-spec"; ⟵ from 1.1: "packet-path"; ⟵ from 3.4: "stale" (optional; absent = nothing stale); missing → waits, checker not launched; failed → "stopped: check failed: <reason>", spec withheld
│         ⟶ for step 5.3: "draft-check", "status" (only when waiting or stopped)
├ 🙋 🖥 🤝 **5.3** TALK — LEADER MODE, on the house style's Screen B: no numbered question list; its "what you do now" line sits above the bar, as Screen B has it. A short opening: the step line and ONE sentence of where we are, then that the skill has NOT been built yet: "I've been keeping notes, we have not built this skill yet, here is a readout; make sure it is correct"; plays the draft back as that readout at three altitudes; asks "who is this for?" once, only when not already known, with the guess "just for you"; then says plainly what happens next (everything goes to /autoplan, design on top; the plan is built with little needed from the person; the plan's last step sharpens this spec and files the skill) and what they do: "if the readout is right, type /next and I'll hand it over; if something's off, just tell me" — the person's `/next` is the "go ahead and build this skill" moment, when decided and agreed or close enough [inferred as to wording]
│         ⟵ incoming from 5.1: "draft-spec"; ⟵ from 5.2: "draft-check"; ⟵ from 5.1, 5.2: "status"; no draft-check → shows status lines or "waiting: checked draft spec from 5.2"
│         ⑂ who is it for? `→ CODE (for-me|for-everyone|none-of-these)` (asked once, skipped when already known). It is Screen B's single question: the question on one line, then its one line with the three tags, "*Recommendation:* just for you · *Confidence:* <…> · *Load-bearing:* <…>"; no other question appears on the screen · for-me → filing "for me" (`~/.claude/skills/<name>/`) · for-everyone → filing "for everyone" (the plugin repo, on a branch, offered back as a PR; canon/manual.md:963); repo, branch and push follow the GitHub SOP §0c, never this skill (L27)
│         ⑂ send it? `→ CODE (send|not-yet|none-of-these)` · send = the person's `/next` → 5.4 · not-yet = the person says what is off `→ LLM (open)`, then 5.6
│         ⑂ where does it go? `→ CODE (autoplan|project-window|none-of-these)` · the screen says it goes to /autoplan; the person's `/next` with no other word = autoplan; project-window only on their word · both → 5.4 [inferred]
│         ⟶ for step 5.4: "destination", "filing"; ⟶ for step 3.1 (via 5.6): "correction"
├ ➡️🏃 💾 **5.4** ALONE — the technical hand-off, one of the TWO: hands everything gathered, written for the next AI, to the destination the person chose: the updated spec on top, treated as settled, plus the whole packet, research included, so nothing is researched twice (L6); files the packet as the record: the packet stays in its folder as the record and the hand-off points at it (a link given to project-manager when there is a project, never a copy); no records/ copy and no journal ledger row (decided 2026-11-24)
│         the HAND-OFF NOTE states three things. (1) There is no extra stage after the build: the plan's FINAL step sharpens and finalizes this draft spec with everything the build discovered (code, JSON, checkers, telemetry); that spec then becomes official, and the skill and its spec are filed per "filing": for me → `~/.claude/skills/<name>/`; for everyone → the plugin repo on a branch, offered back as a PR; routing per the GitHub SOP §0c (canon/build-conformance-sop.md:49). (2) THE GATE (coordinator, 2026-11-23): every item in the spec's section "FOR THE PLANNER AND THE BUILD" must be closed, or deferred by the person with a reason, as part of the build's DONE MEANS and of /autoplan's plan; the skill's component page cannot get its stamped status until that section is empty. (3) §11's step-prompt drafts become the skill's `prompts/` files, and the spec wins where they disagree [inferred].
│         ⟵ incoming from 5.1: "draft-spec"; ⟵ from 1.1: "packet-path"; ⟵ from 5.3: "destination", "filing" (absent → the note says "who it is for: not asked; for me assumed" [inferred]); any of the first three missing → waits; failed → "stopped: hand-over failed: <reason>", nothing is sent twice
│         helper: `prompts/subagents/handoff-note.md` (BUILT; tier medium, approved 2026-11-24), a model tier named, never a model; **no checker:** it goes to the planner AI, whose own vetting checks it, not to the person (decided 2026-11-24)
│         ⟶ for the destination (outside this skill): "handoff-note", the draft spec file on top, plus the packet folder (L6); ⟶ for step 5.5: "status" (the result, or why it waited or stopped)
│         what follows /autoplan is outside this skill
├ 🙋 🖥 **5.5** TALK — LEADER MODE, no question section, on the house style's Screen B: the plain on-screen hand-off, the second of the TWO, for the audience of L23: orients in under two sentences, says where the spec went, where the packet is filed, that the plan's last step sharpens this spec and files the skill where it belongs (no extra stage after the build), and that the "for the planner and the build" items must be closed before the skill can be stamped, or what stopped [inferred]. The final screen ends with a plain line that the run is complete, and offers no second `/next` (it would end the run); a failed hand-off says "try again" (approved 2026-11-24)
│         ⟵ incoming from 5.4: "status"; none → "waiting: hand-over result from 5.4"; saves any reply verbatim, SAID
├ 🔁 **5.6** a small correction to the draft is made inside step 5 without moving (5.1 compiles again, 5.2 checks, 5.3 shows); a correction that changes the design tells the person to type `/back` twice (step 5 to 4 to 3; once for a command), where it is applied ("correction"); repeats until send at 5.3; never moves the step itself; the landing sub-step marks sections from 3.1 on stale in the packet [inferred]
└ ✅ **Done when** the person has a draft spec they said yes to (as complete as they chose), /autoplan holds it with the whole packet, and the packet is filed
```

## 5. HANDOFFS AND THE SCRATCHPAD

Layout (BUILT; the step prompts name these sections, approved 2026-11-24): each section is one file, `<packet>/scratchpad/<section>.md`, where `<packet>` is the packet folder of sub-step 1.1. A section counts as present only when its file exists and is not empty after trimming (`scripts/inputs_check.py`, which also prints the waiting line when a section is missing and launches nothing).

| section | who writes | who reads |
|---|---|---|
| handoff-in | background (/build) | 1.1 |
| packet-path | 1.1 | 1.2, 1.4, 1.6, 1.8, 1.9, 3.1, 3.4, 4.0, 4.0a, 4.1a, 4.1b, 4.1c, 4.5, 5.0, 5.1, 5.2, 5.4 |
| known | 1.1 | 1.4, 5.1 |
| pointed-skill | 1.4 | 1.2 |
| which-skill | 1.4 | 1.8 |
| skill-reading | 1.2 | 1.3 |
| skill-checked | 1.3 | 1.4, 2.1 |
| outcome | 1.4 | 1.6, 1.8, 1.9, 2.1 |
| harness-findings | 1.6 | 1.7 |
| harness-checked | 1.7 | 1.4, 2.1 |
| research-mark | 1.8 | 1.4, 2.1 |
| size-sense | 1.9 | 1.4 |
| steps-draft | 2.1 | 1.8, 3.1, 4.0, 4.1a, 4.1c |
| step-prompts | 2.1 (its helper, step-prompt-drafter; one draft per agreed step) | 2.1 (its checker, checker-step-prompts) |
| step-prompts-checked | 2.1 (its checker, checker-step-prompts) | 3.1, 3.4, 4.0a |
| break | 3.1 | 3.2 |
| heal-proposal | 3.2 | 3.3 |
| heal-checked | 3.3 | 3.1, 3.4 |
| answers | 3.1 | 3.4 |
| packet-updated | 3.4 | 4.1a, 4.1c |
| prep-decisions | 4.0 | 4.1a, 4.1c |
| tensions | 4.1a | 4.2 |
| open-facts | 4.1a | 4.1b |
| facts | 4.1b | 4.1c |
| proposals | 4.1c | 4.2 |
| tensions-checked | 4.2 | 4.3 |
| tension-rulings | 4.3 | 3.1 |
| validation | 4.5 | 4.6, 5.0 |
| tool-builder-message | 5.0 (its helper, tool-builder-handoff; one message per owed part, only when the tool builder exists) | 5.0 (sends it to the tool builder by prompt hand-off, after the mechanical path check) |
| parts-result | 5.0 | 5.1 |
| draft-spec | 5.1 | 5.2, 5.3, 5.4 |
| draft-check | 5.2 | 5.3 |
| destination | 5.3 | 5.4 |
| filing | 5.3 | 5.4 |
| correction | 5.3 | 3.1 |
| handoff-note | 5.4 (its helper, the technical hand-off note) | the destination, outside this skill (sent with the draft spec on top and the packet) [inferred as to the name] |
| stale | the TALK sub-step landed on after a /back (1.4, 2.1, 3.1; the packet's list, not the runner), 3.4 | 3.4, 5.2 |
| status | 1.1, 1.2, 1.3, 1.6, 1.7, 1.8, 1.9, 3.2, 3.3, 3.4, 4.0a, 4.1a, 4.1b, 4.1c, 4.2, 4.5, 5.1, 5.2, 5.4 | 1.4, 2.1, 3.1, 4.0, 4.3, 4.6, 5.0, 5.3, 5.5 |

## 6. ONE HOME PER FACT

Paths not marked as plugin paths are in the owner's design records (private; not shipped; no plugin-side home yet). Private-name rule: when this spec is filed in canon or the plugin, "Nothing private in the plugin" applies (the standing plugin-wide rule, not a skill builder step; checklist: no private names or personal paths in a Harness skill; L8). Every pointer into the private notes (the owner's design records, this packet, private plans) is then replaced by a plugin-side home [inferred as to which pointers move].

| definition | one home |
|---|---|
| The role (the detective) | the owner's design records (private; not shipped) |
| The /build decision tree | the owner's design records (private; not shipped) (its three sizes are superseded by the count-the-steps ruling) |
| The skill builder's decision tree (POINTER; no copy here) | the owner's design records (private; not shipped) (draft 7) |
| Shake the tree: the shared review recipe, fixed and variable parts (POINTER; no copy here) | the owner's design records (private; not shipped) (moves into the plugin; all builders point to it) |
| The skill spec form | the owner's design records (private; not shipped); rebuilt as form v2: plugin system/templates/skill-spec-form/skill-spec-form-v2.md |
| The packet format and the compile | the owner's design records (private; not shipped) |
| His own words, verbatim | the owner's words, verbatim (private record) |
| Every ruling | the owner's design records (private; not shipped) |
| The house style (screens A, A command form, B, Block C; the question block; the closing line; footer phrases), written ONCE, every prompt points here | plugin system/templates/skill-spec-form/house-style.md |
| The step prompt and sub-agent brief templates, pre-filled | plugin system/templates/skill-spec-form/step-prompt-template.md, subagent-brief-template.md |
| The five step instructions (the wording; this spec only lists them, §11) | the skill's `prompts/step-1…5` (BUILT; the older working copy is in the owner's design records, not shipped) |
| The audience profile and the detective role, as delivered | the opening blocks of each step prompt in the skill's `prompts/` (sections 1 and 2; at the start of each step, not every turn); the role's source stays in the owner's design records (private; not shipped) |
| The owner's words recovered from the whole session | the owner's design records (private; not shipped): the recovered session words and the findings drawn from them |
| Who is it for (where a person's build is filed) | plugin canon/manual.md:963 (where-things-live) |
| Repo, branch and push routing | the GitHub SOP §0c (never this skill, L27) |
| The skill scaffold | plugin system/templates/skill-template/ (the newer source; `new-skill.sh` is older, debt ledger) |
| The opening screen (approved, fixed text) | plugin `.claude/skills/skill-builder/references/opening-screen.md` (BUILT, text unchanged); the approved original is in the owner's design records (private; not shipped) |
| Research, notes, hand-off, gaps, transfer list, reviews | the owner's design records (private; not shipped): the packet (the findings document, the research-for-build note, the notes, the archived hand-off, the gaps list (private record), the archived transfer list, the reviews); everything not in this spec is there, and all of it goes to /autoplan with this spec |
| Presentation rules (map first, no tables, one bold line, numbered; short screens) | plugin archive/2026-10-31-skill-builder-closed-for-renovation/skill-builder/SPEC.md lines 1046–1250 (presentation only) |
| The skills checklist | the owner's design records (private; not shipped) (the final checklist; later the skills SOP, plugin canon/skill-building-sop.md); changes go through the canon window as a change card |
| The shared step runner (/next, /back) | plugin system/parts/stage_runner.py |
| Status notes (tiles): envelope, location | plugin canon/status-emission-sop.md |
| Checker proof ("wired and seen refusing once") | plugin canon/status-health-proof-sop.md |
| The plan's own rulings | the build's private plan, RULINGS section (private; not shipped) |
| The emoji key (🤖 This session · 🙋 You · ➡️🏃 Sub-agent · 🌙 Earlier machinery) | the owner's design records (private; not shipped); one definitive key across Lifehack is a debt-ledger task |
| The locked list · the scratchpad table | this spec, §2 · §5 |

## 7. PROOF — HOW WE KNOW IT WORKS

Marks (finish pass, 2026-11-24): the proofs below were all [hypothesis] when this section was designed. The build ran them; each is now **[tested]** with its record (a section of the skill's `BUILD-NOTES.md`) or **[to prove]** with why. By the owner's ruling (2026-11-24) done means every automated test passes; there is no real-job trial, and the skill is fixed in use.

- **A fresh-window run** [to prove]: one real skill designed through the skill builder in a fresh window not told it is watched; a watcher reads that session's records and the packet afterwards. Not run, by the owner's ruling (BUILD-NOTES "Deviations from the build plan (approved)" and "Not tested"); the filed page states the claim scoped: not tried on a real job. What the run would ask: Did it frame big first? At most four questions a round? Acting out as the main mode? Every answer written down? Everything gathered handed over, the updated spec on top? Every step opened with a full reorientation? No question section in step 5?
- **Nothing grades its own work** [tested]: 1.3 checks 1.2; 1.7 checks 1.6; 3.3 checks 3.2; 4.2 checks 4.1a and 4.1c; 4.0a's and 4.5's second sub-agent checks the first; 5.2 checks 5.1; 2.1's step-prompt drafts are checked inside 2.1 (checker-step-prompts). The pairs exist as briefs (§11) and were seen refusing planted faults (BUILD-NOTES "Planted bad inputs"). **Built as:** every brief runs at tier medium, so a checker is a separate sub-agent with a stricter brief, claim by claim against named sources and blind to the author's reasoning, not a different model family (BUILD-NOTES "Nothing grades its own work"). **No checker, and why:** 1.8 (the research mark: its research results are checked where they are used); 1.9 (the size sense: the person sees a "too big" sense plainly at 1.4 and may correct it; it is never enforced); 5.0 (the tool-builder message: the main window checks its file list mechanically before sending, and the tool builder's own round confirms with the person) [inferred as to 5.0]; 3.4 and 5.4 (a 2026-11-24 ruling: internal output, and a note to the planner AI whose own vetting checks it).
- **Planted bad inputs** [tested for 8 of the 9 listed; 8 of 8 recorded plants caught after one fix]: a ruling missing from Decisions (5.2); an invented tool in the harness findings (1.7); an existing skill described with a step it does not have (1.3); a critic's tension that misquotes the spec (4.2); a blank left empty at hand-off and a section still stale at hand-off (5.2 reports both, never blocks; one plant); a handoff arrow with only one end (the reviewer-logic brief, which was fixed to name both ends of every section; re-quizzed 6/6); a "never" not in the locked list (§2). BUILD-NOTES records an eighth plant that is not on this list (an injection line inside person-supplied text: not obeyed, not repeated). **[to prove] and not planted:** a hand-off to /autoplan without the spec on top, or with the research left out (L6): no checker exists for 5.4 by ruling.
- **The code's own tests** [tested]: `python3 -m unittest discover -s scripts/tests`, run in the skill folder 2026-11-24: 62 tests, OK. Each script has good, edge and padded cases and a broken-copy case that proves its check can fail (BUILD-NOTES "Code (P5)").
- **The live runner check** [tested]: a fresh V2 window, a scratch folder outside the plugin: `start` printed the step-1 prompt; the person's typed `/next` and `/back` moved the run; a session trying to move a talk step was blocked by the guard; plain words moved nothing; `stage_runner.py --selftest` passed (BUILD-NOTES "Live runner check"). The check found the injected step text cut off; the fix is under "Shared ownership" below.
- **The routing eval** [to prove]: `routing-eval.md` holds 15 cases (S1–S8 must start the skill, N1–N7 must not) with empty results; it runs on the final commit, on Claude, and is pending at the time of writing (BUILD-NOTES "Deviations from the build plan (approved)").
- **The real test** [to prove]: the skill the spec describes is built and conformance-checked by its own scripts and by the shared runner, and its spec is filed in canon only after the final proof and the push; how pleasant it is over months is not checkable from any artifact (§11).

## 8. OPEN — NOT YET DECIDED

1. **Optional steps in the shared runner** (formerly item 12): his word, "if number four is pretty easy to fix let's just do that". BUILT on the plugin's V2 branch: commit e9632fbb (2026-11-23), "a card step marked optional passes as skipped by the person, only on the person's /next turn; the AI can never skip" (`system/parts/stage_runner.py`, lines 339-343 and 682-712; read from the local copy of the plugin on 2026-11-24). CLOSED (coordinator, 2026-11-24): read back on GitHub, origin/V2 carries e9632fbb (2026-11-24); the build re-reads it at its start. So the card marks steps 3 and 4 `optional`; a skip is the person's own `/next`; the §4 fallback (a one-line skip screen for a runner without the field) is NOT built.
2. **Items 1–11 and 13 of the working spec are SETTLED and live as rulings, not here:** status notes live in `<brain>/status/` (the move is committed, push pending, 2026-11-23); both a status line (which step) and a reply bar (completion, questions, last words); example specs at `references/examples/`, never shown to the person, scrubbed before shipping; routing picks models; builders call each other by prompt hand-off; at most four questions a round; the compile lives in 5.1; a command skips step 4; too big goes back to /build, never enforced; step 3 does real work by hand; parts round at 5.0; no prescribed completeness; what goes to /autoplan: everything gathered, the design on top (the "to explain" question was answered and it is treated as settled).

**Status, finish pass 2026-11-24:** every item above is closed or settled as design. What remains open is build proof, tracked in THE GATE below (the routing eval on the final commit, the status-line wiring with run pickup).
3. **The step-prompt cold read in step 4.** CLOSED (coordinator, 2026-11-24): the cold read is covered by the comprehension quiz in the shake-the-tree recipe; no line is added to the 4.1a readers' launch. (Was: a proposed one-line addition to every 4.1a reader, "read §11 as the only text the future AI gets at that step".)
4. **The status bar's first line.** CLOSED (coordinator, 2026-11-24): the bar's first line is the locked text `🛠 Skill builder · Step N of 5: <name>`. The status line shows the runner's position, `RUN n/N stage (mode)`, not the bar text. Today the plugin's status line does not call the runner; that wiring goes to run pickup.
5. **The fresh window.** CLOSED (coordinator, 2026-11-24): there is no fresh-window rule for a direct `/skill-builder`; a coordinator window and a build window after /autoplan stay best practice only. (Was: round one's FRESH window reporting to the build-skill window, and a citation mismatch.)

## 9. HOW IT PLUGS INTO LIFEHACK (proposed form section; sorted by the owner's ruling into three groups)

**Always true (pre-filled by pointer; never copied):**
- Step count: five steps, so a **skill**. The step-runner rules apply, by pointer to the skills checklist: a card, the shared runner, `/next` and `/back`, one prompt file per step handed over by the shared runner at the START of that step only (never every turn), the inputs line and pause, the start-up pickup, the position on the status line.
- Every new skill starts BLANK from the skill template, never referencing or copying an old skill; its own decision list (D1, D2…) is fine.
- The screens: the house style, by pointer (`system/templates/skill-spec-form/house-style.md` in the plugin; written once).
- No private names when shipped: pointer to the plugin-wide rule "Nothing private in the plugin" (see §6). Not a skill builder step.
- Spec versus prompt files: the spec wins; where they disagree the prompt file is wrong and is fixed [inferred].
- One step instruction per step, handed over by the code at the START of that step only, describing that step only, opening with the reset (the audience profile and the detective role); nothing injected every turn (§11; skills checklist, by pointer).
- Shake the tree and the emoji key: pointers (§6).

**Asked now (design; answered here):**
- Words that start it: "/skill-builder", "build me a skill", "make this skill better" [inferred]. A vague "how do I make a skill" goes to /build, the front door, not here (coordinator second opinion, confirmed by him). Files it writes: the packet folder (findings saved as they happen) and the draft spec, including its step-prompt drafts (§11). Outside connections: none [inferred].
- Where the skill it designs is filed: asked once at the hand-off, "who is it for?" (L27).
- Early stop: the packet is saved every turn, so stopping loses nothing; the shared runner's abandon, resume and snooze pick it up [inferred].
- Required sections [inferred]: a skill, §1–§10; a command, §1–§3, its one step, §7 and §10; these inform the bar and never gate a hand-off.

**For the planner and the build:** see the section "FOR THE PLANNER AND THE BUILD" below.

## 10. HOW WE KNOW IT KEEPS WORKING (proposed form section)

- **The status note:** written by shared code at the end of each run, never by the skill itself; the envelope is pre-filled by pointer to canon/status-emission-sop.md. The shared writer is DEFERRED (root debt ledger §9, his word 2026-11-23). The shared tile writer (`status-tile.lib.sh`) writes to `<brain>/status/` (data-layout; the folder move is on origin/V2, commit affa2be5, read back 2026-11-24).
- **What "it worked" means:** a draft spec was handed over and the 5.2 check ran; how complete it was is the person's call and the bar shows it [inferred]. The person's answer to "what would make you stop trusting it?" (1.4) is added here.
- **The completion figure** (L17) [inferred method]: computed by code as the share of the form's slots that are filled AND confirmed (not `[inferred]` or `[hypothesis]`), every open §8 item counted unfilled, stale sections not counted; informs and never insists.
- **Rhythm:** on demand, no stale timer. **Checkers inside it** (1.3, 1.7, 3.3, 4.2, 5.2) each write their own receipt and count only once seen refusing a planted fault (status-health-proof-sop.md).
- **Built (2026-11-24):** the status writer stays DEFERRED: the skill is an interactive manual command with no scheduled run, and it gains a tile only if it ever gains a scheduled or unattended step (BUILD-NOTES "Records block (P2)"). The completion figure is `scripts/completion.py`, tested (62 tests). Each checker was seen refusing one planted fault (BUILD-NOTES "Planted bad inputs"); a receipt written by code, one command and its exit code, is the final-proof step and is pending at the time of writing.

## 11. STEP PROMPTS (proposed form section)

**One home.** The wording lives in the files; this section only lists them and says how they grow. Where a file and this spec disagree, the spec wins and the file is fixed (§9).

**The skill builder's own five step prompts** (BUILT 2026-11-24 from this spec, the rulings and the recovered session words; folder `prompts/` of the skill):

| step | file | covers |
|---|---|---|
| 1 What you want | `prompts/step-1-what-you-want.md` | 1.1–1.9 |
| 2 The proposed steps | `prompts/step-2-the-proposed-steps.md` | 2.1 (the emoji walk-through) |
| 3 Role-play it | `prompts/step-3-role-play-it.md` | 3.1–3.4 (watching mode, honest acting) |
| 4 Shake the tree | `prompts/step-4-shake-the-tree.md` | 4.0a–4.6 (prep report, the owner's order, six at a time, the final check) |
| 5 The hand-off | `prompts/step-5-the-hand-off.md` | 5.0–5.6 (LEADER MODE with no question section, the corrected ending, who is it for) |

- **The reset, at the top of every file**: a short "who you're talking to" block (the audience of L23; full reorientation: where they are in the whole run, what this step is for, what ROLE they play now) and a short detective block (L20). These are NOT separate shared files and are NOT injected every turn; they come once, at the start of each step.
- **Step instructions and helper briefs are different things** (the owner's question: "how can there be 29 instructions on an eight-step skill?"). A step instruction is handed to the AI in this window at the start of a step: five of them. A helper brief is handed to a sub-agent that cannot see the conversation: 26 brief files (24 run briefs + 2 shared bases), below; 31 prompts in all.
- **Shape**: each step instruction is made from the step prompt template, each helper brief from the sub-agent brief template (both in the plugin, `system/templates/skill-spec-form/`). The templates are PRE-FILLED: fixed text already written in, then a blank with its instruction inside it, never general principles; they both show the filled shape and tell how inside each blank. What the person sees is the house style (`system/templates/skill-spec-form/house-style.md`), named by path at its first mention, once, never copied. Precedent: planning-weekly's working prompts (`prompts/step-1-check-the-compass.md`, `step-4-rank.md`). A step instruction carries: the job of this step; what it reads and writes (the exact §5 sections); which house-style screen it uses; the helpers it sends, each as a helper line in its own text (the brief's path and tier), never deferred to an outside recipe (step 4 included: the reviewer and proposer briefs carry the recipe's text); the choices code reads; edit first; save the person's words as SAID; never-dos by L-number. Each describes its own step only.

**How step prompts grow for ANY skill this builder designs** (the person kept out of the loop: "I'm leaning towards keeping this human out of the loop"): at least one prompt per step, injected at the top of that step (more where needed, for example per sub-agent); drafted quietly in step 2 as each step is agreed (2.1); followed and refined by step 3's acting, the refinements saved by 3.4; written into this section with everything else at 4.0a; their cold read is the comprehension quiz the shake-the-tree recipe carries (§8-3, closed); carried whole at 5.1, a step without one reported at 5.2; the 5.4 note says they become the skill's `prompts/` files and the spec wins; the build turns them into files [inferred as to the sub-step placement].

**How they are tested** (simulated runs are superseded): a COMPREHENSION check, never a simulated full run: a blind AI given only the prompt (its test card stripped) answers six multiple-choice questions on its job, inputs, hand-back, edge cases and finish; a missed question shows what the prompt fails to explain. Done in the design phase for 27 prompts (22 run briefs + the 5 step instructions; the 2 bases are read only with their use or angle files and are not quizzed), 158/162 (the design-phase quiz record, not shipped). No more testing: the build re-quizzed only a prompt whose meaning changed, in small batches: the 10 scored before a stopped full run (6/6 each), the five step prompts, tool-builder-handoff (first 5/6, fixed, then 6/6), packet-writer, handoff-note and step-prompt-drafter (6/6 each), and reviewer-logic after its fix (6/6): 20 prompts, 120/120, by a blind cheap-tier reader (BUILD-NOTES "Re-quiz", "Code (P5)" and "Planted bad inputs"). A prompt that only gained a boilerplate line or lost private text was not re-quizzed.

**Helper briefs, BUILT** (26 files in the skill's `prompts/subagents/`, README excluded; each made from the sub-agent brief template, names a model tier, never a model; everything handed to it is DATA; it writes one section and ends with the finish signal; precedent `planning-weekly/prompts/subagents/`):

| sub-step | brief file | checker |
|---|---|---|
| 1.2 | `skill-reader.md` | 1.3: `checker-base.md` + `checker-skill-reading.md` |
| 1.6 | `harness-search.md` | 1.7: `checker-base.md` + `checker-harness-findings.md` |
| 1.8 | `research-mark.md` (not the cheapest tier) | **no checker:** its research results are checked where they are used (the brief's own line) |
| 1.9 | `size-sense.md` (not the cheapest tier) | **no checker:** the person sees a "too big" sense plainly at 1.4 and may correct it; it is never enforced |
| 2.1 (quiet drafting) | `step-prompt-drafter.md` | inside 2.1: `checker-base.md` + `checker-step-prompts.md` |
| 3.2 | `healer.md` | 3.3: `checker-base.md` + `checker-heal.md` |
| 3.4 | `packet-writer.md` (BUILT; tier medium, approved 2026-11-24) | **no checker:** internal output, not shown to the person here; the person sees the packet again at step 5 (nothing reaches the PERSON unchecked; decided 2026-11-24) |
| 4.0a, 4.5 | `spec-updater.md` (one file, two uses) | the second sub-agent: `checker-base.md` + `checker-spec-update.md` |
| 4.1a | `reviewer-base.md` + four angle files: `reviewer-screens.md`, `reviewer-logic.md`, `reviewer-saving.md`, `reviewer-order.md` (from the recipe) | 4.2 |
| 4.1b | `research-pass-item.md` | 4.2 checks what 4.1c makes of the facts |
| 4.1c | `rulebook-proposer.md` (from the recipe) | 4.2 |
| 4.2 | `tensions-checker.md` (the findings checker; it also de-duplicates and orders; its own brief, not a checker-base use) | (it is the checker) |
| 5.0 | `tool-builder-handoff.md` (the tool-builder message) | **no checker:** the main window's mechanical path check before sending, and the tool builder's own round confirms with the person [inferred] |
| 5.1 | `compiler.md` | 5.2: `checker-base.md` + `checker-draft-spec.md` |
| 5.4 | `handoff-note.md`, the technical hand-off note (BUILT; tier medium, approved 2026-11-24) | **no checker:** it goes to the planner AI, whose own vetting checks it, not to the person (decided 2026-11-24) |

Count (by `ls prompts/subagents | grep -v README | wc -l`, 2026-11-24): 26 files = 24 run briefs (the 22 designed + `packet-writer.md` + `handoff-note.md`) + 2 bases (`checker-base.md`, `reviewer-base.md`); with the five step prompts, 31 prompts. `findings-checker` appears nowhere in the skill (`grep -rn findings-checker` returns nothing); the name is `tensions-checker.md`.

## THE BUILT SKILL: FILES, COUNTS, COVERAGE, OWNERSHIP (finish pass, 2026-11-24)

Everything in this section was read from the built skill, `.claude/skills/skill-builder/`, on 2026-11-24, by running the commands shown, not copied from an earlier count.

**Counts, by command** (run in the skill's folder):

| What | Count | Command |
|---|---|---|
| Helper briefs | 26 (24 run briefs + 2 bases; the 22 designed + `packet-writer.md` + `handoff-note.md`) | `ls prompts/subagents \| grep -v README \| wc -l` |
| Step prompts | 5 | `ls prompts/step-*.md \| wc -l` |
| Scripts | 5 | `ls scripts/*.py \| wc -l` |
| Tests | 62, all pass | `python3 -m unittest discover -s scripts/tests` |
| Prompts re-quizzed in the build | 20 prompts, 120/120 | BUILD-NOTES "Re-quiz", "Code (P5)", "Planted bad inputs" (read from the record; a quiz is not a command) |

**Files, with marks** (checked against disk 2026-11-24):

| Part | Files | Mark | Tested by |
|---|---|---|---|
| The skill's page and card | `SKILL.md`, `card.json`, `routing-eval.md`, `BUILD-NOTES.md` | BUILT | the live runner check; the routing eval is pending |
| The five step prompts | `prompts/step-1-what-you-want.md`, `step-2-the-proposed-steps.md`, `step-3-role-play-it.md`, `step-4-shake-the-tree.md`, `step-5-the-hand-off.md`, `prompts/README.md` | BUILT | `scripts/prompt_sections.py`; quiz 6/6 each |
| The helper briefs | the 26 files in `prompts/subagents/` and its README | BUILT | quiz 6/6 where the meaning changed; the planted inputs |
| The five checks | `scripts/gates.py`, `completion.py`, `inputs_check.py`, `citation_check.py`, `prompt_sections.py`; `scripts/tests/test_*.py` (five files); `scripts/README.md` | BUILT | 62 tests, with broken-copy cases |
| References | `references/opening-screen.md`, `references/README.md`, `references/examples/README.md` | BUILT | text unchanged but for one bookkeeping line (BUILD-NOTES "Records block (P2)") |
| The shared runner and hooks (not this skill's) | the files under "Shared ownership" below | BUILT elsewhere; one CHANGES made by this build | the runner's own tests; the live runner check |

**Covered / not covered**, per check (the record is a section of `BUILD-NOTES.md`):

| Check | Covered | Not covered |
|---|---|---|
| Prompt quiz (a blind reader answers six questions from the prompt alone) | the 20 prompts whose meaning changed, 120/120 | the prompts unchanged in meaning were not re-quizzed; a quiz shows a reader understood the prompt, not that a run behaves |
| Planted bad inputs | 8 of 8 recorded plants caught or handled the designed way, after one brief fix | a hand-off to /autoplan without the spec on top or without the research (no checker for 5.4, by ruling) |
| Unit tests | 62, good, edge and padded cases and a broken copy per script | the AI parts: no unit test can cover them |
| Live runner check | start, `/next`, `/back`, the guard refusing a session, plain words moving nothing, `--selftest` | the plugin's status line showing `RUN n/N` (not wired; with run pickup) |
| Routing eval | 15 cases written (S1–S8, N1–N7) | not run: pending on the final commit |
| Not tested, by the owner's ruling (fixed in use) | | a window filling up mid-run; a student install; models other than those used; vague requests; a real job |

The card's output checks prove that a step's file has its headings, enough words and the code word; they cannot prove the text is real work (the runner's own "declared uncheckable" bound).

**The step-prompt writer's 15 calls.** Where this spec was silent, the writer of the step prompts made 15 calls. The owner approved them on 2026-11-24 ("if they don't change the design intention of the human then it's fine"): 14 were kept as written and one was corrected (step 1 names the shared-tools list, `system/register/toolbox.md`, which exists). Each is written into the §4 or §11 line it belongs to, marked "(approved 2026-11-24)".

**Shared ownership.** The runner files belong to run pickup, not to this skill: `system/parts/stage_runner.py`, `system/parts/run_pickup.py`, `system/hooks/run_step_hook.sh`, `system/hooks/run_pickup_hook.sh`, `system/hooks/guard_run_commands.sh` and `system/templates/skill-template/RUNNER.md`. The skill consumes them in place and copies nothing (G11). This build made one fix there, on the owner's exception (commit 52e4dca6 on V2): the mover's injection now starts with the full-prompt path and the code word, taken from the runner's whole output before the cut-off, because a long step prompt plus `/back` had dropped the fresh code word; the cut-off note now names the current stage file. Any other change to those files goes to run pickup.

## PRODUCER-SPEC TEMPLATE SECTIONS T0–T11 (finish pass, 2026-11-24; re-check of the P1 gap table)

"Producer" here is the template's word for a spec that precedes a skill; it is not "cron-producer". This skill has no scheduled run, so every cell about an unattended run states a null with its reason. Checked on 2026-11-24 against `system/templates/producer-spec-template.md` (updated_at 2026-11-14) and `system/templates/component-page-template.md` (rebuilt 2026-11-21). The gap table of P1 found 2 sections covered, 12 partly and 3 missing; each is filled below or pointed at. The numbering T0–T11 is the template's own section numbers; this spec's §1–§11 are its own.

### T0. How this spec's sections become skill files

**Why this section exists:** a real skill is many files with no obvious map back to the spec that produced it. Naming the map before writing either one stops the build from improvising a structure and stops the spec from describing things the skill has no file for.

| Spec section | Lands in |
|---|---|
| §1 What it is (T1) | `SKILL.md`: the desired outcome in the first lines |
| §2 Inputs (T2) | section 5 of each step prompt, "What you read and write", and `scripts/inputs_check.py` |
| §3 Inherited rails (§2 here, with its "Held by" table) | `SKILL.md` Musts, each step prompt's section 10 "Never", and the shared runner and hooks. No `ANCHOR.md`: null, because nothing is injected every turn; the start-of-step prompt does that job |
| §4 Write model (T4) | section 7 of each step prompt, "The helpers you send"; `prompts/subagents/` |
| §5 The grid (T5) | the per-step logic in sections 4–6 of each step prompt; the step list in `SKILL.md` "Procedure" |
| §6 Step chain (§4 here, T6) | `card.json` (five stages), `prompts/step-1…5`, `SKILL.md` "Procedure" |
| §7 Write targets (T7) | `SKILL.md` "Writes" line |
| §8 Definition of done (T8) | `BUILD-NOTES.md` gate table; THE GATE above |
| §9 Graceful degradation (T9) | null: no tiered inputs (reason in T9) |
| §10 Scratchpad (T10) | `scripts/inputs_check.py`; `SKILL.md` "If it stops early" |
| §11 Evidence and enforceability (T11) | no file of its own: the design-time tags that decide what can be graded |
| This spec's §3 triggers | `SKILL.md` frontmatter (`description`, `triggers`); `routing-eval.md` |
| This spec's §7 proofs | `BUILD-NOTES.md`; `scripts/tests/`; `routing-eval.md` |
| This spec's §11 step prompts | `prompts/` |

### T1. What the skill builder IS

**Why this section exists:** a skill that never states its own intent forces every session, including a compacted or cold one, to guess what it is for.

- **Layer 1, outcome and bar:** §1 "Desired outcome" and "How the person will know it worked".
- **Layer 2, role and autonomy:** the earnest detective (L20); **human-in-the-loop**. It reserves for the person what only the person holds: the "yes, that's it" that settles a line, the `/next` and `/back` that move a step, who the skill is for, and the decision to build. Supplying it is made effortless by fixed answer sets that end in `none-of-these`, and by a recommendation, a confidence and a load-bearing tag on every question.
- **Layer 3, per-run anchor:** null by ruling: nothing is injected every turn. The bar's first line, `🛠 Skill builder · Step N of 5: <name>` (L17), ends every reply and says where the person is; each step prompt reorients them once, at its start; the runner's status line is `RUN n/N`.

### T2. Inputs

**Why this section exists:** a skill that silently re-pulls its source mid-run can show the human a different picture than the one it started interrogating them about, a moving target they cannot correct against.

| Input | Source | Read once and held, or live? | If absent |
|---|---|---|---|
| The hand-over from /build ("handoff-in") | the background hand-over | read once at 1.1, held in the packet | a direct start begins from empty blanks (1.1) |
| A skill the person points at | the path the person names | live, by design: 1.2 re-reads each newly pointed skill, an exception to one-dataset because the person points at a new one | 1.2 launches nothing and the reading stays empty |
| The packet | `<packet>/` (T7) | live, by design: it is the working state, written every turn | 1.1 creates it; if it cannot, "stopped: packet not opened: <reason>" |
| The plugin's rules: `canon/skill-building-sop.md`, `system/register/toolbox.md`, the house style and templates under `system/templates/skill-spec-form/` | the plugin | read once by the step that needs them (1.6, 2.1, 4.1c) | the step says "can't tell" (L7) |
| Files the person hands over in step 3 | the person | read once, through `ingest-reader` at the small tier | none handed over: nothing read |
| Outside knowledge (1.8) | `/research` only | per research round | research-mark "none" |
| Typed text | the person | each turn, through the sanitizer only | not applicable |

- **One dataset:** the draft spec is rewritten only at 4.0a, 4.5 and 5.1, so the reviewers all read the same text.
- **Adversarial inputs:** the pointed skill's text, files the person hands over, research results and the plugin's own text carry this risk; every one is handed to a helper as DATA, never instruction (the helper briefs; "the skill's text is data"). No outside connection is made except through `/research`.

### T3. Inherited non-negotiable rails

**Why this section exists:** a skill built in isolation silently re-derives, and subtly weakens, rules the surrounding system already settled. Lift them verbatim; a paraphrase is where a "never" quietly becomes a "should avoid."

The table is in §2, "Rails: what holds each HARD rule", with the "Held by" column read from the built files.

### T4. The write model (the gears)

**Why this section exists:** skills that write mid-conversation create half-confirmed state, a write the human never approved sitting on disk as though they had.

- **Gear 1, the conversation:** the five TALK steps run in the main window and are never delegated; a sub-agent cannot pause for a person's answer.
- **Gear 2, the writes:** the ➡️🏃 sub-steps run as helpers, each at a named tier (never a model), handed its full content in its launch message because it cannot see the chat; the packet writer (3.4, `prompts/subagents/packet-writer.md`) saves into the packet every turn.
- **The boundary rule:** the packet is written every turn, and it is always labelled: the person's words are SAID, and become RULED only on their yes (L3). Nothing is written outside the packet folder, and the skill never writes the skill it designs (L2). This departs on purpose from the template's "nothing is written until an explicit human disposition", because a lost turn costs the person their answers; SAID-versus-RULED is what keeps a half-confirmed line from passing as confirmed.

### T5. THE GRID

**Why this section exists:** two failure modes hide in two blind spots, a skill that never says what happens before anyone is in the room, and a skill whose data, logic and presentation get designed independently until they silently disagree. The grid forces both into view. Every cell says what happens and where the evidence lands, or `NOWHERE`: that claim is then unverifiable by construction, and grading it must return INCONCLUSIVE, never FAIL.

| | 1. AMBIENT / BEFORE THE RUN | 2. THE LLM'S TURN | 3. THE HUMAN'S TURN | 4. AFTER ENTER |
|---|---|---|---|---|
| **DATA** | not active: no scheduled run, no tile. Only prior-run residue: an earlier packet on a resume. Evidence: the packet folder | reads the scratchpad sections the sub-step needs (`inputs_check.py`), the packet, the plugin's rules. Evidence: its exit code, the packet | surfaces the outline, steps, findings or readout to decide on. Evidence: NOWHERE (the transcript only) | the person's words saved as SAID; step outputs written. Evidence: packet files, `out/step-N.md`, `record.jsonl` |
| **BUSINESS LOGIC** | not active: no scheduled run, no tile | fixed choices read by `gates.py`; the figure by `completion.py`; citations by `citation_check.py`; checkers verify before anything is shown. Evidence: exit codes, the `*-checked` sections | one decision from a fixed set ending `none-of-these`, or an open answer. Evidence: SAID in the packet | the runner checks the step's file on `/next` (headings, words, code word); a failed check refuses, exit 3. Evidence: `record.jsonl` |
| **PRESENTATION** | not active: no scheduled run, no tile | the house style's screen A, B or Block C; the bar; the standing line. Evidence: NOWHERE (the transcript only) | the screen they decide on, with `/next` and `/back` beside the standing line. Evidence: NOWHERE | the mover's hand-over text for the next step, starting with the full-prompt path and the code word; the status line `RUN n/N`. Evidence: the hook log, `record.jsonl` |

**⟳ The iteration question.**
- **Unit of iteration, and how often:** one round inside a step: step 1 rounds until "yes, that's it"; step 2 two steps per screen; step 3 until `/next`; step 4 batches of up to six findings. The count is the person's choice, not fixed.
- **What carries across rounds:** the packet (SAID, rulings, research, the steps draft, the step-prompt drafts), the stale marks, the completion figure.
- **What is cleared between rounds:** only the `status` section, which is rewritten when a helper waits or stops; every other section is overwritten by its own writer on a repeat, and after a `/back` the sections from the landed step on are marked stale, never deleted (§4, Going back) [inferred]. Whether the other sections are cleared on a repeat is not built or tested.
- **Resumable, and what marks a round complete:** yes; the runner's record says which step passed, and the person's typed `/next` is the only mark of completion; run pickup resumes at the step the run was on (SKILL.md "If it stops early").

### T6. The step chain

**Why this section exists:** a skill that sees its own ending too early rushes toward it, pre-writing the conclusion it should have mined from the human. A blind chain is the structural fix; a prose reminder is not.

**T6a. What a step is, and its kind.** This spec's step is a point where the run stops and waits; its sub-steps are the template's "steps" (one unit of human attention each). Kinds: step 1 ROUND-REPEATABLE; step 2 CORRECTION-LOOP (it converges on the agreed steps); step 3 ROUND-REPEATABLE; step 4: 4.3 ROUND-REPEATABLE (batches of six), 4.5–4.6 CORRECTION-LOOP; step 5 ONE-PASS with a correction loop (5.6). For each ROUND-REPEATABLE step: **the offer, verbatim** is the standing line, "keep discussing this round, or ready to move on?" with a recommendation (L24); **the per-round yield** is a clearer outcome (1), a more complete acted-out skill (3), the next six findings (4.3); **the exit backstop** is none by ruling, since the person's `/next` is the only exit and there is no fixed time limit; **what carries** is the packet (above).

**T6a-0. The prescription budget.** The owner locked the HARD level and only the person may change it (§2). Read against the template's three carve-out classes (security invariants, human-elimination gates, loss-prevention gates): L3, L21, L22 and L27 are human-elimination gates (only the person settles a line, moves a step, accepts what is acted, chooses where it is filed); L7 and L8 are the invisible-violation kind (an invented tool or an outside source cannot be seen by the person). L1, L2, L4, L5, L9, L10, L14, L18, L19, L20, L23, L24 and L25 fall outside the three classes, so they read as guidance carrying their reason, and the reason lives beside the R-number in the owner's private rulings record (not shipped). The level stays the owner's call.

**T6b. Each step's one desired outcome, and when it is done:**

| Step | Desired outcome | Done when (the runner's check on its output file) |
|---|---|---|
| 1 What you want | the person's outcome is framed at the highest altitude and they said "yes, that's it"; the harness check and the size sense are in | `out/step-1.md` has `## Outcome`, `## Harness check`, `## Size sense`, at least 60 words, the code word |
| 2 The proposed steps | the skill's steps are agreed, each with its outcome, and the count says command or skill | `## Steps draft`, `## Step count`, at least 80 words, the code word |
| 3 Role-play it (optional) | the skill is acted out by hand and the person's reactions are recorded | `## Done by hand`, `## Answers`, at least 40 words, the code word; a skip is the person's own `/next` |
| 4 Shake the tree (optional) | the findings are ruled on and the spec is validated | `## Rulings`, `## Validation`, at least 40 words, the code word; a skip likewise |
| 5 The hand-off | the readout is confirmed, who it is for is answered, and the spec and packet are handed on | `## Parts result`, `## Draft check`, `## Destination`, at least 60 words, the code word |

- **Chain shape:** five steps, linear, with steps 3 and 4 skippable and `/back` loops (4.4, 5.6).
- **Blind-chain rule:** each step prompt is handed over only at the start of its step; steps 4 and 5 read step 2's output, so a skip never strands them (`card.json`). A reviewer reads the spec blind of the others' findings (4.1a).
- **Injection layers:** L1 identity anchor: null. L2 position: the bar's first line each reply and the runner's status line. L3 the step driver: `prompts/step-N-*.md`, loaded once at entry and not re-injected.

**T6c. The person's turn.** The template's three labelled fields are not labelled as such in the step prompts; the content is carried by each ⑂ line, the house style's question block and the standing line:

| TALK sub-step | What they are deciding | What only they contribute | A valid response |
|---|---|---|---|
| 1.4 | the outcome, and whether to refine, point at a skill or move on | what they want the skill to do for them | the `rounds-step1` set, or open words |
| 2.1 | whether the steps are right | what their days actually look like | the `roleplay-skip` set, or open words |
| 3.1 | whether the acted skill feels right | their reactions as the user | the `roleplay` set, or open words |
| 4.0, 4.3, 4.6 | what to decide now, which findings to accept, whether to fill gaps | the rulings only they can make | the `prep-report`, `findings` and `validation` sets |
| 5.0, 5.3 | whether to run the parts round, who it is for, whether to send | the destination and the final yes | the `parts-round`, `audience`, `send` and `destination` sets |
| 5.5 | nothing: leader mode, no question | nothing: it ends the run | none |

Long operations are bracketed: step 4 says plainly what is running while the reviewers work and reports after (`prompts/step-4-shake-the-tree.md` section 6); step 5 opens with the house style's still-finishing line when step 4's final check is not yet in.

### T7. Write targets (exact)

**Why this section exists:** "it writes the result somewhere" is the sentence that becomes a bug three weeks later when two writers touch the same file with different assumptions.

| What → where (exact path) | Written by | Guard |
|---|---|---|
| The packet folder: `<project>/packet/` when the person names a project or /build created one, otherwise `<brain>/drafts/builds/<skill-name>/`; always a folder | 1.1 opens it; the packet writer (3.4) saves into it every turn | `citation_check.py` (a cited path exists); the SAID-first rule |
| Scratchpad sections → `<packet>/scratchpad/<section>.md` | the sub-step named for each section in §5 | `inputs_check.py` (present only if the file exists and is not empty) |
| The findings document → `<packet>/research.md` | every helper, as it happens | the helper's finish signal; checked where used |
| The draft spec → `<packet>/draft-spec.md` | the spec-updater (4.0a, 4.5) and the compiler (5.1) | `checker-spec-update.md`, `checker-draft-spec.md`; `completion.py` reads it, never writes it |
| The run folder → `<packet>/runs/<run id>/` (`record.jsonl`, `out/step-1.md` … `out/step-5.md`, `stage/`, the marker) | `stage_runner.py` writes the record and stage files; the model writes only `out/step-N.md` | the hash-chained record, re-verified on every read; the card's checks on each out file |
| The hand-off → the destination: `handoff-note` with the draft spec on top, plus a link to the packet folder, never a copy | the hand-off note helper (5.4) | none by ruling; the planner AI's own vetting |
| The skill being designed → `~/.claude/skills/<name>/` (for me) or the plugin repo on a branch (for everyone) | not this skill: the plan's final step, after the person's "who is it for?" | the GitHub SOP §0c; never held here (L27) |

Not written, on purpose: `records/` (the packet stays in its folder as the record), a journal ledger row, the diary, a status tile (G13, deferred), and `canon/components/` (the build never writes canon).

### T8. Definition of done

**Why this section exists:** "the skill works" is not falsifiable.

- Every file in the T0 map exists: BUILT, checked against disk 2026-11-24 (files table above).
- The structural gates pass: THE GATE above, every item closed, deferred with a reason, or open with an owner.
- A dry run on synthetic input: the planted bad inputs and the unit tests run on synthetic input; the live runner check ran a scratch run outside the plugin.
- **Not done until the proving run:** by the owner's ruling (2026-11-24) there is no real-job trial. Done means every automated test passes: the routing eval on the final commit, the live runner check, the planted inputs, the no-personal-info checks. The filed page states the claim scoped: not tried on a real job; fixed in use.

### T9. Graceful degradation

**Why this section exists:** a skill that hard-stops when its ideal input is missing trains the human to avoid running it rather than to trust it.

Null, with its reason: this skill has no tiered inputs, so the template's cascade, confidence tiers and coverage stamp do not apply. The nearest behaviour is a direct start from empty blanks (1.1), and a line the person has not confirmed ends `[inferred]` or `[hypothesis]` (L3), which the completion figure does not count as done.

### T10. Session scratchpad and scribe

**Why this section exists:** a long run that dies mid-way with no persisted state forces a restart, including re-asking the human everything they already answered.

- **Location:** `<packet>/scratchpad/<section>.md`, keyed by the skill being designed (the packet folder), so two designs never collide; two runs on the same design would share it [inferred].
- **Contents:** one file per section, overwritten by its writer, not append-only [inferred]; the SAID log and the findings are kept in the packet.
- **Who persists it, when:** the packet writer (3.4, tier medium) every turn; the main session at each step boundary.
- **Resume:** run pickup resumes the run at its step; the runner's record marks which steps passed; the person can continue, snooze or start over.
- **Deletion:** none: the packet stays as the record and nothing in the skill deletes it.

### T11. Evidence surface and enforceability tagging

**Why this section exists:** grading a rule against the wrong evidence, or against none, produces a false miss that looks like a skill defect when it is a measurement defect. Tagging at design time lets a later reviewer tell "the skill broke this rule" from "this rule was never checkable from here."

| Rule | Evidence surface | Enforceability class |
|---|---|---|
| Only the person's `/next` or `/back` moves a step (L21) | the hook log, `record.jsonl`, the guard's denial | enforceable |
| A step's output file has its headings, words and the code word | `record.jsonl` | enforceable (as to presence only; substance is declared uncheckable by the runner) |
| Fixed answer sets end in `none-of-these`, which never moves the run | `gates.py` exit code | enforceable |
| The completion figure is computed by code (L17) | `completion.py` output | enforceable |
| Cited packet paths exist (L7, in part) | `citation_check.py` exit code | enforceable |
| A step prompt has the template's sections (L20, L23) | `prompt_sections.py` exit code | enforceable |
| Nothing a helper made reaches the person before its checker has passed it (L11) | the `*-checked` scratchpad sections | enforceable as to the section existing; human_in_the_loop as to the check being any good |
| At most four questions a round; the standing line ends every reply (L16, L24) | the transcript | enforceable by a reader of the transcript; no gate exists |
| The screens are clear to a beginner (L23) | the rendered screen | human_in_the_loop (needs human capability) |
| Honest acting: nothing made up is presented as real (L22) | the transcript | human_in_the_loop (blind to outcome); never hard-gated |
| Never rushes to a solution (L1) | the transcript | human_in_the_loop |
| Only the person's yes settles a line (L3) | the SAID and RULED marks in the packet | human_in_the_loop (a machine sees the mark, not the yes) |
| The hand-off sends the spec on top with the whole packet (L6) | the hand-off note and the packet folder | uncheckable-from-artifact (no receipt from the receiver) |
| The skill is pleasant to use over months | NOWHERE | uncheckable-from-artifact (the loop does not close within a run) |

The fresh-window proof (§7) therefore returns INCONCLUSIVE, never FAIL, for the human_in_the_loop and uncheckable-from-artifact rows.

## COMPONENT-PAGE FIELDS (Part B of `system/templates/component-page-template.md`, finish pass 2026-11-24)

The front matter at the top of this file carries Part B's keys (`component`, `title`, `state: spec`, `id`, `scope`, `shared`, `checks`, `receipts`, `health`). The generated fences below stay empty: the generator and the stamper fill them, and a hand edit inside a fence is overwritten and reported.

### The person's workflow
There are three elements, the code, the AI and the person. This is the person's side. They type `/skill-builder`, say in their own words what they want a skill to do for them, or point at a skill they already have. They answer one question at a time, at the highest altitude first; every reply ends with the bar, the standing line and `/next` and `/back`. They type `/next` to go on and `/back` to go back one step; they skip step 3 or step 4 by typing `/next`. In step 2 they read an overview, then two steps per screen, and correct as they go. In step 3 they react to the skill acted out. In step 4 they rule on findings six at a time. In step 5 they read the readout, say who the skill is for, and type `/next` to hand it over; the last screen tells them the run is complete. They never fill in a form and never move a step by speaking. Only the person says "yes, that's it", moves a step, chooses where the skill is filed, and decides to build.

### Where each Part B section lives in this spec

| Part B section | Where here |
|---|---|
| Words used | the "Words." paragraph at the top |
| ▲ 10,000 ft: Purpose/Responsibility, items 1–9 | §1 (desired outcome, the game, what it saves, what it is not); the three intelligences: code is the runner, `gates.py`, `completion.py` and the checks; the AI is the interview, the acting and the helpers; the person is the yes, `/next` and `/back` |
| ▲ 5,000 ft: combinations, chain, parts, seats, when the person is called, how it fails | the chain: §4; the parts: the §11 tables and the files table above; the seam where the AI hands back to code is the person's typed choice read by `gates.py` from a closed set; when the person is called and how a failure shows ("failed → stopped: <reason>"): §4 and the person's workflow above |
| Interface(s) | below |
| Inside (whitebox) | §4 (the chain) and §11 (the parts) |
| Quality characteristics | the `checks` ids in the front matter, each with what it watches |
| Ground: G0 roots and shared tools | the runner, the hooks, `ingest-reader`, `/research` and the project-manager skill are used from the shared layer and never copied; the five scripts are skill-local, and no shared tool covered them, so they have no register rows (BUILD-NOTES "Code (P5)") |
| Ground: G1…Gn, one per part | the files table above, each BUILT and checked against disk 2026-11-24 |
| Directory/file location | the fence below |
| What is tested and what is still to prove | §7 and THE GATE |
| Status | the fence below |
| Decisions (the person's) | DECISIONS; Fulfilled requirements: null, filled after the flip |
| Open decisions; Open issues | §8; Known pointers: null, no ledger line is named on this page; the delta reading is generated after the flip |
| Out of scope | §1 "What it is NOT", each line with its ruling |
| Rulebook updates this creates | ROUTED NOTES: they go to the debt ledger and the canon window, never into canon directly |
| Shared ownership | "THE BUILT SKILL" above |
| Pointed at by | the fence below |

**Interface(s)**, each seam to another part:

| Seam | What crosses, which way | Carried by |
|---|---|---|
| /build | a hand-over in at 1.1; a too-big skill out ("take-it") | a prompt hand-off with the packet |
| The shared step runner | the step prompt and code word out; the person's `/next` and `/back` in | `system/hooks/run_step_hook.sh`, `system/parts/stage_runner.py` |
| The tool builder | a message per owed part out (only when it exists; otherwise deferred work) | `tool-builder-handoff.md`, then a prompt hand-off |
| /research | the research round at 1.8 | the research skill |
| The project-manager skill | a link to the packet; brief notes written only through it | the packet path |
| /autoplan | the draft spec on top, plus the whole packet | `handoff-note.md` and the packet folder |

**Ground completeness check** (ticked 2026-11-24; anything unticked is a gap):
- [x] every part in the files table has its own row (the files table above);
- [ ] every interface shows its exact call: the hand-offs to the tool builder and to /build are written as messages, but the tool builder does not exist, so its exact call is not fixed;
- [x] every command a person or a session runs is named with its arguments: `/skill-builder`, `/next`, `/back`; the scripts' usage lines in their docstrings;
- [x] every file the system reads or writes has its format spelled out: `card.json` (its fields and headings), the scratchpad layout (§5), `out/step-N.md` (the card's headings); the section contents are in each step prompt's sections 5 and 6;
- [x] every NEW or CHANGES item has a real path: nothing here is NEW; the one CHANGES is the runner's first injected line (`system/hooks/run_step_hook.sh`, commit 52e4dca6);
- [x] nothing says "to be decided", "TBD" or "later" without a pointer: G3 and G20 are open with an owner, G13 and G14 are deferred with a reason (THE GATE).

### Directory/file location
*(born)* fills when built.
<!-- AS-BUILT:BEGIN generator=system/tools/organism/component_page.py source=origin/V2@07254c4 fetched=2026-11-24T18:58:42Z sha256=b906e0d5f570aaa8ea061d05038805e93939e65609e161cd508205a8e629fd68 -->
As built from origin `origin/V2` (@07254c4):

| kind | path | commit |
| --- | --- | --- |
| file | .claude/skills/skill-builder/BUILD-NOTES.md | 07254c40 2026-11-24 |
| file | .claude/skills/skill-builder/SKILL.md | e1efb89c 2026-11-24 |
| file | .claude/skills/skill-builder/card.json | 68a70b32 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/README.md | 68a70b32 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/step-1-what-you-want.md | 01d4e545 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/step-2-the-proposed-steps.md | 01d4e545 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/step-3-role-play-it.md | 01d4e545 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/step-4-shake-the-tree.md | 01d4e545 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/step-5-the-hand-off.md | 01d4e545 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/README.md | 68a70b32 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/checker-base.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/checker-draft-spec.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/checker-harness-findings.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/checker-heal.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/checker-skill-reading.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/checker-spec-update.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/checker-step-prompts.md | 5e090fe4 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/compiler.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/handoff-note.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/harness-search.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/healer.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/packet-writer.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/research-mark.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/research-pass-item.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/reviewer-base.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/reviewer-logic.md | de673f53 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/reviewer-order.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/reviewer-saving.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/reviewer-screens.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/rulebook-proposer.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/size-sense.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/skill-reader.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/spec-updater.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/step-prompt-drafter.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/tensions-checker.md | c38a5373 2026-11-24 |
| file | .claude/skills/skill-builder/prompts/subagents/tool-builder-handoff.md | 5e090fe4 2026-11-24 |
| file | .claude/skills/skill-builder/references/README.md | 68a70b32 2026-11-24 |
| file | .claude/skills/skill-builder/references/examples/README.md | 68a70b32 2026-11-24 |
| file | .claude/skills/skill-builder/references/opening-screen.md | 68a70b32 2026-11-24 |
| file | .claude/skills/skill-builder/routing-eval.md | e1efb89c 2026-11-24 |
| file | .claude/skills/skill-builder/scripts/README.md | 68a70b32 2026-11-24 |
| file | .claude/skills/skill-builder/scripts/citation_check.py | 5e090fe4 2026-11-24 |
| file | .claude/skills/skill-builder/scripts/completion.py | 5e090fe4 2026-11-24 |
| file | .claude/skills/skill-builder/scripts/gates.py | 5e090fe4 2026-11-24 |
| file | .claude/skills/skill-builder/scripts/inputs_check.py | 5e090fe4 2026-11-24 |
| file | .claude/skills/skill-builder/scripts/prompt_sections.py | 5e090fe4 2026-11-24 |
| test | .claude/skills/skill-builder/scripts/tests/test_citation_check.py | 5e090fe4 2026-11-24 |
| test | .claude/skills/skill-builder/scripts/tests/test_completion.py | 43af4beb 2026-11-24 |
| test | .claude/skills/skill-builder/scripts/tests/test_gates.py | 5e090fe4 2026-11-24 |
| test | .claude/skills/skill-builder/scripts/tests/test_inputs_check.py | 5e090fe4 2026-11-24 |
| test | .claude/skills/skill-builder/scripts/tests/test_prompt_sections.py | 5e090fe4 2026-11-24 |

Hook wiring (from origin `hooks/hooks.json`):

(none)

Register rows in scope (from origin `system/register/register.jsonl`):

| id | path | type | sha |
| --- | --- | --- | --- |
| skill:public:/.claude/skills/skill-builder/SKILL.md | /.claude/skills/skill-builder/SKILL.md | skill | fecf1c7c |
in scope, unregistered: `.claude/skills/skill-builder/scripts/citation_check.py`
in scope, unregistered: `.claude/skills/skill-builder/scripts/completion.py`
in scope, unregistered: `.claude/skills/skill-builder/scripts/gates.py`
in scope, unregistered: `.claude/skills/skill-builder/scripts/inputs_check.py`
in scope, unregistered: `.claude/skills/skill-builder/scripts/prompt_sections.py`

Pointers:

named but missing: `/skill-builder` ⛔ not on origin
named but missing: `prompts/` ⛔ not on origin
named but missing: `prompts/subagents/` ⛔ not on origin
named but missing: `/next` ⛔ not on origin
named but missing: `/back` ⛔ not on origin
named but missing: `prompts/step-1-what-you-want.md` ⛔ not on origin
named but missing: `prompts/step-3-role-play-it.md` ⛔ not on origin
named but missing: `prompts/step-5-the-hand-off.md` ⛔ not on origin
named but missing: `prompts/subagents/healer.md` ⛔ not on origin
named but missing: `prompts/subagents/checker-heal.md` ⛔ not on origin
named but missing: `prompts/subagents/packet-writer.md` ⛔ not on origin
named but missing: `scripts/completion.py` ⛔ not on origin
named but missing: `references/opening-screen.md` ⛔ not on origin
named but missing: `prompts/step-2-the-proposed-steps.md` ⛔ not on origin
named but missing: `prompts/step-N-*.md` ⛔ not on origin
named but missing: `scripts/citation_check.py` ⛔ not on origin
named but missing: `/` ⛔ not on origin
named but missing: `prompts/subagents/harness-search.md` ⛔ not on origin
named but missing: `scripts/gates.py` ⛔ not on origin
named but missing: `prompts/subagents/checker-base.md` ⛔ not on origin
named but missing: `prompts/step-4-shake-the-tree.md` ⛔ not on origin
named but missing: `scripts/prompt_sections.py` ⛔ not on origin
named but missing: `prompts/subagents/reviewer-screens.md` ⛔ not on origin
named but missing: `prompts/subagents/handoff-note.md` ⛔ not on origin
named but missing: `prompts/subagents/step-prompt-drafter.md` ⛔ not on origin
named but missing: `prompts/subagents/tool-builder-handoff.md` ⛔ not on origin
named but missing: `scripts/inputs_check.py` ⛔ not on origin
named but missing: `prompts/step-1…5` ⛔ not on origin
named but missing: `references/examples/` ⛔ not on origin
named but missing: `prompts/step-1-check-the-compass.md` ⛔ not on origin
named but missing: `planning-weekly/prompts/subagents/` ⛔ not on origin
named but missing: `prompts/README.md` ⛔ not on origin
named but missing: `scripts/tests/test_*.py` ⛔ not on origin
named but missing: `scripts/README.md` ⛔ not on origin
named but missing: `references/README.md` ⛔ not on origin
named but missing: `references/examples/README.md` ⛔ not on origin
named but missing: `scripts/tests/` ⛔ not on origin
named but missing: `/research` ⛔ not on origin
named but missing: `out/step-N.md` ⛔ not on origin
named but missing: `out/step-1.md` ⛔ not on origin
named but missing: `out/step-5.md` ⛔ not on origin
named but missing: `stage/` ⛔ not on origin
named but missing: `records/` ⛔ not on origin
named but missing: `/build` ⛔ not on origin
named but missing: `out/step-2.md` ⛔ not on origin
named but missing: `professor/routing-eval.md:38` ⛔ not on origin

not on origin: 0

pointed at by: none
<!-- AS-BUILT:END -->

### Status
*(born)* fills when built: the status label is stamped by a real check, never typed.
Suffix (human-owned): ·gap
<!-- STATUS:BEGIN stamper=system/tools/organism/component_page.py stamped=2026-11-24T18:58:42Z sha256=663ed536094f7e49eef24ea02c59ce844bfd1b04f8c3316c108cd3f8afbb09f7 -->
Status: unproven (receipt missing) · checked unknown · valid until unknown · <brain>/status/component-skill-builder.json
Past "valid until", read this as unproven, whatever the word says.
Health: no tile declared

| check | watches | result | date | at sha | clean | window | receipt | untested | reading |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| skill-unit-tests | the five scripts do what their docstrings say: every test passes (`python3 -m unittest discover -s scripts/tests`, 62) | — | — | — | — | — | <brain>/status/component-skill-builder.json | — | unproven (receipt missing) |
| runner-live-check | only the person's typed /next or /back moves a step; a session cannot move a talk step; plain words move nothing (live check, BUILD-NOTES) | — | — | — | — | — | <brain>/status/component-skill-builder.json | — | unproven (receipt missing) |
| planted-bad-inputs | each AI checker refuses or reports one planted fault and none passes it silently (8 of 8, BUILD-NOTES) | — | — | — | — | — | <brain>/status/component-skill-builder.json | — | unproven (receipt missing) |
| prompt-quiz | a blind reader understands each prompt whose meaning changed (6 of 6 each, BUILD-NOTES) | — | — | — | — | — | <brain>/status/component-skill-builder.json | — | unproven (receipt missing) |
| routing-eval | the skill starts on the S cases and never on the N cases (routing-eval.md; pending on the final commit) | — | — | — | — | — | <brain>/status/component-skill-builder.json | — | unproven (receipt missing) |
<!-- STATUS:END -->

### Pointed at by
*(born)* fills when built.

## RESEARCH FOLDED IN

- **Telemetry** (the findings document, 2026-11-23, GLM read of V2 canon, key lines spot-checked in the files). Canon already says every producer leaves one tile at `<brain>/status/<producer>.json` (status-emission-sop.md:28, :132), but it is not yet true in practice (:57, :170). The envelope is fixed by the platform (:30; vision:296); the payload is the producer's own. Checkers emit receipts, never the checked (vision ~754; status-health-proof-sop.md:79). Three writes: evidence to records/, story to diary/, glance to status/ (vision ~291). Consequence for this spec: tile and envelope are always-true (pointer), the payload ("what tells you it worked") and the `stale_after_s` rhythm are the per-skill blanks (§10).
- **One-step edge cases** (the findings document, shell survey of 35 skills in the plugin's `.claude/skills`). Class "the switch": one step that turns something on that a hook keeps going (calculate, altitude, project-manager's staying-active flag, the personal /claude-cheap); the command is one step, the lasting behaviour is a part (supports L19). Class "steps with no pause": websearch has three step headings that run alone inside one turn, so they are sub-steps of one step (supports the step definition in Words).
- **Build items answerable by looking** (the research-for-build note, 2026-11-23, background research pass; every answer a draft to confirm in the build). (A) All five steps are TALK steps; the ALONE work is sub-steps inside them, so the Stop-hook handover for alone steps likely applies to nothing. (B) The runner ignored unknown card keys when read; optional steps have since been built (§8-1). (C) `/build` does not exist in the plugin yet; routing near-misses against it come from this spec's description. (D) No reusable hash-pin for skills; consume `stage_runner.py` in place, as planning-weekly does. Also drafted there: the scaffold from `system/templates/skill-template/` (the newer source), the frontmatter (quote the description: an unquoted `: ` breaks YAML), a routing-eval draft (S1–S8, N1–N6), a five-stage card draft (steps 4 and 5 read `out/step-2.md` so a skip cannot freeze them), the folder layout, and the open question of where the spec form lives plugin-side.

## DECISIONS

Every ruling, one line each: date · the decision · R-number. Full text and sources are in the owner's private rulings record (not shipped). "Superseded by Rn" means a later ruling replaced it. One duplicate line (the first of a duplicated pair) is skipped, as marked in that record.

- 2026-11-22 · The role is an interrogative process, an earnest detective and an honest witness: lead, don't follow, never one-shot, come with a guess, measure against the plugin (locked)
- 2026-11-22 · Play it back in plain words; only the person's "yes, that's it" moves things on
- 2026-11-22 · The build skill's decision tree is approved; the skill builder starts where it hands off (Stage 5 small, Stage 8 bigger)
- 2026-11-22 · Three sizes: component, skill, part, calling each other (superseded in part: count the steps, command or skill)
- 2026-11-22 · Role-playing mode is offered every round; it looks up harness rules and warns on non-conformance
- 2026-11-22 · Light enforcement: the human is a capable operator; no perfect code gate
- 2026-11-22 · Recency bias: no cues from v1 builds (excepting the old skill builder's flow)
- 2026-11-22 · Trust only the plugin, no carve-outs; the person's own setup is evidence until approved in
- 2026-11-22 · The person is unsophisticated and wants to be led; no small-build shortcut
- 2026-11-22 · The builders design, they do not build; nothing is built while the packet is filled
- 2026-11-22 · The question game: fewest, most leveraged questions, each with a best guess; the list is rebuilt every round
- 2026-11-22 · The model is lazy about asking; it looks for itself first and asks only what only the person knows (the "never ask what you can find out" form is a reading, L12)
- 2026-11-22 · Build order: the skill builder first, version one written by hand from the plan's forms
- 2026-11-23 · The skill builder is designed and built first; its first job is chosen when a parked project resumes; Grand Central stays paused
- 2026-11-23 · Dependency: the tested skills checklist comes from the canon update window once approved; pulled in by reference and gates only its build
- 2026-11-22 · The packet is approved: front page, draft spec, rulings, research, notes, checklists, landing spot; one file small, a folder big
- 2026-11-23 · COMPILE before the hand-off: only the draft spec goes to /autoplan; packet archived as backup and evidence (softened, then superseded: everything gathered goes, the spec on top)
- 2026-11-23 · The skill spec form and packet format are done and approved
- 2026-11-22 · The skill spec form is the old skill builder form updated with the planning-weekly improvements; it passed four blind tests
- 2026-11-23 · Write "the build skill", never "/build" (superseded: the command is /build)
- 2026-11-22 · Given an existing skill, the builder reverse-engineers its steps and gaps; the human sees "it looks like four or five steps"; fix the skill while using it
- 2026-11-22 · No second build pass: the build skill, then /autoplan, then a coordinator window
- 2026-11-22 · Phase 5d: play-act the skill builder on itself, filling its packet with the new form; it becomes the first finished example
- 2026-11-22 · The build skill fronts five skills: /research, /project-manager, plus the component, skill and part builders (part builder renamed tool builder)
- 2026-11-22 · The builders can call each other (superseded in scope: any direction)
- 2026-11-22 · On a small build research still runs when marked and is saved in the build's own notes; for a small part one window is fine
- 2026-11-22 · His words: the skill builder plays a Q&A game with the human in the loop, most leveraged questions first, until the spec sheet is fully built
- 2026-11-22 · His words: respect the human's time, fewest questions to fill all the data; the pain being avoided is fixing then running then finding it broken
- 2026-11-23 · Never make things up; leave it blank and list it as an open question
- 2026-11-23 · Nothing reaches the person unchecked: a separate check runs before anything a helper produced is shown
- 2026-11-23 · Round one: it is registered as /skill-builder, callable directly; choosing its jobs is the coordinator's business; no separate "done" step, done when the templates are filled; the session runs in a fresh window reporting to the build-skill window; the old form is updated, the old skill is legacy, version one is by hand (Door One) · (round one, no R-number)
- 2026-11-23 · Round two, presentation: a round screen must be much shorter ("simpler") · (round two, no R-number)
- 2026-11-22 · The cold start: open a session, invoke the skill builder, say what you want; or point at an existing skill and it reads it quietly and onboards
- 2026-11-22 · The main mode is approximating a run of the skill; the spec sheet is a scratchpad; learn while using
- 2026-11-22 · The end: "I think we've got the skill now, do you want to build it?"; handed on when decided or close enough
- 2026-11-22 · A folder of completed example skills; shipped examples are scrubbed of personal data
- 2026-11-22 · Moving UP a size: a task that turns out to be a subsystem invokes the component builder (covered by a later ruling: any direction)
- 2026-11-23 · A part it needs is not built by it: back to the project as deferred work, or kept in its own packet when invoked directly
- 2026-11-23 · Coming back later is parked, harness plumbing built by another window, not the skill builder's design
- 2026-11-23 · How he will know it works: a perfectly conformant skill with its own spec, wired into shared plumbing, spec in canon; pleasing to use over years
- 2026-11-23 · Take cues from the old skill builder's flow, minus the many visible steps; much happens in the background (settled)
- 2026-11-23 · The old flow is "exactly the flow" (outcome, steps, sub-steps, shake the tree), conversational, done by role-playing; at most four questions at the bottom; old build and live-run phases are out; settles an earlier open question
- 2026-11-23 · SHAKE THE TREE is kept, with the logic lens rewritten: AI handing back to code is a big potential breaking point
- 2026-11-23 · The hand-off goes back to the main project window or to /autoplan, most likely /autoplan
- 2026-11-23 · Correction: the skill builder is about making and writing the spec, not reading it
- 2026-11-23 · RESTART: codify everything so far and restart the play-act from step 1 in the agreed flow; rounds one to three stand as rulings
- 2026-11-23 · The opening screen is approved verbatim (`opening-screen.md`); the person then asks to build the skill builder itself
- 2026-11-23 · The outcome is the problem it solves: no more build-run-break-rebuild loops; the AI pretends the skill exists and the person iterates in real time
- 2026-11-23 · Onboarding that happens while using: use skills as they are, suggest harness improvements, take notes in the background, autoplan builds in one shot
- 2026-11-23 · Of the four questions, 1, 2, 4 answered; 3 (what breaks trust) not relevant yet
- 2026-11-23 · PRINCIPLE, parachute in: questions run high, medium, low; teach the harness while solutioning
- 2026-11-23 · THE GAME, two tracks: the person operates as if while being led; the AI fills the template without surfacing a huge list; old skill gets a new spec and is migrated
- 2026-11-23 · Pointing at an old skill, the old skill really runs inside a shell with telemetry-like notes; noted cost: background token use
- 2026-11-23 · What it saves: time and stress, which equal money
- 2026-11-23 · THE STATUS BAR at the bottom of every output: visual completion, three questions, a not-ready readout that the system also reads on close or save
- 2026-11-23 · Before pretending, it works out phases, steps and proofs, then offers to approximate the skill
- 2026-11-23 · SELF-HEALING: when the old skill breaks mid-run, a background sub-agent researches the fix and records it; flow-changing breaks come back to the person
- 2026-11-23 · HARNESS FIRST, always: look for what the harness already solves; the more used, the sharper the harness
- 2026-11-23 · Proofs stay; naming change proposed: big chunk = step, moves inside = sub-step (settled)
- 2026-11-23 · Naming settled: step (big chunk), sub-step (N.M)
- 2026-11-23 · ONE LIST: the spec is the checklist; decisions become questions, always-true rules come pre-filled by pointer, one-time testing stays with the build; telemetry in each skill
- 2026-11-23 · THE HIGHER GOAL: one form simple enough that a stateless LLM only has to fill it out; telemetry goes in the form too
- 2026-11-23 · His proposal: drop the three sizes; count steps (confirmed, then locked)
- 2026-11-23 · Yes to count the steps (one = command, two or more = skill); a switch command is only the trigger; a step is where the run stops and waits
- 2026-11-23 · Question: spec for small skills? His counter-argument adopted: every skill gets the one form, the step count is a switch inside it
- 2026-11-23 · LOCKED: the count-the-steps proposals, telemetry in the form, and the two new form sections, the step count as a switch inside the spec (plugs into Lifehack, keeps working)
- 2026-11-23 · Coordinator's points 1–4 accepted: shared code writes the status note, "on demand" rhythm choice, checklist change via a canon change card, glossary "step (in code: stage)"; point 5 to be solved, not debt-listed
- 2026-11-23 · The status-note folder move is handed to the V2 coordinator to do now in its own window; the spec points at canon's path
- 2026-11-23 · Two open questions delegated and solved: four questions a round are the status-bar questions (kept); the skill builder never hands work to another builder (part 2 superseded)
- 2026-11-23 · "It's just one set of questions"; builders call each other in ANY direction; supersedes part 2 of an earlier ruling
- 2026-11-23 · The status bar mockup is LOCKED; calls between builders are a prompt hand-off, not code enforcement; the skill builder gets its own decision tree
- 2026-11-23 · Decision tree draft 1: "Looks really good"; sent to the V2 coordinator for a second opinion
- 2026-11-23 · Transfer list: moving on only by typing `/next` or `/back`; his words saved first each turn; honest acting; coordinator and build windows after /autoplan are best practice only
- 2026-11-23 · Transfer list v2: day/week/month/year is one question; examples not shown to the person; the detective is the standing role; completion figure by code; hand-off reading list; front-page and checklist items held pending explanation (later settled)
- 2026-11-23 · Keep the documents few: cover sheet inside the spec; no "removing a step" rule (a rebuild goes through full autoplan and build); checklist rules pointed to, never copied
- 2026-11-23 · The coordinator's second-opinion fixes (backward moves only by `/back`; self-healing never edits the harness; stale wording; sandbox-only stated; the /build decision tree's work before a builder starts; SAID versus RULED) applied
- 2026-11-23 · Yes to fixes 1–4 and to 5 once explained; get back to running the approximation of the skill builder
- 2026-11-23 · His proposal: the five steps (what you want, proposed steps, role-play it, shake the tree, hand-off); "map it" gone
- 2026-11-23 · The five steps confirmed; too big: strongly recommend /build, never enforced; /build creates the project; one-step commands skip the critics
- 2026-11-23 · Step 3 as a medium-altitude walk-through, two at a time (corrected: that belongs to step 2)
- 2026-11-23 · Role-play step 1 "is really good"; step 2 not yet confirmed
- 2026-11-23 · Step 2 approved; role-play output rule: two or three super-leveraged questions under each step
- 2026-11-23 · Answers: every turn ends with a standard line and `/next` `/back`; launched inside a skill it asks which skill; too big defined; a needed part's design is left for a parts round before the hand-off; a rule-breaking step warns once; a step ends on `/next`
- 2026-11-23 · Step 2 has two parts (one overview screen; a walk-through two at a time at medium altitude); step 3 acts the skill out screen by screen (the first entry is a skipped duplicate)
- 2026-11-23 · Two steps per screen; overview is the first screen of step 2; step 3 runs until `/next`; real data by hand or ask before faking (squared)
- 2026-11-23 · In step 3 it can do anything possible in the system for real and by hand without lying about built machinery; supersedes sandbox-only
- 2026-11-23 · The play-back is correct; steps 2–3 walk-through validated
- 2026-11-23 · THE AUDIENCE (lowest common denominator, anxious, no busy work); step 4 explained as a red-team pass plus a fifth rulebook helper that ranks and proposes, at most six at a time; step 5 orients and says it is not built yet
- 2026-11-23 · The fifth reviewer proposes, never fills in; the person sees all proposals ordered by weight, at most six at a time; re-run after `/back` at the AI's judgment; two hand-offs (technical, on-screen)
- 2026-11-23 · The fifth-reviewer and hand-off design locked with one correction: findings are de-duplicated before the person sees them
- 2026-11-23 · Emoji key for the step walk-through: 🙋 You · 🤖 This session · a Sub-agent mark (still being chosen) · 🌙 Earlier + a word (still being chosen)
- 2026-11-23 · The Sub-agent mark: robot, arrow, runner (his pick; superseded)
- 2026-11-23 · First version: the runner did not render, fallback 🤖➡️🏃 (superseded by the second)
- 2026-11-23 · Second version: Sub-agent mark is just ➡️ 🏃 (supersedes the earlier ones)
- 2026-11-23 · Emoji key LOCKED: 🙋 You · 🤖 This session · ➡️🏃 Sub-agent · 🌙 Earlier machinery, each with its plain meaning
- 2026-11-23 · Step walk-through screen: three sections per step in order (This session, Your part, Sub-agents) as prose; three altitudes of reading
- 2026-11-23 · Walk-through LOCKED; 🌙 Earlier machinery ALWAYS shows, as a question when nothing is known
- 2026-11-23 · (a) naming (superseded: the command is /build); part builder renamed TOOL BUILDER; 🌙 Earlier machinery defined (anything pre-existing)
- 2026-11-23 · Skip the rest of step 2's walk-through and step 3 for this design run; the play-act moves to step 4
- 2026-11-23 · The emoji sections belong only to step 2's walk-through
- 2026-11-23 · Persist everything decided so far into the packet before step 4; accurate completion figure; step 4 opens with a short PREP REPORT
- 2026-11-23 · Decisions go to the rulings file during steps 1–3; the spec is brought up to date first in step 4 by a sub-agent plus a checker
- 2026-11-23 · One definitive emoji key across Lifehack is a debt-ledger task (sent to the V2 coordinator)
- 2026-11-23 · The five reviewers: the screens reviewer gets the audience; the saving reviewer looks for the fewest-token optimum; describe all five at least twice as long and say how the fifth works
- 2026-11-23 · Reviewer prompts: screens asks about the person's specific role; saving ends with the context-rot line; the proposer writes for the audience
- 2026-11-23 · The shake-the-tree recipe LOCKED: fixed and variable parts, readers use the full-read tool, no model choice (the harness routes models)
- 2026-11-23 · Step 4's findings screen shows up to six at a time
- 2026-11-23 · Findings 3–5 accepted; watching mode for improving an existing skill; after the step-4 response the builder re-validates completeness
- 2026-11-23 · Skipping is a plumbing issue sent to the V2 coordinator; he does not recognise the old L6; the packet is meant to pass along between builders
- 2026-11-23 · L6 softened: only the updated spec goes to /autoplan, with a pointer to everything else; the packet is filed as the record (superseded: the whole packet goes too, the spec on top)
- 2026-11-23 · No prescription on completeness; keep working inline while sub-agents run; the hand-off says the plan's final piece finishes the spec; the footer becomes a sliding scale
- 2026-11-23 · Watching mode not overprescribed; never fabricate data or machinery; the plan's final phase finishes the spec, promoted to `~/.claude/skills/<name>/`
- 2026-11-23 · On `/next` the screen moves on at once even while a check finishes, and says plainly what is going on
- 2026-11-23 · Checklist items sorted into three places in the same spec (asked now, always true by pointer, for the planner and the build); build/test-only items go to the third; his "Okay"
- 2026-11-23 · His principle: don't wait for /autoplan for anything research can answer; open items answerable by looking are researched by background sub-agents during the session
- 2026-11-23 · "We just go do this": a background pass drafts the build items answerable by looking into the research-for-build note; such research should have happened by the end of step 4, mainly around the fifth reviewer
- 2026-11-23 · Option A approved: four reviewers at once → a research pass (one small sub-agent per open item answerable by looking) → the rulebook proposer last, with the facts → the checker → the person, six at a time; the final check stays as a backstop
- 2026-11-23 · Every background finding, at any step, is saved to the packet's findings document as it happens; it need not be surfaced to the person (settled)
- 2026-11-23 · Recency bias in all research: the newer source wins (the skill template beats new-skill.sh)
- 2026-11-23 · Coordinator second opinion: spec plus findings to /autoplan (then pending his yes; settled: the whole packet goes); a vague "how do I make a skill" goes to /build; the skill template is the reference and new-skill.sh goes to the debt ledger; optional steps with him; the four form-audit proposals sent on · (coordinator, no R-number)
- 2026-11-23 · The research itself goes to /autoplan, not a tidied summary ("we paid for that"); the vague-question route to /build is correct
- 2026-11-23 · Confirmed (2); optional steps: "if number four is pretty easy to fix let's just do that" (since built, §8-1); the GLM fix saved; the four form-audit changes approved and sent on; skills belong in Claude's own skills folder, don't relitigate; the whole-packet question to explain (answered)
- 2026-11-23 · The skill builder is Lifehack plugin code; a person's skills go to their personal skills folder, with the owner's for-everyone exception, solved by canon's "who is this for?" asked once at the hand-off; routing follows the GitHub SOP §0c
- 2026-11-23 · STEP 5 IS LEADER MODE: no question section once the person is no longer doing the work; tell them plainly what happens next and what they do; everything gathered goes to the planner, the design on top, treated as settled
- 2026-11-23 · (a) The ending corrected: no extra stage after the build; the plan's final step sharpens and finalizes the draft spec and files the skill, for most people in ~/.claude/skills/<name>/. (b) An audience profile prompt is dropped in (made start-of-step)
- 2026-11-23 · Direction: a "Step prompts" section in the spec, at least one prompt per step injected at its top, plus the shared audience and detective prompts; grown through the session; the person kept out of the loop (every-turn part superseded)
- 2026-11-24 · The two shared prompts come only at the START OF EACH STEP, not every turn; every step fully reorients the person as if brand new
- 2026-11-24 · The prompt plan approved in its simple form: Opus writes; a fresh siloed GLM tester per instruction; a different AI grades against the desired outcome and traps; three tries; fix and retest; step instructions first, then helper briefs; small batches (superseded by the test-principle ruling below)
- 2026-11-24 · LOCKED: the house layout style (status bar, closing line, question rules, plain words) is written ONCE as a shared page every skill points to; the skill spec form is rebuilt now from this first finished example; templates are fill-in-the-blanks: a step prompt template per step and a sub-agent brief template per helper, with a test card
- 2026-11-24 · Templates are PRE-FILLED, not described: fixed text written in first, then a blank with its instruction inside it; general principles avoided
- 2026-11-24 · Belt and suspenders: every template both shows the filled shape and tells how inside each blank
- 2026-11-24 · Guaranteeing the prompts get used (step instructions code-delivered; briefs pasted in verbatim with an "extra for this run" box) handed to the V2 coordinator; wary of overbuild; not decided (ROUTED NOTES 20)
- 2026-11-24 · Track 1 test plan: fix step 3 and the 12 failing briefs, a reusable test kit, retest the 13 changed, anything still failing marked "shaky" and not blocking (superseded by the test-principle ruling below)
- 2026-11-24 · Form v2 choices: (1) one-step commands show no /next·/back line; (2) every question carries the AI's recommendation, how confident it is and how load-bearing the decision is; (3) every new skill starts blank, never referencing an old skill (its own D1, D2… list is fine); (4) the rerun-after-/back and unattended-run rules are removed from the general form
- 2026-11-24 · Track 2 test kept light: one GLM cold fill of the finished form for a simple new skill, read by the main window, no separate grader
- 2026-11-24 · TEST PRINCIPLE: a prompt test is a comprehension check (multiple-choice questions a blind AI answers from the prompt alone), never a simulated full run; rounds already run are parsed for the useful part only (supersedes the earlier prompt-plan and Track 1 test-plan rulings)
- 2026-11-24 · The front door's command is /build; there is no /build-skill (supersedes the earlier naming)
- 2026-11-24 · No more prompt testing: the quiz (158/162) and the three fixes are enough; re-quiz only a prompt that changes later

## ROUTED NOTES (for the main window to send)

From the packet's notes and the rulings. Folded into the design: the cold start and the approximation mode, the tile/telemetry findings (§10, RESEARCH), the checklist's runner facts (§4 and §8-1: use the shared runner's `/next` and `/back`, never its own), the status line versus reply bar tension (settled, §8-2), the one-list and one-form outcome, the "step (in code: stage)" glossary line (Words), and the skipping decision (§4). Routed, with where each should go:

1. Status lights written by shared code (the tile writer for skills and one-step commands, "not built yet", status-emission-sop:170) · debt ledger (root §9; he deferred it) · main window.
2. Optional steps in the shared runner (card field `optional`, pass recorded "skipped by the person", about 20 lines, 2 tests), recommended yes for run pickup · LANDED: built by run pickup (commit e9632fbb) and read back on origin/V2 2026-11-24 (§8-1, closed).
3. One definitive emoji key with names, persisted across Lifehack · debt ledger (sent to the V2 coordinator).
4. Changing the skills checklist (count the steps; "stage" brought in line with "step") · a canon change card through the canon window; never edited in place · another window.
5. Skill spec form edits: "step-group" to "step" and "step" to "sub-step"; the two new sections (§9, §10); the rhythm "on demand" choice; cover sheet and DECISIONS sections; the form-audit proposals (a "builder decides" class, a "finish after the build" pass, a "needs platform change" register, shared rules as a standard block, §8 hygiene and a ready test matching the skip ruling, §7 as a standard block, optional trust and time-horizon questions, a ruling-scope check, a "filed publicly" note in §6) · the form's owner, via main window.
6. The /build decision tree (three sizes superseded) and the earlier plan wording (sizing; part builder is now the tool builder), recorded as superseded, not edited away · build-skill window, needs his word there.
7. Coming back later, the picking-up plumbing · harness plumbing, another window is building it and may message this window.
8. Skipping (issue #1 of the findings) is plumbing · V2 coordinator (already sent); the skip is the person's own `/next` (§4).
9. ~~Status-note folder move (state/status/ to canon's status/): built in a build window, committed, push pending; then drop the temporary "writer still writes state/status/" note in §10 · project brief once pushed.~~ DONE: on origin/V2 (affa2be5), §10 note dropped, 2026-11-24.
10. The build skill "listening" mode that notices a skill is really a bigger system · build-skill window (SOP candidate or project brief).
11. SOP candidates: the standing every-turn closing line with `/next` `/back` (L24), shared and built into every skill; "a skip is the person's own `/next` on an optional step"; "the screen never stalls on a helper" (L25) · SOP candidates list.
12. Self-healing as a mode of the build skill itself · build-skill window.
13. Lasting project notes: the vocabulary (step, sub-step, command, skill), the one-form principle, "no side quests" withdrawn (a note to the coordinator, not a rule) · project brief.
14. Professor's routing line (`professor/routing-eval.md:38`) should point a vague "how do I make a skill" to /build (coordinator opinion 2, confirmed by him) · a professor change, via main window.
15. The packet format's compile: everything gathered goes to /autoplan, the design on top, replacing "only the draft spec" (the earlier wording) · the format's owner.
16. `system/tools/new-skill.sh` (older than the skill template): retire or repoint · debt ledger.
17. The shake-the-tree recipe: write in the research pass between the four reviewers and the proposer (approved: "to go into the spec and the shake-the-tree recipe") · LANDED: the recipe now carries the research pass and the comprehension quiz, which covers the step-prompt cold read (§8-3, closed; no added reader line) · the recipe's owner (this packet until it moves into the plugin).
18. The skill spec form gains a STEP PROMPTS section, and the four form-audit changes he approved (already sent) · the form's owner.
19. The rulings record's hygiene: one duplicated entry and two lines carrying the same ruling twice, an early front-page line (superseded by a later ruling) and a line still marked "under discussion", the early "only the spec" lines (superseded by later rulings) · whoever keeps the rulings record; marked superseded, never deleted.
20. Guaranteeing the prompts get used (step instructions code-delivered; sub-agent briefs pasted in verbatim with an "extra for this run" box), wary of overbuild · NOT DECIDED; with the V2 coordinator.

## FOR THE PLANNER AND THE BUILD

**Open items for /autoplan and the build to fill, with the person where needed.** They are build and test items, not design. They do NOT count against the completion figure. They are closed by the finish-after-build pass.

**THE GATE (coordinator, 2026-11-23).** This section closes by a gate, not by goodwill. Every item below must be closed, or deferred by the person with a reason, as part of the build's DONE MEANS and as phases of /autoplan's plan. The skill's component page cannot get its stamped status until this section is empty. The 5.4 hand-off note says so, and so does 5.5's on-screen readout.

**Status at 2026-11-24 (finish pass).** Every item below is closed with its record (a section of the skill's `BUILD-NOTES.md`), or deferred with a reason, or open with an owner. "Drafted" answers in the research-for-build note were confirmed in the build, not re-researched.

| Gate | Item | Status | Record or reason |
|---|---|---|---|
| G1 | Scaffold the skill's folders from `system/templates/skill-template/` | closed | BUILD-NOTES "Records block (P2)" (departures from the template, one line each); every folder has a one-line purpose README; no `{…}` or guidance comment is left in the skill's own pages (a grep, 2026-11-24) |
| G2 | The frontmatter lines (name, description, trigger words) | closed | `SKILL.md` frontmatter; the description starts "(NOT READY: being built)" until the final check removes it |
| G3 | Routing-eval runs, three or more times per case | **open: pending** | `routing-eval.md` has 15 cases and no results; it runs on the final commit, on Claude (approved deviation, BUILD-NOTES "Deviations from the build plan (approved)"); pending at the time of writing |
| G4 | The card | closed | `card.json`: five talk stages, steps 3 and 4 `optional`, checks from the runner's list; BUILD-NOTES "Live runner check" |
| G5 | One prompt file per step, delivered at the start of that step only | closed | `prompts/step-1…5`; template shape by `scripts/prompt_sections.py`; quiz 6/6 each (BUILD-NOTES "Code (P5)") |
| G6 | The helper briefs | closed | 26 files under `prompts/subagents/`, each names its tier (BUILD-NOTES "Re-quiz", "The step prompts' own calls, approved") |
| G7 | The inputs-line code and pause | closed | `scripts/inputs_check.py` and `scripts/gates.py`; 62 tests (BUILD-NOTES "Code (P5)") |
| G8 | Output checks, each tested good, edge and padded | closed | each script's tests, with a broken-copy case (BUILD-NOTES "Code (P5)"); the card's output checks seen in the live runner check |
| G9 | Scripts fail loudly, and every script has a timeout | closed | each script exits 0 / 1 / 2 with a distinct meaning and takes `--timeout` (their docstrings; BUILD-NOTES "Code (P5)"). Helpers have no fixed time limit, by ruling (§4, Waiting) |
| G10 | Stop-hook handover for ALONE steps | closed: not applicable | no step runs alone (BUILD-NOTES "Records block (P2)") |
| G11 | Hash-pinned shared copies | closed: not applicable | the skill uses `stage_runner.py` in place and copies nothing (BUILD-NOTES "Records block (P2)") |
| G12 | All testing rules from the skills checklist | closed | met (quiz, planted inputs, live runner check, unit tests) or deferred by the owner's ruling, fixed in use: a real-job trial, a full window, a student install, other models, vague requests (BUILD-NOTES "Not tested") |
| G13 | The status writer | **deferred** | an interactive manual skill with no scheduled run; change condition: it gains a scheduled or unattended step (BUILD-NOTES "Records block (P2)"; root debt ledger §9, the owner's word 2026-11-23) |
| G14 | Example specs at `references/examples/`, scrubbed | **deferred** | to after filing: this spec becomes the first example, scrubbed by the shipping lane; `references/examples/` holds only its README meanwhile, and the skill spec form carries a worked example (approved by the coordinator 2026-11-24, BUILD-NOTES "Deviations from the build plan (approved)") |
| G15 | The completion method, by code | closed | `scripts/completion.py`; band edges in its docstring (50 its own judgment, 90 the owner's); tested |
| G16 | §7's proofs run | closed in part | §7: tested and not-tested lines, each with its record; the fresh-window run and the real test are [to prove] by the owner's ruling, fixed in use |
| G17 | Optional steps on the shared runner | closed | read back on GitHub: `git ls-remote origin V2` = 91e0d681, the optional-steps commit an ancestor (BUILD-NOTES gate table, 2026-11-24) |
| G18 | The finish-after-build step | closed by this pass | marks, rails, counts, coverage, template sections (2026-11-24); the filing and the flip from `spec` to `component` are later steps |
| G19 | Nothing answerable by looking left open | closed | BUILD-NOTES "G19 — research notes against the newest decisions" (9 clashes, 18 of 18 quotes verified) |
| G20 | The status line shows the step and changes on `/next` | **open: with run pickup** | the runner's `statusline` command prints `RUN n/N`; the plugin's status bar does not call it yet (BUILD-NOTES "Live runner check", "Not checked here"); the wiring belongs to run pickup |

## READY FOR THE PLANNER?

Honest fill, against the form's six checks:
- **Every slot filled, or listed in §8 with a recommendation:** passes, except the proofs (§7), which are all `[hypothesis]` by design and run in the build, and the lines still ending `[inferred]`, which the person has not confirmed.
- **Every "never" locked in §2:** passes (L1–L27).
- **Every handoff arrow has both ends, and the §5 table matches the arrows both ways:** passes as carried from the working spec (not re-run by 5.2 for this compile; the build's check runs it again) [inferred].
- **Every section pointer resolves:** passes inside this file; pointers into the packet were not re-opened for this compile [inferred].
- **Every helper's launch is named in its owning step:** passes.
- **Nothing in this form that belongs in the packet:** passes; rework logs, draft-history paragraphs and superseded notes were removed (they stay in the older working copies).

Update 2026-11-24: the owner's rulings of 2026-11-23 and 2026-11-24 and the recovered session items are now in the design and DECISIONS; 4.1 became 4.1a/4.1b/4.1c with §5 rows "open-facts", "facts", "proposals", and 5.3 gained "filing" (§5 re-matched to the arrows by hand, not by the build's check) [inferred]; §8 items 3–5 are new and open; §11 lists the five drafted step instructions. Open, honestly: (1) §8 item 1, optional steps in the shared runner: built on V2 locally (e9632fbb), not yet read back from GitHub; the spec works either way. (2) The section "FOR THE PLANNER AND THE BUILD" is open by design and gated (above); it does not count against completion. (3) The form-audit's proposals for the form itself (ROUTED NOTES item 5) are for the form's owner, not this spec. (4) Step 4 (shake the tree) has not run on this compiled draft as a whole; the last check on the working spec found every ruling of the owner's 2026-11-23 batch reflected, with its four findings noted: three now have homes (one in §6, two in 4.1), the skip machinery is §8-1 with a fallback, and the validation moment on this spec itself is still to come. The open items are carried in the last section above.

Update 2026-11-24 (spec reconciliation): the owner's rulings of 2026-11-24 are now in DECISIONS and applied (house style written once and pointed to; pre-filled templates; the four choices; testing is the comprehension quiz and "no more testing"; /build, never /build-skill). §8 items 1, 3, 4 and 5 are CLOSED (optional steps read back on origin/V2; the cold read is the quiz; the bar's first line and the status line; no fresh-window rule). The counts are re-derived: 24 helper brief files (22 run briefs + 2 bases), 27 quizzed, 29 prompts. §5 gains "step-prompts", "step-prompts-checked", "tool-builder-message" and "handoff-note" (matched to the arrows by hand, not by the build's check) [inferred]. Helper sub-steps are marked ➡️🏃 in the ladder. This skill's own home: the Lifehack plugin, branch V2 (§1).

Update 2026-11-24 (finish pass): the skill is BUILT in the V2 sandbox and every automated check passes (counts and coverage in "THE BUILT SKILL" above). The marks are BUILT and [tested] or [to prove] with their records; §7 and THE GATE carry the results; the rails table (§2) is read from the built files; the 15 calls the step-prompt writer made where this spec was silent are written into the lines they belong to, each marked "(approved 2026-11-24)"; the producer-spec template's sections are filled in T0–T11 and the component page's Part B fields below them. Open, honestly: G3 (routing eval on the final commit), G20 (status-line wiring, with run pickup), the lines still ending `[inferred]`, which the person has not confirmed, and the private pointers in this file (R-numbers, packet paths), which are replaced by plugin-side homes at filing (§6). The §5 table was matched to the arrows by hand, not by code; the reviewer-logic brief checks both ends of every section (planted input 6, §7).

---
Structure adapted from arc42 (CC BY-SA 4.0); see `system/templates/component-page-template.md`.

