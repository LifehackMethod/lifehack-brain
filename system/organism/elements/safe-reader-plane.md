---
element: safe-reader-plane
title: "safe-reader-plane — element detail (ground/base altitude)"
subsystem: security-ingest
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C2 exception — the egress seal is never armed; runtime-constructed URLs bypass the L2 domain gate. ⚠ CORRECTED 2026-08-15 — the first clause is out of date. The egress seal was BUILT OUT into a switchable Level-2 wall: a persistent switch file, three named states (OFF / ON / AMBIGUOUS, no quiet fourth), a --l2-status flag, and 12 tests. It SHIPS OFF and no caller arms it, so by default it still seals nothing — but a half-configured list now REFUSES rather than passing, and an unsealed read says so out loud. Read the clause as 'the seal ships off and is unwired', not 'the seal does not exist'. The runtime-constructed-URL clause is unchanged and still true. See the CORRECTION banner in the body."
generated_from:
  - system/tools/safe_fetch.py
  - system/tools/safe_calendar.py
  - system/tools/safe_tasks.py
  - system/tools/safe_search_api.sh
  - system/tools/safe_input.py
  - system/tools/sanitize.py
  - system/tools/safe_read.py
  - system/tools/safe_pdf.py
  - system/tools/safe_docx.py
  - system/tools/safe_xlsx.py
  - system/tools/safe_csv.py
  - shared/tools/email_convert.py
  - system/hooks/ingest_gate_enforce.sh
  - system/hooks/guard_file_reads.sh
  - system/hooks/guard_web_fetch.sh
  - system/hooks/guard_web_search.sh
  - system/hooks/guard_skip_safe_backdoor.sh
  - system/reference/settings.json (PreToolUse hook registrations)
  - state/debt-ledger.md (EGRESS-WALL-FAILOPEN, SECURITY-READER-ACTOR, CAL-EMAIL-FALLBACK-REMOVE)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# safe-reader-plane — element detail

> **Altitude = BASE (ground / street view).** Full mechanics of every sanitized-read tool and the
> hook enforcement layer that forces routing through them. The MIDDLE index (`system/organism/manual.md`)
> carries only an interop pointer; the TIP shows only the subsystem box + arrows; the **live artifacts**
> (`system/tools/safe_*.py`, `system/hooks/ingest_gate_enforce.sh`) are the fourth level — executable
> ground truth. This entry is the UNDERSTANDING layer: exhaustive description of what each tool does,
> why it exists, and how they connect as a cluster.
>
> **One-line:** every byte of external content — web, email, calendar, tasks, documents, search results —
> passes through a two-layer filter (L0 deterministic scrub + heuristic injection scan) before the model
> ever reads it, and a hook plane blocks every raw-read bypass.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a registered PreToolUse guard fires, exits 2 on deny) · `[skill]` (skill
> or script logic — mandatory but no blocking hook) · `[honor]` (prose instruction only, no mechanical
> enforcement) · `[human]` (deliberate HITL pause).
>
> ⏳ **Citation note — `unruled`.** `system/reference/settings.json` is named throughout this
> element as the hook-registration source because that is where the donor repository keeps its
> reference copy. It is on no ship list here and no ruling has placed it — a DEBT, not a pass.
> The registrations themselves live in this repository at `.claude/settings.json`.

> **⚠ CORRECTION — 2026-08-15 — the `safe_fetch.py` egress seal was ARMED. It still ships OFF.**
> Every statement below that this element's per-run domain seal is *never armed*, *unarmed*, *exists in code
> but is never set*, or *structurally present but functionally unarmed* — chiefly the GAPS entry and the
> CURRENT/TARGET block — **was true when this element was authored on 2026-07-24 and is false as of today.**
> Each site is struck and dated in place; this banner is the one full statement. Enver ruled it
> (`authority: user`: *"APPROVED — ARM IT"*), to a shape already ruled: three honest levels, default off,
> activatable.
>
> **What shipped, verified this session.** A persistent switch file `system/safe-fetch-allowlist.md` — a
> one-word `on`/`off` switch plus a domain block, using the same marker convention as
> `system/egress-allowlist.md` — and a new `l2_state()` in `system/tools/safe_fetch.py` that resolves every
> read to **three named outcomes and no quiet fourth**: **OFF** — allowed, and it *announces on stderr, once
> per process,* that the seal is not in force; **ON** — enforced, an off-list host refused **before the socket
> opens**; **AMBIGUOUS** — **refused**. Precedence: the `SAFE_FETCH_ALLOWLIST` env var is the **per-run** seal
> and **outranks** the file; the file is the **persistent** switch. A `--l2-status` flag reads the position
> without fetching. `system/tools/test_egress_level2.py` holds 12 tests, passing inside
> `system/tools/run-all-tests.sh`.
>
> ⚠ **THIS IS NOT "THE EGRESS WALL IS NOW ENFORCED," AND THE `LIVE·gap` LABEL WAS NOT CHANGED.** It ships
> `off` with an empty domain block, and `--l2-status` printed, this session: *"L2 egress allowlist: OFF — web
> reads are not sealed to a domain list."* **By default it seals nothing, and no reader in this plane arms
> it.** The honest claim is **armed and switchable, ships OFF, and refuses loudly when half-configured** —
> five ambiguous states now REFUSE rather than pass, including *domains listed while the switch still reads
> `off`*, the believable human error. What improved is that the level you are actually at is knowable and
> stated; a wall did not go up.
>
> ⚠ **Unchanged:** runtime-constructed URLs still bypass the Bash-command domain hook, that hook still **fails
> OPEN deliberately** (it fronts every Bash call, where a false positive gets the guard unregistered — this
> seal fronts web reads only), and the **OS firewall (LuLu) remains the only HARD wall and is still not
> included**. The reader-actor structural wall — the tool-less reader — is untouched by any of this and
> remains this plane's real guarantee.

