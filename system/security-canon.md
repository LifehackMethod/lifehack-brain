---
topic: [agent-security]
record_type: system-canon
title: ClaudeOps Security Canon
version: "1.0"
created_at: 2026-05-23
updated_at: 2026-07-04
status: active
authority: system
loaded_by: root mode, sentinel, any session involving security decisions
---

# ClaudeOps Security Canon

Single source of truth for ClaudeOps security posture. Built from two rounds of
ChatGPT Deep Research and iterative red-teaming in May 2026. Load this before
making security decisions. Do not redo the research — it is here.

---

## The Threat Model

### Prompt Injection and Drift Are the Same Problem

The model cannot inherently distinguish your instructions from content it
ingests. A malicious string in an email body or web page can redirect agent
behavior just as effectively as a direct instruction — and it doesn't require
a one-shot "ignore previous instructions" attack. Research shows agents can be
*gradually* nudged through repeated interactions until they act off-policy.

**The failure mode you're experiencing without any attack:**
- Raw email body reads that bypass the sanitizer (`email_convert.py`)
- Files written to wrong paths or desk roots instead of `records/`
- Analysis saved to ephemeral `~/.claude/projects/` instead of Drive records

These are the same failure class that injection would exploit. The attack
surface exists before any attacker touches it.

### What the Actual Risks Are (Ranked)

1. **LLM instruction compliance drift** — the model follows rules ~90% of the
   time. The 10% failure rate is the primary risk. More text rules do not close
   this gap. Only mechanical enforcement does.

2. **Prompt injection via ingested content** — email bodies and web pages are
   untrusted content in the same context window as trusted instructions. A
   sophisticated injection doesn't need to look like an instruction.

3. **Self-modification** — a compromised session could overwrite hook scripts
   or settings, disabling its own guardrails. This is partially addressed
   but has a known platform limit (see below).

4. **Credential exposure / static posture** — handled by Sentinel. Lower
   ongoing risk because it's checked regularly and the architecture is
   relatively clean.

**What this is NOT:**
- Exfiltration to an external attacker (low risk for a personal home system
  with no open ports, no team access, no external API exposure)
- Enterprise-grade threats (supply chain, insider, physical access)

---

## The Governing Lens — Lethal Trifecta + Blast Radius

Use this to reason about ANY new agentic path *before* building defenses.

**Lethal trifecta (Simon Willison):** a catastrophic agent outcome needs ALL THREE at once — (1) private-data access, (2) untrusted-content ingestion, (3) an outbound/exfiltration channel. **Break any one leg and the worst outcomes mostly vanish, even with zero injection detection.** First question for any new path: do all three co-exist here? If not, the threat class is largely neutralized for free.

**Blast radius is the governing variable, not attacker sophistication:** `(autonomous?) × (reversible?) × (actual write scope)`. A manually-run skill that fails visibly on a supervised run ≈ zero blast radius; a cron with calendar+email writes is real. Over-caution (treating a manual tool as if it were live) is itself a failure mode — ground risk in specifics.

