---
topic: [system-architecture]
element: grand-central
title: "grand-central — element detail (ground/base altitude)"
subsystem: intake
altitude: base
record_type: organism-element
maturity_label: PARTIAL·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C6 known-fix-unapplied — validate_contract() is called only from v1 sync(); the live --write-v2 path skips ENF-B.1/.2/.3 on every real run"
generated_from:
  - shared/tools/email_summary_sync.py
  - shared/tools/email_summary_run.sh
  - shared/tools/tasks_store_sync.py
  - shared/tools/calendar_store_sync.py
  - shared/tools/item_store_read.py
  - shared/tools/intake_backfill.py
  - shared/tools/intake_backfill_batch.py
  - system/tools/email-summary-write-run.sh
  - system/tools/email-summary-freshness-run.sh
  - system/tools/tasks-store-sync-run.sh
  - system/tools/calendar-store-sync-run.sh
  - system/tools/item-store-freshness-run.sh
  - system/hooks/ingest_gate_enforce.sh
  - system/hooks/block_primary_calendar.sh
  - system/reference/settings.json
  - system/pulse-config.md
created_at: 2026-07-23
updated_at: 2026-07-23
status: draft
authority: user
---

# grand-central — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. The marker records what
> happened to the named file AT THIS DESTINATION; it does not change the description.
>
> ⛔ `state/status/item-store.json` — runtime-generated, a status tile written by a run under your own notes root, created on first run and never committed. There is no version of it to ship.
> ⛔ `state/status/email-summary.json` — same: runtime-generated, under your own notes root, created on first run and never committed.
> ⛔ `state/email-summary/meta.json` — same: runtime-generated store-index, under your own notes root, created on first run and never committed.

> **⚠ CORRECTED 2026-08-27, lb2-ops-comms.md claims 40/41/44/46 — this element documents the system as
> LESS SAFE than it currently is on two of its own tracked gaps; both are STALE, already closed.** Live
> code, checked directly this session:
> - **gap-6 (ENF-B not called on `write_v2()`) is CLOSED.** `write_v2()` in `email_summary_sync.py` DOES call
>   `_enforce_contract_once()` at ~line 959, which itself calls `validate_contract()` and `sys.exit(3)` on
>   violation. Commit `922e96d` (2026-08-14) is where this contract check was actually built (it added
>   `email_summary_sync.py` itself, 1701 lines). [CORRECTED 2026-08-27, same-day self-correction — the
>   commit id above was first mis-cited as `b9065a4`/2026-08-20, which `git blame` on the call line
>   returns because that later commit was an unrelated Windows console-encoding fix that happened to
>   touch the same physical line; blame answers "who touched this line last", not "which commit
>   introduced this behavior" — `git show --stat` on 922e96d is what actually confirms it.] The frontmatter's
>   `gap_disposition_note` above and the body sections below describing ENF-B as "entirely skipped on every
>   real Pulse write run" are pre-2026-08-20 and superseded — left unedited per house rule, corrected here.
> - **gap-1 (tasks writer soft-fail-open) is CLOSED.** Reading `tasks_store_sync.py` directly (~lines
>   378-387) shows a HARD `sys.exit(1)` on scan-unavailable, not a soft warn-and-continue — matching
>   `item-store.md`'s account of the same mechanism, not this file's gap-1 description of it.
> - **gap-3 (v1 `email-summary-sync` "still enabled: yes") is STALE the other direction.**
>   `pulse-config.md` shows `email-summary-sync` commented `(RETIRED)` with no live `enabled: yes` row at
>   all — it is not a scheduled Pulse slot today.
> - **`tasks-store-sync` / `calendar-store-sync` cadence is 86400s (24h), not 21600s (6h)** as this file's
>   table below states (same stale figure independently found in `item-store.md`).
> These are map fixes, not defect reports against the code — the code moved on; this element didn't.

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the email/calendar/tasks
> intake firehose — the WRITE side: `email_summary_sync.py` (single verbatim Gmail writer),
> `tasks_store_sync.py`, and `calendar_store_sync.py`, all on Pulse cadence, writing the
> per-thread and per-item stores that the read side (email-service, planning) consumes.
> Distinct from the **email-service** element, which is the read/interpret side.
>
> **One-line:** Pulse-dispatched headless runners pull Gmail threads, Google Tasks, and Calendar
> events on recurring cadences and write faithful, schema-validated, injection-scanned records to
> the Drive-backed v2 stores — the single authoritative write path for all three channels.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires, exits 2) · `[honor]` (prose instruction only) ·
> `[human]` (deliberate HITL pause) · `[skill]` (mandatory script, not a hook)

> **LADDER: ELEMENT (full mechanics). up → manual#grand-central ; ground truth → the live artifacts (generated_from)**

---

## AUTHORED   (human-only)

### TRIGGERS / MODES

Three independent Pulse-dispatched cron runners, each machine-gated to the primary machine only. All
three are `enabled: yes` in `system/pulse-config.md`; Pulse itself fires every 5 min via crontab.

| Pulse slot | Interval | Runner | Python entrypoint |
|---|---|---|---|
| `email-summary-write` | 10800 s (3 h) | `email-summary-write-run.sh` | `email_summary_sync.py --write-v2` |
| `tasks-store-sync` | ~~21600 s (6 h)~~ **86400 s (24 h)** [corrected 2026-08-27, claim 40] | `tasks-store-sync-run.sh` | `tasks_store_sync.py --sync` |
| `calendar-store-sync` | ~~21600 s (6 h)~~ **86400 s (24 h)** [corrected 2026-08-27, claim 40] | `calendar-store-sync-run.sh` | `calendar_store_sync.py --sync` |

Two companion **read-side dead-men** (not writers; they check freshness and emit health tiles):

| Pulse slot | Interval | Runner | Purpose |
|---|---|---|---|
| `email-summary-freshness` | 3600 s (1 h) | `email-summary-freshness-run.sh` | reads email-summary.json tile; buzzes phone if DEGRADED |
| `item-store-freshness` | 3600 s (1 h) | `item-store-freshness-run.sh` | reads item-store.json tile; buzzes phone if DEGRADED |