---

## AUTHORED   (human-only)

### THE CLUSTER MODEL — why this is one element, not many

The safe-reader plane is a **cluster**: a set of purpose-built per-channel tools + a shared core + a
unified blocking hook plane. The tools handle channel-specific extraction (HTML stripping, MIME walking,
hidden-text removal, quote/sig stripping, reader-actor isolation); the shared core (`sanitize.py` +
`safe_input.py`) applies L0 + heuristic scanning; and the enforcement layer (`ingest_gate_enforce.sh`
registered on Bash/WebFetch/WebSearch/Read) blocks any attempt to bypass the cluster.

Each tool is described in its own sub-section below; the hook plane follows; then GAPS and INTEROP.

---

### THE SHARED CORE — two layers every tool runs

**Layer 0 — L0 deterministic scrub (`sanitize.py`)**

`sanitize.py` (`system/tools/sanitize.py`) is the deterministic foundation. It runs on EVERY channel.
Steps (in order):
1. HTML entity unescape (`html.unescape`) — surfaces entity-encoded payloads as plain text before matching.
2. Inline HTML tag removal (`re.sub(r"<[^>]{0,200}>", " ", s)`) — strips markup without a full DOM parse.
3. Unsafe Unicode removal — strips zero-width chars (`\U0000200B–\U0000200F`), bidi overrides (`\U0000202A–\U0000202E`),
   invisible operators, deprecated format chars, BOM (`﻿`), C0/C1 controls, and the Unicode Tags
   block (`\U000E0000–\U000E007F`). These are stego/injection carriers invisible to humans.
4. Whitespace collapse (`re.sub(r"\s+", " ", s).strip()`).
5. Optional length cap (default 200 chars for fields, 800 for bodies, `NO_CAP=0` to disable — email
   bodies and web pages always use `NO_CAP` to prevent truncation from hiding a tail-planted payload).

`email_convert.py` uses a line-preserving wrapper (`_sanitize_preserving_lines`) that scrubs each line
independently so multi-line quote/sig strippers still work after L0.

**Layer 1 — heuristic injection scan (`safe_input.py`)**

`safe_input.py` (`system/tools/safe_input.py`) runs AFTER L0. It applies:
1. **Evasion defang** — NFKC normalization + homoglyph-fold (Cyrillic/Greek lookalikes → ASCII) +
   one URL-decode layer (decoded text appended alongside original so both surfaces are scanned).
2. **Pattern matching** — 43 regex patterns covering: instruction override, system-prompt injection,
   role reassignment, behavioral redirect, base64-obfuscated payloads, data-exfiltration requests,
   simulated role-play escapes.
3. **Provenance routing** — `provenance_route(desk, channel, content, item=...)` stamps every sanitized
   read with a desk tag + channel breadcrumb for the ingest-coverage organ (organism Window 5). This
   fires regardless of verdict, ensuring every external read is witnessed.
4. **Exit codes** — exit 0 = CLEAN; exit 1 = FLAGGED (patterns found, content still returned on stdout
   for the caller to decide); exit 2 = setup/call error.

---

### PER-CHANNEL TOOLS

#### `safe_fetch.py` — web URL fetcher [hook enforced via ingest_gate_enforce.sh]

**Purpose:** mandatory replacement for the native `WebFetch` tool. Fetches a URL and returns clean
plaintext.

**Trigger:** any web URL fetch. Called via `python3 system/tools/safe_fetch.py '<URL>'`.

**Steps:**
1. **Egress allowlist check** — `_enforce_egress_allowlist(url)` (added 2026-07-02, reader-actor build):
   - Blocks non-http(s) schemes (SSRF hygiene) — raises immediately before any socket opens.
   - If `SAFE_FETCH_ALLOWLIST` env var is set (comma-separated domains), rejects any URL whose host is
     not in that list or a subdomain of it. ~~Unset = no allowlist enforcement (backward-compatible).~~
   - ~~This is the per-run domain seal; see GAPS for its current unarmed state.~~
   - ⚠ **CORRECTED 2026-08-15** — the unset case is no longer a silent no-op. `l2_state()` falls through to
     the persistent switch file `system/safe-fetch-allowlist.md` and returns one of three named outcomes:
     **OFF** (the shipped state — the read proceeds, *and one stderr line says the seal is not in force*, so
     the caller is never left assuming a wall), **ON** (an off-list host raises before the socket opens), or
     **AMBIGUOUS** (**the read is REFUSED**, naming the file and the line to fix). The env var remains the
     **per-run** seal and outranks the file; an empty value counts as unset. `--l2-status` reports the
     position without fetching. It **ships OFF**, so by default this step still enforces only the scheme
     check.
