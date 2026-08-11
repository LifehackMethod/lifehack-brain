---
skill: save
title: "Save — put what happened where it belongs"
shape: interactive-workflow
status: active
description: "Routes what a session produced to the right home in your notes. Use on \"/save\", or when saving a finding, a decision, or closing a session — it extracts with reasoning, tiers by durability, confirms what matters, and writes only what survives."
summary: |
  One command that persists everything worth keeping from a session — never as one blob, but sorted
  onto the shelf each piece belongs on: records · state · journal · ledger · canon. It writes the
  reversible things on its own authority and shows you what it did. It stops for exactly one thing:
  canon, which is permanent and loads into every future session.
triggers: ["/save", "save this", "save the session", "close the session", "wrap up"]
allowed-tools: [Read, Write, Edit, Glob, Bash]
created_at: 2026-06-27
updated_at: 2026-08-11
---

## Intent (§0.5)
**User outcome:** one low-effort command with an outsized payout — everything worth keeping gets
persisted, and **never as one monolithic blob that rots into uselessness.** Each piece lands on the
shelf it actually belongs on, with special care for the most important and most **dangerous** shelf:
canon, which loads into every future session and can either sharpen it or rot it. **Bar:** *"one
command and everything's shelved where it belongs — nothing lost, and nothing dumped into a blob I'll
never read again."*
**Role — the archivist.** It does almost all the filing for you: every non-canon item goes to its
shelf with no pre-write wait, but it **shows you what it did** — never a silent dump. The one place it
deliberately slows you down is canon. The whole value is minimal housekeeping with the human placed
exactly where the stakes are.

# Save

