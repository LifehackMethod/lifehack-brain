---
element: statusline-hud
title: "statusline-hud — element detail (ground/base altitude)"
subsystem: session-context
altitude: base
record_type: organism-element
maturity_label: LIVE·gap [provisional]
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — known-actionable — plan_flag record resolves by newest-mtime, so a parallel window can crosswire the plan HUD"
generated_from:
  - system/statusline.sh (120 lines — verified 2026-07-24)
  - system/hooks/guard_statusline_lock.sh (50 lines — verified 2026-07-24)
  - system/hooks/pm_flag.sh (verified 2026-07-24)
  - system/hooks/plan_flag.sh (verified 2026-07-24)
  - system/hooks/scratch_flag.sh (verified 2026-07-24)
  - system/tools/skill_hud.sh (verified 2026-07-24)
  - system/tools/statusline-truth-test.sh (verified 2026-07-24)
  - system/reference/settings.json (statusLine + guard_statusline hook — verified 2026-07-24)
  - state/debt-ledger.md (lines 72, 73, 81, 84, 86, 418, 424 — verified 2026-07-24)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# statusline-hud — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. The marker records what
> happened to the named file AT THIS DESTINATION; it does not change the description.
>
> ⛔ `system/reference/settings.json` did not come across. It was the donor's read-only reference copy of the
> harness config; this repo's hook registry is `.claude/settings.json`, independently authored and smaller —
> an equivalent, never a copy. Check any registration claim below against that file.

> **LADDER: ELEMENT (full mechanics). up → manual#statusline-hud ; ground truth → system/statusline.sh**
>
> **One-line:** always-on terminal status bar that renders model, context usage, session cost, active desk, armed project, active plan, and scratch state on every Claude Code turn — so the user can orient and steer across many parallel windows without asking.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires, registered in `settings.json`) · `[skill]` (skill logic, no hook enforcement) · `[honor]` (prose instruction only) · `[human]` (deliberate HITL pause)

---

## AUTHORED (human-only)

### OVERVIEW

The statusline-HUD is a two-layer rendered bar that the Claude Code harness redraws on every turn by calling `system/statusline.sh` as a bare command. It has no agent-side trigger — the HARNESS drives it unconditionally.

Two output layers, top to bottom:

1. **HUD line (optional, top):** zero or more context lines printed ABOVE the bottom bar. Two sub-layers:
   - **Skill HUD** (ephemeral, above everything): a custom line a running skill draws via `system/tools/skill_hud.sh set`; rendered in cyan; dropped automatically after 6 hours of staleness so a crashed skill cannot leave phantom state.
   - **Context HUD** (always-on when data exists): a freshness-colored line showing `proj: <slug>`, `plan: <filename>`, and `scratch: on` — each independently colored green (<24 h) → yellow (<7 d) → red (older), drawn only when at least one field has data.

2. **Bottom bar (always present):**
   `[<model-short>]  ctx <bar> <pct>%  $<cost>  desk: <where>`
   Color-coded by context use: green (<60 %), yellow (60–79 %), red (≥80 %).

The two layers together give the user: cost burn, context pressure, which model, which desk, what project is armed, what plan is active, and whether a scratchpad is live — without the model having to surface any of it in prose.

---

### RENDERING PIPELINE — step by step

**Input:** the harness passes a JSON blob on stdin. `statusline.sh` reads it once via `INPUT=$(cat)` and extracts:

| Field | JSON path | statusline.sh line |
|---|---|---|
| Model display name | `.model.display_name` or `.model.name` | L13 |
| Context-window used % | `.context_window.used_percentage` | L14 |
| Session cost USD | `.cost.total_cost_usd` or `.session_cost_usd` | L15 |
| Project directory / cwd | `.workspace.project_dir` or `.cwd` | L16 |
| Session ID | `.session_id` | L49 |

All extractions use inline Python 3 (`python3 -c "import sys,json; …"`) for robustness against missing keys.

**Step 1 — Desk detection** (L19–22): `DESK` defaults to `"root"`; if `PROJECT_DIR` contains `/desks/`, the desk name is sliced out with `sed`. This is the cwd-based fallback; the PM flag's `desk=` field (Step 5) takes priority.

**Step 2 — Model short-name** (L25): strips `claude-` prefix and any `-20YY*` date suffix for terminal compactness (e.g. `claude-sonnet-4-6` → `sonnet-4-6`).

**Step 3 — Context bar** (L28–33): renders a 10-character bar of `█` (filled) / `░` (empty) proportional to `CTX_PCT`. Example at 42 %: `████░░░░░░`.