**Supervised-session co-write modes (not Pulse; human-in-the-loop only):**

| Tool | Stores written | Notes |
|---|---|---|
| `intake_backfill.py` | threads-v2/, item-store/tasks/, item-store/calendar/ | backfill/schema-upgrade of existing records; runs in a supervised session, not as a cron job |
| `intake_backfill_batch.py` | threads-v2/ | calls `write_thread_v2_atomic()` from `email_summary_sync`; email-only batch backfill |

**Legacy slot (v1 path, not a writer of the live stores):**
`email-summary-sync` (7200 s, `email_summary_run.sh` → `email_summary_sync.py` no flags) — runs the
v1 `sync()` path and writes `state/email-summary/threads/` + `meta.json`. This is the deprecated path;
the `--write-v2` runner is the live intake. The v1 slot has NOT been disabled in `pulse-config.md`
(see GAPS gap-3).

**Operational sub-modes inside `email_summary_sync.py` (all CLI flags; used in supervised sessions):**

| Flag | Mode | Notes |
|---|---|---|
| `--write-v2` | live v2 Pulse write path | the Pulse runner's primary invocation |
| `--stamp-write-ok` | write-health tile stamp | runner-level invocation after RC=0; best-effort |
| `--dry-run` | read-only diff preview | no writes, no claude -p |
| `--label LABEL` | single-label scope | narrows write_v2 to one label |
| `--force` | bypass unchanged-skip | used for We-3 schema backfill |
| `--threads ID...` | explicit thread list | targeted write_v2 |
| `--emit-degraded` | emit DEGRADED tile | health-tile testing |
| `--freshness-check` | dead-man freshness read | S-1 health tile read |
| `--deep-cold-sweep` | cold-tier migration | moves COLD records >365d to threads-v2-cold/ |
| `--add-tracked-label` / `--remove-tracked-label` | label management | writes meta.json tracked_labels |
| `--mark-completed` / `--mark-active` | lifecycle management | supervised store state change |
| `--self-test` | self-test suite | in-process test harness (tasks + calendar writers have this too) |

---

### FULL HAND-OFF CHAIN

#### ARM 1 — Email v2 (the live intake path)

```
Pulse (*/5 cron)
  → email-summary-write-run.sh [shell]
    → machine-gate: /usr/sbin/scutil --get ComputerName → ComputerName vs
        state/primary-machine marker check
        [non-primary: exit 0 silently, NO writes]
        [missing marker: RC=0 stand-down — stricter than freshness runner]
    → mkdir /tmp/lifehack-email-summary-write.lock [single-instance mutex;
        stale >20m → stolen; email-summary-write-run.sh:50-56]
    → isolated gws auth: GOOGLE_WORKSPACE_CLI_CONFIG_DIR=~/.config/gws-cron,
        GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=~/.config/lifehack/gws-credentials.json,
        GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file [honor: prevents macOS-keychain-delete incident;
        email-summary-write-run.sh:83-90]
    → 3× pre-flight: gws gmail users getProfile [retry 3×4s; fail → RC=2, phone buzz, abort;
        email-summary-write-run.sh:97-106]
    → watchdog-bounded python3 email_summary_sync.py --write-v2 [WATCHDOG_SECS=900;
        kill -9 on timeout; email-summary-write-run.sh:114-121]
      → ENF-A (contract import hard-stop): if email_service_contract fails to import →
          SUMMARY_MODEL sentinel "UNKNOWN-CONTRACT-FAILED" → sync()/write_v2()
          hard-stop before any write [email_summary_sync.py:73-96; honor]
      → _GATE_AVAILABLE check: if ingest_gate import failed → write_v2() returns zero
          counts without writing any thread [email_summary_sync.py:1254-1256; honor]
      → _SCHEMA_AVAILABLE check: if email_thread_schema import failed → write_v2()
          HARD-STOP before any thread write [email_summary_sync.py:1257-1259; honor]
      → load_meta() → tracked_labels list (write_v2 READS meta.json for tracked_labels;
          it does NOT check the enabled flag and does NOT write meta.json
          [email_summary_sync.py:1261-1262; see gap-4])
      → resolve_label_ids() [gws gmail users labels list subprocess → _LABEL_ID_TO_NAME cache]
      → list_thread_ids_for_label() per tracked label [gws gmail users threads list subprocess;
          NO recency floor for Consulting/Emily-Ingest/Deryl-Ingest (NO_RECENCY_FLOOR_LABELS);
          SNOOZED via q=in:snoozed; 30-day floor for INBOX/SENT;
          email_summary_sync.py:RECENCY_FLOOR_DAYS=30]
      → get_thread_metadata() [gws gmail users threads get --format=metadata subprocess]
      → Wr-3 unchanged-skip: newest_message_id == existing.last_message_id → skip
          (cold revive logic: dormant-but-revived threads bypass the skip)
      → process_thread_v2() per thread:
          → email_convert.py subprocess (--messages thread) → sanitized body files in /tmp
          → gate() wrapper: ingest_gate.gate() [RAISES RuntimeError if _GATE_AVAILABLE=False;
              already caught above, but second guard; honor]
          → _scan_for_injection() [from safe_input.scan_for_injection]
          → _run_intake_judge() [from intake_reader; REPLY-FLAGGED derivation is mechanical
              (derive_v2_flag / _scan_for_injection) — no claude -p for that step; but the
              broader v2 path CAN invoke claude -p here (via _run_intake_judge → intake_reader)
              to clear flagged spans]
          → validate_thread_record() [email_thread_schema; SCHEMA-FAIL → skip that thread]
          → write_thread_v2_atomic() [.tmp → os.replace → threads-v2/{thread_id}.json;
              email_summary_sync.py:1035]
      → cold sweep (full run): v2 records not in active set → state=cold,
          write_thread_v2_atomic() (move to threads-v2-cold/ for deep-cold;
          DEEP_COLD_DAYS=365 [email_summary_sync.py:118])
      [write_v2() writes NO status tile — tile stamping is a separate runner step below]
    → runner success branch (RC=0):
        → read error count from worklog: grep -oE 'errors=[0-9]+'
        → python3 email_summary_sync.py --stamp-write-ok --write-errors N
            [SEPARATE runner invocation, not inside write_v2; best-effort:
            failure = warning, not abort; email-summary-write-run.sh:132-133]
            → stamp_write_success() → write_status_tile() → emit_status() → email-summary.json
        → if errors>0: notify-send.sh WARNING partial-refresh [non-critical; honor]
    → runner exit trap (any exit): {rc, ts, stale_after_h} →
        ~/.local/share/lifehack/email-summary-write/last-run.json
        rc != 0 → notify-send.sh CRITICAL [phone buzz; honor]
```

