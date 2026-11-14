---
title: "Ingest Gate — frozen call signature: history log"
what: "Retired and moved text from ingest-gate-signature.md, kept verbatim and dated so nothing is lost. Not read in normal use."
read_in_normal_use: false
base_file: "system/schemas/ingest-gate-signature.md as frozen 2026-11-14 (freeze-2026-11-14, V2 HEAD 0037ccb)"
created: 2026-11-14
status: "draft — lands with the fine-china edit pass, round three"
---

# Ingest Gate — frozen call signature: history log

Each entry is one passage moved out of the document on 2026-11-14 (round three 'lowerbooks'). Line numbers are the frozen base's. The original is copied word for word inside each fenced block. Append-only.

## 2026-11-14 · MOVE · lines 118-124 · G3-108

- Reason: Batch 3 item 1 ("ingest-gate contract v1.1" approved): the v1.0 email FLAG-only clause, superseded by the REAL-ATTACK lift (code since 2026-10-27, `ingest_gate.py` L134-153).

~~~~
When `source_type == "email"`, findings are constrained to **FLAG, never DANGER**, until a
provenance-aware classifier ships. This prevents a base64 attachment or a security-newsletter
snippet from triggering DANGER and quarantining real mail. The gate enforces it by passing
`--flag-only` to the verdict tool and never returning `passed=False` for email. **This clause is
part of the frozen contract — relaxing it requires a schema_version bump.** (Wiring email to the
alarm WITHOUT this constraint would trade a silent false-negative for an auto-quarantine of real
mail — strictly worse than not gating email at all.)
~~~~

