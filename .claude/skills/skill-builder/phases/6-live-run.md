# BUILDER PHASE 6 — THE LIVE RUN, AND THE LOOP BACK

> **Source:** `.claude/skills/skill-builder/SPEC.md` §7a. The step list below is locked — owner, 2026-08-06:
> *"Yes, this is good. Let's push it to the spec document. It's now complete."* (Ratified the same way as
> L7/L14, no separate §1a letter.)

**CHAIN DISCIPLINE.** This file is one link in the `/skill-builder` chain. Run it top to bottom. Your
ONLY exit is the NEXT pointer at the foot — which, in this phase, may point BACK into an earlier phase
file per step `6.14`. Do not read ahead into another phase file beyond where that step sends you. Do
not produce outputs this file doesn't ask for.

**⛔ NAMING RULE (§0, L3).** Always `BUILDER PHASE 6`.

**ROLE.** **PHASE OUTCOME:** the skill has been run for real, by the human, on real work — and what it
got wrong is written back into the spec, so the next pass through the chain fixes it at the source
rather than patching the symptom.

**★ THIS IS WHAT MAKES THE BUILDER RECURSIVE, NOT A ONE-SHOT FACTORY.** No decision in this whole method
is permanently sealed outside §1a's LOCKED LIST — that is exactly why this phase exists.

**TWO WINDOWS AT ONCE.** Session **A** is this builder session and **STAYS OPEN, waiting**. Session
**B** is a disposable window where the skill actually gets run. The human moves between them; **nothing
is copied across by hand** — B writes its findings into the project's own brief and A reads them from
there.

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

⭐ **IN THIS PHASE the draft is the skill AS IT RUNS TODAY.** The live run tests whether the missing parts are now present and the skill survives a human who knows nothing about it.

⛔ **This changes nothing about the step ladder below** — same steps, same order, same forks. The ladder
is HARD-locked; only the human may change it. This block is posture, not a step.

---

## THE LOCKED STEPS

