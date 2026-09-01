---
element: red-team
title: "red-team — element detail (ground/base altitude)"
subsystem: plan-critique
altitude: base
record_type: organism-element
maturity_label: LIVE [provisional]
generated_from:
  - skills/red-team/SKILL.md (v1.0)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# red-team (`/red-team`) — element detail

> ⚠ **CORRECTED 2026-09-01:** the bare `skills/red-team/SKILL.md` cited above (frontmatter) and below
> (at "the skill itself"), and the bare `skills/research/SKILL.md` cited further down at the `/research`
> distinction, are the donor's repo-relative form and resolve nowhere from this repo's root. Verified
> this session: both ship from the installed plugin at `.claude/skills/<name>/` (plugin root, confirmed
> under `~/.claude/plugins/marketplaces/lifehack-brain/`), not from any path inside this repository.

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of how `/red-team` actually works —
> its trigger, its constraint model (no-nitpick / severity-ranked), its output shape, every interop seam,
> and its honest enforcement map. The MIDDLE index (`system/organism/manual.md`) carries only a pointer
> here; the TIP (`CLAUDE.md` schematic) shows only its box + arrows; the **skill itself**
> (`skills/red-team/SKILL.md`) is the fourth level — the executable runtime ground truth.
> This entry is the UNDERSTANDING layer: exhaustive description of what the skill does + why + how it connects.
>
> **One-line:** surface the glaring errors in a plan before they get expensive — no nitpicking, no
> perfection loops — ranked worst-first, with suggested fixes, then stop.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory step) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause)

---

## AUTHORED   (human-only)

### TRIGGERS

Every trigger that causes `/red-team` to run:

1. **Explicit `/red-team`** — the canonical registered trigger (the sole entry in the SKILL.md `triggers:` frontmatter).

The SKILL.md `description:` field also names routing phrases ("red-team this", "punch holes in this") as dispatch-layer hints, but these are NOT a registered `triggers:` list — they are description prose for the skill router. "Surface the glaring errors / omissions" is a paraphrase of the description, not a registered trigger.

No hooks intercept or pre-process these triggers. Trigger recognition is skill-prose / honor-system `[honor]`.

**What it receives:** a plan, proposal, design doc, or decision — any structured "here is what I intend to do" artifact. The artifact is provided in-context; `/red-team` reads nothing from disk and writes nothing. It is stateless and ephemeral.

---

### MECHANICS (how it works)

`actor → in-context plan → model judgment → stdout findings [honor]`

The skill installs a deliberate adversarial posture — **The Adversary** — with a hard constraint:

**The qualification bar (the no-nitpick gate — the single most important mechanic):**
A finding qualifies ONLY if, left unaddressed, it would either:
(a) make the plan **fail its stated goal**, OR
(b) create a **hard-to-reverse** consequence.

Style issues, nice-to-haves, completeness polish, and marginal improvements do NOT qualify. The gate is enforced by skill-prose `[honor]` — there is no hook that verifies findings against this bar.

**Severity classification:**
Each finding is classified as one of three severity levels:
- `FATAL` — would definitively break the plan
- `MAJOR` — high probability of material failure or costly reversal
- `MINOR` — real hole, lower blast radius

**Ranking:** findings are ordered worst-first (FATAL → MAJOR → MINOR). The human sees the most dangerous items first.

**Suggested fix:** every finding carries a suggested fix. The fix is directional, not a roadmap — just enough to unblock the hole.

**Scope boundary (hard — skill-prose `[honor]`):**
After the list, `/red-team` STOPS. It does not:
- iterate or expand unless explicitly asked for a second pass
- produce a roadmap or solution design (out of scope)
- nitpick style, formatting, or completeness for its own sake

---

### OUTPUT FORMAT

```
## Red-Team Findings
[1] [SEVERITY: FATAL|MAJOR|MINOR] finding — suggested fix
[2] [SEVERITY: MAJOR] ...
...
```

