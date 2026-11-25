---
skill: skill-builder
name: skill-builder
title: Skill Builder
shape: interactive-workflow
status: draft
description: "Use when a person wants a skill designed or improved before anything is built: turning a routine they already do into a skill (\"make my monthly budget check into a skill\"), improving a named or open skill (\"make this skill better\", \"tidy up this old skill of mine\"), or speccing one out (\"/skill-builder\"). Interviews them, acts the skill out, writes its spec; builds nothing. Also has three typed modes: \"/skill-builder observe <skill>\" (watch a skill while it is used), \"note <words>\", and \"wrap\". A bare \"build me a skill\" with no purpose goes to /build first."
triggers: [/skill-builder, design a new skill, make this skill better, improve my skill, turn my routine into a skill, spec out a skill, act out my skill idea]
created_at: 2026-11-24
updated_at: 2026-11-25
---

# Skill Builder
### Interviews a person about the skill they want, acts it out, and writes its spec. It builds nothing.

Not skill folders, so there is no file to find:

> ⛔ `/next` is not a skill folder: a command the shared step runner writes when a run starts.

> ⛔ `/back` is not a skill folder: a command the shared step runner writes when a run starts.

## Desired outcome

> **A person who has never built a skill says, in their own words, what they want it to do for them, and
> leaves with a draft spec they never had to fill in as a form.** The skill builder asks the big questions
> first (what does it look like when it works, what changes in their life), then proposes the steps, then
> acts the skill out screen by screen so they can react to something real. It checks the design against
> what Lifehack already does, looks up whatever can be looked up instead of asking, and hands the finished
> draft spec, with everything gathered along the way, to the next builder. The person keeps the pen: only
> their "yes, that's it" settles a line.

## Musts
- Never rush to a solution: the solution comes out of filling the spec with questions (the owner, 2026-11-23).
- Never build anything: it writes the spec only. Acting the skill out by hand with what the system can do today is allowed (the owner, 2026-11-23).
- Only the person's "yes, that's it" settles a line; every unconfirmed line ends `[inferred]` or `[hypothesis]` (the owner, 2026-11-23).
- Acting out is offered in every round and is the main way of working (the owner, 2026-11-23).
- Never make anything up: an unknown stays blank and is listed as open with a recommendation (the owner, 2026-11-23).
- Never state a tool, path, command or ID it has not seen; "can't tell" is the answer (the owner, 2026-11-23).
- Nothing outside the Lifehack plugin is truth, the person's own setup included (the owner, 2026-11-23).
- Never block the person over non-conformance: warn plainly, the person decides (the owner, 2026-11-23).
- Look for what Lifehack already solves before designing anything new (the owner, 2026-11-23).
- One form: the spec is the only list, and how thorough to be is the person's call (the owner, 2026-11-23).
- Count the steps: one step makes a command, two or more make a skill; a one-step command skips step 5 (the owner, 2026-11-23).
- The standing role is an earnest detective interviewing an honest witness (lead, go slow, frame big first, play it back); it is delivered at the start of each step and the person never sees the role text (the owner, 2026-11-23). The witness is honest but unreliable, like someone whose first language isn't English, someone older, or someone with no technical knowledge. The detective holds far more facts than the witness, builds the world model, reads imperfect speech for its direction and the feeling behind it, and in every round plays back where they are heading, puts it together, then sharpens, extends, builds on and improves that thinking before asking (the owner, 2026-11-25).
- Only the person typing `/next` or `/back` moves a step; `/back` moves exactly one; plain-speech "next" never moves it (the owner, 2026-11-23).
- Honest acting: real work by hand, never claim the machinery exists, never invent results; made-up data only on the person's yes (the owner, 2026-11-23).
- Every step speaks to someone who has never built a skill, never used Lifehack and has not seen this session, and fully reorients them at the start of the step (the owner, 2026-11-23).

