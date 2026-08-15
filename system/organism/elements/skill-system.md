---
element: skill-system
title: "skill-system — element detail (ground/base altitude)"
subsystem: skill-system
altitude: base
record_type: organism-element
maturity_label: PARTIAL·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C6 known-fix-unapplied — enforce_skill_frontmatter matcher is Write only; the Edit path is dark. Fix scheduled as S2.3"
generated_from:
  - system/hooks/enforce_skill_frontmatter.sh (PreToolUse Write)
  - system/hooks/auto_register_skill.sh (PostToolUse Write|Edit)
  - system/hooks/skill_anchor.sh (state manager)
  - system/hooks/skill_anchor_inject.sh (UserPromptSubmit)
  - docs/skill-conformance.md
  - system/sops/skill-building-sop.md
  - system/templates/skill-template/SKILL.md
  - system/tools/new-skill.sh
  - system/tools/conformance-lab/conformance.py
  - system/reference/settings.json (hook registration lines 147–291, 347–355)
  - skills/* (directory: 49 live skill folders + ~7 archived/retired)
  - ~/.claude/skills/* (50 symlinks to clone)
  - ~/.claude/commands/* (desk-scoped command stubs; not all from auto_register)
  # PARTS LIBRARY — reusable gate primitives a skill composes (added 2026-07-28, S2.0)
  - system/parts/phase_gate.py
  - system/parts/forbidden_content.py
  - system/parts/order_lint.py
  - system/parts/write_ledger.py
  - system/parts/capture_gate_selftest.py
  - system/parts/completeness_receipt.py
  - system/parts/fanout_gate.py
  - system/parts/residue_scrub.py
  - system/parts/voted_judge.py
  # SPEC FACTORY — spec prose → atomic clauses → gates, plus the adversarial defeater
  - system/factory/spec_units.py
  - system/factory/extract_clauses.py
  - system/factory/classify_clause.py
  - system/factory/defeater.py
created_at: 2026-07-24
updated_at: 2026-07-28
status: draft
authority: user
---

# skill-system — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#skill-system ; ground truth → the live artifacts (generated_from)**
>
> **One-line:** the full lifecycle of a Lifehack skill — from scaffolded birth, through frontmatter
> enforcement and slash-command registration, to every-turn anchor re-injection that keeps a leading
> skill on-frame across a long session.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause)

> **CITATIONS — what the paths below resolve to here.** The body describes the donor's skill lifecycle truthfully; the four lines below record what happened to each named target at THIS destination, and they cover every mention of them in the body.
>
> ⛔ `/slash` and `/skill-name` — not skills and never were. Both are PLACEHOLDER words in the prose below (*"triggered by user phrase or `/slash`"*, *"an accessible `/skill-name` command"*), standing for *any* slash command. No skill by either name exists in the donor or here, so there is nothing to bring.
>
> ⛔ `system/tools/bootstrap-machine.sh` — never ships. Its whole job was wiring a `~/.claude/skills/` symlink farm pointing INTO a second machine's clone; that layer does not exist here at all — verified, every entry under `.claude/skills/` is a real in-repo directory, not a symlink, so the harness discovers skills with nothing to wire. The destination's bootstrap is `system/tools/bootstrap.py`, which scaffolds the reader's NOTES folder and deliberately nothing else. The two-machine residency tooling it belonged to is on the closed exclusion list.
>
> ⏳ unruled — `system/tools/conformance-lab/conformance.py`, the grader itself. On no ship list and no phase owes it: a DEBT, not a pass.
> The rest of the lab DID come over — `system/tools/conformance-lab/driver.py`, `system/tools/conformance-lab/probes/`, `system/tools/conformance-lab/rule-registry.md` and `system/tools/conformance-lab/_verify_guards_manual.py` are all here — while `system/tools/new-skill.sh` line 184 still promises that "conformance.py grades the skill with ZERO new code."
>
> ⏳ unruled — `system/templates/skill-template/SKILL.md`, the canonical template the scaffolder was designed from. It did not come over; no phase owes it. A DEBT, not a pass.
> The templates directory that DID come over holds only the telos starter, yet `system/tools/new-skill.sh` ships and `system/organism/manual.md` line 798 still names this template as what the scaffolder's stamp must stay in sync with.
>
> ⚠ Line 310 below reads to the linter as a `✅` presence claim only because that sentence quotes the literal `✅ phase N complete` boundary marker. It is not a claim about the grader; the two lines above are the authoritative ones.

---

## AUTHORED   (human-only)

### WHAT A SKILL IS

A Lifehack skill is a SKILL.md file the Claude Code harness auto-discovers and auto-triggers from its
`description:` frontmatter field when the user's prompt matches. It is NOT a plugin, daemon, or
compiled artifact — the LLM reads the SKILL.md body at runtime to act. This means the `description:`
field IS the skill from the harness's point of view: the only field the harness reads for auto-trigger.

**Skill vs Command:** a skill has an ordered multi-step flow, may hold state across turns, leads/leads
the user, and carries invariants that must reliably fire. A command is a single large prompt behind a
slash-command: one shot, no ordered flow, no state across turns. Commands pass a lighter bar
(sharp description + clean prose). A skill MUST conform to the full SOP. The test: if you could paste
it as one prompt, it is a command; if it needs steps to hold, it is a skill.
(`system/sops/skill-building-sop.md §2`)

**Three skill shapes** (declared via `shape:` frontmatter, CF-14):
- `interactive-workflow` — human-facing multi-step, triggered by user phrase or `/slash`
- `cron-producer` — autonomous background job; emits a dashboard tile; triggered by the harness runner
- `utility` — helper / routing / one-shot logic called by other skills or explicitly

A skill may declare `shape: [cron-producer, interactive-workflow]` (list) for genuinely multi-mode skills.

---

### THE REGISTRATION CHAIN

The path from an authored SKILL.md to an accessible `/skill-name` command is: **author → birth-guard
→ discover by harness → (desk) stub creation → (global) symlink**.

#### Step 1 — Scaffold (recommended birth path)

`actor → new-skill.sh → skills/{name}/SKILL.md → born conformant [skill]`

The canonical scaffolder is `bash ~/lifehack-brain/system/tools/new-skill.sh <name> --description "<line>"`.
(`system/tools/new-skill.sh`, 180 lines)

What the tool does (verified in code, lines 60–180):
- Validates `--description` is not a REPLACE placeholder and is ≥20 chars
- YAML-escapes the description (backslash + double-quote) to prevent the colon-space YAML trap
- Stamps frontmatter with `skill:`, `description:` (double-quoted), `shape:`, `status: active`,
  `version: 0.1`, `created_at`/`updated_at: TODAY`
- Writes `## Intent (§0.5)` block with REPLACE prompts for User outcome + Role + Per-turn anchor
- Writes `## Rails` section
- With `--multiphase N`: creates `skills/{name}/prompts/NN-phaseN.md` drivers, each born with
  `## Output contract`, `## do NOT`, and `✅ phase N complete` markers (the conformance-lab grade seam)

The tool resolves `CODE` from its own location (`$(dirname "$0")/../..`), not a hardcoded home
path — makes it portable across git worktrees (verified in code, lines 33–35).

#### Step 2 — Frontmatter enforcement (birth guard)

`enforce_skill_frontmatter.sh → PreToolUse Write → exit 2 blocks the write [hook]`

**settings.json line 147–154 (verified):** matcher `Write`, single hook.
**What it checks (Python embedded, verified line-by-line):**

1. **Path filter** — only fires on `*/skills/*/SKILL.md`; skips `*/skills/_*` (archived/retired holding areas) and `*/templates/*` (those legitimately need no description). `[hook: enforce_skill_frontmatter.sh line 38–42]`
2. **Content-only guard** — fires only on a full-content `Write` (where `content:` field is present); an `Edit` (which carries old/new strings, not the whole file) is not covered by this hook. `[hook: line 57–59]`
3. **Size cap (c)** — >500 lines → exit 2, BLOCKED. `[hook: line 61–63]`
4. **YAML frontmatter block** — must open with `--- ... ---`; no block → exit 2. `[hook: line 66–69]`
5. **`description:` non-empty** — frontmatter must parse as YAML with a non-empty `description:` key; YAML import failure → exit 2; `yaml` not installed → regex fallback (presence-check only, not parse-check). `[hook: lines 71–91]`
6. **No scaffold placeholder** — `description:` starting with "REPLACE" → exit 2. `[hook: line 90–91]`

**Exit 2 semantics:** the harness interprets exit 2 as a BLOCK (the Write is not executed). The deny
message states WHY + redirects to `new-skill.sh` + names the two docs (SOP + conformance doc).

**UNVERIFIED:** whether this hook is registered and fires identically on the second machine (the
`settings.json` is machine-local; `git pull` propagates the file but the symlink path is machine-specific).

#### Step 3 — Global skills: symlink discovery

`skills/{name}/ → git clone → ~/.claude/skills/{name} symlink → harness discovers [system]`

Global skills live at `~/lifehack-brain/skills/` (the git clone). The harness discovers them via
`~/.claude/skills/`, which holds symlinks into the clone. As of 2026-07-24: 50 symlinks under
`~/.claude/skills/` pointing to `~/lifehack-brain/skills/` directories (verified: `ls -la ~/.claude/skills/ | grep "^l" | wc -l`).
The symlinks are created once (bootstrap / `system/tools/bootstrap-machine.sh`); the git clone carries
all future changes.

**No command stub for global skills.** `auto_register_skill.sh` explicitly skips global skills
(code verified, lines 43–46) to avoid duplicate slash-command entries — the harness reads the
`~/.claude/skills/` directory directly.

#### Step 4 — Desk skills: command stub creation

`auto_register_skill.sh → PostToolUse Write|Edit → desks/{desk}/.claude/commands/{name}.md [hook]`

**settings.json line 283–291 (verified):** matcher `Write|Edit`, PostToolUse.

Fires when a SKILL.md is written under `desks/{desk}/skills/{name}/SKILL.md` (either in the Drive
root or the clone root — both supported; fixed 2026-06-18 when it was dead for clone writes).

What it does (verified, lines 62–79):
- Extracts `title:` and `note:` from frontmatter (grep/sed, no YAML parse)
- Creates `desks/{desk}/.claude/commands/{name}.md` stub pointing at the skill path
- If a stub already exists: skips (idempotent)
- If `note:` is present: prefixes it to the stub content

**Scope: desk skills only.** Global skills (`lifehack-brain/skills/` or Drive `Lifehack/skills/`)
→ emit an info stderr message + exit 0. The hook distinguishes by path prefix.

**UNVERIFIED:** as of 2026-07-24, the `~/.claude/commands/` dir under the clone root holds no entries
(`ls $HOME/lifehack-brain/.claude/commands/` returns empty); the desk stubs in
`~/.claude/commands/` appear to have been created by other means or an earlier version of the hook.
The hook's PostToolUse Write|Edit matcher applies to both Write AND Edit tool calls, unlike
`enforce_skill_frontmatter.sh` which is Write-only.

---

### ANCHOR SYSTEM (keeping a leading skill on-frame across a long session)

The anchor system addresses **context rot**: a SKILL.md body loads once at invocation and sinks into
the low-attention middle of context as the session grows; a leading/specialist skill drifts toward
the user's framing. Research 2026-06-17 (referenced in both hooks' LLM-CONTEXT blocks) confirmed this
is the dominant failure mode for multi-turn leading skills.

**Two components: state manager + every-turn injector.**

#### skill_anchor.sh — state manager

`skill_anchor.sh arm <slug> <abs_anchor_file> → ~/.claude/run/anchor/anchor-{key}.flag [skill]`

The flag stores: `skill=`, `anchor_file=` (absolute path to a lean anchor file), `armed_at=`
(epoch timestamp), `cwd=`, `session=` (CLAUDE_CODE_SESSION_ID).

Session key logic (verified in code, lines 21–25): uses `sess-{CLAUDE_CODE_SESSION_ID}` when the env
var is set; falls back to `cwd-{12-char sha of $PWD}` when the session ID is absent. This means
parallel windows with the same cwd could share an anchor flag if the session env var is not set.

TTL: 12 hours default (`ANCHOR_TTL_HOURS`, overridable); the `status` command self-expires on read.

Three subcommands: `arm <slug> <abs_anchor_file>` (verifies anchor file exists first; fails if not) ·
`status` (prints active slug or "none"; expires stale flags on read) · `clear` (removes this session's
flags; also sweeps ALL flags sharing the same CLAUDE_CODE_SESSION_ID, not just the current-cwd flag).

A skill arms the anchor after it is triggered; clears it on exit or abandonment. The anchor file is
a separate lean (~150-token) file the skill maintains — NOT the full SKILL.md body.

#### skill_anchor_inject.sh — every-turn injector

`skill_anchor_inject.sh → UserPromptSubmit → injects anchor to context every turn [hook]`

**settings.json line 347–355 (verified):** matcher `""` (all prompts), UserPromptSubmit hook.

What it does on every user prompt (verified in code):
1. Reads the session key (same logic as `skill_anchor.sh`)
2. If no flag → **pure NO-OP** (exit 0 silently, no output)
3. Reads anchor file; strips control/zero-width/bidi chars (but preserves tab + newline) via
   `tr` + perl (verified, line 51)
4. Enforces character ceiling (`ANCHOR_CHAR_CEIL`, default 1200 chars) — truncates with an explicit
   notice so a bloated anchor can't flood every turn
5. Prints:
   - `[SKILL ANCHOR — {slug} · harness-injected every turn, NOT user input. These are YOUR standing principles...]`
   - The anchor body
   - `↳ Before responding: silently re-confirm you are LEADING per the above...`

**DEGRADE-SAFE:** any error → exit 0, behaves as if no anchor. The hook never blocks a prompt.
(verified: `set +e` + every conditional path exits 0 on failure)

**Relationship to pm_persist.sh:** mirrors the pm_flag/pm_persist pattern for the skill context — the
flag manager (`skill_anchor.sh`) mirrors `pm_flag.sh`; the injector (`skill_anchor_inject.sh`) mirrors
`pm_persist.sh`. Both fire as UserPromptSubmit hooks; both are session-scoped; both are degrade-safe.

---

### THE FRONTMATTER CONTRACT

**Required fields (from live template + conformance doc + hook verification):**

| Field | Required for | Source of truth |
|---|---|---|
| `skill:` | all | `new-skill.sh` scaffolds it; slug must match the directory name |
| `description:` | **all** — the ONLY field the harness reads for auto-trigger | `enforce_skill_frontmatter.sh` exit-2 blocks Write if absent/empty/placeholder |
| `shape:` | **all (CF-14)** | `interactive-workflow` / `cron-producer` / `utility` (or list) |
| `status:` | all | `active` / `draft` / `deprecated` |
| `created_at` / `updated_at` | all | ISO date |
| `desk:` | cron-producer | owning desk slug |
| `triggers:` | interactive-workflow + utility | invocation phrases (absent on cron-producers) |
| `title:` | all (used by `auto_register_skill.sh` for stub content) | grep'd from frontmatter |
| `note:` | optional | prefixed to command stub by `auto_register_skill.sh` |
| `allowed-tools:` | utility (optional) | tool allowlist |

**The YAML colon-space trap (live defect that triggered the 46-skill remediation, 2026-07):**
An unquoted `description:` value containing `': '` (colon-space) crashes YAML parsing; the harness
falls back to the body heading. `new-skill.sh` double-quotes and escapes the value to prevent this
at birth; `enforce_skill_frontmatter.sh` catches it at write time via YAML parse failure (exit 2).

**`description:` placement matters:** the harness truncates descriptions at ~250 chars for auto-trigger
matching. The SOP requires trigger conditions + literal trigger words front-loaded before char 250.
(`system/sops/skill-building-sop.md §2`)

**Note on `skill:` vs `name:` vs `summary:` vs `description:` key naming:** the conformance doc
(`docs/skill-conformance.md §1`) canonicalized `skill:` (not `name:`) and `summary:` (not
`description:`) — but the live template and `new-skill.sh` use `description:`, and
`enforce_skill_frontmatter.sh` checks for `description:`. The `skill-conformance.md` v2-tile field
naming (`summary:`) is UNVERIFIED as live — the actual enforcement hook and scaffolder use
`description:`. **This is a documented naming inconsistency; `description:` is the enforced field.**

---

### THE INTENT BLOCK (§0.5)

Every skill's SKILL.md must open with `## Intent (§0.5)` carrying three declared layers:

- **Layer 1 (REQUIRED):** user outcome + bar — what the skill delivers + a success test in the user's voice
- **Layer 2 (REQUIRED):** role + autonomy position — who the skill IS and where it sits between fully-autonomous and human-in-the-loop
- **Layer 3 (ADVISED, multi-turn only):** per-turn anchor — the one line re-injected every turn (the Layer 3 text ALSO goes into the lean anchor file that `skill_anchor.sh` points at)

`new-skill.sh` stamps a REPLACE-prompted Intent block at birth. `enforce_skill_frontmatter.sh` does NOT
verify the Intent block is present — only `description:` + YAML parse + size are checked. The Intent
requirement is `[honor]` at this time.

The outward-facing gist of Layer 1 also goes into the `description:` frontmatter field (the caller-visible
line the harness reads to trigger the skill). These are the same substance at two altitudes.

---

### THE SIX-TRAIT QUALITY FRAMEWORK

The SOP (`system/sops/skill-building-sop.md §0`) defines six traits all skills are built to. These are
the design invariants, not a checklist:

1. **One front door, staged inside** — one command, one voice; no five skills where one door will do
2. **Leads, doesn't follow** — holds its frame against user drift; addressed by the anchor system (above)
3. **Trusts a file, not memory** — durable state in a file (scratchpad/brief), not fragile chat RAM
4. **Proves its work, never just claims done** — evidence over self-report; scaled to the stakes
5. **Right-sizes** — earn every step, gate, model-tier, and split; simplest thing that works
6. **Has a soul + a fence** — character that loves the work's virtue (ceiling); gates (floor)

**The three-floor enforcement model** (multi-step skills only, SOP §3):
- (a) **Reasoning / NL layer** — SKILL.md body; voice, judgment, procedure; probabilistic
- (b) **Deterministic enforcement layer** — hooks, guards, validators; where invariants live because code can't be talked out of them
- (c) **State / memory layer** — scratchpad, receipts, shared state file; infrastructure, not LLM responsibility

**Enforcement reliability ladder** (weakest → strongest):
1. Self-reported marker (`GATE CLEARED`) — fakeable; orientation only, never a guarantee
2. Required artifact — the deliverable must literally contain the section/heading; workhorse
3. Code-verified evidence — a script checks the real world; unfakeable; reserve for genuinely critical gates

---

### MULTI-PHASE SKILLS AND THE CONFORMANCE LAB

For skills declared with `--multiphase N`, `new-skill.sh` creates `skills/{name}/prompts/NN-phaseN.md`
drivers. Each driver is born with:
- `## Output contract` (what must exist on disk when the phase is done)
- `## do NOT` (hard rails for that phase)
- `✅ phase N complete` boundary marker

**The conformance lab** (`system/tools/conformance-lab/conformance.py`) grades multi-phase skills by
reading these contracts and slicing on the `✅ phase N complete` marker. The birth-stamp means
`conformance.py` grades the skill with zero new code — `extract_clauses` + `slice_phases` already read
this shape. The lab is a live tool (debt-ledger lines 424–429 confirm active work; last modified per
git status: `system/tools/conformance-lab/conformance.py` modified).

### THE PARTS LIBRARY + SPEC FACTORY (added to this element 2026-07-28 · S2.0)

Since 2026-07-24 the skill-system has grown a second half that this element did not cite: thirteen
Python modules shipped by the `[SKILL-SYSTEM]` factory window. They matter here because they are the
mechanism by which an `[honor]` instruction inside a skill becomes a `[hook]`-class gate.

- **`system/parts/*.py` (9) — the reusable gate primitives** a skill composes rather than re-invents:
  `phase_gate` (the completion stamp only code can write) · `forbidden_content` (the "do NOT yet"
  checker) · `order_lint` (section A must physically precede B) · `write_ledger` (queue → write →
  read back → mark every row) · `capture_gate_selftest` · `completeness_receipt` (native-id set-diff
  vs a pinned source) · `fanout_gate` · `residue_scrub` (hard cap that REFUSES rather than truncates)
  · `voted_judge` (K samples, folded fail-closed).
- **`system/factory/*.py` (4) — spec prose → enforceable gates:** `spec_units` (the mechanical
  denominator for a spec) → `extract_clauses` (atomic clauses + a coverage receipt) →
  `classify_clause` (the three-field sort) → `defeater` (every gate ships a companion built to BEAT
  it — adopted by this project as S2.2's hostile case-generator, arbitrated 2026-07-28).

**Ownership seam:** the factory window OWNS these modules and their factory-local plumbing; this
element only DESCRIBES them. Corrections to their behaviour go there, not here.

⚠ **Why this omission was invisible.** `generated_from_check.py` verifies that every *cited* path
still exists — it cannot detect a source that was never cited. Thirteen files entered the subsystem
and the drift gauge stayed green at `0 dead + 0 behind-code`. The sweep catches ROT, not OMISSION;
an element growing new code is a human/peer-window catch until a completeness check exists.

---

### STORES TOUCHED (complete list)

| Store | Hook/actor | Access |
|---|---|---|
| `~/lifehack-brain/skills/{name}/SKILL.md` | `enforce_skill_frontmatter.sh` (blocked Write), `auto_register_skill.sh` (reads title/note), `new-skill.sh` (Write) | WRITE at birth; guard on every subsequent Write |
| `~/.claude/run/anchor/anchor-{key}.flag` | `skill_anchor.sh` arm/clear/status, `skill_anchor_inject.sh` reads | WRITE (arm), DELETE (clear), READ (inject) |
| `~/.claude/skills/{name}/` | bootstrap/machine setup; harness discovers | SYMLINK (global skills only) |
| `desks/{desk}/.claude/commands/{name}.md` | `auto_register_skill.sh` | WRITE (stub creation; idempotent) |
| `skills/{name}/prompts/NN-phaseN.md` | `new-skill.sh --multiphase` | WRITE at birth |
| `system/templates/skill-template/SKILL.md` | authoring reference | READ |
| `system/tools/new-skill.sh` | authoring | EXECUTE |

---

### GATES AND ENFORCEMENT (the honest map)

**Live hook-enforced walls:**

1. **`enforce_skill_frontmatter.sh`** (PreToolUse Write, matcher `Write`) `[hook]`
   — BLOCKS the Write (exit 2) when a `skills/*/SKILL.md` lacks a non-empty `description:`, fails
   YAML parse, or exceeds 500 lines. **Only fires on full-content Write** (not Edit). Does not fire
   on archived/retired skill paths or template dirs.

2. **`auto_register_skill.sh`** (PostToolUse Write|Edit, matcher `Write|Edit`) `[hook]`
   — AUTO-CREATES a command stub for desk skills after a Write|Edit to the SKILL.md. For global
   skills: no-op (emits info stderr). Non-blocking (emits to stderr only; exit 0 always).

3. **`skill_anchor_inject.sh`** (UserPromptSubmit, matcher `""`) `[hook]`
   — RE-INJECTS the lean anchor body into every user turn when a skill has armed its anchor. Enforces
   the every-turn re-injection mechanically. DEGRADE-SAFE — never blocks a prompt.

**Honor-system (prose instruction only; no hook enforces):**

- **`## Intent (§0.5)` block present** `[honor]` — `enforce_skill_frontmatter.sh` checks only
  `description:` + YAML + size; the Intent block is not verified mechanically.
