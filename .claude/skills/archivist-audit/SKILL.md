---
skill: archivist-audit
description: "Weekly structural filesystem audit — skeleton, symlinks, metadata, registry, drift, legacy, path/ingest/promise conformance (9 checks). Use on \"/archivist-audit\" (scope=desk/skills/metadata/legacy). Propose-only; writes only the territory map."
shape: interactive-workflow
status: active
topic: [archivist]
summary: Run the structural audit across your notes folder — 9 checks, propose-only.
---

## Intent (§0.5)
**User outcome:** The the notes folder drifts — dead numbered folders, orphaned files, desks missing skeleton pieces, skills out of sync, canon oversized, bare content paths breaking clone-launched sessions. archivist-audit runs the full structural sweep: 12 checks across structure, skill sync, metadata, registry, drift, legacy, stale-systems, territory-map, misplaced files, content-path drift, ingest-conformance, and skill promise-consistency. Output: a timestamped log + an actionable proposals file. **Bar:** "I know the exact structural health of the system — nothing's silently broken or drifting."
**Role:** the faithful weekly inspector — breadth-first, report-only. The opposite of an executor: it reads everything and proposes; the ORCHESTRATING SESSION performs the single managed write (the territory map <notes>/system/canon-purpose-map.md). The archivist subagent itself is pinned to Read/Grep/Glob and cannot write at all. The scope parameter (desk:/skills/metadata/legacy/stale) makes it surgical. The archivist subagent runs at sonnet, fans out read-only checks; nothing executes without explicit user approval. Its job is to make invisible drift visible — not to fix it.

# archivist-audit

Run the Archivist system audit against the notes folder.

## Invocation

```
/archivist-audit
/archivist-audit scope=desk:<subject>
/archivist-audit scope=skills
/archivist-audit scope=metadata
```

## What it does

Delegates to the `archivist` subagent (`.claude/agents/archivist.md`), which is pinned to
`Read, Grep, Glob` — it is structurally incapable of fixing what it finds, which is the point. **Nine
checks survive; three were removed because they audited failure modes that cannot occur here, and
each says so in place rather than being quietly deleted.** The subagent performs:

1. **Structure check** — desk skeleton completeness, shared layer presence
2. ⛔ **REMOVED — skill sync check.** It compared `~/.claude/skills/` against a clone, looking
   for symlink-vs-copy drift. **There is no symlink layer here**: skills are real files in this
   repo and travel by `git pull`. A check for a failure mode that cannot occur reports PASS for
   ever, which is worse than no check — it spends a reader's attention proving nothing.
3. **Metadata compliance** — frontmatter on managed files (post-2026-03-18)
4. **Registry check** — artifacts vs. _registry.md entries; v2 slug→path resolution
5. **Drift detection** — lane files without frontmatter, orphaned files
6. **Legacy detection** — unclassified files predating Stage 1
7. **No-stale-systems check (v2)** — un-migrated briefs, dead numbered-folder system,
   depth-cap violations, oversized canon, dangling stubs, un-retired scaffolding,
   registry/path mismatches, low-cohesion split-candidates, seam-duplication, a deletion
   dependency-gate on every delete proposal, active-projects missing a brief, stale briefs
   (journal newer than brief), and homes with no stated purpose. Keeps post-v2 backfill
   debt visible on every run.
8. **Territory-map regenerate (P6)** — rebuild `<notes>/system/canon-purpose-map.md`: every home (canon · playbook ·
   records-type · state · system · desk-structure) with its purpose + `accepts`, marked STATED/INFERRED. The
   ONE managed file this audit writes — and the ORCHESTRATOR writes it, not the subagent. `.claude/agents/archivist.md`
   pins `tools: Read, Grep, Glob`; it has no Write tool and says so itself. That pinning is deliberate and should stay:
   it is what makes the auditor structurally incapable of touching what it inspects.
9. **Misplaced-file check Q (P6)** — using the map's `accepts`, flag (HIGH-confidence only, grouped,
   propose-only) any file whose content doesn't match its home, with the proposed correct home. Relocation is never automatic: the proposal goes in the queue and a person rules on it.
10. ⛔ **REMOVED — content-path drift check.** It flagged a bare relative content path that should
    have been an absolute Drive path. That was the right check for a system with a code clone, a
    separately-synced content root, and no resolver between them. Here there IS a resolver
    (`shared/brain_root.py`), every skill goes through it, and `docs/data-layout.md` is the list of
    what writes where. **The real question it was asking — does anything write into the repo that
    belongs in your notes? — is worth keeping**, and this script does not answer it: the pre-commit
    guard that refuses to stage `memory/` or `state/` does, along with that layout page. Rebuilding
    it against the resolver is worth doing; porting it as written is not.
