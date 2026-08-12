# START HERE — setting up your Lifehack Brain

You are about to give yourself an AI that remembers you.

Right now it does one thing and does it well: it takes a pile of your own material — an old ChatGPT
export, a folder of notes, a stack of documents — and turns it into a folder structure that you and your
AI can both work from. More will arrive later, and you'll get it with one update.

**This file is the whole setup.** You don't need to know anything technical. You don't need a terminal.
You hand this file to Claude and answer its questions.

---

## The one thing to get right: two folders, not one

**The tool goes in one folder. Everything you write goes in a different one.**

    ~/lifehack-brain/     ← the tool. ours. replaced whole on every update.
    ~/My Notes/           ← everything you write. yours. never touched.

Keeping them apart is what makes updates safe: the tool folder gets replaced
wholesale, and there is nothing of yours inside it to lose.

**⛔ The tool folder must NOT be inside a cloud folder.** Not inside Google Drive,
Dropbox, OneDrive or iCloud Drive. Your home folder is perfect.

> **Why.** The tool folder is a git repository, and git constantly makes and
> deletes hundreds of small files as it works. Cloud sync tools notice each one
> and try to upload it mid-operation. The two fight, and it never shows up as a
> clear error — it shows up as a folder that quietly corrupts, or an update that
> half-applies.

**Your notes folder is the opposite — put it wherever you like, cloud included.**
That is the one worth backing up, and nothing about it fights with syncing.

> It has to be a **real folder on your computer** that happens to sync, not a
> website you log into. Your AI opens files directly and cannot reach into a
> browser tab. The syncing is only your backup.

---

## What you do — three steps, about ten minutes

**1. Open a folder in Claude.** The Claude desktop app → the **Code** tab → any
folder outside your cloud folder. Your home folder is fine. The tool will be
fetched into a new folder inside it.

**2. Drag this file into the chat and say: "Set up my brain."**

**3. Answer its questions.** One of them is where your notes should live. Have an
answer ready, or say "make me one" and it will.

That's it. Claude takes it from here, and it will check with you before each step.

---

## Have this ready

**The material you want sorted.** A ChatGPT export, a folder of notes, one large document — whatever it
is, know where it is on your computer. You'll hand it over later by dragging it into the chat window.

> **You don't need it yet, and nothing will ask for it during setup.** This is just so you're not hunting
> for it afterwards. **Setting up the tool and using it are two separate steps**, and the second one
> happens in a fresh window at the very end.

⚠ **Your material and your notes folder are two different places, and mixing them up is the one mistake
that causes real trouble.** Your material can live anywhere — your Obsidian vault, your Downloads
folder, wherever it already is. Your notes folder is the one you name in step 3, and **everything this
tool produces belongs in there.** When you're asked where your notes live, answer with that folder —
not the folder your material is in.

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
> - ⛔ **Do NOT type `/ingest` yourself, and do not suggest they type it, until STEP 10.**
>
> ⭐ **WHY THIS BLOCK EXISTS — it was watched happening.** A session read this file, saw the "Have this
> ready" note near the top, and **ran ahead to hunt for the corpus before Git was even installed.** The
> person then thought the tool had started working, when in fact nothing had been installed at all.
>
> **The "Have this ready" note above is addressed to the HUMAN, not to you.** It tells them what to have
> on hand *later*. **Treat it as background information you must not act on.**
>
> ## ⛔⛔ NEVER PUT THEIR MATERIAL INSIDE THE TOOL FOLDER. NOT THE ZIP, NOT THE UNZIPPED COPY.
>
> **Their export stays where it already is** — Downloads, Desktop, wherever. ⛔ **Do not copy it in, do not
> move it in, and do not unzip it into this folder or any folder underneath it.**
>
> ⭐ **WHY — watched happening 2026-08-09.** A session was asked to "extract the zip to a folder" and
> extracted it inside the tool folder. That folder is version-controlled, so **git instantly began
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
> handled INSIDE the `/ingest` skill, in a fresh session, after STEP 9's restart.** That skill asks its own
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

