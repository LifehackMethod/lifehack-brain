---
element: gws-plane
title: "gws-plane — Google Workspace access plane (element detail, ground altitude)"
subsystem: google-access
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — the operator ruled 2026-07-28: CLOSE the MCP calendar bypass — block_primary_calendar.sh matches Bash/gws only"
generated_from:
  - system/gws-contract.md (v1.0, 2026-03-26)
  - system/google-policy.md (v1.0, 2026-03-27)
  - system/google-capability-registry.yaml (v1.0, 2026-03-27)
  - system/hooks/guard_gws_logout.sh (2026-06-02)
  - system/hooks/block_primary_calendar.sh (2026-05-31)
  - system/hooks/enforce_email_sanitize.sh (2026-06-13) [SUPERSEDED — unregistered; file exists for historical reference]
  - system/hooks/ingest_gate_enforce.sh (2026-07-17, Window-5 gate)
  - system/hooks/guard_sheet_writes.sh (2026-06-27)
  - system/hooks/guard_sheet_formula_writes.sh
  - system/hooks/guard_tasks_writes.sh (2026-06-25)
  - system/reference/settings.json (hook registrations, verified 2026-07-24)
  - system/tools/safe_calendar.py (clone)
  - system/tools/safe_tasks.py (clone)
  - state/debt-ledger.md (gws entries, DRIVE, read 2026-07-24)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# gws-plane — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. Each marker records what
> happened to that file AT THIS DESTINATION; none of them changes the description.
>
> ⛔ `system/reference/settings.json` did not come across. It was the donor's read-only reference copy of the
> harness config; this repo's hook registry is `.claude/settings.json`, independently authored and smaller.
>
> ⛔ `system/hooks/enforce_email_sanitize.sh` was deliberately not ported. It is one of six per-channel hooks
> that `system/hooks/ingest_gate_enforce.sh` superseded in the donor; it was already unregistered there, and
> §4b below says so. It exists in the donor for historical reference only, and that is not a reason to ship it.

> **LADDER: ELEMENT (full mechanics). up → manual#gws-plane ; ground truth → gws-contract.md + google-policy.md + google-capability-registry.yaml (generated_from above)**

**One-line:** the single, locked, Bash-only conduit for all Google Workspace reads and writes — binary, auth, capability tiers, write-guard stack, and the per-channel ingest wrappers that sanitize untrusted content before it enters context.

**Enforcement tags used below:**
`[hook]` (a PreToolUse hook fires; exit 2 = hard block) · `[honor]` (CLAUDE.md / contract prose only, no mechanical block) · `[human]` (deliberate HITL pause) · `[registry]` (governed by google-capability-registry.yaml).

---

## AUTHORED   (human-only)

### 1. THE BINARY + AUTH

**Binary:** `/opt/homebrew/bin/gws` — **always absolute path** (`system/gws-contract.md` line 18).
**Pinned version:** `0.22.3` (verified: `gws-contract.md` line 26).
**Auth:** OS keychain; no per-session setup. Credentials inherited from the shell environment automatically.

**Critical invocation rule — `2>/dev/null` on ALL JSON-capturing calls:**
`gws` writes `Using keyring backend: keyring` to stderr on every call. Merging stderr (`2>&1`) corrupts the JSON stream. Rule: always `2>/dev/null` when output is piped to a JSON parser (`gws-contract.md` lines 45–49).