**Step 4 — Color gate** (L36–43): selects an ANSI color applied to the bottom bar: green = `\033[32m` (< 60 %), yellow = `\033[33m` (60–79 %), red = `\033[31m` (≥ 80 %).

**Step 5 — Flag file resolution** (L59–69): flag paths are keyed by session. With a session ID: `~/.claude/run/{pm,plan,scratch}/pm-sess-$SID.flag` etc. Without one (edge/test): keyed by a 12-char SHA of `$PWD`. This pattern is shared by `pm_flag.sh`, `plan_flag.sh`, and `scratch_flag.sh` — each writes its flag independently; `statusline.sh` reads all three.

**Step 6 — Skill HUD** (L49–53): reads `~/.claude/hud/$SID.txt`; prints it in cyan if the file exists AND was modified within the last 360 minutes (6 h freshness guard). Rendered ABOVE everything else.

**Step 7 — Context HUD fields** (L91–98):
- `H_PROJ` = `slug=` from pm flag, up to a 14-day (20,160 min) freshness window. Capped at 24 characters.
- `H_PLAN` = `basename` of `plan_file=` from plan flag (filename only, `.md` stripped), same 14-day window. Capped at 24 characters. Shows the plan FILE NAME, not the plan title — a stable, searchable handle.
- `SCRATCH_ON` = non-empty if scratch flag exists AND is < 30 minutes old.

Each field is colored by its flag's `armed_at` epoch via `age_color()` (L77–85): green if the flag was armed < 24 h ago, yellow < 7 d, red older. The color signals freshness — red does not mean error, it means "check whether this is still current."

**Step 8 — Context HUD assembly** (L101–107): the three fields are concatenated with ` · ` separators; only non-empty fields appear. Printed via `printf '%b\n'` to expand ANSI escapes.

**Step 9 — Desk field (TRUTH CONTRACT)** (L117–119): the bottom bar's `desk:` field is `${FLAG_DESK:-$DESK}` — the `desk=` field from the pm flag if present, otherwise the cwd-based `$DESK`. This field MUST equal the REAL desk (planning, root, emily, etc.); the project slug MUST NEVER appear here. The truth contract exists because the user steers across many windows by this field. A 2026-07-13 regression (commit `d54133c`) set it to `${SLUG:-$DESK}`, which caused project-slug bleed; fixed in the same session. Regression-guarded by `system/tools/statusline-truth-test.sh`, wired into `system/tools/verify-hooks.sh`.

**Step 10 — Bottom bar print** (L119–120): `printf "${COLOR}[%s]  ctx %s %d%%  \$%s  desk: %s${RESET}"`.

---

### FLAG PRODUCERS — the three upstream writers

`statusline.sh` reads; the flag scripts write. Each is a tiny independent state-writer (no blocking, always exit 0).

#### pm_flag.sh — project tracking flag
`system/hooks/pm_flag.sh` · `~/.claude/run/pm/pm-{sess|cwd}-<key>.flag`

Flag schema (one `key=value` per line):
```
doc_path=<absolute brief path>
slug=<project slug>
desk=<desk name>
armed_at=<unix epoch>
cwd=<working dir at arm time>
session=<CLAUDE_CODE_SESSION_ID>
```

Operations: `arm <doc_path> <slug> <desk>` (writes the flag + appends to `arm-events.log`), `clear` (deletes flag + appends a `clear` row), `status` (prints `doc_path` or `"none"`, self-expires after 36 h TTL). The durable logbook `~/.claude/run/pm/arm-events.log` (TSV: `ts⇥arm|clear⇥doc⇥slug⇥desk⇥session`) survives TTL expiry and backs the `/save` PM-flag drop recovery (`pm_flag_recover.py`).

**Who calls `arm`:** `/project-manager` on launch; `/read` and `/checkin` on rehydrate. **Who reads `slug` and `desk`:** `statusline.sh` for the HUD. **Who reads `doc_path`:** `/save` Step 0, `/save` Step 7d.

#### plan_flag.sh — session plan identity flag
`system/hooks/plan_flag.sh` · `~/.claude/run/plan/plan-{sess|cwd}-<key>.flag`

Flag schema:
```
name=<plan title or filename>
plan_file=<absolute plan file path>
armed_at=<unix epoch>
session=<CLAUDE_CODE_SESSION_ID>
```

Operations:
- `record` (PreToolUse ExitPlanMode hook — reads plan name from the JSON stdin; extracts H1 from the in-flight plan content; FALLS BACK to newest `~/.claude/plans/*.md` by mtime when H1 unavailable — **this mtime fallback is the CROSSWIRE gap; see GAPS below**).
- `set <path>` (RESUME arm — explicit path, never mtime; called by `/checkin` and `/read` to restore plan context in a resumed window without re-entering plan mode).
- `status` (name or `"none"`; 36 h TTL).
- `path` (absolute file path; consumed by `/advisory-council` to load the live plan as advisory context).
- `clear`.

