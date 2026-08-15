---
element: scratch-capture-gate
title: "scratch-capture-gate — element detail (ground/base altitude)"
subsystem: memory
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: by-design
gap_disposition_note: "ruled 2026-07-28 at class level — C3 degrade-safe by design (a Stop hook cannot write the reply pane); the 36h-vs-12h TTL mismatch is C8 prose drift"
generated_from:
  - system/hooks/scratch_capture_gate.sh
  - system/hooks/scratch_flag.sh
  - system/hooks/pm_flag.sh
  - system/hooks/scratch_sweep_nudge.sh
  - system/hooks/save_routing_hint.sh
  - system/hooks/pm_persist.sh
  - system/reference/settings.json (Stop event entry[3], matcher ""; UserPromptSubmit entries[1],[6],[8])
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# scratch-capture-gate — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. The marker records what
> happened to the named file AT THIS DESTINATION; it does not change the description.
>
> ⛔ `system/reference/settings.json` did not come across. It was the donor's read-only reference copy of the
> harness config; this repo's hook registry is `.claude/settings.json`, independently authored and smaller —
> an equivalent, never a copy. Check any registration claim below against that file.

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the session-memory anti-loss
> Stop-gate. The MIDDLE manual (`system/organism/manual.md`) carries only a one-line + pointer here;
> the TIP (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **One-line:** prevent session-memory loss by blocking every turn-end (once per ~100 k-token bucket)
> when the active scratchpad has un-captured work — forcing the model to surface an ADDED-lines receipt
> before the turn can complete.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires, emits decision:block) · `[advisory]` (hook fires but
> never blocks, exit 0 on all paths) · `[honor]` (prose instruction only, no mechanical enforcement) ·
> `[human]` (deliberate HITL pause).

> **LADDER:** ELEMENT (full mechanics). up → manual#scratch-capture-gate ; ground truth → system/hooks/scratch_capture_gate.sh

---

## AUTHORED   (human-only)

### TRIGGER / MODES

**This element has ONE mode: the Stop-event blocking gate.**
There are no subcommands. The supporting sibling hooks (scratch_sweep_nudge.sh, save_routing_hint.sh,
pm_persist.sh) are separate registered hooks that share stores; they are NOT modes of this element.

**Mode 1 — Stop-gate (the only mode)**
- **Event:** Stop (every turn-end).
- **Registration:** `settings.json` Stop entry[3] — `{"matcher":"","hooks":[{"type":"command","command":"bash ...scratch_capture_gate.sh","statusMessage":"Scratchpad capture gate..."}]}` — fires on ALL Stop events; no selector.
  (settings.json line 448)
- **Behavior:** blocking on due turns — emits `{"decision":"block","reason":"..."}` via stdout + `exit 0`; silent `exit 0` on all other turns. Never calls a model; all computation is mechanical shell/Python3.

**Pre-conditions for any effect (the dormancy cascade):**
1. `stop_hook_active` must be `false` in the Stop payload (loop-safety exit; scratch_capture_gate.sh line 39).
2. A valid `session_id` must be present in the payload (line 40).
3. Either `scratch_flag` or `pm_flag` must resolve to an existing file (pad path; line 51).
4. Token count must be parseable from the transcript (JSONL file must exist + have assistant usage blocks; line 72).
5. Current token bucket must exceed the last checkpoint bucket (new 100 k increment has elapsed; line 107).

If any pre-condition fails, the gate exits 0 silently — designed fail-open (degrade-safe; hook header line 23).
`set +e` runs throughout the entire script (line 26): every subcommand failure silently continues.

---

### HAND-OFF CHAIN (actor → port → store → gate)