Findings are numbered, severity-labeled, and sorted worst-first. The output is a flat list — no prose preamble, no closing summary unless the finding list is empty (in which case "No glaring holes found" is appropriate). The artifact is ephemeral: nothing is saved to disk, no journal entry, no brief update.

---

### STORES TOUCHED

| Store | Access |
|---|---|
| In-context plan/artifact (caller-provided) | READ (model reads it from the conversation context) |
| `stdout` | WRITE (findings output only) |

`/red-team` reads no files. It writes to no files. It does not touch `journal.md`, `debt-ledger.md`, `open-loops.md`, or any brief. Purely ephemeral.

---

### GATES AND ENFORCEMENT (the honest map)

**No hooks exist for `/red-team`.**

A search of `settings.json` (grep: `red.team`, `red_team`) found zero entries — no PreToolUse, PostToolUse, or UserPromptSubmit hook is registered for this skill. `[honor]` throughout.

All behavioral contracts are prose-only:
- The no-nitpick qualification bar `[honor]`
- Severity classification accuracy `[honor]`
- Worst-first ranking `[honor]`
- Stop-after-the-list discipline `[honor]`
- No-roadmap / no-second-pass discipline `[honor]`

**Primary mechanism: the main session's in-context adversarial posture + prose rails in SKILL.md.** The skill is enforced entirely by the model reading SKILL.md at invocation time. No mechanical enforcement exists and none is expected — the skill is a pure-LLM one-shot with no persistent state to guard.

**Maturity: LIVE `[provisional]`** — the primary behavioral contract (adversarial posture + no-nitpick + severity ranking) is the skill-prose itself; it fires as a one-shot every invocation. There are no gaps that would cause a tip-only reader to misjudge enforcement posture — the skill is explicitly `[honor]` throughout; no `·gap` marker required.

**`(honor)` tip-tag:** the PRIMARY behavioral contract of `/red-team` is skill-prose only — no blocking hook enforces it. This qualifies for the `(honor)` tip-tag per §8.4b.

---

### EDGE CASES

1. **"Second pass" request** — if the human asks for a second pass, `/red-team` re-runs with the same no-nitpick bar. The instruction not to iterate unless asked is skill-prose `[honor]`.

2. **Empty / trivial plan** — if the provided artifact has no glaring holes, return "No glaring holes found" and stop. Do not manufacture findings to fill the format.

3. **Invoked by advisory-council's Argue stage** — when `advisory-council` runs its Stage 2 (Argue / red-team), the adversarial charge is structurally different: it is advisor-against-advisor over an anonymized snapshot, with an explicit "refute mandate." This is `advisory-council`'s internal mechanism — it does NOT invoke `/red-team` as a skill. The two are conceptually related but structurally separate.

4. **`planning-weekly` council: "red-team" label banned** — `planning-weekly/prompts/04-council.md` (line 16) explicitly bans the "red team" label in council dispatch framing ("the label makes members perform adversarialism instead of thinking"). When chairing a weekly council, `/red-team` is NOT invoked; advisors receive a neutral "challenge it" charge instead. This is a deliberate design choice, not a gap.

5. **`/research` distinction** — `/research` explicitly states it is "not a red-team / refutation run" (`skills/research/SKILL.md` line 21); convergence-mapping measures the distribution of expert practice and does not argue a side. They are complementary: `/research` finds what experts converge on; `/red-team` challenges whether the plan survives.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** prevent expensive plan failures by applying a focused, time-boxed adversarial pass before execution — ranked by blast radius, no spiraling perfection loops.

**BY DESIGN:** the skill is fully `[honor]`. A one-shot critic needs no state, no hooks, and no stores. The stateless design is correct — mechanical enforcement of "don't nitpick" would require more infrastructure than the skill's entire footprint. The skill-prose IS the enforcement; this is not a gap.

