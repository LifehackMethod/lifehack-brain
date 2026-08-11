---
id: system-playbook-design-process-sop
title: Design Process SOP — vocabulary + grammar + examples (the anti-wobble design doctrine)
record_type: playbook
created_at: 2026-06-22
updated_at: 2026-06-22
status: living
version: v1
authority: user
---

# Design Process SOP

> The operating doctrine for agent-driven design work: how to build a design system the agent
> won't wobble against, how to iterate fast without drifting, and when to reach for a generation
> tool vs. implement directly. Promoted from the grammar-layer research (2026-06-22); **living v1 —
> refined from each real rep, not frozen.** Loaded by the design skill; companion to
> `build-conductor-sop.md` (orchestration). Full basis: `records/context/2026-06-22-design-process-sop-draft.md`.

## Core thesis

**The agent implements; the design system is the source of truth. A complete system =
vocabulary (semantic tokens) + grammar (usage / composition / negative rules + closed-value
sets) + examples (canonical compositions), fed lean + always-on.** Tokens give vocabulary,
not grammar — a missing grammar layer is exactly what makes the agent wobble. Tight ≠
exhaustive: lean + always-current beats comprehensive + stale.

---

## The two halves

Design work splits into two phases. Don't skip the first to reach the second faster — false economy.

**(A) BUILD the system** — discovery → vocabulary + grammar + examples. Front-loads ~75% of the
effort; pays off every subsequent iteration. Sections ①, ④, ⑤ live here.

**(B) ITERATE against it** — look-vs-function loop + reference-diff. The last 25%. Sections ②, ③
live here. Section ⑥ spans both.

---

## ① The complete design system — vocabulary + grammar + examples ⭐⭐

*The ground floor. Missing any one layer is what causes the dashboard swamp.*

**Vocabulary — semantic tokens.** Name by PURPOSE, never appearance: `--color-action-primary`
not `--blue-500`. Structured (DTCG-style JSON, stable v1 Oct 2025). Scattered prose tokens are
not vocabulary — they're hints. *Single biggest hallucination-prevention lever.*

**Grammar — the wobble-killer (most-missing piece).** The agent reads `--spacing-md: 16px`, knows
the value but not when / where / in-what-relationship → invents its own grammar → wobble. Grammar
closes the gap:
- **Usage rules** — when this token fires, what context calls for it.
- **Composition contracts** — parent/child relationships, allowed nestings, forbidden pairings.
- **Negative rules** — explicit "must NOT" (e.g. *must NOT add a 5th status color*, *must NOT
  fabricate content to fill a slot*, *must NOT use a pie/donut*).
- **Closed-value sets** — the agent picks from an enumerated list; it never infers a value.

**Examples — canonical composed views.** Pattern-match at the view level, not the atom level.
These double as the golden templates for the reference-diff in ③ (one artifact, two jobs).

**The 6-point "tight" test** — tight when ALL six pass: (1) semantic token names; (2) closed-value
sets on every dimension that can vary; (3) always-on foundations re-injected every turn; (4) explicit
composition contracts; (5) negative rules present; (6) canonical composed examples per view type.

**Completeness test:** *stuck iterating the same surface past ~3 rounds → your grammar layer is too
thin. Fix the spec, not the output.*

**Delivery — lean always-on:** foundations (spacing / type / color-in-context) as a compact block
re-injected every turn (the skill anchor); component contracts on demand (JSON for contracts,
Markdown for rules/intent — JSON: higher accuracy, ~80% fewer tokens). Keep the always-on block
lean — past ~200 lines it starts being ignored.

---

## ② Look vs. function — and the wobble check ⭐

**Every change is a LOOK tweak or a FUNCTION/DATA change. Misclassifying is the #1 source of
wasted iteration.**
- **LOOK** — render layer only (color / spacing / type / density). Fast: touch the token or contract, re-render, look.
- **FUNCTION / DATA** — touches what data exists / how it's emitted / how the agent reasons. Full-stack: data → emit → render. Don't start at the render layer.

**Wobble check (before blaming data):** a rejected output is usually a loose-grammar problem. Before
re-running a pipeline, ask *does my grammar tell the agent what NOT to do here?* If not — tighten the
spec, then re-run. Burning pipeline cycles on a grammar gap IS the swamp.

---

## ③ Reference-template diff — concrete diagnosis ⭐

**Golden image per view → render current → diff → name the divergence.** Not a vibe, a named delta:
*"card padding 24px, spec says 16px."* The ① canonical examples ARE the golden templates (one
artifact, two jobs). Run the diff before reporting a problem and before starting a fix; a diff that
can't name what diverged isn't actionable. Update the baseline when the spec changes, not when the
render drifts.

---

## ④ Generation vs. implementation — tool selection ⭐

**External tool first (Stitch / Figma / v0)** when: greenfield · brand-heavy · non-coder / client
mockup · pure exploration / teaching.
**Direct-in-agent** when: existing system (tokens + grammar exist) · internal / data-facing view ·
solo operator (the default case).
**Hybrid:** explore externally → eject at ~70% fidelity → implement with the system always-on. The
70% is a sketch, not the deliverable.
**Critical rule: hand over the SYSTEM, never the generated code.** Generated code is throwaway (no
grammar, drifts on regen, teaches nothing durable). The system (tokens + contracts + examples) is the
durable artifact — when it's right, any new session converges fast.

---

## ⑤ Iteration discipline

**Iteration is the nature of design, not failure. Optimize for fast loops, not fewer loops.**
- **Look at the render every time.** The agent can't verify visual output by reading its own code. LOOK is the verification step.
- **75/25 split:** the system does ~75% of convergence automatically; the last 25% is grammar tightening + purpose refinement. Expecting 100% without tightening the grammar is iteration fatigue's root cause.
- **Alpha-user lens:** on rejecting an output, ask *"was my grammar too loose?"* before *"did the agent misunderstand?"* — it's almost always the grammar.
- **Loop cap:** ~3 iterations on one surface without finding the grammar gap → stop and tighten the spec.

---

## ⑥ Always-on lean delivery — the anchor

**The system is only effective if present every turn.** A compact always-on foundations block
re-injects each turn via the skill anchor; component contracts load on demand. **Keep it lean** —
bloat is not thoroughness; a bloated always-on block is an ignored one (~200-line threshold). When a
rule changes, update the anchor; never keep two versions — stale rules the agent confidently applies
are worse than no rules.

---

## Cross-cutting guardrail — tight ≠ exhaustive

**Over-specification is its own failure mode.** A stale 400-line grammar the agent applies with
confidence after a design change is actively harmful. The goal is leanness + currency + hierarchy,
not completeness. Every rule earns its place by preventing a real observed wobble; remove rules that
no longer reflect the system; never copy-paste spec sections "for completeness."

---

## Hard rules

- **Spec before output** — grammar is the source of truth; the render is evidence of whether the grammar is right.
- **Name the delta** — a diff that can't name what diverged is not a diagnosis.
- **System, not code** — the deliverable from any design session is the updated system, not the generated file.
- **Look at the render** — the builder never grades visual output by reading its own code.
- **Tighten the grammar, not the iteration** — the same drift on loop 3 = a missing rule, not more cycles.
- **Lean + current > comprehensive + stale** — always.

> **"Build the vocabulary, then the grammar, then prove it with examples — fed lean every turn.
> Iterate against the spec, not against vibes. The system is the deliverable."**
