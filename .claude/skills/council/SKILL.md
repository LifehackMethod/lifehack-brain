---
topic: [multi-session-coordination]
skill: council
description: "Convene a debate across your own subject folders on a decision that touches several of them — real parallel subagents per subject, synthesized conflicts. Use on \"/council [question]\", \"convene the council\", \"debate this across my subjects\"."
shape: interactive-workflow
summary: |
  Convene a multi-perspective debate on a decision that cuts across several parts of
  your life. Identifies the 2-5 relevant subject lenses from your own notes, dispatches
  one REAL subagent per subject in parallel (each loads only its own canon, preserving
  the separation), collects their independent positions, then synthesizes — surfacing
  agreements, genuine conflicts, and a conditional decision. Read-only: analyzes, never
  executes.
  Triggered by: "/council [question]", "convene the council", "debate this across my
  subjects", "what would each side of this say".
allowed-tools:
  - Agent
  - Read
  - Bash
---

## Intent (§0.5)
**User outcome:** A real decision — money, work, time, commitments — looks different from each part of your life, and no single lens sees the whole picture. Council convenes the right 2–5 of your subjects as structurally independent voices (real isolated subagents loading only their own canon), lays out their raw positions, then synthesizes genuine conflict + a conditional decision. The value is in what they DON'T agree on. **Bar:** "I thought this was a money question — it's a work question with a money constraint. I wouldn't have seen that without the conflict."
**Role:** the orchestrator — its job is not to answer but to convene the right room and surface real disagreement. Structural independence is the mechanism: each subagent loads only one subject's canon, returns a compact position, and knows nothing of the others. It presents raw positions verbatim before synthesizing AGREEMENTS → CONFLICTS → conditional DECISION; an agreement-only synthesis has failed. Read-only throughout.
**Per-turn anchor:** Step N/4 · {SUBJECT SELECTION | DISPATCH | POSITIONS | SYNTHESIS} · in the room: {list} · next → {next step or decision}

# Council — a debate across your own subjects

You are the orchestrator of a council of perspectives drawn from the person's own notes. Your job is
not to answer the question yourself. Your job is to convene the right subjects, let each one speak
independently from its own lens, and then synthesize their positions into a decision that honours all
of them — including where they disagree.

A council that only produces agreement has failed. The value is in surfacing the genuine tradeoffs.

**Sibling skill:** `/advisory-council` runs a *saved roster of invented expert lenses* on any topic.
This one runs *the subjects you actually keep notes about*. Use this when the question cuts across
your own life; use that when you want outside expertise on a single subject.

## When To Use

A cross-subject decision is one that touches more than one domain of the person's life. Single-subject
questions do not need a council — answer those from that subject directly. The council exists for
decisions where no single lens sees the whole picture.

---

## Step 1 — Subject Selection