`pm_persist.sh` (a `project-manager` hook) refreshes the plan flag's TTL every turn by calling `_refresh_armed_at`, an inline function that rewrites the `armed_at=` epoch directly in the flag file on every turn — preventing TTL expiry without the delete-on-expire side-effect that `status` would trigger.

#### scratch_flag.sh — active scratchpad flag
`system/hooks/scratch_flag.sh` · `~/.claude/run/scratch/scratch-{sess|cwd}-<key>.flag`

Flag schema:
```
scratch_path=<path to scratchpad file>
skill=<skill name that armed it>
armed_at=<unix epoch>
session=<CLAUDE_CODE_SESSION_ID>
```

Operations: `arm <path> <skill>`, `clear`, `status` (30-minute TTL — ephemeral by design). Producers: `planning-weekly`, `planning-daily`, `clair-ingest`, or the agent when the user says "start a scratchpad."

`statusline.sh` reads only the PRESENCE of this flag (on/off); the `scratch_path` and `skill` fields are not rendered.

---

### THE EXECUTE-BIT INVARIANT — the HARD single-file rule

`statusline.sh` is registered in `settings.json` as a **bare command** (`$HOME/.claude/statusline.sh`, a symlink → `system/statusline.sh`). The harness exec-calls it directly — not via `bash system/statusline.sh`. This means the file MUST carry its executable bit (`chmod 755` / `+x`). Without it, the harness gets `permission denied` and the bar renders BLANK on every session — silently, with no error surface.

**The critical rule:** edit `system/statusline.sh` via the **Edit tool ONLY, never via Bash writes** (`echo >`, `cat <<EOF >`, `tee`, `sed -i`, `cp`). The Edit tool preserves the file's existing mode bits; Bash redirects and overwrites do not — they write a new inode with default `0644`, which strips `+x`.

This was a REAL INCIDENT on 2026-07-14 (documented in the `statusline.sh` file header, L5–9). The rule is codified in `system/sops/build-sop.md` (currently a bullet under `## General` — the `§4c` titled section referenced by `[INGEST-SKILL-SOP-4C]` in the debt-ledger was never written; treat as a forward-reference until that section is drafted) and enforced by `guard_statusline_lock.sh`.

**Symlink note:** `~/.claude/statusline.sh` → `system/statusline.sh` (the clone). The symlink was placed at `git` clone / machine-setup time. The `settings.json` pointer targets the symlink path (`$HOME/.claude/statusline.sh`); the canonical editable file is `system/statusline.sh` in the git clone.

---

### IMMUTABILITY GUARD — guard_statusline_lock.sh

`system/hooks/guard_statusline_lock.sh` · **Registration:** `settings.json` → `PreToolUse`, matcher `Bash`

The guard fires on every Bash tool call. It blocks three attack vectors:

**(a) Repointing the `settings.json` statusLine pointer** (L42–45): blocks any Bash command that contains `statusLine` AND either (`sed -i` + `settings.json`) OR a shell redirect / `tee` targeting `settings.json`. The old form (`sed -i[^|;&]*settings\.json`) had a bypass: a `sed` command using `|` as the delimiter (e.g. `sed -i 's|statusLine.*|foo|' settings.json`) was not caught. Hardened 2026-07-23 into two separate `grep -qE` calls (one for `\bsed\b.*-i` AND `settings\.json`, one for the redirect/tee form) — the conformance lab found the original bypass.

**(b) Destroying or overwriting statusline.sh** (L47): blocks `>`, `>>`, `tee`, `rm`, `mv`, `truncate`, or `ln -s` targeting a path ending in `statusline.sh` (with a trailing character class to exclude `.bak` renames, which are benign).

**(c) Invoking the built-in statusline-setup agent** (L49): blocks any command containing `statusline-setup`.

**Fail posture:** degrade-safe (exit 0 on parse error, per L30). The guard's header explains: a blanket deny-all-Bash on a transient glitch is worse than the narrow, low-harm risk it guards — `guard_write_paths.sh` backs this up at the Write/Edit layer.

**What the guard does NOT block:** reading `statusline.sh` (cat, grep), editing its CONTENT via the Edit tool, referencing it in a commit message, or any mention of the tokens that does not constitute a real write-to-target.

**REDIRECT (per deny message):** edit `system/statusline.sh` via the Edit tool; change the `settings.json` pointer in `system/reference/settings.json` with user sign-off.

---

### INTEROP SEAMS

