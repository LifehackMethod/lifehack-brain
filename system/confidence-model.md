---
id: system-confidence-model
title: this system Confidence Model — the trust + tiering schema
record_type: doctrine
created_at: 2026-06-27
updated_at: 2026-06-28
status: active
authority: user
---

# this system Confidence Model

> The schema that governs HOW MUCH to trust a piece of knowledge and WHERE it belongs in the tier ladder.
> Confidence is an **overlay orthogonal to the temperature model**: temperature decides WHEN content loads;
> confidence decides HOW MUCH to trust what was loaded. They are independent axes.
>
> This doc is a **checkable schema**, not an essay. `/save`, the Archivist, and any reader of a below-canon
> record implement against it directly.

---

## 1. The Three Trust Layers

These are the spine. Every piece of knowledge in the system sits in exactly one.

### Layer A — Canon = human-vetted-true

**The ONE trusted layer.** "Always-true" means a human agreed — not that the content is old, often-cited, or
machine-confident. Canon earns its trust through the human-in-the-loop gate (`vetted: true`), not corroboration.

- **No corroboration gate on canon** — it has already passed the harder gate.
- **Machine NEVER writes canon true.** It proposes; a human approves. (`vetted: true` is human-only.)
- Placement rules: `system/knowledge-altitude.md` (the canon admission test).

### Layer B — Below Canon (records · insights · Cal entries · machine rollups) = default-skeptical

**Confidence here = CORROBORATION, not location.** A fact sitting in `records/insights/` is not trusted because
it is in insights — it is trusted to the degree that independent sources agree on it.

- A lone finding = one data point, not a verdict.
- **Facts earn UP into canon via human review**, not by age, repetition, or machine confidence.
- The corroboration ladder (originally from `skills/_archived-location-scan/SKILL.md` ⛔ gone — retired 2026-07-12
  and **DELETED 2026-07-28** in the S2.4 retirement sweep. **CORRECTION 2026-09-01**: the claimed verbatim
  copy at `state/archive/2026-07-28-s24-retirement-sweep/skills/_archived-location-scan/` was searched for
  this session, in both this repo and the AI Brain (`state/archive/`), and was NOT found in either —
  that preservation claim is itself unverified/stale, not re-asserted here; the ladder itself is
  doctrine and lives HERE now, so this file is the source, not that one):
  `documented > corroborated > single_signal > manual > inferred`

### Layer C — Snapshot = perishable

Fast-stale values: dollar amounts, this-week numbers, live tallies, API state. These are **re-pull material**,
not promote-to-canon material. A snapshot with a shelf-life is a fact with an expiry; after the expiry, treat
it as UNKNOWN until re-pulled.

---

## 2. Confidence Frontmatter Fields

Every below-canon record (Layer B or C) MAY carry these fields. `/save` and the Archivist write them;
readers interpret them.

```yaml
confidence:  CONFIRMED | INFERRED | HYPOTHESIS | USER-HYPOTHESIS | UNKNOWN
tier:        canon | dated-record | snapshot
shelf-life:  <ISO date or duration, e.g. "2026-07-04" or "7d"> # required for snapshot; optional for dated-record
type:        <register — see §2a below>
```

### §2a — The Register Taxonomy (`type:`)

**"Insight"** is the UMBRELLA for captured knowledge of any register — NOT a synonym for "rule" or "lesson."
Any below-canon record is an insight in the broad sense; the `type:` field specifies which register that
insight belongs to. Registers are sub-types of the `kind: insight` layer.

**DEFAULT = the SOFTEST register that fits.** The model NEVER auto-classifies something as `decision` or `rule`.

| `type:` | Meaning | Default? | Notes |
|---|---|---|---|
| `finding` | An observed or derived fact (confidence + source required) | **YES — default** | Most session outputs land here |
| `open-question` | An unresolved thread or live unknown | yes | Never collapse to a finding without evidence |
| `possibility` | An open direction under consideration (a.k.a. `option`) | yes | Two same-topic possibilities are NEVER merged → CONFLICT |
| `suggestion` | A recommendation or leaning, not committed | yes | Preserved as a suggestion; never upgraded to decision by the machine |
| `pros-cons` | A trade-off analysis | yes | **Preserved AS THE WHOLE WEIGHING — never collapsed to the winning side** |
| `dead-end` | A ruled-out path, with explicit WHY | yes | The "why it failed" is the gold — required, not optional |
| `decision` | An explicitly committed, scoped choice | no | Only when the human explicitly decided/committed; can be a dated-record |
| `snapshot` | A perishable number or fast-stale datum | no | Requires `shelf-life` |
| `rule` | A prescriptive always-on directive | **NEVER default; never model-chosen** | See §2b — the RARE GATED one |

`content` (file-pointer) and `flag` (gap) are inbox note types — NOT register types. They do NOT belong in
`type:` and do NOT live in the register taxonomy.