**Note — ENF-A vs ENF-B distinction:**
- ENF-A (module-import hard-stop): fires inside `sync()` only (lines 1944-1957). `write_v2()` (lines
  1254-1259) checks only `_GATE_AVAILABLE` and `_SCHEMA_AVAILABLE` — it does NOT check
  `_CONTRACT_IMPORT_ERROR` and does not reference `CLAUDE_MODEL`/`SUMMARY_MODEL` (the v2 path is
  mechanical, no claude calls). The module-level sentinel `SUMMARY_MODEL='UNKNOWN-CONTRACT-FAILED'`
  does not cause a hard-stop in `write_v2()` because `write_v2()` never uses that variable. ENF-A
  fires for `sync()` only.
- ENF-B (`validate_contract()` runtime check — model-pin + worker-cap + fitness grep): fires ONLY
  inside `sync()` (v1 legacy path, line 1959). ~~`write_v2()` (line 1243) does NOT call
  `validate_contract()` — ENF-B is entirely skipped on every real Pulse write run (see GAPS gap-6).~~
  **CORRECTED 2026-08-27 (claim 41) — this is stale; `write_v2()` now also calls it via
  `_enforce_contract_once()` at ~line 959, closed by commit `922e96d` (2026-08-14, the commit that added
> email_summary_sync.py itself — not `b9065a4`/2026-08-20, which is an unrelated Windows-encoding fix a
> naive `git blame` on the call line points to; see the correction at the top of this file). See gap-6 in the GAPS
  section and the top-of-file correction banner.**

---

#### ARM 2 — Tasks

```
Pulse
  → tasks-store-sync-run.sh [shell]
    → machine-gate: state/primary-machine marker check [non-primary: exit 0 silently]
    → mkdir /tmp/lifehack-tasks-store-sync.lock [single-instance mutex]
    → isolated gws auth [same pattern as email runner]
    → 3× pre-flight: gws gmail users getProfile subprocess [NOT gws tasks tasklists list;
        tasklist enumeration happens inside Python (_list_tasklists()); tasks-store-sync-run.sh:81]
    → watchdog-bounded python3 tasks_store_sync.py --sync [600 s watchdog]
      → _SCHEMA_AVAILABLE check [HARD-STOP if item_schema import fails; honor;
          tasks_store_sync.py:62-75]
      → _SCAN_AVAILABLE / _READER_AVAILABLE (~~WARNING only, NOT hard-stop — gap-1~~ **HARD-STOP,
          `sys.exit(1)`, confirmed live at ~lines 378-387** [CORRECTED 2026-08-27, claim 44 — gap-1 is
          closed, not a soft warn-and-continue; see the GAPS section and top-of-file banner]):
          if scan_for_injection or intake_reader import fails → the writer now stops rather than
          continuing with uncleaned raw task free-text [tasks_store_sync.py:85-101, ~378-387]
      → _list_tasklists() [gws tasks tasklists list subprocess → [(list_id, list_title)]]
      → for each list: _pull_tasks() paginated [safe_tasks.py --desk planning --redact --params JSON
          subprocess; up to 50 pages × 100 = 5,000 tasks/list; rc 0=clean / 1=flagged-valid / 2=err;
          tasks_store_sync.py:155]
      → for each task: _process_task()
          → _qualified_id(): record_id = {list_id}__{task_id} (CT-3.5: task ids are list-scoped,
              not globally unique; tasks_store_sync.py:330)
          → _is_unchanged() [skip if payload.updated == task_raw.updated]
          → _scan_for_injection() + _run_intake_judge() [SOFT: if either import fails →
              _SCAN_AVAILABLE=False → writer proceeds with uncleaned task free-text; WARNING only,
              no HARD-STOP — see GAPS gap-1]
          → validate_item_record() [item_schema; SCHEMA-FAIL → skip that task, count error]
          → _write_atomic(qid, record) [.tmp → os.replace →
              item-store/tasks/{list_id}__{task_id}.json; tasks_store_sync.py:134]
          → _write_manifest(list_id, ...) [per-list manifest → item-store/task-lists/{list_id}.json]
      → one-pass _cold_sweep() across ALL lists: departed tasks → state=cold (never deleted)
    → runner exit trap: {rc, ts} → ~/.local/share/lifehack/tasks-store-sync/last-run.json
      rc != 0 → notify-send.sh critical [honor]
```

---

#### ARM 3 — Calendar

