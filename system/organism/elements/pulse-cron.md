---
topic: [system-architecture]
element: pulse-cron
title: "pulse-cron — element detail (ground/base altitude)"
subsystem: automation
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C4 silent-death — rc=2 (and rc=75 stand-down) excluded from the failure streak; breaker state is /tmp-ephemeral so reboot re-arms a broken job, but reboot is no longer the only reset path — a trip is held on a doubling backoff (1h → cap 24h) and re-probes half-open on its own clock"
generated_from:
  - system/tools/pulse.sh
  - system/pulse-config.md
  - system/tools/install-schedulers.sh
  - system/tools/ingest-run.lib.sh
  - system/tools/primary-gate.sh   # ⚠ CORRECTED 2026-08-24: this file does not exist anywhere in the repo (find: 0 matches). Neither does the require_primary() function it is cited for below — verified by grep repo-wide: no definition, no call site, only comments recording it was DROPPED. See the correction banner before "GATES AND ACTUAL ENFORCEMENT MECHANISMS" below.
  - system/tools/archivist-run.lib.sh
  - system/tools/marc-research-lib.sh   # ⚠ CORRECTED 2026-08-24: this file does not exist (find: 0 matches). The "D. Marc pipeline runners" section below and its _lead_gate() citations describe donor code that was never ported. See the same correction banner.
  - system/tools/system-health-run.sh
  - system/tools/health-deadman-check.sh
  - system/tools/lifehack-lead.sh
  - system/schemas/runner-standard.md
  - system/reference/settings.json (hook-plane audit)
  - system/pulse-config.md (```jobs + ```crontab + ```launchd blocks)
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# pulse-cron — element detail

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the Pulse background dispatch
> engine — every trigger, every mode, every step in the dispatch loop and runner contract, every store
> touched, every gate and its honest enforcement, and every interop seam.
> The MIDDLE manual (`system/organism/manual.md`) carries only a one-line pointer here; the TIP
> (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **LADDER: ELEMENT (full mechanics). up → manual#pulse-cron ; ground truth → system/tools/pulse.sh + system/pulse-config.md**
>
> **One-line:** one OS-scheduler entry — a `crontab` line on Mac/Linux, a Windows Task Scheduler task
> on Windows — ticks `pulse.sh` every 5 minutes; it reads the `jobs` block in
> `pulse-config.md` and fires any job whose interval has elapsed, with machine-local circuit-breaker
> safety, single-writer machine-gating, and a Drive-mirrored heartbeat feed.
>
> *Step grammar: `actor → port/tool → store → gate`*
> *Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) · `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause)*

> **CITATIONS — what the paths below resolve to here.** The body describes the donor's scheduler plane truthfully; the four lines below record what happened to each named file at THIS destination, and they cover every mention of them in the body.
>
> ⛔ the launchd block in `system/pulse-config.md` — never ships (the file itself is here; the block inside it is not). The dispatcher and its jobs + crontab blocks DID land (verified), but the donor's third block did not, by explicit ruling recorded in the installer's own header (system/tools/install-schedulers.sh lines 71-76): *"⛔ NOT PORTED, ON PURPOSE: the donor's launchd block (bootstrap/Supabase plists)."* The out-of-band health-deadman watcher is a dedicated crontab row here, not a plist.
>
> ⛔ `system/tools/marc-deadman.py` — excluded from the migration — desks. Belongs to the closed-list personal desk marc-desk; its runner and heartbeat do not ship, so every Marc row in the job tables below is donor description, not a promise.
> ⛔ `.claude/skills/cal-weekly/` — same reason: excluded, personal desk (cal-pipeline).
> ⛔ the skill `/cal-weekly` — same reason: excluded, personal desk (cal-pipeline). The general-purpose replacement for the weekly review is .claude/skills/planning-weekly/.
>
> ⛔ `state/status/sentinel.json` — runtime-generated, created on first run, never committed. A status tile the reader's own run writes under their notes/data root (shared/gate/sentinel_response.py line 53 resolves it as `{DATA}/state/status/sentinel.json`); its writers system/tools/sentinel-health.py and system/tools/sentinel-health-run.sh DO ship.
> ⛔ `state/status/*.json` — every other tile of this shape named below is the same class: runtime-generated, created on first run, never committed.
>
> ✅ landed — `system/schemas/runner-standard.md`, the codified `*-run.sh` contract, is now present in `system/schemas/` (21,251 bytes, confirmed 2026-08-24). The line above previously deferred it; that deferral is now stale.
> `system/tools/planning-health.py` line 23 reasons against "the runner-standard rc=1", and the contract it cites now exists.

> ⚖ **NOTE 2026-08-15 — the `…_studio_…` gate names below are DONOR CODE IDENTIFIERS, and are
> deliberately NOT renamed.** `require_studio_hardware` and `ingest_studio_gate` (the latter being
> only a back-compat alias for `require_primary`) named one of the donor's own machines, from an era
> before that gate was renamed to a role. **None of the three functions exists in this repo** —
> verified by grep: they appear here only inside this document and inside port notes recording that
> they were dropped, and the donor files that defined them (the standalone primary-gate script, the
> lead-machine script) were never ported either. So the whole GATES section below is donor
> description, not this system's behaviour — consistent with the CITATIONS note above.
> Under the no-named-machines ruling the *prose* around them has been rewritten to roles ("the
> primary machine" / "the second machine" / "the hardware host"); the identifiers themselves stay
> verbatim because renaming a function that lives in another repo would falsify the record rather
> than fix it. Nothing here names a machine this system runs on.

---

## AUTHORED   (human-only)

### TRIGGER / MODE

Four operating modes compose the full pulse-cron plane. Modes 1–3 are triggers; Mode 4 is invocation-time.

**Mode 1 — Pulse interval dispatcher (`pulse.sh run`, default):**
A single OS-scheduler entry fires every 5 minutes. The scheduler plane has **TWO real backends**, and
the dispatcher is byte-identical on both — only the ENTRY POINT differs. `install-schedulers.sh`
branches once on `uname -s` (`Darwin` → mac · `Linux` → linux · **anything else → windows**, which
deliberately covers MSYS/MINGW/CYGWIN Git Bash *and* a bare `uname` failure), then installs:

- **Backend 1 — Mac / Linux: `crontab`** (the `crontab` fenced block in `system/pulse-config.md`):
```
*/5 * * * *  PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin \
  PULSE_CONFIG="$HOME/lifehack-brain/system/pulse-config.md" \
  bash "$HOME/lifehack-brain/system/tools/pulse.sh" >> /tmp/pulse.log 2>&1
```
  One owned marked region in `crontab -l`, rewritten idempotently on every re-install (the marked-region
  approach is why cron beat launchd here: N per-job `.plist` files plus `launchctl load`/`unload` state
  have no equally clean idempotent diff).

- **Backend 2 — Windows: Task Scheduler via `schtasks.exe`**, driven through Git Bash. Task Scheduler
  cannot run a POSIX script, so the installer resolves Git Bash's `bash.exe` (PATH first, then the two
  standard Git-for-Windows install locations) and converts BOTH that binary and `pulse.sh`'s own path
  with `cygpath -w`; it exits FATAL rather than registering a task it knows cannot fire. Tasks are named
  `Lifehack-<job>`. Schedules are translated by `_cron_to_schtasks`, a **deliberately small** cron→
  `schtasks` translator that understands exactly the two shapes this manifest actually uses —
  `*/N * * * *` (every N minutes) and `M * * * *` (hourly at minute M) — and **REFUSES anything else
  rather than guessing a wrong schedule**, printing a SKIP naming the job and telling the human to add
  that one by hand. ⚠ Consequence for Mode 3 below: the three wall-clock `planning-diary` shapes
  (`0 17 * * 5` · `0 8 1 * *` · `0 8 1 1,4,7,10 *`) are NOT among the two translatable shapes, so on
  Windows they are skipped with a warning, not silently mis-scheduled.

Installed by `install-schedulers.sh` (idempotent; re-runs after `git pull`) on EVERY machine.
The `PULSE_CONFIG` path is baked into the scheduled entry and points to the git-tracked clone copy —
the stale Drive copy is NEVER read. In run mode `pulse.sh` dispatches every job whose elapsed time
meets or exceeds its registered interval and mirrors the machine-local state to Drive after the cycle.
ADR-007 names `pulse-config.md` as the single scheduling truth-surface; `pulse-config.md` itself
documents the same split (crontab on Mac/Linux, Task Scheduler on Windows) and special-cases the
`pulse` row.