├ 🤖 💾 **6.0** Fetch THIS phase's own prompt from the prompt library (`.claude/skills/skill-builder/prompts/
phase-6.md`) and run scoped to it (§8g).
⛔ **If that file is missing, STOP and say so plainly** — never improvise phase-scoped prompt text and present it as though it came from the library.

├ 🤖 🖥 **6.1** Explain what is about to happen and **WHY THE TEST RUNS SOMEWHERE ELSE**: this session
helped decide how the skill should work, so it already knows what everything was MEANT to do. A window
that knows nothing is the only honest test. Teach what the human is looking for — the moments they felt
lost, had to guess, or had to say something twice.
⚠ **No verbatim PRESENTATION block is supplied in the spec for this screen** — build it from §8's
four-move opening; do not invent one and label it "verbatim."

├ 🤖 💾 **6.2** Write the FULL HANDOFF into the brief, containing, in order:
　(a) ⭐ **LOCKED** — an instruction telling session B to load the `project-manager` skill BY NAME, IN
PLAIN LANGUAGE, **NEVER as a slash command**, so B reads the project's brief without firing the command;
　(b) the instruction to then type the target skill's own command by hand;
　(c) what to do during the run;
　(d) THE ROLL-UP PROMPT to paste when the run ends;
　(e) the instruction to come back to session A and say "go."

├ 🤖 🖥 **6.3** Hand over the instructions and say plainly: **LEAVE THIS WINDOW OPEN.** This session is
not finished — it is waiting for session B to write its findings into the brief.

├ 🙋 🤝 **6.4** *(session B, in a fresh window)* The human opens session B, loads the project by name,
and runs the target skill **ON REAL WORK**. They observe and say what they don't like.
⛔ **They do not fix anything and they do not build** — *"I didn't like that, but let's keep going."*
They get as far through the skill as they can and notice everything along the way.

├ 🙋 🤝 **6.5** *(session B)* When the run ends — finished or as far as it got — the human pastes THE
ROLL-UP PROMPT into session B. That prompt tells B exactly what to capture and to write it DURABLY into
the project's scratchpad: everything the human disliked, everything they said, and — ⭐ the part only
that window can see — **EVERYTHING THE HUMAN NEVER SAW**, including background work that happened
off-screen.

├ 🙋 🤝 **6.6** *(back in session A)* The human returns and says **"go."** `→ CODE (go)`
⛔ Anything other than "go" breaks loudly and re-asks — this answer is attached to code, so the human
makes the choice and the choice is confirmed.

├ 🤖 💾 **6.7** Read the project brief and its scratchpad. **Nothing is copied across by hand** — session
B already wrote it down, which is the whole reason the handoff was built that way.

├ 🤖 ⚙️ **6.8** Decide ONE thing first: **is anything critical missing from that test run?** You are
deciding whether you can proceed, not whether the skill was any good.

├ 🤖 🖥 **6.9** Say which it is. If something is missing, **write a second prompt** for the human to
paste into the still-open session B, naming exactly what to find and write to the scratchpad. If
nothing is missing, say session B can be closed.
**THE SCREEN ENDS WITH: A — go fetch what's missing. B — we have everything.**
⚠ **No verbatim PRESENTATION block is supplied in the spec for this screen** — same note as `6.1`.

├ 🙋 🤝 **6.10** ⑂ **THE FORK.** `→ CODE (A|B)`
```bash
python3 .claude/skills/skill-builder/scripts/fork.py "<the human's raw answer>"
```
　· **A → the human pastes the new prompt into session B and returns → BACK TO 6.7.**
　· **B → session B is closed → CONTINUE TO 6.11.**
⛔ Neither answer breaks loudly and re-asks.

├ 🤖 ⚙️ **6.11** Propose changes TO THE SPEC. ⭐ **You may only change what the spec marks
provisional; §1a's LOCKED LIST is what you must not touch without a ruling.** This is what that marking
was for: a fresh session coming in cold can tell instantly what it is allowed to rewrite, instead of
guessing at what was settled.

├ 🤖 🖥 **6.12** Show the proposed spec changes in plain language, each with why the live run justifies
it.
**THE SCREEN ENDS WITH: A — change something. B — approve it.**
⚠ **No verbatim PRESENTATION block is supplied in the spec for this screen** — same note as `6.1`.

├ 🙋 🤝 **6.13** ⑂ **THE FORK.** `→ CODE (A|B)`
```bash
python3 .claude/skills/skill-builder/scripts/fork.py "<the human's raw answer>"
```
　· **A → redraft → BACK TO 6.11.**
　· **B → CONTINUE TO 6.14.**

├ 🔁 **6.14** The chain fires again. **WHERE IT RE-ENTERS DEPENDS ON WHAT `6.11` CHANGED:**
　· the spec changed **MATERIALLY** → **RE-ENTER AT `4-swarm.md` (BUILDER PHASE 4, the tension swarm)**.
Step `6.11` had THIS session rewrite the spec, and a session cannot review its own fresh writing —
measured: 7 of the first swarm's 12 findings were drift that same session created hours earlier. Four
cheap parallel readers are the price of not building on unreviewed self-edits.
　· the change was **trivial** (a wording fix) → **RE-ENTER AT `5-build.md` (BUILDER PHASE 5) and skip
the swarm** — four readers over a one-word change is waste.
　From there: check the SOP, plan it, build it, test it — each with its own approval before it moves.
Nothing is re-specified here, because BUILDER PHASE 5 already is that chain.

├ 🔁 **6.15** The human opens a THIRD window and runs the sharpened skill again, **from `6.4`**. This
loop runs as many times as it takes, and each pass is smaller than the last because the spec keeps the
gains. Loop back to `6.4` in THIS file.

└ ✅ **Done when** the human has run the skill for real, everything that run revealed has been written
into the spec rather than only into the built files, and the human says it is good enough to stop.

---

⭐ **"EVERYTHING THE HUMAN NEVER SAW" IS A CATEGORY OF EVIDENCE NOTHING ELSE IN THIS SYSTEM COLLECTS.**
Every other feedback loop captures what the person noticed. The roll-up prompt (`6.5`) captures what
happened off-screen — and the only window that can see it is the one that just ran.

---

## STOP-CHECK + NEXT

**Done-check:** a real run has happened AND every observation from it has landed in the spec (or been
explicitly ruled out of scope). ⛔ An observation that lives only in the transcript is lost — it must be
in the brief/spec before this file can close.

Tell the human plainly what the live run found and what got written back.

**NEXT — conditional on step `6.14`, not a fixed file:**
- spec changed materially → **`4-swarm.md`** (BUILDER PHASE 4)
- spec changed trivially → **`5-build.md`** (BUILDER PHASE 5)
- human wants another live-run pass (`6.15`) → **loop within this file, from `6.4`**
- human says it's good enough to stop → the chain closes; there is no next file.
