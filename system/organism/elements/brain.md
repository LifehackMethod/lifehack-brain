---
element: brain
title: "brain — element detail (ground/base altitude)"
subsystem: organism-integrity
altitude: base
record_type: organism-element
maturity_label: PARTIAL [provisional] (honor)
generated_from:
  - system/organism/manual.md (the whole file — the MIDDLE layer this element describes)
  - system/organism/elements/ (the BASE layer — the corpus this element belongs to)
  - system/organism/elements/label-checker.md (the honesty loop that stamps AUTO-COMPUTED labels)
  - system/organism-manual-extract.md (the one chapter extracted for the skills that cite it)
  - CLAUDE.md (the always-loaded file the TIP layer lives in)
created_at: 2026-08-15
updated_at: 2026-08-15
status: draft
authority: user
---

# brain — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#brain ; ground truth → the live artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds detail of BRAIN — the system's
> self-description layer. Every other file in `elements/` describes one part of the system; this one
> describes **the three-layer structure you are standing inside while you read it.**
>
> **One-line:** three layers at three altitudes — a MAP that routes, a MANUAL that explains how the
> parts combine, and an ELEMENT CORPUS that exhausts each part — arranged in the shape that **won a
> measured bake-off against seven alternatives**, none of which may be re-litigated from taste.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### THE THREE LAYERS — three altitudes, three different jobs

BRAIN is not one document at three lengths. Each layer answers a **different question**, and a reader
who uses the wrong layer for the wrong question gets a confidently wrong answer.

---

#### LAYER 1 — THE MAP (tip). A DOOR, not a DEFINITION.

**Where:** the always-loaded `CLAUDE.md`. It is paid for on **every single turn of every session**,
which is the entire constraint on its design.

**Its job:** get you to the right door. It names, for each part, **the commonest reason you would
reach for it** — one line, one reason, a filename to open next.

⛔ **NEVER answer *"what can X do?"* from the map.** That is not a style preference; it is what the
map is structurally incapable of. Every line on it is a crude simplification that names one reason
where the real part does considerably more. A line that said everything a part does would be the
element file — and then the map would cost what the corpus costs, on every turn.

⚠ **Anyone whose only source is the map is UNDER-INFORMED BY DESIGN.** That sentence is not an
apology for a thin document — it is the specification. The map is correct precisely when it is
incomplete, because completeness is the next layer's job and the map's budget cannot buy it.

The corollary: **the map is the layer most tied to a particular installation.** Its per-part lines
name that install's parts, its counts, its cadences. A map line that reads like a fact about the
system is very often a fact about *one* system. The two layers below it are where the transferable
description lives.

---

#### LAYER 2 — `system/organism/manual.md` (middle). ⚠ LOAD-BEARING.

**Where:** `system/organism/manual.md`. **1,173 lines.** On disk, on demand — never auto-loaded.

**Its job:** how the parts **work together** at ~5,000 ft. Not an index, not the weeds. It is the
only layer that describes **combinations** — what happens across two parts that neither part's own
file can state alone.

⚠ **IT HOLDS RULES THAT EXIST IN NO ELEMENT FILE.** This is the single most important operational
fact about the manual, and it is why *"the manual is just a summary of the elements, delete it"* is
wrong. Two examples, both grep-verified against the shipped `elements/` corpus at authoring, both
present ONLY in `manual.md`:

1. **The honesty-label grammar** (`manual.md` §THE LABEL GRAMMAR) — the rule that `maturity_label:`
   splits into a MACHINE-OWNED base (`LIVE` · `PARTIAL` · `DORMANT`, computed from a fire test) and
   HUMAN-OWNED suffixes (`·gap`, `[provisional]`, `(honor)`). **Every element file in the corpus
   carries a label written in that grammar; not one of them defines it.** Delete the manual and every
   label in forty-odd files becomes uninterpretable.
2. **The shared-working-tree git rule** — that `git add -A`, `git add .`, `git commit -a` and the rest
   of the everything-add class are blocked, because with several sessions against one working tree
   "add everything" is never your own work. Grep the corpus: it appears in no element file.

