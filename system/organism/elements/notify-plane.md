---
element: notify-plane
title: "notify-plane — element detail (ground/base altitude)"
subsystem: alerting
altitude: base
record_type: organism-element
maturity_label: LIVE [provisional]
generated_from:
  - system/tools/notify-send.sh
  - system/tools/notify-governor.py
  - system/notify-config.sh
  - system/tools/pulse.sh
  - system/tools/system-health.py
  - system/tools/health-deadman-check.sh
  - system/tools/marc-sensor.py
  - system/tools/marc-deadman.py
  - shared/tools/sentinel_response.py
  - system/tools/ingest-run.lib.sh
  - system/tools/archivist-run.lib.sh
  - system/tools/clair-coaching.py
  - system/tools/marc-voice-read.py
  - system/tools/planning-diary-run.sh
  - system/tools/email-summary-freshness-run.sh
  - system/tools/ingest_coverage.py
  - state/debt-ledger.md (known-issues sweep)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# notify-plane — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#notify-plane ; ground truth → the live artifacts (generated_from)**
>
> **One-line:** the single, governor-gated outbound push channel — every Lifehack alarm that reaches the
> user's phone passes through here and nowhere else.
>
> **⛔ NOT HERE — the donor paths this element names that do not exist in this repository, and are not
> owed.** `system/tools/marc-sensor.py`, `system/tools/marc-deadman.py`, `system/tools/marc-voice-read.py`
> and `system/tools/clair-coaching.py` are personal-desk tools, excluded from the migration — desk. The
> plane's own parts moved: `system/tools/notify-governor.py` ships here as
> `shared/notify/notify-governor.py`, and `shared/tools/sentinel_response.py` ships here as
> `shared/gate/sentinel_response.py`. `system/notify-config.sh` is not shipped at all — topic and server
> resolve from the reader's own `$HOME/.config/lifehack/ntfy-topic`, deliberately outside this repository.
> `state/debt-ledger.md` is the reader's own file under their gitignored notes root, never committed.
>
> **⚠ ADDED 2026-08-27, lb2-ops-comms.md claims 21/24 — one more path this section should have caught:**
> `system/tools/notify-send.sh` ⛔ moved — cited in generated_from above and throughout this file but
> does not exist at that path — the live file is `shared/notify/notify-send.sh`, alongside
> `shared/notify/notify-governor.py`. Confirmed live: `--max-time 10` and every other cited line-number
> behavior below reproduced correctly once read from the real path; only the path itself was stale. AND: the
> `NOTIFY_DAILY_CAP=0 (UNLIMITED, live config)` claim below (from the nonexistent `notify-config.sh`) is
> FALSE as a live fact — with no such file to source, the actually-live `DAILY_CAP` is the governor's own
> code default of **3** (`NOTIFY_DAILY_CAP` env var unset by default). The doc's own already-present
> correction that `notify-config.sh` isn't shipped is the accurate half; the specific "overridden to 0" body
> claim two sections down is not.

---

## AUTHORED   (human-only)

### TRIGGER

Any Lifehack component (cron job, desk runner, health monitor, sentinel scan, deadman watcher) that needs
to reach the user's phone calls `notify-send.sh`. There is no direct `curl` path to ntfy and no direct
alternative push channel — every outbound push is forced through this script, which in turn calls
`notify-governor.py` for an ALLOW/SUPPRESS decision before any network contact.

Callers as of 2026-07-24 (file:line, live code verified):