```
Stop event (every turn-end)
  → scratch_capture_gate.sh  [Stop hook, settings.json entry[3], matcher ""]
      │
      ├─ 1. LOOP-SAFETY CHECK
      │      read stop_hook_active from Stop JSON payload (stdin)
      │      if True → exit 0 immediately  [hook: loop guard, line 39]
      │
      ├─ 2. SESSION-ID PARSE
      │      read session_id from Stop JSON payload
      │      if empty → exit 0  [hook: dormancy guard, line 40]
      │
      ├─ 3. PAD RESOLUTION (precedence: scratch_flag first, pm_flag fallback)
      │      → scratch_flag.sh status (CLAUDE_CODE_SESSION_ID=$SID)
      │            reads: ~/.claude/run/scratch/scratch-$KEY.flag  (KEY="sess-$SID" when SID set)
      │            if "armed" → gate hardcodes FLAG="~/.claude/run/scratch/scratch-sess-$SID.flag"
      │                         (scratch_capture_gate.sh line 45 — hardcoded pattern)
      │                         PAD = grep '^scratch_path=' from that hardcoded flag path
      │            ⚠ KEY MISMATCH GAP: if scratch_flag was armed via cwd-hash key (no SID at
      │              arm time), scratch_flag.sh status with SID env set returns "armed" but the
      │              gate's hardcoded path (scratch-sess-$SID.flag) misses the real cwd-keyed flag
      │              (scratch-cwd-<hash>.flag); PAD grep finds nothing → PAD="" → gate goes dormant.
      │              (See Gap 6.)
      │              30m TTL self-expires on status call; pm_persist.sh refreshes armed_at each
      │              turn so active sessions do not expire.  (scratch_flag.sh line 34)
      │      → pm_flag.sh status (CLAUDE_CODE_SESSION_ID=$SID)  [only if scratch_flag = none/empty PAD]
      │            reads: ~/.claude/run/pm/pm-$KEY.flag  (KEY="sess-$SID" or "cwd-<hash>")
      │            TTL: pm_flag.sh line 17 sets TTL_HOURS=36 (pm_flag.sh own expiry);
      │                 BUT pm_persist.sh (line 16) uses TTL_HOURS=12 and ALSO deletes the flag
      │                 at 12h (pm_persist.sh line 83) — effective TTL is 12h (whichever fires first).
      │            if "none" → PAD = ""
      │      if PAD = "" or PAD file not on disk → exit 0  [hook: dormancy guard, line 51]
      │
      ├─ 4. TOKEN-COUNT SIGNAL
      │      read transcript_path from Stop JSON payload
      │      open JSONL transcript; walk all lines; find LAST assistant message with usage block
      │      sum: input_tokens + cache_creation_input_tokens + cache_read_input_tokens = TOK
      │             (scratch_capture_gate.sh lines 54–71)
      │      CAPTURE_EVERY = 100000  (line 28)
      │      if TOK empty or non-numeric → exit 0  [hook: degrade-safe, line 72]
      │      compute: BUCKET = TOK / 100000 (integer div)
      │
      ├─ 5. STATE SIDECAR LOOKUP
      │      STATEDIR = ~/.claude/run/scratch-capture/  (line 75)
      │      reads: ~/.claude/run/scratch-capture/cap-sess-$SID.state  (bucket watermark)
      │             (SFILE, line 76)
      │      reads: ~/.claude/run/scratch-capture/cap-sess-$SID.pad    (last-checkpoint section copy)
      │             (SIDECAR, line 77)
      │      LASTBUCKET = value of "bucket=" line in .state file  (line 78)
      │
      ├─ 6. FIRST-SIGHT SEEDING (only when LASTBUCKET is empty = first Stop in session)
      │      seed .state with "bucket=$BUCKET"; cp current SCRATCHPAD section → .pad sidecar
      │      exit 0  [hook: never blocks on turn 1, lines 100–103]
      │
      ├─ 7. DUE-CHECK (common path — BUCKET ≤ LASTBUCKET → silent)
      │      if BUCKET ≤ LASTBUCKET → rm temp; exit 0  [hook: token-bucket gate, line 107]
      │
      └─ 8. DUE → COMPUTE DIFF + BLOCK
             extract current ## SCRATCHPAD section from PAD file
               (Python3 inline: regex match on "SCRATCHPAD" header; fallback: whole file)
               (lines 82–96)
             python3 inline diff: ADDED = current lines NOT in .pad checkpoint (non-empty, non-header)
               (lines 110–121)
             capped at 20 shown lines ("+N more" suffix if larger)
             advance watermark: echo "bucket=$BUCKET" > .state; cp current section → .pad
               (lines 124–126)
             │
             ├─ if ADDED non-empty → emit block with a VERIFY instruction:
             │      "already captured since the last checkpoint — verify it covers the recent work;
             │       anything missing, spawn ONE sonnet SUB-AGENT to append it. Reply ONE line:
             │       '📝 Scratchpad: N lines captured, verified'. ⛔ Do not reprint the lines."
             │      {"decision":"block","reason":"SCRATCHPAD CHECKPOINT (~${K}k tokens)..."}
             │
             └─ if ADDED empty → emit block with a DELEGATED-WRITE instruction:
                    "⛔ Do NOT write the pad from this window. Spawn ONE sub-agent, model: sonnet:
                     read this session and append the decisions / observations / loose-threads worth
                     keeping to the '## SCRATCHPAD' section of ${PAD}. Nothing new ⇒ it appends a
                     dated '— (no new decisions) —' line. It returns EXACTLY ONE of:
                     'WROTE <n> lines' · 'NOTHING-TO-CAPTURE' · 'FAILED <why>' — never the content,
                     and never FAILED reported as NOTHING-TO-CAPTURE. Then print ONE line:
                     '📝 Scratchpad: <that verdict>'."
                    {"decision":"block","reason":"SCRATCHPAD CHECKPOINT (~${K}k tokens) — nothing..."}
             exit 0

             ⚠ THE PAD WRITE IS DELEGATED, NOT DONE IN THE MAIN WINDOW — and this element described
             the older main-window shape for longer than the code had it. **Both repos already
             delegate**; this is documentation lag, not a migration change. Why the shape: asking the
             main window to write the pad AND reprint the lines back put three copies of the same
             text (model output, file write, reprint) into the exact window the gate exists to
             protect. Sonnet, not haiku, because deciding what matters in a session is judgment and
             lossy compression the caller cannot cheaply check. The three verdicts are a BOUNDED SET
             with FAILED as the explicit no-outcome member — a dead sub-agent and an empty session
             are DIFFERENT FACTS, and conflating them loses a session's decisions silently. The pad
             is CLEARED only at the approval-gated compaction in `/save` or `/checkin`, never here.
```

