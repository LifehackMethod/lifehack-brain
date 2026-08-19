---
element: security-ingest-gate
title: "security-ingest-gate — element detail (ground/base altitude)"
subsystem: security
altitude: base
record_type: organism-element
maturity_label: LIVE
generated_from:
  - system/hooks/ingest_gate_enforce.sh
  - system/reference/settings.json
  - system/tools/safe_fetch.py
  - system/tools/safe_read.py
  - system/tools/safe_calendar.py
  - system/tools/safe_tasks.py
  - shared/tools/email_convert.py
  - shared/tools/email_service_read.py
  - shared/tools/item_store_read.py
  - system/ingestion-reader-contract.md
  - system/information-ingestion-interpretation.md
  - system/security-canon.md
created_at: 2026-07-22
updated_at: 2026-07-22
status: active
authority: user
---

# security-ingest-gate — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. The marker records what
> happened to the named file AT THIS DESTINATION; it does not change the description.
>
> ⛔ `system/reference/settings.json` did not come across. It was the donor's read-only reference copy of the
> harness config; this repo's hook registry is `.claude/settings.json`, independently authored and smaller —
> an equivalent, never a copy. Check any registration claim below against that file.

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the unified on-path external-read
> gate. The MIDDLE manual (`system/organism/manual.md`) carries only a one-line + pointer to here; the TIP
> (`CLAUDE.md` schematic) shows only its box + arrows.
> **One-line:** sanitize/gate EVERY external-read channel so no unsanitized, attacker-authorable content ever reaches the model's context.
> *Step grammar: `actor → port/tool → store → gate` + tag `[hook]` (a real guard fires) · `[skill]` · `[honor]` · `[human]`.*

