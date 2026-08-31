---
element: project-manager
title: "project-manager — element detail (ground/base altitude)"
subsystem: project-state
altitude: base
record_type: organism-element
maturity_label: PARTIAL (honor)
generated_from:
  - skills/project-manager/SKILL.md
  - system/hooks/pm_persist.sh
  - system/hooks/pm_flag.sh
  - system/hooks/scratch_capture_gate.sh
  - system/hooks/scratch_sweep_nudge.sh
  - system/hooks/save_routing_hint.sh
  - system/hooks/skill_anchor.sh
  - system/hooks/skill_anchor_inject.sh
  - system/hooks/announce_plan_write.sh
  - system/hooks/guard_write_paths.sh
  - system/tools/pad_archive.py
  # CORRECTED 2026-08-27 (L.B2 audit, live run): this bare path does not exist —
  # `python3 system/tools/pad_archive.py` → "No such file or directory". The tool's real
  # location is system/tools/save/pad_archive.py (confirmed present and runnable). Every
  # mention of "system/tools/pad_archive.py" below carries the same stale path.
  - system/tools/pm_flag_recover.py
  - system/schemas/project-doc-schema.md
  - system/reference/settings.json
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# project-manager — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. Each marker records what
> happened to that file AT THIS DESTINATION; none of them changes the description.
>
> ⛔ `system/tools/check_slug_folder.py` is the donor's path and is not here. The tool ITSELF did land — it
> ships as `system/tools/project-manager/check_slug_folder.py`, with its test beside it; only the flat
> `system/tools/` location did not come across.
>
> ⛔ `state/debt-ledger.md` is the person's own notes, not a repo file. Here it is
> `<notes>/state/debt-ledger.md`, written by `/save` and `/build` when something is knowingly left imperfect
> (`docs/data-layout.md`). It is created by use, and never committed.

> **LADDER: ELEMENT (full mechanics). up → manual#project-manager ; ground truth → skills/project-manager/SKILL.md**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds mechanics of the brief lifecycle
> engine: how a project doc is created (with human-in-the-loop Frame intake), kept alive across
> turns, compacted losslessly, and dissolved at session end. The MIDDLE manual (`system/organism/manual.md`)
> carries only a one-line pointer here; the TIP (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **One-line:** arm a session-scoped flag → re-inject the active brief on every turn → run HITL Frame
> intake on create → compact the scratchpad losslessly at close → block the Stop event until capture
> is confirmed.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).
>
> **Primary contract is (honor):** the RECEIPT-GATE, FRAME immutability, STORY LOG append-only, and
> journal-first ordering are all skill-prose / schema mandates — no blocking hook enforces them on the
> main path. The stop-capture gate is a real blocker; see Phase 7. (See §8.4b of map-format-specs.md.)

---

## AUTHORED   (human-only)

### TRIGGERS / MODES

`project-manager` has five distinct operating modes. Modes 1–2 are mutually
exclusive at invocation; Modes 3–5 are always-on machinery that runs regardless of
mode.

**Mode 1 — Doc-lifecycle (doc-track)**
Triggered by: `/project-manager`, "where are we on", "rehydrate", "start a project
doc", "update the project doc", or any multi-session work handoff where the user
needs the living doc. Shape: `interactive-workflow` (SKILL.md frontmatter). This is
the default mode — the brief is the artifact; the persistence machinery keeps it alive.
Encompasses: Phase 0 (Frame intake on CREATE), Phase 1a (arm flag), Phases 2–8.

**Mode 2 — Build-conductor (build-track, additive)**
Active when the project is a build — software, hook, skill, dashboard, any
make-a-thing work. Adds to doc-lifecycle mode: Phase 1b (arm skill_anchor.sh),
the ORIENTATION HANDSHAKE (do this FIRST, before any self-directed work — four-beat
output: Identity+posture / State-of-play ≤3 lines / Recommended-next-move /
Hand-over-the-wheel menu), the scoping Q&A (batched, ≤3–5 questions/round, lead with
best guess), and the build recipe (Phase→Feature→Task plan, decompose by surface,
gear-tagged fan-out). The anchor (`ANCHOR.md`) re-injects the four-gear build spine
every turn via `skill_anchor_inject.sh`
(settings.json:347 — UserPromptSubmit, no matcher). Off-switch: `skill_anchor.sh clear`
(12h TTL backstops). (SKILL.md — "Build mode — arm the four-gear conductor")

**Mode 3 — Per-turn orientation injection (always-on)**
`pm_persist.sh` runs every UserPromptSubmit (settings.json:337, empty matcher = fires
on every prompt) as long as a pm-flag is armed. Not a user-invocable mode — it is the
ambient engine. (Phase 2 below.) (Armed-flag/routing-state angle — how pm_persist reads
and re-fires the session flag hub — see `pm-flag` element.)

**Mode 4 — Compaction / pad-archive (triggered at /save only, session-close)**
The AUTOMATIC + LOSSLESS compaction procedure: archive → RECEIPT-GATE → classify →
journal-first → clear → self-heal → 2nd-pass → receipt print. (Phase 6 below.)

**Mode 5 — Stop-event checkpoint (always-on while flag armed)**
`scratch_capture_gate.sh` runs every Stop event (settings.json:448) and blocks the
stop if uncaptured scratchpad content has appeared since the last bucket checkpoint.
(Phase 7 below.)

