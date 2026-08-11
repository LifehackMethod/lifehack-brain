# BUILDER PHASE 5 — BUILD IT (the chain)

> **Source:** `.claude/skills/skill-builder/SPEC.md` §7. The step list below is locked — owner, 2026-08-06:
> *"approve this and push to the spec."* (Ratified the same way as L7/L14, no separate §1a letter.)
> **THE ORDER IS L2, HARD-locked (§1a):** spec → SOP check → `/autoplan` → `/build` → tester → live run.

**CHAIN DISCIPLINE.** This file is one link in the `/skill-builder` chain. Run it top to bottom. Your
ONLY exit is the NEXT pointer at the foot. Do not read ahead into another phase file. Do not produce
outputs this file doesn't ask for.

**⛔ NAMING RULE (§0, L3).** Always `BUILDER PHASE 5`.

**ROLE.** **PHASE OUTCOME:** the skill exists on disk, planned against the SOP, built to the plan, and
tested — a 90–95% finished skill with three-tier architecture and a spec worth keeping, handed to the
human to run.

**ONE JOB PER TOOL.** You INVOKE `/autoplan`, `/build`, and the tester; you never re-implement planning,
building, or testing yourself.

**THE SOP IS ONE FILE, THREE NAMED SECTIONS** (`system/sops/skill-building-sop.md`): **BEST PRACTICES**
(what to do — already there, needs an index not a rewrite), **⭐ DO NOT BUILD** (what was tried and
failed — the owner named this the most important of the three, and it is sparsely populated today), **THE
PARTS LIBRARY** (tools that already exist, each with its real path and whether anything calls it).
⛔ Do not split these into separate files — the owner ruled that out explicitly.

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

⭐ **IN THIS PHASE the draft is the SHIPPED CODE AND PROSE.** The build fills the gaps the chain found; it does not rewrite working parts. A rewrite of something that already works is scope this door never authorised.

⛔ **This changes nothing about the step ladder below** — same steps, same order, same forks. The ladder
is HARD-locked; only the human may change it. This block is posture, not a step.

---

## THE LOCKED STEPS

├ 🤖 💾 **5.0** Fetch THIS phase's own prompt from the prompt library (`.claude/skills/skill-builder/prompts/
phase-5.md`) and run scoped to it (§8g).
⛔ **If that file is missing, STOP and say so plainly** — never improvise phase-scoped prompt text and present it as though it came from the library.

├ 🤖 💾 **5.1** Read the complete spec — every phase, every step, every outcome — because the whole
thing is about to be handed to another tool, and a gap here becomes a gap in the build.

├ 🤖 ⚙️ **5.2** Check the spec against the skills SOP **BEFORE ANYTHING IS PLANNED**: what the SOP
requires, and — the cheaper half — what the **DO-NOT-BUILD** section says was already tried and failed.
There is no point spending tokens building something the rules already rule out.
*Available tooling for this check:* `system/parts/order_lint.py` with
`.claude/skills/skill-builder/scripts/order-rules.json` enforces positional SOP requirements (e.g. Purpose
before Rails) mechanically where a rule is defined — use it where it applies; where the SOP requirement
has no matching rule yet, check it by reading.

├ 🤖 🖥 **5.3** Show what the check found, each item with a recommended fix, or say plainly that the
spec is clean.
**THE SCREEN ENDS WITH: A — fix these first. B — proceed as it stands.**
⚠ **No verbatim PRESENTATION block is supplied in the spec for this screen** — build it from §8's
four-move opening and format rules; do not invent one and label it "verbatim."

├ 🙋 🤝 **5.4** ⑂ **THE FORK.** `→ CODE (A|B)`
```bash
python3 .claude/skills/skill-builder/scripts/fork.py "<the human's raw answer>"
```
　· **A → amend the spec and re-check → BACK TO 5.2.**
　· **B → proceed → CONTINUE TO 5.5.**
⛔ Neither answer breaks loudly and re-asks.

├ 🤖 ⚙️ **5.5** Invoke `/autoplan`, **PASSING AN INJECTED PROMPT THAT POINTS IT AT THE SOP BY PATH**
(`system/sops/skill-building-sop.md`), so the plan is built against the rules rather than against
whatever the planner remembers. ⛔ Not a hope that `/autoplan` remembers the SOP — an explicit pointer,
passed at invocation.

├ 🤖 ⚙️ **5.6** Confirm the returned plan **ACTUALLY CITES** the SOP. A plan that cites nothing did not
check anything — repeat the invocation rather than accept it.

**RUNNABLE — the S1 seam check (SPEC.md §8h):**
```bash
python3 system/parts/section_present.py \
  --rules .claude/skills/skill-builder/scripts/seam-rules.json \
  --artifact "<path to the plan file /autoplan just returned>"
