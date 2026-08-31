---
element: claude-md-pyramid
title: "claude-md-pyramid — element detail (ground/base altitude)"
subsystem: context
altitude: base
record_type: organism-element
maturity_label: PARTIAL·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C3 carve-out — session_context_loader.sh exits 0 on failure, so a session silently starts with no canon/TELOS/pulse-brief and no signal — ⚠ CORRECTED 2026-08-27 (L.B2 audit): the 'silently'/'no signal' half is false. The script deliberately prints a loud stdout failure message on the Drive-unmounted path and exits 0 precisely so that message reaches the model (a non-zero exit would suppress it instead). See the INTENT/CURRENT-VS-TARGET section below for the full correction."
topic: [system-architecture]
generated_from:
  - system/reference/global-CLAUDE.md
  - lifehack-brain/CLAUDE.md
  - desks/cal/CLAUDE.md
  - desks/clair/CLAUDE.md
  - desks/deryl/CLAUDE.md
  - desks/dobby/CLAUDE.md
  - desks/emily/CLAUDE.md
  - desks/marc/CLAUDE.md
  - desks/sentinel/CLAUDE.md
  - system/hooks/session_context_loader.sh
  - system/reference/settings.json
  - system/hooks/guard_write_paths.sh
  - system/hooks/guard_canon_write.sh
  - system/hooks/validate_on_write.sh
  - system/hooks/nudge_flow_drift.sh
  - system/hooks/guard_organism_map.sh
  - system/tools/parity-check.sh
created_at: 2026-07-23
updated_at: 2026-07-23
status: draft
authority: user
---

