---
topic: [system-architecture]
title: "Organism map — the format contract (how the map is written)"
record_type: reference
desk: root
created_at: 2026-08-15
updated_at: 2026-08-15
status: active
authority: agent
---

# The organism map — the format contract

> **What this is.** The exact shape of the self-schematic's artifacts, so every element authored
> lands in one consistent format and the always-loaded map stays thin. **§2 is the live centre of
> this file** — the format of the map itself. The other sections are the surrounding contract that
> other files already cite by section number.

> ⚠ **RECONCILIATION OWED — UNVERIFIED AS OF THIS WRITING.** §2's symbol legend was written from the
> **port source** (the donor system's live map block), because when this file was authored the map
> had **not yet landed** in this repo's global `CLAUDE.md` — verified this session by
> `grep -c "System at a glance"` against it, which returned `0`. The map is being authored by a
> separate lane from a live directory listing. **The legend in §2.2 must eventually match the landed
> map BYTE FOR BYTE, and that comparison has not been run.** Whoever lands the map owes that diff.
> Until then this file is *specified-from-source*, **not** *verified-against-shipped*.
> ⛔ Do not cite §2 as confirmed.

> **Why the section numbers look gappy.** This file's `§` anchors are load-bearing: files already in
> this repo cite `map-format-specs.md §0–§1`, `§8.3` and `§8.5` by number. The numbering is therefore
> **preserved from the port source even where a section is retired**, so those citations still
> resolve. A retired section is marked and kept, never renumbered away.

---

## The altitudes — where each artifact sits

| # | Altitude / Artifact | Metaphor | File | Loads | Spec |
|---|---|---|---|---|---|
| 1 (tip) | **The organism map** | a MAP (schematic) | global `CLAUDE.md` (fenced block) | **EVERY session** | §2 |
| 2 (middle) | **The Manual** | a MANUAL (how-to) | `system/organism/manual.md` | on demand, never auto | §4 |
| 3 (base) | **Encyclopedia entry** | an ENCYCLOPEDIA | `system/organism/elements/<slug>.md`, one file each | on demand | §1 |
| 4 (ground) | **The artifact itself** | the live executable | the actual skill / hook / tool | — | — |

The map is a **regenerable slice** of the manual; the manual points DOWN to the encyclopedia; the
encyclopedia points down to the running code, which is the ground truth.

---

## §0 — THE CONTENT RULE (what goes at each altitude) — PROVISIONAL

> ⚠ **PROVISIONAL — a working rule, not law.** This is the current best rule for deciding *what*
> goes at each altitude, and it gets refined **by doing**: author a few real parts, see what the rule
> gets wrong, revise. Do not over-prescribe from here. §1–§4 lock the *structure* of the artifacts;
> this §0 is the *content* hypothesis.

**Who reads these files: the system itself** — a session looking up how to operate its own machinery.
This is self-knowledge for runtime, not human-facing documentation.

**The deciding principle:** each altitude answers a **different question**; a fact lives at exactly
**ONE** altitude; higher altitudes **POINT DOWN, NEVER COPY.**

Point-down-never-copy is the whole reason the always-loaded tip does not rot: churn-prone specifics
live only at the base, so the tip can go a long time without an edit.

- **TIP (the map, §2) — "Does this part exist, and how do I reach it?"** Pure orientation and routing.
- **MIDDLE (the manual, §4) — "How do I operate the system, and how does this part work WITH the
  others?"** The interop narrative, the seams, when-to-use-X-vs-Y. Not the internal step list.
- **BASE (the element entry, §1) — "How does this part actually work inside?"** Full mechanics, the
  honest enforcement map, every interop seam in detail.

**The escalation ladder is the confusion-resolution path.** A session unsure how its own system works
reads top-down only as far as it needs: map → manual → element → the live artifact. Each level must
be **self-sufficient at its depth** and point cleanly to the next. The ladder only works if a level
actually resolves the confusion the level above it could not.

⚠ **Measured exception:** a tip-only reader can form WRONG beliefs about enforcement posture when an
element has documented fail-open gaps — it over-trusts a bare `LIVE`. The `·gap` qualifier (§8.4b) is
the fix: a side-channel signal that depth is REQUIRED for a safety-posture question, without dragging
the gap prose up to the tip.

**The element-file DEPTH BAR — EXHAUSTIVE, not merely "enough."** The base entry is the canonical
store of **every** piece of functionality-related information about the part: every trigger, every
mode, every step, every store touched, every gate and its honest enforcement, every edge case, every
interop seam. The bar is **completeness**, not a line count — long is fine if the functionality is
real. *Register, not scope:* it is exhaustive about behaviour but written as canonical
**description** (what it does, why, how it connects), not a transcript of the artifact's executable
step-prose. The artifact remains the runtime ground truth. **When in doubt, include it.**

**The skill → encyclopedia flow** (this governs slimming any skill). A skill's content splits by
**consumer**:

- **Executable** — the machine reads it AT RUNTIME to act (e.g. write-format templates) → bundle it
  to a runtime file the skill loads at the point of use.
- **Explanatory** — the *why*, the history, the root-cause stories, read to UNDERSTAND → this is
  encyclopedia material and **graduates UP into the element file**, not into a generic reference doc
  that would just duplicate the entry.

⇒ **Slimming a skill FEEDS its encyclopedia entry.** The skill keeps only what it must execute; the
"why" migrates to the base.

## §1 — ENCYCLOPEDIA ENTRY (the BASE altitude) — LOCKED

**One file per load-bearing element at `system/organism/elements/<slug>.md`.**

The locked format:

- **Frontmatter** — `element` · `subsystem` · `altitude` · `maturity_label` · `generated_from` (the
  list of live artifacts the entry was traced from) · `record_type: organism-element`.
- **A header + one-line gist**, and the ELEMENT ladder legend line (§8.2).
- **An `## AUTHORED` block — human-only.** Trigger · the hand-off chain `actor → port → store → gate`
  · ports touched · outcome · `generated_from` · enforcement points · intent / current-vs-target ·
  **INTEROP SEAMS** (typed, per §8.3) · **GAPS**.
  - **`GAPS` is REQUIRED** whenever a fail-open bypass is documented in code or in a prior audit. It
    is the **sole** source from which the `·gap` marker is derived (§8.4b) — **no `GAPS` ⇒ no `·gap`.**
- **An `## AUTO-COMPUTED` block — machine-only.** `maturity_label` · `last_checked` · `check_detail`,
  written **only** by the label checker.

⛔ **Never hand-write a maturity label.** Labels are machine-owned; recompute them with the label
checker (`system/tools/organism/label_checker.py write-labels`). A hand-written `LIVE` is the exact
failure the write-guard on this tree exists to prevent.

**The detail lives HERE, in its own file — NOT inside the manual.** The manual only points down.

## §2 — THE MAP (the TIP) — the every-session view ★ THE LIVE CENTRE OF THIS FILE

> ⛔ **CHOSEN BY MEASUREMENT, NOT ARGUMENT — do not redesign it.** The map's shape was settled on
> 2026-08-03 by two nights of sealed-agent scoring, 58 probes on the final night, against every
> structural alternative. **Every alternative lost:** signposting down to the manual, deleting the
> manual, splitting the manual, tagging the element files, putting search-strings in the map, and
> carrying no map at all. If you find yourself improving the format from taste, stop — the idea you
> just had is probably one of the ones that already lost. This section documents the format so new
> entries match it; it does not open the format for revision.
>
> ⚠ The cost deltas from that run are **DIRECTIONAL, not precise** (a replicate measured 2.2×
> within-cell variance at n=1). The **categorical** results are the solid part: deleting the manual
> loses two answers outright, and every arm scored worse.

### §2.0 — What the map is

**The map is not a standalone file.** It is a block of text living **inside the global `CLAUDE.md`**,
under a `## System at a glance — the organism map` heading. It loads on **every session**, which is
exactly why it is dense and terse: it pays rent in every context window.

**Its one job is ROUTING** — take a thing you might want to do, and hand you the
`system/organism/elements/<slug>.md` file that actually explains it.

**Measured size of the port source** (the donor's live block, this session): **51 lines**
sentinel-to-sentinel, **67 lines** counting from the `##` heading through the closing sentinel
(which includes the provenance blockquote), of which **24 are routing entries** — the lines carrying
the ` | ` separator. *(A prior working note recorded "~69 lines"; measured here at 67/68 depending on
where the boundary is drawn. The approximate figure was close, not exact.)*

### §2.1 — The sentinels: the block is machine-delimited

```
<!-- ORGANISM v1 --> files = system/organism/elements/<name> · @ you start it · ~ scheduled, unattended · ! fires unasked
...
<!-- END ORGANISM -->
```

Two things that are easy to get wrong:

1. **The legend shares the opening sentinel's line.** `<!-- ORGANISM v1 -->` is followed by a space
   and then the legend text — it is **not** on its own line. Anything regenerating the block must
   reproduce that.
2. **`v1` is a version token**, so the block can be found and replaced programmatically. Bump it only
   if the block's *structure* changes — which, per the ruling above, it should not.

Anything **outside** the sentinels (the `##` heading, the provenance blockquote) is not part of the
regenerable block.

### §2.2 — The SYMBOL LEGEND

⚠ Subject to the byte-for-byte reconciliation owed at the top of this file. These are the symbols the
**port source** actually uses, extracted from it rather than recalled:

| Symbol | Meaning | Count in the source block |
|---|---|---|
| `@` | **you start it** — a human act begins it | 16 lines |
| `~` | **scheduled, unattended** — runs on a timer, nobody present | 3 lines |
| `!` | **fires unasked** — it triggers itself in response to something | 6 lines |
| `⚠` | **a warning** — read this before trusting what is around it | 1 line |
| `-` | a bullet, in the `NOT BUILT` section only | 4 lines |
| *(space)* | a **continuation line** of the entry above it | 16 lines |

The legend line itself is canonical wording and is reproduced exactly:

```
files = system/organism/elements/<name> · @ you start it · ~ scheduled, unattended · ! fires unasked
```

The separator is a **middle dot with spaces** (` · `) — not a pipe, not a comma.

**A second, nested use of `!`.** ⚠ `!` appears in **two** roles and they are not the same thing. As
the **first character of a line** it means *fires unasked*. Indented **inside a continuation block**
it marks a **nested sub-point** that qualifies the entry above it — a caveat sharp enough to earn its
own line. Both uses are live in the source. Do not "unify" them, and do not introduce the nested use
on a new entry unless the caveat genuinely warrants it.

### §2.3 — The ONE-LINE CRUDE-SIMPLIFICATION RULE

This paragraph sits immediately under the legend. It is **not decoration** — it is the instruction
that makes every terse line below it safe to read:

```
⚠ CRUDE SIMPLIFICATIONS — a DOOR, not a DEFINITION. Each line names the COMMONEST reason only; every
part does considerably more than its line says. NEVER answer "what can X do?" from this page — open
elements/<slug>.md, the exhaustive source. If this map is your only source, you are under-informed by design.
```

What it obligates you to, when you write a new line:

- **Name the COMMONEST reason only.** Not the full capability, not the interesting edge case, not the
  most technically precise framing — the reason someone will *most often* want this part. One reason.
  If two are genuinely tied, that is two entries, not one crowded line.
- **Accept that the line is incomplete, and do not fix it.** Every part does considerably more than
  its line says. That gap **is the design**, not a defect. Widening lines to close it is how a map
  bloats into a second manual — one of the alternatives that lost.
- **Under-informing is deliberate.** A reader whose only source is the map is *supposed* to be
  under-informed, because the line's job is to make them open the element file. A line complete
  enough to answer from is a line that has stopped routing.

### §2.4 — A DOOR, not a DEFINITION

This is the most load-bearing sentence in the block and it survives verbatim into any port:

> **NEVER answer "what can X do?" from this page — open `elements/<slug>.md`, the exhaustive source.
> If this map is your only source, you are under-informed by design.**

The distinction the architecture rests on:

- **The map ROUTES.** It gets you to the right door and stops.
- **`system/organism/elements/<slug>.md` DEFINES.** Exhaustive, source-traced (§1).
- **`system/organism/manual.md` EXPLAINS how the parts combine** — and holds rules that live in no
  element file at all. It is **LOAD-BEARING**; deleting it was one of the measured alternatives and
  it lost two answers outright.

An agent that answers a capability question from the map alone has **skipped the source**, and will
be confidently wrong at exactly the rate §2.3 predicts.

### §2.5 — Entry anatomy: the bullet shape

Every routing entry is one line in five parts:

```
<symbol> <trigger>   <plain-English gist> | <element>.md[ <element>.md] — <optional caveat>
```

| Part | Rule |
|---|---|
| **symbol** | one of `@` `~` `!`, per §2.2. Column 1. |
| **trigger** | how it is invoked: a slash command (`/save`), a natural phrase (`open the window`), a parenthetical for things you do not invoke (`(automatic)`, `(no command)`, `(config)`, `(open the file)`), or a literal address. |
| **gist** | lower-case, plain English, **the commonest reason only**. §2.3 governs this part. |
| **separator** | ` \| ` — space, pipe, space. Non-negotiable: it is what makes entries greppable. |
| **element(s)** | **bare filename with `.md`, no directory path** — `save.md`, not `elements/save.md`. Multiple targets are **space-separated** on one line. |
| **caveat** | optional, introduced by an **em dash** ` — `. Lower-case running prose. Reserved for the thing that gets misunderstood if left unsaid. |

**Worked example** — an entry that exists in the source:

```
@ /read    pull the right memory in, no blind search | read.md
```

**With multiple element targets:**

```
! (automatic)   a web page or email body is read safely | safe-reader-plane.md ingest-gate.md
```

**With a caveat and a continuation line:**

```
! (automatic)   the system files a ticket on ITSELF, ranked | hospital.md — detectors write ONE comparable
                finding; the session-start line speaks it unasked. DETECTS+RANKS, never fixes.
```

**Naming the literal command is the thing that made this format win.** In the first bake-off round
every variant hit a 2-of-5 ceiling, and 25 of 25 agents named the same cause: *"the map names the
door, not the handle."* Where a command exists, the entry types it out.

**Continuation lines.** A caveat too long for one line wraps onto a **space-indented continuation
line**, indented to sit under the gist column of its parent. Continuation lines carry **no symbol** —
the leading space *is* the signal that the line belongs to the entry above. 16 of the source block's
lines are continuations, so this is a normal shape, not an exception.

**Column alignment is per-cluster, not global.** The gist column is padded to align **within a run of
consecutive related entries**, and realigns at each new cluster. It is not one global column across
the whole map — a long trigger widens its own cluster and leaves the others alone. Match the cluster
you are joining; do not reflow the map.

**Pointing at something that is not an element.** Occasionally the right destination is not an
element file. When that happens, **say so on the line** — mark it explicitly and state the division
of labour, e.g. a pointer to the canonical structure doc carries `— NOT an element; the canonical
structure doc. this page ROUTES; that one EXPLAINS.` Never leave a non-element path sitting
unlabelled in the target slot; a reader will go looking for it in `elements/` and find nothing.

### §2.6 — How a NEW element gets added to the map

**Prerequisite: the element file exists first.** `system/organism/elements/<slug>.md` is authored and
source-traced (§1) **before** a map line points at it. The map never promises a door that is not
there.

Then:

1. **Decide the symbol** — does a human start it (`@`), a timer (`~`), or does it fire itself (`!`)?
   If the honest answer is "all three," pick the commonest, per §2.3.
2. **Write the trigger** — the literal thing a person types, or the parenthetical for things they do
   not invoke. Where a command exists, **name the command**.
3. **Write the gist in one line, commonest reason only.** Lower-case, plain English. Resist
   completeness; that instinct is the failure mode this format was measured against.
4. **Append ` | <slug>.md`** — bare filename, no path.
5. **Add a caveat only if omitting it causes a predictable misread.** Not for interest, not for
   completeness.
6. **Place it in the symbol cluster it belongs to** — `@` with `@`, `!` with `!`, `~` with `~`, and
   inside a cluster, related entries sit adjacent. **Ordering is by kinship, not alphabetical.**
7. **Align the gist column to the cluster you joined**, and leave the rest of the map untouched.
8. **Stay inside the sentinels** (§2.1).
9. **If the part is genuinely NOT built,** it belongs in the `NOT BUILT` section instead (§2.7).

⚠ **A new element does not automatically earn a map line.** The map is a routing budget every session
pays for. If nobody would go looking for the part by name, the element file is enough and a map line
is cost with no traffic.

### §2.7 — The tail sections

Two blocks close the map. Both are structural, not appendices to be trimmed.

**The aggregate line.** Where many scheduled jobs would otherwise become many near-identical `~`
entries, they collapse into **one** line naming the count, the classes in `{braces}`, how you learn
each one ran, and a pointer to the full manifest. One line, not N.

**`NOT BUILT`.** A short `-` bulleted list under the header:

```
NOT BUILT — admissions, not omissions. knowing now beats inferring a connection that isn't there:
```

⭐ **This is the map's sharpest feature and the easiest to delete by accident.** Its purpose is
preventing a reader from *inferring a connection that does not exist* — the specific failure where an
agent sees two parts on one page and assumes something joins them. Each bullet names the absent
capability plainly and says what you must therefore carry by hand. When a `NOT BUILT` item is later
built, it **moves up** into the routing entries; it is never simply deleted.

## §3 — [NOT APPLICABLE HERE] Per-desk cheat-sheets

The port source specifies a second fenced block per desk, inside each `desks/{desk}/CLAUDE.md`,
loading only on that desk's launch.

⛔ **This repo has no `desks/` tree** (verified this session: `ls -d desks` → *No such file or
directory*). The section number is kept so §4 and §8 do not renumber, and so the absence is a
recorded admission rather than a silent gap. If a desk layer is ever introduced here, the rule that
governed it was: an element is desk-altitude **iff** it is relevant only inside that desk and would
never be used in another; an element shared by *some* desks is duplicated into each, never promoted
to the system map.

## §4 — THE MANUAL (the MIDDLE altitude) — `system/organism/manual.md`

**File + load:** `system/organism/manual.md`; on disk, opened on demand, **never auto-loads.**

**What it is:** a medium-density **how-to guide** describing how the whole system works and operates
**together** at roughly 5,000 ft — how the parts combine into outcomes. It does **not** hold the
per-element weeds (that is §1) and it is **not** a bare pointer-list. It points DOWN to the element
entries for detail.

⚠ **The manual is LOAD-BEARING.** It holds rules that exist in no element file. Deleting it was a
measured alternative and it lost two answers outright. Do not treat it as a redundant middle layer.

**Shape:**

1. **The maintenance + honesty-label rules** — the human-AUTHORED vs machine-AUTO-COMPUTED split, and
   the LIVE / PARTIAL / TARGET criteria.
2. **The ranked element INDEX** — each line `element : [source] · LABEL → elements/<slug>.md`, a
   pointer DOWN. Trivial or dormant parts get **only** this index line (§8.5).
3. **The connective narrative** — the 5,000-ft "how it all works together" prose, synthesising the
   interop across elements.

This file and the manual are the system's own attack-surface map, which is why a PreToolUse
write-guard protects them (§6).

## §5 — [RETIRED] The token budget

⛔ **RETIRED 2026-08-03. The token meter is deleted; do not rebuild it.**

Three reasons, in the order they mattered:

1. **Nothing ever called it** — no cron, no hook, no skill, no runner. It was referenced only by this
   document.
2. **The enforcing control already exists and fires** — `guard_canon_write.sh` (PreToolUse) blocks an
   over-800-token canon write, and was watched blocking and allowing on the day of retirement.
3. **It measured the wrong denominator** — not through a defect, but because the question changed.
   Its scope was deliberately "the map's cost is the generated region, not the whole `CLAUDE.md`,"
   which was right for *"is the map too fat?"*. After the map was pulled and re-sited, the meter
   reported `740 / 1500 ✓ within budget` while the real always-loaded payload measured **24,649
   tokens against a ~20,000 ceiling**. Two advisors reached opposite conclusions from that, one
   reading the payload and one reading the meter; both honest, different questions.

**The map needs no meter: it is human-gated.** The write-guard (§6) blocks a wholesale `Write` to the
map files, and re-injecting the tip is an explicit human-in-the-loop stop.

⚠ The 800-token rail stops **new** bloat; it does not reduce an existing overage. Large grandfathered
reference docs predate it. That is a parked decision, not a missing tool.

## §6 — Guardrails as gates (checkable, not prose)

1. **⛔ There is no prescribed box or entry count.** A count cap was explicitly ruled out on
   2026-08-03: what is prescriptive is that the map be **very thin and light and within roughly the
   budget set for it** — the best map that fits. Do **not** re-introduce a count.
2. **Same-commit rule** — a map file is updated in the **same commit** as the code it cites.
   Checkable at author time; enforced socially, surfaced mechanically.
3. **All map files git-tracked** — checkable with `git ls-files`, covering the manual, this spec, and
   the `CLAUDE.md` that hosts the fenced block. A map file that is not git-tracked cannot be `LIVE`,
   by the same rule that applies to guards.
4. **The write-guard** — a PreToolUse hook blocks a **wholesale `Write`** (full-file overwrite) of the
   manual, this spec, and every `elements/*.md`. Surgical `Edit` calls pass through, and that is the
   normal authoring path. The reason is narrow and worth stating: the map is the system's own
   attack-surface description **and** the label checker's ground truth, so a single injected
   instruction must not be able to replace it, or flip every label to `LIVE`, in one shot.
   ✅ **Status in this repo, 2026-08-15: ENFORCED.** `system/hooks/guard_organism_map.sh` is present,
   registered in `.claude/settings.json` under `PreToolUse` / `matcher: "Write"`, and was fired through a
   real session launched from this repo — it refused a `Write` to `system/organism/elements/` and the deny
   text reached the model in full. A surgical `Edit` to the same path was ALLOWED in the same run, and an
   unrelated `Write` passed untouched. Suite: `system/hooks/tests/test_organism_map_guard.sh` (25 cases,
   ALLOW first). ⚠ Two limits are stated rather than hidden: a Bash write (`>`, `tee`, heredoc) is NOT
   intercepted — that is the deliberate human escape hatch — and `label_checker.py write-labels` writes
   through Python, so it is not intercepted either, which is correct because it is the sanctioned writer.
   ~~⚠ **Status in this repo: the guard is NOT present here** (verified this session: unruled — absent).
   The guarantee described in this clause is currently **unenforced locally**. On no ship list, awaiting a
   decision: a debt, not a pass.~~ ← struck 2026-08-15. It was true when written. The guard had been
   dropped on the sole ground that `system/organism/` did not exist here; Phase 9 landed the tree the same
   day, which killed the premise and left a guarantee documented in six shipped files and enforced in none
   — the defect class house rule `T9.11b` (`system/build-rules-index.md`) is named for. The port closed it.

## §7 — [HISTORICAL] The sign-off gate

The port source records a human-in-the-loop gate: the format specs, the token number and the
guardrails were signed off before element authoring began. Kept for provenance. The gate has already
been passed; it is not a live blocker.

---

## §8 — NAVIGATION + THE TYPED-SEAM FORMAT — the authoritative fill-in contract

> This section supersedes the loose format sketches above for the MAP-line and MANUAL-entry shapes.
> It is the contract every element author fills.

### §8.1 — The ONE-SLUG rule (what makes it navigable by a machine)

Each element has **ONE slug** — its own handle, lowercase-kebab, drawn from the command / hook / tool
name. That **same slug** is:

- the MAP target,
- the MANUAL `## <slug>` header,
- the filename `elements/<slug>.md`.

A machine greps the slug and follows it straight down the ladder. **The only hard match required is
MAP-anchor ↔ MANUAL-header**; the manual always states the explicit `→ elements/<slug>.md` path, so a
filename that differs from a functional descriptor is fine — the path resolves it, not a guessed name.

⛔ **Functional descriptors are GLOSS TEXT, never the slug.** "session knowledge → durable memory" is
a gloss; it is not an identifier. The map does not rename the element.

### §8.2 — The LADDER legend (one line atop every file)

- **MAP:** `> LADDER: MAP (orientation). deeper → manual.md ; mechanics → elements/<slug>.md`
  *(keep it this short — it rides every session)*
- **MANUAL:** `> LADDER: MANUAL (how it works together). up → the map ; full mechanics → elements/<slug>.md`
- **ELEMENT:** `> LADDER: ELEMENT (full mechanics). up → manual#<slug> ; ground truth → the live artifact (generated_from)`

⚠ **Coverage is partial in this repo, measured this session:** ~~31 of the 42 element files carry a
`LADDER:` line. The remaining 11 do not.~~ ⚠ **CORRECTED 2026-09-01** — re-derived both numbers this
session: `system/organism/elements/` holds **44** `.md` files (`ls -1 system/organism/elements/ | wc -l`,
all `.md`, 0 non-`.md`), not 42, and of those, **33** carry a `LADDER:` line
(`grep -l "LADDER:" system/organism/elements/*.md | wc -l`), leaving **11** that do not — the
missing-count held, the denominator was stale. Wording also varies slightly (some entries end
`→ the live artifacts above` rather than naming `generated_from`). Stated as a finding, not
retroactively enforced.

### §8.3 — The seam-verb CLOSED vocabulary (pick from these; never invent)

`SHARES` (shared subroutine or state) · `WRITES→` (writes a store another consumes) · `FEEDS`
(produces data a consumer reads) · `PROPOSES` (hands off for human-gated promotion) · `KEYS-OFF`
(reads shared identity or config) · `CHAINS` (composes in sequence with) · `COMPLEMENTS` (parallel,
non-redundant) · `SYNCS` (must stay in lockstep with) · `TRIGGERS` (fires) · `READS` (reads from) ·
`GUARDED-BY` (the hook that walls on it).

**Closed means closed.** A new verb is a change to this contract, not an authoring choice.

### §8.4 — [RETIRED] The condensed arrow-list map line

⛔ **DO NOT BUILD FROM THIS. It was ruled out, then measured failing twice.**

The retired shape prescribed a flat edge list:

```
<slug> → <box> : <what flows>   [in | out | internal]
<slug> : <verb-phrase>   · <LABEL>[·gap]   → manual#<slug>
```

Ruled out as `v1` in the 2026-08-03 planning: *"DO NOT BUILD IT AS A FLAT EDGE LIST. The current
map's format is what scored 0 of 5 on your routing tests."* Then re-measured independently in the
bake-off: rebuilt faithfully to this spec as a variant, it scored **0 of 5** and produced the most
fabrications of any arm.

**The inherent defect two agents found independently:** subsystem junctions appear as flow **nodes**
with no gloss and no file to open — *"the single most relevant thing to this task has no doorway."*
**An arrow list names junctions; a routing table cannot, because every line must END somewhere.**

**▶ The measured replacement is §2** — goal-phrased routing lines, `<what you want> | <element>.md`,
each carrying a who-acts marker and, where one exists, the literal command to type.

### §8.4b — The `·gap` label qualifier

A maturity label states that the **primary** enforcement mechanism fires. It does **not** say "no
holes." A cold-session audit found that a tip-only reader reads `LIVE` and **over-trusts** it, missing
documented fail-open conditions.

**The fix:** append **`·gap`** to the label — on both the map gloss and the manual header — when the
element has a documented fail-open bypass that would make a tip-only reader misjudge enforcement
posture. `LIVE·gap` = *"the guard fires on the primary vector AND a documented bypass exists — drill
to the element for scope."* The gap **prose** stays in the element file's `GAPS` (§1); the marker is
only a side-channel "stopping here is not sufficient for a safety-posture question."

- **Bar for `·gap`:** only a documented fail-open in the element's `GAPS` / current-vs-target with
  real blast radius. Formatting or statistical-completeness nuances do **not** qualify. It is
  **DERIVED** from `GAPS`, never hand-judged — **no `GAPS` list ⇒ no `·gap`.**
- **Decision test:** *"if a session reads only the gloss and acts on it, would it form a WRONG belief
  about this element's enforcement posture?"* Yes → `·gap`. No (the gap is an implementation detail,
  not a posture question) → omit.
- **System-class gap exclusion:** some gaps are system-wide, not element-specific — e.g. a hook plane
  that fires on `Write|Edit` only, so Bash file-writes bypass it by accepted design. Do **not** re-list
  an inherited system-class gap per element, or derive `·gap` from it, unless this element's blast
  radius materially exceeds the system baseline. Otherwise the marker stops discriminating.
- **The `(honor)` tag:** an optional gloss tag signalling that the element's **primary** behavioural
  contract — its main path, not a bypass — is prose only, with no blocking hook enforcing it.
  Distinct from `·gap` (a bypass of an otherwise-enforced path) and orthogonal to LIVE/PARTIAL/TARGET
  (which measure completeness, not mechanism). Use sparingly, only where the MAIN promise is
  honour-system.

⚠ **Scope note, measured:** the winning map format (§2) carries **no label column at all** — its
entries are goal-phrased routing lines, not `name · LABEL` glosses. So `·gap` and `(honor)` are live
at the **manual and element** altitudes, and currently have **no expression on the map**. If a label
column is ever reintroduced to the tip, these rules govern it.

### §8.5 — MANUAL entry format (index line + TYPED INTEROP SEAM LIST)

**Rule: compress WORDS, never SEAMS — every interaction gets a line.**

Size scales with importance: **critical 30–50 lines · mid 12–20 · trivial = index line + 1–2 seams.**
Genuinely trivial or dormant parts get **only the index line**, never a `## <slug>` section. Each
seam's `<other-slug>` resolves via the manual's index (slug → `elements/<slug>.md`).

```
## <slug> · <trigger>   [<LABEL>[·gap]]   → elements/<slug>.md
<one-line purpose>. <one-line by-design nuance, if any>.

INTEROP:
  <VERB>   <other-slug>   · <what flows / why, one line>
  ...one line per seam, ALL of them...
  GUARDED-BY  <hooks>   · the walls that fire here
```

The element entry's INTEROP SEAMS use these **same** typed verbs (§8.3), so the manual entry is a
copy-and-shrink of them. That is the automation seed: a future dumb script can generate the manual
line from the element file.

### §8.6 — The escalation is progressive disclosure

A machine unsure how its own system works reads top-down only as far as it needs: **MAP** (does it
exist, how do I reach it) → **MANUAL** (how it operates with the others) → **ELEMENT** (full
mechanics) → **the live artifact** (ground truth). Each level is self-sufficient at its depth and
points cleanly DOWN. Higher levels **point down, never copy** — the stability gradient: churn-prone
specifics live only at the base.

---

## Checklist for a new map entry

- [ ] The element file `elements/<slug>.md` exists and is source-traced (§1).
- [ ] Symbol is one of `@` `~` `!` and reflects the **commonest** invocation (§2.2).
- [ ] Gist is one line, lower-case, **commonest reason only** — not the full capability (§2.3).
- [ ] Where a command exists, the entry **names the command**, not just the door (§2.5).
- [ ] Separator is exactly ` | `; the target is a **bare filename with `.md`**, no path.
- [ ] Caveat exists only if omitting it causes a predictable misread.
- [ ] Any continuation line is space-indented under the gist column and carries no symbol.
- [ ] Entry sits in its symbol cluster, adjacent to its kin; column aligned to **that cluster**.
- [ ] Entry is inside `<!-- ORGANISM v1 -->` / `<!-- END ORGANISM -->` (§2.1).
- [ ] The legend line, the ⚠ CRUDE SIMPLIFICATIONS paragraph, and the `NOT BUILT` header are
      unchanged.
- [ ] The slug is identical across map, manual header and filename (§8.1).
- [ ] No maturity label was hand-written (§1).
- [ ] You did not "improve" the format (§2).