---

### PORTS TOUCHED

| Port / Tool | Direction | Purpose |
|---|---|---|
| Stop event JSON (stdin) | READ | session_id, stop_hook_active, transcript_path |
| `scratch_flag.sh status` | READ | primary pad resolver — armed state + scratch_path (30m TTL, scratch_flag.sh line 18) |
| `pm_flag.sh status` | READ | secondary pad resolver — active brief path (36h TTL in pm_flag.sh; 12h effective via pm_persist.sh) |
| JSONL transcript (`transcript_path`) | READ | last assistant usage block → token count |
| `~/.claude/run/scratch-capture/cap-sess-$SID.state` | READ + WRITE | bucket watermark (last checkpoint) |
| `~/.claude/run/scratch-capture/cap-sess-$SID.pad` | READ + WRITE | last-checkpoint SCRATCHPAD section copy |
| Active pad file (brief or scratch_path) | READ | current ## SCRATCHPAD section for diff |
| stdout | WRITE | `{"decision":"block","reason":"..."}` on due turns; nothing otherwise |

---

### OUTCOME

On a due turn with captured or missing scratchpad work: the Stop-event block fires once, the model
cannot complete the turn without (a) verifying or extending the captured diff and (b) printing a
visible `📝 SCRATCHPAD CAPTURED` receipt in its reply. The turn then completes. The watermark advances
so the same bucket never blocks twice.

On all other turns (not due, dormant, or error): silent exit 0.

---

### GENERATED_FROM

- `system/hooks/scratch_capture_gate.sh` — the Stop hook (primary logic)
- `system/hooks/scratch_flag.sh` — pad override resolver (arm/clear/status; 30m TTL; scratch_flag.sh line 18)
- `system/hooks/pm_flag.sh` — brief path resolver (arm/clear/status; 36h TTL native; effective 12h)
- `system/hooks/pm_persist.sh` — UserPromptSubmit hook that maintains pm_flag (12h TTL; pm_persist.sh line 16)
- `system/hooks/scratch_sweep_nudge.sh` — sibling UserPromptSubmit hook (advisory switch-session warning)
- `system/hooks/save_routing_hint.sh` — sibling UserPromptSubmit hook (advisory save routing)
- `system/reference/settings.json` — Stop entry[3] (matcher "", line 448); UPS entries[1],[6],[8]

---

### ENFORCEMENT POINTS (the honest map)

Every gate, with its real enforcement tag and failure posture:

**1. `scratch_capture_gate.sh` as Stop hook — the ONLY hard block** `[hook]`
Registration: `settings.json` Stop entry[3], matcher `""`. On a due turn: outputs
`{"decision":"block","reason":"..."}` to stdout → Claude Code's Stop-event framework prevents
turn completion until the model writes a reply (which must include the receipt). This is the sole
mechanically-enforced capture trigger in the continuous pipeline.
Tag: `[hook]` — emitting `decision:block` via a registered Stop hook is real enforcement.
(scratch_capture_gate.sh lines 128–132 non-empty, 134–135 empty-ADDED)

**2. Loop-safety gate** `[advisory]`
Reads `stop_hook_active` from Stop payload. If `True` (already bounced this turn), exits 0
immediately, preventing infinite re-fire. Runs inside the Stop hook but always exits 0 — never emits
`{"decision":"block"}` on this path.
(scratch_capture_gate.sh line 39)

**3. Dormancy gate (pad-path)** `[advisory]`
If neither `scratch_flag` nor `pm_flag` resolves to an existing file, exits 0. No pad = no gate.
Fires automatically on every Stop event but always exits 0 — never emits `{"decision":"block"}` on
this path.
(scratch_capture_gate.sh line 51)

**4. Token-bucket gate** `[advisory]`
If `BUCKET ≤ LASTBUCKET` (no new 100 k increment), exits 0 silently. Ensures at most one block per
100 k-token bucket per session. Always exits 0 on this path — no block emitted.
(scratch_capture_gate.sh line 107)

**5. First-sight seeding** `[advisory]`
On the very first Stop call in a session (`LASTBUCKET` empty): seeds the watermark and sidecar, exits
0. Never blocks on the first turn — always exits 0, no `{"decision":"block"}` emitted.
(scratch_capture_gate.sh lines 100–103)

**6. Token-count degrade-safe** `[advisory]`
If transcript is absent, unreadable, or has no assistant usage blocks, exits 0. An inaccessible
transcript means no block — the posture is fail-open, not fail-closed. Always exits 0 on this path.
(scratch_capture_gate.sh line 72)

**7. `scratch_sweep_nudge.sh`** (UserPromptSubmit, settings.json UPS[6]) `[advisory]`
Advisory-only sibling hook: at ~600 k tokens (SWITCH_AT=600000, scratch_sweep_nudge.sh line 25)
emits a switch-session warning. Non-blocking; exit 0 on all paths. Shares the transcript
token-counting approach and the scratch_flag/pm_flag precondition. UPS[6] has no `matcher` field.
Explicitly retired its old capture-nudge role (F5.4, 2026-07-15, hook comment line 6) — this gate
replaced it as the mandatory arm. NOT a capture enforcement mechanism — purely advisory late-session warning.

**8. `save_routing_hint.sh`** (UserPromptSubmit, settings.json UPS[8], matcher `""`) `[advisory]`
Advisory-only. Fires when a save-verb prompt matches (save_routing_hint.sh lines 37–51); injects
routing instruction toward the pm-armed brief's `## SCRATCHPAD`. Does NOT block. Reinforces the
same scratchpad target this gate protects but is entirely non-blocking.

**9. `pm_persist.sh`** (UserPromptSubmit, settings.json UPS[1], matcher `""`) `[advisory]`
Fires every turn; injects the active brief path + pm-flag reminders. Also maintains the `pm_flag`
this gate depends on for its secondary pad resolver (refreshes `armed_at` on each turn via
`_refresh_armed_at`, pm_persist.sh lines 37–50). CRITICAL: pm_persist.sh uses its own
`TTL_HOURS="${PM_TTL_HOURS:-12}"` (line 16) and DELETES the pm_flag at 12h (line 83) — overriding
pm_flag.sh's native 36h TTL. The effective pm_flag TTL is therefore 12h when pm_persist.sh is running.
If pm_persist breaks, the pm_flag path stales → this gate falls back to scratch_flag or goes dormant.

