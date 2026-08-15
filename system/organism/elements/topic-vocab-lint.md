---
element: topic-vocab-lint
maturity_label: DORMANT
record_type: organism-element
altitude: index-line
---

Two-part controlled-vocabulary enforcement layer, of which only one part ships. ⛔ **No vocabulary file ships with this repo** — a `topic:` vocabulary is a taxonomy OF A PERSON'S LIFE, and shipping one hands every reader someone else's categories, so `system/topic-vocab.md` is deliberately absent and `system/tools/cowork-ingest/test_topic_check.py` asserts it must never appear. The authoritative closed list of `topic:` slugs is the person's own, written by hand and living beside their material at `<data root>/memory/topic-vocab.md`; `system/tools/cowork-ingest/folder_scaffold.py` and `pipeline.py topic-check` resolve it in a fixed four-rung order (`--vocab` → data root → repo `memory/` → legacy in-repo copy) and, when none of them exists, **REFUSE by name — printing every path tried plus instructions for writing one — rather than passing over an absent subject or inventing a slug** (the `ABSENT-SUBJECT-RULE-v1` shape: "there was nothing here I could check" is a distinct outcome from "I checked and it's clean"). The half that does ship is `system/tools/validate_frontmatter.py` (a PostToolUse hook and direct-call validator that checks required frontmatter fields — `record_type`, `desk`, `created_at`, `status` — are present, that the deprecated `artifact_type` field is absent, and that only managed files are judged; exits 0 valid / 1 violation / 2 cannot-evaluate). Together they enforce the write-gate rule: classify before saving, always from the controlled vocab — but the vocab itself is yours to write, and until you write it the gate refuses instead of quietly passing.

### INTENT: keep every durable file's `topic:` tag drawn from one closed, human-approved vocabulary so memory stays searchable and never accumulates one-off invented slugs.

> INDEX-LINE ONLY — dormant per the 2026-07-24 usage cross-ref; expand to a full entry only if it proves load-bearing.

generated_from: system/topic-vocab.md, system/tools/validate_frontmatter.py
