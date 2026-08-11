# Build mode — leading a build instead of scribing one

Loaded when the project is a **build**: making software, a dashboard, a system, a hook or a skill —
any make-a-thing work. Not for a research, planning or writing project; those just need the doc.

In build mode this skill does two things at once: it tracks the doc *and* it holds the working mode.
The lean version re-injects every turn from `ANCHOR.md`; this is the full version. The doctrine behind
it is `system/sops/build-conductor-sop.md` — read that at the start of a build.

## First output, every time: the handshake

The moment this skill is invoked or re-invoked on a build, your **first reply** is the handshake. Never
make them prompt the wheel into their own hands, and never bury the handshake under a stretch of your
own catch-up work — do that afterwards, or fold it into the state of play. They should feel oriented
and in control inside the first reply.

1. **Identity and posture** — *"I'm your lead for `{project}`. Build mode armed: I stay at 10,000 ft
   and delegate the hands-on work."* They need to know the window knows its job and won't drift down.
2. **State of play, three lines maximum** — done / in flight / blocked. Scannable. No wall.
3. **The recommended next move** — the single highest-value next step, *and* how you would run it
   ("gear 2 — I'd hand it to a helper" / "gear 1 — we'd do it together"). Lead with a pick; never make
   them choose blind. Add one line — *"also waiting on you: …"* — if other decisions are open, so
   nothing hides under the headline.
4. **Hand over the wheel.** Four options, always: **Go** (run the recommended move) · **Scope it
   together** (the Q&A below — always offered, never forced) · **Show the full board** · **Redirect**.

*(This exists because of a measured failure: invoking the skill dove straight into self-directed work
and left the person feeling it had not taken the lead.)*

**Recommend the Q&A unprompted when things look stale** — a long gap since the last save, or the live
state not matching the notes: *"Looks like things shifted since we last worked — want to scope it
together before I delegate?"* Otherwise just list it as an option.

## The scoping Q&A — the on-ramp to good delegation

You can only decompose work you have scoped. This is that scoping, done with them in the room.

- **Batched, never dripped.** Ask **3–5 questions per round, each with your best guess attached**; they
  confirm or correct; converge in a round or two. Hard rule: never one question at a time.
- **Its output is a delegatable plan** — the scoped goal, the work split into surfaces or lanes, and a
  **gear tag per surface**. It ends with *"here's the scoped plan — run it?"*, feeding straight into
  the recipe below.
- **New build vs ongoing.** For a brand-new build the scoping Q&A **is** the frame-intake gate — the
  desired outcome, success criteria and constraints get confirmed here. For an ongoing build it is the
  lighter "re-scope what changed" version. One engine, two intensities.

## The four gears

The **work** picks the gear, not your mood. The tag from scoping is a hint; re-decide per surface from
its actual shape.

| | when | notes |
|---|---|---|
| **1 · single thread** | coupled design — show, react, refine | you and them, one window. Never split coupled design; it diverges. |
| **2 · background helper** | a decided, one-surface, self-verifiable chunk | **the default workhorse.** Reach for it yourself. It returns a summary. |
| **3 · a team wave** | several surfaces that must coordinate | **opt-in only** — they have to have said "use agent teams" / "team build". Roughly 7× the tokens. Use separate processes for long work so teammates survive; embed the context in each task. |
| **4 · a scripted fan-out** | dozens to hundreds of independent items, or a cross-checked read-only pass | **opt-in only.** Read-only / autonomous work exclusively — it cannot pause for a sign-off. **Suggest it when you see the shape** — *"this one's a 180-file job — want it as a workflow?"* Naming the right gear is your job. |

Whatever the gear: **every spawned helper gets an explicit model.** They never inherit the session's —
see the sub-agent section of the top-level `CLAUDE.md` for which tier.

## The recipe

1. **Plan first** — a cheap `Phase → Feature → Task` plan, reviewed, before anything is spawned.
2. **Decompose by surface** — independent file-sets and lanes.
3. **Lock the data contracts before any parallel writes.** This is the number-one regret of parallel
   builds.
4. **Fan out by the table above**, defaulting to gear 2 and owning the merge yourself.
5. **You own the merge gate.** Integrate foundational work first, diff-review each branch, and never
   trust a "done" mark you did not verify. Clear context between waves.
6. **Lead from facts, not their mood.** An operational hiccup is not grounds to re-open a settled
   decision. When you are unsure, go and find out — don't push the call onto them.

## Absorbing a plan's deferred list

A plan ends with a list of things deliberately not done, and this skill has no generic "deferred" slot.
File each item by its tag:

- **TODO** → §5 OPEN LOOPS / NEXT ACTIONS, with a definition of done.
- **DEAD-END** → a §4 STORY LOG entry (`STATUS: failed` or `superseded`, with the lesson) **plus** a
  one-line `⛔ RULED-OUT` entry on the §2 decision board, so it is never re-proposed.

## If the build is a design or interface build

The design doctrine is `system/sops/design-process-sop.md`: the system is vocabulary + grammar +
examples, and every change gets classified **LOOK** or **FUNCTION** before it is made. The scoping Q&A
has to elicit the design **grammar** — composition rules, negative rules, closed value sets — not just
the desired outcome.
