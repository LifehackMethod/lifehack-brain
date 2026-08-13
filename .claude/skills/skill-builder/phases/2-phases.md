# BUILDER PHASE 2 — PROPOSE THE PHASES + EACH PHASE'S DESIRED OUTCOME

> **Source:** `.claude/skills/skill-builder/SPEC.md` §4. The step list below is **L14, HARD-locked** (§1a):
> *"This is fully approved. I love it."* (owner, 2026-08-06). Only the human may change it.

**CHAIN DISCIPLINE.** This file is one link in the `/skill-builder` chain. Run it top to bottom. Your
ONLY exit is the NEXT pointer at the foot. Do not read ahead into another phase file. Do not produce
outputs this file doesn't ask for.

**⛔ NAMING RULE (§0, L3).** Always `BUILDER PHASE 2`, never a bare "phase 2" — and never let the human
confuse this ladder with the target skill's own phase ladder, which is what actually goes on screen.

**ROLE.** **PHASE OUTCOME:** the human has seen a proposed breakdown of their skill into phases, seen
how those phases add up to the outcome they gave in BUILDER PHASE 1, seen a suggested "done" statement
for every single phase, and corrected whatever was wrong.

**⭐ THE SHAPE, stated once because it governs every step below: THE BUILDER SUGGESTS, THE HUMAN
CORRECTS.** ⛔ Do not ask the human to author phase outcomes one at a time — draft all of them together
and present them as a set; the human rules by exception, never composes from blank.

**THE PHASE TEST, applied while drafting (§4):** A PHASE IS A UNIT OF HUMAN ATTENTION — machine-only
work is a step inside the phase it feeds, never a phase of its own. When roughly three genuinely
distinct human decisions live inside one candidate phase, split it.

