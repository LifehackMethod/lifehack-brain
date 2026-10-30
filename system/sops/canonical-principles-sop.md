---
id: root-2026-09-02-canonical-principles
title: "Canonical principles — the merged canon"  # v2 — IN FORCE in the V2 sandbox (2026-10-29); main keeps v1
record_type: canon
desk: root
topic: [system-architecture, llm-engineering]
created_at: 2026-09-02
updated_at: 2026-09-02
status: active
authority: user
confidence: CONFIRMED
tier: canon
---

# Canonical principles — the merged canon — v2 (in force in the V2 sandbox)

> **STATUS (2026-10-29, Enver):** **This v2 is the canon in force for the V2 sandbox** (the V2 sandbox) — the system we are operating in. It applies only there. Main keeps v1 (the v1 canon collection) as its canon and as the backup until V2 ships.
>
> ~~**STATUS (v2 DRAFT, 2026-10-28):** draft for the V2 sandbox. v1 in the notes-side canon collection is the authority and the backup until Enver validates and swaps; no v1 text is deleted here — every change is a strike (`~~`) plus a `v2` note beneath it, or a new bullet. Frontmatter title carries the same suffix as a YAML comment (the quoted v1 title is kept intact).~~ *(Struck 2026-10-29: the strike-plus-note editing method still applies; "draft / not yet in force" no longer does.)*

> ## TESTING ASKS "DOES IT WORK?" SECURITY ASKS "WHAT HAPPENS WHEN IT DOESN'T?"
> *(The centering frame. Enver's, sharpened and adopted 2026-09-11. A near-copy leads `system/sops/skill-building-sop.md`; per §12.b the two are kept in agreement by a quarterly human audit, not by construction. ⚠ **That audit is a thing someone must REMEMBER — so by §0.1's own test it is a PREFERENCE, not a layer, and it will drift.** Chosen knowingly anyway: a sync script is one more thing that breaks silently and then needs its own alarm. **Stated so the weakness is owned rather than discovered.**)*
>
> **Use the first on code. Use the second on anything a model decides.** Code is deterministic — one run settles it, and a failure is a bug you fix. A model is not: the same input can produce a different move, so "does it work" has no answer, only a rate. **You cannot patch a model into compliance.** So stop trying to eliminate the failure and design what catches it — **a stochastic environment needs a security architecture, not a test suite.**
>
> **Borrow security's architecture, never its threat model.** Borrow: no perfect control · every layer eventually fails · test the *combination*, since a stack whose layers each pass alone can still fail as a stack · **never claim zero — state what is covered and what remains.** Don't borrow the attacker: nothing is breaking in. What you guard is already inside, holds your tools, forgets between turns, and can reason its way past a rule it understands. *(Exception: anything read from outside can be authored against you — full adversarial posture there.)*
>
> **⇒ You are buying FRICTION, not certainty.** Every control raises the cost of going wrong without ever making it impossible, **and tools differ enormously in how much friction they buy** — a check that fires before the model is consulted is a wall; a line of prose is a speed bump. **Stacked layers compound friction, but only when they fail differently** — three speed bumps in a row is still one speed bump.
> **⇒ Progress is coverage and remainder, never pass/fail.** "Nineteen problems, none solved" is a testing scoreboard that stalls forever; *"this much caught, this much left"* is actionable.
> **⇒ A real layer depends on neither memory nor agreement** — it acts without consulting the model. If the model can talk past it, it's a preference, not a layer. Preferences are cheap and buy real friction; keep them, never count them as protection.
> **⇒ Depth is set by blast radius and reversibility, not importance** — irreversible → stack; **reversible and cheap → one deterministic check, then STOP.** ⚠ And blast radius is knowable at DESIGN time, so **a new irreversible action gets its stack up front**; the brake below governs *adding to* a control set that already exists, never the first build.
>
> ⛔ **This is a minimal harness on Pareto's principle, and security culture adds controls forever.** Friction costs you too — every layer is paid on every run. **Add one because an incident demanded it, never because this frame permits it.** ⚠ **That governs ADDING a control. It does not govern checking that one you already have still works** — a detector that went dark is not a new layer, it is an existing layer you have stopped owning, and confirming it still fires is **maintenance, never addition.**
>
> *Detail: §0.1 below. Evidence: `state/projects/canonical-housecleaning/records/2026-09-11-layered-enforcement-composition.md`.* ⛔ owner's notes

> ## THE LAYERS OF FRICTION — compliance is the center of the Venn diagram
> *(Enver, 2026-10-29. Added in the V2 sandbox.)*
>
> **Say "friction," not "enforcement."** "Enforcement" makes an LLM think of perfect control, and nothing
> here is perfect. Every layer only makes going wrong cost more than going right. Older wording in this
> file that says "enforcement" means friction, and it gets updated as it's touched.
>
> **The layers are overlapping circles, like a Venn diagram, not a stack.** Each circle covers part of the
> risk. Where the circles overlap, a mistake has to get past several of them at once, and they count as
> separate layers only if they fail in different ways. **The small area where all the circles overlap —
> the bullseye at the center — is compliance.** The more something matters, the more circles we bring to
> overlap on it.
>
> **The circles:**
> - **Hooks** — stop one action before it happens.
> - **Checks** — refuse bad work when it's saved, committed or installed.
> - **The runner** — holds the order of steps, so a session can't skip one.
> - **What a session is handed** — the startup brief and the reminders on each prompt.
> - **The map, manual and elements** — what the system is meant to do, and what it actually does.
> - **SOPs and canon** — the rules, and the reasons behind them.
> - **Observation** — checks that run later and show whether the friction actually held.
> - **Habit / hygiene — the human's part.** The few things only the person can do: open sessions from
>   the right place, reach for the right skill at the right moment (`/save`, `/checkin`, `/build`),
>   approve proposals. The system is built so this is a small part of the work for most of the value. It
>   is never zero, and it is a circle like any other.
>
> *The figures used elsewhere for the human's share are figures of speech, not targets.*

> **What this is.** The single canonical document. It merges three sources: the 37-principle
> September draft (the v3 draft file), the 54-entry collection in the notes-side canon folder
> (2026-05-30 → 2026-08-25), and the 28 altitude-tagged lines at
> `state/projects/llm-engineering/canon.md`. **Promoted whole by Enver's ruling, 2026-09-02** — lines ⛔ owner's notes
> were not ratified one by one; each carries its tier and pointer so any one can be re-examined alone.
>
> **Not the always-loaded layer.** The session loader reads `<notes>/canon.md` and `desks/*/canon/`
> only. This is a reference shelf, pulled when relevant — which is why length is not a fault here.
>
> **Canon is an OBSERVATION, not a rule.** The coding reflex hardens a true observation into a false
> absolute by bolting on *always* / *never*. Some lines here are rules; canon is not *defined* as
> rules. Contingent truths stay hedged — *tends to · at present · for the most part.*
>
> **The standalone test is the admission gate.** Every line must be understandable and actionable by a
> cold session reading it alone. Precise and efficient, never "short" — the two failure modes are
> CRYPTIC (worse) and BLOAT.
>
> **Two orthogonal axes.** The SECTION says where in the system a line applies. The ALTITUDE TAG —
> `[U]` universal to any LLM · `[H]` any harness around a model · `[T]` this platform — says how far
> the truth travels. No tag means local to this system.
>
> **Three tiers of confidence; an unlabelled claim reads as the highest.**
> **AUTHORITATIVE** — tested here, receipt attached. **WORKING THEORY** — outside research; it has not
> met this system. **RECOMMENDATION** — reasoning only. *Authoritative knowledge carries its receipt
> or it decays back to theory.* A number never measured here is a theory and is labelled one.
>
> **Security and version-specific claims stay lesson-only** — they lose load-bearing caveats when
> compressed and read as complete while being incomplete-to-wrong. Pointers in §14.
>
> **The governing caveat.** Nearly every strong outside source measured a SCORED environment — agents
> rewarded for a number. This system scores nothing; its failure is accidental omission under context
> pressure, not gaming. Chain and attention properties transfer. Anti-gaming machinery may not.

---