⚠ **Registration is not execution.** A scheduler entry that registers cleanly and is then silently
denied at FIRE time looks identical to a healthy install if the only check is "is the entry there."
The proof this design leans on is downstream of the scheduler entirely: each job's OWN status tile
(written by that job's real work, not by the installer) plus `health-deadman-check.sh` watching that
tile go stale. The residual gap is named, not hidden — nothing independently watches the watcher's
own scheduled entry.

**Mode 2 — Pulse status / dry-read (`pulse.sh --status`):**
`bash pulse.sh --status` — reads the `jobs` block and prints DUE / waiting / AUTO-DISABLED per job.
No jobs are executed; no state is written; the Drive heartbeat mirror is skipped.
Used for diagnostics without triggering actual runs.

**Mode 3 — Clock-pinned crontab entries (NOT Pulse-dispatched; bypass `pulse.sh` entirely):**
Three `planning-diary-run.sh` variants are installed by `install-schedulers.sh` from the `crontab` fenced
block in `system/pulse-config.md`:
- `0 17 * * 5` → `planning-diary-run.sh --cadence weekly` (every Friday 17:00)
- `0 8 1 * *` → `planning-diary-run.sh --cadence monthly` (1st of month 08:00)
- `0 8 1 1,4,7,10 *` → `planning-diary-run.sh --cadence quarterly` (1st Jan/Apr/Jul/Oct 08:00)

These are wall-clock-pinned (Pulse is interval-only and cannot pin a wall-clock time). They silently
miss when the primary machine is asleep at the scheduled time — see GAPS §4.

**Mode 4 — Sandbox / test run (env-override):**
`PULSE_CONFIG=<alt-config> PULSE_STATE=<alt-state> bash pulse.sh` — all state reads and writes go
to the overridden paths (`pulse.sh:18–19`). The Drive heartbeat mirror is SKIPPED when `PULSE_STATE`
differs from the default `/tmp/lifehack-pulse-state.json` (`pulse.sh:223`) so a sandbox run never
clobbers the real mirror.

**Scheduling manifest single source of truth:** `system/pulse-config.md` (CODE tier, git-tracked).
Contains three fenced blocks: ` ```jobs ``` ` (Pulse interval dispatch manifest), ` ```crontab ``` `
(wall-clock lines `install-schedulers.sh` installs), ` ```launchd ``` ` (four launchd plists:
`ai.lifehack.bootstrap` (machine: all, every 1800s, runs `run-bootstrap.sh`);
`com.<operator>.supabase-keepalive` + `com.<operator>.supabase-backup` (both machine: all — NOT pinned
to one machine; still active via launchd, NOT yet migrated to Pulse);
`ai.lifehack.health-deadman` (machine: one designated machine only)).

---

### FULL HAND-OFF CHAIN

#### A. Pulse dispatcher loop (`pulse.sh` — Mode 1)

```
cron daemon (OS, */5 * * * *)
  → bash pulse.sh run   [CODE: $HOME/lifehack-brain/system/tools/pulse.sh]
    → [PREFLIGHT — lead-machine nag]  (pulse.sh:123–131)
        reads $DRIVE/state/primary-machine
        if unset → log CRITICAL nag + notify-send.sh (once per hour, governor-deduped)
        DOES NOT EXIT — loop continues; non-gated infra jobs still run on both machines
    → reads system/pulse-config.md   ```jobs block   [store: job schedule manifest]
    → reads /tmp/lifehack-pulse-state.json           [store: machine-local last-run + breaker state]
    → FOR EACH JOB in manifest:
        if durably parked (retry_at for {name} in state/pulse-parked-jobs.json > NOW) → log PARKED + skip
          (read DIRECTLY from the park file, never from STATE — so a human's deliberate park survives a
           /tmp wipe; checked BEFORE the breaker, and never confused with a breaker trip)
        if disabled:{name}=1 in STATE:  [pulse.sh:205–223]
            retry_at:{name} <= 0 → log PARKED, will NOT auto-retry (a pre-backoff trip or a deliberate
              park — treating a missing timer as 0 would resurrect it on the very next tick)
            NOW < retry_at:{name}  → log BACKOFF + skip (the line names the minutes until the re-probe)
            otherwise             → HALF-OPEN: clear disabled:{name} and let this ONE run decide
        if (NOW - last_run) < interval → continue (not due)
        → dispatch: `bash -c "$cmd" </dev/null`                  (external runner)
                    OR `eval run_builtin "$@" </dev/null`         (@trim_md_days / @find_delete builtins)
          rc = $?
        → set_last({name}, NOW) → STATE   [UNCONDITIONAL — pulse.sh:187, before rc branches]
          (a failed job STILL advances its last_run; it retries after its FULL interval, not the
           next 5-min Pulse tick — prevents hot-loop retry on a broken job)
        → if rc=0: set_state fails:{name} 0 → STATE  (reset streak)  [pulse.sh:190]
              ALSO clears disabled:{name}, trips:{name} and retry_at:{name} — a half-open probe that
              passes fully re-arms the job AND forgets its backoff history (next hold restarts at BASE)
        → if rc=75 (STOOD DOWN — dispatched, then declined by its OWN preflight):  [pulse.sh:262–276]
              counted as `skipped` — NEVER as `ran`, NEVER as `failed`
              breaker untouched: no streak increment, no reset
              (a job that stands down every tick — e.g. one needing credentials nobody has configured
               yet — would otherwise trip the 3-strike breaker within 15 minutes of a clean install,
               while counting it as `ran` would hide a standing-down job behind a healthy number)
        → if rc=2 (TRANSIENT — gws preflight, lock contention):  [pulse.sh:191–199]
              streak NOT incremented (never trips breaker)
              comment documents the 2026-06-13 and 2026-06-17 emily-breakdown false-disable incidents
        → if rc≠0 and rc≠2 and rc≠75:
              set_state fails:{name} (streak++) → STATE
              if streak >= MAX_FAILURES (3):  [pulse.sh:24; env-overridable PULSE_MAX_FAILURES]
                set_state trips:{name} (trips++) → STATE
                hold = BACKOFF_BASE doubled once per prior trip, capped at BACKOFF_MAX
                set_state disabled:{name} 1 · retry_at:{name} (NOW + hold) · fails:{name} 0 → STATE
                notify-send.sh critical buzz (circuit-breaker trip, naming the hold length)
    → [HEARTBEAT MIRROR — after run cycle, run-mode only (MODE != --status), default STATE path only]
        python3 inline → reads /tmp/lifehack-pulse-state.json  [pulse.sh:225–255]
        → atomic write (.tmp → os.replace):
            $DRIVE/state/status/_pulse-{machine}.json   [store: Drive, machine-namespaced, canonical]
            $DRIVE/state/status/_pulse.json                 [store: Drive, legacy back-compat for Helm transition]
```

**`@` builtins — dispatch verbs (case branches) inside `run_builtin()` in `pulse.sh`, not separate inline shell functions (`pulse.sh:72–106`; `run_builtin()` is the actual shell function; `@trim_md_days` and `@find_delete` are case patterns within its `case` statement at lines 78–101):**
- `@trim_md_days` — trims `## YYYY-MM-DD` sections older than N days from a Markdown file.
  Used by: `learnings-trim` (90d, `$DRIVE/system/learnings.md`), `machinelog-trim` (30d — REGISTERED
  `no`, permanently disabled: pipe-delimited format, no `## YYYY-MM-DD` header sections; re-enable only
  after adding a matching trim builtin for line-date-based formats).
- `@find_delete` — `find {dir} -name "*.jsonl" -mtime +{n} -delete`.
  Used by: `observability-trim` (`$DRIVE/system/observability/*.jsonl`, mtime +30d).

#### B. Standard runner contract (all `*-run.sh` files that invoke `claude -p`)

Every runner that dispatches `claude -p` follows the same typed step sequence (codified in
`system/schemas/runner-standard.md` as the runner-standard contract):

```
pulse.sh → bash {job}-run.sh </dev/null   [CODE: system/tools/{job}-run.sh]
  → ~~[GATE 1 — MACHINE GATE]
      source primary-gate.sh; require_primary || exit 0
      OR source ingest-run.lib.sh; require_primary "$JOB"
        (NOTE: callers of ingest-run.lib.sh:require_primary do NOT add `|| exit 0` —
         the function calls exit 0 internally; adding it is the primary-gate.sh calling convention only)
      OR inline copy (archivist-run.lib.sh → return 0; planning-diary/vault/weekly-analyze/
                       planning-vault-weekly/email-summary-write/item-store-freshness → exit 0)
      OR _lead_gate in marc-research-lib.sh:41 (same logic, different function name)
      Mechanism in ALL cases:
        /usr/sbin/scutil --get ComputerName → mapped to THIS machine's short token
        compare to tr -d '[:space:]' < $DRIVE/state/primary-machine
        NON-LEAD → clean exit 0 or return 0 (deliberate stand-down; NOT counted as a breaker failure)
        UNSET marker → behavior is IMPLEMENTATION-SPECIFIC:
          ingest-run.lib.sh:require_primary (lines 71-74): critical notify-send + exit 0
          primary-gate.sh:require_primary (lines 44-47): plain echo + return 1, NO notify-send, NO exit
          archivist-run.lib.sh inline gate: return 0, NO notify-send
          (fail-CLOSED for Drive writes — no writer runs without a designated lead — but the notify channel varies)
  → [GATE 2 — HARDWARE GATE, dobby/emporia only]
      require_studio_hardware (ingest-run.lib.sh:89–94):
        case $ComputerName in *<hardware-host>*) ;; *) exit 0 ;; esac
        Hard pin — not lead-selectable; the hardware is physically absent on every other machine.~~
  → ⚠ CORRECTED 2026-08-24: GATE 1 and GATE 2 as printed above DO NOT EXIST in this repo. Verified
      this session by grep of the whole tree: `primary-gate.sh` — 0 files; `require_primary()` — 0
      DEFINITIONS anywhere (the string appears only in comments recording it was dropped);
      `marc-research-lib.sh` — 0 files; `require_studio_hardware` — 0 definitions, same treatment.
      `system/tools/ingest-run.lib.sh`'s own header states this explicitly: "None of the three
      functions exists in this repo — verified by grep: no definition and no call site anywhere, in
      any language." The reason is architectural, not a missing port: this system has ONE machine
      ("there is one machine. The two-machine plane is not part of this system." —
      `docs/data-layout.md:215`), so a lead-machine election gate has nothing to elect between.
      `system-health-run.sh` (grepped directly this session) calls neither `require_primary` nor
      anything primary-machine-related — Drive-writing jobs run unconditionally. Correctly stated
      elsewhere in this same repo: `elements/archivist.md:71–72` ("There is no machine gate on the
      run... DROPPED, not translated"), `elements/backlog-authority.md:203–205` ("no machine gate,
      no require_primary, and no state/primary-machine marker"). See also the parallel correction at
      GATES AND ACTUAL ENFORCEMENT MECHANISMS §1 below, which this whole GATE 1/2 block, the D. Marc
      pipeline runners section, and the GAPS §1 dedup note all inherit.
  → [GATE 3 — SENTINEL PAUSE, ingest runners only]
      ingest_check_paused (ingest-run.lib.sh:103–109):
        reads ~/.config/lifehack/sentinel-paused-sources
        if source key present → exit 0; un-pause is HUMAN-ONLY (never auto-resume)
  → [AUTH LOAD]
      ingest_load_auth (or ingest_load_gws + ingest_load_claude separately):
        export CLAUDE_CODE_OAUTH_TOKEN from ~/.config/lifehack/claude-oauth-token
        export GOOGLE_WORKSPACE_CLI_* → ~/.config/gws-cron/ + ~/.config/lifehack/gws-credentials.json
  → [GWS PREFLIGHT, 3× retry with 4s sleep]  (ingest-run.lib.sh:143–152)
      if fail after 3 attempts → exit 2 (TRANSIENT; breaker does NOT count this)
  → [GATE 4 — SINGLE-INSTANCE LOCK]
      ingest_acquire_lock (ingest-run.lib.sh:164–173): mkdir /tmp/lifehack-{job}.lock (atomic mkdir)
      if lock exists and mtime < 1500s → exit 0 (not a failure; not counted)
        [ingest-run.lib.sh:167 uses FIXED 1500s (25 minutes), NOT watchdog-relative — confirmed live]
      stale-steal after 1500s (stale lock dir removed + re-created)
      NOTE: archivist-run.lib.sh uses ARCH_WATCHDOG+300 (= 2100s for the default 1800s watchdog) —
        a DIFFERENT implementation-specific value; only archivist runners use this variant
  → [GATE 5 — NEW-MAIL GATE, email ingest runners only]
      ingest_new_mail_gate (ingest-run.lib.sh:187–213)
        (INLINE — must NOT be called via $(...); calls exit to abort the runner, not a subshell)
        reads ~/.config/lifehack/{job}-last-seen [store: high-water epoch marker]
        if no marker → seed to NOW, exit 0 (avalanche-prevention for first run)
        gws label count query → if 0 new messages → cheap exit 0 (no claude spawn, no tokens burned)
        on new mail → sets INGEST_CUTOFF + INGEST_MARKER_CANDIDATE globals
  → [CLAUDE INVOCATION]
      ingest_run_claude (ingest-run.lib.sh:279–289) or direct claude call:
        claude -p "$PROMPT" --model {MODEL} --dangerously-skip-permissions
        working dir = DESK_DIR or CODE_ROOT/desks/{desk}/
        + WATCHDOG: ( sleep $WATCHDOG; kill -9 $cpid ) & (background subshell; hard-kills a hung session)
        watchdog durations: archivist 1800s (LIVE — confirmed this session: `ARCH_WATCHDOG` default 1800
          at `system/tools/archivist-run.lib.sh:32`, the same file dispatching `sleep "$ARCH_WATCHDOG"` at
          line 160; `archivist-audit`/`archivist-deepmine` are `yes`-enabled, non-`waiting-on-port` rows in
          `system/pulse-config.md`) ·
        ~~emily 1200s (hardcoded) · clair 1200s (env-overridable ${WATCHDOG:-1200}) · deryl 1800s
          (env-overridable ${DERYL_INGEST_WATCHDOG:-1800}) · NOTE: no single canonical "ingest runner
          default" — watchdog is caller-supplied and varies per runner ·
          marc per-researcher 480s (RWATCH) + synthesis 900s (WATCHDOG) ·
          marc-wednesday material-scan 300s · marc narrative-emit 180s~~
        **⚠ CORRECTED 2026-09-01 (#61).** The five struck durations above (emily / clair / deryl /
        marc-weekly / marc-wednesday / marc narrative-emit) describe runners that do not run in this
        install. Confirmed this session two ways: (1) `system/pulse-config.md` lists every one of
        `emily-breakdown`, `deryl-ingest`, `deryl-books-health`, `clair-health`, `clair-billing`,
        `marc-health`, `marc-weekly`, `marc-wednesday`, `marc-deadman` as `waiting-on-port` /
        "NOT PORTED — see comment above"; (2) a repo-wide filename search this session for
        `emily-breakdown-run.sh`, `clair-health-run.sh`, `deryl-ingest-run.sh`, `marc-research-lib.sh`,
        `marc-weekly-run.sh`, `marc-wednesday-run.sh`, and `marc-deadman.py` returned zero files —
        the source scripts these numbers describe are not present here at all. These durations are
        **donor-derived**: illustrative internals carried over from the donor system's code for a
        pipeline that has not been ported, not a measurement of anything executing in this repo.
        Source of the exact figures (1200s / 1800s / 480s / 900s / 300s / 180s) as originally written
        into this file is unverified — no port commit or citation ties them to a script that exists
        here, so their provenance beyond "donor code" is UNKNOWN, not asserted. Only `archivist`,
        left unstruck above, is confirmed live.
  → [EMIT STATUS]
      emit_status.py (or python3 inline) → atomic write $DRIVE/state/status/{desk}.json
      notify-send.sh on threshold breach (all alert routing goes through notify-plane)
  → [FINISH]
      ingest_finish (ingest-run.lib.sh:294–303) [ingest runners]:
        on rc=0 → advance ~/.config/lifehack/{job}-last-seen
      archivist: _upload_queue → gws drive files update/create → Drive review folder
                 _write_tile → $DRIVE/state/status/archivist.json (python3 atomic)
                 arch_postrun (deepmine) → stamp $DRIVE/state/archivist/deepmine-ledger.json
```

#### C. Archivist runner chain (variant — `archivist-run.lib.sh:run_archivist()`)

```
{archivist-audit|deepmine}-run.sh → source archivist-run.lib.sh → run_archivist()
  → step 1: inline lead gate (return 0 on stand-down — NOTE: return, NOT exit, inside the function;
             semantically different if called from a subshell — see GAPS §1)
  → headless auth (CLAUDE_CODE_OAUTH_TOKEN + gws isolated creds)
  → lock: mkdir /tmp/lifehack-{ARCH_LABEL}.lock + trap EXIT rm -rf
           stale-steal after ARCH_WATCHDOG+300 (= 2100s for default 1800s watchdog)
  → arch_prerun hook (deepmine only: reads $DRIVE/state/archivist/deepmine-ledger.json → picks most-overdue desk)
  → claude -p "$ARCH_PROMPT" --model $ARCH_MODEL --dangerously-skip-permissions + watchdog kill (1800s)
  → on success: _upload_queue → gws drive files update/create → $DRIVE (ARCH_REVIEW_FOLDER_ID)
                id cached in ~/.config/lifehack/archivist-{mode}-file-id
  → _write_tile → $DRIVE/state/status/archivist.json (python3 atomic read-modify-write)
  → _ping (notify-send.sh) if drift found
  → arch_postrun (deepmine only): stamp $DRIVE/state/archivist/deepmine-ledger.json
```

#### D. Marc pipeline runners (`marc-research-lib.sh`)

~~##### D1. marc-weekly (`marc-weekly-run.sh` → `marc_research_run`)

```
marc-weekly-run.sh → source marc-research-lib.sh → _lead_gate || exit 0  [marc-research-lib.sh:41]
  → own cadence guard: ISO week / weekend (Sat/Sun) check in shell
    (NOT a wall-clock cron pin; Pulse ticks daily and the runner checks the day)
  → lock /tmp/lifehack-marc-weekly.lock
  → Stage 0: marc-grade.py (grades due projections — pure code, non-fatal)
  → Stage 1 — 8-researcher fan-out: for each of 8 lenses (fed-liquidity · fiscal-currency ·
      valuation-risk · secular-growth · geopolitics · flows-positioning · credit-shadow ·
      market-structure): claude -p "$researcher_prompt" --model sonnet & RPID=$! then
      immediately wait "$RPID" with its own 480s watchdog (sequential, one at a time, 8 serially;
      per-researcher watchdog 480s)  [marc-research-lib.sh:77–89]
  → deterministic gather-gate: marc-gather-gate.py (hard-stop if < floor or stale price feed)
      [marc-research-lib.sh:191–195]
  → price trajectory read: marc-series-read.py  [marc-research-lib.sh:199]
  → Stage 2 — synthesis: claude -p (single call, sequential) + synthesis watchdog 900s (one retry
      after 30s if no wrap text)  [marc-research-lib.sh:203–214]
  → Stage 3 — journal row: bash append to $DRIVE/system/journal.md (one LOW-confidence row)
      [marc-research-lib.sh:217–221]
  → heartbeat stamp: $DRIVE/desks/marc/organism/heartbeat/last-run.json  [marc-research-lib.sh:223]
  → narrative-status emit (additive, NON-FATAL): marc_narrative_emit()  [marc-research-lib.sh:150–166]
      LLM call — reads tracked narratives via marc-narrative-check.py --list,
      proposes {id, state, reason} pairs, routes each through marc-narrative-writer.py --propose
      for validation + write. Own 180s watchdog. Log: /tmp/${SUBSYSTEM_NAME}-narr-emit.log
  → narrative registry health check (additive, NON-FATAL): pure-code validation step
      marc-narrative-check.py --all --dormant-days 21  [marc-research-lib.sh:234–239]
      Validates the tracked-story registry + flags malformed or dormant-by-age narratives.
      Log: /tmp/${SUBSYSTEM_NAME}-narr-check.log (separate from narr-emit.log above)
      Never blocks the market read; non-zero exit = warning in log only
  → emit status tile $DRIVE/state/status/marc-weekly.json  [marc-research-lib.sh:242–251]
```

##### D2. marc-wednesday (`marc-wednesday-run.sh` → `marc_material_change_scan`)

```
marc-wednesday-run.sh → source marc-research-lib.sh → _lead_gate || exit 0
  → own cadence guard: ISO week / Wed (Thu/Fri catch-up) check in shell
  → lock /tmp/lifehack-marc-wednesday.lock
  → marc_material_change_scan: ONE LLM judgment call — reads standing lens current.md +
      live snapshot levels; asks Marc "did anything shift MATERIALLY since the weekend?"
      Single claude -p call + 300s watchdog (NOT the 8-researcher fan-out)
      [marc-research-lib.sh:261–296]
  → journal row always appended to $DRIVE/system/journal.md
  → notify-send ONLY on a MATERIAL verdict (QUIET verdict = journal row only, no buzz)
  → heartbeat stamp: $DRIVE/desks/marc/organism/heartbeat/last-run.json
  → emit status tile $DRIVE/state/status/marc-wednesday.json
```

NOTE: marc-wednesday does NOT call marc_narrative_emit or the narrative registry health check —
those are only in the full marc_research_run (D1). The mid-week scan is intentionally lighter.~~

**⚠ CORRECTED 2026-09-01 (#61).** The entire D1/D2 block above describes donor code that was never
ported. Confirmed this session two ways: (1) `system/pulse-config.md`'s `` ```jobs ``` `` fence lists
both `marc-weekly` and `marc-wednesday` as `waiting-on-port` / "NOT PORTED — see comment above";
(2) a repo-wide filename search this session for `marc-weekly-run.sh`, `marc-wednesday-run.sh`, and
`marc-research-lib.sh` returned zero files (`find . -name "<name>"`, each empty). This is the same
donor-relic pattern the 2026-08-24 citations banner already recorded for `marc-research-lib.sh` at
this file's own header — this D section is the detail that citations banner pointed at but did not
itself strike. Every internal (watchdog duration, lock name, stage sequence, `_lead_gate` call) is
donor description, not this system's behaviour.

#### E. marc-deadman (`system/tools/marc-deadman.py`)

~~```
marc-deadman-run.sh → python3 marc-deadman.py
  → reads $DRIVE/desks/marc/organism/heartbeat/last-run.json   [store: heartbeat set by marc runners]
  → NO lead gate — intentionally runs on EVERY machine (cross-machine dead-man switch;
     both machines must independently catch a dark lead)
  → if >28h stale → notify-send.sh critical (1h dedup via governor collapses double-buzz)
```~~

**⚠ CORRECTED 2026-09-01 (#61).** `system/tools/marc-deadman.py` does not exist in this repo —
confirmed this session by `find . -name "marc-deadman.py"` (zero hits). `system/pulse-config.md`'s
`` ```jobs ``` `` fence lists `marc-deadman` as `waiting-on-port` / "NOT PORTED — see comment above".
The dead-man mechanism described above (cross-machine no-lead-gate design, the 28h staleness read,
the 1h notify dedup) is donor description, same class as Section D above — nothing in this repo
watches a Marc heartbeat today.

#### F. Health/freshness runners (non-gated group)

```
{system-health|email-summary-freshness|item-store-freshness|sentinel-health|
 backlog-health|planning-health|~~clair-health|marc-health|deryl-books-health~~}-run.sh
  → require_primary OR ingest_studio_gate   [same gate as B above]
  → python3 *.py OR emit_status.py
  → writes $DRIVE/state/status/{name}.json (atomic .tmp → os.replace)
  → notify-send.sh on threshold breach
```

**⚠ CORRECTED 2026-09-01 (#61).** This group was one undifferentiated roster; it is actually two.
`system-health`, `email-summary-freshness`, `item-store-freshness`, `sentinel-health`, `backlog-health`,
and `planning-health` are confirmed live: each is `enabled: yes` in `system/pulse-config.md`'s
`` ```jobs ``` `` fence and its runner file exists on disk (`system-health-run.sh`,
`email-summary-freshness-run.sh`, `item-store-freshness-run.sh`, `sentinel-health-run.sh`,
`backlog-health.py`, `planning-health-run.sh` — all found this session). The three struck above —
`clair-health`, `marc-health`, `deryl-books-health` — are `waiting-on-port` / "NOT PORTED" in the same
fence, and a repo-wide filename search this session for `clair-health-run.sh`, `marc-health-run.sh`,
and `deryl-books-health-run.sh` returned zero files. The dispatch chain drawn above (gate → python3/
emit_status.py → status tile → notify-send) is real for the six live runners; for the three struck
names it describes donor code that has not been built here.

#### G. Non-gated infra runners (run on EVERY machine independently)

`bootstrap-sync · git-autopush · git-autopull · obsidian-reindex · hook-doc-lint · security-posture-scan · learnings-trim · observability-trim · helm-keepalive`
[NOTE 2026-08-27, lb2-ops-comms.md claim 38 — `git-autopush`/`git-autopull` are listed in `pulse-config.md`
as `waiting-on-port` / "NOT PORTED"; `git-autopull.sh` does not exist on disk at all. This row names the
target job roster, not all of which is built yet.]

These have NO machine gate and write only machine-local paths or the shared clone (git) — no risk of Drive write conflicts from two machines running simultaneously. Exception nuance: `helm-keepalive` is ungated and hits `localhost:8080` — safe only because scope is machine-local.

#### H. Hardware-pinned runners (one designated machine only)

~~`dobby-health · emporia` — `require_studio_hardware` (`ingest-run.lib.sh:89–94`; case on the hardware host's `ComputerName`) exits 0 everywhere else. The relevant hardware is physically absent on every other machine; this is a permanent hard pin, NOT a lead-selectable gate.~~
**⚠ CORRECTED 2026-09-01 (#61).** `require_studio_hardware` is not live — `system/tools/ingest-run.lib.sh`'s own header (lines ~12–14, quoted above at this file's line 64) lists it as one of three functions explicitly DROPPED and never ported, with "None of the three functions exists in this repo — verified by grep: no definition and no call site anywhere, in any language." Re-verified this session: `grep -rn "require_studio_hardware" system/` (excluding this doc) finds it only inside that same drop-note. And `ingest-run.lib.sh:89–94` — read directly this session — is not this function at all; those lines are the `CLAUDE_BIN` resolution block (`CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude ...)}"` through the fallback loop over `~/.local/bin/claude` / `/opt/homebrew/bin/claude` / `/usr/local/bin/claude`), unrelated to any hardware pin. Whatever machine-pinning `dobby-health`/`emporia` actually rely on (if any) is unverified here — this section only disproves the cited mechanism, it does not establish a replacement.

---

### STORES (exact paths)

| Store | Tier | Written by | Read by | Notes |
|---|---|---|---|---|
| `/tmp/lifehack-pulse-state.json` | ephemeral (machine-local) | `pulse.sh` python3 inline | `pulse.sh` get_last/get_state | Per-job `last_epoch · fails:{n} · disabled:{n}` dict. Lost on `/tmp` wipe (reboot) — correct for BREAKER auto-trips (self-heals; T18.5, 2026-08-04). |
| `$DRIVE/state/pulse-parked-jobs.json` | Drive-synced content | `pulse-park.sh` (human-run) | `pulse.sh` `get_park_retry` (dispatch gate, checked before the breaker) · `fault_proposer.py` `parked_jobs()` | The DELIBERATE-park marker, split out from the row above (T18.5, 2026-08-04) because it is a HUMAN DECISION, not breaker state — `/tmp` losing it on reboot was the bug (git-autopush.md §circuit breaker). `{job: retry_at}`; absence reads as "nothing parked." |
| `system/pulse-config.md` | CODE (git-tracked) | human / git push | `pulse.sh` (reads `jobs` block each tick) · `system-health.py` (parses intervals) · `install-schedulers.sh` | Single scheduling truth-surface (ADR-007). Clone copy is canonical; Drive copy is LEGACY. |
| `$DRIVE/state/primary-machine` | Drive-synced content | `lifehack-lead.sh` (human-run) | `pulse.sh` preflight · `require_primary` in EVERY writer runner | Text marker: the short machine token of the designated primary. Absence → fail-CLOSED for writers; pulse loop continues. |
| `$DRIVE/state/status/_pulse-{machine}.json` | Drive-synced content | `pulse.sh` python3 inline (after every run cycle) | `system-health.py` (reads glob `_pulse-*.json`) · Helm dashboard | Machine-namespaced. schema_version:1. Fields: per-job `last_tick · consecutive_fails · disabled`. |
| `$DRIVE/state/status/_pulse.json` | Drive-synced content | `pulse.sh` python3 inline (same cycle, last-writer-clobber) | Helm dashboard (transition back-compat) | Un-namespaced legacy. Both machines write to this file. Known collision; safe in transition. |
| `$DRIVE/state/status/{desk}.json` | Drive-synced content | each `*-run.sh` via `emit_status.py` | `system-health.py` · Helm dashboard | Per-desk health tiles (emily · archivist · clair · deryl · dobby · marc · sentinel · backlog · planning · item-store · email-summary · security-posture · planning-vault-weekly · marc-weekly · marc-wednesday · _system-health). |
| `/tmp/lifehack-{job}.lock` | ephemeral (machine-local) | `ingest_acquire_lock` (`mkdir` atomic) | `ingest_acquire_lock` (existence check; stale-steal after 1500s fixed for ingest runners, ARCH_WATCHDOG+300 for archivist runners) | PID-less lock dir. |
| `~/.config/lifehack/claude-oauth-token` | machine-local (0600) | human setup / auth refresh | `ingest_load_auth` → `CLAUDE_CODE_OAUTH_TOKEN` | Headless Claude subscription token. |
| `~/.config/lifehack/gws-credentials.json` | machine-local (0600) | human setup | `ingest_load_auth` → `GOOGLE_WORKSPACE_CLI_*` | gws keychain-free exported creds. |
| `~/.config/gws-cron/` | machine-local dir | human setup | `ingest_load_auth` (as isolated gws config dir) | Never `~/.config/gws/` — the main interactive gws config is protected. |
| `~/.config/lifehack/{job}-last-seen` | machine-local | `ingest_finish` on rc=0 | `ingest_new_mail_gate` | High-water epoch marker. Controls which messages are "new" on next tick. |
| `~/.config/lifehack/archivist-{mode}-file-id` | machine-local | `_upload_queue` on first Drive create | `_upload_queue` on subsequent ticks | Cached Drive file-id for tappable queue link. |
| `~/.config/lifehack/sentinel-paused-sources` | machine-local | `sentinel_response.py` (DANGER verdict) | `ingest_check_paused` | Line-delimited. Presence of source key → halt that ingest source. Un-pause = human removes line. |
| `~/.claude/current_email_lane` | machine-local | `ingest_set_lane` (ingest runners) | ingest infrastructure | Active desk lane marker; cleared on EXIT trap. |
| `/tmp/pulse.log` | ephemeral (machine-local) | crontab redirect (`>> /tmp/pulse.log 2>&1`) | human (troubleshooting hint only) | Pulse stdout + stderr. NOTE: `health-deadman-check.sh` does NOT read `/tmp/pulse.log` — it reads `$DRIVE/state/status/_system-health.json` mtime; pulse.log appears only as a human hint string in the notify message body, not as script input. |
| `$DRIVE/state/archivist/deepmine-ledger.json` | Drive-synced content | `arch_postrun` (deepmine runner) | `arch_prerun` (deepmine runner — picks most-overdue desk) | Rotation state: per-desk last-mined timestamp. |
| `$DRIVE/desks/marc/organism/_weekly-wrap.txt` | Drive-synced content | `marc-research-lib.sh` (WRAP_TXT variable, line 29; written by both `marc_research_run` and `marc_material_change_scan`) | `/cal-weekly` skill · human | Marc weekly/wednesday output wrap file. NOTE: no runner code writes to `$DRIVE/desks/marc/diary/` — that path does not exist in live code; grep of full repo finds only the draft's own reference to it. |
| `$DRIVE/desks/marc/organism/heartbeat/last-run.json` | Drive-synced content | `marc-research-lib.sh` (written by `marc_research_run` + `marc_material_change_scan`) | `marc-deadman.py` | Marc pipeline heartbeat; staleness > 28h → dead-man trip. |
| `$DRIVE/system/logs/sentinel-events.jsonl` | Drive-synced content | `_sentinel_log` in `ingest-run.lib.sh` | `sentinel-health-run.sh` → `state/status/sentinel.json` | Append-only security event log. |
| `$DRIVE/system/learnings.md` | Drive-synced content | `@trim_md_days` builtin (learnings-trim job) TRIMS; `/save` skill APPENDS | sessions reading learnings | Trimmed to 90d-old sections. The `/save` skill writes; Pulse only trims. |
| `$DRIVE/system/observability/` | Drive-synced content | observability pipeline | `@find_delete` builtin (observability-trim job) DELETES | `*.jsonl` files older than 30 days deleted. |
| `$DRIVE/state/status/_system-health.json` | Drive-synced content | `system-health.py` (via system-health-run.sh, every 5 min) | `health-deadman-check.sh` (launchd, pinned to one designated machine) · Helm | The health sweeper's own output. |
| `$DRIVE/state/item-store/tasks/` + `.../calendar/` | Drive-synced content | `tasks-store-sync-run.sh` + `calendar-store-sync-run.sh` (Pulse jobs, sole writers) | `item_store_read.py` · planning · ingest desks | Tasks + calendar stores. |
| `$DRIVE/state/email-summary/threads-v2/` | Drive-synced content | `email-summary-write-run.sh` → `email_summary_sync.py --write-v2` (sole writer) | `email_service_read.py` | Faithful thread store. Pulse drives the write; reads go through the adapter. |

---

### GATES AND ACTUAL ENFORCEMENT MECHANISMS

> **⚠ CORRECTED 2026-08-24:** Item 1 below (and every downstream reference to `require_primary`,
> `primary-gate.sh`, `ingest_studio_gate`, `require_studio_hardware`, or `marc-research-lib.sh`
> anywhere in this document — including the "D. Marc pipeline runners" section, the summary INTEROP
> table's `GUARDED-BY require_primary` / `READS two-machine-residency` rows, and GAPS §1/§2 below —
> describes a lead-machine election gate that **does not exist in this repo.** Re-verified directly
> this session:
> - find . -iname '*primary-gate*' → 0 files. `system/tools/primary-gate.sh` — ⛔ verified absent this session; it is part of a fabricated two-machine lead-election model that was never built here (docs/data-layout.md:215: "there is one machine").
> - `grep -rn "require_primary" .` → 0 function DEFINITIONS anywhere, in any language; the string
>   survives only inside comments recording that it was dropped (`system/tools/ingest-run.lib.sh`,
>   `system/tools/archivist-run.lib.sh`, `system/tools/planning-weekly-prime-run.sh`).
> - `find . -iname '*marc-research-lib*'` → 0 files.
> - `grep -n "require_primary\|primary-machine" system/tools/system-health-run.sh
>   system/tools/system-health.py` → 0 matches in either file.
>
> `ingest-run.lib.sh`'s own header states this in full: *"None of the three functions exists in this
> repo — verified by grep: no definition and no call site anywhere, in any language."* The reason is
> architectural: this system has ONE machine — *"there is one machine. The two-machine plane is not
> part of this system."* (`docs/data-layout.md:215`) — so nothing exists for a lead-election gate to
> elect between. Correctly stated elsewhere in this same repo: `elements/archivist.md:71–72`, `elements/backlog-authority.md:203–205`
> ("no machine gate, no require_primary, and no state/primary-machine marker"), and
> `elements/plan-integrity-cluster.md:160` (on the parallel `mirror_plans.sh` fabrication — same
> donor-relic pattern, different file). This whole "1. Machine gate" subsection, both list items
> below, and the mechanism paragraph are DONOR DESCRIPTION carried over uncorrected, not a
> description of what runs here. Struck rather than deleted, per this repo's own no-silent-overwrite
> rule — the fact that four documents carried this as live IS a finding, not just an error to erase.

~~**1. Machine gate — `require_primary` / `ingest_studio_gate` (BLOCKING; `exit 0` on non-lead)**

Three named implementations plus multiple inline copies — all functionally identical in result:
- `primary-gate.sh:require_primary()` — standalone; sourced by emily-breakdown, clair-billing
- `ingest-run.lib.sh:require_primary()` — library function; sourced by clair-ingest, system-health, backlog-health and others
- `ingest-run.lib.sh:ingest_studio_gate()` — name alias for `require_primary`; back-compat for pre-rename runners (planning-health, clair-health, sentinel-health, deryl-ingest, deryl-books-health, marc-health) (`ingest-run.lib.sh:83`)
- Inline copy in `archivist-run.lib.sh` `run_archivist()` step 1 — uses `return 0` (not `exit 0`; correct inside a function, but semantically different if the lib function is ever called from a subshell — see GAPS §1)
- Inline copies in `planning-vault-run.sh`, `planning-diary-run.sh`, `planning-vault-weekly-run.sh`, `cp-utilities-run.sh`, `email-summary-write-run.sh`, `item-store-freshness-run.sh`
- `_lead_gate()` in `marc-research-lib.sh:41` — same logic, different function name

Mechanism in all cases: `/usr/sbin/scutil --get ComputerName` (absolute path — cron's $PATH omits `/usr/sbin`) → mapped to this machine's short token. Compare to `tr -d '[:space:]' < $DRIVE/state/primary-machine`. Non-lead → clean `exit 0` or `return 0`. Pulse's circuit breaker does NOT count deliberate stand-downs as failures.~~

~~**2. Hardware gate — `require_studio_hardware` (BLOCKING; `exit 0` on any machine but the pinned one; `ingest-run.lib.sh:89–94`)**

Case on the raw `ComputerName` of the machine the hardware is physically attached to. NOT lead-selectable — this is a permanent hard pin based on hardware presence. Used by `dobby-health` and `emporia`.~~
**⚠ CORRECTED 2026-09-01 (#61) — this subsection was missed by the 2026-08-24 correction banner
above it, even though that banner's own text names `require_studio_hardware` as one of the things it
covers.** `require_studio_hardware` does not exist in this repo: `system/tools/ingest-run.lib.sh`'s
header lists it as one of three functions explicitly DROPPED and never ported ("None of the three
functions exists in this repo — verified by grep: no definition and no call site anywhere, in any
language"), and `grep -rn "require_studio_hardware" system/` (outside this doc) confirms it survives
only in that drop-note. `ingest-run.lib.sh:89–94` — read directly this session — is not this
function; it is the `CLAUDE_BIN` resolution block (the `command -v claude` / `~/.local/bin/claude` /
`/opt/homebrew/bin/claude` / `/usr/local/bin/claude` fallback chain), unrelated to hardware pinning.
See the same finding at this file's "H. Hardware-pinned runners" line above. Whatever actually
machine-pins `dobby-health`/`emporia` (if anything) is unverified here.

**3. Circuit breaker — `pulse.sh:150–213`**

- Machine-local state in `/tmp/lifehack-pulse-state.json` (keys `fails:{name}` · `disabled:{name}` · `trips:{name}` · `retry_at:{name}`).
- `MAX_FAILURES=3` (`pulse.sh:24`; env-overridable via `PULSE_MAX_FAILURES`). Three consecutive non-zero, non-rc-2, non-rc-75 exits → `disabled:{name}=1` + `notify-send.sh` critical buzz.
- **`set_last` is called UNCONDITIONALLY at `pulse.sh:187`** before the rc branches — even a failing job advances its `last_run` timestamp. This prevents hot-loop retry (a failed job retries after its FULL interval, e.g. 24h for a daily job, not after the next 5-min Pulse tick).
- **rc=2 (TRANSIENT pre-flight) is EXPLICITLY excluded from streak increment** (`pulse.sh:191–199`; comment documents the 2026-06-13 and 2026-06-17 emily-breakdown false-disable incidents). A gws auth blip never trips the breaker.
- **rc=75 (STOOD DOWN) is excluded too, and differently** (`pulse.sh:262–276`): the job WAS dispatched and then declined to run by its OWN preflight. It is counted `skipped` — never `ran`, never `failed` — so the breaker is untouched in both directions. Counting it as `ran` would hide a permanently standing-down job behind a healthy number; counting it as `failed` would trip the 3-strike breaker within 15 minutes of a clean install on any job whose preflight is waiting on configuration that does not exist yet. On the donor system this code meant "not the lead machine"; the CONTRACT is kept for any preflight that decides *not yet*.
- **A trip is a TIMEOUT, not a tombstone.** On the third consecutive real failure the job is held off for a **doubling backoff** — `BACKOFF_BASE=3600` (1h) for the first trip, doubling once per consecutive trip (`trips:{name}`), capped at `BACKOFF_MAX=86400` (24h); both env-overridable (`PULSE_BACKOFF_BASE` / `PULSE_BACKOFF_MAX`). The trip writes `retry_at:{name} = NOW + hold` and restarts the fail streak at 0. The notify buzz names the hold length and says explicitly that the job is not disabled forever.
- **Recovery is TIME-based, not reboot-dependent.** Once `retry_at` passes, the next tick clears `disabled:{name}` and grants **one half-open probe run** (`pulse.sh:205–223`). If the probe exits 0, everything resets — `fails` · `disabled` · `trips` · `retry_at` all cleared, so the next hold would start again at BASE. If it fails, the next hold is twice as long. A genuinely broken job still cannot run unattended in a loop; it retries at 1h, 2h, 4h… instead of never. (The donor incident this closes: three jobs sat disabled 11 / 25 / 28 days after a transient blip tripped an off-forever breaker; when finally run by hand, all three exited clean.)
- **A `disabled` job with `retry_at <= 0` is NOT auto-retried** — that shape means a pre-backoff trip or a deliberate human park, and a missing timer read as 0 would half-open it on the very next tick. Deliberate parks live in their own durable file (see STORES) and are checked BEFORE the breaker.
- Machine-local: a trip on one machine does NOT propagate to the other. A `/tmp` reset (reboot) still clears breaker state wholesale — see GAPS §2 — but it is no longer the only path back: the backoff re-probes on its own clock.

**4. Single-instance lock — `ingest_acquire_lock` (`ingest-run.lib.sh:164–173`)**

`mkdir /tmp/lifehack-{job}.lock` (atomic). If lock exists AND mtime < **1500s (fixed 25 minutes, hardcoded at `ingest-run.lib.sh:167`)** → `exit 0`. Stale-steal after 1500s (remove + re-create). Note: `archivist-run.lib.sh` uses a DIFFERENT threshold: `ARCH_WATCHDOG+300` (= 2100s for the default 1800s archivist watchdog) — this is implementation-specific and applies only to archivist runners. Prevents stacked runs on any job that can run longer than 5 minutes (the Pulse tick interval).

**5. Sentinel pause gate — `ingest_check_paused` (`ingest-run.lib.sh:103–109`)**

Reads `~/.config/lifehack/sentinel-paused-sources`. If source key present → `exit 0`. Never counts as a failure. Human un-pause required (Sentinel never auto-resumes).

**6. New-mail gate — `ingest_new_mail_gate` (`ingest-run.lib.sh:187–213`)**

MUST be called inline (never via `$(...)`) — it calls `exit` to abort the RUNNER process, not a subshell. No marker on first run → seeds to NOW and exits clean (avalanche prevention). gws label count query; if 0 new messages → cheap `exit 0` (no claude spawn, no tokens burned). Sets `INGEST_CUTOFF` + `INGEST_MARKER_CANDIDATE` globals for ingest runners on positive hit.

**7. gws preflight with 3× retry (`ingest_load_gws`; `ingest-run.lib.sh:143–152`)**

Three attempts with 4s sleep between. Failure after 3 → `exit 2` (TRANSIENT). Never counts against the circuit breaker.

**8. Watchdog kill (`ingest_run_claude`; `ingest-run.lib.sh:285`)**

`( sleep $WATCHDOG; kill -9 $cpid ) &` in a background subshell. Prevents a hung `claude -p` process from blocking the job slot indefinitely. Hard-kill; no grace period.

**9. Pulse preflight lead-machine nag (`pulse.sh:123–131`)**

If `$DRIVE/state/primary-machine` is unset: log CRITICAL nag + `notify-send.sh` once (governor-deduped to once per hour). Does NOT exit or abort the Pulse loop — non-writer infra jobs (git-autopush/pull, bootstrap, obsidian-reindex, hook-doc-lint, security-posture-scan, helm-keepalive, marc-deadman, learnings-trim, observability-trim) still run on both machines, which is by-design (see GAPS §3).

**10. Out-of-band health watcher — `health-deadman-check.sh` (BY DESIGN outside Pulse)**

Installed as launchd `ai.lifehack.health-deadman` (pinned to one designated machine, every 900s; the launchd block in `system/pulse-config.md`). Reads mtime of `$DRIVE/state/status/_system-health.json`. If > 2700s stale → critical `notify-send.sh` (governor-deduped). BY DESIGN: this watches the thing-that-watches-Pulse (system-health) — if it were a Pulse job it would share the failure mode it's supposed to catch. Fails OPEN on a missing file (never false-buzzes a fresh clone).

**Hooks from `settings.json` that fire around pulse-cron stores:**

Pulse itself runs entirely as a raw cron subprocess — no Claude Code session, no hook plane. The hooks below fire when a SESSION (human or headless `claude -p` launched by a runner) writes to paths that pulse-cron manages:

- **`guard_write_paths.sh`** (PreToolUse `Write|Edit`) `[hook]` — ~~blocks Write/Edit to `$DRIVE/state/status/*` and other guarded paths from a session tool call.~~ **KNOWN-GAP (accepted 2026-07-14):** only matches the Write/Edit tools; any session write via Bash (`echo >`, `python3`, `tee`, `cp`) bypasses this hook entirely. The Pulse subprocess itself is outside the hook plane by design.
  > **⚠ CORRECTED 2026-08-27, lb2-ops-comms.md claim 35 — misattributed mechanism.** The real
  > `guard_write_paths.sh` is a hooks/settings/.git SELF-PROTECTION guard only — its own header states
  > "THIS IS A DELIBERATE SUBSET, NOT A GENERAL WRITE-CONTAINMENT WALL." `grep -n "state/status"
  > guard_write_paths.sh` returns zero hits, and no other hook file references `state/status` either. This
  > guard does not, in fact, block Write/Edit to `$DRIVE/state/status/*` — see `guard_write_paths.sh`'s
  > actual residency table in hook-plane.md's A10 entry for what it really guards (auto-memory, hooks
  > self-modification, Drive content-class misplacement). The Bash-bypass gap described above is real for
  > what this hook DOES guard; it just doesn't guard `state/status/*`.
- **`ingest_gate_enforce.sh`** (PreToolUse `Bash|WebFetch|WebSearch|Read`) `[hook]` — fires inside a headless `claude -p` session launched by a runner; blocks raw gws Gmail body reads, raw WebFetch/WebSearch. Does NOT fire in the runner's shell itself (only in the spawned claude session that ran `--dangerously-skip-permissions`).
- **`guard_gws_logout.sh`** (PreToolUse `Bash`) `[hook]` — blocks `gws auth logout` patterns. Directly relevant: if a session accidentally ran `gws auth logout` it would destroy the headless gws creds in `~/.config/gws-cron/`. The hook fires in interactive sessions, not in the runner shell.
- **`guard_sheet_writes.sh`** (PreToolUse `Bash`) `[hook]` — destructive Sheet ops require confirmation; does not touch pulse state paths.
- **`block_primary_calendar.sh`** (PreToolUse `Bash`) `[hook]` — blocks gws calendar writes not targeting Agent Ops calendar ID; not pulse-store relevant.
- **`guard_organism_map.sh`** (PreToolUse `Write`) `[hook]` — blocks writes to the organism self-schematic. Not pulse-store relevant; protects the schematic from pulse-cron element edits overwriting shared map files.
- **`nudge_flow_drift.sh`** (PostToolUse `Write|Edit`) — advisory; fires after any Write/Edit on a file cited in an element's `generated_from`; would fire if a session edited `pulse.sh` or `pulse-config.md`.
- **`observability_logger.sh`** (PostToolUse `*`) — logs every tool call; fires universally, no pulse-specific relationship.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** a single crontab line dispatches ALL interval-based maintenance jobs with machine-local state (no shared-lock contention), single-writer machine-gating for Drive writes, and a circuit breaker that auto-disables a broken job before it burns tokens for hours unattended. The human edits `pulse-config.md` to enable/disable jobs; the system then runs autonomously.

**Current state — LIVE with documented residual gaps.** ~~All 37 active jobs in `pulse-config.md`
(confirmed live: 37 `enabled: yes` entries, 4 disabled) are dispatched.~~ ~~**[CORRECTED 2026-08-27,
lb2-ops-comms.md claim 36 — the real count inside `pulse-config.md`'s parseable jobs fence is 21
`enabled: yes` rows and 1 `enabled: no` row, 22 total dispatchable rows, not 37/4.]**~~
**⚠ CORRECTED 2026-09-01 (#61) — the 2026-08-27 correction above has itself drifted, AND the "X yes
/ Y no" shape it used is the deeper defect: this number has now been wrong three times (37/4 →
21/1/22 → the count below) because a two-bucket format cannot represent a row's `enabled` field,
which is a free-text disposition, not a yes/no flag. Restructured below to name every state that
actually occurs, not just "yes" and "everything else."**

Counted this session from `system/pulse-config.md`'s `` ```jobs ``` `` fence — every non-comment
line matching `name | enabled | interval | command` — first to find the **distinct `enabled` values
in use**, via
`grep -vE '^\s*#' <jobs-fence> | grep -E '^\S+ *\| *\S+ *\|' | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}' | sort -u`:
only **two** distinct literals appear — `yes` and `waiting-on-port` — no `no`, no `parked`, no other
spelling (`sort -u` output has exactly 2 lines; `sort -u | wc -l` confirms `2`). So today the
"waiting/parked family" the schema must allow for is a family of *one* live member, not several — the
doc states the actual set rather than assuming `waiting-on-port` was one example among many.

Then the same command with `uniq -c` instead of `sort -u` gives the count per state:
`grep -vE '^\s*#' <jobs-fence> | grep -E '^\S+ *\| *\S+ *\|' | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}' | sort | uniq -c`:

| `enabled:` state | rows | what it means |
|---|---|---|
| `yes` | **23** | dispatched by Pulse every tick its interval allows |
| `no` | **0** | none currently — the literal exists in the schema (see `pulse-config.md`'s own field docs) but no row uses it today |
| `waiting-on-port` (the wait/park family — currently this one literal only) | **22** | declared not-yet-runnable, not silently off; re-check `pulse-config.md` if a future row uses a different member of this family (`parked`, `waiting-on-<other-thing>`) — the family is open-ended by the manifest's own field docs even though only one member is in use right now |
| **total rows in the fence** | **45** | 23 + 0 + 22 |

(the set counted is *rows in the parseable jobs fence*, not "installed crontab entries" and not some
other subset — re-run the commands above against the live file to reproduce every number in this
table, including a re-check of the distinct-values list itself in case a new state has since been
added). All active jobs are dispatched. Circuit breaker,
`require_primary`, sentinel pause, and single-instance lock are all mechanically enforced in live code.
Drive heartbeat mirror (`_pulse-{machine}.json`) feeds system-health. `install-schedulers.sh` is the
versioned installer; `runner-standard.md` codifies the runner contract.

**Known divergences from target:**

- `machine-log-trim` registered `no` permanently: `@trim_md_days` cannot parse its pipe-delimited format (no `## YYYY-MM-DD` date headers). Re-enable only after adding a matching trim builtin. This is a dead entry in pulse-config.
- `supabase-keepalive` / `supabase-backup` registered `no` in Pulse but still ACTIVE via launchd plists in the `launchd` block. Two schedulers for the same jobs until launchd plists are removed. Migration is pending; the Pulse version is the target.
- `marc-wednesday` field reads `enabled: yes` but the comment above the job line says "DISABLED (no) until one live-proof run passes." The live code field wins — it WILL fire. Comment is stale; verify intent.
- `planning-rollup-catchup` is NOT yet built: the three clock-pinned weekly/monthly/quarterly `planning-diary` jobs silently miss when the primary machine is asleep at scheduled wall-clock times. A Pulse interval job that checks for a missed period and builds if absent is the planned fix; not yet registered.
- `runner-standard.md` claims "All 38 runners" comply but the migration table lists only 10 with confirmed status — 28 runners' compliance is opaque (audit gap; the doc is stale).
- `system-health.py`'s `JOB_LABELS`, `JOB_DOWNSTREAM`, and `FRESH_TILES` are hardcoded dicts — new Pulse jobs silently get no label in health output and no staleness overlay.
- `archivist-audit` silencing (debt-ledger `[ARCHIVIST-AUDIT-DEAD]`): the debt item flagged the runner as silent. NOTE: the 2026-07-13 inline annotation on that debt entry reads "LIKELY FALSE-ALARM — pulse.log shows the 2026-07-06 run fired, ran ~78min, hit a transient API drop (rc=1), NOT circuit-broken; next run due ~21:05 tonight. Clear this once tonight's run writes a fresh audit log." The silence may have been a transient failure, not a structural halt. The underlying architectural concern remains valid regardless: single-machine gating is the wrong posture for Drive-stateful cron. TARGET is: Drive-stateful cron jobs should run on BOTH machines (either a cross-machine lock OR idempotent+dedup-safe runs). Current single-machine-gated runners are PARTIAL vs target.

---

### INTEROP SEAMS

```
TRIGGERS    system-health               · dispatches system-health-run.sh → reads _pulse-*.json + pulse-config.md to detect missed runs
TRIGGERS    archivist (audit+deepmine)  · fires archivist-audit/deepmine-run.sh on their respective intervals
TRIGGERS    ~~emily-breakdown~~             · ~~fires emily-breakdown-run.sh; ingest runner contract via ingest-run.lib.sh~~
  [CORRECTED 2026-09-01 (#61) — `emily-breakdown` is `waiting-on-port` in `system/pulse-config.md`'s
  `` ```jobs ``` `` fence; `find . -name "emily-breakdown-run.sh"` returns zero files this session.
  Nothing here fires this runner.]
TRIGGERS    ~~clair-ingest~~                · ~~fires clair-ingest-run.sh; ingest runner contract via ingest-run.lib.sh~~
  [CORRECTED 2026-09-01 (#61) — `clair-ingest` does not appear in `system/pulse-config.md`'s
  `` ```jobs ``` `` fence at all (neither `yes` nor `waiting-on-port`); `find . -name
  "clair-ingest-run.sh"` returns zero files this session. Nothing here fires this runner.]
TRIGGERS    ~~deryl-ingest~~                · ~~fires deryl-ingest-run.sh; ingest runner contract via ingest-run.lib.sh~~
  [CORRECTED 2026-09-01 (#61) — `deryl-ingest` is `waiting-on-port` in `system/pulse-config.md`'s
  `` ```jobs ``` `` fence; `find . -name "deryl-ingest-run.sh"` returns zero files this session.
  Nothing here fires this runner.]
TRIGGERS    ~~marc-pipeline~~               · ~~fires marc-weekly/wednesday/deadman-run.sh; marc-research-lib.sh contract~~
  [CORRECTED 2026-09-01 (#61) — `marc-weekly`, `marc-wednesday`, and `marc-deadman` are all
  `waiting-on-port` in `system/pulse-config.md`'s `` ```jobs ``` `` fence; none of
  `marc-weekly-run.sh`, `marc-wednesday-run.sh`, `marc-deadman.py`, or `marc-research-lib.sh` exist
  in this repo (verified by filename search this session). See Sections D and E above.]
TRIGGERS    email-service               · fires email-summary-write-run.sh + email-summary-freshness-run.sh
TRIGGERS    grand-central               · fires tasks-store-sync-run.sh + calendar-store-sync-run.sh
TRIGGERS    sentinel                    · fires sentinel-health-run.sh → reads sentinel-events.jsonl → tile
TRIGGERS    ~~git-sync~~                    · ~~fires git-autopush + git-autopull (keeps both machines' clone in sync)~~
  [CORRECTED 2026-09-01 (#61) — both `git-autopush` and `git-autopull` are `waiting-on-port` in
  `system/pulse-config.md`'s `` ```jobs ``` `` fence; neither `git-autopush.sh` nor `git-autopull.sh`
  exists in this repo (verified this session). Same finding the SYNCS line below already carries for
  `git-autopull.sh` alone — this TRIGGERS line was the one instance of it left undisclosed.]
READS       two-machine-residency       · [STRUCK — ⚠ CORRECTED 2026-08-24: no code reads state/primary-machine via require_primary; require_primary() has zero definitions anywhere in the repo (verified this session) and this system has one machine (docs/data-layout.md:215). See the correction banner at "GATES AND ACTUAL ENFORCEMENT MECHANISMS" above.] was: reads state/primary-machine on every writer-runner tick via require_primary
READS       pulse-config.md             · reads the ```jobs block every tick for the job schedule manifest
WRITES->    durable-status-plane        · writes state/status/_pulse-{machine}.json + _pulse.json heartbeat mirrors after every cycle
WRITES->    durable-status-plane        · runner jobs write state/status/{desk}.json tiles via emit_status.py
WRITES->    system/learnings.md         · learnings-trim job trims sections older than 90d (the /save skill appends; Pulse trims)
WRITES->    system/observability/       · observability-trim job deletes *.jsonl older than 30d
WRITES->    system/logs/maintenance-due.md · hook-doc-lint job is the sole writer (honor-system pickup by sessions)
FEEDS       helm                        · _pulse-*.json glob drives dashboard freshness + per-job heartbeat tiles
FEEDS       helm                        · state/status/*.json tiles drive per-desk health cards
~~FEEDS       marc-pipeline               · marc_research_run + marc_material_change_scan stamp desks/marc/organism/heartbeat/last-run.json; marc-deadman reads it~~
  [CORRECTED 2026-09-01 (#61) — same finding as the TRIGGERS marc-pipeline line above: none of the
  marc runner scripts this line describes exist in this repo. No heartbeat is written or read here.]
FEEDS       planning                    · planning-vault-weekly-run.sh writes desks/cal/state/weekly-vault/ → planning-weekly-analyze-run.sh consumes (⚠ `desks/cal/` is DELIBERATE: the desk's code/jobs/tiles renamed to `planning`, the records directory did NOT — the operator's call, untaken)
FEEDS       email-service               · email-summary-write-run.sh → state/email-summary/threads-v2/ (faithful thread store)
FEEDS       grand-central               · item-store jobs → state/item-store/tasks/ + state/item-store/calendar/ (sole writers)
SYNCS       two-machine-residency       · ~~git-autopush/pull keep pulse-config.md in sync; NOTE: git-autopull.sh does NOT call install-schedulers.sh — it only does a git fetch + ff-only merge; install-schedulers.sh must be run manually after a pull to rebuild the crontab (bootstrap-machine.sh prints this as an echo instruction, not an automated call)~~
  [CORRECTED 2026-08-27, lb2-ops-comms.md claim 38 — `git-autopull.sh` does not exist anywhere in the repo
  (`find`: 0 hits). `pulse-config.md` itself marks both `git-autopush` and `git-autopull` as
  `waiting-on-port` / "NOT PORTED" — there is no working script here that fetches+ff-merges yet; this line
  described a donor behavior as if it were live here.]
FEEDS       security-posture-scan       · pulse-config.md is read by security-posture-scan.sh to verify supabase jobs stay disabled + emily stays enabled
COMPLEMENTS notify-plane                · pulse.sh calls notify-send.sh directly for circuit-breaker trips + no-lead nag; all *-run.sh runners channel alerts through notify-send.sh
COMPLEMENTS health-deadman-check.sh     · launchd watcher (BY DESIGN outside Pulse) watches system-health tile mtime; catches a dead Pulse+health chain that no Pulse job could detect
GUARDED-BY  require_primary             · [STRUCK — ⚠ CORRECTED 2026-08-24: not a real guard. require_primary() has zero definitions anywhere in the repo and primary-gate.sh does not exist on disk (both verified by grep/find this session); Drive-writing jobs run with no machine gate. See the correction banner at "GATES AND ACTUAL ENFORCEMENT MECHANISMS" above and elements/backlog-authority.md:203-205.] was: single-writer safety on all Drive-writing jobs (ingest-run.lib.sh + primary-gate.sh + inline copies)
GUARDED-BY  ingest_acquire_lock         · prevents stacked runs per job; single-instance enforcement in every claude-invoking runner
GUARDED-BY  circuit breaker (pulse.sh)  · auto-disables a job after 3 consecutive non-transient failures; rc=2 never trips it
GUARDED-BY  ingest_check_paused         · Sentinel danger verdict → human-gated source pause; no auto-resume
GUARDED-BY  guard_write_paths.sh [hook] · ~~blocks Write/Edit tool calls to status stores from a session~~
  [CORRECTED 2026-08-27, claim 35 — misattributed; this guard does not reference `state/status` at all, see
  §6 below] (NOT from the pulse subprocess; Bash-write bypass gap accepted 2026-07-14)
GUARDED-BY  ingest_gate_enforce.sh [hook] · fires inside claude -p sessions launched by runners; blocks raw external reads + gws body reads
```

---

### GAPS (documented fail-open conditions)

**§1 — Multiple parallel `require_primary` implementations (no single canonical copy)**
Three named implementations (`primary-gate.sh`, `ingest-run.lib.sh:require_primary`, `ingest-run.lib.sh:ingest_studio_gate`) plus at least six inline copies scattered across individual runners and `archivist-run.lib.sh`. A bug fix to one implementation does NOT propagate. The `archivist-run.lib.sh` copy uses `return 0` (correct inside a function) while standalone copies use `exit 0` — semantically different if the function is ever called from a subshell. Tracked as `[PRIMARY-GATE-DEDUP]` in debt-ledger (`state:monitoring`). Target: extract a single canonical `primary-gate.sh` and have ALL runners source it.

**§2 — Circuit breaker is machine-local and `/tmp`-ephemeral**
A trip on one machine does not propagate to the other. A `/tmp` wipe (reboot) re-arms a genuinely broken job. The system-health sweeper's staleness detection (no tile update past freshness threshold) is the only backstop. There is a window between reboot and next system-health tick where a re-armed bad job can fire once or more.

**§3 — No-lead-machine is fail-OPEN for the pulse loop itself (FAIL-OPEN condition)**
When `state/primary-machine` is unset, `pulse.sh` preflight logs a nag and CONTINUES the loop. Writer runners individually `exit 0` via `require_primary` — but non-writer infra jobs (`git-autopush/pull`, `bootstrap-sync`, `obsidian-reindex`, `hook-doc-lint`, `security-posture-scan`, `helm-keepalive`, `marc-deadman`, `learnings-trim`, `observability-trim`) all run on both machines with no gate. By design for resilience; means unattended infra writes can occur from both machines simultaneously without a designated lead.

**§4 — Clock-pinned crons silently miss on a sleeping laptop-primary (FAIL-OPEN condition)**
`planning-diary-weekly`, `planning-diary-monthly`, `planning-diary-quarterly` are direct crontab entries (not Pulse interval jobs). If the primary machine is asleep at the scheduled wall-clock time, the run is permanently missed — cron does not catch up. These are "best-effort + regenerable on demand." A `planning-rollup-catchup` Pulse job is the planned fix (debt-ledger `[CAL-ROLLUP-CATCHUP]`, `state:actionable`); not yet built.

**§5 — rc=2 never trips the circuit breaker (FAIL-OPEN condition)**
`pulse.sh:191–199` explicitly excludes rc=2 from the failure streak. A runner permanently stuck in transient-pre-flight (e.g. gws auth consistently failing, returning rc=2 on every tick) will log `WARN` on every tick forever without auto-disabling. The system-health sweeper's tile-staleness detection is the only backstop for a permanently-rc-2-stuck runner.

**§6 — `guard_write_paths.sh` Bash-write bypass (KNOWN-GAP, accepted 2026-07-14)**
~~`guard_write_paths.sh` matches `Write|Edit` tools only. Any session that writes to `$DRIVE/state/status/*` via Bash (`echo >`, `python3 inline`, `tee`, `cp`) bypasses the guard entirely.~~ **⚠ CORRECTED 2026-08-27,
lb2-ops-comms.md claim 35 — this section misattributes the mechanism.** The real `guard_write_paths.sh` is a
self-protection guard for hooks/settings.json/.git only (its own header: "THIS IS A DELIBERATE SUBSET, NOT
A GENERAL WRITE-CONTAINMENT WALL") — `grep -n "state/status" guard_write_paths.sh` returns zero hits, and no
other hook mentions `state/status` either. `$DRIVE/state/status/*` has no dedicated Write/Edit guard of any
kind, Bash-bypassable or otherwise — the gap this §6 describes is broader than "Bash bypasses a guard": no
guard exists to bypass. Mitigation: discipline + review. The pulse subprocess itself is outside the hook
plane by design (it runs as a raw cron subprocess, never inside a Claude Code session).

**§7 — `_pulse.json` (legacy) is last-writer-clobber on Drive**
Both machines write to `$DRIVE/state/status/_pulse.json` (un-namespaced). Whichever machine runs its pulse tick last wins. Safe in the transition period because Helm still reads this file; once Helm migrates to the glob (`_pulse-*.json`) this file can be retired. The machine-namespaced `_pulse-{machine}.json` files are the canonical path.

**§8 — marc-wednesday `enabled: yes` conflicts with its config comment**
The comment above the job line says "DISABLED (no) until one live-proof run passes"; the actual `enabled` field reads `yes`. The live code field wins — it WILL fire. The comment is stale. Verify intent with the operator; one of them needs to be corrected.

**§9 — supabase launchd double-scheduler (migration pending)**
`supabase-keepalive` and `supabase-backup` are registered `no` in pulse-config but remain active via launchd plists in the `launchd` block of the same file. Two schedulers cover the same jobs until the launchd plists are removed. Tracked in pulse-config.md as "remove launchd plists once Pulse is proven stable."

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)

- **maturity_label:** LIVE·gap
- **check_detail:** pending label_checker.py