```
Pulse
  → calendar-store-sync-run.sh [shell]
    → machine-gate: state/primary-machine marker check [non-primary: exit 0 silently]
    → mkdir /tmp/lifehack-calendar-store-sync.lock [single-instance mutex]
    → isolated gws auth [same pattern]
    → 3× pre-flight: gws gmail users getProfile subprocess [NOT gws calendar calendarList list;
        calendar enumeration happens inside Python (_resolve_calendars()); calendar-store-sync-run.sh:81]
    → watchdog-bounded python3 calendar_store_sync.py --sync [600 s watchdog]
      → _SCHEMA_AVAILABLE check [HARD-STOP if item_schema import fails; honor;
          calendar_store_sync.py:80ff]
      → scan_for_injection + intake_reader import [HARD-STOP if either unavailable AND free-text
          exists: sys.exit(1); organism-audit defect(c) fix, commit 734b31a 2026-07-20;
          calendar_store_sync.py:486-491]
      → _resolve_calendars() → CALENDAR_ALLOWLIST (5 calendars hardcoded with live gws name
          lookup; calendar_store_sync.py:60-66)
      → for each calendar, TWO PASSES:
          Pass R: _pull_series() [safe_calendar.py --redact singleEvents=False; series with
              recurrence field only; SERIES_LOOKBACK_DAYS=1825 (~5y);
              calendar_store_sync.py:74]
          Pass O: _pull_oneoffs() [safe_calendar.py --redact singleEvents=True ±90d; both one-off
              AND recurring instances stored — CT-3.5b;
              ONEOFF_LOOKBACK_DAYS=90, ONEOFF_LOOKAHEAD_DAYS=90; calendar_store_sync.py:72-73]
      → for each event: _process_event()
          → _is_unchanged() [skip if payload.updated == event_raw.updated]
          → HARD-STOP if free_text non-empty AND (_SCAN_AVAILABLE or _READER_AVAILABLE is False)
              [sys.exit(1); defect(c) fix; honor via Python sys.exit]
          → _scan_for_injection() + _run_intake_judge() on summary + description + location
          → validate_item_record() [item_schema; SCHEMA-FAIL → skip that event]
          → _write_atomic() [sha256[:16]_{event_id[:32]}.json .tmp → os.replace →
              item-store/calendar/]
      → one-pass _cold_sweep() across ALL calendars and BOTH passes
    → runner exit trap: {rc, ts} → ~/.local/share/lifehack/calendar-store-sync/last-run.json
      rc != 0 → notify-send.sh critical [honor]
      NOTE: failure notification body says "tasks_store_sync" (copy-paste bug) — minor known defect
```

---

#### ARM 4 — Email-summary freshness dead-man

```
Pulse (*/5 cron, ~hourly effective cadence via 3600 s slot)
  → email-summary-freshness-run.sh [shell]
    → machine-gate: /usr/sbin/scutil --get ComputerName → host label vs
        state/primary-machine marker check
        [non-lead: exit 0 silently (single tile-writer); missing marker → run best-effort]
    → mkdir /tmp/lifehack-email-summary-freshness.lock [single-instance mutex;
        stale >900 s → stolen; email-summary-freshness-run.sh:36-42]
    → exit handler trap: {subsystem, rc, ts, stale_after_h=6} →
        ~/.local/share/lifehack/email-summary-freshness/last-run.json on ANY exit
        [email-summary-freshness-run.sh:46-51]
    → python3 email_summary_sync.py --freshness-check [WATCHDOG: none — no
        watchdog wrapper; do_work() exit 0 on UP AND DEGRADED (tile carries signal);
        non-zero only if the check itself throws; email-summary-freshness-run.sh:55-59]
      → freshness_check() [email_summary_sync.py:1508]:
          → v2_active_counts_by_scope() [counts ACTIVE threads per tracked label]
          → _newest_v2_mtime() [scans threads-v2/ for newest .json mtime;
              None → "store EMPTY"; staleness_hours = (now − newest) / 3600]
          → staleness check: staleness_hours > FRESHNESS_MAX_STALE_HOURS → DEGRADED
              [email_summary_sync.py:1525-1526]
          → scope zeroed-check: any tracked label with 0 ACTIVE records → DEGRADED
              [email_summary_sync.py:1529-1531]
          → H1.2 write-side dead-man: read STATUS_TILE_PATH (email-summary.json)
              → last_write_run field → write_age_hours; if write_age_hours >
              WRITE_CADENCE_STALE_HOURS → "writer SILENT" → DEGRADED
              [email_summary_sync.py:1537-1547; defensive try/except — never crashes]
          → status = "DEGRADED" if reasons else "UP"
          → write_status_tile(status, extra=detail) [→ emit_status.py → email-summary.json;
              passes last_successful_run from newest mtime, NOT "now" — prevents false
              janitor-success claim; email_summary_sync.py:1561-1564]
    → DEGRADED branch (RC=0 + tile.status in {DEGRADED, ERROR}):
        → read tile from state/status/email-summary.json
        → notify-send.sh --source email-summary-freshness --tags mailbox,warning
            --title "📭 Email store DEGRADED" --message <reason[:180]>
            [normal priority — respects quiet hours; governor-deduped so hourly DEGRADED
            coalesces to one buzz; email-summary-freshness-run.sh:67-75; honor]
    → active failure branch (RC≠0): notify-send.sh --priority critical [honor]
        [email-summary-freshness-run.sh:78-82]
    → exit trap fires: writes last-run.json + clears lock
```

**Note — email freshness tile semantics:** `freshness_check()` writes `email-summary.json` with the
`last_successful_run` field anchored to the newest RECORD's mtime (not "now"), so a read of the tile
tells a consumer when the store was LAST actually updated — not when the freshness check ran. The
write-side dead-man (H1.2) detects a writer that stopped producing even if old records still look
fresh by mtime. `email-summary-freshness-run.sh` and `email_summary_sync.py --stamp-write-ok` (ARM 1)
are two write contexts for `email-summary.json`, but NOT the only ones: the v1 janitor runner
(`email_summary_run.sh`, the `email-summary-sync` Pulse job) is a third distinct writer context — it
calls `write_status_tile()` on both the success path (line 2213) and error paths (lines 1932, 1946,
1962), and via `emit_degraded_tile()` (via `--emit-degraded`). All writers reach the tile through
`write_status_tile()` → `emit_status.py`.

---

#### ARM 5 — Item-store freshness dead-man