```
READS       pm_flag.sh flag store        · slug= and desk= fields → proj: HUD + desk: bar
READS       plan_flag.sh flag store      · plan_file= basename → plan: HUD
READS       scratch_flag.sh flag store   · armed/not (30-min TTL) → scratch: on
READS       skill_hud.sh hud store       · ~/.claude/hud/$SID.txt (6-h freshness) → top skill line
KEYS-OFF    CLAUDE_CODE_SESSION_ID       · session key for all flag lookups; SHA(PWD) fallback
FEEDS       user terminal display        · rendered two-layer bar, every turn
GUARDED-BY  guard_statusline_lock.sh     · [hook] PreToolUse Bash — blocks repoint/replace
GUARDED-BY  statusline-truth-test.sh     · regression test for desk: truth contract; wired into verify-hooks.sh
SYNCS       plan_flag.sh                 · pm_persist.sh refreshes plan TTL every turn (project-manager concern)
COMPLEMENTS project-manager              · project-manager WRITES the pm_flag; this element READS it
COMPLEMENTS plan-integrity-cluster       · plan-integrity-cluster writes plan_flag via plan_flag.sh; this reads it
COMPLEMENTS save                         · /save reads pm_flag.sh status for project routing (Step 0); statusline reads for display only
```

---

### GAPS

**CROSSWIRE [STATUSLINE-PLAN-CROSSWIRE]** — `plan_flag.sh record` (the ExitPlanMode hook path) resolves the plan name using newest-mtime of `~/.claude/plans/*.md` when the H1 cannot be extracted from the in-flight plan JSON. In a session with multiple parallel plan-mode windows open, "newest mtime" is whichever window saved last — so the `plan:` HUD field can show the WRONG plan (the plan from the other window). `plan_flag.sh set <path>` (the RESUME path) is reliable because it takes an explicit path. Fix requires keying `record` off a session-specific signal or the plan's own content rather than mtime. Status: `actionable` (debt-ledger.md line 84, 2026-07-13). **Blast radius:** misleading `plan:` field in a multi-window session; no data loss.

**INTERP-GAP [STATUSLINE-GUARD-INTERP-GAP]** — `guard_statusline_lock.sh` operates on the COMMAND TEXT of the Bash tool input. It cannot distinguish between "a script that writes TO `statusline.sh`" and "a script that merely mentions `statusline.sh` as a reference." A broad pattern that tried to catch all writes false-positived on legitimate hook-writes and was reverted. Real protection for the execute-bit invariant is therefore procedural (Edit tool only, ⚠ header comment in the file itself) rather than mechanical for this bypass class. Status: `accepted-known-gap` (debt-ledger.md line 418). **Blast radius:** an adversarial or mistaken Bash write to `statusline.sh` would strip `+x` and blank the bar; caught on the next session; no data loss, recoverable with `chmod +x system/statusline.sh`.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** give the user a permanent, always-rendered orientation bar — model, context pressure,
cost, desk, armed project, active plan, live scratchpad — so that across many parallel windows he can
steer by a glance at the bottom of the terminal instead of asking the model "wait, which session is
this?" The bar must never lie: the `desk:` field's truth contract (real desk, never the project slug)
is the one invariant a regression test exists specifically to guard.

**Current (LIVE):**
- Bottom bar renders on every session with model, context, cost, desk. ✅
- HUD line shows proj/plan/scratch with freshness coloring. ✅
- Skill HUD with session isolation and 6-h staleness guard. ✅
- Execute-bit invariant documented + Edit-tool rule encoded in file header. ✅
- `guard_statusline_lock.sh` blocks the three main attack vectors. ✅
- CROSSWIRE (`record` mtime fallback): known gap, unresolved. ⚠
- INTERP-GAP (command-text guard can't catch all interpreter writes): accepted known gap. ⚠
- `statusline-truth-test.sh` wired into `verify-hooks.sh`. ✅

**Target:**
- `plan_flag.sh record` keyed off a session-specific signal (not mtime) so CROSSWIRE is eliminated in multi-window sessions. See debt-ledger `[STATUSLINE-PLAN-CROSSWIRE]`.
- The execute-bit / Edit-tool doctrine (currently a `## General` bullet in `build-sop.md`; forward-referenced as `§4c` in `[INGEST-SKILL-SOP-4C]`) written as a proper titled section and mirrored into `skill-building-playbook.md`. See debt-ledger `[INGEST-SKILL-SOP-4C]`.

---

## AUTO-COMPUTED (machine-only — written by Feature 1.5 checker; do not hand-edit)

```yaml
maturity_label: LIVE·gap [provisional]
check_detail: UNVERIFIED
```