| Source | File | Priority |
|---|---|---|
| Pulse — no-lead-machine nag | `system/tools/pulse.sh:127` | critical |
| Pulse — circuit-breaker trip | `system/tools/pulse.sh:207` | normal (default) |
| Ingest-run.lib — no-lead preflight | `system/tools/ingest-run.lib.sh:71` | critical |
| System-health sweeper — newly-attention jobs | `system/tools/system-health.py:624` | normal or critical |
| Health deadman — sweeper itself gone silent | `system/tools/health-deadman-check.sh:33` | critical |
| Marc sensor — marc alert condition | `system/tools/marc-sensor.py:151` | (UNVERIFIED — line confirmed, priority not read) |
| Marc deadman — marc-sensor gone silent | `system/tools/marc-deadman.py:45` | critical |
| Sentinel — scan finds an issue | `shared/tools/sentinel_response.py:236` | critical |
| Archivist runner — archivist completion buzz | `system/tools/archivist-run.lib.sh:114` | normal |
| Clair desk tool | `system/tools/clair-coaching.py:27` | (UNVERIFIED — ref confirmed, call context not read) |
| Marc voice-read — push readable brief | `system/tools/marc-voice-read.py:41` | (UNVERIFIED — ref confirmed, call context not read) |
| Cal diary runner — check-in ready | `system/tools/planning-diary-run.sh:8` | (UNVERIFIED — comment only, not call read) |
| Email-summary freshness | `system/tools/email-summary-freshness-run.sh:63` | (UNVERIFIED — comment only, not call read) |
| Ingest coverage | `system/tools/ingest_coverage.py:40` | (UNVERIFIED — ref confirmed, call context not read) |

---

### NOTIFY PATH (ntfy)

**Transport: `ntfy.sh` (HTTPS POST, TLS in transit).**

`notify-send.sh` (lines 92–99) sends via:
```bash
curl -sS --max-time 10 "${HDRS[@]}" -d "$MESSAGE" "$SERVER/$TOPIC"
```
- `--max-time 10` is an explicit circuit-breaker: a hung network can never wedge a cron job.
  (`notify-send.sh:91` comment: "a hung network must never wedge a cron job.")
- Server: `NTFY_SERVER` from config, defaulting to `https://ntfy.sh` (`notify-send.sh:57`).
- Topic: `NTFY_TOPIC` is resolved at RUNTIME and is never a committed literal — env var `NTFY_TOPIC` first,
  otherwise the per-user file `$HOME/.config/lifehack/ntfy-topic` (path overridable via `NTFY_TOPIC_FILE`);
  still empty → fail-loud exit 2 with setup instructions, never a silent no-op (`notify-send.sh:60–71`).
  The topic IS a shared secret — anyone who knows the string can read every push sent to it — so it is
  deliberately held outside the repo and is never printed, not in the success line (`:105`) nor in the
  dry-run line (`:96`), which prints `<your topic, not printed>` in its place.
- Priority: `NTFY_PRIO=3` (default / "default" ntfy level) for `--priority normal`;
  `NTFY_PRIO=5` (urgent) for `--priority critical`. (`notify-send.sh:75`)
- Optional headers: `Title`, `Tags`, `Click` (the Drive link, `--url`), `Markdown: yes` (`--markdown`).

**Security posture:** ntfy.sh is TLS-encrypted in transit but NOT end-to-end — the relay server can read
message bodies. Mitigation (from `notify-config.sh:18–21`): (a) reserved topic, (b) `--message` is a
TEASER only — sensitive content (names, dollar amounts, details) goes behind `--url` (a login-gated Drive
link, never in the push body), (c) outbound-only adds zero inbound attack surface.

**Config-resolution order** (`notify-send.sh:54–58`): env var `NTFY_TOPIC` / `NTFY_SERVER` → sourced
`notify-config.sh` → fail-loud exit 2 if topic still empty (never silently no-ops).

**CODE_ROOT resolution** (`notify-send.sh:30`): script uses its own repo root, not a hardcoded Drive path.
This is the "dormant fix" (2026-06-18): ensures the governor and config are always read from the git clone,
never from a stale Drive copy that may have drifted.

**Dry-run mode** (`notify-send.sh:84–89`): `NOTIFY_DRY_RUN=1` prints the would-be POST without any network
contact. Used for setup verification.

---

### THE GOVERNOR — rate / dedup / quiet-hours logic