## STEP 4 — Work out where the tool folder goes, and check it is not in a cloud folder

Find out where you are:
```bash
pwd
```

The tool will be fetched into a **new sub-folder here called `lifehack-brain`**. Say that out loud —
give them the full path — and ask if that is somewhere sensible. If not, ask them where, and have them
drag the folder into the chat, which pastes its location.

⛔ **Then check it is not inside a cloud folder. This is not optional.**

```bash
case "$(pwd)" in
  *Library/CloudStorage*|*Google?Drive*|*GoogleDrive*|*Dropbox*|*OneDrive*|*iCloud*|*"Mobile Documents"*)
    echo "IN A CLOUD FOLDER — pick somewhere else" ;;
  *) echo "NOT IN A CLOUD FOLDER — good" ;;
esac
```

**If it says it is in a cloud folder, stop and move.** Tell them plainly: *"This folder is inside your
cloud storage, and the tool can't live there — the syncing and the tool fight each other, and it goes
wrong in ways that are hard to spot. Your home folder is a good place. Where would you like it?"*
Then `cd` to the folder they name and run the check again.

⚠ **Their notes are a separate question and it comes later, in STEP 7.** Do not ask about them now, and
do not let this folder become the answer to that question by default.

## STEP 5 — Fetch the files

One command, from the folder you just confirmed:

```bash
git clone https://github.com/LifehackMethod/lifehack-brain.git
cd lifehack-brain
```

That makes a new `lifehack-brain` folder and puts everything in it. **There is nothing to unzip, move,
or unhide** — the `.claude` folder your computer hides by default arrives already in the right place.

Then confirm it landed:
```bash
ls .claude/skills/ingest/SKILL.md && echo "the skill is here"
```

**Tell them what arrived**, in a sentence: the tool itself, and the specialist readers it uses.

> ⛔ **If `git clone` refuses because a folder called `lifehack-brain` is already there**, do NOT try to
> merge into it and do NOT `git init` an existing folder. Ask them whether that folder is an older copy
> they can rename or delete, then clone again. A repository assembled by hand out of two half-copies is
> the kind of thing nobody can diagnose later.

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

## STEP 7 — Ask where their notes should live, and set up day one

**This is the question the whole system hangs on. Ask it once, properly, and never guess the answer.**

Ask them, in these words or close to them:

> **"Where should everything you write end up? This is separate from the tool folder — it's the one
> worth backing up, so somewhere inside Google Drive or Dropbox is a good choice. If you don't have a
> preference I'll make you one right next to the tool folder."**

Have them drag the folder into the chat if it exists, which pastes its location. If they have no
preference, the default below sits one level above the tool folder — outside it, beside it.

Then record it. **This is remembered permanently; they will never be asked again.**

```bash
python3 shared/brain_root.py --set "<the folder they named>"     # add --create if it does not exist yet
```

Default, if they had no preference:
```bash
python3 shared/brain_root.py --set "$(cd .. && pwd)/My Notes" --create
```

Confirm it took, and say the path back to them in a sentence:
```bash
python3 shared/brain_root.py
```

Then make the three files a new setup starts with:
```bash
python3 system/tools/bootstrap.py
```

**Tell them what that did, in plain words:** *"I've made you three empty things in that folder — a
journal, a list of projects, and somewhere for project notes to go. They fill themselves in as you
work."*

⛔ **It makes those three and nothing else, deliberately.** Do not add folders for subjects you think
they might need. How their life divides up is theirs to find out, and a guess handed over on day one
teaches them the guess is the answer.

⚠ **If `--set` refuses**, read them the reason — it will say the folder does not exist (add `--create`)
or that they pointed at a file. Do not work around it.

---

## STEP 8 — Prove it can actually run, before you promise them anything

**A check you skipped is not a check that passed.** Run this one:

```bash
python3 -c "import sys; sys.path.insert(0,'system/tools/cowork-ingest'); import pipeline; print('TOOLS OK')"
```

**If it does not print `TOOLS OK`, stop.** Tell them plainly that the install is incomplete, and read them
the last line of the error. Do not tell them to try `/ingest` anyway — it would fail much later, deep in
the process, in a way that looks like something they did.