**STANDING RULES still in force (§8e, carried from BUILDER PHASE 1):** teach as you show · orient every
turn (map, what came before, what's now-and-why, then the questions — §8) · interrogative, never
solving for them · every drafted line is a labelled guess · desired outcomes shown in future tense ·
only desired outcomes are ever written as definitive (L13).

**⛔ DOOR TWO — IF THIS RUN IS FIXING A SKILL THAT ALREADY EXISTS.**

> **Ruled by owner, 2026-08-08, `authority: user`:** *"I didn't build a skill properly because I didn't
> build it with my skill builder. So it's going to put it back through a rigorous pipeline… The critique
> is not really an important part."* ⇒ **Door two is a REMEDIAL PIPELINE, not a reviewer.** A skill built
> without the builder is missing parts; this chain's job is to find which, and put them in.

The chain runs in **FULL** — no phase is skipped and nothing rejoins later. What changes is the POSTURE:

1. **What the skill ALREADY HAS is the draft.** Read it before you write anything, and show the human
   what you found as the draft they correct — never a blank page.
2. **The question at every stage is *"WHAT IS MISSING HERE?"*** — never *"what should this be?"*
   Blank-page work on a skill that already exists is the exact failure this door prevents.
3. **Everything you derived is a GUESS and says so on screen (L12).** Reading a skill tells you what it
   DOES; only the human can say what it was SUPPOSED to do.

⭐ **IN THIS PHASE the draft is the PHASE STRUCTURE the skill already has** — its phase files, or the sections of its `SKILL.md` if it has no phase files. Propose against that, and name what has no phase covering it.

⛔ **This changes nothing about the step ladder below** — same steps, same order, same forks. The ladder
is HARD-locked; only the human may change it. This block is posture, not a step.

---

## THE LOCKED STEPS

├ 🤖 💾 **2.0** Fetch THIS phase's own prompt from the prompt library (`.claude/skills/skill-builder/prompts/
phase-2.md`) and run scoped to it (§8g).
⛔ **If that file is missing, STOP and say so plainly** — never improvise phase-scoped prompt text and present it as though it came from the library.

├ 🤖 💾 **2.1** Re-read the brief and everything BUILDER PHASE 1 gathered, so you propose from the
written record rather than from whatever you happen to remember of the conversation.

├ 🤖 ⚙️ **2.2** Draft the phase list, applying one test to every candidate: **A PHASE IS ONE DISTINCT
DESIRED OUTCOME.** Many exchanges can live inside a single phase because refining one idea takes several
passes; but when a stretch of work is chasing a DIFFERENT outcome, that stretch is a new phase — and
roughly three genuinely distinct human decisions inside one phase means it should almost certainly be
split into two.

├ 🤖 ⚙️ **2.3** Draft a suggested "done" for EVERY phase, all in one pass, so the human never has to
compose a finish line from a blank page.

├ 🤖 ⚙️ **2.4** Write the argument for the breakdown: how these phases, in this order, add up to the
outcome the human gave in BUILDER PHASE 1. **This argument is the thing the human is actually ruling
on** — the list alone is not enough.

├ 🤖 🖥 **2.5** Show the whole thing on one screen, in one order — phase list, then the argument, then
every phase's suggested "done" — and TEACH WHILE YOU SHOW: what a phase is, why the outcome has to be
settled before any step is written, and why the human is being asked to do this at all (because once
the phases exist, the computer can reach into what it already knows and fill in the rest, so the human
never has to write a specification themselves). Every line is labelled a best guess and the invitation
to edit is said out loud.
**THE SCREEN ENDS WITH TWO OPTIONS: A — keep refining this. B — lock it and move to the next phase.**
**PRESENTATION — paste verbatim** (§8b; the outline markers, the 🤖/🙋 labels, the sentence density, and
the closing A/B line are what is locked — the `/ingest` specifics below are the worked example, not
the content you output):

```markdown
# 🛠 Skill Builder

**Your target, in your words**
> [the human's desired outcome, played back verbatim in their own words]

That's the target. Everything below is my attempt to get you there.

**My plan — N phases.** 🤖 = the LLM works · 🙋 = the human's turn · 🔁 = a loop

**[emoji] 1 · [phase name]**
├ 🤖 **LLM** — [full sentence: what it does, why it matters, in plain teaching language]
├ 🙋 **HUMAN** — [full sentence: what they're deciding, the concrete moves available]
└ ✅ **Done when** [felt result, in plain language]

**[emoji] 2 · [phase name]**
[... same shape, one block per proposed phase ...]

**Why this order.** [one paragraph arguing how these phases reach the desired outcome —
this is the real thing the human is ruling on, not decoration]

---

### ❓ Where did I get it wrong?

1. [question, carrying the builder's guess]
2. [question, carrying the builder's guess]
3. [question, carrying the builder's guess]

---

**A** — Keep refining this.
**B** — Lock them and move to the next phase.
```

⛔ Speaker labels are 🤖 **LLM** and 🙋 **HUMAN** — never "me"/"you." 🔁 loop lines are their own line,
never a badge on a phase title. Every sentence names its subject in full — `The computer …` / `The
human …` — never a title-then-dash-then-fragment.

├ 🙋 🤝 **2.6** ⑂ **THE FORK.** `→ CODE (A|B)` — this answer gates the phase, so it must be one of the
two, and an answer that is neither breaks loudly and re-asks.
```bash
python3 "$ROOT/.claude/skills/skill-builder/scripts/fork.py" "<the human's raw answer>"
```
　· **B → the human is accepting the board as it stands → SKIP TO 2.9.**
　· **A → the human says what is wrong** (reorder, merge, split, rename, rewrite a "done", or name
where the argument does not hold) **→ CONTINUE TO 2.7.**

├ 🤖 ⚙️ **2.7** Take those corrections and re-draft the board: a new phase list, new outcomes where they
changed, and a re-written argument — a changed list makes the old argument false, so it is rewritten
too, never patched around.

├ 🔁 **2.8** Show the new version on the same screen, ending with the same two options, and repeat for
as long as the human keeps choosing A. **THE PHASE CANNOT CLOSE WHILE A CORRECTION IS OUTSTANDING** —
loop back to `2.6` after every re-draft.

├ 🤖 💾 **2.9** Only after the human chooses B, write the ratified phase list into **THE SPEC DOCUMENT**
(the target skill's own durable `SPEC.md` — the record `/autoplan` and `/build` will read later, not
this session's chat) and the working notes into the brief.
**Only the desired outcomes are written as definitive** — the steps, methods and wording stay
provisional, because this is version one of something that loops (§7a). Record, for each phase, whether
its "done" is the human's own words or a machine draft the human accepted.

└ ✅ **Done when** every phase carries a "done" the human has accepted or rewritten, the human has seen
all of them side by side, and the record says which ones are theirs.

---

## THE LOOP, made explicit

`2.5` → `2.6` → (if A) `2.7` → `2.8` → back to `2.6` → (if B) `2.9`. This is the same turn-closing fork
every screen in this method ends on (§8f) — read through `scripts/fork.py`, never guessed by eye.

⭐ **2.6 IS A FORK AND THIS DRIVER SAYS SO EXPLICITLY** — a branch that lives only in a reader's head is
one the build gets wrong (owner, 2026-08-06).

---

## STOP-CHECK + NEXT

**Done-check:** every phase carries a "done" the human accepted or rewrote AND the human has seen all
phases side by side AND the record marks which "done" lines are the human's own words versus a machine
draft they accepted. ⛔ A builder-drafted outcome the human has never seen does NOT count — it is a
guess wearing a locked outcome's clothes.

Tell the human plainly what just closed and what opens next.

**NEXT:** `3-steps.md` — BUILDER PHASE 3, decide the steps.
