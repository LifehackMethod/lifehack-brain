---
element: pm-flag
title: "pm-flag — element detail (ground/base altitude)"
subsystem: project-state
altitude: base
record_type: organism-element
maturity_label: PARTIAL·gap
gap_disposition: by-design
gap_disposition_note: "ruled 2026-07-28 at class level — C2 honor-caller — nothing validates the doc_path passed to arm; the flag store is machine-local by design"
generated_from:
  - system/hooks/pm_flag.sh
  - system/hooks/pm_persist.sh
  - system/hooks/save_routing_hint.sh
  - system/hooks/scratch_capture_gate.sh
  - system/hooks/scratch_sweep_nudge.sh
  - system/hooks/announce_plan_write.sh
  - system/hooks/guard_statusline_lock.sh
  - system/tools/pm_flag_recover.py
  - system/reference/settings.json (lines 333-410 UserPromptSubmit; lines 444-452 Stop; lines 455-458 statusLine)
  - system/statusline.sh (via ~/.claude/statusline.sh symlink)
  - skills/save/SKILL.md (Step 0, Step 0.4)
  - skills/read/SKILL.md
  - skills/checkin/SKILL.md
  - skills/project-manager/SKILL.md
  - skills/advisory-council/SKILL.md
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# pm-flag — element detail

> **CITATION BANNER — what this page names that is not here** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. The marker records what
> happened AT THIS DESTINATION; it does not change the description.
>
> ⛔ `/huddle` and `/huddle-board` are not skills here, and there is nothing to bring: neither exists in the
> donor's skill set either — only a huddle.py tool and a tombstoned huddle-plane element draft. The caller list
> below records what called `pm_flag.sh status` at the time it was written; two of those callers never shipped.

> **LADDER: ELEMENT (full mechanics). up → manual#pm-flag ; ground truth → the live artifact (generated_from)**

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the armed-project state hub:
> `pm_flag.sh` (the on/off state writer) and `pm_persist.sh` (the per-turn UserPromptSubmit re-injector).
> The MIDDLE manual (`system/organism/manual.md`) carries only a one-line + pointer to here.
>
> **One-line:** the singleton on/off switch that tells the whole organism which project brief is currently
> active — armed by skills, re-injected every turn, read by every hook that routes saves, HUD tiles,
> plan announces, and session-close captures.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### COMPONENTS

pm-flag is two scripts operating as a single logical hub:

**`pm_flag.sh`** — the state writer/reader. A shared tool (not a hook itself) called by skills and
hooks as a Bash subprocess. Three modes:
- `arm <abs_doc_path> <slug> <desk>` — creates or overwrites the session flag file and appends a
  breadcrumb to the arm-events logbook.
- `status` — reads the flag, enforces TTL, silently deletes a stale flag, returns the `doc_path` or `none`.
- `clear` — removes this session's flag file(s) and appends a clear breadcrumb to the logbook.

**`pm_persist.sh`** — the per-turn injector. A UserPromptSubmit hook registered in `settings.json`
(line 337, matcher `""`) that fires on EVERY user prompt. It refreshes sibling flag TTLs, reads the
pm flag, and emits the `[project-manager ACTIVE]` context anchor to stdout. Non-blocking: always
exits 0 (degrade-safe). It also houses the huddle side-channel (see Step 2 below). (Brief-lifecycle
angle — how pm_persist keeps the project doc alive across turns — see `project-manager` element.)

**`pm_flag_recover.py`** — a recovery tool (not a hook). Called by `/save` Step 0.4 when `pm_flag.sh
status` returns `none`. Reads `arm-events.log` to find the last arm/clear for this session and outputs
`NONE` / `CLEAR` / `ARM<TAB>doc_path<TAB>slug<TAB>desk`.

---

### TRIGGERS

**pm_flag.sh arm** fires when:
1. `/project-manager` runs — the skill calls `pm_flag.sh arm` immediately after the intake/interview process identifies the doc path, slug, and desk (creating or continuing a doc); arm is NOT the first step — intake comes first.
2. `/checkin` runs — two paths: (a) front-door args provided → arm fires immediately; (b) no args → `pm_flag.sh status` runs first, THEN arm fires after resolution. Arm is not universally first for `/checkin`.
3. `/read` runs a rehydrate and a project was previously tracked — re-arms on rehydrate.
4. `/save` Step 0 recovers a dropped flag via Step 0.4 and the user confirms re-arm.
5. `/design-lifehack` discovery SOP references arming via `pm_flag.sh arm`.
6. `/save` Step 0 returns a live doc path (flag already armed) — after completing the save, the
   skill immediately calls `pm_flag.sh arm` again with the same path/slug/desk to refresh the
   `armed_at` TTL (skills/save/SKILL.md lines 95–98). This re-arm-on-success fires on every
   successful pm-routed save and is a regularly-exercised arm invocation.

**pm_flag.sh status** fires on every invocation of `announce_plan_write.sh` (unconditionally),
`scratch_capture_gate.sh` (as fallback when no scratch_flag), and any skill that needs to locate
the active brief (`/save` Step 0, `/huddle`, `/huddle-board`, `/advisory-council`).
`save_routing_hint.sh` calls `pm_flag.sh status` ONLY when the prompt matches a save-request phrase
(exits early at line 51 otherwise — NOT on every invocation).
`scratch_sweep_nudge.sh` calls `pm_flag.sh status` ONLY when `scratch_flag.sh status` returns
non-armed — when scratch is armed, pm_flag.sh status is never reached.

**pm_persist.sh** fires on every UserPromptSubmit event (matcher `""`) — unconditionally, every turn,
for the lifetime of the session.

---

### FULL HAND-OFF STEP CHAIN

---

#### Step 0 — ARM (skill-layer, fires once per project activation)

`/project-manager or /checkin or /read → Bash → pm_flag.sh arm <abs_doc_path> <slug> <desk> → ~/.claude/run/pm/pm-<KEY>.flag (write/overwrite) + arm-events.log (append) [honor — no hook intercepts the arm call; the skill logic drives it]`

