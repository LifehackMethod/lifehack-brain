---
id: system-work-altitude-doctrine
title: Work Altitude — the three altitudes a session names before it works
record_type: doctrine
created_at: 2026-08-05
updated_at: 2026-08-05
status: active
authority: user
---

# Work Altitude

> **The law:** a session working on something states, periodically and unprompted, what it is doing at
> **three altitudes** — and says plainly when there is no larger frame. Read when the `inject_work_altitude`
> hook fires, or on `/altitude`. Lives LOW on purpose: the hook carries the operative question, so nothing
> here needs to load into every conversation.
>
> **This is [`intent-doctrine.md`](intent-doctrine.md) applied to WORK.** The parent law says every *object*
> declares its intent. This is the same law pointed at the *job in front of you*: the work declares which
> intent it is serving, at three levels of zoom.
>
> ⚠ **NOT the same thing as [`knowledge-altitude.md`](knowledge-altitude.md).** That doctrine governs **where
> a piece of knowledge gets FILED** (global canon → desk → sub-folder → deep). This one governs **the zoom
> level of the WORK you are doing right now.** Same word, two different objects. They share a parent and
> nothing else.

## 1. Why this exists

a recurring, illustrative operator complaint: *"a lot of times when I'm trying to work on something, it gets pulled
into the wrong altitude… constantly Claude is pulled into the lowest altitude and it loses its perspective."*

That's a three-altitude filter being invoked by hand, and finding it worked. A rule that has to be re-typed is a
missed system patch (`CLAUDE.md` → *"fix the system, not your notes"*), so it became a hook.

**The failure this prevents** is not ignorance — a session at ground level usually knows the code fine. It is
**losing the reason**: fixing the file correctly while forgetting that the fix exists to serve a seam, and
that the seam exists to serve something being built. A fix that is locally right and globally pointless costs
more than a bug.

## 2. The three rungs, and where each is read from

| rung | the question | read it from |
|---|---|---|
| **Ground** | What am I actually touching right now? | the task in front of you — the file, the function, the failing test |
| **5,000 ft** | What does this sit inside? | the plan's `Phase ▸ Feature`, **or** the seam-neighbourhood this code interlocks with, **or** the generalizable learning this fix is producing |
| **10,000 ft** | What is this ultimately for? | **the brief's desired outcome** — or a standing goal that sits above every brief, which is what `<notes>/canon.md` is for |

**The 10,000-foot view is not capped by the project.** A brief's desired outcome is the usual answer and the
first place to look, but it is not the only legal one. Sometimes the real reason for the work sits *above*
every brief — *"we are fixing this skill because we want a machine that builds better skills"* is a 10,000-foot
view that no brief contains. Reading the rung strictly off the brief will confidently return the project's
goal and silently drop the thing that actually motivated the work.

**Read them, don't compose them.** When a brief or plan exists, the higher rungs are a **lookup**, not a
reflection. Open the file and quote it. A rung you wrote from memory is not a rung.

## 3. The closed answer set — the seam

This doctrine sits on a code/model seam: a hook decides *when* to ask, the model answers, and the answer must
be one of a **bounded set** (`system/build-rules-index.md` → the seam block).

| member | meaning |
|---|---|
| `FRAMED` | all three rungs named, each traceable to a file or to this session |
| `PARTIAL` | ground plus one higher rung; **the missing rung is named as missing** |
| `NO-FRAME` | **ground only — self-contained work, no larger frame. A CORRECT answer.** |
| `UNCHANGED` | the frame is the same as the last check; one line, no restatement |

## 4. `NO-FRAME` is correct, and it is the most important member

The seam rule requires that the bounded set contain **one member meaning no outcome was reached**, precisely
because a model handed no legal way to say *"nothing was decided"* will manufacture a decision that code
cannot tell from a real one.

Here that member is `NO-FRAME`, and it carries the whole design:

- **A ground-only fix is a real and common shape.** Renaming a variable, fixing a typo, correcting a path —
  these genuinely sit inside no seam and serve no larger goal beyond being correct.
- **Without a legal "none," every trivial fix grows a fabricated 5,000 and 10,000-foot view.** That is
  confabulation, it reads exactly like the real thing, and it trains the reader to skim the block — which
  kills the mechanism inside a week.
- **`NO-FRAME` is never a failure and is never scored lower than `FRAMED`.** Answering it honestly is the
  behaviour this doctrine wants. Anything that makes it harder to answer than the other three members is a
  defect in the hook, not in the session.

This is the same discipline as `CLAUDE.md` → *"Confidence Requires a Source"*: label the absence, never
assert into it.

## 5. Answer shape

Short. Three lines when the frame is live, one line when it has not moved:

    ▲ 10,000 — <the desired outcome, quoted from the brief, or the standing goal>
    ▲  5,000 — <the Phase ▸ Feature, the seam, or the learning being produced>
    ▲ ground — <the thing being touched right now>

`UNCHANGED` is a single line. `NO-FRAME` is a single line naming the ground work and saying there is no
larger frame. **Expand into prose only on a DRIFT** — when the ground work has moved away from the 5,000 or
10,000-foot view. That drift is the one thing worth interrupting a human for; everything else is a receipt.

## 6. What fires this

- ✅ **`system/hooks/inject_work_altitude.sh`** — a `UserPromptSubmit` INJECT hook, registered. It fires
  once per 50,000-token bucket of context, offset 10,000 tokens, and again immediately after a compaction
  (detected as the token count dropping below its own watermark). Tune both with `ALTITUDE_CAPTURE_EVERY`
  and `ALTITUDE_OFFSET`.
  ⚠ **The offset carries a lesson that is worth more than the number.** In the system this came from it
  was a bet on firing about one turn before a sibling capture hook, so that captured decisions were filed
  by a session which had just restated its frame — and an adversarial audit on 2026-08-05 refuted the bet:
  it only wins when a single turn adds fewer than 10,000 tokens between the two checks, and a tool-heavy
  turn (85k → 150k in one step, demonstrated) inverts the order silently. That sibling hook is not part of
  this repo, so the bet is moot here and the offset survives only because it staggers the fire points off
  round numbers. **An ordering that nothing reports is not an ordering you have.**
- ✅ **`/altitude`** — sets the top two rungs by hand for work that has no brief and no plan but does have
  a real 10,000-foot view. Also prints the current read on demand.

**The hook parses nothing.** It hands over the brief and plan **paths** and lets the session read them.
Measured 2026-08-05 across three real briefs: the FRAME heading and the desired-outcome formatting both vary
(bold inline prose in two, a `###` heading in the third), so a mechanical extractor cannot be relied on — but
a reader handles the variance without noticing it.

## 7. Self-application

This doctrine governs how a session orients itself; it does not need to load into every conversation, because
the hook carries the operative question. Full text lives here (low, on-demand); `CLAUDE.md` carries a pointer
only. If we ever want to paste this file into `CLAUDE.md`, that is the doctrine failing `knowledge-altitude.md`
§8's test — don't.
