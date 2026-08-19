---
element: sentinel
title: "sentinel — element detail (ground/base altitude)"
subsystem: security
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C4 silent-death — security-health has no Pulse slot; the monthly audit LaunchAgent was retired with no replacement"
generated_from:
  - shared/tools/sentinel_response.py
  - shared/tools/sentinel_ack.py
  - shared/tools/sentinel_quarantine.py
  - shared/tools/ingest_gate.py
  - system/tools/ingest-run.lib.sh
  - system/tools/sentinel-health.py
  - system/tools/sentinel-health-run.sh
  - system/tools/security-health.py
  - system/tools/system-health.py
  - agents/sentinel.md
  - system/reference/settings.json
  - system/pulse-config.md
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# sentinel — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#sentinel ; ground truth → the live artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the injection-verdict gate
> and security monitoring subsystem. The MIDDLE manual (`system/organism/manual.md`) carries only a
> one-line pointer here; the TIP (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **One-line:** classify every inbound scan finding as CLEAN / FLAG / DANGER; on DANGER, pause the
> source, push a phone alert, and reversibly quarantine the Gmail message — then write the result to
> an append-only event ledger and refresh the security dashboard tile.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).
>
> **⛔ NOT HERE — the donor paths this element names that do not exist in this repository, and are not
> owed.** The gate tools moved out of `shared/tools/` on the way over: `shared/tools/sentinel_response.py`,
> `shared/tools/sentinel_ack.py`, `shared/tools/sentinel_quarantine.py` and `shared/tools/ingest_gate.py`
> all shipped, and they live here as `shared/gate/sentinel_response.py`, `shared/gate/sentinel_ack.py`,
> `shared/gate/sentinel_quarantine.py` and `shared/gate/ingest_gate.py`. `state/status/sentinel.json` and
> `state/status/_security.json` are tiles written under the reader's own gitignored notes root —
> runtime-generated, created on first run, never committed. `system/reference/settings.json` is the
> donor's reference mirror of the harness settings and is not reproduced here; the live hook
> registrations are in `.claude/settings.json`. `/security-audit` is not a skill in this repository and
> never was, which is precisely what the T5 paragraph below says when it names it.

---

## AUTHORED   (human-only)

### MODES / TRIGGERS

Five distinct activation paths, each with a different caller and purpose:

**T1 — inline per-item gate (v1, zero live callers)**
Defined as `ingest_sentinel_check()` in `system/tools/ingest-run.lib.sh:231`. No desk `-run.sh`
calls this function — grep across all runner scripts returns zero results. Per note in
`ingest-run.lib.sh:260`: "NOTE (Window 5): no live \*-run.sh calls the per-item gate today — email
ingestion is gate-routed via email_convert.py (Window 3). This is the READY upgraded path for future
per-item runner gating; v1 stays for back-compat." Exit 2 = DANGER; exit 0 = FLAG or CLEAN. This
path is built but unreachable from live ingest jobs. `[gap — see GAP-2]`

**T2 — gate-routed per-item path (v2, the live path)**
`ingest_gate_check()` at `ingest-run.lib.sh:264` calls `shared/tools/ingest_gate.py`, which
internally invokes `sentinel_response.py` (actual subprocess invocation at `ingest_gate.py:113`;
`ingest_gate.py:44` is a path constant assignment, not an invocation). The live email path is
`email_convert.py → ingest_gate.gate()` — a direct Python import of the v2 module. The v2 path adds
provenance tagging, the `--flag-only` invariant for email (never DANGER), and the ENFORCE posture.
The email FLAG-floor runtime enforcement is at `ingest_gate.py:110` (lines 28-31 are docstring
describing the invariant, not enforcement code).

**T3 — Pulse tile recompute (periodic twin, sentinel-health.py)**
`system/tools/sentinel-health-run.sh` → `sentinel-health.py`. Pulse slot named `sentinel-health`,
registered in `system/pulse-config.md:291` with a poll interval of ~1800s (how often Pulse runs the
slot). The tile itself carries `stale_after_s=86400` (24h freshness window, set by
`sentinel-health.py:84` in the `emit_status()` call). Reads the
full `sentinel-events.jsonl` ledger and rewrites `state/status/sentinel.json` (the same tile shape
`sentinel_response.write_tile()` writes inline). Both writers use atomic `os.replace` → double-write
is harmless. This is the freshness path between ingestion runs (tile freshness window = 24h;
individual Pulse ticks ~1800s apart).

