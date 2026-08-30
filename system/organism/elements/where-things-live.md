---
element: where-things-live
title: "where-things-live — element detail (ground/base altitude)"
subsystem: organism-integrity
altitude: base
record_type: organism-element
maturity_label: PARTIAL·gap (honor)
generated_from:
  - CLAUDE.md (## The shape of the thing — the four-homes summary this element expands)
  - system/organism/manual.md (THE THREE COMPROMISES §1 — the git/Drive lifecycle this element expands)
  - INSTALL.md (the AI Brain setup authority; the no-symlink-into-~/.claude rule)
  - .claude/settings.json (hook registration — the only confirmed hook-registration surface, this repo)
  - system/hook-contract.md (hooks: registration file + the portability statement about absolute paths)
  - system/hooks/guard_write_paths.sh (the live guard over new writes under ~/.claude/skills and /commands)
  - shared/brain_root.py (resolve_brain_root / set_brain_root — how the AI Brain path is found and set)
  - shared/paths.py (scratch_dir — the one deliberate exception that does NOT go to the AI Brain)
  - system/organism/elements/brain.md (the map/manual/element vocabulary this element borrows)
  - system/organism/elements/skill-system.md (the skill discovery chain this element generalizes)
created_at: 2026-08-21
updated_at: 2026-08-21
status: draft
authority: user
---

# where-things-live — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#where-things-live ; ground truth → the live artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds detail of the question every new
> builder hits on day one and the map can only gesture at: *"I just wrote a skill / a hook / a
> helper script — where does it actually go?"*
>
> **One-line:** where a thing you build or write goes is decided by ONE question you already know
> the answer to — **who is this for** — not by a judgment call about taste, cleanliness, or where it
> "feels like" it should live.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### THE QUESTION THAT DECIDES EVERYTHING BELOW: WHO IS THIS FOR?

Before any of the mechanics below — discovery, backup, visibility — there is one question, and the
person building the thing always already knows the answer, because it is their own intent:

**Not** *"would a stranger want this"* (a guess about someone else). **Just:** *who did I build this
for?* That answer sorts into exactly three paths.

---

### PATH 1 — A TOOL JUST FOR ME

Their own skill, agent, command, or script — built to solve their own problem, for their own use.
**This is the everyday path, and most people never leave it.**

It lives **outside this repo entirely**, and which of the two outside homes depends on one further,
purely mechanical fact — see THE MECHANISM below:

- Something the harness must **FIND** on its own (a skill, agent, command, or — with the caveat in
  GATES below — a hook) → **`~/.claude/<kind>/<name>/`**, a real folder.
- Something merely **CALLED by path** (a script, a helper, a library — nothing discovers it, a person
  or another tool invokes it directly) → **the AI Brain**, because the AI Brain is backed up and
  `~/.claude/` is not.

**Because it sits outside the repo it can never conflict with an update and can never accidentally
reach a public push.** A `git pull` has nothing of theirs to touch; a `git push` never sees it, because
it was never `git add`-ed into a tree that gets pushed.

---

### PATH 2 — A TOOL FOR EVERYONE

Something they believe belongs **in** the Harness — a new shipped skill, a fix to an existing one, an
improvement to a hook every install should get.

**Built inside the repo, on a branch, and offered back as a pull request.** This is ordinary open
source and nothing more exotic than that — worth saying plainly precisely because it is ordinary:
people routinely assume contributing to a shared tool is harder or more gated than it is. It is not:
branch, build, open a PR, a maintainer reviews it.

This is the path that grows the shared library, and it is the ONLY path that puts a person's own work
inside the tracked tree that ships to every other student on the next `git pull`.

---

### PATH 3 — MY OWN WHOLE SYSTEM

They do not want to add to this Harness or build beside it — they want to take the *idea* of it and
run their own version.

**Copy it out and run it as their own thing, separately.** A legitimate choice, stated neutrally
rather than discouraged: this is a **fork**, not an extension, and **it will not receive Harness
updates.** That is the one real, factual consequence of the choice — not a warning, just what
"separately" means once it is said out loud.

---

### THE CORRECTED SENTENCE — what this element exists to fix

Before this element, `CLAUDE.md` said: *"everything **they** write lives in the AI Brain."* **That
sentence is true for content and false for machinery.** A skill or agent written into the AI Brain is
invisible to the harness forever — it sits in a folder nothing scans. The corrected reading: content
they write (records, notes, project state — anything nothing has to FIND) lives in the AI Brain;
machinery they write, if the harness has to discover it, cannot live there at all. This element is the
full account of that split; `CLAUDE.md` now carries the corrected one-line version.

---

### THE TWO AXES — whose is it, and who can see it

Two questions get confused constantly, and separating them is the whole contribution of this element:

1. **WHOSE IS IT?** — shared (Path 2 material, belongs to everyone who clones this repo) vs. **yours**
   (Path 1 or Path 3 material, belongs to the person who wrote it).
2. **WHO CAN SEE IT?** — public git (this repo, or a PR branch headed there) · a private git repo ·
   **not in git at all.**

**⭐ The rule that makes this load-bearing: personal things belong in the THIRD visibility tier, not
the second.** A private repo is private **by a setting, not by structure** — one flip of that setting
and it is public, and the history is already there to be exposed. This repo's own `.gitignore` makes
exactly this argument for `.brain-root`: the guard is **absence** — the file is never tracked at all —
**not** `.gitignore` coverage, because a `.gitignore` entry is also just a setting someone can remove.
The same logic gives personal machinery **absence** (`~/.claude/`, never git-initialized, nothing to
flip) rather than a private fork (a setting, one flip from public).

---

### THE FOUR HOMES

| Home | Whose | Who can see it | Survives what |
|---|---|---|---|
| **Shared machinery** | shared | public git (this repo) | replaced wholesale, every `git pull` |
| **Your machinery** | yours | not in git at all | depends on discovery — see below |
| **Your content** | yours | not in git at all | the AI Brain, backed up by Drive |
| **Shared content** | shared | — | **essentially empty. Say so.** A worked example, a shared reference doc, anything that is content but belongs to everyone rather than one person, currently has no real home in this system. That is a documented gap, not a place to file something because no better option was obvious. |

⚠ **A fifth row, added 2026-08-25:** shared machinery can also reach a person through a **plugin
cache** (`~/.claude/plugins/cache/<plugin-name>/...`) rather than a repo clone — whose, "shared"
(the plugin's maintainer writes it, everyone who installs the plugin gets it); who can see it,
whatever the plugin's own distribution channel is, not this repo's public git; survives what,
whatever the plugin's install/update mechanism replaces on each update. This table predates the
capability (see the correction in THE MECHANISM below) and was never extended to it until now.

---

### THE MECHANISM — why DISCOVERY, not preference, decides where "your machinery" goes

This is mechanical, not aesthetic, and it is the heart of the element:

**FOUND BY THE TOOL** (skills, agents, commands — and hooks, with the caveat in GATES below): the
harness looks in exactly two places for these, and only these — the repo, or `~/.claude/<kind>/<name>/`.
~~**There is no third option.**~~ ⚠ **CORRECTED 2026-08-25: there is now a third.** A **plugin cache**
(`~/.claude/plugins/cache/<plugin-name>/...`) is a third place the harness discovers skills from —
verified this session: the installed plugin `lifehack-brain@lifehack-brain`, cached at
`~/.claude/plugins/cache/lifehack-brain/lifehack-brain/`, ~~0.3.1, now serves 34 skills~~ **CORRECTED
2026-08-27** (L.B2 audit, live measurement): the cache is now at version **0.3.13** and serves
**44 skills** under the `lifehack-brain:` prefix — both the version and the count have moved on
since 0.3.1/34 was written, as of 2026-08-25 (it served zero through 0.1.0, 0.2.3 and 0.3.0). This page
predates plugins existing as a Claude Code capability at all — see `intended-map.md`, 831 lines with
zero mentions of "plugin," written before this capability shipped — so its absence here was never a
verdict against plugins, only a documentation gap now closed. Put a skill anywhere else (not the repo,
not `~/.claude/<kind>/<name>/`, not a plugin cache) and it still does not exist as far as the harness is
concerned; it simply never loads. So Path-1 machinery of this kind goes in `~/.claude/<kind>/<name>/`
as a **real folder** — not a preference, one of the places discovery looks — **or is served through the
plugin cache**, which is populated by the plugin's own install/update mechanism, not by hand-placing
files. ⛔ The plugin cache is a THIRD HOME, not a substitute resolution path for this repo's own
skills — nothing here should be read as re-pointing ClaudeOps skills to resolve FROM the plugin cache;
it names a third place the harness looks, full stop.

⭐ **Evidence this already works, verified this session:** `find ~/.claude/skills -maxdepth 1 -type d`
~~returns **12 real (non-symlink) directories**~~ **CORRECTED 2026-08-27** (L.B2 audit, live
`find -mindepth 1 -maxdepth 1 -type d` vs `-type l`): returns **18 real (non-symlink) directories**
plus **12 symlinks** (30 entries total) — the "12" in the struck claim is actually the symlink
count, not the real-directory count; it appears to have swapped the two. Both real dirs and
symlinks live under `~/.claude/skills/` right now, tracked by
neither this repo nor any other clone — proof the FOUND-BY-THE-TOOL / `~/.claude/` pairing is not
theoretical, it is the live pattern for many skills already.

**CALLED BY PATH** (a script, a helper, a library — nothing scans for it, something invokes it
directly by its path): free to live anywhere, and the AI Brain is the better home for one concrete,
non-aesthetic reason: **the AI Brain is backed up (Drive-synced); `~/.claude/` is not.**

---

### THE `~/.claude/` BACKUP GAP — the honest cost, stated rather than hidden

**Discovered machinery cannot be backed up by choosing a better folder.** It has to sit in
`~/.claude/<kind>/<name>/` to load — that is the one and only place the harness's discovery scan
looks — and that folder syncs nowhere. Nothing about this is a defect in the AI Brain or the repo; it
is a structural gap between "where discovery looks" and "where anything is backed up," and no folder
choice closes it.

**And it cannot be closed by a symlink either.** `INSTALL.md` states plainly: *"⛔ Do NOT symlink
anything into `~/.claude/`. Symlinks are Mac-coupled and this has to work on Windows too."* Symlinking
`~/.claude/skills/<name>` out to a Drive-backed folder — the obvious workaround — is exactly the move
that rule forecloses, and for a real reason, not caution for its own sake: a symlink is a filesystem
feature that behaves differently (or not at all) across operating systems, and this product ships to
both.

**⇒ The actionable instruction, since the product does not do this for you today: back up
`~/.claude/` yourself** — by whatever mechanism you already use to back up the rest of your machine.
Saying nothing about this gap, which is what shipped before this element, is the failure this section
exists to correct.

---

### THE DECISION TEST — three questions, in order

1. **Would a stranger want this, and would it work for them?** → Path 2 — **the repo**, on a branch,
   as a PR.
2. **Yours, and something has to FIND it?** → Path 1 — **`~/.claude/<kind>/<name>/`**, a real folder.
3. **Yours, and something CALLS it — or it remembers rather than does?** → Path 1 — **the AI Brain**.
4. ⚠ **Added 2026-08-25 — did someone else's plugin install it?** → the **plugin cache**
   (`~/.claude/plugins/cache/<plugin-name>/...`), a third discovery home alongside 1 and 2 above, not
   a fourth path of your own — you never hand-place a file there; the plugin's own install/update
   mechanism does. "Whose is it" for anything served this way is the plugin maintainer's, not yours,
   even though it now runs from a folder under your own `~/.claude/`.

*(Wanting the whole system as your own, rather than adding to or building beside this one, is Path 3 —
copy it out and run it separately, and it will not receive Harness updates.)*

---

### STORES TOUCHED

| Store | Path | Access | By |
|---|---|---|---|
| This repo (the Harness) | the git clone | READ always; WRITE by a maintainer commit, or by anyone via a branch + PR (Path 2) | everyone (read) · a contributor (branch) · the maintainer (merge) |
| The AI Brain | `.brain-root`-named folder, resolved by `resolve_brain_root()` | READ/WRITE by any tool that resolves the brain root | any tool writing content, or a Path-1 CALLED-BY-PATH script |
| `~/.claude/<kind>/<name>/` | machine-local, per-kind (`skills` / `agents` / `commands`) | WRITE by a person authoring Path-1 machinery; READ by the harness's discovery scan every session | the person; the harness |
| `.claude/settings.json` (this repo) | tracked, wholesale-replaced by `git pull` | WRITE by a maintainer commit only (in the deny-list for the Edit tool) | the maintainer |
| `.claude/settings.local.json` ⛔ gitignored by design — absent from a fresh clone, present only once a person writes one | gitignored, untracked, real, survives `git pull` | WRITE by a person; observed holding only `permissions` in current use | the person |
| Machine temp / scratch | resolved by `scratch_dir()` in `shared/paths.py` | WRITE/READ for throwaway, regenerable output only | any tool |

---

### GATES AND ENFORCEMENT (the honest map)

**Live hook-enforced walls:**

1. **`guard_write_paths.sh`** (PreToolUse Write|Edit) `[hook]` — BLOCKS a *new* skill/command file
   written directly under `~/.claude/skills/` or `~/.claude/commands/`, on the stated grounds that
   such a write creates an untracked orphan. **⚠ Its own redirect message is a live inconsistency this
   element documents rather than resolves:** it tells the blocked session to author the file in a
   different repo's clone (a path under a differently-named clone than this one) and then **symlink**
   `~/.claude/skills/<name>` out to it — the exact move `INSTALL.md` bans two sections away, and not
   the pattern the 12 real, already-working `~/.claude/skills/` directories actually follow. This is a
   tension between a live guard and the documented rule, not a defect either side owns cleanly; it is
   recorded here so nobody "fixes" one side into matching the other's mistake by accident.
2. **`Edit(.claude/settings.json)`** (deny-list entry) `[hook]` — a session cannot quietly re-wire its
   own hook registrations; editing the one confirmed hook-registration surface is a deliberate human
   act.

**Honor-system (prose instruction only; no hook enforces):**

- **Path selection itself** `[honor]` — nothing mechanically stops a person from writing their own
  skill inside the tracked repo tree, or from committing a personal script into it. The three-path
  model is a rule a person follows, not a wall that catches them if they don't.
- **"Build beside" for Path 1, "branch + PR" for Path 2** `[honor]` — same as above; the repo has no
  guard that distinguishes a contribution offered as a PR from a personal file quietly added straight
  to the working tree.
- **`~/.claude/` gets backed up** `[honor]`, and *unbuilt* — there is no mechanism in this system that
  backs up `~/.claude/`. The instruction above ("back it up yourself") is the whole of the current
  answer; nothing here does it for you.

---

### EDGE CASES

1. **Can a hook be Path 1 — a personal hook, living outside the repo?** **Investigated this session,
   and the honest answer is: not with any documented, confirmed mechanism.** `system/hook-contract.md`
   — this repo's own canonical reference for hook creation — names exactly one registration surface:
   the tracked `.claude/settings.json`, using `${CLAUDE_PROJECT_DIR}` so the registration "travels
   with `git pull`," and states an absolute path baked into that file instead "works on exactly one
   computer." ~~On this machine, `~/.claude/settings.json` is itself a **symlink into this repo's**
   `.claude/settings.json` — confirmed this session (`ls -la ~/.claude/settings.json`) — so there is no
   independent user-level settings surface to fall back on either; editing "the user's hooks" and
   editing this repo's tracked file are, on this machine, the same act.~~
   > **⚠ CORRECTED 2026-08-24:** Wrong on both premise and conclusion, measured directly this session.
   > `~/.claude/settings.json` is **not** a symlink into this repo's `.claude/settings.json` — it is a
   > regular file, ~~15,516 bytes~~ **CORRECTED 2026-08-27 (L.B2 audit, live wc -c): now 4,999 bytes**, whose content DIFFERS from the repo's copy (it carries `env` and
   > `hooks` blocks the repo copy lacks). `system/tools/gws-audit.sh` ⛔ private-repo runtime state, not shipped in this public tree documents that the symlink was
   > *deliberately* converted to a real file precisely to stop edits there writing through to the
   > tracked (public-upstream) copy. So the corrected conclusion is the opposite of what was written:
   > **there IS an independent user-level settings surface** — `~/.claude/settings.json` itself — and
   > editing "the user's hooks" there and editing this repo's tracked `.claude/settings.json` are **two
   > separate acts on two separate files**, not the same act. A personal hook registered only in the
   > live `~/.claude/settings.json` would in fact have a real, working (if uncommitted, unshared) home —
   > this element's EDGE CASE 1 "no confirmed home" conclusion should be revisited in light of this, not
   > just its premise.
   A second file,
   `.claude/settings.local.json` (⛔ gitignored by design — absent from a fresh clone), is real and
   does survive a `git pull` — and this repo's own `INSTALL.md` already treats it as legitimately
   "yours" (it is one of the two named
   exceptions in the pre-delete-and-reclone ownership check) — **but `system/hook-contract.md` never
   documents it as a hook-registration surface, and the live copy inspected this session
   (`~/.claude/settings.local.json`) holds only a `permissions` block, no `hooks` key, in current use.**
   **Conclusion, stated plainly rather than papered over: personal hooks have no confirmed legal home
   in this system today.** `settings.local.json` is a plausible candidate — real, untracked, already
   sanctioned for *something* personal — but it is unproven for hooks specifically, and this element
   does not assert a mechanism it has not verified fires.
2. **A Path-1 skill written straight into the repo tree instead of `~/.claude/`.** It works today (the
   harness discovers repo-resident skills too) but is now shared-tree material sitting where Path-2
   material lives — the wrong home for something nobody else asked for, and a future contributor
   reviewing the tree cannot tell, from location alone, that it was never meant to ship.
3. **A Path-2 contribution that never becomes a PR.** A branch that sits unshared is functionally
   Path-1 material wearing Path-2 clothing — fine as a personal fork-in-place, but it does not grow
   the shared library until it is actually offered back.
4. **Something CALLED by path that a person puts in `~/.claude/` instead of the AI Brain.** Still
   works (nothing stops a script living there), but forfeits the one reason the AI Brain was the
   better choice — it is not backed up.
5. ⚠ **ADDED 2026-08-27 (L.B2 audit) — THREE full copies of this system coexist, and this element
   does not account for that.** Confirmed live this session: `~/.claude/skills/ClaudeOps` (this
   repo, the working tree), `~/lifehack-brain` (a second full clone), and the plugin cache
   (`~/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.13`, 44 skills) are all present on
   this one machine simultaneously. THE FOUR HOMES table above treats "shared machinery" as a
   single row reached by one repo clone or one plugin cache — it does not describe what happens
   when a person has more than one live copy of the shared machinery itself at once (which one is
   "the" repo for git-pull/PR purposes, whether the two clones can drift from each other, whether a
   fix landed in one automatically reaches the others). This is a real, live gap in the model this
   element presents, not just an edge case of an individual home.

---

### INTENT / CURRENT-VS-TARGET

**Purpose.** Before this element, the system named two boxes — the repo and the AI Brain — and said
where a person's own *content* goes. It never said where a person's own *machinery* goes, and one
sentence actively said the wrong thing (that everything they write lives in the AI Brain — false for
anything the harness has to discover). `skill-builder` ships on day one and invites exactly this
question; this element is the answer, organized around the one question — **who is this for** — that
a builder always already knows.

**BY DESIGN.** Three paths, not a spectrum: for me stays outside the repo entirely (Path 1); for
everyone goes through a branch and a PR (Path 2); a whole separate system is a fork, stated neutrally
(Path 3). Discovery, not preference, decides where Path-1 *machinery* specifically lands, because it
is the one fact a person cannot choose around — a skill the harness cannot find might as well not
exist.

**Current state → PARTIAL·gap, honor-system.** The mechanism is real (discovery genuinely only checks
two places; 12 live skills prove the `~/.claude/` pattern already works) but almost nothing here is
hook-enforced — path selection, build-beside / branch-and-PR, and the backup instruction are all prose
a person follows or doesn't. The **gap**: hooks have no confirmed personal-registration surface at
all, which is a harder edge than the other three kinds (skills/agents/commands at least have a working
`~/.claude/` pattern) — named honestly rather than invented around.

**TARGET.**
1. **Resolve the `guard_write_paths.sh` redirect-message inconsistency** — either the message is
   updated to point at `~/.claude/<kind>/<name>/` as a real folder (matching the 12 already-live
   skills and the no-symlink rule), or the guard's rationale for blocking is revisited. Not resolved
   here on purpose — a live guard and a documented rule disagreeing is a finding to sit with, not
   something this element should quietly patch.
2. **Determine, by testing rather than reading, whether `.claude/settings.local.json` (⛔ gitignored
   by design — absent from a fresh clone) actually registers a hook** — restart a session with a hook
   entry added there and watch whether it fires.
   Until tested, EDGE CASE 1's "no confirmed home" stands as the honest answer.
3. **A backup mechanism for `~/.claude/`** — currently NOT BUILT; the instruction is "do it yourself."

---

### INTEROP SEAMS

```
READS        brain                 · shares brain.md's git/Drive vocabulary (repo = machinery, AI
                                     Brain = content) and extends it with the third surface,
                                     ~/.claude/, that brain.md does not cover [honor]

READS        skill-system          · the discovery mechanism this element generalizes is
                                     skill-system's own registration chain; REAL folders, not
                                     symlinks, is the confirmed live pattern here — this element
                                     states the rule skill-system only demonstrates for one kind
                                     [honor]

READS        hook-plane             · hook registration is the one kind this element found to have
                                     NO confirmed personal home — the tracked .claude/settings.json
                                     is the only documented registration surface, and it travels by
                                     the same wholesale git pull replacement as every other tracked
                                     file [honor]

COMPLEMENTS  two-machine-residency · that element's parity model is for THIS repo's own tracked
                                     files staying in sync across two machines; this element is
                                     about material that is deliberately NOT tracked at all —
                                     adjacent problem, opposite mechanism [honor]

GUARDED-BY   guard_write_paths.sh  · PreToolUse Write|Edit blocks a NEW file written directly under
                                     ~/.claude/skills/ or ~/.claude/commands/, with a redirect
                                     message that names a different repo's clone path and recommends
                                     symlinking — a real, live inconsistency with the no-symlink rule
                                     this element documents rather than resolves (see EDGE CASE 1 /
                                     GATES) [hook]
```

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the label checker will own this once its manifest covers this element)

