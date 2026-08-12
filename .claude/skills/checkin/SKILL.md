---
name: checkin
title: "Check-in — re-orient, and leave the record sharper"
shape: interactive-workflow
status: active
description: "Re-orient on the active project — reconcile where you meant to go against what the notes say and what actually happened, then propose the smallest next scope. Use on \"/checkin\", \"where are we\", \"re-orient\", or after a gap."
summary: |
  Reconciles three horizons — the desired outcome, the last-saved state, and what happened this
  session — surfaces only the tensions that would change what you do next, and proposes today's scope.
  It drafts every change and asks once, in one batched round. It leaves the record sharper than it
  found it, or it has failed.
triggers: ["/checkin", "where are we", "re-orient", "what should we scope today"]
allowed-tools: [Read, Glob, Grep, Bash, Edit]
created_at: 2026-06-02
updated_at: 2026-08-11
---

## Intent (§0.5)
**User outcome:** mid-project, re-orient in under a minute — where they meant to go, versus what the
notes say, versus what actually happened this session, plus the smallest viable scope for today — so
nothing falls through the gap between sessions. **Bar:** *"I ran /checkin and I know what to do next —
the plan isn't lying about what's already done."*
**The blade sharpens with every pass.** That is this skill's reason to exist, not a flourish: each
check-in leaves the record *sharper* than it found it — one more stale line repaired, one more tension
named, one more thing the next session will not have to rediscover. **A pass that leaves the record
duller has failed, even if it produced a tidy summary.** The dulling has a direction: a plan that only
accumulates ✅ marks grows more confident and less accurate at once, because the assumptions underneath
were never revisited while the completion count went up. Sharpening is the counter-force.
**Role:** the project's navigator. It arms the project and plan flags, loads the brief in a deliberate
order, compacts the scratchpad **before** it diffs, surfaces deltas, and proposes a smallest-viable
scope. It appends confirmed decisions to the story log; it never rewrites one.

# Check-in

## Paths (set once)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```

## Write authority — what this may and may not write

- **MAY write freely — the brief's `## 7. SCRATCHPAD`.** It is the dumb capture surface. Anything goes
  in; a big chunk becomes a pointer (name + path), never an inline dump. No confirmation needed.
- **MAY append — the `## 4. STORY LOG`, and set a decision's bucket on the board.** Additive only.
  **Never overwrite, prune or rewrite an existing entry** — an overtaken decision is tagged
  `superseded-by`, not deleted. The one in-place change ever allowed on an entry is that status tag.
  **Journal-first:** the matching `$DATA/system/journal.md` line goes down before or as you append.
- **MAY write — the linked plan**, on a high-confidence stale step, with explicit approval.
- **MAY PROPOSE, never silently write — the `## 2. CURRENT STATE` narrative and the success criteria.**
  Draft a before→after diff; it is shown and confirmed in the one batched round.
- **MAY NOT write — the FRAME, the desired outcome, the definition of done.** That is the locked
  anchor. It changes only on explicit direction in the session, never by inference, in the brief or in
  the plan. **Drift in it is observe-and-flag only:** you may note that new information seems to be
  making it stale. You may not draft a rewrite of it, not even as a proposal.
- **MUST PRINT, MAY PROPOSE, MAY NEVER WRITE UNASKED — the three-rung altitude block.** Three duties,
  and they are not interchangeable. **Print** it, unconditionally, by code, as the opening of the reply.
  **Propose** every change to it — missing, badly worded, drifted, or sitting on competing surfaces — as
  item 0 of the one panel. **Write** only on a yes.

  > ⛔ **THE "WRITE IT DIRECTLY, NO YES NEEDED" LICENCE IS DELETED. Do not restore it.** It rested on
  > two arguments and both failed in the field the day they were written. *"A missing block has no prior
  > claim to contradict"* — false whenever the brief already carries competing status surfaces; observed
  > live, a session found three, wrote a fourth directly, and honestly reported that the new block now
  > sat on top of three contradicting claims. **It degraded the section it was repairing, and the rule
  > told it to.** *"A reword is about prose, not about the project"* — also false. Rewording a rung for
  > a blind reader forces you to disambiguate it, and disambiguating is deciding what it meant. A rung
  > reading *"never made one skill FAST"* cannot be rewritten without choosing between fast-to-build and
  > fast-to-run — a real decision, made silently, under cover of grammar.
  >
  > ⭐ **And the deeper reason: this block's only audience is the person.** An artifact written *for*
  > one human, *by* a machine, *without* that human reading it first, is not maintenance — it is a frame
  > swapped under them. It happened, and the verdict was plain: they approved a frame they had never
  > read. This skill may compose, draft, re-derive and argue for a rung. It may not install one.
  >
  > The schema calls this block *"machine-maintained, unlike the frame."* That is about **who drafts
  > it**, never about **who approves it.** The machine derives the reading; the human ratifies it.

## Arming is immutable for the life of a window

If this window is already armed to a **different** project, `pm_flag.sh arm` **refuses and exits 3.**

⛔ **That refusal is correct. It is not a bug and it must never be worked around** — not by clearing the
lock, not by editing the flag file, not by a second call with different arguments. **Report it and
stop:** *"this window is armed to X; you asked for Y — open a new window, or tell me to continue on X."*

**Why it exists:** a session once re-armed its own window from one project to another on its own
judgment, mid-conversation, while obediently following the arm instruction. Two handoffs went out
pointing at the wrong project and **the wrong brief's human-authored frame was rewritten.** It recurred
in a second window the same evening. The conclusion on the record: **prose could not stop it.** A
same-project re-arm still refreshes normally; only a switch is refused.

## The two modes

