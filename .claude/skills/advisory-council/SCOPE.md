---
topic: [skill-design, multi-session-coordination]
title: /advisory-council — Skill Scope
status: draft-scope
created_at: 2026-06-10
updated_at: 2026-07-21
authority: user-directed (root mode, system skill design)
research_basis: records/context/2026-06-10-council-of-advisors-consensus-map.md (2 /research passes)
related: [[council]] (desk-canon parent pattern)
---

# /advisory-council — Skill Scope

## One-liner
A single, globally-callable skill for chairing a council of domain advisors over a decision.
On invoke it either **loads a saved council** from a central library or **helps you build a
new one** — then runs a chaired **diverge → argue → converge** session: independent positions,
loopable adversarial red-team rounds, and convergence moves you invoke (the floor, the
steelmanned dissent, the integrated plan). The engine is fixed; each council is a swappable
roster cartridge. Councils are fully centralized so the skill works from any desk, any conversation.

## Trigger
`/advisory-council` — then the user says either "build a new council" or "convene my {X}
council." If neither is clear, the skill routes (see §3). Globally available; not desk-bound.

---

## 1. Why this exists (research-grounded)

A council surfaces better, more diverse output — but the lever is **role-as-focus** (narrowing
the model onto one domain lens), NOT identity/personality, and NOT independent fact-checking.
Every load-bearing choice below traces to the saved consensus map. Headlines:
- **Persona identity ≠ accuracy.** Heavy backstory adds tokens and can *lower* factual accuracy;
  role-as-focus helps. → personality is for the human, fenced off from the analysis.
- **Independent-then-synthesize beats debate.** Freeform multi-agent debate collapses into
  sycophantic false consensus (~85% cave-in). → positions are blind first; the chair synthesizes.
- **Structured adversarial critique DOES help (~13%).** The failure is *unstructured* debate.
  → the red-team round is structured, domain-bounded, snapshot-based, anonymized, refute-mandated.
- **Shared base model = shared blind spots.** Diversity is real but shallow. → high-stakes flag;
  the steelman move; real independence = heterogeneous models.
- **Multi-agent costs ~4–15×.** → route to the relevant few; loop only when the chair chooses.

**External validation (2nd /research pass).** Named precedent for every choice: Mixture-of-Agents
(Wang et al., ICLR 2025) = independent→read-once-snapshot→synthesize; CrewAI/LangGraph/AutoGen =
engine + swappable-roster split ("completely settled"); Karpathy `llm-council` + Sourcery panel
(error 40%→20% at ~2× cost) = the council pattern; thin personas for human legibility = universal.

Architectural parent: this repo's `/council` (isolated subagent per desk, synthesized). This skill
**generalizes** it from desk-canon to an arbitrary, user-built roster, and adds the chaired session.

---

## 2. Core model — engine + cartridge + central library

- **One skill (the engine):** the fixed front-door → chaired-session machine. Domain-agnostic.
  Lives once at `.claude/skills/advisory-council/`. Globally callable.
- **A council (a cartridge):** a roster file defining the advisors for one subject. Swappable.
- **Central library:** ALL councils live in `<notes>/councils/` — fully centralized so any
  council is callable from anywhere, any desk, any conversation. No desk-local councils.

---

## 3. The front door — convene or create (NO GUESSING)

A hard binary. The skill never auto-picks a council or improvises one — it either loads an
explicitly identified saved council or goes down the build path.

```
On invoke:
  • User names a council ("convene my investing council")
        → registry lookup.
          - confident match → LOAD it → chaired session.
          - no match → "I don't have an 'investing' council. Build one, or did you
            mean: {close names}?"  (never silently load a different council)
  • User says "build a new council"
        → BUILDER (§6).
  • User is unspecific / unsure
        → read registry, present the list: "Which council? You have: {names}. Or build new."
          - library empty OR nothing fits → "We don't have a council of advisors for this
            yet — let's build one." → BUILDER.
```

Doctrine tie-in: this is "Confidence Requires a Source" / "ask, don't guess" applied to routing.
Load something real, or build something new. No random middle.

---

## 4. The chaired session (the user-facing flow)

It should feel like **a room the user chairs** — the AI convenes and runs it; the user steers at
every seam. Nothing auto-advances; the chair holds the gavel. The arc is **diverge → argue →
converge**, and Stages 1–2 loop until the chair is satisfied, with free backtracking.