2. **HTTP fetch** — `urllib.request.urlopen` with a 10-second timeout, 2 MB body cap, custom User-Agent.
   Raises `RuntimeError` on network error.
3. **Charset detection** — from `Content-Type` header or HTML meta tag; falls back to UTF-8.
4. **HTML-to-text extraction** (`_TextExtractor` HTMLParser subclass):
   - Skips entire subtrees for `script`, `style`, `nav`, `footer`, `head`, `noscript`, `template`,
     `svg`, `math` — these are invisible to humans but visible to the model (prompt injection vectors).
   - Skips elements hidden via inline CSS (`display:none`, `visibility:hidden`, `opacity:0`,
     `font-size:0`, `color:transparent`).
   - Falls back to raw text if no visible text is extracted (handles plain-text URLs).
5. **L0 sanitization** — `sanitize(visible_text, max_len=NO_CAP)`.
6. **Heuristic scan** — `scan_for_injection(clean)` flags patterns to stderr; `provenance_route` always
   runs (clean or flagged) for coverage.

**Enforcement:** `ingest_gate_enforce.sh` (case `WebFetch`) blocks the native `WebFetch` tool with
exit 2; `guard_web_fetch.sh` is the older per-channel hook (still registered on some machines —
UNVERIFIED whether both fire or one is superseded). `LIFEHACK_SKIP_SAFE_FETCH=1` bypass is human-shell
only; `guard_skip_safe_backdoor.sh` (subsumed into `ingest_gate_enforce.sh` case `Bash`·(a)) blocks
an agent from setting it.

**Stores read:** external HTTP(S) endpoint (untrusted). **Stores written:** none (returns stdout).

---

#### `safe_search_api.sh` — Serper API web search

**Purpose:** sanitized Google search via the Serper REST API. Primary search path for all sessions and
subagents (subagents CANNOT run the `/websearch` skill — they MUST call this script via Bash).

**Trigger:** any web search. Called via `bash system/tools/safe_search_api.sh 'query'`.

**Steps:**
1. **Cost guard** — daily call counter in `/tmp/serper_calls_YYYYMMDD.log`; cap defaults to 500
   (`SERPER_MAX_DAILY` env override). Breach → exit 2 (triggers `/websearch` Chrome fallback).
2. **API key retrieval** — `security find-generic-password -s "serper-api-key" -a "lifehack"` (macOS
   keychain; key is NEVER echoed or printed).
3. **Serper POST** — `https://google.serper.dev/search` with JSON payload `{"q": query, ["tbs": tbs]}`.
   `--tbs` flag accepts time-filter strings (e.g. `qdr:w` = past week). Python stdlib only, no pip.
4. **JSON reduction** — extracts answer box, knowledge graph, organic results (top 10), People Also Ask
   (top 5). Returns `__SERPER_ERROR__` sentinel on HTTP/auth failure for the wrapper to distinguish.
5. **Sanitization** — result text piped through `python3 safe_input.py -` (L0 + heuristic scan).

**Enforcement:** `ingest_gate_enforce.sh` (case `WebSearch`) blocks native `WebSearch` with exit 2;
`guard_web_search.sh` is the older per-channel hook (same supersession note as `guard_web_fetch.sh`).

**Stores read:** `https://google.serper.dev/search` (trusted API endpoint). **Stores written:** none.

---

#### `safe_calendar.py` — Google Calendar reader

**Purpose:** sanitized replacement for raw `gws calendar events list`. A calendar invite's title,
description, location, and attendee/organizer/creator displayName are **attacker-controllable free text**
— anyone who knows the calendar address can send an invite and set these fields.

**Trigger:** any calendar read. Called via
`python3 system/tools/safe_calendar.py '<params-json>'`.

**Modes (set by flag, secure by default):**
- **`--isolate` (DEFAULT, 2026-07-04):** every free-text field is moved to a LOCKED scratch file at
  `/tmp/rdr/cal_<sha256>.txt` and replaced on stdout with the marker
  `⟦reader-scratch — spawn ingest-reader on _reader_scratch⟧`. The controller sees structural fields
  only (id, start, end, status) + a `_reader_scratch` pointer. A spawned tool-less `ingest-reader`
  sub-agent must consume the scratch. This is the reader-actor split (2026-07-04).
- **`--redact`:** free-text left in-place (on stdout) but with flagged injection spans neutralized —
  for the `cal-vault` store path where the text must persist.
- **`--no-isolate`:** plumbing/no-LLM path — sanitized text left visible; no scratch isolation.

**Steps (all modes):**
1. Validates params is valid JSON (never hands gws an arbitrary string).
2. Runs `gws calendar events list --params <json>`.
3. Walks every event: sanitizes `summary`, `description`, `location`, attendee `displayName`, organizer
   and creator `displayName` via `safe_input.process()` (L0 + heuristic, same as every other channel).
4. In isolate mode: writes free-text to scratch (`/tmp/rdr`), replaces fields with marker on stdout.
5. Provenance route (`safe_input.provenance_route`) fires on all assembled free-text — clean or flagged.
6. Exit 0 = CLEAN, exit 1 = FLAGGED, exit 2 = call error.