| mode | how it is known | what changes |
|---|---|---|
| **PICKUP** | the `new-session` token is present in the invocation | the graduation does not run · the handoff proof does not run · gate 2 is expected to refuse · the story log is read in full · **an empty panel is the correct output** |
| **CLOSE** | no token — this is the session that did the work | everything runs |

**`new-session` is optional and its absence changes nothing.** The set is `{present, absent}` and
**absent is the no-outcome member.** It must never become required: a required flag would delete the
no-outcome member, and every hand-typed `/checkin` would silently change meaning.

⛔ **The token describes this window's relationship to the work, never the run's importance.** A window
that opens cold and then lands approved edits **owes the handoff proof like any other** — the token
governs the opening, not the whole session. If edits land, the mode has been overtaken by events; say so
rather than resting on the token.

> **Why a token rather than a judgment.** This skill refuses to trust a self-assessed mode, in its own
> words: *a self-assessed mode switch is the same unreliable gradient as a self-assessed depth ladder,
> and it fails the same way.* A model cannot report on its own compliance. **But a token supplied by the
> operator, or by the previous session's handoff, is not a self-report.** Same shape as the pad hash and
> the archive receipt: a fact, not an assertion.

## The steps

Load one phase file at a time and run it top to bottom.

| phase | steps | what it does |
|---|---|---|
| `phases/1-orient.md` | 0 · 0b · 0.8 · 1 · 1.6 · 1.6b · 1.8 | resolve and arm, open the ledger, **print the rungs by code**, load the brief in order, arm the plan, and **compact the pad before anything is compared** |
| `phases/2-reconcile.md` | 2 · 2.5 · 3 | reconcile the three horizons, mine the session for what contradicts nothing, and output the orientation block |
| `phases/3-propose.md` | 3.5 · 3.55 · 3.57 · 3.58 · 3.6 · 4 | draft every change, **ask once**, prove the handoff with a blind reader, harvest, and hand the deep pass to `/save` |

## The rules that hold across all of them

- **Silence cannot be told apart from not having looked.** Every step that finds nothing says so, in
  one line. A pass with no stated outcome is indistinguishable from a pass that never ran.
- **Ask once.** All drafting happens before the one batched round. Three separate gates is how a
  check-in becomes babysitting, and a skill that stops three times gets skipped entirely.
- **Draft the concrete edit, never a bare verdict.** *"The plan looks stale"* is not a proposal. Produce
  the actual change. Even when you are not confident, pair the doubt **with** a drafted edit and ask.
- **Every verdict that comes from a tool comes from its exit code, never from your reading.** A model
  cannot report on its own compliance — it will accurately restate a rule it is simultaneously
  breaking. Quote the token.
- **`CANNOT-READ` is never a clean result.** Notes may live on a cloud mount, and one has already
  produced a live false green here — a readability probe passed while the real read failed. Report
  unevaluated; never fine.
- **Nothing durable moves between the diff and the handoff proof.** That is the invariant the step order
  exists to buy. Test any future edit against it.

## The closed verdict sets

Each comes from a tool's exit code. **Quote the token in the receipt** — its absence is then provable.

| tool | verdicts |
|---|---|
| `checkin_open.py print` | `RUNGS <n>` 0 · `BAD-RANGE <why>` 2 · `CANNOT-READ` 4 |
| `pad_archive.py state` | `PAD-EMPTY` 0 · `PAD-DIRTY <chars>` 2 · `PAD-ARCHIVED-UNCLEARED` 3 · `CANNOT-READ` 4 |
| `gauge_check.py check` | `ONE-GAUGE` 0 · `COMPETING-GAUGES` / `OVERSIZED` / `STALE` 2 · `NO-GAUGE` 3 · `CANNOT-READ` 4 |
| `board_check.py` | `BOARD-CLEAN` 0 · `STALE-OPEN <ids>` / `RUNG-ORPHANED <id>` 2 · `NO-BOARD` 3 · `CANNOT-READ` 4 |
| the blind reader | `CAN PROCEED` · `BLOCKED — <n>` · `CONTRADICTION — <n>` · `NOT RUN` |
| `save_step_ledger.py report --ns checkin` | rc 0 clean · rc 1 a mandatory step **MISSED** · rc 2 applicability **UNKNOWN** |

⛔ **rc 2 is not a softer rc 0.** *"I could not tell"* must never be machine-readable as *"fine"*.

## What this skill needs outside its own folder

| Needed | Why | Status |
|---|---|---|
| `shared/brain_root.py` · `shared/registry.py` | where the notes are, and where this project's files are | ✅ here |
| `system/hooks/pm_flag.sh` · `plan_flag.sh` | arming the project and the plan | ✅ here |
| `system/tools/checkin/checkin_open.py` | prints the rungs mechanically | ✅ here |
| `system/tools/save/pad_archive.py` | the pad's state, archive and clear | ✅ here |
| `system/tools/save/save_step_ledger.py` | the coverage table, `--ns checkin` | ✅ here |
| `system/tools/save/pm_flag_recover.py` | recovers a flag that expired mid-session | ✅ here |
| `.claude/agents/worker.md` | the blind reader — read-only by construction | ✅ here |
| `system/tools/checkin/gauge_check.py` | check 4, the competing-gauges check | ✅ here |
| `system/tools/checkin/board_check.py` | check 5, the stale-queue check | ✅ here |
| `system/schemas/project-doc-schema.md` | the brief's sections and the compaction procedure | ✅ here |
| `system/work-altitude-doctrine.md` | how a rung is composed | ✅ here |
| `system/sops/plan-sharpening-sop.md` | the shared world-model load and the session mining | ✅ here |
| `system/sops/architecture-planning-sop.md` | the shape a planned task must carry | ✅ here |