**Current state → LIVE `[provisional]`:**
- The primary behavioral contract fires on every invocation (the model reads SKILL.md and adopts The Adversary posture).
- No hooks are missing — the design never called for them.
- The `[provisional]` qualifier is honest: the LIVE label is based on reading the single-file skill source; no runtime conformance test has been run against it.

**TARGET (design FORK — morning candidate):**
The skill-sop-audit (2026-07-12, brief.md) identified one deferred action for `/red-team`:
- **Wave 3** of the remediation plan: **recategorize `red-team` as a utility** (not a "leading" skill). The D-grade in the audit was a category artifact — the skill was scored against persona/anchor checks that don't apply to a utility. Recategorizing dissolves the D now (post-remediation). This is a frontmatter/registry change only — note that the scorecard ran against the pre-remediation stub (the §0.5 block, description field, and Adversary posture were added in the same 2026-07-13 wave that executed the review; the score reflects the pre-fix state, not the remediated skill). `state:actionable` per the debt-ledger entry (line 214).

**Known SKILL.md notes:**
- The skill has a single SKILL.md at 31 lines — appropriately lean for a one-shot utility.
- The `## Intent (§0.5)` block was added in the skills-remediation wave (2026-07-13 — the audit was planned 2026-07-12 but remediation commits executed 2026-07-13).
- No `allowed-tools` or `model:` pin declared — consistent with a main-session-only skill that inherits the session model.

---

### INTEROP SEAMS (shared-state edges to other elements — the organism view)

**The key insight:** `/red-team` is a LEAF — no reads, no writes, no state. All seams are CALL seams (other elements invoke it or relate to it) rather than data-flow seams.

```
COMPLEMENTS   advisory-council   · conceptually parallel adversarial mode; advisory-council's Argue
                                   stage runs its own structured red-team round (advisor-vs-advisor
                                   over anonymized snapshot) — it does NOT call /red-team the skill;
                                   the two are distinct mechanisms for the same impulse
COMPLEMENTS   research           · /research maps convergence (what experts do); /red-team attacks
                                   the plan (does ours survive); run /research first, /red-team second
                                   when both are needed
CHAINS        architecture-planning-sop · the SOP uses /advisory-council in pre-mortem mode at
                                   Stage 4 (architecture-planning-sop.md line 91) rather than
                                   /red-team directly; for Quick/Standard tier builds, a "30-sec
                                   self-pre-mortem" (line 27) is the lightweight substitute; /red-team
                                   is the available utility for an ad-hoc pre-mortem outside the SOP
                                   formal gate — INFERRED (underlying facts confirmed; editorial framing
                                   is an inference — no explicit invocation of /red-team found in the SOP)
COMPLEMENTS   council            · /council (convergence) and /red-team (critique) are orthogonal;
                                   run council to generate options, /red-team to punch holes in the
                                   winning option — UNVERIFIED (no explicit cross-reference found)
```

**Exclusions (documented by source):**
- `planning-weekly` council (Phase 4): explicitly bans the `/red-team` label and framing in dispatch; advisors receive a neutral "challenge" charge instead (`04-council.md` line 16, `_member-format.md` line 5). This is a deliberate design decision, not a gap.

---

### GAPS

No documented fail-open conditions exist for `/red-team`. The skill has no enforcement mechanism to fail open. The only risk is an undertrained finding list (model misapplies the no-nitpick bar), which is an execution quality issue, not a structural gap. No `·gap` marker warranted.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** LIVE [provisional]
- **check_detail:** No hooks registered (grep of settings.json: zero hits for `red-team`/`red_team`). One source file: `skills/red-team/SKILL.md` (30 lines, v1.0). Behavioral contract is entirely skill-prose `[honor]`: adversarial posture, no-nitpick bar, severity ranking, stop-after-list. No stores touched. No mechanical enforcement — correct by design for a stateless one-shot utility. Debt-ledger entry (line 214) tracks Wave 3 recategorization as `state:actionable`. `[provisional]` because no runtime conformance test has been run against the skill; LIVE label is based on source-read only.