The calling skill provides the absolute doc path, slug, and desk. `pm_flag.sh arm` writes the session
flag file with six fields: `doc_path`, `slug`, `desk`, `armed_at` (Unix timestamp), `cwd` (at arm
time), `session` (CLAUDE_CODE_SESSION_ID). Simultaneously appends a TSV line to `arm-events.log`:
`<ts>\tarm\t<doc>\t<slug>\t<desk>\t<session>`.

KEY derivation (identical in `pm_flag.sh` and `pm_persist.sh` — they MUST stay in sync):
- If `CLAUDE_CODE_SESSION_ID` is set: `KEY = "sess-$CLAUDE_CODE_SESSION_ID"` → flag path
  `~/.claude/run/pm/pm-sess-<id>.flag`
- Else: `KEY = "cwd-$(printf '%s' "$PWD" | shasum | cut -c1-12)"` → flag path
  `~/.claude/run/pm/pm-cwd-<hash>.flag`

`arm-events.log` is pruned on every write: after the append, if line count exceeds
`PM_EVENTLOG_MAX` (default 500), it is tail-trimmed to 500 lines keeping the most recent (and
therefore the just-appended) event.

The arm call is `[honor]` — no PreToolUse hook validates that the doc_path exists, belongs to a
real brief, or that the skill passed a correct cwd. A skill calling arm with a wrong path silently
poisons downstream routing.

---

#### Step 1 — EVERY-TURN INJECT (pm_persist.sh, UserPromptSubmit, fires every prompt)

`UserPromptSubmit → pm_persist.sh → reads pm/plan/scratch flags → refreshes TTLs + injects [project-manager ACTIVE] anchor [hook — registered settings.json line 337; advisory only, exit 0 always]`

On every UserPromptSubmit event:

**(a) KEY derivation** — reads stdin JSON for CWD fallback; derives KEY using the same scheme as
`pm_flag.sh` (session-id → cwd-hash fallback). If neither is available, exits 0 silently.

**(b) `_refresh_armed_at` calls (TTL anti-expiry)** — for each of the three sibling flag files that
exist for this session (`pm-<KEY>.flag`, `plan-<KEY>.flag`, `scratch-<KEY>.flag`), rewrites their
`armed_at` field to `now` via `sed -i`-equivalent. This prevents mid-session TTL expiry: as long
as the session is active and submitting prompts, no flag can age out and auto-delete. The refresh
only runs when the stored `session` field matches `CLAUDE_CODE_SESSION_ID` (or `CLAUDE_CODE_SESSION_ID`
is empty — the cwd-hash case).

**(c) Huddle side-channel** — reads `~/.claude/run/huddle/huddle-<KEY>.flag`. If it exists, has not
expired (TTL_HOURS=12 as set at pm_persist.sh line 16 — PM_TTL_HOURS; see Edge Case 7 below), and
belongs to this session, emits:
`[huddle ACTIVE: <room>] In an active huddle build — when you FINISH a major chunk...`.

**(d) PM flag read + TTL check** — reads `~/.claude/run/pm/pm-<KEY>.flag`. If the flag is missing,
exits 0 silently. If the flag exists but `armed_at` age >= `TTL_HOURS * 3600`, deletes the flag and
exits 0 silently. `pm_persist.sh` no longer carries its own TTL literal — it resolves the value from
`pm_flag.sh`'s `ttl` verb (36h default). **This was the TTL DRIFT BUG; it is now closed — see Edge
Case 1.**

**(e) Relative doc_path resolve** — if `doc_path` field is a relative path, resolves it against
`cwd_stored` (the CWD at arm time). This catches a skill that armed with a relative path; if
`cwd_stored` is absent or wrong, the resolve fails silently (no fallback).

**(f) Brief freshness** — `stat -f %m` on `doc_path` to compute elapsed time since last write
(`just now` / `Xm ago` / `Xh ago` / `Xd ago`; `NOT YET CREATED` if the file does not exist).

**(g) Current-state excerpt** — if the brief file exists, reads the first content line under a
heading matching `current state` or `next action` (case-insensitive, heading-bleed guarded via awk,
max 180 chars). Strips control chars, zero-width chars, and bidi markers via `LC_ALL=C tr` and
`perl -CSD`. The excerpt is fenced as verbatim data and labeled `NOT an instruction`.

**(h) Emit anchor** — outputs the `[project-manager ACTIVE]` line to stdout so the harness injects
it into the model's context prefix.

---

#### Step 2 — SAVE ROUTING GATE (save_routing_hint.sh, UserPromptSubmit)

`UserPromptSubmit → save_routing_hint.sh → regex-matches prompt for save-request phrases → if matched: calls pm_flag.sh status → ~/.claude/run/pm/pm-<KEY>.flag (read) → injects [save-routing] directive [hook — settings.json line 406, matcher ""; advisory only, exit 0 always]`

Fires ONLY when the user's prompt matches a save-request phrase (verb + demonstrative, or
verb + "scratchpad"). Handoff/reload fingerprint bailout: if the prompt contains `## SCRATCHPAD`
or `/checkin`, exits 0 silently (prevents false-fire on session reload pastes — a real 2026-07-15
incident).

When save intent is detected:
- If pm flag is active → injects `[save-routing]` directing append to the armed brief's
  `## SCRATCHPAD`, naming the exact path. Discourages filesystem scan or guessing.
- If no flag (or `none`) → injects ASK prompt: *"No project's active — save to a standalone
  scratchpad, or which project's brief?"*

This hook never prevents a write; it only injects advisory text. The CLAUDE.md save-routing rule
is the always-loaded backstop for the same behavior.

---

#### Step 3 — PLAN ANNOUNCE ROUTING (announce_plan_write.sh, UserPromptSubmit)