**If it printed `TOOLS OK`, the install is good. Continue.**

> **One thing that is missing ON PURPOSE, stated so nobody hunts for it.** The very last step of an
> ingest asks which subject each thing belongs to, and checks the answer against a list of subjects.
> **That list is theirs and it is not in this package.** Nothing ships one, and the tools refuse rather
> than inventing one — a taxonomy of somebody's life, written by a machine, is worse than none.
>
> When they reach that point the tool prints exactly what to do: write
> `memory/topic-vocab.md` **inside their notes folder**, one line per subject, in the form
> `` - `money` ``. ⛔ **Do not pre-empt it, do not write the file for them, and do not treat its
> absence as a broken install.** Everything before that step — sorting into piles, screening them, the
> deep read — works without it.

---

## STEP 9 — ⛔⛔ THE ONE STEP EVERYTHING ELSE DEPENDS ON: MAKE THEM RESTART CLAUDE

**Claude loads skills and agents when a session opens. This session opened before those files existed,
so it cannot see them yet.**

**This is not optional and it is not a formality.** In a real test, someone skipped it and Claude read
the skill file as a *document* instead of *running* it — it produced something that looked roughly right,
took twenty minutes, and was not the tool at all. **Nothing errored.** That is what makes this dangerous:
skipping it does not fail loudly, it fails quietly and convincingly.

Tell them, in these words or very close to them:

> **"Everything is installed. Now you have to quit Claude completely and open it again — not a new chat,
> the whole app. When it comes back, open the `lifehack-brain` folder — that exact folder, not the one
> above it and not a folder inside it. Until you do that, Claude can't see the new command yet. I'll
> wait."**

⚠ **Say "that exact folder" and mean it.** Claude reads this tool's wiring from a `.claude` folder in
whatever folder you open, and it does **not** look upwards. Open the folder above, or a folder inside,
and nothing loads — no warning, no error, everything simply absent. Tested and confirmed: from one
level down, zero of it starts.

Then **STOP. Do not continue this file. Do not offer to run `/ingest` yourself.**

---

## STEP 10 — After they restart (this is the first thing to do in the NEW session)

Confirm the command exists before they type anything:

```bash
ls .claude/skills/ingest/SKILL.md
```

Then tell them:

> **"You're set up. Type `/ingest` and press enter. It already knows where your notes go — you told it
> during setup. It'll ask for your material: drag the file or folder into the chat and it'll fill in the
> location for you. From there it asks you questions and shows you its work before it writes anything."**

---

## STEP 11 — Mention bug reporting, then leave it alone

**Say this once, at the end, and do not start it:**

> **"One more thing, whenever you have five spare minutes — there's a file next to this one called
> `REPORT-A-BUG.md`. It sets you up so that when something breaks you can just say 'file a bug' and it
> goes straight to the person who maintains this, with the actual error attached. It needs a free GitHub
> account. Not now — it's a separate five minutes, and you don't need it to start using this."**

⛔ **Do not set it up now, do not check whether they have a GitHub account, and do not install anything
for it.** They have just finished a ten-minute install and the next thing they should do is use the
thing they installed. **It is a separate session with its own file**, exactly like `/ingest` is.

⭐ **Why it's worth mentioning at all:** the fastest bug fix so far came from someone who filed one this
way — the report carried the real error, so it was fixed the next day. A bug nobody reports gets found
by the next person instead.

---
---

# IF SOMETHING GOES WRONG

**Read the symptom, not the error message.** These are the three things that actually happen.

> ⭐ **And if none of them is your problem, tell whoever maintains this.** `REPORT-A-BUG.md`, sitting
> beside this file, sets that up in about five minutes — after which you just say **"file a bug"** and
> the actual error goes where it can be fixed. **A problem nobody reports gets found by the next person
> instead.**

**1. You type `/ingest` and nothing happens, or Claude starts improvising.**
Almost always the session wasn't restarted. Go back to **STEP 9** and do it properly — quit the whole
app, not just the chat. If that doesn't fix it, re-run **STEP 6**'s check to confirm the files arrived.