```
　· exit `0` → **PLAN-CITES-SOP** — `skill-building-sop.md` literally appears in the returned plan;
proceed.
　· exit `1` → **PLAN-NO-CITATION** — the marker never appears anywhere in the plan artifact; go BACK TO
5.5, do not accept the plan as-is.
　· `/autoplan` unreachable, wrote no file, or returned empty (nothing to point `--artifact` at) →
**NO-PLAN** — the no-outcome member (LAW 1b: an unreachable model is not a clean result); treat exactly
like `PLAN-NO-CITATION`, never like a pass.
The bounded set for this seam is exactly these three, per SPEC.md §8h row S1:
`PLAN-CITES-SOP · PLAN-NO-CITATION · NO-PLAN`.

├ 🤖 🖥 **5.7** Show the plan in plain language — what will be built, in what order, and where the human
will be stopped.
**THE SCREEN ENDS WITH: A — change something. B — build it.**
⚠ **No verbatim PRESENTATION block is supplied in the spec for this screen** — same note as `5.3`.

├ 🙋 🤝 **5.8** ⑂ **THE FORK.** `→ CODE (A|B)`
```bash
python3 .claude/skills/skill-builder/scripts/fork.py "<the human's raw answer>"
```
　· **A → the human says what to change, the plan is redone → BACK TO 5.5.**
　· **B → CONTINUE TO 5.9.**
⛔ Neither answer breaks loudly and re-asks.

├ 🤖 ⚙️ **5.9** Invoke `/build`, which executes the plan under the existing build rules (Phase → Feature
→ Task, Execute → Verify → ✅) and closes honestly — naming every task it did NOT complete, out loud, at
the top.

├ 🤖 ⚙️ **5.10** Invoke the tester.
⚠ **`/skill-tester` DOES NOT EXIST** — ⛔ no `.claude/skills/*test*` directory ships here, and it is
**ruled CUT** (owner, 2026-08-07). `NO-TESTER-RAN` is the **LIVE value today, not a fallback**.
Today this runs the target skill's own `verify-*.sh`. ⛔ `system/tools/conformance-lab/` — the donor's
other tester — deliberately does not ship: measured, its rule registry names no existing skill as a
subject, so it has no door for "test skill X"; `run_tester.sh` reports its absence and carries on.
**If nothing testable runs, say so plainly** — an untested skill is never recorded as a passing one.

**RUNNABLE — the S3 seam check (SPEC.md §8h):**
```bash
bash .claude/skills/skill-builder/scripts/run_tester.sh "<path to the built skill's directory>"
```
　· prints exactly one verdict line — `TESTER: PASSED` · `TESTER: FAILED` · `TESTER: NO-TESTER-RAN` —
the closed three-member set for this seam, then a short note underneath of what it searched and what it
found or didn't.
　· exit `0` = PASSED, `1` = FAILED, `2` = NO-TESTER-RAN.
`NO-TESTER-RAN` is a **legitimate outcome, not a failure of this step** — record it plainly in `5.11`/
`5.12` rather than smoothing it into a pass.

├ 🤖 🖥 **5.11** Show what happened: what was built, what the tester found, and **what was NOT built and
why** — the unfinished parts first, not buried.

├ 🤖 💾 **5.12** Write all of it into the brief: the plan, the build's honest close, the tester's verdict
or its absence, and anything left owed.

└ ✅ **Done when** the skill exists on disk, the plan it was built from cites the SOP, the build's close
is recorded with every gap named, and the tester's verdict — or the fact that no tester ran — is
written.

---

⭐ **THE BUILDER MUST KNOW WHAT NOT TO DO, NOT ONLY WHAT TO DO** (the owner's emphasis). Step `5.2`'s
DO-NOT-BUILD check is not decoration — it is the cheapest gate in this phase.

---

## STOP-CHECK + NEXT

**Done-check:** the skill is on disk AND the plan cites the SOP AND `/build` closed honestly (gaps named
at the top, not buried) AND the tester's verdict — or its explicit absence — is recorded in the brief.
⛔ Never report a tester ran when nothing ran.

Tell the human plainly what got built, what didn't, and that the next step is running it for real, in a
fresh session.

**NEXT:** `6-live-run.md` — BUILDER PHASE 6, the live run and the loop back.
