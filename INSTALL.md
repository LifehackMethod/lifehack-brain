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

**1. Make a folder and open it in Claude.** Call it whatever you like — "AI Brain" is the usual. Put it
somewhere ordinary like your Documents folder. Then: Claude desktop app, the **Code** tab, open that
folder.

**⛔ Not inside Google Drive, Dropbox or OneDrive.** Setup checks, and will send you back if it is.

**2. Drag this file into the chat and say: "Set up my brain."**

**3. That's it.** The folder you opened *is* your AI Brain — setup builds everything inside it and
doesn't ask you where anything goes.

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

## STEP 4 — ⛔ THE FOLDER THEY ALREADY OPENED **IS** THE AI BRAIN. DO NOT CREATE ANOTHER ONE.

> ⛔⛔ **DO NOT ASK THEM WHERE TO PUT IT. DO NOT OFFER A DEFAULT. DO NOT CREATE A NEW FOLDER.**
> **They already chose it — it is the folder this session is running in.** Every question here is a
> place the install stalls, and on 2026-08-12 it stalled on this question more than on anything else.
> ⭐ **On WINDOWS this matters most:** the old instructions sent people to `C:\Users\<name>\`, which is
> not where their session was running, and it produced permission detours that cost real students their
> install. **Use the session's own folder. Never `C:\Users\` .**

**Find out where you are and say it back to them in one sentence:**

```bash
pwd
```

*"You're set up in `<path>` — that's your AI Brain folder. Everything goes inside it."*

⛔ **Now check that folder is usable. This is the only thing that can send you back to them.**

```bash
python3 - "$PWD" <<'PY'
import os, re, sys
p = os.path.abspath(sys.argv[1]); low = p.replace("\\", "/").lower() + "/"
cloud = ["library/cloudstorage", "google drive", "googledrive", "/my drive/", "/shared drives/",
         "/shared drive/", "onedrive", "dropbox", "icloud", "mobile documents", "/box/", "pcloud"]
prot  = ["/program files", "/programdata", "/windows/", "/system/", "/library/"]
if re.fullmatch(r"[a-z]:/users/?", low) or low in ("/users/", "/home/"):
    print("PROTECTED - the bare users folder"); sys.exit(3)