```
Pulse (*/5 cron, ~hourly effective cadence via 3600 s slot)
  → item-store-freshness-run.sh [shell]
    → machine-gate: /usr/sbin/scutil --get ComputerName → host label vs
        state/primary-machine marker check
        [non-lead: exit 0 silently (single tile-writer); missing marker → run best-effort]
    → mkdir /tmp/lifehack-item-store-freshness.lock [single-instance mutex;
        stale >900 s → stolen; item-store-freshness-run.sh:33-39]
    → exit handler trap: {subsystem, rc, ts, stale_after_h=4} →
        ~/.local/share/lifehack/item-store-freshness/last-run.json on ANY exit
        [item-store-freshness-run.sh:43-47]
    → python3 item_store_read.py --freshness-check [do_work(); exit 0 on OK AND
        ERROR (tile carries signal); non-zero only if the check itself throws;
        item-store-freshness-run.sh:52-55]
      → freshness_check() [item_store_read.py:349]:
          → active_counts_by_type() [counts ACTIVE records in tasks/ and calendar/
              subdirs; {task: N, calendar: M}; item_store_read.py:354]
          → zeroed-type check: any type with count==0 → reasons.append("zeroed ACTIVE
              type(s): ...") [item_store_read.py:356-358]
          → _newest_item_mtime() [scans item-store/tasks/ + item-store/calendar/ for
              newest .json mtime; None → "store EMPTY"; item_store_read.py:335-346]
          → staleness check: staleness_hours > ITEM_FRESHNESS_MAX_STALE_HOURS (30 h)
              → reasons.append(...) [item_store_read.py:365-366]
          → status = "ERROR" if reasons else "OK"
          → emit_status(ITEM_STATUS_TILE_PATH, pulse_job="item-store-freshness",
              stale_after_s=7200, status=status, payload={counts, zeroed_types,
              staleness_hours}, required_payload=("counts",))
              → writes state/status/item-store.json via emit_status.py [ONE validator;
              item_store_read.py:371-376; honor]
    → ERROR branch (RC=0 + tile.status == "ERROR"):
        → read tile from state/status/item-store.json
        → notify-send.sh --source item-store-freshness --tags card_index,warning
            --title "🗂️ Item store DEGRADED" --message <summary[:180]>
            [normal priority; governor-deduped; item-store-freshness-run.sh:60-68; honor]
    → active failure branch (RC≠0): notify-send.sh --priority critical [honor]
        [item-store-freshness-run.sh:71-75]
    → exit trap fires: writes last-run.json + clears lock
```