# claude-md-pyramid — element detail

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the always-loaded CLAUDE.md
> context stack — every trigger, every layer, every file, every gate and its honest enforcement, and
> its connection to the rest of the system. The MIDDLE manual (`system/organism/manual.md`) carries only
> a one-line + pointer to here; the TIP (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **LADDER: ELEMENT (full mechanics). up → manual#claude-md-pyramid ; ground truth → the live artifact (generated_from)**
>
> **One-line:** the always-loaded system-prompt stack (global machine cap + root doctrine + per-desk
> doctrine) plus the SessionStart hook that injects Drive-side canon, TELOS, and the pulse brief to
> complete what the harness cannot natively load.
>
> **Step grammar:** `actor → port/tool → store/file → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).
>
> **CITATION NOTES — what happened, at THIS repository, to the paths this element names.** The
> description above and below is a faithful account of the donor system and is unchanged; these lines
> record only the destination's answer, so a reader hunting for a named file knows what they will find.
>
> ⏳ `system/reference/settings.json` — **unruled.** The donor
> keeps a clone-side reference copy of the harness settings; this
> repository has no `system/reference/` directory at all. The registrations that actually fire here
> live in `.claude/settings.json`. Whether a mirror ever ships here
> is on no ship list and nobody has decided it — a DEBT, not a pass.
>
> ⏳ `system/reference/global-CLAUDE.md` — **unruled**, same reason: the donor's clone-side reference
> copy of the machine-global cap. This repository has no `system/reference/` directory; the global
> cap is the reader's own machine-local `~/.claude/CLAUDE.md`, which is never committed to any repository.
> Whether a mirror ever ships here is on no ship list and nobody has decided it — a DEBT, not a pass.
>
> ✅ `system/organism/map-format-specs.md` — **it is here** *(was `⏳ unruled` earlier on 2026-08-15; `T9.4c` landed it the same day, 579 lines)*. The map's format contract is cited by
> several shipped files here and has not been written at this destination yet. No open landing names
> it, so it stands as a debt until it lands.
>
> ⛔ `state/telos.md` — runtime-generated, created on first run, never committed. It is the reader's
> OWN year-long brief and lives in their notes folder — `.claude/skills/telos/SKILL.md` says
> *"inside your own notes folder — never in this repo"* — and `system/templates/telos-starter.md` is
> the shipped seed the skill writes it from. Absent from a fresh checkout is CORRECT, not missing.
>
> ⛔ `state/pulse-brief.md` — runtime-generated, never committed, and nothing in this repository
> writes or reads it. The destination's `system/hooks/session_context_loader.sh` injects the canon
> floor and TELOS only; its own header states that *"nothing here writes an overnight-jobs brief or a
> Pulse tile."* The step-8 conditional emit described below is donor behaviour.
>
> ⛔ `/distill` — no such skill exists here, and none exists in the donor either. This element names
> it as a NEW CANDIDATE, not as a shipped part (see its own note in the interop seams below).
>
> ⚠ **CORRECTED 2026-08-27** (L.B2 audit, live `ls -la ~/.claude/CLAUDE.md` + `find`): the
> "`~/.claude/CLAUDE.md` is a symlink → `~/lifehack-brain/system/reference/global-CLAUDE.md`"
> premise used throughout this element is false on BOTH halves. `ls -la` shows a **regular file**
> (`-rw-r--r--`, 14,294 bytes), not a symlink; and `find ~/lifehack-brain -iname
> "global-CLAUDE.md"` returns nothing at all — the claimed symlink target does not exist anywhere
> live (only old deferred/backup snapshots carry a file by that name). Every mention of the
> symlink relationship below is the donor's description, kept as written; this note is the single
> place to check for the corrected, current fact.

---

## AUTHORED   (human-only)

### WHAT THIS ELEMENT IS

The "claude-md-pyramid" is two distinct but inseparable mechanisms operating together to form the
session context floor:

**Layer 1 — Harness-native CLAUDE.md stack (no hook, always fires):**
Claude Code reads three CLAUDE.md files at session initialization before the first user turn:
1. `~/.claude/CLAUDE.md` — the global machine cap. In practice a **symlink** at
   `~/.claude/CLAUDE.md → ~/lifehack-brain/system/reference/global-CLAUDE.md`. This file is the
   thin machine-wide behavioral cap: voice, core safety stubs, the code-vs-content residency rule.
   It loads regardless of cwd — every session on every desk, every root window.
2. `{cwd}/CLAUDE.md` — the project/root doctrine loaded from the launch cwd. When launched from
   `~/lifehack-brain/`, this is `~/lifehack-brain/CLAUDE.md` — the full Lifehack operating
   doctrine (identity, tool plane, memory system, safety rails at full depth). When launched from a
   desk directory, the desk's `CLAUDE.md` loads instead (see Layer 1c below).
3. `desks/{desk}/CLAUDE.md` — per-desk doctrine. Loaded when the launch cwd is inside
   `~/lifehack-brain/desks/{desk}/`. Seven desks exist: cal, clair, deryl, dobby, emily, marc,
   sentinel. Each declares its own persona, tool access, role, and a read-order list
   pointing at additional canon files — that read-order is advisory prose, not a mechanical guarantee.

This is a **harness-native behavior**: Claude Code discovers and loads CLAUDE.md files by walking
the cwd and the global `~/.claude/` directory. There is no hook or script driving this — it cannot
fail unless the harness itself breaks. The CLAUDE.md files ride in the context window from session
start until context compaction clears them.

**Layer 2 — SessionStart hook injection (hook-enforced, complementary):**
The harness-native load covers only what is in the git clone. Drive-side content — desk canon,
root canon, TELOS, the pulse brief — must be injected separately. `session_context_loader.sh` is
a SessionStart hook registered in `settings.json` (matcher `""`, fires before the first user turn)
that reads the session's `cwd` field and emits Drive-side context to stdout, which the harness
injects into the session context alongside the CLAUDE.md stack.

The CLAUDE.md pyramid and session_context_loader.sh are not separate elements — they are the two
halves of a single mechanism. (NOTE: a prior draft version attributed a "session-context-loader →
fold into the CLAUDE.md-pyramid element" note to `system/organism/manual.md`; exhaustive grep of
manual.md confirms no such text exists there — the fold rationale is documented here, not in the
manual.)

---

### TRIGGERS / MODES

**Trigger 1 — Session initialization (harness-native, unconditional):**
Every Claude Code session start causes the harness to scan for and load CLAUDE.md files. This
fires before any hook, before any user turn, and before the SessionStart event
<!-- UNVERIFIABLE-BY-CODE · CORROBORATED (Claude Code docs: memory.md, context-window.md) for the general load-before-first-turn claim; the specific ordering of CLAUDE.md-load RELATIVE TO the SessionStart hook event is UNVERIFIABLE-BY-CODE · UNKNOWN (undocumented) — open loop OL-2 --> No configuration
controls it. It loads exactly what the filesystem has at that moment.

**Trigger 2 — SessionStart event → session_context_loader.sh (hook-enforced):**
When the harness fires the SessionStart event, it runs every hook registered under
`settings.json → hooks.SessionStart`. `session_context_loader.sh` is the sole entry (matcher
`""` = always-fires). The hook receives a JSON payload with the session `cwd` and emits the
Drive-side context to stdout.

**No per-turn re-injection:** There is NO UserPromptSubmit or PreToolUse hook that re-injects the
CLAUDE.md content per turn. The context floor is set once at session start and then lives in the
context window. After context compaction, the global `~/.claude/CLAUDE.md` and the project-root
`{cwd}/CLAUDE.md` ARE re-injected from disk by the harness (per Claude Code docs, context-window.md
"What survives compaction"). However, nested subdirectory CLAUDE.md files (e.g., a `desks/{desk}/CLAUDE.md`
loaded because a file within that subdirectory was read) are NOT re-injected after compaction — they
are lost until a file in that directory is read again. The maturity gap is therefore scoped to
nested subdirectory CLAUDE.md files, not the main pyramid layers.

---

### FULL HAND-OFF STEP CHAIN

**A. Harness-native pyramid load (no hook — pure harness behavior):**

1. `harness → filesystem read → ~/.claude/CLAUDE.md (symlink → system/reference/global-CLAUDE.md) → none [honor]`
   Always loads. <!-- UNVERIFIABLE-BY-CODE · CORROBORATED (Claude Code docs: memory.md, context-window.md) -->
   The symlink model means the actual code file is in the git clone at
   `~/lifehack-brain/system/reference/global-CLAUDE.md`; the symlink at `~/.claude/CLAUDE.md`
   is what the harness resolves. The parity-check tool tracks `~/.claude/CLAUDE.md` (by the
   symlink path) as a PARITY_FILE between the two machines.

2. `harness → filesystem read → {cwd}/CLAUDE.md (root doctrine when cwd = lifehack-brain) → none [honor]`
   Loads the root Lifehack operating doctrine when the session launches from the clone root.
   This is the full-depth doctrine: identity, safety rails, memory system, tool plane, hook
   creation rules, planning output format, etc. The global cap's safety stubs point down to
   this file for full prose.

3. `harness → filesystem read → desks/{desk}/CLAUDE.md (desk persona) → none [honor]`
   Loads only when cwd is inside `desks/{desk}/`. <!-- UNVERIFIABLE-BY-CODE · CORROBORATED (Claude Code docs: memory.md, context-window.md) -->
   Declares the desk's role, access model, persona,
   ingest model, output format, and advisory read-order (pointing at canon, briefs, TELOS —
   advisory prose only; the harness does NOT load the referenced files). Seven desk files live in
   `~/lifehack-brain/desks/*/CLAUDE.md`.

**B. SessionStart hook injection chain:**

4. `harness → SessionStart event → session_context_loader.sh → stdout injection [hook]`
   Registered in `system/reference/settings.json` under `hooks.SessionStart[0]`, matcher `""`,
   command: `bash "$HOME/lifehack-brain/system/hooks/session_context_loader.sh"`.
   The hook reads stdin (the SessionStart JSON payload) and extracts the `cwd` field via python3.
   Falls back to `$CLAUDE_PROJECT_DIR` or `$PWD` if the JSON parse fails.

5. `session_context_loader.sh → desk detection → case match on cwd pattern *"/desks/"* → DESK var [hook]`
   Parses the cwd for a `/desks/` segment to extract the desk slug. The case pattern is
   `*"/desks/"*)` (literal-string quoted); after the match, the desk slug is extracted via
   `rest="${CWD#*/desks/}"` and `DESK="${rest%%/*}"`. If found AND the Drive path
   `$DRIVE/desks/$DESK/canon/` exists, emits desk canon. Otherwise emits root canon.

6. `session_context_loader.sh → emit_dir → $DRIVE/desks/$DESK/canon/*.md OR $DRIVE/records/canon/*.md → stdout [hook]`
   `emit_dir()` iterates all `*.md` files in the target directory with `nullglob` (silently skips
   if zero files). Each file is emitted under a labeled header. This is the desk/root canon floor
   that `/read`'s Step 0.6 explicitly skips re-loading when launching into the same desk ("already
   loaded — SKIP it here; re-reading it just double-stuffs the window").

7. `session_context_loader.sh → cat → $DRIVE/state/telos.md → stdout [hook]`
   Always emitted if the file exists. TELOS is the year-long strategic brief (read-only for agents;
   only `/telos` skill updates it under explicit human approval).

8. `session_context_loader.sh → conditional emit → $DRIVE/state/pulse-brief.md → stdout (only if non-empty AND first-content-line ≠ NO_ACTION) [hook]`
   The pulse brief writer is currently UNKNOWN from live code — `archivist-autoplace` is RETIRED
   ("DO NOT REGISTER") and no live code has been identified as the current writer (open loop OL-4).
   Injected when it has real content (after stripping HTML comments and blank lines, the first
   non-empty line must not be `NO_ACTION`). Stays silent when there is nothing to report — the PAI
   isSentinel() pattern.

9. `session_context_loader.sh → exit 0 → always [hook]`
   Non-blocking by design. Nothing is denied if this hook fails, errors, or is absent. It is a
   context loader, not a guard. Classified as `[honor]` for the purpose of its contribution to
   behavioral compliance (the content it injects shapes behavior, but failure is silent).

---

### EVERY STORE / FILE READ OR WRITTEN (exact paths)

**READ (by harness-native load):**
- `~/.claude/CLAUDE.md` → resolves (symlink) to `~/lifehack-brain/system/reference/global-CLAUDE.md`
- `~/lifehack-brain/CLAUDE.md` — root doctrine (loaded when cwd = clone root)
- `~/lifehack-brain/desks/{desk}/CLAUDE.md` — 7 desk files

**READ (by session_context_loader.sh):**
- `$DRIVE/desks/{desk}/canon/*.md` — desk-specific canon files (injected in desk sessions)
- `$DRIVE/records/canon/*.md` — root-wide canon files (injected in non-desk/root sessions)
- `$DRIVE/state/telos.md` — TELOS strategic brief (always injected)
- `$DRIVE/state/pulse-brief.md` — overnight pulse brief (injected conditionally)

**WRITTEN (the write-side of the pyramid — all guarded):**
- `~/.claude/CLAUDE.md` (= the symlink target `system/reference/global-CLAUDE.md`) — explicitly
  ALLOWED (exit 0) by `guard_write_paths.sh` line 90. Note: guard_write_paths.sh is a
  blocking-type hook for restricted paths, but its CLAUDE.md branch allows writes — it does
  NOT block CLAUDE.md. The symlink target in the clone (`system/reference/global-CLAUDE.md`)
  also passes the clone content-class check (not in the content blocklist → `exit 0`).
- `~/lifehack-brain/CLAUDE.md` — allowed by the clone's content-class check (not in blocklist).
- `~/lifehack-brain/desks/{desk}/CLAUDE.md` — same: clone code path, allowed.
- `/save` Step 6 (behavioral rule append) writes to these CLAUDE.md files via Edit.
- The Drive canon files (`desks/{desk}/canon/*.md`, `records/canon/*.md`) that the hook injects
  are written by `/save` Step 6b on human approval — guarded by `guard_canon_write.sh`. The
  Archivist proposes placements but is carved OUT of canon writes (cannot write
  `records/canon/*` or `desks/{desk}/canon/current.md` per agents/archivist.md); only `/save`
  Step 6b executes canon writes on approval.

---

### EVERY GATE + HONEST ENFORCEMENT MECHANISM

**Gate 1 — guard_write_paths.sh (blocking-type hook; ALLOWS CLAUDE.md writes) [hook · fire-testable]**
- Matcher: `Write|Edit` (PreToolUse), registered in `system/reference/settings.json` ~line 161
- File: `~/lifehack-brain/system/hooks/guard_write_paths.sh`
- `~/.claude/CLAUDE.md` path: explicit `exit 0` ALLOW at lines 89-91 (`$CLAUDE_DIR/CLAUDE.md`
  or `$HOME/.claude/CLAUDE.md`). This hook is a blocking-type hook (can exit 1/2 for restricted
  paths), but its CLAUDE.md branch explicitly allows — it does NOT block CLAUDE.md writes.
- Clone CLAUDE.md paths (`~/lifehack-brain/CLAUDE.md`, `desks/*/CLAUDE.md`,
  `system/reference/global-CLAUDE.md`): allowed via the clone content-class check — none of these
  paths match the content blocklist (`state/*`, `records/*`, `desks/*/canon/*`, etc.) → `exit 0`.
- **KNOWN GAP (documented in hook header, accepted 2026-07-14):** Bash file-writes (`echo >`,
  `tee`, `cp`, heredoc) BYPASS this hook entirely — it only matches `Write|Edit` tools. CLAUDE.md
  files can be overwritten via Bash without triggering the guard. Discipline + code review are the
  mitigations. This is the largest honest maturity gap for the pyramid.
- **Enforcement: [hook] blocking-type (exit 1/2 for restricted paths); CLAUDE.md paths exit 0
  (allowed). [honor] for Bash path (hook never fires for Bash writes).**
- **Fire-testable: YES** — git-tracked, registered PreToolUse `Write|Edit`.

**Gate 2 — permissions.deny on settings.json / hooks/** [harness-level · BLOCKING · no bypass]**
- ~~`Write(~/.claude/settings.json)`, `Edit(~/.claude/settings.json)`, `Write(~/.claude/hooks/**)`,
  `Edit(~/.claude/hooks/**)` are HARD-DENIED at the harness permission level in `settings.json`.~~
  **CORRECTED 2026-08-27** (L.B2 audit, live read of `.claude/settings.json`'s `permissions.deny`
  array): the four exact home-relative (`~/.claude/...`) entries above do not appear. What the
  deny list actually contains is **repo-relative** — `Edit(.claude/settings.json)` and
  `Edit(system/hooks/*)` — which protects this repo's own tracked settings/hooks, not the separate
  home-level `~/.claude/settings.json` / `~/.claude/hooks/` paths this claim names. The claim
  conflates the two.
- These are permission-plane denials (enforced by the harness before any hook script runs).
- CLAUDE.md itself is NOT in the deny list — writes to `~/.claude/CLAUDE.md` are not
  permission-denied; they pass to `guard_write_paths.sh` which explicitly allows them.
- **Enforcement: harness-level permission deny — BLOCKING, no bypass possible.** Not applicable
  to CLAUDE.md files directly, but prevents self-modification of the hook registration that causes
  the SessionStart hook to fire.

**Gate 3 — guard_canon_write.sh on canon files [hook · BLOCKING · fire-testable]**
- Matcher: `Write|Edit` (PreToolUse), registered `system/reference/settings.json` ~line 251
- File: `~/lifehack-brain/system/hooks/guard_canon_write.sh`
- Fires on any path containing `/canon/`. CLAUDE.md files do NOT contain `/canon/` in their path —
  this gate does NOT guard CLAUDE.md writes directly.
- Applies to the Drive-side canon files (`desks/{desk}/canon/*.md`, `records/canon/*.md`) that
  `session_context_loader.sh` injects as the session floor. Blocks ~~writes lacking `authority:user`
  or a fast-stale marker~~ **CORRECTED 2026-08-24: writes that are oversized (>3,200 chars) or carry
  a fast-stale marker.** The `authority:user` half of this claim is no longer true — that rail was
  DELIBERATELY DROPPED 2026-08-11 per the guard's own header (self-attestation a machine types as
  easily as a human; it broke `/save`'s own approved canon writes). Re-verified live this session: a
  synthetic Write to a canon path with no `authority` field → `permissionDecision:allow`, exit 0. The
  fast-stale-marker half of this claim is unchanged and still live. Together these still protect the
  canon store from oversized/stale writes, which would silently corrupt every future session's floor
  — but not from an unauthorized WRITER, which this guard no longer distinguishes.
- **Enforcement: [hook] BLOCKING (exit 2) — guards the stores the pyramid LOADS, not the
  pyramid files themselves.**

**Gate 4 — validate_on_write.sh on CLAUDE.md writes (PostToolUse) [honor · ADVISORY ONLY]**
- Matcher: `Write|Edit` (PostToolUse), registered `system/reference/settings.json` ~line 273
- File: `~/lifehack-brain/system/hooks/validate_on_write.sh`
- ADVISORY ONLY — always exits 0. Emits a frontmatter reminder to stderr if fields are missing.
- CLAUDE.md files have no YAML frontmatter → the validator fires but produces no actionable output
  on these files. Zero blocking force.
- **Enforcement: [honor] — advisory, never blocks.**

**Gate 5 — nudge_flow_drift.sh on CLAUDE.md edits (PostToolUse) [honor · ADVISORY ONLY]**
- Matcher: `Write|Edit` (PostToolUse), registered `system/reference/settings.json` ~line 263
- ADVISORY ONLY — exits 0. Checks if the edited file appears in any `system/organism/elements/*.md`
  `generated_from` list. If so, emits a staleness nudge to stderr.
- **FIRE-TESTED: nudge does NOT fire for this element.** Python3 simulation with `*.md` glob against
  `elements/` confirms the glob excludes `.draft` files — `claude-md-pyramid.md.draft` is not
  matched. The nudge fires for `save.md` and `security-ingest-gate.md` when CLAUDE.md is edited
  (both reference CLAUDE.md paths in their `generated_from`), but NOT for this element's draft.
- **Enforcement: [honor] — advisory, always exits 0; does not fire for this element's draft.**

**Gate 6 — session read-order advisory in desk CLAUDE.md files [honor · NO MECHANICAL ENFORCEMENT]**
- Each desk CLAUDE.md declares a read-order (e.g., `1. Lifehack/CLAUDE.md → 2. desks/{desk}/CLAUDE.md
  → 3. canon/*.md ...`). This prose instruction tells the model how to orient a session; it is
  NOT mechanically enforced by the harness.
- `session_context_loader.sh` partially mechanizes the canon-injection step of this read-order,
  but the harness does not verify that files were read in the stated order or that all named files
  were loaded.
- **LIVE CODE VS PROSE DISAGREEMENT (surfaced by source-audit):** The desk CLAUDE.md files declare
  a read-order as if mechanically enforced. LIVE CODE shows only two things are mechanically loaded:
  (a) the harness-native CLAUDE.md stack (not the additional referenced files), and (b)
  `session_context_loader.sh` which injects `$DRIVE/desks/$DESK/canon/*.md` (all .md files in
  that dir, not just the specific files named in the prose read-order). The prose read-order is
  advisory instruction to the model, not a mechanical guarantee. **LIVE CODE WINS.**
- **Enforcement: [honor] for the read-order as a whole; [hook] for the canon injection step only.**

**Gate 8 — guard_organism_map.sh on wholesale Write of the host map files [hook · BLOCKING · fire-testable]**
- Matcher: `Write` (PreToolUse), registered in `system/reference/settings.json` ~line 102
- File: `~/lifehack-brain/system/hooks/guard_organism_map.sh`
- Protects `system/organism/manual.md` and `system/organism/map-format-specs.md` — the two files
  that HOST this element's entry and define the format contract it is authored under. A wholesale
  overwrite of `manual.md` (e.g., from an injected instruction) would silently remove or corrupt
  this element's reference entry and replace the system's own attack-surface map in one shot.
  Similarly, a wholesale overwrite of `map-format-specs.md` would corrupt the format contract.
  NOTE: `label_checker.py` reads `system/tools/organism/label_manifest.yaml` as its operational
  ground truth (label_checker.py line 66: `DEFAULT_MANIFEST = REPO / 'system' / 'tools' / 'organism'
  / 'label_manifest.yaml'`) — it does NOT open `map-format-specs.md`. The guard's rationale here
  is protecting the authoring format contract, not the checker's runtime manifest.
- **Enforcement mechanism:** blocks only when `tool_name == "Write"` AND the `content` field is
  present (i.e., a full-content overwrite). Surgical `Edit` tool calls (old_string→new_string)
  are allowed (exit 0) — that is the normal authoring path. The deny message exits 2 and emits
  JSON on stderr; the redirect is to use `Edit` for surgical changes or shell + human OK for full
  regeneration.
- **Scope:** does NOT protect the element file itself (`elements/claude-md-pyramid.md.draft`) —
  only the two map files that reference it. The element file's content is protected by
  `guard_write_paths.sh` (clone content-class check) and the session's behavioral discipline.
- **Enforcement: [hook] BLOCKING (exit 2) for Write + content-present on the two protected paths;
  exit 0 for all other paths and for Edit tool calls.**
- **Fire-testable: YES** — git-tracked, registered PreToolUse `Write`.

**Gate 7 — parity-check.sh for ~/.claude/CLAUDE.md across two machines [skill · not automated]**
- `~/lifehack-brain/system/tools/parity-check.sh` tracks `$HOME/.claude/CLAUDE.md` in its
  PARITY_FILES array and can repair drifted/missing files across the primary machine and the second machine.
- This is a MANUAL tool (not a hook, not a cron) — it must be invoked explicitly. It is the
  multi-machine consistency gate for the global cap file.
- Since `~/.claude/CLAUDE.md` is a symlink to the git-tracked `system/reference/global-CLAUDE.md`,
  `git pull` on the other machine keeps the symlink target in sync; the parity check provides a
  second-layer verification that the symlink itself exists and points correctly.
- **Enforcement: [skill] — manually invoked; no hook forces it; no cron runs it.**

---

### PORTS TOUCHED

- **Harness filesystem reader** — reads `~/.claude/CLAUDE.md` and `{cwd}/CLAUDE.md` natively
- **SessionStart hook channel** — receives JSON payload; emits stdout context injection
- **Drive filesystem reader** — `session_context_loader.sh` reads canon, TELOS, pulse-brief via
  `cat` and glob expansion
- **`guard_write_paths.sh`** — PreToolUse Write|Edit: blocking-type hook that ALLOWS CLAUDE.md writes (exit 0); blocks restricted paths
- **`guard_canon_write.sh`** — PreToolUse Write|Edit: the gate on canon-file writes
- **`validate_on_write.sh`** — PostToolUse Write|Edit: advisory nudge
- **`nudge_flow_drift.sh`** — PostToolUse Write|Edit: staleness nudge
- **`parity-check.sh`** — manual multi-machine consistency tool
- **`guard_organism_map.sh`** — PreToolUse Write: blocks wholesale overwrites of `system/organism/manual.md` and `system/organism/map-format-specs.md` — the host files that carry this element's reference entry and format contract

---

### OUTCOME

A fresh session has, in its context window before the first user turn:
1. The global machine cap (voice, safety stubs, code-vs-content rule, subagent model guidance)
2. The root Lifehack operating doctrine OR the desk's persona — whichever the cwd selects
3. The desk canon (or root canon) from the Drive spine — the floor of the knowledge stack
4. TELOS — the year-long strategic brief
5. The overnight pulse brief — if anything ran

The session begins oriented: the system's behavioral rules are active, the permanent truths are
loaded, the strategic arc is visible. WITHOUT this stack, the session would have no behavioral
rail and no knowledge floor — it would be a blank model.

---

### EDGE CASES

1. **No desk detected (root session):** `session_context_loader.sh` emits root canon
   (`$DRIVE/records/canon/*.md`). If that directory has zero `.md` files, `emit_dir()` returns
   silently — no canon is injected, no error is emitted.

2. **Desk detected but no canon dir:** If `$DRIVE/desks/$DESK/canon/` does not exist, the hook
   falls through to the `else` branch and emits root canon instead. The hook does NOT emit the desk's
   CLAUDE.md file — that was already loaded by the harness natively.

3. **pulse-brief.md first line is NO_ACTION:** Hook stays silent. The PAI isSentinel() pattern
   prevents noise when the overnight Pulse had nothing to report.

4. **Context compaction after session start:** After compaction, the global `~/.claude/CLAUDE.md`
   and project-root `{cwd}/CLAUDE.md` ARE re-injected from disk by the harness. However, nested
   subdirectory CLAUDE.md files (those loaded because a file in a subdirectory was read, not the
   main pyramid layers) are NOT re-injected and are lost until a file in that directory is read
   again. The maturity gap is scoped to the nested-file case only — the main pyramid layers survive
   compaction.

5. **Desk CLAUDE.md read-order references a file that does not exist:** The harness ignores missing
   files in the read-order list silently. `session_context_loader.sh` does not read the CLAUDE.md's
   read-order list at all; it only reads from the `canon/` directory. Files named in the prose
   but not in `canon/` are simply never loaded.

6. **Multi-desk cwd (nested paths):** The `case "$CWD" in *"/desks/"*)` match uses the FIRST
   `/desks/` segment in the cwd. `rest="${CWD#*/desks/}"` strips the prefix up to the FIRST
   `/desks/`, then `DESK="${rest%%/*}"` takes the first path segment — resolving the desk
   immediately after the FIRST `/desks/` occurrence, not the innermost. In practice this is not a
   real ambiguity since desk directories don't nest.

