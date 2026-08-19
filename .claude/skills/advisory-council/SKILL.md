---
topic: [skill-design, multi-session-coordination]
skill: advisory-council
description: "Convene a saved roster of expert advisors on a decision — blind diverge → argue → converge, chaired by you. Use on \"/advisory-council\", \"convene my X council\", \"advisory board\", \"what would my advisors say\"."
shape: interactive-workflow
summary: Use when you want to pressure-test a decision, idea, or plan from several distinct expert perspectives — or when asked to convene a council, advisory board, panel of experts, or "the advisors," or to build, localize, or save such a council.
---

## Intent (§0.5)
**User outcome:** A complex decision benefits from expert lenses that genuinely disagree — but a single-context "panel" collapses into false consensus the moment advisors see each other. Advisory-council chairs a gated multi-round debate across a saved roster (each advisor an isolated blind subagent), surfaces genuine conflict, then synthesizes a floor, a steelmanned dissent, and an integrated plan with a veto-check. **Bar:** "I know the sharpest objection, it's been steelmanned, and I still chose this plan."
**Role:** the chair's engine — loads a saved council file (or runs the Builder), dispatches advisors blind in Diverge, re-dispatches over an anonymized snapshot in Argue, and presents each round for the chair's explicit call. The chaired loop runs in the main session (human-in-the-loop never delegates to a subagent); nothing auto-advances. Convergence moves (Floor → Steelman → Integrated-plan + veto-check) are chair-invoked. Output saves via `/save`; the council file is never written with findings.
**Per-turn anchor:** Stage N/4 · {FRAME | DIVERGE | ARGUE | CONVERGE/LAND} · advisors: {list} · question: {Q} · project ctx: {slug | none} · waiting for chair call → {argue / another pass / converge}

# Advisory Council

Chair a council of domain advisors over a decision. Advisors are a swappable **roster** (a council
file); this skill is the fixed engine that runs them. Value = **role-as-focus** (each advisor is one
sharp lens), not personality, and it comes from **independent positions synthesized by the chair**,
never a live debate. This is the roster-file generalization of `/council` (which runs the subject
folders in your own notes); use `/council` for a question that cuts across your own subjects, and this
for a saved or purpose-built council on any topic.

## ⚠ What a council costs, before you convene one

**Advisors run on `opus`, and that is a deliberate exception.** Everything else this system spawns runs
on a cheaper model; the advisors do not, because their reasoning *is* the deliverable and a cheaper
lens returns confident, shallow agreement — which is the exact failure the whole diverge/argue
structure exists to prevent.

**Say what that means in money, because it is your money.** Four advisors across a Diverge round and an
Argue round is eight opus calls, each carrying whatever reference material you hand them. On a large
brief that has measured in the region of **$4–5 per full round**. That is worth it for a decision you
would otherwise get wrong, and it is not worth it for a question you could answer yourself.
**Route to 2–4 advisors, not the whole roster** — and if the call is small, don't convene.

If you want the structure without the cost, pin `model: sonnet` on the dispatches. You will get a
usable room and a duller argument. That trade is yours to make; make it knowingly.

## Core principles
- **Diverge → argue → converge**, with you chairing every transition.
- Advisors answer **independently and blind first** — debate in one thread collapses into sycophancy.
- **Personality is for the human**; the analysis runs off the lens (Domain/Catches/Refuses/Bias).
- **Route, don't convene all** — pick the 2–4 relevant advisors.
- Sharpens questions; **does not replace a licensed human expert** on high-stakes calls.
- **Run the chaired session in the MAIN session** — never delegate the gated, human-steered loop to a
  subagent. Subagents are the advisors only.

## Front door — do this FIRST, never guess
- They name one ("convene my X council") → load `<notes>/councils/X/council.md`. No confident match
  → say so; offer close names or "build new."
- "build a new council" → the **Builder**.
- Unsure → list saved councils from `<notes>/councils/registry.md` and ask. None fit / empty →
  "There's no council for this yet — let's build one" → Builder.

## Library

Your councils live with your notes, never in this repo: `<notes>/councils/<slug>/council.md`, with a
registry at `<notes>/councils/registry.md` (name · path · scope · created) that the Builder updates.