- **`description:` trigger-relevance** `[honor]` — the hook verifies non-empty; the quality
  (front-loaded keywords, trigger words before char 250) is prose instruction only.
- **`shape:` field present (CF-14)** `[honor]` — not checked by `enforce_skill_frontmatter.sh`;
  swept by the Archivist at audit time (CF-14 disposition: sweep, not hook).
- **Skill arms and clears its anchor** `[honor]` — the hook re-injects when a flag is armed;
  whether the skill actually arms at the right moment and clears on exit is skill-prose instruction.
- **Per-turn anchor kept lean (≤1200 chars)** — the injector enforces the ceiling mechanically,
  but the skill authoring the lean anchor file is `[honor]`.
- **Compliance with the six-trait framework, three-floor model, SOP §1–§5** `[honor]` — the full
  SOP is prose doctrine. Only the frontmatter shape + size + description are mechanically enforced.

---

### GAPS (documented fail-open conditions)

1. **`enforce_skill_frontmatter.sh` fires only on `Write`, not `Edit`** — an Edit that strips
   `description:` from an existing SKILL.md (or makes frontmatter YAML-invalid) is NOT blocked. The
   hook guards birth; a post-birth Edit that degrades the file is unguarded.
   **VERIFIED 2026-07-28 (S1.1 T1.5):** registration in the tracked `settings.json` is
   `PreToolUse` / matcher **`Write`** — confirmed from source, not inferred. **Live proof the dark
   path is real:** the SOP's own ceiling is **<500 lines** (`skill-building-sop.md`) and
   `skills/save/SKILL.md` currently stands at **871 lines** — it grew past the cap entirely through
   `Edit`, the path the guard cannot see. **This is the ONLY over-cap SKILL.md in the repo** (measured
   this session across all `skills/*/SKILL.md`; the Step-2 note claiming *two* over-cap files is wrong
   — the grandfather list needs one entry, not two).
   ⚠ **The FIX is deliberately NOT done here.** Flipping the matcher to `Write|Edit` needs a
   grandfather mechanism first or every subsequent edit to `/save` bricks. That is guard surgery →
   **Step 2**, per the operator's map-trust-now / system-optimization-later seam. What Step 1 owes is the
   honest LABEL, and this is it.

