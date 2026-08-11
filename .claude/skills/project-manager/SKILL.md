---
skill: project-manager
description: "Maintains a living project doc as the single source of truth for long-arc work. Use on \"where are we on\", \"rehydrate\", \"start/update the project doc\", or any multi-session work."
title: "Project Manager — the living project doc"
shape: interactive-workflow
status: active
summary: |
  Maintains one living, AI-readable document per project — the current operating state of the work,
  not a transcript — so any future session can pick the project up cold and continue with minimal
  loss. Confirms the frame with the person before treating the doc as authoritative, keeps a fixed
  spine of sections, and arms the flags that keep the project in view for the rest of the thread.
  Triggered by: /project-manager, "where are we on", "rehydrate", "start a project doc",
  "update the project doc".
triggers: ["project-manager", "where are we on", "rehydrate", "start a project doc", "update the project doc"]
created_at: 2026-06-06
updated_at: 2026-08-11
---

## Intent (§0.5)
**User outcome:** Long-arc work never loses its thread across sessions — one distilled, AI-readable doc
holds a project's whole operating state so any future session picks it up cold, with each piece in the
right slot (FRAME · DECISION BOARD · STORY LOG · KEY RESOURCES · SCRATCHPAD) so nothing precious is
buried or re-proposed once ruled out. **Bar:** *"a new session reads the brief and keeps going —
nothing lost, nothing ruled-out re-suggested."*
**Role:** the project's chief-of-record — an interrogative lead on a build, a faithful scribe
otherwise. It automates all extraction, reconstruction and compression, and mines the person only for
what only they hold — desired outcome, success criteria, constraints — looping the intake gate until
every critical slot is CONFIRMED or WAIVED. It never proceeds on a guess dressed as fact.
**Per-turn anchor:** the active project doc path + slug, so orientation never fades in a long thread.

# Project Manager — the living project doc

A project doc is not a transcript, a summary, or a notes file. It is **the current operating state of
the work**: what has happened, what is true, what is being built or tested now, what is still
uncertain, and what should happen next. The bar is that a new session with no access to this
conversation can read it and carry on.

## Paths (set once, at the top of any run)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"   # this repo
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```

`$DATA` is the person's folder, never this one. Every path below is under it. If it is not set, **stop
and ask** — never fall back to the current directory. Full map: `docs/data-layout.md`.

## Where the doc lives

**A project is a folder, and the folder is named exactly the slug:**

```
$DATA/state/projects/{slug}/brief.md      the doc
$DATA/state/projects/{slug}/records/      this project's own findings
$DATA/state/projects/{slug}/canon/current.md   what this project has settled
```

**HARD — the folder's last path segment MUST equal the slug.** A category above it is fine
(`state/projects/infrastructure/{slug}/`); the leaf is not. Create the folder *as* the slug, never
named after the work — a person must be able to find a project by its slug alone. Audit with
`python3 $ROOT/system/tools/project-manager/check_slug_folder.py`. Depth cap: 3 levels; phases live *in* the brief,
never as folders.

Then register it, so `/read`, `/save` and `/checkin` can resolve the slug — one pipe-separated row
appended to `$DATA/system/project-registry.md`:

```
{desk} | {slug} | {display name} | {status} | {path}
```

`{status}` is `active` · `paused` · `complete` · `split → [a, b]`. `{path}` is the folder relative to
`$DATA`. `{desk}` is `root` unless the person uses desks. **Build the row with the resolver rather
than by hand** — it refuses a folder whose last segment is not the slug, which is the drift above:

```bash
python3 -c "import sys; sys.path.insert(0,'$ROOT/shared'); import registry; \
  print(registry.format_row('<slug>', '<display name>', 'state/projects/<slug>'))"
