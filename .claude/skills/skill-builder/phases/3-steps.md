# BUILDER PHASE 3 — DECIDE THE STEPS

> **Source:** `.claude/skills/skill-builder/SPEC.md` §5. **⚠ This step list is PROVISIONAL BEST THINKING,
> 2026-08-06 — NOT on the LOCKED LIST (§1a).** the owner: *"push it to the spec document as our provisional
> best thinking."* Render it faithfully, but do not tell the human it is locked; L13 already marks
> everything but a desired outcome as expected to change.

**CHAIN DISCIPLINE.** This file is one link in the `/skill-builder` chain. Run it top to bottom. Your
ONLY exit is the NEXT pointer at the foot. Do not read ahead into another phase file. Do not produce
outputs this file doesn't ask for.

**⛔ NAMING RULE (§0, L3).** Always `BUILDER PHASE 3`. ⛔⛔ **NEVER put this ladder's own phase number on
the human's screen** — say `Skill Builder — Choose the steps`, then the TARGET skill's phase number and
name, never "BUILDER PHASE 3" in the human-facing text itself (§8c rule 1). This file's own header
above is for you, the model, not for the screen you render.

**ROLE.** **PHASE OUTCOME:** every phase has a step list, each step carries its own desired outcome,
and each step is tagged **LLM** or **HUMAN**.
⛔ **Never start step work before that phase's desired outcome is locked** — steps are DERIVED from the
outcome; drafting first means inventing steps and working backwards to justify them.

**THE FRAMING, in the human's own terms (§5):** every skill this system builds runs on four layers — it
fetches or stores **data**, it **works things out**, it **shows** something to a person, and the
**person answers**. This phase reverse-engineers the human's phases into steps that walk those four in
order, often several of the same kind in sequence, because processing usually happens in stages before
anything is worth showing. **The human is never asked to know any of that** — you conform the steps to
the architecture; they only ever rule on whether the steps reach what they said they wanted.

**PACING: one phase per round.** Twenty steps at once is unreadable. This does NOT break
horizontal-by-altitude — every phase's finish line was settled in BUILDER PHASE 2 before any step was
drafted; going phase-by-phase *within* the step altitude is pacing, not verticality. **Say this to the
human explicitly** — it looks like a contradiction otherwise.

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

⭐ **IN THIS PHASE the draft is the STEPS ALREADY WRITTEN in the skill.** Tag each existing step rather than re-deriving it, and spend the effort on the steps that are absent.

⛔ **This changes nothing about the step ladder below** — same steps, same order, same forks. The ladder
is HARD-locked; only the human may change it. This block is posture, not a step.

---

## THE STEPS (run once per target-skill phase; §5's step list, applied to phase N of the target skill)

├ 🤖 💾 **3.0** Fetch THIS phase's own prompt from the prompt library (`.claude/skills/skill-builder/prompts/
phase-3.md`) and run scoped to it (§8g).
⛔ **If that file is missing, STOP and say so plainly** — never improvise phase-scoped prompt text and present it as though it came from the library.

├ 🤖 💾 **3.1** Re-read the ratified phase list and every phase's "done" from the brief — steps are
derived from those outcomes and from nothing else.

├ 🤖 ⚙️ **3.2** Take ONE PHASE AT A TIME and draft its steps by walking the four layers in order — what
has to be fetched or already known, what has to be worked out and in what sequence, what gets shown,
and what the human must decide — reaching into the skills SOP (`system/sops/skill-building-sop.md`) and
the parts library for shapes that already exist rather than inventing new ones.
**Several steps of the same layer in a row is normal** — two rounds of processing before anything is
shown is a sequence, not a mistake.

├ 🤖 💾 **3.2b** The FIRST step drafted for every target-skill phase is always the same one: *the prompt
for that phase is fetched from the prompt library and injected*, so each phase runs on a fresh prompt
scoped to itself and the model never sees where the work is going. **What that prompt SAYS is not
decided here** (§8g) — do not invent its content while drafting this step.

├ 🤖 ⚙️ **3.3** Give every step its own purpose, folded into the sentence as a "so that…" clause — a
step whose purpose cannot be said in the same breath is usually two steps or none.

├ 🤖 ⚙️ **3.4** Mark every step with who acts — computer, human, or loop — and which layer it touches.
**A step needing two layer markers is doing two jobs** — split it before the human ever sees it.

├ 🤖 ⚙️ **3.5** For every human step, mark WHO RECEIVES THE ANSWER: `→ LLM (open)` when the human is
thinking out loud and anything they say is usable, or `→ CODE (A|B)` when their answer is read by code
that gates something. **Every `→ CODE` step also gets its named set of valid answers and a failure
mode** — what happens when the human says something outside the set. It must break loudly and re-ask,
never guess which one they meant.

├ 🤖 🖥 **3.6** Show one target-skill phase's steps on screen, led by that phase's number and its "done"
restated in full, so the human answers "do these steps get me to THAT?" rather than "do these look
alright?" Teach as you show, mark every line a best guess, say that corrections flow backward if a
phase's purpose changes, and explain that you pace one phase per round because twenty steps at once
cannot be read.
**THE SCREEN ENDS WITH: A — keep refining this phase's steps. B — lock them and move to the next
phase.**
**PRESENTATION — paste verbatim** (§8c; approved *"Perfect!"* — the outline density, full sentences,
step numbering `<phase>.<step>`, and the closing A/B line are locked; the `/ingest` content below is
the worked example):

```markdown
# 🛠 Skill Builder — Choose the steps