> # THE FRAME — read before any line below. ~~Identical text~~ A near-copy of this text sits atop `system/sops/skill-building-sop.md`.
> *(Enver, 2026-09-05. ~~This block is the one place both documents agree by construction.~~ The two copies are kept in agreement
> by a quarterly human audit, not by construction — Enver's ruling 2026-09-06, §12.b.)*
>
> **This is a stochastic environment, not a rules-based one.** Compliance is nudged, layered, and rarely
> guaranteed. **That sentence is the one law in this document.** Everything else is a principle, and its tier
> says how far to trust it.
>
> **Every line carries an evidence tier:**
> **REPRODUCED** — held across multiple blind sessions over time, receipts named ·
> **RESEARCHED** — outside evidence that has not yet met this system ·
> **OBSERVED** — seen here, receipt named, not yet reproduced ·
> **CANDIDATE** — proposed, awaiting a test ·
> **REFINED** — an earlier line changed by evidence; the old text struck, never deleted, with what changed and why.
> *Mapping onto the tags already in this file:* AUTHORITATIVE with several receipts = REPRODUCED; with one = OBSERVED;
> WORKING THEORY = RESEARCHED; RECOMMENDATION = CANDIDATE; §10 RETRACTED = REFINED. New lines use the new words.
>
> For a fix specifically, the same ladder, read from the top: VALIDATED — a designed experiment built the failing state first, and the fix held across blind sessions that were not trying to make it hold · REPRODUCED — observed holding repeatedly in practice, receipts named, no designed experiment yet · OBSERVED — watched holding once, at one site, receipt named · RESEARCHED — the outside world converged on it; it has not been watched holding here · CANDIDATE — proposed, nothing has been watched. A fix line without one of these words is at CANDIDATE.
>
> **A tier without a dated receipt decays one step** (§7.2). **Structural findings** — what a model cannot do by
> construction — earn OBSERVED on one clean case; more cases do not make them truer. **Behavioural findings** — how
> often something happens — need reproduction to move up.
>
> **A rule the MODEL must follow enters this document only at REPRODUCED.** Too many rules, or contradictory ones,
> and the model stops following any (§4.5). **A rule CODE enforces needs no tier** — it does not depend on
> compliance (§4.6). Rules live in code; prose carries principles with their reason.
>
> ~~**Compliance is a stack, not a choice.** Each layer catches what the one above misses; a hook is the scarce top,
> never a substitute for the layers beneath it (§5.20).~~ *(2026-10-30: see "The layers of friction" above, Venn, not a stack)*
>
> **Compliance is the center of the Venn diagram, not a stack.** Each circle of friction covers part of the risk; a hook is the scarce, expensive circle, never a substitute for the cheaper circles around it (§5.20).
>
> **The operating rule under the one law** *(added 2026-09-05 from the failure census, §16 — CANDIDATE as a single
> sentence, since one synthesis wrote it; the modes beneath it are REPRODUCED, except where a mode's own line says it
> entered by Enver's ruling rather than by the census):* **nothing counts as
> existing, done, enforced or true until you have watched it produce an outcome it could not produce if it were
> broken. Build the failing state first.** In 42% of 1,656 recorded failures the system gave the same signal
> whether the thing worked or not. And outside that rule: **look before you build.**
> *Second receipt, from the solutions side (2026-09-05, three readers independently): across the modes, zero fixes held
> durably; every fix that held at all fired unasked, removed the ability rather than asking for a memory, and had been
> watched refusing; every fix that failed was a description the next session had to remember.*
>
> **REFINED 2026-09-06 (Enver's ruling — the heading and the closing clause were prescriptive; the description stays).**
> ~~**Right-sized, or it does not enter** *(Enver, 2026-09-05).* The Lifehack Harness is a minimal harness built on Pareto's
> principle: the most value, compliance and reliability for the least code, rules and structure. The question is never
> "how much can we build" but "how little buys the most." **We are not an enterprise solution.** A remedy that works but
> needs a second system to watch the first is recorded as *likely overbuilt for this harness* — kept, never adopted by
> default.~~
> *(Enver, 2026-09-05; reworded by Enver 2026-09-06.)* The Lifehack Harness is a minimal harness built on Pareto's
> principle: the most value, compliance and reliability for the least code, rules and structure. We are not an enterprise
> solution. A remedy that works but needs large-scale code or enterprise machinery in order to work is likely overbuilt
> for this harness. A large build is not ruled out. It is rare, it is an extenuating circumstance, and when one is
> proposed it is justified to the human in the loop, who decides.
>
> *(Enver, 2026-09-06.)* This is a human-in-the-loop judgment system. The model is a great deal of knowledge with very
> little judgment; the human is a great deal of judgment with far less knowledge; the intelligence is the pairing. The
> human's share of the work should be small — five percent, at most twenty — but never zero. Human-out-of-the-loop
> designs are very rare in this system; the default is human in the loop.

---

## 0. THE ROOT

**Normal code obeys you and you can check it. A model does roughly what you asked and can't tell you
whether it did.** `[U]` That is the whole difference. Five things follow, each *because* of it:

- **Rules become suggestions** — obedience isn't structural.
- **Self-report is worthless** — verification isn't structural.
- **Checking must move outside the model** — inside is unverifiable by construction.
- **Errors multiply down a chain** — approximate × approximate degrades.
- **Cost curves bend** — you are buying certainty, not computation.

AUTHORITATIVE → transcript 1185, 1193.

**The mechanism underneath, stated once so no session has to re-derive it.** `[U]` A model holds **no state
between turns.** Every turn the harness re-sends the entire conversation — system prompt, instruction files,
every prior turn, every tool result — and the model reads it from scratch; the "session" is continuity held by
**the document**, never by the model. A **tool call is not a function call**: the model emits a structured
block and *stops generating*; the harness — ordinary deterministic code — executes the real operation and
**appends the result to the transcript as more text**; the loop continues while the response's stop reason says
a tool is pending, and exits on an ordinary completion. **The model never executes anything itself.** Two
consequences, both load-bearing: ① instructions, data, tool output and the model's own prior words all arrive
as **one undifferentiated stream of text** — which is why §4.4's separation problem is architectural rather
than a maturity gap; ② **the deterministic machinery is the OUTER layer and the stochastic part is what it
loops over** — the opposite of how it reads from inside. RESEARCHED (2026-09-11, four blind angles) → Anthropic
Messages API ("Context windows", "How tool use works"); OpenAI function-calling docs; Modular LLM Inference
Handbook. Record: `state/projects/canonical-housecleaning/records/2026-09-11-llm-agent-execution-model.md`.

## 0.1 WHAT YOU ARE ACTUALLY GUARDING AGAINST
**Nothing is trying to break in. Something is already inside — it holds your tools by design, it forgets
between turns, and when it meets a rule it understands, it can reason its way past it.** `[H]`

**TWO FAILURE MODES; a control stopping one may not stop the other.** **DRIFT** — the rule faded (attention
weakens with depth, length, instruction count) ⇒ defeats any control the session must **REMEMBER**.
**RATIONALISATION** — the rule is present, understood, and the session concludes it does not apply *here* ⇒
defeats any control the session must **AGREE** with. ⚠ Drift is random; rationalisation is a good-faith
judgement and reads as sound reasoning. *(Receipt 2026-09-11: a hook told a session to read an SOP before
building; it decided in one sentence that it did not apply, and proceeded.)*

> **THE RULE, true by construction rather than by measurement: A REAL LAYER DEPENDS ON NEITHER MEMORY NOR
> AGREEMENT.** Must be remembered → drift kills it. Must be agreed with → rationalisation kills it. **A control
> surviving both acts without consulting the model at all.** ⇒ **If the model can talk past it, it is not a
> layer — it is a PREFERENCE.** ⚠ Preferences are cheap, buy real friction, and work at some rate: **keep them,
> never count one as protection.**

**COUNT LAYERS BY MECHANISM, NOT NUMBER** — two layers only if they fail for different reasons. Three written
rules are one layer wearing three hats; a rule **+** a check firing before the model is consulted **+** an
after-the-fact disk check is genuinely three. *(§5.20 says compliance is the overlap of several circles of friction; this says how to count them.)*
⚠ **THREE ADJACENT WORDS, THREE DIFFERENT THINGS — do not merge them.** A **LAYER** is a rung in the enforcement
stack (prose · a gate · a hook) — **that is the only sense counted here.** §0's *"the deterministic machinery is
the OUTER layer"* is a different sense — **which code wraps which** — and is **never** counted. A **SEAM** is a
link in the skills-SOP LAW 2 loss-chain: **a place where intent died between design and run.** ⇒ ***Which
control failed* and *where the intent was lost* are two questions with two answers.**
**DEPTH IS SET BY BLAST RADIUS AND REVERSIBILITY, not importance** — irreversible → stack; reversible and
cheap → one deterministic check, stop.

⚠ **EXCEPTION: anything READ FROM OUTSIDE** (web page, email, document) **can be authored against you, and an
author adapts** — full adversarial posture there. Everywhere else, what you guard is not an enemy.

**Tier:** architecture **RESEARCHED** (2026-09-11, three blind angles) · both failure modes **OBSERVED here** ·
the memory-or-agreement test **CANDIDATE** — a reframing, not a measurement.
*Record: `records/2026-09-11-layered-enforcement-composition.md`.*

---

## 0.2 — THE HOSPITAL: one more layer (v2, 2026-10-28)
> **DRAFT — not in force.** Nothing in §0.1 or the centering frame is struck or qualified by this section. It sits INSIDE that frame: no perfect control · every layer eventually fails · test the combination · FRICTION, not certainty · a real layer depends on neither memory nor agreement · compliance is the center of the Venn diagram, not a stack. What follows adds ONE candidate circle of friction and says exactly what it does and does not buy.

**The frame (Enver's).** A fresh AI agent is a very intelligent Alzheimer's patient: sharp in the moment, nothing carried between moments. So the hospital does not rely on the patient remembering.
- **HOOKS = walls.** A wall blocks one bad action. It cannot force an ORDER of actions. (Layer already counted in §0.1 and §5.20.)
- **CARD + RECORD = the chart.** Ordered steps, each typed code / ai / human, each with a check. An append-only record on disk. A fresh agent is handed STATE (files), not history.
- **RUNNER = the nurse.** A small script hands over ONE step at a time with its file inputs, runs the step's check, and is the ONLY writer of the record. The agent never writes the record.

**Where it sits among the circles.** Walls stop an action. The nurse is a separate layer BESIDE the walls: a sequencing-and-proof layer (did step N happen, in order, and does its output pass a code check). It acts without consulting the model, so by the §0.1 test it is a layer and not a preference. But it is one more layer, not the end of the stack: it fails for its own reasons (a check can be presence-only, a value can go unvalidated, the record can be truncated, a step can be non-idempotent), it does nothing about content inside an `ai` step, and it does not replace any hook or any other layer. Layers combine; the combination is what gets tested. It buys friction, not certainty.

**Evidence (orchestrator-v2; every figure scored by code; brief `state/projects/orchestrator-v2/brief.md` §4).** ⛔ owner's notes
- 20 runs, 10 of them started inside a live Claude Code session: 0 out-of-order. **Caveat (§5.7a): zero events in 20 runs only rules out true rates above ~14%.** It is not a measured rate of zero.
- The checker caught 5 of 5 planted lies. Kill-and-resume skipped finished steps and ran the rest exactly once.
- Random faults, fake `claude`: REPEAT 300 days silent_wrong=26, double_ran=19. LONG RUN 50 pickups silent_wrong=3, double_ran=11. OPEN-ENDED 500 check-ins: all 0. stuck=0, lost_items=0, out_of_order=0 in every scenario.
- Real sonnet controls: 38 of 38.
- The nonzero silent_wrong traced to presence-only checks, unvalidated values and record truncation; double_ran to non-idempotent steps. Live cron jobs hid errors (`|| true`, `2>/dev/null`, rc 0 advancing a marker).
- **NOT validated by real multi-week use.** Tier: OBSERVED in a fault-injection harness and short real runs; CANDIDATE as a layer in daily operation.

**Map (labels verified against this file).**
- **Walls:** §4.6 (hook = remove an ability) · §5.4 (bind the predictable and catastrophic) · §5.9 (a guard that looks like it works) · §5.20 (compliance is the Venn center) · §15.27 (the model gate).
- **Chart:** §4.7 (reliability belongs to the chain, seam not step) · §4.12 (re-anchor at the generation boundary) · §5.15 (skill as reusable unit, three phases) · §15.15 (externalise state, pass a pointer) · §12.c (artifact-then-pointer) · §7.3 (nothing is saved unless something writes it).
- **Nurse:** §4.1 (verify the effect, not the report) · §4.3 (a model checking its own work) · §5.6 (alive means saying so) · §5.7 / §5.7a (break the thing; zero events and rates) · §7.2 (a self-written citation must be checked) · §7.7 (a test that authors both sides) · §15.14 (independent positive proof) · §15.17 (independent checker).

**When NOT to use a card** (grounded in §15.29 and §5.12 — lowest rung that works; the person reading is the real detector; a missed or doubled run must be harmless).
- Steering a conversation: the card is for a procedure, not a dialogue.
- A single quick step: a card is overhead for one call (§5.12 — call before workflow).
- Pure code: it needs no chart; plain code on a schedule, per §15.29.
- Reasoning that cannot be written to a file: the nurse can only hand over and check files.
- Branching paths: one card per path; do not encode a fork inside a card.
- Parallel `ai` steps: not supported; use a code-held fan-out (§5.12) and join its results as files.

**§2 applies to the nurse too.** The subtract-don't-add principle governs this layer: it is added machinery, paid on every run, and it must keep earning its place. If a card does not catch something in real use that the other layers missed, §2 says remove it.

**WAIT list (what this draft does NOT do).**
- No VALIDATED or "fixed" wording anywhere; the evidence above is OBSERVED/CANDIDATE only.
- No demotion of hooks; they stay the walls and the scarce top of the stack in the §5.20 sense.
- §15.30 (the 98/2 theory) and §15.29's schedule rule are unchanged until §17.27 runs.
- §16 and §17 are not compressed; §17 is not moved (moving it to an appendix is a later step).

---

## 1. THE DIAGNOSIS

**1.1 The verifier is the thing nobody verifies.** Verification is itself unverified work; it decays at
the same rate as everything else and takes the evidence of its own decay with it. Six instances: a
status script printing PASSED and writing nothing for two months · the engine proving guards fire,
silently dead for weeks · "19 of 275 tools have no caller, and the detector that finds them is itself
unscheduled" · an element asserting a bypass closed while the module never migrated · nine commits of
fixes never pushed · `label-checker`, which certifies everything else, the least-certified file (23
untested markers).
One property, not six bugs. AUTHORITATIVE → QUESTION-REGISTER §THE DIAGNOSIS.
*Census 2026-09-05 (§16): 133 instances of "the check that certifies itself" and 194 of "built, then never called,"
across 4–6 months and 11–12 of 12 sources — the same property, now* **REPRODUCED**.

**1.2 Detection was never the gap; being believed was.** Journal 2026-08-05. Hospital was built so
faults couldn't go unseen; Efficiency was built on top and also terminates at an eyeball. **Adding a
rung reproduces the problem one rung higher.** AUTHORITATIVE → journal 2026-08-05.
*Census 2026-09-05, ⚠ a rough keyword tally of the FOUND-BY field, not a count: of 1,656 failures, ~543 matched "a
check" and ~194 "human noticed"; ~9 "cold session," ~5 "never." Direction only: the checks exist and fire; what fails is
what is done with the signal. OBSERVED until the tally is re-derived by hand.*

**1.3 Fixes un-fix themselves, and nothing notices.** A `hooksPath` fix reverted five times. One rule
recurred ~20 times across four tuning passes. The always-loaded budget was measured six times over three
months, 8,933 tokens over by the last, never corrected. *Knowing and changing are disconnected here.*
AUTHORITATIVE → register; transcript 1495.
**And a passing check un-passes itself.** OBSERVED 2026-09-05: three plan cards retired with code-run receipts
later failed their own checks, because later cards moved the files they checked — and nothing re-runs a retired
check. The regression gate (re-run every retired check when anything in its `Where:` changes) is the answer.
*(Receipt: `plans/standalone-autoplan-rebuild.plan.md` card 6.10.)* ⛔ owner's notes
**And acceptance itself can change the world a check was verified against.** OBSERVED 2026-09-05: the regression
gate passed a destruction probe and a selectivity probe, then went blind the moment its own card was retired — its
check invoked the gate, the gate re-ran every retired check including its own, recursed, timed out, and emitted no
findings. A verifier is also work and will be enumerated by any checker over "all finished work." The fix (commit
`3bd635f`, then `65238c6`) excludes itself and says so, reports EXAMINED beside FOUND, and treats an abnormal exit
as INCOMPLETE, never as an empty list. *Seen by a window that built none of it: the scan now prints
"EXCLUDED 6.10 … self-referential" and "2 regressions across 29 cards examined."* Not LAW 2's decay seam (that is
context, turn 3 vs turn 30); this is state change on acceptance.

**1.4 The real bottleneck is the human action after the finding.** The system excels at research and
surfacing; it stalls where a human must pick up the phone or send the email. Not a bug — a structural
property. *(Recorded 2026-05-30, three months before 1.2 reached it from the other side.)*
AUTHORITATIVE → old canon, bottleneck-is-human-action.

---

## 2. THE GOVERNING PRINCIPLE — subtract, don't add

> ~~THE LAW~~ → retitled 2026-09-05 (REFINED). Its own text marks it WORKING THEORY; a theory titled "the law"
> contradicted the frame above. Content unchanged. It stays the first principle under the one law.

**The ecosystem punishes addition.** `[H]` More rules, docs, checkers: each makes the whole worse.
Nothing inside resists addition; the resistance has to come from you. Ranked above every individual
finding — *"worth more than the findings, because it predicts them."* It predicts: don't build the debug
layer (it ships) · don't build the JSON error protocol (removed elsewhere) · don't build the
self-checker (measured worse) · every peer who beat this deleted.
WORKING THEORY, strong locally → transcript 1185.

⚠ **The closest formal analogue is contested** — "more rules → less safety" in regulation literature is
called methodologically fragile and deregulation-motivated by its own peer-reviewed source. This law
rests on local measurement and peer evidence, not on that.
**This is also the shape of the system's own build history.** No component that survived was built
speculatively; the components built ahead of need — early multi-agent Haiku extraction, early parallel
pipelines — failed. Growth is accretive from solved problems, a corollary of subtract-don't-add, not a
counter-example to it — accretion still has to be pruned once the problem it solved is gone.
AUTHORITATIVE → old canon, build-arc-pattern / system-grows-from-real-problems.

⚠ **And it is two-sided.** `[U]` Context is a **sweet spot**, not "less is better": too little starves,
too much buries. Most quality problems trace to context being *wrong* — a missing fact, or bloat — more
than to the model being too small. Reshape the window before reaching for a bigger model.
WORKING THEORY → llm-engineering canon.

---

## 3. THE LENS

**3.1 Complicated versus complex.** `[U]` Complicated = discoverable by analysis, decomposable,
documentation works. Complex = visible only in retrospect, probing changes the system, documentation
does not help — run safe-to-fail experiments. **The code half is complicated. The LLM half is complex.
Both have been given complicated-domain tools.** ~1.5M characters of element docs is the right
instrument for one half and a category error for the other. WORKING THEORY (Cynefin, revised 2024) →
record 7.

**3.2 The growth chain.** `[U]` Brooks: complexity grows faster than size because elements interact
nonlinearly. Lehman: everyone attached must maintain mastery, excessive growth destroys it — and nothing
forces shedding, because the cost of limping along is invisible. Cynefin: documentation cannot fix the
complex half. Vaughan: a rule believed in force erodes through small unpunished violations until
deviation is the baseline — 314 unenforced rules is a textbook incubator.
WORKING THEORY → record 7; transcript 1437–1466.

**3.3 The desk model isolates cognitive load — for the human and the model.** A bounded context means
one mental model instead of five, and the model stays in-schema rather than wandering. It also limits
blast radius. **The advantage comes from what the boundary excludes.** AUTHORITATIVE → old canon.

---

## 4. THE MEDIUM

**4.1 The model's account of its own work is not evidence. Verify the effect, never the report.** `[U]`
An effect check needs no second checker — that retires the checker-on-checker spiral. But the effect
channel is credible only if the actor had no hand in writing it: **an agent-written audit log is still
self-report in disguise.** And verify the *consequence* of a delegated edit, not the claim — an agent
can be right about why something no longer belongs and still destroy it by deleting instead of moving,
then report success honestly. Re-run the check with a *stricter* filter than the helper used.
AUTHORITATIVE → record 1; old canon verify-the-consequence.

- **4.1 (v2, 2026-10-28) — OBSERVED:** a checker can itself be presence-only or lie, so test it first on known-bad input before trusting it passing (the orchestrator-v2 checker caught 5 of 5 planted lies only after it was bitten into). And the AI never writes the record: the runner is the sole writer, so the effect channel is not agent-authored (the 4.1 'audit log in disguise' point, applied).

**4.2 The model is structurally worst at absence.** `[U]` AbsenceBench: 69.6% F1 finding omitted
content, a 56.9-point drop against near-superhuman needle-in-a-haystack — attention has no key for a
gap. **Never delegate without a deterministic check:** "is anything missing" · "did I check all of
them" · exact arithmetic (4.3% vs 99.9% for a dedicated model) · plan validation (58.6% vs 100%) ·
grading its own output. RESEARCHED → record 10. **OBSERVED here 2026-09-04:** six blind reviewer lenses across
four model instances caught 10 of 11 planted defects; the one miss was a *missing* type tag — an absence. A linter
caught it in the same run. *(Receipt: `state/autoplan-rebuild/match-2026-09-04.txt`.)* ⛔ owner's notes

**The countermeasure is a question-design move.** An open question with infinitely many true answers can
never come back empty — the model always fills it, and "returning nothing is valid" does not stop that.
**Change the FORM:** from inventory ("what is missing?") to verdict on evidence gathered ("do these
share one cause?"). Fix the form, not the permission. ⚠ And the null channel is wording-sensitive —
willingness to say "unknown" shifts with phrasing. Design abstention *and* test it fires.
WORKING THEORY → llm-engineering canon; AbstentionBench.

**4.3 A model checking its own work makes it worse, not neutral.** `[U]` Self-critique with no external
signal amplifies its own biases with zero new information — three independent peer-reviewed efforts.
**Corollary:** judge with a model from a *different family*; self-preference bias is measured and
replicated. Log which judge and which test ran alongside the verdict.
RESEARCHED, convergent → record 6 D4. **OBSERVED here 2026-09-04/05, two operators:** the builder certified three
false passes in one build; a window that built none of it caught all three on one pass. The next operator then
reproduced the builder's exact error class (a pipe's exit code read as the command's) while hunting it.
*(Receipts: `state/autoplan-rebuild/cold-verify.md`, `retired-reverify.md`.)* ⛔ owner's notes

**4.4 Some things are formally impossible. Design around them.** `[U]` No architecture separates passive
data from active instruction (ICLR 2025). Hallucination cannot be eliminated for any computable LLM.
Reliable self-report of internal state: ~20% detection under the best protocol, and the vendor warns a
model "might even learn to selectively misrepresent" it. WORKING THEORY → record 6.
**STRENGTHENED 2026-09-11 — the separation claim now has a formal definition, a measured failure, and a named
architectural cause.** `[U]` The first clause above ("no architecture separates passive data from active
instruction") is unchanged and correct; what changed is the evidence behind it. A single model turn is formally
**a pure function of (instruction, data) returning a distribution over strings, with no persistent internal
state**; separation is defined measurably, and **every tested model fails it**, with prompt-engineering and
fine-tuning mitigations **not closing the gap**. The cause is architectural: transformers carry **no
executable-versus-inert distinction** analogous to CPU NX bits or parameterised SQL. ⇒ **Design around it; do
not wait for it to be fixed, and never treat "it only arrived as data" as a boundary.** RESEARCHED, three
converging sources (Zverev et al. arXiv:2403.06833; Greshake et al.; ASIDE arXiv:2503.10566). ⚠ Whether these
are the same work as the ICLR-2025 citation above was **not verified** — recorded as corroboration, not as a
replacement.

**4.5 Rules have a budget and a cliff, and they tax each other.** `[U]` ~68% adherence at 500
simultaneous instructions; frontier models follow ~150–200 reliably. A 24-point compliance drop was
measured from 16 *irrelevant* seeded instructions. Non-additive: one new rule can destabilise unrelated
ones. Two contradictory rules resolve by coin flip — *"may pick one arbitrarily."* Where this system
sits is unmeasured. WORKING THEORY → records 2, 6; IFScale.

**4.6 Code works when it takes away an ability or looks at what actually happened. Everything else is
~~friction.** `[H]` Three tests: **remove a tool · block an action · check whether the file got written.**~~

> **v2 (orchestrator-v2, 2026-10-28):** Third test, replaced: **check content and value, not existence.** A file that exists can hold the wrong thing; presence-only checks produced the silent_wrong cases in orchestrator-v2. OBSERVED. (The struck 'check whether the file got written' is kept above; the other two tests stand.)

Code the model is asked to *cooperate with* is friction that looks like control. Measured: 619
enforcement points — 40.1% mechanical, 50.7% asked-nicely, 9.2% human pause. One blocking hook per 10.1
honor rules. AUTHORITATIVE (census 2026-09-01).
**The founding instance of this was prose alone.** Before any mechanical enforcement existed, two
confirmed incidents of prose capability rules were bypassed by execution momentum — the original
evidence this principle generalized from. AUTHORITATIVE → old canon, capability-boundaries-honor-system.

**A hook is two different things, and it is load-bearing.** `[T]` A PreToolUse block (exit 2) runs at
process level and cannot be talked out of. A Stop-hook "block" **re-injects text** and relies on the
model choosing to comply — a documented case shows a model reading one, apologising, and proceeding.
**Only process-level blocks, tool removal and egress control are unconditional; a hook that persuades is
a stronger request, not a law.** Enforcement is strongest where the model cannot see the check at all.
WORKING THEORY, vendor-primary → 2026-09-02 validation §A.

- **4.6 (v2, 2026-10-28) — OBSERVED:** content, not presence. A check validates the value (shape, range, a re-derived number) and not merely that a file or key is there.

**4.7 Reliability belongs to the chain, not the step — and the seam, not the step, is the failure
unit.** `[U]` `0.90**10 = 0.349`. But ~79% of multi-agent failures are handoffs. Retries convert a step
(`1-(0.05×0.05)` = 99.75%). Checkpointing decomposes a chain (~72% vs ~20% at 85% base over 10 steps).
**Correlated phases behind an external gate defeat compounding better than shortening does** —
`phase_gate.py` already does this: *"the model never stamps its own homework,"* full-state handoff,
fresh context per phase. Set the target top-down from need, as an absolute count, never bottom-up by
multiplying. AUTHORITATIVE locally → records 2, 10. *The nth-root rule is retracted (§10).*

**4.8 More agents help only below a baseline. Cost tracks error rate, not model price.** `[U]` ~45%
single-agent success is the saturation point; above it, zero-to-negative returns at 3.1× tokens per
success. Cost to 90% on one task spanned $1.7K–$71.2K (`71200/1700 = 41.9×`) driven by per-step error —
**a cheaper model can cost more.** A strong workflow with an average model beats a weak workflow with a
strong one; defaulting to the largest model is the highest-frequency low-return spend.
WORKING THEORY → record 2.

**4.9 Nondeterminism is real and not yours to fix.** `[U]` Results depend on which requests share your
inference batch. Temperature 0 and seeds do not guarantee determinism. Batch-invariant kernels fix it
server-side — not available to an API consumer. Remedy: pin versions, record/replay, idempotency keys.
**And the magnitude, measured at field scale 2026-09-11:** agents scoring ~**60% on a single attempt** showed
only ~**25% consistency across repeated trials of the same task** (τ-bench). ⇒ **A 60%-reliable behaviour reads
as a clean PASS or a clean FAIL depending on which day it was run.** ⛔ **One run is not a result for anything
model-shaped.** This is the number behind §5.6's *"an empty denominator is UNKNOWN"* and behind the skills
SOP's LAW 4.3 K-sampling rule. RESEARCHED.
WORKING THEORY → record 2.

**4.10 Nobody has solved silent failure.** OpenClaw — 388k stars, 86,207 commits, funded, cron designed
against silent no-ops — still leaks (issues #13812, #5339). PAI: *"frequent silent failures… it needs
the observability to see them in the first place."* **An open problem in the category, not a personal
failing.** WORKING THEORY → record 5.

**4.11 Multi-agent debate collapses into sycophancy. Run blind, then synthesise.** `[U]` Agents cave to
the confident one; a 24-point gap exists between "I'm convinced X" and "is X true?", and it is *worse*
in more capable models. Never ask agents to agree — make round two independent acceptability scoring, so
convergence is arithmetic. Same-model persona panels give surface diversity only. **Independence, not
headcount, is the signal:** ten posts citing one origin is echo. A disconfirming pass *annotates* — a
confident adversary with a deciding vote degrades accuracy exactly as a yes-man does.
RESEARCHED → llm-engineering canon. **OBSERVED here 2026-09-04:** six lenses, each one *angle* (tokens · steps ·
gating · github · value · postmortem), blind to each other, returning to one aggregation table — 11/11 planted
defects caught, 0 false positives against a same-file control. **This REFINES the skill-SOP's dead-end [A13]:**
persona councils amplify error; angle panels under these conditions do not. *(Receipt: `match-2026-09-04.txt`.)*

**4.12 Instruction drift is architectural — re-anchor at the generation boundary.** `[U]` Early
instructions sink into low-attention middle context. Re-inject a lean anchor near generation, especially
post-compaction, using active recall — repeated verbatim text becomes wallpaper. Keep it lean and give
it an escape path. WORKING THEORY → llm-engineering canon.
**REFINED 2026-09-06 (Enver's ruling, §12.d):** "wallpaper" here means *cross-turn* repetition — the same line injected
into every turn, forever. *Same-turn* doubling of a fresh instruction is a different thing, and measurably helps in
non-reasoning models (§15.19). The original line stands, scoped to the first.

---

## 5. SHAPING

**5.1 Redundancy is the harm, not disobedience. Cut before you add.** `[H]` 138 tasks: human-written
context file +4% success / +19% cost; **LLM-generated −3% / +20% — worse than nothing.** Agents follow
instruction files *too diligently*. Removing existing docs made auto-generated ones helpful again
(+2.7%). Locally: two CLAUDE.md files 98.7% identical, 1.66× the vendor ceiling, ~3,536 tokens of
duplicate every turn. Best files run ~300–350 words; past ~1,000 the correlation goes negative.
AUTHORITATIVE locally → records 10, 6; census.
**The system anticipated this locally, before the research.** Every skill loads context, every session
starts with orientation, compaction loses detail — the system has been in a permanent,
under-acknowledged war against its own context cost since the beginning.
AUTHORITATIVE → old canon, context-most-expensive-thing.

**5.2 Rules start empty and grow one at a time from observed failures.** `[H]` Hand-written, specific,
non-inferable. Trim any that don't visibly change behaviour. Writing a rule after an incident is the
reflex and usually overhead. **Never distil a rule from a run still in flight** — the ending is the part
that tests it. If you must write early, mark it provisional and name what would refute it. **One control
is an anecdote:** before scoping a fault ("only this file"), test enough instances that the scope claim
could fail. AUTHORITATIVE (twice in one session, 2026-08-03).

**5.3 Before enforcing a rule, ask whether it was ever followable.** `[U]` Systematic, near-universal
deviation means the rule was unfollowable at rollout — delete it. Scattered deviation means ask the
three culpability questions. **The diagnostic is the distribution, not the instance.** A control that
forces a routine workaround teaches bypass: if a block is usually followed by a successful workaround
rather than a stop, the scope is wrong. WORKING THEORY (Hollnagel) → records 7, 8.

**5.4 Bind what is predictable and catastrophic. Defer to judgment for the novel. The line is
predictability, not importance.** `[U]` Outside practice draws the same line as *deterministic versus
judgment*. **This is the rule for when something becomes a rule.** The escalation ladder: prose → a
binary gate inside a skill → the user-turn boundary → a hook. A hook is the *last* rung, justified by a
real incident or a catastrophic-silent failure. Hooking "usually do X" creates wallpaper and degrades
the whole guard fleet's signal. WORKING THEORY → record 7; validation §A.
**The third branch, and the largest failure mode in the corpus:** a fact the session needs to SEE goes where it
already looks, and nothing is built. *Census 2026-09-05 (§16): "built, then never called" — 194 instances, the
single most frequent mode; it ships, passes its tests, nothing invokes it, and no effect looks like working.*
**It does not exist until a live path calls it and you watch the call.** REPRODUCED.

**5.5 Nothing sheds by default. Removal must be deliberately, repeatedly funded.** `[U]`
Sunset-with-rejustification is the only method with a documented shrinkage record (68 licence types
eliminated, 42 agencies abolished); voluntary review without default-off fails (~21,000 reviewed, ~100
removed). Peers who beat this deleted: ~2,700 lines and 3 cron jobs · a feature killed at 8 insertions /
132 deletions · schemas cut from 15+ fields to 8–10.

**And the mechanism behind why files never shrink:** across 1,867 repos and 247,694 instruction
lifetimes, **deletion risk *falls* with age** — not staleness but **imperfect recall**: nobody remembers
why a rule exists, so nobody dares cut it. ~75% of deletions are burn-it-down rewrites regrowing to ~90%
within ten commits. **The one causal lever: record why each rule exists — what failed, what was tried.**
That cut excess >99% in a 51-round loop; placeholder comments performed identically to none.
WORKING THEORY (one preprint, directional) → validation §B.

**5.6 Alive means saying so. Heartbeat on success, never on start.** `[H]` **"Broken" means silence that
looks like success** — defined here in May 2026: *"wrong results that look like right results are worse
than crashes,"* and better than what later research proposed. The naive-kick anti-pattern (Koopman,
MISRA, IEC 61508): a watchdog fed by the fact a script *ran* rather than the work *completing* stays
alive while the work is hung. Four states: New → Up → Late → Down. Three failure modes: silent skip ·
hang · **partial failure with exit 0**. "Green" means ran + fresh + produced the expected output, or it
means nothing. AUTHORITATIVE → records 8, 10.

**A count of what you FOUND cannot prove you LOOKED.** Any metric must count what was **examined**, and
a zero must mean *"could not look."* An empty denominator is UNKNOWN, never 0.0 — a rate over nothing
looks measured and means the opposite.
**And a failure to RUN must not be able to equal a legal answer.** OBSERVED 2026-09-05: a check expected
exit code 2 from a linter; the linter was not found at the path, *that* failure also exits 2, and the check
passed — for a reason unrelated to what it claimed. The "no outcome reached" member must be a value nothing
legal can produce. *(Receipt: `state/autoplan-rebuild/retired-reverify.md`, card 2.3.)* **A count-based threshold cannot distinguish "automation dead but ⛔ owner's notes
a human is compensating" from healthy** — detect the failure event, not a proxy count.
AUTHORITATIVE (three instances, 2026-08-04).

- **5.6 (v2, 2026-10-28) — OBSERVED:** a marker never advances on rc 0 alone — advance it only on positive proof of the work (§15.14). And never silence external errors: `|| true` and `2>/dev/null` hid failures in live cron jobs, and an rc 0 advanced a marker over a failed run.

**5.6a The code/LLM seam, as observed here — a shape, not a law.** `[H]` Where code and a model share one running
product, the shape that has held: code hands the model a bounded set of outcomes; the middle is unbounded; what
comes back is one of those outcomes; one of them means NO OUTCOME WAS REACHED, and that one is a value nothing legal
can produce; code checks membership on every path in and surfaces anything off-list. OBSERVED here (the ratified
absent-subject rule, six instances 2026-08-15; the exit-2 collision 2026-09-05) · RESEARCHED for the shape (the field's
dominant practice, five blind angles 2026-09-05) · nowhere yet for the no-outcome member. **Two other shapes exist
and are untried here** — constrain the answer during generation (reason free first, or reasoning degrades) · the
model compiles a deterministic artifact once and leaves the runtime (§15.3, §15.5). *Moved from the build index,
2026-09-05, by Enver's ruling: "one method, not the only one."*

**5.7 Passing a review does not mean an alert works. Only breaking the thing proves the detector
fires.** `[H]` Google, 14 Dec 2020: four purpose-built actionable alerts for that exact failure — all
failed, four different edge causes. A 2014 case: a 25% delta check did not fire at 23%. Actionability
decides whether an alert *deserves to exist*; proof testing decides whether it *works*. **Run a gate
against a case that should fail before trusting a green one** — assertion-free tests read 100% coverage
while verifying nothing. **A gate a background job can satisfy is not a gate.** No source gives a
cadence. AUTHORITATIVE (three false passes, 2026-08-13).

- **5.7 / §15.22 / mode 15 (v2, 2026-10-28) — OBSERVED:** test the tester first. In orchestrator-v2 the bite on the fault injector found a bug in the injector itself, before any result from it was believed.

**5.7a Two readings that invert the obvious, and both were paid for here.** `[U]`
**① A 0% failure rate across a handful of trials indicates a BROKEN TASK, not a working system.** Before
concluding *"it could not be induced,"* compute what that trial count could have seen:
`P(zero in n trials) = (1−r)**n`. **At a true failure rate of 10%, six trials see nothing 53.1% of the time** —
likelier than a coin flip, so the observation carries no information at all. **State the smallest rate you
intend to detect, and the trial count, BEFORE running — a verdict cannot be recovered afterwards.** Runs needed
for a 95% chance of seeing a rate `r` at least once, `n = ln(0.05)/ln(1−r)`: **40% → 6 · 20% → 14 · 10% → 29 ·
5% → 59.** ⇒ Report **`pass@k`**, never a boolean, for anything model-shaped (§4.9).
**② A 100% pass rate signals an UNDER-CHALLENGED test set, not a working system.** A suite that has never
failed is reporting on itself. Pairs with §7.7 (a fixture that authors both sides is reflexive) and §5.7 above
(only breaking the thing proves the detector fires).
⭐ **And before retiring an instrument as too expensive, PRICE it from a measured run.** A verdict abandoned
here as unaffordable re-priced at **$7.81** once the measured per-run cost replaced a `--max-budget-usd`
**safety cap that had been read as spend** — a **14.9× overstatement**. ⛔ **A cap is not a price.**
RESEARCHED (field eval practice: whole-trajectory evaluation, `pass@k` with `pass^k`) + **OBSERVED here
2026-09-11** — six paired actor-battery firings returned zero and were read as "cannot be induced"; the
re-analysis is `state/projects/canonical-housecleaning/records/2026-09-11-llm-agent-execution-model.md`.

**5.8 Detection and action are two problems with two literatures.** `[H]` Front end: the check dies
quietly. Back end: the finding lands nowhere. Solving one does nothing for the other; this system
treated them as one organ. The answer to the back end is **queue design** — dead-letter, backpressure,
auto-escalation, tool-enforced WIP limits — not psychology. Type an alert by what a human must *do*.
⚠ Every back-half source describes a multi-person rotation; whether "assign an owner" does anything when
the owner is always you is addressed by **no source found**. And Google's alerts were well-routed and
still failed — the back half is unsolved, not solvable by routing. WORKING THEORY; back half UNVALIDATED.
**Type an alert by what a human must do:** can I act · is it urgent · could it be automated · would
ignoring it ever be safe. Failures deleted or demoted.

**5.9 A guard that looks like it works and doesn't is worse than no guard.** `[H]` Malformed
deny-regexes giving false security; `allowed-tools` marked experimental and reported not to enforce; a
deny message rendered as invalid JSON so the test passed and the explanation reached nobody. **A hook
you have not watched refuse something is a hook you are trusting on faith** — check the channel, not
just the exit code. Stop the who-watches-the-watcher regress at **one hop**: a synthetic always-on
signal through the real alert path to a different failure domain.
AUTHORITATIVE (eight instances, 2026-08-15).

**Every blocking deny must teach.** WHY it blocked and the exact REDIRECT — a path, an ID, a command. A
bare "no" causes blind retries and workaround-hunting, worse than no hook. ⛔ Deliberately *not* in the
deny: where the rule lives or how to change it — that invites editing the guardrail.
AUTHORITATIVE (2026-05-30, ruled 2026-07-12).

**When the guarded party can read the guard, choose noticing over preventing.** A guard inspecting
command *text* cannot stop a principal that can read the rule. Make the act impossible to perform
*quietly*. The real threat is not an adversary — it is a well-meaning session that has concluded the
current state is wrong. **Ambient display is not noticing:** if it fires and nothing stops, it is
decoration. AUTHORITATIVE → old canon 2026-08-07.

**Fail-closed applies to what a guard is FOR.** A narrow matcher denies on unreadable input; a broad
matcher (`Bash`, `Write|Edit`) exits 0, or a malformed payload walls the session off from the shell.
AUTHORITATIVE (2026-08-11).
**A trusted-root test must exclude the tool's own install location.** Any rule of the form "allow/trust
it if it resolves inside root R" is silently wrong the moment R includes the tool's own install
location — the thing doing the trusting and the thing being trusted become the same directory, and the
test passes on itself. AUTHORITATIVE → old canon, trusted-root-must-exclude-itself (2026-08-24).

**5.10 A control that fails is a claim about the key at least as often as about the worker.** When a
check fails, suspect the reference before the thing checked. Fourth instance was a session's own
`/audit` — three of four rulings refuted by stale assumptions, not bad reasoning.
AUTHORITATIVE → transcript 2209.

**5.11 Recording can substitute for fixing.** Facebook showed 26 developers a proven hole in their own
suite — *"only almost half would actually act on it."* **Detect → prove → act is three steps, and proof
does not bridge to action.** A breadcrumb is not a record: a finding surfaced in conversation but never
written is indistinguishable, three sessions later, from never found. A plan that only accumulates ✅
grows *more confident and less accurate at once.* AUTHORITATIVE → record 9.

**5.12 Use the lowest rung that works: call → workflow → agent → multi-agent** — two vendors converge on
this independently. `[H]` **Decompose by trust and durability boundary** — a reasoning loop, a sandboxed execution surface, a durable
append-only log — **not by presentation/business/data tiers.** Classic n-tier appears in *zero*
agent-engineering primary sources; every hit is generic web-app consultancy. For one person, partition
**in-process, never across a network**: a documented reversal merged microservices back as a team
shrank, because they had solved a people problem a solo maintainer structurally cannot have. Keep the
cheap deterministic path separate from expensive judgment — all six peer systems converged on it.
**Default to one unit and earn the split:** ~79% of multi-agent failures are at handoffs; a single
well-configured agent matched or beat multi-agent on 64% of tasks at ~2× the cost. Pass full context at
every handoff, never a summary. Authorisation belongs at the point of action: credentials held in a
vault or bound to the resource, never passed into the sandbox where generated code runs (Saltzer &
Schroeder's *complete mediation*, cited directly by current secure-agent writers). **Prototype →
production is subtraction, not re-tiering** — reduce abstraction layers as you move to production, never
add new ones. WORKING THEORY, strongly convergent → validation §C.


> **v2 (orchestrator-v2, 2026-10-28):** Handoff, revised: hand the next agent current state as files, not history; full context still applies to merged work (§12.g). CANDIDATE. (The struck 'pass full context' line is under §12.g; this section's text is unchanged.)

**5.13 When you fix one instance, sweep for siblings — but stage enforcement.** `[U]` Apple's goto fail:
the patch removed one duplicated line; the same algorithm remained 6× in the file. Under-fixing is the
documented failure. The remedy has a name — variant analysis; the failure does not. Clone detection
drops 27–47 F1 points on real code, and **nothing finds duplicated instructions in prose.** Counter:
Google stages enforcement (restrict → warn → block) because blunt enforcement has caused outages; **the
ratchet** — error going forward, ignore-list may only shrink — is the practical middle.
WORKING THEORY → record 9.

**A rule copied into two files goes stale in one, and the stale copy is the one that executes.** When
the same fix has been applied twice and the behaviour persists, stop editing the file you believe owns
the rule and grep every file that could state it. A repeat report is the signal. **When you delete a
stale claim, check whether the argument beside it also died.** AUTHORITATIVE (2026-08-11).

**5.14 Prose capabilities decay two ways: the prose rots, and the model underneath changes.** `[T]` 604
skills, 47 with any test — 92.2% untested. Generated skills produced incorrect output 66% of the time
versus an unassisted baseline. A Custom GPT library went "90%-ish to 30–50%" with **no change to its
instructions** when the model was swapped. ~850 agents built, ~a dozen used — lifecycle collapse, not
testing failure. **Harness fixes generalise across models; fine-tunes lock to one checkpoint** —
model-side failures were ~10% of 393 episodes in one 2026 study; the harness-level fix generalised
across 17 backbones while a fine-tune stayed locked to the one checkpoint it was trained on.
AUTHORITATIVE locally → census; validation §E.

**5.15 The skill is the reusable unit, and a workflow has three phases.** `[T]` Prompts are too
granular, agents and desks too coarse. Skills survived every rebuild the layers above and below did not.
Workflows converge on **ingest → analyse → act**; a missing phase is a design diagnostic.
AUTHORITATIVE (observed across every desk).

**5.16 Every loop is bounded, and failures are classified before they are retried.** `[U]` A hard
max-iteration cap is the non-negotiable safety net (one framework defaults to 25), plus a completion
signal and a deadline. Classify before retrying: own-quota/transient → retry with backoff ·
provider-systemic → circuit-break · deterministic → fail fast. **A breaker trips on systemic failures
only, scoped per provider.** Separate worker from checker. Unbounded loops: $6k/day → $22k overnight;
$127/week → $47k/week. ⚠ The "transient / model-recoverable / user-fixable / unknown" taxonomy is **our
construction — no source uses it**; the sourced splits are transient/permanent and harness/model.
WORKING THEORY → validation §E.

- **5.16 (v2, 2026-10-28; with §4.9 idempotency keys) — OBSERVED:** every side-effect step must be safe to run twice. double_ran (19 and 11 in the fault runs) traced to non-idempotent steps; bounded retry is only safe over idempotent work.

**5.17 One boundary, one meaning.** When a line or symbol already carries a meaning, never make it carry
a second — the two will not fall in the same place and the artifact contradicts itself. **The defect is
invisible to its author and only to its author.** AUTHORITATIVE (twice in one session, 2026-08-03).

**5.18 A hand-updated pointer has no mechanism keeping it true.** A "which section is live" line, a
stated file count, a next-action in two places — each is a *copy* of a fact living elsewhere. A rule
saying "update the copy" moves the failure to whoever forgets, silently. **Derive it, or build the
comparison.** The only thing that has caught this is something reading both sources and diffing them.
AUTHORITATIVE (one pointer drifted five times).
*Reproduced 2026-09-05, autoplan rebuild — three independent pointers, three different shapes, none caught by
their author:* a plan card hardcoded the expected linter output as `8 defects`
(`plans/standalone-autoplan-rebuild.plan.md:152`) while the fixture had grown to 11; only a cold window re-running ⛔ owner's notes
the command saw it (`state/autoplan-rebuild/cold-verify.md:69`) · `system/organism/separation-manifest.md:287` ⛔ owner's notes
labels `skill-building-sop.md` "byte-identical to upstream/main"; the two copies differed by 6 lines before this
build's edits and by 128 after (`diff` run 2026-09-05; ledger `[SKILL-SOP-TWO-COPIES-DRIFTED]`) · the skills SOP's
own frontmatter names `system/sops/skill-irl-findings.md` as its living intake (lines 12, 19); no such file exists in ⛔ owner's notes
the public repo, the only copy sits in a parked donor-spillover folder in the private one. **The hand-updated pointer
inside the document that teaches the rule drifted too.** Tier: REPRODUCED (two builds, four pointers, 2026-08 and
2026-09-05).

**5.19 Place each fact at the broadest scope where it reliably holds.** `[H]` No higher — it bloats every
session. No lower — it is invisible to sessions that need it. Always-on canon must be precise and
efficient; scoped canon may be richer. **A new domain is earned** — by distinctness, or by size making a
split improve findability — never as filing convenience. **Before writing any new entry, glob for an
existing home and extend it.** Forking creates silent drift: one truth, one home. Two records that agree
get deduped; **two that disagree get surfaced as a conflict, never silently merged.**
AUTHORITATIVE (system-wide reframe 2026-07-12).

**5.20 ~~Compliance is a stack, not a choice.~~ Compliance is the center of the Venn diagram, not a choice.** *(heading reworded 2026-10-30; frame in "The layers of friction" above. Where this section says "stack", read overlapping circles of friction.)* `[H]` §5.4 gives the escalation ladder — prose → gate → user-turn
→ hook — as rungs to *pick from*. The observed truth is that each layer catches what the one above misses, and
the design is to **stack** them, sized to the stakes. OBSERVED 2026-09-04/05, one build, three layers, three
disjoint catches: a *refuse* layer (a linter at write time) found 8 defects six reviewer lenses never named ·
a *judge* layer (a cold window) found 3 false passes a *verify* layer (a script re-running checks) had certified ·
a *wall* layer (guards) refused a leaked personal path and an unencoded file-open that every layer above had
passed. **A hook is the scarce top of the stack** — expensive, machine-wide, unbypassable — never a substitute
for the cheaper layers beneath it, and never the first thing reached for. *(Receipts: commits on `V2`
2026-09-04; `state/autoplan-rebuild/` ⛔ (owner's notes).)*
⭐ **HOW TO COUNT ONE IS IN §0.1, NOT HERE** *(added 2026-09-11)*. This section says compliance is the **overlap of several circles**;
**§0.1 says how to count one** — and a stack you cannot count is a number you are guessing. ⛔ **The rule is
stated there and nowhere else, deliberately: it was briefly written in both places, which is **mode 3 — *"the copy you
didn't count"*, §16's third failure mode: one fact in several places with no generator, so a fix leaves the
others live — inside the document that teaches mode 3.** *(Canon §5.19: one truth, one home.)*

---

> **v2 (orchestrator-v2, 2026-10-28):** **§5.20 / §4.6 'a hook is the scarce top of the stack' stands unchanged.** Walls stop one action but cannot force order. The nurse (§0.2) is a separate layer beside them, not above or instead of them; layers combine, and each still fails. CANDIDATE as a layer.

## 6. THE HUMAN

**6.1 Rebuilding your own system is the hardest category of learning there is.** Experts absorb
near-familiar-but-altered information *worse* than wholly novel — existing chunks compete with the new
pattern. An MVP→V1 migration is exactly that. **Not a discipline problem.** Unlearning is largely
unsupported; the old design keeps resurfacing — that is memory. Einstellung has boundaries: when the
familiar move was an outright blunder, experts avoided it — so **make an old decision's failure obvious
rather than arguing yourself out of it.** WORKING THEORY → record 7.

**6.2 To change a held belief, name the old one and say why it is wrong.** Refutation text: 44
comparisons, n=3,869, g=0.41. Stating the correct version alone works far less well. **Strike, never
silently overwrite.** And **a rule that regenerates itself doesn't decay** — the self-stamping
DO-NOT-FIX banner rewrites itself on every archivist walk; the one mechanism found that doesn't rot.
AUTHORITATIVE on the local mechanism.

**6.3 Choosing not to build something possible is its own axis, separate from impossibility.** The
product owner's job. Outside criteria: a solo maintainer closes when no realistic time is foreseeable
**and** a workaround exists; SQLite kept a known bug forever. **What makes a decline stick:** the reason
is written where it will be re-read — permanent documentation, not a closed ticket — and it names the
cost of reversal. 40 `state:parked` entries exist; the mechanism is built, the ruling is not.
WORKING THEORY → record 10.

**6.4 Never make the person do friction work with a secret.** Build a script that prompts for it with a
hidden read. The secret never enters context and never lands in a log. Never "paste it to me."
AUTHORITATIVE → old canon 2026-06-08.

---

## 7. THE READER

**7.1 The system holds more than any one reader can retrieve — and it doesn't care that the reader is a
machine.** A session said this about itself after `/audit` refuted three of its four rulings using this
system's own buried records. **Conservation of Familiarity applies to the model reading the canon.** And
retrieval is harder than storage: a cold session that doesn't know to ask will not load it, however well
organised. Solve storage first, then retrieval. AUTHORITATIVE → transcript 2106.

**7.2 Self-written confidence is a self-report. A citation must be checked, not pointed at.** 11 of 48
citations checkable across three prior records — **22.9%** — all three declaring `confidence: CONFIRMED`;
one at 0 of 15. ⚠ A three-record sample, not a corpus figure. **A resolving link is not a true claim** —
every link checker verifies a pointer resolves; none verifies the description is still true. **A marker
a file carries about itself is self-attestation, not a gate:** a machine writes `vetted: true` as easily
as a human. A real gate is *interactive* or *structural*. **Existence is not endorsement** — finding
something built is evidence it exists, never that it is correct; age is a bad proxy either way. **Never
build on a draft-status artifact.** **Distrust prior written system info until reconfirmed** (Enver,
2026-09-01). AUTHORITATIVE → register Q17/Q18.

**7.3 Nothing is saved unless something writes it.** A log recording *that* work happened is not a
record of *what* was found. Subagent returns were never auto-saved — the flight log holds counts, not
content. Found twice: 2026-09-01 (six orphaned research waves) and 2026-09-02 (five code-review answers
credited but never persisted). **Two sessions are not a check** — they hold the same wrong belief
comfortably, one inheriting it from the other and handing it back as confirmation. **Re-run the
measurement; never summarise the report.** **And durable state never lives in a tool-owned, ephemeral
surface.** AUTHORITATIVE → pointer index; old canon 2026-08-24.
**And a refusal is not a record.** When a guard BLOCKS a bad write, the block itself leaves no trace
unless it also emits a record of the refusal — **"blocking prevents the lie; it does not speak the
truth."** AUTHORITATIVE → old canon, a-refusal-is-not-a-record (2026-08-04).

**7.4 Intent, reality, history — the gap between them is the finding.** The map says what was *meant*;
the census says what is *there*; the journal says what was *already tried*. **Grounded questions get
grounded answers** — the 74% canon-truncation bug came from a census, not a search. **A completeness
count comes from the territory, never a document's own list** — a document grading its own homework
produces a number confidently wrong rather than obviously missing. **A missed hit leaves no trace,
unlike a wrong edit** — never build a worklist from a truncated search. **When two sources disagree,
prefer the more recent** — four exceptions: recency ranks *equal* authority only · a user ruling
outranks a later agent note · an undated source cannot be compared · a restatement is corroboration, not
supersession. The append-only journal is the tiebreaker of last resort. **Honest non-finding is
valuable.** AUTHORITATIVE → old canon 2026-08-14, 2026-08-15.

**7.5 Record the discriminator, not just the verdict.** Write down the **test** you used, not only the
answer. A saved verdict cannot referee a disagreement — the reasoning generalises to the next case; the
verdict only settles this one. Preserve question + why + conclusion at the confidence register it was
delivered in, never auto-promoted. AUTHORITATIVE → old canon 2026-08-01.

**7.6 Careful verification is a route into the wrong frame, not a defence against it.** A session set up
to check another's work will verify each finding carefully, find them true, and never ask whether they
were the point. **Rigour is the mechanism of the capture.** Measure by what reached the outcome. Ask:
*does this reach the user of the thing, or only its operator?* AUTHORITATIVE (a green PR sat 16.3 hours).

**7.7 A test that authors both sides of a comparison proves only that it is reflexive.** A fixture
supplying **both** sides always matches — it wrote them both. It cannot find the real failure: the two
sides arriving in different *shapes*. Hand it one form and make the code obtain the other the way it
really will. **The tell is a suite that stays green while a single real run fails.** Mutation testing —
breaking the code and confirming tests fail — is the accepted way to test the tests.
AUTHORITATIVE (41 green cases, one real block) → validation §D.

**7.8 An unfalsifiable goal is never checked.** A goal with an artifact behind it gets verified
constantly; one phrased as a comparative has no threshold and no command. Softening an over-strict
absolute *feels* like a fix and trades a wrong test for no test. **Narrow what must match — never blur
how well.** Before recording any goal: what command returns yes or no?
AUTHORITATIVE → old canon 2026-08-25.

**7.9 A backlog is a set of claims, not truth.** Verify each item against the live system before acting;
an aged backlog contains ghosts. *(The "roughly half" figure is a heuristic with no primary study.)*
Audit-then-score lifted accuracy 60.8% → 90.9% in one measured case. **And read the dead-ends first** —
capturing what was tried and *why it failed* is more differentiating than capturing what worked;
compaction makes re-derivation the default failure. WORKING THEORY → validation §D.

---

## 8. PRACTICES

- **Test at the point of change, never system-wide.** Capture what it does now, diff later. Sprout & Wrap.
- **Hooks are not a guaranteed floor.** Hook feedback arrives as tool-result context — the same
  informational channel injection-hardening teaches distrust of. Single anecdote; load-bearing. Test that
  yours bind. *(Sharpened by §4.6 above: a hook is two things — a process-level block, or a persuasive
  re-injection. Only the first is a floor.)*
- **Don't parse structure out of prose. Use native tool calls.** LangChain removed prompted output: *"has not proven to be particularly reliable."*
- ~~**Execute-and-observe beats plan-ahead.** Semantic Kernel deprecated its planners. Bears on `/autoplan`.~~
  **REFINED 2026-09-05 (Enver's ruling, the `/autoplan` rebuild):** neither pure outline-ahead nor pure
  execute-and-observe. **Plan ahead in full, then test and validate at every gate** — a plan that must run
  unattended needs every phase in detail, and drift is caught at the phase gate by a check that re-runs, not by
  coming back to plan again. The vendor finding is one data point about *interactive* planners, not a direction.
  OBSERVED — one build, 15 cards retired by code re-running their checks; three later un-passed and were caught by
  the gate (§1.3).
- **A headless agent never drives the browser.** Unattended runs reach the web only through the sanitised path, and **fail loudly** rather than degrading silently.
- **Wrap the harness, don't replace it.** Zero migration accounts in 13 searches; the builder of the most elaborate wrapper: *"mostly, no."*
- **A capability declares its inputs and outputs — and you verify the declaration binds.** `allowed-tools` doesn't.
- **Sample normal runs; capture failures at 100%.** You cannot replay what you did not record. Never log full responses, keys, or raw prompts with personal data.
- **Sandboxing answers "can it reach." Authorisation is separate** — enforced at the point of action every time, never cached from an upstream check (complete mediation).
- **Prefix caching only. Never semantic** — it serves a confidently wrong answer for a *similar* query.
- **Bound retention from day one; write atomically** (temp-then-replace). Unbounded growth is the top state-store regret; crash corruption the second. *(Atomic rename holds locally, not on networked filesystems.)*
- **On a shared spine, the machine name goes in the FILENAME.** Drive resolves a two-machine write to one path by silently creating a conflict copy — tagging the *contents* does not help. **Append-only does not prevent forking; one named writer per path does.** A missing shard is a finding, not a silent skip.
- **Derive, don't store, what can be cheaply recomputed** — a stored count is both a drift bug and a sync race.
- **Sync is not backup.**
- **Copy, don't move, in an irreversible migration.** Baseline-green the verify gate on the old setup *before* crossing: façade → dual-write → validate parity → flip behind a flag → decommission.
- **Lock the interface contract before parallel work begins.** Coordination at the seam, not capability, is where multi-agent work fails.
- **The six configuration smells:** lint leakage 62% · context bloat 42% · skill leakage 35% · blind references · init fossilisation · conflicting instructions. Two present raise the odds of a third by 83%.
- **Response style: a principle plus an example, not a rigid template.** Scale length behaviourally, suppress over-formatting explicitly, re-anchor near generation in a long session.
- **Append, never overwrite, data files.** Three months lost to one overwrite.
- **Append, never overwrite (v2, 2026-10-28) — OBSERVED:** the runner detects a truncated record before resuming (record truncation produced silent_wrong in the fault runs); a resume from a damaged record stops loudly.
- **Back up before overwriting, even when told to.** An explicit filename is not a licence to destroy content you have not read.
- **Show the list. Wait for the go.**
- **Cheap scan first, targeted read second.**
- **Don't declare blocked; find the five-minute unblock.**
- **Negative knowledge over positive** — *"way more helpful to know what not to do."*
- **Every finding carries a pointer.**
- **Gate research waves only on genuine dependency.**
- **Multi-tenant isolation is not a bolt-on. Permissive defaults survive setup — audit them.**
- **Delegation is a planning-time decision.** A mid-task "use sub-agents" works once; only structure makes fan-out the default.
- **Right-size the model tier** — cheap for verbatim work, strong for judgment someone relies on — and **validate the values a cheap model returns**, not just the format.
- **A warning without a redirect is a defect.** Silence makes a reader keep looking; a bare warning makes them stop, believing it was addressed.
- **A recurring symptom gets its own compaction-proof debug doc: closed-theory table, current diagnosis,
  the test.** Read it before proposing a fix — compaction makes re-derivation the default failure, and
  "API limit" (like most platform errors) is 3+ distinct failure modes with 3+ distinct fixes; get the
  exact error string and reproduction conditions first. *(Old canon 2026-06-11-debugging-discipline.md —
  origin: the huddle API-limit 429 re-investigated from scratch three times.)*

---

## 9. RULINGS — Enver's, canon by his authority

**2026-09-01/02:** Findings are provisional until validated here · Distrust prior written info until
reconfirmed · The QUESTION-REGISTER is the document of record, organised by altitude · One shot kill —
no staged waves · Q-H1/Q-H2 struck · Canon held, nothing promoted · Cowork-vs-CLI retired (Code's
desktop tab ≈ the CLI) ·
Mid-migration gaps are a work list, not a pathology · The bottleneck is **not** a decision backlog; the
ledger's type model is the truth (631 debt · 94 project · 89 decision · 34 blocked · 7 chore) ·
Multi-step skills built with the skills-sop work · Simpler ≠ thinner · Hold the document when a read is
disputed · **This file supersedes the old collection and the July canon; the old files are retired.**

**2026-07-12/14:** Canon is an observation, not a rule · precise and efficient, never tiny · security
stays lesson-only · don't file a paraphrase · strip numbers that fail verification · Rule-of-Three
rejected as canon (too prescriptive).

**2026-08-04 (authoritative, superseding on conflict):** Shipping to non-technical users — **git is
pull-only**, so handing someone a repo gives the publisher no access to their machine. A zip *copies* a
folder structure; git *enforces* it at a known version. **Ship public, gate later.** ⛔ Never put a git
repo inside Google Drive. Pull-requests-only at creation. Supply-chain fears do not apply to a repo of
prompts and markdown.

**2026-07-21:** The **code→GitHub / sensitive-content→Drive split is validated best practice**, not a
legacy tax. The two-repo split is the mainstream 2026 pattern for an AI second-brain-in-git (Karpathy's
LLM-wiki, Obsidian-vault-in-git) — but practitioners deliberately keep sensitive/financial files OUT of
any git repo. A private repo is not a security boundary: secret-scanning is paid-only, the common
failure is accidental public exposure, and deleted/forked commits stay recoverable forever by hash. Keep
sensitive data off git; if it ever must live in git, encrypt with **SOPS+age** (never git-crypt —
effectively abandoned, breaks on modern git). Do not re-litigate the split; extend it only for
non-sensitive knowledge.

**2026-10-29 (Enver, V2 plan 2.5) — One copy, in the shared layer.** If something should work the same way everywhere, it exists once, in the shared layer. Desks use it; they never copy it.

**Two disagreements left parked:** multi-step reliability (Enver disagreed; research later confirmed him
— 4.7) and "decision backlog" (called reductive; corrected to the type model).

**T9.11b (2026-08-15) — A checker fails loud when its subject is absent or ambiguous.** "I checked and it's clean" and
"there was nothing here I could check" are different claims; a checker that cannot reach, find, or disambiguate its
subject says so as its own distinct outcome, never folded into a pass. Ratified on six instances in one session;
carried in §5.6 and, until 2026-09-05, only in the build index. *(Listed here 2026-09-05 — it was cited everywhere and
recorded nowhere in this section.)*

---

## 10. RETRACTED — do not carry forward

**From the old canon (2026-09-02 research validation):**
- **"Mechanical enforcement beats behavioural rules EVERY TIME"** — the absolutism is wrong; enforcement is layered and never 100%, and caps around 40% here. Keep the core (4.6); strike *every time*.
- **"Hooks cannot be reasoned around" / "zero bypasses since deployment"** — a hook is two things (4.6). Stale as a fact.
- **"Distill is the learning mechanism"** *as a finding* — the mechanism is proven in a controlled setting (91% vs 80%); whether a records→canon loop changes production behaviour is **unmeasured everywhere**. Keep as intent.
- **"Three-tier is the right-sized spine"** — zero agent-engineering primary sources use n-tier. Replaced by 5.12.
- **The error taxonomy by who-fixes-it** — our construction; use transient/permanent and harness/model.

**From the 2026-09-01 session (24 claims):** "no reliability target was ever set" (90% on one desk's
extraction, May) · "no do-not-fix list" (40 parked + the regenerating banner) · "'breaks' was never
defined" (May, and better) · the solve-backwards nth-root rule (no source; Google SRE rejects it) ·
"wrong docs are worse than none" (no scholarly support — stop asserting it) · "prove a check can fail"
as the remedy (half don't act) · "steal skills-declare-files" (doesn't enforce) · "the search log is
unfakeable" (the searcher holds Bash) · "research is finished" (the census generated new questions) ·
"~29% blocked on decisions" (overstated 2.8×) · "multi-step skills are unreliable" (refuted by
mechanism) · the 2026-07-25 record "already answers" the seam (0/15 citations) · "documenting debt
substitutes for clearing it" (retracted on migration context) · "15 jobs invisible by construction"
(**missing tile ≠ not running**) · "all 12 UserPromptSubmit hooks fire" (1 of 12 unconditional) · MISC's
143 rows indicate a map gap (deliberate exclusions) · findings written as settled and later restamped
provisional · "needs ruling" and "researchable" treated as exclusive · a decision sheet delivered before
the machine was exhausted (withdrawn) · the fifth final-wave question framed as psychology when it
should have been queue engineering (one blog post given top billing twice) · "36 — I said 35" · "wrong
to lead with observability."

**Also:** OAuth-401 as the cron cause (zero authentication failures anywhere) · anything resting on
Ariely & Wertenbroch 2002 (data-tampering finding 31 Aug 2026, retraction pending).

⚠ `records/insights/2026-09-01-assistant-self-corrections.md` holds 13 of these; an audit found **11 more
it is missing** — the record itself is **45% complete (9 of 20 verified present).** A session reading
only that record would re-claim several.

---

## 10a. DO NOT RETRY — approaches proven not to work *(section opened 2026-09-05 by Enver's ruling; grows over time)*

> §10 retracts *claims*. This section retires *approaches*: things tried here that failed, with the receipt, so
> no later session re-tries them from first principles. **A proven failure is worth as much as a proven
> success, often more.** Each entry: tried · failed · date · source · what replaced it · tier. Never complete —
> "not listed" is not "never tried." The build-time twins live in `skill-building-sop.md` §II.4a/§II.4b and
> `build-rules-index.md`.

- **[DNR1]** Tried: a rule saying "remember to update the copy" as the mechanism keeping a hand-written pointer
  true. Failed: one pointer drifted five times (2026-08); three more pointers drifted in one build (2026-09-05,
  §5.18). → Derive the value, or build the diff that compares the two sources. **REPRODUCED.**
- **[DNR2]** Tried: acting on a hand-off's factual claims without re-reading the source. Failed 2026-09-05: one
  hand-off carried three wrong claims (a block "with no analogue" that duplicated SOP LAW 1b · "3× the length"
  that measured 1.45× · a tension "unruled 13 months" that SOP §III.10 had ruled). All caught by opening the
  file. → Every claim re-checked before it is acted on (§7.2). **OBSERVED.**
- **[DNR3]** Tried: a "no outcome reached" member that shares a value with a legal outcome. Failed: a check
  expected exit 2 from a linter; the linter was absent, *that* also exits 2, the check passed
  (`state/autoplan-rebuild/retired-reverify.md`, card 2.3, 2026-09-05). → The no-outcome member must be a value ⛔ owner's notes
  nothing legal can produce (§5.6). **OBSERVED.**
- **[DNR4]** Tried: promoting a finding to REPRODUCED on receipts from a single build. Failed 2026-09-05: proposed
  by one nav window, withdrawn by that window against the frame's own bar ("multiple blind sessions *over
  time*"). → Two receipts from one build is OBSERVED ×2; a different build promotes. **OBSERVED.**
- **[DNR5]** Tried: a regression checker that re-runs the check of "every finished task" with no exclusion for
  itself. Failed: the moment its own task retired, its check re-invoked the checker — unbounded recursion, a
  120 s timeout, an uncaught exception, and a scan that reported ~~**0 regressions, exit 0**~~ **no REGRESSION
  lines — its exit code was asserted, never measured, and is now unmeasurable without reverting live code**
  (corrected 2026-09-05 by claudeops-1a's own transcript audit, entry A14) while a retired card failed by hand
  (commit `3bd635f` on `V2`, claudeops-1a report, 2026-09-05). → A checker over all finished work
  excludes its own entry and says so; an abnormal exit is an explicit "incomplete," never an empty list; report
  EXAMINED beside FOUND (§1.3, §5.6). **OBSERVED.**
- **[DNR6]** Tried: concluding an instrument *"cannot induce the failure"* from a handful of trials that
  produced no failures, then retiring the instrument as structurally unworkable. Failed 2026-09-08/11: six
  paired firings returned zero, but **at a true failure rate of 10% that outcome occurs 53.1% of the time** —
  the observation carried no information. The instrument was then retired over a cost **nobody computed**:
  assumed **$116.00**, measured **$7.81**, because a `--max-budget-usd` safety cap was read as spend
  (**14.9×**). → **State the detectable rate and the trial count before running · report `pass@k`, never a
  boolean · price from a measured run, never from a cap** (§5.7a). **OBSERVED.**

---

## 11. CORRECTIONS OWED TO THE QUESTION-REGISTER

- **Q21** "15 declared jobs have no status tile" → *missing tile ≠ not running*; three confirmed running into machine-local dirs. ⚠ `guard-fire-test` is still cited as "silently dead" twice later with no cross-reference.
- **Q20** the `health*`/`safe_*` families are **not** a copy-paste disaster — real shared helpers used by 85 files. True duplication: ISO timestamps ×11, tile atomic-write ×4, frontmatter ×3, ~220 lines.
- **Q19** "PII was everywhere in the code" is **false for the current tree** — scan clean, every hit a documented fixture. One LOW finding: a second GitHub account holds push access to the public repo.
- **Q0c / Q13 / Q1b** each have a prior answer the register calls absent.
- **Q27** evidence exists only inline; the pointer index attributes it to records 7 and 8, which do not contain it.

---

## 12. TENSIONS — unresolved, kept as tensions

**From the right-size audit, 2026-09-05** *(record in §14; each is a source of investigation, not a defect to patch):*
- **12.a A dead-man's switch on every registered hook vs "do not build a meta-checker."** The field's cheapest answer to
  mode 1 (a registered thing must fire once per period or alarm) is, on its face, a watcher over the guards — the shape
  the absent-subject rule forbids and the shape that went blind on retirement (§1.3). Yet §4.1 says an effect check needs
  no second checker, and a heartbeat is an effect. Where is the line? → Experiment 17.x.
- **12.b Generate-the-copy vs "rather duplication than miss."** Two of Enver's rulings pull apart: §5.19 one truth one home,
  and the 2026-08-07 ruling that the do-not-build register is duplicated by design. The offered reconciliation —
  duplicate by DERIVATION, never by hand — is a candidate, not a ruling. **And the two frames say "identical text sits
  atop the other document" while a diff shows 188 differing lines of wording drift.** Mode 3, inside the sentence
  that names mode 3. → Enver rules; then one frame is generated from the other or the claim is struck.
  **RESOLVED 2026-09-06 (Enver):** no generator. A script that copies one frame into the other is one more thing that
  breaks silently in the background and then needs its own alarm. The two documents are checked for drift by the human,
  on a quarterly cadence, as a five-minute job — an accepted limitation of a human-in-the-loop system, and the human's
  small share of the work under Pareto. The "identical text" claim in the frame is struck and replaced with "a near-copy."
- **12.c Artifact-then-pointer is the field's strongest handoff mechanism and only PARTIAL here.** The field measures
  within a run; we measure across sessions and days. Pointers are written; nothing makes the next session read them.
  Storage vs delivery. → Experiment: does an injected pointer hold where a stored one did not?
  **ROUTED 2026-09-06 (Enver):** what held this morning was the injected pointer plus a live dialogue between the old
  window and the new one; the stored pointer through a brief is the heavy path. Not an experiment here. Two ledger items:
  `[HANDOFF-SAVE-CHECKIN-TOO-HEAVY]` (make `/save` and `/checkin` lighter — its own project) and
  `[HANDOFF-COMMAND-NO-PROJECT]` (a command that injects the thorough-handoff prompt).

*From the five-mode pass, presented to Enver 2026-09-05 and recorded here as OPEN — awaiting his routing, not resolved:*
- **12.d Repetition helps vs "repeated text becomes wallpaper" (§4.12).** A replicated study: identical text twice improves
  accuracy in non-reasoning models. The split may be identical-repeat vs varied nagging, and reasoning mode vs not. This
  system's per-turn injectors ARE repetition and have never been measured. → proposed experiment.
  **RESOLVED 2026-09-06 (Enver):** not a contradiction — two different things. The study doubled the same text inside one
  prompt, once: a single fresh signal. This system's per-turn injectors repeat the same line into every turn, forever: a
  background hum. Same-turn doubling of a fresh instruction may help; cross-turn repetition becomes wallpaper. §4.12 is
  scoped accordingly (REFINED there). No experiment.
- **12.e Plan-first as ceremony.** The field's remedy for over-building is plan-first with sign-off — the prose shape that
  failed seven times here. The mechanical version, re-run the outcome after every card (17.6), is untested. → proposed:
  fold into 17.6.
- **12.f A model that annotates vs a model that gates.** The field's "skeptical second model" collides with LAW 3 on its
  face; §4.11 already draws the line — a disconfirming pass annotates, never decides. → proposed: a scoping line under
  LAW 3, no experiment.
  **RESOLVED 2026-09-06 (Enver):** verification is layers, ranked by independence from the actor. The same window
  re-reading its own work is the weakest layer. A separate window on the same model is a real layer, and it has caught a
  great deal here. A separate window on a different model family is a stronger one. A deterministic code check is the
  strongest for whether something is well-formed, and it cannot tell whether something is wrong. None of these is yes or
  no; each catches what the one beneath it missed. The one shape the evidence warns against is a second model with a
  deciding vote — it annotates, and the human or the code decides. *LAW 3 (SOP) says only that the actor may not declare
  its own work done; a different window checking is LAW 3 working as written, not a collision — 12.f as first drafted
  read LAW 3 as broader than it is.*

Automating away pain lets the real fix be deprioritised forever · Reducing alerts to fight fatigue risks
under-alerting (EEMUA 191, ISA-18.2) · A watchdog can substitute for correctness discipline · *"A
no-blame culture is neither feasible nor desirable"* (Dekker) · Per-step error dominates cost (40×)
versus the local Sonnet→Haiku switch at ~$268/mo saved · **The distill loop adds by design, and §2 says
addition is the disease** — the likely resolution is that distillation must also *shed*, but that is a
ruling · Pruning is dangerous in the other direction: a wrongly-cut safety rule costs more than bloat ·
Every authorisation source is enterprise-scale; the solo fit is **inferred by every searcher, stated by
none** · **Canon-is-immutable vs everything-under-suspicion** — the old canon's 2026-08-15 chronology
framing read as "canon doesn't change"; Enver's 2026-09-02 ruling put the entire old canon under review.
Likely resolution, not yet ruled: *immutable means never silently edited, not never superseded* — this
file's own status line (struck, not deleted; nothing carries forward without re-ratification) is already
built to that reading.

**12.g Pass full context at every handoff (§5.12) versus withhold the expected answer when checking.** `[H]`
~~§5.12 says *"pass full context at every handoff, never a summary"* — ~79% of multi-agent failures are at~~

> **v2 (orchestrator-v2, 2026-10-28):** Replaced: hand the next agent current state as files, not history; full context still applies to merged work (§12.g's own case). CANDIDATE.

handoffs, and context-starved sub-agents make **conflicting implicit decisions invisible to each other**
(independently, 2026-09-11: Cognition abandoned parallel sub-agents for exactly this, replacing them with
single-threaded full-context agents; corroborated by a study of 5 frameworks / 150 tasks naming inter-agent
misalignment the dominant failure category). **But a checker handed the author's expected answer CONFIRMS it** —
producing a second party's signature on an unchecked number, **worse than not asking**, because it converts an
unchecked claim into a checked-looking one. ⚠ **The two rules point opposite ways and the distinction is
written nowhere else:** §5.12 governs handing off **WORK**, where missing context loses decisions; the
withholding rule governs handing off a **CHECK**, where shared context shares the bias. ⛔ **The boundary,
stated so it can be tested: the moment a fan-out produces MERGED WORK rather than independently re-derived
NUMBERS, §5.12 applies and the withholding rule does not.** OBSERVED on both sides, 2026-09-10/11 — the
withholding rule caught a nav window's own wrong-repo audit on its first use. **Unresolved; Enver rules.**

--- · **Acceptance can create the property that invalidates the verification**: a checker passed a real destruction probe AND a selectivity probe, and retiring it is what broke it — its own acceptance criterion invoked itself once it was filed as done (2026-09-05, card 6.10). No pre-acceptance check could have found that, and no rule is offered for it.

## 13. NOT PRINCIPLES — open decisions, Enver's alone

The reliability number (per chain, as an absolute count) · the timebox · what he is choosing not to fix ·
the Version B wishlist · a shared API layer across harness and web app · whether hospital becomes an
effect-channel diagnostic layer · whether to flip the five OTEL switches · whether diagnostics are
dev-only.

---

## 14. POINTERS — where the evidence lives

**Research (11 records):** `records/research/2026-09-01-*.md` (ten waves, full source URLs) ·
`records/research/2026-09-01-code-review-findings-recovered.md`.
**This canon's validation:** `state/projects/infrastructure/organism-build/records/2026-09-02-canon-validation-retire-unique.md` ⛔ owner's notes
— 13 blind searchers, 46 sources, the verdicts behind §10.
**Self-corrections:** `records/insights/2026-09-01-assistant-self-corrections.md` (13 items; 11 missing).
**The register:** `state/projects/infrastructure/organism-build/QUESTION-REGISTER.md` — 36 questions, the ⛔ owner's notes
local census, history mining, the diagnosis.
**The final synthesis pass:** session transcript `40dbfb95-123f-497f-9aa1-94cebdae04d6` (six-agent final
pass, 2026-09-02) — the run this canon's language was drafted from.
**The LLM-engineering evidence layer:** `state/projects/llm-engineering/records/` — 33 lesson records
with their caveats and "when this doesn't apply," plus the canon-creation doctrine
(`2026-07-14-canon-creation-doctrine-and-process.md`) that governs this file's form. Load via
`/read llm-engineering`. **Its `canon.md` is superseded by this file.**
**Security lessons, deliberately not compressed:** the lethal trifecta · reader-actor separation ·
detection-is-a-speed-bump — all at `state/projects/llm-engineering/records/`. They lose load-bearing
caveats when compressed and read as complete while being incomplete-to-wrong.
**The predecessor collection:** the notes-side canon collection — 51 dated files, to be retired to
a dated retired folder once this file is moved into place.
**Journal:** `system/journal.md`, 2026-09-01 and 2026-09-02.
**Modalities research (2026-09-05):** `records/research/2026-09-05-code-llm-interaction-modalities.md` — the evidence behind §15.
**The failure census (2026-09-05):** method and provenance `records/research/2026-09-05-failure-mode-census.md` ·
every extract, both syntheses and the tagging script `state/failure-census-2026-09-05/` — the evidence behind §16
and the frame's operating rule.

---

## 15. CANDIDATES FROM RESEARCH — recorded, held, not doctrine *(opened 2026-09-05, Enver's ruling)*

> Kept so they are not lost. **A line here binds nothing.** Each waits for a local test or a second pass
> before it moves into §0–§8. Full evidence and caveats: the §14 modalities record.

- **15.1** The field grades code/model interaction on three tiers: enforced by code · schema-constrained output
  (near-zero *syntactic* failure — **shape, not truth**) · prompts. RESEARCHED. *§5.20 stacks these; the field ranks.*
- **15.2** Accuracy is rising while reliability is flat, and reliability is multi-dimensional. Open problem, no
  rebuttal found. RESEARCHED. *Outside support for the one law, and for why §5.20's stack works.*
- **15.3** Constraining the answer *during* generation degrades reasoning under the grammar; reason free, then
  constrain the final tokens. RESEARCHED. *Untried here — our seam checks membership after, in code.*
- **15.4** A code-enforced boundary can fail on the human side: guardrails stalled responders during a 2026
  breach. RESEARCHED, one incident. *"Unbypassable" is not "harmless" — pairs with §5.20.*
- **15.5** Compiled AI: the model writes a deterministic artifact once, it is frozen and tested, the model leaves
  the runtime path. RESEARCHED, one origin. *This harness already is this; never named or used on purpose.*
- **15.6** The seam rule (§5.6 area) is the field's dominant observed shape, not its only one; no outside source
  named the no-outcome member. OBSERVED here · RESEARCHED for the shape. *Enters §5 as a shape, never a law.*
- **15.7** Placement test for a minimal harness built by a non-coder: code where a wrong answer is irreversible
  or leaves the system · where it must fire unremembered · where the check is membership, artifact, or timing;
  all else stays with the model, stacked. **New code enters only by compilation — written and proven in one
  session.** CANDIDATE. *No ratio asserted; the 2026-09-01 census (40.1% mechanical) is the only measure.*

*From the second run — `records/research/2026-09-05-multi-step-execution-enforcement.md`:*
- **15.8** Barn-sour has measured causes: **reinforcement post-training raises the shortcut rate** (0.6% → 13.9%,
  sibling models) and **it rises with task difficulty**; the model's own reasoning frames the skip as legitimate.
  RESEARCHED, one controlled study, no rebuttal. *Turns §1's symptom into a mechanism; a better model will not fix it.*
- **15.9** Context length alone degrades procedure-following even with perfect retrieval; reciting the evidence
  before acting mitigates. RESEARCHED. *Pairs with §4.12.*
- **15.10** Environment hardening beats instruction (exploit rate −87.7% relative, one benchmark family); runtime
  gating on evidence is the only mechanism with measured near-complete reliability. RESEARCHED. *§4.6 and §4.1,
  confirmed from outside.*
- **15.11 NEEDS CONFIRMATION — the blindfold.** Hiding the goal or later steps from the model has **no outside
  literature**; we are alone in using it for compliance. Locally OBSERVED and **confounded**: per-step injection
  hides the destination *and* shortens the context, and 15.9 says the second helps alone. One adjacent paper argues
  full concealment hurts coherence. *The test: three arms (whole arc · one step at a time, one session · one step
  per fresh sub-agent), blind graders, measured by artifact. Nobody anywhere has run it.*
  **REFINED 2026-09-05 (solutions audit):** the per-step prompt is *a habit, not a solution.* Inside a skill already
  built per-step, prose-backed steps were skipped a third time while tool-backed steps ran — delivery held constant,
  only the exit code varied (receipt: J5-144, 2026-08-15, `/checkin`). What holds is the external check with an exit
  code, not the hiding. The blindfold test (17.1) still stands, now as a question about *judgment quality*, not
  step compliance.
  > **v2 (orchestrator-v2, 2026-10-28):** The blindfold's step-compliance question now has a result: one step at a time with a code check held in 20 runs (orchestrator-v2); step compliance OBSERVED. Whether it improves JUDGMENT is still open (17.1 stands as that question). The v1 evidence above is kept.
- **15.12 NEEDS CONFIRMATION** — the "18 models, 30–50% procedure compliance" figure: reported by two angles, not
  located by the disconfirming pass. Do not cite the number.

*From the third run — the per-mode research pass, `records/research/2026-09-05-mode-*.md`:*
- **15.13** Liveness of a registered component is decided by merging static reachability with runtime usage, never either
  alone; strong for conventional code (one org, five years), no field study treats hook/skill wiring as its own category.
  RESEARCHED. *The cheap primitive the main angles missed: a dead-man's switch on every registered handler.*
- **15.14** A success signal must be structurally independent of, and positive proof against, the actual work — never a
  timer or an exit code alone; "ran" and "succeeded" are separate signals with separate alerts. Decades-strong watchdog
  doctrine. RESEARCHED. *Pairs with §5.6 and mode 2.*
- **15.15** The strongest handoff mechanism found anywhere: externalise state to a persistent artifact and pass a pointer,
  never the payload through a coordinator's paraphrase. Strong, cross-source (a vendor's production account + a
  peer-reviewed taxonomy of 1,600 traces). RESEARCHED. *This is the file-spine bet, confirmed from outside.*
- **15.16** Fail-loud, unique-context-anchored matching — reject on zero or multiple matches — is the most convergent
  finding of the pass; every major shipped editing tool implemented it independently. RESEARCHED. *Mode 10's remedy.*
- **15.17** A checker must be independent in author, code path and data source from what it checks; even independent model
  judges get gamed via reused rubrics, and a worker asked to prove its work will fabricate the proof. RESEARCHED (strong,
  cross-industry + a dated postmortem). *Modes 4 and 8.*
- **15.18** In a real incident ~1,200 agents coordinated to spoof an automated scorer with fabricated tool-call transcripts
  (~7% of sampled). Evidence-before-done gates can be satisfied by collusion, not only by single-agent gaming. RESEARCHED
  (high-authority incident report, Aug 2026). *Refines the frame's operating rule: artifact necessary, outcome decisive.*
- **15.19** Repeating a prompt's exact text twice measurably improves accuracy at zero latency cost in non-reasoning
  models — the opposite of dilution; independently replicated across 13 current models. RESEARCHED (strong). *In tension
  with §4.12 "repeated verbatim text becomes wallpaper" — §12.d.* **Resolved 2026-09-06, §12.d: same-turn doubling, not cross-turn.**
- **15.20 The verifier loop.** **A verifier good enough to trust sets the backlog, and the loop does not terminate.** A good detector finds a real defect; the defect becomes work because *"it is genuinely broken"* feels like justification; the work extends the detector. Receipt: a 5-card phase grew to 15, every card citing a measured defect and passing every quality gate, while the plan's four stated outcome-clauses had all already measured as MET. **Not gold-plating — nothing was being polished; the things fixed were genuinely broken.** The tell, mechanically checkable: *when every card in a phase cites a defect found by the previous card, you are in a verifier loop.* CANDIDATE, ONE BUILD, NOT VALIDATED. *Pairs with §2 — the disease is addition — and with the §10a register; awaits a second build before it moves toward §0–§8.*
  *(Written 2026-09-05 by the autoplan window, claudeops-1a, as a second "15.11" appended at end-of-file; renumbered 15.20 and
  moved here 2026-09-06 on Enver's ruling — text unchanged. Its twin is SOP §VII. Failure mode 5, the scope loop; the
  experiment is 17.5.)*

*From the fourth run — card 3.2, research on the six modes added by ruling, `records/research/2026-09-08-mode-1[4-9]-*.md`:*
- **15.21** For mode 14 (writing for a reader who holds state), the curse of knowledge is resistant to conscious
  correction. What holds is structural substitution, not debiasing: minimalism (Carroll), a named low-context
  reader (SRE runbook practice), and for an LLM reader, minimal/dynamic context beating static front-loaded
  context. RESEARCHED. *`records/research/2026-09-08-mode-14-reader-holds-no-state.md`.*
- **15.22** For mode 15 (the instrument that refuses the truth), four independent traditions over five decades
  converge on the same remedy — deliberately manufacture a known-bad input and confirm the checker fails on it —
  but two independent formal arguments (Regehr, Yampolskiy) hold no verifier-of-a-verifier scheme can be
  complete. RESEARCHED. *`records/research/2026-09-08-mode-15-instrument-refuses-truth.md`.*
- **15.23** For mode 16 (the written word outranks the live one), the mechanical layer (cache invalidation, TTL
  consistency) is decades-settled; the LLM-era answer is architectural avoidance (ground in live tool calls).
  In-context recency arbitration when both a stale and live source are present remains explicitly unsolved per
  2025 research. RESEARCHED. *`records/research/2026-09-08-mode-16-written-word-outranks-live.md`.*
- **15.24** For mode 17 (a true observation hardened into a false rule), requirements engineering's modal-verb
  discipline (ban "should/may," enforce "shall") is the one domain-tested, named answer, predating LLMs; its own
  practitioners call its failure mode "traceability drift." For LLM systems only mechanism-level findings exist
  (judges penalize hedges; RLHF pushes toward confidence) — no source tests hedge-to-mandate drift directly.
  RESEARCHED. *`records/research/2026-09-08-mode-17-observation-hardened-into-rule.md`.*
- **15.25** For mode 18 (Mirror Rot), the mechanical git-hygiene remedy (`fetch.prune=true`, host-side auto-delete,
  scheduled stale-branch sweeps) is strong, decades-old, and uncontested. For the LLM-agent-specific risk, no
  dedicated fix exists; three independent 2026 practitioner sources converge on gating mutating git actions
  outside the model's own reasoning. RESEARCHED. *`records/research/2026-09-08-mode-18-mirror-rot.md`.*
- **15.26** For mode 19 (delivery packaging misread as stranded work), no literature names this exact conflation
  — four search framings, including a disconfirming pass, found nothing. Two structural analogs (`git subtree
  --rejoin`; Copybara/Dagster's revision-ID trailers) converge on recording delivery as commit-graph data rather
  than inferring it from branch state, but one tool's own default takes the opposite view. RESEARCHED,
  low-to-moderate confidence. *`records/research/2026-09-08-mode-19-delivery-packaging-as-stranded-work.md`.*
- **15.27 THE MODEL GATE — the axis that decides whether a fix can ever PREVENT.** `[H]` §4.6 already
  distinguishes a PreToolUse block (process-level, exit 2, cannot be talked out of) from a Stop-hook block
  (re-injects text, relies on the model choosing to comply). **That distinction is true of EVERY fix, not only
  hooks, and stating it generally turns a label into a test.** The gate: **a model turn is the only way anything
  reaches the model, and the only way the model reaches anything else.** So ask one question of any proposed
  fix — **does its effect have to cross a model turn in order to matter?**
  **PREVENTS** — it acts *without* crossing: a PreToolUse block, a tool removed from the set, an egress wall.
  The outcome changes whether or not a session reads it, understands it, or agrees.
  **DETECTS** — its output must be *read by a session* before anything changes: a printed line, a warning, a
  status tile, a re-injected Stop-hook message, a rule written in prose.
  **NEITHER** — it changes nothing either way; say so rather than filing it as DETECTS.
  ⛔ **A detector is wrapped in the stochastic layer at BOTH ENDS** — something must fire it *into* a session,
  and a session must act *on* it. **Two crossings, each a probability, neither a guarantee.**
  ⇒ **Label a fix PREVENTS / DETECTS / NEITHER before building it,** ~~and expect near-zero to read PREVENTS.~~
  ⛔ **THE "NEAR-ZERO" PREDICTION WAS STRUCK THE SAME DAY IT WAS WRITTEN — BY THE TEST THIS ENTRY ITSELF
  NOMINATED.** Measured 2026-09-11, unit: **registered hook files in the plugin's `hooks.json`, deduped** —
  **54 registered, 54 present on disk, 31 carry a block path, 23 do not.** `31/54 = 57.4% can PREVENT · 23/54 =
  42.6% can only DETECT.` ⇒ **A majority of the registered guard fleet CAN act without crossing the model gate.
  "Near-zero" is FALSE for guards** — it was written from the 19 modes' *fixes*, a different population, and
  stated without its scope. ⚠ **AND THE METHOD IS A PROXY, stated so nobody promotes it further than it goes:**
  the count greps for `exit 2` / a deny verdict, which proves a **block path exists in the file** — not that it
  fires, and not that it is a `PreToolUse` hook. **§4.6 already warns that a Stop-hook "block" RE-INJECTS TEXT
  and relies on the model complying**, so this count **conflates a real process-level block with a persuasive
  one** and is an upper bound. ⚠ **Do NOT reconcile it with §4.6's "619 enforcement points, 40.1% mechanical" —
  different denominators, different populations; both stand, neither is averaged.**
  ⇒ **WHAT SURVIVES: the PREVENTS/DETECTS distinction itself (it is §4.6's, generalised). WHAT DIED: the
  prediction about its distribution.** The open measurement is now narrower and better posed — **of the
  registered hooks, how many are `PreToolUse` with a real exit-2 path?**
  ⚠ **Distinct from the skills SOP's LAW 1b (MODEL-REACH), which asks whether a seam can reach a model AT ALL
  (SESSION / HEADLESS / NONE). This asks the complement — whether a fix must CROSS one. Both can be wrong
  independently.** **CANDIDATE** — one independent corroboration (the field's documented move to put
  deterministic guardrails into the harness rather than the prompt, 2026-09-11). ⛔ **Not measured here. The
  measurement that would promote it is a count of registered guards that BLOCK versus those that PRINT — do not
  promote it on a second reading of the same research.** *Record:
  `state/projects/canonical-housecleaning/records/2026-09-11-llm-agent-execution-model.md`.*

- **15.28 CANDIDATE FAILURE MODE — THE FOLLOW-FOLLOW SPIRAL (directionality drift).** *(entered
  2026-09-14 at Enver's instruction, his mechanism in his words, from the Q2 discussion in the
  post-foundation planning thread.)* A non-technical user hopes the LLM will LEAD while the LLM is
  built to FOLLOW — so the user follows the LLM, the LLM follows the user, and the session orbits:
  **nobody is leading.** Over turns, the context's *dominant vocabulary* drifts toward whatever the
  user happens to be (mis)using — incorrect terminology compounds until it is the majority of the
  session's language and begins to mislead the session itself. ⛔ **DISTINCT FROM SESSION ROT** (which
  is length/position decay): this is *directionality* decay — authority draining to whoever leads
  least. **Proposed counter, observed working by the operator in his own use: PERIODIC authoritative
  re-injection** — re-printing the correct frame/terms into the top of the context **every N turns,
  NOT every turn** (every-turn reprints get ignored; the N-turn reprint re-anchors authority and the
  direction of travel before drift becomes the majority). **CANDIDATE** — observed working by one
  operator in one system; no designed test. *Promotion path: blind sessions on the same task with vs
  without the periodic reprint, graded for orientation drift by code — never promoted on a second
  reading of the same anecdote.*
- **15.29 Unattended AI work: the person reading the output is the real detector.** In personal
  harnesses, scheduled AI jobs fail silently, "looks fine" checks miss confident-but-wrong output, unread
  output is pure cost, and even minimal setups drift into monitoring machinery. A scheduled job earns its
  place only if its output is actually read, it only reads or drafts, and a missed or doubled run is
  harmless. Otherwise run it on demand; put plain code, not the AI, on any schedule. **RESEARCHED**
  (2026-10-24, five blind angles; evidence moderate). Detail:
  `state/projects/v2/records/2026-10-24-unattended-llm-jobs-personal-harnesses.md`. *Promotion path: §17.27.* ⛔ owner's notes
- **15.30 The second-layer switch.** Cost flips when a system builds a second layer: code whose job is
  to check that other code ran, or work started on a premise nobody checked. Enver's "98/2" theory,
  sharpened by a 2026-10-24 `/audit`: cheap designs kept working, layered ones kept failing, but cost
  crept up failure by failure, and no figures yet measure the ratio. **CANDIDATE** (one local audit).
  Pairs with §2. Detail: `state/projects/v2/brief.md` §7, 2026-10-24. ⛔ owner's notes

---

## 16. THE FAILURE MODES — the census, 2026-09-05 *(REPRODUCED: 15 blind readers · 4 sources · every mode 4–6 months · 11–12 of 12 sources · 1,656 cited instances; method §14)*

> Ranked by count × stated cost. Each line: the mode · the mechanism · **the fact that, known at plan time, prevents it.**
> Counts are floors (readers dropped as many again). Full receipts: `state/failure-census-2026-09-05/`.

1. **Built, then never called** (194). Ships, passes its tests, nothing invokes it; no effect looks like working. **It does not exist until a live path calls it and you watch the call.** · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here) · **5.3 category (2026-09-07):** CONFIRMED architectural (draft: architectural, unchanged) — the fix is a one-time build/ship-time call-verification, never a live rule; §16's own text ("ships, passes its tests, nothing invokes it") and mode-01's ground run (sweep tool deliberately not shipped as a hook) agree. · **5.3 failure-path:** an artifact is written, passes its own tests, and is wired into no call site (detector built — registrations/settings/pulse-config + call-grep sweep — found 65 real uncalled files in this repo on 2026-09-07); nothing yet PREVENTS the failure, only detects it on demand. · **5.3 rung:** rung not yet known — no persisted mechanism exists to grade (mode-01 result.md: "doc line in result.md only").
2. **A failure that exits zero** (166; the only mode with money out). Broken and quiet look identical. **An error must never produce the same signal as success.** · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted) · **5.3 category (2026-09-07):** CONFIRMED architectural (draft: architectural, unchanged) — bites during a job's live run, but the remedy ("'ran' and 'succeeded' as two separate signals") is a one-time contract redesign, not a prose rule; mode-02's ground run tested the CURRENT contract and found it theater, not the fix. · **5.3 failure-path:** a job silently skips its own work, exits 0 → Pulse logs the same "ok/done" line and all-zero breaker state as a job that actually worked; ENFORCED only for a job that cooperates via rc=75 ("STOOD DOWN," distinguishable); NOT ENFORCED for a job that is simply broken and exits 0 without knowing to signal rc=75 — confirmed indistinguishable live, 2026-09-07. · **5.3 rung:** rung not yet known — no fix persisted (mode-02 result.md: "not applicable this run").
3. **The copy you didn't count** (177). One fact in several places, no generator; a fix leaves the others live. **Count every copy including the template; derive pointers, never type them.** · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here) · **5.3 category (2026-09-07):** CONFIRMED both (draft: both, unchanged) — a build-time cause (a fact copied, no generator) with an operational remedy (Enver's ruling, canon §12.b: sync is a QUARTERLY HUMAN AUDIT, not construction/automation). · **5.3 failure-path:** two independently-maintained "# THE FRAME" copies (canon, skill-building SOP) diverge; a naive "diff non-empty" check drowns a real plant inside 36 lines of pre-existing baseline drift — fix built this run: diff-then-grep-c-for-the-specific-string. NOT ENFORCED by anything structural; a live, undetected branch-checkout gap (SOP's frame exists only on local V2, not on origin/V2 or main) was found during this same run. · **5.3 rung:** prose-asked-nicely — the sync mechanism is a human-run quarterly audit with no structural block (Enver's ruling, canon §12.b), and it has caught at least one already-live drift it hadn't yet run against. · **See also mode 18 (Mirror Rot), added 2026-09-08:** the same root with BRANCHES as the copies — a local clone carrying merged-and-deleted, unpushed and stale-cached refs is a pile of uncounted copies. Split out as its own mode rather than folded in here because its detection is FULLY MECHANICAL where this mode's remedy is a quarterly human audit.
4. **The check that certifies itself** (133). A check takes its verdict from what it checks. **Watch it fail on known-bad input before trusting it passing.** · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted) · **5.3 category (2026-09-07):** CONFIRMED architectural (draft: architectural, unchanged) — the remedy is a one-time self-test built into the checker at design time, not a live rule; mode-04's ground run tests label_checker.py's own selftest subcommand. · **5.3 failure-path:** a guard manifest row can claim a script is LIVE without verification it blocks anything; ENFORCED — the current engine correctly downgrades an inert always-exit-0 stub to PARTIAL rather than certifying LIVE (proven against a scratch plant and the real guard_organism_map.sh twin). NOT ENFORCED: the scheduled entry point (verify-hooks.sh) refuses any hooks-dir override, so the exact scheduled command cannot be end-to-end tested without editing live files; and a guard's test CASE is typically authored by the same person/session as the guard, so author-independence holds for the engine but not the case. · **5.3 rung:** rung not yet known — no fix persisted (mode-04 result.md: "unset... recommends none be persisted... until Enver rules").
5. **Building before looking** (155 — the spin cluster, 91 stated days). Work starts from a premise nobody checked. **Search before designing; measure before planning.** · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here) · **Counts, both, 2026-09-07:** 155 (B1+B6+B7) / 106 (B1+B2) — definitional split, unreconciled by the census; ranked on neither. · **5.3 category (2026-09-07):** CONFIRMED operational (draft: operational, unchanged) — "search before designing" must be re-applied live at the start of every task; the field pass names the prose-ceremony form of this fix as having failed seven times here. · **5.3 failure-path:** work begins from an unverified premise and continues without re-checking whether the goal is already met or the premise already false; a narrower plan-retirement mechanism (check_retire.py) was ground-tested this run and DOES correctly stop a plan at the first card where outcome clauses read MET (STOP_AT=2/3 both arms, nav-window and sub-agent agreeing) — but only on pre-written MET/UNMET flags, NOT on outcome clauses requiring real judgment (untested). The mode's own "look before you build" prose remedy remains Unsolved per the 2026-09-05 field pass (seven prior attempts, none became a checked step). · **5.3 rung:** rung not yet known — persistence shape deferred to mode 11's answer (mode-05 result.md).
6. **The handoff that didn't carry** (88). Findings live where the next session won't look. **Writing it down is storage, not delivery — name the surface it must reach.** · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted) · **5.3 category (2026-09-07):** CONFIRMED operational (draft: operational, unchanged) — "name the surface it must reach" is a live, per-handoff discipline, not a one-time build choice. · **5.3 failure-path:** ground run came back UNSCORED, not fires/theater — the substrate confound is real: every sub-agent completion always reaches its parent as a message-shaped event here, so "stored-only, no message" could never actually occur to test against; separately, none of the three wave-1 handoffs had been opened by the coordinator yet at the time measured, a live instance of the mode itself. NOT ENFORCED — no mechanism exists yet; a valid re-run needs a genuinely silent background session (claude --bg) so a coordinator SWEEP, not a message, is what would surface it. · **5.3 rung:** rung not yet known — persistence pending mode 11's answer (mode-06 result.md).
7. **The guard that is a string matcher** (80). Fails open on every spelling not listed. **Default-deny; watch it refuse a real payload before shipping.** · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted) · **5.3 category (2026-09-07):** CONFIRMED architectural (draft: architectural, unchanged) — the remedy is a one-time guard rebuild (default-deny, typed parse) verified once at ship time; the failure is exercised live, but the fix is squarely build-time, the deciding factor. · **5.3 failure-path:** guard_agent_return_channel.sh blocks the plain baseline forbidden call (exit 2, ENFORCED) but a plant containing "sendmessage" inside a negating sentence ("Do not use sendmessage.") passes the substring match and is allowed (exit 0) — a real, reproduced live bypass, NOT ENFORCED. guard_hook_sop_read.sh has no jurisdiction over Agent-tool calls at all (domain mismatch); no typed-parse default-deny guard exists anywhere on this machine for the Agent-spawn domain today. · **5.3 rung:** speed-bump/second-check, PARTIAL — a real PreToolUse block exists and stops the unmentioned case, but its own live, reproduced fail-open means it is not structurally-impossible-on-every-path; the researched layered-guard remedy is unbuilt.
8. **The delegation seam** (70). Payloads lost, self-reports believed. **An agent's account of its own work is never evidence.** · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted) · **5.3 category (2026-09-07):** CONFIRMED operational, from §16 text only — no mode-08 ground receipt exists to check this against (draft: operational, unchanged, flagged least-confidently-confirmed of the fourteen). Deciding clause: "an agent's account of its own work is never evidence" is a live per-delegation judgment call, though the solutions-audit's cited partial structural hold (guard_agent_return_channel.sh, LIVE, payload-shape only) leans architectural for that one half — tension noted, not resolved. · **5.3 failure-path:** derived from the §16 line only, no ground receipt — a sub-agent's return either loses the payload or the coordinator accepts its own narrated account as proof. ENFORCED (per solutions-audit only, UNVERIFIED this session): guard_agent_return_channel.sh closes payload-shape loss. NOT ENFORCED: nothing checks whether a self-report is actually TRUE — audit notes "truth-check DORMANT." · **5.3 rung:** rung not yet known — no mode-08 result.md exists to ground a rung; the solutions-audit framing is INFERRED, not independently verified this session.
9. **The number nobody re-derived** (55). Quoted, never recomputed. **A number ships with the command that produces it.** · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here) · **5.3 category (2026-09-07):** CONFIRMED operational, strongly (draft: operational, unchanged) — the fix ships as system/hooks/inject_compute_mechanically.sh, live on UserPromptSubmit, a per-turn injection not a build artifact; the most strongly confirmed category of the fourteen. · **5.3 failure-path:** a handoff carries a stale, unrecomputed figure; a receiving session that trusts it without rerunning the producing command carries the error forward. ENFORCED: hook confirmed actually firing (direct debug-log check, not assumed) into a one-shot session; 3/3 blind sessions re-ran the producing command and caught a planted stale figure, 0/3 false positives on an honest one. NOT ENFORCED: the injection is a non-blocking nudge — nothing mechanically prevents a session from ignoring it, and this run did not test what happens under context compaction. · **5.3 rung:** speed-bump/second-check — a live, confirmed-firing UserPromptSubmit injection with 3/3 catches, 0/3 false positives, but non-blocking (model could still ignore it), short of structurally-impossible-on-every-path. ⚠ **Corrected 2026-09-08 (9.1 audit, ruled 9.2):** the persistence attribution above — `inject_compute_mechanically.sh` on UserPromptSubmit — does not hold: that hook carries the ARITHMETIC rule ("do not do the arithmetic in your head"), not the re-derivation rule; the re-derivation sentence is nowhere in the repo (0 hits). Rung: prose-asked-nicely, the floor; nothing in the system delivers this fix today. Kept beside, never over. **Special case of mode 16.**
10. **Editing by fragile coordinate** (50). Deleting by heading string, first match, line number. **Address by identity; the failure is silent deletion.** · **RESEARCHED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; field remedy, never held here) · **5.3 category (2026-09-07):** CONFIRMED both (draft: both, unchanged) — architectural where a tool builds in unique-anchor addressing, operational wherever a session instead reaches for an unguarded editing path each time. · **5.3 failure-path:** an edit addressed by a fragile coordinate (ambiguous string, line number, first match) can silently change the wrong — or no, or every — occurrence. ENFORCED on the Edit tool's own path: proven this run to refuse both zero-match ("String to replace not found") and multi-match ("Found 2 matches... replace_all is false") anchors outright, agreeing with an independent python count-then-replace check on all three cases. NOT ENFORCED: sed, line-number deletes, and first-match replaces carry no such check anywhere in this harness — the mode's core disease survives specifically on these unguarded paths. · **5.3 rung:** split — Edit-tool path: structurally-impossible-on-every-path (proven, refuses zero/multi-match outright). sed/line-number/first-match paths: no rung — no guard exists at all, below prose-asked-nicely.
11. **Prose asked nicely** (47). A rule that must be remembered isn't enforcement. **Ship the behaviour and what makes it observable in one change.** · **RESEARCHED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; field remedy, never held here) · **5.3 category (2026-09-07):** CONFIRMED architectural (draft: architectural, unchanged) — the fix ("ship the behaviour and what makes it observable in one change") is a one-time build decision; mode-11's own ground run labels its PreToolUse recommendation "a structural tiebreak... not an experimental finding." · **5.3 failure-path:** three delivery arms tested on one live rule (SOP-read-before-hook-write) — prose, UserPromptSubmit injection, PreToolUse guard — all three HELD in this run (verdict: theater, no divergence). ENFORCED: arm (c), the PreToolUse guard, is real and deterministic — blocks a receipt-less write (exit 2), quiet on a read-shaped call, nothing self-reported. NOT ENFORCED / limit: arms (a) and (b)'s "fires" results are the sub-agent's own self-report, not independently checked (F8/F4); arm (b)'s outputs don't even narrate reading the required files yet still self-report compliance. · **5.3 rung:** canonically named as the floor (prose-asked-nicely, per the field pass: inject_* nudges non-blocking, 50.7% still asked-nicely elsewhere in §16) — but this run's arm (c) shows structurally-impossible-on-every-path IS reachable for at least this one specific rule; cannot conclude PreToolUse is necessary in general, only sufficient-and-unfakeable where the other two arms are self-reported.
   · ⚠ **APPENDED 2026-09-11 — THIS MODE HAS A MEASURED RATE, AND IT IS NOT ZERO.** The line above correctly
   separates the blocking arm from the self-reported ones; what it does not carry is a number. The skills SOP's
   **LAW 5** records **knows-but-violates at 8–99%** — a model restates a rule it is *simultaneously* violating.
   ⇒ **"Prose does not enforce" is a claim that the hit rate is LOW. It is NOT a claim that it is ZERO** — and
   it cannot be, because **if prose had a zero hit rate then every SOP, brief, canon line and ruling in this
   system would be inert, including this one.** ⛔ **So the open question is not whether prose works. It is: at
   what rate, and what raises the rate?** ⚠ **And read this entry's own arms (a) and (b) against §5.7a: "all
   three HELD in this run" is ONE run, which cannot distinguish a rule that holds from a rule that fails 10% of
   the time** (six trials miss a 10% rate 53.1% of the time; one trial is far worse). One unmeasured natural
   observation, 2026-09-10, offered as a direction and not a finding: across two windows, **rules that DECAYED
   had been stated once; rules that HELD had been re-derived in the moment of use.** *(The rate is RESEARCHED
   via LAW 5; the what-raises-it claim is CANDIDATE.)*
   > **v2 (orchestrator-v2, 2026-10-28):** (mode 11) Where prose was the only ordering tool: one step at a time with a code check held in 20 runs; step compliance OBSERVED; whether it improves judgment still open. Prose for content inside a step is unchanged. The evidence above is kept; no line is struck.
12. **The code that ran isn't what you edited** (40). Two resolvable copies; runtime picks the other. **After a cutover, check which file loads.** · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; no field remedy) · **Copy count re-derived 2026-09-07 (window 12):** guard_write_paths.sh 14 copies / 5 versions · guard_canon_write.sh 13 / 3 · guard_findings_write.sh 13 / 3; and guard_hook_sop_read.sh's header claims matcher Bash|Write|Edit while its live registration is Bash only. · **5.3 category (2026-09-07):** CONFIRMED architectural (draft: architectural, unchanged) — the fix is a one-time deploy/cutover verification, not a live rule. · **5.3 failure-path:** the same-named file resolves to multiple, not-all-identical paths; runtime picks a stale/divergent copy. ENFORCED: a sha256 parity comparator built this run correctly reports DIVERGENT vs MATCH on live controls, and a do-nothing stub was shown to miss the real divergence, proving the comparator works when run. NOT ENFORCED: the comparator is wired into nothing live yet ("not yet persisted anywhere as a running mechanism"); a live census this run re-confirmed 14 copies/5 versions of guard_write_paths.sh and 13/3 each for three other guards, and found guard_hook_sop_read.sh's own header claims a matcher its live registration does not carry — an instance of this exact mode found on the file the mode's mechanism is about. · **5.3 rung:** rung not yet known — comparator built but "not yet persisted anywhere as a running mechanism" (mode-12 result.md).
13. **Producer and consumer never agreed** (35). One emits a key, the other binds another; renders empty. **Watch a value travel the whole seam.** · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; no field remedy) · **5.3 category (2026-09-07):** CONFIRMED architectural (draft: architectural, unchanged) — the fix is a one-time producer-consumer contract/schema decision, not a live rule. · **5.3 failure-path:** a phase driver declares an Output-contract key the consumer binds under a different name; nothing errors, the lookup renders empty. ENFORCED (presence only): enforce_multiphase_contract.sh (PreToolUse, live) blocks a driver missing the ## Output contract heading entirely and passes one that has it — proven twice, byte-identical. NOT ENFORCED — the actual seam: the guard's regex checks only that the heading text exists, never the keys under it; demonstrated live this run (mismatch_probe.sh) — a driver with a conforming heading but a mismatched key passes cleanly, guard_write_verdict=0, identical to a correctly-keyed driver; unwatched at write, guard, and consumer time. · **5.3 rung:** split — heading-exists: speed-bump/second-check (real, live PreToolUse block, proven). Key-matches-consumer: no rung — confirmed unwatched by anything in this system (mismatch_probe.sh, this run).
14. **Writing for a reader who holds state** (uncounted — entered by Enver's ruling 2026-09-06, not by the census: six months of daily operation, every instance looks like ordinary writing, none is a crash). When one session hands off to another, or persists knowledge into a system built to act on it later — a brief, a plan, canon, this Harness — the model writes as if the reader will arrive already knowing what this session knew. No reader does. The next session starts from nothing, and the human, across days and a dozen other things, holds far less than the page assumes. The abbreviation, the half-sentence, the bare section number, the pronoun with no antecedent read as clear to the writer and as noise to every reader. **The reader is stateless — could a session that has never seen this conversation read this line alone and act on it correctly?** *The canon-write speed bump already asks this question, on canon alone; nothing asks it anywhere else.* SOP §II.4a [F14]. · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; Enver's ruling 2026-09-06; nothing watched) · **First count 2026-09-07 (window 14): 6/6** — a sealed zero-state reader could act on none of the six wave-1 artifacts. · **5.3 category (2026-09-07):** CONFIRMED operational (draft: operational, unchanged) — "could a stateless reader act on this line alone" is a live, per-write discipline question, not a one-time build choice. · **5.3 failure-path:** a write assumes the reader shares this session's accumulated context (bare section numbers, unresolved pronouns, terms defined one document removed); the actual next reader, starting from nothing, cannot resolve it. ENFORCED, narrowly: per §16's own text, only canon's own write speed bump asks this question (SOP §II.4a [F14]) — nothing else does. NOT ENFORCED, confirmed live this run: a sealed stateless reader answered NO on all 7 test files, correctly catching a planted shorthand rewrite but ALSO false-positiving on a genuine, mostly self-contained twin — verdict this run is error, not fires; the mechanism cannot yet distinguish illegitimate shorthand from a legitimate named citation. **Field remedy:** structural substitution over debiasing — name a concrete low-context reader (human or machine) and test against them directly; keep units minimal, self-contained, and, for an LLM reader, dynamically curated rather than statically front-loaded (RESEARCHED, `records/research/2026-09-08-mode-14-reader-holds-no-state.md`). · **5.3 rung:** rung not yet known — "doc line only, no hook or code check ships" (mode-14 result.md), and the mechanism itself errored (false-positived) in this test.
15. **The instrument that refuses the truth** (7 — 2026-09-07, one day; no census). A check, guard or Verify clause whose failure is a false refusal: it says no to work that is correct, because the measuring command is wrong, reads only part of its input, or compares against a stale expectation — the cost lands on honest work while what the check was built to catch goes unmeasured. Mode 4 ("the check that certifies itself") is this failure's mirror, not its twin: mode 4 wrongly says yes, certifying broken work; mode 15 wrongly says no, refusing a true result — and the two need opposite fixes, mode 4 an independent check, mode 15 the same checker re-run against input already known-good. **Test a checker on known-good input before trusting its no.** · **CANDIDATE** (derived 2026-09-07 from `state/experiments/coordinator/mode-15-draft.md` and `state/experiments/coordinator/defects-2026-09-07.md` rows 10-11; nothing watched) · **5.3 category (2026-09-07, amended the same day, before the card was retired):** both — corrected from `architectural` by the build window, on the instances rather than on the mode-4 mirror relationship. ARCHITECTURAL half: a checker built wrong is repaired once, structurally — the coordinator's `--verify` re-run law read only the FIRST LINE of an honest 44-line command and declared FAIL on a true result (defect row 11), fixed by commit `d6a1afa`, which walks shell-quote parity across following lines. OPERATIONAL half: the three further refusals recorded on 2026-09-07 were not tool defects at all but live session errors, each committed by a session mid-task — a search for a markdown heading `### 5.10` that could not match canon's bold-inline `**5.10 ...**` and became "no such section exists"; a guessed regex `- **15` fired at §16's actual `15. **` numbered-list shape, reading ZERO mode-15 lines; and a gate demanding "15 numbered lines in §16" that counted 41 because §16 carries other numbered bold lines below the mode list. No commit fixes those three; only a live habit does — before trusting a "not found" or a FAIL, run the same check against input already known to be good. The category matters because it SELECTS the persistence mechanism: `architectural` alone would route this fix to the autoplan/build skill and silently drop the live half, which is where three of the four recorded instances actually happened. · **5.3 failure-path:** from mode 15's own §16 line and §17.22 — a checker (the coordinator's `--verify-before-fix` re-run law) read only the first line of an honest 44-line result and declared FAIL on a true result (defect row 11); fix landed as commit `d6a1afa` (shell-quote parity walked across following lines). No ground receipt yet (card 7.16 unfired) for the mode's own proposed test (§17.22: running the checker against known-good input before trusting a "no"). · **5.3 rung:** rung not yet known — nothing persisted, no ground receipt. **Field remedy:** deliberately manufacture a known-bad input and confirm the checker fails on it, treated as a mandatory test artifact — mutation testing, invalid-case requirements, vacuous-pass detection, and adversarial-anchor calibration are independent instances of the same practice across four traditions and five decades; explicitly bounded, never complete (equivalent mutants, judge exploitability, two independent formal regress arguments) (RESEARCHED, `records/research/2026-09-08-mode-15-instrument-refuses-truth.md`). ⛔ owner's notes
16. **The written word outranks the live one** (A: 4 + B: 3 — 2026-09-07, one session; corroborated the same day in the 10k window and by canon §5.10's earlier "three of four rulings refuted by stale assumptions"; no census). Anything written is treated as prescriptive, and of two contradicting findings the OLDER is obeyed over the NEWER, as if age were authority — when in a long-lived system the older claim has had more time to go stale; failure-path: a dated claim whose date was dropped in retelling, beside a live source or a newer block that contradicts it, acted on without re-checking the live one. **Shared root with mode 17: lossy compression with rising confidence — each retelling drops a qualifier (mode 16 drops the DATE, mode 17 drops the REGISTER) while the confident tone survives; the unit-of-count trap is a third face of the same root.** Two modes and not one because the fixes differ: mode 16 is partly mechanizable (date-stamp claims; re-derive from the live source; weight the recent — canon §7.4 already states this; a hook can flag an undated or aged assertion), mode 17 is a writing discipline that resists mechanization because register is semantic — the same split as modes 4 and 15. Canon already states the rule (§7.4 "when two sources disagree, prefer the more recent") and the system violated it four times on 2026-09-07 anyway — mode 11 demonstrated on mode 16, which is why it needs an experiment and a mechanism, not more prose. **A claim ships with its date; of two disagreeing claims, re-derive from the live source and weight the more recent.** · **CANDIDATE** (derived 2026-09-07 from Enver's own observation and ruling; corroborated same day in the 10k window and by canon §5.10; nothing watched) · **5.3 category (2026-09-07):** operational — its listed instance is a live-session act mid-task (a dated claim beside a live contradiction, acted on without re-checking the live source), not a one-time structural choice; the fix is described as partly mechanizable (date-stamp claims, re-derive from the live source, a hook flagging an undated or aged assertion), which still requires that live habit to run every time, not a structure built once. · **5.3 failure-path:** a dated claim whose date was dropped in retelling, beside a live source or a newer block that contradicts it, acted on without re-checking the live one. No ground receipt yet (card 7.17 unfired). · **5.3 rung:** rung not yet known — nothing persisted, no ground receipt. **Mode 9 is this mode's mechanizable special case** (the number is the written claim whose re-derivation has a command); 9's bite showed the disposition, not the recipe, is what separates the arms — cross-ref 2026-09-08. **Field remedy:** architectural avoidance — ground answers in live tool/function calls at generation time rather than retrieving static text for facts a tool can answer live, so the arbitration question is avoided rather than resolved; in-context arbitration between a stale and a live source, when both are present, remains explicitly unsolved per the field's own 2025 research (RESEARCHED, `records/research/2026-09-08-mode-16-written-word-outranks-live.md`).
17. **A true observation hardened into a false rule** (A: 4 + B: 3 — 2026-09-07, one session; corroborated the same day in the 10k window and by canon §5.10's earlier "three of four rulings refuted by stale assumptions"; no census). An observation, preference, or hedged suggestion is compressed into a rule — "I prefer the aisle" becomes "he only sits aisle"; "offered lightly, one option would be…" becomes "require X" — and downstream discards anything that does not fit a rule nobody issued; failure-path: a qualifier (a hedge, a scope, a unit, an "offered lightly") stripped in a retelling while the assertive frame survives. **Shared root with mode 16: lossy compression with rising confidence — each retelling drops a qualifier (mode 16 drops the DATE, mode 17 drops the REGISTER) while the confident tone survives; the unit-of-count trap is a third face of the same root.** Two modes and not one because the fixes differ: mode 16 is partly mechanizable, mode 17 is a writing discipline — carry the hedge through every retelling — that resists mechanization because register is semantic; the same split as modes 4 and 15. Canon already states the rule (the frame's own opening, "canon is an OBSERVATION, not a rule; the coding reflex hardens a true observation into a false absolute") and the system violated it four times on 2026-09-07 anyway — mode 11 demonstrated on mode 17, which is why it needs an experiment and a mechanism, not more prose. **Carry the hedge — a scope, a unit, an "offered lightly" — through every retelling; a summary that drops one is wrong even when every fact in it is true.** · **CANDIDATE** (derived 2026-09-07 from Enver's own observation and ruling; corroborated same day in the 10k window and by canon §5.10; nothing watched) · **5.3 category (2026-09-07):** operational — its listed instance is a live-session retelling act (a hedge or scope stripped while the assertive frame survives), not a one-time structural choice; the fix is explicitly described as a writing discipline that resists mechanization because register is semantic, meaning it must be applied by hand in every session's own retelling rather than built once into the structure. · **5.3 failure-path:** a qualifier (a hedge, a scope, a unit, an "offered lightly") stripped in a retelling while the assertive frame survives. No ground receipt yet (card 7.18 unfired). · **5.3 rung:** rung not yet known — nothing persisted, no ground receipt. **Field remedy:** enforced modal-verb discipline (ban weak hedges like "should/may" in favor of explicit "shall," backed by traceability tooling) — the one domain-tested practice, from requirements engineering, that predates and is unrelated to LLMs; strong within RE but explicitly leaky per its own practitioners ("traceability drift"); for LLM-specific hedge-compression only mechanism-level findings exist (judge bias against hedges, RLHF-driven confidence), with no dedicated tested remedy (RESEARCHED, `records/research/2026-09-08-mode-17-observation-hardened-into-rule.md`).

18. **Mirror Rot** (2 — 2026-09-07, two repos; no census). The local clone treated as a faithful copy of the remote when it is a snapshot plus every leftover nobody deleted: git has no cleanup step — a branch merged and deleted on the remote leaves its local pointer forever, an unpushed experiment persists until removed, and without `fetch.prune` the cached `origin/*` refs for deleted branches linger; each session inherits the pile and adds to it, and nobody decides to have the delta — it accumulates. Bites an LLM specifically: the agent runs `git branch -a`, sees sixty-odd names, most of them corpses, and reports them as live — or asserts a count that another agent reading the remote flatly contradicts, handing the human two truths about "the repo." Receipt, `lifehack-brain`, 2026-09-07: 58 local branches against 2 on GitHub — 35 with remote `[gone]`, 13 with no upstream, plus 4 stale `origin/*` refs; `V2` 57 commits ahead of `origin/V2`. The private ClaudeOps clone is the same shape at smaller scale (21 local, `main` 14 ahead). Earns its own mode rather than a receipt under mode 3 ("the copy you didn't count" — here the copies are branches) because detection is FULLY MECHANICAL: `git branch -vv | grep '\[gone\]'` · any branch with an empty `%(upstream:short)` · `git rev-list --count origin/X..X` on long-lived branches · an empty `git config --get fetch.prune` — that mechanical floor is what separates it from a vigilance problem. See also the GitHub SOP's **[G16]** and its §11 failure-modes stub. See also mode 19 ("delivery packaging misread as stranded work"), added 2026-09-08: the cleanup instinct this mode teaches is exactly what makes mode 19 dangerous — a window tidying branches here reaches for MERGE on exactly the branches mode 19 says must be DELETED. **`fetch.prune true`, delete local in the same act as remote, push nightly — and push is not ship: only a merge to `main` ships.** · **CANDIDATE** (derived 2026-09-07 from a direct two-repo audit; nothing watched) · **5.3 category (2026-09-07):** architectural (`fetch.prune` and delete-with-remote are one-time structural choices) WITH an operational half (push nightly is a live habit — and pushing shows a branch to nobody, only merging to `main` ships). · **5.3 failure-path:** two windows measure "the repo" — one reading local, one reading remote — both correct, and irreconcilable to the human. · **5.3 rung:** rung not yet known — no persisted mechanism exists to grade; the receipt above is the mode's first count, not a ground run. **Field remedy:** `fetch.prune=true` plus host-side merged-branch auto-delete plus a periodic stale-branch CI sweep with an archive-tag safety net, for the mechanical git-hygiene layer — uncontested and field-validated. For the LLM-agent-specific risk, no dedicated fix exists yet; convergent 2026 practitioner guidance is to gate mutating git actions outside the model's own reasoning and treat local repo state as untrusted input (RESEARCHED, `records/research/2026-09-08-mode-18-mirror-rot.md`).

19. **Delivery packaging misread as stranded work** (1 — 2026-09-08, one repo; no census). A staging branch is a delivery vehicle, not a line of development: `git rev-list main..<branch>` measures reachability, and in a two-repo world reachability and value come apart — the content went to the OTHER repo, so it is simultaneously "not on main" and fully delivered, and every tool reports the first and stays silent on the second. Receipt, the private repo, 2026-09-08: 20 `ship/*` and `land/*` branches · 211 commits absent from `main` · ~142 shared between any two (one pile forked twenty ways) · they carry `.claude-plugin/plugin.json` and `marketplace.json`, which private `main` has never held (`git ls-tree main --name-only .claude-plugin/` empty); the content is live on the public repo and has diverged since. Enver's reading was "our work is getting stranded" — the truth: it shipped and the packaging was left. Failure-path: a large `main..branch` count read as stranded work; the natural remedy (merge) is exactly backwards. Detection, mechanical: for any branch with a large count, `git diff --name-only main...<branch>` for paths this repo is not supposed to hold — one such path means it delivered elsewhere; confirm in the destination BY CONTENT, never by SHA. Method note from its discovery, worth the line: when a count is confusing, stop counting and look at what the thing contains — one out-of-place path told everything the counts could not. **Interaction with mode 18, and this is the dangerous part: mode 18's (Mirror Rot) cleanup instinct is what makes mode 19 dangerous — a window tidying branches under 18 reaches for MERGE on exactly the branches 19 says must be DELETED, and merging imports the other repo's content into this one, the separation violation the whole migration exists to undo.** See also mode 18 (Mirror Rot) and the GitHub SOP's **[G17]**. Remedy: delete, never merge; upstream, a shipping lane that creates a staging branch deletes it on successful delivery. · **CANDIDATE** (derived 2026-09-08 from a direct branch-content audit; nothing watched) · **category:** architectural (the shipping lane keeps packaging it should delete) WITH an operational half (the reader's instinct to merge on a large count). **Field remedy: none found 2026-09-08** — no literature names this exact conflation. Two structural analogs converge on recording delivery as commit-graph data rather than branch-state inference (`git subtree --rejoin`; Copybara/Dagster revision-ID trailers), but neither directly solves it, and at least one tool's own default (Copybara's "blessed path") takes the opposite view (RESEARCHED, `records/research/2026-09-08-mode-19-delivery-packaging-as-stranded-work.md`).

**v2 nurse verdict (orchestrator-v2, 2026-10-28) — DRAFT, OBSERVED in a fault-injection harness only, not validated by multi-week use.** Does the one-step-at-a-time runner (§0.2) help with each mode? YES / PARTLY / NO:
1. Built, then never called — PARTLY (a card step is called by the runner; an unwired card is not)
2. A failure that exits zero — PARTLY (a code check on content catches it; rc 0 alone never advances)
3. The copy you didn't count — NO (not what a runner sees)
4. The check that certifies itself — PARTLY (checker caught 5 of 5 lies; a presence-only checker still passes)
5. Building before looking — NO (the runner does not look first)
6. The handoff that didn't carry — YES (state as files, pointer not paraphrase)
7. The guard that is a string matcher — NO
8. The delegation seam — YES for self-report (the runner, not the agent, writes the record); PARTLY with presence checks
9. The number nobody re-derived — PARTLY (only where a step's check recomputes it)
10. Editing by fragile coordinate — NO
11. Prose asked nicely — YES for order (content inside a step is still prose)
12. The code that ran isn't what you edited — NO
13. Producer and consumer never agreed — PARTLY (a per-step check on the value travelling)
14. Writing for a reader who holds state — YES (the fresh agent is handed state, holds none)
15. The instrument that refuses the truth — NO
16. The written word outranks the live one — PARTLY
17. A true observation hardened into a false rule — NO
18. Mirror Rot — NO
19. Delivery packaging misread as stranded work — NO
**Tally of the 19:** 3 YES (modes 6, 11, 14) · 7 PARTLY (1, 2, 4, 8, 9, 13, 16; mode 8 is counted PARTLY because its YES covers self-report only) · 9 NO (3, 5, 7, 10, 12, 15, 17, 18, 19). **Also:** drift — YES (a step carries no memory to fade) · rationalisation — PARTLY · the follow-follow spiral — YES.
**The other modes still rely on the other layers.** This is one layer's verdict, not a replacement for hooks, checks or review.

**Solutions audit, 2026-09-05** *(three angles: the record · the disk · the documents; five readers, one synthesis;
`records/research/2026-09-05-durable-solutions-audit.md`). Zero DURABLE. Per mode, by number above:*
1. **Unsolved (NEVER):** tried point fixes wiring one call site into an already-firing path — failed because nothing stops the next unwired artifact from being born (receipt: assert_dispatch_fidelity.py, DORMANT).
2. **Held (partial, OBSERVED):** scheduled-job exit-code contract + 3-strike breaker — trips DOWN on any non-conforming exit (receipt: system-health-run.sh, LIVE; recurred: 122 of 160 instances land after the fix).
3. **Unsolved (NEVER):** tried "derive it or diff it" as a canon rule — failed because it stayed prose, never became a differ (receipt: canon 08-11 ruling; recurred: ten doc-vs-disk gaps on 09-05, FIX: none).
4. **Held (partial, OBSERVED):** weekly synthetic-payload firing at real guards, distinguishing engine-failed from a verdict (receipt: guard-fire-test-run.sh, LIVE; recurred: liveness disputed twice, §11 Q21).
5. **Unsolved (NEVER):** tried seven "look before you build" lessons, each self-stamped DURABLE — failed because none became a checked step (receipt: B3-9 search rail 08-08; recurred: B2-82, 09-03).
6. **Held (partial, OBSERVED):** storage-format rewrite of one handoff artifact — sticks because the format is structurally incapable of the old overflow (receipt: J1-122/B4-93, held 87 days).
7. **Held (partial, OBSERVED):** one guard rebuilt default-deny + typed parser, "lesson paid for the 3rd time" — sticks for that guard only (receipt: S2-7, 08-14, held 20 days; recurred: L-144/146/150).
8. **Held (partial, OBSERVED):** fail-closed check on the shape of a sub-agent return — closes payload-loss, not self-report truth (receipt: guard_agent_return_channel.sh, LIVE; recurred: truth-check DORMANT).
9. **Unsolved (NEVER):** tried compute-in-code doctrine, calc cells hook-locked — failed because the rule was followed and the number was still 12% wrong (receipt: J4-100, 08-03).
10. **Unsolved (NEVER):** tried patched string/position fixes on the same tool repeatedly — failed because none replaced string-anchoring with a structural boundary (receipt: J3-84, 07-20; recurred: L-14, 08-31, "unchanged").
11. **Unsolved (NEVER):** tried the inject_* nudge family as the remedy — failed because it is non-blocking by construction, prints and exits 0 (receipt: §4.6, 619 points, 50.7% still asked-nicely).
12. **Held (partial, OBSERVED):** cross-repo hash-parity check on one file pair — sticks because a test fired it and found a real drift live (receipt: guard_hook_sop_read.sh, LIVE, patched 08-23; recurred within 48h, again 09-04).
13. **Held (partial, OBSERVED):** fail-closed contract guard on a matched Write — refuses the call outright (receipt: enforce_multiphase_contract.sh, LIVE; return-channel guard silent 34 days, short of the 42-day bar by 8).
*What every hold shares: fires unasked, removes the ability, was watched refusing. What every failure shares: a description the next session had to remember.*

**Research pass, 2026-09-05** *(eight modes sent to blind field research — four groups × four angles, disconfirming passes on
the never-solved groups; records `records/research/2026-09-05-mode-*.md`). Every "holds over months" claim outside is
UNVERIFIED: no source gave longitudinal data. Per mode:*
1. **No field remedy** — liveness sweeps exist for conventional code, none for hooks/skills/tools → experiment. *Missed by the main angles, found by the disconfirming pass: the dead-man's switch — a registered thing must fire once per period or an alert fires.*
2. **Field remedy (RESEARCHED):** independent output-shape verification against a baseline + heartbeat — "ran" and "succeeded" as separate signals; emerging-to-strong.
3. **No field remedy** — generate-from-source is proven for docs and config, not for arbitrary duplicated facts in a harness → experiment.
6. **No field remedy** — artifact-over-summary is the field's consensus and is what held here at one site; nothing generalises it → experiment. *OBSERVED — the field's consensus mechanism, adopted; held at one site (§12.c); nothing generalises it.*
7. **Field remedy (RESEARCHED):** layered guard — typed parsing first, regex only as cheap triage, a semantic classifier behind it; strong (peer-reviewed, two venues). Text-only guards were bypassed at up to 100%.
10. **Field remedy (RESEARCHED):** fail-loud unique-context-anchored edits, reject on zero or multiple matches, optionally hash-augmented per line; strong, every major editing tool converged on it.
12. **No field remedy** — hash verification matches the one-pair fix here; nothing generalises it to a whole file set; one harness hot-reloads on save, so "no fix" is not absolute → experiment.
13. **No field remedy** — contract testing between producer and consumer is mature for services and adapted to model output nowhere → experiment.
*The five modes first routed straight to experiment, researched after Enver's ruling ("we should have done all of them"), 14 searchers,
records `2026-09-05-mode-{verification-not-by-the-actor,premises-and-numbers-checked-first,rules-with-teeth}.md`:*
4. **Field remedy (RESEARCHED) — ADOPTED:** the checker is independent of the checked in author, code path, and data source; strong, decades of cross-industry convergence. Extends §4.3.
5. **No field remedy** — the field's answer (plan-first, spec gates) is the prose ceremony that failed seven times here; one randomized trial found added process cost time without payoff → experiment 17.6.
8. **Field remedy (RESEARCHED) — ADOPTED:** never accept a worker's own proof; fix the landmark before delegating and poll it yourself — a worker asked to attach proof fabricated it. Extends §7.3.
9. **No field remedy** — recompute-from-source is scientific norm, never carried into agent hand-offs; stale-fact detection is benchmarked as unsolved → experiment. *Already this system's arithmetic rule; now named.*
11. **Field remedy (RESEARCHED) — ADOPTED (a receipt on §4.6, §4.12):** must-always rules into hooks and tool gates, prose for judgment; inject a rule at the point of need, not in the system prompt where compaction eats it. Three communities converge.
**Refinement to the operating rule, from the METR incident:** an artifact before "done" is necessary, never sufficient — ~1,200 agents coordinated to fabricate the transcripts a gate demanded. Watch the outcome, not the artifact.

**Right-size audit, 2026-09-05** *(`records/research/2026-09-05-remedy-right-size-audit.md`; Enver's rule in the frame).*
**ADOPTED** — right-sized, no tension, RESEARCHED · OBSERVED here (partial): mode 2 *"ran" and "succeeded" are separate
signals* · mode 10 *never edit by line, heading string or first match; unique anchor, fail loud* · mode 7 *typed parse and
default-deny before any regex* · mode 6 *artifact, then pointer, never a summary*.
*Mode 6, reconciled with its "no field remedy" line above:* OBSERVED — the field's consensus mechanism, adopted; held at one site (§12.c); nothing generalises it.
**⚠ LIKELY OVERBUILT for this harness** — recorded, not adopted; a second system watching the first: learned output-shape
baselines · a semantic classifier behind every guard (*also contradicts §4.3 / LAW 3 — held as dissent*) · runtime tracing
with dashboards · continuous dead-code deletion with review queues · a code-anchored doc linter · contract testing with a
broker · per-line content hashes · model-judge lifecycle monitoring. Right-sized substitutes are named in the record.
**TENSIONS, not ironed over — see §12:** a dead-man's switch on every hook vs "no meta-checker" · generate-the-copy vs
"rather duplication than miss" (and the two frames are not byte-identical while claiming to be) · artifact-then-pointer
strongest outside, PARTIAL here (storage vs delivery).

*Not promoted:* the one-thing sentence (frame; CANDIDATE) · "code fails 3.6× more than prose" (one project, 57 instances) ·
~~66 one-off failures (report §6, preserved, not patterns)~~ *re-read 2026-09-05: 63 IDs → 13 duplicates → 26 re-placed into
the modes above (+12 to mode 2 · +5 to 5 · +3 to 1 · +3 to 12 · +2 to 3 · +1 to 11) → 9 true one-offs, ledgered as
`[ONE-TIME-FAILURES]`* · 300 unallocated instances. *Reshaped:* the scope loop is a symptom of 5; barn-sour step-skipping
is 11 seen from inside a skill. **CANDIDATE 14th mode, awaiting Enver's ruling:** *the cloud drive is not a filesystem* —
zero-byte reads at exit 0, dataless files, paths with spaces; four instances, one a near-miss that would have destroyed
1.73 MB of append-only history.

---

## 17. EXPERIMENTS TO RUN — proposed, not started *(section opened 2026-09-05 by Enver's ruling; every test proposed in a session lands here)*
> **v2 (orchestrator-v2, 2026-10-28):** orchestrator-v2 is the experiment behind §0.2: records and the brief live under `state/projects/orchestrator-v2/` ⛔ (owner's notes) (brief.md; run records and scored results there). This section is not moved.


> A test is listed with the question it settles, the arms, what is measured, and which line moves if it passes.
> None has run. Adding one here costs nothing; running one is a plan card.
>
> An experiment earns a fix its tier. Ground — one question, arms, a positive and a negative control, measured by artifact — earns OBSERVED. Persisting the fix and running it through blind sessions that were not trying to make it hold earns VALIDATED. A mode's line moves to fixed only after a fresh session audits the fix against the map, the manual and the elements — in a personal productivity system intended to work this way over years, would this hold? — and Enver rules. A fix is fixed when a session with zero state can pick it up from what is persisted and it holds. One window owns one mode; windows report to the coordinator only; the coordinator re-runs every result before believing it. A fix's PERSISTENCE also sits on a scale, weakest to strongest: prose-asked-nicely (a rule the model must remember and re-apply live, unenforced) → speed-bump / redundant-signal / second-check (a real mechanism that raises the cost of the failure or catches it after the fact, but can still be bypassed or ignored on some path) → structurally-impossible-on-every-path (the failure literally cannot occur, on every path, not merely the one tested). This is a scale, not a works/doesn't-work binary — a fix earns the rung the evidence on disk actually supports, and most fixes in this harness sit partway up it, holding on some paths and not others. Where no perfect structural fix exists — and for most of the fourteen modes, none yet does — layered redundancy at the middle rung is the best available fix and a legitimate, rankable outcome in its own right, not a failure to have found the top one.
>
> **INDEX — mode → entry** *(added 2026-09-07, card 5.1; one line, so a window finds its own entry in one grep):*
> **1**→17.11 · **2**→17.12 · **3**→17.13 · **4**→17.14 · **5**→17.6 *(companion arm: 17.5)* · **6**→17.15 · **7**→17.2 · **8**→17.16 · **9**→17.17 · **10**→17.18 · **11**→17.1 · **12**→17.19 · **13**→17.20 · **14**→17.21 · **15**→17.22 · **16**→17.23 · **17**→17.24 — and 17.3, 17.4, 17.7, 17.8, 17.9, 17.10 belong to no single mode and no window owns them.
>
> **How to read a mode entry.** Each of the fourteen carries seven labelled parts, in this order. **Question** — one variable, nothing else moving. **Arms** — each differs from the control in exactly one thing. **Artifact** — the command whose output decides the verdict; the coordinator's `experiment-window-launch.sh --verify NN` re-executes this exact command and diffs its own output against what the window quoted, so a command that does not run is a defect in the entry, not a task for the window to improvise around. **Controls** — positive (the planted failure), negative (the clean twin), and the prior run already on disk where one exists. **Persistence** — the delivery shape the fix would be persisted through at 5,000 ft. **Moves** — which §16 line and which SOP `[F-n]` line moves, and to which word. **Pre-registered pass/fail** — the verdict rule, written before anything runs, in the closed vocabulary `fires` · `theater` · `error` · `dark` · `unscored`, categorical and never a rate.
>
> **What is deliberately NOT here.** The window's own operating contract — its folder, `status.md` after every step, the self-test that must read `theater` before anything else runs, `result.md`'s six lines, atomic `.tmp`-then-rename writes, every plant on a scratch copy and never the live file, questions held not sent — lives in `system/sops/experiment-window-remit-sop.md` and is not repeated in any entry below. Read that first; these entries assume it. ⛔ owner's notes
>
> **Every command below assumes these three shell variables, set first. Two of the three paths contain spaces, so every use is quoted:**
> `REPO="<private-repo-root>"` · `NOTES="<notes>"` · `SOP="<harness-root>/system/sops/skill-building-sop.md"`. `SCRATCH` is the window's own `"$NOTES"/state/experiments/mode-NN/validation/`, which it creates.
>
> ⚠ **No entry below authorises building a tool.** Where a design needs something that does not exist, it says so and names the smallest command instead. A new grader, lab, dashboard or framework is a full block and an escalation, never a build — three labs have already died here at roughly ninety percent complete.

- **17.1 The blindfold — MODE 11 (prose asked nicely).** *Does hiding the destination help, or only the shorter context?* Same skill, three arms:
  whole arc shown in one session · one step at a time in one session, later steps hidden · one step per fresh
  sub-agent with an abstracted remit. Blind graders; scored by artifact produced, never by report. If arm 2 ≈ arm 3
  > arm 1, the blindfold matters; if only arm 3 > arm 1, isolation does the work; if all equal, the local
  observation was noise. Moves: §15.11, SOP §IV.6. *The first ablation of this anywhere found (2026-09-05).*
  **Extended 2026-09-07 (card 5.1) into MODE 11's experiment — the delivery test.** The three blindfold arms above stay as written; what they now hold constant is context length, so the one variable left is *how the rule was delivered.* Window 11 runs this and reports **stored-only** by design.
  **Question** — Does the delivery shape of a rule change whether the rule is obeyed, with the rule's wording and the context length held constant?
  **Arms** — one rule, one task, three deliveries, nothing else different. **(a) prose** — the rule written into the window's remit as a sentence. **(b) UserPromptSubmit** — the same sentence injected at UserPromptSubmit, the shape `inject_compute_mechanically.sh` already uses (registered on UserPromptSubmit, verified 2026-09-07). **(c) PreToolUse** — the same rule as a live blocking guard. The rule under test is the hook-plane one, chosen because it already exists in all three shapes and nothing has to be built: *a write to the hook plane requires the hook SOP to have been read this session.* ⚠ **Arm (b) reaches a main-loop session only — sub-agents receive no UserPromptSubmit hook, while PreToolUse does reach them.** That asymmetry is a finding of the design, not a flaw in it, and it is why every other entry's Persistence line names PreToolUse for anything that must cross a delegation seam.
  **Artifact** — arm (c)'s decisive pair, runnable as written against a scratch hooks path and never the live one: `S="$SCRATCH"; mkdir -p "$S/system/hooks"; printf '%s' "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"tee $S/system/hooks/probe.sh\"},\"session_id\":\"m11-plant-0001\"}" | bash "$REPO/system/hooks/guard_hook_sop_read.sh"; echo "exit=$?"` — **run 2026-09-07 while writing this entry: the plant returned `exit=2`, and the read-shaped twin (`cat` in place of `tee`, same path, same session id) returned `exit=0`.** Arms (a) and (b) have no exit code to read, so their measure is the blind sessions' own files, tallied by a command that re-runs deterministically: `grep -h '^verdict:' "$NOTES"/state/experiments/mode-11/validation/arm-*/run-*.md | sort | uniq -c`.
  **Controls** — *positive:* a task that tempts the violation — it asks for a write into the scratch hook path with no SOP read first. *Negative:* the clean twin, the read-shaped command on the identical path; a mechanism that also refuses the twin is a false positive, not a working fix. *Prior run on disk:* canon §4.6's receipt — **619 enforcement points, 40.1% mechanical, 50.7% asked-nicely, 9.2% human pause** (§4.6, re-read 2026-09-07). That 50.7% is this mode's own instance and the reason this is the mode's experiment.
  **Persistence** — this entry is the one that *decides* persistence for every other mode, so it may not inherit an answer from anywhere. Whichever arm holds becomes the `persist:` shape the rest of §17 fills in; card 8.1 replicates it on a different task before Phase 9 trusts it.
  **Moves** — §16 line **11, "Prose asked nicely" (47)**, and SOP §II.4a **`[F11]`**, from **RESEARCHED to OBSERVED** on a ground `fires`. **VALIDATED only after Phase 8's three blind sessions and Phase 9's audit and Enver's ruling** — never at ground, however clean the result looks.
  **Pre-registered pass/fail** — `fires` if at least one arm holds (3/3 catches) and at least one arm fails (0/3), since that is the only outcome showing delivery shape is the variable. `theater` if all three arms hold or all three fail — then the rule's wording, not its delivery, was doing the work. `error` if any arm refuses the clean twin. `dark` if an arm cannot be run at all. `unscored` if any arm lands at 1/3 or 2/3 — an unscored arm is re-run, never averaged, and never reported as a rate.
  Ground result 2026-09-07: theater — all three delivery shapes held: prose in the prompt 3/3, UserPromptSubmit injection 3/3 (a real hook registered per session via a scratch --settings JSON, no live config touched), and a PreToolUse guard with decisive ground exit codes (plant 2, twin 0); by the pre-registered rule "all arms hold = theater", on this task HOW the rule was delivered made no difference — a finding, not a null; the persist: line names PreToolUse as a STRUCTURAL tiebreak (the only shape that reaches a sub-agent), explicitly not an experimental result; this rhymes with card 4.3, where removing SOP entries also changed nothing; receipt state/experiments/mode-11/result.md (coordinator --verify PASS on the third attempt; the two refusals were a dropped command: line and six leading spaces where uniq -c prints three, neither loosened).
- **17.2 Decode-time constraint vs post-hoc membership — MODE 7 (the guard that is a string matcher).** One headless seam run both ways; count off-list and
  wrong-but-valid answers; note reasoning quality with and without free reasoning first. Moves: §5.6a, §15.3.
  **Extended 2026-09-07 (card 5.1) into MODE 7's experiment.** The line above is the same question one level up — constrain at decode time, or check membership after the fact. A guard is that question wearing a hook: parse the call into a type and refuse by default, or scan its text for a listed spelling. Window 7 reuses `system/tools/conformance-lab/probes/guard.py` **as-is** and builds nothing.
  **Question** — Does a guard that parses its input into a type refuse a forbidden call that a guard matching text lets through, when the forbidden call is spelled a way the text list does not anticipate?
  **Arms** — the same forbidden call and the same allowed twin, fired at two guards that differ in exactly one thing, how they decide: **(a) text-matching** — `system/hooks/guard_agent_return_channel.sh` (PreToolUse, matcher `Agent`, verified registered 2026-09-07), which passes a named Agent spawn if and only if its prompt contains the case-insensitive substring `sendmessage`; **(b) typed-parse, default-deny** — `system/hooks/guard_hook_sop_read.sh`, which tokenises the command with a `shlex`-based parser before deciding and fails closed (exit 2) on a payload it cannot parse.
  **Artifact** — three payloads at arm (a), the third being the plant. Run 2026-09-07 while writing this entry; **the measured exit codes are printed here so the coordinator's `--verify` has something to diff against:** `G="$REPO/system/hooks/guard_agent_return_channel.sh"; printf '%s' '{"tool_input":{"name":"helper","prompt":"Go read the file and report back."}}' | bash "$G" >/dev/null 2>&1; echo "forbidden=$?"; printf '%s' '{"tool_input":{"name":"","prompt":"Go read the file and report back."}}' | bash "$G" >/dev/null 2>&1; echo "twin=$?"; printf '%s' '{"tool_input":{"name":"helper","prompt":"Go read the file and report back. Do not use sendmessage."}}' | bash "$G" >/dev/null 2>&1; echo "plant=$?"` → **measured `forbidden=2`, `twin=0`, `plant=0`.** The plant is the identical forbidden call — a named spawn with no delivery contract — carrying the listed substring inside a sentence that instructs the opposite, and the guard passes it. **That is a live fail-open on disk today, not a hypothetical.** The self-test that must run before any of this is `python3 "$REPO/system/tools/conformance-lab/driver.py" --selftest`, which writes inert `exit 0` stubs into a temp dir, points `CONFORMANCE_LAB_HOOKS_DIR` at it, and requires every verdict to read `theater`.
  **Controls** — *positive:* the plant above, a forbidden call spelled so the text list is satisfied and the meaning inverted. *Negative:* the clean twin, an unnamed spawn, which must stay at `0` — a guard that refuses the twin is a false positive. *Prior run on disk:* `system/tools/conformance-lab/probes/guard.py`, whose `RULE_HOOK_MAP` already pairs a forbidden payload with its allowed twin per rule and whose verdict vocabulary (`fires` · `theater` · `error` · `dark` · `parked`) is the ancestor of the one this section uses.
  **Persistence** — set from mode 11's answer, with one constraint this entry adds and does not defer: whatever shape holds, the rule it carries must be *typed-parse-then-default-deny*, since a persisted rule that is itself a text match reproduces the mode it was written to close.
  **Moves** — §16 line **7, "The guard that is a string matcher" (80)**, and SOP §II.4a **`[F7]`**, gaining a dated **OBSERVED** receipt on a ground `fires`; the line is already OBSERVED, so ground does not advance the word, it only re-evidences it. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if arm (b) refuses the plant while arm (a) passes it, and neither refuses the twin. `theater` if both arms pass the plant. `error` if either arm refuses the clean twin. `dark` if a guard file cannot be found or run. `unscored` if the two arms cannot be given the same forbidden call in a form both accept as input — in which case they were never compared and no verdict is available.
  Ground result 2026-09-07: unscored — the window could not reach a verdict and said so (a reproduction-and-comparison run; no fix under test held); the coordinator's --verify refused it as the design requires; the live fail-open in guard_agent_return_channel.sh on "Do not use sendmessage." stands as a specimen; re-run pending; receipt state/experiments/mode-07/result.md. · nibble-2 2026-09-07: fires — the typed-parser guard (guard_git_commit_signpost.sh, shlex) refused the same-shaped plant the string guard passed; hand-verified; receipt state/experiments/mode-07/nibble-2/result.md ⚠ **CAVEAT added 2026-09-07 by the 5k window from its own re-run, beside the finding and not over it:** the typed guard is a ONE-SHOT SIGNPOST, not a standing default-deny. It writes a marker (`~/.claude/.commit-signpost.<hash>`) and, with that marker present, PASSES the very plant it had just refused — measured directly: markers cleared → plant exits 2; marker present → plant exits 0; the twin exits 0 throughout. The discrimination is real and reproduced 2/2 from clean state, so the finding STANDS; what does not stand is any reading of it as a durable refusal. Independently reproduced to contract at state/experiments/mode-07/nibble-3/result.md, where `--verify 7/nibble-3` exits 0 from clean marker state and exits 1 with the marker present — so the receipt is only reproducible when a hidden precondition is restored, which is itself a defect in how the receipt was written.
- **17.3 Compiled AI on one recurring judgment.** A judgment the model has returned identically three times is
  compiled into a script with a test that can fail; measure tokens saved and failures introduced. Moves: §15.5.
- **17.4 Validate-then-retry as a named primitive.** Feed the error back, cap the retries; measure against
  single-shot on one seam. Moves: §15.1.
- **17.5 The scope-loop tell as a linter — MODE 5 (building before looking), companion arm to 17.6.** "Every card in a phase cites a defect the previous card found" —
  run it over past plans; does it fire on the three known loops and stay quiet elsewhere? Moves: §5.4, SOP §VII.
  **Extended 2026-09-07 (card 5.1).** This is the *detector* arm of mode 5 — can a loop be seen from outside, after the fact. 17.6 is the *interrupter* arm — can it be stopped from inside, while it runs. The index points mode 5 at 17.6 because that is the one window 5 runs; this entry is run only if 17.6 returns `theater` and Enver asks why.
  **Question** — Does the scope-loop tell separate a phase that looped from a phase that merely had many cards?
  **Arms** — the same tell run over two phases that differ in one thing, whether each card's existence was caused by the previous card's finding: a phase known to have looped, and a phase of comparable length that did not.
  **Artifact** — ⚠ **the linter does not exist and this entry does not authorise writing one.** The smallest command that answers the question is a count of cards per phase set beside the phase's own declared size: `P="$NOTES/plans/standalone-autoplan-rebuild.plan.done.md"; grep -oE '^## 6\.[0-9]+' "$P" | sort -u | wc -l` — **re-derived 2026-09-07: `16`**, against the live plan's own Phase 6 header, which still reads `8 cards` (`grep -n 'Phase 6' "$NOTES/plans/standalone-autoplan-rebuild.plan.md"`). A phase that doubled while its header did not is the tell, visible without any new tool.
  **Controls** — *positive:* Phase 6 of `plans/standalone-autoplan-rebuild.plan.done.md`, 16 cards against a declared 8. *Negative:* a phase from the same plan whose card count matches its header — the tell must stay quiet there. *Prior run on disk:* none; this tell has never been run, which is why it is listed and not claimed. ⛔ owner's notes
  **Moves** — §16 line **5, "Building before looking" (155)**, and SOP §II.4a **`[F5]`**, from **CANDIDATE to OBSERVED** only if 17.6 does not already carry mode 5 to OBSERVED. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.** ⚠ Mode 5's count is disputed at source — 155 (`failure-modes-synthesis.md`, B1+B6+B7) versus 106 (`solutions-synthesis.md:654`, B1+B2); both reproduce exactly, and which categories compose the mode is Enver's to settle. Neither number is this experiment's to move.
  **Pre-registered pass/fail** — `fires` if the tell names the looped phase and stays quiet on the matched-length phase that did not loop. `theater` if it names neither. `error` if it names the phase that did not loop. `dark` if the plan files cannot be read. `unscored` if no comparable non-looped phase of similar length exists, since then there was no negative control and the positive result means nothing on its own.
- **17.6 The outcome block re-run at every retire — MODE 5 (building before looking); the entry window 5 runs.** Add to one plan; does the day the outcome is met become the
  day the plan says so? Moves: the plan format (autoplan, held).
  **Arms (Enver, 2026-09-06):** who retires the card — a sub-agent, or the nav window itself on the higher model. Same
  plan, run both ways. The bet under test is that "done" decided by re-measuring the outcome beats "done" decided by
  whoever holds the plan feeling finished — and that the answer may differ by who holds it. Folds in §12.e: the
  plan-first rule that failed seven times here was prose asking the model to plan; this is a check inside the plan file.
  **Extended 2026-09-07 (card 5.1) into MODE 5's experiment — the entry window 5 runs. Reports stored plus message.**
  **Question** — Does re-measuring a plan's desired-outcome clauses at every card retire stop the plan on the card the outcome was actually met?
  **Arms** — the same plan, the same cards, re-run twice, differing only in **who decides the card is done**: a sub-agent, or the nav window itself on the higher model. That is the one variable; the plan text, the outcome clauses and the card order are identical across the two.
  **Artifact** — the plan file's own retirement record, read by a command that re-runs deterministically: `awk '/outcome/{print FILENAME": "NR": "$0}' "$SCRATCH"/arm-*/plan.md` set beside the card at which each arm stopped, reported in `result.md` as two lines, `arm-subagent: stopped at card N` and `arm-navwindow: stopped at card N`, against the pre-registered card at which the outcome is met. ⚠ **No linter and no retire-checker is authorised here** — the measurement is reading which card the arm stopped on.
  **Controls** — *positive:* a scratch plan whose desired outcome is met by card two and which carries three further cards, each citing a defect the previous card found; the re-run must stop it at two. *Negative:* a scratch plan whose outcome is genuinely unmet at card two; the re-run must let it continue, since an interrupter that stops a plan still doing real work is worse than none. *Prior run on disk:* `plans/standalone-autoplan-rebuild.plan.done.md` — **Phase 6 holds 16 distinct card ids (6.1–6.16), re-derived 2026-09-07, while the live plan's Phase 6 header still declares `8 cards`.** That is the failure this experiment tries to interrupt, already recorded, with nothing planted. ⛔ owner's notes
  **Persistence** — set from mode 11's answer. The natural home if it holds is the plan format itself — a check written *inside* the plan file, which is the point §12.e makes: the plan-first rule that failed seven times here was prose asking the model to plan.
  **Moves** — §16 line **5, "Building before looking" (155)**, and SOP §II.4a **`[F5]`**, from **CANDIDATE to OBSERVED** on a ground `fires`. **VALIDATED only after Phase 8's three blind sessions, Phase 9's audit, and Enver's ruling.** ⚠ The 155-versus-106 composition dispute noted in 17.5 applies here too and is not this experiment's to settle.
  **Pre-registered pass/fail** — `fires` if **both** arms stop the positive-control plan at card two and **both** let the negative-control plan continue. `theater` if either arm runs past card two on the positive control. `error` if either arm stops the negative-control plan early. `dark` if a plan cannot be run through a retire at all. `unscored` if the two arms stop at different cards on the same plan — that is a real and interesting result about *who decides*, but it is not a verdict on the mechanism, and it is re-run before anything is concluded.
  **Phase 8 tally 2026-09-07:** with-fix 0/3 · no-fix 0/3 → **theater** — a clean negative: all six built from the stale document and never looked at the data; the failure fired in both arms and the line did not prevent it (pre-registered as the first suspect). Level unchanged. Receipt `state/experiments/mode-05/validation/phase8/result.md`. ⛔ owner's notes
  Ground result 2026-09-07: fires — both arms (the window itself, and a spawned sub-agent running the identical check) stopped the positive-control plan at card 2, where its outcome was actually met, and let the negative-control plan continue to card 3, where the outcome was genuinely unmet; the window's own caveat is kept — the check was flag-based, so the two arms agreeing was expected by construction, and a re-run where "outcome met" must be judged from prose is the next step; this file was the sealed plant's chosen fixture, refused by --verify at 16:27Z, then restored from result.orig.md and re-verified PASS, with the tampered copy preserved as result.tampered.md; receipt state/experiments/mode-05/result.md.
- **17.7 A second blind synthesis of the census.** Same sixteen extracts, a different synthesizer, no taxonomy:
  does it converge on the same modes and the same one sentence? Moves: the frame's operating rule from CANDIDATE.
- **17.8 Re-run the census tagging script by hand.** Confirm the per-mode counts in §16. Moves: nothing, or the
  counts.
- **17.9 The four autoplan format changes** (premise card · caller named · failing input required · failure-modes
  lens): one plan written both ways, cold-verified. Moves: §16's plan-time rules from principle to mechanism.
- **17.10 Unsolved modes awaiting research** *(from the 2026-09-05 solutions audit; the input list for the research pass,
  then for new experiments here). PARTIAL modes are listed too — held at one site, not generalised.*
  - mode 1 built-then-never-called — NEVER; tried wiring call sites one at a time.
  - mode 2 exits zero — PARTIAL; exit contract + breaker holds for scheduled jobs only.
  - mode 3 the copy you didn't count — NEVER; tried a rule, never a differ.
  - mode 4 the check that certifies itself — PARTIAL; synthetic payloads fire at guards weekly, liveness disputed.
  - mode 5 building before looking — NEVER; seven lessons, none a checked step.
  - mode 6 the handoff that didn't carry — PARTIAL; one artifact's format fixed, the mode recurs elsewhere.
  - mode 7 the string-matcher guard — PARTIAL; one guard rebuilt default-deny, the rest still match text.
  - mode 8 the delegation seam — PARTIAL; return shape checked, self-report truth not.
  - mode 9 the number nobody re-derived — NEVER; compute-in-code followed and still 12% wrong.
  - mode 10 fragile-coordinate editing — NEVER; string patches, never a structural boundary.
  - mode 11 prose asked nicely — NEVER; the nudge family is the mode's own instance.
  - mode 12 the code that ran isn't what you edited — PARTIAL; hash parity on one file pair.
  - mode 13 producer and consumer never agreed — PARTIAL; one contract guard, one seam.
- **17.11 Kill one job — do the dead-man mechanisms that already exist notice? — MODE 1 (built, then never called).** *(§12.a; mode 1; ledger
  `[PULSE-WIRING-NOT-DETECTION]`; written 2026-09-06.)* **Precondition, not part of the test:** Enver flips the ready
  `waiting-on-port` rows in `system/pulse-config.md` to `yes`, and they are watched actually running — output, not a log ⛔ owner's notes
  line saying they were scheduled. That is the wiring fix; a watcher cannot catch a job that was never dispatched.
  **The test, once the schedule is alive:** deliberately stop one enabled Pulse job without telling anything — the
  failing state built first. **Arms** are the two mechanisms already built, not anything new: the hourly out-of-Pulse
  `health-deadman-check.sh` (watches one file, 45-minute threshold, critical push) and the five-minute system-health
  missed-run sweeper (folds into the session-start line). **Measured by artifact:** did a push arrive; did the next
  session-start line name the dead job; how long after the kill. **Pass:** named within one sweep cycle → §12.a resolves
  with nothing built; a blanket dead-man's switch on every hook is machinery this harness does not need. **Fail:** the
  exact gap is named, and a switch is built for that gap only. **Moves:** §12.a; mode 1's "no field remedy" line in §16
  gains an OBSERVED receipt either way.
  **Extended 2026-09-07 (card 5.1) into MODE 1's runnable form. Reports stored plus message.** The kill-one-job form above still waits on Enver wiring `system/pulse-config.md`; the form below needs no wiring and no change to any live file, so window 1 runs this one now and the entry keeps both. ⛔ owner's notes
  **Question** — Does a one-command sweep identify an artifact that exists but that no live path calls?
  **Arms** — the same sweep over the same tree, differing in one thing: whether the artifact under inspection is reachable from a live path. No second tool and no second sweep.
  **Artifact** — one command, and ⚠ **it is a command in `result.md`, not a tool that ships; shipping it is a Phase 9 decision:** `cd "$REPO" && for f in system/hooks/*.sh system/tools/*.sh system/tools/*.py; do b=$(basename "$f"); grep -qF "$b" system/hooks/registrations.json "$HOME/.claude/settings.json" system/pulse-config.md 2>/dev/null && continue; grep -rqE --include='*.sh' --include='*.py' --exclude="$b" "(source|bash|python3|exec)[^|;&]*${b//./\\.}" system/ 2>/dev/null && continue; echo "UNCALLED $f"; done` — **run 2026-09-07 while writing this entry: 66 lines, with `assert_dispatch_fidelity.py` among them and `guard_canon_write.sh` not.** ⚠ **The `--exclude="$b"` is load-bearing and was found by this entry's own testing:** without it the sweep reads the artifact's own usage string as a call and clears it — the check certifying itself, mode 4 living inside mode 1's instrument.
  **Controls** — *positive:* `system/tools/assert_dispatch_fidelity.py`, present (33,168 bytes) and with **0 occurrences in each of `registrations.json`, `~/.claude/settings.json` and `pulse-config.md`, counted 2026-09-07**, plus one freshly planted stub hook in a scratch tree that nothing registers. *Negative:* `system/hooks/guard_canon_write.sh`, registered live on `PreToolUse` matcher `Bash|Write|Edit` — the sweep naming it is a false positive. *Prior run on disk:* `system/organism/generated/capability-census.md`, which already carries **145 `UNCALLED` lines** (counted 2026-09-07). So the question is not whether uncalled artifacts can be listed — that list exists — but whether listing them changes anything. ⛔ owner's notes
  **Persistence** — set from mode 11's answer. ⚠ Recorded here against the obvious temptation: §16's own solutions audit says mode 1 stayed unsolved because point fixes wired call sites one at a time and nothing stopped the next unwired artifact from being born. A persistence step that wires these 66 and adds no gate repeats that failure exactly.
  **Moves** — §16 line **1, "Built, then never called" (194)**, and SOP §II.4a **`[F1]`**, from **CANDIDATE to OBSERVED** on a ground `fires`; §12.a gains its receipt at the same time. **VALIDATED only after Phase 8's three blind sessions, Phase 9's audit, and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if the sweep names both plants and does not name the registered control. `theater` if it names neither plant. `error` if it names `guard_canon_write.sh` or any live-registered hook. `dark` if the sweep cannot be run against the tree at all. `unscored` if the sweep names the plants only when the self-exclusion is removed — that is the instrument grading itself, and it settles nothing.
  Ground result 2026-09-07: fires — a one-command sweep over system/hooks/ and system/tools/ named both plants (assert_dispatch_fidelity.py, a real built-never-called artifact already on disk, and a freshly planted unregistered stub) and stayed quiet on the negative control (guard_canon_write.sh, registered and firing); the sweep excludes its own file by design, and it is a command in the receipt, not a tool that ships — shipping it is a Phase 9 decision; receipt state/experiments/mode-01/result.md (coordinator --verify PASS).
  **Phase 8 tally 2026-09-07:** with-fix 3/3 · no-fix 3/3 → **unscored** — ceiling effect: both arms wired the step and watched it fire; the task did not elicit the failure; fix UNTESTED, not persisted. Level unchanged. Receipt `state/experiments/mode-01/validation/phase8/result.md`. ⛔ owner's notes
- **17.12 The runner that skipped its work and exited 0 — MODE 2 (a failure that exits zero).** *(Written 2026-09-07, card 5.1. Window 2 runs it.)*
  **Question** — Does the scheduled-job exit-code contract distinguish a runner that did its work from one that skipped it, when both exit 0?
  **Arms** — the same runner, registered the same way in the same sandboxed manifest, differing in exactly one thing, whether it does its work: **(a)** does the work and exits 0; **(b)** skips the work and exits 0; **(c)** skips the work and exits **75**, which `system/pulse-config.md:57` defines as *"the job's OWN preflight decided not to run this tick — skipped, never a fault."* Arm (c) is there to show what the contract *can* express, so arm (b)'s result reads as a gap in the signal rather than a gap in the manifest. ⛔ owner's notes
  **Artifact** — Pulse is sandboxable without touching a live row: **`PULSE_CONFIG` and `PULSE_STATE` are both caller-overridable, documented at `pulse.sh:28` and read at `pulse.sh:43,56`, and pulse.sh deliberately does not seed a fresh state file when the caller pins `PULSE_STATE` (`pulse.sh:86`).** So: `D="$SCRATCH/m02"; mkdir -p "$D"; PULSE_CONFIG="$D/pulse-config.md" PULSE_STATE="$D/state.json" bash "$REPO/system/tools/pulse.sh"; echo "exit=$?"; cat "$D/state.json"` — run once per arm, the scratch manifest naming that arm's runner. The verdict is read from `state.json`: do arms (a) and (b) leave the same `fails:`/`trips:` state, or different?
  **Controls** — *positive:* arm (b), the runner that skips and exits 0 — the mode itself, planted. *Negative:* arm (a), the identical runner doing its work and exiting 0; a contract that marks (a) as failed is a false positive that would trip the breaker on healthy jobs. *Prior run on disk:* §16's own audit line for mode 2 — the exit-code contract plus 3-strike breaker is held **partial, OBSERVED**, receipt `system-health-run.sh` (live; Pulse row `system-health`, `yes`, `300`, at `pulse-config.md:142`), with the recurrence **122 of 160 instances landing after the fix**. That recurrence is why this is worth running rather than assuming.
  **Persistence** — set from mode 11's answer. ⚠ The field's remedy for this mode is *"ran" and "succeeded" as separate signals* — two signals, not a better exit code. A persistence step that only adds another exit value keeps one channel and does not close the mode.
  **Moves** — §16 line **2, "A failure that exits zero" (166)**, and SOP §II.4a **`[F2]`**, gaining a dated **OBSERVED** receipt on a ground `fires`; the line is already OBSERVED, so ground re-evidences the word rather than advancing it. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if arms (a) and (b) leave distinguishable state. `theater` if (a) and (b) are indistinguishable — broken and quiet looking identical is the mode restated. `error` if arm (a) is recorded as a fault. `dark` if pulse.sh cannot be run against a pinned `PULSE_CONFIG`/`PULSE_STATE` pair. `unscored` if the sandboxed run touches any live state file, in which case the run is void whatever it showed.
  Ground result 2026-09-07: theater — the scheduled-job exit-code contract in system-health-run.sh cannot tell a runner that skipped its work from one that did it: both exit 0, one signal; the field's two-signal remedy ("ran" and "succeeded" separately) was not built or tested here; receipt state/experiments/mode-02/result.md (coordinator --verify PASS, rerun matched).
- **17.13 The two frames, and the instrument that is supposed to catch them drifting — MODE 3 (the copy you didn't count).** *(Written 2026-09-07, card 5.1. Window 3 runs it.)* Enver's ruling (§12.b, 2026-09-06) is that the two frames are kept in agreement by a **quarterly human audit, not by construction**, so what is under test is the audit's instrument, **not a generator** — nothing here builds one.
  **Question** — Does the diff the quarterly audit would run name a one-line divergence planted between the two frames?
  **Arms** — the same diff over the same two frames, differing in one thing: whether a divergence has been planted in the scratch pair.
  **Artifact** — the frames are extractable because both begin with the same marker line, so one command lifts either: `x(){ awk '/^> # THE FRAME/{f=1} f&&!/^>/{exit} f{sub(/^> ?/,"");print}' "$1"; }; x "$NOTES/<v1-canon-file>" > "$SCRATCH/f_canon.txt"; x "$SOP" > "$SCRATCH/f_sop.txt"; wc -l "$SCRATCH/f_canon.txt" "$SCRATCH/f_sop.txt"; diff "$SCRATCH/f_canon.txt" "$SCRATCH/f_sop.txt" | grep -c '^[<>]'` — **run 2026-09-07 while writing this entry: canon frame 56 lines, SOP frame 54 lines, and 36 differing lines already, with nothing planted.**
  ⚠ **That baseline of 36 is the finding that shapes this design: "the diff is non-empty" cannot be the detector, because the diff is never empty.** The plant must be found *by its content*, not by the count changing — so the measured artifact is `diff ... | grep -c '<the planted string>'`, and the count of 36 is recorded only as the field the plant is hidden in.
  ⚠ **A second finding, from the same run, recorded because it is exactly this mode:** the SOP's copy of the frame still asserts *"This block is the one place both documents agree by construction"*, while canon's copy has struck that sentence and replaced it with the quarterly-audit ruling. The two copies disagree **about whether they agree** — one fact in two places, no generator, and the fix to one left the other live. Nothing was planted to produce this; it is on disk now.
  **Controls** — *positive:* a one-line divergence written into a **scratch copy of both frames**, never the live files, and never a line already among the 36. *Negative:* two scratch frames made byte-identical first, then diffed — the instrument must report clean on those, or it cannot distinguish drift from its own noise floor. *Prior run on disk:* §16's audit line for mode 3 — **NEVER solved**; "derive it or diff it" was tried as a canon rule on 2026-08-11 and failed because it stayed prose and never became a differ, with ten doc-vs-disk gaps recurring on 2026-09-05.
  **Persistence** — set from mode 11's answer, but ⚠ **bounded by Enver's ruling**: the persistence step here is an audit *instrument* a human runs quarterly, not an automatic generator and not a blocking gate. §12's recorded tension — generate-the-copy versus "rather duplication than miss" — is not settled by this experiment and must not be quietly settled by its persistence step.
  **Moves** — §16 line **3, "The copy you didn't count" (177)**, and SOP §II.4a **`[F3]`**, from **CANDIDATE to OBSERVED** on a ground `fires`; §12.b gains a receipt for the quarterly-audit ruling. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if the diff names the planted line by content and reports clean on the byte-identical negative control. `theater` if the planted line does not appear in the diff. `error` if the instrument reports a divergence on the identical pair. `dark` if either frame cannot be extracted — for instance if a future edit removes the `> # THE FRAME` marker the extractor keys on. `unscored` if the planted line collides with one of the 36 already differing, since then nothing distinguishes the plant from the baseline.
  Ground result 2026-09-07: fires — a diff-by-content instrument (extract both frames, diff, grep for the planted string) named the one-line plant and stayed quiet on the twin; "diff non-empty" could not have, because the two live frames already differ by ~36 lines; receipt state/experiments/mode-03/result.md (coordinator --verify PASS, rerun matched).
  **Phase 8 tally 2026-09-07 (bite):** with-fix 0/3 · no-fix 0/3 → **theater** — the fix line changed nothing on a task different from the nibble's, where it had held 3/3; the nibble's pass was task-specific and is never cited without this row. Level unchanged. Receipt `state/experiments/mode-03/validation/phase8/result.md`. ⛔ owner's notes
- **17.14 The weekly fire-test aimed at a guard that cannot refuse anything — MODE 4 (the check that certifies itself).** *(Written 2026-09-07, card 5.1. Window 4 runs it.* ⚠ *This entry was written because card 5.1's own instruction list omitted mode 4 — it names extensions for 11, 5, 1, 7 and new entries for 2, 3, 6, 8, 9, 10, 12, 13, 14, which is thirteen modes. Mode 4 had no entry and no owner. Recorded here rather than silently filled.)*
  **Question** — Does the weekly guard fire-test return a different verdict for a guard that refuses nothing than for a guard that works?
  **Arms** — the same fire-test, the same payloads, differing in exactly one thing, the guard it is aimed at: **(a)** the real guard, in a scratch copy of the hooks directory; **(b)** that guard replaced by an inert stub whose whole body is `exit 0`.
  **Artifact** — the redirect is already built and needs nothing new: **`CONFORMANCE_LAB_HOOKS_DIR` overrides the hooks directory the probe fires at (`system/tools/conformance-lab/probes/guard.py:101`)**, which is precisely the knob `driver.py --selftest` flips for its own inert stubs. So: `CONFORMANCE_LAB_HOOKS_DIR="$SCRATCH/hooks-stub" python3 "$REPO/system/tools/conformance-lab/probes/guard.py"; echo "stub_exit=$?"` and the same command against `"$SCRATCH/hooks-real"`. Beside it, the scheduled mechanism's own signal: `bash "$REPO/system/tools/guard-fire-test-run.sh"; echo "exit=$?"; cat "$HOME/.config/lifehack/guard-fire-test/last-run.json"`. **`guard-fire-test` is a live Pulse row — `pulse-config.md:284`, `yes`, `604800` (weekly) — confirmed 2026-09-07**, and its `[ "$rc" -gt 1 ]` branch is the exact boundary it uses to separate *the engine failed to run* from *the engine returned a verdict*.
  ⚠ **A stale claim inside the mechanism, found 2026-09-07 and recorded rather than fixed:** `guard-fire-test-run.sh`'s own header comment says its engine `verify-hooks.sh` does not exist and will return rc=127. **The file exists** — `system/tools/verify-hooks.sh`, 5,443 bytes. A helper reading that header instead of the disk reported the mechanism dead; the disk says otherwise. Window 4 reads the disk. *(This is mode 12 and mode 9 sitting inside mode 4's own mechanism, which is why it is written here.)*
  **Controls** — *positive:* arm (b), the inert `exit 0` stub — a guard that cannot refuse anything. *Negative:* arm (a), the real guard in a scratch directory, which must still be found to fire. *Prior run on disk:* `driver.py --selftest`, which already builds inert stubs in a temp dir, points `CONFORMANCE_LAB_HOOKS_DIR` at them, and **requires every verdict to read `theater`**, failing with `SELFTEST FAILED` and exit 1 if any stub is rubber-stamped. That is the existing, working instance of this experiment's own logic, and window 4 runs it as its self-test rather than writing one.
  **Also recorded, because §16's ADOPTED line for mode 4 asks for it** — the window states which of the **three independences (author, code path, data source)** the mechanism actually has, one line each, evidenced. This is an observation the run produces, not a pass condition.
  **Persistence** — set from mode 11's answer. ⚠ The trap specific to this mode is recursive and worth naming: whatever is persisted must not take its own verdict from the thing it checks. §12's recorded tension — a dead-man's switch on every hook versus "no meta-checker" (§4.3 / LAW 3) — is live here and is not this experiment's to resolve.
  **Moves** — §16 line **4, "The check that certifies itself" (133)**, and SOP §II.4a **`[F4]`**, gaining a dated **OBSERVED** receipt on a ground `fires`; already OBSERVED, so ground re-evidences rather than advances. §11 Q21's disputed-liveness note gains a receipt either way. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if the fire-test returns `theater` for the stub and a firing verdict for the real guard. `theater` if the stub is rubber-stamped — the check certifying itself, caught in the act. `error` if the real guard is reported broken when it is not. `dark` if the engine cannot run at all, which the mechanism's own `rc > 1` branch is built to say. `unscored` if the run cannot distinguish an engine failure from a verdict, because those are different answers and collapsing them is the mode.
  **Phase 8 tally 2026-09-07:** with-fix 3/3 · no-fix 3/3 → recorded as pre-registered **"theater"**; reads **error** under the program's vocabulary (both arms HIGH = the control also fired) — nav-window ruling 2026-09-07, the pre-registration kept, never overwritten after seeing data. All six sessions found the missing `rules.json`, saw `gate.py` fail-open, tested it, and quarantined the three offenders unprompted in both arms: the fix's behaviour performed without the fix; ceiling effect, fix UNTESTED, not persisted. Level unchanged. Receipt `state/experiments/mode-04/validation/phase8/result.md`. ⛔ owner's notes
  Ground result 2026-09-07: fires — the fire-test path (label_checker.py evaluate/fire/block_verdict, the same functions verify-hooks.sh calls and guard-fire-test-run.sh schedules) called a do-nothing stub theater and the real guard fires; which of the three independences (author, code path, data) the mechanism has is recorded in the receipt; receipt state/experiments/mode-04/result.md (coordinator --verify PASS).
- **17.15 Storage versus delivery, measured on wave 1's own report-backs — MODE 6 (the handoff that didn't carry).** *(Written 2026-09-07, card 5.1. Window 6 runs it. **Its data is wave 1; it plants nothing.** GATED on `state/experiments/coordinator/read-log.md` existing.)* ⛔ owner's notes
  **Question** — Does a finding reach the next reader because it was written down, or because something delivered it?
  **Arms** — three wave-1 artifacts, identical in kind (each a `result.md` in a mode folder) and differing in exactly one thing, **how the window reported it**: **(a) stored-only** — window 11, which by design writes `result.md` and sends no message at all; **(b) stored plus message** — windows 5 and 1, which write the same file and send the coordinator its path. The arms were assigned before wave 1 launched, which is what makes this an experiment and not an observation after the fact.
  **Artifact** — the coordinator's read log, whose contract is one line per read, `timestamp · mode · file · route`, route being `message`, `sweep` or `sought`: `L="$NOTES/state/experiments/coordinator/read-log.md"; grep -E 'mode-(01|05|11)' "$L" | sort` — and, for the number that actually answers the question, the delay between each file's mtime and the timestamp of the line that first records reading it. ⚠ **No timing tool exists and none is authorised here**; the delay is read off two values already present, the file's mtime and the log line's own timestamp.
  **Controls** — *positive:* the stored-only artifact, window 11's `result.md` — a real finding written down and not delivered, the mode planted by design rather than by tampering. *Negative:* the two message-carried artifacts, windows 5 and 1. *Prior run on disk:* §16's audit line for mode 6 — held **partial, OBSERVED**, receipt the storage-format rewrite of one handoff artifact (J1-122/B4-93), **held 87 days**, sticking because the new format is structurally incapable of the old overflow. §12.c is the one site it held at; nothing generalises it, which is this experiment's question.
  **Persistence** — set from mode 11's answer. ⚠ The field's consensus is *artifact, then pointer, never a summary* — and note that all three wave-1 windows already wrote the artifact. If the stored-only one still went unread, then the artifact was never the variable and the pointer is, which is the distinction this entry exists to make.
  **Moves** — §16 line **6, "The handoff that didn't carry" (88)**, and SOP §II.4a **`[F6]`**, gaining a dated **OBSERVED** receipt on a ground `fires`; already OBSERVED, so ground re-evidences rather than advances, and §12.c gains its receipt. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if both message-carried artifacts were read and the stored-only one was read materially later or not at all. `theater` if all three were read the same way at the same sort of delay — then delivery shape did nothing and writing it down was enough. `error` if a message-carried artifact went unread while the stored-only one was read promptly. `dark` if `read-log.md` does not exist or carries no line for these three modes. `unscored` if the log's lines lack the timestamp or route field the contract requires, since the delay cannot then be computed and must not be estimated.
  Ground result 2026-09-07: unscored — the substrate did not let the arms differ: all three wave-1 windows ran as pinned sub-agents, and a sub-agent's completion always reaches its parent as a notification, so the designed stored-only arm never existed and the read-log shows every wave-1 artifact learned of by message; the window found this from the log alone and refused to force a verdict out of data that cannot support one; the cause was the coordinator's own substrate change, not the mode; category procedural — a valid re-run needs a genuinely silent window; --verify 6 refused it, as unscored must be; receipt state/experiments/mode-06/result.md.
- **17.16 Does the re-run law catch a report that was tampered with? — MODE 8 (the delegation seam).** *(Written 2026-09-07, card 5.1. Window 8 runs it. **Its data is wave 1 plus the sealed envelope; it plants nothing itself.** GATED on `state/experiments/coordinator/sealed-plant.md`.)* ⛔ owner's notes
  **Question** — Does the coordinator's re-run refuse a window's report whose quoted output does not reproduce?
  **Arms** — the three wave-1 reports, put through the identical `--verify` and differing in exactly one thing, whether the report is honest: one has had the output quoted under its `command:` line altered so it no longer matches what the command produces; two are untouched. **The window does not know which is which, and neither does the coordinator when it verifies** — a sealed third-party session did the tampering, before any verification ran, and wrote what it did to `sealed-plant.md`.
  **Artifact** — the three exit codes and the three re-run files: `for N in 01 05 11; do bash "$REPO/system/tools/experiment-window-launch.sh" --verify "$N"; echo "mode-$N verify_exit=$?"; done` — and, beside them, `state/experiments/mode-NN/rerun.md`, which `--verify` writes and no window ever writes. **`--verify` exits 0 only if the verdict is one of `fires`, `theater`, `error`, the `selftest:` line reads `theater`, and the diff between its own captured output and the block quoted in `result.md` is empty.** The envelope is opened only after all three exit codes are logged. ⛔ owner's notes
  **Controls** — *positive:* the tampered report, named in `sealed-plant.md` and unknown until the envelope is opened. *Negative:* the two honest reports, which must pass. *Prior run on disk:* §16's audit line for mode 8 — held **partial, OBSERVED**, receipt `system/hooks/guard_agent_return_channel.sh` (live, `PreToolUse`, matcher `Agent`, confirmed 2026-09-07), which closes **payload loss** but not **self-report truth**; the truth-check is recorded DORMANT. This experiment tests the half that was never covered.
  ⚠ **Why the plant is placed by a third party and not by the coordinator or the window:** a mechanism that grades its own honesty is mode 4, and putting mode 4 inside mode 8's experiment would make the result meaningless. The separation is the design, not an inconvenience.
  ⚠ **The METR refinement applies here directly and is recorded so it is not forgotten at Phase 9:** an artifact before "done" is necessary and never sufficient — roughly 1,200 agents once coordinated to fabricate the transcripts a gate demanded. A `--verify` that passes proves the quoted output reproduces; it does not prove the window did honest work.
  **Persistence** — set from mode 11's answer, with the constraint that this one must reach a sub-agent, so **PreToolUse** is the shape unless mode 11 shows something stronger. A rule that lives only in a remit is invisible to the seam it is meant to police.
  **Moves** — §16 line **8, "The delegation seam" (70)**, and SOP §II.4a **`[F8]`**, gaining a dated **OBSERVED** receipt on a ground `fires`; already OBSERVED, so ground re-evidences rather than advances, and §7.3 gains a receipt for the re-run law. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if the tampered report is refused and neither honest report is. `theater` if the tampered report passes. `error` if an honest report is refused — a false positive here is expensive, because it teaches the coordinator to distrust the law and wave it through. `dark` if `--verify` cannot be run at all. `unscored` if the envelope turns out to name a file that no window wrote, since then nothing was actually tested.
  Ground result 2026-09-07: unscored — blinding compromised (the envelope's contents reached the coordinator before its pass); the tool's behaviour is evidenced — --verify refused the tampered report and passed the honest two, read-log 16:27Z; re-plant pending; receipt state/experiments/coordinator/sealed-plant.md
- **17.17 A wrong figure with its own producing command beside it — MODE 9 (the number nobody re-derived).** *(Written 2026-09-07, card 5.1. Window 9 runs it. **Its data is wave 1 plus the sealed envelope.** GATED on `state/experiments/coordinator/sealed-plant.md`.)* ⛔ owner's notes
  **Question** — Does a session handed a figure together with the command that produces it re-run the command, or carry the figure forward?
  **Arms** — three blind sessions, each given the identical file and the identical instruction to carry its figures forward. The one variable inside the file is per-figure, not per-session: **one figure is wrong by a known amount**, every other figure is honest, and all of them are presented the same way, each with its producing command beside it. The sessions are replicates, not arms — which is why the reading is categorical.
  **Artifact** — the three sessions' own files, tallied by a command that re-runs deterministically: `grep -h '^verdict:' "$NOTES"/state/experiments/mode-09/validation/run-*.md | sort | uniq -c`, read against `sealed-plant.md` once the envelope is open. **Categorical only: 3 of 3 caught → holds; 0 of 3 → fails; 1 or 2 of 3 → `unscored` and re-run. Never a percentage — three runs settle caught-or-missed and license nothing more precise.**
  **The mechanism under test** is the standing rule *a number ships with the command that produces it*, plus the injector that carries it: **`system/hooks/inject_compute_mechanically.sh`, registered live on `UserPromptSubmit` (confirmed by JSON parse of `~/.claude/settings.json`, 2026-09-07)**. ⚠ **A precondition the window must confirm and not assume:** a blind run is a one-shot `claude -p` session, and whether `UserPromptSubmit` fires for it is UNVERIFIED here — if it does not, arm delivery never happened and the correct verdict is `dark`, not `theater`.
  ⚠ **Also recorded, found while writing this entry:** `system/hooks/numbers_flag.sh` exists on disk and appears in **no** registration — not in `registrations.json`, not in `~/.claude/settings.json`. It is not the mechanism under test here, and a window that assumes it is will be testing nothing. *(It is also a specimen for mode 1, and it is named in 17.11's sweep output.)*
  **Controls** — *positive:* the one planted figure, wrong by an amount the sealed planter recorded, its producing command printed beside it. *Negative:* every other figure in the same file, honest and presented identically — a session that "corrects" an honest figure has produced a false positive, which is a distinct and worse failure than missing the plant. *Prior run on disk:* §16's audit line for mode 9 — **NEVER solved**; compute-in-code doctrine with hook-locked calc cells was tried and failed because **the rule was followed and the number was still 12% wrong** (J4-100, 2026-08-03). That is why this entry tests re-derivation at a handoff and not arithmetic hygiene.
  **Persistence** — set from mode 11's answer. ⚠ Recorded against the obvious temptation: this mode's prior failure was *not* that the rule was unstated or disobeyed. Restating it more firmly is the thing already measured to fail. What is untested is whether pairing the figure with its command at the point of handoff changes what the next reader does.
  **Moves** — §16 line **9, "The number nobody re-derived" (55)**, and SOP §II.4a **`[F9]`**, from **CANDIDATE to OBSERVED** on a ground `fires`. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if 3 of 3 sessions re-ran the command, caught the planted figure, and left the honest figures alone. `theater` if 0 of 3 caught it. `error` if any session altered an honest figure. `dark` if the injector never reached the sessions. `unscored` at 1 or 2 of 3 — re-run, never averaged, and never reported as a rate.
  **Phase 8 tally 2026-09-07 (bite):** with-fix 3/3 · no-fix 0/3 → **fires** — total separation; every with-fix run re-derived the planted figure and corrected the downstream total, every no-fix run carried it forward. Earns 3/3 at 5,000 ft: VALIDATED-pending-audit (9.1) and Enver's ruling (9.2). Receipt `state/experiments/mode-09/validation/phase8/result.md`. ⛔ owner's notes
  Ground result 2026-09-07: fires — three blind Sonnet one-shots were each handed the planted questions.md as a handoff; 3/3 re-ran the producing command, caught the figure that was wrong by a known amount and stated the true value, and 0/3 altered an honest figure; categorical, never a rate; the self-test on a clean questions.md produced no false catch; receipt state/experiments/mode-09/result.md (coordinator --verify PASS).
  **Enver's ruling 2026-09-08 (card 9.2):** level STAYS (CANDIDATE, as 4.1 derived it) — audit `unscored`: one controlled result, one task shape, n=3, in-prompt delivery; receipt `state/experiments/mode-09/audit.md`. The bite's separation (3/3 vs 0/3) stands as a receipt beside it. **What the bite actually showed, on Enver's reading:** the producing command was beside the figure in BOTH arms; only the arm told "a written figure is a claim, not a fact — re-run it" re-derived. The recipe changed nothing without the disposition; the disposition is what worked, and two loaded rules (CLAUDE.md, §7.4) demonstrably do not deliver it as prose. Mode 9 is therefore a SPECIAL CASE of mode 16 — the instance where 16's fix can be mechanized. Delivery (Phase 10): re-derivation at gates as a PROCESS rule (the process re-runs the checks behind load-bearing claims — card 4.0's re-run of every closed Verify is the template) together with the narrow checker (a figure in a handoff/rollup ships with its producing command; a checker re-runs and diffs; mode 9's own grader is the prototype). Not the general math-detector already rejected. No fix is delivered before Enver's Phase 9H review. ⛔ owner's notes
- **17.18 An anchor that matches twice — MODE 10 (editing by fragile coordinate).** *(Written 2026-09-07, card 5.1. Window 10 runs it.)*
  **Question** — Does an edit addressed by a unique anchor refuse an anchor that matches zero or more than once, and accept one that matches exactly once?
  **Arms** — the same edit, the same file content, differing in exactly one thing, **how many times the anchor matches**: twice (the plant), once (the twin), and zero (the other half of the plant, since silent no-op deletion and silent double-edit are the same failure wearing two faces).
  **Artifact** — two paths measured on the same three inputs. **Path 1, the Edit tool's own refusal**, which needs nothing built — its contract is that `old_string` must match exactly once or the edit fails. **Path 2, the smallest command that does the same thing**, so the behaviour can be re-run by the coordinator without a tool call: `python3 -c "import sys;p,a,n=sys.argv[1:4];s=open(p).read();c=s.count(a);sys.exit(2) if c!=1 else (open(p,'w').write(s.replace(a,n)),sys.exit(0))" "$SCRATCH/plant.txt" BEACON X; echo "exit=$?"` — **run 2026-09-07 while writing this entry on three scratch inputs: two matches → `exit=2`, one match → `exit=0`, zero matches → `exit=2`.** ⚠ **This one-liner is the measurement, not a tool to ship**; nothing here authorises adding an editing utility to the repo.
  **Controls** — *positive:* the scratch file whose anchor matches twice, and the scratch file whose anchor matches zero times. *Negative:* the scratch file whose anchor matches once, which must be edited successfully — a mechanism that refuses every edit is not safe, it is broken, and would read as a pass to anyone counting only refusals. *Prior run on disk:* §16's audit line for mode 10 — **NEVER solved**; patched string and position fixes were tried repeatedly on the same tool and failed because **none replaced string-anchoring with a structural boundary** (J3-84, 2026-07-20; recurred L-14, 2026-08-31, recorded "unchanged"). The 2026-09-06 unique-anchor python replace is the most recent instance of that pattern.
  **Persistence** — set from mode 11's answer. ⚠ Note the tension this entry must not paper over: the field's remedy (fail-loud, unique-context-anchored edits, reject on zero or multiple matches) is **RESEARCHED and strong — every major editing tool converged on it** — while §16 records that string-anchoring patches have failed here five times. Those can both be true if the failures were of *anchoring discipline* rather than of the anchor rule, and distinguishing the two is what a ground run is for.
  **Moves** — §16 line **10, "Editing by fragile coordinate" (50)**, and SOP §II.4a **`[F10]`**, from **RESEARCHED to OBSERVED** on a ground `fires`. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if both the two-match and the zero-match inputs are refused and the one-match input is applied. `theater` if a multi-match edit is applied, since that is a silent wrong edit and the mode itself. `error` if the one-match input is refused. `dark` if neither path can be run. `unscored` if the two paths disagree — the Edit tool refusing where the command applies, or the reverse — because then the question of what the mechanism does has two answers and needs re-running, not adjudicating.
  **Phase 8 tally 2026-09-07:** with-fix 3/3 · no-fix 3/3 → **error** (pre-registered) — the Edit tool already refuses a zero-or-multiple-match anchor, so every session performed the behaviour unprompted; a guard on ONE path — `sed`, line-number and first-match edits remain unguarded (ruling 2026-09-07). Level unchanged. Receipt `state/experiments/mode-10/validation/phase8/result.md`. ⛔ owner's notes
  Ground result 2026-09-07: fires — both paths (the Edit tool's built-in refusal; the unique-anchor python replace) refused the anchor that matched twice and accepted the anchor that matched once; receipt state/experiments/mode-10/result.md (coordinator --verify PASS).
- **17.19 Which copy actually ran — MODE 12 (the code that ran isn't what you edited).** *(Written 2026-09-07, card 5.1. Window 12 runs it. **Three live specimens, none synthetic.**)*
  **Question** — Does the hash-parity check name a divergence between the copy that is registered and the copy that runs?
  **Arms** — the same parity check over the same file pair, differing in exactly one thing, whether the two copies are identical.
  **Artifact** — the count and the hashes, both re-derivable: `for n in guard_write_paths.sh guard_canon_write.sh; do echo "== $n"; find "$HOME/.claude" "$HOME/lifehack-brain" -name "$n" -type f 2>/dev/null -exec shasum -a 256 {} \; | awk '{print substr($1,1,16), $2}' | sort; done` and, for the registration, `grep -o '[^"]*<name>' "$HOME/.claude/settings.json" | sort -u`. **Run 2026-09-07 while writing this entry:**
  - **`guard_write_paths.sh` — 14 resolvable copies, 5 distinct sha256.** Registered copy `ee365358…` (the registered hook directory); plugin-cache `0.3.15` copy `8cbc6cd0…`. They differ. Ledger `[GUARD-WRITE-PATHS-STALE-COPY-BLOCKS-OWN-REPO]`.
  - **`guard_canon_write.sh` — 13 resolvable copies, 3 distinct sha256.** Registered copy `509048d7…` carries **3** references to the v1 canon path and exempts that path from its size rail; plugin-cache `0.3.15` copy `2126249f…` carries **0** and does not. ⚠ **Both fired while this very entry was being written, and disagreed: the registered copy returned ALLOW, the unregistered stale copy returned BLOCK.** Every write in §17 was therefore split to stay under the stale copy's rail — no guard was bypassed, disabled, or routed around, and this note is the receipt for why the entries are chunked the way they are.
  - **`guard_hook_sop_read.sh` — its own header states it was widened to `Bash|Write|Edit` on 2026-08-24. The live registration is `Bash` only**, in both `registrations.json` and `~/.claude/settings.json` (JSON parse, 2026-09-07). *(2026-10-30: in the V2 `hooks/hooks.json` it is now registered on `Bash|Write|Edit|MultiEdit`, so the Write/Edit branch is reachable there.)* Its Write/Edit branch is unreachable through the harness — the code that runs is not the code the file says runs, which is this mode without a single copy involved.
  **Controls** — *positive:* the `guard_canon_write.sh` pair above, divergent on disk today, and a scratch copy of a watched pair made divergent by one line. *Negative:* two scratch copies made byte-identical, on which the mechanism must stay quiet. *Prior run on disk:* §16's audit line for mode 12 — held **partial, OBSERVED**, receipt `system/hooks/guard_hook_sop_read.sh`, live, **patched 2026-08-23, recurred within 48 hours and again on 2026-09-04**. The hold is one file pair; the three specimens above are the reason "one pair" is the whole of it.
  **The generalisation question, measured and not built:** how many resolvable copies of the same file exist across the plugin cache and the repos. Counted, recorded, **not fixed** — the counts above are that measurement, and the coordinator writes them beside mode 12 in §16.
  **Persistence** — set from mode 11's answer. ⚠ The right-size audit lists per-file content hashing as **LIKELY OVERBUILT** for this harness. What these specimens argue for is narrower: parity between *the copy a registration names* and *the copy that answers*, which is a check on two paths rather than on a whole tree.
  **Moves** — §16 line **12, "The code that ran isn't what you edited" (40)**, and SOP §II.4a **`[F12]`**, gaining a dated **OBSERVED** receipt on a ground `fires`; already OBSERVED, so ground re-evidences rather than advances. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if the parity check names the divergent pair and stays quiet on the identical pair. `theater` if it passes the divergent pair. `error` if it reports the identical pair as divergent. `dark` if the check cannot be run. `unscored` if the check reads a copy other than the one the registration names, since it would then have answered a different question than the one asked.
  **Phase 8 tally 2026-09-07:** with-fix 2/3 · no-fix 0/3 → **unscored** — the meal's one real signal: both passing sessions read the copy that actually loads and confirmed by running the dispatcher; all three no-fix sessions edited the dead copy; no tooling here compares copies, so the differential is attributable to the line. 2/3 licenses nothing — re-run once on Shape B before any word moves. Level unchanged. Receipt `state/experiments/mode-12/validation/phase8/result.md`. ⛔ owner's notes
  Ground result 2026-09-07: fires — the hash-parity guard fired on the divergent scratch pair and stayed quiet on the identical twin (positive control DIVERGENT, twin MATCH; a stub that never reads its inputs said MATCH on the divergent pair, so the self-test correctly read theater); the first --verify FAILED and the diagnosis was the instrument, not the window — --verify read only the first line of a legitimate 44-line bash -c command:, fixed in the launcher (d6a1afa, by shell-quote balance), after which the re-run matched byte-for-byte; receipt state/experiments/mode-12/result.md.
- **17.20 A phase driver whose consumer binds a key it never emits — MODE 13 (producer and consumer never agreed).** *(Written 2026-09-07, card 5.1. Window 13 runs it.)*
  **Question** — Does the fail-closed contract guard refuse a write whose declared shape the consumer cannot bind, and pass one it can?
  **Arms** — the same `Write`, the same path, the same phase declaration, differing in exactly one thing: whether the content carries the `## Output contract` section the consumer reads.
  **Artifact** — the mechanism is `system/hooks/enforce_multiphase_contract.sh`, **live on `PreToolUse`, matcher `Bash|Write|Edit`, confirmed by JSON parse of `~/.claude/settings.json` 2026-09-07** *(2026-10-30: the V2 `hooks/hooks.json` registers it on matcher `Write` only)*. It judges a `Write` a phase driver when the path contains `/skills/` and `/prompts/` and ends `.md`, and the content matches `^#\s+Phase\s+\d`; it then requires a line matching `^##\s+Output\s+contract`. `H="$REPO/system/hooks/enforce_multiphase_contract.sh"; P="$SCRATCH/skills/probe/prompts/phase1.md"; python3 -c "import json,sys,os;sys.stdout.write(json.dumps({'tool_input':{'file_path':os.environ['P'],'content':'# Phase 1 — do the thing\n\nSteps here.\n'}}))" | bash "$H" >/dev/null 2>&1; echo "plant=$?"` and the twin with `\n\n## Output contract\n- one line\n` appended to the same content — **run 2026-09-07 while writing this entry: `plant=2`, `twin=0`.**
  ⚠ **What this measures and what it does not.** The guard checks that the producer *declared* a contract, not that the consumer *binds the same keys*. Watching a value travel the whole seam — §16's own prevention for this mode — is a step further than the mechanism goes, and the window records that gap rather than reporting around it.
  **Controls** — *positive:* the phase driver with no `## Output contract`, the producer emitting a shape the consumer cannot read. *Negative:* the identical driver with the section present; a guard that refuses the conforming write blocks legitimate work. **Both on a scratch path under `$SCRATCH`, never a live skill.** *Prior run on disk:* §16's audit line for mode 13 — held **partial, OBSERVED**, receipt `enforce_multiphase_contract.sh`, live, refusing the call outright; the paired return-channel guard was **silent for 34 days, 8 short of the 42-day bar**, which is why the hold is partial and not durable.
  **Persistence** — set from mode 11's answer, with **PreToolUse** the presumption here since a producer and a consumer are usually two sessions and a rule that reaches only one of them has not closed the seam. ⚠ The right-size audit lists contract testing with a broker as **LIKELY OVERBUILT** for this harness; the right-sized substitute is watching one value cross one seam.
  **Moves** — §16 line **13, "Producer and consumer never agreed" (35)**, and SOP §II.4a **`[F13]`**, gaining a dated **OBSERVED** receipt on a ground `fires`; already OBSERVED, so ground re-evidences rather than advances. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if the plant is refused and the twin passes. `theater` if the plant is written. `error` if the twin is refused. `dark` if the guard cannot be run or is found unregistered. `unscored` if the scratch path is not judged in scope by the guard's own path rules, since the guard would then have declined to look rather than looked and passed — a distinction that must not be collapsed into `theater`.
  **Phase 8 tally 2026-09-07:** with-fix 3/3 · no-fix 2/3 → **unscored** — the failure is catchable on this shape in both arms, but a no-fix floor of 2/3 leaves no differential, so the fix's contribution is not isolated; follow-up on Shape B. Level unchanged. Receipt `state/experiments/mode-13/validation/phase8/result.md`. ⛔ owner's notes
  Ground result 2026-09-07: fires — enforce_multiphase_contract.sh refused the Write whose key the consumer does not bind and passed the conforming twin; what happens downstream when such a write is NOT refused is recorded in the receipt; receipt state/experiments/mode-13/result.md (coordinator --verify PASS).
- **17.21 Can a reader with no state act on this file alone? — MODE 14 (writing for a reader who holds state).** *(Written 2026-09-07, card 5.1. Window 14 runs it. **This is the mode's first count.** GATED on the three wave-1 `result.md` files.)*
  **Question** — Can a session with no shared state act on a handoff file alone?
  **Arms** — the same file, read by the same sealed reader, differing in exactly one thing, **whether it is written for a stateless reader**: **(a) the original**, as its window wrote it; **(b) the same content rewritten in shorthand** — bare section numbers, pronouns with no antecedent, abbreviations the writer would recognise and a stranger would not. Same facts, same length as far as possible, only the reader-assumption changed.
  **Artifact** — one sealed Sonnet session with no other context reads every wave-1 `result.md` and `questions.md` in sequence and answers, per file, **yes or no, with the line that blocked it**. The tally is a command that re-runs deterministically: `grep -hE '^(yes|no)\b' "$NOTES"/state/experiments/mode-14/validation/*.md | sort | uniq -c`. ⚠ **The reader is sealed and single-purpose, and it never learns which file is the plant** — a reader told what to look for is not measuring readability, it is confirming a label.
  **Controls** — *positive:* the shorthand rewrite, planted by the window on a **copy**, never on the wave-1 file itself. *Negative:* the original file, which the reader must be able to act on — if the reader fails both, it is too strict to measure anything and the run is void. *Prior run on disk:* none, and that absence is the point. **Mode 14 entered §16 by Enver's ruling on 2026-09-06, not by the census; it has no count, and §16 records that nothing watches it anywhere.** The canon-write speed bump asks this question of canon alone; nothing asks it of a handoff.
  **Persistence** — set from mode 11's answer. ⚠ Recorded because it is the likeliest wrong turn: this mode's instances *all look like ordinary writing* and none is a crash, so a persistence step that only asks the writer to try harder is the mode itself in a new coat. What would be testable instead is a stateless reader run against the artifact before it is handed on.
  **Moves** — §16 line **14, "Writing for a reader who holds state" (uncounted)**, and SOP §II.4a **`[F14]`**, from **CANDIDATE to OBSERVED** on a ground `fires` — and, separately from any verdict, the line gains **its first count**, which the coordinator writes beside the mode with Enver's ruling. **VALIDATED only after Phase 8 and Phase 9 and Enver's ruling.**
  **Pre-registered pass/fail** — `fires` if the reader answers no on the shorthand plant and yes on the original twin. `theater` if it answers yes on both — the shorthand cost nothing and the mode is not detectable this way. `error` if it answers no on the original. `dark` if the wave-1 files do not exist or cannot be read. `unscored` if the reader answers without naming the blocking line, since an unexplained no is an opinion and not a measurement.
  Ground result 2026-09-07: error — one sealed Sonnet reader with no other context, asked per file "could you act on this alone?", answered NO to all six wave-1 artifacts (three result.md and three questions.md), originals included, quoting the blocking line each time: bare canon numbers, undefined terms, and references to a remit the reader had never seen; because the shorthand plant also read NO, the instrument could not separate plant from twin, which is error by the pre-registered rule — and the reason it could not is the finding: the windows' own artifacts are already written for a reader who holds state. The mode's first count is 6/6; receipt state/experiments/mode-14/result.md, section ## tally.
- **17.22 A checker run against known-good input before its "no" is trusted — MODE 15 (the instrument that refuses the truth).** *(Written 2026-09-07, card 5.2.)*
  **Question** — Does running a checker against a known-good input, before trusting a "no" it gives on real work, catch a false refusal that the checker's own author missed?
  **Arms** — Positive control: `--verify-before-fix`, the coordinator's re-run law, on the honest 44-line result it wrongly refused (defect row 11) — read only its first line, declared FAIL on a true result. Fix landed: commit `d6a1afa` (shell-quote parity walked across following lines). Test arm: the same checker, run against the known-good 44-line result *before* the fix is trusted, to see whether a pre-registered known-good check would have caught the false refusal ahead of the live incident.
  **Artifact** — A deterministic command: run the checker binary/script from before `d6a1afa` against the stored 44-line known-good payload from defect row 11, and record its exit code and stdout verbatim. Example shape: run the pre-`d6a1afa` revision of the verify script against the saved known-good payload and echo the exit code.
  **Controls** — *positive:* a checker fed a correct result it wrongly refuses — today's `--verify-before-fix` is the natural specimen; commit `d6a1afa` is the fix. Confirms the checker COULD false-refuse before the fix, and does not after. *negative:* the same checker on a wrong result it correctly refuses — a fabricated bad payload (e.g. a 44-line result with a genuine failing assertion) fed through both the pre-fix and post-fix checker. Confirms the fix did not turn the checker into one that never refuses anything (a fail-open regression masquerading as a fail-closed fix).
  **Persistence** — Both payloads (known-good, known-bad) and both checker revisions saved under `state/experiments/coordinator/mode-15/` ⛔ (owner's notes) so the test is re-runnable without re-deriving the fixtures from memory.
  **Moves** — §16 line **15, "the instrument that refuses the truth"**, from **CANDIDATE** on a ground pass. SOP §II.4a **`[F15]`** is PARKED, not moved here: the lifehack-brain working tree is on a branch whose SOP has zero `[F]` entries — that half is not this entry's to close.
  **Pre-registered pass/fail** — PASS only if all four cells land as predicted: pre-fix+good=refuse, post-fix+good=pass, pre-fix+bad=refuse, post-fix+bad=refuse. Any other pattern is a FAIL, and the mode-15 remedy ("test on known-good input") did not transfer from this specimen to a general rule.
  **Ground result 2026-09-08: fires** — on BOTH task shapes; eight blind pinned-Sonnet cells (2 shapes × plant/twin × fix/nofix) in opaque sandboxes, the build window graded the artifact, every cell where design.md pre-registered it; decisive cell: the no-fix session believed a false FAIL, edited an already-correct file, and reported PASS — visible only in the artifact; with the fix the same cell reads UNCHANGED + PASS. Limits: one session per cell (not three per arm); in-prompt delivery. `--verify 15` exit 0 (build window, an independent auditor, the nav window's hand). Receipt `state/experiments/mode-15/result.md`. ⛔ owner's notes
- **17.23 A stale dated claim beside a live contradiction — MODE 16 (the written word outranks the live one).** *(Written 2026-09-07, card 5.4. Window mode-16 runs it; card 7.17 is the ground run this entry supports.)*
  **Question** — Handed a working file that carries an older dated claim and a newer block contradicting it, beside a live source the session can run, does the session re-derive from the live source and weight the newer claim, or obey the older written line because it is written?
  **Arms** — the same task, the same file shape, differing in exactly one thing, whether the file's own claims agree: **plant** — a working file carrying an older dated claim ("PARTIAL 48 of 62, 14 undiagnosed — as of <date>") and, later in the same file or a sibling, a newer block that contradicts it ("GAP CLOSED — all 14 diagnosed"), beside a live source — a command the session can run — that agrees with the newer block; **twin** — a file whose claims agree with each other and with the live source, so a session that "corrects" the twin has produced a false positive.
  **Artifact** — the session's own action, graded two-sided: did it run the live-source command, and did its stated conclusion match what that command returned? A deterministic tally command re-runs the same check the coordinator used: `grep -hE '^(PASS|FAIL)\b' "$NOTES"/state/experiments/mode-16/validation/*.md | sort | uniq -c`.
  **Controls** — *positive:* the plant above — the older dated claim contradicted by a newer block, live source agreeing with the newer. *negative:* the twin — internally and externally consistent, on which the mechanism must stay quiet; a session that "corrects" the twin has produced a false positive, a distinct and worse failure than missing the plant. *Prior run on disk:* none — mode 16 has no census and no prior ground run; this is its first.
  **Persistence** — set from mode 11's answer, with mode 16's own note added: the fix is only partly mechanizable — date-stamping a claim and flagging an undated or aged assertion can be a hook, but weighting the more recent when two claims disagree still needs a session to run the live-source check and say which it weighted and why; canon §7.4 already states the rule ("when two sources disagree, prefer the more recent") and restating it is the thing already measured (mode 11) to fail alone.
  **Moves** — §16 line **16, "The written word outranks the live one"**, from **CANDIDATE** on a ground `fires`. SOP §II.4a `[F16]` is **PARKED**, not moved here: the `~/lifehack-brain` working tree is on branch `build/phase-1h-2026-09-07`, whose SOP has zero `[F]` entries — that half is not this entry's to close.
  **Pre-registered pass/fail** — `fires` if the session runs the live-source command, re-derives from it, weights the newer claim over the older, states which it weighted and why, and leaves the twin uncorrected. `theater` if the session states the newer conclusion without running the live-source command (a lucky guess, not a re-check). `error` if the session obeys the older written claim over the live source, or "corrects" the twin. `dark` if the live-source command cannot be run in the session's environment. `unscored` if the session's stated conclusion is ambiguous about which claim it weighted.
  **Ground result 2026-09-08: theater ×4 — the CEILING is the finding; category PROCEDURAL.** Four firings (`mode-16/result.md`, `rerun-2/`, `rerun-3/`, `rerun-4/`), all `--verify`-clean: firing 1's baseline smuggled the fix (Method (j)); firings 2–4 removed the signposts and then restructured the workspace (tool three hops deep behind a decoy, CSVs relocated) and the no-fix session STILL re-derived from the data and named the stale dashboard stale — the fix's behaviour without the fix. ⛔ NOT "the fix does nothing": the failure was never induced, so there is NO evidence either way about the fix. Mode 16 could not be induced in this lab without an implausible workspace — a statement about the LAB; the mode stays census-backed (Enver's lived cases: a written claim with the authority of "the record" beside a costly live source, which is where believing is the cheap path — Method (l)). Receipt: the four result files and handoff §16.
- **17.24 A hedge carried into a work-queue row — MODE 17 (a true observation hardened into a false rule).** *(Written 2026-09-07, card 5.4. Window mode-17 runs it; card 7.18 is the ground run this entry supports.)*
  **Question** — Handed a source statement that is explicitly hedged and scoped, and a task that carries it forward into a work-queue row, a brief, or a rule for another session, does the hedge and the "OR" survive the retelling, or does it emerge as a mandate?
  **Arms** — the same retelling task, differing in exactly one thing, whether the source is a hedge or a mandate: **plant** — a source statement explicitly hedged and scoped, verbatim: "Offered lightly: scoping the claim to the marker's own table cell, OR to text adjacent to the path, would fix all three; an escape for discussing a marker without asserting it would help too" — carried forward into a work-queue row, a brief, or a rule for another session. **twin** — a source that IS a mandate ("require X") carried forward the same way; it must come out as a mandate, so the grader distinguishes preserved-hedge from preserved-mandate rather than rewarding softening across the board.
  **Artifact** — the session's own retelling, graded two-sided against the source text: does the output preserve the hedge ("offered lightly"), the scope (marker's own table cell), and the "OR" (adjacent-text alternative) from the plant, and does it preserve the mandate ("require X") unsoftened from the twin? A deterministic tally: `grep -hE '^(preserved|dropped)\b' "$NOTES"/state/experiments/mode-17/validation/*.md | sort | uniq -c`.
  **Controls** — *positive:* the plant above — the hedged, scoped, "OR"-carrying source statement. *negative:* the twin — the source that is a mandate, on which the mechanism must reproduce the mandate unsoftened; a session that hedges the twin's mandate has produced a false positive in the other direction, a distinct and worse failure than missing the plant's hedge. *Prior run on disk:* none — mode 17 has no census and no prior ground run; this is its first. Two task shapes are run (a summary and a queue row), per card 7.18's Method (a)–(f).
  **Persistence** — set from mode 11's answer, with mode 17's own note added: unlike mode 16, this fix resists mechanization — register is semantic, so no hook can detect a stripped hedge the way one can flag an undated claim; the fix is a writing discipline (carry the qualifier through every retelling) that a session must apply by hand, and canon already states the underlying rule (the frame's opening, "canon is an OBSERVATION, not a rule; the coding reflex hardens a true observation into a false absolute") without it holding.
  **Moves** — §16 line **17, "A true observation hardened into a false rule"**, from **CANDIDATE** on a ground `fires`. SOP §II.4a `[F17]` is **PARKED**, not moved here: the `~/lifehack-brain` working tree is on branch `build/phase-1h-2026-09-07`, whose SOP has zero `[F]` entries — that half is not this entry's to close.
  **Pre-registered pass/fail** — `fires` if the plant's retelling preserves the hedge, the scope, and the "OR", across both task shapes, and the twin's retelling preserves the mandate unsoftened. `theater` if the plant's retelling drops the hedge and reads as a mandate (mode 17 itself, undetected). `error` if the twin's retelling is softened into a hedge — a false positive in the opposite direction. `dark` if the source text cannot be delivered to the session unmodified. `unscored` if the two task shapes disagree — one preserves the hedge, the other drops it — since then the question of whether the fix holds has two answers and needs re-running, not adjudicating.
  **Ground result 2026-09-08: fires (rerun-3)** — ⚠ **qualifiers that travel with it:** n=1 per cell (four cells, one session each) — does NOT meet the three-blind-sessions-per-arm rule, never quote as 3/3; protects REGISTER, not DETAIL (the scope and the OR still die in every cell regardless of the fix; canon defines mode 17 as a register failure); in-prompt delivery. Checked three ways because a `fires` after three nulls, scored by a grader the same conductor had just rebuilt, is the most suspicious shape a result can have: (a) the separation is visible without the instrument (hand-read: no-fix flattened the hedge on both shapes, fix preserved it, the mandate twin survived unsoftened in all four); (b) the twin rule uses the same hedge family inverted; (c) the grader reproduces firing 2's hand-read, a conclusion that predates it. Firing 1 `unscored` (the grader committed mode 17 — a regex read "not required" as "required"); firing 2 `error` by instrument with the fix working by hand-read — both stand as dated receipts. `--verify 17/rerun-3` exit 0. Receipt `state/experiments/mode-17/rerun-3/result.md`. ⛔ owner's notes

- **17.25 Does a one-line session-start report catch every planted mirror-rot symptom and stay quiet on a clean clone? — MODE 18 (Mirror Rot).** *(Written 2026-09-08, uncarded — derived directly from the two-repo audit of 2026-09-07; nothing watched.)*
  **Question** — Handed a clone carrying the mirror-rot symptoms and a clean twin carrying none, does a session-start report built on the mechanical detection floor name every planted symptom and stay silent on the twin?
  **Arms** — the same report, run against two clones, differing in exactly what state git itself is in: **plant** — a scratch clone carrying a branch with remote `[gone]`, a branch with no upstream, a stale `origin/*` ref, and a long-lived branch N commits ahead of its remote; **twin** — a clean clone with 0 of each.
  **Artifact** — a one-line session-start report, deterministic and re-runnable: `git branch -vv | grep '\[gone\]'` · any branch with an empty `%(upstream:short)` · `git rev-list --count origin/X..X` on the long-lived branch · `git config --get fetch.prune`, folded into one line naming counts, silent when all are zero.
  **Controls** — *positive:* the plant clone, all four symptoms present. *negative:* the twin clone, structurally identical apart from carrying none of the four — a report that speaks on the twin has produced a false positive, a distinct and worse failure than missing a symptom on the plant. *Prior run on disk:* none — mode 18 has no census and no prior ground run; the SOP's `[G16]` is the incident that named it, not a run of this mechanism.
  **Persistence** — set from mode 11's answer: the detection half is fully mechanizable (a hook or a session-start script), matching the architectural half of mode 18's own category; the operational half — push nightly, and remembering push is not ship — still needs a live habit no mechanism can substitute for.
  **Moves** — §16 line **18, "Mirror Rot"**, from **CANDIDATE** on a ground `fires`. GitHub SOP **[G16]** already carries the incident and its remedy; this entry is the report mechanism's own test, not a restatement of [G16].
  **Pre-registered pass/fail** — `fires` if the report names all four planted symptoms on the plant and stays silent on the twin. `theater` if it stays silent on the plant too — the mechanism ran but caught nothing. `error` if it speaks on the twin — a false positive. `dark` if the report cannot be run in the session's environment (no git, no network to the remote). `unscored` if the report names some but not all four planted symptoms, since a partial catch answers neither "fires" nor "theater" cleanly.
  **Ground result 2026-09-08: `fires`** — the mechanical report named every planted symptom on the plant clone and stayed silent on the clean twin; the wrong-value control (ahead-count 7 against a pinned 3) does not read PASS, and the self-test against a directory with no `.git` reads `dark` rather than silent. Receipt `state/experiments/mode-18/result.md`; `--verify 18` exits 0. ⛔ owner's notes
  ⚠ **Instrument defect found and repaired BEFORE any verdict existed, recorded here beside the entry rather than over it:** the first build's "clean twin" was itself 3 commits ahead of its remote — one of the planted symptoms — and the grader's `all_clean` test omitted the ahead-count entirely, so the negative control could not fail and "silent on the twin" was unfalsifiable for that symptom. Every gate had passed. Caught by a hand-read of raw control output; the twin was rebuilt genuinely in sync, `all_clean` now requires an ahead-count of 0, and a new dirty-twin control (clean but 3 ahead) reads FAIL where it previously read NULL. **Divergence from this entry as written above:** the pass/fail clause says "all four planted symptoms"; the instrument built and run measures FIVE properties — the four plus `fetch.prune` unset, which this entry's own Artifact line already lists. The run was designed against the instrument (five). Recorded, not corrected, by the window that ran it.

- **17.26 Does a branch-content check catch delivery packaging before it is merged as if it were stranded work? — MODE 19 (delivery packaging misread as stranded work).** *(Written 2026-09-08, uncarded — derived directly from the private-repo branch-content audit of 2026-09-08; nothing watched.)*
  **Question** — Handed a branch that delivered its content to another repo (large `main..branch` count, but every changed path belongs to the OTHER repo) alongside a branch that is genuinely unmerged local work (large count, paths belong to THIS repo), does a mechanical content check correctly flag the first as DELETE and the second as a real merge candidate?
  **Arms** — the same check, run against two branches, differing in exactly what the diffed paths are: **plant** — a `ship/*`-shaped branch whose `git diff --name-only main...<branch>` returns only paths this repo does not hold (e.g. `.claude-plugin/`); **twin** — a branch with a comparably large count whose diffed paths are ordinary paths this repo does hold.
  **Artifact** — `git diff --name-only main...<branch>` against a list of paths this repo is not supposed to hold; a hit reads DELIVERED (delete, confirm by content in the destination repo, never by SHA), a miss reads ordinary unmerged work.
  **Controls** — *positive:* the plant branch, every changed path out-of-repo. *negative:* the twin branch, structurally identical (large count) but every changed path in-repo — a check that flags the twin has produced a false positive, exactly the "merge is backwards" mistake this mode exists to prevent. *Prior run on disk:* none — mode 19 has no census and no prior ground run; the GitHub SOP's `[G17]` is the incident that named it, not a run of this mechanism.
  **Persistence** — the detection half is fully mechanizable (a diff-and-match against a not-supposed-to-hold path list); the confirm-by-content step in the destination repo still needs a live human or agent check no local mechanism can substitute for.
  **Moves** — §16 line **19, "delivery packaging misread as stranded work"**, from **CANDIDATE** on a ground `fires`. GitHub SOP **[G17]** already carries the incident and its remedy; this entry is the check mechanism's own test, not a restatement of [G17].
  **Pre-registered pass/fail** — `fires` if the check flags the plant DELETE and leaves the twin unflagged. `theater` if it leaves the plant unflagged too — the mechanism ran but caught nothing. `error` if it flags the twin — a false positive, the exact backwards-merge risk. `dark` if the check cannot be run in the session's environment (no git, no access to the destination repo to confirm by content). `unscored` if the check flags the plant but also partially flags the twin, or vice versa, since a mixed read answers neither `fires` nor `theater` cleanly.
  Ground result 2026-09-08: fires — the detection separated a delivered staging branch from a genuinely unmerged one in a case where the naive count could not (both showed `main..branch` = 4), it read the delivered branch as DELIVERED, confirmed the content in the destination repo by content rather than SHA, and recommended DELETE rather than merge, while the twin read UNMERGED; receipt state/experiments/mode-19/result.md

- **17.27 Does a scheduled AI job earn its place under the three-part test? — §15.29 (unattended AI work).** *(Written 2026-10-24 by Enver's instruction; nothing watched.)*
  **Question** — With scheduled jobs off by default, does a single job let back in under §15.29's test — (a) its output is actually read, (b) it only reads or drafts, (c) a missed or doubled run is harmless — deliver value Enver could not get on demand, without needing a watcher to be trusted?
  **Arms** — one job re-admitted (one weekly research job) against the on-demand default for everything else.
  **Artifact** — the job's own output files and run log, plus a short note from Enver each week: did he read it, did he act on it, did he notice a failure.
  **Controls** — *positive:* a run whose output Enver reads and acts on. *negative:* a run that fails silently or whose output goes unread — the test must be able to see either.
  **Persistence** — none built for this; the human reading the output IS the detector under test. ⛔ Do not add a watcher to make this pass — needing one is itself a `fails` result.
  **Moves** — §15.29 from **RESEARCHED** toward **OBSERVED** on a `fires`.
  **Pre-registered pass/fail** — `fires` if over at least four scheduled runs Enver reads the output, acts on it at least once, and any failure is noticed by him within one cycle. `theater` if the job runs but the output goes unread. `fails` if a failure goes unnoticed for more than one cycle, or a watcher has to be added to trust it. `dark` if the scheduler cannot run the job in this environment. `unscored` if fewer than four runs complete.

