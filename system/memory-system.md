---
id: system-memory-system
title: Memory — how this system remembers across sessions
record_type: doctrine
created_at: 2026-08-14
updated_at: 2026-08-14
status: active
authority: user
---

# Memory

> How this system remembers you across sessions, and keeps that memory from rotting. Loaded on demand,
> not injected into every session. **Core idea:** a conversation is disposable; anything durable lives
> in a file. This doc is the reasoning behind the split between the kinds of file; the concrete map of
> every path is `docs/data-layout.md` — read that one for WHERE something goes, this one for WHY.

## 1. The one rule everything else rests on

Nothing said in a session survives past it unless it lands in a file. The chat window is scratch space,
not memory. A fact worth having next week gets **written down**, to the one place every tool already
knows to look: the AI Brain, resolved once by `shared/brain_root.py` and never guessed at. (Where the
AI Brain lives and how it is set up is `INSTALL.md`'s subject; this page does not repeat it.) Set once
(`brain_root.py --set <folder>`), it never has to be told again — `/read`, `/save`, `/checkin`, the
archivist and `/ingest` all resolve that same root the same way, so nothing you save can go missing
because two tools disagreed about where the AI Brain is.

## 2. Two questions, answered by where a fact lives

Not every fact deserves the same trust, and not every fact needs to be seen every session. **When does
it load?** — a handful of facts earn a place in every conversation; loading everything floods the
window, loading nothing means starting from zero each time. **How much should it be trusted?** — a
fact a person confirmed is not the same as one a session wrote down in passing and nobody checked.

Answered independently: WHEN by *where a fact lives* (below); HOW MUCH by a `confidence:` field
(`system/confidence-model.md`). A below-canon record can be fresh and low-confidence at once; canon can
be old and still fully trusted, because its trust came from a person, not from age.

### The homes

- **`canon.md`** (top level) and **`<subject>/canon/current.md`** — the few things simply TRUE,
  confirmed by a person, never a session's own guess. The only tier loaded automatically at session
  start (`system/hooks/session_context_loader.sh`), which is why it stays small: every line is paid for
  on every turn, forever. The gate a line has to clear: **can a session with zero other context read it
  and act on it correctly?** If it needs the story behind it, it's a record, not canon.
- **`records/<type>/`** — everything found, decided or kept that hasn't earned the always-loaded tier.
  Six closed types (`context · decisions · insights · logs · proposals · research`), searched by
  `/read`, never auto-loaded. Most of what you know lives here; canon should look small next to it.
- **`state/`** — not facts about the world, facts about where things stand: `current.md`,
  `open-loops.md` (started, not finished), `debt-ledger.md` (knowingly deferred), each project's own
  `brief.md`. Overwritten in place, which is safe only because of the next item.
- **`system/journal.md`** — the one place nothing is overwritten. A brief gets rewritten every session;
  the journal is what makes that safe, because a dead end, a decision, or a number that mattered hits it
  *before* the brief that used to hold it gets replaced.
- **`system/project-registry.md`** — the map from a project's name to where its files actually are, so
  everything else is reachable by name instead of by search.

## 3. The skills that move memory in and out

- **`/read`** — pulls the right things back in: resolves a project through the registry, walks its
  canon branch, loads its journal slice, searches records, and labels what it loads by how much to
  trust it. Never writes.
- **`/save`** — the only way things get written. Routes what a session produced to the shelf it
  belongs on, slowing down for exactly one case: a canon candidate — expensive to get wrong, since it
  loads into every future session.
- **`/checkin`** and **project-manager** — keep a project's own memory honest: reconcile what was
  planned against what happened, leaving the brief sharper than they found it, not just longer.
- **`/ingest`** — the one-time move that turns a pile of existing material into this shape. Everything
  above is what happens to a fact afterward.

## 4. The archivist — memory's only janitor, and it never writes

A memory that only accumulates eventually drowns in itself: files nobody rereads, canon gone quietly
stale, a project folder whose name no longer matches its contents. The archivist
(`.claude/agents/archivist.md`, run via `/archivist-audit`, `/archivist-declutter`,
`/archivist-deepmine`, `/archivist-route`) is the standing check — it walks the folder and reports what
drifted, mines old records for insight nobody promoted, and ranks the right canon home for something
newly approved.

**It has exactly three tools — Read, Grep, Glob — and that's the tool list it was built with, not a
policy it follows.** It cannot write, so it cannot "helpfully" fix a line while it's in there looking.
It reports; a person decides. That matters more here than almost anywhere in the system: a wrong
automatic fix to your own canon or journal isn't a bug you notice and revert — it's a quiet loss you
might not catch for months.

## 5. The loop, and the principles underneath it

`/save` puts what matters into the right home, pausing only for a canon write → `/read` brings the
right slice back at the start of the next session → the archivist periodically walks the folder and
surfaces what's drifted, for a person to rule on → repeat.

- **Conversation is disposable; the filesystem is not.** Nothing carries forward on its own.
- **One remembered root, resolved the same way by everything.** `shared/brain_root.py` refuses rather
  than guesses when it doesn't know.
- **Trust is earned by a person looking at it** — not by age, repetition, or how confident a machine
  sounds. That's what separates canon from everything below it.
- **The always-loaded layer stays small on purpose.** Depth belongs in a file reached for on demand.
- **Nothing gets overwritten before the journal has it.**
- **The auditor proposes; it never fixes.** The one part built to look at everything is, by
  construction, the one part that can't change anything it finds.
