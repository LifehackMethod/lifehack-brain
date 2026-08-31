# Lifehack Brain

> ### ⚠ If you set this up before August 11, please read this
>
> Two bugs meant `/ingest` could tell you it had saved your work when it hadn't. Both are fixed.
>
> **To find out whether it touched you:** open this folder in Claude and say *"run the notes check"* —
> or run `bash system/tools/check-my-notes.sh`. It reads your files and reports plainly.
> **It changes nothing** — never moves, writes or deletes.
>
> Most of what it finds is notes saved under the wrong folder name, which takes a minute to put right.
> ⛔ **One thing cannot be recovered:** where a pile's notes file didn't exist yet, the notes were
> discarded rather than saved. The check tells you which piles are empty; re-screening them is the only
> way back.
>
> Setting this up for the first time today? None of it affects you — carry on below.

A starting point for an AI that remembers you.

The one thing you set up first is `/ingest`: it takes a pile of your own
material — an old chat export, a stack of documents, notes you've been keeping —
and turns it into a folder structure you and your AI can both work from.
`INSTALL.md` walks you through that one skill, on purpose, and nothing else.

**It is not the only thing that arrives with it, though.** The same clone brings
a working set of other skills — for keeping a project's memory straight
(`/save`, `/read`, `/checkin`), thinking a decision through (`/first-principles`,
`/red-team`, `/research`), and — once you connect your own Google account —
reading and writing your calendar, tasks and spreadsheets under the guards
`INSTALL.md`'s Google section describes. Once you're set up, type `/` in the
chat to see the full current list; that is the one place this can never go
stale, because it is reading the same folder you are.

More will land here over time. When it does, you'll get it with one update.

---

## Two folders, and which is which

This is the only idea you need to hold, and it takes about a minute:

**There are two folders. They are different folders, and they do different jobs.**

    Lifehack Harness/     ← the folder you open in Claude, every session. this IS the tool.
      .brain-root         ← one line: where your AI Brain is. the only link between the two.

    your AI Brain/        ← a separate folder, in your Google Drive. everything YOU write.

The **Harness** arrives by `git clone` and is replaced every time you update. Your
**AI Brain** is never tracked, never committed, never uploaded — it is not in the
repository at all.

⛔ **Always use `main`.** If you ever find yourself on another branch of this repository —
including one named `DO-NOT-USE` — you are looking at maintenance work in progress, not a
release. Switch back with `git checkout main`. Branches on a public repository cannot be
hidden, so if you see one, that is what it means.

**Where each one goes, and how they get connected, is `INSTALL.md`.** That file is the
authority on it and this page deliberately does not repeat it.

**Your AI Brain is the only thing worth backing up** — it is the only part that cannot
be downloaded again. The Harness is always one `git clone` away. Your AI Brain sits in
Google Drive, which keeps versions, so Drive IS the backup. For an extra local copy:

    cp -R "<your AI Brain folder>" ~/brain-backup-$(date +%F)

---

## Setting it up

**Hand `INSTALL.md` to Claude and say "set up my brain."** It does the rest and
checks with you at each step. About ten minutes.

If you would rather see what it will do first, `INSTALL.md` is written to be
read. It is the one place the setup is written down, and this page does not
duplicate it — a second copy is a copy that goes stale.

**It asks you exactly one thing: which Google Drive folder is your AI Brain.** It
finds the candidates, you confirm, and it remembers the answer permanently.

---

## What is in here

    .claude/         ← ours. the commands — this is where Claude looks.
      agents/        ← the specialist readers the skills use
      skills/
        ingest/      ← the one you're walked through in INSTALL.md
        ...          ← plus a working set of others — type `/` once set up to see them
      settings.json  ← wires it all up, and its safety hooks, the moment you clone

    system/          ← ours. the programs that do the sorting.
    shared/          ← ours. the piece that knows where your AI Brain is.

    CLAUDE.md        ← ours. the standing instructions every session opens with.
    .claude/skills/ingest/PLAN-B.md   ← the manual backup for /ingest, if it ever misbehaves
    .gitignore       ← keeps `.brain-root` (and any old `data/`) out of git. do not edit it.

    .brain-root      ← one line, written by setup: the path of YOUR AI Brain,
                       in Google Drive. never committed.

**Everything you write lives in your AI Brain — the folder that last file names, outside
this one entirely.** It is the only thing here that is yours. Everything above it arrived
with the tool and is replaced when you update; your AI Brain is not, and cannot be.

---

## If something goes wrong

Open `.claude/skills/ingest/PLAN-B.md`, drag it into a fresh Claude conversation,
and say *"help me."*

It is a complete backup. It walks your AI through the same process by hand,
without needing the tool to work. You get the same result, it just takes a bit
longer.

**If you suspect some of your own material got tracked by git instead of staying
in your AI Brain** — an export unzipped in the wrong place, files copied in by hand —
run `sh system/tools/untrack-my-stuff.sh` from this folder. It only stops git
from tracking those files; it never deletes anything from your disk. Full detail
is in `INSTALL.md` under **"IF SOMETHING GOES WRONG."**

---

## Getting updates

Ask Claude: *"check if there is an update to my brain and install it."*

Under the hood that is one command, and it is deliberately the gentle one:

    git pull

**A pull replaces the tool files and leaves your AI Brain completely alone**, because
your AI Brain is not in this folder and git never touches it.

> ⛔ **Do not update by deleting this folder and cloning a fresh copy.** It loses the
> `.brain-root` line that connects the Harness to your AI Brain, and any settings you
> have added. `git pull` is the update.

Full detail, including the one-command check to run before any update, is in
`INSTALL.md` under **"Taking an update later."**