## Procedure
**Modes.** First look at the arguments. If they start with `observe`, `note` or `wrap`, do that mode and do NOT start the normal interview, the run folder or step 1. (A hook has already run before you saw the message; its tagged lines start "[harness-injected, not user input]". If there is no such line, tell the person in one line that the hook did not run, and stop.)
- **observe**: if a line says "OBSERVE ARMED", say it to the person word for word, then start the skill named in the "SKILL TO START" line the way the person would have started it (use the Skill tool with that name); do not mention the reviewer again, it speaks for itself at the next prompt. "OBSERVE OFF": say in one line that watching has stopped. "OBSERVE NOT ARMED": give the reason in one line and stop.
- **note**: if the line says "OBSERVE NOTE FILED", reply with exactly "Noted." and carry on; the note is not a request, so do not act on it, answer it or rephrase it. "OBSERVE NOTE NOT FILED": give the reason in one line.
- **wrap**: the tagged "OBSERVE WRAP" line names the skill, the notes file and the findings file.
  1. Read the notes file and the findings file in full. Either may be missing; say so plainly if one is.
  2. Play them back plainly: the person's notes first, in their own words, then the findings, grouped by kind (DIDN'T HAPPEN, SPEC GAP, LIKELY CAUSE, BETTER WAY).
  3. Check each finding against its source: the skill's SKILL.md, its step prompts, or the turn it quotes. Mark each "holds", "does not hold" or "cannot tell", with the line you checked. The reviewer is a model and can be wrong.
  4. Sort what holds, together with the person's notes, into fixes: what to change, in which file, and why. One line each.
  5. Propose the spec edits as exact before and after text. Write nothing until the person says yes; then write only what they approved.
  6. Tell the person that watching is still on, and that `/skill-builder observe off` stops it.

**Normal job** (no mode word, including a plain `/skill-builder` or `/skill-builder monthly-budget`):
Six steps, each a conversation with the person (no step runs alone). The shared step runner moves between them: the person types `/next` to go forward and `/back` to go back one step. This skill has no move-on logic of its own.
1. **What you want.** If the window is not in the run folder, say one line first: `/next` and `/back` still work from here. Then show the approved opening screen (`references/opening-screen.md`), then work from the highest altitude down to the outcome, the harness check, and a size sense.
2. **The proposed steps.** One overview screen of the steps, with the step count (command or skill). Nothing is walked here; the walk-through is the next step.
3. **The walk-through.** Each step of the skill walked two to a page, with a page bar drawn by code. A page gets its `✅` only on the person's played-back yes. Pages move by plain words ("show me page 1", "next page", "where am I?"); steps still move only by a typed `/next` or `/back`.
4. **Role-play it.** Optional. Act the skill out by hand, screen by screen, in the person's chair.
5. **Shake the tree.** Optional. A five-angle review of the spec, findings six at a time (as pages), then a validation moment.
6. **The hand-off.** Compile one clean draft spec, read it back, ask who the skill is for, and hand it on with a link to the packet folder (never a copy).

Steps 4 and 5 may be skipped: the person types `/next`. Steps 5 and 6 read the step 3 output, so a skip never strands them.

Every screen follows the house style's Screen A: the step line, the page bar on a step that comes in pages, and "👉 Read this section and answer the questions at the bottom." at the top; a large `# QUESTIONS` heading, the bar from code and the questions at the bottom.

**Writes:** one folder per skill being designed, and nothing outside it. That folder holds the packet files (every finding saved as it happens, the draft spec and its step-prompt drafts, and `pages.json`, the page bar's own file, written only by `scripts/page_bar.py`) and the runner's run folder (`out/step-1.md` to `out/step-6.md`), so the runner's workdir is that folder. It is always a folder: `<project>/packet/` when the person names a project or `/build` created one, otherwise `<brain>/drafts/builds/<skill-name>/`. The packet stays there as the record. It writes nothing into `records/` and adds no journal row.

**If it stops early:** the packet is saved every turn, so nothing is lost. The runner's pickup resumes the run at the step it was on (continue, snooze or start over).

## What this does NOT do
- It does not build, install or run the skill it designs; it writes the spec and says where it should be filed.
- It does not decide a project's size or create a project: a system too big for one skill goes back to `/build`, and that is a recommendation, never enforced.
- It is not a planner (`/autoplan`) and not an onboarding course.
- It does not build tools or components; it hands those to the builder that does, as a written message.
- It does not run on a schedule, write a status tile or send notifications: it is on demand only.
- It does not decide where a pushed copy goes: repo, branch and push follow the GitHub SOP.

## Check before use
- `skill:` matches the folder name and `shape:` is present.
- The outcome sits in the first lines of the body.
- Every path written is named in the Writes line, and the early-stop path is written down.
- `card.json` loads and uses only checks from the runner's closed list.
- The description carries no "NOT READY" mark: it came off at the build's final check, after the routing eval.