**T4 — security-health composition (manual / sweeper-triggered)**
`system/tools/system-health.py:567` invokes `subprocess.run(["python3", ".../security-health.py"],
...)` as a side-effect of the system-health sweep. `security-health.py` has `emit_mode: "manual"` and
`stale_after_s=1800` (set at `security-health.py:33`) but no dedicated Pulse slot — tile freshness
is governed by how often `system-health.py` sweeps, not a watcher. It reads `sentinel.json` and
folds it into `state/status/_security.json` (Helm's Security tab tile). `[gap — see GAP-3]`

**T5 — auditor subagent (on-demand / MANUAL BY DESIGN)**
`agents/sentinel.md` is a read-only LLM subagent with name "sentinel". Invoked by the user directly
by agent name (not via a `/security-audit` slash command — no such trigger exists in the agent file).
It is an **11-item checkbox checklist across four sections** — *Secret exposure* (3) · *Secret-storage
permissions* (2) · *Hook and config integrity* (3) · *Config inventory* (3) — each box independently
skippable with a stated reason, where skipping is explicitly NOT the same as passing and the summary
must say which happened. Supports a `scope=` parameter: `scope=secrets` (the two secret sections),
`scope=inventory` (the config-inventory section), `scope=hooks` (the hook/config-integrity section),
no scope = the whole checklist (default). Writes an audit `.md` to `{notes root}/system/logs/`.
**Cadence is MANUAL BY DESIGN, not a gap** — no scheduler is wired to this file and none is proposed;
run it by hand after wiring a new external-content channel, after adding a desk, or for a current
read. That matches the mechanical half (`sentinel_response.py` / `sentinel_ack.py`), which
`system/security-canon.md` already documents as manual-trigger-by-construction.

⭐ **THE COUNT CORRECTION — Sentinel is THREE things, not five.** An earlier draft asserted *"Sentinel
is FIVE things, not one"* and then enumerated only three before flagging itself for a disambiguation
that never happened; the claim was carried forward unverified. Measured and resolved at build time
against what actually exists: **(1)** this read-only manual audit file — a checklist, not a guard: it
cannot block anything, only report; **(2)** the mechanical gate — `shared/gate/sentinel_response.py` +
`sentinel_quarantine.py` + `sentinel_ack.py`, the actual enforcement teeth, running downstream of the
ingest/read adapters and quarantining what they flag, live independent of the audit file; **(3)** the
health tiles — `system/tools/sentinel-health.py` + `sentinel-health-run.sh`, status reporting, not
protection. Three. Nothing is reserved in advance for a fourth or fifth; if a future audit finds a
real fourth thing it gets added explicitly. ⚠ This does NOT collapse the **five activation paths**
(T1–T5) enumerated in this section — those are five distinct CALLERS of the subsystem, a different
taxonomy from the three COMPONENTS, and they remain five.

---

### FULL HAND-OFF CHAINS

---

#### Chain A — ingest item, v1 gate path (FLAG / DANGER) [zero live callers — back-compat reference only]

```
ingest harness desk -run.sh  [actor]
  -> ingest_sentinel_check()  [ingest-run.lib.sh:231]
     -> Bash: python3 shared/tools/sentinel_response.py --source <job> --item <id>  [port: subprocess]
        stdin: findings JSON from scan_for_injection / email_convert.py  [port: pipe]

        sentinel_response.py:main()  [actor]
          -> parse_findings()  [internal: shared/tools/sentinel_response.py:120]
          -> fingerprint_for(source, labels)  [internal: sentinel_response.py:73]

          == CLEAN path (no labels) ==
             print("CLEAN"); exit 0  → caller continues

          == FLAG path (flag-class labels only, or --flag-only + danger-class label) ==
             load_acked_fingerprints()
               [store: DRIVE/system/logs/sentinel-acked-fingerprints.json, read]
               [sentinel_response.py:84 — fail-safe: any read error → empty dict, never hides]
             auto-set disposition if fingerprint in acked set
               [honor: DANGER never auto-suppressed — sentinel_response.py:79]
             log_event(..., verdict="flag", ...)
               [store: DRIVE/system/logs/sentinel-events.jsonl, append — sentinel_response.py:185]
             write_tile()
               [store: DRIVE/state/status/sentinel.json, atomic os.replace — sentinel_response.py:182]
             exit 0  → caller continues

          == DANGER path (danger-class label + --flag-only NOT set) ==
             log_event(..., verdict="danger", disposition="unreviewed", ...)
               [store: DRIVE/system/logs/sentinel-events.jsonl, append — sentinel_response.py:185]
             write_tile()  [store: DRIVE/state/status/sentinel.json, atomic os.replace]
             pause_source(source)
               [store: ~/.config/lifehack/sentinel-paused-sources, append-dedup; machine-local]
               [sentinel_response.py:199 — un-pause is human-only]
             notify_danger(source, labels, reader_verdict)
               [honor: SENTINEL_NOTIFY_DISABLE=1 → skip silently  ·gap — sentinel_response.py:229]
               [honor: reader_verdict=="BENIGN" → suppress push — sentinel_response.py:223]
               -> Bash: notify-send.sh --priority critical  [port: subprocess → NTFY push, outbound]
             quarantine_message(message_id)
               [honor: SENTINEL_QUARANTINE_DISABLE=1 → skip silently  ·gap — sentinel_response.py:249]
               [honor: --message-id absent (non-Gmail item) → no action]
               -> Bash: sentinel_quarantine.py --message-id <id>  [port: subprocess]
                  -> gws gmail users labels create + messages modify
                     [port: gws API → Gmail label, reversible]
             exit 2  → caller HALTS this item

     ingest_sentinel_check():  rc check  [ingest-run.lib.sh:234-249]
       rc==2: _sentinel_log() → DRIVE/system/logs/sentinel-events.jsonl  [DUPLICATE entry on DANGER v1]
              halt item
       rc==0 + output: _sentinel_log() + continue
```

NOTE on the inline write_tile() (binary vs ternary): `sentinel_response.write_tile()`
(`sentinel_response.py:138-182`) emits status as `"DANGER"` if `active_danger` else `"CLEAR"` only
— it does NOT emit `"FLAGS"`. The Pulse twin (`sentinel-health.py:69`) emits `"DANGER"` /
`"FLAGS"` / `"CLEAR"`. Between Pulse ticks, the tile written by Chain A underreports active FLAG
events. `[gap — see GAP-7]`

---

#### Chain B — Pulse tile recompute (T3)

```
pulse.sh (cron, every ~1800s)  [actor: cron/pulse]
  -> sentinel-health-run.sh  [actor: system/tools/sentinel-health-run.sh]
     -> ingest_acquire_lock("sentinel-health")  [gate: mkdir; stale-steal at 25m]
     -> python3 sentinel-health.py  [actor: system/tools/sentinel-health.py]
        -> reads DRIVE/system/logs/sentinel-events.jsonl  [store: read, full scan — sentinel-health.py:41]
        -> emit_status(OUT, ..., stale_after_s=86400, ...)
           [sentinel-health.py:84 — tile freshness window = 86400s / 24h]
           -> DRIVE/state/status/sentinel.json  [store: atomic write via emit_status.py]
```

`sentinel-health.py:69` emits ternary status: `"DANGER"` / `"FLAGS"` / `"CLEAR"`. The inline writer
(`sentinel_response.write_tile()`) emits binary: `"DANGER"` / `"CLEAR"` only. Between Pulse ticks
(~1800s poll interval), the tile underreports active FLAG events. `[gap — see GAP-7]`

---

#### Chain C — Security tile composition (T4)

```
system-health.py:567  [actor: sweeper, manual-triggered]
  -> subprocess security-health.py  [actor: system/tools/security-health.py]
     -> _settings_text()  [reads ~/.claude/settings.json — security-health.py:43]
     -> read_sentinel()   [reads DRIVE/state/status/sentinel.json — security-health.py:100]
     -> hook_active("ingest_gate_enforce", settings_text)  [gate: file-present AND settings.json registration — security-health.py:51]
     -> hook_active("block_primary_calendar", settings_text)  [gate: same pattern]
     -> tool_present checks  [gate: os.path.isfile for safe_fetch.py, email_convert.py, sanitize.py]
     -> compose()  [security-health.py:118]
        -> DRIVE/state/status/_security.json  [store: atomic os.replace — security-health.py:207]
```

`security-health.py:184`: absent `sentinel.json` → downgrades overall status to `FLAGS` (green-illusion
protection). `security-health.py:51-56`: `hook_active()` checks both file presence AND settings.json
registration — both must be true for the hook to count as active. This tile is advisory (drives Helm
Security tab tone); it does NOT block. `stale_after_s=1800` in `_security.json` but no dedicated Pulse
slot — freshness is not independently guaranteed. `[gap — see GAP-3]`

---

#### Chain D — Human acknowledgment (operator, manual)

```
operator  [human]
  -> python3 sentinel_ack.py [--fp|--real|--reviewed] [--source] [--ts] [--fingerprint] [--remember] [--list] [--undo]
     -> _load()  [reads DRIVE/system/logs/sentinel-events.jsonl — sentinel_ack.py]
     -> mutates disposition field in-memory (false-positive / reviewed / real-attack)
     -> atomic rewrite: sentinel-events.jsonl.tmp → os.replace  [store: atomic write]
     -> optional: _save_store()
        -> DRIVE/system/logs/sentinel-acked-fingerprints.json  [store: atomic write]
     -> sr.write_tile()  [sentinel_ack.py imports sentinel_response as sr]
        -> DRIVE/state/status/sentinel.json  [store: atomic refresh]
```

`sentinel_ack.py` imports `sentinel_response as sr` directly — shares path constants `LOG`, `TILE`,
`ACKED_FP` (`sentinel_response.py:37-70`). This is the sole path for un-pausing a source (human
edits `sentinel-paused-sources` directly; no tool writes `--` into it to remove an entry).

---

#### Chain E — Security-audit LLM subagent (T5, on-demand)

```
user -> invokes the "sentinel" subagent by name  [human]  (scope=secrets|inventory|hooks, or none = all)
  -> agents/sentinel.md  [subagent: read-only LLM, no tool writes]
     -> reads: this repo's own tree (system/ shared/ .claude/ agents/ desks/*/), resolved from the
               repo root — never a hardcoded home directory
               .claude/settings.json, .claude/agents/**, .claude/skills/**
               ~/.claude.json (global config: embedded creds + MCP inventory), if present
               ~/.config/lifehack/ (permissions + age only, NEVER values)
               the notes root (resolved the way shared/brain_root.py resolves it) — permissions + age
               only, and permission-UNVERIFIABLE if it is cloud-synced
               system/hooks/ (inventory, permissions, core-enforcement-set presence)
     -> SECTION 1 (3 boxes): secret exposure scan — structural JWT / secret-named JSON keys in
                             settings.json (error) and every other .json (warning); long base64-like
                             runs in .md files (inventory note, not a finding)
     -> SECTION 2 (2 boxes): secret-storage permissions (expects 700 dir, 600 files; flags >90-day-old
                             files) + the LOCAL SECRETS CAVEAT — POSIX bits under a cloud-synced notes
                             root are reported as permission-UNVERIFIABLE rather than asserted as a pass
     -> SECTION 3 (3 boxes): hook and config integrity — the named core enforcement set is present in
                             system/hooks/ (error if any is missing); settings.json denies Edit on
                             system/hooks/** + settings.json + agents/** + skills/**; plus a standing
                             note that permissions.deny is not OS-level protection (recorded every run)
     -> SECTION 4 (3 boxes): config inventory — MCP surface (transport risk-graded stdio-local /
                             http-local / networked + data sensitivity), root permissions, per-desk
                             permissions read from the desk registry or globbed, never hardcoded
     -> redaction rule: NEVER echo a detected secret value  [honor — agents/sentinel.md:54-65; no mechanical enforcement  ·gap]
     -> writes: DRIVE/system/logs/sentinel_{YYYY-MM-DD}_{HHmm}_audit.md  [store: write]
```

---

### PORTS TOUCHED

**Read (hook input):**
- PreToolUse stdin JSON (via ingest harness Bash calls) — not sentinel-specific; flows through the
  `ingest_gate_enforce.sh` precheck before the sentinel invocation.

**Read (operational data):**
- `DRIVE/system/logs/sentinel-events.jsonl` — the full event ledger (read by `sentinel-health.py`,
  `sentinel_ack.py`, `security-health.py` via `sentinel.json`).
- `DRIVE/system/logs/sentinel-acked-fingerprints.json` — human-curated FP fingerprints.
- `DRIVE/state/status/sentinel.json` — the tile (read by `security-health.py`, Helm).
- `~/.claude/settings.json` — read by `security-health.py:_settings_text()` (`security-health.py:43`).

**Written by sentinel's pipeline:**
- `DRIVE/system/logs/sentinel-events.jsonl` — append (inline `log_event()`,
  `sentinel_response.py:185`); atomic rewrite (`sentinel_ack.py`); also appended by
  `enforce_egress_allowlist.py` on block events.
- `DRIVE/state/status/sentinel.json` — atomic `os.replace` by three writers:
  `sentinel_response.write_tile()` (`sentinel_response.py:182`);
  `sentinel-health.py` via `emit_status()` (`sentinel-health.py:84`);
  `sentinel_ack.py` via `sr.write_tile()`.
- `DRIVE/state/status/_security.json` — atomic `os.replace` by `security-health.py:207`
  (Helm Security tab composition tile).
- `~/.config/lifehack/sentinel-paused-sources` — append-dedup by `pause_source()`
  (`sentinel_response.py:199`); machine-local; gate-read in `ingest_check_paused()`.
- `DRIVE/system/logs/sentinel-acked-fingerprints.json` — atomic `os.replace` by
  `sentinel_ack._save_store()`.
- `DRIVE/system/logs/sentinel_{date}_{time}_audit.md` — write by `agents/sentinel.md` LLM subagent.

**No Write/Edit tool matchers registered for sentinel's stores.** All writes are Python `open()` /
`os.replace()` inside Bash subprocess calls — they bypass the Claude Write/Edit tool and therefore
bypass `guard_write_paths.sh` and `guard_canon_write.sh`. Those hooks fire if Claude's Write tool
targets those paths but the pipeline never uses the Write tool for these destinations. (Inherited
system-class bypass — not listed as a `·gap` per §8.4b SYSTEM-CLASS GAP EXCLUSION since blast-radius
does not materially exceed system baseline.)

---

### OUTCOME

Every item entering the ingest pipeline receives a verdict: CLEAN (pass silently), FLAG (log + tile,
caller continues), or DANGER (log + tile + pause source + phone push + Gmail quarantine, caller halts
this item). The verdict gate is synchronous and on-path — items cannot proceed past an unresolved
scan. A DANGER verdict triggers the minimum effective containment set while keeping every action
reversible: the source pause is a newline-append (human removes it manually); the Gmail label is
applied and removable; the NTFY push is best-effort (fail-open). The event ledger is append-only;
`sentinel_ack.py` rewrites dispositions in-place rather than appending corrections, keeping the log
compact and readable.

---

### GENERATED_FROM

`shared/tools/sentinel_response.py` · `shared/tools/sentinel_ack.py` ·
`shared/tools/sentinel_quarantine.py` · `shared/tools/ingest_gate.py` (v2 gate, live via email_convert.py import; direct per-item runner wiring pending) ·
`system/tools/ingest-run.lib.sh` (ingest_sentinel_check + ingest_check_paused) ·
`system/tools/sentinel-health.py` · `system/tools/sentinel-health-run.sh` ·
`system/tools/security-health.py` · `system/tools/system-health.py:567` · `agents/sentinel.md` ·
`system/reference/settings.json` · `system/pulse-config.md`.

---

### STORES TOUCHED (complete list)

| Store | Path | Writer(s) | Reader(s) | Access |
|---|---|---|---|---|
| Event ledger | `DRIVE/system/logs/sentinel-events.jsonl` | `sentinel_response.log_event()` (append, `sentinel_response.py:185`); `_sentinel_log()` in `ingest-run.lib.sh:241` (append, duplicate on DANGER v1); `sentinel_ack.py` (atomic rewrite); `enforce_egress_allowlist.py` (append on block) | `sentinel-health.py`, `sentinel_ack.py`, `security-health.py` (via tile), `ingest_coverage.py` | append / atomic-rewrite |
| Security tile | `DRIVE/state/status/sentinel.json` | `sentinel_response.write_tile()` (binary: DANGER/CLEAR only, `sentinel_response.py:170`); `sentinel-health.py` via `emit_status()` (ternary: DANGER/FLAGS/CLEAR, `sentinel-health.py:69`); `sentinel_ack.py` | `security-health.py`, Helm | atomic `os.replace` |
| Security composition tile | `DRIVE/state/status/_security.json` | `security-health.py` (`security-health.py:207`) | Helm Security tab | atomic `os.replace` |
| Pause list | `~/.config/lifehack/sentinel-paused-sources` | `sentinel_response.pause_source()` (`sentinel_response.py:199`) | `ingest_check_paused()` (`ingest-run.lib.sh:103`) | append-dedup; machine-local |
| Acked fingerprints | `DRIVE/system/logs/sentinel-acked-fingerprints.json` | `sentinel_ack._save_store()` | `sentinel_response.load_acked_fingerprints()` (`sentinel_response.py:84`) | atomic `os.replace` |
| Audit logs | `DRIVE/system/logs/sentinel_{date}_{time}_audit.md` | `agents/sentinel.md` (LLM subagent) | human | write |
| Egress block events | `DRIVE/system/logs/sentinel-events.jsonl` | `enforce_egress_allowlist.py` (best-effort append on block) | `sentinel-health.py`, `security-health.py` | append |

---

### GATES AND ENFORCEMENT POINTS (the honest map)

#### Real + hook-enforced

**1. `ingest_gate_enforce.sh`** (PreToolUse Bash/WebFetch/WebSearch/Read,
`settings.json:211,221,231,241`) `[hook]` — the unified inbound gate that FORCES all external reads
through the sanitizer stack BEFORE sentinel ever sees a findings JSON. Sentinel is downstream of this
hook, not a replacement for it. Exit 2 = block. Fail-CLOSED on unparseable input. This is what makes
the sentinel-verdict gate meaningful: the hook guarantees no raw external content bypasses the scan.

**2. `ingest_check_paused()` source-pause gate** (`ingest-run.lib.sh:103`) `[skill]` — reads
`~/.config/lifehack/sentinel-paused-sources` before every ingest run; exits 0 (skips) if the source
is listed. The DANGER containment effect persists across runs until a human manually removes the
entry. No tool can un-pause a source; the only removal path is human editing the file. This is the
auto-containment gate.

**3. Acked-fingerprint hard safety** (`sentinel_response.py:79, 287`) `[skill]` — FLAG-class
findings matching a human-acked fingerprint auto-retire (`disposition` set to stored value, typically
"false-positive"). HARD SAFETY: DANGER verdicts are NEVER auto-suppressed by an acked fingerprint
regardless of fingerprint match — `disposition` stays "unreviewed" and surfaces.
(`sentinel_response.py:287` — the DANGER path never calls `load_acked_fingerprints()` and always
logs `disposition="unreviewed"`.)

**4. `sentinel_response.py` DANGER_LABELS classifier** (`sentinel_response.py:46-66`) `[skill]` —
exit 2 = DANGER; exit 0 = FLAG/CLEAN. Classification is set-membership against `DANGER_LABELS`
(instruction-override, authority-impersonation, exfiltration class, encoding attack directive). The
set was precision-retooled 2026-07-14 (SEC-BUZZ-VERDICT) to drop FP-prone patterns (`system prompt
extraction` + `prompt leakage attempt` moved from DANGER to FLAG). No ML.

**5. `enforce_egress_allowlist.sh` / `guard_egress.sh`** (PreToolUse Bash, `settings.json:115-123`)
`[hook]` — egress allowlist + credential-exfil guard; fire on the Bash call that invokes
`sentinel_response.py` (and every other Bash call). `notify-send.sh` and `sentinel_quarantine.py`
exit through `ntfy.sh` / `gws` which are allowlisted. These hooks do NOT block sentinel's own
execution.

#### Honor-system (prose instruction only, no hook)

**6. `SENTINEL_NOTIFY_DISABLE=1`** (`sentinel_response.py:229`) `[honor]`
Env var silences the NTFY push in test mode. No hook enforces it is absent in production. A DANGER
event with this var set logs + tiles + pauses but does NOT push a phone alert. Operator may not
notice. `[·gap]`

**7. `SENTINEL_QUARANTINE_DISABLE=1`** (`sentinel_response.py:249`) `[honor]`
Same pattern — test-disable for the Gmail quarantine step. A DANGER event with this var set applies
the pause list but does NOT label the Gmail message. Combined with GAP-6: both side effects can be
silenced by env vars without any hook catching the suppression. `[·gap]`

**8. `--flag-only` email invariant** (`sentinel_response.py:268`, `ingest_gate.py:110`) `[honor]`
Caps verdict at FLAG (never DANGER, never quarantine) when the caller passes `--flag-only`. The email
invariant depends entirely on the calling code passing this argument correctly. No hook validates its
presence when `source_type=="email"`. A bug in the caller silently removes the floor. (Note:
`ingest_gate.py:28-31` is the docstring describing the invariant; runtime enforcement is at line 110.)
`[·gap — see GAP-1]`

**9. `--reader-verdict BENIGN` suppression** (`sentinel_response.py:223-228`) `[honor]`
Suppresses the NTFY push when the tool-less ingest-reader confirms a finding is benign. The DANGER
quarantine + source-pause still run. Fail-safe: silence requires positive BENIGN confirmation;
anything else (None, REAL-ATTACK, unknown) still rings the bell. Reader-verdict is NOT currently
wired to alter the NTFY alert based on the scanner's verdict (reader-verdict → alert wiring is a
documented TARGET). `[·gap]`