**Receipt: model-executed, not mechanically verified** `[honor]`
The hook computes the ADDED lines diff mechanically and issues the block. The pad write itself is
**DELEGATED**: the block instructs the main window to spawn ONE `model: sonnet` sub-agent to append
to the pad, bounded to exactly three verdicts (`WROTE <n> lines` · `NOTHING-TO-CAPTURE` ·
`FAILED <why>`) and forbidden from returning the content; the main window then prints only a ONE-LINE
receipt (`📝 Scratchpad: <verdict>`) and does not reprint the captured lines. The hook has no feedback
loop to verify the sub-agent was spawned, the pad was actually written, or the receipt was actually
printed ("a hook cannot write the reply pane"). The block is mechanically enforced; the delegation and
the receipt are honor-system. ⚠ **This delegated shape is live in BOTH repos** — the element described
the older main-window-writes-the-pad shape after the code had already moved on, so this is
documentation lag corrected, NOT a destination-only improvement.

---

### EVERY STORE (complete list)

| Store | Path | Role | Notes |
|---|---|---|---|
| scratch_flag | `~/.claude/run/scratch/scratch-$KEY.flag` (KEY="sess-$SID" or "cwd-<hash>") | primary pad override (arm path) | 30m TTL from `armed_at`; self-expires on `status` call (scratch_flag.sh line 34); pm_persist.sh refreshes `armed_at` each turn |
| pm_flag | `~/.claude/run/pm/pm-$KEY.flag` (KEY="sess-$SID" or "cwd-<hash>") | secondary pad (brief path) | Native 36h TTL (pm_flag.sh line 17); pm_persist.sh deletes at 12h (pm_persist.sh line 83) — effective TTL is 12h when pm_persist is running |
| bucket watermark | `~/.claude/run/scratch-capture/cap-sess-$SID.state` | last-captured token-bucket index | written on every checkpoint (due or first-sight seeding); (scratch_capture_gate.sh lines 101, 124) |
| pad sidecar | `~/.claude/run/scratch-capture/cap-sess-$SID.pad` | copy of ## SCRATCHPAD at last checkpoint | diff baseline for ADDED lines computation; (scratch_capture_gate.sh line 77) |
| Active brief / scratch pad | Drive path from pm_flag or scratch_path from scratch_flag | the `## SCRATCHPAD` section the model writes to | READ only by this hook; written by the model after the bounce |
| JSONL transcript | `transcript_path` from Stop payload | token-count signal | READ only; gate does not write to it |
| scratch sweep state | `~/.claude/run/sweep/sweep-$KEY.state` | switch-session warning dedup (sibling hook) | written by scratch_sweep_nudge.sh; not used by the gate itself |

---

### INTENT / CURRENT-VS-TARGET

**Why it exists (2026-07-14 failure):** the prior capture mechanism was `scratch_sweep_nudge.sh`
(UserPromptSubmit advisory nudge). A live session showed capture was ignorable and invisible —
a voluntary nudge that could be scrolled past left actual work un-captured. The Stop-gate makes
capture un-ignorable: every turn-end checks the pad, and if it's due, the turn cannot complete
without a visible receipt. The retire-the-nudge's-capture-role decision (F5.4, 2026-07-15) is
documented in `scratch_sweep_nudge.sh`'s own header comment (line 6).