### §2b — The `rule` Register (RARE AND GATED — read this fully before use)

**`type: rule` is NEVER the default. The machine NEVER assigns it. Only the human elevates an item to `rule`
at the review-gate.**

Before creating a `rule`, `/save` surfaces a WARNING about the 2nd and 3rd-order effects:

1. **Always-on** — a rule loads into every relevant session and silently steers behavior. It fires even in
   cases it was not written for.
2. **Over-generalizes** — written for one situation, it fires in adjacent ones where it may not apply.
3. **Compounds** — rules accrete. Always-loaded canon bloats; untraced interactions between rules emerge.
4. **Sticky** — rules are trusted and rarely revisited. A wrong or over-scoped rule persists quietly.

Closing question before elevation: *"Is this really an always-on rule, or a strong suggestion / a finding
to re-read in context?"*

**DOUBLE-GATED:** even after human elevation, a rule is canon-bound → written as a canon-PROPOSAL
(`vetted: false`), never made `vetted: true` by the machine.

**`decision` ≠ `rule`:** a decision is a scoped, recorded choice for a specific situation; a rule is a
generalized always-on directive. Do not conflate them. A committed choice that only applies in one context
is `type: decision`, not `type: rule`.

### §2c — Confidence vocab

(Source: `skills/project-manager/SKILL.md` lines 309–316)

| Label | Meaning |
|---|---|
| `CONFIRMED` | Directly observed, decided, sourced, or stated by the user |
| `INFERRED` | Strongly suggested by evidence, not directly proven |
| `HYPOTHESIS` | Plausible explanation, theory, direction, or working model |
| `USER-HYPOTHESIS` | User's theory — preserved without over-validating |
| `UNKNOWN` | Important unresolved point |
| `CONFLICT` | Apparent contradiction requiring resolution — surface BOTH sides |
| `DEPRECATED` | Formerly believed/useful; now superseded or falsified |

### Example frontmatter block

```yaml
---
id: budget-2026-06-27-runway-snapshot
title: Runway estimate — June 2026
record_type: insight
desk: budget
created_at: 2026-06-27
updated_at: 2026-06-27
status: active
authority: skill
confidence: INFERRED
tier: snapshot
shelf-life: 2026-07-11
type: snapshot
source_refs:
  - "session 2026-06-27 — balance pulled from the source"
---
```

---

## 3. Tier-Assignment Decision Tree

**Deterministic.** `/save` and the Archivist follow this ladder exactly — no improvisation.

```
INPUT: a piece of knowledge to be filed

IF the human has explicitly marked vetted: true
  → tier: canon   (machine never sets this; human-only)

ELSE IF the value is a number, live tally, or any fast-stale datum
  (i.e., its accuracy expires within days/weeks regardless of sourcing)
  → tier: snapshot
    → REQUIRE shelf-life field (date or duration)
    → confidence: CONFIRMED if sourced this session; INFERRED if carried forward

ELSE IF the knowledge has at least one explicit source_ref (a citation, email,
  document, or recorded statement — not "I think" or session memory alone)
  → tier: dated-record
    → confidence: CONFIRMED if source is authoritative + direct
                  INFERRED if source is indirect or requires interpretation
                  HYPOTHESIS if plausible but source is circumstantial

ELSE (no source_ref, no vetted flag, no expiry date)
  → tier: snapshot   (treat as single-session, re-derive next time)
    → confidence: INFERRED or UNKNOWN

NEVER: machine sets tier: canon or vetted: true
NEVER: promote a snapshot to dated-record without adding a real source_ref
```

---

## 4. Named Seams

Three seams where ambiguity has historically caused silent failures. Each is defined precisely so there is
no room to ad-lib.

---

### SEAM 1 — SAVE-ARCHIVIST-HANDOFF

**Definition:** What `/save` emits and what the Archivist may/may-not do with it.

**`/save` emits:** a record or proposal file carrying the confidence frontmatter fields above (tier, confidence,
type, shelf-life). It places the file in the appropriate `records/` path or the journal, then signals the
Archivist router.

**The Archivist MAY:** place the record in the right home · dedup identical content · route cross-cutting
knowledge with one-home-plus-pointer · catch drift · surface CONFLICT between contradicting records.

**The Archivist MAY NOT:** judge the worth, durability, or framing of a record · collapse options · rewrite
conclusions · set `vetted: true` · collapse the register (a `possibility` stays a `possibility`; a `pros-cons`
stays the whole weighing).

**Register-preservation rule (critical):** `type: possibility` (a.k.a. `option`) and `type: decision` objects
are NEVER dedup-collapsed. Two records on the same topic where one is `type: possibility` and another is
`type: possibility` always surface as **CONFLICT** — regardless of text similarity. Collapsing them would
launder an open question into a settled position.

**Binary check:** Plant two `type: possibility` records on the same topic with similar-but-different content →
the Archivist emits CONFLICT, not a dedup merge.

---