**Reader-actor separation (PROVEN 2026-07-03/04 — structural, not behavioral):** the component that READS untrusted text has no tools and no network; the component that ACTS never sees raw text. Pass the reader's output to the actor as **tight TYPED data, never free text** (free-text handoff collapses the separation). In Claude Code: spawn the untrusted-content reader as a tool-less, network-less subagent — a context-isolation guarantee, needs no second model. **Live implementation:** `.claude/agents/ingest-reader.md` (tools: Read only) is the designated reader; `ingest_gate_enforce.sh`'s scratch-dir lock enforces the split mechanically — MAIN-session direct reads of `/tmp/rdr/` + `/tmp/ingest_body/` are denied; sub-agents identified by `agent_id` in hook stdin may read. Proven live across multiple ingestion paths in the system this was ported from; the mechanism is what carries over (the original proof record was a project file on that system's synced drive and does not ship in this repo). **Extension:** a seeded-attack test found calendar + Google Tasks returned raw injection to the controller while email did not (its scratch-lock isolates it). Fixed — `safe_calendar.py`/`safe_tasks.py` **isolate free-text by default** (→ `/tmp/rdr` scratch, `_reader_scratch` pointer on stdout); content-reading skills spawn the reader; modes `--redact` (neutralize spans, used by `planning-vault-pull.py` to close the vault-as-downstream-channel gap) / `--no-isolate` (raw, no-LLM plumbing only).

**Escalation model (airport metaphor — how the reader-actor pipeline actually responds):** (1) **Metal-detector regex** = cheap, fast, over-flags — beeps "look here," decides nothing, never blocks on its own. (2) **Tool-less `ingest-reader`** = the JUDGE ("body scanner"): for EACH flagged span only, it decodes the encoding (base64/hex/URL/zero-width) and judges by MEANING — real injection vs. benign encoded content; redacts only real attacks, passes benign spans through unchanged, emits a VERDICT per span (`REAL-ATTACK | BENIGN | NONE`). (3) **The reader's VERDICT — not the raw scanner beep — gates both redaction AND alerting**: only a `REAL-ATTACK` verdict triggers a quarantine or phone notification; a beep that resolves to `BENIGN` is silently cleared. Note: buzz-on-VERDICT (phone alert wired to the ingest-reader output) is a documented FUTURE fix — the structural redaction is live; live alerting still fires on the scan flag as an interim. The reader judges only what-to-redact, never whether-to-act; DANGER-class content hard-quarantines regardless.

**Egress is the highest-leverage control:** filtering/allowlisting the *outbound* channel structurally caps exfiltration even if an injection lands — stronger than any input-side scanner (semantic injection lives in meaning, not syntax, so input classifiers stop ~no real attacks while breaking legit content; keep any input heuristic as flag-and-count, never a blocker).

### Deliberately Skip (enterprise overkill for a solo system)
Recording what you decline — and why — is half of a right-sized posture; it stops gold-plating and re-litigating settled calls. Skip: full CaMeL capability-interpreters (≈9% task-utility cost + policy fatigue) · enterprise injection-classifier programs + red-team orgs · SOC 2 / MITRE-ATLAS / formal audit trails · SOC monitoring · heavy multi-layer injection-scanning pipelines (≈99.5% false positives → disabled → net-zero protection).

### Calibration — solo systems ARE now real targets (don't over-rotate)
EchoLeak (CVE-2025-32711, a zero-click email-injection) showed personal-scale agentic systems are no longer ignored — but it hit Microsoft 365 Copilot (an *enterprise* product), so treat it as a calibrated heads-up, not evidence someone is hunting a one-person home agent. The structural floor matters at one-person scale; the enterprise tooling above does not.

---

## Current Security Architecture

### What Sentinel Covers (Static Posture)

Sentinel is a read-only audit agent. It checks:
- Secret exposure in settings.json and tracked files (high/medium/low confidence)
- File permissions on `.secrets/` (POSIX bits, with the Drive caveat below)
- MCP surface inventory (servers, transport type, data sensitivity)
- Drive/cloud sharing verification, if the install syncs its data folder through one
- Per-desk permission inventory

**Sentinel does NOT cover:** runtime behavior, prompt injection, write path
violations, or email access scope enforcement. It is a static snapshot, not a
runtime guard.

**Local secrets caveat:** POSIX mode bits are only meaningful for secrets kept in a plain local
directory. If an install syncs its data folder through a cloud-drive client (Dropbox, Google Drive for
Desktop, etc.), file permissions on that mount may not reflect real access control — keep secrets in a
local, non-synced path (this system's own config home is `~/.config/lifehack/`) and treat anything
under a synced folder as permission-unverifiable.

**Cadence:** review `<notes>/system/logs/sentinel-events.jsonl` and the paused-source list
(`~/.config/lifehack/sentinel-paused-sources`) after any new external-content channel is wired in, or
any new desk is added. ⛔ There is no `/sentinel` audit skill here and none is coming — the mechanical
gate scripts (`shared/gate/sentinel_response.py`, `shared/gate/sentinel_ack.py`) are the whole
mechanism, and the review is a thing you do, not a thing you run. No automated schedule for THIS
review either — ⚠ CORRECTED 2026-08-15: this used to say the repo has no scheduler at all, which
is no longer true (`system/tools/pulse.sh` is real and several jobs run on it); it is specifically
this review that has no `pulse-config.md` row, so its trigger stays manual by construction.
⚠ The event log is written under YOUR NOTES ROOT, not into this repository — `sentinel_response.py:52`
resolves it as `{notes root}/system/logs/sentinel-events.jsonl` (falling back to
`~/.cache/lifehack-sentinel` when no root is set). It is a record of your own traffic and must never be
committed.

### Inbound Channel Inventory

The channels this system treats as untrusted-content inbound, and which adapter sanitizes each one,
are enumerated in the Attack Surface Coverage table below and in `shared/gate/ingest_gate.py`'s own
header — that gate is the single shared enforcement point for every channel except email's DANGER
ceiling (see Layer 1). Treat any channel not listed there as unreviewed, not as cleared.

### Existing Hooks (as of 2026-07-04, in the system this canon was authored for)

**Scope note (ported doc):** the hook filenames below are that system's names, current as of the dates
shown — a historical design record, not a live inventory of THIS repo's hooks. This repo's actual
registered guards are in `.claude/settings.json` and `system/hooks/`; the closest equivalents here are
`ingest_gate_enforce.sh` (the unified gate — ported under the same name) and `guard_calendar_writes.sh`
(calendar-write guard; the donor's `block_primary_calendar.sh`, named below, is its ancestor). Read the
table for WHY a unified gate beats N per-channel hooks, not as a map of this repo's files.

**Live unified gate (CURRENT, in the donor system):**

| Hook | Type | Matcher | What It Does | Blocking? |
|------|------|---------|--------------|-----------|
| `ingest_gate_enforce.sh` | PreToolUse | Bash\|WebFetch\|WebSearch\|Read | **Unified ingestion gate** — SUBSUMES the 6 per-channel hooks listed below. Enforces: email→`email_convert.py`, docs→`safe_*`, web→`safe_fetch.py`/`safe_search_api.sh`, calendar→`safe_calendar.py`. Fail-closed (non-email internal error → deny; email → FLAG-floored fail-open). **2026-07-04: scratch-dir lock** — denies MAIN-session `Read` of `/tmp/rdr/` + `/tmp/ingest_body/`; sub-agents pass via `agent_id` in hook stdin, structurally enforcing the reader-actor split in both interactive and cron paths. | Yes — fail-closed |
| `enforce_egress_allowlist.sh` | PreToolUse | Bash | Blocks outbound Bash calls to hosts not in `system/egress-allowlist.md`; structurally caps exfiltration even if an injection lands. | Yes — fail-closed |
| `block_primary_calendar.sh` | PreToolUse | Bash | Blocks calendar writes to any calendar except Agent Ops | Yes — fail-closed |
| `guard_write_paths.sh` | PreToolUse | Write\|Edit | Blocks writes outside Drive spine + approved ~/.claude/ subpaths | Yes — fail-closed |
| `validate_on_write.sh` | PostToolUse | Write\|Edit | Validates frontmatter on written files | No — advisory only |
| `auto_register_skill.sh` | PostToolUse | Write | Creates command stubs for desk-level skills | No |

**SUPERSEDED hooks (retired — do NOT register; functionality folded into `ingest_gate_enforce.sh`):**

| Hook | Superseded Date | Notes |
|------|----------------|-------|
| `enforce_email_sanitize.sh` | 2026-07-03 | Email branch now in `ingest_gate_enforce.sh` |
| `sanitize_calendar_reads.sh` | 2026-07-03 | Calendar branch now in `ingest_gate_enforce.sh` |
| `guard_web_fetch.sh` | 2026-07-03 | WebFetch branch now in `ingest_gate_enforce.sh` |
| `guard_web_search.sh` | 2026-07-03 | WebSearch branch now in `ingest_gate_enforce.sh` |
| `guard_file_reads.sh` | 2026-07-03 | Read branch now in `ingest_gate_enforce.sh` |
| `guard_skip_safe_backdoor.sh` | 2026-07-03 | `CLAUDEOPS_SKIP_*` block now in `ingest_gate_enforce.sh` |

### Existing Deny Rules (this repo, `.claude/settings.json`)

- SSH, GPG, AWS, Kube, `.env`/`.env.local`, macOS Keychains — Read+Edit blocked
- `.claude/settings.json`, `.claude/agents/**`, `.claude/skills/**`, `system/hooks/**` — Edit blocked

**The historical gap this closes:** the system this canon was authored for did NOT protect its
equivalent of `~/.claude/hooks/**` or `~/.claude/settings.json` themselves — the two files that make
the hook system work — which is a real hole (a compromised session could Edit its own guardrails away).
This repo's deny list closes it directly, and `guard_write_paths.sh` (ported) backs it up as a
PreToolUse guard on the same paths — see that hook's own header for the 2026-08-14 measurement that
found every Write/Edit-matched hook here at the time waving through an Edit aimed at another hook,
which is why both layers (deny rule + guard) exist together rather than either alone.

### The `--dangerously-skip-permissions` Situation

If a launcher runs Claude Code with `--dangerously-skip-permissions`, that bypasses interactive
permission prompts — but **hooks still fire regardless**. A calendar-write guard or any other
PreToolUse hook works the same whether or not the flag is set.

**Do not remove this flag as a security fix if you use it.** Hooks are the enforcement layer; the
permission-prompt system is a backup that isn't needed when hooks are correctly designed. Removing the
flag only adds interactive prompts to every non-allow-listed operation — it does not add protection a
correctly-designed hook wasn't already providing.

---

## Platform Limitations — Read Before Building

These are hard constraints of the Claude Code hook architecture discovered
through research and confirmed by ChatGPT Deep Research (2026-05-23). Do not
design hooks that depend on capabilities the platform doesn't have.

### PostToolUse Hooks Cannot Modify Tool Results

PostToolUse hooks run *after* the tool result has been returned to the model.
They can observe, log, alert, or block *subsequent* actions — but they cannot
alter the content the model already received. Trust tagging (wrapping fetched
content as "untrusted") cannot be done mechanically at the hook level.

**Implication:** Any scheme that tries to intercept and modify WebFetch or
WebSearch output before the model sees it requires a wrapper architecture
(a separate agent that sanitizes content before passing it to the main agent),
not a hook. This is a future option, not a current one.

### Deny Rules Do Not Protect Hook Scripts From the Model

Claude Code's `permissions.deny` rules are not enforced against the model's
own hooks and config files at the OS level. A determined session could use
Edit/Write tools on `~/.claude/hooks/` even if those paths appear in the deny
array. The deny rules reduce casual access but do not provide hard guarantees.

**Implication:** The only true self-modification protection is OS-level file
permissions (`chmod 444` on hook files) or running Claude under a separate user
account that cannot write to those paths. The deny rule approach is defense-in-
depth, not a hard wall.

### Env Var Inheritance by Hooks Is Not Guaranteed in Multi-Agent Scenarios

Environment variables set in the parent shell (e.g., in a `.command` launcher)
are inherited by the Claude process and generally by hook subprocesses — but
this is not guaranteed when sub-agents or new Claude instances are spawned.
Hooks in sub-agent contexts may not see the parent's env vars.

**Implication:** For any hook that depends on an env var for trust state (like
the email lane guard), verify inheritance with a diagnostic test first. Have a
file-based fallback ready. The file must be written by the launcher, not the
model.

---

## Defense Architecture — The Layered Plan

### Pre-Req — Protect the Guards (Deploy First)

This repo's `.claude/settings.json` already denies `Edit` on `system/hooks/**` and on
`.claude/settings.json` itself (project-relative paths — see Existing Deny Rules above).
`guard_write_paths.sh` backs that up as a PreToolUse guard on the same paths.

**Why first:** every hook is worthless if the model can overwrite it. These deny rules are not a hard
guarantee (see platform limits above) but they eliminate casual self-modification and raise the bar
significantly.

DO NOT `chmod 444` the hook scripts. Unlike the donor system's advice, this repo's hooks must
stay executable (`755`) — a stripped execute bit is what silently disarmed three guards here on
2026-08-14 (see `guard_write_paths.sh`'s own header). For OS-level hardening beyond the deny rules,
restrict write access at the directory/user level instead of removing the execute bit.

### Layer 1 — Email Body Sanitization (universal)

> **The per-desk "trusted lane" gate was RETIRED 2026-06-19.** Once the sanitizer became
> universal, restricting *which desk* may read email added nothing — the reader-actor STRUCTURE is the wall; the scrub is a speed-bump.
> Any session may now read email **through the sanitizer**. The historical lane setup
> (launcher `TRUSTED_EMAIL_LANE` exports, the `guard_email_reads.sh` hook) is gone; launchers may
> still set the env var, but it now only LABELS the read-audit log and gates nothing. The note
> blocks below are kept for history only.
>
> **This-repo note:** `shared/tools/email_convert.py` (named throughout the blocks below) **landed
> 2026-08-14** — this note previously said it did not exist here, which was true when written and is
> not now. It routes through `shared/gate/ingest_gate.py` for the sanitize+scan step, with
> `shared/tools/email_service_read.py` as the read path. ⚠ Present is not proven: it passes its own
> 9-case self-test and a hostile fixture flagged correctly, but it has never been run against a real
> mailbox here. Read the blocks below for the REASONING, not as a map of this repo's files.

**File:** `~/.claude/hooks/ingest_gate_enforce.sh` (PreToolUse; Bash/WebFetch/WebSearch/Read) — the unified gate; its email branch SUBSUMED the retired `enforce_email_sanitize.sh` (2026-07-03).

**Logic:** Intercept any RAW `gws gmail messages get` / `threads get` body read
(`"format":"full"|"minimal"|"raw"`, or read aliases) and BLOCK it — forcing the read through
`email_convert.py` (L0 scrub + heuristic injection scan + the Sentinel gate). A read already routed
through `email_convert.py` passes; metadata reads (list/labels/getProfile/`format:metadata`) pass
untouched. This is the universal defense: **every** email body any desk/session reads is sanitized
first, so a raw injection payload never reaches the model.

**IMPORTANT — launcher edits are manual, if a launcher is outside the write-path guard's approved
zones.** Once Layer 2 (the write path guard) is deployed, Claude cannot edit files outside those
zones — edit any such launcher yourself first.

(The donor's env-var-inheritance diagnostic and file-based fallback for a per-desk trusted lane are
omitted here — that whole mechanism was the per-desk "trusted lane" gate the callout above already
marks RETIRED, and its worked example named a desk this repo doesn't ship. The general lesson — test
whether a launcher-set env var actually reaches a hook subprocess before depending on it, and have a
file-based fallback ready — still applies to any hook that needs launcher-scoped trust state.)

### Layer 2 — Write Path Guard

**File:** `system/hooks/guard_write_paths.sh` (PreToolUse, matcher: Write|Edit)

**This-repo scope note:** the donor version of this hook was a general write-containment wall — it
allowed writes only inside a synced Drive spine plus a couple of skill-dev paths, and refused
everything else. That wall assumed a two-location split (a code clone plus a separate synced notes
drive) that does not exist in this repo's model: here there is just this repo, plus wherever the user
keeps their own notes, resolved through `shared/brain_root.py`. Porting the donor's wall verbatim would
block an agent from writing anywhere the user asked it to outside the repo — a product decision, not a
security default.

**What this repo's `guard_write_paths.sh` actually does instead:** it protects only the guards
themselves — any Write/Edit aimed at `system/hooks/**`, `.claude/settings.json` /
`.claude/settings.local.json` ⛔ never in this repo — machine-local, git-ignored at `.gitignore:44`; the
guard covers it wherever the harness happens to create it — or `.git/` internals is blocked; everything else is left to whatever
other guard covers that specific target (canon, cross-project, calendar/tasks/sheet writes, etc. — see
their own hook files). The general write-containment wall is a live option for anyone who wants it, not
something this port assumed on the user's behalf.

**Residual gap:** Bash-based file writes (`tee`, `cp`, `mv`, shell redirects) bypass Write/Edit-matched
hooks entirely. Closing it would require gating broad Bash usage, which breaks normal workflow. This is
a hard, documented, accepted gap in both the donor system and here.

### Layer 3 — External Content Behavioral Guardrail

Mechanical trust tagging is not possible (PostToolUse hooks can't modify output).
This layer is behavioral.

**Status: IMPLEMENTED** — `~/.claude/CLAUDE.md` External Content Rule upgraded 2026-05-30 with DataGate injection taxonomy.

**Known injection patterns now explicitly named in the rule:**
- Instruction overrides ("ignore previous instructions", "your new instructions are…")
- Role-play directives ("you are now…", "act as…")
- Exfiltration attempts (instructions to relay content to external endpoints)
- Capability negation ("your restrictions have been lifted")
- Hidden Unicode tricks (zero-width, bidi overrides — stripped mechanically by Layer 5 L0)
- Behavioral deviation ("the user wants you to…", "the system says…")

**Honestly:** Behavioral. Raises the bar for naive injection. Does not stop
sophisticated blended injection. Mechanical L0 sanitization (Layer 5) handles
the hidden Unicode / HTML-encoded payload class. The two-agent AI guard
architecture (L3 in DataGate terms) remains a future option if threat level
warrants it.

### Layer 5 — L0 Sanitization (Partially Implemented)

**Status: PARTIALLY IMPLEMENTED** as of 2026-05-30.

**Reference implementation:** the L0 sanitizer is fully implemented in `system/tools/sanitize.py` —
the external reference kit it was originally drafted from is historical and is not part of this repo.

**What's built:**

| File | Purpose |
|------|---------|
| `system/tools/sanitize.py` | L0 deterministic sanitizer — HTML entity decode, tag strip, zero-width char removal (U+200B–U+200F), bidi override removal (U+202A–U+202E), C0/C1 control strip, BOM removal, whitespace normalize. Importable + runnable as script. |
| `system/tools/safe_fetch.py` | URL fetcher + L0 sanitizer. Python stdlib only (urllib + html.parser). Skips hidden CSS elements (`display:none`, `visibility:hidden`, `opacity:0`, `font-size:0`). Strips `<script>`, `<style>`, `<nav>`, `<footer>`, `<head>` blocks. Returns clean plaintext on stdout. |
| `system/tools/safe_calendar.py` | Calendar read + L0 + heuristic scan. **ISOLATE-BY-DEFAULT (2026-07-04):** free-text (summary/description/location + attendee names) is moved to a LOCKED `/tmp/rdr` scratch file; stdout returns structural fields (times/IDs) + a `_reader_scratch` pointer (free-text redacted with a marker). Modes: default=isolate · `--redact` (real text, injection spans neutralized — used by `planning-vault-pull.py`) · `--no-isolate` (raw, no-LLM plumbing only, e.g. `planning-health`). Hook-enforced by `ingest_gate_enforce.sh` (branch d). |
| `system/tools/safe_tasks.py` | Google Tasks read — same isolate-default architecture as `safe_calendar.py`. Free-text (task title/notes) → `/tmp/rdr`; stdout = structural fields (id/status/due/parent) + `_reader_scratch` pointer. Same 3 modes. Hook-enforced by `ingest_gate_enforce.sh` (branch e). |

**Wired in:**
- Email bodies: the donor's `email_convert.py` (L0 sanitize + heuristic injection scan on body text,
  with an HTML-mail fallback) does not exist in this repo. Its scan logic now runs through the shared
  `shared/gate/ingest_gate.py` gate; the email READ path is `shared/tools/email_service_read.py`. Treat
  this paragraph's description of `email_convert.py`'s internals as the donor's design record, not this
  repo's current code — the HTML-fallback extraction detail has not been re-verified against this
  repo's actual read path.

**Wired and enforced:**
- `safe_fetch.py` — WebFetch hook blocks direct WebFetch, redirects to safe_fetch.py. Tested: 69/69 tests GREEN, benchmark WIRE_IN (AP News: 491k → 8.8k tokens, 98.2% reduction, 111ms overhead).
- `safe_search_api.sh` — WebSearch hook blocks native WebSearch, redirects to /websearch skill, which calls the Serper API directly (no browser). **Corrected 2026-08-15 (T9.5f):** an earlier Chrome/dev-browser fallback (`safe_search.sh`) is DELETED — the operator, `authority: user`: *"research should always work through server... that's an old leftover thing."* There is deliberately no fallback; a search that cannot run through the server path fails and reports why, rather than falling back to a browser dependency this repo doesn't ship.
- `safe_input.py` — Heuristic injection detector + L0 sanitizer for externally-sourced content. 20 known injection patterns (instruction overrides, role-play directives, system prompt extraction, base64 obfuscation, jailbreak keywords). Exit 0 = clean, exit 1 = flagged. Known limitation: false positives on content ABOUT injection (e.g., searching for "prompt injection" flags "Act as a hacker" in search results).
- File format tools: `safe_pdf.py`, `safe_docx.py`, `safe_csv.py`, `safe_xlsx.py` — Read hook blocks .pdf/.docx/.xlsx/.csv, redirects to format-specific safe reader. 170/170 tests GREEN across 3 iterations.

**Attack surface coverage (as of 2026-06-12):**

| Surface | Mechanical | Behavioral |
|---------|-----------|-----------|
| Email bodies (text + HTML) | L0 + injection scan via the shared `shared/gate/ingest_gate.py` gate; reads go through `shared/tools/email_service_read.py`. (Donor-system detail, not re-verified 1:1 against this repo's exact read path — directionally accurate.) | External Content Rule |
| Calendar reads | `ingest_gate_enforce.sh` → `safe_calendar.py` (isolate-default: free-text → `/tmp/rdr` scratch + `_reader_scratch` pointer) → `ingest-reader` sub-agent | Calendar in External Content Rule |
| Google Tasks reads | `ingest_gate_enforce.sh` → `safe_tasks.py` (same isolate-default as calendar) → `ingest-reader` sub-agent | External Content Rule |
| Links in email | WebFetch hook → safe_fetch.py | "No following links" rule |
| WebFetch (active workflows) | WebFetch hook → safe_fetch.py | External Content Rule |
| WebSearch | `ingest_gate_enforce.sh` blocks native WebSearch → **Serper API, the only path** (`safe_search_api.sh`, direct Bash, no browser). **No Chrome/dev-browser fallback** — deleted 2026-08-15 (T9.5f); a fallback that cannot run in this repo is worse than none. Spawned sub-agents MUST call `safe_search_api.sh` directly (can't run `/websearch` skill). `/research` fan-out uses the `web-searcher` restricted agent (`.claude/agents/web-searcher.md`, tools: Bash+Read only — structurally forced through the safe stack, cannot bypass). | External Content Rule |
| PDF/DOCX/CSV/XLSX files | Read hook → safe_pdf/docx/csv/xlsx.py | External Content Rule |
| External paste (web results, copied text) | safe_input.py (manual invocation) | External Content Rule |
| Attachments | None yet — a blanket deny needs case-by-case exceptions for legitimate attachment workflows | "No attachment content" rule |

### Named Scope Exceptions

The donor system carved two sources out of the gate: internal-origin Supabase MCP reads (for a desk
this repo doesn't ship), and local-network Home Assistant entity strings (for a home-automation
integration this repo doesn't ship). Neither MCP nor Home Assistant integration exists in this repo, so
neither carve-out applies here — noted rather than silently dropped, in case either integration is
added later, in which case the same trifecta reasoning (is the untrusted-content leg actually present?)
applies fresh.

### Layer 4 — Make Validate-on-Write Blocking (Deferred)

`validate_on_write.sh` currently calls `validate_frontmatter.py` but is
advisory-only (non-blocking). Making it blocking requires: fixing the 3 files
flagged with schema violations in the 2026-05-22 archivist audit first, then
modifying the hook to exit non-zero on exit code 1.

**Do not activate until schema violations are resolved** or the hook will
immediately break legitimate desk writes.

---

## Residual Risks — Honest Accounting

These gaps exist after all layers above are deployed. They are accepted risks,
not oversights.

| Risk | Why It Exists | Mitigation Available? |
|------|--------------|----------------------|
| Bash-based file writes | Hooks cover Write/Edit tools, not shell | Only by blocking broad Bash — breaks workflow |
| Self-modification via Bash | Deny rules + OS perms stop Write/Edit, not Bash redirects | OS-level perms help; separate user is the hard fix |
| Intra-session trusted-lane contamination | Env var is session-scoped, not workflow-scoped | Accept; split into separate sessions if needed |
| Behavioral injection (web/email) | L0 strips hidden Unicode/HTML payloads; safe_input.py catches 20 common injection patterns | Heuristic filter has false positives on security-related content |
| Sophisticated blended injection | L0 handles encoding tricks; safe_input.py catches templated attacks; semantic injection bypasses both | Two-agent AI guard (DataGate L3) is future option |
| Sub-agent env var loss | Platform limitation — hooks in sub-agents may not inherit | Use file-based fallback; document per-agent |

---

## The New User Account Option

(Donor-specific: a macOS new-user-account option for isolating this system's file writes, tied to a
multi-launcher / launchd / synced-Drive setup this repo does not have. Omitted as not applicable to
this repo's model — the underlying question, "do you need OS-level isolation beyond deny rules and
guards," still applies to any install; the donor's specific migration checklist does not.)

---

## Maintenance Protocol

| Trigger | Action |
|---------|--------|
| New external-content channel wired in | Review `<notes>/system/logs/sentinel-events.jsonl` for the new channel's first events; confirm it routes through `shared/gate/ingest_gate.py` |
| New desk/skill added | Check it inherits the right hook coverage (write-path, egress, calendar/tasks guards as applicable) |
| New hook written | Manually test blocking behavior; verify the hook can't be overwritten |
| Any schema violations fixed | Re-evaluate Layer 4 (`validate_on_write.sh`) blocking activation |
| Periodically | Run `/archivist-audit`; review this document for staleness |

---

## Key Principles

**Mechanical over behavioral.** A rule in CLAUDE.md is followed ~90% of the
time. A PreToolUse hook that exits non-zero is followed 100% of the time. When
the failure mode involves security, require mechanical enforcement.

**Guard the guards first.** Every security layer is worthless if a compromised
session can overwrite it. Protect hook scripts and settings before building on
them.

**The launcher is the trust boundary.** Environment variables and flag files
set by `.command` launchers before Claude starts cannot be forged by the model.
This is the hardest trust boundary available without a separate user account
or container.

**Know the platform limits.** PostToolUse hooks cannot modify tool output.
Deny rules do not provide OS-level file protection. Env vars may not propagate
to sub-agents. Design around these constraints, don't assume them away.

**Drift and injection are the same.** The model goes off-policy on its own
AND can be nudged off-policy by injected content. Both require the same fix:
reduce what the model is *capable* of doing, not just what it's *told* to do.

**Accept the residual.** For a personal home system, you are not defending
against sophisticated adversaries. Bash-based write gaps and behavioral-only
injection protection are accepted risks, not failures. The goal is closing the
10% drift gap on high-stakes operations (email reads, write paths) — not
achieving a zero-trust architecture.

---

## Document History

| Date | Change |
|------|--------|
| 2026-05-23 | Initial version — synthesized from two ChatGPT Deep Research passes and red-team iterations |
| 2026-05-30 | Layer 3 upgraded with DataGate injection taxonomy; Layer 5 added (L0 sanitization — email wired in, WebFetch hook deferred pending testing) |
| 2026-05-30 | Layer 5 fully deployed: WebFetch hook wired + tested, file format suite (safe_pdf/docx/csv/xlsx) wired via Read hook, WebSearch hard-blocked with /websearch skill via Chrome + safe_search.sh + safe_input.py heuristic filter. All 8 hooks now have LLM CONTEXT blocks. Hook inventory updated from 3 to 8. Attack surface table updated — all external content surfaces now have mechanical defense except attachments. |
| 2026-06-15 | Added the Governing Lens (lethal trifecta · blast-radius formula · reader-actor typed-handoff · egress-as-top-control · enterprise-skip list · EchoLeak calibration). Procedure split out to `system/sops/agentic-security-sop.md` ✅ **CORRECTED 2026-09-01** — ~~⏳ unruled — that split happened in the system this canon was ported FROM; the procedure doc is on no ship list here and nobody has decided whether it comes~~; the file now exists on disk at `system/sops/agentic-security-sop.md`, confirmed this session. Until then the Governing Lens above is the whole of it. |
| 2026-07-03/04 | **Reader-actor split built and proven live** across several ingestion paths: `agents/ingest-reader.md` (Read-only), `agents/web-searcher.md` (Bash+Read, Serper-forced). **Unified gate deployed**: `ingest_gate_enforce.sh` SUPERSEDES the 6 per-channel hooks (enforce_email_sanitize · sanitize_calendar_reads · guard_file_reads · guard_web_fetch · guard_web_search · guard_skip_safe_backdoor — now RETIRED/not-registered). **Egress wall deployed**: `enforce_egress_allowlist.sh` + `system/egress-allowlist.md` + LuLu OS firewall. **Scratch-dir lock added 2026-07-04**: mechanically enforces reader-actor split by denying MAIN-session reads of `/tmp/rdr/` + `/tmp/ingest_body/`. WebSearch primary path → Serper API (`safe_search_api.sh`); Chrome = fallback only. Attack surface table, hooks table, and WebSearch row updated to reflect current state. **⛔ Migration note, 2026-08-15:** `agents/ingest-reader.md` and `agents/web-searcher.md` are the donor's paths and are not here — both agents themselves DID land, as `.claude/agents/ingest-reader.md` and `.claude/agents/web-searcher.md`; only the top-level `agents/` location did not come across. |
| 2026-07-09 | **Reader-judge escalation model added** to Governing Lens. Documented: regex scanner = metal detector (beeps, decides nothing); `ingest-reader` = JUDGE (decodes + judges flagged spans, emits VERDICT); VERDICT — not raw scan flag — gates redaction and alerting (only REAL-ATTACK escalates). Airport-metaphor escalation chain and buzz-on-VERDICT future-fix noted. |
| 2026-07-04 | **E2E seeded-attack test (watched) + calendar/tasks isolation.** Planted an inert attack in a live email, Google Task, and calendar invite. Result: email isolated (scratch-lock), but calendar + tasks returned raw injection to the controller. Fix: `safe_calendar.py`/`safe_tasks.py` **isolate free-text by default** (→ `/tmp/rdr`, `_reader_scratch` pointer); content-reading skills spawn `ingest-reader`; `--redact` mode neutralizes spans for the vault-pull store (closes the vault downstream-channel gap); `--no-isolate` for no-LLM plumbing. Also fixed a Tasks-gate false positive (param key `tasklist` matched "list" → blocked Tasks writes). |