**Enforcement:** `ingest_gate_enforce.sh` case `Bash`·(d) — any `gws calendar events list` command NOT
routing through `safe_calendar.py` is blocked with exit 2. `[hook]`
The scratch-dir lock (case `Read` + case `Bash`·(b)) blocks the main session from reading
`/tmp/rdr/*` directly. `[hook]`

**Stores read:** `gws calendar events list` → Google Calendar API. **Stores written:** `/tmp/rdr/cal_*.txt` (scratch, isolate mode).

---

#### `safe_tasks.py` — Google Tasks reader

**Purpose:** sanitized replacement for raw `gws tasks tasks list|get`. Task title and notes are
user-controlled free text — any integration that writes to Google Tasks (or the user themselves) can
plant a payload.

**Trigger:** any Google Tasks read. Called via
`python3 system/tools/safe_tasks.py '<params-json>'` (list) or
`python3 system/tools/safe_tasks.py --get '<params-json>'` (single task).

**Modes:** identical to `safe_calendar.py` — `--isolate` (DEFAULT), `--redact`, `--no-isolate`.

**Steps:**
1. Validates params is valid JSON.
2. Runs `gws tasks tasks list|get --params <json>`.
3. Sanitizes `title` and `notes` fields per task via `safe_input.process()`.
4. Isolate mode: moves free-text to `/tmp/rdr/tasks_<sha256>.txt`, replaces with marker on stdout.
5. Provenance route fires on all assembled free-text.
6. Exit 0/1/2 same as `safe_calendar.py`.

**Enforcement:** `ingest_gate_enforce.sh` case `Bash`·(e) — any `gws tasks tasks list|get` NOT routing
through `safe_tasks.py` is blocked. `[hook]`

**Stores read:** `gws tasks tasks list|get` → Google Tasks API. **Stores written:** `/tmp/rdr/tasks_*.txt` (scratch, isolate mode).

---

#### `email_convert.py` — Gmail thread converter + email sanitizer (`shared/tools/`)

**Purpose:** the universal email body sanitizer. All Gmail body reads MUST route through this tool.
Email bodies are the #1 prompt-injection channel. Handles MIME extraction, HTML-to-text fallback,
L0 sanitization, heuristic scan (wired to the on-path ingest gate), quote/sig stripping, and faithful
thread assembly.

**Trigger:** any Gmail body read. Called via:
`python3 shared/tools/email_convert.py --threads <ID> [--out-dir PATH] [--messages all|thread|first|last|both]`
or `--query <gmail-query>` or `--label <label-id>`.

**Key steps:**
1. **Fetch** — `gws gmail users threads get --params {userId: me, id: ..., format: full}`.
2. **MIME extraction** — `extract_body_texts(payload)`: text/plain preferred; HTML fallback if no
   plain-text part (`html_to_text` via `_HTMLTextExtractor` — stdlib HTMLParser with `convert_charrefs=True`,
   skipping `script/style/head/title/noscript`, suppressing comments). Source (`text/plain` vs `text/html`) is tracked and
   surfaced in the run manifest.
3. **L0 sanitization** — `sanitize(body, max_len=NO_CAP)` on every body; `_sanitize_preserving_lines`
   for multi-message thread paths (preserves line structure for quote/sig strippers). Headers also
   sanitized with `NO_CAP`.
4. **Heuristic scan + ingest gate** — `_flag_injection` routes findings through
   `shared/tools/ingest_gate.gate()` at `source_type="email"` with a `FLAG-only` floor (email can
   never auto-trigger a DANGER/quarantine, which would false-positive on security newsletters etc.).
   Falls back to stderr-only if the gate is unimportable (graceful degradation).
5. **Quote stripping** — `strip_quoted_text` (7 pattern detectors: `>` quote lines, Gmail "On … wrote:",
   split-header pattern, Outlook `From:`/`Sent:` block, `--- Original Message ---`, underscore separator,
   forwarded block). Conservative by design: cuts at the FIRST detected boundary.
6. **Signature stripping** — `strip_signature` (3 conservative patterns only: RFC 3676 `-- ` delimiter,
   mobile footer regex, legal disclaimer opener). Never cuts soft sign-offs ("Best regards," alone) —
   faithful bias.
7. **Thread mode (`--messages thread`, Wc-1)** — `build_clean_thread`: per-message `clean_message`
   (sanitize → scan → quote-strip → sig-strip), then assembles a de-duplicated JSON with
   `{thread_id, subject, message_count, messages[], attachments[], cleanliness{residual_quote_ratio}}`.
   This is the Email Service v2 write path (janitor `email_summary_sync.py` writes the faithful store).
8. **Attachment handling** — `extract_attachment_meta` walks MIME tree collecting
   `{filename, mimeType, size, attachmentId, message_id}` pointers ONLY. No attachment body downloads.
   Policy: metadata PERMITTED, bodies FORBIDDEN.
9. **Sentinel audit** — `_audit_email_read(thread_id, lane, message_count)` appends a metadata-only row
   to `~/.claude/logs/email-reads.jsonl` for every thread read. Content is NEVER logged.
