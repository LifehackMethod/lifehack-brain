---
element: ingest-gate
title: "ingest-gate — element detail (ground/base altitude)"
subsystem: security
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "ruled 2026-07-28 at class level — C2 exception — scratch lock admits ANY sub-agent, not only the tool-less reader family (premortem: allow ingest-reader + ingest-conclusions + ingest-tagger)"
generated_from:
  - shared/tools/ingest_gate.py
  - system/hooks/ingest_gate_enforce.sh
  - system/reference/settings.json
  - system/tools/sanitize.py
  - system/tools/safe_input.py
  - shared/tools/sentinel_response.py
  - system/ingestion-reader-contract.md
  - system/information-ingestion-interpretation.md
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# ingest-gate — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. The marker records what
> happened to the named file AT THIS DESTINATION; it does not change the description.
>
> ⛔ `shared/tools/ingest_gate.py` is the donor's path and is not here. The gate ITSELF did land — it ships as
> `shared/gate/ingest_gate.py`, with its tests beside it — so every mechanism described below is real and
> running; only the `shared/tools/` location did not come across.

> **LADDER: ELEMENT (full mechanics). up → manual#ingest-gate ; ground truth → shared/tools/ingest_gate.py + system/hooks/ingest_gate_enforce.sh**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds mechanics of the universal sanitize →
> scan → route content-security gate for ALL inbound content — the reader-actor perimeter. The MIDDLE
> manual (`system/organism/manual.md`) carries only a pointer to here; the TIP (`CLAUDE.md` schematic)
> shows only its box + arrows.
>
> **One-line:** every external read passes the full L0-sanitize → injection-scan → Sentinel-verdict
> pipeline ONCE, through a single shared Python entry point, before any model context sees the bytes.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires, exit 2) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause)

---

## AUTHORED   (human-only)

### SCOPE AND RELATIONSHIP TO `security-ingest-gate`

Two complementary elements share the ingest-gate subject:

- **`security-ingest-gate`** (live element, `elements/security-ingest-gate.md`) — the HOOK PLANE. Covers `ingest_gate_enforce.sh` (the PreToolUse deny wall): what tool calls it blocks, what it redirects to, how the reader-actor lock fires, and the 14 deny branches (WebFetch / WebSearch / Read / Bash / Grep / Glob — SIX matchers). That element is LIVE + fire-tested (label_checker, 2026-07-22). It is the **wall at the door**.

- **`ingest-gate`** (this element) — the PYTHON GATE. Covers `ingest_gate.py` (the on-path Python harness): the shared `gate()` API every safe_* tool and every desk calls AFTER the hook allows entry; its sanitize → scan → Sentinel → provenance-tag pipeline; posture modes; fail-open invariants; and the breadcrumb ledger. It is the **processing checkpoint inside the door**.

The two compose: the hook plane redirects blocked calls to safe tools → the safe tools call `ingest_gate.gate()` → the gate runs the full pipeline and returns `{content, provenance_tag, passed}` to the caller.

---

### TRIGGER

Every external-content read that passes the `ingest_gate_enforce.sh` deny wall reaches a `safe_*` tool
(`safe_fetch.py`, `safe_read.py`, `safe_pdf.py`, `safe_docx.py`, `safe_xlsx.py`, `safe_csv.py`,
`safe_calendar.py`, `safe_tasks.py`, `email_convert.py`). Each of those tools calls:

```python
from ingest_gate import gate   # shared/tools/ingest_gate.py
result = gate(desk_id, source_type, raw_content, message_id="", item="")
```

`ingest_gate.py` is also callable as a CLI:

```bash
python3 shared/tools/ingest_gate.py \
  --desk <desk_id> --source-type <email|web|file|calendar|api> \
  --item <human-readable-id> [--message-id <gmail_id>] \
  < raw_content_stdin
```
Exit 0 = passed; exit 2 = DANGER (mirrors the Sentinel verdict-tool convention).

**Source types:** `email | web | file | calendar | api` (`ingest_gate.py:45` — `VALID_SOURCE_TYPES`).

**Schema version:** frozen v1.0 (`system/schemas/ingest-gate-signature.md` — confirmed present).

---

### FULL STEP CHAIN

Every step below is derived from `shared/tools/ingest_gate.py` (`gate()`, lines 86–136) — live code wins.

---

#### Step 1 — Provenance tag (`ingest_gate.py:79–83`)

`gate() → _provenance_tag() → sha256(raw_content)[:8] → "{desk_id}/{source_type}/{sha256_8}"`

