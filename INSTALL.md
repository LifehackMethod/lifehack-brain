# START HERE — setting up your Lifehack Brain

You are about to give yourself an AI that remembers you.

Right now it does one thing and does it well: it takes a pile of your own material — an old ChatGPT
export, a folder of notes, a stack of documents — and turns it into a folder structure that you and your
AI can both work from. More will arrive later, and you'll get it with one update.

**This file is the whole setup.** You don't need to know anything technical. You don't need a terminal.
You hand this file to Claude and answer its questions.

---

## What it builds — one folder, and everything lives inside it

    AI Brain/                 <- the ONE folder you open. every time.
    ├── lifehack-brain/          the tool. ours. replaced whole on every update.
    └── data/                    everything you write. yours. never touched.
        └── desks/               a folder per subject, once you've run an ingest

**You open the top one. That's the only thing to remember.**

Setup builds all of it for you. **You are asked exactly one question: where to put the top folder.**

**⛔ It can't live inside Google Drive, Dropbox or OneDrive.** The tool half is a git repository, and
cloud sync services damage those — quietly, not with an error. Setup checks for you and won't let it
happen.

**Your writing still gets backed up.** Setup points your cloud service at the `data` folder and nothing
else — that's the part that's yours and can't be re-downloaded.

## What you do — about ten minutes

**1. Open a folder in Claude.** The desktop app, the **Code** tab, any folder that isn't inside Google
Drive, Dropbox or OneDrive. Your Documents folder is fine.

**2. Drag this file into the chat and say: "Set up my brain."**

**3. Say yes when it asks where to put your AI Brain folder.** That's the only decision. It builds the
rest.

⚠ **If it goes quiet, look for a small box with an Allow button.** It isn't stuck — it's waiting on you.

## Have this ready

**The material you want sorted.** A ChatGPT export, a folder of notes, one large document — whatever it
is, know where it is on your computer. You'll hand it over later by dragging it into the chat window.

> **You don't need it yet, and nothing will ask for it during setup.** This is just so you're not hunting
> for it afterwards. **Setting up the tool and using it are two separate steps**, and the second one
> happens in a fresh window at the very end.

⚠ **Your material and your `data` folder are two different places, and mixing them up is the one mistake
that causes real trouble.** Your material can live anywhere — your Obsidian vault, your Downloads
folder, wherever it already is. **`data` is the folder setup builds inside your AI Brain, and everything
this tool produces belongs in there.** ⛔ Never move your raw material into it, and never move it into
the tool folder either — just tell the tool where it already is.

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
>   Obsidian vault, an AI Brain folder, or anything else. Do not offer to find it.
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

> ⛔⛔ **TWO WINDOWS TRAPS, BOTH MEASURED ON REAL STUDENTS (2026-08-12). Read them BEFORE running the
> command above — both look like something the student did wrong, and neither is.**
>
> **TRAP 1 — `winget` is often BLOCKED, and that is not an error.** Verbatim from a failed run:
> *"I'm blocked by the app's security policy from launching installers."* **Do not diagnose it, do not
> retry it, do not apologise at length.** One sentence — *"Windows won't let me run the installer for
> you, so this bit is yours"* — then send them to <https://www.python.org/downloads/windows/> and wait.
>
> **TRAP 2 — WINDOWS SHIPS DECOY `python.exe` AND `python3.exe` FILES.** They are Microsoft Store
> shortcuts, and Windows puts their folder EARLY on the PATH, so they beat a real installation.
> **The symptom is the confusing part: typing `python` opens the Store, or prints nothing, even after
> Python installed perfectly.** The student will be certain they installed it. They will be right.
> **The fix:** Settings → Apps → **Advanced app settings** → **App execution aliases** → switch OFF both
> `python.exe` and `python3.exe`. Fastest route: Start menu, type "Manage app execution aliases".
> ⭐ **THEN OPEN A NEW WINDOW.** It does not take effect in one already open, and it will look like the
> fix failed. **Say that before they check.**
> ⚠ Reversible, and turns nothing off that they use. Say so — "disable" frightens people.

⚠ **However it gets installed, tell them explicitly: the Windows installer's first screen has a checkbox
reading "Add python.exe to PATH" and they must tick it before clicking Install.** Miss it and nothing
works later, invisibly.

