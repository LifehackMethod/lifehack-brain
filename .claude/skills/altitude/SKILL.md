---
topic: [llm-engineering, hooks]
skill: altitude
description: "Set or read this session's three work altitudes — ground / 5,000 / 10,000-ft. Use on \"/altitude\" when there is no armed brief or plan but the work still has a real frame; \"/altitude clear\" removes them, \"/altitude\" alone prints the current read."
shape: command
summary: |
  The manual rung-setter for work altitude. inject_work_altitude.sh normally reads the
  10,000-ft view off the armed brief and the 5,000-ft view off the armed plan; when neither
  is armed it says so honestly. This command lets a person supply those two rungs by hand for
  work that has a real frame but no project behind it. With no arguments it simply prints the
  current three-altitude read. Rule: system/work-altitude-doctrine.md.
  Triggered by: /altitude, "set the altitude", "what altitude are we at", "clear the altitude".
---

# /altitude

> **Intent.** Give a session a truthful 10,000- and 5,000-foot rung when no brief and no plan can
> supply one — and let a person read or correct the current frame at any time. **Bar:** *"it told me
> where we are at all three altitudes, and it didn't make any of them up."*
>
> **The rule lives in `system/work-altitude-doctrine.md`** — the three rungs, where each is read
> from, and the four-member answer set. Read it if anything here is ambiguous; do not restate it.

## The three rungs

| rung | read it from |
|---|---|
| **ground** | the task in front of you — never stored, always live |
| **5,000** | the armed plan's `Phase ▸ Feature`, the seam this touches, or the learning being produced |
| **10,000** | the armed brief's desired outcome, a standing goal above every brief, or nothing |

Only the top two can be hand-set. Ground is always read live — a stored "what I'm touching now"
would be stale within a turn.

## What to do

Resolve the repo once; every command below hangs off it.

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
```

**1. No arguments — print the current read.**
Resolve, in this order, and say which source each rung came from:

    bash "$ROOT/system/hooks/altitude_flag.sh" status   # hand-set rungs, or "none"
    bash "$ROOT/system/hooks/pm_flag.sh" status         # the armed brief path, or "none"
    bash "$ROOT/system/hooks/plan_flag.sh" path         # the armed plan path, or "none"

Hand-set rungs win over the files. For any rung backed by a file, **open the file and quote it** —
a rung written from memory is not a rung. Then answer in the doctrine's shape, as exactly one of
`FRAMED` · `PARTIAL` · `NO-FRAME` · `UNCHANGED`.

**⚠ If nothing resolves, the answer is `NO-FRAME`.** Do not invent a rung to fill the space. A
ground-only fix is a real and common shape, and `NO-FRAME` is a correct answer, never a failure.

**2. Setting a rung.** Take the person's own words as close to verbatim as they will go — this is
their frame, not your paraphrase of it:

    bash "$ROOT/system/hooks/altitude_flag.sh" set --10k "<the standing goal>" --5k "<what it sits inside>"

Either flag alone is fine; setting one leaves the other untouched. Echo back what landed.

**3. Clearing.**

    bash "$ROOT/system/hooks/altitude_flag.sh" clear

## Notes

- Rungs are **session-scoped**. A flag stamped with another session's id is ignored, so two windows
  never cross-wire.
- Setting a rung does not change the cadence. `inject_work_altitude.sh` still fires on its own token
  bucket; this only changes *what it points at* when it does.
- If a brief or plan later gets armed and the hand-set rung is now wrong, clear it. A stale hand-set
  rung outranks the live file and will quietly keep answering with yesterday's frame.

## What this skill needs outside its own folder

| what | where | status |
|---|---|---|
| the rung store | `system/hooks/altitude_flag.sh` | ✅ here |
| the per-turn re-anchor that reads it | `system/hooks/inject_work_altitude.sh` | ✅ here |
| the armed brief / plan it falls back to | `system/hooks/pm_flag.sh`, `system/hooks/plan_flag.sh` | ✅ here |
| the rule itself | `system/work-altitude-doctrine.md` | ✅ here |
