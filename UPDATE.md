# Getting an update

**Open the tool folder in Claude and say: *"check if there is an update to my brain and install it."***

That is the whole thing you need to remember. Everything below is for Claude to follow.

---

## What an update can and cannot touch

An update replaces **the tool folder** — this folder, the one with `.claude/` and `system/` in it.

**It cannot reach your notes.** Not because it is careful, but because `git pull` only touches files git
tracks, and your notes are not tracked. Since 2026-08-12 they live at `data/` **inside this folder**, kept
out of git by one line in `.gitignore` — folder distance used to do that job, and `.gitignore` does it now.
A pull leaves `data/` completely alone.

⛔ **The one rule that follows: update with `git pull`, never by deleting this folder and re-cloning.**
Under the old layout that was survivable, because `data/` sat outside the repository. It does not any
more, so deleting this folder takes your writing with it. If you ever genuinely need a fresh copy, move
`data/` out first and move it back after.

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
print('INSIDE THE REPO (correct since 2026-08-12)' if path and os.path.realpath(path).startswith(repo + os.sep) else 'outside the repo (pre-2026-08-12 install)')"
```

**`INSIDE THE REPO` is the CORRECT answer on a current install, and this step must not stop on it.**
Since the 2026-08-12 layout change the notes live at `data/` inside this folder by design. What you are
confirming is the line below, which is what actually keeps them safe:

```bash
git check-ignore -q data && echo "data/ is ignored — a pull cannot touch it" || echo "⛔ STOP — data/ is NOT ignored"
```

⛔ **Only `⛔ STOP` is a real stop.** If `data/` is not ignored, do not pull and do not `git add` anything
— the clone is incomplete or something overwrote `.gitignore`. Re-clone the tool per INSTALL.md STEP 5,
moving `data/` aside first.

If the resolver says **outside the repo**, this is an install from before 2026-08-12. That still works
and there is nothing to fix during an update; the notes are simply somewhere a pull was never going to
reach either.

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

**Then re-run bootstrap**, even though this is an update, not a first install:

```bash
python3 system/tools/bootstrap.py
```

⭐ **Why an UPDATE runs an INSTALL script (T8.2a, 2026-08-13).** `bootstrap.py` never clobbers
anything that already exists — it only fills in what is missing, which on an update is normally
nothing. But on Windows it also owns one machine-level fix: a `python3.cmd` shim that makes the bare
word `python3` resolve at all, and — as of this task — forces the interpreter into UTF-8 Mode, because
a stock Windows machine otherwise reads files in cp1252 and silently mangles special characters
instead of crashing. **A machine that installed before this fix already has that shim, and `git pull`
does not touch it** — `git pull` only updates files it tracks, and the shim lives outside the repo,
beside the interpreter. Re-running `bootstrap.py` is what reaches it: on Windows it reports
`upgraded` if the shim predates the fix, `already` if it is current, and prints nothing new on
macOS/Linux either way.

## STEP 6 — ⛔⛔ MAKE THEM RESTART CLAUDE

**Claude loads skills and agents when a session opens. This session opened before the update, so it is
still running the old ones** — including, possibly, a skill file that no longer exists on disk.

Skipping this does not fail loudly. It fails quietly: Claude reads a skill as a *document* instead of
running it, produces something that looks roughly right, and is not the tool at all. Say this:

> **"The update is in. Now quit Claude completely and open it again — the whole app, not a new chat.
> When it comes back, open this exact same folder — the one holding `.claude` and `data`. Until then
> it's still running the old version. I'll wait."**

⭐ **Give them the literal path** (`pwd`). Since 2026-08-12 the tool unpacks into the folder they opened,
so there is **no inner `lifehack-brain` folder** to look for. Anyone who installed before that date will
go hunting for one out of habit — say plainly that it is gone and this folder is the tool.

**Say "that exact folder" and mean it.** Claude reads the wiring from a `.claude` folder in whatever
folder is open, and it does not look upwards. One level off and nothing loads — no warning, no error.

Then **STOP.**

---

# THE CLEAN REINSTALL — when the checks above are more trouble than starting over

This is not a failure and it costs about five minutes. It is the right answer whenever STEP 2 or STEP 4
turns up a mess, or the folder was never a git clone.

⛔⛔ **THEIR NOTES ARE INVOLVED NOW, AND THIS IS THE STEP THAT CAN LOSE THEM.** This section used to say
they were in a different folder and this could not touch them. That stopped being true on 2026-08-12:
`data/` lives inside this folder. **Move it out first, and move it back afterwards.** Never delete this
folder while `data/` is still in it.

```bash
# 1 — get their writing out of the way FIRST, beside the folder, never inside it
mv data ../data-keep

# 2 — set the old tool aside (rename, never delete) and clone fresh INTO this same folder
cd .. && mv "$(basename "$OLDPWD")" brain-old
git clone https://github.com/LifehackMethod/lifehack-brain.git "$(basename "$OLDPWD")"
cd "$(basename "$OLDPWD")"

# 3 — put their writing back where the new copy expects it
mv ../data-keep data

# 4 — confirm the resolver already points here, and that git is ignoring it again
python3 shared/brain_root.py
git check-ignore -q data && echo "data/ is ignored — good" || echo "⛔ STOP — do not continue"
```

⭐ **Note the trailing target on the clone.** The tool must land in the folder they open, not in a
`lifehack-brain` subfolder inside it — same rule as INSTALL.md STEP 5's trailing dot. If a `--set` is
needed at all it is `python3 shared/brain_root.py --set "<your AI Brain folder in Google Drive>"` —
the same folder the old install pointed at; `--set` writes the repo's own `.brain-root` pointer. On a
normal reinstall nothing needs re-answering, but ⚠ **a fresh clone has NO `.brain-root` yet** — run the
`--set` above (or re-drag INSTALL.md, which does it for you) and confirm the resolver answers with
`source: repo-pointer` before trusting the install.

Then STEP 5 and STEP 6 above. **Rename the old folder, do not delete it** — leave it until they have used
the new one and are happy. Deleting it is a separate decision on a separate day.

---

## Why there is no `curl | bash` one-liner here

Because you cannot read one before it runs. Every step above is a command you can look at, run on its
own, and stop after. An update that pipes a script from the internet straight into a shell asks for
exactly the trust this system spends its whole design refusing to ask for.