⛔ **Do not continue until Python answers with 3.9 or higher.**

---

## STEP 4 — Build the AI Brain folder. ONE question, then get on with it.

⛔⛔ **THIS IS THE ONLY THING YOU ASK THEM IN THE WHOLE INSTALL. Everything below STEP 4 you build
without asking.** Every extra question is a place the install stalls, and it has stalled on questions
more than on anything else.

**Offer a default. Do not make them invent one.**

| | offer this |
|---|---|
| **Mac** | `~/AI Brain` |
| **Windows** | `%USERPROFILE%\Documents\AI Brain` |

Say it in one sentence and let them agree or name another: *"I'll put your AI Brain folder at
`<path>` — everything lives inside it. Want it somewhere else instead?"*

⛔ **NEVER offer a protected system location.** Not `C:\Users\` itself, not `C:\Program Files`, not
`C:\ProgramData`, not `/System`, not `/Library`. **If they name one, say plainly it's a protected
system folder and offer the default again.**

⛔ **Then check their answer is not inside a cloud folder. Not optional, and it must be THIS check.**

```bash
python3 - "<the path they chose>" <<'PY'
import os, sys
p = os.path.abspath(sys.argv[1])
low = p.replace("\\", "/").lower() + "/"
# folder names the cloud clients ALWAYS create, on either OS. "my drive" and "shared drives"
# are how Google Drive mounts on WINDOWS, where the path is a bare drive letter (G:\My Drive\...)
# and never contains the word "google".
cloud = ["library/cloudstorage", "google drive", "googledrive", "/my drive/", "/shared drives/",
         "/shared drive/", "onedrive", "dropbox", "icloud", "mobile documents", "/box/", "pcloud"]
# protected system locations — never install here
prot = ["/program files", "/programdata", "/windows/", "/system/", "/library/"]
import re
if re.fullmatch(r"[a-z]:/users/?", low) or low in ("/users/", "/home/"):
    print("PROTECTED - that is the system users folder, pick a folder inside it"); sys.exit(3)
hit = next((t for t in cloud if t in low), None)
if hit:
    print("IN A CLOUD FOLDER - pick somewhere else (matched: %s)" % hit.strip("/")); sys.exit(2)
hit = next((t for t in prot if t in low), None)
if hit:
    print("PROTECTED SYSTEM FOLDER - pick somewhere else (matched: %s)" % hit.strip("/")); sys.exit(3)
