# Session close — the curation flow (SC-1 → SC-5)

Runs when `/save` is called bare, or with "session" / "close" / "end" / "wrap", or when a session has
produced a noticeable number of findings. It produces the items; `phases/standard-steps.md` steps 7–9
then write the journal, the ledgers and the handoff.

Set the paths from `SKILL.md` first. Start the coverage ledger before anything else:

```bash
python3 "$ROOT/system/tools/save/save_step_ledger.py" start
```

---

## SC-1 — Extract, with reasoning

**Pull discrete, addressable items out of the raw session record.** Each one anchored to what was
actually said, each carrying its question and its why. This step **structures** the extraction. It does
not summarise.

> **The failure this is built against:** on a long session the model works from its own lazy in-context
> summary and drops detail. The fix is structure, not "think harder". Extraction is a **mechanical
> pull**, never a recall pass.

**(a) Find the raw transcript first.** Sessions are stored as `.jsonl` under the harness's project
transcript directory, one file per session:

```bash
TRANSCRIPT=$(ls "$HOME/.claude/projects/"*"/${CLAUDE_CODE_SESSION_ID}.jsonl" 2>/dev/null | head -1)
```

The variable is `$CLAUDE_CODE_SESSION_ID`. Transcripts sit directly in the project directory — there is
no `conversations/` subdirectory. **If `$TRANSCRIPT` is empty**, fall back to what is in context and
**say so in the journal entry**, so the lossy pass is visible rather than assumed away.

Write what you extract to a working file (`/tmp/save-extract-<date>.md`) so it survives compaction and
can be re-read on a later pass.

**(b) Several targeted passes, not one sweep.** One pass each for:

1. **Decisions** — anything explicitly committed to.
2. **Dead ends** — anything tried and ruled out. The why is required.
3. **Numbers and snapshots** — any amount, count, date, or fast-staling value.
4. **Open questions** — anything unresolved at close.
5. **Suggestions and leanings** — recommendations not yet committed to.
6. **The reasoning** behind each of the above.

**(c) Anchor every item to evidence.** Cite the turn or quote the line. An item that cannot be anchored
**does not get written.** *"I think we discussed X"* is not an anchor; the quote is.

**(d) One completeness pass.** *What is in the transcript that none of those passes caught?* The items
that fall between categories are often the most valuable ones.

**A trivial session** — one quick lookup, no decisions, no dead ends — skips the transcript pull
entirely. Say plainly that nothing warrants persisting, and skip the rest of this flow.

**Output:** a flat list of `{question, why, conclusion}`, one per finding, each anchored. Internal
working material — the person sees it at SC-4.

---

## SC-2 — Tier by durability

Apply this ladder exactly. No improvisation. (Full model: `system/confidence-model.md`.)

```
human-vetted?
  → tier: canon-proposal      the machine never sets vetted:true — this becomes a proposal

a fast-staling value? (a number, a live tally, a this-week datum — expires in days or weeks
                       however well sourced)
  → tier: snapshot
  → a shelf-life is REQUIRED

has at least one explicit source reference?
  → tier: dated-record
  → confidence: CONFIRMED   source is authoritative and direct
                INFERRED    source is indirect, or needs interpretation
                HYPOTHESIS  plausible, source is circumstantial

no source, no vetting, no expiry
  → tier: snapshot
  → confidence: INFERRED or UNKNOWN
```

Then stamp it:

```bash
python3 "$ROOT/system/tools/save/save_step_ledger.py" stamp tier
```

---

## SC-3 — Assign the register

**What KIND of knowledge is this?** Not just hunch-versus-fact — the precise register:

| the test | register |
|---|---|
| the person explicitly decided or committed | `decision` |
| still open — a direction, a hypothesis, a possibility | `possibility` |
| a recommendation or a leaning, not committed to | `suggestion` |
| a trade-off analysis | `pros-cons` — **preserved as the whole weighing, never collapsed to the winning side** |
| tried and ruled out | `dead-end` — the why is required |
| an unresolved thread | `open-question` |
| a derived fact or a synthesis | `finding` — **the default; most items land here** |
| a live number, fast-staling | `snapshot` |
| a prescriptive always-on directive | `rule` — **STOP. Never assign this.** Only a person elevates something to a rule. |

**Default to the softest register that fits.** The machine never auto-assigns `decision` and never
auto-assigns `rule`.

**Once assigned, a register survives every downstream step.** A `possibility` is still a possibility at
the panel, at the gate, and in the file that gets written. It is not promoted by anything except a
person saying so.

**Two `possibility` items on the same topic are a conflict to surface, not a pair to merge.** Show both;
flag the tension; let a person resolve it.

---

## SC-4 — Pre-fill, and the gate