Beyond those two, the manual is where the **cross-cutting chapters** live — the three deliberate
compromises (no database, no UI framework, single-operator), the assert-your-own-output discipline,
and the provisional CODE/LLM SEAM chapter. None of them belong to any one part, so none of them have
an element file to live in.

---

#### LAYER 3 — `system/organism/elements/` (base). The exhaustive description.

**Where:** `system/organism/elements/<slug>.md`, one file per load-bearing part.

**Its job:** everything. Every trigger, every hand-off step, every store touched, every gate and
**whether that gate is real or prose**, every edge case, every interop seam. Source-traced: each file
declares the live artifacts it was written from, and the honest-map sections say plainly which
claimed enforcement is `[hook]` and which is `[honor]`.

**This is the layer that answers *"what can X do?"*** — and the only one that may.

**The corpus that ships here:** the origin system carried **51** element files. **10 are excluded** —
six personal desk elements, plus `helm`, `two-machine-residency`, `git-autopush` and
`overmyshoulder` — leaving **41**, plus this file, for **42**.

---

### ⭐ THIS STRUCTURE WAS CHOSEN BY MEASUREMENT, NOT BY TASTE — 2026-08-03

**Read this before you improve anything above.**

The three-layer shape is not an aesthetic preference and not one person's opinion about
documentation. It is **the surviving arm of a bake-off**. Two nights of sealed-agent scoring —
**58 probes on 2026-08-03**, counted from returned payloads — put the existing structure against
seven structural alternatives on the same baseline.

**Every single alternative scored WORSE.** The losing ideas, recorded so they are not re-invented:

| Losing arm | What it proposed |
|---|---|
| **Signposting down to the manual** | make the map point explicitly at the manual for depth |
| **Deleting the manual** | fold the middle layer away; keep map + elements |
| **Splitting the manual** | break the 1,173 lines into several smaller files |
| **Tagging the element files** | add routing markers to each element for faster selection |
| **Search-strings in the map** | put grep strings on the map so a reader could find things |
| **No map at all** | drop the always-loaded layer entirely |

**⛔ DELETING THE MANUAL COST TWO ANSWERS OUTRIGHT.** Not "cost more tokens" — questions that were
answered correctly with the manual present became unanswerable without it. Those are the two rules
named in LAYER 2 above (the label grammar and the git rule), which is exactly why they are named
there: the categorical loss and the load-bearing claim are the *same finding*.

**⛔ DO NOT "IMPROVE" THIS FROM TASTE.** Each of the six ideas above is the obvious, reasonable,
tempting thing a competent reader thinks of within about ten minutes of meeting this structure. They
have all been tried, on instruments, and they all lost. If you want to change the shape, the bar is a
measurement — not an argument, and not the fact that it currently looks redundant to you.

---

### ⚠ THE HONEST LIMITS OF THAT MEASUREMENT

The result above is strong in one direction and weak in another, and conflating them would be its own
kind of dishonesty.

- **DIRECTIONAL, NOT PRECISE — the cost deltas.** The per-arm percentages were measured at **n=1 per
  cell**, and a replicate of one cell measured **2.2× within-cell spread**. Any specific figure from
  that run is a direction of travel, never a number to quote or optimise against.
- **SOLID — the categorical results.** *Every arm was worse* and *deleting the manual loses two
  answers* are not statistical claims. The first is a clean sweep across seven arms; the second was
  grep-verified against the corpus, not inferred from a score.
- **The value is in the VARIANCE, not the mean.** Without the map, agents guess from filenames —
  sometimes brilliantly and cheaply, sometimes catastrophically. An average over those two outcomes
  hides the whole effect. So a small, well-run replication reporting *"the map didn't help much on
  average"* has **not** refuted anything.
- ⛔ **One near-miss is part of the record.** Three-quarters of the way through the no-map arm the
  reading was *negative*, and was about to be reported as "the map may not be earning its keep." The
  fourth result reversed the sign. **A partial result from this instrument is not a weak result; it is
  a wrong one.**

---

### ELEMENTS ARE DESCRIPTIVE, NOT PRESCRIPTIVE

An element file describes what the code **does**. It does not specify what the code **should** do.
That distinction decides what you do when the two disagree, and getting it backwards is the single
most damaging mistake available in this layer.

**When an element and the code disagree, the delta is exactly one of three things:**