print("GOOD"); sys.exit(0)
PY
```

> ⛔⛔ **DO NOT REPLACE THIS WITH A SHELL `case` STATEMENT. ONE WAS HERE AND IT WAS BLIND ON WINDOWS.**
> **Google Drive on Windows mounts as a drive letter — `G:\My Drive\AI Brain` — containing no
> occurrence of the word "Google" at all**, so the old check printed *"not in a cloud folder — good"*
> while sitting inside Google Drive. *(Found 2026-08-12 on a real Windows run.)*

Create it:
```bash
mkdir -p "<the path>"
```

⛔ **If `mkdir` fails with a permission error, DO NOT ask for administrator rights and DO NOT retry the
same place.** Say *"Windows won't let me write there — I'll use `<their Documents folder>` instead"*,
and move on. **A real student lost their install to exactly this detour.**

## STEP 5 — Fetch the tool INTO their AI Brain folder

Go into the folder STEP 4 made, then clone. **The clone creates `lifehack-brain` as a subfolder — that
is exactly what we want.**

```bash
cd "<the AI Brain path>" && git clone https://github.com/LifehackMethod/lifehack-brain.git
```

Confirm it landed:
```bash
ls "<the AI Brain path>/lifehack-brain/.claude/skills/ingest/SKILL.md" && echo "the skill is here"
```

**Tell them what arrived**, in a sentence: the tool itself, and the specialist readers it uses.

⭐ **The skills live inside that repo and are found from the folder above it — verified 2026-08-12.**
⛔ **Do NOT symlink anything into `~/.claude/`.** Symlinks are Mac-coupled and this has to work on
Windows too. The tool is discovered where it sits.

> ⛔ **If `git clone` refuses because a `lifehack-brain` folder is already there**, do NOT merge into it
> and do NOT `git init` an existing folder. Ask whether that folder is an older copy they can rename or
> delete, then clone again. A repository assembled by hand from two half-copies is the kind of thing
> nobody can diagnose later.

## STEP 6 — Confirm the pieces arrived, and turn on the safety catch

```bash
cd "<the AI Brain path>/lifehack-brain" && test -f .claude/skills/ingest/SKILL.md && test -d .claude/agents && echo "FILES OK" || echo "FILES MISSING"
```

**If `FILES OK`**, turn on the catch that keeps their own writing out of the repository:

```bash
cd "<the AI Brain path>/lifehack-brain" && git config core.hooksPath system/githooks && echo "SAFETY CATCH ON"
```

**Say what that did, in one plain sentence:** *"I've turned on a safety catch — if anything ever tries to
upload your own notes to the internet, it will stop and refuse."*

⚠ **This line IS the install.** The check ships inside the folder, but git ignores it until this command
points at it. Without it, the file is decoration.

**If `FILES MISSING`**, the download didn't complete. ⛔ **Do not assemble or copy files yourself.**
Delete what's there and run **STEP 5** again — a half-finished download patched by hand produces a setup
nobody can diagnose later.

## STEP 7 — Build `data`. ⛔ ASK THEM NOTHING.

> ⛔⛔ **THIS STEP USED TO ASK *"Where should everything you write end up?"* AND IT WAS THE SINGLE
> BIGGEST CAUSE OF FAILED INSTALLS. DO NOT REINTRODUCE IT IN ANY FORM.**
> It defaulted to a folder called "My Notes", which made people think it was a scratch folder for
> jottings — it is their entire memory. **Measured 2026-08-12: multiple students answered it with a bare
> "ok" and silently got a folder in the wrong place; others stalled on it and never restarted.** It even
> confused a student whose install was otherwise working perfectly.
> ⭐ **There is no decision here. `data` goes inside the AI Brain folder. That is the design.**

```bash
mkdir -p "<the AI Brain path>/data"
python3 "<the AI Brain path>/lifehack-brain/shared/brain_root.py" --set "<the AI Brain path>/data"
cd "<the AI Brain path>/lifehack-brain" && python3 system/tools/bootstrap.py
```

**Then say what you made, in one plain sentence, and move on:** *"Your writing goes in a folder called
`data`, right next to the tool. I've put a journal, a project list and somewhere for project notes in
there — they fill themselves in as you work."*

⛔ **`desks/` is NOT created here.** Those appear inside `data` the first time they run an ingest, one
per subject, built from their own material. **Do not pre-create them and do not invent subject names** —
how their life divides up is theirs to find out, and a guess handed over on day one teaches them the
guess is the answer.

## STEP 8 — Prove it can actually run, before you promise them anything

**A check you skipped is not a check that passed.**

```bash
cd "<the AI Brain path>/lifehack-brain" && python3 -c "import sys; sys.path.insert(0,'system/tools/cowork-ingest'); import pipeline; print('TOOLS OK')"
```

**If it does not print `TOOLS OK`, stop.** Tell them plainly the install is incomplete and read them the
last line of the error. **Do not tell them to try `/ingest` anyway** — it would fail much later, deep in
the process, in a way that looks like something they did.

Then confirm the shape is right — **exactly two folders inside the AI Brain, nothing else:**
```bash
ls -A "<the AI Brain path>"
```
⛔ **It must show exactly `data` and `lifehack-brain`.** A third thing means something went wrong; say so
rather than continuing.

> **One thing missing ON PURPOSE, stated so nobody hunts for it.** The last step of an ingest asks which
> subject each thing belongs to, and checks the answer against a list of subjects. **That list is theirs
> and is not in this package.** Nothing ships one, and the tools refuse rather than inventing one — a
> taxonomy of somebody's life, written by a machine, is worse than none. When they reach that point the
> tool prints exactly what to do. ⛔ **Do not pre-empt it, do not write the file for them, and do not
> treat its absence as a broken install.**

## STEP 9 — ⛔⛔ THE ONE STEP EVERYTHING ELSE DEPENDS ON: MAKE THEM RESTART CLAUDE

**Claude loads its commands when a session opens. This session opened before those files existed, so it
cannot see them yet.**

**Not optional and not a formality.** In a real test someone skipped it and Claude read the skill file as
a *document* instead of *running* it — it produced something that looked roughly right, took twenty
minutes, and was not the tool at all. **Nothing errored.** That is what makes it dangerous: skipping it
fails quietly and convincingly.

Tell them, in these words or very close:

> **"Everything's installed. Now quit Claude completely and open it again — the whole app, not just a
> new chat. When it comes back, open the folder called `<their AI Brain name>`. That exact folder — not
> the ones inside it. I'll wait."**

⚠ **Say "that exact folder" and mean it, and be precise about WHICH one.** They open the **AI Brain**
folder — the outer one. **Not `lifehack-brain`, and not `data`.** Everything the tool needs is reachable
from the outer folder; open one of the inner ones and half the system is outside its reach.

⭐ **This is the single biggest change from the old instructions**, which told people to open
`lifehack-brain` itself. That is what left their writing outside the tool's reach. **If they have done
this before, they will reach for the wrong folder out of habit — say so plainly.**

Then **STOP. Do not continue this file. Do not offer to run `/ingest` yourself.**

## STEP 10 — After they restart (the first thing to do in the NEW session)

Confirm the command exists before they type anything:

```bash
ls lifehack-brain/.claude/skills/ingest/SKILL.md
```

⭐ **Note the path — you are in the AI Brain folder and the tool is one level down.** That is correct and
it is how it is supposed to look.

Then tell them:

> **"You're set up. Type `/ingest` and press enter. It already knows where your writing goes — you told
> it during setup. It'll ask for your material: drag the file or folder into the chat and it'll fill in
> the location for you. From there it asks you questions and shows you its work before it writes
> anything."**

⚠ **And remind them once:** *"If it ever goes quiet, look for a small box with an Allow button. It's
waiting on you, not stuck."*

# IF SOMETHING GOES WRONG

**Read the symptom, not the error message.** These are the three things that actually happen.

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

---

# WHAT'S IN HERE, AND WHY IT'S SPLIT THIS WAY

```
AI Brain/                        <- YOU OPEN THIS ONE. always. every session.
├── lifehack-brain/              <- OURS. replaced whole on every update.
│   ├── .claude/                     the commands — this is where Claude looks
│   │   ├── agents/                  the specialist readers the tool uses
│   │   ├── skills/                  the tools themselves
│   │   └── settings.json            wires it up the moment you clone
│   ├── system/                      the programs that do the sorting
│   ├── CLAUDE.md                    the standing instructions every session opens with
│   ├── UPDATE.md                    how to take a newer version, and what it cannot touch
│   └── PLAN-B.md                    the manual backup, if the tool ever misbehaves
└── data/                        <- YOURS. the only thing backed up.
    ├── system/journal.md            what happened, as it happens
    ├── system/project-registry.md   so a cold session can find an old project
    ├── state/briefs/                project notes
    └── desks/                       a folder per subject — built by your first ingest
        ├── <subject>/               one per pile the ingest finds in your own material
        └── <subject>/