Computed on the RAW (pre-sanitize) bytes so the tag witnesses exactly what was screened. Not a secret;
tamper-evident. Format: `{desk_id}/{source_type}/{sha256_8}` (e.g. `planning/calendar/a3f1c2b9`).

`[skill]` — runs unconditionally before any sanitize/scan step.

---

#### Step 2 — L0 mechanical sanitize (`ingest_gate.py:94`)

`gate() → sanitize(raw_content, max_len=NO_CAP) → clean text [skill]`

Calls `sanitize()` from `system/tools/sanitize.py` with `NO_CAP` (no length cap on content — only
Subject/From header fields are capped at 200 chars inside `sanitize.py` itself; see GAPS below).
Strips hidden chars, HTML, and encoding artifacts. Output is the `clean` string passed downstream.

`[skill]` — stdlib-only, no LLM involved.

---

#### Step 3 — Regex injection scan (`ingest_gate.py:95`)

`gate() → scan_for_injection(clean) → findings list (or empty) → sentinel_response.py OR silent clean [skill]`

Calls `scan_for_injection()` from `system/tools/safe_input.py`. The metal-detector: fast, cheap,
over-flags intentionally. Returns a list of `(match_text, label)` pairs. Empty list = CLEAN.

**CLEAN path (no findings) — `ingest_gate.py:100–102`:**
`gate() → _breadcrumb(tag, source_type, desk_id, "clean") → return {content:clean, provenance_tag:tag, passed:True}`
A CLEAN read never calls `sentinel_response.py` (no subprocess, no event). The coverage breadcrumb is
still written so a clean-only desk shows as "covered" in the provenance ledger.

`[skill]`

---

#### Step 4 — Sentinel verdict call (`ingest_gate.py:104–120`)

Fires ONLY when `findings` is non-empty (injections detected by the scan). Calls `sentinel_response.py`
as a subprocess.

**Command built (`ingest_gate.py:105–112`):**
```bash
python3 shared/tools/sentinel_response.py \
  --source <desk_id> \
  --item <item[:120]> \
  --provenance <tag>
  [--message-id <gmail_id>]   # only for non-email source_type
  [--flag-only]               # only for source_type==email (LOCKED invariant)
```

`sentinel_response.py` receives the findings JSON on stdin as `[[match_text, label], ...]`.

**Exits:**
- **exit 0** → FLAG (or CLEAN): content is flagged but not dangerous. Gate returns `passed:True` with the sanitized content. Breadcrumb: `"flag"`.
- **exit 2** → DANGER: content is genuinely dangerous (non-email only; email is `--flag-only` → always exit 0). Gate returns `{content:"", passed:False}`. Breadcrumb: `"danger"`. The caller MUST halt and NOT process the item. Sentinel has already logged + pushed + paused the source (+ Gmail-quarantined if `message_id` was given).

**Timeout:** `subprocess.run(..., timeout=20)` (`ingest_gate.py:113`).

`[skill]`

---

#### Step 5 — LOCKED email invariant enforcement (`ingest_gate.py:104–120`)

`gate() → is_email flag → --flag-only to sentinel + never pass message_id + never return passed:False [hook-like — code-enforced, not hook]`

When `source_type == "email"`:
- `--flag-only` flag is always passed to `sentinel_response.py` (`ingest_gate.py:110`) — the Sentinel tool is thus UNABLE to escalate to DANGER for email regardless of its own rules.
- `message_id` is never passed (`ingest_gate.py:107–108`) — email can therefore never trigger Gmail quarantine from the gate.
- The `exit 2` DANGER check (`ingest_gate.py:116`) is guarded with `and not is_email` — even if Sentinel somehow returned exit 2 for email (impossible via `--flag-only`, but defensive), the gate would ignore it and return `passed:True`.

**Why:** email bodies are FLAG-floored by the LOCKED invariant until the provenance-aware classifier ships (see GAPS). Relaxing this requires a schema_version bump + Window-3 sign-off (`ingest_gate.py:29–31`).

**Enforcement strength:** code-enforced in `ingest_gate.py` (not a hook file, but the logic is structural, not honor-system). `[skill]`

---

#### Step 6 — Posture-controlled error handling (`ingest_gate.py:121–136`)

Fires when any unhandled exception occurs inside the `gate()` try block (sanitize crash, subprocess error,
timeout, import failure).