---

### FULL HAND-OFF CHAIN

#### Phase 0 — Frame intake (on CREATE — the HITL gate)

**Step 0 — gather and confirm the human-only frame before treating doc as authoritative**
`[skill]` Triggered on every new brief CREATE (not on resume). The 7-step process
(SKILL.md — "Frame intake — the human-in-the-loop gate"):

1. **Gather (silent).** Run reconstruction passes; fill every EXTRACTABLE slot; form
   a best-guess for each HUMAN-ONLY slot (desired outcome, success criteria,
   constraints, scope edges). Ask nothing yet.
2. **Scorecard.** Rate every frame slot: `CONFIRMED` / `INFERRED` / `THIN` / `MISSING`.
   Full critical-slot list: `references/intake_questions.md`
   (skills/project-manager/references/intake_questions.md).
3. **Reflect-back round.** Present the scorecard in one round. For each un-CONFIRMED
   slot, show the inferred guess labeled, ask the user to confirm / correct / fill.
   Never ask cold — always lead with best guess.
4. **Re-score.** Update slot states from answers. New answers may open new gaps.
5. **Hard gate. `[human]`** Treat the doc as authoritative and proceed ONLY when every
   **critical** slot (desired outcome / definition of done / success criteria /
   constraints & non-negotiables / scope edges) is `CONFIRMED` or `WAIVED`. If any
   critical slot is still unconfirmed → ask again with updated guess. Loop until met;
   do NOT silently proceed on guesses.
6. **Waiver.** User may decline any slot ("skip it," "just go"). Mark `WAIVED`, record
   as deliberate gap, proceed without nagging. A blanket "just go" waives all critical
   slots at once.
7. **Record + persist.** Write a **Frame confidence** block into the doc (each slot +
   state + value). Once `CONFIRMED`/`WAIVED`, the slot persists — a later session reads
   this block and does NOT re-interrogate settled slots.

Enforcement: `[human]` — this gate is behavioral, fully procedural. No hook blocks a
brief write that bypasses Frame intake. Proceeding without it is an honor violation.

For a NEW BUILD in build-conductor mode: the Frame intake and the scoping Q&A are the
SAME engine — the scoping Q&A IS the Frame intake gate on a brand-new build (SKILL.md
— "New build vs ongoing").

---

#### Phase 1 — Arm (skill → flag → hook activation)

**Step 1a — skill arms the pm flag**
`[skill]` project-manager SKILL.md → `bash "$HOME/lifehack-brain/system/hooks/pm_flag.sh" arm "<abs_doc_path>" "<slug>" "<desk>"` → writes `~/.claude/run/pm/pm-sess-<CLAUDE_CODE_SESSION_ID>.flag` (cwd-hash fallback when env var absent).

Flag file payload (six key=value lines):
```
doc_path=<abs_doc_path>
slug=<slug>
desk=<desk>
armed_at=<epoch>
cwd=<PWD at arm time>
session=<CLAUDE_CODE_SESSION_ID or empty>
```
Also appends a TSV breadcrumb line to `~/.claude/run/pm/arm-events.log` (format:
`<ts>\tarm\t<doc>\t<slug>\t<desk>\t<session>`). Log is append-only, capped at 500 lines
by prune-on-write (`pm_flag.sh` line 34–35; `PM_EVENTLOG_MAX=500`). The clear subcommand
appends a `clear` line so `pm_flag_recover.py` can distinguish intent from TTL expiry.

TTL: `TTL_HOURS` default **36h** in `pm_flag.sh` (line 17). The `status` subcommand
self-expires stale flags (line 54: `if NOW - armed_at >= 36*3600 → rm flag → echo "none"`).

**Step 1b — build-conductor mode: arm the anchor (optional)**
`[skill]` `bash "$HOME/lifehack-brain/system/hooks/skill_anchor.sh" arm project-manager "$HOME/.claude/skills/project-manager/ANCHOR.md"` → re-injects the four-gear build spine every turn via `skill_anchor_inject.sh` (UserPromptSubmit, no matcher, settings.json:347). TTL: 12h (`skill_anchor.sh` line 19: `TTL_HOURS="${ANCHOR_TTL_HOURS:-12}"`). Off-switch: `skill_anchor.sh clear`.

**Step 1c — build-conductor ORIENTATION HANDSHAKE (do this FIRST on build invocation)**
`[honor]` Immediately on invoking or re-invoking project-manager in build-conductor
mode, the lead's **first output to the user** is the four-beat handshake (SKILL.md —
"On invocation — the ORIENTATION HANDSHAKE"):
1. **Identity + posture** — project name + "Build mode armed: I stay at 10,000 ft."
2. **State of play — ≤3 lines** — done / in-flight / blocked. Scannable.
3. **Recommended next move** — single highest-value next step + how the lead would run it
   (gear tag). Plus: "also waiting on you: …" if other open decisions exist.
4. **Hand over the wheel — the menu:** Go / Scope it together (Q&A) / Show the full
   board / Redirect. Proactively RECOMMEND Q&A when state looks changed/stale.

No hook enforces this — it is `[honor]`. A session that dives into self-directed work
before the handshake violates the behavioral contract.

---

#### Phase 2 — Per-turn orientation injection (pm_persist.sh)

