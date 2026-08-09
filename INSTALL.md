# START HERE — setting up your Lifehack Brain

You are about to give yourself an AI that remembers you.

Right now it does one thing and does it well: it takes a pile of your own material — an old ChatGPT
export, a folder of notes, a stack of documents — and turns it into a folder structure that you and your
AI can both work from. More will arrive later, and you'll get it with one update.

**This file is the whole setup.** You don't need to know anything technical. You don't need a terminal.
You hand this file to Claude and answer its questions.

---

## What you do — three steps, about ten minutes

**1. Make a folder for your brain.**
Somewhere you'll find it again. Inside your Google Drive folder, your Dropbox folder, your OneDrive
folder — whichever one you already use — or plain `Documents` if you use none of them.

Call it **`Lifehack Brain`**.

> It has to be a **real folder on your own computer** that happens to sync, not a website you log into.
> Your AI opens files directly and cannot reach into a browser tab. The syncing is only your backup.

**2. Open that folder in Claude.**
Open the Claude desktop app → the **Code** tab → point it at the folder you just made.

**3. Drag this file into the chat and say: "Set up my brain."**

That's it. Claude takes it from here, and it will check with you before each step.

---

## Have this ready

**The material you want sorted.** A ChatGPT export, a folder of notes, one large document — whatever it
is, know where it is on your computer. You'll hand it over later by dragging it into the chat window.

> **You don't need it yet, and nothing will ask for it during setup.** This is just so you're not hunting
> for it afterwards. **Setting up the tool and using it are two separate steps**, and the second one
> happens in a fresh window at the very end.

⚠ **Your material and your brain are two different places, and mixing them up is the one mistake that
causes real trouble.** Your material can live anywhere — your Obsidian vault, your Downloads folder,
wherever it already is. Your brain is the `Lifehack Brain` folder you made in step 1, and **everything
this tool produces belongs in there.** When you're asked where your brain lives, answer with the folder
from step 1 — not the folder your material is in.

---
---

# INSTRUCTIONS FOR CLAUDE

**You are setting up a non-technical person's AI brain. Read all of this before you do anything.**

## How to behave during this setup

- **They have never opened a terminal and they will not know what anything is called.** Do not show them
  a command and ask them to approve it. Run it, then tell them in one plain sentence what happened.
- **Whole sentences, always.** Say "Git is already installed on your computer, so there's nothing to do
  here" — never "git: OK". A status token means nothing to them.
- **Say what you are about to do before you do it, and what happened after.** Every step.
- **One step at a time. Stop and confirm between steps.** Never chain the whole setup and report at the
  end — if something breaks in the middle they need to know which thing broke.
- **If a step fails, say so plainly and say what it means for them.** Never say "some checks failed."
  Name the thing, in words they can repeat out loud to someone helping them.
- **Never invent a result.** If you could not check something, say you could not check it. A guess that
  sounds confident is worse here than an honest "I don't know," because they cannot tell the difference
  and they will act on it.

> ## ⛔⛔ YOUR JOB IS THE INSTALL. IT IS NOT THE INGEST. DO NOT START THE INGEST.
>
> **This file installs a tool. A DIFFERENT thing — the `/ingest` command — uses it. You are only doing the
> first one.**
>
> **So, for the whole of this file:**
> - ⛔ **Do NOT go looking for their material.** Do not search their computer for a ChatGPT export, an
>   Obsidian vault, a notes folder, or anything else. Do not offer to find it.
> - ⛔ **Do NOT ask them where their material is, what format it is in, or how big it is.** None of that is
>   your business here and asking it makes them think the sorting has begun.
> - ⛔ **Do NOT read, open, convert, copy or move a single one of their files.**
> - ⛔ **Do NOT run any script in `system/tools/`.** Nothing in there belongs to the install.
> - ⛔ **Do NOT type `/ingest` yourself, and do not suggest they type it, until STEP 9.**
>
> ⭐ **WHY THIS BLOCK EXISTS — it was watched happening.** A session read this file, saw the "Have this
> ready" note near the top, and **ran ahead to hunt for the corpus before Git was even installed.** The
> person then thought the tool had started working, when in fact nothing had been installed at all.
>
> **The "Have this ready" note above is addressed to the HUMAN, not to you.** It tells them what to have
> on hand *later*. **Treat it as background information you must not act on.**
>
> ## ⛔⛔ NEVER PUT THEIR MATERIAL INSIDE THE BRAIN FOLDER. NOT THE ZIP, NOT THE UNZIPPED COPY.
>
> **Their export stays where it already is** — Downloads, Desktop, wherever. ⛔ **Do not copy it in, do not
> move it in, and do not unzip it into this folder or any folder underneath it.**
>
> ⭐ **WHY — watched happening 2026-08-09.** A session was asked to "extract the zip to a folder" and
> extracted it inside the brain folder. That folder is version-controlled, so **git instantly began
> tracking 6,228 changes** — including the export's own `users.json`, which carries the person's **email
> address and phone number.** It could not actually reach the public repository (they hold no upload
> credentials), but the folder was polluted and their private history was staged for upload.
>
> **The rule, in the words it was given in:** *"use the root folder as file storage, not the git
> repository — nothing from the user's perspective should be tracked in the git repo."*
>
> ⭐ **You do not need to unzip anything anyway.** The tool opens the zip itself, and unpacks it somewhere
> outside this folder on purpose. **Just tell it where the zip is.**
>
> ⭐ **Everything about their actual material — where it lives, what format it is, how to read it — is
> handled INSIDE the `/ingest` skill, in a fresh session, after STEP 8's restart.** That skill asks its own
> questions in its own order. **If you ask them first, you are asking questions the real tool is about to
> ask again**, and their answers will not carry across the restart anyway.