**2. Something says a module or a file can't be found.**
Python isn't installed, or isn't on the PATH. Go back to **STEP 3**. On Windows this is almost always the
un-ticked "Add python.exe to PATH" checkbox — the fix is to re-run the Python installer and tick it.

**3. It's installed and running, but behaving oddly.**
There is a complete manual backup: **`PLAN-B.md`**, sitting right next to this file in the top folder.
Drag it into a **fresh** Claude conversation and say **"help me."** It walks your AI through the same
process by hand, without needing any of the tools to work. You get the same result; it just takes longer.

**4. Your own notes ended up inside the tool folder, and git is now tracking them.**
This happens if an export got unzipped, or a notes folder got copied, INSIDE the folder you cloned
rather than beside it — the mistake **STEP 4** and **STEP 7** exist to prevent. It is not dangerous:
you cannot upload anything to a repository you do not own. But your private history should not be
sitting in a folder pointed at a public one. Run this from the tool folder:

    sh system/tools/untrack-my-stuff.sh

**It does not delete anything.** It takes your material out of git's index with `git rm --cached` and
leaves every file exactly where it is on disk. It shows you what it found and asks before acting.

---

# WHAT'S IN HERE, AND WHY IT'S SPLIT THIS WAY

```
lifehack-brain/          ← OURS. replaced whole on every update.
├── .claude/                 the command itself — this is where Claude looks
│   ├── agents/              the specialist readers the tool uses
│   ├── skills/              the tool itself
│   └── settings.json        wires it up the moment you clone
├── system/                  the programs that do the sorting
├── CLAUDE.md                the standing instructions every session opens with
├── UPDATE.md                how to take a newer version, and what it cannot touch
├── REPORT-A-BUG.md          five minutes, once, so you can say "file a bug"
└── PLAN-B.md                the manual backup, if the tool ever misbehaves

My Notes/                ← YOURS. a different folder, outside this one.
├── system/journal.md        what happened, as it happens
├── system/project-registry.md   so a cold session can find an old project
├── state/projects/<name>/   one folder per project: its brief, its records, its canon
└── desks/<subject>/         a folder per subject, once you have run an ingest
```

**The split is the whole design.** Everything sent to you is in the first folder. Everything you write
is in the second. An update replaces the first one completely — and cannot reach the second even by
accident, because your notes are not in this repository at all.

**To get updates later, ask Claude:** *"check if there's an update to my brain and install it."*

---

# WEB SEARCH — one key, and it is optional

Searching the web needs an API key from **serper.dev**, which has a free tier. Without one, search
simply refuses and says so; everything else works normally.

There is deliberately no second path. The system this came from had a fallback that drove a real
Chrome window, and it is not here: it depended on a separate browser plugin, and a fallback that
cannot work is worse than none, because you find out at the moment you needed it.

Put the key in a file — this is the version that also works for anything running on a schedule:

```bash
mkdir -p ~/.config/lifehack
umask 077 && printf %s 'your-key-here' > ~/.config/lifehack/serper-key
```

It is also read from `$SERPER_API_KEY`, and on a Mac from the keychain (service `serper-api-key`,
account `lifehack`) — in that order, keychain last. The keychain belongs to your logged-in desktop
session, so anything running unattended cannot see it; the file can.

**Every result is sanitized before it reaches the conversation.** Titles and snippets are written by
whoever owns the page, so they are treated as somebody else's text, not as facts.

---

# READING DOCUMENTS — three optional libraries

PDFs, Word files and spreadsheets are read through tools that strip what you cannot see: white text,
hidden rows, hidden Word runs, and spreadsheet cells that are secretly formulas. Each needs one
library, and each tells you the exact command the first time you need it:

```bash
pip install pdfplumber      # .pdf
pip install python-docx     # .docx
pip install openpyxl        # .xlsx
```

Install them when you first hit one. Plain text, markdown and CSV need nothing.

---

# NOTIFICATIONS ON YOUR PHONE — optional, and off until you set it up