**POSTURE** = `os.environ.get("INGEST_GATE_POSTURE", "enforce").strip().lower()` (`ingest_gate.py:58`).
Default since Window-5 cutover (2026-06-20): **`"enforce"`**.

**`enforce` posture (non-email, `ingest_gate.py:125–128`):**
`exception → DENY: {content:"", passed:False}` — fail-CLOSED.
Breadcrumb: `"error-denied"`. Stderr: `"[ingest-gate] non-fatal (…) — ENFORCE posture: read DENIED (fail-closed)"`.

**`warn` posture OR any email (all error cases, `ingest_gate.py:130–136`):**
`exception → PASS: {content: best-effort sanitize(raw) or "", passed:True}` — fail-OPEN.
Breadcrumb: `"error-open"`. Stderr: `"[ingest-gate] non-fatal (…) — read continues (fail-open), verdict undetermined"`.
This is the pre-Window-5 behavior AND the instant-revert path: `INGEST_GATE_POSTURE=warn`.

**Email under enforce:** email always fails OPEN on an exception (same as `warn` for email). Rationale:
email is FLAG-floored and can never reach DANGER, so failing it OPEN on a gate hiccup removes zero
containment while avoiding a new way to break live email ingestion on a transient error.

**The DANGER verdict path (exit 2, non-email) is posture-independent** — it returns `passed:False`
regardless of posture; the `except` block never reaches it.

`[skill]` (env-var controlled; no hook enforces posture setting).

---

#### Step 7 — Coverage breadcrumb (`ingest_gate.py:61–76`)

`gate() → _breadcrumb() → PROVENANCE_LOG (Drive spine) → append one JSON line [skill best-effort]`

Written on EVERY gate call regardless of verdict (clean / flag / danger / error-denied / error-open).
Purpose: makes coverage MECHANICAL, not opt-in — `ingest_coverage.py` reads this ledger so a desk
that only ever reads clean content still shows as "covered" instead of false-flagging a gap.

**Store:** `$DRIVE/state/status/ingest-provenance.jsonl` (default, `ingest_gate.py:49`).
Overridable: `INGEST_PROVENANCE_LOG` env var (used in tests).

**Record format (`ingest_gate.py:70–71`):**
```json
{"ts":"2026-07-24T10:00:00+10:00","desk":"planning","source_type":"calendar","provenance_tag":"planning/calendar/a3f1c2b9","verdict":"clean"}
```

**`_breadcrumb` is NEVER-RAISES** (`ingest_gate.py:75–76`): any write failure is swallowed to stderr;
the read is never blocked by a coverage write failure.

---

### CONTRACT (frozen v1.0)

```python
gate(desk_id, source_type, raw_content, message_id="", item="")
→ {
    "content":        str,   # sanitized content; "" on DANGER
    "provenance_tag": str,   # "{desk_id}/{source_type}/{sha256_8}"
    "passed":         bool,  # True (FLAG/CLEAN → caller continues); False (DANGER → caller HALTS)
  }
```

`source_type` must be one of `{"email", "web", "file", "calendar", "api"}`.

On `passed=False`: Sentinel has already logged + pushed + paused the source (+ Gmail-quarantined if
`message_id` given). The caller MUST NOT process the item and MUST NOT re-open its body.

**The gate NEVER raises** (defensive design, `ingest_gate.py:86` docstring) — the verdict on an
internal error is posture-dependent (Step 6), but the gate always returns the dict.

---

### STORES TOUCHED

