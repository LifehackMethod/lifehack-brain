---
id: system-playbook-plan-template
title: Plan Template — the shape a plan must come back in
record_type: playbook
created_at: 2026-10-31
status: active
authority: user
---

# Plan Template

> Kept from the retired `architecture-planning-sop.md` (retired 2026-10-31; Enver: "I don't want to lose the plan template."). The section below is that SOP's "★★ ALWAYS — the plan spec" section, copied verbatim. It describes a handoff prompt, so "this SOP" in the text means the retired SOP.

## ★★ ALWAYS — the plan spec the HANDOFF must carry (not a format this SOP produces)
**This SOP never writes a plan — but its handoff prompt MUST order plan mode to build one in a fixed shape.** So
every handoff prompt this SOP emits **REQUIRES the downstream plan to come back as:**
- **A `FRAME` block at the very top** — desired outcome · success criteria · constraints · out-of-scope (one line each is fine). The human-only frame, approved ONCE up front: it's what lets execution run autonomously without re-asking, and it satisfies `project-manager`'s Frame-intake gate so the brief is treated as authoritative.
- **`Phase → Feature → Task`**, and
- **every task = `Execute → Verify & test → mark-complete (- [ ])`** — a task isn't done until its Verify passes, and the **Verify is a *runnable* check** (a command / a rendered output to look at), not "looks done."
- **each task gear-tagged** — gear-1 (single-thread) · gear-2 (background sub-agent) · gear-3 (Agent-Team wave). **The tag is a HINT, not a command:** `/build` re-decides the gear per task from the work's shape, so write each task to *read as standalone* (legible independence + done-criterion + embedded context) — that, not the label, is what gets it fanned out. **Default to gear-2** for decided, self-contained work; **gear-3 only when the user has said "use agent teams" / "team build"** — it's opt-in (~7× tokens). (gears doc archived 2026-10-31)
- **each phase LANE-TAGGED — which tasks are `independent` (launch together) and which are `gated` (and by what).** Gear tags say *how* a task runs; lanes say *when*. **The gate rule: one task gates another only if it writes a file the other reads or writes, or the other consumes its output — nothing else. Independence is the assumption; a gate needs a stated reason.** Without this a plan executes in single file even where nothing blocks it, and the wall-clock loss is invisible because no one ever sees the build it could have been. Name the file each task writes so the gate is checkable, not a judgment the executor has to re-make. Lanes: `skills/autoplan/SKILL.md` → "Lanes"; execution: `skills/build/SKILL.md` → "Delegation is the default."
- **a named "safe-halt" section** (a *checkable* "pause only when X is green," not a vibe). It is ADDITIVE to `/build`'s always-on stops, and **must explicitly list human-side Google writes (Sheets / Calendar / Gmail)** — `/build` does NOT auto-pause for those — alongside the genuinely irreversible / destructive, a failed verify, and any plan-changing decision.
- **a deferred list** — each item tagged **TODO** (still viable → files to the brief's OPEN LOOPS) or **DEAD-END** (ruled out → files to DEAD ENDS), so `project-manager` mirrors it without rework (it has no generic "deferred" slot).
- **NO SILENT DEMOTION — a `⚠ CUT FROM THIS BUILD` block, directly under the FRAME, separate from the deferred list.** The deferred list above is for ideas the *process* explored and set aside. Anything the *stakeholder explicitly named as to-build* that is NOT in the executable Phase▸Feature▸Task body is a different, louder category: it must appear in a top-of-plan `⚠ CUT FROM THIS BUILD` block — each item stating what it is · why it's proposed for deferral · what's lost · flagged **needs explicit OK**. **Plan-approval is NOT cut-approval** (surface each cut as its own decision — the `/save` rule "surface conflicts to the human, never auto-resolve," applied to scope); **default is keep-it-in** (deferral needs an affirmative reason AND sign-off, never the reverse); an approved cut files to OPEN LOOPS so it stays visible and a build that skips it cannot read as "done." Before emitting, reconcile every named build-item + the FRAME's desired outcome against the body — each maps to a Task or lands in this block; nothing vanishes.

- **★ A TASK MAY CITE A RULING ONLY WHERE THAT RULING STATES ITS DATE AND ITS AUTHOR. "See §X" is not a
  citation if §X is still asking the question.** (2026-08-05, T18.8.) A plan task read *"⚖ RULED
  2026-08-04 — see §18.8d"* and authorised re-drawing a boundary that two shipped element files assert
  about themselves. **§18.8d was headed "the operator's call", closed with "Lead's read: it MOVES", and ended
  "⚠ Surfacing rather than deciding" — it recorded an OPEN QUESTION.** Cross-checked: the Story Log, the
  brief's Current State and the scratchpad all failed to mention any such ruling. **It did not exist.**
  ★ **This is the INVERSE of the familiar staleness bug and it is the more dangerous direction:** the
  usual failure leaves a task *asking* for a decision already given, which wastes the human's time; this
  one *asserts* a decision never given, which **spends the human's authority.** Caught at check-in only
  because someone opened the cited section instead of trusting the citation. **How to apply:** when a task
  claims a ruling, the cited location must carry **the verdict, the date, and who gave it** — all three.
  A pointer to a section that still poses the question is a forward reference, not evidence. And when you
  RECORD a ruling, write those three facts at the site, so the next reader can verify the citation without
  reconstructing the conversation.

**No flat plans, ever.** This is a demand you hand to plan mode — paste it in, hit return, plan mode obeys it.

---