1. **GAP** — the behaviour is described but absent here. It did not migrate, or it was never built.
   → **Build it,** or record it as a named gap. The element stays.
2. **IMPROVEMENT** — the code has moved on and is now *better* than the description.
   → **UPDATE THE ELEMENT.** The code is the ground truth; the description is what is stale.
3. **DELIBERATE** — the behaviour was cut on purpose (a personal desk, a machine-specific mechanism, a
   retired path). → **Say so in the element,** so the next reader does not re-file it as a GAP.

⛔ **NEVER FIX CODE BACKWARD TOWARD A STALE DESCRIPTION.** These files are a mirror, not a
specification. Reverting a genuine improvement because a document still describes the old behaviour is
destroying working machinery to satisfy a paragraph — and it is a plausible-looking mistake, because
the file is detailed, dated, source-traced and confident.

The corollary for the reader: **an element is only as fresh as its `generated_from` sources.** A dated
snapshot inside one (a count, a fleet size, a tile reading) was true when written and may not be now.
Numbers in this corpus drift fast; mechanisms drift slowly.

---

### DERIVED ELEMENTS — `generated_from:` and its two positions

Some elements are **DERIVED**: they were written from named live artifacts and are meant to be
**REGENERATED** when those artifacts move, not hand-patched line by line. The marker is the
`generated_from:` declaration listing those artifacts.

⚠ **The marker appears in TWO POSITIONS across this corpus, and a reader must check BOTH.** At port
time the tally was **35 files declaring it inside the YAML frontmatter** and **6 declaring it as a
trailing body line** (a `- **generated_from:**` bullet, or a `### GENERATED_FROM` section further down
the file). A tool — or a person — that looks only at the frontmatter will conclude those 6 files have
no sources, and will treat a derived file as hand-authored.

**Practical consequences:**

- **Hand-patching a derived element is a temporary fix at best**, and at worst it hides the drift it
  was meant to surface: the file now looks current while its sources have moved.
- **A `generated_from` entry naming a file that no longer exists is a live defect**, not cosmetic
  staleness — see the failure mode below.
- The split between what a human may write and what a machine may write is enforced *by the file
  format*: `## AUTHORED` is human-only (meaning, narrative, intent, seams — no script ever writes
  inside it) and `## AUTO-COMPUTED` is machine-only (the maturity label and when it was last checked).
  When a cited source changes, the system **nudges a human to re-author**; it never rewrites the
  meaning itself.

---

### ⛔ THE FAILURE MODE THIS LAYER MUST AVOID — naming a file that isn't there

Of everything that can go wrong in a self-description layer, one failure is worse than the rest:

> **A map or a manual pointing at an element that does not exist.**

**Worse than silence.** Silence sends the reader to look. A dangling pointer sends them to a missing
file and hands them a **wrong root cause** — they conclude the part was deleted, or the install is
broken, or the feature was never built, and then they act on that conclusion. Every downstream
inference is poisoned by a defect that had nothing to do with the subject they were investigating.

This is not hypothetical for a corpus assembled by porting a subset: a pointer that was correct in the
origin becomes dangling the moment its target lands on the exclusion list.

**The rules that follow, all `[honor]` here:**

- **Excluding an element means removing every pointer to it** — in the same edit, not later.
- **Never cite a file to make a point look sourced.** A citation is a promise the reader can open it.
- **Prefer naming nothing to naming something absent.** *"That mechanism is not described here"* is a
  true, useful sentence. A path to a missing file is a false one.
- **A `generated_from` entry is a pointer too**, and is subject to all of the above.

---

### STORES TOUCHED

| Store | Path | Access | By |
|---|---|---|---|
| The map (tip) | `CLAUDE.md` | READ (every turn, auto-loaded) | every session |
| The manual (middle) | `system/organism/manual.md` | READ on demand · WRITE by hand | a human re-authoring; readers |
| The element corpus (base) | `system/organism/elements/*.md` | READ on demand · `## AUTHORED` written by hand · `## AUTO-COMPUTED` written by the label checker | humans; `label-checker` |
| The extracted chapter | `system/organism-manual-extract.md` | READ | the skills that cite the CODE/LLM SEAM idea |

---

### GATES AND ENFORCEMENT (the honest map)