2. **`shape:` is not mechanically enforced** — `enforce_skill_frontmatter.sh` does not check `shape:`.
   A SKILL.md without `shape:` is written silently; CF-14 compliance is enforced only at Archivist
   audit time. (Disposition in `docs/skill-conformance.md §6`: `(b) sweep + build`.)
   **⚠ WORSE THAN UNENFORCED — THE FIELD IS DEGENERATE (measured 2026-07-28, S1.1 T1.5).** Of the
   **64** skill files carrying `shape:`, **48 (75.0%)** hold the identical value
   `interactive-workflow`; the remaining spread is `utility` ×12 and one each of `autonomous-run`,
   `command`, `panel-workflow`, `cron-producer`. A field where three quarters of the population shares
   one value **certifies nothing** — it cannot discriminate, so it cannot grade. Recording it here is
   load-bearing: without this label, Step 2's per-skill conformance checker would enforce `shape:` and
   stamp a conformance the system does not actually have. *(The 79% / 81-files / 64-identical figure
   carried in the plan is SUPERSEDED — it did not survive re-measurement. Repo-wide the count is
   71 files / 70.4%, and that wider figure includes a schema EXAMPLE line, not a real value; the
   skills-scoped number above is the one that means anything.)*

3. **`flow:` — RED LINE, no hand-backfill, ever (ruled 2026-07-28).** The `flow:` field must be
   **DERIVED** from a skill's real reads/writes when that derivation is built, or be **ABSENT**. It
   must never be hand-filled across the skill set. *"A partially hand-filled taxonomy is worse than no
   field, because it looks finished"* — it manufactures exactly the false-completeness that `shape:`
   above already demonstrates in the wild. This constraint binds every future step of this project.

