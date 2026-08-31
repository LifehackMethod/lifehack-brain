---
element: health-invariants
title: "health-invariants — element detail (ground/base altitude)"
subsystem: reliability
altitude: base
record_type: organism-element
maturity_label: LIVE·gap [provisional]
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C4 silent-death — _security.json tile freshness is governed only by the system-health sweep; no independent guard"
generated_from:
  - system/tools/health_invariants.py
  - system/tools/system-health.py
  - system/tools/system-health-run.sh
  - system/tools/health-deadman-check.sh
  - system/tools/marc-deadman.py
  - system/pulse-config.md (system-health Pulse slot; launchd manifest)
  - system/tools/planning-health.py
  - system/tools/marc-health.py
  - system/tools/clair-health.py
  - system/tools/deryl-books-health.py
  - system/tools/dobby-health.py
  - system/tools/backlog-health.py
  - system/tools/sentinel-health.py
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# health-invariants — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#health-invariants ; ground truth → the live artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds detail of how the Health Authority
> detects substrate failure, missed runs, and masking-by-omission across both machines. The MIDDLE
> manual (`system/organism/manual.md`) carries only a one-line pointer here; the TIP (`CLAUDE.md`
> schematic) shows only its box + arrows.
>
> **One-line:** assert five structural invariants and sweep every Pulse job for missed runs — on any
> breach, push a phone alert and surface a `BROKEN` tile on the Helm dashboard; the out-of-band
> dead-man's-switch watches the sweeper itself from outside Pulse so silence is never mistaken for health.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[script]` (deterministic code path, always runs) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).
>
> **CITATION NOTES — what happened, at THIS repository, to the paths this element names.** The
> description is a faithful account of the donor system and is unchanged; these lines record only the
> destination's answer, so a reader hunting for a named file knows what they will find.
>
> ⛔ **Every status tile named here is runtime-generated, created on first run, never committed** —
> `state/status/*.json`, `state/status/_pulse-*.json`, `state/status/_system-health.json`,
> `state/status/planning.json`, `state/status/marc.json`, `state/status/clair.json`,
> `state/status/deryl.json`, `state/status/dobby.json`, `state/status/backlog.json`,
> `state/status/sentinel.json`. These are outputs of a run, written into the reader's own notes
> folder; a fresh checkout correctly has none of them. Two further destination facts: this system runs
> on ONE machine, so `system/tools/pulse.sh` writes a single un-namespaced `_pulse.json` rather than
> the donor's per-machine `_pulse-*.json` set; and the marc / clair / deryl / dobby producers are not
> in this repository at all (those desks are excluded from the migration), so their tiles never appear
> here even at runtime. The planning, backlog and sentinel producers do ship, so those three tiles appear
> once their job has run.
>
> ⛔ `state/health.jsonl` — never a committed file, and not written here at all. This repository's
> `system/tools/health_invariants.py` records each invariant run through
> `system/tools/emit_finding.py` into the per-producer findings shard
> `state/findings/<producer>.<machine>.jsonl` instead of the donor's hand-rolled append; the
> append-only ground-truth guarantee described below is intact, the filename is not.
>
> ⛔ `system/templates/launchd/ai.lifehack.health-deadman.plist` — excluded from the migration:
> machine-local scheduler plumbing. There is no `system/templates/launchd/` here. This repository
> installs its schedules with `system/tools/install-schedulers.sh` (crontab on Mac/Linux, Task
> Scheduler on Windows), which rules *"CRON, NOT LAUNCHD"* in its own header, so no plist template is
> owed. The dead-man script itself, `system/tools/health-deadman-check.sh`, DID land.

---

## AUTHORED   (human-only)

### ARCHITECTURE OVERVIEW

The Health Authority is two collaborating components that together answer the question
"is Lifehack actually running?" — not just "did the last job show green?":