**Nothing in this element is hook-enforced here. All of it is `[honor]`.** Said plainly, because the
corpus is *about* the difference between a real guard and a written rule, and this would be the worst
possible file to be dishonest in.

- **The AUTHORED / AUTO-COMPUTED split** `[honor]` — the format makes the rule *testable* (you can see
  which block a change landed in), but no guard blocks a hand-edit inside `## AUTO-COMPUTED`, and no
  guard stops a script writing inside `## AUTHORED`.
- **"Don't answer from the map"** `[honor]` — prose only. Nothing prevents a session from answering a
  capability question off a one-line map entry.
- **"Never fix code backward toward a stale description"** `[honor]` — prose only, and the rule whose
  violation is hardest to spot after the fact, because the result looks like a tidy revert.
- **Pointer integrity** `[honor]` — no link checker runs over `manual.md` or `elements/`. A dangling
  element reference will sit there until a reader hits it.
- **Label honesty** `[skill]`, partially — `label-checker` fire-tests the guards a label claims and
  stamps the computed base label. Its coverage is the set of guards declared in its manifest, not the
  whole corpus, so most labels here remain hand-set and unverified.
- **In the origin system a PreToolUse write-guard protected the manual and the element files** (the
  self-description layer is also the system's own attack-surface map). ⛔ **Do not assume that guard is
  registered in this install** — stated so no reader infers protection from the fact that the rule is
  written down. Verify against the live hook registration before relying on it.

---

### EDGE CASES

1. **A reader with only the map.** Under-informed, by design — and will not *feel* under-informed,
   because each map line reads like a complete answer. That is the intended cost of the layer, paid
   for by the two layers underneath it. It becomes a defect only when the map is the sole thing
   shipped.
2. **A reader with only the elements.** Loses the cross-cutting rules that live in no element file.
   Measured: two answers, gone. This is the arm that lost hardest and the one most tempting to retry.
3. **A stale count inside an element.** Counts drift far faster than mechanisms — the same hook fleet
   was described at two different sizes seventeen days apart. Treat any snapshot number as dated
   evidence; treat the mechanism around it as current until the code says otherwise.
4. **An element describing a part that did not migrate.** A GAP, not a defect in the file. Record it;
   do not delete the description, and do not build the part merely because a file describes it.
5. **A `generated_from` path that does not resolve here.** Expected for anything traced to an origin
   artifact that was excluded. It must be visibly marked as such, never left to read as a live pointer.
6. **The extract vs. the manual.** `system/organism-manual-extract.md` carries one manual chapter for
   the skills that cite it, and states that the full manual is not shipped. If the manual *is* present
   in this tree, that sentence is stale and should be corrected in the extract — visibly.
7. **Two elements disagreeing with each other.** A finding, not a defect to patch. Record the tension
   where both readers will see it; do not resolve it quietly by editing one to match the other, and do
   not stack a new rule on top of it.

---

### HARD PROHIBITIONS

- **No capability answer from the map.** Open the element.
- **No deleting, splitting, or signposting-away the manual** on the grounds that it looks redundant.
  Those are three separately-named losing arms.
- **No code change made to satisfy a description.** The code is ground truth; the element is the mirror.
- **No pointer to a file that is not present.**
- **No machine write inside `## AUTHORED`; no hand-set label inside `## AUTO-COMPUTED`.**
- **No silent overwrite of a wrong statement in a dated element.** Correct it visibly — strike it, or
  put the correction beside it.
- **No re-litigating the structure from taste.** The bar is a measurement.

---

### INTENT / CURRENT-VS-TARGET

**Purpose.** A system whose logic lives partly in prose, partly in shell, and partly in a running
session cannot be understood by reading its code. BRAIN exists so that a stranger — human or agent —
can reach an accurate understanding of any part at whatever depth the question actually needs, and can
tell, for each rule, whether it is a wall or a wish. Its second purpose is to make that understanding
**auditable**: sources named, enforcement labelled honestly, and meaning kept out of machine hands.

**BY DESIGN — three layers, not one.** The map is cheap and lossy because it is paid for every turn.
The elements are exhaustive and expensive because they are paid for only when opened. The manual
exists because *combinations* have no other home. Collapsing any pair of these was tested and lost.

**BY DESIGN — descriptive, never prescriptive.** The corpus has no authority over the code. It earns
its keep by being *accurate*, and the moment it is treated as a specification it begins destroying the
thing it describes.

**Current state → PARTIAL, for a precise reason.** The structure is real and the corpus is here: the
manual ships intact at 1,173 lines, and the element corpus ships at 41 files plus this one. What keeps
it below LIVE is that **every rule in this element is `[honor]`** — no guard in this install is
confirmed to protect the manual, no link checker enforces pointer integrity, and the label checker's
fire-test coverage is a small manifest rather than the whole corpus. `[provisional]` because this file
is newly authored and has not been independently reviewed.

**TARGET.**
1. **A pointer checker.** Mechanical, cheap, and aimed squarely at the worst failure mode: resolve
   every `elements/<slug>.md` reference in `manual.md`, every `generated_from` path, and every
   cross-element pointer, then report the dangling ones. This is a membership check over a closed set
   — exactly the shape of work code is good at, and exactly the shape prose is bad at.
2. **Grow the fire-test manifest** so more of the corpus's `LIVE` claims are computed rather than
   asserted. Every label the checker does not cover is a hand-typed belief.
3. **Reconcile the extract with the shipped manual** (Edge Case 6), so the two do not contradict each
   other about what is present.

---

### INTEROP SEAMS (shared-state edges — the organism view)

```
CONTAINS     manual                · system/organism/manual.md is BRAIN's MIDDLE layer — the only
                                     place cross-part rules live; two of them (the label grammar and
                                     the shared-tree git rule) exist in NO element file, which is what
                                     "load-bearing" means here [honor]

CONTAINS     elements              · system/organism/elements/*.md is BRAIN's BASE layer — the
                                     exhaustive, source-traced description of each part; the only
                                     layer that may answer "what can X do?" [honor]

FEEDS        every-session         · the TIP map in the always-loaded CLAUDE.md routes a session to
                                     the right door and NOTHING more; a session that answers a
                                     capability question from it is under-informed by design [honor]

WRITES->     label-checker         · label-checker stamps the computed maturity_label + last_checked
                                     into each element's ## AUTO-COMPUTED block; it never touches
                                     ## AUTHORED, and its coverage is its manifest, not the corpus [skill]

SHARES-STORE label-checker         · both operate on system/organism/elements/*.md — BRAIN owns the
                                     meaning (## AUTHORED, human-only), label-checker owns the facts
                                     about enforcement (## AUTO-COMPUTED, machine-only) [honor]

FEEDS        organism-manual-extract · system/organism-manual-extract.md carries one manual chapter
                                     (the CODE/LLM SEAM) for the skills that cite it; it is an extract
                                     and says so — ⚠ its claim that the manual is not shipped needs
                                     reconciling against this tree (Edge Case 6) [honor]

DESCRIBES    every-element         · BRAIN is the only element whose subject is the corpus itself; the
                                     descriptive-not-prescriptive rule and the three-way delta reading
                                     (GAP · IMPROVEMENT · DELIBERATE) govern how EVERY other element
                                     file may be acted on [honor]
```

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the label checker will own this once its manifest covers this element)

- **maturity_label:** PARTIAL [provisional] (honor)
- **check_detail:** pending `label_checker.py` — no guard in this repo's manifest backs any rule in
  this element, so there is nothing here to fire-test today. What is REAL: the three layers exist on
  disk (`CLAUDE.md` · `system/organism/manual.md` at 1,173 lines · `system/organism/elements/`), and
  the two "manual-only" rules were grep-verified against the shipped corpus at authoring — the label
  grammar and the shared-tree git rule appear in `manual.md` and in no element file. What is
  honor-system: the AUTHORED/AUTO-COMPUTED write split (format-testable, not guard-enforced) · the
  don't-answer-from-the-map rule · the never-fix-code-backward rule · pointer integrity (no link
  checker runs) · the exclusion-means-remove-the-pointer rule. The origin system's PreToolUse
  write-guard over this corpus is not confirmed registered here. Honor-only across the board, with the
  measurement-backed structure and the shipped corpus as the real part ⇒ **PARTIAL (honor)**;
  `[provisional]` because this file is newly authored and not independently reviewed.