`notify-governor.py` is called synchronously before any curl send. Exit 0 + `ALLOW` on stdout → send
proceeds and is recorded. Exit 1 + `SUPPRESS: <reason>` on stderr → send is skipped (not an error — exit 0
from `notify-send.sh:69`).

**State store:** `/tmp/lifehack-notify-state.json` (`notify-governor.py:31`). Volatile by design — a reboot
resetting rate counters is acceptable (worst case: one extra nudge). File-level exclusive lock
(`fcntl.LOCK_EX`, line 89) serializes concurrent jobs so two Pulse ticks can't both slip past the cap.
Atomic write via `.tmp` + `os.replace` (line 70–71) prevents torn reads.

**Decision order for a `priority: normal` push** (all three checks run in order; first failure suppresses):

1. **Dedup** (`notify-governor.py:100–107`): compute `sha256(source + "\x00" + message)`. If an identical
   hash appears in `state["sent"]` within the last `DEDUP_HOURS` (default 24h, `line 35`) → SUPPRESS with
   reason `duplicate within 24h`.

2. **Quiet hours** (`notify-governor.py:119–128`): read local clock hour. If `in_quiet_hours(hour)` →
   SUPPRESS. Window: `[NOTIFY_QUIET_START, NOTIFY_QUIET_END)` (defaults: 22:00–07:00 local). Window may
   wrap midnight (e.g. 22→7). (`notify-governor.py:50–56`)

3. **Per-source daily cap** (`notify-governor.py:130–138`): count sends from `source` within last 24h. If
   `count >= DAILY_CAP` → SUPPRESS. `DAILY_CAP` defaults to `3` in governor code (`line 34`) but ~~is
   **overridden to `0` (UNLIMITED) in `notify-config.sh:33`** — cap disabled as of 2026-06-02 per user
   decision ("re-add if buzzes get annoying"). **Live behavior: daily cap is off.**~~
   [CORRECTED 2026-08-27, lb2-ops-comms.md claim 24 — `notify-config.sh` does not exist anywhere in the
   repo (`find`: 0 hits), so it cannot override anything. Live behavior with `NOTIFY_DAILY_CAP` unset: the
   code default of **3 stands and is enforced** — a 2nd identical-source call within 24h was observed
   SUPPRESSED live. The cap is NOT off.]

**Decision order for a `priority: critical` push** — different path, fewer gates:

1. **Dedup — short floor** (`notify-governor.py:100–107`): same hash check but window is
   `CRITICAL_DEDUP_HOURS` (default 1h, `line 39`) — a same-day repeat DANGER still buzzes; a stuck
   source can't flood every 5-min tick.

2. **Critical burst-coalesce** (`notify-governor.py:110–117`): within `CRITICAL_BURST_MINUTES` (default
   10 min, `line 47`) of a prior critical from the SAME source (any message), suppress. Rationale: one
   scan matching 5 patterns fires 5 distinct-message criticals; the push is a doorbell ("go look"), not
   the payload — every event is still in the ledger/tile. After the window, a genuinely separate incident
   still rings.

3. **Quiet hours: SKIPPED** (`notify-governor.py:119` — the `if not critical:` guard). Critical pushes
   bypass quiet hours entirely.

4. **Daily cap: SKIPPED** (same `if not critical:` guard at line 119). Critical pushes bypass the cap.

**Record on ALLOW** (`notify-governor.py:141`): the entry `{ts, source, hash, crit}` is appended to
`state["sent"]`. The `crit` flag lets the burst-coalesce count only critical sends (it's source-keyed,
ignores message).

**State pruning** (`notify-governor.py:94–95`): at the top of every decision, entries older than
`max(DEDUP_HOURS, 24) * 3600` are pruned. With defaults (DEDUP_HOURS=24), this is 24h.

