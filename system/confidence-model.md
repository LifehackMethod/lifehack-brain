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
- The corroboration ladder (originally from `skills/_archived-location-scan/SKILL.md`, retired 2026-07-12
  and **DELETED 2026-07-28** in the S2.4 retirement sweep — the source text is preserved verbatim at
  `state/archive/2026-07-28-s24-retirement-sweep/skills/_archived-location-scan/`; the ladder itself is
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

### SEAM 2 — JOURNAL-FUNNEL

**Definition:** The journal is the SINGLE funnel session-learnings pass through before reaching Cal.

The Cal daily diary is built mechanically FROM the journal by `cal-diary-capture.py`, which reads:
`system/journal.md` + `state/status/*.json` (per-desk current-state snapshots) + Google Tasks + Calendar events.

**It does NOT read canon or records directly.**

**Consequence:** if a session's gold (decisions, dead-ends, key numbers, narrative arc) lands only in a record
or in `state/current.md` but NOT in the journal, the Cal diary for that date is blind to it. The journal is
the mandatory transit point.

**What belongs in a journal SESSION CONTEXT entry:** session date · what was worked · what was followed-from ·
what failed or changed · why · state at close (including missteps).

**Binary check:** Write a fresh journal SESSION CONTEXT entry → the `cal-diary-capture.py` output for that
date includes content drawn from that entry.

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

## 5. Reuse — Do Not Reinvent

These existing sources define the vocabulary this model relies on. Cite them; do not copy inline.

| Concept | Source |
|---|---|
| Confidence vocab (CONFIRMED/INFERRED/HYPOTHESIS/USER-HYPOTHESIS/UNKNOWN) | `skills/project-manager/SKILL.md` lines 309–316 |
| Corroboration tier ladder (documented > corroborated > single_signal > manual > inferred) | THIS FILE is now the source. Originally `skills/_archived-location-scan/SKILL.md` lines 107–120 (retired 2026-07-12, deleted 2026-07-28; verbatim copy at `state/archive/2026-07-28-s24-retirement-sweep/`) |
| Canon admission test (the plain-question level ladder) | `system/knowledge-altitude.md` §3 |
| Temperature model (always-on vs scoped vs on-demand) | ⛔ `system/memory-system.md` §1 — **not shipped.** `docs/data-layout.md` is the map here |
| Frontmatter schema (required fields, record_type canonical list) | `system/schemas/managed-file-frontmatter.md` |