| Component | File | Scheduler | Writer | Role |
|---|---|---|---|---|
| **Sweeper** | `system-health.py` via `system-health-run.sh` | Pulse slot `system-health`, every 300s | ~~Lead machine only (reads `state/primary-machine`)~~ **⚠ CORRECTED 2026-08-24: no lead-machine gate — `system-health-run.sh` reads no such marker, verified this session; see the correction under COMPONENT A below.** | Dead-man's switch: job ABSENCE past interval+grace = BROKEN |
| **Integrity layer** | `health_invariants.py` | Called by sweeper at end of each sweep | Same as sweeper | Deterministic substrate checks: hooks present · guards untampered · clone fresh · both machines heartbeating · coverage complete |
| **Dead-man's-switch for the sweeper** | `health-deadman-check.sh` | launchd `ai.lifehack.health-deadman`, every 900s, second-machine-only | Notification-only (no shared write) | Watches whether `_system-health.json` itself has gone stale |
| **Per-desk producers** | `{desk}-health.py` / `{desk}-health-run.sh` | Pulse, desk-specific intervals | Lead machine | Desk-scoped health tiles (`state/status/{desk}.json`) consumed by the sweeper |
| **Marc dead-man** | `marc-deadman.py` | Pulse slot `marc-deadman`, every 10800s | Notification-only | Watches Marc organism heartbeat specifically (28h threshold; runs on ALL machines) |

The founding doctrine (2026-06-18 council): **"assume broken until proven healthy."** Every check
defaults to BROKEN on its own error — an invariant that cannot run is a RED, never a silent pass.

The **HEADER RULE** at `health_invariants.py:14`: after the founding invariant set, adding a check
requires deleting one. The check set is intentionally sized to real failure classes only — an
ever-growing check list IS the maintenance-tax-as-product failure this loop exists to end.

---

### COMPONENT A — THE MISSED-RUN SWEEPER (`system-health.py`)

