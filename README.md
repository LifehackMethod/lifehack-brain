# Lifehack Brain

> ### ⚠ If you set this up before August 11, please read this
>
> Two bugs meant `/ingest` could tell you it had saved your work when it hadn't. Both are fixed.
>
> **To find out whether it touched you:** open this folder in Claude and say *"run the notes check"* —
> or run `bash lifehack-brain/system/tools/check-my-notes.sh`. It reads your files and reports plainly.
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

## Two folders, and which is which

This is the only idea you need to hold, and it takes about a minute:

**The tool goes in one folder. Your notes go in a different one.**

    ~/lifehack-brain/     ← the tool. ours. replaced whole on every update.
    ~/My Notes/           ← everything you write. yours. never touched.

They are separate on purpose. An update replaces the tool folder completely, so
nothing you wrote can be caught up in it — there is nothing of yours in there to
overwrite.

**One rule about where the tool folder goes: keep it out of your cloud folder.**
Not inside Google Drive, not inside Dropbox, not inside OneDrive, not inside
iCloud Drive. Anywhere else is fine — your home folder is perfect.

> **Why, in one paragraph.** The tool folder is a git repository, and git works
> by constantly making and deleting hundreds of small files as it goes. Cloud
> sync tools watch for exactly that and try to upload each one, mid-operation.
> The two fight, and it does not show up as a clear error — it shows up as a
> folder that quietly corrupts, or an update that half-applies. Every hour spent
> on that is an hour spent on a problem that never had to exist.

**Your notes folder is the opposite: put it wherever you like, cloud included.**
That is the folder worth backing up, and nothing about it fights with syncing.
Inside Google Drive or Dropbox is a good choice.

> It does have to be a **real folder on your own computer** that happens to
> sync, not a website you log into. Your AI opens files directly and cannot
> reach into a browser tab. The syncing is your backup, nothing more.

---

## Setting it up

**Hand `INSTALL.md` to Claude and say "set up my brain."** It does the rest and
checks with you at each step. About ten minutes.

If you would rather see what it will do first, `INSTALL.md` is written to be
read. The short version:

1. Get the tool: `git clone https://github.com/LifehackMethod/lifehack-brain.git`
   somewhere outside any cloud folder.
2. Open **that** folder in Claude — the Code tab of the desktop app.
3. Tell it once where your notes live. It remembers, permanently.
4. Restart Claude, then type `/ingest`.

**Step 2 matters more than it looks.** Claude only finds this tool when you open
the folder it lives in. Open a folder inside it, or a different folder
altogether, and nothing loads — with no error, which is the annoying part.

---

## What is in here

    .claude/         ← ours. the command itself — this is where Claude looks.
      agents/        ← the specialist readers the skill uses
      skills/
        ingest/      ← the one thing it does today
      settings.json  ← wires it all up the moment you clone

    system/          ← ours. the programs that do the sorting.

    CLAUDE.md        ← ours. the standing instructions every session opens with.
    PLAN-B.md        ← the manual backup, if the tool ever misbehaves

Your own notes are **not in this list**, because they are not in this folder.
They are wherever you said in step 3.

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

It replaces this folder with the newer version. Your notes are somewhere else
entirely, so an update cannot reach them even by accident.