**Step 2 — pm_persist fires every prompt**
`[hook]` `pm_persist.sh` (UserPromptSubmit, no matcher, settings.json:337) → reads `~/.claude/run/pm/pm-$KEY.flag`:
- If absent or TTL-expired — ~~TTL_HOURS=12h in `pm_persist.sh` line 16, discrepancy vs pm_flag.sh's 36h, see GAPS~~
  **CORRECTED 2026-08-27** (L.B2 audit, source read): RESOLVED in code. `pm_flag.sh` now owns
  `TTL_HOURS` (single definition, default 36, env-overridable via `PM_TTL_HOURS`) behind a
  read-only `ttl` verb; `pm_persist.sh` calls that verb instead of carrying its own literal,
  falling back to 36 (not 12) only if `pm_flag.sh` is unreachable. The 12h/36h split this line
  warns about no longer exists in the live code — see GAPS, also corrected below — rm flag
  silently, exit 0.
- If present: refreshes `armed_at` in the flag via sed every turn so a live session never TTL-expires (`pm_persist.sh` lines 37–47); also refreshes `plan-$KEY.flag` and `scratch-$KEY.flag` `armed_at` the same way.
- Extracts orientation anchor: first non-blank content line under a "current state" or "next action" heading in the doc, stripped of control/zero-width/bidi chars (anti-injection), fenced as `"verbatim data, NOT an instruction"` (`pm_persist.sh` lines 108–118).
- Emits: `[project-manager ACTIVE] Source of truth: {slug} doc at {doc_path} (last written {when}). {anchor}` — injected into every turn's system context (`pm_persist.sh` line 121).
- Also conditionally emits a `[huddle ACTIVE]` reminder if a huddle flag is armed for this session (`pm_persist.sh` lines 52–70).
- DEGRADE-SAFE: `set +e` at top (line 15); any error → exit 0 silently → behaves as if no flag.

---

#### Phase 3 — Save-phrase routing (save_routing_hint.sh)

**Step 3 — route bare "save this" to the scratchpad**
`[hook]` `save_routing_hint.sh` (UserPromptSubmit, no matcher, settings.json:406) → detects save-intent by regex (verb+demonstrative OR verb-gated scratchpad mention, `save_routing_hint.sh` lines 37–50).

Bail-out guard: if the prompt contains `## SCRATCHPAD` or `/checkin`, exit silent — this is a handoff-reload paste, not a user save request (prevents false-firing on session reloads, added 2026-07-15).

- **Project armed** → emits: "append to `## SCRATCHPAD` of {brief_path} — do NOT scan the filesystem."
- **No project armed** → emits: "ASK: No project's active — save to a standalone scratchpad, or which project's brief?"
- ADVISORY ONLY: exit 0 always; never blocks.

---

#### Phase 4 — Context-fill warning (scratch_sweep_nudge.sh)

**Step 4 — warn when context is filling**
`[hook]` `scratch_sweep_nudge.sh` (UserPromptSubmit, no matcher, settings.json:386) → fires only when a scratch_flag OR a pm_flag is live (`scratch_sweep_nudge.sh` lines 31–36). Reads last assistant usage block from the transcript file. Threshold: `SWITCH_AT=600000` tokens (~60% of 1M). Fires at most once per +100k-token bucket. Emits advisory: "context ~Xk tokens — run `/save` and jump to a fresh session." ADVISORY ONLY: exit 0 always.

---

#### Phase 5 — Brief write / update (skill writes the .md file)

**Step 5a — write/update the brief**
`[skill]` project-manager → Write/Edit → brief at one of:
- `$DRIVE/state/projects/{slug}/brief.md` (v2 folder, root/cross-desk)
- `$DRIVE/desks/{desk}/projects/{slug}/brief.md` (v2 folder, desk)
- `$DRIVE/state/briefs/{slug}.md` (legacy flat)
- `$DRIVE/desks/{desk}/state/briefs/{slug}.md` (legacy flat, desk)

Drive root: `$LIFEHACK_ROOT`.

**F0.4 (HARD):** the folder leaf MUST equal the slug. Auditable via `system/tools/check_slug_folder.py`; no hook enforces this at write time. `[honor]`

**Step 5b — scratchpad self-heal on touch (write-time guard)**
`[skill]` If the brief EXISTS but is missing the `## SCRATCHPAD` section (schema §7):
ADD an empty section when touching the brief. Never leave a re-entered brief without its
scratchpad — it is where the sweep-nudge and `/checkin` capture notes. Add the heading
+ the standard sub-labels; touch nothing else. (SKILL.md core mandate 2a.)
Enforcement: `[skill]` (SKILL.md mandate, no hook verifies the section exists before Write).

**Guards that fire on brief Write/Edit:**
- `[hook]` `guard_write_paths.sh` (PreToolUse Write|Edit): any path under `$DRIVE_ROOT/` → exit 0 (allow). ~~Any path outside → exit 1 (BLOCK).~~ **CORRECTED 2026-08-27** (L.B2 audit, live test): the catch-all deny is gated behind `GUARD_WRITE_PATHS_MODE`, which **defaults to `warn`** — live writes to both `/tmp/outside_zone_test.md` and `/etc/passwd` return exit 0 (ALLOWED, only logged to a warn-log), not blocked, as currently shipped. The write gate is path-based only — does not inspect section content. **KNOWN GAP (accepted, documented in guard_write_paths.sh line 16): Bash heredoc/tee/cp writes to the brief bypass this guard entirely** (guard fires only on Write/Edit tool calls) — confirmed live: matcher is `Write|Edit` only, no Bash.
- `[hook]` `guard_canon_write.sh` (PreToolUse Write|Edit): briefs are not canon paths → passes through.
- `[hook]` `validate_on_write.sh` (PostToolUse Write|Edit): general frontmatter nudge; no brief-specific logic confirmed. Non-blocking.
- `[hook]` `nudge_flow_drift.sh` (PostToolUse Write|Edit): advisory nudge if writing drifts off altitude. Non-blocking.
- `[hook]` `auto_register_skill.sh` (PostToolUse Write|Edit): fires but acts only on skill-file paths — silent on briefs.
- `[hook]` `observability_logger.sh` (PostToolUse `*`): logs every tool use.