**10. `agents/sentinel.md` redaction rule** `[honor]`
"NEVER echo a detected secret value in audit output" (`agents/sentinel.md:54-65`). No PostToolUse
hook checks the written audit `.md` file for embedded secret patterns before it lands in Drive. `[·gap]`

**11. `security-health.py:hook_active()`** `[honor]`
Advisory — drives tile color, does not block. Absent `sentinel.json` downgrades tile to FLAGS
(green-illusion protection in `security-health.py:184`), but there is no Pulse slot guaranteeing
`_security.json` freshness independent of the system-health sweep. `[·gap — see GAP-3]`

#### PostToolUse hooks that fire on sentinel's Bash invocations (incidentally)

`observability_logger.sh` (PostToolUse `*`) fires on every tool call including the Bash calls that
invoke `sentinel_response.py`. Logs one JSON line per call to
`/tmp/lifehack-observability-buffer.jsonl`. No sentinel-specific relationship; incidental.

`nudge_flow_drift.sh` (PostToolUse Write|Edit) fires if Claude uses the Write/Edit tool on a file
listed in an element's `generated_from`. Does NOT fire on Bash calls — sentinel's own Python writes
are not Claude tool calls and never trigger this nudge.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** provide an on-path injection-verdict gate that blocks the most dangerous inbound content
(DANGER class) at the point of ingestion, surfaces lower-severity findings (FLAG class) with
recurrence-silencing for acknowledged FPs, and maintains a persistent, auditable event ledger for
operator review and rollup into the security dashboard. The auditor subagent provides a complementary
structural security scan (permissions, hook integrity, MCP surface) on a recurring or on-demand basis.

