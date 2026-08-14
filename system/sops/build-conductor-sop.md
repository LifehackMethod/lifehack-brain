---
id: system-playbook-build-conductor-sop
title: Build Conductor SOP — how to run an orchestrated / parallel build from one lead
record_type: playbook
created_at: 2026-06-22
updated_at: 2026-06-23
status: active
authority: user
---

# Build Conductor SOP

> The operating mode `project-manager` arms for any **build**: a lean coordinator at altitude
> that puts the work into the right **gear**, delegates decided work, keeps state in files, and
> stays out of the swamp. Promoted from the build-loop draft + proven live 2026-06-22 (Agent
> Teams + guard inheritance verified). Loaded by `/build` for an "orchestrated / parallel build."
> Companion: `build-sop.md` (execution do's). Routing: `build-rules-index.md`.

## Prime directive

**Stay at altitude. The work picks the gear, not the human. Lead from facts, not from the
user's in-the-moment mood.** The coordinator holds the design/taste/decisions and talks to the
human; it delegates everything buildable to fresh context; the rot stays in the workers, the
coordinator stays clean. State lives in files, not the model's head — so saves are rare and a
fresh window can resume from a brief + tracker.

## Starting a build window (the startup recipe — do this first)

1. **Launch normally** (the this system launcher / `claude`). No special launch for the default path.
2. **Invoke `project-manager` and name the build.** This arms the build-lead conductor anchor, which
   **re-injects every turn** and is the ONLY thing that keeps the window at altitude. Skip it → the
   window drifts into one project's weeds (the swamp). This step IS what makes it "the 10,000-ft window."
3. It now leads: delegates decided work to background sub-agents (gear 2), does coupled design with the
   user (gear 1), owns the merge.
4. **Decide gear-3-vs-not BEFORE launching.** Split-pane Agent-Team teammates (gear 3) require the window
   to be launched **inside tmux/iTerm2 from the start** — you CANNOT retrofit it onto a running window.
   For most parallel work, **background sub-agents (gear 2) are the better default** — no special launch,
   no tmux. Only do the tmux-from-launch dance if you specifically want to *watch* teammates in panes.
   **Gear 3 is opt-in** — arm it only when the user has said **"use agent teams" / "team build."**
5. **N parallel sub-projects from one window:** fire one background sub-agent per *decided* chunk (they
   run in parallel, report up); do the parts that need the user's eyes (design/look-react) directly with
   the coordinator, one at a time. The user talks to ONE window; it juggles the rest.

## Two altitudes — Observation Deck vs Build Lead (don't arm the wrong one)

There are **two distinct roles**, and conflating them is a primary failure mode (observed live
2026-06-22):

- **Build Lead** — runs ONE build. Operates the four gears below, delegates, owns the merge,
  holds that build's ground-level detail. Anchor: `skills/project-manager/ANCHOR.md`.
- **Observation Deck** — WATCHES builds to improve the SOP/systems; is **not part of any build**.
  Never advises a build's execution (cells, sub-agent prompts, curls, edits); only extracts the
  systemic lesson. Product = edits to this SOP, skills, hooks.
  *(Its per-turn anchor file, ⛔ `system/anchors/observation-deck-anchor.md`, is not shipped — it re-injects
  the mode's own reminder every turn, and nothing here arms it. The mode works read from this page.)*

**The trap:** arming the *Build Lead* anchor on a window whose real job is observation/coordination
pulls it straight into one build's weeds — it will start advising cells and curl commands and lose
altitude. **Match the anchor to the window's job.** A window in the wrong role is the swamp's entry
point.

## The four gears (the heart)

**The work's shape decides the gear. Don't pick a gear because it sounds impressive.**

| Gear | Fires when | What it is |
|---|---|---|
| **1 · Single-thread** | tightly-coupled **design** — shaping how a thing looks/feels, anything needing show-react-refine | you + the lead, one window. **Never split coupled design — it diverges.** |
| **2 · Sub-agent (fire-and-forget)** | a **decided, one-surface, self-verifiable** chunk | lead fires a background Agent (sonnet), it works in fresh context, returns a summary. The **workhorse.** No tmux, no panes, reports inline. |
| **3 · Agent-Team wave** *(opt-in)* | **multiple independent surfaces** that must **coordinate** (share a task list, talk to each other) — **AND the user has said "use agent teams" / "team build"** | lead spawns fresh teammates into a shared dependency-aware task list. The special-case tool — heavier (~7× tokens), fires only on explicit unlock. |
| **4 · Dynamic workflow** *(opt-in)* | **dozens-to-hundreds of independent items** (a 200-file sweep, a whole-folder audit) **OR** a **repeatable cross-checked quality pass** (adversarial-verify, judge-panel, research convergence) worth codifying as a rerunnable script — **AND the user has said `ultracode` / "use a workflow"** | lead writes a JS orchestration script the runtime runs in the background, fanning out up to ~16 concurrent / 1,000 total sub-agents. The orchestration logic is **code, not context** — only the final answer returns, so the lead's window stays clean. **Read-only / autonomous work ONLY** (a workflow cannot pause mid-run for sign-off). |

**Scope-by-coupling (the rule under the gears):** tightly-coupled write work diverges if split →
single-thread it. Read-only or independent-surface decided work → delegate (gear 2 or 3).
*(Cognition, "Don't Build Multi-Agents.")*

**Gear-3 Agent Teams is OPT-IN; gear-2 sub-agents are the automatic default.** *(Locked 2026-06-23.)*
The lead reaches for **gear-2 background sub-agents on its own** the moment work is decided and
self-contained — that is the default way to keep the main thread at altitude, **no trigger phrase
needed.** **Gear-3 (Agent-Team wave) fires ONLY when the user explicitly says "use agent teams" /
"team build"** — it costs ~7× tokens and spawns separate teammate windows, so it is a deliberate
unlock, never auto-selected. Until that phrase is said, decided parallel work fans out as gear-2
sub-agents and the lead owns the merge. **But once the user HAS said it, guide them fully INTO the
team — do NOT deflect back to sub-agents.** ⚠️ Observed failure (2026-06-22): the lead repeatedly
deflected to gear-2 when the user had asked for a team — steering toward the old fallback and away
from the capability that was the whole point, making the build feel pointless. **The opt-in is the
gate; once it's open, commit to the team.**

**Gear-4 Dynamic Workflows is OPT-IN; the unlock phrase is `ultracode` / "use a workflow".** *(Locked
2026-06-24.)* Same gate shape as gear-3: a workflow spawns a fleet (up to 1,000 agents/run) and can
cost meaningfully more than a chat pass, so it **never auto-fires** — but the lead **proactively
SUGGESTS it the moment it spots the shape**: a many-item sweep (≫ ~20 independent items) or a pass
that wants built-in cross-checking. *"This phase is a 180-file migration — want me to run it as a
workflow?"* Suggest, name the trigger, then wait. **This suggestion IS the "best tool for the job"
intelligence — the lead's job is to name the right gear, not to make the user guess it.** Once the
user says `ultracode` / "use a workflow," commit to the workflow (don't deflect back to a fan of
gear-2s — same deflection failure as gear-3).

## Choosing the gear — decision

1. Does the work need a human to look-and-react mid-task (design/taste), or sign-off before it can finish? → **gear 1.**
2. Is it decided, scoped to one surface, and self-verifiable? → **gear 2** (background sub-agent) — the default; reach for it on your own.
3. Are there several such surfaces that must coordinate / unblock each other? → **gear 3** (wave) **only if the user said "use agent teams" / "team build"**; otherwise fan them as gear-2 sub-agents and the lead owns the merge.
4. Is it **many independent items** (≫ ~20: a folder/codebase sweep, a bulk migration) **or a cross-checked pass worth scripting** (audit, research convergence)? → **suggest gear 4** (dynamic workflow); fire it **only if the user said `ultracode` / "use a workflow"**, and **only for read-only / autonomous work** (no mid-run sign-off possible). Otherwise fan as gear-2s.
5. Trivial one-liner? Just do it inline — dispatch overhead exceeds the work.

**A plan's gear tags are HINTS, not commands.** When you execute a plan whose tasks already carry gear
tags (e.g. from `/autoplan`), treat each as the planner's suggestion and **re-decide it here** from the
task's actual shape (coupled? decided? one-surface? self-verifiable?). The tag guides; the work decides.

## Running a gear-2 background sub-agent (the workhorse)

- One sub-agent = one surface / file-set. Independent surfaces run concurrently, zero collision.
- Give it a **clear done-criterion** and let it loop: execute → verify against ground truth → fix.
  Hard cap ~5 iterations, then surface.
- **Embed the context in the task** — it does not see the lead's chat.
- **sonnet, never opus** (haiku for pure read-only). Per this system subagent rule.
- Returns a summary / writes an artifact to a file. The lead reviews; the human approves.

## Running a gear-3 Agent-Team wave (the special case)

A gear-3 wave spawns fresh teammates into a shared, dependency-aware task list so several
independent surfaces that must coordinate can run together. **Opt-in only** — fires on "use agent
teams" / "team build" — and costs roughly **~7× the tokens** of a chat pass, so the sweet spot is
**~3 teammates**. **Embed context in each task** — teammates don't see the lead's chat — and **the
lead owns the merge**.

## Running a gear-4 dynamic workflow (the fleet)

A workflow is a **JS script the lead writes** that the runtime executes in the background, fanning
work out across many sub-agents. The plan lives in the script (loops, branching, intermediate
results) — so the lead's context holds only the final answer, not the per-item churn. Reach for it
over a fan of gear-2s when there are **too many items to coordinate by hand**, or when the value is
a **repeatable cross-checked quality pass** (not just "more agents").

**Three this system guardrails — non-negotiable (these make it ours, not generic):**
- **Sonnet-pin.** Workflow agents inherit the *session* model (opus) by default. Every `agent()`
  call MUST set `model: 'sonnet'` (haiku for pure read-only) — or it silently violates the global
  subagent rule and burns opus at fleet scale. This is the #1 thing to get right.
- **Read-only / no-mid-run-signoff.** A workflow **cannot pause for approval.** So gear 4 is for
  read-only / autonomous work only; anything that needs your sign-off, or any human-domain / Google
  **write**, stays gear-1 in the main session. Pattern: **workflow does the read-only legwork → lead
  surfaces it → human approves → write happens in the main loop.** For staged sign-off, run each
  stage as its own workflow (the docs' own escape hatch).
- **Opt-in.** Fires only on `ultracode` / "use a workflow" (see decision step 4).

**Operating rules:** **plan-first** (Phase→Feature→Task, reviewed, before scripting); **prefer
`pipeline()`** (each item flows through all stages independently, no barrier) over `parallel()`
(barrier — only when a stage genuinely needs ALL prior results, e.g. dedup); **schema-force
structured output** (`agent(..., {schema})`) so results come back as validated objects, not prose to
re-parse; **bake in a quality pattern** when it earns it — adversarial-verify (independent agents try
to *refute* each finding) or judge-panel (draft N angles, score, synthesize); **prove on a slice
first** (one directory before the whole repo) to gauge token cost; watch + manage the run from
`/workflows`. Note: this system PreToolUse guards still fire inside workflow agents — but nobody can
answer a mid-run prompt, so a guarded *write* just stalls. Another reason gear 4 stays read-only.

**Worked example — system audit as a workflow (the canonical gear-4 use):** the strongest this system
fit, and zero-risk because nothing writes. Mirrors what the `archivist`/`sentinel` agents do, scaled
out: one read-only agent per content folder (`canon/`, `records/`, `state/`, each desk) detecting
drift / missing files / topic-vocab violations / sync mismatches, each pinned to sonnet and returning
a structured findings object, then a synthesis stage that dedupes and ranks. `pipeline()` over the
folder list; a final agent flags what's missing. Output is a proposal the human acts on — never an
auto-fix. (This doubles as the proof-run for the whole capability.)

## The large-build flow (gear 3, or a fan of gear-2s)

1. **Plan-first** — a cheap Phase→Feature→Task plan, reviewed, BEFORE spawning anything.
2. **Decompose by surface** — split the work into independent file-sets/lanes.
3. **Lock the data contracts BEFORE parallel writes** — the #1 regret of parallel builds is
   skipping this. Agree the shape each lane reads/emits first.
4. **Fan out** — gear-2 sub-agents for independent decided lanes; a gear-3 wave only if they must
   coordinate.
5. **The merge gate (the lead owns it; a first-class step):** integrate **sequentially,
   foundational-first** (data → logic → render); **diff-review each branch before it lands**;
   optionally a reviewer sub-agent (~1 per 3–4 builders); **never trust a "done" mark.**
6. **Worktrees only when two workers must edit the SAME file** — give each its own `git worktree`
   + its own port (Helm's `:8080` collides; offset). The `isolation:worktree` param is buggy for
   teams → wire manually. Worktrees carry real tax; not the default.

## The worker loop (depth)

execute → **verify against ground truth** (run it / render it / read the real output — NOT the
code, NOT a self-report) → fix → repeat. ~5-iteration cap, then surface. **Writer ≠ verifier** — a
separate check or the human confirms "done." **Fresh context per cycle** — context rot sets in
~20–30 turns; reset before that; state lives in files.

## Parallel-by-default + cost

- **Throw independent work to background agents the moment it's delegatable** — never do serially
  what can run in parallel. Keep the lead free at altitude.
- But parallelism has a tax (coordination, tokens, review bandwidth). The real bottleneck is
  **human review**, so cap concurrent builders at **~3** and don't fan out past what you can merge.

## Coordinator discipline — LEAD (read the case study below)

- **The coordinator leads from research/facts, not from the user's momentary frustration.** A
  user's "this is confusing / I don't like this" is a **symptom to diagnose**, not a strategy order.
- **Separate "the user can't drive the tool yet" from "the tool is wrong."** The first is a
  30-second teach; the second is an architecture change. Don't confuse them.
- **When uncertain, `/research` — don't push the decision onto the user.** Ending turns with
  "which do you prefer?" on a settled technical call is the drift tell.
- **An operational hiccup is NOT grounds to re-open a settled architectural decision.**
  Prove-before-bake also means **don't un-bake on a vibe.**
- **Keep the mission centered.** A side-quest that swallows the thread = context-rot + drift = the
  swamp. If a turn isn't moving the mission, stop and re-center at the 10,000-ft view.

### Case study — a session losing its thread (2026-06-22, this build)
**Mission:** prove + bake Build Conductor. **Side-quest:** a tmux scroll-wheel UX hiccup (a
30-second fix). **Failure:** the coordinator read the user's momentary confusion as a strategic
signal and flip-flopped — "use Agent Teams in tmux" → "abandon tmux, demote Agent Teams, use
sub-agents instead" — over an *operational detail*, re-litigating a settled architectural decision
and following the user's cues instead of leading from the research (which never said tmux was
unusable). **Tell:** repeatedly ending turns with "which do you prefer?" **Fix:** lead from facts;
diagnose the UX problem (it was real and small); keep the settled decision; re-center on the build.

## Hard rules

- **Only real data** — never fabricate/extrapolate to fill a gap; absent data renders honestly empty.
- **Obey literally** — build exactly what was decided; a downside gets one line, then build as asked;
  never substitute a "cleverer" version.
- **Verify by running/rendering and looking** — the builder never grades itself.
- **Design ends at the approved spec; build executes it** — don't let design re-open locked decisions.
- **Subagents/teammates/workflow agents = sonnet, never opus** (workflow `agent()` calls default to
  the opus session model — pin `model: 'sonnet'` explicitly on every one).
- **Workflows (gear 4) are read-only / autonomous only** — they can't pause for sign-off, so every
  human-domain or Google write stays in the main session.

## When NOT to delegate

- Active design iteration (show-react-refine) — a headless worker can't hold up its end → gear 1.
- Trivial one-liners — dispatch overhead exceeds the work → inline.
- Anything that needs a human mid-task (approval before it can finish) → keep it in the lead loop.

> **"Stay at altitude in one window, put the work in its right gear, fan decided work out to
> isolated workers that loop-until-verified, own the merge from the top, keep state in files — and
> lead from facts, never from the swamp."**
