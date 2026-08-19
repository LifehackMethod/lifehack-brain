# Getting an update

**Open the tool folder in Claude and say: *"check if there is an update to my brain and install it."***

That is the whole thing you need to remember. Everything below is for Claude to follow.

---

## What an update can and cannot touch

An update replaces **the tool folder** — this folder, the one with `.claude/` and `system/` in it.

**It cannot reach your AI Brain.** Your AI Brain is a separate folder in your cloud drive; `git pull`
only touches files git tracks, in this folder, and nothing you write is in this folder at all.
`INSTALL.md` is the authority on that split and this file does not restate it.

⛔ **The one rule that follows: update with `git pull`, never by deleting this folder and re-cloning.**
A re-clone throws away the `.brain-root` line — the one thing connecting this folder to your AI Brain —
along with anything else you have added here.

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

## STEP 1 — ⛔ THE CHECK THAT COMES FIRST: where is their AI Brain?

```bash
python3 -c "
import sys; sys.path.insert(0,'shared')
import brain_root, os
src, path = brain_root.resolve_brain_root()
repo = os.path.realpath('.')
print('AI Brain:', path or 'NOT SET', '| source:', src)
print('⛔ INSIDE THIS FOLDER (older install)' if path and os.path.realpath(path).startswith(repo + os.sep) else 'outside this folder — correct')"
```

**`outside this folder — correct` is what a current install prints, and this step must not stop on it.**
The AI Brain is its own folder in their cloud drive; `INSTALL.md` is the authority on that shape, and an
update is not the moment to re-derive it or move anything.

⛔ **`INSIDE THIS FOLDER` means an older install** that kept their writing here. The update itself is
still safe — `git pull` cannot touch what git does not track — but confirm that with:

```bash
git check-ignore -q data && echo "data/ is ignored — a pull cannot touch it" || echo "⛔ STOP — data/ is NOT ignored"
```

⛔ **Only `⛔ STOP` is a real stop.** If `data/` is not ignored, do not pull and do not `git add` anything
— the clone is incomplete or something overwrote `.gitignore`. Say so and stop; `REPAIR.md` owns fixing
it, not this file. On an older install, also say plainly that moving their writing out to its own folder
is a repair worth doing later — never during an update.

If it says **NOT SET**, that is fine for an update. It only means nobody has told this installation
where their AI Brain is yet.

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
> When it comes back, open this exact same folder — the one holding `.claude` and `system`. Until then
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

⛔⛔ **A fresh clone throws away `.brain-root`, which is the only thing connecting this folder to their
AI Brain.** Their writing itself is not in this folder and a re-clone does not reach it — but the
connection has to be remade afterwards, in step 3 below. **If STEP 1 said `INSIDE THIS FOLDER`, this is
an older install and their writing IS at risk** — step 1 below is the only thing allowed to move it,
and it never deletes.

> ⛔⛔ **DO NOT HAND-ROLL THE MOVE-AND-CLONE, AND DO NOT LET THIS FILE KEEP ITS OWN COPY OF ONE.**
> `INSTALL.md` STEP 5 owns that operation. The two-command shape that used to sit here —
> `mv data ../data-keep`, then `git clone` — **stranded a real person's writing.** Run against a folder
> holding both a `data` folder and one ordinary file of their own: `data` moved out, the clone then
> refused a *second* time because that other file was still in the way, the `&&` short-circuited, and
> **there was no restore step in the line to run anyway.** Her writing ended up outside the folder with
> no `data` folder at all. `INSTALL.md` STEP 5 replaced it with a block that moves everything into ONE
> holding folder next door, clones into the folder it has just emptied, and **puts every single thing
> back if anything at all fails.** ⭐ **One authority, not two.** A second copy here is exactly how the
> two drift apart until one of them is quietly the old, dangerous version again — which is what this
> block was.

⚠⚠ **`INSTALL.md` STEP 5 is a DIFFERENT step from this file's own STEP 5 above.** Every reference below
names the file. Do not substitute one for the other.

**1 — Set the old contents aside and clone fresh, using `INSTALL.md` STEP 5.** Open `INSTALL.md`, find
STEP 5, and run the block under *"If `git clone` refuses because the folder is not empty"* — from
inside this folder, exactly as written, without assembling your own version of it. Read its ending back
to them: anything beginning `STOP` or `CLONE FAILED` means the folder was put back as it was found and
**nothing was lost — stop there, do not retry, do not improvise, do not delete anything to "clean up".**
⭐ **The branch to clone lives in that block too, and this file deliberately does not name one** — so
there is exactly one place in the whole repo that has to change when the release branch changes.

**2 — Turn the safety catch back on, using `INSTALL.md` STEP 6.** A fresh clone does not have it: the
check ships inside the folder but git ignores it until `core.hooksPath` points at it. Skipping this
leaves them with an install that looks finished and has no guard on their writing.

**3 — Point the fresh clone back at their AI Brain.** A fresh clone has NO `.brain-root` yet.

```bash
python3 shared/brain_root.py --set "<their AI Brain folder — the same one the old install pointed at>"
python3 shared/brain_root.py
```

⚠ **The second command must answer with `source: repo-pointer` before you trust the install.** If you
would rather not do this by hand, re-drag `INSTALL.md` into the chat and let it do the whole connection
step. Then verify against `TARGET-STATE.md` — all six facts, not just this one.

⚠ **If a `data` folder was among the things set aside, that is an older one-folder install and it is
their writing.** ⛔ **Do not move it back into a `data` folder inside the fresh clone** — that rebuilds
the exact layout this install is moving away from. Leave it where STEP 5 put it, say plainly that it is
safe and nothing was deleted, and treat folding it into a proper AI Brain as a stop-and-ask-for-help
moment. Migrating that shape is not automated, and improvising it is how it gets lost. *(Same rule, and
deliberately the same words, as `INSTALL.md` STEP 5.)*

Then this file's **STEP 5** and **STEP 6** above — prove the new copy runs, then make them restart
Claude. **Leave the set-aside folder next door alone; do not delete it** — it holds everything that was
in here before. Deleting it is a separate decision on a separate day, after they have used the new
install and are happy.

---

## Why there is no `curl | bash` one-liner here

Because you cannot read one before it runs. Every step above is a command you can look at, run on its
own, and stop after. An update that pipes a script from the internet straight into a shell asks for
exactly the trust this system spends its whole design refusing to ask for.