**Current → LIVE·gap** for the primary chain (email_convert.py → ingest_gate.gate() →
sentinel_response.py → event log + tile + pause + NTFY push + Gmail quarantine). Contract locked
2026-06-13. The Pulse twin (`sentinel-health.py`) has a named Pulse slot with a ~1800s poll cadence
and `stale_after_s=86400` (24h tile freshness window). The DANGER_LABELS set was precision-retooled
2026-07-14 to eliminate FP-buzz (SEC-BUZZ-VERDICT). The quarantine action and NTFY push are
operationally wired. The event ledger holds 5 confirmed audit files back to 2026-03.

**Honest LIVE qualification (the gaps):**
- Several side-effects (NTFY push, Gmail quarantine) are fail-open via `[honor]` env vars.
- The email path is permanently FLAG-floored by caller convention (`--flag-only`), not a hook.
- The v1 gate path (`ingest_sentinel_check`) has zero live callers — v2 is the live path via `email_convert.py`; direct per-item runner wiring for v2 is pending.
- The security-health composition tile has no dedicated Pulse slot.
- The auditor subagent has no scheduler at all — but that is now stated as the DESIGN, not a silent death (see GAP-4). Its cadence is manual, matching the mechanical half.
These are documented gaps; the label carries `·gap`.

**TARGET:**
1. Wire the v2 `ingest_gate.py` path into live ingest runners, retiring the v1 `ingest_sentinel_check()`
   path. This adds provenance tagging and a structurally enforced email FLAG-floor.