**Env-var tuning table** (all optional; four of the seven vars are exported by `notify-send.sh:65` (QUIET_START, QUIET_END, DAILY_CAP, DEDUP_HOURS); the remaining three (NOTIFY_CRITICAL_DEDUP_HOURS, NOTIFY_CRITICAL_BURST_MINUTES, NOTIFY_STATE_FILE) must be set in the caller's environment before invoking `notify-send.sh`):

| Env var | Default | Meaning |
|---|---|---|
| `NOTIFY_QUIET_START` | `22` | Quiet window start hour (local) |
| `NOTIFY_QUIET_END` | `7` | Quiet window end hour (local) |
| `NOTIFY_DAILY_CAP` | `3` (governor code default; live and enforced — `notify-config.sh` does not exist to override it [corrected 2026-08-27, claim 24]) | Max sends/source/24h; 0 = unlimited |
| `NOTIFY_DEDUP_HOURS` | `24` | Normal-priority identical-msg suppression window |
| `NOTIFY_CRITICAL_DEDUP_HOURS` | `1` | Critical-priority dedup floor |
| `NOTIFY_CRITICAL_BURST_MINUTES` | `10` | Critical burst-coalesce window (source-keyed) |
| `NOTIFY_STATE_FILE` | `/tmp/lifehack-notify-state.json` | State store path |

---

### FALLBACK PATH

There is no warm fallback to a second push channel. If `curl` fails (network/timeout), `notify-send.sh`
exits 1 and logs `SEND FAILED — <curl error>` to stderr (`notify-send.sh:97–99`). Callers universally
discard this failure (shell callers (`pulse.sh`, `health-deadman-check.sh`, `archivist-run.lib.sh`) use `|| true`; Python callers (`sentinel_response.py`, `marc-sensor.py`, `marc-deadman.py`, `clair-coaching.py`, `marc-voice-read.py`, `ingest_coverage.py`) use `try/except` — all discard the failure). **A send failure is silent at the caller
level** — no secondary alarm, no retry, no local file fallback. The Helm dashboard (writing via
`system-health.py`) is the only complementary signal, but it is pull-based (requires the user to open it).

This is a **known design gap** — see GAPS section below.

---

### ENFORCEMENT

`notify-send.sh` is not hook-enforced. There is no hook in `settings.json` that blocks or routes
notification calls. Enforcement is **structural / by convention**: all callers in the codebase import the
path to `notify-send.sh` from their `CODE_ROOT` at runtime and call it via `bash "$NOTIFY …"`. There is no
secondary raw-curl path in any caller file reviewed. The governor is called unconditionally inside
`notify-send.sh` (line 66) — a caller cannot bypass it short of calling `curl` directly.

**No hooks registered for this element** in `settings.json` (verified: grep for "notify" returned no
results in settings.json hooks section).

---

### PORTS TOUCHED

| Port | Direction | What |
|---|---|---|
| `system/tools/notify-governor.py` | INTERNAL | Governor subprocess — called every send |
| ~~`system/notify-config.sh`~~ `shared/notify/notify-governor.py` | READ | ⚠ CORRECTED 2026-08-24: `system/notify-config.sh` does not exist on disk (`ls system/notify-config.sh` → No such file or directory, confirmed this session) — matches this doc's own banner above (L44), which already says the file "is not shipped at all." Quiet-hours and cap config actually live as env-var defaults inside `shared/notify/notify-governor.py` (`QUIET_START`/`QUIET_END`, ~L46–47; `DAILY_CAP`, ~L48); topic/server resolve from the reader's own `$HOME/.config/lifehack/ntfy-topic`, per the same banner. Values stated elsewhere in this doc (22:00–07:00 default window) are unchanged by this correction. |
| `/tmp/lifehack-notify-state.json` | READ + WRITE | Governor rate/dedup state (volatile) |
| `/tmp/lifehack-notify-state.json.lock` | WRITE | Exclusive lock for concurrent-safe R-M-W |
| `/tmp/notify-gov.$$` | WRITE (ephemeral) | Capture governor stderr reason |
| `https://ntfy.sh/<topic>` | OUT (network) | HTTPS POST — the phone push |

---

### INTEROP SEAMS

```
CHAINS     pulse               · pulse.sh is the primary scheduler caller; notifies on no-lead + circuit-breaker trip
CHAINS     system-health       · system-health.py calls notify-plane on newly-degraded jobs; critical on error-severity
CHAINS     health-deadman      · health-deadman-check.sh calls notify-plane if system-health itself goes silent
CHAINS     sentinel            · sentinel_response.py calls notify-plane (critical) on any scan hit; disableable via env
CHAINS     pulse-circuit-breaker · the breaker trip in pulse.sh fires notify-plane as its only outbound signal
CHAINS     marc-sensor         · marc-sensor.py calls notify-plane on marc alert conditions
CHAINS     marc-deadman        · marc-deadman.py calls notify-plane (critical) if marc-sensor goes silent
CHAINS     archivist           · archivist-run.lib.sh calls notify-plane on archivist completion
CHAINS     ingest-lib          · ingest-run.lib.sh calls notify-plane (critical) on no-lead-machine abort
SHARES     notify-governor     · governor is a sub-component of notify-plane, not a separate interop peer
```

---

### GAPS (documented fail-open conditions)

**GAP 1 — No fallback channel on send failure.** If `curl` fails (network down, ntfy outage), the failure
is logged to stderr but discarded by all callers (`|| true`). No secondary channel (email-to-self, local
sound, desktop notification) exists. A prolonged ntfy outage = blind user. Source: `notify-send.sh:96–99`
+ every caller's `|| true` pattern. Known, logged in `state/debt-ledger.md` (implied by AUTOPUSH-BREAKER
item: "chain verified by code-read only … not yet live-fired").