`UserPromptSubmit → announce_plan_write.sh → diffs ~/.claude/plans/*.md vs per-session state file → for NEW plan: calls pm_flag.sh status → ~/.claude/run/pm/pm-<KEY>.flag (read) → routes pointer into brief's ## SCRATCHPAD if flag active, else ~/.claude/run/plan-ledger.md [hook — settings.json line 396, matcher ""; advisory only, exit 0]`

On every turn, diffs the plan directory against a per-session state snapshot. For a NEW plan
file: emits a `📋 plan written:` visible inject AND writes a durable pointer line into the armed
brief's `## SCRATCHPAD` (via a direct Python file edit) if the pm flag is active, otherwise
into `~/.claude/run/plan-ledger.md`. For an UPDATED plan: only emits the visible inject (no
pointer written). Seeds silently on first run — pre-existing plans are never treated as "new."

---

#### Step 4 — CONTEXT SWITCH WARNING (scratch_sweep_nudge.sh, UserPromptSubmit)

`UserPromptSubmit → scratch_sweep_nudge.sh → checks scratch_flag.sh status; if not armed, checks pm_flag.sh status → ~/.claude/run/pm/pm-<KEY>.flag (read) → if either armed AND token count >= 600k threshold: emits switch-session warning (rate-limited, once per 100k-token bucket) [hook — settings.json line 386, no matcher field; advisory only, exit 0]`

A session with neither an active scratch_flag nor an active pm flag is a pure no-op. When either
is armed and context depth reaches 600k tokens (~60% of 1M, reasoning-fray threshold), emits a
once-per-100k-bucket switch warning to prompt a fresh session. Rate-limit state:
`~/.claude/run/sweep/sweep-<KEY>.state` (stores last bucket number).

---

#### Step 5 — STATUSLINE HUD READ (statusline.sh, statusLine command)

`every status-bar render → statusline.sh → reads pm/plan/scratch flag files → ~/.claude/run/pm/pm-<KEY>.flag (read) → extracts slug + armed_at + desk → renders HUD proj/plan/scratch tile + bottom-bar desk field [non-hook — runs as statusLine command, settings.json line 457; purely reads, never writes]`

On every status-bar render (triggered by the harness, not a hook event):

Reads `~/.claude/run/pm/pm-sess-<SID>.flag` (or `pm-cwd-<hash>.flag` fallback).

- **`proj:` HUD tile** — reads `slug` field; shows only within a 14-day freshness window
  (`fresh_field "$PM_FLAG" slug 20160`); colored by `armed_at` age: green (<24h) / yellow (<7d)
  / red (older).
- **`desk:` bottom-bar field** — reads `desk` field from the pm flag (`FLAG_DESK`) as the primary
  source; falls back to cwd-detection, then `root`. **TRUTH CONTRACT:** this field shows the session's
  actual desk, NEVER the project slug. A 2026-07-13 regression (`"${SLUG:-$DESK}"`) broke this by
  displaying the project slug in the desk field. Fixed; regression-guarded by
  `system/tools/statusline-truth-test.sh` (run via `system/tools/verify-hooks.sh`).
- `plan:` and `scratch:` tiles likewise read their sibling flag files.

`guard_statusline_lock.sh` (PreToolUse Bash, settings.json line 141) blocks any Bash command that
writes the `statusLine` pointer into `settings.json` or destroys/replaces `statusline.sh`. A 2026-07-23
fix hardened delimiter-agnostic detection of `sed -i` attacks.

---

#### Step 6 — SCRATCHPAD CAPTURE AT SESSION END (scratch_capture_gate.sh, Stop)

`Stop → scratch_capture_gate.sh → resolves pad by precedence: scratch_flag armed → scratch_path; else pm_flag.sh status → ~/.claude/run/pm/pm-<KEY>.flag (read) → brief as pad target → if token bucket advanced past last checkpoint: decision:block [hook — settings.json line 448, matcher ""; blocking-in-intent but exits 0 if no flag]`

At every Stop event, resolves the active pad: scratch_flag takes precedence; if no scratch_flag,
calls `pm_flag.sh status` as the fallback. If the resolved pad does not exist on disk, exits 0
silently. When a pad is found and the token bucket has advanced since the last checkpoint, emits a
`decision:block` JSON with the mechanically-diffed ADDED lines for the model to surface as a
`📝 SCRATCHPAD CAPTURED` receipt. Updates the bucket watermark and sidecar after each checkpoint.

The blocking is in-intent but conditional on flag presence — if no pm flag and no scratch_flag is
armed, the gate is entirely dormant.

---

#### Step 7 — RECOVERY PATH (/save Step 0.4, called by skill)

`/save (Step 0.4) → pm_flag_recover.py → ~/.claude/run/pm/arm-events.log (read) → returns NONE / CLEAR / ARM+fields [honor — called from SKILL.md Step 0.4 only; no hook enforces this call]`

When `/save` Step 0 sees `pm_flag.sh status` return `none`, Step 0.4 runs
`python3 .../pm_flag_recover.py`. The tool reads `arm-events.log`, filters to `CLAUDE_CODE_SESSION_ID`
events only (never cross-session bleed), and returns the last event type.

- `NONE` → no arm event for this session → nothing to recover → proceed as a `none` save.
- `CLEAR` → last event was an intentional clear → respect the stop; never override a deliberate clear.
- `ARM<TAB>doc<TAB>slug<TAB>desk` → flag dropped by TTL/loss but session WAS tracking → surfaces
  a one-tap confirm ("Sync its brief and re-arm tracking? [y/n]"); on `y`, re-arms the flag and
  uses the doc as the brief target for the whole save.

Recovery is session-scoped, logbook-grounded, and confirm-gated. It cannot recover from a `CLEAR`.
The logbook is append-only and survives flag TTL; only genuinely-executed arms land in it
(example/test arms in prose or transcript cannot trip a false recovery).

---

### STORES TOUCHED (complete list)