## Paths (set once, at the top of any run)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"   # this repo
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```

Everything this skill writes lands under `$DATA`. Never this repo, never the current directory. The
full map of what goes where: `docs/data-layout.md`.

## Hard rules

- **Canon is the ONLY mandatory pause.** A save with no proposed canon writes **autonomously** — no
  pre-write wait — and shows a post-write receipt. A save with a canon candidate **stops and waits for
  an explicit yes.** Records, state, the journal and the ledgers are reversible, so blocking on them is
  friction with no safety payoff. Canon is permanent. See the pause section below.
- **Nothing is ever written into canon without the conflict scan** (`system/tools/canon_conflict_scan.py`).
  Every canon-bound item is read against existing canon **content** and tagged NEW / DUPLICATE /
  CONFLICT first. **On a conflict, existing canon wins by default** — never auto-resolved, never
  silently overwritten.
- **A canon item is never a one-liner in a list.** It is lifted out into its own framed block with the
  proposed text **verbatim and in full**, plus the three justifications it has to earn: where it lands,
  why it is permanent, and the conflict verdict. A candidate that cannot fill all three is a record.
  Format: `references/panel.md`.
- **A paused panel always ends with the pending-approval banner** — the very last lines of output,
  verbatim, so a distracted person cannot mistake a pause for a finished save. A completed save never
  prints it; it ends with the coverage note.
- **Journal before brief.** A brief is overwritten in place; the journal is the only append-only
  backstop. Any new dead-end, decision or key number goes to `$DATA/system/journal.md` **first**.
- **No `vetted: true`, ever.** The machine proposes; only a person vets.
- **No silent slug.** Never file under a guessed project. Resolve it or ask.
- **No dedup skip.** Always look for an existing file at the destination before writing a new one.
- **No behavioural rule without its `Why:` and `How to apply:` lines**, and no prose essays pasted
  into `CLAUDE.md`.
- **No deferred work dropped silently.** Anything left unfinished lands in `$DATA/state/debt-ledger.md`.
- **The coverage table is the ledger's print, never a list you compose.** A step that did not run
  cannot stamp itself.

## The canon-gated pause — the one reason this waits

The pause is **risk-tiered, not uniform**. Decided once per save, after the items are known:

- **No canon candidate → autonomous.** Skip the panel-and-wait entirely. Write every survivor, then
  close. Do not print the pending banner; nothing is pending. Mid-session, close with a short
  post-write receipt plus the coverage note. At session close, the receipt is absorbed into the single
  continuation handoff — never a separate "saved X → path" list. **This is what most saves do.**
- **One or more canon candidates → stop and wait.** Show the full panel with each canon item lifted
  out, plus the banner, and wait for an explicit yes.

**A mixed batch pauses as a whole.** The person is already here, so everything is confirmed together —
never a partial auto-write plus a separate canon gate. A blanket *"save it"* / *"go"* approves every
item at its pre-filled placement, canon included.

## Where things go — the routing tree

Ask in order, stop at the first yes.

1. **Does it contain facts, findings, numbers, names, dates, or analysis?** → a **record**.
   - Belongs to an active project → `$DATA/state/projects/<slug>/records/` — where the project can see
     it. Visibility beats tidiness.
   - Belongs to no one project → `$DATA/records/<type>/`.
   - `<type>` is one of six, and the set is closed: `context` · `decisions` · `insights` · `logs` ·
     `proposals` · `research` (`docs/data-layout.md`). Infer it; ask once if genuinely ambiguous.
2. **Is it about the current phase, a blocker, an open item, or the next move?** → **state**.
   - A blocker or open item → `$DATA/state/open-loops.md`.
   - Where things stand → `$DATA/state/current.md`.
3. **Is it a rule about how the assistant should behave?** → the repo's `CLAUDE.md`. Append to the
   section that fits. Distil it to `statement` + `**Why:**` + `**How to apply:**` — never just the
   statement.

**None of the three?** Ask one clarifying question. Never fall back to writing it somewhere plausible.

**And before routing, ask whether the home is even obvious.** Exactly one codified home → place it. If
placing it would require a *decision* — a new project, a synthesised map, genuinely cross-cutting
material — **do not decide in the moment.** Save the content durably first (into the active project's
records if there is one), then note that its home is undecided, and stop. Content is never lost to a
deferred placement.

## How a run goes

| mode | when | what runs |
|---|---|---|
| **mid-session** | `/save` with something to save | `phases/standard-steps.md`, steps 0 → 9 |
| **session close** | `/save` bare, or with "session" / "close" / "end" / "wrap" | `phases/session-close.md` (SC-1 → SC-5) **first**, then standard steps 7 → 9 |
| **review** | the argument contains "review" | the same, showing everything and waiting at each step |
| **deep** | the argument contains "deep" / "ingestion" | the same, plus a full plain-language outline of every record before **any** of them is written |

Load the one phase file you need. Both are written to be run top to bottom.

## Two scripts, and only two

This skill is otherwise Bash-free. It may call exactly these, and nothing else:

```bash
python3 "$ROOT/system/tools/save/pad_archive.py"     archive|verify|state|clear "<abs brief>"
python3 "$ROOT/system/tools/save/save_step_ledger.py" start|stamp|report ...
python3 "$ROOT/system/tools/canon_conflict_scan.py"  --canon-root ... --terms ...
```

Plus the flag readers (`system/hooks/pm_flag.sh status`, `plan_flag.sh path`), which only read.

## What never happens

- No write into this repo. Everything of the person's lives under `$DATA`.
- No `vetted: true`; no canon written before the gate's yes; no canon written without the conflict scan.
- No guessed slug, no guessed desk, no guessed record type — ask instead.
- No brief overwritten with a new dead-end or decision before the journal has it.
- No **register collapse.** A `possibility` stays a possibility, a `suggestion` stays a suggestion, and
  a `pros-cons` is preserved as the **whole weighing** — never flattened to the winning side. The
  machine never promotes a register.
- No auto-assigned `type: rule`. Only a person elevates something to a rule, and even then it writes as
  a proposal.
- No item written that cannot be anchored to something actually said or done. *"I think we discussed
  X"* is not an anchor.
- No snapshot carried past its shelf-life. After it expires the value is UNKNOWN — re-pull it.
- No skipping or shortening the coverage note.
- No self-assessment entry that just repeats what was saved — that step is about how the *system*
  performed, not what the person learned.
- No FRAME authored on a new brief. Identity is not the same as definition-of-done; the frame gate
  belongs to `project-manager`.

## What this skill needs outside its own folder

| Needed | Why | Status |
|---|---|---|
| `shared/brain_root.py` | the one resolver for where the notes live | ✅ here |
| `system/tools/save/pad_archive.py` | archives a section and proves it landed before anything is cleared | ✅ here |
| `system/tools/save/save_step_ledger.py` | records which mandatory steps actually ran | ✅ here |
| `system/tools/canon_conflict_scan.py` | reads canon content before a canon write | ✅ here |
| `system/hooks/pm_flag.sh` · `plan_flag.sh` | which project and plan are live | ✅ here |
| `system/hooks/save_routing_hint.sh` | tells a session where a bare "save this" goes | ✅ here |
| `system/tools/save/pm_flag_recover.py` | recovers a project flag that expired mid-session | lands in T1.8 |
| `system/confidence-model.md` | the tier ladder and the register vocabulary | lands in T1.14 |
| `system/knowledge-altitude.md` | the canon altitudes the panel names | lands in T1.14 |
| `system/schemas/project-doc-schema.md` | the brief's shape, for the sync step | lands in T1.14 |
| `system/schemas/backlog-entry-schema.md` | the debt-ledger tags | lands in T1.14 |
| `docs/data-layout.md` | where everything under `$DATA` goes | ✅ here |
