# History log for security-canon.md

Text cut or moved out of the SOP, copied verbatim first. Append-only.

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 001 (see drafts/security-canon/applied.md)

~~~~
updated_at: 2026-07-04
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 002 (see drafts/security-canon/applied.md)

~~~~
1. **LLM instruction compliance drift** — the model follows rules ~90% of the
   time. The 10% failure rate is the primary risk. More text rules do not close
   this gap. Only mechanical enforcement does.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 003 (see drafts/security-canon/applied.md)

~~~~
   or settings, disabling its own guardrails. This is partially addressed
   but has a known platform limit (see below).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 004 (see drafts/security-canon/applied.md)

~~~~
4. **Credential exposure / static posture** — handled by Sentinel. Lower
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 005 (see drafts/security-canon/applied.md)

~~~~
**Reader-actor separation (PROVEN 2026-07-03/04 — structural, not behavioral):** the component that READS untrusted text has no tools and no network; the component that ACTS never sees raw text. Pass the reader's output to the actor as **tight TYPED data, never free text** (free-text handoff collapses the separation). In Claude Code: spawn the untrusted-content reader as a tool-less, network-less subagent — a context-isolation guarantee, needs no second model. **Live implementation:** `.claude/agents/ingest-reader.md` (tools: Read only) is the designated reader; `ingest_gate_enforce.sh`'s scratch-dir lock enforces the split mechanically — MAIN-session direct reads of `/tmp/rdr/` + `/tmp/ingest_body/` are denied; sub-agents identified by `agent_id` in hook stdin may read. Proven live across multiple ingestion paths in the system this was ported from; the mechanism is what carries over (the original proof record was a project file on that system's synced drive and does not ship in this repo). **Extension:** a seeded-attack test found calendar + Google Tasks returned raw injection to the controller while email did not (its scratch-lock isolates it). Fixed — `safe_calendar.py`/`safe_tasks.py` **isolate free-text by default** (→ `/tmp/rdr` scratch, `_reader_scratch` pointer on stdout); content-reading skills spawn the reader; modes `--redact` (neutralize spans, used by `planning-vault-pull.py` to close the vault-as-downstream-channel gap) / `--no-isolate` (raw, no-LLM plumbing only).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 006 (see drafts/security-canon/applied.md)

~~~~
**Escalation model (airport metaphor — how the reader-actor pipeline actually responds):** (1) **Metal-detector regex** = cheap, fast, over-flags — beeps "look here," decides nothing, never blocks on its own. (2) **Tool-less `ingest-reader`** = the JUDGE ("body scanner"): for EACH flagged span only, it decodes the encoding (base64/hex/URL/zero-width) and judges by MEANING — real injection vs. benign encoded content; redacts only real attacks, passes benign spans through unchanged, emits a VERDICT per span (`REAL-ATTACK | BENIGN | NONE`). (3) **The reader's VERDICT — not the raw scanner beep — gates both redaction AND alerting**: only a `REAL-ATTACK` verdict triggers a quarantine or phone notification; a beep that resolves to `BENIGN` is silently cleared. Note: buzz-on-VERDICT (phone alert wired to the ingest-reader output) is a documented FUTURE fix — the structural redaction is live; live alerting still fires on the scan flag as an interim. The reader judges only what-to-redact, never whether-to-act; DANGER-class content hard-quarantines regardless.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 007 (see drafts/security-canon/applied.md)

~~~~
### What Sentinel Covers (Static Posture)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 008 (see drafts/security-canon/applied.md)

~~~~
Sentinel is a read-only audit agent. It checks:
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 009 (see drafts/security-canon/applied.md)

~~~~
**Sentinel does NOT cover:** runtime behavior, prompt injection, write path
violations, or email access scope enforcement. It is a static snapshot, not a
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 010 (see drafts/security-canon/applied.md)

~~~~
local, non-synced path (this system's own config home is `~/.config/lifehack/`) and treat anything
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 011 (see drafts/security-canon/applied.md)

~~~~
**Cadence:** review `<notes>/system/logs/sentinel-events.jsonl` and the paused-source list
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 012 (see drafts/security-canon/applied.md)

~~~~
⚠ The event log is written under YOUR NOTES ROOT, not into this repository — `sentinel_response.py:52`
resolves it as `{notes root}/system/logs/sentinel-events.jsonl` (falling back to
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 013 (see drafts/security-canon/applied.md)

~~~~
The channels this system treats as untrusted-content inbound, and which adapter sanitizes each one,
are enumerated in the Attack Surface Coverage table below and in `shared/gate/ingest_gate.py`'s own
header — that gate is the single shared enforcement point for every channel except email's DANGER
ceiling (see Layer 1). Treat any channel not listed there as unreviewed, not as cleared.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 014 (see drafts/security-canon/applied.md)

~~~~
| `ingest_gate_enforce.sh` | PreToolUse | Bash\|WebFetch\|WebSearch\|Read | **Unified ingestion gate** — SUBSUMES the 6 per-channel hooks listed below. Enforces: email→`email_convert.py`, docs→`safe_*`, web→`safe_fetch.py`/`safe_search_api.sh`, calendar→`safe_calendar.py`. Fail-closed (non-email internal error → deny; email → FLAG-floored fail-open). **2026-07-04: scratch-dir lock** — denies MAIN-session `Read` of `/tmp/rdr/` + `/tmp/ingest_body/`; sub-agents pass via `agent_id` in hook stdin, structurally enforcing the reader-actor split in both interactive and cron paths. | Yes — fail-closed |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 015 (see drafts/security-canon/applied.md)

~~~~
**SUPERSEDED hooks (retired — do NOT register; functionality folded into `ingest_gate_enforce.sh`):**

| Hook | Superseded Date | Notes |
|------|----------------|-------|
| `enforce_email_sanitize.sh` | 2026-07-03 | Email branch now in `ingest_gate_enforce.sh` |
| `sanitize_calendar_reads.sh` | 2026-07-03 | Calendar branch now in `ingest_gate_enforce.sh` |
| `guard_web_fetch.sh` | 2026-07-03 | WebFetch branch now in `ingest_gate_enforce.sh` |
| `guard_web_search.sh` | 2026-07-03 | WebSearch branch now in `ingest_gate_enforce.sh` |
| `guard_file_reads.sh` | 2026-07-03 | Read branch now in `ingest_gate_enforce.sh` |
| `guard_skip_safe_backdoor.sh` | 2026-07-03 | `CLAUDEOPS_SKIP_*` block now in `ingest_gate_enforce.sh` |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 016 (see drafts/security-canon/applied.md)

~~~~
This repo's deny list closes it directly, and `guard_write_paths.sh` (ported) backs it up as a
PreToolUse guard on the same paths — see that hook's own header for the 2026-08-14 measurement that
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 017 (see drafts/security-canon/applied.md)

~~~~
**Do not remove this flag as a security fix if you use it.** Hooks are the enforcement layer; the
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 018 (see drafts/security-canon/applied.md)

~~~~
not a hook. This is a future option, not a current one.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 019 (see drafts/security-canon/applied.md)

~~~~
> `shared/tools/email_service_read.py` as the read path. ⚠ Present is not proven: it passes its own
> 9-case self-test and a hostile fixture flagged correctly, but it has never been run against a real
> mailbox here. Read the blocks below for the REASONING, not as a map of this repo's files.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 020 (see drafts/security-canon/applied.md)

~~~~
keeps their own notes, resolved through `shared/brain_root.py`. Porting the donor's wall verbatim would
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 021 (see drafts/security-canon/applied.md)

~~~~
architecture (L3 in DataGate terms) remains a future option if threat level
warrants it.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 022 (see drafts/security-canon/applied.md)

~~~~
### Layer 5 — L0 Sanitization (Partially Implemented)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 023 (see drafts/security-canon/applied.md)

~~~~
**Status: PARTIALLY IMPLEMENTED** as of 2026-05-30.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 024 (see drafts/security-canon/applied.md)

~~~~
- Email bodies: the donor's `email_convert.py` (L0 sanitize + heuristic injection scan on body text,
  with an HTML-mail fallback) does not exist in this repo. Its scan logic now runs through the shared
  `shared/gate/ingest_gate.py` gate; the email READ path is `shared/tools/email_service_read.py`. Treat
  this paragraph's description of `email_convert.py`'s internals as the donor's design record, not this
  repo's current code — the HTML-fallback extraction detail has not been re-verified against this
  repo's actual read path.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 025 (see drafts/security-canon/applied.md)

~~~~
| Email bodies (text + HTML) | L0 + injection scan via the shared `shared/gate/ingest_gate.py` gate; reads go through `shared/tools/email_service_read.py`. (Donor-system detail, not re-verified 1:1 against this repo's exact read path — directionally accurate.) | External Content Rule |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 026 (see drafts/security-canon/applied.md)

~~~~
| External paste (web results, copied text) | safe_input.py (manual invocation) | External Content Rule |
| Attachments | None yet — a blanket deny needs case-by-case exceptions for legitimate attachment workflows | "No attachment content" rule |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 027 (see drafts/security-canon/applied.md)

~~~~
| Sophisticated blended injection | L0 handles encoding tricks; safe_input.py catches templated attacks; semantic injection bypasses both | Two-agent AI guard (DataGate L3) is future option |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 028 (see drafts/security-canon/applied.md)

~~~~

---

## The New User Account Option

(Donor-specific: a macOS new-user-account option for isolating this system's file writes, tied to a
multi-launcher / launchd / synced-Drive setup this repo does not have. Omitted as not applicable to
this repo's model — the underlying question, "do you need OS-level isolation beyond deny rules and
guards," still applies to any install; the donor's specific migration checklist does not.)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 029 (see drafts/security-canon/applied.md)

~~~~
| New external-content channel wired in | Review `<notes>/system/logs/sentinel-events.jsonl` for the new channel's first events; confirm it routes through `shared/gate/ingest_gate.py` |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 030 (see drafts/security-canon/applied.md)

~~~~
| Any schema violations fixed | Re-evaluate Layer 4 (`validate_on_write.sh`) blocking activation |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 031 (see drafts/security-canon/applied.md)

~~~~
**Mechanical over behavioral.** A rule in CLAUDE.md is followed ~90% of the
time. A PreToolUse hook that exits non-zero is followed 100% of the time. When
the failure mode involves security, require mechanical enforcement.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: security-canon hunk 032 (see drafts/security-canon/applied.md)

~~~~
10% drift gap on high-stakes operations (email reads, write paths) — not
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13: SC4 retired hook table moved out, approved screen

~~~~
# security-canon archive (moved word for word from the live text, SC4, rulebooks run 2026-11-12)

This is a historical record, not live instruction. Moved out of `security-canon.md` "Existing Hooks" (frozen copy L147-156).

**SUPERSEDED hooks (retired — do NOT register; functionality folded into `ingest_gate_enforce.sh`):**

| Hook | Superseded Date | Notes |
|------|----------------|-------|
| `enforce_email_sanitize.sh` | 2026-07-03 | Email branch now in `ingest_gate_enforce.sh` |
| `sanitize_calendar_reads.sh` | 2026-07-03 | Calendar branch now in `ingest_gate_enforce.sh` |
| `guard_web_fetch.sh` | 2026-07-03 | WebFetch branch now in `ingest_gate_enforce.sh` |
| `guard_web_search.sh` | 2026-07-03 | WebSearch branch now in `ingest_gate_enforce.sh` |
| `guard_file_reads.sh` | 2026-07-03 | Read branch now in `ingest_gate_enforce.sh` |
| `guard_skip_safe_backdoor.sh` | 2026-07-03 | `CLAUDEOPS_SKIP_*` block now in `ingest_gate_enforce.sh` |

~~~~