4. **`auto_register_skill.sh` uses grep/sed not YAML parse for `title:` + `note:`** — if those fields
   have unusual quoting or multi-line values, the stub content may be garbled. No exit-2 protection.

5. **Anchor flag key collision on same-cwd parallel windows (without CLAUDE_CODE_SESSION_ID)** — when
   `CLAUDE_CODE_SESSION_ID` is not set, the key falls back to a 12-char SHA of `$PWD`. Two parallel
   sessions launched from the same working directory share the flag file and would clobber each other's
   anchor state. UNVERIFIED whether the env var is always set in the harness.

6. **`enforce_skill_frontmatter.sh` YAML fallback is weaker** — when the `yaml` Python library is not
   installed, the hook falls back to a regex presence-check for `description:`, which is NOT a parse
   check. A malformed frontmatter with a present but unparseable `description:` passes the fallback.

7. **`auto_register_skill.sh` has a known dead-code era (pre-2026-06-18)** — before the fix
   (`CLONE_ROOT` path added, line 39 comment), the hook was dead for clone writes. Desk skills
   authored in the clone before that date may lack command stubs. Existing stubs are not audited
   for staleness.

8. **Bash-write bypass (system-class gap, per §8.4b SYSTEM-CLASS GAP EXCLUSION):** `guard_write_paths.sh`
   fires on `Write|Edit` only; a Bash file-write bypasses the hook plane. This is an accepted,
   system-wide design (documented in `guard_write_paths.sh` header 2026-07-14). NOT derived as a
   skill-system-specific `·gap` — blast-radius is identical to the system baseline.