hit = next((t for t in cloud if t in low), None)
if hit: print("IN A CLOUD FOLDER - matched: %s" % hit.strip("/")); sys.exit(2)
hit = next((t for t in prot if t in low), None)
if hit: print("PROTECTED SYSTEM FOLDER - matched: %s" % hit.strip("/")); sys.exit(3)
print("GOOD"); sys.exit(0)
PY
```

**`GOOD` → say nothing about it and carry straight on to STEP 5.**

**Anything else → this is the one time you ask them something.** Say plainly why this spot won't work —
*"this folder is inside your cloud storage, and the tool half can't live there; cloud syncing damages it
quietly"* — then: *"Quit Claude, open it again on a folder that isn't inside Google Drive, Dropbox or
OneDrive — your Documents folder is a good spot — and drag this file in again."* **Then STOP.** Do not
try to create a folder elsewhere and carry on; they must reopen the session there, or nothing the tool
does later will be able to reach it.

> ⛔ **Never test writability by asking for administrator rights.** If a write fails anywhere in this
> install, the answer is a different folder, never elevation. **A real student lost their install to
> exactly that detour on 2026-08-12.**

## STEP 5 — Fetch the tool INTO the folder you're already in

```bash
git clone https://github.com/LifehackMethod/lifehack-brain.git
```

**That creates `lifehack-brain` as a subfolder right here. That is exactly right.** ⛔ Do not `cd`
anywhere first, and do not clone into a folder you created yourself.

Confirm it landed:
```bash
ls lifehack-brain/.claude/skills/ingest/SKILL.md && echo "the skill is here"
```

**Tell them what arrived**, in a sentence: the tool itself, and the specialist readers it uses.

⭐ **The skills live inside that subfolder and are found from the folder above it — verified
2026-08-12.** ⛔ **Do NOT symlink anything into `~/.claude/`.** Symlinks are Mac-coupled and this has to
work on Windows too.

> ⛔ **If `git clone` refuses because a `lifehack-brain` folder is already here**, do NOT merge into it
> and do NOT `git init` an existing folder. Ask whether it's an older copy they can rename or delete,
> then clone again.

## STEP 6 — Confirm the pieces arrived, and turn on the safety catch

```bash
test -f lifehack-brain/.claude/skills/ingest/SKILL.md && test -d lifehack-brain/.claude/agents && echo "FILES OK" || echo "FILES MISSING"
```

**If `FILES OK`**, turn on the catch that keeps their own writing out of the repository:

```bash
cd lifehack-brain && git config core.hooksPath system/githooks && cd .. && echo "SAFETY CATCH ON"
```

**Say what that did, in one plain sentence:** *"I've turned on a safety catch — if anything ever tries to
upload your own notes to the internet, it will stop and refuse."*

⚠ **This line IS the install.** The check ships inside the folder, but git ignores it until this command
points at it. Without it, the file is decoration.

**If `FILES MISSING`**, the download didn't complete. ⛔ **Do not assemble or copy files yourself.**
Delete what's there and run **STEP 5** again.

## STEP 7 — Build `data`. ⛔ ASK THEM NOTHING.

> ⛔⛔ **THIS STEP USED TO ASK *"Where should everything you write end up?"* AND IT WAS THE SINGLE
> BIGGEST CAUSE OF FAILED INSTALLS. DO NOT REINTRODUCE IT IN ANY FORM.**
> It defaulted to a folder called "My Notes", which made people think it was a scratch folder for
> jottings — it is their entire memory. **Measured 2026-08-12: several students answered it with a bare
> "ok" and silently got a folder in the wrong place; others stalled on it and never restarted. It even
> confused a student whose install was otherwise working perfectly.**
> ⭐ **There is no decision here. `data` sits beside `lifehack-brain`. That is the design.**

```bash
mkdir -p data
python3 lifehack-brain/shared/brain_root.py --set "$PWD/data"
cd lifehack-brain && python3 system/tools/bootstrap.py && cd ..
```

**Then say what you made, in one plain sentence, and move on:** *"Your writing goes in a folder called
`data`, right next to the tool. I've put a journal, a project list and somewhere for project notes in
there — they fill themselves in as you work."*

⛔ **`desks/` is NOT created here.** Those appear inside `data` the first time they run an ingest, one
per subject, built from their own material. **Do not pre-create them and do not invent subject names.**

---

### ⚠ Then mention syncing — ONCE, as a recommendation. It is NOT a requirement and NOT a gate.

**Say it, and accept whatever they say back:**

> *"One thing worth doing when you have a minute: point Google Drive or Dropbox at the `data` folder, so
> your writing is synced. It's the part that's yours and can't be re-downloaded. Not required — you can
> do it any time."*

⛔ **Do NOT set it up for them, do NOT walk them through the menus now, and do NOT block the install on
it.** They are ten minutes into a setup and this is the least urgent thing in the file.

⛔⛔ **BUT IF THEY DO IT, IT MUST BE `data` AND NOTHING ELSE. NEVER THE FOLDER ABOVE IT.** That one holds
the git repository, and syncing it recreates the corruption problem STEP 4 exists to prevent. **Say that
sentence out loud when you mention it — it is the only part of this that can hurt them.**

## STEP 8 — Prove it can actually run, before you promise them anything

**A check you skipped is not a check that passed.**

```bash
cd lifehack-brain && python3 -c "import sys; sys.path.insert(0,'system/tools/cowork-ingest'); import pipeline; print('TOOLS OK')" && cd ..
```

**If it does not print `TOOLS OK`, stop.** Tell them plainly the install is incomplete and read them the
last line of the error. **Do not tell them to try `/ingest` anyway.**

Then confirm the shape — **exactly two folders, nothing else:**
```bash
ls -A
```
⛔ **It must show `data` and `lifehack-brain`.** Anything else means something went wrong; say so rather
than continuing.

> **One thing missing ON PURPOSE.** The last step of an ingest asks which subject each thing belongs to
> and checks it against a list of subjects. **That list is theirs and is not in this package.** The tool
> prints exactly what to do when they reach it. ⛔ **Do not pre-empt it, do not write the file for them,
> and do not treat its absence as a broken install.**

## STEP 9 — ⛔⛔ THE ONE STEP EVERYTHING ELSE DEPENDS ON: MAKE THEM RESTART CLAUDE

**Claude loads its commands when a session opens. This session opened before those files existed, so it
cannot see them yet.**

**Not optional and not a formality.** In a real test someone skipped it and Claude read the skill file as
a *document* instead of *running* it — twenty minutes of plausible work that wasn't the tool. **Nothing
errored.** That is what makes it dangerous.

Tell them, in these words or very close:

> **"Everything's installed. Now quit Claude completely and open it again — the whole app, not just a
> new chat. When it comes back, open this exact same folder: `<pwd>`. I'll wait."**

⭐ **Give them the literal path. They reopen the SAME folder they're in now** — the one holding `data`
and `lifehack-brain`. **Not `lifehack-brain`, not `data`.** Everything the tool needs is reachable from
here; open one of the inner folders and half the system is outside its reach.

⚠ **If they have installed before, they will reach for `lifehack-brain` out of habit, because the old
instructions told them to. Say so explicitly.**

Then **STOP. Do not continue this file. Do not offer to run `/ingest` yourself.**

## STEP 10 — After they restart (the first thing to do in the NEW session)

Confirm the command exists before they type anything:

```bash
ls lifehack-brain/.claude/skills/ingest/SKILL.md
```

⭐ **You are in the AI Brain folder and the tool is one level down. That is correct and is how it should
look.**

Then tell them:

> **"You're set up. Type `/ingest` and press enter. It already knows where your writing goes. It'll ask
> for your material: drag the file or folder into the chat and it'll fill in the location. From there it
> asks you questions and shows you its work before it writes anything."**

⚠ **And once:** *"If it ever goes quiet, look for a small box with an Allow button. It's waiting on you,
not stuck."*

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
