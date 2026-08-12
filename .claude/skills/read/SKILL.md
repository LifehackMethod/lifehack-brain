---
name: read
title: "Read — pull the right things back in"
shape: utility
status: active
description: "Loads the relevant parts of your notes into the session. Use on \"/read\", or to pick a project or a subject back up — a directed search against what was actually written, never against what the model thinks it remembers."
summary: |
  Finds the right files in your notes and loads them inline, so the session is oriented and that
  orientation survives compaction. It searches live files every time, walks only the canon on the
  branch it needs, labels everything it loads with how much to trust it, and surfaces contradictions
  before content rather than after.
triggers: ["/read", "rehydrate", "pick this back up", "what do we know about"]
allowed-tools: [Read, Glob, Grep, Bash]
created_at: 2026-05-19
updated_at: 2026-08-11
---

## Intent (§0.5)
**User outcome:** a session starts knowing what matters — the right records, the current state of the
project, the canon that applies — each item labelled with how far to trust it, without anyone having to
remember where things live. Below-canon items are labelled sceptically, and conflicts surface *before*
content. **Bar:** *"I ran /read and the session is oriented — I know what we proved versus what to
treat as one data point."*
**Role:** the session's librarian and trust-labeller. It searches the live filesystem, walks only the
canon on the project's own branch (never over-loading adjacent subjects), and wraps everything it loads
in a mechanical sceptical envelope. Autonomous from trigger to close — one clarifying question at most,
and an empty result is always offered, never silent.

# Read