2. ~~Re-provision the monthly security-audit LaunchAgent.~~ **WITHDRAWN** — manual cadence is the declared design (GAP-4); a scheduler is explicitly not proposed.
3. Add a dedicated Pulse slot for `security-health.py` to govern `_security.json` tile freshness.
4. Wire `--reader-verdict` to the NTFY alert so a confirmed BENIGN verdict suppresses the push.
5. ~~Update `agents/sentinel.md` hook manifest from ~4 to the full hook inventory.~~ **DONE** — the stale manifest was replaced by a named core-enforcement-set presence check plus a settings.json deny-list self-protection check, with the residual non-enumeration stated out loud each run (GAP-5).
6. Add a PostToolUse hook or `validate_on_write` extension to check audit-log writes for embedded
   secret patterns.

---

### ★ INTEROP SEAMS

```
FEEDS        pulse-cron            · sentinel-events.jsonl is the source for sentinel-health.py (a Pulse job); Pulse polls the slot every ~1800s and rewrites the tile with stale_after_s=86400 — sentinel produces the event record; Pulse produces the tile refresh
TRIGGERS     notify-plane          · on DANGER: sentinel_response.notify_danger() calls notify-send.sh (critical NTFY push); unidirectional fire; suppressed if reader_verdict=="BENIGN" (honor-only suppression)
WRITES->     helm                  · sentinel_response.write_tile() + sentinel-health.py both write state/status/sentinel.json; security-health.py composes that into state/status/_security.json; Helm's Security tab reads both tiles
WRITES->     email-service         · on DANGER with a Gmail message-id: sentinel_quarantine.py applies the Sentinel/Quarantine Gmail label to the message (reversible; caller-side wiring absent for non-Gmail items — gap)
SHARES       egress-allowlist-wall · sentinel-events.jsonl is the shared append-only event ledger; egress-allowlist-wall writes block events there (enforce_egress_allowlist.py appends on every off-allowlist denial); sentinel-health.py reads it — sentinel is the shared event store for both inbound-injection and outbound-block violation classes
FEEDS        ingest-coverage       · sentinel-events.jsonl is the fallback coverage source when the provenance breadcrumb ledger (ingest-provenance.jsonl) is absent; ingest_coverage.py switches to it automatically (ingest_coverage.py:28, :68)
SYNCS        helm                  · sentinel_ack.py refreshes sentinel.json immediately on each ack; Helm's dismiss overlay (sentinel-dismissed.json) is a parallel read-layer that must stay in sync with the tile's event ids — a stale tile produces stale dismiss state
GUARDED-BY   hook-plane            · security-ingest-gate (ingest_gate_enforce.sh, PreToolUse Bash/WebFetch/WebSearch/Read) is the wall that routes every external read through the sanitizer stack before sentinel sees findings — the gate calls sentinel and acts on its exit code; sentinel is the verdict layer DOWNSTREAM of the gate; enforce_egress_allowlist.sh + guard_egress.sh fire on every Bash invocation in the ingest harness; no Write/Edit hook guards sentinel's own Drive store paths (Python os.replace bypasses the tool-call hooks — inherited system-class bypass per §8.4b)
```

