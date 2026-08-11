---
id: system-playbook-architecture-planning-sop
title: Scoping & Architecture SOP — idea → vetted readiness → a plan-request handoff (NOT the plan)
record_type: playbook
created_at: 2026-06-15
updated_at: 2026-06-23
status: active
authority: user
---

# Scoping & Architecture SOP

> The **scoping front-end**: take a fuzzy "build X / fix this system" into a reviewed, pre-mortem-tested **scope +
> architecture doc-set (TRD / SAD)**, and **END by emitting a HANDOFF PROMPT** — which you paste into plan mode and
> hit return. **This SOP does NOT write the plan and does NOT build anything.** Plan mode builds the plan from the
> handoff; execution then follows **`build-sop.md`**. Scale the rigor to the stakes. Distilled from
> a real architecture project (2026-06-15), reviewed by its own council.

> ⓘ **WHAT THIS SOP CALLS FOR THAT IS NOT HERE YET.** Every stage below is runnable by hand; three of
> them name a command that has not landed, and two pointers name files that never will. Stated up front
> so a reader meets the gap here rather than at stage 4.
>
> - ⏳ `/advisory-council` — **lands in Phase 3.** It is the engine stages 1, 4 and 6 are written around.
>   Until it does, run those stages as what they are: pose the question to two or three independent
>   readings, keep them from seeing each other, then chair the disagreement yourself.
> - ⏳ `/websearch` — **lands in Phase 3.** The load-bearing fork below wants the other one anyway.
> - ⛔ `/scope` — **never built anywhere.** The line below is an old TODO, kept because
>   the wish is legitimate and the reader should not go hunting for a loader that has never existed.
> - ⛔ `system/canon-purpose-map.md` — **not a shipped file.** Where a document lives is recorded in your
>   own notes folder, not in this repository.

## Core principle — SCALE THE RIGOR TO THE STAKES
Pick the tier by **blast radius + reversibility + unknowns**, then run only the stages that tier needs. **Every
tier ends the same way: at the Stage-8 handoff prompt.**

| Tier | When | Stages (all end at the handoff) |
|---|---|---|
| **1 · Quick** | small, reversible, known files (a bugfix) | **0** (read) → **8** (a one-line handoff: "make a small Phase/Feature/Task plan for X") + a 30-sec self-pre-mortem. **Often you can skip this SOP and just do it.** |
| **2 · Standard** | a feature / module / endpoint | **0** → **1-light** (1 reviewer, OR a **capped** council: ≤3 lenses · one pass · no re-run) → **2+3-light** (scope folded into a one-page design note) → **4** (quick pre-mortem) → **7-inline** (a targeted read) → **8** handoff. |
| **3 · Load-bearing** | multi-subsystem · hard-to-reverse · a migration · a new architecture | **full 0→7, looping 4↔6 until sign-off → 8** handoff. (= the this system rebuild.) |

**The default failure is over-doing a Tier-1 or under-doing a Tier-3.** When unsure: *"if this goes wrong, how
hard is it to undo?"* Hard-to-undo → go up a tier.

---