**Trigger:** Pulse dispatches `system-health-run.sh` every 300s. ~~`system-health-run.sh` gates on the
lead machine (`require_primary "system-health"` from `ingest-run.lib.sh`) — `_system-health.json` is
a single shared Drive file, so exactly one host writes it.~~ **⚠ CORRECTED 2026-08-24:**
`system-health-run.sh` has no lead-machine gate — `grep -n "require_primary\|primary" system/tools/
system-health-run.sh` returns zero matches, checked directly this session. `require_primary()` has no
definition anywhere in the repo (grep repo-wide, this session); this system has one machine
(`docs/data-layout.md:215`: "there is one machine. The two-machine plane is not part of this
system."), so there is nothing to elect a lead among. `_system-health.json` has a single writer
because there is only ever one machine running Pulse, not because of a gate — same pattern as
`elements/backlog-authority.md:199-205`'s correctly-stated equivalent. The sweeper READS the
machine-namespaced `_pulse-*.json` glob, so it sees both machines' heartbeats if more than one clone
happens to write there — see the corrected point below on `state/primary-machine` for the rest of
this fabrication.

**Input sources (read by the sweeper each run):**
- `system/pulse-config.md` — authoritative job list (enabled flag, interval, command); parsed from
  the ` ```jobs ` block (`system-health.py:181–195`). Code-resident (clone), not Drive, so a fix in
  the clone is picked up immediately without a Drive sync.
- `state/status/_pulse-*.json` — machine-namespaced heartbeat files; sweeper takes `max(last_tick)`
  across machines per job (`system-health.py:198–213`).
- `state/status/*.json` — per-job or per-desk status tiles; consulted for tile-staleness and
  unexpected-zero overlays (the green-illusion hardening).
- ~~`state/primary-machine` — the current lead machine identifier (read by `system-health-run.sh` via
  `require_primary`; also used by `_current_lead()` at `system-health.py:54`).~~ **⚠ CORRECTED
  2026-08-24:** `system-health-run.sh` does not read `state/primary-machine`, and `system-health.py`
  has no `_current_lead()` function — `grep -n "_current_lead\|primary-machine\|require_primary"
  system/tools/system-health.py` returns zero matches, checked directly this session. Same
  fabrication as the Trigger line above; there is no lead-machine concept in this repo
  (`docs/data-layout.md:215`). The `READS grand-central` row further down this document (INTEROP
  table) repeats this same false claim and needs the identical correction.
- `system/desk-registry.yaml` — desk fleet definition; the drift cop reads it every sweep
  (`system-health.py:381`). Code-resident (clone).
- `~/.config/lifehack/sentinel-paused-sources` — machine-local Sentinel containment list; read
  every sweep to surface PAUSED-BY-SENTINEL state (`system-health.py:218–226`).

**Assess logic (per-job state machine, `system-health.py:296–341`):**

| State | Trigger |
|---|---|
| `EXPECTED-ABSENT` | job pinned to hardware only one machine has + lead ≠ that machine |
| `PAUSED-BY-SENTINEL` | source name is in the sentinel-paused-sources list |
| `PAUSED` | `enabled: no` in pulse-config |
| `DOWN` | circuit-broken (`disabled: true` in heartbeat — set by Pulse's circuit breaker after MAX_FAILURES consecutive fails; `consecutive_fails` is a count stored alongside, not the trigger) |
| `LATE` | never ticked OR now − last_tick > interval + grace (grace = max(600, interval × 0.5)) |
| `STALE` | job ticked on time BUT its status tile is older than `stale_after_s` |
| `VERIFY` | `expect_findings:true` in tile but `findings_count == 0` — silent-empty guard |
| `UP` | all checks pass |

**Green-illusion hardening (the load-bearing caveat):** "green" means ran + fresh + produced expected
output. Two overlays survive even a fresh heartbeat tick: tile staleness and unexpected-zero. If a
job updates its heartbeat every 5 minutes but its tile stops refreshing, it shows STALE, not UP.

**Cron-only tile-watch:** `planning-vault`, `planning-analyze`, `planning-diary` are OS-crontab scheduled (not Pulse
slots). The sweeper watches their status tiles directly via `assess_tile_only()` at `system-health.py:267`.
This is runner-standard §3 compliance: crontab-scheduled runners emit tiles; aliveness watches tiles,
not heartbeats.

**Desk-fleet drift cop (`assess_registry`, `system-health.py:435–516`):** for every desk in
`desk-registry.yaml`, checks: (1) producer file present in `system/tools/` by verbatim name;
(2) conformance — registry `conformant:false` flag OR live-tile envelope drift vs emit_status contract;
(3) named Pulse slot present; (4) `purpose.md` declared and file exists; (5) `reads_external` coverage
(only when `INGEST_COVERAGE_FLAG=on`, which is the live armed state as of 2026-06-21). Returns
DRIFT-shaped dicts that render on the dashboard and buzz through the existing ntfy path — shape-
compatible with `assess()`.

**Side-effect spawns (graceful, none block the sweep):** after assessment, system-health.py spawns:
- `security-health.py` — refreshes `_security.json` (Helm Security tab tile)
- `archivist-placements.py` — folds autoplace-ledger rows into `archivist.json`
- `archivist-lean.py` — refreshes Archivist leanness metrics

All three are `subprocess.run(..., capture_output=True)` calls — a failure never blocks the sweep or
corrupts `_system-health.json`.

**ntfy push:** NEWLY-attention jobs only (deduped against prior feed). Error-severity jobs (`error`)
trigger `--priority critical` to bypass quiet hours. Warning-severity (`warning`) respects quiet hours.

---

### COMPONENT B — THE INTEGRITY LAYER (`health_invariants.py`)

Called at the END of each sweep via `results += _hi.run(DRIVE, CODE_ROOT, now, assessed_jobs=...)` at
`system-health.py:543`. The `assessed_jobs` set is captured BEFORE these results are appended so the
coverage self-check (Invariant 5) is honest. Graceful: a module-level error never blocks the sweep.

Returns attention-shaped dicts (same shape as `assess()`) — so a broken invariant flows into
`need_attention[]` AND buzzes through the same ntfy path as any other dead job.

Also appends ONE line to `state/health.jsonl` — the append-only ground-truth log. This is the
**sole health read that survives even if a tile lies**: the invariant result is always written before
the sweep feed is published. Format per line (`health_invariants.py:215–219`):

```json
{
  "ts": "<ISO8601>",
  "machine": "<machine-token>",
  "invariants": {
    "hooks": {"ok": true|false, "why": ""},
    "guards": {"ok": true|false, "why": ""},
    "clone": {"ok": true|false, "why": ""},
    "heartbeats": {"ok": true|false, "why": ""},
    "coverage": {"ok": true|false, "why": ""}
  },
  "all_ok": true|false,
  "sweeper_assessed": <int>
}
```

The five founding invariants:

#### Invariant 1 — Hooks present (`integrity:hooks`)

`health_invariants.py:71–84`

Globs `system/hooks/guard_*.sh` (all guard scripts). Additionally asserts the four **critical hooks**
(`CRITICAL_HOOKS` at `health_invariants.py:39`):
- `block_primary_calendar.sh`
- `ingest_gate_enforce.sh` (subsumed `enforce_email_sanitize` 2026-07-03)
- `guard_write_paths.sh`
- `guard_egress.sh`

Checks: file exists AND `os.path.getsize > 0`. An empty file is treated as missing (hooks are
`chmod 444`, bash-invoked, not executable — size > 0 is the liveness test).

Severity: `error` on failure.

#### Invariant 2 — Guards untampered (`integrity:guards`)

`health_invariants.py:88–104`

Runs `git status --porcelain -- system/hooks/` against the CODE_ROOT clone. Any guard script in
`system/hooks/` that is **modified but NOT committed** fires a BROKEN with `error` severity.

The rationale (Naomi's "sneaky disable"): a guard edited but not committed = the tamper signature.
Self-clears on a legitimate commit, so normal committed development does NOT trigger this.

Requires `.git` directory present; if absent → BROKEN.

#### Invariant 3 — Clone freshness (`integrity:clone`)

`health_invariants.py:108–133`

Three sub-checks:
1. **Unpushed commits:** `git rev-list --count @{u}..HEAD`. If count > `CLONE_AHEAD_WARN` (8) →
   BROKEN with `warning` severity (the other machine is materially behind). Threshold: 8 commits
   (`health_invariants.py:41`).
2. **Behind origin:** `git rev-list --count HEAD..@{u}`. If count > 0 → `warning` (pull needed).
   Opportunistic — only fires if a recent FETCH_HEAD exists.
3. **Fetch staleness:** `FETCH_HEAD` mtime > `FETCH_STALE_S` (3 days, `health_invariants.py:42`) →
   `warning` (freshness unknown; no network call made here).

Note: `warning` severity (not `error`) for clone-freshness — a stale clone is a problem, not an
emergency.

#### Invariant 4 — Both machines reporting (`integrity:heartbeats`)

`health_invariants.py:138–164`

The **masking-by-omission fix** (the second machine once showed all-green while the primary
machine's jobs were dead because the primary machine's heartbeat simply wasn't seen).
`EXPECTED_MACHINES` at `health_invariants.py:36` holds one token per expected machine.

For each expected machine: reads its `_pulse-{machine}.json`, takes `max(last_tick)` across all
jobs. A machine is BROKEN if:
- no heartbeat file at all (`<machine>: NO heartbeat file`)
- file present but no job has ever ticked
- most-recent tick > `HEARTBEAT_STALE_S` (1800s = 30 min, `health_invariants.py:37`)

Pulse cadence is 5 min → >30 min silent = a real problem (9 consecutive misses), not a blip.

Severity: `error`.

Live state (2026-07-24): the second machine shows `heartbeats: ok:false` — stale 469.8h because
that machine is offline (traveling). This is the documented expected-absent pattern, but the check fires
BROKEN regardless — no lead-aware suppression exists here (unlike the sweeper's `EXPECTED-ABSENT`
state for hardware-pinned jobs). UNVERIFIED whether a planned suppression exists.

#### Invariant 5 — Coverage self-check (`integrity:coverage`)

`health_invariants.py:168–193`

Parses `system/pulse-config.md` for all `enabled: yes` jobs. Compares against the
`assessed_jobs` set passed in by the sweeper. Any enabled job the sweeper never assessed =
`masking-by-omission`. FAIL LOUD.

**When called standalone** (no sweeper passing `assessed_jobs`): `assessed_jobs=None` → returns
PASS with a note ("standalone run — sweeper didn't pass its set"). This prevents false alarms when
the module is run directly for diagnostics.

Severity: `error` on uncovered jobs.

---

### COMPONENT C — THE OUT-OF-BAND DEAD-MAN'S SWITCH (`health-deadman-check.sh`)

**The problem it solves:** if Pulse wedges or the sweeper dies, `_system-health.json` stops
refreshing and the board shows a stale tile — but the system cannot tell you it's blind. The sweeper
cannot watch itself from inside Pulse.

**Scheduler:** launchd `ai.lifehack.health-deadman` (second-machine-only, every 900s / 15 min). Registered
in `system/pulse-config.md` launchd manifest (`pulse-config.md:347`). Script: `system/tools/health-deadman-check.sh`.

**Template gap:** the plist template (`system/templates/launchd/ai.lifehack.health-deadman.plist`)
does NOT exist in the clone (confirmed 2026-07-24 — UNVERIFIED whether a non-template version is
installed on the second machine). The script file exists at `system/tools/health-deadman-check.sh`; the plist
template is absent from the clone. The installed plist on the second machine is NOT verified from this
machine. See GAP-3 below.

**Threshold:** `THRESHOLD=2700` (45 min, `health-deadman-check.sh:21`) — if `_system-health.json`
mtime is > 45 min old, the sweeper is declared wedged and a `critical` notification fires. 45 min =
9 consecutive 5-min Pulse misses, so a transient blip does not alarm.

**Fail-open on absence:** a missing `_system-health.json` → exit 0 (fresh clone / never-run → NOT
a wedge). `health-deadman-check.sh:24`. This is correct and deliberate.

**Notification:** calls `notify-send.sh --priority critical` (bypasses quiet hours — a dead monitor
is a wake-me event). The notify-governor deduplicates so a persisting wedge buzzes once/24h, not
every 15 min.

This watcher is NEVER in a Pulse slot BY DESIGN: a Pulse-dispatched version would die with the very
thing it watches (`pulse-config.md:365`).

---

### COMPONENT D — PER-DESK HEALTH PRODUCERS

Each desk has a dedicated producer that runs on its own Pulse cadence and writes a status tile. The
sweeper consumes these tiles for STALE detection and unexpected-zero overlay.

| Producer | Pulse slot | Cadence | Tile path | FRESH_TILES entry |
|---|---|---|---|---|
| `planning-health.py` (⚠ no `-run.sh` wrapper here — the Pulse row calls the checker directly) | `planning-health` | 21600s (6h) | `state/status/planning.json` | yes |
| `marc-health.py` / `marc-health-run.sh` | `marc-health` | UNVERIFIED | `state/status/marc.json` | yes |
| `clair-health.py` / `clair-health-run.sh` | `clair-health` | UNVERIFIED | `state/status/clair.json` | yes |
| `deryl-books-health.py` / `deryl-books-health-run.sh` | `deryl-books-health` | 86400s (24h) | `state/status/deryl.json` | yes (`deryl-books-health`) |
| `dobby-health.py` / `dobby-health-run.sh` | `dobby-health` | UNVERIFIED | `state/status/dobby.json` | yes |
| `backlog-health.py` / `backlog-health-run.sh` | `backlog-health` | 21600s (6h) | `state/status/backlog.json` | yes |
| `sentinel-health.py` / `sentinel-health-run.sh` | `sentinel-health` | 1800s | `state/status/sentinel.json` | no (sweeper uses `sentinel_fold()` inline) |

These producers are the **source of all desk-level health data** — when a desk producer stops running,
the tile goes stale and the sweeper surfaces it as STALE, then a ntfy fires.

The `FRESH_TILES` dict at `system-health.py:40–44` maps Pulse job slugs to desk names for
tile-staleness lookup. This is a known shadow desk-list (see GAP-1 below).

---

### COMPONENT E — MARC DEAD-MAN'S SWITCH (`marc-deadman.py`)

A desk-specific second dead-man layer (`system-health.py` is the system-level one). Reads
`desks/marc/organism/heartbeat/last-run.json` — stamped UTC by every Marc gather run. If the
heartbeat is > 28h stale (`THRESH_H = 28`, `marc-deadman.py:12`), fires one `critical` notification.

**Runs on ALL machines** (no lead-gate) — `marc-deadman.py:7`: "Runs on EVERY machine (NO lead-gate)
so the non-lead can catch the lead going dark — the heartbeat is Drive-synced, so any machine reads
the last-known stamp." Double-buzz is collapsed by notify-governor's 1h critical-dedup.

**Scheduler:** Pulse slot `marc-deadman`, every 10800s (3h), `pulse-config.md:200`.

---

### STORES WRITTEN

| Store | Writer | Format | Consumers |
|---|---|---|---|
| `state/status/_system-health.json` | `system-health.py` (sweeper) | JSON schema_version:2 with `need_attention[]` + `groups{}` | Helm dashboard (Cron tab + front page); `health-deadman-check.sh` (mtime probe); load_prev_attention() dedup on next sweep |
| `state/health.jsonl` | `health_invariants.py` (append-only) | One JSON line per run (see struct above) | Ground-truth audit log; survives if tiles lie; human-readable history of invariant pass/fail per machine |
| `state/status/{desk}.json` | Per-desk `{desk}-health.py` producers | emit_status.py envelope (schema_version, pulse_job, stale_after_s, last_run, rc, status, summary) | `system-health.py` tile-staleness overlay; Helm per-desk tiles |
| ntfy notification | `notify-send.sh` (called by sweeper + health-deadman-check.sh) | push notification | Phone |

**Atomic write guarantee:** `_system-health.json` is written via `os.replace(tmp, OUT)` at
`system-health.py:614` — the tmp file is complete before the atomic replace, so Helm never reads a
partial feed.

---

### INTEROP SEAMS

| Verb | Other element | What flows / why |
|---|---|---|
| `TRIGGERS` | pulse-cron | Pulse dispatches `system-health-run.sh` every 300s — the sweeper IS a Pulse job, the health layer lives inside the thing it watches (by design; the out-of-band watcher is the escape hatch) |
| `READS` | pulse-cron | `_pulse-*.json` heartbeat files — the raw evidence the sweeper assesses for missed-run detection |
| `WRITES→` | helm | `_system-health.json` feed — Helm's Cron tab and front page render this; shape is frozen (schema_version:2) |
| `WRITES→` | (ground-truth log) | `state/health.jsonl` — append-only invariant record; survives tile lies; not consumed by any UI today |
| `READS` | egress-allowlist-wall | `guard_egress.sh` presence is one of the four critical hooks asserted by Invariant 1; tampering detected by Invariant 2 |
| `READS` | hook-plane | All guard hook files in `system/hooks/guard_*.sh` — Invariant 1 checks presence; Invariant 2 checks git-committed state |
| `READS` | sentinel | `state/status/sentinel.json` tile consumed by `sentinel_fold()` in the sweeper; Sentinel DANGER escalated to `need_attention[]`; a `CLEAR` tile yields an `UP` row so the Hospital gets an `OK` finding that supersedes the prior DANGER (since 2026-08-21 — before that, CLEAR produced nothing and the DANGER finding lingered until SILENT) |
| `READS` | security-ingest-gate | `desk-registry.yaml` `reads_external` field — Invariant 5 / drift-cop coverage check (when `INGEST_COVERAGE_FLAG=on`) |
| `COMPLEMENTS` | sentinel | Sentinel detects INBOUND injection; health-invariants detects SUBSTRATE failure — parallel, non-redundant |
| `CHAINS` | archivist | sweeper spawns `archivist-placements.py` + `archivist-lean.py` as side-effects post-sweep (decoupled + graceful) |
| `READS` | grand-central | ~~`state/primary-machine` — lead-machine detection in `system-health-run.sh` and `_current_lead()`~~ **⚠ CORRECTED 2026-08-24: neither exists — `system-health-run.sh` reads no such marker and `system-health.py` has no `_current_lead()`, verified this session (see COMPONENT A above).** |
| `SYNCS` | (desk-health producers) | `FRESH_TILES` and `assess_registry()` must stay in sync with the desk registry when new desks are added |

---

### GAPS

These are documented fail-open conditions or known design limitations. They inform the `·gap` qualifier
on this element's label and map entry.

**GAP-1: `FRESH_TILES` is a residual shadow desk-list (`system-health.py:40–44`).**
The `DESKS` tuple was de-shadowed (derived from `desk-registry.yaml`), but `FRESH_TILES` — the
job→desk mapping used for tile-staleness lookup — is still hand-maintained. A new desk's
tile-freshness won't be auto-watched until someone manually adds it. Recorded in `debt-ledger.md` as
`[FRESH-TILES-SHADOW]` (`state:monitoring`, `owner:organism`). This is a maintenance gap, not a
safety posture question — the sweeper will not false-green on a new desk (it'll miss the tile-stale
overlay, but the heartbeat check still fires). `[provisional]`

**GAP-2: Invariant 4 (heartbeats) fires BROKEN when a machine is legitimately offline.**
The sweeper has lead-aware suppression for hardware-pinned jobs (`EXPECTED-ABSENT` state), but
`health_invariants.py:Invariant4` has no equivalent. When a machine is legitimately offline (e.g., traveling),
`integrity:heartbeats` fires as a persistent BROKEN in `_system-health.json`. This is a false-alarm
for a known non-emergency. Live example: a machine stale 469.8h as of 2026-07-24. No suppression
mechanism exists in the current code. UNVERIFIED whether a planned fix is in the backlog.

**GAP-3: `health-deadman-check.sh` launchd plist template is absent from the clone.**
`system/templates/launchd/ai.lifehack.health-deadman.plist` does not exist (confirmed 2026-07-24).
The pulse-config.md launchd manifest (`pulse-config.md:347`) lists `ai.lifehack.health-deadman |
<machine> | ai.lifehack.health-deadman.plist` but the plist template is not in the clone. Whether it is
installed on the second machine locally is UNVERIFIED from this machine. The script
(`health-deadman-check.sh`) IS clone-resident and canonical — only the installer artifact is missing
from the template store.

**GAP-4: `system-health.py` has grown to ~640 lines and spawns 4 subprocesses per cycle.**
`[SYSTEM-HEALTH-CREEP]` in `debt-ledger.md` (`state:monitoring`, `owner:organism`): `sentinel_fold`
+ `assess_registry` + inline `security-health`/`archivist-placements`/`archivist-lean` spawns are
folded into one sweep. The comment "Health eating the Archivist's job" captures the scope concern.
This is a leanness debt item, not a correctness gap.

**GAP-5: `_security.json` tile freshness is governed only by system-health.py sweep frequency.**
`security-health.py` has `emit_mode: "manual"` and no dedicated Pulse slot — the Helm Security tab
tile is only refreshed when the sweeper runs. If the sweeper degrades, the Security tile goes stale
with no independent freshness guard. Cross-reference: see `sentinel.md` GAP-3.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** answer "is Lifehack actually running?" — not just "did the last job show green?" The
founding doctrine (2026-06-18 council): assume broken until proven healthy. Every check defaults to
BROKEN on its own error; an invariant that cannot run is a RED, never a silent pass. The out-of-band
dead-man's switch exists because the sweeper cannot watch itself from inside the thing it watches.

**Current state → LIVE·gap [provisional]:** the five founding invariants (hooks present, guards
untampered, clone fresh, both machines heartbeating, coverage complete) all run and append to
`state/health.jsonl` on every sweep; the sweeper's missed-run detection and the out-of-band launchd
dead-man's-switch are both live and have caught real failures. The `·gap` is earned: Invariant 4
(heartbeats) has no lead-aware suppression for a machine that is legitimately offline (e.g.
traveling) — it fires a persistent false BROKEN, unlike the sweeper's own `EXPECTED-ABSENT` state for
hardware-pinned jobs (GAP-2). `_security.json` freshness also rides entirely on the sweeper's own
cadence with no independent guard (GAP-5).

**TARGET:** add lead-aware suppression to Invariant 4 for a known-offline machine (GAP-2); de-shadow
`FRESH_TILES` the same way `DESKS` was derived from the registry (GAP-1, `[FRESH-TILES-SHADOW]`);
confirm the `health-deadman-check.sh` launchd plist is actually installed on the second machine, since the
template is absent from the clone (GAP-3); trim `system-health.py`'s growing scope before it accretes
further (GAP-4, `[SYSTEM-HEALTH-CREEP]`).

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)
- **maturity_label:** LIVE·gap [provisional]
- **check_detail:** "pending label_checker.py"