10. **Lane label** — `_active_email_lane()` returns the active desk slug (env `TRUSTED_EMAIL_LANE` or
    `~/.claude/current_email_lane`) or None. The lane gate was RETIRED 2026-06-19 (the operator); lane now
    labels the audit row only. The universal sanitizer is the sole defense.

**Enforcement:** `ingest_gate_enforce.sh` case `Bash`·(c) blocks any `gws gmail` body read
(`messages.get`/`threads.get` with `format:full|minimal|raw`) NOT routing through `email_convert.py`.
`[hook]`
Also: case `Read`·(email-summary store) and case `Bash`·(g) block un-wrapped reads of the v2 faithful
store (`state/email-summary/threads-v2/`) — must use `email_service_read.py` adapter. `[hook]`

**Stores read:** `gws gmail users threads get`. **Stores written:** `--out-dir PATH` (caller-specified);
the janitor writes `state/email-summary/threads-v2/`.

---

#### `safe_read.py` — external plain text / Markdown file reader

**Purpose:** sanitized reader for external `.txt` / `.md` files — files outside the trusted zone
(the clone `~/lifehack-brain`, `~/.claude`, the Drive `Lifehack` spine). Internal files (skills,
docs, plans, records, canon) still use the `Read` tool directly.

**Trigger:** any Read of a `.txt` / `.md` file outside the trusted zone; also the ClaudeGate
(`~/Desktop/ClaudeGate.md`) two-way slot. Called via:
`python3 system/tools/safe_read.py [--clear-after] '<path>'`.

**Steps:** reads file (up to 5 MB; multiple encoding fallbacks), runs `sanitize(text, max_len=NO_CAP)`,
then the unified Sentinel gate (`safe_input.gate`). `--clear-after` blanks the file post-read (one-shot
drop-read semantics — NOT used for ClaudeGate which is a two-way overwrite slot, not a chute).

**Enforcement:** `ingest_gate_enforce.sh` case `Read`·(txt/md/markdown) blocks raw Read of external
text files with a fail-closed allowlist: paths under the clone, `~/.claude`, or the Drive spine are
allowed through; everything else is denied and redirected to `safe_read.py`. `[hook]`
ClaudeGate specifically: `ingest_gate_enforce.sh` blocks raw Read of `~/Desktop/ClaudeGate.md`. `[hook]`

---

#### Format-specific document readers (`safe_pdf.py`, `safe_docx.py`, `safe_xlsx.py`, `safe_csv.py`)

**Purpose:** sanitized readers for rich document formats where hidden/invisible content is the primary
injection vector.

| Tool | Format | Attack vector | What it strips |
|---|---|---|---|
| `safe_pdf.py` | PDF | White text, sub-4pt font, metadata fields | Hidden text, tiny font spans, metadata |
| `safe_docx.py` | DOCX/DOC | `w:vanish` hidden runs, near-white font | Hidden runs, invisible text |
| `safe_xlsx.py` | XLSX/XLS | Hidden sheets/rows, white font, formula injection | Hidden content; `=,+,-,@` formula starters |
| `safe_csv.py` | CSV | Formula injection cells | Cells starting with `=`, `+`, `-`, `@` |

All four run L0 sanitization after format-specific extraction. Usage:
`python3 system/tools/safe_{pdf,docx,xlsx,csv}.py [--desk <id>] '<path>'`.

**Enforcement:** `ingest_gate_enforce.sh` case `Read` (ext check) blocks raw Read on `.pdf`, `.docx`,
`.doc`, `.xlsx`, `.xls`, `.csv` with exit 2. `[hook]`
`guard_file_reads.sh` is the older per-channel hook (registered separately on some machines —
UNVERIFIED whether it still fires or is fully superseded by `ingest_gate_enforce.sh`). `[hook]` (UNVERIFIED)

---

### THE HOOK PLANE — enforcement layer

The unified enforcement gate is `ingest_gate_enforce.sh`, registered in `settings.json` as a
`PreToolUse` hook on **four matchers**: `Bash`, `WebFetch`, `WebSearch`, `Read`.

**Registration confirmed** (`system/reference/settings.json` lines ~212–250): four separate PreToolUse
blocks, each pointing to the same script with `statusMessage: "Unified ingest-gate enforcement..."`.

**What each case blocks (from the live script `system/hooks/ingest_gate_enforce.sh`):**

