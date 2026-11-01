# BUILDER PHASE 4 — THE TENSION SWARM

> **Source:** `.claude/skills/skill-builder/SPEC.md` §6 + §6a. The step list below is locked — owner, 2026-08-06:
> *"let's lock this."* (Not separately numbered in the §1a table, but ratified the same way L7/L14 were:
> a "✅ THE LOCKED STEP LIST" heading with his verbatim approval.)

**CHAIN DISCIPLINE.** This file is one link in the `/skill-builder` chain. Run it top to bottom. Your
ONLY exit is the NEXT pointer at the foot. Do not read ahead into another phase file. Do not produce
outputs this file doesn't ask for.

**⛔ NAMING RULE (§0, L3).** Always `BUILDER PHASE 4`.

**ROLE.** **PHASE OUTCOME:** the human is handed every tension in the complete spec, each with a
recommended resolution, and rules by exception.

**⭐ THE POSTURE IS THE POINT.** The four readers are critics, never authors — *"it's not making a
decision, it's actually looking for TENSIONS."* Run the swarm over the WHOLE spec, ONCE, not
phase-by-phase (§2's horizontal-by-altitude rule).

**MECHANICS, settled by the first real run (2026-08-05) — apply these while executing the steps below:**
- All four readers run **BLIND from each other, in PARALLEL, in ONE pass**; CHRONOLOGY then gets a
  cheap SECOND look with the other three's findings in hand (not a re-run — a sweep for what it
  structurally could not reach alone).
- They read the **SPEC and the CODE** — spec-versus-reality is where the valuable findings live.
- **The bar: surface a tension only where two parts would produce DIFFERENT WORK**, and say plainly
  when nothing clears it.
- Spawn readers **sonnet, read-only, UNNAMED** — a named agent's final report is discarded by this
  harness (measured: 249 named spawns → 0 payloads; 1,714 unnamed → 1,714).
- **Advisory, never blocking** — the human always overrides.
- ⚠ **A reader can be confidently wrong** — verify every finding against the source before it reaches
  the human.

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

⭐ **IN THIS PHASE the readers hunt what is MISSING from the derived spec**, not only what is wrong in
it. A spec derived from someone else's shipped skill is every line an inference about their intent, so
it needs the readers more than a dictated one does. **This block sits ABOVE the four charges
deliberately — a reader spawned before the posture is read cannot carry it.**

⛔ **This changes nothing about the step ladder below** — same steps, same order, same forks. The ladder
is HARD-locked; only the human may change it. This block is posture, not a step.

---

## THE FOUR READERS — spawn per SPEC §6a, one lens each, blind to one another

**🖥 PRESENTATION reader.** Is a frightened beginner taught, guided AND ORIENTED at every screen — do
they know where they are, how much is left, why they're being asked this, and that editing is allowed?
**Also checks subject–verb–object agreement in every human-facing sentence** — no title-then-dash-then-
fragment, no dangling reference. This is named a MAJOR failure mode (owner, 2026-08-06).

**⚙️ BUSINESS-LOGIC reader — owns ALL processing of information.** How are code and LLM knowledge
integrated, and what are the SEAMS between them; does the spec abide by the skills SOP for integrating
LLM and code. Also, first-class, not an afterthought:
- **Skill-to-skill handoffs** — when one skill calls another as a sub-process, is the handoff actually
  possible between the two.
- **Any math is done by Python, never by the model** — confirm code performs every calculation.
- **Every transformation of information** — what shape goes in, what shape comes out, what happens to
  anything that fits neither.

**💾 DATA reader — information IN, information OUT, and the prompts.**
- **COMING IN:** does the source the skill reads from exist, and is the data in the format the skill
  needs.
- **GOING OUT:** after logic and the human have transformed it, where does it go — where is it
  persisted.
- **THE PROMPTS (§8g):** does each phase have one, where is it stored, is it scoped to that phase alone
  with no leak about later ones, and is it tuned to that phase's desired outcome. ⭐ Applied to this very
  skill: `prompts/phase-1.md` … `phase-6.md` all **EXIST** and were grepped for later-phase leaks with
  zero hits. *(Corrected 2026-08-08: this bullet read "a `prompts/` folder that does not yet exist" and
  told this reader to surface that gap **on every future run until it is built** — written before
  `1353465` shipped the library, never revisited. All six drivers carried the same stale claim in their
  `N.0` steps; this one was worded differently and survived the first sweep.)*