## AUTHORED   (human-only)
- **trigger:** any tool call on an external-read channel — a PreToolUse on **WebFetch · WebSearch · Read · Grep · Glob · Bash** (the **six** matchers `ingest_gate_enforce.sh` is registered under in the git-tracked `settings.json`). The registration SHAPE also changed: one PreToolUse entry with the alternation matcher `Bash|WebFetch|WebSearch|Read|Grep|Glob`, not six separate entries. **Grep and Glob reach Read's own file-type + trusted-zone logic** — the hook handles `Read|Grep|Glob)` as a single case and reads the target from `file_path` first, then `path`, because Grep/Glob carry it under `path`; an omitted path names nothing external and falls through to the same silent `exit 0` an empty Read does. For Bash, the gate inspects the command string for gws gmail/calendar/tasks/drive reads + the `LIFEHACK_SKIP_*` bypass + shell reads of ingest scratch.
- **hand-off chain:** (deny = JSON on stderr + `exit 2`; clean = `exit 0`)
    1. `model → WebFetch → (network) → ingest_gate_enforce.sh BLOCKS → redirect safe_fetch.py [hook]`
    2. `model → WebSearch → (network) → BLOCK → /websearch or safe_search_api.sh [hook]`
    3. `model → Read(.pdf/.docx/.xlsx/.csv) → file → BLOCK → safe_pdf/docx/xlsx/csv.py [hook]`
    4. `model → Read(external .txt/.md OUTSIDE the trusted zone: clone · ~/.claude · Drive Lifehack) → file → BLOCK → safe_read.py [hook]`
    5. `MAIN session → Read(/tmp/rdr, /tmp/ingest_body) → sanitized scratch → BLOCK (reader-actor lock); a SUB-AGENT (agent_id set) is ALLOWED (exit 0) — the CONTROLLER, not the gate, spawns the tool-less ingest-reader [hook]`
    6. `model → Bash(gws gmail messages/threads get format:full) → email body → BLOCK → email_convert.py [hook]`
    7. `model → Bash(gws calendar events list) → invite free-text → BLOCK → safe_calendar.py [hook]`
    8. `model → Bash(gws tasks tasks list/get) → task free-text → BLOCK → safe_tasks.py [hook]`
    9. `model → Bash(gws drive files export, raw) → client Doc body → BLOCK → safe_read/safe_docx/safe_pdf [hook]`
    10. `model → Bash(export LIFEHACK_SKIP_*) → env → BLOCK (the sanitizer-bypass var an injection reaches for) [hook]`
    11. `MAIN session → Bash(cat/head/tail/less/xxd .../tmp/rdr|ingest_body) → scratch → BLOCK (shell reader-actor lock) [hook]`
    12. `non-janitor → Bash(>/tee/rm/open-w into email-summary/ or item-store/) → shared store → BLOCK (single-writer invariant) [hook]`
    13. `model → Read(state/email-summary/threads-v2/*) → verbatim email store → BLOCK → email_service_read.py adapter [hook]`  ·  `model → Read(state/item-store/*) → task/calendar store → BLOCK → item_store_read.py adapter [hook]`  *(the store holds adversarial free-text; a raw read bypasses the adapter's re-scan + refuse-flagged + tool-less-reader routing)*
    14. `MAIN session → Bash(cat/head/tail/... email-summary/threads-v2/ or item-store/) → store → BLOCK → the matching adapter (email_service_read.py / item_store_read.py) [hook]`  *(same wall via the shell, not just the Read tool)*
- **ports touched:** the WebFetch/WebSearch/Read/Bash tool channels; the `safe_*` redirect family (`safe_fetch.py` · `safe_search_api.sh` · `safe_pdf/docx/xlsx/csv.py` · `safe_read.py` · `safe_calendar.py` · `safe_tasks.py`); `email_convert.py`; the tool-less `ingest-reader` subagent; the `/tmp/rdr` + `/tmp/ingest_body` scratch; the `state/email-summary/` + `state/item-store/` single-writer stores.
- **outcome:** no unsanitized external/adversarial content reaches context — every external-read is redirected through a sanitizer + injection scan, and the reader-actor split isolates untrusted free-text to a tool-less subagent that has nothing to act with.
- **generated_from:** `system/hooks/ingest_gate_enforce.sh` · `system/reference/settings.json` (ONE PreToolUse registration, matcher `Bash|WebFetch|WebSearch|Read|Grep|Glob` — six tools) · `system/tools/safe_fetch.py` · `safe_search_api.sh` · `safe_read.py` · `safe_pdf.py`/`safe_docx.py`/`safe_xlsx.py`/`safe_csv.py` · `safe_calendar.py` · `safe_tasks.py` · `shared/tools/email_convert.py` · `shared/tools/email_service_read.py` · `shared/tools/item_store_read.py` (the store-read adapters the gate redirects to) · `system/ingestion-reader-contract.md` · `system/information-ingestion-interpretation.md` · `system/security-canon.md`.
- **enforcement points (the honest map — each fire-tested by `label_checker.py` via `label_manifest.yaml → security-ingest-gate`):**
    - raw WebFetch / native WebSearch / external-doc Read / external-.md Read → `[hook]` `ingest_gate_enforce.sh` PreToolUse → BLOCK `exit 2` (fire-tested).
    - reader-actor scratch lock (main session Read + shell read) → `[hook]` same gate → BLOCK; sub-agent exempt via `agent_id`.
    - gws gmail-body / calendar / tasks / drive-export raw reads → `[hook]` → BLOCK (string-matched in the Bash branch).
    - `LIFEHACK_SKIP_*` bypass assignment → `[hook]` → BLOCK.
    - single-writer store writes (email-summary / item-store) → `[hook]` → BLOCK non-janitor.
    - adapter-required store READS (email-summary/threads-v2 · item-store — via BOTH the Read tool and shell cat/head/tail) → `[hook]` → BLOCK, redirect to `email_service_read.py` / `item_store_read.py` (the store holds adversarial free-text; the adapter re-scans + refuses flagged records).
    - **fail-CLOSED:** unparseable hook input / top-level JSON error → DENY (an external-read gate that can't read its input must not allow the read).
### INTENT / CURRENT-VS-TARGET
    - **Intent — BY DESIGN, a unifier, not a wall.** This ONE hook SUBSUMED six scattered per-channel deny hooks (email-sanitize · web-fetch · web-search · file-reads · calendar-reads · skip-backdoor) into a single on-path control (organism Window-5 cutover) — six things to keep in sync on two machines became one. It's a **REDIRECT** (points at the safe tool), EXCEPT the reader-actor lock, which structurally FORCES the tool-less subagent.
    - **Current → LIVE.** Fire-tested 2026-07-22: 6 synthetic violations all block (`exit 2`), 3 benign allow-cases pass (`exit 0`), git-tracked, registered on all six matchers (the fire test predates the Grep/Glob widening; the registration is six today). This is the reference "LIVE" element — the one that proved the checker pattern.
    - **★ INTEROP SEAMS (shared-state edges — the organism view):**
        - **⇄ the `safe_*` tool family** — the gate only BLOCKS + redirects; the safe tool it names does the actual L0-sanitize + injection-scan + Sentinel gate. The pair is the control: gate = the wall, safe tool = the clean door.
        - **⇄ the `ingest-reader` subagent (reader-actor split).** The gate denies the tool-HOLDING main session any read of sanitized scratch, but lets a tool-LESS subagent (identified by `agent_id`) through — so a hijacked reader has nothing to act with. Contract: `system/ingestion-reader-contract.md`.
        - **⇄ Sentinel + the injection scanner** — downstream of the safe tools; the danger gate that refuses flagged content.
        - **⇄ the single-writer stores** (`email_summary_sync.py` for email-summary; `tasks_store_sync.py`/`calendar_store_sync.py` for item-store) — the gate enforces their write-side invariant too, so this element overlaps the memory/store plane, not just the read plane.
    - **TARGET:** none outstanding for enforcement — the gate is LIVE and fire-tested. (Residual hardening lives on the individual `safe_*` tools, tracked on their own elements.)

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 `label_checker.py`)
- **maturity_label:** LIVE
- **check_detail:** `label_checker.py check --guard security-ingest-gate` → LIVE: 6 violations blocked (`exit 2`: WebFetch · WebSearch · external .pdf · external .md · LIFEHACK_SKIP · main-session scratch read), 3 allow-cases passed (`exit 0`: internal .md · benign Bash · code-file Read); git-tracked; registered PreToolUse Bash/WebFetch/WebSearch/Read.