| Case | Trigger | Blocked by | Redirect |
|---|---|---|---|
| `WebFetch` | any WebFetch tool call | exit 2, always | `safe_fetch.py` |
| `WebSearch` | any WebSearch tool call | exit 2, always | `/websearch` or `safe_search.sh` (live hook deny message; note: `safe_search_api.sh` is the actual primary path but the deny text reflects the older Chrome redirect) |
| `Read` · ext check | Read on pdf/docx/doc/xlsx/xls/csv | exit 2 | `safe_{pdf,docx,xlsx,csv}.py` |
| `Read` · external txt/md | Read of .txt/.md outside trusted zone | exit 2 | `safe_read.py` |
| `Read` · ClaudeGate | Read of `~/Desktop/ClaudeGate.md` | exit 2 | `safe_read.py` (no --clear-after) |
| `Read` · scratch lock | Main session Read of `/tmp/rdr/*` or `/tmp/ingest_body/*` | exit 2 | spawn `ingest-reader` sub-agent |
| `Read` · email store | Read of `state/email-summary/threads-v2/*` | exit 2 | `email_service_read.py` |
| `Read` · item store | Read of `state/item-store/*` | exit 2 | `item_store_read.py` |
| `Bash`·(a) | `LIFEHACK_SKIP_SAFE_*=` assignment | exit 2 | never bypass |
| `Bash`·(b) | cat/head/tail of `/tmp/rdr/*` by main session | exit 2 | spawn `ingest-reader` |
| `Bash`·(c) | raw `gws gmail` body read | exit 2 | `email_convert.py` |
| `Bash`·(d) | raw `gws calendar events list` | exit 2 | `safe_calendar.py` |
| `Bash`·(e) | raw `gws tasks tasks list|get` | exit 2 | `safe_tasks.py` |
| `Bash`·(f) | non-janitor write to email-summary store | exit 2 | run janitor only |
| `Bash`·(g) | un-wrapped shell read of email-summary store | exit 2 | `email_service_read.py` |
| `Bash`·(h) | non-writer write to item store | exit 2 | run writers only |
| `Bash`·(i) | un-wrapped shell read of item store | exit 2 | `item_store_read.py` |
| `Bash`·(j) | raw `gws drive files export` (Phase 3.2) | exit 2 | export to file → `safe_read.py` / `safe_docx.py` |

**Fail posture:** CLOSED. The script begins `set -uo pipefail`; an unparseable JSON input → deny.
`AGENT_ID` is extracted from the hook input: populated only for spawned sub-agents. Used for the
scratch-dir lock: a sub-agent (tool-less `ingest-reader`) is ALLOWED to read `/tmp/rdr/*`; the main
session is denied.

**Retired hooks** (still exist on disk, unregistered, harmless):
- `guard_file_reads.sh` — per-channel file-read deny (superseded by `ingest_gate_enforce.sh`).
- `guard_web_fetch.sh` — per-channel WebFetch deny (superseded).
- `guard_web_search.sh` — per-channel WebSearch deny (superseded).
- `guard_skip_safe_backdoor.sh` — bypass var block (superseded by `Bash`·(a) inside the unified gate).

UNVERIFIED: whether the retired hooks remain registered anywhere outside `system/reference/settings.json`
(e.g. on the second machine or in a local `settings.json` that diverges from the reference). A
`grep` of the live `.claude/settings.json` per machine would confirm.

---

### TRIGGERS (full list)

All triggers are mediated by the hook plane (blocking) or by skill/CLAUDE.md convention (honor):

1. **Web URL fetch** → `safe_fetch.py` `[hook: WebFetch blocked]`
2. **Web search** → `safe_search_api.sh` (primary) or `safe_search.sh` (Chrome fallback) `[hook: WebSearch blocked]`
3. **Calendar read** → `safe_calendar.py` `[hook: raw gws calendar blocked]`
4. **Google Tasks read** → `safe_tasks.py` `[hook: raw gws tasks blocked]`
5. **Gmail body read** → `email_convert.py` `[hook: raw gws gmail body blocked]`
6. **PDF / DOCX / XLSX / CSV file read** → format-specific `safe_*.py` `[hook: Read on these extensions blocked]`
7. **External .txt / .md file read** → `safe_read.py` `[hook: Read on external path blocked]`
8. **ClaudeGate two-way slot** → `safe_read.py` (scan IN; Write tool for reply OUT) `[hook: raw ClaudeGate Read blocked]`
9. **Subagent reading gated scratch** → tool-less `ingest-reader` sub-agent on `/tmp/rdr/*` path `[hook: main-session Read of scratch blocked]`
10. **Google Drive export of external doc** → export to file → `safe_read.py` / `safe_docx.py` `[hook: raw gws drive export blocked]`

---

### STORES TOUCHED

| Store | Role | Mode | Notes |
|---|---|---|---|
| External HTTP(S) endpoints | Read source | `safe_fetch.py` | Egress allowlist check pre-socket |
| `https://google.serper.dev/search` | Read source | `safe_search_api.sh` | API key from keychain |
| Google Calendar API (via gws) | Read source | `safe_calendar.py` | Params validated as JSON first |
| Google Tasks API (via gws) | Read source | `safe_tasks.py` | list or get subcommand |
| Gmail API (via gws) | Read source | `email_convert.py` | thread format: full only |
| `/tmp/rdr/` (scratch) | Write + temp store | `safe_calendar.py`, `safe_tasks.py` | Isolate mode; main session blocked from reading by hook |
| `/tmp/ingest_body/` (scratch) | Write + temp store | `email_convert.py` output dir | Same scratch-dir lock applies |
| `state/email-summary/threads-v2/` | Write (janitor only) | `email_convert.py` via janitor | Single-writer invariant enforced by hook |
| `state/item-store/` | Write (store writers only) | calendar/tasks store syncs | Single-writer invariant enforced by hook |
| `~/.claude/logs/email-reads.jsonl` | Audit append | `email_convert.py` | Metadata-only rows; never content |

---

### GATES