**zsh quoting rules (gws-contract.md §"zsh Quoting Rules"):**
- `--params` value: always single-quoted: `--params '{"key":"value"}'`
- `--json` body: always single-quoted
- `!` in named-tab ranges (`Sheet1!A1`) fails in zsh — gws exits 3 ("invalid escape"). Safe pattern: bare ranges (`A1:Z100`). Workaround for named tabs: Python `subprocess.run([...], shell=False)` which bypasses zsh entirely (confirmed 2026-05-07, `gws-contract.md` rule #3).
- Shell var interpolation: double-quoted JSON with vars expanded: `"{\"key\":\"$VAR\"}"`

**Auth error handling:**
- exit 2 = auth broken — stop and tell the user. Do NOT attempt repair; do NOT call `gws auth login` or `gws auth logout`. Recovery path: user runs `! gws auth login --full` themselves.
- If `token_valid` is false or `encrypted_credentials_exists` is false → stop and report.

**Auth destruction guard — `guard_gws_logout.sh` `[hook]`:**
`gws auth logout` destroys ALL credentials for every window at once (destroyed the system 2026-06-01). The hook fires as a PreToolUse Bash matcher; on match it exits 2 (`deny → stderr, exit 2`, council audit 2026-06-16). Regex: `(^|[[:space:]]|/)gws[[:space:]]+auth[[:space:]]+logout`. Registered in `settings.json` (`system/reference/settings.json` line 126). Also guarded at the `settings.json` `permissions.deny` level: `Bash(gws auth logout:*)`, `Bash(~/.cargo/bin/gws auth logout:*)`, `Bash(/opt/homebrew/bin/gws auth logout:*)`.

**Auth-adjacent config guard — `settings.json` deny-list `[hook]`:**
`Read(~/.config/gws/**)`, `Edit(~/.config/gws/**)`, `Write(~/.config/gws/**)` are all in the deny list. No agent reads or edits gws config files except under an explicit root-mode user instruction.

**gws auth login `[honor]` `[human]`:**
`gws auth login --full` and `gws auth setup` require explicit user approval (`!` prefix). Listed in `settings.json` `permissions.ask` (`settings.json` lines 83–86). Agents must NEVER call these; they suggest the user runs them.

---

### 2. CAPABILITY TIERS

Two tiers govern which gws commands may be wired to skills (`google-capability-registry.yaml` §"tiers"):

**STABLE** — live-validated gws Bash support, contract examples verified. Safe to wire to desks.
**VERIFY-BEFORE-USE** — schema accessible but not live-verified; a desk may NOT list in `allowed` until `global_reachability` is populated.

Five risk classes govern every capability (`google-capability-registry.yaml` §"risk_classes"):

| Class | Meaning | Confirm |
|---|---|---|
| READ | No side effects | Never |
| WRITE_SAFE | Creates/modifies, reversible | Show before execute |
| WRITE_DESTRUCTIVE | Deletes/bulk-overwrites | Explicit per-operation confirm |
| ADMIN | Permissions/structure | Explicit confirm + desk must declare |
| AUTOMATION | Apps Script execution | Explicit confirm + function-level desk declaration |

**Desk capability model:**
Each desk declares `access_model` (BROAD / BROAD_READ) and `max_risk_class` in its CLAUDE.md and in `google-capability-registry.yaml §"desks"`. Read-only from the registry:
- planning, emily, deryl, clair, dobby: `access_model: BROAD`, `max_risk_class: WRITE_SAFE`
- marc: `access_model: BROAD_READ`, `max_risk_class: READ`
Finding a capability in the registry does NOT mean a desk has it — the desk CLAUDE.md `write_capabilities` list is the actual grant.

**Global deny list** (`google-capability-registry.yaml §"global_deny"` + `google-policy.md §"Hard Prohibitions"`):
Hard-blocked for all desks regardless of declaration:
- Gmail: `gmail.send`, `gmail.draft`, `gmail.reply`, `gmail.batch_ops`, `gmail.label_manage`, `gmail.filter_manage`, `gmail.delete`
- Calendar: `calendar.update_event` (any calendar)
- Drive: `drive.delete_file`, `drive.share_file`, `drive.manage_permissions`, `drive.public_link`
- Sheets: `sheets.row_delete`, `sheets.formula_injection`
- Apps Script: `apps_script.edit_code`, `apps_script.manage_triggers`
- People/Contacts: `people.all`
- Self: `self.expand_powers`, `self.change_toolplane`

**Note — `calendar.delete_event`:** NOT globally denied — Cal desk + Agent Ops calendar only; enforced by desk CLAUDE.md declaration and `block_primary_calendar.sh` calendarId check, not by the deny list.

---

### 3. WRITE GUARDS (the enforcement stack)

The gws write-guard stack is five hooks, all PreToolUse on Bash, all registered in `settings.json`, all exit 2 on deny (the proven mechanism: deny → stderr, exit 2; confirmed by council audit 2026-06-16).

#### 3a. `guard_gws_logout.sh` — auth destruction guard
Already covered in §1. The root backstop: blocks `gws auth logout` from any session. `[hook]`

#### 3b. `block_primary_calendar.sh` — calendar write target guard
**Trigger:** any `gws calendar` command that is not a RECOGNISED READ. `[hook]`
**Enforcement: DEFAULT-DENY** (inverted from an allowlist-of-write-verbs on 2026-08-01, organism-audit T8.4). The guard recognises READS — `events list|get|instances`, `calendarList list|get`, `calendars get`, `acl list|get`, `freebusy query`, `colors get`, `settings list|get`, `+agenda`, `help` — matched against the command HEAD only (everything from the first flag or quote onward is payload, so a `--params` body containing the words "events list" can never talk a write into looking like a read). Those pass. Everything else — a write verb OR a verb the guard does not recognise — must name the Agent Ops calendarId somewhere in the full command, or it is denied. The trailing `|| exit 0` is deliberately absent: that was the bug. The old allowlist form failed OPEN on gws's own documented `+insert` helper (fire-tested — `gws calendar +insert --calendar primary` returned rc=0 and walked through), and equally on `events delete`, `calendars clear`, `acl insert`, `calendarList delete`, and any verb gws adds in future. An unknown verb is now unknown-therefore-DENIED. Fail-closed: unreadable stdin or unparseable JSON → deny.
⚠ **The destination's equivalent guard differs on two points and the fail posture is one of them.** It is named `guard_calendar_writes.sh`, it shares this default-deny core, but (a) it reads the target calendar id from `shared/cal_config.py` / `<notes>/config/cal.md` instead of hardcoding it — and denies outright if no calendar has been configured — and (b) on *unparseable* stdin it **exits 0, not deny**, deliberately, so that a malformed payload in front of every Bash command cannot wall the session off from the shell. Fail-CLOSED there begins once a calendar command is actually in hand. Do not read the "Fail posture: CLOSED" line above as describing the destination.
**Agent Ops calendarId (canonical):** `<agent-ops-calendar-id>`
**Why it exists:** Claude defaulted writes to `primary`, corrupting personal events (established 2026-05-31, `block_primary_calendar.sh` LLM CONTEXT header).
**Gap:** does NOT block MCP Google Calendar writes to primary — the guard matches Bash/gws only. An MCP-path write bypasses this hook entirely. Known debt: `[CAL-WEEKLY] MCP-matcher calendar guard hook` in `debt-ledger.md`. `[hook]·gap`

#### 3c. `guard_sheet_writes.sh` — Sheets write discipline guard
**Trigger:** any `gws sheets` write command (`append`, `update`, `batchUpdate`, `clear`, `delete`, structural `spreadsheets batchUpdate`) unless `LIFEHACK_SHEET_CONFIRM=1` is set. `[hook]`
**Two layers:**
1. **Read-the-rules-first (LLM_GUIDE gate):** before any Sheets write, the hook checks for a per-sheet marker file at `~/.claude/run/sheet-llm/<SHEET_ID>` (TTL 12h). The marker is set when the `_LLM_GUIDE` (or legacy `LLM`/`README`/`instructions`) tab has been read. No marker → deny. Sheets pass once read.
2. **Destructive-op confirm:** `clear`, `delete`, mass-overwrite operations also require `LIFEHACK_SHEET_CONFIRM=1` (the operator's in-session yes). Structural `spreadsheets batchUpdate` is separately denied and redirected to `google-sheet-sop.md` + `/google-sheet` skill.
**Why it exists:** Sheets-as-databases (billing/financial/ledger) are "fine china" — irreversible overwrites have occurred (built 2026-06-17).

#### 3d. `guard_sheet_formula_writes.sh` — Sheets formula injection guard
**Trigger:** `values update` or `values batchUpdate` against a Sheets range where the CURRENT CELL CONTENT (read back with `valueRenderOption:FORMULA`) starts with `=` or contains the lock emoji `🔒`. Does NOT check the incoming write value; does NOT block `@`, `+`, `-` prefixed values at the hook layer (only at the policy/prohibition #13 layer). Appends always pass. `[hook]`
**Why it exists:** formula injection — LLM-generated values prefixed with `=` execute as spreadsheet formulas (`google-policy.md` prohibition #13, `google-capability-registry.yaml global_deny: sheets.formula_injection`).
**Known FP (`[SHEET-GUARD-NAMEDTAB]`):** the hook's own verification read (`gws sheets spreadsheets values get --params '{"spreadsheetId":"...","range":"Tab!A1:B2",...}'`) fail-closes on zsh `!` quoting errors, blocking a legit plain-cell update targeting a named tab even when the cell is not a formula.

#### 3e. `guard_tasks_writes.sh` — Life Map read-only guard
**Trigger:** any `gws tasks` write verb (`insert`/`update`/`patch`/`delete`/`move`/`clear`) targeting the Life Map tasklist (`<google-resource-id>`), EXCEPT an `insert`/`update`/`patch`/`move` referencing the Daily Win parent task (`<google-resource-id>`). `[hook]`
**Why it exists:** the Life Map is human-maintained, read-only for all agents (CLAUDE.md "Life Map" rule). Clair cadence-nudge opened write access to Tasks generally (2026-06-04); this guard walls off the Life Map specifically (2026-06-25). One narrow carve-out: planning-daily may write the day's confirmed dominoes as Daily-Win subtasks.

---

### 4. INGEST WRAPPERS (per-channel read sanitization)

gws reads three attacker-controllable free-text channels: email bodies, calendar event text, and task notes/titles. Each channel has a mandatory wrapper before the content enters the model's context. The unified enforcement gate is `ingest_gate_enforce.sh`.

#### 4a. `ingest_gate_enforce.sh` — the unified on-path gate (Window-5)
**Registered:** PreToolUse on Bash, WebFetch, WebSearch, Read (`settings.json` lines 211/221/231/241). `[hook]`
**Subsumes:** the six prior per-channel hooks (enforce_email_sanitize · guard_web_fetch · guard_web_search · guard_file_reads · sanitize_calendar_reads · guard_skip_safe_backdoor). Those files still exist in `system/hooks/` but are unregistered/superseded.
**Fail posture:** CLOSED — unparseable hook input → deny.

**gws branches enforced by `ingest_gate_enforce.sh`:**

**(c) Gmail body read — must route through `email_convert.py`:**
Pattern: `gws.*gmail` + `(messages|threads).get` + `"format":"(full|minimal|raw)"` → deny unless `email_convert.py` is present in the command.
Email body reads go to `shared/tools/email_convert.py` (L0 scrub + heuristic injection scan + Sentinel gate). The Email Service layer sits above this: `email_service_read.py` / `read_thread(thread_id, desk)` is the sanctioned store-first read path (LIVE 2026-07-10; all four ingest desks wired). `load_digest()` is retired v1.

**(d) Calendar events read — must route through `safe_calendar.py`:**
Pattern: `(gws|.cargo/bin/gws).*calendar` + `calendar events list` → deny unless `safe_calendar.py` is present.
Wrapper: `python3 system/tools/safe_calendar.py '<params-json>'` — takes the same params JSON as `gws calendar events list --params`. Default behavior: returns structural fields + a `_reader_scratch` pointer; free-text moved to `/tmp/rdr` scratch for a spawned tool-less `ingest-reader` sub-agent. Flags: `--redact` (text with injection spans neutralized, for store/vault paths), `--no-isolate` (raw, no-LLM plumbing only).

**(e) Google Tasks read — must route through `safe_tasks.py`:**
Pattern: `(gws|.cargo/bin/gws) tasks tasks (list|get)` → deny unless `safe_tasks.py` is present.
Wrapper: `python3 system/tools/safe_tasks.py '<params-json>'` — same isolation model as `safe_calendar.py`. (Listing tasklists — `gws tasks tasklists list` — is structural metadata, not gated.)

**(j) gws drive files export — must route through a safe reader:**
Pattern: `(gws|.cargo/bin/gws|/opt/homebrew/bin/gws).*drive.*files.*export` → deny unless `safe_read.py` or `safe_docx.py` or `safe_pdf.py` is present in the command. Raw export dumps a client-authored Google Doc straight to context (the #1 doc-injection channel after email).

**SCRATCH-DIR LOCK (F2.1c, 2026-07-04):** the main/controller session may NOT directly Read `/tmp/rdr/*` or `/tmp/ingest_body/*` — only a spawned tool-less `ingest-reader` sub-agent (detected by `agent_id` populated in hook input) may read those paths. This structurally enforces the reader-actor split for both interactive and cron sessions.

**Email-summary store guard (Ra-2):** non-janitor writes to `state/email-summary/threads-v2/` are blocked. Only `email_summary_sync.py` (the janitor) may write the store. Un-wrapped Bash reads of the v2 store are also blocked; use `email_service_read.py` adapter.

**Item-store guard (CT-1):** same pattern for `state/item-store/` — only `tasks_store_sync.py` / `calendar_store_sync.py` may write; reads must use `item_store_read.py`.

#### 4b. `enforce_email_sanitize.sh` — email sanitize guard (legacy, unregistered)
NOT currently registered in `settings.json` (confirmed 2026-07-24). File exists at `system/hooks/enforce_email_sanitize.sh` for historical reference. All six pre-Window-5 per-channel hooks are unregistered; `ingest_gate_enforce.sh` is the sole active enforcement path. Dates from 2026-06-13 (before the unified gate). Known debt: `[SECURITY-MINOR-2026-07-04]` — consider removing the six subsumed hook files to reduce clutter.

---

### 5. READ POLICY

**All STABLE READ capabilities run freely — no confirmation needed** (`google-policy.md §"Broadly Available"`):
Gmail: `read_threads`, `read_by_label`, `read_sent`, `read_snoozed` · Calendar: `read_events`, `list_calendars`, `free_busy` · Drive: `list_files`, `read_metadata`, `export_doc` · Docs: `read`, `export` · Sheets: `read` · Slides: `read` · Tasks: `read`, `list_lists` (READ paths live-verified 2026-03-27).

**But read sanitization still applies for attacker-controllable channels** (see §4).

**Metadata-only default for Gmail:** `format:"metadata"` returns headers only (Subject, From, To, CC, Date, labelIds). Always default to metadata for any call that does not require body content.

**Schema discovery:** `gws schema <service.resource.method>` — always use before guessing param shapes (`gws-contract.md §"Schema Discovery"`).

**Output:** all gws output is JSON. Parse with `python3 -m json.tool` or inline Python. Paginate with `--page-all` (returns NDJSON, one JSON object per page).

---

### 6. WRITE POLICY

**Show-before-execute (show_confirm = all WRITE_SAFE and above):** every write shows the user the exact command + JSON body and waits for explicit confirmation before executing. `gws` has no `--dry-run` flag; the confirmation model is the only pre-flight check (`gws-contract.md §"Read vs Write Policy"`).

**No silent overwrite** (`google-policy.md` prohibition #11): no wholesale document replacement, no Sheets range bulk-overwrite without before/after scope shown.

**No inferred write target** (#12): target resource must be named by the user in session OR declared as `canonical_write_targets` in desk CLAUDE.md. No best-guess selection.

**Calendar writes — Agent Ops calendar only** (`block_primary_calendar.sh`): calendarId must be the Agent Ops ID. Personal primary (`you@example.com`) is read-only for all desks.

**Admin exception — authorized governance work only:** the policy prohibitions lift ONLY under all three conditions: (a) root mode, (b) explicit user instruction naming the specific file(s), (c) authorized governance/maintenance purpose — NOT workflow execution (`google-policy.md §"Admin Exception"`). Agents do not self-authorize.

---

### 7. PER-SERVICE CALL PATTERNS (concrete values from `gws-contract.md`)

**Gmail metadata-safe (all desks, default):**
```bash
/opt/homebrew/bin/gws gmail users messages get \
  --params '{"userId":"me","id":"MESSAGE_ID","format":"metadata"}' 2>/dev/null
```

**Calendar events list — MUST use safe_calendar.py wrapper:**
```bash
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python3 '$LIFEHACK_ROOT/system/tools/safe_calendar.py' \
  "{\"calendarId\":\"you@example.com\",\"maxResults\":50,\"singleEvents\":true,\"orderBy\":\"startTime\",\"timeMin\":\"$TS\"}"
```

**Calendar write (Agent Ops calendarId required):**
```bash
/opt/homebrew/bin/gws calendar events insert \
  --params '{"calendarId":"<agent-ops-calendar-id>"}' \
  --json '{"summary":"Event","start":{...},"end":{...}}'
```

**Sheets read (bare range, safe):**
```bash
/opt/homebrew/bin/gws sheets spreadsheets values get \
  --params '{"spreadsheetId":"ID","range":"A1:Z100"}' 2>/dev/null
```

**Sheets write (requires LLM_GUIDE read first; confirm-gate for destructive ops):**
```bash
# 1. Read _LLM_GUIDE tab first (sets the marker)
# 2. Then write
/opt/homebrew/bin/gws sheets spreadsheets values append \
  --params '{"spreadsheetId":"ID","range":"A1","valueInputOption":"USER_ENTERED","insertDataOption":"INSERT_ROWS"}' \
  --json '{"values":[["col1","col2"]]}' 2>/dev/null
# For destructive ops: set LIFEHACK_SHEET_CONFIRM=1 after the operator's explicit yes
```

**Tasks read — MUST use safe_tasks.py wrapper:**
```bash
python3 '$LIFEHACK_ROOT/system/tools/safe_tasks.py' \
  '{"tasklist":"@default","maxResults":100}'
```

---

### 8. INTEROP SEAMS

```
TRIGGERS    ingest-gate (ingest_gate_enforce.sh)   · fires on every gws Gmail/calendar/tasks/drive-export Bash call
GUARDED-BY  guard_gws_logout.sh                   · blocks auth destruction — root backstop
GUARDED-BY  block_primary_calendar.sh             · all calendar writes must target Agent Ops calendar
GUARDED-BY  guard_sheet_writes.sh                 · Sheets write requires LLM_GUIDE read; destructive ops need confirm
GUARDED-BY  guard_sheet_formula_writes.sh         · blocks formula injection in Sheets values
GUARDED-BY  guard_tasks_writes.sh                 · protects Life Map (read-only) from agent writes
READS       google-capability-registry.yaml       · tiers + risk classes + per-desk access model
READS       gws-contract.md                       · canonical invocation patterns, auth, quoting rules
READS       google-policy.md                      · prohibitions, admin exception, guarded capability list
WRITES→     planning (planning-daily, planning-weekly)   · calendar events read/write through this plane
WRITES→     email-ingest (planning-daily + the donor's cal-recon, emily, deryl, clair)  · Gmail reads through this plane via email_convert.py / email_service_read.py
WRITES→     sheets-desks (deryl DFM, clair billing, reconcile)        · Sheets reads/writes through this plane
FEEDS       safe_calendar.py                      · gws-plane invokes; the wrapper sanitizes calendar event free-text
FEEDS       safe_tasks.py                         · gws-plane invokes; the wrapper sanitizes task title/notes
FEEDS       email_convert.py / email_service_read.py  · gws Gmail body goes through before reaching model context
KEYS-OFF    settings.json permissions.deny list   · `gws auth logout`, auth login, ~/.config/gws/ all deny-listed
SYNCS       grand-central (skill routing)          · Google-touching skills (planning, emily, deryl, marc, clair) route through desks that invoke this plane
COMPLEMENTS security-ingest-gate                   · ingest_gate_enforce.sh overlaps — the ingest gate IS the on-path enforcement arm of this plane for read channels
```

---

### GAPS

1. **`block_primary_calendar.sh` MCP bypass** — the hook matches only Bash/gws. A write via the Claude.ai MCP Google Calendar connector would bypass this guard entirely, landing on `primary`. Known, tracked: `[CAL-WEEKLY] MCP-matcher calendar guard hook` (`debt-ledger.md`). Real blast-radius: an MCP-path calendar write could corrupt personal events. `→ ·gap`

2. **Belt-and-suspenders hook redundancy** — six per-channel hooks (enforce_email_sanitize · sanitize_calendar_reads · guard_file_reads · guard_web_fetch · guard_web_search · guard_skip_safe_backdoor) were subsumed by `ingest_gate_enforce.sh` (Window-5, 2026-07-03), but some may still be registered in `settings.json`, firing redundantly. Verified: `enforce_email_sanitize.sh` is still present in hooks/ directory (unregistered or redundant). Tracked: `[SECURITY-MINOR-2026-07-04]`. Blast-radius: performance only (double-fire); no safety gap.

3. **`guard_sheet_formula_writes.sh` named-tab false-positive** — the hook's own verification read (`gws sheets spreadsheets values get --params '{"spreadsheetId":"...","range":"Tab!A1:B2",...}'`) fail-closes on zsh `!` quoting errors, blocking a legit plain-cell update targeting a named tab even when the cell is not a formula. `guard_sheet_writes.sh` is unaffected (it makes no gws reads). Server-side cron (Python subprocess) is unaffected. Tracked: `[SHEET-GUARD-NAMEDTAB]`.

4. **gws token expiry (1h access token)** — never formally verified that gws re-auths cleanly after the 1h OAuth access token expires during a long session. System typically runs nightly cron, not long-lived sessions, so practically fine, but unverified. Tracked: `[GWS-CRON-1H]`.

5. **gws on cargo on the second machine** — the second machine still has `~/.cargo/bin/gws` rather than the Homebrew path `/opt/homebrew/bin/gws`. Known: `[SECOND-MACHINE] gws still on cargo on the second machine` (`debt-ledger.md`). Risk: gws-contract.md contract examples use the Homebrew absolute path; cargo path still matches the hook regexes (hooks pattern on `gws` token, not path), so enforcement holds. But the contract version pinning (`0.22.3`) cannot be guaranteed on the cargo binary.

6. **Non-email gws channel sweep incomplete** — Tasks and Drive channels were hardened (2026-07-04 CT-1), but the `[GWS-CHANNEL-SWEEP]` debt item (`debt-ledger.md`) notes Sheets cell text and Gmail metadata (subjects) haven't been confirmed sanitized-or-explicitly-cleared for injection risk. Monitoring state.

7. **planning-health unsanitized Gmail headers — DONOR-ONLY, the function did not migrate.** The donor's `cal-health.py::read_snoozed()` returned subject/from without the L0 `sanitize()` that `planning-light-sweep.py` applies. ⚠ Verified this session: `system/tools/planning-health.py` has **no `read_snoozed`** — the snoozed-mail read was trimmed in the port, so the gap it describes cannot fire here. Kept as donor description, still tracked upstream as `[CAL-HEALTH-SANITIZE]`.

---

## UNVERIFIED

- `safe_calendar.py` and `safe_tasks.py` exist in the git clone at `system/tools/` (confirmed by `ls` this session). Their Drive copies (`$LIFEHACK_ROOT/system/tools/`) returned "NOT FOUND" — likely a Drive path resolution issue at audit time, not actual absence. INFERRED: they exist on Drive (the contract references them, skills invoke them, debt items reference them as LIVE). `→ [UNVERIFIED: Drive path resolution for safe_calendar.py / safe_tasks.py]`
- `enforce_email_sanitize.sh` registration status in `settings.json` — confirmed NOT registered (2026-07-24). The hook file exists in `system/hooks/` but does not appear in `settings.json`. `ingest_gate_enforce.sh` is the sole active Bash PreToolUse gate for email. All six pre-Window-5 per-channel hooks are unregistered.
- guard_sheet_formula_writes.sh — file confirmed present; full logic not read this session. INFERRED from name, guard_sheet_writes.sh header ref, and registry `global_deny: sheets.formula_injection`. `→ [UNVERIFIED: exact guard_sheet_formula_writes.sh implementation details]`

---

## MATURITY LABEL

**`LIVE·gap`** — the primary enforcement mechanisms (guard_gws_logout, block_primary_calendar, ingest_gate_enforce, guard_sheet_writes, guard_tasks_writes) are all registered PreToolUse hooks firing at exit 2. The plane is architecturally sound and has defended real incidents (auth destruction 2026-06-01, primary calendar corruption, email injection channel). The `·gap` marker is warranted for the MCP bypass on calendar writes (real blast-radius: personal event corruption), which makes a tip-only reader over-trust the calendar write guard's scope.

**Provisional notes:**
- The legacy per-channel hooks (enforce_email_sanitize, sanitize_calendar_reads, etc.) being subsumed but possibly still registered is an implementation detail, not a posture gap.
- The `guard_sheet_formula_writes.sh` named-tab FP is a false-block (too restrictive), not a false-allow (safety breach) — it makes the guard harder to use but not less secure.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** gws is the single, locked, Bash-only conduit for every Google Workspace read and write —
one binary, one auth path, one write-guard stack — so that no skill or desk ever talks to Google
directly, and every dangerous verb (calendar write, sheet write, task write, auth logout) passes
through a hook before it executes.

**Current state → LIVE·gap:** the core write-guard stack is real and has defended actual incidents —
`guard_gws_logout.sh` stopped the credential-destruction failure mode that hit 2026-06-01,
`block_primary_calendar.sh` stops Claude's default-to-`primary` corruption, and `ingest_gate_enforce.sh`
+ `guard_sheet_writes.sh` + `guard_tasks_writes.sh` are all registered PreToolUse hooks firing on every
matching Bash call. The `·gap` is earned honestly: `block_primary_calendar.sh` matches Bash/gws only,
so an MCP-path Google Calendar write bypasses it entirely and could land on `primary` — currently
dormant only because the MCP connectors are disconnected.

**TARGET:** close the MCP calendar bypass when the connectors come back online (add an MCP matcher to
`block_primary_calendar.sh`, or accept the gap only as long as connectors stay disabled — see "DESIGN
FORK FOR MORNING" below); migrate the second machine off the cargo-installed `gws` onto the pinned
Homebrew binary; confirm gws token-refresh behavior across a long-running session; finish the
non-email channel sweep (Sheets cell text, Gmail subjects) for injection-risk clearance
(`[GWS-CHANNEL-SWEEP]`).

---

## AUTO-COMPUTED   (machine-only — Feature 1.5 checker writes this)

```yaml
maturity_label: LIVE·gap
check_detail: UNSET
```

---

## DESIGN FORK FOR MORNING

**Single design question requiring the operator's call:**

> **MCP calendar guard scope** — `block_primary_calendar.sh` is Bash-only. MCP Google Calendar writes bypass it entirely (known gap, `[CAL-WEEKLY] MCP-matcher calendar guard hook`). The Claude.ai connectors are currently disconnected (`[COWORK-MCP-CONNECTOR-RETEST]` blocked), so this is dormant. When connectors come back online: (a) add an MCP PreToolUse matcher to `block_primary_calendar.sh` blocking the MCP `create_event`/`update_event` tools from targeting primary, OR (b) accept the gap as long as the MCP connectors remain disabled and revisit when the cowork build activates them.

Recommendation: (a) is the right long-term answer (close the structural gap), but (b) is the correct near-term posture since the connectors are offline. Wire the fix as part of `[COWORK-MCP-CONNECTOR-RETEST]` (not a standalone security sprint).