**Required spine (SKILL.md — "Structure — fixed HEADERS"):** stamp verbatim on every brief CREATE, in order:
- `## 0. 🛑 LLM NOTICE` (the "fine china" guard — read-only notice to LLMs)
- `## 1. FRAME` (desired outcome · success criteria · constraints · scope edges — human-only, LLM read-only)
- `## 2. CURRENT STATE — the DECISION BOARD` (✅ LOCKED · ⛔ RULED-OUT · ❓ OPEN)
- `## 4. STORY LOG` (append-only chronological arc — tried → outcome → STATUS: locked | superseded-by | open → why/lesson)
- `## 5. OPEN LOOPS / NEXT ACTIONS`
- `## 6. KEY RESOURCES / IDS`
- `## 7. SCRATCHPAD` (the ephemeral live working surface; the compaction source)
- `## 8. ARTIFACTS`
- `## + CHRONICLE POINTER` (footer — one line, not a numbered section; schema §8 / `## + CHRONICLE POINTER`, `system/schemas/project-doc-schema.md` line 167)

(No `## 3` — the old DON'T-RETRY is retired; its scan lives in §2's RULED-OUT bucket.)

**CREATE vs UPDATE gate:** on CREATE, the FRAME section is human-only. The skill runs the
Frame intake gate (Phase 0) — scoping Q&A to confirm desired-outcome / success-criteria /
constraints — or stubs each slot as `INFERRED / UNCONFIRMED` for explicit human confirmation.
`[human]` gate. No hook enforces the FRAME's read-only constraint — enforcement is schema text
+ `[honor]`.

Each project folder also holds a `canon.md` (always-true-HERE facts, PROPOSED not auto-written;
each line self-explanatory to a cold, zero-context session — scoped canon may be richer than
desk-wide canon). This is a PROPOSED file — the skill proposes it; human approves and maintains
it; it is not auto-created. (SKILL.md — "Where the project doc lives", schema §9.)

---

#### Phase 6 — Compaction / pad-archive (the lossless clear path)

Triggered at `/save` only, at session-close (`/checkin` harvests notes into the scratchpad and appends confirmed decisions to the Story Log, but never triggers this compaction procedure). Strict 8-step order from
`system/schemas/project-doc-schema.md` → "BRIEF COMPACTION". This is the skill's most
structurally significant mechanism.

**Step 6a — Copy-everything-first (pad_archive.py archive)**
`[skill]` `python3 $HOME/lifehack-brain/system/tools/pad_archive.py archive "<abs_brief_path>"` →
reads the `## SCRATCHPAD` section verbatim from the brief (lossless bias: under-capture stopped only
at ARTIFACTS/CHRONICLE POINTER section — `pad_archive.py` `END_SECTION_RE` line 51 — else captures
to EOF) → appends a chained, self-describing block to `{brief}.pad-archive.md` (beside the brief,
append-only) → reads back to confirm the block landed (readback-verify) → prints `RECEIPT <sha256>`
on exit 0.

Archive block header format: `<!-- pad-archive :: compaction #N :: <ISO-ts> :: host=<hostname> :: prev=<prev-sha256> :: hash=<sha256> -->`. Idempotent: unchanged pad → no duplicate block, re-emits RECEIPT.