| Gate | Enforcement | What it stops |
|---|---|---|
| `ingest_gate_enforce.sh` PreToolUse | `[hook]` HARD — exit 2 blocks the tool call | All raw reads of external content via WebFetch, WebSearch, Read, Bash gws commands |
| `AGENT_ID` scratch-dir lock | `[hook]` HARD — derived from PreToolUse hook input | Main session reading sanitized scratch; sub-agents allowed |
| Egress allowlist (`safe_fetch.py:_enforce_egress_allowlist`) | `[skill]` — raises before socket opens | Non-http(s) schemes (SSRF hygiene); out-of-allowlist domains when SAFE_FETCH_ALLOWLIST is armed. ⚠ CORRECTED 2026-08-15 — also refuses EVERY web read when the Level-2 switch is AMBIGUOUS (half-configured), and announces on stderr when it is OFF. Default is OFF, so by default this row stops only the scheme check |
| JSON params validation | `[skill]` — python `json.loads` pre-flight | Arbitrary string injection into gws CLI args |
| Receipt-gate (Bash`·(a)` bypass block) | `[hook]` HARD — blocks `LIFEHACK_SKIP_SAFE_*=` assignment by agent | Disabling the sanitization layer via env var |
| `ingest_gate.gate()` FLAG-floor for email | `[skill]` — coded into `email_convert._flag_injection` | Auto-DANGER on email (would false-positive security newsletters); floors any verdict at FLAG |
| Single-writer invariant (email-summary store) | `[hook]` HARD — `Bash`·(f)/(g) cases | Non-janitor writes and un-wrapped reads of the faithful-thread store |
| Single-writer invariant (item store) | `[hook]` HARD — `Bash`·(h)/(i) cases | Non-writer writes and un-wrapped reads of calendar/tasks store |

---

### INTEROP SEAMS

```
GUARDED-BY   ingest_gate_enforce.sh   · PreToolUse hook plane that forces all external reads through the safe-reader cluster
READS        safe_input.py / sanitize.py   · L0 + heuristic core shared by every channel tool
FEEDS        security-ingest-gate   · on-path Sentinel gate receives provenance_route breadcrumbs from every read
CHAINS       ingest-reader (sub-agent)   · tool-less reader consumes scratch files /tmp/rdr/* written by safe_calendar.py / safe_tasks.py
COMPLEMENTS  egress-allowlist-wall   · safe_fetch.py's _enforce_egress_allowlist is one layer; the OS-layer LuLu firewall is a parallel backstop
WRITES→      state/email-summary/threads-v2/   · email_convert.py (via janitor) writes the faithful-thread store
WRITES→      state/item-store/   · calendar/tasks store syncs write; item_store_read.py adapts reads
READS        email_service_read.py   · the read adapter for the v2 faithful-thread store (wraps re-scan + refuse-flagged + tool-less-reader routing)
KEYS-OFF     system/security-canon.md   · reader-actor split contract + channel classification lives there
COMPLEMENTS  /websearch skill   · skill wraps safe_search_api.sh (primary) + safe_search.sh (Chrome fallback) for interactive sessions
```

---

### GAPS

1. ~~**`SAFE_FETCH_ALLOWLIST` per-run domain seal is NEVER ARMED by any caller** (`[EGRESS-WALL-FAILOPEN]`,
   debt-ledger 2026-07-23). `safe_fetch.py` has `_enforce_egress_allowlist` which does nothing unless the
   env var is set. No caller sets it. A research sweep that follows a redirected URL could reach an
   off-list domain; the L2 domain gate is structurally present but functionally unarmed.
   `state:actionable` — needs a scoping pass before build.~~
   **⚠ RESTATED 2026-08-15 — the seal was BUILT. The gap narrowed; it did not close.** The text above is the
   2026-07-24 record, kept because it is what was true then. What is true now, verified this session: the seal
   is **armed and switchable** — a persistent switch file `system/safe-fetch-allowlist.md` beside the env var,
   `l2_state()` returning **OFF / ON / AMBIGUOUS** with no quiet fourth state, a half-configured setting
   **refusing every web read** instead of passing it, `--l2-status` to check the position without fetching,
   and 12 tests in `system/tools/test_egress_level2.py` inside `system/tools/run-all-tests.sh`. The scoping
   pass this gap asked for was ruled and executed by Enver (`authority: user`, *"APPROVED — ARM IT"*).
   **What is STILL a gap, and why this entry stays open:** it **ships `off`** with an empty domain block and
   **no caller in this plane sets the env var** — so the third sentence above holds unchanged, and a sweep
   following a redirect can still reach an off-list domain. The one real change to the risk is that such a
   read now *announces* it is unsealed rather than passing silently. Honest one-line form: **the seal exists,
   is tested and is switchable — and it is off, so it seals nothing today.** `state:actionable`, scope
   narrowed from *build it* to *arm it and wire the callers*. ⚠ Note also that this entry's "L2 domain gate"
   means the **in-process `safe_fetch.py` seal**, which the shipped code and `docs/OUTSIDE-SERVICES.md` call
   **Level 2**; that is a different layer from the Bash-command hook `enforce_egress_allowlist.sh`, which
   other elements number L2 and which is untouched by this change.

