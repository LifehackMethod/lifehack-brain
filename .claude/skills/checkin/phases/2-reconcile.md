# Phase 2 — reconcile (steps 2 → 3)

Compare the horizons, mine what contradicts nothing, and put a tight orientation block on screen.

---

## Step 2 — Reconcile three horizons

**This runs every time, in full.** There is no mode to pick and nothing to detect — a self-assessed
mode switch is the same unreliable gradient as a self-assessed depth ladder, and it fails the same way.
When there is nothing to reconcile it costs one line; that is the whole price.

Compare:

- **GOAL** — the desired outcome. Stable. Where we are trying to land.
- **BRIEF** — the last-saved state: current state, the decision board, open loops, key resources.
  Possibly stale; only as fresh as the last save.
- **SESSION** — what has actually happened this session. Live, in context, includes the pad. May be
  ahead of the notes.

The linked **PLAN** is a fourth object these three get checked against.

Name the deltas: what has been done since the last save? Which plan steps are now stale — done,
obsolete, or overtaken? What dead ends were hit this session that are not in the brief yet?

### The filter, and what each pairing means

**A tension counts ONLY when acting on one source would mean doing DIFFERENT WORK than acting on
another.** Not *"these say different things"* — ***"these point somewhere different."*** Without that
bar you flag everything, they stop reading, and a real tension gets buried under ten trivial ones —
which is worse than not checking at all.

| pairing | what it means | what you do |
|---|---|---|
| **GOAL ↔ PLAN** | the plan has drifted from what we are aiming at — scope creep, or it was built for an older goal | draft the concrete fix and propose it |
| **GOAL ↔ SESSION** | what we **learned** threatens the goal itself | **always surface it; never resolve it yourself.** The frame is observe-and-flag only |
| **SESSION ↔ PLAN** | the plan is stale on facts | the most common and least interesting — repair it and say you did |
| **BRIEF ↔ BRIEF/SESSION** | the brief contradicting itself: a ✅ LOCKED item a ⛔ RULED-OUT line contradicts · a number corrected in one section and stale in another · an open loop the story log says is closed · a key resource pointing at a file that moved · anything current state asserts that the story log's supersession chain contradicts | draft the fix into current state, the board, open loops or key resources, and propose it. **Never** into the story log or a ruled-out line |

> ⚠ **GUARDRAIL — the story log and the ⛔ RULED-OUT bucket are SOURCES for that last pairing, never
> TARGETS.** The story log is append-only and **deliberately contains wrong turns and killed ideas —
> that is its job.** Read from its supersession chain to *detect* a tension; the *fix* always lands
> elsewhere. The only in-place change ever permitted on a story-log entry is a `superseded-by` tag.
> Never rewrite an entry's content, and never delete a ruled-out line.

**Prefer SESSION; do not rule by it.** The session goes stale too, and it holds ideas that were
*explored* alongside ones that were *adopted* — a hard "newest wins" rule would let something rejected
override something settled. So say which version you believe is current **and why it is more current**:
a date, a commit it cites, a check that was actually run. Never a bare assertion that one looks fresher.

**Nothing in tension → say so in one line** — *"goal, brief, plan and session agree; no tensions."*

> **The failure this exists to catch.** A plan's phase header carried no ✅ and no ✗, and the brief's
> current state listed the other phases complete and simply omitted it. **Neither surface *said* it was
> done — they just never said it wasn't.** Five sessions read past it and one nearly built the next
> phase on top. The scratchpad had it right the whole time. **Nothing was comparing them.**

## Step 2.5 — Mine the session

Step 2 surfaces **tensions**. **Most sharpening contradicts nothing** — the plan simply never mentioned
it — so a tension-only filter never sees it, finds no stale steps, and reports *"plan current, no
changes."* Truthful, and the plan dulls anyway. **This step exists to catch exactly that gap.**

Scan this session — free, the material is already in context — for four things:

1. **A measured number, and what it replaced.**
2. **A claim disproved**, including one of your own.
3. **An approach ruled out**, and why.
4. **A correction they made** to your read of the system.

**Routing is hard.** Every finding goes explicitly into one of three places: the plan's context, a
**task**, or **deferred as a dead end**. A finding that gets mentioned and not routed is
indistinguishable, three sessions later, from never having been found — and that gap is the exact
failure this step exists to prevent.

Nothing surfaced → say so in one line: *"session mined, nothing to route."*

## Step 3 — The orientation block

Scannable, not a wall:

- **Desired outcome** — one line. The anchor.
- **Where we are** — current state, reconciled with this session.
- **Don't re-try** — the relevant dead ends.
- **Stale in the plan** — steps that no longer apply.
- **Scope for today** — the smallest viable next moves toward the outcome, cheapest-first.

If the frame itself looks like it is going stale, **say so here as an observation.** Do not draft a
rewrite of it, not even as a proposal.
