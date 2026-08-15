---
topic: [ingestion-pipeline, system-architecture, agent-security]
id: system-information-ingestion-interpretation
title: "Information Ingestion & Interpretation — the ONE-GATE doctrine"
record_type: reference
desk: root
status: active
authority: user
created_at: 2026-07-11
updated_at: 2026-07-12
tags: [ingestion, interpret, one-gate, sentinel, item-store, dead-ideas, injectable]
note: The definitive, injectable picture of how information enters this system and how a desk reads it. Point a confused/fresh session here when it starts reinventing ingestion. Security deep-dive = system/security-canon.md; the reader spec = system/ingestion-reader-contract.md.
---

# Information Ingestion & Interpretation

> **When to inject this:** a fresh session starts reinventing how ingestion / email / corpus-reading /
> security should work, or tries to resurrect an approach we already killed. This doc outranks any
> half-remembered pattern.
>
> **THE RULE THAT GOVERNS EVERYTHING BELOW — ONE SECURITY GATE, AT INTAKE (the airport model).**
> **Every** external input — email, a task, a calendar invite, a PDF, a Word doc, a markdown file, a web
> page, a Google-Doc export, pasted text, *anything* from outside — passes the **complete** security stack
> **once, at the door**: mechanical scrub → regex scan → the tool-less redaction reader. The **cleared copy**
> is what gets stored. **Once inside, content is TRUSTED — every agent uses it freely, with NO second security
> check, ever.** One checkpoint, then airside.
>
> Two phases follow from this and must not be confused: **INTAKE** (clean + secure + store a faithful copy)
> and **INTERPRET** (a desk makes sense of the already-cleared copy). Intake carries ALL the security; interpret
> carries none — it trusts the store.

> **▶ STATUS IN THIS REPO.** The one-gate doctrine is ratified AND shipped — the redaction reader runs at
> intake, not at per-consumer read-time; verify in `shared/tools/email_service_read.py`'s `reader_applied`
> handling (§1 below). The donor doc this was ported from carried a `[CURRENT]` vs `[TARGET]` migration
> tracker here, pointing at a project file (`injection-gate-overblock-handoff.md`) and a component-map doc
> (`sentinel-build-reference.md`) that lived on that system's own synced drive — neither ships in this
> repo, and neither is needed here: what follows is not a target this repo is moving toward, it is what
> the code already does. `system/security-canon.md`'s Attack Surface Coverage section is this repo's
> component + channel map.

---

## 1. INTAKE — clean + secure + store a faithful copy

Intake takes whatever is coming in and turns it into a **clean, faithful, CLEARED, stored copy** — no
interpretation yet. It runs in **two modes**, and many source types plug into each.

### The two modes
**A) The firehose (streaming intake).** New material arriving continuously — today's email, a new task, a new
calendar event. Swallowed whole by the machine, **no human**, on whatever cadence the item-store writers
are run.
- Done by the item-store writers `shared/tools/tasks_store_sync.py` and `shared/tools/calendar_store_sync.py`
  — both ship here and are real, runnable janitors (`--sync`, `--dry-run`, `--self-test`). ⛔ **The
  email-side writer does not ship in this repo.** `shared/tools/email_service_read.py` is the READ adapter
  for a faithful email store that a *separate* Gmail-pulling process populates (its own header calls that
  process "the janitor" and, in code comments only, carries the donor's internal ticket name for it,
  "Grand Central" — neither name marks a shipped file here). On a fresh install, or before an account is
  connected, every email read returns `MISS-NEW` ("no record for this thread") — that is the correct,
  by-design state of an unconnected store, never a broken adapter. **There is also no scheduler in this
  repo** — whatever populates a store (a janitor a team wires up, a manual sync run) fires on whatever
  cadence its operator gives it, not a fixed interval this repo assumes for you.
- Stores a **faithful de-duplicated copy — never a summary**: every message/event/task, chronological,
  attachments as pointers, with a completeness guard so nothing is silently dropped, under
  `<notes>/state/email-summary/threads-v2/` + `<notes>/state/item-store/`.
- The store is **durable memory, never a cache — never hard-deleted** (lifecycle active→completed→cold→deep-cold).