---

### INTEROP SEAMS

**SHARES** `pm_flag.sh` / `pm_persist.sh` pattern — `skill_anchor.sh` + `skill_anchor_inject.sh`
are a direct architectural mirror of the `pm_flag.sh` + `pm_persist.sh` pair (flag state manager +
UserPromptSubmit injector). Same session-key scheme; same TTL logic; same degrade-safe posture. Changes
to the session-key design or TTL mechanism should be applied to both pairs.

**FEEDS** `save` (memory-write element) — `/save`'s Step 7b (`machine-log.md`) and Step 7c (learnings)
record skill-related events when a session runs a skill and then saves. The skill system does not directly
write to `/save`'s stores; `/save` reads the session context.

**FEEDS** `label-checker` — the conformance-lab's multi-phase driver contracts (`## Output contract` +
`✅ phase N complete`) are the machine-readable seam the conformance grader reads. `new-skill.sh
--multiphase` creates this seam at birth; `conformance.py` consumes it. A skill born without
`--multiphase` has no graded contract and cannot be scored by the lab.

**TRIGGERS** `auto_register_skill.sh` — a Write or Edit to a `desks/{desk}/skills/{name}/SKILL.md`
automatically triggers stub creation. The save element (`/save`) may trigger this if it ever writes a
SKILL.md in the course of a session (e.g., a skill-build session where `/save` writes a modified
SKILL.md).

