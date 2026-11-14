---
title: "The register — schema v1: history log"
what: "Retired and moved text from schema-v1.md, kept verbatim and dated so nothing is lost. Not read in normal use."
read_in_normal_use: false
base_file: "system/register/schema-v1.md as frozen 2026-11-14 (freeze-2026-11-14, V2 HEAD 0037ccb)"
created: 2026-11-14
status: "draft — lands with the fine-china edit pass, round three"
---

# The register — schema v1: history log

Each entry is one passage moved out of the document on 2026-11-14 (round three 'lowerbooks'). Line numbers are the frozen base's. The original is copied word for word inside each fenced block. Append-only.

## 2026-11-14 · MOVE · lines 138-154 · G3-9

- Reason: Batch 4 item 3 (struck chains to history); K31 — the five design questions as first asked, struck through, verdicts in the Rulings section.

~~~~
## Design questions Enver ruled on, 2026-09-15 (history — see "Rulings" above for the verdicts)

These were the five open questions this doc originally raised at the B1.1 checkpoint. Kept here,
struck through, as the record of what was actually asked — the "Rulings" section above is the
verdict each one got; nothing here still applies.

1. ~~`hook.event` — closed enum or open string?~~ **Ruled: CLOSED**, to the documented 33-event
   Claude Code set (Ruling 1).
2. ~~`launch_mode` — what closes it, and when?~~ **Ruled: DROPPED from v1 entirely** — not
   deferred, not left null (Ruling 2). **Then RESTORED the same day** (Option G) — see the
   "Addendum" section below; this history entry stands as what was asked and answered FIRST, not
   as the field's final state.
3. ~~Strict unknown-key rejection — too strict for v1?~~ **Ruled: STRICT stays**, permanently
   (Ruling 3).
4. ~~JSONL vs YAML — confirm the call.~~ **Ruled: JSONL**, confirmed (Ruling 4).
5. ~~`scheduled.path` is forced to double duty — confirm acceptable?~~ **Ruled: KEPT**, documented
   as intended (Ruling 5).
~~~~