2. **Runtime-constructed URLs bypass the egress check** (`[EGRESS-WALL-FAILOPEN]`). The hook-plane
   `ingest_gate_enforce.sh` case `Bash`·(j) and the egress allowlist both operate on statically visible
   URL strings. A URL assembled at runtime (f-string / var concat) or an IP-literal call slips past
   the L2 domain gate. Fail-OPEN on this vector.

3. **Reader-actor split incomplete across all desks** (`[SECURITY-READER-ACTOR]`, debt-ledger 2026-07-03).
   Foundation is DONE and PROVEN (tool-less `ingest-reader`, `safe_fetch.py` egress allowlist, Deryl
   wired). REMAINING: (1) supervised live deryl-ingest on real mail + cron flip; (2) wire emily-1-ingest
   + clair-ingest; (3) research fetch-only searcher hook; (4) egress tool-layer allowlist hook;
   (5) pf network firewall (needs the operator sudo); (6) Supabase MCP host-lock;
   (7) `guard_ingest_reader_split.sh` conformance hook. `state:actionable`.

4. **Retired hooks (`guard_file_reads.sh`, `guard_web_fetch.sh`, `guard_web_search.sh`,
   `guard_skip_safe_backdoor.sh`) still exist on disk, unregistered**. Harmless on this machine, but
   if a settings drift on the second machine re-registers them instead of `ingest_gate_enforce.sh`,
   the unified gate's full logic would silently regress to the older per-channel-only coverage
   (missing the Bash cases, the scratch-dir lock, the item-store guards, etc.). Not currently tracked.

5. **`guard_web_search.sh` redirect is stale** (still points to `safe_search.sh` Chrome fallback, not
   `safe_search_api.sh` which became the primary 2026-07-03). The deny message is wrong but
   harmless — the hook still blocks the tool; only the human-facing redirect text is inaccurate.

6. **Cal email-convert fallback** (`[CAL-EMAIL-FALLBACK-REMOVE]`, debt-ledger): `cal-vault-pull.py`
   still has a direct-Gmail fallback path that bypasses the store-first path. Load-bearing graceful
   degradation; blocked for removal until store-sourced read rate is validated. UNVERIFIED whether the
   hook covers this fallback path (it would, since it matches `gws gmail` body reads).

---

### INTENT / CURRENT-VS-TARGET

**Intent:** make sure every byte of external content — web pages, email, calendar invites, task
notes, documents, search results — passes through a two-layer filter (deterministic L0 scrub +
heuristic injection scan) before the model ever reads it, and that a hook plane makes bypassing that
filter structurally impossible, not just discouraged.

**Current state → LIVE·gap:** the shared core and every per-channel tool are real, in daily use, and
the unified `ingest_gate_enforce.sh` hook is registered on all four matchers
(Bash/WebFetch/WebSearch/Read) with a fail-closed posture. The `·gap` is earned on two fronts: ~~the
per-run egress domain seal (`SAFE_FETCH_ALLOWLIST`) exists in `safe_fetch.py`'s code but is never
armed by any caller, so it provides zero actual restriction today~~; and a runtime-constructed URL
(built from a variable or an IP literal) slips past the static-string domain gate entirely. Both are
documented, known, and not silently glossed.

⚠ **CORRECTED 2026-08-15 — the first front, restated. `LIVE·gap` still holds and was NOT raised.** The seal
no longer merely "exists in code": it is switchable from a persistent file, resolves to three named states
with no quiet fourth, refuses outright when half-configured, is checkable via `--l2-status`, and carries 12
tests inside the aggregate gate. **But it ships OFF and no caller arms it — so the struck clause's
conclusion, "zero actual restriction today", is STILL TRUE by default.** The honest replacement wording:
*the per-run egress domain seal is now built, tested and switchable, ships OFF, and refuses loudly when
half-configured — so it restricts nothing until someone turns it on, and it says so on every unsealed read.*
The second front (runtime-constructed URLs) is entirely unchanged.

**TARGET:** ~~arm `SAFE_FETCH_ALLOWLIST` with a scoping pass before relying on it~~
**✔ DONE IN PART — 2026-08-15:** the scoping pass was ruled and the mechanism built, switchable and tested;
**what remains is wiring the callers and deciding whether to flip the switch on** — both still open, so this
target is not closed —
(`[EGRESS-WALL-FAILOPEN]`); close the reader-actor rollout gaps still open across desks — supervised
live deryl-ingest, wiring emily-1-ingest + clair-ingest, a research fetch-only searcher hook, an
egress tool-layer allowlist hook, the pf network firewall, Supabase host-lock, and a conformance hook
for the split itself (`[SECURITY-READER-ACTOR]`); retire the six superseded per-channel hooks from
disk so a settings drift on either machine can't silently re-register the weaker predecessor instead
of the unified gate; fix the stale `safe_search_api.sh`/`safe_search.sh` redirect text in the
WebSearch deny message.

---

## AUTO-COMPUTED   (machine-only — written by Feature 1.5 checker; do NOT hand-edit)

```yaml
maturity_label: LIVE·gap
check_detail: "Not yet run by the Feature 1.5 automated checker."
```

<!-- provisional: this label was set by the human author from live code inspection, not the checker -->