### [emoji] [Target skill] phase N — [that phase's short name]

**Desired outcome —** [that phase's "done," restated in full, from BUILDER PHASE 2]

**Everything below is a guess.** You told me what the phases are and what "done" means for
each one. From that, I've worked out what I *think* the steps inside this phase should be. None
of it is decided. You correct whatever's wrong, and if a correction changes what this phase is
actually for, we go back and fix that phase's finish line in BUILDER PHASE 2.

I'm doing one phase per round, because twenty steps at once is unreadable.

├ 🤖 **N.1** [The computer …, full sentence, folded "so that …" clause]
├ 🤖 **N.2** [The computer …]
├ 🙋 **N.3** [The human …, what they're deciding, full sentence]
├ 🔁 **N.4** [The computer re-shows / the human keeps correcting …, if this phase loops]
└ ✅ Done when [restate the phase's "done"]

---

### ❓ Where did I get it wrong?

1. [question carrying the builder's guess]
2. [question carrying the builder's guess]
3. [question carrying the builder's guess]

---

**A** — Keep refining this phase's steps.
**B** — Lock them and move to the next phase.
```

⛔ Never repeat the target skill's own name on the phase-number line — the H1 above already named it;
the phase number is the human's position and is the one line that orients them.
⛔ Never put THIS builder's own phase number ("BUILDER PHASE 3") on this screen — two numbered ladders
on one screen is the ambiguity that cost a whole session (§8c rule 1).
⛔ Every step line is numbered `<phase>.<step>` (e.g. `1.7`, `2.3`) — the human is dictating; an
unnumbered list forces them to restate a whole sentence to point at it.
⛔ The 🔁 loop line is its own numbered step; the ✅ line carries no number.

├ 🙋 🤝 **3.7** ⑂ **THE FORK.** `→ CODE (A|B)` — this answer gates the phase, so it must be one of the
two.
```bash
python3 .claude/skills/skill-builder/scripts/fork.py "<the human's raw answer>"
```
　· **B → the human accepts these steps → SKIP TO 3.10.**
　· **A → the human says what is wrong** (a step missing, one that does not belong, one in the wrong
order, or one whose purpose is not what they meant) **→ CONTINUE TO 3.8.**

├ 🤖 ⚙️ **3.8** Re-draft that phase's steps from the corrections, and **IF A CORRECTION CHANGED WHAT THE
PHASE IS FOR**, say so out loud and reopen that phase's "done" back in BUILDER PHASE 2 rather than
fitting steps to an outcome that no longer describes the work.

├ 🔁 **3.9** Show the new version on the same screen, ending with the same two options, and repeat for
as long as the human keeps choosing A — loop back to `3.6`.

├ 🤖 💾 **3.10** Write that phase's ratified steps into **THE SPEC DOCUMENT** as PROVISIONAL, and the
working notes into the brief — only the desired outcomes stay definitive. Record which steps are the
human's own and which are machine drafts they accepted.

├ 🔁 **3.11** Move to the next target-skill phase and run `3.2` through `3.10` again, saying each time
how many phases remain, until every phase has a step list. Loop back to `3.2` for the next phase.

└ ✅ **Done when** every phase has a step list the human has accepted or corrected, every step carries
its purpose, its actor and its layer, every human step names whether its answer goes to the LLM or to
code, and the record says which steps are the human's.

---

## STOP-CHECK + NEXT

**Done-check:** every target-skill phase has a step list the human accepted or corrected AND every step
carries purpose + actor + layer AND every human step declares `→ LLM` or `→ CODE` with, for `→ CODE`
steps, a named valid-answer set and a failure mode.

Tell the human plainly what just closed and what opens next — that the readers in BUILDER PHASE 4 are
about to go over the whole thing at once, not phase by phase.

**NEXT:** `4-swarm.md` — BUILDER PHASE 4, the tension swarm.
