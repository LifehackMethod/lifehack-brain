---
skill: archivist-declutter
description: "Line-level leanness audit of the always-loaded layers (global/root/desk CLAUDE.md + canon). Use on \"/archivist-declutter\" when always-loaded files feel bloated. Propose-only."
shape: interactive-workflow
status: active
topic: [archivist]
summary: Line-level sink/split audit of the always-loaded layers against each home's declared intent (leanness immune system).
---

## Intent (§0.5)
**User outcome:** Always-loaded files — the ones that load every single session — accrete weight silently: a desk-specific rule drifts into global, a specialty fact sits in a canon that loads even when irrelevant. Over time this bloats the summit and degrades compliance. archivist-declutter is the standing counter-pressure: it tests every line in those scarce layers against each home's admission bar and surfaces the ones that don't earn their altitude. **Bar:** "the always-loaded layers stay lean — every line there genuinely needs to be there for every session."
**Role:** the precision line-auditor — high precision over recall (a false sink wastes the human's time; a missed line is cheap). Three failure modes only: SINKER (too specific for its altitude), SEAM-DUP (same rule in two layers), SPLIT-CANDIDATE (a home grown broad enough to split). No numeric scoring — the bar is the home's English intent. One extra gate: if a hook depends on prose being present at altitude, flag dep-gate:KEEP rather than sink it. The only write is the grouped queue a person then rules on (see the handoff note at the foot of this file; `/archivist-review` is retired and not shipped here).

# archivist-declutter

> **Content root (Drive).** Every relative `state/…`, `records/…`, `canon/…`, `desks/…` path in this
> skill is **content** — it resolves under the Drive root
> `<notes>/`, never the code
> clone. Sessions launch from the clone now, so resolve these against that absolute Drive root.

## Paths (set once)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```
Documentation consistency with the rest of this skill family — `<notes>` above is `$DATA`, resolved
here rather than left for a session to work out on its own initiative.

The **line-level sink/split audit** — the archivist's harness-leanness immune system. Re-tests existing lines in
the always-loaded layers (global + root + desk `CLAUDE.md` / canon) against each home's declared `intent`, and
**proposes** the ones that no longer earn their altitude (sink them lower) plus the homes grown fat enough to
split. READ-ONLY / PROPOSE-ONLY — it writes a review queue; a person rules on it (see the handoff note at the foot of this file — `/archivist-review` is retired); nothing
is edited here. (Part of `archivist-rebuild` — **P11**. Check **J** grown up, applied to LINES not whole desks.)

## Why this exists
Always-loaded files accrete weight with no admission discipline — a desk-specific rule creeps into global, a slab
of specialty detail sits in a desk canon that loads every session. Left alone they bloat the summit (the
lean-harness research: longer always-loaded layers → lower compliance + more tokens). This pass is the standing
counter-pressure: **pointers up high, content down low.** It does for LINES what check Q does for FILES.

## The doctrine it audits against (read these FIRST, every run)
- `system/intent-doctrine.md` — the parent law (every object declares its intent).
- `system/knowledge-altitude.md` — the admission-difficulty model (Global hardest → Deep easy; the air thins as
  you climb; "pointers up high, content down low").
- `<notes>/system/archivist/home-intents.md` — the **authored admission bars** (`intent` + optional ONE `not:` near-miss)
  for each home. This is the bar each line is judged against. (Authored law for global + 6 desks; do not second-guess
  the wording — apply it.)

## The targets (the always-loaded layers — the scarce summit space)
Only the layers that load EVERY session, where bloat is most expensive. In altitude order:
1. **Global** `~/.claude/CLAUDE.md` (the summit — loads every session, every machine, cwd-independent).
2. **Root shell** `$ROOT/CLAUDE.md` — the repo's own always-loaded brief, the one file every session opens with.
   *(This read `_Lifehack/CLAUDE.md` until 2026-08-13: a folder name from the system this came from, which exists nowhere here. There is exactly one `CLAUDE.md` in this repo and it is at the top level.)*
3. **Each desk** `<notes>/desks/{desk}/canon/current.md` (loads every conversation in that desk). *(This used to also
   target `$ROOT/desks/{desk}/CLAUDE.md` until 2026-08-16: the light desk shape here — `canon/current.md`,
   `canon/purpose.md`, `records/` only, per `docs/data-layout.md:217` — has no per-desk `CLAUDE.md`; `canon/current.md`
   is the correct, and only, always-loaded desk target.)*
Do NOT walk deep sub-folder canon here — that's "sea level, thick air, cheap" (a fat low canon is fine by design).
This pass is about the layers whose every line is paid for on every load.

## Procedure
1. **Load the doctrine + the authored bars** (the three files above). Hold each target home's `intent` + `not:` in mind.
2. **Walk each target layer line-by-line / block-by-block.** For each line ask the one altitude question:
   *"Does this line clear THIS home's admission bar — is it required to be present in EVERY session that loads this
   layer?"* Three failure modes to flag (and only flag a clear miss — high precision, like Q; a borderline line stays):
   - **SINKER** — the line is more specific than the home's bar: a desk/domain rule sitting in global, or specialty
     detail (a specific account, device, client, dated fact) sitting in a desk canon/CLAUDE.md. It belongs LOWER.
     Propose the specific lower home (a sub-folder canon, a `google-config.md`, a record) + a one-line pointer to
     leave in place if the layer still needs to know the detail exists. (This is the `not:` near-miss made concrete.)
   - **SEAM-DUP (line-level K)** — the same rule copied verbatim across two layers (e.g. a rule in both global and a
     desk CLAUDE.md). Propose: keep ONE home (the lowest layer where it's still universal), pointer in the other.
   - **SPLIT-CANDIDATE (line-level J)** — a single home grown broad enough that it holds ≥2 disjoint clusters that
     would never co-load. Propose the split that creates lower shelves for sinkers to land on. PROPOSE only — a
     split is an identity-level human call (same rule as check J).
3. **Dep-gate every sink (the hook-without-prose trap).** Before proposing to sink a rule lower, check: does a
   **hook** (`settings.json` / `system/hooks/`) depend on this rule ALSO existing as prose-at-altitude? Per the
   hook-without-prose-fallback rule, a hook-enforced catastrophic rule (auth, calendar, sheet-guard) needs its prose
   kept where it's visible — hooks don't fire outside the CLI. If sinking it would strip the only prose copy from a
   layer that must carry it, do NOT propose the sink; flag it `dep-gate: KEEP (hook-paired prose)` instead.
4. **Write the grouped queue** (don't edit anything) → `<notes>/system/logs/archivist_{YYYY-MM-DD}_declutter.md`, in the
   the standard queue shape, so whoever works it can act row by row:
   - group **SINK** (line → proposed lower home + pointer-to-leave) · group **SEAM-DUP** (line → one-home + pointer)
     · group **SPLIT** (home → proposed children). Each item: `id · layer · the line/excerpt · proposed-action ·
     altitude-verdict (why it misses the bar) · dep-gate(clear|KEEP) · risk · reversible(y)`.
   - Lead with a one-screen summary: N sinkers / N dups / N split-candidates, and the rough line-weight each layer
     could shed. If a layer is clean, say so — "global: 0 sinkers, earns every line."
5. **Stop.** Leave the queue for a person to work through (a supervised session executes the
   moves snapshot-first). This skill never moves a line.

## Rails
- READ-ONLY / PROPOSE-ONLY. Never edit a `CLAUDE.md` / canon. The queue is the only thing written.
- **High precision over recall** (Q's rule): a false sink wastes a human's time and risks stripping a needed line;
  a missed one is cheap (next pass catches it). When unsure a line misses the bar, LEAVE IT.
- **KISS — plain-text + LLM judgment. NO numeric scoring, no line-budget math, no thresholds.** The bar is the
  home's English `intent`; you read and judge. (Doctrine §3.)
- **Never sink a hook-paired prose rule out of the layer that must carry it** (step 3). Belt-and-suspenders holds:
  the prose at altitude is half the protection.
- Crown-jewel caution: global `~/.claude/CLAUDE.md` and the `How to Respond` block are the reader-owned. Propose sinks
  against them with extra conservatism and NEVER touch the `How to Respond` example text.

## Reference
- Formerly consumed by a review skill that has since been retired (SINK folded into its ROUTE/RELOCATE group; SPLIT into SCOPE). Bars:
  `<notes>/system/archivist/home-intents.md`. Doctrine: `system/knowledge-altitude.md` + `system/intent-doctrine.md`.
- Sibling focused passes: `skills/archivist-deepmine` (mine bodies), the Q misplaced-FILE check (charter). This is
  the misplaced-LINE pass. Plan: `<notes>/state/projects/archivist-rebuild/task_plan.md` (P11).
- The 2026-06-12 by-hand thinning pass (global 164→51, root 312→85, 6 desks, combined doctrine 422→136) is the
  manual precedent this automates — same method (separate backbone/sink/dup; grep the sink-home has it; pointer).

---

## Where the queue goes, and who acts on it

This skill **proposes and never executes.** Its output is a queue, and the queue lands at:

```
<notes>/records/proposals/archivist-{YYYY-MM-DD}-{what}.md
```

`records/proposals/` is one of the six record types, and it means exactly this: *something proposed,
waiting on a person to rule on it.*

⛔ **There is no `/archivist-review`.** The system this came from had one, and retired it on
2026-07-11 as a dead approve-then-file model — its own scheduled runner records the replacement in
one line: **the scanner just FLAGS, and the next `/save` picks it up.** So nothing here waits for a
review command that does not exist. Write the queue, say where it is, and stop. When you next run
`/save`, the open proposals are there to be dealt with.

## What this skill needs OUTSIDE its own folder

| what | where | status |
|---|---|---|
| the intent law it checks against | `system/intent-doctrine.md` | shipped |
| the altitude law it checks against | `system/knowledge-altitude.md` | shipped — 266 lines |
| the guards it inventories | `system/hooks/` | shipped |
