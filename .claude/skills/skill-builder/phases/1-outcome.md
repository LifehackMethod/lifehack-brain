# BUILDER PHASE 1 — DEFINE THE DESIRED OUTCOME

> **Source:** `.claude/skills/skill-builder/SPEC.md` §3. The step list below is **L7, HARD-locked** (§1a):
> *"lock this into the spec document as locked for phase one"* (owner, 2026-08-06). Only the human may
> change it. This driver renders that list step for step — nothing added, nothing dropped.

**CHAIN DISCIPLINE.** This file is one link in the `/skill-builder` chain. Run it top to bottom. Your
ONLY exit is the NEXT pointer at the foot. Do not read ahead into another phase file. Do not produce
outputs this file doesn't ask for.

**⛔ NAMING RULE (§0, L3 HARD-locked).** Never say a bare "phase 1." Always **`BUILDER PHASE 1`** when
talking about this file's own place in the chain, and `<the target skill> PHASE N` for the skill being
built. Two ladders are in play at once; conflating them cost a whole session once.

**ROLE.** You are the builder, running BUILDER PHASE 1 of the skill-builder chain. **PHASE OUTCOME**
(the bar this file exists to clear): the whole skill's desired outcome exists in the human's own words,
as a felt result, and you understand it well enough to propose a phase breakdown next. You do **not**
propose the phases here — that is BUILDER PHASE 2's job (§4's ruling: *"the phases can be the second
step"*). This phase only scopes the outcome and how big the work is.

**STANDING RULES ON EVERY TURN YOU SHOW (§8e, L9–L13 — apply for the rest of this file, not just once):**
1. **Teach, don't just instruct** — say *why*, not only *what* (L9).
2. **Orient every turn** — where they are, what's next, that it will end (L10).
3. **Interrogative, never solving for them** — you brainstorm WITH the human; you never invoke the
   `brainstorming` skill (L11).
4. **Everything you write is a labelled guess** until the human confirms it (L12).
5. **Desired outcomes shown to the human are future tense** — "you'll be asked," never "you were
   asked" (L16). Only the desired outcome itself is ever written as *definitive* (L13); everything
   else in this phase's output is provisional.

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

⭐ **IN THIS PHASE the draft is the DESIRED OUTCOME the shipped skill already implies** — step `1.2` reads it off disk and `1.3` writes it down for the human to correct.

⛔ **This changes nothing about the step ladder below** — same steps, same order, same forks. The ladder
is HARD-locked; only the human may change it. This block is posture, not a step.

**THE BY-PRODUCT — never the deliverable.** While `1.2` reads the skill, keep a running list of **claims
with nothing enforcing them**, each cited `file:line`. The two richest seams, both in
`system/sops/skill-building-sop.md`:

- **§V.4d** (line 1990) — *"a claim's PROXIMITY to a thing is not evidence about that thing. Before you
  price, plan, or certify anything off a comment, a status field, a marker, a docstring or a shown
  expression — read the thing itself."*
- **§V.9** (line 2110) — **validator-exists-but-nothing-calls-it:** a real checker sitting in the repo
  that no orchestrator ever runs. `grep` for each checker's callers; never assume it fires.

⛔ **the owner ruled this a BY-PRODUCT, 2026-08-08** — it feeds `1.4`'s *"what did you want it to do that it
wasn't doing"* conversation and never replaces it. Do not re-scope this phase around producing a report.

---

## THE LOCKED STEPS

├ 🤖 💾 **1.0** Fetch THIS phase's own prompt from the prompt library (`.claude/skills/skill-builder/prompts/
phase-1.md`) and run scoped to it — the model never sees where the work is going (§8g).
⛔ **If that file is missing, STOP and say so plainly** — never improvise phase-scoped prompt text and present it as though it came from the library.

├ 🙋 🤝 **1.1** ⑂ **THE FORK.** `→ CODE (A|B)`
The opening screen asks two things at once — are we building a **NEW** skill, or fixing one that
**ALREADY EXISTS** — and only then, depending on the answer, either "what do you want this skill to do
for you" (§8a's reframings) or "point me at the skill you want to improve." One screen; the second
question is meaningless without the first.
　· **A = a NEW skill → SKIP TO 1.4.**
　· **B = it ALREADY EXISTS → CONTINUE TO 1.2.**
⭐ **Half-built and shipped are the SAME answer** — both mean "something is on disk, go read it." *How
much* exists is discovered by looking (step 1.2), never asked of the human.
⛔ **Nothing is pulled, read, or asked before this step.** For a brand-new skill there is nothing on
disk to mine yet, and the two paths need completely different first moves.
⛔ An answer that is neither A nor B breaks loudly and re-asks — never guessed.
**PRESENTATION — paste verbatim** (§8a; only the skill's own name changes; this is fixed text, not
regenerated per run):

```markdown
# 🛠 Skill Builder

Let's build you a skill.

You tell me what you want it to do, in your own words. I do the rest — work out the
phases, draft what each one has to accomplish, and show you my guesses so you can tell
me where I'm wrong. You never have to learn how any of it works underneath.

**One question to start, and it's the only one that matters right now.**

### What do you want this skill to do for you?

If that's a hard way to think about it, any of these get at the same thing:

1. What does it look like when it's done?
2. What does it produce, if it worked?
3. What would happen in your life that doesn't happen now?

Not how it works — what it's like when it's working.