```

**The split is the whole design.** Everything sent to you is in `lifehack-brain`. Everything you write
is in `data`, including the desks your ingest builds. An update replaces the first one completely — and
cannot reach the second even by accident, because your writing is not in that repository at all.

⭐ **And you open the folder ABOVE both of them.** That is what lets the tool reach your writing while
keeping it out of the repository. Opening one of the inner folders instead is the single most common way
this goes wrong.

**To get updates later, ask Claude:** *"check if there's an update to my brain and install it."*

---

# THE GOOGLE-CONNECTED PARTS — not here yet, and what they will need

Some of what is coming — reading your calendar, working with your mail, building spreadsheets — needs a
connection to **your own** Google account. **None of it is in this package yet**, so there is nothing to
set up today and nothing to go looking for.

Stated now so the shape is not a surprise later:

- **You connect your own account.** Nobody else's credentials are involved and nothing is shared. The
  tools ship; the account they talk to is yours.
- **Your own identifiers — which calendar, which spreadsheet — live in your `data` folder**, at
  `config/`, never in this repository. Same rule as everything else you own.
- **It is a sit-down, not a click.** Expect to do it with someone the first time.

⛔ **Until those parts ship, do not install Google tooling, do not run an authentication flow, and do not
ask them for account details.** Nothing here uses them.