**Present each item with a best-guess placement so the person confirms, corrects or cuts. They are
never asked to author from a blank page — they react to a proposal.**

The panel is **where-first, grouped by destination**: the bucket is a header read once, the items sit
under it. Nobody should have to read to the end of a sentence to find out where something lands.
**Imitate `references/panel.md` exactly** — it carries the bucket order, the canon-altitude labelling,
the lifted-out canon block and the pending banner, with a worked example.

Two tiers:

- **Tier 1, the glance** — buckets as headers, canon first, each item a global number + a short bold
  name + one plain sentence. **No paths.** Canon is always shown even when empty, so *"nothing is
  touching your permanent truths"* is said out loud rather than left silent.
- **Tier 2, the pre-write detail** — shown on their OK, right before writing: the exact destination
  path, create-or-update, the full content, and the machine fields (`tier`, `type`, `confidence`,
  `shelf-life`). Grouped by register here, so each item is reviewed in its true epistemic class.

For any `type: rule` item that has been elevated by a person, print this before writing:

> ⚠ **RULE WARNING** — rules are always-on, generalise to cases they were not written for, accrete
> silently, and are rarely revisited. They steer behaviour invisibly. *Is this really an always-on
> rule, or a strong suggestion — or a finding to re-read in context?* Even on confirm, it writes as a
> **proposal**, never as vetted canon.

**Then ask about debt, once:**

> Any technical debt from this session to clear? (enter to skip)

Not a blocker. A skip is accepted — and **logged in the journal entry**, so the gap is visible.

### Brief compaction — right after the debt check

If **all three** hold: (a) this is a session close, (b) the brief came from **the flag (step 0) or the
logbook recovery (step 0.4)**, and (c) the pad actually has something in it — then run the compaction.
Condition (c) is **a file read, not a judgment**:

```bash
python3 "$ROOT/system/tools/save/pad_archive.py" state "<abs brief>"
```

> ⛔ **(b) IS ABOUT PROVENANCE — WHERE THE BRIEF CAME FROM, NOT WHETHER ONE EXISTS.** Step 0.5's
> ladder can also produce a brief path: it matches your work against the project registry and asks
> you to confirm the name. **That brief is NOT eligible for compaction.** Downstream, an armed brief
> and a registry-matched one are the same string, which is how a window that never armed anything
> reaches this step holding someone else's brief.
>
> **Why the distinction is worth a rule.** Clearing the pad does not delete notes — it *graduates*
> each one into an append-only story log as a settled decision, a dead end, or an open thread. Those
> calls cannot be taken back, and a window that did not do the work cannot make them correctly.
> `/checkin` protects the identical act with a hash proving that window wrote to the pad; this skill
> has no such proof and does not need one, because the honest question here is simply *where did this
> path come from.*
>
> **So: if step 0 returned `none` AND step 0.4 recovered nothing, skip — out loud, naming the reason:**
>
> > ⊘ **compaction SKIPPED** — brief resolved from the registry, not armed for this window. The next
> > `/checkin` will compact it.
>
> A silent skip is indistinguishable from never having looked. *(Found 2026-08-11 by running it: a
> `/save` with no flag and no recovery matched a project from the registry and compacted its brief —
> 6,815 characters archived, graduated and cleared. Nothing was lost, because the archive chain
> verifies and the clear is hash-gated, which is exactly how a missing gate stays invisible.)*

> ⛔ **ASK THE FILE, NEVER THE MODEL.** This used to read *"the scratchpad holds real content"* — a
> call made by eye. A `/save` once wrote a brief, skipped compaction, and printed a clean coverage
> table while the pad held 52,323 characters and was seven days stale.

| verdict | rc | what to do |
|---|---|---|
| `PAD-DIRTY` | 2 | **compact** |
| `PAD-ARCHIVED-UNCLEARED` | 3 | an aborted earlier run — the clear is still owed. Run it **without re-archiving.** |
| `PAD-EMPTY` | 0 | **skip, out loud** — see below |
| `CANNOT-READ` | 4 | **unevaluated, never clean.** Say the pad could not be read. Do not report the brief clean. |

⭐ **On `PAD-EMPTY`, skip out loud — never silently.** Read the newest block's host and timestamp from
`{brief}.pad-archive.md` and print, for the record:

> ⊘ **compaction SKIPPED** — pad already captured by `{host}` at `{ts}` (archive block #{n}).

That line is what makes a duplicated step auditable: it distinguishes *"another window already did
it"* from *"nobody did it"* — the exact distinction the failure above could not make.

**Before compacting: final delta capture.** Scan this session for any decision, outcome or dead end
settled since the pad was last written to that is **not yet in `## 7. SCRATCHPAD`**, and append it —
chronologically, append-only. Then compact, so the pad is complete when it is archived.

**The compaction, in order. It always runs when the three conditions hold — no approval gate, no
"let it ride".**

1. **Read** the brief.
2. **Archive everything first, and prove it.**
   `pad_archive.py archive "<abs brief>"` must exit 0 with a `RECEIPT`. **If it does not → ABORT.**
   Clear nothing, prepend a loud `> ⚠ COMPACTION ABORTED {ts} — archive not confirmed; pad left intact`
   line to the pad, and say so. **No receipt, no clear.** Then `pad_archive.py verify` — a non-zero
   exit means a historical chain break worth surfacing; it does not block this run's clear. Then:
   ```bash
   python3 "$ROOT/system/tools/save/save_step_ledger.py" stamp compact "<abs brief>"
   ```
   That stamp is **caused, not asserted** — it independently re-verifies the chain and its freshness
   and refuses if either fails. A refusal is not optional to skip.
3. **Graduate** each item: a decision or a win → the STORY LOG (append-only) plus a ✅ LOCKED line on
   the decision board · a dead end → the STORY LOG **with its why** plus a ⛔ RULED-OUT line · an open
   thread → OPEN LOOPS plus ❓ OPEN · a resource or path → KEY RESOURCES · pure choreography → drop it,
   it is safe in the archive. **Preserve every dead end. Never rewrite a STORY LOG entry. Never touch
   §0 or §1.**
4. **Journal first** — every keeper hits the journal before or as it lands in the brief.
5. **Clear** the graduated items — only now, and only via `pad_archive.py clear`. Never by hand.
6. **Self-healing diff** — for each item just cleared, check that its substance actually landed in the
   STORY LOG. Match text first, then judge by meaning for the rest (reworded is not missing). **If a
   durable item did not land, write it in now.** Heal it; do not just flag it.
7. **Print the receipt** and record the compaction in the journal entry:

> 📝 **Compaction done** — the scratchpad had {N} items → **Story Log +{S}** · **board** ✅{L}/⛔{K}/❓{J}
> · **dropped {D}** · **self-healed {H}** · **archive #{n}**. To restore: open `{brief}.pad-archive.md`,
> find today's block, copy notes back.

> ⛔ **THE AUDIT DOES NOT LIVE HERE.** This step used to spawn a blind reader to check whether
> compaction lost anything and whether a stranger could resume. Both are **audits**, and neither is
> persistence. `/save` is persistence; `/checkin` is the audit, and it runs the blind read after its
> edits land. Moving it also stops the session that did the sorting from grading its own sorting. **Do
> not re-add a reader here.** The safety net was never the reader — it is the verified archive, which
> refuses to let anything be cleared without a read-back receipt.

> ⚠ **AND THIS PARAGRAPH IS PROSE, WHICH IS A WISH.** It was disobeyed once and nothing noticed: a
> session near its context limit reasoned *"most curation already landed"*, skipped compaction, and
> closed. Its own account: *"I cut the expensive step under context pressure and told myself it wasn't
> needed."* Compaction is the most expensive step here, so it is the first one a squeezed session
> drops. What actually catches it is the ledger: `compact` is mandatory and its stamp is refused
> without a fresh verified archive, so a skip renders **✗ MISSED**. ⇒ **If you are running low on
> context, compact FIRST and cut something else.**

### Then: pause, or don't

**Check the survivors for a canon candidate.** None → do not pause. Go straight to SC-5, write
everything, and close through the single continuation handoff. **One or more → render the panel with
canon lifted out, print the banner, and wait.** (`SKILL.md` → the canon-gated pause.)

**Show the panel once, then write.** The moment they confirm — including a blanket *"save it"* / *"go"*
/ approve-all — go **straight** to SC-5. Do not re-render the panel, do not re-summarise it, do not
re-ask for confirmation you already hold. Near session close the failure mode is over-asking, not
over-writing: when a save is standing and you are unsure, **write.**

---

## SC-5 — Write only the survivors

Write exactly what was confirmed. **Cut items are dropped silently** — no stub, no placeholder.

Formats are in `references/write-formats.md` — read it at this point and write against it:

| tier | goes to | format section |
|---|---|---|
| `dated-record` | the project's `records/`, or `$DATA/records/<type>/` | § Dated record |
| `canon-proposal` | `records/proposals/`, always `vetted: false` | § Canon proposal |
| `snapshot` | as above, **shelf-life required**, never promoted to canon | § Snapshot |
| the session entry | `$DATA/system/journal.md` | § Journal session entry |

Every file carries a `topic:` slug drawn from **the person's own vocabulary**,
`$DATA/memory/topic-vocab.md`. **Use only slugs already in it. Never invent one, and never edit their
vocabulary yourself** — the taxonomy of someone's life is theirs. If nothing fits, omit `topic:` and
say so.

Then continue at `phases/standard-steps.md` step 7.