7. **Session launched from outside the clone (e.g., `~/Desktop`):** The harness finds no
   project-level CLAUDE.md (no `CLAUDE.md` in `~/Desktop/`). Only the global cap loads natively.
   <!-- UNVERIFIABLE-BY-CODE · CORROBORATED (Claude Code docs: memory.md, context-window.md) -->
   `session_context_loader.sh` fires but detects no desk, so it emits root canon + TELOS +
   pulse-brief. The root doctrine DOES NOT load in this case.

8. **CLAUDE.md write via Bash bypasses guard_write_paths:** The guard fires only on Write/Edit
   tool calls. A `echo "..." >> ~/.claude/CLAUDE.md` Bash call passes through. This is the
   documented Bash-write gap (KNOWN-GAP, accepted 2026-07-14). CLAUDE.md is particularly sensitive
   because its content shapes every future session's behavior.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** establish a deterministic, always-on behavioral rail + knowledge floor for every session
before any user turn — so the model knows how to behave, what the safety rails are, and what the
permanent truths are, without the user having to reinstate them each time.

**Current state → PARTIAL, for precise reasons:**
- The harness-native CLAUDE.md load is fully LIVE: reliable, cannot be toggled off, git-tracked
  (via the symlink model), parity-checked across machines.
- The SessionStart hook injection is fire-testable and real: `session_context_loader.sh` is
  git-tracked, registered in `settings.json`, exits 0 (non-blocking; advisory classification).
