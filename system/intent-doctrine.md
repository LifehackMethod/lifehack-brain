---
topic: [archivist, memory-architecture]
id: system-intent-doctrine
title: Intent Doctrine — every object declares why it exists
record_type: doctrine
desk: root
created_at: 2026-06-12
updated_at: 2026-06-12
status: active
authority: user
---

# Intent Doctrine

> **Purpose of this doc:** state the one law — that every object in ClaudeOps carries its INTENT — so a fresh,
> memoryless session can act correctly on it. Read when **creating, auditing, or placing ANY object** (folder,
> desk, canon, project, skill, hook, cron). Lives LOW (it governs how we *design* the OS, not every chat) — and
> it declares its own purpose right here, eating its own dogfood. **Parent of `system/knowledge-altitude.md`**,
> which is this same law applied to one case: knowledge placement.

## 1. The one law
**Every object in ClaudeOps declares its INTENT, because the LLM is the runtime — and an LLM acts by
*understanding*, not by blind execution.**

Dead code never needs to know why it exists; it runs deterministically regardless. But our runtime is an LLM
that decides what to do *based on what it understands*. So an object's stated intent isn't documentation sitting
beside it — it **is the control surface** that tells the intelligence how to act when it arrives. A purposeless
object is *ambiguous*, so a fresh session **guesses** — and guessing on a load-bearing object is the catastrophic
failure mode. **Intent is executable. The absence of intent is a bug, not a blank.**

## 2. Two flavors — PURPOSE vs DESIRED OUTCOME
One test sorts everything: **"Does this thing ever get *done*?"**

- **Standing / never completes → declare a PURPOSE** — a perpetual function ("I am the repository for X" / "I
  enforce boundary Y"). It is never finished; it just keeps serving.
- **Bounded / completes → declare a DESIRED OUTCOME** — a target end-state ("reach X" / "produce Y"). It has a
  definition-of-done.

This is the same cut as **Areas vs Projects**: a standing thing is an Area (purpose); a bounded thing is a
Project (outcome).

## 3. What each object declares, and where its intent already lives
| Object | Standing / bounded | Declares | Home of its intent |
|---|---|---|---|
| Domain folder / desk | standing | PURPOSE | the folder's `purpose.md` / canon header (indexed by the territory map) |
| Canon home | standing | PURPOSE (its admission `intent`) | `knowledge-altitude.md` + `home-intents.md` |
| Project | bounded | DESIRED OUTCOME | the brief's **FRAME** |
| Skill | standing capability (bounded per run) | a **3-layer intent (§0.5)**: user-outcome+bar · role+autonomy-position · per-run outcome (advised) | top of the `SKILL.md` (identity region) + the `description:` carries Layer 1's caller-visible gist; the per-run outcome rides the §4 anchor. Full rule: ⏳ `system/sops/skill-building-sop.md` §0.5 — lands later in phase 3, with `skill-builder` |
| Hook | standing | PURPOSE — **not just to block, but to re-teach the boundary:** the deny message states WHY + the REDIRECT, so a fresh session *learns the rule* instead of hitting a silent wall | the deny message + `hook-contract.md` WHY/REDIRECT fields |
| Scheduled job | standing schedule (bounded per run) | PURPOSE | the entry that schedules it |

Most of these *already* carry intent (the territory map, brief FRAMEs, hook WHY/REDIRECT, skill descriptions).
This doctrine names the one law they're all instances of — and makes its **absence a flaggable defect**.

## 4. The folder taxonomy this supersedes
- **SUPERSEDED (stale):** "a project = its own folder" (flat per-project folders).
- **THE RULE:** **a folder is a DOMAIN of knowledge — it has a PURPOSE and holds the domain's canon; PROJECTS
  live *inside* a domain folder, each with its own DESIRED OUTCOME.** Domain (purpose) on the outside; projects
  (outcomes) nested within.
- **A CONTAINER ALWAYS TAKES A PURPOSE — never agonize "does it finish?"** A folder is a container of knowledge,
  so its intent is ALWAYS a purpose: *"the home for everything about X."* You never owe a folder a "done-when." The
  DESIRED OUTCOME belongs to a **bounded effort that lives inside** the folder (a build, a deliverable, a goal) — a
  separate layer. **Worked example, which resolves the whole question:** a folder for one ongoing client is a
  *domain folder*, so its intent is a PURPOSE — *"home for everything about working with this client"* — and NOT a
  forced "done-when." Whether the relationship ever "completes" is irrelevant: you label the CONTAINER, not the
  relationship. This dissolves the standing-vs-bounded agonizing for
  every client and every domain folder.
- **KISS for containers:** when the folder's name already says it (a client folder named `meena`), the purpose is
  near-self-evident and a one-liner is plenty — don't bureaucratize. A container's purpose earns extra words ONLY
  when it adds what the name doesn't: the admission bar / what does NOT belong here (the one near-miss).

That's purpose-vs-outcome applied to the file tree. The desks already work this way; the flat root
`state/projects/` pile is the debt. This doctrine sets the **rule**; the actual reorg is gated on the
PARA-migration research, which executes it.

## 5. KISS — intent is never ABSENT, but it's rarely LONG
Don't bureaucratize. An obvious object gets a **one-liner**; the payoff of an explicit intent is highest for the
ambiguous and the load-bearing. The law is "intent is never *missing*," not "intent is always a paragraph."

## 6. How this stays load-bearing (not a doc that gathers dust)
It is pointed-to from the live system three ways (the wiring is its own build phase — tracked in the
archivist-rebuild brief):
1. **PREVENT** — creation templates require a declared intent + cite this doctrine, so a new object can't be born
   without one.
2. **ENFORCE** — the archivist's audit flags any object missing an intent (check **O**, generalized from
   "home-has-no-purpose" to "any object with no declared intent").
3. **ANCHOR** — the archivist charter (`agents/archivist.md`), this project's FRAME, and its plan all cite this
   doctrine, so every archivist action inherits it.

## 7. Self-application
This doctrine governs how we *design and maintain* the OS — not every conversation — so it lives LOW (here), not
at the summit; and it declares its own purpose at the top (the opening blockquote). If we ever want to paste it
into `CLAUDE.md`, that's the doctrine failing its own scope test — don't.