| Store | Written by | Read by | Notes |
|---|---|---|---|
| `~/.claude/run/pm/pm-sess-<SID>.flag` | `pm_flag.sh arm` | pm_persist.sh, save_routing_hint.sh, announce_plan_write.sh, scratch_sweep_nudge.sh, scratch_capture_gate.sh, statusline.sh | PRIMARY flag; fields: doc_path, slug, desk, armed_at, cwd, session |
| `~/.claude/run/pm/pm-cwd-<hash>.flag` | `pm_flag.sh arm` | same readers | CWD-hash fallback when session_id absent |
| `~/.claude/run/pm/arm-events.log` | `pm_flag.sh arm + clear` | `pm_flag_recover.py` | TSV, append-only, pruned to 500 lines; NOT read by any hook |
| `~/.claude/run/huddle/huddle-<KEY>.flag` | `huddle_flag.sh` | `pm_persist.sh` (read only) | pm_persist.sh checks for huddle-active reminder |
| `~/.claude/run/plan/plan-<KEY>.flag` | `plan_flag.sh` | `pm_persist.sh` `_refresh_armed_at` | TTL refresh only; statusline.sh reads it for plan tile |
| `~/.claude/run/scratch/scratch-<KEY>.flag` | `scratch_flag.sh` | `pm_persist.sh` `_refresh_armed_at` | TTL refresh only |
| `~/.claude/run/sweep/sweep-<KEY>.state` | `scratch_sweep_nudge.sh` | same | bucket watermark for switch-warning rate-limit |
| `~/.claude/run/scratch-capture/cap-sess-<SID>.state` | `scratch_capture_gate.sh` | same | bucket watermark for Stop-gate capture |
| `~/.claude/run/scratch-capture/cap-sess-<SID>.pad` | `scratch_capture_gate.sh` | same | sidecar of last-checkpointed scratchpad section |
| Active project brief (doc_path) | downstream skills/hooks (not pm_flag.sh itself) | `pm_persist.sh` (read for excerpt), `announce_plan_write.sh` (write plan pointer to ## SCRATCHPAD) | pm_flag.sh only stores the PATH; the brief content is the payload |
| `~/.claude/run/pm/lock-<KEY>.project` | `pm_flag.sh arm` (write-once; rewritten ONLY by a human-word override) | `pm_flag.sh` `_locked_id`, `pm_persist.sh` (TAMPER cross-check) | ⚠ ADDED 2026-08-15 — the window's project IDENTITY. Fields: lock_slug, lock_doc, lock_desk, locked_at, origin (`first-arm`/`logbook`/`human-override`), session; on an override also previous_slug + override_phrase. Pruned after 30 days. **NEVER deleted by `clear`** — that is what stops the clear-then-arm-elsewhere bypass |
| `~/.claude/run/pm/arm-denied.log` | `pm_flag.sh` (refusals AND authorised overrides) | humans | ⚠ ADDED 2026-08-15 — deliberately NOT `arm-events.log`: `pm_flag_recover.py` reads the LAST event there and would report a DENIED project as recoverable |
| `~/.claude/run/pm/override-<KEY>.grant` | `pm_persist.sh` ONLY (from the human's raw prompt) | `pm_flag.sh` `_consume_grant` **and `plan_flag.sh` `_consume_grant`** | ⚠ ADDED 2026-08-15 — the human-word grant. Fields: granted_at, session, phrase, cwd. **GENERIC ON PURPOSE — ONE grant type serves BOTH the project lock and the plan lock.** Single-use, burned on spend; dies on the next prompt that does not re-authorise |
| `~/.claude/run/plan/lock-<KEY>.plan` | `plan_flag.sh record`/`set` | `plan_flag.sh` `_locked_id` + its `locked` verb | ⚠ ADDED 2026-08-15 — the PLAN half's lock. Same shape, same grant, DIFFERENT store — and that store has **no custodian guard** (see wall 2b) |

---

### ⭐ THE LOCK — ADDED 2026-08-15 (the element described a world without it)

> ⚠ **CORRECTED 2026-08-15.** Everything below this heading is new to this element. The element as
> written described `pm_flag.sh` as a plain state writer whose "arm integrity" was honor-system
> (*"wrong path succeeds silently"*). **That has not been true since 2026-08-06.** The elements are
> DESCRIPTIVE — the code moved ahead of the description, so the description is what changes here.
> Nothing below asks the code to move backward.

**The ruling** (the owner, `authority: user`, verbatim): *"When you fire a plan in a project inside
of a session window, it should be LOCKED. If you want to change it, you need to go to a new session
window — unless the human explicitly says write to this other project or this other plan, in which
case I'm okay with the hook firing once and then the human can override the hook."*

**1. The project lock (2026-08-06).** The FIRST well-formed `arm` in a session writes
`lock-<KEY>.project`. After that, `arm` with a DIFFERENT slug is REFUSED (**exit 3**, nothing
written, logged to `arm-denied.log`) and `clear` is REFUSED (exit 3). A SAME-slug `arm` still
refreshes normally — `/checkin` Step 0 re-arms on every run and `/save`'s recovery path depends on
it. Keyed by session; the cwd-hash fallback is deliberately **not** lockable, because two windows in
one folder share that key and a lock there would refuse a legitimate window.
*Why it exists:* on 2026-08-06 a session re-armed its own window from `ingest-skill` to
`skill-builder` on its own judgment, mid-conversation. Two `/save` handoffs went to the wrong
project and a human-authored FRAME block in the wrong brief was edited. It recurred the same evening
in a second window. Prose could not stop it.

**2. The human-word override (2026-08-15) — the second half of the ruling.** Until this date only
the *new window* exit existed, so a human who said *"write to this other project"* was told to open
one. The override is built on the **one channel a model cannot write to: the raw
`UserPromptSubmit` prompt.** `pm_persist.sh` is the only code in the system handed that text; it
matches it against a **narrow closed list of explicit phrases** and writes
`override-<KEY>.grant`. `pm_flag.sh` `_consume_grant` burns it on **exactly one** change and shouts
on **stdout AND stderr**.
- ⛔ **THE CRUX: the override is the HUMAN'S WORD, not a flag the model can set for itself.** Every
  flag, env var, argument or file a session can set fails that test — it would be the model
  authorising itself. If the model can produce the thing that unlocks it, there is no lock.
- **What it deliberately does NOT do:** it does not read *which* project they named and does not
  check the arm against it. That comparison needs *"the ingest project"* to equal `ingest-skill`
  before it can run — judgement wearing a regex, and it would refuse correct work. The grant is
  permission for ONE change; the banner shouts the destination actually taken.
- **Lifetime:** one turn. The next prompt that does not re-authorise deletes it.
- **Session-bound:** a grant minted in one window is not consumable in another.
- **`clear` never deletes the LOCK**, authorised or not — that is what closes the two-step
  clear-then-arm-elsewhere bypass.
- **Stated hole, not an oversight:** a person who PASTES text containing one of the phrases issues a
  grant they did not mean; and a session with a shell can run `pm_persist.sh` itself (which is why
  `guard_pm_flag_store.sh` denies exactly that). There is deliberately **no validator inside the
  thing being forged** — a check the forger runs reads as protection while being none. The real
  backstop is NOISE: every spend prints a banner naming both projects, and writes `previous_slug` +
  `override_phrase` into the lock plus an `arm-override` line into the logbook. The owner's bar:
  *"I don't mind being able to write into a different brief; what I want is for it not to change
  without me seeing it."*

**3. The PLAN half (2026-08-15).** `plan_flag.sh` now carries the same lock for plans —
`lock-<KEY>.plan`, first-arm-wins, a different plan REFUSED (**exit 2** on the `record` /
ExitPlanMode hook path, which is the harness's block code so the second plan is genuinely not fired;
**exit 3** on the `set`/`clear` CLI verbs, matching `pm_flag.sh`, whose callers are skills). It
**consumes the SAME `override-<KEY>.grant`** — the 2026-08-15 lane made the grant generic and put it
in the pm store precisely so the plan lane could reuse it, and **no second grant type exists.**
Same-plan re-arms refresh normally (plan mode re-fires on every amendment); "same plan" is
`plan_file` OR H1 `name` string equality and nothing looser. One declared fail-open: if `record`
cannot work out which plan it was handed, it writes nothing **and refuses nothing** — refusing on no
evidence would wall off plan mode on a payload glitch.
Fire-tests: `system/hooks/tests/test_pm_lock_override.sh` (61 cases) ·
`system/hooks/tests/test_plan_lock_override.sh` (53 cases). Both counted by `verify-hooks.sh`.

**4. ⚠ THE TTL WAS INERT UNTIL 2026-08-15 — and two prior passes missed it.** Worth recording
because the failure hid behind two separate "fixes" that both looked complete:
- **2026-07-11** bumped the TTL 12h → 36h **in `pm_flag.sh` only.** `pm_persist.sh` carried its own
  independent copy of the default, still at 12h, and its expiry check runs every turn while
  `pm_flag.sh` runs only when invoked — so the stale copy always won. The 36h extension had never
  once taken effect.
- **2026-08-14** fixed *that* by deleting the duplicate literal: `pm_persist.sh` now reads the number
  from `pm_flag.sh`'s read-only `ttl` verb, which is the sole definition. **The TTL was still inert.**
- **2026-08-15 — the actual bug.** `_refresh_armed_at` ran **before** the expiry check and rewrote
  `armed_at` to *now* for any flag whose `session=` matched — **every flag in its own window**, which
  is the only case that ever reaches the check. The age it tested was always zero, so the value could
  never take effect **at any setting**. Measured: a **40-hour-old flag survived**; the same flag
  carrying a foreign `session=` was correctly deleted.
- **Fixed by deciding expiry against the value ON DISK first**, and refreshing only a flag that
  survived it. Both original intents stay whole: alive while you are working (every turn re-stamps
  it), aged out after a real gap. Now measured: **20h survives, 40h expires.** It matters most on
  `--resume` of a window abandoned for weeks — the one moment the TTL is actually *for*.

---

### GATES AND ENFORCEMENT (the honest map)

#### Real hook-enforced walls

**1. `guard_statusline_lock.sh`** (PreToolUse Bash, settings.json line 141) `[hook]` — **BLOCKING.**
Blocks any Bash command that writes the `statusLine` pointer into `settings.json` (via `sed -i`,
redirect, or `tee`) or destroys/moves/replaces `statusline.sh`. Does NOT protect the pm flag files
themselves (those live under `~/.claude/run/pm/`, not a guarded path). The 2026-07-23 fix added
delimiter-agnostic detection for `sed -i` attacks that used non-standard `s///` delimiters.

**2. `guard_write_paths.sh`** (PreToolUse Write|Edit) `[hook]` — **BLOCKING.** The residency wall
does NOT cover `~/.claude/run/pm/` — the flag store is machine-local and NOT in a protected Drive
path, so ~~no hook blocks a direct Write/Edit to the flag files themselves~~. It DOES protect
`settings.json` from direct Write/Edit.

> ⚠ **CORRECTED 2026-08-15** — the struck clause was true of `guard_write_paths.sh` and false of the
> system. **`guard_pm_flag_store.sh` IS registered** (PreToolUse `Bash|Write|Edit`,
> `.claude/settings.json:181`) and it *does* block a direct Write/Edit anywhere under
> `~/.claude/run/pm/`, plus a Bash command that names the store and carries a write/destroy token,
> plus running `pm_persist.sh` by hand (the grant-forgery route). It is listed as **wall 2b** below.
> ⛔ It is a **speed bump, not a wall, by its own header's admission** — it matches text, does not
> resolve variables, `cd`s or symlinks, and an audit walked past it several ways. Do not read this
> correction as "the store is now safe"; read it as "the claim that nothing guards it is false."

**2b. `guard_pm_flag_store.sh`** (PreToolUse `Bash|Write|Edit`, `.claude/settings.json:181`) `[hook]`
— **BLOCKING.** The custodian of the arming store. Denies (a) any `Write`/`Edit`/`NotebookEdit`
whose target is under `~/.claude/run/pm/`; (b) any Bash command that names that path **and** carries
a write/destroy token in the same command segment (redirect · `rm`/`mv`/`cp`/`tee`/`truncate`/`ln`/
`dd`/`chmod`/`touch`/`shred` · `sed -i`/`perl -i` · an interpreter shown doing a write); (c) running
`pm_persist.sh` by hand — the sole issuer of the human-word grant, which would otherwise let a
session pipe itself a sentence the person never typed. Reads of the store (`ls`/`cat`/`grep`) and
ordinary `pm_flag.sh arm|clear|status|locked` stay allowed. **FAIL_POSTURE: closed** — unparseable
input denies. Fire-test: `system/hooks/tests/test_pm_lock_override.sh` §11.
**⛔ The store it guards is `~/.claude/run/pm/` ONLY. `~/.claude/run/plan/` — which now holds the
plan lock (below) — is NOT covered**, so a direct write to `plan-<key>.flag`, or a delete of
`lock-<key>.plan`, skips the plan refusal entirely. Stated, not overlooked.

#### UserPromptSubmit hooks (ambient — fire every turn, advisory only)

**3. `pm_persist.sh`** (UserPromptSubmit, settings.json line 337) `[hook]` — registers with matcher
`""` (fires on all prompts). Non-blocking (always exits 0). Refreshes sibling TTLs and injects the
`[project-manager ACTIVE]` anchor. Its advisory output CAN be ignored by the model; there is no
mechanical enforcement that the model acts on the injected brief routing.

**4. `save_routing_hint.sh`** (UserPromptSubmit, settings.json line 406) `[hook]` — matcher `""`.
Always exits 0. Injects save-routing direction but CANNOT prevent a mis-routed save write.

**5. `announce_plan_write.sh`** (UserPromptSubmit, settings.json line 396) `[hook]` — matcher `""`.
Always exits 0. Directly edits the brief's `## SCRATCHPAD` section when a NEW plan is detected.
This is the one pm-flag-reader hook that actually WRITES a non-flag file (the brief) — the only
mechanical mutation this hub causes in downstream content.

**6. `scratch_sweep_nudge.sh`** (UserPromptSubmit, settings.json line 386, no explicit matcher
field) `[hook]` — advisory switch-warning only. Always exits 0.

#### Stop hook

**7. `scratch_capture_gate.sh`** (Stop, settings.json line 448) `[hook]` — **BLOCKING-IN-INTENT.**
Emits `decision:block` when the token bucket advances past a checkpoint AND an active pad (scratch
or pm brief) is found. If no flag is armed, exits 0 silently — so the blocking is conditional on
session state, not unconditional.

#### Honor-system

**8. Flag arm integrity** `[honor]` — no hook validates that the doc_path passed to `pm_flag.sh arm`
is a real brief, exists, or belongs to the armed session. A skill providing a wrong path poisons the
entire downstream chain (routing hints, HUD, capture gate, scratchpad writes) silently.

**9. `pm_flag_recover.py` call** `[honor]` — mandated by `/save` SKILL.md Step 0.4. No PreToolUse
hook enforces the call. A revised skill that skips Step 0.4 silently loses recovery.

**10. Brief routing honor** `[honor]` — save_routing_hint.sh injects advisory text; the model can
still write to the wrong place when a project is armed. No PreToolUse guard blocks an off-brief
write when the flag is set.

---

### EDGE CASES

**1. TTL DRIFT BUG (history — ✅ RESOLVED; kept because the shape of the bug is the lesson):**
As authored 2026-07-23 this read: `pm_flag.sh` uses `TTL_HOURS=36` (set 2026-07-11, noted in the
header comment at line 11), `pm_persist.sh` uses `TTL_HOURS=12` (its own line 16; header comment
still saying "default 12h"). The two scripts share the same flag file but enforced different TTLs,
so a flag that `pm_flag.sh status` would consider alive (age 13h–36h) was silently deleted by
`pm_persist.sh`'s TTL check on the next UserPromptSubmit turn. The `_refresh_armed_at` function in
pm_persist.sh masked it — it rewrites `armed_at` to `now` on every turn and runs BEFORE the TTL
check, so mid-session expiry was prevented in practice. But if `_refresh_armed_at` failed (sed
failure, filesystem error, race) and `armed_at` was not updated, pm_persist.sh would delete at 12h
a flag pm_flag.sh would have kept for 36h. LIVE CODE WON: `pm_persist.sh` was the operative per-turn
value, and the 36h intent had never once taken effect.

**✅ THE DRIFT IS CLOSED — there is now ONE definition of the TTL.** `pm_flag.sh:68` holds it
(`TTL_HOURS="${PM_TTL_HOURS:-36}"`) and exposes it through a read-only `ttl` verb; `pm_persist.sh`
no longer carries a literal at all, resolving its default at runtime via
`TTL_HOURS="${PM_TTL_HOURS:-$(_pm_default_ttl)}"`, where `_pm_default_ttl()` shells out to
`pm_flag.sh ttl` (`pm_persist.sh:44-60`). `PM_TTL_HOURS` still short-circuits first when set, so no
subprocess runs in the common env-override case. The literal `36` inside `_pm_default_ttl` is an
explicit last-resort fallback for when `pm_flag.sh` cannot be found or run at all — it fails toward
the CURRENT correct value and is **not** a second source of truth; if the default ever changes it
changes in `pm_flag.sh` only. The fix names its own cause: two files carrying the same literal is
exactly how the 2026-07-11 bump landed in one file and never reached the other.

**2. KEY derivation must stay in sync:**
`pm_flag.sh` and `pm_persist.sh` use identical KEY derivation logic, but they are separate scripts.
A change to one (e.g., different hash function, different cwd source) that is not mirrored in the
other causes the hook to look at a different flag file than the tool writes — silent mismatch, no
error, zero output. This is a maintenance trap.

**3. `_refresh_armed_at` race/failure:**
The refresh uses `sed "s/^armed_at=.*/armed_at=$_now/" "$1" > "$_tmp" && mv "$_tmp" "$1"`. If sed
or mv fails (e.g., filesystem full, concurrent write), the flag retains the old `armed_at` and the
TTL check on the very next line may delete it. The script is `set +e` and has no retry, so a single
failure silently drops the flag.

**4. No flag validation on arm:**
`pm_flag.sh arm` requires only that `$2` (doc_path) is non-empty; it writes whatever value is
provided. A skill can arm with a non-existent path, a relative path (resolved only later by
pm_persist.sh using `CWD_STORED`, which depends on the skill having passed the correct cwd), or
a completely wrong path. The downstream consequence is that pm_persist.sh injects a reference to
a nonexistent or wrong brief, announce_plan_write.sh may write a plan pointer to the wrong file,
and scratch_capture_gate.sh may use the wrong brief as the scratchpad target.

**5. Clear only sweeps session-scoped flags:**
`pm_flag.sh clear` with a `CLAUDE_CODE_SESSION_ID` env set will also sweep any flags in the pm
directory whose stored `session=` field matches that session id. A cwd-hash flag from a session
without a session_id is cleared only if `KEY` matches (same cwd). Cross-session pollution is
structurally prevented by the session-id match in `pm_flag_recover.py`.

**6. `statusline.sh` uses a different freshness window than `pm_flag.sh` TTL:**
`statusline.sh` shows the `slug` field within a 14-day freshness window (`fresh_field ... 20160`
minutes). `pm_flag.sh` TTL is 36 hours. So the HUD tile can persist and show a stale proj entry
for up to 14 days even after the flag itself would have been deleted by the next status call. This
is by design (the HUD retains the last-known project for ambient orientation even across sessions)
but creates an appearance of ongoing tracking when no flag actually exists.

**7. Huddle TTL inside pm_persist.sh is governed by PM_TTL_HOURS, not a separately tunable constant:**
`pm_persist.sh` applies its own resolved `TTL_HOURS` when checking the huddle flag expiry in its
per-turn loop (step (c)), rather than a separately governed `HUDDLE_TTL_HOURS`. `huddle_flag.sh`
uses `TTL_HOURS=${PM_TTL_HOURS:-12}` as its own write TTL. The two are therefore free to disagree:
the operative TTL for the huddle flag during a UserPromptSubmit turn is always whatever
`pm_persist.sh` resolved — `PM_TTL_HOURS` when set, otherwise `pm_flag.sh`'s definition (36h; see
Edge Case 1) — regardless of what `huddle_flag.sh` wrote it with. The 12h default now lives only on
the huddle side. ⚠ **DESCRIPTIVE DEBT:** the huddle side-channel described here is a donor
mechanism; it is not present in this repo's `pm_persist.sh`, and no `huddle_flag.sh` ships. Recorded
as written rather than silently deleted.

---

### INTENT / CURRENT-VS-TARGET

**Purpose:** provide a single, machine-checkable, always-current signal of which project brief is
the active context anchor — so that every hook and skill that needs to route saves, injections, HUD
tiles, plan pointers, and session-close captures can do so without each one re-deriving the active
project from scratch or from the less-reliable context window.

**BY DESIGN — the hub, not the wall:**
pm-flag does not block anything on its own; it is a ROUTING STATE source read by the gates and
skills that do the actual blocking and routing. The separation is intentional: the state store stays
simple (a tiny flat-key file), while enforcement and routing logic lives in the consumers.

**BY DESIGN — degrade-safe throughout:**
Every consumer of pm_flag.sh status handles the `none` case gracefully (silent pass-through or
advisory-only). A broken or expired flag degrades to "no project armed" behavior, never to a hard
failure. The recovery path (`pm_flag_recover.py`) adds a logbook-based safety net above the pure
TTL-based degradation.

**Current state → PARTIAL·gap:**
- Hook registration is real and verified (`pm_persist.sh` UserPromptSubmit at settings.json:337,
  scratch_capture_gate.sh Stop at settings.json:448, save_routing_hint.sh and announce_plan_write.sh
  registered; statusLine command registered).
- `_refresh_armed_at` prevents mid-session TTL expiry in the normal case.
- `arm-events.log` + `pm_flag_recover.py` provide a real, logbook-grounded recovery path.
- `guard_statusline_lock.sh` BLOCKS Bash attacks on the statusline script that reads the flag.
- What is honor-system: arm integrity (wrong path, wrong slug, wrong desk all succeed silently),
  save routing (advisory only — model can still write to wrong place), `pm_flag_recover.py` call
  (mandated by skill prose, not a hook). The TTL-drift bug that used to sit in this list — a
  mid-session expiry window opened by pm_persist.sh's 12h against pm_flag.sh's 36h whenever
  `_refresh_armed_at` failed — is ✅ closed: there is one TTL definition now (Edge Case 1).

**TARGET:**
1. **Resolve TTL drift** — ✅ DONE, and not by aligning a second literal: `pm_persist.sh` stopped
   carrying a TTL literal altogether and now reads `pm_flag.sh`'s via its `ttl` verb, so there is a
   single definition (36h) that cannot drift again (Edge Case 1).
2. **Add arm-path validation** — a simple `[ -f "$2" ]` check in `pm_flag.sh arm` (with a warning,
   not a hard block) would catch the wrong-path case before it poisons downstream routing.
3. **Harden save routing** — today the routing hint is advisory; a PreToolUse Write gate that checks
   the pm flag when writing to a `## SCRATCHPAD`-adjacent path would close the off-brief write gap.

---

### INTEROP SEAMS (shared-state edges to other elements — the organism view)

INTEROP:
  TRIGGERS    project-manager   · /project-manager calls pm_flag.sh arm after the intake/interview identifies doc path/slug/desk — NOT as the first step; intake comes first [honor]
  TRIGGERS    checkin           · /checkin has two paths: (a) front-door args → arm immediately; (b) no args → status check first, then arm after resolution; arm is not universally first [honor]; /read re-arms on rehydrate when a project was previously tracked [honor]
  TRIGGERS    design-lifehack  · /design-lifehack discovery SOP references pm_flag.sh arm for project activation [honor]
  READS       save              · /save Step 0 calls pm_flag.sh status to route the write; Step 0.4 calls pm_flag_recover.py to recover a dropped flag from arm-events.log; re-arms after a successful save to refresh TTL [honor]
  READS       scratch-capture-gate  · scratch_capture_gate.sh calls pm_flag.sh status as fallback pad resolver when no scratch_flag is armed; pm brief becomes Stop-gate scratchpad target [hook]
  READS       hook-plane        · announce_plan_write.sh calls pm_flag.sh status on every UserPromptSubmit turn (unconditional); save_routing_hint.sh calls pm_flag.sh status ONLY when prompt matches a save-request phrase (early-exit otherwise); scratch_sweep_nudge.sh calls pm_flag.sh status ONLY when scratch_flag is not armed (skipped when scratch is armed) [hook]
  SYNCS       plan-flag         · pm_persist.sh refreshes plan-<KEY>.flag armed_at on every turn via _refresh_armed_at; /advisory-council also reads plan_flag.sh path (plan file path) alongside pm_flag.sh status to build the settled-ground card [honor]
  SHARES      plan-flag         · ⚠ ADDED 2026-08-15 — plan_flag.sh consumes THE SAME ~/.claude/run/pm/override-<KEY>.grant that pm_flag.sh does, minted by the same pm_persist.sh against the same closed phrase list (which already covers the plan wording). ONE grant type serves both locks; there is no plan-only grant [hook]
  SYNCS       scratch-flag      · pm_persist.sh refreshes scratch-<KEY>.flag armed_at on every turn via _refresh_armed_at [hook]
  READS       huddle-flag       · pm_persist.sh reads huddle-<KEY>.flag each turn to inject BUILD CLOSE-OUT nudge for active huddle sessions; huddle TTL applied is PM_TTL_HOURS (see Edge Cases) [hook]
  READS       huddle            · /huddle and /huddle-board call pm_flag.sh status to locate the active project brief before posting or cross-referencing [honor]
  READS       advisory-council  · /advisory-council calls pm_flag.sh status AND plan_flag.sh path before convening advisors to build the settled-ground card from the active brief and plan [honor]
  READS       helm              · statusline.sh reads the pm flag to compose the proj: HUD tile (slug + freshness color) and desk: bottom-bar field (desk=, not slug — TRUTH CONTRACT) [honor for read]
  GUARDED-BY  guard_statusline_lock.sh  · PreToolUse Bash hook blocks Bash commands that destroy or repoint the statusline script that reads the pm flag; ~~the flag store itself (~/.claude/run/pm/) has no PreToolUse write guard~~ [hook]
              ⚠ CORRECTED 2026-08-15 — FALSE. `guard_pm_flag_store.sh` IS registered (PreToolUse Bash|Write|Edit, .claude/settings.json:181) and guards exactly that store. See GATES wall 2b. A speed bump, not a wall.
  GUARDED-BY  guard_pm_flag_store.sh    · PreToolUse Bash|Write|Edit; denies direct writes to ~/.claude/run/pm/ (flag · lock · grant) and denies running pm_persist.sh by hand (the grant-forgery route) [hook]

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL·gap
- **check_detail:** pending label_checker.py — PROVISIONAL basis for PARTIAL: hook registration is
  verified (`pm_persist.sh` UserPromptSubmit at settings.json:337; `save_routing_hint.sh` and
  `announce_plan_write.sh` and `scratch_sweep_nudge.sh` UserPromptSubmit; `scratch_capture_gate.sh`
  Stop at settings.json:448; `statusLine` command at settings.json:457). `_refresh_armed_at`
  prevents mid-session TTL expiry in the normal case. `arm-events.log` + `pm_flag_recover.py`
  provide a real logbook-grounded recovery path. `guard_statusline_lock.sh` BLOCKS Bash attacks
  on the statusline. What is honor-system: ~~arm integrity (wrong path succeeds silently)~~, save
  routing advisory-only, `pm_flag_recover.py` call skill-prose only (no hook), ~~TTL drift bug
  (pm_persist.sh 12h vs pm_flag.sh 36h — pm_persist.sh is the operative value)~~. Mixed (real hook
  surface alongside material honor-system gaps) ⇒ **PARTIAL·gap** (~~three~~ documented fail-open
  [honor] bypasses: ~~arm integrity,~~ save routing, pm_flag_recover.py call — each with named
  blast-radius). ~~Cannot be LIVE without fire-testing the per-turn inject + TTL-refresh contract;
  TTL drift bug should be resolved before LIVE claim.~~

  > ⚠ **CORRECTED 2026-08-15.** Two of the three struck claims are stale, and they were the two the
  > label rested on. **(a) Arm integrity is no longer honor-system** — the project lock
  > (2026-08-06) refuses a re-arm onto a different slug outright, `guard_pm_flag_store.sh`
  > (`.claude/settings.json:181`) is the store's custodian, and the only thing that moves a locked
  > window is the human's own words via a single-use grant. **(b) The TTL drift bug is resolved** —
  > single-sourced 2026-08-14 (`pm_flag.sh ttl`), and the deeper inertness fixed 2026-08-15
  > (`_refresh_armed_at` ran before the expiry check, so the age tested was always zero; measured
  > now: 20h survives, 40h expires). **(c) The fire-testing this said was missing now exists** —
  > `system/hooks/tests/test_pm_lock_override.sh` (61 cases) and
  > `system/hooks/tests/test_plan_lock_override.sh` (53 cases), both counted by `verify-hooks.sh`.
  > **Save routing and the `pm_flag_recover.py` call remain honor-system**, and the store guard is a
  > speed bump by its own admission — so the label is NOT being raised here. This corrects the
  > *basis*; re-grading the label is `label_checker.py`'s job, not this note's.