- Guard coverage on CLAUDE.md writes is real for Write/Edit tool calls (guard fires, `exit 0` for
  allowed paths, `exit 1/2` for blocked ones). But Bash writes BYPASS the guard entirely
  (documented gap).
- What is HONOR-SYSTEM and thus PARTIAL:
  - **Desk read-order compliance** — the prose in desk CLAUDE.md files instructing which files
    to load first is advisory only; no hook verifies the order was followed.
  - **Post-compaction behavioral integrity (nested files only)** — the global cap and project-root
    doctrine ARE re-injected after compaction (harness behavior, per Claude Code docs). However,
    nested subdirectory CLAUDE.md files are not re-injected; if desk CLAUDE.md was loaded via a
    subdirectory read, it may be lost after compaction with no re-injection mechanism.
  - **Bash write bypass** — Bash can overwrite CLAUDE.md files without triggering `guard_write_paths.sh`.
  - **`session_context_loader.sh` non-blocking** — ~~if the hook fails, the canon floor, TELOS,
    and pulse-brief are silently absent from the session. No error surfaces.~~ **CORRECTED
    2026-08-27** (L.B2 audit, `grep -n "exit 0\|exit 1"` + source read of
    `session_context_loader.sh`): the exit-0-always half is TRUE — the script's own header says so
    on purpose ("EVERY EXIT PATH IN THIS FILE IS exit 0, ON PURPOSE, INCLUDING THE REAL
    FAILURES"). But "silently absent... no error surfaces" is the OPPOSITE of what the code does:
    for the Drive-unmounted case specifically, it prints a loud message to stdout — *"!! YOUR NOTES
    ARE NOT WHERE THIS SYSTEM REMEMBERS THEM: $REMEMBERED ... Nothing was loaded. This is NOT an
    empty system — it is a system that cannot see its own memory."* — and per the script's own
    comments, exit 0 is chosen DELIBERATELY so that message reaches the model: stdout on
    SessionStart is injected into context regardless of exit code, whereas a non-zero exit would
    instead SUPPRESS the message entirely. The design's whole point is the opposite of "no error
    surfaces" — exit 0 here means the failure IS surfaced, not hidden.
- Mixed (significant live infrastructure + meaningful honor-system gaps) → **PARTIAL**.

**TARGET:**
1. **Harden against compaction for nested CLAUDE.md files** — the global cap and project-root
   doctrine survive compaction (harness re-injects them). A mechanism to detect and re-inject
   nested subdirectory CLAUDE.md files (e.g., desk CLAUDE.md loaded via a subdirectory read)
   after compaction would close the remaining gap for those files.
2. **Block Bash writes to CLAUDE.md** — closing the Bash bypass gap would make the write-guard
   complete. Currently accepted as a known gap (chasing every Bash write breaks more than it protects).
3. ~~**session_context_loader.sh fail-alerting** — a non-zero exit or a stderr emission when canon
   injection fails would surface silent floor-absence to the user; currently silent.~~ **CORRECTED
   2026-08-27: this TARGET item describes a problem that doesn't exist — the script already
   surfaces the Drive-unmounted failure loudly via stdout at SessionStart, by design (see the
   corrected bullet above). No further action item is owed here.
4. **Desk read-order mechanization** — making the desk CLAUDE.md's declared read-order order
   actually load the referenced files (vs. just `canon/*.md` alphabetically) would close the
   prose-vs-code gap.

---

### GAPS

**Gap 1 — Bash writes to CLAUDE.md bypass guard_write_paths.sh [element-specific fail-open]**
`guard_write_paths.sh` is registered as `PreToolUse Write|Edit` only — and for CLAUDE.md paths
it explicitly ALLOWS (exit 0), so even for Write/Edit tool calls, CLAUDE.md writes are not blocked
by this hook. Any Bash file-write (`echo >`, `tee`, `cp`, heredoc) to `~/.claude/CLAUDE.md`,
`~/lifehack-brain/CLAUDE.md`, or any desk `CLAUDE.md` bypasses the hook entirely — the hook
never fires for Bash tool calls. CLAUDE.md is particularly sensitive because its content shapes
every future session's behavior; an unchecked Bash overwrite could silently corrupt the behavioral
rail system-wide. Accepted KNOWN-GAP (guard_write_paths.sh header, 2026-07-14). Mitigation:
discipline + code review only.
- **Blast radius:** silent corruption of the always-on behavioral rail on every future session.
- **Enforcement tag: [honor] for Bash path (hook never fires for Bash writes); CLAUDE.md paths are
  explicitly allowed (exit 0) even when the hook fires for Write/Edit tool calls.**

**Gap 2 — ~~session_context_loader.sh is non-blocking; failure silently drops the full Drive-side context floor~~ [element-specific fail-open, corrected]**

⚠ **CORRECTED 2026-08-27** (L.B2 audit, `grep -n "exit 0\|exit 1"` + source read of
`system/hooks/session_context_loader.sh`): this entire gap entry inverts what the code does. The
SessionStart hook always exits 0 regardless of success or error — that half is true, and is
confirmed by the script's own header ("EVERY EXIT PATH IN THIS FILE IS exit 0, ON PURPOSE,
INCLUDING THE REAL FAILURES"). But the rest of this entry — "silently absent... no error surfaces,
no user notification fires" — is FALSE. For the Drive-unmounted case specifically, the script
prints, to stdout: *"!! YOUR NOTES ARE NOT WHERE THIS SYSTEM REMEMBERS THEM: $REMEMBERED ...
Nothing was loaded. This is NOT an empty system — it is a system that cannot see its own memory."*
Per the script's own comments, exit 0 is chosen DELIBERATELY so this message reaches the model:
stdout on SessionStart is injected into context regardless of exit code, while a non-zero exit
would instead SUPPRESS the message. The design's entire point is the opposite of "no error
surfaces" — this hook uses exit 0 specifically so failure messages reach the model, not to hide
them. What remains true and un-corrected: the session does start with only the harness-native
CLAUDE.md stack and zero Drive-side knowledge floor when the Drive is unmounted — the loss itself
is real, only the "silent, no signal" framing was wrong.
- **Blast radius:** session starts with no canon floor, no TELOS — behavioral rules from the
  Drive-side memory system are absent for the full session, but a loud stdout message names this,
  it is not silent.
- **Enforcement tag: [honor] — context loader, never blocking; failure is loudly surfaced by design, not silent.**

---

### INTEROP SEAMS (shared-state edges to other elements — the organism view)

- `COMPLEMENTS` `read` · `/read`'s Step 0.6 (lazy-canon walk) EXPLICITLY skips loading the desk
  canon when `session_context_loader.sh` already injected it at SessionStart ("the SessionStart
  floor auto-injects the active desk's canon... already loaded — SKIP it here"). The pyramid injects
  the floor; `/read` builds the project branch on top without double-loading. These two are
  co-designed around each other.

- `GUARDED-BY` `guard-write-paths` · `guard_write_paths.sh` (PreToolUse Write|Edit) is a
  blocking-type hook that ALLOWS writes to `~/.claude/CLAUDE.md` and the clone CLAUDE.md paths
  (explicit exit 0) — it does not block CLAUDE.md writes. `session_context_loader.sh` lives at
  `~/lifehack-brain/system/hooks/` (git clone only — no Drive copy); its registration is in
  `settings.json` (line 315), not in a hook script. The loader's registration is separately
  shielded by the harness-level `Write(~/.claude/settings.json)` permission deny.

- `GUARDED-BY` `guard-canon-write` · `guard_canon_write.sh` (PreToolUse Write|Edit) protects the
  Drive-side canon stores (`desks/{desk}/canon/*.md`, `records/canon/*.md`) that
  `session_context_loader.sh` injects as the session floor. A poisoned canon write bypassed here
  would corrupt every future session's context floor silently.

- `GUARDED-BY` `guard-organism-map` · `guard_organism_map.sh` (PreToolUse Write) blocks wholesale
  Write overwrites of `system/organism/manual.md` and `system/organism/map-format-specs.md` — the
  host files that reference this element's entry and define its format contract. A poisoned overwrite
  of `manual.md` would silently corrupt the organism schematic that this element belongs to; a
  poisoned overwrite of `map-format-specs.md` would corrupt the format contract that governs
  authoring. (`label_checker.py` reads `label_manifest.yaml` as its runtime ground truth, not
  `map-format-specs.md` directly.) Surgical Edits (old_string→new_string) are allowed. This is a
  real seam with a real registered hook (settings.json ~line 102), not an advisory.

- `READS` `save` · `/save` Step 6 WRITES behavioral rules BACK into the CLAUDE.md files via Edit;
  the pyramid is the read-time surface for those rules. The pyramid is the always-on reader;
  `/save` is the authorized writer of behavioral rules into its files.

- `READS` `canon` · `session_context_loader.sh` reads `desks/{desk}/canon/*.md` and
  `records/canon/*.md` on every SessionStart. The pyramid is the intake point for the canon store
  into the session; the canon element is the store and its governance.

- `KEYS-OFF` `hook-plane` · The SessionStart hook registration in `system/reference/settings.json`
  is the hook-plane's record that makes `session_context_loader.sh` fire. If the hook-plane
  changes or corrupts that entry, the pyramid's Layer 2 is silently disabled. The pyramid depends
  on the hook-plane for its enforcement mechanism.

- `SYNCS` `two-machine-residency` · `~/.claude/CLAUDE.md` is tracked by `parity-check.sh` as a
  PARITY_FILE between the primary machine and the second machine. The symlink target (`system/reference/global-CLAUDE.md`)
  travels by `git pull` on the other machine. The settings.json that carries the SessionStart
  registration IS still parity-tracked — `$HOME/.claude/settings.json` is explicitly in the
  PARITY_FILES array (parity-check.sh lines 22-28). NOTE: the "NO LONGER parity-tracked" comment
  in parity-check.sh refers to HOOKS, not settings.json. The pyramid's files and its SessionStart
  registration must be parity-identical across both machines for consistent behavior.

- `READS` `telos` · `session_context_loader.sh` reads `state/telos.md` at every SessionStart;
  `/telos` is the sole documented writer of that file under human approval (exhaustive grep across
  planning-weekly files found zero telos write references — the planning-weekly council phase does NOT write
  to `state/telos.md`). The pyramid is the always-on injection path; `/telos` is the update path.
  They share the single file.

- `READS` `pulse-cron` · `session_context_loader.sh` reads `state/pulse-brief.md` on every
  SessionStart. The pyramid is the sole consumer. The writer of `state/pulse-brief.md` is
  currently UNKNOWN from live code — `archivist-autoplace` is RETIRED ("DO NOT REGISTER") and
  no live replacement writer has been identified (open loop OL-4).

- `READS` `archivist` · The Archivist proposes placement changes to `desks/{desk}/canon/*.md` and
  `records/canon/*.md` — the exact stores the pyramid loads as the session floor. However, the
  Archivist is carved OUT of canon writes (per agents/archivist.md); only `/save` Step 6b executes
  canon writes on human approval. Approved Archivist proposals (executed via `/save`) directly
  alter what the next session sees.

- `READS` `distill` · `/distill` is the machine-proposed canon promotion path: it reads and
  proposes writes to `desks/{desk}/canon/*.md`. Its approved outputs alter what the pyramid injects
  next session. (NOTE: `/distill` is not in the ranked-element-list ~28 — see NEW CANDIDATES below.)

- `KEYS-OFF` `session_context_loader.sh` desk-detection · The loader's `case "$CWD" in *"/desks/"*)`
  pattern uses the cwd to determine WHICH desk's canon to inject. The desk CLAUDE.md files declare
  this cwd implicitly by living in `desks/{desk}/`; the loader uses the same path structure as the
  routing signal. This means the desk CLAUDE.md's LOCATION is its routing identity for the loader.

---

### HARD PROHIBITIONS

What the pyramid must never allow under any circumstances:

- No write to the Drive copy of system/hooks/ or Lifehack/system/hooks/ — guards are
  enforcement-layer code; agent self-modification is blocked by `guard_write_paths.sh`.
- ~~No direct write to `desks/{desk}/canon/*.md` or `records/canon/*.md` without `authority:user`
  — `guard_canon_write.sh` enforces this; a silently-written canon would corrupt the floor.~~
  **CORRECTED 2026-08-24: this prohibition is no longer mechanically enforced.** The `authority:user`
  rail was DELIBERATELY DROPPED 2026-08-11 (guard's own header) — self-attestation a machine types as
  easily as a human, and it broke `/save`'s own approved canon writes. Re-verified live this session:
  a synthetic Write to a canon path with no `authority` field → `permissionDecision:allow`, exit 0.
  `guard_canon_write.sh` today enforces only size (>3,200 chars) and stale markers; a silently-written
  canon under that size with no stale marker passes. The prohibition on unauthorized canon writes now
  holds only as `[honor]` — agent discipline — not `[hook]`.
- No re-routing the SessionStart hook via settings.json edits — `Write(~/.claude/settings.json)`
  and `Edit(~/.claude/settings.json)` are harness-level permission-denied.
- No treating the desk CLAUDE.md's prose read-order list as a mechanical guarantee — it is
  advisory instruction only; the harness does not enforce it.

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)

- **maturity_label:** PARTIAL·gap
- **check_detail:** pending label_checker.py
