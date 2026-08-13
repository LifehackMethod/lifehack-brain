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

Right now it does one thing, and does it well: it takes a pile of your own
material — an old chat export, a stack of documents, notes you've been keeping —
and turns it into a folder structure you and your AI can both work from.

More will land here over time. When it does, you'll get it with one update.

---

## One folder, and what is inside it

This is the only idea you need to hold, and it takes about a minute:

**The tool and your notes live in the same folder. Git only ever touches one of
them.**

    ~/AI Brain/           ← the folder you open. every session. this IS the tool.
      data/               ← everything you write. yours. git ignores it entirely.

**It used to be two separate folders, and it changed on 2026-08-12.** Claude only
finds a tool's commands in the folder you actually open. With the tool sitting one
level down, `/ingest` simply never appeared — and nothing reported an error, which
is what made it expensive to work out. Putting the tool at the top level is the fix.

What keeps your writing out of the repository is therefore no longer *distance* —
it is a single line in `.gitignore` that excludes `data`. Nothing in there is ever
tracked, committed, or uploaded. **Do not remove that line, and do not let anything
talk you into `git add -f data`.**

**Put the folder wherever suits you** — your home folder or Documents is perfect.

**`data` is the only thing here worth backing up** — it is the only part that
cannot be downloaded again. The tool half is always one `git clone` away. Keep it
somewhere that gets backed up however you already back things up, or copy it out
as often as suits you:

    cp -R ~/"AI Brain/data" ~/brain-backup-$(date +%F)

---

## Setting it up

**Hand `INSTALL.md` to Claude and say "set up my brain."** It does the rest and
checks with you at each step. About ten minutes.

If you would rather see what it will do first, `INSTALL.md` is written to be
read. The short version:

1. Make an empty folder outside any cloud folder — `~/AI Brain` is a good name.
2. Open **that** folder in Claude — the Code tab of the desktop app.
3. Get the tool *into* it — note the trailing dot:
   `git clone https://github.com/LifehackMethod/lifehack-brain.git .`
4. Restart Claude, then type `/ingest`.

**The dot in step 3 is not a typo.** It unpacks the tool into the folder you
opened instead of burying it in a subfolder. Leave it off and `/ingest` will not
exist — with no error, which is the annoying part.

**You are not asked where your notes should go.** Setup makes `data` for you,
inside that same folder, and remembers it permanently. There is no decision to
make and nothing to answer.

---

## What is in here

    .claude/         ← ours. the command itself — this is where Claude looks.
      agents/        ← the specialist readers the skill uses
      skills/
        ingest/      ← the one thing it does today
      settings.json  ← wires it all up the moment you clone

    system/          ← ours. the programs that do the sorting.
    shared/          ← ours. the piece that knows where your writing lives.

    CLAUDE.md        ← ours. the standing instructions every session opens with.
    PLAN-B.md        ← the manual backup, if the tool ever misbehaves
    .gitignore       ← the line that keeps `data` out of git. do not edit it.

    data/            ← YOURS. made by setup. ignored by git, so it is never
                       tracked, committed or uploaded.

**Your own notes are in that last one**, and it is the only entry in this list
that is yours. Everything above it arrived with the tool and is replaced when you
update; `data` is not, and cannot be.

---

## If something goes wrong

Open `PLAN-B.md` in the top folder, drag it into a fresh Claude conversation,
and say *"help me."*

It is a complete backup. It walks your AI through the same process by hand,
without needing the tool to work. You get the same result, it just takes a bit
longer.

---

## Getting updates

Ask Claude: *"check if there is an update to my brain and install it."*

Under the hood that is one command, and it is deliberately the gentle one:

    git pull

**A pull replaces the tool files and leaves `data` completely alone**, because git
ignores it and so never touches it.

> ⛔ **Never update by deleting this folder and cloning a fresh copy.** That worked
> safely under the old two-folder layout, where your notes sat outside the
> repository. **They are inside it now, so deleting the folder deletes them too.**
> If you ever truly need a clean copy of the tool, move `data` out first and move it
> back afterwards.

Full detail, including the one-command check to run before any update, is in
`INSTALL.md` under **"Taking an update later."**