---

## GAPS

The following are documented fail-open conditions that a tip-only reader of the `LIVE` label would
miss. They inform the `·gap` qualifier on this element's label and map entry.

**GAP-1: `--flag-only` email invariant is caller-convention, not hook-enforced.**
The guarantee that email can never trigger DANGER, quarantine, or source-pause depends entirely on
the calling code passing `--flag-only` to `sentinel_response.py`. Both `ingest-run.lib.sh` (v1) and
`ingest_gate.py` (v2) must do this correctly; no hook or gate validates its presence when
`source_type=="email"`. A bug in the caller silently drops the floor: a DANGER-class injection in an
email body triggers full containment (pause + quarantine + alert) with no override possible at
runtime. Source: `sentinel_response.py:268` (argparse definition); `ingest_gate.py:110` (runtime
enforcement — lines 28-31 are docstring describing the invariant, not enforcement code).

**GAP-2: v1 gate path (`ingest_sentinel_check`) has zero live callers — v2 is the live path, but per-item runner gating is not yet wired.**
The live email ingest path is `email_convert.py → ingest_gate.gate()` (v2 Python import). The v1
`ingest_sentinel_check()` function in `ingest-run.lib.sh:231` has no callers in any runner script.
However, direct per-item gating via `ingest_gate_check()` from runner scripts is also not wired — the
v2 module is reached only via the `email_convert.py` import path. Non-email ingest runners wishing to
use the ENFORCE-posture + provenance-tagging v2 path have no wiring today.
Source: `ingest-run.lib.sh:260`.

