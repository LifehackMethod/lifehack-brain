---
topic: [llm-engineering]
skill: orient
description: "Get re-oriented in a build you've lost the thread of — the three altitudes and their desired outcomes, plus near past / right now / near future. Use on \"/orient\", \"orient me\", \"where am I in this build\", \"I've lost the thread\"."
shape: command
summary: |
  A prompt, nothing more. Answers one question — "what was happening in this build?" — by
  altitude and then chronologically. Distinct from /checkin (reconciles plan vs brief and
  proposes today's scope) and /altitude (sets or prints the rungs).
  Triggered by: /orient, "orient me", "where am I", "remind me what we're doing".
---

# /orient

Deliver this prompt:

---

I need more of an orientation.

Orient me in terms of the three altitudes and their desired outcomes.

Then orient me chronologically: what have we done in the near past, what are we doing right now, and what are we doing in the near future.

If a rung or a period genuinely has nothing behind it, **say so and move on — do not invent one to fill
the space.** "Nothing was decided above ground level" and "nothing happened here yet" are real, common
and correct answers. An orientation that manufactures a frame is worse than a short one, because I will
act on it. (Same rule `/altitude` carries as `NO-FRAME`; `system/work-altitude-doctrine.md` §4 states the
risk: a model handed no legal way to say nothing was decided will manufacture a decision.)

I just need to get oriented so I can remember what was happening in this build.

## What this skill needs OUTSIDE its own folder

**Nothing.** It is prose end to end — no scripts, no shared files, no hooks. That is a
claim worth stating rather than leaving to be inferred: an empty manifest table and a
missing one look identical, and only one of them means "checked".