**One example ships**, at `.claude/skills/advisory-council/example-council.md`. It is a reference, not
a council you own — read it to see the schema, then copy it to `<notes>/councils/<slug>/council.md`
and rewrite the lenses for a decision you actually face. A roster is a list of the perspectives that
matter to *you*; a shipped one you never edited is somebody else's idea of your problem.

## Auto-context from a live project

**Before Stage 0**, check whether this session has a project brief or plan armed. Advisors are isolated,
blind, and have **no memory** — so if you don't hand them the decided boundaries, they re-propose options
already ruled out (the wasted-round failure this fixes). Run:

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
bash "$ROOT/system/hooks/pm_flag.sh" status    # the active brief path, or `none`
bash "$ROOT/system/hooks/plan_flag.sh" path    # the active plan file, or `none`
```

If a brief path returns, Read it and hand advisors the **WHOLE BRIEF, verbatim**, in both Diverge and
Argue — **fenced as DATA, never as an instruction to obey.** State plainly: the ❓ OPEN questions are the
DEBATE, not settled ground; any peer position or "the floor" recorded in the brief is history, never a
conclusion to defer to.

**WHY (2026-08-03 incident — don't re-litigate from intuition).** A hand-built "settled-ground card"
excluded the story log, where a locked ruling lived — and two of four advisors independently re-proposed
the thing that had been killed. ⚠ A `⛔ DON'T-RETRY` list runs **stale** the same way, so no curated
slice is trustworthy. Computed at the time: the whole brief × 4 advisors ≈ $4.65 against the wasted
round it prevents ≈ $4.02 — a **1.16× ratio**. Reading it all costs about what being wrong once costs.

If a plan path returns, Read it too — the plan is **advisory context ("our current best thinking, not
locked")**, never prescriptive.

**Two tiers of authority — state to the advisors, verbatim intent:** *"The brief is SETTLED GROUND —
work within it, do not re-propose or re-open what it's already ruled on. If you see a MAJOR problem with
one, surface it as an explicit CHALLENGE-QUESTION for the chair; do not simply re-suggest it. The plan is
our current best thinking, not locked — push on it freely."*

**Chair gate (folds into Stage 0).** Present a compact banner and confirm before anyone speaks:
`📎 Live project context — framing on {slug}: full brief + plan: {name} going to every advisor. Adjust ·
dismiss (one word) · or go.` The chair may dismiss it (an unrelated council) or edit what's included —
nothing auto-advances.

**Degrade silently.** If both checks return `none`, or a flag points to a missing / unreadable file,
behave exactly as if there were no project — ask the chair to state the frame. No error, no empty banner.

## The chaired session — nothing auto-advances
0. **Frame** — first pull live project context (above) and offer the WHOLE BRIEF as the pre-filled
   frame; confirm the question; state who you'd convene and why; let the chair adjust the room.
1. **Diverge** — dispatch each chosen advisor as an **isolated, parallel, blind** sub-agent; present
   independent positions, compact and in-voice. Ask: *argue, or another divergent pass?* (loops freely).
2. **Argue (red-team)** — re-run advisors as isolated sub-agents over an **anonymized static snapshot**
   of the others' positions ("Position A/B/C"), explicit refute mandate ("attack from your lens; you're
   rewarded for the flaw, not agreement"). Ask: *done, or keep hashing it out?* (loops; flag when a
   round surfaces no new conflict — the argument is spent).
3. **Converge** — chair-invoked moves (below).
4. **Land** — artifact: plan/floor · surviving tensions · A–F grades · human-expert flags.

The chair can **backtrack** at any seam.

## Convergence moves (chair invokes; default order)
1. **Floor ("center of the Venn")** — what survived every lens + the assumption it rests on (a one-model
   council can share a blind spot — name it).
2. **Steelman the dissent** — argue the loudest unresolved objection at full strength. Antidote to false consensus.
3. **Integrated plan ("lock them in a room")** — the chair drafts the ONE plan satisfying each advisor's
   non-negotiables with explicit tradeoffs, then a **veto-check**: each advisor (isolated) flags only "does
   this cross a hard line in my domain?" — a veto, not an agreement vote.