**GAP 2 — Governor state is volatile (`/tmp`).** A reboot or `/tmp` wipe resets all rate/dedup counters.
This is explicitly accepted by design (`notify-governor.py:13`): "worst case is one extra nudge." However,
an OS crash mid-incident followed by a reboot could cause a burst of previously-deduped alerts to re-fire.
No severity label — accepted design tradeoff.

**GAP 3 — AUTOPUSH circuit-breaker notify path live-unverified.** The chain
`git-autopush.sh → pulse.sh:207 (circuit-breaker notify) → [independently] system-health.py:624 (newly-degraded notify)` has been code-read but never live-fired
through 3 consecutive failures. Source: `state/debt-ledger.md` line tagged `[AUTOPUSH-BREAKER-LIVE-TEST]` (debt-ledger entry itself carries stale line numbers from when it was written).

**GAP 4 — Several caller call-contexts UNVERIFIED.** Priority/message for `clair-coaching.py`,
`marc-voice-read.py`, `planning-diary-run.sh`, `email-summary-freshness-run.sh`, `ingest_coverage.py` were
confirmed by ref, but the full call arguments were not read this session. Their priority routing (normal vs
critical) is therefore UNVERIFIED.

**GAP 5 — No auto-mute-after-false-alerts.** Intentionally deferred in v1 (`notify-governor.py:27`):
"needs a feedback channel ('that was a false alert') we don't have yet." A false-alarm-heavy incident
requires manual tuning (edit config, reset state).

---

### INTENT / CURRENT-VS-TARGET

**Purpose (standing):** provide ONE gated push channel so any component can alert the user without risking
spam, leaking sensitive content, or wedging a cron job on network issues. Alert-fatigue is the named
dominant failure mode (`notify-governor.py:3`).

**Current:** governor fully implements quiet-hours + dedup + critical-bypass + burst-coalesce. Daily cap
is deliberately disabled. Transport is single-channel ntfy. State is volatile. No hooks enforce call
routing.

**Target / known gaps:** a fallback channel on send failure is the open design fork (GAP 1 above). The
LuLu-egress integration (Sentinel tile + ntfy on suspect off-prem blocks) is logged in `debt-ledger.md`
line 224 as NOT BUILDING NOW (explicit, 2026-07-03). The auto-mute feedback channel is deferred.

---

## AUTO-COMPUTED   (machine-only — written by Feature 1.5 checker, not by hand)

```yaml
maturity_label: LIVE [provisional]
check_detail: ~
```