**CHAINS** `skill_anchor.sh` → `skill_anchor_inject.sh` — the anchor state manager arms a flag;
the injector reads the flag every turn. The injector is useless without the manager arming it; the
manager is pointless without the injector consuming it. They compose as one mechanism split across
the pre-tool (state) and per-prompt (inject) planes.

**READS** `system/sops/skill-building-sop.md` — the SOP is the canonical doctrine for all skill
authoring decisions. The hook's deny message explicitly names it (`skill-building-sop.md §0.5`). The
SOP is the highest-altitude authoring contract; the hook enforces the narrow mechanical subset.

**SYNCS** `docs/skill-conformance.md` — the frontmatter schema (`shape:`, `emit_diary:`, etc.) is
canonicalized in the conformance doc. The hook's deny message points there. Changes to the schema must
land in the conformance doc first; the hook and scaffolder are updated in the same commit.

**READS** `system/templates/skill-template/SKILL.md` — the canonical template that `new-skill.sh`
was designed from. The template and the scaffolder must stay in sync; the scaffolder's stamp IS the
template's required structure.

**GUARDED-BY** `enforce_skill_frontmatter.sh` (Write birth guard) · `skill_anchor_inject.sh`
(every-turn anchor re-injection) · `auto_register_skill.sh` (stub creation post-write)