- **maturity_label:** PARTIAL·gap (honor)
- **check_detail:** No guard in this repo's fire-test manifest backs any rule specific to this
  element. What was claimed as "REAL and verified this session" here — ~~`~/.claude/settings.json` is
  a symlink into this repo's `.claude/settings.json` (`ls -la`)~~ — is **⚠ CORRECTED 2026-08-24:**
  false, per direct measurement this session: it is a regular file, ~~15,516 bytes~~ **CORRECTED 2026-08-27: 4,999 bytes, live-measured**, with content that
  DIFFERS from the repo's copy (an `env` block and a `hooks` block the repo copy lacks). See EDGE CASE
  1's correction above for the full account, including `system/tools/gws-audit.sh` ⛔ private-repo runtime state, not shipped in this public tree's documentation that
  this was a deliberate symlink-to-real-file conversion. What remains verified: 12 real (non-symlink) directories exist under
  `~/.claude/skills/` (`find -maxdepth 1 -type d`); `~/.claude/settings.local.json` exists, is real
  (not a symlink), and holds only a `permissions` block in current use; `guard_write_paths.sh` blocks
  new writes under `~/.claude/skills/` and `/commands/` (read from source, lines 142–155) with a
  redirect message that names a different repo's clone path. What is `[hook]`: the write-block above,
  and the `Edit(.claude/settings.json)` deny-list entry. What is `[honor]`: which of the three paths a
  person chooses, build-beside / branch-and-PR, and the `~/.claude/` backup instruction — none of
  these are mechanically enforced. The **gap**: no confirmed mechanism exists for a personal hook at
  all. Mixed — a real, working discovery mechanism for skills/agents/commands, one live guard, and an
  unresolved hook gap — ⇒ **PARTIAL·gap (honor)**.