### SEAM 2 — THE JOURNAL IS THE ONE FUNNEL

**Definition:** everything a session learned passes through the journal. Not *also* through it — *through*
it. It is the append-only backstop, and the one place a later reader can go when they do not yet know what
they are looking for or where it would have been filed.

**Consequence:** if a session's gold — a decision, a dead end, a number that mattered, the shape of what
happened — lands only in a record or only in a state file and never in the journal, then finding it later
depends on already knowing it exists. The journal is what makes it findable without that.

**What belongs in a journal entry:** the date · what was worked on · what it followed from · what failed or
changed · why · where things stood at the close, missteps included.

**Binary check:** write an entry, then in a cold session ask a question it answers without naming the
entry — `/read` should surface it.

> ⚖ **CORRECTED 2026-08-11.** This section used to describe the journal as a feed into a daily-diary tool,
> named a script that builds it, and specified what that script reads. **None of that machinery is in this
> repository** — it is part of the author's own setup. The rule about the journal is real and general; the
> pipeline it was described in terms of was not, and a doctrine page that points at tooling a reader does
> not have teaches them to go looking for something that was never sent.

---

### SEAM 3 — CONFLICT-SURFACE

**Definition:** Same content → dedup; different content on the same topic → emit CONFLICT.

- **Dedup:** normalized text or hash match → one record wins, the duplicate is removed.
- **CONFLICT:** same topic slug, different content → surface BOTH with `confidence: CONFLICT`, never drop one.
  The LLM applies the CONFLICT label; detection is deterministic (normalized-text comparison), not LLM judgment.

**Why this matters:** a silent merge is an opinion masquerading as a fact. Two different findings on the same
question may both be correct in different conditions, or may reveal a real contradiction — either way, a human
needs to see it.

**Binary check:** Plant two records with the same `topic:` slug and contradictory content → the Archivist
emits CONFLICT for both, neither is silently dropped.

---

### SEAM 4 — THE DENOMINATOR IS AUTHORED BY THE RUNNER, NEVER BY THE RUN

**Definition:** when a job is handed a bounded set of work, the count of what it was supposed to do comes
from whoever handed it out — and the job reports **what** it touched, never **how many**.

**Why this is a seam and not a style preference.** "I processed 12 items" is an assertion made by the thing
under examination. It cannot be checked, it cannot be wrong in any visible way, and it is the same sentence
whether the run was faithful, forgetful, or did nothing at all. A LIST can be diffed against the handoff. A
NUMBER can only be believed.

**The direction nobody watches.** Every completeness check ever written asks *did we get everything?* Almost
none asks *did we get only that?* — and an over-reaching job is silent by construction: it does not error,
it does not slow down, and its output is indistinguishable from a correct job that happened to be handed
more work. The only thing that reveals it is the diff against its own handoff. `shared/bounded_input.py`
is that diff.

**The rule, in three lines:**
- the caller writes down what it handed out, before the work starts
- the run writes down what it touched, as a list of identifiers
- something else diffs the two — and refuses to evaluate at all if either side is missing, empty or a shape
  it does not recognise, because a check with no denominator passes everything while appearing to work

**Binary check:** hand `bounded_input.py` a processed file containing a count rather than a list → exit 2,
CANNOT EVALUATE. Hand it an empty handed list → exit 2. Neither may ever be exit 0.

**What it cannot do, stated so nobody assumes otherwise:** it cannot detect a run that did *less* than it
was handed and copied its work-list to look busy. That is undecidable from these two inputs — the forged
file is byte-identical to the honest one — and closing it needs a third witness that records work as it
happens. The tool's own header carries the measurement.

---

## 5. Reuse — Do Not Reinvent

These existing sources define the vocabulary this model relies on. Cite them; do not copy inline.

| Concept | Source |
|---|---|
| Confidence vocab (CONFIRMED/INFERRED/HYPOTHESIS/USER-HYPOTHESIS/UNKNOWN) | `skills/project-manager/SKILL.md` lines 309–316 |
| Corroboration tier ladder (documented > corroborated > single_signal > manual > inferred) | THIS FILE is now the source. Originally `skills/_archived-location-scan/SKILL.md` ⛔ gone — lines 107–120 (retired 2026-07-12, deleted 2026-07-28; claimed verbatim copy at `state/archive/2026-07-28-s24-retirement-sweep/` NOT found this session in repo or AI Brain — CORRECTED 2026-09-01, unverified) |
| Canon admission test (the plain-question level ladder) | `system/knowledge-altitude.md` §3 |
| Temperature model (always-on vs scoped vs on-demand) | ⛔ `system/memory-system.md` §1 — **not shipped.** `docs/data-layout.md` is the map here |
| Frontmatter schema (required fields, record_type canonical list) | `system/schemas/managed-file-frontmatter.md` |
| The runner-authored denominator (SEAM 4) | `shared/bounded_input.py` — the check, and the measured limits on it |