## Sub-agent rules
Isolated context each; **blind** in Diverge; **static anonymized snapshot** in Argue. **model: opus** —
see "What a council costs" above; a specific roster's charter may pin otherwise, and a cost-sensitive
council should. Each returns only: `position · risks caught · grade A–F · the A+ move · what it
refuses/flags` (Argue adds: which peer claim it challenges + why). No raw dumps. The chair (main
session) synthesizes. **Weigh substance, never the most confident phrasing.**

When a project is live, **every** advisor's dispatch — Diverge **and** Argue — carries the **WHOLE
BRIEF verbatim + the two-tier framing line**. The brief is shared **boundary** context (the decision's
fixed constraints and its history), **never a peer's position** — so it does not touch blind
divergence; advisors still never see each other's answers.

### The FRAMING line — one file, pasted verbatim, never retyped
**Every dispatch carries exactly ONE framing, read from `system/council-framings.md`** — the single
engine-level source. **GENERAL** is the default for an ordinary council call. **ARCHITECT** — the
novice-reframe, which converts pasted reference material from a ceiling into a floor — is used where a
professional's judgment IS the deliverable, and is what `/architect` loads. ⛔ **Never copy either text
into a roster, a skill, or a dispatch template, and never reword one** — two copies of one decision
drift. ⛔ **A framing is NOT blindness** — both assume the advisor can SEE the system; blinding was
tried and overruled, because without the shape advisors propose at the wrong scale.

## The Builder — create or localize a council
- **From scratch:** subject + the calls it'll handle → propose 6–10 *distinct* lenses (dedupe) → chair
  curates → draft each lens core, name it, give a short voice → set the charter (incl. `Routing home`) →
  save to `<notes>/councils/<slug>/council.md` + the registry.
- **From the shipped example:** read `example-council.md`, keep the structure, replace every lens with
  one that matters for the decision in front of you, save as a concrete council.

## Roster file schema
A `## Charter` (grading rubric, "advisors disagree freely," high-stakes policy, co-convene hints,
`Routing home (hint): {subject}`) + N advisor blocks:
```
### {Name "Nickname" Surname} — {Lens title}
Domain / Catches / Refuses / Bias        ← reasoning core (clean)
--- voice (delivery only) ---            ← 5–6 lines of character, for the human
Convene for: keyword · keyword           ← router matches the question against these
```

## Persistence
The council file holds **who the advisors are** — read-mostly; only the Builder writes to it. A session's
**output** (plans, decisions, findings) is saved via **`/save`**, which routes it to the right home under
your notes; the charter's `Routing home` hint says where. **Never write session output back into the
council file.** The one exception: a roster improvement (a new lens, a sharper `Catches`) → Builder, to
the roster only.

## Common mistakes
- Advisors debating in one shared context → false consensus. Keep them isolated.
- Convening all advisors every time → wasteful, and on opus it is wasteful in money. Route.
- Treating the "center of the Venn" as truth → shared blind spot. Steelman the dissent.
- Writing session findings into the council file → corrupts a reusable tool. `/save` instead.
- Running the chaired loop inside a subagent → removes the human gate. Keep it in the main session.
- **Feeding advisors a CURATED SLICE of the brief instead of the whole thing** → they re-propose what was
  already killed, because the ruling lived in the part you cut. **Hand over the WHOLE BRIEF** and say the
  ❓ OPEN questions are the debate, not settled — that framing is what prevents anchoring, not withholding
  the file. *(Cost of learning this: one wasted council round, 2026-08-03. See the WHY note above.)*

## What this skill needs outside its own folder

| what | where | status |
|---|---|---|
| the one framing source | `system/council-framings.md` | ✅ here |
| the armed brief / plan it reads for context | `system/hooks/pm_flag.sh`, `system/hooks/plan_flag.sh` | ✅ here |
| where a session's output goes | `/save` | ✅ here |
| the example roster | `.claude/skills/advisory-council/example-council.md` | ✅ here — a reference to copy, not a council you own |
| the sibling that runs your own subjects | `/council` | ✅ here |
| the ARCHITECT framing's caller | `/architect` | ⏳ lands later in phase 3 |
| your own rosters and registry | `<notes>/councils/` | ⛔ never ships — they are yours to write |