11. ⛔ **REMOVED — mail-ingest conformance check.** It checked three named mail-reading skills for
    two hard security invariants. **None of those three skills is in this repo**, and neither is the
    mail plane they read through. The invariant itself still holds everywhere it applies — every
    external read goes through the sanitizers, enforced by `system/hooks/ingest_gate_enforce.sh` and
    its 46 cases — it simply has no mail-ingest skill here to audit.
12. **Skill promise-consistency check (W)** — resolve the clone first, then run the sweep against it:
    ```bash
    ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
    python3 "$ROOT/system/tools/skill_promise_sweep.py" --root "$ROOT"
    ```
    ⛔ `$ROOT` was previously used here without ever being assigned in this file, and the sweep used to
    default `--root` to `$LIFEHACK_ROOT` — the person's NOTES folder, which contains no skills. Between
    them, this check either died on a bad path or reported `0 skills scanned · 0 REFUSED` and exited 0.
    Pass `--root` explicitly so a future default can never re-point it at the notes tree.
    (a thin caller over `skill_promise_check.py`'s own per-file checker — the sweep never reimplements its
    logic). Per skill it cross-checks a curated set of NEGATIVE/BOUNDARY self-promises (e.g. "never touches the
    Sheet," "propose-only, never executes fixes," "never deletes") against that same file's own fenced command
    blocks — the literal instructions a session executes. Three verdicts: **REFUSED** (a real, quoted
    contradiction — flag it, propose the skill fix) is the only actionable finding; **PASS** means the file's
    own promises hold; **CANNOT_EVALUATE** means the file made none of the recognized promises — an honest "no
    signal," never reported as a pass or a problem, rolled into the summary count only. Report-only, like every
    other check.

## Scope parameter

- (none) — full audit, all checks
- `scope=desk:{name}` — restrict to one desk's structure + artifacts
- `scope=skills` — the skill promise-consistency check (12) only
  *(this pointed at check 2 until 2026-08-13; check 2 is one of the three explicitly removed above, so the scope resolved to nothing.)*
- `scope=metadata` — metadata compliance only
- `scope=legacy` — legacy classification only
- `scope=stale` — no-stale-systems (v2 backfill debt) check only

## Output

- Audit log → `<notes>/records/logs/archivist-{YYYY-MM-DD}-audit.md` (`logs/` is one of the six
  record types: *a session, a pass, a phase — what was done*).
- Proposals → `<notes>/records/proposals/archivist-{YYYY-MM-DD}-audit.md`, **only if there is
  something actionable.** An empty proposals file is a false errand.

## Authority

Archivist reads broadly, writes only to its designated output paths.
Proposals require explicit user approval before any action is taken.
Archivist never executes fixes.

## Where this came from

⛔ It replaced a skill called `/steward-audit`, which was kept alongside it for backward
compatibility and does not ship here — there is nothing to be backward-compatible with on a fresh
install.

---

## Where the queue goes, and who acts on it

This skill **proposes and never executes.** Its output is a queue, and the queue lands at:

```
<notes>/records/proposals/archivist-{YYYY-MM-DD}-{what}.md
```

`records/proposals/` is one of the six record types, and it means exactly this: *something proposed,
waiting on a person to rule on it.*

⛔ **There is no `/archivist-review`.** The system this came from had one, and retired it on
2026-07-11 as a dead approve-then-file model — its own scheduled runner records the replacement in
one line: **the scanner just FLAGS, and the next `/save` picks it up.** So nothing here waits for a
review command that does not exist. Write the queue, say where it is, and stop. When you next run
`/save`, the open proposals are there to be dealt with.

## What this skill needs OUTSIDE its own folder

| what | where | status |
|---|---|---|
| the pinned auditor agent | `.claude/agents/archivist.md` | shipped — `tools:` pinned, read-only by construction |
| the notes-root resolver | `shared/brain_root.py` | shipped |
| the layout it audits against | `docs/data-layout.md` | shipped |
| the read guard it checks for | `system/hooks/ingest_gate_enforce.sh` | shipped |

⛔ **Three of the donor's twelve checks were removed, not ported** — see this file's own
notes: they audited failure modes that cannot occur here (a symlink layer that does not
exist, a content-path drift a resolver already prevents, and a mail plane that does not
ship). A check for an impossible failure reports PASS for ever.
