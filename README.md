# Lifehack Brain

A starting point for an AI that remembers you.

Right now it does one thing, and does it well: it takes a pile of your own
material — an old chat export, a stack of documents, notes you've been keeping —
and turns it into a folder structure you and your AI can both work from.

More will land here over time. When it does, you'll get it with one update.

---

## Setting it up

**1. Pick where your brain lives.**

Make a folder on your computer, inside whatever cloud service you already use —
your Google Drive folder, your Dropbox folder, your OneDrive folder.

This matters and it's worth thirty seconds: you want a **real folder on your own
machine that happens to sync**, not a website you log into. Your AI opens files
directly; it can't reach into a browser tab. The syncing is just your backup.

If you don't use any of those, a plain folder in your Documents works fine. You
just won't have a backup.

**2. Get these files.**

On the green **Code** button above, choose **Download ZIP**. Unzip it, then move
**everything inside** into the folder you made in step 1 — including the `.claude`
folder, which your computer may hide by default.

On a Mac, press **⌘ + Shift + .** in Finder to show hidden files. **Don't skip
it** — `.claude` is what makes the `/ingest` command exist. Without it nothing
happens when you type it.

*(If you know git, just clone the repo instead — nothing to move, nothing hidden.)*

**3. Open that folder in Claude.**

Open the Claude desktop app, go to the **Code** tab, and point it at your folder.
No terminal, nothing to install.

**4. Have your material ready.**

Whatever you want sorted — a ChatGPT export, a folder of notes, a big document.
Know where it is on your computer. You'll hand it over in the next step by
dragging it into the chat window, which pastes its location for you.

**5. Say what you want.**

    /ingest

It'll ask where your brain lives, then ask for your material — drag the file or
folder in when it does. From there it asks questions and shows you its work
before it writes anything.

---

## What's in here

    .claude/         ← ours. the command itself — this is where Claude looks.
      agents/        ← the specialist readers the skill uses
      skills/
        ingest/      ← the one thing it does today

    system/          ← ours. the programs that do the sorting.

    PLAN-B.md        ← the manual backup, if the tool ever misbehaves

    memory/          ← yours. updates never touch it.

**The split is the whole design.** Everything we send you lives in `.claude/` and `system/`.
Everything you write lives in `memory/`. When you update, only those change —
your own notes aren't part of this repository at all, so there's nothing here that
could overwrite them.

---

## If something goes wrong

Open `PLAN-B.md` in the top folder, drag it into a fresh Claude conversation,
and say *"help me."*

It's a complete backup. It walks your AI through the same process by hand, without
needing the tool to work. You get the same result, it just takes a bit longer.

---

## Getting updates

Ask Claude: *"check if there's an update to my brain and install it."*

It'll replace our folders with the newer version and leave `memory/` alone.