**⏱ CHRONOLOGY reader — one, not per-tier; the human's stopwatch walking the whole thing end to end.**
1. Is anything in the wrong order — used before it's produced, or merely later than optimal?
2. Could any of this run in PARALLEL to make it shorter?
3. How long will this take the human, in felt duration?
4. Are sub-agents / background agents / fan-out used the way `/build`'s own doctrine says?
5. ⭐ The tough questions nobody else is charged to ask: could phases consolidate? Are there more phases
   than the outcomes need? Are steps repetitive enough to merge? Is a step doing more than one thing?
   **Only this reader has a mandate to say the whole shape is too big.**

---

## THE LOCKED STEPS

├ 🤖 💾 **4.0** Fetch THIS phase's own prompt from the prompt library (`.claude/skills/skill-builder/prompts/
phase-4.md`) and run scoped to it (§8g).
⛔ **If that file is missing, STOP and say so plainly** — never improvise phase-scoped prompt text and present it as though it came from the library.

├ 🤖 💾 **4.1** Assemble the COMPLETE spec — every phase, every step, the outcomes, and the target
skill's own files if any already exist — because a reader given fragments finds fragment-sized problems.

├ 🤖 ⚙️ **4.2** Send out four readers AT ONCE, BLIND to each other, each with one lens and no authority
to decide anything. Their charges are the four readers section above.

├ 🤖 ⚙️ **4.3** The readers read the SPEC and the CODE, because the most valuable findings are the ones
where the two disagree.

├ 🤖 ⚙️ **4.4** After the first three report, give the CHRONOLOGY reader a second, cheap look with their
findings in hand — not a re-run, but a sweep for the ordering problems it could not reach blind.

├ 🤖 ⚙️ **4.5** RANK every finding rather than discarding any of it. Findings **TWO OR MORE READERS
FOUND** go at the top, then single-reader findings that would change real work, then the rest. ⛔
**Nothing is thrown away** — the tokens are already spent, you read them all, and a finding one reader
saw alone can still be the real one.

├ 🤖 ⚙️ **4.6** Check every surviving finding against the source before the human sees it — a reader can
be confidently wrong (one quoted a stale docstring for a field that had already been demoed rendering
that same evening).

├ 🤖 🖥 **4.7** Show the tensions, each with its own recommended fix, so the human rules by exception
instead of solving problems. Say how many were found and how many rejected, and teach what a tension
is — a place where two parts of the plan disagree, not a bug.
**THE SCREEN ENDS WITH: A — work through these. B — none of these change anything, move on.**
⚠ **No verbatim PRESENTATION block is supplied in the spec for this screen** (§8's four-move opening
— map, what came before, what's now-and-why, then the questions — still governs the shape; §8's ban on
tables/walls-of-bold/boxes still applies). Do not invent one and mark it "verbatim" — build it from the
opening-moves doctrine instead.

├ 🙋 🤝 **4.8** ⑂ **THE FORK.** `→ CODE (A|B)`
```bash
python3 "$ROOT/.claude/skills/skill-builder/scripts/fork.py" "<the human's raw answer>"
```
　· **A → the human rules on each tension** (accept the fix, reject it, or decide it differently)
**→ CONTINUE TO 4.9.**
　· **B → nothing is adopted, the phase closes → SKIP TO 4.10.**
⛔ An answer that is neither breaks loudly and re-asks.

├ 🤖 ⚙️ **4.9** Apply the accepted fixes, and **where a fix changes what a phase is for**, say so and
reopen that phase's "done" back in BUILDER PHASE 2 rather than quietly editing around it.

├ 🤖 💾 **4.10** Write the outcome into the brief: what was found, what was adopted, and **what was
rejected and why**. The rejections matter as much as the fixes — an unrecorded rejection gets
re-proposed by the next reader who looks.

└ ✅ **Done when** every surviving tension has been ruled on by the human, the adopted fixes are in the
spec, and the rejected ones are on the record with their reasons.

---

## STOP-CHECK + NEXT

**Done-check:** every surviving tension has a human ruling AND adopted fixes are written into the spec
AND rejections are recorded with reasons. ⛔ **DO NOT BUILD BEFORE THE SWARM** — a spec that skipped this
phase and went straight to a build cost a full window once (§2).

Tell the human plainly what closed here and that the chain moves from planning into the actual build
next.

**NEXT:** `5-build.md` — BUILDER PHASE 5, build it (the chain).