> **Auto-context:** before Stage 0, if a project brief / plan is armed in the session,
> the engine auto-injects a **settled-ground card** (the brief's decided boundaries) as the pre-filled
> frame, chair-confirmed — see SKILL.md `## Auto-context from a live project`.

```
STAGE 0 · FRAME      Confirm the question; state who's convening + why (routing); let the
                     chair adjust the room before anyone speaks.

STAGE 1 · DIVERGE    Independent, blind positions — compact + voiced for legibility.
        ⟲ GATE:      "Send them to argue — or another divergent pass? (add a lens, sharpen
                     the question, or have them take an angle they missed)"  Loops freely.

STAGE 2 · ARGUE      Structured red-team round (see §9). Conflicts surfaced vividly.
        ⟲ GATE:      "Done — or keep hashing it out? I can press the unresolved conflicts,
                     or point me at what they glossed over."  Loops; the skill flags
                     diminishing returns ("no new conflict this round — converge?").

STAGE 3 · CONVERGE   Chair-invoked moves (§5). Not automatic.

STAGE 4 · LAND       The artifact: plan/floor · surviving tensions · A–F grades ·
                     human-expert flags. Durable, saveable.

BACKTRACK at any seam: from converge → argue more; from argue → add a lens. A room, not a
conveyor belt. Pause-and-steer at BOTH seams (after diverge, after argue).
```

**Loop safety (the one risk).** Looping the argument is technically multi-round debate (the
documented failure mode). Protected by: (1) each round critiques the *current* positions only —
advisors carry no swelling transcript; the **orchestrator holds the running conflict ledger**;
(2) the chair's steering between rounds keeps each loop purposeful; (3) the diminishing-returns
signal tells the chair when more rounds add nothing. Looping divergence is strictly safe (more
independent samples).

---

## 5. The convergence moves (Stage 3)

Three moves, run in this order by default, each individually invocable by the chair:

1. **The floor ("center of the Venn") — orient.** What survived every lens, tagged with the
   shared-blind-spot flag ("here's the assumption the agreement rests on — sanity-check it").
   Answers *"what's safe?"*
2. **Steelman the dissent — stress-test.** Take the loudest *unresolved* objection and argue it
   at full strength: "the strongest case the whole council is collectively wrong." The antidote
   to false/shared consensus. Answers *"what if the agreement is the mistake?"*
3. **The integrated plan ("lock them in a room") — act.** The ORCHESTRATOR (not agents
   negotiating) drafts the one plan satisfying each advisor's non-negotiables with explicit named
   tradeoffs, then a **veto-check ratification**: each advisor, isolated, checks only "does this
   cross a hard line in my domain?" — a veto, not an agreement vote ("can you live with it?"
   resists sycophancy; "do you agree?" invites it). Answers *"what do I do?"*

Order rationale: orient → try to blow a hole in it → build on ground that survived the attack.
"Press a specific conflict" is NOT a convergence move — it's more arguing, so it lives in the
Stage-2 loop.

---

## 6. The Builder — create a council on any subject

Domain-general. Good = **distinct, non-redundant lenses spanning the decision surface** (lens
diversity creates value; redundancy wastes it). AI-proposed, human-curated:

```
1. FRAME      "What's this council for, and what calls will it chew on?" (subject + decision type)
2. PROPOSE    Skill proposes ~6–10 candidate lenses covering the angles that matter, each with a
              one-line rationale, and actively DEDUPES ("these two overlap — merge?").
3. CURATE     Chair keeps / cuts / merges / adds / adjusts granularity.
4. FLESH      Per kept lens: draft the reasoning core (Domain/Catches/Refuses/Bias). Then
              character creation — chair names them + sets a vibe, or "give me a grizzled retired
              inspector for the code lens" and the AI writes the fenced voice. Personality is pure
              upside here (legibility, zero accuracy cost) — lean into it.
5. CHARTER    Grading rubric + high-stakes policy (sensible default, editable).
6. SAVE+REG   Write to the central library; add the registry entry.
```

