---
skill: summarize
description: "Brief conversational gist of the most recent response only. Use on \"/summarize\" — distinct from /simplify (condense) and /explain (unpack)."
shape: utility
title: Summarize
version: 1.0
created_at: 2026-05-25
updated_at: 2026-05-25
status: active
triggers:
  - "/summarize"
note: "Summarize only the most recent response, not the full thread."
---

## Intent (§0.5)
**User outcome:** A one-word shortcut to a brief conversational gist of just the last response — nothing more. **Bar:** "I got the gist of what you just said in a sentence — I didn't have to re-read it."
**Role:** the gist-reporter — the thinnest of the three re-render skills. Last response only, conversational, no thread recap; does NOT unpack (that's /explain) or preserve-full-substance (that's /simplify) — it just gives the gist. One-shot, fully autonomous.

Summarize only your most recent response conversationally for me. Do not recap the full conversation thread — focus exclusively on what you just said.

## Format (R-6)
≤3 sentences, plain prose, no bullet lists, no headers. One sentence per main point from the **last response only**; lead with the single most important takeaway. **Do not use for** full-thread recaps or multi-turn distillations.
