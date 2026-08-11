---
id: system-build-rules-index
title: Build Rules-of-Engagement Index — what /build must read before it builds
record_type: reference
created_at: 2026-06-20
updated_at: 2026-08-11
status: active
authority: user
---

<!-- CODE-SPIRAL-v2 BEGIN -->
> ⚠ **PROVISIONAL — 2026-08-09.** Best current thinking, not doctrine. Full record:
> it sits in tension with `skill-building-sop.md` LAW 1 and has not been ruled on.
>
> **A failure appears → *"how do we DETECT this?"* is almost always the WRONG FIRST QUESTION.** The model
> is rarely bad at detecting; it is bad at **REMEMBERING TO LOOK**. Detection code answers a delivery
> problem, and that code then needs its own enforcement — that second step is the spiral.
>
> **FIRST, WHAT KIND OF THING IS THIS?**
> **(1) IRREVERSIBLE?** → it must be code. **(2) FIRES WITHOUT BEING REMEMBERED?** → it must be a hook.
> **(3) NEITHER?** → it is a **FACT the session needs to SEE**, not a tool it must remember to run — put
> it where the session already looks. ⭐ **Branch 3 is the one that says build nothing. Take it seriously.**
>
> **THE SESSION IS WHAT'S RUNNING. Code is a guest it may or may not pick up.**
> **IF you are building: it is almost always TWO things — something that fires on its own, and something
> it leaves behind. That is the whole shape.**
>
> **FOUR QUESTIONS, BEFORE YOU BUILD:**
> **1 · WHAT WILL CALL THIS?** Pick one and write it down: a **hook** (fires when a specific action
> happens) · an **injector** (fires every turn, attached to the user's message) · the model remembers.
> **If it's the third, you have a suggestion, not a control.**
> **2 · WHAT ARTIFACT WILL PROVE IT RAN?** Name the file, hash, receipt or record only real execution
> could produce. Without one, "it worked" is a claim, not a fact.
> **3 · IS THERE A SOFT WORD IN IT?** *meaningful · stale · real · right · proper · significant.* If you
> must define the word before you can write the check, **that definition IS the judgment** — and judgment
> is the model's half. Code gets **membership** ("is X in this list?"), **artifacts** ("does this hash
> match?") and **timing** ("fire on this event"). Nothing else.
> **4 · IF THIS BROKE SILENTLY, HOW WOULD YOU FIND OUT?** No answer means you moved the failure somewhere
> invisible. You did not remove it.
>
> ⛔ **THE RULE — AN ORDER, NOT AN OBSERVATION:**
> **IF YOUR FIX HAS THREE PARTS AND ONE OF THEM CHECKS THE OTHER TWO — DELETE THAT ONE.**
> **THE EXCEPTION:** a part that checks its **own** output before finishing is one part. The forbidden
> third is a **separate** thing that watches the first two.
>
> ⛔ **TWO WAYS THIS GETS FAKED — both happen by accident:**
> **Your proof must be made by the work, not by a wrapper around it.** `if it_ran: write_proof()` proves
> only that your wrapper ran.
> **"It fires automatically" is not enough — it must fire in NORMAL OPERATION.** A hook on a once-a-year
> event technically fires and protects nothing.
>
> **A WORKED EXAMPLE — the same problem, solved twice, on one day.**
> **2026-08-09.** A required step got skipped. The session built a namespaced ledger, a coverage table,
> applicability markers and a timestamp check — **111 lines.** An independent auditor broke it five ways in
> six minutes, and every break was in the part that guessed.
> **What actually worked: one line printed into a message that already fires every turn.**
> Same problem, same day. **111 lines versus 1.**
>
> **MEASURED FAILURES IN THIS SYSTEM — why the questions above exist:**
> a script printed `PASSED` daily for two months and wrote no file · a test sat red for 16 days and nobody
> looked · a guard printed its refusal on the wrong channel, blocked nothing, and scored PASS · a detector
> wrote to a log file for weeks that nobody read · **15 tools were built that nothing ever calls, while 49
> registered hooks all fire** · a rule was written into four files and reached none of them.
<!-- CODE-SPIRAL-v2 END -->

<!-- SEAM-RULE-v1 BEGIN -->
> **THE CODE/LLM SEAM — binds only a HYBRID build** (code and a model in the same running product;
> question zero below). **Classify the PRODUCT, not the change.**
>
> **Code hands the model a bounded set of outcomes. The middle is unbounded — the model, alone or in
> conversation with a human, works however it needs to. What comes back is one of those outcomes, and the
> set must contain one meaning NO OUTCOME WAS REACHED. Code checks membership on every path in; anything
> off-list is surfaced, never silently absorbed.**
>
> **The no-outcome member is for the MODEL, not the human.** A human can say anything at any time — the
> session is their escape hatch. The model has to hand code *something*, and with no legal way to say
> "nothing was decided" it manufactures a decision code cannot tell from a real one.
> **Name the slot, never the words** — every product picks its own set; this rule names no vocabulary.
> **Perimeter only** — it governs the shape that crosses the boundary, never how the model reasons inside it.
<!-- SEAM-RULE-v1 END -->

<!-- MODEL-REACH-RULE-v1 BEGIN -->
> LAW 1 above says WHAT crosses the seam. **This asks whether the seam is REACHABLE AT ALL** — a seam
> with no reach is not a weak seam, it is an absent one wearing the paperwork of a present one.
>
> **Three reaches, not interchangeable: SESSION** (skill prose — ⛔ does NOT exist in cron) ·
> **HEADLESS** (`claude -p` — works in cron, ⛔ cannot pause for approval) · **NONE.** A seam whose
> only reach is SESSION does not exist in cron — name that in the plan, or a background path will
> silently skip the model step and report success.
>
> ⭐ **AN UNREACHABLE MODEL IS NOT A CLEAN RESULT.** Measured: when `claude -p` cannot run, stdout is
> EMPTY and exit is 127 — indistinguishable from "the model found nothing," and in cron nobody is
> watching. Map `unreachable · timed-out · rate-limited · malformed · empty` onto the NO-OUTCOME
> member, NEVER onto clean.
>
> **Never reach the model by bare name** — `claude` lives at `~/.local/bin/claude`, not on cron's
> PATH. Use an absolute `CLAUDE_BIN` + the `~/.config/lifehack/claude-oauth-token` pattern, already
> the house standard in any headless runner in this repo.
<!-- MODEL-REACH-RULE-v1 END -->

# Build Rules-of-Engagement Index

> Read by the `/build` skill's **Step 0** gate. Maps **what you're building** → the **binding docs**
> whose rules govern it. `/build` FETCHES these (reads the real files) before building — it never relies
> on memory. **Paths are relative to this repo's root**, wherever it was cloned — resolve them with
> `git rev-parse --show-toplevel`, never against a remembered location.
>
> This index is the **single place to update** when docs move or get verified — the `/build` skill never
> hardcodes doc paths. When the SAD/architecture audit lands, flip the trust tags here; **no skill edit
> needed.**

## Trust legend
- `[VERIFIED <date>]` — pointer **and** currency confirmed as of `<date>`; treat as authoritative.
- `[UNVERIFIED]` — the pointer is correct, but the doc's **currency has NOT been confirmed**. Read it,
  but **verify before relying** on it. (The SAD set is stakeholder-flagged as possibly stale.)
- `[PARTIAL §x]` — only section x confirmed current.

## ALWAYS — every build, regardless of type
- `system/sops/build-sop.md` — hard-won build do's (general + a domain section only when it applies). `[VERIFIED 2026-06-20]`
- `system/sops/architecture-planning-sop.md` — the **Phase → Feature → Task** discipline every plan/build follows. `[VERIFIED 2026-06-20]`
- `system/sops/build-conductor-sop.md` — the **four gears**: when to run the work yourself and when to fan it out to sub-agents, and how to run each. `[VERIFIED 2026-06-22]`

> **Why the conductor SOP is ALWAYS and not a routing row** *(moved here 2026-07-28)*. It used to sit in the
> table below under *"an orchestrated / parallel build."* That was circular — the doc that tells you to
> delegate was reachable only once you had already decided to delegate, and Step 0 classifies by **artifact**
> ("hook? skill? cron?"), never by shape, so an ordinary build never matched the row. Measured 2026-07-28: in
> four `/build` sessions that spawned **zero** sub-agents, the other three docs here were read and this one
> never was. **Every build chooses a gear, including the gear "do it myself" — so every build reads this.**

## FIRST — what KIND of thing are you building?
*(Answer this **before** the routing table.)*

The table below routes by **artifact** — hook, skill, cron. This question routes by **composition**: is
there a model at runtime, is there code at runtime, or both. It answers the more useful question, and the
one the table structurally cannot: **which rules do NOT apply to me right now.** Types 1–3 exist mainly so
a session can rule itself OUT of rules that do not bind it — **the index below only ever ADDS obligations,
never removes them**, and a build carrying rules it does not need is slower and, worse, learns to skim them.

1. **CONVERSATION — no artifact.** A brainstorm, a question, an exploration; nothing is being built.
   **NO build SOP binds.** Not `build-sop.md`, not `architecture-planning-sop.md`, not the conductor.
   Stated explicitly so nobody drags a build gate into a thinking session.
2. **CODE-ONLY PRODUCT — the LLM is scaffolding and is ABSENT at runtime.** You are using Claude to build
   a thing that then runs without a model in it (a spreadsheet whose logic is all formulas; a pure script,
   a hook, a migration). Ordinary engineering rules apply, plus whatever
   domain row matches below. **`system/sops/skill-building-sop.md` does NOT bind** — there is no runtime
   model to keep on-frame, so every law about prose decay, judgment fences, and drift is inert here.
3. **LLM-ONLY PRODUCT — a prose skill with no code behind it.** There is nothing to gate, so most of
   `skill-building-sop.md` PART II (the enforcement toolbox) is **inert — do not manufacture gates for
   something with no mechanical surface.** **LAW 5 (prose decay, `skill-building-sop.md:183`) is the whole
   risk**, and §II.1's **REFRESH** family (`:249` — fresh contexts working off a file spine) is the only
   one of the four families that touches decay. Read those two; skip the rest of PART II.
4. **HYBRID — code and the LLM in one running product, meant to work together.** ⭐ **A SEAM EXISTS.**
   The full `system/sops/skill-building-sop.md` binds, **plus THE CODE/LLM SEAM** — what the handoff between
   the two halves has to be made of. **You do not need to fetch it:** the rule is carried inline, verbatim,
   in `/autoplan` STEP 2 and `/build` Step 0 (a pointer nobody follows is not a rule).
   The evidence behind it lives in the author's own notes and does not ship; the rule above is the
   whole of what binds.
   **This is what almost every skill here is**, so this is the usual answer; the other three are the
   ones worth checking for.

A build can also be multiple types below. This question, though, has exactly one answer.

> ⚠ **Classify the PRODUCT, not the change.** When you are adding one rule or one function to something that
> already exists, the type is a property of **the running thing you are adding to**, never of your edit. A
> purely mechanical gate added to a skill that has a model in it is still a **HYBRID** build — because the
> seam it has to survive is the skill's, not the gate's. Getting this backwards routes you to type 2 and
> tells you the whole `skill-building-sop.md` is inert, which is the exact opposite of the truth.
> *(Added 2026-08-05 from the cold-reader test: a fresh reader given only these files reached the right
> answer but flagged this as the one place it could have gone the wrong way.)*

## Routing table — match what you're building
*(a build can be **multiple types** — match EVERY applicable row)*

| building… | read first (binding) | status |
|---|---|---|
| **a hook** | `system/hook-contract.md` · `system/sops/hook-sop.md` | hook-sop lands in T1.14; hook-contract in Phase 2 |
| **a skill** | `system/sops/skill-building-sop.md` | the LAW 4.2 extract lands in T1.14; the full SOP with `skill-builder` |
| **memory, a doc, or a where-does-this-live decision** | `docs/data-layout.md` · `system/knowledge-altitude.md` | data-layout ✅ here; knowledge-altitude lands in T1.14 |
| **a design, dashboard or interface** | `system/sops/design-process-sop.md` | lands in T1.14 |
| **anything security-touching** | the security wall docs | land in Phase 2 |
| **a Google interaction** | the Google policy docs | land in Phase 2 |
| **an orchestrated / parallel build** | *(promoted to ALWAYS above — every build reads the conductor SOP, not just this one)* | — |

> ## ⚖ ROWS THAT ARE NOT HERE, AND WHY — a named absence beats a silent one
>
> The table this came from carried six more rows, each pointing at a document that **does not exist in
> this repo and is not going to.** A routing row naming a file nobody can open is worse than no row: it
> sends a build looking for rules, finds nothing, and teaches the reader that the table lies.
>
> - **a desk (new)** — a "desk" here is the light subject folder `/ingest` builds, and nothing in this
>   release promotes one to the heavy shape. The SOP and scaffold for that are not part of it.
> - **a cron or scheduled job** — there is no scheduler in this release.
> - **a spreadsheet** — the sheet-building skill is not in this release.
> - **an architecture change** — the architecture docs it named describe a system this repo is not.
>   `docs/data-layout.md` is the equivalent that does ship, and it is in the memory row above.
> - **a mail or corpus reader** — the ingestion doctrine is `/ingest`'s own `SPEC.md`, which ships with
>   that skill and is read from there.
> - **the topic vocabulary** — deliberately never shipped. It is the person's own, and no package hands
>   anyone else's taxonomy of their life.
>
> ⛔ **Do not restore a row without the file.** If a doc lands later, add its row then.

## Catch-all — no row matched
Read `system/sops/build-sop.md`, state plainly what you're building, and **ask which rules apply**
before proceeding. Don't build blind.

<!-- v2 seams (tracked in state/debt-ledger.md → [BUILD-RULES-GATE], 2026-06-20):
  (1) test -f sweep over every path in this index — LOAD-BEARING, not cosmetic: an unresolved path is a
      silent gap. Wire into the Archivist audit walk.
  (2) trust-tag lifecycle: flip [UNVERIFIED]→[VERIFIED <date>] as the SAD rewrite lands; flag stale tags.
  (3) enforcement escalation: only if advisory v1 proves skippable — a UserPromptSubmit/in-skill
      produced-gate. Don't pre-build. -->