Quality-of-life paths: **clone & modify** an existing council; **grow/edit** mid-session ("that
lens was gold, keep them" → add advisor, save back). Councils improve with use.

---

## 7. The Library + Registry (centralized)

- **Library:** `<notes>/councils/{slug}/council.md` — every council, one home each.
- **Registry:** `<notes>/councils/registry.md` — the index the front door reads:
  `name · slug/path · one-line scope · created`. The Builder maintains it on save/edit.
- Fully centralized → callable from any desk/conversation with identical behavior.

## 7b. Persistence boundary — cartridge vs. memory

Two kinds of content, two destinations, **never mixed**:

- **The COUNCIL** (who the advisors are) → the library cartridge. **Read-mostly.** The ONLY
  writes are roster-definition changes via the Builder (create / grow / refine). It never
  receives session output.
- **The OUTPUT** (what a session concluded — plans, decisions, findings, critical info) →
  routed through the normal memory path: `/save` → the **Archivist places it** in the
  correct project's `records/` · `state/` · `canon` (cross-project = one home + a pointer).
  **NEVER written into the library.**

Rules:
- **The skill never auto-persists.** Stage 4 yields the artifact; the user `/save`s it (manual
  save-back default). Conversation is disposable — only the keeper is routed.
- **Critical info is the Archivist's to place** — by subject/project, not into the council file.
  A foundation finding goes to your own records, not into an advisor's block.
- **One legitimate write-back:** a roster improvement (a useful new lens, a sharper `Catches`)
  → via the Builder, to the cartridge only.
- **Optional charter field** `Routing home (hint): {project}` tells the Archivist where this
  council's outputs usually belong (e.g. a home-renovation council → your home-projects notes).
  A hint, not a bypass — Archivist adjudicates.

---

## 8. Roster (cartridge) schema

A council file = a one-time **charter** header + N **advisor** blocks.

**Charter:** synthesis rules, A–F grading rubric, high-stakes policy, co-convene hints, the
"does not replace a human expert" line.

**Advisor block:**
```
### {Name "Nickname" Surname} — {Lens title}
Domain:  {what they cover}
Catches: {the specific failures/risks they reliably spot}
Refuses: {what they won't do / won't call something}
Bias:    {their decision tilt}
--- voice (delivery only — does NOT drive the analysis) ---
{5–6 lines of personality for human legibility: cadence, signature phrases, quirks}
Convene for: {keyword} · {keyword} · {keyword}
```
The `Domain/Catches/Refuses/Bias` block is the reasoning core (clean, instruction-like). The
`voice` block is fenced, used for delivery only — protects accuracy, gives the human a character.

---

## 9. Mechanical engine + subagent contract

```
ROUTE      Orchestrator scans each advisor's "Convene for:" keys vs the question; picks 2–4.
           States who + why. Honors chair force-include/exclude. Never convenes all by default.
DISPATCH   Each picked advisor → own ISOLATED, parallel subagent (model: opus), loads only its
           block + shared context, blind to peers. Returns compressed verdict.
           (When a project is live, "shared context" includes the settled-ground card + two-tier
            framing line — boundary context, never a peer position — see SKILL.md `## Auto-context`.)
RED-TEAM   (Stage-2 rounds) advisors re-run as isolated subagents over a STATIC, ANONYMIZED
           snapshot of peers' positions (Position A/B/C — judge the argument, not the authority),
           explicit refute mandate, domain-bounded.
SYNTHESIZE Orchestrator only — advisors never vote to agree. Produces §10 output.
```

**Subagent contract:** Opus (the sole sanctioned exception to this repo's Subagent Model Selection guidance — advisors reason, opus earns its cost; a council's locked contract may pin otherwise, e.g. the 7-lens market-analysis council stays sonnet);
isolated; blind in diverge, snapshot in red-team; loads its own block + shared context only;
returns `position · risks caught · grade A–F · the A+ move · what it refuses/flags` (red-team adds
`which peer claim it challenges + why`). No raw dumps.

---

## 10. Synthesis output (the deliverable)

1. Who convened + why. 2. **Floor** (+ blind-spot flag). 3. **Surviving conflicts** (flag which
held through red-team). 4. **Grades** (each A–F + A+ move; orchestrator overall read).
5. **Integrated plan** (+ veto-check results). 6. **High-stakes flag** — "sharpens questions;
does not replace {engineer/inspector/licensed pro} sign-off" for load-bearing/life-safety/expensive calls.

**Synthesis guard:** weigh substance, never the most vivid/confident phrasing. A persuasive-but-wrong
critique reaching an uncalibrated judge is how structured critique backfires (Wynn et al. 2025) —
rank by evidence/domain-fit; a lone confident dissent does not override the rest by force of tone.

---

## 11. Boundaries / non-goals

- **Not a fact-checker** (shared base model → shared errors; diversifies lenses, not facts).
- **Not a human-expert replacement** (AI sharpens, humans sign off).
- **No live debate room** (arguing = structured Phase-2 snapshot only).
- **No auto-convene-all; no guessing a council** (load a named one or build; §3).
- **Advisors don't decide** — only the chair + orchestrator adjudicate.
- **The engine ships zero advisors** — all domain knowledge lives in cartridges.

---

## 12. Where it lives

- **Engine:** `.claude/skills/advisory-council/SKILL.md` (+ this SCOPE.md). System skill,
  symlinked per machine per the Skill Registration Chain. Globally callable.
- **Councils + registry:** `<notes>/councils/` (centralized).
- **Reference/context:** wholesale long/image files (product manuals, zoning documents, and
  similar reference material) kept un-ingested for reference; advisors are pointed at them,
  not fed them inline.

---

## 13. Build sequence (proof before multiplying)

1. **Distill the first council** — one real council, fully charted: charter + the kept
   advisors (lens core + fenced voice + convene-for). Register it. Wire any reference
   files the domain needs (kept wholesale, not ingested).
2. **Manual proof** — chair one full session against a real decision the user actually faces:
   confirm routing, loop gates, voices, a surviving conflict, and the three convergence moves.
   Tune the schema against what that real run actually needed.
3. **Generalize the engine** — only after the council proves out, write the `/advisory-council`
   SKILL.md (front door + chaired session + Builder), using `superpowers:writing-skills`.
4. **Register** — folder + per-machine symlinks; confirm it appears in session reminders.

---

## 14. Open decisions (carried)

- Heterogeneous-model advisors (real epistemic diversity) — future option, not v1.
- Red-team: one round vs up to two for the hardest calls — decide after the proof run.
- Whether the floor auto-renders inside the integrated-plan move or stays fully separate —
  decide from the proof session feel.

## Resolved
- One skill, build + run under one front door. ✓
- Fully centralized library (`<notes>/councils/`), callable anywhere. ✓
- Hard no-guess front door: load a named council or build one. ✓
- Stages 1–2 loop, no auto-advance, free backtrack. ✓
- Convergence = floor → steelman → integrated plan + veto-check. ✓