| Store | Step | Access |
|---|---|---|
| `$DRIVE/state/status/ingest-provenance.jsonl` | Step 7 | APPEND (one JSON line per gate call; never-delete) |
| `/tmp/rdr/` and `/tmp/ingest_body/` (scratch) | (downstream, not written by gate itself) | READ by tool-less ingest-reader subagent; DENIED to main session by `ingest_gate_enforce.sh` |
| `sentinel-events.jsonl` (Sentinel's own ledger) | Step 4 (via sentinel_response.py) | WRITE (findings-only; separate from provenance.jsonl) |

---

### GATES AND ENFORCEMENT (the honest map)

**What is hook-enforced:**

1. **`ingest_gate_enforce.sh`** (PreToolUse Bash/WebFetch/WebSearch/Read/Grep/Glob — **SIX** matchers,
   registered as ONE alternation entry `"Bash|WebFetch|WebSearch|Read|Grep|Glob"` rather than as four
   separate registrations; Grep and Glob are handled in the SAME case as Read and run the identical
   file-type + trusted-zone logic downstream, but carry their target under `path` rather than
   `file_path`) `[hook]` — the deny wall that
   **forces** all external reads through the safe_* tools which in turn call `ingest_gate.gate()`. The
   full enforcement picture lives in `elements/security-ingest-gate.md`. Without this hook firing
   correctly, callers could bypass `ingest_gate.py` entirely.

**What is code-enforced (within the Python gate):**

2. **Email LOCKED invariant** (Step 5) — `--flag-only` and `not is_email` guard on exit-2 check are
   structural in the gate's Python code; not bypassable by a prompt. `[skill]`

3. **DANGER → passed:False** (Step 4) — enforced by checking `r.returncode == 2 and not is_email`.
   Posture-independent. `[skill]`

4. **Enforce posture → fail-CLOSED on error** (Step 6) — env-controlled, default `"enforce"`. A caller
   cannot soften it without setting `INGEST_GATE_POSTURE=warn`. `[skill]`

**What is honor-system:**

5. **Callers must check `passed` before processing** `[honor]` — the gate returns `passed:False` with
   `content:""` on DANGER, but there is no hook verifying that every caller inspects `passed` before
   acting on the content. A caller that ignores `result["passed"]` and uses `result["content"]` (which
   is `""` on DANGER) would silently skip the item rather than crash — low blast-radius, but unverified.

6. **`ingest_gate.py` is actually called by every safe_* tool** `[honor + structural]` — the hook
   redirects to the safe tools (enforced); that those safe tools import and call `gate()` is a code
   convention, not a hook-enforced invariant. A newly-written `safe_*` tool that skips the call would
   silently bypass the Python gate.

7. **Coverage breadcrumb integrity** `[honor]` — `_breadcrumb` is best-effort and never-raises; a
   persistent write failure (e.g., Drive not mounted) produces no breadcrumb and silently shows as a
   gap in `ingest_coverage.py`. The gate does not fail on a missed breadcrumb.

---

### GAPS (documented fail-open conditions)

These are real posture gaps — a tip-only reader seeing `LIVE·gap` should drill here.

**G1 — Email fails OPEN on gate error (BY DESIGN, not a defect).**
Under the `enforce` posture, email reads that hit an internal exception still return `passed:True`
(Step 6). This is BY DESIGN (email is FLAG-floored, can never DANGER, so failing it open removes zero
containment). Source: `ingest_gate.py:51–54`. Documented as an accepted design choice.

**G2 — `sanitize.py` caps Subject/From at 200 chars (potential injection hide).**
`sanitize.py` caps header fields (Subject/From) at 200 chars before the scan. A >200-char Subject could
hide an injection payload past the cap while the body uses `NO_CAP`. Low surface (headers only, not
bodies), but documented. Source: debt-ledger `[SECURITY-MINOR-2026-07-04]` item (a).
**PARTIALLY MITIGATED:** `email_convert.py`'s `get_headers()` already calls `sanitize()` with `NO_CAP`,
so the 200-char cap does not apply to headers processed through that path. The gap remains only for
other callers that invoke `sanitize_fields()` with the default cap directly.

**G3 — Coverage breadcrumb is best-effort; persistent write failures produce silent gaps.**
If `$DRIVE/state/status/ingest-provenance.jsonl` is unreachable (Drive unmounted, permissions), the
breadcrumb is silently skipped. `ingest_coverage.py` would then falsely flag the desk as uncovered
even if the gate ran correctly. The read itself is unaffected. Source: `ingest_gate.py:75–76`.

**G4 — The on-path Python gate is not called by the hook directly.**
`ingest_gate_enforce.sh` BLOCKS the raw call and redirects to `safe_*` tools. The Python gate
(`ingest_gate.py`) runs only if those safe tools correctly import and call `gate()`. A new safe tool
that skips the call bypasses the Python gate entirely with no hook catching it. Structural convention,
not mechanical enforcement. Source: code inspection.

**G5 — Scratch-dir lock allows ANY sub-agent, not only the tool-less reader.**
`ingest_gate_enforce.sh` identifies sub-agents by `agent_id` OR `agent_type`
(`d.get('agent_id','') or d.get('agent_type','')`) — it allows any sub-agent (not just `ingest-reader`)
to read `/tmp/rdr` and `/tmp/ingest_body`. A controller that (by mistake or compromise) spawns a
full-tool sub-agent to read scratch would slip through the lock. Mitigated by: reader-scope named rule
+ F2.5 conformance check + skills explicitly spawning `ingest-reader`. Tracked:
debt-ledger `[SCRATCH-LOCK-ANY-SUBAGENT]` `state:monitoring`.

**G6 — Buzz-on-verdict not yet wired (alerting fires on scan beep, not reader VERDICT).**
The `sentinel_response.py` phone-buzz fires on the scanner-level DANGER, not on the tool-less reader's
semantic `REAL-ATTACK | BENIGN | NONE` verdict. This causes FP notification spam for benign encoding
(e.g., signing link hashes). The `--reader-verdict` hook is available but unwired by design (precision
fix via DANGER-label retier was preferred over per-read `claude -p` machinery). Tracked: debt-ledger
`[SEC-BUZZ-VERDICT]` — CLEARED 2026-07-14 via precision re-tier; the underlying verdict-wiring remains
a future fix. Source: `system/information-ingestion-interpretation.md §1`.

**G7 — One-gate doctrine is current-vs-target: reader still runs at READ-time, not intake.**
The ratified end-state has the tool-less reader running ONCE at intake (Grand Central), so the cleared
store is downstream-trusted with no re-scan. Today the reader runs at READ-time (per-consumer). This is
NOT a gate bug — the Python gate itself is correct — but a caller architecture gap: desks re-run the
reader on already-gated content until the Grand Central handoff ships. Tracked:
`system/information-ingestion-interpretation.md §5` + `$DRIVE/state/injection-gate-overblock-handoff.md`
(confirmed present).
**✅ PARTLY CLOSED — the STORE READ-WALL is LIVE.** `ingest_gate_enforce.sh` now DENIES a direct `Read`
of the item store (`*/state/item-store/*`) and of the v2 faithful-thread store
(`*/state/email-summary/threads-v2/*`, plus `threads-v2-cold`), redirecting each to its read adapter
(`item_store_read.py` · `email_service_read.py`). The placement is the load-bearing part: both deny
cases sit BEFORE the trusted-zone allowlist, because both stores live INSIDE that zone — a rule placed
after it would never fire and the raw read would sail through as an ordinary internal file. Watched
refusing: `exit 2` with the correct deny JSON. This makes the one-gate rule REAL for these two stores:
a record carrying `reader_applied=true` was judged by the tool-less reader AT THE DOOR and is served
inline with no second reader; only a record NOT cleared at intake is re-scanned and isolated at read
time. So the flat claim above — "today the reader runs at READ-time (per-consumer)" — is now stale for
these stores: read-time scanning is the FALLBACK for uncleared records, not the only path.

---

### MODES / POSTURE CONTROL

| Env var | Value | Effect |
|---|---|---|
| `INGEST_GATE_POSTURE` | `"enforce"` (default since 2026-06-20) | Non-email gate error → fail-CLOSED (`passed:False`) |
| `INGEST_GATE_POSTURE` | `"warn"` | Gate error → fail-OPEN (`passed:True`) — pre-W5 behavior; instant revert |
| `INGEST_PROVENANCE_LOG` | custom path | Override breadcrumb ledger location (used in tests) |

**DANGER verdict path** is posture-independent — it always returns `passed:False` for non-email.

---

### EDGE CASES

1. **DANGER on non-email:** `content` is `""`, `passed` is `False`. Sentinel already quarantined the
   source. Caller must halt. Re-opening the body "to inspect" re-blends the payload into context —
   the exact hole the reader-actor split closes. Never do it.

2. **Empty raw_content:** `gate(desk_id, source_type, "")` — `_provenance_tag` hashes the empty string;
   `sanitize("")` returns `""`; `scan_for_injection("")` returns empty findings → CLEAN path → returns
   `{content:"", provenance_tag:..., passed:True}`. Not a failure.

3. **Sentinel subprocess timeout (20s):** falls through to the `except Exception` branch → posture
   determines the verdict (enforce → deny; warn or email → pass). A 20-second Sentinel hang means a
   timed-out call returns a deny for non-email under enforce posture.

4. **`message_id` passed for email source_type:** silently ignored (`ingest_gate.py:107–108` conditions
   on `not is_email`). Email is never quarantined from the gate regardless of `message_id`.

5. **`source_type` not in VALID_SOURCE_TYPES:** the CLI rejects it (`choices=` in argparse). The `gate()`
   function itself does not validate — a direct Python caller with an invalid source_type would proceed
   with `is_email = (source_type == "email")` defaulting to `False` (non-email path). Low blast-radius
   (wrong breadcrumb label, non-email posture applied).

6. **Drive not mounted (breadcrumb write fails):** `_breadcrumb` swallows the error; read continues
   unaffected. Coverage ledger has a silent gap (see G3).

---

### INTENT / CURRENT-VS-TARGET

**Intent:** ONE shared Python entry point that every desk's external read passes through — so coverage
is mechanical (the breadcrumb proves it) not opt-in (each safe_* tool doing its own thing). Closes the
email hole (pre-W3 `email_convert._flag_injection` was disconnected, printing to stderr only); tags
provenance so gaps are detectable; enforces the LOCKED email FLAG-never-DANGER invariant in code.

**Current → LIVE·gap** (honest):
- The Python gate fires correctly on every safe_* call.
- Email invariant is code-enforced; DANGER verdict closes non-email.
- Breadcrumb ledger is live (`INGEST_COVERAGE_FLAG=on` since 2026-06-21).
- GAPS G2, G5, G6, G7 are documented fail-open or current-vs-target items (see GAPS above).
- `·gap` justified: G5 (any-sub-agent scratch lock), G4 (convention not hook), G2 (200-char cap), G7
  (reader at read-time not intake) — a tip-only `LIVE` would over-trust the gate's completeness.

**TARGET:**
1. **Reader at intake (`one-gate` move)** — the Grand Central handoff ships the tool-less reader into
   the intake path so the cleared store is downstream-trusted with no re-scan (G7).
2. **Scratch-dir lock narrowed to `ingest-reader` only** — check `agent_type` ∈ {ingest-reader,
   web-searcher} rather than any non-empty `agent_id` (G5).
3. **`sanitize.py` Subject/From cap raised or removed** — verify injection surface, then lift the 200-
   char cap if safe (G2).

---

### INTEROP SEAMS

```
CHAINS         security-ingest-gate   · hook plane fires first; redirects to safe_* tools which call gate()
READS          sanitize               · L0 scrub (system/tools/sanitize.py); gate imports it directly
READS          safe_input             · injection scanner (system/tools/safe_input.py); gate imports it directly
TRIGGERS       sentinel               · sentinel_response.py called on any findings (non-empty scan result)
WRITES→        ingest-provenance      · breadcrumb ledger ($DRIVE/state/status/ingest-provenance.jsonl) on every gate call
FEEDS          ingest-reader          · on FLAG/CLEAN, safe_* tools write cleared content to /tmp/rdr for the tool-less reader subagent to consume
GUARDED-BY     security-ingest-gate   · the deny hook (ingest_gate_enforce.sh) forces callers through safe_* tools, which is what causes gate() to be called
SHARES         email_convert          · email_convert.py is the safe_* tool for email; it calls gate(source_type="email") → enforces the FLAG-floor invariant
SHARES         safe_calendar/tasks    · safe_calendar.py and safe_tasks.py call gate(source_type="calendar"/"api") — same pipeline, different source_type
COMPLEMENTS    sentinel               · sentinel_response.py is the verdict arbiter; the gate is the pipeline; the hook is the wall — three layers, each distinct
SYNCS          ingest-gate-signature  · frozen contract v1.0 in system/schemas/ingest-gate-signature.md (confirmed); any signature change requires schema version bump + Window-3 sign-off
```

---

### HARD PROHIBITIONS (what the gate never does)

- Never raises on its own internals — posture determines the returned verdict; the gate always returns the dict.
- Never quarantines email (even on DANGER-class content from the scanner) — email is FLAG-floored.
- Never calls Sentinel on a CLEAN read (no findings) — clean reads produce a coverage breadcrumb only.
- Never passes `message_id` for email source_type — email quarantine is structurally excluded.
- Never summarizes content — sanitize strips; scan flags; Sentinel judges. The cleared content is returned verbatim minus stripped characters, not paraphrased.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** LIVE·gap [provisional]
- **check_detail:** AUTHORED from live code inspection of `shared/tools/ingest_gate.py` (154 lines, stdlib-only) + `system/hooks/ingest_gate_enforce.sh` (194 lines) + debt-ledger sweep + `system/information-ingestion-interpretation.md`. The Python gate fires on every safe_* tool call (structural, not separately fire-tested here — `security-ingest-gate.md` covers the hook fire-test). Gaps G1–G7 documented from live code + debt-ledger. LIVE (gate fires; posture=enforce; breadcrumb live; email invariant code-enforced) + `·gap` (G5 any-sub-agent scratch lock; G4 safe_* convention not hook; G2 200-char Subject cap; G7 reader still at read-time) — label is honest. `[provisional — not fire-tested independently]`