---

## STEP 0 — Say hello and get a go

Tell them, in your own words and in about four sentences:
- what you are about to install (a folder of files that adds one new command, `/ingest`, to Claude),
- that it takes about ten minutes,
- that you'll check with them at each step,
- that nothing on their computer gets changed outside the folder you're working in.

Then ask: **"Ready to start?"** Wait for them.

---

## STEP 1 — Find out what kind of computer this is

```bash
uname -s 2>/dev/null || echo "Windows"
```

`Darwin` means a Mac. `Linux` means Linux. Anything else, treat it as Windows.

**Say which one you found, in a sentence.** Everything below has a Mac path and a Windows path; pick the
right one and never show them the other.

---

## STEP 2 — Check for Git, and install it if it's missing

Git is the thing that will fetch the files, and later fetch updates.

```bash
git --version
```

**If that printed a version number:** tell them Git is already installed and there's nothing to do. Move
on.

**If it did not — Mac:**
```bash
xcode-select --install
```
This opens a small Apple dialog box on their screen. **Tell them it will appear, tell them to click
Install, and tell them it can take several minutes.** Then wait — do not move on until `git --version`
answers. Check again when they say it finished.

**If it did not — Windows:**
```powershell
winget install --id Git.Git -e --source winget
```
If `winget` isn't available, send them to <https://git-scm.com/download/win>, tell them to run the
installer and click Next through all of it, and wait for them to say it's done.

⛔ **Do not continue until `git --version` prints a version.** Every later step depends on it.

---

## STEP 3 — Check for Python, and install it if it's missing

Python runs the tools that do the actual sorting.

```bash
python3 --version || python --version
```

**You need version 3.9 or higher.** If you got a version and it's 3.9+, tell them it's already there and
move on.

**If it's missing or too old — Mac:**
```bash
xcode-select --install    # usually brings it along; check again after
```
If it's still missing, send them to <https://www.python.org/downloads/macos/> and have them run the
installer.

**If it's missing or too old — Windows:**
```powershell
winget install --id Python.Python.3.12 -e --source winget
```
Or <https://www.python.org/downloads/windows/>. ⚠ **Tell them explicitly: on the first screen of the
Windows installer there is a checkbox that says "Add python.exe to PATH" and they must tick it before
clicking Install.** If they miss it, nothing will work later and the reason will be invisible.

⛔ **Do not continue until Python answers with 3.9 or higher.**

---

## STEP 4 — Confirm where the brain goes, out loud

Find out where you currently are:
```bash
pwd
```

**Show them that folder and ask, in plain words: "Is this where you want your brain to live?"**

- **Yes** → that's the target. Continue.
- **No** → ask them for the right folder. Have them drag it into the chat, which pastes its location.

⚠ **Do not skip this and do not assume.** This exact confusion was watched happening in a real test: the
person pointed the tool at their notes folder and the output landed in their notes folder instead of
their brain. **The folder their material is in is not the folder their brain lives in.**

---

## STEP 5 — Fetch the files

From inside the target folder:

```bash
git clone https://github.com/LifehackMethod/lifehack-brain.git .
```

**If it refuses because the folder isn't empty**, that is normal and recoverable — the folder probably
already has this file in it. Do this instead:
```bash
git init
git remote add origin https://github.com/LifehackMethod/lifehack-brain.git
git fetch origin
git checkout -f -t origin/main
```

Then confirm it landed:
```bash
ls .claude/skills/ingest/SKILL.md && echo "the skill is here"
```

**Tell them what arrived**, in a sentence: the tool itself, the specialist readers it uses, and an empty
`memory/` folder that is theirs.

---

## STEP 6 — Confirm the pieces arrived

One check. Claude only discovers a skill inside a folder called `.claude`, so confirm it's there:

```bash
test -f .claude/skills/ingest/SKILL.md && test -d .claude/agents && echo "FILES OK" || echo "FILES MISSING"
```

**If it says `FILES OK`**, turn on the safety catch that keeps their own notes out of the repository, and
then move on:

```bash
git config core.hooksPath system/githooks && echo "SAFETY CATCH ON"
```

**Tell them what that did, in one plain sentence:** *"I've turned on a safety catch — if anything ever
tries to upload your own notes to the internet, it will stop and refuse."*
⚠ **This line IS the install.** The check itself ships inside the folder, but git ignores it until this
command points at it — without this, the file is decoration.

**If it says `FILES MISSING`**, the download did not complete. ⛔ **Do not try to assemble or copy the
files yourself.** Delete what's there and run **STEP 5** again — a half-finished download that you patch
by hand produces a setup nobody can diagnose later.

> *(There is nothing to repair or wire up here. The files ship in the exact place Claude looks for them.)*

---

## STEP 7 — Prove it can actually run, before you promise them anything

**A check you skipped is not a check that passed.** Run this one:

```bash
python3 -c "import sys; sys.path.insert(0,'system/tools/cowork-ingest'); import pipeline; print('TOOLS OK')"
```

**If it does not print `TOOLS OK`, stop.** Tell them plainly that the install is incomplete, and read them
the last line of the error. Do not tell them to try `/ingest` anyway — it would fail much later, deep in
the process, in a way that looks like something they did.

**If it printed `TOOLS OK`, the install is good. Continue.**

> **A known gap, stated so nobody wastes time hunting it.** One file that the *final* step needs —
> `system/topic-vocab.md`, used when the folder structure is written out at the very end — is not in this
> release yet. **It does not affect anything up to that point:** sorting into piles, screening them, and
> the deep read all work without it. It arrives in the next update, which you get by asking Claude to
> check for one. ⛔ **Do not treat its absence as a broken install and do not try to write the file
> yourself** — an invented vocabulary is worse than a missing one.

---

## STEP 8 — ⛔⛔ THE ONE STEP EVERYTHING ELSE DEPENDS ON: MAKE THEM RESTART CLAUDE

**Claude loads skills and agents when a session opens. This session opened before those files existed,
so it cannot see them yet.**

**This is not optional and it is not a formality.** In a real test, someone skipped it and Claude read
the skill file as a *document* instead of *running* it — it produced something that looked roughly right,
took twenty minutes, and was not the tool at all. **Nothing errored.** That is what makes this dangerous:
skipping it does not fail loudly, it fails quietly and convincingly.

Tell them, in these words or very close to them:

> **"Everything is installed. Now you have to quit Claude completely and open it again — not a new chat,
> the whole app. When it comes back, open this same folder. Until you do that, Claude can't see the new
> command yet. I'll wait."**

Then **STOP. Do not continue this file. Do not offer to run `/ingest` yourself.**

---

## STEP 9 — After they restart (this is the first thing to do in the NEW session)

Confirm the command exists before they type anything:

```bash
ls .claude/skills/ingest/SKILL.md
```

Then tell them:

> **"You're set up. Type `/ingest` and press enter. It'll ask where your brain lives — that's this
> folder. Then it'll ask for your material — drag the file or folder into the chat and it'll fill in the
> location for you. From there it asks you questions and shows you its work before it writes anything."**

---
---

# IF SOMETHING GOES WRONG

**Read the symptom, not the error message.** These are the three things that actually happen.

**1. You type `/ingest` and nothing happens, or Claude starts improvising.**
Almost always the session wasn't restarted. Go back to **STEP 8** and do it properly — quit the whole
app, not just the chat. If that doesn't fix it, re-run **STEP 6**'s check to confirm the files arrived.

**2. Something says a module or a file can't be found.**
Python isn't installed, or isn't on the PATH. Go back to **STEP 3**. On Windows this is almost always the
un-ticked "Add python.exe to PATH" checkbox — the fix is to re-run the Python installer and tick it.

**3. It's installed and running, but behaving oddly.**
There is a complete manual backup: **`PLAN-B.md`**, sitting right next to this file in the top folder.
Drag it into a **fresh** Claude conversation and say **"help me."** It walks your AI through the same
process by hand, without needing any of the tools to work. You get the same result; it just takes longer.

---

# WHAT'S IN HERE, AND WHY IT'S SPLIT THIS WAY

```
Lifehack Brain/
├── .claude/     ← ours. The command itself — this is where Claude looks.
│   ├── agents/      the specialist readers the tool uses
│   └── skills/      the tool itself
├── system/      ← ours. The programs that do the sorting.
├── PLAN-B.md    ← the manual backup, if the tool ever misbehaves
└── memory/      ← YOURS. Updates never touch it.
```

**The split is the whole design.** Everything sent to you lives in `.claude/` and `system/`. Everything
you write lives in `memory/`. When you update, only the first two change — what you wrote is not part of
this repository at all, so there is nothing here that could overwrite it.

**To get updates later, ask Claude:** *"check if there's an update to my brain and install it."*
