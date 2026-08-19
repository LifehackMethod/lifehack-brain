---
element: calculate
maturity_label: DORMANT
record_type: organism-element
altitude: index-line
---

A single-command skill (`skills/calculate/SKILL.md`) that arms "numbers-mode" for the current session — a UserPromptSubmit hook then re-injects the compute-mechanically rule every turn (via the compute-mechanically-gate plane) until explicitly disarmed or a 12h TTL expires. Subject folders named on your own list at `<notes>/config/numbers-auto-arm` (one folder name per line; no file means no auto-arm) arm themselves on launch; `/calculate` is the manual on-switch for any other session. `/calculate off` disarms. See compute-mechanically-gate for the underlying hook implementation.

### INTENT: make sure a number that matters is never hand-computed by the model — arm the compute-mechanically rule for the session so every calculation runs through code, not the model's head.

> INDEX-LINE ONLY — dormant per the 2026-07-24 usage cross-ref; expand to a full entry only if it proves load-bearing.

generated_from: skills/calculate/SKILL.md
