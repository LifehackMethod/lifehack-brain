# The standard steps (0 → 9)

Steps 0–6 run for a mid-session `/save`. Steps 7–9 run for **every** save, including after the
session-close flow has produced its items.

Set the paths from `SKILL.md` first, and open the coverage ledger:

```bash
python3 "$ROOT/system/tools/save/save_step_ledger.py" start
```

---

## Step 0 — Is a project live?

```bash
bash "$ROOT/system/hooks/pm_flag.sh" status
```

- **A path** → route through it. The active brief is the primary destination for live operating
  state: step 7d is promoted from "also sync" to the primary write, using **this** path — do not
  re-infer the slug. Discrete records still route by the tree in `SKILL.md`. After writing, re-arm to
  refresh the TTL.
- **`none`** → run **step 0.4** first. The flag may have expired mid-session even though this session
  *was* tracking a project.

If the flag command errors for any reason, ignore it and carry on. It never blocks a save.

## Step 0.4 — Recover a dropped flag *(only when step 0 said `none`)*

The flag is session-scoped and self-expires, and on a long or multi-day session it can quietly
disappear — after which `/save` sees `none`, assumes there is no project, and **silently skips the
brief sync.** This step is the net for that.

**The source of truth is the arm logbook, not the conversation.** Every real arm or clear appends a
line to a durable append-only log that outlives the flag, so only genuinely-executed arms can be
recovered and an *example* arm command in some documentation can never trip a false one.

```bash
python3 "$ROOT/system/tools/save/pm_flag_recover.py"
```

| it prints | what it means | what you do |
|---|---|---|
| `ARM <tab> path <tab> slug <tab> desk` | armed, never intentionally cleared — the flag expired | **Ask, once:** *"The project flag reads none, but this session armed `<slug>` earlier and never cleared it — the flag likely expired. Sync its brief and re-arm?"* On yes, that slug is the resolved project for the **whole** save; re-arm the flag. |
| `CLEAR` | somebody deliberately said stop tracking | **Nothing.** Never resurrect a deliberately-cleared flag. |
| `NONE` | no project was armed this session | **Nothing** — and never infer a project from the session's content. But do not skip *silently*: at close, say in one line *"ℹ brief sync skipped — no armed project. If you were working a project, re-arm it and re-run."* |

Then: `save_step_ledger.py stamp 0.4`.

## Step 0.5 — Which project? (ask, never guess)

**First: is this even project work?** The slug is a filing label, not a precondition — a save never
blocks on it. The anti-guess rule exists to prevent mis-filing, not to demand a project for everything.