Nothing pushes to your phone unless you give it somewhere to push to. If you want it, pick a long
unguessable string as your topic, subscribe to that topic in the **ntfy** app, and write it down:

```bash
mkdir -p ~/.config/lifehack
umask 077 && printf %s 'your-long-unguessable-topic' > ~/.config/lifehack/ntfy-topic
```

**Treat that string as a password.** Anyone who knows it can read every notification you send.

Two things are true of it by design. **A notification is a doorbell, never the parcel** — it says
something happened and where to look, and never carries names, amounts or content, because a push
lands on a lock screen. And **the volume is capped in code, not by good intentions**: no more than
three per source per day, nothing during quiet hours, and the same message never twice. A genuine
emergency ignores all three, which is the only reason the other three can be trusted.

---

# THE GOOGLE-CONNECTED PARTS — the readers are here, the connection is not

The **sanitizing side** now ships: `system/tools/safe_calendar.py` and `system/tools/safe_tasks.py`
take a calendar or task list and run every piece of free text through the same filter as everything
else — because an invite's title and description are written by whoever sent it, and anyone who
knows your address can send you one.

What is **not** here is the connection. These tools call a command-line tool called `gws` that talks
to your account, and neither it nor your authentication is part of this package.

- **You connect your own account.** Nobody else's credentials are involved and nothing is shared.
- **Your own identifiers — which calendar, which spreadsheet — live in your notes folder**, at
  `config/`, never in this repository. Same rule as everything else you own.
- **It is a sit-down, not a click.** Expect to do it with someone the first time.

⛔ **Until you have done that sit-down, do not run an authentication flow on your own and do not hand
your account details to anything.** Nothing here needs them yet.

## What the sit-down covers

Do these in order, together, once. None of it is needed to use everything else in this package.

**1 — Install `gws` and log in.** It is the command-line tool that talks to Google. Install it however
your machine installs things, then run its login and grant only the scopes you actually intend to use.
Check it landed and that the login took:

```bash
command -v gws          # a path means it is installed
gws auth status         # says which account is connected
```

⛔ **Never `gws auth logout`, and never delete or move `~/.config/gws/`.** That directory is the
login for every window on this machine, and there is no undo — you would redo this sit-down. If
something looks broken, run `gws auth status` and read what it says before touching anything.

**2 — Put your own identifiers in your notes folder, not in this repo.** Which calendar, which
spreadsheet, which task list — those are yours, and they are the kind of thing a public repository
must never carry. They live at `<notes>/config/`, one small file per thing, named so a stranger
could tell what it is:

```
<notes>/config/sheets.md     # "billing tracker → 1AbC...", one line per sheet you use
<notes>/config/cal.md        # which calendar things get written to
```

A skill that needs an id reads it from there. If the file is not there, the skill says so rather than
guessing — which is the correct behaviour, and the reason nothing is pre-filled.

**3 — `clasp`, only if you want Apps Script.** `clasp` is Google's command-line tool for Apps Script,
and `/google-sheet` uses it for logic a formula cannot express. **Skip this unless you hit that wall** —
formulas, `ARRAYFORMULA` and the self-check layer all work with no clasp installed at all, and most
sheets never need it. If you do install it, its credential (`~/.clasprc.json`) is machine-local and
must never be committed, exactly like the `gws` login.

## What is guarded once you are connected

Two hooks watch spreadsheet writes from the moment you register them, and they are worth knowing about
before they surprise you:

- **You must read a sheet's `_LLM_GUIDE` tab before writing to it.** Every sheet this system builds
  carries one, holding its structure and its rules. The first write to a sheet in a session is refused
  with an instruction to read that tab; after that, writes go through for twelve hours.
- **A write that would land on a formula is refused outright.** Google's own cell protection does not
  stop a write authenticated as the file's owner — which is you — so this is the only place it can be
  stopped. Appending rows is never blocked. Changing a formula on purpose means showing yourself the
  exact before and after and re-running with `LIFEHACK_SHEET_CONFIRM=1` in front of the command.

Neither hook touches anything that is not a `gws sheets` command, and neither needs `jq`.