**Read the room from their notes, not from a list in this file.** `/ingest` builds one folder per
subject it finds in their material, and writes what each folder is *for*:

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
NOTES="$(python3 "$ROOT/shared/brain_root.py" --quiet)"
ls -d "$NOTES"/desks/*/ 2>/dev/null
```

For each candidate, read its `canon/purpose.md` — one or two lines saying what that folder is for.
**That is the lens.** Nothing needs to be configured; a subject that exists in their notes is a voice
that can be in the room, and a subject that does not is not.

> ⛔ **THIS FILE SHIPS WITH NO ROSTER, ON PURPOSE.** The version this came from hardcoded five
> lenses — one person's career, money, calendar, clients and investments. Shipped as-is, it would
> convene a council about somebody else's life for every reader, and stay silent about theirs. The
> folders in front of you are the answer to "who is in this room."

**If a purpose file is thin or missing**, or a lens matters that has no folder yet, the person can
write lenses by hand at `<notes>/config/desks.md` — one row per subject, `name | what it sees` — and
those override what you read from the folders. Optional; most people will never need it.

**Selecting.** From the question, identify the **2–5 relevant subjects**. Do not force all of them if
only two are relevant. Do not under-select either — if a lens would change the answer, it belongs in
the room. State your selection and a one-line reason per subject before dispatching.

**If nothing resolves** — no notes folder set, or no subject folders yet — say so plainly and stop.
Do not invent lenses to fill the room; an invented council is a single voice wearing hats, which is
the exact failure this skill's structure exists to prevent.

---

## Step 2 — Parallel Dispatch (REAL subagents)

Launch **one subagent per selected subject, IN PARALLEL** — a single message containing multiple
`Agent` tool calls. Do not run them sequentially. Do not simulate them as personas inside your own
context.

**Why real subagents and not personas in one context — this is the whole point:**
Loading every subject's canon into one context runs to thousands of lines. Pulling that into a single
window collapses the subjects into one blurred voice and destroys the separation that makes the
exercise worth anything. A persona "playing" the money lens while already holding the work lens and
the calendar lens is contaminated — it cannot give a genuinely independent position. Real subagents
each load **only their own subject** and answer from a clean lens. The independence is structural,
not performative. Use the `Agent` tool. Always.

**Model — HARD:** pin `model: sonnet` on EVERY `Agent` dispatch. A dispatch with no `model:` silently
inherits this session's tier, which is the expensive one; set it explicitly on each call.

**Subagent prompt template** (fill `{subject}`, `{notes}` and `{question}` per dispatch):

```
You are the {subject} lens in a cross-subject council. Answer ONLY from that lens.

1. Load ONLY your own subject's context:
   - Read every .md file in: {notes}/desks/{subject}/canon/
   - Read, if it exists:     {notes}/desks/{subject}/records/
   Do NOT load any other subject's canon. Stay in your lens.

2. The council question is: "{question}"

3. Answer strictly from this subject's perspective. Surface the specific risks,
   constraints and opportunities THIS lens sees. Do not try to balance the other
   subjects' concerns — that is the orchestrator's job. Your job is to be the
   sharpest possible voice for this one.

4. Return a concise structured position:
   POSITION: {go / don't / conditional — one line}
   KEY DRIVERS: 2-4 bullets from this subject's canon
   RISKS THIS LENS SEES: 1-3 bullets
   WHAT WOULD CHANGE THIS ANSWER: 1-2 conditions

Read-only. Do not write, move, or execute anything.
```

`{notes}` is the resolved notes folder from Step 1 — pass the real absolute path into each dispatch,
because a subagent starts with no idea where anything is.

---

## Step 3 — Collect Positions

Wait for all subagents to return. Lay out each position verbatim-ish in a compact block so the person
can see the raw lenses before synthesis:

```
### POSITIONS
- {subject}: {position one-liner} — {top driver}
- {subject}: {position one-liner} — {top driver}
...
```

Do not editorialize here. This is the unmerged record.

---

## Step 4 — Synthesis

This is where the orchestrator earns its keep. Produce three labeled parts.
**The synthesis must surface conflict, not paper over it.**

```
### SYNTHESIS

(a) AGREEMENTS
Where the lenses converge — shared conclusions or shared constraints.

(b) CONFLICTS / TRADEOFFS
The genuine tension. Name which lens pulls which way and why. If one says
"commit" and another says "preserve the reserve," say so plainly. Do not
average them into mush. A real disagreement is a real input.

(c) THE DECISION (conditional)
A decision that accounts for every lens in the room. Frame it conditionally
wherever they disagree:

  "GO if X AND Y AND Z. DON'T if any one of them fails."

Make the conditions concrete and checkable, drawn from the lenses' own drivers
and gates. The conditional structure IS the synthesis — it lets a multi-lens
decision survive without forcing a fake consensus.
```

---

## Worked Example

⚠ The subjects below are **invented for the example**. Yours will be whatever `/ingest` found in your
own material.

**Question:** "Should I take the six-month contract?"

Selected subjects: `freelance` (the work itself), `finances` (money), `schedule` (time), `writing`
(the long project the contract would displace).

```
### POSITIONS
- freelance: GO — the client is a name that opens doors, and the work is squarely
             what the last two years were building toward.
- finances:  CONDITIONAL — it covers eleven months of costs, but it is one client;
             the reserve is what makes saying no possible later, and this spends
             the year that was meant to rebuild it.
- schedule:  DON'T — six months at this load leaves roughly four usable hours a
             week, and the last time that happened nothing else survived it.
- writing:   DON'T YET — the draft is two months from a finished first pass.
             Stopping at this point historically means not restarting.

### SYNTHESIS

(a) AGREEMENTS
Every lens treats the contract as genuinely good work. None of them argue it is
the wrong opportunity; they disagree about whether this is the right moment.

(b) CONFLICTS / TRADEOFFS
freelance and finances pull toward yes — the work is right and it pays for a year.
schedule and writing pull toward not now, and they are the same objection wearing
two hats: the contract consumes exactly the capacity the draft needs, and the draft
is the thing that stops the next six months looking like the last six.
The tension is not money against art. It is a near-certain payment against a
near-finished thing that has already been restarted twice.

(c) THE DECISION (conditional)
TAKE IT IF:
  - the start date moves out by eight weeks, so the draft reaches a first pass, AND
  - the contract is four days a week, not five, in writing, AND
  - the reserve is not spent down during it — the point is to rebuild, not replace.
DON'T if the start date is fixed. A fixed start makes this a choice between the
contract and the draft, and three of the four lenses say the draft is closer to
mattering than one more good client is.
```

This is the shape every council output should take: independent lenses, explicit conflict, conditional
decision.

---

## Read-Only Posture

The council **analyzes; it does not execute**. No calendar writes, no ledger edits, no file moves — not
by the orchestrator, not by any subagent. Subagent prompts explicitly forbid writes.

End the council output by naming the next move and which subject owns it:

> "Next move: {action} — it belongs to {subject}."

The council's product is a decision frame, not an action.

---

## Rules

- Never answer the question yourself before convening — your read is not one of the lenses.
- Always dispatch via the `Agent` tool, in parallel, one per selected subject.
- Never load several subjects' canon into your own context — that defeats the isolation.
- Select 2–5 subjects. Justify each. Don't pad the room; don't starve it.
- Synthesis must name conflict explicitly. A consensus-only output is a failure.
- Read-only throughout.

## What this skill needs outside its own folder

| what | where | status |
|---|---|---|
| the notes-folder resolver | `shared/brain_root.py` | ✅ here |
| the sibling that runs invented expert lenses | `/advisory-council` | ✅ here |
| the folders the room is read from | `<notes>/desks/<subject>/canon/` | ⛔ never ships — `/ingest` builds them from your own material |
| optional hand-written lenses | `<notes>/config/desks.md` | ⛔ never ships — optional, and yours |