- **System / governance work** (this repo's docs, hooks, skills) → `$DATA/records/<type>/`, titled from
  the content. **Skip the ladder. Do not interrogate for a project.**
- **Genuine project work** → the ladder:

1. **Flag set and the session is consistent with it** → proceed silently.
2. **Flag set but the session looks like different work** → ask: *"the active project is X, but this
   looks like Y — route to Y, split, or stay on X?"*
3. **No flag, one clear registry match** → propose it for a one-tap confirm. Never a silent commit.
4. **No flag, ambiguous or no match** → ask. Show the registry candidates plus "new project".
5. **New project** → confirm the slug and display name, add the row to
   `$DATA/system/project-registry.md` **before** the first save. Registering a slug is **identity
   only, never the frame** — if a brief is needed, that is `project-manager`'s frame gate.
6. **A session spanning several projects** → segment and route each, or ask. Don't force one slug.

The slug resolved here is authoritative for the whole save. Steps 3, 5 and 7 use it and must not
re-infer a different one. Then: `save_step_ledger.py stamp 0.5`.

## Step 1 — What are we saving?

An argument is the description. No argument: take the most recent output. If it is genuinely unclear,
offer one candidate — *"I'll save: X. Correct?"* — but **default to acting, not asking.**

## Step 2 — Resolve the project folder

**Ask the resolver; do not restate the rule.**

```bash
python3 "$ROOT/shared/registry.py" "<slug>"
```

It prints the layout (`folder` or `flat`) and the three paths — brief, records, canon — marking any
that do not exist yet. `NOT-REGISTERED` with rc 3 means there is no such row: **say so and offer to
register one.** Never invent a folder.

Both shapes resolve, always. That dual resolution is the safety invariant — a save works whether or
not a set of notes has been migrated. The rule lives in `shared/registry.py` and nowhere else, so the
four skills that need it cannot drift apart.

## Step 3 — Route

The three-question tree is in `SKILL.md`. Stop at the first yes. Then step 4.

## Step 4 — Deduplicate

Before writing a record, look for an existing file at the destination whose name contains the slug:

```
<destination>/*<slug>*
```

A match: update it if it is clearly the same thing, write a new file if the content is genuinely
distinct. Say which you did. No match: write.

## Step 4.6 — The canon conflict scan (before **any** canon write)

Canon is the vetted record. A silent duplicate there is clutter; a silent contradiction is worse,
because everything downstream is read as though canon were coherent. So before writing **or proposing**
anything bound for a canon file — in addition to step 4's filename check, and reading canon *content*:

```bash
python3 "$ROOT/system/tools/canon_conflict_scan.py" \
  --canon-root "<the target canon dir or file>" --terms "<3-6 key terms>" --title "<title>"
```

**Read the exit code, then the output:**

| rc | means | what you do |
|---|---|---|
| 0 | it read canon and reports | classify (below) |
| 3 | `NO-CANON-YET` — nothing written there yet | proceed, **and say that is why it was clean** |
| 4 | `CANNOT-READ` — canon exists but could not be read | **STOP. Do not write.** An incomplete scan certifies nothing |
| 2 | bad arguments | fix the call |

**Classify the incoming item:**

- **NEW** — nothing in canon covers it → safe to propose.
- **DUPLICATE** — canon already says this → **do not write.** Point at the existing line.
- **CONFLICT** — it contradicts or supersedes an existing line → **STOP.** Put **both** in front of the
  person and let them choose: keep existing / replace / merge / keep both. **Existing canon wins by
  default.** Never auto-resolve.

Surface the verdict — NEW / DUPLICATE / CONFLICT, with the exact file and line — in the panel.

> **★★ This is the feature, not a byproduct.** Surfacing every conflict and redundancy back to a
> person, and never resolving one automatically, is the entire reason this gate exists. A real case:
> an ingest had concluded someone was repositioning *away* from their established primary lane and was
> about to overwrite that canon line. The scan surfaced it; the person corrected it — the established
> lane stays primary, the new register is an **additive secondary layer**. Auto-resolving would have
> written the wrong primary into canon and steered every future session wrong. **Never trade this gate
> for speed.**

## Step 4.5 — The confirm gate (mid-session)

**Canon-gated.** Not a canon candidate → **do not wait.** Write it, show a one-line receipt
(*"Saved X → path."*) and the coverage note. A state edit or a rule append is reversible and also
writes without waiting.

A canon candidate → show it in the same where-first style as the panel (`references/panel.md`): the
bucket first, then a short name and one plain sentence, **no path on the glance**. Name the canon
**altitude**, never the bare word — `CANON · global` / `CANON · project (<name>)` /
`CANON · subject (<area>)` — using the human-readable level, not the file path. Then the pending
banner, and wait. Then: `save_step_ledger.py stamp canon-gate`.

## Step 5 — Write the record

Format: `references/write-formats.md` § Mid-session record. Filename `YYYY-MM-DD-<slug>.md`, slug 2–5
kebab-cased words from the title.

`topic:` takes 1–3 slugs from **`$DATA/memory/topic-vocab.md` — the person's own vocabulary.** Only
slugs already in it. **Never invent one; never edit their vocabulary yourself.** If nothing fits, omit
`topic:` and say so.

Review mode: show destination, frontmatter and a content preview; wait. Default: write, then confirm
*"Written to <path>."*

## Step 5b — Edit state

Default: edit directly, bump `updated_at`, confirm *"Updated <path>."* Review mode: show it first.

## Step 6 — Append a behavioural rule

Distil it to the exact three-part structure — statement, `**Why:**`, `**How to apply:**`. Never omit a
part. Format: `references/write-formats.md` § Behavioural rule.

## Step 6b — Propose canon (propose, never auto-write)

If the session produced a **durable, generalisable** lesson, consider proposing a canon line. **Both**
tests must pass:

1. **The generalisation test** — would this hold for a future *different* case, without the backstory?
2. **The standalone test** — can a completely fresh, zero-context session read this line **alone** and
   fully understand and act on it?

Either fails → it is a record, not canon. Both pass → find the **right level**: the project's own
canon, or a level above it where the statement reliably holds. Then:

- **Run step 4.6 first** and attach its verdict to the proposal. Never propose a canon line without it.
- **Propose it for a one-tap yes.** Never auto-write canon — machine-written canon degrades the system.
  Even in autonomous mode this is the one write that surfaces.
- **Word it to pass the standalone test.** That gate matters far more than length. Precision beats
  brevity; the two failure modes are **cryptic** (worse) and **bloated**.
- On approval, append it and **densify in place** — if it makes an older line redundant or stale,
  merge or prune.
- **Hard operational rules are never canon.** They belong in a hook, where they actually fire.

---

## Step 7 — The journal

**Always journal** a record write, and the session entry when the close flow ran. **Never journal** a
behavioural rule append — that is governance, not chronology. **Judgment call** for a state edit:
journal it only if it materially changes the project's chronology.

Write a full session entry when any of these is true: several failed attempts, an architecture
decision, a pivot, or a session spanning more than one phase. Otherwise the ledger row is enough.

The ledger row — **appended by the tool, which validates it**:

```bash
python3 "$ROOT/system/tools/journal.py" append --slug "<slug>" \
  --event "<what changed AND why>" --to "<artifact path>" [--supersedes "<path>"]
```

It refuses a filename echo and refuses a `supersedes` that is a concept rather than a path, then reads
the line back off disk. The shape it writes:

```
{YYYY-MM-DD} | {desk} | {slug} | {event} | supersedes: {path or —} | → {artifact-path}
```

- **`event`** is one sentence: what changed **and why**. Not a filename echo. Bad: *"Updated state."*
  Good: *"Moved X from tier 1 to tier 2 after the count came back zero; the shortlist priority changes."*
- **`supersedes`** is a path or `—`. Never a concept. `[partial: …]` when only part of the old file is
  invalidated; `[renamed]` when a file moved rather than being superseded.
- **`slug`** is the one resolved at step 0.5. Never re-inferred, never silently `general`.

If the close flow already wrote a session entry, do not write a second one. The ledger row still fires.

## Step 7b — What changed outside the notes folder

Scan the session for files created, modified or deleted **outside `$DATA`** — this repo, the harness
config, anything machine-local — and note them in the journal entry, one line each.

> ⚖ **There is no machine column, and there is no machine log.** The system this came from ran on two
> computers and recorded which one touched what. This one does not: there is one machine, so a
> `machine:` field would be a column that is always the same value, and a reader would eventually
> believe it meant something.

## Step 7c — What the system got wrong

Not what the person wants saved — **how the system performed.** Three questions about this session:

1. What did I miss or fail to find?
2. What did I get wrong that they had to correct?
3. What should I do differently next time?

Categorise: **FRICTION** (errors, broken tools, workarounds, stalls) · **CORRECTION** (facts they had
to fix) · **PREFERENCE** (how they want to work, not yet encoded) · **WORKED** (worth repeating).

One line each — this is a flight recorder, not a narrative. **Do not echo what was saved in the earlier
steps.** Every entry answers *"how could this system be better?"* Nothing meaningful happened → skip
silently. Append a dated block to `$DATA/system/learnings.md`, creating it if it is missing.

## Step 7c.5 — Sweep debt in

Anything left unfinished, deferred, or working-but-not-clean: deferred work, half-done migrations,
workarounds and band-aids, stubbed or untested pieces, stale references after a move — **anything you
said "we should fix that later" about.**

**One home:** `$DATA/state/debt-ledger.md`, under `## Open`, one tight line each with an `[AREA]` tag.
Grep first — update an existing line, never duplicate it. Stamp each with `type:` (`debt` · `project` ·
`decision` · `blocked`) and `state:` (`actionable` · `waiting-external` · `waiting-date` ·
`monitoring` · `parked`); a waiting state needs an `unblock:` tag saying what it waits on. Schema:
`system/schemas/backlog-entry-schema.md`.

**Never silently drop deferred work.** Then: `save_step_ledger.py stamp 7c.5`.

## Step 7c.6 — Sweep resolved items out

7c.5 sweeps debt in; this sweeps it out, so the active list never fills with done items that get
re-read as open.

For everything this session **demonstrably** closed: **delete** the line from `## Open` (move a
one-line dated entry to `## Cleared` only if it is worth the history), and relocate a resolved entry in
`$DATA/state/open-loops.md` to its `## Resolved` section.

**Do not mark ✅ in place.** A ticked item left in the active list is the exact failure this step
exists to prevent — it gets re-investigated and re-done from scratch, which is the single largest
waste there is. **Scope: only what you confidently closed this session.** If unsure, leave it active.

## Step 7d — Sync the brief

**The journal-first gate runs first, hard.** If this save adds any dead end, decision or key number to
the brief, the journal entry capturing it is written **before** the brief is touched. The brief is
overwritten in place; the journal is the only append-only backstop. If step 7 concluded "no journal"
but this step is about to add a dead end — **override, and write the journal entry now.**

**Creating versus updating.** Everything below assumes an existing brief. **If the brief does not
exist, you are creating one, and that carries a gate record-writes do not.** Populate the extractable
spine yourself — the notice, the decision board, the story log, key resources, open loops. But the
**FRAME** — desired outcome, success criteria, constraints, scope edges — is **human-only.** Either
hand off to `project-manager`'s frame gate, or **stub it and label it**: each slot written as your best
guess marked `INFERRED`, the frame marked unconfirmed, and the slots surfaced in one round for
confirm / correct / waive. **Never write a frame slot as settled fact.** Confirming a project's name is
not confirming its definition of done.

**Updating:** refresh where the work stands · move completed items forward · record new decisions,
results and lessons · update next actions and open questions · bump `updated_at`.

**Dead-end capture is the key job — do not skip it.** Scan the whole session for everything tried and
ruled out, and land each one in the STORY LOG (`{date} — tried X → failed because Y → STATUS: killed →
lesson`) plus a one-line ⛔ RULED-OUT entry on the decision board.

**On a long session, or one that may have been compacted, ask:** *"Long session — any dead ends from
earlier I should make sure are captured?"* Early-session material is outside your view; do not assume
the scan is complete.

**Normalise drifted headers while you are here.** Check the brief's headers against the canonical
skeleton (`system/schemas/project-doc-schema.md`). Identify sections **by meaning**, not by regex.
**Headers and structure only — never rewrite section content;** the frame text is human-only and stays
byte-for-byte. Show a tiny before→after for their OK. An already-canonical brief is a silent no-op.

Then: `save_step_ledger.py stamp 7d`.

## Step 7e — Deferred placement

Only for things whose **home needs a decision** — never for laundering an observation into a rule.

- **`content`** — a pointer to the durably-saved file for anything the placement test marked ambiguous.
- **`flag`** — a gap to fix later. In particular a **missing intent**: if this save created a new
  project, file or folder and no purpose was recorded for it, drop a flag.

One small markdown file each, into `$DATA/state/deferred-placement/`, named
`YYYY-MM-DD-<short-slug>.md`:

```yaml
---
kind: content | flag
captured: <YYYY-MM-DD>
project: <slug, or ->
pointer: <path to the durable file>          # for kind: content
placement_hint: <best guess — a GUESS, not a decision>   # optional
---
<one plain line a fresh, no-context session can read>
```

Do not propose a home, do not touch canon. Just drop the pointer. **List what you dropped, then move
on** — never block the save on a reply. Nothing deferred → skip silently, and write no empty files.

## Step 8 — The continuation handoff

**Fill in this form. Emit it. Nothing else.**

```
COLD PICKUP — arm both flags, then read. Do NOT run /checkin.

bash system/hooks/pm_flag.sh arm "<brief path>" "<slug>" "<desk>"
bash system/hooks/plan_flag.sh set "<plan path>"

Then read the brief's §2 (the three rungs + the decision board) and the plan's current
Phase ▸ Feature. That is the whole orientation.

⛔ The brief and plan are hard-won — start from the assumption they're right. ORIENT,
THEN STOP — do NOT start the next step, re-plan, re-scope, or enter plan mode. ⛔ Change
no CONTENT this turn — not the plan's tasks, not the brief's sections. ✅ DO arm the
flags — that is SETUP, not work. Believe a step is wrong? Say it in ONE line and wait.

Re-anchor first: DERIVE the three rungs from the work, then compare against the brief's
§2 block, and state where we stand at 10,000 / 5,000 / ground.
Reading the block back is not a re-anchor.

NEXT (report it, do NOT begin it — wait for my go): <one action. not a sequence.>

LIVE: <the in-flight thinking that is in no file. skip if none.>

WAITING ON YOU: <what needs them. skip if nothing.>

<brief path> · <plan path>
```

**HARD CAP — 200 words, all of the above included. Count it; do not eyeball it:**

```bash
python3 -c "import sys;t=sys.stdin.read();w=len(t.split());print(w,'PASS' if w<=200 else 'OVER — CUT')"
```

**The rules:**

- **Skip any empty slot.** No headers with nothing under them, no "nothing to report". A quiet
  session's handoff is forty words and that is correct.
- **If the brief or the plan holds it, do not write it.** The next session opens both in its first
  action. Where we are (§2) · the desired end state (§1) · what just happened (§4) · the rails
  (✅ LOCKED) · what not to retry (⛔ RULED-OUT) · a list of files saved — all already there. **One
  exception:** something established *this* session that has not landed in the brief yet — carry it,
  and say it needs to land.
- **No backstory, no rationale, no meta-commentary.** Do not explain your own compliance, do not name
  the rule you are following, and do not state a point as prose that you are about to state again as
  an instruction.
- **The three things that belong here and nowhere else:** the **very next action** (one concrete move,
  not a theme) · the **live thinking** not yet written to any file — the working theory, the hunch, the
  thing you were mid-way through weighing, **the single most valuable item here and the one thing a
  brief structurally cannot hold** · **what is waiting on them**.
- **The COLD PICKUP declaration is load-bearing — never strip it as noise.** It tells the next window
  it is opening cold, so that window is *handed* its mode instead of inferring one. This used to be a
  literal `new-session` token on a `/checkin` line; the line is gone but the declaration is not — if a
  session does later run `/checkin` by hand, that skill still reads a `new-session` argument the same
  way.
- ⛔ **Do not put `/checkin` back in this handoff.** Arming two flags and reading §2 is all a cold
  pickup needs, and it costs a fraction of what invoking `/checkin` does — that skill's whole file
  loads on invocation (see `system/hooks/guard_checkin_needs_project.sh`), and it is an END-of-session
  auditor, not an opener. Do not build a separate "resume" skill for this either; the handoff IS the
  mechanism.
- **Over 200 words of load-bearing handoff? Write a FILE and point at it in one line.** Put it in the
  project folder, then emit: `Read this handoff in full before doing anything, then execute it: <abs
  path>`. **The escape hatch is the FILE, never a longer inline handoff.** A working session's handoff
  is expected to reach for the file when it genuinely needs to; a quiet one still fits inline at forty
  words and that is still correct.
  ⛔ **Do not raise the 200-word cap to accommodate this.** It has been tightened before on evidence,
  and each loosening got gamed by a longer handoff sneaking through. ⭐ **The cap protects what is
  printed at the person at session close; the file carries what the next session needs.** Two
  different readers, two different budgets — that is why raising the cap is the wrong fix and the
  file is the right one.
- **No project armed?** There is no brief to point at, so **do carry a compact receipt** — what
  changed, where, and the commit if there is one. Skip the arming block, the rail and the re-anchor.
  Pointing at nothing is not economy, it is a lost handoff.

> **Why a form and not prose.** This spec was once 2,000 words of rationale asking for a short handoff,
> and every real handoff came out long — **a model reading a wall about brevity writes a wall.** The
> instruction was the anti-example. Each earlier cap died to a loophole: "25 lines" (a paragraph is one
> line — 665 words passed) → "400 words, fixed text exempt" (345 passed while the reader got 507) →
> **200 words, nothing exempt.** Do not re-expand this section.

**Then check the plan link.** The handoff emits a plan path, which comes from the brief's `plan:`
frontmatter. Check it: **absent and this session worked a plan** → propose adding it, never overwrite
an existing value · **set but the file does not exist** → surface it; a dead pointer is worse than a
blank · **set but this session worked a different plan** → that is a possible fork; name both, say
which you think is live, let them decide · **set and correct** → use it. **Never guess a plan path into
a brief, and never create a plan file here** — that is `/autoplan`'s job. Plans live at `$DATA/plans/`.
A standalone plan legitimately has no brief and no `plan:` field: say so in one line and move on. Do
not treat it as a defect.

Then: `save_step_ledger.py stamp 8`.

## Step 9 — The coverage note, and the evidence

Print this verbatim, every time, no shortening. At session close it sits at the **foot of the handoff**
(the handoff is the one closer); mid-session it follows the receipt.

> Journal reflects saves via /save and explicitly logged decisions only. In-session pivots, verbal
> agreements, and file changes outside /save are not captured. A clean-looking journal is not a
> complete journal.

That is a **disclaimer**. This is the **evidence**:

```bash
python3 "$ROOT/system/tools/save/save_step_ledger.py" report --findings --session-close
```

**The table is whatever the ledger prints — never a list you recall or compose.** A step that did not
run cannot stamp itself, so it renders `✗ MISSED`. No ledger for the session → `UNKNOWN`, **never
"clean"**: an absent ledger is itself a skipped-step signal.

Then: `save_step_ledger.py stamp 9`.