**GAP-3: `security-health.py` has no dedicated Pulse slot — `_security.json` tile freshness is ungoverned.**
The Helm Security tab tile (`_security.json`) is only refreshed when `system-health.py` sweeps.
`security-health.py` has `emit_mode: "manual"` (`security-health.py:192`) and no `stale_after_s`
watcher. If `system-health.py` degrades, the Security tab can go stale with no freshness guard or
alert. Source: `system/tools/security-health.py:192`; `system/pulse-config.md` (no
security-health Pulse entry).

**GAP-4: ~~Monthly security-audit LaunchAgent is retired — audit runs manually only.~~ ✅ NOT A GAP —
manual cadence is now stated as the DESIGN.**
The history stands: a LaunchAgent was provisioned 2026-05-22 for monthly automated runs, and no
matching plist was present at audit time (2026-07-23) — it was retired after initial provisioning.
What has changed is the disposition, not the mechanism. `agents/sentinel.md` now carries an explicit
*"Cadence — Manual By Design, Not A Gap"* section: no scheduler is wired to it and none is proposed;
it is run by hand after wiring a new external-content channel, after adding a desk, or for a current
read. This is the same shape as the mechanical half (`sentinel_response.py` / `sentinel_ack.py`),
which `system/security-canon.md` documents as manual-trigger-by-construction. Reclassify from
`·gap` to BY-DESIGN; the TARGET item that asked for the LaunchAgent to be re-provisioned is withdrawn.

