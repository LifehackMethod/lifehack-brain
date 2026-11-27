---
title: "Organism map — the format contract: history log"
what: "Retired and moved text from map-format-specs.md, kept verbatim and dated so nothing is lost. Not read in normal use."
read_in_normal_use: false
base_file: "canon/map-format-specs.md as frozen 2026-11-14 (freeze-2026-11-14, V2 HEAD 0037ccb)"
created: 2026-11-14
status: "draft — lands with the fine-china edit pass, round three"
---

# Organism map — the format contract: history log

Each entry is one passage moved out of the document on 2026-11-14 (round three 'lowerbooks'). Line numbers are the frozen base's. The original is copied word for word inside each fenced block. Append-only.

## 2026-11-14 · MOVE · lines 19-26 · G3-20

- Reason: factual fix (canon): K41 — the legend line was byte-checked against the landed map 2026-11-13; Batch 4 item 3 for the move.

~~~~
> ⚠ **RECONCILIATION OWED — UNVERIFIED AS OF THIS WRITING.** §2's symbol legend was written from the
> **port source** (the donor system's live map block), because when this file was authored the map
> had **not yet landed** in this repo's global `CLAUDE.md` — verified this session by
> `grep -c "System at a glance"` against it, which returned `0`. The map is being authored by a
> separate lane from a live directory listing. **The legend in §2.2 must eventually match the landed
> map BYTE FOR BYTE, and that comparison has not been run.** Whoever lands the map owes that diff.
> Until then this file is *specified-from-source*, **not** *verified-against-shipped*.
> ⛔ Do not cite §2 as confirmed.
~~~~

## 2026-11-14 · MOVE · lines 344-354 · G3-25

- Reason: Settled (b) "map: settled" (no per-desk copies, K41); K9 (desks are live) — the old desk-duplication clause.

~~~~
## §3 — [NOT APPLICABLE HERE] Per-desk cheat-sheets

The port source specifies a second fenced block per desk, inside each `desks/{desk}/CLAUDE.md`,
loading only on that desk's launch.

⛔ **This repo has no `desks/` tree** (verified this session: `ls -d desks` → *No such file or
directory*). The section number is kept so §4 and §8 do not renumber, and so the absence is a
recorded admission rather than a silent gap. If a desk layer is ever introduced here, the rule that
governed it was: an element is desk-altitude **iff** it is relevant only inside that desk and would
never be used in another; an element shared by *some* desks is duplicated into each, never promoted
to the system map.
~~~~

## 2026-11-14 · MOVE · lines 426-431 · G3-32

- Reason: Batch 4 item 3 (struck chains to history).

~~~~
   ~~⚠ **Status in this repo: the guard is NOT present here** (verified this session: unruled — absent).
   The guarantee described in this clause is currently **unenforced locally**. On no ship list, awaiting a
   decision: a debt, not a pass.~~ ← struck 2026-08-15. It was true when written. The guard had been
   dropped on the sole ground that `system/organism/` did not exist here; Phase 9 landed the tree the same
   day, which killed the premise and left a guarantee documented in six shipped files and enforced in none
   — the defect class house rule `T9.11b` (`system/build-rules-index.md`) is named for. The port closed it.
~~~~

## 2026-11-14 · MOVE · lines 469-474 · G3-34

- Reason: Batch 4 item 3 — struck count and the 2026-09-01 correction; replaced by the 2026-11-13 count (K41, K42).

~~~~
⚠ **Coverage is partial in this repo, measured this session:** ~~31 of the 42 element files carry a
`LADDER:` line. The remaining 11 do not.~~ ⚠ **CORRECTED 2026-09-01** — re-derived both numbers this
session: `system/organism/elements/` holds **44** `.md` files (`ls -1 system/organism/elements/ | wc -l`,
all `.md`, 0 non-`.md`), not 42, and of those, **33** carry a `LADDER:` line
(`grep -l "LADDER:" system/organism/elements/*.md | wc -l`), leaving **11** that do not — the
missing-count held, the denominator was stale. Wording also varies slightly (some entries end
~~~~

## 2026-11-14 · MOVE · lines 533-537 · G3-27

- Reason: Batch 6 item 1 — the `(honor)` tag retired; "LIVE (honor)" is not a legal label; TARGET dropped.

~~~~
- **The `(honor)` tag:** an optional gloss tag signalling that the element's **primary** behavioural
  contract — its main path, not a bypass — is prose only, with no blocking hook enforcing it.
  Distinct from `·gap` (a bypass of an otherwise-enforced path) and orthogonal to LIVE/PARTIAL/TARGET
  (which measure completeness, not mechanism). Use sparingly, only where the MAIN promise is
  honour-system.
~~~~


## 2026-11-27 - reason: C4 landing item 1: altitudes table + closing paragraph

~~~~
| # | Altitude / Artifact | Metaphor | File | Loads | Spec |
|---|---|---|---|---|---|
| 1 (tip) | **The organism map** | a MAP (schematic) | the harness brief the plugin delivers (`CLAUDE.md` at the plugin root, a fenced block) | **EVERY session** | §2 |
| 2 (middle) | **The Manual** | a MANUAL (how-to) | `canon/manual.md` | on demand, never auto | §4 |
| 3 (base) | **Encyclopedia entry** | an ENCYCLOPEDIA | `system/organism/elements/<slug>.md`, one file each | on demand | §1 |
| 4 (ground) | **The artifact itself** | the live executable | the actual skill / hook / tool | — | — |

The map is a **regenerable slice** of the manual; the manual points DOWN to the encyclopedia; the
~~~~

## 2026-11-27 - reason: C4 landing item 1: section 8.6 body

~~~~
A machine unsure how its own system works reads top-down only as far as it needs: **MAP** (does it
exist, how do I reach it) → **MANUAL** (how it operates with the others) → **ELEMENT** (full
mechanics) → **the live artifact** (ground truth). Each level is self-sufficient at its depth and
points cleanly DOWN. Higher levels **point down, never copy** — the stability gradient: churn-prone
~~~~

## 2026-11-27 - reason: C4 landing item 1: altitudes closing paragraph (rest)

~~~~
encyclopedia points down to the running code, which is the ground truth.
~~~~

## 2026-11-27 - reason: C4 landing item 1: section 8.6 body (rest)

~~~~
points cleanly DOWN. Higher levels **point down, never copy** — the stability gradient: churn-prone
~~~~

## 2026-11-27 - reason: landing the four-level altitudes table, approved 2026-11-27

~~~~
| # | Altitude / Artifact | Metaphor | File | Loads | Spec |
|---|---|---|---|---|---|
| 1 (tip) | **The organism map** | a MAP (schematic) | the harness brief the plugin delivers (`CLAUDE.md` at the plugin root, a fenced block) | **EVERY session** | §2 |
| 2 (middle) | **The Manual** | a MANUAL (how-to) | `canon/manual.md` | on demand, never auto | §4 |
| 3 (base) | **Encyclopedia entry** | an ENCYCLOPEDIA | `system/organism/elements/<slug>.md`, one file each | on demand | §1 |
| 4 (ground) | **The artifact itself** | the live executable | the actual skill / hook / tool | — | — |

The map is a **regenerable slice** of the manual; the manual points DOWN to the encyclopedia; the
~~~~

## 2026-11-27 - reason: landing the four-level progressive disclosure, approved 2026-11-27

~~~~
A machine unsure how its own system works reads top-down only as far as it needs: **MAP** (does it
exist, how do I reach it) → **MANUAL** (how it operates with the others) → **ELEMENT** (full
mechanics) → **the live artifact** (ground truth). Each level is self-sufficient at its depth and
points cleanly DOWN. Higher levels **point down, never copy** — the stability gradient: churn-prone
~~~~

## 2026-11-27 - reason: landing the altitudes closing paragraph, approved 2026-11-27

~~~~
The map is a **regenerable slice** of the manual; the manual points DOWN to the encyclopedia; the
encyclopedia points down to the running code, which is the ground truth.
~~~~

## 2026-11-27 - reason: landing the progressive disclosure tail, approved 2026-11-27

~~~~
points cleanly DOWN. Higher levels **point down, never copy** — the stability gradient: churn-prone
specifics live only at the base.
~~~~