## ★★ ALWAYS — the plan spec the HANDOFF must carry (not a format this SOP produces)
**This SOP never writes a plan — but its handoff prompt MUST order plan mode to build one in a fixed shape.** So
every handoff prompt this SOP emits **REQUIRES the downstream plan to come back as:**
- **A `FRAME` block at the very top** — desired outcome · success criteria · constraints · out-of-scope (one line each is fine). The human-only frame, approved ONCE up front: it's what lets execution run autonomously without re-asking, and it satisfies `project-manager`'s Frame-intake gate so the brief is treated as authoritative.
- **`Phase → Feature → Task`**, and
- **every task = `Execute → Verify & test → mark-complete (- [ ])`** — a task isn't done until its Verify passes, and the **Verify is a *runnable* check** (a command / a rendered output to look at), not "looks done."
- **each task gear-tagged** — gear-1 (single-thread) · gear-2 (background sub-agent) · gear-3 (Agent-Team wave). **The tag is a HINT, not a command:** `/build` re-decides the gear per task from the work's shape, so write each task to *read as standalone* (legible independence + done-criterion + embedded context) — that, not the label, is what gets it fanned out. **Default to gear-2** for decided, self-contained work; **gear-3 only when the user has said "use agent teams" / "team build"** — it's opt-in (~7× tokens). Gears: `build-conductor-sop.md`.
- **each phase LANE-TAGGED — which tasks are `independent` (launch together) and which are `gated` (and by what).** Gear tags say *how* a task runs; lanes say *when*. **The gate rule: one task gates another only if it writes a file the other reads or writes, or the other consumes its output — nothing else. Independence is the assumption; a gate needs a stated reason.** Without this a plan executes in single file even where nothing blocks it, and the wall-clock loss is invisible because no one ever sees the build it could have been. Name the file each task writes so the gate is checkable, not a judgment the executor has to re-make. Lanes: `skills/autoplan/SKILL.md` → "Lanes"; execution: `skills/build/SKILL.md` → "Delegation is the default."
- **a named "safe-halt" section** (a *checkable* "pause only when X is green," not a vibe). It is ADDITIVE to `/build`'s always-on stops, and **must explicitly list human-side Google writes (Sheets / Calendar / Gmail)** — `/build` does NOT auto-pause for those — alongside the genuinely irreversible / destructive, a failed verify, and any plan-changing decision.
- **a deferred list** — each item tagged **TODO** (still viable → files to the brief's OPEN LOOPS) or **DEAD-END** (ruled out → files to DEAD ENDS), so `project-manager` mirrors it without rework (it has no generic "deferred" slot).
- **NO SILENT DEMOTION — a `⚠ CUT FROM THIS BUILD` block, directly under the FRAME, separate from the deferred list.** The deferred list above is for ideas the *process* explored and set aside. Anything the *stakeholder explicitly named as to-build* that is NOT in the executable Phase▸Feature▸Task body is a different, louder category: it must appear in a top-of-plan `⚠ CUT FROM THIS BUILD` block — each item stating what it is · why it's proposed for deferral · what's lost · flagged **needs explicit OK**. **Plan-approval is NOT cut-approval** (surface each cut as its own decision — the `/save` rule "surface conflicts to the human, never auto-resolve," applied to scope); **default is keep-it-in** (deferral needs an affirmative reason AND sign-off, never the reverse); an approved cut files to OPEN LOOPS so it stays visible and a build that skips it cannot read as "done." Before emitting, reconcile every named build-item + the FRAME's desired outcome against the body — each maps to a Task or lands in this block; nothing vanishes.

- **★ A TASK MAY CITE A RULING ONLY WHERE THAT RULING STATES ITS DATE AND ITS AUTHOR. "See §X" is not a
  citation if §X is still asking the question.** (2026-08-05, T18.8.) A plan task read *"⚖ RULED
  2026-08-04 — see §18.8d"* and authorised re-drawing a boundary that two shipped element files assert
  about themselves. **§18.8d was headed "the operator's call", closed with "Lead's read: it MOVES", and ended
  "⚠ Surfacing rather than deciding" — it recorded an OPEN QUESTION.** Cross-checked: the Story Log, the
  brief's Current State and the scratchpad all failed to mention any such ruling. **It did not exist.**
  ★ **This is the INVERSE of the familiar staleness bug and it is the more dangerous direction:** the
  usual failure leaves a task *asking* for a decision already given, which wastes the human's time; this
  one *asserts* a decision never given, which **spends the human's authority.** Caught at check-in only
  because someone opened the cited section instead of trusting the citation. **How to apply:** when a task
  claims a ruling, the cited location must carry **the verdict, the date, and who gave it** — all three.
  A pointer to a section that still poses the question is a forward reference, not evidence. And when you
  RECORD a ruling, write those three facts at the site, so the next reader can verify the citation without
  reconstructing the conversation.

**No flat plans, ever.** This is a demand you hand to plan mode — paste it in, hit return, plan mode obeys it.

---

## The stages (domain-agnostic; each names its ARTIFACT + its GATE)

**Stage 0 — Understand the ground truth (never design blind).**
Inventory the *real* current system. At Tier 3, fan out **read-only auditors by concern-cluster (NOT per file)**,
then **verify the map with a 2nd pass** — undercounting is the default failure. *(Reframed this system "rebuild" →
"ratify+enforce" once the map showed ~60–70% already converged.)*
→ Artifact: an as-is map (+ verification addendum at Tier 3). → Gate: the map is verified, not first-pass.

**Stage 1 — Independent review / council (Diverge → Argue → Converge).**
Scale the room: 1 reviewer (Tier 2, capped) → 4–6 **domain-advisor lenses** (Tier 3). Advisors run **blind,
isolated, in parallel** — *never a live debate* (it collapses into agreement). The **chair synthesizes**; a lone
self-grading agent anchors on its first idea — N blind lenses catch what it can't. The **stakeholder lens is the
FLOOR (a KISS veto), not a vote.**
→ Sub-rule: at a **load-bearing fork (≥2 viable approaches with different reversibility), STOP and `/research`**
(multi-source convergence map — *not* `/websearch`, which is for a single fact).
→ Artifact: ratified decisions. → **Gate:** the chair issues a written synthesis that **closes or escalates each
open question**; a closed item doesn't reopen without new information.

> **★ THE ENGINE — `/advisory-council` (powers Stages 1, 4 AND 6).** One reusable skill: blind, isolated,
> parallel advisors over a **swappable roster cartridge** (built ONCE per project, reused across all three
> stages), chaired diverge→argue→converge. **Stage 1** runs it on the open questions; **Stage 4 (pre-mortem) is
> the same council in "what did we miss" mode**; **Stage 6 re-runs it** to verify. Each advisor = a sharp *lens*
> (Domain/Catches/Refuses/Bias), persona fenced from the reasoning. **Protocol:** every advisor returns the SAME
> fixed schema (strengths · gaps · grade · veto) — freeform defeats chair synthesis. An advisor that returns
> empty / stalls at zero tokens has **hung pre-spawn** → re-spawn once, then do it inline. Library:
> `<your notes>/councils/<slug>/council.md` + a registry beside it.

**Stage 2 — Decide + scope: the WHAT, in ONE findable doc.**
Fold every decided-for/against + the fix-list into a **single, specifically-named** scope doc — no duplication,
no generic names. *(Tier 2: fold this into the Stage-3 design note.)* At Tier 3, audit it for faithfulness with
independent read-only agents. **Scope lives in a maintained doc, NOT plan mode.**
→ Artifact: the scope (WHAT's in/out + the fix-list). → Gate: a faithfulness check finds no dropped decision.

**Stage 3 — Design: the HOW (the TRD / SAD).**
Tier 2: a one-page design note. Tier 3: a **SAD** — fan out **drafting** agents (one per subsystem) → chair-
assemble. Capture the structure, the **named boundaries/ports**, the one contract, the **ADRs** (the irreversible
decisions live here, not Stage 2), and the **conformance rules** (testable fitness functions). Keep it lean.
→ Artifact: the design doc-set (TRD/SAD). → Gate: every boundary is named; every rule has a test.

**Stage 4 — Pre-mortem (the highest-value gate; the one most people skip).**
**Run `/advisory-council` in pre-mortem mode** (same roster, adversarial-completeness charge): *"Assume the build
derailed halfway — what major part did we miss?"* **Catches silent omissions a forward review never does.**
*(Ours caught the design covered the plumbing ~40% and missed ~60% of the operational surface — before any code.)*
→ Artifact: a verdict (READY / NOT-YET) + a clustered punch-list.

**Stage 5 — Revise (close the punch-list).**
Cluster the gaps; **add** the missing, **specify** the under-specified, **fix** contradictions. **Surface the
genuine forks to the stakeholder — don't problem-solve them for him.**
→ Artifact: the revised design.

**Stage 6 — Re-review (verify the revision; LOOP with 5 until sign-off).**
**Re-run the same `/advisory-council`**, tighter: *did the revision close each condition + break nothing new?* The
**stakeholder makes the big calls** (e.g. overriding the floor's overbuild veto — the stakeholder owns the trade).
→ **Gate / loop-exit:** sign-off = the council issues a **READY verdict** AND the **stakeholder confirms no
overrides outstanding**. Until both, loop 5↔6.

**Stage 7 — Recon (verify-don't-assert) — the last *work* stage.**
Pin the **exact** current-state facts the downstream plan will need. *Tier 2: an inline targeted read (no agents).
Tier 3: a fan-out by concern-cluster.* **Replace every "likely / UNKNOWN" with a fact** *(turned "3 violations"
into the real 140)*. → **Gate:** an unresolvable UNKNOWN is a **STOP** — surface to the user; **never let an
INFERRED value travel into the handoff as a fact.**
→ Artifact: a **fact-sheet** (the handoff carries it downstream).

**Stage 8 — THE HANDOFF (this SOP's final output).**
You are READY. Emit ONE **handoff prompt** — the thing you paste into plan mode and hit return. It bundles:
1. **Pointers** to the vetted scope (Stage 2) + design/TRD/SAD (Stage 3) + the recon **fact-sheet** (Stage 7).
2. **The required plan spec** (the `★★ ALWAYS` block): a **FRAME block** up top, then **Phase → Feature → Task**,
   every task **Execute → Verify → mark-complete** + **gear-tagged** (gear-2 default; gear-3 only on "use agent
   teams"), with a **safe-halt section** (incl. human-side Google writes) + the **deferred list** (TODO / DEAD-END).
3. The one-line **build goal** + any stakeholder constraints still open.
**That's where this SOP ENDS.** Paste → return → plan mode takes it from here.
→ Artifact: the handoff prompt. → Gate: it names scope+design+facts AND carries the required plan spec.

---

## Downstream (NOT part of this SOP — for orientation only)
Plan mode builds the plan from the handoff (in the required Phase→Feature→Task shape). **Execution** then follows
**`build-sop.md`** (loaded by `/build`): backup-FIRST (halt if the backup can't be verified), prove-cheap-before-
expensive, prove-live-once-before-automating, human-in-the-loop in the main session.

## The doctrine (holds across every scoping stage)
- **Map before you design; verify-don't-assert** (Stages 0/7) — an unresolvable UNKNOWN is a STOP, never a guess.
- **Reviewers run blind / isolated / parallel → a chair synthesizes** — live debate breeds sycophancy; a lone agent anchors on its first idea; advisors return ONE fixed schema.
- **The stakeholder is the floor, not a vote** — minimalism can veto consensus, but the stakeholder owns the trade and can override the floor.
- **Separate stakeholder OUTCOMES (the human sets) from technical DECISIONS (the process decides).** In an exploratory phase **stay non-prescriptive** — surface options, route decisions to the council / the stakeholder; presenting a leaning as "locked" is the failure.
- **`/research` the load-bearing forks** (≥2 viable approaches, different reversibility) — don't answer from training.
- **One findable doc per purpose** — no duplication, no generic names; scope/design in maintained docs, NOT plan mode. **`ExitPlanMode` is for the downstream CODE-implementation plan, never for this scoping work** — here you edit the doc + confirm in text.
- **Pre-mortem before you commit; iterate 5↔6 until READY.**
- **Agents:** exploration subagents = **read-only**; drafting subagents write to **isolated scratch only** (the chair assembles). Fan out only when (a) the reads are genuinely parallel + non-trivial, OR (b) isolation is the point (blind review) — else inline. Subagents run **Sonnet** — except the `/advisory-council` engine this SOP invokes (Stages 1/4/6), whose advisors run **opus** (the sanctioned exception); the SOP's own exploration/drafting subagents stay sonnet.
- **Right-size:** YAGNI for implementations, rigor for boundaries. For a single-user LLM/Claude harness the right-sized spine is **three-tier + thin-AI inside the business tier + one narrow data seam** (not a full ports framework).

---

## Worked example — a Tier-3 architecture project
AS-IS map (+verify) → 6-lens council (`/research`-validated) → one scope doc (+faithfulness audit) → the SAD
(TRD/SAD) → pre-mortem (NOT-YET, ~60% gap) → revise → re-pre-mortem (→ stakeholder override → **6/6 READY**) →
recon (fact-sheet) → **a handoff prompt** → *[pasted into plan mode → the plan built there →
executed per `build-sop.md`]* (the bracketed part is downstream, not this SOP).

*Registered: `system/canon-purpose-map.md` (`system/sops/`). Downstream companion: `build-sop.md` (execution). Engine: `/advisory-council`. TODO: wire a `/scope` loader.*