**Note — item-store tile semantics:** `item_store_read.py` is the SOLE writer of `state/status/item-store.json`
(grand-central's three write ARMs do NOT touch this tile). The tile signals `status=ERROR` (not DEGRADED — the
CT-4 enum in `emit_status.py`) when any tracked type (`task`, `calendar`) has 0 ACTIVE records or the store is
stale. Helm reads the `ERROR` status for the heartboard red indicator. The `stale_after_s=7200` (2 h) is the
tile's own staleness horizon for Helm's tile-freshness check — distinct from `ITEM_FRESHNESS_MAX_STALE_HOURS=30 h`
(the records' freshness floor).

---

### PORTS TOUCHED (complete store list)

| Store | Path (relative to $DRIVE) | Sole Pulse writer | Supervised co-writers |
|---|---|---|---|
| Email v2 faithful threads | `state/email-summary/threads-v2/{thread_id}.json` | `email_summary_sync.py` (`--write-v2`) | `intake_backfill.py`, `intake_backfill_batch.py` (supervised session only) |
| Email v2 cold tier | `state/email-summary/threads-v2-cold/{thread_id}.json` | `email_summary_sync.py` (MOVE, not delete) | `intake_backfill.py` |
| Email v1 threads (legacy) | `state/email-summary/threads/{thread_id}.json` | v1 `sync()` only (deprecated path) | — |
| Email pruned tombstones | `state/email-summary/pruned/{thread_id}.json` | `email_summary_sync.py` only | — |
| Email meta | `state/email-summary/meta.json` | v1 `sync()` + label-management helpers (`add/remove_tracked_labels`); `write_v2()` READS but does NOT write meta.json | — |
| Email health tile | `state/status/email-summary.json` | `email_summary_sync.py` via `stamp_write_success()` (runner-level `--stamp-write-ok` invocation) | — |
| Tasks item records | `state/item-store/tasks/{list_id}__{task_id}.json` | `tasks_store_sync.py` (Pulse) | `intake_backfill.py` (supervised session only) |
| Tasks list manifests | `state/item-store/task-lists/{list_id}.json` | `tasks_store_sync.py` only | — |
| Calendar item records | `state/item-store/calendar/{sha256[:16]}_{event_id[:32]}.json` | `calendar_store_sync.py` (Pulse) | `intake_backfill.py` (supervised session only) |
| Item-store health tile | `state/status/item-store.json` | `item_store_read.py --freshness-check` (reads grand-central's output to produce this tile) | — |
| Runner proof artifacts (machine-local) | `~/.local/share/lifehack/{subsystem}/last-run.json` + `last-write.log` | each runner's exit trap | — |

Live record counts (verified 2026-07-23 audit): email threads-v2 ≈ 1,015 · tasks ≈ 124 · calendar ≈ 2,000.

---

### OUTCOME

Three Drive-backed stores are kept continuously fresh: verbatim Gmail threads (threads-v2/), durable
task records (item-store/tasks/), and calendar event records (item-store/calendar/). These stores are
the sole Pulse-written input to the email-service read adapter and the planning item-window reader.
Cold/departed records are retained with `state=cold` — never deleted. Health tiles emit to Helm; errors
buzz the phone immediately. Schema validation + injection scanning + atomic writes are on every write
path; no partial records are possible. Supervised-session co-writers (intake_backfill.py,
intake_backfill_batch.py) can also write all three stores but only under direct human supervision.

---

### ENFORCEMENT POINTS (the honest map)

**Hook-enforced (session-side — fire inside Claude sessions only, NOT during headless cron):**

1. **`ingest_gate_enforce.sh`** (PreToolUse Bash + Read) `[hook]` — the session-side single-writer
   invariant and adapter-required read:
   - **(f)** Non-janitor shell WRITE to `email-summary/` → BLOCK exit 2 (hook line 156-159)
   - **(g)** Un-wrapped shell READ of `threads-v2/` → BLOCK exit 2 (hook line 162-164)
   - **(h)** Non-writer shell WRITE to `item-store/` → BLOCK exit 2 (hook line 169-171)
   - **(i)** Un-wrapped shell READ of `item-store/` → BLOCK exit 2 (hook line 175-177)
   - **(Ra-2)** Read tool on `*email-summary/threads-v2/*` → BLOCK exit 2 (hook line 83)
   - **(CT-1)** Read tool on `*item-store/*` → BLOCK exit 2 (hook line 86)
   - Also blocks: raw gmail body reads, raw gws calendar events list, raw gws tasks reads (these are
     the pull-side guards that complement the write-side single-writer invariant).
   - Fail-CLOSED: parse error / top-level JSON error → DENY.
   - **Critical gap:** these hooks fire only inside a Claude session. Headless Pulse cron runners call
     Python directly via subprocess — the hooks do NOT fire on the writers' own store writes. Single-writer
     invariant during cron is purely honor-based (see GAPS gap-2).

2. **`block_primary_calendar.sh`** (PreToolUse Bash) `[hook]` — guards gws calendar write verbs not
   targeting the Agent Ops calendarId. Relevant if a session attempts to write calendar events directly;
   not in grand-central's write path (the runners call `safe_calendar.py` for reads only).

3. **`guard_write_paths.sh`** (PreToolUse Write|Edit) `[hook]` — the residency wall: blocks any
   Write/Edit outside the Drive spine / approved `~/.claude/` paths / the clone. The item-store and
   email-summary stores live at `$DRIVE/state/...` (inside the Drive spine) → a Write/Edit to those
   paths is ALLOWED by this hook (it enforces location, not single-writer identity). The single-writer
   invariant for these stores is enforced by `ingest_gate_enforce.sh` (h) for the Bash tool, NOT by
   guard_write_paths. Known gap: a Write/Edit tool call directly authoring valid JSON into
   `state/item-store/` would pass guard_write_paths (location OK) without touching the schema
   validators. Fail-CLOSED on unparseable input.

**Python-internal hard-stops (fire inside the cron Python processes — NOT Claude hooks):**

4. **ENF-A (contract import):** if `email_service_contract` fails to import → sentinels set →
   `sync()` / `write_v2()` hard-stop before any write. `[honor]`
   (email_summary_sync.py:73-96)

5. **ENF-B (validate_contract runtime):** model-pin + worker-cap ≤5 + grep fitness check over the
   codebase for unauthorized Gmail callers. Fires inside `sync()` (email_summary_sync.py:1959, v1
   legacy path) ~~only~~ **and also inside `write_v2()`, via `_enforce_contract_once()` at ~line 959**
   [CORRECTED 2026-08-27, claim 41 — commit `922e96d` (2026-08-14) closed this; ENF-B fires on the live
   Pulse write path too now]. Non-empty violations → tile DEGRADED + HARD-STOP on either path.
   **Gap:** the grep does NOT scan `skills/` or `agents/` directories — an unauthorized Gmail caller in
   a skill would evade this check (see GAPS gap-5, still open — not part of this correction).
   `[honor]`

6. **ingest_gate 1.1b hard-stop:** `_GATE_AVAILABLE=False` → `write_v2()` returns zero counts without
   writing any thread. `[honor]` (email_summary_sync.py:1254-1256)

7. **email_thread_schema hard-stop:** `_SCHEMA_AVAILABLE=False` → `write_v2()` HARD-STOP before any
   thread write. `[honor]` (email_summary_sync.py:1257-1259)

8. **item_schema hard-stop (tasks + calendar):** `_SCHEMA_AVAILABLE=False` → `sync()` returns
   `{"error": "schema_unavailable"}` before writing anything. `[honor]`
   (tasks_store_sync.py:62-75, calendar_store_sync.py:80ff)

9. **calendar scan HARD-STOP:** `free_text` non-empty AND (`_SCAN_AVAILABLE` or `_READER_AVAILABLE`
   is False) → `sys.exit(1)`. This is the organism-audit defect(c) fix (commit `734b31a`, 2026-07-20).
   `[honor]` (calendar_store_sync.py:486-491)

10. **Atomic write invariant:** all three writers use `.tmp` → `os.replace()` on every store file.
    No partial reads are structurally possible. `[honor]`

**Shell-level guards (fire in the runner before Python is invoked):**

11. **Primary-machine marker:** `state/primary-machine` read; runner stands down if missing or
    non-matching. Missing marker → stand-down (fail-safe; stores stay un-refreshed rather than
    running blind). `[honor]` (email-summary-write-run.sh:38-46)

12. **Single-instance mutex:** `mkdir /tmp/lifehack-{name}.lock`; stale lock threshold varies by
    runner: write runners (email-summary-write, tasks-store-sync, calendar-store-sync) use 1200 s
    (20 min); freshness runners (email-summary-freshness, item-store-freshness) use 900 s (15 min).
    Prevents double-pull on a Pulse double-tick. `[honor]`

13. **Isolated gws credentials:** `GOOGLE_WORKSPACE_CLI_CONFIG_DIR=~/.config/gws-cron`. Prevents
    the macOS-keychain-delete incident from recurring. `[honor]`
    (email-summary-write-run.sh:83-90)

---

### INTENT / CURRENT-VS-TARGET

**Intent:** a single, continuous, machine-maintained mirror of the three Google data channels
(Gmail threads, Tasks, Calendar events) — verbatim, faithful, schema-validated, injection-scanned
— so that every downstream consumer (email-service, planning, Helm health) reads from a
Drive-local store rather than pulling raw gws data on demand.

**Current → PARTIAL, for a precise reason:**
The three writers are Pulse-enabled, proven live (last verified write counts: email 1015 threads,
tasks 124, calendar 2000), atomic-write-safe, schema-validated, and health-monitored. The
session-side hook enforcement (ingest_gate_enforce.sh) is fully live and fire-tested.

What remains PARTIAL:
- **Tasks scanner soft-fail-open (gap-1):** the tasks writer lacks the calendar writer's HARD-STOP
  on scanner/reader import failure — it silently stores uncleaned task free-text. This is a documented
  fail-open bypass on the security posture.
- **Session-hooks don't cover headless cron (gap-2):** ingest_gate_enforce.sh is a Claude-session gate
  only; the Pulse cron paths are entirely honor-based single-writer.
- **v1 Pulse slot still enabled (gap-3):** the legacy email-summary-sync slot is `enabled:yes` —
  documented-intentional since Phase-8 go-live (2026-07-09), gated at the code level by meta.json's
  `enabled` flag. The operational gap is that two Pulse slots write to `meta.json` on overlapping
  cadences (concurrent shared-state writer).
- **ENF-B.3 coverage hole (gap-5):** the runtime fitness grep omits `skills/` and `agents/`.
- **ENF-B not called on live write path (gap-6):** `validate_contract()` fires in `sync()` (v1 legacy)
  only; `write_v2()` (the live Pulse path) skips it entirely — model-pin, worker-cap, and the
  unauthorized-caller grep are all silently bypassed on every real Pulse write run.
> ⚖ **NOTE 2026-08-15 — the two `…-STUDIO-VERIFY` strings below are IDENTIFIERS, not machine names,
> and are deliberately NOT renamed.** They are primary keys into the donor repo's debt-ledger, and
> that ledger is **not in this repo** (`grep` finds these IDs in exactly two files, both here) — so
> renaming them at this end would silently break the only reference they have. Per the
> no-named-machines ruling, every *description* around them now uses roles ("the primary machine" /
> "the second machine"); the bracketed keys stay verbatim so the cross-reference survives. If the
> donor ledger is ever ported here, rename BOTH ends in one change or neither.

- **[EMAIL-ENF-C-STUDIO-VERIFY] debt item `state:waiting-external`:** ingest_gate_enforce.sh verified
  on the primary machine but NOT yet fire-tested on the second machine — the session-side enforcement is PARTIAL until
  both machines register the hook.
- **[EMAIL-CRON-STUDIO-VERIFY] debt item `state:waiting-external`:** whether the email-summary-sync
  cron exists on the second machine's crontab is unverified.

**TARGET:**
1. Fix tasks scanner to match calendar's hard-stop posture (parity with defect-c fix).
2. Disable the v1 `email-summary-sync` Pulse slot (or gate it explicitly behind a separate flag).
3. Extend ENF-B.3 grep scope to `skills/` and `agents/` directories.
4. Call `validate_contract()` at `write_v2()` entry so ENF-B (model-pin + worker-cap + grep) fires
   on the live Pulse path, not only in the deprecated `sync()` path (closes gap-6).
5. Fire-test `ingest_gate_enforce.sh` on the second machine (unblock: `[EMAIL-ENF-C-STUDIO-VERIFY]`).
6. Verify the second machine's crontab contains the correct Pulse slots (`[EMAIL-CRON-STUDIO-VERIFY]`).
7. Consider adding `ENF-C` (a Claude-harness write-time hook) once the store-access guard is
   verified on both machines (`[EMAIL-ENFORCE-REVIEW]` debt item, review 2026-08-09).

---

### INTEROP SEAMS (shared-state edges — the organism view)

```
FEEDS      email-service    · state/email-summary/threads-v2/ is the exclusive store
                              email_service_read.py (read_thread) serves to the 4 ingest desks;
                              grand-central is the sole Pulse writer, email-service is the sole
                              sanctioned reader
FEEDS      planning         · item_store_read.read_item("calendar") reads state/item-store/calendar/
                              for event payloads; grand-central (calendar_store_sync.py) is sole
                              Pulse writer
FEEDS      planning         · item_store_read.read_item("task") reads state/item-store/tasks/ for
                              task payloads; grand-central (tasks_store_sync.py) is sole Pulse writer
WRITES->   helm             · state/status/email-summary.json — written by email_summary_sync.py
                              via stamp_write_success() → --stamp-write-ok runner invocation after
                              RC=0 (and also by the v1 janitor and freshness runner; see ARM 4 note).
                              system-health.py (Helm) does NOT read email-summary.json; Helm monitors
                              the email-summary-sync/freshness/write jobs by HEARTBEAT (pulse-config),
                              not by tile. The tile is read by email-summary-freshness-run.sh itself
                              for local DEGRADED notification logic.
FEEDS      item-store-freshness-runner  · grand-central's output stores (state/item-store/tasks/,
                              state/item-store/calendar/) are the INPUT that item_store_read.py
                              --freshness-check reads; that runner writes state/status/item-store.json
                              (grand-central is NOT the direct writer of item-store.json —
                              item_store_read.py is; grand-central only produces the records it reads)
TRIGGERS   notify-plane     · write-runners (email-summary-write-run.sh, tasks-store-sync-run.sh,
                              calendar-store-sync-run.sh) and freshness-runners call notify-send.sh
                              on ERROR/DEGRADED; grand-central is a direct trigger source for the
                              notify-plane on every write failure
GUARDED-BY security-ingest-gate  · ingest_gate_enforce.sh blocks direct Read of threads-v2/ and
                              item-store/, and blocks non-janitor Write to those paths; PreToolUse
                              + Read hook, fail-CLOSED; the write-side single-writer invariant is
                              enforced at the session boundary (not during headless cron)
KEYS-OFF   pulse-cron       · all three writers and both freshness runners are registered in
                              pulse-config.md and dispatched by Pulse on their cadences (3h, 6h,
                              6h, 1h, 1h); Pulse is the sole trigger source for the write paths
SHARES     security-ingest-gate  · email_convert.py (universal sanitizer), ingest_gate.py,
                              safe_input.py (injection scanner, in-degree 17), and intake_reader.py
                              (judge) are shared library components used by grand-central's Python
                              writers AND by security-ingest-gate's redirect targets; the conjunction
                              of layers is load-bearing (organism-audit efficiency-research O-02:
                              layering exists to catch degraded-layer failures — calendar defect-c
                              is the proof case)
```

---

### GAPS (documented fail-open conditions)

These are the conditions that cause this element to `·gap` — real bypass paths where a tip-only
reader would over-trust the stated PARTIAL label. Each is code-verified in the source audit.

**gap-1 · tasks scanner soft fail-open (security-relevant, ~~open~~ CLOSED)**
~~`tasks_store_sync.py` lines 85-101: if `_SCAN_AVAILABLE` or `_READER_AVAILABLE` is False (import
failure at cron startup), the tasks writer continues and stores raw, unscanned task free-text
(`cleared_title = raw_title`, no reader applied).~~ **⚠ CORRECTED 2026-08-27, lb2-ops-comms.md claim
44 — this gap is closed, not open.** Reading `tasks_store_sync.py` directly (~lines 378-387) shows a
HARD `sys.exit(1)` on scan-unavailable — the same posture as the calendar writer, not the soft
warn-and-continue this entry describes. `item-store.md`'s account of this same mechanism (a hard stop
in both writers) is the accurate one; this entry is stale. The pull-level `safe_tasks.py --redact`
scrub still runs regardless. **No fix needed — already matches calendar's `sys.exit(1)` pattern.**

**gap-2 · hook plane does not cover headless cron writes (structural, accepted)**
`ingest_gate_enforce.sh` and all session-side single-writer-invariant hooks fire only inside a Claude
session (PreToolUse). The Pulse runners invoke Python directly via subprocess — no hook runs. Single-
writer enforcement during cron is purely honor-based: the runners are the only things that call the
writers, but a rogue cron entry or manual Python call from the shell could write the stores without
any hook gating. Documented in `ingest_gate_enforce.sh` header as a known structural gap. Accepted
2026-07-14 (`guard_write_paths.sh` header notes the same limitation for Bash writes).

**gap-3 · legacy v1 email-summary-sync Pulse slot still enabled (operational, ~~documented-intentional~~ CLOSED)**
~~`pulse-config.md` lines 89-94: `email-summary-sync` (7200 s, `email_summary_run.sh` → no `--write-v2`
flag) is `enabled: yes`~~ **⚠ CORRECTED 2026-08-27, lb2-ops-comms.md claim 46 — this is stale.**
`pulse-config.md` now shows `email-summary-sync` commented `(RETIRED)` with no live `enabled: yes` row
at all — it is not a scheduled Pulse slot today, contradicting the claim that it is running as
documented-intentional debt. The concurrent-writer risk this entry warns about no longer applies since
the slot isn't dispatched. **No fix needed — already retired.**

**gap-4 · write_v2() does not check meta.json enabled flag (advisory, accepted)**
The `enabled: False` default in `meta.json` gates the legacy v1 `sync()` path only
(email_summary_sync.py:1919-1924). `write_v2()` reads `meta.json` for `tracked_labels` only
(line 1261) — it does NOT check `enabled`. An operator setting `enabled: False` intending to
disable all email-summary writes would stop v1 but not v2. The design intent is that the Pulse
job itself is the gate, but there is no code-level check to prevent `write_v2` running if
`enabled: False`. Accepted asymmetry; documented here as a footgun.

**gap-5 · ENF-B.3 grep omits skills/ and agents/ (security-relevant, open)**
`validate_contract()` in `email_summary_sync.py` (line 314) runs a fitness grep over
`shared/tools/`, `system/tools/`, and `desks/` for unauthorized Gmail-access patterns. It does NOT
scan `skills/` or `agents/` directories. A skill or agent calling `gws gmail` directly would evade
the runtime fitness check. No verified fix commit in the audit corpus — treat as open. **FIX:**
extend the grep paths to include `skills/` and `agents/`.

**gap-6 · ENF-B (validate_contract) does NOT fire on the live --write-v2 Pulse path (security-relevant, ~~open~~ CLOSED 2026-08-20)**
~~`validate_contract()` (defined at line 314) is called at line 1959 inside `sync()` — the v1 legacy
path — only. `write_v2()` (line 1243), which is the entrypoint the live `email-summary-write-run.sh`
runner invokes via `--write-v2`, does NOT call `validate_contract()`. This means on every real Pulse
write run: the model-pin check (ENF-B.1), the worker-cap ≤5 check (ENF-B.2), and the fitness grep
that catches unauthorized Gmail callers in `shared/tools/`, `system/tools/`, and `desks/` (ENF-B.3)
are ALL silently skipped. An unauthorized Gmail caller added to any scanned directory — or a
model-pin violation — would not be caught by ENF-B during normal operation; the check only fires on
the now-deprecated `sync()` path. This is a fail-open on the primary write path.~~
**⚠ CORRECTED 2026-08-27, lb2-ops-comms.md claim 41 — this gap is closed and this was the most
consequential single correction in that pass.** `write_v2()` DOES call `_enforce_contract_once()` at
~line 959 inside its own body, which itself calls `validate_contract()` and `sys.exit(3)` on
violation. Commit `922e96d` (2026-08-14, the commit that added `email_summary_sync.py` itself) is what
actually closed this — not `b9065a4`/2026-08-20, which `git blame` on that call line points to only
because it was an unrelated Windows-encoding fix that happened to touch the same physical line last.
this correction. ENF-B.1/.2/.3 fire on the live Pulse write path today; this element (and its
frontmatter `gap_disposition_note`, ruled 2026-07-28) describe a state that predates the fix.
**No fix needed — already called.**

---

## AUTO-COMPUTED   (machine-only — written by Feature 1.5 `label_checker.py`)

- **maturity_label:** PARTIAL·gap
- **check_detail:** pending label_checker.py
