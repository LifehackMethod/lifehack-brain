# Getting an update

**Open the tool folder in Claude and say: *"check if there is an update to my brain and install it."***

That is the whole thing you need to remember. Everything below is for Claude to follow.

---

## What an update can and cannot touch

An update replaces **the tool folder** — this folder, the one with `.claude/` and `system/` in it.

**It cannot reach your notes.** Not because it is careful, but because your notes are not in here. They
live in a completely separate folder you chose at install, and nothing in this process looks at it. That
separation is the whole reason the two folders exist. It is also why the one rule from install still
holds: **this folder is never inside iCloud, Dropbox, Google Drive or OneDrive.** Your notes may be.

**It takes about two minutes** and ends with you quitting Claude and opening it again. That last part is
not optional — see STEP 6.

---

# INSTRUCTIONS FOR CLAUDE

You are updating someone's already-working installation. **The failure you are guarding against is not a
broken update — it is a half-applied one**, where new files land beside old ones and the system loads a
mix of both. That failure is silent. Nothing errors; things just behave oddly in ways nobody can
diagnose later. Every check below exists to make that impossible rather than unlikely.

**Show them what you are doing and what you found.** Do not run all seven steps silently and announce
success at the end.

## STEP 0 — Confirm you are in the right folder, and that it is a clone

```bash
pwd && ls .claude/skills/ingest/SKILL.md && git rev-parse --is-inside-work-tree
```

All three must succeed. If `git rev-parse` fails, this folder was not installed with `git clone` and
there is nothing to pull — go to **THE CLEAN REINSTALL** at the bottom of this file instead.

⛔ **Do not `git init` a folder that is not already a clone.** It produces something that looks like a
repository, has no history and no remote, and cannot be updated ever again.

## STEP 1 — ⛔ THE CHECK THAT COMES FIRST: are their notes inside this folder?

```bash
python3 -c "
import sys; sys.path.insert(0,'shared')
import brain_root, os
src, path = brain_root.resolve_brain_root()
repo = os.path.realpath('.')
print('notes:', path or 'NOT SET', '| source:', src)
print('INSIDE THE REPO' if path and os.path.realpath(path).startswith(repo + os.sep) else 'outside the repo — good')"
```

If it says **INSIDE THE REPO**, stop and tell them. Their notes are somewhere an update is entitled to
overwrite, and the update is not the emergency — the arrangement is. Move the notes out first, re-point
the root with `python3 shared/brain_root.py --set <the new place>`, then come back.

If it says **NOT SET**, that is fine for an update. It only means nobody has told this installation
where the notes live yet.

## STEP 2 — Look before you pull

```bash
git status --porcelain -uall
```

**Blank output means go.** Anything else means this folder is not a clean copy of the tool, and you must
show them what it is before touching it:

- **Modified tracked files** (`M`) — they, or something, edited the tool itself. Show them the list. Ask
  whether those edits matter. If they do, copy them somewhere outside this folder first. `git pull` will
  either refuse or produce a conflict, and neither is something to resolve on their behalf.
- **Untracked files** (`??`) — usually harmless leftovers, but see STEP 4: some of them are exactly the
  stale copies that cause the silent failure.

⚠ **Never run `git checkout .`, `git reset --hard`, or `git clean` to make this output go away.** Each of
those destroys the thing you were supposed to show them first.

## STEP 3 — Show them what is actually coming

```bash
git fetch origin && git log --oneline HEAD..origin/main
```

If that prints nothing, **they are already up to date. Say so and stop** — do not pull, do not restart,
do not perform an update that has no content. An update that changes nothing but tells them it worked
teaches them the check is theatre.

Otherwise read the list and tell them in one or two sentences what changed. Then:

```bash
git pull --ff-only origin main
```

`--ff-only` is deliberate. If the pull cannot be a clean fast-forward, this **refuses** instead of
inventing a merge commit in a folder nobody is going to maintain. A refusal here means STEP 2 found
something you decided to proceed past — go back to it, or use THE CLEAN REINSTALL.

## STEP 4 — ⛔⛔ THE STALE-COPY CHECK, AND THE REASON THIS FILE EXISTS

**`git pull` updates the files git knows about. It does nothing about files git does not know about.**
When a file MOVES between versions, the old path is deleted from the repository — but if a copy of it
exists locally that git never tracked, the pull leaves it exactly where it is. Skills are found by
scanning folders, not by reading a list, so a leftover folder gets loaded like any other. **This has
already happened in a live class.**

Two checks. Both must come back blank.

```bash
git status --porcelain -uall -- .claude system
```

```bash
comm -13 <(git ls-files .claude/skills | cut -d/ -f3 | sort -u) <(ls .claude/skills | sort)
```

The second one lists **skill folders sitting on disk that this version of the tool does not contain**.
Every name it prints is a skill Claude will load and the update did not put there.

**If either prints anything:** show them the list and say plainly what it is — old parts of the tool from
a previous version, which will be loaded alongside the new ones. Then move them out rather than deleting
them, so a mistake is recoverable:

```bash
mkdir -p ../lifehack-brain-leftovers && mv <each path it named> ../lifehack-brain-leftovers/
```

Move them to a folder **beside** this one, never inside it. Then re-run both checks.

## STEP 5 — Prove the new copy runs before promising anything

```bash
ls .claude/skills/ | wc -l && ls .claude/agents/ && python3 -c "import sys; sys.path.insert(0,'shared'); import brain_root; print('resolver OK')"
```

If this repository has a self-test script, run it now and paste the last line. A green check they can see
is worth more than your assurance.

## STEP 6 — ⛔⛔ MAKE THEM RESTART CLAUDE

**Claude loads skills and agents when a session opens. This session opened before the update, so it is
still running the old ones** — including, possibly, a skill file that no longer exists on disk.

Skipping this does not fail loudly. It fails quietly: Claude reads a skill as a *document* instead of
running it, produces something that looks roughly right, and is not the tool at all. Say this:

> **"The update is in. Now quit Claude completely and open it again — the whole app, not a new chat.
> When it comes back, open the `lifehack-brain` folder, that exact folder. Until then it's still running
> the old version. I'll wait."**

**Say "that exact folder" and mean it.** Claude reads the wiring from a `.claude` folder in whatever
folder is open, and it does not look upwards. One level off and nothing loads — no warning, no error.

Then **STOP.**

---

# THE CLEAN REINSTALL — when the checks above are more trouble than starting over

This is not a failure and it costs about five minutes. It is the right answer whenever STEP 2 or STEP 4
turns up a mess, or the folder was never a git clone.

**Their notes are not involved.** They are in a different folder, this does not touch it, and after the
reinstall the new copy is pointed back at them.

```bash
cd ..
mv lifehack-brain lifehack-brain-old
git clone https://github.com/LifehackMethod/lifehack-brain.git
cd lifehack-brain
python3 shared/brain_root.py --set "<their notes folder>"
```

Then STEP 5 and STEP 6 above. **Rename the old folder, do not delete it** — leave it until they have used
the new one and are happy. Deleting it is a separate decision on a separate day.

---

## Why there is no `curl | bash` one-liner here

Because you cannot read one before it runs. Every step above is a command you can look at, run on its
own, and stop after. An update that pipes a script from the internet straight into a shell asks for
exactly the trust this system spends its whole design refusing to ask for.