---

### INTENT / CURRENT-VS-TARGET

**BY DESIGN:** the `enforce_skill_frontmatter.sh` guard is intentionally Write-only (not Edit) — the
hook targets birth conformance (the 46-skill remediation proved skills are born malformed, not
degraded-in-place). Post-birth Edit protection is deferred as KISS (an Edit stripping `description:`
is detectable but uncommon; the birth guard is the 80/20 fix).

**BY DESIGN:** `auto_register_skill.sh` skips global skills to avoid duplicate harness entries — the
`~/.claude/skills/` symlinks ARE the registration for global skills; a stub would create a collision.

**PARTIAL, for a specific reason:** the anchor system (arm + inject) is live and mechanically enforced
for every-turn re-injection — this is fully `[hook]`. But whether a skill actually ARMS the anchor at
the right moment, writes a lean (<1200 char) anchor file, and CLEARs it on exit is `[honor]` (skill
prose only). The injection mechanism is solid; the skill's adoption of it is not. Mixed → **PARTIAL**.

**The `shape:` gap is the largest open structural hole:** CF-14 (every SKILL.md has `shape:`) is
disposition `(b) sweep + build` — enforced at Archivist audit time, not at write time. This means a
skill can be born without `shape:` (the scaffolder stamps it; but a hand-authored or edited SKILL.md
can drop it). The `docs/skill-conformance.md §6` table marks this as `build` status (not `live`).