**B) The archive (bulk-corpus intake).** A giant one-time pile — years of old chat exports, a document
dump, a pile of notes from somewhere else entirely. **Worked in sections, a human ruling whole baskets.**
This is what the **`/ingest` skill** already does on a personal text corpus (chat export, large document,
markdown, or plain text — see `.claude/skills/ingest/SKILL.md`; email and complex structured formats are
explicitly out of its scope).

### The security stack — runs ONCE here, at intake
Every item, both modes, passes the full stack before it is stored (the component map is
`system/security-canon.md`'s Attack Surface Coverage section): **(1)** L0 mechanical scrub
(`system/tools/sanitize.py` — strip hidden chars / HTML / encoding) → **(2)** regex injection scan
(`system/tools/safe_input.py` — the **metal detector**: beeps "look here," decides nothing, over-flags
intentionally) → **(3)** the **tool-less judge reader** (`.claude/agents/ingest-reader.md`, Haiku, no
Bash/Write/network) which acts as the **body scanner**: for EACH flagged span ONLY, it **decodes** (base64
/ hex / URL / zero-width) and **judges by meaning** — real injection (a command / "you are now…" /
exfiltration / prompt-override) vs benign (signing token, tracking hash, ID). It **redacts ONLY real
attacks**; benign flags are cleared and kept verbatim; everything OUTSIDE a flagged span is carried
whole/verbatim. The reader's **VERDICT** (REAL-ATTACK | BENIGN | NONE) — not the raw scanner beep — is what
gates redaction. What lands in the store is the **cleared** copy. **✅ SHIPPED — the reader runs HERE, AT
INTAKE**, both as the tool-less `ingest-reader` subagent for a controller that holds tools, and as
`shared/tools/intake_reader.py` (a `claude -p haiku` decode-and-judge caller with the same contract) for a
non-interactive writer like the item-store sync scripts. *(This repo's own code comments carry the same
build history the donor doc did — `shared/tools/email_service_read.py` still references commit `3e4b37d`
for the re-scan-skip half. Re-check the CODE before trusting any status marker in a doc, including this one.)*

- **Graded response:** a merely-flagged item whose verdict is BENIGN or NONE is **kept verbatim** — no
  redaction. A REAL-ATTACK verdict is **redacted-and-stored** (bad span blacked out, the rest kept and usable).
  A genuinely-DANGER-class item is **hard-quarantined at the door and NOT stored** (reversible Gmail label,
  never deleted, via `shared/gate/sentinel_quarantine.py`).
- **Alerting gates on verdict, not beep [FUTURE FIX — not built yet]:** only a REAL-ATTACK verdict should
  trigger a phone-buzz notification (the governed push path here is `shared/notify/notify-send.sh` +
  `shared/notify/notify-governor.py`). Today the buzz fires on the raw scanner beep, causing notification
  spam for benign flags. Wiring the buzz to the reader's verdict is a documented future fix.
- **`reader_applied` marker — LIVE, both halves:** the cleared record carries the flag and read-side
  adapters (`shared/tools/item_store_read.py` / `shared/tools/email_service_read.py`) honour it **twice
  over** — they skip the redundant **re-scan** *and* skip the redundant **isolation**, so a cleared record
  is served INLINE to a tooled desk with no second reader. Both checks are strict `is True`, so an unmarked
  record still scans AND still isolates — **fails closed.** A `REPLY-FLAGGED` record is refused even when
  cleared, regardless of the marker. *(The donor doc measured live coverage on its own populated mailbox —
  95.3% of its threads carried the marker at the time. That count is that install's own snapshot, not a
  fact about this repo: this repo's store starts empty until an account is connected. What carries over is
  the mechanism, not the number.)*

### Universal scope — every channel, or a NAMED exception (never a silent hole)
The channel-coverage table lives in `system/security-canon.md`'s Attack Surface Coverage section. The rule
is universal; the two honest edges:
- **Pasted / typed text in a conversation turn** cannot be gated by a hook (no tool call fires on a chat
  turn). **Closed by convention, via a drop-file:** the operator writes a message into a plain
  text/markdown file, and reading it back is a gated tool call (L0 scrub + injection scan + the Sentinel
  gate on the way in, because typed text is untrusted external content) through `system/tools/safe_read.py`.
  Its optional `--clear-after` flag self-erases the file after a successful read — POST-read only, never on
  an error path, so "empty = it was pulled." That is a one-way pull, not a fixed two-way overwrite slot;
  the donor system had evolved its own drop-file into exactly such a two-way convention, but that specific
  shape is not what ships here — a per-install team can build the same convention on top of
  `--clear-after` if they want it.
- **`.txt`/`.md` reads and a Google-Doc export are GATED** — verify in `system/hooks/ingest_gate_enforce.sh`
  (the trusted-zone allowlist plus the `.txt`/`.md` and `drive files export` arms). **Web fetch/search is a
  NAMED, ACCEPTED exception** — it is scrubbed (L0) + injection-scanned (`system/tools/safe_input.py`) +
  egress-capped (`system/hooks/enforce_egress_allowlist.sh`), but not `/tmp/rdr` reader-isolated. By the
  adopted security posture (structural least-privilege + human-gated actions + EGRESS filtering beat heavy
  input-side isolation — a finding inherited from the system this doc was ported from), that is sufficient,
  NOT a gap to close.

### Why intake is built this way (stops relitigation)
- **Faithful copy, never an AI *summary*.** A `/research` pass found LLM summaries fabricate ~25% of named
  entities and mash dates/dollar-amounts; mechanical de-dup gets a ~73–86% size cut with **zero** fidelity
  loss. The word "summary" is banned here on purpose. **The reader REDACTS, it does not summarize — so
  fidelity survives the security step.**
- **Store-first over re-reading the source.** Read once, well, and never re-read; the cleared store is the record.

### Dedup = archive-state (how "done" is marked, firehose)
Inbox label = still needs processing; moved to archive label = done. Not read-state, not a timestamp.

---

## 2. INTERPRET — a desk makes sense of the CLEARED store (no security burden)

Because intake already cleared the content, a desk reading it **trusts the store — no second reader, no re-scan.**
Interpret is a *judgment* problem, not a security one.

### The doctrine it LOCKS: **SHARED HOW · PRIVATE WHAT**
- **Shared HOW (every desk):** read store-first; **right-size the model**; **batch, don't go one-at-a-time**;
  **sort-then-read** (cheap triage, deep-read only the keepers). *(Note: the old "always read bodies via the
  tool-less reader" clause is retired at the desk layer — that security step now lives at intake. Desks read
  the cleared store directly.)*
- **Private WHAT (each desk's identity — do not touch):** what a desk judges FOR and where it FILES. This
  repo does not ship named desks — `docs/data-layout.md`'s `desks/<subject>/` is one folder per subject,
  built by `/ingest` from a person's own material — but the principle holds for any two: a finance-subject
  desk and a career-subject desk read the same store the same way and still judge and file differently.

### Right-sizing the model — the "too cheap" lesson (load-bearing)
- **Verbatim / structural work → Haiku** (the reader returns a clean envelope, no judgment).
- **Judgment a human relies on → Sonnet.** `/ingest`'s SCAN triage was dropped to Haiku for ~8× savings and
  Haiku "lost the intuition that recognizes a chat's project + senses a mis-file" → reverted to Sonnet
  (commit `779157c`, 2026-07-11). Savings from bigger batches are durable; savings from a weaker judgment model
  are not. "Shared" ≠ "one model for all."

### The reference implementation
The `/ingest` skill is the worked example of the shared HOW — one skill led by **VERA THE CURATOR**, run as
FOUR phases (a phase is a unit of human attention, not a machine step): **① SORT** (make the piles) →
**② SCAN** (screen a pile) → **③ DEEP-READ** (the world map) → **④ PLACE** (file it + the root canon —
folding in what used to be a separate filer's load/schema/confirm steps). The MINER (phases ①–③) never
files; only phase ④ writes, and only with approval. This is the concrete instance of the canonical producer
split `ingest → process → emit`. A desk's Stage 2 should follow this shape and swap in its private WHAT.
**Not yet wired into every desk — the named next build.** *(DEEP-READ reads each keeper WHOLE in one
cache-backed pass — below a size ceiling — rather than slicing; a rare giant is sampled head+tail +
flagged. The `sort-then-read` GATE above is unchanged — that's where the token savings live; whole-read is
the accuracy mechanism on the survivors. Normative detail: `.claude/skills/ingest/SPEC.md`.)*

⛔ **Not carried over:** the donor doc tracked an open Stage-2 model-selection inconsistency in a personal
desk's own ingest skill. That skill does not ship in this repo, so there is nothing here to fix — noted so
its absence isn't mistaken for an oversight.

---

## 3. The security spine — the one gate, in one place

**Everything coming in is treated as hostile** (an email, a document, a prior corpus dump can all carry "ignore your
instructions and do X"). Handling is the same regardless of source, and it happens **once, at intake**:
**(1)** mechanically scrub before any model sees it; **(2)** the **no-hands judge reader** (tool-less
`ingest-reader` — Read-only) **decodes each flagged span and judges it by meaning**, redacting only real
attacks; **(3)** the cleared copy is stored and **everything downstream trusts it.**

### The airport-escalation model (teaching metaphor)

| Layer | Analogy | What it does | Decides? |
|---|---|---|---|
| Regex scan (`system/tools/safe_input.py`) | **Metal detector** | Beeps on anything suspicious — fast, cheap, over-flags intentionally | ❌ No — just "look here" |
| Tool-less judge reader (`.claude/agents/ingest-reader.md`) | **Body scanner** | For each flagged span: DECODES (base64/hex/URL/zero-width) + JUDGES by meaning (real attack vs benign) | ✅ Yes — REAL-ATTACK / BENIGN / NONE |
| Quarantine + human review + phone-buzz | **Pat-down / wand / swab** | For genuine DANGER-class content only | ✅ Human |

You never confiscate at the mere beep. The metal detector hands off to the body scanner; only a real find
escalates to the pat-down. Escalating scrutiny — not escalating paranoia.

**Critical framing:** the fix for scanner over-flagging is NOT "exempt encoded strings from the scanner" — that
is an exploited hole (attacks hide inside encoding: base64→command, HashJack URL-fragment, zero-width Unicode,
Morse). The fix lives in the **READER** (decode-and-judge each flagged span), not in the scanner's coverage.
*(This finding is inherited from the system this doc was ported from; its own research record was a project
file on that system's synced drive and does not ship here.)*

**Verdict gates alerting:** only a REAL-ATTACK verdict from the reader should notify/phone-buzz. Buzzing
on the raw scanner beep = spam on every signing link and tracking hash. [Buzz-on-verdict wiring is a FUTURE FIX
— not built yet; see §1 alerting note.]

**Guardrails — the reader judges WHAT to redact, never WHETHER to act:** the reader has no hands (a hijack
can't act), and the **egress allowlist guards the exits** (even a landed injection can't exfiltrate — see
`system/egress-allowlist.md` + `system/hooks/enforce_egress_allowlist.sh`). DANGER-class content still
hard-quarantines regardless of verdict. Detection is a speed-bump pointing the scanner at the right spans;
**safety comes from STRUCTURE**, not from catching every attack.

**Full detail is canonical elsewhere — do not duplicate here:** `system/security-canon.md` (architecture,
hooks, residual risk, and the component + channel map) · `system/ingestion-reader-contract.md` (the reader
spec) · enforcement `system/hooks/ingest_gate_enforce.sh`. The founding principles behind this model —
structure over trust, guard the exits, no-hands reader — are inherited from the system this doc was ported
from; its own founding canon file was a project record on that system's synced drive and does not ship
here. What's in this doc IS the current, updated one-gate stance — there is no separate earlier-stance
document in this repo to reconcile it against.

---

## 4. Dead ideas — DO NOT RESURRECT

| Dead approach | Replaced by | Date · source |
|---|---|---|
| LLM (Haiku) **summary** of first+last message only | faithful mechanical de-dup thread, no summary | 2026-07-10 · compaction-research |
| Any LLM *summarizing/reshaping* in the intake/write path | mechanical de-dup + the **redaction reader** (redacts, never summarizes) | 2026-07-12 · one-gate ratify |
| The security reader runs at READ-time (per-consumer, second gate) | ONE gate at intake; store cleared; trust downstream | 2026-07-12 · one-gate ratify |
| "The scrub is the wall" | the **reader-actor structure** is the wall; the scrub is a speed-bump | 2026-07-12 · one-gate ratify |
| Hard-delete after 8 days | never-delete; lifecycle states | 2026-07-10 |
| Per-desk Gmail pulls as the primary path | the shared item-store + store-first reads (this repo's code comments still carry the donor's internal name for the writer side, "Grand Central," historically) | 2026-07-11 |
| Mark-read dedup | archive-state dedup | 2026-06-03 |
| `load_digest()` (v1 read) as the sanctioned read | `shared/tools/email_service_read.py` / `read_thread()` (v2) | 2026-07-10 |
| Haiku on human-facing judgment ("too cheap") | Sonnet for judgment; Haiku for structural only | 2026-07-11 · `779157c` |
| Cal's own email poll | retire dead-last; read the shared store | 2026-07-10 |

---

## 5. Built vs. not-built (so this doc can't fake completion)
- ⚖ **Firehose intake** — **tasks + calendar ship live**: `shared/tools/tasks_store_sync.py` and
  `shared/tools/calendar_store_sync.py` are real, runnable writers, faithful store, never-delete,
  store-first read. ⛔ **Email's writer does not ship** — `shared/tools/email_service_read.py` is a read
  adapter for a store a separate, unshipped Gmail-pulling process populates; on a fresh install it serves
  `MISS-NEW` until one is connected.
- ✅ **Archive intake for a personal text corpus** (`/ingest`) — **live.**
- ✅ **The security stack** (scrub + scan + tool-less reader) — **live, AT INTAKE**, for every channel whose
  writer ships here (tasks, calendar, `/ingest`'s archive path). The mechanism (`shared/tools/intake_reader.py`,
  the `.claude/agents/ingest-reader.md` contract) is the same mechanism an email janitor would use if one
  were wired up.
- ✅ **Reader-at-intake + `reader_applied` marker + store-cleared** — **the one-gate move is built**, verified
  in `shared/tools/email_service_read.py` (re-scan skip and isolation skip both present, both fail closed on
  an unmarked record). The governing rule is now what the code does: once content is inside the store, it
  is inside the airport — no sub-agent needs to run a second security level on it.
- ⛔ **Scanner precision is NOT a prerequisite** — that dependency was downgraded in the system this doc was
  ported from (2026-07-12): the tool-less reader is the real protection; the scanner is a cheap hint, and
  its length rules emit `FLAG`, never `DANGER`, so a loose scanner is safe. Do not re-raise it as a blocker.
- ✅ **Channel-gap closures** (`.txt`/`.md` reads, a Google-Doc export, the pasted-text drop-file convention)
  — all GATED in this repo's code today; verify in `system/hooks/ingest_gate_enforce.sh` and
  `system/tools/safe_read.py`. The donor doc tracked these as a still-open phase; here they are shipped.
- ✗ **Stage-2 thinking-method** wired into every desk (the `/ingest` shape) — the named next build.

---

## 6. How this doc is loaded
- **Home:** `system/information-ingestion-interpretation.md` (this file; repo-canonical).
- **Linked:** `docs/data-layout.md` is this repo's nearest equivalent to a system architecture map. ⛔
  The donor's own `docs/architecture.md` describes a system this repo is not — it does not ship here.
- **Build-time:** wired into `system/hooks/inject_sop_before_build.sh`, which already names this file on an
  ingestion-shaped build prompt — landing this file is what lets that hook's table row resolve instead of
  degrading silently (see that hook's own header comment). `system/build-rules-index.md` does not route
  here today; its own ingestion row points at `/ingest`'s `SPEC.md` instead, and that is a separate,
  narrower doctrine (the archive-intake skill's own mechanics) than this file's broader security/architecture
  picture.
- **Companion docs:** `system/security-canon.md` (components + channel coverage + hooks + residual risk) ·
  `system/ingestion-reader-contract.md` (the reader spec).