```

**A brief may also be found as a flat file** — `$DATA/state/briefs/{slug}.md` — because that is what
older notes hold. **Read that shape; never create it.** Both resolve; `python3 "$ROOT/shared/registry.py"
"<slug>"` is the one place that knows how. One brief per slug, for the project's whole life, updated
in place, never dated or duplicated.

Folders are created lazily, on first write. This is the person's own working state — writing here needs
no separate approval. When you do not know the slug, **ask** — never silently infer one.

## Write authority

**JOURNAL-FIRST (hard rule).** The brief is overwritten in place; `$DATA/system/journal.md` is the only
append-only backstop. Before you overwrite the brief with any new dead-end, decision or key number,
that item must **also** be written to the journal. Never let something precious live only in the
mutable brief. If you are updating the doc directly rather than through `/save`, write the journal
entry in the same action — do not defer it.

**Never touch §0 or §1.** The LLM notice and the FRAME are the person's, and changing them needs their
explicit say-so in the session. **The STORY LOG only grows** — an overtaken entry is marked
`superseded-by`, never deleted or rewritten. Compress an entry's prose; never remove it.

## Staying active across the thread

Skill text is injected once and lost at compaction, so this skill arms flags a hook re-reads every
turn. Run these from the session's working directory, as soon as you know the path, slug and desk:

```bash
bash "$ROOT/system/hooks/pm_flag.sh" arm "<abs_doc_path>" "<slug>" "<desk>"
bash "$ROOT/system/hooks/plan_flag.sh" set "<abs_plan_path>"    # only if the doc's `plan:` names one
```

Re-running `arm` moves the pointer when the active project changes. The path must be absolute. The flag
is session-scoped and expires after 12h, so a crashed session leaves no zombie. **Off-switch** —
`bash "$ROOT/system/hooks/pm_flag.sh" clear` when the person says the project is done.

If the brief has no `plan:` value, say so in one line and move on — an honest blank beats a wrong
pointer. Do **not** invent plan-resolution logic here (candidate search, fork detection, offering to
link one); that lives in `/checkin` alone so the two cannot drift apart.

**On a build**, also arm the working-mode anchor so the build spine re-injects every turn:

```bash
bash "$ROOT/system/hooks/skill_anchor.sh" arm project-manager "$ROOT/.claude/skills/project-manager/ANCHOR.md"
```

Then read **`references/build-mode.md`** — the handshake, the scoping round, and how work is handed
off. Clear it when the build is done: `bash "$ROOT/system/hooks/skill_anchor.sh" clear`.

## Frame intake — the human-in-the-loop gate

Some of what the doc must hold is **extractable** (recoverable from the session and the files — what
happened, what was tried, results, current state). Some is **human-only** (the desired outcome, success
criteria, constraints, scope edges) — it lives in their head and often was never said out loud. For the
human-only half, inference is **a guess dressed as a fact**, and every "on track" judgment downstream is
derived from it. So it gets confirmed before the doc is treated as authoritative.

This is not an interrogation up front. **Gather first, then confirm:**

1. **Gather, silently.** Run the reconstruction passes. Answer every extractable slot yourself; form a
   best guess for each human-only slot. Ask nothing yet.
2. **Scorecard.** Rate every frame slot `CONFIRMED` / `INFERRED` / `THIN` / `MISSING`.
3. **Reflect back, in ONE round.** For each slot not already confirmed, show your guess, labelled as a
   guess, and ask them to confirm, correct or fill it. **Never ask cold** — always lead with your best
   guess so they are never starting from a blank page.
4. **Re-score.** New answers may open new gaps.
5. **The gate.** Treat the doc as authoritative only when every **critical** slot — desired outcome /
   definition of done, success criteria, constraints, scope edges — is `CONFIRMED` or explicitly
   `WAIVED`. Otherwise ask again with your updated guess. **Loop until met.**
6. **Waiver.** They may decline any slot ("skip it", "just go"). Mark it `WAIVED`, record it as a
   deliberate gap, proceed without nagging. A blanket "just go" waives all remaining critical slots.
7. **Persist.** Write a **Frame confidence** block into the doc. Once confirmed or waived it sticks —
   a later session reads it and does not re-interrogate settled slots.

The slot definitions and the questions: `references/intake_questions.md`.

## The required spine — fixed headers, organic bodies

**Stamp these headers verbatim, in this order, on every brief you create.** Header drift is what makes
later programmatic passes unsafe. What goes *inside* each one is organic — a troubleshooting doc, a
research doc and a build doc fill them differently.

`## 0. 🛑 LLM NOTICE` → `## 1. FRAME` → `## 2. CURRENT STATE — the DECISION BOARD` → `## 4. STORY LOG`
→ `## 5. OPEN LOOPS / NEXT ACTIONS` → `## 6. KEY RESOURCES / IDS` → `## 7. SCRATCHPAD` →
`## 8. ARTIFACTS` → `## + CHRONICLE POINTER`. (There is no `## 3`; the old don't-retry list is retired
into §2's ruled-out bucket.)

**What belongs in each section, the two blocks that are written word-for-word, and the one rule about
clearing the scratchpad: `references/spine.md`.** Read it before creating a brief or touching §0, §1
or §7. Full schema: `system/schemas/project-doc-schema.md`.

Three things from it that get broken often enough to repeat here:

- **§1 FRAME is human-only and read-only to you.** Changing it needs their explicit say-so in session.
- **§4 STORY LOG only ever grows.** A superseded entry is marked, never deleted or rewritten.
- **Only `/save` clears §7.** And only after the whole pad is archived and read back with a receipt.

**Self-heal on touch:** if a brief exists but has no `## 7. SCRATCHPAD`, add an empty one when you next
touch it. Never leave a re-entered brief without its pad — that is where `/checkin` and the sweep-nudge
put things.

## Working rules

Treat the doc as authoritative project state. If none exists, create it at the routed path. If invoked
midstream, reconstruct in **multiple passes** — do not pretend one pass is enough for a long thread
(`references/reconstruction_protocol.md`). Keep it comprehensive but dense. Distinguish facts,
decisions, tests, results, hypotheses, assumptions and deprecated beliefs — use the confidence labels
in `references/quality_standard.md`. Update whenever durable information appears, not every turn. When
it grows messy, do real maintenance rather than appending forever
(`references/maintenance_rules.md`).

**Avoid:** turning the doc into a transcript · prettiness over density · one rigid template for every
domain · deleting nuance to make it short · treating a hypothesis as a fact · mixing deprecated ideas
with live ones · answering from memory while ignoring the doc · a shallow summary masquerading as a
source of truth · piling on clarifying *detail* questions before a reasonable first pass. *(That last
one is about premature detail. It does not apply to the frame gate — confirming the frame is required,
and is never "too many questions.")*

## The final test

> Could a new session with no history of this conversation rehydrate the project from this document
> and carry on with minimal loss?

If not, the doc is not done.

## What this skill needs outside its own folder

| Needed | Why | Status |
|---|---|---|
| `shared/brain_root.py` | the one resolver for where the person's notes live | ✅ here |
| `system/hooks/pm_flag.sh` · `plan_flag.sh` · `skill_anchor.sh` | the per-turn flags | ✅ here |
| `system/hooks/pm_persist.sh` | re-injects the armed project every turn | ✅ here |
| `system/tools/project-manager/check_slug_folder.py` | audits folder-name/slug drift | ✅ here |
| `system/schemas/project-doc-schema.md` | the full brief schema | ✅ here |
| `system/sops/build-conductor-sop.md` | the build doctrine `ANCHOR.md` points at | ✅ here |
| `system/sops/design-process-sop.md` | design builds only | ✅ here |
| `system/tools/save/pad_archive.py` | archives a section and proves it landed, before anything is cleared | ✅ here |
| `docs/data-layout.md` | where everything under `$DATA` goes | ✅ here |