**Design principle — continuous vs session-close:** `/save`'s SC-4 F5.6 is the FINAL DELTA-CAPTURE
step (runs once at session-close, catches anything since the last gate-capture — labeled "HARD, before
any promotion or compaction"). Brief compaction is the separate roll-up that follows F5.6, not part of
it. This gate is the CONTINUOUS arm (fires once per ~100 k-token bucket throughout the session). They
are complementary: the gate populates the pad progressively; F5.6 closes the gap between the last
gate-fire and the end.

**Current → LIVE (with documented gaps):**
The Stop hook is registered, fires on every turn-end, and issues a mechanically-enforced block on due
turns. The 100 k-bucket gate, loop-safety, dormancy guard, and first-sight seeding all work
mechanically. The diff computation (ADDED lines) is Python3 inline — deterministic, not model-guessed.
What is honor-system: the model's receipt content and the actual pad write after the bounce
(a hook cannot write the reply pane). The maturity label is `LIVE·gap` because six documented
fail-open conditions exist (see GAPS).

**TARGET:** no outstanding enforcement targets — the gate is LIVE for its primary mechanism. The
identified gaps are accepted by design (fail-open is the explicit posture for a Stop hook; the
30m scratch_flag TTL is acknowledged as a known limitation; the pm_flag 12h/36h TTL discrepancy
is a known interaction between pm_persist.sh and pm_flag.sh). Future improvement: a PostToolUse
Write observer that verifies the receipt line appeared in the reply would close Gap 1, but no such
hook currently exists. Additionally, no guard hook currently protects this element's own Stop-hook
registration from being removed; `guard_organism_map.sh` (Feature 1.6, built 2026-07-22, registered
in settings.json at line 102 as PreToolUse/Write) protects the map that references it, but the
settings.json registration itself remains unguarded.

---

### INTEROP SEAMS

Every interaction with other organism elements, from this element's perspective:

```
INTEROP:
  COMPLEMENTS   save              · both target the same ## SCRATCHPAD section; gate
                                    captures continuously (~100k-tok bucket); /save SC-4 F5.6
                                    does the final delta-capture at session-close (before compaction,
                                    which is a separate subsequent step) —
                                    not redundant, they interlock (gate populates, F5.6 closes)
  READS         pm-flag           · reads pm_flag.sh status → brief path (secondary pad
                                    resolver; fires when scratch_flag = none or empty PAD)
  READS         scratch-flag      · reads scratch_flag.sh status → armed state + scratch_path
                                    (primary pad override; armed externally, 30m TTL)
  SHARES        project-manager   · the active brief's ## SCRATCHPAD section is this gate's
                                    target pad; pm_persist.sh (project-manager) injects the brief
                                    + flag every turn, refreshing pm_flag for this gate;
                                    pm_flag_recover.py repairs a dropped pm_flag this gate depends on
  COMPLEMENTS   scratch-sweep-nudge
                                  · sibling UserPromptSubmit hook sharing the same transcript
                                    token-counting approach and scratch_flag/pm_flag precondition;
                                    designed as the split partner (F5.4 retired sweep's capture
                                    nudge INTO this gate); sweep is now advisory-only late-session
                                    warning; NOT in ranked element list — new candidate
  KEYS-OFF      hook-plane        · Stop-event registration in settings.json is what arms this
                                    gate at all; deregistering it (or removing the matcher) silently
                                    disables all continuous capture for the session
```

---

## GAPS

Documented fail-open conditions — every case where the gate does NOT fire even though capture
might be warranted:

**Gap 1 — Receipt is model-executed, not mechanically verified.**
The hook computes the ADDED lines diff mechanically and issues the block, forcing the model to
respond. However, the hook has no feedback loop to confirm the model actually printed the receipt
or actually appended to the pad. If the model interprets the bounce incorrectly, responds without
the receipt, or silently skips the pad append, no second block fires. Acknowledged in hook header
line 20: "a hook cannot write the reply pane." This is an accepted trust-in-model gap, not a code gap.
*Blast radius: a single turn's worth of scratchpad work may go un-confirmed (not un-blockable);
the next bucket checkpoint would catch any structural miss in the next 100k tokens.*

**Gap 2 — scratch_flag 30m TTL — silent expiry in long-idle sessions.**
If a session armed `scratch_flag` for an explicit scratch_path (not a project brief via pm_flag)
and then sits idle for more than 30 minutes, `scratch_flag.sh status` self-expires the flag on the
next call (scratch_flag.sh line 34). The gate then falls through to pm_flag for its secondary
resolver, or goes dormant if pm_flag is also unset. A session that deliberately armed scratch_flag
for a custom pad path silently loses that override after 30 minutes of inactivity.
**Mitigation caveat:** `pm_persist.sh` (UserPromptSubmit) calls `_refresh_armed_at` on
`scratch-$KEY.flag` every turn (pm_persist.sh lines 37–50), resetting `armed_at` to the current
epoch second. This means the 30m TTL is continually extended for any active session where
`pm_persist.sh` is also firing — the scratch_flag will NOT expire mid-session as long as the user
is actively sending prompts. The silent expiry risk is real only for sessions that go genuinely idle
(no turns) for >30m, or sessions where `pm_persist.sh` is not running (no pm_flag armed).
*Blast radius: sessions using explicit scratch_flag paths that go idle for >30m without any turn
activity; the project-brief path via pm_flag is unaffected; active sessions with pm_persist running
are substantially protected.*

**Gap 3 — No fallback pad for sessions with neither flag.**
If neither scratch_flag nor pm_flag is armed (no active project, no explicit scratchpad), the gate
exits 0 entirely at the dormancy gate (scratch_capture_gate.sh line 51). Sessions with no active
project tracking — any untracked root-mode session, a desk session that never armed a project flag —
receive zero continuous capture. Work done in those sessions is entirely unguarded by this gate.
*Blast radius: untracked sessions; the user must rely on manual /save or natural-language
"save this" → save_routing_hint.sh routing (which does not block, only redirects).*

**Gap 4 — Token signal requires accessible transcript.**
The token count is read from `transcript_path` in the Stop payload (JSONL file, last assistant usage
block; scratch_capture_gate.sh lines 54–71). If the transcript is absent, unreadable, or has no
assistant usage blocks (e.g. the very first message in a session before any assistant reply), `TOK`
is empty and the gate exits 0 silently (line 72). This is the designed degrade-safe / FAIL_OPEN
posture (hook header line 23). Additionally, `set +e` runs throughout the entire script (line 26),
so any subcommand failure silently continues — every error path is fail-open by design.
*Blast radius: turns where the transcript is temporarily inaccessible (race condition or file
system delay) — the checkpoint is simply skipped; the next due turn will catch it.*

**Gap 5 — pm_flag effective TTL is 12h, not 36h — silent drop after 12h idle.**
`pm_flag.sh` has a native 36h TTL (`TTL_HOURS="${PM_TTL_HOURS:-36}"`, pm_flag.sh line 17), but
`pm_persist.sh` reads the SAME `PM_TTL_HOURS` env var and sets its own default of 12h
(`TTL_HOURS="${PM_TTL_HOURS:-12}"`, pm_persist.sh line 16). pm_persist.sh DELETES the pm_flag
when `NOW - ARMED_AT >= TTL_HOURS * 3600` (pm_persist.sh line 83). Because pm_persist.sh fires
on EVERY UserPromptSubmit, it is the more frequent reader — and it deletes the flag at 12h. Any
session where the pm_flag was armed and then no prompt is sent for 12h (or PM_TTL_HOURS is unset)
will have its pm_flag silently deleted by pm_persist.sh on the next turn. On the next Stop event,
`pm_flag.sh status` returns "none" → gate goes dormant. Sessions using pm_flag as the sole pad
resolver silently lose capture after 12h of inactivity (not 36h as pm_flag.sh's own TTL implies).
*Blast radius: any session armed via pm_flag where the effective 12h window has elapsed since
arming; the scratch_flag path (if armed) is unaffected; the 36h vs 12h discrepancy is a known
interaction between pm_persist.sh and pm_flag.sh that has not been reconciled.*

**Gap 6 — scratch_flag key mismatch: cwd-hash armed sessions silently skipped.**
`scratch_flag.sh` uses `KEY="sess-$CLAUDE_CODE_SESSION_ID"` when the env var is set, else
`KEY="cwd-$(printf '%s' "$PWD" | shasum | cut -c1-12)"` (scratch_flag.sh lines 20–21). If
scratch_flag was armed in a context where `CLAUDE_CODE_SESSION_ID` was UNSET (key = cwd-hash),
the flag lives at `scratch-cwd-<hash>.flag`. When `scratch_capture_gate.sh` later calls
`scratch_flag.sh status` with `CLAUDE_CODE_SESSION_ID="$SID"` set (line 43), scratch_flag.sh
routes to `scratch-sess-$SID.flag` (different file), finds it absent, and returns "none". The
gate then falls through to pm_flag. However, even if scratch_flag.sh returned "armed" (the
reverse case where the cwd-hash happens to match), the gate at line 45 hardcodes
`FLAG="$HOME/.claude/run/scratch/scratch-sess-$SID.flag"` — always the session-keyed path —
so the cwd-hash flag's `scratch_path` is never read. Concretely: any session where scratch_flag
was armed without `CLAUDE_CODE_SESSION_ID` in the environment silently uses pm_flag as fallback,
or goes dormant. The cwd-hash-armed scratch_path override is not honored by this gate.
*Blast radius: sessions that armed scratch_flag via the cwd-hash fallback (no SID env set at arm
time) — a rare case since Claude Code normally sets `CLAUDE_CODE_SESSION_ID`; the default project-
brief path via pm_flag is unaffected.*

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)

- **maturity_label:** LIVE·gap
- **check_detail:** "pending label_checker.py"