~~Two permissions allowlist entries in settings.json (lines 12–13) ensure pad_archive.py runs without
a prompt: `Bash(python3 $HOME/lifehack-brain/system/tools/pad_archive.py:*)` and the absolute-path
form. This is the ONLY explicit tool-level allow for pad_archive.~~ **CORRECTED 2026-08-27** (L.B2
audit, live grep across repo .claude/settings.json, repo `.claude/settings.local.json` ⛔ (gitignored, machine-local, not tracked here — searched at its live path, not this repo), user
`~/.claude/settings.json`, and this skill's own `settings.local.json`): zero matches for
"pad_archive" anywhere in any settings file found. No permissions-allowlist entry for
`pad_archive.py` exists today — it runs (if it runs) under whatever ambient Bash permission
already covers it, not a dedicated allow.

`[skill]` then runs `pad_archive.py verify "<abs_brief_path>"` → chain + counter integrity check.
Exit 0 = intact; exit 2 = missing or malformed archive; exit 3 = chain/counter integrity break (both surface a warning but do NOT block this run's clear).

**Step 6b — Receipt-gate (FAIL-CLOSED)**
`[skill]` **RECEIPT-GATE:** the clear in Step 6e is FORBIDDEN without a fresh exit-0 RECEIPT from
Step 6a. If pad_archive.py was not called, errored, or exited non-zero → **ABORT:** prepend
`> ⚠ COMPACTION ABORTED {ts} — archive not confirmed; pad left intact` to `## SCRATCHPAD` and
surface to user. pad_archive.py exits 2 on any failure.

**This gate is PROCEDURAL ONLY** — the skill text and schema mandate it, but no hook blocks a model
that clears the pad without calling pad_archive.py. **See GAPS.**

**Step 6c — Classify + graduate (model judgment)**
`[honor]` Classify each scratchpad item:
- Settled decision / win → STORY LOG (`STATUS: locked`) + DECISION BOARD ✅ LOCKED
- Dead-end / demoted / stale → STORY LOG (`STATUS: superseded/killed`, with why) + DECISION BOARD ⛔ RULED-OUT
- Open thread → OPEN LOOPS + DECISION BOARD ❓ OPEN
- Resource/ID/path → KEY RESOURCES
- Pure choreography with no lasting lesson → drop (safe in archive from 6a)
NEVER touch §0 / §1 FRAME content.

**Step 6d — Journal-first for precious keepers**
`[honor]` Every precious keeper (decision / dead-end / number) → append to `system/journal.md`
before/as it lands in the brief. The brief is overwritten in place; the journal is the only
append-only backstop. No hook enforces the journal-first ordering.

**Step 6e — Clear graduated items**
`[skill]` Only after a fresh RECEIPT: `Edit` → remove graduated items from `## SCRATCHPAD`. Leave
unresolved/recent items.

**Step 6f — Self-healing completeness diff**
`[honor]` For each cleared item: mechanical pre-filter (text present in STORY LOG?) → meaning-judge
the residual → if a durable item did NOT land → write it into STORY LOG now (self-heal, not flag).
Count = `{H}` healed.

**Step 6g — Independent second-pass**
`[honor]` Spawn one isolated read-only sonnet subagent → compare newest `{brief}.pad-archive.md`
block vs durable sections → return any durable item not represented → main session writes confirmed
misses. Spawned by model decision; no harness-level guarantee it runs every compaction.

**Step 6h — Print receipt**
`[skill]` Print: `📝 Compaction: Story Log +{S} · board ✅{L}/⛔{K}/❓{J} · dropped {D} · self-healed {H} · 2nd-pass recovered {R} · archive #{N}.` (canonical format per `system/schemas/project-doc-schema.md` line 219)

---

#### Phase 7 — Stop-event checkpoint (scratch_capture_gate.sh)

**Step 7 — block the stop if scratchpad is uncaptured**
`[hook]` `scratch_capture_gate.sh` (Stop event, no matcher, settings.json:448). Resolves active
pad by precedence: (1) `scratch_flag` armed → its `scratch_path`; (2) else `pm_flag status` →
brief's `## SCRATCHPAD` section; (3) else dormant.

Reads last assistant usage block from the transcript to get the token count. Buckets every 100k
tokens. On first sight of the session, seeds the watermark + sidecar (a checkpoint snapshot of the
current scratchpad section), then exits 0 — never bounces on turn one.

When a new bucket is crossed (capture is DUE):
1. Mechanically diffs current scratchpad section vs the sidecar checkpoint → computes ADDED lines.
2. Advances watermark (bucket + sidecar) for the next checkpoint.
3. Emits `{"decision":"block","reason":"..."}` → **BLOCKS the stop**, instructing the model to:
   - Verify ADDED lines, append anything missing.
   - Print a `📝 SCRATCHPAD CAPTURED —` receipt in the visible reply showing the captured lines.
4. Loop-safe: `stop_hook_active` guard in the JSON input (line 39) → if already bounced this turn, exit 0 (prevents infinite Stop-block loop).
5. If ADDED is empty: emits a softer block instructing the model to append a `(no new decisions)` dated line if genuinely nothing new.

DEGRADE-SAFE: `set +e` at top; any error → exit 0 (allow stop, never wedge a turn).

---

#### Phase 8 — Off-switch

**Step 8 — clear the flag**
`[skill]` "stop tracking" / `/project-manager done` → `bash "$HOME/lifehack-brain/system/hooks/pm_flag.sh" clear` → removes `~/.claude/run/pm/pm-$KEY.flag` and any session-matching flags in `$FLAGDIR`. Appends a `clear` breadcrumb to arm-events.log. TTL auto-expiry (36h, single-sourced in pm_flag.sh, ~~12h in pm_persist.sh line 16 — TTL discrepancy~~ **CORRECTED 2026-08-27, see GAPS: resolved in code**) also clears stale flags.

---

### PORTS TOUCHED

`pm_flag.sh arm/clear/status` · `pm_persist.sh` (reads the flag, refreshes armed_at, emits system note) · `scratch_capture_gate.sh` (reads flag, reads brief scratchpad section, emits block) · `save_routing_hint.sh` (reads flag, emits routing hint) · `scratch_sweep_nudge.sh` (reads flag, reads transcript usage) · `skill_anchor.sh / skill_anchor_inject.sh` (build-mode addendum only) · `pad_archive.py archive/verify` (reads + appends to pad-archive) · `pm_flag_recover.py` (reads arm-events.log, assists /save Step 0.4) · Write/Edit → brief.md · Write/Edit → brief.md.pad-archive.md · guard_write_paths.sh (PreToolUse Write|Edit) · observability_logger.sh (PostToolUse `*`)

---

### OUTCOME

Any session that arms a project remains continuously oriented to the brief: the doc path and current
state are re-injected every turn; Frame intake confirms the human-only slots before the doc is treated
as authoritative; save-phrase routing is automatic; the scratchpad is archived and verified before any
clear; the Stop event is blocked until capture is confirmed. The result is cross-session durable
continuity — a cold session reads the brief and picks up exactly where the last left off, with no
durable material lost.

---

### STORES (exact paths)

| Store | Path | Writable by |
|---|---|---|
| Active flag | `~/.claude/run/pm/pm-sess-<CLAUDE_CODE_SESSION_ID>.flag` (or `pm-cwd-<hash>.flag`) | pm_flag.sh arm/clear |
| Arm-events log | `~/.claude/run/pm/arm-events.log` | pm_flag.sh arm/clear (append-only, capped 500 lines — pm_flag.sh line 34–35) |
| Brief (v2 folder, root) | `$DRIVE/state/projects/{slug}/brief.md` | skill / /save |
| Brief (v2 folder, desk) | `$DRIVE/desks/{desk}/projects/{slug}/brief.md` | skill / /save |
| Brief (legacy, root) | `$DRIVE/state/briefs/{slug}.md` | skill / /save |
| Brief (legacy, desk) | `$DRIVE/desks/{desk}/state/briefs/{slug}.md` | skill / /save |
| canon.md (per-project) | `{project-folder}/canon.md` | skill PROPOSES; human approves — not auto-written |
| Pad-archive | `<abs_brief_path>.pad-archive.md` (beside the brief, append-only chained) | pad_archive.py only |
| Scratch-capture state | `~/.claude/run/scratch-capture/cap-sess-<SID>.state` + `.pad` (sidecar) | scratch_capture_gate.sh |
| Context-sweep state | `~/.claude/run/sweep/sweep-<key>.state` | scratch_sweep_nudge.sh |
| Journal backstop | `$DRIVE/system/journal.md` | skill / /save (journal-first rule) |
| Project registry | `$DRIVE/system/project-registry.md` | skill (on first project write) |
| Plan pointer | `~/.claude/plans/` (machine-local; ⛔ NOT mirrored to Drive — `mirror_plans.sh` does not exist in this repo, verified 2026-08-25; the only copy lives on the machine that wrote it) | announce_plan_write.sh / Claude plan mode |

---

### ENFORCEMENT POINTS (the honest map)

| Gate | Mechanism | Blocking? | Source ref |
|---|---|---|---|
| Brief Write path | guard_write_paths.sh PreToolUse Write\|Edit: Drive root → allow (exit 0); else → ~~exit 1 BLOCK~~ **CORRECTED 2026-08-27**: WARN-ONLY by default (`GUARD_WRITE_PATHS_MODE=warn`) — live-confirmed exit 0/allow, only logged, not blocked (line 141) | ~~BLOCKING~~ WARN-ONLY BY DEFAULT (on Write/Edit tool calls) | guard_write_paths.sh:71–73 (allow path), :141 (warn path) |
| Bash-write bypass | guard_write_paths.sh does NOT intercept Bash heredoc/tee/cp — KNOWN GAP (accepted, 2026-07-14) | UNGUARDED | guard_write_paths.sh line 16 comment |
| Flag TTL (per-turn) | ~~pm_persist.sh line 82–84: `NOW - armed_at >= 12*3600`~~ **CORRECTED 2026-08-27**: pm_persist.sh no longer carries an independent literal — it reads the TTL from `pm_flag.sh`'s read-only `ttl` verb (36h), falling back to 36h (not 12h) only if `pm_flag.sh` is unreachable → rm flag, exit 0 | Advisory (silently expires, no error) | pm_persist.sh (current source) |
| Flag TTL (arm-time) | pm_flag.sh: `TTL_HOURS="${PM_TTL_HOURS:-36}"`, single source of truth, exposed via `ttl` verb | Advisory | pm_flag.sh |
| pad_archive.py execution | ~~settings.json permissions allowlist lines 12–13: both path forms of `pad_archive.py`~~ **CORRECTED 2026-08-27: zero matches for "pad_archive" in any settings file, live-grepped — no dedicated allow exists** | ~~Allow (no prompt)~~ UNVERIFIED | n/a (citation was stale) |
| RECEIPT-GATE (pad clear) | Skill text + schema mandate: no clear without exit-0 RECEIPT this run; pad_archive.py exits 2 on failure | PROCEDURAL ONLY — no hook enforces | SKILL.md lines 401–405, schema:195–198 |
| FRAME read-only | `## 0. 🛑 LLM NOTICE` + `## 1. FRAME` warning stamped verbatim in every brief; no Write\|Edit guard checks section content | PROCEDURAL ONLY — no hook enforces | schema:72–78 |
| STORY LOG append-only | Schema rule: "never drop or rewrite an entry"; no hook enforces | PROCEDURAL ONLY — no hook enforces | schema:124–125 |
| Journal-first ordering | SKILL.md doctrine + schema §4 hard rule; no hook enforces sequence | PROCEDURAL ONLY — no hook enforces | SKILL.md:382–389, schema:48–49 |
| Frame intake gate | 7-step HITL process; no hook forces the intake before write; behavioral contract + [human] gate | PROCEDURAL ONLY — no hook enforces | SKILL.md "Frame intake" section |
| Orientation handshake (build) | First-reply behavioral rule in build-conductor mode; no hook fires | PROCEDURAL ONLY — no hook enforces | SKILL.md "Orientation Handshake" section |
| Scratchpad self-heal on touch | SKILL.md core mandate 2a; no hook verifies ## SCRATCHPAD section exists before Write | PROCEDURAL ONLY — no hook enforces | SKILL.md:197 |
| Stop-capture gate | scratch_capture_gate.sh emits `{"decision":"block"}` when capture is due | BLOCKING on the stop turn | settings.json:448, scratch_capture_gate.sh |
| Save-phrase routing | save_routing_hint.sh: advisory inject | Advisory (exit 0) | settings.json:406 |
| Context-fill warning | scratch_sweep_nudge.sh: advisory inject | Advisory (exit 0) | settings.json:386 |
| slug=folder-leaf (F0.4) | SKILL.md HARD rule; `check_slug_folder.py` is the audit tool; no gate at write time | PROCEDURAL ONLY — no hook enforces | SKILL.md F0.4 |
| guard_throughline_write_scope.sh (PreToolUse Write\|Edit) | Fires on every Write\|Edit; armed only during a /throughline session (throughline_flag.sh); passes through silently on all brief paths | Non-blocking on brief paths (exit 0 unless /throughline flag armed) | settings.json:171 |
| guard_ledger_discipline.sh (PreToolUse Write\|Edit) | Fires on every Write\|Edit; guards only `state/debt-ledger.md`; exits 0 on any non-ledger path including all brief paths | Non-blocking on brief paths (exit 0 on non-ledger targets) | settings.json:166 |
| guard_organism_map.sh (PreToolUse Write only) | Fires on Write tool calls only; guards `system/organism/manual.md` and `map-format-specs.md`; passes through on all brief paths | Non-blocking on brief paths (exit 0 on non-map targets) | settings.json:102 |

---

### INTENT / CURRENT-VS-TARGET

**Intent:** give every multi-session project a single, continuously-maintained source of truth that
any future session can rehydrate cold — with the persistence machinery ensuring orientation never
fades in long threads and the compaction machinery ensuring the scratchpad is archived losslessly
before any clear.

**Current:** the mechanical layer (pm_persist orientation re-injection, flag TTL + per-turn refresh,
pad_archive.py fail-closed readback-verify, scratch_capture_gate Stop-block) is sound and live. The
permissions allowlist for pad_archive.py is explicit. ~~The two TTLs (36h in pm_flag.sh vs 12h in
pm_persist.sh) create a minor operational inconsistency on crashed/orphaned sessions (see GAPS).~~
**CORRECTED 2026-08-27** (L.B2 audit): this discrepancy is resolved in code — pm_flag.sh is now the
single source of the 36h TTL and pm_persist.sh reads it via a `ttl` verb (see GAPS).

The hard safety invariant (RECEIPT-GATE, STORY LOG append-only, FRAME read-only, journal-first,
Frame intake HITL gate, Orientation Handshake, scratchpad self-heal) is **PROCEDURAL ONLY** — no
hook blocks a brief write that would overwrite the FRAME, drop a STORY LOG entry, or clear the
scratchpad without archiving. This is the element's structural weakness. The primary behavioral
contract is honor-system on all these paths; only the Stop-capture gate (`scratch_capture_gate.sh`)
is a real blocker.

**Target:** the structural gaps are known and accepted for now. Priority improvements would be:
(1) unify TTL values, (2) hook-enforce the RECEIPT-GATE (e.g., a PreToolUse Write guard that checks
for a pad-archive receipt before allowing a Write to `## SCRATCHPAD` that reduces its size), (3)
hook-enforce FRAME immutability (block any Write to a brief that changes `## 1. FRAME` without an
explicit user-instruction marker).

---

### INTEROP SEAMS

```
SHARES    save              · /save runs the BRIEF COMPACTION (pad_archive.py → pad-archive → CLEAR) — the sole authorized compactor at session-close; the skill also writes the brief's STORY LOG / DECISION BOARD during compaction [honor for ordering; pad_archive.py call is skill-mandated]

SHARES    checkin           · /checkin harvests notes into the same ## SCRATCHPAD and appends confirmed decisions to the Story Log, but never fires the compaction engine; only /save invokes pad_archive.py, at session-close [honor; Bash allowed]

WRITES->  journal           · project-manager writes system/journal.md JOURNAL-FIRST (session context or ledger row) before overwriting the brief on any direct update — journal is the only append-only backstop for brief content [honor — no hook enforces the ordering; guard_write_paths fires on both writes but not the sequence]

READS     pm-flag           · pm_persist.sh reads the armed doc_path from the flag to inject the Current-State excerpt into every turn [hook — pm_persist.sh UserPromptSubmit]

COMPLEMENTS announce_plan_write · announce_plan_write.sh (UserPromptSubmit) writes a plan pointer line INTO this element's owned ## SCRATCHPAD section when a NEW plan file appears in ~/.claude/plans/ and pm-flag is armed; falls back to plan-ledger.md when no brief is active — announce_plan_write writes to pm's store, not vice versa [hook — announce_plan_write.sh UserPromptSubmit; degrade-safe, exit 0 always]

FEEDS     read              · /read resolves the slug via project-registry.md, loads {path}/brief.md as the primary rehydration source, and re-arms pm-flag pointing at that brief — the brief is the memory chunk /read delivers [honor]

WRITES->  project-registry  · project-manager writes a new slug→path row into system/project-registry.md on first project creation; /save, /checkin, and /read all resolve the brief path from that registry row — one write, many readers [honor; no hook guards the registry write]

COMPLEMENTS scratch-capture-gate · scratch_capture_gate.sh reads the pm-flag-armed brief path as its fallback scratchpad target at Stop; the brief's ## SCRATCHPAD is what the gate inspects for uncaptured decisions — they share the same mutable section but write at different times (gate at Stop, skill at session-close compaction) [hook — Stop event]

FEEDS     archivist         · archivist-audit reads brief.md ## FRAME and ## STORY LOG (current schema; "## DESIRED OUTCOME" / "## DEAD ENDS" are legacy names no longer in use), and compares brief.md updated_at against the newest journal line for the slug (staleness signal) — the brief is the primary audit target [agent; read-only]

FEEDS     council-engine    · /advisory-council calls pm_flag.sh status to locate the active brief and builds the settled-ground card from its FRAME / desired-outcome + DECISION BOARD before convening advisors [honor]

FEEDS     build-plan-plane  · project-manager instructs the skill to record a Current plan pointer in ## SCRATCHPAD and link the plan path; build-plan-plane (autoplan/build) likely picks up the linked plan via pm_persist injection on its next turn — but this is an architectural inference, not confirmed by any live source [honor; second half INFERRED]

GUARDED-BY guard_write_paths · guard_write_paths.sh (PreToolUse Write|Edit) gates all Write/Edit to the brief path; allows Drive-root paths, ~~blocks everything else~~ **CORRECTED 2026-08-27: warn-only by default (`GUARD_WRITE_PATHS_MODE=warn`) — everything else is currently logged, not blocked** — but does NOT check section content or archive status [hook — WARN-ONLY BY DEFAULT on Write/Edit tool calls]
```

---

## GAPS

1. ~~**TTL discrepancy (12h vs 36h):** pm_flag.sh writes `TTL_HOURS` default 36h (line 17); pm_persist.sh defaults to 12h (line 16). On a crashed/orphaned session, the persist hook's 12h TTL expires the flag before the 36h pm_flag.sh limit.~~ **CORRECTED 2026-08-27** (L.B2 audit, source read + pm-flag.md's own resolution note): RESOLVED IN CODE. `pm_flag.sh` now owns `TTL_HOURS` as the single definition (default 36, env-overridable, exposed via a read-only `ttl` verb); `pm_persist.sh` calls that verb instead of carrying its own literal, falling back to 36 (not 12) only if `pm_flag.sh` is unreachable. This element's own citation of an open "12h vs 36h" gap was itself the stale part — the discrepancy it warns about no longer exists in the live code.

2. **RECEIPT-GATE is PROCEDURAL only — no hook blocks an unchecked clear:** nothing in the harness prevents a model from clearing `## SCRATCHPAD` without calling pad_archive.py first. The fail-closed guarantee lives entirely in the model obeying skill text + schema. A confused or context-degraded model can clear the pad silently without archiving it.

3. **FRAME and STORY LOG immutability are PROCEDURAL only:** guard_write_paths.sh allows any Write to a Drive-root path without inspecting section content. A Write to `brief.md` that drops STORY LOG entries, rewrites FRAME content, or condenses settled decisions passes the guard entirely.

4. **Journal-first ordering is PROCEDURAL only:** no hook enforces that a precious item hits `system/journal.md` before the brief is overwritten. If the model skips journal-first, no gate catches the miss — the item may exist only in the mutable brief.

5. **Step 6g independent sonnet audit is best-effort:** spawned by model decision inside the skill; no harness-level guarantee it runs on every compaction. The main session can substitute its own audit pass as a fallback but this is not mechanically enforced.

6. **Bash-write bypass (accepted, documented):** any Bash heredoc/tee/cp write to a brief path bypasses guard_write_paths.sh entirely. Accepted and noted in guard_write_paths.sh line 16 (2026-07-14). NOTE: This is a system-class gap shared by all Drive-path writes — not derived `·gap` per §8.4b SYSTEM-CLASS GAP EXCLUSION, as blast-radius does not materially exceed baseline.

7. **slug=folder-leaf (F0.4) not enforced at write time:** SKILL.md makes this a HARD rule (folder leaf must equal slug), but `check_slug_folder.py` is only an audit tool — no PreToolUse hook blocks a Write that violates this constraint.

8. **scratch_capture_gate fires only on Stop, not on /save's early exit:** if a session ends via process kill or crash before the Stop event fires (or if the session exits mid-/save before triggering Stop), the capture gate never runs for that session. The pad-archive from a prior /save compaction remains the last confirmed backstop.

9. **Frame intake and orientation handshake are PROCEDURAL only:** no hook forces the Frame intake 7-step process to run before doc is treated as authoritative on CREATE, and no hook enforces the build-conductor Orientation Handshake as the first reply. Both are honor-system behavioral contracts.

10. **Scratchpad self-heal (2a) is PROCEDURAL only:** no hook verifies `## SCRATCHPAD` exists before a Write to the brief. A session that touches a brief missing its scratchpad section without running the self-heal misses the mandate silently.

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)
- **maturity_label:** PARTIAL (honor)
- **check_detail:** "pending label_checker.py"