**GAP-5: ~~`agents/sentinel.md` hook manifest covers only ~4 of ~50 hooks.~~ ✅ RESOLVED — the stale
manifest was replaced by a named core-enforcement set plus a self-protection check.**
The history stands: the auditor's hook-integrity check was built on a stale manifest of ~4 hook files
against a much larger live hook plane (`records/2026-07-16-synthesis-defect-clusters.md` THEME 6 cites
~22 at the time; the count later grew). The manifest is gone. The check now asserts (a) that the named
**core enforcement set** is present in `system/hooks/` — `ingest_gate_enforce.sh` ·
`guard_write_paths.sh` · `guard_canon_write.sh` · `guard_calendar_writes.sh` · `guard_egress.sh` ·
`enforce_egress_allowlist.sh` — raising an **error** on any absence, on the reasoning that someone may
have deleted a guard; and (b) that `settings.json` denies `Edit` on `system/hooks/**`, on
`settings.json` itself, on `agents/**` and on `skills/**` — the hook self-protection layer, an error if
any of the four is missing. ⚠ The audit still does not enumerate every hook file, and it now says so
out loud with a third standing note recorded every run: `permissions.deny` is **not** OS-level file
protection — a Bash-tool session can still overwrite a hook via shell redirection with the deny rule
present. Naming the residual limit is the fix for the old silent-undercoverage problem.

**GAP-6: NTFY push and Gmail quarantine are both fail-open via env-var test-disable flags.**
`SENTINEL_NOTIFY_DISABLE=1` silences the push; `SENTINEL_QUARANTINE_DISABLE=1` skips the
quarantine. On a DANGER event with either flag set, the event is logged and the tile is updated,
but the operator may not notice. No hook enforces that these vars are absent in production. Combined,
both side effects can be silenced without any blocking guard.
Source: `sentinel_response.py:229, 249`.

**GAP-7: Inline tile writer emits binary status; Pulse twin emits ternary — FLAGS state is underreported.**
`sentinel_response.write_tile()` emits only `"DANGER"` or `"CLEAR"` (binary —
`sentinel_response.py:170`). `sentinel-health.py` emits `"DANGER"` / `"FLAGS"` / `"CLEAR"` (ternary
— `sentinel-health.py:69`). Between Pulse ticks (~1800s poll interval), the tile written by the
inline path does not reflect active FLAG events — the tile shows `"CLEAR"` even when unreviewed flag
events exist. The tile's 24h danger_count is also inflated 2x on DANGER events via the v1 path due
to the shell `_sentinel_log()` duplicate write (Chain A, `ingest-run.lib.sh:239-249`).
Source: `sentinel_response.py:170`; `sentinel-health.py:69`; `ingest-run.lib.sh:239-249`.

**GAP-8: `agents/sentinel.md` audit redaction rule has no mechanical enforcement.**
The "NEVER echo a detected secret value in audit output" directive is an `[honor]` contract. No
PostToolUse hook validates the written audit `.md` for embedded secret patterns before it lands in
Drive. Source: `agents/sentinel.md:54-65`.

**GAP-9: DANGER email de-queue bug — quarantined message loops in queue.**
A quarantined DANGER email is not de-labeled after processing; it remains in the Gmail queue and
loops on the next ingest run. Referenced as `SENTINEL-DEQUEUE` in `debt-ledger.md` — not a standalone
entry but an inline reference within the `[HELM-INGEST-PIPELINE]` item (line 127). SENTINEL-DEQUEUE
is an UNDERLYING contributing factor to the pipeline blockage; the pipeline's unblock condition is the
broader `deryl-ingest-pipeline`, not SENTINEL-DEQUEUE alone. `state:waiting-external
unblock:deryl-ingest-pipeline`. Source: `debt-ledger.md [HELM-INGEST-PIPELINE]` (line 127).

**GAP-10: Egress block events written to sentinel-events.jsonl are not surfaced in the Helm Security tile.**
`enforce_egress_allowlist.py` appends `{"source":"hook/egress","verdict":"blocked",...}` records to
`sentinel-events.jsonl`. Neither `security-health.py` nor the Helm Security tile renders a `blocked`
channel or egress-hook event sub-section. Blocked events sit in the log unseen. Filed as
`[HELM-EGRESS-ALARM-TILE]`. Source: `debt-ledger.md [HELM-EGRESS-ALARM-TILE]`.

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)
- **maturity_label:** LIVE·gap
- **check_detail:** "pending label_checker.py"
