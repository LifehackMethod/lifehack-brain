---
topic: [agent-security]
id: system-playbook-agentic-security
title: "Securing a New Agentic Path — playbook"
record_type: playbook
desk: root
status: active
authority: user
created_at: 2026-06-15
updated_at: 2026-06-15
sources:
  - system/security-canon.md (the posture + hook specs + platform limits — the WHY/architecture)
  - system/archivist/insight-inbox/2026-06-15-research-sop-draft-validation.md (web validation)
---

# Securing a New Agentic Path

**How to make a new path safe BEFORE you ship it — any path where an agent reads untrusted content (email, web, files) or can take actions (sends, writes, deletes, external calls).**

> **Through-line (confirmed 2026-06-15 — validate in use):** The dangerous thing about an AI agent isn't that attackers are clever — it's that **the model literally can't tell your instructions from the content it reads**, so the only real defense is removing *capability*, not adding detection. *Why it's hard the first time:* the instinct is to "scan for bad input," but 99% detection is a failing grade (the attacker finds the 1%) — and it's just as easy to over-build enterprise security theater a one-person system never needed. *What failure looks like:* a new desk or cron quietly reads raw email bodies, or an injected string makes the agent send/delete/exfiltrate something — and there was no *gate* that would have stopped it, only a rule it was supposed to follow.

This is the **procedure**. The posture, the hook specs, and the platform limits live in **`system/security-canon.md`** — read that for the *why* and the *how-it's-built*; this is the *what-to-do*.

---

## Step 1 — Apply the lens (before building anything)
- **Break a leg of the lethal trifecta.** Catastrophe needs all three at once: private-data access · untrusted-content ingestion · an outbound channel. Ask "do all three co-exist on this path?" If not, the threat class is mostly already gone. (Full lens: security-canon.md → "The Governing Lens.")
- **Rate the blast radius:** `(autonomous?) × (reversible?) × (write scope)`. A skill you run by hand that fails visibly ≈ zero blast radius; a cron with send/delete is real.

## Step 2 — Build the structural floor (in order)
1. **Least-privilege tools** — no standing send/delete/write; grant at the moment of need.
2. **Reader-actor separation** — the thing that *reads* untrusted text has **no tools and no network**; the thing that *acts* **never sees the raw text**. Hand the reader's output to the actor as **tight TYPED data, never free text** — e.g. a fixed-key struct `{source, body_text, flags[], metadata}`; the actor extracts only defined keys and wraps any quoted free text in a clearly-marked `DATA:` block. (Free-text handoff collapses the whole separation — Anthropic's named failure mode.)
3. **Sanitize at a hook chokepoint, not the honor system** — one shared scan enforced by a hook, so a *new* consumer can't silently skip it. (ClaudeOps: the `safe_*` tools + the PreToolUse guards — security-canon.md Layer 5.)
4. **Human-gate irreversible actions** — autonomous OK for reversible/low-blast (log, flag, quarantine-hold); irreversible/high-blast (delete, external send, halt-all) needs a human turn.
5. **Egress / output filtering (the strongest single control)** — block or allowlist unexpected *outbound* calls and validate tool-output shape. This structurally caps exfiltration *even if* an injection succeeds — better signal-to-noise than any input scanner.

## Step 3 — Ingestion specifics
- **HTML → plain text with a real stdlib parser (`html.parser`), NEVER regex** (regex silently fails on `>`-in-attribute, split tags, CDATA, comments). Decode entities *during* the parse, not after. This is text extraction, not XSS sanitizing. (Built: `safe_fetch.py` / `email_convert.py`.)
- **Strip hidden/zero-width/bidi chars; never auto-fetch links; skip attachments by default.** The cheapest defense is often an *absence* — don't scan for a risk the pipeline never runs.
- **Retrieved documents (RAG) are an injection surface too** (OWASP LLM01) — content pulled into context counts as untrusted, same as email/web.
- **Use the model's instruction-hierarchy / system-prompt privilege** where the platform offers it — a complementary first line, not a replacement for the floor.

## Step 4 — When something's flagged: the response ladder (graduated, never binary)
| Signal | Response |
|---|---|
| low / single flag | log only |
| moderate | flag + continue |
| accumulating (per-source sliding window) | quarantine the item + hold for review |
| high-confidence, high-blast | block |
| systemic / critical path | halt + notify |

Rules: **quarantine the item, never halt the whole pipeline** (that's a self-inflicted DoS); notify only on danger + accumulation (per-flag alerts → alarm fatigue → alerts get disabled → zero protection); a flagged payload is inert text — re-read it safely in the tool-less reader, **never paste it into a live tool-having assistant to "analyze it."**

## Step 5 — The new-path audit checklist (run this before shipping)
- [ ] Do all three lethal-trifecta legs co-exist here? If so, which leg breaks it?
- [ ] What's the blast radius (autonomous? reversible? write scope)?
- [ ] Is untrusted content isolated in a tool-less reader before the actor — handed over as typed data?
- [ ] Is the sanitize path enforced by a hook (not "remember to call the cleaner")?
- [ ] Are irreversible actions human-gated?
- [ ] Does the security gate **fail OPEN** (bounded timeout + try/except → findings stand, verdict undetermined)? A gate that crashes the read it guards is worse than the gap.
- [ ] Is egress filtered / outbound allowlisted?

## Step 6 — Don't build (enterprise overkill — deliberately skip)
Full CaMeL capability-interpreters · enterprise injection-classifier programs + red teams · SOC 2 / MITRE-ATLAS / formal audit trails · SOC monitoring · heavy multi-layer injection-scanning pipelines (≈99.5% false positives → operators disable them → net protection zero). **Recording what you skip and why is half a right-sized posture.** (Full list: security-canon.md → "Deliberately Skip.")

---

*Reality check (2026-06-13): personal-scale agents ARE now real targets (EchoLeak, a zero-click email-injection in Microsoft 365 Copilot, CVE-2025-32711) — but that was an enterprise product, so treat it as a calibrated heads-up, not proof someone is hunting your home agent. The structural floor above is worth it regardless; the enterprise tooling in Step 6 is not.*
