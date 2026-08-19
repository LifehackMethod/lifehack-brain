# planning-weekly BUILD CHECKLIST — the 41 injection pieces (anti-drop backstop)

> Every injection file / component the 7-phase rebuild must produce. Source: the design's 41-item
> punch-list (`desks/cal/projects/cadence-skills/cadence-phases-combined-2026-07-19.md`). **Nothing ships
> until every line is checked.** A line is ✅ ONLY when the piece is written AND its phase passed a live
> run (SOP: "done" = verified in the running skill, never "written"). **STATUS 2026-07-20:** P0–P5 (items 1–32) ALL WRITTEN rough = `[~]` — awaiting the Phase C live shakeout for behavioral ✅. Phase-6 items 33–38 = Phase E (spun off). Standing components 39–41 ✅.

Status: ⬜ not started · ✍️ written
> (awaiting live verify) · ✅ written + live-verified.

## Standing components (used across all phases) — Phase A ✅ DONE + VERIFIED 2026-07-20
- [x] 39. **ANCHOR.md** — L1 identity anchor: Cal + THE LAW, 7-phase arc, interrogative mandate. `[A1]` ✅
- [x] 40. **HUD line format** — `🧭 Cal · Weekly [N/6] PHASE · what · next → X`; 6 buckets `[1/6] ORIENTATION … [6/6] TRIAGE`. Rendered in Verify-A. `[A2/PRE-3]` ✅
- [x] 41. **scratch_capture_gate.sh** — confirmed resolving the armed pad in Verify-A (reuse, not rebuilt). `[A2]` ✅
- [x] —. **SKILL.md** — 7-phase front door + blind-chain entry + arm/clear wiring for all 3 hooks. Injector/gate registered in live settings; wiring proven in Verify-A. `[A1]` ✅

## Phase 0 — System Layer (map agents) — B0
- [~] 1. Map-agent driver — **Conflicts** angle (reads-for, Map output format, delta-only read rule).
- [~] 2. Map-agent driver — **Lanes** angle.
- [~] 3. Map-agent driver — **Audit/Biological** angle.
- [~] 4. Map-agent driver — **Delta-vs-Monthly-Goal** angle.
- [~] 5. **Map output-format spec** — pointers vs thin content vs flagged items.
- [~] 6. **Size/confidence-readout format** — round-count suggestion → Phase 1.
- [~] —. On-demand full-read sub-agent — WRITTEN as its own brief `prompts/_full-read-reader.md` (sonnet; reach corpus when unsure; raw never enters main window; referenced from P2). `[B0 audit-patch]`

## Phase 1 — Orientation — B1
- [~] 7. **Phase 1 driver** (`prompts/01-orientation.md`) — deliberate-bias framing · soft new-user gate · big-delta notify-and-ask · cast · flow.

## Phase 2 — Connect the Dots — B2
- [~] 8. **Phase 2 driver** (`prompts/02-connect-the-dots.md`) — leveraged-question rule · SMART rule · dot-connecting · adaptive rounds · flywheel write-back · THE LAW ("collect dots, never name the Win").
- [N/A] 9. (lens = rank-biggest-first mixed, chosen 2026-07-20 → folded into the 02 driver, no separate file) sub-driver — Conflicts step.
- [N/A] 10. (lens = rank-biggest-first mixed, chosen 2026-07-20 → folded into the 02 driver, no separate file) sub-driver — Lanes step (1 Q/lane · don't push quiet · gate on filled lanes file).
- [N/A] 11. (lens = rank-biggest-first mixed, chosen 2026-07-20 → folded into the 02 driver, no separate file) sub-driver — Audit/Biological step.

## Phase 3 — Prioritization — B3
- [~] 12. **Phase 3 driver** (`prompts/03-prioritization.md`) — portrait-painting · 3 reports' mechanics · leverage-angle engine · micro-report · signal-through-noise.
- [~] 13. Leverage-angle brief — **Multiplier** (Cascade + Subtraction/Keller).
- [~] 14. Leverage-angle brief — **Threat**.
- [~] 15. Leverage-angle brief — **Honest Self-Reckoning** (Avoidance + Retrospective).
- [~] 16. Leverage-angle brief — **Chain-Fidelity**.
- [~] 17. Leverage-angle brief — **Calendar**.
- [~] 18. Leverage-angle brief — **Identity**.
- [~] 19. Leverage-angle brief — **Relational**.
- [~] 20. Leverage-angle brief — **External-Eye**.
- [~] 21. Leverage-angle brief — **Capacity**.

## Phase 4 — The Council — B4
- [~] 22. **Phase 4 driver** (`prompts/04-council.md`) — council setup · roster · thorough-brief rule · headline+reasoning format · `advisory-council` invocation.
- [~] 23. Member injection — **April** (10th Man; persona wording open).
- [~] 24. Member injection — **Time Supply**.
- [~] 25. Member injection — **Blind Spot Detector** (11-bias framework embedded).
- [~] 26. Member injection — **Touchdown Dance**.
- [~] 27. Member injection — **Long-lens / Ponzi**.
- [~] 28. Member injection — **The Builder** (untapped-software-features angle).

## Phase 5 — Action — B5
- [~] 29. **Phase 5 driver** (`prompts/05-action.md`) — 3 steps · scope guard · write-reach bounds · un-skippable confirm gate · read-back rule.
- [~] 30. **Calendarize** step sub-driver — body-first · Win-in-best-energy-window · shallow-batching · WRITE-LEDGER · floor+ceiling · masterpiece bar.
- [~] 31. **Report** step sub-driver — SMAL Win · Bonus Aims · NOT-THIS-WEEK · capacity · week shape · mid-week checkpoint · skeptic pass · Olsen close.
- [~] 32. **Act / Clerk** sub-agent brief — full WRITE-LEDGER embedded · read-back gate every row · ❌/✅ · delete scratchpad last only if all ✅ · Agent-Ops-only rail · bounded task/email reach.

## Phase 6 — Inbox Zero / Triage — BUILT 2026-07-21 (pulled into planning-weekly per the person; task-app-neutral, outside-framework depth folded)
- [~] 33. **Phase 6 driver** (`prompts/06-triage.md`) — sweep order · email-as-task-vector · bulk-default · parking-first-class · wrap-tally · suggest-aggressively/execute-nothing-unseen.
- [~] 34. Step sub-driver — **Fires-First**.
- [~] 35. Step sub-driver — **Dead-Pile Pre-Clear**.
- [~] 36. Step sub-driver — **Bulk** (≤10 attention rows).
- [~] 37. Step sub-driver — **Individually-Handle** (email-as-task-vector; human threads never archived alone).
- [~] 38. Step sub-driver — **Park** (clean-exit framing).

---
**Total: 41 punch-list items + SKILL.md.** Phases 0–5 built in this plan (A–D); Phase 6 (33–38) spun off to Phase E.
Per-phase L3 desired-outcome line (§1.6 #2) written into each driver. Every driver gets a lean-check at its verify.