## Paths (set once)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"   # this repo
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```

Everything below is under `$DATA`. The layout: `docs/data-layout.md`.

## Step 0 — Is a project live?

```bash
bash "$ROOT/system/hooks/pm_flag.sh" status
```

- **`none`** → an ordinary read. Go to step 1. (If this read rehydrates a project and they are clearly
  resuming it, you may *offer* to arm it — never arm it silently.)
- **A path** → route through it. Say so: *"a project is active — loading its brief first."* Load that
  brief as the spine, then search as secondary fill-in.

  **Lead with what is ruled out, and with the story.** Before anything else, surface the ⛔ RULED-OUT
  lines and read the STORY LOG as a chronological arc — what was tried, what failed, what worked, how
  it got here — plus KEY RESOURCES and the current next action. **That is the whole point of a
  pickup:** the session knows the history and does not re-suggest ruled-out work or re-litigate settled
  decisions. Then re-arm to refresh the flag's TTL.

If the flag command errors, ignore it and carry on. It never blocks a read.

## Step 0.6 — Resolve the project, and walk its canon branch

Given a slug — from the flag, the argument, or step 1's signals — **ask the resolver:**

```bash
python3 "$ROOT/shared/registry.py" "<slug>"
```

It prints the layout (`folder` or `flat`) and the brief, records and canon paths. `NOT-REGISTERED`
(rc 3) means there is no such project: say so and say where you looked. Both shapes resolve, always —
a half-migrated set of notes never breaks lookup — and the rule lives in `shared/registry.py` and
nowhere else.

**Then walk the branch and load canon along it — lazily, most specific first:**

```bash
# REL = the project folder, relative to $DATA (from the registry's path field)
p="$REL"
while [ -n "$p" ] && [ "$p" != "." ]; do
  [ -f "$DATA/$p/canon/current.md" ] && echo "CANON: $p/canon/current.md"
  case "$p" in */*) p="${p%/*}";; *) p="";; esac
done
```

Read each hit, most specific first. Plus the canon of any slug named in the brief's `scope:`
frontmatter, if it has one.

**Hard limits — minimalism is the gate:**

- **Only canon on the branch.** Skip every off-branch project and subject.
- **Skip every `desks/*/canon/current.md`.** The session loader already put all of them in context at
  SessionStart. Re-reading them double-stuffs the window with a copy of what is already there. The one
  exception is when the loader hit its size ceiling and said so — it names what it dropped; those you
  may pull.
- **This is a mechanical walk you perform**, not a directive in a file and not the model's choice. Each
  canon file is meant to be precise and self-explanatory. If one is bloated or cryptic, load only its
  top section and say it needs tightening.

> **Why the walk is lazy rather than eager.** A parent's canon is loaded by every read that ever walks
> past it — so a fact placed too high is charged to every descendant read, forever. Loading only the
> branch is what makes that cost real instead of theoretical.

## Step 1 — Read the room

Scan the conversation for signals: topic, project, names, dates, entities, the active thread. Fold in
any argument. That is the search brief.

Genuinely no signals and no argument → **ask one question**: *"What should I orient around?"* Wait.
**Never more than one question.**

## Step 2 — Say what you are orienting around, first

Before touching the filesystem, one line at the very top of the reply:

`Orienting around <topic> — loading from <project or subject>.`

It goes first, above any loaded content, so it survives compaction even if what follows gets
compressed.

## Step 2a — A second `/read` this session loads the DELTA, never re-stuffs

**A second invocation brings in what is NEW and skips what is already in the window.** Additive but
deduplicated — not a blind re-read, and not a replacement of what was loaded before. The failure mode
being prevented is **over**-stuffing, so when in doubt, **skip rather than reload.**

**How you know what is loaded — reuse the channel that already exists; do not invent a ledger.** Step
2's orient line and step 6's close line are both placed to survive compaction:

1. Scan this session for every earlier `Orienting around …` line and every earlier close line. **The
   paths they name are already in the window.**
2. Skip those paths. Do not re-read them, do not re-print them.
3. **Say what you skipped and why** — *"skipped 4 already loaded this session (see the earlier read)."*
   A silent skip is indistinguishable from a search that missed them, which is the failure this whole
   skill exists to prevent.
4. **Re-read anyway, deliberately, in exactly two cases:** you have reason to believe the file changed
   on disk this session (you or a helper wrote to it), or the earlier read loaded one section and you
   now need a different part. **Name the reason when you do.**

The SessionStart floor counts as already-loaded too — step 0.6's canon skip is this same rule, applied
to one case.

## Step 2b — Load the journal slice

Chronology before state: what was saved, in what order, and what supersedes what.

**Scope it.** Project and slug both known → a project slice. Project unclear → ask once. Do not infer,
and do not proceed without an answer.

**The journal is one current file plus rotated monthly segments**
(`$DATA/system/journal.md` and `$DATA/system/journal/YYYY-MM.md`). **Search both.** Reading only the
current file silently loses everything older than the last rotation — and it fails *quietly*, which is
the worst shape: the slice comes back short and looks like a quiet project rather than a truncated
search.

```bash
python3 "$ROOT/system/tools/journal.py" slice --slug "<slug>" --limit 20
```

It reads the segments and the current file, oldest first so the arc reads forwards, and prints the
coverage disclaimer at the foot. When you want one specific period, read that segment directly
(`$DATA/system/journal/2026-06.md`).

**Empty slice** → say so: *"No journal entries for `<slug>`. Either nothing has been saved, or this is
new."*

**Gap signal — dates only.** If the newest entry for this project is 7 or more days old:

> Gap signal: the last journal entry for `<slug>` was `<date>`. Worth checking the project's state for
> unrecorded activity.

Do not infer what happened in the gap, and never derive a warning from the *text* of entries. A date
is a prompt to check, not a finding.

**Then print this verbatim, immediately after any journal output. No shortening.**

> Journal reflects saves via /save and explicitly logged decisions only. In-session pivots, verbal
> agreements, and file changes outside /save are not captured. A clean-looking journal is not a
> complete journal.

## Step 3 — Search

### 3.0 — Form the query

**You are the reasoning layer; the search only retrieves.**

- **They typed search terms** → use them. Do not infer or decompose.
- **They pointed at something** (*"where's that from"*, *"verify that"*) → infer the information need
  from that output.

**Default: ONE inferred query.** Three to six words, **anchored on the most distinctive signal** — a
name, a number, a place, a proper noun. One search. On a set of notes this size, splitting a query into
several gives no gain and adds noise.

**Escalate to parallel faceted search only when the topic is genuinely broad or multi-claim** — it
spans several distinct sub-topics, or one query came back thin and clearly missed a thread. Then: **N =
the topic's natural facet count, floor 2, ceiling 6** — not a fixed number. One query drops whole
facets; a fixed count goes blind above it and over-fetches below it. **One entity-anchored query per
facet**, run together, merged and de-duplicated. Anchoring on distinctive nouns rather than generic
ones ("investment", "automation") is what keeps the results clean.

**Never** search a whole sentence verbatim as a phrase, never default to a fixed number of searches,
and never use vague query terms.

### 3.1 — Where to look

**Live files, every time.** Glob by name first, grep full-text as the fallback:

1. **`$DATA/state/projects/**/*.md`** — a project's brief, its records and its canon all live in its
   own folder.
2. **`$DATA/records/**`** — findings that belong to no one project.
3. **`$DATA/state/current.md`** and **`$DATA/state/open-loops.md`** — where things stand, and what is
   unfinished.
4. **`$DATA/desks/*/canon/**/*.md`** — subject canon, **including sub-folders**. Grep the whole tree,
   not just `current.md`: without that, a fact filed in a sub-folder is reachable only if the model
   reads the top file and follows a pointer, which is one un-backstopped path that fails silently.
5. **`$DATA/canon.md`** — the few things true across everything.

> **There is one tier, and it is this one.** An earlier version ran a semantic index first and this
> grep second. The index is not part of this system: it needed an external package fetched at run
> time, which collides with the rule that external code is quarantined and reviewed before it runs, and
> it was only ever as fresh as its last reindex — so it could not answer *"did I just save that?"*,
> which is the most common reason to run this at all. **Do not add an adapter for it.** Live files,
> every time.

**State currency check.** If you load a state file, compare its `updated_at` against the newest
relevant record. Records newer → flag it inline: *"state may be behind — the most recent record is from
`<date>`."*

## Step 3.9 — Load the right ALTITUDE, not just the right topic

A read that returns the right *subject* at the wrong *depth* is still a bad read: it either buries the
session in detail it cannot use, or hands it a summary when it needed specifics.

- **Start at the highest altitude that answers the question, and descend only if it does not.** Canon
  and a brief's frame are the tip; records are the base. Do not open the base when the tip answers it.
- **A pointer beats a paste.** If a file is large and only its existence or location matters to the
  task at hand, load the pointer — path plus one line — not the body. **Say that you did.**
- **Match the depth to the ask.** *"Where does X live?"* is a tip question. *"Why did X fail on the
  14th?"* is a base question. Answering either at the wrong level costs the window twice: once loading
  it, once reasoning past it.
- **When you descend, say why** — *"canon answered the what; pulling the record for the when."*

⚠ Altitude is not relevance. Step 4 ranks *which* files; this ranks *how deep*. A perfectly relevant
file loaded at the wrong depth still costs the session.

## Step 4 — Rank before loading

Rank candidates against the search brief and load the strongest first. Load more only if the strong
ones do not cover it.

When you cut, be explicit: *"found N more — skipping X and Y as lower signal. Say 'load more' to pull
them in."* Never quietly blow up the window on marginal material.

## Step 5 — Load and present

Read the ranked files. Present content inline, structured by source:

```
## <path>
<content>
```

Large file → load the sections that matter and **say what you skipped**: *"skipped `<section>` — not
relevant to `<topic>`."*

**Contradictions surface BEFORE the content, never after:**

`Conflict: <A> says X · <B>, from <date>, says Y. Loading both — flag for resolution.`

## Step 5b — The sceptical envelope

A **mechanical labelling pass** over everything step 5 loaded. Not a vibe check, not an essay: one line
per item is the norm, and you flag only what deviates.

**A — which layer.**

| layer | how you know | what you do |
|---|---|---|
| **A · canon** | the file is under a `canon/` path, or carries `vetted: true` | load it trusted; no label. It has already passed a human gate. |
| **B · below canon** | anywhere else, without `vetted: true` | label it **`[source-of-record]`** — default sceptical, evidence not verdict |
| **C · snapshot** | frontmatter has `tier: snapshot` or a `shelf-life` | label **`[snapshot — re-pull before relying on it]`**, and if the shelf-life has passed, append **`[EXPIRED — treat as UNKNOWN until re-pulled]`** |

Label only substantive knowledge items — never the orient line, the coverage disclaimer, or tool
output.

**B — corroboration, a count and nothing more.** For each Layer B item, count the combined entries in
`source:` and `source_refs:`. **0 or 1** → append `⚑ single-source — treat as one data point`. **2 or
more** → no flag. If a `confidence:` field is present, surface it inline. This is a count read straight
off the frontmatter, not a judgment.

**C — contradictions across the whole loaded set.** If two or more loaded items assert different values
for the same named fact:

`⚑ CONFLICT: <A> says X · <B> says Y — loading both, flag for resolution.`

**Never silently pick one. Never synthesise a middle value.** Surface it and load both.

**Keep the output lean** — one inline annotation per flagged item, not a separate section:

```
## records/insights/2026-06-14-runway.md  [source-of-record]  ⚑ single-source — treat as one data point  |  confidence: INFERRED
```

**If everything loaded is canon and nothing is flagged, print no envelope at all.** A clean read does
not need a wall of labels.

## Step 6 — Close

One closing line: what was loaded, what was skipped, and whether anything looked stale or contradicted.
This is the forward anchor for the rest of the session.

**Name the PATHS, not just the count.** Step 2a reads this line on a second `/read` to work out the
delta — a close that says *"loaded 6 files"* gives the next invocation nothing to deduplicate against,
and the window gets re-stuffed. Paths, explicitly.

## Found nothing

Report exactly **where** you searched and **what for**, then offer one specific next move — *"should I
search `<broader term>` / the journal segments / a different subject?"* **Never go silent.**

## What never happens

- No orient line at the bottom. Always the top.
- No loading files without ranking them first.
- No sprawling across every subject regardless of signal.
- No loading stale state without flagging it.
- No contradiction presented without calling it out.
- No silence on an empty result.
- No more than one clarifying question.
- **No returning pointers instead of content** when the content is what was asked for — load the actual
  material. (A deliberate pointer under step 3.9, announced as such, is a different thing.)
- No journal-derived summary without the coverage disclaimer, verbatim.
- No silent inference of which project when it is ambiguous. Ask.
- No gap warning derived from the text of entries. Dates only.
- **No writing.** This skill reads. It arms a flag and it loads files; it changes nothing.

## What this skill needs outside its own folder

| Needed | Why | Status |
|---|---|---|
| `shared/brain_root.py` | the one resolver for where the notes live | ✅ here |
| `system/hooks/pm_flag.sh` | which project is live | ✅ here |
| `system/hooks/session_context_loader.sh` | puts subject canon in context at session start — the reason step 0.6 skips it | ✅ here |
| `docs/data-layout.md` | where everything under `$DATA` lives | ✅ here |
| `system/schemas/project-doc-schema.md` | the brief's section names, for the pickup read | ✅ here |
| `system/knowledge-altitude.md` | the doctrine behind step 3.9 | ✅ here |
| `system/confidence-model.md` | the tiers and confidence vocabulary step 5b reads | ✅ here |
