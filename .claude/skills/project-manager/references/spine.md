# The spine — the two verbatim blocks, and the one rule about clearing the scratchpad

Loaded when creating a brief, or when something wants to touch §0, §1 or §7. The section order itself
is in `SKILL.md`; this file holds the parts that must be written **word for word** and the one
procedure that has cost real work when improvised.

## §0 — the LLM notice. Write this verbatim, immediately below the frontmatter.

> 🛑 **LLM NOTICE — READ FIRST.** This brief is high-value, human-in-the-loop, VERIFIED knowledge — the
> fine china of the system. Operate with extreme care: prefer append over rewrite, never condense or
> "improve" settled content, and treat the DESIRED OUTCOME (§1) as read-only. When unsure, ASK the
> human — do not edit.

## §1 — the FRAME warning. Write this verbatim, as the first line under the heading.

> ⚠ **HUMAN-IN-THE-LOOP APPROVAL REQUIRED TO CHANGE.** Do NOT override, rewrite, condense, or
> "improve" this desired outcome without EXPLICIT human approval in-session.

Everything below that line in §1 is theirs: the desired outcome, success criteria, constraints, scope
edges, and the Frame confidence block. You write it once, from what they confirmed at the intake gate,
and after that you read it.

## §2 — the decision board

It **opens with the three-altitude read**:

- `▲ 10,000` — §1's desired outcome, restated.
- `▲ 5,000` — the phase, feature or seam you are currently inside.
- `▲ ground` — what was last worked on, dated, with a re-verify-before-acting note.

⭐ **▲10,000 is a restatement, never a position — human-authored, human-only.** A 10,000 line that
re-quotes §1 is *correct*: it is a faithful copy of §1's desired outcome. A session may PRINT it, and
may FLAG it as looking stale against §1, but never rewrites it, appends to it, or dresses it in
position/status language. Position, status and measurement belong at ▲5,000 and ▲ground only. Read the
5,000 line **off the live plan**; do not compose it from memory. ▲ground records what was last worked on
and when — never phrased as an instruction, since the next reader may arrive after it has gone stale, so
it always carries its own date and an explicit re-verify note. A rung with no honest answer says so —
`no larger frame`, `no plan armed` — and never invents one.

Under that, the live status of every granular decision, in three buckets:

- **✅ LOCKED** — in force.
- **⛔ RULED-OUT** — tried and killed. One line, `what → why`, plus a pointer to its story-log entry.
  This bucket is the fast scan that stops a settled question being re-proposed six weeks later.
- **❓ OPEN** — still under discussion.

▲5,000 and ▲ground are machine-maintained, unlike §1 — kept current by compaction off the story log.
▲10,000 is not machine-maintained: it is human territory, present here only to be printed or flagged.

## §4 — the story log

The chronological history of the build, **append-only**, oldest first, one entry per real move:

```
{when} — tried/decided X → outcome → STATUS: locked | superseded-by:<entry> | open → why/lesson
```

It holds the full failure narrative, which is the part that stops the same dead end being walked
twice. **Never drop or rewrite an entry.** An overtaken decision is marked `superseded-by`, not
deleted — the supersession chain is what makes re-litigation visible. You may compress an entry's
prose; you may not remove it. When you are unsure of a status, write `open`. Never guess `locked`.

## §6 — key resources

The live handles needed to **act**: IDs, URLs, tables, tool paths, key file paths. A doc that explains
a project beautifully but hides where its ledger lives is useless on pickup.

## §7 — the scratchpad, and the only way it may ever be cleared

The pad is the dumb capture surface: this session's live working notes, plus the pointer to the active
plan. It is deliberately the *one* scratch home, so a stale or compacted session can find it by "check
the scratchpad" with no filename to remember. Dump into it freely. Anything large becomes a pointer —
a name and a path — never a second copy of the thing.

**Compaction is `/save`'s job and nobody else's.** At session close, `/save` GRADUATES the pad's
content into the STORY LOG (§4) and the DECISION BOARD (§2) and then CLEARS the graduated items —
automatically, with no approval step. There is exactly one precondition, and it is not optional:

1. The **whole** pad is first appended to the append-only `{brief}.pad-archive.md`, and
2. that append is **read back and verified** — `python3 "$ROOT/system/tools/save/pad_archive.py"
   archive "<brief>"` must exit 0 and print a `RECEIPT`.
3. No receipt → **abort**, leave the pad exactly as it was, and write a loud `⚠ COMPACTION ABORTED`
   marker. Fail closed.

After clearing, run the self-healing diff — write back in anything durable that did not land — and an
independent second-pass audit by a different reader than the one that wrote it.

⛔ **Never clear the pad any other way.** Not by hand, not "it's already in the story log", not as part
of a tidy-up.

> **Why it works this way.** Three earlier designs failed in the same direction. A never-wipe rule left
> the pad growing until it was unreadable. An approval gate defaulted to "skip", so in practice the pad
> never compacted at all. A rolling `.bak` lost the middle copy. What makes automatic clearing safe is
> the combination: an append-only verified archive, an append-only story log, an untouched FRAME, and a
> diff that heals what the graduation missed. Remove any one of those four and the automatic clear
> stops being safe.

## Plans

Do not fight the harness's own plan-saving. When a plan is made, let it save where it normally saves,
and record a **link to its path** in §7. The doc is the hub that points at the plan, not a second copy
competing with it. If the plan needs to outlive that location, capture its key bullets in the doc too.
Plans that the person owns live at `$DATA/plans/` — see `docs/data-layout.md`.