Say it however it comes out. *"I want to be able to…"* or *"right now I have to ___ and
I hate it."* Messy is fine. I'll say it back to you, we'll sharpen it over a round or
two, and then we move.

---

**Why I'm only asking you this one thing.** Once I know what you want out of it, I can work out the rest — how it breaks up, what each part has to do, which pieces already exist that I can reuse. What I can't work out is what you actually *want*, or whether I've guessed right.

So those are the only things I'll come back to you for. Everything else is mine, and I won't make you sit through it. That's the whole idea here — you shouldn't have to hold this in your head, or learn how any of it works, or write a single thing down properly. You talk, I draft, you tell me where I got it wrong.
```

✅ **THE "WHY AM I BEING ASKED THIS" PASSAGE IS WRITTEN AND APPROVED** (owner, 2026-08-08). It is the closing
beat of the screen above and is FIXED TEXT — reproduce it verbatim, never regenerate it. ⚠ Its PLACEMENT at
the foot of the screen is provisional; the owner ruled the presentation layer gets refined during the first real
run.
⛔ **Do not open by showing the spec template, the grid, the tiers, or the four undecidables** (§1,
§8a) — those are machinery, and machinery never surfaces to the human (L6).

　↳ **if the skill ALREADY EXISTS (from 1.1's B branch)**

├ 🤖 💾 **1.2** Pull everything on disk about that skill — its `SKILL.md`, its phase files, its code, its
`SPEC.md` if it has one, and its project history — so the human is never asked for what the system
already knows.

├ 🤖 ⚙️ **1.3** Draft the desired outcome that skill **ALREADY IMPLIES** from what you just read, so the
human corrects a draft instead of composing from a blank page. Present it explicitly as a guess (L12).

　↳ **both paths rejoin here**

├ 🔁 **1.4** Brainstorm WITH the human. For a new skill: ask what they want it to do and why. For an
existing one: ask what went wrong — what did they want it to do that it wasn't doing — debugging in
plain language. Teach as you go (L9) and say where they are (L10).
⛔ Never invoke the `brainstorming` skill — just brainstorm.
**EVERY ROUND ENDS WITH THE TWO OPTIONS:** A — keep going. B — I've said enough, move on.

├ 🙋 🤝 **1.5** ⑂ **THE FORK.** `→ CODE (A|B)`
　· **A → BACK TO 1.4** — the loop continues.
　· **B → CONTINUE TO 1.6.**
⛔ Neither answer breaks loudly and re-asks — the human always knows the door is there.
Read the human's raw answer through the fork reader (§8f's closed vocabulary, already built):
```bash
python3 .claude/skills/skill-builder/scripts/fork.py "<the human's raw answer>"
```
Prints `A`, `B`, or `NO_OUTCOME` and exits non-zero on `NO_OUTCOME` — an unrecognised answer is never
read as consent. On `NO_OUTCOME`, re-ask; do not guess which one they meant.

├ 🤖 ⚙️ **1.6** Work out from the conversation how big this thing actually is: how many steps, how much
the human is involved, how much information has to be gathered and processed.

├ 🤖 💾 **1.7** **At the end of the phase — not before —** create the project brief (plus a plan if the
work warrants one), and fill in as much of it as you can from everything this phase produced, writing
the rest into that brief's scratchpad.
⭐ Every field you filled is marked **THE MACHINE'S BEST GUESS**, never settled — you are guessing at a
human's intent and must say so.
⭐ **Only the desired outcome is written as definitive (L13);** everything else drafted here — steps,
methods, wording — is version one and expected to change.
**The brief IS the scratchpad** — there is no second place. A one-step skill gets neither brief nor
plan. Arm/inspect it the way the rest of this system does:
```bash
bash system/hooks/pm_flag.sh status   # names the armed brief, or `none`
```
Waiting until the end of the phase means someone who walks away mid-conversation leaves no orphan file.

└ ✅ **Done when** the human's own words are on the page as a felt result, you can state how you would
break the work into phases, and — if the skill is big enough to warrant it — a brief exists holding
everything gathered, with every machine-filled field marked as a guess.

---

## THREE RULINGS THAT GOVERN THIS PHASE (§3, earned the sitting it was drafted)

1. ⛔ **Nothing is pulled, read, or asked before 1.1.** The fork question comes first — the two paths
   need different first moves, and for a new skill there is nothing on disk to mine.
2. ⛔ **There is no separate scratchpad.** The brief IS the scratchpad — two homes for one artifact is
   the exact mistake that lost `/ingest`'s world-model file once.
3. ⛔ **This phase does not propose the phases.** It scopes HOW BIG (1.6); BUILDER PHASE 2 proposes the
   list.

**The phase test to carry forward into BUILDER PHASE 2:** *"The computer does something, then the human
responds — that's a phase. Looping and ideating on one thing isn't a new phase."* If the human's next
turn is the SAME turn again, better, it's a loop, not a phase.

---

## STOP-CHECK + NEXT

**Done-check before you leave this file:** the human's own words are on the page as a felt result AND
you can say how you'd break the work into phases AND (if warranted) the brief exists with every
machine-filled field marked a guess. If any of those is missing, you are still inside step 1.4/1.5's
loop — do not advance.

Tell the human plainly what just happened and what comes next, in the spirit of §8's four-move opening
(map → what came before → what's now, and why → the question) — never a bare "done."

**NEXT:** `2-phases.md` — BUILDER PHASE 2, propose the phases + each phase's desired outcome.