**TARGET:**
1. **Extend `enforce_skill_frontmatter.sh` to cover Edit** — catch a post-birth Edit that strips
   `description:` or makes frontmatter invalid. Requires parsing the merged result of old+new, not
   just the content field.
2. **Add `shape:` to the frontmatter enforcement hook** — promote CF-14 from sweep to hook-enforced
   birth guard. Add one YAML check to the existing Python block.
3. **Audit existing skills for missing `shape:`** — the Archivist sweep (`/archivist-audit
   scope=skills`) surfaces this; the `[SKILL-SOP-FIXES]` debt-ledger item (line 214) tracks the
   46-skill backlog with scorecards at `state/projects/skill-sop-audit/`.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL·gap
- **check_detail:** Three live hooks constitute the enforcement surface:
  (1) `enforce_skill_frontmatter.sh` — PreToolUse Write, exit-2 BLOCKS non-conformant SKILL.md writes
  (description + YAML + 500-line cap); settings.json line 147–154. Write-only (not Edit).
  (2) `auto_register_skill.sh` — PostToolUse Write|Edit, creates desk command stubs automatically;
  settings.json line 283–291. Non-blocking (stderr only).
  (3) `skill_anchor_inject.sh` — UserPromptSubmit matcher "", re-injects anchor body every turn when
  armed; settings.json line 347–355. DEGRADE-SAFE (never blocks).
  What is honor-system: `## Intent (§0.5)` block presence · `description:` trigger-quality (keywords
  front-loaded before char 250) · `shape:` field (CF-14, sweep-not-hook) · skill's own arm/clear of
  anchor · lean anchor file authoring · all six-trait quality traits · SOP §1–§5 compliance.
  Birth conformance is mechanically enforced for the minimal set (description + YAML + size);
  behavioral quality and structural completeness are honor. Mixed → **PARTIAL**. Not "unprotected" —
  the birth guard blocks the worst class of defect (invisible-to-harness skill from missing
  description); the structural and behavioral quality surface is large and honor-only.
